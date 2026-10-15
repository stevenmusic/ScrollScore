// 用 App 的鋼琴引擎(取樣、逐音音色、音樂廳殘響、踏板共鳴、EQ、母帶鏈)演奏一份 MIDI 演奏(mid2json 轉好的 JSON),
// 跟同一份演奏的真實錄音比較音色/空間/力度(不含彈性速度與自動力度,因為時間與力度都照 MIDI)。
// 用法:node midi_render.mjs <notes.json> <out.wav>
import { chromium } from "playwright";
import http from "node:http"; import fs from "node:fs"; import path from "node:path"; import { createRequire } from "node:module";
const require = createRequire(import.meta.url);
const [jsonPath, outPath, setArg] = process.argv.slice(2);   // 第三個參數(可省略):{"MASTER.compRatio":2,...} 改設定物件的欄位
const ROOT = path.resolve(path.join(path.dirname(new URL(import.meta.url).pathname), "../.."));
const server = http.createServer((req, res) => { const p = path.join(ROOT, decodeURIComponent(req.url.split("?")[0])); if (!p.startsWith(ROOT) || !fs.existsSync(p) || fs.statSync(p).isDirectory()) { res.writeHead(404); return res.end(); } fs.createReadStream(p).pipe(res); });
await new Promise(r => server.listen(0, "127.0.0.1", r));
const browser = await chromium.launch(); const page = await browser.newPage();
page.on("pageerror", e => console.error("[pageerror]", e.message));
await page.route(/cdn\.jsdelivr\.net\/npm\/opensheetmusicdisplay/, r => r.fulfill({ path: require.resolve("opensheetmusicdisplay/build/opensheetmusicdisplay.min.js"), contentType: "text/javascript" }));
await page.route(/cdn\.jsdelivr\.net\/npm\/jszip/, r => r.fulfill({ path: require.resolve("jszip/dist/jszip.min.js"), contentType: "text/javascript" }));
await page.route(/raw\.githubusercontent\.com|tonejs\.github\.io|nbrosowsky/, r => r.abort());
const data = JSON.parse(fs.readFileSync(jsonPath, "utf8"));
await page.addInitScript(sec => {
  window.AudioContext = window.webkitAudioContext = function () { const c = new OfflineAudioContext(2, Math.ceil(48000 * (sec + 6)), 48000); c.resume = () => Promise.resolve(); window.__ctx = c; return c; };
}, data.sec);
await page.goto(`http://127.0.0.1:${server.address().port}/index.html`);
await page.waitForFunction(() => typeof loadPianoSamples === "function");
await page.evaluate(sets => { for (const [k, v] of Object.entries(sets)) { const [o, f] = k.split("."); eval(o)[f] = v; } }, JSON.parse(setArg || "{}"));
await page.evaluate(async d => {
  const hz = m => 440 * Math.pow(2, (m - 69) / 12);
  // 讓載入器照這份 MIDI 載需要的音 × 力度層
  events = d.notes.map(n => ({ tWhole: n.t, notes: [{ freq: hz(n.m), durWhole: n.d, pvel: n.v }] }));
  pedalRanges = d.pedals.map(([a, b]) => ({ start: a, end: b }));
  computePianoDynamics = () => {};
  pianoComputeNeeds = () => {
    const need = new Map();
    for (const n of d.notes) {
      const c = pianoCenterFor(n.m), L = pianoLayerFor(n.v), key = pianoNoteName(c) + "-v" + L;
      const e = need.get(key) || { key, c, L, uses: 0, sec: 0 }; e.uses++; e.sec = Math.max(e.sec, n.damp - n.t + 1); need.set(key, e);
    }
    return need;
  };
  ensureAudio();
  await masterReady;
  await loadPianoSamples();
  for (let i = 0; i < 100 && !pianoVerbUseHall(); i++) await new Promise(r => setTimeout(r, 50));
  const T0 = 0.2;
  pianoResetVoices();
  getPianoResonance();
  if (pianoResGate) { const p = pianoResGate.gain; p.setValueAtTime(0, 0); for (const [a, b] of d.pedals) { p.setTargetAtTime(1, T0 + a, PIANO_SYMPA.openTau); p.setTargetAtTime(0, T0 + b, PIANO_SYMPA.closeTau); } }
  for (const [a, b] of d.pedals) { const dn = pianoAux.pedalD1, up = pianoAux.pedalU1, g = PIANO_GAIN * Math.pow(10, (-20 + 1.5) / 20) * 0.6; if (dn) pianoOneShot(dn, T0 + a + 0.05, g * 0.8, 1, PIANO_VERB_SEND); if (up) pianoOneShot(up, T0 + b, g, 1, PIANO_VERB_SEND); }
  for (const n of [...d.notes].sort((x, y) => x.t - y.t)) playPianoNote(hz(n.m), T0 + n.t, n.d, false, n.ped, T0 + n.damp, null, n.v, false);
}, data);
const len = await page.evaluate(async () => { window.__buf = await __ctx.startRendering(); return __buf.length; });
const chans = [];
for (let c = 0; c < 2; c++) {
  const out = new Float32Array(len);
  for (let o = 0; o < len; o += 1 << 20) {
    const b64 = await page.evaluate(([c, o, n]) => { const d = __buf.getChannelData(c).subarray(o, o + n); const u = new Uint8Array(d.buffer, d.byteOffset, d.byteLength); let s = ""; for (let i = 0; i < u.length; i += 0x8000) s += String.fromCharCode.apply(null, u.subarray(i, i + 0x8000)); return btoa(s); }, [c, o, 1 << 20]);
    const b = Buffer.from(b64, "base64"); out.set(new Float32Array(b.buffer, b.byteOffset, b.byteLength / 4), o);
  }
  chans.push(out);
}
const off = Math.round(0.2 * 48000), n = len - off, hdr = Buffer.alloc(44), bytes = n * 8;
hdr.write("RIFF", 0); hdr.writeUInt32LE(36 + bytes, 4); hdr.write("WAVE", 8); hdr.write("fmt ", 12); hdr.writeUInt32LE(16, 16); hdr.writeUInt16LE(3, 20); hdr.writeUInt16LE(2, 22); hdr.writeUInt32LE(48000, 24); hdr.writeUInt32LE(384000, 28); hdr.writeUInt16LE(8, 32); hdr.writeUInt16LE(32, 34); hdr.write("data", 36); hdr.writeUInt32LE(bytes, 40);
const body = Buffer.alloc(bytes); for (let i = 0; i < n; i++) { body.writeFloatLE(chans[0][i + off], i * 8); body.writeFloatLE(chans[1][i + off], i * 8 + 4); }
fs.writeFileSync(outPath, Buffer.concat([hdr, body]));
console.error("wrote", outPath);
await browser.close(); server.close();
