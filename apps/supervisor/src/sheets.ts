import { google } from "googleapis";
import "dotenv/config";

const auth = new google.auth.GoogleAuth({
  scopes: ["https://www.googleapis.com/auth/spreadsheets.readonly"],
});

function requireEnv(name: string) {
  const value = process.env[name];
  if (!value) throw new Error(`Missing ${name}`);
  return value;
}

function getSheetsClient() {
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
