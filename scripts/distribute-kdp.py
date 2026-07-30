#!/usr/bin/env python3
"""
Gullah Geechee Biz — Distribution Bot 1: KDP (Amazon)
Generates KDP-ready submission files for new ebooks.
Output: EPUB + cover + metadata for manual KDP upload.
"""

import json, os, shutil, subprocess
from pathlib import Path
from datetime import datetime

HOME = Path.home()
STATE_DIR = HOME / ".hermes" / "distribution"
KDP_DIR = HOME / "distribution" / "kdp"
KDP_DIR.mkdir(parents=True, exist_ok=True)

def main():
    print("📚 KDP Distribution Bot")
    
    state_file = STATE_DIR / "kdp-state.json"
    submitted = set()
    if state_file.exists():
        with open(state_file) as f:
            submitted = set(json.load(f).get("submitted", []))
    
    # Check for new ebooks
    ebooks_dir = HOME / "ebooks" / "mass"
    pdfs_dir = HOME / "etsy-products" / "ebook-pdfs"
    available = set(f.stem for f in ebooks_dir.glob("*.docx"))
    pending = sorted(available - submitted)
    
    if not pending:
        print("   ✅ No new ebooks to prepare")
        return 0
    
    print(f"   📖 {len(pending)} ebook(s) pending KDP preparation")
    
    prepared = 0
    for slug in pending[:5]:  # Batch of 5
        docx = ebooks_dir / f"{slug}.docx"
        pdf = pdfs_dir / f"{slug}.pdf"
        
        if not pdf.exists():
            print(f"   ⚠️  No PDF for {slug}, skipping")
            continue
        
        # Create KDP submission folder
        out_dir = KDP_DIR / slug
        out_dir.mkdir(parents=True, exist_ok=True)
        
        # Copy PDF
        shutil.copy2(pdf, out_dir / f"{slug}.pdf")
        
        # Generate metadata file
        meta = {
            "title": slug.replace("-", " ").title(),
            "author": "Darryl Elliott Brown",
            "publisher": "Gullah Geechee Biz",
            "isbn": "",
            "categories": [],
            "price": 9.99,
            "description": f"A Gullah Geechee guide to {slug.replace('-', ' ')}.",
            "tags": ["gullah geechee", "african american", "lowcountry", slug.split("-")[0]]
        }
        
        with open(out_dir / "metadata.json", "w") as f:
            json.dump(meta, f, indent=2)
        
        print(f"   ✅ Prepared: {slug}")
        prepared += 1
    
    # Update state
    submitted.update([s for s in pending[:5]])
    with open(state_file, "w") as f:
        json.dump({"submitted": list(submitted), "last_run": str(datetime.now())}, f, indent=2)
    
    print(f"\n   📁 KDP files at: {KDP_DIR}/")
    print(f"   📊 {prepared} ebook(s) prepared for KDP upload")
    return 0

if __name__ == "__main__":
    import sys
    sys.exit(main())
