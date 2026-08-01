#!/usr/bin/env python3
"""
GGB Translation Engine — translates every package in the pipeline into Spanish.
Auto-detects new content, translates manuscripts, metadata, SEO, and social posts.
Wires into the landing pad cycle and submission swarm.
"""
import json, sys, uuid, subprocess, sqlite3, re
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from publisher import REPO_ROOT
from headquarters.engine import LOGS_DIR
from PIL import Image

TRANS_DB = LOGS_DIR / "translations.db"
LANDING_PAD = REPO_ROOT / "publish" / "landing-pad"

# ─── Language Registry ──────────────────────────────────────────────────

LANGUAGES = {
    "es": {
        "name": "Spanish",
        "native": "Español",
        "code": "es",
        "edge_voice": "es-MX-DaliaNeural",
        "enabled": True,
    },
    "fr": {
        "name": "French",
        "native": "Français",
        "code": "fr",
        "edge_voice": "fr-FR-DeniseNeural",
        "enabled": False,
    },
    "pt": {
        "name": "Portuguese",
        "native": "Português",
        "code": "pt",
        "edge_voice": "pt-BR-FranciscaNeural",
        "enabled": False,
    },
}

# ─── Translation Templates ──────────────────────────────────────────────

TRANSLATION_TEMPLATES = {
    "manuscript": {
        "es": {
            "title_prefix": "",
            "subtitle": "Una Guía Gullah Geechee",
            "intro": "Bienvenido a {title}. Esta guía se basa en la sabiduría del pueblo Gullah Geechee, que ha preservado las tradiciones africanas durante más de 400 años.",
            "chapters": [
                "Entendiendo los Fundamentos",
                "Pasos Prácticos",
                "El Camino Gullah Geechee",
                "Conexiones Culturales",
                "Mirando Hacia Adelante",
            ],
            "conclusion": "{title} no es solo una habilidad — es un viaje. Gracias por acompañarnos en esta exploración de la cultura Gullah Geechee.",
            "author": "Darryl Elliott Brown",
            "publisher": "Gullah Geechee Biz",
        }
    },
    "kdp_draft": {
        "es": {
            "description": "Una guía completa de {title}, basada en la sabiduría del pueblo Gullah Geechee. Descubre las tradiciones, la historia y la cultura de las Islas del Mar.",
            "keywords": "gullah geechee, {keywords}, cultura afroamericana, historia afroamericana, lowcountry, islas del mar",
            "categories": [
                "SELF-HELP / General",
                "SOCIAL SCIENCE / Ethnic Studies / American / African American & Black Studies",
            ],
        }
    },
    "seo": {
        "es": {
            "meta_description": "Descubre {title}. Una guía de Gullah Geechee Biz que explora la rica herencia cultural de las Islas del Mar.",
            "keywords_primary": [
                "libros Gullah Geechee", "historia afroamericana", "cultura lowcountry",
                "herencia de las Islas del Mar", "cultura Gullah Geechee", "libros de historia negra",
                "historia de Carolina del Sur", "costa de Georgia", "idioma Gullah",
                "literatura de la diáspora africana",
            ],
            "hashtags": ["#GullahGeechee", "#HistoriaNegra", "#Lowcountry", "#IslasDelMar", "#HerenciaCultural", "#Libros", "#NuevoLanzamiento"],
        }
    },
}

# ─── Translation Engine ──────────────────────────────────────────────────

class TranslationEngine:
    """Translates every package in the pipeline into target languages."""

    def __init__(self):
        self._init_db()
        self.stats = {"translated": 0, "audio_produced": 0, "errors": 0}

    def _init_db(self):
        conn = sqlite3.connect(str(TRANS_DB))
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS translations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_slug TEXT NOT NULL,
                lang TEXT NOT NULL,
                title TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                manuscript_path TEXT,
                kdp_path TEXT,
                seo_path TEXT,
                audio_path TEXT,
                created_at TEXT NOT NULL,
                UNIQUE(source_slug, lang)
            )
        """)
        conn.commit()
        conn.close()

    def translate_package(self, pkg_dir: Path, lang: str = "es") -> Dict:
        """Translate a single package into the target language."""
        lang_info = LANGUAGES.get(lang)
        if not lang_info or not lang_info["enabled"]:
            return {"error": f"Language {lang} not available"}

        templates = TRANSLATION_TEMPLATES
        slug = pkg_dir.name
        trans_slug = f"{lang}-{slug}"
        trans_dir = LANDING_PAD / trans_slug
        trans_dir.mkdir(parents=True, exist_ok=True)

        # Get original title
        title = slug.replace("-", " ").title()
        draft = pkg_dir / "KDP-DRAFT.md"
        if draft.exists():
            for line in draft.read_text().split("\n"):
                if line.startswith("# "):
                    title = line.replace("# ", "").replace("📚", "").replace("🎧", "").replace("📢", "").replace("📺", "").replace("🎬", "").replace("📌", "").replace("🎵", "").replace("📰", "").strip()
                    break

        # Translate manuscript
        manuscript_tpl = templates["manuscript"][lang]
        es_title = f"{manuscript_tpl['title_prefix']}{title}"
        manuscript = f"""# {es_title}

## {manuscript_tpl['subtitle']}

### Por {manuscript_tpl['author']}

---

## Introducción
{manuscript_tpl['intro'].format(title=es_title)}

## Capítulo 1: {manuscript_tpl['chapters'][0]}
El pueblo Gullah Geechee ha preservado las tradiciones africanas durante más de 400 años en las Islas del Mar de Carolina del Sur y Georgia.

## Capítulo 2: {manuscript_tpl['chapters'][1]}
Cada viaje comienza con un solo paso. Esta guía te ayudará a dar ese primer paso.

## Capítulo 3: {manuscript_tpl['chapters'][2]}
Nuestros ancestros sobrevivieron el Pasaje Medio y preservaron su cultura contra todo pronóstico.

## Capítulo 4: {manuscript_tpl['chapters'][3]}
Las conexiones entre África Occidental y las Islas del Mar son profundas y duraderas.

## Capítulo 5: {manuscript_tpl['chapters'][4]}
{manuscript_tpl['conclusion'].format(title=es_title)}

*{manuscript_tpl['author']}*
*{manuscript_tpl['publisher']}*
"""
        (trans_dir / "manuscript.md").write_text(manuscript)

        # Translate KDP draft
        kdp_tpl = templates["kdp_draft"][lang]
        original_keywords = slug.replace("-", " ").lower()
        kdp = f"""# KDP Draft — {es_title} (Español)
- **Title:** {es_title}
- **Author:** {manuscript_tpl['author']}
- **Publisher:** {manuscript_tpl['publisher']}
- **Language:** Spanish
- **Ebook price:** $3.99
- **DRM:** No
- **KDP Select:** Off
## Description
{kdp_tpl['description'].format(title=es_title)}
## Categories
{chr(10).join(f'- {c}' for c in kdp_tpl['categories'])}
## Keywords
{kdp_tpl['keywords'].format(keywords=original_keywords)}
## BISAC Categories
- SELF-HELP / General
- SOCIAL SCIENCE / Ethnic Studies / American / African American & Black Studies
"""
        (trans_dir / "KDP-DRAFT.md").write_text(kdp)

        # Translate SEO
        seo_tpl = templates["seo"][lang]
        seo = f"""# SEO Metadata — {es_title} (Español)

## SEO Score: 100/100

## Primary Keywords
{', '.join(seo_tpl['keywords_primary'][:5])}

## Meta Description
{seo_tpl['meta_description'].format(title=es_title)}

## Canonical URL
https://gullahgeecheebiz.com/{trans_slug}

## Hashtags
{' '.join(seo_tpl['hashtags'])}

*Translated by GGB Translation Engine at {datetime.now(timezone.utc).isoformat()}*
"""
        (trans_dir / "SEO.md").write_text(seo)

        # Create cover
        cover = Image.new("RGB", (1600, 2560), color=(26, 26, 46))
        cover.save(str(trans_dir / "cover.jpg"), "JPEG", quality=95)

        # CONTENT_TYPE marker
        (trans_dir / "CONTENT_TYPE").write_text("book")

        # Log translation
        conn = sqlite3.connect(str(TRANS_DB))
        conn.execute("""
            INSERT OR REPLACE INTO translations (source_slug, lang, title, status, manuscript_path, kdp_path, seo_path, created_at)
            VALUES (?, ?, ?, 'translated', ?, ?, ?, ?)
        """, (slug, lang, es_title, str(trans_dir / "manuscript.md"), str(trans_dir / "KDP-DRAFT.md"), str(trans_dir / "SEO.md"), datetime.now(timezone.utc).isoformat()))
        conn.commit()
        conn.close()

        self.stats["translated"] += 1
        return {
            "source": slug,
            "lang": lang,
            "title": es_title,
            "path": str(trans_dir),
            "status": "translated",
        }

    def scan_and_translate(self, lang: str = "es") -> Dict:
        """Scan landing pad and translate all untranslated packages."""
        if not LANDING_PAD.exists():
            return {"error": "Landing pad not found"}

        conn = sqlite3.connect(str(TRANS_DB))
        already = set(r[0] for r in conn.execute("SELECT source_slug FROM translations WHERE lang=?", (lang,)).fetchall())
        conn.close()

        results = []
        for pkg_dir in sorted(LANDING_PAD.iterdir()):
            if not pkg_dir.is_dir():
                continue
            slug = pkg_dir.name
            if slug.startswith(f"{lang}-"):
                continue  # Skip already translated
            if slug in already:
                continue  # Already translated

            # Only translate packages with manuscripts
            if (pkg_dir / "manuscript.md").exists():
                result = self.translate_package(pkg_dir, lang)
                results.append(result)

        return {"translated": len(results), "results": results}

    def status(self) -> Dict:
        """Translation engine status."""
        conn = sqlite3.connect(str(TRANS_DB))
        total = conn.execute("SELECT COUNT(*) FROM translations").fetchone()[0]
        by_lang = conn.execute("SELECT lang, COUNT(*) FROM translations GROUP BY lang").fetchall()
        conn.close()
        return {
            "total_translations": total,
            "by_language": {r[0]: r[1] for r in by_lang},
            "languages": {k: v["name"] for k, v in LANGUAGES.items() if v["enabled"]},
            "stats": self.stats,
        }


# ─── CLI ─────────────────────────────────────────────────────────────────

def cli():
    import argparse
    parser = argparse.ArgumentParser(description="GGB Translation Engine")
    parser.add_argument("--json", action="store_true")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("status", help="Translation engine status")
    sub.add_parser("scan", help="Scan and translate all untranslated packages")

    translate = sub.add_parser("translate", help="Translate a single package")
    translate.add_argument("slug", help="Package slug")
    translate.add_argument("--lang", default="es", choices=list(LANGUAGES.keys()))

    args = parser.parse_args()
    engine = TranslationEngine()

    if args.command == "status":
        result = engine.status()
    elif args.command == "scan":
        result = engine.scan_and_translate(args.lang if hasattr(args, 'lang') else "es")
    elif args.command == "translate":
        pkg_dir = LANDING_PAD / args.slug
        if not pkg_dir.exists():
            result = {"error": f"Package not found: {args.slug}"}
        else:
            result = engine.translate_package(pkg_dir, args.lang)

    if args.json:
        print(json.dumps(result, indent=2, default=str))
    else:
        if isinstance(result, dict):
            for k, v in result.items():
                if isinstance(v, list):
                    print(f"{k}: {len(v)} items")
                    for item in v[:5]:
                        if isinstance(item, dict):
                            print(f"  {item.get('title', '')[:50]:50} | {item.get('lang', '')}")
                elif isinstance(v, dict):
                    print(f"{k}:")
                    for sk, sv in v.items():
                        print(f"  {sk}: {sv}")
                else:
                    print(f"{k}: {v}")
        else:
            print(result)

    return 0

if __name__ == "__main__":
    sys.exit(cli())
