import "./tracing.js";
import fs from "fs-extra";
import "dotenv/config";
import path from "node:path";
import { spawn } from "node:child_process";
import { readConfig, readQueue, updateBackfill } from "./sheets.js";
import { callLLM, callStructuredLLM, generateBatch, type BatchGenerationResult, type BatchJobItem, validateNoYears } from "./llm.js";
import { generateHostedGeminiImages, publishArticle } from "./shopify-client.js";
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

const RULES_SUFFIX = [
  "WORD COUNT IS THE #1 PRIORITY: You MUST write 1400-2500 words of text content in the html field. Each H2 section MUST have 150-300 words. Short articles WILL BE REJECTED. Count your words carefully.",
  "Rules: Return JSON only {title, seo_title, meta_desc, html, images:[{src,alt}]}.",
  "TITLE: ≤70 chars, primary keyword in first 10 chars. SEO_TITLE: ≤60 chars. META_DESC: ≤155 chars.",
  "HTML must be Shopify-safe. STRICT NO YEARS: never output any 4-digit year (19xx/20xx).",
  "STRUCTURE: Include these H2 sections with exact kebab-case ids: key-conditions, background, framework, troubleshooting, expert-tips, faq, key-terms, sources. Minimum 6 H2 tags.",
  "DIRECT ANSWER: First 50-70 words must directly answer the query. Primary keyword within first 120 characters.",
  "CITATIONS: ≥5 external links to authoritative sources (.gov/.edu/journals). Every <a> must use absolute HTTPS and rel=\"nofollow noopener\".",
  "SOURCES DEPTH: In the #sources section, include 8-12 source links total when possible, each with organization/site name and why it supports the claim.",
  "EVIDENCE TOKENS: Include claim registry markers in the article body for key evidence, e.g. [EVID:STAT_1], [EVID:QUOTE_1]. Minimum: 3 stat tokens and 2 quote tokens.",
  "EXPERT QUOTES: ≥2 <blockquote> tags with real expert name + title + organization.",
  "STATISTICS: ≥3 quantified stats with named sources.",
  "FAQ SECTION: 5-7 <h3> questions under the #faq section, each answer 50-80 words.",
  "KEY TERMS: 5-8 terms defined under the #key-terms section, each wrapped in <dfn> or <dt>/<dd>.",
  "IMAGES HARD RULE: Exactly 3 inline <img> inside html body, each with meaningful alt text (80-140 chars, literal description, no marketing).",
  "FEATURED IMAGE HARD RULE: Exactly 1 featured image in images[0] with non-empty src and alt. Do not return multiple featured images.",
  "IMAGE PROMPT RULES: photorealistic, 50mm lens, f/2.8, ISO 200, 1/125s, natural window light, shallow depth of field, high resolution, ultra-detailed.",
  "IMAGE BANS: no people, no hands, no faces, no logos, no text, no watermarks.",
  "BANNED: no sales CTAs (shop now/buy/add to cart/limited time), no clickbait, no keyword stuffing.",
  "VOICE: cozy-authority tone — practical, warm, sensory micro-moments. Avoid generic filler and repeated intro templates.",
  "Every claim/stat/quote MUST reference a fetched source. No-fetch-no-claim.",
  "FINAL REMINDER: The article MUST be 1400-2500 words. Write detailed, expansive paragraphs. Do NOT be concise."
].join(" ");

const MIN_INLINE_IMAGES = Number(process.env.MIN_INLINE_IMAGES || "3");
const MIN_ARTICLE_WORDS = Number(process.env.MIN_ARTICLE_WORDS || "1400");
const MAX_ARTICLE_WORDS = Number(process.env.MAX_ARTICLE_WORDS || "2500");
const MIN_H2_COUNT = Number(process.env.MIN_H2_COUNT || "6");
const MIN_EXTERNAL_LINKS = Number(process.env.MIN_EXTERNAL_LINKS || "5");
const MIN_BLOCKQUOTES = Number(process.env.MIN_BLOCKQUOTES || "2");
const TITLE_MAX_LENGTH = Number(process.env.TITLE_MAX_LENGTH || "70");
const SEO_TITLE_MAX_LENGTH = Number(process.env.SEO_TITLE_MAX_LENGTH || "60");
const META_DESC_MAX_LENGTH = Number(process.env.META_DESC_MAX_LENGTH || "155");
const MIN_FAQ_QUESTIONS = Number(process.env.MIN_FAQ_QUESTIONS || "5");
const MAX_FAQ_QUESTIONS = Number(process.env.MAX_FAQ_QUESTIONS || "7");
const MIN_KEY_TERMS = Number(process.env.MIN_KEY_TERMS || "5");
const MIN_AUTHORITATIVE_LINKS = Number(process.env.MIN_AUTHORITATIVE_LINKS || "3");
const TARGET_FEATURED_IMAGES = 1;
const MIN_EVID_STAT_TOKENS = Number(process.env.MIN_EVID_STAT_TOKENS || "3");
const MIN_EVID_QUOTE_TOKENS = Number(process.env.MIN_EVID_QUOTE_TOKENS || "2");

const AUTHORITATIVE_DOMAINS = [".gov", ".edu", "ncbi.nlm.nih", "sciencedirect", "nature.com", "wiley.com", "springer.com", "pubmed"];

function countWords(html: string): number {
  const textOnly = html.replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim();
  return textOnly ? textOnly.split(" ").length : 0;
}

const INITIAL_USER_PROMPT = [
  `CRITICAL: Your html field MUST contain at least ${Number(process.env.MIN_ARTICLE_WORDS || "1400")} words of text content.`,
  "Write comprehensive paragraphs (4-6 sentences each) for EVERY H2 section.",
  "Each section should have 150-300 words with concrete details, examples, and analysis.",
  "Return only a single minified JSON object. No markdown, no code fences, no commentary.",
].join(" ");

const REQUIRED_SECTION_IDS = [
  "key-conditions",
  "background",
  "framework",
  "troubleshooting",
  "expert-tips",
  "faq",
  "key-terms",
  "sources",
];

const BANNED_CTA_PHRASES = ["shop now", "buy", "add to cart", "limited time"];

const MAX_QUALITY_RETRIES = Number(process.env.MAX_QUALITY_RETRIES || "4");

type ImageBrief = {
  prompt: string;
  alt: string;
};

type ChatgptUiImageResult = {
  images?: string[];
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
  const strictChatgpt = isStrictChatgptRequired();

  if (!queue.length) {
    await writeSummary(summary);
    console.log("No pending items");
    return;
  }

  const context = createContext(config);
  const precomputed = await maybeGenerateBatch(context, queue);
  try {
    await processQueue(queue, context, summary, precomputed, strictChatgpt);
  } finally {
    await writeSummary(summary);
  }
}

function isStrictChatgptRequired() {
  const required = (process.env.CHATGPT_UI_REQUIRED || "").trim().toLowerCase() === "true";
  const order = (process.env.LLM_PROVIDER_ORDER || "").toLowerCase();
  return required && order.includes("chatgpt_ui");
}

function parseBatchSize() {
  const batchSize = Number(process.env.MAX_ITEMS || process.env.BATCH_SIZE || "30");
  return Number.isFinite(batchSize) && batchSize > 0 ? batchSize : 30;
}

function createContext(config: Record<string, unknown>): ExecutorContext {
  const mode = resolveMode();
  const ctrlPrompt = asString(config.LLM_CONTROL_PROMPT, "");
  const isDiscoverMode = process.env.DISCOVER_MODE === "true";

  if (!isDiscoverMode && (ctrlPrompt.length < 50 || !ctrlPrompt.includes("{{URL_BLOG}}"))) {
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
    buildSystemPrompt: (urlOrTopic: string) => {
      if (urlOrTopic.startsWith("topic://")) {
        const topic = urlOrTopic.slice("topic://".length);
        return buildTopicSystemPrompt(topic);
      }
      return `${ctrlPrompt.replaceAll("{{URL_BLOG}}", urlOrTopic)}\n\n${RULES_SUFFIX}`;
    },
  };
}

function buildTopicSystemPrompt(topic: string): string {
  return [
    "You are a senior botanical wellness editor for The Rike (therike.com), a premium organic herbal products store.",
    `Write a comprehensive, authoritative blog article about: "${topic}".`,
    "",
    "CONTEXT: The Rike specializes in organic herbal teas, seeds, superfoods, and traditional remedies.",
    "The blog (Agritourism) covers wellness, sustainable agriculture, herbal medicine, and mindful living.",
    "",
    "WRITING APPROACH:",
    "- Write from deep expertise in herbalism, botany, and wellness.",
    "- Include real scientific names, traditional uses, and modern research.",
    "- Reference authoritative sources (.gov, .edu, PubMed, USDA, WHO).",
    "- Use concrete examples, sensory descriptions, and practical growing tips.",
    "- Address the reader as a mindful wellness enthusiast or home grower.",
    "- Do NOT mention any product prices, store URLs, or commercial offers.",
    "",
    RULES_SUFFIX,
  ].join("\n");
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
  strictChatgpt: boolean,
) {
  for (const row of queue) {
    try {
      await processQueueRow(row, context, precomputed);
      summary.processed += 1;
    } catch (error) {
      handleQueueRowError(error, row, summary, strictChatgpt);
    }
  }
}

async function processQueueRow(
  row: QueueRow,
  context: ExecutorContext,
  precomputed: BatchGenerationResult | null,
) {
  const data = await generateWithQualityRetry(row, context, precomputed);
  data.images = normalizeFeaturedImages(data.images);

  const preferExisting = (process.env.PREFER_EXISTING_INLINE_IMAGES || "true").toLowerCase() !== "false";
  const existingInline = preferExisting ? extractExistingInlineImageTags(data.html || "") : [];
  const hasEnoughExistingInline = existingInline.length >= TARGET_INLINE_IMAGES;

  // Generate LLM-directed image prompts, then inject into HTML
  const inlineBriefs = await generateInlineImageBriefs(data.html || "", data.title || "", context.model);
  const directUiImageUrls = hasEnoughExistingInline
    ? []
    : await generateInlineImagesViaChatgptUi(inlineBriefs, data.title || "");
  const geminiFallbackImageUrls = hasEnoughExistingInline || directUiImageUrls.length >= TARGET_INLINE_IMAGES
    ? []
    : await generateHostedGeminiImages(
      inlineBriefs.slice(directUiImageUrls.length, TARGET_INLINE_IMAGES),
      data.title || "",
    );
  const resolvedInlineImageUrls = [...directUiImageUrls, ...geminiFallbackImageUrls].slice(0, TARGET_INLINE_IMAGES);
  data.html = injectInlineImages(data.html || "", inlineBriefs, resolvedInlineImageUrls);
  const postInjectInline = extractExistingInlineImageTags(data.html || "");

  if (!hasEnoughExistingInline && directUiImageUrls.length < TARGET_INLINE_IMAGES) {
    console.warn(
      `[IMAGE_UI] Partial/missing ChatGPT UI images (${directUiImageUrls.length}/${TARGET_INLINE_IMAGES}); Gemini hosted fallback filled ${geminiFallbackImageUrls.length}.`,
    );
  }

  if (resolvedInlineImageUrls.length > 0) {
    data.images = [
      {
        src: resolvedInlineImageUrls[0],
        alt: (inlineBriefs[0]?.alt || data.title || "featured image").trim(),
      },
    ];
  } else if ((!Array.isArray(data.images) || !data.images[0]?.src?.trim()) && existingInline.length > 0) {
    const firstSrc = extractFirstImageSrc(existingInline[0]);
    if (firstSrc) {
      data.images = [
        {
          src: firstSrc,
          alt: (inlineBriefs[0]?.alt || data.title || "featured image").trim(),
        },
      ];
    }
  } else if ((!Array.isArray(data.images) || !data.images[0]?.src?.trim()) && postInjectInline.length > 0) {
    const firstSrc = extractFirstImageSrc(postInjectInline[0]);
    if (firstSrc) {
      data.images = [
        {
          src: firstSrc,
          alt: (inlineBriefs[0]?.alt || data.title || "featured image").trim(),
        },
      ];
      console.log("[IMAGE_UI] Featured image recovered from post-injection inline fallback");
    }
  }

  if (postInjectInline.length < TARGET_INLINE_IMAGES) {
    throw new Error(`Image pipeline exhausted before publish: only ${postInjectInline.length}/${TARGET_INLINE_IMAGES} inline images available`);
  }

  if (!Array.isArray(data.images) || !data.images[0]?.src?.trim()) {
    throw new Error("Image pipeline exhausted before publish: missing featured image");
  }

  const preview = await writePreview({
    url_blog_crawl: row.url_blog_crawl,
    blogHandle: context.blogHandle,
    author: context.author,
    content: data,
  });

  if (!context.publishEnabled) {
    console.log(`[REVIEW] Draft saved: ${preview.htmlPath}`);
    return;
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
}

function handleQueueRowError(error: unknown, row: QueueRow, summary: Summary, strictChatgpt: boolean) {
  const message = error instanceof Error ? error.message : String(error);
  summary.failed += 1;
  summary.errors.push({ url: row.url_blog_crawl, error: message });
  console.error(`Failed for ${row.url_blog_crawl}:`, message);
  if (strictChatgpt && message.toLowerCase().includes("chatgpt_ui required")) {
    throw new Error(message);
  }
}

async function generateWithQualityRetry(
  row: QueueRow,
  context: ExecutorContext,
  precomputed: BatchGenerationResult | null,
): Promise<Awaited<ReturnType<typeof callLLM>>> {
  // First attempt uses precomputed batch or normal LLM call
  const rawData = await getDraftForRow(row, context, precomputed);
  const data = stripYearTokens(rawData);
  validateNoYears(data);

  let lastData = data;
  let lastError: string | undefined;

  try {
    validateDraftQuality(lastData);
    return lastData;
  } catch (error) {
    lastError = error instanceof Error ? error.message : String(error);
    console.warn(`[QUALITY_GUARD] FAIL attempt 1/${MAX_QUALITY_RETRIES + 1}: ${lastError}`);
  }

  // Retry with feedback — always a fresh LLM call (not precomputed)
  for (let attempt = 2; attempt <= MAX_QUALITY_RETRIES + 1; attempt++) {
    const correctionPrompt = buildCorrectionPrompt(context, row.url_blog_crawl, lastData, lastError as string);
    const currentWordCount = countWords(lastData.html || "");
    const correctionUserPrompt = [
      `URGENT: Your previous article was only ${currentWordCount} words. The MINIMUM is ${MIN_ARTICLE_WORDS} words.`,
      `You MUST write at least ${MIN_ARTICLE_WORDS} words of text content in the html field.`,
      "Write MUCH longer paragraphs (4-6 sentences each). Each H2 section needs 150-300 words.",
      "Expand with more concrete details, real-world examples, expert insights, and practical advice.",
      "Return only a single minified JSON object. No markdown, no code fences, no commentary.",
    ].join(" ");
    const retryRaw = await withRetry(() => callLLM(correctionPrompt, context.model, correctionUserPrompt));
    const retryData = stripYearTokens(retryRaw);
    validateNoYears(retryData);
    lastData = retryData;

    try {
      validateDraftQuality(lastData);
      console.log(`[QUALITY_GUARD] PASS on retry attempt ${attempt}/${MAX_QUALITY_RETRIES + 1}`);
      return lastData;
    } catch (error) {
      lastError = error instanceof Error ? error.message : String(error);
      console.warn(`[QUALITY_GUARD] FAIL attempt ${attempt}/${MAX_QUALITY_RETRIES + 1}: ${lastError}`);
    }
  }

  // All retries exhausted — throw the last quality gate error
  throw new Error(lastError as string);
}

function buildCorrectionPrompt(
  context: ExecutorContext,
  url: string,
  previousData: Awaited<ReturnType<typeof callLLM>>,
  qualityErrors: string,
): string {
  const base = context.buildSystemPrompt(url);
  const prevWordCount = countWords(previousData.html || "");
  const feedback = [
    "\n\n--- CORRECTION REQUIRED ---",
    `Your previous output was REJECTED. Errors: ${qualityErrors}`,
    "",
    `*** WORD COUNT IS THE #1 ISSUE: Your previous article was only ${prevWordCount} words. MINIMUM is ${MIN_ARTICLE_WORDS} words. ***`,
    `You MUST write at least ${MIN_ARTICLE_WORDS} words. Write 150-300 words per H2 section. Use detailed paragraphs with 4-6 sentences each.`,
    "",
    "Fix ALL issues simultaneously:",
    "1. WORD COUNT: Write at least " + MIN_ARTICLE_WORDS + " words total in the html body. This is NON-NEGOTIABLE.",
    "2. H2 sections with exact ids: key-conditions, background, framework, troubleshooting, expert-tips, faq, key-terms, sources",
    "3. ≥5 external links with rel=\"nofollow noopener\", ≥3 to .gov/.edu/journals",
    "4. ≥2 <blockquote> with expert name + title",
    "5. FAQ: 5-7 <h3> questions under <h2 id=\"faq\">",
    "6. Key terms: 5-8 under <h2 id=\"key-terms\"> using <dfn> or <dt>/<dd>",
    "7. seo_title ≤ 60 chars, meta_desc ≤ 160 chars",
    "8. No banned CTAs (buy now/shop now/order today/limited time/add to cart)",
    "9. Images hard rule: exactly 3 inline images in html body and exactly 1 featured image in images[0]",
    "10. Add evidence markers: >=3 [EVID:STAT_n] and >=2 [EVID:QUOTE_n]",
    "11. Strengthen #sources with authoritative links (.gov/.edu/journal) and clear relevance",
    "",
    `Previous title: ${previousData.title}`,
    "Generate a COMPLETE, LONG, DETAILED article. Return JSON only.",
  ].join("\n");

  return base + feedback;
}

const TARGET_INLINE_IMAGES = 3;

function normalizeFeaturedImages(images: Array<{ src: string; alt?: string }> | undefined) {
  if (!Array.isArray(images) || images.length === 0) return [];
  const first = images[0];
  return [
    {
      src: (first?.src || "").trim(),
      alt: (first?.alt || "").trim(),
    },
  ];
}

function normalizeInlineBriefs(
  briefs: Array<{ prompt: string; alt: string }>,
  fallbackSections: string[],
): Array<{ prompt: string; alt: string }> {
  const base = briefs
    .map((b) => ({
      prompt: (b.prompt || "").trim(),
      alt: (b.alt || "").trim().slice(0, 140),
    }))
    .filter((b) => b.prompt.length > 0 && b.alt.length > 0)
    .slice(0, TARGET_INLINE_IMAGES);

  let i = 0;
  while (base.length < TARGET_INLINE_IMAGES) {
    const section = fallbackSections[i % fallbackSections.length] || "article section";
    base.push({
      prompt: `${section}, realistic editorial photography, natural soft light, shallow depth-of-field`,
      alt: `${section} - editorial photograph`.slice(0, 140),
    });
    i++;
  }
  return base;
}

function stripInlineImageTags(html: string): string {
  return html
    .replace(/<figure\b[^>]*>[\s\S]*?<img\b[^>]*>[\s\S]*?<\/figure>/gi, "")
    .replace(/<img\b[^>]*>/gi, "");
}

function extractFirstImageSrc(tagOrHtml: string): string | undefined {
  const m = String(tagOrHtml || "").match(/<img\b[^>]*\bsrc\s*=\s*"([^"]+)"/i);
  return m?.[1]?.trim();
}

function extractExistingInlineImageTags(html: string): string[] {
  const results: string[] = [];
  const seen = new Set<string>();

  const figureMatches = html.match(/<figure\b[^>]*>[\s\S]*?<img\b[^>]*>[\s\S]*?<\/figure>/gi) || [];
  for (const tag of figureMatches) {
    const trimmed = tag.trim();
    if (trimmed && !seen.has(trimmed)) {
      seen.add(trimmed);
      results.push(trimmed);
    }
  }

  const imgMatches = html.match(/<img\b[^>]*>/gi) || [];
  for (const tag of imgMatches) {
    const trimmed = tag.trim();
    if (trimmed && !seen.has(trimmed)) {
      seen.add(trimmed);
      results.push(`<figure>${trimmed}</figure>`);
    }
  }

  return results;
}

function escapeHtmlAttr(s: string): string {
  return s.replaceAll("&", "&amp;").replaceAll('"', "&quot;").replaceAll("<", "&lt;").replaceAll(">", "&gt;");
}

function escapeHtml(s: string): string {
  return s.replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;");
}

/**
 * Use the LLM to generate specific, contextual image prompts for each inline
 * image placement. Falls back to keyword-based prompts on failure.
 */
async function generateInlineImageBriefs(
  html: string,
  title: string,
  model: string,
): Promise<Array<{ prompt: string; alt: string }>> {
  const headingMatches = [...html.matchAll(/<h2\b[^>]*>([\s\S]*?)<\/h2>/gi)];
  const headings = headingMatches
    .map((m) => m[1].replaceAll(/<[^>]+>/g, "").trim())
    .filter((h) => h.length > 2);

  const sections = headings.slice(1); // skip first (intro)
  const targetSections = sections.length > 0 ? [...sections] : [title];
  while (targetSections.length < TARGET_INLINE_IMAGES) {
    targetSections.push(targetSections[targetSections.length - 1] || title);
  }

  const count = TARGET_INLINE_IMAGES;

  const systemPrompt = [
    "You are a senior visual editor for realistic editorial photography.",
    `Return a JSON array of exactly ${count} objects: [{"prompt": "...", "alt": "..."}].`,
    "Each prompt: concrete, specific to the section topic, 15-30 words describing a real photograph.",
    "Style direction: realistic documentary/editorial photo, soft natural light, shallow depth-of-field, muted earth tones.",
    "NEVER include text overlays, logos, watermarks, or fantasy/artistic elements in the prompt.",
    "Each alt: 80-140 characters, literal visual description of what the image shows. No marketing language.",
    "Return JSON only. No markdown, no code fences, no commentary.",
  ].join(" ");

  const userPrompt = [
    `ARTICLE TITLE: ${title}`,
    "",
    "SECTIONS NEEDING IMAGES:",
    ...targetSections.slice(0, TARGET_INLINE_IMAGES).map((s, i) => `${i + 1}. ${s}`),
    "",
    `Generate ${count} realistic photo descriptions.`,
  ].join("\n");

  try {
    const briefs = await withRetry(() =>
      callStructuredLLM<Array<{ prompt: string; alt: string }>>(systemPrompt, model, userPrompt),
    );
    if (Array.isArray(briefs) && briefs.length > 0) {
      const normalized = normalizeInlineBriefs(briefs, targetSections);
      console.log(`[IMAGE_BRIEF] LLM generated ${briefs.length} prompts, normalized to ${normalized.length}`);
      return normalized;
    }
  } catch (err) {
    console.warn("[IMAGE_BRIEF] LLM fallback:", err instanceof Error ? err.message : err);
  }

  // Fallback: keyword-based prompts
  return normalizeInlineBriefs([], targetSections);
}

/**
 * Inject inline images into article HTML using Pollinations AI image generation.
 * Accepts pre-generated image briefs (from LLM) for contextual, high-quality prompts.
 */
function injectInlineImages(
  html: string,
  briefs: Array<{ prompt: string; alt: string }>,
  directUiImageUrls: string[] = [],
): string {
  const preferExisting = (process.env.PREFER_EXISTING_INLINE_IMAGES || "true").toLowerCase() !== "false";
  const existingInline = preferExisting ? extractExistingInlineImageTags(html).slice(0, TARGET_INLINE_IMAGES) : [];
  const cleanedHtml = stripInlineImageTags(html);
  const normalizedBriefs = normalizeInlineBriefs(briefs, ["article section"]);
  const needed = TARGET_INLINE_IMAGES;

  const imageTags: string[] = [];
  for (const tag of existingInline) {
    imageTags.push(tag);
  }

  for (let i = imageTags.length; i < needed && i < directUiImageUrls.length; i++) {
    const brief = normalizedBriefs[i];
    const src = String(directUiImageUrls[i] || "").trim();
    if (!src) continue;
    const safeAlt = escapeHtmlAttr(brief.alt);
    imageTags.push(
      `<figure><img src="${escapeHtmlAttr(src)}" alt="${safeAlt}" loading="lazy" width="800" height="450"><figcaption>${escapeHtml(brief.alt)}</figcaption></figure>`,
    );
  }

  // Prefer natural interleaving after paragraph closes at ~22%, ~52%, ~80% of article depth.
  const parts = cleanedHtml.split(/(<\/p>)/i);
  const paragraphCloseIndexes: number[] = [];
  for (let i = 0; i < parts.length; i++) {
    if (/^<\/p>$/i.test(parts[i])) paragraphCloseIndexes.push(i);
  }

  if (paragraphCloseIndexes.length === 0) {
    const result = `${cleanedHtml}\n${imageTags.join("\n")}\n`;
    console.log(
      `[IMAGE_INJECT] Enforced ${imageTags.length}/${TARGET_INLINE_IMAGES} inline images (existing=${existingInline.length}, fallback=${Math.max(0, imageTags.length - existingInline.length)})`,
    );
    return result;
  }

  const targetInsertions = [0.22, 0.52, 0.8].map((ratio) =>
    paragraphCloseIndexes[
      Math.min(paragraphCloseIndexes.length - 1, Math.floor(paragraphCloseIndexes.length * ratio))
    ],
  );

  const uniqueInsertions: number[] = [];
  for (const insertion of targetInsertions) {
    if (!uniqueInsertions.includes(insertion)) uniqueInsertions.push(insertion);
  }

  let backfill = paragraphCloseIndexes.length - 1;
  while (uniqueInsertions.length < needed && backfill >= 0) {
    const candidate = paragraphCloseIndexes[backfill];
    if (!uniqueInsertions.includes(candidate)) uniqueInsertions.push(candidate);
    backfill--;
  }

  const insertionMap = new Map<number, string>();
  for (let i = 0; i < needed && i < uniqueInsertions.length; i++) {
    insertionMap.set(uniqueInsertions[i], `\n${imageTags[i]}\n`);
  }

  const rebuilt: string[] = [];
  for (let i = 0; i < parts.length; i++) {
    rebuilt.push(parts[i]);
    if (insertionMap.has(i)) {
      rebuilt.push(insertionMap.get(i) as string);
    }
  }

  const result = rebuilt.join("");
  console.log(
    `[IMAGE_INJECT] Enforced ${imageTags.length}/${TARGET_INLINE_IMAGES} inline images (existing=${existingInline.length}, fallback=${Math.max(0, imageTags.length - existingInline.length)})`,
  );
  return result;
}

async function generateInlineImagesViaChatgptUi(
  briefs: Array<{ prompt: string; alt: string }>,
  title: string,
): Promise<string[]> {
  const enabled = (process.env.CHATGPT_UI_IMAGE_DIRECT || "false").trim().toLowerCase() === "true";
  if (!enabled) return [];

  const scriptPath = (
    process.env.CHATGPT_UI_NODE_SCRIPT ||
    path.join("ui-automation", "scripts", "chatgpt_ui.mjs")
  ).trim();

  if (!scriptPath || !(await fs.pathExists(scriptPath))) {
    console.warn(`[IMAGE_UI] Missing ChatGPT UI script at ${scriptPath}`);
    return [];
  }

  const urls: string[] = [];
  for (const [index, brief] of briefs.slice(0, TARGET_INLINE_IMAGES).entries()) {
    const prompt = [
      `Create one photorealistic editorial image for this blog section titled: "${title}".`,
      `Scene brief: ${brief.prompt}`,
      "No text, no logos, no watermark, no people faces.",
      "Return image only.",
    ].join("\n");

    try {
      const result = await runChatgptUiImage(scriptPath, prompt);
      const candidate = result.images?.find((url) => /^https?:\/\//i.test(String(url || "")));
      if (candidate) {
        urls.push(candidate);
        console.log(`[IMAGE_UI] Generated image ${index + 1}/${TARGET_INLINE_IMAGES}`);
      }
    } catch (error) {
      console.warn(`[IMAGE_UI] Failed image ${index + 1}:`, error instanceof Error ? error.message : error);
    }
  }

  return urls.slice(0, TARGET_INLINE_IMAGES);
}

async function runChatgptUiImage(scriptPath: string, prompt: string): Promise<ChatgptUiImageResult> {
  const timeoutMsRaw = Number(process.env.CHATGPT_UI_IMAGE_TIMEOUT_MS || process.env.CHATGPT_UI_TIMEOUT_MS || "240000");
  const timeoutMs = Number.isFinite(timeoutMsRaw) ? Math.max(60000, Math.min(900000, timeoutMsRaw)) : 240000;
  const imageModelLabel = (process.env.CHATGPT_UI_IMAGE_MODEL_LABEL || process.env.CHATGPT_UI_MODEL_LABEL || "5.4").trim();
  const imageStrictModel = (process.env.CHATGPT_UI_IMAGE_STRICT_MODEL || "false").trim().toLowerCase();

  return await new Promise((resolve, reject) => {
    const child = spawn("node", [scriptPath], {
      env: {
        ...process.env,
        CHATGPT_UI_MODE: "image",
        CHATGPT_UI_MODEL_LABEL: imageModelLabel,
        CHATGPT_UI_STRICT_MODEL: imageStrictModel,
      },
      stdio: ["pipe", "pipe", "pipe"],
    });

    let stdout = "";
    let stderr = "";
    let settled = false;

    const timer = setTimeout(() => {
      if (settled) return;
      settled = true;
      child.kill("SIGTERM");
      reject(new Error("chatgpt_ui image request timed out"));
    }, timeoutMs);

    child.stdout.setEncoding("utf8");
    child.stderr.setEncoding("utf8");
    child.stdout.on("data", (chunk) => {
      stdout += String(chunk || "");
    });
    child.stderr.on("data", (chunk) => {
      stderr += String(chunk || "");
    });

    child.on("error", (error) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      reject(error);
    });

    child.on("close", (code) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);

      if (code !== 0) {
        const message = stderr.trim() || `chatgpt_ui image failed (exit ${code ?? -1})`;
        reject(new Error(message));
        return;
      }

      const text = stdout.trim();
      if (!text) {
        reject(new Error("chatgpt_ui image returned empty output"));
        return;
      }

      try {
        resolve(JSON.parse(text) as ChatgptUiImageResult);
      } catch {
        reject(new Error(`chatgpt_ui image returned non-JSON: ${text.slice(0, 240)}`));
      }
    });

    child.stdin.write(prompt);
    child.stdin.end();
  });
}

function stripYearTokens(data: Awaited<ReturnType<typeof callLLM>>) {
  const normalizeInlineMarkdown = (value: string | undefined) => {
    if (!value || !value.includes("*")) return value;
    return value
      .replace(/\*\*\*\s*([^*][\s\S]*?)\s*\*\*\*/g, "<strong>$1</strong>")
      .replace(/\*\*\s*([^*][\s\S]*?)\s*\*\*/g, "<strong>$1</strong>")
      .replace(/(^|[^*])\*\s*([^*][\s\S]*?)\s*\*(?!\*)/g, "$1<em>$2</em>");
  };

  const sanitize = (value: string | undefined) => {
    if (!value) return value;
    const normalized = normalizeInlineMarkdown(value) || value;
    return normalized
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

function collectDraftQualityErrors(data: Awaited<ReturnType<typeof callLLM>>): string[] {
  const html = data.html || "";
  const htmlLower = html.toLowerCase();
  const errors: string[] = [];
  const checks = [
    () => checkTitleAndMetaLengths(data),
    () => checkStructureRequirements(html),
    () => checkLinkRequirements(html),
    () => checkSourcesSectionRequirements(html),
    () => checkEvidenceRegistryTokens(html),
    () => checkAuthoritativeSources(html),
    () => checkInlineImageRequirements(html),
    () => checkFeaturedImageRequirement(data),
    () => checkLengthAndQuoteRequirements(html),
    () => checkFaqSection(html),
    () => checkKeyTermsSection(html),
    () => checkBannedCtas(htmlLower),
  ];
  for (const check of checks) {
    try {
      check();
    } catch (error) {
      errors.push(error instanceof Error ? error.message : String(error));
    }
  }
  return errors;
}

function validateDraftQuality(data: Awaited<ReturnType<typeof callLLM>>) {
  const errors = collectDraftQualityErrors(data);
  if (errors.length > 0) {
    throw new Error(errors.join(" | "));
  }

  const html = data.html || "";
  // Log pass summary for observability
  const textOnly = html.replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim();
  const wc = textOnly ? textOnly.split(" ").length : 0;
  const h2 = (html.match(/<h2\b[^>]*>/gi) || []).length;
  const links = (html.match(/<a\b[^>]*href\s*=\s*"https?:\/\//gi) || []).length;
  const imgs = (html.match(/<img\b[^>]*>/gi) || []).length;
  const bq = (html.match(/<blockquote\b[^>]*>/gi) || []).length;
  console.log(`[QUALITY_GUARD] PASS — title:${(data.title || "").length}c h2:${h2} links:${links} imgs:${imgs} words:${wc} bq:${bq}`);
}

function checkStructureRequirements(html: string) {
  const h2Count = (html.match(/<h2\b[^>]*>/gi) || []).length;
  if (h2Count < MIN_H2_COUNT) {
    throw new Error(`QUALITY_GUARD: h2 count too low (${h2Count}/${MIN_H2_COUNT})`);
  }

  for (const sectionId of REQUIRED_SECTION_IDS) {
    if (!new RegExp(`id\\s*=\\s*"${sectionId}"`, "i").test(html)) {
      throw new Error(`QUALITY_GUARD: missing required section id (${sectionId})`);
    }
  }
}

function checkLinkRequirements(html: string) {
  const externalLinks = (html.match(/<a\b[^>]*href\s*=\s*"https?:\/\//gi) || []).length;
  if (externalLinks < MIN_EXTERNAL_LINKS) {
    throw new Error(`QUALITY_GUARD: external links too low (${externalLinks}/${MIN_EXTERNAL_LINKS})`);
  }

  const invalidLink = /<a\b[^>]*href\s*=\s*"(?!https:\/\/)[^"]+"/i.test(html);
  if (invalidLink) {
    throw new Error("QUALITY_GUARD: found non-HTTPS/relative link");
  }

  const missingRel = /<a\b[^>]*href\s*=\s*"https:\/\/[^"]+"(?![^>]*\brel\s*=\s*"[^"]*nofollow noopener[^"]*")[^>]*>/i.test(html);
  if (missingRel) {
    throw new Error("QUALITY_GUARD: external links must include rel=\"nofollow noopener\"");
  }
}

function checkInlineImageRequirements(html: string) {
  const imgTags = html.match(/<img\b[^>]*>/gi) || [];
  if (imgTags.length !== TARGET_INLINE_IMAGES) {
    throw new Error(`QUALITY_GUARD: inline images must be exactly ${TARGET_INLINE_IMAGES} (got ${imgTags.length})`);
  }

  const missingAlt = imgTags.filter((tag) => !/\balt\s*=\s*"[^"\n]*\S[^"\n]*"/i.test(tag));
  if (missingAlt.length > 0) {
    throw new Error(`QUALITY_GUARD: inline image alt missing (${missingAlt.length})`);
  }
}

function checkSourcesSectionRequirements(html: string) {
  const sourcesMatch = html.match(/<h2\b[^>]*id\s*=\s*"sources"[^>]*>[\s\S]*?(?=<h2\b|$)/i);
  if (!sourcesMatch) {
    throw new Error("QUALITY_GUARD: missing #sources section body");
  }
  const sourceLinks = (sourcesMatch[0].match(/<a\b[^>]*href\s*=\s*"https:\/\//gi) || []).length;
  if (sourceLinks < MIN_EXTERNAL_LINKS) {
    throw new Error(`QUALITY_GUARD: #sources links too low (${sourceLinks}/${MIN_EXTERNAL_LINKS})`);
  }
}

function checkEvidenceRegistryTokens(html: string) {
  const statTokens = (html.match(/\[EVID:STAT_\d+\]/g) || []).length;
  const quoteTokens = (html.match(/\[EVID:QUOTE_\d+\]/g) || []).length;
  if (statTokens < MIN_EVID_STAT_TOKENS) {
    throw new Error(`QUALITY_GUARD: stat evidence tokens too low (${statTokens}/${MIN_EVID_STAT_TOKENS})`);
  }
  if (quoteTokens < MIN_EVID_QUOTE_TOKENS) {
    throw new Error(`QUALITY_GUARD: quote evidence tokens too low (${quoteTokens}/${MIN_EVID_QUOTE_TOKENS})`);
  }
}

function checkLengthAndQuoteRequirements(html: string) {
  const textOnly = html.replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim();
  const wordCount = textOnly ? textOnly.split(" ").length : 0;
  if (wordCount < MIN_ARTICLE_WORDS) {
    throw new Error(`QUALITY_GUARD: word count too low (${wordCount}/${MIN_ARTICLE_WORDS})`);
  }
  if (wordCount > MAX_ARTICLE_WORDS) {
    throw new Error(`QUALITY_GUARD: word count too high (${wordCount}/${MAX_ARTICLE_WORDS})`);
  }

  const blockquotes = (html.match(/<blockquote\b[^>]*>/gi) || []).length;
  if (blockquotes < MIN_BLOCKQUOTES) {
    throw new Error(`QUALITY_GUARD: blockquotes too low (${blockquotes}/${MIN_BLOCKQUOTES})`);
  }
}

function checkTitleAndMetaLengths(data: Awaited<ReturnType<typeof callLLM>>) {
  const title = data.title || "";
  const seoTitle = data.seo_title || "";
  const metaDesc = data.meta_desc || "";

  if (title.length > TITLE_MAX_LENGTH) {
    throw new Error(`QUALITY_GUARD: title too long (${title.length}/${TITLE_MAX_LENGTH} chars)`);
  }
  if (seoTitle && seoTitle.length > SEO_TITLE_MAX_LENGTH) {
    throw new Error(`QUALITY_GUARD: seo_title too long (${seoTitle.length}/${SEO_TITLE_MAX_LENGTH} chars)`);
  }
  if (metaDesc && metaDesc.length > META_DESC_MAX_LENGTH) {
    throw new Error(`QUALITY_GUARD: meta_desc too long (${metaDesc.length}/${META_DESC_MAX_LENGTH} chars)`);
  }
}

function checkAuthoritativeSources(html: string) {
  const linkMatches = html.match(/<a\b[^>]*href\s*=\s*"(https?:\/\/[^"]+)"[^>]*>/gi) || [];
  let authCount = 0;
  for (const tag of linkMatches) {
    const hrefMatch = tag.match(/href\s*=\s*"(https?:\/\/[^"]+)"/i);
    if (hrefMatch) {
      const url = hrefMatch[1].toLowerCase();
      if (AUTHORITATIVE_DOMAINS.some((domain) => url.includes(domain))) {
        authCount++;
      }
    }
  }
  if (authCount < MIN_AUTHORITATIVE_LINKS) {
    throw new Error(`QUALITY_GUARD: authoritative sources too low (${authCount}/${MIN_AUTHORITATIVE_LINKS} .gov/.edu/journal links)`);
  }
}

function checkFaqSection(html: string) {
  const faqSectionMatch = html.match(/id\s*=\s*"faq"[\s\S]*?(?=<h2\b|$)/i);
  if (faqSectionMatch) {
    const faqH3Count = (faqSectionMatch[0].match(/<h3\b[^>]*>/gi) || []).length;
    if (faqH3Count < MIN_FAQ_QUESTIONS) {
      throw new Error(`QUALITY_GUARD: FAQ questions too few (${faqH3Count}/${MIN_FAQ_QUESTIONS})`);
    }
    if (faqH3Count > MAX_FAQ_QUESTIONS) {
      throw new Error(`QUALITY_GUARD: FAQ questions too many (${faqH3Count}/${MAX_FAQ_QUESTIONS})`);
    }
  }
}

function checkKeyTermsSection(html: string) {
  const keyTermsMatch = html.match(/id\s*=\s*"key-terms"[\s\S]*?(?=<h2\b|$)/i);
  if (keyTermsMatch) {
    const dtCount = (keyTermsMatch[0].match(/<dt\b|<dfn\b/gi) || []).length;
    const h3Count = (keyTermsMatch[0].match(/<h3\b[^>]*>/gi) || []).length;
    const termCount = Math.max(dtCount, h3Count);
    if (termCount < MIN_KEY_TERMS) {
      throw new Error(`QUALITY_GUARD: key terms too few (${termCount}/${MIN_KEY_TERMS})`);
    }
  }
}

function checkBannedCtas(htmlLower: string) {
  for (const phrase of BANNED_CTA_PHRASES) {
    if (htmlLower.includes(phrase)) {
      throw new Error(`QUALITY_GUARD: banned sales CTA phrase detected (${phrase})`);
    }
  }
}

function checkFeaturedImageRequirement(data: Awaited<ReturnType<typeof callLLM>>) {
  const imageCount = Array.isArray(data.images) ? data.images.length : 0;
  if (imageCount !== TARGET_FEATURED_IMAGES) {
    throw new Error(`QUALITY_GUARD: featured images must be exactly ${TARGET_FEATURED_IMAGES} (got ${imageCount})`);
  }
  const featured = Array.isArray(data.images) ? data.images[0] : undefined;
  const featuredSrc = featured?.src?.trim();
  const featuredAlt = featured?.alt?.trim();
  if (!featuredSrc || !featuredAlt) {
    throw new Error("QUALITY_GUARD: featured image missing (images[0].src + images[0].alt required)");
  }
}

async function getDraftForRow(
  row: QueueRow,
  context: ExecutorContext,
  precomputed: BatchGenerationResult | null,
): Promise<Awaited<ReturnType<typeof callLLM>>> {
  const systemPrompt = context.buildSystemPrompt(row.url_blog_crawl);
  if (!precomputed) {
    return withRetry(() => callLLM(systemPrompt, context.model, INITIAL_USER_PROMPT));
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
