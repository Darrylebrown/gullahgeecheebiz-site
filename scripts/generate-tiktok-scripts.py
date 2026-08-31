#!/usr/bin/env python3
"""Generate TikTok scripts for GGB promotion."""
from pathlib import Path
from datetime import datetime

promotion_dir = Path("/Users/darrylsmac/gullahgeecheebiz-site/publish/promotion/googleplay")
promotion_dir.mkdir(parents=True, exist_ok=True)

scripts = []
for i in range(1, 11):
    script = f"""TikTok Script #{i}

🎬 HOOK (0-3 seconds):
"Did you know there's a culture older than America itself?"

📝 BODY (3-30 seconds):
"The Gullah Geechee people have preserved 300 years of history, language, and traditions on the Sea Islands from Georgia to Florida.

From red rice to ring shouts, from sweetgrass baskets to freestyle rap — this is the foundation of African American culture.

And now, the COMPLETE encyclopedia is available. All 25 volumes. One box set."

💰 CTA (30-45 seconds):
"Link in bio to get the Gullah Geechee Encyclopedia Box Set — $39.99 for all 25 volumes!"

🏷️ HASHTAGS:
#gullah #geechee #history #blackhistory #southernfood #culture #education #learnontiktok #africanamerican #heritage"""
    scripts.append(script)

output_file = promotion_dir / "tiktok-scripts-batch1.md"
output_file.write_text("\n\n".join(scripts), encoding="utf-8")
print(f"Created {len(scripts)} TikTok scripts")
