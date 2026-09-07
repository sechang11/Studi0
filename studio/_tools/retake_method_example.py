#!/usr/bin/env python3
"""The worked example, corrected by its own rules, then re-made.

What the first pass taught, read off the strips and the QC:

  060  the scene anchor already stands her at the steps, so "walks in from the left" cannot
       happen - the anchor fixes where a shot STARTS.  And a burst of sparkles arrived unasked
       in the last two seconds: the anime engine's prior, and nothing in the negative forbade
       it.  Section H says the negative grows in the fault's own words.  So it does.
  080  "starts up the steps" in a close-up: the engine followed the action and abandoned the
       framing, and the last frame is the back of her head - which the scorer, correctly, does
       not recognise.  Framing and action must agree (block 3).  The close-up keeps an action
       that stays in frame, and takes its own generated close keyframe instead of continuing
       from 070's drifted profile (block 1).

Both shots are un-picked and re-made once at a new seed.  Nothing is force-picked afterwards:
the fixed studio picks a clean take or leaves the shot for a person.
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


def wait(jid, budget=1800):
    t0 = time.time()
    while time.time() - t0 < budget:
        time.sleep(8)
        for j in jobs():
            if j.get("id") == jid and j.get("state") not in ("running", "queued"):
                return j
    return None


def film():
    return json.load(open(os.path.join(STUDIO, "films", FID, "film.json"), encoding="utf-8"))


f = film()
cast_id = next(iter(f["cast"]))
print("negative grows: the sparkles get named", flush=True)
api("/edit", {"film": FID, "negative": "lowres, bad anatomy, extra limbs, text, watermark, nsfw, "
                                       "magic sparkles, glowing particles, light burst, "
                                       "transformation effect"})

print("060: an action the anchor allows - she is already at the steps", flush=True)
# the studio composes a start frame per shot from the plate and the pack; the first pass left
# 060's at assets/anchor_shot_060.png, and the single-shot make wants it named, not "scene"
anchor_060 = "file:" + os.path.join(STUDIO, "films", FID, "assets", "anchor_shot_060.png")
api("/editshot", {"film": FID, "shot": "060", "anchor": anchor_060, "duration": 6, "beats": [{
    "framing": "wide shot", "move": "static", "subject": cast_id,
    "action": "stands at the foot of the shrine steps and slowly raises her eyes to the gate",
    "background": "wind moves the cedar branches; a single bell far off",
    "dialogue": {"char": "", "line": "", "delivery": ""}, "transition_in": ""}],
    "sfx": "wind in the cedars, a single distant bell, no music"})

print("080: a close-up whose action stays in frame, from its own close keyframe", flush=True)
api("/editshot", {"film": FID, "shot": "080", "anchor": "generate", "duration": 4,
    "keyframe_prompt": "a close-up of her face at the foot of the shrine steps at dawn, eyes "
                       "closed, cedar trunks soft behind her, cool dawn light",
    "beats": [{
    "framing": "close-up", "move": "handheld, a faint float", "subject": cast_id,
    "action": "closes her eyes for a breath, opens them, and lifts her chin toward the gate",
    "background": "the wind dropping away",
    "dialogue": {"char": "", "line": "", "delivery": ""}, "transition_in": ""}],
    "sfx": "her breath, the wind dropping away, no music"})

for sid in ("060", "080"):
    api("/pick", {"film": FID, "shot": sid, "take": ""})
    j = api("/make", {"film": FID, "shot": sid, "seed": 9091, "variants": 1})
    done = wait(j["job"])
    sh = film()["shots"][sid]
    tk = next((t for t in sh.get("takes") or [] if t["id"] == sh.get("picked")), None)
    newest = (sh.get("takes") or [None])[-1]
    idn = ((tk or newest) or {}).get("identity") or {}
    print("  %s job %s | picked=%s | newest identity %s->%s %s | qc %s" % (
        sid, (done or {}).get("state"), bool(tk), idn.get("start"), idn.get("end"),
        idn.get("verdict_end"), ((tk or newest) or {}).get("qc", [])[:3]), flush=True)
print("RETAKE DONE", flush=True)
