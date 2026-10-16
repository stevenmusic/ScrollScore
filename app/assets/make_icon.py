"""App 圖示:python3 make_icon.py logo-original.png icon-1024.png

使用者畫的 logo(logo-original.png,1254x1254)本身已經是圓角方塊、外面是白底。iOS 會自己把圖示裁成圓角
(圓角比原圖小),所以原圖直接用的話四個角會露出白邊。這裡把它做成 App Store 規格:
- 四個角(圓角方塊外面)補成同一列的背景色(原圖由上到下的深灰漸層,每一列取背景區的中位數)
- 五線譜那幾列的白線延伸到邊緣,不能整段塗掉,只修最外圈 4px 的亮邊
- 以圓角方塊為中心裁成正方形、縮成 1024x1024 RGB(不透明;App Store 不接受透明通道)
圖案本身完全不動。"""
from PIL import Image
import numpy as np, sys

src, dst = sys.argv[1], sys.argv[2]
im = np.asarray(Image.open(src).convert('RGB')).astype(float)
H, W, _ = im.shape
lum = im.sum(2)
dark = lum < 200
ys, xs = np.nonzero(dark)
x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max()       # 圓角方塊的範圍(原圖 43..1210 × 31..1215)

# 每一列的背景色:避開中間的播放軸,取暗的像素的中位數
cols = np.r_[int(W * 0.1):int(W * 0.45), int(W * 0.54):int(W * 0.9)]
bg = np.zeros((H, 3)); last = None
rows_ok = [y for y in range(H) if (im[y, cols].sum(1) < 180).sum() > 50]
for y in range(H):
    px = im[y, cols]; d = px[px.sum(1) < 180]
    if len(d) > 50: last = np.median(d, 0)
    if last is not None: bg[y] = last
bg[:rows_ok[0]] = bg[rows_ok[0]]; bg[rows_ok[-1]:] = bg[rows_ok[-1]]

# 五線譜的列(白線橫跨大部分寬度)
staff = [y for y in range(y0 + 60, y1 - 60) if (lum[y, int(W * 0.05):int(W * 0.95)] > 450).mean() > 0.5]
s0, s1 = min(staff) - 12, max(staff) + 12

out = im.copy(); RIM = 4
for y in range(H):
    if s0 <= y <= s1:                                    # 五線譜區:只修最外圈
        out[y, :x0 + RIM] = bg[y]; out[y, x1 - RIM + 1:] = bg[y]; continue
    d = np.nonzero(dark[y])[0]
    if len(d) == 0 or y < y0 + RIM or y > y1 - RIM: out[y, :] = bg[y]; continue
    out[y, :d.min() + RIM] = bg[y]; out[y, d.max() - RIM + 1:] = bg[y]

s = x1 - x0 + 1; top = int(round((y0 + y1) / 2 - s / 2))
img = Image.fromarray(out.clip(0, 255).astype(np.uint8)).crop((x0, top, x0 + s, top + s)).resize((1024, 1024), Image.LANCZOS)
img.save(dst)
a = np.asarray(img).astype(int)
corners = np.concatenate([a[:240, :240], a[:240, -240:], a[-240:, :240], a[-240:, -240:]]).reshape(-1, 3)
print(f'{dst}: {img.size} {img.mode}, staff rows {min(staff)}-{max(staff)}, brightest corner pixel {corners.sum(1).max()} (white = 765)')
