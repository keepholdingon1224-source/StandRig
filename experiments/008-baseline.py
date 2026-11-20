"""Execute 007 unmodified in an isolated working directory."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import resource
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory
from time import perf_counter

import cv2 as cv
import numpy as np


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    code = Path("experiments/007-segment.py").resolve()
    args.output.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix="008-007-baseline-") as scratch:
        root = Path(scratch)
        (root / "source_007").mkdir()
        shutil.copyfile(args.source, root / "source_007/original.png")
        original_out = root / "results/007-character-application"
        (original_out / "segmentation").mkdir(parents=True)
        (original_out / "source").mkdir()
        (original_out / "reconstruction").mkdir()
        start = perf_counter()
        # Capturing the script namespace in its exception handler preserves the
        # intermediate role masks if execution aborts before writing any PNG.
        diagnostics = """
import sys
import cv2 as cv
import numpy as np
source = sys.argv[1]
namespace = {"__name__": "__main__", "__file__": source}
try:
    exec(compile(open(source, "rb").read(), source, "exec"), namespace)
except Exception:
    from pathlib import Path
    if "skirt_core" in namespace:
        cv.imwrite("skirt-core-intermediate.png", namespace["skirt_core"].astype("uint8") * 255)
    for name, mask in namespace.get("masks", {}).items():
        cv.imwrite(f"{name}-intermediate.png", mask.astype("uint8") * 255)
    raise
"""
        run = subprocess.run([sys.executable, "-c", diagnostics, str(code)], cwd=root,
                             capture_output=True, text=True)
        elapsed = perf_counter() - start
        image = cv.imread(os.fspath(args.source))
        roles = {"left": "hair-left", "right": "hair-right", "skirt": "skirt",
                 "fixed": "fixed", "background": "background"}
        modes = [("A-007-auto", original_out / "segmentation", 0)]
        assist = original_out / "segmentation/assisted"
        if assist.exists():
            modes.append(("A-007-assisted", assist, 2))
        for method, directory, manual in modes:
            out = args.output / method
            out.mkdir(exist_ok=True)
            unavailable, intermediate = [], []
            for old, new in roles.items():
                path = directory / f"{old}-binary.png"
                if not path.exists() and manual == 0:
                    recovered = root / f"{old}-intermediate.png"
                    if old == "skirt" and not recovered.exists():
                        recovered = root / "skirt-core-intermediate.png"
                    if recovered.exists():
                        path = recovered
                        intermediate.append(new)
                if path.exists():
                    shutil.copyfile(path, out / f"{new}.png")
                else:
                    unavailable.append(new)
                    cv.imwrite(str(out / f"{new}.png"), np.zeros(image.shape[:2], dtype="uint8"))
            report = {"returncode": run.returncode, "stdout": run.stdout, "stderr": run.stderr,
                      "script_sha256": hashlib.sha256(code.read_bytes()).hexdigest(),
                      "total_replay_seconds": elapsed, "manual_interventions": manual,
                      "unavailable_roles_zero_filled_for_scoring": unavailable,
                      "recovered_intermediate_roles": intermediate,
                      "peak_child_rss_kib": resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss}
            geometry = directory / "parts.json" if manual == 0 else original_out / "reconstruction/method.json"
            if geometry.exists():
                report["007_parameters_record"] = json.loads(geometry.read_text())
                report["seconds"] = report["007_parameters_record"].get(
                    "seconds" if manual == 0 else "processingSeconds")
            (out / "run.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
