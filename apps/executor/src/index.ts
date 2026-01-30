import "./tracing.js";
import fs from "fs-extra";
import "dotenv/config";
import { readConfig, readQueue, updateBackfill } from "./sheets.js";
import { callLLM, generateBatch, type BatchGenerationResult, type BatchJobItem, validateNoYears } from "./llm.js";
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
  "Rules: Return JSON only {title, seo_title, meta_desc, html, images:[{src,alt}]}; HTML Shopify-safe; NO YEARS; up to 4 images.";

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
      const data = await getDraftForRow(row, context, precomputed);
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

      const article = await publishArticle(context.blogHandle, context.author, data);
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
