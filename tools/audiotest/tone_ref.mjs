// 產生自己的音源頻譜對齊的參考表 USER_PIANO_TONE.ref:用 App 的內建鋼琴(取樣 + PIANO_TONE + PIANO_EQ + PIANO_WIDTH,不含殘響/共鳴)
// 照 USER_PIANO_TONE.probes × vels 各彈一個音,在 masterGain 量 toneBands(跟自己的音源同一個函式)。
// 用法:node tone_ref.mjs > ref.json(印出 JSON,貼進 index.html 的 USER_PIANO_TONE.ref)
import { chromium } from "playwright";
import http from "node:http"; import fs from "node:fs"; import path from "node:path"; import { createRequire } from "node:module";
const require = createRequire(import.meta.url);
const ROOT = path.resolve(path.join(path.dirname(new URL(import.meta.url).pathname), "../.."));
const server = http.createServer((req, res) => { const p = path.join(ROOT, decodeURIComponent(req.url.split("?")[0])); if (!p.startsWith(ROOT) || !fs.existsSync(p) || fs.statSync(p).isDirectory()) { res.writeHead(404); return res.end(); } fs.createReadStream(p).pipe(res); });
await new Promise(r => server.listen(0, "127.0.0.1", r));
const browser = await chromium.launch(); const page = await browser.newPage();
page.on("pageerror", e => console.error("[pageerror]", e.message));
page.on("console", m => { if (/error/i.test(m.type())) console.error("[console]", m.text()); });
await page.route(/cdn\.jsdelivr\.net\/npm\/opensheetmusicdisplay/, r => r.fulfill({ path: require.resolve("opensheetmusicdisplay/build/opensheetmusicdisplay.min.js"), contentType: "text/javascript" }));
await page.route(/cdn\.jsdelivr\.net\/npm\/jszip/, r => r.fulfill({ path: require.resolve("jszip/dist/jszip.min.js"), contentType: "text/javascript" }));
await page.route(/raw\.githubusercontent\.com|tonejs\.github\.io|nbrosowsky|fonts\.g/, r => r.abort());
const GAP = 3, T0 = 0.3;
await page.addInitScript(([gap, t0]) => {
  window.REVERB_OVERRIDE = 0;
  window.PIANO_VARY_OVERRIDE = { layerZone: 0, presDb: 0, airDb: 0, attack: 0, gainDb: 0, damper: 0 };
  window.PIANO_XFADE_OVERRIDE = { jitter: 0 };
  window.AudioContext = window.webkitAudioContext = function () { const c = new OfflineAudioContext(2, Math.ceil(48000 * (t0 + 48 * gap + 3)), 48000); c.resume = () => Promise.resolve(); window.__ctx = c; return c; };
}, [GAP, T0]);
await page.goto(`http://127.0.0.1:${server.address().port}/index.html`);
await page.waitForFunction(() => typeof loadPianoSamples === "function" && typeof toneBands === "function");
const out = await page.evaluate(async ([gap, t0]) => {
  const T = USER_PIANO_TONE, hz = m => 440 * Math.pow(2, (m - 69) / 12), list = [];
  T.vels.forEach(v => T.probes.forEach(p => list.push({ m: p, v, t: t0 + list.length * gap })));
  events = list.map(n => ({ tWhole: n.t, notes: [{ freq: hz(n.m), durWhole: 2.5, pvel: n.v }] }));
  pedalRanges = []; pianoRanges = () => [];
  computePianoDynamics = () => {};
  pianoComputeNeeds = () => { const need = new Map(); for (const n of list) { const c = pianoCenterFor(n.m); for (const L of [pianoLayerFor(n.v)]) { const key = pianoNoteName(c) + "-v" + L; need.set(key, { key, c, L, uses: 1, sec: 4 }); } } return need; };
  ensureAudio(); await masterReady; await loadPianoSamples();
  getPianoBus(); masterGain.disconnect(); masterGain.connect(__ctx.destination);
  pianoResetVoices();
  for (const n of list) playPianoNote(hz(n.m), n.t, 2.5, false, false, n.t + 2.5, null, n.v, false);
  const buf = await __ctx.startRendering(), L = buf.getChannelData(0), R = buf.getChannelData(1), sr = buf.sampleRate;
  const tab = T.vels.map(() => []);
  list.forEach((n, i) => { const a = Math.round((n.t - 0.01) * sr), b = Math.round((n.t + gap - 0.05) * sr);
    const e = toneBands(L.subarray(a, b), R.subarray(a, b), sr, null, T.sec);
    tab[T.vels.indexOf(n.v)].push({ m: e.m.map(x => +x.toPrecision(4)), s: e.s.map(x => +x.toPrecision(4)) }); });
  return tab;
}, [GAP, T0]);
console.log(JSON.stringify(out));
await browser.close(); server.close();
