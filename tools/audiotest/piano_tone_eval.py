"""鋼琴音色校正:用 App 的鋼琴取樣與播放規則「彈」MAESTRO 真人演奏的 MIDI,跟同一份演奏的真實 Yamaha 錄音逐音比較。

用法:python3 piano_tone_eval.py <資料目錄> <設定.json> [秒數=70]
  資料目錄裡放成對的 <曲名>.flac(MAESTRO 錄音)與 <曲名>.mid(同一份演奏的 MIDI),例如 ASAP 對應到的
  Bach BWV846、Rachmaninoff Op.23-4、Schubert D.899-2/3、Chopin Op.10-12、Ballade 1/2(MAESTRO v3 只拿來測試,不放 repo)
  設定.json:{"名稱": 參數, ...},參數見 DEFAULT(對應 index.html 的 PIANO_TONE / PIANO_EQ);{"voice": false} = 不加逐音音色

輸出(每組設定,第一列是真實錄音):
  bright  各力度區間(1-44 / 45-64 / 65-84 / 85-127)單獨的音新加入能量中 2kHz 以上的比例(dB,越接近 0 越亮)
  atk     起音 0~30ms 對 30~120ms 的 2~8kHz 能量比(琴槌敲弦那一下的亮度)
  brRng   力度 30→110 的亮度變化;loud = 力度 30→110 的音量變化
  1/3 八度頻譜(250~1000Hz 對齊)跟真實錄音的差
模擬是乾聲(不含殘響、壓縮、限幅、踏板共鳴、放鍵聲),只比音色"""
import sys, os, json, numpy as np, soundfile as sf, mido
from multiprocessing import Pool
from scipy.signal import lfilter, resample_poly
P = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../piano/')
SR = 48000
DEFAULT = dict(presF=2000, presLo=-10, presHi=5, presV0=45, presV1=105, airF=6500, airLo=4, airHi=21, airExp=1.4,
               trAmt=12, trTau=0.02, bus=[['peq', 450, -2, 1.0], ['peq', 3300, -4.5, 1.1], ['low', 100, 1.5]])
man = json.load(open(P + 'manifest.json'))
NAMES = ["C", "Cs", "D", "Ds", "E", "F", "Fs", "G", "Gs", "A", "As", "B"]
nn = lambda m: NAMES[m % 12] + str(m // 12 - 1)
center = lambda m: max(21, min(108, 21 + 3 * round((m - 21) / 3)))
def layer(v):
    for i, (a, b) in enumerate(man['velRanges']):
        if v <= b + 0.5: return i + 1
    return 16
velgain = lambda v: 0.015 + 0.985 * (max(1, min(127, v)) / 127) ** 2
def dtau(m): return 0.16 - (m - 21) / 27 * 0.06 if m <= 48 else (0.10 - (m - 48) / 24 * 0.04 if m <= 72 else max(0.045, 0.06 - (m - 72) / 16 * 0.015))
_cache = {}
def samp(c, L):
    k = f'{nn(c)}-v{L}'
    if k not in _cache: _cache[k] = sf.read(P + f'pf-{k}.flac')[0]
    return _cache[k]
def notes_from_midi(path, sec):
    t = 0; on = {}; out = []; ped = []; pdown = None
    for msg in mido.MidiFile(path):
        t += msg.time
        if t > sec + 10: break
        if msg.type == 'note_on' and msg.velocity > 0: on[msg.note] = (t, msg.velocity)
        elif msg.type in ('note_off', 'note_on') and msg.note in on:
            s, v = on.pop(msg.note); out.append((msg.note, v, s, t))
        elif msg.type == 'control_change' and msg.control == 64:
            if msg.value >= 64 and pdown is None: pdown = t
            elif msg.value < 64 and pdown is not None: ped.append((pdown, t)); pdown = None
    return [n for n in out if n[2] < sec], ped
def shelf(f, g, kind='high'):   # Web Audio 的 highshelf/lowshelf(Audio EQ Cookbook,S = 1)
    A = 10 ** (g / 40); w = 2 * np.pi * f / SR; c = np.cos(w); al = np.sin(w) / 2 * np.sqrt(2); sA = 2 * np.sqrt(A) * al
    if kind == 'high':
        b = [A * ((A + 1) + (A - 1) * c + sA), -2 * A * ((A - 1) + (A + 1) * c), A * ((A + 1) + (A - 1) * c - sA)]; a = [(A + 1) - (A - 1) * c + sA, 2 * ((A - 1) - (A + 1) * c), (A + 1) - (A - 1) * c - sA]
    else:
        b = [A * ((A + 1) - (A - 1) * c + sA), 2 * A * ((A - 1) - (A + 1) * c), A * ((A + 1) - (A - 1) * c - sA)]; a = [(A + 1) + (A - 1) * c + sA, -2 * ((A - 1) + (A + 1) * c), (A + 1) + (A - 1) * c - sA]
    return np.array(b) / a[0], np.array(a) / a[0]
def peq(f, g, q):
    A = 10 ** (g / 40); w = 2 * np.pi * f / SR; al = np.sin(w) / (2 * q); c = np.cos(w)
    b = [1 + al * A, -2 * c, 1 - al * A]; a = [1 + al / A, -2 * c, 1 - al / A]; return np.array(b) / a[0], np.array(a) / a[0]
def tone(v, p):
    gp = p['presLo'] + (p['presHi'] - p['presLo']) * np.clip((v - p['presV0']) / (p['presV1'] - p['presV0']), 0, 1)
    return gp, p['airLo'] + (p['airHi'] - p['airLo']) * (max(1, min(127, v)) / 127) ** p['airExp'], p['trAmt'] * max(1, v) / 127
def render(midi, sec, p):
    notes, ped = notes_from_midi(midi, sec)
    y = np.zeros((int((sec + 12) * SR), 2))
    for m, v, s, e in notes:
        c = center(m); x = samp(c, layer(v)); rate = 2 ** ((m - c + man['tune'].get(str(m), 0) / 100) / 12)
        damp = next((b for a, b in ped if a <= e < b), e)
        if m >= 89: damp = 1e9
        n = min(int(len(x) / rate), int((damp - s + 7 * dtau(m)) * SR) if damp < 1e8 else int(len(x) / rate))
        idx = np.arange(n) * rate
        seg = np.stack([np.interp(idx, np.arange(len(x)), x[:, ch]) for ch in (0, 1)], 1) * 1.5 * velgain(v)
        t = np.arange(n) / SR; d0 = damp - s
        if d0 < n / SR: seg *= np.where(t < d0, 1, np.exp(-(t - d0) / dtau(m)))[:, None]
        if p.get('voice', True):
            gp, ga, tr = tone(v, p)
            b, a = shelf(p['airF'], ga); seg = lfilter(b, a, seg, axis=0)
            b, a = shelf(p['presF'], gp); lo = lfilter(b, a, seg, axis=0)
            if tr > 0.05:   # 起音:濾波器增益從 gp+tr 以 trTau 回到 gp(近似成兩個濾波結果交叉淡化)
                b, a = shelf(p['presF'], gp + tr); hi = lfilter(b, a, seg[:int(0.2 * SR)], axis=0)
                env = np.exp(-t[:len(hi)] / p['trTau'])[:, None]; lo[:len(hi)] = env * hi + (1 - env) * lo[:len(hi)]
            seg = lo
        i0 = int(s * SR); y[i0:i0 + n] += seg[:len(y) - i0]
    for f in p['bus']:
        b, a = peq(f[1], f[2], f[3]) if f[0] == 'peq' else shelf(f[1], f[2], f[0]); y = lfilter(b, a, y, axis=0)
    return y[:int((sec + 6) * SR)].mean(1), notes
def feats(x, notes):
    """單獨的音(前 150ms、後 250ms 沒有別的音,G3~C6):[音, 力度, 新增能量 dB, 2kHz 以上比例 dB, 起音 dB]"""
    N = int(0.12 * SR); win = np.hanning(N); f = np.fft.rfftfreq(N, 1 / SR)
    ons = sorted(n[2] for n in notes); out = []
    def hfe(z):
        Z = np.abs(np.fft.rfft(z, 8192)) ** 2; ff = np.fft.rfftfreq(8192, 1 / SR); return Z[(ff > 2000) & (ff < 8000)].sum() / len(z)
    for m, v, s, e in notes:
        if not (55 <= m <= 84) or any(0 < s - o < 0.15 or 0 < o - s < 0.25 for o in ons): continue
        i = int((s - 0.005) * SR)
        if i - N < 0 or i + N > len(x): continue
        add = np.clip(np.abs(np.fft.rfft(x[i:i + N] * win)) ** 2 - np.abs(np.fft.rfft(x[i - N:i] * win)) ** 2, 0, None)
        tot = add.sum()
        if tot <= 0: continue
        out.append((m, v, 10 * np.log10(tot), 10 * np.log10(add[f > 2000].sum() / tot + 1e-9),
                    10 * np.log10(hfe(x[i:i + int(0.03 * SR)]) / (hfe(x[i + int(0.03 * SR):i + N]) + 1e-20) + 1e-12)))
    return np.array(out).reshape(-1, 5)
F3 = [50 * 2 ** (i / 3) for i in range(25)]
def ltas(m):
    N = 8192; f = np.fft.rfftfreq(N, 1 / SR); S = np.zeros(len(f))
    for k in range(0, len(m) - N, N // 2): S += np.abs(np.fft.rfft(m[k:k + N] * np.hanning(N))) ** 2
    b = np.array([10 * np.log10(S[(f >= c / 2 ** (1 / 6)) & (f < c * 2 ** (1 / 6))].sum() + 1e-20) for c in F3])
    return b - np.mean([b[i] for i, c in enumerate(F3) if 250 <= c <= 1000])
def real_one(a):
    d, name, sec = a
    x, sr = sf.read(f'{d}/{name}.flac', always_2d=True); x = resample_poly(x[:int(sec * sr)].mean(1), SR, sr)
    notes, _ = notes_from_midi(f'{d}/{name}.mid', sec); return feats(x, notes), ltas(x)
def sim_one(a):
    d, name, sec, p = a
    y, notes = render(f'{d}/{name}.mid', sec, p); y = y[:int(sec * SR)]; return feats(y, notes), ltas(y)
def summarize(R):
    F = np.vstack([r[0] for r in R]); v = F[:, 1]
    bins = [(1, 45), (45, 65), (65, 85), (85, 128)]
    return dict(bright=[float(np.median(F[(v >= a) & (v < b), 3])) for a, b in bins], n=len(F), attack=float(np.median(F[:, 4])),
                range=float(np.polyfit(v, F[:, 3], 1)[0] * 80), loud=float(np.polyfit(v, F[:, 2], 1)[0] * 80), ltas=np.mean([r[1] for r in R], 0))
if __name__ == '__main__':
    d, cfg = sys.argv[1], json.load(open(sys.argv[2])); sec = float(sys.argv[3]) if len(sys.argv) > 3 else 70
    names = sorted(os.path.splitext(f)[0] for f in os.listdir(d) if f.endswith('.flac') and os.path.exists(f'{d}/{os.path.splitext(f)[0]}.mid'))
    with Pool(min(8, len(names))) as pool:
        res = {'real': summarize(pool.map(real_one, [(d, n, sec) for n in names]))}
        for k, p in cfg.items(): res[k] = summarize(pool.map(sim_one, [(d, n, sec, {**DEFAULT, **p}) for n in names]))
    idx = [i for i, c in enumerate(F3) if c >= 1000]
    print(f"{len(names)} 首、{res['real']['n']} 個單獨的音")
    print('%-10s %27s %5s %6s %5s | ' % ('', 'bright pp / mp / mf / f', 'atk', 'brRng', 'loud') + ' '.join('%6.0f' % F3[i] for i in idx))
    for k, r in res.items():
        lt = r['ltas'] if k == 'real' else r['ltas'] - res['real']['ltas']
        print('%-10s %27s %5.1f %6.1f %5.1f | ' % (k, ' '.join('%6.1f' % b for b in r['bright']), r['attack'], r['range'], r['loud']) + ' '.join('%6.1f' % lt[i] for i in idx))
