#!/usr/bin/env python3
"""Three one-minute demo films as shot scripts (2026-09-29), each built to show one thing the
studio does well, and each flagging - in `seedance` - the shots the paid engine would take.

  dead-stock   action: a physical beat choreographed in Blender, H3 for dust and close sound
  house-rules  dialogue: five spoken lines, lip-synced, one room, two faces across cuts
  temper       texture: fire, sparks, steam - effects beats on H3, one multishot generation

Fields beyond the fight.py schema (the tool ignores what it does not use):
  engine     ltx (default) | h3 | both | previz
  face       close | medium | wide | none  - how identity is measured (none/wide: not scored)
  line       the words a take must say (checked by ear-model in take_rank.py)
  seedance   {why, prompt, secs} - the prompt we WOULD send to Seedance 2.5, and did not
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


def still(framing, body, grade):
    return "A still frame from a live-action film, %s %s %s" % (framing, body, grade)


# =================================================================================== DEAD STOCK
G1 = ("Cinematic film, night, sodium-orange practical lamps against cold blue-green shadow, wet "
      "reflective concrete, haze in the air, deep blacks with detail, fine grain, anamorphic.")
dead_stock = {
    "_comment": "Demo film 1 of 3 (2026-09-29). Action, built around a physical beat choreographed in "
                "Blender (studio/_tools/previz_shot.py) instead of hoped for from words.",
    "film": "dead-stock", "title": "DEAD STOCK",
    "logline": "A courier cornered in a warehouse at night brings the stock down between herself and "
               "the man sent to collect it.",
    "grade": G1, "avoid": AVOID, "realism": REAL,
    "score_tags": ("dark cinematic tension score, low pulsing synth bass, sustained low strings, soft "
                   "ticking percussion, slow build, suspense, instrumental, no vocals"),
    "score_tags_b": ("cinematic aftermath, low strings swell and fall away, a few sparse piano notes, "
                     "distant thunder, quiet, instrumental, no vocals"),
    "place": {"id": "warehouse", "prompt": (
        "Wide photograph of the inside of a vast old warehouse at night, nobody in it: a long central "
        "aisle between towering stacks of old wooden shipping crates, sodium lamps hanging on chains "
        "casting pools of orange light, rain running down a row of skylights, puddles on the cracked "
        "concrete floor reflecting the lamps, a large loading door at the far end of the aisle half open "
        "onto the rain. Deep perspective, anamorphic. " + REAL)},
    "cast": {
        "nadia": {"role": "the courier", "prompt": (
            "Full-length reference photograph of a lean athletic woman of about thirty against a plain "
            "mid-grey backdrop, even soft light, standing still, facing the camera, arms at her sides. "
            "Short choppy black hair, a small scar through her left eyebrow, a dark olive waterproof rain "
            "jacket zipped to the chin, black cargo trousers, worn black trail shoes, a battered brown "
            "canvas messenger bag worn across her chest on a wide strap. " + REAL)},
        "hale": {"role": "the collector", "prompt": (
            "Full-length reference photograph of a tall broad-shouldered man of about fifty-five against "
            "a plain mid-grey backdrop, even soft light, standing still, facing the camera, arms at his "
            "sides. Close-cropped grey hair and a short grey beard, a heavy charcoal wool overcoat worn "
            "open over a black roll-neck sweater, black leather gloves, dark trousers, polished black "
            "shoes. " + REAL)},
    },
    "shots": [
        {"id": "010", "title": "the warehouse", "secs": 5, "refs": ["warehouse"], "anchor": None,
         "engine": "ltx", "face": "none", "avoid_extra": NOBODY,
         "prompt": ("Nothing moves in the empty warehouse but the weather and the light: rain streams down "
                    "the skylights, one hanging sodium lamp sways slightly on its chain so its pool of "
                    "orange light drifts across the wet floor, drops fall from the roof into a puddle and "
                    "ripple the reflection. Nobody is here. The camera pushes in slowly and steadily down "
                    "the aisle. Heavy rain drumming on the roof, the electrical hum of the lamps, dripping "
                    "water. No music.")},
        {"id": "020", "title": "hiding", "secs": 4, "refs": ["nadia", "nadia", "warehouse"], "engine": "both",
         "face": "close",
         "anchor": still("a MEDIUM CLOSE-UP,",
                         "the woman of reference one pressed with her back flat against a tall stack of "
                         "wooden crates in the warehouse of reference three, her head turned to listen "
                         "toward the aisle on her left, the canvas bag held tight to her chest with both "
                         "hands, rain-wet hair on her forehead. A sodium lamp behind her rims her face in "
                         "orange; the rest is cold blue shadow.", G1),
         "prompt": ("She holds her breath and listens, her eyes moving toward the aisle, then lets the "
                    "breath out slowly through her mouth, very quietly. She does not move from the crates. "
                    "Handheld camera close, a faint float, almost still. Her shallow breathing, rain "
                    "drumming on the roof far above, a distant drip. No music.")},
        {"id": "030", "title": "the door", "secs": 5, "refs": ["hale", "hale", "warehouse"], "engine": "ltx",
         "face": "wide",
         "anchor": still("a WIDE SHOT", "straight down the long central aisle of the warehouse of reference "
                         "three toward the big loading door at the far end, open onto the rain; in the "
                         "doorway stands the man of reference one, small and dark against the grey rain "
                         "outside, one gloved hand on the door frame.", G1),
         "prompt": ("The man in the doorway lets go of the door frame and takes one slow step into the "
                    "warehouse, out of the rain, and stops, looking down the aisle. Rain blows in around "
                    "him. Static camera. The heavy loading door creaking on its rails, rain roaring "
                    "outside, one footstep on wet concrete. No music."),
         "seedance": {"secs": 5, "why": "A walk. Measured: our engines hold the picture and the person "
                                         "but not the walk itself - he takes one step and stops because "
                                         "we wrote it that way. Seedance would walk him the whole aisle.",
                      "prompt": ("[image 1] is the first frame. The man of [image 2] walks in out of the "
                                 "rain through the loading door of the warehouse of [image 3] and comes "
                                 "slowly down the long aisle toward the camera, unhurried, gloved hands "
                                 "loose at his sides, lamplight passing over him lamp by lamp until he "
                                 "stops ten metres from us. Static camera, anamorphic, night, sodium "
                                 "orange and blue shadow. Sound: rain roaring outside, the door on its "
                                 "rails, his footsteps on wet concrete getting closer. No music.")}},
        {"id": "040", "title": "the offer", "secs": 6, "refs": ["hale", "hale", "warehouse"], "engine": "ltx",
         "face": "close", "line": "It's only a bag, Nadia. Put it down and walk out of here.",
         "anchor": still("a MEDIUM CLOSE-UP", "of the man of reference one standing in the aisle of the "
                         "warehouse of reference three under a hanging sodium lamp, rain water on the "
                         "shoulders of his coat, his face calm and patient, looking a little to the left "
                         "of camera.", G1),
         "prompt": ("He speaks calmly and quietly, in a low, rough, unhurried voice: \"It's only a bag, "
                    "Nadia. Put it down and walk out of here.\" Then he waits, very still. Static camera, "
                    "a faint handheld float. His voice echoing in the big space, rain on the roof, the hum "
                    "of the lamp. No music.")},
        {"id": "050", "title": "the stack", "secs": 5, "refs": ["nadia", "nadia", "warehouse"], "engine": "both",
         "face": "close",
         "anchor": still("a CLOSE-UP", "of the woman of reference one leaning back against the wooden "
                         "crates in the warehouse of reference three, eyes closed, rain on her face, lit "
                         "from above by an orange lamp.", G1),
         "prompt": ("Her eyes open and she slowly tilts her head back to look straight up at the top of "
                    "the tall stack of crates she is leaning on; her jaw sets. Handheld camera close, "
                    "almost still. Her breath, rain far above, a loose strap tapping against wood. "
                    "No music.")},
        {"id": "060", "title": "the strap", "secs": 4, "refs": ["nadia", "nadia", "warehouse"], "engine": "ltx",
         "face": "medium",
         "anchor": still("a MEDIUM SHOT", "of the woman of reference one at the foot of a towering stack of "
                         "wooden crates in the warehouse of reference three, both hands gripping a frayed "
                         "orange cargo strap that hangs down the side of the stack, her body leaning "
                         "back, ready to pull.", G1),
         "prompt": ("She throws her whole weight back on the strap; it snaps taut and the tower of crates "
                    "above her groans and begins to tilt. Handheld camera, a faint float. The strap "
                    "creaking, wood groaning and cracking, rain far above. No music.")},
        {"id": "070", "title": "the fall", "secs": 5, "refs": ["hale", "hale", "warehouse"], "engine": "previz",
         "face": "none", "previz": {"scene": "aisle", "seconds": 5},
         "anchor": None,
         "prompt": ("Inside a vast dark warehouse at night under hanging sodium lamps, a towering stack of "
                    "old wooden shipping crates topples across the aisle; the crates crash onto the wet "
                    "concrete, burst apart and tumble, piling up into a wall of broken wood that blocks the "
                    "aisle, splinters and dust thrown up into the orange lamplight. Far down the aisle a "
                    "man in a long dark coat stands still. The camera drifts slowly. Sound: a deep groan "
                    "of wood, then a thunderous crash and clatter of crates, splintering boards, debris "
                    "settling, rain on the roof. No music."),
         "seedance": {"secs": 5, "why": "A physical event with dozens of bodies in contact. We choreographed "
                                         "it in Blender and drew it through depth control, so every crate "
                                         "lands where the simulation put it; Seedance would invent the "
                                         "physics from words - better texture at speed, no guarantee "
                                         "where anything lands.",
                      "prompt": ("[image 1] is the first frame: the warehouse of [image 3] with the man of "
                                 "[image 2] far down the aisle. A towering stack of old wooden crates "
                                 "beside the camera tips over and falls across the aisle; the crates crash "
                                 "onto the wet concrete, burst apart, tumble and pile up into a wall of "
                                 "broken wood that cuts the aisle in two, splinters and dust bursting into "
                                 "the orange lamplight, the man beyond it raising an arm. Camera low and "
                                 "static, slight shake at the impact. Sound: a long groan of wood, a "
                                 "thunderous crash, boards splintering, debris settling, rain. No music.")}},
        {"id": "080", "title": "the dust", "secs": 4, "refs": ["hale", "hale", "warehouse"], "engine": "h3",
         "face": "medium",
         "anchor": still("a MEDIUM SHOT", "of the man of reference one in the aisle of the warehouse of "
                         "reference three, one arm raised in front of his face as a cloud of dust and "
                         "splinters rolls toward him out of the dark, a sodium lamp swinging above him.", G1),
         "prompt": ("The dust cloud rolls over him and thins; he slowly lowers his arm and squints ahead "
                    "through the settling dust. Static camera. Debris settling and pattering, a last board "
                    "clattering down, his cough, rain. No music."),
         "seedance": {"secs": 4, "why": "An effect that must arrive at an instant and then clear (the "
                                         "breakdown's rule 3). Measured: LTX lets dust accumulate whatever "
                                         "the words say; H3 plateaus and clears, which is why this shot is "
                                         "on H3. Seedance keys the effect to the impact frame.",
                      "prompt": ("[image 1] is the first frame. A wave of dust and splinters from the fallen "
                                 "crates hits the man of [image 2] at the instant it arrives - he flinches "
                                 "behind his raised arm - and in a second the air clears; he lowers the arm "
                                 "and squints through the last of it. Medium shot, static camera, the "
                                 "sodium lamp swinging above him. Sound: the dust's rush, debris "
                                 "pattering, his cough, rain. No music.")}},
        {"id": "090", "title": "the wall", "secs": 5, "refs": ["warehouse", "warehouse", "warehouse"],
         "engine": "ltx", "face": "none", "avoid_extra": NOBODY,
         "anchor": still("a WIDE SHOT", "down the aisle of the warehouse of reference one, now completely "
                         "blocked by a chaotic wall of broken and tumbled wooden crates piled higher than a "
                         "man, splintered boards everywhere, dust hanging in the orange lamplight, nobody "
                         "visible.", G1),
         "prompt": ("Nothing moves but the settling dust drifting through the lamplight and one loose board "
                    "that slides down the pile and clatters onto the floor. Nobody is here. Static camera. "
                    "Dust hissing down, the board's clatter, rain on the roof, the lamps' hum. No music.")},
        {"id": "100", "title": "fine", "secs": 5, "refs": ["hale", "hale", "warehouse"], "engine": "ltx",
         "face": "close", "line": "Fine. Run, then.",
         "anchor": still("a CLOSE-UP", "of the man of reference one in the warehouse of reference three, "
                         "dust settling on his coat and in his beard, staring ahead at something just past "
                         "the camera, an orange lamp behind him.", G1),
         "prompt": ("He stares ahead, unreadable, and says quietly, in a low, rough voice: \"Fine. Run, then.\" "
                    "His face barely moves; only his eyes narrow a little. Static camera, a faint float. His "
                    "voice, dust pattering, rain. No music."),
         "note": "re-directed 2026-09-29: the first words (a faintest smile) gave a full grin on three seeds"},
        {"id": "110", "title": "the other side", "secs": 6, "refs": ["nadia", "nadia", "warehouse"],
         "engine": "both", "face": "close",
         "anchor": still("a MEDIUM CLOSE-UP", "of the woman of reference one squeezed into a narrow dark gap "
                         "between stacks of wooden crates in the warehouse of reference three, the canvas "
                         "bag clutched to her chest, dust in the air, a thin blade of orange lamplight "
                         "falling across her eyes.", G1),
         "prompt": ("She listens, completely still, then lets out a long breath, and the ghost of a smile "
                    "crosses her face. Handheld camera close, almost still. Her breath, dust settling, rain "
                    "far above. No music.")},
        {"id": "120", "title": "lights out", "secs": 5, "refs": ["warehouse"], "anchor": None, "engine": "ltx",
         "face": "none", "avoid_extra": NOBODY,
         "prompt": ("Nothing moves in the empty warehouse but the lamps: the nearest hanging sodium lamp sways "
                    "slowly on its chain, flickers twice and goes out, leaving only the cold blue light from "
                    "the skylights and the rain. Nobody is here. Static camera. Rain on the roof, the lamp's "
                    "buzzing hum and the click as it dies. No music.")},
    ],
    "not_shot": [
        {"title": "the sprint", "why": "The obvious action beat - she runs the length of the aisle as the "
                                       "stack comes down behind her - is the one this box measurably cannot "
                                       "do (motion fidelity at speed). The script was written around it: "
                                       "she brings the stack down and is simply on the other side of it.",
         "seedance": ("[image 1] is the woman of [image 2] at the foot of the crates in the warehouse of "
                      "[image 3]. She sprints flat out down the aisle toward the camera as the tower of "
                      "crates behind her tips and crashes down, splinters and dust chasing her, lamplight "
                      "strobing over her as she passes under each lamp; she dives through the last gap as "
                      "the crates close it. Camera tracking backward low and fast. Sound: her feet slapping "
                      "wet concrete, her breath, the roar of falling crates. No music."), "secs": 6},
    ],
}

# ================================================================================== HOUSE RULES
G2 = ("Cinematic film, three in the morning, warm tungsten light inside against the cold blue rain "
      "outside, red and green neon reflections on wet glass and chrome, soft haze, deep blacks with "
      "detail, fine grain, anamorphic.")
IRIS_V = "in a warm, low, slightly husky older woman's voice"
THEO_V = "in a soft, hoarse young man's voice"
house_rules = {
    "_comment": "Demo film 2 of 3 (2026-09-29). Dialogue: five spoken lines lip-synced on LTX-2.5, one "
                "room, two faces held across cuts by composed start frames.",
    "film": "house-rules", "title": "HOUSE RULES",
    "logline": "At three in the morning a soaked stranger walks into a roadside diner, and the waitress "
               "remembers him before he says who he is.",
    "grade": G2, "avoid": AVOID, "realism": REAL,
    "score_tags": ("sparse late-night solo piano, soft upright bass, very quiet brushed drums, warm, "
                   "melancholic, tender, slow, instrumental, no vocals"),
    "score_tags_b": ("solo piano, gentle warm resolution, soft strings enter under it, hopeful, tender, "
                     "slow, instrumental, no vocals"),
    "place": {"id": "diner", "prompt": (
        "Wide photograph of the inside of an empty roadside diner at three in the morning, nobody in it: a "
        "long counter with a chrome edge and red vinyl stools, a glass pie case holding a cherry pie, a "
        "glass coffee pot on a warmer, a row of red booths along big windows streaked with rain, the glow "
        "of a red and green neon sign outside through the wet glass, warm tungsten light inside, black "
        "night beyond. Deep perspective, anamorphic. " + REAL)},
    "cast": {
        "iris": {"role": "the waitress", "prompt": (
            "Full-length reference photograph of a woman of about sixty-five against a plain mid-grey "
            "backdrop, even soft light, standing still, facing the camera, arms at her sides. Silver hair "
            "pinned up in a loose bun, a warm lined face, reading glasses hanging on a thin chain round her "
            "neck, a pale blue waitress dress with short sleeves and a white apron, a small name badge, "
            "white canvas shoes. " + REAL)},
        "theo": {"role": "the stranger", "prompt": (
            "Full-length reference photograph of a young man of about twenty-five against a plain mid-grey "
            "backdrop, even soft light, standing still, facing the camera, arms at his sides. Dark curly "
            "hair wet and flattened by rain, a few days of stubble, tired kind eyes, a faded denim jacket "
            "over a grey hooded sweatshirt, both soaked dark with rain, black jeans, scuffed white "
            "sneakers. " + REAL)},
    },
    "shots": [
        {"id": "010", "title": "open all night", "secs": 5, "refs": ["diner"], "anchor": None, "engine": "ltx",
         "face": "none", "avoid_extra": NOBODY,
         "prompt": ("Nothing moves in the empty diner but the weather and the light: rain streams down the "
                    "big windows, the neon glow outside flickers on the wet glass, a thread of steam rises "
                    "from the coffee pot on its warmer. Nobody is here. The camera pushes in slowly along "
                    "the counter. Rain against the windows, the buzz of the neon sign, the hum of a "
                    "refrigerator. No music.")},
        {"id": "020", "title": "the bell", "secs": 4, "refs": ["iris", "iris", "diner"], "engine": "ltx",
         "face": "medium",
         "anchor": still("a MEDIUM SHOT", "of the woman of reference one behind the counter of the diner of "
                         "reference three, drying a white coffee cup with a cloth, her head bowed over it, "
                         "warm light on her face, rain on the windows behind her.", G2),
         "prompt": ("The little bell over the door jingles; she looks up from the cup toward the sound and "
                    "her hands stop. Static camera, a faint handheld float. The bell's jingle, a gust of "
                    "rain noise from the door, then the rain muffled again. No music.")},
        {"id": "030", "title": "the stranger", "secs": 5, "refs": ["theo", "theo", "diner"], "engine": "ltx",
         "face": "medium",
         "anchor": still("a MEDIUM SHOT", "of the young man of reference one standing just inside the glass "
                         "door of the diner of reference three, soaked, water running off his jacket, the "
                         "neon glow and the rain behind him through the glass.", G2),
         "prompt": ("He stands dripping just inside the door and hesitates; he pushes the wet hair off his "
                    "forehead with one hand and looks toward the counter. Static camera. Water dripping "
                    "onto the floor mat, the door easing shut behind him, the rain outside muffled. "
                    "No music."),
         "seedance": {"secs": 5, "why": "The only candidate in this film, and a weak one: an entrance is a "
                                         "walk, and our engines hold the walker rather than the walk - so he "
                                         "is already inside when the shot begins. Dialogue, faces and a room "
                                         "at night are what this box does best; nothing else here needs "
                                         "paying for.",
                      "prompt": ("[image 1] is the first frame. The young man of [image 2] pushes the glass "
                                 "door of the diner of [image 3] open against the wind and steps in out of "
                                 "the rain, the bell jingling above him; he stops on the mat, dripping, and "
                                 "looks toward the counter. Static camera, medium shot, warm tungsten "
                                 "inside, blue rain and neon outside. Sound: the bell, a gust of rain, the "
                                 "door easing shut. No music.")}},
        {"id": "040", "title": "coffee", "secs": 5, "refs": ["theo", "iris", "diner"], "engine": "ltx",
         "face": "medium",
         "anchor": still("a MEDIUM TWO-SHOT", "across the chrome counter of the diner of reference three: on "
                         "the left the young man of reference one sitting on a red stool, wet, his hands "
                         "around an empty white cup; on the right the woman of reference two behind the "
                         "counter, holding a glass coffee pot over his cup.", G2),
         "prompt": ("She pours hot coffee into his cup and steam curls up between them in the warm light; he "
                    "wraps both hands around it. Neither of them speaks. Static camera. Coffee pouring into "
                    "the cup, the pot set down on the steel counter, rain on the windows. No music.")},
        {"id": "050", "title": "I can pay", "secs": 5, "refs": ["theo", "theo", "diner"], "engine": "ltx",
         "face": "close", "line": "I can pay for it.",
         "anchor": still("a MEDIUM CLOSE-UP", "of the young man of reference one sitting at the counter of the "
                         "diner of reference three, a steaming white cup in front of him, a few coins in "
                         "his open palm, warm light on his face, neon glow on the wet window behind him.", G2),
         "prompt": ("He sets the coins down on the counter one by one and pushes them forward, not quite "
                    "meeting her eyes, and says quietly, %s: \"I can pay for it.\" Static camera, a faint "
                    "float. The coins clicking on steel, his voice, the rain. No music." % THEO_V)},
        {"id": "060", "title": "house rules", "secs": 6, "refs": ["iris", "iris", "diner"], "engine": "ltx",
         "face": "close", "line": "Coffee's free after three, love. House rules.",
         "anchor": still("a MEDIUM CLOSE-UP", "of the woman of reference one behind the counter of the diner "
                         "of reference three, leaning on the counter with one hand, looking across at "
                         "someone just off camera, a kind half-smile, warm light, the pie case glowing "
                         "behind her.", G2),
         "prompt": ("She slides the coins back across the counter with two fingers and says, %s: \"Coffee's "
                    "free after three, love. House rules.\" Static camera, a faint float. The coins sliding "
                    "on steel, her voice, the rain on the windows. No music." % IRIS_V)},
        {"id": "070", "title": "you don't remember", "secs": 5, "refs": ["theo", "theo", "diner"],
         "engine": "ltx", "face": "close", "line": "You don't remember me.",
         "anchor": still("a CLOSE-UP", "of the young man of reference one at the counter of the diner of "
                         "reference three, rain water still on his face, looking up at someone just off "
                         "camera, warm light and a red neon glint in his eyes.", G2),
         "prompt": ("He looks at her for a long moment, then says quietly, %s: \"You don't remember me.\" "
                    "Static camera, a faint float. His voice, the rain, the refrigerator's hum. "
                    "No music." % THEO_V)},
        {"id": "080", "title": "yellow raincoat", "secs": 7, "refs": ["iris", "iris", "diner"],
         "engine": "ltx", "face": "close", "line": "Yellow raincoat. Cherry pie. You were seven.",
         "anchor": still("a CLOSE-UP", "of the woman of reference one behind the counter of the diner of "
                         "reference three, her reading glasses on, looking at someone just off camera, warm "
                         "light on her lined face.", G2),
         "prompt": ("She takes her reading glasses off slowly and looks at him properly; her face softens and "
                    "she says, %s: \"Yellow raincoat. Cherry pie. You were seven.\" Static camera, a faint "
                    "float. Her voice, the rain, the neon buzz. No music." % IRIS_V)},
        {"id": "090", "title": "the pie", "secs": 4, "refs": ["iris", "iris", "diner"], "engine": "ltx",
         "face": "none",
         "anchor": still("an INSERT CLOSE-UP", "on the chrome counter of the diner of reference three: a "
                         "steaming white coffee cup, and the hand of the woman of reference one, in a pale "
                         "blue sleeve, setting down a plate with a slice of cherry pie beside it.", G2),
         "prompt": ("Her hand sets the plate down beside the cup, gives it a small push forward, and "
                    "withdraws. Static camera, close. The plate touching down on steel, the rain. "
                    "No music.")},
        {"id": "100", "title": "he laughs", "secs": 5, "refs": ["theo", "theo", "diner"], "engine": "both",
         "face": "close",
         "anchor": still("a CLOSE-UP", "of the young man of reference one at the counter of the diner of "
                         "reference three, looking down at something on the counter in front of him, eyes "
                         "wet, warm light on his face.", G2),
         "prompt": ("His eyes fill; he laughs once, softly, through his nose, and wipes his eye with the heel "
                    "of his hand, smiling down at the counter. Static camera, a faint float. His soft breath "
                    "of a laugh, the rain, the neon buzz. No music.")},
        {"id": "110", "title": "last orders", "secs": 7, "refs": ["theo", "iris", "diner"], "engine": "ltx",
         "face": "wide",
         "anchor": still("a WIDE SHOT", "of the diner of reference three from the far end of the counter: "
                         "the young man of reference one sitting on a stool eating pie, the woman of "
                         "reference two leaning on the counter across from him, both small in the frame, "
                         "the neon glow and the rain on the big windows beside them.", G2),
         "prompt": ("She leans on the counter across from him while he eats; she refills his cup, and they "
                    "both laugh at something. Static camera. The low murmur of their voices too quiet to "
                    "make out, rain on the windows, the neon buzz. No music.")},
    ],
    "not_shot": [],
}

# ======================================================================================= TEMPER
G3 = ("Cinematic film, night, deep orange firelight against cool blue moonlight from an open doorway, "
      "glowing embers, drifting smoke haze, rich blacks with detail, fine grain, anamorphic.")
temper = {
    "_comment": "Demo film 3 of 3 (2026-09-29). Texture: fire, sparks and steam. Effects beats rendered on "
                "H3 and LTX both and picked by measurement; one multishot generation with internal cuts.",
    "film": "temper", "title": "TEMPER",
    "logline": "One night at the forge: fire, hammer, water, and a blade that holds its edge.",
    "grade": G3, "avoid": AVOID, "realism": REAL,
    "score_tags": ("slow cinematic build, deep taiko drums, low droning cello, metallic percussion like "
                   "distant anvils, dark, epic, instrumental, no vocals"),
    "score_tags_b": ("cinematic climax and release, full low strings and pounding taiko, then a single "
                     "long sustained string note fading, instrumental, no vocals"),
    "place": {"id": "forge", "prompt": (
        "Wide photograph of the inside of an old stone village forge at night, nobody in it: a brick hearth "
        "with a bed of glowing orange coals under a sooty hood, a heavy black iron anvil on a tree-stump "
        "block in the middle of the floor, hammers and tongs hanging on the rough stone wall, a wooden "
        "trough of dark water, big leather bellows, smoke drifting under old timber rafters, a doorway open "
        "onto blue moonlit night. Deep perspective, anamorphic. " + REAL)},
    "cast": {
        "maren": {"role": "the smith", "prompt": (
            "Full-length reference photograph of a broad-shouldered strong woman of about forty-five against "
            "a plain mid-grey backdrop, even soft light, standing still, facing the camera, arms at her "
            "sides. Dark hair tied back under a faded red headscarf, a weathered face with a smudge of soot "
            "on one cheek, bare muscular forearms streaked with soot, a heavy scorched brown leather apron "
            "over a sleeveless grey linen shirt, thick leather work gloves, heavy boots. " + REAL)},
    },
    "shots": [
        {"id": "010", "title": "the forge", "secs": 5, "refs": ["forge"], "anchor": None, "engine": "ltx",
         "face": "none", "avoid_extra": NOBODY,
         "prompt": ("Nothing moves in the empty forge but the fire: the bed of coals glows and pulses, small "
                    "flames lick up and die back, sparks drift up into the hood, smoke curls along the "
                    "rafters. Nobody is here. The camera pushes in slowly toward the hearth. The low roar of "
                    "the fire, crackling coals, a distant owl. No music.")},
        {"id": "020", "title": "bellows", "secs": 4, "refs": ["maren", "maren", "forge"], "engine": "both",
         "face": "none",
         "anchor": still("an INSERT CLOSE-UP", "of the big leather bellows beside the hearth of the forge of "
                         "reference three, the gloved hand of the woman of reference one on the wooden "
                         "handle, the bed of coals glowing beside it.", G3),
         "prompt": ("The gloved hand pumps the bellows down hard twice; at each breath of air the coals flare "
                    "white-hot and a spray of sparks leaps up into the hood. Static camera, close. The deep "
                    "whoosh of the bellows, the fire roaring up, sparks crackling. No music.")},
        {"id": "030", "title": "watching", "secs": 5, "refs": ["maren", "maren", "forge"], "engine": "both",
         "face": "close",
         "anchor": still("a CLOSE-UP", "of the woman of reference one in the forge of reference three, her "
                         "face lit from below by the orange glow of the hearth, eyes fixed on the fire, "
                         "sweat on her brow, smoke drifting past.", G3),
         "prompt": ("She watches the fire without blinking; the glow pulses across her face, and a bead of "
                    "sweat runs down her temple. Handheld camera close, almost still. The roar of the fire, "
                    "crackling coals, her slow breath. No music.")},
        {"id": "040", "title": "the blade", "secs": 4, "refs": ["maren", "maren", "forge"], "engine": "ltx",
         "face": "none",
         "anchor": still("an INSERT CLOSE-UP", "inside the hearth of the forge of reference three: long iron "
                         "tongs gripping a blade buried in the glowing coals, held by the gloved hand of the "
                         "woman of reference one.", G3),
         "prompt": ("The tongs draw the long blade out of the coals; it glows bright orange-yellow along its "
                    "whole length and sheds sparks as it comes. Static camera, close. Steel scraping over "
                    "coals, the fire's crackle and roar. No music.")},
        {"id": "050", "title": "first blow", "secs": 5, "refs": ["maren", "maren", "forge"], "engine": "both",
         "face": "medium",
         "anchor": still("a MEDIUM SHOT", "of the woman of reference one standing at the anvil in the forge of "
                         "reference three, a heavy hammer raised in her right hand, the glowing orange blade "
                         "held flat on the anvil with tongs in her left, the hearth blazing behind her.", G3),
         "prompt": ("She brings the hammer down on the glowing blade, once, twice, three times; at each blow a "
                    "burst of bright sparks sprays off the anvil and dies away. Static camera. The ringing "
                    "clang of the hammer on hot steel at each blow, the fire roaring behind her. No music."),
         "seedance": {"secs": 5, "why": "Sparks that exist at the instant of each blow and are gone before "
                                         "the next - the breakdown's rule 3, which we measured does not "
                                         "transfer to LTX-2.5 (the effect accumulates) and partly does to H3. "
                                         "This shot is rendered on both and picked; Seedance is the engine "
                                         "that keys an effect to an impact frame.",
                      "prompt": ("[image 1] is the first frame. The woman of [image 2] brings the hammer "
                                 "down on the glowing blade on the anvil of the forge of [image 3] three "
                                 "times in a steady rhythm; at the exact instant each blow lands a burst of "
                                 "white-orange sparks explodes off the steel and is gone before the hammer "
                                 "rises again; between the blows the air is clear. Medium shot, static "
                                 "camera, firelight and blue moonlight. Sound: three ringing clangs, each "
                                 "with the spit of sparks, the fire's roar. No music.")}},
        {"id": "060", "title": "the rhythm", "secs": 8, "refs": ["maren", "maren", "forge"], "engine": "ltx",
         "face": "medium",
         "anchor": still("a MEDIUM CLOSE SHOT", "of the woman of reference one at the anvil in the forge of "
                         "reference three, mid-swing, the hammer high, the glowing blade on the anvil in "
                         "front of her, sparks hanging in the air, firelight on her face.", G3),
         "prompt": ("She hammers the glowing blade in a steady rhythm, sparks flying at every blow. Cut to a "
                    "close-up of the hammer striking the orange steel on the anvil in a burst of sparks. Cut "
                    "to a close-up of her face, sweat and firelight, eyes on the work. Cut back to her at the "
                    "anvil as she turns the blade with the tongs and strikes again. Static camera in every "
                    "shot. The ringing rhythm of the hammer, the roar of the fire, her breath. No music."),
         "seedance": {"secs": 10, "why": "Several angles on fast repeated strikes in one generation. LTX-2.5 "
                                          "does the cuts (measured: the word cut makes the cut, and the face "
                                          "holds when it is in the start frame) but not the speed of the "
                                          "swing; Seedance's 15-second multi-shot with references is built "
                                          "for exactly this.",
                      "prompt": ("[image 1] is the first frame. The woman of [image 2] works the glowing "
                                 "blade on the anvil of the forge of [image 3] in a fast, heavy rhythm. Shot "
                                 "one, medium: three hard blows, sparks bursting at each. Cut to shot two, "
                                 "an extreme close-up: the hammer face meeting the orange steel, sparks "
                                 "spraying at the lens. Cut to shot three, a close-up of her face in the "
                                 "firelight, eyes narrowed, sweat running. Cut to shot four, medium: she "
                                 "turns the blade with the tongs and brings the hammer down again. Sound: "
                                 "the ringing rhythm of the hammer, her breath, the fire's roar. No music.")}},
        {"id": "070", "title": "quench", "secs": 4, "refs": ["maren", "maren", "forge"], "engine": "both",
         "face": "none",
         "anchor": still("an INSERT CLOSE-UP", "of a wooden trough of dark water in the forge of reference "
                         "three, a glowing orange blade held in tongs by the gloved hand of the woman of "
                         "reference one just above the surface.", G3),
         "prompt": ("The glowing blade plunges into the water; the water boils violently around it and a "
                    "thick cloud of white steam bursts up and rolls away across the frame. Static camera, "
                    "close. A loud angry hiss and bubbling, then the steam's fading sigh. No music."),
         "seedance": {"secs": 4, "why": "A burst of steam at the instant of contact that must then roll away "
                                         "and clear - rule 3 again. Rendered here on H3 and LTX and picked.",
                      "prompt": ("[image 1] is the first frame. The glowing blade held by the woman of "
                                 "[image 2] plunges into the water trough of the forge of [image 3]; at the "
                                 "instant it touches, the water erupts into a violent boil and a burst of "
                                 "white steam, which rolls away and thins in a second to show the dark "
                                 "blade under the water. Insert close-up, static camera. Sound: a sharp "
                                 "angry hiss at the instant of contact, bubbling, then quiet. No music.")}},
        {"id": "080", "title": "through the steam", "secs": 5, "refs": ["maren", "maren", "forge"],
         "engine": "both", "face": "medium",
         "anchor": still("a MEDIUM CLOSE-UP", "of the woman of reference one standing in drifting white steam "
                         "in the forge of reference three, holding a dark blade upright in her gloved hand, "
                         "firelight behind her.", G3),
         "prompt": ("The steam thins around her; she raises the dark blade to eye level and sights down its "
                    "edge, turning it slowly in the firelight. Handheld camera, a faint float. The last hiss "
                    "of steam, the fire's low roar. No music.")},
        {"id": "090", "title": "the edge", "secs": 5, "refs": ["maren", "maren", "forge"], "engine": "ltx",
         "face": "close",
         "anchor": still("a CLOSE-UP", "of the woman of reference one in the forge of reference three holding "
                         "a finished dark steel blade upright beside her face, its bright edge catching the "
                         "firelight, soot on her cheek.", G3),
         "prompt": ("She turns the blade a little so the firelight runs along its edge like a line of light; "
                    "the ghost of a satisfied smile. Static camera, a faint float. The fire crackling low, "
                    "her slow breath out. No music.")},
        {"id": "100", "title": "hang the hammer", "secs": 6, "refs": ["maren", "maren", "forge"], "engine": "ltx",
         "face": "wide",
         "anchor": still("a WIDE SHOT", "of the forge of reference three at night, the woman of reference one "
                         "standing by the stone wall hanging a hammer on its hook, the finished blade in her "
                         "other hand, the fire in the hearth burning low, blue moonlight in the doorway.", G3),
         "prompt": ("She hangs the hammer on its hook and stands for a moment looking at the fire burning "
                    "down, the blade in her hand. Static camera. The hammer's clink on the hook, the fire "
                    "crackling low, an owl outside. No music.")},
        {"id": "110", "title": "embers", "secs": 5, "refs": ["forge"], "anchor": None, "engine": "ltx",
         "face": "none", "avoid_extra": NOBODY,
         "prompt": ("Nothing moves in the empty forge but the dying fire: the coals fade from orange to a dull "
                    "red glow, a last thin curl of smoke rises into the hood, and the moonlight lies still "
                    "in the doorway. Nobody is here. Static camera. The faint tick and crackle of cooling "
                    "coals, the night outside. No music.")},
    ],
    "not_shot": [
        {"title": "the full forging, one take", "why": "A whole forging in one continuous 15-second take - "
                                                      "heat, strike, turn, strike, quench - is a chain of "
                                                      "fast motions with effects at each instant. We cut it "
                                                      "into one beat per shot, which is what this box does "
                                                      "well; Seedance would attempt it in one.",
         "seedance": ("[image 1] is the woman of [image 2] at the anvil of the forge of [image 3]. In one "
                      "continuous take she draws the glowing blade from the coals, strikes it four times with "
                      "sparks bursting at each blow, turns it, strikes twice more, then plunges it into the "
                      "trough in an eruption of steam. Handheld camera circling her slowly. Sound: the fire, "
                      "six ringing blows, the hiss of the quench. No music."), "secs": 15},
    ],
}

os.makedirs(DST, exist_ok=True)
for seq in (dead_stock, house_rules, temper):
    p = os.path.join(DST, seq["film"] + ".json")
    json.dump(seq, open(p, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    tot = sum(s["secs"] for s in seq["shots"])
    eng = {}
    for s in seq["shots"]:
        eng[s.get("engine", "ltx")] = eng.get(s.get("engine", "ltx"), 0) + 1
    print("wrote %-40s %2d shots, %d s, cast %s, engines %s" % (
        os.path.relpath(p, ROOT), len(seq["shots"]), tot, ",".join(seq["cast"]), eng))
