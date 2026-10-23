// 匯出 App 對 ASAP 樂譜自動算出的演奏(每個音的力度、秒數、踏板範圍),給 perf_compare.py 跟真人演奏比。
// 用法:node perf_dump.mjs <樂譜清單.txt(每行一個 MusicXML 路徑)> <輸出目錄>
import { chromium } from "playwright";
import http from "node:http"; import fs from "node:fs"; import path from "node:path";
const ROOT=process.env.ROOT||path.resolve(path.dirname(new URL(import.meta.url).pathname),"../..");
const server=http.createServer((q,r)=>{const p=path.join(ROOT,decodeURIComponent(q.url.split("?")[0]));if(!fs.existsSync(p)||fs.statSync(p).isDirectory()){r.writeHead(404);return r.end();}r.writeHead(200,{"content-type":p.endsWith(".html")?"text/html":"application/octet-stream"});fs.createReadStream(p).pipe(r);});
await new Promise(r=>server.listen(0,"127.0.0.1",r));
const b=await chromium.launch(); const pg=await b.newPage();
await pg.route(/fonts\.googleapis|fonts\.gstatic|jsdelivr|githubusercontent|\.flac/,r=>r.abort());
await pg.goto(`http://127.0.0.1:${server.address().port}/index.html`);
await pg.waitForFunction(()=>typeof loadScoreFile==="function");
const [list,outDir]=process.argv.slice(2);
for (const f of fs.readFileSync(list,"utf8").trim().split("\n")) {
  const out=path.join(outDir, f.replace(/[\/ ]/g,"_")+".json"); if (fs.existsSync(out)) continue;
  await pg.evaluate(()=>{window.__prev=typeof events!=="undefined"?events:null;});
  await pg.setInputFiles("#fileInput", f);
  try { await pg.waitForFunction(()=>events!==window.__prev && events.length>0 && events.some(e=>e.notes.some(n=>n.pvel!=null)),null,{timeout:240000}); } catch(e){ console.log("timeout",f); continue; }
  await pg.waitForTimeout(400);
  const r=await pg.evaluate(()=>{
    const notes=[]; const seen=new Set();
    for(const e of events) for(const n of e.notes) if(n.freq){ const m=Math.round(freqToMidi(n.freq)); const k=e.srcT.toFixed(5)+"_"+m; if(seen.has(k)) continue; seen.add(k);
      notes.push([+e.srcT.toFixed(5), m, Math.round(n.pvel), n.pmel?1:0, +(n.pdt||0).toFixed(4)]); }
    // 演奏位置→秒(含彈性速度)
    const sec=[]; for(const e of events){ sec.push([+e.srcT.toFixed(5), +e.tWhole.toFixed(5), +(typeof posToSec==="function"?posToSec(e.tWhole):0).toFixed(4)]); }
    return {notes, sec, ped: pedalRanges.map(r=>[r.start,r.end]), auto: (autoPedalRanges||[]).map(r=>[r.start,r.end]), p: (classicalProbInfo&&classicalProbInfo().p)};
  });
  fs.writeFileSync(out, JSON.stringify(r)); console.log("ok", path.basename(f), r.notes.length, "p", r.p?.toFixed(2));
}
await b.close(); server.close();
