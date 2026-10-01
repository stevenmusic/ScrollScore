import { chromium } from '/opt/node22/lib/node_modules/playwright/index.mjs';
import fs from 'fs';
const SP = process.cwd();
const b = await chromium.launch();
const FONTCSS = `@font-face{font-family:'Noto Serif TC';font-weight:200 900;src:url(http://localhost:8767/video/fonts/NotoSerifTC.ttf)}@font-face{font-family:'Noto Sans TC';font-weight:100 900;src:url(http://localhost:8767/video/fonts/NotoSansTC.ttf)}`;
async function make(score, inst, out, dims, title, subtitle, sec, kb) {
  const p = await b.newPage({ viewport: { width: 1280, height: 720 } });
  await p.route('**/*', r => { const u = r.request().url();
    if (u.includes('opensheetmusicdisplay.min.js')) return r.fulfill({ path: SP+'/npm/opensheetmusicdisplay-2.0.0/build/opensheetmusicdisplay.min.js' });
    if (u.includes('jszip.min.js')) return r.fulfill({ path: SP+'/npm/jszip-3.10.1/dist/jszip.min.js' });
    if (u.includes('fonts.googleapis')) return r.fulfill({ status: 200, contentType: 'text/css', body: FONTCSS });
    if (u.startsWith('http://localhost')) return r.continue();
    return r.fulfill({ status: 404, body: '' }); });
  await p.goto('http://localhost:8767/app/index.html');
  await p.selectOption('#instrument', inst);
  await p.setInputFiles('#fileInput', SP + '/' + score);
  await p.waitForFunction(() => document.querySelector('#score svg'), null, { timeout: 30000 });
  const png = await p.evaluate(async ([d, title, subtitle, sec, kb]) => {
    await showExportPreview(Object.assign({ align: 'center', bitrate: 5e6, fps: 30, includeKeyboard: kb, startSec: sec, endSec: null }, d, { watermarkEnabled: true, title, subtitle, channel: 'Steven Music' }));
    return $("previewImg").src;
  }, [dims, title, subtitle, sec, kb]);
  fs.writeFileSync(out, Buffer.from(png.split(',')[1], 'base64')); await p.close(); console.log(out);
}
await make('mozart_k545_movement1_exposition.mxl', 'piano', 'vid_export_16x9.png', { W: 1920, H: 1080, scoreH: 440 }, 'Sonata in C, K.545', 'W. A. Mozart', 7, true);
await make('groove_dyn.musicxml', 'drum', 'vid_export_9x16.png', { W: 1080, H: 1920, scoreH: 380 }, 'Groove Study', 'Drum Set', 3, true);
await make('bach_bwv846.mxl', 'piano', 'vid_export_1x1.png', { W: 1080, H: 1080, scoreH: 400 }, 'Prelude in C, BWV 846', 'J. S. Bach', 10, false);
await b.close();
