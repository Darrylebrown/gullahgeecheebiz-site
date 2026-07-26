# Season 1 · Airtable Sync

Airtable is the source of truth for **all 16 Season 1 episode pages**. Edit an
episode in Airtable → run one command → the entire `/season-1/` section
regenerates and can be pushed to GitHub Pages.

- **Base:** [Gullah Geechee Encyclopedia — Production Tracker](https://airtable.com/appr9ojv124GBNCtR)
- **Table:** [Season 1 Episodes](https://airtable.com/appr9ojv124GBNCtR/tblykMJANGPLZQyPi)
- **Renderer:** `scripts/build_season1_site.py` (QA-approved template)
- **Sync tool:** `scripts/sync_from_airtable.py`
- **Local cache / JSON feed:** `season-1/episodes.json`

---

## Editing an episode

1. Open the [Season 1 Episodes table](https://airtable.com/appr9ojv124GBNCtR/tblykMJANGPLZQyPi).
2. Edit any field on the record. **Do not edit the `Slug` field** — the slug is
   the URL and must never change (see "Slug lock" below).
3. Set `Status` to `Published` (green) or `Ready` (yellow) for it to render on
   the site. `Draft` and `Archived` records are hidden.
4. Run the sync (below). Commit + push.

## Fields

| Field | Type | Notes |
|---|---|---|
| Title | text (primary) | Displayed everywhere. |
| Episode Number | number | 1–16. Controls order. |
| **Slug** | text | **LOCKED.** URL segment. Never edit. |
| Premiere Date | YYYY-MM-DD | ISO date. Renders as "Sat Sep 5, 2026". |
| Runtime (min) | number | Integer minutes. Displays as "100 MIN". |
| Era | text | Short subtitle era, e.g. "Reconstruction". |
| Cultural Anchor | text | Short line under premiere date. |
| Hero Line | long text | Big pull-quote at top of episode page. |
| Logline | long text | 1–2 sentence summary. |
| Beat 1 / Beat 2 / Beat 3 | long text | The three beats of the episode. |
| Status | single-select | Draft / Ready / Published / Archived. |
| Production Notes | long text | Optional. Overrides default footer text. |
| Last Synced | datetime | Auto-updated by sync (future). |

---

## Sync commands

Set your token once per shell:

```bash
export AIRTABLE_TOKEN=patXXXXXXXXXXXXXX
```

Create the token at [airtable.com/create/tokens](https://airtable.com/create/tokens)
with scope `data.records:read` on the Encyclopedia base only.

Then:

```bash
# Preview what would change
python3 scripts/sync_from_airtable.py --dry

# Actually pull from Airtable + regenerate all pages
python3 scripts/sync_from_airtable.py

# Rebuild from local cache (no Airtable / no network)
python3 scripts/sync_from_airtable.py --from-cache

# Same as default, but fails hard if token missing (for CI/cron)
python3 scripts/sync_from_airtable.py --ci
```

After the sync, review with `git diff season-1/` and commit as usual.

---

## Slug lock

The URL `/season-1/queen-quet-2000.html` is a **permanent public URL**. Once an
episode has a slug in Airtable, that slug must never change. If you edit an
episode's Slug field, the old URL will 404 and every share link + backlink
breaks.

- The sync tool refuses to run if two episodes share the same slug.
- If you truly need to rename an episode's URL, add a redirect first (via a
  new `<meta http-equiv="refresh">` or `_redirects` file) and only then update
  the slug.

---

## Optional: automated sync (GitHub Actions)

`.github/workflows/sync-season-1.yml` will run this sync every 6 hours and
push any changes automatically. To enable:

1. Repo → **Settings → Secrets and variables → Actions → New repository secret**.
2. Name: `AIRTABLE_TOKEN`. Value: your PAT from
   [airtable.com/create/tokens](https://airtable.com/create/tokens) (scope
   `data.records:read` on the Encyclopedia base only).
3. Actions tab → **Sync Season 1 from Airtable → Enable workflow**.
4. First run: click **Run workflow** to test.

After that, edits in Airtable propagate to the live site within 6 hours with
no command-line work. To disable, just disable the workflow in the Actions
tab — no credentials or code changes needed.

---

## Fallback / offline

`season-1/episodes.json` is committed alongside the HTML. If Airtable is down
or you're offline:

```bash
python3 scripts/sync_from_airtable.py --from-cache
```

rebuilds everything from that file. It's also a JSON feed you can point other
tools at (podcast player, Substack import, etc).
