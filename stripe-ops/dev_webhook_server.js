// dev_webhook_server.js — local Stripe webhook receiver for GGB
// Usage: node dev_webhook_server.js
// Point Stripe CLI: stripe listen --forward-to localhost:9000/webhook
import http from 'http';
import { handler } from './webhook_monitor.js';

const PORT = process.env.PORT || 9000;

function parseRawBody(req) {
  return new Promise((resolve, reject) => {
    let body = '';
    req.on('data', (chunk) => (body += chunk));
    req.on('end', () => resolve(body));
    req.on('error', reject);
  });
}

const server = http.createServer(async (req, res) => {
  if (req.method === 'GET' && (req.url === '/' || req.url === '/health')) {
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(
      JSON.stringify({
        ok: true,
        service: 'ggb-stripe-dev-webhook',
        bot: 'Publisher_Bot_01',
        webhook: '/webhook',
      })
    );
    return;
  }

  if (req.url !== '/webhook') {
    res.writeHead(404).end('Not found');
    return;
  }

  const raw = await parseRawBody(req);
  const event = { headers: req.headers, body: raw };
  try {
    const r = await handler(event);
    res.writeHead(r.statusCode || 200, { 'Content-Type': 'text/plain' });
    res.end(r.body || 'OK');
  } catch (e) {
    console.error('handler error', e);
    res.writeHead(500, { 'Content-Type': 'text/plain' });
    res.end('handler error');
  }
});

server.listen(PORT, () =>
  console.log(
    `Local webhook server listening on http://localhost:${PORT}/webhook`
  )
);
