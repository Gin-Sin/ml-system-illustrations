#!/usr/bin/env python3
"""Render chapters, concatenate web video, export captions and chapter metadata."""
import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHAPTERS = ["KVCache", "Fragmentation", "BlockMapping", "Attention", "Allocation", "Sharing"]


def run(*args):
    subprocess.run(args, cwd=ROOT, check=True)


def stamp(seconds):
    ms = round(seconds * 1000)
    return f"{ms//3600000:02}:{ms//60000%60:02}:{ms//1000%60:02}.{ms%1000:03}"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--quality", choices=["l", "m", "h"], default="h")
    parser.add_argument("--assemble-only", action="store_true")
    args = parser.parse_args()
    if not args.assemble_only:
        run(sys.executable, "-m", "manim", f"-q{args.quality}", "--fps", "30",
            "scenes/paged_attention.py", *CHAPTERS)
    folder = ROOT / "media/videos/paged_attention" / {"l":"480p30","m":"720p30","h":"1080p30"}[args.quality]
    concat = ROOT / "media/concat.txt"
    concat.write_text("".join(f"file '{folder / (name + '.mp4')}'\n" for name in CHAPTERS))
    assets = ROOT / "docs/assets"
    assets.mkdir(parents=True, exist_ok=True)
    run("ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", str(concat),
        "-c:v", "libx264", "-preset", "slow", "-crf", "20", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
        "-an", str(assets / "paged-attention.mp4"))
    chapters, cues, offset = [], [], 0.0
    for name in CHAPTERS:
        data = json.loads((ROOT / f"media/timings/{name}.json").read_text())
        duration = float(subprocess.check_output(["ffprobe","-v","error","-show_entries","format=duration",
                                                  "-of","default=nw=1:nk=1",str(folder / f"{name}.mp4")]))
        chapters.append({"title": data["title"], "start": round(offset,3), "duration": duration})
        for cue in data["cues"]:
            cues.append({"start":cue["start"]+offset,"end":min(cue["end"],duration)+offset,"text":cue["text"]})
        offset += duration
    (assets / "chapters.json").write_text(json.dumps(chapters, indent=2)+"\n")
    (assets / "captions.vtt").write_text("WEBVTT\n\n"+"\n\n".join(
        f"{stamp(c['start'])} --> {stamp(c['end'])}\n{c['text']}" for c in cues)+"\n")
    (assets / "transcript.json").write_text(json.dumps(cues,indent=2)+"\n")
    run("ffmpeg","-y","-v","error","-ss",str(chapters[2]["start"]+10),"-i",str(assets / "paged-attention.mp4"),
        "-frames:v","1","-update","1",str(assets / "poster.jpg"))
    print(f"Built {offset:.1f}s video, {len(chapters)} chapters, and {len(cues)} captions.")


if __name__ == "__main__":
    main()
