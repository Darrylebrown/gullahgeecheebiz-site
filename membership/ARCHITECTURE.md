# Gullah Geechee Biz — Membership Architecture

## Concept
A worldwide digital membership for Gullah Geechee cultural content. Everything we already produce, packaged into subscription tiers. Stripe payments. Deployed on GitHub Pages (free, global CDN).

## Architecture

```
                    ┌─────────────────────────┐
                    │   gullahgeecheebiz.com   │
                    │     (GitHub Pages)       │
                    └──────────┬──────────────┘
                               │
          ┌────────────────────┼────────────────────┐
          │                    │                    │
          ▼                    ▼                    ▼
   ┌────────────┐      ┌────────────┐      ┌────────────┐
   │  Public    │      │  Member    │      │  Admin     │
   │  Site     │      │  Portal    │      │  Dashboard │
   └─────┬──────┘      └─────┬──────┘      └─────┬──────┘
         │                   │                   │
         │                   │                   │
         ▼                   ▼                   ▼
   ┌────────────┐      ┌────────────┐      ┌────────────┐
   │  Stripe    │      │  Stripe    │      │  Stripe    │
   │  Checkout │      │  Portal    │      │  Dashboard │
   └────────────┘      └────────────┘      └────────────┘
```

## Site Structure

```
gullahgeecheebiz.com/
├── index.html              ← Landing / marketing page
├── membership/             ← Membership info + pricing
│   ├── index.html
│   ├── digital-pass.html
│   ├── heritage-pass.html
│   └── legacy-pass.html
├── member/                 ← Member-only area (behind Stripe auth)
│   ├── dashboard.html      ← Member home
│   ├── library.html        ← All content organized
│   ├── pins/               ← Pin archive
│   ├── books/              ← Ebook library
│   ├── guides/             ← Digital guides
│   ├── recipes/            ← Recipe archive
│   ├── map/                ← Corridor map
│   └── audio/              ← Audio atlas
├── guides/                 ← Free digital guides (lead magnets)
│   ├── beaufort.html
│   ├── charleston.html
│   └── ...
├── recipes/                ← Public recipe previews
├── about.html
└── assets/
    ├── css/
    ├── js/
    └── images/
```

## Content Pipeline (Already Running)

```
Pin Factory (daily) ──→ member/pins/     ← 100 pins/day
Book Generator (daily) ──→ member/books/  ← 1 book/day
Digital Guides (on demand) ──→ guides/    ← Lead magnets
Recipe Archive (on demand) ──→ recipes/    ← SEO traffic
Corridor Map (one-time build) ──→ member/map/
Audio Atlas (daily) ──→ member/audio/    ← 1 audio/day
```

## Payment Flow

```
User visits site
  → Sees membership page
  → Clicks "Subscribe"
  → Stripe Checkout (hosted page)
  → Payment processed
  → Stripe webhook → creates member record
  → User redirected to member dashboard
  → Access granted to member/ area
```

## Stripe Integration (No Backend Needed)

- **Stripe Checkout** — hosted payment pages, no backend code
- **Stripe Customer Portal** — members manage their own subscriptions
- **Stripe Webhooks** — listen for subscription events
- **Client-side auth** — Stripe publishes session IDs; member pages check against a simple token or cookie

## Zero-Cost Hosting

| Component | Platform | Cost |
|-----------|----------|------|
| Website | GitHub Pages | Free |
| Payments | Stripe | 2.9% + $0.30 per transaction |
| Content | Pin Factory (local) | Free |
| Email | Substack (free tier) | Free |
| Domain | Already owned | Already paid |

## Revenue Model

| Tier | Price | Est. Members | Monthly Revenue |
|------|-------|-------------|----------------|
| Digital Pass | $9.99/mo | 100 | $999 |
| Heritage Pass | $19.99/mo | 50 | $999 |
| Legacy Pass | $49.99/mo | 20 | $999 |
| **Total** | | **170** | **~$3,000/mo** |

At 1,000 total members: ~$15,000-20,000/mo
At 5,000 total members: ~$75,000-100,000/mo

## Build Order

1. Landing page (index.html) — sell the vision
2. Membership page — pricing tiers, Stripe checkout buttons
3. Member dashboard — simple hub with links to content
4. Content pages — pins, books, guides, recipes, map, audio
5. Stripe webhook handler — grant/revoke access
6. Deploy to GitHub Pages — worldwide in seconds
