// 直式翻頁影片檢查:實際跑一段直式匯出,記錄每一格畫的是第幾頁、播放軸在哪一行,確認換頁時機,並存下換頁前後的畫面。
// node page_export_check.mjs <樂譜> <輸出目錄> [開始秒=0] [結束秒=20] [piano|drum]
import { chromium } from "playwright";
import http from "node:http"; import fs from "node:fs"; import path from "node:path";
const [score, out, s0 = "0", s1 = "20", inst] = process.argv.slice(2);
const ROOT = path.resolve(path.join(path.dirname(new URL(import.meta.url).pathname), "../.."));
const server = http.createServer((req, res) => { const p = path.join(ROOT, decodeURIComponent(req.url.split("?")[0])); if (!fs.existsSync(p) || fs.statSync(p).isDirectory()) { res.writeHead(404); return res.end(); } res.writeHead(200); fs.createReadStream(p).pipe(res); });
await new Promise(r => server.listen(0, "127.0.0.1", r));
const browser = await chromium.launch({ args: ["--autoplay-policy=no-user-gesture-required"] });
const page = await browser.newPage({ viewport: { width: 1280, height: 800 } });
await page.route(/raw\.githubusercontent\.com|\.flac|fonts\.g/, r => r.abort());
const errs = [];
page.on("pageerror", e => errs.push(e.message));
page.on("console", m => { if (m.type() === "error") errs.push(m.text()); });
await page.goto(`http://127.0.0.1:${server.address().port}/index.html`);
if (inst) await page.selectOption("#instrument", inst).catch(() => {});
await page.setInputFiles("#fileInput", path.resolve(score));
await page.waitForFunction(() => typeof events !== "undefined" && events.length > 0, null, { timeout: 120000 });
await page.waitForTimeout(1000);
const res = await page.evaluate(async ({ a, b }) => {
  const log = [], shots = {};
  const orig = drawExportPageFrame;
  drawExportPageFrame = function(ctx, layout, cfg, pg, songSec, calib){
    orig(ctx, layout, cfg, pg, songSec, calib);
    const pos = pagePosAt(pg, songSec);
    const want = pos ? pos.sys.page : -1;
    const last = log[log.length - 1];
    if (!last || last.shown !== pg.shown || last.want !== want) {
      log.push({ sec: +songSec.toFixed(2), shown: pg.shown, want, sys: pos ? pg.systems.indexOf(pos.sys) : -1, pages: pg.pages.length });
      if (Object.keys(shots).length < 6) shots[songSec.toFixed(2)] = ctx.canvas.toDataURL("image/jpeg", 0.6);
    }
  };
  let delivered = null;
  deliverExportedVideo = (blob, name) => { delivered = { size: blob.size, name }; };
  exportPrefs.format = "portrait"; exportPrefs.panel = true;
  const cfg = buildExportCfg();
  cfg.startSec = a; cfg.endSec = b;
  await exportVideo(cfg);
  return { log, shots, delivered, pages: pageScoreCache && pageScoreCache.pages.map(p => [p.first, p.last]) };
}, { a: +s0, b: +s1 });
for (const [k, v] of Object.entries(res.shots)) fs.writeFileSync(`${out}/frame_${k}.jpg`, Buffer.from(v.split(",")[1], "base64"));
console.log("pages", JSON.stringify(res.pages));
for (const l of res.log) console.log(JSON.stringify(l));
console.log("delivered", JSON.stringify(res.delivered));
console.log(errs.length ? "errors:\n" + errs.join("\n") : "no errors");
await browser.close(); server.close();
