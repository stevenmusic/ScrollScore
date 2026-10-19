// 封面樣式選擇框(#coverOverlay)版面檢查:各尺寸 × 橫/直/方,量對話框與兩張縮圖的大小、佔畫面比例,
// 檢查縮圖沒超出畫面、不用捲動就看得到兩張與取消鈕。node cover_sheet_check.mjs <樂譜> [截圖目錄]
import { chromium } from "playwright";
import http from "node:http"; import fs from "node:fs"; import path from "node:path";
import { createRequire } from "node:module";
const require = createRequire(import.meta.url);
const [score, shotDir] = process.argv.slice(2);
const ROOT = path.resolve(path.join(path.dirname(new URL(import.meta.url).pathname), "../.."));
const server = http.createServer((req, res) => { const p = path.join(ROOT, decodeURIComponent(req.url.split("?")[0])); if (!fs.existsSync(p) || fs.statSync(p).isDirectory()) { res.writeHead(404); return res.end(); } res.writeHead(200); fs.createReadStream(p).pipe(res); });
await new Promise(r => server.listen(0, "127.0.0.1", r));
const browser = await chromium.launch();
const SIZES = (process.env.SIZES ? JSON.parse(process.env.SIZES) : [[280,653],[320,568],[390,844],[393,660],[430,932],[844,390],[932,430],[600,960],[768,1024],[1024,768],[820,1180],[1180,820],[1024,1366],[1366,1024],[1280,800],[1440,900],[1920,1080]]);
let bad = 0;
for (const [w, h] of SIZES) {
  const touch = Math.min(w, h) < 1100;
  const page = await browser.newPage({ viewport: { width: w, height: h }, hasTouch: touch, isMobile: touch && Math.min(w, h) < 500 });
  await page.route(/cdn\.jsdelivr\.net\/npm\/opensheetmusicdisplay/, r => r.fulfill({ path: require.resolve("opensheetmusicdisplay/build/opensheetmusicdisplay.min.js"), contentType: "text/javascript" }));
  await page.route(/cdn\.jsdelivr\.net\/npm\/jszip/, r => r.fulfill({ path: require.resolve("jszip/dist/jszip.min.js"), contentType: "text/javascript" }));
  await page.route(/raw\.githubusercontent\.com|\.flac|fonts\.g/, r => r.abort());
  const errs = []; page.on("pageerror", e => errs.push(e.message));
  await page.goto(`http://127.0.0.1:${server.address().port}/index.html`);
  await page.waitForTimeout(300);
  await page.setInputFiles("#fileInput", path.resolve(score));
  await page.waitForFunction(() => typeof events !== "undefined" && events.length > 0, null, { timeout: 120000 });
  await page.waitForTimeout(600);
  for (const fmt of ["landscape", "portrait", "square"]) {
    await page.evaluate(fmt => { exportPrefs.format = fmt; openExportSheet(); }, fmt);
    await page.waitForTimeout(300);
    await page.evaluate(fmt => { const b = document.querySelector(`#expFormatSeg [data-v="${fmt}"]`); if (b && b.getAttribute("aria-checked") !== "true") b.click(); $("coverBtn").click(); }, fmt);
    await page.waitForFunction(() => Array.from(document.querySelectorAll("#coverOverlay .cover-thumb img")).every(i => i.complete && i.naturalWidth > 0), null, { timeout: 30000 }).catch(() => {});
    await page.waitForTimeout(200);
    const r = await page.evaluate(() => {
      const R = el => el.getBoundingClientRect(), W = innerWidth, H = innerHeight;
      const box = R(document.querySelector("#coverOverlay .box"));
      const imgs = Array.from(document.querySelectorAll("#coverOverlay .cover-thumb img")).map(R);
      const cancel = R($("coverCancel"));
      const issues = [];
      for (const i of imgs) if (i.left < -1 || i.right > W + 1 || i.top < -1 || i.bottom > H + 1) issues.push("img-offscreen");
      for (const i of imgs) if (i.left < box.left - 1 || i.right > box.right + 1 || i.top < box.top - 1 || i.bottom > box.bottom + 1) issues.push("img-outside-box");
      for (const t of document.querySelectorAll("#coverOverlay .cover-thumb")) { const r = R(t); if (r.right > box.right + 1 || r.left < box.left - 1) issues.push("thumb-outside-box"); }
      if (box.left < -1 || box.right > W + 1 || box.top < -1 || box.bottom > H + 1) issues.push("box-offscreen");
      if (cancel.bottom > H + 1) issues.push("cancel-below");
      const sc = document.querySelector("#coverOverlay .box"); if (sc.scrollHeight > sc.clientHeight + 1) issues.push("box-scrolls");
      const area = imgs.reduce((a, i) => a + i.width * i.height, 0) / (W * H);
      return { box: `${Math.round(box.width)}x${Math.round(box.height)}`, imgs: imgs.map(i => `${Math.round(i.width)}x${Math.round(i.height)}`).join(" "), area: +(area * 100).toFixed(0), issues };
    });
    if (r.issues.length) bad++;
    console.log(`${w}x${h} ${fmt.padEnd(9)} box ${r.box.padEnd(9)} imgs ${r.imgs.padEnd(17)} 佔畫面 ${r.area}% ${r.issues.join(",")}`);
    if (shotDir) await page.screenshot({ path: path.join(shotDir, `cover-${w}x${h}-${fmt}.png`) });
    await page.evaluate(() => { $("coverCancel").click(); $("formatOverlay").classList.remove("show"); });
  }
  if (errs.length) { bad++; console.log("  錯誤:", errs.join(" | ")); }
  await page.close();
}
console.log(bad ? `有問題 ${bad}` : "全部通過");
await browser.close(); server.close();
