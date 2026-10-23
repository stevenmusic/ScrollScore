"""鋼琴的「房間麥克風」層(早期反射):python3 piano/build/room_brahms.py <DetmoldSRIR 解壓目錄> [輸出.flac,預設 piano/room.flac]

商業鋼琴音色都是近距離 + 演奏者位置 + 房間幾組麥克風混在一起;房間麥克風晚幾毫秒到,帶著地板、牆面、天花板的早期反射,
是「琴在空間裡、有前後深度」的主要來源。我們的取樣(Salamander)只有一對近距離 AB,音樂廳殘響(hall.flac)又是 8m 外、
音量很小的長尾巴,所以缺這一層。

來源:Open Database of Spatial Room Impulse Responses at Detmold University of Music
  (Amengual Garí, Sahin, Eddy, Kob, AES 149th Convention 2020;https://zenodo.org/records/4116247,CC BY 4.0)
  Set A:Brahmssaal(Detmold 音樂大學的室內樂廳,17.4 × 8.1m,舞台上放兩台平台鋼琴,空廳;RT60 1kHz 約 1.2 秒)真實量測,
  音源 Neumann KH 120 A(平直 EQ)在舞台中央,接收 = Open Array 的 NTi M2010 全指向麥克風(陣列正前方那一支)。
  左聲道 = R2(第一排,離音源約 3m),右聲道 = R3(第三排,約 4.7m):兩個位置相距約 1.8m,就像一對分開擺的房間麥克風,
  反射的時間與方向不一樣 → 左右自然不相關(立體、包圍),不是人工亂數。

處理(以下是對原始資料的修改):
  1. 各自從自己的直達聲到達時間起算(兩聲道對齊),拿掉直達聲(取樣本身就是直達聲),保留之後的反射
  2. 補償量測喇叭的高頻:用 hall.flac 同一組(4k +1.5、8k +4、16k +5.4dB,Konzerthaus 軸上量的),見程式說明
  3. 250Hz 以下左右往平均拉一半:真實殘響的低頻左右幾乎一樣(相距 1.8m 的兩支全指向在低頻反而會不相關、聽起來「飄」)
  4. 只留早期部分:0~120ms 完整,120~350ms 餘弦淡出(長尾巴由 hall.flac 負責,兩個長殘響疊在一起會糊)
  5. 48kHz 立體聲 16-bit FLAC,峰值 0.9。App 的 PIANO_ROOM.wet 要在 App 裡量回送響度校正(ConvolverNode 會自動正規化)
"""
import sys, os, numpy as np, soundfile as sf
from scipy.signal import butter, sosfiltfilt
ROOT = sys.argv[1]
OUT = sys.argv[2] if len(sys.argv) > 2 else 'piano/room.flac'
SR = 48000
D = os.path.join(ROOT, 'SetA_SingleSources', 'Data', 'Brahmssaal', 'OpenArray')
def load(r):
    x, sr = sf.read(os.path.join(D, f'C1S1{r}.wav')); assert sr == SR
    return x[:, 0]   # 陣列第 1 支 = 正前方
def onset(x): return int(np.argmax(np.abs(x) > np.abs(x).max() * 0.3))

OCT = [500, 1000, 2000, 4000, 8000, 16000]
def direct_oct(x):
    a0 = onset(x); w = x[a0 - 48:a0 + 120] * np.hanning(168)
    Y = np.abs(np.fft.rfft(w, 8192)) ** 2; f = np.fft.rfftfreq(8192, 1 / SR)
    return np.array([10 * np.log10(Y[(f >= c / 1.414) & (f < c * 1.414)].mean()) for c in OCT])
raw = {r: load(r) for r in ('R2', 'R3', 'R4')}
dev = np.mean([direct_oct(v) for v in raw.values()], 0); dev -= dev[1]
# 這裡量到的直達聲 4k −5.6、8k −9.2dB,比 hall_detmold.py 在 Konzerthaus 量的多(R2/R3 偏在喇叭側邊約 30°,KH 120 A 高頻有指向性),
# 補這麼多會把離軸的反射也變亮,所以用 hall.flac 同一組補償(軸上的值),兩層音色一致
gain_db = np.array([0, 0, 0, 1.5, 4.0, 5.4])
print('speaker HF deviation (dB re 1k):', dict(zip(OCT, np.round(dev, 1))), '-> boost', dict(zip(OCT, np.round(gain_db, 1))))

LEN = int(0.35 * SR)
chans = []
for r in ('R2', 'R3'):
    x = raw[r]; a0 = onset(x)
    y = x[a0:a0 + LEN].copy()
    cut = int(0.001 * SR); ramp = int(0.002 * SR)
    y[:cut] = 0; y[cut:cut + ramp] *= np.linspace(0, 1, ramp)
    chans.append(y)
x = np.stack(chans, 1)

n = 1 << int(np.ceil(np.log2(LEN * 2)))
f = np.fft.rfftfreq(n, 1 / SR)
g = 10 ** (np.interp(np.log2(np.maximum(f, 1)), np.log2(OCT), gain_db) / 20)
x = np.fft.irfft(np.fft.rfft(x, n, axis=0) * g[:, None], n, axis=0)[:LEN]

lo = butter(4, 250, btype='low', fs=SR, output='sos')
low = sosfiltfilt(lo, x, axis=0); mid = low.mean(1, keepdims=True)
x = x - 0.5 * (low - mid)

t = np.arange(LEN) / SR
win = np.ones(LEN); k = t > 0.12
win[k] = np.cos((t[k] - 0.12) / (0.35 - 0.12) * np.pi / 2) ** 2
x *= win[:, None]
x *= 0.9 / np.abs(x).max()
sf.write(OUT, x, SR, subtype='PCM_16', format='FLAC')
c = lambda a, b: float(np.dot(a, b) / np.sqrt(np.dot(a, a) * np.dot(b, b)))
for lo_, hi_ in [(60, 250), (250, 1000), (1000, 4000), (4000, 12000)]:
    s = butter(3, [lo_, hi_], btype='band', fs=SR, output='sos'); a = sosfiltfilt(s, x[:, 0]); b = sosfiltfilt(s, x[:, 1])
    print(f'L/R corr {lo_}-{hi_}Hz: {c(a, b):.2f}')
print(f'wrote {OUT}: {LEN / SR:.2f}s')
