#!/usr/bin/env python3
"""Shot 080 once more, from the close frame the studio already composed for it.

The `generate` route hung: its keyframe render handed ComfyUI an absolute path to the portrait,
validation rejected the prompt, and the job waited on a history entry that will never exist.
That is being fixed separately.  The example does not need that route: the first pass composed
a proper close start frame for 080 (assets/anchor_shot_080.png) - person, wardrobe, place and
light together, from the plate and the pack - which is block 1 of the method as written.

Same corrected action as before (one that stays in frame), a new seed, no force-pick.
"""
import json
import os
import time
import urllib.request

API = "http://127.0.0.1:8777/api/film"
STUDIO = os.path.expanduser("~/shared/comfy-studio/studio")
FID = "the-method---worked-example"


def api(path, body):
    req = urllib.request.Request(API + path, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req, timeout=120))


def jobs():
    return json.load(urllib.request.urlopen(API + "/jobs", timeout=60)).get("jobs") or []


def wait(jid, budget=1200):
    t0 = time.time()
    while time.time() - t0 < budget:
        time.sleep(8)
        for j in jobs():
            if j.get("id") == jid and j.get("state") not in ("running", "queued"):
                return j
    return None


def film():
    return json.load(open(os.path.join(STUDIO, "films", FID, "film.json"), encoding="utf-8"))


cast_id = next(iter(film()["cast"]))
anchor = "file:" + os.path.join(STUDIO, "films", FID, "assets", "anchor_shot_080.png")
api("/editshot", {"film": FID, "shot": "080", "anchor": anchor, "duration": 4, "beats": [{
    "framing": "close-up", "move": "handheld, a faint float", "subject": cast_id,
    "action": "closes her eyes for a breath, opens them, and lifts her chin toward the gate",
    "background": "the wind dropping away",
    "dialogue": {"char": "", "line": "", "delivery": ""}, "transition_in": ""}],
    "sfx": "her breath, the wind dropping away, no music"})
api("/pick", {"film": FID, "shot": "080", "take": ""})
j = api("/make", {"film": FID, "shot": "080", "seed": 9092, "variants": 1})
done = wait(j["job"])
sh = film()["shots"]["080"]
tk = next((t for t in sh.get("takes") or [] if t["id"] == sh.get("picked")), None)
newest = (sh.get("takes") or [None])[-1]
idn = ((tk or newest) or {}).get("identity") or {}
print("080 job %s | picked=%s | newest %s->%s %s | qc %s" % (
    (done or {}).get("state"), bool(tk), idn.get("start"), idn.get("end"),
    idn.get("verdict_end"), ((tk or newest) or {}).get("qc", [])[:3]), flush=True)
print("RETAKE080 DONE", flush=True)
