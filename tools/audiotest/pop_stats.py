"""流行鋼琴演奏統計:Pop1K7(1747 首 YouTube 流行鋼琴翻彈的自動轉譜,CC BY 4.0,zenodo 13167761,只拿來量數字、不放 repo)vs App(perf_dump.mjs 輸出)
用法:python3 pop_stats.py <perf_dump 輸出目錄>(在放 pop1k7/Pop1K7/midi_analyzed/ 的目錄執行;BPM_MAX=85 只算慢歌)
指標:同時起音群內最高音−其他、最低音−中間、旋律平均−其他、力度標準差、每小節(4 拍)平均力度的標準差與 p90−p10、跟音符密度的相關、各拍輕重、旋律每半音力度、速度起伏(拍點是自動偵測,偏穩)
轉譜力度可信度:同一個轉譜模型(Kong 2021)對 MAESTRO 4 首,群內差距/力度標準差/3 秒窗起伏跟真實 MIDI 差 ≤ 2(音訊壓縮後也差不多)"""
import sys, glob, json, numpy as np, mido
from multiprocessing import Pool
def notes_pop(path):
    m = mido.MidiFile(path); tpb = m.ticks_per_beat
    # 拍(ticks/tpb)與秒:mido 依 tempo map 換秒
    t = 0.0; tick = 0; on = {}; out = []
    for msg in mido.merge_tracks(m.tracks):
        tick += msg.time
        t += mido.tick2second(msg.time, tpb, cur_tempo) if 'cur_tempo' in dir() else 0
        if msg.type == 'set_tempo': globals()['cur_tempo'] = msg.tempo
    return None
def load_pop(path):
    m = mido.MidiFile(path); tpb = m.ticks_per_beat; tempo = 500000
    tick = 0; sec = 0.0; on = {}; out = []
    for msg in mido.merge_tracks(m.tracks):
        if msg.time: sec += mido.tick2second(msg.time, tpb, tempo); tick += msg.time
        if msg.type == 'set_tempo': tempo = msg.tempo
        elif msg.type == 'note_on' and msg.velocity > 0: on.setdefault(msg.note, []).append((tick / tpb, sec, msg.velocity))
        elif msg.type in ('note_off', 'note_on') and on.get(msg.note):
            b, s, v = on[msg.note].pop(0); out.append((b, s, msg.note, v, sec - s))
    out.sort(); return np.array(out)   # beat, sec, pitch, vel, dur
def load_app(path):
    d = json.load(open(path))
    sec = {}
    for s in d['sec']: sec.setdefault(round(s[0], 5), s[2])
    out = []
    for n in d['notes']:
        out.append((n[0] * 4, sec.get(round(n[0], 5), np.nan) + n[4], n[1], n[2], 0))
    return np.array(sorted(out))
def metrics(a):
    if len(a) < 200: return None
    beat, sec, pit, vel = a[:, 0], a[:, 1], a[:, 2], a[:, 3]
    R = {}
    # 同時起音群(拍位置差 < 1/16 拍)
    order = np.argsort(beat); beat, sec, pit, vel = beat[order], sec[order], pit[order], vel[order]
    groups = []; i = 0
    while i < len(beat):
        j = i
        while j + 1 < len(beat) and beat[j + 1] - beat[i] < 0.06: j += 1
        groups.append(np.arange(i, j + 1)); i = j + 1
    # 旋律 = 每群最高音(skyline);群內最高 − 其他
    tops = np.array([g[np.argmax(pit[g])] for g in groups])
    gap = [vel[g[np.argmax(pit[g])]] - np.mean(np.delete(vel[g], np.argmax(pit[g]))) for g in groups if len(g) >= 2]
    R['群內最高音−其他'] = np.mean(gap)
    lowgap = [vel[g[np.argmin(pit[g])]] - np.mean(vel[g][(pit[g] != pit[g].min()) & (pit[g] != pit[g].max())]) for g in groups if len(g) >= 3]
    R['群內最低音−中間'] = np.mean(lowgap) if lowgap else np.nan
    # 右手旋律(≥ C4 的 skyline)vs 其他所有音
    mel = np.zeros(len(vel), bool); mel[tops[pit[tops] >= 60]] = True
    R['旋律平均−其他平均'] = vel[mel].mean() - vel[~mel].mean()
    R['力度標準差'] = vel.std()
    # 每小節(4 拍)平均力度
    bar = np.floor(beat / 4).astype(int); ub = np.unique(bar)
    bm = np.array([vel[bar == b].mean() for b in ub]); dens = np.array([(bar == b).sum() for b in ub])
    ok = dens >= 4
    R['小節力度標準差'] = bm[ok].std()
    R['小節力度 p90−p10'] = np.percentile(bm[ok], 90) - np.percentile(bm[ok], 10)
    R['小節力度~密度相關'] = np.corrcoef(bm[ok], np.log(dens[ok]))[0, 1]
    # 拍位置:每拍力度相對整體(4/4)
    pos = beat - np.floor(beat / 4) * 4
    for k, nm in ((0, '第1拍'), (1, '第2拍'), (2, '第3拍'), (3, '第4拍')):
        sel = np.abs(pos - k) < 0.06; R[nm] = vel[sel].mean() - vel.mean() if sel.any() else np.nan
    off = np.abs(pos - np.round(pos)) > 0.2; R['反拍'] = vel[off].mean() - vel.mean()
    # 旋律起伏:旋律音相對前後 8 個旋律音平均的高低 vs 力度
    mi = np.where(mel)[0]
    if len(mi) > 30:
        mp, mv = pit[mi], vel[mi]; k = 8
        loc = np.array([mp[max(0, i - k):i + k + 1].mean() for i in range(len(mp))]); locv = np.array([mv[max(0, i - k):i + k + 1].mean() for i in range(len(mv))])
        x, y = mp - loc, mv - locv
        R['旋律每半音力度'] = np.polyfit(x, y, 1)[0] if x.std() > 0 else np.nan
    # 時間:每拍秒數(拍點)→ 速度起伏
    bi = np.floor(beat + 1e-6); ub2 = np.unique(bi)
    bt = np.array([sec[bi == b].min() - (beat[bi == b].min() - b) * 0 for b in ub2])   # 每拍第一個音
    onb = np.array([abs(beat[bi == b].min() - b) < 0.06 for b in ub2])
    bb, tt = ub2[onb], bt[onb]
    if len(bb) > 20:
        ioi = np.diff(tt) / np.diff(bb); ok2 = (np.diff(bb) <= 2) & (ioi > 0)
        lt = np.log(ioi[ok2]); lt -= np.median(lt)
        R['逐拍速度起伏%'] = 100 * lt.std()
        # 小節級(4 拍平滑)
        ks = np.convolve(lt, np.ones(8) / 8, 'same'); R['樂句速度起伏%'] = 100 * ks[4:-4].std()
        R['最後 2 小節放慢%'] = 100 * (np.exp(np.mean(lt[-8:])) - 1)
    # 和弦裡最高音比其他音早幾 ms(群內)
    lead = [ (np.mean(np.delete(sec[g], np.argmax(pit[g]))) - sec[g[np.argmax(pit[g])]]) * 1000 for g in groups if len(g) >= 2]
    R['最高音提前ms'] = np.median(lead)
    return R
def bpm_of(p):
    for msg in mido.MidiFile(p).tracks[0]:
        if msg.type=='marker' and msg.text.startswith('global_bpm_'): return float(msg.text.split('_')[-1])
    return np.nan
def one(p):
    try:
        r=metrics(load_pop(p))
        if r: r['_bpm']=bpm_of(p)
        return r
    except Exception as e: return None
if __name__ == '__main__':
    files = sorted(glob.glob('pop1k7/Pop1K7/midi_analyzed/*/*.mid*'))
    with Pool(8) as pool: res = [r for r in pool.map(one, files) if r]
    import os
    lo=float(os.environ.get('BPM_MAX','999')); hi=float(os.environ.get('BPM_MIN','0'))
    res=[r for r in res if hi<=r['_bpm']<=lo]
    keys = [k for k in res[0].keys() if not k.startswith('_')]
    H = {k: np.nanmedian([r[k] for r in res if k in r]) for k in keys}
    Q = {k: (np.nanpercentile([r[k] for r in res if k in r], 25), np.nanpercentile([r[k] for r in res if k in r], 75)) for k in keys}
    A = {}
    for p in sorted(glob.glob(sys.argv[1] + '/*.json')):
        r = metrics(load_app(p)); 
        if r: A[p.split('scratchpad_')[-1][:28]] = r
    print(f'真人 {len(res)} 首(中位數 [四分位])  |  App:' + ' / '.join(A.keys()))
    for k in keys:
        print(f'{k:16s} 真人 {H[k]:7.2f} [{Q[k][0]:6.2f} ~ {Q[k][1]:6.2f}]  App ' + '  '.join(f'{r.get(k, np.nan):6.2f}' for r in A.values()))
