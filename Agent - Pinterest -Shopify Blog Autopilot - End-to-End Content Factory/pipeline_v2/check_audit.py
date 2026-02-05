#!/usr/bin/env python3
"""Check quality gate audit for an article."""
import os
import requests
from dotenv import load_dotenv

load_dotenv()

store = "https://" + os.getenv("SHOPIFY_STORE_DOMAIN", "").strip()
token = os.getenv("SHOPIFY_ACCESS_TOKEN")
blog_id = os.getenv("SHOPIFY_BLOG_ID")
headers = {"X-Shopify-Access-Token": token}

aid = 691791921470
url = f"{store}/admin/api/2025-01/blogs/{blog_id}/articles/{aid}.json"
r = requests.get(url, headers=headers)
article = r.json().get("article", {})

# Import quality gate
from ai_orchestrator import QualityGate

qg = QualityGate()
audit = qg.full_audit(article)

print("=== AUDIT RESULT ===")
print(f'Overall pass: {audit["overall_pass"]}')
print(f'Score: {audit["score"]}/10')
print()
print("=== DETERMINISTIC GATE ===")
gate = audit.get("deterministic_gate", {})
print(f'Gate pass: {gate.get("pass")}')
print(f'Gate score: {gate.get("score")}/10')
print()
print("=== ISSUES ===")
for issue in audit.get("issues", []):
    print(f"  - {issue}")
print()
print("=== DETAILS ===")
import json

details = audit.get("details", {})
for key, val in details.items():
    if isinstance(val, dict) and "pass" in val:
        status = "✅" if val["pass"] else "❌"
        print(f"{status} {key}: {val}")
