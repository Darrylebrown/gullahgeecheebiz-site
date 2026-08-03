#!/usr/bin/env python3
"""
GGB Gullah Geechee Stories — monthly oral tradition book series.
One book per month, each capturing a different Gullah Geechee story,
folktale, or oral tradition. Full pipeline: English + Spanish + audio + pins + Binyah promo.
"""
import json, os, sys, sqlite3, hashlib, urllib.request, time, re, uuid
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Optional

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
PUB_DB = REPO_ROOT / "publish" / "publisher.db"
LANDING_PAD = REPO_ROOT / "publish" / "landing-pad"
LOGS_DIR = Path(__file__).resolve().parent / "logs"
OUTPUT_DIR = REPO_ROOT / "publish" / "gg-stories"

LOGS_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

AGNES_KEY = os.environ.get("AGNES_API_KEY", "sk-qGBXic9m7VJcJ1vLJ6UPDdJLUbbunIWsNWs4Yl8RqFOfJPCj")
AGNES_URL = "https://apihub.agnes-ai.com/v1/chat/completions"

STORIES_DB = LOGS_DIR / "gg-stories.db"

STORY_THEMES = [
    "Brer Rabbit and the Briar Patch",
    "How the Gullah People Came to the Sea Islands",
    "The Flying Africans",
    "The Hag and the Midnight Ride",
    "The Singing Bones of Sullivan's Island",
    "The Sweetgrass Spirit",
    "The Boy Who Talked to the Gullah",
    "The Cunning Crab and the Rice Field",
    "The Ghost Ship of St. Helena Sound",
    "The Wisdom of the Old Oak",
    "The Basket That Held the Moon",
    "The River That Remembered",
    "The Drum That Called the Ancestors",
    "The Girl Who Outran the Storm",
    "The Turtle and the Hurricane",
    "The Secret of the Marsh",
    "The Firefly Messenger",
    "The Gullah Woman Who Tamed the Wind",
    "The Treasure Beneath the Oak",
    "The Night the Stars Sang Gullah",
    "The Oyster Catcher's Tale",
    "The Root Doctor's Apprentice",
    "The Bridge of Souls",
    "The Song That Freed the Captives",
    "The Keeper of the Gullah Words",
    "The Legend of the Golden Rice",
    "The Crab's Revenge",
    "The Spirit of the Praise House",
    "The Boy Who Rode the Dolphin",
    "The Gullah Midwife's Secret",
    "The Warrior of the Salt Marsh",
    "The Children of the Middle Passage",
    "The Witch of Daufuskie",
    "The Talking Gourd",
    "The Last Gullah Storyteller",
    "The Moon and the Sweetgrass Basket",
]

def init_db():
    conn = sqlite3.connect(str(STORIES_DB))
    conn.execute("""CREATE TABLE IF NOT EXISTS stories (
        id TEXT PRIMARY KEY,
        number INTEGER,
        title TEXT,
        theme TEXT,
        words INTEGER,
        lang TEXT,
        file_path TEXT,
        manifest_id TEXT,
        created_at TEXT
    )""")
    conn.commit()
    return conn

def call_agnes(prompt: str, max_tokens: int = 6000) -> str:
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
    return json.loads(resp.read())["choices"][0]["message"]["content"]

def generate_story(theme: str, story_num: int, lang: str = "en") -> Dict:
    """Generate one Gullah Geechee story book."""
    lang_name = "English" if lang == "en" else "Spanish"
    title = f"Gullah Geechee Stories: {theme}"
    if lang == "es":
        title = f"Historias Gullah Geechee: {theme}"
    
    print(f"  📖 Story #{story_num}: {title} ({lang_name})")
    
    # Generate the story
    prompt = f"""Write a complete Gullah Geechee folktale book in {lang_name} titled '{title}'.

This is Story #{story_num} in the Gullah Geechee Stories series — a monthly collection of oral traditions from the Sea Islands.

Write 2000-2500 words with:
1. Title Page
2. Introduction — setting the scene, where this story comes from
3. The Story — the full folktale with dialogue, description, and cultural detail
4. Story Notes — the meaning, origin, and cultural significance of this tale
5. Glossary — Gullah words used in the story with their meanings

Center Gullah Geechee voices and perspectives. Use authentic Gullah language where appropriate. Make it feel like a story passed down through generations.

Theme: {theme}"""

    content = call_agnes(prompt, max_tokens=6000)
    words = len(content.split())
    
    # Save the manuscript
    lang_suffix = "" if lang == "en" else "-es"
    filename = f"gg-stories-{story_num:03d}{lang_suffix}.md"
    filepath = OUTPUT_DIR / filename
    filepath.write_text(content)
    
    return {
        "title": title,
        "theme": theme,
        "words": words,
        "file": str(filepath),
        "lang": lang,
    }

def register_in_pipeline(title: str, story_num: int, lang: str = "en") -> Optional[str]:
    """Register the story in the publisher pipeline so it gets full treatment."""
    import sys
    sys.path.insert(0, str(REPO_ROOT / "ggb-engine"))
    
    try:
        import publisher
        import importlib
        importlib.reload(publisher)
        
        slug = f"gg-stories-{story_num:03d}"
        pkg_dir = LANDING_PAD / slug
        pkg_dir.mkdir(parents=True, exist_ok=True)
        
        lang_suffix = "" if lang == "en" else "-es"
        src_file = OUTPUT_DIR / f"gg-stories-{story_num:03d}{lang_suffix}.md"
        
        if src_file.exists():
            dest = pkg_dir / f"manuscript{lang_suffix}.md"
            dest.write_text(src_file.read_text())
        
        # Create KDP draft
        price = "3.99" if lang == "en" else "3.99"
        (pkg_dir / "KDP-DRAFT.md").write_text(f"""# KDP Draft — {title}
- **Title:** {title}
- **Author:** Darryl Elliott Brown
- **Publisher:** Gullah Geechee Biz
- **Language:** {"English" if lang == "en" else "Spanish"}
- **Series:** Gullah Geechee Stories (#{story_num})
- **Ebook price:** ${price}
- **DRM:** No
- **KDP Select:** Off
## Description
Story #{story_num} in the Gullah Geechee Stories series. {title} is a traditional folktale from the Sea Islands, passed down through generations of Gullah Geechee storytellers.
## Categories
- FICTION / Fairy Tales, Folk Tales, Legends & Mythology
- SOCIAL SCIENCE / Ethnic Studies / American / African American & Black Studies
- HISTORY / African American & Black
## Keywords
gullah geechee, folktales, oral tradition, sea islands, african american folklore, storytelling
""")
        
        # Run the pipeline to discover and process
        engine = publisher.PublishEngine()
        engine.discover()
        engine.reconcile()
        engine.audit()
        engine.stage()
        engine.preview()
        engine.approve()
        
        # Get the manifest ID
        conn = sqlite3.connect(str(PUB_DB))
        row = conn.execute("""
            SELECT manifest_id FROM manifests 
            WHERE json_extract(data, '$.title.canonical') = ?
            ORDER BY rowid DESC LIMIT 1
        """, (title,)).fetchone()
        conn.close()
        
        if row:
            return row[0]
        
    except Exception as e:
        print(f"     ⚠️  Pipeline registration: {str(e)[:80]}")
    
    return None

def run_monthly():
    """Generate this month's Gullah Geechee Story."""
    now = datetime.now(timezone.utc)
    month = now.month
    year = now.year
    
    # Determine which story theme to use
    story_num = (year - 2026) * 12 + month
    
    conn = init_db()
    
    # Check if this month's story already exists
    existing = conn.execute("SELECT id FROM stories WHERE number = ?", (story_num,)).fetchone()
    if existing:
        print(f"  ⏭️  Story #{story_num} already exists for {month}/{year}")
        conn.close()
        return
    
    # Pick theme
    theme_idx = (story_num - 1) % len(STORY_THEMES)
    theme = STORY_THEMES[theme_idx]
    
    print(f"\n{'='*60}")
    print(f"📖 GULLAH GEECHEE STORIES — Month {story_num}")
    print(f"   {now.strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"   Theme: {theme}")
    print(f"{'='*60}")
    
    # Generate English
    en = generate_story(theme, story_num, "en")
    
    # Generate Spanish
    es = generate_story(theme, story_num, "es")
    
    # Register in pipeline
    print(f"\n  🔄 Registering in pipeline...")
    mid = register_in_pipeline(en["title"], story_num, "en")
    
    # Save to DB
    conn.execute("INSERT OR REPLACE INTO stories VALUES (?,?,?,?,?,?,?,?,?)",
                (f"story-{story_num:03d}", story_num, en["title"], theme, en["words"], "en", en["file"], mid or "",
                 now.isoformat()))
    conn.execute("INSERT OR REPLACE INTO stories VALUES (?,?,?,?,?,?,?,?,?)",
                (f"story-{story_num:03d}-es", story_num, es["title"], theme, es["words"], "es", es["file"], "",
                 now.isoformat()))
    conn.commit()
    
    # Summary
    print(f"\n{'='*60}")
    print(f"📊 SUMMARY")
    print(f"{'='*60}")
    print(f"Story #{story_num}: {en['title']}")
    print(f"English: {en['words']} words")
    print(f"Spanish: {es['words']} words")
    print(f"Total:   {en['words'] + es['words']} words")
    print(f"Manifest: {mid or 'pending'}")
    print(f"\nNext story: Month {story_num + 1}")
    
    conn.close()
    return {"story_num": story_num, "en": en, "es": es, "manifest_id": mid}

if __name__ == "__main__":
    run_monthly()
