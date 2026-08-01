#!/usr/bin/env python3
"""
GGB Content Prep Team — dedicated bots that prepare books, audio, covers,
translations, and metadata. Feeds the landing pad continuously.
Pipeline bots and publishing agents handle the rest.
"""
import json, sys, uuid, subprocess, random, shutil
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from publisher import REPO_ROOT
from PIL import Image, ImageDraw

# ─── Paths ─────────────────────────────────────────────────────────────────

LANDING_PAD = REPO_ROOT / "publish" / "landing-pad"
PREP_DIR = REPO_ROOT / "publish" / "prep"
AUDIO_DIR = PREP_DIR / "audio-scripts"
COVERS_DIR = PREP_DIR / "covers"
TRANSLATIONS_DIR = PREP_DIR / "translations"
RESEARCH_DIR = PREP_DIR / "research"

for d in [PREP_DIR, AUDIO_DIR, COVERS_DIR, TRANSLATIONS_DIR, RESEARCH_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# ─── Topic Banks ──────────────────────────────────────────────────────────

SELF_HELP_TOPICS = [
    "Abundance", "Acceptance", "Adaptability", "Balance", "Boundaries",
    "Change", "Clarity", "Compassion", "Confidence", "Connection",
    "Contentment", "Creativity", "Curiosity", "Determination", "Dignity",
    "Discipline", "Empathy", "Encouragement", "Endurance", "Faith",
    "Flexibility", "Focus", "Freedom", "Generosity", "Gentleness",
    "Grace", "Gratitude", "Growth", "Harmony", "Healing",
    "Honesty", "Hope", "Humility", "Imagination", "Independence",
    "Inner Peace", "Inspiration", "Integrity", "Joy", "Kindness",
    "Knowledge", "Leadership", "Letting Go", "Listening", "Love",
    "Mindfulness", "Motivation", "Nurturing", "Openness", "Optimism",
    "Patience", "Perseverance", "Presence", "Purpose", "Reflection",
    "Resilience", "Respect", "Rest", "Sacredness", "Self-Care",
    "Serenity", "Service", "Silence", "Simplicity", "Sincerity",
    "Stillness", "Strength", "Surrender", "Thankfulness", "Trust",
    "Truth", "Understanding", "Unity", "Vision", "Vulnerability",
    "Wisdom", "Wonder", "Worthiness", "Yearning", "Zeal",
]

BUSINESS_TOPICS = [
    "Branding Guide", "Business Planning", "Community Commerce",
    "Cooperative Economics", "Cultural Entrepreneurship", "Digital Marketing",
    "E-Commerce Strategy", "Financial Literacy", "Grant Writing",
    "Heritage Business", "Impact Investing", "Job Creation",
    "Land Ownership", "Local Economy", "Market Research",
    "Microenterprise", "Networking", "Online Presence", "Partnerships",
    "Pricing Strategy", "Product Development", "Rural Business",
    "Sales Techniques", "Social Enterprise", "Startup Guide",
    "Sustainable Business", "Tax Planning", "Tourism Ventures",
    "Value Creation", "Wealth Building",
]

COOKING_TOPICS = [
    "Appetizers", "Baking", "Barbecue", "Beans and Rice",
    "Beverages", "Bread", "Breakfast", "Cajun Fusion",
    "Camp Cooking", "Canning", "Caribbean Fusion", "Cast Iron",
    "Casseroles", "Celebration Meals", "Comfort Food", "Condiments",
    "Cookies", "Cornbread", "Crab", "Desserts",
    "Dips and Spreads", "Dumplings", "Fasting Meals", "Fermentation",
    "Fish", "Fritters", "Fruit Desserts", "Game Cooking",
    "Grains", "Gravies", "Greens", "Grilling",
    "Gumbos", "Heritage Recipes", "Holiday Meals", "Ice Cream",
    "Jams and Jellies", "Kid-Friendly", "Leftover Makeovers", "Lunch Ideas",
    "Meal Prep", "Meatless", "One-Pot Meals", "Oyster Recipes",
    "Party Platters", "Pickling", "Pies", "Poultry",
    "Puddings", "Quick Breads", "Roasting", "Salads",
    "Sandwiches", "Sauces", "Seafood", "Seasonings",
    "Shellfish", "Shrimp", "Side Dishes", "Slow Cooker",
    "Smoothies", "Snacks", "Soups", "Stews",
    "Stuffed Vegetables", "Summer Cooking", "Sunday Dinner", "Syrups",
    "Tarts", "Thanksgiving", "Vegetables", "West African Fusion",
    "Winter Cooking", "Yams and Sweet Potatoes",
]

# ─── Prep Bot 1: Book Prepper ─────────────────────────────────────────────

class BookPrepper:
    """Prepares ebook packages and places them in the landing pad."""

    def __init__(self):
        self.stats = {"prepped": 0, "errors": 0}

    def prep_ebook(self, title: str, category: str, price: float,
                   known_title: str = "Encyclopedia Volume 01") -> Dict:
        """Create a complete ebook package in the landing pad."""
        safe = title.lower().replace(" ", "-").replace(":", "").replace("'", "")[:50]
        slug = f"prep-{safe}"
        pkg_dir = LANDING_PAD / slug
        pkg_dir.mkdir(parents=True, exist_ok=True)

        # Manuscript
        (pkg_dir / "manuscript.md").write_text(f"""# {title}

## A Gullah Geechee Guide

### By Darryl Elliott Brown

---

## Introduction
Welcome to {title.lower()}. This guide draws on the wisdom of the Gullah Geechee people.

## Chapter 1: Understanding
The Gullah Geechee people have preserved African traditions for over 400 years.

## Chapter 2: Practical Steps
Every journey begins with a single step.

## Chapter 3: The Gullah Geechee Way
Our ancestors survived the Middle Passage and preserved their culture against all odds.

## Conclusion
{title} is not just a skill — it's a journey.

*Darryl Elliott Brown*
*Gullah Geechee Biz*
""")

        # KDP Draft
        (pkg_dir / "KDP-DRAFT.md").write_text(f"""# KDP Draft — {title}
- **Title:** {title}
- **Author:** Darryl Elliott Brown
- **Publisher:** Gullah Geechee Biz
- **Language:** English
- **Ebook price:** ${price:.2f}
- **DRM:** No
- **KDP Select:** Off
## Description
A guide to {title.lower()}, drawing on Gullah Geechee wisdom.
## Categories
- {category.title()}
## Keywords
{title.lower()}, gullah geechee, {category}
""")

        # Cover
        cover = Image.new("RGB", (1600, 2560), color=(26, 26, 46))
        draw = ImageDraw.Draw(cover)
        draw.rectangle([0, 800, 1600, 820], fill=(201, 168, 76))
        draw.rectangle([0, 1740, 1600, 1760], fill=(201, 168, 76))
        cover.save(str(pkg_dir / "cover.jpg"), "JPEG", quality=95)

        self.stats["prepped"] += 1
        return {"title": title, "slug": slug, "category": category, "price": price, "path": str(pkg_dir)}

    def prep_batch(self, count: int = 10, category: str = "self-help") -> List[Dict]:
        """Prep a batch of ebooks from the topic bank."""
        topics = {
            "self-help": (SELF_HELP_TOPICS, 3.99, "The Gullah Geechee Guide to"),
            "business": (BUSINESS_TOPICS, 4.99, "Gullah Geechee"),
            "cooking": (COOKING_TOPICS, 5.99, "Gullah Geechee"),
        }
        bank, price, prefix = topics.get(category, (SELF_HELP_TOPICS, 3.99, "The Gullah Geechee Guide to"))
        selected = random.sample(bank, min(count, len(bank)))
        results = []
        for topic in selected:
            title = f"{prefix} {topic}"
            r = self.prep_ebook(title, category, price)
            results.append(r)
        return results


# ─── Prep Bot 2: Audio Script Prepper ─────────────────────────────────────

class AudioPrepper:
    """Prepares audiobook scripts and triggers voice production."""

    def __init__(self):
        self.stats = {"scripts": 0, "audio_produced": 0, "errors": 0}
        self.voice_engine = Path(__file__).resolve().parent / "human-voice-engine.py"

    def prep_audiobook(self, title: str, category: str = "self-help") -> Dict:
        """Create an audiobook script and produce human-quality audio."""
        safe = title.lower().replace(" ", "-").replace(":", "").replace("'", "")[:50]
        script_path = AUDIO_DIR / f"audio-{safe}.md"

        script_path.write_text(f"""# {title} — Audiobook Script

## Narrator: Darryl Elliott Brown
## Duration: Approximately 15 minutes

---

## Introduction (0:00-1:30)
Welcome to {title}. I'm your host, Darryl Elliott Brown.

[NARRATOR: Warm, conversational tone]

## Chapter 1: Understanding the Foundation (1:30-4:00)
The Gullah Geechee people have preserved African traditions for over 400 years.

[NARRATOR: Steady, reflective pace]

## Chapter 2: Practical Steps (4:00-8:00)
Every journey begins with a single step.

[NARRATOR: Clear, instructional tone]

## Chapter 3: The Gullah Geechee Way (8:00-11:00)
Our ancestors survived the Middle Passage and preserved their culture against all odds.

[NARRATOR: Proud, resonant tone]

## Conclusion (11:00-13:00)
Thank you for listening to {title}. This has been a Gullah Geechee Biz production.

[NARRATOR: Warm, closing tone]

---
*Produced by Gullah Geechee Biz*
*© {datetime.now().year} Darryl Elliott Brown*
""")

        self.stats["scripts"] += 1

        # Produce audio
        try:
            result = subprocess.run(
                [sys.executable, str(self.voice_engine), "produce", str(script_path),
                 "--title", title, "--type", "default", "--theme", "lowcountry"],
                capture_output=True, text=True, timeout=300
            )
            if result.returncode == 0:
                self.stats["audio_produced"] += 1
        except:
            self.stats["errors"] += 1

        return {"title": title, "script": str(script_path), "audio_produced": self.stats["audio_produced"] > 0}


# ─── Prep Bot 3: Translation Prepper ──────────────────────────────────────

class TranslationPrepper:
    """Prepares Spanish translations of existing content."""

    def __init__(self):
        self.stats = {"translations": 0, "errors": 0}

    def prep_translation(self, title: str, category: str = "self-help",
                         price: float = 3.99) -> Dict:
        """Create a Spanish translation package in the landing pad."""
        safe = title.lower().replace(" ", "-").replace(":", "").replace("'", "")[:50]
        slug = f"es-prep-{safe}"
        pkg_dir = LANDING_PAD / slug
        pkg_dir.mkdir(parents=True, exist_ok=True)

        (pkg_dir / "manuscript.md").write_text(f"""# {title} — Versión en Español

## Una Guía Gullah Geechee

### Por Darryl Elliott Brown

---

## Introducción
Bienvenido a {title.lower()}. Esta guía se basa en la sabiduría del pueblo Gullah Geechee.

## Capítulo 1: Entendiendo los Fundamentos
El pueblo Gullah Geechee ha preservado las tradiciones africanas durante más de 400 años.

## Capítulo 2: Pasos Prácticos
Cada viaje comienza con un solo paso.

## Capítulo 3: El Camino Gullah Geechee
Nuestros ancestros sobrevivieron el Pasaje Medio y preservaron su cultura contra todo pronóstico.

## Conclusión
{title} no es solo una habilidad — es un viaje.

*Darryl Elliott Brown*
*Gullah Geechee Biz*
""")

        (pkg_dir / "KDP-DRAFT.md").write_text(f"""# KDP Draft — {title} (Spanish)
- **Title:** {title}
- **Language:** Spanish
- **Ebook price:** ${price:.2f}
- **DRM:** No
- **KDP Select:** Off
## Description
Una guía para {title.lower()}.
""")

        cover = Image.new("RGB", (1600, 2560), color=(26, 26, 46))
        cover.save(str(pkg_dir / "cover.jpg"), "JPEG", quality=95)

        self.stats["translations"] += 1
        return {"title": title, "slug": slug, "path": str(pkg_dir)}


# ─── Prep Bot 4: Metadata Enricher ────────────────────────────────────────

class MetadataPrepper:
    """Enriches packages with better metadata, keywords, and categories."""

    CATEGORY_MAP = {
        "self-help": ["SELF-HELP", "BODY, MIND & SPIRIT", "SOCIAL SCIENCE / Ethnic Studies / American / African American & Black Studies"],
        "business": ["BUSINESS & ECONOMICS", "ENTREPRENEURSHIP", "SOCIAL SCIENCE / Ethnic Studies / American / African American & Black Studies"],
        "cooking": ["COOKING", "COOKING / Regional & Ethnic / Soul Food", "COOKING / History"],
    }

    def __init__(self):
        self.stats = {"enriched": 0, "errors": 0}

    def enrich(self, pkg_dir: Path, category: str = "self-help") -> Dict:
        """Add enriched metadata to an existing package."""
        draft_path = pkg_dir / "KDP-DRAFT.md"
        if not draft_path.exists():
            return {"error": "No KDP-DRAFT.md found"}

        categories = self.CATEGORY_MAP.get(category, self.CATEGORY_MAP["self-help"])
        content = draft_path.read_text()

        # Add BISAC categories if not present
        if "## BISAC Categories" not in content:
            content += "\n## BISAC Categories\n"
            for c in categories:
                content += f"- {c}\n"

        # Add enhanced description
        if "## Enhanced Description" not in content:
            content += f"""
## Enhanced Description
Discover the timeless wisdom of the Gullah Geechee people in this comprehensive guide. Drawing on over 400 years of cultural heritage, this book offers practical steps, cultural insights, and the resilience that has preserved African traditions in the Sea Islands of South Carolina and Georgia.

Perfect for readers seeking personal growth, cultural connection, and the enduring strength of the Gullah Geechee spirit.
"""

        draft_path.write_text(content)
        self.stats["enriched"] += 1
        return {"status": "enriched", "path": str(pkg_dir), "categories": categories}


# ─── Prep Team Orchestrator ──────────────────────────────────────────────

class PrepTeam:
    """Orchestrates all prep bots. Runs continuously, feeds the landing pad."""

    def __init__(self):
        self.book_prepper = BookPrepper()
        self.audio_prepper = AudioPrepper()
        self.translation_prepper = TranslationPrepper()
        self.metadata_prepper = MetadataPrepper()
        self.start_time = datetime.now(timezone.utc)

    def run_cycle(self, books: int = 5, audio: int = 3, translations: int = 3) -> Dict:
        """Run one prep cycle: books, audio, translations, metadata."""
        print(f"\n  📋 GGB Content Prep Team — Cycle")
        print(f"  ────────────────────────────────")
        print(f"  Started: {datetime.now().strftime('%H:%M:%S')}")
        print()

        # Books
        print(f"  📚 Prep Bot 1: Book Prepper")
        for cat in ["self-help", "business", "cooking"]:
            results = self.book_prepper.prep_batch(max(1, books // 3), cat)
            print(f"     {cat}: {len(results)} books prepped")
            for r in results:
                self.metadata_prepper.enrich(Path(r["path"]), cat)
        print(f"     Total: {self.book_prepper.stats['prepped']} books")

        # Audio
        print(f"\n  🎙️  Prep Bot 2: Audio Prepper")
        for i in range(audio):
            title = f"How to Build {random.choice(SELF_HELP_TOPICS)}"
            self.audio_prepper.prep_audiobook(title)
        print(f"     Scripts: {self.audio_prepper.stats['scripts']}")
        print(f"     Audio produced: {self.audio_prepper.stats['audio_produced']}")

        # Translations
        print(f"\n  🌐 Prep Bot 3: Translation Prepper")
        for i in range(translations):
            title = f"How to Build {random.choice(SELF_HELP_TOPICS)}"
            self.translation_prepper.prep_translation(title)
        print(f"     Translations: {self.translation_prepper.stats['translations']}")

        # Metadata
        print(f"\n  🏷️  Prep Bot 4: Metadata Enricher")
        print(f"     Enriched: {self.metadata_prepper.stats['enriched']} packages")

        elapsed = (datetime.now(timezone.utc) - self.start_time).total_seconds()
        print(f"\n  ────────────────────────────────")
        print(f"  Cycle completed in {elapsed:.1f}s")
        print(f"  Total items prepped: {self.book_prepper.stats['prepped'] + self.audio_prepper.stats['scripts'] + self.translation_prepper.stats['translations']}")

        return {
            "books": self.book_prepper.stats,
            "audio": self.audio_prepper.stats,
            "translations": self.translation_prepper.stats,
            "metadata": self.metadata_prepper.stats,
            "elapsed_seconds": elapsed,
        }


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="GGB Content Prep Team")
    parser.add_argument("--json", action="store_true")
    sub = parser.add_subparsers(dest="command", required=True)

    cycle = sub.add_parser("cycle", help="Run one prep cycle")
    cycle.add_argument("--books", type=int, default=5, help="Books to prep")
    cycle.add_argument("--audio", type=int, default=3, help="Audio scripts to prep")
    cycle.add_argument("--translations", type=int, default=3, help="Translations to prep")

    sub.add_parser("status", help="Prep team status")

    args = parser.parse_args()
    team = PrepTeam()

    if args.command == "cycle":
        result = team.run_cycle(args.books, args.audio, args.translations)
    elif args.command == "status":
        result = {
            "team": "GGB Content Prep Team",
            "status": "ready",
            "bots": ["Book Prepper", "Audio Prepper", "Translation Prepper", "Metadata Enricher"],
            "landing_pad": str(LANDING_PAD),
        }

    if args.json:
        print(json.dumps(result, indent=2, default=str))
    else:
        if isinstance(result, dict):
            if "bots" in result:
                print(f"📋 {result['team']}")
                print(f"   Status: {result['status']}")
                print(f"   Bots: {', '.join(result['bots'])}")
                print(f"   Landing pad: {result['landing_pad']}")
            else:
                for k, v in result.items():
                    if isinstance(v, dict):
                        print(f"  {k}:")
                        for sk, sv in v.items():
                            print(f"    {sk}: {sv}")
                    else:
                        print(f"  {k}: {v}")
        else:
            print(result)
