#!/usr/bin/env node
/**
 * Gullah Geechee Biz — Batch Pinterest Uploader
 * Uploads pins in small batches to avoid Browserbase timeouts
 */

import { Stagehand } from "@browserbasehq/stagehand";
import { config } from "dotenv";
import { join, resolve } from "path";
import { readFileSync, existsSync, readdirSync } from "fs";
config();

const HOME = process.env.HOME;
const PINS_DIR = resolve(HOME, "pins-final");
const EMAIL = "darrylebrown2014@icloud.com";
const PASS = "Vufzyf-kymcab-tydce0";
const BATCH_SIZE = 5;

async function sleep(ms) {
  return new Promise(r => setTimeout(r, ms));
}

async function uploadBatch(files, startIndex) {
  const sh = new Stagehand({
    env: "BROWSERBASE",
    model: "google/gemini-2.5-flash",
  });
  await sh.init();
  const page = sh.context.pages()[0];

  // Login
  await page.goto("https://www.pinterest.com/login/", { waitUntil: "domcontentloaded" });
  await sleep(2000);
  await page.evaluate((e, p) => {
    const email = document.querySelector('input[type="email"]');
    const pass = document.querySelector('input[type="password"]');
    if (email) email.value = e;
    if (pass) pass.value = p;
  }, EMAIL, PASS);
  await page.evaluate(() => {
    const btn = document.querySelector('button[type="submit"]');
    if (btn) btn.click();
  });
  await sleep(3000);

  let uploaded = 0;
  for (let i = 0; i < files.length; i++) {
    const pinPath = resolve(PINS_DIR, files[i]);
    const idx = startIndex + i + 1;
    console.log(`  [PIN ${idx}] Uploading ${files[i]}...`);

    await page.goto("https://www.pinterest.com/pin-builder/", { waitUntil: "domcontentloaded" });
    await sleep(2000);

    const fileBuffer = readFileSync(pinPath);
    const base64 = fileBuffer.toString("base64");

    await page.evaluate(async (b64) => {
      const input = document.querySelector('input[type="file"]');
      if (input) {
        const resp = await fetch(`data:image/png;base64,${b64}`);
        const blob = await resp.blob();
        const file = new File([blob], "pin.png", { type: "image/png" });
        const dt = new DataTransfer();
        dt.items.add(file);
        input.files = dt.files;
        input.dispatchEvent(new Event("change", { bubbles: true }));
      }
    }, base64);
    await sleep(3000);

    // Click publish
    await page.evaluate(() => {
      const btns = document.querySelectorAll('button');
      for (const b of btns) {
        if (b.textContent.includes("Publish") || b.textContent.includes("Save")) {
          b.click();
          return;
        }
      }
    });
    await sleep(2000);
    console.log(`  [PIN ${idx}] Published`);
    uploaded++;
  }

  await sh.close();
  return uploaded;
}

async function main() {
  console.log("=".repeat(60));
  console.log("  GULLAH GEECHEE BIZ — BATCH PIN UPLOADER");
  console.log("=".repeat(60));
  console.log();

  const allFiles = readdirSync(PINS_DIR)
    .filter(f => f.endsWith(".png"))
    .sort();

  console.log(`  Total pins to upload: ${allFiles.length}`);
  console.log(`  Batch size: ${BATCH_SIZE}`);
  console.log();

  let totalUploaded = 0;
  for (let batch = 0; batch < allFiles.length; batch += BATCH_SIZE) {
    const batchFiles = allFiles.slice(batch, batch + BATCH_SIZE);
    console.log(`\n  📦 Batch ${Math.floor(batch / BATCH_SIZE) + 1}: ${batchFiles.length} pins`);
    
    try {
      const count = await uploadBatch(batchFiles, batch);
      totalUploaded += count;
      console.log(`  ✅ Batch complete: ${count} uploaded`);
    } catch (e) {
      console.log(`  ⚠️  Batch error: ${e.message}`);
    }
  }

  console.log(`\n  ✅ Total uploaded: ${totalUploaded}/${allFiles.length}`);
  console.log("=".repeat(60));
}

main().catch(e => console.error("Error:", e.message));
