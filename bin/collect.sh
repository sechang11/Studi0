#!/usr/bin/env bash
# Turn whatever generate.sh has produced into something you can actually look at.
#
#   ./bin/collect.sh                 # contact sheets + index.html over studio/samples/rolled
#   ./bin/collect.sh --open          # and print the URL to open
#   ./bin/collect.sh --top 40        # only the 40 brightest/most saturated stills
#
# A folder of 400 webp files is not a demo library. This builds three things from it:
#   contact_NN.jpg   6-across contact sheets, so a run can be judged in one glance
#   index.html       every artifact with the style, place, grade and engine that made it
#   manifest.json    the same as data
#
# WHY THE RECIPE IS ON THE PAGE. Every artifact from render_job.py has a .json sidecar with
# the exact cards and seed behind it. A gallery that shows only the picture teaches nothing;
# one that shows "this is `claymation` on `qwen`, in `locker_room`, graded `warm`, seed
# 118..." lets you go straight back to the wizard and make another.

set -uo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DIR="$REPO/studio/samples/rolled"
TOP=0; OPEN=0

while [ $# -gt 0 ]; do
  case "$1" in
    --dir)  DIR="$2"; shift 2 ;;
    --top)  TOP="$2"; shift 2 ;;
    --open) OPEN=1; shift ;;
    -h|--help) sed -n '2,18p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "unknown option: $1" >&2; exit 1 ;;
  esac
done

[ -d "$DIR" ] || { echo "nothing at $DIR - run bin/generate.sh first" >&2; exit 1; }

python3 - "$DIR" "$TOP" <<'PY'
import glob, html, json, os, subprocess, sys

d, top = sys.argv[1], int(sys.argv[2])
recs = []
for sc in sorted(glob.glob(os.path.join(d, "*", "*.json"))):
    if os.path.basename(os.path.dirname(sc)) == "rejected":
        continue
    try:
        r = json.load(open(sc, encoding="utf-8"))
    except Exception:
        continue
    if r.get("file") and os.path.exists(r["file"]):
        recs.append(r)

rej = len(glob.glob(os.path.join(d, "*", "rejected", "*.json")))
stills = [r for r in recs if r["domain"] == "image"]
# Brightest-and-most-saturated first is a crude ranking, but it is a MEASURED one, and it
# reliably floats the flat grey renders to the bottom where they belong.
stills.sort(key=lambda r: -((r.get("luma") or 0) * 0.5 + (r.get("sat") or 0) * 2))
if top:
    stills = stills[:top]

sheets = []
for i in range(0, len(stills), 24):
    batch = stills[i:i + 24]
    out = os.path.join(d, "contact_%02d.jpg" % (i // 24 + 1))
    cmd = ["ffmpeg", "-y", "-v", "error"]
    for r in batch:
        cmd += ["-i", r["file"]]
    n = len(batch)
    # Explicit scale per input before tiling. `tile=` fed a glob silently DROPS cells whose
    # size differs from the first, which cost this project two ruined contact sheets; every
    # cell is forced to one size here and the count is checked afterwards.
    fc = "".join("[%d:v]scale=320:320:force_original_aspect_ratio=decrease,"
                 "pad=320:320:(ow-iw)/2:(oh-ih)/2:color=0x111111[c%d];" % (k, k)
                 for k in range(n))
    # fill= matters: a last row that does not divide by six leaves empty canvas, and
    # xstack's default for that is BRIGHT GREEN. The first sheet came out with a quarter
    # of it looking like a chroma-key screen.
    fc += "".join("[c%d]" % k for k in range(n)) + \
        "xstack=inputs=%d:fill=0x111111:layout=%s[v]" % (
            n, "|".join("%d_%d" % (320 * (k % 6), 320 * (k // 6)) for k in range(n)))
    if n == 1:
        fc = "[0:v]scale=320:320:force_original_aspect_ratio=decrease[v]"
    cmd += ["-filter_complex", fc, "-map", "[v]", "-frames:v", "1", out]
    p = subprocess.run(cmd, capture_output=True, text=True)
    if os.path.exists(out):
        sheets.append((os.path.basename(out), n))
    else:
        print("  ! sheet %d failed: %s" % (i // 24 + 1, p.stderr.strip()[:160]))

def cell(r):
    f = os.path.relpath(r["file"], d)
    bits = [b for b in (r.get("style"), r.get("place"), r.get("look"),
                        r.get("cue"), r.get("preset"), r.get("voice")) if b]
    meta = " · ".join(html.escape(str(b)) for b in bits)
    eng = html.escape(str(r.get("engine") or r["domain"]))
    if r["domain"] == "image":
        m = '<img src="%s" loading="lazy">' % html.escape(f)
    elif r["domain"] == "video":
        m = '<video src="%s" controls preload="none"></video>' % html.escape(f)
    else:
        m = '<audio src="%s" controls preload="none"></audio>' % html.escape(f)
    return ('<figure>%s<figcaption><b>%s</b><span>%s</span>'
            '<code>seed %s</code></figcaption></figure>'
            % (m, meta or r["domain"], eng, r.get("seed", "")))

by_dom = {}
for r in recs:
    by_dom.setdefault(r["domain"], []).append(r)

parts = ["""<!doctype html><meta charset=utf-8><title>Rolled gallery</title><style>
body{background:#101014;color:#e8e8ee;font:15px/1.5 system-ui,sans-serif;margin:0;padding:28px}
h1{font-size:22px;margin:0 0 4px} h2{margin:34px 0 10px;font-size:16px;color:#9fb3ff}
p.note{color:#8a8a99;max-width:70ch;margin:0 0 8px}
.grid{display:grid;gap:14px;grid-template-columns:repeat(auto-fill,minmax(240px,1fr))}
figure{margin:0;background:#191921;border-radius:8px;overflow:hidden}
figure img,figure video{width:100%;display:block;aspect-ratio:1;object-fit:cover}
figure audio{width:100%;padding:8px 0}
figcaption{padding:8px 10px;font-size:12px;display:flex;flex-direction:column;gap:2px}
figcaption span{color:#8a8a99} figcaption code{color:#6f6f80;font-size:11px}
a{color:#9fb3ff}</style>"""]
parts.append("<h1>Rolled gallery</h1><p class=note>%d artifacts, %d rejected before they "
             "reached this page. Every one carries the cards and the seed that made it, so "
             "any of them can be made again.</p>" % (len(recs), rej))
if sheets:
    parts.append("<p class=note>Contact sheets: " + " ".join(
        '<a href="%s">%s (%d)</a>' % (s, s, n) for s, n in sheets) + "</p>")
for dom in ("image", "video", "music", "sfx", "voice"):
    rs = by_dom.get(dom) or []
    if not rs:
        continue
    parts.append("<h2>%s (%d)</h2><div class=grid>%s</div>"
                 % (dom, len(rs), "".join(cell(r) for r in rs)))

open(os.path.join(d, "index.html"), "w", encoding="utf-8").write("".join(parts))
json.dump(recs, open(os.path.join(d, "manifest.json"), "w", encoding="utf-8"), indent=1)

print("%d artifacts (%d rejected), %d contact sheet(s)" % (len(recs), rej, len(sheets)))
for dom, rs in sorted(by_dom.items()):
    print("  %-6s %d" % (dom, len(rs)))
print("  %s/index.html" % d)
PY

[ "$OPEN" = "1" ] && echo "open file://$DIR/index.html"
exit 0
