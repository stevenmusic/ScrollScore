"""MIDI 演奏 → midi_render.mjs 用的 JSON:python3 mid2json.py in.midi out.json [起始秒 長度秒]
notes: t 起音秒、d 時值、m 音高、v 力度、ped 起音時踩著延音踏板、damp 制音器落下的秒數(放鍵時還踩著就到踏板放開);pedals: [[踩下, 放開]](CC64 ≥ 64)"""
import sys, json, mido
src, out = sys.argv[1], sys.argv[2]
t0 = float(sys.argv[3]) if len(sys.argv) > 3 else 0; dur = float(sys.argv[4]) if len(sys.argv) > 4 else 1e9
t = 0; on = {}; notes = []; ped = []; pdown = None
for msg in mido.MidiFile(src):
    t += msg.time
    if msg.type == 'note_on' and msg.velocity > 0: on[msg.note] = (t, msg.velocity)
    elif msg.type in ('note_off', 'note_on') and msg.note in on:
        a, v = on.pop(msg.note); notes.append([a, t, msg.note, v])
    elif msg.type == 'control_change' and msg.control == 64:
        if msg.value >= 64 and pdown is None: pdown = t
        elif msg.value < 64 and pdown is not None: ped.append([pdown, t]); pdown = None
if pdown is not None: ped.append([pdown, t])
def pedal_at(x):
    for a, b in ped:
        if a <= x < b: return b
    return None
N = []
for a, b, m, v in notes:
    if a < t0 or a >= t0 + dur: continue
    e = pedal_at(a); off = pedal_at(b); damp = max(b, off) if off else b
    N.append(dict(t=a - t0, d=b - a, m=m, v=v, ped=e is not None, damp=min(damp, t0 + dur + 3) - t0))
P = [[max(0, a - t0), min(b, t0 + dur + 3) - t0] for a, b in ped if b > t0 and a < t0 + dur]
sec = max(n['damp'] for n in N) + 1
json.dump(dict(sec=sec, notes=N, pedals=P), open(out, 'w'))
print(f'{len(N)} notes, {len(P)} pedals, {sec:.1f}s')
