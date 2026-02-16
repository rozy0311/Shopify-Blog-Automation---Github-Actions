#!/usr/bin/env python3
"""_expand_low_words.py — Expand articles that fall below the minimum word count.

Uses a multi-provider LLM fallback chain with DUAL Gemini API keys
to generate additional high-quality content sections and pad articles
to the required 1800+ word minimum.

Fallback order:
  1. GitHub Models (gpt-4o-mini)     — fast, cheap, good quality
  2. gemini-2.5-pro (primary key)    — heavyweight, best expansion quality
  3. gemini-2.5-pro (fallback key)
  4. gemini-2.0-flash (primary key)
  5. gemini-2.0-flash (fallback key)
  6. gemini-2.5-flash-lite (primary key)
  7. gemini-2.5-flash-lite (fallback key)
  8. gemini-2.5-flash (primary key)
  9. gemini-2.5-flash (fallback key)
  10. gemini-2.0-flash-lite (primary key)
  11. gemini-2.0-flash-lite (fallback key)

Each Gemini model is tried with PRIMARY key first, then FALLBACK key,
exhausting all Gemini models before moving to external providers.
"""

from __future__ import annotations

import os
import re
import sys
import time
import random
import argparse

try:
    import requests
except ImportError:
    print("⚠️ requests not installed. Run: pip install requests")
    sys.exit(1)

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None

# ── Environment / Keys ──────────────────────────────────────────────
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "") or os.environ.get(
    "GOOGLE_AI_STUDIO_API_KEY", ""
)
FALLBACK_GEMINI_API_KEY = os.environ.get("FALLBACK_GEMINI_API_KEY", "") or os.environ.get(
    "FALLBACK_GOOGLE_AI_STUDIO_API_KEY", ""
)

GH_MODELS_API_KEY = os.environ.get("GH_MODELS_API_KEY", "")
GH_MODELS_API_BASE = os.environ.get(
    "GH_MODELS_API_BASE", "https://models.github.ai/inference"
)
GH_MODELS_MODEL = os.environ.get("GH_MODELS_MODEL_EXPAND", "gpt-4o-mini")

GEMINI_DELAY_SECONDS = float(os.environ.get("GEMINI_DELAY_SECONDS", "2.0"))
LLM_MAX_OUTPUT_TOKENS = int(os.environ.get("LLM_MAX_OUTPUT_TOKENS", "7000"))

# ── Gemini models for expansion (ordered) ───────────────────────────
EXPAND_GEMINI_MODELS = [
    "gemini-2.5-pro",
    "gemini-2.0-flash",
    "gemini-2.5-flash-lite",
    "gemini-2.5-flash",
    "gemini-2.0-flash-lite",
]

# Minimum word count — articles below this will be expanded
HARD_MIN_WORDS = 1800
TARGET_WORDS = 2200  # We aim for this (buffer above minimum)


def _word_count(html: str) -> int:
    """Count words in HTML content."""
    if BeautifulSoup:
        soup = BeautifulSoup(html, "html.parser")
        text = soup.get_text(separator=" ", strip=True)
    else:
        text = re.sub(r"<[^>]+>", " ", html)
    return len(text.split())


def _mask_secrets(text: str) -> str:
    """Mask API keys in error messages."""
    for key_val in [GEMINI_API_KEY, FALLBACK_GEMINI_API_KEY, GH_MODELS_API_KEY]:
        if key_val and len(key_val) > 8:
            text = text.replace(key_val, key_val[:4] + "****" + key_val[-4:])
    return text


# ═══════════════════════════════════════════════════════════════
# LLM PROVIDERS
# ═══════════════════════════════════════════════════════════════


def _call_github_models(prompt: str, max_tokens: int = 5000) -> str:
    """Call GitHub Models API (gpt-4o-mini) — fast, cheap, first choice for expansion."""
    if not GH_MODELS_API_KEY:
        print("⚠️ GH_MODELS_API_KEY not set, skipping GitHub Models")
        return ""

    endpoint = f"{GH_MODELS_API_BASE}/chat/completions"
    headers = {
        "Authorization": f"Bearer {GH_MODELS_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": GH_MODELS_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": 0.7,
    }

    try:
        resp = requests.post(endpoint, json=payload, headers=headers, timeout=120)
        if resp.status_code == 200:
            data = resp.json()
            choices = data.get("choices", [])
            if choices:
                return choices[0].get("message", {}).get("content", "")
        print(f"⚠️ GitHub Models ({GH_MODELS_MODEL}) error: {resp.status_code}")
    except Exception as e:
        print(f"⚠️ GitHub Models exception: {_mask_secrets(str(e))}")
    return ""


def _call_gemini(
    prompt: str,
    model: str,
    api_key: str,
    max_tokens: int = 5000,
    max_retries: int = 4,
) -> str:
    """Call Gemini API with retry logic for 429/5xx."""
    if not api_key:
        return ""

    endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": api_key,
    }
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "maxOutputTokens": max_tokens,
            "temperature": 0.7,
        },
    }

    if GEMINI_DELAY_SECONDS > 0:
        time.sleep(GEMINI_DELAY_SECONDS + random.uniform(0, 1))

    for attempt in range(max_retries):
        try:
            resp = requests.post(endpoint, json=payload, headers=headers, timeout=180)
            if resp.status_code == 200:
                data = resp.json()
                candidates = data.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    if parts:
                        return parts[0].get("text", "")
            elif resp.status_code == 429:
                wait = (2 ** attempt) * 15 + random.uniform(5, 15)
                print(
                    f"⚠️ Gemini {model} rate-limited (429), waiting {wait:.0f}s "
                    f"(attempt {attempt + 1}/{max_retries})"
                )
                time.sleep(wait)
                continue
            elif resp.status_code >= 500:
                wait = (2 ** attempt) * 2
                print(f"⚠️ Gemini {model} server error ({resp.status_code}), retry in {wait}s")
                time.sleep(wait)
                continue
            else:
                safe = _mask_secrets(resp.text[:300])
                print(f"⚠️ Gemini {model} error: {resp.status_code} — {safe}")
                return ""
        except requests.exceptions.Timeout:
            print(f"⚠️ Gemini {model} timeout (attempt {attempt + 1}/{max_retries})")
            if attempt < max_retries - 1:
                time.sleep(5)
                continue
        except Exception as e:
            print(f"⚠️ Gemini {model} exception: {_mask_secrets(str(e))}")
            return ""

    print(f"⚠️ Gemini {model} failed after {max_retries} retries")
    return ""


# ═══════════════════════════════════════════════════════════════
# EXPANSION PROMPT
# ═══════════════════════════════════════════════════════════════


def _build_expand_prompt(title: str, current_html: str, current_words: int) -> str:
    """Build a prompt to expand an article that is too short."""
    words_needed = TARGET_WORDS - current_words
    return f"""You are expanding an existing blog article that is too short.

ARTICLE TITLE: "{title}"
CURRENT WORD COUNT: {current_words} words (minimum required: {HARD_MIN_WORDS})
ADDITIONAL WORDS NEEDED: approximately {words_needed} words

EXISTING ARTICLE (do NOT repeat this content):
---
{current_html[:6000]}
---

TASK: Write ADDITIONAL sections to expand this article. The new content must:
1. Be directly relevant to "{title}" — no generic filler
2. Add NEW information not already covered above
3. Use proper HTML: <h2>, <h3>, <p>, <ul>, <li>, <blockquote>, <table>
4. Be specific with real data, measurements, and practical tips
5. Be approximately {words_needed} words

BANNED PHRASES — NEVER USE:
- "crucial to understand", "it's essential", "it is essential", "it's important"
- "in this guide", "this guide", "in this article", "this article"
- "we'll explore", "let's dive", "let's explore", "without further ado"
- "in conclusion", "to sum up", "in summary", "to summarize"
- "game-changer", "unlock the potential", "master the art", "elevate your"
- "happy growing", "happy gardening", "happy cooking", "thank you for reading"

SUGGESTED NEW SECTIONS (pick 2-4 that fit):
- <h2>Regional Variations</h2> — climate/region-specific advice
- <h2>Seasonal Calendar</h2> — month-by-month timeline
- <h2>Cost Analysis</h2> — budget breakdown with specific numbers
- <h2>Equipment & Tools</h2> — what you need with alternatives
- <h2>Common Mistakes to Avoid</h2> — specific pitfalls
- <h2>Long-Term Maintenance</h2> — ongoing care and monitoring
- <h2>Community Tips</h2> — advice from practitioners

Output ONLY the new HTML sections. Start with <h2>. No markdown, no code blocks, no explanations."""


def _clean_expansion(content: str) -> str:
    """Clean LLM expansion output."""
    # Remove markdown code blocks
    content = re.sub(r"^```html?\s*\n?", "", content, flags=re.MULTILINE)
    content = re.sub(r"\n?```\s*$", "", content, flags=re.MULTILINE)
    # Remove html/body wrappers
    content = re.sub(r"</?html[^>]*>", "", content, flags=re.IGNORECASE)
    content = re.sub(r"</?body[^>]*>", "", content, flags=re.IGNORECASE)
    content = re.sub(r"<head>.*?</head>", "", content, flags=re.DOTALL | re.IGNORECASE)
    return content.strip()


# ═══════════════════════════════════════════════════════════════
# MAIN FALLBACK CHAIN
# ═══════════════════════════════════════════════════════════════


def expand_article(title: str, current_html: str) -> str:
    """Expand an article that is below HARD_MIN_WORDS using the LLM fallback chain.

    Fallback order:
      1. GitHub Models (gpt-4o-mini)
      2-11. Gemini models × 2 keys (primary then fallback for each model)

    Returns the expanded HTML (original + new sections), or original if all fail.
    """
    current_words = _word_count(current_html)
    if current_words >= HARD_MIN_WORDS:
        print(f"✅ Article already at {current_words} words (≥ {HARD_MIN_WORDS}), no expansion needed")
        return current_html

    print(f"📝 Expanding article: \"{title}\" ({current_words}/{HARD_MIN_WORDS} words)")
    prompt = _build_expand_prompt(title, current_html, current_words)

    # ── 1. GitHub Models (gpt-4o-mini) — fast first attempt ──────────
    if GH_MODELS_API_KEY:
        print(f"🔄 [1] Trying GitHub Models ({GH_MODELS_MODEL})...")
        expansion = _call_github_models(prompt)
        if expansion and len(expansion) > 500:
            expansion = _clean_expansion(expansion)
            new_html = _insert_expansion(current_html, expansion)
            new_words = _word_count(new_html)
            if new_words >= HARD_MIN_WORDS:
                print(f"✅ Expanded to {new_words} words with GitHub Models ({GH_MODELS_MODEL})")
                return new_html
            print(f"⚠️ GitHub Models expansion too short ({new_words} words), trying next...")
    else:
        print("⚠️ GH_MODELS_API_KEY not set, skipping GitHub Models")

    # ── 2-11. Gemini models × dual key ──────────────────────────────
    step = 2
    for model_name in EXPAND_GEMINI_MODELS:
        for key_label, api_key in [("primary", GEMINI_API_KEY), ("fallback", FALLBACK_GEMINI_API_KEY)]:
            if not api_key:
                print(f"⚠️ [{step}] Gemini {key_label} key not set, skipping")
                step += 1
                continue

            print(f"🔄 [{step}] Trying Gemini {model_name} ({key_label} key)...")
            expansion = _call_gemini(prompt, model_name, api_key)
            if expansion and len(expansion) > 500:
                expansion = _clean_expansion(expansion)
                new_html = _insert_expansion(current_html, expansion)
                new_words = _word_count(new_html)
                if new_words >= HARD_MIN_WORDS:
                    print(f"✅ Expanded to {new_words} words with Gemini {model_name} ({key_label} key)")
                    return new_html
                print(f"⚠️ Gemini {model_name} expansion too short ({new_words} words), trying next...")
            step += 1

    print(f"❌ All providers exhausted. Article remains at {current_words} words.")
    return current_html


def _insert_expansion(original_html: str, expansion_html: str) -> str:
    """Insert expansion content before the Sources/FAQ section, or at the end."""
    # Try to insert before Sources & Further Reading
    patterns = [
        r"(<h2[^>]*>\s*Sources\s*(?:&amp;|&)\s*Further\s*Reading\s*</h2>)",
        r"(<h2[^>]*>\s*Frequently\s*Asked\s*Questions?\s*</h2>)",
        r"(<h2[^>]*>\s*FAQ\s*</h2>)",
        r"(</article>)",
    ]
    for pat in patterns:
        match = re.search(pat, original_html, re.IGNORECASE)
        if match:
            insert_pos = match.start()
            return original_html[:insert_pos] + "\n" + expansion_html + "\n" + original_html[insert_pos:]

    # Fallback: append at end
    return original_html + "\n" + expansion_html


# ═══════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════


def _print_chain():
    """Print the configured fallback chain."""
    pk = "✅" if GEMINI_API_KEY else "❌"
    fk = "✅" if FALLBACK_GEMINI_API_KEY else "❌"
    gh = "✅" if GH_MODELS_API_KEY else "❌"
    print("🔧 _expand_low_words.py — LLM Fallback Chain:")
    print(f"   1. GitHub Models: {GH_MODELS_MODEL} (key: {gh})")
    step = 2
    for model in EXPAND_GEMINI_MODELS:
        print(f"   {step}. Gemini: {model} (primary key: {pk})")
        step += 1
        print(f"   {step}. Gemini: {model} (fallback key: {fk})")
        step += 1
    print(f"   Total: {step - 1} fallback slots")


def main():
    parser = argparse.ArgumentParser(
        description="Expand articles below minimum word count using LLM fallback chain"
    )
    parser.add_argument("--chain", action="store_true", help="Print the fallback chain and exit")
    parser.add_argument("--file", type=str, help="Path to HTML file to expand")
    parser.add_argument("--title", type=str, default="", help="Article title (for LLM context)")
    parser.add_argument("--min-words", type=int, default=HARD_MIN_WORDS, help=f"Minimum word count (default: {HARD_MIN_WORDS})")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be expanded without writing")
    args = parser.parse_args()

    if args.chain:
        _print_chain()
        return

    if not args.file:
        print("❌ --file is required. Usage: python _expand_low_words.py --file article.html --title 'My Article'")
        sys.exit(1)

    if not os.path.exists(args.file):
        print(f"❌ File not found: {args.file}")
        sys.exit(1)

    with open(args.file, "r", encoding="utf-8") as f:
        html = f.read()

    current_words = _word_count(html)
    print(f"📊 Current: {current_words} words | Minimum: {args.min_words}")

    if current_words >= args.min_words:
        print(f"✅ Already at {current_words} words. No expansion needed.")
        return

    title = args.title or os.path.splitext(os.path.basename(args.file))[0].replace("-", " ").title()
    expanded = expand_article(title, html)

    new_words = _word_count(expanded)
    if new_words > current_words:
        if args.dry_run:
            print(f"🔍 DRY RUN: Would expand from {current_words} → {new_words} words (+{new_words - current_words})")
        else:
            with open(args.file, "w", encoding="utf-8") as f:
                f.write(expanded)
            print(f"✅ Expanded: {current_words} → {new_words} words (+{new_words - current_words})")
    else:
        print(f"❌ Could not expand article (still at {current_words} words)")
        sys.exit(1)


if __name__ == "__main__":
    main()
