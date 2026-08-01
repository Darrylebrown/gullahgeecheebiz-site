#!/usr/bin/env python3
"""
GGB Music Studio — Generates music prompts, schedules production, manages catalog.
Integrates with Suno AI, DistroKid, and the radio station.
"""
import json, sys, uuid, random
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from headquarters.engine import HQDatabase, STUDIO_DIR

# ─── Music Catalog ─────────────────────────────────────────────────────────

GENRES = {
    "ambient": {"bpm": (60, 80), "instruments": ["pads", "field recordings", "soft piano", "strings"]},
    "folk": {"bpm": (80, 120), "instruments": ["acoustic guitar", "banjo", "fiddle", "harmonica"]},
    "blues": {"bpm": (60, 100), "instruments": ["slide guitar", "piano", "bass", "harmonica"]},
    "world": {"bpm": (90, 130), "instruments": ["djembe", "kora", "kalimba", "talking drum"]},
    "cinematic": {"bpm": (60, 90), "instruments": ["orchestra", "choir", "brass", "strings"]},
    "gospel": {"bpm": (80, 120), "instruments": ["organ", "piano", "choir", "hand claps"]},
    "percussion": {"bpm": (100, 140), "instruments": ["djembe", "shekere", "claves", "conga"]},
}

THEMES = {
    "sweetgrass": "Gentle, warm, organic. Acoustic guitar and soft percussion. Evokes coastal marshlands at sunset.",
    "gullah": "Rhythmic, celebratory. Call-and-response vocals, djembe, banjo. African diaspora roots.",
    "lowcountry": "Slow, atmospheric. Slide guitar, piano, deep bass. Sea Islands at dawn.",
    "rice": "Upbeat, rhythmic. Banjo, fiddle, hand claps. Work song energy. Joyful.",
    "history": "Cinematic, building. Strings, brass, choir. From somber to triumphant.",
    "resilience": "Steady, determined. Piano, strings, soft percussion. Overcoming adversity.",
    "community": "Warm, harmonious. Acoustic ensemble, group vocals. Togetherness.",
    "healing": "Slow, meditative. Ambient pads, soft piano, nature sounds. Restoration.",
}

class MusicStudio:
    """GGB Music Studio — prompt generation, catalog management, production scheduling."""

    def __init__(self, db: HQDatabase = None):
        self.db = db or HQDatabase()

    def generate_prompt(self, theme: str = "sweetgrass", genre: str = None) -> dict:
        """Generate a Suno AI music prompt from a theme."""
        theme_desc = THEMES.get(theme, f"Atmospheric music inspired by {theme}")
        if genre and genre in GENRES:
            g = GENRES[genre]
            bpm = random.randint(g["bpm"][0], g["bpm"][1])
            instruments = random.sample(g["instruments"], min(3, len(g["instruments"])))
            prompt = f"{theme_desc} Style: {genre}. Instruments: {', '.join(instruments)}. BPM: {bpm}. No vocals. Instrumental."
        else:
            prompt = theme_desc

        result = {
            "theme": theme,
            "genre": genre or "auto",
            "prompt": prompt,
            "generated": datetime.now(timezone.utc).isoformat(),
        }

        output = STUDIO_DIR / f"music-{theme}-{uuid.uuid4().hex[:6]}.json"
        output.write_text(json.dumps(result, indent=2))
        self.db.log_content("music", "prompt", f"Music prompt: {theme}", str(output))
        return result

    def generate_album(self, theme: str = "gullah", tracks: int = 8) -> dict:
        """Generate a full album of music prompts."""
        album = {
            "title": f"{theme.title} Collection",
            "theme": theme,
            "tracks": tracks,
            "generated": datetime.now(timezone.utc).isoformat(),
            "track_list": [],
        }
        for i in range(tracks):
            genre = random.choice(list(GENRES.keys()))
            prompt = self.generate_prompt(theme, genre)
            album["track_list"].append({
                "track": i + 1,
                "title": f"{theme.title} Movement {i + 1}",
                "genre": genre,
                "prompt": prompt["prompt"],
            })

        output = STUDIO_DIR / f"album-{theme}-{uuid.uuid4().hex[:6]}.json"
        output.write_text(json.dumps(album, indent=2))
        self.db.log_content("music", "album", album["title"], str(output))
        return album

    def catalog(self) -> dict:
        """List all generated music assets."""
        prompts = list(STUDIO_DIR.glob("music-*.json"))
        albums = list(STUDIO_DIR.glob("album-*.json"))
        return {
            "prompts": len(prompts),
            "albums": len(albums),
            "total": len(prompts) + len(albums),
        }


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="GGB Music Studio")
    parser.add_argument("--json", action="store_true")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("catalog", help="List music assets")
    prompt = sub.add_parser("prompt", help="Generate a music prompt")
    prompt.add_argument("--theme", default="sweetgrass")
    prompt.add_argument("--genre")
    album = sub.add_parser("album", help="Generate an album")
    album.add_argument("--theme", default="gullah")
    album.add_argument("--tracks", type=int, default=8)

    args = parser.parse_args()
    studio = MusicStudio()

    if args.command == "catalog":
        result = studio.catalog()
    elif args.command == "prompt":
        result = studio.generate_prompt(args.theme, args.genre)
    elif args.command == "album":
        result = studio.generate_album(args.theme, args.tracks)

    if args.json:
        print(json.dumps(result, indent=2, default=str))
    else:
        if isinstance(result, dict):
            for k, v in result.items():
                print(f"{k}: {v}")
        else:
            print(result)
