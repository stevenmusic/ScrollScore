"""Ella Gitauru 5 (Malaclypse the Younger, BJAM 5.25.06, MIT) -> guitar/steel/*.flac + manifest.json

原始檔:16kHz 單聲道 OGG,每個檔都已被原作者正規化到峰值 0dBFS。
真正的錄音只有 6E/5A/4D/2B 四條空弦 × mp/mf/f/ff(另有 2B 的第二組 (z) 與 B5 的 15va 短取樣);
「每 2 格」的檔案(2B-mf05 …)是空弦錄音加濾波複製出來的(與空弦相干性 0.9,真正不同的錄音只有 0.6),
所以這裡只收真錄音,把位的音色改在播放時用濾波器做(見 index.html 的 gtrFretTone)。

每個檔:
1. 量音準(諧波擬合),用 FFT 重取樣校正到 0 音分
2. 起音前留 5ms
3. 頻譜降噪(每個頻格用後段的最小統計估雜訊,低於雜訊 2 倍才壓,最多壓 -24dB,時間/頻率平滑)
4. (--excite)高頻激勵:3.5~7.5kHz 帶通 → 全波整流 → 8kHz 高通,音量照 4~7.5kHz 的頻譜斜率外插、再低 3dB
5. 音量對齊:每個檔前 0.5 秒的 K 加權響度對齊到 -18 LKFS(大小聲交給播放時的力度曲線)
6. 尾巴低於峰值 -66dB 之後截掉,最後 0.4 秒 cos² 淡出
用法:python3 steel_build.py <Ella G5 目錄> <輸出目錄> [--excite]
"""
import sys, os, json, glob
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, soundfile as sf
from scipy import signal

SRC, OUT = sys.argv[1], sys.argv[2]
EXCITE = '--excite' in sys.argv or '--excite-strong' in sys.argv
STRONG = '--excite-strong' in sys.argv
SR_IN = 16000
SR_OUT = 32000 if EXCITE else 16000
os.makedirs(OUT, exist_ok=True)

STRINGS = {'6E': 40, '5A': 45, '4D': 50, '2B': 59}
LAYERS = ['mp', 'mf', 'f', 'ff']

from gtr_common import f0_cents, kweight, loud, denoise
import gtr_common
gtr_common.STRONG = STRONG
excite = gtr_common.excite

man = {'source': 'Ella Gitauru 5 (Malaclypse the Younger, BJAM 5.25.06), MIT License',
       'sr': SR_OUT, 'excite': EXCITE, 'velRanges': [[1, 48], [49, 91], [92, 119], [120, 127]],
       'ampVeltrack': 98, 'samples': {}}
jobs = []
for s, root in STRINGS.items():
    for i, L in enumerate(LAYERS):
        jobs.append((f'{s}-{L}00.ogg', f'st-{s}-L{i + 1}', root, s, i + 1, 1))
        if s == '2B': jobs.append((f'2B-{L}(z).ogg', f'st-{s}-L{i + 1}-2', root, s, i + 1, 2))
for i, L in enumerate(LAYERS):
    jobs.append((f'2B-{L}(z) 15va.ogg', f'st-B5-L{i + 1}', 83, 'B5', i + 1, 1))

for src, name, root, s, L, rr in jobs:
    x, sr = sf.read(os.path.join(SRC, src)); x = x if x.ndim == 1 else x.mean(1)
    assert sr == SR_IN
    c = f0_cents(x, sr, root)
    if SR_OUT != sr: x = signal.resample_poly(x, SR_OUT // sr, 1)
    # 音準校正:偏高 c 音分 → 拉長 2^(c/1200) 倍
    n2 = int(round(len(x) * 2 ** (c / 1200)))
    x = signal.resample(np.concatenate([x, np.zeros(4096)]), n2 + int(round(4096 * 2 ** (c / 1200))))[:n2]
    on = int(np.argmax(np.abs(x) > 0.02 * np.abs(x).max()))
    x = x[max(0, on - int(0.005 * SR_OUT)):]
    x = denoise(x, SR_OUT)
    ex_db = None
    if EXCITE: x, ex_db = excite(x, SR_OUT)
    lu = loud(x[:int(0.5 * SR_OUT)], SR_OUT)
    x = x * 10 ** ((-18 - lu) / 20)
    w = int(0.02 * SR_OUT); nb = len(x) // w
    env = 20 * np.log10(np.sqrt((x[:nb * w].reshape(nb, w) ** 2).mean(1)) + 1e-12)
    pk = env.max(); above = np.where(env > pk - 66)[0]
    end = min(len(x), (above[-1] + 1) * w + int(0.4 * SR_OUT))
    x = x[:end]; fd = int(0.4 * SR_OUT)
    x[-fd:] *= np.cos(np.linspace(0, np.pi / 2, fd)) ** 2
    peak = float(np.abs(x).max())
    if peak > 0.99: x *= 0.99 / peak; peak = 0.99
    sf.write(os.path.join(OUT, name + '.flac'), x.astype(np.float32), SR_OUT, subtype='PCM_16')
    man['samples'][name] = {'root': root, 'string': s, 'L': L, 'rr': rr, 'frames': len(x),
                            'tuneFix': round(-c, 1), 'peak': round(20 * np.log10(peak), 1)}
    print(f'{name:14s} {src:22s} tune {c:+5.1f}c  len {len(x) / SR_OUT:5.1f}s  peak {20 * np.log10(peak):5.1f}dB' + (f'  excite {ex_db:+.1f}dB' if EXCITE else ''))
json.dump(man, open(os.path.join(OUT, 'manifest.json'), 'w'), indent=1)
