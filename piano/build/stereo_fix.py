import numpy as np
from scipy.signal import stft, istft
def pan_gains(p):
    th = (p + 1) * np.pi / 4
    return np.cos(th) * np.sqrt(2), np.sin(th) * np.sqrt(2)
def mono_safe(x, sr, pan=0.0, side=0.45, nper=2048, gmax=3.0):
    """Energy-preserving mid (per STFT bin |M| := sqrt((|L|^2+|R|^2)/2), phase of L+R) so the mono sum never
    comb-cancels; side narrowed to `side`; mid placed at `pan`."""
    L, R = x[:, 0], x[:, 1]; n = len(L)
    _, _, Lz = stft(L, sr, nperseg=nper, noverlap=nper * 3 // 4, boundary='even', padded=True)
    _, _, Rz = stft(R, sr, nperseg=nper, noverlap=nper * 3 // 4, boundary='even', padded=True)
    M = (Lz + Rz) / 2; P = np.sqrt((np.abs(Lz) ** 2 + np.abs(Rz) ** 2) / 2)
    g = np.minimum(P / np.maximum(np.abs(M), 1e-12), gmax)
    _, m = istft(M * g, sr, nperseg=nper, noverlap=nper * 3 // 4, boundary=True)
    m = m[:n] if len(m) >= n else np.pad(m, (0, n - len(m)))
    # attack: keep the plain time-domain mid (no STFT smearing / pre-echo), crossfade to the energy-preserving mid
    a = np.abs(L + R); on = int(np.argmax(a > a.max() * 0.1))
    i0, i1 = min(n, on + int(0.015 * sr)), min(n, on + int(0.05 * sr))
    w = np.zeros(n); w[i1:] = 1
    if i1 > i0: w[i0:i1] = 0.5 - 0.5 * np.cos(np.linspace(0, np.pi, i1 - i0))
    m = (L + R) / 2 * (1 - w) + m * w
    s = (L - R) / 2 * side
    gl, gr = pan_gains(pan)
    y = np.stack([m * gl + s, m * gr - s], 1)
    # balance: make the channel RMS ratio follow the register pan (the AB pair's per-note imbalance jumps around)
    rl, rr = np.sqrt((y[:, 0] ** 2).mean()), np.sqrt((y[:, 1] ** 2).mean())
    want = gl / gr; k = want / (rl / rr)
    y[:, 0] *= np.sqrt(k); y[:, 1] /= np.sqrt(k)
    return y
