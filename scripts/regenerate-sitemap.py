#!/usr/bin/env python3
"""Regenerate sitemap.xml with all pages including new recipes."""
import os, glob

HOME = os.path.expanduser("~")
SITE_DIR = os.path.join(HOME, "gullahgeecheebiz-site")
BASE = "https://gullahgeecheebiz.com"

urls = []

# Root pages
urls.append(("", "1.0"))
urls.append(("shop.html", "0.8"))
urls.append(("shop-binyah.html", "0.8"))
urls.append(("bot-dashboard.html", "0.5"))

# Sections
for section in ["membership", "season-1", "guide", "services", "dashboard", "viral", "trending", "tools", "recipes"]:
    index = os.path.join(SITE_DIR, section, "index.html")
    if os.path.exists(index):
        urls.append((f"{section}/", "0.9"))

# Viral pages
for f in sorted(glob.glob(os.path.join(SITE_DIR, "viral", "*.html"))):
    name = os.path.basename(f).replace(".html", "")
    if name != "index":
        urls.append((f"viral/{name}", "0.7"))

# Recipe pages
for f in sorted(glob.glob(os.path.join(SITE_DIR, "recipes", "*.html"))):
    name = os.path.basename(f).replace(".html", "")
    if name != "index":
        urls.append((f"recipes/{name}", "0.8"))

# Season 1 episodes
for f in sorted(glob.glob(os.path.join(SITE_DIR, "season-1", "*.html"))):
    name = os.path.basename(f).replace(".html", "")
    if name != "index":
        urls.append((f"season-1/{name}", "0.6"))

# Tools
for tool_dir in sorted(glob.glob(os.path.join(SITE_DIR, "tools", "*", "index.html"))):
    name = os.path.basename(os.path.dirname(tool_dir))
    urls.append((f"tools/{name}/", "0.7"))

# Trending
for f in sorted(glob.glob(os.path.join(SITE_DIR, "trending", "*.html"))):
    name = os.path.basename(f).replace(".html", "")
    urls.append((f"trending/{name}", "0.6"))

xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
xml += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
for path, priority in urls:
    xml += f'  <url><loc>{BASE}/{path}</loc><priority>{priority}</priority></url>\n'
xml += '</urlset>\n'

with open(os.path.join(SITE_DIR, "sitemap.xml"), "w") as f:
    f.write(xml)

count = len(urls)
print(f"Sitemap regenerated: {count} URLs")
