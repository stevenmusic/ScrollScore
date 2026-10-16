"""銅鈸取樣補回完整尾巴:python3 drums/build/cymbal_tails.py <Naked Drums sfz 根目錄> [drums 目錄,預設 drums]

原本的預混(stevenmusic/drum-samples 的 web/nk-*.flac)把銅鈸裁成固定長度:crash 3.0 秒、ride/china 2.6、ride bell 2.4、
splash 1.8 秒,而且從結尾前約 0.6 秒開始淡出。原廠錄音 crash 有 5~6 秒,輕打的 crash 在 2 秒時還有 −26dB 就被切掉。
這支程式用原廠多軌錄音(sfzinstruments/WilkinsonAudio.NakedDrums,CC-BY 4.0)照同一個混音配方重建尾巴:

  配方(反推驗證過):原廠「Naked Drums FR」立體聲預設 = overhead + close room + far rooms(ride 另有近距麥克風),
  各麥克風 trim −3dB、房間麥克風再 +6dB;crash 反推出來 overhead −3.0 / close room +3.0 / far room +3.0dB,
  殘差 −42dB(等於逐點重建出同一個檔案)。china、splash 用的是原廠第 1 片(第 2 片完全對不上)。

每個檔案:
  1. 原廠各麥克風 44.1k → 48k,跟現有檔案對齊(互相關),在 0.05 秒 ~ 交叉淡化結束之間對左右聲道各自做最小平方法
     求各麥克風權重(現有檔案開頭 10ms 有淡入/低頻處理,不拿來擬合)。擬合後殘差要 < −30dB 才用
  2. 找現有檔案開始被淡出的時間(跟重建版的 50ms 能量比掉超過 1dB 的地方),在那之前 0.3 秒內交叉淡化:
     前段保留現有檔案(擊打音色完全不變),後段換成重建的完整尾巴
  3. 尾巴留到 50ms 能量比最大值低 54dB 為止,最長 6 秒(ride 要 8~12 秒才到 −60dB);48kHz 16-bit FLAC、TPDF dither
     (預混的 round-robin 編號跟原廠不同時——ride bell——在 10 個原廠錄音裡找開頭最像的)
  4. manifest.json 的 frames 重算(lufs 是瞬時響度最大值,只看開頭,不變)
"""
import sys, os, re, json, numpy as np, soundfile as sf
from scipy.signal import resample_poly, fftconvolve

ND = os.path.join(sys.argv[1], 'Wilkinson Audio', 'Naked Drums')
OUT = sys.argv[2] if len(sys.argv) > 2 else 'drums'
SR = 48000
MAX_SEC = 6.0
RRN = ['one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten']
# 鼓件 → 原廠 file 定義(各麥克風)、力度層數
SPEC = {
    'crashL': (['H2DR', '5ASI', 'Q16J'], 3),            # crash1 邊緣:OH、CR、FR
    'crashR': (['6447', '1V3V', 'SJ0B'], 3),            # crash2 邊緣
    'ride': (['ZAHP', 'KXMA', 'DVUI', 'QQM6'], 3),       # ride 鈸面:DI、OH、CR、FR
    'rideBell': (['A5YV', 'DJ89', '1XK0', '13ZX'], 1),
    'china': (['KI3W', 'ZXEH', 'KGUU'], 3),              # china1
    'splash': (['8T96', 'G73D', 'IZ0F'], 2),             # splash1
}

def sample_path(filedef, layer, rr):
    d = open(os.path.join(ND, 'Data', 'file', filedef + '.txt')).read()
    D = dict(re.findall(r'#define \$(\w+)\s+(\S+)', d))
    nl = sum(1 for k in D if re.fullmatch(r'VEL\d', k))
    code = D['CODE_%02d' % ((rr - 1) * nl + layer)]
    return os.path.join(ND, 'Samples', f"{D['MIC']}_{D['ART']}_{D['VEL%d' % layer]}_{RRN[rr - 1]}-{code}.flac")

def load48(p):
    x, sr = sf.read(p)
    x = x if x.ndim > 1 else np.stack([x, x], 1)
    assert sr == 44100
    return resample_poly(x, 160, 147, axis=0)

def env_db(x, w=2400):
    e = np.convolve((x ** 2).sum(1), np.ones(w) / w, 'same')
    return 10 * np.log10(e + 1e-30)

def tpdf16(x, rng):
    q = 1 / 32768
    return np.clip(np.round((x + (rng.random(x.shape) - rng.random(x.shape)) * q) / q), -32768, 32767).astype(np.int16)

man_path = os.path.join(OUT, 'manifest.json')
man = json.load(open(man_path))
rng = np.random.default_rng(1)
worst = -999
for piece, (defs, nl) in SPEC.items():
    info = man['pieces'][piece]
    assert len(info['layers']) == nl
    for li in range(nl):
        frames = 0
        for rr in range(1, info['layers'][li]['rr'] + 1):
            fn = os.path.join(OUT, f"{info['prefix']}-L{li + 1}.{rr:02d}.flac")
            y, sr = sf.read(fn); assert sr == SR
            # 對齊:互相關找大概位置,再在 ±200 個樣本內用擬合殘差找真正的對齊點
            # (ride bell 幾乎是純音、週期約 56 個樣本,互相關會跳到別的波峰)
            def resid_at(mics, lg):
                i0, i1 = int(0.05 * SR), int(0.5 * SR); num = den = 0
                for ch in (0, 1):
                    cols = []
                    for m in mics:
                        for c in (0, 1):
                            col = np.zeros(i1 - i0); src_i = np.arange(i0, i1) - lg
                            ok = (src_i >= 0) & (src_i < len(m)); col[ok] = m[src_i[ok], c]; cols.append(col)
                    A = np.stack(cols, 1); t = y[i0:i1, ch]
                    w, *_ = np.linalg.lstsq(A, t, rcond=None); num += np.sum((t - A @ w) ** 2); den += np.sum(t ** 2)
                return num / den
            def align(src_rr):
                mics = [load48(sample_path(d, li + 1, src_rr)) for d in defs]
                n_all = min(len(m) for m in mics); mics = [m[:n_all] for m in mics]
                ref = sum(mics); a = ref[:int(0.3 * SR)].mean(1); b = y[:int(0.3 * SR)].mean(1)
                lag = int(np.argmax(fftconvolve(b, a[::-1])) - (len(a) - 1))
                lag = min(range(lag - 200, lag + 201, 4), key=lambda g: resid_at(mics, g))
                lag = min(range(lag - 4, lag + 5), key=lambda g: resid_at(mics, g))
                return resid_at(mics, lag), lag, mics, n_all
            # 預混的 round-robin 編號應該跟原廠一樣;萬一對不上,在 10 個原廠錄音裡找殘差最小的
            r0, lag, mics, n_all = align(rr)
            src = rr
            if r0 > 1e-3:
                r0, lag, mics, n_all, src = min((align(k) + (k,) for k in range(1, 11)), key=lambda c: c[0])
            def shift(x):
                out = np.zeros((n_all + max(lag, 0), 2))
                if lag >= 0: out[lag:lag + len(x)] = x
                else: out[:len(x) + lag] = x[-lag:]
                return out
            M = [shift(m) for m in mics]
            # 粗擬合(0.05 ~ 1.0 秒)找淡出起點,再用到淡出前的範圍精擬合
            def solve(t0, t1):
                i0, i1 = int(t0 * SR), int(t1 * SR); W = []
                for ch in (0, 1):
                    A = np.stack([m[i0:i1, c] for m in M for c in (0, 1)], 1)
                    w, *_ = np.linalg.lstsq(A, y[i0:i1, ch], rcond=None); W.append(w)
                return W
            def mix(W):
                return np.stack([sum(W[ch][k * 2 + c] * M[k][:, c] for k in range(len(M)) for c in (0, 1)) for ch in (0, 1)], 1)
            short = len(y) / SR < 2.0
            rough = mix(solve(0.05, 0.7 if short else 1.0))
            n = min(len(y), len(rough))
            ratio = env_db(y[:n]) - env_db(rough[:n])
            ok_until = 0.4
            ref_ratio = np.median(ratio[int(0.2 * SR):int(0.6 * SR)])
            for i in range(int(0.4 * SR), n, 480):
                if ratio[i] < ref_ratio - 1.0: break
                ok_until = i / SR
            xf_end = min(ok_until - 0.05, 1.5); xf_start = xf_end - 0.3
            W = solve(0.05, xf_end)
            full = mix(W)
            i0, i1 = int(0.05 * SR), int(xf_end * SR)
            err = 10 * np.log10(np.sum((y[i0:i1] - full[i0:i1]) ** 2) / np.sum(y[i0:i1] ** 2))
            worst = max(worst, err)
            assert err < -30, (fn, err)
            # 交叉淡化(等功率不需要:兩者幾乎相同,線性即可)
            a, b2 = int(xf_start * SR), int(xf_end * SR)
            out = full.copy()
            out[:a] = y[:a]
            t = np.linspace(0, 1, b2 - a)[:, None]
            out[a:b2] = y[a:b2] * (1 - t) + full[a:b2] * t
            # 尾巴長度:50ms 能量低於最大值 54dB 為止(drum-samples 原本的裁切標準),最長 6 秒(ride 響到 −60dB 要 8~12 秒,
            # 解碼後太占記憶體);被 6 秒切到的最後 0.5 秒淡出,自然結束的 50ms 淡出
            e = env_db(out); keep = np.nonzero(e > e.max() - 54)[0][-1] + int(0.05 * SR)
            capped = keep > MAX_SEC * SR
            out = out[:min(keep, int(MAX_SEC * SR), len(out))]
            f = int((0.5 if capped else 0.05) * SR); out[-f:] *= (np.cos(np.linspace(0, np.pi / 2, f)) ** 2)[:, None]
            q = tpdf16(out, rng)
            q[:a] = np.round(y[:a] * 32768).astype(np.int16)      # 交叉淡化之前跟原檔逐位元相同(不重新加 dither)
            sf.write(fn, q, SR, subtype='PCM_16', format='FLAC')
            frames += len(out)
            print(f'{os.path.basename(fn)}: {len(y) / SR:.2f}s -> {len(out) / SR:.2f}s, crossfade {xf_start:.2f}-{xf_end:.2f}s, fit residual {err:.1f} dB' + (f' (原廠 rr {src})' if src != rr else ''))
        info['layers'][li]['frames'] = frames
json.dump(man, open(man_path, 'w'), indent=1)
print('worst fit residual %.1f dB' % worst)
