#!/usr/bin/env bash
# One-time setup for a fresh machine: Python packages, the Kokoro voice model, caption fonts.
# Safe to run again; it skips anything already in place.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"

pip install --break-system-packages -q kokoro-onnx soundfile brotli fonttools pillow numpy onnxruntime

mkdir -p "$HERE/models" "$HERE/fonts"
# Model export WITH phoneme durations (needed for word-timed captions) lives in the v1.1 release.
[ -s "$HERE/models/kokoro-timed.onnx" ] || curl -sSL --retry 3 -o "$HERE/models/kokoro-timed.onnx" \
  https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.1/kokoro-v1.0.onnx
[ -s "$HERE/models/voices-v1.0.bin" ] || curl -sSL --retry 3 -o "$HERE/models/voices-v1.0.bin" \
  https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin

python3 - "$HERE/models/kokoro-timed.onnx" <<'EOF'
import sys, onnxruntime as ort
outs = {o.name for o in ort.InferenceSession(sys.argv[1], providers=["CPUExecutionProvider"]).get_outputs()}
assert "duration" in outs, f"model has no duration output: {outs}"
print("voice model ok")
EOF

# Caption/card fonts: Montserrat from npm, converted to TTF with unique family names for libass.
if [ ! -s "$HERE/fonts/RSCaption.ttf" ]; then
  TMP="$(mktemp -d)"
  (cd "$TMP" && npm init -y >/dev/null 2>&1 && npm i @fontsource/montserrat >/dev/null 2>&1)
  python3 - "$TMP" "$HERE/fonts" <<'EOF'
import sys
from fontTools.ttLib import TTFont
src = sys.argv[1] + "/node_modules/@fontsource/montserrat/files/montserrat-latin-{w}-normal.woff2"
for w, fam in [(800, "RS Caption"), (700, "RS Card Bold"), (600, "RS Card Semi")]:
    f = TTFont(src.format(w=w)); f.flavor = None
    name = f["name"]
    for rec in list(name.names):
        if rec.nameID in (1, 4, 6, 16, 17):
            name.removeNames(nameID=rec.nameID)
    for pid, eid, lid in [(3, 1, 0x409), (1, 0, 0)]:
        name.setName(fam, 1, pid, eid, lid); name.setName("Regular", 2, pid, eid, lid)
        name.setName(fam, 4, pid, eid, lid); name.setName(fam.replace(" ", ""), 6, pid, eid, lid)
    f["OS/2"].usWeightClass = 400
    f["OS/2"].fsSelection = (f["OS/2"].fsSelection & ~0b100001) | 0b1000000
    f["head"].macStyle = 0
    f.save(sys.argv[2] + "/" + fam.replace(" ", "") + ".ttf")
print("fonts ok")
EOF
fi

FILTERS="$(ffmpeg -hide_banner -filters 2>/dev/null || true)"
grep -q " ass " <<<"$FILTERS" || { echo "ffmpeg without libass"; exit 1; }
echo "setup complete"
