#!/usr/bin/env python3
"""Log final marketing event to brain database"""
import sqlite3
import json
from datetime import datetime, timezone

brain_db = "/Users/darrylsmac/gullahgeecheebiz-site/ggb-engine/headquarters/brain.db"
events = [
    ("marketing_run_complete", "MARKETING_GOAL", "Marketing orchestrator run complete — content generated, site deployed, API rate-limited on product publishing", {
        "date": "2026-09-01",
        "run_id": "cron-20260901-2130",
        "actions": {
            "substack_published": 4,
            "tiktok_scripts_created": 9,
            "pinterest_pins_generated": 20,
            "twitter_tweets_created": 10,
            "seo_pages_created": 10,
            "total_viral_pages": 93,
            "gumroad_products_total": 91,
            "gumroad_published": 46,
            "gumroad_unpublished": 43,
            "sales": 0.0,
            "email_list_size": 0,
            "status": "content_generation_active_api_rate_limited"
        },
        "blockers": ["gumroad_api_rate_limit", "twitter_auth_missing", "facebook_auth_missing"],
        "next_cron": "Continue content generation and monitor organic SEO traffic"
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
print("Final events logged to brain.")
