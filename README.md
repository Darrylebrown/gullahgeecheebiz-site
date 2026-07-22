# Gullah Geechee Biz — Website

Simple public brand site. **Independent of Manus.**

## Live now
- GitHub Pages: https://gullahgeecheebiz.com/
- Perplexity: https://gullah-geechee-biz.pplx.app

## Point GullahGeecheeBiz.com (Namecheap)

Do this in Namecheap → Domain List → Manage → Advanced DNS:

### 1. Cut Manus
- **Delete** any Host `www` CNAME whose value is `cname.manus.space`
- Delete any other Manus A/CNAME records

### 2. Point to GitHub Pages
| Type | Host | Value | TTL |
|------|------|-------|-----|
| A | `@` | `185.199.108.153` | Automatic |
| A | `@` | `185.199.109.153` | Automatic |
| A | `@` | `185.199.110.153` | Automatic |
| A | `@` | `185.199.111.153` | Automatic |
| CNAME | `www` | `Darrylebrown.github.io` | Automatic |

### 3. After DNS propagates (often 5–60 min)
Tell Computer: “DNS is set” — we re-add the GitHub custom domain + HTTPS.

Do **not** re-enable the custom domain on GitHub until Namecheap no longer points at Manus, or visitors stay on the old offline page.
