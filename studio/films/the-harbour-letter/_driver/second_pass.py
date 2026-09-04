#!/usr/bin/env python3
"""Second pass on THE HARBOUR LETTER, from what the contact sheets showed.

- The "harbour" place is a stone arch bridge over slow water in fog. The prose
  said boats and a quay, and LTX rewrote the plate into a marina. Words that
  contradict the anchor are instructions to leave it; the scene and every beat
  now describe what is actually in the plate.
- Shot F's walk regenerated her at four times the size. The end state now
  clamps the change of scale and stands her at the depth that size implies;
  the shot is pinned again with the feet free (a walk moves them).
- Shot D is rendered again from the corrected prose; the rest keep their takes.
Then assemble, contact sheets, verify-page entries, and the library build.
"""
import json, os, subprocess, time, urllib.request

BASE = "http://127.0.0.1:8777"
FID = "the-harbour-letter"


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


def post(p, b):
    r = urllib.request.Request(BASE + p, json.dumps(b).encode(), {"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(r, timeout=90))


def get(p):
    return json.load(urllib.request.urlopen(BASE + p, timeout=60))


def wait(jid, limit, label=""):
    t0, seen = time.time(), 0
    while time.time() - t0 < limit:
        me = [x for x in get("/api/film/jobs")["jobs"] if x["id"] == jid]
        if me:
            lg = me[0].get("log") or []
            for l in lg[seen:]:
                log("   |", l)
            seen = len(lg)
            if me[0]["state"] != "running":
                log("  %s -> %s %s (%.0fs)" % (label or jid, me[0]["state"], me[0].get("error") or "", time.time() - t0))
                return me[0]
        time.sleep(8)
    log("  %s still running after %ds" % (label or jid, limit))


def idle():
    t0 = time.time()
    while time.time() - t0 < 1500:
        if not any(j["state"] == "running" for j in get("/api/film/jobs")["jobs"]):
            return
        time.sleep(10)


idle()
log("no jobs running; fixing the film")
tree = get("/api/film/" + FID)
sc2 = tree["scenes"][1]["id"]
post("/api/film/edit", {"film": FID, "logline": "A letter found in the rain is carried to the old bridge at dawn."})
post("/api/film/editscene", {"film": FID, "scene": sc2, "title": "the old bridge, dawn",
                             "location": "an old stone arch bridge over slow water, thick fog, first light",
                             "ambience": "slow water under the arch, drips from the stone, a distant bird"})
shots = {}
for sc in tree["scenes"]:
    for s in sc["shots"]:
        d = get("/api/film/%s/shot/%s" % (FID, s["id"]))["shot"]
        shots[d.get("title") or s["id"]] = d

def edit_beats(key, **changes):
    sh = shots[key]
    b = sh["beats"][0]
    b.update({k: v for k, v in changes.items() if k not in ("sfx",)})
    body = {"film": FID, "shot": sh["id"], "beats": [b]}
    if "sfx" in changes:
        body["sfx"] = changes["sfx"]
    post("/api/film/editshot", body)
    log("edited", key)

edit_beats("D", action="first light comes through the fog under the old stone bridge, the slow river moving beneath the arch",
           background="mist drifts across the water", ambient=["water", "light"],
           sfx="slow water under the arch, drips from the stone, a distant bird")
edit_beats("E", action="turns from the water to face the camera, fog behind him",
           background="fog drifts under the arch behind him", sfx="slow water, his coat moving")
edit_beats("F", action="walks a few steps closer along the bank, the letter in her hand",
           background="the fog thins over the water behind her", sfx="her boots on wet grass, slow water")
edit_beats("G", action="his expression softens as he sees her, a small nod",
           background="fog over the water behind him")
edit_beats("H", action="sunlight spreads across the wet stone of the old bridge, the river glittering below",
           background="ripples cross the slow water")

# D again, from the corrected prose
sid = shots["D"]["id"]
j = post("/api/film/takes", {"film": FID, "shot": sid, "engines": ["ltx"], "n": 1})
wait(j["job"], 900, "ltx D")
d = get("/api/film/%s/shot/%s" % (FID, sid))["shot"]
newest = sorted(d["takes"], key=lambda t: t["id"])[-1]
post("/api/film/pick", {"film": FID, "shot": sid, "take": newest["id"]})
log("D picked", newest["id"], "qc:", newest.get("qc"))

# F again: a walk, feet free, scale clamped by the new geometry
sid = shots["F"]["id"]
change = "the subject has walked a few steps closer to the camera along the bank, a little larger in the frame, still holding the letter"
j = post("/api/film/pinpreview", {"film": FID, "shot": sid, "change": change, "seconds": 8, "hold_feet": False})
r = wait(j["job"], 400, "pinpreview F")
pv = (r or {}).get("result") or {}
log("F preview:", {k: pv.get(k) for k in ("rate", "ok", "longest")})
force = (not pv.get("ok")) and pv.get("rate", 0) >= 0.0015
j = post("/api/film/pin", {"film": FID, "shot": sid, "change": change, "seconds": 8, "hold_feet": False, "force": force})
wait(j["job"], 1200, "pin F")

# assemble
j = post("/api/film/assemble", {"film": FID, "music": True})
wait(j["job"], 1500, "assemble")
tree = get("/api/film/" + FID)
log("film:", tree.get("film"))

# sheets
FD = os.path.expanduser("~/shared/comfy-studio/studio/films/the-harbour-letter")
subprocess.run(["python3", "/tmp/sheet.py", os.path.join(FD, "assets/film.mp4"), "/tmp/sheet_film.jpg", "2", "8"])
for key in ("B", "D", "F"):
    sh = get("/api/film/%s/shot/%s" % (FID, shots[key]["id"]))["shot"]
    tk = next((t for t in sh["takes"] if t["id"] == sh.get("picked")), None)
    if tk:
        subprocess.run(["python3", "/tmp/sheet.py", os.path.join(FD, tk["file"]), "/tmp/sheet_%s2.jpg" % key, "1", "8"])
subprocess.run(["python3", "/tmp/verify_entries.py"])
log("starting the library build")
subprocess.Popen("setsid nohup python3 /tmp/build_library.py > /tmp/library_build.log 2>&1 < /dev/null &", shell=True)
log("FIX DONE")
