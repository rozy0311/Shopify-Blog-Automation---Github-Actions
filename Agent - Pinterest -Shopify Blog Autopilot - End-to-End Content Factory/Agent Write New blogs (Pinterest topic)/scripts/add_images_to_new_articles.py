"""
Add AI Images to New Blog Articles
Uses ai_image_generator_v2.py from pipeline_v2 to add featured + inline images

Usage:
    python add_images_to_new_articles.py
"""

import os
import sys
import subprocess
import time
from datetime import datetime

# Add pipeline_v2 path
PIPELINE_V2_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "Agent - Pinterest -Shopify Blog Autopilot - End-to-End Content Factory",
    "pipeline_v2",
)

# New article IDs from the batch generation
NEW_ARTICLE_IDS = [
    690770247998,  # Homemade Elderberry Syrup for Immune Support
    690770280766,  # DIY Fire Cider Recipe for Cold Season
    690770313534,  # Natural Chest Rub with Essential Oils
    690770346302,  # Homemade Cough Drops with Honey and Herbs
    690770379070,  # Healing Salve for Cuts and Scrapes
    690770411838,  # Herbal Tea Blends for Digestive Health
    690770444606,  # Natural Headache Relief Remedies
    690770477374,  # Homemade Muscle Rub for Aches and Pains
    690770510142,  # DIY Sore Throat Spray Recipe
    690770542910,  # Natural Sleep Remedies with Herbs
    690770575678,  # Homemade Bug Bite Relief Balm
    690770608446,  # Herbal Tinctures for Beginners
    690770641214,  # Natural Allergy Relief Remedies
    690770706750,  # DIY Vapor Rub for Congestion
    690770739518,  # Homemade Wound Healing Poultice
    690770772286,  # Calendula Salve for Skin Healing
    690770805054,  # Lavender Uses for Home Remedies
    690770837822,  # Plantain Leaf for First Aid
    690770870590,  # Ginger Remedies for Nausea
    690770903358,  # Honey and Lemon for Sore Throat
]


def log(message, level="INFO"):
    timestamp = datetime.now().strftime("%H:%M:%S")
    icons = {"INFO": "≡ƒôï", "SUCCESS": "Γ£à", "ERROR": "Γ¥î", "WARNING": "ΓÜá∩╕Å", "IMAGE": "≡ƒû╝∩╕Å"}
    print(f"[{timestamp}] {icons.get(level, '≡ƒôï')} {message}")


def add_images_to_article(article_id):
    """Run ai_image_generator_v2.py for a single article"""
    log(f"Adding AI images to article: {article_id}", "IMAGE")

    script_path = os.path.join(PIPELINE_V2_DIR, "ai_image_generator_v2.py")

    if not os.path.exists(script_path):
        log(f"Script not found: {script_path}", "ERROR")
        return False

    try:
        result = subprocess.run(
            ["python", script_path, "--article-id", str(article_id)],
            cwd=PIPELINE_V2_DIR,
            capture_output=True,
            text=True,
            timeout=300,  # 5 minute timeout per article
        )

        if result.returncode == 0:
            log(f"Article {article_id}: Images added successfully", "SUCCESS")
            return True
        else:
            log(f"Article {article_id}: Failed - {result.stderr[:200]}", "ERROR")
            return False

    except subprocess.TimeoutExpired:
        log(f"Article {article_id}: Timeout", "ERROR")
        return False
    except Exception as e:
        log(f"Article {article_id}: Error - {e}", "ERROR")
        return False


def main():
    log("=" * 60)
    log("Adding AI Images to New Blog Articles")
    log("=" * 60)
    log(f"Total articles: {len(NEW_ARTICLE_IDS)}")
    log(f"Image generator: {PIPELINE_V2_DIR}")

    results = {"success": 0, "failed": 0}

    for i, article_id in enumerate(NEW_ARTICLE_IDS):
        log(f"\n[{i+1}/{len(NEW_ARTICLE_IDS)}] Processing article {article_id}")

        if add_images_to_article(article_id):
            results["success"] += 1
        else:
            results["failed"] += 1

        # Rate limiting
        if i < len(NEW_ARTICLE_IDS) - 1:
            log("Waiting 5 seconds before next article...")
            time.sleep(5)

    log("\n" + "=" * 60)
    log(f"COMPLETE: {results['success']} success, {results['failed']} failed")
    log("=" * 60)


if __name__ == "__main__":
    main()
