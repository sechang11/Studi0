# THE PITCH - all four things at once.
#
#     "what makes them draw attention in? the epic crescendo in the music, the sound
#      effects at the right time, the perfect transitions, the witty banter"
#
# That was the question a long way back, and until tonight none of the four were available.
# Now: the transitions are LTX's own hard cuts inside one generation, the sound effects come
# out of the same pass as the picture, the banter is spoken by mouths on screen, and the
# crescendo comes from ACE-Step because LTX makes wind when asked for an orchestra.
#
# One location, two people, a car at night - because a car interior is the most reliable
# dialogue set there is: both faces available, nothing to walk out of frame, and every cut
# is a natural angle change rather than a new place to re-derive.
#
# All three scenes start from ONE keyframe, which is what holds the pair, the car and the
# light together across the film.
HER = "the woman in the dark green jacket in the left-hand seat"
HIM = "the man in the grey hooded sweatshirt at the wheel"
LOOK = ("photoreal cinematic film still, 35mm, shallow depth of field, hard streetlight "
        "and dashboard glow, rain on the glass, high detail, colour photograph")
NEG = ("cartoon, childish, ugly, video game, blurry, watermark, text, subtitles, captions, "
       "on-screen text")
ANCHOR = "~/shared/LTX-FILM/pitch_anchor.png"


def sc(sid, seed, note, opening, cuts, sound):
    return {"id": sid, "seconds": 15, "megapixels": 1.2, "seed": seed, "neg": NEG,
            "engine": "photo", "note": note, "image": ANCHOR,
            "prompt": beats(opening + " " + LOOK, cuts, sound)}


FILM = {"scenes": [

    sc("pt1", 601, "the setup",
       "A wide two-shot from the bonnet looking in through a rain-streaked windscreen: %s "
       "sits in a parked car at night with %s beside her at the wheel, streetlight "
       "coming through the water on the glass, neither of them moving." % (HER, HIM),
       [("A hard cut transitions to", "a close-up", HER,
         "who does not look across and says flatly in an American accent, \"Say it again.\"")],
       "heavy rain drumming on a car roof and windscreen, a wiper parked and still, an "
       "engine ticking as it cools, and her voice speaking the line clearly"),

    sc("pt2", 602, "the banter",
       "A close-up of %s at the wheel, lit from the side by a streetlight through "
       "wet glass, who spreads both hands and says brightly in an American accent, "
       "\"Nobody is going to be looking at the door.\"" % HIM,
       [("A hard cut transitions to", "a close-up", HER,
         "who turns her head an inch towards him and answers, dry, \"They are always "
         "looking at the door.\""),
        ("Another hard cut transitions to", "a medium two-shot", "the pair of them",
         "sitting in silence while the rain runs down the windscreen between them and the "
         "streetlight swings")],
       "rain on glass, a seat creaking, both of their voices speaking their lines clearly, "
       "and a car passing outside with a wash of water"),

    sc("pt3", 613, "the go",
       "A close-up of %s, who looks straight ahead through the windscreen, breathes out "
       "once, and says quietly in an American accent, \"Then look at me instead.\"" % HER,
       [("A hard cut transitions to", "a tight macro shot",
         "her hand low on the interior door handle beside her knee",
         "as her fingers close around it and pull it towards her"),
        ("Another hard cut transitions to", "a medium two-shot",
         "the pair of them still in their seats",
         "as her door swings open beside her and cold blue street light and the noise of "
         "the rain pour into the car across both of them")],
       "her voice speaking the line clearly, one breath, a door latch releasing with a "
       "hard click, then the rain outside suddenly loud in the cabin and a seatbelt "
       "retracting"),
]}
