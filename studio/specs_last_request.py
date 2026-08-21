# THE LAST REQUEST - a two-minute short with spoken dialogue.
#
# Six scenes, one location, one face. Written to play to exactly what LTX-2.5 turned out to
# be good at and around what it is not:
#
#   it speaks through a visible mouth        -> every line belongs to the man on screen
#   it will not narrate over a plate         -> no voiceover anywhere
#   it will not write music                  -> the record is heard, never scored
#   cross-scene identity is prompt-only      -> all six scenes start from ONE keyframe
#   whatever is not restated at a cut is lost -> he is re-identified at every cut
#
# The turn is that it is the station's last night, and he does not say so until the end.
HIM = ("the radio host in his fifties, grey stubble, black headphones around his neck, "
       "dark shirt with the sleeves rolled")
ROOM = ("a small late-night radio booth, one warm desk lamp, a microphone on a boom, a "
        "wall of faders, a window behind showing a dark city")
LOOK = ("photoreal cinematic film still, 35mm, warm practical light, shallow depth of "
        "field, high detail, colour photograph, filmic grade")
NEG = ("cartoon, childish, ugly, video game, blurry, watermark, text, subtitles, captions, "
       "on-screen text, crowd")
ANCHOR = "~/shared/LTX-FILM/lr_anchor.png"


def sc(sid, seed, note, opening, cuts, sound):
    return {"id": sid, "seconds": 15, "megapixels": 1.2, "seed": seed, "neg": NEG,
            "engine": "photo", "note": note, "image": ANCHOR,
            "prompt": beats(opening + " " + LOOK, cuts, sound)}


FILM = {"assemble": "THE_LAST_REQUEST", "scenes": [

    sc("lr1", 71, "the ident",
       "A wide shot of %s: %s leans in to the microphone and says in a warm, "
       "unhurried American accent, \"It's four in the morning, and you're still here.\""
       % (ROOM, HIM),
       [("A hard cut transitions to", "a close-up", HIM,
         "who lets a small smile go and adds, \"So am I.\"")],
       "a quiet studio room tone, a chair creaking, a fader sliding, and his voice "
       "speaking the lines clearly"),

    sc("lr2", 72, "the call comes in",
       "A medium shot of %s in the booth as a line lights up on the desk in front of him "
       "and he puts his headphones on with both hands and listens, saying nothing" % HIM,
       [("A hard cut transitions to", "a tight close-up", "the same host's face",
         "listening, the light from the desk on one side of him, and he says quietly, "
         "\"Go ahead. I'm listening.\"")],
       "a phone line connecting with a soft click, headphones settling, a room tone, and "
       "his voice speaking the line clearly"),

    sc("lr3", 73, "he takes it in",
       "A close-up of %s listening without moving, his eyes down, one hand flat on the "
       "desk beside the microphone" % HIM,
       [("A hard cut transitions to", "a medium shot", HIM,
         "who nods once, leans back into the mic and answers gently, \"Then play it for "
         "her. I'll wait.\"")],
       "a faint voice on a phone line under everything, a room tone, and his voice "
       "speaking the line clearly"),

    sc("lr4", 74, "the record",
       "A close shot of the hands of %s lowering a needle onto a spinning vinyl record on "
       "a turntable beside the desk" % HIM,
       [("A hard cut transitions to", "a tight macro shot", "the same needle in the groove",
         "as the record turns under it and dust lifts off the surface"),
        ("Another hard cut transitions to", "a wide shot", HIM,
         "sitting back in his chair with his eyes closed while the record plays")],
       "a needle touching down with a crackle, an old soul record beginning to play warmly "
       "in the room, and a chair settling"),

    sc("lr5", 75, "the sign-off",
       "A close-up of %s opening his eyes and leaning back in to the microphone, who says "
       "in a warm, level accent, \"That's the last one, folks.\"" % HIM,
       [("A hard cut transitions to", "a medium shot", HIM,
         "who takes his headphones off and sets them down on the desk and adds quietly, "
         "\"Thirty years. Thank you for staying up with me.\"")],
       "the record still playing under him, headphones set down on a desk, and his voice "
       "speaking the lines clearly"),

    sc("lr6", 76, "dawn",
       "A wide shot of %s as %s reaches out and pulls the fader all the way down, and the "
       "room goes quiet" % (ROOM, HIM),
       [("A hard cut transitions to", "a wide shot", "the same booth from behind him",
         "as he stands and looks out of the window, where the first grey light is coming "
         "up over the dark city, and the desk lamp is the only thing still lit")],
       "a fader sliding down, the record cutting off, a long room tone, a chair pushed "
       "back, and distant early traffic far below"),
]}
