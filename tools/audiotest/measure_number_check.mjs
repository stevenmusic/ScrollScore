// 小節數字重疊檢查:node measure_number_check.mjs <樂譜...>(ROOT 環境變數可換版本;PAD = 邊界容許像素,預設 0.5,0 = 只算真的重疊)
import { chromium } from "playwright";
import http from "node:http"; import fs from "node:fs"; import path from "node:path";
const ROOT=process.env.ROOT||path.resolve(path.dirname(new URL(import.meta.url).pathname),"../..");
const server=http.createServer((q,r)=>{const p=path.join(ROOT,decodeURIComponent(q.url.split("?")[0]));if(!fs.existsSync(p)||fs.statSync(p).isDirectory()){r.writeHead(404);return r.end();}r.writeHead(200,{"content-type":p.endsWith(".html")?"text/html":"application/octet-stream"});fs.createReadStream(p).pipe(r);});
await new Promise(r=>server.listen(0,"127.0.0.1",r));
const b=await chromium.launch(); const pg=await b.newPage({viewport:{width:1440,height:900}});
await pg.route(/fonts\.googleapis|fonts\.gstatic|jsdelivr|githubusercontent|\.flac/,r=>r.abort());
await pg.goto(`http://127.0.0.1:${server.address().port}/index.html`);
await pg.waitForFunction(()=>typeof loadScoreFile==="function");
for (const f of process.argv.slice(2)) {
  await pg.evaluate(()=>{window.__prevEv=typeof events!=="undefined"?events:null;}); await pg.setInputFiles("#fileInput",f); await pg.waitForFunction(()=>events!==window.__prevEv&&events.length>0&&document.querySelector("#score svg"),null,{timeout:300000}); await pg.waitForTimeout(1500);
  const r = await pg.evaluate((PAD)=>{
    const svg=document.querySelector("#score svg");
    const labels=[]; try { for (const sys of osmd.GraphicSheet.MusicPages[0].MusicSystems) for (const l of sys.MeasureNumberLabels||[]) if (l.SVGNode) labels.push(l.SVGNode); } catch(e){}
    const nums = labels.length ? labels : [...svg.querySelectorAll("text")].filter(t=>/^\d+$/.test(t.textContent.trim()));
    const all=[...svg.querySelectorAll("path,text,rect,line,polygon,polyline,ellipse,circle")];
    const hits=[];
    for (const t of nums) {
      const R=t.getBoundingClientRect(); const pad=PAD;
      const inR=(x,y)=>x>R.left-pad&&x<R.right+pad&&y>R.top-pad&&y<R.bottom+pad;
      for (const e of all) { if (e===t || t.contains(e) || e.contains(t)) continue;
        const B=e.getBoundingClientRect(); if (B.width===0&&B.height===0) continue;
        if (B.right<R.left-pad||B.left>R.right+pad||B.bottom<R.top-pad||B.top>R.bottom+pad) continue;
        if (B.height<1.6 && B.width>R.width*2) continue;        // 譜線
        if (B.width<2.2 && B.height>R.height*1.5) continue;     // 小節線
        let hit=false;
        if (e.tagName==="path" && (B.width>R.width*1.5||B.height>R.height*1.5)) {
          const M=e.getScreenCTM(); const L=e.getTotalLength(); const step=Math.max(0.3, L/1500);
          for (let s=0;s<=L;s+=step){ const p=e.getPointAtLength(s); const x=M.a*p.x+M.c*p.y+M.e, y=M.b*p.x+M.d*p.y+M.f; if(inR(x,y)){hit=true;break;} }
        } else hit=true;
        if (hit) hits.push({num:t.textContent.trim(), tag:e.tagName, cls:(e.getAttribute("class")||e.parentNode.getAttribute&&e.parentNode.getAttribute("class")||""), txt:e.tagName==="text"?e.textContent:"", w:Math.round(B.width), h:Math.round(B.height)});
      }
    }
    return {n:nums.length, fromLabels:labels.length>0, hits};
  }, +(process.env.PAD ?? 0.5));
  console.log(path.basename(path.dirname(f))+"/"+path.basename(f), "numbers", r.n, r.fromLabels?"(labels)":"(text)", "overlaps", r.hits.length);
  for (const h of r.hits.slice(0,30)) console.log("   ", JSON.stringify(h));
}
await b.close(); server.close();
