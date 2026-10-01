# Rewrite groove_dyn.musicxml in standard two-voice drum notation:
# voice 1 = hands (stems up), voice 2 = kick (stems down), no <beam> (the app auto-beams), final barline.
import re
src = open('groove_dyn.musicxml').read()
head, body = src.split('<part id="P1">', 1)
body = body.rsplit('</part>', 1)[0]
TYPES = {1: ('16th', 0), 2: ('eighth', 0), 3: ('eighth', 1), 4: ('quarter', 0), 6: ('quarter', 1), 8: ('half', 0), 12: ('half', 1), 16: ('whole', 0)}
def rest(d):
    t, dot = TYPES[d]
    disp = {2: ('E', 4), 8: ('E', 4), 3: ('E', 4), 1: ('E', 4)}.get(d)   # kick-voice rests sit low, clear of the snare line
    r = f'<rest><display-step>{disp[0]}</display-step><display-octave>{disp[1]}</display-octave></rest>' if disp else '<rest/>'
    return f'<note>{r}<duration>{d}</duration><voice>2</voice><type>{t}</type>{"<dot/>" * dot}</note>'
def gap_rests(a, b):
    out = []
    while a < b:
        if a % 8 == 0 and b - a >= 8: d = 8
        elif a % 4 == 0 and b - a >= 4: d = 4
        else: d = min(b, (a // 4 + 1) * 4) - a
        if d == 3 and a % 4 != 0: out.append(rest(1)); a += 1; continue
        out.append(rest(d)); a += d
    return out
out_measures = []
measures = re.findall(r'(<measure number="(\d+)"[^>]*>)(.*?)</measure>', body, re.S)
for open_tag, num, m in measures:
    els = re.findall(r'<attributes>.*?</attributes>|<direction[ >].*?</direction>|<sound[^>]*/>|<note>.*?</note>|<barline.*?</barline>', m, re.S)
    pre, v1, kicks, pos, pending = [], [], [], 0, []
    groups = []   # (onset, dur, [notes])
    for e in els:
        if e.startswith('<attributes'): pre.append(e); continue
        if not e.startswith('<note>'): pending.append(e); continue
        if '<chord/>' in e: groups[-1][2].append(e); continue
        d = int(re.search(r'<duration>(\d+)', e).group(1))
        groups.append([pos, d, [e], pending]); pending = []; pos += d
    total = pos
    for onset, d, notes, dirs in groups:
        hands = [n for n in notes if 'P1-I36' not in n]
        kick = [n for n in notes if 'P1-I36' in n]
        assert hands, (num, onset)
        v1 += dirs
        for i, n in enumerate(hands):
            n = n.replace('<chord/>', '')
            if i: n = n.replace('<note>', '<note><chord/>', 1)
            v1.append(n)
        if kick: kicks.append((onset, d, kick[0]))
    v2, at = [], 0
    for k, (onset, d, n) in enumerate(kicks):
        nxt = kicks[k + 1][0] if k + 1 < len(kicks) else total
        v2 += gap_rests(at, onset)
        kd = d if d >= 4 else min(nxt, (onset // 4 + 1) * 4) - onset
        t, dot = TYPES[kd]
        n = n.replace('<chord/>', '')
        n = re.sub(r'<duration>\d+</duration>', f'<duration>{kd}</duration>', n)
        n = re.sub(r'<voice>\d+</voice>', '<voice>2</voice>', n)
        n = re.sub(r'<type>\w+</type>', f'<type>{t}</type>' + '<dot/>' * dot, n)
        n = re.sub(r'<stem>\w+</stem>', '', n)
        if t != 'whole': n = n.replace(f'<type>{t}</type>' + '<dot/>' * dot, f'<type>{t}</type>' + '<dot/>' * dot + '<stem>down</stem>')
        v2.append(n); at = onset + kd
    v2 += gap_rests(at, total)
    bar = '<barline location="right"><bar-style>light-heavy</bar-style></barline>' if num == measures[-1][1] else ''
    out_measures.append(open_tag + ''.join(pre) + ''.join(v1) + f'<backup><duration>{total}</duration></backup>' + ''.join(v2) + bar + '</measure>')
res = head + '<part id="P1">' + ''.join(out_measures) + '</part></score-partwise>'
res = res.replace('<accent/>', '<accent placement="above"/>')
open('groove_dyn2.musicxml', 'w').write(res)
# summary
for open_tag, num, m in re.findall(r'(<measure number="(\d+)"[^>]*>)(.*?)</measure>', res, re.S)[:5]:
    v2 = m.split('<backup>')[1]
    print(num, ' '.join(('R' if '<rest/>' in n else 'K') + re.search(r'<type>(\w+)', n).group(1)[:2] + ('.' if '<dot/>' in n else '') for n in re.findall(r'<note>.*?</note>', v2)))
