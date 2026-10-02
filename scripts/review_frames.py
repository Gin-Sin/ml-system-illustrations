#!/usr/bin/env python3
"""Extract authored review moments and make a contact sheet for visual QA."""
import argparse
import json
from pathlib import Path
import subprocess

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--quality", choices=["l", "h"], default="h")
    args = parser.parse_args()
    resolution = "480p30" if args.quality == "l" else "1080p60"
    target = ROOT / "test-results/frames"
    target.mkdir(parents=True, exist_ok=True)
    frames = []
    names = ["KVCache", "Fragmentation", "BlockMapping", "Attention", "Allocation", "Sharing"]
    for name in names:
        data = json.loads((ROOT / f"media/timings/{name}.json").read_text())
        for moment in data["review_frames"]:
            image = target / f"{moment['name']}.png"
            subprocess.run([
                "ffmpeg", "-y", "-v", "error", "-ss", str(moment["time"]+.1),
                "-i", str(ROOT / f"media/videos/paged_attention/{resolution}/{name}.mp4"),
                "-frames:v", "1", "-update", "1", str(image),
            ], check=True)
            frames.append((moment["name"], Image.open(image).convert("RGB").resize((960, 540))))
    sheet = Image.new("RGB", (1920, ((len(frames)+1)//2)*570), "#151515")
    draw = ImageDraw.Draw(sheet)
    for i,(name,frame) in enumerate(frames):
        x, y = (i%2)*960, (i//2)*570
        draw.text((x+15,y+8),name,fill="white")
        sheet.paste(frame,(x,y+30))
    sheet.save(target / "contact-sheet.jpg")
    print(target / "contact-sheet.jpg")


if __name__ == "__main__":
    main()
