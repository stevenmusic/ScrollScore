// 模擬真人操作:隨機點按頂欄/設定/開關、連點、切語言主題、旋轉螢幕、播放中操作;每步檢查狀態一致與 console 錯誤。
// node human_check.mjs <樂譜> [種子...]
import { chromium } from "playwright";
import http from "node:http"; import fs from "node:fs"; import path from "node:path";
import { createRequire } from "node:module";
const require = createRequire(import.meta.url);
const [score, ...seeds] = process.argv.slice(2);
const ROOT = path.resolve(path.join(path.dirname(new URL(import.meta.url).pathname), "../.."));
const server = http.createServer((req, res) => { const p = path.join(ROOT, decodeURIComponent(req.url.split("?")[0])); if (!fs.existsSync(p) || fs.statSync(p).isDirectory()) { res.writeHead(404); return res.end(); } res.writeHead(200); fs.createReadStream(p).pipe(res); });
await new Promise(r => server.listen(0, "127.0.0.1", r));
const browser = await chromium.launch({ args: ["--autoplay-policy=no-user-gesture-required"] });
let fails = 0;
for (const seed of (seeds.length ? seeds : ["1", "2", "3"]).map(Number)) {
  let x = seed * 9301 + 49297; const rnd = () => (x = (x * 9301 + 49297) % 233280) / 233280;
  const page = await browser.newPage({ viewport: { width: 390, height: 844 }, hasTouch: true, isMobile: true });
  await page.route(/cdn\.jsdelivr\.net\/npm\/opensheetmusicdisplay/, r => r.fulfill({ path: require.resolve("opensheetmusicdisplay/build/opensheetmusicdisplay.min.js"), contentType: "text/javascript" }));
  await page.route(/cdn\.jsdelivr\.net\/npm\/jszip/, r => r.fulfill({ path: require.resolve("jszip/dist/jszip.min.js"), contentType: "text/javascript" }));
  await page.route(/raw\.githubusercontent\.com/, r => r.abort());
  const errs = []; page.on("pageerror", e => errs.push(e.message)); page.on("console", m => { if (m.type() === "error" && !/wakeLock|Wake Lock|attribute d/.test(m.text())) errs.push(m.text()); });
  await page.goto(`http://127.0.0.1:${server.address().port}/index.html`);
  await page.setInputFiles("#fileInput", path.resolve(score));
  await page.waitForFunction(() => typeof events !== "undefined" && events.length > 0, null, { timeout: 120000 });
  await page.waitForTimeout(1500);
  const sizes = [[390, 844], [844, 390], [320, 568], [768, 1024], [1280, 800]];
  const actions = [
    async () => page.click("#playBtn").catch(() => {}),
    async () => page.click("#stopBtn").catch(() => {}),
    async () => page.click("#settingsToggle").catch(() => {}),
    async () => page.click("#themeToggle", { timeout: 800 }).catch(() => {}),
    async () => page.click("#langToggle", { timeout: 800 }).catch(() => {}),
    async () => { const v = 40 + Math.floor(rnd() * 200); await page.evaluate(v => { const t = $("tempo"); t.value = v; t.dispatchEvent(new Event("input")); }, v).catch(() => {}); },   // 速度在設定面板裡(2026-10 起頂欄沒有速度按鈕)
    async () => page.keyboard.press("Escape"),
    async () => page.keyboard.press("Space"),
    async () => { const s = sizes[Math.floor(rnd() * sizes.length)]; await page.setViewportSize({ width: s[0], height: s[1] }); },
    async () => { for (let k = 0; k < 4; k++) await page.click("#playBtn").catch(() => {}); },
    async () => page.click(".switch-row >> nth=" + Math.floor(rnd() * 4), { timeout: 800 }).catch(() => {}),
    async () => page.mouse.click(Math.floor(rnd() * 300) + 20, Math.floor(rnd() * 500) + 80),
  ];
  for (let step = 0; step < 60; step++) {
    await actions[Math.floor(rnd() * actions.length)]();
    await page.waitForTimeout(120 + rnd() * 250);
    const st = await page.evaluate(() => ({
      theme: document.querySelectorAll("#themeToggle").length, lang: document.querySelectorAll("#langToggle").length,
      prefsInHeader: !!document.querySelector("header #themeToggle"), moved: document.body.classList.contains("header-prefs-moved"),
      hscroll: document.documentElement.scrollWidth > innerWidth + 1,
      twoRows: getComputedStyle(document.getElementById("transportBar")).display !== "none" && document.body.classList.contains("score-loaded")
    }));
    const bad = st.theme !== 1 || st.lang !== 1 || st.prefsInHeader === st.moved || st.hscroll;
    if (bad) { fails++; console.log("seed", seed, "step", step, "BAD", JSON.stringify(st)); break; }
  }
  if (errs.length) { fails++; console.log("seed", seed, "errors:", errs.slice(0, 5).join(" | ")); }
  else console.log("seed", seed, "ok");
  await page.close();
}
console.log(fails ? `失敗 ${fails}` : "全部通過");
await browser.close(); server.close();
