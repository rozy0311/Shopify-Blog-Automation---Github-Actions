import "./tracing.js";
import fs from "fs-extra";
import "dotenv/config";
import { readConfig, readQueue, updateBackfill } from "./sheets.js";
import { callLLM, callStructuredLLM, generateBatch, type BatchGenerationResult, type BatchJobItem, validateNoYears } from "./llm.js";
import { publishArticle } from "./shopify.js";
import { withRetry } from "./batch.js";
import { writePreview } from "./preview.js";

interface Summary {
  attempted: number;
  processed: number;
  failed: number;
  errors: Array<{ url: string; error: string }>;
}

type QueueRow = Awaited<ReturnType<typeof readQueue>>[number];

type ExecutorContext = {
  publishEnabled: boolean;
  blogHandle: string;
  author: string;
  model: string;
  useBatch: boolean;
  buildSystemPrompt: (url: string) => string;
};

const RULES_SUFFIX =
  "Rules: Return JSON only {title, seo_title, meta_desc, html, images:[{src,alt}]}; HTML Shopify-safe; NO YEARS; up to 4 images; avoid generic filler; include concrete, practical specifics tied to the source URL context; avoid repeated intro templates and vague motivational language.";

type ImageBrief = {
  prompt: string;
  alt: string;
};

function resolveMode() {
  const explicit = process.env.MODE?.toLowerCase();
  if (explicit === "publish" || explicit === "review") return explicit;
  return process.env.WF_ENABLED === "true" ? "publish" : "review";
}

async function writeSummary(summary: Summary) {
  await fs.ensureDir("out");
  await fs.writeJSON("out/summary.json", summary, { spaces: 2 });
  console.log("SUMMARY", JSON.stringify(summary));
}

async function main() {
  const config = await readConfig();
  const queue = await readQueue(parseBatchSize());
  const summary: Summary = { attempted: queue.length, processed: 0, failed: 0, errors: [] };

  if (!queue.length) {
    await writeSummary(summary);
    console.log("No pending items");
    return;
  }

  const context = createContext(config);
  const precomputed = await maybeGenerateBatch(context, queue);
  await processQueue(queue, context, summary, precomputed);
  await writeSummary(summary);
}

function parseBatchSize() {
  const batchSize = Number(process.env.BATCH_SIZE || "30");
  return Number.isFinite(batchSize) && batchSize > 0 ? batchSize : 30;
}

function createContext(config: Record<string, unknown>): ExecutorContext {
  const mode = resolveMode();
  const ctrlPrompt = asString(config.LLM_CONTROL_PROMPT, "");
  if (ctrlPrompt.length < 50 || !ctrlPrompt.includes("{{URL_BLOG}}")) {
    throw new Error("Invalid LLM_CONTROL_PROMPT");
  }

  const blogHandle = asString(config.BLOG_HANDLE, "agritourism");
  const author = asString(config.AUTHOR, "The Rike");
  const model = process.env.OPENAI_MODEL || "gpt-4o-mini";
  const useBatch = process.env.USE_BATCH === "true";

  return {
    publishEnabled: mode === "publish",
    blogHandle,
    author,
    model,
    useBatch,
    buildSystemPrompt: (url: string) => `${ctrlPrompt.replaceAll("{{URL_BLOG}}", url)}\n\n${RULES_SUFFIX}`,
  };
}

async function maybeGenerateBatch(context: ExecutorContext, queue: QueueRow[]): Promise<BatchGenerationResult | null> {
  if (!context.useBatch || !queue.length) return null;
  const jobs: BatchJobItem[] = queue.map((row) => ({
    id: row.url_blog_crawl,
    systemPrompt: context.buildSystemPrompt(row.url_blog_crawl),
  }));
  return withRetry(() => generateBatch(jobs, context.model));
}

async function processQueue(
  queue: QueueRow[],
  context: ExecutorContext,
  summary: Summary,
  precomputed: BatchGenerationResult | null,
) {
  for (const row of queue) {
    try {
      const rawData = await getDraftForRow(row, context, precomputed);
      const data = stripYearTokens(rawData);
      validateNoYears(data);

      const preview = await writePreview({
        url_blog_crawl: row.url_blog_crawl,
        blogHandle: context.blogHandle,
        author: context.author,
        content: data,
      });

      if (!context.publishEnabled) {
        console.log(`[REVIEW] Draft saved: ${preview.htmlPath}`);
        summary.processed += 1;
        continue;
      }

      const imageBrief = await buildImageBrief(row.url_blog_crawl, data, context);
      const article = await publishArticle(context.blogHandle, context.author, data, imageBrief);
      const handle = article?.article?.handle;
      if (!handle) throw new Error("Shopify response missing article handle");
      const shop = process.env.SHOPIFY_SHOP;
      if (!shop) throw new Error("Missing SHOPIFY_SHOP env var");
      const url = `https://${shop}.myshopify.com/blogs/${context.blogHandle}/${handle}`;

      await withRetry(() => updateBackfill(row.url_blog_crawl, url));
      console.log(`Published: ${url}`);
      summary.processed += 1;
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      summary.failed += 1;
      summary.errors.push({ url: row.url_blog_crawl, error: message });
      console.error(`Failed for ${row.url_blog_crawl}:`, message);
    }
  }
}

function stripYearTokens(data: Awaited<ReturnType<typeof callLLM>>) {
  const sanitize = (value: string | undefined) => {
    if (!value) return value;
    return value
      .replaceAll(/\b(19|20)\d{2}\b/g, "")
      .replaceAll(/\s{2,}/g, " ")
      .trim();
  };

  return {
    ...data,
    title: sanitize(data.title) || data.title,
    seo_title: sanitize(data.seo_title),
    meta_desc: sanitize(data.meta_desc),
    html: sanitize(data.html) || data.html,
  };
}

async function getDraftForRow(
  row: QueueRow,
  context: ExecutorContext,
  precomputed: BatchGenerationResult | null,
): Promise<Awaited<ReturnType<typeof callLLM>>> {
  const systemPrompt = context.buildSystemPrompt(row.url_blog_crawl);
  if (!precomputed) {
    return withRetry(() => callLLM(systemPrompt, context.model));
  }
  const precomputedError = precomputed.errors[row.url_blog_crawl];
  if (precomputedError) {
    throw new Error(precomputedError);
  }
  const draft = precomputed.outputs[row.url_blog_crawl];
  if (!draft) {
    throw new Error("Batch output missing for row");
  }
  return draft;
}

async function buildImageBrief(
  sourceUrl: string,
  data: Awaited<ReturnType<typeof callLLM>>,
  context: ExecutorContext,
): Promise<ImageBrief | undefined> {
  const plainHtml = (data.html || "")
    .replaceAll(/<[^>]+>/g, " ")
    .replaceAll(/\s{2,}/g, " ")
    .trim()
    .slice(0, 1200);

  const systemPrompt = [
    "You are a senior visual editor for realistic editorial photography.",
    "Return JSON only with schema: {\"prompt\": string, \"alt\": string}.",
    "Prompt must be concrete, non-generic, and visually grounded in the article context.",
    "Style: realistic documentary photo, natural light, no text overlay, no logos, no fantasy art.",
  ].join(" ");

  const userPrompt = [
    `SOURCE_URL: ${sourceUrl}`,
    `TITLE: ${data.title}`,
    `SEO_TITLE: ${data.seo_title || ""}`,
    `SUMMARY_TEXT: ${plainHtml}`,
    "Create one realistic hero-image prompt and one concise descriptive alt text.",
  ].join("\n");

  try {
    const brief = await withRetry(() => callStructuredLLM<ImageBrief>(systemPrompt, context.model, userPrompt));
    if (!brief?.prompt?.trim() || !brief?.alt?.trim()) return undefined;
    return {
      prompt: brief.prompt.trim(),
      alt: brief.alt.trim(),
    };
  } catch {
    return undefined;
  }
}

function asString(value: unknown, fallback: string): string {
  if (typeof value === "string") return value;
  if (typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }
  return fallback;
}

try {
  await main();
} catch (error) {
  console.error("Executor crashed", error);
  process.exitCode = 1;
}
