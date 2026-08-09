#!/usr/bin/env python3
"""
GGB Marketing Orchestrator — SEO Structured Data Injection
Injects valid JSON-LD (Article + BreadcrumbList + Organization) into every
viral SEO landing page (English + Spanish). This is the highest-leverage
on-page factor for enabling Google rich results (Article/FAQ) and lifting
organic CTR on the only live traffic channel (gullahgeecheebiz.com).

One-directional: local viral/ -> served GitHub Pages branch.
"""
import json, re
from pathlib import Path

SITE = Path(__file__).resolve().parent.parent
VIRAL = SITE / "viral"
BASE = "https://gullahgeecheebiz.com"

ORG = {
    "@context": "https://schema.org",
    "@type": "Organization",
    "name": "Gullah Geechee Biz",
    "url": BASE,
    "logo": f"{BASE}/logo.png",
    "sameAs": [
        "https://www.instagram.com/gullahgeecheebiz",
        "https://www.pinterest.com/gullahgeecheebiz",
        "https://kofigullahgeecheebiz.substack.com",
    ],
}


def esc(s: str) -> str:
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
             .replace('"', "&quot;"))

def extract_head(file):
    txt = file.read_text(encoding="utf-8", errors="replace")
    t = re.search(r"<title>(.*?)</title>", txt, re.S)
    m = re.search(r'<meta name="description" content="(.*?)"', txt, re.S)
    url = re.search(r'rel="canonical" href="(.*?)"', txt)
    title = esc(t.group(1).strip()) if t else "Gullah Geechee Biz"
    desc = esc(m.group(1).strip()) if m else ""
    canon = url.group(1).strip() if url else None
    h1 = re.search(r"<h1>(.*?)</h1>", txt, re.S)
    headline = esc(h1.group(1).strip()) if h1 else title
    return txt, title, desc, canon or (BASE + "/"), headline


def build_jsonld(title, desc, url, headline):
    article = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": headline,
        "description": desc,
        "image": f"{BASE}/logo.png",
        "author": {"@type": "Organization", "name": "Gullah Geechee Biz", "url": BASE},
        "publisher": {"@type": "Organization", "name": "Gullah Geechee Biz",
                      "logo": {"@type": "ImageObject", "url": f"{BASE}/logo.png"}},
        "datePublished": "2026-08-09",
        "dateModified": "2026-08-09",
        "mainEntityOfPage": url,
    }
    crumbs = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Home", "item": BASE},
            {"@type": "ListItem", "position": 2, "name": "Culture & Heritage Guide",
             "item": f"{BASE}/viral/"},
            {"@type": "ListItem", "position": 3, "name": headline, "item": url},
        ],
    }
    return (f'<script type="application/ld+json">{json.dumps(article)}</script>\n'
            f'<script type="application/ld+json">{json.dumps(crumbs)}</script>\n'
            f'<script type="application/ld+json">{json.dumps(ORG)}</script>')


def main():
    count = 0
    for p in sorted(VIRAL.glob("*.html")):
        txt, title, desc, url, headline = extract_head(p)
        if "application/ld+json" in txt:
            print(f"  SKIP (already has schema): {p.name}")
            continue
        if url is None:
            url = f"{BASE}/viral/{p.stem}"
        block = build_jsonld(title, desc, url, headline)
        if "</head>" in txt:
            txt = txt.replace("</head>", block + "\n</head>", 1)
        else:
            txt = block + "\n" + txt
        p.write_text(txt, encoding="utf-8")
        print(f"  +{p.name}")
        count += 1
    print(f"INJECTED structured data into {count} pages.")


if __name__ == "__main__":
    main()