# ATLAS part two, rewritten after the first attempt failed.
#
# WHAT WENT WRONG. The first version cut river -> campfire -> ice -> mountain in four
# jumps, and one beat asked for "a gloved hand" cracking ice off the canvas. LTX took the
# hand and grew a whole man out of it: after the first cut the bag was being WORN by a
# bearded hiker who then just stood looking at camera for twelve seconds, and none of the
# remaining beats happened.
#
# Two rules from the official guide, both of which I had broken:
#   * do not jump geography between cuts without explaining the jump in the prose
#   * keep the frame uncrowded - a few clear subjects, and no incidental people, because
#     an incidental person becomes the subject
#
# So: three cuts instead of four, every place jump named as a time jump ("that night",
# "by morning"), and not one human anywhere in the prompt. The bag is the only character.
BAG = "the same worn olive canvas backpack with leather straps and a brass buckle"
LOOK = ("shot on 35mm with an anamorphic lens, high contrast, teal and amber grade, "
        "cinematic commercial photography, sharp and detailed, no people in frame")
NEG = ("cartoon, childish, ugly, video game, blurry, watermark, text, logo, brand name, "
       "person, man, woman, hiker, hands, face, model wearing a backpack")

FILM = {"scenes": [
    {"id": "atlas_b", "seconds": 20, "megapixels": 1.2, "seed": 33, "neg": NEG,
     "note": "river -> fire -> frost -> hero, no people", "engine": "photo",
     "keyframe": "a worn olive canvas backpack with leather straps and a brass buckle "
                 "alone in a fast rocky river, whitewater breaking over it, cold morning "
                 "light, no people",
     "prompt": beats(
         "A close tracking shot with no people anywhere in frame: %s is swept sideways "
         "down a fast rocky river, whitewater breaking over it and rolling it against the "
         "stones. %s" % (BAG, LOOK),
         [("That night, a hard cut transitions to", "a slow low shot",
           "%s alone on the ground beside a burning campfire" % BAG,
           "as sparks and embers blow sideways across it and land on the canvas and die "
           "out without catching, still no people in frame"),
          ("By morning, another hard cut transitions to", "a tight macro shot",
           "the surface of %s" % BAG,
           "sheeted in white frost, and the frost splits and flakes away from the canvas "
           "as the sun reaches it, the fabric underneath completely intact"),
          ("A final hard cut transitions to", "a clean wide hero shot",
           "%s standing alone on a bare rock at altitude" % BAG,
           "scuffed and stained but whole, the low sun coming up behind it and the wind "
           "moving its loose strap, empty mountains all around and no people in frame")],
         "whitewater roaring over stone, then a fire crackling and embers popping in the "
         "quiet, then frost splitting with a fine crackle, and finally wind over open rock "
         "with one low sustained note rising underneath")},
]}
