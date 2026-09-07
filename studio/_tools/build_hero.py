#!/usr/bin/env python3
"""The book's opening film, built by the method through the editor's own routes.

Terra at the night market. quickstart makes the scene and its five coverage shots from the plate
and her pack; four are re-written as one-beat shots with sound, one keeps its detail; the studio
makes them, picks by its own rule, and the finish applies the filmic look, the 2x master and a
music bed.  Every frame in chapter 0 of the book comes from this film, and every later chapter
explains one of the pieces that made it.

    python3 build_hero.py            # ~35-45 minutes on the card
"""
import json
import os
import subprocess
import sys
import time
import urllib.request

API = "http://127.0.0.1:8777/api/film"
STUDIO = os.path.expanduser("~/shared/comfy-studio/studio")
OUT = os.path.join(STUDIO, "samples", "docs", "book")
TITLE = "Lantern Night"


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
                print("  %s %s: %s %s" % (label, jid, j.get("state"), (j.get("error") or "")[:160]), flush=True)
                return j
    print("  %s %s: TIMED OUT" % (label, jid), flush=True)
    return None


def film(fid):
    return json.load(open(os.path.join(STUDIO, "films", fid, "film.json"), encoding="utf-8"))


def quiet(budget=1800):
    """no film job running - editing film.json under a running job races its writes (a 500)"""
    t0 = time.time()
    while time.time() - t0 < budget:
        if not any(j.get("state") in ("running", "queued") for j in jobs()):
            return True
        time.sleep(8)
    return False


def main():
    os.makedirs(OUT, exist_ok=True)
    resume = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("-") else None
    if resume:
        fid = resume
        f = film(fid)
        scid = f["scenes"][0]["id"]
        print("== resuming %s (scene %s); waiting for its coverage job" % (fid, scid), flush=True)
    else:
        print("== quickstart: Terra at the night market", flush=True)
        q = api("/quickstart", {"title": TITLE, "look": "anime", "characters": ["terra"],
                                "place": "night-market", "plate": "night_wide",
                                "scene_title": "lantern night"})
        fid, scid = q["id"], q["scene"]
        print("  film %s scene %s anchor job %s" % (fid, scid, q.get("job")), flush=True)
    # the coverage job composes anchors and writes film.json as it goes: edit only when it is done
    quiet()
    f = film(fid)
    cast_id = next((k for k, v in (f.get("cast") or {}).items()
                    if (v or {}).get("foundry") == "terra"), None) or next(iter(f["cast"]))
    print("  cast %r" % cast_id, flush=True)
    api("/edit", {"film": fid, "negative": "lowres, bad anatomy, extra limbs, text, watermark, nsfw, "
                                           "magic sparkles, glowing particles, light burst"})
    api("/editscene", {"film": fid, "scene": scid, "time_of_day": "night",
                       "ambience": "the murmur of a night market, paper lanterns creaking on their "
                                   "strings, a distant flute, footsteps on wet stone",
                       "music": "soft koto and wind chimes, a night market, gentle and warm",
                       "cast_present": [cast_id]})

    f = film(fid)
    ids = [sid for sc in f["scenes"] if sc["id"] == scid for sid in sc["shots"]]
    print("  coverage shots:", ids, flush=True)
    # the coverage grid, re-written as the story - keep each shot's framing and move, change what
    # happens in it, and write the sound; one beat per shot because a face is in most of them
    plan = {
        # the anchor check said the plate has no crowd, and 010 and 050 are no-people shots: a
        # named crowd there is either invented (a fault) or drifted toward - so nothing is named
        # that the picture does not already hold (method rule: the start frame fixes what begins)
        0: dict(title="the market", dur=6,
                action="paper lanterns sway over the stalls and steam drifts from a food stall",
                bg="lantern light on wet stone, banners stirring, a flute somewhere",
                sfx="the murmur of a night market, lanterns creaking, a distant flute, no music"),
        1: dict(title="Terra arrives", dur=5,
                action="stands among the stalls under the lanterns and slowly looks up at them",
                bg="the crowd moves past behind her, lantern light on her hair",
                sfx="the market murmur, closer; a lantern string creaking, no music"),
        2: dict(title="the lantern", dur=5,
                action="lifts a paper lantern from the stall in both hands and turns it slowly, "
                       "looking into its light",
                bg="the stallkeeper's hands and the other lanterns soft behind",
                line="I remember this place.",
                sfx="paper rustling, the market softer, no music"),
        3: dict(title="the smile", dur=4,
                action="smiles, and her eyes follow a lantern rising into the dark above her",
                bg="bokeh of lanterns, the crowd far away",
                sfx="her breath, the market far away, no music"),
        4: dict(title="a flame", dur=4,
                action="a single candle flame gutters inside a paper lantern and steadies",
                bg="the lantern's red paper, the dark stalls behind",
                sfx="the flame's faint hiss, the market murmur, no music"),
    }
    for i, sid in enumerate(ids[:5]):
        sh = f["shots"][sid]
        p = plan.get(i)
        if not p:
            continue
        beats = sh.get("beats") or [{}]
        b = dict(beats[0])
        b["action"] = p["action"]
        b["background"] = p["bg"]
        b["motion"] = ""
        if p.get("line"):
            b["dialogue"] = {"char": cast_id, "line": p["line"], "delivery": "quiet, half to herself"}
        else:
            b["dialogue"] = {"char": "", "line": "", "delivery": ""}
        api("/editshot", {"film": fid, "shot": sid, "title": p["title"], "duration": p["dur"],
                          "beats": [b], "sfx": p["sfx"]})
        print("  %s %-14s %ds  %s / %s" % (sid, p["title"], p["dur"], b.get("framing"), b.get("move")), flush=True)

    print("== make every shot", flush=True)
    m = api("/makeall", {"film": fid, "assemble": False})
    wait(m["job"], label="makeall")
    f = film(fid)
    report = {"film": fid, "title": TITLE, "shots": []}
    ok = True
    for sid in ids[:5]:
        sh = f["shots"][sid]
        tk = next((t for t in sh.get("takes") or [] if t["id"] == sh.get("picked")), None)
        row = {"shot": sid, "title": sh.get("title"), "picked": bool(tk), "takes": len(sh.get("takes") or [])}
        if tk:
            idn = tk.get("identity") or {}
            row.update({"engine": tk.get("engine"), "duration": tk.get("duration"),
                        "identity": [idn.get("start"), idn.get("end")],
                        "verdict": [idn.get("verdict_start"), idn.get("verdict_end")], "qc": tk.get("qc") or [],
                        "file": tk.get("file")})
        else:
            ok = False
            row["faults"] = [t.get("qc") for t in sh.get("takes") or []][-2:]
        report["shots"].append(row)
        print("  %s %-14s %s" % (sid, sh.get("title"), json.dumps(row, ensure_ascii=False)[:240]), flush=True)
    if ok:
        print("== finish: filmic, 2x master, music bed", flush=True)
        a = api("/assemble", {"film": fid, "music": True, "grade": "filmic", "upscale": True})
        wait(a["job"], budget=2400, label="assemble")
        final = os.path.join(STUDIO, "films", fid, "assets", "film.mp4")
        if os.path.exists(final):
            r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-count_frames",
                                "-show_entries", "stream=width,height,nb_read_frames", "-of", "csv=p=0", final],
                               capture_output=True, text=True)
            report["film_mp4"] = r.stdout.strip()
            print("  film.mp4:", report["film_mp4"], flush=True)
    else:
        print("== NOT assembled: a shot has no clean take (not force-picked)", flush=True)
    json.dump(report, open(os.path.join(OUT, "hero.json"), "w"), indent=1)
    print("HERO DONE", flush=True)


if __name__ == "__main__":
    main()
