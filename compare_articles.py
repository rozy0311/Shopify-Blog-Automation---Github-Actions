#!/usr/bin/env python3
import sys

sys.path.insert(
    0,
    "Agent - Pinterest -Shopify Blog Autopilot - End-to-End Content Factory/pipeline_v2",
)
import re
from ai_orchestrator import AIOrchestrator

o = AIOrchestrator()

# Get both articles
bad = o.api.get_article("691790905662")  # Bay leaves - BAD
good = o.api.get_article("690496602430")  # Yogurt - GOOD

bad_body = bad.get("body_html", "")
good_body = good.get("body_html", "")

print("=== COMPARISON ===")
print()
print("BAD ARTICLE (Bay Leaves):")
print("  - Title:", bad.get("title", ""))
print("  - Length:", len(bad_body), "chars")
print("  - Word count (approx):", len(bad_body.split()))
print()
print("GOOD ARTICLE (Yogurt):")
print("  - Title:", good.get("title", ""))
print("  - Length:", len(good_body), "chars")
print("  - Word count (approx):", len(good_body.split()))
print()

# Check for issues in bad article
bad_title = bad.get("title", "")
title_count = bad_body.lower().count(bad_title.lower())
print(f'ISSUE: Title "{bad_title[:40]}..." appears {title_count} times in body')

# Check for placeholder
if "{topic}" in bad_body:
    print("ISSUE: Contains {topic} placeholder!")

# Check generic phrases
generic_phrases = [
    "actionable, ways, use",
    "directly support actionable",
    "match size to actionable",
    "a key component in",
]
for g in generic_phrases:
    if g in bad_body.lower():
        print(f'ISSUE: Contains generic phrase: "{g}"')

# Check for repeated "Note X: In ... should be checked"
note_pattern = r"Note \d+: In .* should be checked"
notes = re.findall(note_pattern, bad_body)
if notes:
    print(f'ISSUE: Contains {len(notes)} generic "Note X" patterns')

print()
print("=" * 60)
print("KEY TERMS COMPARISON")
print("=" * 60)

# Check Key Terms
kt_bad = re.search(r"Key Terms</h2>(.*?)<h2", bad_body, re.DOTALL | re.IGNORECASE)
kt_good = re.search(r"Key Terms</h2>(.*?)<h2", good_body, re.DOTALL | re.IGNORECASE)

if kt_bad:
    print()
    print("BAD Key Terms:")
    print(kt_bad.group(1)[:800])

if kt_good:
    print()
    print("GOOD Key Terms:")
    print(kt_good.group(1)[:800])

print()
print("=" * 60)
print("DIRECT ANSWER COMPARISON")
print("=" * 60)

# Direct Answer
da_bad = re.search(r"Direct Answer</h2>(.*?)<h2", bad_body, re.DOTALL | re.IGNORECASE)
da_good = re.search(r"Direct Answer</h2>(.*?)<h2", good_body, re.DOTALL | re.IGNORECASE)

if da_bad:
    print()
    print("BAD Direct Answer:")
    print(da_bad.group(1)[:600])

if da_good:
    print()
    print("GOOD Direct Answer:")
    print(da_good.group(1)[:600])
