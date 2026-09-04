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
j = post("/api/film/quickstart", {"title": "School Morning", "look": "anime", "resolution": "auto", "place": "school-morning",
                                  "plate": "day_wide", "characters": ["renji", "kite-seller"]})
fid = j["id"]; log("quickstart", {k: j.get(k) for k in ("id", "scene", "job", "cast")}); wait(j["job"], 900, "coverage")
tree = get("/api/film/" + fid); cast = list(tree["cast"].keys()); A, B = cast[0], cast[1]
post("/api/film/editscene", {"film": fid, "scene": tree["scenes"][0]["id"], "music": "anime score, bright piano and strings, morning, school, 96 bpm"})
shots = {}
for s in tree["scenes"][0]["shots"]:
    d = get("/api/film/%s/shot/%s" % (fid, s["id"]))["shot"]; shots[d.get("title", "")] = d
EDITS = {
    "wide - establishing": ("the courtyard in the morning, petals drifting, long shadows", "", None, ["leaves", "light"]),
    "wide - %s and %s" % (A, B): ("stand by the bicycle rack, she is teasing him", "", (B, "You're late again.", "teasing"), ["leaves", "light"]),
    "medium - %s" % A: ("looks up at the sky and sighs", "look_up", None, ["leaves", "light"]),
    "medium - %s" % B: ("laughs, hands on her hips", "laugh", (B, "Every single morning.", "bright"), ["light"]),
    "insert - detail": ("the bicycle rack and the courtyard wall, petals falling", "", None, ["leaves", "light"]),
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
if os.path.exists(F): subprocess.run(["python3", "/tmp/sheet.py", F, "/tmp/sheet_school.jpg", "2", "8"])
tree = get("/api/film/" + fid)
for s in tree["scenes"][0]["shots"]:
    d = get("/api/film/%s/shot/%s" % (fid, s["id"]))["shot"]; tk = next((t for t in d["takes"] if t["id"] == d.get("picked")), None)
    print("  ", s["id"], d.get("title"), "|", (tk or {}).get("engine"), "| qc:", (tk or {}).get("qc"))
log("FILM7 DONE")
