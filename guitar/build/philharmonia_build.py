"""Philharmonia Orchestra 古典吉他取樣 → ScrollScore guitar/classical/ 的 FLAC + manifest.json
來源:Philharmonia Orchestra sound samples(CC BY-SA 3.0),guitar_<音>_very-long_<forte|piano>_normal.mp3(MP3 96kbps、單聲道、44.1kHz)
處理:65Hz 高通(有幾個檔在音符前有碰到琴身的低頻雜音;吉他最低音 E2 = 82Hz)、對齊起音(去掉前面的空白,留 3ms)、估音準寫進 manifest 的 tune(音分,播放時校正,不重新取樣)、
     響度對齊到 −20 LUFS(力度交給播放時的 amp_veltrack 曲線)、尾巴淡出、存 16-bit FLAC(來源是 96kbps MP3,24-bit 沒有多的細節)。處理後的檔案同樣是 CC BY-SA 3.0
用法:python3 guitar/build/philharmonia_build.py <mp3 目錄> guitar/classical(HarmonyHands、HarmonyMap 也從這裡讀)"""
import sys, os, re, json, subprocess, numpy as np, soundfile as sf, pyloudnorm as pyln
from scipy.signal import butter, sosfiltfilt
src, dst = sys.argv[1], sys.argv[2]
os.makedirs(dst, exist_ok=True)
NAMES = ["C", "Cs", "D", "Ds", "E", "F", "Fs", "G", "Gs", "A", "As", "B"]
SR = 44100
meter = pyln.Meter(SR)
HP = butter(4, 65, "highpass", fs=SR, output="sos")
def midi_of(n):
    m = re.match(r"([A-G]s?)(\d)", n); return (int(m.group(2)) + 1) * 12 + NAMES.index(m.group(1))
def decode(p):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", p, "-f", "f32le", "-ac", "1", "-ar", str(SR), "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).astype(np.float64)
def f0_cents(x, midi):
    # 起音後 0.2~1.0 秒的頻譜:在第 1、2、3 泛音附近(±50 音分)找最高的峰,拋物線內插後換算回基頻,跟理論音高比較
    seg = x[int(0.2 * SR):int(1.0 * SR)]
    seg = (seg - seg.mean()) * np.hanning(len(seg))
    N = 1 << 19
    mag = np.abs(np.fft.rfft(seg, N)); df = SR / N
    f_ref = 440 * 2 ** ((midi - 69) / 12)
    best = None
    for h in (1, 2, 3):
        lo, hi = int(h * f_ref * 2 ** (-50 / 1200) / df), int(h * f_ref * 2 ** (50 / 1200) / df) + 1
        k = lo + int(np.argmax(mag[lo:hi]))
        a, b, c = np.log(mag[k - 1] + 1e-12), np.log(mag[k] + 1e-12), np.log(mag[k + 1] + 1e-12)
        kk = k + 0.5 * (a - c) / (a - 2 * b + c)
        if best is None or mag[k] > best[0]: best = (mag[k], kk * df / h)
    return 1200 * np.log2(best[1] / f_ref)
man = {"source": "Philharmonia Orchestra sound samples (CC BY-SA 3.0), processed by guitar/build/philharmonia_build.py",
       "mode": "nearest", "sr": SR, "velRanges": [[1, 79], [80, 127]], "ampVeltrack": 96, "samples": {}}
rows = []
for f in sorted(os.listdir(src)):
    m = re.match(r"guitar_([A-G]s?\d)_very-long_(forte|piano)_normal\.mp3$", f)
    if not m: continue
    note, dyn = m.groups(); midi = midi_of(note); L = 2 if dyn == "forte" else 1
    x = sosfiltfilt(HP, decode(os.path.join(src, f)))
    # 起音:5ms 視窗的 RMS 第一次到最大值的 1/4(雜音不會到這麼大)
    w = int(0.005 * SR); rms = np.sqrt(np.convolve(x * x, np.ones(w) / w, "same"))
    on = int(np.argmax(rms > rms.max() * 0.25)); on = max(0, on - int(0.003 * SR))
    x = x[on:]
    cents = f0_cents(x, midi)
    loud = meter.integrated_loudness(x[:int(min(len(x), 3 * SR))])
    x = x * 10 ** ((-20 - loud) / 20)
    fade = int(0.3 * SR); x[-fade:] *= np.cos(np.linspace(0, np.pi / 2, fade)) ** 2
    if np.abs(x).max() > 0.99: x *= 0.99 / np.abs(x).max()
    name = f"ph-{note}-L{L}"
    sf.write(os.path.join(dst, name + ".flac"), x.astype(np.float32), SR, subtype="PCM_16")
    man["samples"][name] = {"root": midi, "L": L, "rr": 1, "tune": round(float(cents), 1), "frames": len(x)}
    rows.append((midi, note, dyn, round(float(cents), 1), round(len(x) / SR, 1), round(loud, 1), round(on / SR * 1000)))
json.dump(man, open(os.path.join(dst, "manifest.json"), "w"), ensure_ascii=False, indent=0)
for r in sorted(rows): print(*r)
