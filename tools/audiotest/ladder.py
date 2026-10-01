"""力度階梯(gen_piano_dyn.py)每段的響度:python3 ladder.py a.wav [b.wav ...];每段 2 小節 @96 = 5 秒"""
import sys, numpy as np, soundfile as sf, pyloudnorm as pyln
for p in sys.argv[1:]:
    x, sr = sf.read(p, always_2d=True); x = x[:, :2]
    m = pyln.Meter(sr, block_size=0.4)
    seg = [m.integrated_loudness(x[int(i * 5 * sr):int((i * 5 + 5) * sr)]) for i in range(6)]
    print(p.split('/')[-2] + '/' + p.split('/')[-1], ' '.join(f'{v:6.1f}' for v in seg), ' pp→ff %.1f dB' % (seg[-1] - seg[0]))
