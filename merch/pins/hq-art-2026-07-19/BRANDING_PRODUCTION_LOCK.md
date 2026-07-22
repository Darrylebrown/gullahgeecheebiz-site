# Pin Production Branding Lock (HARDWIRED)

**Status:** LOCKED ops standard — all production pins  
**Date locked:** 2026-07-19  
**Brand:** Gullah Geechee Biz  
**Author (hardwired):** Darryl Elliott Brown  
**Publisher (hardwired):** Gullah Geechee Biz

## Rule

**No pin may enter production (`Pin Status = Ready` or live post) without Gullah Geechee Biz branding.**

This is not optional filler. Savers engage traditional HQ pins that carry the house name.

## Required on every production pin image

1. **Visible brand mark:** `GULLAH GEECHEE BIZ` (chip, seal, or clear type) on the image itself  
2. **Credit bar (preferred):** `Author Darryl Elliott Brown · Publisher Gullah Geechee Biz`  
3. **Culture-first line** allowed: e.g. `Culture first · Traditional Gullah Geechee`  
4. **Airtable `Name` / `Description`:** must include `Gullah Geechee Biz`  
5. **Author line in Description:** `Author Darryl Elliott Brown` (or equivalent hardwired credit)

## Forbidden in production

- Unbranded stock (Unsplash/Pexels/etc.) without GGB overlay  
- Manus CDN assets  
- Free Stack geometric fillers as the **primary** Ready lane (emergency backlog only, and only if brand-locked first)  
- Celebrity name-drops  
- Mock dialect  
- Personal tip-jar framing  
- Side-money / Steady Lane / Morgan Ellis mix-in

## Gate (must pass)

Run before any Airtable Ready import:

```bash
python3 /home/user/workspace/ggb-books/pin-factory/brand_gate.py \
  --dir /path/to/pin/batch \
  --manifest /path/to/MANIFEST.json
```

Exit code **0** = production OK. Non-zero = **do not import**.

## Soft CTA links (allowed)

- Site: https://gullahgeecheebiz.com/  
- Shop: …/shop.html  
- Vol 1: https://www.amazon.com/dp/B0H8M57FBP  
- Blood Remembers: https://www.amazon.com/dp/B0H7WQ69N9  
- Podcast / Substack as culture invites — not tip jar

## Enforcement checklist

- [ ] Image shows **GULLAH GEECHEE BIZ**  
- [ ] Image or metadata credits **Darryl Elliott Brown** + **Gullah Geechee Biz**  
- [ ] `brand_gate.py` passed  
- [ ] Unique Image URL gate vs Ready+Posted  
- [ ] Category is HQ core (Brand / Encyclopedia / Merch / Book) — not anonymous stock  

---

*Named parallel to Free Stack Map and pipeline AUTHOR/PUBLISHER hardwire.*
