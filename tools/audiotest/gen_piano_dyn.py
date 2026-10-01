"""鋼琴力度階梯測試譜:同一段(右手旋律 + 和弦、左手低音)依序用 pp p mp mf f ff 各彈 2 小節,
量每段響度就知道整條鏈路(取樣力度層 → 壓縮 → 限幅)最後留下多少大小聲差。用法:python3 gen_piano_dyn.py out.musicxml"""
import sys
DYNS = ['pp', 'p', 'mp', 'mf', 'f', 'ff']
def n(step, oct, dur, typ, chord=False, staff=1, voice=1, alter=0):
    a = f'<alter>{alter}</alter>' if alter else ''
    return (f'<note>{"<chord/>" if chord else ""}<pitch><step>{step}</step>{a}<octave>{oct}</octave></pitch>'
            f'<duration>{dur}</duration><voice>{voice}</voice><type>{typ}</type><staff>{staff}</staff></note>')
def rest(dur, typ, staff, voice): return f'<note><rest/><duration>{dur}</duration><voice>{voice}</voice><type>{typ}</type><staff>{staff}</staff></note>'
bars = []
num = 1
for d in DYNS:
    for k in range(2):
        m = f'<measure number="{num}">'
        if num == 1:
            m += ('<attributes><divisions>2</divisions><key><fifths>0</fifths></key><time><beats>4</beats><beat-type>4</beat-type></time>'
                  '<staves>2</staves><clef number="1"><sign>G</sign><line>2</line></clef><clef number="2"><sign>F</sign><line>4</line></clef></attributes>'
                  '<direction placement="above"><direction-type><metronome><beat-unit>quarter</beat-unit><per-minute>96</per-minute></metronome></direction-type><sound tempo="96"/></direction>')
        if k == 0: m += f'<direction placement="below"><direction-type><dynamics><{d}/></dynamics></direction-type><staff>1</staff></direction>'
        # 右手:四分音符旋律 + 和弦
        mel = [('E', 5), ('G', 5), ('C', 6), ('G', 5)] if k == 0 else [('F', 5), ('A', 5), ('D', 6), ('B', 5)]
        ch = [('C', 5), ('E', 5)] if k == 0 else [('D', 5), ('F', 5)]
        for st, oc in mel:
            m += n(st, oc, 2, 'quarter') + ''.join(n(cs, co, 2, 'quarter', True) for cs, co in ch)
        m += '<backup><duration>8</duration></backup>'
        lo = [('C', 3), ('G', 3)] if k == 0 else [('G', 2), ('D', 3)]
        for st, oc in lo:
            m += n(st, oc, 4, 'half', staff=2, voice=5) + n(st, oc + 1, 4, 'half', True, staff=2, voice=5)
        bars.append(m + '</measure>'); num += 1
bars.append(f'<measure number="{num}">' + rest(8, 'whole', 1, 1) + '<backup><duration>8</duration></backup>' + rest(8, 'whole', 2, 5) + '</measure>')
xml = ('<?xml version="1.0" encoding="UTF-8"?>\n<score-partwise version="3.1"><work><work-title>Piano dynamics ladder</work-title></work>'
       '<part-list><score-part id="P1"><part-name>Piano</part-name></score-part></part-list><part id="P1">' + ''.join(bars) + '</part></score-partwise>')
open(sys.argv[1] if len(sys.argv) > 1 else 'piano_dyn.musicxml', 'w').write(xml)
