# THE LIBRARY, RE-SHOT. Six product spots, each one generation with real cuts.
#
# The existing library clips are 5.2 s single shots from H3 - one gesture each, no cutting,
# because a cut used to mean a second generation and a second generation used to mean a
# different product. Each of these is 15 s containing two hard cuts, so every item now has
# an actual spot instead of a moving product photo.
#
# All six brands are the project's own invented ones. No real brand appears.
#
# Every action is still a FORCE WITH A DIRECTION - the rule that separated the torture
# shots that worked from the one where the bag just sat there - and no shot names a person,
# because naming any human body part makes LTX grow a whole model who takes over the frame.
LOOK = ("shot on 35mm, shallow depth of field, high detail, colour photograph, commercial "
        "product cinematography, no people in frame")
NEG = ("cartoon, childish, ugly, video game, blurry, watermark, text, logo, brand name, "
       "person, model, hands, face")


def spot(sid, seed, keyframe, opening, cut1, cut2, sound):
    return {"id": sid, "seconds": 15, "megapixels": 1.2, "seed": seed, "neg": NEG,
            "engine": "photo", "note": sid, "keyframe": keyframe + ". " + LOOK,
            "prompt": beats(opening + " " + LOOK, [cut1, cut2], sound)}


FILM = {"assemble": "LIBRARY_LTX", "scenes": [

    spot("lib_atlas", 101,
         "a worn olive canvas backpack with leather straps on a bare rock at altitude, "
         "low sun, mountains behind, no people",
         "A wide shot with no people in frame: a worn olive canvas backpack with leather "
         "straps stands on a bare rock at altitude as wind drives cloud past the peaks "
         "behind it and moves its loose strap.",
         ("A hard cut transitions to", "a tight macro shot",
          "the brass buckle and waxed canvas of the same backpack",
          "as rain begins to fall on it and beads across the weave without soaking in, "
          "the frame completely empty of people"),
         ("Another hard cut transitions to", "a low wide shot",
          "the same backpack",
          "now sunlit and steaming dry on the same rock, the storm moving off behind it, "
          "the frame still completely empty of people"),
         "wind over open rock, canvas and webbing moving, rain arriving hard on fabric and "
         "then easing away"),

    spot("lib_lumen", 102,
         "a minimal black desk lamp on an empty oak desk in a dark room, one warm pool of "
         "light, no people",
         "A slow wide shot in a dark room with no people in frame: a minimal black desk "
         "lamp throws one warm pool of light across an empty oak desk, and the arm swings "
         "down so the pool slides across the wood and sharpens.",
         ("A hard cut transitions to", "a tight macro shot",
          "the edge of the same lamp's shade",
          "where the light falls off into darkness across the grain of the desk"),
         ("Another hard cut transitions to", "a wide shot",
          "the same lamp and desk",
          "as the rest of the room lights come up and the lamp's pool disappears into "
          "daylight"),
         "a metal hinge creaking under load, a switch clicking, and a very quiet room"),

    spot("lib_northwind", 103,
         "loose black tea leaves beside a clear glass teapot on a pale stone counter, "
         "steam, no people",
         "A close shot with no people in frame: hot water pours into a clear glass teapot "
         "of loose black tea leaves and the leaves lift and turn and the water darkens "
         "from clear to deep amber.",
         ("A hard cut transitions to", "a tight macro shot",
          "a single tea leaf inside the same teapot",
          "unfurling slowly in the moving water"),
         ("Another hard cut transitions to", "a wide shot",
          "the same glass teapot",
          "now full and still on the stone counter, steam rising straight up off it"),
         "water pouring and boiling, glass ticking as it heats, and a quiet kitchen"),

    spot("lib_pace", 104,
         "a single running shoe on wet black tarmac at dawn, cold blue light, puddles, "
         "no people",
         "A low close shot with no people in frame: a single running shoe stands on wet "
         "black tarmac at dawn and a hard gust drives a sheet of rainwater sideways across "
         "the road past it.",
         ("A hard cut transitions to", "a tight macro shot",
          "the tread of the same shoe",
          "as water is forced up out of the grooves and runs off the rubber"),
         ("Another hard cut transitions to", "a wide shot",
          "the same shoe on the empty road",
          "as the first sun comes up the tarmac behind it and the wet surface turns gold"),
         "hard rain on tarmac and standing water, wind, then the rain stopping and a "
         "distant early city"),

    spot("lib_slowsunday", 105,
         "an unmade bed with morning light across white linen, a curtain at the window, "
         "empty room, no people",
         "A slow wide shot with no people in frame: morning light lies in a band across "
         "the white linen of an unmade bed, and the curtain lifts on a draught so the band "
         "of light slides across the sheets.",
         ("A hard cut transitions to", "a tight macro shot",
          "the weave of the same linen",
          "with dust turning slowly through the shaft of light above it"),
         ("Another hard cut transitions to", "a wide shot",
          "the same bed and window",
          "as the light broadens and fills the whole room"),
         "fabric moving on a draught, a room tone, and birds outside a window"),

    spot("lib_tidewater", 106,
         "a single plain unlabelled glass bottle alone on wet dark stone at the shore, "
         "soft grey sea light, deserted, no people, no glasses, no hands",
         "A close shot with no people in frame: a plain unlabelled glass bottle stands on "
         "wet dark stone and a wave washes across the rock and past it, foaming and "
         "draining away around the base.",
         ("A hard cut transitions to", "a tight macro shot",
          "the shoulder of the same bottle",
          "as seawater sheets off the glass and beads run down it, the frame completely "
          "empty of people and hands"),
         ("Another hard cut transitions to", "a wide shot",
          "the same bottle on the rock",
          "with the tide gone out behind it and flat grey water to the horizon, the "
          "frame still completely empty of people and hands"),
         "a wave breaking and draining over stone, water running off glass, gulls and a "
         "wide open shore"),
]}
