#!/usr/bin/env python3
"""Generate per-volume TikTok cover art + captions for Encyclopedia volumes that are
published on Gumroad but have never had a TikTok post (vol 01-05, 12-25).

Each cover is a distinct navy/gold branded image (vol number + real dc:title from
the volume's EPUB). Caption links to the volume's live Gumroad short_url.
"""
from __future__ import annotations

import json
import re
import sys
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

GP_DIR = Path("/Users/darrylsmac/gullahgeecheebiz-site/publish/for-distribution/google-play")
OUT_DIR = Path("/Users/darrylsmac/gullahgeecheebiz-site/tiktok-content")
CATALOG = json.load(open("/Users/darrylsmac/gullahgeecheebiz-site/publish/gumroad_full_catalog_2026-09-02-0408.json"))

NAVY = (11, 26, 56, 255)        # deep navy bg
NAVY2 = (16, 38, 82, 255)       # subtle gradient bottom
GOLD = (212, 175, 55, 255)      # metallic gold
CREAM = (245, 240, 228, 255)    # warm paper white

W, H = 1080, 1350

GEORGIA = "/System/Library/Fonts/Supplemental/Georgia.ttf"
GEORGIA_BOLD = "/System/Library/Fonts/Supplemental/Georgia Bold.ttf"


def font(path, size):
    return ImageFont.truetype(path, size)


def get_epub_title(vol: int) -> str:
    """Read dc:title from the volume EPUB's content.opf."""
    fp = GP_DIR / f"pedia-vol-{vol:02d}.epub"
    with zipfile.ZipFile(fp) as z:
        opf_name = next(n for n in z.namelist() if n.endswith(".opf"))
        root = ET.fromstring(z.read(opf_name))
    ns = {"dc": "http://purl.org/dc/elements/1.1/"}
    t = root.find(".//dc:title", ns)
    return t.text.strip() if t is not None and t.text else ""


def get_short_url(vol: int) -> str | None:
    for p in CATALOG:
        if p.get("name") == f"Encyclopedia Volume {vol:02d}" and p.get("published"):
            return p.get("short_url")
    for p in CATALOG:  # fallback: any (incl. name without zero-pad)
        if p.get("name") == f"Encyclopedia Volume {vol}" and p.get("published"):
            return p.get("short_url")
    return None


def wrap(text: str, draw: ImageDraw.ImageDraw, fnt, max_w: int) -> list[str]:
    words = text.split()
    lines, cur = [], ""
    for w in words:
        test = f"{cur} {w}".strip()
        if draw.textlength(test, font=fnt) <= max_w:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def make_cover(vol: int, title: str, out_path: Path) -> None:
    img = Image.new("RGB", (W, H), NAVY[:3])
    # subtle vertical gradient
    top = Image.new("RGB", (1, H))
    for y in range(H):
        f = y / H
        c = tuple(int(NAVY[i] * (1 - f) + NAVY2[i] * f) for i in range(3))
        top.putpixel((0, y), c)
    img = top.resize((W, H))
    d = ImageDraw.Draw(img)

    # gold frame (double rule) — nod to Philip Simmons ironwork simplicity
    m = 70
    d.rectangle([m, m, W - m, H - m], outline=GOLD[:3], width=3)
    d.rectangle([m + 14, m + 14, W - m - 14, H - m - 14], outline=GOLD[:3], width=1)

    # top brand line
    f_brand = font(GEORGIA, 44)
    d.text((W / 2, 250), "GULLAH GEECHEE", font=f_brand, fill=GOLD[:3], anchor="mm")
    f_brand2 = font(GEORGIA, 44)
    d.text((W / 2, 305), "ENCYCLOPEDIA", font=f_brand2, fill=GOLD[:3], anchor="mm")

    # gold divider
    d.line([W / 2 - 220, 350, W / 2 + 220, 350], fill=GOLD[:3], width=2)

    # volume number
    f_vol = font(GEORGIA, 150)
    d.text((W / 2, 520), f"VOLUME {vol:02d}", font=f_vol, fill=GOLD[:3], anchor="mm")

    # volume title (wrapped)
    f_title = font(GEORGIA, 76)
    lines = wrap(title.upper(), d, f_title, W - 2 * (m + 60))
    y = 700
    for ln in lines[:4]:
        d.text((W / 2, y), ln, font=f_title, fill=CREAM[:3], anchor="mm")
        y += 100

    # bottom brand
    f_foot = font(GEORGIA, 40)
    d.text((W / 2, H - 180), "Darryl Elliott Brown", font=f_foot, fill=CREAM[:3], anchor="mm")
    d.text((W / 2, H - 128), "Gullah Geechee Biz", font=f_foot, fill=GOLD[:3], anchor="mm")

    img.save(out_path, "JPEG", quality=90)


def main() -> int:
    vols = list(range(1, 6)) + list(range(12, 26))
    made, skipped = [], []
    for v in vols:
        title = get_epub_title(v)
        url = get_short_url(v)
        if not title or not url:
            skipped.append((v, title, url))
            continue
        jpg = OUT_DIR / f"encyclopedia-volume-{v:02d}.jpg"
        txt = OUT_DIR / f"encyclopedia-volume-{v:02d}.txt"
        make_cover(v, title, jpg)
        caption = (
            f"\U0001F4DA Encyclopedia Volume {v:02d}: {title} by Darryl Elliott Brown\n"
            "Now available on Gumroad!\n\n"
            "Explore the rich Gullah Geechee heritage \u2014 language, history, traditions, and more.\n\n"
            f"\u25B6 https://debtide0.gumroad.com/l/{url.rsplit('/', 1)[-1]}\n\n"
            "#GullahGeechee #AfricanAmericanHistory #BlackHistory #GullahGeecheeBiz #Books #Knowledge"
        )
        txt.write_text(caption)
        made.append(v)
        print(f"vol {v:02d}: {title!r} -> {jpg.name} | {url}")

    print(f"\nMade {len(made)} covers: {made}")
    if skipped:
        print("SKIPPED (missing title/url):", skipped)
    return 0 if skipped == [] else 1


if __name__ == "__main__":
    sys.exit(main())
