"""Run the pinned official GPU pipeline and preserve layers, provenance and logs."""
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from time import perf_counter, sleep


CODE = "fc4440db7c076518e313f378e28b1504e9886a95"
REPOSITORIES = {
    "standard": ("layerdifforg/seethroughv0.0.2_layerdiff3d", "24yearsold/seethroughv0.0.1_marigold"),
    "nf4": ("24yearsold/seethroughv0.0.2_layerdiff3d_nf4", "24yearsold/seethroughv0.0.1_marigold_nf4"),
}


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def extract(psd_path, original, destination):
    import numpy as np
    from PIL import Image
    from psd_tools import PSDImage

    psd = PSDImage.open(psd_path)
    with Image.open(original) as source:
        width, height = source.size
    size = max(width, height)
    left, top = (size - width) // 2, (size - height) // 2
    crop = (left, top, left + width, top + height)
    if psd.width != psd.height or not len(psd):
        raise ValueError("Expected nonempty square PSD from official padded inference")
    visible_dir = destination / "semantic-visible"
    completed_dir = destination / "completed"
    visible_dir.mkdir()
    completed_dir.mkdir()
    occupied = np.zeros((height, width), dtype=bool)
    inventory = []
    # psd-tools iterates bottom to top. Assign each pixel to the frontmost alpha >= 128.
    for idx, layer in reversed(list(enumerate(psd))):
        if not layer.is_visible():
            continue
        layer_img = layer.topil()
        if layer_img is None:
            raise ValueError(f"Unreadable PSD layer {layer.name}")
        canvas = Image.new("RGBA", (psd.width, psd.height))
        canvas.paste(layer_img.convert("RGBA"), (layer.left, layer.top))
        aligned = canvas.resize((size, size), Image.Resampling.BILINEAR).crop(crop)
        name = f"{idx:02d}-{re.sub(r'[^a-zA-Z0-9_-]+', '-', layer.name)}.png"
        aligned.save(completed_dir / name)
        mask = np.asarray(aligned.getchannel("A")) >= 128
        visible = mask & ~occupied
        Image.fromarray(visible.astype(np.uint8) * 255).save(visible_dir / name)
        occupied |= mask
        inventory.append({"name": layer.name, "file": name, "bounds_in_psd": list(layer.bbox),
                          "visible_pixels": int(visible.sum()), "completed_pixels": int(mask.sum())})
    if not occupied.any():
        raise ValueError("No nontransparent semantic layers")
    return {"psd_size": [psd.width, psd.height], "original_size": [width, height],
            "resample_to_square": size, "crop": crop, "alpha_threshold": 128,
            "layers_front_to_back": inventory}


def run(args):
    import psutil
    import torch
    from huggingface_hub import snapshot_download

    code, source, output = (p.resolve() for p in (args.code, args.source, args.output))
    head = subprocess.check_output(["git", "-C", str(code), "rev-parse", "HEAD"], text=True).strip()
    changes = subprocess.check_output(["git", "-C", str(code), "status", "--porcelain",
                                       "--untracked-files=no"], text=True)
    if head != CODE or changes:
        raise ValueError("See-through tracked checkout must match the pinned commit")
    revisions = json.loads(args.revisions.read_text())
    repos = REPOSITORIES[args.mode]
    for repo in repos:
        if not re.fullmatch(r"[0-9a-f]{40}", revisions.get(repo, "")):
            raise ValueError(f"Supply reviewed immutable revision for {repo}")
    output.mkdir(parents=True, exist_ok=False)
    started = perf_counter()
    report = {"status": "started", "official_code": head, "source_sha256": digest(source),
              "models": {repo: revisions[repo] for repo in repos}, "mode": args.mode,
              "resolution": args.resolution, "depth_resolution": 768, "seed": 42,
              "torch": torch.__version__, "cuda": torch.version.cuda,
              "gpu": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
              "native_cuda_bf16": torch.cuda.is_available() and torch.cuda.is_bf16_supported(including_emulation=False),
              "group_offload": args.mode == "nf4" or args.group_offload,
              "cpu_offload_requested": args.cpu_offload,
              "system_ram_bytes": psutil.virtual_memory().total,
              "platform": sys.platform, "disk_free_bytes": shutil.disk_usage(output).free}
    report_path = output / "run.json"
    try:
        if not shutil.which("nvidia-smi"):
            raise RuntimeError("nvidia-smi unavailable")
        if not torch.cuda.is_available():
            raise RuntimeError("No CUDA GPU available")
        snapshots = [Path(snapshot_download(repo, revision=revisions[repo])) for repo in repos]
        report["model_file_sha256"] = {
            repo: {str(p.relative_to(snapshot)): digest(p) for p in sorted(snapshot.rglob("*")) if p.is_file()}
            for repo, snapshot in zip(repos, snapshots)
        }
        script = "inference_psd_quantized.py" if args.mode == "nf4" else "inference_psd.py"
        command = [sys.executable, f"inference/scripts/{script}", "--srcp", str(source),
                   "--save_dir", str(output), "--save_to_psd", "--seed", "42",
                   "--resolution", str(args.resolution), "--resolution_depth", "768",
                   "--repo_id_layerdiff", str(snapshots[0]), "--repo_id_depth", str(snapshots[1])]
        if args.mode == "standard" and args.group_offload:
            command.append("--group_offload")
        if args.cpu_offload:
            command.append("--cpu_offload")
        report["command"] = command
        with (output / "gpu-samples.csv").open("w") as gpu, (output / "inference.txt").open("w") as log:
            monitor = subprocess.Popen(["nvidia-smi", "--query-gpu=timestamp,index,name,driver_version,memory.total,memory.used,memory.free",
                                        "--format=csv", "-l", "1"], stdout=gpu, stderr=subprocess.STDOUT)
            try:
                inference_started = perf_counter()
                process = subprocess.Popen(command, cwd=code, env={**os.environ, "HF_HUB_OFFLINE": "1"},
                                           stdout=log, stderr=subprocess.STDOUT)
                target = psutil.Process(process.pid)
                peak = 0
                with (output / "ram-samples.csv").open("w") as ram:
                    ram.write("elapsed_seconds,process_tree_rss_bytes\n")
                    while process.poll() is None:
                        rss = 0
                        try:
                            children = target.children(recursive=True)
                        except psutil.NoSuchProcess:
                            break
                        for member in [target, *children]:
                            try:
                                rss += member.memory_info().rss
                            except psutil.NoSuchProcess:
                                continue
                        ram.write(f"{perf_counter() - inference_started:.3f},{rss}\n")
                        peak = max(peak, rss)
                        sleep(1)
                report["peak_sampled_process_tree_rss_bytes"] = peak
                if process.wait():
                    raise subprocess.CalledProcessError(process.returncode, command)
                report["inference_seconds"] = perf_counter() - inference_started
            finally:
                monitor.terminate()
                monitor.wait()
        per_gpu = {}
        with (output / "gpu-samples.csv").open(newline="") as samples:
            for row in csv.reader(samples):
                if len(row) == 7 and row[1].strip().isdigit():
                    index = row[1].strip()
                    used = row[5].strip().split()[0]
                    if used.isdigit():
                        per_gpu[index] = max(per_gpu.get(index, 0), int(used))
        report["peak_sampled_device_memory_mib_by_index"] = per_gpu
        report["output_geometry"] = extract(output / f"{source.stem}.psd", source, output)
        report["status"] = "layer_smoke_pass"
    except Exception as error:
        report["status"] = "failed"
        report["error"] = str(error)
        raise
    finally:
        report["elapsed_seconds"] = perf_counter() - started
        report_path.write_text(json.dumps(report, indent=2) + "\n")
        checksums = [f"{digest(p)}  {p.relative_to(output).as_posix()}" for p in sorted(output.rglob("*")) if p.is_file()]
        (output / "SHA256SUMS").write_text("\n".join(checksums) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("code", "source", "output", "revisions"):
        parser.add_argument(name, type=Path)
    parser.add_argument("--mode", choices=REPOSITORIES, default="standard")
    parser.add_argument("--resolution", type=int, choices=(1024, 1280), default=1280)
    parser.add_argument("--group-offload", action="store_true", help="Enable for standard mode; NF4 already enables it")
    parser.add_argument("--cpu-offload", action="store_true",
                        help="NF4 LayerDiff CPU offload; official NF4 Marigold uses group offload")
    args = parser.parse_args()
    if args.cpu_offload and args.mode != "nf4":
        parser.error("--cpu-offload is available in NF4 mode")
    run(args)
