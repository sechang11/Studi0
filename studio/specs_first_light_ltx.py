# FIRST LIGHT, remade on LTX-2.5. Four scenes, each ONE generation containing real cuts.
#
# The H3 version needed sixteen generations, a sibling-waypoint scheme and an anchor pass,
# and it still had no cuts inside a scene and drifting backgrounds between segments. Each
# scene here is a single sampling pass, so there is nothing to drift, and the cuts are the
# model's own. Keyframes are the ones already approved on the H3 pass - art direction that
# has been looked at beats a fresh roll of the dice.
LW = ("the young swordswoman with very long straight black hair and a white and "
      "jade-green hanfu")
HAT = "the tall figure in the all-black travelling robe and wide dark straw hat"
CEL = ("The whole scene stays flat cel-shaded hand-drawn 2D anime with clean line art and "
       "painted background art throughout")
NEG = "photorealistic, live action, 3d render, cgi, realistic skin, blurry, ugly, deformed"
E = "~/shared/EPISODE"

FILM = {"assemble": "FIRST_LIGHT_LTX", "scenes": [
    {"id": "s1_dawn", "seconds": 20, "megapixels": 1.2, "seed": 5,
     "image": E + "/s1_dawn_wp1.png", "note": "wide -> medium turn -> close", "neg": NEG,
     "prompt": beats(
         "A wide establishing shot in flat cel-shaded 2D anime: %s stands alone on a misty "
         "flagstone courtyard of a mountain sword school at dawn, pine trees and a tiled "
         "gate behind her, and she steps forward and sweeps her straight sword up in one "
         "long cut, her wide silk sleeves flaring out with the movement" % LW,
         [("A hard cut transitions to", "a medium shot", LW,
           "who turns her whole body through a second cut so her long black hair and "
           "sleeves trail around after her, mist swirling in her wake"),
          ("Another hard cut transitions to", "a tight close-up",
           "the same swordswoman's face",
           "calm and steady, as she draws the blade back beside her head and holds still, "
           "only her hair settling. " + CEL)],
         "a blade cutting air in long arcs, silk snapping, one measured footfall on wet "
         "stone, wind through pines and a distant temple bell")},

    {"id": "s2_arrival", "seconds": 20, "megapixels": 1.2, "seed": 6,
     "image": E + "/s2_arrival_wp1.png", "note": "climb -> gate -> hand", "neg": NEG,
     "prompt": beats(
         "A wide shot in flat cel-shaded 2D anime, seen from above and behind: %s climbs a "
         "long flight of worn stone steps cut into a misty pine mountainside, paper "
         "lanterns on posts either side, and the mist rolls down past him the other way as "
         "his black robe drags in the wind" % HAT,
         [("A hard cut transitions to", "a low-angle medium shot", HAT,
           "reaching the top of the steps and stopping dead in front of a closed timber "
           "gate, the mist streaming past him"),
          ("Another hard cut transitions to", "a tight close-up", "his gloved hand",
           "as he raises it and lays it flat against the wet timber of the gate and the "
           "wood shifts under it. " + CEL)],
         "slow heavy footsteps on wet stone, a robe snapping in the wind, a crow calling, "
         "then the wind dropping away to silence and a heavy latch shifting")},

    {"id": "s3_duel", "seconds": 20, "megapixels": 1.2, "seed": 7,
     "image": E + "/s3_duel_wp1.png", "note": "charge -> clash -> apart", "neg": NEG,
     "prompt": beats(
         "A wide shot in flat cel-shaded 2D anime: %s and %s stand far apart across a wide "
         "flagstone courtyard with dead pine needles blowing between them, then both break "
         "into a run straight at each other, needles thrown up from under their feet"
         % (LW, HAT),
         [("A hard cut transitions to", "a medium shot", "the two of them",
           "crashing together in the centre with their blades locked hard, orange sparks "
           "bursting off the steel between them as both drive forward"),
          ("Another hard cut transitions to", "a wide shot", "the two of them",
           "breaking the bind and stepping through past each other to opposite sides of "
           "the frame, blades scraping apart, hair and robes swinging round after them, "
           "and coming to a stop back to back, absolutely still. " + CEL)],
         "two sets of running footfalls on stone, a violent steel clash and sparks, blades "
         "grinding apart, then silence falling and wind through pines")},

    {"id": "s4_firstlight", "seconds": 20, "megapixels": 1.2, "seed": 8,
     "image": E + "/s4_firstlight_wp1.png", "note": "bow -> departure -> sunrise",
     "neg": NEG,
     "prompt": beats(
         "A medium two-shot in flat cel-shaded 2D anime: %s lowers her sword and %s bows "
         "deeply to her with both hands together, the mist burning off the flagstones "
         "around them" % (LW, HAT),
         [("A hard cut transitions to", "a wide shot", HAT,
           "turning and walking away across the courtyard towards the tiled gate, his robe "
           "swinging, while she stays exactly where she is and watches him go"),
          ("Another hard cut transitions to", "a low-angle wide shot", LW + " alone",
           "as the first sunlight breaks over the mountain ridge behind her and floods "
           "across the courtyard, and she slides the sword back into its scabbard in one "
           "movement and lifts her head into the light. " + CEL)],
         "cloth folding and a long breath, receding footsteps on stone, then a low warm "
         "swell, birds starting, a blade sliding home into a scabbard and one temple bell")},
]}
