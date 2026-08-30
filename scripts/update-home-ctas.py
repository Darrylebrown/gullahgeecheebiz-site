#!/usr/bin/env python3
"""
Update homepage CTAs to point to the new 3-tier Gumroad offers.
Replaces old Gumroad URLs with the repurposed product links.
"""
import re
from pathlib import Path

BASE_DIR = Path("/Users/darrylsmac/gullahgeecheebiz-site")
INDEX = BASE_DIR / "index.html"

# New Gumroad URLs from the restructure
OFFER_LINKS = {
    "box_set": "https://debtide0.gumroad.com/l/yfbgtf",
    "heritage_vault": "https://debtide0.gumroad.com/l/mxzynu",
    "institutional": "https://debtide0.gumroad.com/l/qdemp",
}

content = INDEX.read_text()

# Track replacements
replacements = []

# Replace the Complete Box Set CTA
if 'https://debtide0.gumroad.com/l/fpnfz' in content:
    old = 'https://debtide0.gumroad.com/l/fpnfz'
    content = content.replace(old, OFFER_LINKS["box_set"])
    replacements.append(f"Box Set: {old} → {OFFER_LINKS['box_set']}")

# Replace the Heritage Vault CTA
if 'https://debtide0.gumroad.com/l/rlxww' in content:
    old = 'https://debtide0.gumroad.com/l/rlxww'
    content = content.replace(old, OFFER_LINKS["heritage_vault"])
    replacements.append(f"Heritage Vault: {old} → {OFFER_LINKS['heritage_vault']}")

# Replace the Institutional License CTA
if 'https://debtide0.gumroad.com/l/hoiak' in content:
    old = 'https://debtide0.gumroad.com/l/hoiak'
    content = content.replace(old, OFFER_LINKS["institutional"])
    replacements.append(f"Institutional: {old} → {OFFER_LINKS['institutional']}")

if replacements:
    INDEX.write_text(content)
    print(f"✅ Updated {len(replacements)} CTA links on homepage:")
    for r in replacements:
        print(f"   {r}")
else:
    print("⚠️  No old URLs found to replace (may already be updated)")
