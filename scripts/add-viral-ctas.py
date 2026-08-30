#!/usr/bin/env python3
"""
Add Gumroad offer CTAs to viral SEO landing pages.
Targets high-traffic pages and adds a bottom-of-page CTA for the Complete Box Set.
"""
import re
from pathlib import Path

BASE_DIR = Path("/Users/darrylsmac/gullahgeecheebiz-site")
VIRAL_DIR = BASE_DIR / "viral"
BOX_SET_URL = "https://debtide0.gumroad.com/l/yfbgtf"
VAULT_URL = "https://debtide0.gumroad.com/l/mxzynu"

CTA_BLOCK = f'''
<!-- GGB Sales CTA -->
<div style="background:linear-gradient(135deg,#0A1428,#1a1a2e);border:1px solid rgba(212,175,55,0.3);border-radius:12px;padding:2rem;margin:2rem 0;text-align:center;">
  <h3 style="color:#D4AF37;font-size:1.5rem;margin-bottom:0.5rem;">Preserve Gullah Geechee Heritage</h3>
  <p style="color:rgba(255,255,255,0.7);margin-bottom:1rem;">Get the complete 25-volume Encyclopedia collection — all history, culture, language &amp; traditions in one digital box set.</p>
  <div style="display:flex;gap:1rem;justify-content:center;flex-wrap:wrap;">
    <a href="{BOX_SET_URL}" style="background:#D4AF37;color:#0A1428;padding:0.75rem 1.5rem;border-radius:8px;text-decoration:none;font-weight:bold;">Get the Box Set — $39.99</a>
    <a href="{VAULT_URL}" style="border:1px solid #D4AF37;color:#D4AF37;padding:0.75rem 1.5rem;border-radius:8px;text-decoration:none;">Open the Heritage Vault — $97</a>
  </div>
</div>
<!-- End GGB Sales CTA -->
'''

# Pages most likely to convert (culture/history/genealogy focused)
TARGET_PAGES = [
    "gullah-geechee-heritage-guide.html",
    "gullah-geechee-genealogy-research-guide.html",
    "gullah-geechee-books-collection.html",
    "gullah-geechee-culture-guide-2026.html",
    "gullah-geechee-lowcountry-recipes-traditional.html",
    "gullah-geechee-food-history.html",
    "gullah-geechee-music-origins.html",
    "gullah-language-preservation.html",
    "gullah-geechee-traditions-explained.html",
    "gullah-geechee-ancestry-genealogy.html",
]

updated = []
skipped = []

for page_name in TARGET_PAGES:
    page_path = VIRAL_DIR / page_name
    if not page_path.exists():
        skipped.append(f"MISSING: {page_name}")
        continue
    
    content = page_path.read_text()
    
    # Check if CTA already exists
    if "GGB Sales CTA" in content:
        skipped.append(f"ALREADY_HAS_CTA: {page_name}")
        continue
    
    # Add CTA before closing </body> tag
    if "</body>" in content:
        new_content = content.replace("</body>", CTA_BLOCK + "</body>")
        page_path.write_text(new_content)
        updated.append(page_name)
        print(f"✅ {page_name}")
    else:
        skipped.append(f"NO_BODY_TAG: {page_name}")

print(f"\n📊 RESULT: {len(updated)} pages updated, {len(skipped)} skipped")
if skipped:
    for s in skipped:
        print(f"   {s}")
