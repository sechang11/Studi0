#!/usr/bin/env python3
"""THE HARBOUR LETTER - a short film made entirely through the studio API.

This is the proof that the machinery the Shot tab exposes can carry a film:
composed anchors (character IN the start frame), pinned motion (both ends
chosen, H3 interpolates, end frame on the pristine plate), ambient selectors
(named motion so backgrounds do not freeze), one-beat LTX shots, scene music,
assembly. Every step is a call the UI makes. Resumable: rerun and it skips what
already landed.

Eight shots, two scenes, about 56 seconds. Photoreal. Mara Okonjo and Doran Vey,
both invented, both level-1 packs.
"""
import json, os, sys, time, urllib.request, urllib.error

BASE = "http://127.0.0.1:8777"
ROOT = os.path.expanduser("~/shared/comfy-studio")
CHARS = os.path.join(ROOT, "studio", "foundry", "characters")
PLACES = os.path.join(ROOT, "studio", "foundry", "places")
TITLE = "The Harbour Letter"


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


def post(p, b, timeout=90):
    r = urllib.request.Request(BASE + p, json.dumps(b).encode(),
                               {"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(r, timeout=timeout))


def get(p, timeout=60):
    return json.load(urllib.request.urlopen(BASE + p, timeout=timeout))


def wait(jid, limit=1500, label=""):
    t0 = time.time()
    seen = 0
    while time.time() - t0 < limit:
        me = [x for x in get("/api/film/jobs")["jobs"] if x["id"] == jid]
        if me:
            lg = me[0].get("log") or []
            for l in lg[seen:]:
                log("   |", l)
            seen = len(lg)
            if me[0]["state"] != "running":
                log("  %s -> %s %s (%.0fs)" % (label or jid, me[0]["state"],
                                              me[0].get("error") or "", time.time() - t0))
                return me[0]
        time.sleep(8)
    log("  %s still running after %ds" % (label or jid, limit))
    return None


def char_meta(cid):
    a = json.load(open(os.path.join(CHARS, cid, "asset.json"), encoding="utf-8"))
    c = a.get("compiled") or {}
    return {"name": a.get("name", cid), "clause": c.get("clause", ""),
            "short": c.get("short", "") or a.get("name", cid).split()[0],
            "sheet": os.path.join(CHARS, cid, "base_portrait.png"),
            "portrait": os.path.join(CHARS, cid, "base_portrait.png"),
            "voice": "", "voice_desc": ""}


def plate(place, key):
    return os.path.join(PLACES, place, key + ".png")


# ── the film ────────────────────────────────────────────────────────────────────────
SCENES = [
    {"key": "S1", "title": "rain street, night",
     "location": "a narrow rain-soaked street at night, shuttered shops, neon signs, "
                 "wet tarmac", "time_of_day": "night", "weather": "heavy rain",
     "ambience": "rain on tarmac and awnings, distant traffic, a neon buzz",
     "music": "cinematic ambient, slow solo piano, rain, melancholic, sparse, 70 bpm",
     "cast_present": ["MARA"]},
    {"key": "S2", "title": "harbour, dawn",
     "location": "a small fishing harbour at first light, wet stone quay, moored boats",
     "time_of_day": "dawn", "weather": "clear and cold",
     "ambience": "water lapping against hulls, gulls far off, rope creaking",
     "music": "cinematic ambient, warm strings, hopeful, dawn, slow, 65 bpm",
     "cast_present": ["MARA", "DORAN"]},
]

SHOTS = [
    # ── S1 ──
    {"key": "A", "scene": "S1", "kind": "ltx", "duration": 8,
     "anchor": "file:" + plate("rain-street", "night_wide"), "no_people": True,
     "sfx": "rain on tarmac, distant tyres on a wet road, a neon sign buzzing",
     "beats": [{"framing": "wide establishing shot", "move": "static", "subject": "",
                "action": "rain hammers the empty street, neon reflections trembling in the puddles",
                "background": "a car passes slowly at the far end",
                "motion": "", "ambient": ["rain", "traffic", "light"], "dialogue": {}}]},
    {"key": "B", "scene": "S1", "kind": "pin", "duration": 8,
     "compose": {"character": "mara-okonjo", "place": "rain-street", "plate": "night_wide",
                 "stand": 0.35, "cx": 0.42, "view": "turn_front"},
     "pin": "the subject has lowered into a deep crouch, knees bent, weight low, one hand "
            "reaching for a sodden envelope on the wet road",
     "sfx": "rain, her boots on wet tarmac, a distant car",
     "beats": [{"framing": "wide shot", "move": "static", "subject": "MARA",
                "action": "crouches to pick a sodden letter off the road",
                "background": "rain falls through the street light",
                "motion": "crouch", "ambient": ["rain"], "dialogue": {}}]},
    {"key": "C", "scene": "S1", "kind": "ltx", "duration": 6,
     "compose": {"character": "mara-okonjo", "place": "rain-street", "plate": "night_detail",
                 "stand": 0.12, "cx": 0.45, "view": "turn_front_three_quarter"},
     "sfx": "rain, paper crackling wetly",
     "beats": [{"framing": "medium shot", "move": "static", "subject": "MARA",
                "action": "unfolds the wet letter and reads it, rain running off her hair, "
                          "her face changing as she reads",
                "background": "rain streaks through the light behind her",
                "motion": "look_off", "ambient": ["rain", "light"], "dialogue": {}}]},
    # ── S2 ──
    {"key": "D", "scene": "S2", "kind": "ltx", "duration": 8,
     "anchor": "file:" + plate("harbour-dawn", "dawn_wide"), "no_people": True,
     "sfx": "water lapping at hulls, ropes creaking, distant gulls",
     "beats": [{"framing": "wide establishing shot", "move": "static", "subject": "",
                "action": "first light spreads across the harbour, boats rocking gently at "
                          "their moorings",
                "background": "the water moves continuously, gulls cross the sky",
                "motion": "", "ambient": ["water", "light"], "dialogue": {}}]},
    {"key": "E", "scene": "S2", "kind": "pin", "duration": 6,
     "compose": {"character": "doran-vey", "place": "harbour-dawn", "plate": "dawn_wide",
                 "stand": 0.40, "cx": 0.56, "view": "turn_side"},
     "pin": "the subject has turned to face the camera squarely, looking straight into "
            "the lens",
     "sfx": "water lapping, a rope creaking, his coat moving",
     "beats": [{"framing": "wide shot", "move": "static", "subject": "DORAN",
                "action": "turns from the water to face the camera",
                "background": "boats rock gently behind him",
                "motion": "turn_to", "ambient": ["water"], "dialogue": {}}]},
    {"key": "F", "scene": "S2", "kind": "pin", "duration": 8,
     "compose": {"character": "mara-okonjo", "place": "harbour-dawn", "plate": "dawn_reverse",
                 "stand": 0.55, "cx": 0.45, "view": "turn_front"},
     "pin": "the subject has walked closer to the camera and is larger in the frame, "
            "still holding the letter",
     "sfx": "her boots on wet stone, water lapping, gulls",
     "beats": [{"framing": "wide shot", "move": "static", "subject": "MARA",
                "action": "walks along the quay toward the camera, the letter in her hand",
                "background": "the water moves, light spreading across the stone",
                "motion": "walk_to", "ambient": ["water", "light"], "dialogue": {}}]},
    {"key": "G", "scene": "S2", "kind": "ltx", "duration": 6,
     "compose": {"character": "doran-vey", "place": "harbour-dawn", "plate": "dawn_wide",
                 "stand": 0.15, "cx": 0.50, "view": "turn_front"},
     "sfx": "water, a gull, his breath",
     "beats": [{"framing": "medium shot", "move": "static", "subject": "DORAN",
                "action": "his expression softens as he sees her, a small nod",
                "background": "the water glitters behind him",
                "motion": "nod", "ambient": ["water", "light"], "dialogue": {}}]},
    {"key": "H", "scene": "S2", "kind": "ltx", "duration": 6,
     "anchor": "file:" + plate("harbour-dawn", "dawn_detail"), "no_people": True,
     "sfx": "water lapping at the quay, a single gull",
     "beats": [{"framing": "wide shot", "move": "static", "subject": "",
                "action": "sunlight spreads across the wet stone of the quay, the water "
                          "glittering",
                "background": "ripples cross the harbour",
                "motion": "", "ambient": ["water", "light"], "dialogue": {}}]},
]


def main():
    fid = "the-harbour-letter"
    try:
        tree = get("/api/film/" + fid)
        log("film exists:", fid)
    except urllib.error.HTTPError:
        f = post("/api/film/new", {"title": TITLE, "look": "photoreal", "resolution": "auto"})
        fid = f["id"]
        log("film created:", fid)
        tree = get("/api/film/" + fid)

    # cast, from the foundry packs
    cast = tree.get("cast") or {}
    if "MARA" not in cast or "DORAN" not in cast:
        cast["MARA"] = char_meta("mara-okonjo")
        cast["DORAN"] = char_meta("doran-vey")
        post("/api/film/edit", {"film": fid, "cast": cast,
                                "logline": "A letter found in the rain is carried to the "
                                           "harbour at dawn."})
        log("cast set: MARA, DORAN")

    # scenes by title
    tree = get("/api/film/" + fid)
    by_title = {sc.get("title"): sc for sc in tree["scenes"]}
    scene_ids = {}
    for sc in SCENES:
        if sc["title"] in by_title:
            scene_ids[sc["key"]] = by_title[sc["title"]]["id"]
        else:
            r = post("/api/film/scene", {"film": fid, "title": sc["title"]})
            scene_ids[sc["key"]] = r["id"]
            post("/api/film/editscene", dict(film=fid, scene=r["id"],
                                             **{k: v for k, v in sc.items() if k not in ("key",)}))
            log("scene", sc["key"], "->", r["id"])

    # shots by title (= key)
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
        body = {"film": fid, "shot": r["id"], "title": sh["key"], "duration": sh["duration"],
                "beats": sh["beats"], "sfx": sh["sfx"], "transition_out": "cut",
                "no_people": bool(sh.get("no_people"))}
        if sh.get("anchor"):
            body["anchor"] = sh["anchor"]
        post("/api/film/editshot", body)
        have[sh["key"]] = get("/api/film/%s/shot/%s" % (fid, r["id"]))["shot"]
        log("shot", sh["key"], "->", r["id"])

    # the work, shot by shot, in order
    for sh in SHOTS:
        det = get("/api/film/%s/shot/%s" % (fid, have[sh["key"]]["id"]))["shot"]
        sid = det["id"]
        log("== shot %s (%s) %s ==" % (sh["key"], sid, sh["kind"]))
        if sh.get("compose") and not det.get("anchor_source"):
            j = post("/api/film/compose", dict(film=fid, shot=sid, **sh["compose"]))
            r = wait(j["job"], 600, "compose %s" % sh["key"])
            if not r or r.get("error"):
                log("  !! compose failed; skipping shot"); continue
            det = get("/api/film/%s/shot/%s" % (fid, sid))["shot"]
        if det.get("takes"):
            log("  has %d take(s); picked=%s" % (len(det["takes"]), det.get("picked")))
            if not det.get("picked"):
                post("/api/film/pick", {"film": fid, "shot": sid, "take": det["takes"][0]["id"]})
            continue
        if sh["kind"] == "pin":
            j = post("/api/film/pinpreview", {"film": fid, "shot": sid, "change": sh["pin"],
                                              "seconds": sh["duration"]})
            r = wait(j["job"], 400, "pinpreview %s" % sh["key"])
            pv = (r or {}).get("result") or {}
            force = False
            if not pv.get("ok"):
                if pv.get("rate", 0) >= 0.0015:
                    force = True
                    log("  below the floor (%.4f) - pinning anyway, rate is not trivial" % pv.get("rate", 0))
                else:
                    log("  too little change (%.4f) - falling back to an LTX take" % pv.get("rate", 0))
                    sh["kind"] = "ltx"
            if sh["kind"] == "pin":
                j = post("/api/film/pin", {"film": fid, "shot": sid, "change": sh["pin"],
                                           "seconds": sh["duration"], "force": force})
                r = wait(j["job"], 1200, "pin %s" % sh["key"])
                if r and not r.get("error"):
                    continue
                log("  !! pin failed; falling back to an LTX take")
        j = post("/api/film/takes", {"film": fid, "shot": sid, "engines": ["ltx"], "n": 1})
        r = wait(j["job"], 1500, "ltx %s" % sh["key"])
        det = get("/api/film/%s/shot/%s" % (fid, sid))["shot"]
        if det.get("takes") and not det.get("picked"):
            good = [t for t in det["takes"] if not t.get("qc")] or det["takes"]
            post("/api/film/pick", {"film": fid, "shot": sid, "take": good[0]["id"]})
            log("  picked", good[0]["id"], "qc:", good[0].get("qc"))

    # assemble with music
    log("== assemble ==")
    j = post("/api/film/assemble", {"film": fid, "music": True})
    r = wait(j["job"], 1500, "assemble")
    tree = get("/api/film/" + fid)
    log("film file:", tree.get("film"))
    log("DONE")


if __name__ == "__main__":
    main()
