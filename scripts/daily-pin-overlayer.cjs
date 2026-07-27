#!/usr/bin/env node
/**
 * Gullah Geechee Biz — Daily Pin Overlayer
 * Overlays perfect text + emblem on clean backgrounds
 * Zero cost, highest quality, no AI spelling errors
 */

const sharp = require("sharp");
const { readFileSync, existsSync, mkdirSync } = require("fs");
const { join } = require("path");
const { homedir } = require("os");

const HOME = homedir();
const BG_DIR = join(HOME, "pins-bg");
const OUT_DIR = join(HOME, "pins-daily-output");
const EMBLEM_PATH = join(HOME, "logos-final", "emblem-daily-001.png");
const MANIFEST_DIR = join(HOME, "pins-daily");

mkdirSync(OUT_DIR, { recursive: true });

const GOLD = "rgb(212,175,55)";
const NAVY = "rgb(10,20,40)";
const WHITE = "rgb(255,255,255)";

function makeOverlay(title, subtitle) {
  return Buffer.from(`
    <svg width="1080" height="1920" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <linearGradient id="topGrad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="black" stop-opacity="0.8"/>
          <stop offset="100%" stop-color="black" stop-opacity="0"/>
        </linearGradient>
        <linearGradient id="botGrad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="black" stop-opacity="0"/>
          <stop offset="100%" stop-color="black" stop-opacity="0.85"/>
        </linearGradient>
        <linearGradient id="goldShine" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stop-color="#D4AF37"/>
          <stop offset="50%" stop-color="#FFF8DC"/>
          <stop offset="100%" stop-color="#B8860B"/>
        </linearGradient>
      </defs>
      <rect x="0" y="0" width="1080" height="400" fill="url(#topGrad)"/>
      <rect x="0" y="1200" width="1080" height="720" fill="url(#botGrad)"/>
      <line x1="100" y1="50" x2="980" y2="50" stroke="${GOLD}" stroke-width="2" opacity="0.6"/>
      <text x="540" y="140" text-anchor="middle" font-family="Georgia, serif" font-size="56" font-weight="bold" fill="url(#goldShine)">${escapeXml(title)}</text>
      <line x1="300" y1="170" x2="780" y2="170" stroke="${GOLD}" stroke-width="1.5" opacity="0.4"/>
      <text x="540" y="240" text-anchor="middle" font-family="Georgia, serif" font-size="24" font-style="italic" fill="${WHITE}">${escapeXml(subtitle)}</text>
      <circle cx="540" cy="1480" r="55" stroke="${GOLD}" stroke-width="3" fill="none"/>
      <text x="540" y="1488" text-anchor="middle" font-family="Georgia, serif" font-size="22" font-weight="bold" fill="${GOLD}">GGB</text>
      <text x="540" y="1512" text-anchor="middle" font-family="Georgia, serif" font-size="18" fill="${GOLD}">\u2605</text>
      <text x="540" y="1560" text-anchor="middle" font-family="Georgia, serif" font-size="16" font-weight="bold" fill="${GOLD}">GULLAH GEECHEE BIZ</text>
      <text x="540" y="1585" text-anchor="middle" font-family="Georgia, serif" font-size="13" font-style="italic" fill="${WHITE}">Preserving a Culture. Telling a Story.</text>
      <line x1="200" y1="1610" x2="880" y2="1610" stroke="${GOLD}" stroke-width="1.5" opacity="0.4"/>
      <rect x="340" y="1750" width="400" height="50" rx="25" fill="${GOLD}"/>
      <text x="540" y="1782" text-anchor="middle" font-family="Georgia, serif" font-size="20" font-weight="bold" fill="${NAVY}">Explore gullahgeecheebiz.com</text>
      <path d="M0,0 Q30,0 30,30 Q30,60 0,60" stroke="${GOLD}" stroke-width="2" fill="none" opacity="0.15"/>
      <path d="M1080,0 Q1050,0 1050,30 Q1050,60 1080,60" stroke="${GOLD}" stroke-width="2" fill="none" opacity="0.15"/>
      <path d="M0,1920 Q30,1920 30,1890 Q30,1860 0,1860" stroke="${GOLD}" stroke-width="2" fill="none" opacity="0.15"/>
      <path d="M1080,1920 Q1050,1920 1050,1890 Q1050,1860 1080,1860" stroke="${GOLD}" stroke-width="2" fill="none" opacity="0.15"/>
    </svg>
  `);
}

function escapeXml(s) {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&apos;');
}

async function processPin(pin) {
  const bgPath = join(BG_DIR, pin.filename);
  const outPath = join(OUT_DIR, pin.filename);
  
  if (!existsSync(bgPath)) {
    console.log(`  \u26a0\ufe0f  Background not found: ${pin.filename}`);
    return false;
  }
  
  const overlay = makeOverlay(pin.title, pin.subtitle);
  const composites = [{ input: overlay, top: 0, left: 0 }];
  
  if (existsSync(EMBLEM_PATH)) {
    composites.push({
      input: await sharp(EMBLEM_PATH).resize(80, 80).toBuffer(),
      top: 1440,
      left: 500
    });
  }
  
  await sharp(bgPath)
    .resize(1080, 1920, { fit: 'cover' })
    .composite(composites)
    .png()
    .toFile(outPath);
  
  return true;
}

async function main() {
  console.log("=".repeat(60));
  console.log("  GULLAH GEECHEE BIZ \u2014 DAILY PIN OVERLAYER");
  console.log("=".repeat(60));
  console.log();
  
  // Use today's manifest, or fall back to the latest available
  const today = new Date().toISOString().split('T')[0];
  let manifestPath = join(MANIFEST_DIR, `manifest-${today}.json`);
  
  if (!existsSync(manifestPath)) {
    // Fall back to latest manifest
    const { readdirSync } = require("fs");
    const files = readdirSync(MANIFEST_DIR).filter(f => f.startsWith('manifest-')).sort().reverse();
    if (files.length === 0) {
      console.log(`  \u26a0\ufe0f  No manifest found`);
      process.exit(1);
    }
    manifestPath = join(MANIFEST_DIR, files[0]);
    console.log(`  Using latest manifest: ${files[0]}`);
  }
  
  const manifest = JSON.parse(readFileSync(manifestPath, 'utf-8'));
  const pins = manifest.pins;
  
  console.log(`  Processing ${pins.length} pins for ${today}`);
  console.log();
  
  let ok = 0, fail = 0;
  for (const pin of pins) {
    const result = await processPin(pin);
    if (result) {
      ok++;
      if (ok <= 5 || ok % 20 === 0) {
        console.log(`  \u2705 [${ok}/${pins.length}] ${pin.title}`);
      }
    } else {
      fail++;
    }
  }
  
  console.log();
  console.log(`  Results: ${ok} overlaid, ${fail} skipped`);
  console.log(`  Output: ${OUT_DIR}`);
  console.log("=".repeat(60));
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
