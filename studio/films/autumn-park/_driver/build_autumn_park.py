"""The whole non-AI path: new film from the form (quickstart) -> a sentence per shot and
two lines -> Make every missing shot, then assemble."""
import json, os, time, urllib.request, subprocess
BASE = "http://127.0.0.1:8777"
def log(*a): print(time.strftime("%H:%M:%S"), *a, flush=True)
def post(p, b):
    r = urllib.request.Request(BASE + p, json.dumps(b).encode(), {"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(r, timeout=90))
def get(p): return json.load(urllib.request.urlopen(BASE + p, timeout=60))
def wait(jid, limit=3000, label=""):
    t0, seen = time.time(), 0
    while time.time() - t0 < limit:
        me = [x for x in get("/api/film/jobs")["jobs"] if x["id"] == jid]
        if me:
            for l in (me[0].get("log") or [])[seen:]: log("   |", l[:170])
            seen = len(me[0].get("log") or [])
            if me[0]["state"] != "running": log("  %s -> %s %s (%.0fs)" % (label, me[0]["state"], me[0].get("error") or "", time.time() - t0)); return me[0]
        time.sleep(8)
j = post("/api/film/quickstart", {"title": "Autumn Park", "look": "photoreal", "resolution": "auto", "place": "autumn-park",
                                  "plate": "day_wide", "characters": ["ines-varga", "station-master"]})
fid = j["id"]; log("quickstart", {k: j.get(k) for k in ("id", "scene", "job", "cast")}); wait(j["job"], 900, "coverage")
tree = get("/api/film/" + fid); cast = list(tree["cast"].keys()); A, B = cast[0], cast[1]
post("/api/film/editscene", {"film": fid, "scene": tree["scenes"][0]["id"], "music": "cinematic, autumn, solo clarinet and strings, overcast, 62 bpm"})
shots = {}
for s in tree["scenes"][0]["shots"]:
    d = get("/api/film/%s/shot/%s" % (fid, s["id"]))["shot"]; shots[d.get("title", "")] = d
EDITS = {
    "wide - establishing": ("the park path under grey sky, leaves drifting down", "", None, ["leaves", "light"]),
    "wide - %s and %s" % (A, B): ("stand on the path a few steps apart, both looking at the trees", "", (A, "You kept the watch.", "quiet"), ["leaves"]),
    "medium - %s" % A: ("turns her head toward him", "look_off", None, ["leaves", "light"]),
    "medium - %s" % B: ("looks down at the watch in his hand and nods once", "nod", (B, "It still runs. That's something.", "low"), ["leaves"]),
    "insert - detail": ("wet leaves on the path, a bench, the wind moving the branches", "", None, ["leaves", "cloth"]),
}
for title, (action, motion, line, amb) in EDITS.items():
    sh = shots.get(title)
    if not sh: log("no shot", title, "| have:", list(shots.keys())); continue
    b = sh["beats"][0]; b["action"] = action; b["motion"] = motion; b["ambient"] = amb
    b["dialogue"] = {"char": line[0], "line": line[1], "delivery": line[2]} if line else {}
    post("/api/film/editshot", {"film": fid, "shot": sh["id"], "beats": [b], "duration": 6})
log("edits done; make every missing shot, then assemble")
j = post("/api/film/makeall", {"film": fid, "assemble": True}); wait(j["job"], 3000, "makeall")
F = os.path.expanduser("~/shared/comfy-studio/studio/films/%s/assets/film.mp4" % fid)
if os.path.exists(F): subprocess.run(["python3", "/tmp/sheet.py", F, "/tmp/sheet_park.jpg", "2", "8"])
tree = get("/api/film/" + fid)
for s in tree["scenes"][0]["shots"]:
    d = get("/api/film/%s/shot/%s" % (fid, s["id"]))["shot"]; tk = next((t for t in d["takes"] if t["id"] == d.get("picked")), None)
    print("  ", s["id"], d.get("title"), "|", (tk or {}).get("engine"), "| qc:", (tk or {}).get("qc"))
log("FILM8 DONE")
