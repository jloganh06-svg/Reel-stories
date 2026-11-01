"""Own-voice mode: use a person's recorded narration instead of the AI voice.

Jack reads a part into his phone (any format: m4a, mp3, wav, ogg, webm). We still know the exact
script, so captions don't need speech recognition: we synthesize the same text with a reference
AI voice (which gives exact word timings), then line the reference up against the recording with
dynamic time warping over MFCC features and carry every word's timing across.

Ad-libs and small slips are fine; DTW absorbs them. Reading a different paragraph order is not.
"""
import glob
import json
import os
import subprocess

import numpy as np
import soundfile as sf

SR = 24000
HOP = 480            # 20 ms frames
REF_VOICE = "am_michael"   # a male reference voice lines up better with Jack's voice
EXTS = ("m4a", "mp3", "wav", "aac", "ogg", "opus", "webm", "mp4", "mov", "caf", "flac")


def find_recording(rec_dir, story_num, part):
    """Recording for story NN part P: S11_P2.m4a (also accepts 11-2.m4a / 11_2.m4a)."""
    if not rec_dir:
        return None
    for stem in (f"S{story_num:02d}_P{part}", f"{story_num}-{part}", f"{story_num}_{part}",
                 f"{story_num:02d}-{part}", f"{story_num:02d}_{part}"):
        for ext in EXTS:
            hits = glob.glob(os.path.join(rec_dir, f"{stem}.{ext}")) + \
                glob.glob(os.path.join(rec_dir, f"{stem}.{ext.upper()}"))
            if hits:
                return hits[0]
    return None


def load_recording(path, out_wav):
    """Decode to 24 kHz mono, clean phone rumble/hiss lightly, trim dead air at both ends."""
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", path, "-vn", "-ac", "1", "-ar", str(SR),
                    "-af", "highpass=f=70,afftdn=nf=-25", out_wav], check=True)
    y, _ = sf.read(out_wav, dtype="float32")
    import librosa
    _, (a, b) = librosa.effects.trim(y, top_db=38, frame_length=1024, hop_length=256)
    pad = int(0.12 * SR)
    y = y[max(a - pad, 0):min(b + pad, len(y))]
    sf.write(out_wav, y, SR)
    return y


def features(y):
    import librosa
    m = librosa.feature.mfcc(y=y, sr=SR, n_mfcc=20, n_fft=1024, hop_length=HOP)[1:]
    d = librosa.feature.delta(m)
    f = np.vstack([m, d])
    f = (f - f.mean(axis=1, keepdims=True)) / (f.std(axis=1, keepdims=True) + 1e-6)
    return f


def warp_map(ref_y, rec_y):
    """Return a function mapping reference seconds -> recording seconds."""
    import librosa
    X, Y = features(ref_y), features(rec_y)
    _, wp = librosa.sequence.dtw(X=X, Y=Y, metric="euclidean")
    wp = wp[::-1]
    n = X.shape[1]
    acc = [[] for _ in range(n)]
    for i, j in wp:
        acc[i].append(j)
    ref_f = np.arange(n)
    rec_f = np.array([np.mean(a) if a else np.nan for a in acc])
    ok = ~np.isnan(rec_f)
    rec_f = np.interp(ref_f, ref_f[ok], rec_f[ok])
    rec_f = np.maximum.accumulate(rec_f)          # keep it monotonic
    fr = HOP / SR

    def to_rec(t):
        return float(np.interp(t / fr, ref_f, rec_f) * fr)
    return to_rec


def narrate_from_recording(rec_path, paras, workdir, voice_factory, narrate_part):
    """Writes narration_1x.wav (the person's voice) + timeline_1x.json, like the AI path does."""
    os.makedirs(workdir, exist_ok=True)
    refdir = os.path.join(workdir, "ref")
    vc = voice_factory(REF_VOICE)
    ref_words, ref_dur, _ = narrate_part(vc, paras, refdir)
    ref_y, _ = sf.read(os.path.join(refdir, "narration_1x.wav"), dtype="float32")
    out_wav = os.path.join(workdir, "narration_1x.wav")
    rec_y = load_recording(rec_path, out_wav)
    to_rec = warp_map(ref_y, rec_y)
    words = []
    for w in ref_words:
        s, e = to_rec(w["start"]), to_rec(w["end"])
        words.append(dict(w, start=s, end=max(e, s + 0.04)))
    dur = len(rec_y) / SR
    json.dump({"words": words, "dur": dur, "source": "recording", "recording": os.path.basename(rec_path),
               "align": [{"para": -1, "words": len(words), "groups": 0, "cost": 0, "missing": 0}]},
              open(os.path.join(workdir, "timeline_1x.json"), "w"), indent=1)
    return words, dur
