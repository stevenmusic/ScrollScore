"""MF Concert Guitar (Markus Fiedler) -> guitar/nylon/*.flac + manifest.json

來源:bigcat instruments 的 Kontakt 版 MF Natural Concert Guitar(原作者 SFZ,terzmagazin 收錄)
  http://www.mediafire.com/download/34v85uzzs5buwk2/MF_Natural_Concert_Guitar.nki(要用瀏覽器 User-Agent 才下載得到)
授權:CC-BY-NC-SA 3.0(另允許用於商業音樂製作);處理後的檔案同樣是 CC-BY-NC-SA 3.0。

.nki 是 Kontakt monolith:檔名表(UTF-16)後面依序接 114 個 NCW(NI 壓縮 wav)。
NCW:檔頭 01 A8 9E D6 31 01 00 00,之後 <HHIIIII> = 聲道、位元、取樣率、取樣數、區塊表位置、資料位置、資料長度;
每 512 個取樣一個區塊,每聲道 16 bytes 區塊頭(3E 9A 0C 16 簽名、base、bits、flags):
bits>0 為差分(第一個值是 base,之後累加),bits<0 為絕對值,0 為原始 PCM;flags=1 表示 mid/side。
取樣其實是單聲道(左右完全一樣)、每檔峰值正規化、標示 44000Hz。

8 個音高(E2 A2 D3 G3 B3 E4 A4 D5)× pp/p/f/ff × 2~4 次輪替(有 5 組完全重複的檔案,去掉),
另有 6 個放音聲(off)與 9 個換把位擦弦聲(fretnoise)。每個檔:
1. 量音準,FFT 重取樣校正到 0 音分(同時從 44000 轉成 48000Hz)
2. 起音前留 5ms;頻譜降噪(pp 層被正規化放大,底噪只有 -44dB)
3. 前 0.5 秒 K 加權響度對齊 -18 LKFS(放音聲 -44 LKFS,約比音符小 26dB),大小聲交給播放時的力度曲線
4. 尾巴低於峰值 -66dB 截掉,最後 0.4 秒 cos² 淡出
用法:python3 nylon_build.py <MF_Natural_Concert_Guitar.nki> <輸出目錄>
"""
import sys, os, re, json, struct, hashlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, soundfile as sf
from scipy import signal
from gtr_common import f0_cents, loud, denoise

NKI, OUT = sys.argv[1], sys.argv[2]
SR_OUT = 48000
os.makedirs(OUT, exist_ok=True)
NOTE = {'c': 0, 'd': 2, 'e': 4, 'f': 5, 'g': 7, 'a': 9, 'b': 11}
LAYERS = ['pp', 'p', 'f', 'ff']

def unpack_bits(buf, bits, n):
    a = np.frombuffer(buf, dtype=np.uint8)
    v = (np.unpackbits(a, bitorder='little')[:n * bits].reshape(n, bits).astype(np.int64) << np.arange(bits)).sum(1)
    return np.where(v >= 1 << (bits - 1), v - (1 << bits), v)

def ncw_decode(b, p):
    ch, bps, sr, ns, bo, do, ds = struct.unpack('<HHIIIII', b[p + 8:p + 32])
    nb = (ns + 511) // 512
    offs = struct.unpack('<%dI' % nb, b[p + bo:p + bo + 4 * nb])
    out = np.zeros((ch, nb * 512), np.int64)
    for k, o in enumerate(offs):
        q = p + do + o; chans = []; ms = False
        for c in range(ch):
            assert b[q:q + 4] == bytes.fromhex('160c9a3e')
            base, bits, flags = struct.unpack('<ihH', b[q + 4:q + 12]); q += 16
            if bits > 0:
                d = unpack_bits(b[q:q + bits * 64], bits, 512); q += bits * 64
                s = base + np.concatenate([[0], np.cumsum(d[:-1])])
            elif bits < 0:
                s = unpack_bits(b[q:q - bits * 64], -bits, 512); q += -bits * 64
            else:
                s = np.frombuffer(b[q:q + 512 * bps // 8], dtype='<i2').astype(np.int64); q += 512 * bps // 8
            chans.append(s); ms = ms or flags == 1
        if ch == 2 and ms: chans = [chans[0] + chans[1], chans[0] - chans[1]]
        for c in range(ch): out[c, k * 512:(k + 1) * 512] = chans[c]
    return sr, out[:, :ns] / 32768.0

b = open(NKI, 'rb').read()
names = [m.decode('utf-16-le')[:-4] for m in re.findall(rb'(?:[\x20-\x7e]\x00){4,}\.\x00n\x00c\x00w\x00', b)]
sig = bytes.fromhex('01a89ed631010000')
pos = [m.start() for m in re.finditer(re.escape(sig), b)]
assert len(names) == len(pos) == 114, (len(names), len(pos))

man = {'source': 'MF Concert Guitar by Markus Fiedler (Kontakt version by bigcat instruments), CC-BY-NC-SA 3.0',
       'mode': 'nearest', 'sr': SR_OUT, 'velRanges': [[1, 40], [41, 74], [75, 104], [105, 127]],
       'ampVeltrack': 96, 'samples': {}, 'off': {}, 'fret': {}}
seen = {}
groups = {}
for nm, p in zip(names, pos):
    sr, x = ncw_decode(b, p)
    x = x.mean(0)
    h = hashlib.md5(x.tobytes()).hexdigest()
    if h in seen: print(f'skip {nm} (same as {seen[h]})'); continue
    seen[h] = nm
    m = re.match(r'mf-nylon-guitar-([a-g])(\d)-(pp|p|ff|f)(\d)$', nm)
    off = re.match(r'mf-nylon-guitar-([a-g])(\d)-off$', nm)
    fret = re.match(r'mf-nylon-guitar-fretnoise(\d)$', nm)
    if fret:
        # 換把位時手指在纏弦上滑動的擦弦聲:整段響度對齊 -40 LKFS(比音符小約 22dB)
        y = signal.resample_poly(x, 12, 11)                         # 44000 → 48000
        on = int(np.argmax(np.abs(y) > 0.02 * np.abs(y).max())); y = y[max(0, on - int(0.003 * SR_OUT)):]
        y = y * 10 ** ((-40 - loud(y, SR_OUT)) / 20)
        fd = min(int(0.1 * SR_OUT), len(y) // 3); y[-fd:] *= np.cos(np.linspace(0, np.pi / 2, fd)) ** 2
        name = f'ny-fret{fret.group(1)}'
        sf.write(os.path.join(OUT, name + '.flac'), y.astype(np.float32), SR_OUT, subtype='PCM_16')
        man['fret'][name] = {'frames': len(y)}
        print(f'{name:14s} {nm[16:]:12s} len {len(y) / SR_OUT:5.2f}s')
        continue
    if not (m or off): continue
    g = m or off
    root = 12 * (int(g.group(2)) + 1) + NOTE[g.group(1)]
    c = f0_cents(x, sr, root) if m else 0.0
    # 44000 → 48000 並校正音準(偏高 c 音分 → 拉長 2^(c/1200) 倍)
    n2 = int(round(len(x) * SR_OUT / sr * 2 ** (c / 1200)))
    pad = 4096
    y = signal.resample(np.concatenate([x, np.zeros(pad)]), n2 + int(round(pad * SR_OUT / sr * 2 ** (c / 1200))))[:n2]
    on = int(np.argmax(np.abs(y) > 0.02 * np.abs(y).max()))
    y = y[max(0, on - int(0.005 * SR_OUT)):]
    if m: y = denoise(y, SR_OUT)
    lu = loud(y[:int(0.5 * SR_OUT)], SR_OUT)
    y = y * 10 ** (((-18 if m else -44) - lu) / 20)
    w = int(0.02 * SR_OUT); nb = len(y) // w
    env = 20 * np.log10(np.sqrt((y[:nb * w].reshape(nb, w) ** 2).mean(1)) + 1e-12)
    pk = env.max(); above = np.where(env > pk - 66)[0]
    y = y[:min(len(y), (above[-1] + 1) * w + int(0.4 * SR_OUT))]
    fd = min(int(0.4 * SR_OUT), len(y) // 3)
    y[-fd:] *= np.cos(np.linspace(0, np.pi / 2, fd)) ** 2
    peak = float(np.abs(y).max())
    if peak > 0.99: y *= 0.99 / peak; peak = 0.99
    note = g.group(1).upper() + g.group(2)
    if m:
        L = LAYERS.index(m.group(3)) + 1
        k = groups[(note, L)] = groups.get((note, L), 0) + 1
        name = f'ny-{note}-L{L}-{k}'
        man['samples'][name] = {'root': root, 'L': L, 'rr': k, 'frames': len(y), 'tuneFix': round(-c, 1), 'peak': round(20 * np.log10(peak), 1)}
    else:
        name = f'ny-{note}-off'
        man['off'][name] = {'root': root, 'frames': len(y)}
    sf.write(os.path.join(OUT, name + '.flac'), y.astype(np.float32), SR_OUT, subtype='PCM_16')
    print(f'{name:14s} {nm[16:]:8s} tune {c:+5.1f}c  len {len(y) / SR_OUT:5.1f}s  peak {20 * np.log10(peak):5.1f}dB')
json.dump(man, open(os.path.join(OUT, 'manifest.json'), 'w'), indent=1)
