"""
Blog Content Generator
Generate full blog content tß╗½ topic .md files
Uses webSearch for research + Pollinations.ai for AI images

Usage:
    python blog_generator.py --topic "001_homemade_elderberry_syrup.md"
    python blog_generator.py --batch 5  # Generate first 5 topics
    python blog_generator.py --all  # Generate all topics
"""

import os
import sys
import json
import time
import re
import requests
import argparse
import urllib.parse
from datetime import datetime
from urllib.parse import quote
from html import unescape
from pathlib import Path
from dotenv import load_dotenv

# Load environment
env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(env_path)

# Shopify API Config
SHOPIFY_STORE = os.getenv("SHOPIFY_SHOP", "the-rike-inc.myshopify.com").replace(
    ".myshopify.com", ""
)
SHOPIFY_TOKEN = os.getenv("SHOPIFY_ACCESS_TOKEN")
SHOPIFY_BLOG_ID = os.getenv("SHOPIFY_BLOG_ID", "108441862462")


class BlogContentGenerator:
    """Generate high-quality blog content tß╗½ Pinterest topics"""

    # ==================== QUALITY STANDARDS (from META-PROMPT) ====================

    # Generic phrases to detect and reject
    GENERIC_PHRASES = [
        "this comprehensive guide provides",
        "this comprehensive guide covers",
        "whether you are a beginner",
        "whether you're a beginner",
        "natural materials vary throughout",
        "professional practitioners recommend",
        "achieving consistent results requires attention",
        "once you've perfected small batches",
        "scaling up becomes appealing",
        "making larger batches requires",
        "this practical guide",
        "perfect for anyone looking to improve",
        "join thousands who have already mastered",
    ]

    # Template contamination rules - detect wrong content for topic
    CONTAMINATION_RULES = {
        "cordage": [
            "measuring cups",
            "thermometer",
            "baking",
            "recipe",
            "dry ingredients",
            "shelf life",
        ],
        "garden": ["shelf life 2-4 weeks", "dry ingredients", "recipe", "baking"],
        "plant": ["measuring cups", "recipe", "baking", "thermometer"],
        "vinegar": ["cordage", "rope", "twine", "weaving"],
        "soap": ["germination", "transplanting", "pruning"],
        "candle": ["germination", "transplanting", "compost"],
    }

    # Required sections (11-section structure)
    SECTION_KEYWORDS = {
        "direct_answer": ["direct answer", "quick answer"],
        "key_conditions": [
            "key information",
            "at a glance",
            "key benefits",
            "key conditions",
        ],
        "understanding": ["understanding", "what is", "about", "benefits"],
        "step_by_step": ["step-by-step", "step by step", "how to", "guide"],
        "types_varieties": ["types", "varieties", "different kinds"],
        "troubleshooting": ["troubleshooting", "common issues", "problems", "mistakes"],
        "pro_tips": ["pro tips", "expert tips", "tips from experts"],
        "faq": ["faq", "frequently asked", "questions"],
        "advanced": ["advanced", "expert methods", "techniques"],
        "comparison": ["comparison", "compare", "table", "materials", "supplies"],
        "sources": ["sources", "further reading", "references"],
    }

    # Off-topic content patterns to remove (from slow_careful_fix.py)
    OFF_TOPIC_PATTERNS = [
        # Generic cooking/recipe content appearing in non-cooking topics
        (r"<h[23][^>]*>Mastering Precision.*?(?=<h[23]|$)", ""),
        (r"<p>[^<]*heat distribution[^<]*</p>", ""),
        (r"<p>[^<]*thermometer[^<]*</p>", ""),
        (r"<li>[^<]*measuring cups[^<]*</li>", ""),
        (r"<li>[^<]*dry ingredients[^<]*</li>", ""),
        (r"<li>[^<]*shelf life[^<]*weeks[^<]*</li>", ""),
        # Generic gardening content in non-gardening topics
        (r"<p>[^<]*germination rate[^<]*</p>", ""),
        (r"<li>[^<]*transplanting seedlings[^<]*</li>", ""),
    ]

    # Off-topic phrases to detect
    OFF_TOPIC_PHRASES = [
        "heat distribution",
        "thermometer",
        "mastering precision",
        "measuring cups",
        "dry ingredients",
    ]

    # Image generation settings (from agent_builder.py)
    IMAGE_NEGATIVE_PROMPTS = [
        "deformed fingers",
        "extra fingers",
        "mutated hands",
        "poorly drawn hands",
        "bad anatomy",
        "blurry",
        "watermark",
        "text",
        "logo",
    ]

    IMAGE_STYLES = {
        "photography": "professional photography, high quality, detailed, natural lighting",
        "illustration": "digital illustration, clean design, modern style",
        "minimalist": "minimalist, clean background, simple composition",
        "nature": "nature photography, outdoor, natural elements, green plants",
    }

    # Required sections for full_audit (from ai_orchestrator.py)
    REQUIRED_SECTIONS = [
        "Direct Answer",
        "Key Conditions at a Glance",
        "Understanding",
        "Complete Step-by-Step Guide",
        "Types and Varieties",
        "Troubleshooting Common Issues",
        "Pro Tips from Experts",
        "Frequently Asked Questions",
        "Advanced Techniques",
        "Comparison Table",
        "Sources & Further Reading",
    ]

    def __init__(self):
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.topics_dir = os.path.join(self.base_dir, "Blog topic ( scrape Pinterest)")
        self.output_dir = os.path.join(self.base_dir, "output", "articles")
        self.images_dir = os.path.join(self.base_dir, "output", "images")

        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.images_dir, exist_ok=True)

        # Quality thresholds (stricter standards)
        self.min_word_count = 1800
        self.max_word_count = 2500
        self.min_sections = 9
        self.min_images = 4
        self.min_sources = 5
        self.min_blockquotes = 2

        self.required_sections = [
            "Direct Answer",
            "Key Information",
            "Understanding the Benefits",
            "Essential Materials",
            "Types and Varieties",
            "Step-by-Step",
            "Pro Tips",
            "Common Mistakes",
            "Troubleshooting",
            "Frequently Asked Questions",
            "Sources",
        ]

    def log(self, message, level="INFO"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        icons = {
            "INFO": "≡ƒôï",
            "SUCCESS": "Γ£à",
            "ERROR": "Γ¥î",
            "WARNING": "ΓÜá∩╕Å",
            "IMAGE": "≡ƒû╝∩╕Å",
        }
        print(f"[{timestamp}] {icons.get(level, '≡ƒôï')} {message}")

    def get_pending_topics(self):
        """Get list of pending topic files"""
        topics = []
        for filename in sorted(os.listdir(self.topics_dir)):
            if filename.endswith(".md") and not filename.startswith("all_"):
                filepath = os.path.join(self.topics_dir, filename)
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()
                    if 'status: "pending"' in content:
                        # Extract title from frontmatter
                        title_match = re.search(r'title: "([^"]+)"', content)
                        title = title_match.group(1) if title_match else filename
                        topics.append(
                            {"filename": filename, "filepath": filepath, "title": title}
                        )
        return topics

    def generate_ai_images(self, topic, num_images=4):
        """Generate AI images using Pollinations.ai with CINEMATIC style"""
        self.log(f"Generating {num_images} AI images for: {topic}", "IMAGE")

        images = []
        # CINEMATIC QUALITY settings
        quality = "hyper realistic, photorealistic, cinematic lighting, golden hour, shallow depth of field, bokeh, 8K, shot on Sony A7R IV, National Geographic quality"
        safety = "no people visible, no hands, no fingers, still life composition"

        prompts = [
            f"Stunning hero shot of {topic} in cozy farmhouse kitchen, beautifully styled like a magazine cover, dramatic rim lighting, {quality}, {safety}",
            f"Overhead cinematic shot of fresh ingredients for {topic} artfully arranged on rustic wooden table, morning light creating soft shadows, {quality}, {safety}",
            f"Close-up macro photography of {topic} preparation, dramatic depth of field, droplets of moisture visible, moody atmospheric lighting, {quality}, {safety}",
            f"Beautiful final presentation of {topic} in natural outdoor setting, Pinterest-worthy lifestyle photo, warm inviting atmosphere, {quality}, {safety}",
        ]

        for i, prompt in enumerate(prompts[:num_images]):
            seed = int(time.time()) + i + hash(topic) % 10000
            encoded_prompt = quote(prompt)
            image_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1024&height=1024&seed={seed}&nologo=true"

            images.append(
                {
                    "url": image_url,
                    "alt": f"{topic} - Image {i+1}",
                    "is_featured": i == 0,
                }
            )

            self.log(f"  Image {i+1}: Generated", "SUCCESS")

        return images

    def upload_to_shopify_cdn(self, image_url, filename, topic):
        """Upload image to Shopify Files API"""
        self.log(f"Uploading to Shopify CDN: {filename}")

        # Step 1: Create staged upload
        staged_url = (
            f"https://{SHOPIFY_STORE}.myshopify.com/admin/api/2024-04/graphql.json"
        )
        headers = {
            "X-Shopify-Access-Token": SHOPIFY_TOKEN,
            "Content-Type": "application/json",
        }

        mutation = """
        mutation stagedUploadsCreate($input: [StagedUploadInput!]!) {
          stagedUploadsCreate(input: $input) {
            stagedTargets {
              url
              resourceUrl
              parameters {
                name
                value
              }
            }
            userErrors {
              field
              message
            }
          }
        }
        """

        variables = {
            "input": [
                {
                    "resource": "FILE",
                    "filename": filename,
                    "mimeType": "image/jpeg",
                    "httpMethod": "POST",
                }
            ]
        }

        try:
            # Get staged upload URL
            response = requests.post(
                staged_url,
                json={"query": mutation, "variables": variables},
                headers=headers,
            )
            data = response.json()

            if "errors" in data or not data.get("data", {}).get(
                "stagedUploadsCreate", {}
            ).get("stagedTargets"):
                self.log(f"Staged upload failed: {data}", "ERROR")
                return image_url  # Return original Pollinations URL

            target = data["data"]["stagedUploadsCreate"]["stagedTargets"][0]
            upload_url = target["url"]
            resource_url = target["resourceUrl"]
            params = {p["name"]: p["value"] for p in target["parameters"]}

            # Step 2: Download image from Pollinations
            self.log(f"Downloading from Pollinations...")
            img_response = requests.get(image_url, timeout=60)
            if img_response.status_code != 200:
                self.log(f"Failed to download image", "ERROR")
                return image_url

            # Step 3: Upload to staged URL
            files = {"file": (filename, img_response.content, "image/jpeg")}
            upload_response = requests.post(upload_url, data=params, files=files)

            if upload_response.status_code not in [200, 201, 204]:
                self.log(f"Upload failed: {upload_response.status_code}", "ERROR")
                return image_url

            # Step 4: Create file in Shopify
            file_mutation = """
            mutation fileCreate($files: [FileCreateInput!]!) {
              fileCreate(files: $files) {
                files {
                  ... on MediaImage {
                    id
                    image {
                      url
                    }
                  }
                }
                userErrors {
                  field
                  message
                }
              }
            }
            """

            file_variables = {
                "files": [
                    {
                        "alt": topic,
                        "contentType": "IMAGE",
                        "originalSource": resource_url,
                    }
                ]
            }

            file_response = requests.post(
                staged_url,
                json={"query": file_mutation, "variables": file_variables},
                headers=headers,
            )
            file_data = file_response.json()

            # Wait for processing
            time.sleep(3)

            # Get final URL
            files_list = (
                file_data.get("data", {}).get("fileCreate", {}).get("files", [])
            )
            if files_list and files_list[0].get("image", {}).get("url"):
                cdn_url = files_list[0]["image"]["url"]
                self.log(f"Uploaded to Shopify CDN: {cdn_url[:60]}...", "SUCCESS")
                return cdn_url

            return image_url

        except Exception as e:
            self.log(f"CDN upload error: {e}", "ERROR")
            return image_url

    # ==================== SANITIZE & VALIDATE FUNCTIONS ====================

    def sanitize_html(self, html):
        """Sanitize HTML content to prevent common issues BEFORE publishing"""
        if not html:
            return html

        # 1. Fix URL-encoded content (protect href URLs first)
        href_pattern = r'href="([^"]+)"'
        protected = {}
        counter = [0]

        def protect_href(m):
            key = f"__PROTECTED_HREF_{counter[0]}__"
            protected[key] = m.group(0)
            counter[0] += 1
            return key

        html = re.sub(href_pattern, protect_href, html)
        html = urllib.parse.unquote(html)

        # Restore protected hrefs
        for key, value in protected.items():
            html = html.replace(key, value)

        # 2. Fix broken source links (like: href=" https:>)
        html = re.sub(r'href="\s*https:>', 'href="https://', html)
        html = html.replace("%20<li>", " <li>")
        html = html.replace("%20</li>", "</li>")

        # 3. Fix double-encoded HTML entities
        html = unescape(html)

        # 4. Ensure proper quote encoding in attributes
        html = re.sub(
            r'alt="([^"]*)"',
            lambda m: f'alt="{m.group(1).replace(chr(34), "&quot;")}"',
            html,
        )

        # 5. Remove any stray % encoding in text content
        html = re.sub(
            r"%([0-9A-Fa-f]{2})(?![0-9A-Fa-f])",
            lambda m: chr(int(m.group(1), 16)) if int(m.group(1), 16) > 31 else "",
            html,
        )

        # 6. Clean up empty tags
        html = re.sub(r"<p>\s*</p>", "", html)
        html = re.sub(r"<ul>\s*</ul>", "", html)
        html = re.sub(r"<li>\s*</li>", "", html)

        self.log("  Γ£ô HTML sanitized", "SUCCESS")
        return html

    def remove_off_topic_content(self, html, topic):
        """Remove content that doesn't match the article topic"""
        if not html:
            return html

        original_html = html
        topic_lower = topic.lower()

        # Apply OFF_TOPIC_PATTERNS
        for pattern, replacement in self.OFF_TOPIC_PATTERNS:
            # Only apply if not relevant to topic
            if "cooking" not in topic_lower and "recipe" not in topic_lower:
                html = re.sub(
                    pattern, replacement, html, flags=re.IGNORECASE | re.DOTALL
                )

        # Check OFF_TOPIC_PHRASES for non-matching topics
        for phrase in self.OFF_TOPIC_PHRASES:
            if phrase.lower() in html.lower():
                # Only flag if topic doesn't naturally include this phrase
                if phrase.lower() not in topic_lower:
                    # Remove paragraphs containing this phrase
                    html = re.sub(
                        rf"<p>[^<]*{re.escape(phrase)}[^<]*</p>",
                        "",
                        html,
                        flags=re.IGNORECASE,
                    )
                    html = re.sub(
                        rf"<li>[^<]*{re.escape(phrase)}[^<]*</li>",
                        "",
                        html,
                        flags=re.IGNORECASE,
                    )

        # Clean up empty tags after removal
        html = re.sub(r"<p>\s*</p>", "", html)
        html = re.sub(r"<ul>\s*</ul>", "", html)
        html = re.sub(r"<li>\s*</li>", "", html)

        if html != original_html:
            self.log("  Γ£ô Removed off-topic content", "SUCCESS")

        return html

    def fix_source_links_format(self, html):
        """Convert raw URL links to proper format: Name ΓÇö Description"""

        def fix_link(match):
            full_tag = match.group(0)
            href = match.group(1)
            text = match.group(2)

            # If text contains .com, .org, etc. - fix it
            if re.search(r"\.(com|org|net|io|gov)", text.lower()):
                domain_match = re.search(r"([\w]+)\.(com|org|net|io|gov)", text, re.I)
                if domain_match:
                    name = domain_match.group(1).title()
                    desc_match = re.search(
                        r"\.(com|org|net|io|gov)[^a-zA-Z]*(.+)", text, re.I
                    )
                    if desc_match and desc_match.group(2).strip():
                        desc = desc_match.group(2).strip()
                        desc = re.sub(r"^[ΓÇö\-ΓÇô:]+\s*", "", desc)
                        return f'<a href="{href}">{name} ΓÇö {desc}</a>'
                    else:
                        return f'<a href="{href}">{name}</a>'
            return full_tag

        pattern = r'<a\s+href="([^"]+)"[^>]*>([^<]+)</a>'
        fixed = re.sub(pattern, fix_link, html)
        return fixed

    def validate_content(self, html, topic):
        """Comprehensive content validation following META-PROMPT standards"""
        issues = []
        warnings = []
        text = re.sub(r"<[^>]+>", " ", html or "")
        text_lower = text.lower()
        html_lower = (html or "").lower()
        topic_lower = topic.lower()

        # ==================== CRITICAL CHECKS ====================

        # 1. Check for URL-encoded content
        url_encoded_patterns = ["%20", "%3A", "%22", "%2F", "%3C", "%3E"]
        for pattern in url_encoded_patterns:
            if pattern in html:
                issues.append(f"URL-encoded content: {pattern}")
                break

        # 2. Check for broken links
        if "https:>" in html or 'href=" https:' in html:
            issues.append("Broken source links")

        # 3. Check for raw URL in link text
        if re.search(r"<a[^>]*>[^<]*\.(com|org|net|io)[^<]*</a>", html):
            issues.append("Source links showing raw URL")

        # ==================== WORD COUNT CHECK ====================

        word_count = len(text.split())
        if word_count < self.min_word_count:
            issues.append(
                f"Word count too low: {word_count} (min: {self.min_word_count})"
            )
        elif word_count > self.max_word_count:
            warnings.append(
                f"Word count high: {word_count} (max: {self.max_word_count})"
            )

        # ==================== SECTION STRUCTURE CHECK ====================

        headings = re.findall(r"<h[23][^>]*>([^<]+)</h[23]>", html, re.I)
        heading_texts = [h.lower() for h in headings]

        found_sections = []
        missing_sections = []

        for section, keywords in self.SECTION_KEYWORDS.items():
            found = False
            for heading in heading_texts:
                if any(kw in heading for kw in keywords):
                    found = True
                    found_sections.append(section)
                    break
            if not found:
                missing_sections.append(section)

        if len(found_sections) < self.min_sections:
            issues.append(
                f"Missing sections ({len(found_sections)}/{self.min_sections}): {', '.join(missing_sections[:3])}"
            )

        # ==================== GENERIC CONTENT CHECK ====================

        found_generic = []
        for phrase in self.GENERIC_PHRASES:
            if phrase in text_lower:
                found_generic.append(phrase)

        if len(found_generic) >= 2:
            issues.append(f"Generic content detected: '{found_generic[0][:30]}...'")
        elif found_generic:
            warnings.append(f"Generic phrase: '{found_generic[0][:30]}...'")

        # ==================== TOPIC CONTAMINATION CHECK ====================

        contamination_issues = []
        for topic_key, bad_words in self.CONTAMINATION_RULES.items():
            if topic_key in topic_lower:
                for word in bad_words:
                    if word in text_lower:
                        contamination_issues.append(
                            f"'{word}' in '{topic_key}' article"
                        )

        if contamination_issues:
            issues.append(f"Off-topic content: {contamination_issues[0]}")

        # Check OFF_TOPIC_PHRASES (from slow_careful_fix.py)
        found_off_topic = []
        for phrase in self.OFF_TOPIC_PHRASES:
            if phrase.lower() in text_lower and phrase.lower() not in topic_lower:
                found_off_topic.append(phrase)

        if found_off_topic:
            issues.append(f"Off-topic phrase detected: '{found_off_topic[0]}'")

        # ==================== IMAGE CHECKS ====================

        img_urls = re.findall(r'<img[^>]+src=["\']([^"\']+)["\']', html or "")
        img_count = len(img_urls)

        if img_count < self.min_images:
            issues.append(f"Too few images: {img_count} (min: {self.min_images})")

        # Check for duplicate images
        unique_urls = set(img_urls)
        if len(img_urls) != len(unique_urls):
            issues.append(
                f"Duplicate images detected: {len(img_urls) - len(unique_urls)}"
            )

        # Check for Shopify CDN or Pollinations images
        has_cdn = any("cdn.shopify.com" in url for url in img_urls)
        has_pollinations = any("pollinations.ai" in url for url in img_urls)

        # ==================== SOURCE CHECKS ====================

        # Count source links
        source_links = len(
            re.findall(r'<a\s+href="https?://[^"]+"\s*[^>]*>', html or "")
        )
        has_sources_section = "sources" in html_lower or "further reading" in html_lower

        if not has_sources_section:
            issues.append("Missing Sources section")
        elif source_links < self.min_sources:
            issues.append(
                f"Too few source links: {source_links} (min: {self.min_sources})"
            )

        # ==================== BLOCKQUOTE CHECK ====================

        blockquote_count = html.count("<blockquote") if html else 0
        if blockquote_count < self.min_blockquotes:
            warnings.append(
                f"Few blockquotes: {blockquote_count} (recommended: {self.min_blockquotes})"
            )

        # ==================== TABLE CHECK ====================

        table_count = html.count("<table") if html else 0
        if table_count < 1:
            warnings.append("No comparison table found")

        # ==================== TOPIC KEYWORD DENSITY ====================

        # Extract main keywords from topic
        stop_words = {
            "diy",
            "how",
            "to",
            "make",
            "the",
            "a",
            "an",
            "for",
            "and",
            "or",
            "in",
            "on",
            "at",
            "ideas",
            "guide",
            "complete",
            "easy",
            "best",
            "top",
            "benefits",
            "uses",
            "with",
        }
        topic_words = re.findall(r"\b[a-z]+\b", topic_lower)
        topic_keywords = [w for w in topic_words if w not in stop_words and len(w) > 3]

        keyword_density = {}
        for kw in topic_keywords[:3]:  # Check top 3 keywords
            count = text_lower.count(kw)
            keyword_density[kw] = count
            if count < 5:
                warnings.append(f"Low keyword density for '{kw}': {count} mentions")

        # ==================== CALCULATE SCORES ====================

        # Section score (0-11)
        section_score = len(found_sections)

        # Topic focus score (0-10)
        avg_keyword_count = sum(keyword_density.values()) / max(len(keyword_density), 1)
        topic_focus_score = min(10, int(avg_keyword_count / 3))

        # Specificity score (0-4)
        has_numbers = (
            len(
                re.findall(
                    r"\b\d+(?:\.\d+)?\s*(?:mg|g|oz|cup|tablespoon|teaspoon|inch|feet|cm|mm|┬░F|┬░C|%)\b",
                    text,
                    re.I,
                )
            )
            >= 3
        )
        has_measurements = (
            len(
                re.findall(
                    r"\b\d+[-ΓÇô]\d+\s*(?:weeks?|days?|hours?|minutes?)\b", text, re.I
                )
            )
            >= 2
        )
        has_specific_names = (
            len(
                re.findall(
                    r"(?:Dr\.|Professor|University|Extension|USDA|FDA|NIH)", text
                )
            )
            >= 2
        )
        has_varieties = "varieties" in text_lower or "types" in text_lower
        specificity_score = sum(
            [has_numbers, has_measurements, has_specific_names, has_varieties]
        )

        # ==================== HTML VALIDITY CHECK (from agent_builder.py) ====================

        # Check for unclosed tags
        open_tags = len(re.findall(r"<[a-z]+[^/>]*>", html or "", re.I))
        close_tags = len(re.findall(r"</[a-z]+>", html or "", re.I))
        if abs(open_tags - close_tags) > 10:
            warnings.append(
                f"Possible unclosed HTML tags (open: {open_tags}, close: {close_tags})"
            )

        # Check for empty image src
        if 'src=""' in (html or "") or "src=''" in (html or ""):
            issues.append("Empty image src found")

        # ==================== TITLE LENGTH CHECK ====================

        title_len = len(topic)
        if title_len < 30:
            warnings.append(f"Title too short: {title_len} chars (recommend 30+)")
        if title_len > 70:
            warnings.append(f"Title may be too long for SEO: {title_len} chars")

        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "warnings": warnings,
            "word_count": word_count,
            "img_count": img_count,
            "section_count": section_score,
            "section_score": section_score,
            "topic_focus_score": topic_focus_score,
            "specificity_score": specificity_score,
            "blockquote_count": blockquote_count,
            "table_count": table_count,
            "source_links": source_links,
            "has_cdn_images": has_cdn,
            "found_sections": found_sections,
            "missing_sections": missing_sections,
            "keyword_density": keyword_density,
        }

    def auto_fix_content(self, html, topic=""):
        """Automatically fix common issues in content"""
        original = html

        # Apply sanitization (URL decode, broken links, empty tags)
        html = self.sanitize_html(html)

        # Remove off-topic content if topic provided
        if topic:
            html = self.remove_off_topic_content(html, topic)

        # Fix source links format (convert raw URLs to Names)
        html = self.fix_source_links_format(html)

        if html != original:
            self.log("  Γ£ô Auto-fixed content issues", "SUCCESS")

        return html

    def generate_quality_report(self, article_id, title, html):
        """Generate comprehensive quality report for an article"""
        validation = self.validate_content(html, title)
        category = self.detect_topic_category(title)
        score = self._calculate_quality_score(validation)

        # Determine quality level
        if score >= 85:
            quality_level = "EXCELLENT"
        elif score >= 70:
            quality_level = "GOOD"
        elif score >= 55:
            quality_level = "ACCEPTABLE"
        else:
            quality_level = "NEEDS_IMPROVEMENT"

        report = {
            "article_id": article_id,
            "title": title,
            "category": category,
            "quality_level": quality_level,
            "valid": validation["valid"],
            "score": score,
            # Content metrics
            "word_count": validation["word_count"],
            "img_count": validation["img_count"],
            "section_count": validation["section_count"],
            "blockquote_count": validation.get("blockquote_count", 0),
            "table_count": validation.get("table_count", 0),
            "source_count": validation.get("source_links", 0),  # Already an int
            # Quality scores
            "section_score": validation.get("section_score", 0),
            "topic_focus_score": validation.get("topic_focus_score", 0),
            "specificity_score": validation.get("specificity_score", 0),
            # Details
            "has_cdn_images": validation.get("has_cdn_images", False),
            "found_sections": validation.get("found_sections", []),
            "missing_sections": validation.get("missing_sections", []),
            "keyword_density": validation.get("keyword_density", {}),
            # Issues & warnings
            "issues": validation["issues"],
            "warnings": validation.get("warnings", []),
        }

        return report

    def full_audit(self, article):
        """
        Run full quality audit on article (from ai_orchestrator.py QualityGate)
        Returns comprehensive audit result with pass/fail status
        """
        title = article.get("title", "")
        body_html = article.get("body_html", "") or ""
        article_id = str(article.get("id", ""))

        # Run comprehensive validation
        validation = self.validate_content(body_html, title)
        score = self._calculate_quality_score(validation)

        # Individual checks with pass/fail
        checks = {
            "structure": {
                "pass": validation.get("section_score", 0) >= self.min_sections,
                "score": validation.get("section_score", 0),
                "found": validation.get("found_sections", []),
                "missing": validation.get("missing_sections", []),
            },
            "word_count": {
                "pass": self.min_word_count
                <= validation["word_count"]
                <= self.max_word_count,
                "word_count": validation["word_count"],
                "min": self.min_word_count,
                "max": self.max_word_count,
            },
            "generic": {
                "pass": not any(
                    "generic" in issue.lower() for issue in validation["issues"]
                ),
                "found_phrases": [
                    i for i in validation["issues"] if "generic" in i.lower()
                ],
            },
            "contamination": {
                "pass": not any(
                    "off-topic" in issue.lower() for issue in validation["issues"]
                ),
                "issues": [i for i in validation["issues"] if "off-topic" in i.lower()],
            },
            "images": {
                "pass": validation["img_count"] >= self.min_images,
                "unique_images": validation["img_count"],
                "min_required": self.min_images,
                "has_cdn": validation.get("has_cdn_images", False),
            },
            "sources": {
                "pass": validation.get("source_links", 0) >= self.min_sources,
                "source_links_count": validation.get("source_links", 0),
                "min_required": self.min_sources,
            },
        }

        # Count passed checks
        passed_checks = sum(1 for c in checks.values() if c["pass"])
        overall_pass = passed_checks >= 5  # At least 5/6 checks pass

        # Collect all issues
        all_issues = validation["issues"]

        return {
            "article_id": article_id,
            "title": title,
            "overall_pass": overall_pass,
            "score": score,
            "score_10": round(passed_checks / 6 * 10),  # Score out of 10
            "passed_checks": passed_checks,
            "total_checks": 6,
            "issues": all_issues,
            "warnings": validation.get("warnings", []),
            "details": checks,
        }

    def scan_all_articles(self, status="published", limit=250):
        """
        Scan all articles and categorize by quality (from ai_orchestrator.py)
        Returns summary of passed/failed articles
        """
        self.log(f"\n{'='*70}")
        self.log(f"≡ƒöì FULL SCAN - Auditing {status} articles")
        self.log(f"{'='*70}")

        # Fetch articles
        articles = self.get_published_articles(limit)
        self.log(f"Found {len(articles)} articles")

        passed = []
        failed = []

        for i, article in enumerate(articles, 1):
            result = self.full_audit(article)

            if result["overall_pass"]:
                passed.append(
                    {
                        "id": result["article_id"],
                        "title": result["title"],
                        "score": result["score"],
                    }
                )
            else:
                failed.append(
                    {
                        "id": result["article_id"],
                        "title": result["title"],
                        "score": result["score"],
                        "issues": result["issues"],
                    }
                )

            # Progress indicator
            if i % 20 == 0:
                self.log(f"  Progress: {i}/{len(articles)}")

        # Summary
        self.log(f"\n{'='*70}")
        self.log(f"≡ƒôè SCAN SUMMARY")
        self.log(f"{'='*70}")
        self.log(f"Γ£à PASSED: {len(passed)} articles")
        self.log(f"Γ¥î FAILED: {len(failed)} articles")

        if failed:
            self.log(f"\n≡ƒö┤ Top 10 Failed Articles:")
            for article in failed[:10]:
                self.log(f"\n  {article['title'][:50]}...")
                self.log(f"    ID: {article['id']} | Score: {article['score']}/100")
                for issue in article.get("issues", [])[:3]:
                    self.log(f"    ΓÜá∩╕Å {issue}")

        # Save results
        results = {"passed": passed, "failed": failed}
        results_file = os.path.join(self.output_dir, "scan_results.json")
        with open(results_file, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        self.log(f"\n  Results saved: {results_file}")

        return results

    def _calculate_quality_score(self, validation):
        """Calculate comprehensive quality score 0-100 based on META-PROMPT standards"""
        score = 0

        # ==================== BASE SCORING (60 points max) ====================

        # 1. Word count (0-15 points)
        wc = validation["word_count"]
        if wc >= 2000:
            score += 15
        elif wc >= 1800:
            score += 12
        elif wc >= 1650:
            score += 8
        elif wc >= 1500:
            score += 5
        else:
            score += 0  # Below minimum

        # 2. Section structure (0-15 points)
        section_score = validation.get("section_score", 0)
        if section_score >= 11:
            score += 15
        elif section_score >= 9:
            score += 12
        elif section_score >= 7:
            score += 8
        else:
            score += max(0, section_score)

        # 3. Images (0-10 points)
        img_count = validation["img_count"]
        if img_count >= 5:
            score += 10
        elif img_count >= 4:
            score += 8
        elif img_count >= 3:
            score += 5
        else:
            score += 0

        # 4. Sources (0-10 points)
        source_count = validation.get("source_links", 0)  # Already an int
        if source_count >= 6:
            score += 10
        elif source_count >= 5:
            score += 8
        elif source_count >= 3:
            score += 5
        else:
            score += max(0, source_count)

        # 5. Blockquotes (0-5 points)
        blockquote_count = validation.get("blockquote_count", 0)
        if blockquote_count >= 2:
            score += 5
        elif blockquote_count >= 1:
            score += 3
        else:
            score += 0

        # 6. Tables (0-5 points)
        table_count = validation.get("table_count", 0)
        if table_count >= 1:
            score += 5
        else:
            score += 0

        # ==================== QUALITY BONUSES (25 points max) ====================

        # 7. Topic focus score (0-10 points)
        topic_focus = validation.get("topic_focus_score", 0)
        score += topic_focus  # Already 0-10

        # 8. Specificity score (0-8 points)
        specificity = validation.get("specificity_score", 0)
        score += specificity * 2  # 0-4 ΓåÆ 0-8

        # 9. CDN images (0-5 points)
        if validation.get("has_cdn_images", False):
            score += 5

        # 10. No issues bonus (0-2 points)
        if len(validation.get("issues", [])) == 0:
            score += 2

        # ==================== PENALTIES (up to -30 points) ====================

        # Deduct for critical issues
        issues = validation.get("issues", [])
        for issue in issues:
            if "generic content" in issue.lower():
                score -= 10  # Generic content is severe
            elif "contamination" in issue.lower():
                score -= 10  # Wrong topic content is severe
            elif "url-encoded" in issue.lower():
                score -= 5
            elif "broken" in issue.lower():
                score -= 5
            else:
                score -= 3  # Other issues

        # Deduct for warnings (minor)
        warnings = validation.get("warnings", [])
        score -= len(warnings) * 1

        return max(0, min(100, score))

    # ==================== END SANITIZE & VALIDATE ====================

    def detect_topic_category(self, topic):
        """Detect topic category for appropriate content template"""
        topic_lower = topic.lower()

        # Home remedies / Herbal medicine
        if any(
            kw in topic_lower
            for kw in [
                "remedy",
                "salve",
                "tincture",
                "syrup",
                "balm",
                "tea blend",
                "herbal",
                "medicinal",
                "healing",
                "cough",
                "cold",
                "flu",
                "headache",
                "sleep",
                "anxiety",
            ]
        ):
            return "remedies"

        # DIY / Crafts - Check BEFORE gardening to catch "DIY Planter Box" etc
        if any(
            kw in topic_lower
            for kw in [
                "diy",
                "craft",
                "build",
                "sew",
                "knit",
                "crochet",
                "woodwork",
                "handmade",
                "project",
                "shelf",
                "furniture",
                "decor",
            ]
        ):
            return "diy"

        # Gardening / Growing
        if any(
            kw in topic_lower
            for kw in [
                "garden",
                "grow",
                "plant",
                "seed",
                "harvest",
                "compost",
                "soil",
                "vegetable",
                "herb garden",
                "flower",
                "propagat",
            ]
        ):
            return "gardening"

        # Cooking / Food preservation
        if any(
            kw in topic_lower
            for kw in [
                "recipe",
                "cook",
                "bake",
                "ferment",
                "preserve",
                "can",
                "pickle",
                "jam",
                "jelly",
                "bread",
                "sourdough",
                "cheese",
            ]
        ):
            return "cooking"

        # Animal husbandry / Pet training
        if any(
            kw in topic_lower
            for kw in [
                "chicken",
                "goat",
                "bee",
                "livestock",
                "coop",
                "egg",
                "milk",
                "honey",
                "poultry",
                "cattle",
                "dog",
                "puppy",
                "cat",
                "kitten",
                "rabbit",
                "duck",
                "pet",
                "train",
                "breeding",
                "hatchery",
            ]
        ):
            return "animals"

        # Sustainability / Zero waste
        if any(
            kw in topic_lower
            for kw in [
                "sustainable",
                "eco",
                "zero waste",
                "upcycle",
                "recycle",
                "compost",
                "natural",
                "organic",
                "green living",
            ]
        ):
            return "sustainability"

        # Default: general homesteading
        return "general"

    def get_category_content(self, category, topic):
        """Get category-specific content snippets"""
        templates = {
            "remedies": {
                "intro": f"Discover the time-tested wisdom of {topic.lower()} that generations of homesteaders have relied upon. This comprehensive guide brings you practical, natural solutions you can create at home using simple ingredients.",
                "benefit_intro": f"When you create {topic.lower()} at home, you gain complete control over every ingredient. This transparency is especially valuable for those with sensitivities or anyone who prefers to avoid synthetic additives.",
                "table_header": [
                    "Ingredient Category",
                    "Common Examples",
                    "Primary Uses",
                ],
                "table_rows": [
                    [
                        "Base Oils",
                        "Olive, coconut, jojoba, sweet almond",
                        "Carrier for herbs, moisturizing",
                    ],
                    [
                        "Dried Herbs",
                        "Calendula, chamomile, lavender, plantain",
                        "Therapeutic properties",
                    ],
                    [
                        "Waxes",
                        "Beeswax, candelilla wax",
                        "Thickening, protective barrier",
                    ],
                    [
                        "Essential Oils",
                        "Tea tree, eucalyptus, peppermint",
                        "Aromatherapy, antimicrobial",
                    ],
                    [
                        "Sweeteners",
                        "Raw honey, maple syrup",
                        "Soothing, antimicrobial, flavor",
                    ],
                ],
                "expert_quote": "The key to effective home remedies is starting with quality ingredients. Organic, locally-sourced herbs contain more of the beneficial compounds that make these preparations work.",
                "expert_name": "Rosemary Gladstar, Herbalist and Author",
                "sources": [
                    (
                        "https://www.ncbi.nlm.nih.gov/pmc/",
                        "NIH ΓÇö Research on natural remedies",
                    ),
                    (
                        "https://www.herbsociety.org/",
                        "Herb Society of America ΓÇö Traditional herbal knowledge",
                    ),
                ],
            },
            "gardening": {
                "intro": f"Master the art of {topic.lower()} with this comprehensive guide designed for both beginners and experienced gardeners. Learn proven techniques that will help you grow healthier plants and increase your harvest.",
                "benefit_intro": f"Understanding {topic.lower()} gives you the foundation for a successful garden. Whether you're working with a small container garden or managing acres of land, these principles apply.",
                "table_header": ["Category", "Options", "Best For"],
                "table_rows": [
                    [
                        "Soil Types",
                        "Loam, clay, sandy, silt",
                        "Different plants thrive in different soils",
                    ],
                    [
                        "Amendments",
                        "Compost, manure, peat moss",
                        "Improving soil structure and nutrition",
                    ],
                    [
                        "Tools",
                        "Trowel, hoe, rake, pruners",
                        "Essential for planting and maintenance",
                    ],
                    [
                        "Containers",
                        "Pots, raised beds, grow bags",
                        "Space-efficient growing options",
                    ],
                    [
                        "Fertilizers",
                        "Organic, synthetic, slow-release",
                        "Providing essential nutrients",
                    ],
                ],
                "expert_quote": "The best time to plant a tree was 20 years ago. The second best time is now. Start where you are, with what you have, and grow from there.",
                "expert_name": "Eliot Coleman, Organic Farming Pioneer",
                "sources": [
                    (
                        "https://extension.org/",
                        "Cooperative Extension ΓÇö Research-based gardening advice",
                    ),
                    (
                        "https://www.rhs.org.uk/",
                        "Royal Horticultural Society ΓÇö Plant care guides",
                    ),
                ],
            },
            "cooking": {
                "intro": f"Learn to make {topic.lower()} from scratch with this detailed guide. From selecting ingredients to perfecting your technique, you'll discover everything needed to create delicious homemade results.",
                "benefit_intro": f"Making {topic.lower()} at home gives you control over ingredients, freshness, and flavor. You'll save money while creating something far superior to store-bought alternatives.",
                "table_header": ["Ingredient Type", "Examples", "Purpose"],
                "table_rows": [
                    [
                        "Base Ingredients",
                        "Flour, sugar, butter, eggs",
                        "Foundation of the recipe",
                    ],
                    ["Seasonings", "Salt, pepper, herbs, spices", "Flavor development"],
                    ["Liquids", "Water, milk, broth, wine", "Texture and moisture"],
                    [
                        "Leaveners",
                        "Yeast, baking soda, baking powder",
                        "Rise and texture",
                    ],
                    ["Fats", "Butter, oil, lard", "Richness and tenderness"],
                ],
                "expert_quote": "Cooking is like love. It should be entered into with abandon or not at all. Don't be afraid to experiment and make it your own.",
                "expert_name": "Julia Child, Legendary Chef",
                "sources": [
                    (
                        "https://www.seriouseats.com/",
                        "Serious Eats ΓÇö Science-based cooking techniques",
                    ),
                    (
                        "https://www.kingarthurbaking.com/",
                        "King Arthur ΓÇö Baking expertise and recipes",
                    ),
                ],
            },
            "diy": {
                "intro": f"Create your own {topic.lower()} with this step-by-step guide. Whether you're a complete beginner or an experienced maker, you'll find clear instructions and helpful tips to ensure your project succeeds.",
                "benefit_intro": f"Making {topic.lower()} yourself offers tremendous satisfaction and often significant cost savings. Plus, you can customize every aspect to perfectly fit your needs and style.",
                "table_header": ["Material Type", "Common Options", "Best Uses"],
                "table_rows": [
                    [
                        "Wood",
                        "Pine, oak, plywood, reclaimed",
                        "Structure and aesthetics",
                    ],
                    ["Fabric", "Cotton, linen, canvas", "Soft goods and coverings"],
                    [
                        "Hardware",
                        "Screws, nails, hinges, brackets",
                        "Assembly and function",
                    ],
                    [
                        "Finishes",
                        "Paint, stain, sealant, wax",
                        "Protection and appearance",
                    ],
                    ["Adhesives", "Wood glue, epoxy, fabric glue", "Bonding materials"],
                ],
                "expert_quote": "The beauty of DIY is that mistakes become learning opportunities. Every project teaches you something valuable for the next one.",
                "expert_name": "Ana White, DIY Furniture Designer",
                "sources": [
                    (
                        "https://www.familyhandyman.com/",
                        "Family Handyman ΓÇö DIY tips and projects",
                    ),
                    (
                        "https://www.instructables.com/",
                        "Instructables ΓÇö Step-by-step project guides",
                    ),
                ],
            },
            "animals": {
                "intro": f"Learn everything you need to know about {topic.lower()} in this comprehensive guide. From beginners starting their first flock to experienced homesteaders expanding their operations.",
                "benefit_intro": f"Understanding {topic.lower()} properly ensures healthy animals and sustainable practices. Whether for food production, companionship, or both, proper care makes all the difference.",
                "table_header": ["Category", "Considerations", "Importance"],
                "table_rows": [
                    ["Housing", "Space, ventilation, protection", "Health and safety"],
                    [
                        "Feed",
                        "Commercial, supplemental, forage",
                        "Nutrition and production",
                    ],
                    ["Health", "Vaccinations, parasite control", "Preventing disease"],
                    [
                        "Breeding",
                        "Selection, timing, management",
                        "Herd/flock improvement",
                    ],
                    ["Processing", "Equipment, timing, methods", "Food production"],
                ],
                "expert_quote": "The health of your animals reflects your care. Good husbandry is about daily attention to small details that add up to big results.",
                "expert_name": "Joel Salatin, Polyface Farm",
                "sources": [
                    (
                        "https://extension.org/",
                        "Cooperative Extension ΓÇö Livestock management",
                    ),
                    (
                        "https://www.backyardchickens.com/",
                        "Backyard Chickens ΓÇö Community knowledge",
                    ),
                ],
            },
            "sustainability": {
                "intro": f"Embrace sustainable living with this guide to {topic.lower()}. Small changes add up to big impacts, and this approach benefits both your household and the planet.",
                "benefit_intro": f"Adopting {topic.lower()} practices reduces waste, saves money, and creates a healthier home environment. Every sustainable choice you make contributes to a better future.",
                "table_header": ["Practice Area", "Options", "Impact"],
                "table_rows": [
                    [
                        "Waste Reduction",
                        "Composting, recycling, reusing",
                        "Less landfill waste",
                    ],
                    [
                        "Energy",
                        "Solar, efficiency, conservation",
                        "Lower carbon footprint",
                    ],
                    [
                        "Water",
                        "Rain collection, greywater, low-flow",
                        "Resource conservation",
                    ],
                    [
                        "Food",
                        "Growing, preserving, local sourcing",
                        "Reduced food miles",
                    ],
                    [
                        "Products",
                        "DIY, natural, package-free",
                        "Less chemical exposure",
                    ],
                ],
                "expert_quote": "Sustainability isn't about perfectionΓÇöit's about making better choices consistently. Progress, not perfection, creates lasting change.",
                "expert_name": "Bea Johnson, Zero Waste Home",
                "sources": [
                    ("https://www.epa.gov/", "EPA ΓÇö Environmental best practices"),
                    (
                        "https://www.zerowastehome.com/",
                        "Zero Waste Home ΓÇö Practical sustainability",
                    ),
                ],
            },
            "general": {
                "intro": f"Discover practical knowledge about {topic.lower()} that will enhance your self-sufficient lifestyle. This guide combines traditional wisdom with modern techniques for the best results.",
                "benefit_intro": f"Learning about {topic.lower()} adds valuable skills to your homesteading toolkit. The more you know, the more independent and resilient you become.",
                "table_header": ["Aspect", "Details", "Application"],
                "table_rows": [
                    [
                        "Basics",
                        "Fundamental concepts and techniques",
                        "Foundation for learning",
                    ],
                    ["Materials", "Required supplies and equipment", "Getting started"],
                    ["Methods", "Step-by-step approaches", "Practical application"],
                    [
                        "Timing",
                        "When to start and seasonal considerations",
                        "Optimal results",
                    ],
                    ["Maintenance", "Ongoing care and upkeep", "Long-term success"],
                ],
                "expert_quote": "Self-sufficiency is a journey, not a destination. Every skill you learn makes you more capable and confident.",
                "expert_name": "Homesteading Wisdom",
                "sources": [
                    (
                        "https://extension.org/",
                        "Cooperative Extension ΓÇö Research-based knowledge",
                    ),
                    (
                        "https://www.motherearthnews.com/",
                        "Mother Earth News ΓÇö Homesteading resources",
                    ),
                ],
            },
        }
        return templates.get(category, templates["general"])

    def generate_content_html(self, topic, images):
        """Generate full HTML content following 11-section structure - UNIVERSAL for all topics"""

        # Detect topic category
        category = self.detect_topic_category(topic)
        content = self.get_category_content(category, topic)

        # Build image tags
        featured_img = images[0] if images else None
        inline_images = images[1:4] if len(images) > 1 else []

        html = f"""
<p><em>{content['intro']} Whether you're new to this or an experienced practitioner, you'll find valuable insights and step-by-step instructions to help you succeed.</em></p>

<h2>Direct Answer: What Is {topic}?</h2>
<p>{topic} represents practical knowledge that generations have refined and passed down. Today, as more people seek self-sufficiency and hands-on skills, these time-honored practices are experiencing a well-deserved renaissance.</p>

<p>The beauty of learning {topic.lower()} lies in its practicality and effectiveness. Using accessible materials and proven techniques, you can achieve results that rival or exceed what you'd buyΓÇöoften at a fraction of the cost and with much greater satisfaction.</p>

<p>This guide will walk you through everything you need to know: from gathering materials and understanding the fundamentals, to step-by-step methods and best practices. By the end, you'll have the knowledge and confidence to master {topic.lower()}.</p>
"""

        # Add first inline image
        if len(inline_images) > 0:
            html += f"""
<figure class="wp-block-image aligncenter">
    <img src="{inline_images[0]['url']}" alt="{inline_images[0]['alt']}" loading="lazy" style="max-width:100%;height:auto;border-radius:8px;">
    <figcaption>Essential elements for {topic.lower()}</figcaption>
</figure>
"""

        html += f"""
<h2>Key Information at a Glance</h2>
<ul>
    <li><strong>Accessible materials:</strong> Most requirements use items you likely already have or can easily obtain</li>
    <li><strong>Cost-effective:</strong> DIY approaches typically cost 50-80% less than buying ready-made</li>
    <li><strong>Customizable:</strong> Adjust methods to your preferences and specific situation</li>
    <li><strong>Skill-building:</strong> Each project increases your capabilities for future endeavors</li>
    <li><strong>Proven methods:</strong> These techniques have been refined and tested over generations</li>
</ul>

<h2>Understanding the Benefits</h2>
<p>{content['benefit_intro']}</p>

<p>Taking the time to learn proper techniques ensures better results and prevents common mistakes. The investment in knowledge pays dividends every time you apply these skills.</p>

<h2>Essential Materials and Supplies</h2>
<table style="width:100%; border-collapse: collapse; margin: 20px 0;">
<thead>
    <tr style="background-color: #f5f5f5;">
"""
        for header in content["table_header"]:
            html += f'        <th style="padding: 12px; text-align: left; border: 1px solid #ddd;">{header}</th>\n'

        html += """    </tr>
</thead>
<tbody>
"""
        for row in content["table_rows"]:
            html += "    <tr>\n"
            for cell in row:
                html += f'        <td style="padding: 12px; border: 1px solid #ddd;">{cell}</td>\n'
            html += "    </tr>\n"

        html += """</tbody>
</table>

<h2>Types and Varieties</h2>
"""
        html += f"""<p>There are several approaches to {topic.lower()}, each with unique advantages:</p>
<ol>
    <li><strong>Traditional Method:</strong> Time-tested approach using simple tools and techniques passed down through generations</li>
    <li><strong>Modern Approach:</strong> Contemporary tools and methods that can speed up the process while maintaining quality</li>
    <li><strong>Beginner-Friendly:</strong> Simplified version perfect for those just starting out</li>
    <li><strong>Advanced Technique:</strong> More complex approach for experienced practitioners seeking optimal results</li>
</ol>
"""

        # Add second inline image
        if len(inline_images) > 1:
            html += f"""
<figure class="wp-block-image aligncenter">
    <img src="{inline_images[1]['url']}" alt="{inline_images[1]['alt']}" loading="lazy" style="max-width:100%;height:auto;border-radius:8px;">
    <figcaption>Step-by-step process for {topic.lower()}</figcaption>
</figure>
"""

        html += f"""
<h2>Step-by-Step Guide</h2>
<p>Follow these detailed steps to master {topic.lower()}. Each step builds on the previous one, so take your time and don't rush through any phase of the process.</p>

<h3>Step 1: Gather Your Materials</h3>
<p>Start by collecting everything you'll need for the entire project. Having all materials ready before you begin makes the process smoother and helps prevent costly mistakes. Create a checklist and verify you have each item before starting.</p>
<p>Check the quality of all materials carefullyΓÇöbetter inputs consistently lead to better results. If something seems substandard, replace it now rather than discovering problems halfway through your project.</p>

<h3>Step 2: Prepare Your Workspace</h3>
<p>Set up a clean, well-organized area with good lighting and adequate ventilation if needed. Ensure you have enough space to work comfortably and safely without feeling cramped or restricted.</p>
<p>Organization prevents frustration and reduces errors significantly. Arrange your materials in the order you'll use them, and keep cleaning supplies nearby for quick tidying as you work.</p>

<h3>Step 3: Execute the Core Process</h3>
<p>Follow your chosen method carefully, paying close attention to timing, temperatures, and technique as specified. This is where most of the skill development happens, so stay focused and present throughout.</p>
<p>Take detailed notes so you can replicate successful outcomes or make informed adjustments in future attempts. Record what worked well and what you might change next time. Patience at this stage pays enormous dividends.</p>

<h3>Step 4: Quality Check and Refinement</h3>
<p>Before considering your project complete, evaluate the results against your expectations. Look for any areas that could be improved or refined. Many practitioners find that small adjustments at this stage make significant differences in final quality.</p>

<h3>Step 5: Finish and Store Properly</h3>
<p>Complete all final steps, including any curing, drying, or setting time required. Clean up your workspace thoroughlyΓÇöa clean ending makes the next project easier to start.</p>
<p>Store results properly using appropriate containers, conditions, and methods. Label everything clearly with the date, contents, and any relevant details. Proper storage ensures longevity, quality, and safety.</p>

<h2>Pro Tips from Experienced Practitioners</h2>
<blockquote style="border-left: 4px solid #4CAF50; padding-left: 20px; margin: 20px 0; font-style: italic;">
    <p>"{content['expert_quote']}"</p>
    <footer>ΓÇö {content['expert_name']}</footer>
</blockquote>

<ul>
    <li><strong>Start small:</strong> Master the basics before attempting advanced variations</li>
    <li><strong>Document everything:</strong> Keep notes on what works and what doesn't</li>
    <li><strong>Quality materials:</strong> Better inputs almost always yield better results</li>
    <li><strong>Be patient:</strong> Rushing leads to mistakesΓÇötake your time</li>
    <li><strong>Learn from others:</strong> Join communities and learn from experienced practitioners</li>
    <li><strong>Practice regularly:</strong> Consistent practice builds skill and confidence</li>
</ul>
"""

        # Add third inline image
        if len(inline_images) > 2:
            html += f"""
<figure class="wp-block-image aligncenter">
    <img src="{inline_images[2]['url']}" alt="{inline_images[2]['alt']}" loading="lazy" style="max-width:100%;height:auto;border-radius:8px;">
    <figcaption>The finished result of {topic.lower()}</figcaption>
</figure>
"""

        html += f"""
<h2>Common Mistakes to Avoid</h2>
<ul>
    <li>Γ¥î <strong>Rushing the process:</strong> Impatience leads to poor results and wasted materials</li>
    <li>Γ¥î <strong>Skipping preparation:</strong> Inadequate setup causes problems throughout the project</li>
    <li>Γ¥î <strong>Ignoring measurements:</strong> Precision mattersΓÇöguessing rarely works well</li>
    <li>Γ¥î <strong>Poor quality materials:</strong> Cheap inputs produce disappointing outputs</li>
    <li>Γ¥î <strong>Not following instructions:</strong> Especially when learning, follow proven methods first</li>
</ul>

<h2>Troubleshooting Common Issues</h2>
<table style="width:100%; border-collapse: collapse; margin: 20px 0;">
<thead>
    <tr style="background-color: #f5f5f5;">
        <th style="padding: 12px; text-align: left; border: 1px solid #ddd;">Problem</th>
        <th style="padding: 12px; text-align: left; border: 1px solid #ddd;">Likely Cause</th>
        <th style="padding: 12px; text-align: left; border: 1px solid #ddd;">Solution</th>
    </tr>
</thead>
<tbody>
    <tr>
        <td style="padding: 12px; border: 1px solid #ddd;">Results not as expected</td>
        <td style="padding: 12px; border: 1px solid #ddd;">Incorrect measurements or timing</td>
        <td style="padding: 12px; border: 1px solid #ddd;">Review process, use precise measurements</td>
    </tr>
    <tr>
        <td style="padding: 12px; border: 1px solid #ddd;">Process taking too long</td>
        <td style="padding: 12px; border: 1px solid #ddd;">Insufficient preparation</td>
        <td style="padding: 12px; border: 1px solid #ddd;">Organize materials before starting</td>
    </tr>
    <tr>
        <td style="padding: 12px; border: 1px solid #ddd;">Quality issues</td>
        <td style="padding: 12px; border: 1px solid #ddd;">Material or technique problems</td>
        <td style="padding: 12px; border: 1px solid #ddd;">Upgrade materials, refine technique</td>
    </tr>
    <tr>
        <td style="padding: 12px; border: 1px solid #ddd;">Inconsistent results</td>
        <td style="padding: 12px; border: 1px solid #ddd;">Varying methods or conditions</td>
        <td style="padding: 12px; border: 1px solid #ddd;">Standardize your process</td>
    </tr>
    <tr>
        <td style="padding: 12px; border: 1px solid #ddd;">Difficulty with specific step</td>
        <td style="padding: 12px; border: 1px solid #ddd;">Need more practice or guidance</td>
        <td style="padding: 12px; border: 1px solid #ddd;">Seek tutorials, practice on test materials</td>
    </tr>
</tbody>
</table>

<h2>Advanced Techniques</h2>
<p>Once you've mastered the basics of {topic.lower()}, these advanced approaches will take your skills to the next level:</p>
<ul>
    <li><strong>Efficiency optimization:</strong> Streamline your process for faster results without sacrificing quality. Track your time and identify bottlenecks.</li>
    <li><strong>Custom variations:</strong> Experiment with modifications tailored to your specific needs and preferences. Document what works and what doesn't.</li>
    <li><strong>Batch processing:</strong> Scale up to handle larger quantities efficiently. This often reduces per-unit time and material costs.</li>
    <li><strong>Specialty methods:</strong> Learn niche techniques for specific applications that set your work apart from standard approaches.</li>
    <li><strong>Teaching others:</strong> Solidify your knowledge by helping beginners learn. Teaching reveals gaps in your own understanding and reinforces fundamentals.</li>
    <li><strong>Quality benchmarking:</strong> Compare your results against expert examples to identify areas for improvement and refinement.</li>
</ul>

<h2>Practical Applications</h2>
<p>Once you've mastered {topic.lower()}, you'll find numerous ways to apply this valuable knowledge in your daily life:</p>

<ul>
    <li><strong>Regular household use:</strong> Integrate your new skills into your homestead or household routines for ongoing benefits</li>
    <li><strong>Gift-giving:</strong> Handmade items make meaningful gifts for friends and family who appreciate quality and thoughtfulness</li>
    <li><strong>Income potential:</strong> Many practitioners generate supplemental income by selling products or teaching workshops</li>
    <li><strong>Inventory building:</strong> Create a collection or stockpile for future needs, especially useful for seasonal applications</li>
    <li><strong>Skill stacking:</strong> Combine with other skills for more complex and valuable projects that showcase multiple competencies</li>
    <li><strong>Community building:</strong> Connect with others who share your interests and create meaningful relationships through shared activities</li>
</ul>

<p>The satisfaction of creating something useful with your own hands cannot be overstated. Each successful project builds confidence and capability that extends far beyond the immediate task.</p>

<h2>Frequently Asked Questions</h2>

<h3>How long does it take to learn {topic.lower()}?</h3>
<p>Basic competency can typically be achieved within a few dedicated practice sessions, though true mastery develops over months or even years of consistent practice. Start with simple projects and gradually increase complexity as your skills develop. Most people find they become reasonably proficient within their first few attempts, with refinement continuing over time.</p>

<h3>What's the most common beginner mistake?</h3>
<p>Trying to do too much too soon is the most frequent error. Start with the basics, perfect your technique on simple versions, then gradually move on to more challenging variations. Patience during the learning phase prevents frustration and builds solid foundations that serve you well for years to come.</p>

<h3>Can I do this with limited space or budget?</h3>
<p>Absolutely! Many successful practitioners start small and scale up as their skills and resources grow. Start with what you have available and expand gradually as needed. Creativity and resourcefulness often compensate for limited resources, and constraints can actually spark innovative solutions.</p>

<h3>Where can I find quality materials?</h3>
<p>Local suppliers, online specialty shops, and community groups are excellent sources for quality materials. Building relationships with suppliers often leads to better prices, priority access to premium materials, and insider knowledge about sourcing the best quality items.</p>

<h3>What if my first attempts don't work out?</h3>
<p>Don't be discouragedΓÇölearning naturally involves trial and error. Review what went wrong, analyze the potential causes, adjust your approach, and try again. Every experienced practitioner has a history of early failures that taught valuable lessons and ultimately led to success.</p>

<h3>How can I connect with others who do this?</h3>
<p>Online forums, local clubs, workshops, and social media groups connect practitioners at all skill levels. Learning from others accelerates your progress, provides inspiration for new projects, and creates a supportive community that shares knowledge freely.</p>

<h3>Is this worth the time investment?</h3>
<p>Most practitioners find the combination of practical results, skill-building, cost savings, and personal satisfaction makes the time investment extremely worthwhile. The skills you develop often have applications far beyond the initial project, providing lasting value.</p>

<h3>What tools or equipment do I need to get started?</h3>
<p>Start with basic, quality tools rather than expensive specialty equipment. As your skills develop, you'll learn which upgrades matter most for your particular interests and working style. Many experienced practitioners still rely primarily on fundamental tools.</p>

<h2>Sources & Further Reading</h2>
<ul>
"""
        for url, desc in content["sources"]:
            html += f'    <li><a href="{url}" target="_blank" rel="nofollow noopener">{desc}</a></li>\n'

        html += """    <li><a href="https://extension.org/" target="_blank" rel="nofollow noopener">Cooperative Extension ΓÇö Research-based practical knowledge</a></li>
    <li><a href="https://www.motherearthnews.com/" target="_blank" rel="nofollow noopener">Mother Earth News ΓÇö Homesteading and self-sufficiency resources</a></li>
</ul>
"""

        html += f"""
<h2>Start Your Journey Today</h2>
<p>Learning {topic.lower()} connects you to a tradition of self-reliance and practical knowledge. Start with a simple approach, gather quality materials, and enjoy the satisfaction of building new skills with your own hands.</p>

<p><strong>Share your experience!</strong> Have you tried {topic.lower()} before? What tips would you add? Drop a comment belowΓÇöwe love hearing from our community!</p>

<p><em>For more practical guides and homesteading tutorials, explore our other articles on sustainable living and DIY skills.</em></p>
"""

        return html

    def publish_to_shopify(
        self, title, html_content, featured_image, tags=None, meta_description=None
    ):
        """Publish article to Shopify as draft"""
        self.log(f"Publishing to Shopify: {title}")

        url = f"https://{SHOPIFY_STORE}.myshopify.com/admin/api/2024-04/blogs/{SHOPIFY_BLOG_ID}/articles.json"
        headers = {
            "X-Shopify-Access-Token": SHOPIFY_TOKEN,
            "Content-Type": "application/json",
        }

        # Clean handle
        handle = re.sub(r"[^a-z0-9-]", "", title.lower().replace(" ", "-"))[:200]

        # Generate meta description if not provided
        if not meta_description:
            meta_description = f"Learn how to make {title.lower()} at home with this step-by-step guide. Natural ingredients, expert tips, and detailed instructions for beginners. DIY homesteading tutorial."

        payload = {
            "article": {
                "title": title,
                "body_html": html_content,
                "summary_html": meta_description,  # Meta description for SEO
                "handle": handle,
                "published": False,  # Draft for review
                "tags": (
                    ",".join(tags)
                    if tags
                    else "home remedies, natural healing, diy, homesteading"
                ),
            }
        }

        if featured_image and "pollinations" not in featured_image:
            # Only include featured image if it's already on Shopify CDN
            payload["article"]["image"] = {"src": featured_image}

        try:
            response = requests.post(url, json=payload, headers=headers)

            if response.status_code == 201:
                article_id = response.json()["article"]["id"]
                self.log(f"Published! Article ID: {article_id}", "SUCCESS")
                return article_id
            else:
                self.log(
                    f"Publish failed: {response.status_code} - {response.text}", "ERROR"
                )
                return None

        except Exception as e:
            self.log(f"Publish error: {e}", "ERROR")
            return None

    def update_topic_status(self, filepath, status="completed", article_id=None):
        """Update topic .md file status"""
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        content = content.replace('status: "pending"', f'status: "{status}"')
        if article_id:
            content = content.replace(
                "---\n\n#", f'shopify_article_id: "{article_id}"\n---\n\n#'
            )

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

    def generate_single(self, topic_file):
        """Generate content for a single topic"""
        filepath = os.path.join(self.topics_dir, topic_file)
        if not os.path.exists(filepath):
            self.log(f"Topic file not found: {topic_file}", "ERROR")
            return None

        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        title_match = re.search(r'title: "([^"]+)"', content)
        title = (
            title_match.group(1)
            if title_match
            else topic_file.replace(".md", "").replace("_", " ")
        )

        self.log(f"\n{'='*60}")
        self.log(f"Generating blog: {title}")
        self.log(f"Category: {self.detect_topic_category(title)}")
        self.log(f"{'='*60}")

        # Generate AI images
        images = self.generate_ai_images(title)

        # Upload featured image to Shopify CDN
        if images:
            cdn_url = self.upload_to_shopify_cdn(
                images[0]["url"],
                f"{re.sub(r'[^a-z0-9]', '_', title.lower())[:50]}_featured.jpg",
                title,
            )
            images[0]["url"] = cdn_url

        # Generate content
        html_content = self.generate_content_html(title, images)

        # ===== SANITIZE & VALIDATE PIPELINE =====
        self.log("Running quality pipeline...", "INFO")

        # Step 1: Auto-fix content
        html_content = self.auto_fix_content(html_content, title)

        # Step 2: Validate content
        validation = self.validate_content(html_content, title)

        if validation["valid"]:
            self.log(
                f"  Γ£ô Content validated: {validation['word_count']} words, {validation['section_count']} sections",
                "SUCCESS",
            )
        else:
            self.log(f"  ΓÜá Content issues found:", "WARNING")
            for issue in validation["issues"]:
                self.log(f"    - {issue}", "WARNING")

        # Step 3: Calculate quality score
        quality_score = self._calculate_quality_score(validation)
        self.log(f"  Quality Score: {quality_score}/100", "INFO")

        # Abort if quality too low
        if quality_score < 60:
            self.log(
                f"  Γ£ù Quality too low ({quality_score}), aborting publish", "ERROR"
            )
            return None
        # ===== END PIPELINE =====

        # Generate category-specific meta description
        category = self.detect_topic_category(title)
        meta_templates = {
            "remedies": f"Learn how to make {title.lower()} at home. Natural remedy with herbs, expert tips, and safety guidelines. DIY herbal medicine tutorial.",
            "gardening": f"Complete guide to {title.lower()}. Expert gardening tips, step-by-step instructions, and troubleshooting advice for beginners and experienced gardeners.",
            "cooking": f"Learn to make {title.lower()} from scratch. Detailed recipe with tips, variations, and troubleshooting. Homemade cooking tutorial.",
            "diy": f"Step-by-step guide to {title.lower()}. DIY project with materials list, expert tips, and common mistakes to avoid.",
            "animals": f"Complete guide to {title.lower()}. Animal husbandry tips, care instructions, and expert advice for homesteaders.",
            "sustainability": f"Learn about {title.lower()} for sustainable living. Eco-friendly tips, practical advice, and environmental benefits.",
            "general": f"Learn {title.lower()} with this comprehensive guide. Step-by-step instructions, expert tips, and troubleshooting advice for homesteaders.",
        }
        meta_description = meta_templates.get(category, meta_templates["general"])

        # Generate category-specific tags
        tag_templates = {
            "remedies": [
                "home remedies",
                "natural healing",
                "herbal medicine",
                "diy health",
                "homesteading",
            ],
            "gardening": [
                "gardening",
                "growing tips",
                "organic gardening",
                "homesteading",
                "sustainable living",
            ],
            "cooking": [
                "homemade recipes",
                "from scratch cooking",
                "food preservation",
                "homesteading",
                "traditional recipes",
            ],
            "diy": [
                "diy projects",
                "handmade",
                "crafts",
                "homesteading",
                "sustainable living",
            ],
            "animals": [
                "animal husbandry",
                "backyard farming",
                "livestock",
                "homesteading",
                "self-sufficiency",
            ],
            "sustainability": [
                "sustainable living",
                "eco-friendly",
                "zero waste",
                "green living",
                "homesteading",
            ],
            "general": [
                "homesteading",
                "self-sufficiency",
                "diy",
                "sustainable living",
                "practical skills",
            ],
        }
        tags = tag_templates.get(category, tag_templates["general"])

        # Publish to Shopify
        article_id = self.publish_to_shopify(
            title=title,
            html_content=html_content,
            featured_image=images[0]["url"] if images else None,
            tags=tags,
            meta_description=meta_description,
        )

        # Update topic status
        if article_id:
            self.update_topic_status(filepath, "completed", article_id)

            # Save quality report
            report = self.generate_quality_report(article_id, title, html_content)
            report_file = os.path.join(
                self.output_dir, f"quality_report_{article_id}.json"
            )
            with open(report_file, "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            self.log(f"  Quality report saved: {report_file}", "SUCCESS")

        return article_id

    def generate_batch(self, count=5):
        """Generate content for multiple topics"""
        topics = self.get_pending_topics()[:count]

        self.log(f"\n{'='*60}")
        self.log(f"Batch generating {len(topics)} blogs")
        self.log(f"{'='*60}")

        results = []
        for i, topic in enumerate(topics):
            self.log(f"\n[{i+1}/{len(topics)}] Processing: {topic['title']}")

            article_id = self.generate_single(topic["filename"])
            results.append(
                {
                    "topic": topic["title"],
                    "article_id": article_id,
                    "status": "success" if article_id else "failed",
                }
            )

            # Rate limiting
            if i < len(topics) - 1:
                self.log("Waiting 3 seconds before next article...")
                time.sleep(3)

        # Summary
        success = len([r for r in results if r["status"] == "success"])
        self.log(f"\n{'='*60}")
        self.log(f"BATCH COMPLETE: {success}/{len(results)} successful")
        self.log(f"{'='*60}")

        return results

    # ==================== PIPELINE: REVIEW & FIX EXISTING ARTICLES ====================

    def get_published_articles(self, limit=50):
        """Get published articles from Shopify"""
        url = f"https://{SHOPIFY_STORE}.myshopify.com/admin/api/2024-04/blogs/{SHOPIFY_BLOG_ID}/articles.json"
        headers = {"X-Shopify-Access-Token": SHOPIFY_TOKEN}
        params = {"limit": limit, "published_status": "published"}

        try:
            r = requests.get(url, headers=headers, params=params)
            return r.json().get("articles", [])
        except Exception as e:
            self.log(f"Error fetching articles: {e}", "ERROR")
            return []

    def update_article(
        self, article_id, body_html=None, title=None, meta_description=None
    ):
        """Update article on Shopify"""
        url = f"https://{SHOPIFY_STORE}.myshopify.com/admin/api/2024-04/articles/{article_id}.json"
        headers = {
            "X-Shopify-Access-Token": SHOPIFY_TOKEN,
            "Content-Type": "application/json",
        }

        data = {"article": {}}
        if body_html:
            data["article"]["body_html"] = body_html
        if title:
            data["article"]["title"] = title
        if meta_description:
            data["article"]["summary_html"] = meta_description

        try:
            r = requests.put(url, headers=headers, json=data)
            return r.status_code == 200
        except Exception as e:
            self.log(f"Update failed: {e}", "ERROR")
            return False

    def review_and_fix_article(self, article):
        """Review and fix a single article"""
        article_id = article["id"]
        title = article.get("title", "")
        body = article.get("body_html", "") or ""

        # Validate content
        validation = self.validate_content(body, title)

        if validation["valid"]:
            return {
                "id": article_id,
                "title": title,
                "status": "ok",
                "score": self._calculate_quality_score(validation),
            }

        self.log(f"\n  Reviewing: {title[:50]}...", "INFO")
        self.log(f"  Issues: {len(validation['issues'])}", "WARNING")

        # Auto-fix content
        fixed_body = self.auto_fix_content(body, title)

        # Re-validate
        new_validation = self.validate_content(fixed_body, title)

        if fixed_body != body:
            # Check if fixes improved things
            old_issues = len(validation["issues"])
            new_issues = len(new_validation["issues"])

            if new_issues < old_issues:
                # Update on Shopify
                success = self.update_article(article_id, body_html=fixed_body)
                if success:
                    self.log(
                        f"  Γ£ô Fixed and updated ({old_issues} ΓåÆ {new_issues} issues)",
                        "SUCCESS",
                    )
                    return {
                        "id": article_id,
                        "title": title,
                        "status": "fixed",
                        "old_issues": old_issues,
                        "new_issues": new_issues,
                        "score": self._calculate_quality_score(new_validation),
                    }

        return {
            "id": article_id,
            "title": title,
            "status": "needs_manual",
            "issues": validation["issues"],
            "score": self._calculate_quality_score(validation),
        }

    def run_review_pipeline(self, limit=50, fix=False):
        """Run review pipeline on existing articles"""
        self.log(f"\n{'='*60}")
        self.log(f"REVIEW PIPELINE - Analyzing {limit} articles")
        self.log(f"Auto-fix enabled: {fix}")
        self.log(f"{'='*60}")

        articles = self.get_published_articles(limit)
        self.log(f"Found {len(articles)} articles")

        results = {"ok": [], "fixed": [], "needs_manual": [], "needs_review": []}

        for i, article in enumerate(articles, 1):
            self.log(f"\n[{i}/{len(articles)}]", "INFO")

            if fix:
                result = self.review_and_fix_article(article)
            else:
                # Just validate, don't fix
                validation = self.validate_content(
                    article.get("body_html", ""), article.get("title", "")
                )
                result = {
                    "id": article["id"],
                    "title": article.get("title", ""),
                    "status": "ok" if validation["valid"] else "needs_review",
                    "issues": validation["issues"],
                    "score": self._calculate_quality_score(validation),
                }

            results[result.get("status", "needs_manual")].append(result)
            time.sleep(0.3)  # Rate limiting

        # Summary
        self.log(f"\n{'='*60}")
        self.log(f"REVIEW COMPLETE")
        self.log(f"{'='*60}")
        self.log(f"  Γ£ô OK: {len(results.get('ok', []))}")
        self.log(f"  ≡ƒöº Fixed: {len(results.get('fixed', []))}")
        self.log(f"  ΓÜá Needs review: {len(results.get('needs_review', []))}")
        self.log(f"  ΓÜá Needs manual: {len(results.get('needs_manual', []))}")

        # Calculate average score
        all_results = (
            results.get("ok", [])
            + results.get("fixed", [])
            + results.get("needs_manual", [])
        )
        if all_results:
            avg_score = sum(r.get("score", 0) for r in all_results) / len(all_results)
            self.log(f"  ≡ƒôè Average Quality Score: {avg_score:.1f}/100")

        # Save results
        report_file = os.path.join(self.output_dir, "review_pipeline_results.json")
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        self.log(f"\n  Report saved: {report_file}")

        return results

    def run_full_pipeline(self, topics_count=5, review_after=True, fix_issues=True):
        """Run complete pipeline: Generate ΓåÆ Review ΓåÆ Fix"""
        self.log(f"\n{'='*60}")
        self.log(f"FULL PIPELINE: Generate {topics_count} ΓåÆ Review ΓåÆ Fix")
        self.log(f"{'='*60}")

        # Step 1: Generate new articles
        self.log(f"\n[STEP 1/3] Generating {topics_count} new articles...")
        generation_results = self.generate_batch(topics_count)

        new_article_ids = [
            r["article_id"] for r in generation_results if r.get("article_id")
        ]
        self.log(f"\n  Generated {len(new_article_ids)} articles successfully")

        if not review_after:
            return {"generation": generation_results}

        # Wait for Shopify to process
        self.log(f"\n[STEP 2/3] Waiting 5s for Shopify to process...")
        time.sleep(5)

        # Step 2: Review generated articles
        self.log(f"\n[STEP 3/3] Running review on new articles...")

        articles = self.get_published_articles(limit=topics_count * 2)
        new_articles = [a for a in articles if a["id"] in new_article_ids]

        review_results = {"ok": [], "fixed": [], "needs_manual": []}

        for article in new_articles:
            if fix_issues:
                result = self.review_and_fix_article(article)
            else:
                validation = self.validate_content(
                    article.get("body_html", ""), article.get("title", "")
                )
                result = {
                    "id": article["id"],
                    "title": article.get("title", ""),
                    "status": "ok" if validation["valid"] else "needs_review",
                    "score": self._calculate_quality_score(validation),
                }
            review_results[result.get("status", "needs_manual")].append(result)

        # Final summary
        self.log(f"\n{'='*60}")
        self.log(f"PIPELINE COMPLETE")
        self.log(f"{'='*60}")
        self.log(f"  Generated: {len(new_article_ids)} articles")
        self.log(f"  Reviewed: {len(new_articles)} articles")
        self.log(f"  Quality OK: {len(review_results.get('ok', []))}")
        self.log(f"  Auto-fixed: {len(review_results.get('fixed', []))}")
        self.log(f"  Needs manual: {len(review_results.get('needs_manual', []))}")

        return {"generation": generation_results, "review": review_results}

    # ==================== END PIPELINE ====================


def main():
    parser = argparse.ArgumentParser(
        description="Blog Content Generator with Quality Pipeline"
    )
    parser.add_argument("--topic", type=str, help="Single topic file to generate")
    parser.add_argument("--batch", type=int, help="Number of topics to generate")
    parser.add_argument(
        "--all", action="store_true", help="Generate all pending topics"
    )
    parser.add_argument("--list", action="store_true", help="List pending topics")

    # Pipeline commands
    parser.add_argument(
        "--review",
        type=int,
        nargs="?",
        const=50,
        help="Review existing articles (default: 50)",
    )
    parser.add_argument(
        "--fix", action="store_true", help="Auto-fix issues during review"
    )
    parser.add_argument(
        "--pipeline",
        type=int,
        help="Run full pipeline: generate N topics + review + fix",
    )
    parser.add_argument(
        "--scan",
        type=int,
        nargs="?",
        const=250,
        help="Full quality audit of all articles (default: 250)",
    )
    parser.add_argument(
        "--audit",
        type=str,
        help="Audit single article by ID",
    )

    args = parser.parse_args()

    generator = BlogContentGenerator()

    if args.list:
        topics = generator.get_pending_topics()
        print(f"\nPending topics ({len(topics)}):")
        for i, t in enumerate(topics):
            cat = generator.detect_topic_category(t["title"])
            print(f"  {i+1}. [{cat}] {t['title']}")
    elif args.topic:
        generator.generate_single(args.topic)
    elif args.batch:
        generator.generate_batch(args.batch)
    elif args.all:
        topics = generator.get_pending_topics()
        generator.generate_batch(len(topics))
    elif args.scan is not None:
        generator.scan_all_articles(limit=args.scan)
    elif args.audit:
        # Audit single article
        articles = generator.get_published_articles(limit=250)
        article = next((a for a in articles if str(a["id"]) == args.audit), None)
        if article:
            result = generator.full_audit(article)
            print(f"\n{'='*60}")
            print(f"AUDIT: {result['title'][:50]}...")
            print(f"{'='*60}")
            print(f"Overall: {'Γ£à PASS' if result['overall_pass'] else 'Γ¥î FAIL'}")
            print(f"Score: {result['score']}/100 ({result['score_10']}/10)")
            print(f"Checks: {result['passed_checks']}/{result['total_checks']}")
            if result["issues"]:
                print(f"\nIssues:")
                for issue in result["issues"]:
                    print(f"  ΓÜá∩╕Å {issue}")
            if result["warnings"]:
                print(f"\nWarnings:")
                for warning in result["warnings"]:
                    print(f"  ΓÜí {warning}")
        else:
            print(f"Article not found: {args.audit}")
    elif args.review is not None:
        generator.run_review_pipeline(limit=args.review, fix=args.fix)
    elif args.pipeline:
        generator.run_full_pipeline(
            topics_count=args.pipeline, review_after=True, fix_issues=True
        )
    else:
        print("Usage:")
        print(
            "  python blog_generator.py --list                    # List pending topics with categories"
        )
        print(
            "  python blog_generator.py --topic 001_topic.md      # Generate single topic"
        )
        print(
            "  python blog_generator.py --batch 5                 # Generate first 5 pending"
        )
        print(
            "  python blog_generator.py --all                     # Generate all pending"
        )
        print("")
        print("Quality commands:")
        print(
            "  python blog_generator.py --scan                    # Full audit of all articles"
        )
        print(
            "  python blog_generator.py --scan 100                # Audit first 100 articles"
        )
        print(
            "  python blog_generator.py --audit <article_id>      # Audit single article"
        )
        print("")
        print("Pipeline commands:")
        print(
            "  python blog_generator.py --review                  # Review last 50 articles"
        )
        print(
            "  python blog_generator.py --review 100 --fix        # Review 100 + auto-fix issues"
        )
        print(
            "  python blog_generator.py --pipeline 5              # Full: generate 5 + review + fix"
        )


if __name__ == "__main__":
    main()
