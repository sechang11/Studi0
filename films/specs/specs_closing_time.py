# CLOSING TIME - the first thing this studio has made that talks.
#
#     "what makes them draw attention in? ... the witty banter"
#
# That was asked a long way back and there has never been an answer. Every engine here was
# silent or made effects only; H3 turned out to make real pitch but never a word. LTX-2.5
# speaks, and the mouth moves with it - verified on a close-up where the spectrogram shows
# a voiced harmonic stack with syllable gaps and the lip crop shows real articulation.
#
# Set at the night market stall because that location has rendered reliably all night, so
# the risk sits entirely on the new thing: three scenes, two characters, one exchange.
#
# WHAT THE DIALOGUE RULES TURNED OUT TO BE:
#   * put the line in quotation marks and name the accent
#   * the speaker must be ON SCREEN. A narrator over an empty landscape produced no voice
#     at all, just wind - LTX speaks through a visible mouth, not over a plate.
#   * re-identify the speaker after every cut, exactly like any other multishot character
#   * keep the line short. One sentence per shot lands; a paragraph does not.
COOK = "the cook in the black shirt with the towel over his shoulder"
CUST = "the customer in the grey canvas jacket"
LOOK = ("photoreal cinematic film still, 35mm, deep focus, warm practical light from "
        "hanging bulbs, high detail, colour photograph, filmic grade")
NEG = ("cartoon, childish, ugly, video game, blurry, watermark, text, subtitles, "
       "captions, on-screen text")

FILM = {"assemble": "CLOSING_TIME", "scenes": [

    {"id": "ct1", "seconds": 15, "megapixels": 1.2, "seed": 61, "neg": NEG,
     "engine": "photo", "note": "arrival + first line",
     "image": "~/shared/LTX-FILM/ct_anchor.png",
     "keyframe": "a night street food stall closing up, a cook in a black shirt with a "
                 "towel over his shoulder wiping down a steel counter, one empty stool, "
                 "hanging bulbs, the lane behind him nearly empty",
     "prompt": beats(
         "A wide shot of a night street food stall almost closed: %s wipes down the steel "
         "counter under the hanging bulbs while the lane behind him stands nearly empty, "
         "and %s walks in from the left and sits down on the last stool. %s"
         % (COOK, CUST, LOOK),
         [("A hard cut transitions to", "a close-up", CUST,
           "who looks at the shuttered half of the stall and says in a level American "
           "accent, \"You're closed.\"")],
         "a steel counter being wiped, a stool scraping, a quiet lane at night with one "
         "distant scooter, and the customer's voice speaking the line clearly")},

    {"id": "ct2", "seconds": 15, "megapixels": 1.2, "seed": 62, "neg": NEG,
     "engine": "photo", "note": "the comeback + the burner",
     "image": "~/shared/LTX-FILM/ct_anchor.png",
     "keyframe": "a cook in a black shirt with a towel over his shoulder standing behind "
                 "a steel counter at a night food stall, one hand resting on a cold wok, "
                 "hanging bulbs, a customer in a grey canvas jacket seated opposite",
     "prompt": beats(
         "A close-up of %s behind the counter, who does not look up and answers in a dry "
         "accent, \"I'm closed.\" %s" % (COOK, LOOK),
         [("A hard cut transitions to", "a medium shot", CUST,
           "who tips his head towards the burner still burning blue under the wok and says "
           "in a level American accent, \"Then what's that.\""),
          ("Another hard cut transitions to", "a low shot",
           "%s's hands" % COOK,
           "as he drops a handful of noodles into the wok and it flares up hard, the flame "
           "lighting the whole counter")],
         "the cook's and the customer's voices speaking their lines clearly, a gas burner "
         "ticking then roaring, and a handful of noodles hitting hot steel")},

    {"id": "ct3", "seconds": 15, "megapixels": 1.2, "seed": 63, "neg": NEG,
     "engine": "photo", "note": "the turn",
     "image": "~/shared/LTX-FILM/ct_anchor.png",
     "keyframe": "a cook in a black shirt tossing noodles in a flaming wok at a night food "
                 "stall, a customer in a grey canvas jacket watching from a stool, hanging "
                 "bulbs, steam and fire",
     "prompt": beats(
         "A medium shot of %s heaving the wok up so a fireball rolls off it, then tipping "
         "the noodles into a white bowl and sliding it across the steel counter. %s"
         % (COOK, LOOK),
         [("A hard cut transitions to", "a close-up", COOK,
           "who finally looks up, half a smile, and says in a dry accent, \"You always "
           "come at closing.\""),
          ("Another hard cut transitions to", "a wide shot", "the two of them",
           "as %s picks up the bowl and %s pulls the shutter halfway down behind him, the "
           "lane dark beyond" % (CUST, COOK))],
         "a wok roaring and noodles hitting a bowl, the cook's voice speaking his line "
         "clearly, a bowl set on steel, then a metal shutter rolling down")},
]}
