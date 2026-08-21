# Two hero shots at the top of the measured envelope: 2.0 MP -> 1920x1088, 8s.
# (4 * 2.0) * 193 = 1544, comfortably inside the 2600 cliff. 2.5 MP is fatal.
NEG_P = "cartoon, childish, ugly, video game, blurry, watermark, text, logo"
NEG_A = "photorealistic, live action, 3d render, cgi, realistic skin, blurry, ugly"
CEL = ("The whole shot stays flat cel-shaded hand-drawn 2D anime with clean line art "
       "throughout")

FILM = {"scenes": [
    {"id": "hero_anime", "seconds": 8, "megapixels": 2.0, "seed": 41, "neg": NEG_A,
     "engine": "anime", "sheet": "sheet_liwen.png", "size": (1216, 832),
     "tags": ("1girl, solo, long black hair, very long hair, straight hair, jade hairpin, "
              "brown eyes, pale skin, white and jade-green hanfu, straight sword"),
     "note": "1080p anime hero",
     "keyframe": ("standing under a blossoming plum tree on a stone terrace at dusk, "
                  "petals falling around her, lanterns lit behind, mountains beyond"),
     "prompt": beats(
         "A medium shot in flat cel-shaded 2D anime: a young swordswoman with very long "
         "straight black hair and a white and jade-green hanfu stands under a blossoming "
         "plum tree on a stone terrace at dusk, and a gust lifts a cloud of petals off the "
         "branches and carries them sideways across the frame, her sleeves and hair "
         "streaming with it",
         [("A hard cut transitions to", "a tight close-up",
           "the same swordswoman's face",
           "as she closes her eyes and opens them again, petals passing across the frame "
           "in front of her. " + CEL)],
         "a soft gust through blossom, cloth moving, a single low temple bell and distant "
         "evening birds")},

    {"id": "hero_atlas", "seconds": 8, "megapixels": 2.0, "seed": 42, "neg": NEG_P,
     "engine": "photo", "size": (1216, 832), "note": "1080p product hero",
     "keyframe": ("a worn olive canvas backpack with leather straps and a brass buckle "
                  "standing alone on a bare wet rock at altitude, low sun behind it, "
                  "mountains falling away, no people"),
     "prompt": beats(
         "A slow wide hero shot with no people in frame: a worn olive canvas backpack with "
         "leather straps and a brass buckle stands alone on a bare wet rock at altitude, "
         "scuffed and stained but whole, while the low sun climbs behind it and the wind "
         "moves its loose strap and drives cloud past the peaks below. Shot on 35mm with "
         "an anamorphic lens, high contrast, teal and amber grade, sharp and detailed",
         [("A hard cut transitions to", "a tight macro shot",
           "the brass buckle and waxed canvas of the same backpack",
           "with water beading on the weave and the low sun raking across it, still no "
           "people in frame")],
         "wind over open rock, canvas and webbing moving, and one low sustained note "
         "rising underneath")},
]}
