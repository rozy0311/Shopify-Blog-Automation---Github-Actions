# AGENT PRE-PUBLISH REVIEW SYSTEM

## Mục đích
Script `pre_publish_review.py` tự động kiểm tra tất cả bài viết theo META-PROMPT standards trước khi publish.

---

## Cách sử dụng

### Review 1 bài cụ thể:
```bash
python scripts/pre_publish_review.py 690513117502
```

### Review nhiều bài:
```bash
python scripts/pre_publish_review.py 690513117502 690513150270 690513183038
```

### Review 10 bài mặc định:
```bash
python scripts/pre_publish_review.py
```

---

## WORKFLOW BẮT BUỘC

```
1. Tạo content đúng META-PROMPT ngay từ đầu
2. Tự chạy pre_publish_review.py TRƯỚC khi báo hoàn thành
3. Nếu có lỗi → tự fix → chạy lại review
4. Chỉ khi 100% PASS mới báo hoàn thành
```

**KHÔNG CẦN USER NHẮC LẠI. AGENT TỰ CHỊU TRÁCH NHIỆM.**

---

## META-PROMPT REQUIREMENTS CHECKLIST

### Content Metrics
| Requirement | Min | Max | Notes |
|-------------|-----|-----|-------|
| Word Count | 1800 | 2200 | Hard limit |
| Main Image | 1 | - | Required với alt text |
| Inline Images | 3 | - | Trong `<figure>` tags |
| Figures | 3 | - | `<figure>` tags |
| Blockquotes | 2 | - | Expert quotes |
| Tables | 1 | - | Data presentation |

### SEO Requirements
| Requirement | Min | Max | Notes |
|-------------|-----|-----|-------|
| Title Length | 30 | 60 | Chars |
| Meta Description | 50 | 160 | Chars |
| H2/H3 Headings | 5 | - | For structure |
| Lists (ul/ol) | 2 | - | Scanability |
| Internal Links | 2 | - | Links to other blogs |

### META-PROMPT Hard Validations
| Requirement | Details |
|-------------|---------|
| NO YEARS | Ban `\b(19|20)\d{2}\b` in all fields |
| Sources Section | ≥5 citations với proper links |
| Expert Quotes | ≥2 với real name/title/org format |
| Quantified Stats | ≥3 với sources |
| Heading IDs | Kebab-case id on all H2/H3 |
| Link rel | `rel="nofollow noopener"` on external links |
| No Schema in Body | JSON-LD NOT inside body_html |
| Direct Answer | Opening paragraph 50-70 words |
| Key Terms Section | Required |
| Sources & Further Reading | Required section |

### Field Requirements
| Field | Status | Notes |
|-------|--------|-------|
| title | Required | Must not be empty |
| body_html | Required | Must not be empty |
| handle | Required | Must not be empty |
| meta_description | Recommended | 50-160 chars for SEO |
| author | Recommended | Default: "The Rike" |
| tags | Recommended | For categorization |

---

## Output Format

```
======================================================================
ARTICLE: [Title]
ID: [Article ID]
STATUS: ✅ PASS / ❌ FAIL
======================================================================

CONTENT METRICS:
  Words: X (need 1800-2200)
  Main Image: ✅/❌
  Main Image Alt: ✅/❌
  Inline Images: X (need 3+)
  Figures: X (need 3+)
  Blockquotes: X (need 2+)
  Tables: X (need 1+)

SEO METRICS:
  Title Length: ✅/⚠️ X chars (need 30-60)
  H2 Headings: X
  H3 Headings: X
  Lists (ul/ol): X (need 2+)
  Internal Links: ✅/⚠️ X (need 2+)

META-PROMPT COMPLIANCE:
  Sources/Citations: ✅/❌ X (need 5+)
  Expert Quotes: ✅/⚠️ X (need 2+)
  Quantified Stats: ✅/⚠️ X (need 3+)
  Heading IDs: ✅/⚠️ X with id, X missing

FIELD STATUS:
  Handle: ✅/❌
  Author: ✅/⚠️
  Tags: ✅/⚠️
  Meta Description: ✅/⚠️/❌ (X chars, need 50-160)
  Summary HTML: ✅/⚠️
  Published: ✅/⚠️

ERRORS: [Critical issues that cause FAIL]
WARNINGS: [Non-critical issues to improve]
```

---

## Error Types

### ❌ ERRORS (Causes FAIL)
- Missing required fields (title, body_html, handle)
- Word count < 1800
- Missing main image
- Inline images < 3
- Figures < 3
- Blockquotes < 2
- Tables < 1
- Sources citations < 5
- Year in title (when strict_no_years=true)
- JSON-LD schema in body_html

### ⚠️ WARNINGS (Should fix but doesn't fail)
- Word count > 2200
- Title length outside 30-60
- Meta description missing or wrong length
- Missing author/tags
- Internal links < 2
- No CTA
- Expert quotes < 2 (format issues)
- Stats < 3
- Heading IDs missing
- External links missing rel attribute
- Year in body content
- Missing Key Terms section

---

## Shopify API Config
```python
import os
SHOP = os.environ.get("SHOPIFY_SHOP", "the-rike-inc.myshopify.com")
TOKEN = os.environ.get("SHOPIFY_ACCESS_TOKEN", "")  # Set in .env file
BLOG_ID = os.environ.get("SHOPIFY_BLOG_ID", "108441862462")
API_VERSION = "2025-01"
```

---

## Article IDs (10 bài mới)
```python
ARTICLE_IDS = [
    690513117502,  # Citrus Vinegar Cleaner
    690513150270,  # Glass Cleaner
    690513183038,  # Baking Soda Scrub
    690513215806,  # Castile Soap Dilution
    690513248574,  # Laundry Booster
    690513281342,  # Fabric Refresher
    690513314110,  # Deodorizer Sachets
    690513346878,  # Produce Wash
    690513379646,  # Lemon Juice Cleaning
    690513412414,  # Kombucha Guide
]
```

---

## Related Scripts
- `pre_publish_review.py` - Main review script
- `fix_failed_articles.py` - Fix failed articles (images, meta)
- `fix_meta_descriptions.py` - Add meta descriptions via metafields
- `fix_featured_images.py` - Add featured images
- `fix_images_relevant.py` - Replace with topic-specific images

---

**Last Updated: 2026-01-03**
**Agent tự review trước khi publish. Không cần user nhắc.**
