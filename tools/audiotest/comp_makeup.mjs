// 量 DynamicsCompressor 的自動補增益(PIANO_MASTER.*.makeupDb 用):100Hz 小訊號通過同參數壓縮器的增益 dB。node comp_makeup.mjs (JSON 參數)…
import { chromium } from "playwright";
const b = await chromium.launch(); const p = await b.newPage();
for (const a of process.argv.slice(2)) {
  const r = await p.evaluate(async L => {
    const ctx = new OfflineAudioContext(1, 48000, 48000);
    const o = ctx.createOscillator(); o.frequency.value = 100; const g = ctx.createGain(); g.gain.value = 1e-4;
    const c = ctx.createDynamicsCompressor(); c.threshold.value = L.threshold; c.knee.value = L.knee; c.ratio.value = L.ratio; c.attack.value = L.attack; c.release.value = L.release;
    o.connect(g); g.connect(c); c.connect(ctx.destination); o.start(); const buf = await ctx.startRendering(); const d = buf.getChannelData(0);
    let s = 0, n = 0; for (let i = 24000; i < 48000; i++) { s += d[i] * d[i]; n++; } return 20 * Math.log10(Math.sqrt(s / n) / (1e-4 / Math.SQRT2));
  }, JSON.parse(a));
  console.log(a, "->", r.toFixed(2), "dB");
}
await b.close();
