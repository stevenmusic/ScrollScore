// MP4 封裝檢查(2026-10,iPhone Safari 快速匯出「track.info.decoderConfig is null」):用 ffmpeg 做一段真的 H.264(Annex B,含 AUD)+ AAC,
// 照 Safari / Chrome 可能的四種輸出(Annex B 沒 meta、meta 沒 description、長度前綴 + description、長度前綴 + 參數組在位元流)
// 餵給 App 的 muxVideoChunkFn / muxAudioChunkFn,輸出的 MP4 用 ffmpeg 解碼,畫面要跟原始串流逐位元相同。
// node mux_check.mjs [暫存目錄]
import { chromium } from "playwright";
import http from "node:http"; import fs from "node:fs"; import path from "node:path"; import os from "node:os"; import { execFileSync } from "node:child_process";
const ROOT = path.resolve(path.join(path.dirname(new URL(import.meta.url).pathname), "../.."));
const D = process.argv[2] || fs.mkdtempSync(path.join(os.tmpdir(), "muxcheck-"));
execFileSync("ffmpeg", ["-v", "error", "-y", "-f", "lavfi", "-i", "testsrc=size=1920x1080:rate=30", "-t", "4", "-c:v", "libx264", "-profile:v", "high", "-bf", "0", "-x264-params", "aud=1:keyint=60", "-pix_fmt", "yuv420p", "-f", "h264", D + "/v.h264"]);
execFileSync("ffmpeg", ["-v", "error", "-y", "-f", "lavfi", "-i", "sine=f=440:r=48000", "-ac", "2", "-t", "4", "-c:a", "aac", "-b:a", "192k", "-f", "adts", D + "/a.aac"]);
const server = http.createServer((req, res) => { const p = path.join(ROOT, decodeURIComponent(req.url.split("?")[0])); if (!fs.existsSync(p) || fs.statSync(p).isDirectory()) { res.writeHead(404); return res.end(); } res.writeHead(200); fs.createReadStream(p).pipe(res); });
await new Promise(r => server.listen(0, "127.0.0.1", r));
const browser = await chromium.launch(); const page = await browser.newPage();
await page.route(/raw\.githubusercontent\.com|fonts\.g/, r => r.abort());
const errs = []; page.on("pageerror", e => errs.push(e.message));
await page.goto(`http://127.0.0.1:${server.address().port}/index.html`);
await page.waitForFunction(() => typeof muxVideoChunkFn === "function");
const v = fs.readFileSync(D + "/v.h264").toString("base64"), a = fs.readFileSync(D + "/a.aac").toString("base64");
for (const mode of ["annexb-nometa", "annexb-meta-nodesc", "avcc-desc", "avcc-nodesc-inband"]) {
  const out = await page.evaluate(async ({ v, a, mode }) => {
    const b = s => Uint8Array.from(atob(s), c => c.charCodeAt(0));
    const vb = b(v), ab = b(a);
    // AUD(00 00 00 01 09)切成一格一格
    const aus = []; let last = -1;
    for (let i = 0; i + 4 < vb.length; i++) if (vb[i] === 0 && vb[i+1] === 0 && vb[i+2] === 0 && vb[i+3] === 1 && (vb[i+4] & 31) === 9) { if (last >= 0) aus.push(vb.subarray(last, i)); last = i; }
    aus.push(vb.subarray(last));
    const Muxer = await loadMuxer("mp4");
    const target = new Muxer.ArrayBufferTarget();
    const muxer = new Muxer.Muxer({ target, video: { codec: "avc", width: 1920, height: 1080, frameRate: 30 }, audio: { codec: "aac", numberOfChannels: 2, sampleRate: 48000 }, fastStart: "in-memory", firstTimestampBehavior: "offset" });
    const fmtSel = { container: "mp4", muxV: "avc", vCodec: "avc1.640028" };
    const onV = muxVideoChunkFn(muxer, fmtSel, 1920, 1080, 30), onA = muxAudioChunkFn(muxer, fmtSel, 48000);
    const fake = (u8, type, ts, dur) => ({ byteLength: u8.length, copyTo(d){ d.set(u8); }, type, timestamp: ts, duration: dur });
    // AVCC 模式先用 packer 轉好(模擬 Chrome:資料已經是長度前綴、description 在 meta)
    const pk = makeH264Packer(); const conv = aus.map(au => pk(au));
    const desc = conv.find(c => c.desc).desc;
    aus.forEach((au, i) => {
      const key = au.some((_, j) => j + 4 < au.length && au[j] === 0 && au[j+1] === 0 && au[j+2] === 1 && (au[j+3] & 31) === 5);
      const ts = Math.round(i * 1e6 / 30);
      if (mode === "annexb-nometa") onV(fake(au, key ? "key" : "delta", ts, null), undefined);
      else if (mode === "annexb-meta-nodesc") onV(fake(au, key ? "key" : "delta", ts, 33333), i === 0 ? { decoderConfig: { codec: "avc1.640028" } } : {});
      else if (mode === "avcc-desc") onV(fake(conv[i].data, key ? "key" : "delta", ts, 33333), i === 0 ? { decoderConfig: { codec: "avc1.640028", description: desc, colorSpace: { primaries: "bt709", transfer: "bt709", matrix: "bt709", fullRange: false } } } : undefined);
      else { // 長度前綴、SPS/PPS 在位元流裡(把 annexb 每個 NAL 改成長度前綴,不拿掉參數組)
        const nals = h264SplitNals(au); let sz = 0; nals.forEach(n => sz += 4 + n.length); const d = new Uint8Array(sz); let o = 0;
        nals.forEach(n => { new DataView(d.buffer).setUint32(o, n.length); d.set(n, o + 4); o += 4 + n.length; });
        onV(fake(d, key ? "key" : "delta", ts, null), undefined);
      }
    });
    // ADTS → 原始 AAC 幀
    let i = 0, k = 0;
    while (i + 7 < ab.length) { const len = ((ab[i+3] & 3) << 11) | (ab[i+4] << 3) | (ab[i+5] >> 5); const hl = (ab[i+1] & 1) ? 7 : 9; onA(fake(ab.subarray(i + hl, i + len), "key", Math.round(k * 1024 / 48000 * 1e6), null), undefined); i += len; k++; }
    muxer.finalize();
    let s = ""; const u = new Uint8Array(target.buffer); for (let j = 0; j < u.length; j += 0x8000) s += String.fromCharCode.apply(null, u.subarray(j, j + 0x8000));
    return { aus: aus.length, mp4: btoa(s) };
  }, { v, a, mode });
  fs.writeFileSync(`${D}/${mode}.mp4`, Buffer.from(out.mp4, "base64"));
  console.log(mode, "frames in", out.aus);
}
await browser.close(); server.close();
const md5 = f => execFileSync("ffmpeg", ["-v", "error", "-i", f, "-map", "0:v", "-f", "md5", "-"]).toString().trim();
const ref = md5(D + "/v.h264"); let bad = errs.length;
for (const mode of ["annexb-nometa", "annexb-meta-nodesc", "avcc-desc", "avcc-nodesc-inband"]) {
  const f = `${D}/${mode}.mp4`, got = md5(f);
  const info = execFileSync("ffprobe", ["-v", "error", "-count_frames", "-show_entries", "stream=codec_name,nb_read_frames", "-of", "csv=p=0", f]).toString().trim().replace(/\n/g, " ");
  const ok = got === ref; if (!ok) bad++;
  console.log(ok ? "✓" : "✗", mode, info, ok ? "畫面逐位元相同" : "畫面不同");
}
if (errs.length) console.log("錯誤:", errs.join(" | "));
process.exit(bad ? 1 : 0);
