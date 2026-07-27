# Gullah Geechee Biz — Bot-Managed Membership System

## Core Principle
Every piece of this system runs on bots. No manual steps. No human intervention. The bots produce, deploy, manage, and report — 24/7, worldwide, zero cost.

## Bot Team

```
                    ┌─────────────────────────────┐
                    │   🧠 ORCHESTRATOR BOT       │
                    │   (Hermes cron: 6 AM daily) │
                    └──────────┬──────────────────┘
                               │
          ┌────────────────────┼──────────────────────┐
          │                    │                      │
          ▼                    ▼                      ▼
   ┌────────────┐      ┌────────────┐      ┌──────────────┐
   │  CONTENT   │      │  DEPLOY    │      │  MEMBERSHIP  │
   │  BOTS     │      │  BOTS     │      │  BOTS       │
   └─────┬──────┘      └─────┬──────┘      └──────┬───────┘
         │                   │                    │
         ▼                   ▼                    ▼
   ┌────────────┐      ┌────────────┐      ┌────────────┐
   │ Pin Factory│      │GitHub Pages│      │  Stripe    │
   │ Book Gen  │      │ Auto-Deploy│      │  Webhooks  │
   │ Audio Atlas│      │            │      │  Portal    │
   └────────────┘      └────────────┘      └────────────┘
```

## Bot Roles

### 🧠 Orchestrator Bot (Daily at 6 AM)
- Wakes up, checks all systems
- Runs the content pipeline
- Triggers deployment
- Reports to owner

### 📌 Content Bots (Run on Schedule)

| Bot | Schedule | Output | Destination |
|-----|----------|--------|-------------|
| **Pin Bot** | 4 AM daily | 100 pins | `member/pins/` |
| **Book Bot** | 3 AM daily | 1 ebook | `member/books/` |
| **Guide Bot** | Weekly | 1 digital guide | `guides/` |
| **Recipe Bot** | Weekly | 5 recipes | `recipes/` |
| **Audio Bot** | Daily | 1 audio piece | `member/audio/` |
| **Map Bot** | Monthly | Corridor map update | `member/map/` |

### 🚀 Deploy Bot (Daily at 7 AM)
- Reads all content buffers
- Generates HTML pages from templates
- Pushes to GitHub Pages
- Verifies deployment worldwide

### 💳 Membership Bot (Continuous)
- Listens for Stripe webhook events
- Grants/revokes member access
- Sends welcome emails
- Reports subscription metrics

### 🛡️ Security Bot (Every 15 min)
- Checks all bot statuses
- Verifies deployments
- Alerts on failures
- Rotates keys if needed

## Bot Communication

```
Content Bots ──→ pins/buffer_ready/ (filesystem bus)
Deploy Bot   ──→ reads buffers → generates HTML → git push
Membership Bot ──→ Stripe webhook → updates member list → git push
Orchestrator  ──→ checks all → reports to owner
```

No database. No API server. The filesystem + git is the bus.

## Deployment Flow (Fully Automated)

```
1. Content Bot finishes → files land in ~/gullahgeecheebiz-site/
2. Deploy Bot wakes up → runs build script
3. Build script generates HTML from templates + content
4. git add, git commit, git push
5. GitHub Pages deploys worldwide (CDN, <30 seconds)
6. Deploy Bot verifies: curl https://gullahgeecheebiz.com/ → 200 OK
7. Deploy Bot logs: "Deployed: 100 pins, 1 book, 5 recipes"
```

## Membership Flow (Fully Automated)

```
1. User visits gullahgeecheebiz.com/membership/
2. User clicks "Subscribe" → Stripe Checkout
3. Stripe processes payment → sends webhook
4. Membership Bot receives webhook → updates member list
5. Deploy Bot picks up member list → regenerates member pages
6. User can access member/ area immediately
7. Monthly: Stripe sends invoice → Membership Bot logs revenue
```

## Bot Status Dashboard

All bots report to `~/.hermes/logs/bot-activity.log`:

```
✅ Pin Bot: 100 pins generated, 0 failed
✅ Book Bot: 1 book generated, 38KB
✅ Deploy Bot: Deployed to GitHub Pages, 200 OK
✅ Membership Bot: 3 active members, $29.97 MRR
✅ Security Bot: All systems healthy
```

## Cron Schedule

| Time | Bot | Job |
|------|-----|-----|
| 3 AM | Book Bot | Generate daily ebook |
| 4 AM | Pin Bot | Generate 100 pins |
| 5 AM | Logo Bot | Generate fresh logos |
| 6 AM | Orchestrator | Run full pipeline |
| 7 AM | Deploy Bot | Push to GitHub Pages |
| 8 AM | Report Bot | Daily summary to owner |
| 9 AM | Health Bot | System check |
| Every 15 min | Security Bot | Watchdog |
| Continuous | Membership Bot | Stripe webhooks |

## Zero-Cost Stack

| Component | Platform | Cost |
|-----------|----------|------|
| Content gen | Pin Factory (local) | Free |
| Hosting | GitHub Pages | Free |
| Payments | Stripe | 2.9% + $0.30/txn |
| Domain | Already owned | $0 |
| Monitoring | Hermes cron | Free |
| CDN | GitHub Pages (Fastly) | Free |
| Email | Substack free tier | Free |

## Revenue Target

$10,000/month = ~500 Digital Pass + ~200 Heritage Pass + ~50 Legacy Pass

All managed by bots. No human labor. No overhead. Pure cultural content, delivered worldwide, automated.
