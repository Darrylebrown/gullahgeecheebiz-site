#!/usr/bin/env python3
"""
GGB Social Media Syndication Bot — auto-generates TikTok scripts, Instagram carousels,
Twitter threads, and Pinterest pins for every new publication.
"""
import json, sys, uuid
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from publisher import REPO_ROOT

OUTPUT_DIR = REPO_ROOT / "publish" / "social"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

class SocialSyndicator:
    def __init__(self):
        self.stats = {"generated": 0}

    def generate_tiktok_script(self, title: str, description: str) -> dict:
        script = f"""TikTok Script: {title}

[HOOK - 0-3s]
"Did you know the Gullah Geechee people have preserved African traditions for over 400 years?"

[BODY - 3-25s]
"Today we're talking about {title.lower()}. This is a story that needs to be told."

[VISUAL]
- Text overlay: "{title}"
- Background: Lowcountry marsh or sweetgrass basket weaving
- Music: Soft acoustic guitar

[CTA - 25-30s]
"Link in bio to learn more. Follow for more Gullah Geechee culture."

#GullahGeechee #Lowcountry #CulturalHeritage #{title.replace(' ', '')}
"""
        path = OUTPUT_DIR / f"tiktok-{uuid.uuid4().hex[:8]}.md"
        path.write_text(script)
        self.stats["generated"] += 1
        return {"platform": "tiktok", "title": title, "path": str(path)}

    def generate_instagram_carousel(self, title: str) -> dict:
        carousel = f"""Instagram Carousel: {title}

Slide 1: Cover image with title overlay
Slide 2: "The Gullah Geechee people have preserved African traditions for over 400 years."
Slide 3: "This book explores {title.lower()} through the lens of Gullah Geechee culture."
Slide 4: "Available now at gullahgeecheebiz.com"
Slide 5: "Follow for more Gullah Geechee stories."

#GullahGeechee #BookLaunch #Lowcountry #{title.replace(' ', '')}
"""
        path = OUTPUT_DIR / f"instagram-{uuid.uuid4().hex[:8]}.md"
        path.write_text(carousel)
        self.stats["generated"] += 1
        return {"platform": "instagram", "title": title, "path": str(path)}

    def generate_pinterest_pin(self, title: str) -> dict:
        pin = f"""Pinterest Pin: {title}

Title: {title}
Description: Discover the rich history and culture of the Gullah Geechee people. {title} is available now.
Board: Gullah Geechee Books
Link: https://gullahgeecheebiz.com/ebooks

#GullahGeechee #Books #Lowcountry #{title.replace(' ', '')}
"""
        path = OUTPUT_DIR / f"pinterest-{uuid.uuid4().hex[:8]}.md"
        path.write_text(pin)
        self.stats["generated"] += 1
        return {"platform": "pinterest", "title": title, "path": str(path)}

    def syndicate(self, title: str, description: str = "") -> dict:
        return {
            "tiktok": self.generate_tiktok_script(title, description),
            "instagram": self.generate_instagram_carousel(title),
            "pinterest": self.generate_pinterest_pin(title),
        }


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("title", help="Book title")
    parser.add_argument("--description", default="")
    args = parser.parse_args()
    bot = SocialSyndicator()
    result = bot.syndicate(args.title, args.description)
    print(json.dumps(result, indent=2))
