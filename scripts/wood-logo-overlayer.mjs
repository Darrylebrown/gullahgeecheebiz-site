#!/usr/bin/env node
/**
 * Gullah Geechee Biz — Wood Logo Overlayer
 * Overlays gold emblem on beautiful wood textures
 */

import sharp from "sharp";
import { existsSync, mkdirSync, readdirSync } from "fs";
import { join, resolve } from "path";
import { homedir } from "os";

const HOME = homedir();
const BG_DIR = resolve(HOME, "logos");
const OUT_DIR = resolve(HOME, "logos-wood");
if (!existsSync(OUT_DIR)) mkdirSync(OUT_DIR, { recursive: true });

const woodTypes = [
  { file: "wood-mahogany.png", name: "Mahogany" },
  { file: "wood-barn.png", name: "Barn Wood" },
  { file: "wood-oak.png", name: "Oak" },
  { file: "wood-walnut.png", name: "Walnut" },
  { file: "wood-driftwood.png", name: "Driftwood" },
];

async function overlayLogo(wood) {
  const bgPath = join(BG_DIR, wood.file);
  if (!existsSync(bgPath)) {
    console.log(`  [SKIP] ${wood.name} — not found`);
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
    <circle cx="540" cy="440" r="200" fill="none" stroke="#D4AF37" stroke-width="4"/>
    <circle cx="540" cy="440" r="195" fill="none" stroke="#D4AF37" stroke-width="1" opacity="0.5"/>
    
    <!-- Star -->
    <polygon points="540,300 560,380 640,380 580,430 600,510 540,460 480,510 500,430 440,380 520,380" fill="#D4AF37"/>
    
    <!-- GULLAH text -->
    <text x="540" y="520" text-anchor="middle" fill="#D4AF37" font-family="Georgia" font-size="36" font-weight="bold" letter-spacing="8">GULLAH</text>
    
    <!-- GEECHEE text -->
    <text x="540" y="565" text-anchor="middle" fill="#D4AF37" font-family="Georgia" font-size="36" font-weight="bold" letter-spacing="8">GEECHEE</text>
    
    <!-- BIZ text -->
    <text x="540" y="605" text-anchor="middle" fill="#D4AF37" font-family="Georgia" font-size="24" font-weight="bold" letter-spacing="4">BIZ</text>
    
    <!-- Tagline -->
    <text x="540" y="660" text-anchor="middle" fill="rgba(255,255,255,0.6)" font-family="Georgia" font-size="16" font-style="italic">Preserving a Culture. Telling a Story.</text>
    
    <!-- Bottom branding -->
    <text x="540" y="1000" text-anchor="middle" fill="rgba(255,255,255,0.3)" font-family="Georgia" font-size="12">${wood.name} — GULLAH GEECHEE BIZ</text>
  </svg>`;

  const outPath = join(OUT_DIR, `logo-wood-${wood.file.replace("wood-", "").replace(".png", "")}.png`);

  await sharp(bgPath)
    .resize(1080, 1080, { fit: "cover" })
    .composite([
      { input: Buffer.from(svgOverlay), top: 0, left: 0 }
    ])
    .png()
    .toFile(outPath);

  console.log(`  [LOGO] ${wood.name} — ${outPath.split("/").pop()}`);
}

async function main() {
  console.log("=".repeat(60));
  console.log("  GULLAH GEECHEE BIZ — WOOD LOGO OVERLAYER");
  console.log("=".repeat(60));
  console.log();

  for (const wood of woodTypes) {
    await overlayLogo(wood);
  }

  console.log(`\n✅ ${woodTypes.length} wood logos generated at:`);
  console.log(`   ${OUT_DIR}`);
}

main().catch(e => console.error("Error:", e.message));
