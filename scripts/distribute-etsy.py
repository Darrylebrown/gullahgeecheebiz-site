#!/usr/bin/env python3
"""
Gullah Geechee Biz — Distribution Bot 3: Etsy
Prepares daily batch of 3 listings with real PDF files.
Output: Ready-to-upload manifests with actual ebook PDFs.
"""

import json, os, shutil
from pathlib import Path
from datetime import date

HOME = Path.home()
STATE_DIR = HOME / ".hermes" / "distribution"
BATCH_DIR = HOME / "distribution" / "etsy" / str(date.today())
BATCH_SIZE = 3

def main():
    print("🛍️  Etsy Distribution Bot")
    
    state_file = STATE_DIR / "etsy-state.json"
    state = {"uploaded": [], "last_run": None, "completed": False}
    if state_file.exists():
        with open(state_file) as f:
            state = json.load(f)
    
    if state["completed"]:
        print("   ✅ All ebooks already uploaded to Etsy")
        return 0
    
    uploaded = set(state["uploaded"])
    
    # Check available ebooks
    ebooks_dir = HOME / "ebooks" / "mass"
    pdfs_dir = HOME / "etsy-products" / "ebook-pdfs"
    all_slugs = sorted(f.stem for f in ebooks_dir.glob("*.docx"))
    pending = [s for s in all_slugs if s not in uploaded]
    
    if not pending:
        state["completed"] = True
        with open(state_file, "w") as f:
            json.dump(state, f, indent=2)
        print("   ✅ All ebooks uploaded to Etsy!")
        return 0
    
    batch = pending[:BATCH_SIZE]
    BATCH_DIR.mkdir(parents=True, exist_ok=True)
    
    print(f"   📖 Today's batch ({len(batch)} listings):")
    
    for slug in batch:
        pdf = pdfs_dir / f"{slug}.pdf"
        if not pdf.exists():
            print(f"   ⚠️  No PDF for {slug}, skipping")
            continue
        
        # Copy the real PDF
        shutil.copy2(pdf, BATCH_DIR / f"{slug}.pdf")
        
        # Generate listing manifest
        manifest = {
            "title": slug.replace("-", " ").title(),
            "price": 4.99,
            "category": slug.split("-")[0] if slug.split("-")[0] in ["gullah", "lowcountry"] else "ebook",
            "tags": ["gullah geechee", "digital download", "ebook", slug.split("-")[0]],
            "description": f"Digital ebook by Darryl Elliott Brown. Published by Gullah Geechee Biz. Instant download.",
            "pdf_file": f"{slug}.pdf",
            "pdf_size_kb": pdf.stat().st_size // 1024
        }
        
        with open(BATCH_DIR / f"{slug}.json", "w") as f:
            json.dump(manifest, f, indent=2)
        
        print(f"      ✅ {slug} — {manifest['pdf_size_kb']}KB PDF ready")
    
    state["uploaded"].extend(batch)
    state["last_run"] = str(date.today())
    with open(state_file, "w") as f:
        json.dump(state, f, indent=2)
    
    remaining = len(all_slugs) - len(state["uploaded"])
    days = (remaining + BATCH_SIZE - 1) // BATCH_SIZE
    print(f"\n   📁 Batch ready at: {BATCH_DIR}/")
    print(f"   📊 Progress: {len(state['uploaded'])}/{len(all_slugs)} uploaded")
    print(f"   ⏱️  Estimated: {days} more days")
    return 0

if __name__ == "__main__":
    import sys
    sys.exit(main())
