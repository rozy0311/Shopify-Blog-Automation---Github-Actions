import { google } from "googleapis";
import fs from "node:fs/promises";
import path from "node:path";
import "dotenv/config";

function buildAuth(scopes: string[]) {
  const raw =
    process.env.GOOGLE_SERVICE_ACCOUNT_JSON ||
    process.env.GOOGLE_APPLICATION_CREDENTIALS_JSON ||
    process.env.GOOGLE_CREDENTIALS;
  if (raw) {
    try {
      const credentials = JSON.parse(raw);
      return new google.auth.GoogleAuth({ scopes, credentials });
    } catch (err) {
      throw new Error(`Invalid GOOGLE_CREDENTIALS JSON: ${(err as Error).message}`);
    }
  }
  return new google.auth.GoogleAuth({ scopes });
}

const auth = buildAuth(["https://www.googleapis.com/auth/spreadsheets"]);

async function getSheetsClient() {
  return google.sheets({ version: "v4", auth });
}

function requireEnv(name: string): string {
  const value = process.env[name];
  if (!value) {
    throw new Error(`Missing required env var ${name}`);
  }
  return value;
}

export async function readConfig(): Promise<Record<string, string>> {
  if (process.env.LOCAL_ONLY === "true") {
    const configFile = process.env.CONFIG_FILE;
    if (configFile) {
      const fileConfig = await readConfigFromFile(configFile);
      return hydrateConfig(fileConfig);
    }
    return hydrateConfig({});
  }

  const configFile = process.env.CONFIG_FILE;
  if (configFile) {
    const fileConfig = await readConfigFromFile(configFile);
    return hydrateConfig(fileConfig);
  }

  if (process.env.SHEETS_ENABLED === "false" || !process.env.SHEETS_ID) {
    return hydrateConfig({});
  }

  const sheets = await getSheetsClient();
  const range = process.env.CONFIG_RANGE || "CONFIG!A:B";
  const { data } = await sheets.spreadsheets.values.get({
    spreadsheetId: requireEnv("SHEETS_ID"),
    range,
  });
  const rows = (data.values ?? []) as string[][];
  const map: Record<string, string> = {};
  for (const row of rows.slice(1)) {
    const key = (row?.[0] || "").trim();
    if (key) {
      map[key] = (row?.[1] || "").trim();
    }
  }
  return hydrateConfig(map);
}

export type QueueRow = {
  url_blog_crawl: string;
  url_blog_shopify: string;
};

export async function readQueue(limit = 30): Promise<QueueRow[]> {
  const queueFile = process.env.QUEUE_FILE;
  if (queueFile) {
    return readQueueFromFile(queueFile, limit);
  }

  const queueUrl = process.env.QUEUE_URL;
  if (queueUrl) {
    return readQueueFromUrl(queueUrl, limit);
  }

  if (process.env.LOCAL_ONLY === "true") {
    throw new Error("Missing queue source for LOCAL_ONLY: set QUEUE_FILE or QUEUE_URL");
  }

  if (process.env.SHEETS_ENABLED === "false" || !process.env.SHEETS_ID) {
    throw new Error("Missing queue source: set QUEUE_FILE/QUEUE_URL or enable Sheets");
  }

  const sheets = await getSheetsClient();
  const range = process.env.SHEETS_RANGE || "Sheet1!A:B";
  const { data } = await sheets.spreadsheets.values.get({
    spreadsheetId: requireEnv("SHEETS_ID"),
    range,
  });
  const rows = (data.values ?? []) as string[][];
  return normalizeQueueRows(
    rows
      .slice(1)
      .map((row) => ({
        url_blog_crawl: (row?.[0] || "").trim(),
        url_blog_shopify: (row?.[1] || "").trim(),
      }))
      .filter((row) => row.url_blog_crawl && !row.url_blog_shopify),
    limit,
  );
}

export async function updateBackfill(urlBlogCrawl: string, publishedUrl: string) {
  if (process.env.LOCAL_ONLY === "true") {
    console.warn("Skipping Sheets backfill in LOCAL_ONLY mode.");
    return;
  }

  const sheets = await getSheetsClient();
  const range = process.env.SHEETS_RANGE || "Sheet1!A:B";
  const { data } = await sheets.spreadsheets.values.get({
    spreadsheetId: requireEnv("SHEETS_ID"),
    range,
  });
  const rows = (data.values ?? []) as string[][];
  const rowIndex = rows.findIndex((row) => (row?.[0] || "").trim() === urlBlogCrawl);
  if (rowIndex < 0) {
    throw new Error(`Row not found for backfill: ${urlBlogCrawl}`);
  }
  const sheetName = range.split("!")[0] || "Sheet1";
  const targetRange = `${sheetName}!B${rowIndex + 1}:B${rowIndex + 1}`;
  await sheets.spreadsheets.values.update({
    spreadsheetId: requireEnv("SHEETS_ID"),
    range: targetRange,
    valueInputOption: "RAW",
    requestBody: { values: [[publishedUrl]] },
  });
}

function hydrateConfig(map: Record<string, string>): Record<string, string> {
  const merged = { ...map };
  if (!merged.BLOG_HANDLE) merged.BLOG_HANDLE = process.env.BLOG_HANDLE || "agritourism";
  if (!merged.AUTHOR) merged.AUTHOR = process.env.AUTHOR || "The Rike";
  if (!merged.LLM_CONTROL_PROMPT && process.env.LLM_CONTROL_PROMPT) {
    merged.LLM_CONTROL_PROMPT = process.env.LLM_CONTROL_PROMPT;
  }
  return merged;
}

async function readConfigFromFile(filePath: string): Promise<Record<string, string>> {
  const resolved = path.isAbsolute(filePath) ? filePath : path.resolve(process.cwd(), filePath);
  const text = await fs.readFile(resolved, "utf8");
  const ext = path.extname(resolved).toLowerCase();
  if (ext === ".json") {
    const parsed = JSON.parse(text) as Record<string, string>;
    return Object.fromEntries(
      Object.entries(parsed).map(([key, value]) => [String(key), String(value ?? "")]),
    );
  }
  return parseEnvText(text);
}

async function readQueueFromFile(filePath: string, limit: number): Promise<QueueRow[]> {
  const resolved = path.isAbsolute(filePath) ? filePath : path.resolve(process.cwd(), filePath);
  const text = await fs.readFile(resolved, "utf8");
  const ext = path.extname(resolved).toLowerCase();
  if (ext === ".json") {
    const parsed = JSON.parse(text);
    return normalizeQueueRows(coerceQueueItems(parsed), limit);
  }
  return normalizeQueueRows(parseDelimitedQueue(text), limit);
}

async function readQueueFromUrl(url: string, limit: number): Promise<QueueRow[]> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 30000);
  let response: Response;
  try {
    response = await fetch(url, { signal: controller.signal });
  } finally {
    clearTimeout(timeout);
  }
  if (!response.ok) {
    throw new Error(`Failed to fetch queue URL (${response.status})`);
  }
  const text = await response.text();
  const contentType = response.headers.get("content-type") || "";
  if (contentType.includes("application/json") || url.toLowerCase().endsWith(".json")) {
    const parsed = JSON.parse(text);
    return normalizeQueueRows(coerceQueueItems(parsed), limit);
  }
  return normalizeQueueRows(parseDelimitedQueue(text), limit);
}

function coerceQueueItems(input: unknown): QueueRow[] {
  if (Array.isArray(input)) {
    return input
      .map((item) => {
        if (typeof item === "string") {
          return { url_blog_crawl: item, url_blog_shopify: "" };
        }
        if (item && typeof item === "object") {
          const obj = item as Record<string, unknown>;
          const url = String(obj.url_blog_crawl || obj.url || obj.source || "");
          const published = String(obj.url_blog_shopify || obj.published || "");
          return { url_blog_crawl: url.trim(), url_blog_shopify: published.trim() };
        }
        return { url_blog_crawl: "", url_blog_shopify: "" };
      })
      .filter((row) => row.url_blog_crawl);
  }
  if (input && typeof input === "object") {
    const list = (input as Record<string, unknown>).items;
    if (Array.isArray(list)) return coerceQueueItems(list);
  }
  return [];
}

function parseDelimitedQueue(text: string): QueueRow[] {
  const lines = text
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean);
  if (!lines.length) return [];
  const delimiter = lines.some((line) => line.includes("\t")) ? "\t" : ",";
  const hasHeader = /url/i.test(lines[0]);
  const dataLines = hasHeader ? lines.slice(1) : lines;
  return dataLines
    .map((line) => {
      const [crawl, published] = line.split(delimiter).map((value) => value.trim());
      return { url_blog_crawl: crawl || "", url_blog_shopify: published || "" };
    })
    .filter((row) => row.url_blog_crawl);
}

function normalizeQueueRows(rows: QueueRow[], limit: number): QueueRow[] {
  return rows
    .filter((row) => row.url_blog_crawl && !row.url_blog_shopify)
    .slice(0, limit);
}

function parseEnvText(text: string): Record<string, string> {
  const map: Record<string, string> = {};
  for (const raw of text.split(/\r?\n/)) {
    const line = raw.trim();
    if (!line || line.startsWith("#")) continue;
    const idx = line.indexOf("=");
    if (idx < 0) continue;
    const key = line.slice(0, idx).trim();
    const value = line.slice(idx + 1).trim().replace(/^"(.*)"$/, "$1");
    if (key) map[key] = value;
  }
  return map;
}
