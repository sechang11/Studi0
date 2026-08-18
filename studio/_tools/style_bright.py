#!/usr/bin/env python3
"""studio/_tools/style_bright.py - what each shorts style preset does to brightness.

look_luma answers this for the 25 deterministic GRADES. This answers it for the five
style strings that go into the prompt, which is where the delivered slate's remaining
darkness actually lives now that the letterbox is gone.

The five presets in shorts_specs.py were written before anything here measured luma, and
read as if brightness were free:

    STYLE_CLEAN    "soft diffused daylight ... muted natural palette"
    STYLE_KITCHEN  "morning kitchen light ... muted earthy palette"
    STYLE_LAB      "cool even lighting, white and steel surfaces"
    STYLE_NATURE   "soft golden hour, gentle haze, muted greens"
    STYLE_CINE     "dramatic contrast, moody practical lighting, rich shadows"

Four of the five ask for light and then say "muted" or "haze" in the same breath, and the
delivered films measured 31.9 to 47.6 - the whole slate within 16 luma of each other,
which is not five different looks, it is one dark look five times.

The controlled result this is built on (bright_test, three seeds, one subject):

    lighting adjectives      +57 luma
    named bright objects     +61 luma
    both together            +73 luma
    moody/shadow adjectives  -38 luma

So the language works in both directions and a preset gets what it asks for. Run this
before and after editing a preset; a style that is meant to read bright and measures
within noise of the moody one is a preset that does not do what its name says.

    python3 studio/_tools/style_bright.py
    python3 studio/_tools/style_bright.py --seeds 42 --subject "a glass jar on a counter"
"""
import argparse
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
COMFY_OUT = os.path.expanduser("~/ComfyUI/output")
sys.path.insert(0, HERE)

# One neutral subject for every preset, so the only variable is the style string. A
# subject with its own strong brightness (a lamp, a night sky) would drown the signal.
SUBJECT = "a canvas backpack standing on a wooden table in a room"


def sh(*a, **kw):
    return subprocess.run(a, capture_output=True, text=True, **kw)


def luma(path):
    from PIL import Image
    im = Image.open(path).convert("L").resize((256, 144))
    px = list(im.getdata())
    return 255.0 * sum(px) / (len(px) * 255.0)


def presets():
    import shorts_specs as S
    return [(n, getattr(S, n)) for n in sorted(dir(S)) if n.startswith("STYLE_")]


def render(text, seed, prefix):
    r = sh(sys.executable, os.path.join(ROOT, "scripts", "comfy.py"), "run",
           os.path.join(ROOT, "workflows", "01_qwen_t2i_turbo.json"),
           "-s", "10.inputs.text=%s" % text, "-s", "13.inputs.seed=%d" % seed,
           "-s", "15.inputs.filename_prefix=%s" % prefix, cwd=ROOT)
    m = re.search(r"-> (\S+\.png)", r.stdout or "")
    if not m:
        print("      FAILED: %s" % ((r.stderr or r.stdout or "").strip()[-200:]))
        return None
    return os.path.join(COMFY_OUT, m.group(1))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", default="42,1234,7701")
    ap.add_argument("--subject", default=SUBJECT)
    ap.add_argument("--out", default=os.path.expanduser("~/shared/AB/styles"))
    a = ap.parse_args()
    seeds = [int(s) for s in a.seeds.split(",") if s.strip()]
    os.makedirs(a.out, exist_ok=True)

    rows = []
    # bare subject first - the baseline every preset is judged against
    for name, style in [("(no style)", "")] + presets():
        vals = []
        for seed in seeds:
            text = a.subject + (", " + style if style else "")
            p = render(text, seed, "claude-generated/sb_%s_%d"
                       % (re.sub(r"\W+", "", name) or "bare", seed))
            if not p or not os.path.exists(p):
                continue
            keep = os.path.join(a.out, "%s_%d.png" % (re.sub(r"\W+", "_", name), seed))
            sh("cp", p, keep)
            vals.append(luma(keep))
        if vals:
            rows.append((name, sum(vals) / len(vals), len(vals)))
            print("  %-16s %.1f  (n=%d)" % (name, rows[-1][1], len(vals)))

    base = next((v for n, v, _c in rows if n == "(no style)"), None)
    print("\n%-16s %8s %10s" % ("preset", "luma", "vs bare"))
    for name, val, _n in rows:
        d = ("%+.1f" % (val - base)) if base is not None else "--"
        print("%-16s %8.1f %10s" % (name, val, d))

    styled = [(n, v) for n, v, _c in rows if n != "(no style)"]
    if len(styled) > 1:
        lo = min(styled, key=lambda r: r[1])
        hi = max(styled, key=lambda r: r[1])
        print("\nspread across presets: %.1f luma  (%s %.1f -> %s %.1f)"
              % (hi[1] - lo[1], lo[0], lo[1], hi[0], hi[1]))
        if hi[1] - lo[1] < 25:
            print("THESE ARE NOT FIVE LOOKS. Every preset lands within 25 luma of every "
                  "other, so the style choice is not reaching the picture's exposure.")
    print("\nimages: %s" % a.out)


if __name__ == "__main__":
    main()
