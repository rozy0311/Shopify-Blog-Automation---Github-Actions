#!/usr/bin/env python3
"""
Fix Images Properly - Restores Pinterest images + adds topic-specific AI images
Requirements:
1. Keep original Pinterest images as inline
2. Add 3 topic-specific AI inline images (Pollinations.ai + Shopify CDN)
3. Add 1 featured/main image (topic-specific)
4. NO duplicates
"""

import sys
import io
import base64

# Fix encoding for Windows console
sys.stdout = io.TextIOWrapper(
    sys.stdout.buffer, encoding="utf-8", errors="replace", line_buffering=True
)
sys.stderr = io.TextIOWrapper(
    sys.stderr.buffer, encoding="utf-8", errors="replace", line_buffering=True
)

import requests
import hashlib
import re
import json
import time
import os
import random
from urllib.parse import quote
from urllib.parse import urlencode

# Shopify Config
SHOP = (os.environ.get("SHOPIFY_SHOP", "the-rike-inc.myshopify.com") or "").strip()
if "." not in SHOP or "myshopify.com" not in SHOP:
    print("⚠️ Invalid SHOPIFY_SHOP; falling back to the-rike-inc.myshopify.com")
    SHOP = "the-rike-inc.myshopify.com"
BLOG_ID = os.environ.get("SHOPIFY_BLOG_ID", "108441862462")
TOKEN = os.environ.get("SHOPIFY_ACCESS_TOKEN") or os.environ.get("SHOPIFY_TOKEN")
API_VERSION = os.environ.get("SHOPIFY_API_VERSION", "2025-01")

if not TOKEN:
    raise SystemExit("Missing SHOPIFY_ACCESS_TOKEN")

# Pinterest matched data
MATCHED_DATA_FILE = "../scripts/matched_drafts_pinterest.json"
MATCHED_FALLBACK_FILE = "../scripts/pinterest_shopify_match_results.json"

# Quality settings for Pollinations
QUALITY = "professional photography, high resolution, 8K, detailed, sharp focus, beautiful lighting"
POLLINATIONS_API_KEY = os.environ.get("POLLINATIONS_API_KEY", "").strip()
POLLINATIONS_MODEL = os.environ.get("POLLINATIONS_MODEL", "flux").strip()
POLLINATIONS_NEGATIVE = os.environ.get(
    "POLLINATIONS_NEGATIVE", "text, watermark, logo, signature"
).strip()
USE_LEXICA = os.environ.get("USE_LEXICA", "0").lower() in {"1", "true", "yes"}
LEXICA_ONLY_SD15 = os.environ.get("LEXICA_ONLY_SD15", "1").lower() in {"1", "true", "yes"}
LEXICA_RESULT_LIMIT = int(os.environ.get("LEXICA_RESULT_LIMIT", "30"))
LEXICA_STRICT = os.environ.get("LEXICA_STRICT", "1").lower() in {"1", "true", "yes"}
LEXICA_FALLBACK_ONLY = os.environ.get("LEXICA_FALLBACK_ONLY", "1").lower() in {
    "1",
    "true",
    "yes",
}
def _normalize_gcp_value(value: str) -> str:
    if not value:
        return ""
    cleaned = value.strip()
    cleaned = re.split(r"[\s(]", cleaned, maxsplit=1)[0]
    return cleaned.strip()


GCP_PROJECT = _normalize_gcp_value(os.environ.get("GCP_PROJECT", ""))
GCP_LOCATION = _normalize_gcp_value(os.environ.get("GCP_LOCATION", "us-central1"))
GEMINI_IMAGE_MODEL = os.environ.get(
    "GEMINI_IMAGE_MODEL", "imagen-4.0-fast-generate-001"
).strip()
GOOGLE_APPLICATION_CREDENTIALS = os.environ.get(
    "GOOGLE_APPLICATION_CREDENTIALS", ""
).strip()
USE_VERTEX_IMAGEN = os.environ.get("USE_VERTEX_IMAGEN", "").lower() in {
    "1",
    "true",
    "yes",
}
if not USE_VERTEX_IMAGEN:
    if (
        GCP_PROJECT
        and GOOGLE_APPLICATION_CREDENTIALS
        and os.path.exists(GOOGLE_APPLICATION_CREDENTIALS)
    ):
        USE_VERTEX_IMAGEN = True
BAD_IMAGE_HASHES = {
    # Pollinations rate-limit placeholder
    "ced31e06bc36e7b76a5de3f81df1f57517c430aed6b7e146cb9a3c712582cdef"
}

# Optional vision review (auto-enable when key is present)
VISION_REVIEW = os.environ.get("VISION_REVIEW", "").lower() in {
    "1",
    "true",
    "yes",
}
VISION_API_BASE = os.environ.get(
    "VISION_API_BASE", "https://models.github.ai/inference"
)
VISION_MODEL_ID = os.environ.get("VISION_MODEL_ID", "openai/gpt-4o-mini")
VISION_API_KEY = os.environ.get("VISION_API_KEY", "")
VISION_PROVIDER = os.environ.get("VISION_PROVIDER", "").lower().strip()
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
if GEMINI_API_KEY:
    if not VISION_PROVIDER or VISION_PROVIDER in {"github", "github models", "gh"}:
        VISION_PROVIDER = "gemini"
elif VISION_API_KEY and not VISION_PROVIDER:
    VISION_PROVIDER = "github"
if VISION_API_KEY and not VISION_REVIEW:
    VISION_REVIEW = True
VISION_TIMEOUT = int(os.environ.get("VISION_TIMEOUT", "30"))
VISION_MAX_ATTEMPTS = int(os.environ.get("VISION_MAX_ATTEMPTS", "6"))
VISION_RETRY_SLEEP = float(os.environ.get("VISION_RETRY_SLEEP", "6"))
VISION_BACKOFF_FACTOR = float(os.environ.get("VISION_BACKOFF_FACTOR", "1.8"))


def load_matched_data():
    """Load Pinterest matched data (primary + fallback)."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    for rel_path in [MATCHED_DATA_FILE, MATCHED_FALLBACK_FILE]:
        filepath = os.path.join(script_dir, rel_path)
        if os.path.exists(filepath):
            try:
                with open(filepath, "r", encoding="utf-8-sig") as f:
                    data = json.load(f)
            except json.JSONDecodeError:
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
            if isinstance(data, dict):
                if "matched" in data:
                    return data
                if "exact_matches" in data:
                    return {"matched": data.get("exact_matches", [])}
            return data
    return {"matched": []}


def get_pinterest_image_url(pin_id: str) -> str:
    """Get Pinterest image URL from pin ID"""
    # Pinterest CDN pattern
    return f"https://i.pinimg.com/736x/{pin_id[:2]}/{pin_id[2:4]}/{pin_id[4:6]}/{pin_id}.jpg"


def get_pollinations_url(
    prompt: str, width: int = 1200, height: int = 800, seed: int = 42
) -> str:
    """Get Pollinations.ai image URL"""
    encoded_prompt = quote(prompt)
    token_param = f"&token={POLLINATIONS_API_KEY}" if POLLINATIONS_API_KEY else ""
    private_param = "&private=true" if POLLINATIONS_API_KEY else ""
    model_param = f"&model={POLLINATIONS_MODEL}" if POLLINATIONS_MODEL else ""
    negative_param = f"&negative={quote(POLLINATIONS_NEGATIVE)}" if POLLINATIONS_NEGATIVE else ""
    return (
        f"https://image.pollinations.ai/prompt/{encoded_prompt}"
        f"?width={width}&height={height}&seed={seed}&nologo=true"
        f"{model_param}{private_param}{token_param}{negative_param}"
    )


def search_lexica_images(query: str, limit: int = 20) -> list:
    """Search Lexica API and return candidate image URLs."""
    params = urlencode({"q": query})
    url = f"https://lexica.art/api/v1/search?{params}"
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json",
    }
    for attempt in range(3):
        try:
            resp = requests.get(url, headers=headers, timeout=30)
            if resp.status_code != 200:
                print(f"    ⚠️ Lexica search failed: {resp.status_code}")
                time.sleep(2 + attempt * 2)
                continue
            data = resp.json()
            images = data.get("images", [])
            results = []
            for img in images:
                if img.get("nsfw"):
                    continue
                if LEXICA_ONLY_SD15 and img.get("model") != "stable-diffusion":
                    continue
                src = img.get("src") or ""
                if not src:
                    continue
                # Prefer full resolution
                full_src = re.sub(r"/md\d*_webp/", "/full_webp/", src)
                full_src = re.sub(r"/sm\d*_webp/", "/full_webp/", full_src)
                results.append(
                    {
                        "url": full_src,
                        "prompt": img.get("prompt", ""),
                        "model": img.get("model", ""),
                    }
                )
                if len(results) >= limit:
                    break
            return results
        except Exception as e:
            print(f"    ⚠️ Lexica search error: {e}")
            time.sleep(2 + attempt * 2)
    return []


def download_image(url: str, max_retries: int = 3) -> bytes:
    """Download image and return bytes"""
    for attempt in range(1, max_retries + 1):
        try:
            print(f"    📥 Downloading... (attempt {attempt})")
            response = requests.get(url, timeout=120)
            content_type = (response.headers.get("Content-Type") or "").lower()
            header = response.content[:4]
            is_image = content_type.startswith("image/")
            looks_like_image = header.startswith(b"\xff\xd8") or header.startswith(
                b"\x89PNG"
            ) or header.startswith(b"RIFF")
            if (
                response.status_code == 200
                and len(response.content) > 10000
                and (is_image or looks_like_image)
            ):
                digest = hashlib.sha256(response.content).hexdigest()
                if digest in BAD_IMAGE_HASHES:
                    print("    ⚠️ Pollinations rate-limit image detected, retrying...")
                    time.sleep(5)
                    continue
                print(f"    ✅ Downloaded {len(response.content) // 1024}KB")
                return response.content
            else:
                print(f"    ⚠️ Response too small or failed, retrying...")
                time.sleep(5)
        except Exception as e:
            print(f"    ⚠️ Attempt {attempt} failed: {e}")
            if attempt < max_retries:
                time.sleep(5)

    print(f"    ❌ Failed after {max_retries} attempts")
    return None


def _extract_json(text: str):
    try:
        return json.loads(text)
    except Exception:
        pass

    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except Exception:
            return None
    return None


def _fallback_parse(text: str):
    t = text.lower()
    has_hands = None
    has_people = None
    if re.search(r"has_hands[^a-z]*true", t):
        has_hands = True
    if re.search(r"has_hands[^a-z]*false", t):
        has_hands = False
    if "no hands" in t or "no fingers" in t:
        has_hands = False
    if "hands" in t and "no hands" not in t:
        has_hands = True if has_hands is None else has_hands

    if re.search(r"has_people[^a-z]*true", t):
        has_people = True
    if re.search(r"has_people[^a-z]*false", t):
        has_people = False
    if "no people" in t or "no person" in t:
        has_people = False
    if "people" in t and "no people" not in t:
        has_people = True if has_people is None else has_people

    if has_hands is None and has_people is None:
        return None

    safe = not (has_hands or has_people)
    return {
        "has_hands": bool(has_hands),
        "has_people": bool(has_people),
        "safe": safe,
        "reason": "fallback_parse",
    }


def _download_for_vision(image_url: str) -> bytes | None:
    try:
        resp = requests.get(image_url, timeout=30)
        if resp.status_code == 200 and len(resp.content) > 10000:
            return resp.content
    except Exception:
        return None
    return None


def vision_review_image_gemini(image_url: str):
    if not GEMINI_API_KEY:
        return None
    img_bytes = _download_for_vision(image_url)
    if not img_bytes:
        return None
    b64 = base64.b64encode(img_bytes).decode("utf-8")
    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [
                    {
                        "text": (
                            "Check if the image contains any visible hands, fingers, or people. "
                            "Return JSON with keys: has_hands (true/false), has_people (true/false), "
                            "safe (true/false), reason (short)."
                        )
                    },
                    {
                        "inline_data": {
                            "mime_type": "image/jpeg",
                            "data": b64,
                        }
                    },
                ],
            }
        ],
        "generationConfig": {"temperature": 0, "maxOutputTokens": 80},
    }
    endpoints = [
        "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent",
        "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent",
        "https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent",
        "https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash-latest:generateContent",
        "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro:generateContent",
    ]
    for endpoint in endpoints:
        try:
            url = f"{endpoint}?key={GEMINI_API_KEY}"
            resp = requests.post(url, json=payload, timeout=VISION_TIMEOUT)
            if resp.status_code != 200:
                print(f"    ⚠️ Gemini vision failed: {resp.status_code}")
                continue
            data = resp.json()
            content = (
                data.get("candidates", [{}])[0]
                .get("content", {})
                .get("parts", [{}])[0]
                .get("text", "")
            )
            return _extract_json(content)
        except Exception as e:
            print(f"    ⚠️ Gemini vision error: {e}")
            continue
    return None


def vision_review_bytes_gemini(img_bytes: bytes):
    if not GEMINI_API_KEY or not img_bytes:
        return None
    b64 = base64.b64encode(img_bytes).decode("utf-8")
    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [
                    {
                        "text": (
                            "Check if the image contains any visible hands, fingers, or people. "
                            "Return JSON with keys: has_hands (true/false), has_people (true/false), "
                            "safe (true/false), reason (short)."
                        )
                    },
                    {
                        "inline_data": {
                            "mime_type": "image/jpeg",
                            "data": b64,
                        }
                    },
                ],
            }
        ],
        "generationConfig": {"temperature": 0, "maxOutputTokens": 80},
    }
    endpoints = [
        "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent",
        "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent",
        "https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent",
        "https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash-latest:generateContent",
        "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro:generateContent",
    ]
    for endpoint in endpoints:
        try:
            url = f"{endpoint}?key={GEMINI_API_KEY}"
            resp = requests.post(url, json=payload, timeout=VISION_TIMEOUT)
            if resp.status_code != 200:
                print(f"    ⚠️ Gemini vision failed: {resp.status_code}")
                continue
            data = resp.json()
            content = (
                data.get("candidates", [{}])[0]
                .get("content", {})
                .get("parts", [{}])[0]
                .get("text", "")
            )
            return _extract_json(content)
        except Exception as e:
            print(f"    ⚠️ Gemini vision error: {e}")
            continue
    return None


def vision_review_image_github(image_url: str):
    payload = {
        "model": VISION_MODEL_ID,
        "temperature": 0,
        "max_tokens": 120,
        "response_format": {"type": "json_object"},
        "messages": [
            {
                "role": "system",
                "content": "You are a strict image safety reviewer. Reply ONLY in JSON.",
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "Check if the image contains any visible hands, fingers, or people. "
                            "Return JSON with keys: has_hands (true/false), has_people (true/false), "
                            "safe (true/false), reason (short)."
                        ),
                    },
                    {"type": "image_url", "image_url": {"url": image_url}},
                ],
            },
        ],
    }

    base = VISION_API_BASE.rstrip("/")
    if base.endswith("/inference"):
        url = f"{base}/chat/completions"
    else:
        url = f"{base}/inference/chat/completions"

    try:
        resp = None
        for attempt in range(3):
            resp = requests.post(
                url,
                headers={
                    "Authorization": f"Bearer {VISION_API_KEY}",
                    "Content-Type": "application/json",
                    "Accept": "application/vnd.github+json",
                    "X-GitHub-Api-Version": "2022-11-28",
                },
                json=payload,
                timeout=VISION_TIMEOUT,
            )
            if resp.status_code != 429:
                break
            # Back off on rate limits and retry
            sleep_s = VISION_RETRY_SLEEP * (VISION_BACKOFF_FACTOR**attempt)
            time.sleep(min(sleep_s, 60))
        if resp is None or resp.status_code != 200:
            status = resp.status_code if resp is not None else "NO_RESPONSE"
            preview = resp.text.replace("\n", " ")[:200] if resp is not None else ""
            print(f"    ⚠️ Vision review failed: {status} {preview}")
            if GEMINI_API_KEY:
                return vision_review_image_gemini(image_url)
            return None

        data = resp.json()
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        if not content:
            print(f"    ⚠️ Vision response empty: {str(data)[:200]}")
            return None
        result = _extract_json(content)
        if result is None:
            result = _fallback_parse(content)
        if result is None:
            preview = content.replace("\n", " ")[:200]
            print(f"    ⚠️ Vision response not JSON: {preview}")
        return result
    except Exception as e:
        print(f"    ⚠️ Vision review error: {e}")
        return None


def vision_review_image(image_url: str):
    if not VISION_REVIEW:
        return None
    if VISION_PROVIDER == "gemini":
        result = vision_review_image_gemini(image_url)
        if result is None and VISION_API_KEY:
            return vision_review_image_github(image_url)
        return result
    return vision_review_image_github(image_url)


def is_vision_safe(result) -> bool:
    if result is None:
        return False
    if result.get("has_hands") or result.get("has_people"):
        return False
    if result.get("safe") is False:
        return False
    return True


def generate_valid_pollinations_image(
    prompt: str,
    width: int,
    height: int,
    seed_base: int,
    max_attempts: int = VISION_MAX_ATTEMPTS,
    used_urls: set | None = None,
):
    used_urls = used_urls or set()
    for attempt in range(max_attempts):
        seed = seed_base + attempt
        poll_url = get_pollinations_url(prompt, width, height, seed=seed)
        if poll_url in used_urls:
            continue
        vision_result = vision_review_image(poll_url)
        if VISION_REVIEW and not is_vision_safe(vision_result):
            print(f"    ⚠️ Vision reject: {vision_result}")
            sleep_s = VISION_RETRY_SLEEP * (VISION_BACKOFF_FACTOR**attempt)
            time.sleep(min(sleep_s, 30))
            continue
        img_bytes = download_image(poll_url)
        if img_bytes:
            used_urls.add(poll_url)
            return img_bytes, poll_url, vision_result
        sleep_s = VISION_RETRY_SLEEP * (VISION_BACKOFF_FACTOR**attempt)
        time.sleep(min(sleep_s, 30))
    return None, None, None


def generate_valid_lexica_image(
    query: str,
    used_urls: set | None = None,
):
    """Try Lexica (SD1.5 CC0) images first, then return first safe one."""
    used_urls = used_urls or set()
    candidates = search_lexica_images(query, limit=LEXICA_RESULT_LIMIT)
    for item in candidates:
        url = item["url"]
        if url in used_urls:
            continue
        vision_result = vision_review_image(url)
        if VISION_REVIEW and not is_vision_safe(vision_result):
            print(f"    ⚠️ Vision reject: {vision_result}")
            continue
        img_bytes = download_image(url)
        if img_bytes:
            used_urls.add(url)
            return img_bytes, url, vision_result
    return None, None, None


def _vertex_aspect_ratio(width: int, height: int) -> str:
    if height <= 0:
        return "1:1"
    ratio = width / height
    if 0.9 <= ratio <= 1.1:
        return "1:1"
    if ratio >= 1.2:
        return "4:3"
    return "3:4"


def _vertex_access_token() -> str | None:
    if not GOOGLE_APPLICATION_CREDENTIALS:
        return None
    if not os.path.exists(GOOGLE_APPLICATION_CREDENTIALS):
        return None
    try:
        from google.oauth2 import service_account
        from google.auth.transport.requests import Request
    except Exception as e:
        print(f"    ⚠️ google-auth not available: {e}")
        return None
    try:
        creds = service_account.Credentials.from_service_account_file(
            GOOGLE_APPLICATION_CREDENTIALS,
            scopes=["https://www.googleapis.com/auth/cloud-platform"],
        )
        creds.refresh(Request())
        return creds.token
    except Exception as e:
        print(f"    ⚠️ Vertex auth failed: {e}")
        return None


def _vertex_generate_image_bytes(
    prompt: str,
    width: int,
    height: int,
) -> bytes | None:
    if not GCP_PROJECT:
        return None
    token = _vertex_access_token()
    if not token:
        return None
    aspect_ratio = _vertex_aspect_ratio(width, height)
    payload = {
        "instances": [{"prompt": prompt}],
        "parameters": {
            "sampleCount": 1,
            "aspectRatio": aspect_ratio,
            "enhancePrompt": False,
            "personGeneration": "dont_allow",
        },
    }
    url = (
        f"https://{GCP_LOCATION}-aiplatform.googleapis.com/v1/projects/"
        f"{GCP_PROJECT}/locations/{GCP_LOCATION}/publishers/google/models/"
        f"{GEMINI_IMAGE_MODEL}:predict"
    )
    try:
        resp = requests.post(
            url,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json; charset=utf-8",
            },
            json=payload,
            timeout=120,
        )
        if resp.status_code != 200:
            print(f"    ⚠️ Vertex Imagen failed: {resp.status_code}")
            return None
        data = resp.json()
        predictions = data.get("predictions", [])
        if not predictions:
            return None
        b64 = predictions[0].get("bytesBase64Encoded")
        if not b64:
            return None
        return base64.b64decode(b64)
    except Exception as e:
        print(f"    ⚠️ Vertex Imagen error: {e}")
        return None


def generate_valid_vertex_image(
    prompt: str,
    width: int,
    height: int,
    max_attempts: int = VISION_MAX_ATTEMPTS,
):
    for attempt in range(max_attempts):
        img_bytes = _vertex_generate_image_bytes(prompt, width, height)
        if not img_bytes:
            sleep_s = VISION_RETRY_SLEEP * (VISION_BACKOFF_FACTOR**attempt)
            time.sleep(min(sleep_s, 30))
            continue
        vision_result = None
        if VISION_REVIEW:
            if GEMINI_API_KEY:
                vision_result = vision_review_bytes_gemini(img_bytes)
            else:
                temp_url = upload_to_shopify_cdn(
                    img_bytes, f"vision_tmp_{int(time.time())}.jpg"
                )
                if temp_url:
                    vision_result = vision_review_image(temp_url)
        if VISION_REVIEW and not is_vision_safe(vision_result):
            print(f"    ⚠️ Vision reject: {vision_result}")
            sleep_s = VISION_RETRY_SLEEP * (VISION_BACKOFF_FACTOR**attempt)
            time.sleep(min(sleep_s, 30))
            continue
        return img_bytes, None, vision_result
    return None, None, None


def _extract_existing_image_urls(body_html: str) -> set:
    urls = re.findall(r'<img[^>]+src=["\']([^"\']+)["\']', body_html or "")
    return {url.strip() for url in urls if url}


def _seed_base(article_id: int) -> int:
    return int(time.time()) % 100000 + int(article_id) % 1000 + random.randint(1, 999)


def upload_to_shopify_cdn(image_bytes: bytes, filename: str) -> str:
    """Upload image to Shopify Files via GraphQL API"""
    headers = {
        "X-Shopify-Access-Token": TOKEN,
        "Content-Type": "application/json",
    }

    graphql_url = f"https://{SHOP}/admin/api/{API_VERSION}/graphql.json"

    # Step 1: Get staged upload URL
    stage_query = """
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
                "filename": filename,
                "mimeType": "image/jpeg",
                "resource": "FILE",
                "httpMethod": "POST",
                "fileSize": str(len(image_bytes)),
            }
        ]
    }

    response = requests.post(
        graphql_url,
        headers=headers,
        json={"query": stage_query, "variables": variables},
    )

    if response.status_code != 200:
        print(f"    ❌ Stage upload failed: {response.status_code}")
        return None

    data = response.json()
    staged = data.get("data", {}).get("stagedUploadsCreate", {})

    if staged.get("userErrors"):
        print(f"    ❌ User errors: {staged['userErrors']}")
        return None

    targets = staged.get("stagedTargets", [])
    if not targets:
        print("    ❌ No staged targets returned")
        return None

    target = targets[0]
    upload_url = target["url"]
    resource_url = target["resourceUrl"]
    params = {p["name"]: p["value"] for p in target["parameters"]}

    # Step 2: Upload to staged URL
    files = {
        **{k: (None, v) for k, v in params.items()},
        "file": (filename, image_bytes, "image/jpeg"),
    }

    upload_response = requests.post(upload_url, files=files)

    if upload_response.status_code not in [200, 201, 204]:
        print(f"    ❌ File upload failed: {upload_response.status_code}")
        return None

    # Step 3: Create file in Shopify
    create_query = """
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

    create_variables = {
        "files": [
            {
                "originalSource": resource_url,
                "alt": filename.replace("_", " ").replace(".jpg", ""),
            }
        ]
    }

    create_response = requests.post(
        graphql_url,
        headers=headers,
        json={"query": create_query, "variables": create_variables},
    )

    if create_response.status_code != 200:
        return None

    create_data = create_response.json()
    files_result = create_data.get("data", {}).get("fileCreate", {})
    files_list = files_result.get("files", [])

    if files_list and files_list[0].get("image"):
        cdn_url = files_list[0]["image"]["url"]
        print(f"    ✅ CDN URL: {cdn_url[:60]}...")
        return cdn_url

    # Poll for CDN URL
    print("    ⏳ Waiting for CDN processing...")
    file_id = files_list[0].get("id") if files_list else None

    if file_id:
        for attempt in range(10):
            time.sleep(3)
            query = """
            query getFile($id: ID!) {
              node(id: $id) {
                ... on MediaImage {
                  image { url }
                }
              }
            }
            """
            resp = requests.post(
                graphql_url,
                headers=headers,
                json={"query": query, "variables": {"id": file_id}},
            )
            if resp.status_code == 200:
                node = resp.json().get("data", {}).get("node") or {}
                if node.get("image", {}).get("url"):
                    cdn_url = node["image"]["url"]
                    print(f"    ✅ CDN ready: {cdn_url[:60]}...")
                    return cdn_url

    return resource_url  # fallback


def generate_topic_specific_prompts(title: str) -> tuple[dict, str]:
    """Generate image prompts that are SPECIFIC to the article topic"""

    title_lower = title.lower()

    # Extract main subject - more intelligent parsing
    main_subject = title
    for prefix in [
        "how to ",
        "the ",
        "a ",
        "an ",
        "complete guide to ",
        "guide to ",
        "diy ",
    ]:
        if title_lower.startswith(prefix):
            main_subject = title[len(prefix) :]
            break

    # Clean up
    main_subject = main_subject.split(":")[0].split("+")[0].split("|")[0].strip()
    if len(main_subject) > 50:
        main_subject = " ".join(main_subject.split()[:6])

    # Topic-specific keywords for better image matching
    topic_keywords = main_subject.lower()

    safety_suffix = "object-only frame, static composition, empty scene, no interaction"

    # Generate SPECIFIC prompts based on the topic
    prompts = {
        "featured": {
            "prompt": (
                f"Studio product photo of {main_subject}, isolated on white background, "
                f"object-only scene, no text, no watermark, "
                f"16:9 aspect ratio, {QUALITY}, {safety_suffix}"
            ),
            "alt": f"{main_subject.title()} - Featured Image",
        },
        "inline1": {
            "prompt": (
                f"Materials and tools for {main_subject}, overhead flat lay, "
                f"isolated background, object-only, "
                f"professional photography, no text, no watermark, {QUALITY}, {safety_suffix}"
            ),
            "alt": f"Materials for {main_subject}",
        },
        "inline2": {
            "prompt": (
                f"Close-up product photo of {main_subject} components, isolated background, "
                f"object-only still life, no text, no watermark, "
                f"{QUALITY}, {safety_suffix}"
            ),
            "alt": f"Components for {main_subject}",
        },
        "inline3": {
            "prompt": (
                f"Finished {main_subject}, studio product shot, isolated on white background, "
                f"object-only, no text, no watermark, {QUALITY}, {safety_suffix}"
            ),
            "alt": f"Completed {main_subject}",
        },
    }

    # Make prompts even MORE specific based on keywords
    if "vinegar" in topic_keywords or "ferment" in topic_keywords:
        prompts["inline1"][
            "prompt"
        ] = f"Fresh fruit scraps, apple peels, glass jars for making homemade vinegar, rustic kitchen setting, {QUALITY}"
        prompts["inline2"][
            "prompt"
        ] = f"Glass jar with fruit scraps submerged in water for vinegar fermentation, {QUALITY}"
        prompts["inline3"][
            "prompt"
        ] = f"Beautiful homemade fruit vinegar in glass bottles, amber color, rustic labels, {QUALITY}"

    elif (
        "cordage" in topic_keywords
        or "rope" in topic_keywords
        or "fiber" in topic_keywords
    ):
        prompts["inline1"][
            "prompt"
        ] = f"Natural plant fibers for making cordage, bark strips, dried leaves, bushcraft materials, {QUALITY}"
        prompts["inline2"][
            "prompt"
        ] = f"Natural plant fibers twisted into strong rope using reverse wrap technique, laid on a table, {QUALITY}"
        prompts["inline3"][
            "prompt"
        ] = f"Finished natural cordage and handmade rope coiled beautifully, rustic outdoor setting, {QUALITY}"

    elif "cactus" in topic_keywords or "propagat" in topic_keywords:
        prompts["inline1"][
            "prompt"
        ] = f"Christmas cactus cuttings, small pots, potting soil, propagation supplies on table, {QUALITY}"
        prompts["inline2"][
            "prompt"
        ] = f"Christmas cactus segment cuttings with clean tools on a surface, {QUALITY}"
        prompts["inline3"][
            "prompt"
        ] = f"Rooted christmas cactus cuttings in small pots, new growth, healthy plants, {QUALITY}"

    elif (
        "drip" in topic_keywords
        or "water" in topic_keywords
        or "bottle" in topic_keywords
    ):
        prompts["inline1"][
            "prompt"
        ] = f"Plastic soda bottles, scissors, drill, garden supplies for DIY drip irrigation, {QUALITY}"
        prompts["inline2"][
            "prompt"
        ] = f"Plastic bottle with drilled holes for drip feeder system, tools arranged nearby, {QUALITY}"
        prompts["inline3"][
            "prompt"
        ] = f"Completed bottle drip feeder watering plants in garden, sustainable irrigation, {QUALITY}"

    elif (
        "survival" in topic_keywords
        or "garden" in topic_keywords
        or "medicine" in topic_keywords
    ):
        prompts["inline1"][
            "prompt"
        ] = f"Seeds, medicinal herbs, garden tools for survival garden planning, {QUALITY}"
        prompts["inline2"][
            "prompt"
        ] = f"Survival garden bed with medicinal herbs and vegetables planted, soil and tools arranged, {QUALITY}"
        prompts["inline3"][
            "prompt"
        ] = f"Thriving survival garden with medicinal plants and vegetables, abundant harvest, {QUALITY}"

    elif "pot" in topic_keywords or "planter" in topic_keywords:
        prompts["inline1"][
            "prompt"
        ] = f"Upcycled materials for DIY plant pots, cans, bottles, paint, crafting supplies, {QUALITY}"
        prompts["inline2"][
            "prompt"
        ] = f"Painted DIY plant pots made from recycled materials arranged on a table, {QUALITY}"
        prompts["inline3"][
            "prompt"
        ] = f"Beautiful collection of handmade DIY plant pots with succulents and plants, {QUALITY}"

    elif "ginger" in topic_keywords or "nausea" in topic_keywords:
        prompts["inline1"][
            "prompt"
        ] = f"Fresh ginger root, lemon slices, honey, and a ceramic mug for ginger tea, clean kitchen counter, {QUALITY}, {safety_suffix}"
        prompts["inline2"][
            "prompt"
        ] = f"Ginger tea preparation setup with sliced ginger simmering in a small pot, steam rising, close-up, {QUALITY}, {safety_suffix}"
        prompts["inline3"][
            "prompt"
        ] = f"Finished ginger tea in a mug with sliced ginger beside it, calming setting, {QUALITY}, {safety_suffix}"

    elif (
        "cinder" in topic_keywords
        or "block" in topic_keywords
        or "outdoor" in topic_keywords
    ):
        prompts["inline1"][
            "prompt"
        ] = f"Cinder blocks, paint, brushes, and outdoor decor materials for DIY garden projects, {QUALITY}, {safety_suffix}"
        prompts["inline2"][
            "prompt"
        ] = f"Painted cinder blocks arranged for outdoor garden decoration, {QUALITY}, {safety_suffix}"
        prompts["inline3"][
            "prompt"
        ] = f"Stunning cinder block garden furniture and planters in backyard, styled outdoor space, {QUALITY}, {safety_suffix}"

    for value in prompts.values():
        if safety_suffix not in value["prompt"].lower():
            value["prompt"] = f"{value['prompt']}, {safety_suffix}"

    return prompts, main_subject


def count_existing_images(body_html: str) -> dict:
    """Count different types of images in article"""
    pinterest_imgs = len(
        re.findall(
            r'<img[^>]+(?:data-source=["\']pinterest["\']|alt=["\']Pinterest:|src=["\'][^"\']*(?:pinimg\.com|pinterest_)[^"\']+)',
            body_html,
            re.IGNORECASE,
        )
    )
    shopify_imgs = len(
        re.findall(r'<img[^>]+src="[^"]*cdn\.shopify\.com[^"]*"', body_html)
    )
    pollinations_imgs = len(
        re.findall(r'<img[^>]+src="[^"]*pollinations\.ai[^"]*"', body_html)
    )
    pexels_imgs = len(re.findall(r'<img[^>]+src="[^"]*pexels\.com[^"]*"', body_html))
    total = len(re.findall(r"<img[^>]+>", body_html))

    return {
        "pinterest": pinterest_imgs,
        "shopify_cdn": shopify_imgs,
        "pollinations": pollinations_imgs,
        "pexels": pexels_imgs,
        "total": total,
    }


def _extract_img_src(img_tag: str) -> str:
    match = re.search(r'src=["\']([^"\']+)["\']', img_tag, re.IGNORECASE)
    return match.group(1).strip() if match else ""


def _is_pinterest_img_tag(img_tag: str) -> bool:
    tag_lower = img_tag.lower()
    if 'data-source="pinterest"' in tag_lower or "alt=\"pinterest:" in tag_lower:
        return True
    return bool(re.search(r'src=["\'][^"\']*(pinimg\.com|pinterest_)[^"\']+', img_tag, re.IGNORECASE))


def _strip_non_pinterest_images(body_html: str) -> str:
    def keep_or_drop_figure(match: re.Match) -> str:
        fig = match.group(0)
        return fig if _is_pinterest_img_tag(fig) else ""

    def keep_or_drop_img(match: re.Match) -> str:
        tag = match.group(0)
        return tag if _is_pinterest_img_tag(tag) else ""

    body_html = re.sub(
        r"<figure[^>]*>[\s\S]*?</figure>",
        keep_or_drop_figure,
        body_html,
        flags=re.IGNORECASE,
    )
    body_html = re.sub(
        r"<img[^>]+>",
        keep_or_drop_img,
        body_html,
        flags=re.IGNORECASE,
    )
    return body_html


def _hash_bytes(image_bytes: bytes) -> str:
    return hashlib.sha256(image_bytes).hexdigest() if image_bytes else ""


def fix_article_images(
    article_id: int, pinterest_image_url: str = None, dry_run: bool = False
) -> bool:
    """
    Fix article images properly:
    1. Keep/restore Pinterest image
    2. Remove any off-topic or duplicate images
    3. Add topic-specific AI images
    """

    headers = {"X-Shopify-Access-Token": TOKEN, "Content-Type": "application/json"}

    # Get article
    url = f"https://{SHOP}/admin/api/{API_VERSION}/blogs/{BLOG_ID}/articles/{article_id}.json"
    print("   Fetching article data...")
    response = requests.get(url, headers=headers, timeout=30)

    if response.status_code != 200:
        print(f"❌ Error fetching article {article_id}: {response.status_code}")
        return False

    article = response.json()["article"]
    title = article["title"]
    body_html = article["body_html"]
    existing_urls = _extract_existing_image_urls(body_html)
    pinterest_urls = set()
    for tag in re.findall(r"<img[^>]+>", body_html, re.IGNORECASE):
        if _is_pinterest_img_tag(tag):
            src = _extract_img_src(tag)
            if src:
                pinterest_urls.add(src)

    print(f"\n{'='*60}")
    print(f"📝 {title}")
    print(f"   ID: {article_id}")

    # Count existing images
    img_counts = count_existing_images(body_html)
    print(
        f"   Current images: Pinterest={img_counts['pinterest']}, Shopify CDN={img_counts['shopify_cdn']}, Total={img_counts['total']}"
    )

    # Generate topic-specific prompts
    prompts, main_subject = generate_topic_specific_prompts(title)
    print(f"\n🎨 Topic-specific prompts generated:")
    print(f"   Featured: {prompts['featured']['alt']}")
    print(f"   Inline1: {prompts['inline1']['alt']}")
    print(f"   Inline2: {prompts['inline2']['alt']}")
    print(f"   Inline3: {prompts['inline3']['alt']}")

    if not VISION_REVIEW:
        print("\n❌ VISION_REVIEW=1 is required to publish images.")
        return False
    if not (VISION_API_KEY or GEMINI_API_KEY):
        print("\n❌ VISION_API_KEY or GEMINI_API_KEY is required for vision review.")
        return False

    if dry_run:
        print("\n🔍 DRY RUN - No changes made")
        return True

    # Resolve Pinterest image from mapping only if missing in body
    if pinterest_urls:
        pinterest_image_url = None

    if not pinterest_image_url and not pinterest_urls:
        matched = load_matched_data().get("matched", [])
        for item in matched:
            if str(item.get("draft_id")) == str(article_id):
                pin_id = item.get("pin_id")
                if pin_id:
                    pinterest_image_url = get_pinterest_image_url(pin_id)
                break

    # Step 1: Clean up body - remove non-Pinterest inline images only
    # (Keep Pinterest images in place)
    new_html = _strip_non_pinterest_images(body_html)

    # Clean up empty paragraphs and extra whitespace
    new_html = re.sub(r"<p>\s*</p>", "", new_html)
    new_html = re.sub(r"\n{3,}", "\n\n", new_html)

    print(f"\n🧹 Cleaned existing images from body")

    # Step 2: Upload Pinterest images to Shopify CDN (avoid 403)
    used_image_hashes = set()
    pinterest_cdn_map = {}
    for url in sorted(pinterest_urls):
        if not url or "cdn.shopify.com" in url:
            continue
        print(f"\n📌 Uploading Pinterest image to CDN: {url[:60]}...")
        pin_bytes = download_image(url, max_retries=3)
        if not pin_bytes:
            print("    ⚠️ Failed to download Pinterest image; keeping original URL")
            continue
        digest = _hash_bytes(pin_bytes)
        if digest:
            used_image_hashes.add(digest)
        cdn_url = upload_to_shopify_cdn(pin_bytes, f"pinterest_{article_id}.jpg")
        if cdn_url:
            pinterest_cdn_map[url] = cdn_url

    for old_url, cdn_url in pinterest_cdn_map.items():
        new_html = new_html.replace(old_url, cdn_url)
        existing_urls.discard(old_url)
        existing_urls.add(cdn_url)
    pinterest_cdn_urls = set(pinterest_cdn_map.values())
    if pinterest_cdn_urls:
        def _mark_pinterest(match: re.Match) -> str:
            tag = match.group(0)
            src = _extract_img_src(tag)
            if src in pinterest_cdn_urls and 'data-source="pinterest"' not in tag.lower():
                return tag.replace("<img", '<img data-source="pinterest"', 1)
            return tag

        new_html = re.sub(
            r"<img[^>]+>", _mark_pinterest, new_html, flags=re.IGNORECASE
        )

    # Step 3: Generate and upload new AI images
    print("\n🖼️ Generating topic-specific AI images...")

    cdn_urls = []
    used_poll_urls = set(existing_urls)
    used_cdn_urls = set(existing_urls)
    featured_b64 = None
    seed_base = _seed_base(article_id)

    # Featured image
    print("\n  [1/4] Featured image:")
    featured_bytes = None
    if USE_LEXICA and LEXICA_STRICT:
        featured_bytes, _, _ = generate_valid_lexica_image(
            main_subject, used_urls=used_poll_urls
        )
        if not featured_bytes:
            print("❌ Lexica strict mode: no featured image found.")
            return False
    else:
        if USE_VERTEX_IMAGEN:
            featured_bytes, _, _ = generate_valid_vertex_image(
                prompts["featured"]["prompt"],
                1200,
                800,
            )
        if not LEXICA_FALLBACK_ONLY:
            if USE_LEXICA:
                featured_bytes, _, _ = generate_valid_lexica_image(
                    main_subject, used_urls=used_poll_urls
                )
        if not featured_bytes:
            featured_bytes, _, _ = generate_valid_pollinations_image(
                prompts["featured"]["prompt"],
                1200,
                800,
                seed_base=seed_base,
                used_urls=used_poll_urls,
            )
        if not featured_bytes and USE_LEXICA:
            featured_bytes, _, _ = generate_valid_lexica_image(
                main_subject, used_urls=used_poll_urls
            )
    if featured_bytes:
        import base64

        digest = _hash_bytes(featured_bytes)
        if digest in used_image_hashes:
            print("    ⚠️ Duplicate image detected for featured, regenerating...")
            featured_bytes = None
        else:
            used_image_hashes.add(digest)
        if featured_bytes:
            featured_b64 = base64.b64encode(featured_bytes).decode("utf-8")

    # Inline images
    lexica_queries = {
        "inline1": f"{main_subject} materials",
        "inline2": f"{main_subject} components",
        "inline3": f"{main_subject} finished",
    }
    for i, key in enumerate(["inline1", "inline2", "inline3"], 1):
        print(f"\n  [{i+1}/4] {prompts[key]['alt']}:")
        img_bytes = None
        cdn_url = None
        for attempt in range(VISION_MAX_ATTEMPTS):
            if USE_LEXICA and LEXICA_STRICT:
                img_bytes, _, _ = generate_valid_lexica_image(
                    lexica_queries.get(key, main_subject),
                    used_urls=used_poll_urls,
                )
                if not img_bytes:
                    print("❌ Lexica strict mode: no inline image found.")
                    return False
            else:
                if USE_VERTEX_IMAGEN and attempt == 0:
                    img_bytes, _, _ = generate_valid_vertex_image(
                        prompts[key]["prompt"],
                        1000,
                        667,
                        max_attempts=1,
                    )
                if USE_LEXICA and attempt == 0 and not LEXICA_FALLBACK_ONLY:
                    img_bytes, _, _ = generate_valid_lexica_image(
                        lexica_queries.get(key, main_subject),
                        used_urls=used_poll_urls,
                    )
                if not img_bytes:
                    img_bytes, _, _ = generate_valid_pollinations_image(
                        prompts[key]["prompt"],
                        1000,
                        667,
                        seed_base=seed_base + (i * 100) + attempt,
                        used_urls=used_poll_urls,
                    )
                if not img_bytes and USE_LEXICA:
                    img_bytes, _, _ = generate_valid_lexica_image(
                        lexica_queries.get(key, main_subject),
                        used_urls=used_poll_urls,
                    )
            if not img_bytes:
                continue
            digest = _hash_bytes(img_bytes)
            if digest in used_image_hashes:
                print("    ⚠️ Duplicate image bytes detected, regenerating...")
                img_bytes = None
                continue
            cdn_url = upload_to_shopify_cdn(
                img_bytes, f"article_{article_id}_{key}_{attempt}.jpg"
            )
            if not cdn_url:
                continue
            if cdn_url in used_cdn_urls:
                print("    ⚠️ Duplicate CDN URL detected, regenerating...")
                sleep_s = VISION_RETRY_SLEEP * (VISION_BACKOFF_FACTOR**attempt)
                time.sleep(min(sleep_s, 30))
                continue
            used_cdn_urls.add(cdn_url)
            cdn_urls.append((cdn_url, prompts[key]["alt"]))
            if digest:
                used_image_hashes.add(digest)
            break

    if featured_b64 is None or len(cdn_urls) < 3:
        print(
            f"\n❌ Image generation incomplete: featured={bool(featured_b64)} inline={len(cdn_urls)}/3"
        )
        print("   Skipping update to avoid bad images.")
        return False

    # Step 4: Add Pinterest image if missing in body
    if not pinterest_urls and pinterest_image_url:
        print(f"\n📌 Adding Pinterest image: {pinterest_image_url[:50]}...")
        pin_bytes = download_image(pinterest_image_url, max_retries=3)
        if pin_bytes:
            digest = _hash_bytes(pin_bytes)
            if digest:
                used_image_hashes.add(digest)
            cdn_url = upload_to_shopify_cdn(pin_bytes, f"pinterest_{article_id}.jpg")
            if cdn_url:
                pinterest_image_url = cdn_url

    # Step 5: Insert images into body
    paragraphs = list(re.finditer(r"</p>", new_html))
    total_paras = len(paragraphs)

    print(f"\n📝 Inserting images into {total_paras} paragraphs...")

    # Calculate positions for images
    images_to_insert = []

    # Pinterest image goes near the beginning (after 2nd paragraph) if missing
    if not pinterest_urls and pinterest_image_url and total_paras > 2:
        images_to_insert.append(
            {
                "pos_idx": 1,
                "url": pinterest_image_url,
                "alt": f"Pinterest: {title}",
                "source": "pinterest",
            }
        )

    # AI images distributed throughout
    def _even_positions(total: int, n: int) -> list[int]:
        if total <= 0:
            return []
        positions = []
        for idx in range(n):
            pos = int(((idx + 1) * total) / (n + 1))
            pos = max(0, min(total - 1, pos))
            positions.append(pos)
        # ensure unique and sorted
        return sorted(set(positions), reverse=False)

    ai_positions = _even_positions(total_paras, len(cdn_urls))
    if len(ai_positions) < len(cdn_urls):
        ai_positions = list(range(min(len(cdn_urls), total_paras)))

    for i, (cdn_url, alt) in enumerate(cdn_urls):
        if i < len(ai_positions):
            images_to_insert.append(
                {"pos_idx": ai_positions[i], "url": cdn_url, "alt": alt, "source": "ai"}
            )

    # Sort by position descending (insert from end to avoid position shifts)
    images_to_insert.sort(key=lambda x: x["pos_idx"], reverse=True)

    # Insert images
    for img in images_to_insert:
        pos_idx = img["pos_idx"]
        if pos_idx < len(paragraphs):
            pos = paragraphs[pos_idx].end()

            if img.get("source") == "pinterest":
                img_html = f"""
<figure style="margin: 30px auto; text-align: center; max-width: 900px;" data-source="pinterest">
    <img src="{img['url']}" alt="{img['alt']}" data-source="pinterest" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.1);">
    <figcaption style="font-style: italic; color: #666; margin-top: 10px; font-size: 0.9em;">{img['alt']}</figcaption>
</figure>
"""
            else:
                img_html = f"""
<figure style="margin: 30px auto; text-align: center; max-width: 900px;">
    <img src="{img['url']}" alt="{img['alt']}" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.1);">
    <figcaption style="font-style: italic; color: #666; margin-top: 10px; font-size: 0.9em;">{img['alt']}</figcaption>
</figure>
"""
            new_html = new_html[:pos] + img_html + new_html[pos:]
            # Re-find paragraphs after insertion
            paragraphs = list(re.finditer(r"</p>", new_html))

    # Step 6: Update article
    update_data = {
        "article": {"id": article_id, "body_html": new_html, "published": True}
    }

    # Add featured image if we have one
    if featured_b64:
        update_data["article"]["image"] = {
            "attachment": featured_b64,
            "alt": prompts["featured"]["alt"],
        }

    print("\n📤 Publishing updated article...")
    update_url = f"https://{SHOP}/admin/api/{API_VERSION}/blogs/{BLOG_ID}/articles/{article_id}.json"
    update_resp = requests.put(update_url, headers=headers, json=update_data)

    if update_resp.status_code == 200:
        final_counts = count_existing_images(new_html)
        pinterest_count = len(pinterest_urls) if pinterest_urls else (1 if pinterest_image_url else 0)
        print(f"\n✅ SUCCESS!")
        print(f"   Pinterest images: {pinterest_count}")
        print(f"   AI inline images: {len(cdn_urls)}")
        print(f"   Featured image: {'Yes' if featured_b64 else 'No'}")
        return True
    else:
        print(f"\n❌ Failed to update: {update_resp.status_code}")
        print(update_resp.text[:200])
        return False


def fix_all_matched_articles(dry_run: bool = False):
    """Fix all matched Pinterest articles"""

    matched_data = load_matched_data()
    articles = matched_data.get("matched", [])

    print(f"\n{'='*60}")
    print(f"FIX IMAGES PROPERLY - {len(articles)} matched articles")
    print(f"{'='*60}")

    success = 0
    failed = 0

    for article in articles:
        article_id = article["draft_id"]
        pin_id = article.get("pin_id", "")

        # Try to get Pinterest image URL
        pinterest_url = None
        if pin_id:
            # Pinterest image URL pattern
            pinterest_url = f"https://i.pinimg.com/736x/{pin_id}.jpg"

        if fix_article_images(article_id, pinterest_url, dry_run):
            success += 1
        else:
            failed += 1

        # Rate limiting
        if not dry_run:
            time.sleep(2)

    print(f"\n{'='*60}")
    print(f"DONE: {success} success, {failed} failed")
    print(f"{'='*60}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Fix article images properly")
    parser.add_argument("--article-id", type=int, help="Single article ID to fix")
    parser.add_argument("--all", action="store_true", help="Fix all matched articles")
    parser.add_argument("--dry-run", action="store_true", help="Don't make changes")
    args = parser.parse_args()

    if args.article_id:
        # Load matched data to get Pinterest URL
        matched_data = load_matched_data()
        pinterest_url = None
        for article in matched_data.get("matched", []):
            if article["draft_id"] == args.article_id:
                pin_id = article.get("pin_id", "")
                if pin_id:
                    pinterest_url = f"https://i.pinimg.com/736x/{pin_id}.jpg"
                break

        fix_article_images(args.article_id, pinterest_url, args.dry_run)
    elif args.all:
        fix_all_matched_articles(args.dry_run)
    else:
        print("Usage: python fix_images_properly.py --article-id ID [--dry-run]")
        print("       python fix_images_properly.py --all [--dry-run]")
