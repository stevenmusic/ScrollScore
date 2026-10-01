import sys, numpy as np, soundfile as sf
from scipy.signal import resample_poly
x, sr = sf.read(sys.argv[1]); print('NaN:', np.isnan(x).any())
segs = [('100Hz',0,.5),('1k',.5,1),('5k',1,1.5),('10k',1.5,2),('15k',2,2.5),('18k',2.5,3),('20k',3,3.5),('impulses',3.7,4.7),('bass+bursts',4.7,5.7)]
up = np.abs(resample_poly(x, 16, 1, axis=0)).max(1)   # 整段一起升取樣(切段再升取樣,邊緣的截斷會假造出峰值)
for name,a,b in segs:
    tp = 20*np.log10(up[int(a*sr)*16:int(b*sr)*16].max())
    print(f'{name:12s} TP16x {tp:6.2f} dBTP')
