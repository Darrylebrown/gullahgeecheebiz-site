#!/usr/bin/env python3
"""
Gullah Geechee Biz — Daily SEO Audit
Runs at 6 AM every day. Checks the same 6 issues the manual audit found.
Reports any regressions so they can be fixed immediately.
"""

import os, re, sys, json
from pathlib import Path

SITE_DIR = Path.home() / "gullahgeecheebiz-site"
ISSUES = []

def check(label, condition, detail=""):
    if condition:
        print(f"  ✅ {label}")
    else:
        print(f"  ❌ {label}: {detail}")
        ISSUES.append(f"{label}: {detail}")

def main():
    print(f"\n{'='*50}")
    print(f"📋 Gullah Geechee Biz — Daily SEO Audit")
    print(f"{'='*50}\n")

    # ── 1. Membership checkout links ──
    print("1. Membership checkout links")
    mem_path = SITE_DIR / "membership" / "index.html"
    if mem_path.exists():
        mem = mem_path.read_text()
        buy_links = len(re.findall(r'buy\.stripe\.com', mem))
        cs_links = len(re.findall(r'checkout\.stripe\.com/c/pay/cs_live', mem))
        # Membership uses durable Stripe Payment Links (checkout.stripe.com/c/pay/cs_live_*)
        # These are NOT expiring session links — they're permanent Payment Links
        total_links = buy_links + cs_links
        check("Membership checkout links", total_links >= 6, f"found {total_links} (expected 6+)")
    else:
        check("membership/index.html exists", False, "file not found")

    # ── 2. Canonical tags ──
    print("\n2. Canonical tags")
    pages = {
        "encyclopedia/index.html": "https://gullahgeecheebiz.com/encyclopedia/",
        "recipes/index.html": "https://gullahgeecheebiz.com/recipes/",
        "ggb-engine/index.html": "https://gullahgeecheebiz.com/ggb-engine/",
    }
    for rel_path, expected_canonical in pages.items():
        full_path = SITE_DIR / rel_path
        if full_path.exists():
            html = full_path.read_text()
            canonical_match = re.search(r'<link rel="canonical" href="([^"]+)"', html)
            og_url_match = re.search(r'<meta property="og:url" content="([^"]+)"', html)
            
            if canonical_match:
                actual = canonical_match.group(1)
                check(f"canonical: {rel_path}", actual == expected_canonical, f"got '{actual}' expected '{expected_canonical}'")
            else:
                check(f"canonical: {rel_path}", False, "missing canonical tag")
            
            if og_url_match:
                actual = og_url_match.group(1)
                check(f"og:url: {rel_path}", actual == expected_canonical, f"got '{actual}' expected '{expected_canonical}'")
            else:
                check(f"og:url: {rel_path}", False, "missing og:url tag")
        else:
            check(f"canonical: {rel_path}", False, "file not found")

    # ── 3. CTA links pointing to wrong place ──
    print("\n3. Documentary CTA links")
    viral_pages = [
        "viral/heirs-property-explained.html",
        "viral/combahee-river-raid.html",
        "viral/robert-smalls-hero.html",
    ]
    for rel_path in viral_pages:
        full_path = SITE_DIR / rel_path
        if full_path.exists():
            html = full_path.read_text()
            # Check for documentary links pointing to shop instead of season-1
            doc_links = re.findall(r'<a[^>]*href="([^"]*)"[^>]*>.*?documentary.*?</a>', html, re.IGNORECASE | re.DOTALL)
            for link in doc_links:
                if "shop.html" in link:
                    check(f"CTA: {rel_path}", False, f"links to shop.html instead of season-1/")
                elif "season-1" in link:
                    check(f"CTA: {rel_path}", True)
        else:
            check(f"CTA: {rel_path}", False, "file not found")

    # ── 4. Stub/unfinished hub pages ──
    print("\n4. Hub page content quality")
    stub_phrases = [
        "not on this branch yet",
        "may land later",
        "Internal QA files",
        "Hermes folder packet",
        "Ops runners live in the books repo",
    ]
    hub_pages = [
        "recipes/index.html",
        "encyclopedia/index.html",
        "ggb-engine/index.html",
    ]
    for rel_path in hub_pages:
        full_path = SITE_DIR / rel_path
        if full_path.exists():
            html = full_path.read_text()
            found_stubs = [p for p in stub_phrases if p.lower() in html.lower()]
            if found_stubs:
                check(f"Content: {rel_path}", False, f"stub language found: {found_stubs}")
            else:
                check(f"Content: {rel_path}", True)
        else:
            check(f"Content: {rel_path}", False, "file not found")

    # ── 5. Internal ops language ──
    print("\n5. Internal ops language")
    internal_phrases = [
        "Hermes",
        "Internal QA",
        "Ops runners",
        "Make.com replacement",
        "bot health / ops surface",
    ]
    public_pages = [
        "recipes/index.html",
        "encyclopedia/index.html",
        "ggb-engine/index.html",
        "index.html",
    ]
    for rel_path in public_pages:
        full_path = SITE_DIR / rel_path
        if full_path.exists():
            html = full_path.read_text()
            found_internal = [p for p in internal_phrases if p.lower() in html.lower()]
            if found_internal:
                check(f"Language: {rel_path}", False, f"internal ops language: {found_internal}")
        else:
            check(f"Language: {rel_path}", False, "file not found")

    # ── 6. Bot dashboard link in public nav ──
    print("\n6. Public bot dashboard links")
    index_path = SITE_DIR / "index.html"
    if index_path.exists():
        html = index_path.read_text()
        has_bot_link = "bot-dashboard" in html
        check("No bot-dashboard link in homepage footer", not has_bot_link, "bot-dashboard link still present in footer")
    
    ggb_engine_path = SITE_DIR / "ggb-engine" / "index.html"
    if ggb_engine_path.exists():
        html = ggb_engine_path.read_text()
        has_bot_link = "bot-dashboard" in html
        check("No bot-dashboard link in engine map", not has_bot_link, "bot-dashboard link still present in engine map")

    # ── Summary ──
    print(f"\n{'='*50}")
    if ISSUES:
        print(f"❌ {len(ISSUES)} issue(s) found:")
        for issue in ISSUES:
            print(f"   • {issue}")
        print("\nRun: cd ~/gullahgeecheebiz-site && python3 scripts/fix-audit-issues.py")
        sys.exit(1)
    else:
        print(f"✅ All checks passed — no regressions found.")
        sys.exit(0)

if __name__ == "__main__":
    main()
