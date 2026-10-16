"""真人鼓手的力度/時間統計(對照 App 的 humanizeDrumHit / computeDrumPerformance 用)
用法:python3 gmd_stats.py <groove 目錄>(Groove MIDI Dataset v1.0.0 midionly 解壓後的 groove/,Magenta,CC BY 4.0,
     https://storage.googleapis.com/magentadata/datasets/groove/groove-v1.0.0-midionly.zip;只拿來測試,不放 repo;另需 pip install mido)
只用 4/4 的 beat(不含 fill)。印出:各鼓件力度、hi-hat/ride 各拍位置的相對力度、小鼓 backbeat 與鬼音、各鼓件時間偏移、
同一拍各肢體的時間差、扣掉節奏型後的力度起伏與相鄰兩下的相關(搖滾/流行、扣掉局部速度漂移的版本在最後)。
App 這邊:shot.mjs --eval 跑 computeDrumSongDynamics(); computeDrumPerformance(); 再對每個鼓音呼叫 humanizeDrumHit(ev, n) 取 s 與 dt。
2026-10 結果(搖滾/流行):hi-hat 力度殘差 15.5、lag-1 0.08;同一拍大鼓−hi-hat 時間差中位數 9.5ms、小鼓−hi-hat 6.3ms,
大鼓/小鼓平均比 hi-hat 早 3ms;hi-hat 第 1~4 拍 +12.7/+19.9/+7.0/+19.4;ride 重音約 hi-hat 的 6 成;大鼓正拍 66、其他 52"""
import sys, csv, mido, numpy as np, collections
G=sys.argv[1].rstrip('/')+'/'
CLS={36:'kick',38:'snare',40:'snare',37:'rim',42:'hhC',22:'hhC',44:'hhP',46:'hhO',26:'hhO',51:'ride',59:'ride',53:'bell',49:'crash',55:'crash',57:'crash',52:'crash',48:'tom',50:'tom',45:'tom',47:'tom',43:'tom',58:'tom'}
rows=[r for r in csv.DictReader(open(G+'info.csv')) if r['beat_type']=='beat' and r['time_signature']=='4-4']
print('files',len(rows), collections.Counter(r['style'].split('/')[0] for r in rows).most_common(8))
H=[]  # per hit: file, cls, vel, pos16 (0..15), off_ms, t, bpm
for fi,r in enumerate(rows):
    mid=mido.MidiFile(G+r['midi_filename']); bpm=float(r['bpm'])
    t=0; tempo=None; notes=[]
    for msg in mido.merge_tracks(mid.tracks):
        t+=mido.tick2second(msg.time, mid.ticks_per_beat, tempo or 500000) if True else 0
        if msg.type=='set_tempo': tempo=msg.tempo
        if msg.type=='note_on' and msg.velocity>0 and msg.note in CLS: notes.append((t,msg.note,msg.velocity))
    q=60/bpm/4
    for (tt,nn,vv) in notes:
        k=round(tt/q); off=(tt-k*q)*1000
        H.append((fi,CLS[nn],vv,k%16,off,tt,bpm,k, r['style'].split('/')[0]))
import numpy as np
A=np.array([(h[0],h[2],h[3],h[4],h[5],h[6],h[7]) for h in H]); C=np.array([h[1] for h in H]); ST=np.array([h[8] for h in H])
f,vel,pos,off,tt,bpm,k=A.T
print('hits',len(H))
def within_sd(mask,x):
    # sd after removing each file's mean (drummer intrinsic variation within a performance)
    vals=[]; 
    for fid in np.unique(f[mask]):
        m=mask&(f==fid)
        if m.sum()>=8: vals.append(x[m]-x[m].mean())
    v=np.concatenate(vals); return v.std(), len(v)
print('\n== velocity per class (mean, within-file sd) ==')
for c in ['kick','snare','hhC','hhO','hhP','ride','crash','tom','rim']:
    m=C==c
    if m.sum()<50: continue
    print(f'{c:6s} n={m.sum():6d} mean {vel[m].mean():5.1f} p10 {np.percentile(vel[m],10):4.0f} p90 {np.percentile(vel[m],90):4.0f} within-file sd {within_sd(m,vel)[0]:4.1f}')
print('\n== hh closed / ride velocity by grid position (within-file mean-removed) ==')
for c in ['hhC','ride']:
    m=C==c; rel=np.zeros_like(vel)
    for fid in np.unique(f[m]):
        mm=m&(f==fid); rel[mm]=vel[mm]-vel[mm].mean()
    for name,ps in [('quarter',[0,4,8,12]),('8th-and',[2,6,10,14]),('16th e/a',[1,3,5,7,9,11,13,15])]:
        mm=m&np.isin(pos,ps); print(f'  {c} {name:9s} n={mm.sum():6d} rel vel {rel[mm].mean():+5.1f}  abs mean {vel[mm].mean():5.1f}')
    for name,ps in [('beat1',[0]),('beat2',[4]),('beat3',[8]),('beat4',[12])]:
        mm=m&np.isin(pos,ps); print(f'  {c} {name} rel {rel[mm].mean():+5.1f}')
print('\n== snare: backbeat vs other, ghost notes ==')
m=C=='snare'
bb=m&np.isin(pos,[4,12]); oth=m&~np.isin(pos,[4,12])
print(f'  backbeat mean {vel[bb].mean():.1f} (n={bb.sum()}), others mean {vel[oth].mean():.1f} (n={oth.sum()})')
# ghost = off-backbeat snare with vel < 60% of file's backbeat mean
g=[];r=[]
for fid in np.unique(f[bb]):
    mb=bb&(f==fid); mo=oth&(f==fid); 
    if mb.sum()<4 or mo.sum()<4: continue
    ref=vel[mb].mean(); gv=vel[mo][vel[mo]<0.6*ref]
    if len(gv): g.append(gv.mean()/ref); r.append(ref)
print(f'  ghost/backbeat velocity ratio median {np.median(g):.2f} (files {len(g)}), backbeat median {np.median(r):.0f}')
print(f'  kick on-quarter vs off: {vel[(C=="kick")&np.isin(pos,[0,4,8,12])].mean():.1f} vs {vel[(C=="kick")&~np.isin(pos,[0,4,8,12])].mean():.1f}')
print('\n== timing (ms re 16th grid): per class mean & within-file sd ==')
mstraight = ~np.isin(ST,['jazz','afrobeat','afrocuban','neworleans','latin','reggae','dance'])  # styles with swing/shuffle feel excluded
for c in ['kick','snare','hhC','ride']:
    m=(C==c)&mstraight&(np.abs(off)<60)
    sd,n=within_sd(m,off)
    print(f'  {c:6s} mean offset {off[m].mean():+5.1f} ms, within-file sd {sd:4.1f} ms (n={n})')
bbm=(C=='snare')&np.isin(pos,[4,12])&mstraight&(np.abs(off)<60)
print(f'  snare backbeat mean offset {off[bbm].mean():+.1f} vs hhC same files {off[(C=="hhC")&mstraight&(np.abs(off)<60)].mean():+.1f}')
# simultaneous kick+hh: correlation of offsets (shared component)
pairs=[]
idx=collections.defaultdict(dict)
for i,(fi,c,v,p,o,t_,b,kk,s) in enumerate(H):
    if c in('kick','hhC','snare') and abs(o)<60 and s not in('jazz','afrobeat','afrocuban','neworleans','latin','reggae','dance'): idx[(fi,kk)][c]=o
d1=[];d2=[]
for key,dd in idx.items():
    if 'kick' in dd and 'hhC' in dd: d1.append((dd['kick'],dd['hhC']))
    if 'snare' in dd and 'hhC' in dd: d2.append((dd['snare'],dd['hhC']))
d1=np.array(d1); d2=np.array(d2)
print(f'  kick-hh same step: corr {np.corrcoef(d1.T)[0,1]:.2f}, sd of difference {np.std(d1[:,0]-d1[:,1]):.1f} ms, mean diff {np.mean(d1[:,0]-d1[:,1]):+.1f}')
print(f'  snare-hh same step: corr {np.corrcoef(d2.T)[0,1]:.2f}, sd of difference {np.std(d2[:,0]-d2[:,1]):.1f} ms, mean diff {np.mean(d2[:,0]-d2[:,1]):+.1f}')
# lag-1 autocorrelation of hh velocity residual (after removing position means) within files
ac=[]
for fid in np.unique(f[C=='hhC']):
    m=(C=='hhC')&(f==fid)
    if m.sum()<30: continue
    o=np.argsort(tt[m]); v=vel[m][o]; p=pos[m][o]
    res=v.copy().astype(float)
    for pp in np.unique(p): res[p==pp]-=v[p==pp].mean()
    ac.append(np.corrcoef(res[:-1],res[1:])[0,1])
print(f'\n== hh velocity residual lag-1 autocorr (after removing grid-position means): median {np.nanmedian(ac):.2f} (files {len(ac)})')
# residual sd after removing position means
rs=[]
for fid in np.unique(f[C=='hhC']):
    m=(C=='hhC')&(f==fid)
    if m.sum()<30: continue
    v=vel[m]; p=pos[m]; res=v.astype(float).copy()
    for pp in np.unique(p): res[p==pp]-=v[p==pp].mean()
    rs.append(res.std())
print(f'   hh residual velocity sd (after position pattern) median {np.median(rs):.1f}')

print('\n===== refined: rock/pop only, local-detrended timing =====')
sel=np.isin(ST,['rock','pop'])
from collections import defaultdict
res=defaultdict(list); diffs=defaultdict(list); vres=defaultdict(list); ac2=defaultdict(list)
for fid in np.unique(f[sel]):
    m=sel&(f==fid)&(np.abs(off)<60)
    ks=k[m]; os_=off[m]; cs=C[m]
    # local shared timing: median offset of all hits within +-4 16th steps (2 beats) around each step
    steps=np.unique(ks)
    loc={s:np.median(os_[np.abs(ks-s)<=4]) for s in steps}
    lo=np.array([loc[s] for s in ks]); r_=os_-lo
    for c in ['kick','snare','hhC','ride']:
        mm=cs==c
        if mm.sum()>10: res[c].append(r_[mm])
    byk=defaultdict(dict)
    for s_,c_,o_ in zip(ks,cs,os_): byk[s_][c_]=o_
    for s_,dd in byk.items():
        if 'kick' in dd and 'hhC' in dd: diffs['kick-hh'].append(dd['kick']-dd['hhC'])
        if 'snare' in dd and 'hhC' in dd: diffs['snare-hh'].append(dd['snare']-dd['hhC'])
        if 'kick' in dd and 'snare' in dd: diffs['kick-snare'].append(dd['kick']-dd['snare'])
    # velocity residual after per-position mean, for kick, snare backbeat, hh
    mv=sel&(f==fid)
    for c,pp in [('hhC',None),('kick',None),('snareBB',[4,12])]:
        cc='snare' if c=='snareBB' else c
        mm=mv&(C==cc)&(np.isin(pos,pp) if pp else True)
        if mm.sum()<16: continue
        o=np.argsort(tt[mm]); v=vel[mm][o].astype(float); p=pos[mm][o]
        for q in np.unique(p): v[p==q]-=v[p==q].mean()
        vres[c].append(v.std()); 
        if len(v)>20: ac2[c].append(np.corrcoef(v[:-1],v[1:])[0,1])
for c,v in res.items():
    v=np.concatenate(v); print(f'  {c:6s} local timing residual sd {v.std():.1f} ms  (IQR {np.percentile(v,25):+.1f}..{np.percentile(v,75):+.1f})')
for c,v in diffs.items():
    v=np.array(v); print(f'  {c:10s} same-step offset difference: mean {v.mean():+.1f} ms, sd {v.std():.1f}, median |diff| {np.median(np.abs(v)):.1f} ms')
for c in vres: print(f'  {c:8s} velocity residual sd median {np.median(vres[c]):.1f}, lag-1 autocorr median {np.nanmedian(ac2[c]):.2f}')
