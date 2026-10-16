// 中文換行檢查:打開 App 的每個畫面,在各種寬度下逐字算出每段文字實際在哪裡換行,列出不好看的斷法。
// node text_wrap_check.mjs [樂譜=../../samples/ode-to-joy.musicxml] [--lang zh|en] [--all(連沒問題的也列出)]
// 抓的問題:括號被拆到兩行、數字和單位/英文單字被拆開、最後一行只剩 1~2 個字、標點跑到行首(或開括號留在行尾)
import { chromium } from "playwright";
import http from "node:http"; import fs from "node:fs"; import path from "node:path";
const args = process.argv.slice(2);
const opt = (k, d) => { const i = args.indexOf("--" + k); return i >= 0 ? args[i + 1] : d; };
const score = path.resolve(args.find(a => !a.startsWith("--") && args[args.indexOf(a) - 1] !== "--lang") || path.join(path.dirname(new URL(import.meta.url).pathname), "../../samples/ode-to-joy.musicxml"));
const LANG = opt("lang", "zh"), SHOW_ALL = args.includes("--all");
const ROOT = path.resolve(path.join(path.dirname(new URL(import.meta.url).pathname), "../.."));
const server = http.createServer((req, res) => { const p = path.join(ROOT, decodeURIComponent(req.url.split("?")[0])); if (!fs.existsSync(p) || fs.statSync(p).isDirectory()) { res.writeHead(404); return res.end(); } res.writeHead(200); fs.createReadStream(p).pipe(res); });
await new Promise(r => server.listen(0, "127.0.0.1", r));
const browser = await chromium.launch();
const SIZES = [[280, 653], [320, 568], [360, 740], [390, 844], [430, 932], [568, 320], [768, 1024], [1280, 800]];

// 在頁面裡執行:掃 root 底下所有看得到的文字,依「最近的區塊層級祖先」分組,逐字取位置分行
const SCAN = (rootSel) => {
  const root = document.querySelector(rootSel);
  if (!root) return [];
  const isInlineish = el => { const d = getComputedStyle(el).display; return d === "inline" || d === "inline-block" || d === "contents"; };
  const blockOf = n => { let e = n.parentElement; while (e && e !== root && isInlineish(e)) e = e.parentElement; return e; };
  const groups = new Map();
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
  for (let t = walker.nextNode(); t; t = walker.nextNode()) {
    // 元素之間的空白(例如 <b>…</b> <a>…</a>)也要留著,不然兩個單字看起來黏在一起
    const p = t.parentElement;
    if (!p || p.closest("svg,script,style,option,select,textarea")) continue;
    const r = p.getBoundingClientRect();
    if (!r.width || !r.height) continue;
    const st = getComputedStyle(p); if (st.visibility === "hidden" || +st.opacity === 0) continue;
    const b = blockOf(t);
    if (!groups.has(b)) groups.set(b, []);
    groups.get(b).push(t);
  }
  const out = [];
  for (const [b, nodes] of groups) {
    const chars = [];
    for (const t of nodes) {
      const s = t.textContent;
      for (let i = 0; i < s.length; i++) {
        const rg = document.createRange(); rg.setStart(t, i); rg.setEnd(t, i + 1);
        const rc = rg.getClientRects()[0];
        chars.push({ c: s[i], top: rc ? rc.top : null, h: rc ? rc.height : 0 });
      }
    }
    const lines = []; let cur = null, lastTop = null;
    for (const ch of chars) {
      if (ch.top == null) { if (cur) cur.push(ch.c); continue; }
      if (lastTop == null || Math.abs(ch.top - lastTop) > Math.max(3, ch.h * 0.5)) { cur = []; lines.push(cur); lastTop = ch.top; }
      cur.push(ch.c);
    }
    const L = lines.map(l => l.join("").replace(/\s+/g, " ").trim()).filter(Boolean);
    const full = chars.map(c => c.c).join("");
    if (!/[㐀-鿿]/.test(full) && !/[A-Za-z]{2,}/.test(full)) continue;
    const issues = [];
    if (L.length > 1) {
      for (let i = 0; i < L.length; i++) {
        const l = L[i];
        const opens = (l.match(/[(（「『]/g) || []).length, closes = (l.match(/[)）」』]/g) || []).length;
        if (opens > closes) issues.push("括號被拆開");
        if (i > 0 && /^[、,，。.;；:：!！?？)）」』%]/.test(l)) issues.push("標點在行首");
        if (i < L.length - 1) {
          const a = l.slice(-1), z = L[i + 1][0];
          // 原文這兩個字之間沒有空白才算拆開(「V3 by」本來就有空格,不算)
          const glued = full.replace(/\s+/g, " ").includes(l.slice(-6) + L[i + 1].slice(0, 6));
          if (glued && /[0-9]/.test(a) && /[A-Za-z%]/.test(z)) issues.push("數字和單位被拆開");
          if (glued && /[A-Za-z]/.test(a) && /[A-Za-z]/.test(z)) issues.push("英文單字被拆開");
        }
      }
      const last = L[L.length - 1].replace(/[、,，。.;；:：!！?？)）」』\s]/g, "");
      if (/[㐀-鿿]/.test(full) && last.length <= 2) issues.push("最後一行只剩「" + L[L.length - 1] + "」");
    }
    const desc = (b.id ? "#" + b.id : b.tagName.toLowerCase() + (b.className && typeof b.className === "string" ? "." + b.className.split(" ")[0] : "")) + (b.getAttribute("data-i18n") ? "[" + b.getAttribute("data-i18n") + "]" : "");
    out.push({ desc, lines: L, issues: [...new Set(issues)] });
  }
  return out;
};

const STATES = [
  { name: "開始畫面", root: "body", prep: async () => {} , beforeLoad: true },
  { name: "設定面板", root: "#settingsPanel", prep: async p => p.evaluate(() => { openSettingsSheet(); document.querySelectorAll("#settingsPanel details").forEach(d => d.open = true); }) },
  { name: "頂欄", root: "header", prep: async p => p.evaluate(() => closeSettingsSheet()) },
  { name: "速度", root: "#tempoPopover", prep: async p => p.evaluate(() => $("tempoPopover").classList.add("open")) },
  { name: "匯出影片", root: "#formatOverlay", prep: async p => { await p.evaluate(() => { $("tempoPopover").classList.remove("open"); openExportSheet(); $("expAdvanced").open = true; $("exportRangeToggle").checked = true; $("exportRangeToggle").dispatchEvent(new Event("change")); }); await p.waitForTimeout(1500); } },
  { name: "匯出中", root: "#exportOverlay", prep: async p => p.evaluate(() => { $("formatOverlay").classList.remove("show"); $("exportOverlay").classList.add("show"); $("exportOverlayTitle").textContent = T("exportAnalyzingPct", { pct: 37 }); $("exportOverlaySub").textContent = T("exportAnalyzingSub"); }) },
  { name: "儲存影片", root: "#shareOverlay", prep: async p => p.evaluate(() => { $("exportOverlay").classList.remove("show"); $("shareOverlay").classList.add("show"); }) },
  { name: "選擇音軌", root: "#trackOverlay", prep: async p => p.evaluate(() => { $("shareOverlay").classList.remove("show"); $("trackOverlay").classList.add("show"); }) },
  { name: "快捷鍵", root: "#shortcutOverlay", prep: async p => p.evaluate(() => { $("trackOverlay").classList.remove("show"); $("kbdHint").click(); }) },
  { name: "跳到時間", root: "#seekPopover", prep: async p => p.evaluate(() => { $("shortcutOverlay").classList.remove("show"); openSeekPopover(); }) },
];

const found = new Map();   // key: 狀態 + 元素 + 問題 → 哪些寬度
for (const [w, h] of SIZES) {
  const page = await browser.newPage({ viewport: { width: w, height: h } });
  await page.route(/raw\.githubusercontent\.com|\.flac|fonts\.g|jsdelivr/, r => r.abort());
  await page.goto(`http://127.0.0.1:${server.address().port}/index.html`);
  await page.waitForFunction(() => typeof applyLanguage === "function");
  await page.evaluate(l => applyLanguage(l), LANG);
  let loaded = false;
  for (const s of STATES) {
    if (!s.beforeLoad && !loaded) {
      await page.setInputFiles("#fileInput", score);
      await page.waitForFunction(() => typeof events !== "undefined" && events.length > 0, null, { timeout: 120000 });
      await page.waitForTimeout(800);
      loaded = true;
    }
    try { await s.prep(page); } catch (e) { console.log("無法打開", s.name, e.message); continue; }
    await page.waitForTimeout(250);
    const res = await page.evaluate(SCAN, s.root);
    for (const r of res) {
      if (!r.issues.length && !SHOW_ALL) continue;
      const key = s.name + " " + r.desc + " " + (r.issues.join("、") || "(無)");
      if (!found.has(key)) found.set(key, { widths: [], sample: r.lines });
      found.get(key).widths.push(w);
    }
  }
  await page.close();
}
for (const [k, v] of found) console.log(`${k}  @${v.widths.join(",")}\n    ${v.sample.join(" / ")}`);
console.log(found.size ? `共 ${found.size} 項` : "沒有發現不好看的換行");
await browser.close(); server.close();
