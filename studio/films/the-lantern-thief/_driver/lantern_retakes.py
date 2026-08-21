#!/usr/bin/env python3
"""Retake pass for THE LANTERN THIEF: the three Hoshi shots that predate the
creature-clause fix, plus the Keeper two-shot whose wide anchor swallowed the
framing. Waits for the main driver, retakes, re-picks, re-VOs, re-masters,
then re-assembles."""
import json, os, sys, time, urllib.request

BASE = "http://127.0.0.1:8777"
FILM = "the-lantern-thief"

def post(p, b):
    r = urllib.request.Request(BASE + p, json.dumps(b).encode(),
                               {"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(r, timeout=300))

def get(p):
    return json.load(urllib.request.urlopen(BASE + p, timeout=60))

def wait_job(jid, label):
    while True:
        j = get("/api/film/job/" + jid)
        j = j.get("job", j)
        if j.get("state") != "running":
            print("  [%s] %s %s" % (label, j.get("state"), j.get("error") or ""),
                  flush=True)
            if j.get("state") == "failed":
                for line in (j.get("log") or [])[-8:]:
                    print("    |", line, flush=True)
            return j.get("state") == "done"
        time.sleep(10)

def film():
    return json.load(open("studio/films/%s/film.json" % FILM))

# wait for the main driver's assembly
while True:
    log = open("/tmp/lantern_v2.log").read()
    if "FILM COMPLETE" in log:
        break
    if ": take failed" in log or ": vo failed" in log or ": master failed" in log \
            or "assemble failed" in log:
        sys.exit("main driver failed - fix that first")
    time.sleep(15)
print("main driver complete, retaking", flush=True)

# t3 reframed intimate: a close two-shot the wide anchor cannot swallow
f = film()
sh = f["shots"]["160"]
b = sh["beats"][0]
b["framing"] = "close-up"
b["action"] = ("THE_KEEPER's weathered, deeply wrinkled face close in the fog "
               "beside the altar as he bows slightly to JIN, whose white hair "
               "edges the close foreground as she ducks her head, caught")
post("/api/film/editshot", {"film": FILM, "shot": "160", "beats": sh["beats"]})
print("160 reframed close", flush=True)

# d1 reframed subject-led: the dawn wide let the scene prior invent a bystander
f = film()
sh = f["shots"]["180"]
b = sh["beats"][0]
b["framing"] = "medium shot"
b["move"] = "static"
b["action"] = ("JIN, in red and gold festival silks, stands on a step-stool "
               "hanging small paper lanterns along the lantern stall, dawn "
               "light washing the street behind her")
post("/api/film/editshot", {"film": FILM, "shot": "180", "beats": sh["beats"]})
print("180 reframed subject-led", flush=True)

# d3 too: the fox vanished into the dawn-market prior
f = film()
sh = f["shots"]["200"]
b = sh["beats"][0]
b["framing"] = "close-up"
b["action"] = ("HOSHI, a small auburn fox spirit, perches close on the stall's "
               "wooden roof edge batting at a hanging paper charm with one paw, "
               "his twin ember-tipped tails swinging together for balance")
post("/api/film/editshot", {"film": FILM, "shot": "200", "beats": sh["beats"]})
print("200 reframed close", flush=True)

RETAKES = ["050", "080", "120", "160", "180", "200"]
for sid in RETAKES:
    sh = film()["shots"][sid]
    j = post("/api/film/takes", {"film": FILM, "shot": sid,
                                 "engines": ["ltx"], "n": 1})
    print("%s (%s): retake job %s" % (sid, sh["title"], j["job"]), flush=True)
    if not wait_job(j["job"], "%s retake" % sid):
        print("%s retake failed - keeping the old take" % sid, flush=True)
        continue
    sh = film()["shots"][sid]
    tid = sh["takes"][-1]["id"]
    post("/api/film/pick", {"film": FILM, "shot": sid, "take": tid})
    if sh["beats"][0]["dialogue"]["line"]:
        j = post("/api/film/vo", {"film": FILM, "shot": sid, "take": tid})
        if wait_job(j["job"], "%s vo" % sid):
            sh = film()["shots"][sid]
            post("/api/film/pick", {"film": FILM, "shot": sid,
                                    "take": sh["takes"][-1]["id"]})
    j = post("/api/film/master", {"film": FILM, "shot": sid})
    wait_job(j["job"], "%s master" % sid)

j = post("/api/film/assemble", {"film": FILM, "music": True})
wait_job(j["job"], "re-assemble")
print("RETAKES COMPLETE", flush=True)
