import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { chromium } from 'playwright';

function log(msg = '') {
  process.stdout.write(`${msg}\n`);
}

async function waitForEnter() {
  return await new Promise((resolve) => {
    process.stdin.resume();
    process.stdin.once('data', () => resolve());
  });
}

function isTruthy(value, defaultValue = false) {
  const raw = String(value || '').trim().toLowerCase();
  if (!raw) return defaultValue;
  return ['1', 'true', 'yes', 'on'].includes(raw);
}

async function hasAuthenticatedSession(context) {
  const cookies = await context.cookies();
  return cookies.some((cookie) =>
    cookie?.name?.startsWith('__Secure-next-auth.session-token') || cookie?.name === 'oai-client-auth-session',
  );
}

async function main() {
  const baseUrl = String(process.env.CHATGPT_UI_BASE_URL || 'https://chatgpt.com/').trim();
  const outPath = String(
    process.env.CHATGPT_UI_STORAGE_STATE_OUT || path.join(process.cwd(), '.chatgpt-storageState.json'),
  ).trim();
  const useChromeChannel = ['1', 'true', 'yes', 'on'].includes(
    String(process.env.CHATGPT_UI_USE_CHROME_CHANNEL || '').trim().toLowerCase(),
  );
  const autoSave = isTruthy(process.env.CHATGPT_UI_BOOTSTRAP_AUTO_SAVE, true);
  const maxWaitSecondsRaw = String(process.env.CHATGPT_UI_BOOTSTRAP_MAX_WAIT_SECONDS || '600').trim();
  const maxWaitSeconds = Number.isFinite(Number(maxWaitSecondsRaw)) ? Math.max(60, Number(maxWaitSecondsRaw)) : 600;

  const launchOptions = {
    headless: false,
    channel: useChromeChannel ? 'chrome' : undefined,
    args: ['--disable-blink-features=AutomationControlled'],
  };

  log('ChatGPT UI bootstrap');
  log(`- Base URL: ${baseUrl}`);
  log(`- Output storage state: ${outPath}`);
  log('');
  log('Browser will open. Please:');
  log('1) Complete Cloudflare/Turnstile if shown');
  log('2) Login to ChatGPT');
  log('3) Wait until you can type in prompt box');
  log('4) Script will auto-save when chat box is detected (or press ENTER manually)');

  const browser = await chromium.launch(launchOptions);
  const context = await browser.newContext();
  const page = await context.newPage();
  await page.goto(baseUrl, { waitUntil: 'domcontentloaded' });

  const textboxSelector = [
    'div#prompt-textarea[contenteditable="true"]',
    'div.ProseMirror[contenteditable="true"]',
    'div[contenteditable="true"][role="textbox"]',
    'textarea[name="prompt-textarea"]',
  ].join(', ');

  if (autoSave) {
    log(`Waiting for chat textbox (up to ${maxWaitSeconds}s)...`);
    await Promise.race([
      page.waitForSelector(textboxSelector, { state: 'visible', timeout: maxWaitSeconds * 1000 }),
      waitForEnter(),
    ]);
  } else {
    await waitForEnter();
  }

  // Guard against anonymous/free mode false-positives. Only save after authenticated session cookies exist.
  const isAuthed = await hasAuthenticatedSession(context);
  if (!isAuthed) {
    log('Authentication not detected yet (missing session cookies).');
    log('Please finish login/challenge in this browser, then press ENTER to retry save.');
    await waitForEnter();
  }

  const isAuthedAfterRetry = await hasAuthenticatedSession(context);
  if (!isAuthedAfterRetry) {
    throw new Error('Session cookies not found. Refusing to save unauthenticated storage state.');
  }

  const dir = path.dirname(outPath);
  fs.mkdirSync(dir, { recursive: true });
  await context.storageState({ path: outPath });

  await browser.close();

  const raw = fs.readFileSync(outPath);
  const b64 = raw.toString('base64');
  const b64Path = `${outPath}.b64.txt`;
  fs.writeFileSync(b64Path, b64, 'utf8');

  log('');
  log(`Saved storage state: ${outPath}`);
  log(`Saved base64 file  : ${b64Path}`);
}

main().catch((error) => {
  process.stderr.write(`${String(error?.message || error)}\n`);
  process.exit(1);
});
