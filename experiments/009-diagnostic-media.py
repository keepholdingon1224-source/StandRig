"""Render the saved asset-02 prompt ablation as two timed diagnostic views."""
import argparse
import json
from pathlib import Path
import subprocess

import numpy as np
from PIL import Image, ImageDraw, ImageFont


def render(source, reference, diagnostics, output):
    with Image.open(source) as image:
        original = np.asarray(image.convert("RGB"))
    font = ImageFont.load_default(size=31)
    for mode, variants in {
        "008-input": ("008-exact", "008-exact"),
        "reference-prompt": ("reference-box-sam-rank-uncut", "reference-points-box-008-rank-uncut"),
    }.items():
        image = original.copy()
        error = np.zeros_like(image)
        for part, variant in zip(("hair-left", "hair-right"), variants):
            with Image.open(reference / f"{part}.png") as mask:
                truth = np.asarray(mask) != 0
            with Image.open(diagnostics / f"{part}-{variant}.png") as mask:
                prediction = np.asarray(mask) != 0
            for region, color in ((prediction & truth, (52, 210, 147)),
                                  (prediction & ~truth, (255, 80, 84)),
                                  (truth & ~prediction, (60, 160, 255))):
                image[region] = np.rint(.45 * original[region] + .55 * np.array(color))
                error[region] = color
        panel = Image.fromarray(image)
        draw = ImageDraw.Draw(panel)
        draw.rectangle((0, 0, panel.width, 104), fill=(16, 20, 26))
        label = "008 inputs" if mode == "008-input" else "Reference prompts (diagnostic only)"
        draw.text((22, 12), label, font=font, fill="white")
        draw.text((22, 56), "Correct", font=font, fill=(52, 210, 147))
        draw.text((210, 56), "False positive", font=font, fill=(255, 80, 84))
        draw.text((495, 56), "Missed", font=font, fill=(60, 160, 255))
        panel.save(output / "overlays" / f"asset-02-{mode}.png")
        Image.fromarray(error).save(output / "errors" / f"asset-02-{mode}.png")
    video = output / "videos" / "asset-02-mobilesam-ablation.mp4"
    before, after = (str(output / "overlays" / f"asset-02-{mode}.png")
                     for mode in ("008-input", "reference-prompt"))
    subprocess.run(["ffmpeg", "-v", "error", "-n", "-loop", "1", "-framerate", "30", "-t", "4",
                    "-i", before, "-loop", "1", "-framerate", "30", "-t", "4", "-i", after,
                    "-filter_complex", "[0:v][1:v]concat=n=2:v=1:a=0[out]", "-map", "[out]",
                    "-c:v", "libx264", "-threads", "2", "-pix_fmt", "yuv420p",
                    "-movflags", "+faststart", str(video)], check=True)
    probe = subprocess.check_output(["ffprobe", "-v", "error", "-count_frames", "-show_entries",
                                    "stream=width,height,avg_frame_rate,nb_read_frames,duration",
                                    "-of", "json", str(video)])
    rows = json.loads(probe)["streams"]
    row, = rows
    if (row["width"], row["height"], row["avg_frame_rate"], int(row["nb_read_frames"]),
        float(row["duration"])) != (1152, 2048, "30/1", 240, 8):
        raise ValueError(row)
    subprocess.run(["ffmpeg", "-v", "error", "-xerror", "-threads", "2", "-i", str(video),
                    "-f", "null", "-"], check=True)
    (output / "logs" / "diagnostic-video-decode.json").write_text(json.dumps(row, indent=2) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("source", "reference", "diagnostics", "output"):
        parser.add_argument(name, type=Path)
    render(**vars(parser.parse_args()))
