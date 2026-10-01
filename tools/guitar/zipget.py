import struct, sys, json, zlib, urllib.request, os
URL, idx, pat, outdir = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
files = json.load(open(idx))['files']
def rng(a, b):
    req = urllib.request.Request(URL, headers={'Range': f'bytes={a}-{b}'})
    for t in range(4):
        try:
            with urllib.request.urlopen(req, timeout=300) as r: return r.read()
        except Exception as e: err = e
    raise err
import re
rx = re.compile(pat)
n = 0
for name, meth, csize, usize, loff in files:
    if not rx.search(name) or name.endswith('/'): continue
    h = rng(loff, loff + 29)
    nl, el = struct.unpack('<HH', h[26:30])
    data = rng(loff + 30 + nl + el, loff + 30 + nl + el + csize - 1) if csize else b''
    if meth == 8: data = zlib.decompress(data, -15)
    p = os.path.join(outdir, name); os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, 'wb').write(data); n += 1
print('extracted', n)
