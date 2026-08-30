// stripe_accounting_webhook.js — create Checkout Sessions for GGB products
// Name is historical (Hermes pack); this is session creation, not the webhook receiver.
// Env: STRIPE_SECRET_KEY
// Optional: STRIPE_SUCCESS_URL, STRIPE_CANCEL_URL
import Stripe from 'stripe';

const stripe = new Stripe(process.env.STRIPE_SECRET_KEY || '', {
  apiVersion: '2022-11-15',
});

const DEFAULT_SUCCESS =
  process.env.STRIPE_SUCCESS_URL ||
  'https://gullahgeecheebiz.com/shop.html?checkout=success';
const DEFAULT_CANCEL =
  process.env.STRIPE_CANCEL_URL ||
  'https://gullahgeecheebiz.com/shop.html?checkout=cancel';

/**
 * Create a one-time Checkout Session and return the hosted URL.
 * @param {string} title - Product name shown on Stripe Checkout
 * @param {number} amount_cents - Unit amount in cents (e.g. 2999 = $29.99)
 * @param {Record<string, string|number>} metadata - Passed through to webhook (slug, title, quantity…)
 * @returns {Promise<string>} session.url
 */
export async function createSession(title, amount_cents, metadata = {}) {
  if (!process.env.STRIPE_SECRET_KEY) {
    throw new Error('STRIPE_SECRET_KEY not set');
  }
  if (!title || typeof title !== 'string') {
    throw new Error('title required');
  }
  const cents = Number(amount_cents);
  if (!Number.isFinite(cents) || cents < 50) {
    throw new Error('amount_cents must be >= 50');
  }

  // Stripe metadata values must be strings
  const meta = {};
  for (const [k, v] of Object.entries(metadata || {})) {
    if (v === undefined || v === null) continue;
    meta[String(k)] = String(v);
  }
  if (!meta.title) meta.title = title;
  if (!meta.bot_id) meta.bot_id = 'Publisher_Bot_01';
  if (!meta.brand) meta.brand = 'Gullah Geechee Biz';

  const session = await stripe.checkout.sessions.create({
    payment_method_types: ['card'],
    line_items: [
      {
        price_data: {
          currency: 'usd',
          product_data: {
            name: title,
            metadata: {
              brand: 'Gullah Geechee Biz',
              site: 'https://gullahgeecheebiz.com/',
            },
          },
          unit_amount: Math.round(cents),
        },
        quantity: 1,
      },
    ],
    mode: 'payment',
    metadata: meta,
    success_url: DEFAULT_SUCCESS,
    cancel_url: DEFAULT_CANCEL,
  });

  if (!session.url) {
    throw new Error('Stripe session created without url');
  }
  return session.url;
}

/**
 * Full session object (id + url) for accounting logs.
 */
export async function createSessionRecord(title, amount_cents, metadata = {}) {
  const url = await createSession(title, amount_cents, metadata);
  // createSession already created; for id we need create once — refactor thin:
  // Re-fetch not needed if callers only want URL. Provide createSessionDetailed below.
  return { url };
}

export async function createSessionDetailed(title, amount_cents, metadata = {}) {
  if (!process.env.STRIPE_SECRET_KEY) {
    throw new Error('STRIPE_SECRET_KEY not set');
  }
  const cents = Number(amount_cents);
  if (!Number.isFinite(cents) || cents < 50) {
    throw new Error('amount_cents must be >= 50');
  }
  const meta = {};
  for (const [k, v] of Object.entries(metadata || {})) {
    if (v === undefined || v === null) continue;
    meta[String(k)] = String(v);
  }
  if (!meta.title) meta.title = title;
  if (!meta.bot_id) meta.bot_id = 'Publisher_Bot_01';
  if (!meta.brand) meta.brand = 'Gullah Geechee Biz';

  const session = await stripe.checkout.sessions.create({
    payment_method_types: ['card'],
    line_items: [
      {
        price_data: {
          currency: 'usd',
          product_data: {
            name: title,
            metadata: {
              brand: 'Gullah Geechee Biz',
              site: 'https://gullahgeecheebiz.com/',
            },
          },
          unit_amount: Math.round(cents),
        },
        quantity: 1,
      },
    ],
    mode: 'payment',
    metadata: meta,
    success_url: DEFAULT_SUCCESS,
    cancel_url: DEFAULT_CANCEL,
  });

  return {
    id: session.id,
    url: session.url,
    amount_cents: Math.round(cents),
    currency: 'usd',
    metadata: meta,
  };
}

export default { createSession, createSessionDetailed };
