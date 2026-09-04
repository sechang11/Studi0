#!/usr/bin/env python3
"""THE LAST BOAT - coverage, then dialogue. The one capability tonight's films
had not touched: spoken lines through on-screen mouths (LTX speaks; photoreal
lip sync is measured). Coverage makes the scene's shots from selectors; the
director's only work here is the lines. Synthetic voices only."""
import json, os, subprocess, time, urllib.request, urllib.error

BASE = "http://127.0.0.1:8777"
C = os.path.expanduser("~/shared/comfy-studio/studio/foundry/characters/")


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


def post(p, b):
    r = urllib.request.Request(BASE + p, json.dumps(b).encode(), {"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(r, timeout=90))


def get(p):
    return json.load(urllib.request.urlopen(BASE + p, timeout=60))


def wait(jid, limit=1800, label=""):
    t0, seen = time.time(), 0
    while time.time() - t0 < limit:
        me = [x for x in get("/api/film/jobs")["jobs"] if x["id"] == jid]
        if me:
            lg = me[0].get("log") or []
            for l in lg[seen:]:
                log("   |", l[:170])
            seen = len(lg)
            if me[0]["state"] != "running":
                log("  %s -> %s %s (%.0fs)" % (label, me[0]["state"], me[0].get("error") or "", time.time() - t0))
                return me[0]
        time.sleep(8)


def meta(cid, voice, voice_desc):
    a = json.load(open(C + cid + "/asset.json")); c = a.get("compiled") or {}
    return {"name": a["name"], "clause": c.get("clause", ""), "short": c.get("short", "") or a["name"].split()[0],
            "sheet": C + cid + "/base_portrait.png", "portrait": C + cid + "/base_portrait.png",
            "voice": voice, "voice_desc": voice_desc, "foundry": cid}


fid = "the-last-boat"
try:
    get("/api/film/" + fid); log("film exists")
except urllib.error.HTTPError:
    fid = post("/api/film/new", {"title": "The Last Boat", "look": "photoreal", "resolution": "auto"})["id"]
    post("/api/film/edit", {"film": fid, "logline": "Two people wait on a fog-bound boat for a boat that is not coming.",
                            "cast": {"INES": meta("ines-varga", "female_04_maya", "a low, dry woman's voice, unhurried"),
                                     "TOMAS": meta("tomas-reyl", "male_05_samuel", "a warm, gravelly older man's voice")}})
    sc = post("/api/film/scene", {"film": fid, "title": "deck, night"})["id"]
    post("/api/film/editscene", {"film": fid, "scene": sc, "weather": "fog", "time_of_day": "night",
                                 "location": "the deck of a small fishing boat in a fog-bound harbour at night, sodium lamps on the quay",
                                 "ambience": "water against the hull, rope creaking, a foghorn far off",
                                 "music": "cinematic ambient, low cello, fog, night, patient, 60 bpm",
                                 "cast_present": ["INES", "TOMAS"]})
    j = post("/api/film/coverage", {"film": fid, "scene": sc, "place": "harbour-night", "plate": "night_reverse",
                                    "prop": "oil-lantern",
                                    "characters": [{"cast": "INES", "foundry": "ines-varga"},
                                                   {"cast": "TOMAS", "foundry": "tomas-reyl"}]})
    wait(j["job"], 900, "coverage")

tree = get("/api/film/" + fid)
shots = {}
for s in tree["scenes"][0]["shots"]:
    d = get("/api/film/%s/shot/%s" % (fid, s["id"]))["shot"]
    shots[d.get("title", "")] = d

LINES = {
    "wide - INES and TOMAS": ("TOMAS", "Last boat's not coming back tonight, Ines.", "quiet, matter of fact",
                              "stand at the rail looking out into the fog; he speaks without turning"),
    "medium - INES": ("INES", "Then we wait with the light on.", "low, steady",
                      "looks out at the fog and answers without looking at him"),
    "medium - TOMAS": ("TOMAS", "Aye. We wait.", "warm, almost a laugh",
                       "nods slowly, the smile coming"),
}
for title, (who, line, deliv, action) in LINES.items():
    sh = shots.get(title)
    if not sh:
        log("no shot titled", title); continue
    b = sh["beats"][0]
    b["action"] = action
    b["dialogue"] = {"char": who, "line": line, "delivery": deliv}
    b["motion"] = ""
    post("/api/film/editshot", {"film": fid, "shot": sh["id"], "beats": [b], "duration": 6})
    log("dialogue on", sh["id"], who, "-", line)

wide = shots.get("wide - establishing")
if wide:
    b = wide["beats"][0]; b["action"] = "the fog-bound deck at night, the lamps hazing, the water moving under the hull"
    post("/api/film/editshot", {"film": fid, "shot": wide["id"], "beats": [b]})
ins = shots.get("insert - detail")
if ins:
    b = ins["beats"][0]; b["action"] = "coiled rope and the lantern on the wet deck, fog drifting past"
    post("/api/film/editshot", {"film": fid, "shot": ins["id"], "beats": [b]})

# compile check on a dialogue shot: the line must be in the prose
d = get("/api/film/%s/compile/%s" % (fid, shots["medium - INES"]["id"]))["compiled"]["ltx"]
log("INES compile:", d["prompt"][:300])
for w in d.get("warnings", []):
    log("  WARN", w[:140])

j = post("/api/film/draftall", {"film": fid, "engines": ["ltx"]}); wait(j["job"], 2400, "draftall")
tree = get("/api/film/" + fid)
for s in tree["scenes"][0]["shots"]:
    dd = get("/api/film/%s/shot/%s" % (fid, s["id"]))["shot"]
    if dd.get("takes") and not dd.get("picked"):
        post("/api/film/pick", {"film": fid, "shot": s["id"], "take": dd["takes"][0]["id"]})
j = post("/api/film/assemble", {"film": fid, "music": True}); wait(j["job"], 1500, "assemble")
F = os.path.expanduser("~/shared/comfy-studio/studio/films/the-last-boat/assets/film.mp4")
subprocess.run(["python3", "/tmp/sheet.py", F, "/tmp/sheet_boat.jpg", "2", "8"])
# is there speech? loudness of the dialogue shots' takes vs the empty wide
for title in ("wide - establishing", "medium - INES", "medium - TOMAS"):
    sh = get("/api/film/%s/shot/%s" % (fid, shots[title]["id"]))["shot"]
    tk = next((t for t in sh["takes"] if t["id"] == sh.get("picked")), None)
    if tk:
        p = os.path.expanduser("~/shared/comfy-studio/studio/films/the-last-boat/" + tk["file"])
        out = subprocess.run(["ffmpeg", "-v", "error", "-i", p, "-af", "volumedetect", "-f", "null", "-"],
                             capture_output=True, text=True).stderr
        mean = [l for l in out.splitlines() if "mean_volume" in l]
        log(title, "|", (mean[0].split("]")[-1].strip() if mean else "no audio stats"))
log("BOAT DONE")
