"""Encode diagnostic comparison panels from saved overlays and error masks."""
import argparse
import json
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory

import numpy as np
from PIL import Image, ImageDraw, ImageFont

METHODS = ("A-007-auto", "A-007-assisted", "B-opencv", "C-mobile-sam", "D-tta", "E-mirror")
PARTS = ("hair-left", "hair-right", "skirt")
WIDTH, HEIGHT = 1152, 2048
FPS = 30
FRAMES = 240


def load(path):
    with Image.open(path) as im:
        return im.convert("RGB")


def panel(asset, method, values, original, results, closeup):
    background = Image.new("RGB", (WIDTH, HEIGHT), "#131923")
    draw = ImageDraw.Draw(background)
    title, caption = ImageFont.load_default(size=46), ImageFont.load_default(size=27)
    draw.text((36, 31), f"{asset}  /  {method}", font=title, fill="#f3f4f5")
    draw.text((36, 101), "IoU    " + "    ".join(
        f"{part} {values[part]['iou']:.4f}" for part in PARTS
    ), font=caption, fill="#d8e2f1")
    arrays = [np.asarray(load(results / "errors" / asset / method / f"{part}-pixels.png"))
              for part in PARTS]
    errors = Image.fromarray(np.maximum.reduce(arrays))
    overlay = load(results / "overlays" / asset / f"{method}.png")
    if closeup:
        roots_path = results / "reference" / asset / "landmarks.json"
        roots = json.loads(roots_path.read_text())
        centers = [roots[f"{part}-root"] for part in PARTS[:2]]
        crop = (max(0, min(p["x"] for p in centers)-145), max(0, min(p["y"] for p in centers)-110),
                min(WIDTH, max(p["x"] for p in centers)+145), min(HEIGHT, max(p["y"] for p in centers)+230))
        images = [(original.crop(crop), "Original / roots"), (overlay.crop(crop), "Prediction / roots"),
                  (errors.crop(crop), "Red: excess    Blue: missed")]
        positions = [(36, 161), (36, 777), (36, 1393)]
        size = (1080, 550)
    else:
        images = [(original, "Original"), (overlay, "Prediction overlay"),
                  (errors, "Red: excess    Blue: missed")]
        positions = [(36, 163), (596, 163), (326, 1090)]
        size = (520, 870)
    for (im, text), (x, y) in zip(images, positions):
        draw.text((x, y), text, font=caption, fill="#f3f4f5")
        im.thumbnail(size)
        background.paste(im, (x + (size[0]-im.width)//2, y+35))
    return background


def run(*args):
    return subprocess.run(args, check=True, capture_output=True, text=True).stdout


def check_video(path, frames):
    stream = json.loads(run("ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0",
                            "-show_streams", "-of", "json", str(path)))["streams"][0]
    run("ffmpeg", "-v", "error", "-xerror", "-threads", "2", "-i", str(path), "-f", "null", "-")
    if (stream["width"], stream["height"], int(stream["nb_read_frames"]), stream["avg_frame_rate"],
        float(stream["duration"])) != (WIDTH, HEIGHT, frames, "30/1", frames / FPS):
        raise ValueError(f"Unexpected decoded video metadata for {path}")
    return {"status": "pass", "frames": frames, "fps": FPS, "seconds": frames / FPS,
            "width": WIDTH, "height": HEIGHT}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("results", type=Path)
    args = parser.parse_args()
    results = args.results.resolve()
    out = results / "videos"
    out.mkdir(exist_ok=True)
    report = {}
    with TemporaryDirectory(prefix="008-comparison-") as temp:
        work = Path(temp)
        for version, closeup in (("comparison", False), ("roots-closeup", True)):
            for index in (1, 2):
                asset = f"asset-{index:02}"
                original = load(Path(f"source_{index + 6:03}/original.png"))
                metrics = json.loads((results / "logs" / f"metrics-{asset}.json").read_text())["methods"]
                methods = [m for m in METHODS if m in metrics]
                for slot, method in enumerate(methods):
                    path = work / f"slide-{slot:02}.png"
                    panel(asset, method, metrics[method]["parts"], original, results, closeup).save(path)
                dest = out / f"{asset}-{version}.mp4"
                run("ffmpeg", "-v", "error", "-y", "-framerate", f"{len(methods)}/8", "-start_number", "0",
                    "-i", str(work / "slide-%02d.png"), "-frames:v", str(FRAMES), "-vf", "fps=30",
                    "-c:v", "libx264", "-threads", "3", "-pix_fmt", "yuv420p",
                    "-movflags", "+faststart", str(dest))
                report[dest.name] = check_video(dest, FRAMES)
                for path in work.glob("slide-*.png"):
                    path.unlink()
        for index in (1, 2):
            asset = f"asset-{index:02}"
            dest = out / f"{asset}-comparison-three-cycles.mp4"
            run("ffmpeg", "-v", "error", "-y", "-stream_loop", "2", "-i",
                str(out / f"{asset}-comparison.mp4"), "-c", "copy", "-movflags", "+faststart", str(dest))
            report[dest.name] = check_video(dest, 3 * FRAMES)
    (results / "logs" / "diagnostic-video-decode.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
