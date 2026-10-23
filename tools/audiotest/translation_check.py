#!/usr/bin/env python3
"""多裝置轉譯檢查:同一份混音在 6 種播放裝置上聽起來會怎樣(離線模擬)。

用法:python3 translation_check.py a.wav [b.wav ...] [--json out.json]
輸入:ScrollScore 離線輸出(render / rnw.mjs 存的 wav,立體聲;33 位元浮點或 16 位元都可以)。

**重要:下面的裝置頻率響應都是「文獻與常見量測的近似曲線」,不是某一支手機/耳機的實測。**
來源是常見的量測報告與產品評測的典型形狀(小喇叭低頻衰減、耳道共振、車內低頻增強…),
目的是比較「改前 / 改後」哪一個在各種裝置上比較安全,不是預測某一台的聲音。
每個裝置 = pre(放大器端的補償 EQ)→ 軟削波(喇叭/放大器的振幅極限,tanh)→ acoustic(喇叭 + 房間的聲學響應)。
削波的 c 是相對於數位滿刻度的極限:音量固定(同一個裝置音量設定),所以訊號越大聲越容易削波,
這正是「播放音量變化」會影響的部分。

每個裝置輸出:
  頻段能量比例(輸出端):低 <250Hz、中低 250~1k、中 1k~4k、高 >4k(%)
  clip:軟削波失真 = 10log10(失真能量 / 訊號能量) dB(越小越好)、超過削波點的 20ms 區塊比例(%)
  clarity:旋律清晰度代理 = 10log10(E[1~4kHz] / E[100~500Hz]) dB(越大越清楚;低頻太多把旋律蓋住時變小)
  mono:單聲道相容 = 響度(L+R 混成單聲道,兩邊一樣) − 響度(立體聲),LUFS 差(負的越多 = 相消越嚴重)
另外印出訊號本身(不經裝置)的 LUFS 與頻段比例。
"""
import sys, json
import numpy as np
import soundfile as sf
import pyloudnorm as pn
from scipy.signal import butter, sosfilt, tf2sos


# ---- RBJ biquad(回傳 sos 一列) ----
def _sos(b, a):
    return tf2sos(b, a)


def peaking(fs, f0, gdb, q):
    A = 10 ** (gdb / 40); w = 2 * np.pi * f0 / fs; al = np.sin(w) / (2 * q); c = np.cos(w)
    return _sos([1 + al * A, -2 * c, 1 - al * A], [1 + al / A, -2 * c, 1 - al / A])


def lowshelf(fs, f0, gdb, s=1.0):
    A = 10 ** (gdb / 40); w = 2 * np.pi * f0 / fs; c = np.cos(w)
    al = np.sin(w) / 2 * np.sqrt((A + 1 / A) * (1 / s - 1) + 2); sq = 2 * np.sqrt(A) * al
    b = [A * ((A + 1) - (A - 1) * c + sq), 2 * A * ((A - 1) - (A + 1) * c), A * ((A + 1) - (A - 1) * c - sq)]
    a = [(A + 1) + (A - 1) * c + sq, -2 * ((A - 1) + (A + 1) * c), (A + 1) + (A - 1) * c - sq]
    return _sos(b, a)


def highshelf(fs, f0, gdb, s=1.0):
    A = 10 ** (gdb / 40); w = 2 * np.pi * f0 / fs; c = np.cos(w)
    al = np.sin(w) / 2 * np.sqrt((A + 1 / A) * (1 / s - 1) + 2); sq = 2 * np.sqrt(A) * al
    b = [A * ((A + 1) + (A - 1) * c + sq), -2 * A * ((A - 1) + (A + 1) * c), A * ((A + 1) + (A - 1) * c - sq)]
    a = [(A + 1) - (A - 1) * c + sq, 2 * ((A - 1) - (A + 1) * c), (A + 1) - (A - 1) * c - sq]
    return _sos(b, a)


def hp(fs, f0, order=2):
    return butter(order, f0, 'hp', fs=fs, output='sos')


def lp(fs, f0, order=2):
    return butter(order, f0, 'lp', fs=fs, output='sos')


def chain(*parts):
    return np.vstack([p for p in parts if p is not None and len(p)])


def devices(fs):
    """6 種裝置的近似模型。mono = 左右相加成單聲道;c = 軟削波極限(None = 不削波)。"""
    return {
        # 手機內建喇叭(iPhone/一般旗艦機):單聲道、放大器把低頻補償 +8dB(350Hz 以下)後推小喇叭,喇叭 450Hz 以下幾乎發不出
        '手機喇叭': dict(mono=True, c=0.7,
                     pre=chain(hp(fs, 120), lowshelf(fs, 350, 8)),
                     acoustic=chain(hp(fs, 450), peaking(fs, 1500, 3, 1.2), peaking(fs, 3500, 2, 1.0))),
        # 耳塞(AirPods 類):立體聲、低頻到 ~60Hz、耳道共振 ~2.7kHz +5dB、8kHz 以上緩降;不削波
        '耳塞': dict(mono=False, c=None, pre=None,
                   acoustic=chain(hp(fs, 50), lowshelf(fs, 120, 1.5), peaking(fs, 2700, 5, 1.6), peaking(fs, 6500, -3, 2.0), lp(fs, 14000))),
        # 筆電喇叭:近乎單聲道(兩顆很近)、300Hz 以下衰減快、800Hz~1.5kHz 箱體共振、高頻 12kHz 以上掉
        '筆電喇叭': dict(mono=True, c=0.75,
                     pre=chain(hp(fs, 100), lowshelf(fs, 300, 4)),
                     acoustic=chain(hp(fs, 250), peaking(fs, 1000, 3, 1.0), peaking(fs, 4500, -2, 1.5), lp(fs, 13000))),
        # 汽車:立體聲、低頻被車廂增強(80Hz +5)、250~500Hz 悶(-3)、高頻被座椅/玻璃吸收(6kHz 以上 -4),不削波
        '汽車': dict(mono=False, c=None, pre=None,
                   acoustic=chain(hp(fs, 35), lowshelf(fs, 90, 5), peaking(fs, 350, -3, 0.8), highshelf(fs, 6000, -4))),
        # 監聽喇叭:平坦,立體聲,當對照
        '監聽': dict(mono=False, c=None, pre=None, acoustic=None),
        # 電視:近乎單聲道、150Hz 以下衰減、箱體共振 400Hz 附近 +3、高頻 10kHz 以上掉、小喇叭削波
        '電視': dict(mono=True, c=0.8,
                   pre=chain(hp(fs, 80), lowshelf(fs, 250, 3)),
                   acoustic=chain(hp(fs, 150), peaking(fs, 400, 3, 0.9), peaking(fs, 3000, -2, 1.0), lp(fs, 11000))),
    }


def softclip(y, c):
    return c * np.tanh(y / c)


def band_fracs(y, fs, edges=(20, 250, 1000, 4000, 20000)):
    tot = np.mean(y ** 2) + 1e-20
    out = []
    for lo, hi in zip(edges[:-1], edges[1:]):
        s = butter(4, [lo, min(hi, fs / 2 * 0.99)], 'bp', fs=fs, output='sos')
        out.append(100 * np.mean(sosfilt(s, y) ** 2) / tot)
    return out


def band_e(y, fs, lo, hi):
    s = butter(4, [lo, min(hi, fs / 2 * 0.99)], 'bp', fs=fs, output='sos')
    return np.mean(sosfilt(s, y) ** 2) + 1e-20


def lufs(x, fs):
    return pn.Meter(fs).integrated_loudness(x)


def run_device(name, d, x, fs):
    y = x.mean(1) if d['mono'] else x.T
    mono_in = d['mono']

    def proc(sig):
        z = sig
        if d['pre'] is not None:
            z = sosfilt(d['pre'], z, axis=-1)
        return z

    z = proc(y)
    if d['c'] is not None:
        zc = softclip(z, d['c'])
        dist = 10 * np.log10(np.sum((zc - z) ** 2) / (np.sum(z ** 2) + 1e-20) + 1e-20)
        b = int(0.02 * fs)
        zz = np.abs(z) if mono_in else np.maximum(np.abs(z[0]), np.abs(z[1]))
        k = len(zz) // b
        over = 100 * np.mean(zz[:k * b].reshape(k, b).max(1) > d['c'])
    else:
        zc, dist, over = z, float('nan'), float('nan')
    out = sosfilt(d['acoustic'], zc, axis=-1) if d['acoustic'] is not None else zc
    m = out if mono_in else out.mean(0)          # 頻段、清晰度用單聲道代表
    fr = band_fracs(m, fs)
    clar = 10 * np.log10(band_e(m, fs, 1000, 4000) / band_e(m, fs, 100, 500))
    return dict(low=fr[0], lowmid=fr[1], mid=fr[2], high=fr[3], dist=dist, over=over, clarity=clar)


def analyze(path):
    x, fs = sf.read(path, dtype='float64')
    x = x[:, :2] if x.ndim == 2 else np.stack([x, x], 1)
    res = dict(file=path, fs=fs)
    res['lufs'] = lufs(x, fs)
    res['peak'] = 20 * np.log10(np.abs(x).max() + 1e-12)
    mono = x.mean(1)
    res['src_bands'] = band_fracs(mono, fs)
    monoLoud = lufs(np.stack([mono, mono], 1), fs)
    res['mono_loss'] = monoLoud - res['lufs']
    res['devices'] = {n: run_device(n, d, x, fs) for n, d in devices(fs).items()}
    return res


def show(r):
    print('== %s' % r['file'])
    sb = r['src_bands']
    print('訊號 LUFS %.2f 峰值 %.2f dBFS | 頻段%% 低<250 %.1f 中低250-1k %.1f 中1-4k %.1f 高>4k %.1f | 單聲道相容(L+R 響度 − 立體聲) %+.2f LU'
          % (r['lufs'], r['peak'], sb[0], sb[1], sb[2], sb[3], r['mono_loss']))
    print('%-8s %6s %7s %6s %6s | %9s %9s | %9s' % ('裝置', '低%', '中低%', '中%', '高%', '削波失真dB', '過限區塊%', '清晰度dB'))
    for n, v in r['devices'].items():
        ds = '—' if np.isnan(v['dist']) else '%.1f' % v['dist']
        ov = '—' if np.isnan(v['over']) else '%.1f' % v['over']
        print('%-8s %6.1f %7.1f %6.1f %6.1f | %9s %9s | %9.1f' % (n, v['low'], v['lowmid'], v['mid'], v['high'], ds, ov, v['clarity']))


if __name__ == '__main__':
    argv = sys.argv[1:]
    jpath = None
    if '--json' in argv:
        i = argv.index('--json'); jpath = argv[i + 1]; del argv[i:i + 2]
    allr = []
    for f in argv:
        r = analyze(f); show(r); allr.append(r)
    if jpath:
        json.dump(allr, open(jpath, 'w'), ensure_ascii=False, indent=1, default=float)
