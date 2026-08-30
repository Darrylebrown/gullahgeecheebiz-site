#!/usr/bin/env python3
"""
GGB Inventory Manager — Stock Check & Refill Generator
Checks inventory across all stores and auto-generates products when needed.

Thresholds:
  - Digital stores (Stripe, Etsy, Shopify): 90 minimum, 100 target
  - KDP: 5 minimum, 7 target
"""
import json
import sys
from pathlib import Path
from datetime import datetime

HOME = Path.home()
SITE_DIR = HOME / "gullahgeecheebiz-site"
SCRIPTS_DIR = SITE_DIR / "scripts"
EBOOKS_DIR = HOME / "ebooks" / "mass"
STATE_DIR = HOME / ".hermes" / "distribution"
OUTPUT_DIR = HOME / "ebooks" / "generated"

# ─── Thresholds ─────────────────────────────────────────────────────────────
DIGITAL_THRESHOLD = 90
DIGITAL_TARGET = 100
KDP_THRESHOLD = 5
KDP_TARGET = 7


def load_state(name: str) -> dict:
    path = STATE_DIR / f"{name}-state.json"
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return {"submitted": [], "uploaded": [], "last_run": None}


def get_total_catalog() -> int:
    """Count total ebooks in the mass catalog."""
    if not EBOOKS_DIR.exists():
        return 0
    return len(list(EBOOKS_DIR.glob("*.docx")))


def get_existing_slugs() -> set:
    """Get slugs of all existing ebooks."""
    if not EBOOKS_DIR.exists():
        return set()
    return {f.stem for f in EBOOKS_DIR.glob("*.docx")}


def check_store_inventory(store_name: str, thresholds: dict) -> dict:
    """Check inventory for a specific store."""
    threshold = thresholds["threshold"]
    target = thresholds["target"]
    
    total_catalog = get_total_catalog()
    
    if store_name == "stripe":
        # Stripe: all catalog items available
        stock = total_catalog
        status = "healthy" if stock >= threshold else "below_threshold"
        return {
            "store": store_name,
            "stock": stock,
            "threshold": threshold,
            "target": target,
            "status": status,
            "deficit": max(0, target - stock),
        }
    
    elif store_name == "etsy":
        # Etsy: count uploaded listings
        state = load_state("etsy")
        uploaded = len(state.get("uploaded", []))
        pending = total_catalog - uploaded
        stock = uploaded  # Current active listings
        status = "healthy" if stock >= threshold else "below_threshold"
        return {
            "store": store_name,
            "stock": stock,
            "pending_to_upload": pending,
            "threshold": threshold,
            "target": target,
            "status": status,
            "deficit": max(0, threshold - stock),
            "notes": "Distribution in progress (3/day)" if pending > 0 else "",
        }
    
    elif store_name == "shopify":
        # Shopify: mirrors Stripe
        stock = total_catalog
        status = "healthy" if stock >= threshold else "below_threshold"
        return {
            "store": store_name,
            "stock": stock,
            "threshold": threshold,
            "target": target,
            "status": status,
            "deficit": max(0, target - stock),
        }
    
    elif store_name == "kdp":
        # KDP: count submitted titles
        state = load_state("kdp")
        submitted = len(state.get("submitted", []))
        stock = submitted
        status = "healthy" if stock >= threshold else "below_threshold"
        return {
            "store": store_name,
            "stock": stock,
            "threshold": threshold,
            "target": target,
            "status": status,
            "deficit": max(0, threshold - stock),
        }
    
    return {"store": store_name, "error": "Unknown store"}


def main():
    print("=" * 70)
    print("📦 GGB Inventory Manager Report")
    print(f"   Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    print()
    
    # Check all stores
    stores_config = {
        "stripe": {"threshold": DIGITAL_THRESHOLD, "target": DIGITAL_TARGET},
        "etsy": {"threshold": DIGITAL_THRESHOLD, "target": DIGITAL_TARGET},
        "shopify": {"threshold": DIGITAL_THRESHOLD, "target": DIGITAL_TARGET},
        "kdp": {"threshold": KDP_THRESHOLD, "target": KDP_TARGET},
    }
    
    results = {}
    for store, config in stores_config.items():
        results[store] = check_store_inventory(store, config)
    
    # Print stock table
    print("📊 STOCK STATUS")
    print("-" * 70)
    print(f"  {'Store':<12} {'Stock':>8} {'Threshold':>10} {'Target':>8} {'Status':>20}")
    print("-" * 70)
    
    stores_below_threshold = []
    
    for store, data in results.items():
        stock = data.get("stock", "N/A")
        threshold = data.get("threshold", "N/A")
        target = data.get("target", "N/A")
        status = data.get("status", "unknown")
        
        icon = "✅" if status == "healthy" else "⚠️"
        status_label = "HEALTHY" if status == "healthy" else "BELOW THRESHOLD"
        
        print(f"  {icon} {store.capitalize():<11} {stock:>8} {threshold:>10} {target:>8} {status_label:>20}")
        
        if status == "below_threshold":
            stores_below_threshold.append((store, data))
    
    print("-" * 70)
    print()
    
    # Summary
    print("📋 SUMMARY")
    print("-" * 70)
    print(f"  Total ebooks in catalog: {get_total_catalog()}")
    print(f"  Stores checked: 4")
    print(f"  Stores healthy: {4 - len(stores_below_threshold)}")
    print(f"  Stores below threshold: {len(stores_below_threshold)}")
    print()
    
    # Actions needed
    if stores_below_threshold:
        print("⚠️  STORES NEEDING ATTENTION")
        print("-" * 70)
        
        for store, data in stores_below_threshold:
            deficit = data.get("deficit", 0)
            pending = data.get("pending_to_upload", 0)
            
            print(f"  📌 {store.capitalize()}:")
            print(f"     Current stock: {data['stock']} / Threshold: {data['threshold']}")
            print(f"     Deficit: {deficit} products needed")
            
            if store == "etsy" and pending > 0:
                print(f"     Pending distribution: {pending} ebooks in queue")
                print(f"     Distribution rate: 3 listings/day")
                days_to_threshold = (deficit + 2) // 3
                print(f"     ETA to threshold: ~{days_to_threshold} days")
                print(f"     Action: Continue daily distribution (no new products needed)")
            else:
                print(f"     Action: Generate {deficit} new ebooks")
            print()
    else:
        print("✅ ALL STORES ABOVE THRESHOLD — Inventory healthy")
    
    # Final status
    print()
    print("=" * 70)
    if stores_below_threshold:
        print(f"⚠️  ALERT: {len(stores_below_threshold)} store(s) below threshold")
        return 1
    else:
        print("✅ Inventory check complete — all stores healthy")
        return 0


if __name__ == "__main__":
    sys.exit(main())
