"""App 自動演奏 vs 真人鋼琴家((n)ASAP 逐音對照,只拿來量數字、不放 repo)。
用法:python3 perf_compare.py(在放 pd/〔perf_dump.mjs 輸出〕與 async/〔match_xml.txt、match_mid.txt、nasap/*.match、nmid/*.mid〕的目錄執行)
每首:逐音力度相關、每個全音符平均力度相關(App vs 真人;真人 vs 其他真人平均 = 上限)、起伏大小、旋律比同時其他音大多少、局部速度相關與起伏、
踏板(每個音起音時有沒有踩:比例、跟真人一致程度、每個全音符踩幾次)"""
import re, json, glob, sys, os, numpy as np, mido
from collections import defaultdict
SN=re.compile(r"snote\(([^,]+),\[([A-G]),([^\]]*)\],(-?\d+),(-?\d+):([\d]+),([^,]+),([^,]+),([-\d.]+),([-\d.]+),\[([^\]]*)\]\)-(note\((.*)\)|deletion)\.")
STEP={"C":0,"D":2,"E":4,"F":5,"G":7,"A":9,"B":11}; ALT={"n":0,"#":1,"b":-1,"##":2,"bb":-2,"x":2}
TS=re.compile(r"scoreprop\(timeSignature,(\d+)/(\d+),[^,]+,[^,]+,([-\d.]+)\)")
def parse(f):
    txt=open(f).read()
    mu=int(re.search(r"midiClockUnits,(\d+)",txt).group(1)); mr=int(re.search(r"midiClockRate,(\d+)",txt).group(1)); k=mr/1e6/mu
    ts=sorted([(float(b),int(d)) for n,d,b in TS.findall(txt)])
    if not ts:
        m5=re.search(r"info\(timeSignature,\[(\d+)/(\d+)",txt); ts=[(0.0,int(m5.group(2)) if m5 else 4)]
    def whole(onb):
        W=0; prev=ts[0]
        for i,(b,d) in enumerate(ts):
            if i==0: continue
            if onb>=b: W+=(b-prev[0])/prev[1]; prev=(b,d)
        return W+(onb-prev[0])/prev[1]
    out=[]
    for m in SN.finditer(txt):
        if not m.group(13): continue
        rep=m.group(1).split("-"); 
        if len(rep)>1 and rep[1]!="1": continue
        p=m.group(13).split(",")
        if "[" in m.group(13): p=[p[0],None,p[4],p[5],p[7]]
        pitch=(int(m.group(4))+1)*12+STEP[m.group(2)]+ALT.get(m.group(3),0)
        out.append(dict(w=whole(float(m.group(9))),pitch=pitch,t=int(p[2])*k,off=int(p[3])*k,v=int(p[4]),staff=2 if 'staff2' in m.group(11) else 1))
    return out
def pedal(midf):
    t=0; dn=None; R=[]
    for msg in mido.MidiFile(midf):
        t+=msg.time
        if msg.type=='control_change' and msg.control==64:
            if msg.value>=64 and dn is None: dn=t
            elif msg.value<64 and dn is not None: R.append((dn,t)); dn=None
    return R
mx=dict(l.rstrip('\n').split('\t') for l in open('async/match_xml.txt'))
mm=dict(l.rstrip('\n').split('\t') for l in open('async/match_mid.txt'))
def corr(a,b):
    a=np.asarray(a,float); b=np.asarray(b,float)
    if len(a)<5 or a.std()==0 or b.std()==0: return np.nan
    return float(np.corrcoef(a,b)[0,1])
R=defaultdict(list)
for js in sorted(glob.glob((sys.argv[1] if len(sys.argv)>1 else 'pd')+'/*.json')):
    name=js.split('nxml_')[1].replace('.json','')
    app=json.load(open(js))
    perfs=[f for f,x in mx.items() if x.endswith(name)]
    akey={(round(n[0],3),n[1]):n for n in app['notes']}
    # 每個演奏對到 App 的音
    P=[]
    for f in perfs:
        ns=parse('async/'+f); hits=[]
        from collections import Counter
        byp=defaultdict(list)
        for a in app['notes']: byp[a[1]].append(a[0])
        cnt=Counter()
        for n in sorted(ns,key=lambda n:n['w'])[:300]:
            for aw in byp.get(n['pitch'],[]):
                d=round(aw-n['w'],3)
                if abs(d)<8: cnt[d]+=1
        sh=cnt.most_common(1)[0][0] if cnt else 0
        for shift in (sh,):
            for n in ns:
                a=akey.get((round(n['w']+shift,3),n['pitch']))
                if a: hits.append((a,n))
        cov=len(hits)/max(1,len(app['notes']))
        if cov<0.6: continue
        P.append((f,hits,ns))
    if len(P)<2: print(name,'對不上',len(perfs)); continue
    # 以 App 音為主鍵,收集每位演奏者的力度與時間
    keys=sorted(set(k for _,h,_ in P for k in [(round(a[0],3),a[1]) for a,_ in h]))
    idx={k:i for i,k in enumerate(keys)}; N=len(keys); M=len(P)
    V=np.full((M,N),np.nan); T=np.full((M,N),np.nan); appv=np.zeros(N); apps=np.zeros(N); appmel=np.zeros(N); W=np.zeros(N); PIT=np.zeros(N)
    secmap={}
    for s in app['sec']: secmap.setdefault(round(s[0],3),s[2])
    for j,(f,h,ns) in enumerate(P):
        for a,n in h:
            i=idx[(round(a[0],3),a[1])]; V[j,i]=n['v']; T[j,i]=n['t']; appv[i]=a[2]; appmel[i]=a[3]; W[i]=a[0]; PIT[i]=a[1]; apps[i]=secmap.get(round(a[0],3),np.nan)
    # 1 逐音力度相關:App vs 每位演奏者;演奏者 vs 其他人平均
    ca=[]; ch=[]
    for j in range(M):
        ok=~np.isnan(V[j]); others=np.nanmean(np.delete(V,j,0),0)
        ca.append(corr(appv[ok],V[j][ok])); ok2=ok&~np.isnan(others); ch.append(corr(others[ok2],V[j][ok2]))
    R['vel_note_app'].append(np.nanmean(ca)); R['vel_note_human'].append(np.nanmean(ch))
    # 2 段落力度(每 1 個全音符窗的平均)
    bins=np.floor(W/1.0).astype(int); ub=np.unique(bins)
    def binmean(x): return np.array([np.nanmean(x[bins==b]) if np.any(~np.isnan(x[bins==b])) else np.nan for b in ub])
    cons=np.nanmean(V,0)
    ba=binmean(appv); bc=binmean(cons)
    cpa=[];cph=[]
    for j in range(M):
        bj=binmean(V[j]); others=binmean(np.nanmean(np.delete(V,j,0),0)); ok=~np.isnan(bj)&~np.isnan(others)
        cpa.append(corr(ba[ok],bj[ok])); cph.append(corr(others[ok],bj[ok]))
    R['vel_bar_app'].append(np.nanmean(cpa)); R['vel_bar_human'].append(np.nanmean(cph))
    # 3 起伏大小:逐音標準差、每小節平均的標準差
    R['vel_sd_app'].append(np.nanstd(appv)); R['vel_sd_human'].append(np.nanmean([np.nanstd(V[j]) for j in range(M)]))
    R['bar_sd_app'].append(np.nanstd(ba)); R['bar_sd_human'].append(np.nanmean([np.nanstd(binmean(V[j])) for j in range(M)]))
    # 4 旋律比同時其他音大多少
    on=defaultdict(list)
    for i in range(N): on[W[i]].append(i)
    da=[];dh=[]
    for w,ii in on.items():
        if len(ii)<2: continue
        top=max(ii,key=lambda i:PIT[i]); rest=[i for i in ii if i!=top]
        da.append(appv[top]-np.mean(appv[rest]))
        dh.append(np.nanmean(V[:,top])-np.nanmean(V[:,rest]))
    R['mel_app'].append(np.nanmean(da)); R['mel_human'].append(np.nanmean(dh))
    # 5 速度:每個全音符窗的局部速度(秒/全音符),log 去中位數
    def tempo(times):
        out=[]
        for b in ub:
            sel=(bins==b)&~np.isnan(times)
            if sel.sum()<3 or np.ptp(W[sel])<0.2: out.append(np.nan); continue
            s=np.polyfit(W[sel],times[sel],1)[0]; out.append(np.log(s) if s>0 else np.nan)
        o=np.array(out); return o-np.nanmedian(o)
    ta=tempo(apps); tc=[tempo(T[j]) for j in range(M)]
    cta=[];cth=[]
    for j in range(M):
        others=np.nanmean(np.delete(np.array(tc),j,0),0); ok=~np.isnan(tc[j])&~np.isnan(others)&~np.isnan(ta)
        cta.append(corr(ta[ok],tc[j][ok])); cth.append(corr(others[ok],tc[j][ok]))
    R['tempo_app'].append(np.nanmean(cta)); R['tempo_human'].append(np.nanmean(cth))
    R['tempo_sd_app'].append(np.nanstd(ta)); R['tempo_sd_human'].append(np.nanmean([np.nanstd(x) for x in tc]))
    # 6 踏板:把演奏時間換回樂譜位置,看每個音起音時踏板有沒有踩
    appped=app['ped']+app['auto']; src=('譜+自動' if app['auto'] else '譜') if app['ped'] else '自動'
    def down_at(w,ranges): return any(a-1e-6<=w<b-1e-6 for a,b in ranges)
    pa=np.array([down_at(W[i],appped) for i in range(N)],float)
    hp=[]; changes=[]
    for j,(f,h,ns) in enumerate(P):
        ped=pedal('async/'+mm[f]); tt=T[j]
        hp.append(np.array([any(a<=tt[i]+0.02<b for a,b in ped) if not np.isnan(tt[i]) else np.nan for i in range(N)],float))
        dur=np.nanmax(tt)-np.nanmin(tt); changes.append(len([1 for a,b in ped if a<np.nanmax(tt)])/ (np.ptp(W)+1e-9))
    hp=np.array(hp); hm=np.nanmean(hp,0)
    R['ped_frac_app'].append(pa.mean()); R['ped_frac_human'].append(np.nanmean(hp))
    agree_app=np.nanmean([np.nanmean((pa==hp[j]).astype(float)[~np.isnan(hp[j])]) for j in range(M)])
    agree_h=np.nanmean([np.nanmean(((np.nanmean(np.delete(hp,j,0),0)>=0.5)==hp[j]).astype(float)[~np.isnan(hp[j])]) for j in range(M)])
    R['ped_agree_app'].append(agree_app); R['ped_agree_human'].append(agree_h)
    R['ped_press_app'].append(len(appped)/(np.ptp(W)+1e-9)); R['ped_press_human'].append(np.mean(changes))
    print(f"{name[:34]:34s} 演奏{M:2d} 力度相關 App {np.nanmean(ca):.2f}/人 {np.nanmean(ch):.2f}  小節力度 {np.nanmean(cpa):.2f}/{np.nanmean(cph):.2f}  起伏sd {np.nanstd(appv):4.1f}/{R['vel_sd_human'][-1]:4.1f}  旋律+ {np.nanmean(da):4.1f}/{np.nanmean(dh):4.1f}  速度相關 {np.nanmean(cta):.2f}/{np.nanmean(cth):.2f} sd {R['tempo_sd_app'][-1]:.3f}/{R['tempo_sd_human'][-1]:.3f}  踏板({src}) 踩 {pa.mean():.2f}/{np.nanmean(hp):.2f} 一致 {agree_app:.2f}/{agree_h:.2f} 每全音符踩 {R['ped_press_app'][-1]:.2f}/{R['ped_press_human'][-1]:.2f}")
print()
for k in sorted(set(x.rsplit('_',1)[0] for x in R)):
    print(f"{k:12s} App {np.nanmean(R[k+'_app']):.3f}   真人 {np.nanmean(R[k+'_human']):.3f}")
