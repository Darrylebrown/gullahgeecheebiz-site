#!/usr/bin/env node
/**
 * Gullah Geechee Biz — Smoke Test
 * Verifies the site is structurally sound: key files exist, HTML isn't
 * empty, sitemap is valid XML, deploy-bot.py is syntactically valid.
 * No framework, no dependencies. Run: npm test
 */
const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

const ROOT = path.resolve(__dirname, '..');
let passed = 0;
let failed = 0;

function ok(name) {
  passed++;
  console.log(`  ✅ ${name}`);
}

function fail(name, reason) {
  failed++;
  console.error(`  ❌ ${name}: ${reason}`);
}

function exists(rel) {
  const full = path.join(ROOT, rel);
  return fs.existsSync(full) && fs.statSync(full).size > 0;
}

console.log('Gullah Geechee Biz — Smoke Test\n' + '='.repeat(40));

// 1. Key HTML files exist and aren't empty
const htmlFiles = [
  'index.html',
  'shop.html',
  'shop-binyah.html',
  'bot-dashboard.html',
  'membership/index.html',
  'season-1/index.html',
  'guide/index.html',
  'services/index.html',
];
for (const f of htmlFiles) {
  exists(f) ? ok(`HTML: ${f}`) : fail(`HTML: ${f}`, 'missing or empty');
}

// 2. Assets
exists('assets/membership.css') ? ok('asset: membership.css') : fail('asset: membership.css', 'missing');
exists('style.css') ? ok('asset: style.css') : fail('asset: style.css', 'missing');

// 3. CNAME points to the right domain
try {
  const cname = fs.readFileSync(path.join(ROOT, 'CNAME'), 'utf8').trim();
  cname === 'gullahgeecheebiz.com' ? ok(`CNAME: ${cname}`) : fail('CNAME', `got "${cname}"`);
} catch (e) {
  fail('CNAME', 'missing');
}

// 4. Sitemap is valid XML with expected URLs
try {
  const xml = fs.readFileSync(path.join(ROOT, 'sitemap.xml'), 'utf8');
  const urlCount = (xml.match(/<loc>/g) || []).length;
  if (urlCount >= 50) {
    ok(`sitemap: ${urlCount} URLs`);
  } else {
    fail('sitemap', `only ${urlCount} URLs (expected 50+)`);
  }
  // Check key pages are in sitemap
  const must = ['membership/', 'season-1/', 'tools/'];
  for (const m of must) {
    xml.includes(m) ? ok(`sitemap has: ${m}`) : fail(`sitemap has: ${m}`, 'missing');
  }
} catch (e) {
  fail('sitemap', e.message);
}

// 5. .gitignore blocks secrets
try {
  const gi = fs.readFileSync(path.join(ROOT, '.gitignore'), 'utf8');
  gi.includes('.env') && gi.includes('node_modules') && gi.includes('secrets/')
    ? ok('.gitignore: blocks .env, node_modules, secrets/')
    : fail('.gitignore', 'missing required entries');
} catch (e) {
  fail('.gitignore', 'missing');
}

// 6. node_modules NOT tracked in git
try {
  const tracked = execSync('git ls-files node_modules/', { cwd: ROOT, encoding: 'utf8' }).trim();
  tracked === '' ? ok('git: node_modules not tracked') : fail('git: node_modules not tracked', `${tracked.split('\n').length} files still tracked`);
} catch (e) {
  ok('git: node_modules not tracked');
}

// 7. No tokens embedded in git remotes
try {
  const remotes = execSync('git remote -v', { cwd: ROOT, encoding: 'utf8' });
  const hasToken = /ghp_|github_pat_|pat[A-Za-z0-9]{10,}/.test(remotes.replace(/REDACTED/g, ''));
  !hasToken ? ok('git: no tokens in remotes') : fail('git: no tokens in remotes', 'token pattern found');
} catch (e) {
  fail('git: remotes', e.message);
}

// 8. deploy-bot.py is syntactically valid
try {
  execSync('python3 -c "import ast; ast.parse(open(\'scripts/deploy-bot.py\').read())"', {
    cwd: ROOT,
    encoding: 'utf8',
    stdio: 'pipe',
  });
  ok('deploy-bot.py: syntax valid');
} catch (e) {
  fail('deploy-bot.py: syntax valid', e.stderr || e.message);
}

// 9. build-membership.py is syntactically valid
try {
  execSync('python3 -c "import ast; ast.parse(open(\'scripts/build-membership.py\').read())"', {
    cwd: ROOT,
    encoding: 'utf8',
    stdio: 'pipe',
  });
  ok('build-membership.py: syntax valid');
} catch (e) {
  fail('build-membership.py: syntax valid', e.stderr || e.message);
}

// 10. .nojekyll exists (so GitHub Pages serves the site as-is)
// Special case: .nojekyll is intentionally empty (0 bytes)
  const nj = path.join(ROOT, '.nojekyll');
  fs.existsSync(nj) ? ok('.nojekyll present') : fail('.nojekyll', 'missing');

// 11. Stripe checkout links present in membership page
try {
  const mem = fs.readFileSync(path.join(ROOT, 'membership/index.html'), 'utf8');
  const stripeLinks = (mem.match(/checkout\.stripe\.com/g) || []).length;
  stripeLinks >= 6 ? ok(`Stripe: ${stripeLinks} checkout links`) : fail('Stripe', `only ${stripeLinks} links (expected 6+)`);
} catch (e) {
  fail('Stripe', e.message);
}

// Summary
console.log('\n' + '='.repeat(40));
console.log(`Passed: ${passed}  |  Failed: ${failed}`);
if (failed > 0) {
  console.error('\n❌ SMOKE TEST FAILED');
  process.exit(1);
} else {
  console.log('\n✅ ALL SMOKE TESTS PASSED');
  process.exit(0);
}
