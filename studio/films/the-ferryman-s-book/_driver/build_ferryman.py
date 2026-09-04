#!/usr/bin/env python3
"""THE FERRYMAN'S BOOK - a second short, anime, from tonight's new library, with
tonight's lessons applied as workflow rather than as hindsight:

  - every anchor is checked against its prose BEFORE anything renders, and the
    words the anchor lacks are printed (the director's decision point);
  - pins are in-place motions only (H3 honours those); walks are LTX prose;
  - props ride in the composite (Renji carries the old book; the lantern sits
    by the shrine);
  - ambient motion is named on every beat.

Six shots, two scenes, about 44 seconds. Renji and The Ferryman, both invented.
Resumable.
"""
import json, os, sys, time, urllib.request, urllib.error

BASE = "http://127.0.0.1:8777"
ROOT = os.path.expanduser("~/shared/comfy-studio")
CHARS = os.path.join(ROOT, "studio", "foundry", "characters")
PLACES = os.path.join(ROOT, "studio", "foundry", "places")
TITLE = "The Ferryman's Book"


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
    {"key": "S1", "title": "forest shrine, dawn",
     "location": "a moss-covered shrine deep in a cedar forest, mist between the trunks, stone lanterns",
     "time_of_day": "dawn", "weather": "fog", "ambience": "wind in cedar branches, a bell far off, dripping moss",
     "music": "anime score, soft koto and strings, mist, dawn, gentle, 62 bpm", "cast_present": ["RENJI"]},
    {"key": "S2", "title": "rain bridge, night",
     "location": "an iron footbridge over a canal at night, rain, paper lanterns along the rail",
     "time_of_day": "night", "weather": "rain", "ambience": "rain on iron and water, a lantern creaking",
     "music": "anime score, low strings and a music box, rain, night, uneasy, 58 bpm", "cast_present": ["RENJI", "FERRY"]},
]

SHOTS = [
    {"key": "A", "scene": "S1", "kind": "ltx", "duration": 8, "no_people": True,
     "plate": ("forest-shrine", ["dawn_wide", "day_wide"]),
     "sfx": "wind in high branches, dripping moss, a distant bell",
     "beats": [{"framing": "wide establishing shot", "move": "static", "subject": "",
                "action": "mist drifts between the cedar trunks around the old shrine, first light through the fog",
                "background": "leaves stir in the wind", "motion": "", "ambient": ["leaves", "light"], "dialogue": {}}]},
    {"key": "B", "scene": "S1", "kind": "ltx", "duration": 6,
     "compose": {"character": "renji", "place": "forest-shrine", "plate": ("forest-shrine", ["dawn_wide", "day_wide"]),
                 "stand": 0.30, "cx": 0.40, "view": "turn_front",
                 "props": [{"id": "old-book", "stand": 0.22, "cx": 0.62}]},
     "sfx": "wind, his footsteps on wet stone, pages",
     "beats": [{"framing": "wide shot", "move": "static", "subject": "RENJI",
                "action": "stands before the shrine looking at the old book left on the stone",
                "background": "mist drifts between the trunks", "motion": "look_off", "ambient": ["leaves", "light"], "dialogue": {}}]},
    {"key": "C", "scene": "S1", "kind": "pin", "duration": 6,
     "compose": {"character": "renji", "place": "forest-shrine", "plate": ("forest-shrine", ["dawn_detail", "day_detail", "dawn_wide"]),
                 "stand": 0.30, "cx": 0.45, "view": "turn_front_three_quarter"},
     "pin": "the subject has lowered into a crouch, knees bent, one hand reaching down to the ground",
     "sfx": "wind, cloth, pages turning",
     "beats": [{"framing": "medium shot", "move": "static", "subject": "RENJI",
                "action": "crouches to pick up the book", "background": "mist drifts behind him",
                "motion": "crouch", "ambient": ["leaves"], "dialogue": {}}]},
    {"key": "D", "scene": "S2", "kind": "ltx", "duration": 8, "no_people": True,
     "plate": ("rain-bridge", ["night_wide"]),
     "sfx": "rain on iron and water, a lantern creaking, distant thunder",
     "beats": [{"framing": "wide establishing shot", "move": "static", "subject": "",
                "action": "rain falls across the iron footbridge, paper lanterns swaying along the rail, the canal moving below",
                "background": "rain streaks through the lantern light", "motion": "", "ambient": ["rain", "lanterns", "water"], "dialogue": {}}]},
    {"key": "E", "scene": "S2", "kind": "pin", "duration": 8,
     "compose": {"character": "the-ferryman", "place": "rain-bridge", "plate": ("rain-bridge", ["night_wide"]),
                 "stand": 0.45, "cx": 0.55, "view": "turn_front",
                 "props": [{"id": "paper-lantern", "stand": 0.40, "cx": 0.70}]},
     "pin": "the subject has raised one arm, the long pole lifted, and is looking up",
     "sfx": "rain, water, the lantern creaking, a low hum",
     "beats": [{"framing": "wide shot", "move": "static", "subject": "FERRY",
                "action": "raises the pole and looks up into the rain", "background": "lanterns sway along the rail",
                "motion": "look_up", "ambient": ["rain", "lanterns", "water"], "dialogue": {}}]},
    {"key": "F", "scene": "S2", "kind": "ltx", "duration": 8,
     "compose": {"character": "renji", "place": "rain-bridge", "plate": ("rain-bridge", ["night_detail", "night_wide"]),
                 "stand": 0.15, "cx": 0.45, "view": "turn_front",
                 "props": [{"id": "red-umbrella", "stand": 0.13, "cx": 0.72}]},
     "sfx": "rain on the umbrella, water below, his breath",
     "beats": [{"framing": "medium shot", "move": "static", "subject": "RENJI",
                "action": "holds the book to his chest and looks across the bridge, rain running off the umbrella",
                "background": "rain falls through the lantern light, lanterns swaying", "motion": "look_off",
                "ambient": ["rain", "lanterns"], "dialogue": {}}]},
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
    fid = "the-ferryman-s-book"
    try:
        tree = get("/api/film/" + fid)
        log("film exists:", fid)
    except urllib.error.HTTPError:
        f = post("/api/film/new", {"title": TITLE, "look": "anime", "resolution": "auto"})
        fid = f["id"]
        log("film created:", fid)
        tree = get("/api/film/" + fid)
    cast = tree.get("cast") or {}
    if "RENJI" not in cast:
        cast["RENJI"] = char_meta("renji")
        cast["FERRY"] = char_meta("the-ferryman")
        post("/api/film/edit", {"film": fid, "cast": cast,
                                "logline": "An apprentice finds a book at a forest shrine; its owner waits on the rain bridge."})
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
