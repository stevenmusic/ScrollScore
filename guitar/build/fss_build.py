"""FSS Steel-String Acoustic Guitar (FreePats 2020-05-21) -> guitar/steel/*.flac + manifest.json

來源:https://freepats.zenvoid.org/Guitar/steel-acoustic-guitar.html
  FSS-SteelStringGuitar-SFZ-20200521.tar.xz(FlameStudios「FS Seagull Steel String Acoustic Guitar」的子集)
授權:GPL-3.0-or-later + FreePats 音色例外條款(用這些聲音做的音樂不受 GPL 約束);處理後的檔案同授權。

E2~C6 每個半音一個錄音(缺 F#3、A5,用相鄰的),HV(重)42 個 + MV(中)17 個,44.1kHz 單聲道。
每個檔:
1. 量音準,FFT 重取樣校正到 0 音分(同時 44100 → 48000Hz)
2. 起音前留 5ms;頻譜降噪(同其他吉他)
3. 音色連續性:原始錄音 B3 以上比以下亮很多(8kHz 以上差約 20dB),同一層裡相鄰的音也會忽亮忽暗。
   MV/HV 兩層各自對音高做線性迴歸(2.5~8kHz、8kHz 以上兩個頻段占總能量的比例),
   每個音偏離趨勢的部分修掉 70%(2.5kHz、8kHz 兩段高頻架,最多 ±9dB),保留「越高越亮、輕彈較暗」
4. 前 0.5 秒 K 加權響度對齊 -18 LKFS(大小聲交給播放時的力度曲線)
5. 尾巴低於峰值 -66dB 截掉,最後 0.3 秒 cos² 淡出
用法:python3 fss_build.py <FSS-SteelStringGuitar-SFZ-20200521 目錄> <輸出目錄>
"""
import sys, os, re, json, glob
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, soundfile as sf
from scipy import signal
from gtr_common import f0_cents, loud, denoise

SRC, OUT = sys.argv[1], sys.argv[2]
SR_OUT = 48000
os.makedirs(OUT, exist_ok=True)
NAMES = ['C', 'Cs', 'D', 'Ds', 'E', 'F', 'Fs', 'G', 'Gs', 'A', 'As', 'B']

def shelf(x, sr, f0, gain_db):
    if abs(gain_db) < 0.05: return x
    A = 10 ** (gain_db / 40); w = 2 * np.pi * f0 / sr; al = np.sin(w) / 2 * np.sqrt(2); c = np.cos(w); sA = 2 * np.sqrt(A) * al
    b = [A * ((A + 1) + (A - 1) * c + sA), -2 * A * ((A - 1) + (A + 1) * c), A * ((A + 1) + (A - 1) * c - sA)]
    a = [(A + 1) - (A - 1) * c + sA, 2 * ((A - 1) - (A + 1) * c), (A + 1) - (A - 1) * c - sA]
    return signal.lfilter(b, a, x)

def bands(x, sr):
    f, P = signal.welch(x[:int(0.3 * sr)], sr, nperseg=2048)
    tot = P[f > 50].sum()
    return 10 * np.log10(P[(f > 2500) & (f < 8000)].sum() / tot), 10 * np.log10(P[f > 8000].sum() / tot)

files = sorted(glob.glob(os.path.join(SRC, 'samples', '*.wav')))
info = []
for p in files:
    m = re.match(r'(HV|MV)_(\d+)\.wav$', os.path.basename(p))
    x, sr = sf.read(p); x = x if x.ndim == 1 else x.mean(1)
    info.append(dict(path=p, layer=m.group(1), midi=int(m.group(2)), x=x, sr=sr, b=bands(x, sr)))
# 各層對音高的趨勢
fix = {}
for layer in ('MV', 'HV'):
    rows = [r for r in info if r['layer'] == layer]
    ms = np.array([r['midi'] for r in rows])
    for k in (0, 1):
        v = np.array([r['b'][k] for r in rows]); p = np.polyfit(ms, v, 1)
        for r in rows: fix.setdefault(id(r), [0, 0])[k] = float(np.clip(-0.7 * (r['b'][k] - np.polyval(p, r['midi'])), -9, 9))

man = {'source': 'FSS Steel-String Acoustic Guitar (FreePats 2020-05-21, samples by Gary Campion / FlameStudios), GPL-3.0-or-later with the FreePats sound exception',
       'mode': 'nearest', 'sr': SR_OUT, 'velRanges': [[1, 85], [86, 127]], 'ampVeltrack': 98, 'samples': {}}
for r in info:
    x, sr, root = r['x'], r['sr'], r['midi']
    c = f0_cents(x, sr, root)
    n2 = int(round(len(x) * SR_OUT / sr * 2 ** (c / 1200))); pad = 4096
    y = signal.resample(np.concatenate([x, np.zeros(pad)]), n2 + int(round(pad * SR_OUT / sr * 2 ** (c / 1200))))[:n2]
    on = int(np.argmax(np.abs(y) > 0.02 * np.abs(y).max()))
    y = y[max(0, on - int(0.005 * SR_OUT)):]
    y = denoise(y, SR_OUT)
    g1, g2 = fix[id(r)]
    y = shelf(y, SR_OUT, 2500, g1)
    y = shelf(y, SR_OUT, 8000, g2 - g1)          # 8kHz 以上已經跟著 2.5kHz 的架子動了 g1,這裡補差額
    y = y * 10 ** ((-18 - loud(y[:int(0.5 * SR_OUT)], SR_OUT)) / 20)
    w = int(0.02 * SR_OUT); nb = len(y) // w
    env = 20 * np.log10(np.sqrt((y[:nb * w].reshape(nb, w) ** 2).mean(1)) + 1e-12)
    above = np.where(env > env.max() - 66)[0]
    y = y[:min(len(y), (above[-1] + 1) * w + int(0.3 * SR_OUT))]
    fd = min(int(0.3 * SR_OUT), len(y) // 3); y[-fd:] *= np.cos(np.linspace(0, np.pi / 2, fd)) ** 2
    peak = float(np.abs(y).max())
    if peak > 0.99: y *= 0.99 / peak; peak = 0.99
    L = 1 if r['layer'] == 'MV' else 2
    name = f'fs-{NAMES[root % 12]}{root // 12 - 1}-L{L}'
    sf.write(os.path.join(OUT, name + '.flac'), y.astype(np.float32), SR_OUT, subtype='PCM_16')
    man['samples'][name] = {'root': root, 'L': L, 'rr': 1, 'frames': len(y), 'tuneFix': round(-c, 1), 'tone': [round(g1, 1), round(g2, 1)]}
    print(f'{name:12s} tune {c:+5.1f}c  tone 2.5k {g1:+5.1f} 8k {g2:+5.1f}  len {len(y) / SR_OUT:4.1f}s')
json.dump(man, open(os.path.join(OUT, 'manifest.json'), 'w'), indent=1)
