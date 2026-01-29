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

export async function updateArticle(articleId: string, payload: any) {
  const shop = process.env.SHOPIFY_SHOP;
  const token = process.env.SHOPIFY_TOKEN;
  if (!shop || !token) throw new Error("Missing Shopify env vars");

  const response = await fetch(
    `https://${shop}.myshopify.com/admin/api/2023-10/articles/${articleId}.json`,
    {
      method: "PUT",
      headers: {
        "X-Shopify-Access-Token": token,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ article: payload }),
    },
  );

  if (!response.ok) {
    const text = await response.text();
    throw new Error(`Shopify PUT ${response.status}: ${text}`);
  }
  return response.json();
}

export async function publishArticle(
  blogHandle: string,
  author: string,
  data: { title: string; html: string; images?: Array<{ src?: string } | null> },
) {
  const blog = await withRetry(() => getBlogByHandle(blogHandle));
  const image = Array.isArray(data.images) && data.images[0]?.src ? { src: data.images[0]?.src } : undefined;
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

export async function createDraftArticle(
  blogHandle: string,
  author: string,
  data: { title: string; html: string; images?: Array<{ src?: string } | null> },
) {
  const blog = await withRetry(() => getBlogByHandle(blogHandle));
  const image = Array.isArray(data.images) && data.images[0]?.src ? { src: data.images[0]?.src } : undefined;
  return withRetry(() =>
    createArticle(blog.id, {
      title: data.title,
      author,
      body_html: data.html,
      tags: [],
      image,
      published: false,
    }),
  );
}

export async function publishExistingArticle(articleId: string) {
  return withRetry(() => updateArticle(articleId, { published: true }));
}
