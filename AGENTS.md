# Gullah Geechee Biz — Site

## Project
Static HTML/CSS site for Gullah Geechee Biz — luxury brand, culture-first. Hosted on GitHub Pages at gullahgeecheebiz.com.

## Tech Stack
- Static HTML + CSS (no framework)
- Node.js scripts (smoke tests, build tools)
- Python scripts (deploy, pin generation, book generation, membership builder)
- GitHub Pages deployment

## Commands
- Test: `npm test` (runs scripts/smoke-test.js)
- Deploy: `python3 scripts/deploy-bot.py`
- Build membership: `python3 scripts/build-membership.py`
- Build season 1: `python3 scripts/build_season1_site.py`
- Daily pins: `python3 scripts/daily-pin-generator.py`
- Daily books: `python3 scripts/daily-book-generator.py`

## Brand
- Colors: Navy + gold
- Accent: Philip Simmons wrought iron
- Tone: Luxury frame, culture picture
- Spelling: Gullah Geechee (not Geechee alone)

## Key Files
- `index.html` — homepage
- `style.css` — global styles
- `scripts/` — all build/deploy/test scripts
- `viral/` — SEO landing pages
- `membership/` — membership tiers ($9.99–$49.99)
- `season-1/` — season content
- `sitemap.xml` — site index

## Boundaries
- Never commit .env files or secrets
- Never modify node_modules
- Run smoke test before deploy
- All scripts in scripts/ are Python unless they end in .js
