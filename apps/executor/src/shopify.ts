import "dotenv/config";
import { withRetry } from "./batch.js";

export async function getBlogByHandle(handle: string) {
  const shop = process.env.SHOPIFY_SHOP;
  if (!shop) throw new Error("Missing SHOPIFY_SHOP");
  const token = process.env.SHOPIFY_TOKEN;
  if (!token) throw new Error("Missing SHOPIFY_TOKEN");

  const response = await fetch(`https://${shop}.myshopify.com/admin/api/2023-10/blogs.json`, {
    headers: {
      "X-Shopify-Access-Token": token,
      "Content-Type": "application/json",
    },
  });
  if (!response.ok) {
    throw new Error(`Shopify GET blogs ${response.status}`);
  }
  const json = await response.json();
  const blog = (json.blogs || []).find((entry: any) => (entry.handle || "") === handle);
  if (!blog) throw new Error(`Blog handle not found: ${handle}`);
  return blog;
}

export async function createArticle(blogId: string, payload: any) {
  const shop = process.env.SHOPIFY_SHOP;
  const token = process.env.SHOPIFY_TOKEN;
  if (!shop || !token) throw new Error("Missing Shopify env vars");

  const response = await fetch(
    `https://${shop}.myshopify.com/admin/api/2023-10/blogs/${blogId}/articles.json`,
    {
      method: "POST",
      headers: {
        "X-Shopify-Access-Token": token,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ article: payload }),
    },
  );

  if (!response.ok) {
    const text = await response.text();
    throw new Error(`Shopify POST ${response.status}: ${text}`);
  }
  return response.json();
}

export async function publishArticle(
  blogHandle: string,
  author: string,
  data: { title: string; html: string; images?: Array<{ src?: string } | null> },
) {
  const blog = await withRetry(() => getBlogByHandle(blogHandle));
  const rawImageSrc = Array.isArray(data.images) ? data.images[0]?.src?.trim() : undefined;
  let image: { src: string } | undefined;
  if (rawImageSrc) {
    try {
      const parsed = new URL(rawImageSrc);
      if (parsed.protocol === "http:" || parsed.protocol === "https:") {
        image = { src: rawImageSrc };
      }
    } catch {
      // Keep image undefined when src is malformed so article can still publish.
    }
  }
  return withRetry(() =>
    createArticle(blog.id, {
      title: data.title,
      author,
      body_html: data.html,
      tags: [],
      image,
    }),
  );
}
