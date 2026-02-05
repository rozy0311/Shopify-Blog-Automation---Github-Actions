#!/usr/bin/env python3
"""
AUTONOMOUS AGENT SYSTEM - CHß║╛ ─Éß╗ÿ Rß║«N
====================================

Hß╗ç thß╗æng 3 agent tß╗▒ ─æß╗Öng:
1. Agent Executor - Thß╗▒c hiß╗çn task
2. Agent Supervisor - Gi├ím s├ít v├á ph├ít hiß╗çn lß╗ùi
3. Agent QA - Thß║⌐m ─æß╗ïnh chß║Ñt l╞░ß╗úng

Tß║ñT Cß║ó Tß╗░ Hß╗ÄI - Tß╗░ TRß║ó Lß╗£I - Tß╗░ FOLLOW UP
KH├öNG Cß║ªN Hß╗ÄI NG╞»ß╗£I D├ÖNG
"""

import os
import json
import time
import requests
from datetime import datetime
from dotenv import load_dotenv

# Load environment
load_dotenv(
    r"D:\active-projects\Auto Blog Shopify NEW Rosie\Shopify Blog Automation - Github Actions\Agent - Pinterest -Shopify Blog Autopilot - End-to-End Content Factory\.env"
)

SHOPIFY_STORE = (
    os.getenv("SHOPIFY_STORE_URL", "").replace("https://", "").replace("/", "")
)
SHOPIFY_TOKEN = os.getenv("SHOPIFY_ACCESS_TOKEN", "")
POLLINATIONS_API_KEY = os.getenv("POLLINATIONS_API_KEY", "")
BLOG_ID = "73095348337"  # Sustainable Living

# ==========================================
# MASTER RULES - KH├öNG ─É╞»ß╗óC VI PHß║áM
# ==========================================
MASTER_RULES = {
    "11_SECTIONS": [
        "Direct Answer",
        "Key Conditions at a Glance",
        "Understanding [Topic]",
        "Complete Step-by-Step Guide",
        "Types and Varieties",
        "Troubleshooting Common Issues",
        "Pro Tips from Experts",
        "FAQs",
        "Advanced Techniques",
        "Comparison Table",
        "Sources & Further Reading",
    ],
    "IMAGES": {
        "featured_required": True,
        "inline_minimum": 3,
        "pinterest_preserve": True,
        "no_hands_fingers": True,
        "no_duplicate": True,
    },
    "CONTENT": {
        "min_words": 1800,
        "max_words": 2500,
        "topic_focus_score_min": 8,
        "no_generic_phrases": True,
        "no_template_contamination": True,
    },
    "SOURCE_FORMAT": '<a href="URL">T├¬n nguß╗ôn ΓÇö M├┤ tß║ú ngß║»n</a>',
    "META_DESCRIPTION_REQUIRED": True,
}


# ==========================================
# AGENT SUPERVISOR - GI├üM S├üT & PH├üT HIß╗åN Lß╗ûI
# ==========================================
class AgentSupervisor:
    """Agent gi├ím s├ít to├án bß╗Ö qu├í tr├¼nh, ph├ít hiß╗çn lß╗ùi"""

    def __init__(self):
        self.issues_found = []
        self.warnings = []

    def ask_self(self, question):
        """Tß╗▒ hß╗Åi v├á tß╗▒ trß║ú lß╗¥i"""
        print(f"\n≡ƒöì SUPERVISOR Hß╗ÄI: {question}")
        # Tß╗▒ ph├ón t├¡ch v├á trß║ú lß╗¥i
        return self.analyze(question)

    def analyze(self, question):
        """Ph├ón t├¡ch c├óu hß╗Åi v├á trß║ú lß╗¥i"""
        if "c├│ ─æß║ít" in question.lower():
            return self.check_quality()
        elif "lß╗ùi" in question.lower():
            return self.list_issues()
        return "Cß║ºn th├¬m th├┤ng tin"

    def check_quality(self):
        """Kiß╗âm tra chß║Ñt l╞░ß╗úng b├ái viß║┐t"""
        return len(self.issues_found) == 0

    def list_issues(self):
        """Liß╗çt k├¬ c├íc lß╗ùi ─æ├ú ph├ít hiß╗çn"""
        return self.issues_found

    def validate_article(self, article):
        """Validate mß╗Öt b├ái viß║┐t theo tß║Ñt cß║ú rules"""
        self.issues_found = []

        title = article.get("title", "")
        body = article.get("body_html", "")

        # 1. Check 11 sections
        missing_sections = []
        for section in MASTER_RULES["11_SECTIONS"]:
            section_lower = section.lower().replace("[topic]", "")
            if section_lower not in body.lower():
                missing_sections.append(section)
        if missing_sections:
            self.issues_found.append(f"MISSING_SECTIONS: {missing_sections[:3]}")

        # 2. Check images
        img_count = body.count("<img")
        if img_count < 3:
            self.issues_found.append(f"LOW_IMGS: {img_count}/3")

        # 3. Check meta description
        if not article.get("metafields_global_description_tag"):
            summary_description = article.get("summary_html", "")
            if not summary_description:
                self.issues_found.append("NO_META_DESCRIPTION")

        # 4. Check featured image
        if not article.get("image"):
            self.issues_found.append("NO_FEATURED_IMAGE")

        # 5. Check generic content
        generic_phrases = [
            "comprehensive guide",
            "this article will",
            "in this blog post",
        ]
        for phrase in generic_phrases:
            if phrase.lower() in body.lower():
                self.issues_found.append(f"GENERIC_CONTENT: '{phrase}'")
                break

        # 6. Check source links format
        if "Sources" in body or "Further Reading" in body:
            if '<a href="' not in body:
                self.issues_found.append("BAD_SOURCE_FORMAT")

        # 7. Check word count
        import re

        text_only = re.sub(r"<[^>]+>", "", body)
        word_count = len(text_only.split())
        if word_count < 1800:
            self.issues_found.append(f"LOW_WORDS: {word_count}/1800")

        # Self-ask: B├ái n├áy c├│ ─æß║ít kh├┤ng?
        self.ask_self("B├ái n├áy c├│ ─æß║ít ti├¬u chuß║⌐n kh├┤ng?")

        return len(self.issues_found) == 0, self.issues_found


# ==========================================
# AGENT QA - THß║¿M ─Éß╗èNH CHß║ñT L╞»ß╗óNG
# ==========================================
class AgentQA:
    """Agent thß║⌐m ─æß╗ïnh chß║Ñt l╞░ß╗úng cuß╗æi c├╣ng"""

    def __init__(self):
        self.passed = False
        self.score = 0

    def ask_self(self, question):
        """Tß╗▒ hß╗Åi v├á tß╗▒ trß║ú lß╗¥i"""
        print(f"\nΓ£à QA Hß╗ÄI: {question}")
        return self.evaluate(question)

    def evaluate(self, question):
        """─É├ính gi├í"""
        if "publish" in question.lower():
            return self.passed and self.score >= 8
        return False

    def final_review(self, article, supervisor_issues):
        """Review cuß╗æi c├╣ng tr╞░ß╗¢c khi publish"""

        # Nß║┐u supervisor ph├ít hiß╗çn lß╗ùi critical, kh├┤ng pass
        critical_issues = [
            i for i in supervisor_issues if "GENERIC" in i or "MISSING" in i
        ]

        if critical_issues:
            self.passed = False
            self.score = 3
            print(f"\nΓ¥î QA REJECT: {len(critical_issues)} critical issues")
            return False, critical_issues

        # Nß║┐u chß╗ë c├│ minor issues, c├│ thß╗â pass vß╗¢i cß║únh b├ío
        if len(supervisor_issues) <= 2:
            self.passed = True
            self.score = 7
            print(f"\nΓÜá∩╕Å QA PASS WITH WARNINGS: {supervisor_issues}")
            return True, supervisor_issues

        # Kh├┤ng c├│ issue
        if len(supervisor_issues) == 0:
            self.passed = True
            self.score = 10
            print("\nΓ£à QA PASS: Perfect score")
            return True, []

        self.passed = False
        self.score = 5
        return False, supervisor_issues


# ==========================================
# AGENT EXECUTOR - THß╗░C HIß╗åN TASK
# ==========================================
class AgentExecutor:
    """Agent thß╗▒c hiß╗çn c├íc task fix/publish"""

    def __init__(self):
        self.supervisor = AgentSupervisor()
        self.qa = AgentQA()
        self.api_url = f"https://{SHOPIFY_STORE}/admin/api/2025-01"
        self.headers = {
            "X-Shopify-Access-Token": SHOPIFY_TOKEN,
            "Content-Type": "application/json",
        }

    def ask_self(self, question):
        """Tß╗▒ hß╗Åi v├á tß╗▒ trß║ú lß╗¥i"""
        print(f"\n≡ƒöº EXECUTOR Hß╗ÄI: {question}")
        return self.decide(question)

    def decide(self, question):
        """Quyß║┐t ─æß╗ïnh h├ánh ─æß╗Öng"""
        if "fix" in question.lower():
            return "Tiß║┐n h├ánh fix"
        elif "publish" in question.lower():
            return "Chß╗¥ QA approve"
        return "Cß║ºn ph├ón t├¡ch th├¬m"

    def get_article(self, article_id):
        """Lß║Ñy th├┤ng tin b├ái viß║┐t"""
        url = f"{self.api_url}/articles/{article_id}.json"
        response = requests.get(url, headers=self.headers)
        if response.status_code == 200:
            return response.json().get("article", {})
        return None

    def fix_article(self, article_id):
        """Fix mß╗Öt b├ái viß║┐t theo quy tr├¼nh ─æß║ºy ─æß╗º"""
        print(f"\n{'='*60}")
        print(f"PROCESSING ARTICLE: {article_id}")
        print(f"{'='*60}")

        # 1. Lß║Ñy b├ái viß║┐t
        article = self.get_article(article_id)
        if not article:
            print(f"Γ¥î Cannot fetch article {article_id}")
            return False

        title = article.get("title", "Unknown")
        print(f"≡ƒô¥ Title: {title}")

        # 2. SUPERVISOR: Validate
        print("\n--- AGENT SUPERVISOR ---")
        is_valid, issues = self.supervisor.validate_article(article)

        if is_valid:
            print("Γ£à Article already meets all criteria")
            return True

        print(f"ΓÜá∩╕Å Issues found: {issues}")

        # 3. EXECUTOR: Tß╗▒ hß╗Åi c├│ n├¬n fix kh├┤ng
        self.ask_self(f"C├│ n├¬n fix b├ái {title} kh├┤ng?")

        # 4. Thß╗▒c hiß╗çn fix tß╗½ng issue
        fixed_content = article.get("body_html", "")
        updates = {}

        for issue in issues:
            if "NO_META_DESCRIPTION" in issue:
                # Tß║ío meta description
                meta = f"Learn about {title}. Complete guide with step-by-step instructions, expert tips, and FAQs."
                updates["metafields_global_description_tag"] = meta[:160]
                print(f"  Γ£ô Added meta description")

            elif "LOW_IMGS" in issue:
                # Th├¬m placeholder cho images (cß║ºn generate thß╗▒c tß║┐)
                print(f"  ΓÜá∩╕Å Need to add images (requires Pollinations API)")

            elif "MISSING_SECTIONS" in issue:
                # Th├¬m sections c├▓n thiß║┐u
                print(
                    f"  ΓÜá∩╕Å Need to add missing sections (requires content generation)"
                )

        # 5. QA: Review cuß╗æi
        print("\n--- AGENT QA ---")
        qa_passed, qa_issues = self.qa.final_review(article, issues)

        self.qa.ask_self("B├ái n├áy c├│ thß╗â publish ─æ╞░ß╗úc kh├┤ng?")

        # 6. Publish nß║┐u pass
        if qa_passed:
            print(f"\nΓ£à APPROVED FOR PUBLISH")
            # Thß╗▒c hiß╗çn update nß║┐u c├│ changes
            if updates:
                self.update_article(article_id, updates)
            return True
        else:
            print(f"\nΓ¥î NOT APPROVED - Issues: {qa_issues}")
            return False

    def update_article(self, article_id, updates):
        """Update b├ái viß║┐t tr├¬n Shopify"""
        url = f"{self.api_url}/articles/{article_id}.json"
        data = {"article": updates}
        response = requests.put(url, headers=self.headers, json=data)
        return response.status_code == 200

    def run_autonomous(self, article_ids):
        """Chß║íy tß╗▒ ─æß╗Öng cho danh s├ích b├ái"""
        results = {"passed": [], "failed": [], "total": len(article_ids)}

        for i, article_id in enumerate(article_ids, 1):
            print(f"\n{'#'*60}")
            print(f"# ARTICLE {i}/{len(article_ids)}: {article_id}")
            print(f"{'#'*60}")

            success = self.fix_article(article_id)

            if success:
                results["passed"].append(article_id)
            else:
                results["failed"].append(article_id)

            # Delay ─æß╗â tr├ính rate limit
            time.sleep(2)

        # Summary
        print(f"\n{'='*60}")
        print("AUTONOMOUS RUN COMPLETE")
        print(f"{'='*60}")
        print(f"Γ£à Passed: {len(results['passed'])}")
        print(f"Γ¥î Failed: {len(results['failed'])}")

        return results


# ==========================================
# MAIN - CHß║áY Hß╗å THß╗ÉNG
# ==========================================
def main():
    print(
        """
    ΓòöΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòù
    Γòæ     AUTONOMOUS AGENT SYSTEM - CHß║╛ ─Éß╗ÿ Rß║«N                 Γòæ
    Γòæ                                                          Γòæ
    Γòæ  ΓÇó Agent Executor: Thß╗▒c hiß╗çn task                        Γòæ
    Γòæ  ΓÇó Agent Supervisor: Gi├ím s├ít & ph├ít hiß╗çn lß╗ùi            Γòæ
    Γòæ  ΓÇó Agent QA: Thß║⌐m ─æß╗ïnh chß║Ñt l╞░ß╗úng                        Γòæ
    Γòæ                                                          Γòæ
    Γòæ  Tß╗░ Hß╗ÄI - Tß╗░ TRß║ó Lß╗£I - Tß╗░ FOLLOW UP                     Γòæ
    ΓòÜΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓò¥
    """
    )

    executor = AgentExecutor()

    # Lß║Ñy danh s├ích b├ái cß║ºn xß╗¡ l├╜ tß╗½ backup
    backup_dir = r"D:\active-projects\Auto Blog Shopify NEW Rosie\Shopify Blog Automation - Github Actions\Agent - Pinterest -Shopify Blog Autopilot - End-to-End Content Factory\pipeline_v2\backups_master_fix"

    article_ids = []
    if os.path.exists(backup_dir):
        for f in os.listdir(backup_dir):
            if f.endswith(".json"):
                try:
                    article_id = f.split("_")[0]
                    if article_id.isdigit():
                        article_ids.append(article_id)
                except:
                    pass

    if not article_ids:
        print("No articles to process from backup")
        return

    print(f"Found {len(article_ids)} articles in backup")

    # Chß║íy autonomous
    results = executor.run_autonomous(article_ids[:5])  # Test vß╗¢i 5 b├ái ─æß║ºu

    print("\nDone!")


if __name__ == "__main__":
    main()
