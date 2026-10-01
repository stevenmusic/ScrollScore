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

def f0_cents(x, sr, midi):
    ft = 440 * 2 ** ((midi - 69) / 12)
    seg = x[int(.25 * sr):int(1.5 * sr)]; seg = seg - seg.mean()
    n = 1 << 20
    S = np.abs(np.fft.rfft(seg * np.hanning(len(seg)), n))
    best = None
    for c in np.arange(-100, 100.1, 1):
        f = ft * 2 ** (c / 1200); s = 0
        for h in range(1, 6):
            k = int(round(h * f * n / sr))
            if k + 3 < len(S): s += np.log(S[k - 3:k + 4].max() + 1e-12)
        if best is None or s > best[0]: best = (s, c)
    # 基音與第 2 諧波各自拋物線內插,取平均(避免高次諧波的非諧和性)
    ests = []
    for h in (1, 2):
        f = h * ft * 2 ** (best[1] / 1200); k = int(round(f * n / sr)); k = k - 8 + np.argmax(S[k - 8:k + 9])
        y0, y1, y2 = np.log(S[k - 1:k + 2]); d = 0.5 * (y0 - y2) / (y0 - 2 * y1 + y2)
        ests.append(1200 * np.log2((k + d) * sr / n / h / ft))
    return float(np.mean(ests))

def kweight(x, sr):
    # ITU-R BS.1770 K 加權(兩段 biquad,依取樣率重算)
    f0, G, Q = 1681.974450955533, 3.999843853973347, 0.7071752369554196
    K = np.tan(np.pi * f0 / sr); Vh = 10 ** (G / 20); Vb = Vh ** 0.4996667741545416
    a0 = 1 + K / Q + K * K
    b = [(Vh + Vb * K / Q + K * K) / a0, 2 * (K * K - Vh) / a0, (Vh - Vb * K / Q + K * K) / a0]
    a = [1, 2 * (K * K - 1) / a0, (1 - K / Q + K * K) / a0]
    y = signal.lfilter(b, a, x)
    f0, Q = 38.13547087602444, 0.5003270373238773
    K = np.tan(np.pi * f0 / sr)
    a = [1, 2 * (K * K - 1) / (1 + K / Q + K * K), (1 - K / Q + K * K) / (1 + K / Q + K * K)]
    return signal.lfilter([1, -2, 1], a, y)

def loud(x, sr):
    y = kweight(x, sr); return -0.691 + 10 * np.log10(np.mean(y ** 2) + 1e-20)

def denoise(x, sr):
    nper = 1024; hop = 256
    f, t, Z = signal.stft(x, sr, nperseg=nper, noverlap=nper - hop)
    M = np.abs(Z)
    tail = M[:, int(M.shape[1] * 0.6):]
    N = np.percentile(tail, 20, axis=1, keepdims=True) * 1.3           # 每個頻格的雜訊估計
    snr = M / (N + 1e-12)
    g = np.clip((snr - 1.0) / 1.0, 0, 1) ** 1.5                         # snr ≤1 全壓、≥2 不動
    g = np.maximum(g, 10 ** (-24 / 20))
    g = signal.convolve2d(g, np.ones((3, 5)) / 15, mode='same', boundary='symm')
    _, y = signal.istft(Z * g, sr, nperseg=nper, noverlap=nper - hop)
    return y[:len(x)]

def excite(x, sr):
    sos_b = signal.butter(4, [2500 if STRONG else 3500, 7500], 'bandpass', fs=sr, output='sos')
    band = signal.sosfiltfilt(sos_b, x)
    h = np.abs(band)
    sos_h = signal.butter(8, 8000, 'highpass', fs=sr, output='sos')
    h = signal.sosfiltfilt(sos_h, h)
    seg = slice(0, int(sr * 1.0))
    f, P = signal.welch(x[seg], sr, nperseg=2048)
    _, Ph = signal.welch(h[seg], sr, nperseg=2048)
    def dens(P, lo, hi): m = (f >= lo) & (f < hi); return 10 * np.log10(P[m].mean() + 1e-30)
    d1, d2 = dens(P, 4000, 5500), dens(P, 5500, 7300)
    slope = min((d2 - d1) / np.log2(6350 / 4700), -4.5 if STRONG else -6.0)                 # dB/八度,最平也只到 -6
    target = d2 + slope * np.log2(10000 / 6350) - (0.0 if STRONG else 3.0)                   # 8~12k 的目標密度
    cur = dens(Ph, 8500, 12000)
    return x + h * 10 ** ((target - cur) / 20), round(target - cur, 1)

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
