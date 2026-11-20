"""Verify the v4 reference and apply only the four pinned ERRATA corrections."""
import argparse
import importlib.util
import json
from pathlib import Path
import re

legacy_spec = importlib.util.spec_from_file_location(
    "verify_008", Path(__file__).with_name("008-verify-reference.py")
)
legacy = importlib.util.module_from_spec(legacy_spec)
legacy_spec.loader.exec_module(legacy)

APPROVAL = "b41bfa774a39629f1ed92f9a9e706103336f1d82"
ERRATA = "788367477ba721657701243d4795de8c5c52dea2"


def verify():
    result = legacy.verify()
    freeze_path = legacy.REFERENCE / "REVIEW-AND-FREEZE.md"
    errata_path = legacy.REFERENCE / "ERRATA-20261120.md"
    if freeze_path.read_bytes() != legacy.git("show", f"{APPROVAL}:{freeze_path}"):
        raise ValueError("Freeze record differs from approval")
    if errata_path.read_bytes() != legacy.git("show", f"{ERRATA}:{errata_path}"):
        raise ValueError("ERRATA differs from its approved commit")
    corrections = {
        path: (old, new)
        for path, old, new in re.findall(
            r"\| (asset-0[12]/[^|]+?) \| `([0-9a-f]{64})` \| `([0-9a-f]{64})` \|",
            errata_path.read_text(),
        )
    }
    expected_paths = {
        f"{asset}/{name}"
        for asset in ("asset-01", "asset-02")
        for name in ("manifest.json", "annotation-notes.md")
    }
    if corrections.keys() != expected_paths:
        raise ValueError("Unexpected correction scope")
    result["errata_corrections"] = {}
    for path, (old, new) in corrections.items():
        asset, name = path.split("/")
        row = result["references"][asset]
        actual = row["frozen_sha256_mismatches"].get(name)
        if actual != {"expected": old, "actual": new}:
            raise ValueError(f"ERRATA correction did not match actual evidence: {path}")
        document = legacy.REFERENCE / path
        for revision in (legacy.BASE, APPROVAL):
            if document.read_bytes() != legacy.git("show", f"{revision}:{document}"):
                raise ValueError(f"Document differs from {revision}: {path}")
        result["errata_corrections"][path] = row["frozen_sha256_mismatches"].pop(name)
    result["passed"] = not result["frozen_input_changes"] and len(result["references"]) == 2 and all(
        row["returncode"] == 0
        and row["original_dimensions_match"]
        and not row["frozen_sha256_mismatches"]
        and len(row["png_8bit_grayscale_binary"]) == 8
        and all(row["png_8bit_grayscale_binary"].values())
        and row["saved_png_checks"].get("all_checks_passed")
        for row in result["references"].values()
    )
    paths = legacy.git("ls-files", "-z", "--", "source_007", "source_008",
                       ":(glob)experiments/008-*", ":(glob)results/008-*/**").decode().split("\0")
    result["protected_sha256"].update(
        {path: legacy.digest(Path(path)) for path in paths if path}
    )
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    args = parser.parse_args()
    report = verify()
    args.report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(f"v4 gate: {report['passed']}; {len(report['protected_sha256'])} protected files")
    raise SystemExit(0 if report["passed"] else 1)
