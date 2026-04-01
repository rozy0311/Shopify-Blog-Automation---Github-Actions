const fs = require("fs");
const path = require("path");
require("dotenv").config();

const rawShop = (process.env.SHOPIFY_SHOP || "").trim();
const shop = rawShop
  .replace(/^https?:\/\//, "")
  .replace(/\/$/, "")
  .replace(/\.myshopify\.com$/, "");
const token = process.env.SHOPIFY_TOKEN || process.env.SHOPIFY_ACCESS_TOKEN;
const apiBase = `https://${shop}.myshopify.com/admin/api/2023-10`;

const target = {
  title: "Bitter melon pruning and training for higher yield in small spaces",
  dir: "pplx-ui-batch/out/content/bitter-melon-pruning-and-training-boosting-flower-set-and-fruit-size",
  blogHandle: "sustainable-living",
  author: "The Rike",
};

async function jfetch(url, opt = {}) {
  const response = await fetch(url, {
    ...opt,
    headers: {
      "X-Shopify-Access-Token": token,
      "Content-Type": "application/json",
      ...(opt.headers || {}),
    },
  });
  const text = await response.text();
  if (!response.ok) {
    throw new Error(`${response.status} ${text.slice(0, 400)}`);
  }
  return text ? JSON.parse(text) : {};
}

function readArticleHtml(dir) {
  const mdPath = path.join(dir, "article.md");
  const clipboardPath = path.join(dir, "article.clipboard.txt");
  let content = "";

  if (fs.existsSync(mdPath)) {
    content = fs.readFileSync(mdPath, "utf8");
  } else if (fs.existsSync(clipboardPath)) {
    content = fs.readFileSync(clipboardPath, "utf8");
  } else {
    throw new Error(`Missing article content in ${dir}`);
  }

  const articleIndex = content.indexOf("<article");
  return articleIndex >= 0 ? content.slice(articleIndex).trim() : content.trim();
}

async function main() {
  if (!shop || !token) throw new Error("Missing SHOPIFY_SHOP or SHOPIFY_TOKEN");

  const blogsJson = await jfetch(`${apiBase}/blogs.json`);
  const blog = (blogsJson.blogs || []).find((b) => b.handle === target.blogHandle) || blogsJson.blogs?.[0];
  if (!blog) throw new Error("No blog found");

  const html = readArticleHtml(target.dir);
  const created = await jfetch(`${apiBase}/blogs/${blog.id}/articles.json`, {
    method: "POST",
    body: JSON.stringify({
      article: {
        title: target.title,
        author: target.author,
        body_html: html,
        tags: [],
      },
    }),
  });

  const articleId = created.article.id;

  const themesJson = await jfetch(`${apiBase}/themes.json`);
  const mainTheme = (themesJson.themes || []).find((t) => t.role === "main") || themesJson.themes?.[0];

  const inlineUrls = [];
  for (let i = 1; i <= 3; i += 1) {
    const imagePath = path.join(target.dir, `inline-${i}.png`);
    if (!fs.existsSync(imagePath)) continue;

    const attachment = fs.readFileSync(imagePath).toString("base64");
    const key = `assets/auto-inline-${articleId}-${i}-${Date.now()}.png`;

    await jfetch(`${apiBase}/themes/${mainTheme.id}/assets.json`, {
      method: "PUT",
      body: JSON.stringify({ asset: { key, attachment } }),
    });

    inlineUrls.push(`https://${shop}.myshopify.com/cdn/shop/t/${mainTheme.id}/${key}`);
  }

  if (inlineUrls.length > 0) {
    const imageBlocks = inlineUrls
      .map(
        (url, idx) =>
          `<figure><img src="${url}" alt="${target.title} image ${idx + 1}" loading="lazy" /></figure>`
      )
      .join("");

    const updatedBody = `${imageBlocks}${created.article.body_html || ""}`;

    await jfetch(`${apiBase}/blogs/${blog.id}/articles/${articleId}.json`, {
      method: "PUT",
      body: JSON.stringify({ article: { id: articleId, body_html: updatedBody, image: { src: inlineUrls[0] } } }),
    });
  }

  const verify = await jfetch(`${apiBase}/blogs/${blog.id}/articles/${articleId}.json`);
  const imgCount = ((verify.article.body_html || "").match(/<img\b/gi) || []).length;

  console.log(
    JSON.stringify(
      {
        id: verify.article.id,
        title: verify.article.title,
        published_at: verify.article.published_at,
        imgCount,
        url: `https://${shop}.myshopify.com/blogs/${blog.handle}/${verify.article.handle}`,
      },
      null,
      2,
    ),
  );
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
