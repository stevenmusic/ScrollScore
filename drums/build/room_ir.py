"""鼓房脈衝響應(房間麥克風):python3 drums/build/room_ir.py [輸出.flac,預設 drums/room.flac]

Naked Drums 是在很乾的房間錄的(實測小鼓 210ms 就衰減到 −30dB),只有 plate 殘響的話,鼓聽起來像飄在空中、
沒有「在房間裡」的感覺。真實的鼓錄音一定有房間麥克風,這裡用跟鋼琴音樂廳(piano/build/hall_ir.py)同一套
幾何聲學模擬(pyroomacoustics,MIT 授權:鏡像法前 3 階 + 射線追蹤、倍頻程吸音係數、空氣吸收)算一間錄音室鼓房:
  空間 8.5 × 6.5 × 3.6 m;地板木頭 + 鼓底下一塊地毯;牆面石膏板 + 木板 + 少量吸音板;天花板一半吸音
  鼓組在房間一側(2.2, 3.25, 1.0 m),一對間隔 1m 的全指向房間麥克風在鼓前約 3.3m、高 1.6m
  → 中頻 RT60 約 0.6 秒(錄音室 live room 常見 0.4~0.8)
輸出:直達聲拿掉(取樣本身就是近距離收音),以直達聲到達時間為 0;低頻左右相關性修正成擴散聲場的理論值 sinc(kd)
(射線追蹤的後段兩支麥克風各自隨機,低頻會不相關、聽起來飄);−60dB 或 1.2 秒截止、最後 0.25 秒淡出。
射線追蹤有隨機性,重建時各頻段 T30 會差一點點。"""
import sys, numpy as np, soundfile as sf, pyroomacoustics as pra
from scipy.signal import butter, sosfilt, sosfiltfilt
OUT = sys.argv[1] if len(sys.argv) > 1 else 'drums/room.flac'
SR = 48000; D_MIC = 1.0
d = pra.materials_data['absorption']
coef = lambda cat, name: d[cat][name]['coeffs']
def band7(c): return list(c) + [c[-1]] * (7 - len(c))
def mix(*pairs): return [sum(w * band7(c)[i] for w, c in pairs) for i in range(7)]
FREQS = [125, 250, 500, 1000, 2000, 4000, 8000]
M = lambda a: pra.Material({'coeffs': a, 'center_freqs': FREQS}, 0.5)
wood_floor, rug = coef('Wood', 'stage_floor'), coef('Floor coverings', 'carpet_tufted_9.5mm')
board, wood = coef('Lightweight constructions and linings', 'plasterboard'), coef('Wood', 'wood_16mm')
absorber = coef('Wall absorbers', 'panel_fabric_covered_6pcf')
ceiling_abs = coef('Wall absorbers', 'mineral_wool_50mm_40kgm3')
walls = M(mix((0.5, board), (0.35, wood), (0.15, absorber)))
materials = {'floor': M(mix((0.8, wood_floor), (0.2, rug))), 'ceiling': M(mix((0.5, board), (0.5, ceiling_abs))),
             'east': walls, 'west': walls, 'north': walls, 'south': walls}
room = pra.ShoeBox([8.5, 6.5, 3.6], fs=SR, materials=materials, max_order=3, air_absorption=True, ray_tracing=True)
room.set_ray_tracing(receiver_radius=0.4, n_rays=150000, energy_thres=1e-8)
room.add_source([2.2, 3.25, 1.0])
room.add_microphone_array(np.array([[5.5, 5.5], [3.25 - D_MIC / 2, 3.25 + D_MIC / 2], [1.6, 1.6]]))
room.compute_rir()
L, R = room.rir[0][0], room.rir[1][0]
n = min(len(L), len(R)); x = np.stack([L[:n], R[:n]], 1)
a0 = int(np.argmax(np.abs(x).max(1) > np.abs(x).max() * 0.3))
x = x[a0:].copy(); cut = int(0.001 * SR); x[:cut] = 0
ramp = int(0.002 * SR); x[cut:cut + ramp] *= np.linspace(0, 1, ramp)[:, None]
e = np.sqrt(np.convolve((x ** 2).mean(1), np.ones(480) / 480, 'same'))
end = min(len(x), int(1.2 * SR), int(np.nonzero(e > e.max() * 1e-3)[0][-1]) + int(0.05 * SR))
x = x[:end]; fade = int(0.25 * SR); x[-fade:] *= np.cos(np.linspace(0, np.pi / 2, fade))[:, None] ** 2
def t30(y, lo, hi):
    z = sosfilt(butter(4, [lo, hi], 'bandpass', fs=SR, output='sos'), y) ** 2
    s = np.cumsum(z[::-1])[::-1]; s = 10 * np.log10(s / s[0] + 1e-30); tt = np.arange(len(s)) / SR
    i5, i35 = np.argmax(s < -5), np.argmax(s < -35)
    return 2 * (tt[i35] - tt[i5]) if i35 > i5 else float('nan')
print('T30 by octave:', {f: round(t30(x.mean(1), f / 1.414, f * 1.414), 2) for f in (125, 250, 500, 1000, 2000, 4000)})
# 低頻左右相關性 → 擴散聲場理論值(間隔 1m:125Hz 約 0.35、更低更高);用零相位分頻,低頻往左右平均拉
target = float(np.sinc(2 * 100 * D_MIC / 343))   # np.sinc(x) = sin(πx)/(πx);kd = 2π f d / c
low = sosfiltfilt(butter(2, 220, 'low', fs=SR, output='sos'), x, axis=0); high = x - low
corr = lambda y: float(np.corrcoef(y[:, 0], y[:, 1])[0, 1])
w = 0.0
while corr((1 - w) * low + w * low.mean(1, keepdims=True)) < max(0.4, target) and w < 1: w += 0.02
x = (1 - w) * low + w * low.mean(1, keepdims=True) + high
print(f'low-band L/R correlation -> {corr((1 - w) * low + w * low.mean(1, keepdims=True)):.2f}, overall {corr(x):.2f}')
x *= 0.9 / np.abs(x).max()
sf.write(OUT, x, SR, subtype='PCM_16', format='FLAC')
print(f'wrote {OUT}: {len(x) / SR:.2f}s')
