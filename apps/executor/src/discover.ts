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
  "packs", "bags", "satchets", "sachets", "supply", "supplies",
  "buy", "shop", "order", "discount", "coupon", "free shipping",
  "add to cart", "limited time", "on sale",
];

const MIN_NICHE_CHARS = 85;
const MAX_NICHE_CHARS = 95;

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

interface RotationState {
  lastIndex: number;
  publishedTopics: string[];
  updatedAt: string;
}

interface NicheIdea {
  product: string;
  topic: string;
  chars: number;
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
    `Generate exactly ${count} micro niche blog topic ideas for the product: "${product.commonName}".`,
    "",
    "CONSTRAINTS (STRICT):",
    `- Each topic MUST be ${MIN_NICHE_CHARS}-${MAX_NICHE_CHARS} characters long (count carefully).`,
    "- English only.",
    `- NEVER use these shopping/commercial words: ${BANNED_KEYWORDS.join(", ")}`,
    "- Use the common product name (not brand names or Vietnamese names).",
    "- Focus on HIGH SEARCH VOLUME, HIGH ENGAGEMENT angles:",
    "  * Specific audiences (e.g. 'pho lovers', 'balcony growers', 'first-time tea drinkers')",
    "  * Practical how-to (growing, brewing, cooking, preserving)",
    "  * Health/wellness benefits backed by science",
    "  * Cultural significance and traditional uses",
    "  * Comparison or 'vs' topics",
    "  * Seasonal or regional relevance",
    "- Each idea should target a DIFFERENT angle — no duplicates.",
    "",
    `Return a JSON array of exactly ${count} objects: [{"topic": "...", "chars": N}]`,
    "Where chars is the exact character count of the topic string.",
    "Return JSON only. No markdown, no code fences.",
  ].join("\n");

  const userPrompt = [
    `Product common name: ${product.commonName}`,
    `Full product title: ${product.title}`,
    "",
    `Generate ${count} unique micro niche ideas. Each MUST be ${MIN_NICHE_CHARS}-${MAX_NICHE_CHARS} characters.`,
  ].join("\n");

  const raw = await withRetry(() =>
    callStructuredLLM<Array<{ topic: string; chars: number }>>(systemPrompt, model, userPrompt),
  );

  if (!Array.isArray(raw)) return [];

  return raw
    .filter((item) => item?.topic && typeof item.topic === "string")
    .map((item) => ({
      product: product.commonName,
      topic: item.topic.trim(),
      chars: item.topic.trim().length,
    }));
}

/* ─── filtering ─── */

export function filterNicheIdeas(ideas: NicheIdea[], existingTopics: string[]): NicheIdea[] {
  const existingLower = new Set(existingTopics.map((t) => t.toLowerCase()));

  return ideas.filter((idea) => {
    const topic = idea.topic;
    const lower = topic.toLowerCase();

    // Character length check
    if (topic.length < MIN_NICHE_CHARS || topic.length > MAX_NICHE_CHARS) {
      console.log(`[DISCOVER] REJECT (chars=${topic.length}): ${topic}`);
      return false;
    }

    // Banned keywords
    for (const banned of BANNED_KEYWORDS) {
      if (lower.includes(banned)) {
        console.log(`[DISCOVER] REJECT (banned="${banned}"): ${topic}`);
        return false;
      }
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

  // 2. Load rotation state
  const state = await loadRotationState();

  // 3. Pick next products from rotation
  const picked = pickNextProducts(products, state, PRODUCTS_PER_RUN);
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
      const selected = filtered.slice(0, PICK_PER_PRODUCT);
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
  const queuePath = await writeDiscoverQueue(allIdeas);
  console.log(`[DISCOVER] Queue file: ${queuePath}`);

  // 6. Optionally append to Google Sheets
  if (writeToSheets) {
    await appendToSheetsQueue(allIdeas);
  }

  // 7. Update rotation state
  state.publishedTopics.push(...allIdeas.map((i) => i.topic));
  // Keep only last 500 topics to prevent unbounded growth
  if (state.publishedTopics.length > 500) {
    state.publishedTopics = state.publishedTopics.slice(-500);
  }
  state.updatedAt = new Date().toISOString();
  await saveRotationState(state);

  // 8. Summary
  console.log(`[DISCOVER] ✓ Generated ${allIdeas.length} topics from ${picked.length} products`);
  for (const idea of allIdeas) {
    console.log(`  - [${idea.chars}c] ${idea.product}: ${idea.topic}`);
  }
}

try {
  await main();
} catch (error) {
  console.error("[DISCOVER] Crashed:", error);
  process.exitCode = 1;
}
