# GGB Engine + Hub + Buffer — Architecture

## What This Is

A zero-cost, API-free, active-active workflow automation system that runs entirely on your local machine. No cloud, no subscriptions, no third-party services. Every component has a hot backup — if one instance fails, another takes over instantly.

---

## System Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        GGB HUB (port 8770)                         │
│  Active-Active Registry + Router                                   │
│  ┌─────────────┐  ┌─────────────┐                                  │
│  │  Hub A      │  │  Hub B      │  ← Both live, same state        │
│  │  (Primary)  │  │  (Backup)   │  ← Auto-failover                │
│  └──────┬──────┘  └──────┬──────┘                                  │
│         │                │                                          │
│         └────────────────┘                                          │
│                    │                                                 │
│         ┌──────────┴──────────┐                                      │
│         │   SQLite Database   │  ← Shared state (nodes, routes)     │
│         └─────────────────────┘                                      │
└─────────────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
┌───────────────┐   ┌───────────────┐   ┌───────────────┐
│  GGB ENGINE   │   │  GGB BUFFER   │   │  NEW BUSINESS │
│  (port 8768)  │   │  (port 8769)  │   │  (plugs in)   │
│               │   │               │   │               │
│  Runs         │   │  Job queue    │   │  Registers    │
│  workflows    │   │  Rate limit   │   │  once via     │
│  11 step      │   │  4 workers    │   │  Hub API      │
│  types        │   │  Preloaded    │   │               │
│  Parallel     │   │  schedules    │   │  No rewiring  │
│  execution    │   │  Retry logic  │   │  needed       │
└───────┬───────┘   └───────┬───────┘   └───────┬───────┘
        │                   │                   │
        └───────────────────┼───────────────────┘
                            │
                            ▼
              ┌─────────────────────────┐
              │     OUTPUT CHANNELS     │
              │                         │
              │  • Site (GitHub Pages)  │
              │  • Etsy                 │
              │  • Shopify              │
              │  • TikTok               │
              │  • Instagram            │
              │  • Pinterest            │
              │  • Substack             │
              │  • KDP / D2D / ACX      │
              │  • DistroKid / Spotify  │
              │  • Local files          │
              └─────────────────────────┘
```

---

## Component Breakdown

### 1. GGB Hub (`hub.py`)

**What it does:** Central registry and router. Every business, website, or tool registers here once. The hub remembers what channels each node has and routes content automatically.

**Port:** 8770
**Dashboard:** http://localhost:8770

**Key features:**
- Active-active (two instances, same state)
- Auto-failover (if Hub A dies, Hub B takes over)
- Node registry (add a business once, it's wired forever)
- Content routing (ebooks → Etsy + Shopify, videos → TikTok + Instagram)
- Heartbeat monitoring (every 15 seconds)
- Cross-instance sync (queues changes for peer)

**How to add a new business:**
```
curl "http://localhost:8770/api/register?name=My+New+Business&type=store"
```
Or click "Register Node" on the dashboard.

### 2. GGB Engine (`engine.py`)

**What it does:** Runs workflows. Each workflow is a JSON file with a series of steps. The engine executes them in order, with support for parallel branches, retry logic, and conditional branching.

**Port:** 8768 (webhook server, optional)

**11 step types (all API-free):**
| Step Type | What It Does |
|-----------|-------------|
| `python` | Execute Python code |
| `shell` | Run a shell command |
| `write_file` | Write content to a file |
| `read_file` | Read a file into context |
| `condition` | If/then/else branching |
| `loop` | Iterate over items |
| `sleep` | Wait N seconds |
| `log` | Print a message |
| `parallel` | Run branches simultaneously |
| `retry` | Retry a step on failure |
| `aggregate` | Combine context values |

**How to run a workflow:**
```
python3 engine.py run <workflow-name>
```

**How to start as a server:**
```
python3 engine.py serve          # Primary instance
python3 engine.py serve --backup # Backup instance
```

### 3. GGB Buffer (`buffer.py`)

**What it does:** Job queue with rate limiting, priority, and retry. Sits between cron triggers and workflow execution. Prevents overload and ensures jobs don't get lost.

**Port:** 8769
**Dashboard:** http://localhost:8769

**Key features:**
- Priority queue (higher priority jobs run first)
- Rate limiting (max 10 jobs per minute, configurable)
- 4 parallel workers
- Auto-retry on failure (up to 3 attempts)
- Batch processing (group related jobs)
- Preloaded schedules (6 default schedules)
- Pause/resume (stop the queue without losing jobs)

**Preloaded schedules:**
| Schedule | Time | Workflow |
|----------|------|----------|
| SEO Audit | 6 AM daily | `seo-audit-daily` |
| Distribution AM | 9 AM daily | `distribution-overseer-am` |
| Ad Generator | Every 6 hours | `ad-generator-every-4h` |
| Fable Prompts | Every 6 hours (+15m) | `fable-prompts-every-6h` |
| Traffic Check | Every 6 hours (+45m) | `traffic-check-every-4h` |
| Manus Factory | Monday 8 AM | `manus-factory-weekly` |

---

## How to Add a New Business or Website

### Step 1: Register with the Hub
```bash
curl -X POST http://localhost:8770/api/register \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Your Business Name",
    "type": "store",
    "channels": [
      {"type": "etsy", "name": "Etsy Store"},
      {"type": "shopify", "name": "Shopify Store"}
    ],
    "content_types": ["ebook", "video"]
  }'
```

### Step 2: Add Routing Rules
```bash
curl "http://localhost:8770/api/route?source=<node-id>&content_type=ebook&target=<channel-id>"
```

### Step 3: That's It
The hub handles everything from there. Content flows automatically to the right channels. No scripts to edit, no cron jobs to add, no config files to touch.

---

## Active-Active Failover

```
Normal Operation:
  Hub A (Primary) ──── sync ──── Hub B (Backup)
       │                              │
       │ Both process jobs            │
       │ Both serve dashboards        │
       └──────────────────────────────┘

If Hub A Fails:
  Hub B (Backup) → becomes Primary
       │
       │ Continues processing
       │ No data loss
       │ No manual intervention
       └── Auto-promoted via heartbeat
```

Both instances share the same SQLite database. If one goes down, the other detects the missing heartbeat within 15 seconds and takes over. When the failed instance comes back, it syncs state and resumes as backup.

---

## Port Map

| Port | Service | Purpose |
|------|---------|---------|
| 8765 | Redemption Server | Ebook download codes |
| 8766 | Tracker Server | Page view analytics |
| 8767 | Site Monitor | SEO + traffic monitoring |
| 8768 | Engine Webhook | (removed — API-free) |
| 8769 | Buffer Queue | Job queue + dashboard |
| 8770 | GGB Hub | Registry + router + dashboard |

---

## File Locations

```
~/gullahgeecheebiz-site/ggb-engine/
├── engine.py          # Workflow engine (active-active)
├── buffer.py          # Job queue + rate limiter
├── hub.py             # Registry + router (active-active)
├── workflows/         # 11 workflow definitions
│   ├── master-orchestrator.json
│   ├── daily-book.json
│   ├── daily-logo.json
│   ├── etsy-daily-batch.json
│   ├── publishing-content.json
│   ├── publishing-production.json
│   ├── publishing-distribution.json
│   ├── publishing-promotion.json
│   ├── publishing-health.json
│   ├── daily-pins.json
│   └── soe-marketing-drafts.json
├── logs/              # Workflow execution logs
├── state/             # Engine state files
└── index.html         # Public documentation page

~/.hermes/
├── buffer/            # Buffer queue database
├── hub/               # Hub database + heartbeat
└── distribution/      # Distribution bot state
```

---

## Design Principles

1. **Zero cost** — Everything runs on local hardware. No cloud, no subscriptions, no API keys.
2. **API-free** — No external dependencies. No services that can go away or change their pricing.
3. **Active-active** — Every component has a hot backup. No single point of failure.
4. **Plug and play** — New businesses register once. The hub handles routing automatically.
5. **Self-healing** — Failed jobs retry automatically. Failed instances fail over automatically.
6. **Transparent** — Every component has a live dashboard. You can see exactly what's running, queued, or failed.

---

## Quick Start

```bash
# Start the hub (primary)
cd ~/gullahgeecheebiz-site/ggb-engine
python3 hub.py

# Start the hub (backup — on another machine or terminal)
python3 hub.py --backup

# Start the engine
python3 engine.py serve

# Start the buffer
python3 buffer.py

# Run a workflow
python3 engine.py run master-orchestrator

# Check the dashboards
open http://localhost:8770   # Hub
open http://localhost:8769   # Buffer
```

---

*Built for Gullah Geechee Biz. Zero cost. Always up. Never rewired.*
