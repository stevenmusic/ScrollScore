// 大譜表上下兩行的間距(譜線間距為單位,下一行頂線到上一行底線):node staff_gap.mjs <樂譜...>
// base = App 現在的排版;slurs = 不畫圓滑線時(看圓滑線撐開多少)。一般樂譜約 6~10 格
import { chromium } from "playwright";
import http from "node:http"; import fs from "node:fs"; import path from "node:path";
const ROOT = "/home/user/ScrollScore";
const server = http.createServer((req, res) => { const p = path.join(ROOT, decodeURIComponent(req.url.split("?")[0])); if (!fs.existsSync(p) || fs.statSync(p).isDirectory()) { res.writeHead(404); return res.end(); } res.writeHead(200); fs.createReadStream(p).pipe(res); });
await new Promise(r => server.listen(0, "127.0.0.1", r));
const browser = await chromium.launch();
for (const score of process.argv.slice(2)) {
  const page = await browser.newPage({ viewport: { width: 1400, height: 900 } });
  await page.route(/raw\.githubusercontent\.com|\.flac|fonts\.g|jsdelivr/, r => r.abort());
  await page.goto(`http://127.0.0.1:${server.address().port}/index.html`);
  await page.waitForFunction(() => typeof loadScoreFile === "function");
  await page.setInputFiles("#fileInput", path.resolve(score));
  await page.waitForFunction(() => typeof events !== "undefined" && events.length > 0, null, { timeout: 120000 });
  await page.waitForTimeout(800);
  const r = await page.evaluate(() => {
    const gap = () => { const L = osmd.GraphicSheet.MusicPages[0].MusicSystems[0].StaffLines; return +(L[1].PositionAndShape.RelativePosition.y - L[0].PositionAndShape.RelativePosition.y - 4).toFixed(1); };
    const R = osmd.EngravingRules, out = { base: gap() };
    const tries = { slurs: ["RenderSlurs", false] };
    for (const [k, [rule, v]] of Object.entries(tries)) { const o = R[rule]; R[rule] = v; osmd.render(); out[k] = gap(); R[rule] = o; }
    // 全部關掉
    return out;
  });
  console.log(path.basename(path.dirname(path.dirname(score))) + "/" + path.basename(path.dirname(score)), JSON.stringify(r));
  await page.close();
}
await browser.close(); server.close();
