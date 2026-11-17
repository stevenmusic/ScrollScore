"""相鄰兩層力度錄音的起音時間差(換層漸層 PIANO_XFADE 用)。
用法:python3 piano/build/xlag.py(在 repo 根目錄),寫進 piano/manifest.json 的 xlag:
xlag[檔名音名(Ds1 等)][i] = 第 i+1 層對第 i+2 層的位移(取樣數,48kHz):第 i+1 層[t + k] ≈ 第 i+2 層[t]。
Accurate-Salamander 相鄰層對齊後相關 0.98~1.00,但有些層差約 1ms,直接疊會互相抵消(相關 −0.56)"""
import json, os, numpy as np, soundfile as sf
D = os.path.join(os.path.dirname(__file__), "..")
man = json.load(open(os.path.join(D, "manifest.json")))
def load(name):
    a, sr = sf.read(os.path.join(D, f"pf-{name}.flac")); return (a.mean(1) if a.ndim > 1 else a), sr
out = {}
NN = ["C","Cs","D","Ds","E","F","Fs","G","Gs","A","As","B"]   # 同 index.html PIANO_NOTE_NAMES(檔名用)
for midi in man["notes"].values():
    note = NN[midi % 12] + str(midi // 12 - 1)
    lags = []
    for l in range(1, len(man["velRanges"])):
        try: a, sr = load(f"{note}-v{l}"); b, _ = load(f"{note}-v{l+1}")
        except Exception: lags.append(0); continue
        n = int(0.08 * sr); A = a[:n] / (np.linalg.norm(a[:n]) or 1); B = b[:n] / (np.linalg.norm(b[:n]) or 1)
        c = np.correlate(np.pad(A, 400), B, "valid")   # c[j] = Σ A[i + j − 240]·B[i]
        k = int(np.argmax(c)) - 400
        lags.append(k if c.max() > 0.8 and abs(k) < 390 else 0)   # 搜尋邊界上的值不可信
    out[note] = lags
man["xlag"] = out
json.dump(man, open(os.path.join(D, "manifest.json"), "w"), ensure_ascii=False, indent=0)
print({k: v for k, v in list(out.items())[:3]})
