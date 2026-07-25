#!/usr/bin/env node
/**
 * Gullah Geechee Biz — Printful Merch Design Generator
 * Creates print-ready design files from metallic logos
 * For t-shirts, hoodies, mugs, totes, and more
 */

import sharp from "sharp";
import { existsSync, mkdirSync } from "fs";
import { join } from "path";
import { homedir } from "os";

const HOME = homedir();
const LOGO_DIR = join(HOME, "logos-final");
const OUT_DIR = join(HOME, "merch-designs");
mkdirSync(OUT_DIR, { recursive: true });

const DESIGNS = [
  // ── T-Shirt Designs (front chest) ──
  { name: "tshirt-gold", logo: "logo-gold.png", width: 3600, height: 4200, label: "Gold Logo T-Shirt" },
  { name: "tshirt-black-titanium", logo: "logo-black-titanium.png", width: 3600, height: 4200, label: "Black Titanium T-Shirt" },
  { name: "tshirt-white-gold", logo: "logo-white-gold.png", width: 3600, height: 4200, label: "White Gold T-Shirt" },
  { name: "tshirt-rose-gold", logo: "logo-rose-gold.png", width: 3600, height: 4200, label: "Rose Gold T-Shirt" },
  { name: "tshirt-platinum", logo: "logo-platinum.png", width: 3600, height: 4200, label: "Platinum T-Shirt" },
  
  // ── Hoodie Designs ──
  { name: "hoodie-gold", logo: "logo-gold.png", width: 3600, height: 4200, label: "Gold Logo Hoodie" },
  { name: "hoodie-gunmetal", logo: "logo-gunmetal.png", width: 3600, height: 4200, label: "Gunmetal Logo Hoodie" },
  
  // ── Mug Designs ──
  { name: "mug-gold", logo: "logo-gold.png", width: 2550, height: 1200, label: "Gold Logo Mug" },
  { name: "mug-rose-gold", logo: "logo-rose-gold.png", width: 2550, height: 1200, label: "Rose Gold Mug" },
  
  // ── Tote Bag Designs ──
  { name: "tote-gold", logo: "logo-gold.png", width: 3600, height: 3600, label: "Gold Logo Tote" },
  { name: "tote-copper", logo: "logo-copper.png", width: 3600, height: 3600, label: "Copper Logo Tote" },
  
  // ── Hat Designs ──
  { name: "hat-gold", logo: "logo-gold.png", width: 1350, height: 1350, label: "Gold Logo Hat" },
  { name: "hat-silver", logo: "logo-silver.png", width: 1350, height: 1350, label: "Silver Logo Hat" },
  
  // ── Phone Case Designs ──
  { name: "phone-gold", logo: "logo-gold.png", width: 1800, height: 3200, label: "Gold Logo Phone Case" },
  { name: "phone-bronze", logo: "logo-bronze.png", width: 1800, height: 3200, label: "Bronze Logo Phone Case" },
];

async function generateDesign(design) {
  const logoPath = join(LOGO_DIR, design.logo);
  const outPath = join(OUT_DIR, `${design.name}.png`);
  
  if (!existsSync(logoPath)) {
    console.log(`  ⚠️  ${design.logo} not found`);
    return false;
  }
  
  // Create a canvas with transparent background
  const canvas = await sharp({
    create: {
      width: design.width,
      height: design.height,
      channels: 4,
      background: { r: 0, g: 0, b: 0, alpha: 0 }
    }
  }).png().toBuffer();
  
  // Calculate logo size (proportional to canvas)
  const logoSize = Math.min(design.width, design.height) * 0.6;
  const logoX = Math.round((design.width - logoSize) / 2);
  const logoY = Math.round((design.height - logoSize) / 2);
  
  // Composite the logo centered on the canvas
  await sharp(canvas)
    .composite([{
      input: await sharp(logoPath).resize(logoSize, logoSize, { fit: 'contain' }).png().toBuffer(),
      top: logoY,
      left: logoX
    }])
    .png()
    .toFile(outPath);
  
  return true;
}

async function main() {
  console.log("=".repeat(60));
  console.log("  GULLAH GEECHEE BIZ — MERCH DESIGN GENERATOR");
  console.log("=".repeat(60));
  console.log();
  
  let ok = 0;
  for (const d of DESIGNS) {
    const result = await generateDesign(d);
    if (result) {
      console.log(`  ✅ ${d.name}.png — ${d.label} (${d.width}×${d.height})`);
      ok++;
    }
  }
  
  console.log(`\n  ${ok} merch designs created`);
  console.log(`  Output: ${OUT_DIR}`);
  console.log("\n  Upload these to Printful for:");
  console.log("  • T-shirts, hoodies, tank tops");
  console.log("  • Mugs, water bottles");
  console.log("  • Tote bags, backpacks");
  console.log("  • Hats, beanies");
  console.log("  • Phone cases, pillows");
  console.log("=".repeat(60));
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
