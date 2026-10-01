"""量測 render.mjs 的輸出:整體響度(LUFS)、真峰值、LRA、軟削波作用時間、響度壓縮量。
用法:python3 analyze.py a.wav [b.wav ...]"""
import sys, numpy as np, soundfile as sf, pyloudnorm as pyln
from scipy.signal import resample_poly

def short_term(meter_rate, x, win=3.0, hop=0.1):
    m = pyln.Meter(meter_rate, block_size=0.4)
    # K 加權後算 3 秒視窗響度(EBU short-term)
    xf = x.copy()
    for f in m._filters.values(): xf = f.apply_filter(xf)
    p = (xf ** 2).sum(axis=1) if xf.ndim > 1 else xf ** 2
    n, h = int(win * meter_rate), int(hop * meter_rate)
    cs = np.concatenate([[0], np.cumsum(p)])
    idx = np.arange(0, len(p) - n, h)
    ms = (cs[idx + n] - cs[idx]) / n
    return -0.691 + 10 * np.log10(ms + 1e-12)

def lra(st):
    st = st[st > -70]
    if len(st) < 3: return 0.0
    rel = 10 * np.log10(np.mean(10 ** (st / 10))) - 20
    st = st[st > rel]
    return float(np.percentile(st, 95) - np.percentile(st, 10))

def analyze(path):
    x, sr = sf.read(path, always_2d=True)
    out = x[:, :2]
    meter = pyln.Meter(sr)
    I = meter.integrated_loudness(out)
    tp = 20 * np.log10(np.abs(resample_poly(out, 4, 1, axis=0)).max() + 1e-12)
    st = short_term(sr, out)
    knee = (np.abs(out) > 0.708).any(axis=1).mean() * 100   # 軟削波起彎點 −3dBFS 以上的時間比例
    corr = np.corrcoef(out[:, 0], out[:, 1])[0, 1]
    r = dict(file=path.split('/')[-1], LUFS=round(I, 1), TP=round(tp, 2), LRA=round(lra(st), 1),
             STmax=round(float(st.max()), 1), clipPct=round(knee, 3), LRcorr=round(corr, 2))
    if x.shape[1] >= 4:
        pre = x[:, 2:4]
        if np.abs(pre).max() > 1e-6:
            Ipre = meter.integrated_loudness(pre)
            r['preLUFS'] = round(Ipre, 1); r['preLRA'] = round(lra(short_term(sr, pre)), 1)
            r['prePk'] = round(20 * np.log10(np.abs(pre).max()), 1)
    return r

if __name__ == '__main__':
    for p in sys.argv[1:]:
        print(analyze(p))
