#!/usr/bin/env python3
"""HARBOUR NIGHT - a third short, cinematic, with the two-shot in a story.

Ines Varga and Tomas Reyl, both new tonight. Six shots, two scenes, about 40s.
Rules as workflow: anchors checked before rendering; pins for in-place motion
only; a second character as a compositor layer; props as set dressing at a
distance; ambient named on every beat. Resumable.
"""
import json, os, sys, time, urllib.request, urllib.error

BASE = "http://127.0.0.1:8777"
ROOT = os.path.expanduser("~/shared/comfy-studio")
CHARS = os.path.join(ROOT, "studio", "foundry", "characters")
PLACES = os.path.join(ROOT, "studio", "foundry", "places")
TITLE = "Harbour Night"


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


def post(p, b, timeout=90):
    r = urllib.request.Request(BASE + p, json.dumps(b).encode(), {"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(r, timeout=timeout))


def get(p, timeout=60):
    return json.load(urllib.request.urlopen(BASE + p, timeout=timeout))


def wait(jid, limit=1500, label=""):
    t0, seen = time.time(), 0
    while time.time() - t0 < limit:
        me = [x for x in get("/api/film/jobs")["jobs"] if x["id"] == jid]
        if me:
            lg = me[0].get("log") or []
            for l in lg[seen:]:
                log("   |", l[:200])
            seen = len(lg)
            if me[0]["state"] != "running":
                log("  %s -> %s %s (%.0fs)" % (label or jid, me[0]["state"], me[0].get("error") or "", time.time() - t0))
                return me[0]
        time.sleep(8)
    log("  %s still running after %ds" % (label or jid, limit))


def char_meta(cid):
    a = json.load(open(os.path.join(CHARS, cid, "asset.json"), encoding="utf-8"))
    c = a.get("compiled") or {}
    return {"name": a.get("name", cid), "clause": c.get("clause", ""),
            "short": c.get("short", "") or a.get("name", cid).split()[0],
            "sheet": os.path.join(CHARS, cid, "base_portrait.png"),
            "portrait": os.path.join(CHARS, cid, "base_portrait.png"), "voice": "", "voice_desc": ""}


def first_plate(place, prefer):
    d = os.path.join(PLACES, place)
    ps = sorted(f for f in os.listdir(d) if f.endswith(".png") and not f.endswith("_depth.png"))
    for p in prefer:
        if p + ".png" in ps:
            return p
    return ps[0][:-4]


SCENES = [
    {"key": "S1", "title": "harbour, night",
     "location": "the deck of a small weathered fishing boat in a fog-bound harbour at night, sodium lamps on the quay",
     "time_of_day": "night", "weather": "fog", "ambience": "water against the hull, rope creaking, a foghorn far off",
     "music": "cinematic ambient, low cello, fog, night, patient, 60 bpm", "cast_present": ["INES", "TOMAS"]},
    {"key": "S2", "title": "station, dusk",
     "location": "a small-town railway platform under a long canopy at dusk, a departures board",
     "time_of_day": "dusk", "weather": "overcast", "ambience": "wind under the canopy, a distant train, the board clicking",
     "music": "cinematic, sparse piano, dusk, departure, 66 bpm", "cast_present": ["INES"]},
]

SHOTS = [
    {"key": "A", "scene": "S1", "kind": "ltx", "duration": 8, "no_people": True,
     "plate": ("harbour-night", ["night_wide", "late_night_wide"]),
     "sfx": "water against the hull, rope creaking, a foghorn far off",
     "beats": [{"framing": "wide establishing shot", "move": "static", "subject": "",
                "action": "fog drifts over the black water between the moored boats, the sodium lamps hazing, ropes and rigging swaying",
                "background": "the water moves under the hulls", "motion": "", "ambient": ["water", "light", "cloth"], "dialogue": {}}]},
    {"key": "B", "scene": "S1", "kind": "pin", "duration": 6,
     "compose": {"character": "ines-varga", "place": "harbour-night", "plate": ("harbour-night", ["night_wide", "late_night_wide"]),
                 "stand": 0.35, "cx": 0.40, "view": "turn_front",
                 "props": [{"id": "oil-lantern", "stand": 0.30, "cx": 0.58}]},
     "pin": "the subject has raised one arm and is pointing out across the water",
     "sfx": "water, rope, her coat moving",
     "beats": [{"framing": "wide shot", "move": "static", "subject": "INES",
                "action": "stands on the deck by the lantern and points out across the water",
                "background": "fog drifts between the boats", "motion": "gesture", "ambient": ["water", "light"], "dialogue": {}}]},
    {"key": "C", "scene": "S1", "kind": "ltx", "duration": 8,
     "compose": {"character": "ines-varga", "place": "harbour-night", "plate": ("harbour-night", ["night_reverse", "night_wide"]),
                 "stand": 0.32, "cx": 0.36, "view": "turn_front_three_quarter",
                 "props": [{"character": "tomas-reyl", "view": "turn_front_three_quarter", "stand": 0.32, "cx": 0.62}]},
     "sfx": "water against the hull, his low laugh, rope",
     "beats": [{"framing": "medium two-shot", "move": "static", "subject": "INES",
                "action": "and the fisherman beside her stand on the deck facing each other, she speaks and he nods",
                "background": "fog and lamplight over the water behind them", "motion": "nod", "ambient": ["water", "light", "cloth"], "dialogue": {}}]},
    {"key": "D", "scene": "S1", "kind": "pin", "duration": 6,
     "compose": {"character": "tomas-reyl", "place": "harbour-night", "plate": ("harbour-night", ["night_detail", "night_wide"]),
                 "stand": 0.25, "cx": 0.50, "view": "turn_front",
                 "props": [{"id": "field-radio", "stand": 0.20, "cx": 0.68}]},
     "pin": "the subject has crouched down low, knees bent, one hand reaching toward the radio on the deck",
     "sfx": "the radio crackling, water, his boots on the deck",
     "beats": [{"framing": "medium shot", "move": "static", "subject": "TOMAS",
                "action": "crouches to the field radio on the deck", "background": "fog over the water behind him",
                "motion": "crouch", "ambient": ["water"], "dialogue": {}}]},
    {"key": "E", "scene": "S2", "kind": "ltx", "duration": 6, "no_people": True,
     "plate": ("station-dusk", ["dusk_wide", "night_wide"]),
     "sfx": "wind under the canopy, the departures board clicking, a distant train",
     "beats": [{"framing": "wide establishing shot", "move": "static", "subject": "",
                "action": "the empty platform at dusk, the departures board flickering, lights far down the line",
                "background": "the canopy lamps flicker", "motion": "", "ambient": ["light", "traffic"], "dialogue": {}}]},
    {"key": "F", "scene": "S2", "kind": "ltx", "duration": 6,
     "compose": {"character": "ines-varga", "place": "station-dusk", "plate": ("station-dusk", ["dusk_wide", "night_wide"]),
                 "stand": 0.22, "cx": 0.42, "view": "turn_side"},
     "sfx": "wind, her coat, the board clicking",
     "beats": [{"framing": "medium shot", "move": "static", "subject": "INES",
                "action": "stands on the platform looking down the line, her coat moving in the wind",
                "background": "the lamps flicker along the canopy", "motion": "look_off", "ambient": ["cloth", "light"], "dialogue": {}}]},
]


def plate_path(spec):
    place, prefer = spec
    return "file:" + os.path.join(PLACES, place, first_plate(place, prefer) + ".png")


def anchor_check(fid, sid, key):
    j = post("/api/film/anchorcheck", {"film": fid, "shot": sid})
    r = wait(j["job"], 300, "anchorcheck %s" % key)
    res = (r or {}).get("result") or {}
    if res.get("missing"):
        log("  ** prose names what the anchor lacks: %s" % ", ".join(res["missing"]))
    return res


def main():
    fid = "harbour-night"
    try:
        tree = get("/api/film/" + fid)
        log("film exists:", fid)
    except urllib.error.HTTPError:
        f = post("/api/film/new", {"title": TITLE, "look": "photoreal", "resolution": "auto"})
        fid = f["id"]
        log("film created:", fid)
        tree = get("/api/film/" + fid)
    cast = tree.get("cast") or {}
    if "INES" not in cast:
        cast["INES"] = char_meta("ines-varga")
        cast["TOMAS"] = char_meta("tomas-reyl")
        post("/api/film/edit", {"film": fid, "cast": cast,
                                "logline": "A harbour master and a fisherman wait out the fog; by dusk she is on the platform alone."})
        log("cast set")
    tree = get("/api/film/" + fid)
    by_title = {sc.get("title"): sc for sc in tree["scenes"]}
    scene_ids = {}
    for sc in SCENES:
        if sc["title"] in by_title:
            scene_ids[sc["key"]] = by_title[sc["title"]]["id"]
        else:
            r = post("/api/film/scene", {"film": fid, "title": sc["title"]})
            scene_ids[sc["key"]] = r["id"]
            post("/api/film/editscene", dict(film=fid, scene=r["id"], **{k: v for k, v in sc.items() if k != "key"}))
            log("scene", sc["key"], "->", r["id"])
    tree = get("/api/film/" + fid)
    have = {}
    for sc in tree["scenes"]:
        for s in sc["shots"]:
            det = get("/api/film/%s/shot/%s" % (fid, s["id"]))["shot"]
            if det.get("title"):
                have[det["title"]] = det
    for sh in SHOTS:
        if sh["key"] in have:
            continue
        r = post("/api/film/shot", {"film": fid, "scene": scene_ids[sh["scene"]]})
        body = {"film": fid, "shot": r["id"], "title": sh["key"], "duration": sh["duration"], "beats": sh["beats"],
                "sfx": sh["sfx"], "transition_out": "cut", "no_people": bool(sh.get("no_people"))}
        if sh.get("plate"):
            body["anchor"] = plate_path(sh["plate"])
        post("/api/film/editshot", body)
        have[sh["key"]] = get("/api/film/%s/shot/%s" % (fid, r["id"]))["shot"]
        log("shot", sh["key"], "->", r["id"])

    for sh in SHOTS:
        det = get("/api/film/%s/shot/%s" % (fid, have[sh["key"]]["id"]))["shot"]
        sid = det["id"]
        log("== shot %s (%s) %s ==" % (sh["key"], sid, sh["kind"]))
        if sh.get("compose") and not det.get("anchor_source"):
            c = dict(sh["compose"])
            place, prefer = c.pop("plate")
            c["plate"] = first_plate(place, prefer)
            j = post("/api/film/compose", dict(film=fid, shot=sid, **c))
            r = wait(j["job"], 600, "compose %s" % sh["key"])
            if not r or r.get("error"):
                log("  !! compose failed; skipping"); continue
            det = get("/api/film/%s/shot/%s" % (fid, sid))["shot"]
        if not det.get("anchor_check"):
            anchor_check(fid, sid, sh["key"])
        if det.get("takes"):
            log("  has %d take(s); picked=%s" % (len(det["takes"]), det.get("picked")))
            if not det.get("picked"):
                post("/api/film/pick", {"film": fid, "shot": sid, "take": det["takes"][0]["id"]})
            continue
        if sh["kind"] == "pin":
            j = post("/api/film/pinpreview", {"film": fid, "shot": sid, "change": sh["pin"], "seconds": sh["duration"], "hold_feet": True})
            r = wait(j["job"], 400, "pinpreview %s" % sh["key"])
            pv = (r or {}).get("result") or {}
            force = (not pv.get("ok")) and pv.get("rate", 0) >= 0.0012
            if not pv.get("ok") and not force:
                log("  too little change (%.4f) - LTX take instead" % pv.get("rate", 0))
                sh["kind"] = "ltx"
            else:
                j = post("/api/film/pin", {"film": fid, "shot": sid, "change": sh["pin"], "seconds": sh["duration"],
                                           "hold_feet": True, "force": force})
                r = wait(j["job"], 1200, "pin %s" % sh["key"])
                if r and not r.get("error"):
                    continue
                log("  !! pin failed; LTX take instead")
        j = post("/api/film/takes", {"film": fid, "shot": sid, "engines": ["ltx"], "n": 1})
        wait(j["job"], 1500, "ltx %s" % sh["key"])
        det = get("/api/film/%s/shot/%s" % (fid, sid))["shot"]
        if det.get("takes") and not det.get("picked"):
            good = [t for t in det["takes"] if not t.get("qc")] or det["takes"]
            post("/api/film/pick", {"film": fid, "shot": sid, "take": good[0]["id"]})
            log("  picked", good[0]["id"], "qc:", good[0].get("qc"))

    log("== assemble ==")
    j = post("/api/film/assemble", {"film": fid, "music": True})
    wait(j["job"], 1500, "assemble")
    log("film file:", get("/api/film/" + fid).get("film"))
    log("DONE")


if __name__ == "__main__":
    main()
