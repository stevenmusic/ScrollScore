# Listening comparison: same arpeggio (E2 A2 D3 G3 B3 E4) then E4 at 4 dynamics (mp mf f ff), per library.
import subprocess, numpy as np, os
FF='/usr/local/lib/python3.11/dist-packages/imageio_ffmpeg/binaries/ffmpeg-linux-x86_64-v7.0.2'
SR=48000
def load(f, semis=0):
    flt = f'asetrate={SR}*{2**(semis/12):.6f},aresample={SR}' if semis else 'anull'
    raw = subprocess.run([FF,'-v','error','-i',f,'-af',flt,'-ac','2','-ar',str(SR),'-f','f32le','-'],capture_output=True).stdout
    return np.frombuffer(raw,np.float32).reshape(-1,2).copy()
E='x/BJAM 5.25.06/Ella G5/'
libs = {
 'current (tonejs, 1 layer)': dict(arp=[('cur/E2.mp3',0),('cur/A2.mp3',0),('cur/D3.mp3',0),('cur/G3.mp3',0),('cur/B3.mp3',0),('cur/E4.mp3',0)],
     dyn=[('cur/E4.mp3',0,g) for g in (0.35,0.55,0.8,1.0)]),
 'Ella Gitauru (Fender DG8S, 4 layers)': dict(arp=[(E+'6E-mf00.ogg',0),(E+'5A-mf00.ogg',0),(E+'4D-mf00.ogg',0),(E+'4D-mf05.ogg',0),(E+'2B-mf00.ogg',0),(E+'2B-mf05.ogg',0)],
     dyn=[(E+f'2B-{d}05.ogg',0,1.0) for d in ('mp','mf','f','ff')]),
 'Martin HD28 (1 layer)': dict(arp=[('martin/MartinGM2_040__E2_1.wav',0),('martin/MartinGM2_046_Bb2_1.wav',-1),('martin/MartinGM2_049_Db3_1.wav',1),('martin/MartinGM2_055__G3_1.wav',0),('martin/MartinGM2_058_Bb3_1.wav',1),('martin/MartinGM2_064__E4_1.wav',0)],
     dyn=[('martin/MartinGM2_064__E4_1.wav',0,g) for g in (0.35,0.55,0.8,1.0)]),
 'FreePats FSS Seagull (2 layers, partial)': dict(arp=[('FSS-SteelStringGuitar-SFZ-20200521/samples/HV_40.wav',0),('FSS-SteelStringGuitar-SFZ-20200521/samples/MV_45.wav',0),('FSS-SteelStringGuitar-SFZ-20200521/samples/MV_50.wav',0),('FSS-SteelStringGuitar-SFZ-20200521/samples/MV_55.wav',0),('FSS-SteelStringGuitar-SFZ-20200521/samples/HV_59.wav',0),('FSS-SteelStringGuitar-SFZ-20200521/samples/HV_64.wav',0)],
     dyn=[('FSS-SteelStringGuitar-SFZ-20200521/samples/HV_64.wav',0,g) for g in (0.35,0.55,0.8,1.0)]),
}
def lufs_gain(x, target=-20):
    # simple K-weight-free RMS approximation over the loud part
    r = np.sqrt(np.mean(x**2)+1e-12); return 10**((target - 20*np.log10(r) - 0.7)/20)
out=[]; marks=[]
t=0
for name, L in libs.items():
    seg = np.zeros((int(SR*9.5),2),np.float32)
    for i,(f,s) in enumerate(L['arp']):
        x=load(f,s)[:int(SR*4)]; x*=np.linspace(1,0,len(x))[:,None]**0.5
        o=int(SR*(0.35*i)); seg[o:o+len(x)]+=x[:len(seg)-o]
    for i,(f,s,g) in enumerate(L['dyn']):
        x=load(f,s)[:int(SR*1.4)]*g; x[-2400:]*=np.linspace(1,0,2400)[:,None]
        o=int(SR*(3.6+1.45*i)); seg[o:o+len(x)]+=x[:len(seg)-o]
    seg*=lufs_gain(seg); out.append(seg); out.append(np.zeros((int(SR*0.8),2),np.float32))
    marks.append((t,name)); t+=len(seg)/SR+0.8
y=np.concatenate(out); y/=max(1,np.abs(y).max()/0.89)
subprocess.run([FF,'-v','error','-y','-f','f32le','-ar',str(SR),'-ac','2','-i','-','-c:a','libmp3lame','-b:a','256k','guitar_compare.mp3'],input=y.astype(np.float32).tobytes())
for m,n in marks: print(f'{int(m//60)}:{m%60:04.1f}  {n}')
