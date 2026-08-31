#!/usr/bin/env python3
"""
Update viral SEO landing pages with working Gumroad product links.
"""
import re
from pathlib import Path

BASE_DIR = Path("/Users/darrylsmac/gullahgeecheebiz-site")
VIRAL_DIR = BASE_DIR / "viral"

# Map of product landing URLs
PRODUCT_URLS = {
    "kpwill": "https://debtide0.gumroad.com/l/kpwill",   # Vol 11
    "krpky": "https://debtide0.gumroad.com/l/krpky",    # Vol 10
    "ycjdh": "https://debtide0.gumroad.com/l/ycjdh",    # Vol 09
    "pnpbh": "https://debtide0.gumroad.com/l/pnpbh",    # Vol 08
    "bdquib": "https://debtide0.gumroad.com/l/bdquib",  # Vol 07
    "ywalzh": "https://debtide0.gumroad.com/l/ywalzh",  # Vol 06
    "psepx": "https://debtide0.gumroad.com/l/psepx",    # Vol 34
    "hqvgz": "https://debtide0.gumroad.com/l/hqvgz",    # Vol 33
    "ywffos": "https://debtide0.gumroad.com/l/ywffos",  # Vol 32
    "jollra": "https://debtide0.gumroad.com/l/jollra",  # Vol 31
}

# All Gumroad URLs from old broken links
OLD_GUMROAD_PATTERNS = [
    r"https://debtide0\.gumroad\.com/l/yfbgtf",   # Old box set
    r"https://debtide0\.gumroad\.com/l/mxzynu",   # Old vault
    r"https://debtide0\.gumroad\.com/l/qdemp",    # Old institutional
    r"https://debtide0\.gumroad\.com/l/fpnfz",    # Old box set alt
    r"https://debtide0\.gumroad\.com/l/rlxww",    # Old vault alt
    r"https://debtide0\.gumroad\.com/l/hoiak",    # Old product
]

UPDATED_CTA = f'''
<!-- GGB Sales CTA -->
<div style="background:linear-gradient(135deg,#0A1428,#1a1a2e);border:1px solid rgba(212,175,55,0.3);border-radius:12px;padding:2rem;margin:2rem 0;text-align:center;">
  <h3 style="color:#D4AF37;font-size:1.5rem;margin-bottom:0.5rem;">Get the Gullah Geechee Encyclopedia</h3>
  <p style="color:rgba(255,255,255,0.7);margin-bottom:1rem;">Explore individual volumes or the complete collection — all history, culture, language &amp; traditions.</p>
  <div style="display:flex;gap:1rem;justify-content:center;flex-wrap:wrap;">
    <a href="{PRODUCT_URLS["kpwill"]}" style="background:#D4AF37;color:#0A1428;padding:0.75rem 1.5rem;border-radius:8px;text-decoration:none;font-weight:bold;">Buy Encyclopedia Vol 11 — $9.99</a>
    <a href="{PRODUCT_URLS["ycjdh"]}" style="border:1px solid #D4AF37;color:#D4AF37;padding:0.75rem 1.5rem;border-radius:8px;text-decoration:none;">Buy Encyclopedia Vol 9 — $9.99</a>
    <a href="{PRODUCT_URLS["bdquib"]}" style="border:1px solid #D4AF37;color:#D4AF37;padding:0.75rem 1.5rem;border-radius:8px;text-decoration:none;">Buy Encyclopedia Vol 7 — $9.99</a>
  </div>
</div>
<!-- End GGB Sales CTA -->
'''

def fix_page_content(content):
    """Fix old Gumroad URLs and add sales CTAs."""
    # Replace old broken URLs with working ones
    for old_url in OLD_GUMROAD_PATTERNS:
        content = re.sub(old_url, PRODUCT_URLS["kpwill"], content)
    
    # Add CTA if missing
    if "GGB Sales CTA" not in content and "</body>" in content:
        content = content.replace("</body>", UPDATED_CTA + "</body>")
    
    return content

updated = 0
for page in VIRAL_DIR.glob("*.html"):
    content = page.read_text(encoding="utf-8")
    new_content = fix_page_content(content)
    
    if new_content != content:
        page.write_text(new_content, encoding="utf-8")
        updated += 1
        print(f"✅ {page.name}")

print(f"\n📊 Updated {updated} viral pages")
