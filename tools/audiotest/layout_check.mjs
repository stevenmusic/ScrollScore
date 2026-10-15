// 版面檢查(19 種尺寸 × 中英文):載入樂譜後頂欄是否單排、有沒有橫向捲動、按鈕是否超出畫面/重疊/小於 28px、
// 設定面板打開後內容是否超出。node layout_check.mjs <樂譜> [截圖目錄]
import { chromium } from "playwright";
import http from "node:http"; import fs from "node:fs"; import path from "node:path";
import { createRequire } from "node:module";
const require = createRequire(import.meta.url);
const [score, shotDir] = process.argv.slice(2);
const ROOT = path.resolve(path.join(path.dirname(new URL(import.meta.url).pathname), "../.."));
const server = http.createServer((req, res) => { const p = path.join(ROOT, decodeURIComponent(req.url.split("?")[0])); if (!fs.existsSync(p) || fs.statSync(p).isDirectory()) { res.writeHead(404); return res.end(); } res.writeHead(200); fs.createReadStream(p).pipe(res); });
await new Promise(r => server.listen(0, "127.0.0.1", r));
const browser = await chromium.launch();
const SIZES = [[280,653],[320,568],[360,740],[375,667],[390,844],[414,896],[430,932],[568,320],[667,375],[844,390],[932,430],[600,960],[768,1024],[1024,768],[820,1180],[1180,820],[1280,800],[1440,900],[1920,1080]];
let bad = 0;
for (const [w, h] of SIZES) for (const lang of ["zh", "en"]) {
  const touch = Math.min(w, h) < 900;
  const page = await browser.newPage({ viewport: { width: w, height: h }, hasTouch: touch, isMobile: touch && Math.min(w, h) < 500 });
  await page.route(/cdn\.jsdelivr\.net\/npm\/opensheetmusicdisplay/, r => r.fulfill({ path: require.resolve("opensheetmusicdisplay/build/opensheetmusicdisplay.min.js"), contentType: "text/javascript" }));
  await page.route(/cdn\.jsdelivr\.net\/npm\/jszip/, r => r.fulfill({ path: require.resolve("jszip/dist/jszip.min.js"), contentType: "text/javascript" }));
  await page.route(/raw\.githubusercontent\.com|\.flac/, r => r.abort());
  const errs = []; page.on("pageerror", e => errs.push(e.message));
  await page.goto(`http://127.0.0.1:${server.address().port}/index.html`);
  await page.waitForTimeout(400);
  if (lang === "en") await page.evaluate(() => { if (currentLang !== "en") document.getElementById("langToggle").click(); });
  await page.setInputFiles("#fileInput", path.resolve(score));
  await page.waitForFunction(() => typeof events !== "undefined" && events.length > 0, null, { timeout: 120000 });
  await page.waitForTimeout(1600);
  const check = () => page.evaluate(() => {
    const vis = el => { const r = el.getBoundingClientRect(); const cs = getComputedStyle(el); return r.width > 0 && r.height > 0 && cs.display !== "none" && cs.visibility !== "hidden"; };
    const header = document.querySelector("header"), tb = document.getElementById("transportBar");
    const btns = [...document.querySelectorAll("header .btn, #transportBar .btn, header h1")].filter(vis);
    const rects = btns.map(b => ({ id: b.id || b.tagName, r: b.getBoundingClientRect() }));
    const issues = [];
    if (document.documentElement.scrollWidth > innerWidth + 1) issues.push("hscroll");
    for (const { id, r } of rects) {
      if (r.left < -1 || r.right > innerWidth + 1) issues.push("out:" + id);
      if (id !== "H1" && (r.width < 28 || r.height < 28)) issues.push("small:" + id + Math.round(r.width) + "x" + Math.round(r.height));
    }
    for (let i = 0; i < rects.length; i++) for (let j = i + 1; j < rects.length; j++) {
      const a = rects[i].r, b = rects[j].r;
      if (a.left < b.right - 1 && b.left < a.right - 1 && a.top < b.bottom - 1 && b.top < a.bottom - 1) issues.push("overlap:" + rects[i].id + "/" + rects[j].id);
    }
    for (const b of btns) { const l = b.querySelector(".btn-label"); if (l && vis(l) && l.scrollWidth > l.clientWidth + 1) issues.push("clipped:" + b.id); }
    const twoRows = vis(tb);
    return { issues, twoRows, headerH: Math.round(header.getBoundingClientRect().height), prefsMoved: document.body.classList.contains("header-prefs-moved") };
  });
  const a = await check();
  await page.click("#settingsToggle"); await page.waitForTimeout(500);
  const b = await page.evaluate(() => {
    const p = document.getElementById("settingsPanel"), issues = [];
    if (document.documentElement.scrollWidth > innerWidth + 1) issues.push("hscroll");
    for (const el of p.querySelectorAll("button, select, input, .switch-row, summary")) {
      const r = el.getBoundingClientRect(); if (!r.width) continue;
      if (r.left < -1 || r.right > innerWidth + 1) issues.push("panel-out:" + (el.id || el.className));
    }
    for (const el of p.querySelectorAll("[data-i18n]")) { if (el.offsetParent && getComputedStyle(el).visibility !== "hidden" && el.scrollWidth > el.clientWidth + 2 && getComputedStyle(el).overflow === "hidden") issues.push("panel-clip:" + el.dataset.i18n); }
    return issues;
  });
  if (shotDir && ((w === 320 && h === 568) || (w === 390) || (w === 844) || (w === 1440))) { await page.screenshot({ path: `${shotDir}/lc_${w}x${h}_${lang}_panel.png` }); await page.keyboard.press("Escape"); await page.click("#settingsToggle").catch(() => {}); await page.waitForTimeout(400); await page.screenshot({ path: `${shotDir}/lc_${w}x${h}_${lang}.png` }); }
  const issues = [...a.issues, ...b, ...errs.map(e => "error:" + e)];
  if (a.twoRows) issues.push("header-two-rows");
  if (issues.length) { bad++; console.log("BAD", `${w}x${h}`, lang, a.headerH + "px", issues.join(" ")); }
  else console.log("ok ", `${w}x${h}`, lang, "header " + a.headerH + "px", a.prefsMoved ? "(主題/語言在設定裡)" : "");
  await page.close();
}
console.log(`檢查 ${SIZES.length * 2} 種,問題 ${bad} 種`);
await browser.close(); server.close();
