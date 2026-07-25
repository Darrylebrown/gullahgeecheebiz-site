#!/usr/bin/env node
/**
 * Gullah Geechee Biz — Pin Text Overlayer
 * Overlays perfect text on clean pin backgrounds
 * No more AI spelling errors
 */

import sharp from "sharp";
import { readFileSync, existsSync, mkdirSync } from "fs";
import { join, resolve } from "path";
import { homedir } from "os";

const HOME = homedir();
const PIN_DIR = join(HOME, "pins-ai");
const OUT_DIR = join(HOME, "pins-final");
mkdirSync(OUT_DIR, { recursive: true });

const GOLD = { r: 212, g: 175, b: 55 };
const WHITE = { r: 255, g: 255, b: 255 };
const NAVY = { r: 10, g: 20, b: 40 };
const CREAM = { r: 245, g: 240, b: 230 };

const PINS = [
  { file: "pin-034-philip-simmons.png", title: "PHILIP SIMMONS", subtitle: "The Gullah Geechee ironwork master. His gates define Charleston's beauty." },
  { file: "pin-035-charleston.png", title: "CHARLESTON", subtitle: "Gullah Geechee history in the Holy City. From the port to the praise houses." },
  { file: "pin-036-savannah.png", title: "SAVANNAH", subtitle: "Gullah Geechee roots in the Hostess City. Squares, oaks, and coastal heritage." },
  { file: "pin-037-beaufort.png", title: "BEAUFORT", subtitle: "Where Gullah Geechee history runs deep. The spirit of the Lowcountry." },
  { file: "pin-038-hilton-head.png", title: "HILTON HEAD", subtitle: "Beyond the resorts. Gullah Geechee heritage on Hilton Head Island." },
  { file: "pin-039-st-helena.png", title: "ST. HELENA ISLAND", subtitle: "The heart of Gullah Geechee culture. Penn Center, oaks, and sacred ground." },
  { file: "pin-040-edisto.png", title: "EDISTO ISLAND", subtitle: "Gullah Geechee history on Edisto. Beaches, oaks, and a story that endures." },
  { file: "pin-041-georgetown.png", title: "GEORGETOWN", subtitle: "Gullah Geechee heritage in Georgetown. River town, rice history." },
  { file: "pin-042-daufuskie-v2.png", title: "DAUFUSKIE ISLAND", subtitle: "The remote Sea Island. Gullah Geechee culture preserved in isolation." },
  { file: "pin-043-port-royal.png", title: "PORT ROYAL", subtitle: "Where Gullah Geechee history meets the sea. Port Royal, South Carolina." },
  { file: "pin-044-yemassee.png", title: "YEMASSEE", subtitle: "Gullah Geechee roots in Yemassee. Small town, big history." },
  { file: "pin-045-ridgeland.png", title: "RIDGELAND", subtitle: "Gullah Geechee heritage in Ridgeland. The heart of the Lowcountry." },
  { file: "pin-046-hardeeville.png", title: "HARDEEVILLE", subtitle: "Gullah Geechee heritage in Hardeeville. Gateway to the Lowcountry." },
  { file: "pin-047-bluffton.png", title: "BLUFFTON", subtitle: "Gullah Geechee history in Bluffton. Old town, new stories." },
  { file: "pin-048-walterboro.png", title: "WALTERBORO", subtitle: "Gullah Geechee roots in Walterboro. The Lowcountry's front porch." },
  { file: "pin-049-jasper-county.png", title: "JASPER COUNTY", subtitle: "Gullah Geechee heritage in Jasper County. Land, family, tradition." },
  { file: "pin-050-coles-hill.png", title: "COLES HILL", subtitle: "Gullah Geechee history in Coles Hill. The northern reach of the corridor." },
  { file: "pin-051-corridor.png", title: "GULLAH GEECHEE CORRIDOR", subtitle: "From North Carolina to Florida. 12 counties. One culture. Our heritage." },
  { file: "pin-052-johns-island.png", title: "JOHNS ISLAND", subtitle: "Gullah Geechee heritage on Johns Island. Angel Oak, land, legacy." },
  { file: "pin-053-wadmalaw.png", title: "WADMALAW ISLAND", subtitle: "Gullah Geechee history on Wadmalaw Island. Tea, oaks, and tradition." },
  { file: "pin-054-james-island.png", title: "JAMES ISLAND", subtitle: "Gullah Geechee roots on James Island. Fort, river, resilience." },
  { file: "pin-055-mount-pleasant.png", title: "MOUNT PLEASANT", subtitle: "Gullah Geechee heritage in Mount Pleasant. Shem Creek, oaks, history." },
  { file: "pin-056-folly-beach.png", title: "FOLLY BEACH", subtitle: "Gullah Geechee history at Folly Beach. Coast, community, culture." },
  { file: "pin-057-mcclellanville.png", title: "MCCLELLANVILLE", subtitle: "Gullah Geechee heritage in McClellanville. Fishing village, tradition." },
  { file: "pin-058-moncks-corner.png", title: "MONCKS CORNER", subtitle: "Gullah Geechee heritage in Moncks Corner. Lake, land, legacy." },
  { file: "pin-059-saint-george.png", title: "SAINT GEORGE", subtitle: "Gullah Geechee history in Saint George. Small town, deep roots." },
  { file: "pin-060-brunswick.png", title: "BRUNSWICK", subtitle: "Gullah Geechee heritage in Brunswick. Gateway to the Golden Isles." },
  { file: "pin-061-darien.png", title: "DARIEN", subtitle: "Gullah Geechee history in Darien. McIntosh County, marsh, heritage." },
  { file: "pin-062-sapelo-island.png", title: "SAPELO ISLAND", subtitle: "Gullah Geechee heritage on Sapelo Island. Hog Hammock, marsh, tradition." },
  { file: "pin-063-st-simons.png", title: "ST. SIMONS ISLAND", subtitle: "Gullah Geechee history on St. Simons Island. Beach, oaks, heritage." },
  { file: "pin-064-red-rice.png", title: "GULLAH RED RICE", subtitle: "The signature dish of the Lowcountry. Every Gullah kitchen has a recipe." },
  { file: "pin-065-shrimp-grits.png", title: "SHRIMP AND GRITS", subtitle: "A Lowcountry classic. Gullah Geechee flavors in every bite." },
  { file: "pin-066-okra-soup.png", title: "OKRA SOUP", subtitle: "West African roots. Gullah Geechee soul. A bowl of history." },
  { file: "pin-067-benne-wafers.png", title: "BENNE WAFERS", subtitle: "Sesame cookies brought from West Africa. A Gullah Geechee tradition." },
  { file: "pin-068-frogmore-stew.png", title: "FROGMORE STEW", subtitle: "The Lowcountry boil. Shrimp, sausage, corn, potatoes. A community feast." },
  { file: "pin-069-fried-fish.png", title: "FRIED FISH", subtitle: "Fresh from the coast. Gullah Geechee fried fish, hushpuppies, and love." },
  { file: "pin-070-bowens-island.png", title: "BOWEN'S ISLAND", subtitle: "Gullah Geechee seafood on Folly Beach since 1946. A Lowcountry institution." },
  { file: "pin-071-fish-camp.png", title: "GULLAH FISH CAMP", subtitle: "Fresh catch, Gullah style. A fish camp tradition in the Lowcountry." },
  { file: "pin-072-soul-food.png", title: "SOUL FOOD KITCHEN", subtitle: "Gullah Geechee soul food. Collards, mac and cheese, cornbread, love." },
  { file: "pin-073-lowcountry-seafood.png", title: "LOWCOUNTRY SEAFOOD", subtitle: "Fresh oysters, shrimp, crab. The bounty of the Gullah Geechee coast." },
  { file: "pin-074-charleston-soul.png", title: "CHARLESTON SOUL FOOD", subtitle: "Gullah Geechee flavors in the Holy City. Where tradition meets the plate." },
  { file: "pin-075-savannah-soul.png", title: "SAVANNAH SOUL FOOD", subtitle: "Gullah Geechee cuisine in the Hostess City. History on every plate." },
];

// SVG overlay builder
function makeOverlay(title, subtitle) {
  return Buffer.from(`
    <svg width="1080" height="1920" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <linearGradient id="topGrad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="black" stop-opacity="0.85"/>
          <stop offset="100%" stop-color="black" stop-opacity="0"/>
        </linearGradient>
        <linearGradient id="botGrad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="black" stop-opacity="0"/>
          <stop offset="100%" stop-color="black" stop-opacity="0.85"/>
        </linearGradient>
      </defs>
      
      <!-- Top gradient -->
      <rect x="0" y="0" width="1080" height="500" fill="url(#topGrad)"/>
      
      <!-- Bottom gradient -->
      <rect x="0" y="1300" width="1080" height="620" fill="url(#botGrad)"/>
      
      <!-- Title -->
      <text x="540" y="120" text-anchor="middle" font-family="Georgia, serif" font-size="64" font-weight="bold" fill="rgb(212,175,55)">${escapeXml(title)}</text>
      
      <!-- Subtitle -->
      <text x="540" y="210" text-anchor="middle" font-family="Helvetica, sans-serif" font-size="28" fill="white">${escapeXml(subtitle)}</text>
      
      <!-- CTA Button -->
      <rect x="340" y="1700" width="400" height="50" rx="25" fill="rgb(212,175,55)"/>
      <text x="540" y="1732" text-anchor="middle" font-family="Helvetica, sans-serif" font-size="22" font-weight="bold" fill="rgb(10,20,40)">Explore at gullahgeecheebiz.com</text>
      
      <!-- Emblem -->
      <circle cx="540" cy="1500" r="50" stroke="rgb(212,175,55)" stroke-width="3" fill="none"/>
      <text x="540" y="1508" text-anchor="middle" font-family="Helvetica, sans-serif" font-size="20" font-weight="bold" fill="rgb(212,175,55)">GGB</text>
      <text x="540" y="1530" text-anchor="middle" font-family="Helvetica, sans-serif" font-size="16" fill="rgb(212,175,55)">★</text>
      <text x="540" y="1575" text-anchor="middle" font-family="Helvetica, sans-serif" font-size="18" font-weight="bold" fill="rgb(212,175,55)">GULLAH GEECHEE BIZ</text>
      <line x1="340" y1="1595" x2="740" y2="1595" stroke="rgb(212,175,55)" stroke-width="2"/>
    </svg>
  `);
}

function escapeXml(s) {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&apos;');
}

async function processPin(pin) {
  const srcPath = join(PIN_DIR, pin.file);
  const dstPath = join(OUT_DIR, pin.file);
  
  if (!existsSync(srcPath)) {
    console.log(`  ⚠️  ${pin.file} not found`);
    return false;
  }
  
  const overlay = makeOverlay(pin.title, pin.subtitle);
  
  await sharp(srcPath)
    .resize(1080, 1920, { fit: 'cover' })
    .composite([
      { input: overlay, top: 0, left: 0 }
    ])
    .png()
    .toFile(dstPath);
  
  return true;
}

async function main() {
  console.log("=".repeat(60));
  console.log("  GULLAH GEECHEE BIZ — PIN TEXT OVERLAYER");
  console.log("=".repeat(60));
  console.log();
  
  let ok = 0, fail = 0;
  for (const pin of PINS) {
    const result = await processPin(pin);
    if (result) {
      console.log(`  ✅ ${pin.file} — ${pin.title}`);
      ok++;
    } else {
      fail++;
    }
  }
  
  console.log(`\n  ${ok} pins overlaid, ${fail} skipped`);
  console.log(`  Output: ${OUT_DIR}`);
  console.log("=".repeat(60));
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
