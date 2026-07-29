#!/usr/bin/env python3
"""Generate the ebook store HTML with individual Stripe checkout links."""
import json, os

HOME = os.path.expanduser("~")
SITE_DIR = os.path.join(HOME, "gullahgeecheebiz-site")
LINKS_FILE = os.path.join(SITE_DIR, "downloads", "stripe-links.json")

with open(LINKS_FILE) as f:
    links = json.load(f)

# Build a lookup by slug
link_map = {l["slug"]: l["checkout_url"] for l in links}

# Read the current ebooks page
with open(os.path.join(SITE_DIR, "ebooks", "index.html")) as f:
    html = f.read()

# Replace the generic STRIPE_LINK with individual links
# We need to rebuild the EBOOKS array with checkout URLs
ebooks_js = "const EBOOKS = [\n"
for l in links:
    cat = "self-help"
    if l["slug"] in [
        "gullah-entrepreneur","lowcountry-marketing","gullah-side-hustle","gullah-finance",
        "gullah-publishing","gullah-ecommerce","gullah-tourism","gullah-craft-business",
        "gullah-food-business","gullah-cooperative","gullah-freelance","gullah-real-estate",
        "gullah-nonprofit","gullah-investing","gullah-consulting","gullah-remote-work",
        "gullah-budget","gullah-credit","gullah-debt","gullah-retirement","gullah-taxes",
        "gullah-insurance","gullah-estate","gullah-farming","gullah-fishing","gullah-catering",
        "gullah-bed-breakfast","gullah-art-gallery","gullah-museum","gullah-podcast",
        "gullah-youtube","gullah-newsletter","gullah-etsy","gullah-wholesale"
    ]:
        cat = "business"
    elif l["slug"] in [
        "gullah-kitchen-v1","gullah-kitchen-v2","gullah-sunday-dinner","gullah-seafood",
        "gullah-soul-food","gullah-desserts","gullah-one-pot","gullah-holiday",
        "gullah-vegetarian","gullah-breakfast","gullah-preserving","gullah-grilling",
        "gullah-sauces","gullah-baking","gullah-drinks","gullah-rice","gullah-cast-iron",
        "gullah-slow-cooker","gullah-30-minute","gullah-meal-prep","gullah-kids-cook",
        "gullah-appetizers","gullah-summer-cooking","gullah-winter-cooking","gullah-cajun",
        "gullah-caribbean","gullah-west-african","gullah-fermentation","gullah-gluten-free",
        "gullah-vegan","gullah-keto","gullah-paleo","gullah-air-fryer","gullah-instant-pot",
        "gullah-camping"
    ]:
        cat = "cooking"
    
    ebooks_js += f'  {{ slug: "{l["slug"]}", title: "{l["title"]}", cat: "{cat}", url: "{l["checkout_url"]}" }},\n'
ebooks_js += "];\n"

# Replace the EBOOKS array in the HTML
import re
html = re.sub(
    r'const EBOOKS = \[.*?\];',
    ebooks_js,
    html,
    flags=re.DOTALL
)

# Update the render function to use individual URLs
html = html.replace(
    "const checkoutUrl = STRIPE_LINK + '?ebook=' + b.slug;",
    "const checkoutUrl = b.url;"
)

# Remove the unused STRIPE_LINK constant
html = html.replace('const STRIPE_LINK = "https://buy.stripe.com/28E6oG6XscKVfea90GcjS00";\n    ', '')

with open(os.path.join(SITE_DIR, "ebooks", "index.html"), "w") as f:
    f.write(html)

print("✅ Ebook store updated with individual Stripe checkout links")
print(f"   {len(links)} ebooks with unique buy buttons")
