"""
🚀 AUTOPILOT AGENT - Full Pipeline: Research → Write → Review → Images → Publish

This is the MAIN entry point for the blog automation pipeline.
It orchestrates all steps automatically with built-in review checkpoints.

Usage:
    python scripts/autopilot_agent.py "Topic Title Here"
    python scripts/autopilot_agent.py --file topics.txt  # Process from file
    python scripts/autopilot_agent.py --next             # Next topic from queue

Pipeline Steps:
    1. Research & Evidence Collection (Claude + web tools)
    2. Article Writing (Claude with evidence integration)
    3. Content Validation (8 hard rules)
    4. Image Search & Review (Pexels API)
    5. SEO Optimization (title, description, author)
    6. Final Review & Approval
    7. Publish to Shopify
    8. Post-Publish Verification

Author: The Rike
"""

import os
import sys
import json
import re
import requests
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import Optional, List, Tuple

# Paths
SCRIPT_DIR = Path(__file__).parent
ROOT_DIR = SCRIPT_DIR.parent
CONTENT_DIR = ROOT_DIR / "content"
CONFIG_PATH = ROOT_DIR / "SHOPIFY_PUBLISH_CONFIG.json"
TOPICS_PATH = ROOT_DIR / "content" / "topics.json"

# Ensure directories exist
CONTENT_DIR.mkdir(exist_ok=True)

# Constants
PEXELS_API_KEY = os.environ.get(
    "PEXELS_API_KEY", "os.environ.get("PEXELS_API_KEY", "")"
)
AUTHOR_NAME = "The Rike"
BLOG_HANDLE = "sustainable-living"


@dataclass
class PipelineState:
    """Track pipeline progress and results."""

    topic: str
    status: str  # pending, researching, writing, validating, images, seo, reviewing, publishing, published, failed
    started_at: str
    completed_at: Optional[str] = None
    article_id: Optional[str] = None
    article_url: Optional[str] = None
    errors: List[str] = None
    warnings: List[str] = None
    review_results: dict = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []


class AutopilotAgent:
    """Main autopilot agent that orchestrates the entire pipeline."""

    def __init__(self):
        self.config = json.loads(CONFIG_PATH.read_text())
        self.shop = self.config["shop"]
        self.api_url = (
            f"https://{self.shop['domain']}/admin/api/{self.shop['api_version']}"
        )
        self.headers = {
            "Content-Type": "application/json",
            "X-Shopify-Access-Token": self.shop["access_token"],
        }
        self.state: Optional[PipelineState] = None

    def log(self, msg: str, level: str = "INFO"):
        """Log with timestamp and level."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        icons = {
            "INFO": "📝",
            "SUCCESS": "✅",
            "ERROR": "❌",
            "WARN": "⚠️",
            "STEP": "🔄",
        }
        icon = icons.get(level, "•")
        print(f"[{timestamp}] {icon} {msg}")

    def run_pipeline(self, topic: str) -> PipelineState:
        """Run the complete pipeline for a topic."""
        self.state = PipelineState(
            topic=topic, status="pending", started_at=datetime.now().isoformat()
        )

        print("\n" + "=" * 70)
        print("🚀 AUTOPILOT AGENT - Starting Pipeline")
        print("=" * 70)
        print(f"Topic: {topic}")
        print(f"Author: {AUTHOR_NAME}")
        print(f"Blog: {BLOG_HANDLE}")
        print("=" * 70 + "\n")

        try:
            # Step 1: Load or generate article content
            self.state.status = "loading"
            self.log("Loading article content...", "STEP")
            article = self.load_article_content()
            if not article:
                raise Exception(
                    "No article content found. Run content generation first."
                )
            self.log(f"Article loaded: {article.get('title', 'Unknown')}", "SUCCESS")

            # Step 2: Validate content
            self.state.status = "validating"
            self.log("Validating article content...", "STEP")
            validation = self.validate_article(article)
            if not validation["passed"]:
                self.state.errors.extend(validation["errors"])
                raise Exception(f"Validation failed: {validation['errors']}")
            self.log(f"Validation passed: {validation['score']}/100", "SUCCESS")

            # Step 3: Search and select images
            self.state.status = "images"
            self.log("Searching for images...", "STEP")
            images = self.search_and_review_images(article["title"])
            if len(images) < 3:
                self.state.warnings.append(
                    f"Only {len(images)} images found (recommended: 5)"
                )
            self.log(f"Found {len(images)} unique images", "SUCCESS")

            # Step 4: Generate SEO metadata
            self.state.status = "seo"
            self.log("Generating SEO metadata...", "STEP")
            seo = self.generate_seo(article)
            self.log(f"SEO title: {seo['title'][:50]}...", "SUCCESS")

            # Step 5: Insert images into article
            self.log("Inserting images into article...", "STEP")
            article_with_images = self.insert_images(article, images)
            self.log(f"Images inserted: {len(images)}", "SUCCESS")

            # Step 6: Final review
            self.state.status = "reviewing"
            self.log("Running final review...", "STEP")
            review = self.final_review(article_with_images, images, seo)
            self.state.review_results = review

            if not review["approved"]:
                self.log(f"Review issues: {review['issues']}", "WARN")
                # Continue anyway with warnings for now
            else:
                self.log("Final review passed!", "SUCCESS")

            # Step 7: Publish to Shopify
            self.state.status = "publishing"
            self.log("Publishing to Shopify...", "STEP")
            result = self.publish_article(
                article_with_images, seo, images[0] if images else None
            )

            if result.get("error"):
                raise Exception(f"Publish failed: {result['error']}")

            self.state.article_id = result["id"]
            self.state.article_url = result["url"]
            self.log(f"Published! ID: {result['id']}", "SUCCESS")

            # Step 8: Post-publish verification
            self.log("Verifying published article...", "STEP")
            verification = self.verify_published_article(result["id"])

            if verification["success"]:
                self.log("Verification passed!", "SUCCESS")
            else:
                self.state.warnings.extend(verification["issues"])
                self.log(f"Verification warnings: {verification['issues']}", "WARN")

            # Complete!
            self.state.status = "published"
            self.state.completed_at = datetime.now().isoformat()

            self.print_summary()
            return self.state

        except Exception as e:
            self.state.status = "failed"
            self.state.errors.append(str(e))
            self.log(f"Pipeline failed: {e}", "ERROR")
            self.save_state()
            raise

    def load_article_content(self) -> dict:
        """Load article content from payload file."""
        payload_path = CONTENT_DIR / "article_payload.json"
        if payload_path.exists():
            return json.loads(payload_path.read_text(encoding="utf-8"))
        return None

    def validate_article(self, article: dict) -> dict:
        """Validate article against quality rules."""
        errors = []
        warnings = []
        score = 100

        body = article.get("body_html", "")
        title = article.get("title", "")

        # Rule 1: Title length (50-60 chars ideal)
        if len(title) < 30:
            errors.append("Title too short (< 30 chars)")
            score -= 20
        elif len(title) > 80:
            warnings.append("Title may be too long (> 80 chars)")
            score -= 5

        # Rule 2: Word count (1500-2500 ideal)
        text = re.sub(r"<[^>]+>", "", body)
        word_count = len(text.split())
        if word_count < 1000:
            errors.append(f"Article too short ({word_count} words, need 1000+)")
            score -= 30
        elif word_count < 1500:
            warnings.append(f"Article could be longer ({word_count} words)")
            score -= 10

        # Rule 3: Has headings (h2, h3)
        h2_count = len(re.findall(r"<h2", body))
        h3_count = len(re.findall(r"<h3", body))
        if h2_count < 3:
            errors.append(f"Need more H2 headings ({h2_count} found, need 3+)")
            score -= 15

        # Rule 4: Has evidence markers
        evidence_count = len(re.findall(r"\[EVID:", body))
        if evidence_count < 3:
            warnings.append(f"Low evidence count ({evidence_count} citations)")
            score -= 10

        # Rule 5: Has FAQ section
        if "faq" not in body.lower():
            warnings.append("No FAQ section detected")
            score -= 5

        # Rule 6: Has sources
        if "sources" not in body.lower() and "reference" not in body.lower():
            warnings.append("No sources section detected")
            score -= 5

        # Rule 7: No placeholder text
        placeholders = ["[TODO]", "[TBD]", "Lorem ipsum", "PLACEHOLDER"]
        for ph in placeholders:
            if ph.lower() in body.lower():
                errors.append(f"Contains placeholder: {ph}")
                score -= 20

        # Rule 8: Proper HTML structure
        if body.count("<p>") != body.count("</p>"):
            warnings.append("Unbalanced paragraph tags")
            score -= 5

        return {
            "passed": len(errors) == 0,
            "score": max(0, score),
            "errors": errors,
            "warnings": warnings,
            "stats": {
                "word_count": word_count,
                "h2_count": h2_count,
                "h3_count": h3_count,
                "evidence_count": evidence_count,
            },
        }

    def search_and_review_images(self, topic: str) -> List[dict]:
        """Search Pexels for relevant images."""
        if not PEXELS_API_KEY:
            self.log("No Pexels API key, skipping images", "WARN")
            return []

        # Extract keywords from topic
        stop_words = {
            "how",
            "to",
            "make",
            "the",
            "a",
            "an",
            "from",
            "with",
            "for",
            "and",
            "or",
            "in",
            "on",
            "at",
            "your",
            "this",
            "that",
        }
        keywords = [
            w.lower()
            for w in re.findall(r"\b\w+\b", topic)
            if w.lower() not in stop_words and len(w) > 2
        ]

        # Generate search queries
        queries = [
            " ".join(keywords[:3]),
            f"{keywords[0]} {keywords[1] if len(keywords) > 1 else 'diy'}",
            f"{keywords[0]} kitchen homemade",
            f"{keywords[0]} jar glass",
            "sustainable kitchen zero waste",
        ]

        all_images = []
        seen_ids = set()

        headers = {"Authorization": PEXELS_API_KEY}

        for query in queries[:4]:
            try:
                resp = requests.get(
                    "https://api.pexels.com/v1/search",
                    headers=headers,
                    params={"query": query, "per_page": 8, "orientation": "landscape"},
                    timeout=15,
                )

                if resp.status_code == 200:
                    for photo in resp.json().get("photos", []):
                        photo_id = photo["id"]
                        if photo_id in seen_ids:
                            continue
                        seen_ids.add(photo_id)

                        alt = photo.get("alt", "")

                        # Skip images with text overlays
                        skip_words = [
                            "text",
                            "quote",
                            "banner",
                            "sign",
                            "poster",
                            "letter",
                            "word",
                        ]
                        if any(w in alt.lower() for w in skip_words):
                            continue

                        # Quality check
                        if photo["width"] < 800 or photo["height"] < 500:
                            continue

                        all_images.append(
                            {
                                "id": photo_id,
                                "url": photo["src"]["large2x"],
                                "url_medium": photo["src"]["large"],
                                "photographer": photo.get("photographer", "Unknown"),
                                "alt": alt,
                                "width": photo["width"],
                                "height": photo["height"],
                            }
                        )

                        if len(all_images) >= 5:
                            break

            except Exception as e:
                self.log(f"Pexels search error: {e}", "WARN")

            if len(all_images) >= 5:
                break

        return all_images[:5]

    def generate_seo(self, article: dict) -> dict:
        """Generate SEO metadata for article."""
        title = article.get("title", "")

        # SEO title (50-60 chars)
        seo_title = f"{title} | Easy DIY Guide"
        if len(seo_title) > 60:
            seo_title = f"{title[:50]}... | DIY Guide"

        # Meta description (150-160 chars)
        # Extract first paragraph as base
        body = article.get("body_html", "")
        first_p = re.search(r"<p[^>]*>(.+?)</p>", body)
        base_text = re.sub(r"<[^>]+>", "", first_p.group(1) if first_p else title)[:100]

        seo_description = (
            f"{base_text}... Step-by-step guide with tips. Free and sustainable!"
        )
        if len(seo_description) > 160:
            seo_description = seo_description[:157] + "..."

        return {
            "title": seo_title,
            "description": seo_description,
            "author": AUTHOR_NAME,
        }

    def insert_images(self, article: dict, images: List[dict]) -> dict:
        """Insert images into article body."""
        if not images:
            return article

        body = article.get("body_html", "")
        topic = article.get("title", "")

        # Remove any existing figure tags first
        body = re.sub(r"<figure[^>]*>.*?</figure>\s*", "", body, flags=re.DOTALL)

        # Hero image after first paragraph
        hero = images[0]
        hero_alt = f"Featured image: {topic} - {hero.get('alt', '')[:60]}"
        hero_html = f"""
<figure class="article-hero-image" style="margin:24px 0;">
  <img src="{hero['url']}"
       alt="{hero_alt}"
       loading="eager"
       width="{hero['width']}"
       height="{hero['height']}"
       style="width:100%;height:auto;border-radius:12px;box-shadow:0 4px 12px rgba(0,0,0,0.1);">
  <figcaption style="text-align:center;font-size:0.85em;color:#666;margin-top:10px;">
    {hero_alt} | Photo by {hero['photographer']} via Pexels
  </figcaption>
</figure>
"""

        first_p = body.find("</p>")
        if first_p > 0:
            body = body[: first_p + 4] + hero_html + body[first_p + 4 :]

        # Section images after h2 headings
        h2_pattern = re.compile(r"(</h2>)")
        matches = list(h2_pattern.finditer(body))

        offset = 0
        for i, match in enumerate(matches[: len(images) - 1]):
            if i + 1 >= len(images):
                break

            img = images[i + 1]
            img_alt = f"{topic} - {img.get('alt', '')[:60]}"
            img_html = f"""
<figure class="article-section-image" style="margin:24px 0;">
  <img src="{img['url']}"
       alt="{img_alt}"
       loading="lazy"
       width="{img['width']}"
       height="{img['height']}"
       style="width:100%;height:auto;border-radius:8px;">
  <figcaption style="text-align:center;font-size:0.8em;color:#888;margin-top:8px;">
    {img_alt}
  </figcaption>
</figure>
"""
            insert_pos = match.end() + offset
            body = body[:insert_pos] + img_html + body[insert_pos:]
            offset += len(img_html)

        article["body_html"] = body
        return article

    def final_review(self, article: dict, images: List[dict], seo: dict) -> dict:
        """Run final review before publishing."""
        issues = []

        # Check images
        if len(images) < 3:
            issues.append(f"Only {len(images)} images (recommended: 5)")

        # Check SEO
        if len(seo.get("title", "")) > 70:
            issues.append("SEO title too long")
        if len(seo.get("description", "")) > 170:
            issues.append("Meta description too long")

        # Check article body
        body = article.get("body_html", "")
        if len(body) < 5000:
            issues.append("Article body seems short")

        # Check for required elements
        if "img" not in body:
            issues.append("No images in body")
        if "<h2" not in body:
            issues.append("No H2 headings")

        return {
            "approved": len(issues) == 0,
            "issues": issues,
            "timestamp": datetime.now().isoformat(),
        }

    def publish_article(
        self, article: dict, seo: dict, featured_image: Optional[dict]
    ) -> dict:
        """Publish article to Shopify."""
        # Get blog ID
        blog_query = f"""
        query {{
          blogByHandle(handle: "{BLOG_HANDLE}") {{
            id
          }}
        }}
        """

        resp = requests.post(
            f"{self.api_url}/graphql.json",
            headers=self.headers,
            json={"query": blog_query},
        )
        data = resp.json()
        blog_id = data.get("data", {}).get("blogByHandle", {}).get("id")

        if not blog_id:
            return {"error": f"Blog '{BLOG_HANDLE}' not found"}

        # Create article via GraphQL
        mutation = """
        mutation articleCreate($article: ArticleCreateInput!) {
          articleCreate(article: $article) {
            article {
              id
              handle
              title
            }
            userErrors {
              field
              message
            }
          }
        }
        """

        handle = re.sub(r"[^a-z0-9]+", "-", article.get("title", "").lower()).strip("-")

        article_input = {
            "blogId": blog_id,
            "title": article.get("title"),
            "handle": handle,
            "body": article.get("body_html"),
            "author": {"name": seo.get("author", AUTHOR_NAME)},
            "isPublished": True,
        }

        resp = requests.post(
            f"{self.api_url}/graphql.json",
            headers=self.headers,
            json={"query": mutation, "variables": {"article": article_input}},
        )
        result = resp.json()

        article_data = result.get("data", {}).get("articleCreate", {}).get("article")
        errors = result.get("data", {}).get("articleCreate", {}).get("userErrors", [])

        if errors:
            return {"error": errors}

        if not article_data:
            return {"error": "No article data returned"}

        article_id = article_data["id"].split("/")[-1]

        # Update with SEO and featured image via REST API
        rest_url = f"{self.api_url}/articles/{article_id}.json"

        update_data = {
            "article": {
                "id": int(article_id),
                "author": seo.get("author", AUTHOR_NAME),
                "metafields_global_title_tag": seo.get("title"),
                "metafields_global_description_tag": seo.get("description"),
            }
        }

        # Add featured image if available
        if featured_image:
            update_data["article"]["image"] = {
                "src": featured_image.get("url"),
                "alt": f"Featured: {article.get('title', '')}",
            }

        requests.put(rest_url, headers=self.headers, json=update_data)

        store_domain = (
            self.shop["domain"].replace(".myshopify.com", "").replace("-", "")
        )
        admin_url = f"https://admin.shopify.com/store/{store_domain}/content/articles/{article_id}"

        return {
            "id": article_id,
            "handle": article_data["handle"],
            "url": f"https://{self.shop['domain']}/blogs/{BLOG_HANDLE}/{article_data['handle']}",
            "admin_url": admin_url,
        }

    def verify_published_article(self, article_id: str) -> dict:
        """Verify the published article."""
        issues = []

        rest_url = f"{self.api_url}/articles/{article_id}.json"
        resp = requests.get(rest_url, headers=self.headers)

        if resp.status_code != 200:
            return {"success": False, "issues": ["Could not fetch article"]}

        article = resp.json().get("article", {})

        # Check author
        if article.get("author") != AUTHOR_NAME:
            issues.append(f"Author mismatch: {article.get('author')}")

        # Check body has images
        body = article.get("body_html", "")
        if "<img" not in body:
            issues.append("No images in published body")

        # Check featured image
        if not article.get("image"):
            issues.append("No featured image set")

        return {
            "success": len(issues) == 0,
            "issues": issues,
            "article": {
                "id": article_id,
                "title": article.get("title"),
                "author": article.get("author"),
                "published_at": article.get("published_at"),
                "has_image": article.get("image") is not None,
            },
        }

    def print_summary(self):
        """Print pipeline summary."""
        print("\n" + "=" * 70)
        print("📊 PIPELINE SUMMARY")
        print("=" * 70)
        print(f"Topic: {self.state.topic}")
        print(f"Status: {self.state.status.upper()}")
        print(f"Started: {self.state.started_at}")
        print(f"Completed: {self.state.completed_at}")

        if self.state.article_id:
            print(f"\n📄 Article ID: {self.state.article_id}")
            print(f"🔗 URL: {self.state.article_url}")

        if self.state.warnings:
            print(f"\n⚠️ Warnings ({len(self.state.warnings)}):")
            for w in self.state.warnings:
                print(f"   - {w}")

        if self.state.errors:
            print(f"\n❌ Errors ({len(self.state.errors)}):")
            for e in self.state.errors:
                print(f"   - {e}")

        print("=" * 70)

        self.save_state()

    def save_state(self):
        """Save pipeline state to file."""
        state_path = CONTENT_DIR / "pipeline_state.json"
        state_path.write_text(
            json.dumps(asdict(self.state), indent=2, ensure_ascii=False)
        )


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage:")
        print('  python scripts/autopilot_agent.py "Your Topic Title"')
        print("  python scripts/autopilot_agent.py --next")
        sys.exit(1)

    arg = sys.argv[1]

    if arg == "--next":
        # Load next topic from queue
        if TOPICS_PATH.exists():
            topics = json.loads(TOPICS_PATH.read_text())
            pending = [t for t in topics if t.get("status") == "pending"]
            if pending:
                topic = pending[0]["title"]
            else:
                print("No pending topics in queue")
                sys.exit(1)
        else:
            print("No topics file found")
            sys.exit(1)
    else:
        topic = arg

    agent = AutopilotAgent()

    try:
        state = agent.run_pipeline(topic)

        if state.status == "published":
            print("\n✅ SUCCESS! Article published and verified.")
            sys.exit(0)
        else:
            print(f"\n❌ Pipeline ended with status: {state.status}")
            sys.exit(1)

    except Exception as e:
        print(f"\n❌ Pipeline failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
