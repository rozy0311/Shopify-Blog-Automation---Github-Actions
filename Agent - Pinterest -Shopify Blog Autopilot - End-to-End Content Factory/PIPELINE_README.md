# Pinterest → Shopify Blog Autopilot

**End-to-End Content Factory**: Trend Mining → Topic/Title Review → Research → Write → 4 Photos → Validate → Review → Batch Publish (20/20min, No Duplicates)

## Overview

This system automates the entire Shopify blog publishing pipeline:

1. **Trend Mining** - Discover high-interest topics from Pinterest
2. **Topic/Title Generation** - Keyword-first, intent-matched titles
3. **Research** - Web search + page fetching → evidence ledger
4. **Write Article** - AEO/GEO HTML + separate schema payload
5. **Generate Images** - 4 photorealistic images (1 main + 3 inline)
6. **Validate** - Automated checks for HTML, links, word count, sources
7. **Review** - Claims verified against evidence ledger
8. **Batch Publish** - 20 posts → wait 20 minutes → next 20
9. **No Duplicates** - Local state + Shopify fingerprint metafield

## Directory Structure

```
.
├── SHOPIFY_PUBLISH_CONFIG.json  # Main configuration
├── topics.txt                    # Topic queue (one per line)
├── scripts/
│   ├── validate_article.py      # Validator script
│   ├── publish_article.py       # Shopify publisher
│   ├── batch_publish.py         # Batch scheduler
│   └── run_one_topic.py         # Single topic pipeline
├── content/
│   ├── state.json               # Batch state (published/failed)
│   ├── topic_state.json         # Topic discovery state
│   ├── trend_state.json         # Pinterest trends state
│   ├── article_payload.json     # Current article data
│   ├── evidence_ledger.json     # Research evidence
│   ├── qa_report.json           # Validation/review results
│   ├── image_plan.json          # Image generation plan
│   └── publish_result.json      # Publish outcome
└── apps/
    ├── executor/                # TypeScript executor
    ├── supervisor/              # Supervisor service
    └── amp/                     # AMP utilities
```

## Quick Start

### 1. Install Dependencies

```bash
pip install beautifulsoup4 requests
```

### 2. Set Environment Variables

```bash
# Windows PowerShell
$env:SHOPIFY_STORE_DOMAIN = "your-store.myshopify.com"
$env:SHOPIFY_ADMIN_ACCESS_TOKEN = "shpat_xxxxx"
$env:SHOPIFY_API_VERSION = "2025-10"

# Linux/Mac
export SHOPIFY_STORE_DOMAIN="your-store.myshopify.com"
export SHOPIFY_ADMIN_ACCESS_TOKEN="shpat_xxxxx"
export SHOPIFY_API_VERSION="2025-10"
```

### 3. Add Topics

Edit `topics.txt` with your topics (one per line):

```text
# Kitchen How-To
How to Make Homemade Vinegar from Fruit Scraps
DIY Vanilla Extract at Home
Natural All-Purpose Cleaner Recipe
```

### 4. Run Batch Publisher

```bash
python scripts/batch_publish.py
```

Options:
```bash
# Dry run (no actual publishing)
DRY_RUN=true python scripts/batch_publish.py

# Custom batch settings
BATCH_SIZE=10 PAUSE_MINUTES=15 python scripts/batch_publish.py
```

## Pipeline Scripts

### validate_article.py

Validates article payload against hard rules:
- Word count within 1800-2200
- SEO title ≤60 chars, meta desc ≤155 chars
- No year tokens (YYYY) if strict_no_years=true
- All H2/H3 have unique kebab-case IDs
- All links absolute HTTPS with rel="nofollow noopener"
- Minimum 5 citations, 2 quotes, 3 stats
- Schema NOT inside HTML body
- All images have alt text

```bash
python scripts/validate_article.py content/article_payload.json
```

### publish_article.py

Publishes to Shopify via Admin GraphQL API:
- Only publishes if validator_pass AND reviewer_pass = true
- Checks for duplicates via fingerprint metafield
- Sets schema JSON-LD as metafield
- Handles rate limiting with exponential backoff

```bash
python scripts/publish_article.py content/article_payload.json
```

### batch_publish.py

Batch scheduler:
- Publishes 20 articles per batch
- Pauses 20 minutes between batches
- Never repeats already published topics
- Tracks daily limits
- Saves checkpoint for resume

```bash
python scripts/batch_publish.py
```

### run_one_topic.py

Full pipeline for single topic:
1. Creates template files
2. (LLM agent fills content)
3. Runs validator
4. Runs reviewer
5. Publishes if both pass

```bash
python scripts/run_one_topic.py --topic "How to Make Homemade Vinegar"
python scripts/run_one_topic.py --topic "..." --dry-run
```

## Configuration

### SHOPIFY_PUBLISH_CONFIG.json

Key settings:

```json
{
  "defaults": {
    "blog_handle": "sustainable-living",
    "author_name": "The Rike",
    "publish_mode": "draft"
  },
  "content": {
    "word_budget_min": 1800,
    "word_budget_max": 2200,
    "min_citations": 5,
    "min_quotes": 2,
    "min_stats": 3,
    "strict_no_years": true
  },
  "batch": {
    "size": 20,
    "pause_minutes": 20,
    "max_daily_posts": 100
  }
}
```

## Evidence-Based Writing

### Evidence Ledger

All claims must be backed by fetched sources:

```json
{
  "sources": [
    {
      "url": "https://extension.edu/article",
      "org": "University Extension",
      "domain_score": 5,
      "fetched": true,
      "key_facts": ["fact 1", "fact 2"]
    }
  ],
  "stats": [
    {
      "id": "STAT_1",
      "stat": "pH should reach 2-3",
      "source_url": "https://...",
      "context": "For proper acidity"
    }
  ],
  "quotes": [
    {
      "id": "QUOTE_1",
      "quote": "Exact quote text...",
      "speaker": "Dr. Name",
      "title": "Title, Organization",
      "verified": true
    }
  ]
}
```

### Claim Markers

In article HTML, mark claims with evidence references:

```html
<p>Final vinegar should reach pH 2-3 [EVID:STAT_1].</p>
<blockquote>"Quote text..." [EVID:QUOTE_1]</blockquote>
```

The reviewer validates these markers exist in the evidence ledger.

## Image Pipeline

### 4 Required Images

1. **Main/Featured** - Hero shot of final result
2. **Inline 1 (prep)** - Ingredients/materials setup
3. **Inline 2 (process)** - Key step in action
4. **Inline 3 (troubleshoot)** - Common issue or final check

### Image Rules

- Photorealistic style (50mm lens, f/2.8, natural light)
- No people, hands, faces, logos, text, watermarks
- All props must exist in SOURCE_POINTS/facts
- Alt text literal (describes what's visible)
- Min 1600px width
- Upload to Shopify Files, wait for READY status

### Image Plan Template

```json
{
  "main_image": {
    "prompt": "Glass jar with fruit peels, natural window light...",
    "alt": "Glass jar filled with apple peels and cores submerged in water"
  },
  "inline_images": [
    {
      "insert_after_section_id": "prep",
      "prompt": "Fresh apple cores on wooden cutting board...",
      "alt": "Fresh apple cores and peels arranged on wooden cutting board"
    }
  ]
}
```

## Deduplication

### Local State

`content/state.json` tracks:
- `published`: hash → topic info
- `failed`: hash → error info + retry count

### Shopify Fingerprint

Each article gets a metafield:
- Namespace: `qa`
- Key: `fingerprint`
- Value: SHA256(topic + keyword + title)

Before creating, pipeline queries Shopify for existing fingerprint.

## Validation Gates

### Validator (Machine Check)

- [ ] Required fields present
- [ ] SEO lengths within limits
- [ ] No year tokens (if strict)
- [ ] Schema not in HTML body
- [ ] Heading IDs unique + kebab-case
- [ ] All links HTTPS + rel attributes
- [ ] ≥5 source citations
- [ ] ≥2 blockquotes
- [ ] ≥3 stat markers
- [ ] Word count in range
- [ ] All images have alt + HTTPS src

### Reviewer (Content Check)

- [ ] Stat markers reference valid ledger entries
- [ ] Quote markers reference valid ledger entries
- [ ] Minimum sources in ledger
- [ ] Primary keyword in title
- [ ] No fabricated claims

## VSCode Agent Integration

Use this prompt to have VSCode Copilot generate content:

```markdown
You are an execution agent for Shopify blog publishing.

TOOLS YOU MUST USE:
- vscode-websearchforcopilot_webSearch (discovery)
- fetch_webpage (EVERY source you cite)

NO-FETCH-NO-CLAIM POLICY:
- You may only include a citation/quote/stat if you fetched the page
- Mark claims with [EVID:STAT_N] and [EVID:QUOTE_N]

WORKFLOW:
1. Research topic with webSearch
2. Fetch top 5-10 sources
3. Build evidence_ledger.json
4. Write article following meta-prompt
5. Generate image_plan.json
6. Save article_payload.json

TOPIC: <your topic here>
```

## Troubleshooting

### Validator Fails

Check `content/qa_report.json` for specific errors:
```bash
cat content/qa_report.json | python -m json.tool
```

### Rate Limited by Shopify

The publisher uses exponential backoff. If persistent:
- Reduce BATCH_SIZE
- Increase PAUSE_MINUTES
- Check API rate limits in Shopify admin

### Duplicate Detection

If seeing duplicate errors:
1. Check `content/state.json` for published hashes
2. Query Shopify for articles with fingerprint metafield
3. Clear state.json to reset (careful: may republish)

### Pipeline Stops at Reviewer

Ensure evidence_ledger.json has:
- ≥5 sources with valid URLs
- ≥2 quotes with speaker + title
- ≥3 stats with source_url

## API Requirements

Shopify Admin API scopes needed:
- `write_content` - Create/update articles
- `write_files` - Upload images to Files
- `read_content` - Query existing articles

## License

MIT

## Credits

Built following the Pinterest → Shopify Blog Autopilot blueprint for evidence-based, batch-published content with automated quality gates.
