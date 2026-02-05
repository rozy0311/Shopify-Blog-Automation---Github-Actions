#!/usr/bin/env python3
"""Deep scan articles for scattered generic phrases."""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

store = 'https://' + os.getenv('SHOPIFY_STORE_DOMAIN', '').strip()
token = os.getenv('SHOPIFY_ACCESS_TOKEN')
blog_id = os.getenv('SHOPIFY_BLOG_ID')

url = f'{store}/admin/api/2025-01/blogs/{blog_id}/articles.json?limit=20'
headers = {'X-Shopify-Access-Token': token}
r = requests.get(url, headers=headers)
articles = r.json().get('articles', [])

# Expanded list of scattered generic phrases
scattered_patterns = [
    # Template placeholders
    '[Insert', '[Add', '[Your', '[Specific',
    'Lorem ipsum', 'placeholder text',
    # Generic filler phrases
    'It is important to note that',
    'In this section, we will',
    'As mentioned above',
    'As discussed earlier',
    # Template source patterns
    'Example: EPA or FDA guidelines',
    'manufacturer instructions, official guidelines',
    # Generic advice
    'Consult a professional before',
    'Always do your research before',
    'Results may vary',
    # Template FAQ answers
    'A clean workspace, basic tools',
    'reliable materials',
    'Follow best practices and',
    'standard safety protocols',
    # Other generic section markers
    'used throughout the content below',
    'Central to',
    'provides guidelines and best practices',
    'is essential for achieving optimal results',
    # Broken/incomplete content
    '...more content here...',
    'TODO:',
    'FIXME:',
]

print(f'Deep scanning {len(articles)} articles for scattered generic phrases...')
print()

warn_count = 0
for a in articles:
    body = a.get('body_html', '').lower()
    aid = a['id']
    title = a['title'][:45]
    found = []
    for p in scattered_patterns:
        if p.lower() in body:
            found.append(p[:30])
    if found:
        print(f'[WARN] {aid}: {title}')
        for f in found[:5]:
            print(f'        - "{f}"')
        warn_count += 1
    else:
        print(f'[OK]   {aid}: {title}')

print()
print(f'Summary: {warn_count} articles have potential issues')
