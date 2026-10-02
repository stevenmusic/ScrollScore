// Render the promo: node render.mjs <mode> ...
//   still <t1,t2,...> <dsf>      -> stills/still_<t>.png
//   seg <f0> <f1> <out.mp4>      -> frames [f0,f1) at 30 fps, 3840x2160, H.264
import { chromium } from '/opt/node22/lib/node_modules/playwright/index.mjs';
import { spawn } from 'child_process';
import fs from 'fs';
const SP = process.env.SP || '/tmp/claude-0/-home-user-ScrollScore/a858f8bd-7d7a-58c3-a5fa-1f0f8dc246d8/scratchpad';   // 暫存資料夾(放 npm/、樂譜、stills/),可用環境變數 SP 指定
const FF = process.env.FF || 'ffmpeg';   // ffmpeg 路徑,可用環境變數 FF 指定
const FPS = 30;
const [mode, a1, a2, a3] = process.argv.slice(2);
const dsf = mode === 'still' ? +(a2 || 1) : 2;
const FONTCSS = `@font-face{font-family:'Noto Serif TC';font-weight:200 900;src:url(http://localhost:8767/video/fonts/NotoSerifTC.ttf)}@font-face{font-family:'Noto Sans TC';font-weight:100 900;src:url(http://localhost:8767/video/fonts/NotoSansTC.ttf)}`;
const b = await chromium.launch({ args: ['--autoplay-policy=no-user-gesture-required'] });
const ctx = await b.newContext({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: dsf });
await ctx.route('**/*', r => {
  const u = r.request().url();
  if (u.includes('opensheetmusicdisplay.min.js')) return r.fulfill({ path: SP + '/npm/opensheetmusicdisplay-2.0.0/build/opensheetmusicdisplay.min.js' });
  if (u.includes('jszip.min.js')) return r.fulfill({ path: SP + '/npm/jszip-3.10.1/dist/jszip.min.js' });
  if (u.includes('fonts.googleapis')) return r.fulfill({ status: 200, contentType: 'text/css', body: FONTCSS });
  if (/\/app\/(piano|drums)\/.*\.flac$/.test(u)) return r.fulfill({ status: 404, body: '' });   // visuals only, no audio decoding
  if (u.startsWith('http://localhost')) return r.continue();
  return r.fulfill({ status: 404, body: '' });
});
const page = await ctx.newPage();
page.on('pageerror', e => console.error('pageerror', e.message));
await page.goto('http://localhost:8767/video/comp.html');
await page.waitForFunction(() => window.COMP_READY && document.fonts.status === 'loaded', null, { timeout: 60000 });
const SETUP = {
  empty: null,
  main: ['piano', 'mozart_k545_movement1_exposition.mxl'], main2: ['piano', 'mozart_k545_movement1_exposition.mxl'], main3: ['piano', 'mozart_k545_movement1_exposition.mxl'],
  custom: ['piano', 'mozart_k545_movement1_exposition.mxl'], phone: ['piano', 'mozart_k545_movement1_exposition.mxl'],
  drum: ['drum', 'groove_dyn2.musicxml'],
};
for (const [key, cfg] of Object.entries(SETUP)) {
  let fr = null;
  for (let i = 0; i < 200 && !fr; i++) { fr = page.frames().find(f => f.url().includes('f=' + key)); if (!fr) await page.waitForTimeout(100); }
  await fr.waitForFunction(() => typeof seekTo === 'function' && document.getElementById('fileInput'), null, { timeout: 60000 });
  await fr.addStyleTag({ content: '*,*::before,*::after{transition:none!important;animation:none!important;caret-color:transparent!important}' });
  if (cfg) {
    await fr.selectOption('#instrument', cfg[0]);
    await fr.setInputFiles('#fileInput', SP + '/' + cfg[1]);
    await fr.waitForFunction(() => document.querySelector('#score svg') && events.length, null, { timeout: 60000 });
  }
}
await page.waitForTimeout(4000);   // let sample loaders give up quietly
for (const [key, cfg] of Object.entries(SETUP)) {
  const fr = page.frames().find(f => f.url().includes('f=' + key));
  await fr.evaluate((inst) => {
    const st = document.getElementById('status');
    if (st && inst) st.textContent = inst === 'drum' ? '鼓音色就緒' : '鋼琴音色就緒(16 層力度)';
    if (st && !inst) st.textContent = '尚未載入樂譜';
  }, cfg && cfg[0]);
}
const total = await page.evaluate(() => window.TOTAL);
console.error('TOTAL', total.toFixed(2), 's =', Math.round(total * FPS), 'frames');
if (mode === 'still') {
  fs.mkdirSync(SP + '/video/stills', { recursive: true });
  for (const t of a1.split(',').map(Number)) {
    await page.evaluate(t => window.setTime(t), t);
    await page.waitForTimeout(60);
    await page.screenshot({ path: `${SP}/video/stills/still_${t.toFixed(2)}.png` });
    console.error('still', t);
  }
} else if (mode === 'seg') {
  const f0 = +a1, f1 = Math.min(+a2, Math.round(total * FPS));
  const ff = spawn(FF, ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-c:v', 'mjpeg', '-framerate', String(FPS), '-i', '-', '-c:v', 'libx264', '-preset', 'medium', '-crf', '16', '-pix_fmt', 'yuv420p', '-r', String(FPS), a3], { stdio: ['pipe', 'inherit', 'inherit'] });
  const t0 = Date.now();
  for (let f = f0; f < f1; f++) {
    await page.evaluate(t => window.setTime(t), f / FPS);
    const buf = await page.screenshot({ type: 'jpeg', quality: 94 });
    if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
    if ((f - f0) % 60 === 0) console.error(`seg ${a3.split('/').pop()} frame ${f}/${f1} ${((Date.now() - t0) / 1000 / Math.max(1, f - f0 + 1)).toFixed(2)} s/frame`);
  }
  ff.stdin.end(); await new Promise(r => ff.on('close', r));
}
await b.close();
