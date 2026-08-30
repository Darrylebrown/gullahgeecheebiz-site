#!/usr/bin/env python3
"""Fix viral landing pages with correct Gumroad product URLs."""
import urllib.request, json
from pathlib import Path

BASE = Path("/Users/darrylsmac/gullahgeecheebiz-site")
VIRAL = BASE / "viral"

TOKEN = None
for line in open(BASE / ".env").read().splitlines():
    if line.startswith("GUMROAD_ACCESS_TOKEN="):
        TOKEN = line.split("=", 1)[1].strip().strip('"').strip("'")
        break

# Fetch current Gumroad URLs
req = urllib.request.Request("https://api.gumroad.com/v2/products", headers={"Authorization": f"Bearer {TOKEN}"})
with urllib.request.urlopen(req) as resp:
    data = json.loads(resp.read().decode())

gumroad_urls = {}
for p in data.get("products", []):
    name = p["name"].strip()
    gumroad_urls[name] = p.get("short_url", "")

print("Gumroad URLs fetched:")
for k, v in gumroad_urls.items():
    print(f"  {k[:50]}: {v}")

# Fix the encyclopedia box set landing page
box_set_url = gumroad_urls.get("Gullah Geechee Encyclopedia - Complete Box Set (Vol 1-25)", "https://debtide0.gumroad.com/l/encyclopedia-box-set")
vault_url = gumroad_urls.get("Ultimate Gullah Geechee Heritage Vault (Ebooks + Audiobooks + Genealogy)", "")
language_url = gumroad_urls.get("Gullah Geechee Cultural Heritage Collection — Language & Dialect", "")
history_url = gumroad_urls.get("Gullah Geechee Cultural Heritage Collection — History & Genealogy", "")
traditions_url = gumroad_urls.get("Gullah Geechee Cultural Heritage Collection — Traditions & Recipes", "")
spirituality_url = gumroad_urls.get("Gullah Geechee Cultural Heritage Collection — Spirituality & Folklore", "")
art_url = gumroad_urls.get("Gullah Geechee Cultural Heritage Collection — Art & Craft", "")
music_url = gumroad_urls.get("Gullah Geechee Cultural Heritage Collection — Music & Storytelling", "")
environment_url = gumroad_urls.get("Gullah Geechee Cultural Heritage Collection — Environment & Ecology", "")

print(f"\nBox Set URL: {box_set_url}")
print(f"Vault URL: {vault_url}")

# Update the landing page
page = VIRAL / "encyclopedia-box-set-buy.html"
content = page.read_text()
content = content.replace("https://debtide0.gumroad.com/l/encyclopedia-box-set", box_set_url)
page.write_text(content)
print(f"Updated: {page.name}")

# Update books collection page if it exists
books_page = VIRAL / "gullah-geechee-books-collection.html"
if books_page.exists():
    content = books_page.read_text()
    content = content.replace("https://debtide0.gumroad.com/l/fpnfz", box_set_url)
    content = content.replace("https://debtide0.gumroad.com/l/rlxww", vault_url)
    content = content.replace("https://debtide0.gumroad.com/l/hoiak", gumroad_urls.get("Gullah Geechee Institutional Site License (Library / University)", ""))
    books_page.write_text(content)
    print(f"Updated: {books_page.name}")

print("Done.")
