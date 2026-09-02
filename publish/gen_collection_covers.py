#!/usr/bin/env python3
"""Generate TikTok covers + captions for the 2 collections never promoted
(Music & Storytelling, Environment & Ecology) — both live on Gumroad.
Navy/gold style matching scripts/make-volume-tiktok-covers.py.
"""
from __future__ import annotations
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

OUT_DIR = Path("/Users/darrylsmac/gullahgeecheebiz-site/tiktok-content")
W, H = 1080, 1350
NAVY = (11, 26, 56, 255)
NAVY2 = (16, 38, 82, 255)
GOLD = (212, 175, 55, 255)
CREAM = (245, 240, 228, 255)
GEORGIA = "/System/Library/Fonts/Supplemental/Georgia.ttf"
GEORGIA_BOLD = "/System/Library/Fonts/Supplemental/Georgia Bold.ttf"

COLLECTIONS = [
    {
        "stem": "ggb-music-storytelling",
        "kicker": "GULLAH GEECHEE",
        "kicker2": "CULTURAL HERITAGE COLLECTION",
        "title": "Music & Storytelling",
        "subtitle": "Ring shouts, spirituals, and the stories that carry the culture.",
        "url": "https://debtide0.gumroad.com/l/vwnpk",
        "hashtags": "#GullahGeechee #Music #Storytelling #SeaIslands #GullahGeecheeBiz #Culture",
    },
    {
        "stem": "ggb-environment-ecology",
        "kicker": "GULLAH GEECHEE",
        "kicker2": "CULTURAL HERITAGE COLLECTION",
        "title": "Environment & Ecology",
        "subtitle": "Marshes, tides, and the living ecology that shaped Sea Island life.",
        "url": "https://debtide0.gumroad.com/l/xgkkis",
        "hashtags": "#GullahGeechee #Environment #Ecology #Lowcountry #GullahGeecheeBiz #SeaIslands",
    },
]


def font(path: str, size: int):
    return ImageFont.truetype(path, size)


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


def make_cover(cfg: dict) -> None:
    img = Image.new("RGB", (1, H))
    d0 = ImageDraw.Draw(img)
    for y in range(H):
        f = y / H
        c = tuple(int(NAVY[i] * (1 - f) + NAVY2[i] * f) for i in range(3))
        d0.point((0, y), fill=c)
    img = img.resize((W, H))
    d = ImageDraw.Draw(img)
    m = 70
    d.rectangle([m, m, W - m, H - m], outline=GOLD[:3], width=3)
    d.rectangle([m + 14, m + 14, W - m - 14, H - m - 14], outline=GOLD[:3], width=1)
    d.text((W / 2, 235), cfg["kicker"], font=font(GEORGIA, 46), fill=GOLD[:3], anchor="mm")
    d.text((W / 2, 295), cfg["kicker2"], font=font(GEORGIA, 42), fill=GOLD[:3], anchor="mm")
    d.line([W / 2 - 220, 345, W / 2 + 220, 345], fill=GOLD[:3], width=2)
    f_title = font(GEORGIA_BOLD, 84)
    lines = wrap(cfg["title"].upper(), d, f_title, W - 2 * (m + 40))
    y = 500
    for ln in lines[:4]:
        d.text((W / 2, y), ln, font=f_title, fill=CREAM[:3], anchor="mm")
        y += 108
    f_sub = font(GEORGIA, 46)
    sublines = wrap(cfg["subtitle"], d, f_sub, W - 2 * (m + 80))
    y = 760
    for ln in sublines[:4]:
        d.text((W / 2, y), ln, font=f_sub, fill=(200, 196, 180, 255), anchor="mm")
        y += 64
    d.text((W / 2, H - 170), "Darryl Elliott Brown", font=font(GEORGIA, 40), fill=CREAM[:3], anchor="mm")
    d.text((W / 2, H - 122), "Gullah Geechee Biz", font=font(GEORGIA, 40), fill=GOLD[:3], anchor="mm")
    jpg = OUT_DIR / f"{cfg['stem']}.jpg"
    img.save(jpg, "JPEG", quality=90)
    caption = (
        f"\U0001F4DA {cfg['kicker2'].title()}: {cfg['title']} by Darryl Elliott Brown\n"
        "\n"
        f"{cfg['subtitle']} Ebooks for every reader — available now on Gumroad.\n"
        "\n"
        f"\u25B6 {cfg['url']}\n"
        "\n"
        f"{cfg['hashtags']}"
    )
    (OUT_DIR / f"{cfg['stem']}.txt").write_text(caption)
    print("made", jpg.name)


if __name__ == "__main__":
    for cfg in COLLECTIONS:
        make_cover(cfg)
