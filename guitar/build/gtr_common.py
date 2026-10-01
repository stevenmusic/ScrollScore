"""吉他取樣重建共用函式(steel_build.py / nylon_build.py)"""
import numpy as np
from scipy import signal
STRONG = False
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

