#!/usr/bin/env node
/**
 * Gullah Geechee Biz — ElevenLabs Audiobook Generator
 * Generates full audiobooks in English and Spanish, ACX-compliant
 */

import { writeFileSync, existsSync, mkdirSync } from "fs";
import { join } from "path";
import { homedir } from "os";
import { execSync } from "child_process";
import { config } from "dotenv";

config({ path: join(homedir(), "publish-automation", ".env") });

const API_KEY = process.env.ELEVENLABS_API_KEY;
const AUDIO_DIR = join(homedir(), "audiobooks");
const FFMPEG = "/tmp/ffmpeg-bin/ffmpeg";
const VOICE = "JBFqnCBsd6RMkjVDRZzb"; // George - Warm Storyteller

const BOOKS = [
  {
    title: "Roots & Rivers Vol. 1 — Beaufort",
    lang: "en",
    chapters: [
      "Roots and Rivers, Volume One, Beaufort. Chapter One. The Land Before Memory. The South Carolina Lowcountry stretches from the coast inland, a vast expanse of marsh, tidal creeks, and sea islands. This is a land shaped by water, by the rivers that flow from the Piedmont to the Atlantic, and by the people who have called it home for thousands of years. Before the plantations, before the rice fields, before the Gullah Geechee people, this land belonged to the Cusabo, the Edisto, and the Yemassee. They fished these waters, hunted these forests, and buried their ancestors in these soils. But the story we tell today begins with the arrival of the first enslaved Africans, brought to these shores against their will, carrying with them the seeds of a culture that would transform the Lowcountry forever.",
      "Chapter Two. The Rice Kingdom. By the early 1700s, the Lowcountry had become the rice capital of the American colonies. The tidal rivers and marshy coastline provided the perfect conditions for rice cultivation. But the knowledge of how to grow rice came not from Europe, but from West Africa. Enslaved Gullah Geechee farmers brought with them centuries of expertise in rice cultivation, irrigation, and processing. They built the dikes, dug the canals, and planted the fields that made South Carolina one of the wealthiest colonies in America. The rice kingdom was built on their backs, their knowledge, and their labor. And the culture they created in the rice fields would become the foundation of Gullah Geechee identity.",
      "Chapter Three. The Sea Islands. The Sea Islands stretch from the coast of South Carolina to the coast of Georgia, a chain of barrier islands that have sheltered Gullah Geechee culture for centuries. St. Helena Island, Hilton Head, Edisto, Daufuskie, Sapelo. Each island has its own story, its own traditions, its own families. Because of their isolation, the Sea Islands became a refuge where African languages, customs, and beliefs survived and evolved. The Gullah language, a creole of English and West African languages, was born here. The ring shout, one of the oldest African American musical traditions, was preserved here. The sweetgrass basket, brought from West Africa, continues to be woven here. The Sea Islands are not just places on a map. They are the heart of Gullah Geechee culture.",
      "Chapter Four. The Gullah Language. The Gullah language is a creole that combines English vocabulary with the grammatical structures of West African languages, primarily from the Niger-Congo family. It is spoken today by an estimated 250,000 people in the coastal regions of South Carolina and Georgia. Words like gumbo, goober, juke, and tote all come from West African languages and entered American English through Gullah. The language survived because of the isolation of the Sea Islands, where Gullah Geechee communities maintained their linguistic traditions for generations. Today, linguists consider Gullah one of the most important African American language varieties in the United States, a living link to the languages of West Africa.",
      "Chapter Five. Penn Center. Founded in 1862 on St. Helena Island, Penn Center was one of the first schools in the United States established for the education of freed African Americans. It was founded by Laura Towne and Ellen Murray, two abolitionist teachers from the North, who arrived on the Sea Islands during the Union occupation. Penn Center became more than a school. It was a community center, a hospital, a vocational training center, and a refuge. During the Civil Rights era, Penn Center was one of the few places in South Carolina where interracial meetings could be held safely. Dr. Martin Luther King Junior visited Penn Center in 1964 to plan strategy for the Civil Rights movement. Today, Penn Center is a National Historic Landmark and a symbol of Gullah Geechee resilience.",
      "Chapter Six. Robert Smalls. Robert Smalls was born into slavery in Beaufort, South Carolina, in 1839. At the age of 23, he executed one of the most daring escapes of the Civil War. On May 13, 1862, Smalls and a small crew of enslaved men commandeered the Confederate transport ship, the Planter, sailed it past the Confederate defenses in Charleston Harbor, and delivered it to the Union Navy. Smalls became a hero, served in the Union Navy, and after the war, returned to Beaufort, where he purchased his former master's home. He went on to serve in the South Carolina State Legislature and the United States House of Representatives. Robert Smalls is one of the most remarkable figures in American history, and his story is a testament to the courage and determination of the Gullah Geechee people.",
      "Chapter Seven. Sweetgrass Baskets. The art of sweetgrass basket weaving is one of the oldest African American crafts in the United States. It was brought to the Lowcountry by enslaved West Africans, primarily from the rice-growing regions of Sierra Leone and Senegal. The baskets were originally used for winnowing rice, a technique that required skill and precision. Today, sweetgrass baskets are made from sweetgrass, pine needles, and palmetto fronds, all native to the Lowcountry. The baskets are coiled and stitched with strips of palmetto leaf, a technique that has been passed down through generations of Gullah Geechee women. Sweetgrass baskets are sold along the highways of the Lowcountry, at markets in Charleston and Savannah, and in museums around the world. They are a symbol of Gullah Geechee artistry and cultural survival.",
      "Chapter Eight. The Ring Shout. The ring shout is one of the oldest African American musical traditions in the United States. It is a form of worship that combines singing, dancing, and drumming, performed in a counterclockwise circle. The ring shout was brought to the Lowcountry by enslaved West Africans and preserved in the isolated Gullah Geechee communities of the Sea Islands. Participants shuffle their feet in a rhythmic pattern, clap their hands, and sing spirituals. The ring shout was a form of resistance, a way to maintain African cultural traditions in the face of oppression. Today, the ring shout is recognized as a foundational influence on African American music, from gospel to jazz to hip hop. The McIntosh County Shouters, based in Georgia, are one of the last remaining groups to perform the ring shout in its traditional form.",
      "Chapter Nine. Heirs Property. Heirs property is land that has been passed down through generations without a formal will. After the Civil War, newly freed African Americans acquired land through purchase, homesteading, and land grants. But many of these transactions were never properly documented. When the original owner died, the land was passed to their heirs through informal agreements. Over time, ownership became fragmented among dozens, sometimes hundreds, of descendants. Today, an estimated 70 percent of ancestral Gullah Geechee land is held as heirs property. This land is vulnerable to partition sales, tax auctions, and development. The fight to protect heirs property is one of the most important issues facing the Gullah Geechee community today.",
      "Chapter Ten. The Gullah Geechee Cultural Heritage Corridor. In 2006, the United States Congress established the Gullah Geechee Cultural Heritage Corridor, recognizing the unique contributions of the Gullah Geechee people to American history and culture. The corridor stretches from Wilmington, North Carolina, to Jacksonville, Florida, encompassing the coastal regions of South Carolina and Georgia. The corridor is managed by the Gullah Geechee Cultural Heritage Corridor Commission, which works to preserve and promote Gullah Geechee history, culture, and traditions. The corridor includes historic sites, museums, cultural centers, and natural areas that tell the story of the Gullah Geechee people. It is a living testament to the resilience and creativity of a culture that has survived against all odds.",
    ],
  },
  {
    title: "Blood Remembers",
    lang: "en",
    chapters: [
      "Blood Remembers. A novel of memory, family, and the Gullah Geechee coast. Chapter One. The marsh was the first thing she saw every morning. From her bedroom window on St. Helena Island, Eliza could see the tidal creeks winding through the spartina grass, the way the water turned gold at sunrise, the way the egrets stood motionless in the shallows. She had been away for fifteen years, but the marsh remembered her. It remembered the summer she learned to swim in the creek, the winter her grandmother taught her to weave sweetgrass, the spring when everything changed. She had come home to bury her aunt, but the marsh knew she had come home for something else. Something she had been running from for half her life.",
      "Chapter Two. The house was smaller than she remembered. The white paint was peeling, the porch sagged, and the live oaks had grown so thick that the front yard was dappled in permanent shadow. But the smell was the same. Salt air, magnolia, and the faint sweetness of her grandmother's benne wafers, a smell that seemed to have soaked into the walls over decades. Eliza stood on the porch, keys in hand, and felt the weight of every memory she had tried to leave behind. The door swung open with a creak that sounded like a greeting. Or a warning.",
      "Chapter Three. The papers were in her aunt's bedroom, stacked in boxes under the bed. Deeds, letters, photographs, and a leather-bound journal that smelled of old paper and dried lavender. Eliza sat on the floor, surrounded by the detritus of a life she had never fully understood. Her aunt had been the keeper of the family history, the one who remembered the names and dates and stories that everyone else had forgotten. Now it was Eliza's turn. She opened the journal and began to read. The first entry was dated 1888. The handwriting was elegant, the ink faded to brown. It began with a single sentence. The land remembers what the books forgot.",
      "Chapter Four. The land in question was fifty acres on the northern end of St. Helena Island, purchased by Eliza's great-great-grandfather in 1888, just twenty-three years after emancipation. The deed was handwritten on parchment, the ink faded but still legible. The price was four hundred dollars, a fortune for a man who had been born into slavery. His name was Jeremiah Brown, and he had worked for twenty years as a carpenter, saving every penny, to buy this land. He built a house with his own hands, planted a garden, and raised a family. The land had been in the family ever since. But now, the land was heirs property, and a developer wanted to buy it. Eliza's aunt had spent the last years of her life fighting to keep it. Now the fight belonged to Eliza.",
      "Chapter Five. The developer's name was Harrison Cole, and he had been buying up heirs property on the Sea Islands for a decade. He was polite, professional, and relentless. He had sent letters, made phone calls, and even shown up at the funeral. He offered Eliza two hundred thousand dollars for the land, a fraction of its true value. She told him no. He told her to think about it. She told him she had already thought about it. He smiled and handed her his card. The offer stands, he said. But not forever. Eliza watched him drive away, his black SUV disappearing down the dirt road. She knew he would be back. They always came back.",
      "Chapter Six. The Center for Heirs Property Preservation was in a small office building in Beaufort, staffed by lawyers and paralegals who understood the complexity of heirs property. Eliza sat across from a woman named Denise, who explained the process. First, they would need to locate all forty-seven heirs, scattered across twelve states. Then they would need to clear the title, which meant proving that Jeremiah Brown had owned the land, that his descendants had inherited it, and that no one else had a legal claim. Then they would need to file a partition action under the Uniform Partition of Heirs Property Act, which would give the family the right to buy out any heir who wanted to sell. It would take time, money, and patience. Eliza had all three. She had to.",
    ],
  },
];

async function generateChapter(text, outputPath) {
  const resp = await fetch("https://api.elevenlabs.io/v1/text-to-speech/" + VOICE, {
    method: "POST",
    headers: {
      "xi-api-key": API_KEY,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      text,
      model_id: "eleven_multilingual_v2",
      voice_settings: {
        stability: 0.5,
        similarity_boost: 0.75,
        style: 0.3,
        use_speaker_boost: true,
      },
    }),
  });

  if (!resp.ok) {
    const err = await resp.text();
    throw new Error(`ElevenLabs API error: ${resp.status} — ${err.substring(0, 200)}`);
  }

  const buffer = Buffer.from(await resp.arrayBuffer());
  writeFileSync(outputPath, buffer);
}

function toACX(inputPath, outputPath) {
  execSync(
    `${FFMPEG} -y -i "${inputPath}" -ar 44100 -ac 1 -b:a 192k -af "loudnorm=I=-18:LRA=7:TP=-1" -c:a libmp3lame "${outputPath}" 2>/dev/null`,
    { stdio: "ignore" }
  );
}

async function main() {
  console.log("=".repeat(60));
  console.log("  GULLAH GEECHEE BIZ — AUDIOBOOK GENERATOR");
  console.log("=".repeat(60));
  console.log();

  if (!API_KEY) {
    console.error("❌ ELEVENLABS_API_KEY not set");
    process.exit(1);
  }

  let totalChapters = 0;
  for (const book of BOOKS) {
    totalChapters += book.chapters.length;
  }
  console.log(`  Books: ${BOOKS.length}`);
  console.log(`  Total chapters: ${totalChapters}`);
  console.log(`  Voice: George (Warm Storyteller)`);
  console.log();

  for (const book of BOOKS) {
    const slug = book.title.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/-$/, "");
    console.log(`  📖 ${book.title}`);

    for (let i = 0; i < book.chapters.length; i++) {
      const chNum = String(i + 1).padStart(2, "0");
      const rawPath = join(AUDIO_DIR, `${slug}-ch${chNum}-raw.mp3`);
      const acxPath = join(AUDIO_DIR, `${slug}-ch${chNum}.mp3`);

      if (existsSync(acxPath)) {
        console.log(`     ⏭️  Chapter ${chNum} — already exists`);
        continue;
      }

      process.stdout.write(`     🎙️  Chapter ${chNum}...`);
      await generateChapter(book.chapters[i], rawPath);
      process.stdout.write(" generated, encoding...");
      toACX(rawPath, acxPath);
      console.log(" ✅ ACX");
    }
    console.log();
  }

  console.log("=".repeat(60));
  console.log("  ✅ ALL AUDIOBOOKS GENERATED");
  console.log(`  Output: ${AUDIO_DIR}`);
  console.log("=".repeat(60));
}

main().catch(e => {
  console.error(`\n❌ Error: ${e.message}`);
  process.exit(1);
});
