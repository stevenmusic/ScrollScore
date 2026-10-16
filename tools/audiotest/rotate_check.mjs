// 旋轉螢幕檢查(2026-10,使用者反映:設定頁直式 → 橫式 → 直式,字變大):
// 手機尺寸 × 各種狀態(載入前/後、設定面板開著或轉完才開、匯出畫面、連轉好幾次、轉的時候切語言/主題),
// 轉完回到原本尺寸後,每個看得到的元素字級與大小要跟「直接用這個尺寸打開」一樣。
// node rotate_check.mjs <樂譜> [--nofix](--nofix 拿掉 text-size-adjust,確認這個檢查抓得到問題)
import { chromium } from "playwright";
import http from "node:http"; import fs from "node:fs"; import path from "node:path";
const args = process.argv.slice(2), score = args.find(a => !a.startsWith("--")), nofix = args.includes("--nofix");
const ROOT = path.resolve(path.join(path.dirname(new URL(import.meta.url).pathname), "../.."));
const server = http.createServer((req, res) => {
  const p = path.join(ROOT, decodeURIComponent(req.url.split("?")[0]));
  if (!fs.existsSync(p) || fs.statSync(p).isDirectory()) { res.writeHead(404); return res.end(); }
  if (nofix && p.endsWith("index.html")) { res.writeHead(200, { "content-type": "text/html" }); return res.end(fs.readFileSync(p, "utf8").replace("html{-webkit-text-size-adjust:100%;text-size-adjust:100%}", "")); }
  res.writeHead(200); fs.createReadStream(p).pipe(res);
});
await new Promise(r => server.listen(0, "127.0.0.1", r));
const URL0 = `http://127.0.0.1:${server.address().port}/index.html`;
const browser = await chromium.launch({ args: ["--autoplay-policy=no-user-gesture-required"] });
const PHONES = [[390, 844], [375, 667], [430, 932], [320, 568], [360, 780], [768, 1024]];
// 狀態:載入前/後 × 要看的畫面
const VIEWS = {
  settings: async p => { await p.click("#settingsToggle"); await p.waitForTimeout(400); },
  main: async p => {},
  exportDlg: async p => { await p.evaluate(() => { const b = $("exportHdrBtn"); if (b && b.offsetParent) b.click(); else { $("settingsToggle").click(); } }); await p.waitForTimeout(800); },
};
// 匯出畫面的預覽是延遲重畫的,等它畫完(不是 busy)再量
const settle = p => p.waitForFunction(() => { const o = document.getElementById("formatOverlay"); const pv = document.querySelector(".exp-preview"); return !o || getComputedStyle(o).display === "none" || !pv || !pv.classList.contains("busy"); }, null, { timeout: 20000 }).catch(() => {}).then(() => p.waitForTimeout(300));
const snap = async p => { await settle(p); return snapNow(p); };
const snapNow = p => p.evaluate(() => {
  const out = {};
  const els = [...document.querySelectorAll("header *, #settingsPanel *, #formatOverlay *, #startScreen *, body > *")];
  els.forEach((el, i) => {
    if (!el.offsetParent && getComputedStyle(el).position !== "fixed") return;
    const r = el.getBoundingClientRect(); if (r.width === 0 && r.height === 0) return;
    const key = (el.id ? "#" + el.id : el.tagName.toLowerCase() + "." + [...el.classList].join(".")) + "@" + i;
    const cs = getComputedStyle(el);
    out[key] = { fs: parseFloat(cs.fontSize), w: Math.round(r.width), h: Math.round(r.height), txt: (el.childNodes.length === 1 && el.firstChild.nodeType === 3) ? el.textContent.trim().slice(0, 12) : "" };
  });
  return out;
});
const fresh = async (w, h, loaded, view) => {
  const p = await browser.newPage({ viewport: { width: w, height: h }, hasTouch: true, isMobile: true, deviceScaleFactor: 3 });
  await p.route(/raw\.githubusercontent\.com|fonts\.g/, r => r.abort());
  p.errs = []; p.on("pageerror", e => p.errs.push(e.message));
  await p.goto(URL0);
  if (loaded) { await p.setInputFiles("#fileInput", path.resolve(score)); await p.waitForFunction(() => typeof events !== "undefined" && events.length > 0, null, { timeout: 120000 }); }
  await p.waitForTimeout(900);
  return p;
};
const rotate = async (p, w, h) => { await p.setViewportSize({ width: w, height: h }); await p.evaluate(() => { window.dispatchEvent(new Event("orientationchange")); window.dispatchEvent(new Event("resize")); }); await p.waitForTimeout(450); };
const SEQS = {
  "直→橫→直": async (p, w, h) => { await rotate(p, h, w); await rotate(p, w, h); },
  "連轉 3 次": async (p, w, h) => { for (let k = 0; k < 3; k++) { await rotate(p, h, w); await rotate(p, w, h); } },
  "橫的時候切語言主題": async (p, w, h) => { await rotate(p, h, w); await p.evaluate(() => { for (const id of ["langToggle", "themeToggle"]) { const b = $(id); if (b) b.click(); } }); await p.waitForTimeout(300); await p.evaluate(() => { for (const id of ["langToggle", "themeToggle"]) { const b = $(id); if (b) b.click(); } }); await rotate(p, w, h); },
  "快速轉(不等)": async (p, w, h) => { for (let k = 0; k < 4; k++) { await p.setViewportSize({ width: k % 2 ? w : h, height: k % 2 ? h : w }); } await rotate(p, w, h); },
};
let fails = 0, checks = 0;
for (const [w, h] of PHONES) for (const loaded of [false, true]) for (const [vname, open] of Object.entries(VIEWS)) {
  if (vname === "exportDlg" && !loaded) continue;
  const ref = await fresh(w, h, loaded, vname); await open(ref); const want = await snap(ref); await ref.close();
  for (const [sname, seq] of Object.entries(SEQS)) for (const openFirst of [true, false]) {
    const p = await fresh(w, h, loaded, vname);
    if (openFirst) { await open(p); await seq(p, w, h); }
    else { await seq(p, w, h); await open(p); }
    const got = await snap(p);
    const diffs = [];
    for (const k of Object.keys(want)) { const a = want[k], b = got[k]; if (!b) continue; if (Math.abs(a.fs - b.fs) > 0.01) diffs.push(`${k} 字級 ${a.fs}→${b.fs} ${a.txt}`); else if (Math.abs(a.h - b.h) > 2) diffs.push(`${k} 高 ${a.h}→${b.h} ${a.txt}`); }
    checks++;
    if (diffs.length || p.errs.length) { fails++; console.log(`✗ ${w}×${h} ${loaded ? "已載入" : "未載入"} ${vname} ${sname} ${openFirst ? "開著轉" : "轉完才開"}: ${diffs.length} 處不同`, diffs.slice(0, 5).join(" | "), p.errs.slice(0, 3).join(" | ")); }
    await p.close();
  }
}
console.log(fails ? `${fails}/${checks} 項有差異` : `全部 ${checks} 項一致`);
await browser.close(); server.close();
process.exit(fails ? 1 : 0);
