# AT THE GATE - anime dialogue, cut the way anime is actually cut.
#
# LTX speaks in cel anime but does NOT move the drawn mouth: measured, the mouth region
# changes 0.43x as much as the whole frame against 1.01x for a photoreal talking head, and
# visually it is a closed line for every frame of the line. Voice yes, lip sync no.
#
# That is a scheduling problem, not a wall. Limited animation has always played dialogue
# over anything but a moving mouth - an over-shoulder, a back of head, the listener
# reacting, a hand on a hilt, a wide of the courtyard. So every line here lands on a
# CUTAWAY, and the speaker's face is only ever on screen in silence.
#
# Scene structure, three times over:
#   the speaker is established        (no line yet)
#   HARD CUT to something that is not their mouth, and the line plays there
#   HARD CUT back for the reaction    (silent)
LW = ("the young swordswoman with very long straight black hair and a white and "
      "jade-green hanfu")
HAT = "the tall figure in the all-black travelling robe and wide dark straw hat"
CEL = ("The whole scene stays flat cel-shaded hand-drawn 2D anime with clean line art and "
       "painted background art throughout")
NEG = ("photorealistic, live action, 3d render, cgi, realistic skin, blurry, ugly, "
       "deformed, subtitles, captions, on-screen text")
E = "~/shared/EPISODE"


def sc(sid, seed, img, note, opening, cuts, sound, ipa=None):
    d = {"id": sid, "seconds": 15, "megapixels": 1.2, "seed": seed, "neg": NEG,
         "note": note, "image": img, "prompt": beats(opening, cuts, sound)}
    return d


FILM = {"assemble": "AT_THE_GATE", "scenes": [

    sc("gt1", 501, E + "/s2_arrival_wp3.png", "his line, over the gate",
       "A low-angle wide shot in flat cel-shaded 2D anime: %s stands at the top of the "
       "worn stone steps in front of a closed timber gate, mist streaming past him, and he "
       "lifts his head towards it without speaking" % HAT,
       [("A hard cut transitions to", "a tight close-up", "his gloved hand on the timber",
         "pressing flat against the wet wood, and his voice says from off screen in a low "
         "even tone, \"Open it, or I will.\""),
        ("Another hard cut transitions to", "a wide shot", "the same figure in black",
         "standing motionless before the gate as the wind drops away and the mist settles "
         "around his boots. " + CEL)],
       "wind falling away over stone, a hand on wet timber, his voice speaking the line "
       "clearly from off screen, and a heavy latch shifting"),

    sc("gt2", 502, E + "/s1_dawn_wp4.png", "her line, over the blade",
       "A medium shot in flat cel-shaded 2D anime: %s stands on the misty flagstone "
       "courtyard on the other side of the gate, her straight sword still sheathed, and "
       "she turns her head towards the sound without speaking" % LW,
       [("A hard cut transitions to", "a tight close-up", "her hand closing on the scabbard",
         "as her thumb pushes the guard a finger's width clear of the mouth, and her voice "
         "says from off screen, level and quiet, \"Then it is already open.\""),
        ("Another hard cut transitions to", "a low-angle shot", "the same swordswoman",
         "standing square to the gate with her sleeves lifting in the draught, saying "
         "nothing. " + CEL)],
       "a sword guard clicking clear of a scabbard mouth, silk lifting in a draught, her "
       "voice speaking the line clearly from off screen, and wind through pines"),

    sc("gt3", 503, E + "/s3_duel_wp1.png", "the last line, over the courtyard",
       "A wide shot in flat cel-shaded 2D anime: the timber gate swings inward and %s and "
       "%s stand facing each other across the empty flagstone courtyard with dead pine "
       "needles blowing between them" % (LW, HAT),
       [("A hard cut transitions to", "an overhead view", "the courtyard from far above",
         "with the two small figures at opposite ends of the flagstones and the needles "
         "turning between them, and her voice says from off screen, almost kindly, "
         "\"You should have come at dawn.\""),
        ("Another hard cut transitions to", "a medium shot", "the two of them",
         "drawing their blades at the same moment, and holding absolutely still. " + CEL)],
       "a heavy gate swinging inward, needles skittering over stone, her voice speaking the "
       "line clearly from off screen, then two blades leaving their scabbards together and "
       "silence"),
]}
