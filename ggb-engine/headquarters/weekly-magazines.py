#!/usr/bin/env python3
"""
GGB Weekly Sports Magazine Generator — produces 7 sport magazines
every week in English and Spanish. Runs as a cron job.
"""
import json, os, sys, sqlite3, hashlib, urllib.request, time, re
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
PUB_DB = REPO_ROOT / "publish" / "publisher.db"
OUTPUT_DIR = REPO_ROOT / "publish" / "magazines"
SITE_DIR = REPO_ROOT
LOGS_DIR = Path(__file__).resolve().parent / "logs"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)

AGNES_KEY = os.environ.get("AGNES_API_KEY", "sk-qGBXic9m7VJcJ1vLJ6UPDdJLUbbunIWsNWs4Yl8RqFOfJPCj")
AGNES_URL = "https://apihub.agnes-ai.com/v1/chat/completions"

SPORTS = [
    {"name": "Pickleball", "slug": "pickleball", "tagline": "The fastest-growing sport in America"},
    {"name": "Volleyball", "slug": "volleyball", "tagline": "Spike, set, and serve your way to greatness"},
    {"name": "Indoor Golf", "slug": "indoor-golf", "tagline": "Perfect your swing year-round"},
    {"name": "Golf", "slug": "golf", "tagline": "Where legends are made on the fairway"},
    {"name": "Basketball", "slug": "basketball", "tagline": "From the court to the culture"},
    {"name": "Soccer", "slug": "soccer", "tagline": "The world's game, every week"},
    {"name": "Football", "slug": "football", "tagline": "Gridiron greatness, delivered weekly"},
    {"name": "Church & Faith", "slug": "church-faith", "tagline": "Weekly inspiration, devotionals, and community news"},
    {"name": "Fishing & Boating", "slug": "fishing-boating", "tagline": "Cast your line, chart your course — every week"},
    {"name": "Tourism", "slug": "tourism", "tagline": "Explore the world, one destination at a time"},
    {"name": "Dining", "slug": "dining", "tagline": "Savor every bite — restaurant reviews and recipes"},
    {"name": "Fitness", "slug": "fitness", "tagline": "Stronger every day — workouts, nutrition, wellness"},
    {"name": "Cooking", "slug": "cooking", "tagline": "From kitchen to table — recipes, tips, and techniques"},
    {"name": "Retirement", "slug": "retirement", "tagline": "Your guide to living the good life after work"},
    {"name": "Investing", "slug": "investing", "tagline": "Build wealth wisely — markets, strategies, insights"},
    {"name": "Cars", "slug": "cars", "tagline": "Reviews, news, and the open road"},
    {"name": "Trucking", "slug": "trucking", "tagline": "The backbone of America — on the road and in the know"},
]

def call_agnes(prompt: str, max_tokens: int = 4000) -> str:
    """Call Agnes 2.5 Flash with a prompt."""
    data = json.dumps({
        "model": "agnes-2.5-flash",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
    }).encode()
    req = urllib.request.Request(AGNES_URL, data=data, headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {AGNES_KEY}",
    })
    resp = urllib.request.urlopen(req, timeout=180)
    result = json.loads(resp.read())
    return result["choices"][0]["message"]["content"]

def generate_magazine(sport: Dict, lang: str = "en") -> Dict:
    """Generate a weekly magazine issue for a sport."""
    now = datetime.now(timezone.utc)
    week_num = now.isocalendar()[1]
    year = now.year
    issue = f"{sport['name']} Weekly — Issue {week_num}, {year}"
    
    title = issue if lang == "en" else f"{sport['name']} Semanal — Edición {week_num}, {year}"
    lang_name = "English" if lang == "en" else "Spanish"
    
    print(f"  📝 {title} ({lang_name})")
    
    # Generate the magazine content
    prompt = f"""Write a weekly {sport['name'].lower()} magazine issue in {lang_name}. 
This is Issue {week_num} of {year}.

Write 1500-2000 words with these sections:
1. Cover Story — the biggest story in {sport['name'].lower()} this week
2. Player Spotlight — a featured player or team
3. Game Analysis — breakdown of a key game or match
4. Tips & Training — advice for players of all levels
5. Upcoming Events — what to watch for next week
6. Community Corner — grassroots and local news
7. History Lesson — a look back at {sport['name'].lower()} history

Write in an engaging, magazine-style tone. Include specific names, dates, and details.
Make it feel like a real sports publication.

Tagline: {sport['tagline']}"""

    content = call_agnes(prompt, max_tokens=6000)
    words = len(content.split())
    
    # Save the magazine
    slug = sport['slug']
    lang_suffix = "" if lang == "en" else "-es"
    filename = f"{slug}-weekly-{year}-w{week_num:02d}{lang_suffix}.md"
    filepath = OUTPUT_DIR / filename
    filepath.write_text(content)
    
    # Also generate an HTML version for the site
    html_filename = f"{slug}-weekly-{year}-w{week_num:02d}{lang_suffix}.html"
    html_path = SITE_DIR / "magazines" / html_filename
    html_path.parent.mkdir(parents=True, exist_ok=True)
    
    html = f"""<!DOCTYPE html>
<html lang="{lang}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} — Gullah Geechee Biz</title>
    <meta name="description" content="{sport['tagline']} — Weekly issue {week_num}, {year}. In-depth coverage, player spotlights, game analysis, tips, and community news.">
    <meta name="keywords" content="{sport['name'].lower()}, weekly magazine, {sport['name'].lower()} news, {sport['name'].lower()} tips, sports magazine, gullah geechee biz, issue {week_num} {year}">
    <meta name="robots" content="index, follow">
    <link rel="canonical" href="https://gullahgeecheebiz.com/magazines/{html_filename}">
    <meta property="og:type" content="article">
    <meta property="og:title" content="{title}">
    <meta property="og:description" content="{sport['tagline']} — Weekly issue {week_num}, {year}. Read the latest {sport['name'].lower()} coverage.">
    <meta property="og:url" content="https://gullahgeecheebiz.com/magazines/{html_filename}">
    <meta property="og:site_name" content="Gullah Geechee Biz">
    <meta property="og:locale" content="{'en_US' if lang == 'en' else 'es_ES'}">
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:title" content="{title}">
    <meta name="twitter:description" content="{sport['tagline']} — Weekly issue {week_num}, {year}.">
    <script type="application/ld+json">
    {{
        "@context": "https://schema.org",
        "@type": "NewsArticle",
        "headline": "{title}",
        "description": "{sport['tagline']} — Weekly issue {week_num}, {year}",
        "datePublished": "{datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}",
        "author": {{
            "@type": "Organization",
            "name": "Gullah Geechee Biz"
        }},
        "publisher": {{
            "@type": "Organization",
            "name": "Gullah Geechee Biz",
            "url": "https://gullahgeecheebiz.com"
        }},
        "isPartOf": {{
            "@type": "Periodical",
            "name": "{sport['name']} Weekly",
            "issn": ""
        }},
        "inLanguage": "{'en-US' if lang == 'en' else 'es-ES'}"
    }}
    </script>
    <link rel="stylesheet" href="/style.css">
</head>
<body>
    <nav><a href="/">Home</a> &raquo; <a href="/magazines/">Magazines</a> &raquo; <span>{title}</span></nav>
    <main>
        <h1>{title}</h1>
        <div class="content">
{content}
        </div>
    </main>
    <footer><p>&copy; {year} Gullah Geechee Biz. All rights reserved.</p></footer>
</body>
</html>"""
    html_path.write_text(html)
    
    return {
        "sport": sport['name'],
        "lang": lang,
        "issue": issue,
        "words": words,
        "file": str(filepath),
        "html": str(html_path),
    }

def run_weekly():
    """Generate all 7 sports magazines in English and Spanish."""
    print(f"\n{'='*60}")
    print(f"📰 WEEKLY SPORTS MAGAZINES")
    print(f"   {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"{'='*60}")
    
    results = []
    
    for sport in SPORTS:
        print(f"\n🏐 {sport['name']}")
        
        # English
        en = generate_magazine(sport, "en")
        results.append(en)
        
        # Spanish
        es = generate_magazine(sport, "es")
        results.append(es)
    
    # Summary
    print(f"\n{'='*60}")
    print(f"📊 SUMMARY")
    print(f"{'='*60}")
    total_words = sum(r['words'] for r in results)
    print(f"Magazines: {len(results)} ({len(SPORTS)} sports × 2 languages)")
    print(f"Total words: {total_words:,}")
    print(f"Avg per issue: {total_words // len(results):,} words")
    
    # Save report
    report = LOGS_DIR / f"magazines-{datetime.now().strftime('%Y%m%d')}.json"
    report.write_text(json.dumps(results, indent=2))
    print(f"Report: {report}")
    
    return results

if __name__ == "__main__":
    run_weekly()
