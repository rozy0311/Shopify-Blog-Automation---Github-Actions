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

const auth = buildAuth(["https://www.googleapis.com/auth/spreadsheets.readonly"]);

function requireEnv(name: string) {
  const value = process.env[name];
  if (!value) throw new Error(`Missing ${name}`);
  return value;
}

async function getSheetsClient() {
  return google.sheets({ version: "v4", auth });
}

export async function getQueueStatus(limitSample = 5) {
  const sheets = await getSheetsClient();
  const range = process.env.SHEETS_RANGE || "Sheet1!A:B";
  const { data } = await sheets.spreadsheets.values.get({
    spreadsheetId: requireEnv("SHEETS_ID"),
    range,
  });
  const rows = (data.values ?? []).slice(1) as string[][];
  const pending = rows.filter((row) => (row?.[0] || "").trim() && !(row?.[1] || "").trim());
  return {
    totalPending: pending.length,
    sampleUrls: pending.slice(0, limitSample).map((row) => (row?.[0] || "").trim()),
  };
}
