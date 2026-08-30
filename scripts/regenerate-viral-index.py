#!/usr/bin/env python3
"""Regenerate the viral index page to include all pages."""
from pathlib import Path
import os

BASE = Path("/Users/darrylsmac/gullahgeecheebiz-site")
VIRAL = BASE / "viral"
INDEX = VIRAL / "index.html"

# Collect all .html files (excluding index.html)
pages = []
for f in sorted(VIRAL.glob("*.html")):
    if f.name == "index.html":
        continue
    name = f.stem
    # Skip Spanish versions for listing
    if "-es" in name:
        continue
    # Extract display title from filename
    display = name.replace("-", " ").title()
    pages.append((name, display, f))

# Generate index
html_parts = [
    '<!DOCTYPE html>',
    '<html lang="en">',
    '<head>',
    '  <meta charset="UTF-8">',
    '  <meta name="viewport" content="width=device-width, initial-scale=1.0">',
    '  <title>Gullah Geechee Culture: Heritage & Business</title>',
    '  <meta name="description" content="Explore the vibrant Gullah Geechee culture, its rich heritage, and dynamic businesses. Discover traditions, art, and entrepreneurship in one captivating experience.">',
    '  <link rel="canonical" href="https://gullahgeecheebiz.com/viral/">',
    '  <style>',
    '    * { margin: 0; padding: 0; box-sizing: border-box; }',
    '    body { font-family: -apple-system, BlinkMacSystemFont, \'Segoe UI\', Roboto, sans-serif; background: #0a0a14; color: #f0ede5; line-height: 1.6; }',
    '    .container { max-width: 800px; margin: 0 auto; padding: 40px 20px; }',
    '    h1 { font-family: Georgia, \'Times New Roman\', serif; font-size: 2em; color: #d4af37; margin-bottom: 10px; }',
    '    .subtitle { margin-bottom: 30px; color: #999; }',
    '    .card { background: #12121e; border-radius: 12px; padding: 24px; margin-bottom: 16px; border: 1px solid #222; }',
    '    .card h2 { font-size: 1.2em; margin-bottom: 8px; }',
    '    .card h2 a { color: #d4af37; text-decoration: none; }',
    '    .card h2 a:hover { text-decoration: underline; }',
    '    .card .lang { color: #666; font-size: 0.8em; margin-top: 8px; }',
    '    .card .lang a { color: #d4af37; text-decoration: none; }',
    '    @media (max-width: 600px) { h1 { font-size: 1.5em; } .container { padding: 20px 15px; } }',
    '  </style>',
    '</head>',
    '<body>',
    '<div class="container">',
    '  <nav style="margin-bottom:30px;opacity:.7"><a href="/" style="color:#d4af37;text-decoration:none;font-size:.9em">&larr; Back to Gullah Geechee Biz</a></nav>',
    '  <h1>Gullah Geechee Culture & Heritage</h1>',
    '  <p class="subtitle">Free digital guides, culturalExploring Gullah Geechee Culture & History</p>',
    '  <div class="cards">',
]

for name, display, fpath in pages:
    desc = ""
    if "encyclopedia" in name or "box-set" in name:
        desc = "Buy the complete 25-volume Encyclopedia Box Set and explore Sea Island heritage."
    elif "words" in name or "phrases" in name:
        desc = "Learn essential Gullah Geechee words and phrases still spoken on the Sea Islands."
    elif "genealogy" in name:
        desc = "Trace your Gullah Geechee ancestry with our complete research guide."
    elif "recipes" in name:
        desc = "Traditional Gullah Geechee recipes from the Lowcountry — red rice, shrimp and grits, and more."
    elif "heirs" in name:
        desc = "Heirs' property explained — how Gullah Geechee families have held land for generations."
    elif "sweetgrass" in name:
        desc = "Sweetgrass baskets are one of the oldest African art forms in North America."
    elif "language" in name:
        desc = "The Gullah language is an English-based creole with direct roots in West African languages."
    elif "food" in name:
        desc = "Red rice, okra soup, shrimp and grits — Gullah Geechee cuisine shaped Southern food."
    else:
        desc = f"Explore {display.replace('&', 'and')}."
    
    html_parts.append(f'    <div class="card">\n      <h2><a href="{name}.html">{display}</a></h2>\n      <p>{desc}</p>\n      <div class="lang"><a href="{name}.html">English</a></div>\n    </div>')

html_parts.extend([
    '  </div>',
    '  <footer style="margin-top:40px;padding-top:20px;border-top:1px solid #333;font-size:.85em;color:#666;text-align:center">',
    '    &copy; 2026 Gullah Geechee Biz. Preserve the past. Inspire the future.',
    '  </footer>',
    '</div>',
    '</body>',
    '</html>'
])

INDEX.write_text("\n".join(html_parts), encoding="utf-8")
print(f"Updated index with {len(pages)} pages.")
