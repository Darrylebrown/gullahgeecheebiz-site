#!/usr/bin/env python3
"""
Gullah Geechee Biz — Etsy Product Generator
Creates PDF delivery documents and listing metadata for all 100 ebooks.
Follows the "boring PDFs" model: sell a PDF that delivers the actual files.
"""

import os, json, textwrap
from datetime import date
from fpdf import FPDF

HOME = os.path.expanduser("~")
SITE_DIR = os.path.join(HOME, "gullahgeecheebiz-site")
EBOOKS_DIR = os.path.join(HOME, "ebooks", "mass")
OUT_DIR = os.path.join(HOME, "etsy-products")
os.makedirs(OUT_DIR, exist_ok=True)
os.makedirs(os.path.join(OUT_DIR, "pdfs"), exist_ok=True)
os.makedirs(os.path.join(OUT_DIR, "metadata"), exist_ok=True)

# Ebook catalog (same as the Stripe generator)
EBOOKS = [
    {"slug": "gullah-resilience", "title": "The Gullah Geechee Guide to Resilience", "cat": "self-help"},
    {"slug": "gullah-mindset", "title": "The Gullah Geechee Mindset", "cat": "self-help"},
    {"slug": "gullah-identity", "title": "Finding Your Roots: A Gullah Geechee Guide to Identity", "cat": "self-help"},
    {"slug": "gullah-purpose", "title": "The Gullah Geechee Guide to Purpose", "cat": "self-help"},
    {"slug": "gullah-gratitude", "title": "Gullah Geechee Gratitude", "cat": "self-help"},
    {"slug": "gullah-healing", "title": "Gullah Geechee Healing", "cat": "self-help"},
    {"slug": "gullah-calm", "title": "The Gullah Geechee Guide to Calm", "cat": "self-help"},
    {"slug": "gullah-joy", "title": "Gullah Geechee Joy", "cat": "self-help"},
    {"slug": "gullah-grief", "title": "Gullah Geechee Wisdom for Grief", "cat": "self-help"},
    {"slug": "gullah-courage", "title": "Gullah Geechee Courage", "cat": "self-help"},
    {"slug": "gullah-patience", "title": "The Gullah Geechee Art of Patience", "cat": "self-help"},
    {"slug": "gullah-community", "title": "The Gullah Geechee Way of Community", "cat": "self-help"},
    {"slug": "gullah-wisdom", "title": "Gullah Geechee Wisdom for Daily Living", "cat": "self-help"},
    {"slug": "gullah-fatherhood", "title": "Gullah Geechee Fatherhood", "cat": "self-help"},
    {"slug": "gullah-motherhood", "title": "Gullah Geechee Motherhood", "cat": "self-help"},
    {"slug": "gullah-forgiveness", "title": "Gullah Geechee Forgiveness", "cat": "self-help"},
    {"slug": "gullah-hope", "title": "Gullah Geechee Hope", "cat": "self-help"},
    {"slug": "gullah-elders", "title": "Honoring Gullah Geechee Elders", "cat": "self-help"},
    {"slug": "gullah-marriage", "title": "Gullah Geechee Marriage", "cat": "self-help"},
    {"slug": "gullah-grandparenting", "title": "Gullah Geechee Grandparenting", "cat": "self-help"},
    {"slug": "gullah-aging", "title": "Gullah Geechee Guide to Aging Well", "cat": "self-help"},
    {"slug": "gullah-mental-health", "title": "Gullah Geechee Guide to Mental Health", "cat": "self-help"},
    {"slug": "gullah-sabbath", "title": "The Gullah Geechee Sabbath", "cat": "self-help"},
    {"slug": "gullah-relationships", "title": "Gullah Geechee Relationships", "cat": "self-help"},
    {"slug": "gullah-morning", "title": "Gullah Geechee Morning Rituals", "cat": "self-help"},
    {"slug": "gullah-bedtime", "title": "Gullah Geechee Bedtime Rituals", "cat": "self-help"},
    {"slug": "gullah-spring", "title": "Gullah Geechee Spring", "cat": "self-help"},
    {"slug": "gullah-summer", "title": "Gullah Geechee Summer", "cat": "self-help"},
    {"slug": "gullah-autumn", "title": "Gullah Geechee Autumn", "cat": "self-help"},
    {"slug": "gullah-winter", "title": "Gullah Geechee Winter", "cat": "self-help"},
    {"slug": "gullah-gratitude-journal", "title": "The Gullah Geechee Gratitude Journal", "cat": "self-help"},
    {"slug": "gullah-entrepreneur", "title": "The Gullah Geechee Entrepreneur", "cat": "business"},
    {"slug": "lowcountry-marketing", "title": "Lowcountry Marketing", "cat": "business"},
    {"slug": "gullah-side-hustle", "title": "The Gullah Geechee Side Hustle", "cat": "business"},
    {"slug": "gullah-finance", "title": "Gullah Geechee Guide to Financial Freedom", "cat": "business"},
    {"slug": "gullah-publishing", "title": "The Gullah Geechee Guide to Self-Publishing", "cat": "business"},
    {"slug": "gullah-ecommerce", "title": "Gullah Geechee E-Commerce", "cat": "business"},
    {"slug": "gullah-tourism", "title": "Gullah Geechee Tourism Guide", "cat": "business"},
    {"slug": "gullah-craft-business", "title": "The Gullah Geechee Craft Business Guide", "cat": "business"},
    {"slug": "gullah-food-business", "title": "Starting a Gullah Geechee Food Business", "cat": "business"},
    {"slug": "gullah-cooperative", "title": "The Gullah Geechee Cooperative", "cat": "business"},
    {"slug": "gullah-freelance", "title": "The Gullah Geechee Freelancer", "cat": "business"},
    {"slug": "gullah-real-estate", "title": "Gullah Geechee Guide to Real Estate", "cat": "business"},
    {"slug": "gullah-nonprofit", "title": "Starting a Gullah Geechee Nonprofit", "cat": "business"},
    {"slug": "gullah-investing", "title": "Gullah Geechee Investing", "cat": "business"},
    {"slug": "gullah-consulting", "title": "The Gullah Geechee Consultant", "cat": "business"},
    {"slug": "gullah-remote-work", "title": "Gullah Geechee Guide to Remote Work", "cat": "business"},
    {"slug": "gullah-budget", "title": "The Gullah Geechee Budget", "cat": "business"},
    {"slug": "gullah-credit", "title": "Gullah Geechee Guide to Credit", "cat": "business"},
    {"slug": "gullah-debt", "title": "Gullah Geechee Guide to Debt Freedom", "cat": "business"},
    {"slug": "gullah-retirement", "title": "Gullah Geechee Guide to Retirement", "cat": "business"},
    {"slug": "gullah-taxes", "title": "Gullah Geechee Guide to Taxes", "cat": "business"},
    {"slug": "gullah-insurance", "title": "Gullah Geechee Guide to Insurance", "cat": "business"},
    {"slug": "gullah-estate", "title": "Gullah Geechee Guide to Estate Planning", "cat": "business"},
    {"slug": "gullah-farming", "title": "The Gullah Geechee Farmer", "cat": "business"},
    {"slug": "gullah-fishing", "title": "The Gullah Geechee Fisherman", "cat": "business"},
    {"slug": "gullah-catering", "title": "Starting a Gullah Geechee Catering Business", "cat": "business"},
    {"slug": "gullah-bed-breakfast", "title": "Starting a Gullah Geechee Bed and Breakfast", "cat": "business"},
    {"slug": "gullah-art-gallery", "title": "Starting a Gullah Geechee Art Gallery", "cat": "business"},
    {"slug": "gullah-museum", "title": "Starting a Gullah Geechee Museum", "cat": "business"},
    {"slug": "gullah-podcast", "title": "Starting a Gullah Geechee Podcast", "cat": "business"},
    {"slug": "gullah-youtube", "title": "Starting a Gullah Geechee YouTube Channel", "cat": "business"},
    {"slug": "gullah-newsletter", "title": "Starting a Gullah Geechee Newsletter", "cat": "business"},
    {"slug": "gullah-etsy", "title": "Selling Gullah Geechee Products on Etsy", "cat": "business"},
    {"slug": "gullah-wholesale", "title": "The Gullah Geechee Guide to Wholesale", "cat": "business"},
    {"slug": "gullah-kitchen-v1", "title": "The Gullah Geechee Kitchen Volume 1", "cat": "cooking"},
    {"slug": "gullah-kitchen-v2", "title": "The Gullah Geechee Kitchen Volume 2", "cat": "cooking"},
    {"slug": "gullah-sunday-dinner", "title": "Gullah Geechee Sunday Dinner", "cat": "cooking"},
    {"slug": "gullah-seafood", "title": "Gullah Geechee Seafood Cookbook", "cat": "cooking"},
    {"slug": "gullah-soul-food", "title": "Gullah Geechee Soul Food", "cat": "cooking"},
    {"slug": "gullah-desserts", "title": "Gullah Geechee Desserts", "cat": "cooking"},
    {"slug": "gullah-one-pot", "title": "Gullah Geechee One-Pot Meals", "cat": "cooking"},
    {"slug": "gullah-holiday", "title": "Gullah Geechee Holiday Cookbook", "cat": "cooking"},
    {"slug": "gullah-vegetarian", "title": "Gullah Geechee Vegetarian", "cat": "cooking"},
    {"slug": "gullah-breakfast", "title": "Gullah Geechee Breakfast", "cat": "cooking"},
    {"slug": "gullah-preserving", "title": "Gullah Geechee Guide to Preserving", "cat": "cooking"},
    {"slug": "gullah-grilling", "title": "Gullah Geechee Grilling", "cat": "cooking"},
    {"slug": "gullah-sauces", "title": "Gullah Geechee Sauces and Seasonings", "cat": "cooking"},
    {"slug": "gullah-baking", "title": "Gullah Geechee Baking", "cat": "cooking"},
    {"slug": "gullah-drinks", "title": "Gullah Geechee Drinks and Beverages", "cat": "cooking"},
    {"slug": "gullah-rice", "title": "Gullah Geechee Rice Cookbook", "cat": "cooking"},
    {"slug": "gullah-cast-iron", "title": "Gullah Geechee Cast Iron Cooking", "cat": "cooking"},
    {"slug": "gullah-slow-cooker", "title": "Gullah Geechee Slow Cooker Recipes", "cat": "cooking"},
    {"slug": "gullah-30-minute", "title": "Gullah Geechee 30-Minute Meals", "cat": "cooking"},
    {"slug": "gullah-meal-prep", "title": "Gullah Geechee Meal Prep", "cat": "cooking"},
    {"slug": "gullah-kids-cook", "title": "Gullah Geechee Kids Cookbook", "cat": "cooking"},
    {"slug": "gullah-appetizers", "title": "Gullah Geechee Appetizers", "cat": "cooking"},
    {"slug": "gullah-summer-cooking", "title": "Gullah Geechee Summer Cooking", "cat": "cooking"},
    {"slug": "gullah-winter-cooking", "title": "Gullah Geechee Winter Cooking", "cat": "cooking"},
    {"slug": "gullah-cajun", "title": "Gullah Geechee and Cajun Cooking", "cat": "cooking"},
    {"slug": "gullah-caribbean", "title": "Gullah Geechee and Caribbean Cooking", "cat": "cooking"},
    {"slug": "gullah-west-african", "title": "Gullah Geechee and West African Cooking", "cat": "cooking"},
    {"slug": "gullah-fermentation", "title": "Gullah Geechee Fermentation", "cat": "cooking"},
    {"slug": "gullah-gluten-free", "title": "Gullah Geechee Gluten-Free Cooking", "cat": "cooking"},
    {"slug": "gullah-vegan", "title": "Gullah Geechee Vegan Cooking", "cat": "cooking"},
    {"slug": "gullah-keto", "title": "Gullah Geechee Keto Cooking", "cat": "cooking"},
    {"slug": "gullah-paleo", "title": "Gullah Geechee Paleo Cooking", "cat": "cooking"},
    {"slug": "gullah-air-fryer", "title": "Gullah Geechee Air Fryer Recipes", "cat": "cooking"},
    {"slug": "gullah-instant-pot", "title": "Gullah Geechee Instant Pot Recipes", "cat": "cooking"},
    {"slug": "gullah-camping", "title": "Gullah Geechee Camp Cooking", "cat": "cooking"},
]

def generate_etsy_tags(title, category):
    """Generate 13 Etsy tags from the title and category."""
    words = title.lower().replace(":", "").replace(",", "").replace("'", "").split()
    tags = set()
    
    # Add category-specific tags
    if category == "self-help":
        tags.update(["gullah geechee", "self help", "personal development", "cultural heritage", "african american", "lowcountry", "sea islands", "south carolina", "mental wellness", "mindset"])
    elif category == "business":
        tags.update(["gullah geechee", "small business", "entrepreneurship", "cultural heritage", "african american", "lowcountry", "business guide", "side hustle", "financial freedom", "marketing"])
    elif category == "cooking":
        tags.update(["gullah geechee", "soul food", "southern cooking", "lowcountry recipes", "african american", "cookbook", "southern recipes", "soul food cookbook", "lowcountry", "south carolina"])
    
    # Add title-based tags
    for word in words:
        if len(word) > 3 and word not in ["the", "and", "for", "with", "from", "that", "this", "guide", "your"]:
            tags.add(word)
    
    # Add bigrams from title
    for i in range(len(words) - 1):
        bigram = f"{words[i]} {words[i+1]}"
        if len(bigram) > 5:
            tags.add(bigram)
    
    return list(tags)[:13]

def generate_etsy_title(book):
    """Generate an SEO-optimized Etsy title."""
    cat = book["cat"]
    prefix = {
        "self-help": "Gullah Geechee",
        "business": "Gullah Geechee",
        "cooking": "Gullah Geechee"
    }[cat]
    return f"{prefix} {book['title']} - Digital Download PDF Ebook"

def generate_etsy_description(book):
    """Generate a compelling Etsy description."""
    cat_labels = {"self-help": "self-help and personal development", "business": "business and entrepreneurship", "cooking": "cooking and food"}
    
    return f"""Ebook: {book['title']}

by Darryl Elliott Brown - Gullah Geechee Biz

---

ABOUT THIS EBOOK

{book['title']} is a comprehensive guide in the {cat_labels[book['cat']]} category, written from the authentic perspective of the Gullah Geechee community of the South Carolina Lowcountry.

This digital ebook contains 10 chapters of rich, original content - approximately 8,000-12,000 words of practical wisdom, cultural knowledge, and actionable guidance.

---

WHAT YOU GET

- Complete ebook (PDF format)
- 10 in-depth chapters
- Written by Darryl Elliott Brown
- Published by Gullah Geechee Biz
- Instant digital download

---

HOW IT WORKS

1. Purchase this listing
2. Download the PDF from Etsy
3. Open on any device - phone, tablet, computer
4. Read and enjoy

---

ABOUT THE AUTHOR

Darryl Elliott Brown is a Gullah Geechee publisher, author, and cultural advocate from the Lowcountry of South Carolina. Through Gullah Geechee Biz, he works to preserve and share the rich history, food, language, and traditions of the Gullah Geechee people with the world.

---

MORE FROM GULLAH GEECHEE BIZ

Visit gullahgeecheebiz.com for our full catalog of books, recipes, and cultural resources.

(c) {date.today().year} Gullah Geechee Biz. All rights reserved."""

def create_delivery_pdf(book):
    """Create a PDF delivery document for the ebook."""
    pdf = FPDF()
    pdf.add_page()
    
    # Navy background header
    pdf.set_fill_color(10, 10, 20)
    pdf.rect(0, 0, 210, 60, 'F')
    
    # Gold title
    pdf.add_font("ArialUnicode", "", "/System/Library/Fonts/Supplemental/Arial Unicode.ttf", uni=True)
    pdf.set_text_color(212, 175, 55)
    pdf.set_font("ArialUnicode", "", 20)
    pdf.set_y(15)
    pdf.cell(0, 12, "GULLAH GEECHEE BIZ", align="C")
    
    pdf.set_font("ArialUnicode", "", 10)
    pdf.set_y(30)
    pdf.cell(0, 8, "Preserving a Culture. Telling a Story.", align="C")
    
    # Book title
    pdf.set_text_color(240, 237, 229)
    pdf.set_font("ArialUnicode", "", 14)
    pdf.set_y(50)
    pdf.cell(0, 10, book["title"], align="C")
    
    # Thank you section
    pdf.set_text_color(10, 10, 20)
    pdf.set_y(80)
    pdf.set_font("ArialUnicode", "", 16)
    pdf.set_text_color(212, 175, 55)
    pdf.cell(0, 10, "Thank You for Your Purchase!", align="C")
    
    pdf.set_text_color(50, 50, 50)
    pdf.set_font("ArialUnicode", "", 11)
    pdf.set_y(100)
    pdf.multi_cell(0, 7, f"""
Thank you for purchasing "{book['title']}" from Gullah Geechee Biz.

Your download is ready. You can access your ebook file through Etsy's download system.

If you have any questions or issues with your download, please contact us at hello@gullahgeecheebiz.com.

We hope you enjoy this journey into Gullah Geechee culture.

---
About this ebook:
- Title: {book['title']}
- Author: Darryl Elliott Brown
- Publisher: Gullah Geechee Biz
- Category: {book['cat'].title()}
- Format: Digital PDF
- Pages: Approximately 80-120
---

Explore more at gullahgeecheebiz.com
    """.strip())
    
    # Footer
    pdf.set_y(260)
    pdf.set_font("ArialUnicode", "", 8)
    pdf.set_text_color(150, 150, 150)
    pdf.cell(0, 10, f"(c) {date.today().year} Gullah Geechee Biz - gullahgeecheebiz.com", align="C")
    
    # Save
    filename = f"{book['slug']}.pdf"
    filepath = os.path.join(OUT_DIR, "pdfs", filename)
    pdf.output(filepath)
    return filepath

def generate_metadata(book):
    """Generate Etsy listing metadata JSON."""
    title = generate_etsy_title(book)
    tags = generate_etsy_tags(book["title"], book["cat"])
    description = generate_etsy_description(book)
    
    metadata = {
        "title": title,
        "description": description,
        "tags": tags,
        "price": 4.99,
        "quantity": 999,
        "category": "Digital Media",
        "type": "Digital Download",
        "slug": book["slug"],
        "filename": f"{book['slug']}.pdf"
    }
    
    filepath = os.path.join(OUT_DIR, "metadata", f"{book['slug']}.json")
    with open(filepath, "w") as f:
        json.dump(metadata, f, indent=2)
    return filepath

def main():
    print(f"📦 Gullah Geechee Biz — Etsy Product Generator")
    print(f"   Generating PDFs and metadata for {len(EBOOKS)} ebooks...\n")
    
    for i, book in enumerate(EBOOKS, 1):
        # Create delivery PDF
        pdf_path = create_delivery_pdf(book)
        
        # Generate metadata
        meta_path = generate_metadata(book)
        
        print(f"  [{i}/{len(EBOOKS)}] {book['title']}")
    
    print(f"\n✅ All products generated!")
    print(f"   📄 PDFs: {OUT_DIR}/pdfs/ ({len(os.listdir(os.path.join(OUT_DIR, 'pdfs')))} files)")
    print(f"   📋 Metadata: {OUT_DIR}/metadata/ ({len(os.listdir(os.path.join(OUT_DIR, 'metadata')))} files)")
    print(f"\n📎 Sample Etsy listing:")
    sample = EBOOKS[0]
    print(f"   Title: {generate_etsy_title(sample)}")
    print(f"   Tags: {', '.join(generate_etsy_tags(sample['title'], sample['cat']))}")
    print(f"   Price: $4.99")

if __name__ == "__main__":
    main()
