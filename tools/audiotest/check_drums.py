"""鼓譜記譜檢查(Weinberg / PAS 鼓組記譜):python3 check_drums.py 檔案...
檢查:每個聲部每小節總長正確、音符/休止符不跨拍(四分以上必須從拍頭開始且不跨過第 3 拍的中線)、
手聲部符桿朝上/腳聲部朝下、腳的鼓件(大鼓、踩 hi-hat)不在手聲部、符尾不跨拍、三連音成組"""
import sys, re
POS = {('F', 4): 'kick', ('D', 4): 'pedalhh'}
for f in sys.argv[1:]:
    s = open(f).read(); errs = []
    div = int(re.search(r'<divisions>(\d+)', s).group(1)); beat = div; bar = 4 * div
    for mi, m in enumerate(re.findall(r'<measure.*?</measure>', s, re.S), 1):
        for vi, part in enumerate(m.split('<backup>')):
            pos = 0; beam_open = None
            for n in re.findall(r'<note>(.*?)</note>', part, re.S):
                if '<chord/>' in n: continue
                d = int(re.search(r'<duration>(\d+)', n).group(1))
                start, end = pos, pos + d
                if d < beat and start // beat != (end - 1) // beat: errs.append(f'm{mi} v{vi+1} @{start/div:.2f} 跨拍')
                if d == 2 * beat and start % (2 * beat): errs.append(f'm{mi} v{vi+1} 二分音符/休止沒對齊半小節')
                if beat < d < 2 * beat or (d >= beat and start % beat): errs.append(f'm{mi} v{vi+1} @{start/div:.2f} 長度 {d/div} 跨拍')
                if '<rest' not in n:
                    stem = re.search(r'<stem>(\w+)', n)
                    want = 'up' if vi == 0 else 'down'
                    if not stem or stem.group(1) != want: errs.append(f'm{mi} v{vi+1} 符桿方向錯')
                    st = re.search(r'<display-step>(\w)</display-step><display-octave>(\d)', n)
                    if vi == 0 and (st.group(1), int(st.group(2))) in POS: errs.append(f'm{mi} 腳的鼓件寫在手聲部')
                b = re.search(r'<beam number="1">([\w ]+)', n)
                if b:
                    if b.group(1) == 'begin': beam_open = start // beat
                    elif beam_open is not None and start // beat != beam_open: errs.append(f'm{mi} v{vi+1} 符尾跨拍')
                pos = end
            if pos != bar: errs.append(f'm{mi} v{vi+1} 小節長度 {pos/div} 拍')
    print(f.split('/')[-1], 'OK' if not errs else f'{len(errs)} 個問題: ' + '; '.join(errs[:8]))
