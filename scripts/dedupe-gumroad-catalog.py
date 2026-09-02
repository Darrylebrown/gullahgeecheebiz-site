#!/usr/bin/env python3
"""Deduplicate Gumroad catalog: keep site-linked/canonical listing per name, unpublish (disable) the rest.
Reversible — products are disabled, never deleted."""
import requests, json, re, glob, time
from collections import defaultdict
from pathlib import Path

BASE = Path("/Users/darrylsmac/gullahgeecheebiz-site")
API = "https://api.gumroad.com/v2"

def load_token():
    for line in (BASE / ".env").read_text().splitlines():
        if line.startswith("GUMROAD_ACCESS_TOKEN="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise SystemExit("No token")

TOKEN = load_token()

def req(method, url, **kw):
    for attempt in range(5):
        try:
            r = requests.request(method, url, timeout=60, **kw)
            if r.status_code == 429:
                time.sleep(30 + attempt * 20)
                continue
            return r
        except Exception:
            if attempt < 4:
                time.sleep(5 + attempt * 10)
                continue
            raise
    return None

def get_all_products():
    allp, page = [], None
    while True:
        params = {"access_token": TOKEN}
        if page:
            params["page_key"] = page
        r = req("GET", f"{API}/products", params=params)
        if r is None:
            break
        d = r.json()
        allp.extend(d.get("products", []))
        page = d.get("next_page_key")
        if not page:
            break
    return allp

def main():
    dry_run = False  # verified safe: volumes only, canonical permalink kept, none site-linked
    # 1. collect site slugs
    site_slugs = set()
    for f in glob.glob(str(BASE / "**" / "*.html"), recursive=True):
        if "node_modules" in f:
            continue
        try:
            html = open(f, encoding="utf-8", errors="ignore").read()
            for m in re.finditer(r"gumroad\.com/l/([a-zA-Z0-9_-]+)", html):
                site_slugs.add(m.group(1))
        except Exception:
            continue
    print(f"site slugs: {len(site_slugs)}")

    # 2. fetch all products + their short_url / permalink
    prods = get_all_products()
    print(f"total products: {len(prods)}")
    enriched = []
    slug_owners = {}  # slug -> list of (id, name) for pre-flight check
    for p in prods:
        pid = p["id"]
        g = req("GET", f"{API}/products/{pid}", params={"access_token": TOKEN})
        prod = {}
        if g is not None:
            prod = g.json().get("product", {})
        short_url = prod.get("short_url") or p.get("short_url") or ""
        perm = prod.get("custom_permalink") or p.get("custom_permalink") or ""
        slug = re.sub(r"https://debtide0\.gumroad\.com/l/", "", short_url) if short_url else ""
        name = prod.get("name") or p.get("name") or ""
        enriched.append({
            "id": pid,
            "name": name,
            "price": p.get("price", 0),
            "permalink": perm,
            "short_slug": slug,
            "site_linked": slug in site_slugs or perm in site_slugs,
            "file_info": prod.get("file_info"),
        })
        if slug:
            slug_owners.setdefault(slug, []).append((pid[:14], name[:40]))
        if perm:
            slug_owners.setdefault(perm, []).append((pid[:14], name[:40]))

    # pre-flight: every site slug must resolve to at least one product
    unresolved = [s for s in site_slugs if s not in slug_owners]
    print(f"\nPRE-FLIGHT: unresolved site slugs: {unresolved if unresolved else 'NONE — all resolve'}")
    for s in sorted(site_slugs):
        if s in slug_owners:
            print(f"  {s} -> {slug_owners[s]}")

    # 3. group by name — but ONLY dedupe "Encyclopedia Volume N" groups.
    #    Vault/license/box-set have unresolved dashboard slug aliases (yfbgtf, kpwill...)
    #    that could point at any member — leave those groups untouched.
    groups = defaultdict(list)
    for e in enriched:
        groups[e["name"]].append(e)

    import re as _re
    to_disable = []
    kept = []
    for name, es in groups.items():
        is_volume = bool(_re.match(r"^encyclopedia volume \d+$", name, _re.I))
        if len(es) <= 1 or not is_volume:
            kept.extend(es)
            continue
        # canonical = site-linked first, then has permalink, then has files, then lower id
        def rank(e):
            return (
                0 if e["site_linked"] else 1,
                0 if e["permalink"] else 1,
                0 if e["file_info"] else 1,
                0 if e["price"] == 999 else 1,  # prefer canonical $9.99
                e["id"],
            )
        es_sorted = sorted(es, key=rank)
        keep = es_sorted[0]
        for e in es_sorted[1:]:
            to_disable.append(e)
        kept.append(keep)

    print(f"\nkept: {len(kept)} | to disable: {len(to_disable)}")
    # safety: never disable a site-linked product
    dangerous = [e for e in to_disable if e["site_linked"]]
    if dangerous:
        print(f"⚠️ would disable site-linked products: {[e['name'][:40] for e in dangerous]} — ABORT")
        return
    print("no site-linked products in disable list — safe")

    # show summary of what gets disabled
    for e in to_disable[:20]:
        print(f"  DISABLE {e['id'][:16]} | {e['name'][:45]} | ${e['price']/100:.2f}")
    if len(to_disable) > 20:
        print(f"  ... and {len(to_disable)-20} more")

    if dry_run:
        print("\nDRY RUN — not executing. Set dry_run=False to run.")
        json.dump({
            "kept": [{"id": e["id"], "name": e["name"], "price": e["price"]} for e in kept],
            "to_disable": [{"id": e["id"], "name": e["name"], "price": e["price"], "site_linked": e["site_linked"]} for e in to_disable],
        }, open(str(BASE / "publish" / "dedup-dryrun.json"), "w"), indent=2)
        print("saved dedup-dryrun.json")
        return

    # 4. execute disable
    done = 0
    failed = []
    for e in to_disable:
        r = req("PUT", f"{API}/products/{e['id']}/disable", params={"access_token": TOKEN})
        if r is not None and r.json().get("success"):
            done += 1
        else:
            failed.append(e["name"])
        time.sleep(1.5)
    print(f"\n✅ disabled: {done} | failed: {len(failed)}")
    for n in failed[:10]:
        print("  FAIL:", n)

    json.dump({
        "kept": len(kept), "disabled": len(to_disable), "disabled_ok": done,
        "disabled_list": [{"id": e["id"], "name": e["name"], "price": e["price"]} for e in to_disable],
        "failed": failed,
    }, open(str(BASE / "publish" / "dedup-results.json"), "w"), indent=2)

if __name__ == "__main__":
    main()
