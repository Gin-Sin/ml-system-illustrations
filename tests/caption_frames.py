"""OCR the actual video frames and compare burned-in narration with the shared script.

Requires FFmpeg and Tesseract with English language data.
Usage: python3 tests/caption_frames.py
"""
import json
import re
import subprocess
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "docs/assets"
OUT = ROOT / "test-results/captions"
OUT.mkdir(parents=True, exist_ok=True)
script = json.loads((ROOT / "audio/narration.json").read_text())["cues"]
speech = json.loads((ASSETS / "soundtrack.json").read_text())["speech"]


def words(text):
    # Font ligatures, punctuation, and line wrapping do not alter spoken words.
    return re.sub(r"[^a-z0-9]", "", unicodedata.normalize("NFKC", text).casefold())


for index, (text, cue) in enumerate(zip(script, speech)):
    frame = OUT / f"{index + 1:02d}.png"
    time = (cue["start"] + cue["end"]) / 2
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", str(time),
                    "-i", str(ASSETS / "paged-attention.mp4"), "-frames:v", "1",
                    "-vf", "crop=1880:130:20:940,negate,scale=2820:195", "-update", "1", str(frame)], check=True)
    result = subprocess.run(["tesseract", str(frame), "stdout", "-l", "eng", "--psm", "6"],
                            check=True, capture_output=True, text=True).stdout.strip()
    assert words(result) == words(text), f"Cue {index + 1}:\nVIDEO:  {result}\nSCRIPT: {text}"
    print(f"PASS frame {index + 1:02d}: burned-in text matches the spoken script", flush=True)
assert len(script) == len(speech) == 20
