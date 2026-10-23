// 樂譜排版錯誤自動檢查:node engrave_check.mjs <樂譜...>  (ROOT 環境變數可換版本;JSON=1 印詳細)
// 檢查畫面上(單行排版)的 SVG:
//   (TAB 譜的品格數字不算;文字外框扣掉字型上下留白)
//   text-text   文字互相重疊(歌詞、和弦名稱、小節數字、表情文字、連音數字…)
//   text-note   文字壓到符頭/附點升降記號/符桿/符尾旗
//   text-curve  文字壓到圓滑線/延音線(沿線取點)
//   text-beam   文字壓到符尾橫線(沿外框取點)
//   curve-note  圓滑線/延音線穿過別的符頭(端點附近 1.2 格內的符頭不算,那是它自己的音)
//   slur-far    圓滑線端點離自己的音超過 2.5 格
// 都只算真的重疊(內縮 0.3 單位),貼著不算。SHOT=目錄 時每個問題截一張圖(紅圈 = 位置)
import { chromium } from "playwright";
import http from "node:http"; import fs from "node:fs"; import path from "node:path";
const ROOT = process.env.ROOT || path.resolve(path.dirname(new URL(import.meta.url).pathname), "../..");
const server = http.createServer((q, r) => { const p = path.join(ROOT, decodeURIComponent(q.url.split("?")[0])); if (!fs.existsSync(p) || fs.statSync(p).isDirectory()) { r.writeHead(404); return r.end(); } r.writeHead(200, { "content-type": p.endsWith(".html") ? "text/html" : "application/octet-stream" }); fs.createReadStream(p).pipe(r); });
await new Promise(r => server.listen(0, "127.0.0.1", r));
const b = await chromium.launch(); const pg = await b.newPage({ viewport: { width: 1440, height: 900 } });
const errs = []; pg.on("pageerror", e => errs.push(e.message));
await pg.route(/fonts\.googleapis|fonts\.gstatic|jsdelivr|githubusercontent|\.flac/, r => r.abort());
await pg.goto(`http://127.0.0.1:${server.address().port}/index.html`);
await pg.waitForFunction(() => typeof loadScoreFile === "function");
const total = {};
for (const f of process.argv.slice(2)) {
  errs.length = 0;
  await pg.evaluate(() => { window.__prevEv = typeof events !== "undefined" ? events : null; });
  await pg.setInputFiles("#fileInput", f);
  try { await pg.waitForFunction(() => events !== window.__prevEv && events.length > 0 && document.querySelector("#score svg"), null, { timeout: 180000 }); }
  catch (e) { console.log(path.basename(f), "載入逾時"); continue; }
  await pg.waitForTimeout(1200);
  const r = await pg.evaluate(() => {
    // 全部用 SVG 內部座標(1 格 = 10 單位):畫面上的樂譜有 CSS 縮放,混用 getBoundingClientRect / getScreenCTM 會對不上
    const svg = document.querySelector("#score svg");
    const sp = 10;
    const off = el => { let x = 0, y = 0; for (let n = el; n && n !== svg; n = n.parentNode) { const m = n.getAttribute && /translate\(\s*([-\d.]+)[ ,]+([-\d.]+)/.exec(n.getAttribute("transform") || ""); if (m) { x += +m[1]; y += +m[2]; } } return { x, y }; };
    const box = e => { const b = e.getBBox(), o = off(e); return { l: b.x + o.x, t: b.y + o.y, r: b.x + b.width + o.x, b: b.y + b.height + o.y }; };
    const shrink = (B, k) => ({ l: B.l + k, t: B.t + k, r: B.r - k, b: B.b - k });
    const ov = (A, B) => A.l < B.r && B.l < A.r && A.t < B.b && B.t < A.b;
    const inB = (p, B) => p.x > B.l && p.x < B.r && p.y > B.t && p.y < B.b;
    const pts = el => { const o = off(el); const L = el.getTotalLength ? el.getTotalLength() : 0; const out = []; const step = Math.max(0.3, L / 800);
      for (let s = 0; s <= L; s += step) { const p = el.getPointAtLength(s); out.push({ x: p.x + o.x, y: p.y + o.y }); } return out; };
    const M0 = { a: 1, e: 0, d: 1, f: 0, inverse: () => ({ a: 1, b: 0, c: 0, d: 1, e: 0, f: 0 }) };
    const ms = osmd.GraphicSheet.MeasureList.map(row => row.find(m => m)).filter(Boolean).map(m => ({ n: m.MeasureNumber, x: M0.a * m.PositionAndShape.AbsolutePosition.x * 10 + M0.e }));
    const mAt = x => { let n = ms.length ? ms[0].n : 0; for (const m of ms) if (m.x <= x + 1) n = m.n; return n; };
    const q = sel => [...svg.querySelectorAll(sel)];
    const heads = q(".vf-notehead path").map(e => ({ e, B: box(e) })).filter(o => o.B.r > o.B.l);
    const mods = q(".vf-modifiers path, .vf-modifiers text").map(e => ({ e, B: box(e) })).filter(o => o.B.r > o.B.l);
    const stems = q(".vf-stem path, path.vf-stem, .vf-flag path").map(e => ({ e, B: box(e) })).filter(o => o.B.r - o.B.l > 0 || o.B.b - o.B.t > 0);
    const beams = q(".vf-beam path").map(e => ({ e, P: pts(e), B: box(e) }));
    const curves = q(".vf-curve path, .vf-stavetie path, path.vf-curve, path.vf-stavetie").map(e => ({ e, P: pts(e), B: box(e), tie: !!e.closest(".vf-stavetie") || e.classList.contains("vf-stavetie") }));
    const kindOf = t => t.closest(".lyrics") ? "lyric" : t.closest(".measure-number") ? "mnum" : t.closest(".ss-chord") ? "chord" : (t.closest("[class*=tuplet]") ? "tuplet" : "text");
    // <text> 的外框包含字型的上下留白:逐字取範圍(getExtentOfChar),上緣內縮 22%、下緣 18%(g/p/y/j/q 這類有下伸筆畫的字不縮下緣)
    const tchars = e => { const o = off(e), n = e.getNumberOfChars ? e.getNumberOfChars() : 0, out = [];
      for (let i = 0; i < n; i++) { const c = e.textContent[i]; if (!c || !c.trim()) continue; let r; try { r = e.getExtentOfChar(i); } catch (x) { continue; }
        const h = r.height, desc = /[gjpqyf,;]/.test(c); out.push({ l: r.x + o.x + 0.3, r: r.x + r.width + o.x - 0.3, t: r.y + o.y + 0.22 * h, b: r.y + r.height + o.y - (desc ? 0.05 : 0.18) * h }); }
      return out; };
    const texts = q("text").filter(t => t.textContent.trim() && !t.closest(".vf-tabnote")).map(e => { const C = tchars(e); if (!C.length) return null;
      return { e, k: kindOf(e), s: e.textContent.trim(), C, B: { l: Math.min(...C.map(c => c.l)), r: Math.max(...C.map(c => c.r)), t: Math.min(...C.map(c => c.t)), b: Math.max(...C.map(c => c.b)) } }; }).filter(Boolean);
    const ovT = (T, B) => ov(T.B, B) && T.C.some(c => ov(c, B));
    const inT = (p, T) => inB(p, T.B) && T.C.some(c => inB(p, c));
    const out = [];
    const inv = M0.inverse();
    const add = (type, x, msg, y) => { const sx = inv.a * x + inv.c * (y || 0) + inv.e, sy = y != null ? inv.b * x + inv.d * y + inv.f : null; out.push({ type, m: mAt(x), msg, sx, sy }); };
    for (let i = 0; i < texts.length; i++) for (let j = i + 1; j < texts.length; j++) {
      const A = texts[i], C = texts[j];
      if (ov(A.B, C.B) && A.C.some(a => C.C.some(c => ov(a, c))) && !(A.s === C.s && Math.abs(A.B.l - C.B.l) < 1 && Math.abs(A.B.t - C.B.t) < 1)) add("text-text", A.B.l, `${A.k}「${A.s}」×${C.k}「${C.s}」`);
    }
    for (const T of texts) {
      for (const H of [...heads, ...mods, ...stems]) if (ovT(T, shrink(H.B, 0.3))) { add("text-note", T.B.l, `${T.k}「${T.s}」× ${H.e.closest(".vf-modifiers") ? "記號" : H.e.closest(".vf-notehead") ? "符頭" : "符桿/旗"}`, (T.B.t + T.B.b) / 2); break; }
      for (const C of curves) if (ov(T.B, C.B) && C.P.some(p => inT(p, T))) { add("text-curve", T.B.l, `${T.k}「${T.s}」× ${C.tie ? "延音線" : "圓滑線"}`, (T.B.t + T.B.b) / 2); break; }
      for (const Bm of beams) if (ov(T.B, Bm.B) && Bm.P.some(p => inT(p, T))) { add("text-beam", T.B.l, `${T.k}「${T.s}」× 符尾線`, (T.B.t + T.B.b) / 2); break; }
    }
    for (const C of curves) {
      const a = C.P[0], z = C.P.reduce((p, c) => (c.x > p.x ? c : p), C.P[0]), s = C.P.reduce((p, c) => (c.x < p.x ? c : p), C.P[0]);
      for (const H of heads) {
        if (!ov(C.B, H.B)) continue;
        const cx = (H.B.l + H.B.r) / 2;
        if (Math.abs(cx - s.x) < 1.2 * sp || Math.abs(cx - z.x) < 1.2 * sp) continue;
        const HB = shrink(H.B, (H.B.b - H.B.t) * 0.2);
        if (C.P.some(p => inB(p, HB))) { add("curve-note", cx, (C.tie ? "延音線" : "圓滑線") + "穿過符頭", (H.B.t + H.B.b) / 2); break; }
      }
    }
    // 圓滑線端點離自己的音太遠(OSMD 資料)
    try {
      for (const sys of osmd.GraphicSheet.MusicPages[0].MusicSystems) for (const sl of sys.StaffLines) for (const gs of sl.GraphicalSlurs || []) {
        const sy = sl.PositionAndShape.AbsolutePosition.y, sx = sl.PositionAndShape.AbsolutePosition.x;
        const chk = (pt, note, se) => {
          if (!pt || !note || !se) return;
          let ve = null; for (const v of se.graphicalVoiceEntries) if (v.notes.some(n => n.sourceNote === note)) ve = v;
          if (!ve) return; const ps = ve.PositionAndShape, top = ps.AbsolutePosition.y - sy + ps.BorderMarginTop, bot = ps.AbsolutePosition.y - sy + ps.BorderMarginBottom;
          const d = pt.y < top ? top - pt.y : pt.y > bot ? pt.y - bot : 0;
          if (d > 2.5) add("slur-far", M0.a * (pt.x + sx) * 10 + M0.e, `端點離音 ${d.toFixed(1)} 格`, M0.d * (pt.y + sy) * 10 + M0.f);
        };
        chk(gs.bezierStartPt, gs.slur && gs.slur.StartNote, gs.staffEntries[0]);
        chk(gs.bezierEndPt, gs.slur && gs.slur.EndNote, gs.staffEntries[gs.staffEntries.length - 1]);
      }
    } catch (e) {}
    return { n: ms.length, out };
  });
  if (process.env.SHOT) {   // SHOT=目錄:每個問題截一張圖(以問題位置為中心,寬 30 格、高 24 格)
    fs.mkdirSync(process.env.SHOT, { recursive: true });
    let k = 0;
    for (const o of r.out.slice(0, 40)) {
      if (o.sy == null) continue;
      const file = path.join(process.env.SHOT, `${path.basename(f).replace(/\W+/g, "_")}_${String(++k).padStart(2, "0")}_${o.type}_m${o.m}.png`);
      await pg.evaluate(o => { const svg = document.querySelector("#score svg").cloneNode(true); const u = 10 * (osmd.zoom || 1);
        svg.setAttribute("viewBox", `${o.sx - 15 * u} ${o.sy - 12 * u} ${30 * u} ${24 * u}`); svg.setAttribute("width", 600); svg.setAttribute("height", 480);
        const old = document.getElementById("__shot"); if (old) old.remove();
        const d = document.createElement("div"); d.id = "__shot"; d.style.cssText = "position:fixed;left:0;top:0;width:600px;height:480px;background:#fff;z-index:99999"; d.appendChild(svg);
        const c = document.createElementNS("http://www.w3.org/2000/svg", "circle"); c.setAttribute("cx", o.sx); c.setAttribute("cy", o.sy); c.setAttribute("r", 1.6 * u); c.setAttribute("fill", "none"); c.setAttribute("stroke", "red"); c.setAttribute("stroke-width", 1.5); svg.appendChild(c);
        document.body.appendChild(d); }, o);
      await pg.screenshot({ path: file, clip: { x: 0, y: 0, width: 600, height: 480 } });
    }
    await pg.evaluate(() => { const old = document.getElementById("__shot"); if (old) old.remove(); });
  }
  const by = {};
  for (const o of r.out) (by[o.type] = by[o.type] || []).push(o);
  const summary = Object.entries(by).map(([k, v]) => `${k} ${v.length}`).join(" · ") || "沒有問題";
  console.log(`${path.basename(f)}(${r.n} 小節):${summary}${errs.length ? " · 錯誤 " + errs.join(" / ") : ""}`);
  for (const [k, v] of Object.entries(by)) { total[k] = (total[k] || 0) + v.length; for (const o of v.slice(0, process.env.JSON ? 999 : 6)) console.log(`    ${k} 第 ${o.m} 小節 ${o.msg}`); }
}
console.log("合計", JSON.stringify(total));
await b.close(); server.close();
