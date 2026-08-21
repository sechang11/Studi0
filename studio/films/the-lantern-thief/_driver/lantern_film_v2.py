#!/usr/bin/env python3
"""THE LANTERN THIEF v2 - single-beat shots, cut at assembly.

v1 asked LTX for 3-beat 28s multishots; the model spent 24s on beat 1,
dissolved late, re-derived wardrobe at the internal cut, and the 28s take
could not even be mastered (interpolation ceiling 25s). The identity-moments
doctrine applies to anime after all: every cast beat becomes its own shot,
every cut happens at assembly."""
import json, os, sys, time, urllib.request

BASE = "http://127.0.0.1:8777"
FILM = "the-lantern-thief"
STATE_P = "/tmp/lantern_state_v2.json"
OLD_STATE_P = "/tmp/lantern_film_state.json"
S = json.load(open(STATE_P)) if os.path.exists(STATE_P) else {}

def save():
    json.dump(S, open(STATE_P, "w"), indent=1)

def post(p, b):
    r = urllib.request.Request(BASE + p, json.dumps(b).encode(),
                               {"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(r, timeout=300))

def get(p):
    return json.load(urllib.request.urlopen(BASE + p, timeout=60))

def wait_film_job(jid, label):
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

def tree():
    return json.load(open("studio/films/%s/film.json" % FILM))

def shot_of(t, shid):
    return t["shots"][shid]

def D(char, line, delivery):
    return {"char": char, "line": line, "delivery": delivery}

ND = {"char": "", "line": "", "delivery": ""}

# scenes were created by v1 and carry anchors, music, cast_present
if "scenes" not in S:
    old = json.load(open(OLD_STATE_P))
    S["scenes"] = old["scenes"]
    save()
SC = S["scenes"]

# -- clear the v1 multishot shots ------------------------------------------------------
if not S.get("cleared"):
    t = tree()
    for shid in list(t["shots"]):
        post("/api/film/delete", {"film": FILM, "shot": shid})
        print("deleted v1 shot", shid, flush=True)
    S["cleared"] = True
    save()

# -- the shot list: one beat per shot, every cut at assembly ---------------------------
# (key, scene, title, secs, sfx, framing, move, subject, action, background,
#  dialogue, no_people, transition_out)
AMB1 = ("a busy festival market at night: hundreds of voices murmuring, food "
        "sizzling on flat grills, paper lanterns creaking on their lines, running "
        "under the whole shot and never stopping")
AMB2 = ("wind over the tiles and the market hum far below, running under the "
        "whole shot and never stopping")
AMB3 = ("steady rain on stone and tin, water running in a gutter, the market "
        "muffled and far away, running under the whole shot and never stopping")
AMB4 = ("a steady wind through pine trees and a slow temple bell, running under "
        "the whole shot and never stopping")
AMB5 = ("a waking market: shutters sliding open, sparrows, a broom sweeping "
        "stone, a kettle beginning to sing, running under the whole shot and "
        "never stopping")

SHOTS = [
 ("m1", SC[0], "The market", 10, AMB1,
  "wide establishing shot", "pan", "",
  "festival crowds drift between the food stalls, dozens of paper lanterns "
  "swaying gently overhead, steam rising from the cook fires",
  "the lantern-lit market street", None, False, "cut"),
 ("m2", SC[0], "Jin weaves", 10, AMB1,
  "medium shot", "follow", "JIN",
  "JIN weaves quickly between festival-goers, slipping through gaps in the "
  "crowd, glancing back over her shoulder",
  "market stalls and moving crowds", None, False, "cut"),
 ("m3", SC[0], "The stall", 8, AMB1,
  "medium shot", "push in", "THE_KEEPER",
  "THE_KEEPER tends a stall hung with rows of glowing paper lanterns, "
  "adjusting one gently with both hands",
  "the lantern stall glowing warm", None, False, "cut"),
 ("m4", SC[0], "The lift", 10,
  "the market murmur close by, a lantern's paper skin rustling",
  "close-up", "static", "JIN",
  "among rows of warm orange lanterns hangs one small blue-white lantern, and "
  "JIN's gloved hand closes around its handle and lifts it free",
  "the lantern stall", D("JIN", "One little light. He has hundreds.",
                         "a wry whisper"), False, "cut"),
 ("m5", SC[0], "Watcher", 8,
  "the market murmur far below, wood creaking under small paws",
  "high-angle shot", "static", "HOSHI",
  "HOSHI crouches on a rooftop beam above the market, two tails flicking, "
  "amber eyes tracking movement in the crowd below",
  "the market glowing below the rooftops", None, False, "dissolve"),

 ("c1", SC[1], "Sprint", 10, AMB2,
  "wide shot", "follow", "JIN",
  "JIN sprints along a rooftop ridge clutching the blue-white lantern, HOSHI "
  "bounding along the tiles beside her",
  "moonlit tiled rooftops, the city lights beyond", None, False, "cut"),
 ("c2", SC[1], "The leap", 9, AMB2,
  "low tracking shot", "follow", "JIN",
  "JIN leaps the gap between two rooftops, coat flaring, the lantern swinging "
  "wide in her hand, and lands running",
  "a dark alley gap between roofs", None, False, "cut"),
 ("c3", SC[1], "Cornered", 9, AMB2,
  "medium shot", "static", "JIN",
  "a ring of glowing paper charms sweeps in a circle ahead of JIN and she "
  "skids to a stop on the tiles, HOSHI bristling at her side",
  "the rooftop ridge in moonlight",
  D("HOSHI", "They're following! They're following!",
    "breathless and delighted"), False, "cut"),
 ("c4", SC[1], "The glow", 8,
  "wind steady over the tiles, the paper lantern humming faintly",
  "close-up", "push in", "JIN",
  "JIN holds the blue-white lantern up before her face, its pale glow "
  "reflected in her green eyes, city lights blurred far behind",
  "the night skyline out of focus", None, False, "dissolve"),

 ("a1", SC[2], "Dead end", 9, AMB3,
  "medium shot", "handheld", "JIN",
  "JIN ducks into the rain-dark alley and presses her back against the brick "
  "wall, breathing hard, the lantern hugged to her chest",
  "rain streaking past a single high lamp", None, False, "cut"),
 ("a2", SC[2], "Guttering", 7,
  "rain tapping the lantern's paper skin, the gutter running",
  "close-up", "static", "",
  "inside the paper lantern the pale flame gutters low, shrinking to a "
  "trembling point of light; no people in the frame",
  "the dark alley", None, True, "cut"),
 ("a3", SC[2], "The truth", 9, AMB3,
  "medium two-shot", "static", "HOSHI",
  "HOSHI lands soft on a wooden crate beside JIN, shakes the rain from his "
  "fur, and looks up at the dimming lantern in her arms",
  "the alley wall in the rain",
  D("HOSHI", "That's the temple's last flame. Everything else went out.",
    "quiet, suddenly serious"), False, "cut"),
 ("a4", SC[2], "Choice", 8,
  "the rain easing slightly, a distant temple bell through the wet air",
  "close-up", "push in", "JIN",
  "rain drips from JIN's hood as she stares down at the small flame, her wry "
  "look fading into something quieter and resolved",
  "the dark alley", D("JIN", "...of course it is.", "a rueful sigh"),
  False, "dissolve"),

 ("t1", SC[3], "The climb", 10, AMB4,
  "wide shot", "tilt up", "JIN",
  "JIN climbs the long fog-wrapped stone steps toward the temple gate, the "
  "blue-white lantern held out ahead of her, its glow a small moon in the grey",
  "fog rolling between the pines", None, False, "cut"),
 ("t2", SC[3], "The altar", 9, AMB4,
  "medium shot", "static", "JIN",
  "JIN sets the blue-white lantern on the stone altar shelf, and the pale "
  "flame steadies, rises, and brightens",
  "the temple altar in fog", None, False, "cut"),
 ("t3", SC[3], "The Keeper", 10, AMB4,
  "medium two-shot", "static", "THE_KEEPER",
  "THE_KEEPER steps out of the fog beside the altar, hands folded in his "
  "sleeves, and bows slightly to JIN, who ducks her head, caught",
  "the temple court in first light",
  D("THE_KEEPER", "It was never stolen. It was carried.",
    "warm and unhurried"), False, "cut"),
 ("t4", SC[3], "First light", 10,
  "the wind in the pines opening into birdsong, the bell fading",
  "wide establishing shot", "static", "",
  "dawn light spreads through the fog down the temple hillside, the lantern's "
  "glow answering from the altar, rooflines dark against the gold; no people "
  "anywhere in the frame",
  "the temple hill at first light", None, True, "dissolve"),

 ("d1", SC[4], "Morning after", 9, AMB5,
  "wide shot", "pan", "JIN",
  "the same market street at dawn, stalls opening one by one, JIN in red and "
  "gold festival silks on a step-stool hanging small paper lanterns along the "
  "lantern stall",
  "the market street washed in dawn light", None, False, "cut"),
 ("d2", SC[4], "Handing up", 9, AMB5,
  "medium two-shot", "static", "THE_KEEPER",
  "THE_KEEPER passes JIN another paper lantern up to hang, laughing in his "
  "beard as she wobbles on the step-stool",
  "the lantern stall in morning light",
  D("JIN", "Turns out lanterns are heavier going up.",
    "mock-grumbling, smiling"), False, "cut"),
 ("d3", SC[4], "Hoshi", 8, AMB5,
  "medium shot", "static", "HOSHI",
  "HOSHI perches on the stall's roof edge batting at a hanging paper charm, "
  "two tails swinging for balance",
  "lantern lines crossing the morning sky", None, False, "cut"),
 ("d4", SC[4], "Ember", 8,
  "the market waking softly, one lantern's paper skin ticking as it warms",
  "close-up", "pull back", "",
  "one small paper lantern glows warm against the sunrise as the sun clears "
  "the rooftops behind it; no people in the frame",
  "the waking market softened to bokeh", None, True, "fade"),
]

if "shots" not in S:
    S["shots"] = {}
for row in SHOTS:
    key, scid, title, secs, sfx, framing, move, subject, action, bg, dlg, nop, tout = row
    if key in S["shots"]:
        continue
    r = post("/api/film/shot", {"film": FILM, "scene": scid})
    shid = r["id"]
    post("/api/film/editshot", {"film": FILM, "shot": shid, "title": title,
        "duration": secs, "anchor": "scene", "sfx": sfx, "no_people": nop,
        "transition_out": tout,
        "beats": [{"framing": framing, "move": move, "transition_in": "",
                   "subject": subject, "action": action, "background": bg,
                   "dialogue": dlg or dict(ND)}]})
    S["shots"][key] = shid
    print("shot %s -> %s" % (key, shid), flush=True)
    save()

# -- render: takes -> pick -> vo -> master, sequential ---------------------------------
def stage_done(key, st):
    return S.setdefault("done", {}).setdefault(key, {}).get(st)

def mark(key, st):
    S["done"][key][st] = True
    save()

for row in SHOTS:
    key, scid, title, secs, sfx, framing, move, subject, action, bg, dlg, nop, tout = row
    shid = S["shots"][key]
    if key == "d1" and not S.get("festival_swap"):
        post("/api/foundry/send", {"film": FILM, "characters": [
            {"id": "jin", "costume": "festival-silks"}]})
        S["festival_swap"] = True
        save()
        print("cast swap: JIN now wears festival silks", flush=True)
    if not stage_done(key, "take"):
        j = post("/api/film/takes", {"film": FILM, "shot": shid,
                                     "engines": ["ltx"], "n": 1})
        print("%s: takes job %s" % (key, j["job"]), flush=True)
        if not wait_film_job(j["job"], "%s take" % key):
            sys.exit("%s: take failed" % key)
        sh = shot_of(tree(), shid)
        if not sh["takes"]:
            sys.exit("%s: no take landed" % key)
        post("/api/film/pick", {"film": FILM, "shot": shid,
                                "take": sh["takes"][-1]["id"]})
        mark(key, "take")
    if dlg and not stage_done(key, "vo"):
        sh = shot_of(tree(), shid)
        j = post("/api/film/vo", {"film": FILM, "shot": shid,
                                  "take": sh["picked"]})
        if not wait_film_job(j["job"], "%s vo" % key):
            sys.exit("%s: vo failed" % key)
        sh = shot_of(tree(), shid)
        post("/api/film/pick", {"film": FILM, "shot": shid,
                                "take": sh["takes"][-1]["id"]})
        mark(key, "vo")
    if not stage_done(key, "master"):
        j = post("/api/film/master", {"film": FILM, "shot": shid})
        if not wait_film_job(j["job"], "%s master" % key):
            sys.exit("%s: master failed" % key)
        mark(key, "master")

# -- assembly --------------------------------------------------------------------------
if not S.get("assembled"):
    j = post("/api/film/assemble", {"film": FILM, "music": True})
    if not wait_film_job(j["job"], "assemble"):
        sys.exit("assemble failed")
    S["assembled"] = True
    save()
print("FILM COMPLETE", flush=True)
