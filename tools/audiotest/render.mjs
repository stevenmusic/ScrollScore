// 離線算出 ScrollScore 的實際輸出(跟網頁播放走同一條音訊路徑),存成 32-bit float WAV。
// 用法:node render.mjs <樂譜> <輸出.wav> [--inst piano|drum] [--tempo N] [--reverb N] [--sec 最長秒數] [--taps]
//   --taps:多存 2 聲道 = masterGain(響度壓縮器之前的鋼琴/吉他總和),共 4 聲道
// 需要:npm i playwright opensheetmusicdisplay@2.0.0 jszip(在 NODE_PATH 或本目錄)
// 雲端環境 jsdelivr 被擋,所以 OSMD/JSZip 從 npm 拿,用 page.route 攔截
import { chromium } from "playwright";
import http from "node:http";
import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const args = process.argv.slice(2);
const opt = (k, d) => { const i = args.indexOf("--" + k); return i >= 0 ? args[i + 1] : d; };
// --root:要測的 ScrollScore 目錄(預設本 repo),拿來跟舊版本 A/B
const ROOT = path.resolve(opt("root", path.join(path.dirname(new URL(import.meta.url).pathname), "../..")));
const flag = k => args.includes("--" + k);
const [scorePath, outPath] = args;
if (!scorePath || !outPath) { console.error("usage: node render.mjs score.xml out.wav [--inst piano] [--tempo N] [--taps] [--root 目錄] [--set JSON(改 MASTER/DRUM_BUS 等參數)]"); process.exit(1); }

const MIME = { ".html": "text/html", ".json": "application/json", ".flac": "audio/flac", ".js": "text/javascript" };
const server = http.createServer((req, res) => {
  const p = path.join(ROOT, decodeURIComponent(req.url.split("?")[0]));
  if (!p.startsWith(ROOT) || !fs.existsSync(p) || fs.statSync(p).isDirectory()) { res.writeHead(404); return res.end(); }
  res.writeHead(200, { "content-type": MIME[path.extname(p)] || "application/octet-stream" });
  fs.createReadStream(p).pipe(res);
});
await new Promise(r => server.listen(0, "127.0.0.1", r));
const port = server.address().port;

const browser = await chromium.launch({ args: ["--autoplay-policy=no-user-gesture-required"] });
const page = await browser.newPage();
page.on("pageerror", e => console.error("[pageerror]", e.message));
page.on("console", m => { if (m.type() === "error") console.error("[console]", m.text()); });
await page.route(/cdn\.jsdelivr\.net\/npm\/opensheetmusicdisplay/, r => r.fulfill({ path: require.resolve("opensheetmusicdisplay/build/opensheetmusicdisplay.min.js"), contentType: "text/javascript" }));
await page.route(/cdn\.jsdelivr\.net\/npm\/jszip/, r => r.fulfill({ path: require.resolve("jszip/dist/jszip.min.js"), contentType: "text/javascript" }));
await page.route(/raw\.githubusercontent\.com|tonejs\.github\.io|nbrosowsky/, r => r.abort());   // 只測本機取樣
const TAPS = flag("taps") ? 4 : 2;
await page.addInitScript(([taps, fixedSec]) => {
  // AudioContext 換成 OfflineAudioContext:長度在第一次建立時依樂譜長度決定
  window.AudioContext = window.webkitAudioContext = function () {
    const sec = Math.min(fixedSec || 1e9, (typeof totalSec === "function" && totalSec() > 0) ? totalSec() + 9 : 600);
    const ctx = new OfflineAudioContext(taps, Math.ceil(48000 * sec), 48000);
    ctx.resume = () => Promise.resolve();
    window.__ctx = ctx;
    return ctx;
  };
}, [TAPS, +opt("sec", 0)]);
await page.goto(`http://127.0.0.1:${port}/index.html`);
await page.waitForFunction(() => typeof loadScoreFile === "function");
const inst = opt("inst", null);
// --set '{"MASTER.makeup":1.4,"DRUM_BUS.makeup":0.8}':在樂譜載入前改全域設定物件的欄位
const sets = JSON.parse(opt("set", "{}"));
await page.evaluate(sets => { for (const [k, v] of Object.entries(sets)) { const [o, f] = k.split("."); eval(o)[f] = v; } }, sets);
await page.evaluate(i => { try { localStorage.clear(); } catch (e) {} if (i) $("instrument").value = i; }, inst);
await page.setInputFiles("#fileInput", path.resolve(scorePath));
await page.waitForFunction(() => typeof events !== "undefined" && events.length > 0 && typeof totalWhole !== "undefined" && totalWhole > 0, null, { timeout: 120000 });
if (inst) await page.evaluate(i => { $("instrument").value = i; }, inst);
const tempo = opt("tempo", null), reverb = opt("reverb", null);
await page.evaluate(([t, rv]) => {
  if (t) applyTempo(+t);
  if (rv != null) { $("reverbAmount").value = rv; }
}, [tempo, reverb]);
const info = await page.evaluate(async () => {
  const hasDrum = events.some(e => e.notes.some(n => n.drum));
  const hasPitched = events.some(e => e.notes.some(n => !n.drum && n.freq));
  if (hasPitched) await loadInstrumentSamples(currentInstrument());
  if (hasDrum) await loadDrumKit();
  ensureAudio();
  const worklet = typeof masterReady !== "undefined" ? await masterReady : null;
  return { worklet, hasDrum, hasPitched, total: totalSec(), inst: currentInstrument(), len: __ctx.length / 48000, tempo: bpm() };
});
console.error("info", JSON.stringify(info));
const t0 = Date.now();
const nch = await page.evaluate(async taps => {
  const ctx = __ctx;
  if (taps === 4) {
    masterOut.disconnect();
    const m = ctx.createChannelMerger(4), s1 = ctx.createChannelSplitter(2), s2 = ctx.createChannelSplitter(2);
    masterOut.connect(s1); s1.connect(m, 0, 0); s1.connect(m, 1, 1);
    (typeof masterBus !== "undefined" && masterBus ? masterBus : masterGain).connect(s2); s2.connect(m, 0, 2); s2.connect(m, 1, 3);
    ctx.destination.channelInterpretation = "discrete";
    m.connect(ctx.destination);
  }
  startAudioFrom(0);
  window.__buf = await ctx.startRendering();
  return window.__buf.numberOfChannels;
}, TAPS);
console.error("rendered in", (Date.now() - t0) / 1000, "s");
// 分段取回 float32
const len = await page.evaluate(() => __buf.length);
const chans = [];
const CH = 1 << 20;
for (let c = 0; c < nch; c++) {
  const out = new Float32Array(len);
  for (let o = 0; o < len; o += CH) {
    const b64 = await page.evaluate(([c, o, n]) => {
      const d = __buf.getChannelData(c).subarray(o, o + n);
      const u = new Uint8Array(d.buffer, d.byteOffset, d.byteLength);
      let s = ""; for (let i = 0; i < u.length; i += 0x8000) s += String.fromCharCode.apply(null, u.subarray(i, i + 0x8000));
      return btoa(s);
    }, [c, o, CH]);
    const bytes = Buffer.from(b64, "base64");
    out.set(new Float32Array(bytes.buffer, bytes.byteOffset, bytes.byteLength / 4), o);
  }
  chans.push(out);
}
// 去掉尾端靜音
let end = len;
while (end > 48000 && Math.abs(chans[0][end - 1]) < 1e-5 && Math.abs(chans[1][end - 1]) < 1e-5) end--;
end = Math.min(len, end + 4800);
const hdr = Buffer.alloc(44), dataBytes = end * nch * 4;
hdr.write("RIFF", 0); hdr.writeUInt32LE(36 + dataBytes, 4); hdr.write("WAVE", 8); hdr.write("fmt ", 12);
hdr.writeUInt32LE(16, 16); hdr.writeUInt16LE(3, 20); hdr.writeUInt16LE(nch, 22); hdr.writeUInt32LE(48000, 24);
hdr.writeUInt32LE(48000 * nch * 4, 28); hdr.writeUInt16LE(nch * 4, 32); hdr.writeUInt16LE(32, 34); hdr.write("data", 36); hdr.writeUInt32LE(dataBytes, 40);
const body = Buffer.alloc(dataBytes);
for (let i = 0; i < end; i++) for (let c = 0; c < nch; c++) body.writeFloatLE(chans[c][i], (i * nch + c) * 4);
fs.writeFileSync(outPath, Buffer.concat([hdr, body]));
console.error("wrote", outPath, (end / 48000).toFixed(1) + "s", nch + "ch");
await browser.close(); server.close();
