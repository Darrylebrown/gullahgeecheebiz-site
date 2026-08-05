#!/usr/bin/env node
const { chromium } = require('playwright');

async function main() {
  const args = process.argv.slice(2);
  const command = args[0];
  const cmdArgs = args.slice(1);

  const browser = await chromium.launch({ headless: false, channel: 'chrome', args: ['--start-maximized'] });
  const page = await (await browser.newContext({ viewport: null })).newPage();

  let result;
  switch (command) {
    case 'goto':
      await page.goto(cmdArgs[0], { waitUntil: 'networkidle', timeout: 30000 });
      result = `URL: ${page.url()}`;
      break;
    case 'screenshot':
      await page.screenshot({ path: cmdArgs[0] || '/tmp/ss.png' });
      result = `Screenshot saved`;
      break;
    case 'fill':
      await page.fill(cmdArgs[0], cmdArgs[1]);
      result = `Filled ${cmdArgs[0]}`;
      break;
    case 'click':
      await page.click(cmdArgs[0]);
      result = `Clicked ${cmdArgs[0]}`;
      break;
    case 'login-d2d':
      await page.goto('https://www.draft2digital.com/login', { waitUntil: 'networkidle' });
      await page.fill('#email', cmdArgs[0]);
      await page.fill('#password', cmdArgs[1]);
      await page.click('button[type="submit"]');
      await page.waitForTimeout(5000);
      await page.goto('https://www.draft2digital.com/book/books', { waitUntil: 'networkidle' });
      await page.screenshot({ path: '/tmp/d2d_after_login.png' });
      result = 'Login attempted, screenshot saved';
      break;
    default:
      result = `Unknown: ${command}`;
  }
  
  console.log(result);
  await new Promise(r => setTimeout(r, 60000));
  await browser.close();
}

main().catch(e => { console.error('Error:', e.message); process.exit(1); });
