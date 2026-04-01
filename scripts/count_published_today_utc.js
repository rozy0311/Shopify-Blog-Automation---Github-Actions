const shopRaw = (process.env.SHOPIFY_SHOP || "").trim();
const shop = shopRaw.replace(/^https?:\/\//, "").replace(/\/$/, "").replace(/\.myshopify\.com$/, "");
const token = process.env.SHOPIFY_TOKEN || "";
const blogHandle = process.env.BLOG_HANDLE || "";

function fail(msg) {
  console.error(msg);
  process.exit(1);
}

if (!shop || !token || !blogHandle) {
  fail("Missing SHOPIFY_SHOP / SHOPIFY_TOKEN / BLOG_HANDLE");
}

const apiBase = `https://${shop}.myshopify.com/admin/api/2023-10`;
const headers = {
  "X-Shopify-Access-Token": token,
  "Content-Type": "application/json",
};

const now = new Date();
const dayStart = Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate(), 0, 0, 0, 0);
const dayEnd = dayStart + 24 * 60 * 60 * 1000;

function parsePublishedMs(value) {
  if (!value) return null;
  const ms = Date.parse(value);
  return Number.isFinite(ms) ? ms : null;
}

async function main() {
  const blogsResp = await fetch(`${apiBase}/blogs.json`, { headers });
  if (!blogsResp.ok) fail(`Shopify blogs API failed: ${blogsResp.status}`);
  const blogsJson = await blogsResp.json();
  const blogs = Array.isArray(blogsJson.blogs) ? blogsJson.blogs : [];
  const blog = blogs.find((b) => (b.handle || "") === blogHandle);
  if (!blog) fail(`Blog handle not found: ${blogHandle}`);

  let sinceId = 0;
  let count = 0;

  while (true) {
    const url = new URL(`${apiBase}/blogs/${blog.id}/articles.json`);
    url.searchParams.set("limit", "250");
    url.searchParams.set("fields", "id,published_at");
    if (sinceId > 0) url.searchParams.set("since_id", String(sinceId));

    const resp = await fetch(url.toString(), { headers });
    if (!resp.ok) fail(`Shopify articles API failed: ${resp.status}`);

    const json = await resp.json();
    const page = Array.isArray(json.articles) ? json.articles : [];
    if (page.length === 0) break;

    for (const article of page) {
      const ms = parsePublishedMs(article.published_at);
      if (ms !== null && ms >= dayStart && ms < dayEnd) count += 1;
    }

    sinceId = page[page.length - 1].id;
    if (page.length < 250) break;
  }

  console.log(String(count));
}

main().catch((error) => fail(error instanceof Error ? error.message : String(error)));
