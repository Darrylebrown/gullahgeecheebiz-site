// bothealth_watcher.js — Publisher bot fleet health + emergency publish pause
// Cron: every 10–15 min on Hermes Mac / host
// Env: SLACK_WEBHOOK_URL, HEARTBEAT_FILE, PAUSE_FILE
import fs from 'fs';
import path from 'path';
import fetch from 'node-fetch';

const SLACK_WEBHOOK_URL = process.env.SLACK_WEBHOOK_URL || '';
const HEARTBEAT_FILE =
  process.env.HEARTBEAT_FILE || path.join(process.cwd(), 'heartbeats.json');
const PAUSE_FILE =
  process.env.PAUSE_FILE || path.join(process.cwd(), '.publish_pause');
const WARN_MS = Number(process.env.BOTHEALTH_WARN_MS || 20 * 60 * 1000);
const CRITICAL_MS = Number(process.env.BOTHEALTH_CRITICAL_MS || 40 * 60 * 1000);
const WARN_COUNT_PAUSE = Number(process.env.BOTHEALTH_WARN_PAUSE_COUNT || 3);

function nowISO() {
  return new Date().toISOString();
}

function loadHeartbeats() {
  try {
    const raw = fs.readFileSync(HEARTBEAT_FILE, 'utf8');
    const data = JSON.parse(raw);
    // allow { bots: [...] } or bare array
    if (Array.isArray(data)) return data;
    if (Array.isArray(data.bots)) return data.bots;
    if (Array.isArray(data.heartbeats)) return data.heartbeats;
    return [];
  } catch (e) {
    return [];
  }
}

async function postSlack(msg) {
  if (!SLACK_WEBHOOK_URL) {
    console.log('[Slack]', msg);
    return;
  }
  try {
    await fetch(SLACK_WEBHOOK_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text: msg }),
    });
  } catch (e) {
    console.error('Slack post failed', e);
  }
}

/**
 * Other bots call this to record liveness.
 * @param {string} bot_id
 * @param {'ok'|'warn'|'critical'} status
 * @param {string} [details]
 */
export function writeHeartbeat(bot_id, status = 'ok', details = '') {
  let list = loadHeartbeats();
  const entry = {
    bot_id,
    status,
    details: details || '',
    ts: nowISO(),
  };
  const i = list.findIndex((h) => h.bot_id === bot_id);
  if (i >= 0) list[i] = entry;
  else list.push(entry);
  fs.writeFileSync(HEARTBEAT_FILE, JSON.stringify(list, null, 2));
  return entry;
}

export function isPublishPaused() {
  return fs.existsSync(PAUSE_FILE);
}

export function clearPublishPause() {
  if (fs.existsSync(PAUSE_FILE)) fs.unlinkSync(PAUSE_FILE);
}

async function main() {
  const hbs = loadHeartbeats();
  const warnings = [];
  const criticals = [];
  const now = Date.now();

  if (hbs.length === 0) {
    await postSlack(
      'BOT HEALTH — no heartbeats file/entries yet (heartbeats.json empty). Fleet not reporting.'
    );
    console.log('bothealth done — empty');
    return;
  }

  for (const hb of hbs) {
    const ts = Date.parse(hb.ts);
    const age = Number.isFinite(ts) ? now - ts : CRITICAL_MS + 1;
    const bot = hb.bot_id || 'unknown';

    if (age > CRITICAL_MS) {
      criticals.push({ bot, reason: `no heartbeat >${Math.round(CRITICAL_MS / 60000)}m` });
    } else if (age > WARN_MS) {
      warnings.push({ bot, reason: `no heartbeat >${Math.round(WARN_MS / 60000)}m` });
    } else if (hb.status === 'warn') {
      warnings.push({ bot, reason: hb.details || 'status=warn' });
    } else if (hb.status === 'critical') {
      criticals.push({ bot, reason: hb.details || 'status=critical' });
    }
  }

  const summary =
    `BOT HEALTH — warnings:${warnings.length} criticals:${criticals.length}` +
    (warnings.length
      ? `\nWarn: ${warnings.map((w) => `${w.bot}(${w.reason})`).join(', ')}`
      : '') +
    (criticals.length
      ? `\nCrit: ${criticals.map((c) => `${c.bot}(${c.reason})`).join(', ')}`
      : '');

  await postSlack(summary);

  if (criticals.length > 0 || warnings.length >= WARN_COUNT_PAUSE) {
    fs.writeFileSync(
      PAUSE_FILE,
      JSON.stringify(
        {
          ts: nowISO(),
          warnings: warnings.length,
          criticals: criticals.length,
          detail_warnings: warnings,
          detail_criticals: criticals,
          brand: 'Gullah Geechee Biz',
        },
        null,
        2
      )
    );
    await postSlack(
      ':rotating_light: EMERGENCY PAUSE engaged — publishing paused. Clear `.publish_pause` after fix.'
    );
  }

  console.log('bothealth done', {
    warnings: warnings.length,
    criticals: criticals.length,
    paused: isPublishPaused(),
  });
}

// Run when executed directly
const isMain =
  process.argv[1] &&
  (process.argv[1].endsWith('bothealth_watcher.js') ||
    process.argv[1].includes('bothealth_watcher'));

if (isMain) {
  main().catch((e) => {
    console.error(e);
    process.exit(1);
  });
}

export { main as runBotHealth };
