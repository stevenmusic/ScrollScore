// Guitar Pro 匯入比對:node gp_compare.mjs <檔.gp> <輸出前綴> [--track N] [--root 目錄]
// 產生 <前綴>-alphatab.png(alphaTab 照 Guitar Pro 規則排的版,當作「原檔長相」的參考)、
// <前綴>-app.png(ScrollScore 匯入後畫面上的整條樂譜)、<前綴>.musicxml(轉換結果)
import { chromium } from "playwright";
import http from "node:http"; import fs from "node:fs"; import path from "node:path";
import { createRequire } from "node:module";
const require = createRequire(import.meta.url);
const args = process.argv.slice(2);
const opt = (k, d) => { const i = args.indexOf("--" + k); return i >= 0 ? args[i + 1] : d; };
const ROOT = path.resolve(opt("root", path.join(path.dirname(new URL(import.meta.url).pathname), "../..")));
const AT_DIST = path.join(path.dirname(new URL(import.meta.url).pathname), "node_modules/@coderline/alphatab/dist");
const gpFile = path.resolve(args[0]), prefix = args[1], track = +opt("track", "-1");
const server = http.createServer((req, res) => {
  const u = decodeURIComponent(req.url.split("?")[0]);
  if (u === "/__gp") { res.writeHead(200); return fs.createReadStream(gpFile).pipe(res); }
  if (u === "/__at.html") { res.writeHead(200, { "content-type": "text/html" }); return res.end(`<!doctype html><body style="margin:0;background:#fff"><div id="at" style="width:1600px"></div>
<script src="/__atdist/alphaTab.min.js"></script><script>
const api = new alphaTab.AlphaTabApi(document.getElementById("at"), { core: { fontDirectory: "/__atdist/font/", useWorkers: false, engine: "svg" },
  display: { layoutMode: alphaTab.LayoutMode.Page }, notation: { notationMode: alphaTab.NotationMode.GuitarPro }, player: { playerMode: 0 } });
api.renderFinished.on(() => { window.__done = true; });
fetch("/__gp").then(r => r.arrayBuffer()).then(b => { const s = alphaTab.importer.ScoreLoader.loadScoreFromBytes(new Uint8Array(b), api.settings);
  const t = ${track} >= 0 ? ${track} : Math.max(0, s.tracks.findIndex(t => t.isPercussion));
  for (const st of s.tracks[t].staves) st.showTablature = false;
  api.renderScore(s, [t]); });
</script>`); }
  if (u.startsWith("/__atdist/")) { const p = path.join(AT_DIST, u.slice(10)); if (fs.existsSync(p)) { res.writeHead(200); return fs.createReadStream(p).pipe(res); } res.writeHead(404); return res.end(); }
  const p = path.join(ROOT, u);
  if (!p.startsWith(ROOT) || !fs.existsSync(p) || fs.statSync(p).isDirectory()) { res.writeHead(404); return res.end(); }
  res.writeHead(200); fs.createReadStream(p).pipe(res);
});
await new Promise(r => server.listen(0, "127.0.0.1", r));
const base = `http://127.0.0.1:${server.address().port}`;
const browser = await chromium.launch();
// 1) alphaTab 參考
const pa = await browser.newPage({ viewport: { width: 1600, height: 900 } });
pa.on("pageerror", e => console.error("[alphatab pageerror]", e.message));
await pa.goto(base + "/__at.html");
await pa.waitForFunction(() => window.__done, null, { timeout: 60000 });
await pa.waitForTimeout(500);
await pa.locator("#at").screenshot({ path: prefix + "-alphatab.png" });
// 2) ScrollScore
const page = await browser.newPage({ viewport: { width: 1400, height: 900 } });
const errors = [];
page.on("pageerror", e => { errors.push(e.message); console.error("[pageerror]", e.message); });
page.on("console", m => { if (m.type() === "error") errors.push(m.text()); });
await page.route(/cdn\.jsdelivr\.net\/npm\/opensheetmusicdisplay/, r => r.fulfill({ path: require.resolve("opensheetmusicdisplay/build/opensheetmusicdisplay.min.js"), contentType: "text/javascript" }));
await page.route(/cdn\.jsdelivr\.net\/npm\/jszip/, r => r.fulfill({ path: require.resolve("jszip/dist/jszip.min.js"), contentType: "text/javascript" }));
await page.route(/cdn\.jsdelivr\.net\/npm\/@coderline\/alphatab@[\d.]+\/dist\/alphaTab\.min\.js/, r => r.fulfill({ path: path.join(AT_DIST, "alphaTab.min.js"), contentType: "text/javascript" }));
await page.route(/raw\.githubusercontent\.com|tonejs\.github\.io|nbrosowsky|fonts\.g/, r => r.abort());
await page.goto(base + "/index.html");
await page.waitForFunction(() => typeof loadScoreFile === "function");
await page.setInputFiles("#fileInput", gpFile);
await page.waitForFunction(() => $("trackOverlay").classList.contains("show") || (typeof events !== "undefined" && events.length > 0), null, { timeout: 60000 });
if (await page.evaluate(() => $("trackOverlay").classList.contains("show"))) {
  const btns = page.locator("#trackList button");
  console.log("tracks:", (await btns.allTextContents()).join(" | "));
  if (track >= 0) await btns.nth(track).click();
  else if (await page.locator("#trackList button[style]").count()) await page.locator("#trackList button[style]").click();
  else await btns.first().click();
}
await page.waitForFunction(() => typeof events !== "undefined" && events.length > 0, null, { timeout: 60000 }).catch(() => {});
await page.waitForTimeout(1200);
fs.writeFileSync(prefix + ".musicxml", await page.evaluate(() => lastXmlText || ""));
console.log(await page.evaluate(() => ($("status") || {}).textContent || ""));
console.log("events:", await page.evaluate(() => events.length), "drumScore:", await page.evaluate(() => isDrumScore));
// 整條樂譜(SVG 本身,不受畫面寬度限制)
const svgB64 = await page.evaluate(async () => {
  const svg = $("score").querySelector("svg"); if (!svg) return null;
  const c = svg.cloneNode(true); const w = +svg.getAttribute("width"), h = +svg.getAttribute("height");
  c.setAttribute("xmlns", "http://www.w3.org/2000/svg");
  const img = new Image(); img.src = "data:image/svg+xml;charset=utf-8," + encodeURIComponent(new XMLSerializer().serializeToString(c));
  await img.decode();
  const W = Math.min(w, 16000), cv = document.createElement("canvas"); cv.width = W; cv.height = h;
  const g = cv.getContext("2d"); g.fillStyle = "#fff"; g.fillRect(0, 0, W, h); g.drawImage(img, 0, 0);
  return cv.toDataURL("image/png").split(",")[1];
});
if (svgB64) fs.writeFileSync(prefix + "-app.png", Buffer.from(svgB64, "base64"));
console.log("drum keys:", await page.evaluate(() => { const h = {}; for (const ev of events) for (const n of ev.notes) if (n.drum) h[n.key + (n.ghost ? "g" : "")] = (h[n.key + (n.ghost ? "g" : "")] || 0) + 1; return JSON.stringify(h); }));
console.log("errors:", errors.length ? errors : "none");
await browser.close(); server.close();
