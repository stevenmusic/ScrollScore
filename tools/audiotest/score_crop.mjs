// 樂譜局部截圖:node score_crop.mjs <樂譜> <輸出前綴> <小節,...|0> [{"rules":{OSMD 排版規則}}]
// 小節編號照 OSMD 的 MeasureNumber(截 2 小節);0 = 自動找大譜表上下兩行最擠的 4 個地方(看是什麼撐開間距)
import { chromium } from "playwright";
import http from "node:http"; import fs from "node:fs"; import path from "node:path";
import { createRequire } from "node:module";
const require = createRequire(import.meta.url);
const [score, out, list, cfg] = process.argv.slice(2);
const ROOT = "/home/user/ScrollScore";
const server = http.createServer((req, res) => { const p = path.join(ROOT, decodeURIComponent(req.url.split("?")[0])); if (!fs.existsSync(p) || fs.statSync(p).isDirectory()) { res.writeHead(404); return res.end(); } res.writeHead(200); fs.createReadStream(p).pipe(res); });
await new Promise(r => server.listen(0, "127.0.0.1", r));
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1400, height: 900 } });
await page.route(/raw\.githubusercontent\.com|\.flac|fonts\.g|jsdelivr/, r => r.abort());
await page.goto(`http://127.0.0.1:${server.address().port}/index.html`);
await page.waitForFunction(() => typeof loadScoreFile === "function");

await page.setInputFiles("#fileInput", path.resolve(score));
await page.waitForFunction(() => typeof events !== "undefined" && events.length > 0, null, { timeout: 120000 });
await page.waitForTimeout(1000);
if (cfg && JSON.parse(cfg).rules) await page.evaluate(c => { Object.assign(osmd.EngravingRules, JSON.parse(c).rules); osmd.render(); }, cfg);
const data = await page.evaluate(ms => {
  const svg = $("score").querySelector("svg"); const z = 10;
  const ML = osmd.GraphicSheet.MeasureList;
  const res = [];
  if (ms[0] === 0) {   // 自動:找最擠的地方(需要的距離 − 實際距離 最大)
    const L = osmd.GraphicSheet.MusicPages[0].MusicSystems[0].StaffLines, b = L[0].BottomLine, k = L[1].SkyLine, R = osmd.EngravingRules;
    const cur = L[1].PositionAndShape.RelativePosition.y - L[0].PositionAndShape.RelativePosition.y;
    const x0 = L[0].PositionAndShape.AbsolutePosition.x, over = [];
    for (let t = 0; t < b.length; t++) { let a = 0; for (let j = Math.max(0, t - 6); j <= Math.min(k.length - 1, t + 6); j++) a = Math.min(a, k[j]); over.push(b[t] - a + R.MinSkyBottomDistBetweenStaves - cur); }
    const picks = [];
    const idx = over.map((v, i) => [v, i]).sort((p, q) => q[0] - p[0]);
    for (const [v, i] of idx) { if (picks.length >= 4 || v <= -2) break; const x = (x0 + i / 3) * z; if (picks.some(p => Math.abs(p.x - x) < 900)) continue; picks.push({ x, v }); }
    for (const p of picks) res.push({ m: "x" + Math.round(p.x) + "_over" + p.v.toFixed(1), x0: p.x - 500, x1: p.x + 500 });
    return { svg: new XMLSerializer().serializeToString(svg), h: parseFloat(svg.getAttribute("height")), res };
  }
  for (const m of ms) {
    const sm = osmd.GraphicSheet.MusicPages[0].MusicSystems[0].StaffLines[0].Measures;
    const i0 = sm.findIndex(q => q.MeasureNumber === m); if (i0 < 0) continue;
    const rw = [sm[i0]], ls = [sm[Math.min(sm.length - 1, i0 + 1)]];
    { const x0 = rw[0].PositionAndShape.AbsolutePosition.x * z - 20, x1 = (ls[0].PositionAndShape.AbsolutePosition.x + ls[0].PositionAndShape.Size.width) * z + 20; res.push({ m, x0, x1 }); continue; }
    const x0 = row[0].PositionAndShape.AbsolutePosition.x * z - 20;
    const last = ML.find(r => r[0] && r[0].MeasureNumber === m + 3) || row;
    const x1 = (last[0].PositionAndShape.AbsolutePosition.x + last[0].PositionAndShape.Size.width) * z + 20;
    res.push({ m, x0, x1 });
  }
  return { svg: new XMLSerializer().serializeToString(svg), h: parseFloat(svg.getAttribute("height")), res };
}, list.split(",").map(Number));
const p2 = await browser.newPage({ viewport: { width: 1600, height: 900 } });
for (const r of data.res) {
  const w = r.x1 - r.x0, sc = 1600 / w;
  const svg = data.svg.replace(/<svg([^>]*)>/, (all, attrs) => `<svg${attrs.replace(/\s(width|height|viewBox)="[^"]*"/g, "")} width="1600" height="${Math.round(data.h * sc)}" viewBox="${r.x0} 0 ${w} ${data.h}">`);
  await p2.setContent(`<body style="margin:0;background:#fff">${svg}</body>`);
  await p2.setViewportSize({ width: 1600, height: Math.round(data.h * sc) });
  await p2.screenshot({ path: `${out}_m${r.m}.png` });
}
console.log("done", data.res.length);
await browser.close(); server.close();
