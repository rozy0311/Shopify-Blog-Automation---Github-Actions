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

function ensureDir(dirPath) {
  if (!dirPath) return '';
  try {
    fs.mkdirSync(dirPath, { recursive: true });
    return dirPath;
  } catch {
    return '';
  }
}

async function writeDebugArtifacts(page, details) {
  const baseDir = String(process.env.CHATGPT_UI_DEBUG_DIR || 'out/chatgpt-ui-debug').trim();
  if (!baseDir) return '';
  const dir = ensureDir(baseDir);
  if (!dir) return '';

  const stamp = new Date().toISOString().replace(/[:.]/g, '-');
  const prefix = path.join(dir, `chatgpt-ui-${stamp}`);
  const reportPath = `${prefix}.json`;
  const htmlPath = `${prefix}.html`;
  const screenshotPath = `${prefix}.png`;

  const report = {
    ...details,
    capturedAt: new Date().toISOString(),
  };

  try {
    if (page) {
      report.url = report.url || page.url();
      report.title = report.title || (await page.title().catch(() => ''));
      const html = await page.content().catch(() => '');
      if (html) {
        fs.writeFileSync(htmlPath, html, 'utf8');
        report.htmlPath = htmlPath;
      }
      await page.screenshot({ path: screenshotPath, fullPage: true }).catch(() => {});
      if (fs.existsSync(screenshotPath)) {
        report.screenshotPath = screenshotPath;
      }
    }
  } catch {
    // Ignore debug capture failures.
  }

  fs.writeFileSync(reportPath, JSON.stringify(report, null, 2), 'utf8');
  return reportPath;
}

function toBool(value, defaultValue = false) {
  const raw = String(value || '').trim().toLowerCase();
  if (!raw) return defaultValue;
  return raw === '1' || raw === 'true' || raw === 'yes' || raw === 'on';
}

function toClampedSeconds(value, fallbackSeconds, minSeconds = 15, maxSeconds = 1800) {
  const parsed = Number(String(value || '').trim());
  if (!Number.isFinite(parsed)) return fallbackSeconds;
  return Math.max(minSeconds, Math.min(maxSeconds, parsed));
}

function profileHasData(profileDir) {
  const dir = String(profileDir || '').trim();
  if (!dir || !fs.existsSync(dir)) return false;
  try {
    return fs.readdirSync(dir).length > 0;
  } catch {
    return false;
  }
}

function classifyChatgptUiError(error) {
  const message = String(error?.message || error || '').toLowerCase();
  if (
    message.includes('no persistent profile data') ||
    message.includes('missing chatgpt_ui storage state') ||
    message.includes('storage state parse failed')
  ) {
    return 'no_profile';
  }
  if (
    message.includes('not authenticated') ||
    message.includes('no chat textbox') ||
    message.includes('chat textbox not found') ||
    message.includes('authenticated session cookies were not detected') ||
    message.includes('manual login completed visually') ||
    message.includes('verify you are human') ||
    message.includes('just a moment') ||
    message.includes('current page: https://chatgpt.com/auth')
  ) {
    return 'expired';
  }
  return 'error';
}

async function hasAuthenticatedSession(context) {
  const cookies = await context.cookies().catch(() => []);
  return cookies.some((cookie) =>
    cookie?.name?.startsWith('__Secure-next-auth.session-token') || cookie?.name === 'oai-client-auth-session',
  );
}

async function persistStorageState(context, targetPath) {
  const outPath = String(targetPath || '').trim();
  if (!outPath) return '';

  fs.mkdirSync(path.dirname(outPath), { recursive: true });
  await context.storageState({ path: outPath, indexedDB: true });

  const raw = fs.readFileSync(outPath);
  fs.writeFileSync(`${outPath}.b64.txt`, raw.toString('base64'), 'utf8');
  return outPath;
}

function shouldPreferPersistentProfile(profileDir) {
  if (!String(profileDir || '').trim()) return false;
  return toBool(process.env.CHATGPT_UI_PREFER_PERSISTENT_PROFILE, true);
}

async function waitForManualLogin(page, context, textbox, options) {
  const {
    enabled,
    timeoutSeconds,
    persistPath,
  } = options;

  if (!enabled) return false;

  const currentUrl = page.url();
  const currentTitle = await page.title().catch(() => '');
  writeErr(
    [
      'ChatGPT UI session expired or login challenge detected.',
      `Open browser is ready for manual login. Current page: ${currentUrl || '(unknown)'}${currentTitle ? ` | title=${currentTitle}` : ''}`,
      `Please complete password / Cloudflare in the browser within ${timeoutSeconds}s.`,
      'After the chat textbox appears, the script will save the refreshed session and continue automatically.',
    ].join(' '),
  );

  await textbox.waitFor({ state: 'visible', timeout: timeoutSeconds * 1000 });

  const authed = await hasAuthenticatedSession(context);
  if (!authed) {
    throw new Error('Manual login completed visually, but authenticated session cookies were not detected.');
  }

  if (persistPath) {
    const savedPath = await persistStorageState(context, persistPath);
    writeErr(`Saved refreshed ChatGPT UI storage state: ${savedPath}`);
  }

  return true;
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

function modelTokensMatch(text, modelLabel) {
  const lowerText = String(text || '').toLowerCase();
  const lowerLabel = String(modelLabel || '').toLowerCase();
  if (!lowerText || !lowerLabel) return false;
  if (lowerText.includes(lowerLabel)) return true;

  const tokens = splitModelTokens(modelLabel);
  return tokens.length > 0 && tokens.every((token) => lowerText.includes(token));
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

function imageMetadataLooksRenderable(image) {
  if (!image || typeof image !== 'object') return false;
  const src = String(image.src || '').trim();
  const naturalWidth = Number(image.naturalWidth || 0);
  const naturalHeight = Number(image.naturalHeight || 0);
  const renderedWidth = Number(image.renderedWidth || 0);
  const renderedHeight = Number(image.renderedHeight || 0);
  if (!src) return false;
  if (naturalWidth >= 256 && naturalHeight >= 256) return true;
  if (renderedWidth >= 200 && renderedHeight >= 200) return true;
  return src.startsWith('http://') || src.startsWith('https://') || src.startsWith('data:image/') || src.startsWith('blob:');
}

async function collectAssistantImageMetadata(page) {
  const assistant = assistantLocator(page);
  if (!(await assistant.count())) return [];

  return await assistant
    .evaluate((node) => {
      const images = Array.from(node.querySelectorAll('img'));
      return images.map((img, index) => ({
        index,
        src: String(img.currentSrc || img.getAttribute('src') || '').trim(),
        alt: String(img.getAttribute('alt') || '').trim(),
        naturalWidth: Number(img.naturalWidth || 0),
        naturalHeight: Number(img.naturalHeight || 0),
        renderedWidth: Number(img.clientWidth || 0),
        renderedHeight: Number(img.clientHeight || 0),
      }));
    })
    .catch(() => []);
}

function guessImageExtension(mimeType, source = '') {
  const lowerMime = String(mimeType || '').toLowerCase();
  if (lowerMime.includes('png')) return '.png';
  if (lowerMime.includes('webp')) return '.webp';
  if (lowerMime.includes('jpeg') || lowerMime.includes('jpg')) return '.jpg';

  const cleanedSource = String(source || '').split('#')[0].split('?')[0].toLowerCase();
  if (cleanedSource.endsWith('.png')) return '.png';
  if (cleanedSource.endsWith('.webp')) return '.webp';
  if (cleanedSource.endsWith('.jpg') || cleanedSource.endsWith('.jpeg')) return '.jpg';
  return '.png';
}

function normalizeImageOutputPath(outputPath, fallbackExtension = '.png') {
  const raw = String(outputPath || '').trim();
  if (!raw) return '';
  const parsed = path.parse(raw);
  const resolved = parsed.ext ? raw : `${raw}${fallbackExtension}`;
  fs.mkdirSync(path.dirname(resolved), { recursive: true });
  return resolved;
}

function decodeDataUrlImage(source) {
  const match = /^data:(image\/[a-zA-Z0-9.+-]+);base64,(.+)$/i.exec(String(source || ''));
  if (!match) return null;

  try {
    return {
      mimeType: String(match[1] || '').toLowerCase(),
      buffer: Buffer.from(match[2], 'base64'),
    };
  } catch {
    return null;
  }
}

async function saveAssistantImage(page, context, images, outputPath) {
  const requestedPath = String(outputPath || '').trim();
  if (!requestedPath || !Array.isArray(images) || images.length === 0) return '';

  const preferred = images.find((image) => imageMetadataLooksRenderable(image)) || images[0];
  const src = String(preferred?.src || '').trim();

  const dataUrl = decodeDataUrlImage(src);
  if (dataUrl?.buffer?.length) {
    const targetPath = normalizeImageOutputPath(requestedPath, guessImageExtension(dataUrl.mimeType, src));
    fs.writeFileSync(targetPath, dataUrl.buffer);
    return targetPath;
  }

  if (/^https?:\/\//i.test(src)) {
    try {
      const response = await context.request.get(src, {
        timeout: 30000,
        failOnStatusCode: false,
      });
      if (response.ok()) {
        const body = await response.body();
        if (body?.length) {
          const contentType = String(response.headers()['content-type'] || '').trim();
          const targetPath = normalizeImageOutputPath(requestedPath, guessImageExtension(contentType, src));
          fs.writeFileSync(targetPath, body);
          return targetPath;
        }
      }
    } catch {
      // Fall back to element screenshot below.
    }
  }

  const assistant = assistantLocator(page);
  const handles = assistant.locator('img');
  const count = await handles.count().catch(() => 0);
  for (let index = 0; index < count; index += 1) {
    const handle = handles.nth(index);
    const currentSrc = String((await handle.evaluate((img) => img.currentSrc || img.getAttribute('src') || '').catch(() => '')) || '').trim();
    if (src && currentSrc && currentSrc !== src) continue;

    try {
      await handle.scrollIntoViewIfNeeded().catch(() => {});
      const targetPath = normalizeImageOutputPath(requestedPath, '.png');
      await handle.screenshot({ path: targetPath });
      if (fs.existsSync(targetPath) && fs.statSync(targetPath).size > 0) {
        return targetPath;
      }
    } catch {
      // Try the next rendered image candidate.
    }
  }

  return '';
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

// Reconstruct markdown from the rendered assistant message DOM. ChatGPT renders
// markdown into HTML, so innerText() loses link URLs, heading levels, list
// markers, etc. This walker rebuilds a reasonable markdown source. Gated by
// CHATGPT_UI_AS_MARKDOWN=1 so default callers keep existing innerText output.
async function extractAssistantMarkdown(page) {
  const assistant = assistantLocator(page);
  if (!(await assistant.count())) return '';
  return assistant.evaluate((root) => {
    if (!root) return '';
    const PRESERVE_NEWLINES = '\u0001';
    function walk(node) {
      if (!node) return '';
      if (node.nodeType === Node.TEXT_NODE) {
        return (node.nodeValue || '').replace(/\s+/g, ' ');
      }
      if (node.nodeType !== Node.ELEMENT_NODE) return '';
      const tag = (node.tagName || '').toLowerCase();
      const childMarkdown = () =>
        Array.from(node.childNodes || []).map(walk).join('');
      switch (tag) {
        case 'h1':
        case 'h2':
        case 'h3':
        case 'h4':
        case 'h5':
        case 'h6': {
          const level = Number(tag.slice(1));
          return `\n\n${'#'.repeat(level)} ${childMarkdown().trim()}\n\n`;
        }
        case 'p':
          return `\n\n${childMarkdown().trim()}\n\n`;
        case 'br':
          return PRESERVE_NEWLINES;
        case 'strong':
        case 'b':
          return `**${childMarkdown()}**`;
        case 'em':
        case 'i':
          return `*${childMarkdown()}*`;
        case 'code':
          if ((node.parentElement || {}).tagName === 'PRE') return childMarkdown();
          return `\`${childMarkdown()}\``;
        case 'pre': {
          const code = (node.textContent || '').replace(/\n$/, '');
          return `\n\n\`\`\`\n${code}\n\`\`\`\n\n`;
        }
        case 'a': {
          const href = node.getAttribute('href') || '';
          const text = childMarkdown().trim() || href;
          if (!href) return text;
          return `[${text}](${href})`;
        }
        case 'ul': {
          const items = Array.from(node.children || [])
            .filter((c) => (c.tagName || '').toLowerCase() === 'li')
            .map((li) => `- ${walk(li).trim()}`);
          return `\n\n${items.join('\n')}\n\n`;
        }
        case 'ol': {
          const items = Array.from(node.children || [])
            .filter((c) => (c.tagName || '').toLowerCase() === 'li')
            .map((li, i) => `${i + 1}. ${walk(li).trim()}`);
          return `\n\n${items.join('\n')}\n\n`;
        }
        case 'li':
          return childMarkdown().trim();
        case 'blockquote':
          return `\n\n> ${childMarkdown().trim().split('\n').join('\n> ')}\n\n`;
        case 'hr':
          return '\n\n---\n\n';
        case 'table': {
          const rows = Array.from(node.querySelectorAll('tr'));
          if (!rows.length) return '';
          const lines = [];
          rows.forEach((tr, idx) => {
            const cells = Array.from(tr.children || []).map((td) =>
              walk(td).trim().replace(/\|/g, '\\|').replace(/\n+/g, ' '),
            );
            lines.push(`| ${cells.join(' | ')} |`);
            if (idx === 0) {
              lines.push(`| ${cells.map(() => '---').join(' | ')} |`);
            }
          });
          return `\n\n${lines.join('\n')}\n\n`;
        }
        default:
          return childMarkdown();
      }
    }
    let out = walk(root);
    out = out.replace(new RegExp(PRESERVE_NEWLINES, 'g'), '\n');
    out = out.replace(/[ \t]+\n/g, '\n');
    out = out.replace(/\n{3,}/g, '\n\n');
    return out.trim();
  });
}

async function waitForAssistantImages(page, responseTimeoutSeconds) {
  const deadline = Date.now() + responseTimeoutSeconds * 1000;
  let last = [];

  while (Date.now() < deadline) {
    try {
      const images = await collectAssistantImageMetadata(page);
      if (Array.isArray(images) && images.length > 0) {
        last = images;
        const renderable = images.filter((image) => imageMetadataLooksRenderable(image));
        if (renderable.length > 0) {
          return renderable;
        }
      }
    } catch {
      // Ignore transient UI errors and keep polling.
    }

    await page.waitForTimeout(900);
  }

  return last;
}

async function enforceModelSelection(page, modelLabel, strictModel) {
  if (!modelLabel) return;
  let selected = false;

  try {
    const maybeSwitcher = page
      .locator('button[aria-label^="Model selector, current model is"]').first()
      .or(page.getByRole('button', { name: /model|gpt/i }).first());

    if (await maybeSwitcher.count()) {
      await maybeSwitcher.click({ timeout: 3000 }).catch(() => {});
      const option = page.getByRole('menuitem', { name: new RegExp(modelLabel.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'i') }).first();
      if (await option.count()) {
        await option.click({ timeout: 3000 }).catch(() => {});
        selected = true;
      } else {
        const any = page.getByText(modelLabel, { exact: false }).first();
        if (await any.count()) {
          await any.click({ timeout: 3000 }).catch(() => {});
          selected = true;
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
  const buttonText = String((await selectorBtn.innerText().catch(() => '')) || '');
  const visibleModelSignals = await page.evaluate(() => {
    const elements = Array.from(document.querySelectorAll('button,[role="button"],[role="menuitem"]'));
    return elements
      .map((element) => {
        const text = String(element.textContent || '').trim();
        const ariaLabel = String(element.getAttribute('aria-label') || '').trim();
        return [ariaLabel, text].filter(Boolean).join(' | ');
      })
      .filter(Boolean)
      .slice(0, 80);
  }).catch(() => []);

  const candidates = [aria, buttonText, ...visibleModelSignals].filter(Boolean);
  let ok = candidates.some((candidate) => modelTokensMatch(candidate, modelLabel));

  if (!ok && selected) {
    ok = candidates.some((candidate) => /thinking|5\.4|gpt/i.test(String(candidate || '')));
  }

  if (!ok) {
    const preview = candidates.slice(0, 8).join(' || ');
    writeErr(`Strict model selection failed: could not confirm model '${modelLabel}' is active. Current signals: ${preview || '(missing)'}`);
    process.exit(16);
  }
}

async function main() {
  const probeOnly = toBool(process.env.CHATGPT_UI_PROBE_ONLY, false);
  const prompt = String((await readStdin()) || '').trim();
  if (!probeOnly && !prompt) {
    writeErr('No prompt on stdin');
    process.exit(2);
  }

  const baseUrl = sanitizeBaseUrl(process.env.CHATGPT_UI_BASE_URL || 'https://chatgpt.com/');
  const modelLabel = String(process.env.CHATGPT_UI_MODEL_LABEL || '5.4 Thinking').trim();
  const mode = String(process.env.CHATGPT_UI_MODE || 'text').trim().toLowerCase();
  const strictModel = toBool(process.env.CHATGPT_UI_STRICT_MODEL, true);
  const allowManualLogin = toBool(process.env.CHATGPT_UI_ALLOW_MANUAL_LOGIN, false);
  const manualLoginTimeoutRaw = String(process.env.CHATGPT_UI_MANUAL_LOGIN_TIMEOUT_SECONDS || '').trim();
  const manualLoginTimeoutSeconds = Number.isFinite(Number(manualLoginTimeoutRaw))
    ? Math.max(60, Math.min(1800, Number(manualLoginTimeoutRaw)))
    : 900;
  const headless = allowManualLogin ? false : toBool(process.env.CHATGPT_UI_HEADLESS, true);
  const useChromeChannel = toBool(process.env.CHATGPT_UI_USE_CHROME_CHANNEL, false);

  const responseTimeoutRaw = String(process.env.CHATGPT_UI_RESPONSE_TIMEOUT_SECONDS || '').trim();
  const responseTimeoutSeconds = toClampedSeconds(responseTimeoutRaw, 240, 30, 900);
  const textboxTimeoutRaw = String(process.env.CHATGPT_UI_TEXTBOX_TIMEOUT_SECONDS || '').trim();
  const textboxTimeoutSeconds = toClampedSeconds(textboxTimeoutRaw, probeOnly ? 60 : 45, 15, 1800);
  const imageOutputPath = String(process.env.CHATGPT_UI_IMAGE_OUTPUT_PATH || '').trim();

  const storageStateB64 = String(process.env.CHATGPT_UI_STORAGE_STATE_B64 || '').trim();
  const storageStatePath = String(process.env.CHATGPT_UI_STORAGE_STATE_PATH || '').trim();
  const profileDir = String(process.env.CHATGPT_UI_PROFILE_DIR || '').trim();
  const preferPersistentProfile = shouldPreferPersistentProfile(profileDir);

  if (preferPersistentProfile && !profileHasData(profileDir) && !storageStateB64 && !(storageStatePath && fs.existsSync(storageStatePath))) {
    throw new Error(`No persistent profile data found at ${profileDir}`);
  }

  let resolvedStorageStatePath = '';
  let cleanupPath = '';
  let storageStateSource = 'none';
  let storageCookieCount = 0;
  let storageOriginCount = 0;
  let runtimeSource = preferPersistentProfile ? 'persistent-profile' : 'storage-state';
  let profileLaunchError = '';

  if (storageStatePath && fs.existsSync(storageStatePath)) {
    resolvedStorageStatePath = storageStatePath;
    storageStateSource = 'path';
    try {
      const parsed = JSON.parse(fs.readFileSync(storageStatePath, 'utf8'));
      const normalized = normalizeStorageState(parsed);
      storageCookieCount = normalized.cookies.length;
      storageOriginCount = normalized.origins.length;
    } catch {
      // Keep counters at zero.
    }
  } else if (storageStateB64) {
    try {
      const decoded = decodeStorageStatePayload(storageStateB64);
      const parsed = JSON.parse(decoded);
      const normalized = normalizeStorageState(parsed);
      storageStateSource = 'base64';
      storageCookieCount = normalized.cookies.length;
      storageOriginCount = normalized.origins.length;
      const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'chatgpt-state-'));
      cleanupPath = tmpDir;
      resolvedStorageStatePath = path.join(tmpDir, 'storageState.json');
      fs.writeFileSync(resolvedStorageStatePath, JSON.stringify(normalized), 'utf8');
    } catch (error) {
      throw new Error(`CHATGPT_UI storage state parse failed: ${String(error?.message || error || 'unknown parse error')}`);
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

    if (preferPersistentProfile) {
      try {
        fs.mkdirSync(profileDir, { recursive: true });
        context = await chromium.launchPersistentContext(profileDir, launchOptions);
      } catch (error) {
        runtimeSource = 'storage-state';
        profileLaunchError = String(error?.message || error || 'unknown persistent profile error');
        writeErr(`Persistent ChatGPT UI profile launch failed; falling back to storage state. ${profileLaunchError}`);
      }
    }

    if (!context) {
      browser = await chromium.launch(launchOptions);

      if (resolvedStorageStatePath && fs.existsSync(resolvedStorageStatePath)) {
        context = await browser.newContext({ storageState: resolvedStorageStatePath });
      } else {
        context = await browser.newContext();
      }
    }

    const page = context.pages()[0] ? context.pages()[0] : await context.newPage();
    page.setDefaultTimeout(45000);

    await page.goto(baseUrl, { waitUntil: 'domcontentloaded' });

    const textbox = composerLocator(page);
    try {
      await textbox.waitFor({ state: 'visible', timeout: textboxTimeoutSeconds * 1000 });
    } catch {
      const persistPath = storageStatePath || process.env.CHATGPT_UI_STORAGE_STATE_OUT || '';
      const resumed = await waitForManualLogin(page, context, textbox, {
        enabled: allowManualLogin,
        timeoutSeconds: manualLoginTimeoutSeconds,
        persistPath,
      }).catch(() => false);

      if (resumed) {
        await textbox.waitFor({ state: 'visible', timeout: 10000 });
      } else {
      const reportPath = await writeDebugArtifacts(page, {
        reason: 'no-chat-textbox',
        storageStateSource,
        storageCookieCount,
        storageOriginCount,
        runtimeSource,
        profileDir: profileDir || undefined,
        profileLaunchError: profileLaunchError || undefined,
        modelLabel,
        strictModel,
        textboxTimeoutSeconds,
        baseUrl,
      });
      const storageHint =
        storageStateSource === 'none'
          ? 'No storage state loaded.'
          : `Storage loaded from ${storageStateSource} (cookies=${storageCookieCount}, origins=${storageOriginCount}).`;
      const url = page.url();
      const title = await page.title().catch(() => '');
      writeErr(
        `Not authenticated (no chat textbox). ${storageHint} Current page: ${url || '(unknown)'}${title ? ` | title=${title}` : ''}.${reportPath ? ` Debug report: ${reportPath}` : ''}`,
      );
      process.exit(10);
      }
    }

    if (probeOnly) {
      const title = await page.title().catch(() => '');
      process.stdout.write(JSON.stringify({ ok: true, mode: 'probe', url: page.url(), title, modelLabel }));
      return;
    }

    await enforceModelSelection(page, modelLabel, strictModel);

    if (allowManualLogin && storageStatePath) {
      await persistStorageState(context, storageStatePath).catch(() => {});
    }

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

    if (mode === 'image') {
      const imageDetails = await waitForAssistantImages(page, responseTimeoutSeconds);
      if (!Array.isArray(imageDetails) || imageDetails.length === 0) {
        writeErr('No image URL found in assistant response');
        process.exit(13);
      }

      const images = imageDetails
        .map((image) => String(image?.src || '').trim())
        .filter(Boolean);

      const savedPath = imageOutputPath
        ? await saveAssistantImage(page, context, imageDetails, imageOutputPath)
        : '';

      process.stdout.write(JSON.stringify({ images, imageDetails, savedPath }));
    } else {
      const output = String((await waitForAssistantText(page, responseTimeoutSeconds)) || '').trim();
      if (!output) {
        writeErr('Empty assistant response');
        process.exit(12);
      }
      let finalOutput = output;
      if (toBool(process.env.CHATGPT_UI_AS_MARKDOWN, false)) {
        try {
          const md = String((await extractAssistantMarkdown(page)) || '').trim();
          if (md) finalOutput = md;
        } catch (err) {
          writeErr(`markdown_extraction_failed: ${err?.message || err}`);
        }
      }
      process.stdout.write(finalOutput);
    }
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
  if (toBool(process.env.CHATGPT_UI_PROBE_ONLY, false)) {
    writeErr(`probe_status=${classifyChatgptUiError(error)}`);
  }
  writeErr(String(error?.message || error || 'unknown error'));
  process.exit(1);
});
