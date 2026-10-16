// 功能總檢查:像使用者一樣把每個功能按一遍,逐項檢查狀態對不對、有沒有錯誤訊息。
// node feature_check.mjs   (用 samples/ 的範例樂譜;音色檔照常載入)
import { chromium } from "playwright";
import http from "node:http"; import fs from "node:fs"; import path from "node:path";
const ROOT = path.resolve(path.join(path.dirname(new URL(import.meta.url).pathname), "../.."));
const server = http.createServer((req, res) => { const p = path.join(ROOT, decodeURIComponent(req.url.split("?")[0])); if (!fs.existsSync(p) || fs.statSync(p).isDirectory()) { res.writeHead(404); return res.end(); } res.writeHead(200); fs.createReadStream(p).pipe(res); });
await new Promise(r => server.listen(0, "127.0.0.1", r));
const URL0 = `http://127.0.0.1:${server.address().port}/index.html`;
const browser = await chromium.launch({ args: ["--autoplay-policy=no-user-gesture-required"] });
const results = [];
const check = (name, ok, info = "") => { results.push({ name, ok: !!ok, info }); console.log((ok ? "✓ " : "✗ ") + name + (info ? "  " + info : "")); };
const page = await browser.newPage({ viewport: { width: 1280, height: 800 } });
await page.route(/raw\.githubusercontent\.com|fonts\.g/, r => r.abort());
const errs = [];
page.on("pageerror", e => errs.push(e.message));
page.on("console", m => { if (m.type() === "error" && !/ERR_FAILED|Wake Lock|wakeLock|status of 404/.test(m.text())) errs.push(m.text()); });
const wait = ms => page.waitForTimeout(ms);
await page.goto(URL0);
await page.evaluate(() => { try { localStorage.clear(); } catch (e) {} });
await page.reload();
await page.waitForFunction(() => typeof events !== "undefined");

// 1. 範例樂譜(小星星內建、歡樂頌、搖滾鼓)
await page.click("#trySampleBtn");
await page.waitForFunction(() => events.length > 0, null, { timeout: 60000 });
check("小星星範例載入", await page.evaluate(() => events.length > 10 && document.body.classList.contains("score-loaded")));
await page.evaluate(() => { stopPlayback(); });
await page.evaluate(() => document.querySelector('[data-sample="ode-to-joy"]') && null);
await page.setInputFiles("#fileInput", path.join(ROOT, "samples/ode-to-joy.musicxml"));
await page.waitForFunction(() => events.length > 0 && $("score").querySelector("svg"), null, { timeout: 60000 });
await wait(800);
const tot = await page.evaluate(() => totalSec());
check("歡樂頌載入", tot > 20, "長度 " + tot.toFixed(1) + " 秒");

// 2. 頂欄按鈕
const hdr = await page.evaluate(() => ["loadBtn", "playBtn", "stopBtn", "themeToggle", "langToggle", "exportHdrBtn", "settingsToggle"].map(id => { const r = $(id).getBoundingClientRect(); return id + ":" + (r.width > 0 && r.top < 80 ? "ok" : "hidden"); }).join(" "));
check("頂欄 7 顆按鈕都在第一排", !hdr.includes("hidden"), hdr);
check("頂欄沒有速度按鈕、沒有錄影模式", await page.evaluate(() => !document.getElementById("tempoToggle") && !document.getElementById("recBtn")));

// 3. 播放 / 暫停 / 從頭
await page.evaluate(() => ensureAudio());
await page.evaluate(async () => { await loadInstrumentSamples("piano"); });
await page.click("#playBtn"); await wait(2500);
const p1 = await page.evaluate(() => ({ playing, sec: currentSec(), x: lastScrollX }));
check("播放", p1.playing && p1.sec > 1, "播到 " + p1.sec.toFixed(2) + " 秒");
await page.click("#playBtn"); await wait(300);
const p2 = await page.evaluate(() => ({ playing, paused: pausedAtSec }));
check("暫停", !p2.playing && p2.paused > 1);
await page.click("#stopBtn"); await wait(300);
check("從頭", await page.evaluate(() => !playing && pausedAtSec === 0));

// 4. 跳轉(進度條、時間輸入)
await page.evaluate(() => seekTo(10)); await wait(200);
check("進度條跳轉", await page.evaluate(() => Math.abs(pausedAtSec - 10) < 0.01));
await page.evaluate(() => openSeekPopover()); await page.fill("#seekInput", "0:05"); await page.click("#seekGoBtn"); await wait(200);
check("輸入時間跳轉", await page.evaluate(() => Math.abs(pausedAtSec - 5) < 0.05), await page.evaluate(() => pausedAtSec.toFixed(2)));

// 5. 設定面板:速度、移調、開關、色票、背景圖
await page.click("#settingsToggle"); await wait(400);
check("設定面板打開", await page.evaluate(() => $("settingsPanel").classList.contains("open")));
const sec0 = await page.evaluate(() => totalSec());
await page.fill("#tempoVal", "60"); await page.dispatchEvent("#tempoVal", "change"); await wait(200);
const sec1 = await page.evaluate(() => ({ t: totalSec(), raw: rawTempo(), slider: $("tempo").value }));
check("速度改 60(滑桿、數字同步,曲長變長)", sec1.raw === 60 && sec1.slider === "60" && sec1.t > sec0 * 1.3, sec0.toFixed(1) + " → " + sec1.t.toFixed(1) + " 秒");
await page.evaluate(() => { $("tempo").value = 120; $("tempo").dispatchEvent(new Event("input")); }); await wait(200);
check("速度滑桿 120", await page.evaluate(() => rawTempo() === 120 && $("tempoVal").value === "120"));
const pitch0 = await page.evaluate(() => Math.round(freqToMidi(events.find(e => e.notes.length).notes[0].freq)));
await page.click("#transUp"); await page.waitForTimeout(1500);
const pitch1 = await page.evaluate(() => Math.round(freqToMidi(events.find(e => e.notes.length).notes[0].freq)));
check("移調 +1", pitch1 === pitch0 + 1 && (await page.textContent("#transVal")).includes("1"), pitch0 + " → " + pitch1);
await page.click("#transDown"); await page.waitForTimeout(1500);
for (const id of ["countIn", "measureHl", "showTempoMarks", "mergeRestMeasures", "showPedalMarks", "rubatoOn"]) {
  const before = await page.evaluate(id => $(id).checked, id);
  await page.evaluate(id => $(id).closest("label").click(), id); await wait(id === "countIn" || id === "measureHl" || id === "rubatoOn" ? 200 : 1500);
  const after = await page.evaluate(id => $(id).checked, id);
  await page.evaluate(id => $(id).closest("label").click(), id); await wait(id === "countIn" || id === "measureHl" || id === "rubatoOn" ? 200 : 1500);
  const back = await page.evaluate(id => $(id).checked, id);
  check("開關 " + id + " 可切換", after === !before && back === before);
}
check("開關預設:小節高亮開、踏板記號關、彈性速度開", await page.evaluate(() => $("measureHl").checked && !$("showPedalMarks").checked && $("rubatoOn").checked));
await page.click('#cursorColorRow .swatch[data-color="#F2877A"]'); await wait(100);
check("色票換紅色", await page.evaluate(() => getComputedStyle(document.documentElement).getPropertyValue("--cursor-col").trim() === "#F2877A"));
await page.click('#cursorColorRow .swatch[data-color="#E9CB7A"]');
check("沒有空間感、游標濃度滑桿", await page.evaluate(() => !$("reverbAmount") && !$("cursorOpacity")));
await page.evaluate(() => document.querySelectorAll("#settingsPanel details").forEach(d => d.open = true));
await page.setInputFiles("#bgImageFile", path.join(ROOT, "app/assets/logo-original.png")); await wait(1200);
check("背景圖匯入(背景濃度出現且自動設好)", await page.evaluate(() => !!customBgImage && !$("bgOpacityRow").hidden && +$("scoreBgOpacity").value > 0));
await page.click("#bgImageClearBtn"); await wait(200);
check("背景圖移除", await page.evaluate(() => !customBgImage && $("bgOpacityRow").hidden));
await page.evaluate(() => closeSettingsSheet());

// 6. 主題、語言
await page.click("#themeToggle"); await wait(200);
check("淺色模式", await page.evaluate(() => document.body.classList.contains("light")));
await page.click("#themeToggle"); await wait(200);
await page.click("#langToggle"); await wait(300);
check("切英文", await page.evaluate(() => $("playLabel").textContent.trim() === "Play" || document.documentElement.lang.startsWith("en")), await page.textContent("#playLabel"));
await page.click("#langToggle"); await wait(300);
check("切回中文", (await page.textContent("#playLabel")).includes("播放"));

// 7. 重新整理後設定還在
await page.evaluate(() => { $("tempoVal").value = 90; $("tempoVal").dispatchEvent(new Event("change")); $("cursorColor").value = "#7DB9F2"; $("cursorColor").dispatchEvent(new Event("input")); });
await page.evaluate(() => { $("countIn").closest("label").click(); });
await page.reload(); await page.waitForFunction(() => typeof events !== "undefined");
await wait(400);
check("重新整理後記住色票、預備拍", await page.evaluate(() => hlCursorColor() === "#7DB9F2" && $("countIn").checked));
await page.evaluate(() => { $("countIn").checked = false; $("countIn").dispatchEvent(new Event("change")); });

// 8. 鼓譜
await page.selectOption("#instrument", "drum");
await page.setInputFiles("#fileInput", path.join(ROOT, "samples/drums-rock.musicxml"));
await page.waitForFunction(() => events.length > 0 && isDrumScore, null, { timeout: 60000 });
await page.evaluate(async () => { ensureAudio(); await loadDrumKit(); });
await page.click("#playBtn"); await wait(2000);
check("鼓譜播放", await page.evaluate(() => playing && currentSec() > 0.8));
await page.click("#stopBtn");
check("鼓組面板沒有多餘黑邊", await page.evaluate(() => { const r = $("keyboardCanvas").getBoundingClientRect(); return r.height <= drumKitNaturalH(r.width) + 1; }));

// 9. 匯出頁面:格式、記住選擇、直式鋼琴不顯示鍵盤選項
await page.selectOption("#instrument", "piano");
await page.setInputFiles("#fileInput", path.join(ROOT, "samples/ode-to-joy.musicxml"));
await page.waitForFunction(() => events.length > 0 && !isDrumScore, null, { timeout: 60000 });
await wait(500);
await page.click("#exportHdrBtn"); await wait(300);
check("頂欄匯出按鈕打開匯出頁", await page.evaluate(() => $("formatOverlay").classList.contains("show")));
for (const f of ["portrait", "square", "landscape"]) {
  await page.click(`#expFormatSeg button[data-v="${f}"]`);
  const want0 = { portrait: [1080, 1920], square: [1080, 1080], landscape: [1920, 1080] }[f];
  // 預覽是改選項 180ms 後才開始畫,等到畫出對的尺寸(最多 60 秒)
  await page.waitForFunction(w => { const im = $("previewImg"); return !im.parentElement.classList.contains("busy") && im.naturalWidth === w[0] && im.naturalHeight === w[1]; }, want0, { timeout: 60000 }).catch(() => {});
  const info = await page.evaluate(() => { const im = $("previewImg"); return { w: im.naturalWidth, h: im.naturalHeight, panelRow: !$("expPanelRow").hidden && getComputedStyle($("expPanelRow")).display !== "none" }; });
  const want = { portrait: [1080, 1920], square: [1080, 1080], landscape: [1920, 1080] }[f];
  check("預覽 " + f, info.w === want[0] && info.h === want[1] && (f === "portrait" ? !info.panelRow : info.panelRow), JSON.stringify(info));
}
await page.click(`#expFormatSeg button[data-v="square"]`); await page.click("#fmtCancel");
await page.reload(); await page.waitForFunction(() => typeof exportPrefs !== "undefined");
check("匯出格式記住(方形)", await page.evaluate(() => exportPrefs.format === "square"));

// 10. 用 alphaTab 把歡樂頌轉成 Guitar Pro 7 檔,再用 App 匯入(Guitar Pro 匯入流程)
const gpOk = await page.evaluate(async () => {
  try {
    const AT = await loadAlphaTab();
    const xml = await (await fetch("samples/ode-to-joy.musicxml")).text();
    const settings = new AT.Settings();
    const score = AT.importer.ScoreLoader.loadScoreFromBytes(new TextEncoder().encode(xml.replace(/\{\{TITLE\}\}/g, "Ode")), settings);
    const bytes = new AT.exporter.Gp7Exporter().export(score, settings);
    const file = new File([bytes], "ode.gp", { type: "application/octet-stream" });
    const dt = new DataTransfer(); dt.items.add(file);
    $("fileInput").files = dt.files; $("fileInput").dispatchEvent(new Event("change"));
    for (let i = 0; i < 300 && !(events.length && lastXmlText && lastXmlText.includes("Ode")); i++) await new Promise(r => setTimeout(r, 100));
    return events.length > 10 ? "ok " + events.length + " events" : "no events";
  } catch (e) { return "error " + e.message; }
});
check("Guitar Pro 檔匯入", gpOk.startsWith("ok"), gpOk);

check("全程沒有錯誤訊息", errs.length === 0, errs.slice(0, 5).join(" | "));
const bad = results.filter(r => !r.ok);
console.log(bad.length ? `\n${bad.length} 項沒通過` : `\n全部 ${results.length} 項通過`);
await browser.close(); server.close();
