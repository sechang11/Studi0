# ATLAS - the torture-test commercial, finally shot the way it was asked for.
#
#     "a bag gets tossed. many cinematic shots. it gets run over by a car. it gets dragged
#      in an army training camp. it goes through the worst conditions, and survives them
#      all. then Atlas is revealed as the brand in the end. think of it as a short movie."
#
# That brief needed CUTS, and until tonight a cut meant a separate generation, which meant
# a different bag in every shot. Each film below is ONE generation containing three or four
# real cuts, so it is the same bag all the way through and one continuous soundtrack.
#
# ATLAS is this project's own invented brand. No real brand, logo or product appears.
BAG = "the same worn olive canvas backpack with leather straps and a brass buckle"
LOOK = ("shot on 35mm with an anamorphic lens, high contrast, teal and amber grade, "
        "shallow depth of field, cinematic commercial photography, sharp and detailed")
NEG = "cartoon, childish, ugly, video game, blurry, watermark, text, logo, brand name"

FILM = {"assemble": "ATLAS_LTX", "scenes": [

    # 1. THE TORTURE. Every beat is a force with a direction - the rule that separated the
    #    torture shots that worked from the one where the bag just sat there.
    {"id": "atlas_a", "seconds": 20, "megapixels": 1.2, "seed": 21, "neg": NEG,
     "note": "thrown -> run over -> dragged", "engine": "photo",
     "keyframe": "a worn olive canvas backpack with leather straps and a brass buckle "
                 "lying on wet grey asphalt at dawn, low camera, wide empty road, mist",
     "prompt": beats(
         "A low wide shot on wet asphalt at dawn: %s is hurled in from the left and hits "
         "the road hard, tumbling twice and skidding to a stop, grit spraying off it. %s"
         % (BAG, LOOK),
         [("A hard cut transitions to", "a low tracking shot",
           "%s lying in the road" % BAG,
           "as the tyre of a heavy truck rolls straight over it and presses it flat into "
           "the wet asphalt, water bursting out sideways from under the tread"),
          ("Another hard cut transitions to", "a side-on tracking shot",
           "%s" % BAG,
           "being dragged fast across a churned mud training ground on the end of a rope, "
           "throwing up a long spray of mud behind it, boots running past on both sides")],
         "a heavy canvas impact and skid on wet road, a truck tyre crushing down through "
         "standing water, rope creaking under load and mud spraying")},

    # 2. THE WORST CONDITIONS, then the turn.
    {"id": "atlas_b", "seconds": 20, "megapixels": 1.2, "seed": 22, "neg": NEG,
     "note": "river -> fire -> ice -> reveal", "engine": "photo",
     "keyframe": "a worn olive canvas backpack with leather straps and a brass buckle "
                 "half-submerged in a fast rocky river, whitewater breaking over it, "
                 "cold morning light",
     "prompt": beats(
         "A close tracking shot: %s is swept sideways down a fast rocky river, whitewater "
         "breaking over it and rolling it against the stones. %s" % (BAG, LOOK),
         [("A hard cut transitions to", "a slow low shot",
           "%s" % BAG,
           "sitting beside a burning campfire as sparks and embers blow across it and one "
           "ember lands on the canvas and dies out without catching"),
          ("Another hard cut transitions to", "a tight macro shot",
           "the frozen surface of %s" % BAG,
           "as a gloved hand cracks a shell of ice off the canvas and the fabric "
           "underneath is completely intact"),
          ("A final hard cut transitions to", "a clean wide hero shot",
           "%s standing alone on a bare rock at altitude" % BAG,
           "scuffed and stained but whole, the low sun coming up behind it and the wind "
           "moving the loose strap")],
         "whitewater roaring over stone, then a fire crackling and embers popping, then "
         "ice cracking off stiff canvas, and finally wind over open rock and one low "
         "sustained note rising underneath")},
]}
