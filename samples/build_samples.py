"""App 內建範例樂譜:python3 samples/build_samples.py
- ode-to-joy.musicxml:貝多芬《歡樂頌》(第九號交響曲終樂章主題,公版)的簡易鋼琴版,右手旋律 + 左手和弦,本專案自己編寫
- drums-rock.musicxml / drums-funk.musicxml:tools/audiotest/gen_drums.py 產生的搖滾、放克節奏(本專案自己寫的,照標準鼓譜記譜)
標題用 {{TITLE}},App 載入時換成目前語言的名稱。小星星仍內建在 index.html(SAMPLE_MUSICXML)。"""
import os, subprocess, sys, tempfile, re
HERE = os.path.dirname(os.path.abspath(__file__))

# ── 歡樂頌(C 大調、4/4、四分音符 = 100)───────────────────────────
DIV = 2   # 每四分音符 2(八分音符 = 1)
STEP = {'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11}
TYPES = {1: ('eighth', False), 2: ('quarter', False), 3: ('quarter', True), 4: ('half', False), 8: ('whole', False)}
# 旋律:(音名八度, 長度) 長度以八分音符為單位
A = [('E5', 2), ('E5', 2), ('F5', 2), ('G5', 2)], [('G5', 2), ('F5', 2), ('E5', 2), ('D5', 2)], [('C5', 2), ('C5', 2), ('D5', 2), ('E5', 2)]
END1 = [('E5', 3), ('D5', 1), ('D5', 4)]
END2 = [('D5', 3), ('C5', 1), ('C5', 4)]
B = [[('D5', 2), ('D5', 2), ('E5', 2), ('C5', 2)], [('D5', 2), ('E5', 1), ('F5', 1), ('E5', 2), ('C5', 2)],
     [('D5', 2), ('E5', 1), ('F5', 1), ('E5', 2), ('D5', 2)], [('C5', 2), ('D5', 2), ('G4', 4)]]
MEL = [*A, END1, *A, END2, *B, *A, END2]
# 左手:每小節的和弦(全音符或兩個二分音符)
C, G, G7, F = ['C3', 'E3', 'G3'], ['B2', 'D3', 'G3'], ['B2', 'F3', 'G3'], ['C3', 'F3', 'A3']
HAR = [[(C, 8)], [(G, 8)], [(C, 8)], [(G, 8)],
       [(C, 8)], [(G, 8)], [(C, 8)], [(G7, 4), (C, 4)],
       [(G, 8)], [(G7, 4), (C, 4)], [(G7, 4), (C, 4)], [(C, 4), (G, 4)],
       [(C, 8)], [(G, 8)], [(F, 4), (C, 4)], [(G7, 4), (C, 4)]]
DYN = {0: 'mf', 8: 'p', 12: 'f'}
WEDGE = {10: 'crescendo', 11: 'stop'}

def note(p, dur, voice, staff, chord=False, last=False):
    m = re.match(r'([A-G])(\d)', p); typ, dot = TYPES[dur]
    return (f'<note>{"<chord/>" if chord else ""}<pitch><step>{m.group(1)}</step><octave>{m.group(2)}</octave></pitch>'
            f'<duration>{dur * DIV // 2}</duration><voice>{voice}</voice><type>{typ}</type>{"<dot/>" if dot else ""}<staff>{staff}</staff></note>')

def ode():
    meas = []
    for i, (mel, har) in enumerate(zip(MEL, HAR)):
        x = f'<measure number="{i + 1}">'
        if i == 0:
            x += ('<attributes><divisions>2</divisions><key><fifths>0</fifths></key><time><beats>4</beats><beat-type>4</beat-type></time>'
                  '<staves>2</staves><clef number="1"><sign>G</sign><line>2</line></clef><clef number="2"><sign>F</sign><line>4</line></clef></attributes>'
                  '<direction placement="above"><direction-type><metronome><beat-unit>quarter</beat-unit><per-minute>100</per-minute></metronome></direction-type>'
                  '<staff>1</staff><sound tempo="100"/></direction>')
        if i in DYN:
            x += f'<direction placement="below"><direction-type><dynamics><{DYN[i]}/></dynamics></direction-type><staff>1</staff></direction>'
        if i in WEDGE:
            x += f'<direction placement="below"><direction-type><wedge type="{WEDGE[i]}"/></direction-type><staff>1</staff></direction>'
        for p, d in mel: x += note(p, d, 1, 1)
        x += '<backup><duration>8</duration></backup>'
        for chord, d in har:
            for k, p in enumerate(chord): x += note(p, d, 2, 2, chord=k > 0)
        if i == len(MEL) - 1: x += '<barline location="right"><bar-style>light-heavy</bar-style></barline>'
        meas.append(x + '</measure>')
    assert all(sum(d for _, d in m) == 8 for m in MEL) and all(sum(d for _, d in h) == 8 for h in HAR)
    return ('<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE score-partwise PUBLIC "-//Recordare//DTD MusicXML 4.0 Partwise//EN" '
            '"http://www.musicxml.org/dtds/partwise.dtd">\n<score-partwise version="4.0"><work><work-title>{{TITLE}}</work-title></work>'
            '<identification><creator type="composer">L. v. Beethoven</creator><rights>Arrangement: ScrollScore (public domain)</rights></identification>'
            '<part-list><score-part id="P1"><part-name>Piano</part-name></score-part></part-list><part id="P1">' + ''.join(meas) + '</part></score-partwise>\n')

open(os.path.join(HERE, 'ode-to-joy.musicxml'), 'w').write(ode())
with tempfile.TemporaryDirectory() as d:
    subprocess.run([sys.executable, os.path.join(HERE, '..', 'tools', 'audiotest', 'gen_drums.py'), d], check=True, capture_output=True)
    for src, dst in [('drums_rock', 'drums-rock'), ('drums_funk', 'drums-funk')]:
        x = open(os.path.join(d, src + '.musicxml')).read()
        x = re.sub(r'<work-title>[^<]*</work-title>', '<work-title>{{TITLE}}</work-title>', x)
        open(os.path.join(HERE, dst + '.musicxml'), 'w').write(x)
print('ok')
