#!/usr/bin/env node
/**
 * Gullah Geechee Biz — Payment Audit
 * Static validation only: reads HTML off disk, never opens a network
 * connection, never submits a form, never calls Stripe or Shopify.
 * Run: node scripts/payment-audit.js
 */
const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

const ROOT = path.resolve(__dirname, '..');
const SKIP_DIRS = new Set(['.git', 'node_modules', 'netlify']);

// Pages that intentionally carry no support-lanes band.
const EXCEPTIONS = {
  'ebooks/success.html': 'post-payment download page',
  'redeem/index.html': 'post-purchase code redemption',
  'dashboard/index.html': 'internal revenue dashboard (robots-disallowed)',
  'bot-dashboard.html': 'internal bot dashboard (robots-disallowed)',
};

const MEMBERSHIP_LINKS = {
  'Digital Pass monthly $9.99': 'https://buy.stripe.com/fZu9ASa9E8uFd625OucjS08',
  'Digital Pass annual $99.99': 'https://buy.stripe.com/7sYdR8epU5itfeadgWcjS09',
  'Heritage Pass monthly $19.99': 'https://buy.stripe.com/5kQ7sK5To12dgiegt8cjS0a',
  'Heritage Pass annual $199.99': 'https://buy.stripe.com/00wdR8ftYdOZaXU6SycjS0b',
  'Legacy Pass monthly $49.99': 'https://buy.stripe.com/00wcN41D8eT39TQ7WCcjS0c',
  'Legacy Pass annual $499.99': 'https://buy.stripe.com/eVqdR8epUcKV8PMa4KcjS0d',
};

const MERCH_LINKS = {
  'Binyah Sea Islands Tee $29.99': 'https://buy.stripe.com/28E6oG6XscKVfea90GcjS00',
  'Binyah Tote Bag $24.99': 'https://buy.stripe.com/9B628q4PkfX77LI3GmcjS02',
  'Blood Remembers Tee $29.99': 'https://buy.stripe.com/3cI7sK5ToeT3c1Ya4KcjS03',
  'Lowcountry Sea Islands Tee $28.99': 'https://buy.stripe.com/7sY8wOa9E9yJ4zwccScjS04',
  'Roots & Rivers Mug $18.99': 'https://buy.stripe.com/00w4gya9EeT37LI2CicjS05',
  'Lowcountry Marsh Poster $22.99': 'https://buy.stripe.com/7sYcN4bdIfX79TQ3GmcjS06',
  'Binyah Sticker $4.99': 'https://buy.stripe.com/28E6oGgy2h1b4zw2CicjS07',
};

const SPONSORS = 'https://github.com/sponsors/Darrylebrown';
const LANES_MARKER = 'GGB_SUPPORT_LANES:START';
const LANES_CSS = '/assets/support-lanes.css';

const ALLOWED_STRIPE = new Set(
  [...Object.values(MEMBERSHIP_LINKS), ...Object.values(MERCH_LINKS)].map((u) =>
    u.replace('https://buy.stripe.com/', '')
  )
);

let passed = 0;
let failed = 0;
const ok = (n) => { passed++; console.log(`  ✅ ${n}`); };
const fail = (n, why) => { failed++; console.error(`  ❌ ${n}: ${why}`); };

function walk(dir, out = []) {
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    if (entry.name.startsWith('.') || SKIP_DIRS.has(entry.name)) continue;
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) walk(full, out);
    else if (entry.name.endsWith('.html')) out.push(path.relative(ROOT, full));
  }
  return out;
}

const pages = walk(ROOT).sort();
const read = (rel) => fs.readFileSync(path.join(ROOT, rel), 'utf8');

console.log('Gullah Geechee Biz — Payment Audit\n' + '='.repeat(44));
console.log(`\nPages found: ${pages.length}  |  Documented exceptions: ${Object.keys(EXCEPTIONS).length}\n`);

// 1. Every public page carries the shared payment pathway.
{
  const missingBand = [];
  const missingCss = [];
  const strayBand = [];
  for (const rel of pages) {
    const html = read(rel);
    const hasBand = html.includes(LANES_MARKER);
    if (rel in EXCEPTIONS) {
      if (hasBand) strayBand.push(rel);
      continue;
    }
    if (!hasBand) missingBand.push(rel);
    if (!html.includes(LANES_CSS)) missingCss.push(rel);
  }
  const covered = pages.length - Object.keys(EXCEPTIONS).length;
  missingBand.length === 0
    ? ok(`support lanes: present on all ${covered} public pages`)
    : fail('support lanes', `${missingBand.length} missing — ${missingBand.slice(0, 5).join(', ')}`);
  missingCss.length === 0
    ? ok('support lanes: stylesheet linked on every page')
    : fail('support lanes stylesheet', `${missingCss.length} missing — ${missingCss.slice(0, 5).join(', ')}`);
  strayBand.length === 0
    ? ok('exceptions: correctly excluded from the band')
    : fail('exceptions', `band present on ${strayBand.join(', ')}`);
}

// 2. Every exception is a real file, so the list can't rot silently.
{
  const gone = Object.keys(EXCEPTIONS).filter((rel) => !fs.existsSync(path.join(ROOT, rel)));
  gone.length === 0
    ? ok('exceptions: all documented paths exist')
    : fail('exceptions', `stale entries: ${gone.join(', ')}`);
}

// 3. The four lanes resolve from the band itself.
{
  const sample = read('index.html');
  const lanes = [['/membership/', 'membership'], ['/shop.html', 'merch'], ['/ebooks/', 'ebooks'], [SPONSORS, 'sponsor']];
  const missing = lanes.filter(([href]) => !sample.includes(href)).map(([, name]) => name);
  missing.length === 0
    ? ok('lanes: membership, merch, ebooks, sponsor all reachable')
    : fail('lanes', `missing ${missing.join(', ')}`);
  fs.existsSync(path.join(ROOT, 'membership/index.html')) && fs.existsSync(path.join(ROOT, 'shop.html'))
    ? ok('lanes: internal destinations exist on disk')
    : fail('lanes', 'internal destination page missing');
}

// 4. Membership links land on the membership page, correctly paired.
{
  const mem = read('membership/index.html');
  const missing = Object.entries(MEMBERSHIP_LINKS).filter(([, url]) => !mem.includes(url)).map(([n]) => n);
  missing.length === 0
    ? ok(`membership: all ${Object.keys(MEMBERSHIP_LINKS).length} Stripe links present`)
    : fail('membership links', `missing ${missing.join('; ')}`);

  const prices = ['$9.99', '$99.99', '$19.99', '$199.99', '$49.99', '$499.99'];
  const missingPrice = prices.filter((p) => !mem.includes(p));
  missingPrice.length === 0
    ? ok('membership: displayed prices match the live links')
    : fail('membership prices', `not shown: ${missingPrice.join(', ')}`);

  /Secure payment via Stripe/i.test(mem)
    ? ok('membership: Stripe trust line present')
    : fail('membership', 'trust line missing');

  try {
    execSync('python3 scripts/build-membership.py --check', {
      cwd: ROOT,
      encoding: 'utf8',
      stdio: 'pipe',
    });
    ok('membership: builder and committed page are in sync');
  } catch (e) {
    fail('membership builder', 'membership/index.html is not reproducible from repo source');
  }
}

// 5. Merch links land on the merch pages, correctly paired.
{
  const shop = read('shop.html');
  const missing = Object.entries(MERCH_LINKS).filter(([, url]) => !shop.includes(url)).map(([n]) => n);
  missing.length === 0
    ? ok(`merch: all ${Object.keys(MERCH_LINKS).length} Stripe links present on shop.html`)
    : fail('merch links', `missing ${missing.join('; ')}`);

  const prices = ['$29.99', '$24.99', '$28.99', '$18.99', '$22.99', '$4.99'];
  const missingPrice = prices.filter((p) => !shop.includes(p));
  missingPrice.length === 0
    ? ok('merch: displayed prices match the live links')
    : fail('merch prices', `not shown: ${missingPrice.join(', ')}`);

  /Secure checkout via Stripe/i.test(shop)
    ? ok('merch: Stripe trust line present on shop.html')
    : fail('shop.html', 'trust line missing');

  const binyah = read('shop-binyah.html');
  const binyahLinks = ['GGB-BINYAH-TEE', 'GGB-BINYAH-TOTE', 'GGB-BINYAH-STICKER'];
  const binyahUrls = [MERCH_LINKS['Binyah Sea Islands Tee $29.99'], MERCH_LINKS['Binyah Tote Bag $24.99'], MERCH_LINKS['Binyah Sticker $4.99']];
  binyahUrls.every((u) => binyah.includes(u)) && binyahLinks.every((s) => binyah.includes(s))
    ? ok('merch: shop-binyah.html links and SKUs paired')
    : fail('shop-binyah.html', 'a Binyah link or SKU is missing');
  /Secure checkout via Stripe/i.test(binyah)
    ? ok('merch: Stripe trust line present on shop-binyah.html')
    : fail('shop-binyah.html', 'trust line missing');
}

// 6. The ebook catalog states its real availability and sells nothing it cannot
// deliver. The Shopify store has no published products, so any per-title buy
// CTA or price tag there is a dead purchase path: assert it stays absent until
// the storefront is actually stocked.
{
  const ebooks = read('ebooks/index.html');
  !/buy\.stripe\.com|checkout\.stripe\.com/.test(ebooks)
    ? ok('ebooks: no Stripe checkout claimed for the catalog')
    : fail('ebooks', 'a Stripe checkout URL is present on the ebook page');
  ebooks.includes('gullahgeecheebiz.myshopify.com/collections/roots-rivers-encyclopedia')
    ? ok('ebooks: Roots & Rivers single-title checkout routes to the live Shopify collection')
    : fail('ebooks', 'missing live Roots & Rivers Shopify collection link');
  !/checkout\.stripe\.com|cs_live_/.test(ebooks)
    ? ok('ebooks: no expired Stripe session URLs')
    : fail('ebooks', 'expired Stripe session URL present');
  ebooks.includes('/membership/')
    ? ok('ebooks: membership lane still offered for the catalog library')
    : fail('ebooks', 'no membership route');
  // Whole file, not just the static markup: the 100 cards are built by an
  // inline <script>, so a price restored to that template must fail too.
  !/\$\d/.test(ebooks)
    ? ok('ebooks: no per-title price advertised while checkout is closed')
    : fail('ebooks', 'a price is shown but nothing is purchasable');
  read('shop/index.html').includes('/ebooks/')
    ? ok('shop hub: ebook catalog route linked')
    : fail('shop/index.html', 'ebook catalog route missing');
}

// 7. No expiring Checkout Session URLs anywhere.
{
  const offenders = pages.filter((rel) => /checkout\.stripe\.com\/c\/pay\/cs_(live|test)_/.test(read(rel)));
  offenders.length === 0
    ? ok('stripe: zero single-use cs_ session URLs in HTML')
    : fail('stripe sessions', `${offenders.length} pages — ${offenders.slice(0, 5).join(', ')}`);
}

// 8. Only verified Stripe links ship — an unverified one must not reappear.
{
  const found = new Map();
  for (const rel of pages) {
    for (const m of read(rel).matchAll(/buy\.stripe\.com\/([A-Za-z0-9]+)/g)) {
      if (!ALLOWED_STRIPE.has(m[1])) {
        if (!found.has(m[1])) found.set(m[1], new Set());
        found.get(m[1]).add(rel);
      }
    }
  }
  found.size === 0
    ? ok('stripe: every payment link is on the verified allowlist')
    : fail('stripe allowlist', [...found].map(([id, f]) => `${id} in ${[...f][0]}`).join('; '));
}

// 9. No deceptive or dead-end payment affordances.
{
  // A purchase word inside an anchor whose href is empty, "#", or javascript:.
  const deadCta = /<a\b[^>]*href=["'](?:|#|javascript:[^"']*)["'][^>]*>[^<]*\b(?:Buy|Subscribe|Checkout|Purchase)\b/i;
  const bad = pages.filter((rel) => deadCta.test(read(rel)));
  bad.length === 0
    ? ok('a11y: no purchase buttons pointing nowhere')
    : fail('purchase buttons', `${bad.slice(0, 3).join(', ')}`);

  // Scoped to payment links: those must open safely and announce themselves.
  const payHosts = /buy\.stripe\.com|myshopify\.com|github\.com\/sponsors/;
  const unsafe = pages.filter((rel) =>
    [...read(rel).matchAll(/<a\b[^>]*target=["']_blank["'][^>]*>/gi)].some(
      (m) => payHosts.test(m[0]) && !/rel=["'][^"']*noopener/i.test(m[0])
    )
  );
  unsafe.length === 0
    ? ok('a11y: every payment link opening a new tab carries rel=noopener')
    : fail('payment links', `${unsafe.length} pages — ${unsafe.slice(0, 3).join(', ')}`);
}

// 10. Claims we are not allowed to make about where money goes.
// A percentage only counts as a claim when it is tied to charitable giving —
// wholesale discounts and event splits are ordinary commercial terms.
{
  const CHARITY = '(?:donat\\w*|charit\\w*|food[- ]bank\\w*|homeless\\w*|community support|the cause|nonprofit)';
  const claims = [
    [new RegExp(`\\b\\d{1,3}\\s?%[^.<]{0,80}${CHARITY}`, 'i'), 'fixed-percentage donation claim'],
    [new RegExp(`${CHARITY}[^.<]{0,80}\\b\\d{1,3}\\s?%`, 'i'), 'fixed-percentage donation claim'],
    [/tax[- ]deductible/i, 'tax-deductibility claim'],
  ];
  const hits = [];
  for (const rel of pages) {
    const html = read(rel);
    for (const [re, label] of claims) if (re.test(html)) hits.push(`${label} in ${rel}`);
  }
  hits.length === 0
    ? ok('copy: no percentage or tax-deductibility claims')
    : fail('copy claims', hits.slice(0, 3).join('; '));
}

// 11. Canonical domain for on-site navigation.
{
  const legacy = pages.filter((rel) => read(rel).includes('darrylebrown.github.io'));
  legacy.length === 0
    ? ok('links: no obsolete darrylebrown.github.io references')
    : fail('canonical domain', `${legacy.length} pages — ${legacy.slice(0, 3).join(', ')}`);
}

console.log('\n' + '='.repeat(44));
console.log(`Passed: ${passed}  |  Failed: ${failed}`);
if (failed > 0) {
  console.error('\n❌ PAYMENT AUDIT FAILED');
  process.exit(1);
}
console.log('\n✅ PAYMENT AUDIT PASSED');
process.exit(0);
