"""彈性速度模型訓練:ASAP 真人演奏的拍點 → 每個音的局部速度,用 App 的 rubatoFeatures() 特徵訓練梯度提升樹,寫進 index.html。

步驟:
  1. git clone ASAP(github.com/fosfrancesco/asap-dataset,只拿來訓練,不放 repo;sparse checkout metadata.csv、*_annotations.txt、*.musicxml 即可)
  2. node rubato_features.mjs <所有 xml_score.musicxml 的清單> <特徵目錄>     (讓 App 自己算特徵,保證跟網頁一致)
  3. python3 rubato_train.py <ASAP 目錄> <特徵目錄> [--cv]                 (--cv:先做 5 折分組交叉驗證,約 15 分鐘)
     → 改寫 index.html 裡 `const RUBATO_MODEL = …;` 那一行

目標值:每份演奏每一拍的 log(樂譜速度 / 實際速度) 減掉該份演奏的中位數(樂譜速度用 App 的 tempoMap 換算,譜上寫的速度變化不算彈性);
同一首曲子的多份演奏取平均(共識)當目標,每個音拿它所在那一拍的值,權重 = 音長 × 演奏份數。
2026-10 結果:213 首、30 萬個音;沒看過的曲子上預測與共識的相關係數中位數 0.42;
句讀、長音/休止前、小節第一拍、漸弱、rit. 的放慢幅度跟真人平均差 ≤ 3%;延長記號與最後一小節低估(網頁端另外用規則補)"""
import os, sys, re, json, csv, numpy as np
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.model_selection import GroupKFold
from collections import Counter
P = dict(n_estimators=200, max_depth=4, learning_rate=0.05, subsample=0.7, min_samples_leaf=200, random_state=1, loss='huber', alpha=0.9)
def load_ann(p):
    t, lab = [], []
    for l in open(p):
        a = l.rstrip('\n').split('\t')
        if len(a) >= 3: t.append(float(a[0])); lab.append(a[2])
    return np.array(t), lab
def beat_positions(lab):
    """拍點標籤(db/b,db 帶拍號)→ 每拍的全音符位置。拍長 = 小節長 / 該拍號最常見的每小節拍數(不完整小節、弱起也對)"""
    dbs = [i for i, l in enumerate(lab) if l.startswith('db')]
    if not dbs: return None
    ts_at = []; ts = None
    for i in dbs:
        p = lab[i].split(',')
        if len(p) > 1 and '/' in p[1]: n, d = p[1].split('/'); ts = (int(n), int(d))
        ts_at.append(ts)
    if ts_at[0] is None: return None
    nb = [(dbs[k + 1] if k + 1 < len(dbs) else len(lab)) - dbs[k] for k in range(len(dbs))]
    mode = {t: Counter(n for n, tt in zip(nb, ts_at) if tt == t).most_common(1)[0][0] for t in set(ts_at)}
    pos = np.full(len(lab), np.nan); w = 0.0
    for k, i0 in enumerate(dbs):
        t = ts_at[k]; bl = t[0] / t[1] / mode[t]
        for j in range(nb[k]): pos[i0 + j] = w + j * bl
        w += nb[k] * bl
    if dbs[0] > 0:
        t = ts_at[0]; bl = t[0] / t[1] / mode[t]
        for i in range(dbs[0]): pos[i] = -(dbs[0] - i) * bl
        pos -= pos[0]
    return pos
def dataset(A, FD):
    meta = list(csv.DictReader(open(A + '/metadata.csv')))
    Xs, Ys, Ws, Gs = [], [], [], []
    for folder in sorted({m['folder'] for m in meta}):
        fj = os.path.join(FD, os.path.abspath(A + '/' + folder + '/xml_score.musicxml').replace('/', '_').replace(' ', '_') + '.json')
        if not os.path.exists(fj): continue
        F = json.load(open(fj))
        if not F or not F.get('X'): continue
        _, lab = load_ann(A + '/' + folder + '/midi_score_annotations.txt')
        pos = beat_positions(lab)
        if pos is None or not np.isfinite(pos).all(): continue
        ev = np.array([[e[0], e[1]] for e in F['ev']], float); total = F['totalWhole']
        if abs(pos[-1] + (pos[-1] - pos[-2]) - total) / total > 0.03: continue   # 拍點跟 App 的時間軸對不起來(反覆記號展開不同等)
        Cpos = np.interp(pos, list(ev[:, 0]) + [total], list(ev[:, 1]) + [F['totalC']])
        ys = []
        for m in meta:
            pa = A + '/' + m['performance_annotations']
            if m['folder'] != folder or not os.path.exists(pa): continue
            tp, _ = load_ann(pa)
            if len(tp) != len(pos): continue
            ip, isc = np.diff(tp), np.diff(Cpos); ok = (ip > 0.03) & (isc > 1e-4)
            y = np.full(len(ip), np.nan); y[ok] = np.log(isc[ok] / ip[ok]); y -= np.nanmedian(y)
            y[np.abs(y) > 1.2] = np.nan   # 標注錯誤
            ys.append(y)
        if not ys: continue
        with np.errstate(all='ignore'): cons = np.nanmean(np.array(ys), 0)
        T = ev[:, 0]; X = np.array(F['X'], float); bi = np.searchsorted(pos, T + 1e-6) - 1
        yy = np.full(len(T), np.nan); okk = (bi >= 0) & (bi < len(cons)); yy[okk] = cons[bi[okk]]
        w = np.clip(np.diff(np.r_[T, total]), 1e-3, 1) * len(ys)
        m = np.isfinite(yy) & np.isfinite(X).all(1)
        Xs.append(X[m]); Ys.append(yy[m]); Ws.append(w[m]); Gs += [folder] * int(m.sum())
    return np.vstack(Xs), np.concatenate(Ys), np.concatenate(Ws), np.array(Gs)
if __name__ == '__main__':
    A, FD = sys.argv[1], sys.argv[2]
    X, Y, W, G = dataset(A, FD)
    print(f'{len(set(G))} 首、{len(Y)} 個音')
    if '--cv' in sys.argv:
        pr = np.zeros(len(Y))
        for tr, te in GroupKFold(5).split(X, Y, G): pr[te] = GradientBoostingRegressor(**P).fit(X[tr], Y[tr], sample_weight=W[tr]).predict(X[te])
        cors = [np.corrcoef(pr[G == g], Y[G == g])[0, 1] for g in set(G) if (G == g).sum() > 50 and np.std(pr[G == g]) > 0]
        print('沒看過的曲子:預測與真人共識的相關係數中位數 %.2f(IQR %.2f~%.2f)' % (np.median(cors), np.percentile(cors, 25), np.percentile(cors, 75)))
    g = GradientBoostingRegressor(**P).fit(X, Y, sample_weight=W)
    trees = []
    for est in g.estimators_[:, 0]:
        t = est.tree_
        trees.append([t.feature.tolist(), [round(float(v), 4) for v in t.threshold], t.children_left.tolist(), t.children_right.tolist(),
                      [round(float(v[0][0]) * g.learning_rate, 5) for v in t.value]])
    model = json.dumps(dict(init=round(float(g.init_.constant_[0][0]), 5), trees=trees), separators=(',', ':'))
    html = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../index.html')
    s = open(html, encoding='utf-8').read()
    s2, n = re.subn(r'const RUBATO_MODEL = .*?;   // RUBATO_MODEL_JSON', lambda _: f'const RUBATO_MODEL = {model};   // RUBATO_MODEL_JSON', s, count=1)
    assert n == 1, '找不到 RUBATO_MODEL 那一行'
    open(html, 'w', encoding='utf-8').write(s2)
    print(f'寫進 index.html:{len(trees)} 棵樹、{len(model) / 1024:.0f} KB')
