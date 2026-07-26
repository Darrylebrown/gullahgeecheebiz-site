#!/usr/bin/env node
/**
 * Gullah Geechee Biz — Animal Logo Overlayer
 * Overlays gold emblem on beautiful animal photography
 */

import sharp from "sharp";
import { existsSync, mkdirSync } from "fs";
import { join, resolve } from "path";
import { homedir } from "os";

const HOME = homedir();
const BG_DIR = resolve(HOME, "logos");
const OUT_DIR = resolve(HOME, "logos-animals");
if (!existsSync(OUT_DIR)) mkdirSync(OUT_DIR, { recursive: true });

const animals = [
  { file: "animal-sea-turtle.png", name: "Sea Turtle", latin: "Chelonia mydas" },
  { file: "animal-blue-crab.png", name: "Blue Crab", latin: "Callinectes sapidus" },
  { file: "animal-heron.png", name: "Great Blue Heron", latin: "Ardea herodias" },
  { file: "animal-alligator.png", name: "American Alligator", latin: "Alligator mississippiensis" },
  { file: "animal-dolphins.png", name: "Bottlenose Dolphin", latin: "Tursiops truncatus" },
];

async function overlayLogo(animal) {
  const bgPath = join(BG_DIR, animal.file);
  if (!existsSync(bgPath)) {
    console.log(`  [SKIP] ${animal.name} — not found`);
    return;
  }

  const svgOverlay = `<svg width="1080" height="1080" viewBox="0 0 1080 1080" xmlns="http://www.w3.org/2000/svg">
    <defs>
      <linearGradient id="shadow" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stop-color="rgba(0,0,0,0.3)"/>
        <stop offset="100%" stop-color="rgba(0,0,0,0.1)"/>
      </linearGradient>
    </defs>
    <rect width="1080" height="1080" fill="url(#shadow)"/>
    
    <!-- Outer ring -->
    <circle cx="540" cy="400" r="180" fill="none" stroke="#D4AF37" stroke-width="3"/>
    <circle cx="540" cy="400" r="175" fill="none" stroke="#D4AF37" stroke-width="1" opacity="0.5"/>
    
    <!-- Star -->
    <polygon points="540,280 555,350 625,350 575,395 590,470 540,425 490,470 505,395 455,350 525,350" fill="#D4AF37"/>
    
    <!-- GULLAH text -->
    <text x="540" y="480" text-anchor="middle" fill="#D4AF37" font-family="Georgia" font-size="32" font-weight="bold" letter-spacing="6">GULLAH</text>
    
    <!-- GEECHEE text -->
    <text x="540" y="520" text-anchor="middle" fill="#D4AF37" font-family="Georgia" font-size="32" font-weight="bold" letter-spacing="6">GEECHEE</text>
    
    <!-- BIZ text -->
    <text x="540" y="555" text-anchor="middle" fill="#D4AF37" font-family="Georgia" font-size="20" font-weight="bold" letter-spacing="4">BIZ</text>
    
    <!-- Animal name -->
    <text x="540" y="620" text-anchor="middle" fill="#F5F0E6" font-family="Georgia" font-size="28" font-weight="bold">${animal.name}</text>
    
    <!-- Latin name -->
    <text x="540" y="655" text-anchor="middle" fill="rgba(255,255,255,0.5)" font-family="Georgia" font-size="16" font-style="italic">${animal.latin}</text>
    
    <!-- Tagline -->
    <text x="540" y="700" text-anchor="middle" fill="rgba(255,255,255,0.4)" font-family="Georgia" font-size="14" font-style="italic">Gullah Geechee Corridor — Lowcountry Wildlife</text>
    
    <!-- Bottom branding -->
    <text x="540" y="1000" text-anchor="middle" fill="rgba(255,255,255,0.3)" font-family="Georgia" font-size="12">GULLAH GEECHEE BIZ — Preserving a Culture. Telling a Story.</text>
  </svg>`;

  const outPath = join(OUT_DIR, `logo-animal-${animal.file.replace("animal-", "").replace(".png", "")}.png`);

  await sharp(bgPath)
    .resize(1080, 1080, { fit: "cover" })
    .composite([
      { input: Buffer.from(svgOverlay), top: 0, left: 0 }
    ])
    .png()
    .toFile(outPath);

  console.log(`  [LOGO] ${animal.name} — ${outPath.split("/").pop()}`);
}

async function main() {
  console.log("=".repeat(60));
  console.log("  GULLAH GEECHEE BIZ — ANIMAL LOGO OVERLAYER");
  console.log("=".repeat(60));
  console.log();

  for (const animal of animals) {
    await overlayLogo(animal);
  }

  console.log(`\n✅ ${animals.length} animal logos generated at:`);
  console.log(`   ${OUT_DIR}`);
}

main().catch(e => console.error("Error:", e.message));
