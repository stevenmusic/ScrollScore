// 匯出影片版面預覽:用跟實際匯出同一套 computeExportLayout/drawExportFrame 畫出橫式/直式/方形 × 有無樂器面板的畫面。
// node export_preview.mjs <樂譜> <輸出目錄> [秒數=8] [piano|drum]
import { chromium } from "playwright";
import http from "node:http"; import fs from "node:fs"; import path from "node:path";
import { createRequire } from "node:module";
const require = createRequire(import.meta.url);
const [score, out, secArg, inst] = process.argv.slice(2);
const ROOT = path.resolve(path.join(path.dirname(new URL(import.meta.url).pathname), "../.."));
const server = http.createServer((req, res) => { const p = path.join(ROOT, decodeURIComponent(req.url.split("?")[0])); if (!fs.existsSync(p) || fs.statSync(p).isDirectory()) { res.writeHead(404); return res.end(); } res.writeHead(200); fs.createReadStream(p).pipe(res); });
await new Promise(r => server.listen(0, "127.0.0.1", r));
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1400, height: 900 } });
await page.route(/cdn\.jsdelivr\.net\/npm\/opensheetmusicdisplay/, r => r.fulfill({ path: require.resolve("opensheetmusicdisplay/build/opensheetmusicdisplay.min.js"), contentType: "text/javascript" }));
await page.route(/cdn\.jsdelivr\.net\/npm\/jszip/, r => r.fulfill({ path: require.resolve("jszip/dist/jszip.min.js"), contentType: "text/javascript" }));
await page.route(/raw\.githubusercontent\.com|\.flac|fonts\.g/, r => r.abort());
page.on("pageerror", e => console.error("[pageerror]", e.message));
await page.goto(`http://127.0.0.1:${server.address().port}/index.html`);
if (inst) await page.selectOption("#instrument", inst).catch(() => {});
await page.setInputFiles("#fileInput", path.resolve(score));
await page.waitForFunction(() => typeof events !== "undefined" && events.length > 0, null, { timeout: 120000 });
await page.waitForTimeout(1500);
for (const [name, W, H, sh] of [["landscape", 1920, 1080, 440], ["portrait", 1080, 1920, await page.evaluate(() => isDrumScore ? 380 : EXPORT_PORTRAIT_SCORE_H)], ["square", 1080, 1080, await page.evaluate(() => isDrumScore ? 400 : EXPORT_SQUARE_SCORE_H)]]) for (const kb of [true, false]) {
  const data = await page.evaluate(async ({ W, H, sh, kb, sec }) => {
    const cfg = Object.assign({ W, H, scoreH: sh, autoKind: W === H ? "square" : H > W ? "portrait" : "landscape", align: typeof chosenAlign !== "undefined" ? chosenAlign : "center", bitrate: 5e6, fps: 30, includeKeyboard: kb, startSec: sec, endSec: null }, watermarkCfg());
    await showExportPreview(cfg);
    $("previewOverlay").classList.remove("show");
    const L = computeExportLayout(pendingExportCfg);
    return { src: $("previewImg").src, L };
  }, { W, H, sh, kb, sec: +(secArg || 8) });
  fs.writeFileSync(`${out}/exp_${name}_${kb ? "kb" : "score"}.png`, Buffer.from(data.src.split(",")[1], "base64"));
  console.log(name, kb ? "kb" : "score", JSON.stringify(Object.fromEntries(Object.entries(data.L).map(([k, v]) => [k, Math.round(v)]))));
}
await browser.close(); server.close();
