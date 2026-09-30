#!/usr/bin/env python3
"""Three challenge films as shot scripts (2026-09-30), each written from a brief that names what AI
video is bad at - and each built with what the studio knew the day before plus what /sheets found.

  system-error   2D cyberpunk anime: transparent liquid, glass refraction, steam fogging glasses,
                 and LEGIBLE text ("SYSTEM ERROR") on a moving hologram
  smallest-gear  stop-motion puppets: micro-movements, four hands working together, knitted wool
  storm-sonata   photoreal: rain on lacquer, reflections, lightning, fingers racing on piano keys

What is new since the demo films (craft/SHEETS.md):
  - a second angle of each place is the SAME place turned by the multiple-angles LoRA
    (`<sks> ...` words), not a second text-to-image room; it is a cast entry with a wide ref_
  - characters seen from behind or side-on use the view from their own character sheet as the
    reference, instead of asking the compositor to invent the back of a coat
The brief's words stay in the shots; what the engines are known to get wrong is designed around,
not hidden: every challenge shot is still in the film, rendered on both engines and ranked.

Fields beyond the fight.py schema are those of _make_demo_films_0929.py (engine, face, line).
"""
import json
import os

ROOT = os.path.expanduser("~/shared/comfy-studio")
DST = os.path.join(ROOT, "studio", "shotscripts")

REAL = ("Unretouched photograph, available light, visible skin texture and pores, fine film grain, "
        "shallow depth of field, no retouching, no gloss.")
AVOID = ("lowres, blurry, deformed limbs, fused fingers, extra fingers, extra limbs, doubled figure, "
         "two of the same person, melting face, morphing, warping, text, letters, subtitles, captions, "
         "watermark, logo, nsfw")
NOBODY = "people, a person, a figure, a crowd, a face, hands"


def still(kind, framing, body, grade):
    return "A still frame from %s, %s %s %s" % (kind, framing, body, grade)


# ================================================================================= SYSTEM ERROR
ANIME = ("2D anime film still, clean confident line art, cel shading with two tones, painted background "
         "art, muted blues and deep purples with high-contrast neon cyan and magenta accents, flat colour, "
         "no photographic texture.")
G1 = ("2D anime, cyberpunk night, muted blue and deep purple palette, high-contrast neon cyan and magenta "
      "accents, soft bloom on the neon, rain haze, clean line art, cel shading.")
A1 = "a 2D anime film"
# the film is about a word on a sign: text is NOT banned here, only the things that are never wanted
AVOID1 = ("lowres, blurry, deformed hands, fused fingers, extra fingers, extra limbs, doubled figure, two of "
          "the same person, melting face, morphing, warping, photorealistic, photograph, 3d render, cgi, "
          "subtitles, captions, watermark, nsfw")
STYLE1 = "2D anime, cel shading, clean line art."
system_error = {
    "_comment": "Challenge film 1 of 3 (2026-09-30): transparent liquid, glass refraction, steam on glasses "
                "and legible text on a moving hologram, in 2D cyberpunk anime.",
    "film": "system-error", "title": "SYSTEM ERROR",
    "logline": "In a noodle bar under a broken billboard, a detective with machine eyes waits out the rain.",
    "grade": G1, "avoid": AVOID1, "realism": ANIME,
    "score_tags": ("dark synthwave, slow, muted analog synth pads, soft rain ambience, distant city hum, "
                   "lonely, melancholic, cyberpunk noir, instrumental, no vocals"),
    "score_tags_b": ("lo-fi cyberpunk, soft electric piano over warm synth pads, gentle, rain, lonely, "
                     "resolving, instrumental, no vocals"),
    "place": {"id": "noodlebar", "prompt": (
        "Wide anime background painting of the inside of a tiny noodle bar in a cyberpunk city at night, "
        "nobody in it: a narrow wooden counter with six stools, steaming pots and ladles behind it, paper "
        "lanterns glowing warm, a big rain-streaked window along one side looking onto a neon alley where a "
        "huge holographic billboard glows magenta and cyan, warm lamplight inside against blue night outside. "
        + ANIME)},
    "cast": {
        "detective": {"role": "the detective", "prompt": (
            "Full-length anime character reference of a young woman detective of about thirty against a "
            "plain mid-grey backdrop, even soft light, standing still, facing the camera, arms at her sides. "
            "A lean build, short black hair with an undercut, round wire-rimmed glasses over glowing cyan "
            "cybernetic eyes with thin circuit lines at the temples, a long dark navy trench coat with a "
            "high collar over a grey turtleneck, thin black gloves, black trousers, black boots. " + ANIME)},
        "cook": {"role": "the cook", "prompt": (
            "Full-length anime character reference of an old noodle cook of about seventy against a plain "
            "mid-grey backdrop, even soft light, standing still, facing the camera, arms at his sides. A "
            "small wiry man with a white towel tied around his head, a thin grey moustache, kind tired eyes, "
            "a dark blue work shirt with rolled sleeves under a stained white apron, weathered hands, wooden "
            "sandals. " + ANIME)},
        # a second place - a wide ref drawn directly, so --cast leaves it alone
        "alley": {"role": "the alley (a second place)", "place": True, "prompt": (
            "Wide anime background painting of a narrow rainy cyberpunk alley at night seen from street "
            "level, nobody in it: wet asphalt reflecting neon, tangled cables overhead, steam rising from a "
            "vent, the warm glowing window of a tiny noodle bar on the left, and high on the building "
            "opposite a huge holographic billboard floating in the rain that displays the words "
            "\"SYSTEM ERROR\" in sharp glowing red-magenta capital letters. " + ANIME)},
        # the detective from behind, from her own character sheet (studio/sheets.py)
        "detective_back": {"role": "the detective, seen from behind", "sheet_view": ["detective", "turn_back"],
                           "prompt": "The back view from the detective's character sheet."},
    },
    "shots": [
        {"id": "010", "title": "the billboard", "secs": 5, "refs": ["alley"], "engine": "ltx", "face": "none",
         "avoid_extra": NOBODY,
         "anchor": still(A1, "a WIDE SHOT", "of the rainy alley of reference one at night, looking up past the "
                         "glowing window of the noodle bar to the huge holographic billboard floating over the "
                         "street, its sharp glowing red-magenta letters reading \"SYSTEM ERROR\", rain falling "
                         "through its light, nobody in the street.", G1),
         "prompt": ("Rain pours down through the neon alley. High above, the holographic billboard flickers and "
                    "glitches for an instant, and the words on it stay sharp and steady, glowing red. Raindrops "
                    "streak through the hologram light, puddles ripple, steam drifts from a vent. The camera "
                    "pushes in very slowly toward the billboard. " + STYLE1 + " Heavy rain, a distant city hum, "
                    "the electric buzz of the billboard. No music.")},
        {"id": "020", "title": "rain on glass", "secs": 4, "refs": ["noodlebar"], "engine": "both",
         "face": "none", "avoid_extra": NOBODY,
         "anchor": still(A1, "an EXTREME CLOSE-UP", "of the big rain-streaked window of the noodle bar of "
                         "reference one, seen from inside: fat raindrops clinging to the glass and running down "
                         "it in crooked trails, each drop refracting a tiny upside-down copy of the neon alley "
                         "outside, the neon beyond melted into soft cyan and magenta bokeh.", G1),
         "prompt": ("Raindrops hit the window and run down the glass in crooked trails, merging as they fall; "
                    "each drop bends the neon light behind it like a lens. The camera holds still, the neon "
                    "soft beyond. " + STYLE1 + " Rain drumming on glass, the muffled city. No music.")},
        {"id": "030", "title": "the counter", "secs": 5, "refs": ["detective", "detective", "noodlebar"],
         "engine": "ltx", "face": "medium",
         "anchor": still(A1, "a MEDIUM SHOT", "of the woman of reference one sitting alone at the wooden "
                         "counter of the noodle bar of reference three, side-on to the camera, in her dark "
                         "trench coat, her glowing cyan eyes behind round glasses, steam drifting across the "
                         "counter, the rain-streaked window and the neon alley behind her.", G1),
         "prompt": ("She sits still at the counter, gloved hands folded; steam drifts across in front of her; "
                    "she lifts her head slightly toward the kitchen. The camera pushes in slowly. " + STYLE1 +
                    " Rain on the window, a pot simmering, the low murmur of the city. No music.")},
        {"id": "040", "title": "the bowl", "secs": 4, "refs": ["cook", "cook", "noodlebar"], "engine": "both",
         "face": "none",
         "anchor": still(A1, "a CLOSE SHOT", "over the counter of the noodle bar of reference three: the "
                         "weathered hands of the old man of reference one setting down a deep black ceramic bowl "
                         "of swirling iridescent broth full of glowing translucent noodles, thick steam billowing "
                         "up from it, his white apron behind.", G1),
         "prompt": ("The old cook's hands set the bowl down gently on the counter and draw back. The iridescent "
                    "broth swirls slowly, its surface shifting through rainbow colours; thick steam rises and "
                    "curls. Static camera. " + STYLE1 + " The soft knock of ceramic on wood, broth lapping, a "
                    "pot bubbling. No music.")},
        {"id": "050", "title": "chopsticks", "secs": 5, "refs": ["detective", "noodlebar"], "engine": "both",
         "face": "none",
         "anchor": still(A1, "an EXTREME CLOSE-UP", "of a steaming bowl on the counter of the noodle bar of "
                         "reference two: slender black lacquered chopsticks with fine silver inlay, held in the "
                         "black-gloved hand of the woman of reference one, lifting a bundle of glowing translucent "
                         "noodles out of swirling iridescent broth; droplets hanging from the noodles, light "
                         "refracting through them like glass, steam rising.", G1),
         "prompt": ("The chopsticks lift the glowing noodles slowly up out of the broth; the translucent strands "
                    "stretch and sway, broth drips from them in bright droplets back into the swirling bowl and "
                    "ripples spread across it. Steam rises. The camera holds close and still. " + STYLE1 +
                    " The drip of broth, a soft slurp, rain beyond. No music.")},
        {"id": "060", "title": "fog", "secs": 4, "refs": ["detective", "detective", "noodlebar"],
         "engine": "both", "face": "close",
         "anchor": still(A1, "a CLOSE-UP", "of the face of the woman of reference one at the counter of the "
                         "noodle bar of reference three, leaning over the steaming bowl, steam rising into her "
                         "face, her round glasses starting to mist at the bottom edge, her glowing cyan "
                         "cybernetic eyes shining through the lenses.", G1),
         "prompt": ("Steam rises from the bowl into her face and her round lenses mist over from the bottom up, "
                    "until only the glow of her cyan eyes shows through the fog. She blinks slowly. Static "
                    "camera, close. " + STYLE1 + " Steam hissing softly, rain on the window. No music.")},
        {"id": "070", "title": "the sign", "secs": 5, "refs": ["detective_back", "noodlebar", "alley"],
         "engine": "ltx", "face": "none",
         "anchor": still(A1, "an OVER-THE-SHOULDER SHOT", "from behind the woman of reference one sitting at the "
                         "counter of the noodle bar of reference two, looking out through the big rain-streaked "
                         "window at the alley of reference three, where the huge holographic billboard across "
                         "the street displays the words \"SYSTEM ERROR\" in sharp glowing red capital letters; "
                         "raindrops on the glass between us and the sign.", G1),
         "prompt": ("Outside the rain-streaked window the holographic billboard glitches: the words flicker, "
                    "break into scanlines and snap back sharp and legible, while rain streams down the glass in "
                    "front. She sits motionless, watching. Static camera. " + STYLE1 + " Rain on the glass, "
                    "the billboard's electric crackle muffled through the window. No music.")},
        {"id": "080", "title": "rain on the hologram", "secs": 4, "refs": ["alley"], "engine": "both",
         "face": "none", "avoid_extra": NOBODY,
         "anchor": still(A1, "a CLOSE SHOT", "of the huge holographic billboard of the alley of reference one, "
                         "its sharp glowing red letters reading \"SYSTEM ERROR\" filling the frame, heavy rain "
                         "falling through and in front of the letters, raindrops splashing on the glass "
                         "projector panel below them in tiny bursts of red light.", G1),
         "prompt": ("Heavy raindrops fall through the hologram and burst in tiny splashes of red light on the "
                    "glass panel below; the letters stay sharp and steady, glitching once and snapping back. "
                    "The camera drifts very slowly sideways. " + STYLE1 + " Pounding rain, an electric hum. "
                    "No music.")},
        {"id": "090", "title": "again", "secs": 5, "refs": ["detective", "detective", "noodlebar"],
         "engine": "ltx", "face": "close", "line": "System error... again.",
         "anchor": still(A1, "a CLOSE-UP", "of the woman of reference one at the counter of the noodle bar of "
                         "reference three, her round glasses clear, red light from the billboard outside glinting "
                         "in the lenses, her glowing cyan eyes tired, chopsticks resting across the bowl in front "
                         "of her.", G1),
         "prompt": ("Red light from outside flickers across her face. She looks toward the window and says "
                    "quietly, with a tired half-smile: \"System error... again.\" Static camera, close. " +
                    STYLE1 + " Rain, her voice low and dry. No music.")},
        # the wide place first: with no plate among the refs, the start frame takes image 1's shape
        {"id": "100", "title": "last light", "secs": 5, "refs": ["alley", "detective"], "engine": "ltx",
         "face": "wide",
         "anchor": still(A1, "a WIDE SHOT", "of the rainy alley of reference one at night: the warm glowing window "
                         "of the noodle bar in the middle of the frame with the small figure of the woman of "
                         "reference two sitting alone at the counter inside, rain pouring, neon reflections on "
                         "the wet asphalt, the red glow of the billboard falling across the street.", G1),
         "prompt": ("Rain pours down the alley. Inside the warm window she sits alone at the counter, small and "
                    "still. The red glow of the billboard flickers across the wet street. The camera pulls back "
                    "slowly into the rain. " + STYLE1 + " Heavy rain, a distant siren, the city hum. "
                    "No music.")},
    ],
}

# ================================================================================ SMALLEST GEAR
PUPPET = ("Handcrafted stop-motion animation, a real miniature puppet set photographed on a studio stage, "
          "puppets with smooth porcelain-like sculpted faces and glass eyes, hand-knitted wool clothing at "
          "puppet scale, visible hand-made textures, tilt-shift shallow depth of field, warm practical light.")
G2 = ("Stop-motion film, warm late-afternoon sunlight through a window, a golden shaft of light full of "
      "floating dust, cosy tungsten practicals, rich browns and brass, soft shadows, shallow depth of field.")
A2 = "a stop-motion animated film"
AVOID2 = AVOID + ", live-action actors, realistic human skin, smooth CGI plastic render"
STYLE2 = "Stop-motion animation, handcrafted puppets, miniature set."
smallest_gear = {
    "_comment": "Challenge film 2 of 3 (2026-09-30): micro-movements, two characters' hands working together "
                "and knitted wool, as a stop-motion puppet film.",
    "film": "smallest-gear", "title": "THE SMALLEST GEAR",
    "logline": "An old clockmaker lends his apprentice his steadiness for the smallest part of a watch.",
    "grade": G2, "avoid": AVOID2, "realism": PUPPET,
    "score_tags": ("gentle whimsical chamber music, pizzicato strings, soft celesta, a music box melody, the "
                   "ticking of clocks, warm, tender, playful, slow, instrumental, no vocals"),
    "score_tags_b": ("warm resolution, soft strings swell under celesta and a music box, tender, hopeful, "
                     "instrumental, no vocals"),
    "place": {"id": "workshop", "prompt": (
        "Wide photograph of a miniature stop-motion set: the inside of a cluttered, whimsical clockmaker's "
        "workshop, nobody in it: dozens of antique clocks of every size covering the walls, pendulums and "
        "cuckoo clocks, a long wooden workbench under a window crowded with tiny brass gears, springs, "
        "jeweller's tools and a loupe, a green-shaded lamp, stacks of old books, a dramatic shaft of golden "
        "late-afternoon sunlight falling through the window across the bench, dust motes floating in it. "
        + PUPPET)},
    "cast": {
        "artisan": {"role": "the clockmaker", "prompt": (
            "Full-length reference photograph of a stop-motion puppet of an elderly clockmaker of about eighty "
            "against a plain mid-grey backdrop, even soft light, standing still, facing the camera, arms at his "
            "sides. A small stooped man with a deeply wrinkled porcelain-like sculpted face, a bulbous nose, "
            "wispy white hair and bushy white eyebrows, small round brass spectacles, a thick oatmeal "
            "cable-knit wool sweater with hyper-detailed knit texture, a worn brown leather apron, brown "
            "corduroy trousers, felt slippers, long careful fingers. " + PUPPET)},
        "apprentice": {"role": "the apprentice", "prompt": (
            "Full-length reference photograph of a stop-motion puppet of a young apprentice girl of about "
            "twelve against a plain mid-grey backdrop, even soft light, standing still, facing the camera, arms "
            "at her sides. A small girl with a smooth porcelain-like sculpted face, freckles, big earnest eyes, "
            "auburn hair in a messy bun held with a pencil, a chunky moss-green hand-knitted wool sweater with "
            "sleeves too long, a small canvas apron, brown trousers, lace-up boots. " + PUPPET)},
        # the same workshop from higher and to the side: the plate turned by the angles LoRA
        "workshop_high": {"role": "the workshop, raised angle", "place": True,
                          "place_view": ["workshop", "angle_high_l"],
                          "prompt": "The workshop plate turned to a raised three-quarter view (studio/sheets.py)."},
    },
    "shots": [
        {"id": "010", "title": "the workshop", "secs": 5, "refs": ["workshop"], "anchor": None, "engine": "ltx",
         "face": "none", "avoid_extra": NOBODY,
         "prompt": ("The workshop is still but for time: pendulums swing, the hands of a dozen clocks tick "
                    "forward, dust motes drift slowly through the shaft of golden sunlight. Nobody is here. The "
                    "camera glides slowly along the workbench. " + STYLE2 + " A chorus of ticking clocks, the "
                    "soft creak of wood. No music.")},
        {"id": "020", "title": "the lesson", "secs": 5, "refs": ["artisan", "apprentice", "workshop"],
         "engine": "ltx", "face": "medium",
         "anchor": still(A2, "a MEDIUM TWO-SHOT", "at the workbench of the workshop of reference three: the old "
                         "man of reference one and the girl of reference two sitting side by side, bent over an "
                         "open pocket watch on a cloth, the girl holding a pair of fine tweezers, the old man "
                         "leaning in beside her, a shaft of golden sunlight across the bench.", G2),
         "prompt": ("The two of them lean over the open pocket watch; the old man points one finger into the "
                    "watch and the girl nods, gripping her tweezers. The camera pushes in slowly. " + STYLE2 +
                    " Ticking clocks, the girl's soft breath, a chair creaking. No music.")},
        {"id": "030", "title": "the watch", "secs": 4, "refs": ["workshop"], "engine": "both", "face": "none",
         "avoid_extra": NOBODY,
         "anchor": still(A2, "an EXTREME CLOSE-UP", "of an open antique pocket watch lying on a cloth on the "
                         "workbench of the workshop of reference one: its intricate brass movement of tiny gears "
                         "and red jewels, one empty spindle where a gear is missing, golden sunlight raking across "
                         "it, dust motes glittering in the light above the gears.", G2),
         "prompt": ("Dust motes drift down through the shaft of sunlight and settle softly on the tiny still "
                    "gears of the open watch; one glints as it lands. The camera holds still, very close. " +
                    STYLE2 + " A deep soft ticking from the clocks around. No music.")},
        {"id": "040", "title": "nerves", "secs": 4, "refs": ["apprentice", "apprentice", "workshop"],
         "engine": "ltx", "face": "close",
         "anchor": still(A2, "a CLOSE-UP", "of the face of the girl of reference one at the workbench of the "
                         "workshop of reference three, bent close over the watch, biting her lower lip in "
                         "concentration, her eyes wide, a strand of auburn hair falling across her freckled "
                         "cheek, golden sunlight on one side of her face.", G2),
         "prompt": ("She holds her breath and her eyes narrow in concentration; the loose strand of hair "
                    "trembles in front of her face; she swallows. Static camera, close. " + STYLE2 + " The "
                    "ticking of many clocks, her held breath. No music.")},
        {"id": "050", "title": "four hands", "secs": 5, "refs": ["artisan", "apprentice", "workshop"],
         "engine": "both", "face": "none",
         "anchor": still(A2, "an EXTREME CLOSE-UP", "over the open pocket watch on the workbench of the workshop "
                         "of reference three: the small hand of the girl of reference two holding fine steel "
                         "precision tweezers that grip a microscopic golden gear, and the old wrinkled hand of "
                         "the man of reference one resting over hers, his steady fingers gently guiding her hand "
                         "toward the empty spindle; the thick knitted cuffs of their wool sweaters, oatmeal and "
                         "moss green, in the frame; golden sunlight and floating dust.", G2),
         "prompt": ("Her hand trembles slightly; his steady fingers close gently around hers and guide the "
                    "tweezers down, slowly, until the tiny golden gear hovers over the empty spindle. The "
                    "knitted cuffs of their sweaters shift and crease as they move. Macro lens, static camera, "
                    "shallow focus. " + STYLE2 + " Soft ticking, the faint scrape of steel. No music.")},
        {"id": "060", "title": "steady", "secs": 5, "refs": ["artisan", "artisan", "workshop"], "engine": "ltx",
         "face": "close", "line": "Steady now... let it find its own place.",
         "anchor": still(A2, "a CLOSE-UP", "of the face of the old man of reference one at the workbench of the "
                         "workshop of reference three, his round brass spectacles on his nose, looking down at the "
                         "watch with a gentle, patient smile, deep wrinkles creasing around his eyes, golden "
                         "sunlight on his face.", G2),
         "prompt": ("He watches her work with a patient smile and says softly and warmly: \"Steady now... let "
                    "it find its own place.\" Static camera, close. " + STYLE2 + " His voice low and kind, the "
                    "clocks ticking. No music.")},
        {"id": "070", "title": "it catches", "secs": 4, "refs": ["workshop"], "engine": "both", "face": "none",
         "avoid_extra": NOBODY,
         "anchor": still(A2, "an EXTREME CLOSE-UP", "of the open pocket watch movement on the workbench of the "
                         "workshop of reference one: a tiny golden gear sitting on its spindle among the other "
                         "brass gears, the balance wheel beside it, golden sunlight.", G2),
         "prompt": ("The tiny golden gear settles onto its spindle, the gears engage, and the balance wheel "
                    "springs to life, swinging back and forth; every gear begins to turn. Static macro camera. " +
                    STYLE2 + " One tiny click, then a quick bright ticking. No music.")},
        {"id": "080", "title": "breath", "secs": 4, "refs": ["apprentice", "apprentice", "workshop"],
         "engine": "ltx", "face": "close",
         "anchor": still(A2, "a MEDIUM CLOSE-UP", "of the girl of reference one at the workbench of the workshop "
                         "of reference three, sitting back with the tweezers still in her hand, her chunky "
                         "moss-green knitted sweater bunched at her shoulders, a huge relieved grin spreading "
                         "across her freckled face.", G2),
         "prompt": ("She lets out a long breath; her shoulders drop and the thick knitted wool of her sweater "
                    "settles and creases; a huge grin spreads across her face. Static camera. " + STYLE2 +
                    " A long relieved exhale, the watch ticking quickly. No music.")},
        {"id": "090", "title": "well done", "secs": 5, "refs": ["artisan", "apprentice", "workshop"],
         "engine": "ltx", "face": "medium",
         "anchor": still(A2, "a MEDIUM TWO-SHOT", "at the workbench of the workshop of reference three: the old "
                         "man of reference one resting one hand on the shoulder of the girl of reference two, "
                         "both smiling down at the ticking pocket watch she holds up in her palm, a shaft of "
                         "golden sunlight between them.", G2),
         "prompt": ("The old man gives her shoulder a gentle squeeze; she lifts the ticking watch to her ear and "
                    "laughs; he chuckles. The camera pushes in slowly. " + STYLE2 + " The watch ticking, a soft "
                    "chuckle, the clocks around them. No music.")},
        {"id": "100", "title": "on the hour", "secs": 5, "refs": ["workshop_high"], "engine": "ltx",
         "face": "none", "avoid_extra": NOBODY,
         "anchor": still(A2, "a HIGH WIDE SHOT", "of the whole workshop of reference one from above the "
                         "workbench, every clock on the walls, the shaft of golden sunlight across the bench.", G2),
         "prompt": ("Every clock in the workshop strikes the hour at once: pendulums swing, cuckoos pop out of "
                    "their doors, little bells ring; the dust in the sunbeam swirls. The camera pulls back "
                    "slowly. " + STYLE2 + " A joyful chorus of chimes, bells and cuckoos. No music.")},
    ],
}

# ================================================================================= STORM SONATA
G3 = ("Cinematic film, night thunderstorm, cold blue-grey rain light, warm sodium street lamps, white "
      "lightning flashes, glossy wet surfaces and reflections, deep blacks with detail, fine grain, anamorphic.")
A3 = "a live-action film"
storm_sonata = {
    "_comment": "Challenge film 3 of 3 (2026-09-30): rain, reflections, lightning and fingers racing on piano "
                "keys, photoreal.",
    "film": "storm-sonata", "title": "STORM SONATA",
    "logline": "A street pianist plays through a thunderstorm in an empty square, and does not stop.",
    "grade": G3, "avoid": AVOID, "realism": REAL,
    "score_tags": ("virtuosic romantic solo grand piano, fast stormy arpeggios, thundering left hand octaves, "
                   "passionate, dramatic, intense, fast tempo, instrumental, no vocals, no other instruments"),
    "score_tags_b": ("solo grand piano, final crashing chords, then a quiet tender resolution, slow, "
                     "instrumental, no vocals, no other instruments"),
    "place": {"id": "plaza", "prompt": (
        "Wide photograph of a deserted old European plaza at night in a violent thunderstorm, nobody in it: "
        "rain-soaked cobblestones flooded with puddles, a glossy black concert grand piano standing alone in "
        "the middle of the square with its lid raised, a baroque church facade and old stone buildings with "
        "tall shuttered windows around it, iron street lamps glowing warm, sheets of rain, a fork of "
        "lightning over the rooftops lighting the stone white. Deep perspective, anamorphic. " + REAL)},
    "cast": {
        "pianist": {"role": "the pianist", "prompt": (
            "Full-length reference photograph of a man of about thirty against a plain mid-grey backdrop, even "
            "soft light, standing still, facing the camera, arms at his sides. A lean, intense street musician "
            "with shoulder-length wavy dark hair, a short dark beard, long slender fingers, a white linen shirt "
            "with the sleeves rolled to the elbows and open at the collar, dark braces, dark grey trousers, "
            "worn brown leather boots. " + REAL)},
        "plaza_high": {"role": "the square from above", "place": True, "place_view": ["plaza", "angle_aerial"],
                       "prompt": "The plaza plate turned to an aerial view (studio/sheets.py)."},
        "pianist_face": {"role": "the pianist's face, three-quarter", "sheet_view": ["pianist", "face_front_r"],
                         "prompt": "The three-quarter face view from the pianist's character sheet."},
    },
    "shots": [
        {"id": "010", "title": "the square", "secs": 5, "refs": ["plaza"], "anchor": None, "engine": "ltx",
         "face": "none", "avoid_extra": NOBODY,
         "prompt": ("Rain hammers down on the deserted square; a flash of lightning lights the church facade "
                    "white for an instant and is gone; the puddles on the cobblestones leap with the rain around "
                    "the lone piano. The camera pushes in slowly toward the piano. Violent rain, a crack of "
                    "thunder rolling round the square. No music.")},
        {"id": "020", "title": "he plays", "secs": 5, "refs": ["pianist", "pianist", "plaza"], "engine": "ltx",
         "face": "wide",
         "anchor": still(A3, "a WIDE SHOT", "of the square of reference three in the storm: the man of reference "
                         "one seated at the glossy black grand piano in the middle of the square, playing with "
                         "fierce energy, his white shirt soaked through and clinging to him, rain bouncing off the "
                         "piano, lightning over the rooftops.", G3),
         "prompt": ("He plays furiously in the pouring rain, his whole body driving into the keys, head bowed, "
                    "soaked hair swinging; lightning flickers across the sky. The camera pushes in slowly. The "
                    "roar of rain, thunder, the thud of the keys. No music.")},
        {"id": "025", "title": "from above", "secs": 4, "refs": ["plaza_high", "pianist"], "engine": "ltx",
         "face": "none",
         "anchor": still(A3, "a HIGH WIDE SHOT", "looking down on the square of reference one from above the "
                         "rooftops: the tiny figure of the man of reference two at the grand piano in the middle "
                         "of the flooded square, rain streaking down through the lamplight.", G3),
         "prompt": ("From high above, the tiny figure plays on at the piano in the middle of the flooded square as "
                    "sheets of rain sweep across it; lightning flashes and the whole square turns white for an "
                    "instant. The camera descends slowly. Rain, thunder rolling. No music.")},
        {"id": "030", "title": "rain on lacquer", "secs": 4, "refs": ["plaza"], "engine": "both", "face": "none",
         "avoid_extra": NOBODY,
         "anchor": still(A3, "an EXTREME CLOSE-UP", "of the glossy black lacquered lid of the grand piano in the "
                         "square of reference one, heavy rain splashing violently off the wet surface, the "
                         "mirror-like lacquer reflecting the lit windows of the old buildings and a jagged fork of "
                         "lightning.", G3),
         "prompt": ("Heavy raindrops smash onto the glossy black lid and burst into splashes and spray; in the "
                    "mirror-black lacquer the reflection of the old buildings trembles, and a flash of lightning "
                    "blazes across it. The camera slides slowly along the lid. Rain drumming on wood, a crack of "
                    "thunder. No music.")},
        {"id": "040", "title": "the run", "secs": 4, "refs": ["pianist", "plaza"], "engine": "both",
         "face": "none",
         "anchor": still(A3, "an EXTREME CLOSE-UP", "of the keyboard of the glossy black grand piano in the rainy "
                         "square of reference two: the long slender hands of the man of reference one racing "
                         "across the wet black and white keys in a fast run, water standing in beads on the "
                         "ivory, rain falling onto the keys and onto his soaked white shirt cuffs.", G3),
         "prompt": ("His fingers race across the keys in a fast, precise run up the keyboard; with every strike, "
                    "water droplets fly off the keys in bright sprays; rain keeps falling on his hands. The camera "
                    "tracks fast alongside the hands. The rapid thud of keys, rain, spray. No music.")},
        {"id": "050", "title": "soaked", "secs": 5, "refs": ["pianist_face", "pianist", "plaza"],
         "engine": "both", "face": "close",
         "anchor": still(A3, "a CLOSE-UP", "of the face of the man of reference one playing the grand piano in the "
                         "storm in the square of reference three, eyes closed in passion, his soaked dark hair "
                         "plastered to his forehead and cheeks, rain and sweat streaming down his face, a flash "
                         "of lightning lighting one side of his face.", G3),
         "prompt": ("He sways with the music, eyes shut, jaw tight; drops of rain and sweat fly off his hair and "
                    "chin as he moves; lightning flashes across his face. Static camera, close. Rain, thunder, "
                    "his hard breathing. No music.")},
        {"id": "060", "title": "the reflection", "secs": 4, "refs": ["pianist", "plaza"], "engine": "both",
         "face": "none",
         "anchor": still(A3, "a LOW ANGLE SHOT", "of a wide flooded puddle on the cobblestones of the square of "
                         "reference two, reflecting upside down the grand piano and the man of reference one "
                         "playing it, rain rings spreading across the reflection, the lit church facade behind.",
                         G3),
         "prompt": ("Raindrops ring across the puddle and shatter the upside-down reflection of the pianist and "
                    "the piano; a flash of lightning turns the reflection white for an instant. The camera stays "
                    "low and still. Rain splashing in the puddle, thunder. No music.")},
        {"id": "070", "title": "fortissimo", "secs": 4, "refs": ["pianist", "pianist", "plaza"], "engine": "both",
         "face": "medium",
         "anchor": still(A3, "a MEDIUM SHOT", "of the man of reference one at the glossy black grand piano in the "
                         "square of reference three, both hands raised high above the keyboard about to crash "
                         "down, his soaked shirt clinging, rain sheeting down, a bolt of lightning splitting the "
                         "sky behind the church.", G3),
         "prompt": ("His hands crash down onto the keys in one huge chord and spray flies off the keyboard; at "
                    "the same instant lightning strikes behind the church and floods the square with white "
                    "light. Static camera. The crash of the keys, a deafening crack of thunder, pouring rain. "
                    "No music.")},
        {"id": "080", "title": "after", "secs": 5, "refs": ["pianist", "plaza"], "engine": "ltx", "face": "none",
         "anchor": still(A3, "a CLOSE SHOT", "of the hands of the man of reference one lifting slowly from the "
                         "wet keys of the grand piano in the square of reference two, water dripping from his "
                         "fingertips onto the ivory, his soaked shirt cuffs.", G3),
         "prompt": ("He lifts his hands slowly from the keys and holds them there; water drips from his "
                    "fingertips onto the ivory; the rain begins to ease. Static camera, close. Dripping water, "
                    "the rain softening. No music.")},
        {"id": "090", "title": "the rain eases", "secs": 5, "refs": ["pianist", "pianist", "plaza"],
         "engine": "ltx", "face": "wide",
         "anchor": still(A3, "a WIDE SHOT", "of the square of reference three as the storm breaks: the man of "
                         "reference one standing beside the grand piano, head tipped back, face turned up to the "
                         "thinning rain, the wet cobblestones gleaming gold under the street lamps, a last "
                         "flicker of lightning far away over the rooftops.", G3),
         "prompt": ("He stands by the piano with his face turned up into the thinning rain and breathes; far away "
                    "a last faint flicker of lightning; the puddles settle. The camera pulls back slowly. Soft "
                    "rain, distant thunder rolling away, water dripping from the rooftops. No music.")},
    ],
}

if __name__ == "__main__":
    for film in (system_error, smallest_gear, storm_sonata):
        p = os.path.join(DST, film["film"] + ".json")
        if os.path.exists(p):
            print("keeping %s (it exists - delete it to rewrite)" % p)
            continue
        with open(p, "w", encoding="utf-8") as f:
            json.dump(film, f, indent=1, ensure_ascii=False)
        secs = sum(x["secs"] for x in film["shots"])
        print("%-14s %2d shots, %d s -> %s" % (film["film"], len(film["shots"]), secs, p))
