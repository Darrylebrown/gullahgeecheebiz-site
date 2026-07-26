#!/usr/bin/env node
/**
 * Gullah Geechee Biz — Ultimate Themed Logo Generator
 * Processes all themes: streets, beaches, fish, marshes, golf, horses, plantations
 */

import sharp from "sharp";
import { existsSync, mkdirSync } from "fs";
import { join, resolve } from "path";
import { homedir } from "os";

const HOME = homedir();
const BG_DIR = resolve(HOME, "logos");
const OUT_DIR = resolve(HOME, "logos-themed");
if (!existsSync(OUT_DIR)) mkdirSync(OUT_DIR, { recursive: true });

const items = [
  // Street Signs
  { file: "street-charleston.png", name: "Charleston Street Sign", location: "Charleston, SC", theme: "Street Signs" },
  { file: "street-rural.png", name: "Lowcountry Crossroads", location: "Sea Islands, SC", theme: "Street Signs" },
  { file: "street-heritage-marker.png", name: "Gullah Heritage Marker", location: "St. Helena Island, SC", theme: "Street Signs" },
  { file: "street-signpost.png", name: "Lowcountry Signpost", location: "Sea Islands, SC", theme: "Street Signs" },
  { file: "street-corridor.png", name: "Gullah Geechee Corridor", location: "Coastal Highway, SC", theme: "Street Signs" },
  // Beaches
  { file: "beach-sunrise.png", name: "Lowcountry Sunrise Beach", location: "Sea Islands, SC", theme: "Beaches" },
  { file: "beach-hilton-head.png", name: "Hilton Head Beach", location: "Hilton Head, SC", theme: "Beaches" },
  { file: "beach-hunting-island.png", name: "Hunting Island Beach", location: "Hunting Island, SC", theme: "Beaches" },
  { file: "beach-sea-island.png", name: "Secluded Sea Island Beach", location: "Sea Islands, SC", theme: "Beaches" },
  { file: "beach-tybee.png", name: "Tybee Island Beach", location: "Tybee Island, GA", theme: "Beaches" },
  // Fish
  { file: "fish-red-drum.png", name: "Red Drum (Redfish)", location: "Lowcountry Waters, SC", theme: "Fish" },
  { file: "fish-flounder.png", name: "Southern Flounder", location: "Lowcountry Waters, SC", theme: "Fish" },
  { file: "fish-speckled-trout.png", name: "Speckled Sea Trout", location: "Lowcountry Waters, SC", theme: "Fish" },
  { file: "fish-sheepshead.png", name: "Sheepshead", location: "Lowcountry Waters, SC", theme: "Fish" },
  { file: "fish-tarpon.png", name: "Tarpon", location: "Lowcountry Waters, SC", theme: "Fish" },
  // Marshes
  { file: "marsh-golden-hour.png", name: "Golden Hour Marsh", location: "Sea Islands, SC", theme: "Marshes" },
  { file: "marsh-tidal-creek.png", name: "Tidal Creek Marsh", location: "Sea Islands, SC", theme: "Marshes" },
  { file: "marsh-sunrise-mist.png", name: "Sunrise Marsh Mist", location: "Sea Islands, SC", theme: "Marshes" },
  { file: "marsh-grass-closeup.png", name: "Marsh Grass", location: "Sea Islands, SC", theme: "Marshes" },
  { file: "marsh-sunset.png", name: "Marsh Sunset", location: "Sea Islands, SC", theme: "Marshes" },
  // Golf Courses
  { file: "golf-sunset.png", name: "Lowcountry Golf Sunset", location: "Sea Islands, SC", theme: "Golf Courses" },
  { file: "golf-harbour-town.png", name: "Harbour Town Golf Links", location: "Hilton Head, SC", theme: "Golf Courses" },
  { file: "golf-ocean.png", name: "Oceanfront Golf Hole", location: "Sea Islands, SC", theme: "Golf Courses" },
  { file: "golf-marsh.png", name: "Marsh Side Golf", location: "Sea Islands, SC", theme: "Golf Courses" },
  { file: "golf-oaks.png", name: "Oak Lined Fairway", location: "Sea Islands, SC", theme: "Golf Courses" },
  // Horses
  { file: "horse-beach.png", name: "Wild Beach Horses", location: "Sea Islands, SC", theme: "Horses" },
  { file: "horse-pasture.png", name: "Lowcountry Pasture Horse", location: "Sea Islands, SC", theme: "Horses" },
  { file: "horse-foal.png", name: "Mare and Foal", location: "Sea Islands, SC", theme: "Horses" },
  { file: "horse-marsh.png", name: "Horse in the Marsh", location: "Sea Islands, SC", theme: "Horses" },
  { file: "horse-charleston.png", name: "Charleston Carriage Horse", location: "Charleston, SC", theme: "Horses" },
  // Plantations
  { file: "plantation-oak-avenue.png", name: "Plantation Oak Avenue", location: "Lowcountry, SC", theme: "Plantations" },
  { file: "plantation-boone-hall.png", name: "Boone Hall Plantation", location: "Charleston, SC", theme: "Plantations" },
  { file: "plantation-rice-field.png", name: "Historic Rice Field", location: "Lowcountry, SC", theme: "Plantations" },
  { file: "plantation-chapel.png", name: "Plantation Chapel", location: "Lowcountry, SC", theme: "Plantations" },
  { file: "plantation-slave-cabin.png", name: "Historic Slave Cabin", location: "Lowcountry, SC", theme: "Plantations" },
];

async function overlayLogo(item) {
  const bgPath = join(BG_DIR, item.file);
  if (!existsSync(bgPath)) {
    console.log(`  [SKIP] ${item.name} — not found`);
    return;
  }

  const name = item.name.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/'/g, "&apos;").replace(/"/g, "&quot;");
  const location = item.location.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/'/g, "&apos;").replace(/"/g, "&quot;");
  const theme = item.theme.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/'/g, "&apos;").replace(/"/g, "&quot;");

  const svgOverlay = `<svg width="1080" height="1080" viewBox="0 0 1080 1080" xmlns="http://www.w3.org/2000/svg">
    <defs>
      <linearGradient id="shadow" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stop-color="rgba(0,0,0,0.35)"/>
        <stop offset="100%" stop-color="rgba(0,0,0,0.1)"/>
      </linearGradient>
    </defs>
    <rect width="1080" height="1080" fill="url(#shadow)"/>
    <circle cx="540" cy="380" r="170" fill="none" stroke="#D4AF37" stroke-width="3"/>
    <circle cx="540" cy="380" r="165" fill="none" stroke="#D4AF37" stroke-width="1" opacity="0.5"/>
    <polygon points="540,270 553,335 618,335 573,375 585,445 540,400 495,445 507,375 462,335 527,335" fill="#D4AF37"/>
    <text x="540" y="455" text-anchor="middle" fill="#D4AF37" font-family="Georgia" font-size="30" font-weight="bold" letter-spacing="6">GULLAH</text>
    <text x="540" y="490" text-anchor="middle" fill="#D4AF37" font-family="Georgia" font-size="30" font-weight="bold" letter-spacing="6">GEECHEE</text>
    <text x="540" y="520" text-anchor="middle" fill="#D4AF37" font-family="Georgia" font-size="18" font-weight="bold" letter-spacing="4">BIZ</text>
    <text x="540" y="590" text-anchor="middle" fill="#F5F0E6" font-family="Georgia" font-size="26" font-weight="bold">${name}</text>
    <text x="540" y="625" text-anchor="middle" fill="rgba(255,255,255,0.6)" font-family="Georgia" font-size="18">📍 ${location}</text>
    <text x="540" y="660" text-anchor="middle" fill="rgba(255,255,255,0.4)" font-family="Georgia" font-size="16" font-style="italic">Gullah Geechee ${theme}</text>
    <text x="540" y="1000" text-anchor="middle" fill="rgba(255,255,255,0.3)" font-family="Georgia" font-size="12">GULLAH GEECHEE BIZ — Preserving a Culture. Telling a Story.</text>
  </svg>`;

  const safeName = item.file.replace(/\.png$/, "");
  const outPath = join(OUT_DIR, `logo-${item.theme.toLowerCase().replace(/\s+/g, "-")}-${safeName.replace(/^(street-|beach-|fish-|marsh-|golf-|horse-|plantation-)/, "")}.png`);

  await sharp(bgPath)
    .resize(1080, 1080, { fit: "cover" })
    .composite([
      { input: Buffer.from(svgOverlay), top: 0, left: 0 }
    ])
    .png()
    .toFile(outPath);

  console.log(`  [${item.theme}] ${item.name}`);
}

async function main() {
  console.log("=".repeat(60));
  console.log("  GULLAH GEECHEE BIZ — ULTIMATE THEMED LOGO GENERATOR");
  console.log("=".repeat(60));
  console.log();

  for (const item of items) {
    await overlayLogo(item);
  }

  console.log(`\n✅ ${items.length} themed logos generated at:`);
  console.log(`   ${OUT_DIR}`);
  console.log("\nThemes: Street Signs (5), Beaches (5), Fish (5), Marshes (5), Golf Courses (5), Horses (5), Plantations (5)");
}

main().catch(e => console.error("Error:", e.message));
