import { google } from "googleapis";
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
const sheetsTimeoutMs = Number(process.env.SHEETS_TIMEOUT_MS || "20000");

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
  const sheets = await getSheetsClient();
  const range = process.env.CONFIG_RANGE || "CONFIG!A:B";
  const { data } = await sheets.spreadsheets.values.get({
    spreadsheetId: requireEnv("SHEETS_ID"),
    range,
    timeout: Number.isFinite(sheetsTimeoutMs) && sheetsTimeoutMs > 0 ? sheetsTimeoutMs : 20000,
  });
  const rows = (data.values ?? []) as string[][];
  const map: Record<string, string> = {};
  for (const row of rows.slice(1)) {
    const key = (row?.[0] || "").trim();
    if (key) {
      map[key] = (row?.[1] || "").trim();
    }
  }
  if (!map.BLOG_HANDLE) map.BLOG_HANDLE = process.env.BLOG_HANDLE || "agritourism";
  if (!map.AUTHOR) map.AUTHOR = process.env.AUTHOR || "The Rike";
  return map;
}

export type QueueRow = {
  url_blog_crawl: string;
  url_blog_shopify: string;
};

export async function readQueue(limit = 30): Promise<QueueRow[]> {
  const sheets = await getSheetsClient();
  const range = process.env.SHEETS_RANGE || "Sheet1!A:B";
  const { data } = await sheets.spreadsheets.values.get({
    spreadsheetId: requireEnv("SHEETS_ID"),
    range,
    timeout: Number.isFinite(sheetsTimeoutMs) && sheetsTimeoutMs > 0 ? sheetsTimeoutMs : 20000,
  });
  const rows = (data.values ?? []) as string[][];
  return rows
    .slice(1)
    .map((row) => ({
      url_blog_crawl: (row?.[0] || "").trim(),
      url_blog_shopify: (row?.[1] || "").trim(),
    }))
    .filter((row) => row.url_blog_crawl && !row.url_blog_shopify)
    .slice(0, limit);
}

export async function updateBackfill(urlBlogCrawl: string, publishedUrl: string) {
  const sheets = await getSheetsClient();
  const range = process.env.SHEETS_RANGE || "Sheet1!A:B";
  const { data } = await sheets.spreadsheets.values.get({
    spreadsheetId: requireEnv("SHEETS_ID"),
    range,
    timeout: Number.isFinite(sheetsTimeoutMs) && sheetsTimeoutMs > 0 ? sheetsTimeoutMs : 20000,
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
    timeout: Number.isFinite(sheetsTimeoutMs) && sheetsTimeoutMs > 0 ? sheetsTimeoutMs : 20000,
  });
}
