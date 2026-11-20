#!/usr/bin/env python3
"""asset-01 v3 LOCAL polygon fixes (per ChatGPT v3 instruction).
Explicit edit polygons - no global re-extraction.
1) hair-left specks on forearm/cuff zone -> fixed
2) fixed-class islands inside both tails -> bundle class
3) hair-right specks on blouse (x>=690, y 560-760) -> fixed
4) blouse-visible: thin false strips along forearms removed by polygons
5) hem-trim: rebuilt by per-column gold scan along the visible line
"""
import numpy as np, json
from PIL import Image, ImageDraw
from scipy import ndimage as ndi

WORK = '/home/hatch/workspace/live2d-research/material-008/work/'
OUTD = '/home/hatch/workspace/live2d-research/material-008/reference/asset-01/'
img = np.array(Image.open(WORK + 'asset01.png').convert('RGB')).astype(int)
H, W, _ = img.shape
R, G, B = img[..., 0], img[..., 1], img[..., 2]
label = np.load(WORK + 'label_v2.npy')
prev_label = label.copy()
names = {0: 'background', 1: 'hair-left', 2: 'hair-right', 3: 'skirt', 4: 'fixed'}
prev_counts = {names[k]: int((prev_label == k).sum()) for k in range(5)}

def poly_mask(poly):
    m = Image.new('L', (W, H), 0)
    ImageDraw.Draw(m).polygon(poly, fill=1)
    return np.array(m) > 0

edits = []
# 1) forearm/cuff specks
pm = poly_mask([(398, 795), (432, 795), (432, 862), (398, 862)])
hit = pm & (label == 1)
label[hit] = 4
edits.append(f'hair-left forearm/cuff specks -> fixed: {int(hit.sum())}px (polygon x398-432,y795-862)')
# 3) blouse specks right of right tail
pm = poly_mask([(690, 560), (730, 560), (730, 760), (690, 760)])
hit = pm & (label == 2)
label[hit] = 4
edits.append(f'hair-right blouse specks -> fixed: {int(hit.sum())}px (polygon x690-730,y560-760)')
# 2) fixed islands inside tails -> bundle
for cls, (x0, x1, y0, y1) in {1: (390, 520, 545, 905), 2: (605, 720, 460, 770)}.items():
    sub = (label == 4) & (np.mgrid[0:H, 0:W][1] >= x0) & (np.mgrid[0:H, 0:W][1] <= x1) & \
          (np.mgrid[0:H, 0:W][0] >= y0) & (np.mgrid[0:H, 0:W][0] <= y1)
    lab, n = ndi.label(sub)
    cnt = 0
    for i in range(1, n + 1):
        c = lab == i
        if c.sum() <= 60 and (ndi.binary_dilation(c, iterations=1) & (label == cls)).any():
            label[c] = cls
            cnt += int(c.sum())
    edits.append(f'fixed islands inside class {cls} -> bundle: {cnt}px')

# 4) blouse arm strips
blouse = np.array(Image.open(OUTD + 'blouse-visible.png')) > 0
prev_blouse = int(blouse.sum())
for poly in [[(338, 820), (368, 820), (368, 1000), (338, 1000)],
             [(788, 830), (820, 830), (820, 1010), (788, 1010)]]:
    pm = poly_mask(poly)
    hit = pm & blouse
    blouse[hit] = False
    edits.append(f'blouse arm strip removed: {int(hit.sum())}px (polygon {poly[0]}-{poly[2]})')
Image.fromarray((blouse * 255).astype(np.uint8)).save(OUTD + 'blouse-visible.png')

# 5) hem-trim by per-column gold scan
skirt = label == 3
bottom = np.zeros(W, int)
for x in range(W):
    ys = np.nonzero(skirt[:, x])[0]
    bottom[x] = ys.max() if len(ys) else 0
goldness = R - B
trim = np.zeros((H, W), bool)
yy, xx = np.mgrid[0:H, 0:W]
for x in range(W):
    if bottom[x] == 0:
        continue
    band = slice(max(0, bottom[x] - 62), max(0, bottom[x] - 6))
    g = goldness[band, x]
    if len(g) and g.max() >= -10:
        ybest = band.start + int(np.argmax(g))
        for dy in (-1, 0, 1):
            y = ybest + dy
            if 0 <= y < H and skirt[y, x] and goldness[y, x] >= -25:
                trim[y, x] = True
# connect small horizontal gaps along the line
lab, n = ndi.label(trim)
sizes = ndi.sum_labels(trim, lab, range(1, n + 1))
trim = np.isin(lab, [i + 1 for i, s in enumerate(sizes) if s >= 4])
trim = ndi.binary_dilation(trim, iterations=1) & skirt & (yy > 1450)
prev_trim = json.load(open(OUTD + 'validation.json'))['aux_pixel_counts']['hem-trim']
Image.fromarray((trim * 255).astype(np.uint8)).save(OUTD + 'hem-trim.png')
edits.append(f'hem-trim rescanned per-column: {prev_trim} -> {int(trim.sum())}px')

np.save(WORK + 'label_v3.npy', label)
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
orig = Image.open(WORK + 'asset01.png').convert('RGB')
def check(name, box):
    a = orig.crop(box); b = ovim.crop(box)
    canvas = Image.new('RGB', (a.width * 2 + 8, a.height), (255, 255, 255))
    canvas.paste(a, (0, 0)); canvas.paste(b, (a.width + 8, 0))
    canvas.save(OUTD + name)
check('check-roots.png', (330, 340, 760, 820))
check('check-tips.png', (330, 480, 760, 980))
check('check-sleeves.png', (280, 480, 880, 900))
check('check-waist.png', (300, 680, 850, 920))
check('check-trim.png', (200, 1540, 950, 1800))
# aux overlays + diff + 3-way
bo = img.copy(); bo[blouse] = [255, 0, 255]
Image.fromarray(bo.astype(np.uint8)).save(OUTD + 'overlay-blouse.png')
to = img.copy(); to[trim] = [255, 0, 0]
Image.fromarray(to.astype(np.uint8)).save(OUTD + 'overlay-trim.png')
diff = np.zeros((H, W, 3), np.uint8)
chg = prev_label != label
diff[chg] = [255, 0, 0]
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
val['revision'] = 'v3 local polygon fixes (see annotation-notes.md)'
val['v2_class_pixel_counts'] = prev_counts
json.dump(val, open(OUTD + 'validation.json', 'w'), ensure_ascii=False, indent=2)
man = json.load(open(OUTD + 'manifest.json'))
man['revision'] = 'v3 (2026-11-20): local polygon fixes per ChatGPT v3 instruction; script annotation-v3.py'
json.dump(man, open(OUTD + 'manifest.json', 'w'), ensure_ascii=False, indent=2)
print('\n'.join(edits))
print('counts', counts, 'blouse', int(blouse.sum()), 'trim', int(trim.sum()))
