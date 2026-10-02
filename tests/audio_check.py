"""Check the actual encoded soundtrack with FFmpeg; no Python dependencies.

Usage: python3 tests/audio_check.py [path/to/paged-attention.mp4]
"""
import json
import ast
import hashlib
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "docs/assets"
movie = Path(sys.argv[1]) if len(sys.argv) > 1 else ASSETS / "paged-attention.mp4"


def command(*args):
    return subprocess.run(args, check=True, capture_output=True, text=True)


def mean_volume(start, duration):
    result = command("ffmpeg", "-hide_banner", "-ss", str(start), "-i", str(movie),
                     "-t", str(duration), "-vn", "-af", "volumedetect", "-f", "null", "-")
    return float(re.search(r"mean_volume: ([-\d.]+) dB", result.stderr)[1])


metadata = json.loads(command("ffprobe", "-v", "error", "-show_streams", "-of", "json", str(movie)).stdout)
audio = [s for s in metadata["streams"] if s["codec_type"] == "audio"]
video = [s for s in metadata["streams"] if s["codec_type"] == "video"]
assert len(audio) == len(video) == 1, metadata
assert audio[0]["codec_name"] == "aac" and audio[0]["channels"] == 2, audio
assert audio[0]["sample_rate"] == "48000", audio
assert video[0]["width"] == 1920 and video[0]["height"] == 1080, video
assert video[0]["r_frame_rate"] == "60/1", video
assert abs(float(audio[0]["duration"]) - float(video[0]["duration"])) < .06

report = json.loads((ASSETS / "soundtrack.json").read_text())
captions = json.loads((ASSETS / "transcript.json").read_text())
script = json.loads((ROOT / "audio/narration.json").read_text())
visual = json.loads((ASSETS / "visual-cues.json").read_text())
chapters = json.loads((ASSETS / "chapters.json").read_text())
assert len(report["speech"]) == len(captions) == len(script["cues"]) == len(visual) == 20
scene_source = ast.parse((ROOT / "scenes/paged_attention.py").read_text())
caption_calls = sorted((node for node in ast.walk(scene_source)
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    and node.func.attr == "caption"), key=lambda node: node.lineno)
assert [ast.literal_eval(node.args[0]) for node in caption_calls] == list(range(20)), "Manim must use every shared cue exactly once."
assert [c["text"] for c in visual] == script["cues"], "Rendered text differs from narration script."
levels = []
previous_end = 0
for speech, caption, text, scene in zip(report["speech"], captions, script["cues"], visual):
    assert caption["text"] == speech["text"] == scene["text"] == text, "Narration, video, and captions must be verbatim."
    assert (ROOT / speech["source"]).is_file()
    cache_key = json.dumps([report["engine"].replace(" ", "-"), script["voice"], script["rate"], text])
    assert Path(speech["source"]).stem == hashlib.sha256(cache_key.encode()).hexdigest()[:16], "Voice clip was generated from different text."
    assert previous_end <= speech["start"] < speech["end"] <= scene["end"]
    assert scene["start"] <= speech["start"]
    assert caption["start"] == speech["start"] and caption["end"] >= speech["end"]
    assert speech["tempo"] == 1, "Extend the scene hold instead of speeding up or shortening narration."
    assert abs(speech["start"] - scene["start"] - script["speech_lead"]) < .002
    assert scene["end"] - speech["end"] >= script["end_pause"] - .025
    level = mean_volume(speech["start"], speech["end"] - speech["start"])
    assert -29 < level < -11, f"Missing or unbalanced speech cue: {speech}, {level} dB"
    levels.append(level)
    previous_end = speech["end"]
for chapter in chapters:
    assert mean_volume(chapter["start"] + .13, .65) > -56, "Missing chapter sound effect"

result = command("ffmpeg", "-hide_banner", "-i", str(movie), "-vn", "-af",
                 "loudnorm=I=-16:TP=-1.5:LRA=7:print_format=json", "-f", "null", "-").stderr
loudness = json.loads(result[result.rfind("{"):result.rfind("}") + 1])
assert -17.2 <= float(loudness["input_i"]) <= -14.8, loudness
assert float(loudness["input_tp"]) <= -.9, loudness
assert abs(report["loudness_lufs"] - float(loudness["input_i"])) < .2
print(f"PASS: 20 verbatim on-screen/speech/caption cues at natural speed, six chapter chimes, stereo AAC at 48 kHz, "
      f"1080p/60 video; {loudness['input_i']} LUFS, {loudness['input_tp']} dBTP; "
      f"speech levels {min(levels):.1f} to {max(levels):.1f} dB.")
