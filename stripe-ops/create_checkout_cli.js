#!/usr/bin/env node
// Usage: node create_checkout_cli.js "Binyah Tee" 2999 slug=binyah-tee
import { createSessionDetailed } from './stripe_accounting_webhook.js';

const title = process.argv[2];
const cents = process.argv[3];
if (!title || !cents) {
  console.error('Usage: node create_checkout_cli.js "Title" amount_cents key=val ...');
  process.exit(1);
}
const metadata = {};
for (const a of process.argv.slice(4)) {
  const i = a.indexOf('=');
  if (i > 0) metadata[a.slice(0, i)] = a.slice(i + 1);
}

const rec = await createSessionDetailed(title, cents, metadata);
console.log(JSON.stringify(rec, null, 2));
