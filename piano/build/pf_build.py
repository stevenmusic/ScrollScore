"""Build ScrollScore's piano from Accurate-Salamander Grand Piano V6.2 (Yamaha C5; Salamander by Alexander Holm CC-BY 3.0,
remastered/retuned by the Accurate-Salamander project). Every velocity layer (16) of the 30 sampled notes, plus
release resonance (harmL/harmS), key-release noise (rel) and pedal noise. Trims pre-attack silence, cuts each tail
where it has decayed below the noise floor or at a register-dependent cap, fades, writes 48k/16-bit stereo FLAC
+ manifest.json (per-sample loudness, length, per-key tuning)."""
import json, os, re, sys, glob
import numpy as np, soundfile as sf, pyloudnorm as pyln, soxr
from concurrent.futures import ProcessPoolExecutor
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stereo_fix import mono_safe
PAN = lambda m: (min(108, max(21, m)) - 64.5) / 43.5 * 0.25   # 低音在左、高音在右(演奏者視角),±0.25
HERE = os.path.dirname(os.path.abspath(__file__))
SRC = f'{HERE}/acc/AccurateSalamanderGrandPianoV6.2_48khz24bit/48khz24bit/'
OUT = sys.argv[1] if len(sys.argv) > 1 else '/home/user/ScrollScore/piano/'
NOTES = ['A0','C1','D#1','F#1','A1','C2','D#2','F#2','A2','C3','D#3','F#3','A3','C4','D#4','F#4','A4','C5','D#5','F#5','A5','C6','D#6','F#6','A6','C7','D#7','F#7','A7','C8']
MIDI = {n: 21 + 3 * i for i, n in enumerate(NOTES)}
FN = lambda n: n.replace('#', 's')          # file-name safe: D#1 -> Ds1
# Velocity ranges of the 16 layers (Accurate-Salamander V6.2 sfz_base_config VEL_16)
WIDTH = [26, 6, 5, 5, 5, 5, 6, 6, 7, 8, 8, 8, 8, 8, 8, 8]
CAP = [(21, 16.0), (36, 13.0), (48, 11.0), (60, 9.0), (72, 7.0), (84, 5.0), (96, 3.5), (108, 2.5)]
def cap_for(m): return float(np.interp(m, [a for a, _ in CAP], [b for _, b in CAP]))
FLOOR_DB = float(os.environ.get('FLOOR_DB', '-66'))

def mom(x, sr):
    n = int(0.41 * sr)
    if len(x) < n: x = np.vstack([x, np.zeros((n - len(x), x.shape[1]))])
    return pyln.Meter(sr, block_size=0.4).integrated_loudness(x[:n])

def trim(x, sr, cap, floor_db=FLOOR_DB, pre=0.002, fade_max=2.0):
    a = np.abs(x).max(1); st = max(0, int(np.argmax(a > a.max() * 0.05)) - int(pre * sr))
    y = x[st:].copy(); fi = int(0.0015 * sr); y[:fi] *= np.linspace(0, 1, fi)[:, None]
    w = int(0.05 * sr); e = np.sqrt(np.convolve((y ** 2).mean(1), np.ones(w) / w, 'same'))
    above = np.nonzero(e > e.max() * 10 ** (floor_db / 20))[0]
    end = min(len(y), int(above[-1]) + int(0.05 * sr), int(cap * sr))
    y = y[:end]; f = min(int(fade_max * sr), end // 4); y[end - f:] *= np.cos(np.linspace(0, np.pi / 2, f))[:, None] ** 2
    return y, st

def write(y, path, seed):
    rng = np.random.default_rng(seed)
    z = y + (rng.random(y.shape) - rng.random(y.shape)) / 32768.0
    sf.write(path, np.clip(z, -1, 1), 48000, subtype='PCM_16', format='FLAC')

def job_main(args):
    note, v = args; m = MIDI[note]
    x, sr = sf.read(f'{SRC}{m:03d}_{note}v{v:02d}.wav')
    if sr != 48000: x = soxr.resample(x, sr, 48000, quality='VHQ'); sr = 48000   # tuning was applied as asetrate
    # spaced AB pair: some notes nearly cancel when summed to mono (C5 -10 dB); make every note mono-safe and
    # placed consistently by register, then restore the Accurate-Salamander loudness calibration
    lu0 = mom(x[int(np.argmax(np.abs(x).max(1) > np.abs(x).max() * 0.05)):], sr)
    x = mono_safe(x, sr, PAN(m))
    x *= 10 ** ((lu0 - mom(x[int(np.argmax(np.abs(x).max(1) > np.abs(x).max() * 0.05)):], sr)) / 20)
    y, st = trim(x, sr, cap_for(m))
    write(y, f'{OUT}pf-{FN(note)}-v{v}.flac', m * 100 + v)
    return note, v, round(mom(y, sr), 2), len(y), round(st / sr, 4)

def job_aux(name):
    x, sr = sf.read(f'{SRC}{name}.wav')
    if sr != 48000: x = soxr.resample(x, sr, 48000, quality='VHQ'); sr = 48000
    if name.startswith('harm'): key = MIDI[re.sub(r'^harm[LS]', '', name).replace('s', '#') if 's' in name[5:] else re.sub(r'^harm[LS]', '', name)]
    elif name.startswith('rel'): key = 20 + int(name[3:])
    else: key = 64.5
    if x.ndim == 2 and x.shape[1] == 2:
        g0 = np.sqrt((x ** 2).mean()); x = mono_safe(x, sr, PAN(key) if key != 64.5 else 0.0); x *= g0 / max(np.sqrt((x ** 2).mean()), 1e-12)
    if name.startswith('pedalD'): y, _ = trim(x, sr, 3.0, fade_max=1.2)
    elif name.startswith('harm'): y, _ = trim(x, sr, 2.4, floor_db=-60, fade_max=0.8)
    else: y, _ = trim(x, sr, 1.0, floor_db=-60, fade_max=0.15)
    write(y, f'{OUT}{FN(name)}.flac', hash(name) % 100000)
    return name, round(mom(y, sr), 2), len(y), round(20 * np.log10(np.abs(y).max()), 2)

if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    for f in glob.glob(f'{OUT}*.flac'): os.remove(f)
    with ProcessPoolExecutor(4) as ex:
        R = list(ex.map(job_main, [(n, v) for n in NOTES for v in range(1, 17)]))
        aux = [os.path.basename(f)[:-4] for f in glob.glob(f'{SRC}*.wav') if re.match(r'(harm[LS]|rel|pedal)', os.path.basename(f))]
        A = list(ex.map(job_aux, sorted(aux)))
    tune = {}
    for line in open(f'{HERE}/acc/src/tuned_sfz.txt'):
        mm = re.match(r'(\d{3})_\S+\s+([+-]?\d+(?:\.\d+)?)', line)
        if mm: tune[int(mm.group(1))] = float(mm.group(2))
    # d = (Accurate level) - (original V3 level) per sample: the V3 sfz sets release-resonance / key-noise / pedal
    # volumes relative to the original recordings, so the app converts them with this offset
    ev = {k: {(r[0], r[1]): r[2] for r in np.load(f'{HERE}/pianoeval_{k}.npy', allow_pickle=True)} for k in ('v3', 'acc')}
    D = {f'{FN(n)}-v{v}': round(float(ev['acc'][(n, v)] - ev['v3'][(n, v)]), 2) for n in NOTES for v in range(1, 17)}
    lo = 1; ranges = []
    for w in WIDTH: ranges.append([lo, lo + w - 1]); lo += w
    man = dict(piano='Accurate-Salamander Grand Piano V6.2 (Yamaha C5) - Salamander Grand Piano V3 by Alexander Holm, CC-BY 3.0',
               notes={n: MIDI[n] for n in NOTES}, velRanges=ranges, ampVeltrack=98.5,
               tune={str(k): tune.get(k, 0) for k in range(21, 109)},
               samples={f'{FN(n)}-v{v}': dict(lufs=lu, frames=fr, d=D[f'{FN(n)}-v{v}']) for n, v, lu, fr, st in R},
               aux={FN(n): dict(lufs=lu, frames=fr, peak=pk) for n, lu, fr, pk in A})
    json.dump(man, open(f'{OUT}manifest.json', 'w'), indent=0)
    tot = sum(fr for *_, fr, st in R)
    print(f'main samples {len(R)}, aux {len(A)}; decoded stereo float32 {tot * 8 / 1e6:.0f} MB; mean length {tot / len(R) / 48000:.1f}s')
    print('onset trims (s):', sorted({st for *_, st in R})[:5], '...', max(st for *_, st in R))
