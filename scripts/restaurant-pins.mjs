#!/usr/bin/env node
/**
 * Gullah Geechee Biz — Restaurant Pin Generator
 * Creates branded Pinterest pins for Gullah Geechee restaurants
 */

import { writeFileSync, mkdirSync, existsSync } from "fs";
import { join, resolve } from "path";
import { homedir } from "os";

const HOME = homedir();
const OUT_DIR = resolve(HOME, "pins-restaurants");
if (!existsSync(OUT_DIR)) mkdirSync(OUT_DIR, { recursive: true });

const restaurants = [
  { name: "Gullah Grub", town: "St. Helena Island", cuisine: "Gullah Soul Food" },
  { name: "The Foolish Frog", town: "St. Helena Island", cuisine: "Lowcountry Fare" },
  { name: "Shrimp Shack", town: "St. Helena Island", cuisine: "Fresh Seafood" },
  { name: "Beaufort Bistro", town: "Beaufort", cuisine: "Southern Classics" },
  { name: "Plums Restaurant", town: "Beaufort", cuisine: "Lowcountry Dining" },
  { name: "Saltus River Grill", town: "Beaufort", cuisine: "Coastal Cuisine" },
  { name: "Breakwater Restaurant", town: "Beaufort", cuisine: "Waterfront Dining" },
  { name: "Old Bull Tavern", town: "Beaufort", cuisine: "Gastropub Fare" },
  { name: "Wren Bistro", town: "Beaufort", cuisine: "Farm to Table" },
  { name: "Dashi", town: "Beaufort", cuisine: "Japanese Lowcountry" },
  { name: "Hudson's Seafood", town: "Hilton Head", cuisine: "Fresh Catch" },
  { name: "Skull Creek Boathouse", town: "Hilton Head", cuisine: "Waterfront Seafood" },
  { name: "The Crazy Crab", town: "Hilton Head", cuisine: "Lowcountry Seafood" },
  { name: "Old Oyster Factory", town: "Hilton Head", cuisine: "Oyster Bar" },
  { name: "Sea Shack", town: "Hilton Head", cuisine: "Casual Seafood" },
  { name: "Kenny B's", town: "Hilton Head", cuisine: "Southern Kitchen" },
  { name: "A Lowcountry Backyard", town: "Hilton Head", cuisine: "Gullah Inspired" },
  { name: "The Jazz Corner", town: "Hilton Head", cuisine: "Jazz & Dining" },
  { name: "Fleetwood Diner", town: "Hilton Head", cuisine: "Breakfast & Brunch" },
  { name: "Santa Fe Cafe", town: "Hilton Head", cuisine: "Southwest Fusion" },
  { name: "Hominy Grill", town: "Charleston", cuisine: "Southern Classics" },
  { name: "Bertha's Kitchen", town: "Charleston", cuisine: "Gullah Soul Food" },
  { name: "Hannibal's Kitchen", town: "Charleston", cuisine: "Gullah Cuisine" },
  { name: "The Glass Onion", town: "Charleston", cuisine: "Lowcountry Fare" },
  { name: "FIG", town: "Charleston", cuisine: "Fine Dining" },
  { name: "Husk", town: "Charleston", cuisine: "Southern Revival" },
  { name: "The Ordinary", town: "Charleston", cuisine: "Seafood Hall" },
  { name: "Leon's Oyster Shop", town: "Charleston", cuisine: "Fried Chicken & Oysters" },
  { name: "Poogan's Porch", town: "Charleston", cuisine: "Southern Comfort" },
  { name: "Slightly North of Broad", town: "Charleston", cuisine: "Lowcountry Fine" },
  { name: "The Grey", town: "Savannah", cuisine: "Southern Revival" },
  { name: "Mrs. Wilkes Dining Room", town: "Savannah", cuisine: "Board Table Southern" },
  { name: "The Olde Pink House", town: "Savannah", cuisine: "Colonial Dining" },
  { name: "Treylor Park", town: "Savannah", cuisine: "Creative Southern" },
  { name: "Alligator Soul", town: "Savannah", cuisine: "Wild Game & Seafood" },
  { name: "Collins Quarter", town: "Savannah", cuisine: "Australian Cafe" },
  { name: "The Wyld Dock Bar", town: "Savannah", cuisine: "Waterfront Casual" },
  { name: "Cotton & Rye", town: "Savannah", cuisine: "Modern American" },
  { name: "B. Matthew's Eatery", town: "Savannah", cuisine: "Brunch & Lunch" },
  { name: "The Vault", town: "Savannah", cuisine: "Craft Cocktails & Small Plates" },
  { name: "Gullah Cafe", town: "Georgetown", cuisine: "Gullah Soul Food" },
  { name: "River Room", town: "Georgetown", cuisine: "Waterfront Dining" },
  { name: "Big T's BBQ", town: "Georgetown", cuisine: "Lowcountry BBQ" },
  { name: "The Crab Shack", town: "Georgetown", cuisine: "Seafood & Crabs" },
  { name: "Frank's Restaurant", town: "Georgetown", cuisine: "Southern Home Cooking" },
  { name: "Spero's Restaurant", town: "Georgetown", cuisine: "Italian Lowcountry" },
  { name: "Seven Sisters Restaurant", town: "Georgetown", cuisine: "Gullah Heritage" },
  { name: "The Rice Paddy", town: "Georgetown", cuisine: "Lowcountry Fusion" },
  { name: "Marsh View Restaurant", town: "Georgetown", cuisine: "Seafood & Views" },
  { name: "Bistro 217", town: "Georgetown", cuisine: "American Lowcountry" },
];

// Generate HTML pins (since we can't use sharp for image generation)
let html = `<!DOCTYPE html>
<html><head><meta charset="UTF-8"><style>
body { font-family: Georgia, serif; margin: 0; padding: 20px; background: #0A1428; color: #F5F0E6; }
h1 { color: #D4AF37; text-align: center; }
.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 20px; }
.pin { background: linear-gradient(135deg, #1a2a4a, #0A1428); border: 1px solid rgba(212,175,55,0.3); border-radius: 16px; padding: 20px; text-align: center; aspect-ratio: 9/16; display: flex; flex-direction: column; justify-content: center; }
.emblem { width: 50px; height: 50px; border: 2px solid #D4AF37; border-radius: 50%; margin: 0 auto 15px; display: flex; align-items: center; justify-content: center; color: #D4AF37; font-weight: bold; font-size: 12px; }
.name { color: #D4AF37; font-size: 1.3rem; font-weight: bold; margin-bottom: 5px; }
.town { color: rgba(255,255,255,0.6); font-size: 0.9rem; margin-bottom: 10px; }
.cuisine { color: #F5F0E6; font-size: 0.85rem; margin-bottom: 15px; font-style: italic; }
.cta { background: #D4AF37; color: #0A1428; padding: 8px 20px; border-radius: 20px; font-size: 0.8rem; font-weight: bold; display: inline-block; }
.footer { color: rgba(255,255,255,0.3); font-size: 0.65rem; margin-top: 15px; }
</style></head><body>
<h1>🏆 Gullah Geechee Corridor — Restaurant Pins</h1>
<p style="text-align:center;color:rgba(255,255,255,0.5);margin-bottom:30px;">${restaurants.length} pins ready for screenshots</p>
<div class="grid">`;

restaurants.forEach((r, i) => {
  html += `
<div class="pin">
  <div class="emblem">GGB</div>
  <div class="name">${r.name}</div>
  <div class="town">📍 ${r.town}, SC</div>
  <div class="cuisine">${r.cuisine}</div>
  <div class="cta">Visit GullahGeecheeBiz.com</div>
  <div class="footer">GULLAH GEECHEE BIZ</div>
</div>`;
});

html += `\n</div>\n</body>\n</html>`;

writeFileSync(join(OUT_DIR, "restaurant-pins.html"), html);
console.log(`✅ Generated ${restaurants.length} restaurant pin previews at:`);
console.log(`   ${join(OUT_DIR, "restaurant-pins.html")}`);
console.log(`\nOpen this HTML file in a browser and take screenshots of each pin.`);
console.log(`Each pin is 9:16 aspect ratio (Pinterest format).`);
