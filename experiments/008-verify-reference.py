"""Read frozen inputs, run the original verifiers on copies, and pin protected files."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory

import numpy as np
from PIL import Image

RESULTS = Path("results/008-segmentation-accuracy")
REFERENCE = RESULTS / "reference"
BASE = "ca383315a73c0f5e0621f15b9a943d6b67f87d23"
PROTECTED = [
    str(REFERENCE), "source_007/original.png", "source_008/original.png",
    ":(glob)experiments/00[567]-*", ":(glob)results/00[567]-*/**",
]


def digest(path):
    return hashlib.file_digest(path.open("rb"), "sha256").hexdigest()


def git(*args):
    return subprocess.check_output(["git", *args])


def verify():
    record = (REFERENCE / "REVIEW-AND-FREEZE.md").read_text()
    changed = git("diff", "--name-only", BASE, "--", str(REFERENCE / "asset-01"),
                  str(REFERENCE / "asset-02"), *PROTECTED[1:3]).decode().splitlines()
    reports = {}
    with TemporaryDirectory(prefix="008-reference-") as temp:
        for index, section in enumerate(record.split("### asset-")[1:], start=1):
            asset = f"asset-{index:02}"
            original = Path(f"source_{index + 6:03}/original.png").resolve()
            expected = re.search(r"Original SHA-256: `([0-9a-f]{64})`", section)[1]
            hashes = dict(re.findall(r"\| ([^|]+?) \| `([0-9a-f]{64})` \|", section))
            source = REFERENCE / asset
            copy = Path(temp) / asset
            shutil.copytree(source, copy)
            command = [sys.executable, str(source / "verify-reference.py"), str(copy), str(original), expected]
            run = subprocess.run(command, capture_output=True, text=True)
            report_path = copy / "reference-verification.json"
            report = json.loads(report_path.read_text()) if run.returncode == 0 else {}
            png_checks = {}
            for name in sorted(hashes):
                if name.endswith(".png"):
                    path = copy / name
                    with Image.open(path) as image, path.open("rb") as stream:
                        header = stream.read(29)
                        png_checks[name] = (
                            image.format == "PNG" and image.size == (1152, 2048)
                            and image.mode == "L" and header[24:26] == bytes([8, 0])
                            and set(np.unique(np.asarray(image))).issubset({0, 255})
                        )
            mismatches = {name: {"expected": sha, "actual": digest(copy / name)}
                          for name, sha in hashes.items() if digest(copy / name) != sha}
            reports[asset] = {
                "command_template": ["python", str(source / "verify-reference.py"), "<temporary copy>",
                                     str(original.relative_to(Path.cwd())), expected],
                "returncode": run.returncode, "stdout": run.stdout, "stderr": run.stderr,
                "original_dimensions_match": Image.open(original).size == (1152, 2048),
                "frozen_sha256_mismatches": mismatches, "png_8bit_grayscale_binary": png_checks,
                "saved_png_checks": report,
            }
    paths = git("ls-files", "-z", "--", *PROTECTED).decode().rstrip("\0").split("\0")
    protected = {path: digest(Path(path)) for path in sorted(paths)}
    passed = not changed and len(reports) == 2 and all(
        row["original_dimensions_match"] and not row["frozen_sha256_mismatches"]
        and len(row["png_8bit_grayscale_binary"]) == 8 and all(row["png_8bit_grayscale_binary"].values())
        and row["saved_png_checks"].get("all_checks_passed") for row in reports.values())
    return {"passed": passed, "frozen_snapshot": BASE, "frozen_input_changes": changed,
            "references": reports, "protected_sha256": protected}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    args = parser.parse_args()
    result = verify()
    args.report.write_text(json.dumps(result, indent=2) + "\n")
    print(f"Reference gate: {result['passed']}; SHA-256 pinned for {len(result['protected_sha256'])} files")
    sys.exit(0 if result["passed"] else 1)
