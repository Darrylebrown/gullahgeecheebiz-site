#!/usr/bin/env python3
"""Generate promo banners for the Heritage Vault and Institutional Site License."""
from PIL import Image, ImageDraw, ImageFilter, ImageFont
import glob, os

W, H = 1600, 700

def gradient(bg_top, bg_bot):
    img = Image.new("RGB", (W, H), bg_top)
    d = ImageDraw.Draw(img)
    for y in range(H):
        t = y / (H - 1)
        d.line([(0, y), (W, y)], fill=(int(bg_top[0] + (bg_bot[0] - bg_top[0]) * t),
                                       int(bg_top[1] + (bg_bot[1] - bg_top[1]) * t),
                                       int(bg_top[2] + (bg_bot[2] - bg_top[2]) * t)))
    return img

def font(sz):
    cands = sorted(glob.glob("/Library/Fonts/*Bold*.ttf") +
                   glob.glob("/System/Library/Fonts/Supplemental/*Bold*.ttf") +
                   glob.glob("/Library/Fonts/*.ttf"))
    cands += ["/System/Library/Fonts/Supplemental/Georgia Bold.ttf",
              "/System/Library/Fonts/Supplemental/Times New Roman Bold.ttf"]
    for p in cands:
        if "Georgia" in p or "Times" in p or "Bold" in p:
            try:
                return ImageFont.truetype(p, sz)
            except Exception:
                pass
    return ImageFont.load_default()

def shelf(img, covers, x_start, y_base, cw=118, ch=178, gap=16):
    d = ImageDraw.Draw(img)
    for i, p in enumerate(covers[:6]):
        if not os.path.exists(p):
            continue
        try:
            c = Image.open(p).convert("RGB").resize((cw, ch))
            x = x_start + i * (cw + gap)
            y = y_base + i * 2
            sh = Image.new("RGBA", (cw + 8, ch + 8), (0, 0, 0, 0))
            ImageDraw.Draw(sh).rectangle([4, 4, cw + 3, ch + 3], fill=(0, 0, 0, 120))
            sh = sh.filter(ImageFilter.GaussianBlur(3))
            img.paste(sh, (x - 2, y + 6), sh)
            img.paste(c, (x, y))
        except Exception as e:
            print("cover skip", p, e)

def frame(img, gold=(196, 138, 26)):
    d = ImageDraw.Draw(img)
    d.rectangle([0, H - 18, W, H], fill=gold)
    d.ellipse([W - 420, H - 420, W - 60, H - 60], outline=(*gold, 90), width=2)
    d.ellipse([W - 380, H - 380, W - 100, H - 100], outline=(*gold, 60), width=1)

COVERS = lambda vs: [f"publish/landing-pad/encyclopedia-vol-{v}/cover.jpg" for v in vs]

# ---------- Heritage Vault ----------
GOLD = (196, 138, 26); CREAM = (245, 239, 230); SOFT = (214, 195, 160)
img = gradient((15, 42, 66), (7, 18, 30))
d = ImageDraw.Draw(img)
frame(img)
f_tag = font(26); f_big = font(84); f_mid = font(40); f_sub = font(26)
d.text((70, 95), "THE ULTIMATE", font=f_tag, fill=GOLD)
d.text((70, 140), "HERITAGE VAULT", font=f_big, fill=CREAM)
d.text((70, 268), "Complete ebooks + audiobook narration", font=f_mid, fill=SOFT)
d.text((70, 324), "+ genealogy checklists, in one master library.", font=f_mid, fill=SOFT)
d.text((70, 400), "Read, listen, and trace your ancestry — one download.", font=f_sub, fill=SOFT)
d.text((70, 470), "Only $97.00 \u00b7 every sale funds preservation", font=f_sub, fill=SOFT)
shelf(img, COVERS(["28", "10", "16", "22", "25", "44"]), 850, 250, 122, 186)
img.save("promo/heritage-vault-promo.png")
print("wrote promo/heritage-vault-promo.png", os.path.getsize("promo/heritage-vault-promo.png"))

# ---------- Site License ----------
img = gradient((12, 26, 22), (4, 12, 10))
d = ImageDraw.Draw(img)
frame(img, gold=(186, 130, 22))
f_tag = font(26); f_big = font(80); f_mid = font(38); f_sub = font(26)
d.text((70, 95), "FOR LIBRARIES, UNIVERSITIES & MUSEUMS", font=f_tag, fill=GOLD)
d.text((70, 145), "INSTITUTIONAL", font=f_big, fill=CREAM)
d.text((70, 248), "SITE LICENSE", font=f_big, fill=CREAM)
d.text((70, 362), "Unlimited campus-wide & patron access to the", font=f_mid, fill=SOFT)
d.text((70, 414), "complete Gullah Geechee Encyclopedia collection.", font=f_mid, fill=SOFT)
d.text((70, 486), "One institutional license \u00b7 $497.00", font=f_sub, fill=SOFT)
shelf(img, COVERS(["25", "44", "42", "28", "20", "10"]), 850, 250, 122, 186)
img.save("promo/site-license-promo.png")
print("wrote promo/site-license-promo.png", os.path.getsize("promo/site-license-promo.png"))