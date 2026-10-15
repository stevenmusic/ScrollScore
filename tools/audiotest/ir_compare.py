# 殘響 IR 比較:python3 ir_compare.py a.flac b.flac …
# 各倍頻程 EDT/T30、C80 與重心時間、左右相關性、單聲道相容、後段頻譜、殘響密度(Abel & Huang,1 = 完全擴散)、
# 尾端剩多少、聽得到的音量內的離散回聲(50ms 後、比前後中位數高 6dB 以上)
import sys, numpy as np, soundfile as sf
from scipy.signal import butter, sosfilt, sosfiltfilt
from scipy.special import erfc
BANDS = [125, 250, 500, 1000, 2000, 4000, 8000]
def bp(x, c, sr, ff=False):
    sos = butter(3, [c / 1.414, min(c * 1.414, sr / 2 - 100)], 'bandpass', fs=sr, output='sos')
    return (sosfiltfilt if ff else sosfilt)(sos, x, axis=0)
def schroeder(z):
    s = np.cumsum(z[::-1])[::-1]; return 10 * np.log10(s / s[0] + 1e-30)
def rt(s, sr, a, b):
    t = np.arange(len(s)) / sr; m = (s <= a) & (s >= b)
    if m.sum() < 10: return float('nan')
    p = np.polyfit(t[m], s[m], 1); return -60 / p[0]
def ned(m, sr, win=0.02):
    # Abel & Huang normalized echo density (1 = Gaussian, fully diffuse)
    w = int(win * sr); h = np.hanning(w); h /= h.sum(); out = []
    for i in range(0, len(m) - w, w // 4):
        seg = m[i:i + w]; sd = np.sqrt(np.sum(h * seg ** 2))
        out.append(np.sum(h * (np.abs(seg) > sd)) / erfc(1 / np.sqrt(2)))
    return np.array(out), w // 4
for p in sys.argv[1:]:
    x, sr = sf.read(p); m = x.mean(1)
    print('==', p.split('/')[-1], f'{len(x)/sr:.2f}s')
    row = {}
    for c in BANDS:
        z = bp(m, c, sr) ** 2; s = schroeder(z)
        row[c] = (rt(s, sr, 0, -10), rt(s, sr, -5, -35))
    print('  EDT ', ' '.join(f'{c}:{v[0]:.2f}' for c, v in row.items()))
    print('  T30 ', ' '.join(f'{c}:{v[1]:.2f}' for c, v in row.items()))
    e = m ** 2; i80 = int(0.08 * sr); i50 = int(0.05 * sr)
    print(f'  C80(reverb only) {10*np.log10(e[:i80].sum()/e[i80:].sum()):.1f} dB   ts(center time) {np.sum(np.arange(len(e))*e)/e.sum()/sr*1000:.0f} ms')
    corr = [np.corrcoef(*bp(x, c, sr, True).T)[0, 1] for c in BANDS]
    print('  L/R corr', ' '.join(f'{c}:{v:.2f}' for c, v in zip(BANDS, corr)))
    mono = [10 * np.log10(np.sum(bp(x.sum(1), c, sr) ** 2) / (2 * np.sum(bp(x, c, sr) ** 2))) for c in BANDS]
    print('  mono sum vs stereo (dB)', ' '.join(f'{c}:{v:+.1f}' for c, v in zip(BANDS, mono)))
    late = m[int(0.1 * sr):int(0.6 * sr)]; Y = np.abs(np.fft.rfft(late)) ** 2; f = np.fft.rfftfreq(len(late), 1 / sr)
    sp = [10 * np.log10(Y[(f >= c / 1.414) & (f < c * 1.414)].mean()) for c in BANDS + [16000]]
    print('  late spectrum re 1k', ' '.join(f'{c}:{v-sp[3]:+.1f}' for c, v in zip(BANDS + [16000], sp)))
    d, hop = ned(m, sr)
    t9 = np.argmax(d > 0.9) * hop / sr * 1000
    print(f'  echo density: reaches 0.9 at {t9:.0f} ms; mean 0.1-1.0s {d[int(0.1*sr/hop):int(1.0*sr/hop)].mean():.2f}; at 20/50/100ms',
          ' '.join(f'{d[int(t*sr/hop)]:.2f}' for t in (0.02, 0.05, 0.1)))
    # 尾端還剩多少(相對各頻段最大短時能量)
    tail = []
    for c in BANDS:
        z = np.convolve(bp(m, c, sr) ** 2, np.ones(2400) / 2400, 'same')
        tail.append(10 * np.log10(z[-int(0.3 * sr)] / z.max()))
    print('  level 0.3s before end (dB re max)', ' '.join(f'{c}:{v:.0f}' for c, v in zip(BANDS, tail)))
    # 離散回聲:50ms 後,5ms 能量比前後 40ms 中位數高 > 6dB
    env = np.convolve(e, np.ones(240) / 240, 'same'); peaks = []; mx = env.max()
    for i in range(int(0.05 * sr), len(env) - 2000, 120):
        loc = np.median(env[i - 1920:i + 1920])
        if env[i] > 4 * loc and env[i] > mx * 1e-5: peaks.append((round(i / sr * 1000), round(10 * np.log10(env[i] / mx))))
    print('  discrete echoes (ms, dB re max; >6dB above local, after 50ms, within 50dB of max):', peaks[:12], f'({len(peaks)})')
