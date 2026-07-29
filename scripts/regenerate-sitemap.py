#!/usr/bin/env python3
"""Regenerate sitemap.xml for gullahgeecheebiz-site."""
import os, glob
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
SITE_DIR = HERE if (HERE / "index.html").exists() else Path.home() / "gullahgeecheebiz-site"
BASE = "https://gullahgeecheebiz.com"

urls = []  # (path, priority)

def add(path, pri="0.7"):
    path = path.lstrip("/")
    urls.append((path, pri))

add("", "1.0")
for p in ["shop.html", "shop-binyah.html", "bot-dashboard.html"]:
    if (SITE_DIR / p).exists():
        add(p, "0.8")

# Section indexes
for section in [
    "membership", "season-1", "guide", "services", "dashboard", "viral",
    "trending", "tools", "recipes", "ebooks", "wholesale", "shop",
    "encyclopedia", "ggb-engine", "redeem", "merch",
]:
    if (SITE_DIR / section / "index.html").exists():
        add(f"{section}/", "0.9")

def walk_html(subdir, pri="0.7", skip_index=True):
    d = SITE_DIR / subdir
    if not d.is_dir():
        return
    for f in sorted(d.rglob("*.html")):
        if ".html.html" in f.name:
            continue
        rel = f.relative_to(SITE_DIR).as_posix()
        if skip_index and f.name == "index.html":
            # already added as section/
            if f.parent == d:
                continue
            # nested index
            add(str(f.relative_to(SITE_DIR).parent).replace("\\", "/") + "/", pri)
            continue
        name = rel[:-5] if rel.endswith(".html") else rel
        # pretty URLs without .html when file is leaf
        if rel.endswith(".html") and f.name != "index.html":
            add(rel.replace(".html", ""), pri)
        else:
            add(rel, pri)

for sub, pri in [
    ("viral", "0.7"), ("recipes", "0.8"), ("season-1", "0.6"),
    ("trending", "0.6"), ("encyclopedia", "0.7"), ("ebooks", "0.8"),
]:
    walk_html(sub, pri)

# tools/*
for tool_dir in sorted((SITE_DIR / "tools").glob("*/index.html")) if (SITE_DIR / "tools").exists() else []:
    add(f"tools/{tool_dir.parent.name}/", "0.7")

# dedupe preserve order
seen = set()
out = []
for path, pri in urls:
    if path in seen:
        continue
    seen.add(path)
    out.append((path, pri))

xml = ['<?xml version="1.0" encoding="UTF-8"?>',
       '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
for path, pri in out:
    loc = f"{BASE}/{path}" if path else f"{BASE}/"
    xml.append(f"  <url><loc>{loc}</loc><priority>{pri}</priority></url>")
xml.append("</urlset>")
(SITE_DIR / "sitemap.xml").write_text("\n".join(xml) + "\n")
print(f"Wrote {len(out)} URLs → {SITE_DIR / 'sitemap.xml'}")
