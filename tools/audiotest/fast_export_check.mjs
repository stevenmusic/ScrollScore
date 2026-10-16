// 快速匯出檢查:實際跑一次匯出(跟按「開始匯出」同一段程式),存下影片檔,印出花的時間與影片資訊。
// node fast_export_check.mjs <樂譜> <輸出目錄> [landscape|portrait|square] [開始秒] [結束秒] [--realtime] [--mp4test] [--inst drum]
//   --realtime:強制走舊的即時錄影(比較用);--mp4test:用 MP4 容器 + VP9/Opus 測 mp4-muxer(雲端 Chromium 沒有 H.264/AAC 編碼器);
//   --webmtest:強制快速匯出走 WebM(跳過「試編速度不夠就改即時錄影」的判斷;雲端沒有硬體編碼器,軟體編碼比即時慢)
import { chromium } from "playwright";
import http from "node:http"; import fs from "node:fs"; import path from "node:path";
const args = process.argv.slice(2);
const flags = new Set(args.filter(a => a.startsWith("--")));
const opt = k => { const i = args.indexOf("--" + k); return i >= 0 ? args[i + 1] : null; };
const pos = args.filter((a, i) => !a.startsWith("--") && !(i > 0 && args[i - 1] === "--inst"));
const [score, out, format = "landscape", s0, s1] = pos;
const ROOT = path.resolve(path.join(path.dirname(new URL(import.meta.url).pathname), "../.."));
const server = http.createServer((req, res) => { const p = path.join(ROOT, decodeURIComponent(req.url.split("?")[0])); if (!fs.existsSync(p) || fs.statSync(p).isDirectory()) { res.writeHead(404); return res.end(); } res.writeHead(200); fs.createReadStream(p).pipe(res); });
await new Promise(r => server.listen(0, "127.0.0.1", r));
const browser = await chromium.launch({ args: ["--autoplay-policy=no-user-gesture-required"] });
const page = await browser.newPage({ viewport: { width: 1280, height: 800 } });
await page.route(/raw\.githubusercontent\.com|fonts\.g/, r => r.abort());
const errs = [];
page.on("pageerror", e => errs.push(e.message));
page.on("console", m => { if (m.type() === "error" || m.type() === "warning" || m.type() === "info") errs.push(m.type() + ": " + m.text()); });
await page.goto(`http://127.0.0.1:${server.address().port}/index.html`);
if (opt("inst")) await page.selectOption("#instrument", opt("inst"));
await page.setInputFiles("#fileInput", path.resolve(score));
await page.waitForFunction(() => typeof events !== "undefined" && events.length > 0, null, { timeout: 120000 });
await page.evaluate(async () => { const inst = currentInstrument(); if (inst === "drum") await loadDrumKit(); else await loadInstrumentSamples(inst); });
await page.waitForTimeout(500);
const res = await page.evaluate(async ({ format, s0, s1, realtime, mp4test, webmtest }) => {
  if (realtime) window.FAST_EXPORT_DISABLE = true;
  if (mp4test) window.FAST_EXPORT_FORCE = { container: "mp4", vCodec: "vp09.00.40.08", aCodec: "opus", muxV: "vp9", muxA: "opus", mime: "video/mp4;codecs=vp9,opus", ext: "mp4" };
  if (webmtest) window.FAST_EXPORT_FORCE = { container: "webm", vCodec: "vp09.00.40.08", aCodec: "opus", muxV: "V_VP9", muxA: "A_OPUS", mime: "video/webm;codecs=vp9,opus", ext: "webm" };
  let delivered = null, done;
  const got = new Promise(r => done = r);
  deliverExportedVideo = async (blob, name, mime) => { delivered = { name, mime, size: blob.size, b64: await new Promise(r => { const fr = new FileReader(); fr.onload = () => r(String(fr.result).split("base64,")[1]); fr.readAsDataURL(blob); }) }; done(); };
  exportPrefs.format = format; exportPrefs.panel = true;
  const cfg = buildExportCfg();
  if (s0 != null) { cfg.startSec = +s0; cfg.endSec = +s1; }
  const t0 = performance.now();
  await exportVideo(cfg);
  const ms = performance.now() - t0;
  await Promise.race([got, new Promise(r => setTimeout(r, 20000))]);
  return { ms: Math.round(ms), delivered, status: $("status") ? $("status").textContent : "", len: (cfg.endSec != null ? cfg.endSec - cfg.startSec : totalSec()) };
}, { format, s0, s1, realtime: flags.has("--realtime"), mp4test: flags.has("--mp4test"), webmtest: flags.has("--webmtest") });
if (res.delivered) {
  const tag = flags.has("--realtime") ? "rt-" : flags.has("--mp4test") ? "mp4test-" : flags.has("--webmtest") ? "webmtest-" : "";
  const f = path.join(out, tag + res.delivered.name);
  fs.writeFileSync(f, Buffer.from(res.delivered.b64, "base64"));
  console.log("file", f, res.delivered.mime, (res.delivered.size / 1048576).toFixed(2) + "MB");
}
console.log("music", res.len.toFixed(1) + "s", "export took", (res.ms / 1000).toFixed(1) + "s", "status:", res.status);
console.log(errs.filter(e => !/ERR_FAILED|wakeLock|Wake Lock/.test(e)).slice(0, 10).join("\n") || "no errors");
await browser.close(); server.close();
