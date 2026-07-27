// webhook_monitor.js — Gullah Geechee Biz / Publisher_Bot_01
// Verifies Stripe webhooks, logs raw events, alerts Slack on sales.
// Secrets: STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET, SLACK_WEBHOOK_URL (optional)
import fs from 'fs';
import path from 'path';
import fetch from 'node-fetch';
import Stripe from 'stripe';

const stripe = new Stripe(process.env.STRIPE_SECRET_KEY || '', {
  apiVersion: '2022-11-15',
});

const SLACK_WEBHOOK_URL = process.env.SLACK_WEBHOOK_URL || '';
const DATA_DIR = process.env.STRIPE_DATA_DIR || process.cwd();
const RAW_WEBHOOK_FILE =
  process.env.RAW_WEBHOOK_FILE || path.join(DATA_DIR, 'raw_webhooks.jsonl');
const ORDERS_FILE =
  process.env.ORDERS_FILE || path.join(DATA_DIR, 'Orders.jsonl');

async function postSlack(msg) {
  if (!SLACK_WEBHOOK_URL) {
    console.log('[Slack]', msg);
    return;
  }
  try {
    await fetch(SLACK_WEBHOOK_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text: msg }),
    });
  } catch (e) {
    console.error('Slack post failed', e);
  }
}

function appendJsonl(file, obj) {
  try {
    fs.mkdirSync(path.dirname(file), { recursive: true });
    fs.appendFileSync(file, JSON.stringify(obj) + '\n');
  } catch (e) {
    console.error('appendJsonl failed', file, e);
  }
}

/**
 * Netlify/AWS-style handler
 * @param {{ headers: Record<string,string>, body: string }} event
 */
export async function handler(event) {
  const headers = event.headers || {};
  const sig =
    headers['stripe-signature'] ||
    headers['Stripe-Signature'] ||
    headers['stripe-Signature'] ||
    '';

  let stripeEvent;
  try {
    if (!process.env.STRIPE_WEBHOOK_SECRET) {
      throw new Error('STRIPE_WEBHOOK_SECRET not set');
    }
    stripeEvent = stripe.webhooks.constructEvent(
      event.body,
      sig,
      process.env.STRIPE_WEBHOOK_SECRET
    );
  } catch (err) {
    const msg = String(err?.message || err);
    await postSlack(`:warning: GGB Webhook signature verification failed: ${msg}`);
    appendJsonl(RAW_WEBHOOK_FILE, {
      received_at: new Date().toISOString(),
      valid: false,
      error: msg,
      raw_body: typeof event.body === 'string' ? event.body.slice(0, 2000) : null,
    });
    return { statusCode: 400, body: `Webhook error: ${msg}` };
  }

  appendJsonl(RAW_WEBHOOK_FILE, {
    received_at: new Date().toISOString(),
    valid: true,
    event_type: stripeEvent.type,
    id: stripeEvent.id,
  });

  try {
    if (stripeEvent.type === 'checkout.session.completed') {
      const session = stripeEvent.data.object;
      const amount =
        (session.amount_total || session.amount_subtotal || 0) / 100;
      const email = session.customer_details?.email || 'unknown';
      const orderId = session.id;

      await postSlack(
        `NEW SALE — ${amount} USD\nOrder: ${orderId}\nCustomer email: ${email}\nBot: Publisher_Bot_01\nBrand: Gullah Geechee Biz`
      );

      const ordersLine = {
        order_id: orderId,
        created_at: new Date().toISOString(),
        bot_id: 'Publisher_Bot_01',
        slug: session.metadata?.slug || '',
        product_title: session.metadata?.title || '',
        quantity: Number(session.metadata?.quantity || 1),
        gross_amount: amount,
        currency: (session.currency || 'usd').toUpperCase(),
        stripe_fee: null,
        net_amount: null,
        customer_email: email,
        status: 'PAID',
      };
      appendJsonl(ORDERS_FILE, ordersLine);
    }

    return { statusCode: 200, body: 'ok' };
  } catch (procErr) {
    const msg = String(procErr?.message || procErr);
    await postSlack(`:x: GGB Webhook processing error: ${msg}`);
    appendJsonl(RAW_WEBHOOK_FILE, {
      received_at: new Date().toISOString(),
      valid: true,
      event_type: stripeEvent.type,
      processing_error: msg,
    });
    return { statusCode: 500, body: 'processing error' };
  }
}

export default { handler };
