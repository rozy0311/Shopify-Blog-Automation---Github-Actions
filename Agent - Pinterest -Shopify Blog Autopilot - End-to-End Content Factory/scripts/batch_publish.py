#!/usr/bin/env python3
"""
batch_publish.py - Batch scheduler for Shopify blog publishing.

Publishes 20 blogs, pauses 20 minutes, then continues.
Never repeats already published topics.

Usage:
    python scripts/batch_publish.py

    # With custom settings:
    BATCH_SIZE=10 PAUSE_MINUTES=15 python scripts/batch_publish.py

Environment Variables:
    TOPICS_FILE - Path to topics file (default: topics.txt)
    STATE_FILE - Path to state file (default: content/state.json)
    BATCH_SIZE - Number of articles per batch (default: 20)
    PAUSE_MINUTES - Minutes to pause between batches (default: 20)
    DRY_RUN - If "true", don't actually publish (default: false)
    MAX_DAILY_POSTS - Maximum posts per day (default: 100)
"""

import os
import time
import json
import hashlib
import subprocess
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Paths
SCRIPT_DIR = Path(__file__).parent
ROOT_DIR = SCRIPT_DIR.parent
CONTENT_DIR = ROOT_DIR / "content"

# Configuration
TOPICS_FILE = os.getenv("TOPICS_FILE", str(ROOT_DIR / "topics.txt"))
STATE_FILE = os.getenv("STATE_FILE", str(CONTENT_DIR / "state.json"))
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "20"))
PAUSE_MINUTES = int(os.getenv("PAUSE_MINUTES", "20"))
DRY_RUN = os.getenv("DRY_RUN", "false").lower() == "true"
MAX_DAILY_POSTS = int(os.getenv("MAX_DAILY_POSTS", "100"))


def sha256(s: str) -> str:
    """Compute SHA256 hash of string."""
    return hashlib.sha256(s.strip().encode("utf-8")).hexdigest()


def load_topics(path: str) -> list:
    """Load topics from file (one per line)."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Missing topics file: {path}")

    lines = p.read_text(encoding="utf-8").splitlines()
    topics = []

    for line in lines:
        line = line.strip()
        # Skip empty lines and comments
        if line and not line.startswith("#"):
            topics.append(line)

    return topics


def load_state(path: str) -> dict:
    """Load state from JSON file."""
    p = Path(path)
    if not p.exists():
        p.parent.mkdir(parents=True, exist_ok=True)
        initial_state = {
            "published": {},
            "failed": {},
            "last_index": 0,
            "last_run": None,
            "daily_count": 0,
            "daily_reset_date": None,
        }
        p.write_text(json.dumps(initial_state, indent=2), encoding="utf-8")
        return initial_state

    return json.loads(p.read_text(encoding="utf-8"))


def save_state(path: str, state: dict):
    """Save state to JSON file."""
    Path(path).write_text(
        json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def reset_daily_count_if_needed(state: dict) -> dict:
    """Reset daily count if it's a new day."""
    today = datetime.now().strftime("%Y-%m-%d")

    if state.get("daily_reset_date") != today:
        state["daily_count"] = 0
        state["daily_reset_date"] = today

    return state


def run_topic_pipeline(topic: str) -> dict:
    """
    Run the full pipeline for a single topic.

    This calls run_one_topic.py which should:
    1. Research the topic
    2. Generate article payload + evidence ledger
    3. Run validator
    4. Run reviewer
    5. Publish if both pass

    Returns dict with returncode, stdout, stderr.
    """
    cmd = [sys.executable, str(SCRIPT_DIR / "run_one_topic.py"), "--topic", topic]

    if DRY_RUN:
        cmd.append("--dry-run")

    print(f"\n{'='*60}")
    print(f"Running pipeline for: {topic[:80]}")
    print(f"{'='*60}")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600,  # 10 minute timeout per topic
        )

        return {
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }

    except subprocess.TimeoutExpired:
        return {
            "returncode": -1,
            "stdout": "",
            "stderr": "TIMEOUT: Pipeline exceeded 10 minute limit",
        }
    except Exception as e:
        return {"returncode": -1, "stdout": "", "stderr": f"ERROR: {str(e)}"}


def format_duration(seconds: int) -> str:
    """Format seconds as human-readable duration."""
    if seconds < 60:
        return f"{seconds}s"
    elif seconds < 3600:
        return f"{seconds // 60}m {seconds % 60}s"
    else:
        hours = seconds // 3600
        mins = (seconds % 3600) // 60
        return f"{hours}h {mins}m"


def main():
    """Main batch publishing function."""
    print("\n" + "=" * 60)
    print("SHOPIFY BLOG BATCH PUBLISHER")
    print("=" * 60)

    if DRY_RUN:
        print("⚠️  DRY RUN MODE - No actual publishing")

    print(f"Batch size: {BATCH_SIZE}")
    print(f"Pause between batches: {PAUSE_MINUTES} minutes")
    print(f"Max daily posts: {MAX_DAILY_POSTS}")

    # Load topics and state
    try:
        topics = load_topics(TOPICS_FILE)
        print(f"Loaded {len(topics)} topics from {TOPICS_FILE}")
    except FileNotFoundError as e:
        print(f"\n❌ {e}")
        print("\nCreate a topics.txt file with one topic per line:")
        print("  # Example topics.txt")
        print("  How to Make Homemade Vinegar from Fruit Scraps")
        print("  Natural All-Purpose Cleaner with Citrus")
        print("  ...")
        sys.exit(1)

    state = load_state(STATE_FILE)
    state = reset_daily_count_if_needed(state)

    # Statistics
    batch_published = 0
    batch_failed = 0
    batch_skipped = 0
    start_time = time.time()

    # Resume from last index
    i = int(state.get("last_index", 0))

    print(f"\nResuming from index: {i}")
    print(f"Already published: {len(state.get('published', {}))}")
    print(f"Already failed: {len(state.get('failed', {}))}")
    print(f"Today's count: {state.get('daily_count', 0)}/{MAX_DAILY_POSTS}")

    while i < len(topics):
        # Check daily limit
        if state.get("daily_count", 0) >= MAX_DAILY_POSTS:
            print(f"\n🛑 Daily limit reached ({MAX_DAILY_POSTS}). Stopping.")
            break

        topic = topics[i]
        key = sha256(topic)

        # Skip if already published
        if key in state.get("published", {}):
            print(
                f"\n⏭️  [{i+1}/{len(topics)}] SKIP (already published): {topic[:50]}..."
            )
            batch_skipped += 1
            i += 1
            continue

        # Skip if failed too many times
        fail_rec = state.get("failed", {}).get(key)
        if fail_rec and fail_rec.get("count", 0) >= 3:
            print(f"\n⏭️  [{i+1}/{len(topics)}] SKIP (failed 3+ times): {topic[:50]}...")
            batch_skipped += 1
            i += 1
            continue

        print(f"\n📝 [{i+1}/{len(topics)}] Processing: {topic[:60]}...")

        # Run the pipeline
        result = run_topic_pipeline(topic)

        if result["returncode"] == 0:
            # Success
            state.setdefault("published", {})[key] = {
                "topic": topic,
                "timestamp": int(time.time()),
                "date": datetime.now().isoformat(),
            }
            state["daily_count"] = state.get("daily_count", 0) + 1
            batch_published += 1

            print(f"✅ Published successfully!")
            print(f"   Daily count: {state['daily_count']}/{MAX_DAILY_POSTS}")

        else:
            # Failed
            fail_rec = state.get("failed", {}).get(key, {"topic": topic, "count": 0})
            fail_rec["count"] = fail_rec.get("count", 0) + 1
            fail_rec["last_error"] = (result.get("stderr") or result.get("stdout", ""))[
                -2000:
            ]
            fail_rec["last_attempt"] = datetime.now().isoformat()

            state.setdefault("failed", {})[key] = fail_rec
            batch_failed += 1

            print(f"❌ Failed (attempt {fail_rec['count']}/3)")
            if result.get("stderr"):
                print(f"   Error: {result['stderr'][:200]}")

        # Update state
        i += 1
        state["last_index"] = i
        state["last_run"] = datetime.now().isoformat()
        save_state(STATE_FILE, state)

        # Check if batch complete
        if batch_published >= BATCH_SIZE:
            elapsed = int(time.time() - start_time)
            print(f"\n" + "=" * 60)
            print(f"🎉 BATCH COMPLETE")
            print(f"   Published: {batch_published}")
            print(f"   Failed: {batch_failed}")
            print(f"   Skipped: {batch_skipped}")
            print(f"   Elapsed: {format_duration(elapsed)}")
            print(f"   Daily total: {state.get('daily_count', 0)}/{MAX_DAILY_POSTS}")

            # Check if more topics remain
            remaining = sum(
                1
                for j in range(i, len(topics))
                if sha256(topics[j]) not in state.get("published", {})
            )

            if remaining > 0 and state.get("daily_count", 0) < MAX_DAILY_POSTS:
                print(f"\n⏰ Sleeping {PAUSE_MINUTES} minutes before next batch...")
                print(f"   Remaining topics: {remaining}")

                # Sleep with countdown
                for remaining_mins in range(PAUSE_MINUTES, 0, -1):
                    print(f"   Resuming in {remaining_mins} minutes...", end="\r")
                    time.sleep(60)

                print(" " * 50, end="\r")  # Clear line

                # Reset batch counters
                batch_published = 0
                batch_failed = 0
                batch_skipped = 0
                start_time = time.time()
            else:
                break

    # Final summary
    elapsed = int(time.time() - start_time)
    print(f"\n" + "=" * 60)
    print(f"🏁 BATCH PUBLISHING COMPLETE")
    print(f"=" * 60)
    print(f"Total published (this run): {batch_published}")
    print(f"Total failed (this run): {batch_failed}")
    print(f"Total skipped: {batch_skipped}")
    print(f"All-time published: {len(state.get('published', {}))}")
    print(f"All-time failed: {len(state.get('failed', {}))}")
    print(f"Session duration: {format_duration(elapsed)}")

    # Check for remaining
    remaining_topics = len(topics) - i
    if remaining_topics > 0:
        print(f"\n📋 {remaining_topics} topics remaining in queue")
        print(f"   Run again to continue from index {i}")
    else:
        print(f"\n✅ All {len(topics)} topics processed!")


if __name__ == "__main__":
    main()
