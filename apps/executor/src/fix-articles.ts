import "dotenv/config";
import fs from "fs-extra";
import { callLLM, validateNoYears } from "./llm.js";
import { getBlogByHandle, listArticles, updateArticle } from "./shopify-client.js";
import { withRetry } from "./batch.js";

/* ─── constants ─── */

const FIX_LIMIT = Number(process.env.FIX_LIMIT || "10");
const MAX_FIX_RETRIES = Number(process.env.MAX_FIX_RETRIES || "3");
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
const BANNED_CTA_PHRASES = ["shop now", "buy", "add to cart", "limited time"];
const REQUIRED_SECTION_IDS = ["key-conditions", "background", "framework", "troubleshooting", "expert-tips", "faq", "key-terms", "sources"];

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
  "FINAL REMINDER: The article MUST be 1400-2500 words. Write detailed, expansive paragraphs. Do NOT be concise.",
].join(" ");

/* ─── types ─── */

interface FixResult {
  id: number;
  title: string;
  status: "ok" | "fixed" | "failed";
  errors?: string[];
  newErrors?: string[];
}

/* ─── quality checks (same logic as index.ts) ─── */

function countWords(html: string): number {
  const textOnly = html.replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim();
  return textOnly ? textOnly.split(" ").length : 0;
}

function collectQualityErrors(html: string, title?: string): string[] {
  const errors: string[] = [];

  // Word count
  const wc = countWords(html);
  if (wc < MIN_ARTICLE_WORDS) errors.push(`word count too low (${wc}/${MIN_ARTICLE_WORDS})`);
  if (wc > MAX_ARTICLE_WORDS) errors.push(`word count too high (${wc}/${MAX_ARTICLE_WORDS})`);

  // Structure: H2 count
  const h2Count = (html.match(/<h2\b[^>]*>/gi) || []).length;
  if (h2Count < MIN_H2_COUNT) errors.push(`h2 count too low (${h2Count}/${MIN_H2_COUNT})`);

  // Required section IDs
  for (const id of REQUIRED_SECTION_IDS) {
    if (!new RegExp(`id\\s*=\\s*"${id}"`, "i").test(html)) {
      errors.push(`missing section id="${id}"`);
    }
  }

  // External links
  const externalLinks = (html.match(/<a\b[^>]*href\s*=\s*"https?:\/\//gi) || []).length;
  if (externalLinks < MIN_EXTERNAL_LINKS) errors.push(`external links too low (${externalLinks}/${MIN_EXTERNAL_LINKS})`);

  // Authoritative sources
  const linkMatches = html.match(/<a\b[^>]*href\s*=\s*"(https?:\/\/[^"]+)"[^>]*>/gi) || [];
  let authCount = 0;
  for (const tag of linkMatches) {
    const hrefMatch = tag.match(/href\s*=\s*"(https?:\/\/[^"]+)"/i);
    if (hrefMatch && AUTHORITATIVE_DOMAINS.some((d) => hrefMatch[1].toLowerCase().includes(d))) {
      authCount++;
    }
  }
  if (authCount < MIN_AUTHORITATIVE_LINKS) errors.push(`authoritative sources too low (${authCount}/${MIN_AUTHORITATIVE_LINKS})`);

  // Blockquotes
  const bq = (html.match(/<blockquote\b[^>]*>/gi) || []).length;
  if (bq < MIN_BLOCKQUOTES) errors.push(`blockquotes too low (${bq}/${MIN_BLOCKQUOTES})`);

  // FAQ section
  const faqMatch = html.match(/id\s*=\s*"faq"[\s\S]*?(?=<h2\b|$)/i);
  if (faqMatch) {
    const faqH3 = (faqMatch[0].match(/<h3\b[^>]*>/gi) || []).length;
    if (faqH3 < MIN_FAQ_QUESTIONS) errors.push(`FAQ questions too few (${faqH3}/${MIN_FAQ_QUESTIONS})`);
    if (faqH3 > MAX_FAQ_QUESTIONS) errors.push(`FAQ questions too many (${faqH3}/${MAX_FAQ_QUESTIONS})`);
  }

  // Key terms section
  const ktMatch = html.match(/id\s*=\s*"key-terms"[\s\S]*?(?=<h2\b|$)/i);
  if (ktMatch) {
    const dtCount = (ktMatch[0].match(/<dt\b|<dfn\b/gi) || []).length;
    const h3Count = (ktMatch[0].match(/<h3\b[^>]*>/gi) || []).length;
    if (Math.max(dtCount, h3Count) < MIN_KEY_TERMS) errors.push(`key terms too few`);
  }

  // Banned CTAs
  const lower = html.toLowerCase();
  for (const phrase of BANNED_CTA_PHRASES) {
    if (lower.includes(phrase)) errors.push(`banned CTA: "${phrase}"`);
  }

  // Title length (if provided)
  if (title && title.length > TITLE_MAX_LENGTH) {
    errors.push(`title too long (${title.length}/${TITLE_MAX_LENGTH})`);
  }

  return errors;
}

/* ─── LLM regeneration ─── */

function buildFixSystemPrompt(title: string): string {
  return [
    "You are a senior botanical wellness editor for The Rike (therike.com), a premium organic herbal products store.",
    `Rewrite and improve this existing blog article: "${title}".`,
    "",
    "The article MUST meet ALL quality standards. Previous version had issues.",
    "CONTEXT: The Rike specializes in organic herbal teas, seeds, superfoods, and traditional remedies.",
    "The blog (Agritourism) covers wellness, sustainable agriculture, herbal medicine, and mindful living.",
    "",
    "WRITING APPROACH:",
    "- Write from deep expertise in herbalism, botany, and wellness.",
    "- Include real scientific names, traditional uses, and modern research.",
    "- Reference authoritative sources (.gov, .edu, PubMed, USDA, WHO).",
    "- Use concrete examples, sensory descriptions, and practical tips.",
    "- Do NOT mention any product prices, store URLs, or commercial offers.",
    "",
    RULES_SUFFIX,
  ].join("\n");
}

function buildFixUserPrompt(title: string, qualityErrors: string[], wordCount: number): string {
  return [
    `REWRITE the article titled: "${title}"`,
    "",
    "The previous version FAILED quality checks with these errors:",
    ...qualityErrors.map((e) => `  - ${e}`),
    "",
    `Previous word count: ${wordCount}. MINIMUM required: ${MIN_ARTICLE_WORDS}.`,
    "Fix ALL issues. Write comprehensive, detailed paragraphs.",
    "Return only a single minified JSON object. No markdown, no code fences.",
  ].join("\n");
}

function stripYearTokens(data: { title?: string; seo_title?: string; meta_desc?: string; html?: string }) {
  const normalizeInlineMarkdown = (v: string | undefined) => {
    if (!v || !v.includes("*")) return v;
    return v
      .replace(/\*\*\*\s*([^*][\s\S]*?)\s*\*\*\*/g, "<strong>$1</strong>")
      .replace(/\*\*\s*([^*][\s\S]*?)\s*\*\*/g, "<strong>$1</strong>")
      .replace(/(^|[^*])\*\s*([^*][\s\S]*?)\s*\*(?!\*)/g, "$1<em>$2</em>");
  };

  const sanitize = (v: string | undefined) =>
    v
      ? (normalizeInlineMarkdown(v) || v).replace(/\b(19|20)\d{2}\b/g, "").replace(/\s{2,}/g, " ").trim()
      : v;
  return {
    ...data,
    title: sanitize(data.title) || data.title,
    seo_title: sanitize(data.seo_title),
    meta_desc: sanitize(data.meta_desc),
    html: sanitize(data.html) || data.html,
  };
}

/* ─── main ─── */

async function main() {
  const blogHandle = process.env.BLOG_HANDLE || "agritourism";
  const model = process.env.OPENAI_MODEL || "gpt-4o-mini";
  const dryRun = process.env.FIX_DRY_RUN === "true";

  console.log(`[FIX] Starting article quality scan (blog=${blogHandle}, limit=${FIX_LIMIT}, dry=${dryRun})`);

  // 1. Get the blog
  const blog = await withRetry(() => getBlogByHandle(blogHandle));
  console.log(`[FIX] Blog ID: ${blog.id}`);

  // 2. Fetch articles
  const articles = await listArticles(blog.id, FIX_LIMIT * 5); // fetch more than limit to filter
  console.log(`[FIX] Fetched ${articles.length} articles`);

  // 3. Scan quality
  const results: FixResult[] = [];
  let fixCount = 0;

  for (const article of articles) {
    if (fixCount >= FIX_LIMIT) break;

    const html = article.body_html || "";
    const errors = collectQualityErrors(html, article.title);

    if (errors.length === 0) {
      const wc = countWords(html);
      console.log(`[FIX] OK (${wc}w): ${article.title}`);
      results.push({ id: article.id, title: article.title, status: "ok" });
      continue;
    }

    console.log(`[FIX] NEEDS FIX (${errors.length} issues): ${article.title}`);
    errors.forEach((e) => console.log(`  - ${e}`));

    if (dryRun) {
      results.push({ id: article.id, title: article.title, status: "failed", errors });
      fixCount++;
      continue;
    }

    // 4. Regenerate via LLM with retry
    let fixed = false;
    for (let attempt = 1; attempt <= MAX_FIX_RETRIES; attempt++) {
      try {
        const systemPrompt = buildFixSystemPrompt(article.title);
        const userPrompt = buildFixUserPrompt(article.title, errors, countWords(html));

        const rawData = await withRetry(() => callLLM(systemPrompt, model, userPrompt));
        const data = stripYearTokens(rawData);
        validateNoYears(rawData);

        const newHtml = data.html || "";
        const newErrors = collectQualityErrors(newHtml, data.title);

        if (newErrors.length > 0) {
          console.warn(`[FIX] Attempt ${attempt}/${MAX_FIX_RETRIES} still has ${newErrors.length} issues for: ${article.title}`);
          if (attempt === MAX_FIX_RETRIES) {
            results.push({ id: article.id, title: article.title, status: "failed", errors, newErrors });
            fixCount++;
          }
          continue;
        }

        // 5. Update on Shopify
        const updatePayload: Record<string, unknown> = { body_html: newHtml };
        if (data.title && data.title.length <= TITLE_MAX_LENGTH) {
          updatePayload.title = data.title;
        }
        if (data.meta_desc) {
          updatePayload.summary_html = `<p>${data.meta_desc}</p>`;
        }

        await withRetry(() => updateArticle(blog.id, article.id, updatePayload));

        const newWc = countWords(newHtml);
        console.log(`[FIX] FIXED (${newWc}w, attempt ${attempt}): ${article.title}`);
        results.push({ id: article.id, title: article.title, status: "fixed" });
        fixed = true;
        fixCount++;
        break;
      } catch (err) {
        console.error(`[FIX] Attempt ${attempt}/${MAX_FIX_RETRIES} error for ${article.title}:`, err instanceof Error ? err.message : err);
        if (attempt === MAX_FIX_RETRIES) {
          results.push({ id: article.id, title: article.title, status: "failed", errors, newErrors: [err instanceof Error ? err.message : String(err)] });
          fixCount++;
        }
      }
    }
  }

  // 6. Write summary report
  const summary = {
    total: results.length,
    ok: results.filter((r) => r.status === "ok").length,
    fixed: results.filter((r) => r.status === "fixed").length,
    failed: results.filter((r) => r.status === "failed").length,
    results,
    timestamp: new Date().toISOString(),
  };

  await fs.ensureDir("out");
  await fs.writeJSON("out/fix-articles-report.json", summary, { spaces: 2 });
  console.log(`\n[FIX] ─── Summary ───`);
  console.log(`  Total scanned: ${summary.total}`);
  console.log(`  Already OK:    ${summary.ok}`);
  console.log(`  Fixed:         ${summary.fixed}`);
  console.log(`  Failed:        ${summary.failed}`);
}

try {
  await main();
} catch (error) {
  console.error("[FIX] Crashed:", error);
  process.exitCode = 1;
}
