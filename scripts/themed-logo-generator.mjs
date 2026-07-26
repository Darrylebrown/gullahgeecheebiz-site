#!/usr/bin/env node
/**
 * Gullah Geechee Biz — Themed Logo Generator
 * Bridges, Churches, Oak Trees — all with gold branding
 */

import sharp from "sharp";
import { existsSync, mkdirSync } from "fs";
import { join, resolve } from "path";
import { homedir } from "os";

const HOME = homedir();
const BG_DIR = resolve(HOME, "logos");
const OUT_DIR = resolve(HOME, "logos-themed");
if (!existsSync(OUT_DIR)) mkdirSync(OUT_DIR, { recursive: true });

const themes = [
  // Bridges
  { file: "bridge-cooper-river.png", name: "Cooper River Bridge", location: "Charleston, SC", theme: "Bridges" },
  { file: "bridge-hilton-head.png", name: "Hilton Head Bridge", location: "Hilton Head, SC", theme: "Bridges" },
  { file: "bridge-savannah.png", name: "Talmadge Memorial Bridge", location: "Savannah, GA", theme: "Bridges" },
  { file: "bridge-swing.png", name: "Lowcountry Swing Bridge", location: "Sea Islands, SC", theme: "Bridges" },
  { file: "bridge-beaufort.png", name: "Woods Memorial Bridge", location: "Beaufort, SC", theme: "Bridges" },
  // Churches
  { file: "church-st-helena.png", name: "St. Helena Island Church", location: "St. Helena Island, SC", theme: "Churches" },
  { file: "church-penn-center.png", name: "Penn Center Chapel", location: "St. Helena Island, SC", theme: "Churches" },
  { file: "church-charleston.png", name: "Historic Charleston Church", location: "Charleston, SC", theme: "Churches" },
  { file: "church-lowcountry.png", name: "Lowcountry Country Church", location: "Sea Islands, SC", theme: "Churches" },
  { file: "church-savannah.png", name: "Historic Savannah Church", location: "Savannah, GA", theme: "Churches" },
  // Oak Trees
  { file: "oak-live-oak.png", name: "Lowcountry Live Oak", location: "Sea Islands, SC", theme: "Oak Trees" },
  { file: "oak-angel.png", name: "Angel Oak Tree", location: "Johns Island, SC", theme: "Oak Trees" },
  { file: "oak-avenue.png", name: "Oak Avenue", location: "Lowcountry, SC", theme: "Oak Trees" },
  { file: "oak-marsh.png", name: "Marsh Oak", location: "Sea Islands, SC", theme: "Oak Trees" },
  { file: "oak-sunrise.png", name: "Sunrise Oak", location: "Lowcountry, SC", theme: "Oak Trees" },
];

async function overlayLogo(item) {
  const bgPath = join(BG_DIR, item.file);
  if (!existsSync(bgPath)) {
    console.log(`  [SKIP] ${item.name} — not found`);
    return;
  }

  const svgOverlay = `<svg width="1080" height="1080" viewBox="0 0 1080 1080" xmlns="http://www.w3.org/2000/svg">
    <defs>
      <linearGradient id="shadow" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stop-color="rgba(0,0,0,0.35)"/>
        <stop offset="100%" stop-color="rgba(0,0,0,0.1)"/>
      </linearGradient>
    </defs>
    <rect width="1080" height="1080" fill="url(#shadow)"/>
    
    <!-- Outer ring -->
    <circle cx="540" cy="380" r="170" fill="none" stroke="#D4AF37" stroke-width="3"/>
    <circle cx="540" cy="380" r="165" fill="none" stroke="#D4AF37" stroke-width="1" opacity="0.5"/>
    
    <!-- Star -->
    <polygon points="540,270 553,335 618,335 573,375 585,445 540,400 495,445 507,375 462,335 527,335" fill="#D4AF37"/>
    
    <!-- GULLAH text -->
    <text x="540" y="455" text-anchor="middle" fill="#D4AF37" font-family="Georgia" font-size="30" font-weight="bold" letter-spacing="6">GULLAH</text>
    
    <!-- GEECHEE text -->
    <text x="540" y="490" text-anchor="middle" fill="#D4AF37" font-family="Georgia" font-size="30" font-weight="bold" letter-spacing="6">GEECHEE</text>
    
    <!-- BIZ text -->
    <text x="540" y="520" text-anchor="middle" fill="#D4AF37" font-family="Georgia" font-size="18" font-weight="bold" letter-spacing="4">BIZ</text>
    
    <!-- Item name -->
    <text x="540" y="590" text-anchor="middle" fill="#F5F0E6" font-family="Georgia" font-size="26" font-weight="bold">${item.name}</text>
    
    <!-- Location -->
    <text x="540" y="625" text-anchor="middle" fill="rgba(255,255,255,0.6)" font-family="Georgia" font-size="18">📍 ${item.location}</text>
    
    <!-- Theme tag -->
    <text x="540" y="660" text-anchor="middle" fill="rgba(255,255,255,0.4)" font-family="Georgia" font-size="16" font-style="italic">Gullah Geechee ${item.theme}</text>
    
    <!-- Bottom branding -->
    <text x="540" y="1000" text-anchor="middle" fill="rgba(255,255,255,0.3)" font-family="Georgia" font-size="12">GULLAH GEECHEE BIZ — Preserving a Culture. Telling a Story.</text>
  </svg>`;

  const outPath = join(OUT_DIR, `logo-${item.theme.toLowerCase().replace(/\s+/g, "-")}-${item.file.replace(/^(bridge-|church-|oak-)/, "").replace(".png", "")}.png`);

  await sharp(bgPath)
    .resize(1080, 1080, { fit: "cover" })
    .composite([
      { input: Buffer.from(svgOverlay), top: 0, left: 0 }
    ])
    .png()
    .toFile(outPath);

  console.log(`  [${item.theme}] ${item.name} — ${outPath.split("/").pop()}`);
}

async function main() {
  console.log("=".repeat(60));
  console.log("  GULLAH GEECHEE BIZ — THEMED LOGO GENERATOR");
  console.log("=".repeat(60));
  console.log();

  for (const item of themes) {
    await overlayLogo(item);
  }

  console.log(`\n✅ ${themes.length} themed logos generated at:`);
  console.log(`   ${OUT_DIR}`);
  console.log("\nThemes: Bridges (5), Churches (5), Oak Trees (5)");
}

main().catch(e => console.error("Error:", e.message));
