"""踏板共鳴(sympathetic resonance)的脈衝響應:python3 piano/build/sympa_ir.py [輸出.flac,預設 piano/sympa.flac]

踩下延音踏板時,所有制音器離開琴弦,88 組琴弦都會被正在響的音(經由琴橋/響板)帶動、跟著共振。
這個 IR 就是「全部琴弦一起當共振器」:每條弦的每個泛音是一個衰減的正弦波
  頻率 f_n = n·f0·√(1 + B·n²)        (B = 鋼弦的非諧和係數,低音約 1e-4、高音約 1e-2)
  衰減 T60 = 低音弦約 18 秒 → 最高音約 2 秒,高次泛音衰減較快
  位置   低音在左、高音在右(跟 pf_build.py 的 PAN 一樣,±0.25)
App 把踩著踏板時的琴聲送進這個 IR(ConvolverNode),輸出經過踏板閘門(放開踏板 = 制音器落下 → 共鳴止住)。
聲音跟某條弦的泛音重疊越多,那條弦就響越大,所以 C 和弦會帶出所有 C/E/G 的弦,這就是真鋼琴踩踏板時的「光暈」。
左右:每個泛音到兩支麥克風的相位與大小各自不同(響板輻射,500Hz 以上左右不相關、低頻同相),共鳴聽起來是包圍的一片,不是一個點。
長度 3 秒(更長的部分已經比直達聲小 30dB 以上,而且卷積成本隨長度增加),最後 0.6 秒淡出。固定種子,每次產生的一樣。"""
import sys, numpy as np, soundfile as sf
SR, SEC = 48000, 3.0
OUT = sys.argv[1] if len(sys.argv) > 1 else 'piano/sympa.flac'
rng = np.random.default_rng(88)
DECOR_F, DECOR_DB = 500.0, 2.5
n = int(SR * SEC); t = np.arange(n) / SR
L = np.zeros(n); R = np.zeros(n)
for m in range(21, 109):
    f0 = 440 * 2 ** ((m - 69) / 12)
    B = 8e-5 * np.exp(0.055 * (m - 21))                   # 非諧和係數:A0 ≈ 8e-5,C8 ≈ 1e-2
    t60 = 18 * (2 / 18) ** ((m - 21) / 87)               # 18 秒 → 2 秒(對數內插)
    pan = (m - 64.5) / 43.5 * 0.25
    gl, gr = np.sqrt(0.5 - pan), np.sqrt(0.5 + pan)       # 等功率擺位
    strings = 1 if m < 29 else 2 if m < 41 else 3          # 單弦 / 雙弦 / 三弦一組(同組各弦有一點點走音 → 拍頻)
    for k in range(1, 61):
        fk = k * f0 * np.sqrt(1 + B * k * k)
        if fk > 9000: break
        tk = t60 / (1 + 0.06 * (k - 1) ** 1.3)             # 高次泛音衰減較快
        amp = 1 / k ** 0.8 / np.sqrt(strings)
        env = np.exp(-6.91 * t / tk)
        for s in range(strings):
            det = 1 + (s - (strings - 1) / 2) * 0.6 / 1200 if strings > 1 else 1   # 同組弦相差約 ±0.3 cent
            ph = rng.uniform(0, 2 * np.pi)
            # 響板輻射(2026-10 加):共振的弦是透過整片響板向四面發聲,兩支麥克風收到同一個泛音的相位、大小都不一樣
            # (響板各處振動模態不同);以前左右是同一個正弦波只差音量 → 共鳴是「擺在某個位置的點」,很扁。
            # 低頻波長長、兩支麥克風收到的幾乎同相,DECOR_F 以上完全不相關;大小差 ±DECOR_DB(常態分布)
            dec = min(1.0, fk / DECOR_F)
            phr = ph + rng.uniform(-np.pi, np.pi) * dec
            al = 10 ** (rng.normal(0, DECOR_DB * dec) / 20); ar = 10 ** (rng.normal(0, DECOR_DB * dec) / 20)
            base = 2 * np.pi * fk * det * t
            L += np.sin(base + ph) * env * (amp * gl * al)
            R += np.sin(base + phr) * env * (amp * gr * ar)
fade = int(0.6 * SR)
win = np.ones(n); win[-fade:] = np.cos(np.linspace(0, np.pi / 2, fade)) ** 2
L *= win; R *= win
# 起頭 3ms 淡入(避免卷積時產生喀聲)
fi = int(0.003 * SR); L[:fi] *= np.linspace(0, 1, fi); R[:fi] *= np.linspace(0, 1, fi)
x = np.stack([L, R], 1)
x *= 0.9 / np.abs(x).max()                   # 峰值 −0.9dBFS。App 的 PIANO_SYMPA.send 是對這個檔案校正的(重建後要重新校正)
sf.write(OUT, x, SR, subtype='PCM_16', format='FLAC')
print(f'wrote {OUT}: {SEC}s')
