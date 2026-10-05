#!/usr/bin/env python3
"""THE JESTER IN THE WOOD (2026-09-30): a fight inside one 3D set, with physics.

The forest is built once (studio/_tools/set_forest.py): a dense, dangerous wood with a path down the middle,
a huge old oak at its edge, a dead snag, a boulder, a stone lantern, a fallen log. Terra walks the path; a
grinning harlequin jester (an original villain, sheet: studio/sheets/forest-fight-the-jester) drops from the
oak onto the path, they trade blows, she casts a fireball, he flips aside and it brings the oak down across
the path - Blender's rigid bodies decide where every leaf, pebble, splinter and the tree itself go, and the
last shot is set in the wreckage the physics left.

Each shot is a camera in the set with a choreography (`"action"`: set_forest.act) moving the two characters
as jointed puppets (set_actors.py). The start frames are the place dressed as anime with the characters put
in by the set (set_test.py cast); the takes are LTX-2.3 with the IC-LoRA on the set's depth; the fire's
last frame is pinned too.
"""
import json
import math
import os

ROOT = os.path.expanduser("~/shared/comfy-studio")
DST = os.path.join(ROOT, "studio", "shotscripts")


def xp(y):
    return round(1.4 * math.sin(y / 10.0), 3)


GRADE = ("2D anime film, hand-drawn cel animation, painted backgrounds, a dark fantasy forest at dusk, shafts of low "
         "sunlight through the canopy, drifting mist.")
AVOID = ("lowres, blurry, morphing, warping, melting, flicker, deformed hands, extra fingers, extra limbs, two of the "
         "same person, subtitles, captions, watermark, nsfw")
OTHERS = "3d render, cgi, photorealistic, live action, a crowd, other people, blood, gore"
HER = "a young woman with long wavy sea-green hair, a red dress, a lilac sash and red boots"
# no colour of his may be one of hers: with "magenta hair" in his words, the woman in the foreground came
# back with magenta hair in two shots (the words name colours, not whose they are)
HIM = ("a lanky harlequin jester in a purple-and-yellow diamond costume and a purple-and-yellow two-horned cap, "
       "with a chalk-white face and a wide red grin")
DRESS = ("Turn <image1> into a frame from a hand-drawn 2D anime film: a dark fantasy forest painted as an anime "
         "background, clean line art, flat cel shading, shafts of late sunlight through the canopy, drifting mist. "
         "Keep the camera, the lens, the framing, the perspective and the layout of <image1> exactly: everything in it "
         "stays exactly where it is, at the same size, with the same colours; add nothing and remove nothing.")
A2D = "2D anime, hand-drawn cel animation. "

SHOTS = [
    ("301", "the path", 5, "walk_far",
     {"cam": [1.0, -15.5, 5.0], "cam_to": [0.9, -12.0, 4.2], "look": [0.4, 4.0, 1.0], "look_to": [0.3, 5.0, 0.8], "lens": 24},
     A2D + "High above a dark, dense fantasy forest at dusk, a narrow dirt path winds between huge gnarled trees, shafts "
     "of low sunlight cutting through drifting mist. %s walks alone along the path, small far below. The camera glides "
     "slowly forward and down. Sound: wind in the canopy, a distant crow, creaking branches, footsteps on dirt. No music."
     % (HER[0].upper() + HER[1:])),
    ("302", "she walks", 4, "walk_toward",
     {"cam": [xp(-0.8), -0.8, 1.45], "cam_to": [xp(2.8), 2.8, 1.45], "look": [xp(-4.4), -4.4, 1.2],
      "look_to": [xp(-0.8), -0.8, 1.2], "lens": 35},
     A2D + "%s walks slowly toward the camera along a dark forest path, glancing left and right, uneasy; mist drifts "
     "between the gnarled trees behind her; the camera moves backward ahead of her at her pace. Sound: her footsteps, "
     "leaves rustling, an owl, a twig snapping somewhere. No music." % (HER[0].upper() + HER[1:])),
    ("303", "watched", 4, "watched",
     {"cam": [1.85, 7.0, 4.65], "cam_to": [1.8, 6.9, 4.6], "look": [xp(-2.8), -2.8, 1.0], "look_to": [xp(0.6), 0.6, 1.0], "lens": 32},
     A2D + "From high on a branch of the old oak, through dark leaves: far below, the young woman with long sea-green hair walks along "
     "the forest path, unaware she is being watched; the leaves in the foreground stir. A soft, high giggle close by. "
     "Sound: rustling leaves, the giggle, her distant footsteps. No music."),
    ("304", "he drops", 4, "drop",
     {"cam": [0.95, -2.3, 1.55], "cam_to": [0.9, -1.8, 1.55], "look": [1.0, 6.5, 2.4], "look_to": [0.8, 6.0, 1.6],
      "lens": 28},
     A2D + "From behind the young woman with long sea-green hair, in the foreground on the forest path: ahead, %s "
     "crouches on a huge branch over the path, then leaps down onto the path in front of her in a shower of falling leaves and twigs, lands in a crouch and rises slowly, grinning. She "
     "stops dead. Sound: a high giggle, rustling, a thud on the dirt. No music." % HIM),
    ("305", "blows", 4, "blows",
     {"cam": [4.4, 3.6, 1.45], "cam_to": [4.2, 3.7, 1.45], "look": [0.3, 3.6, 1.15], "lens": 30},
     A2D + "Side view on the forest path: the grinning jester in his purple-and-yellow diamond costume lunges at the "
     "young woman with long sea-green hair and a red dress with a fast punch; she blocks "
     "with both forearms, then kicks him in the chest; he skids back along the dirt, kicking up pebbles, and straightens, "
     "giggling. Sound: a whoosh, the thump of the block, the kick, scattering pebbles, his laughter. No music."),
    ("306", "fire", 5, "fire",
     {"cam": [-1.0, -1.6, 1.85], "cam_to": [-0.9, -1.2, 1.9], "look": [2.2, 6.4, 2.8], "look_to": [1.6, 7.0, 2.2],
      "lens": 24, "pin": True},
     A2D + "Over her shoulder: she thrusts both hands forward and a blazing fireball bursts from them and streaks along "
     "the path; the jester flips aside; the fireball slams into the huge old tree behind him - the trunk explodes in fire "
     "and splinters, and the whole tree topples and crashes across the path in a storm of leaves and dust. Sound: the "
     "roar of the fireball, an explosion, splintering wood, the crash of the tree. No music."),
    ("307", "the fallen oak", 4, "aftermath",
     {"cam": [2.2, -0.6, 1.7], "cam_to": [2.3, 0.0, 1.75], "look": [0.6, 6.2, 1.7], "lens": 28},
     A2D + "The huge fallen tree lies across the forest path, smoke and dust drifting, embers glowing on its shattered "
     "trunk; the jester in his purple-and-yellow diamond costume crouches on top of the trunk, head tilted, giggling; the "
     "young woman with long sea-green hair and a red dress faces him from the path, "
     "her hands rising to cast again. Sound: crackling embers, settling debris, his giggle, wind. No music."),
]

film = {
    "_comment": "The jester in the wood (2026-09-30): a fight inside one 3D set, with physics. "
                "See _make_forest_fight_0930.py.",
    "film": "forest-fight", "title": "THE JESTER IN THE WOOD",
    "logline": "On a path through a dangerous wood, a grinning jester drops from a tree, and she burns it down.",
    "grade": GRADE, "avoid": AVOID, "realism": "",
    "score_tags": "dark fantasy anime score, taiko drums, tense strings, a music-box motif, instrumental, no vocals",
    "place": {"id": "forest", "prompt": "A dense, dangerous fantasy forest with a dirt path down the middle, painted "
                                        "as an anime background."},
    "cast": {"terra": {"role": "Terra", "prompt": "Terra: her character sheet (studio/sheets/terra-in-the-plaza-terra)."},
             "jester": {"role": "the jester", "prompt": "The jester: his character sheet (studio/sheets/forest-fight-the-jester)."}},
    "shots": [],
}
for sid, name, secs, action, cam, prompt in SHOTS:
    pz = {"scene": "set", "set": "forest", "action": action, "frames": 24 * secs + 1, "masks": 8, "dress": DRESS,
          "dress_place": DRESS, "grade": GRADE, "start": "anchor_%s.png" % sid}
    pz.update(cam)
    film["shots"].append({"id": sid, "name": name, "title": name, "secs": secs, "face": "none", "engine": "previz",
                          "refs": ["forest", "terra", "jester"], "anchor": None, "prompt": prompt,
                          "avoid_extra": OTHERS, "previz": pz})

if __name__ == "__main__":
    p = os.path.join(DST, film["film"] + ".json")
    if os.path.exists(p):
        raise SystemExit("keeping %s (it exists - delete it to rewrite)" % p)
    json.dump(film, open(p, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print("%s: %d shots -> %s" % (film["film"], len(film["shots"]), p))
