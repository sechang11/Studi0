#!/usr/bin/env python3
"""THE QUANTUM COURIER (2026-09-30) - the extra-credit stress test: ONE character in a detailed,
non-standard outfit, held across a crowded neon market, a brutalist chase with first-person shots,
and a gravity-reversed flight between skyscrapers. About three minutes.

The control variable is Maya, so she is built the way /sheets builds anyone: one full-length
reference, then her character sheet, and every shot that sees her from behind, from the side or
close on the face is handed THAT view as its reference (sheet_refs.py), not a description. Her
outfit is written once, in the reference prompt, and never again - rule 1, "show the character,
never describe them" - except where a shot is ABOUT a piece of it (the coat's colour shift, the
amber circuit on the left sleeve, the nose ring), and then only that piece is named.

One design decision the brief forces: the amber circuit pattern is on the TURTLENECK's left sleeve,
under a trench coat, and the brief wants it visible in the last frame. The coat is therefore
asymmetrical in a way that shows it - its left sleeve ends above the elbow.

Scenes are shot as sequences of 4-6 s shots (the measured envelope, craft/ACTION_SEQUENCE.md);
the brief's shot descriptions are kept, and each named camera move is its own shot or a pair
joined by a cut on motion.
"""
import json
import os

ROOT = os.path.expanduser("~/shared/comfy-studio")
DST = os.path.join(ROOT, "studio", "shotscripts")

REAL = ("Unretouched photograph, available light, visible skin texture and pores, fine film grain, "
        "shallow depth of field, no retouching, no gloss.")
AVOID = ("lowres, blurry, deformed limbs, fused fingers, extra fingers, extra limbs, doubled figure, "
         "two of the same person, melting face, morphing, warping, subtitles, captions, watermark, nsfw")
NOBODY = "people, a person, a figure, a crowd, a face, hands"

G_MARKET = ("Cinematic film, night, rain, high contrast, hot pink and electric blue neon against deep "
            "shadow, wet reflective surfaces, haze, deep blacks with detail, fine grain, anamorphic.")
G_CORRIDOR = ("Cinematic film, cold brutalist concrete, hard white light from high slit windows, deep "
              "shadow, cyan and grey, high contrast, fine grain, anamorphic.")
G_SKY = ("Cinematic film, blinding midday sun over a futuristic canyon city, white-gold light, hard "
         "glints, deep blue sky, atmospheric haze, high contrast, fine grain, anamorphic.")
G_SUNSET = ("Cinematic film, a massive orange setting sun, violet and amber sky, long haze, silhouettes, "
            "high contrast, fine grain, anamorphic.")


def still(framing, body, grade):
    return "A still frame from a live-action film, %s %s %s" % (framing, body, grade)


def shot(sid, title, secs, refs, anchor, prompt, engine="ltx", face="none", **kw):
    d = {"id": sid, "title": title, "secs": secs, "refs": refs, "engine": engine, "face": face,
         "anchor": anchor, "prompt": prompt}
    d.update(kw)
    return d


MAYA = ("Full-length reference photograph of a woman of about twenty-eight against a plain mid-grey backdrop, "
        "even soft light, standing still, facing the camera, arms at her sides. An East Asian woman with a "
        "sharp jawline, short asymmetrical neon-blue hair cut longer on one side, a small silver hoop "
        "piercing in her left nostril. She wears a high-collared asymmetrical technical trench coat made of "
        "iridescent reflective holographic nylon that shifts from emerald green to deep violet, its left "
        "sleeve ending above the elbow; under it a matte black tactical turtleneck with a distinct glowing "
        "amber circuit pattern running down the left sleeve; dark grey cargo pants with several loose "
        "hanging straps; heavy-soled black combat boots; matte black tactical gloves. " + REAL)

courier = {
    "_comment": "Extra-credit film (2026-09-30): one character in a complex reflective outfit held across "
                "three environments, first-person shots, a reflection, and reversed gravity.",
    "film": "quantum-courier", "title": "THE QUANTUM COURIER",
    "logline": "A courier runs from something she never looks at, and when the roof runs out, she keeps going.",
    "grade": G_MARKET, "avoid": AVOID, "realism": REAL,
    "score_tags": ("dark driving cyberpunk score, pulsing analog synth bass, tense arpeggios, heavy slow "
                   "drums building to a chase, rain, cinematic, instrumental, no vocals"),
    "score_tags_b": ("soaring cinematic synth score, huge warm pads, euphoric rising strings, weightless, "
                     "wonder, slow build to a vast resolution at sunset, instrumental, no vocals"),
    "place": {"id": "market", "prompt": (
        "Wide photograph of a narrow cyberpunk street market at night in the rain, nobody in it: stalls "
        "under dripping tarpaulins, strings of lanterns, stacked neon signs in hot pink and electric blue, "
        "steam rising from food stalls, puddles on the stone reflecting the neon, tangled cables overhead, "
        "tall buildings closing in. Deep perspective, anamorphic. " + REAL)},
    "cast": {
        "maya": {"role": "the courier", "prompt": MAYA},
        "maya_back": {"role": "the courier from behind", "sheet_view": ["maya", "turn_back"],
                      "prompt": "The back view from the courier's character sheet."},
        "maya_side": {"role": "the courier side-on", "sheet_view": ["maya", "turn_right"],
                      "prompt": "The side view from the courier's character sheet."},
        "maya_face": {"role": "the courier's face", "sheet_view": ["maya", "face_front_r"],
                      "prompt": "The three-quarter face from the courier's character sheet."},
        "market_high": {"role": "the market from above", "place": True, "place_view": ["market", "angle_aerial"],
                        "prompt": "The market plate turned to an aerial view (studio/sheets.py)."},
        "corridor": {"role": "the corridor (a second place)", "place": True, "prompt": (
            "Wide photograph of a long narrow brutalist concrete corridor inside a vast building, nobody in "
            "it: raw board-marked concrete walls and ceiling, hard white light falling from high slit "
            "windows in stripes across the floor, a waist-high concrete barrier across the corridor halfway "
            "down, and at the far end a massive floor-to-ceiling glass window. Deep perspective, anamorphic. "
            + REAL)},
        "canyon": {"role": "the canyon city (a third place)", "place": True, "prompt": (
            "Wide photograph from the edge of a skyscraper rooftop over a blinding sunlit futuristic canyon "
            "city, nobody in it: sheer glass and white stone towers plunging down into haze on both sides, "
            "sky bridges, the rooftop's concrete edge in the foreground, the sun high and glaring off the "
            "glass. Deep perspective, anamorphic. " + REAL)},
        "sunset": {"role": "the city at sunset (a fourth place)", "place": True, "prompt": (
            "Wide static landscape photograph of a futuristic canyon city of towers at sunset, nobody in it: "
            "a massive orange setting sun low between two towers, a violet and amber sky, haze over the "
            "canyon, the towers dark against the light. Anamorphic. " + REAL)},
    },
    "shots": [
        # ---------------------------------------------------------- SCENE 1: the wardrobe check
        shot("101", "the market", 5, ["market"], still("a HIGH WIDE SHOT", "of the rainy neon street market of "
             "reference one crowded with people under umbrellas, steam rising from the stalls.", G_MARKET),
             "Rain falls through the neon over the crowded market; umbrellas drift, steam rises from the food "
             "stalls, a sign flickers. The camera cranes slowly down toward the crowd. Rain, the murmur of a "
             "crowd, sizzling food, distant traffic. No music."),
        shot("102", "the eye", 4, ["maya_face", "market"], still("an EXTREME MACRO CLOSE-UP", "of the left eye "
             "and nose of the woman of reference one in the rainy market of reference two: the small silver "
             "hoop in her left nostril, rain streaking down her cheek, pink and blue neon reflected in her "
             "eye.", G_MARKET),
             "A raindrop runs down her cheek past the silver nose ring; she blinks once and her eye shifts to "
             "look past the camera; neon light flickers across her skin. Macro lens, static. Rain very close, "
             "her breath. No music.", face="close"),
        shot("103", "the coat", 4, ["maya", "market"], still("an EXTREME CLOSE-UP", "of the shoulder and collar "
             "of the iridescent holographic trench coat of the woman of reference one in the rainy market of "
             "reference two: rain beading on the reflective nylon, its colour sliding from emerald green to "
             "deep violet, pink and blue neon mirrored in it.", G_MARKET),
             "She turns her shoulder slightly; the iridescent fabric ripples and crinkles, its colour sliding "
             "from emerald green to deep violet as the angle changes, rain running off it in beads, neon "
             "reflections sliding across it. The camera holds close. Rain on nylon, the crowd beyond. "
             "No music.", engine="both"),
        shot("104", "she walks", 5, ["maya", "maya", "market"], still("a LOW ANGLE TRACKING SHOT", "looking up "
             "at forty-five degrees at the woman of reference one walking straight toward the camera through "
             "the crowded rainy market of reference three, her trench coat open and flaring, neon signs "
             "above her.", G_MARKET),
             "She walks forward with purpose and the camera dollies backward in front of her at the same "
             "speed, low and tilted up; her holographic coat ripples and crinkles with every step and "
             "reflects the pink and blue neon; the crowd parts around her. Her boots on wet stone, rain, the "
             "crowd. No music.", face="medium"),
        shot("1xx", "the stall", 4, ["maya", "maya", "market"], still("a MEDIUM TRACKING SHOT", "of the woman of "
             "reference one walking past a steaming street-food stall in the rainy market of reference three, "
             "a floating hologram menu above it throwing cyan and magenta light across her reflective coat.",
             G_MARKET),
             "She walks past the stall without looking at it; the hologram's colours slide across her "
             "reflective coat as she moves and steam curls around her. The camera tracks with her. Sizzling "
             "food, rain, the crowd. No music.", face="medium"),
        shot("105", "boots", 4, ["maya", "market"], still("a LOW CLOSE SHOT", "at ground level in the rainy "
             "market of reference two: the heavy-soled black combat boots of the woman of reference one "
             "splashing through a neon-lit puddle, the loose straps of her grey cargo pants swinging.",
             G_MARKET),
             "Her boots stride through the puddle, throwing up splashes of pink and blue light; the loose "
             "straps swing with each step. The camera tracks backward at ground level. Heavy footsteps, "
             "splashing, rain. No music.", engine="both"),
        shot("106", "the crowd", 5, ["maya_back", "market"], still("an OVER-THE-SHOULDER SHOT", "from just "
             "behind the right shoulder of the woman of reference one, her neon-blue hair in the foreground, "
             "as she pushes into a dense crowd of people of every age and look in the rainy market of "
             "reference two, umbrellas and neon ahead.", G_MARKET),
             "She threads her way through the dense crowd, turning her shoulder to slip between people; the "
             "camera follows close over her right shoulder. The crowd's voices, rain on umbrellas, a vendor "
             "calling out. No music."),
        shot("107", "crane up", 5, ["market_high", "maya"], still("a HIGH ANGLE SHOT", "looking steeply down "
             "into the crowded rainy market of reference one from above: the woman of reference two in the "
             "centre of the frame among the umbrellas, her neon-blue hair and her green-violet coat bright "
             "against the crowd.", G_MARKET),
             "The camera cranes straight up and away from her, rising until it looks directly down on the "
             "market; she stays in the centre of the frame, moving through the crowd, her blue hair and "
             "shifting coat always visible among the umbrellas. Rain, the crowd receding below. No music."),
        shot("108", "top-down", 4, ["market_high", "maya"], still("a TOP-DOWN AERIAL SHOT", "straight down on the "
             "crowded rainy market of reference one: a sea of umbrellas and neon, and in the exact centre the "
             "woman of reference two, her neon-blue hair and iridescent coat catching the light.", G_MARKET),
             "From directly above, umbrellas drift around her like a slow current while she stops still in "
             "the centre; the neon flickers on the wet ground. Static camera. Rain, the crowd far below. "
             "No music."),
        shot("109", "something behind", 4, ["maya_face", "market"], still("a CLOSE-UP", "of the woman of "
             "reference one in the rainy market of reference two, glancing back over her shoulder, rain on "
             "her face, the silver nose ring catching the neon, her eyes sharp.", G_MARKET),
             "She glances back over her shoulder at something behind her; her eyes narrow; she turns back and "
             "her jaw sets. Static camera, close. Rain, the crowd, a low electronic hum rising. No music.",
             face="close"),
        shot("110", "she runs", 4, ["maya", "maya", "market"], still("a MEDIUM SHOT", "of the woman of "
             "reference one breaking into a run through the crowded rainy market of reference three, people "
             "turning, her coat flaring.", G_MARKET),
             "She breaks into a run, pushing through the crowd; people turn and step aside; her coat flares "
             "out behind her. The camera whips after her. Running footsteps, shouts, rain. No music.",
             face="medium"),
        # ---------------------------------------------------------- SCENE 2: the physics and POV switch
        shot("201", "the corridor", 4, ["corridor", "maya"], still("a WIDE SHOT", "down the long brutalist "
             "concrete corridor of reference one: the woman of reference two bursting in at the far end, "
             "running toward the camera, stripes of hard white light across the floor.", G_CORRIDOR),
             "She sprints toward the camera down the corridor, through the stripes of hard light, her coat "
             "streaming behind her. Static camera. Her footsteps echoing on concrete, her breath. No music."),
        shot("202", "side-on", 5, ["maya_side", "corridor"], still("a SIDE-PROFILE TRACKING SHOT", "of the woman "
             "of reference one sprinting flat out along the brutalist concrete corridor of reference two, "
             "seen side-on, her trench coat tails and the loose straps of her cargo pants whipping out "
             "behind her.", G_CORRIDOR),
             "She sprints at full speed and the camera tracks alongside her in profile, fast; the tails of "
             "her trench coat and the loose straps on her cargo pants whip and snap out behind her in the "
             "wind of her run; stripes of light flash over her. Pounding footsteps, whipping fabric, her "
             "breath. No music.", engine="both", face="medium"),
        shot("203", "coat tails", 4, ["maya", "corridor"], still("a LOW CLOSE TRACKING SHOT", "behind the "
             "running woman of reference one in the concrete corridor of reference two: the tails of her "
             "iridescent trench coat and the loose straps of her cargo pants whipping out behind her.",
             G_CORRIDOR),
             "The coat tails billow and snap and the loose straps whip wildly behind her legs as she runs; "
             "the camera tracks low and close behind. Flapping fabric, footsteps, wind. No music.",
             engine="both"),
        shot("204", "the threat", 4, ["corridor"], still("a WIDE SHOT", "back along the empty brutalist concrete "
             "corridor of reference one, red scanning light sweeping across the far wall from somewhere out "
             "of sight.", G_CORRIDOR),
             "Red scanning light sweeps across the concrete walls of the empty corridor behind her; a deep "
             "mechanical hum grows; nothing is seen. Static camera. A rising electronic whine, distant "
             "footsteps. No music.", avoid_extra=NOBODY),
        shot("2xx", "the wall", 4, ["maya", "maya", "corridor"], still("a MEDIUM CLOSE SHOT", "of the woman of "
             "reference one pressed flat with her back against the concrete wall at a corner of the brutalist "
             "corridor of reference three, breathing hard, red scanning light sweeping across the wall just "
             "beside her.", G_CORRIDOR),
             "She holds herself flat against the wall, chest heaving, as the red light sweeps past a hand's "
             "width from her face; she waits, then pushes off and runs. Static camera. Her breath, the "
             "electronic whine passing. No music.", face="medium"),
        shot("205", "into her head", 4, ["maya_back", "corridor"], still("a MEDIUM SHOT", "from directly behind "
             "the running woman of reference one in the concrete corridor of reference two, her neon-blue "
             "hair and the back of her collar filling the middle of the frame.", G_CORRIDOR),
             "The camera rushes forward directly into the back of her head until her neon-blue hair fills "
             "the whole frame. A rush of air, her breath, footsteps. No music."),
        shot("206", "point of view", 5, ["corridor", "maya"], still("a FIRST-PERSON POINT-OF-VIEW SHOT", "running "
             "down the brutalist concrete corridor of reference one toward a waist-high concrete barrier: two "
             "hands in matte black tactical gloves reaching forward at the bottom of the frame, the "
             "iridescent coat sleeve on the right arm, the glowing amber circuit sleeve on the left arm, as "
             "worn by the woman of reference two.", G_CORRIDOR),
             "First-person view: the camera bobs with her running stride as the barrier rushes closer; her "
             "gloved hands reach out in front. Heavy breathing, footsteps, the whine behind. No music."),
        shot("207", "the vault", 4, ["corridor", "maya"], still("a FIRST-PERSON POINT-OF-VIEW SHOT", "at the "
             "waist-high concrete barrier in the corridor of reference one: two hands in matte black tactical "
             "gloves planted on top of the barrier, the glowing amber circuit on the left sleeve of the woman "
             "of reference two, the corridor floor beyond.", G_CORRIDOR),
             "First-person view: her gloved hands slam down on the barrier and she vaults over it; the camera "
             "swings up and over, then jolts hard and tilts down as she lands on the far side. A grunt, the "
             "slap of gloves on concrete, the thud of landing. No music.", engine="both"),
        shot("208", "the vault, from the side", 4, ["maya_side", "corridor"], still("a WIDE SIDE SHOT", "of the "
             "woman of reference one in mid-vault over the waist-high concrete barrier in the corridor of "
             "reference two, both gloved hands on the barrier, legs swinging over, coat flying.", G_CORRIDOR),
             "She swings her legs over the barrier and lands running on the far side, the coat flying out "
             "and falling back. Static camera. Gloves on concrete, the landing, running on. No music.",
             engine="both", face="medium"),
        shot("209", "the reflection", 5, ["corridor", "maya"], still("a FIRST-PERSON POINT-OF-VIEW SHOT",
             "looking up at the massive floor-to-ceiling glass window at the end of the concrete corridor of "
             "reference one: in the dark glass, the clear reflection of the full body of the woman of "
             "reference two standing and looking up at it, her face intent, her iridescent coat mirroring the "
             "corridor's light.", G_CORRIDOR),
             "First-person view, looking up at the huge window; in the reflection she stands breathing hard, "
             "chest rising and falling, her face tense with focus, her coat catching the light in green and "
             "violet. The camera tilts up slowly. Breathing, a hum through the glass. No music.",
             face="wide"),
        shot("210", "her face in the glass", 4, ["maya_face", "corridor"], still("a CLOSE-UP", "of the "
             "reflection of the face of the woman of reference one in the dark glass window of the concrete "
             "corridor of reference two, intent, a strand of neon-blue hair across her forehead.", G_CORRIDOR),
             "Her reflection breathes hard, eyes fixed and steady, then she looks up toward something above. "
             "Static camera. Her breathing slowing. No music.", face="close"),
        shot("211", "the stairs", 4, ["maya_back", "corridor"], still("a MEDIUM SHOT", "from behind the woman of "
             "reference one running up a steep concrete stairwell off the brutalist corridor of reference two "
             "toward a bright door at the top.", G_CORRIDOR),
             "She takes the concrete stairs two at a time toward the bright door at the top; the camera "
             "follows. Footsteps ringing on concrete, her breath. No music."),
        shot("212", "the roof", 5, ["canyon", "maya"], still("a WIDE SHOT", "of the skyscraper rooftop of "
             "reference one in blinding sunlight: the woman of reference two bursting out of a door onto the "
             "roof, the futuristic canyon city beyond.", G_SKY),
             "She bursts through the door onto the roof and blinding sunlight floods over her; she shields "
             "her eyes for a moment and walks toward the edge. Wind, the door banging, the city far below. "
             "No music."),
        # ---------------------------------------------------------- SCENE 3: the flight
        shot("301", "the edge", 5, ["canyon", "maya_back"], still("a WIDE SHOT", "from behind the woman of "
             "reference two standing at the very edge of the skyscraper rooftop of reference one, the sunlit "
             "canyon city plunging away below her, her coat moving in the wind.", G_SKY),
             "She stands at the very edge with her back to us; the wind tugs at her coat and hair; far below, "
             "sky traffic glints between the towers. The camera pushes in slowly. Wind, a distant city. "
             "No music."),
        shot("302", "breath", 4, ["maya_face", "canyon"], still("a CLOSE-UP", "of the face of the woman of "
             "reference one at the edge of the sunlit rooftop of reference two, calm now, eyes closed, sunlight "
             "on her skin, her neon-blue hair moving in the wind.", G_SKY),
             "She breathes in slowly, eyes closed, and lets the breath go; she opens her eyes and looks down. "
             "Static camera, close. Wind, her breath. No music.", face="close"),
        shot("303", "step", 4, ["maya_side", "canyon"], still("a SIDE SHOT", "of the woman of reference one at "
             "the very edge of the rooftop of reference two, one boot stepping out over the drop, the sunlit "
             "canyon city below.", G_SKY),
             "She steps calmly off the edge into the air. The camera holds still as she drops out of the "
             "bottom of the frame. Wind, a sudden silence. No music.", face="medium"),
        shot("304", "gravity turns", 6, ["maya", "canyon"], still("a WIDE SHOT", "of the woman of reference one "
             "suspended in the bright air beside a sheer glass skyscraper in the sunlit canyon city of "
             "reference two, drifting upward, her iridescent coat billowing up toward the sky, dust and grit "
             "floating up around her.", G_SKY),
             "In extreme slow motion she floats upward instead of falling; her coat billows softly up toward "
             "the sky as if gravity has turned over; specks of dust drift upward around her, glittering in the "
             "sun. The camera rises with her, slowly. A deep soft whoosh, wind slowed right down. No music.",
             engine="both", face="medium"),
        shot("305", "the sleeve", 4, ["maya", "canyon"], still("a CLOSE SHOT", "of the left arm of the woman of "
             "reference one floating in the sunlit air of reference two: the glowing amber circuit pattern on "
             "her black sleeve, her matte black gloved hand open, dust motes floating upward past it.", G_SKY),
             "Her gloved hand drifts open; dust motes float upward past the glowing amber circuit on her "
             "sleeve, which pulses slowly. Slow motion, the camera drifting. Soft wind, a low hum. No music.",
             engine="both"),
        shot("306", "rising", 4, ["maya", "canyon"], still("a LOW ANGLE SHOT", "looking straight up at the "
             "woman of reference one rising against the blinding sun between two sheer towers of the canyon "
             "city of reference two, her coat billowing upward.", G_SKY),
             "She rises slowly up into the sun between the towers, her coat spreading upward like wings; the "
             "sun flares around her. Static camera. A deep swell of wind. No music."),
        shot("307", "she flies", 5, ["maya", "canyon"], still("a TRACKING SHOT", "beside the woman of reference "
             "one flying horizontally at great speed between the glass skyscrapers of the canyon city of "
             "reference two, body stretched out, coat streaming behind her.", G_SKY),
             "She tips forward and shoots between the skyscrapers at breakneck speed; the camera circles "
             "around her as she flies, tight and fast, the towers streaking past behind. Roaring wind, "
             "rushing air. No music.", engine="both", face="medium"),
        shot("3xx", "through the haze", 4, ["maya", "canyon"], still("a TRACKING SHOT", "of the woman of "
             "reference one flying fast out of a bank of white haze between the towers of the sunlit canyon "
             "city of reference two, vapour streaming off her coat and her neon-blue hair.", G_SKY),
             "She bursts out of the white haze at speed, trails of vapour peeling off her coat and hair and "
             "streaming behind her in the sun. The camera tracks alongside. A roar of wind, a whoomp of air. "
             "No music.", engine="both", face="medium"),
        shot("308", "the glint", 4, ["maya", "canyon"], still("a CLOSE TRACKING SHOT", "of the woman of "
             "reference one flying through the sunlit canyon city of reference two, the sun glinting hard off "
             "her iridescent holographic coat, green on one side and violet on the other.", G_SKY),
             "As the camera swings around her, the sunlight glints off her holographic coat and its colour "
             "shifts rapidly from emerald green to deep violet with the angle of the sun. Roaring wind. "
             "No music.", face="medium"),
        shot("3xx", "face in flight", 4, ["maya_face", "canyon"], still("an EXTREME CLOSE-UP", "of the face of "
             "the woman of reference one flying through the sunlit canyon city of reference two, wind tearing "
             "at her neon-blue hair, the silver nose ring glinting, her eyes bright and fierce.", G_SKY),
             "Wind tears at her hair and skin as she flies; she narrows her eyes against it and a fierce, "
             "wild smile breaks across her face. The camera flies with her, close. A howl of wind. No music.",
             face="close"),
        shot("309", "first person", 4, ["canyon"], still("a FIRST-PERSON FLYING SHOT", "at high speed between the "
             "glass and white stone skyscrapers of the canyon city of reference one, a sky bridge rushing "
             "toward the camera, sunlight flaring.", G_SKY),
             "First-person view flying at breakneck speed between the towers; the camera dives under a sky "
             "bridge and banks hard around a tower. Rushing wind, a sonic roar. No music.",
             avoid_extra=NOBODY),
        shot("310", "barrel roll", 4, ["maya", "canyon"], still("a MEDIUM SHOT", "of the woman of reference one "
             "rolling sideways through the air between the towers of the sunlit canyon city of reference two, "
             "coat whipping around her, motion blur.", G_SKY),
             "She does a tight barrel roll through the air and the camera spins with her; the city blurs into "
             "streaks of light around her; the spin slows and steadies. Roaring wind, a rush of sound. "
             "No music.", engine="both", face="medium"),
        shot("311", "the pull back", 4, ["sunset", "maya"], still("a MEDIUM WIDE SHOT", "of the woman of "
             "reference two hovering still in the air above the canyon city of reference one at sunset, the "
             "huge orange sun behind her.", G_SUNSET),
             "The spin stops; the camera pulls back sharply away from her as she hangs still in the air in "
             "front of the setting sun. Wind dropping away. No music.", face="medium"),
        shot("312", "sunset", 6, ["sunset", "maya"], still("a WIDE STATIC LANDSCAPE SHOT", "of the canyon city of "
             "reference one at sunset, the massive orange sun low between the towers, and small in the middle "
             "of the sky the woman of reference two hovering perfectly still, her silhouette sharp, her "
             "neon-blue hair and the amber glow of her left sleeve visible against the light.", G_SUNSET),
             "She hovers perfectly still against the enormous setting sun; her coat stirs gently in the wind; "
             "the amber glow on her left sleeve pulses once. The camera does not move. Wind, a vast quiet. "
             "No music."),
    ],
}

def number(shots):
    """Ids from position within each scene (the first digit): 101, 102 ... 201 ... - so a shot can be
    inserted anywhere above without renumbering by hand."""
    seen = {}
    for x in shots:
        scene = x["id"][0]
        seen[scene] = seen.get(scene, 0) + 1
        x["id"] = "%s%02d" % (scene, seen[scene])
    return shots


courier["shots"] = number(courier["shots"])

if __name__ == "__main__":
    p = os.path.join(DST, courier["film"] + ".json")
    if os.path.exists(p):
        raise SystemExit("keeping %s (it exists - delete it to rewrite)" % p)
    json.dump(courier, open(p, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print("%s: %d shots, %d s -> %s" % (courier["film"], len(courier["shots"]),
                                        sum(x["secs"] for x in courier["shots"]), p))
