// 彈性速度訓練資料:讓 App 讀每份樂譜,輸出每個事件的 rubatoFeatures() 與時間資訊(JSON)。node rubato_features.mjs <樂譜清單.txt> <輸出目錄>
import { chromium } from "playwright";
import http from "node:http"; import fs from "node:fs"; import path from "node:path";
import { createRequire } from "node:module";
const require = createRequire(import.meta.url);
const [listFile, outDir] = process.argv.slice(2);
const ROOT = path.resolve(path.join(path.dirname(new URL(import.meta.url).pathname), "../.."));
const server = http.createServer((req, res) => { const p = path.join(ROOT, decodeURIComponent(req.url.split("?")[0])); if (!p.startsWith(ROOT) || !fs.existsSync(p) || fs.statSync(p).isDirectory()) { res.writeHead(404); return res.end(); } res.writeHead(200); fs.createReadStream(p).pipe(res); });
await new Promise(r => server.listen(0, "127.0.0.1", r));
const browser = await chromium.launch();
const files = fs.readFileSync(listFile, "utf8").trim().split("\n");
for (const f of files) {
  const out = path.join(outDir, f.replace(/[\/ ]/g, "_") + ".json");
  if (fs.existsSync(out)) continue;
  const page = await browser.newPage({ viewport: { width: 1400, height: 900 } });
  await page.route(/cdn\.jsdelivr\.net\/npm\/opensheetmusicdisplay/, r => r.fulfill({ path: require.resolve("opensheetmusicdisplay/build/opensheetmusicdisplay.min.js"), contentType: "text/javascript" }));
  await page.route(/cdn\.jsdelivr\.net\/npm\/jszip/, r => r.fulfill({ path: require.resolve("jszip/dist/jszip.min.js"), contentType: "text/javascript" }));
  await page.route(/raw\.githubusercontent\.com|tonejs\.github\.io|nbrosowsky|fonts\.g|\.flac/, r => r.abort());
  try {
    await page.goto(`http://127.0.0.1:${server.address().port}/index.html`);
    await page.waitForFunction(() => typeof loadScoreFile === "function");
    await page.setInputFiles("#fileInput", path.resolve(f));
    await page.waitForFunction(() => typeof events !== "undefined" && events.length > 0, null, { timeout: 120000 });
    await page.waitForTimeout(800);
    const data = await page.evaluate(() => {
      try { computePianoDynamics(); } catch (e) {}
      const C = w => wholeToSec(w) * bpm() / 240;
      const ps = detectPhraseBoundaries();
      return {
        totalWhole, totalC: C(totalWhole), timeSig: scoreTimeSig, phraseStarts: ps, X: rubatoFeatures(), words: scoreTempoWords,
        ev: events.map(ev => {
          const p = ev.notes.filter(n => n.freq);
          return [ev.tWhole, C(ev.tWhole), ev.srcT, p.length, ev.notes.length ? Math.max(...ev.notes.map(n => n.durWhole || 0)) : 0,
            p.some(n => (n.staff || 1) === 1) ? 1 : 0, ev.artic && ev.artic.fermata ? 1 : 0, ev.artic && (ev.artic.accent || ev.artic.strongAccent) ? 1 : 0,
            ev.artic && ev.artic.tenuto ? 1 : 0, p.length ? Math.max(...p.map(n => freqToMidi(n.freq))) : null,
            p.length ? p.reduce((a, n) => a + (n.pvel || 0), 0) / p.length : null, ev.barPos, ev.mIdx];
        })
      };
    });
    fs.writeFileSync(out, JSON.stringify(data));
    console.log("ok", f, data.ev.length);
  } catch (e) { console.log("FAIL", f, e.message.slice(0, 80)); fs.writeFileSync(out, "null"); }
  await page.close();
}
await browser.close(); server.close();
