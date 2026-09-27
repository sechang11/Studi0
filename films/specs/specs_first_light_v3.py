# FIRST LIGHT v3 - the anime short, rebuilt on everything the night learned.
#
# v2 was the first thing LTX made and it shows: the keyframes were left over from the H3
# pass, so the backgrounds wander inside a scene, and every keyframe ran at IPAdapter 0.6,
# which is the weight that turns a wide shot into a portrait.
#
# v3 fixes both. Each scene gets its OWN keyframe made at ipa 0.3 so the scene description
# survives, and the two-hander scenes still come from the masked two-character workflow
# because one PLUS FACE reference is applied to every face in the frame.
LW = ("the young swordswoman with very long straight black hair and a white and "
      "jade-green hanfu")
HAT = "the tall figure in the all-black travelling robe and wide dark straw hat"
TAGS = ("1girl, long black hair, very long hair, straight hair, jade hairpin, brown eyes, "
        "white and jade-green hanfu, straight sword")
CEL = ("The whole scene stays flat cel-shaded hand-drawn 2D anime with clean line art and "
       "painted background art throughout")
NEG = ("photorealistic, live action, 3d render, cgi, realistic skin, blurry, ugly, "
       "deformed, watermark, text")

FILM = {"scenes": [
    {"id": "fl3_dawn", "seconds": 20, "megapixels": 1.2, "seed": 5, "neg": NEG,
     "engine": "anime", "sheet": "sheet_liwen.png", "tags": TAGS, "kseed": 91, "ipa": 0.3,
     "size": (1216, 832), "note": "wide form -> turn -> close",
     "keyframe": ("standing alone at the centre of a wide misty flagstone courtyard of a "
                  "mountain sword school at dawn, straight sword held low, pine trees and "
                  "a tiled gate behind her, full body, wide shot"),
     "prompt": beats(
         "A wide establishing shot in flat cel-shaded 2D anime: %s stands alone on the "
         "misty flagstone courtyard at dawn and steps forward, sweeping her straight sword "
         "up across the frame in one long cut, her wide silk sleeves flaring" % LW,
         [("A hard cut transitions to", "a medium shot", LW,
           "turning her whole body through a second cut so her hair and sleeves trail "
           "round after her, mist swirling in her wake"),
          ("Another hard cut transitions to", "a tight close-up",
           "the same swordswoman's face",
           "calm and steady as she draws the blade back beside her head and holds still. "
           + CEL)],
         "a steady wind moving through pine trees for the whole shot and never stopping, "
         "with a blade cutting air in long arcs over it, silk snapping, one measured "
         "footfall on wet stone and a distant temple bell")},

    {"id": "fl3_arrival", "seconds": 20, "megapixels": 1.2, "seed": 6, "neg": NEG,
     "engine": "anime", "sheet": "sheet_stranger.png", "tags": "1boy, solo", "kseed": 92, "ipa": 0.3,
     "size": (1216, 832), "note": "climb -> gate -> hand",
     "keyframe": ("a tall figure in an all-black travelling robe and a wide dark conical "
                  "straw hat, face hidden in shadow, climbing a long flight of worn stone "
                  "steps cut into a misty pine mountainside, paper lanterns on posts, seen "
                  "from above and behind, wide shot"),
     "prompt": beats(
         "A wide shot in flat cel-shaded 2D anime, seen from above and behind: %s climbs a "
         "long flight of worn stone steps into the mist, his black robe dragging in the "
         "wind and the mist rolling down past him the other way" % HAT,
         [("A hard cut transitions to", "a low-angle medium shot", HAT,
           "reaching the top of the steps and stopping dead before a closed timber gate"),
          ("Another hard cut transitions to", "a tight close-up", "his gloved hand",
           "laid flat on the wet timber of the gate as the wood shifts under it. " + CEL)],
         "slow heavy footsteps on wet stone, a robe snapping in wind, a crow calling, then "
         "the wind dropping to silence and a heavy latch shifting")},

    {"id": "fl3_duel", "seconds": 20, "megapixels": 1.2, "seed": 7, "neg": NEG,
     "image": "~/shared/EPISODE/s3_duel_wp1.png", "note": "charge -> clash -> apart",
     "prompt": beats(
         "A wide shot in flat cel-shaded 2D anime: %s and %s stand far apart across a wide "
         "flagstone courtyard with dead pine needles blowing between them, then both break "
         "into a run straight at each other, needles thrown up under their feet"
         % (LW, HAT),
         [("A hard cut transitions to", "a medium shot", "the two of them",
           "crashing together in the centre with their blades locked hard and orange sparks "
           "bursting off the steel between them"),
          ("Another hard cut transitions to", "a wide shot", "the two of them",
           "breaking the bind and stepping through past each other to opposite sides of the "
           "frame, then stopping back to back, absolutely still. " + CEL)],
         "a steady wind through pines running under the whole shot and never stopping, with "
         "two sets of running footfalls on stone over it, a violent steel clash and sparks, "
         "and blades grinding apart")},

    {"id": "fl3_first", "seconds": 20, "megapixels": 1.2, "seed": 8, "neg": NEG,
     "image": "~/shared/EPISODE/s4_firstlight_wp1.png", "note": "bow -> departure -> sun",
     "prompt": beats(
         "A medium two-shot in flat cel-shaded 2D anime: %s lowers her sword and %s bows "
         "deeply to her with both hands together, the mist burning off the flagstones "
         "around them" % (LW, HAT),
         [("A hard cut transitions to", "a wide shot", HAT,
           "turning and walking away across the courtyard towards the tiled gate while she "
           "stays exactly where she is and watches him go"),
          ("Another hard cut transitions to", "a low-angle wide shot", LW + " alone",
           "as the first sun breaks over the ridge behind her and floods the courtyard, and "
           "she slides the sword home and lifts her head into the light. " + CEL)],
         "a steady wind through pines running under the whole shot and never stopping, with "
         "cloth folding over it, receding footsteps on stone, birds starting, a blade "
         "sliding home into a scabbard and one temple bell")},
]}
