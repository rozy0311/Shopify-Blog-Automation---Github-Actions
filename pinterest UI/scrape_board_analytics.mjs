import { chromium } from 'playwright';
import fs from 'fs';
import path from 'path';

// Configuration
const BOARD_URL = 'https://www.pinterest.com/therike/blogs/';
const OUTPUT_FILE = 'bulk_content.json';
const SCROLL_DELAY = 1500;
const MAX_SCROLLS = 100;

async function scrapeBoardAnalytics() {
  const userDataDir = path.join(process.cwd(), 'chrome_stealth_profile');

  console.log('🚀 Launching browser with persistent profile...');
  const context = await chromium.launchPersistentContext(userDataDir, {
    headless: false,
    viewport: { width: 1400, height: 900 },
    args: ['--disable-blink-features=AutomationControlled']
  });

  const page = await context.newPage();

  try {
    console.log(`📍 Navigating to board: ${BOARD_URL}`);
    await page.goto(BOARD_URL, { waitUntil: 'networkidle', timeout: 60000 });
    await page.waitForTimeout(3000);

    // Check if logged in
    const isLoggedIn = await page.$('div[data-test-id="header-profile"]');
    if (!isLoggedIn) {
      console.log('⚠️ Not logged in! Please login manually...');
      console.log('Waiting 60 seconds for manual login...');
      await page.waitForTimeout(60000);
    }

    console.log('📜 Scrolling to load all pins...');
    let previousHeight = 0;
    let scrollCount = 0;

    while (scrollCount < MAX_SCROLLS) {
      await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
      await page.waitForTimeout(SCROLL_DELAY);

      const currentHeight = await page.evaluate(() => document.body.scrollHeight);
      if (currentHeight === previousHeight) {
        console.log('✅ Reached end of page');
        break;
      }
      previousHeight = currentHeight;
      scrollCount++;

      if (scrollCount % 10 === 0) {
        const pinCount = await page.$$eval('[data-test-id="pin"]', pins => pins.length);
        console.log(`  Scrolled ${scrollCount}x, found ${pinCount} pins...`);
      }
    }

    // Collect pin URLs
    console.log('🔍 Collecting pin URLs...');
    const pinElements = await page.$$('[data-test-id="pin"] a[href*="/pin/"]');
    const pinUrls = [];

    for (const el of pinElements) {
      const href = await el.getAttribute('href');
      if (href && href.includes('/pin/') && !pinUrls.includes(href)) {
        pinUrls.push(href.startsWith('http') ? href : `https://www.pinterest.com${href}`);
      }
    }

    console.log(`📌 Found ${pinUrls.length} unique pins`);

    // Scrape each pin for analytics
    const pins = [];

    for (let i = 0; i < pinUrls.length; i++) {
      const pinUrl = pinUrls[i];
      console.log(`\n[${i + 1}/${pinUrls.length}] Scraping: ${pinUrl}`);

      try {
        await page.goto(pinUrl, { waitUntil: 'domcontentloaded', timeout: 30000 });
        await page.waitForTimeout(2000);

        // Get pin title
        const title = await page.$eval('h1', el => el.textContent?.trim()).catch(() => '');

        // Get destination URL
        let destUrl = '';
        try {
          const linkEl = await page.$('a[data-test-id="pin-closeup-link"]');
          if (linkEl) {
            destUrl = await linkEl.getAttribute('href') || '';
          }
        } catch {}

        // Try to get analytics (clicks, impressions, saves)
        let clicks = 0, impressions = 0, saves = 0;

        try {
          // Look for analytics section
          const statsText = await page.$$eval('[data-test-id="stats-row"] span, [data-test-id="pin-stats"] span',
            els => els.map(e => e.textContent?.trim() || ''));

          for (const text of statsText) {
            if (text.includes('click') || text.includes('Click')) {
              const num = parseInt(text.replace(/\D/g, '')) || 0;
              clicks = num;
            }
            if (text.includes('impression') || text.includes('Impression')) {
              const num = parseInt(text.replace(/\D/g, '')) || 0;
              impressions = num;
            }
            if (text.includes('save') || text.includes('Save')) {
              const num = parseInt(text.replace(/\D/g, '')) || 0;
              saves = num;
            }
          }
        } catch {}

        // Extract pin ID
        const pinId = pinUrl.match(/\/pin\/(\d+)/)?.[1] || '';

        pins.push({
          pinId,
          pinUrl,
          title,
          destUrl,
          analytics: { clicks, impressions, saves },
          content: null // Will be filled by generate_content_bulk.mjs
        });

        console.log(`  ✓ ${title.slice(0, 50)}... | Clicks: ${clicks}`);

      } catch (err) {
        console.log(`  ✗ Error: ${err.message}`);
        pins.push({
          pinId: pinUrl.match(/\/pin\/(\d+)/)?.[1] || '',
          pinUrl,
          title: '',
          destUrl: '',
          analytics: { clicks: 0, impressions: 0, saves: 0 },
          content: null,
          error: err.message
        });
      }

      // Small delay between pins
      await page.waitForTimeout(500);
    }

    // Save results
    fs.writeFileSync(OUTPUT_FILE, JSON.stringify(pins, null, 2));
    console.log(`\n✅ Saved ${pins.length} pins to ${OUTPUT_FILE}`);

    // Summary
    const zeroClicks = pins.filter(p => p.analytics.clicks === 0).length;
    console.log(`\n📊 Summary:`);
    console.log(`  Total pins: ${pins.length}`);
    console.log(`  Zero clicks: ${zeroClicks}`);
    console.log(`  With clicks: ${pins.length - zeroClicks}`);

  } catch (error) {
    console.error('❌ Error:', error);
  } finally {
    await context.close();
  }
}

scrapeBoardAnalytics();
