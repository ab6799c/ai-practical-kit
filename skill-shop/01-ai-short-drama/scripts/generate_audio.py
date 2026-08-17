#!/usr/bin/env python3
"""generate_audio.py: TTS + SRT generation from scenes.json"""
import json, os, sys, wave, struct, subprocess, argparse, tempfile, shutil
from pathlib import Path
from datetime import timedelta

if sys.stdout.encoding and sys.stdout.encoding.upper() in ('GBK', 'GB2312', 'CP936'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

SR, CH, SW = 24000, 1, 2

# Locate ffmpeg
FFMPEG = shutil.which("ffmpeg")
if not FFMPEG:
    candidates = [
        "D:/NewProject/MoneyPrinterTurbo/.venv/Lib/site-packages/imageio_ffmpeg/binaries/ffmpeg-win-x86_64-v7.1.exe",
        "C:/Program Files/ffmpeg/bin/ffmpeg.exe",
        "C:/ffmpeg/bin/ffmpeg.exe",
    ]
    for c in candidates:
        if os.path.exists(c):
            FFMPEG = c
            break
if not FFMPEG:
    FFMPEG = "ffmpeg"  # fallback, will error with clear message


def parse_scenes(p):
    return json.loads(Path(p).read_text("utf-8"))


def srt_time(sec):
    td = timedelta(seconds=sec)
    h, m = td.seconds // 3600, (td.seconds % 3600) // 60
    s, ms = td.seconds % 60, int((sec - int(sec)) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def to_wav(src, dst):
    r = subprocess.run([FFMPEG, "-y", "-i", src, "-ar", str(SR), "-ac", "1",
                        "-sample_fmt", "s16", dst, "-loglevel", "error"],
                       capture_output=True, timeout=60)
    return r.returncode == 0 and os.path.exists(dst)


def wav_dur(wav):
    with wave.open(wav) as wf:
        return wf.getnframes() / wf.getframerate()


def tts_edge(text, out_wav):
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
        mp3 = tmp.name
    try:
        r = subprocess.run([sys.executable, "-m", "edge_tts",
                            "--voice", "zh-CN-XiaoxiaoNeural",
                            "--text", text, "--write-media", mp3],
                           capture_output=True, timeout=120)
        if r.returncode or not os.path.exists(mp3) or os.path.getsize(mp3) < 100:
            return 0
        return wav_dur(out_wav) if to_wav(mp3, out_wav) else 0
    finally:
        if os.path.exists(mp3):
            os.unlink(mp3)


def tts_sapi(text, out_wav):
    e = text.replace("'", "''").replace('"', '`')
    r = subprocess.run(["powershell", "-NoProfile", "-Command",
                        f"Add-Type -AssemblyName System.Speech;"
                        f"$s=New-Object System.Speech.Synthesis.SpeechSynthesizer;"
                        f"$s.SelectVoice('Microsoft Huihui Desktop');"
                        f"$s.SetOutputToWaveFile('{out_wav}');$s.Rate=2;$s.Speak('{e}');$s.Dispose()"],
                       capture_output=True, timeout=120)
    return wav_dur(out_wav) if r.returncode == 0 and os.path.exists(out_wav) else 0


ENGINES = {"edge": tts_edge, "sapi": tts_sapi}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenes", required=True)
    ap.add_argument("--out", "-o", default="novel_audio")
    ap.add_argument("--tts", default="edge", choices=["edge", "sapi"])
    a = ap.parse_args()

    data = parse_scenes(a.scenes)
    scenes = data["scenes"]
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    tmp = out / "_tts_tmp"
    tmp.mkdir(exist_ok=True)

    tts = ENGINES.get(a.tts, tts_edge)
    all_segs, cursor = [], 0.0

    for si, sc in enumerate(scenes):
        print(f"[{si+1}/{len(scenes)}] {sc.get('title', f'scene{si+1}')}")
        texts = [t for t in [sc.get("narration"), sc.get("dialogue")] if t]
        segs = []
        for ti, txt in enumerate(texts or ["..."]):
            txt = txt.strip()
            if len(txt) < 2:
                segs.append({"text": txt, "dur": 0.5, "start": cursor})
                cursor += 0.5
                continue
            wf = str(tmp / f"s{si:02d}_{ti:03d}.wav")
            d = tts(txt, wf)
            if d <= 0:
                d, wf = max(0.5, len(txt) / 4), None
            segs.append({"text": txt, "dur": d, "start": cursor, "file": wf})
            cursor += d
        all_segs.append(segs)

    # SRT
    lines, n = [], 1
    for segs in all_segs:
        for s in segs:
            if not s["text"].strip():
                continue
            end = s["start"] + s["dur"]
            lines += [str(n), f"{srt_time(s['start'])} --> {srt_time(end)}", s["text"], ""]
            n += 1
    (out / "字幕.srt").write_text("\n".join(lines), "utf-8")
    print(f"  SRT: {n-1} entries")

    # Merge audio
    total = int(cursor * SR) + SR
    audio = [0.0] * total
    for segs in all_segs:
        for s in segs:
            if not s.get("file") or not os.path.exists(s["file"]):
                continue
            try:
                with wave.open(s["file"]) as wf:
                    import array
                    d = array.array("h")
                    d.frombytes(wf.readframes(wf.getnframes()))
                    off = int(s["start"] * SR)
                    for j, v in enumerate(d):
                        idx = off + j
                        if idx < total:
                            audio[idx] += v
            except Exception:
                pass

    for f in tmp.glob("*.wav"):
        f.unlink()
    tmp.rmdir()

    pk = max(abs(v) for v in audio) or 1
    samples = [max(-32767, min(32767, int(v * 0.85 / (pk / 32767)))) for v in audio]

    wav_path = out / "voiceover.wav"
    with wave.open(str(wav_path), "w") as wf:
        wf.setnchannels(CH); wf.setsampwidth(SW); wf.setframerate(SR)
        wf.writeframes(struct.pack("<" + "h" * len(samples), *samples))

    sec = len(samples) / SR
    mb = os.path.getsize(str(wav_path)) / 1048576
    print(f"  voiceover.wav ({sec:.0f}s, {mb:.1f}MB)")


if __name__ == "__main__":
    main()
