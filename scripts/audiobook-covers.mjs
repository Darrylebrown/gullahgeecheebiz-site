#!/usr/bin/env node
/**
 * Gullah Geechee Biz — Audiobook Cover Overlayer
 * Overlays perfect text on clean cover backgrounds
 */

import sharp from "sharp";
import { existsSync } from "fs";
import { join } from "path";
import { homedir } from "os";

const HOME = homedir();
const AUDIO_DIR = join(HOME, "audiobooks");

const COVERS = [
  {
    bg: "cover-bg-roots-rivers.png",
    out: "cover-roots-rivers.png",
    title: "ROOTS & RIVERS",
    subtitle: "Vol. 1 · Beaufort",
    tagline: "The first encyclopedia of Gullah Geechee history",
  },
  {
    bg: "cover-bg-blood-remembers.png",
    out: "cover-blood-remembers.png",
    title: "BLOOD REMEMBERS",
    subtitle: "A novel of memory, family, and the Gullah Geechee coast",
    tagline: "The land remembers what the books forgot",
  },
];

function makeOverlay(title, subtitle, tagline) {
  return Buffer.from(`
    <svg width="3000" height="3000" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <linearGradient id="goldGrad" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stop-color="#D4AF37"/>
          <stop offset="50%" stop-color="#FFD700"/>
          <stop offset="100%" stop-color="#B8860B"/>
        </linearGradient>
        <linearGradient id="topFade" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="black" stop-opacity="0.8"/>
          <stop offset="100%" stop-color="black" stop-opacity="0"/>
        </linearGradient>
        <linearGradient id="botFade" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="black" stop-opacity="0"/>
          <stop offset="100%" stop-color="black" stop-opacity="0.8"/>
        </linearGradient>
      </defs>
      
      <!-- Top fade -->
      <rect x="0" y="0" width="3000" height="800" fill="url(#topFade)"/>
      
      <!-- Bottom fade -->
      <rect x="0" y="2000" width="3000" height="1000" fill="url(#botFade)"/>
      
      <!-- Emblem -->
      <circle cx="1500" cy="200" r="80" stroke="#D4AF37" stroke-width="4" fill="none"/>
      <text x="1500" y="215" text-anchor="middle" font-family="Georgia, serif" font-size="40" font-weight="bold" fill="#D4AF37">GGB</text>
      <text x="1500" y="250" text-anchor="middle" font-family="Georgia, serif" font-size="20" fill="#D4AF37">★</text>
      
      <!-- GULLAH GEECHEE BIZ arc -->
      <path id="topArc" d="M 800,200 A 700,700 0 0,1 2200,200" fill="none"/>
      <text font-family="Georgia, serif" font-size="32" font-weight="bold" fill="#D4AF37">
        <textPath href="#topArc" startOffset="50%" text-anchor="middle">GULLAH GEECHEE BIZ</textPath>
      </text>
      
      <!-- Title -->
      <text x="1500" y="1200" text-anchor="middle" font-family="Georgia, serif" font-size="160" font-weight="bold" fill="#D4AF37" stroke="#8B6914" stroke-width="3">${escapeXml(title)}</text>
      
      <!-- Subtitle -->
      <text x="1500" y="1350" text-anchor="middle" font-family="Georgia, serif" font-size="60" fill="white">${escapeXml(subtitle)}</text>
      
      <!-- Tagline -->
      <text x="1500" y="1450" text-anchor="middle" font-family="Helvetica, sans-serif" font-size="36" fill="#D4AF37" font-style="italic">${escapeXml(tagline)}</text>
      
      <!-- Bottom branding -->
      <text x="1500" y="2700" text-anchor="middle" font-family="Georgia, serif" font-size="28" fill="#D4AF37">GULLAH GEECHEE BIZ</text>
      <line x1="1000" y1="2730" x2="2000" y2="2730" stroke="#D4AF37" stroke-width="2"/>
      <text x="1500" y="2780" text-anchor="middle" font-family="Helvetica, sans-serif" font-size="22" fill="white">gullahgeecheebiz.com</text>
    </svg>
  `);
}

function escapeXml(s) {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&apos;');
}

async function main() {
  console.log("=".repeat(60));
  console.log("  GULLAH GEECHEE BIZ — AUDIOBOOK COVERS");
  console.log("=".repeat(60));
  console.log();
  
  for (const cover of COVERS) {
    const bgPath = join(AUDIO_DIR, cover.bg);
    const outPath = join(AUDIO_DIR, cover.out);
    
    if (!existsSync(bgPath)) {
      console.log(`  ⚠️  ${cover.bg} not found`);
      continue;
    }
    
    const overlay = makeOverlay(cover.title, cover.subtitle, cover.tagline);
    
    await sharp(bgPath)
      .resize(3000, 3000, { fit: 'cover' })
      .composite([{ input: overlay, top: 0, left: 0 }])
      .png()
      .toFile(outPath);
    
    console.log(`  ✅ ${cover.out}`);
    console.log(`     ${cover.title}`);
    console.log();
  }
  
  console.log("=".repeat(60));
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
