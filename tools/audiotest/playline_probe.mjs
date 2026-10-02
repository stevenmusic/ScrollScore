// 播放軸長度檢查:node playline_probe.mjs a.musicxml,b.musicxml <截圖目錄>(各裝置畫面 + 匯出影片各版面,單位:譜線間距)
// 量播放軸上下端離「譜線+符頭」多遠(單位:譜線間距),App 畫面各裝置 + 匯出影片各版面
import { chromium, devices } from "playwright";
import http from "node:http"; import fs from "node:fs"; import path from "node:path";
import { createRequire } from "node:module";
const require = createRequire(import.meta.url);
const ROOT = process.env.ROOT || "/home/user/ScrollScore", SHOTS = process.argv[3], scores = process.argv[2].split(",");
const server = http.createServer((req, res) => { const p = path.join(ROOT, decodeURIComponent(req.url.split("?")[0])); if (!fs.existsSync(p) || fs.statSync(p).isDirectory()) { res.writeHead(404); return res.end(); } res.writeHead(200); fs.createReadStream(p).pipe(res); });
await new Promise(r => server.listen(0, "127.0.0.1", r));
const browser = await chromium.launch();
const DEV = { desktop: { viewport: { width: 1440, height: 900 } }, iphone: devices["iPhone 13"], iphoneL: devices["iPhone 13 landscape"], ipad: devices["iPad (gen 7)"], android: devices["Pixel 7"] };
const measureJS = () => {
  const svg = document.querySelector("#score svg"), pl = $("playline").getBoundingClientRect();
  const lines = [...svg.querySelectorAll(".vf-measure > path")].map(e => e.getBoundingClientRect()).filter(r => r.width > 20 && r.height < 3);
  const ys = [...new Set(lines.map(r => Math.round(r.top * 2) / 2))].sort((a, b) => a - b);
  const diffs = ys.slice(1).map((y, i) => y - ys[i]).filter(d => d > 1).sort((a, b) => a - b);
  const sp = diffs[Math.floor(diffs.length / 4)] || 8;
  let top = Infinity, bot = -Infinity;
  for (const e of [...svg.querySelectorAll(".vf-measure > path"), ...svg.querySelectorAll(".vf-notehead")]) { const q = e.getBoundingClientRect(); if (q.width || q.height) { top = Math.min(top, q.top); bot = Math.max(bot, q.bottom); } }
  const st = $("stage").getBoundingClientRect();
  return { sp: +sp.toFixed(1), topPad: +((top - pl.top) / sp).toFixed(1), botPad: +((pl.bottom - bot) / sp).toFixed(1), plLen: Math.round(pl.height), contentH: Math.round(bot - top), plInStage: pl.top >= st.top - 1 && pl.bottom <= st.bottom + 1 };
};
for (const score of scores) {
  const name = path.basename(score, ".musicxml");
  for (const [dname, dev] of Object.entries(DEV)) {
    const ctx = await browser.newContext(dev); const page = await ctx.newPage();
    await page.route(/cdn\.jsdelivr\.net\/npm\/opensheetmusicdisplay/, r => r.fulfill({ path: require.resolve("opensheetmusicdisplay/build/opensheetmusicdisplay.min.js") }));
    await page.route(/cdn\.jsdelivr\.net\/npm\/jszip/, r => r.fulfill({ path: require.resolve("jszip/dist/jszip.min.js") }));
    await page.route(/raw\.githubusercontent|tonejs|nbrosowsky|fonts\.g|\.flac/, r => r.abort());
    await page.goto(`http://127.0.0.1:${server.address().port}/index.html`);
    await page.waitForFunction(() => typeof loadScoreFile === "function");
    await page.setInputFiles("#fileInput", score);
    await page.waitForFunction(() => typeof events !== "undefined" && events.length > 0, null, { timeout: 120000 });
    await page.waitForTimeout(800);
    const live = await page.evaluate(measureJS);
    console.log(name, dname, "live", JSON.stringify(live));
    await page.screenshot({ path: `${SHOTS}/pl_${name}_${dname}.png` });
    if (dname === "desktop") {
      for (const [W, H, sh] of [[1920, 1080, 440], [1080, 1920, 380]]) for (const kb of [true, false]) {
        const r = await page.evaluate(async ([W, H, sh, kb]) => {
          const cfg = Object.assign({ W, H, scoreH: sh, align: "center", bitrate: 5e6, fps: 30, includeKeyboard: kb }, watermarkCfg());
          const layout = computeExportLayout(cfg); const { tiles, scale } = await rasterizeScore(layout.SCORE_H);
          const cv = document.createElement("canvas"); cv.width = W; cv.height = H; const c = cv.getContext("2d");
          let rec = null; const mt = c.moveTo.bind(c), lt = c.lineTo.bind(c);
          c.moveTo = (x, y) => { if (c.lineWidth === 4 && !rec) rec = { top: y }; return mt(x, y); };
          c.lineTo = (x, y) => { if (c.lineWidth === 4 && rec && rec.bottom == null) rec.bottom = y; return lt(x, y); };
          drawExportFrame(c, layout, cfg, tiles, scale, 3, useCalib());
          const svg = $("score").querySelector("svg"), sr = svg.getBoundingClientRect(), k = layout.SCORE_H / sr.height;
          const lines = [...svg.querySelectorAll(".vf-measure > path")].map(e => e.getBoundingClientRect()).filter(q => q.width > 20 && q.height < 3);
          const ys = [...new Set(lines.map(q => Math.round(q.top * 2) / 2))].sort((a, b) => a - b);
          const diffs = ys.slice(1).map((y, i) => y - ys[i]).filter(d => d > 1).sort((a, b) => a - b);
          const sp = (diffs[Math.floor(diffs.length / 4)] || 8) * k;
          let top = Infinity, bot = -Infinity;
          for (const e of [...svg.querySelectorAll(".vf-measure > path"), ...svg.querySelectorAll(".vf-notehead")]) { const q = e.getBoundingClientRect(); if (q.width || q.height) { top = Math.min(top, q.top); bot = Math.max(bot, q.bottom); } }
          top = layout.topY + (top - sr.top) * k; bot = layout.topY + (bot - sr.top) * k;
          const kbTop = kb ? H - layout.kbH : H;
          return { sp: +sp.toFixed(1), topPad: +((top - rec.top) / sp).toFixed(1), botPad: +((rec.bottom - bot) / sp).toFixed(1), plTop: Math.round(rec.top), plBot: Math.round(rec.bottom), kbTop: Math.round(kbTop), overlapsKb: rec.bottom > kbTop, url: cv.toDataURL("image/jpeg", 0.7) };
        }, [W, H, sh, kb]);
        fs.writeFileSync(`${SHOTS}/plx_${name}_${W}x${H}_${kb ? "kb" : "score"}.jpg`, Buffer.from(r.url.split(",")[1], "base64")); delete r.url;
        console.log(name, `export ${W}x${H} ${kb ? "kb" : "score"}`, JSON.stringify(r));
      }
    }
    await ctx.close();
  }
}
await browser.close(); server.close();
