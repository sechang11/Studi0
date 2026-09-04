"""The non-AI flow, end to end: scene with a place -> coverage -> a sentence per shot
and one spoken line -> Make every missing shot, then assemble."""
import json, os, time, urllib.request, urllib.error, subprocess
BASE = "http://127.0.0.1:8777"; C = os.path.expanduser("~/shared/comfy-studio/studio/foundry/characters/")
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
def meta(cid, voice="", vd=""):
    a = json.load(open(C + cid + "/asset.json")); c = a.get("compiled") or {}
    return {"name": a["name"], "clause": c.get("clause", ""), "short": c.get("short", "") or a["name"].split()[0],
            "sheet": C + cid + "/base_portrait.png", "portrait": C + cid + "/base_portrait.png", "voice": voice, "voice_desc": vd, "foundry": cid}
fid = "the-station-master"
try: get("/api/film/" + fid)
except urllib.error.HTTPError:
    fid = post("/api/film/new", {"title": "The Station Master", "look": "photoreal", "resolution": "auto"})["id"]
    post("/api/film/edit", {"film": fid, "logline": "The last train is late; the station master and a woman in a knit cap wait.",
                            "cast": {"MASTER": meta("station-master", "male_03_carter", "a deep, unhurried man's voice"),
                                     "INES": meta("ines-varga", "female_04_maya", "a low, dry woman's voice")}})
    sc = post("/api/film/scene", {"film": fid, "title": "platform, dusk"})["id"]
    post("/api/film/editscene", {"film": fid, "scene": sc, "weather": "overcast", "time_of_day": "dusk",
                                 "location": "a small-town railway platform under a long canopy at dusk",
                                 "ambience": "wind under the canopy, the departures board clicking, a distant train",
                                 "music": "cinematic, sparse piano, dusk, waiting, 64 bpm", "cast_present": ["MASTER", "INES"]})
    j = post("/api/film/coverage", {"film": fid, "scene": sc, "place": "station-dusk", "plate": "dusk_wide",
                                    "characters": [{"cast": "MASTER", "foundry": "station-master"}, {"cast": "INES", "foundry": "ines-varga"}]})
    wait(j["job"], 900, "coverage")
tree = get("/api/film/" + fid)
shots = {}
for s in tree["scenes"][0]["shots"]:
    d = get("/api/film/%s/shot/%s" % (fid, s["id"]))["shot"]; shots[d.get("title", "")] = d
EDITS = {
    "wide - establishing": ("the empty platform at dusk, the departures board flickering, lights far down the line", "", None, ["light", "traffic"]),
    "wide - MASTER and INES": ("stand under the canopy looking down the line for the train", "", ("MASTER", "It's late. It is never late.", "quiet"), ["light", "cloth"]),
    "medium - MASTER": ("checks his pocket watch and looks up", "look_up", None, ["light"]),
    "medium - INES": ("watches the empty track without moving", "", ("INES", "It'll come. They always do.", "low, dry"), ["light", "cloth"]),
    "insert - detail": ("the departures board, the bench, wind moving a scrap of paper along the platform", "", None, ["light", "cloth"]),
}
for title, (action, motion, line, amb) in EDITS.items():
    sh = shots.get(title)
    if not sh: log("no shot", title); continue
    b = sh["beats"][0]; b["action"] = action; b["motion"] = motion; b["ambient"] = amb
    b["dialogue"] = {"char": line[0], "line": line[1], "delivery": line[2]} if line else {}
    post("/api/film/editshot", {"film": fid, "shot": sh["id"], "beats": [b], "duration": 6})
log("edits done; Make every missing shot, then assemble")
j = post("/api/film/makeall", {"film": fid, "assemble": True}); wait(j["job"], 3000, "makeall")
F = os.path.expanduser("~/shared/comfy-studio/studio/films/%s/assets/film.mp4" % fid)
if os.path.exists(F): subprocess.run(["python3", "/tmp/sheet.py", F, "/tmp/sheet_station.jpg", "2", "8"])
log("FILM5 DONE")
