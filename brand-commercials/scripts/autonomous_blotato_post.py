#!/usr/bin/env python3
"""Autonomous Blotato TikTok post for 3 GGB brand commercials.
Uses BLOTATO_API_KEY from env (injected via custom-cred proxy when available).
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request

API_BASE = "https://backend.blotato.com/v2"
TIKTOK_ACCOUNT_ID = os.environ.get(
    "BLOTATO_TIKTOK_ACCOUNT_ID", "67831c2612959648943d04a6"
)

POSTS = [
    {
        "name": "BP1 Full House",
        "media": "https://raw.githubusercontent.com/Darrylebrown/gullahgeecheebiz-site/master/merch/videos/ggb-brand-full-house.mp4",
        "text": (
            "Where rivers remember… and roots run deep.\n\n"
            "This is Gullah Geechee Biz — a cultural media house documenting Gullah Geechee "
            "people, places, and traditions so the record can never fade.\n\n"
            "Books. Podcasts. Audiobooks. Music. Daily stories. Heritage merch. One living archive.\n\n"
            "Preserve the past. Inspire the future.\n"
            "Subscribe @GullahGeecheeBiz\n\n"
            "#GullahGeechee #GullahGeecheeBiz #RootsAndRivers #Lowcountry #SeaIslands "
            "#CulturalHeritage #BlackHistory #DocumentaryCulture #PreserveThePast #SouthCarolina"
        ),
    },
    {
        "name": "BP2 Living Record",
        "media": "https://raw.githubusercontent.com/Darrylebrown/gullahgeecheebiz-site/master/merch/videos/ggb-brand-living-record.mp4",
        "text": (
            "Where rivers remember… and roots run deep.\n\n"
            "From Beaufort to Savannah and across the corridor, Gullah Geechee Biz builds the full cultural stack:\n\n"
            "Encyclopedia volumes. Kindle and Audible titles. Podcast episodes. Music releases. "
            "Daily social storytelling. Pinterest discovery. Merch that funds the work.\n\n"
            "This is more than content. It is a living record of America's Sea Island culture.\n\n"
            "Subscribe @GullahGeecheeBiz\n"
            "Preserve the past. Inspire the future.\n\n"
            "#GullahGeechee #GullahGeecheeBiz #RootsAndRivers #Beaufort #Savannah #SeaIslands "
            "#Lowcountry #CulturalHeritage #LivingRecord"
        ),
    },
    {
        "name": "BP3 Roots Rivers Beaufort",
        "media": "https://raw.githubusercontent.com/Darrylebrown/gullahgeecheebiz-site/master/merch/videos/ggb-brand-roots-rivers-beaufort.mp4",
        "text": (
            "Where rivers remember… and roots run deep.\n\n"
            "Welcome to Beaufort, South Carolina — where the Gullah Geechee legacy lives through "
            "history, family, faith, and tradition.\n\n"
            "Discover Roots and Rivers: Beaufort, South Carolina — Volume One of the Gullah Geechee "
            "Encyclopedia by Darryl Elliott Brown.\n\n"
            "This is more than a book. It is a journey into one of America's greatest cultural treasures.\n\n"
            "Subscribe to Gullah Geechee Biz. Preserve the past. Inspire the future.\n\n"
            "#GullahGeechee #GullahGeecheeBiz #RootsAndRivers #Beaufort #Lowcountry #SeaIslands #CulturalHeritage"
        ),
    },
]


def request(method: str, path: str, body: dict | None = None) -> tuple[int, object]:
    key = os.environ.get("BLOTATO_API_KEY")
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "blotato-api-key": key or "",
    }
    data = None if body is None else json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        f"{API_BASE}{path}", data=data, headers=headers, method=method
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            try:
                return resp.status, json.loads(raw)
            except json.JSONDecodeError:
                return resp.status, raw
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace")
        try:
            return e.code, json.loads(raw)
        except json.JSONDecodeError:
            return e.code, raw


def main() -> int:
    if not os.environ.get("BLOTATO_API_KEY"):
        # Proxy may inject via header only; still attempt verify
        print("WARN: BLOTATO_API_KEY env empty — relying on credential proxy injection")

    print("=== verify /users/me ===")
    status, me = request("GET", "/users/me")
    print(status, me)
    if status == 401:
        print("FAIL: unauthorized — need Blotato API key")
        return 2
    if status >= 400:
        print("FAIL: users/me error")
        return 3

    print("=== accounts ===")
    status, accounts = request("GET", "/users/me/accounts")
    print(status, accounts)

    results = []
    for i, post in enumerate(POSTS):
        payload = {
            "post": {
                "accountId": TIKTOK_ACCOUNT_ID,
                "content": {
                    "text": post["text"],
                    "mediaUrls": [post["media"]],
                    "platform": "tiktok",
                },
                "target": {
                    "targetType": "tiktok",
                    "privacyLevel": "PUBLIC_TO_EVERYONE",
                    "disabledComments": False,
                    "disabledDuet": False,
                    "disabledStitch": False,
                    "isBrandedContent": False,
                    "isYourBrand": True,
                    "isAiGenerated": True,
                },
            }
        }
        print(f"=== post {i+1}/3 {post['name']} ===")
        status, body = request("POST", "/posts", payload)
        print(status, body)
        results.append({"name": post["name"], "status": status, "body": body})
        if i < len(POSTS) - 1:
            time.sleep(2)

    out_path = "/home/user/workspace/ggb_commercials/autonomous_post_results.json"
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)
    print("wrote", out_path)

    ok = sum(1 for r in results if r["status"] in (200, 201))
    print(f"DONE {ok}/{len(results)} accepted")
    return 0 if ok == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
