#!/usr/bin/env python3
"""asset-02 v3b: band-limited curve adjustment (replaces v3's overreaching
below-curve reassignment) + v1-style hem-trim. Other steps same as v3."""
import numpy as np, json
from PIL import Image, ImageDraw
from scipy import ndimage as ndi

WORK = '/home/hatch/workspace/live2d-research/material-008/work/'
OUTD = '/home/hatch/workspace/live2d-research/material-008/reference/asset-02/'
img = np.array(Image.open(WORK + 'asset02.png').convert('RGB')).astype(int)
H, W, _ = img.shape
R, G, B = img[..., 0], img[..., 1], img[..., 2]
V = img.max(axis=2)
label = np.load(WORK + 'label2_v2.npy')
prev_label = label.copy()
names = {0: 'background', 1: 'hair-left', 2: 'hair-right', 3: 'skirt', 4: 'fixed'}
prev_counts = {names[k]: int((prev_label == k).sum()) for k in range(5)}
yy, xx = np.mgrid[0:H, 0:W]
edits = []

def poly_mask(poly):
    m = Image.new('L', (W, H), 0)
    ImageDraw.Draw(m).polygon(poly, fill=1)
    return np.array(m) > 0

# a) hair-left navy absorption cleanup
hl = label == 1
suspect = hl & (V <= 150)
body = hl & (V > 150)
keep = suspect & ndi.binary_dilation(body, iterations=4)
removed = suspect & ~keep
label[removed] = 4
edits.append(f'hair-left navy absorption -> fixed: {int(removed.sum())}px')
hl = label == 1
lab, n = ndi.label(hl)
sizes = ndi.sum_labels(hl, lab, range(1, n + 1))
main = lab == (1 + int(np.argmax(sizes)))
near = ndi.binary_dilation(main, iterations=5)
extra = hl & ~near
label[extra] = 4
edits.append(f'hair-left detached protrusions -> fixed: {int(extra.sum())}px')

# b) skirt navy invasion
sk = label == 3
navy = sk & (B > R) & (V < 135) & (R < 72)
label[navy] = 4
edits.append(f'skirt navy invasion -> fixed: {int(navy.sum())}px')

# c) band-limited root curve adjustment (v2 flats: left 219, right 250)
def curve(pts):
    b = np.full(W, 0.0)
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    for x in range(min(xs), max(xs) + 1):
        b[x] = np.interp(x, xs, ys)
    return b
hairish = np.isin(label, [1, 2, 4]) & (B - R >= -2) & (V >= 60)
for cls, pts, (x0, x1), flat in [
    (1, [(405, 200), (440, 220), (470, 228), (500, 220), (528, 242), (550, 278)], (395, 560), 219),
    (2, [(632, 238), (665, 222), (700, 214), (735, 222), (762, 242), (790, 268)], (620, 800), 250),
]:
    b = curve(pts)
    inwin = (xx >= x0) & (xx <= x1)
    above = inwin & (yy < b[xx]) & (label == cls)
    label[above] = 4
    band = inwin & (yy >= b[xx]) & (yy <= np.maximum(flat, b[xx]) + 25) & (label == 4) & hairish
    near = ndi.binary_dilation(label == cls, iterations=6)
    add = band & near
    label[add] = cls
    edits.append(f'root curve class {cls}: above->{int(above.sum())}px fixed, band below->{int(add.sum())}px bundle')

# d) locks -> fixed
pm = poly_mask([(612, 235), (668, 235), (676, 330), (660, 445), (636, 430), (620, 330)])
hit = pm & (label == 2)
label[hit] = 4
edits.append(f'right side-lock -> fixed: {int(hit.sum())}px')
hit = (label == 1) & (xx >= 503) & (yy <= 440)
label[hit] = 4
edits.append(f'left lock sliver -> fixed: {int(hit.sum())}px')

# e) skirt outer hem edges
sk = label == 3
rows = np.nonzero(sk.any(axis=1))[0]
for y in range(max(rows.min(), 1450), rows.max() + 1):
    xs = np.nonzero(sk[y])[0]
    if len(xs) == 0:
        continue
    sil_row = np.nonzero(label[y] != 0)[0]
    lo, hi = xs.min(), xs.max()
    slo, shi = sil_row.min(), sil_row.max()
    for x in range(slo, lo):
        if label[y, x] == 4 and (V[y, x] <= 175 or (R[y, x] - B[y, x]) >= 15):
            label[y, x] = 3
    for x in range(hi + 1, shi + 1):
        if label[y, x] == 4 and (V[y, x] <= 175 or (R[y, x] - B[y, x]) >= 15):
            label[y, x] = 3
edits.append('skirt outer hem edges extended (dark/gold only)')

# f) blouse-visible rebuilt
cloth = (label == 4) & (B - R >= 6) & (V <= 165) & (yy >= 330)
cloth = ndi.binary_closing(cloth, structure=np.ones((3, 3)), iterations=1)
lab, n = ndi.label(cloth)
blouse = np.zeros_like(cloth)
for i in range(1, n + 1):
    c = lab == i
    if c.sum() < 3000:
        continue
    ys, xs = np.nonzero(c)
    if 380 <= ys.mean() <= 1050:
        blouse |= c
prev_blouse = 126240
Image.fromarray((blouse * 255).astype(np.uint8)).save(OUTD + 'blouse-visible.png')
edits.append(f'blouse-visible rebuilt: {prev_blouse} -> {int(blouse.sum())}px')

# g) hem-trim v1-style: strong gold core + grow + dilate
skirt = label == 3
bottom = np.zeros(W, int)
for x in range(W):
    ys = np.nonzero(skirt[:, x])[0]
    bottom[x] = ys.max() if len(ys) else 0
goldness = R - B
band = skirt & (yy > 1400) & (yy >= bottom[None, :] - 75) & (yy <= bottom[None, :] - 4)
cand = band & (goldness >= 55) & (G - B >= 25)
grow = band & (goldness >= 28) & (G - B >= 8)
for _ in range(4):
    cand = cand | (grow & ndi.binary_dilation(cand, iterations=2))
trim = ndi.binary_dilation(cand, iterations=1) & skirt & (yy > 1400)
prev_trim = 2977
Image.fromarray((trim * 255).astype(np.uint8)).save(OUTD + 'hem-trim.png')
edits.append(f'hem-trim v1-style rebuild: {prev_trim} -> {int(trim.sum())}px')

np.save(WORK + 'label2_v3.npy', label)
def save_mask(mask, path):
    Image.fromarray((mask * 255).astype(np.uint8), mode='L').save(path)
for k in range(5):
    save_mask(label == k, OUTD + names[k] + '.png')
boundary = np.zeros((H, W), bool)
for dx, dy in ((1, 0), (0, 1)):
    boundary |= label != np.roll(label, (dy, dx), axis=(0, 1))
uncertain = ndi.binary_dilation(boundary, iterations=1)
save_mask(uncertain, OUTD + 'uncertain.png')
colors = {1: (255, 60, 60), 2: (255, 160, 0), 3: (0, 200, 255), 4: (120, 255, 120)}
ov = img.astype(float)
for k, c in colors.items():
    m = label == k
    ov[m] = ov[m] * 0.45 + np.array(c) * 0.55
ovim = Image.fromarray(ov.astype(np.uint8))
ovim.save(OUTD + 'overlay.png')
orig = Image.open(WORK + 'asset02.png').convert('RGB')
def check(name, box):
    a = orig.crop(box); b = ovim.crop(box)
    canvas = Image.new('RGB', (a.width * 2 + 8, a.height), (255, 255, 255))
    canvas.paste(a, (0, 0)); canvas.paste(b, (a.width + 8, 0))
    canvas.save(OUTD + name)
check('check-roots.png', (380, 90, 860, 420))
check('check-tips.png', (380, 620, 900, 1150))
check('check-sleeves.png', (280, 380, 880, 900))
check('check-waist.png', (300, 660, 850, 900))
check('check-trim.png', (200, 1450, 950, 1720))
bo = img.copy(); bo[blouse] = [255, 0, 255]
Image.fromarray(bo.astype(np.uint8)).save(OUTD + 'overlay-blouse.png')
to = img.copy(); to[trim] = [255, 0, 0]
Image.fromarray(to.astype(np.uint8)).save(OUTD + 'overlay-trim.png')
diff = np.zeros((H, W, 3), np.uint8)
diff[prev_label != label] = [255, 0, 0]
Image.fromarray(diff).save(OUTD + 'diff-v2-v3.png')
old_ov = img.astype(float)
for k, c in colors.items():
    m = prev_label == k
    old_ov[m] = old_ov[m] * 0.45 + np.array(c) * 0.55
trio = Image.new('RGB', (W * 3 // 2 + 16, H // 2), (255, 255, 255))
trio.paste(orig.resize((W // 2, H // 2)), (0, 0))
trio.paste(Image.fromarray(old_ov.astype(np.uint8)).resize((W // 2, H // 2)), (W // 2 + 8, 0))
trio.paste(ovim.resize((W // 2, H // 2)), (W + 16, 0))
trio.save(OUTD + 'compare-v1-v2-v3.png')
counts = {names[k]: int((label == k).sum()) for k in range(5)}
val = json.load(open(OUTD + 'validation.json'))
val['class_pixel_counts'] = counts
val['total_pixels'] = int(sum(counts.values()))
val['unclassified_pixels'] = int(W * H - sum(counts.values()))
val['aux_pixel_counts'] = {'blouse-visible': int(blouse.sum()), 'hem-trim': int(trim.sum()),
                           'uncertain': int(uncertain.sum())}
val['revision'] = 'v3 local polygon/curve fixes (see annotation-notes.md)'
val['v2_class_pixel_counts'] = prev_counts
json.dump(val, open(OUTD + 'validation.json', 'w'), ensure_ascii=False, indent=2)
man = json.load(open(OUTD + 'manifest.json'))
man['revision'] = 'v3 (2026-11-20): local polygon/curve fixes per ChatGPT v3 instruction; script annotation-v3.py'
json.dump(man, open(OUTD + 'manifest.json', 'w'), ensure_ascii=False, indent=2)
lm = json.load(open(OUTD + 'landmarks.json'))
lm['hair-left-root'] = {'x': 470, 'y': 224, 'note': 'hand-set curve under the left bow: (405,200)-(440,220)-(470,228)-(500,220)-(528,242)-(550,278); band-limited adjustment from v2 flat 219'}
lm['hair-right-root'] = {'x': 705, 'y': 224, 'note': 'hand-set curve under the right bow: (632,238)-(665,222)-(700,214)-(735,222)-(762,242)-(790,268); band-limited adjustment from v2 flat 250'}
json.dump(lm, open(OUTD + 'landmarks.json', 'w'), ensure_ascii=False, indent=2)
print('\n'.join(edits))
print('counts', counts)
