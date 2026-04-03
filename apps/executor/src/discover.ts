import "dotenv/config";
import fs from "fs-extra";
import path from "node:path";
import { callStructuredLLM } from "./llm.js";
import { withRetry } from "./batch.js";

/* ─── constants ─── */

const STORE_URL = process.env.STORE_URL || "https://therike.com";
const COLLECTION_HANDLE = process.env.DISCOVER_COLLECTION || "trending";
const PRODUCTS_PER_PAGE = 250;
const MAX_PAGES = 10;

/** Characters that signal a shopping listing rather than a niche idea. */
const BANNED_KEYWORDS = [
  "pack", "packs", "bag", "bags", "satchet", "satchets", "sachet", "sachets", "satches", "supply", "supplies",
  "buy", "shop", "order", "discount", "coupon", "free shipping",
  "add to cart", "limited time", "on sale",
];

const MIN_NICHE_CHARS = Number(process.env.DISCOVER_MIN_NICHE_CHARS || "52");
const MAX_NICHE_CHARS = Number(process.env.DISCOVER_MAX_NICHE_CHARS || "89");
const MIN_COMBINED_SCORE = Number(process.env.DISCOVER_MIN_COMBINED_SCORE || "15");

const HIGH_INTENT_HINTS = [
  "how to", "best", "vs", "for beginners", "benefits", "guide", "tips", "problems", "troubleshooting",
  "recipe", "grow", "growing", "care", "when to", "why",
];

// Must stay inside the approved natural living / herbal / homestead editorial scope.
const REQUIRED_DOMAIN_HINTS = [
  "herb", "herbal", "tea", "tincture", "salve", "infused oil",
  "natural", "zero-waste", "low-tox", "plastic-free",
  "garden", "growing", "grow", "soil", "seed", "compost",
  "kitchen", "ferment", "fermentation", "vinegar", "sourdough", "dehydrat",
  "cleaning", "pantry", "homestead", "frugal", "seasonal", "remedies",
  "diy", "homemade", "store-bought alternative",
];

// Off-domain or policy-risk terms that should never appear in topic selection.
const DISALLOWED_TOPIC_TERMS = [
  "app", "apps", "ai app", "chatgpt", "software", "tool", "platform",
  "diagnose", "diagnosis", "medical", "disease", "cure", "treat", "treatment",
  "crypto", "forex", "casino", "gambling",
];

const ROTATION_STATE_FILE = process.env.DISCOVER_STATE_FILE || "out/discover-state.json";
const DISCOVER_QUEUE_FILE = process.env.DISCOVER_QUEUE_FILE || "out/discover-queue.json";
const PRODUCTS_PER_RUN = Number(process.env.DISCOVER_PRODUCTS_PER_RUN || "5");
const IDEAS_PER_PRODUCT = Number(process.env.DISCOVER_IDEAS_PER_PRODUCT || "8");
const PICK_PER_PRODUCT = Number(process.env.DISCOVER_PICK_PER_PRODUCT || "2");

/* ─── types ─── */

interface Product {
  id: number;
  title: string;
  handle: string;
  commonName: string;
}

function hasAnyHint(topicLower: string, hints: string[]): boolean {
  return hints.some((hint) => topicLower.includes(hint));
}

function hasDisallowedTerm(topicLower: string): string | null {
  for (const term of DISALLOWED_TOPIC_TERMS) {
    const pattern = new RegExp(`\\b${escapeRegex(term.toLowerCase())}\\b`, "i");
    if (pattern.test(topicLower)) return term;
  }
  return null;
}

interface RotationState {
  lastIndex: number;
  publishedTopics: string[];
  updatedAt: string;
}

interface NicheIdea {
  product: string;
  topic: string;
  chars: number;
  searchScore: number;
  engagementScore: number;
  intentReason?: string;
}

function dedupeProductsByCommonName(products: Product[]): Product[] {
  const seen = new Set<string>();
  const output: Product[] = [];
  for (const product of products) {
    const key = product.commonName.toLowerCase().trim();
    if (!key) continue;
    if (seen.has(key)) continue;
    seen.add(key);
    output.push(product);
  }
  return output;
}

function hashString(input: string): number {
  let hash = 0;
  for (let i = 0; i < input.length; i += 1) {
    hash = (hash * 31 + input.charCodeAt(i)) >>> 0;
  }
  return hash;
}

function computeDynamicRotationStart(total: number): number {
  if (total <= 0) return 0;
  const runId = String(process.env.GITHUB_RUN_ID || "").trim();
  const runAttempt = String(process.env.GITHUB_RUN_ATTEMPT || "").trim();
  const hourKey = new Date().toISOString().slice(0, 13); // UTC hour bucket
  const seed = `${hourKey}|${runId}|${runAttempt}|${COLLECTION_HANDLE}`;
  return hashString(seed) % total;
}

function escapeRegex(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function hasBannedKeyword(lowerTopic: string): string | null {
  for (const banned of BANNED_KEYWORDS) {
    const pattern = new RegExp(`\\b${escapeRegex(banned.toLowerCase())}\\b`, "i");
    if (pattern.test(lowerTopic)) return banned;
  }
  return null;
}

function extractProductTokens(productName: string): string[] {
  return productName
    .toLowerCase()
    .split(/[^a-z0-9]+/)
    .filter((token) => token.length >= 4);
}

function topicMentionsProduct(topic: string, productName: string): boolean {
  const lowerTopic = topic.toLowerCase();
  const lowerProduct = productName.toLowerCase();
  if (lowerTopic.includes(lowerProduct)) return true;

  const tokens = extractProductTokens(productName);
  return tokens.some((token) => new RegExp(`\\b${escapeRegex(token)}\\b`, "i").test(lowerTopic));
}

function countIntentHints(topic: string): number {
  const lowerTopic = topic.toLowerCase();
  let count = 0;
  for (const hint of HIGH_INTENT_HINTS) {
    if (lowerTopic.includes(hint)) count += 1;
  }
  return count;
}

function rankIdea(idea: NicheIdea): number {
  const combined = idea.searchScore + idea.engagementScore;
  const intentBonus = Math.min(2, countIntentHints(idea.topic));
  return combined + intentBonus;
}

function selectTopIdeas(ideas: NicheIdea[], pickCount: number): NicheIdea[] {
  return [...ideas]
    .sort((a, b) => rankIdea(b) - rankIdea(a) || a.topic.length - b.topic.length)
    .slice(0, Math.max(0, pickCount));
}

function interleaveIdeasByProduct(ideas: NicheIdea[]): NicheIdea[] {
  const buckets = new Map<string, NicheIdea[]>();
  const productOrder: string[] = [];

  for (const idea of ideas) {
    if (!buckets.has(idea.product)) {
      buckets.set(idea.product, []);
      productOrder.push(idea.product);
    }
    buckets.get(idea.product)!.push(idea);
  }

  const output: NicheIdea[] = [];
  let added = true;
  while (added) {
    added = false;
    for (const product of productOrder) {
      const queue = buckets.get(product);
      if (queue && queue.length) {
        output.push(queue.shift()!);
        added = true;
      }
    }
  }

  return output;
}

/* ─── scrape products from Shopify public JSON API ─── */

export async function scrapeProducts(): Promise<Product[]> {
  const allProducts: Product[] = [];
  let page = 1;

  while (page <= MAX_PAGES) {
    const url = `${STORE_URL}/collections/${COLLECTION_HANDLE}/products.json?page=${page}&limit=${PRODUCTS_PER_PAGE}`;
    console.log(`[DISCOVER] Fetching products page ${page}: ${url}`);

    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 30_000);
    let resp: Response;
    try {
      resp = await fetch(url, { signal: controller.signal });
    } finally {
      clearTimeout(timeout);
    }

    if (!resp.ok) {
      // Some stores block this endpoint — fall back to hardcoded list
      console.warn(`[DISCOVER] Products JSON returned ${resp.status}, stopping at page ${page}`);
      break;
    }

    const json = await resp.json() as { products?: Array<{ id: number; title: string; handle: string }> };
    const products = json.products || [];
    if (products.length === 0) break;

    for (const p of products) {
      allProducts.push({
        id: p.id,
        title: p.title,
        handle: p.handle,
        commonName: extractCommonName(p.title),
      });
    }

    if (products.length < PRODUCTS_PER_PAGE) break;
    page++;
  }

  console.log(`[DISCOVER] Scraped ${allProducts.length} products from ${page} page(s)`);
  return allProducts;
}

/**
 * Extract the common plant/product name from a Shopify product title.
 * Strips quantities (e.g. "100 gram", "2 pack x 3000 seeds"), unit info,
 * and trailing descriptors like "for planting", "Non-GMO", etc.
 */
export function extractCommonName(title: string): string {
  let name = title
    // Remove leading quantity patterns
    .replace(/^\d+[\s-]*(gram|g|oz|pack|pc|pcs)\b[^\w]*/i, "")
    .replace(/^\d+\s*(x\s*)?\d+\s*(gram|g|seeds?|pack)\b[^\w]*/i, "")
    .replace(/^\d+\s*pack\s*(x\s*)?\d+\s*(seeds?|gram|g)\b[^\w]*/i, "")
    // Remove trailing " - N seeds/gram" patterns
    .replace(/\s*[-–]\s*\d+\s*(seeds?|gram|g)\b.*$/i, "")
    // Remove "N seeds for planting" / "N gram"
    .replace(/\s+\d+\s*(seeds?|gram|g)\b.*$/i, "")
    // Remove "for planting", "Non-GMO", "Organic", "Heirloom"
    .replace(/\b(for\s+planting|non[- ]?gmo|organic|heirloom|plant\s+seeds?)\b/gi, "")
    // Remove Vietnamese names in parentheses
    .replace(/\([^)]*\)/g, "")
    // Collapse whitespace
    .replace(/\s+/g, " ")
    .trim();

  // If extraction left nothing useful, return the original title truncated
  if (name.length < 3) name = title.split(/[-–(]/)[0].trim();
  return name;
}

/* ─── product rotation ─── */

async function loadRotationState(): Promise<RotationState> {
  try {
    const resolved = path.resolve(ROTATION_STATE_FILE);
    if (await fs.pathExists(resolved)) {
      return await fs.readJSON(resolved);
    }
  } catch {
    /* ignore */
  }
  return { lastIndex: 0, publishedTopics: [], updatedAt: new Date().toISOString() };
}

async function saveRotationState(state: RotationState): Promise<void> {
  await fs.ensureDir(path.dirname(path.resolve(ROTATION_STATE_FILE)));
  await fs.writeJSON(path.resolve(ROTATION_STATE_FILE), state, { spaces: 2 });
}

/**
 * Pick the next N products from the rotation, ensuring diversity.
 * Cycles through the full product list before repeating.
 */
function pickNextProducts(products: Product[], state: RotationState, count: number): Product[] {
  if (products.length === 0) return [];
  const n = Math.min(count, products.length);
  const picked: Product[] = [];
  let idx = state.lastIndex % products.length;

  for (let i = 0; i < n; i++) {
    picked.push(products[idx]);
    idx = (idx + 1) % products.length;
  }

  state.lastIndex = idx;
  return picked;
}

/* ─── niche idea generation via LLM ─── */

export async function generateNicheIdeas(
  product: Product,
  model: string,
  count: number = IDEAS_PER_PRODUCT,
): Promise<NicheIdea[]> {
  const systemPrompt = [
    "You are a senior SEO content strategist specializing in organic herbal products, gardening, and wellness.",
      `Generate exactly ${count} nano niche blog topic ideas for the product: "${product.commonName}".`,
    "",
    "CONSTRAINTS (STRICT):",
      `- Each topic MUST be ${MIN_NICHE_CHARS}-${MAX_NICHE_CHARS} characters long (count carefully, never exceed ${MAX_NICHE_CHARS}).`,
    "- English only.",
    "- Do NOT output topic questions. No question mark and no Q&A phrasing.",
    "- Do NOT output tech/software/app topics.",
    "- Do NOT output medical diagnosis/treatment claims.",
    `- NEVER use these shopping/commercial words: ${BANNED_KEYWORDS.join(", ")}`,
      "- Use the common product name naturally in each topic (not brand names or Vietnamese names).",
    "- Focus on HIGH SEARCH VOLUME, HIGH ENGAGEMENT angles:",
    "  * Specific audiences (e.g. 'pho lovers', 'balcony growers', 'first-time tea drinkers')",
    "  * Practical how-to (growing, brewing, cooking, preserving)",
    "  * Health/wellness benefits backed by science",
    "  * Cultural significance and traditional uses",
    "  * Comparison or 'vs' topics",
    "  * Seasonal or regional relevance",
    "- Each idea should target a different angle and avoid semantic overlap.",
      "- Prioritize topics people actively search and discuss right now.",
    "",
      `Return a JSON array of exactly ${count} objects: [{"topic": "...", "chars": N, "searchScore": 1-10, "engagementScore": 1-10, "intentReason": "..."}]`,
    "Where chars is the exact character count of the topic string.",
      "searchScore and engagementScore must reflect realistic popularity and user intent strength.",
    "Return JSON only. No markdown, no code fences.",
  ].join("\n");

  const userPrompt = [
    `Product common name: ${product.commonName}`,
    `Full product title: ${product.title}`,
    "",
      `Generate ${count} unique nano niche ideas. Each MUST be ${MIN_NICHE_CHARS}-${MAX_NICHE_CHARS} characters.`,
      "Each topic should read like a high-intent search query users genuinely care about.",
  ].join("\n");

  const raw = await withRetry(() =>
      callStructuredLLM<Array<{ topic: string; chars: number; searchScore?: number; engagementScore?: number; intentReason?: string }>>(
        systemPrompt,
        model,
        userPrompt,
      ),
  );

  if (!Array.isArray(raw)) return [];

  return raw
    .filter((item) => item?.topic && typeof item.topic === "string")
    .map((item) => ({
      product: product.commonName,
      topic: item.topic.trim(),
      chars: item.topic.trim().length,
        searchScore: Math.max(1, Math.min(10, Number(item.searchScore || 1))),
        engagementScore: Math.max(1, Math.min(10, Number(item.engagementScore || 1))),
        intentReason: typeof item.intentReason === "string" ? item.intentReason.trim() : "",
    }));
}

/* ─── filtering ─── */

export function filterNicheIdeas(ideas: NicheIdea[], existingTopics: string[]): NicheIdea[] {
  const existingLower = new Set(existingTopics.map((t) => t.toLowerCase()));
  const acceptedLower = new Set<string>();

  return ideas.filter((idea) => {
    const topic = idea.topic;
    const lower = topic.toLowerCase();

    // Character length check
    if (topic.length < MIN_NICHE_CHARS || topic.length > MAX_NICHE_CHARS) {
      console.log(`[DISCOVER] REJECT (chars=${topic.length}): ${topic}`);
      return false;
    }

    // Banned keywords
    const banned = hasBannedKeyword(lower);
    if (banned) {
      console.log(`[DISCOVER] REJECT (banned="${banned}"): ${topic}`);
      return false;
    }

    // Off-domain / risky terms
    const disallowed = hasDisallowedTerm(lower);
    if (disallowed) {
      console.log(`[DISCOVER] REJECT (off-domain="${disallowed}"): ${topic}`);
      return false;
    }

    // No question-style topics; keep production-ready declarative intents only.
    if (topic.includes("?") || /^(what|why|how|can|should|is|are)\b/i.test(topic.trim())) {
      console.log(`[DISCOVER] REJECT (question-style): ${topic}`);
      return false;
    }

    // Product focus check
    if (!topicMentionsProduct(topic, idea.product)) {
      console.log(`[DISCOVER] REJECT (missing product term): ${topic}`);
      return false;
    }

    // Product keyword should be early to align with "primary keyword first" editorial rule.
    const productPos = lower.indexOf(idea.product.toLowerCase());
    if (productPos > 18) {
      console.log(`[DISCOVER] REJECT (product too late, idx=${productPos}): ${topic}`);
      return false;
    }

    // Domain guardrail: must match at least one approved niche cluster hint.
    if (!hasAnyHint(lower, REQUIRED_DOMAIN_HINTS)) {
      console.log(`[DISCOVER] REJECT (outside niche clusters): ${topic}`);
      return false;
    }

    // Search + engagement threshold
    const combinedScore = idea.searchScore + idea.engagementScore;
    if (combinedScore < MIN_COMBINED_SCORE) {
      console.log(`[DISCOVER] REJECT (low score=${combinedScore}): ${topic}`);
      return false;
    }

    // English-only check (reject if >30% non-ASCII chars)
    const nonAscii = topic.replace(/[\x20-\x7E]/g, "").length;
    if (nonAscii / topic.length > 0.3) {
      console.log(`[DISCOVER] REJECT (non-English): ${topic}`);
      return false;
    }

    // Dedup against existing topics
    if (existingLower.has(lower)) {
      console.log(`[DISCOVER] REJECT (duplicate): ${topic}`);
      return false;
    }

    // Dedup inside current generation batch
    if (acceptedLower.has(lower)) {
      console.log(`[DISCOVER] REJECT (duplicate-in-run): ${topic}`);
      return false;
    }

    acceptedLower.add(lower);

    return true;
  });
}

/* ─── queue output ─── */

async function writeDiscoverQueue(ideas: NicheIdea[]): Promise<string> {
  await fs.ensureDir(path.dirname(path.resolve(DISCOVER_QUEUE_FILE)));
  const queue = ideas.map((idea) => ({
    url_blog_crawl: `topic://${idea.topic}`,
    url_blog_shopify: "",
    product: idea.product,
    chars: idea.chars,
    search_score: idea.searchScore,
    engagement_score: idea.engagementScore,
    intent_reason: idea.intentReason || "",
  }));
  await fs.writeJSON(path.resolve(DISCOVER_QUEUE_FILE), queue, { spaces: 2 });
  console.log(`[DISCOVER] Wrote ${queue.length} topics to ${DISCOVER_QUEUE_FILE}`);
  return path.resolve(DISCOVER_QUEUE_FILE);
}

/* ─── Google Sheets append (optional) ─── */

async function appendToSheetsQueue(ideas: NicheIdea[]): Promise<void> {
  if (process.env.SHEETS_ENABLED === "false" || !process.env.SHEETS_ID) {
    console.log("[DISCOVER] Sheets disabled, skipping append");
    return;
  }

  try {
    const { google } = await import("googleapis");
    const raw =
      process.env.GOOGLE_SERVICE_ACCOUNT_JSON ||
      process.env.GOOGLE_APPLICATION_CREDENTIALS_JSON ||
      process.env.GOOGLE_CREDENTIALS;
    if (!raw) {
      console.warn("[DISCOVER] No Google credentials, skipping Sheets append");
      return;
    }

    const credentials = JSON.parse(raw);
    const authClient = new google.auth.GoogleAuth({
      scopes: ["https://www.googleapis.com/auth/spreadsheets"],
      credentials,
    });
    const sheets = google.sheets({ version: "v4", auth: authClient });
    const sheetsId = process.env.SHEETS_ID!;
    const range = process.env.SHEETS_RANGE || "Sheet1!A:B";

    const values = ideas.map((idea) => [`topic://${idea.topic}`, ""]);

    await sheets.spreadsheets.values.append({
      spreadsheetId: sheetsId,
      range,
      valueInputOption: "RAW",
      requestBody: { values },
    });

    console.log(`[DISCOVER] Appended ${values.length} topics to Google Sheets`);
  } catch (err) {
    console.error("[DISCOVER] Failed to append to Sheets:", err instanceof Error ? err.message : err);
  }
}

/* ─── main ─── */

async function main() {
  const model = process.env.OPENAI_MODEL || "gpt-4o-mini";
  const writeToSheets = process.env.DISCOVER_WRITE_SHEETS === "true";

  console.log("[DISCOVER] Starting product discovery...");
  console.log(`[DISCOVER] Config: products_per_run=${PRODUCTS_PER_RUN}, ideas_per_product=${IDEAS_PER_PRODUCT}, pick_per_product=${PICK_PER_PRODUCT}`);

  // 1. Scrape products
  const products = await scrapeProducts();
  if (products.length === 0) {
    console.error("[DISCOVER] No products found, aborting");
    process.exitCode = 1;
    return;
  }

  const uniqueProducts = dedupeProductsByCommonName(products);
  if (uniqueProducts.length === 0) {
    console.error("[DISCOVER] No unique products after dedupe, aborting");
    process.exitCode = 1;
    return;
  }

  if (uniqueProducts.length !== products.length) {
    console.log(`[DISCOVER] Product dedupe by commonName: ${products.length} -> ${uniqueProducts.length}`);
  }

  // 2. Load rotation state
  const state = await loadRotationState();

  // In CI runs, rotation file is often ephemeral. Seed a run-specific start offset
  // when there is no persistent history to avoid repeatedly picking the first products.
  if (state.lastIndex === 0 && (!Array.isArray(state.publishedTopics) || state.publishedTopics.length === 0)) {
    state.lastIndex = computeDynamicRotationStart(uniqueProducts.length);
    console.log(`[DISCOVER] Rotation cold-start offset: ${state.lastIndex}/${uniqueProducts.length}`);
  }

  // 3. Pick next products from rotation
  const picked = pickNextProducts(uniqueProducts, state, PRODUCTS_PER_RUN);
  console.log(`[DISCOVER] Selected products: ${picked.map((p) => p.commonName).join(", ")}`);

  // 4. Generate niche ideas for each product
  const allIdeas: NicheIdea[] = [];
  for (const product of picked) {
    console.log(`[DISCOVER] Generating niche ideas for: ${product.commonName}`);
    try {
      const raw = await generateNicheIdeas(product, model);
      const filtered = filterNicheIdeas(raw, state.publishedTopics);
      console.log(`[DISCOVER] ${product.commonName}: ${raw.length} generated, ${filtered.length} passed filters`);

      // Pick top N ideas per product
      const selected = selectTopIdeas(filtered, PICK_PER_PRODUCT);
      allIdeas.push(...selected);
    } catch (err) {
      console.error(`[DISCOVER] Failed for ${product.commonName}:`, err instanceof Error ? err.message : err);
    }
  }

  if (allIdeas.length === 0) {
    console.warn("[DISCOVER] No valid niche ideas generated");
    // Write empty queue so downstream steps don't crash on missing file
    await writeDiscoverQueue([]);
    await saveRotationState(state);
    return;
  }

  // 5. Write queue file
  const interleavedIdeas = interleaveIdeasByProduct(allIdeas);
  const queuePath = await writeDiscoverQueue(interleavedIdeas);
  console.log(`[DISCOVER] Queue file: ${queuePath}`);

  // 6. Optionally append to Google Sheets
  if (writeToSheets) {
    await appendToSheetsQueue(interleavedIdeas);
  }

  // 7. Update rotation state
  state.publishedTopics.push(...interleavedIdeas.map((i) => i.topic));
  // Keep only last 500 topics to prevent unbounded growth
  if (state.publishedTopics.length > 500) {
    state.publishedTopics = state.publishedTopics.slice(-500);
  }
  state.updatedAt = new Date().toISOString();
  await saveRotationState(state);

  // 8. Summary
  console.log(`[DISCOVER] ✓ Generated ${interleavedIdeas.length} topics from ${picked.length} products`);
  for (const idea of interleavedIdeas) {
    console.log(`  - [${idea.chars}c | search=${idea.searchScore} | engage=${idea.engagementScore}] ${idea.product}: ${idea.topic}`);
  }
}

try {
  await main();
} catch (error) {
  console.error("[DISCOVER] Crashed:", error);
  process.exitCode = 1;
}
