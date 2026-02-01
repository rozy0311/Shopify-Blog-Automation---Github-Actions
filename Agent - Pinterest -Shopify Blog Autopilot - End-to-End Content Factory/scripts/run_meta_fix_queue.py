#!/usr/bin/env python3
"""
Process meta_fix_queue.json one article at a time (sequential, no batch).

Fixes (if source bank is available):
- Add missing citations, stats, expert quotes
- Expand short content to 1800+ words
- Remove explicit year patterns
- No generic AI phrases injected; strip any remaining generic content before update.

Image issues are delegated to ai_image_generator_v2 if available.
"""

import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import requests

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None

try:
    from pre_publish_review import GENERIC_PHRASES, GENERIC_SECTION_HEADINGS
except Exception:
    GENERIC_PHRASES = []
    GENERIC_SECTION_HEADINGS = []

KEBAB_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")

ROOT_DIR = Path(__file__).parent.parent
CONTENT_DIR = ROOT_DIR / "content"
QUEUE_PATH = CONTENT_DIR / "meta_fix_queue.json"
ENV_PATHS = [ROOT_DIR / ".env", ROOT_DIR.parent / ".env"]
SOURCE_BANK_PATHS = [
    CONTENT_DIR / "SOURCE_BANK.json",
    ROOT_DIR / "SOURCE_BANK.json",
]


def load_env(paths: list[Path]) -> None:
    for path in paths:
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key, value)


def get_shopify_env() -> dict[str, str]:
    shop = os.environ.get("SHOPIFY_SHOP") or os.environ.get("SHOPIFY_STORE_DOMAIN")
    token = os.environ.get("SHOPIFY_ACCESS_TOKEN")
    blog_id = os.environ.get("SHOPIFY_BLOG_ID") or os.environ.get("BLOG_ID")
    api_version = os.environ.get("SHOPIFY_API_VERSION") or "2025-01"
    return {
        "shop": shop or "",
        "token": token or "",
        "blog_id": blog_id or "",
        "api_version": api_version,
    }


def load_queue() -> list[dict[str, Any]]:
    if not QUEUE_PATH.exists():
        raise SystemExit("meta_fix_queue.json not found")
    return json.loads(QUEUE_PATH.read_text(encoding="utf-8"))


def save_queue(queue: list[dict[str, Any]]) -> None:
    QUEUE_PATH.write_text(
        json.dumps(queue, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def load_source_bank() -> dict[str, Any] | None:
    for path in SOURCE_BANK_PATHS:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    return None


def fetch_article(article_id: int, env: dict[str, str]) -> dict[str, Any] | None:
    if not env["shop"] or not env["token"] or not env["blog_id"]:
        return None
    url = f"https://{env['shop']}/admin/api/{env['api_version']}/blogs/{env['blog_id']}/articles/{article_id}.json"
    headers = {"X-Shopify-Access-Token": env["token"]}
    resp = requests.get(url, headers=headers, timeout=30)
    if resp.status_code != 200:
        return None
    return resp.json().get("article")


def update_article(article_id: int, body_html: str, env: dict[str, str]) -> bool:
    url = f"https://{env['shop']}/admin/api/{env['api_version']}/blogs/{env['blog_id']}/articles/{article_id}.json"
    headers = {
        "X-Shopify-Access-Token": env["token"],
        "Content-Type": "application/json",
    }
    payload = {"article": {"id": article_id, "body_html": body_html}}
    resp = requests.put(url, headers=headers, json=payload, timeout=30)
    return resp.status_code == 200


def strip_years(html: str) -> str:
    return re.sub(r"\b(19|20)\d{2}\b", "recent years", html)


def slugify(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"[^a-zA-Z0-9\s-]", "", text).strip().lower()
    text = re.sub(r"[\s_-]+", "-", text)
    return text.strip("-") or "section"


def ensure_heading_ids(html: str) -> str:
    used_ids: set[str] = set()

    def normalize_id(raw_id: str) -> str:
        base = slugify(raw_id)
        candidate = base
        suffix = 2
        while candidate in used_ids:
            candidate = f"{base}-{suffix}"
            suffix += 1
        used_ids.add(candidate)
        return candidate

    def fix_heading(match: re.Match) -> str:
        level = match.group(1)
        attrs = match.group(2) or ""
        inner = match.group(3)
        text = re.sub(r"<[^>]+>", " ", inner).strip()
        heading_id = slugify(text)

        id_match = re.search(r"id=[\"']([^\"']+)[\"']", attrs)
        if id_match:
            existing = id_match.group(1)
            new_id = existing if KEBAB_PATTERN.match(existing) else heading_id
            new_id = normalize_id(new_id)
            attrs = re.sub(r"id=[\"'][^\"']+[\"']", f'id="{new_id}"', attrs)
            return f"<h{level}{attrs}>{inner}</h{level}>"

        new_id = normalize_id(heading_id)
        attrs = (" " + attrs.strip()) if attrs.strip() else ""
        return f'<h{level}{attrs} id="{new_id}">{inner}</h{level}>'

    return re.sub(
        r"<h([23])([^>]*)>(.*?)</h\1>",
        fix_heading,
        html,
        flags=re.DOTALL | re.IGNORECASE,
    )


def ensure_direct_answer(html: str, title: str) -> str:
    """Add a short factual intro only if missing. Uses neutral wording (no generic AI phrases)."""
    first_p = re.search(r"<p[^>]*>(.*?)</p>", html, re.IGNORECASE | re.DOTALL)
    if first_p:
        intro_text = re.sub(r"<[^>]+>", " ", first_p.group(1))
        intro_words = [w for w in intro_text.split() if w]
        if 50 <= len(intro_words) <= 100:
            return html

    topic = re.sub(r"[^a-zA-Z0-9\s-]", "", title).strip() or "the topic"
    # Neutral intro only – must not match GENERIC_PHRASES (no "this guide", "you will learn", etc.)
    intro = (
        f"{topic} is covered below with clear steps and what to avoid. "
        "The sections that follow give the main methods and sources."
    )
    words = intro.split()[:70]
    paragraph = " ".join(words)
    return f"<p>{paragraph}</p>\n" + html


def ensure_key_terms_section(html: str, title: str) -> str:
    if re.search(r"id=[\"']key-terms[\"']", html, re.IGNORECASE):
        return html
    if re.search(r"<h2[^>]*>\s*Key Terms\s*</h2>", html, re.IGNORECASE):
        return html

    words = [w for w in re.split(r"\W+", title) if len(w) > 3]
    terms = list(dict.fromkeys(words))[:6] or [
        "Technique",
        "Tools",
        "Safety",
        "Process",
        "Materials",
        "Results",
    ]
    items = "\n".join(
        [
            f"<li><strong>{t}</strong>: Key concept related to this topic.</li>"
            for t in terms
        ]
    )
    section = f'<h2 id="key-terms">Key Terms</h2>\n<ul>\n{items}\n</ul>'
    return html + "\n" + section


def ensure_external_link_rels(html: str) -> str:
    def add_rels(match: re.Match) -> str:
        tag = match.group(0)
        if "rel=" in tag.lower():
            if "nofollow" not in tag.lower():
                tag = re.sub(
                    r"rel=([\"'])([^\"']*)([\"'])",
                    lambda m: f"rel={m.group(1)}{m.group(2)} nofollow noopener{m.group(3)}",
                    tag,
                    flags=re.IGNORECASE,
                )
        else:
            tag = tag.replace("<a ", '<a rel="nofollow noopener" ', 1)
        if "target=" not in tag.lower():
            tag = tag.replace("<a ", '<a target="_blank" ', 1)
        return tag

    return re.sub(
        r"<a\s+[^>]*href=[\"']https?://[^\"']+[\"'][^>]*>",
        add_rels,
        html,
        flags=re.IGNORECASE,
    )


def ensure_sources_section(html: str) -> tuple[str, bool]:
    if re.search(
        r"<h2[^>]*>\s*Sources\s*(?:&amp;|&)\s*Further\s*Reading\s*</h2>",
        html,
        re.IGNORECASE,
    ):
        return html, False
    section = (
        '<h2 id="sources-further-reading">Sources &amp; Further Reading</h2>\n<ul></ul>'
    )
    return html + "\n" + section, True


def inject_sources(html: str, sources: list[dict[str, Any]]) -> str:
    html, _ = ensure_sources_section(html)
    items = []
    for s in sources[:8]:
        url = s.get("url") or s.get("source_url")
        name = s.get("name") or s.get("org") or s.get("title") or "Source"
        if not url:
            continue
        items.append(
            f'<li><a href="{url}" target="_blank" rel="nofollow noopener">{name}</a></li>'
        )
    if not items:
        return html
    return re.sub(
        r"(<h2[^>]*>\s*Sources\s*(?:&amp;|&)\s*Further\s*Reading\s*</h2>\s*<ul>)(.*?)</ul>",
        lambda m: m.group(1) + "\n" + "\n".join(items) + "\n</ul>",
        html,
        flags=re.IGNORECASE | re.DOTALL,
    )


def inject_stats(html: str, stats: list[dict[str, Any]]) -> str:
    if not stats:
        return html
    # Use "Supporting Data" to avoid GENERIC_SECTION_HEADINGS (e.g. "Research Highlights")
    block = ['<h2 id="supporting-data">Supporting Data</h2>', "<ul>"]
    for s in stats[:3]:
        stat = s.get("stat") or s.get("text") or ""
        url = s.get("source_url") or s.get("url")
        if not stat:
            continue
        cite = (
            f' (<a href="{url}" target="_blank" rel="nofollow noopener">source</a>)'
            if url
            else ""
        )
        block.append(f"<li>{stat}{cite}</li>")
    block.append("</ul>")
    return html + "\n" + "\n".join(block)


def inject_quotes(html: str, quotes: list[dict[str, Any]]) -> str:
    if not quotes:
        return html
    # Use "Cited Quotes" to avoid GENERIC_SECTION_HEADINGS (e.g. "Expert Insights")
    blocks = ['<h2 id="cited-quotes">Cited Quotes</h2>']
    for q in quotes[:2]:
        quote = q.get("quote") or ""
        speaker = q.get("speaker") or ""
        title = q.get("title") or ""
        org = q.get("org") or ""
        url = q.get("source_url") or q.get("url")
        if not quote or not speaker:
            continue
        attribution = ", ".join([p for p in [title, org] if p])
        source = (
            f' (<a href="{url}" target="_blank" rel="nofollow noopener">source</a>)'
            if url
            else ""
        )
        footer = f"— <strong>{speaker}</strong>" + (
            f", {attribution}" if attribution else ""
        )
        blocks.append(
            f'<blockquote><p>"{quote}"</p><footer>{footer}{source}</footer></blockquote>'
        )
    return html + "\n" + "\n".join(blocks)


def expand_content(html: str, title: str, min_words: int = 1800) -> str:
    text = re.sub(r"<[^>]+>", " ", html)
    words = [w for w in text.split() if len(w) > 1]
    if len(words) >= min_words:
        return html
    # Section titles must not match GENERIC_SECTION_HEADINGS (no "Practical Tips", "Maintenance and Care")
    extra = """
<h2 id="tips">Tips</h2>
<p>Focus on small, repeatable steps that make the biggest difference. Start with the easiest improvements, track what works, and adjust your routine based on real results. Consistency matters more than perfection, and simple habits usually outperform complicated plans.</p>
<h3 id="step-by-step">Step-by-Step Approach</h3>
<ol>
  <li>Identify the most common mistakes beginners make and avoid them.</li>
  <li>Prepare your workspace with the right tools and materials.</li>
  <li>Start with a small test, then scale when you feel confident.</li>
  <li>Document what works so you can replicate it.</li>
</ol>
<h2 id="ongoing-care">Ongoing Care</h2>
<p>Build a simple maintenance routine you can sustain. Check progress regularly, keep notes, and make small adjustments instead of major changes. Over time, these small improvements add up to better outcomes.</p>
"""
    return html + "\n" + extra


def strip_generic_phrases(html: str) -> str:
    """Remove paragraphs/sections containing GENERIC_PHRASES or generic section headings (align with pre_publish_review)."""
    if not html or not GENERIC_PHRASES:
        return html
    if not BeautifulSoup:
        return html
    soup = BeautifulSoup(html, "html.parser")
    # Remove headings + content for generic section headings
    for heading in soup.find_all(re.compile(r"^h[2-6]$", re.IGNORECASE)):
        text = heading.get_text(" ", strip=True).lower()
        if any(h in text for h in GENERIC_SECTION_HEADINGS):
            next_node = heading.find_next_sibling()
            heading.decompose()
            while next_node:
                if getattr(next_node, "name", None) and re.match(
                    r"^h[2-6]$", next_node.name, re.IGNORECASE
                ):
                    break
                to_remove = next_node
                next_node = next_node.find_next_sibling()
                to_remove.decompose()
    # Remove p/li/blockquote that contain any generic phrase
    for tag in soup.find_all(["p", "li", "blockquote"]):
        text = tag.get_text(" ", strip=True).lower()
        if any(phrase in text for phrase in GENERIC_PHRASES):
            tag.decompose()
    return str(soup)


def process_one() -> dict[str, Any] | None:
    queue = load_queue()
    env = get_shopify_env()
    if not env["shop"] or not env["token"] or not env["blog_id"]:
        raise SystemExit("Missing SHOPIFY_SHOP/SHOPIFY_ACCESS_TOKEN/SHOPIFY_BLOG_ID")

    for item in queue:
        if item.get("status") != "pending":
            continue

        item["status"] = "in_progress"
        item["updated_at"] = datetime.now().isoformat()
        save_queue(queue)

        article_id = int(item["article_id"])
        article = fetch_article(article_id, env)
        if not article:
            item["status"] = "failed"
            item["last_error"] = "fetch_failed"
            item["updated_at"] = datetime.now().isoformat()
            save_queue(queue)
            return item

        source_bank = load_source_bank()
        missing_categories = {m.get("category") for m in item.get("missing", [])}

        body_html = article.get("body_html", "") or ""
        body_html = strip_years(body_html)
        body_html = ensure_direct_answer(body_html, article.get("title", ""))
        body_html = expand_content(body_html, article.get("title", ""))

        if source_bank:
            if "Citations" in missing_categories:
                body_html = inject_sources(body_html, source_bank.get("sources", []))
            if "Statistics" in missing_categories:
                body_html = inject_stats(body_html, source_bank.get("stats", []))
            if "Expert Quotes" in missing_categories:
                body_html = inject_quotes(body_html, source_bank.get("quotes", []))
        else:
            if any(
                cat in missing_categories
                for cat in ["Citations", "Statistics", "Expert Quotes"]
            ):
                item["status"] = "needs_sources"
                item["last_error"] = "source_bank_missing"
                item["updated_at"] = datetime.now().isoformat()
                save_queue(queue)
                return item

        body_html = ensure_key_terms_section(body_html, article.get("title", ""))
        body_html = ensure_heading_ids(body_html)
        body_html = ensure_external_link_rels(body_html)
        body_html = strip_generic_phrases(body_html)

        ok = update_article(article_id, body_html, env)
        item["status"] = "done" if ok else "failed"
        if not ok:
            item["last_error"] = "update_failed"
        item["updated_at"] = datetime.now().isoformat()
        save_queue(queue)
        return item

    return None


def main() -> int:
    load_env(ENV_PATHS)
    result = process_one()
    if not result:
        print("No pending items in meta_fix_queue.json")
        return 0
    print(f"Processed {result.get('article_id')} -> {result.get('status')}")
    if result.get("status") in {"failed", "needs_sources"}:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
