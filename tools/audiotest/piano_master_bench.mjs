// 離線測試台:把 render.mjs --taps --tapsrc mg 存的 masterGain(3、4 聲道)灌進 [buildPianoMaster → loudnessComp → makeup],存 2 聲道 wav(不含限幅器;與整首渲染 LUFS 差 ≤ 0.03)
// 用法:node piano_master_bench.mjs <tap.wav> <out.wav> [--root 目錄] [--ov JSON(PIANO_MASTER_OVERRIDE)] [--mk JSON(MASTER 覆寫)]
import { chromium } from "playwright";
import http from "node:http"; import fs from "node:fs"; import path from "node:path";
const args = process.argv.slice(2);
const opt = (k, d) => { const i = args.indexOf("--" + k); return i >= 0 ? args[i + 1] : d; };
const [tapPath, outPath] = args;
const ROOT = path.resolve(opt("root", path.join(path.dirname(new URL(import.meta.url).pathname), "../..")));
const server = http.createServer((req, res) => {
  const u = decodeURIComponent(req.url.split("?")[0]);
  const p = u === "/__tap" ? path.resolve(tapPath) : path.join(ROOT, u);
  if (!fs.existsSync(p) || fs.statSync(p).isDirectory()) { res.writeHead(404); return res.end(); }
  res.writeHead(200, { "content-type": u.endsWith(".html") ? "text/html" : "application/octet-stream" }); fs.createReadStream(p).pipe(res);
});
await new Promise(r => server.listen(0, "127.0.0.1", r));
const port = server.address().port;
const browser = await chromium.launch(); const page = await browser.newPage();
page.on("pageerror", e => console.error("[pageerror]", e.message));
await page.route(/cdn\.jsdelivr|raw\.githubusercontent|tonejs|fonts\.g/, r => r.abort());
const ov = JSON.parse(opt("ov", "null")), mk = JSON.parse(opt("mk", "{}"));
await page.addInitScript(([ov]) => { if (ov) window.PIANO_MASTER_OVERRIDE = ov; }, [ov]);
await page.goto(`http://127.0.0.1:${port}/index.html`);
await page.waitForFunction(() => typeof buildPianoMaster === "function");
const info = await page.evaluate(async ([mk]) => {
  const buf = await (await fetch("/__tap")).arrayBuffer();
  const dv = new DataView(buf); const nch = dv.getUint16(22, true), n = (buf.byteLength - 44) / 4 / nch;
  const f = new Float32Array(buf, 44, n * nch);
  const L = new Float32Array(n), R = new Float32Array(n);
  for (let i = 0; i < n; i++) { L[i] = f[i * nch + 2]; R[i] = f[i * nch + 3]; }
  const ctx = new OfflineAudioContext(2, n, 48000);
  const ab = ctx.createBuffer(2, n, 48000); ab.copyToChannel(L, 0); ab.copyToChannel(R, 1);
  const src = ctx.createBufferSource(); src.buffer = ab;
  const M = Object.assign({}, MASTER, mk);
  const comp = ctx.createDynamicsCompressor();
  comp.threshold.value = M.compThreshold; comp.knee.value = M.compKnee; comp.ratio.value = M.compRatio; comp.attack.value = M.compAttack; comp.release.value = M.compRelease;
  const mkg = ctx.createGain(); mkg.gain.value = M.makeup;
  const on = (window.PIANO_MASTER_OVERRIDE || PIANO_MASTER).on !== false;
  if (on) { const pm = buildPianoMaster(ctx); src.connect(pm.input); pm.output.connect(comp); } else src.connect(comp);
  comp.connect(mkg); mkg.connect(ctx.destination);
  src.start(0);
  window.__o = await ctx.startRendering();
  return n;
}, [mk]);
const CH = 1 << 20; const out = [new Float32Array(info), new Float32Array(info)];
for (let c = 0; c < 2; c++) for (let o = 0; o < info; o += CH) {
  const b64 = await page.evaluate(([c, o, n]) => { const d = __o.getChannelData(c).subarray(o, o + n); const u = new Uint8Array(d.buffer, d.byteOffset, d.byteLength); let s = ""; for (let i = 0; i < u.length; i += 0x8000) s += String.fromCharCode.apply(null, u.subarray(i, i + 0x8000)); return btoa(s); }, [c, o, CH]);
  const bytes = Buffer.from(b64, "base64"); out[c].set(new Float32Array(bytes.buffer, bytes.byteOffset, bytes.byteLength / 4), o);
}
const hdr = Buffer.alloc(44), db = info * 8; hdr.write("RIFF", 0); hdr.writeUInt32LE(36 + db, 4); hdr.write("WAVE", 8); hdr.write("fmt ", 12); hdr.writeUInt32LE(16, 16); hdr.writeUInt16LE(3, 20); hdr.writeUInt16LE(2, 22); hdr.writeUInt32LE(48000, 24); hdr.writeUInt32LE(48000 * 8, 28); hdr.writeUInt16LE(8, 32); hdr.writeUInt16LE(32, 34); hdr.write("data", 36); hdr.writeUInt32LE(db, 40);
const body = Buffer.alloc(db); for (let i = 0; i < info; i++) { body.writeFloatLE(out[0][i], i * 8); body.writeFloatLE(out[1][i], i * 8 + 4); }
fs.writeFileSync(outPath, Buffer.concat([hdr, body])); await browser.close(); server.close();
