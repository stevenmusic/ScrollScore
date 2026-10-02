/* ScrollScore promo — every frame is a pure function of time t (seconds). The renderer calls setTime(t). */
const W = 1920, H = 1080;
const $c = (tag, cls, parent, html) => { const e = document.createElement(tag); if (cls) e.className = cls; if (html != null) e.innerHTML = html; (parent || document.body).appendChild(e); return e; };
const clamp = (x, a = 0, b = 1) => Math.max(a, Math.min(b, x));
const lerp = (a, b, p) => a + (b - a) * p;
const seg = (t, a, b) => clamp((t - a) / (b - a));
const eOut = p => 1 - Math.pow(1 - p, 3);
const eIn = p => p * p * p;
const eIO = p => p < .5 ? 4 * p * p * p : 1 - Math.pow(-2 * p + 2, 3) / 2;
const eBack = p => { const c1 = 1.70158, c3 = c1 + 1; return 1 + c3 * Math.pow(p - 1, 3) + c1 * Math.pow(p - 1, 2); };
const css = (el, o) => { for (const k in o) el.style[k] = o[k]; };
function rnd(seed) { let s = seed | 0; return () => { s = s + 0x6D2B79F5 | 0; let t = Math.imul(s ^ s >>> 15, 1 | s); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; }; }

/* ── text helpers ── */
function maskLine(parent, html, cls, style) {
  const m = $c('div', 'mask ' + (cls || ''), parent); const s = $c('span', '', m, html); if (style) css(m, style); return { m, s };
}
function reveal(line, p, dy = 110) { line.s.style.transform = `translateY(${(1 - eOut(p)) * dy}%)`; line.m.style.opacity = p > 0 ? 1 : 0; }
function titleBlock(parent, x, y, kicker, title, sub, opts = {}) {
  const box = $c('div', 'abs', parent); css(box, { left: x + 'px', top: y + 'px', width: (opts.w || 900) + 'px', textAlign: opts.align || 'left' });
  const k = maskLine(box, kicker, 'kicker'); $c('div', '', box).style.height = '18px';
  const lines = title.split('\n').map(l => { const r = maskLine(box, l, 'h2', { display: 'block' }); return r; });
  $c('div', '', box).style.height = '22px';
  const s = maskLine(box, sub, 'sub', { display: 'block' });
  const bar = $c('div', 'abs', box); css(bar, { left: opts.align === 'center' ? 'calc(50% - 60px)' : '0', top: '-26px', height: '3px', background: 'var(--gold)', width: '0px' });
  return {
    box, update(lt, out) {
      reveal(k, seg(lt, 0.0, 0.6)); lines.forEach((l, i) => reveal(l, seg(lt, 0.12 + i * 0.12, 0.85 + i * 0.12))); reveal(s, seg(lt, 0.45, 1.2));
      bar.style.width = (eOut(seg(lt, 0.2, 1.0)) * 120) + 'px';
      const o = 1 - eIn(seg(lt, out - 0.5, out)); box.style.opacity = o; box.style.transform = `translateY(${(1 - o) * -30}px)`;
    }
  };
}
function chip(parent, html, x, y) { const c = $c('div', 'chip abs', parent, html); css(c, { left: x + 'px', top: y + 'px' }); return c; }
function popIn(el, p, from = 0.85) { const q = eBack(clamp(p)); el.style.opacity = clamp(p * 1.6); el.style.transform = `translateY(${(1 - eOut(p)) * 40}px) scale(${lerp(from, 1, q)})`; }

/* ── device frames with live app iframes ── */
const APP = {};
function laptop(parent, key, x, y, w, query, vw = 1920) {
  const h = w * 9 / 16, wrap = $c('div', 'laptop', parent); css(wrap, { left: x + 'px', top: y + 'px', width: w + 'px', height: h + 'px' });
  const scr = $c('div', 'screen', wrap); css(scr, { left: 0, top: 0, width: w + 'px', height: h + 'px' });
  const base = $c('div', 'base', wrap); css(base, { left: -w * 0.06 + 'px', top: h + 14 + 'px', width: w * 1.12 + 'px' });
  let fr = null;
  if (key) { fr = $c('iframe', '', scr); fr.src = '/app/index.html?f=' + key + (query || ''); css(fr, { width: vw + 'px', height: (vw * 9 / 16) + 'px', transform: `scale(${w / vw})` }); APP[key] = fr; }
  return { wrap, scr, fr };
}
function phone(parent, key, x, y, w) {
  const h = w * 844 / 390, wrap = $c('div', 'phone abs', parent); css(wrap, { left: x + 'px', top: y + 'px', width: w + 'px', height: h + 'px' });
  const scr = $c('div', 'screen', wrap); css(scr, { left: 0, top: 0, width: w + 'px', height: h + 'px' });
  const fr = $c('iframe', '', scr); fr.src = '/app/index.html?f=' + key; css(fr, { width: '390px', height: '844px', transform: `scale(${w / 390})` }); APP[key] = fr;
  return { wrap, scr, fr };
}
/* drive an app iframe to song position sec, looking like it is playing */
function appAt(key, sec) {
  const fr = APP[key]; if (!fr || !fr.contentWindow || !fr.contentWindow.seekTo) return;
  const w = fr.contentWindow;
  try { if (w.__lastSec !== sec) { w.seekTo(sec); w.drawKeyboardLive && w.drawKeyboardLive(sec); w.updateMeasureHighlight && w.updateMeasureHighlight(sec); w.__lastSec = sec; } if (!w.__playLook) { w.setPlayBtnState && w.setPlayBtnState(true); w.__playLook = true; } } catch (e) { }
}

/* ── background ── */
const bg = document.getElementById('bg'); bg.width = 3840; bg.height = 2160; bg.style.width = '1920px'; bg.style.height = '1080px';
const g = bg.getContext('2d'); g.scale(2, 2);
const DUST = (() => { const r = rnd(7); return Array.from({ length: 70 }, () => ({ x: r() * W, y: r() * H, s: 0.6 + r() * 2.2, v: 4 + r() * 14, ph: r() * 6.28, a: 0.15 + r() * 0.45 })); })();
function drawBg(t, glow = 1) {
  const gr = g.createRadialGradient(W * 0.5, H * 0.45, 50, W * 0.5, H * 0.5, W * 0.75);
  gr.addColorStop(0, '#1d150c'); gr.addColorStop(1, '#070504'); g.fillStyle = gr; g.fillRect(0, 0, W, H);
  const blobs = [[0.18, 0.25, 520, 0.10], [0.82, 0.7, 640, 0.08], [0.55, 0.1, 420, 0.06]];
  blobs.forEach(([bx, by, r, a], i) => {
    const x = W * bx + Math.sin(t * 0.21 + i * 2) * 90, y = H * by + Math.cos(t * 0.17 + i) * 60;
    const rg = g.createRadialGradient(x, y, 0, x, y, r); rg.addColorStop(0, `rgba(214,178,94,${a * glow})`); rg.addColorStop(1, 'rgba(214,178,94,0)');
    g.fillStyle = rg; g.fillRect(0, 0, W, H);
  });
  // faint drifting staff lines
  g.strokeStyle = 'rgba(214,178,94,0.05)'; g.lineWidth = 1.2;
  for (let k = 0; k < 5; k++) { const y = H * 0.82 + k * 16; g.beginPath(); for (let x = 0; x <= W; x += 40) g.lineTo(x, y + Math.sin(x * 0.004 + t * 0.4) * 10); g.stroke(); }
  for (const d of DUST) {
    const y = (d.y - t * d.v + H * 10) % H, x = d.x + Math.sin(t * 0.5 + d.ph) * 12;
    g.fillStyle = `rgba(232,200,120,${d.a * (0.6 + 0.4 * Math.sin(t * 1.3 + d.ph)) * glow})`; g.beginPath(); g.arc(x, y, d.s, 0, 6.283); g.fill();
  }
}

const ICON = {"piano": "<svg width=\"78\" height=\"66\" viewBox=\"0 0 70 60\"><rect x=\"2\" y=\"2\" width=\"66\" height=\"56\" rx=\"6\" fill=\"none\" stroke=\"#d6b25e\" stroke-width=\"3\"/><g fill=\"#d6b25e\"><rect x=\"13\" y=\"2\" width=\"7\" height=\"32\"/><rect x=\"27\" y=\"2\" width=\"7\" height=\"32\"/><rect x=\"45\" y=\"2\" width=\"7\" height=\"32\"/></g><g stroke=\"#d6b25e\" stroke-width=\"2\"><line x1=\"16.5\" y1=\"34\" x2=\"16.5\" y2=\"58\"/><line x1=\"30.5\" y1=\"34\" x2=\"30.5\" y2=\"58\"/><line x1=\"39\" y1=\"2\" x2=\"39\" y2=\"58\"/><line x1=\"48.5\" y1=\"34\" x2=\"48.5\" y2=\"58\"/></g></svg>", "guitar": "<svg width=\"72\" height=\"72\" viewBox=\"0 0 70 70\"><g fill=\"none\" stroke=\"#d6b25e\" stroke-width=\"3\" stroke-linecap=\"round\"><circle cx=\"22\" cy=\"50\" r=\"15\"/><circle cx=\"34\" cy=\"36\" r=\"10\"/><line x1=\"39\" y1=\"31\" x2=\"60\" y2=\"10\"/><rect x=\"56\" y=\"3\" width=\"10\" height=\"10\" rx=\"2\" transform=\"rotate(45 61 8)\"/><circle cx=\"25\" cy=\"46\" r=\"4.5\"/><line x1=\"14\" y1=\"58\" x2=\"20\" y2=\"52\"/></g></svg>", "drum": "<svg width=\"72\" height=\"72\" viewBox=\"0 0 70 70\"><g fill=\"none\" stroke=\"#d6b25e\" stroke-width=\"3\" stroke-linecap=\"round\"><ellipse cx=\"35\" cy=\"34\" rx=\"24\" ry=\"8\"/><path d=\"M11 34v18c0 4.4 10.7 8 24 8s24-3.6 24-8V34\"/><path d=\"M11 40l48 12M59 40L11 52\" stroke-width=\"1.6\"/><line x1=\"16\" y1=\"4\" x2=\"33\" y2=\"28\"/><line x1=\"56\" y1=\"4\" x2=\"39\" y2=\"28\"/></g></svg>"};
/* ── scenes ── */
const SC = [];
const root = document.getElementById('scenes');
function scene(dur, build) { const el = $c('div', 'scene', root); const s = { el, dur, start: 0 }; s.update = build(el, s); SC.push(s); return s; }

/* small SVG note helpers */
// head centre at (17,140); stem = 3.5 staff spaces (119px). Stem up on the right of the head, down on the left.
function noteSVG(down) { return `<svg width="46" height="280" viewBox="0 0 46 280"><ellipse cx="17" cy="140" rx="16" ry="12" transform="rotate(-22 17 140)" fill="currentColor"/><rect x="${down ? 1 : 29}" y="${down ? 142 : 21}" width="4" height="117" fill="currentColor"/></svg>`; }

/* 1. Intro */
scene(6.23, (el, s) => {
  const staff = $c('div', 'abs', el); css(staff, { left: '0', top: '420px', width: '1920px', height: '240px' });
  const lines = Array.from({ length: 5 }, (_, i) => { const l = $c('div', 'abs', staff); css(l, { left: '160px', top: (i * 34) + 'px', height: '2.5px', background: 'linear-gradient(90deg, rgba(214,178,94,0), var(--gold) 10%, var(--gold) 90%, rgba(214,178,94,0))', width: '0px' }); return l; });
  const notes = [[260, 3.5], [420, 2.5], [580, 1.5], [740, 3], [900, 2], [1060, 1], [1220, 2.5], [1380, 1.5], [1540, 0.5], [1680, 2]].map(([x, pos], i) => {
    // head y = pos*34+17 → staff line index pos+0.5 (0 = top line, 2 = middle line); on or above the middle line → stem down
    const n = $c('div', 'abs gold', staff, noteSVG(pos + 0.5 <= 2)); css(n, { left: x + 'px', top: (pos * 34 + 17 - 140) + 'px', color: 'var(--gold)' }); return n;
  });
  const logo = $c('div', 'abs serif', el); css(logo, { left: 0, width: '1920px', top: '380px', textAlign: 'center', fontSize: '176px', fontWeight: 700, letterSpacing: '.04em' });
  const letters = 'ScrollScore'.split('').map((ch, i) => { const sp = $c('span', '', logo, ch); css(sp, { display: 'inline-block', color: i < 6 ? 'var(--gold)' : 'var(--ivory)' }); return sp; });
  const tag = $c('div', 'abs', el); css(tag, { left: 0, width: '1920px', top: '625px', textAlign: 'center' });
  const t1 = maskLine(tag, '讓樂譜跟著音樂，自己捲動', 'serif', { display: 'block', fontSize: '50px', fontWeight: 600, color: 'var(--ivory)' });
  const t2 = maskLine(tag, 'SCROLLING SHEET MUSIC PLAYER', 'kicker', { display: 'block', marginTop: '22px', fontSize: '24px' });
  return (lt) => {
    lines.forEach((l, i) => { l.style.width = (eIO(seg(lt, 0.1 + i * 0.08, 1.4 + i * 0.08)) * 1600) + 'px'; });
    notes.forEach((n, i) => popIn(n, seg(lt, 0.7 + i * 0.12, 1.25 + i * 0.12), 0.3));
    const up = eIO(seg(lt, 2.4, 3.3)); css(staff, { transform: `translateY(${-up * 170}px) scale(${1 - up * 0.25})`, opacity: 1 - up * 0.75 });
    letters.forEach((sp, i) => { const p = seg(lt, 2.7 + i * 0.05, 3.4 + i * 0.05); sp.style.opacity = p; sp.style.transform = `translateY(${(1 - eOut(p)) * 60}px)`; sp.style.filter = `blur(${(1 - p) * 10}px)`; });
    reveal(t1, seg(lt, 3.5, 4.3)); reveal(t2, seg(lt, 3.8, 4.6));
  };
});

/* 2. Load MusicXML */
scene(8, (el, s) => {
  const tb = titleBlock(el, 130, 330, '01 · 載入樂譜', '匯入 MusicXML\n馬上開始', 'Sibelius · Finale · MuseScore 匯出的檔案都能用', { w: 700 });
  const lap = laptop(el, 'empty', 840, 250, 960);
  const lap2 = laptop(el, 'main', 840, 250, 960);
  const file = $c('div', 'abs card', el); css(file, { left: '0px', top: '0px', width: '210px', height: '260px', display: 'grid', placeItems: 'center', borderRadius: '22px' });
  file.innerHTML = '<div style="text-align:center"><svg width="90" height="100" viewBox="0 0 90 100"><path d="M10 6h48l22 22v66H10z" fill="none" stroke="#d6b25e" stroke-width="4"/><path d="M58 6v22h22" fill="none" stroke="#d6b25e" stroke-width="4"/><rect x="24" y="48" width="42" height="3" fill="#d6b25e"/><rect x="24" y="60" width="42" height="3" fill="#d6b25e"/><rect x="24" y="72" width="30" height="3" fill="#d6b25e"/></svg><div class="en" style="font-size:30px;font-weight:700;margin-top:12px;color:#f4ecd9">.mxl</div></div>';
  const row = $c('div', 'abs', el); css(row, { left: '130px', top: '700px', display: 'flex', gap: '18px' }); const chips = ['.xml', '.mxl', '.musicxml'].map(n => { const c = $c('div', 'chip en', row, n); c.style.position = 'relative'; return c; });
  return (lt) => {
    tb.update(lt, s.dur);
    const lp = eOut(seg(lt, 0.2, 1.1)); css(lap.wrap, { opacity: lp, transform: `translateX(${(1 - lp) * 120}px)` });
    const fp = seg(lt, 1.6, 3.0), fx = lerp(560, 1220, eIO(fp)), fy = lerp(620, 400, eIO(fp)) - Math.sin(fp * Math.PI) * 120;
    css(file, { left: fx + 'px', top: fy + 'px', opacity: (fp > 0 ? 1 : 0) * (1 - seg(lt, 2.85, 3.05)), transform: `rotate(${lerp(-14, 0, eOut(fp))}deg) scale(${lerp(1, 0.55, eIn(seg(lt, 2.4, 3.0)))})` });
    const sw = seg(lt, 3.0, 3.6); css(lap2.wrap, { opacity: lp * sw }); lap2.wrap.style.transform = lap.wrap.style.transform;
    appAt('main', 0);
    chips.forEach((c, i) => popIn(c, seg(lt, 1.0 + i * 0.15, 1.6 + i * 0.15)));
  };
});

/* 3. Scrolling playback */
scene(12, (el, s) => {
  const tb = titleBlock(el, 0, 70, '02 · 自動捲動', '樂譜跟著音樂走，眼睛不用追', 'A fixed playhead — the score scrolls to you', { w: 1920, align: 'center' });
  const lap = laptop(el, 'main2', 300, 280, 1320);
  const cs = [
    { el: null, x: 1660, y: 540, html: '固定播放軸', side: 'r', ax: 300 + 1320 * 0.25, ay: 280 + 742 * 0.40, at: 2.2 },
    { el: null, x: 1660, y: 830, html: '鍵盤即時亮起 · 左右手分色', side: 'r', ax: 300 + 1320 * 0.55, ay: 280 + 742 * 0.86, at: 4.4 },
    { el: null, x: 1660, y: 980, html: '進度條・時間・快速跳轉', side: 'r', ax: 300 + 1320 * 0.94, ay: 280 + 742 * 0.98, at: 6.6 },
  ];
  cs.forEach(c => { c.box = $c('div', 'abs card', el); css(c.box, { padding: '18px 30px', fontSize: '30px', fontWeight: 600, whiteSpace: 'nowrap' }); c.box.innerHTML = '<span class="gold">●</span>  ' + c.html; c.svg = $c('div', 'abs', el); });
  const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg'); svg.setAttribute('width', 1920); svg.setAttribute('height', 1080); css(svg, { position: 'absolute', left: 0, top: 0, pointerEvents: 'none' }); el.appendChild(svg);
  cs.forEach(c => { c.path = document.createElementNS('http://www.w3.org/2000/svg', 'path'); c.path.setAttribute('stroke', '#d6b25e'); c.path.setAttribute('stroke-width', '2.5'); c.path.setAttribute('fill', 'none'); svg.appendChild(c.path); c.dot = document.createElementNS('http://www.w3.org/2000/svg', 'circle'); c.dot.setAttribute('r', '9'); c.dot.setAttribute('fill', '#d6b25e'); svg.appendChild(c.dot); });
  return (lt) => {
    tb.update(lt, s.dur);
    const lp = eOut(seg(lt, 0.0, 0.9)); css(lap.wrap, { opacity: lp, transform: `translateY(${(1 - lp) * 60}px) scale(${lerp(0.94, 1, lp)})` });
    appAt('main2', 1.0 + Math.max(0, lt - 0.3) * 1.0);
    cs.forEach((c, i) => {
      const p = seg(lt, c.at, c.at + 0.7), hide = seg(lt, c.at + 2.0, c.at + 2.5);
      const bx = 1490, by = 360 + i * 150;
      css(c.box, { left: bx + 'px', top: by + 'px', opacity: eOut(p) * (1 - hide), transform: `translateX(${(1 - eOut(p)) * 40}px)` });
      const len = eOut(seg(lt, c.at, c.at + 0.5));
      const x0 = bx, y0 = by + 36, x1 = lerp(x0, c.ax, len), y1 = lerp(y0, c.ay, len);
      c.path.setAttribute('d', `M${x0},${y0} L${x1},${y1}`); c.path.setAttribute('opacity', (1 - hide) * (p > 0 ? 1 : 0));
      c.dot.setAttribute('cx', c.ax); c.dot.setAttribute('cy', c.ay); c.dot.setAttribute('opacity', (1 - hide) * seg(lt, c.at + 0.4, c.at + 0.6)); c.dot.setAttribute('r', 9 + Math.sin(lt * 6) * 2);
    });
  };
});

/* 4. Real instruments */
scene(12, (el, s) => {
  const tb = titleBlock(el, 0, 70, '03 · 真實樂器音色', '真實錄音取樣，不是電子合成音', 'Piano · Drum kit', { w: 1920, align: 'center' });
  const items = [
    [ICON.piano, '鋼琴', 'Yamaha C5 平台鋼琴', '16 層力度・弦共鳴・踏板聲'],
    [ICON.drum, '鼓組', 'Naked Drums', '全部力度層・輪替取樣'],
  ];
  const cards = items.map(([ic, n, a, b], i) => {
    const c = $c('div', 'abs card', el); css(c, { width: '380px', height: '300px', padding: '40px 36px' });
    c.innerHTML = `<div style="height:72px;display:flex;align-items:center">${ic}</div><div class="serif" style="font-size:46px;font-weight:700;margin-top:22px">${n}</div><div style="font-size:26px;color:var(--gold);margin-top:10px;font-weight:600">${a}</div><div style="font-size:24px;color:var(--muted);margin-top:8px">${b}</div>`;
    return c;
  });
  const lap = laptop(el, 'drum', 460, 420, 1000, '', 1280);
  const eq = $c('div', 'abs', el); css(eq, { left: '0', top: '0' });
  return (lt) => {
    tb.update(lt, s.dur);
    const shrink = eIO(seg(lt, 5.6, 6.6));
    cards.forEach((c, i) => {
      const p = seg(lt, 0.5 + i * 0.18, 1.2 + i * 0.18);
      // 兩張卡(鋼琴、鼓組;吉他找不到夠好的音色已拿掉):先置中並排,筆電出現時分到左右兩側
      const x0 = 555 + i * 430, y0 = 380, x1 = i === 0 ? 60 : 1520, y1 = 560;
      const sc = lerp(1, 0.86, shrink);
      css(c, { left: lerp(x0, x1, shrink) + 'px', top: lerp(y0, y1, shrink) + 'px', opacity: eOut(p), transform: `translateY(${(1 - eOut(p)) * 60}px) scale(${sc})`, transformOrigin: '0 0' });
      // glow pulse on the drum card while the drum kit plays
      c.style.borderColor = (i === 1 && lt > 6.6) ? `rgba(214,178,94,${0.4 + 0.4 * Math.abs(Math.sin(lt * 3.4))})` : '';
    });
    const lp = eOut(seg(lt, 6.2, 7.0)); css(lap.wrap, { opacity: lp, transform: `translateY(${(1 - lp) * 80}px)` });
    appAt('drum', 0.5 + Math.max(0, lt - 6.2));
  };
});

/* 5. Human expression */
scene(10, (el, s) => {
  const tb = titleBlock(el, 140, 120, '04 · 像真人一樣彈', '每個音的輕重\n都自動算好', 'Dynamics · Phrasing · Pedal — simulated per note', { w: 900 });
  const plot = $c('div', 'abs', el); css(plot, { left: '140px', top: '520px', width: '1640px', height: '380px' });
  const N = 72, bars = [];
  const vel = i => { const ph = i / N; const macro = 0.45 + 0.35 * Math.sin(Math.PI * ph) ; const arch = 0.08 * Math.sin(Math.PI * ((i % 18) / 18)); const beat = (i % 4 === 0 ? 0.08 : i % 2 === 0 ? 0.03 : -0.03); const r = rnd(i * 13 + 5)(); return clamp(macro + arch + beat + (r - 0.5) * 0.06, 0.12, 1); };
  for (let i = 0; i < N; i++) { const b = $c('div', 'bar', plot); css(b, { left: (i * 22.6) + 'px', height: '0px', opacity: 0.95 }); bars.push(b); }
  const marks = [['p', 0.06], ['mf', 0.3], ['f', 0.5], ['mf', 0.72], ['p', 0.92]].map(([m, x]) => { const d = $c('div', 'abs serif', plot); css(d, { left: (x * 1640) + 'px', top: '400px', fontStyle: 'italic', fontWeight: 700, fontSize: '44px', color: 'var(--ivory)' }); d.textContent = m; return d; });
  const ped = $c('div', 'abs', plot); css(ped, { left: '0', top: '505px', height: '3px', background: 'rgba(63,199,180,.8)', width: '0px' });
  const pedL = $c('div', 'abs en', plot); css(pedL, { left: '-70px', top: '488px', fontSize: '26px', color: 'var(--teal)', fontWeight: 600 }); pedL.textContent = 'Ped.';
  const chipsT = ['力度記號 pp – fff', '漸強 / 漸弱', '旋律突出・伴奏放輕', '延音踏板與半踏板', '樂句起伏', '反覆記號・琶音'];
  const chips = chipsT.map((t, i) => chip(el, t, 1080 + (i % 2) * 360, 150 + Math.floor(i / 2) * 96));
  return (lt) => {
    tb.update(lt, s.dur);
    bars.forEach((b, i) => { const p = seg(lt, 0.6 + i * 0.025, 1.4 + i * 0.025); const v = vel(i) * (1 + 0.04 * Math.sin(lt * 2.2 + i * 0.4)); b.style.height = (eOut(p) * v * 340) + 'px'; b.style.opacity = 0.35 + 0.65 * (i / N < seg(lt, 2.0, 8.0) ? 1 : 0.4); });
    marks.forEach((m, i) => popIn(m, seg(lt, 1.6 + i * 0.25, 2.1 + i * 0.25)));
    ped.style.width = (eIO(seg(lt, 3.0, 6.0)) * 1640) + 'px'; pedL.style.opacity = seg(lt, 3.0, 3.4);
    chips.forEach((c, i) => popIn(c, seg(lt, 1.2 + i * 0.22, 1.8 + i * 0.22)));
  };
});

/* 6. Practice tools */
scene(10, (el, s) => {
  const tb = titleBlock(el, 0, 70, '05 · 練習好幫手', '慢速、移調、預備拍，一次到位', 'Tempo · Transpose · Count-in · Measure highlight · Seek · Shortcuts', { w: 1920, align: 'center' });
  const cells = [];
  const mk = (i, title, sub) => { const c = $c('div', 'abs card', el); const x = 150 + (i % 3) * 556, y = 330 + Math.floor(i / 3) * 350; css(c, { left: x + 'px', top: y + 'px', width: '506px', height: '310px', padding: '34px 38px' }); c.innerHTML = `<div class="serif" style="font-size:40px;font-weight:700">${title}</div><div style="font-size:24px;color:var(--muted);margin-top:6px">${sub}</div>`; const v = $c('div', 'abs', c); css(v, { left: '38px', right: '38px', top: '140px', bottom: '30px' }); cells.push(c); return v; };
  // tempo
  const v1 = mk(0, '速度', '40–400 BPM，慢練再加速'); const num = $c('div', 'abs en', v1); css(num, { left: 0, top: '0px', fontSize: '76px', fontWeight: 800, color: 'var(--gold)' }); const bpm = $c('div', 'abs en', v1); css(bpm, { left: '190px', top: '42px', fontSize: '28px', color: 'var(--muted)' }); bpm.textContent = 'BPM';
  const tr = $c('div', 'abs', v1); css(tr, { left: 0, right: 0, top: '120px', height: '8px', borderRadius: '4px', background: 'rgba(214,178,94,.18)' }); const fill = $c('div', 'abs', tr); css(fill, { left: 0, top: 0, bottom: 0, borderRadius: '4px', background: 'var(--gold)' }); const knob = $c('div', 'abs', tr); css(knob, { top: '-10px', width: '28px', height: '28px', borderRadius: '50%', background: 'var(--ivory)', boxShadow: '0 0 0 6px rgba(214,178,94,.35)' });
  // transpose
  const v2 = mk(1, '移調', '升降半音，樂譜即時改寫'); const keyA = $c('div', 'abs serif', v2); css(keyA, { left: '0', top: '-6px', fontSize: '86px', fontWeight: 700 }); const arrows = $c('div', 'abs en', v2); css(arrows, { left: '170px', top: '28px', fontSize: '30px', color: 'var(--gold)', fontWeight: 700 });
  // count-in
  const v3 = mk(2, '預備拍', '先敲一小節，再開始'); const dots = Array.from({ length: 4 }, (_, i) => { const d = $c('div', 'abs', v3); css(d, { left: (i * 100) + 'px', top: '20px', width: '64px', height: '64px', borderRadius: '50%', border: '3px solid var(--gold)' }); return d; });
  // measure highlight
  const v4 = mk(3, '小節高亮', '目前小節整段標色'); for (let k = 0; k < 5; k++) { const l = $c('div', 'abs', v4); css(l, { left: 0, right: 0, top: (20 + k * 18) + 'px', height: '2px', background: 'rgba(244,236,217,.55)' }); } const hl = $c('div', 'abs', v4); css(hl, { top: '6px', height: '102px', width: '25%', borderRadius: '6px', background: 'rgba(214,178,94,.32)' }); for (let k = 1; k < 4; k++) { const bl = $c('div', 'abs', v4); css(bl, { left: (k * 25) + '%', top: '20px', width: '2px', height: '74px', background: 'rgba(244,236,217,.55)' }); }
  // seek
  const v5 = mk(4, '精準跳轉', '點時間、拖進度條、指定區間'); const tm = $c('div', 'abs en', v5); css(tm, { left: 0, top: '0px', fontSize: '76px', fontWeight: 800, color: 'var(--ivory)' }); const caret = $c('div', 'abs', v5); css(caret, { top: '14px', width: '4px', height: '74px', background: 'var(--gold)' });
  // shortcuts
  const v6 = mk(5, '快捷鍵與手勢', '鍵盤、觸控都好操作'); const keys = ['Space', '←', '→', 'Esc'].map((k, i) => { const kc = $c('div', 'abs en', v6); css(kc, { left: [0, 160, 250, 340][i] + 'px', top: '24px', padding: '14px 22px', border: '2px solid var(--line)', borderBottomWidth: '6px', borderRadius: '14px', fontSize: '28px', fontWeight: 700 }); kc.textContent = k; return kc; });
  return (lt) => {
    tb.update(lt, s.dur);
    cells.forEach((c, i) => popIn(c, seg(lt, 0.5 + i * 0.14, 1.2 + i * 0.14), 0.9));
    const tp = eIO(seg(lt, 1.6, 4.0)); const b = Math.round(lerp(60, 132, tp)); num.textContent = b; fill.style.width = (tp * 100) + '%'; knob.style.left = `calc(${tp * 100}% - 14px)`;
    const kStep = Math.floor(clamp((lt - 2.0) / 1.2, 0, 4)); keyA.textContent = ['C', 'D♭', 'D', 'E♭', 'E'][kStep]; arrows.textContent = kStep ? `+${kStep} 半音` : '原調';
    const beat = Math.floor(((lt - 1.5) * 2.2) % 4 + 4) % 4; dots.forEach((d, i) => { const on = lt > 1.5 && i === beat; d.style.background = on ? 'var(--gold)' : 'transparent'; d.style.transform = `scale(${on ? 1.12 : 1})`; d.style.boxShadow = on ? '0 0 30px rgba(214,178,94,.8)' : 'none'; });
    hl.style.left = (Math.floor(clamp((lt - 1.5) / 1.5, 0, 3.99)) * 25) + '%';
    const full = '1:24', n = Math.floor(clamp((lt - 2.2) / 0.35, 0, 4)); tm.textContent = full.slice(0, n) || ' '; caret.style.left = (n * 44) + 'px'; caret.style.opacity = (Math.floor(lt * 2) % 2) ? 1 : 0.2;
    keys.forEach((k, i) => { const on = Math.floor((lt - 1.5) * 1.6) % 4 === i && lt > 1.5; k.style.background = on ? 'rgba(214,178,94,.35)' : 'transparent'; k.style.transform = `translateY(${on ? 4 : 0}px)`; });
  };
});

/* 7. Sync with your recording */
scene(8, (el, s) => {
  const tb = titleBlock(el, 0, 70, '06 · 配合你的演奏錄音', '匯入音檔或影片，樂譜自動對上', 'Auto beat detection · Tap calibration · Score + video', { w: 1920, align: 'center' });
  const cv = $c('canvas', 'abs', el); cv.width = 3200; cv.height = 900; css(cv, { left: '160px', top: '340px', width: '1600px', height: '450px' });
  const c2 = cv.getContext('2d'); c2.scale(2, 2);
  const r = rnd(3), wav = Array.from({ length: 1600 }, (_, i) => { const beat = (i % 100); const env = Math.exp(-beat / 18); return (0.15 + 0.85 * env) * (0.5 + 0.5 * r()); });
  const chips = ['自動偵測拍點', '手動 Tap 校準', '樂譜＋影片一起輸出'].map((t, i) => chip(el, t, 460 + i * 360, 850));
  return (lt) => {
    tb.update(lt, s.dur);
    c2.clearRect(0, 0, 1600, 450);
    const shift = (lt * 140) % 100;
    // staff with notes on top
    c2.strokeStyle = 'rgba(244,236,217,.5)'; c2.lineWidth = 1.5; for (let k = 0; k < 5; k++) { c2.beginPath(); c2.moveTo(0, 30 + k * 14); c2.lineTo(1600, 30 + k * 14); c2.stroke(); }
    const alignP = eIO(seg(lt, 3.0, 5.0));
    for (let i = 0; i < 18; i++) {
      const xb = i * 100 - shift + 50, jitter = (rnd(i * 7 + 1)() - 0.5) * 60 * (1 - alignP);
      const xn = xb + jitter, y = 30 + ((i * 3) % 5) * 7;
      c2.fillStyle = '#f4ecd9'; c2.beginPath(); c2.ellipse(xn, y + 10, 9, 7, -0.4, 0, 6.283); c2.fill();
      const vis = seg(lt, 1.2 + i * 0.05, 1.5 + i * 0.05);
      c2.strokeStyle = `rgba(214,178,94,${0.85 * vis})`; c2.lineWidth = 2; c2.setLineDash([6, 6]); c2.beginPath(); c2.moveTo(xb, 130); c2.lineTo(xn, y + 22); c2.stroke(); c2.setLineDash([]);
    }
    // waveform
    for (let x = 0; x < 1600; x++) { const idx = Math.floor(x + shift * 1) % 1600; const a = wav[idx] * 130 * eOut(seg(lt, 0.5, 1.3)); c2.fillStyle = 'rgba(214,178,94,.85)'; c2.fillRect(x, 300 - a, 1, a * 2); }
    // onset markers
    for (let i = 0; i < 18; i++) { const xb = i * 100 - shift + 50; const p = seg(lt, 1.0 + i * 0.05, 1.3 + i * 0.05); c2.fillStyle = `rgba(63,199,180,${p})`; c2.beginPath(); c2.moveTo(xb, 140); c2.lineTo(xb - 9, 124); c2.lineTo(xb + 9, 124); c2.fill(); c2.fillRect(xb - 1, 140, 2, 300); }
    // playhead
    c2.fillStyle = 'rgba(214,178,94,1)'; c2.fillRect(480, 0, 3, 450);
    chips.forEach((c, i) => popIn(c, seg(lt, 2.0 + i * 0.3, 2.6 + i * 0.3)));
  };
});

/* 8. Export video */
scene(12, (el, s) => {
  const tb = titleBlock(el, 0, 60, '07 · 一鍵匯出影片', 'YouTube、Shorts、IG 一次搞定', 'Landscape 16:9 · Portrait 9:16 · Square 1:1 — titles & watermark included', { w: 1920, align: 'center' });
  const steps = ['匯出類型', '片段區間', '樂譜對齊', '標題・浮水印', '影片格式'];
  const st = steps.map((t, i) => { const c = $c('div', 'abs', el); css(c, { left: (260 + i * 290) + 'px', top: '300px', width: '250px', textAlign: 'center' }); c.innerHTML = `<div class="en" style="width:64px;height:64px;margin:0 auto;border-radius:50%;border:2px solid var(--gold);display:grid;place-items:center;font-size:28px;font-weight:700;color:var(--gold)">${i + 1}</div><div style="font-size:28px;margin-top:14px;font-weight:600">${t}</div>`; return c; });
  const conn = $c('div', 'abs', el); css(conn, { left: '385px', top: '331px', height: '3px', background: 'var(--gold)', width: '0px' });
  const P = [['/sp/vid_export_16x9.png', 1920, 1080], ['/sp/vid_export_9x16.png', 1080, 1920], ['/sp/vid_export_1x1.png', 1080, 1080]];
  const frames = P.map(([src, w, h], i) => { const f = $c('div', 'abs', el); const hh = 470, ww = hh * w / h; css(f, { width: ww + 'px', height: hh + 'px', borderRadius: '20px', overflow: 'hidden', boxShadow: '0 0 0 2px rgba(214,178,94,.5), 0 40px 90px rgba(0,0,0,.65)', background: `#fffdf6 url(${src}) center/cover` }); const lab = $c('div', 'abs en', f.parentNode); css(lab, { fontSize: '30px', fontWeight: 700, color: 'var(--gold)' }); lab.textContent = ['16 : 9', '9 : 16', '1 : 1'][i]; return { f, ww, hh, lab }; });
  return (lt) => {
    tb.update(lt, s.dur);
    st.forEach((c, i) => { popIn(c, seg(lt, 0.5 + i * 0.25, 1.0 + i * 0.25)); const act = lt > 1.0 + i * 0.55 && lt < 5.5; c.firstChild.style.background = act ? 'rgba(214,178,94,.3)' : 'transparent'; });
    conn.style.width = (eIO(seg(lt, 1.0, 3.8)) * 1160) + 'px';
    const out = eIO(seg(lt, 5.0, 5.8)); st.forEach(c => { c.style.opacity = 1 - out; }); conn.style.opacity = 1 - out;
    let x = 960 - (frames.reduce((a, f) => a + f.ww, 0) + 80) / 2;
    frames.forEach((fr, i) => {
      const p = seg(lt, 5.4 + i * 0.35, 6.3 + i * 0.35);
      css(fr.f, { left: x + 'px', top: (430 + (1 - eOut(p)) * 80) + 'px', opacity: eOut(p), transform: `scale(${lerp(0.9, 1, eBack(p))})`, backgroundPosition: `${50 + Math.sin(lt * 0.4 + i) * 8}% 50%` });
      css(fr.lab, { left: x + 'px', top: '935px', width: fr.ww + 'px', textAlign: 'center', opacity: eOut(seg(lt, 6.0 + i * 0.35, 6.6 + i * 0.35)) });
      x += fr.ww + 40;
    });
  };
});

/* 9. Personalize */
scene(8, (el, s) => {
  const tb = titleBlock(el, 120, 300, '08 · 打造你的風格', '顏色、背景、\n深淺主題、中英介面', 'Cursor · Background · Light / Dark · 中文 / EN', { w: 680 });
  const lap = laptop(el, 'custom', 820, 230, 1000);
  const sw = ['#d6b25e', '#3fc7b4', '#e0708a', '#7aa2ff'].map((c, i) => { const d = $c('div', 'swatch', el); css(d, { left: (120 + i * 120) + 'px', top: '760px', background: c }); return d; });
  return (lt) => {
    tb.update(lt, s.dur);
    const lp = eOut(seg(lt, 0.2, 1.0)); css(lap.wrap, { opacity: lp, transform: `translateX(${(1 - lp) * 100}px)` });
    sw.forEach((d, i) => { popIn(d, seg(lt, 1.0 + i * 0.12, 1.5 + i * 0.12), 0.5); });
    const ci = Math.floor(clamp((lt - 2.0) / 1.0, 0, 3.99)); sw.forEach((d, i) => { d.style.borderColor = i === ci && lt > 2 ? '#fff' : 'rgba(255,255,255,.18)'; d.style.boxShadow = i === ci && lt > 2 ? '0 0 0 6px rgba(255,255,255,.15)' : 'none'; });
    const fr = APP.custom; if (fr && fr.contentWindow && fr.contentWindow.document) {
      const w = fr.contentWindow, d = w.document;
      const col = ['#d6b25e', '#3fc7b4', '#e0708a', '#7aa2ff'][lt > 2 ? ci : 0];
      const inp = d.getElementById('cursorColor'); if (inp && inp.value !== col) { inp.value = col; inp.dispatchEvent(new w.Event('input', { bubbles: true })); }
      const wantLight = lt > 4.5, isLight = d.documentElement.classList.contains('light') || d.body.classList.contains('light') || d.documentElement.dataset.theme === 'light';
      if (wantLight !== !!w.__light) { const b = d.getElementById('themeToggle'); if (b) b.click(); w.__light = wantLight; }
      const wantEn = lt > 6.0; if (wantEn !== !!w.__en) { const b = d.getElementById('langToggle'); if (b) b.click(); w.__en = wantEn; }
      const st = d.getElementById('status'); const want = wantEn ? 'Piano ready (16 velocity layers)' : '鋼琴音色就緒(16 層力度)'; if (st && st.textContent !== want) st.textContent = want;
      appAt('custom', 3 + lt * 0.9);
    }
  };
});

/* 10. Every device */
scene(6, (el, s) => {
  const tb = titleBlock(el, 0, 70, '09 · 手機、平板、電腦都能用', '免安裝，打開網頁就能用', 'Runs in the browser · Add to Home Screen', { w: 1920, align: 'center' });
  const lap = laptop(el, 'main3', 330, 330, 1000);
  const ph = phone(el, 'phone', 1380, 300, 300);
  return (lt) => {
    tb.update(lt, s.dur);
    const lp = eOut(seg(lt, 0.3, 1.1)); css(lap.wrap, { opacity: lp, transform: `translateY(${(1 - lp) * 70}px)` });
    const pp = eOut(seg(lt, 0.7, 1.5)); css(ph.wrap, { opacity: pp, transform: `translateY(${(1 - pp) * 90}px) rotate(${(1 - pp) * 6}deg)` });
    appAt('main3', 8 + lt); appAt('phone', 8 + lt);
  };
});

/* 11. Outro — same layout as the HarmonyMap ending: logo, spaced Chinese subtitle, email, copyright, gold→teal rule */
scene(7.8, (el, s) => {
  const grid = $c('div', 'abs', el); css(grid, { inset: '0', backgroundImage: 'linear-gradient(rgba(214,178,94,.045) 1px, transparent 1px), linear-gradient(90deg, rgba(214,178,94,.045) 1px, transparent 1px)', backgroundSize: '64px 64px', WebkitMaskImage: 'radial-gradient(ellipse at 50% 45%, #000 30%, transparent 78%)' });
  const teal = $c('div', 'abs', el); css(teal, { right: '-260px', bottom: '-300px', width: '900px', height: '900px', borderRadius: '50%', background: 'radial-gradient(circle, rgba(63,150,150,.16), rgba(63,150,150,0) 65%)' });
  const block = $c('div', 'abs', el); css(block, { left: 0, top: 0, width: '1920px', height: '1080px' });
  const logo = $c('div', 'abs serif', block); css(logo, { left: 0, width: '1920px', top: '330px', textAlign: 'center', fontSize: '176px', fontWeight: 600, letterSpacing: '.06em', lineHeight: 1 });
  const letters = 'ScrollScore'.split('').map((ch, i) => { const sp = $c('span', '', logo, ch); css(sp, { display: 'inline-block' }); if (i < 6) css(sp, { background: 'linear-gradient(180deg, #ece5d5, #b9b1a0)', WebkitBackgroundClip: 'text', color: 'transparent' }); else css(sp, { color: '#c4974a' }); return sp; });
  const zh = $c('div', 'abs serif', block); css(zh, { left: 0, width: '1920px', top: '548px', textAlign: 'center', fontSize: '44px', fontWeight: 600, letterSpacing: '.42em', paddingLeft: '.42em', color: '#e6dece' }); zh.textContent = '捲動樂譜播放器';
  const mail = $c('div', 'abs en', block); css(mail, { left: 0, width: '1920px', top: '640px', textAlign: 'center', fontSize: '38px', fontWeight: 500, letterSpacing: '.03em', color: '#c4974a' }); mail.textContent = 'steventsaimusic@gmail.com';
  const copy = $c('div', 'abs', block); css(copy, { left: 0, width: '1920px', top: '712px', textAlign: 'center', fontSize: '28px', fontWeight: 400, color: '#6e6656' }); copy.textContent = '© 2026 Steven Tsai';
  const rule = $c('div', 'abs', el); css(rule, { left: 0, top: '982px', height: '3px', width: '0px', background: 'linear-gradient(90deg, #b8893f, #c4974a 45%, #5fa29b)' });
  return (lt) => {
    css(grid, { opacity: eOut(seg(lt, 0, 1.2)) });
    css(teal, { opacity: eOut(seg(lt, 0.2, 1.6)) });
    letters.forEach((sp, i) => { const p = seg(lt, 0.15 + i * 0.05, 0.95 + i * 0.05); sp.style.opacity = p; sp.style.transform = `translateY(${(1 - eOut(p)) * 46}px)`; sp.style.filter = `blur(${(1 - p) * 8}px)`; });
    const zp = seg(lt, 0.9, 1.8); css(zh, { opacity: eOut(zp), letterSpacing: lerp(0.7, 0.42, eOut(zp)) + 'em', paddingLeft: lerp(0.7, 0.42, eOut(zp)) + 'em' });
    const mp = seg(lt, 1.4, 2.1); css(mail, { opacity: eOut(mp), transform: `translateY(${(1 - eOut(mp)) * 18}px)` });
    const cp = seg(lt, 1.7, 2.4); css(copy, { opacity: eOut(cp), transform: `translateY(${(1 - eOut(cp)) * 14}px)` });
    rule.style.width = (eIO(seg(lt, 0.6, 2.4)) * 1920) + 'px';
    const fo = eIn(seg(lt, s.dur - 1.6, s.dur)); el.style.filter = `brightness(${1 - fo})`;
  };
});

/* ── timeline ── */
const XF = 0.6;   // crossfade seconds
let acc = 0; for (const s of SC) { s.start = acc; acc += s.dur; }
window.TOTAL = acc;
window.SCENES = SC.map(s => ({ start: s.start, dur: s.dur }));
window.setTime = function (t) {
  drawBg(t, 1 - eIn(seg(t, window.TOTAL - 1.6, window.TOTAL)));
  for (const s of SC) {
    const lt = t - s.start;
    const vis = lt > -XF && lt < s.dur + XF;
    if (!vis) { s.el.style.opacity = 0; s.el.style.visibility = 'hidden'; continue; }
    s.el.style.visibility = 'visible';
    const fin = s === SC[0] ? 1 : eIO(seg(lt, -XF / 2, XF / 2)), fout = s === SC[SC.length - 1] ? 1 : 1 - eIO(seg(lt, s.dur - XF / 2, s.dur + XF / 2));
    s.el.style.opacity = Math.min(fin, fout);
    s.el.style.transform = `scale(${1 + (1 - fin) * 0.03 - (1 - fout) * 0.03})`;
    s.update(clamp(lt, 0, s.dur));
  }
};
window.COMP_READY = true;
