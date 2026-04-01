require('dotenv').config();

const shop = (process.env.SHOPIFY_SHOP || '')
  .replace(/^https?:\/\//, '')
  .replace(/\/$/, '')
  .replace(/\.myshopify\.com$/, '');
const token = process.env.SHOPIFY_TOKEN || process.env.SHOPIFY_ACCESS_TOKEN;
const base = `https://${shop}.myshopify.com/admin/api/2023-10`;
const blogId = '108441862462';
const ids = [692971766078, 692971798846, 692971700542];

function firstImg(html = '') {
  const m = html.match(/<img[^>]+src=["']([^"']+)["']/i);
  return m ? m[1] : null;
}

async function run() {
  for (const id of ids) {
    const get = await fetch(`${base}/blogs/${blogId}/articles/${id}.json`, {
      headers: {
        'X-Shopify-Access-Token': token,
        'Content-Type': 'application/json'
      }
    });
    const gj = await get.json();
    const a = gj.article || {};
    const src = firstImg(a.body_html || '');
    if (!src) {
      console.log(JSON.stringify({ id, updated: false, reason: 'NO_IMAGE_IN_BODY' }));
      continue;
    }

    const put = await fetch(`${base}/blogs/${blogId}/articles/${id}.json`, {
      method: 'PUT',
      headers: {
        'X-Shopify-Access-Token': token,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ article: { id, image: { src } } })
    });
    const pj = await put.json();
    console.log(JSON.stringify({
      id,
      updated: true,
      hasFeatured: !!(pj.article && pj.article.image && pj.article.image.src),
      featuredSrc: pj.article?.image?.src || null
    }));
  }
}

run().catch((e) => {
  console.error(e);
  process.exit(1);
});
