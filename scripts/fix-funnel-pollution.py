#!/usr/bin/env python3
"""Fix GGB funnel pages: strip cross-project/AI-garbage pollution from the 50
encyclopedia-vol-NN lead-magnet pages. Rebuilds <title>, meta description,
social-share block, and related-content block with canonical GGB content.
Only touches publish/funnel/encyclopedia-vol-*/*.html that match the template.
"""
import re
from pathlib import Path
from urllib.parse import quote

FUNNEL = Path("/Users/darrylsmac/gullahgeecheebiz-site/publish/funnel")
VOLS = sorted(FUNNEL.glob("encyclopedia-vol-*/index.html"))

JUNK_TOKENS = [
    "cinematic", "Cinematic", "film", "Film", "template vault", "esoteric",
    "OmniRoute", "console-build", "Opportunity Map", "opportunity map",
    "secret archives", "ancient mysteries", "visionary worlds",
    "Creative Story Inspiration", "Electronic Dictionary", "Elevate Your",
]

def vol_number(path: Path) -> str:
    m = re.search(r"encyclopedia-vol-(\d+)", path.parent.name)
    return m.group(1) if m else "?"

def build_share(url: str, label: str) -> str:
    text = quote(f"Free Gullah Geechee Encyclopedia {label} — Heritage & Culture")
    return (
        '  <div class="social-share">\n'
        '    <p>Share this: \n'
        f'      <a href="https://twitter.com/intent/tweet?text={text}" target="_blank">Twitter</a> |\n'
        f'      <a href="https://www.facebook.com/sharer/sharer.php?u={url}" target="_blank">Facebook</a> |\n'
        f'      <a href="https://pinterest.com/pin/create/button/?url={url}&description={text}" target="_blank">Pinterest</a>\n'
        '    </p>\n'
        '  </div>'
    )

def build_related() -> str:
    return (
        '  <div class="related-content">\n'
        '    <h3>Explore More Free Gullah Geechee Books</h3>\n'
        '    <ul>\n'
        '      <li><a href="/publish/funnel/full-catalog/">Browse the Full Free Book Library</a></li>\n'
        '      <li><a href="/books.html">Books &amp; Collections</a></li>\n'
        '      <li><a href="/guide/">Free Gullah Geechee Corridor Guide</a></li>\n'
        '      <li><a href="/">Gullah Geechee Biz Home</a></li>\n'
        '    </ul>\n'
        '  </div>'
    )

changed, skipped = [], []
for f in VOLS:
    nn = vol_number(f)
    html = f.read_text(encoding="utf-8", errors="replace")
    orig = html

    # 1) Title
    html = re.sub(
        r"<title>.*?</title>",
        f"<title>Free Gullah Geechee Encyclopedia Vol. {nn} | Heritage &amp; Culture</title>",
        html, count=1, flags=re.S)

    # 2) Meta description
    desc = (f"Get Encyclopedia Vol. {nn} free when you join the Gullah Geechee "
            f"reading circle — history, culture & heritage. Weekly stories, "
            "recipes, and first access to new releases.")
    html = re.sub(
        r'<meta name="description" content="[^"]*">',
        f'<meta name="description" content="{desc}">',
        html, count=1)

    # 3) Rebuild social-share + related-content tail (kills stacked dupes too)
    url = f"https://gullahgeecheebiz.com/publish/funnel/encyclopedia-vol-{nn}/"
    label = f"Vol. {nn}"
    tail = f"{build_share(url, label)}\n{build_related()}\n</body>\n</html>"
    if "<!-- Social Sharing -->" in html and "</body>" in html:
        html = html.split("<!-- Social Sharing -->", 1)[0] + tail
    else:
        skipped.append((f.name, "no social marker"))
        continue

    if html == orig:
        skipped.append((f.name, "no change"))
        continue

    # 4) Final junk sweep — any remaining junk token = flag for manual review
    leftover = [t for t in JUNK_TOKENS if t.lower() in html.lower()]
    f.write_text(html, encoding="utf-8")
    changed.append((f.name, leftover))

print(f"Processed {len(VOLS)} volume pages")
print(f"Changed: {len(changed)}")
for name, leftover in changed:
    flag = f"  LEFTOVER: {leftover}" if leftover else ""
    print(f"  OK {name}{flag}")
for name, why in skipped:
    print(f"  SKIP {name}: {why}")
