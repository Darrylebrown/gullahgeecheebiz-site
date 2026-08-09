#!/usr/bin/env python3
"""GGB Marketing Orchestrator helper:
1. Strip leaked internal '.agents/skills' related-content blocks from viral/ SEO pages.
2. Insert hub cards for new pages into viral/index.html.
"""
import re, sys
from pathlib import Path

SITE = Path("/Users/darrylsmac/gullahgeecheebiz-site")
VIRAL = SITE / "viral"

JUNK_RE = re.compile(
    r'<!--\s*Related Content\s*-->.*?<div class="related-content">.*?</div>\s*',
    re.DOTALL,
)

fixed = []
for p in sorted(VIRAL.glob("*.html")):
    if p.name == "index.html":
        continue
    txt = p.read_text()
    if ".agents/skills" not in txt:
        continue
    new = JUNK_RE.sub("", txt)
    if ".agents/skills" in new:
        # last resort: cut from comment to end-of-block
        new = re.sub(r'<!-- Related Content -->.*?(</div>\s*</div>)\s*(?=</body>)', '', new, flags=re.DOTALL)
    if ".agents/skills" in new:
        print(f"  !! could not fully clean {p.name}")
    p.write_text(new)
    fixed.append(p.name)

print(f"Cleaned .agents/skills related-content blocks from {len(fixed)} pages.")

# ---- Insert hub cards for new pages ----
hub = VIRAL / "index.html"
htxt = hub.read_text()
RICE_CARD = '''    <div class="card">
      <h2><a href="gullah-geechee-rice-history.html">Carolina Gold Rice &amp; Gullah Geechee Rice Cultivation History</a></h2>
      <p>Carolina Gold rice made the Lowcountry wealthy — and enslaved Gullah Geechee Africans built it. The untold history of rice and foodways....</p>
      <div class="lang"><a href="gullah-geechee-rice-history.html">English</a></div>
    </div>
    <div class="card">
      <h2><a href="sapelo-island-gullah-geechee.html">Sapelo Island Gullah Geechee: The Last Sea Island Community</a></h2>
      <p>Sapelo Island, Georgia is home to one of the last intact Gullah Geechee communities, Hog Hammock. History, culture, and travel guide....</p>
      <div class="lang"><a href="sapelo-island-gullah-geechee.html">English</a></div>
    </div>
'''
anchor = '    <div class="brand"><p>GULLAH GEECHEE BIZ</p></div>'
# use the card-block ending before .brand
marker = '      <p>Experience the real Gullah Geechee Lowcountry'
if "gullah-geechee-rice-history" not in htxt:
    # insert before the .brand div that closes the container
    if anchor in htxt:
        htxt = htxt.replace(anchor, RICE_CARD + "\n" + anchor, 1)
    else:
        # fallback: before </div>\n  </div>\n\n  <!-- Related Content -->
        htxt = htxt.replace('    </div>\n  </div>\n\n  <!-- Related Content -->',
                            RICE_CARD + '    </div>\n  </div>', 1)
    hub.write_text(htxt)
    print("Added 2 new hub cards to viral/index.html")
else:
    print("Hub cards already present.")

# verify counts
print("Remaining .agents/skills refs in viral/:",
      sum(1 for fp in VIRAL.glob('*.html') if '.agents/skills' in fp.read_text()))