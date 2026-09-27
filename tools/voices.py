"""Japanese voice track: every subtitle line that has an entry in
dialogue_ja.JA is spoken with Kokoro TTS (offline, ONNX) in the speaker's voice.

  python3 tools/voices.py            synthesise missing / changed lines

Outputs
  tools/voice_index.json                         "speaker|line" -> {id, ja, dur}  (timing source for film.say)
  build/voices/<id>.wav                          24 kHz mono, for the preview mix
  resourcepack/assets/kino/sounds/voice/<id>.ogg the same line for the game (sound event kino:voice.<id>)

Needs  pip install kokoro-onnx misaki[ja] soundfile  and the model files
(downloaded to build/cache/kokoro/ on first run)."""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
import dialogue_ja  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX = os.path.join(ROOT, "tools", "voice_index.json")
WAV_DIR = os.path.join(ROOT, "build", "voices")
OGG_DIR = os.path.join(ROOT, "resourcepack", "assets", "kino", "sounds", "voice")
MODEL_DIR = os.path.join(ROOT, "build", "cache", "kokoro")
MODEL_URL = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/"
SR = 24000


def key(who, text):
    return f"{who}|{text}"


def voice_id(who, text):
    return hashlib.sha1(key(who, text).encode("utf-8")).hexdigest()[:10]


def load_index():
    if os.path.exists(INDEX):
        with open(INDEX, encoding="utf-8") as fh:
            return json.load(fh)
    return {}


def lines_from_script():
    import script
    F = script.build()
    out = []
    for (_t0, _t1, who, text) in F.subs:
        if who and text in dialogue_ja.JA and (who, text) not in out:
            out.append((who, text))
    return out


def trim(a, thr=0.012, pad=0.03):
    """Cut leading/trailing silence, keep a short pad."""
    env = np.convolve(np.abs(a), np.ones(240) / 240, mode="same")
    idx = np.where(env > thr)[0]
    if len(idx) == 0:
        return a
    s = max(0, idx[0] - int(pad * SR))
    e = min(len(a), idx[-1] + int(pad * SR))
    return a[s:e]


def normalise(a, target_rms=0.1, peak=0.93):
    """Speech-level RMS (loud frames only) to a common target, then keep peaks in range."""
    fr = 480
    n = len(a) // fr
    if n == 0:
        return a
    rms = np.sqrt((a[: n * fr].reshape(n, fr) ** 2).mean(axis=1))
    loud = rms[rms > rms.max() * 0.2]
    g = target_rms / max(float(np.sqrt((loud ** 2).mean())), 1e-6)
    a = a * g
    p = float(np.abs(a).max())
    if p > peak:
        a = a * (peak / p)
    fade = min(len(a) // 4, int(0.01 * SR))
    a[:fade] *= np.linspace(0, 1, fade)
    a[len(a) - fade:] *= np.linspace(1, 0, fade)
    return a.astype(np.float32)


def ensure_model():
    os.makedirs(MODEL_DIR, exist_ok=True)
    for f in ("kokoro-v1.0.onnx", "voices-v1.0.bin"):
        p = os.path.join(MODEL_DIR, f)
        if not os.path.exists(p):
            subprocess.check_call(["curl", "-sSfL", "-o", p, MODEL_URL + f])


def main():
    import soundfile as sf
    lines = lines_from_script()
    index = load_index()
    todo = []
    for who, text in lines:
        vid = voice_id(who, text)
        blend, speed = dialogue_ja.VOICES[who]
        spec = {"ja": dialogue_ja.JA[text], "voice": blend, "speed": speed}
        cur = index.get(key(who, text))
        have = os.path.exists(os.path.join(OGG_DIR, vid + ".ogg")) and os.path.exists(os.path.join(WAV_DIR, vid + ".wav"))
        if cur and have and all(cur.get(k) == (list(map(list, v)) if k == "voice" else v) for k, v in spec.items()):
            continue
        todo.append((who, text, vid, spec))
    print(f"voices: {len(lines)} lines, {len(todo)} to synthesise")
    if todo:
        ensure_model()
        from kokoro_onnx import Kokoro
        from misaki import ja
        g2p = ja.JAG2P()
        k = Kokoro(os.path.join(MODEL_DIR, "kokoro-v1.0.onnx"), os.path.join(MODEL_DIR, "voices-v1.0.bin"))
        styles = {}
        os.makedirs(WAV_DIR, exist_ok=True)
        os.makedirs(OGG_DIR, exist_ok=True)
        for n, (who, text, vid, spec) in enumerate(todo):
            if who not in styles:
                styles[who] = sum(k.get_voice_style(v) * w for v, w in spec["voice"])
            ps, _ = g2p(spec["ja"])
            a, sr = k.create(ps, voice=styles[who], speed=spec["speed"], is_phonemes=True)
            assert sr == SR
            a = normalise(trim(np.asarray(a, dtype=np.float32)))
            wav = os.path.join(WAV_DIR, vid + ".wav")
            sf.write(wav, a, SR, subtype="PCM_16")
            subprocess.check_call(["ffmpeg", "-y", "-loglevel", "error", "-i", wav, "-ac", "1", "-c:a", "libvorbis",
                                   "-q:a", "2", os.path.join(OGG_DIR, vid + ".ogg")])
            index[key(who, text)] = {"id": vid, "ja": spec["ja"], "voice": [list(v) for v in spec["voice"]],
                                     "speed": spec["speed"], "dur": round(len(a) / SR, 3)}
            print(f"  [{n + 1}/{len(todo)}] {who}: {spec['ja']}  {len(a) / SR:.2f}s", flush=True)
            if n % 20 == 19:
                save(index, lines)
    save(index, lines)
    total = sum(v["dur"] for v in index.values())
    print(f"voices: {len(index)} lines, {total / 60:.1f} min of speech -> {os.path.relpath(OGG_DIR, ROOT)}")


def save(index, lines):
    keep = {key(w, t) for w, t in lines}
    index = {k: v for k, v in index.items() if k in keep}
    with open(INDEX, "w", encoding="utf-8") as fh:
        json.dump(index, fh, ensure_ascii=False, indent=1, sort_keys=True)
    ids = {v["id"] for v in index.values()}
    if os.path.isdir(OGG_DIR):
        for f in os.listdir(OGG_DIR):
            if f.endswith(".ogg") and f[:-4] not in ids:
                os.remove(os.path.join(OGG_DIR, f))


if __name__ == "__main__":
    main()
