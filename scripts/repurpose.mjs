#!/usr/bin/env node
/**
 * Gullah Geechee Biz — Content Repurposing Pipeline
 * Takes one piece of content and generates 10 formats
 */

import { existsSync, mkdirSync, writeFileSync } from "fs";
import { join } from "path";

const CONTENT_DIR = join(process.env.HOME, "gullahgeecheebiz-site", "content-pipeline");
const OUTPUT_DIR = join(process.env.HOME, "gullahgeecheebiz-site", "repurposed");

if (!existsSync(OUTPUT_DIR)) mkdirSync(OUTPUT_DIR, { recursive: true });

const TEMPLATES = {
  "tiktok-script": (title, body) => `[HOOK] "${body.split('.')[0]}"
[VISUAL] ${title} footage, slow motion, warm lighting
[BODY] "${body.substring(0, 200)}"
[CTA] "Follow @gullahgeecheebiz for more."
[HASHTAGS] #GullahGeechee #Lowcountry #Culture`,

  "pinterest-pin": (title, body) => `Title: ${title}
Description: ${body.substring(0, 500)}
CTA: Visit gullahgeecheebiz.com for the full story
Hashtags: #GullahGeechee #Lowcountry #Travel`,

  "substack-post": (title, body) => `# ${title}

${body}

---

*Gullah Geechee Biz — Preserving a Culture. Telling a Story.*

*[Subscribe](https://kofigullahgeecheebiz.substack.com) · [Follow on TikTok](https://www.tiktok.com/@gullahgeecheebiz)*`,

  "tweet": (title, body) => `${body.split('.')[0]}. 

Read more: gullahgeecheebiz.com

#GullahGeechee #Lowcountry`,

  "instagram-caption": (title, body) => `${title}

${body.substring(0, 300)}

Follow @gullahgeecheebiz for more Gullah Geechee content.

#GullahGeechee #Lowcountry #SouthCarolina #Georgia #History #Culture`,

  "email-brief": (title, body) => `Subject: ${title}

Hey,

${body.substring(0, 150)}...

[Read the full story on our website →]

— Darryl`,

  "youtube-description": (title, body) => `${title}

${body.substring(0, 300)}

📚 Get the books: gullahgeecheebiz.com
🎬 Watch the documentary: gullahgeecheebiz.com
🎧 Listen to audiobooks: gullahgeecheebiz.com

#GullahGeechee #Lowcountry #Documentary`,

  "facebook-post": (title, body) => `${title}

${body.substring(0, 400)}

👉 Follow Gullah Geechee Biz for more stories from the Corridor.`,

  "rumble-description": (title, body) => `${title}

${body.substring(0, 200)}

Subscribe to Gullah Geechee Biz for more content from the Gullah Geechee Corridor.`,

  "blog-seo": (title, body) => `---
title: "${title}"
description: "${body.substring(0, 160)}"
date: "${new Date().toISOString().split('T')[0]}"
tags: [gullah-geechee, lowcountry, culture, history]
---

# ${title}

${body}

---

*Published by Gullah Geechee Biz*
*[Subscribe to The Root](https://kofigullahgeecheebiz.substack.com)*
*[Follow on TikTok](https://www.tiktok.com/@gullahgeecheebiz)*`
};

function repurpose(title, body) {
  const slug = title.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/(^-|-$)/g, "");
  const postDir = join(OUTPUT_DIR, slug);
  if (!existsSync(postDir)) mkdirSync(postDir, { recursive: true });

  for (const [format, template] of Object.entries(TEMPLATES)) {
    const content = template(title, body);
    const ext = format.includes("blog") ? "md" : format.includes("script") ? "md" : "txt";
    writeFileSync(join(postDir, `${format}.${ext}`), content);
  }

  console.log(`✅ Repurposed "${title}" into 10 formats`);
  console.log(`   Output: ${postDir}`);
}

// Example usage
const sampleContent = {
  title: "The Gullah Geechee Alligator — 300 Years of Living Alongside the Marsh",
  body: "The American alligator has been swimming in Lowcountry waters for thousands of years. But for the Gullah Geechee people, the alligator is more than just an animal. It's a symbol of survival. Gullah Geechee ancestors learned to read the alligator's movements — where it basks, where it hunts, where it nests. These patterns told them about the health of the marsh, the quality of the water, and the best times to fish. Today, the alligator is one of the most iconic animals of the Gullah Geechee Corridor. A video of an alligator in a Lowcountry marsh recently went viral with over half a million views. People are fascinated by these ancient creatures. But the real story is the people who have lived alongside them for 300 years."
};

repurpose(sampleContent.title, sampleContent.body);

console.log("\n📋 Pipeline ready! To use:");
console.log("   node repurpose.mjs <title> <body>");
console.log("   Or import and call repurpose(title, body)");
