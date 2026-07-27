/**
 * Netlify Function: POST /.netlify/functions/stripe-webhook
 * Env: STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET, SLACK_WEBHOOK_URL (optional)
 * Note: filesystem logs are ephemeral on Netlify — pair with Slack + external store later.
 */
import { handler as coreHandler } from '../../stripe-ops/webhook_monitor.js';

export async function handler(event) {
  if (event.httpMethod === 'GET') {
    return {
      statusCode: 200,
      body: JSON.stringify({
        ok: true,
        service: 'ggb-stripe-webhook',
        bot: 'Publisher_Bot_01',
      }),
    };
  }
  if (event.httpMethod !== 'POST') {
    return { statusCode: 405, body: 'Method Not Allowed' };
  }

  // Stripe needs raw body for signature verification
  const body = event.isBase64Encoded
    ? Buffer.from(event.body || '', 'base64').toString('utf8')
    : event.body || '';

  const normalized = {
    headers: event.headers || {},
    body,
  };

  const result = await coreHandler(normalized);
  return {
    statusCode: result.statusCode || 200,
    body: result.body || 'ok',
  };
}
