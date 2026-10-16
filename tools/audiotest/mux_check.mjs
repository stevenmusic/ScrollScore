// MP4 封裝檢查(2026-10,iPhone Safari 快速匯出「track.info.decoderConfig is null」):用 ffmpeg 做真的 H.264 + AAC,
// 照 Safari / Chrome 可能的四種輸出餵給 App 的 muxVideoChunkFn / muxAudioChunkFn,封裝跟 App 一樣用 StreamTarget 分塊 + makeChunkCollector,
// 輸出的 MP4 用 ffmpeg 解碼:畫面要跟原始串流逐位元相同,聲音要解得出來、長度對。
//   四種:annexb-nometa(Annex B、沒 decoderConfig = iPhone 實測)、annexb-meta-nodesc(有 decoderConfig 沒 description)、
//         avcc-desc(長度前綴 + description = Chrome 標準)、avcc-nodesc-inband(長度前綴、參數組在位元流裡)、
//         ignored-avcc-desc / ignored-avcc-inband(要求 Annex B 但瀏覽器忽略、照樣給長度前綴)
//   兩種來源:testsrc(每格開頭有 AUD,NAL 都很大)、靜態畫面 + 小方塊(沒有 AUD,很多 256~511 位元組的小 P 格:
//   長度前綴開頭剛好是 00 00 01,以前從資料猜格式會弄壞,審查發現)
// node mux_check.mjs [暫存目錄]
import { chromium } from "playwright";
import http from "node:http"; import fs from "node:fs"; import path from "node:path"; import os from "node:os"; import { execFileSync } from "node:child_process";
const ROOT = path.resolve(path.join(path.dirname(new URL(import.meta.url).pathname), "../.."));
const D = process.argv[2] || fs.mkdtempSync(path.join(os.tmpdir(), "muxcheck-"));
const SOURCES = {
  testsrc: ["testsrc=size=1920x1080:rate=30", "aud=1:keyint=60"],
  static: ["color=c=white:size=1920x1080:rate=30,drawbox=x=t*40:y=500:w=40:h=40:c=black:t=fill", "keyint=60"],
};
for (const [name, [src, x264]] of Object.entries(SOURCES))
  execFileSync("ffmpeg", ["-v", "error", "-y", "-f", "lavfi", "-i", src, "-t", "4", "-c:v", "libx264", "-profile:v", "high", "-bf", "0", "-x264-params", x264, "-pix_fmt", "yuv420p", "-f", "h264", `${D}/${name}.h264`]);
execFileSync("ffmpeg", ["-v", "error", "-y", "-f", "lavfi", "-i", "sine=f=440:r=48000", "-ac", "2", "-t", "4", "-c:a", "aac", "-b:a", "192k", "-f", "adts", D + "/a.aac"]);
const server = http.createServer((req, res) => { const p = path.join(ROOT, decodeURIComponent(req.url.split("?")[0])); if (!fs.existsSync(p) || fs.statSync(p).isDirectory()) { res.writeHead(404); return res.end(); } res.writeHead(200); fs.createReadStream(p).pipe(res); });
await new Promise(r => server.listen(0, "127.0.0.1", r));
const browser = await chromium.launch(); const page = await browser.newPage();
await page.route(/raw\.githubusercontent\.com|fonts\.g/, r => r.abort());
const errs = []; page.on("pageerror", e => errs.push(e.message));
await page.goto(`http://127.0.0.1:${server.address().port}/index.html`);
await page.waitForFunction(() => typeof muxVideoChunkFn === "function");
const a = fs.readFileSync(D + "/a.aac").toString("base64");
const MODES = ["annexb-nometa", "annexb-meta-nodesc", "avcc-desc", "avcc-nodesc-inband", "ignored-avcc-desc", "ignored-avcc-inband"];   // ignored-*:要了 Annex B,瀏覽器卻照樣給長度前綴
const md5 = (f, m) => execFileSync("ffmpeg", ["-v", "error", "-i", f, "-map", "0:" + m, "-f", "md5", "-"]).toString().trim();
let bad = 0;
for (const name of Object.keys(SOURCES)) {
  const v = fs.readFileSync(`${D}/${name}.h264`).toString("base64");
  const ref = md5(`${D}/${name}.h264`, "v");
  for (const mode of MODES) {
    const out = await page.evaluate(async ({ v, a, mode }) => {
      const b = s => Uint8Array.from(atob(s), c => c.charCodeAt(0));
      const vb = b(v), ab = b(a);
      // Annex B 切成一格一格:參數組/SEI/AUD 或新的畫面 NAL 出現、而目前這格已經有畫面時,就是新的一格(每格一個 slice)
      const starts = [];
      for (let i = 0; i + 3 < vb.length; i++) if (vb[i] === 0 && vb[i+1] === 0 && vb[i+2] === 1) { starts.push(i > 0 && vb[i-1] === 0 ? i - 1 : i); i += 2; }
      const aus = []; let auStart = 0, hasVcl = false;
      for (const st of starts) {
        const hdr = vb[vb[st + 2] === 1 ? st + 3 : st + 4] & 31;
        if (hasVcl && [1, 5, 6, 7, 8, 9].includes(hdr)) { aus.push(vb.subarray(auStart, st)); auStart = st; hasVcl = false; }
        if (hdr === 1 || hdr === 5) hasVcl = true;
      }
      aus.push(vb.subarray(auStart));
      const Muxer = await loadMuxer("mp4");
      const col = makeChunkCollector();
      const target = new Muxer.StreamTarget({ onData: (data, position) => col.write(data, position), chunked: true, chunkSize: 65536 });   // 小塊才測得到收尾時回頭改前面
      const muxer = new Muxer.Muxer({ target, video: { codec: "avc", width: 1920, height: 1080, frameRate: 30 }, audio: { codec: "aac", numberOfChannels: 2, sampleRate: 48000 }, fastStart: false, firstTimestampBehavior: "offset" });
      const avcFormat = mode.startsWith("avcc") ? "avc" : "annexb";
      const fmtSel = { container: "mp4", muxV: "avc", vCodec: "avc1.640028", avcFormat };
      const onV = muxVideoChunkFn(muxer, fmtSel, 1920, 1080, 30), onA = muxAudioChunkFn(muxer, fmtSel, 48000);
      const fake = (u8, type, ts, dur) => ({ byteLength: u8.length, copyTo(d){ d.set(u8); }, type, timestamp: ts, duration: dur });
      const toAvcc = nals => { let sz = 0; nals.forEach(n => sz += 4 + n.length); const d = new Uint8Array(sz); let o = 0; nals.forEach(n => { new DataView(d.buffer).setUint32(o, n.length); d.set(n, o + 4); o += 4 + n.length; }); return d; };
      // Chrome 標準:長度前綴、沒有參數組,description 自己組(用 annexb 的 packer)
      const pk = makeH264Packer("annexb"); const conv = aus.map(au => pk(au));
      const desc = conv.find(c => c.desc).desc;
      let small = 0;
      aus.forEach((au, i) => {
        const nals = h264SplitNals(au, "annexb");
        const key = nals.some(n => (n[0] & 31) === 5) ? "key" : "delta";
        const ts = Math.round(i * 1e6 / 30);
        if (mode === "annexb-nometa") onV(fake(au, key, ts, null), undefined);
        else if (mode === "annexb-meta-nodesc") onV(fake(au, key, ts, 33333), i === 0 ? { decoderConfig: { codec: "avc1.640028" } } : {});
        else if (mode === "avcc-desc" || mode === "ignored-avcc-desc") {
          const d = toAvcc(nals.filter(n => ![7, 8, 9].includes(n[0] & 31)));
          if (d[0] === 0 && d[1] === 0 && d[2] === 1) small++;
          onV(fake(d, key, ts, 33333), i === 0 ? { decoderConfig: { codec: "avc1.640028", description: desc, colorSpace: { primaries: "bt709", transfer: "bt709", matrix: "bt709", fullRange: false } } } : undefined);
        } else onV(fake(toAvcc(nals), key, ts, null), undefined);
      });
      // ADTS → 原始 AAC 幀
      let i = 0, k = 0;
      while (i + 7 < ab.length) { const len = ((ab[i+3] & 3) << 11) | (ab[i+4] << 3) | (ab[i+5] >> 5); const hl = (ab[i+1] & 1) ? 7 : 9; onA(fake(ab.subarray(i + hl, i + len), "key", Math.round(k * 1024 / 48000 * 1e6), null), undefined); i += len; k++; }
      muxer.finalize();
      const u = new Uint8Array(await col.toBlob("video/mp4").arrayBuffer());
      let s = ""; for (let j = 0; j < u.length; j += 0x8000) s += String.fromCharCode.apply(null, u.subarray(j, j + 0x8000));
      return { aus: aus.length, aacFrames: k, small, mp4: btoa(s) };
    }, { v, a, mode });
    const f = `${D}/${name}-${mode}.mp4`;
    fs.writeFileSync(f, Buffer.from(out.mp4, "base64"));
    let ok = false, info = "", aud = "";
    try {
      info = execFileSync("ffprobe", ["-v", "error", "-count_frames", "-show_entries", "stream=codec_name,nb_read_frames", "-of", "csv=p=0", f]).toString().trim().replace(/\n/g, " ");
      const vOk = md5(f, "v") === ref;
      const aFrames = +execFileSync("ffprobe", ["-v", "error", "-select_streams", "a", "-count_frames", "-show_entries", "stream=nb_read_frames", "-of", "csv=p=0", f]).toString().trim();
      const decodeErr = execFileSync("ffmpeg", ["-v", "error", "-i", f, "-f", "null", "-"], { stdio: ["ignore", "pipe", "pipe"] }).toString().trim();
      ok = vOk && aFrames === out.aacFrames && !decodeErr;
      aud = `聲音 ${aFrames}/${out.aacFrames} 格`;
      if (!vOk) info += " 畫面不同";
    } catch (e) { info += " 解不開: " + String(e.message).slice(0, 120); }
    if (!ok) bad++;
    console.log(ok ? "✓" : "✗", name, mode, info, aud, `${out.aus} 格`, out.small ? `(開頭像起始碼的小格 ${out.small} 個)` : "", ok ? "畫面逐位元相同" : "");
  }
}
await browser.close(); server.close();
if (errs.length) { bad++; console.log("錯誤:", errs.join(" | ")); }
console.log(bad ? `${bad} 項失敗` : "全部通過");
process.exit(bad ? 1 : 0);
