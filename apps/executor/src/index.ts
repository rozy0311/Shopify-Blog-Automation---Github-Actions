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

const RULES_SUFFIX = [
  "WORD COUNT IS THE #1 PRIORITY: You MUST write 1400-2500 words of text content in the html field. Each H2 section MUST have 150-300 words. Short articles WILL BE REJECTED. Count your words carefully.",
  "Rules: Return JSON only {title, seo_title, meta_desc, html, images:[{src,alt}]}.",
  "TITLE: ≤70 chars, primary keyword in first 10 chars. SEO_TITLE: ≤60 chars. META_DESC: ≤155 chars.",
  "HTML must be Shopify-safe. STRICT NO YEARS: never output any 4-digit year (19xx/20xx).",
  "STRUCTURE: Include these H2 sections with exact kebab-case ids: key-conditions, background, framework, troubleshooting, expert-tips, faq, key-terms, sources. Minimum 6 H2 tags.",
  "DIRECT ANSWER: First 50-70 words must directly answer the query. Primary keyword within first 120 characters.",
  "CITATIONS: ≥5 external links to authoritative sources (.gov/.edu/journals). Every <a> must use absolute HTTPS and rel=\"nofollow noopener\".",
  "EXPERT QUOTES: ≥2 <blockquote> tags with real expert name + title + organization.",
  "STATISTICS: ≥3 quantified stats with named sources.",
  "FAQ SECTION: 5-7 <h3> questions under the #faq section, each answer 50-80 words.",
  "KEY TERMS: 5-8 terms defined under the #key-terms section, each wrapped in <dfn> or <dt>/<dd>.",
  "IMAGES: ≥3 inline <img> inside html body, each with meaningful alt text (80-140 chars, literal description, no marketing). 1 featured image in images[0] with non-empty src and alt.",
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

  // Inject inline images post-quality-gate (LLM can't produce real image URLs)
  data.html = injectInlineImages(data.html || "", data.title || "");

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
    "",
    `Previous title: ${previousData.title}`,
    "Generate a COMPLETE, LONG, DETAILED article. Return JSON only.",
  ].join("\n");

  return base + feedback;
}

const TARGET_INLINE_IMAGES = 3;

/**
 * Inject inline images into article HTML using Pollinations AI image generation.
 * Inserts images after the first N `<h2>` sections for natural editorial flow.
 */
function injectInlineImages(html: string, title: string): string {
  // Skip if html is very short or already has enough images
  const existingImgs = (html.match(/<img\b[^>]*>/gi) || []).length;
  if (existingImgs >= TARGET_INLINE_IMAGES) return html;

  const needed = TARGET_INLINE_IMAGES - existingImgs;

  // Extract section headings for contextual image prompts
  const headingMatches = [...html.matchAll(/<h2\b[^>]*>([\s\S]*?)<\/h2>/gi)];
  const headings = headingMatches
    .map((m) => m[1].replaceAll(/<[^>]+>/g, "").trim())
    .filter((h) => h.length > 2);

  // Build image prompts from article title + section headings
  const prompts: string[] = [];
  for (let i = 0; i < needed; i++) {
    const sectionHint = headings[i + 1] || headings[i] || ""; // skip first heading (usually title)
    const prompt = sectionHint
      ? `${title} - ${sectionHint}, realistic editorial photo, natural light`
      : `${title}, realistic editorial photo, natural light`;
    prompts.push(prompt);
  }

  // Find insertion points: after closing </p> of each <h2> section
  let injected = 0;
  const h2Positions: number[] = [];
  const h2Regex = /<\/h2>\s*<p\b[^>]*>[\s\S]*?<\/p>/gi;
  let match: RegExpExecArray | null;
  while ((match = h2Regex.exec(html)) !== null) {
    h2Positions.push(match.index + match[0].length);
  }

  // Insert images at positions (reverse order to preserve indices)
  const insertions = h2Positions.slice(1, needed + 1); // skip first h2 (usually intro)
  if (insertions.length === 0 && h2Positions.length > 0) {
    insertions.push(h2Positions[0]);
  }

  let result = html;
  for (let i = insertions.length - 1; i >= 0 && injected < needed; i--) {
    const pos = insertions[i];
    const prompt = encodeURIComponent(prompts[injected] || title);
    const altText = prompts[injected]?.replace(/, realistic editorial photo.*$/, "") || title;
    const imgTag = `\n<figure><img src="https://image.pollinations.ai/prompt/${prompt}?width=800&height=450&nologo=true" alt="${altText}" loading="lazy" width="800" height="450"><figcaption>${altText}</figcaption></figure>\n`;
    result = result.slice(0, pos) + imgTag + result.slice(pos);
    injected++;
  }

  // If we still need more images, append at end before closing
  while (injected < needed) {
    const prompt = encodeURIComponent(prompts[injected] || title);
    const altText = prompts[injected]?.replace(/, realistic editorial photo.*$/, "") || title;
    const imgTag = `\n<figure><img src="https://image.pollinations.ai/prompt/${prompt}?width=800&height=450&nologo=true" alt="${altText}" loading="lazy" width="800" height="450"><figcaption>${altText}</figcaption></figure>\n`;
    result += imgTag;
    injected++;
  }

  console.log(`[IMAGE_INJECT] Injected ${injected} inline images via Pollinations`);
  return result;
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

function collectDraftQualityErrors(data: Awaited<ReturnType<typeof callLLM>>): string[] {
  const html = data.html || "";
  const htmlLower = html.toLowerCase();
  const errors: string[] = [];
  const checks = [
    () => checkTitleAndMetaLengths(data),
    () => checkStructureRequirements(html),
    () => checkLinkRequirements(html),
    () => checkAuthoritativeSources(html),
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
  if (imgTags.length < MIN_INLINE_IMAGES) {
    throw new Error(`QUALITY_GUARD: inline images too low (${imgTags.length}/${MIN_INLINE_IMAGES})`);
  }

  const missingAlt = imgTags.filter((tag) => !/\balt\s*=\s*"[^"\n]*\S[^"\n]*"/i.test(tag));
  if (missingAlt.length > 0) {
    throw new Error(`QUALITY_GUARD: inline image alt missing (${missingAlt.length})`);
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
