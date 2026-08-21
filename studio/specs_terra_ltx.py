# TERRA through LTX-2.5 - the anime character work, upgraded.
#
# Her H3 set was the first thing this project made that drew "this is perfect, let's make
# some more". Those were 5.2s single shots: one spell, one pose, one feat each, no cutting,
# and every clip forced to 9:16 portrait by a hardcoded node nobody had noticed.
#
# These are 15s, widescreen, one generation apiece with two hard cuts - so a spell now has
# a cast, an impact and a reaction instead of just a flash.
#
# Keyframes still come from her own path, which the identity test scored as the strongest
# combination here: animagine, her reference sheet through IPAdapter, and her tags. LTX
# only has to move what that gives it - and batch two established that a style survives the
# motion pass as long as the video prompt keeps asking for it, which is what CEL does.
#
# `solo` is dropped wherever a beast shares the frame. It is a danbooru tag that actively
# suppresses a second subject, which is why an earlier beast refused to appear at all.
SOLO = ("terra branford (final fantasy vi), 1girl, solo, long wavy green hair, very long "
        "hair, green eyes, red hair ribbon")
WITH = SOLO.replace("1girl, solo, ", "1girl, ")
HER = "the green-haired sorceress in the red hair ribbon"
CEL = ("The whole scene stays flat cel-shaded hand-drawn 2D anime with clean line art and "
       "painted background art throughout")
NEG = ("photorealistic, live action, 3d render, cgi, realistic skin, blurry, lowres, bad "
       "anatomy, bad hands, extra limbs, watermark, signature, text, nudity, nsfw")

FILM = {"assemble": "TERRA_LTX", "scenes": [

    {"id": "tx_fire", "seconds": 15, "megapixels": 1.2, "seed": 401, "neg": NEG,
     "engine": "anime", "sheet": "sheet_anime_terra.png", "tags": WITH, "kseed": 41,
     "ipa": 0.3,
     "size": (1216, 832), "note": "cast -> impact -> reaction",
     "keyframe": ("standing braced with one arm thrown forward on a ruined stone bridge at "
                  "night, facing a huge snarling black wolf-beast with burning orange eyes"),
     "prompt": beats(
         "A wide shot in flat cel-shaded 2D anime: %s stands braced on a ruined stone "
         "bridge at night with one arm thrown forward, and a wall of fire bursts from her "
         "hand across the bridge" % HER,
         [("A hard cut transitions to", "a medium shot",
           "the huge snarling black wolf-beast with burning orange eyes",
           "as the fire slams into it and throws it sideways off its feet, embers "
           "scattering across the stone"),
          ("Another hard cut transitions to", "a tight close-up", "the same sorceress",
           "lowering her arm, her face lit orange, embers drifting past her. " + CEL)],
         "a beast roaring, an ignition whoomph and a wall of flame, a heavy impact and a "
         "yelp, then embers ticking and settling")},

    {"id": "tx_ice", "seconds": 15, "megapixels": 1.2, "seed": 402, "neg": NEG,
     "engine": "anime", "sheet": "sheet_anime_terra.png", "tags": SOLO, "kseed": 42,
     "size": (1216, 832), "note": "cast -> crystal macro -> crossing",
     "keyframe": ("standing at the edge of a deep misty chasm with one hand extended over "
                  "the drop, mountain pass, morning"),
     "prompt": beats(
         "A wide shot in flat cel-shaded 2D anime: %s stands at the edge of a deep misty "
         "chasm with one hand held out over the drop, and a bridge of ice crystallises "
         "outward from her hand in jagged plates across the gap" % HER,
         [("A hard cut transitions to", "a tight macro shot", "the growing ice",
           "as plates fracture and lock into one another and frost races along the edges"),
          ("Another hard cut transitions to", "a wide shot", "the same sorceress",
           "walking out onto the finished ice bridge with mist pouring past below her. "
           + CEL)],
         "a crystalline crackle spreading fast, ice groaning under its own weight, and "
         "wind moving through a deep chasm")},

    {"id": "tx_dance", "seconds": 15, "megapixels": 1.2, "seed": 403, "neg": NEG,
     "engine": "anime", "sheet": "sheet_anime_terra.png", "tags": SOLO, "kseed": 43,
     "ipa": 0.3,
     "size": (1216, 832), "note": "wide routine -> spin -> held pose",
     "keyframe": ("standing at the centre of a lantern-lit stone plaza at night, arms low, "
                  "skirt still, lanterns strung overhead"),
     "prompt": beats(
         "A wide shot in flat cel-shaded 2D anime: %s sweeps into a dance across a "
         "lantern-lit stone plaza at night, turning so her skirt flares and her arms carve "
         "up and across" % HER,
         [("A hard cut transitions to", "a medium shot", "the same sorceress",
           "spinning through a full turn with her long hair and skirt trailing round after "
           "her and the lantern light streaking behind"),
          ("Another hard cut transitions to", "a low-angle shot", "the same sorceress",
           "dropping into a final held pose with one arm raised, the lanterns swinging "
           "above her. " + CEL)],
         "a rhythmic drum and string melody, cloth whipping round, and footfalls landing on "
         "stone in time")},

    {"id": "tx_close", "seconds": 15, "megapixels": 1.2, "seed": 404, "neg": NEG,
     "engine": "anime", "sheet": "sheet_anime_terra.png", "tags": SOLO, "kseed": 44,
     "size": (896, 1216), "note": "the cute beat, close and legible",
     "keyframe": ("upper body portrait, close on her face, smiling warmly at the viewer, "
                  "soft sunlit background, petals in the air"),
     "prompt": beats(
         "An upper body portrait in flat cel-shaded 2D anime, close on the face of %s: she "
         "closes one eye in a slow deliberate wink and her smile widens as she tilts her "
         "head" % HER,
         [("A hard cut transitions to", "a tight close-up", "the same sorceress",
           "pressing two fingers to her lips and sweeping her hand outward, small glowing "
           "hearts trailing off her fingertips. " + CEL)],
         "a soft sparkle chime, a gentle breeze through petals, and a light laugh")},
]}
