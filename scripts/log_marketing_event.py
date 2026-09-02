#!/usr/bin/env python3
"""Log marketing event to brain database"""
import sqlite3
import json
from datetime import datetime, timezone

brain_db = "/Users/darrylsmac/gullahgeecheebiz-site/ggb-engine/headquarters/brain.db"
events = [
    ("marketing_run", "MARKETING_GOAL", "Marketing content batch created — TikTok scripts, Pinterest pins, Twitter posts, Substack published", {
        "date": "2026-09-01",
        "actions": {
            "substack_published": 4,
            "tiktok_scripts_created": 9,
            "pinterest_pins_generated": 20,
            "twitter_tweets_created": 10,
            "seo_pages_existing": 68,
            "gumroad_products_total": 91,
            "gumroad_published": 46,
            "gumroad_unpublished": 43,
            "sales": 0.0,
            "email_list_size": 0,
            "status": "content_generation_active"
        },
        "notes": "Revenue orchestrator running in background to publish remaining products. Twitter/Facebook auth blocked. Organic SEO pages live but need indexing time."
    }),
    ("content_created", "MARKETING_GOAL", "Generated new marketing content: 9 TikTok scripts, 20 Pinterest pins, 10 Twitter posts", {
        "files_created": [
            "/Users/darrylsmac/gullahgeecheebiz-site/tiktok-scripts/2026-09-01-content-batch2.md",
            "/Users/darrylsmac/gullahgeecheebiz-site/pinterest/2026-09-01-pin-batch2.md",
            "/Users/darrylsmac/gullahgeecheebiz-site/twitter/2026-09-01-content-batch2.md"
        ]
    }),
]

conn = sqlite3.connect(brain_db)
c = conn.cursor()
for event_type, source_bot, message, data in events:
    c.execute(
        "INSERT INTO event_stream (timestamp, source_bot, event_type, message, data) VALUES (?, ?, ?, ?, ?)",
        (datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S'), source_bot, event_type, message, json.dumps(data))
    )
    print(f"[LOG] {event_type}: {message}")
conn.commit()
conn.close()
print("Events logged to brain.")
