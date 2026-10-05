#!/usr/bin/env python3
"""TERRA IN THE PLAZA (2026-09-30): the plaza test's set with a character standing in it and things added.

The plaza test (_make_plaza_test_0930.py) showed one 3D set keeps a place the same place from shot to shot.
This asks the next two questions on the same set (set_plaza_market.py - the square on a market afternoon):

  a CHARACTER    Terra (studio/foundry/characters/terra, anime) stands east of the fountain looking at the
                 cafe. Her real shape is in the set (her Hunyuan3D mesh, --figure-glb), so the depth puts her
                 where she stands in every shot; her look comes from her reference picture in the dress.
  ADDED THINGS   a fruit stall with a striped canopy, a red bicycle on the fountain, pots of flowers, strings
                 of lights: do they stay put from shot to shot like the buildings?
  A STYLE        the whole scene in 2D anime, her own style: the dress paints the set's render as cel animation.

Four shots: the square from above with her in it; her face; over her shoulder to the cafe; the camera
circling her (pinned at its end - the plaza test's lesson for a move that reveals).
"""
import json
import os

ROOT = os.path.expanduser("~/shared/comfy-studio")
DST = os.path.join(ROOT, "studio", "shotscripts")

GRADE = "2D anime film, hand-drawn cel animation, painted backgrounds, soft afternoon sunlight, gentle colours."
AVOID = ("lowres, blurry, morphing, warping, melting buildings, bending walls, flicker, deformed hands, extra "
         "fingers, extra limbs, two of the same person, subtitles, captions, watermark, nsfw")
OTHERS = "other people, a crowd, a second woman, a man, 3d render, cgi, photorealistic, live action"
HER = "a young woman with long wavy sea-green hair tied with a red ribbon, a sleeveless red dress, a lilac sash and red boots"
SOUND = "Sound: the fountain splashing, a light breeze, distant swallows, the murmur of a market. No music."
DRESS = ("Turn <image1> into a frame from a hand-drawn 2D anime film: a painted anime background, clean line art, "
         "flat cel shading, soft afternoon sunlight. Keep the camera, the lens, the framing, the perspective and the "
         "layout of <image1> exactly: everything in it stays exactly where it is, at the same size, with the same "
         "colours; add nothing and remove nothing. The light grey standing figure is the young woman of <image2>, "
         "drawn in the same anime style - her long wavy sea-green hair, her red dress, her lilac sash, her red "
         "boots - standing exactly where the figure stands, in the same pose, facing the same way.")
# her shape: a Hunyuan3D mesh from the clean front view of her character sheet (/sheets). The Foundry's own
# mesh.glb was built from a picture with its decorative background still in it and came in as a box.
# the place on its own, for set_test.py cast: the dress redrew her from her reference at the reference's size
# (full length, centred) wherever the set had her cut by the frame, so the place is dressed without her and
# the view of her sheet facing the camera is put in where the set says she stands
DRESS_PLACE = DRESS.split(" The light grey standing figure")[0]
TERRA = {"figure_glb": "studio/sheets/terra-in-the-plaza-terra/model.glb", "figure_at": [6.5, -2.5, 0.0],
         "figure_turn": 90, "figure_name": "terra", "figure_height": 1.62,
         "figure_sheet": "studio/sheets/terra-in-the-plaza-terra", "dress_place": DRESS_PLACE}
# which of her sheet's views the dress is handed: her front where the camera sees her face, her back where
# it is behind her (the cyber-alchemist's back view, the same way)
VIEW = {"201": "terra_back", "202": "terra", "203": "terra_back", "204": "terra"}

SHOTS = [
    ("201", "the square, and her", 5,
     {"cam": [-12, -13, 9], "cam_to": [-10.5, -11.5, 8.2], "look": [5, 1, 1.5], "lens": 24},
     "2D anime, hand-drawn cel animation. A high wide view of a sunlit Italian hill-town square in the afternoon: "
     "the stone clock tower, the ochre cafe with its red-and-white striped awning, a fruit stall under a yellow "
     "striped canopy, strings of lights across the square, the round stone fountain with a red bicycle leaning on "
     "it. %s stands alone near the fountain, looking toward the cafe. The camera glides slowly forward and down. "
     "Water splashes in the fountain; her hair and sash stir in the breeze. %s" % (HER[0].upper() + HER[1:], SOUND)),
    ("202", "her face", 4,
     {"cam": [11.5, -2.9, 1.5], "cam_to": [10.6, -2.8, 1.5], "look": [6.5, -2.5, 1.35], "lens": 40},
     "2D anime, hand-drawn cel animation. A medium shot: %s stands facing the camera in a sunlit Italian square, "
     "the round stone fountain and the white house with blue shutters behind her. She looks toward the cafe, then "
     "smiles softly; her hair and her lilac sash move in the breeze. The camera moves slowly closer. %s"
     % (HER, SOUND)),
    ("203", "over her shoulder", 4,
     {"cam": [4.6, -3.4, 1.75], "cam_to": [4.85, -3.3, 1.75], "look": [16, -0.5, 2.0], "lens": 32},
     "2D anime, hand-drawn cel animation. Over her shoulder: the long wavy sea-green hair and lilac sash of the "
     "young woman in the foreground on the left, looking across the square at the ochre cafe with its "
     "red-and-white striped awning, its green CAFFE sign, terracotta pots of red flowers and small tables outside; "
     "strings of lights overhead. She stands still; her hair stirs in the breeze. %s" % SOUND),
    ("204", "round her", 5,
     {"cam": [8.6, -6.137, 1.6], "arc": 120, "arc_center": [6.5, -2.5, 0.0], "look": [6.5, -2.5, 1.35],
      "lens": 35, "ease": "linear"},
     "2D anime, hand-drawn cel animation. The camera circles slowly around %s at a steady pace while she stands "
     "still beside the fountain, looking toward the cafe, her hair stirring; the square turns behind her: the town "
     "hall and the fruit stall, the white house and the plane tree, then the stone archway. %s" % (HER, SOUND)),
]

film = {
    "_comment": "Terra in the plaza (2026-09-30): the plaza test's set with a character in it and things added. "
                "See _make_plaza_terra_0930.py.",
    "film": "plaza-terra", "title": "TERRA IN THE PLAZA",
    "logline": "On a market afternoon, a young woman stops by a fountain and looks at a cafe.",
    "grade": GRADE, "avoid": AVOID, "realism": "",
    "score_tags": "gentle anime slice-of-life score, acoustic guitar, soft strings, instrumental, no vocals",
    "place": {"id": "plaza", "prompt": "A small Italian hill-town square on a market afternoon, painted as an anime "
                                       "background."},
    "cast": {"terra": {"role": "Terra", "prompt": "Terra from the front: her character sheet's front view."},
             "terra_back": {"role": "Terra from behind", "prompt": "Terra from behind: her character sheet's back view."}},
    "shots": [],
}
for sid, name, secs, cam, prompt in SHOTS:
    pz = {"scene": "set", "set": "plaza_market", "frames": 24 * secs + 1, "masks": 8, "dress": DRESS, "grade": GRADE}
    pz.update(TERRA)
    pz.update(cam)
    pz["start"] = "anchor_%s.png" % sid       # composed by set_test.py cast: the place dressed, her put in by the set
    film["shots"].append({"id": sid, "name": name, "title": name, "secs": secs, "face": "none", "engine": "previz",
                          "refs": ["plaza", VIEW[sid]], "anchor": None, "prompt": prompt, "avoid_extra": OTHERS,
                          "previz": pz})

if __name__ == "__main__":
    p = os.path.join(DST, film["film"] + ".json")
    if os.path.exists(p):
        raise SystemExit("keeping %s (it exists - delete it to rewrite)" % p)
    json.dump(film, open(p, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print("%s: %d shots -> %s" % (film["film"], len(film["shots"]), p))
