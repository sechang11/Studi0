#!/usr/bin/env python3
"""studio/_tools/camrig.py - camera moves as reusable, parameterised shot templates.

THE GAP THIS CLOSES. Three engines make a picture out of a prompt; none of them makes a
picture out of a CAMERA. Every attempt to ask LTX or H3 for a specific camera move came
back as a drift, and the moves that finally worked were written by hand, frame by frame,
and then thrown away with the film. This makes them assets instead: named rigs, declared
parameters, documented ranges, saved presets, and a numeric report you can read before
spending a render.

A rig takes a STILL and produces a SHOT. Its plate is the shot's anchor image, so a cam
shot is specified exactly like any other shot in /film - the only difference is that its
motion comes from arithmetic rather than from a model, which means it is repeatable to the
pixel and free to re-render.

  camrig.py list
  camrig.py doc drive_by_brake
  camrig.py report drive_by_brake --preset sour_pickle
  camrig.py render drive_by_brake plate.png out.mp4 --preset sour_pickle --grip 3.4

Rig definitions - parameters, ranges, docs and presets - live in studio/camrigs/*.json.
The motion lives here. See studio/CAMRIG.md for the whole story.
"""
import json, math, os, subprocess, sys

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
STUDIO = os.path.dirname(HERE)
RIGDIR = os.path.join(STUDIO, "camrigs")


# ── rig definitions ─────────────────────────────────────────────────────────────────

def rig_names():
    if not os.path.isdir(RIGDIR):
        return []
    return sorted(f[:-5] for f in os.listdir(RIGDIR) if f.endswith(".json"))


def load_rig(name):
    p = os.path.join(RIGDIR, name + ".json")
    if not os.path.exists(p):
        raise KeyError("no camrig %r (have: %s)" % (name, ", ".join(rig_names())))
    return json.load(open(p, encoding="utf-8"))


def resolve(name, params=None, preset=None):
    """defaults <- preset <- explicit params. Unknown keys are an error, not a typo that
    silently does nothing - that is the failure mode this whole module exists to avoid."""
    rig = load_rig(name)
    out = {k: v["default"] for k, v in rig["params"].items()}
    if preset:
        if preset not in rig.get("presets", {}):
            raise KeyError("rig %r has no preset %r (have: %s)"
                           % (name, preset, ", ".join(rig.get("presets", {}))))
        out.update(rig["presets"][preset]["params"])
    for k, v in (params or {}).items():
        if k not in rig["params"]:
            raise KeyError("rig %r has no parameter %r" % (name, k))
        out[k] = v
    for k, spec in rig["params"].items():
        lo, hi = spec.get("min"), spec.get("max")
        if lo is not None and out[k] < lo:
            raise ValueError("%s=%s is below the usable minimum %s" % (k, out[k], lo))
        if hi is not None and out[k] > hi:
            raise ValueError("%s=%s is above the usable maximum %s" % (k, out[k], hi))
    return out


# ── the motion. Each rig returns per-frame (cx, cy, zoom, roll_deg, blur_px) ─────────
# All positions are in PLATE PIXELS, so a rig behaves identically whatever the plate's
# resolution - upscale the plate and scale the numbers with it.

def _drive_by_brake(p, fps):
    """A camera held out of a car window, pointed square at a facade, that a hard brake
    stops. Three phases fall out of one spring:

      1 CRUISE   the car travels, the operator is upright, framing moves steadily
      2 BRAKE    the car decelerates, the operator does NOT - inertia carries them
                 forward, so the FRAMING ACCELERATES while the car slows
      3 RELEASE  the operator is at maximum lean, which is where the restoring force is
                 largest, so the return is the fastest movement in the shot

    The operator is a mass on a spring driven by the pseudo-force of the car's own
    deceleration. Integrated at `substeps` per frame."""
    n = int(round(p["seconds"] * fps))
    sub = int(p["substeps"])
    dt = 1.0 / (fps * sub)
    w = 2 * math.pi * p["freq"]
    v = (p["x_rest"] - p["x_start"]) / (p["t_cruise"] + p["t_brake"] / 2.0)
    s = sdot = 0.0
    x_car = float(p["x_start"])
    frames = []
    for i in range(n * sub + 1):
        t = i * dt
        if t < p["t_cruise"]:
            a_car, v_car = 0.0, v
        elif t < p["t_cruise"] + p["t_brake"]:
            a_car = -v / p["t_brake"]
            v_car = max(0.0, v * (1 - (t - p["t_cruise"]) / p["t_brake"]))
        else:
            a_car, v_car = 0.0, 0.0
        sddot = -p["grip"] * a_car - w * w * s - 2 * p["damping"] * w * sdot
        sdot += sddot * dt
        s += sdot * dt
        x_car += v_car * dt
        if i % sub == 0:
            frames.append((x_car + s, s, sdot))
    out = []
    for i in range(n):
        x, s, sdot = frames[i]
        nxt = frames[min(i + 1, len(frames) - 1)][0]
        t = i / fps
        cy = p["y_center"] + p["dip"] * s + \
            p["breathe_px"] * math.sin(2 * math.pi * p["breathe_hz"] * t)
        # roll is normalised against window width: degrees per 5% of the window's width
        # of lean. Expressing it per-PIXEL is not scale invariant, and a plate upscaled x4
        # then rolls four times as hard for the same move - which is how a 7 degree tilt
        # got into a shot that wanted one.
        lean = s / (0.05 * p["win_w"])
        roll = p["roll_deg"] * (lean * 0.6 + sdot / (0.05 * p["win_w"]) * 0.012)
        out.append((x, cy, 1.0, roll, (nxt - x) * p["blur"],
                    {"lean": s, "lean_v": sdot}))
    return out


def _still_push(p, fps):
    """A slow push into a still. The honest answer whenever a shot must be pixel-faithful
    to a photograph - readable signage, a real person's face, a plate of food that must not
    morph. Nothing is invented; the frame simply closes in."""
    n = int(round(p["seconds"] * fps))
    out = []
    for i in range(n):
        u = i / max(1, n - 1)
        e = u * u * (3 - 2 * u) if p["ease"] else u
        z = p["zoom_start"] + (p["zoom_end"] - p["zoom_start"]) * e
        drift = p["drift_px"] * e
        out.append((p["cx"] + drift, p["cy"], z, 0.0, 0.0))
    return out


def _zoom_punch(p, fps):
    """A fast shove into the frame that overshoots and rings out - an impact, a slam, a
    title card landing. The hit is a step; everything after it is one damped spring, so the
    recovery cannot look unrelated to the blow."""
    n = int(round(p["seconds"] * fps))
    w = 2 * math.pi * p["freq"]
    out = []
    for i in range(n):
        t = i / fps
        if t < p["t_hit"]:
            u = t / p["t_hit"]
            z = p["z_start"] + (p["z_rest"] - p["z_start"]) * (u ** 3)
            osc = 0.0
        else:
            u = t - p["t_hit"]
            osc = math.sin(w * u) * math.exp(-p["damping"] * w * u)
            z = p["z_rest"] + p["overshoot"] * osc
        out.append((p["cx"] + p["shake"] * osc * 3.0,
                    p["cy"] - p["shake"] * osc * 4.0, z,
                    p["roll"] * osc, 0.0))
    return out


RIGS = {"drive_by_brake": _drive_by_brake, "still_push": _still_push,
        "zoom_punch": _zoom_punch}


# ── the compositor, shared by every rig ─────────────────────────────────────────────

def _grab(im, cx, cy, vw, vh, blur):
    """Crop the window, smeared horizontally by averaging offset copies.
    The ORIGIN is clamped, never the box: the crops must be identical in size or they
    cannot be averaged, and clamping the box silently changes its dimensions."""
    n = max(1, min(18, int(round(abs(blur) / 6.0))))
    acc = None
    for i in range(n):
        off = (i - (n - 1) / 2.0) * (blur / max(1, n))
        left = max(0, min(im.width - vw, int(round(cx + off - vw / 2))))
        top = max(0, min(im.height - vh, int(round(cy - vh / 2))))
        c = im.crop((left, top, left + vw, top + vh))
        acc = c if acc is None else Image.blend(acc, c, 1.0 / (i + 1))
    return acc


def report(name, params=None, preset=None, fps=24):
    """Framing velocity and lean over time, so a move can be judged as numbers before it
    costs a render. For drive_by_brake the test is written into the numbers: phase 2 must
    SUSTAIN a velocity above the cruise, and phase 3 must exceed phase 2."""
    p = resolve(name, params, preset)
    fr = RIGS[name](p, fps)
    rows = []
    for i in range(len(fr) - 1):
        t = i / fps
        vx = (fr[i + 1][0] - fr[i][0]) * fps
        rows.append({"t": round(t, 3), "x": round(fr[i][0], 1),
                     "vx": round(vx, 1), "zoom": round(fr[i][2], 4),
                     "roll": round(fr[i][3], 3)})
    return rows


def verdict(name, params=None, preset=None, fps=24):
    """The shape test, as numbers. For drive_by_brake the two rules are:
         phase 2 must SUSTAIN a framing velocity above the cruise
         phase 3 must EXCEED phase 2
    A setting that fails the second rule reads as a car accident - the surge collapses
    before the brake has finished and the shot jumps straight to the snap-back."""
    p = resolve(name, params, preset)
    fr = RIGS[name](p, fps)
    v = [(fr[i + 1][0] - fr[i][0]) * fps for i in range(len(fr) - 1)]
    tc = p.get("t_cruise")
    if tc is None:
        return {"rig": name, "note": "no phase test defined for this rig"}
    i0 = int(tc * fps)
    cruise = sum(v[max(1, i0 - 8):i0]) / max(1, len(v[max(1, i0 - 8):i0]))
    # THE BODY, not the framing. Through the brake the framing velocity still carries the
    # car's residual speed, so a framing-based comparison can never show phase 3 winning
    # even when the operator is unmistakably snapping back harder than they lurched.
    lv = [f[5]["lean_v"] for f in fr if len(f) > 5]
    surge = max(lv) if lv else max(v[i0:])
    ret = min(lv) if lv else min(v[i0:])
    peak_lean = max((f[5]["lean"] for f in fr if len(f) > 5), default=0.0)
    settled = all(abs(x) < abs(cruise) * 0.12 for x in v[int((p["seconds"] - 0.3) * fps):])
    frame_surge = max(v[i0:]) if v[i0:] else 0.0
    return {"rig": name, "preset": preset,
            "cruise_framing": round(cruise, 1),
            "framing_peak": round(frame_surge, 1),
            "peak_lean_px": round(peak_lean, 1),
            "body_out": round(surge, 1), "body_back": round(ret, 1),
            "phase2_ok": frame_surge > cruise * 1.08,
            "phase3_ok": abs(ret) > surge,   # the snap back beats the lurch out
            "settles_in_shot": settled,
            "pass": frame_surge > cruise * 1.08 and abs(ret) > surge}


def render(name, plate, out, params=None, preset=None, fps=24,
           out_w=1920, out_h=1080, tmp=None, crf=16):
    p = resolve(name, params, preset)
    fr = RIGS[name](p, fps)
    im = Image.open(plate).convert("RGB")
    tmp = tmp or "/tmp/camrig_%s" % os.getpid()
    os.makedirs(tmp, exist_ok=True)
    for f in os.listdir(tmp):
        os.remove(os.path.join(tmp, f))
    for i, fr_i in enumerate(fr):
        cx, cy, z, roll, blur = fr_i[:5]
        vw = max(8, int(round(p["win_w"] / z)))
        vh = max(8, int(round(p["win_h"] / z)))
        c = _grab(im, cx, cy, min(vw, im.width), min(vh, im.height), blur)
        if abs(roll) > 0.01:
            c = c.rotate(roll, resample=Image.BICUBIC)
        c.resize((out_w, out_h), Image.LANCZOS).save(
            os.path.join(tmp, "f%05d.png" % i))
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-framerate", str(fps),
                    "-i", os.path.join(tmp, "f%05d.png"), "-c:v", "libx264",
                    "-crf", str(crf), "-pix_fmt", "yuv420p", out], check=True)
    return {"rig": name, "preset": preset, "frames": len(fr), "params": p, "file": out}


# ── cli ─────────────────────────────────────────────────────────────────────────────

def _cli():
    a = sys.argv[1:]
    if not a or a[0] in ("-h", "--help"):
        print(__doc__)
        return
    cmd = a[0]
    if cmd == "list":
        for n in rig_names():
            r = load_rig(n)
            print("%-18s %s" % (n, r.get("summary", "")))
            for pn, ps in r.get("presets", {}).items():
                print("      preset %-14s %s" % (pn, ps.get("note", "")))
        return
    if cmd == "doc":
        r = load_rig(a[1])
        print("\n%s - %s\n" % (a[1], r.get("summary", "")))
        print(r.get("doc", "").strip(), "\n")
        print("%-13s %10s %10s %10s   %s" % ("PARAM", "DEFAULT", "MIN", "MAX", "WHAT IT DOES"))
        for k, v in r["params"].items():
            print("%-13s %10s %10s %10s   %s" % (k, v["default"], v.get("min", "-"),
                                                 v.get("max", "-"), v.get("doc", "")))
        if r.get("presets"):
            print("\nPRESETS")
            for pn, ps in r["presets"].items():
                print("  %-14s %s" % (pn, ps.get("note", "")))
                print("      %s" % json.dumps(ps["params"]))
        return
    kw, pos = {}, []
    i = 1
    while i < len(a):
        if a[i].startswith("--"):
            k = a[i][2:]
            v = a[i + 1]
            kw[k] = v
            i += 2
        else:
            pos.append(a[i]); i += 1
    preset = kw.pop("preset", None)
    fps = int(kw.pop("fps", 24))
    params = {k: (float(v) if v.replace(".", "", 1).replace("-", "", 1).isdigit() else v)
              for k, v in kw.items()}
    if cmd == "verdict":
        print(json.dumps(verdict(pos[0], params, preset, fps), indent=1))
        return
    if cmd == "report":
        rows = report(pos[0], params, preset, fps)
        print("   t      x        vx      zoom    roll")
        for r in rows[::max(1, len(rows) // 22)]:
            print("%6.2f %8.1f %8.1f %8.4f %7.3f"
                  % (r["t"], r["x"], r["vx"], r["zoom"], r["roll"]))
        return
    if cmd == "render":
        print(json.dumps(render(pos[0], pos[1], pos[2], params, preset, fps),
                         indent=1)[:900])
        return
    print("unknown command %r" % cmd)


if __name__ == "__main__":
    _cli()
