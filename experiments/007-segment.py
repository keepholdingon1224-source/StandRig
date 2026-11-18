"""Asset-local color segmentation and hidden-pixel completion for experiment 007."""
import hashlib
import json
from pathlib import Path
from time import perf_counter

import cv2 as cv
import numpy as np
from scipy.ndimage import gaussian_filter1d

START = perf_counter()
SOURCE = Path('source_007/original.png')
OUT = Path('results/007-character-application')
EXPECTED = 'a1388c37f35c19278d346ab4491c8bcc919e1f375b07f312a70ab7e87bbcbcea'
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == EXPECTED
image = cv.imread(str(SOURCE))
h, w = image.shape[:2]
y, x = np.indices((h, w))
blue, green, red = image.astype(np.int16).transpose(2, 0, 1)

def save(path, pixels):
    assert cv.imwrite(str(OUT / path), pixels)

def record(path, value):
    (OUT / path).write_text(json.dumps(value, indent=2) + '\n')

def largest(mask):
    count, labels, stats, _ = cv.connectedComponentsWithStats(mask.astype('uint8'))
    if count < 2:
        raise ValueError('No foreground component')
    return labels == (1 + stats[1:, cv.CC_STAT_AREA].argmax())

def fill(mask):
    contours, _ = cv.findContours(mask.astype('uint8'), cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE)
    return cv.drawContours(np.zeros((h, w), np.uint8), contours, -1, 1, cv.FILLED).astype(bool)

def clean(mask, size):
    return cv.morphologyEx(mask.astype('uint8'), cv.MORPH_CLOSE, np.ones((size, size), np.uint8)).astype(bool)

# Sample the background palette from image margins. Blank backgrounds with
# unrelated colors require a different segmentation method.
margin = np.concatenate((image[:, :w//20], image[:, -w//20:]), axis=1)
bg = np.median(margin, axis=(0, 1))
subject = fill(largest(clean(np.max(np.abs(image - bg), axis=2) > 17, 9)))
skirt_core = fill(largest(clean((blue-red > 24) & (green-red > 23) & subject, 17)))
sk_y, sk_x = np.where(skirt_core)
mid_x = int(np.median(sk_x))
waist = int(np.quantile(sk_y, 0.002))
shoulder = int(np.where(subject)[0].min() + .54 * (waist - np.where(subject)[0].min()))
brown = clean((red-blue > 21) & (red-green > 12) & (red < 177) & (green < 136), 9) & subject

def hair(side):
    sliced = brown & ((x < mid_x) if side == 'left' else (x >= mid_x))
    # Find the neck of the strand by scanning upward from the lower free
    # segment. Width expansion signals the upper tied hair mass.
    lower = largest(sliced & (y >= shoulder))
    rows = np.where(lower.any(axis=1))[0]
    width = gaussian_filter1d(lower.sum(axis=1).astype(float), 4)
    span = rows[-1] - rows[0]
    normal = np.median(width[rows[0]+span//2:rows[-1]-span//10])
    candidates = np.flatnonzero((width > normal * 1.48) &
                                (np.arange(h) < rows[-1]-span*.37))
    root = int(candidates[-1]+1) if candidates.size else int(rows[0])
    return fill(largest(lower & (y >= root)))

masks = {side: hair(side) for side in ('left', 'right')}
masks['skirt'] = skirt_core & ~(masks['left'] | masks['right'])
masks['skirt-left'] = masks['skirt'] & (x < mid_x)
masks['skirt-right'] = masks['skirt'] & (x >= mid_x)
moving = masks['left'] | masks['right'] | masks['skirt']
masks['fixed'] = subject & ~moving
masks['background'] = ~subject
overlay = image.copy()
geometry = {}
for name, mask in masks.items():
    yy, xx = np.where(mask)
    alpha = mask.astype('uint8') * 255
    save(f'segmentation/{name}-binary.png', alpha)
    save(f'segmentation/{name}-alpha.png', alpha)
    save(f'segmentation/{name}.png', np.dstack((image, alpha)))
    geometry[name] = {'bboxXYWH': [int(xx.min()), int(yy.min()),
                                  int(np.ptp(xx)+1), int(np.ptp(yy)+1)]}
for name, color in [('left', (30, 70, 255)), ('right', (45, 210, 250)), ('skirt', (240, 70, 40))]:
    mask = masks[name]
    overlay[mask] = np.rint(image[mask]*.65 + np.array(color)*.35).astype('uint8')
save('segmentation/overlay.png', overlay)
record('source/input.json', {'path': str(SOURCE), 'sha256': EXPECTED, 'dimensions': [w,h],
                             'mode': 'RGB', 'format': 'PNG', 'generationConditions': None})
record('segmentation/parts.json', {'parts': geometry, 'drawOrder': ['background','fixed','skirt','left','right'],
                                  'method': 'RGB differences, connected components, closing, contour fill, width transition',
                                  'parameterSource': 'Asset-class palette and silhouette heuristics',
                                  'individualCoordinates': [], 'alpha': 'binary matte',
                                  'opencv': cv.__version__, 'seconds': perf_counter()-START})

# Assisted variant: cut lines annotated after inspection of the automatic
# overlay. The image-left tied cap was included and the right root was missed.
assist_start = perf_counter()
assist = OUT / 'segmentation/assisted'
assist.mkdir(exist_ok=True)
for side, root in [('left', 538), ('right', 452)]:
    half = (x < mid_x) if side == 'left' else (x >= mid_x)
    masks[side] = fill(largest(brown & half & (y >= root)))
    # Recover the dark outline next to the brown seed without including nearby
    # pink skin or a white blouse highlight.
    seed = masks[side]
    border = cv.dilate(seed.astype('uint8'), np.ones((7,7),np.uint8)).astype(bool)
    masks[side] = fill(seed | (border & (y >= root) & (red < 116) & (green < 105) & (red-blue >= 5)))
hair_mask = masks['left'] | masks['right']
outline = cv.dilate(skirt_core.astype('uint8'), np.ones((15,15),np.uint8)).astype(bool)
outline &= (red < 180) & (green < 180) & (blue > red-15) & (y >= waist+10)
skirt_core = fill(largest(skirt_core | outline))
skirt = fill(largest(clean(skirt_core | (hair_mask & (y >= waist)), 25))) & ~((y < waist) & ~skirt_core)
# Extend the skirt under the hair only where it meets known skirt pixels.
skirt &= skirt_core | hair_mask
hair_only = hair_mask & ~skirt
skirt_hidden = skirt & hair_mask
skirt_known = skirt & ~hair_mask
skirt_texture = image.copy()
from scipy.ndimage import distance_transform_edt
neighbors = distance_transform_edt(~skirt_known, sampling=(4,1), return_distances=False, return_indices=True)
skirt_texture[skirt_hidden] = image[tuple(neighbors[:, skirt_hidden])]
background = np.broadcast_to(np.rint(bg).astype('uint8'), image.shape)
base = image.copy()
base[skirt] = background[skirt]
hole = hair_only.astype('uint8') * 255
# Compare two local alternatives for the exposed shirt and edge regions.
telea = cv.inpaint(base, hole, 5, cv.INPAINT_TELEA)
navier = cv.inpaint(base, hole, 5, cv.INPAINT_NS)
save('reconstruction/inpaint-nav-stokes.png', navier)
save('reconstruction/inpaint-telea.png', telea)
# Inpainting propagates dark boundary strokes across the full cavity. Sample
# clean colors on both sides per row, then interpolate across each strand.
for side in ('left', 'right'):
    cavity = masks[side] & hair_only
    for row in np.flatnonzero(cavity.any(axis=1)):
        columns = np.flatnonzero(cavity[row])
        a, b = columns[0], columns[-1]
        def sample(start, stop):
            source = base[row,max(0,start):min(w,stop)]
            bright = source[source.max(axis=1)>=147]
            return np.median(bright if len(bright) else source, axis=0)
        start = sample(a-13, a-3)
        end = sample(b+4, b+14)
        weight = ((columns-a+1)/(b-a+2))[:,None]
        base[row,columns] = np.rint(start*(1-weight)+end*weight).astype('uint8')
# Recover the small portion of each calf exposed by the hem's horizontal
# displacement. Transfer only visible skin immediately below the skirt.
legs = np.zeros((h,w),bool)
for col in range(w):
    below = np.flatnonzero((red[:,col]-blue[:,col]>23)&(red[:,col]>152)&(y[:,col]>int(sk_y.max())-90)&~skirt[:,col])
    skirt_rows = np.flatnonzero(skirt[:,col])
    if len(below) and len(skirt_rows) and 0 < below[0]-skirt_rows[-1] <= 12:
        end = int(skirt_rows[-1])+1
        start = max(0,end-28)
        legs[start:end,col] = skirt[start:end,col]
        base[start:end,col][legs[start:end,col]] = image[below[0],col]
save('reconstruction/leg-extension-mask.png',legs.astype('uint8')*255)
save('reconstruction/completed-base.png', base)
save('reconstruction/synthesized-mask.png', (skirt | hair_mask).astype('uint8')*255)
save('reconstruction/skirt-hidden-mask.png', skirt_hidden.astype('uint8')*255)
save('reconstruction/hair-exposure-mask.png', hole)
save('reconstruction/background-completion-mask.png', skirt.astype('uint8')*255)
save('reconstruction/source-preserved-mask.png', (~(skirt | hair_mask)).astype('uint8')*255)
masks['skirt'] = skirt
masks['skirt-left'] = skirt & (x < mid_x)
masks['skirt-right'] = skirt & (x >= mid_x)
masks['fixed'] = subject & ~(skirt | hair_mask)
annotated = image.copy()
for name, mask in masks.items():
    alpha = mask.astype('uint8')*255
    colors = skirt_texture if name.startswith('skirt') else image
    save(f'segmentation/assisted/{name}-binary.png', alpha)
    save(f'segmentation/assisted/{name}.png', np.dstack((np.where(mask[...,None], colors, 0), alpha)))
    if name in ('left', 'right', 'skirt'):
        annotated[mask] = np.rint(image[mask]*.65 + np.array((30,80,255) if name!='skirt' else (250,80,40))*.35).astype('uint8')
save('segmentation/assisted/overlay.png', annotated)
static = base.copy()
static[skirt] = skirt_texture[skirt]
static[hair_mask] = image[hair_mask]
save('reconstruction/static.png', static)
save('reconstruction/difference.png', cv.absdiff(image, static))
assert np.array_equal(image, static)
record('reconstruction/method.json', {
    'shirt': 'Row-wise clean endpoint color interpolation; OpenCV Telea and Navier-Stokes comparison',
    'skirt': 'nearest known skirt sample with vertical distance weighted 4x',
    'background': 'median BGR from source margins',
    'hiddenLegs': 'Short vertical transfer of visible skin below the hem', 'staticChangedPixels': 0,
    'assistedRootRows': {'left': 538, 'right': 452},
    'processingSeconds': perf_counter()-assist_start, 'manualOperations': 2
})
