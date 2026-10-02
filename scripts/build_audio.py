#!/usr/bin/env python3
"""Synthesize/cache narration, design quiet effects, and mux a timed stereo mix.

Voice clips are checked in, so --offline rebuilds without a speech service.
Manim reads this same script and holds each caption until the full speech finishes.
"""
import argparse
import asyncio
import hashlib
import json
import os
import subprocess
from pathlib import Path

import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, sosfilt

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "docs/assets"
WORK = ROOT / "media/audio"
CACHE = ROOT / "audio/voice"
RATE = 48000


def run(*args, **kwargs):
    return subprocess.run(args, check=True, capture_output=True, **kwargs)


def probe(path):
    return json.loads(run("ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)).stdout)


def clip_path(text, spec):
    key = json.dumps(["edge-tts-7.2.8", spec["voice"], spec["rate"], text])
    return CACHE / f"{hashlib.sha256(key.encode()).hexdigest()[:16]}.mp3"


async def generate(spec, offline):
    import edge_tts
    semaphore = asyncio.Semaphore(3)
    proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")

    async def one(index, text):
        path = clip_path(text, spec)
        if path.exists() and path.stat().st_size > 1000:
            return
        if offline:
            raise RuntimeError(f"Missing cached voice for cue {index + 1}; run without --offline once.")
        async with semaphore:
            temporary = path.with_suffix(".part.mp3")
            for attempt in range(3):
                try:
                    voice = edge_tts.Communicate(text, spec["voice"], rate=spec["rate"], proxy=proxy)
                    await asyncio.wait_for(voice.save(str(temporary)), timeout=45)
                    probe(temporary)
                    temporary.replace(path)
                    print(f"Synthesized narration {index + 1:02d}/{len(spec['cues'])}", flush=True)
                    return
                except Exception:
                    temporary.unlink(missing_ok=True)
                    if attempt == 2:
                        raise
                    await asyncio.sleep(1 + attempt)
    await asyncio.gather(*(one(i, text) for i, text in enumerate(spec["cues"])))


def decode(path):
    return np.frombuffer(run("ffmpeg", "-v", "error", "-i", str(path), "-f", "f32le", "-ac", "1", "-ar", str(RATE), "-").stdout, dtype="<f4").copy()


def trim_silence(samples):
    # Retain breath/consonant margins around the audible speech, and all internal pauses.
    block = RATE // 100
    count = len(samples) // block
    rms = np.sqrt(np.mean(samples[:count * block].reshape(count, block) ** 2, axis=1))
    active = np.flatnonzero(rms > max(0.001, float(rms.max()) * 0.018))
    if not len(active):
        raise ValueError("Speech clip is silent")
    start = max(0, int(active[0] * block - RATE * 0.07))
    end = min(len(samples), int((active[-1] + 1) * block + RATE * 0.12))
    return samples[start:end]


def measure_loudness(path, target=-16):
    result = run("ffmpeg", "-hide_banner", "-i", str(path), "-af",
                 f"loudnorm=I={target}:TP=-1.5:LRA=7:print_format=json", "-f", "null", "-")
    output = result.stderr.decode()
    return json.loads(output[output.rfind("{"):output.rfind("}") + 1])


def normalize(source, destination, target):
    measured = measure_loudness(source, target)
    values = ":".join(f"measured_{key}={measured[value]}" for key, value in [
        ("I", "input_i"), ("TP", "input_tp"), ("LRA", "input_lra"), ("thresh", "input_thresh")])
    run("ffmpeg", "-y", "-v", "error", "-i", str(source), "-af",
        f"loudnorm=I={target}:TP=-1.5:LRA=7:{values}:offset={measured['target_offset']}:linear=true",
        "-ar", str(RATE), "-c:a", "pcm_f32le", str(destination))


def effect(kind, seed):
    durations = {"tick": .11, "write": .19, "allocate": .38, "resolve": .5,
                 "copy": 1.35, "release": .75, "trace": .95, "chapter": .65}
    duration = durations[kind]
    t = np.arange(round(duration * RATE)) / RATE
    edge = np.minimum(t / .008, 1) * np.minimum((duration - t) / .035, 1)
    if kind in ["copy", "trace", "release"]:
        rng = np.random.default_rng(seed)
        noise = sosfilt(butter(2, [600, 2800], btype="bandpass", fs=RATE, output="sos"), rng.normal(size=len(t)))
        noise /= max(1.0, float(np.abs(noise).max()))
        start, end = (580, 260) if kind == "release" else (280, 580)
        phase = 2 * np.pi * (start * t + (end - start) * t * t / (2 * duration))
        waveform = (.65 * noise + .15 * np.sin(phase)) * np.sin(np.pi * t / duration) ** 2
        amplitude = .034
    else:
        frequency = {"tick": 720, "write": 620, "allocate": 440, "resolve": 523.25, "chapter": 293.66}[kind]
        waveform = (np.sin(2 * np.pi * frequency * t) + .28 * np.sin(2 * np.pi * frequency * 1.5 * t))
        waveform *= np.exp(-t / (duration * .24))
        if kind in ["allocate", "chapter"]:
            delayed = np.maximum(0, t - .12)
            waveform += .55 * np.sin(2 * np.pi * frequency * 1.5 * delayed) * np.exp(-delayed / .11) * (t > .12)
        amplitude = .045 if kind == "chapter" else .038
    return (waveform * edge * amplitude).astype(np.float32)


def stamp(seconds):
    ms = round(seconds * 1000)
    return f"{ms // 3600000:02}:{ms // 60000 % 60:02}:{ms // 1000 % 60:02}.{ms % 1000:03}"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--offline", action="store_true", help="Use checked-in speech clips; never request synthesis.")
    parser.add_argument("--prepare-only", action="store_true", help="Synthesize and measure the shared script before Manim renders.")
    args = parser.parse_args()
    WORK.mkdir(parents=True, exist_ok=True)
    CACHE.mkdir(parents=True, exist_ok=True)
    spec = json.loads((ROOT / "audio/narration.json").read_text())
    asyncio.run(generate(spec, args.offline))
    clips = [trim_silence(decode(clip_path(text, spec))) for text in spec["cues"]]
    prepared = {"voice": spec["voice"], "rate": spec["rate"], "cues": [
        {"text": text, "duration": len(samples) / RATE}
        for text, samples in zip(spec["cues"], clips)
    ]}
    (WORK / "narration-timing.json").write_text(json.dumps(prepared, indent=2) + "\n")
    if args.prepare_only:
        print(f"Prepared {len(clips)} verbatim speech clips for Manim timing.")
        return
    visual = json.loads((ASSETS / "visual-cues.json").read_text())
    chapters = json.loads((ASSETS / "chapters.json").read_text())
    assert spec["cues"] == [c["text"] for c in visual], "Voice and on-screen text differ; re-render from the shared script."
    movie = ASSETS / "paged-attention.mp4"
    duration = float(probe(movie)["format"]["duration"])
    narration = np.zeros(round(duration * RATE), dtype=np.float32)
    captions, speech = [], []
    for index, (text, cue, samples) in enumerate(zip(spec["cues"], visual, clips)):
        available = cue["end"] - cue["start"] - spec["speech_lead"] - spec["end_pause"]
        if len(samples) / RATE > available + .025:
            raise ValueError(f"Cue {index + 1} needs a longer visual hold. Run scripts/render.py; do not shorten the speech independently.")
        # Tiny edge fades prevent cuts from creating clicks.
        fade = min(round(.008 * RATE), len(samples) // 2)
        samples[:fade] *= np.linspace(0, 1, fade)
        samples[-fade:] *= np.linspace(1, 0, fade)
        start = cue["start"] + spec["speech_lead"]
        end = start + len(samples) / RATE
        assert end <= cue["end"] - spec["end_pause"] + .025, f"Cue {index + 1} runs into the next visual."
        offset = round(start * RATE)
        narration[offset:offset + len(samples)] += samples
        captions.append({"start": round(start, 3), "end": round(end + .08, 3), "text": text})
        speech.append({"cue": index, "start": round(start, 3), "end": round(end, 3),
                       "text": text, "tempo": 1.0, "source": str(clip_path(text, spec).relative_to(ROOT))})
        print(f"Cue {index + 1:02d}: {start:.2f}–{end:.2f}s; verbatim at natural speed", flush=True)
    wavfile.write(WORK / "narration-raw.wav", RATE, narration)
    normalize(WORK / "narration-raw.wav", WORK / "narration.wav", -18)
    _, narration = wavfile.read(WORK / "narration.wav")
    narration = narration[:round(duration * RATE)]
    effects = np.zeros((len(narration), 2), dtype=np.float32)
    events = [{**item, "time": visual[item["cue"]]["start"] + item["offset"]} for item in spec["effects"]]
    events += [{"kind": "chapter", "time": c["start"] + .13, "pan": 0} for c in chapters]
    # Duck effects under speech using a smooth amplitude envelope.
    blocks = len(narration) // 480
    rms = np.sqrt(np.mean(narration[:blocks * 480].reshape(blocks, 480) ** 2, axis=1))
    smooth = np.convolve(rms, np.ones(9) / 9, mode="same")
    envelope = np.interp(np.arange(len(narration)) / 480, np.arange(blocks), smooth)
    duck = 1 - .58 * np.clip(envelope / .04, 0, 1)
    for index, event in enumerate(events):
        sound = effect(event["kind"], index)
        offset = round(event["time"] * RATE)
        length = min(len(sound), len(effects) - offset)
        assert length > 0
        angle = (event["pan"] + 1) * np.pi / 4
        gains = np.array([np.cos(angle), np.sin(angle)])
        effects[offset:offset + length] += sound[:length, None] * gains * duck[offset:offset + length, None]
    wavfile.write(WORK / "effects.wav", RATE, effects)
    mix = narration[:, None] * np.ones((1, 2), dtype=np.float32) + effects
    wavfile.write(WORK / "mix-raw.wav", RATE, mix.astype(np.float32))
    normalize(WORK / "mix-raw.wav", WORK / "mix.wav", -16)
    temporary = WORK / "paged-attention-narrated.mp4"
    run("ffmpeg", "-y", "-v", "error", "-i", str(movie), "-i", str(WORK / "mix.wav"),
        "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
        "-ar", str(RATE), "-ac", "2", "-t", str(duration), "-movflags", "+faststart",
        "-metadata:s:a:0", "language=eng", "-metadata:s:a:0", "title=English narration and original sound effects", str(temporary))
    loudness = measure_loudness(temporary)
    assert -17.2 <= float(loudness["input_i"]) <= -14.8, loudness
    assert float(loudness["input_tp"]) <= -.9, loudness
    temporary.replace(movie)
    (ASSETS / "transcript.json").write_text(json.dumps(captions, indent=2) + "\n")
    (ASSETS / "captions.vtt").write_text("WEBVTT\n\n" + "\n\n".join(
        f"{stamp(c['start'])} --> {stamp(c['end'])}\n{c['text']}" for c in captions) + "\n")
    report = {"voice": spec["voice"], "rate": spec["rate"], "engine": "edge-tts 7.2.8",
              "duration": duration, "sample_rate": RATE, "channels": 2,
              "loudness_lufs": float(loudness["input_i"]), "true_peak_dbtp": float(loudness["input_tp"]),
              "speech": speech, "effects": events,
              "sound_design": "Original synthesized ticks, writes, allocation tones, copy sweeps, releases, and chapter chimes; ducked below speech."}
    (ASSETS / "soundtrack.json").write_text(json.dumps(report, indent=2) + "\n")
    print(f"Mixed {len(speech)} narration cues and {len(events)} effects: {report['loudness_lufs']} LUFS, {report['true_peak_dbtp']} dBTP.")


if __name__ == "__main__":
    main()
