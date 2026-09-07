#!/usr/bin/env python3
"""Retake the book's opening film by changing WORDS, then finish it.

The first pass of Lantern Night was read take by take (the strips, not the numbers alone):

  010  asked for a static market; the engine pushed in 278%.       -> give the camera a job: slow push in
  020  asked Terra to stand and look up; she walked at the lens.    -> "feet planted ... she does not walk"
  030  a stranger walked through the foreground of her line.        -> "the lane is empty, no one else"
  040  a close-up that CUT to a crowd scene after three seconds.    -> "the camera stays on her face"
  050  a wide, empty street the engine filled with people, twice.   -> a close-up insert whose start
                                                                       frame is a lantern, made by the
                                                                       studio's anime keyframe workflow

Every fix is the method's own rule (retry by words; one mover per beat; give the camera a job; the
start frame fixes what is in the shot).  The film negative also grows by the faults met, as the
rulebook says it should.  One shot renders at a time; the studio picks by its own rule; the finish
is filmic, 2x master, music bed; hero.json is rewritten for the book's figure builder.

    python3 studio/_tools/retake_hero.py                 # everything, ~25-35 min
    python3 studio/_tools/retake_hero.py --finish-only   # picks are in: assemble and write hero.json
"""
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.request

API = "http://127.0.0.1:8777/api/film"
ROOT = os.path.expanduser("~/shared/comfy-studio")
STUDIO = os.path.join(ROOT, "studio")
OUT = os.path.join(STUDIO, "samples", "docs", "book")
FID = "lantern-night"
TITLE = "Lantern Night"
NOTE_PREFIXES = ("ends closer", "sound borrowed", "words not in the picture", "camera:", "identity:",
                 "angle:", "the studio cut the take")


def api(path, body):
    req = urllib.request.Request(API + path, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req, timeout=120))


def jobs():
    return json.load(urllib.request.urlopen(API + "/jobs", timeout=60)).get("jobs") or []


def wait(jid, budget=3600, label=""):
    t0 = time.time()
    while time.time() - t0 < budget:
        time.sleep(8)
        for j in jobs():
            if j.get("id") == jid and j.get("state") not in ("running", "queued"):
                print("  %s %s: %s %s" % (label, jid, j.get("state"), (j.get("error") or "")[:200]), flush=True)
                for ln in j.get("log") or []:
                    print("     |", ln[:220], flush=True)
                return j
    print("  %s %s: TIMED OUT" % (label, jid), flush=True)
    return None


def quiet(budget=1800):
    t0 = time.time()
    while time.time() - t0 < budget:
        if not any(j.get("state") in ("running", "queued") for j in jobs()):
            return True
        time.sleep(8)
    return False


def film():
    return json.load(open(os.path.join(STUDIO, "films", FID, "film.json"), encoding="utf-8"))


def faults(take):
    return [q for q in (take.get("qc") or []) if not q.lower().startswith(NOTE_PREFIXES)]


# ---- the lantern start frame ------------------------------------------------------------
def lantern_frame():
    """A close-up of one lantern, through the studio's own anime keyframe workflow (the IPAdapter
    needs an image - the plate, at weight 0, so it says nothing).  Cached by path."""
    dest = os.path.join(STUDIO, "films", FID, "assets", "anchor_shot_050_lantern.png")
    if os.path.exists(dest):
        return dest
    sys.path.insert(0, os.path.join(ROOT, "scripts"))
    sys.path.insert(0, os.path.join(STUDIO, "_tools"))
    from comfy import run, set_path                      # noqa
    from epic import load_wf, ensure_local, HOST, COMFY  # noqa
    import post                                          # noqa
    print("== making room on the card for the still", flush=True)
    post.make_room()
    plate = os.path.join(STUDIO, "foundry", "places", "night-market", "night_detail.png")
    staged = "hero_lantern_ref.png"
    shutil.copy(plate, os.path.join(COMFY, "input", staged))
    wf = load_wf("22_anime_kf_ipadapter.json")
    set_path(wf, "2.inputs.image", staged)
    set_path(wf, "4.inputs.weight", 0.0)
    set_path(wf, "5.inputs.text",
             "close-up of a single red paper lantern hanging from a wooden night market stall, a candle "
             "flame glowing inside it, warm light through the paper, dark stalls softly blurred behind, "
             "night, nobody, no people, masterpiece, best quality, anime key visual, painterly light")
    set_path(wf, "6.inputs.text",
             "people, person, crowd, face, girl, boy, hands, text, watermark, signature, lowres, blurry, "
             "photorealistic, 3d, multiple views, nsfw")
    set_path(wf, "7.inputs.width", 1216)
    set_path(wf, "7.inputs.height", 832)
    set_path(wf, "8.inputs.seed", 4207)
    set_path(wf, "10.inputs.width", 1216)
    set_path(wf, "10.inputs.height", 832)
    set_path(wf, "11.inputs.filename_prefix", "claude-generated/films/%s/kf_050_lantern" % FID)
    _, outs = run(HOST, wf, quiet=True)
    if not outs:
        raise RuntimeError("the lantern still returned nothing")
    ensure_local(outs[0], dest)
    print("  lantern start frame:", dest, flush=True)
    return dest


# ---- the words ------------------------------------------------------------------------
def edits(lantern):
    f = film()

    def beat(sid, **kw):
        b = dict((f["shots"][sid].get("beats") or [{}])[0])
        b.update(kw)
        return [b]

    return [
        ("010", {"beats": beat("010", framing="wide establishing shot", move="slow push in",
                               action="paper lanterns sway gently on their strings over the empty stalls and "
                                      "their light flickers on the wet stone",
                               background="the lane empty, the banners still, warm light in every stall"),
                 "sfx": "the murmur of a night market far off, lanterns creaking on their strings, no music"}),
        ("020", {"beats": beat("020", framing="wide shot", move="static", subject="TERRA",
                               action="stands still in the middle of the lane, feet planted, and slowly lifts "
                                      "her eyes to the lanterns above her; she does not walk",
                               background="the empty stalls glow behind her, lantern light on her hair"),
                 "sfx": "the market murmur, closer; a lantern string creaking, no music"}),
        ("030", {"beats": beat("030", framing="medium shot", move="static", subject="TERRA",
                               action="lifts a paper lantern from the stall in both hands and turns it slowly, "
                                      "looking into its light",
                               background="the other lanterns glow softly behind her; the lane is empty, "
                                          "no one else in the frame"),
                 "sfx": "paper rustling, the market softer, no music"}),
        ("040", {"beats": beat("040", framing="close-up", move="static", subject="TERRA",
                               action="smiles slowly, and her eyes lift to follow a lantern drifting up above "
                                      "her; the camera stays on her face for the whole shot and never cuts away",
                               background="soft lantern bokeh behind her and nothing else, no one else"),
                 "sfx": "her breath, the market far away, no music"}),
        ("050", {"beats": beat("050", framing="close-up", move="static", subject="",
                               action="the candle flame inside the paper lantern gutters once and steadies",
                               background="the lantern's red paper glowing, darkness behind it"),
                 "anchor": "file:" + lantern, "no_people": True, "duration": 4,
                 "sfx": "the flame's faint hiss, the market murmur far away, no music"}),
    ]


def report_and_finish():
    f = film()
    ids = ["010", "020", "030", "040", "050"]
    report = {"film": FID, "title": TITLE, "shots": []}
    ok = True
    for sid in ids:
        sh = f["shots"][sid]
        tk = next((t for t in sh.get("takes") or [] if t["id"] == sh.get("picked")), None)
        row = {"shot": sid, "title": sh.get("title"), "picked": bool(tk), "takes": len(sh.get("takes") or [])}
        if tk:
            idn = tk.get("identity") or {}
            row.update({"engine": tk.get("engine"), "duration": tk.get("duration"),
                        "identity": [idn.get("start"), idn.get("end")],
                        "verdict": [idn.get("verdict_start"), idn.get("verdict_end")], "qc": tk.get("qc") or [],
                        "file": tk.get("file"), "take": tk.get("id")})
        else:
            ok = False
            row["faults"] = [t.get("qc") for t in sh.get("takes") or []][-2:]
        report["shots"].append(row)
        print("  %s %-14s %s" % (sid, sh.get("title"), json.dumps(row, ensure_ascii=False)[:300]), flush=True)
    if ok:
        print("== finish: filmic, 2x master, music bed", flush=True)
        a = api("/assemble", {"film": FID, "music": True, "grade": "filmic", "upscale": True})
        wait(a["job"], budget=2400, label="assemble")
        final = os.path.join(STUDIO, "films", FID, "assets", "film.mp4")
        if os.path.exists(final):
            r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-count_frames",
                                "-show_entries", "stream=width,height,nb_read_frames", "-of", "csv=p=0", final],
                               capture_output=True, text=True)
            report["film_mp4"] = r.stdout.strip()
            print("  film.mp4:", report["film_mp4"], flush=True)
    else:
        print("== NOT assembled: a shot still has no clean take", flush=True)
    os.makedirs(OUT, exist_ok=True)
    json.dump(report, open(os.path.join(OUT, "hero.json"), "w"), indent=1)
    print("RETAKE DONE", flush=True)


def main():
    if "--finish-only" in sys.argv:
        quiet()
        report_and_finish()
        return
    if not quiet():
        print("a film job is still running; not editing under it", flush=True)
        sys.exit(2)
    f = film()
    neg = f.get("negative") or ""
    grow = ["passers-by", "strangers", "extra people", "crowd", "a second person", "scene change",
            "cut to a different shot"]
    neg2 = ", ".join([neg] + [g for g in grow if g not in neg]) if neg else ", ".join(grow)
    print("== negative grows by the faults met:", neg2, flush=True)
    api("/edit", {"film": FID, "negative": neg2})
    lantern = lantern_frame()
    for sid, body in edits(lantern):
        body.update({"film": FID, "shot": sid})
        r = api("/editshot", body)
        print("  editshot %s -> %s" % (sid, str(r)[:120]), flush=True)
    for sid in ("010", "020", "030", "040", "050"):
        quiet()
        print("== make %s" % sid, flush=True)
        m = api("/make", {"film": FID, "shot": sid, "variants": 1})
        wait(m["job"], label="make %s" % sid)
        sh = film()["shots"][sid]
        for t in sh.get("takes") or []:
            print("   take %s%s faults=%d qc=%s" % (t["id"], " PICKED" if t["id"] == sh.get("picked") else "",
                                                     len(faults(t)), "; ".join(t.get("qc") or [])[:300]), flush=True)
    report_and_finish()


if __name__ == "__main__":
    main()
