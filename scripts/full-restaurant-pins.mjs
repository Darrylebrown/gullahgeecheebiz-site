#!/usr/bin/env node
/**
 * Gullah Geechee Biz — Full Restaurant Pin Generator (50 pins)
 * Overlays branding on food backgrounds for Gullah Geechee Corridor restaurants
 */

import sharp from "sharp";
import { existsSync, mkdirSync } from "fs";
import { join, resolve } from "path";
import { homedir } from "os";

const HOME = homedir();
const BG_DIR = resolve(HOME, "pins-restaurants");
const OUT_DIR = resolve(HOME, "pins-restaurants-final");
if (!existsSync(OUT_DIR)) mkdirSync(OUT_DIR, { recursive: true });

const backgrounds = [
  "bg-shrimp-grits.png", "bg-catfish.png", "bg-seafood-boil.png", "bg-oysters.png",
  "bg-collards.png", "bg-sweet-potato-pie.png", "bg-red-rice.png", "bg-seafood-platter.png",
  "bg-red-rice-okra.png", "bg-shrimp-grits-2.png", "bg-fried-green-tomatoes.png", "bg-crab-cakes.png"
];

const restaurants = [
  { name: "Gullah Grub", town: "St. Helena Island, SC", cuisine: "Gullah Soul Food" },
  { name: "The Foolish Frog", town: "St. Helena Island, SC", cuisine: "Lowcountry Fare" },
  { name: "Shrimp Shack", town: "St. Helena Island, SC", cuisine: "Fresh Seafood" },
  { name: "Beaufort Bistro", town: "Beaufort, SC", cuisine: "Southern Classics" },
  { name: "Plums Restaurant", town: "Beaufort, SC", cuisine: "Lowcountry Dining" },
  { name: "Saltus River Grill", town: "Beaufort, SC", cuisine: "Coastal Cuisine" },
  { name: "Breakwater Restaurant", town: "Beaufort, SC", cuisine: "Waterfront Dining" },
  { name: "Old Bull Tavern", town: "Beaufort, SC", cuisine: "Gastropub Fare" },
  { name: "Wren Bistro", town: "Beaufort, SC", cuisine: "Farm to Table" },
  { name: "Dashi", town: "Beaufort, SC", cuisine: "Japanese Lowcountry" },
  { name: "Hudson's Seafood", town: "Hilton Head, SC", cuisine: "Fresh Catch" },
  { name: "Skull Creek Boathouse", town: "Hilton Head, SC", cuisine: "Waterfront Seafood" },
  { name: "The Crazy Crab", town: "Hilton Head, SC", cuisine: "Lowcountry Seafood" },
  { name: "Old Oyster Factory", town: "Hilton Head, SC", cuisine: "Oyster Bar" },
  { name: "Sea Shack", town: "Hilton Head, SC", cuisine: "Casual Seafood" },
  { name: "Kenny B's", town: "Hilton Head, SC", cuisine: "Southern Kitchen" },
  { name: "A Lowcountry Backyard", town: "Hilton Head, SC", cuisine: "Gullah Inspired" },
  { name: "The Jazz Corner", town: "Hilton Head, SC", cuisine: "Jazz & Dining" },
  { name: "Fleetwood Diner", town: "Hilton Head, SC", cuisine: "Breakfast & Brunch" },
  { name: "Santa Fe Cafe", town: "Hilton Head, SC", cuisine: "Southwest Fusion" },
  { name: "Hominy Grill", town: "Charleston, SC", cuisine: "Southern Classics" },
  { name: "Bertha's Kitchen", town: "Charleston, SC", cuisine: "Gullah Soul Food" },
  { name: "Hannibal's Kitchen", town: "Charleston, SC", cuisine: "Gullah Cuisine" },
  { name: "The Glass Onion", town: "Charleston, SC", cuisine: "Lowcountry Fare" },
  { name: "FIG", town: "Charleston, SC", cuisine: "Fine Dining" },
  { name: "Husk", town: "Charleston, SC", cuisine: "Southern Revival" },
  { name: "The Ordinary", town: "Charleston, SC", cuisine: "Seafood Hall" },
  { name: "Leon's Oyster Shop", town: "Charleston, SC", cuisine: "Fried Chicken & Oysters" },
  { name: "Poogan's Porch", town: "Charleston, SC", cuisine: "Southern Comfort" },
  { name: "Slightly North of Broad", town: "Charleston, SC", cuisine: "Lowcountry Fine" },
  { name: "The Grey", town: "Savannah, GA", cuisine: "Southern Revival" },
  { name: "Mrs. Wilkes Dining Room", town: "Savannah, GA", cuisine: "Board Table Southern" },
  { name: "The Olde Pink House", town: "Savannah, GA", cuisine: "Colonial Dining" },
  { name: "Treylor Park", town: "Savannah, GA", cuisine: "Creative Southern" },
  { name: "Alligator Soul", town: "Savannah, GA", cuisine: "Wild Game & Seafood" },
  { name: "Collins Quarter", town: "Savannah, GA", cuisine: "Australian Cafe" },
  { name: "The Wyld Dock Bar", town: "Savannah, GA", cuisine: "Waterfront Casual" },
  { name: "Cotton & Rye", town: "Savannah, GA", cuisine: "Modern American" },
  { name: "B. Matthew's Eatery", town: "Savannah, GA", cuisine: "Brunch & Lunch" },
  { name: "The Vault", town: "Savannah, GA", cuisine: "Craft Cocktails & Small Plates" },
  { name: "Gullah Cafe", town: "Georgetown, SC", cuisine: "Gullah Soul Food" },
  { name: "River Room", town: "Georgetown, SC", cuisine: "Waterfront Dining" },
  { name: "Big T's BBQ", town: "Georgetown, SC", cuisine: "Lowcountry BBQ" },
  { name: "The Crab Shack", town: "Georgetown, SC", cuisine: "Seafood & Crabs" },
  { name: "Frank's Restaurant", town: "Georgetown, SC", cuisine: "Southern Home Cooking" },
  { name: "Spero's Restaurant", town: "Georgetown, SC", cuisine: "Italian Lowcountry" },
  { name: "Seven Sisters Restaurant", town: "Georgetown, SC", cuisine: "Gullah Heritage" },
  { name: "The Rice Paddy", town: "Georgetown, SC", cuisine: "Lowcountry Fusion" },
  { name: "Marsh View Restaurant", town: "Georgetown, SC", cuisine: "Seafood & Views" },
  { name: "Bistro 217", town: "Georgetown, SC", cuisine: "American Lowcountry" },
];

async function overlayPin(restaurant, index) {
  const bgFile = backgrounds[index % backgrounds.length];
  const bgPath = join(BG_DIR, bgFile);
  if (!existsSync(bgPath)) {
    console.log(`  [SKIP ${index + 1}] ${restaurant.name} — bg not found`);
    return;
  }

  const name = restaurant.name.toUpperCase().replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/'/g, "&apos;").replace(/"/g, "&quot;");
  const town = restaurant.town.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/'/g, "&apos;").replace(/"/g, "&quot;");
  const cuisine = restaurant.cuisine.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/'/g, "&apos;").replace(/"/g, "&quot;");

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
    <text x="540" y="900" text-anchor="middle" fill="#D4AF37" font-family="Georgia" font-size="56" font-weight="bold">${name}</text>
    
    <!-- Town -->
    <text x="540" y="970" text-anchor="middle" fill="rgba(255,255,255,0.7)" font-family="Arial" font-size="26">📍 ${town}</text>
    
    <!-- Cuisine -->
    <text x="540" y="1020" text-anchor="middle" fill="#F5F0E6" font-family="Georgia" font-size="22" font-style="italic">${cuisine}</text>
    
    <!-- CTA Button -->
    <rect x="340" y="1100" width="400" height="60" rx="30" fill="#D4AF37"/>
    <text x="540" y="1138" text-anchor="middle" fill="#0A1428" font-family="Arial" font-size="22" font-weight="bold">VISIT GULLAHGEECHEEBIZ.COM</text>
    
    <!-- Bottom branding -->
    <text x="540" y="1850" text-anchor="middle" fill="rgba(255,255,255,0.3)" font-family="Georgia" font-size="14">GULLAH GEECHEE BIZ — Preserving a Culture. Telling a Story.</text>
  </svg>`;

  const safeName = restaurant.name.toLowerCase().replace(/[^a-z0-9]/g, "-").replace(/-+/g, "-").replace(/^-|-$/g, "");
  const outPath = join(OUT_DIR, `restaurant-pin-${String(index + 1).padStart(3, "0")}-${safeName}.png`);

  await sharp(bgPath)
    .resize(1080, 1920, { fit: "cover" })
    .composite([
      { input: Buffer.from(svgOverlay), top: 0, left: 0 }
    ])
    .png()
    .toFile(outPath);

  console.log(`  [PIN ${index + 1}/50] ${restaurant.name} — ${town}`);
}

async function main() {
  console.log("=".repeat(60));
  console.log("  GULLAH GEECHEE BIZ — 50 RESTAURANT PINS");
  console.log("=".repeat(60));
  console.log();

  for (let i = 0; i < restaurants.length; i++) {
    await overlayPin(restaurants[i], i);
  }

  console.log(`\n✅ ${restaurants.length} restaurant pins generated at:`);
  console.log(`   ${OUT_DIR}`);
}

main().catch(e => console.error("Error:", e.message));
