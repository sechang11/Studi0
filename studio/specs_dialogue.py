# DOES LTX-2.5 SPEAK? The one capability this project has never had.
#
#     "what makes them draw attention in? ... the witty banter"
#
# That was asked months of work ago and there has never been an answer, because every video
# engine here was silent or made effects only. H3 turned out to make real pitch - a cello
# note at a stable 124 Hz - but never a word. LTX-2.5's guide says to put spoken dialogue in
# quotation marks and to name the language and accent, which implies actual speech.
#
# Three tests, cheapest first:
#   one_line    a single close-up, one sentence. Does a mouth move in time with words?
#   banter      two characters, a line each across a cut. Does the voice survive the cut?
#   vo          narration over a shot with nobody in it - the easy case, no lip sync needed
#
# All characters are invented. No real person is referenced, and the blocked voice packs in
# studio/voices are not involved in any way - this is the model's own synthesis.
LOOK = ("photoreal cinematic film still, 35mm, shallow depth of field, warm practical "
        "light, high detail, colour photograph")
NEG = "cartoon, childish, ugly, video game, blurry, watermark, text, subtitles, captions"

FILM = {"scenes": [

    {"id": "dlg_one_line", "seconds": 8, "megapixels": 1.2, "seed": 51, "neg": NEG,
     "engine": "photo", "note": "single line, lip sync?",
     "keyframe": "a woman in her thirties in a green work jacket sitting at a diner "
                 "counter at night, coffee in front of her, neon through the window "
                 "behind, looking straight at camera",
     "prompt": beats(
         "A tight close-up: a woman in her thirties in a green work jacket sits at a diner "
         "counter at night with neon behind her, looks straight down the lens and says in "
         "a calm American accent, \"You said the same thing last year, and I still paid "
         "for the coffee.\" She raises her eyebrows and lifts her cup. %s" % LOOK,
         [],
         "her voice speaking the line clearly in a quiet diner, a cup set down on a "
         "counter, a refrigerator hum and faint traffic outside")},

    {"id": "dlg_banter", "seconds": 12, "megapixels": 1.2, "seed": 52, "neg": NEG,
     "engine": "photo", "note": "line each across a cut",
     "keyframe": "two people sitting opposite each other in a diner booth at night, a "
                 "woman in a green work jacket on the left and a man in a grey hoodie on "
                 "the right, neon through the window, coffee cups between them",
     "prompt": beats(
         "A medium two-shot in a diner booth at night: a woman in a green work jacket sits "
         "opposite a man in a grey hoodie, and she leans back and says in a dry American "
         "accent, \"You have exactly one good idea a year.\" %s" % LOOK,
         [("A hard cut transitions to", "a close-up",
           "the same man in the grey hoodie",
           "who shrugs, grins and answers in an American accent, \"Then this is the "
           "year, and you are buying.\" He picks up his cup")],
         "the two of them speaking their lines clearly in a quiet diner, cups on a table, "
         "a refrigerator hum and faint traffic outside")},

    {"id": "dlg_vo", "seconds": 10, "megapixels": 1.2, "seed": 53, "neg": NEG,
     "engine": "photo", "note": "narration with nobody in shot",
     "keyframe": "a worn olive canvas backpack alone on a bare wet rock at altitude at "
                 "dawn, mountains falling away behind it, no people",
     "prompt": beats(
         "A slow wide shot with no people in frame: a worn olive canvas backpack stands "
         "alone on a bare wet rock at altitude while cloud drives past the peaks below and "
         "the wind moves its loose strap. A calm male narrator says over the top, in an "
         "English accent, \"Everything you own is on loan. This one is not.\" %s" % LOOK,
         [],
         "wind over open rock, and a calm male voice speaking the narration clearly over "
         "the top of it")},
]}
