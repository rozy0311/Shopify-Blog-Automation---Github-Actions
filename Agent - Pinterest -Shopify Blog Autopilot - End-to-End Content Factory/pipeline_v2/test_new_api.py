#!/usr/bin/env python3
"""Test Pollinations.ai API - New endpoint"""
import requests

# NEW endpoint: gen.pollinations.ai/image/{prompt}
url = "https://gen.pollinations.ai/image/beautiful%20garden%20with%20flowers?model=flux&width=512&height=512"
print(f"Testing NEW API: {url}")

try:
    r = requests.get(url, timeout=180)
    print(f"Status: {r.status_code}")
    print(f"Size: {len(r.content)} bytes")
    print(f"Content-Type: {r.headers.get('content-type')}")

    # Check if it's an image
    if len(r.content) > 10000 and (
        r.content[:4] == b"\xff\xd8\xff\xe0" or r.content[:4] == b"\xff\xd8\xff\xe1"
    ):
        print("Γ£à Valid JPEG image!")
        with open("test_new_api.jpg", "wb") as f:
            f.write(r.content)
        print("Saved to test_new_api.jpg")
    elif r.content[:8] == b"\x89PNG\r\n\x1a\n":
        print("Γ£à Valid PNG image!")
        with open("test_new_api.png", "wb") as f:
            f.write(r.content)
        print("Saved to test_new_api.png")
    else:
        print(f"Content preview: {r.content[:200]}")
except Exception as e:
    print(f"Error: {e}")
