"""踏板共鳴(sympathetic resonance)的脈衝響應:python3 piano/build/sympa_ir.py [輸出.flac,預設 piano/sympa.flac]

踩下延音踏板時,所有制音器離開琴弦,88 組琴弦都會被正在響的音(經由琴橋/響板)帶動、跟著共振。
這個 IR 就是「全部琴弦一起當共振器」:每條弦的每個泛音是一個衰減的正弦波
  頻率 f_n = n·f0·√(1 + B·n²)        (B = 鋼弦的非諧和係數,低音約 1e-4、高音約 1e-2)
  衰減 T60 = 低音弦約 30 秒 → 最高音約 4 秒(照取樣實測),高次泛音衰減稍快
  位置   低音在左、高音在右(跟 pf_build.py 的 PAN 一樣,±0.25)
App 把踩著踏板時的琴聲送進這個 IR(ConvolverNode),輸出經過踏板閘門(放開踏板 = 制音器落下 → 共鳴止住)。
聲音跟某條弦的泛音重疊越多,那條弦就響越大,所以 C 和弦會帶出所有 C/E/G 的弦,這就是真鋼琴踩踏板時的「光暈」。
左右:每個泛音到兩支麥克風的相位與大小各自不同(響板輻射,500Hz 以上左右不相關、低頻同相),共鳴聽起來是包圍的一片,不是一個點。
長度 5 秒、最後 2 秒淡出(放開踏板時 App 的閘門會收掉,不會跨踏板糊在一起)。固定種子,每次產生的一樣。"""
import sys, numpy as np, soundfile as sf
# 2026-11 新版(使用者試聽:「B 比較有共鳴在繞圈的感覺」):5 秒(最後 2 秒淡出)、相鄰弦差 1.6 cent、T60 A0 30 秒 → C8 4 秒、高次泛音變快係數 0.02。
#   原因:實測取樣本身中音區 T60 約 10~20 秒,舊模型(18 → 2 秒、係數 0.06)只有 4~9 秒,共鳴 3 秒後就沒了;
#   舊版 3 秒、0.87 cent。換檔要重新校正 App 的 PIANO_SYMPA.send(這版 3.1e-4,前 1 秒共鳴音量跟舊版一樣)、SAMPLE_CACHE 版本加一
import os
SR = 48000
SEC = float(os.environ.get('SYMPA_SEC', 5.0))
DETUNE_CENT = float(os.environ.get('SYMPA_DETUNE', 1.6))   # 同組相鄰兩條弦相差幾 cent
T60_LO, T60_HI, HARM_K = (float(v) for v in os.environ.get('SYMPA_T60', '30,4,0.02').split(','))   # A0 / C8 的 T60 秒數、高次泛音變快的係數
OUT = sys.argv[1] if len(sys.argv) > 1 else 'piano/sympa.flac'
rng = np.random.default_rng(88)
DECOR_F, DECOR_DB = 500.0, 2.5
# 擴散(2026-11,試聽中:repo 裡的 piano/sympa.flac 還是前一版〔沒有 BLOOM/DRIFT〕,使用者選定後才重新產生;
#   重新產生:SYMPA_MATCH=舊的 sympa.flac python3 piano/build/sympa_ir.py → 照舊檔前 1 秒響度對齊,App 的 send 不用改)
# 使用者:「希望共鳴聽起來是一個球形,有擴散出去的感覺」):
#   BLOOM:左右差異(相位、大小)剛響起時只有 BLOOM0 倍,BLOOM_SEC 秒內 smoothstep 長到完整 → 共鳴先在琴的位置、再往四周散開
#   DRIFT:每個泛音左右的相位差/大小差各自用很慢的正弦飄移(DRIFT_HZ 範圍內隨機,約 2~7 秒一圈)→ 共鳴在空間裡慢慢流動
#   單聲道(左+右)的音量會跟著飄移一點,但每個泛音飄的速度不同,加起來是平的
BLOOM0 = float(os.environ.get('SYMPA_BLOOM0', 0.25))
BLOOM_SEC = float(os.environ.get('SYMPA_BLOOM_SEC', 0.45))
DRIFT_RAD = float(os.environ.get('SYMPA_DRIFT', 1.2))      # 相位差飄移幅度(弧度)
DRIFT_DB = float(os.environ.get('SYMPA_DRIFT_DB', 1.5))    # 左右大小差飄移幅度(dB)
DRIFT_HZ = tuple(float(v) for v in os.environ.get('SYMPA_DRIFT_HZ', '0.15,0.45').split(','))
MATCH = os.environ.get('SYMPA_MATCH', '')                  # 指定舊檔:照它前 1 秒的響度對齊(App 的 send 不用改)
n = int(SR * SEC); t = np.arange(n) / SR
u = np.clip(t / BLOOM_SEC, 0, 1) if BLOOM_SEC > 0 else np.ones(n)
bloom = BLOOM0 + (1 - BLOOM0) * u * u * (3 - 2 * u)
L = np.zeros(n); R = np.zeros(n)
for m in range(21, 109):
    f0 = 440 * 2 ** ((m - 69) / 12)
    B = 8e-5 * np.exp(0.055 * (m - 21))                   # 非諧和係數:A0 ≈ 8e-5,C8 ≈ 1e-2
    t60 = T60_LO * (T60_HI / T60_LO) ** ((m - 21) / 87)   # 對數內插(照取樣實測,見檔頭)
    pan = (m - 64.5) / 43.5 * 0.25
    gl, gr = np.sqrt(0.5 - pan), np.sqrt(0.5 + pan)       # 等功率擺位
    strings = 1 if m < 29 else 2 if m < 41 else 3          # 單弦 / 雙弦 / 三弦一組(同組各弦有一點點走音 → 拍頻)
    for k in range(1, 61):
        fk = k * f0 * np.sqrt(1 + B * k * k)
        if fk > 9000: break
        tk = t60 / (1 + HARM_K * (k - 1) ** 1.3)           # 高次泛音衰減較快
        amp = 1 / k ** 0.8 / np.sqrt(strings)
        env = np.exp(-6.91 * t / tk)
        for s in range(strings):
            det = 2 ** ((s - (strings - 1) / 2) * DETUNE_CENT / 1200) if strings > 1 else 1   # 同組相鄰弦相差 DETUNE_CENT
            ph = rng.uniform(0, 2 * np.pi)
            # 響板輻射(2026-10 加):共振的弦是透過整片響板向四面發聲,兩支麥克風收到同一個泛音的相位、大小都不一樣
            # (響板各處振動模態不同);以前左右是同一個正弦波只差音量 → 共鳴是「擺在某個位置的點」,很扁。
            # 低頻波長長、兩支麥克風收到的幾乎同相,DECOR_F 以上完全不相關;大小差 ±DECOR_DB(常態分布)
            dec = min(1.0, fk / DECOR_F)
            d0 = rng.uniform(-np.pi, np.pi) * dec
            dl, dr = rng.normal(0, DECOR_DB * dec), rng.normal(0, DECOR_DB * dec)
            fd = rng.uniform(*DRIFT_HZ); pd = rng.uniform(0, 2 * np.pi)
            fl = rng.uniform(*DRIFT_HZ); pl = rng.uniform(0, 2 * np.pi)
            dph = (d0 + DRIFT_RAD * dec * np.sin(2 * np.pi * fd * t + pd)) * bloom   # 左右相位差:先小、再散開,之後慢慢飄
            ldb = ((dr - dl) / 2 + DRIFT_DB * dec * np.sin(2 * np.pi * fl * t + pl)) * bloom
            base = 2 * np.pi * fk * det * t + ph
            L += np.sin(base - dph / 2) * env * (amp * gl * 10 ** (-ldb / 40) * 10 ** ((dl + dr) / 40))
            R += np.sin(base + dph / 2) * env * (amp * gr * 10 ** (ldb / 40) * 10 ** ((dl + dr) / 40))
fade = int(float(os.environ.get('SYMPA_FADE', 2.0)) * SR)   # 最後幾秒慢慢收(太短會聽到共鳴在踏板中途突然不見)
win = np.ones(n); win[-fade:] = np.cos(np.linspace(0, np.pi / 2, fade)) ** 2
L *= win; R *= win
# 起頭 3ms 淡入(避免卷積時產生喀聲)
fi = int(0.003 * SR); L[:fi] *= np.linspace(0, 1, fi); R[:fi] *= np.linspace(0, 1, fi)
x = np.stack([L, R], 1)
if MATCH:   # 照舊檔前 1 秒的響度對齊(App 的 PIANO_SYMPA.send 不用改)
    o = sf.read(MATCH)[0][:SR]; x *= np.sqrt(np.mean(o ** 2) / np.mean(x[:SR] ** 2))
    print(f'peak {20*np.log10(np.abs(x).max()):.2f} dBFS')
else:
    x *= 0.9 / np.abs(x).max()               # 峰值 −0.9dBFS。App 的 PIANO_SYMPA.send 是對這個檔案校正的(重建後要重新校正)
sf.write(OUT, x, SR, subtype='PCM_16', format='FLAC')
print(f'wrote {OUT}: {SEC}s')
