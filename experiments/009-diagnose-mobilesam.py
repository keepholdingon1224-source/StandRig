"""Isolated 008 ablations. Reference-derived prompts are diagnostic only."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import resource
from time import perf_counter

import cv2 as cv
import numpy as np
from scipy.ndimage import distance_transform_edt


def load_experiment(filename):
    spec = importlib.util.spec_from_file_location(filename, Path(__file__).with_name(filename))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


baseline = load_experiment("008-segment.py")
evaluation = load_experiment("008-evaluate.py")


def interior_points(mask):
    rows = np.flatnonzero(mask.any(axis=1))
    bands = np.array_split(rows, 5)
    depth = distance_transform_edt(mask)
    points = []
    for band in bands:
        y, x = np.unravel_index(depth[band].argmax(), depth[band].shape)
        points.append([x, band[y]])
    return np.asarray(points)


def negative_points(reference, box):
    x0, y0, x1, y1 = box
    points = []
    for label in ("fixed", "blouse-visible", "skirt"):
        mask = reference[label].copy()
        mask[:y0] = mask[y1 + 1:] = False
        mask[:, :x0] = mask[:, x1 + 1:] = False
        if mask.any():
            y, x = np.unravel_index(distance_transform_edt(mask).argmax(), mask.shape)
            points.append([x, y])
    return np.asarray(points, dtype=int).reshape(-1, 2)


def run(args):
    began = perf_counter()
    args.output.mkdir(parents=True, exist_ok=False)
    image = cv.imread(str(args.source))
    reference = {name: evaluation.read(args.reference / f"{name}.png")
                 for name in (*evaluation.PRIMARY, *evaluation.AUX)}
    predictor, model = baseline.load_predictor(args.mobile_sam)
    prior = baseline.proposals(image)
    prior = prior[0] if isinstance(prior, tuple) else prior
    exact = baseline.ai_masks(image, prior, predictor)
    rows = []

    def record(part, variant, mask, assisted, score=None):
        path = args.output / f"{part}-{variant}.png"
        baseline.save_mask(path, mask)
        truth = reference[part]
        tp = int((mask & truth).sum())
        fp = int((mask & ~truth).sum())
        fn = int((~mask & truth).sum())
        rows.append({"part": part, "variant": variant, "reference_prompt": assisted,
                     "iou": evaluation.divide(tp, tp + fp + fn),
                     "precision": evaluation.divide(tp, tp + fp),
                     "recall": evaluation.divide(tp, tp + fn), "fp": fp, "fn": fn,
                     "selection_score": score,
                     "mask": path.name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})

    for part in evaluation.PARTS:
        seed = prior[part]
        truth = reference[part]
        yy, xx = np.where(seed)
        if not yy.size:
            raise ValueError(f"008 prior was empty for {part}")
        margin = max(5, round(.12 * (xx.max() - xx.min())))
        box = np.clip([xx.min()-margin, yy.min()-margin, xx.max()+margin, yy.max()+margin],
                      0, np.tile([seed.shape[1]-1, seed.shape[0]-1], 2))
        interior_point = np.unravel_index(distance_transform_edt(seed).argmax(), seed.shape)
        point = np.array([[interior_point[1], interior_point[0]]])
        ty, tx = np.where(truth)
        full_box = np.array([tx.min(), ty.min(), tx.max(), ty.max()])
        positives = interior_points(truth)
        negatives = negative_points(reference, full_box) if part.startswith("hair") else np.empty((0, 2), int)
        record(part, "008-exact", exact[part], False)

        prompts = (
            ("008-input", point, box, np.empty((0, 2), int), False),
            ("reference-points", positives, box, np.empty((0, 2), int), True),
            ("reference-box", point, full_box, np.empty((0, 2), int), True),
            ("reference-points-box", positives, full_box, np.empty((0, 2), int), True),
            ("reference-points-box-negatives", positives, full_box, negatives, True),
        )
        for mode, positive, region, negative, assisted in prompts:
            masks, scores, _ = predictor.predict(
                np.concatenate([positive, negative]),
                np.concatenate([np.ones(len(positive)), np.zeros(len(negative))]),
                box=region, multimask_output=True,
            )
            overlap = np.array([evaluation.iou(mask, seed) or 0 for mask in masks])
            selections = {"008-rank": .78 * overlap + .22 * scores, "sam-rank": scores}
            for rank, values in selections.items():
                idx = int(values.argmax())
                uncut = masks[idx]
                for crop in ("uncut", "008-cut") if part.startswith("hair") else ("uncut",):
                    mask = uncut
                    if crop == "008-cut":
                        mask = uncut & (np.arange(seed.shape[0])[:, None] >= yy.min() - margin // 3)
                    record(part, f"{mode}-{rank}-{crop}", baseline.largest(mask), assisted, float(values[idx]))
    report = {"model": model, "source_sha256": hashlib.sha256(args.source.read_bytes()).hexdigest(),
              "seconds": perf_counter() - began, "peak_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
              "scope": "diagnostics only; never use reference prompts or this grid for automatic prediction",
              "postprocess": "008-exact includes original part priority/foreground packing. Other rows use largest component only.",
              "rows": rows}
    (args.output / "metrics.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("reference", type=Path)
    parser.add_argument("mobile_sam", type=Path)
    parser.add_argument("output", type=Path)
    run(parser.parse_args())
