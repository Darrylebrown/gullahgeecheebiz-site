# GGB Stripe / bot ops pack — COMPLETE (Computer 2026-07-27)

| File | Role |
|------|------|
| `webhook_monitor.js` | Verify Stripe sig → Slack sale → Orders.jsonl |
| `dev_webhook_server.js` | Local `localhost:9000/webhook` |
| `stripe_accounting_webhook.js` | Create Checkout sessions (GGB URLs) |
| `create_checkout_cli.js` | CLI checkout helper |
| `bothealth_watcher.js` | Heartbeats → Slack → emergency `.publish_pause` |
| `netlify/functions/stripe-webhook.mjs` | Production function entry (repo root) |

## Hermes still owns
1. Secrets in env (never commit)
2. Netlify (or host) deploy + Stripe webhook URL
3. Cron: bothealth every 10–15m; Stripe maintain daily
4. Bots writing heartbeats.json

Brand: Gullah Geechee Biz · https://gullahgeecheebiz.com/
