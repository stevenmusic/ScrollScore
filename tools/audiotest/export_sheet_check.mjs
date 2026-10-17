// 匯出頁版面檢查(2026-10,使用者 iPhone 截圖:預覽圖上面被切掉、下面蓋住「格式」):19 種尺寸 × 橫/直/方 × 中英文,
// 打開匯出頁等預覽畫好,檢查:預覽圖沒有超出它的區塊(上下被切/蓋到下面)、沒變形、不跟選項重疊、
// 選項/按鈕沒有超出畫面或被截斷、沒有橫向捲動。node export_sheet_check.mjs <樂譜> [截圖目錄]
import { chromium } from "playwright";
import http from "node:http"; import fs from "node:fs"; import path from "node:path";
import { createRequire } from "node:module";
const require = createRequire(import.meta.url);
const [score, shotDir] = process.argv.slice(2);
const ROOT = path.resolve(path.join(path.dirname(new URL(import.meta.url).pathname), "../.."));
const server = http.createServer((req, res) => { const p = path.join(ROOT, decodeURIComponent(req.url.split("?")[0])); if (!fs.existsSync(p) || fs.statSync(p).isDirectory()) { res.writeHead(404); return res.end(); } res.writeHead(200); fs.createReadStream(p).pipe(res); });
await new Promise(r => server.listen(0, "127.0.0.1", r));
const browser = await chromium.launch();
const SIZES = [[280,653],[320,568],[360,740],[375,667],[390,844],[393,660],[414,896],[430,932],[568,320],[667,375],[844,390],[932,430],[600,960],[768,1024],[1024,768],[820,1180],[1180,820],[1280,800],[1440,900],[1920,1080]];
let bad = 0;
for (const [w, h] of SIZES) for (const lang of ["zh", "en"]) {
  const touch = Math.min(w, h) < 900;
  const page = await browser.newPage({ viewport: { width: w, height: h }, hasTouch: touch, isMobile: touch && Math.min(w, h) < 500 });
  await page.route(/cdn\.jsdelivr\.net\/npm\/opensheetmusicdisplay/, r => r.fulfill({ path: require.resolve("opensheetmusicdisplay/build/opensheetmusicdisplay.min.js"), contentType: "text/javascript" }));
  await page.route(/cdn\.jsdelivr\.net\/npm\/jszip/, r => r.fulfill({ path: require.resolve("jszip/dist/jszip.min.js"), contentType: "text/javascript" }));
  await page.route(/raw\.githubusercontent\.com|\.flac|fonts\.g/, r => r.abort());
  const errs = []; page.on("pageerror", e => errs.push(e.message));
  await page.goto(`http://127.0.0.1:${server.address().port}/index.html`);
  await page.waitForTimeout(300);
  if (lang === "en") await page.evaluate(() => { if (currentLang !== "en") document.getElementById("langToggle").click(); });
  await page.setInputFiles("#fileInput", path.resolve(score));
  await page.waitForFunction(() => typeof events !== "undefined" && events.length > 0, null, { timeout: 120000 });
  await page.waitForTimeout(800);
  const issues = [];
  for (const fmt of ["landscape", "portrait", "square"]) {
    await page.evaluate(fmt => { exportPrefs.format = fmt; openExportSheet(); }, fmt);
    await page.waitForFunction(() => $("formatOverlay").classList.contains("show"), null, { timeout: 5000 }).catch(() => {});
    await page.evaluate(fmt => { const b = document.querySelector(`#expFormatSeg [data-v="${fmt}"]`); if (b && b.getAttribute("aria-checked") !== "true") b.click(); }, fmt);
    await page.waitForFunction(() => { const i = $("previewImg"); return i.complete && i.naturalWidth > 0 && !i.parentElement.classList.contains("busy"); }, null, { timeout: 30000 }).catch(() => issues.push(fmt + ":preview-timeout"));
    await page.waitForTimeout(250);
    const r = await page.evaluate(fmt => {
      const out = [], R = el => el.getBoundingClientRect();
      const img = $("previewImg"), box = img.parentElement, body = document.querySelector(".exp-body"), opts = document.querySelector(".exp-opts");
      body.scrollTop = 0;
      const ri = R(img), rb = R(box), rbody = R(body), ro = R(opts);
      if (ri.top < rb.top - 1 || ri.bottom > rb.bottom + 1) out.push(`${fmt}:img-overflows-box(${Math.round(ri.top - rb.top)},${Math.round(ri.bottom - rb.bottom)})`);
      if (ri.top < rbody.top - 1) out.push(`${fmt}:img-clipped-top(${Math.round(rbody.top - ri.top)})`);
      if (ri.left < rbody.left - 1 || ri.right > rbody.right + 1) out.push(`${fmt}:img-out-x`);
      const ar = img.naturalWidth / img.naturalHeight, shown = ri.width / ri.height;
      if (Math.abs(shown / ar - 1) > 0.02) out.push(`${fmt}:img-distorted`);
      if (ri.height < 60) out.push(`${fmt}:img-tiny(${Math.round(ri.height)})`);
      // 預覽圖跟選項(同一欄時)不能重疊
      if (ri.left < ro.right - 1 && ro.left < ri.right - 1 && ri.top < ro.bottom - 1 && ro.top < ri.bottom - 1) out.push(`${fmt}:img-overlaps-opts(${Math.round(ri.bottom - ro.top)})`);
      if (document.documentElement.scrollWidth > innerWidth + 1) out.push(fmt + ":hscroll");
      for (const el of document.querySelectorAll("#formatOverlay button, #formatOverlay input, #formatOverlay .exp-label, #formatOverlay summary, #formatOverlay .switch-row")) {
        const e = R(el); if (!e.width) continue;
        if (e.left < -1 || e.right > innerWidth + 1) out.push(fmt + ":out:" + (el.id || el.className || el.tagName));
        if (el.tagName === "BUTTON" && el.scrollWidth > el.clientWidth + 2) out.push(fmt + ":clipped:" + (el.id || el.textContent.trim().slice(0, 8)));
      }
      const acts = R(document.querySelector(".exp-actions"));
      if (acts.bottom > innerHeight + 1) out.push(fmt + ":actions-offscreen");
      return out;
    }, fmt);
    issues.push(...r);
    if (shotDir && [393, 320, 844, 1440].includes(w) && lang === "zh") await page.screenshot({ path: `${shotDir}/es_${w}x${h}_${fmt}.png` });
    await page.evaluate(() => $("formatOverlay").classList.remove("show"));
  }
  issues.push(...errs.map(e => "error:" + e));
  if (issues.length) bad++;
  console.log(issues.length ? "✗" : "✓", `${w}x${h}`, lang, issues.join(" ") || "");
  await page.close();
}
await browser.close(); server.close();
console.log(bad ? `${bad} 種有問題` : "全部通過");
process.exit(bad ? 1 : 0);
