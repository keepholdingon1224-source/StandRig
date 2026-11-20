#!/usr/bin/env python3
"""Independent verification of experiment-008 reference masks.
Reads the SAVED PNG files directly (no label arrays, no prior validation.json)
and recomputes every check. Usage:
  python3 verify-reference.py <asset_dir> <original_png> <expected_original_sha256>
Writes <asset_dir>/reference-verification.json.
"""
import sys, os, json, hashlib
import numpy as np
from PIL import Image

PRIMARY = ['background', 'hair-left', 'hair-right', 'skirt', 'fixed']
AUX = ['blouse-visible', 'hem-trim', 'uncertain']

def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()

def main():
    asset_dir, original, expected_sha = sys.argv[1], sys.argv[2], sys.argv[3]
    result = {'asset_dir': os.path.basename(asset_dir.rstrip('/'))}
    result['original_sha256'] = sha256(original)
    result['original_sha256_matches_registered'] = result['original_sha256'] == expected_sha
    masks = {}
    file_hashes = {}
    ok = True
    for name in PRIMARY + AUX:
        p = os.path.join(asset_dir, name + '.png')
        file_hashes[name + '.png'] = sha256(p)
        im = Image.open(p)
        arr = np.array(im)
        vals = sorted(int(v) for v in np.unique(arr))
        masks[name] = arr
        entry = {'size': list(im.size), 'mode': im.mode, 'unique_values': vals,
                 'white_pixels': int((arr == 255).sum())}
        if im.size != (1152, 2048) or vals != [0, 255]:
            ok = False
        result[name] = entry
    stack = np.stack([(masks[n] == 255) for n in PRIMARY])
    cover = stack.sum(axis=0)
    result['primary_overlap_pixels'] = int((cover > 1).sum())
    result['primary_unclassified_pixels'] = int((cover == 0).sum())
    result['blouse_subset_fixed_violations'] = int((masks['blouse-visible'] == 255) & ~(masks['fixed'] == 255)).__int__() if False else int(((masks['blouse-visible'] == 255) & (masks['fixed'] != 255)).sum())
    result['hemtrim_subset_skirt_violations'] = int(((masks['hem-trim'] == 255) & (masks['skirt'] != 255)).sum())
    for extra in ['landmarks.json', 'manifest.json', 'annotation-notes.md', 'annotation-v3.py']:
        p = os.path.join(asset_dir, extra)
        if os.path.exists(p):
            file_hashes[extra] = sha256(p)
    result['file_sha256'] = file_hashes
    result['all_checks_passed'] = bool(
        ok and result['original_sha256_matches_registered']
        and result['primary_overlap_pixels'] == 0
        and result['primary_unclassified_pixels'] == 0
        and result['blouse_subset_fixed_violations'] == 0
        and result['hemtrim_subset_skirt_violations'] == 0)
    with open(os.path.join(asset_dir, 'reference-verification.json'), 'w') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(json.dumps({k: result[k] for k in ('original_sha256_matches_registered',
          'primary_overlap_pixels', 'primary_unclassified_pixels',
          'blouse_subset_fixed_violations', 'hemtrim_subset_skirt_violations',
          'all_checks_passed')}, indent=2))

if __name__ == '__main__':
    main()
