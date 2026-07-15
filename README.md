# Gullah Geechee Biz — Website

Simple public brand site. Independent of Manus hosting.

- Live (GitHub Pages): https://gullahgeecheebiz.com (after DNS)
- Source: this repo

## Namecheap DNS (cut Manus)

1. Delete any `www` CNAME pointing to `cname.manus.space`
2. Apex `@` A records (GitHub Pages):
   - 185.199.108.153
   - 185.199.109.153
   - 185.199.110.153
   - 185.199.111.153
3. `www` CNAME → `Darrylebrown.github.io`
4. In repo Settings → Pages → Custom domain: `gullahgeecheebiz.com` + Enforce HTTPS
