// Guitar Pro 匯入的介面測試:node gp_ui_test.mjs <多音軌.gp> [--seed N]
// 1) 19 種尺寸打開「選擇音軌」對話框:沒有橫向捲動、對話框在畫面內、按鈕 ≥ 28×28、文字沒被截斷
// 2) 模擬真人操作(隨機種子):選軌、取消(按鈕/Esc)、連點、載入中旋轉螢幕、重新整理、切語言、播放中再匯入…
//    每一步檢查狀態一致、沒有 console 錯誤
import { chromium } from "playwright";
import http from "node:http"; import fs from "node:fs"; import path from "node:path";
import { createRequire } from "node:module";
const require = createRequire(import.meta.url);
const args = process.argv.slice(2);
const opt = (k, d) => { const i = args.indexOf("--" + k); return i >= 0 ? args[i + 1] : d; };
const HERE = path.dirname(new URL(import.meta.url).pathname);
const ROOT = path.resolve(opt("root", path.join(HERE, "../..")));
const AT_JS = path.join(HERE, "node_modules/@coderline/alphatab/dist/alphaTab.min.js");
const gpFile = path.resolve(args[0]);
let seed = +opt("seed", "1");
const rnd = () => { seed = (seed * 1103515245 + 12345) % 2147483648; return seed / 2147483648; };
const server = http.createServer((req, res) => {
  const p = path.join(ROOT, decodeURIComponent(req.url.split("?")[0]));
  if (!p.startsWith(ROOT) || !fs.existsSync(p) || fs.statSync(p).isDirectory()) { res.writeHead(404); return res.end(); }
  res.writeHead(200); fs.createReadStream(p).pipe(res);
});
await new Promise(r => server.listen(0, "127.0.0.1", r));
const url = `http://127.0.0.1:${server.address().port}/index.html`;
const browser = await chromium.launch();
const SIZES = [[280, 653], [320, 568], [360, 640], [375, 667], [390, 844], [393, 873], [412, 915], [430, 932],
  [568, 320], [667, 375], [844, 390], [932, 430], [768, 1024], [820, 1180], [1024, 768], [1180, 820], [1280, 800], [1440, 900], [1920, 1080]];
let fails = 0;
const fail = m => { fails++; console.log("  ✗ " + m); };
async function newPage(w, h, touch){
  const ctx = await browser.newContext({ viewport: { width: w, height: h }, hasTouch: !!touch, isMobile: !!touch });
  const page = await ctx.newPage();
  page.errors = [];
  page.on("pageerror", e => page.errors.push(e.message));
  page.on("console", m => { if (m.type() === "error" && !/Failed to load resource|wakeLock/.test(m.text())) page.errors.push(m.text()); });
  await page.route(/cdn\.jsdelivr\.net\/npm\/opensheetmusicdisplay/, r => r.fulfill({ path: require.resolve("opensheetmusicdisplay/build/opensheetmusicdisplay.min.js"), contentType: "text/javascript" }));
  await page.route(/cdn\.jsdelivr\.net\/npm\/jszip/, r => r.fulfill({ path: require.resolve("jszip/dist/jszip.min.js"), contentType: "text/javascript" }));
  await page.route(/cdn\.jsdelivr\.net\/npm\/@coderline\/alphatab@[\d.]+\/dist\/alphaTab\.min\.js/, r => r.fulfill({ path: AT_JS, contentType: "text/javascript" }));
  await page.route(/raw\.githubusercontent\.com|tonejs\.github\.io|nbrosowsky|fonts\.g/, r => r.abort());
  await page.goto(url);
  await page.waitForFunction(() => typeof loadScoreFile === "function");
  return page;
}
const overlayOpen = page => page.evaluate(() => $("trackOverlay").classList.contains("show"));
async function openPicker(page){
  await page.setInputFiles("#fileInput", gpFile);
  await page.waitForFunction(() => $("trackOverlay").classList.contains("show"), null, { timeout: 30000 });
}

// ── 1) 版面 ──
console.log("版面(19 種尺寸)");
for (const [w, h] of SIZES) {
  for (const lang of ["zh", "en"]) {
    const page = await newPage(w, h, w < 1024);
    if (lang === "en") await page.evaluate(() => { applyLanguage("en"); refreshDynamicI18nText(); });
    await openPicker(page);
    const r = await page.evaluate(() => {
      const box = $("trackOverlay").querySelector(".box").getBoundingClientRect();
      const out = { sw: document.documentElement.scrollWidth, iw: innerWidth, ih: innerHeight, box: [box.left, box.top, box.right, box.bottom], small: [], cut: [] };
      for (const b of $("trackOverlay").querySelectorAll("button")) {
        const rc = b.getBoundingClientRect();
        if (rc.width < 28 || rc.height < 28) out.small.push(b.textContent + " " + rc.width.toFixed(0) + "×" + rc.height.toFixed(0));
        for (const t of [b, ...b.querySelectorAll("b,small")]) if (t.scrollWidth > t.clientWidth + 1) out.cut.push(t.textContent);
      }
      return out;
    });
    const tag = `${w}×${h} ${lang}`;
    if (r.sw > r.iw) fail(`${tag} 橫向捲動 ${r.sw} > ${r.iw}`);
    if (r.box[0] < 0 || r.box[1] < 0 || r.box[2] > r.iw + 0.5 || r.box[3] > r.ih + 0.5) fail(`${tag} 對話框超出畫面 ${r.box.map(Math.round)}`);
    if (r.small.length) fail(`${tag} 按鈕太小 ${r.small}`);
    if (r.cut.length) fail(`${tag} 文字被截斷 ${r.cut}`);
    if (page.errors.length) fail(`${tag} console 錯誤 ${page.errors}`);
    if (w === 280 || w === 1920 || (w === 568 && lang === "zh")) await page.screenshot({ path: path.join(opt("out", "/tmp"), `gp-picker-${w}x${h}-${lang}.png`) });
    await page.context().close();
  }
}

// ── 2) 模擬真人操作 ──
console.log("模擬操作(seed " + seed + ")");
const page = await newPage(390, 844, true);
const nTracks = async () => page.locator("#trackList button").count();
const loaded = () => page.evaluate(() => typeof events !== "undefined" && events.length > 0);
const actions = {
  async pickRandom(){ await openPicker(page); const n = await nTracks(); await page.locator("#trackList button").nth(Math.floor(rnd() * n)).click(); await page.waitForFunction(() => events.length > 0 && !$("trackOverlay").classList.contains("show"), null, { timeout: 60000 }); },
  async cancelBtn(){ await openPicker(page); await page.click("#trackCancel"); if (await overlayOpen(page)) fail("取消後對話框還開著"); },
  async cancelEsc(){ await openPicker(page); await page.keyboard.press("Escape"); if (await overlayOpen(page)) fail("Esc 後對話框還開著"); },
  async doubleClickTrack(){ await openPicker(page); const b = page.locator("#trackList button").first(); const wasPlaying = await page.evaluate(() => playing); await b.dblclick(); await page.waitForTimeout(800); if (await overlayOpen(page)) fail("連點後對話框還開著"); if (!wasPlaying && await page.evaluate(() => playing)) fail("連點音軌的第二下開始播放了"); },
  async rotateWhileOpen(){ await openPicker(page); await page.setViewportSize({ width: 844, height: 390 }); await page.waitForTimeout(200); const sw = await page.evaluate(() => document.documentElement.scrollWidth - innerWidth); if (sw > 0) fail("旋轉後橫向捲動"); await page.setViewportSize({ width: 390, height: 844 }); await page.click("#trackCancel"); },
  async spaceWhileOpen(){ await openPicker(page); const before = await page.evaluate(() => typeof playing !== "undefined" ? playing : null); await page.keyboard.press("Space"); await page.waitForTimeout(100); const after = await page.evaluate(() => typeof playing !== "undefined" ? playing : null); if (before !== after) fail("對話框開著時空白鍵觸發了播放"); if (await overlayOpen(page)) await page.click("#trackCancel"); else await page.waitForFunction(() => events.length > 0, null, { timeout: 60000 }); },
  async toggleLangWhileOpen(){ await openPicker(page); await page.evaluate(() => $("langToggle").click()); const t = await page.textContent("#trackTitle"); if (!t || !t.trim()) fail("切語言後標題空白"); await page.click("#trackCancel"); },
  async playThenImport(){ if (!(await loaded())) return; await page.evaluate(() => $("playBtn").click()); await page.waitForTimeout(300); await openPicker(page); await page.locator("#trackList button").last().click(); await page.waitForFunction(() => events.length > 0 && !$("trackOverlay").classList.contains("show"), null, { timeout: 60000 }); },
  async reload(){ await page.reload(); await page.waitForFunction(() => typeof loadScoreFile === "function"); },
};
const names = Object.keys(actions);
for (let i = 0; i < 14; i++) {
  const a = names[Math.floor(rnd() * names.length)];
  try { await actions[a](); } catch (e) { fail(`${a}: ${e.message.split("\n")[0]}`); }
  if (page.errors.length) { fail(`${a} 後 console 錯誤:${page.errors.join(" / ")}`); page.errors.length = 0; }
  const st = await page.evaluate(() => ({ overlay: $("trackOverlay").classList.contains("show"), status: $("status").textContent }));
  console.log(`  ${i + 1}. ${a} → ${st.overlay ? "對話框開著" : "ok"}|${st.status.slice(0, 40)}`);
  if (st.overlay) { await page.keyboard.press("Escape"); }
}
console.log(fails ? `失敗 ${fails} 項` : "全部通過");
await browser.close(); server.close();
process.exit(fails ? 1 : 0);
