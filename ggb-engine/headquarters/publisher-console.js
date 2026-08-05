#!/usr/bin/env node
/**
 * GGB Publisher Console — Browser Control Hub
 * Controls Chrome via CDP. Connects to existing logged-in sessions.
 * 
 * Usage: node publisher-console.js <command> [args]
 * 
 * Commands:
 *   connect     — Connect to Chrome and list all tabs
 *   books       — Open Draft2Digital books page (in existing Chrome)
 *   scan [url]  — Scan a page and report its content
 *   fill [tab] [selector] [value] — Fill a form field
 *   click [tab] [selector] — Click an element
 */
const { chromium } = require('playwright');

const CDP_URL = 'http://127.0.0.1:9222';

async function connectToChrome() {
  try {
    const browser = await chromium.connectOverCDP(CDP_URL);
    return browser;
  } catch (e) {
    console.log('⚠️  Cannot connect to Chrome via CDP.');
    console.log('   Start Chrome with:');
    console.log('   open -a "Google Chrome" --args --remote-debugging-port=9222');
    return null;
  }
}

async function listTabs(browser) {
  const contexts = browser.contexts();
  let allPages = [];
  for (const context of contexts) {
    allPages = allPages.concat(context.pages());
  }
  
  console.log(`\n📊 ${allPages.length} tab(s) found:\n`);
  for (let i = 0; i < allPages.length; i++) {
    const page = allPages[i];
    const url = page.url();
    const title = await page.title().catch(() => '(no title)');
    const icon = url.includes('draft2digital') ? '📖' :
                 url.includes('gumroad') ? '🛍️' :
                 url.includes('google') ? '🔍' :
                 url.includes('amazon') ? '📦' :
                 url.includes('shopify') ? '🏪' : '🌐';
    console.log(`  [${i}] ${icon} ${title.substring(0, 60)}`);
    console.log(`      ${url.substring(0, 90)}`);
    console.log();
  }
  return allPages;
}

async function main() {
  const cmd = process.argv[2] || 'connect';
  
  switch (cmd) {
    case 'connect': {
      const browser = await connectToChrome();
      if (browser) {
        await listTabs(browser);
        console.log('✅ Connected! I can control any tab above.');
        await browser.close();
      }
      break;
    }
    
    case 'open': {
      const url = process.argv[3];
      if (!url) { console.log('Usage: node publisher-console.js open <url>'); break; }
      
      // Launch a new Chrome window that I control
      const browser = await chromium.launch({ 
        headless: false, 
        channel: 'chrome',
        args: ['--start-maximized', '--disable-blink-features=AutomationControlled']
      });
      const page = await (await browser.newContext({ viewport: null })).newPage();
      await page.goto(url, { waitUntil: 'networkidle', timeout: 30000 });
      console.log(`✅ Opened: ${url}`);
      console.log(`   Title: ${await page.title()}`);
      
      // Keep alive for commands
      console.log('   Browser open. Closing in 60s...');
      setTimeout(() => browser.close(), 60000);
      break;
    }
    
    default:
      console.log('Commands: connect, open <url>');
  }
}

main().catch(e => console.error('Error:', e.message));
