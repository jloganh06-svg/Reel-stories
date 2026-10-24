#!/usr/bin/env python3
"""ReelStories video maker.

stories.txt  ->  narrated (Kokoro TTS), word-captioned, 9:16 MP4s over a gameplay background.

Usage (run pipeline/setup.sh once per fresh machine first):
  python3 make.py all --stories ../stories/batch-02.txt --out out/batch-02
  python3 make.py tts    ...   # narration only (cached per paragraph)
  python3 make.py render ...   # videos only
Options: --speed 1.05 (default; keeps every part over 1 minute)  --voice af_heart
         --only 11:2 (story 11 part 2) or --only 11 (all parts of story 11)
"""
import argparse
import csv
import hashlib
import json
import os
import re
import subprocess
import sys
import time

import numpy as np
import soundfile as sf

ROOT = os.path.dirname(os.path.abspath(__file__))
MODEL = os.path.join(ROOT, "models", "kokoro-timed.onnx")
VOICES = os.path.join(ROOT, "models", "voices-v1.0.bin")
FONTS = os.path.join(ROOT, "fonts")
AVATAR = os.path.join(ROOT, "assets", "avatar.png")
SR = 24000

W, H = 1080, 1920
CAP_Y = 900                 # caption centre line
CARD_CY = 880               # hook card centre line
HOOK_GAP = 0.40             # silence after the hook (seconds, before speed-up)
PARA_GAP = 0.28             # silence between paragraphs (before speed-up)
TAIL = 0.45                 # video keeps running after the last word (after speed-up)
MAX_WORDS, MAX_CHARS = 3, 14
WHITE, AMBER = "&H00FFFFFF&", "&H003DC8FF&"   # ASS colours (&HAABBGGRR)

PUNCT = set(';:,.!?¡¿—–…"«»“”‘’()[]\'-')


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


# ---------------------------------------------------------------- stories
def load_stories(path):
    raw = open(path, encoding="utf-8").read()
    bits = re.split(r"^=== (.+?) ===\s*$", raw, flags=re.M)
    stories = []
    for i in range(1, len(bits), 2):
        num, slug = bits[i].strip().split(" ", 1)
        parts = []
        for body in re.split(r"^--- part ---\s*$", bits[i + 1], flags=re.M):
            paras = [re.sub(r"\s+", " ", p).strip()
                     for p in re.split(r"\n\s*\n", body.strip()) if p.strip()]
            parts.append(paras)
        stories.append({"num": int(num), "slug": slug, "parts": parts})
    return stories


def spoken_form(word):
    """How a caption word should be read aloud."""
    m = re.match(r"^(\W*?)\$([\d,]+)(\W*)$", word)
    if m:  # $1,140 -> 1,140 dollars   (espeak says "dollar one thousand..." otherwise)
        return f"{m.group(1)}{m.group(2)} dollars{m.group(3)}"
    m = re.match(r"^(\W*)(\d{1,2}):(\d{2})(\W*)$", word)
    if m:  # 4:30 -> 4 30  (a colon would make the voice pause mid-time)
        return f"{m.group(1)}{m.group(2)} {m.group(3)}{m.group(4)}"
    return word


# ---------------------------------------------------------------- voice
class Voice:
    def __init__(self, voice):
        from kokoro_onnx import Kokoro
        self.k = Kokoro(MODEL, VOICES)
        assert self.k.has_timings, "model must expose phoneme durations"
        self.voice = voice
        self.vocab = self.k.tokenizer.vocab

    def synth(self, text):
        audio, sr, tim = self.k.create_timed(
            text, voice=self.voice, speed=1.0, lang="en-us",
            sentence_pause=0.22, clause_pause=0.08)
        assert sr == SR
        return audio.astype(np.float32), [(t.phoneme, t.start, t.end) for t in tim]

    def iso(self, words):
        """Phonemize each word on its own (one espeak call for the list)."""
        import phonemizer
        from kokoro_onnx.tokenizer import _espeak_lock
        with _espeak_lock:
            out = phonemizer.phonemize(words, language="en-us", backend="espeak",
                                       preserve_punctuation=True, with_stress=True)
        return [norm_ph("".join(c for c in o if c in self.vocab)) for o in out]


def norm_ph(s):
    return "".join(c for c in s if c not in PUNCT and not c.isspace() and c not in "ˈˌ")


def phoneme_groups(timings):
    """Split phoneme timings into space-separated words with their time spans."""
    groups, cur = [], None
    for ph, s, e in timings:
        if ph.isspace():
            if cur:
                groups.append(cur)
            cur = None
            continue
        if ph in PUNCT or ph in "ˈˌ":
            continue
        if cur is None:
            cur = {"ph": "", "start": s, "end": e}
        cur["ph"] += ph
        cur["end"] = e
    if cur:
        groups.append(cur)
    return groups


def lev(a, b):
    if a == b:
        return 0
    if not a or not b:
        return max(len(a), len(b))
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def dist(a, b):
    return lev(a, b) / max(len(a), len(b), 1)


def align(iso, groups):
    """DP-align caption words (isolated phonemes) to spoken phoneme groups.
    Returns per-word (start, end) or None when the word got no audio."""
    n, m = len(iso), len(groups)
    g = [x["ph"] for x in groups]
    INF = float("inf")
    dp = [[INF] * (m + 1) for _ in range(n + 1)]
    bk = [[None] * (m + 1) for _ in range(n + 1)]
    dp[0][0] = 0.0

    def relax(i, j, c, how):
        if c < dp[i][j]:
            dp[i][j], bk[i][j] = c, how

    for i in range(n + 1):
        for j in range(m + 1):
            c0 = dp[i][j]
            if c0 == INF:
                continue
            if j < m:
                relax(i, j + 1, c0 + 1.0, ("skipg", i, j))
            if i < n:
                relax(i + 1, j, c0 + (0.0 if not iso[i] else 1.0), ("skipw", i, j))
                for k in (1, 2, 3, 4):
                    if j + k <= m:
                        relax(i + 1, j + k, c0 + dist(iso[i], "".join(g[j:j + k])) + 0.1 * (k - 1),
                              ("take", i, j, k))
                for w in (2, 3):
                    if i + w <= n and j < m:
                        relax(i + w, j + 1, c0 + dist("".join(iso[i:i + w]), g[j]) + 0.1 * (w - 1),
                              ("merge", i, j, w))
    # backtrack
    spans = [None] * n
    i, j = n, m
    while (i, j) != (0, 0):
        how = bk[i][j]
        kind = how[0]
        if kind == "skipg":
            i, j = how[1], how[2]
        elif kind == "skipw":
            i, j = how[1], how[2]
        elif kind == "take":
            _, pi, pj, k = how
            spans[pi] = (groups[pj]["start"], groups[pj + k - 1]["end"])
            i, j = pi, pj
        else:  # merge: several words share one group, split by phoneme length
            _, pi, pj, w = how
            s, e = groups[pj]["start"], groups[pj]["end"]
            lens = [max(len(iso[pi + q]), 1) for q in range(w)]
            tot, acc = sum(lens), 0
            for q in range(w):
                spans[pi + q] = (s + (e - s) * acc / tot, s + (e - s) * (acc + lens[q]) / tot)
                acc += lens[q]
            i, j = pi, pj
    return spans, dp[n][m]


def fill_missing(spans):
    """Words the voice skipped get a zero-length slot between their neighbours."""
    out = list(spans)
    for idx, sp in enumerate(out):
        if sp is None:
            prev_end = next((out[q][1] for q in range(idx - 1, -1, -1) if out[q]), 0.0)
            out[idx] = (prev_end, prev_end)
    return out


def cache_key(voice, text):
    return hashlib.sha1(f"{voice}|{os.path.getsize(MODEL)}|{text}".encode()).hexdigest()[:16]


def narrate_part(vc, paras, workdir):
    """Synthesize a part paragraph by paragraph; return 1x audio + word timeline."""
    cache = os.path.join(ROOT, "cache", vc.voice)
    os.makedirs(cache, exist_ok=True)
    chunks, words, t = [], [], 0.0
    report = []
    for pi, para in enumerate(paras):
        cap_words = para.split(" ")
        spoken = " ".join(spoken_form(w) for w in cap_words)
        key = cache_key(vc.voice, spoken)
        npz = os.path.join(cache, key + ".npz")
        if os.path.exists(npz):
            d = np.load(npz, allow_pickle=True)
            audio, tim = d["audio"], [tuple(x) for x in d["tim"].tolist()]
            tim = [(str(p), float(s), float(e)) for p, s, e in tim]
        else:
            audio, tim = vc.synth(spoken)
            np.savez(npz, audio=audio, tim=np.array(tim, dtype=object))
        groups = phoneme_groups(tim)
        iso = vc.iso([spoken_form(w) for w in cap_words])
        spans, cost = align(iso, groups)
        missing = sum(1 for s in spans if s is None)
        report.append({"para": pi, "words": len(cap_words), "groups": len(groups),
                       "cost": round(cost, 2), "missing": missing})
        spans = fill_missing(spans)
        for w, (s, e) in zip(cap_words, spans):
            words.append({"text": w, "start": t + s, "end": t + e, "para": pi})
        chunks.append(audio)
        t += len(audio) / SR
        if pi < len(paras) - 1:
            gap = HOOK_GAP if pi == 0 else PARA_GAP
            chunks.append(np.zeros(int(gap * SR), dtype=np.float32))
            t += gap
    audio = np.concatenate(chunks)
    os.makedirs(workdir, exist_ok=True)
    sf.write(os.path.join(workdir, "narration_1x.wav"), audio, SR)
    json.dump({"words": words, "dur": len(audio) / SR, "align": report},
              open(os.path.join(workdir, "timeline_1x.json"), "w"), indent=1)
    return words, len(audio) / SR, report


# ---------------------------------------------------------------- audio speed + loudness
def speed_audio(workdir, speed):
    src = os.path.join(workdir, "narration_1x.wav")
    dst = os.path.join(workdir, "narration.wav")
    chain = []
    s = speed
    while s > 2.0 + 1e-9:          # keep each atempo stage within its best range
        chain.append("atempo=2.0")
        s /= 2.0
    if abs(s - 1.0) > 1e-6:
        chain.append(f"atempo={s:.6f}")
    pre = ",".join(chain) if chain else "anull"
    meas = subprocess.run(
        ["ffmpeg", "-hide_banner", "-nostats", "-i", src, "-af",
         f"{pre},loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json", "-f", "null", "-"],
        capture_output=True, text=True).stderr
    js = json.loads(meas[meas.rindex("{"):meas.rindex("}") + 1])
    ln = (f"loudnorm=I=-14:TP=-1.5:LRA=11:measured_I={js['input_i']}:measured_TP={js['input_tp']}:"
          f"measured_LRA={js['input_lra']}:measured_thresh={js['input_thresh']}:"
          f"offset={js['target_offset']}:linear=true")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", src, "-af", f"{pre},{ln},aresample=48000",
                    "-ar", "48000", dst], check=True)
    return dst


# ---------------------------------------------------------------- hook card
def wrap(text, font, width, draw):
    lines, cur = [], ""
    for w in text.split(" "):
        test = (cur + " " + w).strip()
        if draw.textlength(test, font=font) <= width or not cur:
            cur = test
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def make_card(hook, out_png):
    from PIL import Image, ImageDraw, ImageFilter, ImageFont
    cw, pad, rad, shadow = 920, 48, 44, 40
    f_name = ImageFont.truetype(os.path.join(FONTS, "RSCardBold.ttf"), 40)
    f_sub = ImageFont.truetype(os.path.join(FONTS, "RSCardSemi.ttf"), 28)
    f_text = ImageFont.truetype(os.path.join(FONTS, "RSCardBold.ttf"), 54)
    probe = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    lines = wrap(hook, f_text, cw - 2 * pad, probe)
    lh, av = 68, 96
    ch = pad + av + 30 + lh * len(lines) - 6 + pad
    img = Image.new("RGBA", (cw + 2 * shadow, ch + 2 * shadow), (0, 0, 0, 0))
    sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle((shadow, shadow + 14, shadow + cw, shadow + ch + 14),
                                         radius=rad, fill=(0, 0, 0, 120))
    img = Image.alpha_composite(img, sh.filter(ImageFilter.GaussianBlur(20)))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((shadow, shadow, shadow + cw, shadow + ch), radius=rad, fill=(255, 255, 255, 255))
    ax, ay = shadow + pad, shadow + pad
    a = Image.open(AVATAR).convert("RGBA").resize((av * 4, av * 4), Image.LANCZOS)
    mask = Image.new("L", a.size, 0)
    ImageDraw.Draw(mask).ellipse((0, 0, a.size[0] - 1, a.size[1] - 1), fill=255)
    a.putalpha(mask)
    img.alpha_composite(a.resize((av, av), Image.LANCZOS), (ax, ay))
    d.text((ax + av + 24, ay + 10), "ReelStories", font=f_name, fill=(17, 17, 17))
    d.text((ax + av + 24, ay + 58), "Story time", font=f_sub, fill=(128, 128, 128))
    ty = ay + av + 30
    for i, line in enumerate(lines):
        d.text((ax, ty + i * lh), line, font=f_text, fill=(15, 15, 15))
    img.save(out_png)
    return img.size


# ---------------------------------------------------------------- captions
def ass_time(t):
    t = max(0.0, t)
    cs = int(round(t * 100))
    return f"{cs // 360000}:{cs // 6000 % 60:02d}:{cs // 100 % 60:02d}.{cs % 100:02d}"


def chunk_words(words):
    chunks, cur = [], []
    for w in words:
        length = sum(len(x["text"]) for x in cur) + len(cur)
        if cur and (len(cur) >= MAX_WORDS or length + 1 + len(w["text"]) > MAX_CHARS):
            chunks.append(cur)
            cur = []
        cur.append(w)
        if re.search(r"[.!?,;:][\"”’']?$", w["text"]):
            chunks.append(cur)
            cur = []
    if cur:
        chunks.append(cur)
    return chunks


def make_ass(words, out_path, end_time):
    head = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,RS Caption,112,{WHITE},{WHITE},&H00000000&,&H70000000&,0,0,0,0,100,100,0,0,1,9,5,5,100,100,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    chunks = chunk_words(words)
    lines = []
    for ci, ch in enumerate(chunks):
        c_start = ch[0]["start"]
        nxt = chunks[ci + 1][0]["start"] if ci + 1 < len(chunks) else end_time
        c_end = min(nxt, ch[-1]["end"] + 0.35)
        if nxt - c_end < 0.25:          # bridge short pauses so text doesn't flicker
            c_end = nxt
        for wi, w in enumerate(ch):
            s = c_start if wi == 0 else w["start"]
            e = ch[wi + 1]["start"] if wi + 1 < len(ch) else c_end
            if e - s < 0.04:
                continue
            txt = " ".join((f"{{\\c{AMBER}}}{x['text']}{{\\c{WHITE}}}" if xi == wi else x["text"])
                           for xi, x in enumerate(ch))
            tag = f"{{\\pos({W // 2},{CAP_Y})"
            tag += "\\fscx84\\fscy84\\t(0,90,\\fscx100\\fscy100)}" if wi == 0 else "}"
            lines.append(f"Dialogue: 0,{ass_time(s)},{ass_time(e)},Cap,,0,0,0,,{tag}{txt}")
    open(out_path, "w", encoding="utf-8").write(head + "\n".join(lines) + "\n")
    return len(chunks)


# ---------------------------------------------------------------- render
def bg_duration(bg):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                 "-of", "csv=p=0", bg], capture_output=True, text=True).stdout)


def render_part(story, pidx, gidx, args, vc=None):
    tag = f"S{story['num']:02d}_P{pidx + 1}"
    workdir = os.path.join(ROOT, "work", tag)
    paras = story["parts"][pidx]
    tl = os.path.join(workdir, "timeline_1x.json")
    if not os.path.exists(tl) or args.retts:
        if vc is None:
            vc = Voice(args.voice)
        narrate_part(vc, paras, workdir)
    data = json.load(open(tl))
    if args.stage == "tts":
        return None
    speed = args.speed
    nar = speed_audio(workdir, speed)
    nar_dur = float(sf.info(nar).duration)
    words = [dict(w, start=w["start"] / speed, end=w["end"] / speed) for w in data["words"]]
    hook = [w for w in words if w["para"] == 0]
    body = [w for w in words if w["para"] > 0]
    total = max(nar_dur, words[-1]["end"]) + TAIL
    card_end = (body[0]["start"] - 0.02) if body else hook[-1]["end"] + 0.3
    ass = os.path.join(workdir, "captions.ass")
    n_chunks = make_ass(body, ass, total - 0.1)
    card = os.path.join(workdir, "card.png")
    cw, chh = make_card(paras[0], card)
    cx, cy = (W - cw) // 2, CARD_CY - chh // 2
    bgdur = bg_duration(args.bg)
    offset = (gidx * 17.3) % bgdur
    flip = "hflip," if gidx % 2 else ""
    os.makedirs(args.out, exist_ok=True)
    out = os.path.join(args.out, f"ReelStories_{tag}_{story['slug']}.mp4")
    fc = (f"[0:v]{flip}setpts=PTS-STARTPTS,fps=30[bg];"
          f"[1:v]format=rgba,fade=out:st={max(card_end - 0.15, 0):.3f}:d=0.15:alpha=1[card];"
          f"[bg][card]overlay=x={cx}:y={cy}:enable='lte(t,{card_end:.3f})'[v1];"
          f"[v1]ass=filename={ass}:fontsdir={FONTS}[v]")
    cmd = ["ffmpeg", "-v", "error", "-y",
           "-stream_loop", "-1", "-ss", f"{offset:.3f}", "-i", args.bg,
           "-loop", "1", "-framerate", "30", "-i", card,
           "-i", nar,
           "-filter_complex", fc, "-map", "[v]", "-map", "2:a",
           "-t", f"{total:.3f}", "-r", "30",
           "-c:v", "libx264", "-preset", args.preset, "-crf", str(args.crf), "-profile:v", "high",
           "-maxrate", args.maxrate, "-bufsize", args.bufsize,
           "-pix_fmt", "yuv420p", "-g", "60",
           "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
           "-movflags", "+faststart", out]
    t0 = time.time()
    subprocess.run(cmd, check=True)
    info = {"file": out, "tag": tag, "duration": round(total, 2), "chunks": n_chunks,
            "card_end": round(card_end, 2), "bg_offset": round(offset, 1), "flip": bool(flip),
            "align": data["align"], "render_s": round(time.time() - t0, 1),
            "size_mb": round(os.path.getsize(out) / 1e6, 1)}
    json.dump(info, open(os.path.join(workdir, "render.json"), "w"), indent=1)
    return info


def posting_sheet(stories, args):
    rows = []
    tags = "#storytime #redditstories #aita #relationshipdrama #fyp"
    for s in stories:
        n = len(s["parts"])
        for pi, paras in enumerate(s["parts"]):
            tag = f"S{s['num']:02d}_P{pi + 1}"
            hook = s["parts"][0][0]          # the story's main hook gives every part context
            cap = f"Part {pi + 1}/{n}: {hook} {tags}"
            rows.append({"file": f"ReelStories_{tag}_{s['slug']}.mp4", "story": s["num"],
                         "part": pi + 1, "caption": cap})
    path = os.path.join(args.out, "posting_sheet.csv")
    with open(path, "w", newline="", encoding="utf-8") as fh:
        wr = csv.DictWriter(fh, fieldnames=["file", "story", "part", "caption"])
        wr.writeheader()
        wr.writerows(rows)
    return path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["tts", "render", "all"])
    ap.add_argument("--stories", default=os.path.join(ROOT, "stories.txt"))
    ap.add_argument("--bg", default=os.path.join(ROOT, "bg", "bg_916.mp4"))
    ap.add_argument("--out", default=os.path.join(ROOT, "out"))
    ap.add_argument("--voice", default="af_heart")
    ap.add_argument("--speed", type=float, default=1.05)
    ap.add_argument("--crf", type=int, default=23)
    ap.add_argument("--preset", default="veryfast")
    ap.add_argument("--maxrate", default="4500k")
    ap.add_argument("--bufsize", default="9000k")
    ap.add_argument("--only", default="", help="e.g. 1:1 or 3 (story) or 1:1,2:3")
    ap.add_argument("--retts", action="store_true")
    args = ap.parse_args()

    stories = load_stories(args.stories)
    want = set()
    for item in filter(None, args.only.split(",")):
        if ":" in item:
            a, b = item.split(":")
            want.add((int(a), int(b)))
        else:
            want.update((int(item), p + 1) for p in range(4))
    jobs = []
    for s in stories:
        for pi in range(len(s["parts"])):
            if not want or (s["num"], pi + 1) in want:
                jobs.append((s, pi))
    vc = None
    # background start point + mirroring come from the story number, so every batch gets fresh footage
    gidx_of = {(s["num"], pi): (s["num"] - 1) * 4 + pi for s in stories for pi in range(len(s["parts"]))}
    for s, pi in jobs:
        tag = f"S{s['num']:02d}_P{pi + 1}"
        if vc is None and (args.retts or not os.path.exists(os.path.join(ROOT, "work", tag, "timeline_1x.json"))):
            vc = Voice(args.voice)
        args_stage = argparse.Namespace(**vars(args))
        args_stage.stage = "tts" if args.stage == "tts" else "render"
        t0 = time.time()
        info = render_part(s, pi, gidx_of[(s["num"], pi)], args_stage, vc)
        if info:
            log(tag, "done", f"{info['duration']}s", f"{info['size_mb']}MB", f"render {info['render_s']}s",
                "align", [(a["words"], a["groups"], a["cost"], a["missing"]) for a in info["align"]])
        else:
            log(tag, "tts done", f"{time.time() - t0:.1f}s")
    if args.stage != "tts":
        os.makedirs(args.out, exist_ok=True)
        log("posting sheet:", posting_sheet(stories, args))


if __name__ == "__main__":
    main()
