#!/usr/bin/env python3
"""080 retook after the festival swap and dressed Jin in red mid-chase.
Cloak on, retake, silks restored, re-assemble."""
import json, time, urllib.request

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
            return j.get("state") == "done"
        time.sleep(10)

def film():
    return json.load(open("studio/films/%s/film.json" % FILM))

post("/api/foundry/send", {"film": FILM, "characters": [
    {"id": "jin", "costume": "thief-cloak"}]})
print("jin back in the cloak", flush=True)

j = post("/api/film/takes", {"film": FILM, "shot": "080",
                             "engines": ["ltx"], "n": 1})
if not wait_job(j["job"], "080 retake"):
    raise SystemExit("retake failed")
sh = film()["shots"]["080"]
tid = sh["takes"][-1]["id"]
post("/api/film/pick", {"film": FILM, "shot": "080", "take": tid})
j = post("/api/film/vo", {"film": FILM, "shot": "080", "take": tid})
if wait_job(j["job"], "080 vo"):
    sh = film()["shots"]["080"]
    post("/api/film/pick", {"film": FILM, "shot": "080",
                            "take": sh["takes"][-1]["id"]})
j = post("/api/film/master", {"film": FILM, "shot": "080"})
wait_job(j["job"], "080 master")

post("/api/foundry/send", {"film": FILM, "characters": [
    {"id": "jin", "costume": "festival-silks"}]})
print("jin back in silks for the record", flush=True)

j = post("/api/film/assemble", {"film": FILM, "music": True})
wait_job(j["job"], "final assemble")
print("FIX080 COMPLETE", flush=True)
