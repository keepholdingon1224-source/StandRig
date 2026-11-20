"""Score saved predictions against frozen PNGs. No predictor imports."""
import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image
from scipy.ndimage import binary_erosion, distance_transform_edt

PARTS = ("hair-left", "hair-right", "skirt")
PRIMARY = (*PARTS, "fixed", "background")
AUX = ("blouse-visible", "hem-trim", "uncertain")
SIZE = (1152, 2048)
THRESHOLD = .90
ROOT_RADIUS = 32
COLORS = ((249, 75, 94), (255, 220, 55), (49, 182, 249))


def read(path):
    with Image.open(path) as image:
        if image.size != SIZE or image.mode != "L":
            raise ValueError(f"Unexpected mask format: {path}")
        arr = np.asarray(image)
        if not np.all((arr == 0) | (arr == 255)):
            raise ValueError(f"Non-binary pixels: {path}")
        return arr == 255


def divide(num, den):
    return float(num / den) if den else None


def iou(a, b):
    return divide(np.count_nonzero(a & b), np.count_nonzero(a | b))


def root_xy(mask):
    rows = np.flatnonzero(mask.any(axis=1))
    if not rows.size:
        return None
    y = int(rows[0])
    return [float(np.median(np.flatnonzero(mask[y]))), y]


def metric(pred, truth, uncertain, fixed):
    tp = int((pred & truth).sum())
    fp = int((pred & ~truth).sum())
    fn = int((~pred & truth).sum())
    pb = pred & ~binary_erosion(pred, border_value=0)
    tb = truth & ~binary_erosion(truth, border_value=0)
    p_dist = distance_transform_edt(~tb)[pb] if tb.any() else np.full(pb.sum(), np.inf)
    t_dist = distance_transform_edt(~pb)[tb] if pb.any() else np.full(tb.sum(), np.inf)
    f1 = {}
    for radius in (1, 2, 4):
        precision = divide((p_dist <= radius).sum(), pb.sum())
        recall = divide((t_dist <= radius).sum(), tb.sum())
        f1[str(radius)] = 2 * precision * recall / (precision + recall) if precision and recall else 0.0
    score = divide(tp, tp + fp + fn)
    return {"iou": score, "passes_0_90": score is not None and score >= THRESHOLD,
            "iou_without_uncertain": iou(pred & ~uncertain, truth & ~uncertain),
            "precision": divide(tp, tp + fp), "recall": divide(tp, tp + fn),
            "true_positive_pixels": tp, "false_positive_pixels": fp, "false_negative_pixels": fn,
            "boundary_f1": f1, "fixed_pixels_misclassified": int((pred & fixed).sum()),
            "empty": not pred.any()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("reference", type=Path)
    parser.add_argument("predictions", type=Path)
    parser.add_argument("results", type=Path)
    args = parser.parse_args()
    asset = args.reference.name
    refs = {name: read(args.reference / f"{name}.png") for name in (*PRIMARY, *AUX)}
    landmarks = json.loads((args.reference / "landmarks.json").read_text())
    with Image.open(args.source) as original:
        rgb = np.asarray(original.convert("RGB"))
    y, x = np.ogrid[:SIZE[1], :SIZE[0]]
    root_windows = {}
    for part in PARTS[:2]:
        target = landmarks[f"{part}-root"]
        root_windows[part] = (x-target["x"]) ** 2 + (y-target["y"]) ** 2 <= ROOT_RADIUS ** 2
    report = {"threshold": THRESHOLD, "formal_includes_uncertain": True,
              "root_local_region": "disk of radius 32 pixels around each reference root", "methods": {}}
    for directory in sorted(args.predictions.iterdir()):
        if not (directory / "run.json").exists():
            continue
        method = directory.name
        masks = {name: read(directory / f"{name}.png") for name in PRIMARY}
        coverage = sum((mask.astype("uint8") for mask in masks.values()))
        run = json.loads((directory / "run.json").read_text())
        counts = {"overlap_pixels": int((coverage > 1).sum()), "unclassified_pixels": int((coverage == 0).sum()),
                  "empty_primary": [name for name, mask in masks.items() if not mask.any()]}
        row = {"coverage": counts, "run": run, "parts": {}}
        overlay = rgb.copy()
        error_dir = args.results / "errors" / asset / method
        error_dir.mkdir(parents=True, exist_ok=True)
        for name, color in zip(PARTS, COLORS):
            mask, truth = masks[name], refs[name]
            overlay[mask] = np.rint(.60*rgb[mask] + .40*np.array(color)).astype("uint8")
            values = metric(mask, truth, refs["uncertain"], refs["fixed"])
            if name in root_windows:
                root = root_xy(mask)
                ref = landmarks[f"{name}-root"]
                window = root_windows[name]
                values.update({"root_xy": root,
                               "root_error_px": float(np.hypot(root[0]-ref["x"], root[1]-ref["y"])) if root else None,
                               "root_local_iou": iou(mask & window, truth & window)})
            else:
                values["trim_inclusion"] = divide((mask & refs["hem-trim"]).sum(), refs["hem-trim"].sum())
                values["blouse_contamination_pixels"] = int((mask & refs["blouse-visible"]).sum())
            row["parts"][name] = values
            labels = np.zeros((*truth.shape, 3), dtype="uint8")
            labels[mask & ~truth] = (255, 76, 76)
            labels[truth & ~mask] = (65, 164, 255)
            Image.fromarray(labels).save(error_dir / f"{name}-pixels.png")
            pb = mask & ~binary_erosion(mask)
            tb = truth & ~binary_erosion(truth)
            labels[:] = 0
            labels[pb] = (255, 76, 76)
            labels[tb] = (65, 164, 255)
            labels[pb & tb] = (230, 230, 230)
            Image.fromarray(labels).save(error_dir / f"{name}-boundaries.png")
        overlay_path = args.results / "overlays" / asset / f"{method}.png"
        overlay_path.parent.mkdir(parents=True, exist_ok=True)
        Image.fromarray(overlay).save(overlay_path)
        lm_path = args.results / "landmarks" / asset / f"{method}.json"
        lm_path.parent.mkdir(parents=True, exist_ok=True)
        predictions = run.get("landmarks", {name: {"root_xy": root_xy(masks[name]), "centerline_xy": [
            [float(np.median(np.flatnonzero(masks[name][yy]))), int(yy)]
            for yy in np.flatnonzero(masks[name].any(axis=1))]} for name in PARTS})
        lm_path.write_text(json.dumps(predictions, indent=2) + "\n")
        row["all_parts_pass"] = all(item["passes_0_90"] for item in row["parts"].values())
        report["methods"][method] = row
    (args.results / "logs" / f"metrics-{asset}.json").write_text(json.dumps(report, indent=2) + "\n")
    for method, row in report["methods"].items():
        print(method, *(f"{name}={row['parts'][name]['iou']:.6f}" for name in PARTS))


if __name__ == "__main__":
    main()
