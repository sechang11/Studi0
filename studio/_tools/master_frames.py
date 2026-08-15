#!/usr/bin/env python3
"""studio/_tools/master_frames.py - the master-frame consistency kit (Phase 6).

    python3 studio/_tools/master_frames.py crop --hero H.png --frame ms --anchor 0.5 0.4 --out k.png
    python3 studio/_tools/master_frames.py outpaint --src H.png --left 512 --right 512 \
            --prompt "the same street continuing" --out wide.png
    python3 studio/_tools/master_frames.py edit --ref H.png --prompt "the same woman seen \
            from behind, same alley, same lighting" --out reverse.png
    python3 studio/_tools/master_frames.py chain --start a.png --end b.png \
            --motion "she turns and walks away" --seconds 4 --out clip.mp4
    python3 studio/_tools/master_frames.py scene --spec scene.json --out DIR

THE LOCAL ANSWER TO MULTI-SHOT CONSISTENCY. Seedance-class models hold a scene together
by attending across shots; nothing on this box can do that in one pass. What this box
CAN do is refuse to re-roll the world: render ONE hero still per scene and DERIVE every
other angle from its pixels -

    crop      a framing is a window on the master, not a new generation. Deterministic,
              free, and the background cannot drift because it is the same background.
    outpaint  when the story needs more world than the hero holds, extend the master
              once (28_flux_outpaint) and crop from the wider plate thereafter.
    edit      a genuinely new angle re-uses the master as a REFERENCE
              (14_qwen_edit_ref): the prompt asks for the change, the pixels vote for
              everything else.
    chain     first->last i2v (50_ltx_first_last): a shot that ENDS on the next shot's
              keyframe. Cuts land on matching frames because the match was rendered in.

`scene` composes them: spec -> keyframes -> chained clips, everything derived from one
master. Keyframes come back at the workflow's native sizes; the film cutter already
scales, so derivation order is the contract here, not resolution.
"""
import argparse
import json
import os
import shutil
import sys

TOOLS = os.path.dirname(os.path.abspath(__file__))
STUDIO = os.path.dirname(TOOLS)
ROOT = os.path.dirname(STUDIO)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
sys.path.insert(0, STUDIO)
os.environ.setdefault("COMFY_HOST", "127.0.0.1:8188")

from comfy import run, set_path            # noqa: E402
from engine import load_wf, HOST           # noqa: E402

COMFY = os.environ.get("COMFY_ROOT", os.path.expanduser("~/ComfyUI"))

# Named framings as window FRACTIONS of the master's height (width follows 16:9).
# A crop is a zoom: cu takes 35% of the plate's height around the anchor.
FRAMES = {"cu": 0.35, "mcu": 0.5, "ms": 0.68, "mws": 0.85, "ws": 1.0}


def stage(src, name):
    dst = os.path.join(COMFY, "input", name)
    shutil.copy(src, dst)
    return name


def collect(outs, dst, exts):
    for o in outs or []:
        if str(o).lower().endswith(exts):
            p = os.path.join(COMFY, "output", o)
            if os.path.exists(p):
                shutil.copy(p, dst)
                return dst
    return None


def crop(hero, frame, anchor, out, min_px=640):
    """A framing as a window on the master. Refuses a window that would upscale past
    breaking: a cu on a 704px plate is 246px tall, and pretending that is a keyframe
    would trade the consistency win for mush - outpaint or edit is the honest move."""
    from PIL import Image
    im = Image.open(hero).convert("RGB")
    W, H = im.size
    f = FRAMES.get(frame, None)
    if f is None:
        f = float(frame)
    ch = int(H * f)
    cw = int(ch * W / H)
    ax, ay = anchor
    cx, cy = int(ax * W), int(ay * H)
    x0 = max(0, min(W - cw, cx - cw // 2))
    y0 = max(0, min(H - ch, cy - ch // 2))
    win = im.crop((x0, y0, x0 + cw, y0 + ch))
    if ch < min_px and f < 0.999:
        print(f"  ! {frame} window is {ch}px tall on a {H}px plate - upscaling x"
              f"{min_px/ch:.1f} will be soft; consider edit for this framing",
              file=sys.stderr)
    win = win.resize((W, H), Image.LANCZOS)
    win.save(out)
    print(f"crop {frame} @({ax:.2f},{ay:.2f}) -> {out}")
    return out


def outpaint(src, prompt, out, left=0, right=0, top=0, bottom=0, seed=8080):
    wf = load_wf("28_flux_outpaint.json")
    set_path(wf, "5.inputs.image", stage(src, "claude_outpaint_src.png"))
    for k, v in (("left", left), ("right", right), ("top", top), ("bottom", bottom)):
        set_path(wf, f"6.inputs.{k}", int(v))
    set_path(wf, "7.inputs.text", prompt)
    set_path(wf, "11.inputs.seed", seed)
    set_path(wf, "13.inputs.filename_prefix", "claude-generated/master-frames/outpaint")
    _, outs = run(HOST, wf, quiet=True)
    got = collect(outs, out, (".png", ".webp", ".jpg"))
    print(f"outpaint +{left}/+{right}px -> {got or 'FAILED'}")
    return got


def edit(ref, prompt, out, ref2=None, seed=7):
    """A new angle that keeps the world: the master is the reference, the prompt asks
    only for the change. ref2 (optional) carries a second identity - the character
    sheet - so person and place survive the same pass."""
    wf = load_wf("14_qwen_edit_ref.json")
    set_path(wf, "8.inputs.image", stage(ref, "claude_mf_ref1.png"))
    set_path(wf, "9.inputs.image",
             stage(ref2 or ref, "claude_mf_ref2.png"))
    set_path(wf, "10.inputs.prompt", prompt)
    set_path(wf, "13.inputs.seed", seed)
    set_path(wf, "15.inputs.filename_prefix", "claude-generated/master-frames/edit")
    _, outs = run(HOST, wf, quiet=True)
    got = collect(outs, out, (".png", ".webp", ".jpg"))
    print(f"edit -> {got or 'FAILED'}")
    return got


def chain(start, end, motion, seconds, out, seed=1234):
    """First->last i2v: the shot ends ON the next shot's keyframe, so the cut lands on
    a matching frame by construction. Frame math is the LTX law: 8n+1 at 24fps."""
    frames = int(round(float(seconds) * 24 / 8)) * 8 + 1
    wf = load_wf("50_ltx_first_last.json")
    set_path(wf, "8.inputs.image", stage(start, "ltx_start.png"))
    set_path(wf, "58.inputs.image", stage(end, "ltx_end.png"))
    set_path(wf, "10.inputs.text", motion or "gentle natural motion")
    set_path(wf, "20.inputs.length", frames)
    set_path(wf, "21.inputs.frames_number", frames)
    set_path(wf, "21.inputs.frame_rate", 24)
    set_path(wf, "32.inputs.noise_seed", seed)
    set_path(wf, "43.inputs.filename_prefix", "claude-generated/master-frames/chain")
    _, outs = run(HOST, wf, quiet=True)
    got = collect(outs, out, (".mp4", ".webm", ".mov"))
    print(f"chain {seconds}s ({frames}f) -> {got or 'FAILED'}")
    return got


def scene(spec_path, outdir):
    """One master, many shots. Spec:
    {"hero": "path.png",
     "beats": [{"id": "b1", "frame": "ws"},
               {"id": "b2", "frame": "cu", "anchor": [0.5, 0.35]},
               {"id": "b3", "edit": "the same street seen from the far end"},
               {"id": "b4", "outpaint": {"right": 512, "prompt": "..."}, "frame": "ms"}],
     "chain": [{"from": "b1", "to": "b2", "motion": "she steps forward", "seconds": 4}]}
    Keyframes land in <outdir>/keys/, chained clips in <outdir>/clips/."""
    spec = json.load(open(spec_path, encoding="utf-8"))
    hero = spec["hero"]
    keys = os.path.join(outdir, "keys")
    clipd = os.path.join(outdir, "clips")
    os.makedirs(keys, exist_ok=True)
    os.makedirs(clipd, exist_ok=True)
    plate = hero
    made = {}
    for i, b in enumerate(spec["beats"]):
        dst = os.path.join(keys, b["id"] + ".png")
        if b.get("outpaint"):
            op = b["outpaint"]
            wide = os.path.join(keys, b["id"] + "_plate.png")
            got = outpaint(plate, op.get("prompt", ""), wide,
                           left=op.get("left", 0), right=op.get("right", 0),
                           top=op.get("top", 0), bottom=op.get("bottom", 0),
                           seed=8080 + i)
            if got:
                plate = got          # later crops see the wider world
        if b.get("edit"):
            got = edit(plate, b["edit"], dst, ref2=b.get("ref2"), seed=7 + i)
        else:
            got = crop(plate, b.get("frame", "ws"),
                       tuple(b.get("anchor", [0.5, 0.5])), dst)
        if got:
            made[b["id"]] = got
    for i, c in enumerate(spec.get("chain", [])):
        a, z = made.get(c["from"]), made.get(c["to"])
        if not (a and z):
            print(f"  ! chain {c['from']}->{c['to']}: missing keyframe", file=sys.stderr)
            continue
        chain(a, z, c.get("motion", ""), float(c.get("seconds", 4)),
              os.path.join(clipd, f"{c['from']}__{c['to']}.mp4"), seed=1234 + i)
    print(f"scene: {len(made)} keyframes, {len(spec.get('chain', []))} chained clips "
          f"-> {outdir}")
    return 0


def main():
    ap = argparse.ArgumentParser(description="Master-frame consistency kit: one hero "
                                             "still per scene, every angle derived.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("crop")
    c.add_argument("--hero", required=True)
    c.add_argument("--frame", default="ms")
    c.add_argument("--anchor", nargs=2, type=float, default=[0.5, 0.5])
    c.add_argument("--out", required=True)
    o = sub.add_parser("outpaint")
    o.add_argument("--src", required=True)
    o.add_argument("--prompt", required=True)
    for side in ("left", "right", "top", "bottom"):
        o.add_argument("--" + side, type=int, default=0)
    o.add_argument("--seed", type=int, default=8080)
    o.add_argument("--out", required=True)
    e = sub.add_parser("edit")
    e.add_argument("--ref", required=True)
    e.add_argument("--ref2")
    e.add_argument("--prompt", required=True)
    e.add_argument("--seed", type=int, default=7)
    e.add_argument("--out", required=True)
    h = sub.add_parser("chain")
    h.add_argument("--start", required=True)
    h.add_argument("--end", required=True)
    h.add_argument("--motion", default="")
    h.add_argument("--seconds", type=float, default=4.0)
    h.add_argument("--seed", type=int, default=1234)
    h.add_argument("--out", required=True)
    s = sub.add_parser("scene")
    s.add_argument("--spec", required=True)
    s.add_argument("--out", required=True)
    a = ap.parse_args()
    if a.cmd == "crop":
        return 0 if crop(a.hero, a.frame, tuple(a.anchor), a.out) else 1
    if a.cmd == "outpaint":
        return 0 if outpaint(a.src, a.prompt, a.out, a.left, a.right, a.top, a.bottom,
                             a.seed) else 1
    if a.cmd == "edit":
        return 0 if edit(a.ref, a.prompt, a.out, a.ref2, a.seed) else 1
    if a.cmd == "chain":
        return 0 if chain(a.start, a.end, a.motion, a.seconds, a.out, a.seed) else 1
    if a.cmd == "scene":
        return scene(a.spec, a.out)


if __name__ == "__main__":
    sys.exit(main())
