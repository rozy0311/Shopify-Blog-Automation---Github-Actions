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

const blogHandle = "sustainable-living";
const author = "The Rike";

const folders = [
  "bitter-melon-cool-season-strategies-in-mild-coastal-areas-zones-8-9",
  "bitter-melon-troubleshooting-yellow-leaves-blossom-drop-and-bitter-off-flavors",
];

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
  if (!response.ok) throw new Error(`${response.status} ${text.slice(0, 400)}`);
  return text ? JSON.parse(text) : {};
}

function readArticle(dir) {
  const mdPath = path.join(dir, "article.md");
  const clipPath = path.join(dir, "article.clipboard.txt");
  let raw = "";
  if (fs.existsSync(mdPath)) raw = fs.readFileSync(mdPath, "utf8");
  else if (fs.existsSync(clipPath)) raw = fs.readFileSync(clipPath, "utf8");
  else throw new Error(`Missing content file in ${dir}`);

  const titleMatch = raw.match(/^#\s+(.+)$/m) || raw.match(/^TITLE:\s*(.+)$/m);
  const title = titleMatch ? titleMatch[1].trim() : path.basename(dir).replace(/-/g, " ");
  const i = raw.indexOf("<article");
  const html = i >= 0 ? raw.slice(i).trim() : raw.trim();
  return { title, html };
}

function stripInlineImages(html) {
  return html
    .replace(/<figure\b[^>]*>[\s\S]*?<img\b[^>]*>[\s\S]*?<\/figure>/gi, "")
    .replace(/<img\b[^>]*>/gi, "");
}

function interleaveByParagraph(html, imageTags) {
  const parts = html.split(/(<\/p>)/i);
  const closes = [];
  for (let i = 0; i < parts.length; i += 1) {
    if (/^<\/p>$/i.test(parts[i])) closes.push(i);
  }
  if (!closes.length) return `${html}\n${imageTags.join("\n")}`;

  const target = [0.22, 0.52, 0.8].map((r) => closes[Math.min(closes.length - 1, Math.floor(closes.length * r))]);
  const uniq = [];
  for (const x of target) if (!uniq.includes(x)) uniq.push(x);

  const map = new Map();
  for (let i = 0; i < imageTags.length && i < uniq.length; i += 1) map.set(uniq[i], `\n${imageTags[i]}\n`);

  const out = [];
  for (let i = 0; i < parts.length; i += 1) {
    out.push(parts[i]);
    if (map.has(i)) out.push(map.get(i));
  }
  return out.join("");
}

async function main() {
  if (!shop || !token) throw new Error("Missing SHOPIFY_SHOP or SHOPIFY_TOKEN");

  const blogs = await jfetch(`${apiBase}/blogs.json`);
  const blog = (blogs.blogs || []).find((b) => b.handle === blogHandle) || blogs.blogs?.[0];
  if (!blog) throw new Error("No blog found");

  const themes = await jfetch(`${apiBase}/themes.json`);
  const mainTheme = (themes.themes || []).find((t) => t.role === "main") || themes.themes?.[0];
  if (!mainTheme) throw new Error("No main theme");

  const results = [];

  for (const folder of folders) {
    const dir = path.join("pplx-ui-batch", "out", "content", folder);
    const { title, html } = readArticle(dir);

    const created = await jfetch(`${apiBase}/blogs/${blog.id}/articles.json`, {
      method: "POST",
      body: JSON.stringify({ article: { title, author, body_html: html, tags: [] } }),
    });

    const articleId = created.article.id;
    const urls = [];
    for (let i = 1; i <= 3; i += 1) {
      const imgPath = path.join(dir, `inline-${i}.png`);
      if (!fs.existsSync(imgPath)) continue;
      const attachment = fs.readFileSync(imgPath).toString("base64");
      const key = `assets/auto-inline-${articleId}-${i}-${Date.now()}.png`;
      const uploaded = await jfetch(`${apiBase}/themes/${mainTheme.id}/assets.json`, {
        method: "PUT",
        body: JSON.stringify({ asset: { key, attachment } }),
      });
      const u = uploaded?.asset?.public_url || uploaded?.asset?.src || `https://${shop}.myshopify.com/cdn/shop/t/${mainTheme.id}/assets/${path.basename(key)}?v=${Date.now()}`;
      urls.push(u);
    }

    if (urls.length) {
      const tags = urls.map((u, idx) => `<figure><img src="${u}" alt="${title} inline image ${idx + 1}" loading="lazy" /></figure>`);
      const cleaned = stripInlineImages(created.article.body_html || "");
      const body = interleaveByParagraph(cleaned, tags);
      await jfetch(`${apiBase}/blogs/${blog.id}/articles/${articleId}.json`, {
        method: "PUT",
        body: JSON.stringify({ article: { id: articleId, body_html: body, image: { src: urls[0] } } }),
      });
    }

    const verify = await jfetch(`${apiBase}/blogs/${blog.id}/articles/${articleId}.json`);
    const count = ((verify.article.body_html || "").match(/<img\b/gi) || []).length;
    results.push({
      id: verify.article.id,
      title: verify.article.title,
      imgCount: count,
      published_at: verify.article.published_at,
      url: `https://${shop}.myshopify.com/blogs/${blog.handle}/${verify.article.handle}`,
    });
  }

  console.log(JSON.stringify({ results }, null, 2));
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
