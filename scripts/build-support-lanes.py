#!/usr/bin/env python3
"""
Gullah Geechee Biz — shared support / payment lanes builder.

Injects one shared band into every substantive public page so each route has a
visible, truthful path to pay: membership (Stripe), merch (Stripe), ebooks
(Shopify), and sponsorship (GitHub). This file is the single source for that
markup — edit here and re-run, never hand-edit the generated block in a page.

Run: python3 scripts/build-support-lanes.py [--check]
  --check  exit non-zero if any page is out of date (no files written)
"""

import argparse
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

START = "<!-- GGB_SUPPORT_LANES:START -->"
END = "<!-- GGB_SUPPORT_LANES:END -->"
STYLESHEET = '<link rel="stylesheet" href="/assets/support-lanes.css">'

# Pages that intentionally carry no payment lane, with the reason. Post-payment
# and internal operations pages — pushing more checkout at someone who just paid
# (or at an ops dashboard) is noise, and /dashboard/ + /bot-dashboard.html are
# already disallowed in robots.txt.
EXCEPTIONS = {
    "ebooks/success.html": "post-payment download page",
    "redeem/index.html": "post-purchase code redemption",
    "dashboard/index.html": "internal revenue dashboard (robots-disallowed)",
    "bot-dashboard.html": "internal bot dashboard (robots-disallowed)",
}

# Lane order is deliberate: recurring support first, then one-time purchases,
# then the separate open-source sponsorship lane.
LANES = [
    {
        "key": "membership",
        "href": "/membership/",
        "label": "Join the Circle",
        "blurb": "Monthly or annual membership. Secure payment via Stripe.",
        "external": False,
        "current_on": ("membership/index.html",),
    },
    {
        "key": "merch",
        "href": "/shop.html",
        "label": "Shop merchandise",
        "blurb": "Tees, tote, mug, poster, sticker. Secure checkout via Stripe.",
        "external": False,
        "current_on": ("shop.html", "shop-binyah.html", "shop/index.html"),
    },
    {
        "key": "ebooks",
        "href": "https://gullahgeecheebiz.myshopify.com/",
        "label": "Buy ebooks",
        "blurb": "Browse the ebook storefront. Shopify handles checkout for titles that are live there.",
        "external": True,
        "current_on": ("ebooks/index.html",),
    },
    {
        "key": "sponsor",
        "href": "https://github.com/sponsors/Darrylebrown",
        "label": "Sponsor open work",
        "blurb": "Monthly sponsorship on GitHub. Separate from membership.",
        "external": True,
        "current_on": (),
    },
]

LEDE = (
    "Gullah Geechee Biz is independent. Membership, merchandise, and books keep "
    "the archive growing and help sustain the community support work behind it, "
    "including food-bank and homelessness support."
)

FINE = (
    "Memberships and merchandise are processed by Stripe. Ebooks are processed by "
    "Shopify for titles that are live there. Sponsorship is processed by GitHub. Card details are handled by those "
    "providers, never by this site."
)


def render(page_rel):
    """Render the lanes block for one page."""
    items = []
    for lane in LANES:
        current = page_rel in lane["current_on"]
        li_attrs = ' aria-current="true"' if current else ""
        if lane["external"]:
            link = (
                '<a href="{href}" target="_blank" rel="noopener noreferrer">{label}'
                '<span class="ggb-ext" aria-hidden="true">↗</span>'
                '<span class="ggb-sr"> (opens in a new tab)</span></a>'
            ).format(href=lane["href"], label=lane["label"])
        else:
            link = '<a href="{href}">{label}</a>'.format(
                href=lane["href"], label=lane["label"]
            )
        items.append(
            '      <li class="ggb-lane"{attrs}>\n'
            '        <h3 class="ggb-lane-name">{link}</h3>\n'
            "        <p>{blurb}</p>\n"
            "      </li>".format(attrs=li_attrs, link=link, blurb=lane["blurb"])
        )

    return (
        "{start}\n"
        '<aside class="ggb-lanes" aria-labelledby="ggb-lanes-title">\n'
        '  <div class="ggb-lanes-inner">\n'
        '    <h2 class="ggb-lanes-title" id="ggb-lanes-title">Support the work</h2>\n'
        '    <p class="ggb-lanes-lede">{lede}</p>\n'
        '    <ul class="ggb-lanes-grid">\n'
        "{items}\n"
        "    </ul>\n"
        '    <p class="ggb-lanes-fine">{fine}</p>\n'
        "  </div>\n"
        "</aside>\n"
        "{end}"
    ).format(start=START, lede=LEDE, items="\n".join(items), fine=FINE, end=END)


def public_pages():
    """Every tracked public HTML page, repo-relative, sorted."""
    found = []
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [
            d for d in dirnames if d not in (".git", "node_modules", "netlify")
        ]
        for name in filenames:
            if not name.endswith(".html"):
                continue
            rel = os.path.relpath(os.path.join(dirpath, name), ROOT)
            found.append(rel.replace(os.sep, "/"))
    return sorted(found)


def apply_to(page_rel, check_only):
    """Return True if the page is already up to date, else write (or report)."""
    path = os.path.join(ROOT, page_rel)
    with open(path, encoding="utf-8") as fh:
        original = fh.read()

    updated = original

    if page_rel in EXCEPTIONS:
        # Strip the block if a page later becomes an exception.
        updated = re.sub(
            re.escape(START) + r".*?" + re.escape(END) + r"\n?",
            "",
            updated,
            flags=re.DOTALL,
        )
    else:
        block = render(page_rel)
        if START in updated and END in updated:
            updated = re.sub(
                re.escape(START) + r".*?" + re.escape(END),
                lambda _: block,
                updated,
                flags=re.DOTALL,
            )
        else:
            updated = updated.replace("</body>", block + "\n</body>", 1)

        if STYLESHEET not in updated:
            updated = updated.replace("</head>", "  " + STYLESHEET + "\n</head>", 1)

    if updated == original:
        return True
    if not check_only:
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(updated)
    return False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    pages = public_pages()
    stale = [p for p in pages if not apply_to(p, args.check)]

    verb = "out of date" if args.check else "updated"
    print("Gullah Geechee Biz — support lanes")
    print("  pages scanned : {}".format(len(pages)))
    print("  exceptions    : {}".format(len(EXCEPTIONS)))
    print("  {:<14}: {}".format(verb, len(stale)))
    for page in stale:
        print("    - {}".format(page))

    if args.check and stale:
        print("\nRun: python3 scripts/build-support-lanes.py")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
