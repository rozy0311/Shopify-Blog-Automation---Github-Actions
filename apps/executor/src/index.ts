import "./tracing.js";
import fs from "fs-extra";
import "dotenv/config";
import { readConfig, readQueue, updateBackfill } from "./sheets.js";
import { callOpenAI, validateNoYears } from "./llm.js";
import { publishArticle } from "./shopify.js";
import { withRetry } from "./batch.js";
import { writePreview } from "./preview.js";

interface Summary {
  attempted: number;
  processed: number;
  failed: number;
  errors: Array<{ url: string; error: string }>;
}

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
  const queue = await readQueue(30);
  const summary: Summary = { attempted: queue.length, processed: 0, failed: 0, errors: [] };

  if (!queue.length) {
    await writeSummary(summary);
    console.log("No pending items");
    return;
  }

  const mode = resolveMode();
  const publishEnabled = mode === "publish";
  const blogHandle = config.BLOG_HANDLE || "agritourism";
  const author = config.AUTHOR || "The Rike";
  const model = process.env.OPENAI_MODEL || "gpt-4o-mini";

  for (const row of queue) {
    try {
      const ctrlPrompt = (config.LLM_CONTROL_PROMPT || "").toString();
      if (ctrlPrompt.length < 50 || !ctrlPrompt.includes("{{URL_BLOG}}")) {
        throw new Error("Invalid LLM_CONTROL_PROMPT");
      }

      const systemPrompt = `${ctrlPrompt.replace(/\{\{URL_BLOG\}\}/g, row.url_blog_crawl)}\n\n` +
        "Rules: Return JSON only {title, seo_title, meta_desc, html, images:[{src,alt}]}; HTML Shopify-safe; NO YEARS; up to 4 images.";

      const data = await withRetry(() => callOpenAI(systemPrompt, model));
      validateNoYears(data);

      const preview = await writePreview({
        url_blog_crawl: row.url_blog_crawl,
        blogHandle,
        author,
        content: data,
      });

      if (!publishEnabled) {
        console.log(`[REVIEW] Draft saved: ${preview.htmlPath}`);
        summary.processed += 1;
        continue;
      }

      const article = await publishArticle(blogHandle, author, data);
      const handle = article?.article?.handle;
      if (!handle) throw new Error("Shopify response missing article handle");
      const shop = process.env.SHOPIFY_SHOP;
      if (!shop) throw new Error("Missing SHOPIFY_SHOP env var");
      const url = `https://${shop}.myshopify.com/blogs/${blogHandle}/${handle}`;

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

  await writeSummary(summary);
}

main().catch((error) => {
  console.error("Executor crashed", error);
  process.exitCode = 1;
});
