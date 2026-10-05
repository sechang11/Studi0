#!/usr/bin/env python3
"""THE PLAZA TEST (2026-09-30): does a scene stay in one place when every shot stands in one 3D set?

The question behind it: a building stays "the same building" only while the plate - the one picture of
the place every shot is drawn from - shows it. So the same eight shots of one Italian hill-town square
are made two ways, and measured against each other:

  plaza-set     THE SET. The square is built once in Blender (studio/_tools/set_plaza.py) and every shot
                is a camera in it (previz_blender.py --scene set): its first frame is the set's render
                dressed as a photograph (Qwen-Image-2.1, with the plate as the look), and the take is
                LTX-2.3 with the IC-LoRA union control reading the render's depth (workflow 74), so the
                camera moves the way the set says and what is behind it exists.
  plaza-words   TODAY'S WAY. The same plate (the set's establishing frame, dressed) is the place; each
                shot's start frame is composed from it by words (Flux 2 and Qwen-Image-2.1), with the
                plate turned by the angles LoRA where the shot looks the other way; the take is
                LTX-2.5 with the move asked for in words.

Both share the plate, the shot list, the video prompts and the seeds. set_measure.py scores every start
frame and take against the set's own render of the same camera (does the geometry land where the map
says?) and every landmark's colour against the plate (is the cafe still the same ochre?).
"""
import json
import os

ROOT = os.path.expanduser("~/shared/comfy-studio")
DST = os.path.join(ROOT, "studio", "shotscripts")

GRADE = ("Cinematic film, a sunny afternoon in a small Italian hill town, warm sunlight and soft blue shadows, "
         "natural colour, 35mm film grain.")
REAL = "Unretouched photograph, available light, fine film grain, natural colour, no retouching."
# no "text" here: the cafe's sign is part of the place, and it has to survive for the test to see it
AVOID = ("lowres, blurry, morphing, warping, melting buildings, bending walls, flicker, subtitles, captions, "
         "watermark, nsfw")
NOBODY = "people, a person, a figure, a crowd, pedestrians, a face"
PLACE = ("Wide photograph of a small Italian hill-town square on a sunny afternoon, nobody in it: a stone clock "
         "tower with white clock faces and a green copper roof on the north side between a terracotta town hall "
         "with an arcade and a pale yellow house with green shutters; an ochre cafe with a red-and-white striped "
         "awning and a green CAFFE sign on the east side; a stone archway gate onto a road of cypresses on the "
         "south side between a salmon-pink house and a grey stone bakery with a blue door; a white house with "
         "blue shutters and iron balconies and a plane tree on the west side; a round stone fountain in the "
         "middle. " + REAL)
# The render alone, and words that name nothing: measured on 2026-09-30, the plate as <image2> made
# Qwen-Image-2.1 return the PLATE's view for 7 of 7 shots (even when told to take only its colours), and a
# list of the set's objects put them where they are not (a clock face on the fountain, a tower over the cafe)
DRESS = ("Turn <image1> into a still frame from a live-action film shot on location in a real Italian hill-town "
         "square on a sunny afternoon. Keep the camera, the lens, the framing, the perspective and the layout of "
         "<image1> exactly: everything in it stays exactly where it is, at the same size, with the same colours; "
         "add nothing and remove nothing. Make every surface real: weathered plaster and stone, terracotta roof "
         "tiles, worn paving stones, real glass, real leaves, real water.")

LIFE = "Water splashes in the fountain; the plane tree's leaves stir in a light breeze. The square is empty."
SOUND = "Sound: the fountain splashing, a light breeze, distant swallows. No music."


def still(framing, body):
    return "A still frame from a live-action film, %s %s %s" % (framing, body, GRADE)


# id, name, secs, the camera in the set, the video prompt, (the words today's way composes the start
# frame with, the references it composes from)
SHOTS = [
    ("101", "establishing", 5,
     {"cam": [-13, -13.5, 11], "cam_to": [-11.5, -12, 10], "look": [3, 8, 5], "lens": 22},
     "A high wide view of a sunlit Italian hill-town square in the afternoon: the stone clock tower with its white "
     "clock face and green copper roof, the pale yellow house with green shutters, the ochre cafe with its "
     "red-and-white striped awning, the round stone fountain in the middle, a plane tree in the foreground. The "
     "camera glides slowly forward and down over the square. " + LIFE + " " + SOUND,
     None, ["plaza", "plaza", "plaza"]),
    ("102", "the tower", 4,
     {"cam": [6.5, -11, 1.6], "cam_to": [6.0, -9.5, 1.6], "look": [-1, 16, 8], "lens": 30},
     "The stone clock tower with its white clock face rises over the square; the terracotta town hall with its "
     "arcade stands to its left behind the fountain, the pale yellow house with green shutters to its right. The "
     "camera moves slowly forward at eye level. " + LIFE + " " + SOUND,
     still("a WIDE SHOT at eye level", "of the square of reference one seen from its south-east side, looking "
           "north-north-west: the stone clock tower with its white clock face and green copper roof in the centre, "
           "the top of the fountain on the left in front of the terracotta town hall and its arcade, the pale "
           "yellow house with green shutters on the right. Nobody is there."),
     ["plaza", "plaza", "plaza"]),
    ("103", "the archway", 4,
     {"cam": [-4.0, 6.5, 1.7], "look": [-0.5, -17, 4.2], "lens": 28},
     "Looking south across the square: the stone archway gate in the centre, a road lined with cypresses and "
     "green hills seen through it; the salmon-pink house with olive shutters and a balcony of red flowers on the "
     "right; the grey stone bakery with a blue door on the left; the fountain in the foreground on the left. The "
     "camera is still. " + LIFE + " " + SOUND,
     still("a WIDE SHOT at eye level", "of the south side of the square of reference one, looking south from "
           "beside the fountain: a stone archway gate in the centre with a road of cypress trees and green hills "
           "seen through it, a salmon-pink house with olive shutters and a balcony of red flowers on the right of "
           "the arch, a grey stone bakery with a blue door on the left of the arch, the fountain in the foreground "
           "on the left, a wooden bench and a black lamp post on the right. Nobody is there."),
     ["plaza_rev", "plaza", "plaza"]),
    # 13 m back, not 6.5: from the foot of the tower with a 20 mm lens the dress re-imagined the view on 8 of 8
    # seeds (a steep close-up is where Qwen-Image-2.1 stops keeping the layout). And drawn DOWN from the clock,
    # then played backwards ("reverse"): dressed from its base, the plain lower shaft came back as a house
    # front with a roof on it on 4 of 4 seeds; from the clock face it is unmistakably the tower.
    ("104", "up the tower", 5,
     {"cam": [1.8, 4.0, 1.5], "look": [0, 17, 15.3], "look_to": [0, 17, 3.5], "lens": 24, "reverse": True},
     "The stone clock tower on the north side of the square: the camera tilts slowly up its weathered stone shaft "
     "from the wooden door at its base to the white clock face high above, the terracotta town hall and its arcade "
     "on the left and the pale yellow house on the right. " + SOUND,
     still("a WIDE SHOT at eye level, looking slightly up", "at the foot of the stone clock tower of reference one "
           "from across the north side of the square: its wooden door at the base, the stone shaft rising out of "
           "frame, the terracotta town hall and its arcade on the left, the pale yellow house with green shutters "
           "on the right. Nobody is there."),
     ["plaza", "plaza", "plaza"]),
    ("105", "the cafe", 4,
     {"cam": [4.5, -5.0, 1.7], "cam_to": [5.5, -4.2, 1.7], "look": [16, 2, 2.6], "lens": 32},
     "The ochre cafe on the east side of the square: its red-and-white striped awning, the dark green sign that "
     "reads CAFFE, three small round tables with chairs outside, a black iron lamp post on the left. The camera "
     "drifts slowly toward it. The awning stirs in the breeze. " + SOUND,
     still("a MEDIUM WIDE SHOT at eye level", "of the ochre cafe on the east side of the square of reference one: "
           "its red-and-white striped awning, a dark green sign reading CAFFE above it, three small round tables "
           "with chairs outside, brown shutters on the windows above, a black iron lamp post on the left. Nobody is "
           "there."),
     ["plaza", "plaza", "plaza"]),
    ("106", "round the fountain", 5,
     {"cam": [4.0, 6.93, 2.2], "arc": 100, "arc_center": [0, 0, 0], "look": [0, 0, 1.6], "lens": 28,
      "ease": "linear"},
     "The camera circles slowly around the round stone fountain at a steady pace, keeping it in the centre, "
     "while the square turns behind it: from the stone archway gate and the salmon-pink house to the white house "
     "with blue shutters, then round to the ochre cafe with its striped awning. " + LIFE + " " + SOUND,
     still("a WIDE SHOT at eye level", "of the round stone fountain in the square of reference one, seen from the "
           "north side, looking south: the fountain in the centre, the stone archway gate behind it on the left "
           "with cypresses seen through it, the salmon-pink house behind it, the white house with blue shutters on "
           "the right. Nobody is there."),
     ["plaza", "plaza", "plaza"]),
    ("107", "up to the map", 5,
     {"cam": [0, -9, 3.0], "cam_to": [0, -2.0, 38], "look": [0, 2, 2.5], "look_to": [0, 0.5, 0], "lens": 24},
     "The camera cranes up from beside the fountain, rising high above the square and tilting down until it looks "
     "straight down on the round fountain, the paving, the plane tree, the striped awning and the rooftops around "
     "the square. " + LIFE + " " + SOUND,
     still("a WIDE SHOT at eye level", "of the round stone fountain in the square of reference one seen from the "
           "south, looking north: the fountain in the centre, the stone clock tower behind it, the terracotta town "
           "hall on the left, the pale yellow house on the right. Nobody is there."),
     ["plaza", "plaza", "plaza"]),
    ("108", "the west side", 4,
     {"cam": [8.5, -1.5, 1.7], "cam_to": [8.5, 1.5, 1.7], "look": [-20, 3, 4.5], "lens": 28},
     "Looking west across the fountain at the white house with blue shutters and small iron balconies, the plane "
     "tree on the right. The camera tracks slowly sideways to the right. " + LIFE + " " + SOUND,
     still("a WIDE SHOT at eye level", "of the west side of the square of reference one, looking west across the "
           "round stone fountain: a white house with blue shutters and small black iron balconies behind it, the "
           "plane tree on the right, the salmon-pink house at the left edge. Nobody is there."),
     ["plaza_left", "plaza", "plaza"]),
]


def film(name, title, set_arm):
    shots = []
    for sid, nm, secs, cam, prompt, words, refs in SHOTS:
        d = {"id": sid, "name": nm, "title": nm, "secs": secs, "face": "none", "prompt": prompt,
             "avoid_extra": NOBODY}
        if set_arm:
            pz = {"scene": "set", "set": "plaza", "frames": 24 * secs + 1, "masks": 8, "dress": DRESS,
                  "grade": GRADE}
            pz.update(cam)
            if sid == "101":
                pz["start"] = "anchor_101.png"      # the establishing shot starts on the plate itself
            d.update({"engine": "previz", "refs": ["plaza"], "anchor": None, "previz": pz})
        else:
            d.update({"engine": "ltx", "refs": refs, "anchor": words, "set_camera": cam})
        shots.append(d)
    cast = {} if set_arm else {
        "plaza_rev": {"role": "the square turned round", "place_view": ["plaza", "angle_reverse"],
                      "prompt": "The plate turned round by the angles LoRA."},
        "plaza_left": {"role": "the square turned left", "place_view": ["plaza", "angle_left"],
                       "prompt": "The plate turned to the left by the angles LoRA."},
    }
    return {
        "_comment": "The plaza test (2026-09-30): the same eight shots of one square, %s. "
                    "See _make_plaza_test_0930.py." % ("each a camera in one 3D set" if set_arm else
                                                       "each composed from the plate by words"),
        "film": name, "title": title,
        "logline": "An afternoon in a small Italian square, from eight places in it.",
        "grade": GRADE, "avoid": AVOID, "realism": REAL,
        "score_tags": "quiet acoustic guitar and soft strings, a warm lazy afternoon, instrumental, no vocals",
        "place": {"id": "plaza", "prompt": PLACE},
        "cast": cast,
        "shots": shots,
    }


if __name__ == "__main__":
    for name, title, arm in (("plaza-set", "THE PLAZA - one set", True),
                             ("plaza-words", "THE PLAZA - one plate and words", False)):
        p = os.path.join(DST, name + ".json")
        if os.path.exists(p):
            print("keeping %s (it exists - delete it to rewrite)" % p)
            continue
        json.dump(film(name, title, arm), open(p, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
        print("%s: %d shots -> %s" % (name, len(SHOTS), p))
