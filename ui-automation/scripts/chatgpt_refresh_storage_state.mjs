import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { chromium } from 'playwright';

function decodeStorageStatePayload(b64) {
  const normalized = String(b64 || '').replace(/\s+/g, '');
  if (!normalized) return '';
  return Buffer.from(normalized, 'base64').toString('utf8');
}

function normalizeStorageState(raw) {
  if (!raw || typeof raw !== 'object') {
    return { cookies: [], origins: [] };
  }
  return {
    cookies: Array.isArray(raw.cookies) ? raw.cookies : [],
    origins: Array.isArray(raw.origins) ? raw.origins : [],
  };
}

async function main() {
  const baseUrl = String(process.env.CHATGPT_UI_BASE_URL || 'https://chatgpt.com/').trim();
  const stateB64 = String(process.env.CHATGPT_UI_STORAGE_STATE_B64 || '').trim();
  if (!stateB64) {
    throw new Error('Missing CHATGPT_UI_STORAGE_STATE_B64');
  }

  const outPath = String(
    process.env.CHATGPT_UI_STORAGE_STATE_OUT || path.join(process.cwd(), '.chatgpt-storageState.runner.json'),
  ).trim();

  const decoded = decodeStorageStatePayload(stateB64);
  const parsed = JSON.parse(decoded);
  const normalized = normalizeStorageState(parsed);

  const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'chatgpt-refresh-'));
  const inputStatePath = path.join(tmpDir, 'storageState.in.json');
  fs.writeFileSync(inputStatePath, JSON.stringify(normalized), 'utf8');

  const browser = await chromium.launch({
    headless: false,
    args: ['--disable-blink-features=AutomationControlled'],
  });

  try {
    const context = await browser.newContext({ storageState: inputStatePath });
    const page = await context.newPage();
    await page.goto(baseUrl, { waitUntil: 'domcontentloaded' });

    const textboxSelector = [
      'div#prompt-textarea[contenteditable="true"]',
      'div.ProseMirror[contenteditable="true"]',
      'div[contenteditable="true"][role="textbox"]',
      'textarea[name="prompt-textarea"]',
    ].join(', ');

    await page.waitForSelector(textboxSelector, { state: 'visible', timeout: 60000 });

    fs.mkdirSync(path.dirname(outPath), { recursive: true });
    await context.storageState({ path: outPath });

    const raw = fs.readFileSync(outPath);
    const outB64Path = `${outPath}.b64.txt`;
    fs.writeFileSync(outB64Path, raw.toString('base64'), 'utf8');

    const refreshed = JSON.parse(raw.toString('utf8'));
    const cookieCount = Array.isArray(refreshed.cookies) ? refreshed.cookies.length : 0;
    const originCount = Array.isArray(refreshed.origins) ? refreshed.origins.length : 0;

    process.stdout.write(`Refreshed storage state saved: ${outPath}\n`);
    process.stdout.write(`Cookie count: ${cookieCount}, origin count: ${originCount}\n`);
  } finally {
    await browser.close();
    fs.rmSync(tmpDir, { recursive: true, force: true });
  }
}

main().catch((error) => {
  process.stderr.write(`${String(error?.message || error)}\n`);
  process.exit(1);
});
