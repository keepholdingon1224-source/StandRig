"""Assemble the two-asset record and cross-check saved scores using Pillow histograms."""
import csv
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys

from PIL import Image, ImageChops

ROOT = Path("results/008-segmentation-accuracy")
LOGS = ROOT / "logs"
ASSETS = ("asset-01", "asset-02")
PARTS = ("hair-left", "hair-right", "skirt")
METHODS = ("A-007-auto", "A-007-assisted", "B-opencv", "C-mobile-sam", "D-tta", "E-mirror")
START = "06d77d8ea4d8432115eabe738f8d3e9feb2df822"
FREEZE = "c0ea3bba6421fe6a7d98546b64cd7dd5493f9d44"


def read(path):
    return json.loads(path.read_text())


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def output(*args):
    return subprocess.check_output(args, text=True).strip()


def count_iou(path_a, path_b):
    with Image.open(path_a) as a, Image.open(path_b) as b:
        intersection = ImageChops.darker(a, b).histogram()[255]
        union = ImageChops.lighter(a, b).histogram()[255]
    return intersection / union if union else None


def main():
    assets = {name: read(LOGS / f"metrics-{name}.json") for name in ASSETS}
    model = read(ROOT / "model-selection.json")
    model["freeze_commit"] = FREEZE
    for file, expected in model["code_sha256"].items():
        assert digest(Path(file)) == expected
    selected = model["selected_method"]
    selected_rows = {a: assets[a]["methods"][selected] for a in ASSETS}
    checks = {}
    table = []
    for asset in ASSETS:
        for method, entry in assets[asset]["methods"].items():
            checks[f"{asset}/{method}"] = {}
            for part, score in entry["parts"].items():
                pred = ROOT / "predictions" / asset / method / f"{part}.png"
                ref = ROOT / "reference" / asset / f"{part}.png"
                checked = count_iou(pred, ref)
                assert checked == score["iou"], (asset, method, part)
                assert score["passes_0_90"] == (checked is not None and checked >= .90)
                checks[f"{asset}/{method}"][part] = checked
                run = entry["run"]
                table.append({
                    "asset": asset, "method": method,
                    "mode": "assisted" if method.endswith("assisted") else "automatic",
                    "part": part, "status": "not_generated" if part in run.get(
                        "unavailable_roles_zero_filled_for_scoring", []
                    ) else ("pass" if score["passes_0_90"] else "fail"),
                    "iou": checked, "precision": score["precision"], "recall": score["recall"],
                    "false_positive_pixels": score["false_positive_pixels"],
                    "false_negative_pixels": score["false_negative_pixels"],
                    **{f"boundary_f1_{radius}px": score["boundary_f1"][str(radius)] for radius in (1, 2, 4)},
                    "seconds": run.get("seconds", run.get("total_replay_seconds")),
                    "peak_rss_kib": run.get("peak_process_rss_kib", run.get("peak_child_rss_kib")),
                    "manual_interventions": run["manual_interventions"],
                    "overlap_pixels": entry["coverage"]["overlap_pixels"],
                    "unclassified_pixels": entry["coverage"]["unclassified_pixels"],
                })
    with (ROOT / "method-comparison.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(table[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(table)
    before, after = (read(LOGS / f"reference-{phase}.json") for phase in ("before", "after"))
    assert before["protected_sha256"] == after["protected_sha256"]
    assert not before["frozen_input_changes"] and not after["frozen_input_changes"]
    for row in after["references"].values():
        assert row["original_dimensions_match"] and row["saved_png_checks"]["all_checks_passed"]
        assert len(row["png_8bit_grayscale_binary"]) == 8 and all(row["png_8bit_grayscale_binary"].values())
        assert set(row["frozen_sha256_mismatches"]) == {"manifest.json", "annotation-notes.md"}
    legacy = read(LOGS / "regression-007-verification.json")
    gui = read(LOGS / "regression-007-gui.json")
    diagnostic = read(LOGS / "diagnostic-video-decode.json")
    assert legacy["numericAndOperationalChecksPassed"] and gui["status"] == "pass"
    assert len(diagnostic) == 6 and all(row["status"] == "pass" for row in diagnostic.values())
    assert "ℹ pass 183" in (LOGS / "npm-test.log").read_text()
    assert "ℹ fail 0" in (LOGS / "npm-test.log").read_text()
    assert "built in" in (LOGS / "build.log").read_text()
    verification = {
        "reference_inputs": {"status": "pass", "pngs_checked": 16, "originals_checked": 2,
                             "freeze_document_hash_index": "mismatch_in_four_metadata_entries",
                             "detail": "logs/reference-document-discrepancies.json",
                             "before": "logs/reference-before.json", "after": "logs/reference-after.json"},
        "protection": {"status": "pass", "matched_file_count": len(before["protected_sha256"]),
                       "includes": "005–007 code/results/acceptance records, both originals, all fixed references"},
        "independent_iou_recalculation": {"status": "pass", "implementation": "Pillow darker/lighter + histogram",
                                           "checked_values": checks},
        "build": {"status": "pass", "log": "logs/build.log"},
        "npm_test": {"status": "pass", "passed": 183, "failed": 0, "log": "logs/npm-test.log"},
        "007_numeric_and_video_regression": {"status": "pass", "results": "logs/regression-007-verification.json",
                                              "all_decoded_videos": legacy["checks"]["videos"]},
        "007_gui_regression": {"status": "pass", "operations": gui["checks"], "log": "logs/regression-007-gui.json"},
        "008_diagnostic_videos": diagnostic,
        "008_baked_animation_video": {"status": "not_run", "reason": "Formal automatic segmentation failed."},
        "008_gui_with_new_rig": {"status": "not_run", "reason": "No model passed the automatic segmentation gate."},
    }
    deltas = {}
    for asset in ASSETS:
        m = assets[asset]["methods"]
        def diff(first, second):
            return {p: m[first]["parts"][p]["iou"] - m[second]["parts"][p]["iou"] for p in PARTS}
        deltas[asset] = {
            "B_minus_A_auto": diff("B-opencv", "A-007-auto"),
            "C_minus_B": diff("C-mobile-sam", "B-opencv"),
            "D_minus_C": diff("D-tta", "C-mobile-sam"),
            "E_minus_D": diff("E-mirror", "D-tta"),
        }
    pass_flags = {a: selected_rows[a]["all_parts_pass"] for a in ASSETS}
    assert not any(pass_flags.values())
    statuses = {
        "asset_01_automatic_segmentation": "fail",
        "asset_02_automatic_segmentation": "fail",
        "AI_effect": "mixed; benefit on asset-01 right hair and asset-02 skirt, severe asset-01 left-hair loss",
        "TTA_effect": "mixed; asset-01 left improves and right falls below 0.90; asset-02 skirt improves marginally",
        "mirror_shape_effect": "not selected; asset-01 hair degrades and asset-02 hair gains remain below 0.90",
        "hidden_completion_quality": "not_run_after_segmentation_failure",
        "automatic_rigging_and_deformation": "not_run_after_segmentation_failure",
        "StandRig_GUI_with_008_model": "not_run_after_segmentation_failure",
        "user_video_quality_approval": "not_reviewed_no_008_animation",
    }
    first = ROOT / "predictions" / "asset-02"
    generalization = {
        "type": "first post-freeze application of the same pipeline to publicly accessible asset-02",
        "freeze_commit": FREEZE, "selected_method": selected, "asset_02_specific_adjustments": 0,
        "first_run_status": "fail", "threshold_for_each_target": .90,
        "first_run_part_iou": {p: selected_rows["asset-02"]["parts"][p]["iou"] for p in PARTS},
        "all_six_pass": False, "method_scores": {m: {p: row["parts"][p]["iou"] for p in PARTS}
                                               for m, row in assets["asset-02"]["methods"].items()},
        "after_holdout_tuning": "none",
        "excluded_assisted_baseline": "007 assisted path was not reached after assertion on source SHA-256",
        "result_sha256": {str(p.relative_to(ROOT)): digest(p) for p in sorted(first.rglob("*")) if p.is_file()},
        "timeline": "logs/asset-02-freeze-check.log", "details": "logs/metrics-asset-02.json",
    }
    auto = {
        "selected_method": selected, "formal_status": "fail",
        "automatic_steps": ["background and subject detection", "Lab palette seed selection", "connected components",
                            "root and centerline estimates", "GrabCut and stroke recovery", "AI prompt generation",
                            "MobileSAM inference", "reflected inference and label restoration",
                            "hair width-based mirror trial", "independent metrics",
                            "diagnostic overlay, error images and comparison videos"],
        "manual_inference_interventions": {
            a: {name: row["run"]["manual_interventions"] for name, row in assets[a]["methods"].items()}
            for a in ASSETS},
        "manual_pair_of_cut_lines": "A-007-assisted only; historic asset-01 root rows 538 and 452",
        "model_development": "Human-designed shared features and tuning on asset-01; no manual per-image prediction configuration.",
        "gate": "Six individual IoUs at or above 0.90.",
        "downstream": {k: v for k, v in statuses.items() if k in (
            "hidden_completion_quality", "automatic_rigging_and_deformation",
            "StandRig_GUI_with_008_model", "user_video_quality_approval")},
    }
    manifest = {
        "experiment": "008-segmentation-accuracy", "start_utc": "2026-11-20T07:04:00Z",
        "execution_approval": "2026-11-20 JST", "repository": "keepholdingon1224-source/StandRig",
        "branch": "experiment/rigging-validation-20261115", "initial_remote_sha": START,
        "start_worktree": "clean isolated checkout; original local work branch remained separate",
        "code_freeze": FREEZE, "frozen_reference_source": "ca383315a73c0f5e0621f15b9a943d6b67f87d23",
        "frozen_reference_approval": "b41bfa774a39629f1ed92f9a9e706103336f1d82",
        "inputs": {a: {"source": f"source_{i+7:03}/original.png", "dimensions": [1152, 2048],
                       "sha256": before["references"][a]["saved_png_checks"]["original_sha256"],
                       "reference": f"reference/{a}", "role": "development" if i == 0 else "held-out"}
                   for i, a in enumerate(ASSETS)},
        "environment": {"system": platform.system(), "architecture": platform.machine(),
                        "python": platform.python_version(), "python_executable": Path(sys.executable).name,
                        "python_package_list": "logs/python-packages.txt", "node": output("node", "-v"),
                        "npm": output("npm", "-v"), "ffmpeg": output("ffmpeg", "-version").splitlines()[0],
                        "chromium": output("chromium", "--version"),
                        "compute": "3 CPU threads for 008 segmentation, MobileSAM CPU PyTorch"},
        "external_paid_apis": 0, "additional_cost": 0,
        "prediction_inputs": "B–E process only the original PNG and pinned code/model; A uses original legacy script and hash guard.",
        "preflight_access": "Both source PNGs and reference sets read for original SHA-256 and saved PNG consistency; no asset-02 visual inspection or reference data used for model selection.",
        "development_access": ["source_007/original.png", "experiments/007-segment.py",
                               "frozen asset-01 masks and landmarks via separate evaluator",
                               "pre-existing 007 artifact copies for regression", "pinned public MobileSAM"],
        "asset_02_first_application": ["source_008/original.png passed to frozen B–E and A commands",
                                      "reference/asset-02 passed only to frozen evaluation after prediction"],
        "commands": "README.md#再現コマンド",
    }
    write(ROOT / "model-selection.json", model)
    write(ROOT / "verification.json", verification)
    write(ROOT / "generalization-report.json", generalization)
    write(ROOT / "automation-report.json", auto)
    write(ROOT / "manifest.json", manifest)
    write(ROOT / "metrics.json", {"threshold": .90, "formal_iou_includes_uncertain": True,
                                  "selected_method": selected, "formal_all_six_pass": False,
                                  "assets": assets, "deltas": deltas, "stage_status": statuses})
    write(ROOT / "completion" / "status.json", {"status": "not_run", "reason": statuses["hidden_completion_quality"]})
    write(ROOT / "model" / "status.json", {"status": "not_run", "reason": statuses["automatic_rigging_and_deformation"],
                                          "007_regression_results": "../logs/regression-007-verification.json"})
    for asset, m in assets.items():
        for method in METHODS:
            if method in m["methods"] and m["methods"][method]["run"].get("stderr"):
                (LOGS / f"{asset}-{method}-stderr.txt").write_text(m["methods"][method]["run"]["stderr"])


if __name__ == "__main__":
    main()
