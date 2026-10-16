// 把 App 要用的檔案複製到 app/www(Capacitor 的 webDir)。只放 App 會用到的東西:
//   index.html、privacy.html、vendor/(程式庫)、samples/(範例樂譜)、piano/、drums/(音色)
// 不放:guitar/(吉他沒有在 App 裡;授權也不能放進商業 App:GPL / CC-BY-NC)、tools/、各資料夾裡的 build/ 建置腳本
import fs from "node:fs";
import path from "node:path";
const ROOT = path.resolve(path.dirname(new URL(import.meta.url).pathname), "..");
const OUT = path.join(ROOT, "app", "www");
const FILES = ["index.html", "privacy.html"];
const DIRS = ["vendor", "samples", "piano", "drums"];
const SKIP = new Set(["build", "__pycache__"]);
const SKIP_EXT = new Set([".py"]);
fs.rmSync(OUT, { recursive: true, force: true });
fs.mkdirSync(OUT, { recursive: true });
let n = 0, bytes = 0;
const copy = (src, dst) => { fs.mkdirSync(path.dirname(dst), { recursive: true }); fs.copyFileSync(src, dst); n++; bytes += fs.statSync(src).size; };
for (const f of FILES) copy(path.join(ROOT, f), path.join(OUT, f));
const walk = (rel) => {
  for (const e of fs.readdirSync(path.join(ROOT, rel), { withFileTypes: true })) {
    if (SKIP.has(e.name)) continue;
    const r = path.join(rel, e.name);
    if (e.isDirectory()) walk(r);
    else if (!SKIP_EXT.has(path.extname(e.name))) copy(path.join(ROOT, r), path.join(OUT, r));
  }
};
for (const d of DIRS) walk(d);
console.log(`app/www: ${n} files, ${(bytes / 1048576).toFixed(1)} MB`);
