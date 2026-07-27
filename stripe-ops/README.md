# GGB Stripe webhook monitor (Publisher_Bot_01)

Verifies Stripe signatures, logs events, posts **NEW SALE** to Slack, appends `Orders.jsonl`.

## Env (never commit secrets)

| Variable | Required |
|----------|----------|
| `STRIPE_SECRET_KEY` | yes |
| `STRIPE_WEBHOOK_SECRET` | yes |
| `SLACK_WEBHOOK_URL` | optional (logs to console if empty) |

## Local

```bash
cd stripe-ops && npm i
# run behind any host that calls handler({ headers, body })
```

## Netlify

1. Connect `gullahgeecheebiz-site` or deploy this folder with `netlify.toml`.
2. Set env vars in Netlify UI.
3. Stripe Dashboard → Developers → Webhooks → endpoint:
   `https://<your-netlify-site>/.netlify/functions/stripe-webhook`
4. Events: at least `checkout.session.completed`
5. Copy **Signing secret** → `STRIPE_WEBHOOK_SECRET`

## GitHub Pages note

gullahgeecheebiz.com on Pages **cannot** receive Stripe webhooks.  
Payment Links still work; **this function must live on Netlify/Replit/Fly** (or Hermes internal cloud).

## Ephemeral disk

On Netlify, `Orders.jsonl` may not persist across invokes. **Slack is the durable alert**; later wire Orders → Sheet/Airtable.

## Brand

Gullah Geechee Biz · https://gullahgeecheebiz.com/  
No secrets in public HTML.

## Local dev server

```bash
cd stripe-ops && npm i
export STRIPE_SECRET_KEY=sk_test_...
export STRIPE_WEBHOOK_SECRET=whsec_...   # from: stripe listen
export SLACK_WEBHOOK_URL=               # optional
npm run dev:webhook
# → http://localhost:9000/webhook
# health: http://localhost:9000/health

stripe listen --forward-to localhost:9000/webhook
stripe trigger checkout.session.completed
```

## Create Checkout Session (dynamic)

```js
import { createSession } from './stripe_accounting_webhook.js';
const url = await createSession('Binyah Tee', 2999, { slug: 'binyah-tee', title: 'Binyah Tee' });
// redirect customer to url
```

CLI:
```bash
export STRIPE_SECRET_KEY=sk_test_...
npm run checkout -- "Binyah Tee" 2999 slug=binyah-tee
```

Success/cancel default to `https://gullahgeecheebiz.com/shop.html?checkout=…`  
Override with `STRIPE_SUCCESS_URL` / `STRIPE_CANCEL_URL`.

Metadata on the session is what `webhook_monitor.js` reads on `checkout.session.completed`.
