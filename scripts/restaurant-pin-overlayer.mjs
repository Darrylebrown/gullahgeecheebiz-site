#!/usr/bin/env node
/**
 * Gullah Geechee Biz — Restaurant Pin Overlayer
 * Overlays perfect branding on clean food backgrounds
 */

import sharp from "sharp";
import { readFileSync, writeFileSync, mkdirSync, existsSync, readdirSync } from "fs";
import { join, resolve } from "path";
import { homedir } from "os";

const HOME = homedir();
const BG_DIR = resolve(HOME, "pins-restaurants");
const OUT_DIR = resolve(HOME, "pins-restaurants-final");
if (!existsSync(OUT_DIR)) mkdirSync(OUT_DIR, { recursive: true });

const SVG_EMBLEM = `<svg width="80" height="80" viewBox="0 0 80 80">
  <circle cx="40" cy="40" r="38" fill="none" stroke="#D4AF37" stroke-width="2"/>
  <text x="40" y="36" text-anchor="middle" fill="#D4AF37" font-family="Georgia" font-size="11" font-weight="bold">GULLAH</text>
  <text x="40" y="52" text-anchor="middle" fill="#D4AF37" font-family="Georgia" font-size="11" font-weight="bold">GEECHEE</text>
  <text x="40" y="66" text-anchor="middle" fill="#D4AF37" font-family="Georgia" font-size="7">BIZ</text>
</svg>`;

const restaurants = [
  { name: "Gullah Grub", town: "St. Helena Island", cuisine: "Gullah Soul Food", bg: "bg-shrimp-grits.png" },
  { name: "The Foolish Frog", town: "St. Helena Island", cuisine: "Lowcountry Fare", bg: "bg-catfish.png" },
  { name: "Shrimp Shack", town: "St. Helena Island", cuisine: "Fresh Seafood", bg: "bg-seafood-boil.png" },
  { name: "Hudson's Seafood", town: "Hilton Head", cuisine: "Fresh Catch", bg: "bg-oysters.png" },
  { name: "Skull Creek Boathouse", town: "Hilton Head", cuisine: "Waterfront Seafood", bg: "bg-collards.png" },
  { name: "The Crazy Crab", town: "Hilton Head", cuisine: "Lowcountry Seafood", bg: "bg-sweet-potato-pie.png" },
  { name: "Old Oyster Factory", town: "Hilton Head", cuisine: "Oyster Bar", bg: "bg-red-rice.png" },
];

async function overlayPin(restaurant, index) {
  const bgPath = join(BG_DIR, restaurant.bg);
  if (!existsSync(bgPath)) {
    console.log(`  [SKIP] ${restaurant.name} — background not found`);
    return;
  }

  const name = restaurant.name.toUpperCase();
  const town = `📍 ${restaurant.town}, SC`;
  const cuisine = restaurant.cuisine;

  // Create SVG overlay
  const svgOverlay = `<svg width="1080" height="1920" viewBox="0 0 1080 1920" xmlns="http://www.w3.org/2000/svg">
    <defs>
      <linearGradient id="overlay" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stop-color="rgba(10,20,40,0.7)"/>
        <stop offset="50%" stop-color="rgba(10,20,40,0.3)"/>
        <stop offset="100%" stop-color="rgba(10,20,40,0.85)"/>
      </linearGradient>
    </defs>
    <rect width="1080" height="1920" fill="url(#overlay)"/>
    
    <!-- Top emblem -->
    <circle cx="540" cy="100" r="45" fill="none" stroke="#D4AF37" stroke-width="2"/>
    <text x="540" y="95" text-anchor="middle" fill="#D4AF37" font-family="Georgia" font-size="14" font-weight="bold">GULLAH</text>
    <text x="540" y="112" text-anchor="middle" fill="#D4AF37" font-family="Georgia" font-size="14" font-weight="bold">GEECHEE</text>
    <text x="540" y="128" text-anchor="middle" fill="#D4AF37" font-family="Georgia" font-size="9">BIZ</text>
    
    <!-- Restaurant name -->
    <text x="540" y="900" text-anchor="middle" fill="#D4AF37" font-family="Georgia" font-size="64" font-weight="bold">${name}</text>
    
    <!-- Town -->
    <text x="540" y="970" text-anchor="middle" fill="rgba(255,255,255,0.7)" font-family="Arial" font-size="28">${town}</text>
    
    <!-- Cuisine -->
    <text x="540" y="1020" text-anchor="middle" fill="#F5F0E6" font-family="Georgia" font-size="24" font-style="italic">${cuisine}</text>
    
    <!-- CTA Button -->
    <rect x="340" y="1100" width="400" height="60" rx="30" fill="#D4AF37"/>
    <text x="540" y="1138" text-anchor="middle" fill="#0A1428" font-family="Arial" font-size="22" font-weight="bold">VISIT GULLAHGEECHEEBIZ.COM</text>
    
    <!-- Bottom branding -->
    <text x="540" y="1850" text-anchor="middle" fill="rgba(255,255,255,0.3)" font-family="Georgia" font-size="14">GULLAH GEECHEE BIZ — Preserving a Culture. Telling a Story.</text>
  </svg>`;

  const outPath = join(OUT_DIR, `restaurant-pin-${String(index + 1).padStart(3, "0")}-${restaurant.name.toLowerCase().replace(/[^a-z0-9]/g, "-")}.png`);

  await sharp(bgPath)
    .resize(1080, 1920, { fit: "cover" })
    .composite([
      { input: Buffer.from(svgOverlay), top: 0, left: 0 }
    ])
    .png()
    .toFile(outPath);

  console.log(`  [PIN ${index + 1}] ${restaurant.name} — ${town}`);
}

async function main() {
  console.log("=".repeat(60));
  console.log("  GULLAH GEECHEE BIZ — RESTAURANT PIN OVERLAYER");
  console.log("=".repeat(60));
  console.log();

  for (let i = 0; i < restaurants.length; i++) {
    await overlayPin(restaurants[i], i);
  }

  console.log(`\n✅ ${restaurants.length} restaurant pins generated at:`);
  console.log(`   ${OUT_DIR}`);
  console.log("\nAll pins have Gullah Geechee Biz branding, gold emblem, and CTA.");
}

main().catch(e => console.error("Error:", e.message));
