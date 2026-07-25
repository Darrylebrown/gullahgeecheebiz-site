#!/usr/bin/env node
/**
 * Gullah Geechee Biz — Logo Text Overlayer
 * Overlays perfect text on clean metallic badge backgrounds
 */

import sharp from "sharp";
import { existsSync, mkdirSync } from "fs";
import { join } from "path";
import { homedir } from "os";

const HOME = homedir();
const BADGE_DIR = join(HOME, "logos");
const OUT_DIR = join(HOME, "logos-final");
mkdirSync(OUT_DIR, { recursive: true });

const BADGES = [
  { file: "badge-gold.png", finish: "Gold" },
  { file: "badge-rose-gold.png", finish: "Rose Gold" },
  { file: "badge-silver.png", finish: "Silver" },
  { file: "badge-copper.png", finish: "Copper" },
  { file: "badge-bronze.png", finish: "Bronze" },
  { file: "badge-platinum.png", finish: "Platinum" },
  { file: "badge-black-titanium.png", finish: "Black Titanium" },
  { file: "badge-champagne.png", finish: "Champagne" },
  { file: "badge-gunmetal.png", finish: "Gunmetal" },
  { file: "badge-white-gold.png", finish: "White Gold" },
];

function makeOverlay(finish) {
  return Buffer.from(`
    <svg width="1080" height="1080" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <linearGradient id="goldGrad" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stop-color="#D4AF37"/>
          <stop offset="50%" stop-color="#FFD700"/>
          <stop offset="100%" stop-color="#B8860B"/>
        </linearGradient>
      </defs>
      
      <!-- Star -->
      <polygon points="540,280 560,340 625,340 572,380 590,445 540,405 490,445 508,380 455,340 520,340"
        fill="url(#goldGrad)" stroke="#D4AF37" stroke-width="2"/>
      
      <!-- GGB text -->
      <text x="540" y="560" text-anchor="middle" font-family="Georgia, serif" font-size="120" font-weight="bold"
        fill="url(#goldGrad)" stroke="#8B6914" stroke-width="2">GGB</text>
      
      <!-- Top arc text -->
      <path id="topArc" d="M 200,540 A 340,340 0 0,1 880,540" fill="none"/>
      <text font-family="Georgia, serif" font-size="36" font-weight="bold" fill="url(#goldGrad)" stroke="#8B6914" stroke-width="1">
        <textPath href="#topArc" startOffset="50%" text-anchor="middle">GULLAH GEECHEE BIZ</textPath>
      </text>
      
      <!-- Bottom arc text -->
      <path id="botArc" d="M 200,560 A 340,340 0 0,0 880,560" fill="none"/>
      <text font-family="Georgia, serif" font-size="28" fill="url(#goldGrad)" stroke="#8B6914" stroke-width="1">
        <textPath href="#botArc" startOffset="50%" text-anchor="middle">PRESERVING A CULTURE · TELLING A STORY</textPath>
      </text>
      
      <!-- Decorative dots -->
      <circle cx="540" cy="650" r="4" fill="#D4AF37"/>
      <circle cx="520" cy="650" r="3" fill="#D4AF37" opacity="0.5"/>
      <circle cx="560" cy="650" r="3" fill="#D4AF37" opacity="0.5"/>
    </svg>
  `);
}

async function main() {
  console.log("=".repeat(60));
  console.log("  GULLAH GEECHEE BIZ — LOGO OVERLAYER");
  console.log("=".repeat(60));
  console.log();
  
  let ok = 0;
  for (const badge of BADGES) {
    const srcPath = join(BADGE_DIR, badge.file);
    const dstPath = join(OUT_DIR, `logo-${badge.file.replace('badge-', '')}`);
    
    if (!existsSync(srcPath)) {
      console.log(`  ⚠️  ${badge.file} not found`);
      continue;
    }
    
    const overlay = makeOverlay(badge.finish);
    
    await sharp(srcPath)
      .resize(1080, 1080, { fit: 'cover' })
      .composite([{ input: overlay, top: 0, left: 0 }])
      .png()
      .toFile(dstPath);
    
    console.log(`  ✅ logo-${badge.file.replace('badge-', '')} — ${badge.finish}`);
    ok++;
  }
  
  console.log(`\n  ${ok} logos created`);
  console.log(`  Output: ${OUT_DIR}`);
  console.log("=".repeat(60));
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
