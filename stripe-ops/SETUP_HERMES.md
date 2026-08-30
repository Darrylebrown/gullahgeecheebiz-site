# Hermes — finish Stripe webhook (owner away from terminal)

Computer landed code in repo. You still need **secrets + host**:

1. [ ] Choose host: Netlify functions (recommended) or always-on Mac/VPS
2. [ ] `npm i` in `stripe-ops/` on host
3. [ ] Set env: STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET, SLACK_WEBHOOK_URL
4. [ ] Stripe webhook URL → function endpoint; event `checkout.session.completed`
5. [ ] Test with Stripe CLI: `stripe trigger checkout.session.completed`
6. [ ] Confirm Slack “NEW SALE” + no signature errors
7. [ ] Daily maintain cron: hit GET health URL + Stripe dashboard failed webhooks

Do not commit `.env` or keys.
