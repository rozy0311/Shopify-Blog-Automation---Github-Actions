import "dotenv/config";
import { withRetry } from "./batch.js";

export type ImageBrief = {
  prompt: string;
  alt: string;
};

let cachedMainThemeId: number | undefined;

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

export async function listArticles(blogId: string, limit = 250): Promise<Array<{ id: number; title: string; handle: string; body_html: string; published_at: string | null }>> {
  const shop = process.env.SHOPIFY_SHOP;
  const token = process.env.SHOPIFY_TOKEN;
  if (!shop || !token) throw new Error("Missing Shopify env vars");

  const articles: Array<{ id: number; title: string; handle: string; body_html: string; published_at: string | null }> = [];
  let sinceId = 0;

  while (true) {
    const url = new URL(`https://${shop}.myshopify.com/admin/api/2023-10/blogs/${blogId}/articles.json`);
    url.searchParams.set("limit", String(Math.min(limit - articles.length, 250)));
    url.searchParams.set("fields", "id,title,handle,body_html,published_at");
    if (sinceId > 0) url.searchParams.set("since_id", String(sinceId));

    const response = await fetch(url.toString(), {
      headers: {
        "X-Shopify-Access-Token": token,
        "Content-Type": "application/json",
      },
    });

    if (!response.ok) {
      const text = await response.text();
      throw new Error(`Shopify GET articles ${response.status}: ${text}`);
    }

    const json = await response.json() as { articles: Array<{ id: number; title: string; handle: string; body_html: string; published_at: string | null }> };
    const page = json.articles || [];
    if (page.length === 0) break;

    articles.push(...page);
    sinceId = page.at(-1)?.id || sinceId;

    if (articles.length >= limit || page.length < 250) break;
  }

  return articles;
}

export async function getArticle(blogId: string, articleId: number) {
  const shop = process.env.SHOPIFY_SHOP;
  const token = process.env.SHOPIFY_TOKEN;
  if (!shop || !token) throw new Error("Missing Shopify env vars");

  const response = await fetch(
    `https://${shop}.myshopify.com/admin/api/2023-10/blogs/${blogId}/articles/${articleId}.json`,
    {
      headers: {
        "X-Shopify-Access-Token": token,
        "Content-Type": "application/json",
      },
    },
  );

  if (!response.ok) {
    const text = await response.text();
    throw new Error(`Shopify GET article ${response.status}: ${text}`);
  }

  return response.json();
}

export async function updateArticle(blogId: string, articleId: number, payload: Record<string, unknown>) {
  const shop = process.env.SHOPIFY_SHOP;
  const token = process.env.SHOPIFY_TOKEN;
  if (!shop || !token) throw new Error("Missing Shopify env vars");

  const response = await fetch(
    `https://${shop}.myshopify.com/admin/api/2023-10/blogs/${blogId}/articles/${articleId}.json`,
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
    throw new Error(`Shopify PUT article ${response.status}: ${text}`);
  }

  return response.json();
}

export async function publishArticle(
  blogHandle: string,
  author: string,
  data: { title: string; html: string; images?: Array<{ src?: string } | null> },
  imageBrief?: ImageBrief,
) {
  const blog = await withRetry(() => getBlogByHandle(blogHandle));
  const duplicate = await findDuplicateArticleByTitle(blog.id, data.title);
  if (duplicate) {
    console.warn(`[SHOPIFY] Duplicate title detected, reusing existing article: ${duplicate.title} (${duplicate.id})`);
    return { article: duplicate, duplicate: true as const };
  }

  const rawImageSrc = Array.isArray(data.images) ? data.images[0]?.src?.trim() : undefined;
  const candidates = await resolvePublishableImageCandidates(rawImageSrc, data.title, imageBrief);

  let image: { attachment: string; alt: string } | undefined;
  for (const candidate of candidates) {
    const attachment = await buildShopifyImageAttachment(candidate, imageBrief?.alt || data.title);
    if (attachment) {
      image = attachment;
      break;
    }
  }

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

async function findDuplicateArticleByTitle(
  blogId: string,
  title: string,
): Promise<{ id: number; title: string; handle: string; body_html: string; published_at: string | null } | null> {
  const normalizedTarget = normalizeTitle(title);
  if (!normalizedTarget) return null;

  const existing = await withRetry(() => listArticles(blogId, 250));
  for (const article of existing) {
    if (normalizeTitle(article.title) === normalizedTarget) {
      return article;
    }
  }
  return null;
}

function normalizeTitle(value: string): string {
  return String(value || "")
    .toLowerCase()
    .replaceAll(/\s+/g, " ")
    .trim();
}

export async function generateHostedGeminiImages(
  briefs: ImageBrief[],
  title: string,
): Promise<string[]> {
  const urls: string[] = [];
  const normalized = briefs
    .map((brief) => ({
      prompt: String(brief.prompt || "").trim(),
      alt: String(brief.alt || "").trim(),
    }))
    .filter((brief) => brief.prompt.length > 0);

  for (const [index, brief] of normalized.entries()) {
    try {
      const generated = await generateGeminiImage(brief, title);
      const uploaded = await uploadThemeAssetImage(generated.bytes, generated.mimeType, `${title}-${index + 1}`);
      urls.push(uploaded);
      console.log(`[GEMINI_IMAGE] Hosted fallback image ${index + 1}/${normalized.length}`);
    } catch (error) {
      console.warn(`[GEMINI_IMAGE] Failed hosted fallback image ${index + 1}:`, error instanceof Error ? error.message : error);
    }
  }

  return urls;
}

async function buildShopifyImageAttachment(imageSrc: string, title: string): Promise<{ attachment: string; alt: string } | undefined> {
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
      return undefined;
    }

    const contentLength = Number(response.headers.get("content-length") || "0");
    if (Number.isFinite(contentLength) && contentLength > 12 * 1024 * 1024) {
      return undefined;
    }

    const arrayBuffer = await response.arrayBuffer();
    const bytes = Buffer.from(arrayBuffer);
    if (!bytes.length || bytes.length > 12 * 1024 * 1024) {
      return undefined;
    }

    return {
      attachment: bytes.toString("base64"),
      alt: title,
    };
  } catch {
    return undefined;
  } finally {
    clearTimeout(timeout);
  }
}

async function resolvePublishableImageCandidates(
  rawImageSrc: string | undefined,
  title: string,
  imageBrief?: ImageBrief,
): Promise<string[]> {
  const candidates: string[] = [];

  if (rawImageSrc) {
    const direct = await tryGetPublishableImageSrc(rawImageSrc);
    if (direct) candidates.push(direct);
  }

  if (imageBrief?.prompt) {
    const hostedFallbacks = await generateHostedGeminiImages([imageBrief], title);
    for (const fallback of hostedFallbacks) {
      const resolved = await tryGetPublishableImageSrc(fallback);
      if (resolved) {
        console.log(`[SHOPIFY] Using Gemini hosted fallback image for: ${title}`);
        candidates.push(resolved);
      }
    }
  }

  return [...new Set(candidates)];
}

async function generateGeminiImage(
  brief: ImageBrief,
  title: string,
): Promise<{ bytes: Buffer; mimeType: string }> {
  const model = (process.env.GEMINI_IMAGE_MODEL || "gemini-2.5-flash-image").trim();
  const imageSize = (process.env.GEMINI_IMAGE_SIZE || "1K").trim();
  const apiKeys = getGeminiApiKeys();
  const endpoint = `https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent`;
  const prompt = buildGeminiImagePrompt(brief, title);
  let lastError: Error | undefined;

  for (const apiKey of apiKeys) {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), getGeminiImageTimeoutMs());

    try {
      const response = await fetch(endpoint, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "x-goog-api-key": apiKey,
        },
        body: JSON.stringify({
          contents: [
            {
              role: "user",
              parts: [{ text: prompt }],
            },
          ],
          generationConfig: {
            responseModalities: ["IMAGE"],
            imageConfig: {
              aspectRatio: "16:9",
              imageSize,
            },
          },
        }),
        signal: controller.signal,
      });

      if (!response.ok) {
        const message = await readResponseError(response, `Gemini image HTTP ${response.status}`);
        const error = new Error(message);
        lastError = error;
        if (shouldTryNextGeminiKey(response.status)) {
          continue;
        }
        throw error;
      }

      const json = await response.json();
      const imagePart = extractGeminiImagePart(json);
      if (!imagePart) {
        const finishReason = json?.candidates?.[0]?.finishReason || json?.candidates?.[0]?.finish_reason;
        const blockReason = json?.promptFeedback?.blockReason || json?.prompt_feedback?.block_reason;
        throw new Error(`Gemini image returned no image data${finishReason ? ` (${finishReason})` : ""}${blockReason ? ` [${blockReason}]` : ""}`);
      }

      return {
        bytes: Buffer.from(imagePart.data, "base64"),
        mimeType: imagePart.mimeType,
      };
    } catch (error) {
      const isAbort = error instanceof Error && error.name === "AbortError";
      lastError = isAbort ? new Error("Gemini image request timed out") : error instanceof Error ? error : new Error(String(error));
      if (!isAbort && !shouldContinueAfterGeminiError(lastError)) {
        throw lastError;
      }
    } finally {
      clearTimeout(timeout);
    }
  }

  throw lastError || new Error("Gemini image exhausted all configured API keys");
}

function getGeminiApiKeys(): string[] {
  const keyCandidates = [
    process.env.GOOGLE_AI_STUDIO_API_KEY,
    process.env.GEMINI_API_KEY,
    process.env.FALLBACK_GOOGLE_AI_STUDIO_API_KEY,
    process.env.FALLBACK_GEMINI_API_KEY,
    process.env.SECOND_FALLBACK_GOOGLE_AI_STUDIO_API_KEY,
    process.env.SECOND_FALLBACK_GEMINI_API_KEY,
    process.env.THIRD_FALLBACK_GOOGLE_AI_STUDIO_API_KEY,
    process.env.THIRD_FALLBACK_GEMINI_API_KEY,
    process.env.FOURTH_FALLBACK_GOOGLE_AI_STUDIO_API_KEY,
    process.env.FOURTH_FALLBACK_GEMINI_API_KEY,
    process.env.FIFTH_FALLBACK_GOOGLE_AI_STUDIO_API_KEY,
    process.env.FIFTH_FALLBACK_GEMINI_API_KEY,
    process.env.SIXTH_FALLBACK_GOOGLE_AI_STUDIO_API_KEY,
    process.env.SIXTH_FALLBACK_GEMINI_API_KEY,
  ];
  const apiKeys = [...new Set(keyCandidates.map((key) => (key || "").trim()).filter(Boolean))];
  if (!apiKeys.length) {
    throw new Error("Missing Gemini image API keys");
  }
  return apiKeys;
}

function buildGeminiImagePrompt(brief: ImageBrief, title: string): string {
  return [
    `Create one photorealistic editorial image for the article titled: ${title}.`,
    `Scene brief: ${brief.prompt}`,
    "Camera direction: 50mm lens, f/2.8, ISO 200, 1/125s, natural window light, shallow depth of field.",
    "High resolution, ultra-detailed, cozy-authority editorial photography.",
    "Do not include people, hands, faces, logos, text overlays, or watermarks.",
    "Output image only.",
  ].join("\n");
}

function getGeminiImageTimeoutMs(): number {
  const raw = Number(process.env.GEMINI_IMAGE_TIMEOUT_MS || process.env.OPENAI_TIMEOUT_MS || "240000");
  return Number.isFinite(raw) ? Math.max(60000, Math.min(900000, raw)) : 240000;
}

function shouldTryNextGeminiKey(status: number): boolean {
  return status === 401 || status === 403 || status === 429 || status >= 500;
}

function shouldContinueAfterGeminiError(error: Error): boolean {
  const message = error.message.toLowerCase();
  return message.includes("timed out") || message.includes("429") || message.includes("500") || message.includes("503");
}

function extractGeminiImagePart(payload: any): { data: string; mimeType: string } | undefined {
  const candidates = Array.isArray(payload?.candidates) ? payload.candidates : [];
  for (const candidate of candidates) {
    const parts = Array.isArray(candidate?.content?.parts) ? candidate.content.parts : [];
    for (const part of parts) {
      const inlineData = part?.inlineData || part?.inline_data;
      const data = inlineData?.data;
      const mimeType = inlineData?.mimeType || inlineData?.mime_type;
      if (typeof data === "string" && typeof mimeType === "string" && mimeType.startsWith("image/")) {
        return { data, mimeType };
      }
    }
  }
  return undefined;
}

async function uploadThemeAssetImage(bytes: Buffer, mimeType: string, title: string): Promise<string> {
  const shop = process.env.SHOPIFY_SHOP;
  const token = process.env.SHOPIFY_TOKEN;
  if (!shop || !token) throw new Error("Missing Shopify env vars");

  const themeId = await getMainThemeId();
  const extension = mimeTypeToExtension(mimeType);
  const slug = slugify(title) || "generated-image";
  const key = `assets/auto-${slug}-${Date.now()}.${extension}`;
  const response = await fetch(`https://${shop}.myshopify.com/admin/api/2023-10/themes/${themeId}/assets.json`, {
    method: "PUT",
    headers: {
      "X-Shopify-Access-Token": token,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      asset: {
        key,
        attachment: bytes.toString("base64"),
      },
    }),
  });

  if (!response.ok) {
    throw new Error(await readResponseError(response, `Shopify theme asset upload ${response.status}`));
  }

  const json = await response.json();
  return (
    json?.asset?.public_url ||
    json?.asset?.src ||
    `https://${shop}.myshopify.com/cdn/shop/t/${themeId}/assets/${key.split("/").at(-1)}?v=${Date.now()}`
  );
}

async function getMainThemeId(): Promise<number> {
  if (cachedMainThemeId) return cachedMainThemeId;

  const shop = process.env.SHOPIFY_SHOP;
  const token = process.env.SHOPIFY_TOKEN;
  if (!shop || !token) throw new Error("Missing Shopify env vars");

  const response = await fetch(`https://${shop}.myshopify.com/admin/api/2023-10/themes.json`, {
    headers: {
      "X-Shopify-Access-Token": token,
      "Content-Type": "application/json",
    },
  });

  if (!response.ok) {
    throw new Error(await readResponseError(response, `Shopify GET themes ${response.status}`));
  }

  const json = await response.json();
  const themes = Array.isArray(json?.themes) ? json.themes : [];
  const mainTheme = themes.find((theme: any) => theme?.role === "main") || themes[0];
  if (!mainTheme?.id) {
    throw new Error("No Shopify main theme found for hosted image upload");
  }

  cachedMainThemeId = Number(mainTheme.id);
  return cachedMainThemeId;
}

function mimeTypeToExtension(mimeType: string): string {
  if (mimeType.includes("png")) return "png";
  if (mimeType.includes("webp")) return "webp";
  if (mimeType.includes("jpeg") || mimeType.includes("jpg")) return "jpg";
  return "png";
}

function slugify(value: string): string {
  return String(value || "")
    .toLowerCase()
    .replaceAll(/[^a-z0-9]+/g, "-")
    .replaceAll(/^-+|-+$/g, "")
    .slice(0, 48);
}

async function readResponseError(response: Response, fallback: string): Promise<string> {
  try {
    const text = await response.text();
    if (!text) return fallback;
    const parsed = JSON.parse(text);
    return parsed?.error?.message || parsed?.message || fallback;
  } catch {
    return fallback;
  }
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
