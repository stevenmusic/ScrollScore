import struct, sys, urllib.request, json, os
URL = sys.argv[1]
def rng(a, b):
    req = urllib.request.Request(URL, headers={'Range': f'bytes={a}-{b}'})
    with urllib.request.urlopen(req, timeout=120) as r: return r.read()
# size
req = urllib.request.Request(URL, method='HEAD')
with urllib.request.urlopen(req, timeout=60) as r: size = int(r.headers['Content-Length'])
tail = rng(size - 65536, size - 1)
i = tail.rfind(b'PK\x05\x06')
cd_size, cd_off = struct.unpack('<II', tail[i+12:i+20])
if cd_off == 0xFFFFFFFF or cd_size == 0xFFFFFFFF:
    j = tail.rfind(b'PK\x06\x06')
    cd_size, cd_off = struct.unpack('<QQ', tail[j+40:j+56])
cd = rng(cd_off, cd_off + cd_size - 1)
out = []; p = 0
while p < len(cd) and cd[p:p+4] == b'PK\x01\x02':
    meth, = struct.unpack('<H', cd[p+10:p+12])
    csize, usize = struct.unpack('<II', cd[p+20:p+28])
    nlen, elen, clen = struct.unpack('<HHH', cd[p+28:p+34])
    loff, = struct.unpack('<I', cd[p+42:p+46])
    name = cd[p+46:p+46+nlen].decode('utf-8', 'replace')
    extra = cd[p+46+nlen:p+46+nlen+elen]
    # zip64 extra
    q = 0
    while q < len(extra):
        hid, hl = struct.unpack('<HH', extra[q:q+4])
        if hid == 1:
            vals = extra[q+4:q+4+hl]; k = 0
            if usize == 0xFFFFFFFF: usize, = struct.unpack('<Q', vals[k:k+8]); k += 8
            if csize == 0xFFFFFFFF: csize, = struct.unpack('<Q', vals[k:k+8]); k += 8
            if loff == 0xFFFFFFFF: loff, = struct.unpack('<Q', vals[k:k+8]); k += 8
        q += 4 + hl
    out.append([name, meth, csize, usize, loff])
    p += 46 + nlen + elen + clen
json.dump({'size': size, 'files': out}, open(sys.argv[2], 'w'))
print(size, len(out))
