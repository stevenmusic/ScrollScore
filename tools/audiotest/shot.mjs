// 樂譜畫面截圖:node shot.mjs <樂譜> <輸出.png> [--root 目錄]
// 一併印出載入狀態列與頁面錯誤,檢查記譜/載入問題用
import { chromium } from "playwright";
import http from "node:http"; import fs from "node:fs"; import path from "node:path";
import { createRequire } from "node:module";
const require = createRequire(import.meta.url);
const args = process.argv.slice(2);
const opt = (k, d) => { const i = args.indexOf("--" + k); return i >= 0 ? args[i + 1] : d; };
const ROOT = path.resolve(opt("root", path.join(path.dirname(new URL(import.meta.url).pathname), "../..")));
const server = http.createServer((req, res) => {
  const p = path.join(ROOT, decodeURIComponent(req.url.split("?")[0]));
  if (!p.startsWith(ROOT) || !fs.existsSync(p) || fs.statSync(p).isDirectory()) { res.writeHead(404); return res.end(); }
  res.writeHead(200); fs.createReadStream(p).pipe(res);
});
await new Promise(r => server.listen(0, "127.0.0.1", r));
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1400, height: 900 } });
page.on("pageerror", e => console.error("[pageerror]", e.message));
await page.route(/cdn\.jsdelivr\.net\/npm\/opensheetmusicdisplay/, r => r.fulfill({ path: require.resolve("opensheetmusicdisplay/build/opensheetmusicdisplay.min.js"), contentType: "text/javascript" }));
await page.route(/cdn\.jsdelivr\.net\/npm\/jszip/, r => r.fulfill({ path: require.resolve("jszip/dist/jszip.min.js"), contentType: "text/javascript" }));
await page.route(/raw\.githubusercontent\.com|tonejs\.github\.io|nbrosowsky|fonts\.g/, r => r.abort());
await page.goto(`http://127.0.0.1:${server.address().port}/index.html`);
await page.waitForFunction(() => typeof loadScoreFile === "function");
await page.setInputFiles("#fileInput", path.resolve(args[0]));
await page.waitForFunction(() => typeof events !== "undefined" && events.length > 0, null, { timeout: 120000 }).catch(() => {});
await page.waitForTimeout(+opt("wait", 1500));
if (opt("eval", null)) console.log(await page.evaluate(opt("eval")));
console.log(await page.evaluate(() => ($("status") || {}).textContent || ""));
await page.screenshot({ path: args[1] });
await browser.close(); server.close();
