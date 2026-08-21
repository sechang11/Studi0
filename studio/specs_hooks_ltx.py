# THE HOOKS, re-shot. Six atmospheric openers, each one generation with two hard cuts.
#
# These are the library's teasers - places, not products, with nothing to sell in frame.
# The old versions were 5.2s single shots. Each of these is 15s and cuts twice, which is
# what a hook actually needs: a wide that sets the place, a detail that makes it real, and
# a return that pays it off.
#
# THE EMPTY FRAME IS RE-STATED AT EVERY CUT, because saying it once in the opening was not
# enough on the product set - two of six grew a person after the first cut even with
# person/hands/face in the negative. Each cut is a fresh shot description, and an absence
# has to be re-declared exactly like a character does.
LOOK = ("shot on 35mm, anamorphic, shallow depth of field, high detail, colour photograph, "
        "cinematic, no people in frame")
NEG = ("cartoon, childish, ugly, video game, blurry, watermark, text, logo, person, model, "
       "hands, face, crowd")
EMPTY = "the frame completely empty of people"


def hook(sid, seed, keyframe, opening, c1, c2, sound):
    return {"id": sid, "seconds": 15, "megapixels": 1.2, "seed": seed, "neg": NEG,
            "engine": "photo", "note": sid, "keyframe": keyframe + ". " + LOOK,
            "prompt": beats(opening + " " + LOOK, [c1, c2], sound)}


FILM = {"assemble": "HOOKS_LTX", "scenes": [

    hook("hk_door", 201,
         "extreme low angle on the floor at the foot of a closed panelled door, a bright "
         "line of light under it across worn lino, the door filling the frame, deserted",
         "An extreme low angle shot from the floor, the closed panelled door filling the "
         "whole frame with a bright line of light beneath it: the line of light widens "
         "into a hard wedge across the worn lino as a draught pushes the door open above "
         "camera. Empty floor, no feet, no legs, no figure anywhere in frame.",
         ("A hard cut transitions to", "a tight macro shot", "the edge of the same door",
          "where the light cuts a hard line across the worn lino, dust turning in it, "
          + EMPTY),
         ("Another hard cut transitions to", "a low shot", "the same doorway from the floor",
          "as the wedge of light narrows back to a thin line and goes out, empty floor, "
          "no feet and no legs, " + EMPTY),
         "a latch releasing, a door swinging on a dry hinge, a deep empty room tone, then "
         "the door closing and silence"),

    hook("hk_garden", 202,
         "a bare winter allotment of dark empty soil with a wooden fence behind, grey "
         "morning, no people",
         "A low wide shot of a bare winter allotment with no people in frame: rain starts "
         "and comes on hard, darkening the soil and beating craters into it.",
         ("A hard cut transitions to", "a tight macro shot", "the same wet soil",
          "as drops strike it and water begins to pool and run between the clods, "
          + EMPTY),
         ("Another hard cut transitions to", "a wide shot", "the same allotment",
          "as the rain stops and steam lifts off the dark ground into the cold air, "
          + EMPTY),
         "rain arriving and building hard on bare earth, water running, then the rain "
         "stopping and a hedge dripping"),

    hook("hk_library", 203,
         "a vast dim library interior, towering shelves receding into darkness, shafts of "
         "light from high windows, no people",
         "A slow wide shot inside a vast dim library with no people in frame: a single "
         "book slides itself out from a high shelf and dust lifts off it through a shaft "
         "of light.",
         ("A hard cut transitions to", "a tight macro shot", "the same book's spine",
          "turning slowly in the air with dust drifting across the gold lettering, "
          + EMPTY),
         ("Another hard cut transitions to", "a wide shot", "the same aisle of shelves",
          "as the book settles back into its gap and the dust falls through the light, "
          + EMPTY),
         "a book sliding on a wooden shelf, a deep echoing quiet, a distant footstep far "
         "away in the building"),

    hook("hk_lift", 204,
         "an old civic building lobby with terrazzo floors, brass lift doors closed, tall "
         "windows, no people",
         "A wide shot of an empty civic lobby with no people in frame: the brass lift "
         "doors slide apart and warm light spills out across the terrazzo floor.",
         ("A hard cut transitions to", "a tight macro shot", "the same brass doors",
          "where the polished metal catches the light as they open, " + EMPTY),
         ("Another hard cut transitions to", "a wide shot", "the same lobby",
          "as the doors roll shut again and the lobby returns to grey daylight, " + EMPTY),
         "a lift chime, heavy doors rolling open on runners, a big echoing lobby, then the "
         "doors closing"),

    hook("hk_signal", 205,
         "an enormous white radio dish against a grey moorland sky, wide shot, heather and "
         "grass below, no people",
         "A wide shot on open moorland with no people in frame: an enormous white radio "
         "dish rotates slowly across the grey sky while the wind flattens the grass "
         "beneath it in long waves.",
         ("A hard cut transitions to", "a low tight shot", "the base of the same dish",
          "where the drive gears turn and the steel structure shifts under load, "
          + EMPTY),
         ("Another hard cut transitions to", "a wide shot", "the same dish",
          "as it comes to rest pointing straight up and the cloud races past behind it, "
          + EMPTY),
         "a heavy motor turning under load, steel creaking, and hard wind across open moor"),

    hook("hk_lowtide", 206,
         "a harbour at low tide, wooden boats resting over on wet mud, stone quay behind, "
         "grey morning, no people",
         "A wide shot of a harbour at low tide with no people in frame: the tide floods "
         "back across the mud and the resting boats lift and swing round on their "
         "moorings.",
         ("A hard cut transitions to", "a tight macro shot", "the same mooring rope",
          "as it pulls taut and streams water while the boat comes up, " + EMPTY),
         ("Another hard cut transitions to", "a wide shot", "the same harbour",
          "now full of water with every boat floating level, " + EMPTY),
         "water moving in over soft mud, ropes creaking under load, hulls knocking, and "
         "gulls over a harbour"),
]}
