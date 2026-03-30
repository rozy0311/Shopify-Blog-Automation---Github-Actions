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
  const imageSrc = await resolvePublishableImageSrc(rawImageSrc, data.title);
  const image = imageSrc ? await buildShopifyImageAttachment(imageSrc, data.title) : undefined;

  if (!image) {
    console.warn(`[SHOPIFY] No publishable featured image for: ${data.title}`);
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

async function buildShopifyImageAttachment(imageSrc: string, title: string) {
  const timeoutMs = 20000;
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(imageSrc, {
      method: "GET",
      redirect: "follow",
      signal: controller.signal,
    });

    if (!response.ok || !isImageContentType(response.headers.get("content-type"))) {
      return { src: imageSrc, alt: title };
    }

    const contentLength = Number(response.headers.get("content-length") || "0");
    if (Number.isFinite(contentLength) && contentLength > 12 * 1024 * 1024) {
      return { src: imageSrc, alt: title };
    }

    const arrayBuffer = await response.arrayBuffer();
    const bytes = Buffer.from(arrayBuffer);
    if (!bytes.length || bytes.length > 12 * 1024 * 1024) {
      return { src: imageSrc, alt: title };
    }

    return {
      attachment: bytes.toString("base64"),
      alt: title,
    };
  } catch {
    return { src: imageSrc, alt: title };
  } finally {
    clearTimeout(timeout);
  }
}

async function resolvePublishableImageSrc(rawImageSrc: string | undefined, title: string): Promise<string | undefined> {
  if (rawImageSrc) {
    const direct = await tryGetPublishableImageSrc(rawImageSrc);
    if (direct) return direct;
  }

  const fallback = buildPollinationsFallbackImageUrl(title);
  if (!fallback) return undefined;

  const fallbackResolved = await tryGetPublishableImageSrc(fallback);
  if (fallbackResolved) {
    console.log(`[SHOPIFY] Using fallback realistic image for: ${title}`);
  }
  return fallbackResolved;
}

function buildPollinationsFallbackImageUrl(title: string): string | undefined {
  const prompt = `ultra realistic editorial photo for blog article: ${title}, natural lighting, high detail`;
  const encodedPrompt = encodeURIComponent(prompt);
  const seed = deterministicSeed(title);

  // Public Pollinations endpoint, tuned for realistic photo style.
  return `https://image.pollinations.ai/prompt/${encodedPrompt}?width=1536&height=1024&nologo=true&seed=${seed}&model=flux`;
}

function deterministicSeed(input: string): number {
  let hash = 0;
  for (let i = 0; i < input.length; i += 1) {
    hash = (hash * 31 + input.charCodeAt(i)) >>> 0;
  }
  return hash || 1;
}

async function tryGetPublishableImageSrc(rawImageSrc: string): Promise<string | undefined> {

  let parsed: URL;
  try {
    parsed = new URL(rawImageSrc);
  } catch {
    return undefined;
  }

  if (parsed.protocol !== "http:" && parsed.protocol !== "https:") {
    return undefined;
  }

  const timeoutMs = 12000;
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const head = await fetch(parsed.toString(), {
      method: "HEAD",
      redirect: "follow",
      signal: controller.signal,
    });
    if (head.ok && isImageContentType(head.headers.get("content-type"))) {
      return parsed.toString();
    }

    const get = await fetch(parsed.toString(), {
      method: "GET",
      redirect: "follow",
      signal: controller.signal,
    });
    if (get.ok && isImageContentType(get.headers.get("content-type"))) {
      return parsed.toString();
    }

    return undefined;
  } catch {
    return undefined;
  } finally {
    clearTimeout(timeout);
  }
}

function isImageContentType(value: string | null): boolean {
  if (!value) return false;
  return value.toLowerCase().includes("image/");
}
