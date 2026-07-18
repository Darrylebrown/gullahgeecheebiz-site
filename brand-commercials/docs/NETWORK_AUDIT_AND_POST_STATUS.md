# GGB Publish Network Audit + Brand Promo Post Status
**Date:** 2026-07-18  
**Goal:** Post 3 brand commercials to TikTok @gullahgeecheebiz

## Network audit

| Layer | Status | Detail |
|-------|--------|--------|
| Airtable connector | **OK** | Connected (`airtable_oauth__pipedream`) |
| Content calendar (`apppmxxJ6rnoKpN1K`) | **OK** | Week 1–3 + Merch Launch tables present |
| GGB Pinterest Pin Queue (`app8c8zjl9xLMmwN8`) | **OK** | Pin Queue, GGB Content, Events, Merch Queue |
| Merch Launch M1–M6 | **Queued only** | All 6 still `Scheduled` (none `Posted`) |
| GitHub site repo | **OK** | Public raw video hosting works (HTTP 200) |
| Brand promo videos | **Hosted** | Pushed commit `27669da` to `gullahgeecheebiz-site` |
| Blotato API | **Blocked** | Backend reachable (401 without key); no session credential |
| Replit ggb-publish-queue | **Down** | `ggb-publish-queue.replit.app` → “This app isn't live yet” |
| Local Comet | **Unavailable** | Not connected this session |
| GGB site / shop | **OK** | GitHub Pages 200 |

## Public media URLs (Blotato-ready)

1. Full House  
   https://raw.githubusercontent.com/Darrylebrown/gullahgeecheebiz-site/master/merch/videos/ggb-brand-full-house.mp4

2. Living Record  
   https://raw.githubusercontent.com/Darrylebrown/gullahgeecheebiz-site/master/merch/videos/ggb-brand-living-record.mp4

3. Roots & Rivers Beaufort  
   https://raw.githubusercontent.com/Darrylebrown/gullahgeecheebiz-site/master/merch/videos/ggb-brand-roots-rivers-beaufort.mp4

## Airtable rows created this run

- Content calendar → **Gullah Geechee TikTok - Merch Launch**: BP1, BP2, BP3 (`Scheduled`, `READY_FOR_BLOTATO` notes)
- GGB Pinterest Pin Queue → **GGB Content**: 3 × `[READY] Brand promo…` (`Scheduled`, video Link = raw URL)

## Post path (what still blocks live TikTok)

```
Airtable (queue) ──✓──► Public video URLs ──✓──► Blotato POST /v2/posts ──✗──► TikTok
                                                     needs BLOTATO_API_KEY
```

Blotato payload (per post):
- accountId: `67831c2612959648943d04a6`
- platform/target: `tiktok`
- privacyLevel: `PUBLIC_TO_EVERYONE`
- isAiGenerated: `true`
- isYourBrand: `true`
- isBrandedContent: `false`

## Immediate unblock options

1. **Approve Blotato API key form** in this thread (Settings → API in Blotato)  
2. **Publish Replit** `ggb-publish-queue` with `BLOTATO_API_KEY` secret, then hit `/api/social/merch-batch`  
3. **Comet + Personal Computer** for manual Studio upload  

Until one of those is live, posts remain **queued in Airtable only**.
