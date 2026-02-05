"""
Fix one article: strip generic content, fix images, then publish.
Usage (from workspace root, .env loaded):
  python pipeline_v2/fix_content_and_publish_one.py <article_id>
  python pipeline_v2/fix_content_and_publish_one.py 691791954238

Other articles: run the same command with a different article_id, or use a loop:
  for id in 691791954238 690495586622; do python pipeline_v2/fix_content_and_publish_one.py $id; done
"""
import os
import sys
import subprocess
from pathlib import Path

# Repo root and env
REPO_ROOT = Path(__file__).resolve().parent.parent
os.chdir(REPO_ROOT)
sys.path.insert(0, str(REPO_ROOT))
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

def main():
    if len(sys.argv) < 2:
        print("Usage: python pipeline_v2/fix_content_and_publish_one.py <article_id>")
        sys.exit(1)
    article_id = sys.argv[1].strip()

    from pipeline_v2.ai_orchestrator import AIOrchestrator

    orchestrator = AIOrchestrator()

    # 1) Strip generic content + duplicate paragraphs (update body_html on Shopify)
    print("[1/3] Stripping generic content and duplicate paragraphs...")
    orchestrator._strip_generic_before_publish(article_id)

    # 2) Fix images (Pinterest + topic-specific AI images via fix_images_properly.py)
    print("[2/3] Fixing images (fix_images_properly.py)...")
    r = subprocess.run(
        [sys.executable, str(REPO_ROOT / "pipeline_v2" / "fix_images_properly.py"), "--article-id", article_id],
        cwd=str(REPO_ROOT),
        env={**os.environ, "VISION_REVIEW": "1"},
    )
    if r.returncode != 0:
        print("[WARN] fix_images_properly.py returned %s (continuing)" % r.returncode)

    # 2.5) Strip generic again so final content on Shopify is clean (avoids race where fix_images had stale body)
    print("[2.5/3] Stripping generic content again (final pass)...")
    orchestrator._strip_generic_before_publish(article_id)

    # 3) Publish (REST + GraphQL so article shows on storefront)
    print("[3/3] Publishing (REST + GraphQL)...")
    r2 = subprocess.run(
        [sys.executable, str(REPO_ROOT / "pipeline_v2" / "publish_now_graphql.py"), article_id],
        cwd=str(REPO_ROOT),
    )
    if r2.returncode != 0:
        print("[WARN] publish_now_graphql.py returned %s" % r2.returncode)
        sys.exit(1)

    print("Done. Check storefront and Shopify Admin for article %s." % article_id)

if __name__ == "__main__":
    main()
