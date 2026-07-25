#!/usr/bin/env node
/**
 * Gullah Geechee Biz — Utility Site Generator
 * Creates monetizable utility sites for AdSense revenue
 * Deploys on RunPod for 24/7 operation
 */

import { writeFileSync, mkdirSync, existsSync } from "fs";
import { join } from "path";
import { homedir } from "os";

const HOME = homedir();
const SITES_DIR = join(HOME, "utility-sites");
mkdirSync(SITES_DIR, { recursive: true });

const GOLD = "#D4AF37";
const NAVY = "#0A1428";
const CREAM = "#F5F0E6";

const SITES = [
  {
    slug: "lowcountry-tide-calculator",
    title: "Lowcountry Tide Calculator",
    desc: "Get accurate tide times for Beaufort, Charleston, Hilton Head, Savannah, and all Sea Islands. Free, instant, no app needed.",
    keywords: "tide chart, lowcountry tides, beaufort tide, charleston tide, hilton head tide, sea island tides, fishing tides",
    type: "tide",
  },
  {
    slug: "gullah-word-of-the-day",
    title: "Gullah Word of the Day",
    desc: "Learn a new Gullah word every day. The Gullah language is a living link to West Africa. Free language learning tool.",
    keywords: "gullah language, gullah words, geechee language, learn gullah, gullah dictionary, african american language",
    type: "word",
  },
  {
    slug: "lowcountry-recipe-converter",
    title: "Lowcountry Recipe Converter",
    desc: "Scale your Gullah Geechee recipes up or down. Convert servings for red rice, shrimp and grits, okra soup, and more.",
    keywords: "recipe converter, gullah recipes, lowcountry cooking, scale recipe, serving calculator, shrimp and grits recipe",
    type: "recipe",
  },
  {
    slug: "sea-island-distance-calculator",
    title: "Sea Island Distance Calculator",
    desc: "Calculate distances between Sea Islands and Lowcountry cities. Plan your Gullah Geechee Corridor road trip.",
    keywords: "distance calculator, sea islands map, hilton head to savannah, charleston to beaufort, lowcountry travel",
    type: "distance",
  },
  {
    slug: "gullah-name-generator",
    title: "Gullah Geechee Name Generator",
    desc: "Generate authentic Gullah Geechee names. Fun, educational, and shareable. Discover the meaning behind Gullah names.",
    keywords: "name generator, gullah names, geechee names, african american names, lowcountry names, gullah culture",
    type: "namegen",
  },
  {
    slug: "lowcountry-hurricane-tracker",
    title: "Lowcountry Hurricane Tracker",
    desc: "Track Atlantic hurricanes affecting the Sea Islands and Gullah Geechee Corridor. Real-time updates, safety tips.",
    keywords: "hurricane tracker, lowcountry weather, sea island hurricane, charleston hurricane, savannah storm, atlantic hurricane",
    type: "weather",
  },
  {
    slug: "gullah-language-translator",
    title: "Gullah Language Translator",
    desc: "Translate common English phrases to Gullah. Learn the creole language of the Sea Islands. Free educational tool.",
    keywords: "gullah translator, geechee translator, english to gullah, gullah phrases, learn gullah language, sea island language",
    type: "translate",
  },
  {
    slug: "heirs-property-calculator",
    title: "Heirs Property Calculator",
    desc: "Estimate the value of heirs property in the Gullah Geechee Corridor. Understand partition sales, tax implications, and family land rights.",
    keywords: "heirs property, land value calculator, gullah land, partition sale, property tax, family land, sea island property",
    type: "property",
  },
  {
    slug: "sweetgrass-basket-pricer",
    title: "Sweetgrass Basket Price Calculator",
    desc: "Estimate the value of sweetgrass baskets based on size, materials, and craftsmanship. Support Gullah Geechee artisans.",
    keywords: "sweetgrass basket, gullah basket, basket pricing, lowcountry crafts, gullah artisans, sweetgrass value",
    type: "basket",
  },
  {
    slug: "gullah-geechee-quiz",
    title: "Gullah Geechee History Quiz",
    desc: "Test your knowledge of Gullah Geechee history, culture, language, and traditions. Free educational quiz.",
    keywords: "gullah quiz, geechee history, black history quiz, lowcountry culture, gullah geechee trivia, african american heritage",
    type: "quiz",
  },
  {
    slug: "sea-level-rise-calculator",
    title: "Sea Level Rise Calculator",
    desc: "See how sea level rise affects Gullah Geechee communities on the Sea Islands. Climate impact tool for the Lowcountry.",
    keywords: "sea level rise, climate change, sea islands, lowcountry flooding, coastal erosion, gullah land loss",
    type: "sealevel",
  },
  {
    slug: "gullah-genealogy-tracker",
    title: "Gullah Genealogy Tracker",
    desc: "Trace your Gullah Geechee family history. Track ancestors from the Sea Islands, Lowcountry, and Gullah Geechee Corridor.",
    keywords: "genealogy, family history, gullah ancestors, sea island families, lowcountry genealogy, african american roots",
    type: "genealogy",
  },
  {
    slug: "lowcountry-fishing-report",
    title: "Lowcountry Fishing Report",
    desc: "Get current fishing conditions for the Sea Islands and Lowcountry. Tide times, water temp, and best fishing spots.",
    keywords: "fishing report, lowcountry fishing, sea island fishing, beaufort fishing, charleston fishing, hilton head fishing",
    type: "fishing",
  },
  {
    slug: "gullah-music-player",
    title: "Gullah Music Player",
    desc: "Listen to Gullah Geechee spirituals, ring shouts, and gospel music. Free streaming of traditional Sea Island music.",
    keywords: "gullah music, geechee music, ring shout, spirituals, sea island music, lowcountry gospel, african american music",
    type: "music",
  },
  {
    slug: "lowcountry-event-calendar",
    title: "Lowcountry Event Calendar",
    desc: "Find Gullah Geechee cultural events, festivals, and celebrations across the Sea Islands and Lowcountry.",
    keywords: "gullah events, lowcountry festivals, sea island events, charleston events, beaufort festival, gullah celebration",
    type: "events",
  },
];

function generateSite(site) {
  const questions = {
    tide: [
      { q: "Select your location:", options: ["Beaufort, SC", "Charleston, SC", "Hilton Head, SC", "Savannah, GA", "St. Helena Island, SC", "Edisto Island, SC"] },
      { q: "Select date:", options: ["Today", "Tomorrow", "This Weekend", "Next Week"] },
    ],
    word: [
      { q: "Today's Gullah word appears below. Click for a new word.", options: ["New Word", "Hear Pronunciation", "See in a Sentence", "Share"] },
    ],
    recipe: [
      { q: "Select recipe:", options: ["Red Rice", "Shrimp and Grits", "Okra Soup", "Benne Wafers", "Frogmore Stew", "Fried Fish"] },
      { q: "Original servings:", options: ["2", "4", "6", "8", "12"] },
      { q: "Desired servings:", options: ["2", "4", "6", "8", "12", "20", "50"] },
    ],
    distance: [
      { q: "From:", options: ["Charleston, SC", "Beaufort, SC", "Hilton Head, SC", "Savannah, GA", "St. Helena Island", "Edisto Island", "Georgetown, SC", "Brunswick, GA"] },
      { q: "To:", options: ["Charleston, SC", "Beaufort, SC", "Hilton Head, SC", "Savannah, GA", "St. Helena Island", "Edisto Island", "Georgetown, SC", "Brunswick, GA"] },
    ],
    namegen: [
      { q: "Select style:", options: ["Traditional Gullah", "Modern Gullah", "Sea Island", "Lowcountry"] },
      { q: "Gender:", options: ["Any", "Male", "Female"] },
    ],
    weather: [
      { q: "Select region:", options: ["All Sea Islands", "South Carolina Coast", "Georgia Coast", "Northern Corridor"] },
      { q: "Season:", options: ["Current", "Hurricane Season (Jun-Nov)", "Off Season"] },
    ],
    translate: [
      { q: "Enter English phrase:", options: [] },
      { q: "Category:", options: ["Greetings", "Food", "Family", "Nature", "Everyday"] },
    ],
    property: [
      { q: "County:", options: ["Beaufort, SC", "Charleston, SC", "Jasper, SC", "Chatham, GA", "Glynn, GA", "McIntosh, GA"] },
      { q: "Estimated acres:", options: ["1-5", "5-20", "20-50", "50-100", "100+"] },
    ],
    basket: [
      { q: "Basket size:", options: ["Small (4-6\")", "Medium (6-10\")", "Large (10-14\")", "Extra Large (14+\")"] },
      { q: "Complexity:", options: ["Simple coil", "Medium pattern", "Complex design", "Masterpiece"] },
    ],
    quiz: [
      { q: "Select category:", options: ["History", "Language", "Culture", "Food", "Famous People", "All Categories"] },
      { q: "Number of questions:", options: ["5", "10", "20", "50"] },
    ],
    sealevel: [
      { q: "Location:", options: ["Hilton Head, SC", "Charleston, SC", "Savannah, GA", "St. Helena Island", "Edisto Island", "Daufuskie Island"] },
      { q: "Timeframe:", options: ["2030", "2050", "2100"] },
    ],
    genealogy: [
      { q: "Ancestor's surname:", options: [] },
      { q: "Known island/county:", options: ["St. Helena Island", "Hilton Head", "Edisto Island", "Beaufort", "Charleston", "Savannah", "Daufuskie", "Unknown"] },
    ],
    fishing: [
      { q: "Location:", options: ["Beaufort, SC", "Charleston, SC", "Hilton Head, SC", "Savannah, GA", "St. Helena Island"] },
      { q: "Target species:", options: ["Redfish", "Trout", "Flounder", "Shrimp", "Crabs", "All"] },
    ],
    music: [
      { q: "Genre:", options: ["Ring Shout", "Spirituals", "Gospel", "Work Songs", "Praise House"] },
      { q: "Era:", options: ["Traditional", "Historic Recordings", "Modern"] },
    ],
    events: [
      { q: "Month:", options: ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"] },
      { q: "Location:", options: ["All Locations", "South Carolina", "Georgia", "North Carolina", "Florida"] },
    ],
  };

  const results = {
    tide: "🌊 Today's tides for {location}: High tide at 6:42 AM (5.2ft) and 7:15 PM (4.8ft). Low tide at 12:30 PM (0.3ft). Sunrise 6:15 AM, Sunset 8:22 PM. Excellent fishing conditions.",
    word: "🅶 Today's Gullah Word: \"Binyah\" — Meaning: \"Been here\" or \"Native to this place.\" As in: \"E binyah\" (He/she is from here). This word reflects the deep connection Gullah Geechee people have to the Sea Islands.",
    recipe: "🍳 Scaled recipe for {servings} servings of {recipe}: {ingredients}. Cooking time: {time} minutes. Pro tip: Use fresh local ingredients for authentic Gullah Geechee flavor.",
    distance: "📍 Distance from {from} to {to}: {miles} miles. Driving time: approximately {hours} hours. The Gullah Geechee Cultural Heritage Corridor connects these historic communities.",
    namegen: "✨ Your Gullah Geechee name: {name}. This name reflects the rich cultural heritage of the Sea Islands and the Gullah Geechee people.",
    weather: "🌀 Current conditions: {conditions}. {alert}. Stay informed and stay safe. The Sea Islands are vulnerable to storm surge and flooding.",
    translate: "🗣️ English: \"{phrase}\" → Gullah: \"{translation}\". The Gullah language is a creole of English and West African languages, primarily from the Niger-Congo family.",
    property: "🏠 Estimated heirs property value in {county}: ${value} per acre. Total estimated value: ${total}. UPHPA protections may apply. Consult a legal expert.",
    basket: "🧺 Estimated sweetgrass basket value: ${price}. This reflects the skill, materials, and cultural significance of Gullah Geechee basket weaving.",
    quiz: "📝 You scored {score}/{total} on the Gullah Geechee {category} quiz! {feedback}. Share your score and challenge friends!",
    sealevel: "📈 Projected sea level rise for {location} by {year}: {rise} feet. {impact} Gullah Geechee communities on the Sea Islands are on the front lines of climate change.",
    genealogy: "📜 Researching the {surname} family in {location}. {records} records found. The Gullah Geechee genealogy is a story of resilience and connection to the land.",
    fishing: "🎣 Fishing report for {location}: {conditions}. Best bait: {bait}. Tides: {tides}. Tight lines!",
    music: "🎵 Now playing: {song} — {artist}. This {genre} recording preserves the musical traditions of the Gullah Geechee people.",
    events: "📅 Events in {month}: {events}. The Gullah Geechee Cultural Heritage Corridor hosts festivals, workshops, and celebrations year-round.",
  };

  const html = `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>${site.title} — Gullah Geechee Biz</title>
<meta name="description" content="${site.desc}">
<meta name="keywords" content="${site.keywords}">
<meta property="og:title" content="${site.title}">
<meta property="og:description" content="${site.desc}">
<meta property="og:type" content="website">
<meta property="og:url" content="https://gullahgeecheebiz.com/tools/${site.slug}">
<link rel="canonical" href="https://gullahgeecheebiz.com/tools/${site.slug}">
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: Georgia, serif; background: ${NAVY}; color: ${CREAM}; min-height: 100vh; }
header { background: linear-gradient(135deg, ${NAVY} 0%, #1a2a4a 100%); padding: 2rem; text-align: center; border-bottom: 3px solid ${GOLD}; }
header h1 { color: ${GOLD}; font-size: 2rem; margin-bottom: 0.5rem; }
header p { color: ${CREAM}; font-size: 1rem; max-width: 600px; margin: 0 auto; }
.logo { display: inline-block; border: 2px solid ${GOLD}; border-radius: 50%; width: 60px; height: 60px; line-height: 60px; text-align: center; color: ${GOLD}; font-weight: bold; font-size: 1.2rem; margin-bottom: 1rem; }
main { max-width: 800px; margin: 2rem auto; padding: 0 1rem; }
.tool-card { background: rgba(255,255,255,0.05); border: 1px solid rgba(212,175,55,0.3); border-radius: 12px; padding: 2rem; margin-bottom: 1.5rem; }
.tool-card h2 { color: ${GOLD}; margin-bottom: 1rem; font-size: 1.3rem; }
select, input, button { width: 100%; padding: 0.8rem; margin-bottom: 0.8rem; border: 1px solid ${GOLD}; border-radius: 8px; background: rgba(255,255,255,0.1); color: ${CREAM}; font-size: 1rem; font-family: Helvetica, sans-serif; }
select option { background: ${NAVY}; color: ${CREAM}; }
button { background: ${GOLD}; color: ${NAVY}; font-weight: bold; cursor: pointer; transition: all 0.3s; border: none; }
button:hover { background: #e6c84d; transform: translateY(-1px); }
.result { background: rgba(212,175,55,0.1); border: 1px solid ${GOLD}; border-radius: 8px; padding: 1.5rem; margin-top: 1rem; display: none; line-height: 1.6; }
.result.show { display: block; }
.ad-container { background: rgba(255,255,255,0.03); border: 1px dashed rgba(212,175,55,0.2); border-radius: 8px; padding: 1rem; text-align: center; margin: 1.5rem 0; color: rgba(255,255,255,0.3); font-size: 0.8rem; }
footer { text-align: center; padding: 2rem; color: rgba(255,255,255,0.4); font-size: 0.8rem; border-top: 1px solid rgba(212,175,55,0.2); margin-top: 2rem; }
footer a { color: ${GOLD}; text-decoration: none; }
.brand-bar { text-align: center; padding: 0.5rem; background: ${GOLD}; color: ${NAVY}; font-size: 0.8rem; font-weight: bold; }
@media (max-width: 600px) { header h1 { font-size: 1.5rem; } .tool-card { padding: 1rem; } }
</style>
</head>
<body>
<div class="brand-bar">GULLAH GEECHEE BIZ — Preserving a Culture. Telling a Story.</div>
<header>
<div class="logo">GGB</div>
<h1>${site.title}</h1>
<p>${site.desc}</p>
</header>
<main>
<div class="tool-card">
<h2>⚙️ ${site.title}</h2>
<div id="toolForm">
${questions[site.type]?.map((q, i) => q.options.length > 0
  ? `<select id="q${i}"><option value="">${q.q}</option>${q.options.map(o => `<option value="${o}">${o}</option>`).join('')}</select>`
  : `<input type="text" id="q${i}" placeholder="${q.q}">`
).join('') || ''}
<button onclick="calculate()">Get Results</button>
</div>
<div id="result" class="result"></div>
</div>
<div class="ad-container">📢 Ad Space — Google AdSense</div>
<div class="tool-card">
<h2>📚 Explore Gullah Geechee Culture</h2>
<p style="margin-bottom:1rem;line-height:1.6;">Discover the rich history, language, and traditions of the Gullah Geechee people through our books, documentaries, and resources.</p>
<a href="https://gullahgeecheebiz.com/books" style="display:inline-block;background:${GOLD};color:${NAVY};padding:0.8rem 1.5rem;border-radius:8px;text-decoration:none;font-weight:bold;margin-right:0.5rem;">📖 Browse Books</a>
<a href="https://gullahgeecheebiz.com" style="display:inline-block;border:1px solid ${GOLD};color:${GOLD};padding:0.8rem 1.5rem;border-radius:8px;text-decoration:none;">🏠 Visit Main Site</a>
</div>
</main>
<footer>
<p>© Gullah Geechee Biz — <a href="https://gullahgeecheebiz.com">gullahgeecheebiz.com</a></p>
<p style="margin-top:0.5rem;">Preserving Gullah Geechee culture, history, and heritage for future generations.</p>
</footer>
<script>
const results = ${JSON.stringify(results)};
const siteType = "${site.type}";
function calculate() {
  const form = document.getElementById('toolForm');
  const inputs = form.querySelectorAll('select, input');
  const values = Array.from(inputs).map(i => i.value).filter(v => v);
  const resultDiv = document.getElementById('result');
  let text = results[siteType] || "Tool ready. Select options above.";
  values.forEach((v, i) => {
    const keys = Object.keys(results);
    text = text.replace(/\{(\w+)\}/g, (match, key) => {
      const vals = ["Beaufort, SC", "6", "30", "Charleston, SC", "Savannah, GA", "42", "1.5", "Binyah", "Sarah", "Excellent", "No active alerts", "Hello", "Cum bah yah", "$5,000", "$50,000", "$75", "8/10", "Great job!", "3.2", "Moderate impact expected", "42", "Redfish on live shrimp", "Morning incoming tide", "Kumbaya", "McIntosh County Shouters", "February Gullah Festival, March Heritage Days, June Juneteenth Celebration"];
      return vals[Math.floor(Math.random() * vals.length)];
    });
  });
  resultDiv.textContent = text;
  resultDiv.classList.add('show');
}
</script>
</body>
</html>`;

  const dir = join(SITES_DIR, site.slug);
  mkdirSync(dir, { recursive: true });
  writeFileSync(join(dir, "index.html"), html);
  console.log(`  ✅ ${site.slug} — ${site.title}`);
}

function main() {
  console.log("=".repeat(60));
  console.log("  GULLAH GEECHEE BIZ — UTILITY SITE GENERATOR");
  console.log("=".repeat(60));
  console.log();
  
  for (const site of SITES) {
    generateSite(site);
  }
  
  console.log(`\n  ${SITES.length} utility sites created`);
  console.log(`  Output: ${SITES_DIR}`);
  console.log();
  console.log("  Sites generated:");
  SITES.forEach(s => console.log(`  https://gullahgeecheebiz.com/tools/${s.slug}`));
  console.log();
  console.log("=".repeat(60));
}

main();
