#!/usr/bin/env python3
"""Does a better start frame make a better local take?  Measure it before paying for one.

The argument in docs/WHERE-WE-STAND.md: the whole video path is image-to-video, so the start
frame decides most of what reads as quality, and a frontier IMAGE costs a fraction of a frontier
video second.  Spend there, not on video.  That is a hypothesis until a shot has been rendered
both ways and scored - and this is the harness that does it.

    ~/ComfyUI/venv/bin/python3 hybrid_frame_test.py --film encyclopedia-check --shot 160 \\
        --frame /path/to/better_start_frame.png [--seed 4242] [--label frontier]

WHAT IT DOES.  Records the shot's current anchor.  Renders the shot once from that anchor at a
fixed seed (the control), then swaps the anchor to `file:<frame>` and renders again at the same
seed, then puts the anchor back.  Both takes land in the film as ordinary takes - poster, strip,
identity, QC, angle, drift - and neither is picked, so the film's delivered cut does not move.
The report is the delta, take against take, on the numbers the studio already trusts:

    identity start / end    CLIP against the pack portrait on the matte-found head
    qc                      the fault list the studio would show a person
    angle, drift            where the camera stood and how far the scene moved

A frame that does not move those numbers did not earn its price, however it looks in isolation.

THE STAND-IN.  Until a frontier frame exists, --sharpen renders the control's own anchor through
the studio's 2x master and back down, and tests THAT as the "better" frame.  It is not a
frontier frame; it is the same frame with more detail, which is the cheapest honest version of
the question "does the start frame's quality reach the take at all".  If even that moves
nothing, a bought frame is unlikely to.

Runs against the live studio over HTTP, one shot at a time, and refuses to start while any
film job is running - film.json is read, modified and written back, and a concurrent make
would race it.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.request

ROOT = os.path.expanduser("~/shared/comfy-studio")
STUDIO = os.path.join(ROOT, "studio")
API = os.environ.get("STUDIO_API", "http://127.0.0.1:8777/api/film")
OUT = os.path.join(STUDIO, "samples", "hybrid")
PY = os.path.expanduser("~/ComfyUI/venv/bin/python3")


def api(path, body=None):
    req = urllib.request.Request(API + path, method="POST" if body is not None else "GET",
                                 data=json.dumps(body).encode() if body is not None else None,
                                 headers={"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req, timeout=60))


def jobs_running():
    d = api("/jobs")
    return [j for j in (d.get("jobs") or []) if j.get("state") in ("running", "queued")]


def wait_job(jid, budget=1800):
    t0 = time.time()
    while time.time() - t0 < budget:
        time.sleep(6)
        for j in (api("/jobs").get("jobs") or []):
            if j.get("id") == jid and j.get("state") not in ("running", "queued"):
                return j
    return None


def film_path(fid):
    return os.path.join(STUDIO, "films", fid, "film.json")


def load(fid):
    return json.load(open(film_path(fid), encoding="utf-8"))


def save(fid, data):
    json.dump(data, open(film_path(fid), "w", encoding="utf-8"), indent=1, ensure_ascii=False)


def new_take(fid, shid, before_ids):
    sh = load(fid)["shots"][shid]
    fresh = [t for t in sh.get("takes") or [] if t["id"] not in before_ids]
    return fresh[-1] if fresh else None


def render(fid, shid, seed):
    before = {t["id"] for t in load(fid)["shots"][shid].get("takes") or []}
    j = api("/make", {"film": fid, "shot": shid, "seed": seed, "variants": 1})
    done = wait_job(j["job"])
    if not done:
        return None, "job %s did not finish" % j["job"]
    t = new_take(fid, shid, before)
    return t, (done.get("error") or done.get("result") or "")


def sharpen(src, dst):
    """the control's own anchor through the 2x master and back to its size: same frame, more detail"""
    sys.path.insert(0, os.path.join(STUDIO, "_tools"))
    import post  # noqa: E402
    from PIL import Image
    tmp_v = dst + "_1f.mp4"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-loop", "1", "-i", src, "-t", "0.1",
                    "-r", "10", "-pix_fmt", "yuv420p", tmp_v], capture_output=True)
    up, info = post.upscale(tmp_v, dst + "_up.mp4", scale=2)
    if not up:
        return None, info
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", up, "-frames:v", "1", dst + "_big.png"],
                   capture_output=True)
    w, h = Image.open(src).size
    Image.open(dst + "_big.png").convert("RGB").resize((w, h), Image.LANCZOS).save(dst)
    for p in (tmp_v, up, dst + "_big.png"):
        try:
            os.remove(p)
        except OSError:
            pass
    return dst, info


def summarise(t):
    idn = t.get("identity") or {}
    return {"take": t["id"], "seed": t.get("seed"), "engine": t.get("engine"),
            "identity_start": idn.get("start"), "identity_end": idn.get("end"),
            "verdict_start": idn.get("verdict_start"), "verdict_end": idn.get("verdict_end"),
            "qc": t.get("qc") or [], "angle": (t.get("angle_measured") or {}).get("label")
            if isinstance(t.get("angle_measured"), dict) else t.get("angle_measured"),
            "drift": t.get("drift"), "file": t.get("file")}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--film", required=True)
    ap.add_argument("--shot", required=True)
    ap.add_argument("--frame", help="the candidate start frame (a frontier render, or anything)")
    ap.add_argument("--sharpen", action="store_true",
                    help="no frame yet: test the control's own anchor through the 2x master")
    ap.add_argument("--seed", type=int, default=4242)
    ap.add_argument("--label", default=None)
    a = ap.parse_args()
    if not a.frame and not a.sharpen:
        sys.exit("give --frame PATH or --sharpen")
    if jobs_running():
        sys.exit("a film job is running - this edits film.json and would race it")
    os.makedirs(OUT, exist_ok=True)
    fid, shid = a.film, a.shot
    data = load(fid)
    sh = data["shots"].get(shid)
    if not sh:
        sys.exit("no shot %s in %s" % (shid, fid))
    orig_anchor = sh.get("anchor") or "scene"
    control_frame = orig_anchor[5:] if orig_anchor.startswith("file:") else None
    label = a.label or ("sharpened" if a.sharpen else "frame")
    print("%s/%s  anchor today: %s" % (fid, shid, orig_anchor), flush=True)

    frame = a.frame
    if a.sharpen:
        if not control_frame or not os.path.exists(control_frame):
            sys.exit("--sharpen needs a file: anchor to sharpen; this shot's is %s" % orig_anchor)
        frame = os.path.join(OUT, "%s_%s_sharpened.png" % (fid, shid))
        got, info = sharpen(control_frame, frame)
        if not got:
            sys.exit("could not sharpen the anchor: %s" % info)
        print("  stand-in frame: %s (%s)" % (frame, info), flush=True)
    frame = os.path.abspath(frame)
    if not os.path.exists(frame):
        sys.exit("no frame at %s" % frame)

    backup = film_path(fid) + ".hybrid_bak"
    shutil.copy(film_path(fid), backup)
    report = {"film": fid, "shot": shid, "seed": a.seed, "control_anchor": orig_anchor,
              "candidate_frame": frame, "label": label}
    try:
        print("  rendering the control (seed %d) ..." % a.seed, flush=True)
        t0, note0 = render(fid, shid, a.seed)
        report["control"] = summarise(t0) if t0 else {"error": note0}
        print("  control: %s" % json.dumps(report["control"])[:200], flush=True)

        d = load(fid)
        d["shots"][shid]["anchor"] = "file:" + frame
        save(fid, d)
        print("  rendering from the candidate frame (same seed) ...", flush=True)
        t1, note1 = render(fid, shid, a.seed)
        report["candidate"] = summarise(t1) if t1 else {"error": note1}
        print("  candidate: %s" % json.dumps(report["candidate"])[:200], flush=True)
    finally:
        # the anchor goes back whatever happened, and the pick is never moved
        d = load(fid)
        d["shots"][shid]["anchor"] = orig_anchor
        save(fid, d)
        try:
            os.remove(backup)
        except OSError:
            pass

    c, k = report.get("control") or {}, report.get("candidate") or {}
    if c.get("identity_start") is not None and k.get("identity_start") is not None:
        report["delta"] = {
            "identity_start": round(k["identity_start"] - c["identity_start"], 3),
            "identity_end": round((k.get("identity_end") or 0) - (c.get("identity_end") or 0), 3),
            "qc_faults": len(k.get("qc") or []) - len(c.get("qc") or [])}
        print("\n  %-16s %10s %10s %8s" % ("", "control", label, "delta"))
        for key in ("identity_start", "identity_end"):
            print("  %-16s %10.3f %10.3f %+8.3f" % (key, c[key] or 0, k[key] or 0,
                                                    report["delta"][key]))
        print("  %-16s %10d %10d %+8d" % ("qc faults", len(c.get("qc") or []),
                                          len(k.get("qc") or []), report["delta"]["qc_faults"]))
    out = os.path.join(OUT, "%s_%s_%s_%d.json" % (fid, shid, label, a.seed))
    json.dump(report, open(out, "w"), indent=1)
    print("\n  -> %s" % out)
    print("HYBRID DONE", flush=True)


if __name__ == "__main__":
    main()
