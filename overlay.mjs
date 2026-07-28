#!/usr/bin/env node
/**
 * GGB Agent Opus — Premium Text Overlay
 * Uses sharp + SVG for gold serif text on scene images
 * Call: node overlay.mjs <image_path> <text> <output_path>
 */

import sharp from "sharp";
import { readFileSync, writeFileSync } from "fs";

const [,, imgPath, text, outPath] = process.argv;

const NAVY = "#0A1628";
const GOLD = "#C9A84C";
const WHITE = "#FFFFFF";

// Escape text for SVG
const safeText = text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");

// Determine font size based on text length
const fontSize = safeText.length > 20 ? 42 : safeText.length > 10 ? 52 : 64;
const subtitleSize = 24;

const svg = Buffer.from(`
<svg width="1080" height="1920" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="goldGrad" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#D4AF37"/>
      <stop offset="50%" stop-color="#C9A84C"/>
      <stop offset="100%" stop-color="#B8860B"/>
    </linearGradient>
    <linearGradient id="barGrad" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#0A1628" stop-opacity="0.85"/>
      <stop offset="100%" stop-color="#0A1628" stop-opacity="0.95"/>
    </linearGradient>
  </defs>

  <!-- Bottom text bar -->
  <rect x="0" y="1620" width="1080" height="300" fill="url(#barGrad)"/>

  <!-- Gold accent line above text -->
  <rect x="340" y="1635" width="400" height="3" fill="url(#goldGrad)"/>

  <!-- Main text -->
  <text x="540" y="1760" text-anchor="middle" 
        font-family="Georgia, 'Times New Roman', serif" 
        font-size="${fontSize}" font-weight="bold" 
        fill="url(#goldGrad)">${safeText}</text>

  <!-- Gold accent line below text -->
  <rect x="340" y="1890" width="400" height="3" fill="url(#goldGrad)"/>

  <!-- Brand watermark bottom-right -->
  <text x="1040" y="1910" text-anchor="end" 
        font-family="Helvetica, Arial, sans-serif" 
        font-size="14" fill="${GOLD}" opacity="0.5">GGB</text>
</svg>
`);

async function main() {
  const img = sharp(imgPath);
  const meta = await img.metadata();

  // Resize to 1080x1920 with cover crop
  const resized = await img
    .resize(1080, 1920, { fit: "cover", position: "center" })
    .composite([{ input: svg, top: 0, left: 0 }])
    .png()
    .toBuffer();

  // Write output
  writeFileSync(outPath, resized);
  console.log(`Overlay applied: ${outPath}`);
}

main().catch(e => { console.error(e); process.exit(1); });
