import subprocess, numpy as np
FF='/usr/local/lib/python3.11/dist-packages/imageio_ffmpeg/binaries/ffmpeg-linux-x86_64-v7.0.2'
SR=48000
def load(f):
    raw=subprocess.run([FF,'-v','error','-i',f,'-ac','1','-ar',str(SR),'-f','f32le','-'],capture_output=True).stdout
    return np.frombuffer(raw,np.float32)
def db(x): return 20*np.log10(x+1e-12)
def frames_rms(x,win=2400):
    n=len(x)//win; return np.sqrt(np.mean(x[:n*win].reshape(n,win)**2,axis=1))
def analyze(f, midi):
    x=load(f); on=np.argmax(np.abs(x)>0.05*np.abs(x).max()); x=x[on:]
    r=frames_rms(x); pk=r.max()
    # noise floor: quietest 50ms frame in the last 30% of the file, relative to peak
    tail=r[int(len(r)*0.7):]; nf=db(np.percentile(tail,10)/pk) if len(tail) else 0
    # decay: time to fall 30 dB below peak
    below=np.where(db(r/pk)<-30)[0]; below=below[below>np.argmax(r)]
    t30=(below[0]*2400/SR) if len(below) else len(x)/SR
    # spectrum of first 0.25 s
    s=x[:int(SR*0.25)]*np.hanning(int(SR*0.25)); S=np.abs(np.fft.rfft(s))**2; fr=np.fft.rfftfreq(len(s),1/SR)
    cen=(S*fr).sum()/S.sum()
    hf=10*np.log10(S[(fr>2000)&(fr<8000)].sum()/S.sum())
    # pitch: harmonic product spectrum on 0.3-1.3s
    seg=x[int(SR*0.3):int(SR*1.3)]; seg=seg*np.hanning(len(seg)); P=np.abs(np.fft.rfft(seg,len(seg)*4)); pf=np.fft.rfftfreq(len(seg)*4,1/SR)
    f0=440*2**((midi-69)/12); band=(pf>f0*0.94)&(pf<f0*1.06)
    fe=pf[band][np.argmax(P[band])]; cents=1200*np.log2(fe/f0)
    return dict(len=len(x)/SR, noise=nf, t30=t30, cen=cen, hf=hf, cents=cents, peak=db(pk))
E='x/BJAM 5.25.06/Ella G5/'; FS='FSS-SteelStringGuitar-SFZ-20200521/samples/'
sets={
 'current':[('cur/E2.mp3',40,'E2'),('cur/B3.mp3',59,'B3'),('cur/E4.mp3',64,'E4')],
 'Ella mf':[(E+'6E-mf00.ogg',40,'E2'),(E+'2B-mf00.ogg',59,'B3'),(E+'2B-mf05.ogg',64,'E4')],
 'Martin':[('martin/MartinGM2_040__E2_1.wav',40,'E2'),('martin/MartinGM2_058_Bb3_1.wav',58,'Bb3'),('martin/MartinGM2_064__E4_1.wav',64,'E4')],
 'FSS HV':[(FS+'HV_40.wav',40,'E2'),(FS+'HV_59.wav',59,'B3'),(FS+'HV_64.wav',64,'E4')],
}
print(f"{'lib':9s} {'note':4s} {'len':>5s} {'noise':>6s} {'t-30dB':>6s} {'centroid':>8s} {'2-8k':>6s} {'tune':>6s}")
for k,v in sets.items():
    for f,m,n in v:
        a=analyze(f,m); print(f"{k:9s} {n:4s} {a['len']:5.1f} {a['noise']:6.1f} {a['t30']:6.2f} {a['cen']:8.0f} {a['hf']:6.1f} {a['cents']:+6.1f}")
print('\nvelocity layers -> timbre (centroid Hz / 2-8k dB / peak dB)')
for lab,fs in [('Ella E2',[E+f'6E-{d}00.ogg' for d in ('mp','mf','f','ff')]),('Ella B3',[E+f'2B-{d}00.ogg' for d in ('mp','mf','f','ff')]),('Ella E4',[E+f'2B-{d}05.ogg' for d in ('mp','mf','f','ff')]),('FSS E2',[FS+'MV_40.wav',FS+'HV_40.wav']),('FSS A2',[FS+'MV_45.wav',FS+'HV_45.wav'])]:
    print(lab, ' | '.join(f"{a['cen']:.0f}/{a['hf']:.1f}/{a['peak']:.1f}" for a in [analyze(f,40) for f in fs]))
