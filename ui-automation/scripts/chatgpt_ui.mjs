import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import zlib from 'node:zlib';

import { chromium } from 'playwright';

function readStdin() {
  return new Promise((resolve, reject) => {
    let data = '';
    process.stdin.setEncoding('utf8');
    process.stdin.on('data', (chunk) => {
      data += String(chunk || '');
    });
    process.stdin.on('end', () => resolve(data));
    process.stdin.on('error', reject);
  });
}

function writeErr(message) {
  process.stderr.write(`${String(message || '').trim()}\n`);
}

function toBool(value, defaultValue = false) {
  const raw = String(value || '').trim().toLowerCase();
  if (!raw) return defaultValue;
  return raw === '1' || raw === 'true' || raw === 'yes' || raw === 'on';
}

function sanitizeBaseUrl(raw) {
  const fallback = 'https://chatgpt.com/';
  const text = String(raw || '').trim();
  if (!text || text === 'https://' || text === 'http://') return fallback;
  try {
    const url = new URL(text.includes('://') ? text : `https://${text}`);
    if (url.protocol !== 'https:') return fallback;
    if (!url.pathname || url.pathname === '') url.pathname = '/';
    return url.toString();
  } catch {
    return fallback;
  }
}

function decodeStorageStatePayload(b64) {
  const normalized = String(b64 || '').replace(/\s+/g, '');
  if (!normalized) return '';
  const binary = Buffer.from(normalized, 'base64');

  // Try plain UTF-8 JSON first.
  const plain = binary.toString('utf8');
  try {
    JSON.parse(plain);
    return plain;
  } catch {
    // Continue to gzip path.
  }

  try {
    const gunzipped = zlib.gunzipSync(binary).toString('utf8');
    JSON.parse(gunzipped);
    return gunzipped;
  } catch {
    return plain;
  }
}

function normalizeStorageState(raw) {
  if (!raw || typeof raw !== 'object') {
    return { cookies: [], origins: [] };
  }
  const cookies = Array.isArray(raw.cookies) ? raw.cookies : [];
  const origins = Array.isArray(raw.origins) ? raw.origins : [];
  return { cookies, origins };
}

function splitModelTokens(text) {
  return String(text || '')
    .toLowerCase()
    .replace(/gpt\s*[-_]?/g, ' ')
    .replace(/[^a-z0-9.\s]+/g, ' ')
    .split(/\s+/)
    .map((token) => token.trim())
    .filter(Boolean)
    .filter((token) => !new Set(['gpt', 'chatgpt', 'thinking', 'reasoning', 'model']).has(token));
}

function composerLocator(page) {
  return page
    .locator(
      [
        'div#prompt-textarea[contenteditable="true"]:visible',
        'div.ProseMirror[contenteditable="true"]:visible',
        'div[contenteditable="true"][role="textbox"]:visible',
        'textarea[name="prompt-textarea"]:visible',
      ].join(', '),
    )
    .first();
}

function assistantLocator(page) {
  return page
    .locator(
      [
        '[data-message-author-role="assistant"]',
        'article[data-testid^="conversation-turn-"]:has(div.markdown)',
        'main div.markdown',
      ].join(', '),
    )
    .last();
}

async function clickSendButton(page) {
  const candidates = [
    page.getByRole('button', { name: /send/i }).first(),
    page.locator('button[data-testid="send-button"]').first(),
    page.locator('button[aria-label*="Send"]').first(),
  ];

  for (const button of candidates) {
    try {
      if (!(await button.count())) continue;
      await button.click({ timeout: 3000 });
      return true;
    } catch {
      // Try next candidate.
    }
  }
  return false;
}

async function waitForAssistantText(page, responseTimeoutSeconds) {
  const deadline = Date.now() + responseTimeoutSeconds * 1000;
  let previous = '';
  let stableCount = 0;

  while (Date.now() < deadline) {
    try {
      const assistant = assistantLocator(page);
      if (await assistant.count()) {
        const text = String((await assistant.innerText().catch(() => '')) || '').trim();
        if (text) {
          if (text === previous) {
            stableCount += 1;
            if (stableCount >= 2) return text;
          } else {
            stableCount = 0;
            previous = text;
          }
        }
      }
    } catch {
      // Ignore transient UI errors and keep polling.
    }

    await page.waitForTimeout(900);
  }

  return previous;
}

async function enforceModelSelection(page, modelLabel, strictModel) {
  if (!modelLabel) return;

  try {
    const maybeSwitcher = page
      .locator('button[aria-label^="Model selector, current model is"]').first()
      .or(page.getByRole('button', { name: /model|gpt/i }).first());

    if (await maybeSwitcher.count()) {
      await maybeSwitcher.click({ timeout: 3000 }).catch(() => {});
      const option = page.getByRole('menuitem', { name: new RegExp(modelLabel.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'i') }).first();
      if (await option.count()) {
        await option.click({ timeout: 3000 }).catch(() => {});
      } else {
        const any = page.getByText(modelLabel, { exact: false }).first();
        if (await any.count()) {
          await any.click({ timeout: 3000 }).catch(() => {});
        }
      }
    }
  } catch {
    // Continue and validate below.
  }

  if (!strictModel) return;

  await page.waitForTimeout(500);
  const selectorBtn = page.locator('button[aria-label^="Model selector, current model is"]').first();
  const aria = String((await selectorBtn.getAttribute('aria-label').catch(() => '')) || '');
  const ariaLower = aria.toLowerCase();
  const expectedLower = String(modelLabel || '').toLowerCase();

  let ok = ariaLower.includes(expectedLower);
  if (!ok) {
    const tokens = splitModelTokens(modelLabel);
    if (tokens.length >= 1) {
      ok = tokens.every((token) => ariaLower.includes(token));
    }
  }

  if (!ok) {
    writeErr(`Strict model selection failed: could not confirm model '${modelLabel}' is active. Current aria-label: ${aria || '(missing)'}`);
    process.exit(16);
  }
}

async function main() {
  const prompt = String((await readStdin()) || '').trim();
  if (!prompt) {
    writeErr('No prompt on stdin');
    process.exit(2);
  }

  const baseUrl = sanitizeBaseUrl(process.env.CHATGPT_UI_BASE_URL || 'https://chatgpt.com/');
  const modelLabel = String(process.env.CHATGPT_UI_MODEL_LABEL || '5.4 Thinking').trim();
  const strictModel = toBool(process.env.CHATGPT_UI_STRICT_MODEL, true);
  const headless = toBool(process.env.CHATGPT_UI_HEADLESS, true);
  const useChromeChannel = toBool(process.env.CHATGPT_UI_USE_CHROME_CHANNEL, false);

  const responseTimeoutRaw = String(process.env.CHATGPT_UI_RESPONSE_TIMEOUT_SECONDS || '').trim();
  const responseTimeoutSeconds = Number.isFinite(Number(responseTimeoutRaw))
    ? Math.max(30, Math.min(900, Number(responseTimeoutRaw)))
    : 240;

  const storageStateB64 = String(process.env.CHATGPT_UI_STORAGE_STATE_B64 || '').trim();
  const storageStatePath = String(process.env.CHATGPT_UI_STORAGE_STATE_PATH || '').trim();

  let resolvedStorageStatePath = '';
  let cleanupPath = '';

  if (storageStatePath && fs.existsSync(storageStatePath)) {
    resolvedStorageStatePath = storageStatePath;
  } else if (storageStateB64) {
    try {
      const decoded = decodeStorageStatePayload(storageStateB64);
      const parsed = JSON.parse(decoded);
      const normalized = normalizeStorageState(parsed);
      const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'chatgpt-state-'));
      cleanupPath = tmpDir;
      resolvedStorageStatePath = path.join(tmpDir, 'storageState.json');
      fs.writeFileSync(resolvedStorageStatePath, JSON.stringify(normalized), 'utf8');
    } catch (error) {
      writeErr(`CHATGPT_UI storage state parse failed: ${String(error?.message || error || 'unknown parse error')}`);
    }
  }

  let browser;
  let context;

  try {
    const launchOptions = {
      headless,
      channel: useChromeChannel ? 'chrome' : undefined,
      args: [
        '--disable-blink-features=AutomationControlled',
        '--no-default-browser-check',
        '--no-first-run',
      ],
    };

    browser = await chromium.launch(launchOptions);

    if (resolvedStorageStatePath && fs.existsSync(resolvedStorageStatePath)) {
      context = await browser.newContext({ storageState: resolvedStorageStatePath });
    } else {
      context = await browser.newContext();
    }

    const page = context.pages()[0] ? context.pages()[0] : await context.newPage();
    page.setDefaultTimeout(45000);

    await page.goto(baseUrl, { waitUntil: 'domcontentloaded' });

    const textbox = composerLocator(page);
    try {
      await textbox.waitFor({ state: 'visible', timeout: 30000 });
    } catch {
      writeErr('Not authenticated (no chat textbox). Provide CHATGPT_UI_STORAGE_STATE_B64.');
      process.exit(10);
    }

    await enforceModelSelection(page, modelLabel, strictModel);

    const tag = String((await textbox.evaluate((el) => el?.tagName || '').catch(() => '')) || '').toLowerCase();
    if (tag === 'textarea') {
      await textbox.fill(prompt);
      const sentByButton = await clickSendButton(page);
      if (!sentByButton) {
        await textbox.press('Enter');
      }
    } else {
      await textbox.click({ timeout: 8000 }).catch(() => {});
      await textbox.fill(prompt).catch(async () => {
        await textbox.evaluate((el, value) => {
          if (el) {
            el.textContent = String(value || '');
          }
        }, prompt);
      });

      const sentByButton = await clickSendButton(page);
      if (!sentByButton) {
        await textbox.press('Enter').catch(() => {});
      }
    }

    const output = String((await waitForAssistantText(page, responseTimeoutSeconds)) || '').trim();
    if (!output) {
      writeErr('Empty assistant response');
      process.exit(12);
    }

    process.stdout.write(output);
  } finally {
    try {
      if (context) await context.close();
    } catch {
      // Ignore close errors.
    }
    try {
      if (browser) await browser.close();
    } catch {
      // Ignore close errors.
    }
    if (cleanupPath) {
      try {
        fs.rmSync(cleanupPath, { recursive: true, force: true });
      } catch {
        // Ignore cleanup errors.
      }
    }
  }
}

main().catch((error) => {
  writeErr(String(error?.message || error || 'unknown error'));
  process.exit(1);
});
