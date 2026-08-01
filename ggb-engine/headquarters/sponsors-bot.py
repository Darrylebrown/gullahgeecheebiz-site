#!/usr/bin/env python3
"""
GGB GitHub Sponsors Bot — sponsorship tiers, automated thank-you messages,
sponsor-only content delivery, and growth automation.
Generates content only. Never posts without owner approval.
"""
import json, sys, uuid
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from headquarters.engine import HQDatabase, CONTENT_DIR, LOGS_DIR

# ─── Sponsorship Tiers ─────────────────────────────────────────────────────

TIERS = [
    {
        "name": "Supporter",
        "amount": 1,
        "description": "Support the mission. Get early access to newsletter content.",
        "benefits": ["Weekly newsletter", "Community access"],
    },
    {
        "name": "Patron",
        "amount": 5,
        "description": "Help us publish more Gullah Geechee stories and recipes.",
        "benefits": ["Everything in Supporter", "Monthly ebook discount code", "Name in acknowledgments"],
    },
    {
        "name": "Guardian",
        "amount": 10,
        "description": "Sustain the publishing pipeline. Get exclusive content.",
        "benefits": ["Everything in Patron", "Early access to new releases", "Behind-the-scenes updates", "Quarterly digital magazine"],
    },
    {
        "name": "Ancestor",
        "amount": 25,
        "description": "Preserve the culture for future generations. Highest tier.",
        "benefits": ["Everything in Guardian", "Personal thank-you video", "Name in every book", "Private community channel", "Monthly 1-on-1 call with publisher"],
    },
]

# ─── Thank-You Templates ───────────────────────────────────────────────────

THANK_YOU_TEMPLATES = {
    "Supporter": """# Thank You for Supporting Gullah Geechee Biz

Dear {sponsor_name},

Thank you for becoming a **{tier}** sponsor. Your support helps us preserve and share Gullah Geechee culture with the world.

## What You Get

{benefits}

## Stay Connected

- [Visit our website](https://gullahgeecheebiz.com)
- [Follow on TikTok](https://www.tiktok.com/@gullahgeecheebiz)
- [Read our books](https://gullahgeecheebiz.com/ebooks)

With gratitude,
*Darryl Elliott Brown*
*Publisher, Gullah Geechee Biz*
""",

    "Patron": """# Thank You for Your Patronage

Dear {sponsor_name},

Thank you for becoming a **{tier}** sponsor. Your support at this level makes a real difference in our ability to publish new works.

## Your Benefits

{benefits}

## Discount Code

Use code **{discount_code}** for {discount}% off any ebook on our website.

With deep gratitude,
*Darryl Elliott Brown*
*Publisher, Gullah Geechee Biz*
""",

    "Guardian": """# Thank You for Being a Guardian

Dear {sponsor_name},

Thank you for becoming a **{tier}** sponsor. As a Guardian, you are helping sustain the entire publishing pipeline.

## Your Exclusive Benefits

{benefits}

## Early Access

You'll receive early access to all new releases before they go public.

With profound gratitude,
*Darryl Elliott Brown*
*Publisher, Gullah Geechee Biz*
""",

    "Ancestor": """# Thank You for Being an Ancestor-Level Sponsor

Dear {sponsor_name},

Thank you for becoming an **{tier}** sponsor. Your support at this level ensures Gullah Geechee culture is preserved for generations to come.

## Your Full Benefits

{benefits}

## Personal Invitation

I would like to invite you to a private 1-on-1 call to discuss our work and how you can be more involved. Please reply to schedule.

With deepest gratitude,
*Darryl Elliott Brown*
*Publisher, Gullah Geechee Biz*
""",
}

class GitHubSponsorsBot:
    """GitHub Sponsors automation — tiers, thank-yous, sponsor-only content."""

    def __init__(self, db: HQDatabase = None):
        self.db = db or HQDatabase()
        self.sponsor_url = "https://github.com/sponsors/Darrylebrown"

    def generate_thank_you(self, sponsor_name: str = "Friend", tier: str = "Supporter") -> dict:
        """Generate a personalized thank-you message for a sponsor."""
        tier_info = next((t for t in TIERS if t["name"] == tier), TIERS[0])
        discount = 10 + (TIERS.index(tier_info) * 5) if TIERS.index(tier_info) > 0 else 0
        discount_code = f"SPONSOR-{uuid.uuid4().hex[:6].upper()}"

        benefits = "\n".join(f"- {b}" for b in tier_info["benefits"])
        template = THANK_YOU_TEMPLATES.get(tier, THANK_YOU_TEMPLATES["Supporter"])

        message = template.format(
            sponsor_name=sponsor_name,
            tier=tier,
            benefits=benefits,
            discount_code=discount_code,
            discount=discount,
        )

        result = {
            "sponsor": sponsor_name,
            "tier": tier,
            "amount": tier_info["amount"],
            "discount_code": discount_code if discount > 0 else None,
            "message": message,
            "generated": datetime.now(timezone.utc).isoformat(),
        }

        output = CONTENT_DIR / f"thank-you-{sponsor_name.lower().replace(' ', '-')}-{uuid.uuid4().hex[:6]}.md"
        output.write_text(message)
        self.db.log_content("sponsors", "thank_you", f"Thank you: {sponsor_name} ({tier})", str(output))
        return result

    def generate_sponsor_only_content(self, tier: str = "Guardian") -> dict:
        """Generate sponsor-only content for a specific tier."""
        content = {
            "Supporter": "Weekly newsletter preview and community updates.",
            "Patron": "Monthly behind-the-scenes look at the publishing pipeline.",
            "Guardian": "Early access to new releases and quarterly digital magazine.",
            "Ancestor": "Private community channel, monthly 1-on-1 calls, name in every book.",
        }

        post = {
            "title": f"Sponsor-Only: {tier} Content",
            "tier": tier,
            "content": content.get(tier, "Exclusive sponsor content."),
            "generated": datetime.now(timezone.utc).isoformat(),
        }

        output = CONTENT_DIR / f"sponsor-only-{tier.lower()}-{uuid.uuid4().hex[:6]}.md"
        output.write_text(f"# {post['title']}\n\n{post['content']}")
        self.db.log_content("sponsors", "sponsor_only", post["title"], str(output))
        return post

    def sponsorship_report(self) -> dict:
        """Generate a sponsorship strategy report."""
        stats = self.db.get_stats()
        return {
            "platform": "GitHub Sponsors",
            "url": self.sponsor_url,
            "tiers": len(TIERS),
            "tier_details": TIERS,
            "monthly_range": f"${TIERS[0]['amount']} - ${TIERS[-1]['amount']}/month",
            "content_generated": stats.get("by_type", {}).get("thank_you", 0),
            "growth_tactics": [
                "Automated thank-you messages per tier",
                "Sponsor-only content pipeline",
                "Discount codes for Patron+ tiers",
                "Personal 1-on-1 calls for Ancestor tier",
                "Name in acknowledgments for all tiers",
                "Early access to new releases",
                "Quarterly digital magazine for Guardian+",
                "Cross-promotion from Substack newsletter",
            ],
        }


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="GGB GitHub Sponsors Bot")
    parser.add_argument("--json", action="store_true")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("report", help="Sponsorship strategy report")
    thank = sub.add_parser("thank", help="Generate thank-you message")
    thank.add_argument("--name", default="Friend")
    thank.add_argument("--tier", default="Supporter", choices=[t["name"] for t in TIERS])
    sponsor = sub.add_parser("content", help="Generate sponsor-only content")
    sponsor.add_argument("--tier", default="Guardian", choices=[t["name"] for t in TIERS])

    args = parser.parse_args()
    bot = GitHubSponsorsBot()

    if args.command == "report":
        result = bot.sponsorship_report()
    elif args.command == "thank":
        result = bot.generate_thank_you(args.name, args.tier)
    elif args.command == "content":
        result = bot.generate_sponsor_only_content(args.tier)

    if args.json:
        print(json.dumps(result, indent=2, default=str))
    else:
        if isinstance(result, dict):
            for k, v in result.items():
                if k == "message":
                    print(f"\n{v}\n")
                elif k == "tier_details":
                    for t in v:
                        print(f"  {t['name']:>12} | ${t['amount']}/mo | {t['description']}")
                elif isinstance(v, list):
                    print(f"{k}:")
                    for item in v:
                        print(f"  - {item}")
                else:
                    print(f"{k}: {v}")
        else:
            print(result)
