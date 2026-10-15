"""鋼琴殘響用的真實音樂廳脈衝響應:python3 piano/build/hall_detmold.py <DetmoldSRIR 解壓目錄> [輸出.flac,預設 piano/hall.flac] [S2] [R57]

來源:Open Database of Spatial Room Impulse Responses at Detmold University of Music
  (Amengual Garí, Sahin, Eddy, Kob, AES 149th Convention 2020;https://zenodo.org/records/4116247,CC BY 4.0)
  Set C:德國 Detmold 音樂大學音樂廳(Konzerthaus,約 600 席,空廳)真實量測,
  音源 Neumann KH 120 A(平直 EQ)放在舞台,接收點同時有 NTi M2010 全指向 + Schoeps CCM8 8 字形
  (8 字形朝左右、零點對著舞台,依 ISO 3382-1 校正過靈敏度;實測後段 8 字形/全指向 −4dB ≈ 擴散聲場理論值 −4.8dB)。
  預設 S2(舞台前排、中線左邊 2m,鋼琴常放的位置)→ R57(第三排中間,離音源約 8m)。比過 S2/S3 × R10/R57/R62,
  各頻段殘響時間、左右相關性都差不多,R57 的早期擴散最均勻(殘響密度 20ms 就到 0.9)。

處理(以下是對原始資料的修改):
  1. 全指向 + 8 字形組成 M/S 立體聲:左 = M + k·S、右 = M − k·S(8 字形正極朝左:觀眾看過去舞台左邊的 S1 到中間座位,
     8 字形與全指向的直達聲同相;右邊的 S4 反相)。k = 1.2:250Hz~4kHz 左右相關性跟模擬版差不多(寬度不變);
     單聲道(左+右)= 純全指向,完全不會抵消
  2. 補償量測喇叭的高頻:同一音源到數個座位的直達聲(1ms 前 ~ 2.5ms 後)平均頻譜,2kHz 以上比 1kHz 低多少就補回多少(上限 +6dB,
     倍頻程平滑、零相位)。KH 120 A 軸上是平的,直達聲窗太短、低頻量不準,所以低頻不動
  3. 直達聲拿掉(App 的取樣本身就是近距離的直達聲),以直達聲到達時間為 0(預延遲 0),保留之後的早期反射與殘響
  4. 尾巴延長(見下面程式說明):原始檔只錄到直達聲後約 1.45 秒,高頻更早碰到量測底噪
  5. 48kHz 立體聲 16-bit FLAC,峰值 0.9
結果(tools/audiotest/ir_compare.py):T30 125Hz 1.96 / 500 1.52 / 1k 1.51 / 2k 1.42 / 4k 1.29 / 8k 0.90 秒,殘響密度 20ms 到 0.9(模擬版 190ms),
聽得到的音量內沒有離散回聲(模擬版 0.89~0.97 秒有 −37dB 的平行牆顫動回聲)
"""
import sys, os, numpy as np, soundfile as sf
ROOT = sys.argv[1]
OUT = sys.argv[2] if len(sys.argv) > 2 else 'piano/hall.flac'
SRC = sys.argv[3] if len(sys.argv) > 3 else 'S2'
REC = sys.argv[4] if len(sys.argv) > 4 else 'R57'
K = 1.2
SR = 48000
D = os.path.join(ROOT, 'SetC_DenseKH_LSOrchestra', 'Data')
def load(kind, s, r):
    x, sr = sf.read(os.path.join(D, kind, f'{s}{r}.wav')); assert sr == SR; return x
def onset(x): return int(np.argmax(np.abs(x) > np.abs(x).max() * 0.3))

# 1. 量測喇叭高頻補償:同一音源到前面幾排座位的直達聲平均
OCT = [500, 1000, 2000, 4000, 8000, 16000]
def direct_oct(x):
    a0 = onset(x); w = x[a0 - 48:a0 + 120] * np.hanning(168)
    Y = np.abs(np.fft.rfft(w, 8192)) ** 2; f = np.fft.rfftfreq(8192, 1 / SR)
    return np.array([10 * np.log10(Y[(f >= c / 1.414) & (f < c * 1.414)].mean()) for c in OCT])
dev = np.mean([direct_oct(load('Omni', SRC, r)) for r in ('R10', 'R52', 'R57', 'R62', 'R67')], 0)
dev -= dev[1]
gain_db = np.clip(-dev, 0, 6); gain_db[OCT.index(2000) - 1::-1] = 0   # 2kHz 以下不動
print('speaker HF deviation (dB re 1k):', dict(zip(OCT, np.round(dev, 1))), '-> boost', dict(zip(OCT, np.round(gain_db, 1))))

M = load('Omni', SRC, REC); S = load('Fig8', SRC, REC)
a0 = onset(M)
x = np.stack([M + K * S, M - K * S], 1)

# 2. 零相位 EQ(整段 FFT,前後補零避免繞回)
n = 1 << int(np.ceil(np.log2(len(x) * 2)))
f = np.fft.rfftfreq(n, 1 / SR)
lf = np.log2(np.maximum(f, 1))
g = 10 ** (np.interp(lf, np.log2(OCT), gain_db) / 20)
x = np.fft.irfft(np.fft.rfft(x, n, axis=0) * g[:, None], n, axis=0)[:len(x)]

# 3. 拿掉直達聲,從直達聲到達起算(跟 hall_ir.py 同樣做法)
x = x[a0:].copy(); cut = int(0.001 * SR)
x[:cut] = 0; ramp = int(0.002 * SR); x[cut:cut + ramp] *= np.linspace(0, 1, ramp)[:, None]

# 4. 尾巴延長:原始檔在直達聲後約 1.45 秒就截斷,低中頻還在 −40dB 左右(沒衰減完);高頻則更早就碰到量測底噪
#    (8kHz 約 0.8 秒、4kHz 約 1.1 秒以後只剩底噪)。後段殘響在統計上就是指數衰減的擴散雜訊,照標準做法延長:
#    在 STFT 上逐頻率格(1/3 八度平滑)找「比底噪高 15dB」的範圍,用 M+S 總能量擬合對數衰減直線(M、S 共用衰減率,
#    擴散聲場本來就一樣),S/M 能量比取同一範圍的平均(= 左右相關性不變);每個頻率格在快碰到底噪(最晚 1.15 秒)前
#    0.12 秒內交叉淡化到同樣頻譜、同樣衰減率的隨機相位雜訊(固定種子),延長到所有頻段比最大值低 70dB(最長 3 秒)
from scipy.signal import stft, istft, butter, sosfiltfilt
NPS, HOP = 2048, 512
T_END = 3.0
xp = np.zeros((int(T_END * SR), 2)); xp[:len(x)] = x
Mx, Sx = (xp[:, 0] + xp[:, 1]) / 2, (xp[:, 0] - xp[:, 1]) / 2
fz, tz, ZM = stft(Mx, fs=SR, nperseg=NPS, noverlap=NPS - HOP)
_, _, ZS = stft(Sx, fs=SR, nperseg=NPS, noverlap=NPS - HOP)
def smooth(P):   # 1/3 八度(頻率)+ 5 個 frame(時間)平滑
    out = np.empty_like(P)
    for i, f in enumerate(fz):
        out[i] = P[(fz >= f / 2 ** (1 / 6)) & (fz <= max(f * 2 ** (1 / 6), f + 40))].mean(0)
    k = np.ones(5) / 5
    return np.apply_along_axis(lambda v: np.convolve(v, k, 'same'), 1, out)
PM, PS = smooth(np.abs(ZM) ** 2), smooth(np.abs(ZS) ** 2)
PT = PM + PS
t_rec = (len(x) / SR) - 0.15                                   # 原始資料可信的最後時間(避開檔尾)
inrec = tz <= t_rec
floor = PT[:, inrec & (tz > 0.5)].min(1)                       # 每個頻率格的底噪(上限估計)
rng = np.random.default_rng(20201010)
# STFT 隨機相位重建的能量比例(實測校正)
wn = rng.standard_normal(SR * 2); _, _, Zw = stft(wn, fs=SR, nperseg=NPS, noverlap=NPS - HOP)
_, wr = istft(np.abs(Zw) * np.exp(2j * np.pi * rng.random(Zw.shape)), fs=SR, nperseg=NPS, noverlap=NPS - HOP)
rp = np.sqrt(np.mean(wn[NPS:-NPS] ** 2) / np.mean(wr[NPS:len(wn) - NPS] ** 2))
WF = int(round(0.12 * SR / HOP))
outM, outS = ZM.copy(), ZS.copy()
sw_t = np.zeros(len(fz)); rts = np.zeros(len(fz))
for i in range(len(fz)):
    ok = inrec & (tz >= 0.15) & (PT[i] > floor[i] * 10 ** 1.5)
    t_lim = min(tz[ok].max() if ok.any() else 0.4, 1.15)
    sel = (tz >= 0.15) & (tz <= t_lim)
    if sel.sum() < 6: sel = (tz >= 0.1) & (tz <= 0.5)
    sl, ic = np.polyfit(tz[sel], 10 * np.log10(PT[i, sel]), 1)
    sl = min(sl, -20.0)
    rts[i] = -60 / sl
    ratioS = np.mean(PS[i, sel] / PT[i, sel])
    j0 = max(int(np.searchsorted(tz, t_lim)) - WF, 1); sw_t[i] = tz[j0]
    lvl = 10 ** ((ic + sl * tz) / 10)                           # 擬合的總能量
    mag_M = np.sqrt(lvl * (1 - ratioS)) * rp; mag_S = np.sqrt(lvl * ratioS) * rp
    w = np.clip((np.arange(len(tz)) - j0) / WF, 0, 1); w = np.sin(w * np.pi / 2) ** 2
    phM = np.exp(2j * np.pi * rng.random(len(tz))); phS = np.exp(2j * np.pi * rng.random(len(tz)))
    outM[i] = ZM[i] * (1 - w) + mag_M * phM * w
    outS[i] = ZS[i] * (1 - w) + mag_S * phS * w
print('switch time / fitted RT60:', {c: (round(float(np.interp(c, fz, sw_t)), 2), round(float(np.interp(c, fz, rts)), 2)) for c in (125, 250, 500, 1000, 2000, 4000, 8000, 16000)})
_, yM = istft(outM, fs=SR, nperseg=NPS, noverlap=NPS - HOP)
_, yS = istft(outS, fs=SR, nperseg=NPS, noverlap=NPS - HOP)
y = np.stack([yM + yS, yM - yS], 1)[:int(T_END * SR)]
# 結尾:所有倍頻程都比各自最大值低 70dB 的地方,再淡出 0.3 秒
end = int(1.6 * SR)
for c in (125, 250, 500, 1000, 2000, 4000):
    z = sosfiltfilt(butter(3, [c / 1.414, c * 1.414], 'bandpass', fs=SR, output='sos'), y.mean(1)) ** 2
    zs = np.convolve(z, np.ones(2400) / 2400, 'same')
    end = max(end, int(np.nonzero(zs > zs.max() * 1e-7)[0][-1]))
x = y[:min(end + int(0.15 * SR), len(y))].copy()
fade = int(0.3 * SR); x[-fade:] *= np.cos(np.linspace(0, np.pi / 2, fade))[:, None] ** 2

x *= 0.9 / np.abs(x).max()
sf.write(OUT, x, SR, subtype='PCM_16', format='FLAC')
print(f'wrote {OUT}: {len(x) / SR:.2f}s  ({SRC}->{REC}, k={K})')
