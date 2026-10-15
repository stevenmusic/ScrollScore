"""彈性速度分析(用法:python3 rubato_analyze.py <ASAP 目錄> <rubato_features.mjs 輸出目錄>;第一次做 5 折交叉驗證約 15 分鐘,存 cv_pred.npy):5 折分組交叉驗證(沒看過的曲子)的預測,套上 App 的後處理(平滑 ±1/8 全音符、中位數歸零、快慢不對稱倍率),
跟 ASAP 真人(多位鋼琴家共識 + 個別演奏)比:整體相關、起伏大小、作曲家/風格、各種位置的平均快慢。"""
import sys, os, json, numpy as np, csv
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rubato_train as RT
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.model_selection import GroupKFold
A, FD = sys.argv[1], sys.argv[2]
NAMES = ["ioiNext", "ioiPrev", "dur", "restAfter", "bndHere", "bndNext", "barPhase", "downbeat", "toEnd", "fermata", "fermataNext",
  "accent", "tenuto", "dynLevel", "dynSlope", "wedge", "pitchZ", "leapNext", "contour", "chord", "density", "slurEnd",
  "phraseX", "phraseLen", "toPhraseEnd", "rit", "ritAge", "accel", "atempo", "beatsPerBar", "bpm"]
fi = {n: i for i, n in enumerate(NAMES)}
# 跟 RT.dataset 一樣,但多回傳每個音的時間、曲長與個別演奏的起伏
meta = list(csv.DictReader(open(A + '/metadata.csv')))
rows = []
for folder in sorted({m['folder'] for m in meta}):
    fj = os.path.join(FD, os.path.abspath(A + '/' + folder + '/xml_score.musicxml').replace('/', '_').replace(' ', '_') + '.json')
    if not os.path.exists(fj): continue
    F = json.load(open(fj))
    if not F or not F.get('X'): continue
    _, lab = RT.load_ann(A + '/' + folder + '/midi_score_annotations.txt')
    pos = RT.beat_positions(lab)
    if pos is None or not np.isfinite(pos).all(): continue
    ev = np.array([[e[0], e[1]] for e in F['ev']], float); total = F['totalWhole']
    if abs(pos[-1] + (pos[-1] - pos[-2]) - total) / total > 0.03: continue
    Cpos = np.interp(pos, list(ev[:, 0]) + [total], list(ev[:, 1]) + [F['totalC']])
    ys = []
    for m in meta:
        pa = A + '/' + m['performance_annotations']
        if m['folder'] != folder or not os.path.exists(pa): continue
        tp, _ = RT.load_ann(pa)
        if len(tp) != len(pos): continue
        ip, isc = np.diff(tp), np.diff(Cpos); ok = (ip > 0.03) & (isc > 1e-4)
        y = np.full(len(ip), np.nan); y[ok] = np.log(isc[ok] / ip[ok]); y -= np.nanmedian(y); y[np.abs(y) > 1.2] = np.nan
        ys.append(y)
    if not ys: continue
    with np.errstate(all='ignore'): cons = np.nanmean(np.array(ys), 0)
    T = ev[:, 0]; X = np.array(F['X'], float); bi = np.searchsorted(pos, T + 1e-6) - 1
    okk = (bi >= 0) & (bi < len(cons))
    yy = np.full(len(T), np.nan); yy[okk] = cons[bi[okk]]
    indiv = np.full((len(ys), len(T)), np.nan)
    for k, y in enumerate(ys): indiv[k, okk] = y[bi[okk]]
    w = np.clip(np.diff(np.r_[T, total]), 1e-3, 1) * len(ys)
    m = np.isfinite(yy) & np.isfinite(X).all(1)
    rows.append(dict(folder=folder, X=X[m], Y=yy[m], W=w[m], T=T[m], total=total, ind=indiv[:, m], np=len(ys)))
X = np.vstack([r['X'] for r in rows]); Y = np.concatenate([r['Y'] for r in rows]); W = np.concatenate([r['W'] for r in rows])
G = np.concatenate([[i] * len(r['Y']) for i, r in enumerate(rows)])
print(f'{len(rows)} 首、{len(Y)} 個音')
if os.path.exists('cv_pred.npy'): pr = np.load('cv_pred.npy')
else:
    pr = np.zeros(len(Y))
    for tr, te in GroupKFold(5).split(X, Y, G):
        pr[te] = GradientBoostingRegressor(**RT.P).fit(X[tr], Y[tr], sample_weight=W[tr]).predict(X[te])
    np.save('cv_pred.npy', pr)
def post(p, T, X, amount=1.8, sm=0.125, neg=None, final=0.83):
    # App:±sm 全音符時間加權平滑、中位數歸零、×amount、延長記號/曲尾規則、範圍 0.45~1.6
    s = np.array([np.mean(p[(T >= t - sm) & (T <= t + sm)]) for t in T])
    s = s - np.median(s); s = np.where(s < 0, s * (neg if neg is not None else amount), s * amount)
    mult = np.exp(s)
    mult = np.where(X[:, fi['fermata']] > 0, np.minimum(mult, 0.58), mult)
    mult = np.where(X[:, fi['fermataNext']] > 0, np.minimum(mult, 0.62), mult)
    mult = np.where(X[:, fi['toEnd']] < np.log(2), mult * final, mult)   # toEnd 是 log(1+小節數)
    return np.log(np.clip(mult, 0.45, 1.6))
out = []
for i, r in enumerate(rows):
    sel = G == i; p = pr[sel]; app = post(p, r['T'], r['X'])
    cons = r['Y']; ind = r['ind']
    c = np.corrcoef(app, cons)[0, 1] if np.std(app) > 0 else np.nan
    ci = [np.corrcoef(np.nan_to_num(ind[k]), cons)[0, 1] for k in range(len(ind))] if len(ind) > 1 else []
    sd_ind = np.nanmean([np.nanstd(ind[k]) for k in range(len(ind))])
    out.append(dict(folder=r['folder'], comp=r['folder'].split('/')[0], n=len(cons), corr=c, sd_app=np.std(app), sd_cons=np.std(cons), sd_ind=sd_ind, np=r['np']))
import collections
print('\n整體:相關係數中位數 %.2f;起伏(log 標準差)App %.3f、共識 %.3f、個別演奏 %.3f' % (np.nanmedian([o['corr'] for o in out]), np.median([o['sd_app'] for o in out]), np.median([o['sd_cons'] for o in out]), np.median([o['sd_ind'] for o in out])))
print('\n作曲家    首數  相關   App起伏  個別真人起伏  比例')
by = collections.defaultdict(list)
for o in out: by[o['comp']].append(o)
for k, v in sorted(by.items(), key=lambda kv: -len(kv[1])):
    print(f'{k:12s} {len(v):3d}  {np.nanmedian([o["corr"] for o in v]):.2f}   {np.median([o["sd_app"] for o in v]):.3f}    {np.median([o["sd_ind"] for o in v]):.3f}     {np.median([o["sd_app"] / o["sd_ind"] for o in v]):.2f}')
# 各種位置:真人共識 vs App 的平均快慢(%,負 = 比平常慢)
APP = np.concatenate([post(pr[G == i], r['T'], r['X']) for i, r in enumerate(rows)])
T_all = np.concatenate([r['T'] for r in rows]); TOT = np.concatenate([[r['total']] * len(r['Y']) for r in rows])
ctx = {
  '句尾(離句尾 < 1/4 小節)': X[:, fi['toPhraseEnd']] < 0.25,
  '句中': (X[:, fi['phraseX']] > 0.3) & (X[:, fi['phraseX']] < 0.7),
  '樂句開頭(前 10%)': X[:, fi['phraseX']] < 0.1,
  '小節第一拍': X[:, fi['downbeat']] > 0,
  '休止前': X[:, fi['restAfter']] > 0,
  '延長記號': X[:, fi['fermata']] > 0,
  '最後一小節': X[:, fi['toEnd']] < np.log(2),
  '曲子開頭(前 2 小節)': T_all < 2 * (1 / 1),
  'rit. 文字後': X[:, fi['rit']] > 0,
  'a tempo 後': X[:, fi['atempo']] > 0,
  '漸強': X[:, fi['wedge']] > 0, '漸弱': X[:, fi['wedge']] < 0,
  '很密的快音群(密度前 10%)': X[:, fi['density']] > np.percentile(X[:, fi['density']], 90),
  '長音(音長前 10%)': X[:, fi['dur']] > np.percentile(X[:, fi['dur']], 90),
  '高音旋律(音高前 10%)': X[:, fi['pitchZ']] > np.percentile(X[:, fi['pitchZ']], 90),
}
print('\n位置                         數量    真人共識   App     差(App−真人)')
for k, m in ctx.items():
    if m.sum() < 50: continue
    h = 100 * (np.exp(np.average(Y[m], weights=W[m])) - 1); a = 100 * (np.exp(np.average(APP[m], weights=W[m])) - 1)
    print(f'{k:24s} {m.sum():7d}  {h:+6.1f}%  {a:+6.1f}%   {a - h:+5.1f}')
json.dump(out, open('per_piece.json', 'w'), default=float)
