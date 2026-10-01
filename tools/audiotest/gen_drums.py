"""產生測試用鼓譜 MusicXML,照 MuseScore 4 預設鼓組(src/engraving/dom/drumset.cpp)與它的 MusicXML 匯出格式:
- 位置/符頭:大鼓 F4、小鼓 C5、邊擊 C5 slashed 符頭、閉合/開放 hi-hat G5 x 符頭(開放加 <technical><open/>,畫成上方的「o」)、
  踩 hi-hat D4 x、ride F5 x、ride bell F5 diamond、crash1 A5 x、crash2 B5 x、
  中鼓 48 E5 / 47 D5 / 45 B4、落地鼓 43 A4 / 41 G4
- 手一個聲部(voice 1,符桿朝上),腳一個聲部(voice 2,符桿朝下);兩個聲部各自寫滿整小節(休止符補齊)
- 記譜規則(Weinberg / PAS):音符與休止符都不跨拍;每拍內的音符延到下一個擊打或拍尾為止;
  空拍用對齊拍子的休止符(整拍 = 四分休止、第 1-2 或 3-4 拍都空 = 二分休止、整小節空 = 全休止);
  符尾以拍為單位(每拍一組),同一拍的和弦一起
- 搖擺(爵士)用八分音符三連音記,播放才會是真的搖擺,不用附點八分 + 十六分
- 鬼音 <notehead parentheses="yes">、重音 <accent/>
用法:python3 gen_drums.py <輸出目錄>;check_drums.py 檢查上面這些規則"""
import sys, os

PIECES = {   # GM 鼓號: (顯示音名, 八度, 符頭)
    36: ('F', 4, None), 38: ('C', 5, None), 37: ('C', 5, 'slashed'), 42: ('G', 5, 'x'), 46: ('G', 5, 'x'),
    44: ('D', 4, 'x'), 51: ('F', 5, 'x'), 53: ('F', 5, 'diamond'), 49: ('A', 5, 'x'), 57: ('B', 5, 'x'),
    48: ('E', 5, None), 47: ('D', 5, None), 45: ('B', 4, None), 43: ('A', 4, None), 41: ('G', 4, None),
}
NAMES = {36: 'Bass Drum', 38: 'Snare', 37: 'Side Stick', 42: 'Closed Hi-Hat', 46: 'Open Hi-Hat', 44: 'Pedal Hi-Hat', 51: 'Ride',
         53: 'Ride Bell', 49: 'Crash 1', 57: 'Crash 2', 48: 'Hi-Mid Tom', 47: 'Low-Mid Tom', 45: 'Low Tom', 43: 'High Floor Tom', 41: 'Low Floor Tom'}
FEET = {36, 44}
DIVISIONS = 12   # 每四分音符 12:十六分 = 3、三連音八分 = 4

def instruments():
    return ''.join(f'<score-instrument id="P1-I{k}"><instrument-name>{NAMES[k]}</instrument-name></score-instrument>' for k in PIECES) + \
           ''.join(f'<midi-instrument id="P1-I{k}"><midi-channel>10</midi-channel><midi-unpitched>{k + 1}</midi-unpitched></midi-instrument>' for k in PIECES)

def typ(sub, d):
    """一拍分成 sub 格(4 = 十六分、3 = 八分三連音),長 d 格 → (duration, type, 附點, 三連音)"""
    if sub == 4: return {1: (3, '16th', False, False), 2: (6, 'eighth', False, False), 3: (9, 'eighth', True, False), 4: (12, 'quarter', False, False)}[d]
    return {1: (4, 'eighth', False, True), 2: (8, 'quarter', False, True), 3: (12, 'quarter', False, False)}[d]

def element(voice, sub, d, notes=None, beam=None, tup=None):
    dur, ty, dot, trip = typ(sub, d)
    tm = '<time-modification><actual-notes>3</actual-notes><normal-notes>2</normal-notes></time-modification>' if trip else ''
    tupx = f'<tuplet type="{tup}" bracket="no"/>' if tup else ''
    if not notes:
        s = f'<note><rest/><duration>{dur}</duration><voice>{voice}</voice><type>{ty}</type>' + ('<dot/>' if dot else '') + tm
        return s + (f'<notations>{tupx}</notations>' if tupx else '') + '</note>'
    out = ''
    for j, (k, ghost, acc, opn) in enumerate(notes):
        st, oc, nh = PIECES[k]
        s = '<note>' + ('<chord/>' if j else '') + f'<unpitched><display-step>{st}</display-step><display-octave>{oc}</display-octave></unpitched>'
        s += f'<duration>{dur}</duration><instrument id="P1-I{k}"/><voice>{voice}</voice><type>{ty}</type>' + ('<dot/>' if dot else '') + tm
        s += f'<stem>{"down" if voice == 2 else "up"}</stem>'
        if nh or ghost:
            par = ' parentheses="yes"' if ghost else ''
            s += f'<notehead{par}>{nh or "normal"}</notehead>'
        if j == 0 and beam:
            for lvl, v in enumerate(beam, 1): s += f'<beam number="{lvl}">{v}</beam>'
        nots = (tupx if j == 0 else '') + ('<articulations><accent/></articulations>' if acc else '') + ('<technical><open/></technical>' if opn else '')
        if nots: s += f'<notations>{nots}</notations>'
        out += s + '</note>'
    return out

def rests(start, length, sub):
    """拍內休止符:十六分格裡對齊八分的 2 格 = 八分休止,其他用十六分;三連音逐格"""
    r, p = [], start
    while length > 0:
        if sub == 4 and length >= 2 and p % 2 == 0: r.append((p, 2, None)); p += 2; length -= 2
        else: r.append((p, 1, None)); p += 1; length -= 1
    return r

def beat_xml(hits, voice, sub):
    items, cur = [], 0
    pos = sorted(hits)
    for i, p in enumerate(pos):
        if p > cur: items += rests(cur, p - cur, sub)
        end = pos[i + 1] if i + 1 < len(pos) else sub
        d = end - p
        if sub == 4 and d == 3 and p != 0: d = 1      # 從 e 拍點寫附點八分少見,MuseScore 會寫十六分 + 八分休止
        if sub == 4 and d == 2 and p % 2: d = 1        # 從 e/a 拍點的八分音符會跨過 & 的位置
        items.append((p, d, hits[p])); cur = p + d
        if cur < end: items += rests(cur, end - cur, sub); cur = end
    if cur < sub: items += rests(cur, sub - cur, sub)
    # 符尾:同一拍裡兩個以上有符尾的音符才連,休止符在中間不斷開;十六分第二條符尾只連相鄰的十六分
    flagged = [i for i, (p, d, n) in enumerate(items) if n and typ(sub, d)[1] in ('eighth', '16th')]
    beams = {}
    if len(flagged) >= 2:
        for idx, i in enumerate(flagged):
            b = ['begin' if idx == 0 else 'end' if idx == len(flagged) - 1 else 'continue']
            if typ(sub, items[i][1])[1] == '16th':
                is16 = lambda q: 0 <= q < len(flagged) and typ(sub, items[flagged[q]][1])[1] == '16th' and abs(flagged[q] - i) == 1
                prv, nxt = is16(idx - 1), is16(idx + 1)
                b.append('continue' if prv and nxt else 'end' if prv else 'begin' if nxt else ('backward hook' if idx == len(flagged) - 1 else 'forward hook'))
            beams[i] = b
    trip = sub == 3 and not (len(items) == 1 and items[0][1] == 3)
    out = ''
    for i, (p, d, n) in enumerate(items):
        tup = ('start' if i == 0 else 'stop' if i == len(items) - 1 else None) if trip else None
        out += element(voice, sub, d, n, beams.get(i), tup)
    return out

def voice_xml(hits, voice, sub, beats=4):
    """hits: {(拍, 格): [...]}。整小節空 = 全休止;第 1-2、3-4 拍都空 = 二分休止;其他空拍 = 四分休止"""
    if not hits: return f'<note><rest measure="yes"/><duration>{beats * DIVISIONS}</duration><voice>{voice}</voice><type>whole</type></note>'
    out, b = '', 0
    while b < beats:
        bh = {g: v for (bb, g), v in hits.items() if bb == b}
        if not bh:
            if b % 2 == 0 and b + 1 < beats and not any(bb == b + 1 for (bb, g) in hits):
                out += f'<note><rest/><duration>{2 * DIVISIONS}</duration><voice>{voice}</voice><type>half</type></note>'; b += 2; continue
            out += f'<note><rest/><duration>{DIVISIONS}</duration><voice>{voice}</voice><type>quarter</type></note>'; b += 1; continue
        out += beat_xml(bh, voice, sub); b += 1
    return out

def measure(num, hits, sub, first, dyn, wedge, tempo, text):
    hands, feet = {}, {}
    for pos, v in hits.items():
        for h in v: (feet if h[0] in FEET else hands).setdefault(pos, []).append(h)
    s = f'<measure number="{num}">'
    if first:
        s += (f'<attributes><divisions>{DIVISIONS}</divisions><key><fifths>0</fifths></key><time><beats>4</beats><beat-type>4</beat-type></time>'
              '<clef><sign>percussion</sign><line>2</line></clef></attributes>')
    if tempo: s += f'<direction placement="above"><direction-type><metronome><beat-unit>quarter</beat-unit><per-minute>{tempo}</per-minute></metronome></direction-type><sound tempo="{tempo}"/></direction>'
    if text: s += f'<direction placement="above"><direction-type><words>{text}</words></direction-type></direction>'
    if dyn: s += f'<direction placement="below"><direction-type><dynamics><{dyn}/></dynamics></direction-type></direction>'
    if wedge: s += f'<direction placement="below"><direction-type><wedge type="{wedge}"/></direction-type></direction>'
    s += voice_xml(hands, 1, sub) + f'<backup><duration>{4 * DIVISIONS}</duration></backup>' + voice_xml(feet, 2, sub)
    return s + '</measure>'

def score(title, plan, tempo, sub=4, text=None):
    """plan: [(hits, 力度記號, 髮夾)...];hits = {小節內格位置: [...]},位置 p → (第 p//sub 拍, 第 p%sub 格)"""
    ms = []
    for i, (h, dyn, wedge) in enumerate(plan):
        hits = {}
        for p, v in h.items(): hits.setdefault((p // sub, p % sub), []).extend(v)
        ms.append(measure(i + 1, hits, sub, i == 0, dyn, wedge, tempo if i == 0 else None, text if i == 0 else None))
    ms[-1] = ms[-1].replace('</measure>', '<barline location="right"><bar-style>light-heavy</bar-style></barline></measure>')
    return ('<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE score-partwise PUBLIC "-//Recordare//DTD MusicXML 4.0 Partwise//EN" "http://www.musicxml.org/dtds/partwise.dtd">\n'
            f'<score-partwise version="4.0"><work><work-title>{title}</work-title></work><part-list><score-part id="P1"><part-name>Drumset</part-name>{instruments()}</score-part></part-list>'
            f'<part id="P1">{"".join(ms)}</part></score-partwise>')

# ── 節奏型(十六分格:一小節 0~15;爵士用三連音格 0~11)──
def hit(k, ghost=False, acc=False, opn=False): return (k, ghost, acc, opn)
def merge(*ds):
    out = {}
    for d in ds:
        for p, v in d.items(): out.setdefault(p, []).extend(v)
    return out
def at(k, *ps, **kw): return {p: [hit(k, **kw)] for p in ps}
def hat8(): return at(42, *range(0, 16, 2))
def ride8(): return at(51, *range(0, 16, 2))
def fill_toms():
    seq = [38, 38, 38, 38, 48, 48, 47, 47, 43, 43, 43, 43, 41, 41, 41, 41]
    return merge({p: [hit(k, acc=p in (0, 4, 8, 12))] for p, k in enumerate(seq)}, at(36, 0, 8))

def rock():
    verse = merge(hat8(), at(38, 4, 12), at(36, 0, 8, 10))
    pre = merge(hat8(), at(38, 4, 12), at(36, 0, 6, 8, 10))
    chorus = merge(ride8(), at(38, 4, 12, acc=True), at(36, 0, 6, 8, 10))
    chorus1 = merge(chorus, at(49, 0))
    end = merge(at(49, 0), at(57, 0), at(36, 0))
    P = [(verse, 'mp', None)] + [(verse, None, None)] * 6 + [(fill_toms(), None, None)] + [(pre, None, 'crescendo')] + [(pre, None, None)] * 2 + \
        [(fill_toms(), None, 'stop')] + [(chorus1, 'f', None)] + [(chorus, None, None)] * 6 + [(fill_toms(), None, None)] + \
        [(merge(verse, at(49, 0)), 'mp', None)] + [(verse, None, None)] * 6 + [(fill_toms(), None, None)] + [(chorus1, 'f', None)] + \
        [(chorus, None, None)] * 6 + [(fill_toms(), None, None), (end, None, None)]
    return score('Test Rock', P, 112)

def funk():
    g1 = merge(at(42, *range(16)), at(38, 4, 12, acc=True), at(38, 2, 7, 9, 14, ghost=True), at(36, 0, 3, 6, 10))
    # 開放 hi-hat:第 2 拍的 & 開,第 3 拍用踩 hi-hat 關(腳),手在開放後那個十六分不打
    g2 = merge(at(42, *[p for p in range(16) if p not in (6, 7)]), at(46, 6, opn=True), at(44, 8),
               at(38, 4, 12, acc=True), at(38, 2, 9, 11, 15, ghost=True), at(36, 0, 3, 8, 10, 13))
    fill = merge({p: [hit(38, ghost=(p % 2 == 1), acc=(p % 2 == 0))] for p in range(8)},
                 {p: [hit(k, acc=(p % 2 == 0))] for p, k in zip(range(8, 16), [48, 48, 47, 47, 43, 43, 41, 41])}, at(36, 0, 8))
    P = [(g1, 'mf', None)] + [(g2, None, None), (g1, None, None)] * 7 + [(fill, None, None), (merge(g1, at(49, 0)), None, None)] + \
        [(g2, None, None), (g1, None, None)] * 6 + [(fill, None, None), (merge(at(49, 0), at(36, 0)), None, None)]
    return score('Test Funk', P, 98)

def jazz():
    """三連音格(每拍 3 格):ride「叮 叮-嗒 叮 叮-嗒」= 第 1、3 拍四分音符,第 2、4 拍三連音的第 1、3 格;踩 hi-hat 在 2、4 拍"""
    ride = at(51, 0, 3, 5, 6, 9, 11)
    hh = at(44, 3, 9)
    c1 = merge(ride, hh, at(38, 11, ghost=True))
    c2 = merge(ride, hh, at(38, 5), at(38, 8, ghost=True), at(36, 11))   # 大鼓在第 4 拍搖擺的「c2 = merge(ride, hh, at(38, 5), at(38, 8, ghost=True), at(36, 10))」(三連音第 3 格)
    P = [(c1, 'p', None)] + [(c2, None, None), (c1, None, None)] * 7 + [(c2, None, None), (merge(at(49, 0), at(36, 0)), None, None)]
    return score('Test Jazz Swing', P, 160, sub=3, text='Swing')

def ballad():
    v = merge(hat8(), at(37, 4, 12), at(36, 0, 10))
    c = merge(hat8(), at(38, 4, 12), at(36, 0, 6, 8))
    P = [(v, 'pp', None)] + [(v, None, None)] * 7 + [(c, 'mp', 'crescendo')] + [(c, None, None)] * 2 + [(c, None, 'stop')] + \
        [(merge(c, at(49, 0)), 'f', None)] + [(c, None, None)] * 5 + [(c, None, 'diminuendo')] + [(c, None, None), (c, None, 'stop')] + \
        [(v, 'p', None)] + [(v, None, None)] * 5 + [(merge(at(49, 0), at(36, 0)), None, None)]
    return score('Test Ballad Dynamics', P, 72)

def metal():
    g = merge(at(49, 0), at(51, *range(2, 16, 2)), at(38, 4, 12, acc=True), at(36, *range(16)))
    g0 = merge(ride8(), at(38, 4, 12, acc=True), at(36, *range(16)))
    blast = merge(at(57, *range(0, 16, 2)), at(36, *range(0, 16, 2)), at(38, *range(1, 16, 2)))
    fill = merge({p: [hit(k, acc=p % 4 == 0)] for p, k in enumerate([38, 38, 38, 38, 48, 48, 48, 48, 47, 47, 47, 47, 43, 43, 41, 41])}, at(36, *range(16)))
    P = [(g, 'ff', None)] + [(g0, None, None)] * 6 + [(fill, None, None)] + [(merge(blast, at(49, 0)), None, None)] + [(blast, None, None)] * 6 + \
        [(fill, None, None)] + [(g, None, None)] + [(g0, None, None)] * 6 + [(fill, None, None), (merge(at(49, 0), at(57, 0), at(36, 0)), None, None)]
    return score('Test Metal', P, 180)

if __name__ == '__main__':
    out = sys.argv[1] if len(sys.argv) > 1 else '.'
    os.makedirs(out, exist_ok=True)
    for name, fn in [('drums_rock', rock), ('drums_funk', funk), ('drums_jazz', jazz), ('drums_ballad', ballad), ('drums_metal', metal)]:
        with open(os.path.join(out, name + '.musicxml'), 'w') as f: f.write(fn())
        print('wrote', name)
