#!/usr/bin/env python3
"""
Gullah Geechee Biz — Search Index Builder
Scans all HTML pages and builds a client-side search index.
Output: search-index.json — loaded by the search bar on every page.
"""

import json, os, re
from pathlib import Path
from html.parser import HTMLParser

HOME = Path.home()
SITE_DIR = HOME / "gullahgeecheebiz-site"
OUTPUT = SITE_DIR / "search-index.json"

class PageParser(HTMLParser):
    """Extract title and text content from HTML."""
    def __init__(self):
        super().__init__()
        self.title = ""
        self.in_title = False
        self.in_script = False
        self.in_style = False
        self.text_parts = []
        self._current_tag = ""
    
    def handle_starttag(self, tag, attrs):
        self._current_tag = tag
        if tag == "title":
            self.in_title = True
        elif tag in ("script", "style"):
            self.in_script = True if tag == "script" else self.in_script
            self.in_style = True if tag == "style" else self.in_style
    
    def handle_endtag(self, tag):
        if tag == "title":
            self.in_title = False
        elif tag in ("script", "style"):
            self.in_script = False
            self.in_style = False
    
    def handle_data(self, data):
        if self.in_title:
            self.title += data.strip()
        elif not self.in_script and not self.in_style:
            text = data.strip()
            if text and len(text) > 3:
                self.text_parts.append(text)
    
    def get_text(self):
        return " ".join(self.text_parts)

def build_index():
    pages = []
    
    for html_file in sorted(SITE_DIR.rglob("*.html")):
        # Skip node_modules
        if "node_modules" in str(html_file):
            continue
        
        rel_path = html_file.relative_to(SITE_DIR)
        url = f"/{rel_path}"
        
        # Clean URL (remove index.html)
        if url.endswith("/index.html"):
            url = url[:-10]  # Remove index.html
            if url == "":
                url = "/"
        elif url.endswith(".html"):
            url = url[:-5]  # Remove .html
        
        try:
            with open(html_file, "r", errors="ignore") as f:
                content = f.read()
            
            parser = PageParser()
            parser.feed(content)
            
            title = parser.title or html_file.stem.replace("-", " ").title()
            text = parser.get_text()
            
            # Extract description from meta tags
            desc_match = re.search(r'<meta\s+name="description"\s+content="([^"]+)"', content)
            description = desc_match.group(1) if desc_match else ""
            
            # Extract category from path
            parts = rel_path.parts
            category = parts[0] if len(parts) > 1 else "home"
            
            # Detect content type
            content_type = "page"
            if "recipe" in str(rel_path).lower() or "recipes" in str(rel_path).lower():
                content_type = "recipe"
            elif "ebook" in str(rel_path).lower():
                content_type = "ebook"
            elif "membership" in str(rel_path).lower():
                content_type = "membership"
            elif "shop" in str(rel_path).lower():
                content_type = "shop"
            
            pages.append({
                "url": url,
                "title": title[:100],
                "description": description[:200],
                "category": category,
                "type": content_type,
                "text": text[:500]  # First 500 chars for search
            })
            
        except Exception as e:
            print(f"  ⚠️  {rel_path}: {e}")
    
    # Write index
    index = {
        "pages": pages,
        "total": len(pages),
        "built": str(__import__('datetime').datetime.now().isoformat())
    }
    
    with open(OUTPUT, "w") as f:
        json.dump(index, f, indent=2)
    
    print(f"✅ Search index built: {len(pages)} pages")
    print(f"   Output: {OUTPUT}")
    print(f"   Size: {OUTPUT.stat().st_size // 1024}KB")
    
    return pages

if __name__ == "__main__":
    build_index()
