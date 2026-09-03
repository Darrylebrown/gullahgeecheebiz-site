# GGB Promotion Orchestrator — Session Report
**Generated:** 2026-09-02 ~04:25 UTC
**Source Bot:** PROMOTION_GOAL

## What happened this run (all verified)

1. **Gumroad catalog audit — 101 products, not 10.** The previous state ("10 live products") was wrong: the Gumroad v2 API is paginated (10/page) and earlier runs only crawled page 1. Full 11-page crawl found **101 products, 96 published**, including heavy duplicates: Vol 06 ×5, Vol 07 ×5, Vol 08 ×4, Vol 09–11 ×3 each, Vol 12–22 ×2 each, Vol 31–34 ×2 each, Box Set ×3, Site License ×4, Heritage Vault ×4. A shop showing 5 copies of Volume 06 hurts trust and conversion. Full id map saved to `/tmp/gumroad_full.json`.

2. **Fixed Volume 34's dead product link.** `https://debtide0.gumroad.com/l/encyclopedia-volume-34` was returning **404** — no product owned that permalink. Assigned it via API (`PUT custom_permalink`) to the $9.99 canonical listing. Verified: now **HTTP 200**. All 10 canonical volume URLs (06–11, 31–34) verified live.

3. **Fixed the Blotato account-id bug (root cause of HTTP 500s).** The poster scripts defaulted to `67831c2612959648943d04a6`, which the API rejects: `invalid input syntax for type bigint`. Verified via `/users/me/accounts` that the TikTok account id is **40117** (`gullahgeecheebiz`). Patched `blotato-poster.py` + `autonomous_blotato_post.py`. Also confirmed the key itself is valid (the 00:00 UTC 401 was a credential-proxy env miss, not an expired key).

4. **Posted 8 product promos to TikTok via Blotato — all HTTP 201 with real submission IDs:** encyclopedia volumes 06, 07, 08, 09, 10, 31, 33, 34, each with its Gumroad CTA caption and product image (media URLs verified 200). Submission IDs recorded in state. Blotato state file now tracks 21 media items posted.

5. **Recorded everything:** 11 events appended to `publish/event_stream.jsonl` (source_bot=PROMOTION_GOAL), `publish/promotion_state.json` updated, `~/.blotato_poster_state.json` updated.

## Status

| Metric | Value |
|---|---|
| TikTok posts this run | 8 (HTTP 201 each) |
| Canonical Gumroad URLs live | 10/10 (HTTP 200) |
| Gumroad listings (API) | 101 total / 96 published / ~30 dupes |
| Sales | still $0 |
| Goal met | **No** — continue |

## Next run (priority order)
1. **Gumroad duplicate cleanup** — unpublish (reversible) ~30 duplicate listings, keep the canonical $9.99 product with the friendly permalink per title. Highest-value step for conversion.
2. Continue Blotato cycling — 4 brand media items left, plus Blotato has Facebook (40385), YouTube (42801), Pinterest (8338), Twitter (22451) accounts connected and available as new channels.
3. Pinterest token refresh / xurl / Substack cookie (manual auth items).
