// 母帶限幅器單元測試:把 index.html 裡的 MASTER_LIMITER_SRC 拿出來在 node 裡跑,輸出 WAV 給 limiter_tp.py 量真峰值
import fs from "node:fs"; import path from "node:path";
const html = fs.readFileSync(path.join(path.dirname(new URL(import.meta.url).pathname), "../../index.html"), "utf8");
const src = html.match(/const MASTER_LIMITER_SRC = `([\s\S]*?)`;/)[1];
const SR = +(process.argv[3] || 48000);
let seed = 12345; const rnd = () => { seed = (seed * 1103515245 + 12345) >>> 0; return seed / 4294967296; };   // 固定種子,每次測一樣的訊號
let Proc; globalThis.sampleRate = SR; globalThis.AudioWorkletProcessor = class { constructor() { this.port = { postMessage() {}, onmessage: null }; } };
globalThis.registerProcessor = (n, c) => { Proc = c; };
eval(process.env.DOFF ? src.replace("this.D = this.L + 8", "this.D = this.L + " + process.env.DOFF) : src);
const sig = [];
const add = (fn, sec) => { for (let i = 0; i < sec * SR; i++) sig.push(fn(i / SR)); };
for (const f of [100, 1000, 5000, 10000, 15000, 18000, 20000]) add(t => [2 * Math.sin(2 * Math.PI * f * t + 0.3), 2 * Math.sin(2 * Math.PI * f * t + 0.3)], 0.5);
add(t => [0, 0], 0.2);
add(t => (Math.floor(t * SR) % 4800 === 0 ? [30, -30] : [0.1 * Math.sin(2 * Math.PI * 220 * t), 0.1 * Math.sin(2 * Math.PI * 220 * t)]), 1);   // 突發衝擊
add(t => [0.9 * Math.sin(2 * Math.PI * 60 * t) + 1.2 * (rnd() * 2 - 1) * (t % 0.25 < 0.01), 0.5 * Math.sin(2 * Math.PI * 60 * t)], 1);
add(t => [NaN, 0], 0.01); add(t => [0, 0], 0.5);
const p = new Proc({ processorOptions: { ceilingDb: -1.3, lookahead: 0.005, release: 0.09, releaseSlow: 0.7 } });
const outL = new Float32Array(sig.length), outR = new Float32Array(sig.length);
for (let o = 0; o + 128 <= sig.length; o += 128) {
  const iL = new Float32Array(128), iR = new Float32Array(128);
  for (let i = 0; i < 128; i++) { iL[i] = sig[o + i][0]; iR[i] = sig[o + i][1]; }
  const oL = new Float32Array(128), oR = new Float32Array(128);
  p.process([[iL, iR]], [[oL, oR]]);
  outL.set(oL, o); outR.set(oR, o);
}
const n = sig.length, hdr = Buffer.alloc(44);
hdr.write("RIFF", 0); hdr.writeUInt32LE(36 + n * 8, 4); hdr.write("WAVEfmt ", 8); hdr.writeUInt32LE(16, 16); hdr.writeUInt16LE(3, 20); hdr.writeUInt16LE(2, 22);
hdr.writeUInt32LE(SR, 24); hdr.writeUInt32LE(SR * 8, 28); hdr.writeUInt16LE(8, 32); hdr.writeUInt16LE(32, 34); hdr.write("data", 36); hdr.writeUInt32LE(n * 8, 40);
const b = Buffer.alloc(n * 8); for (let i = 0; i < n; i++) { b.writeFloatLE(outL[i], i * 8); b.writeFloatLE(outR[i], i * 8 + 4); }
fs.writeFileSync(process.argv[2], Buffer.concat([hdr, b]));
