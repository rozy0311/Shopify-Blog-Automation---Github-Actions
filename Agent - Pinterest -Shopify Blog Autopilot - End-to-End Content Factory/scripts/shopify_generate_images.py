"""
Shopify Magic Image Generator - UI Automation (Stealth Mode)

Uses Playwright with stealth to automate Shopify's built-in AI image generation.
This saves API costs by using Shopify's free AI image feature.

Usage:
    python scripts/shopify_generate_images.py <article_id>

Example:
    python scripts/shopify_generate_images.py 690495095102

Requirements:
    pip install playwright playwright-stealth
    playwright install chromium
"""

import asyncio
import json
import os
import sys
import time
from pathlib import Path

# Check if playwright is installed
try:
    from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout
    from playwright_stealth import stealth_async
except ImportError:
    print("ERROR: Playwright not installed. Run:")
    print("  pip install playwright playwright-stealth")
    print("  playwright install chromium")
    sys.exit(1)

# Paths
SCRIPT_DIR = Path(__file__).parent
ROOT_DIR = SCRIPT_DIR.parent
CONFIG_PATH = ROOT_DIR / "SHOPIFY_PUBLISH_CONFIG.json"
# Use persistent Chrome profile to avoid bot detection
CHROME_PROFILE_PATH = ROOT_DIR / "shopify_stealth_profile"


def load_config() -> dict:
    """Load Shopify config."""
    if CONFIG_PATH.exists():
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    return {}


async def login_shopify(page, shop_domain: str):
    """Login to Shopify admin (manual first time, then reuses session)."""
    admin_url = f"https://{shop_domain}/admin"

    print(f"Navigating to {admin_url}...")
    await page.goto(admin_url, wait_until="networkidle")
    await asyncio.sleep(2)

    # Check if already logged in (look for admin dashboard elements)
    current_url = page.url.lower()
    if (
        "admin.shopify.com" in current_url
        and "login" not in current_url
        and "verify" not in current_url
    ):
        print("Already logged in!")
        return True

    # Check for human verification
    if "verify" in current_url or "captcha" in current_url:
        print("\n" + "=" * 60)
        print("HUMAN VERIFICATION REQUIRED")
        print("=" * 60)
        print("Please complete the verification in the browser window.")
        print("The script will continue automatically after verification.")
        print("=" * 60 + "\n")

        # Wait for verification to complete
        try:
            await page.wait_for_url(
                lambda url: "admin.shopify.com" in url and "verify" not in url.lower(),
                timeout=180000,  # 3 minutes for verification
            )
            print("Verification complete!")
            return True
        except PlaywrightTimeout:
            print("ERROR: Verification timeout.")
            return False

    # Need manual login
    print("\n" + "=" * 60)
    print("MANUAL LOGIN REQUIRED")
    print("=" * 60)
    print("Please log in to Shopify in the browser window.")
    print("The script will continue automatically after login.")
    print("=" * 60 + "\n")

    # Wait for successful login (URL changes to admin dashboard)
    try:
        await page.wait_for_url(
            lambda url: "/admin" in url and "login" not in url.lower(),
            timeout=120000,  # 2 minutes for manual login
        )
        print("Login successful!")
        return True
    except PlaywrightTimeout:
        print("ERROR: Login timeout. Please try again.")
        return False


async def navigate_to_article(page, shop_domain: str, article_id_or_handle: str):
    """Navigate to the article edit page by ID or handle."""

    # If it's a numeric ID, go directly to the article
    if article_id_or_handle.isdigit():
        article_url = f"https://{shop_domain}/admin/articles/{article_id_or_handle}"
        print(f"Navigating directly to article: {article_url}")
        await page.goto(article_url, wait_until="networkidle")
        await asyncio.sleep(3)

        # Debug: print current URL
        print(f"Current URL: {page.url}")

        # Check if we landed on the article page (could be /admin/blog/articles/xxx)
        if "/article" in page.url.lower() or "edit" in page.url.lower():
            print("Article page loaded!")
            return True
        else:
            print(f"Unexpected page. Trying blog articles path...")
            # Try alternative path with blog
            alt_url = f"https://{shop_domain}/admin/blogs/sustainable-living/articles/{article_id_or_handle}"
            print(f"Trying: {alt_url}")
            await page.goto(alt_url, wait_until="networkidle")
            await asyncio.sleep(2)
            print(f"Current URL: {page.url}")
            if "/article" in page.url.lower():
                return True
            return False

    # Otherwise search by handle
    articles_url = f"https://{shop_domain}/admin/articles"

    print(f"Navigating to articles list...")
    await page.goto(articles_url, wait_until="networkidle")
    await asyncio.sleep(2)

    # Search for the article
    print(f"Searching for article: {article_id_or_handle}...")

    # Click search and type article handle
    search_input = page.locator('[placeholder*="Search"]').first
    if await search_input.is_visible():
        await search_input.fill(article_handle.replace("-", " ")[:30])
        await asyncio.sleep(2)

    # Click on the article in results
    article_link = page.locator(
        f'a:has-text("{article_handle.replace("-", " ")[:20]}")'
    ).first
    if await article_link.is_visible(timeout=5000):
        await article_link.click()
        await page.wait_for_load_state("networkidle")
        print("Article found and opened!")
        return True

    # Alternative: try direct URL pattern
    # Shopify article URLs: /admin/articles/<id>
    print("Trying to find article via list...")

    # Look for any article link containing the handle text
    article_title = article_handle.replace("-", " ").title()
    links = page.locator("table a, [data-polaris-unstyled] a")
    count = await links.count()

    for i in range(min(count, 20)):  # Check first 20 links
        link = links.nth(i)
        text = await link.text_content()
        if text and article_handle.replace("-", " ")[:15].lower() in text.lower():
            await link.click()
            await page.wait_for_load_state("networkidle")
            print(f"Found article: {text}")
            return True

    print(f"WARNING: Could not find article with handle: {article_handle}")
    return False


async def generate_images_via_magic(page):
    """Click Shopify Magic generate images button and wait for generation."""
    print("\nLooking for image generation options...")

    # Wait for page to fully load
    await asyncio.sleep(2)

    # Look for "Add media" or image section
    add_media_btn = page.locator(
        'button:has-text("Add media"), button:has-text("Add image")'
    )
    if await add_media_btn.is_visible(timeout=5000):
        print("Found 'Add media' button, clicking...")
        await add_media_btn.click()
        await asyncio.sleep(1)

    # Look for "Generate" or Shopify Magic option
    generate_selectors = [
        'button:has-text("Generate")',
        'button:has-text("Magic")',
        '[data-testid*="generate"]',
        'button:has-text("AI")',
        'button[aria-label*="generate"]',
        '.Polaris-Button:has-text("Generate")',
    ]

    for selector in generate_selectors:
        btn = page.locator(selector).first
        if await btn.is_visible(timeout=2000):
            print(f"Found generate button, clicking...")
            await btn.click()
            await asyncio.sleep(2)
            break
    else:
        # Try looking in dropdown/menu
        more_actions = page.locator(
            'button:has-text("More actions"), button[aria-label="More"]'
        )
        if await more_actions.is_visible(timeout=2000):
            await more_actions.click()
            await asyncio.sleep(1)

            generate_option = page.locator(
                'button:has-text("Generate"), [role="menuitem"]:has-text("Generate")'
            )
            if await generate_option.is_visible(timeout=2000):
                await generate_option.click()
                await asyncio.sleep(2)

    # Wait for generation to complete (look for loading indicator to disappear)
    print("Waiting for image generation...")

    # Look for loading indicators
    loading_indicators = [
        '[data-testid*="loading"]',
        ".Polaris-Spinner",
        '[aria-busy="true"]',
    ]

    for _ in range(30):  # Wait up to 30 seconds
        is_loading = False
        for indicator in loading_indicators:
            if await page.locator(indicator).is_visible(timeout=500):
                is_loading = True
                break

        if not is_loading:
            break

        print(".", end="", flush=True)
        await asyncio.sleep(1)

    print("\nImage generation attempt complete!")
    return True


async def save_article(page):
    """Click Save button to save the article with new images."""
    save_btn = page.locator(
        'button:has-text("Save"), button[type="submit"]:has-text("Save")'
    )

    if await save_btn.is_visible(timeout=5000):
        print("Saving article...")
        await save_btn.click()
        await asyncio.sleep(3)

        # Wait for save confirmation
        try:
            await page.wait_for_selector(
                '[aria-label*="saved"], .Polaris-Toast, [data-testid*="success"]',
                timeout=10000,
            )
            print("Article saved successfully!")
        except PlaywrightTimeout:
            print("Save might have completed (no confirmation detected)")

        return True

    print("WARNING: Could not find Save button")
    return False


async def main(article_handle: str):
    """Main automation flow."""
    config = load_config()
    shop_domain = config.get("shop", {}).get("domain", "")

    if not shop_domain:
        print("ERROR: No shop domain in config")
        sys.exit(1)

    print(f"Shop: {shop_domain}")
    print(f"Article: {article_handle}")
    print("=" * 60)

    async with async_playwright() as p:
        # Use persistent context with stealth to avoid bot detection
        # This uses a real Chrome profile that persists cookies and fingerprint

        print(f"Using persistent profile at: {CHROME_PROFILE_PATH}")

        context = await p.chromium.launch_persistent_context(
            user_data_dir=str(CHROME_PROFILE_PATH),
            headless=False,  # Must be visible for manual verification
            slow_mo=150,  # Human-like speed
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--no-sandbox",
            ],
            ignore_default_args=["--enable-automation"],
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        )

        page = context.pages[0] if context.pages else await context.new_page()

        # Apply stealth to avoid detection
        await stealth_async(page)

        try:
            # Step 1: Login
            if not await login_shopify(page, shop_domain):
                print("Login failed, exiting.")
                return

            # Step 2: Navigate to article
            if not await navigate_to_article(page, shop_domain, article_handle):
                print("Could not find article, exiting.")
                return

            # Step 3: Generate images
            await generate_images_via_magic(page)

            # Step 4: Save
            await save_article(page)

            print("\n" + "=" * 60)
            print("DONE! Check the article in Shopify admin.")
            print("=" * 60)

            # Keep browser open for verification
            print("\nBrowser will close in 10 seconds...")
            await asyncio.sleep(10)

        finally:
            await context.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/shopify_generate_images.py <article_id>")
        print("Example: python scripts/shopify_generate_images.py 690495095102")
        sys.exit(1)

    article_handle = sys.argv[1]
    asyncio.run(main(article_handle))
