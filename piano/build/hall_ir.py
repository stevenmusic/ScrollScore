"""(舊版,2026-10 起 piano/hall.flac 改用真實量測的 Detmold 音樂廳:piano/build/hall_detmold.py;這支只留著參考)
模擬的音樂廳脈衝響應:python3 piano/build/hall_ir.py [輸出.flac]

當時真實音樂廳的量測 IR(OpenAIR、Detmold、3D-MARCo)拿不到(OpenAIR 憑證過期、Zenodo 限流),
改用 pyroomacoustics(MIT 授權)做幾何聲學模擬:鏡像法(前 3 階,早期反射位置/延遲準確)+ 射線追蹤(後段殘響),
材料用 ISO/文獻的倍頻程吸音係數,空氣吸收開著,所以各頻率的衰減、早期反射的時間與方向都是物理算出來的,
不是手調的雜訊包絡。
  空間 26 × 17 × 11 m 的鞋盒型獨奏廳(約 400 席,維也納金廳也是鞋盒型)
  舞台:木地板;觀眾區:中度軟墊座椅;側牆:木板 + 灰泥;天花板:石膏板;散射係數 0.4
  鋼琴在舞台上(4, 8.5, 1.2 m),一對間隔 60cm 的全指向麥克風(AB)在琴前約 6m、高 2.6m(錄音室常用的廳堂麥克風位置)
  → 中頻 RT60 約 1.8 秒(獨奏廳常見 1.6~2.0);高頻再加衰減到 2k 1.6 / 4k 1.3 / 8k 0.9 秒(坐滿觀眾的廳)
輸出:直達聲拿掉(App 的取樣本身就是近距離的直達聲),以直達聲到達時間為 0,保留之後的早期反射與殘響;
-70dB 或 2.8 秒截止、最後 0.4 秒淡出、低頻左右相關性修正到擴散聲場的理論值,48kHz 立體聲 16-bit FLAC。射線追蹤有隨機性,重建時各頻段 T30 會差 0.1 秒左右。"""
import sys, numpy as np, soundfile as sf, pyroomacoustics as pra
OUT = sys.argv[1] if len(sys.argv) > 1 else 'hall_sim.flac'
SR = 48000
np.random.seed(7)
d = pra.materials_data['absorption']
coef = lambda cat, name: d[cat][name]['coeffs']
def band7(c): return list(c) + [c[-1]] * (7 - len(c))   # 補到 7 個倍頻程(125~8k)
def mix(*pairs): return [sum(w * band7(c)[i] for w, c in pairs) for i in range(7)]
FREQS = [125, 250, 500, 1000, 2000, 4000, 8000]
seats = coef('Seating (2 seats per m2)', 'chairs_medium_upholstered')
stage = coef('Wood', 'stage_floor')
wood = coef('Wood', 'wood_16mm')
plaster = coef('Massive constructions and hard surfaces', 'rough_lime_wash')
board = coef('Lightweight constructions and linings', 'plasterboard')
M = lambda a: pra.Material({'coeffs': a, 'center_freqs': FREQS}, 0.4)
materials = {
    'floor': M(mix((0.75, seats), (0.25, stage))),          # 觀眾席 3/4、舞台 1/4
    'ceiling': M(mix((0.7, board), (0.3, plaster))),
    'east': M(mix((0.5, wood), (0.5, plaster))), 'west': M(mix((0.6, wood), (0.4, plaster))),   # 舞台後牆 / 觀眾席後牆
    'north': M(mix((0.5, wood), (0.5, plaster))), 'south': M(mix((0.5, wood), (0.5, plaster))),
}
room = pra.ShoeBox([26, 17, 11], fs=SR, materials=materials, max_order=3, air_absorption=True, ray_tracing=True)
room.set_ray_tracing(receiver_radius=0.5, n_rays=200000, energy_thres=1e-8)
room.add_source([4.0, 8.5, 1.2])
room.add_microphone_array(np.array([[10.0, 10.0], [8.2, 8.8], [2.6, 2.6]]))
room.compute_rir()
L, R = room.rir[0][0], room.rir[1][0]
n = min(len(L), len(R)); x = np.stack([L[:n], R[:n]], 1)
rt = room.measure_rt60()
print('RT60 (L/R, broadband) =', np.round(rt, 2))
# 直達聲:第一個大峰。拿掉直達聲(之前 + 之後 1ms),從直達聲到達的時間起算
a0 = int(np.argmax(np.abs(x).max(1) > np.abs(x).max() * 0.3))
x = x[a0:].copy(); cut = int(0.001 * SR)
x[:cut] = 0; ramp = int(0.002 * SR); x[cut:cut + ramp] *= np.linspace(0, 1, ramp)[:, None]
e = np.sqrt(np.convolve((x ** 2).mean(1), np.ones(480) / 480, 'same'))
end = min(len(x), int(2.8 * SR), int(np.nonzero(e > e.max() * 10 ** -3.5)[0][-1]) + int(0.05 * SR))
x = x[:end]; fade = int(0.4 * SR); x[-fade:] *= np.cos(np.linspace(0, np.pi / 2, fade))[:, None] ** 2
# 各頻段 RT60(T30 由 Schroeder 積分)
def t30(y, lo, hi):
    from scipy.signal import butter, sosfilt
    sos = butter(4, [lo, hi], 'bandpass', fs=SR, output='sos'); z = sosfilt(sos, y) ** 2
    s = np.cumsum(z[::-1])[::-1]; s = 10 * np.log10(s / s[0] + 1e-30); tt = np.arange(len(s)) / SR
    i5, i35 = np.argmax(s < -5), np.argmax(s < -35)
    return 2 * (tt[i35] - tt[i5]) if i35 > i5 else float('nan')
print('T30 by octave:', {f: round(t30(x.mean(1), f / 1.414, f * 1.414), 2) for f in (125, 250, 500, 1000, 2000, 4000)})
print('L/R correlation:', round(float(np.corrcoef(x[:, 0], x[:, 1])[0, 1]), 3))
# 高頻殘響:射線追蹤算出 4kHz 仍有 1.65 秒,比真實坐滿觀眾的廳亮(觀眾衣物與空氣把高頻吸得更快,
# 典型 2kHz 1.6、4kHz 1.3、8kHz 0.9 秒)。用 STFT 對 1kHz 以上乘 exp(−α(f)·t),α = 6.91·(1/目標 − 1/目前)
from scipy.signal import stft, istft
TARGET = [(1000, None), (2000, 1.6), (4000, 1.3), (8000, 0.9), (16000, 0.7)]
def cur_rt(f): return 1.7 if f <= 2000 else 1.65
fz, tz, Z = stft(x.T, fs=SR, nperseg=1024, noverlap=768)
alpha = np.zeros(len(fz))
for i, f in enumerate(fz):
    if f <= 1000: continue
    tf = np.interp(np.log2(f), [np.log2(a) for a, _ in TARGET[1:]], [b for _, b in TARGET[1:]])
    tf = np.interp(np.log2(f), [np.log2(1000), np.log2(2000)], [1.7, 1.6]) if f < 2000 else tf
    alpha[i] = max(0.0, 6.91 * (1 / tf - 1 / cur_rt(f)))
Z *= np.exp(-alpha[None, :, None] * tz[None, None, :])
x = istft(Z, fs=SR, nperseg=1024, noverlap=768)[1].T[:len(x)]
print('T30 after HF damping:', {f: round(t30(x.mean(1), f / 1.414, f * 1.414), 2) for f in (125, 500, 1000, 2000, 4000, 8000 if SR > 24000 else 4000)})
# 低頻左右相關性:射線追蹤的後段每支麥克風各自隨機,低頻也幾乎不相關(0.2),但真實擴散聲場裡相距 d 的兩支全指向麥克風
# 相關性是 sinc(kd)(60cm:125Hz ≈ 0.7、250Hz ≈ 0.15、更高 ≈ 0)。用零相位分頻(低頻 = 低通,高頻 = 原訊號減低頻,相加完全還原),
# 低頻部分往左右平均拉,調到 125Hz 附近 0.7
from scipy.signal import butter, sosfiltfilt
low = sosfiltfilt(butter(2, 220, 'low', fs=SR, output='sos'), x, axis=0); high = x - low
def corr(y): return float(np.corrcoef(y[:, 0], y[:, 1])[0, 1])
w = 0.0
while corr(low * 0 + (1 - w) * low + w * low.mean(1, keepdims=True)) < 0.7 and w < 1: w += 0.02
low = (1 - w) * low + w * low.mean(1, keepdims=True)
x = low + high
print(f'low-band L/R correlation -> {corr(low):.2f} (mix {w:.2f})')
x *= 0.9 / np.abs(x).max()
sf.write(OUT, x, SR, subtype='PCM_16', format='FLAC')
print(f'wrote {OUT}: {len(x) / SR:.2f}s')
