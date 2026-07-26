# Autonomous Publish Probe — GGB / Darrylebrown

**Date:** 2026-07-18
**Scope:** Live-probe every candidate Replit deployment, n8n webhook, and Blotato endpoint tied to Darryl Elliott Brown / Gullah Geechee Biz (`Darrylebrown`) automation stack. Report only concrete URLs that return HTTP 200 with JSON.

## Summary verdict

**No live, working GGB-specific publish endpoint currently returns 200 with JSON.** The intended pipeline (Replit → n8n → Blotato) exists on paper and in prior session notes, but every GGB-specific hop is either offline, unregistered, or gated behind a required API key. The only 200-with-JSON responses found are **generic platform health/auth endpoints that are not GGB-specific** and confirm infrastructure exists but is not wired up for public/unauthenticated use.

---

## 1. Replit deployment (`ggb-publish-queue`)

**Claimed live URL (from prior session memory):** `https://ggb-publish-queue.replit.app`

| Probe | Result |
|---|---|
| `GET https://ggb-publish-queue.replit.app` | **HTTP 404** — Replit placeholder page, title "This app isn't live yet" |
| `GET https://ggb-publish-queue.replit.app/api/health` | **HTTP 404** — same placeholder |
| `GET https://ggb-publish-queue.replit.app/api/blotato/verify` | **HTTP 404** — same placeholder |
| `https://ggb-publish-queue.darrylebrown.repl.co` (legacy domain pattern) | DNS does not resolve |
| `https://ggb-publish-queue.darrylebrown.replit.dev` | DNS does not resolve |

**GitHub source repo check:** The repo is documented internally as [`github.com/Darrylebrown/ggb-publish-queue`](https://github.com/Darrylebrown/ggb-publish-queue), but a direct API check returns:
```
GET https://api.github.com/repos/Darrylebrown/ggb-publish-queue → HTTP 404 "Not Found"
```
A full listing of the `Darrylebrown` account's public repos returns only **3 repos**, and `ggb-publish-queue` is not one of them:
- `.github`
- `Darrylebrown`
- `gullahgeecheebiz-site` (homepage: [gullahgeecheebiz.com](https://gullahgeecheebiz.com))

A GitHub code-search for `ggb-publish-queue` as a repo name returns `total_count: 0`. This means the repo referenced in prior internal notes ([ggb-publish-queue project note](https://github.com/Darrylebrown/ggb-publish-queue)) is either private, deleted, or was never pushed publicly — it cannot currently be imported fresh from a public link, and the Replit deployment tied to it is unpublished.

**Conclusion:** No live Replit deployment exists for `ggb-publish-queue`. This matches the last recorded internal status ([NETWORK_AUDIT_AND_POST_STATUS.md](/home/user/workspace/ggb_commercials/NETWORK_AUDIT_AND_POST_STATUS.md)): *"Replit ggb-publish-queue — Down — `ggb-publish-queue.replit.app` → 'This app isn't live yet'."* Nothing has changed since.

---

## 2. n8n cloud webhook for GGB / Blotato

Tested plausible n8n Cloud subdomains tied to the brand name:

| URL | Result |
|---|---|
| `https://darrylebrown.app.n8n.cloud` | HTTP 404 — "No workspace here" |
| `https://ggb.app.n8n.cloud` | HTTP 404 — "No workspace here" |
| **`https://gullahgeecheebiz.app.n8n.cloud`** | **HTTP 200** — confirmed real, live n8n Cloud workspace (title: "n8n.io - Workflow Automation", served via Cloudflare) |

This confirms a **real n8n Cloud instance exists** for the brand — consistent with the internal setup docs ([Replit-Blotato-Live-Setup.md](/home/user/workspace/memory/sessions/2026-07-13_2026-07-19/0088d750/ai_outputs/Replit-Blotato-Live-Setup.md), [Stack-Setup-Replit-n8n-Blotato.md](/home/user/workspace/memory/sessions/2026-07-13_2026-07-19/022f740d/ai_outputs/Stack-Setup-Replit-n8n-Blotato.md)) describing an "all branches" Blotato fan-out workflow (`n8n-All-Branches-Blotato.json`) meant to be imported here.

However, **the root URL is the login/editor UI, not a JSON health endpoint** — it returns `content-type: text/html`, not JSON. Probing every plausible production webhook path returned n8n's standard "not registered" JSON error, meaning no workflow is currently active under a guessable path:

```
/webhook/ggb-book-promote      → 404 not registered
/webhook/health                → 404 not registered
/webhook/ggb-publish           → 404 not registered
/webhook/ggb                   → 404 not registered
/webhook/blotato                → 404 not registered
/webhook/social                 → 404 not registered
/webhook/merch-batch            → 404 not registered
/webhook/ggb-pin                → 404 not registered
/webhook/ggb-publish-queue      → 404 not registered
/rest/login                     → 401 Unauthorized (confirms live n8n REST API, requires auth)
```

n8n Cloud production webhook paths normally include a workflow-specific slug or UUID chosen at creation time and are not guessable from the brand name alone. **No public/documented n8n production webhook URL for GGB/Blotato was found.** If one exists, it has not been published anywhere indexable and must be retrieved directly from inside the n8n workspace (Workflow → Webhook node → "Production URL").

**Conclusion:** The n8n Cloud workspace is live and reachable, but no GGB/Blotato webhook path is publicly discoverable or returns JSON without knowing the exact configured path.

---

## 3. Blotato public API test path (no key required)

Per [Blotato's official API docs](https://help.blotato.com/advanced/api-docs) and [API quickstart](https://help.blotato.com/api/start), the REST base is `https://backend.blotato.com/v2`, and **all functional endpoints require a `blotato-api-key` header** — "Requests without a valid API key will be rejected and a 401 error will be returned."

Direct probes confirm this exactly:

| URL | Result |
|---|---|
| `https://backend.blotato.com` | HTTP 404 JSON — `{"message":"Route GET:/ not found",...}` (server alive, no root route) |
| **`https://backend.blotato.com/health`** | **HTTP 200** — `{"status":"ok"}` — genuine JSON health response |
| `https://backend.blotato.com/v2/health` | HTTP 404 JSON — no `/v2/health` route |
| `https://backend.blotato.com/v2/posts` | HTTP 401 JSON — `{"message":"Unauthorized"}` |
| `https://backend.blotato.com/v2/users/me/accounts` | HTTP 401 JSON — `{"message":"Unauthorized"}` |
| `https://api.blotato.com` | DNS does not resolve (not a valid Blotato host) |

**This confirms the task's hypothesis exactly:** Blotato does expose one unauthenticated, no-key JSON endpoint — `https://backend.blotato.com/health` → `{"status":"ok"}` — which proves the backend is live, but it is a **generic platform liveness check**, not a per-account or GGB-specific test path. Every functional route (`/v2/posts`, `/v2/users/me/accounts`, etc.) requires a real `BLOTATO_API_KEY` and returns 401 without one. There is no free/sandbox key or public test-post path.

---

## Consolidated findings table

| Layer | URL | Live? | Returns 200 JSON? | Notes |
|---|---|---|---|---|
| Replit app | `https://ggb-publish-queue.replit.app` | **No** | No (404 HTML placeholder) | App never published/deployed |
| Replit app `/api/health` | same host | **No** | No | Same placeholder |
| GitHub source repo | `github.com/Darrylebrown/ggb-publish-queue` | **No** | N/A | 404 via GitHub API; not in account's public repo list |
| n8n Cloud workspace | `https://gullahgeecheebiz.app.n8n.cloud` | **Yes** | No (HTML login page) | Real, active n8n Cloud instance — confirms infra exists |
| n8n webhook (any guessed path) | `.../webhook/*` | N/A | No (404 "not registered") | No active/guessable production webhook found |
| Blotato backend root | `https://backend.blotato.com` | Yes | No (404, but valid JSON error) | Confirms server up |
| **Blotato generic health** | **`https://backend.blotato.com/health`** | **Yes** | **Yes — `{"status":"ok"}`** | **Only confirmed 200+JSON endpoint found; generic, not GGB-specific, no auth needed** |
| Blotato posts/accounts API | `https://backend.blotato.com/v2/*` | Yes | No (401, valid JSON error) | Requires real `BLOTATO_API_KEY`; no free/sandbox path exists |

## Bottom line

- **No GGB-specific automation endpoint (Replit deployment, n8n webhook, or Blotato account route) is publicly live and returning 200 with JSON.**
- The **only** concrete URL that returns HTTP 200 with JSON in this entire stack is Blotato's generic platform health check: **`https://backend.blotato.com/health`** → `{"status":"ok"}`. This is not GGB-specific and doesn't require or reveal any account state.
- The n8n Cloud workspace **`https://gullahgeecheebiz.app.n8n.cloud`** is confirmed live and real (HTTP 200, but HTML, not JSON), consistent with the brand's documented automation plan — but no active webhook path is publicly discoverable.
- The Replit deployment and its backing GitHub repo (`Darrylebrown/ggb-publish-queue`) are **not currently live or publicly resolvable** — this matches and reconfirms the last internal audit dated 2026-07-18 ([NETWORK_AUDIT_AND_POST_STATUS.md](/home/user/workspace/ggb_commercials/NETWORK_AUDIT_AND_POST_STATUS.md)).
- Blotato has no free/sandbox public API test path for real posting actions — every functional route requires a genuine `BLOTATO_API_KEY`, confirming the task's assumption.

## Sources

- [Blotato API Quickstart](https://help.blotato.com/api/start)
- [Blotato API Docs — Authentication](https://help.blotato.com/advanced/api-docs)
- [Blotato API Reference for LLMs](https://help.blotato.com/api/llm)
- [GGB Publish Queue internal project note](/home/user/workspace/memory/knowledge/projects/ggb-publish-queue.md)
- [Replit + Blotato Live Setup guide (internal)](/home/user/workspace/memory/sessions/2026-07-13_2026-07-19/0088d750/ai_outputs/Replit-Blotato-Live-Setup.md)
- [Replit/n8n/Blotato Stack Setup (internal)](/home/user/workspace/memory/sessions/2026-07-13_2026-07-19/022f740d/ai_outputs/Stack-Setup-Replit-n8n-Blotato.md)
- [Network Audit and Post Status — 2026-07-18 (internal)](/home/user/workspace/ggb_commercials/NETWORK_AUDIT_AND_POST_STATUS.md)
- [GitHub — Darrylebrown account repos](https://github.com/Darrylebrown?tab=repositories)
- [GitHub — gullahgeecheebiz-site repo](https://github.com/Darrylebrown/gullahgeecheebiz-site)
- Direct live probes performed 2026-07-18 via `curl` against all URLs listed above
