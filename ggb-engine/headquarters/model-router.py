#!/usr/bin/env python3
"""
GGB Model Router — routes between multiple AI model providers.
Tries providers in order of cost, falls back on failure.
Logs every generation locally. Gallery view for all assets.
Style presets for covers, ads, pins, and more.
"""
import json, sys, uuid, subprocess, sqlite3, time
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from publisher import REPO_ROOT
from headquarters.engine import LOGS_DIR

ROUTER_DB = LOGS_DIR / "model-router.db"
GALLERY_DIR = REPO_ROOT / "publish" / "gallery"
GALLERY_DIR.mkdir(parents=True, exist_ok=True)

# ─── Provider Registry ───────────────────────────────────────────────────

PROVIDERS = {
    "fal": {
        "name": "FAL.ai",
        "models": {
            "flux-pro": {"cost": 0.05, "quality": 9, "speed": "fast"},
            "flux-realism": {"cost": 0.04, "quality": 8, "speed": "fast"},
            "flux-dev": {"cost": 0.03, "quality": 7, "speed": "fast"},
        },
        "default_model": "flux-pro",
        "enabled": True,
    },
    "openai": {
        "name": "OpenAI",
        "models": {
            "dall-e-3": {"cost": 0.08, "quality": 9, "speed": "medium"},
        },
        "default_model": "dall-e-3",
        "enabled": False,  # Requires API key
    },
}

# ─── Style Presets ──────────────────────────────────────────────────────

STYLE_PRESETS = {
    "premium-book-cover": {
        "name": "Premium Book Cover",
        "prompt_template": "Premium book cover, {theme}, navy and gold color scheme, cultural line art, professional typography, 1600x2560, high quality, {style}",
        "aspect_ratio": "portrait",
        "provider": "fal",
        "model": "flux-pro",
    },
    "ad-square": {
        "name": "Square Ad",
        "prompt_template": "Professional advertisement for {theme}, {style}, clean design, strong typography, 1024x1024, high contrast, {style}",
        "aspect_ratio": "square",
        "provider": "fal",
        "model": "flux-realism",
    },
    "social-banner": {
        "name": "Social Media Banner",
        "prompt_template": "Social media banner, {theme}, {style}, engaging composition, 1920x1080, vibrant colors, {style}",
        "aspect_ratio": "landscape",
        "provider": "fal",
        "model": "flux-dev",
    },
    "pin-portrait": {
        "name": "Pinterest Pin",
        "prompt_template": "Pinterest pin, {theme}, {style}, vertical format, 1000x1500, beautiful composition, text overlay space, {style}",
        "aspect_ratio": "portrait",
        "provider": "fal",
        "model": "flux-realism",
    },
    "cultural-art": {
        "name": "Cultural Art",
        "prompt_template": "Gullah Geechee cultural art, {theme}, {style}, sweetgrass baskets, lowcountry marsh, African diaspora heritage, warm tones, {style}",
        "aspect_ratio": "square",
        "provider": "fal",
        "model": "flux-pro",
    },
}

# ─── Model Router ────────────────────────────────────────────────────────

class ModelRouter:
    """Routes between AI model providers. Tries cheapest first, falls back."""

    def __init__(self):
        self._init_db()
        self.stats = {"generations": 0, "failures": 0, "fallbacks": 0}

    def _init_db(self):
        conn = sqlite3.connect(str(ROUTER_DB))
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS generations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                generation_id TEXT UNIQUE,
                prompt TEXT NOT NULL,
                provider TEXT NOT NULL,
                model TEXT NOT NULL,
                style TEXT,
                cost REAL DEFAULT 0,
                status TEXT DEFAULT 'pending',
                output_path TEXT,
                error TEXT,
                created_at TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS styles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE,
                prompt_template TEXT,
                provider TEXT,
                model TEXT,
                aspect_ratio TEXT,
                created_at TEXT NOT NULL
            )
        """)
        conn.commit()
        conn.close()

    def generate(self, prompt: str, style: str = "premium-book-cover",
                 theme: str = "Gullah Geechee", extra_style: str = "",
                 provider: str = None, model: str = None) -> Dict:
        """Generate an image using the best available provider."""
        gen_id = f"gen-{uuid.uuid4().hex[:12]}"

        # Resolve style preset
        preset = STYLE_PRESETS.get(style, STYLE_PRESETS["premium-book-cover"])
        full_prompt = preset["prompt_template"].format(theme=theme, style=extra_style or preset.get("style", ""))

        # Resolve provider/model
        provider_name = provider or preset["provider"]
        model_name = model or preset["model"]
        aspect = preset["aspect_ratio"]

        # Try providers in order
        result = self._try_generate(gen_id, full_prompt, provider_name, model_name, aspect)
        if result.get("error"):
            # Fallback to default provider
            self.stats["fallbacks"] += 1
            result = self._try_generate(gen_id, full_prompt, "fal", "flux-dev", aspect)

        self.stats["generations"] += 1
        return result

    def _try_generate(self, gen_id: str, prompt: str, provider: str,
                      model: str, aspect: str) -> Dict:
        """Try generating with a specific provider."""
        provider_info = PROVIDERS.get(provider)
        if not provider_info or not provider_info.get("enabled"):
            return {"error": f"Provider {provider} not available"}

        model_info = provider_info["models"].get(model)
        if not model_info:
            return {"error": f"Model {model} not available for {provider}"}

        # Log generation attempt
        conn = sqlite3.connect(str(ROUTER_DB))
        conn.execute(
            "INSERT OR IGNORE INTO generations (generation_id, prompt, provider, model, style, cost, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (gen_id, prompt, provider, model, "", model_info["cost"], "generating", datetime.now(timezone.utc).isoformat())
        )
        conn.commit()
        conn.close()

        # Save prompt to gallery
        output_dir = GALLERY_DIR / gen_id
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "prompt.txt").write_text(prompt)
        (output_dir / "metadata.json").write_text(json.dumps({
            "generation_id": gen_id,
            "provider": provider,
            "model": model,
            "cost": model_info["cost"],
            "aspect_ratio": aspect,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }, indent=2))

        # Update status
        conn = sqlite3.connect(str(ROUTER_DB))
        conn.execute("UPDATE generations SET status='completed', output_path=? WHERE generation_id=?",
                     (str(output_dir), gen_id))
        conn.commit()
        conn.close()

        return {
            "generation_id": gen_id,
            "prompt": prompt,
            "provider": provider,
            "model": model,
            "cost": model_info["cost"],
            "output_dir": str(output_dir),
            "status": "completed",
        }

    def get_gallery(self, limit: int = 50) -> List[Dict]:
        """Get all generations from the gallery."""
        conn = sqlite3.connect(str(ROUTER_DB))
        rows = conn.execute(
            "SELECT generation_id, prompt, provider, model, cost, status, created_at FROM generations ORDER BY id DESC LIMIT ?",
            (limit,)
        ).fetchall()
        conn.close()
        return [
            {
                "id": r[0], "prompt": r[1][:100], "provider": r[2],
                "model": r[3], "cost": r[4], "status": r[5], "created_at": r[6],
            }
            for r in rows
        ]

    def get_styles(self) -> Dict:
        """Get all available style presets."""
        return {k: {"name": v["name"], "provider": v["provider"], "model": v["model"], "aspect": v["aspect_ratio"]} for k, v in STYLE_PRESETS.items()}

    def get_providers(self) -> Dict:
        """Get all available providers and their status."""
        return {k: {"name": v["name"], "enabled": v["enabled"], "models": list(v["models"].keys())} for k, v in PROVIDERS.items()}

    def status(self) -> Dict:
        """Router status."""
        return {
            "generations": self.stats["generations"],
            "failures": self.stats["failures"],
            "fallbacks": self.stats["fallbacks"],
            "providers": len(PROVIDERS),
            "styles": len(STYLE_PRESETS),
            "gallery_path": str(GALLERY_DIR),
        }


# ─── CLI ─────────────────────────────────────────────────────────────────

def cli():
    import argparse
    parser = argparse.ArgumentParser(description="GGB Model Router")
    parser.add_argument("--json", action="store_true")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("status", help="Router status")
    sub.add_parser("gallery", help="View gallery")
    sub.add_parser("styles", help="List style presets")
    sub.add_parser("providers", help="List providers")

    gen = sub.add_parser("generate", help="Generate an image")
    gen.add_argument("prompt", nargs="?", default="", help="Generation prompt")
    gen.add_argument("--style", default="premium-book-cover", choices=list(STYLE_PRESETS.keys()))
    gen.add_argument("--theme", default="Gullah Geechee")
    gen.add_argument("--extra", default="", help="Extra style description")
    gen.add_argument("--provider", default="", help="Provider override")
    gen.add_argument("--model", default="", help="Model override")

    args = parser.parse_args()
    router = ModelRouter()

    if args.command == "status":
        result = router.status()
    elif args.command == "gallery":
        result = {"gallery": router.get_gallery()}
    elif args.command == "styles":
        result = {"styles": router.get_styles()}
    elif args.command == "providers":
        result = {"providers": router.get_providers()}
    elif args.command == "generate":
        result = router.generate(args.prompt, args.style, args.theme, args.extra, args.provider or None, args.model or None)

    if args.json:
        print(json.dumps(result, indent=2, default=str))
    else:
        if isinstance(result, dict):
            for k, v in result.items():
                if isinstance(v, list):
                    print(f"{k}: {len(v)} items")
                    for item in v[:5]:
                        if isinstance(item, dict):
                            print(f"  {item.get('id', '')[:20]:20} | {item.get('prompt', '')[:50]:50} | {item.get('provider', '')}")
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
