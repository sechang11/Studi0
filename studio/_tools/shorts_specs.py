#!/usr/bin/env python3
"""studio/_tools/shorts_specs.py - the 20 overnight short-form pieces, as SPECS.

    python3 studio/_tools/shorts_specs.py --write films/shorts

A spec is the compact thing a person edits: id, kind, voice, cue, style, and a list of
beats each holding a prompt, a motion, a spoken line, a caption and optionally an effect.
The builder expands it into the full film JSON short.py renders, applying the house rules
this project measured rather than making the author remember them:

  vertical 1080x1920                short form is watched on a phone
  captions on every beat            short form is watched MUTED first
  transitions only where the beat    a 0.25s dissolve cannot live on a 0.2s micro-shot
    is long enough                   (short.py says so out loud when it skips)
  camera moves as ffmpeg post        measured: asking LTX for a camera move fails 5-22%
  keyframe engine qwen (prose)       these are photographic subjects, not anime
  motion text names ONE mover        the motion library's own rule

THREE KINDS, and the content rules that go with them:

  supplement  Neutral, evidence-framed summaries. NO dosing prescriptions, no "cures",
              no invented studies or numbers presented as citations. Every piece ends on
              the same honest beat: this is general information, not medical advice, and
              individual needs differ. That is both the responsible choice and the one
              that survives contact with an audience.
  commercial  INVENTED brands only (the project's standing rule: no real brands in
              typography or props). Product categories are ordinary; the names are ours.
  hook        The GRAMMAR of a scroll-stopping open - cold image, question, whip, payoff -
              cast with OUR places and characters. No third-party footage is used or
              implied; what is borrowed is the SHAPE, which is what the Dragon Ball
              breakdown established as the reusable part.
"""
import argparse
import json
import os
import sys

TOOLS = os.path.dirname(os.path.abspath(__file__))
STUDIO = os.path.dirname(TOOLS)
ROOT = os.path.dirname(STUDIO)

CANVAS = [1080, 1920]
FPS = 24

# Voices chosen from the MEASURED library (samples/voices/*.json): pitch, brightness and
# pace are on the cards, so casting is a lookup rather than a guess.
V_INFORM = "voices_examples/male/male_03_carter.wav"    # 129 Hz, warm, fast - explainer
V_CALM = "voices_examples/male/male_04_frank.wav"       # 115 Hz, narrow range - steady
V_WARM_F = "voices_examples/female/female_04_maya.wav"    # 198 Hz, dark/warm - brand warmth
V_BRIGHT_F = "voices_examples/female/female_03_alice.wav"  # 214 Hz, young, clear
V_LOW = "voices_examples/male/male_02.wav"                     # 82 Hz - the lowest, for menace

STYLE_CLEAN = ("clean modern product photography, soft diffused daylight, shallow depth "
               "of field, matte surfaces, muted natural palette, minimal composition, "
               "crisp focus, high detail")
# "morning kitchen light" plus "soft shadows, muted earthy palette" cancelled out: this
# preset measured 94.4 luma against 96.6 for no style at all, i.e. it was inert, while
# six delivered films leaned on it for exactly the brightness it was not providing.
# Rebuilt with both halves the measurement supports - a NAMED bright surface and the
# bright adjectives - and without "muted". Verify with studio/_tools/style_bright.py.
STYLE_KITCHEN = ("warm documentary photography, a white kitchen counter by a large "
                 "window, morning sunlight falling across the worktop, bright and airy, "
                 "natural textures, shallow depth of field, high detail")
STYLE_LAB = ("clean scientific still life, cool even lighting, white and steel surfaces, "
             "glass and precision instruments, shallow depth of field, minimal, high detail")
STYLE_NATURE = ("natural light landscape photography, soft golden hour, gentle haze, "
                "muted greens and warm neutrals, shallow depth of field, high detail")
STYLE_CINE = ("cinematic film still, anamorphic, dramatic contrast, moody practical "
              "lighting, rich shadows, filmic grain, high detail")

DISCLAIMER = ("General information, not medical advice. Talk to a doctor about what fits "
              "you.")

SUPPLEMENTS = [
    dict(id="sup-creatine", title="CREATINE", hook="creatine|what it actually does",
         cue="driving_pulse", voice=V_INFORM, style=STYLE_LAB,
         beats=[
             ("A single scoop of fine white powder on a clean steel surface, top-down, "
              "soft studio light, one shaft of light across it",
              "The powder settles slowly. Dust drifts in the light.",
              "Creatine is the most studied sports supplement there is.",
              "The most studied one on the shelf", "quiet room tone, a soft scoop of powder"),
             ("A glass of water on a steel counter with powder dissolving in it, "
              "close-up, backlit, small bubbles rising",
              "The powder swirls and dissolves. Bubbles rise slowly.",
              "Your muscles store it as phosphocreatine, and use it to recycle energy "
              "during short, hard efforts.",
              "It recycles energy for short hard efforts", None),
             ("A heavy barbell resting on a gym floor in low warm light, chalk dust in "
              "the air, close-up on the knurling",
              "Chalk dust drifts slowly through the light.",
              "That mostly shows up in the last rep or two of a heavy set. Small, but "
              "real, and it adds up over months.",
              "Shows up in the last rep or two", "a barbell settling on a gym floor"),
             ("A simple glass of water beside a plain notebook on a wooden table, "
              "morning light, calm and ordinary",
              "Light shifts slowly across the table.",
              "The research also looks at effects beyond the gym, but that work is "
              "younger and less settled.",
              "Other effects are still being studied", None),
             ("An open palm holding a small amount of white powder, soft daylight, "
              "shallow focus, quiet and honest",
              "The hand stays still. Light moves gently.",
              "It is cheap, it is well studied, and it is not magic.",
              "Cheap, well studied, not magic", None),
             ("A clean empty countertop with a single glass of water, soft light, "
              "text-free minimal composition",
              "Still. Light drifts almost imperceptibly.",
              DISCLAIMER, "Not medical advice", None),
         ]),
    dict(id="sup-vitamin-d", title="VITAMIN D", hook="vitamin D|the sunlight one",
         cue="quiet_dawn", voice=V_CALM, style=STYLE_NATURE,
         beats=[
             ("Low winter sun through a bare window onto a wooden floor, long shadows, "
              "dust in the light, quiet interior",
              "The light creeps slowly across the floor. Dust drifts.",
              "Your skin makes vitamin D from sunlight. That is the whole reason this "
              "one is complicated.",
              "Your skin makes it from sunlight", "a quiet room, faint outdoor hum"),
             ("An overcast grey sky over a cold northern city rooftop, flat light, "
              "muted palette, no people",
              "Cloud moves slowly across the sky.",
              "Far from the equator, in winter, the sun sits too low for your skin to "
              "make much of it at all.",
              "In winter, far north, the sun is too low", None),
             ("A plate of oily fish and eggs on a plain table, soft daylight, "
              "documentary style, close-up",
              "Steam drifts gently from the plate.",
              "Some comes from food. Oily fish, egg yolks, fortified milk.",
              "Some comes from food", None),
             ("A small blood sample vial on a clean white surface beside a lab form, "
              "cool even light, clinical and calm",
              "Very still. A faint shadow shifts.",
              "It is one of the few where a blood test actually tells you where you "
              "stand, instead of guessing.",
              "A blood test tells you where you stand", None),
             ("A person's silhouette at a bright window, backlit, warm light spilling "
              "in, calm and hopeful",
              "The light brightens slowly and steadies.",
              DISCLAIMER, "Not medical advice", None),
         ]),
    dict(id="sup-magnesium", title="MAGNESIUM", hook="magnesium|which one, though",
         cue="warm_memory", voice=V_INFORM, style=STYLE_CLEAN,
         beats=[
             ("Several small unlabelled glass jars of white powder in a row on a pale "
              "surface, soft even light, minimal",
              "Light shifts slowly across the jars.",
              "Magnesium is not one thing. What it is bound to changes how much you "
              "absorb.",
              "It is not one thing", "glass jars set down on a counter"),
             ("A close-up of magnesium-rich foods, pumpkin seeds and dark leafy greens "
              "on a wooden board, natural light",
              "A faint breeze moves the leaves.",
              "Most people get some from food. Seeds, greens, beans, whole grains.",
              "Seeds, greens, beans, grains", None),
             ("A glass of water on a bedside table in warm low lamplight, evening mood, "
              "shallow focus",
              "The lamp flickers very slightly. Still otherwise.",
              "Different forms are marketed for different things - sleep, digestion, "
              "muscle cramps - and the evidence is stronger for some than others.",
              "Different forms, different claims", None),
             ("An empty bed with soft morning light across white sheets, calm, "
              "no people, quiet",
              "Light moves slowly across the sheets.",
              "The honest summary: correcting a real shortfall helps. Adding more on "
              "top of enough usually does not.",
              "Fixing a shortfall helps; more does not", None),
             ("A single glass jar on a clean surface, soft light, minimal composition",
              "Still. Light drifts.",
              DISCLAIMER, "Not medical advice", None),
         ]),
    dict(id="sup-omega3", title="OMEGA-3", hook="omega-3|fish oil, honestly",
         cue="quiet_dawn", voice=V_CALM, style=STYLE_KITCHEN,
         beats=[
             ("A fillet of oily fish on ice on a steel counter, close-up, cold blue "
              "light, glistening surface",
              "Ice melts very slowly. A drop runs down.",
              "Omega-3s are fats your body cannot make. You have to eat them.",
              "Your body cannot make these", "ice shifting on a steel counter"),
             ("Amber capsules spilled on a pale surface beside a glass of water, soft "
              "daylight, shallow depth of field",
              "The capsules settle. Light glints across them.",
              "Two of them do most of the work in the research: EPA and DHA. Both come "
              "mainly from marine sources.",
              "EPA and DHA do most of the work", None),
             ("A plate of grilled salmon and greens on a wooden table, warm kitchen "
              "light, documentary style",
              "Steam drifts up gently.",
              "Eating fish a couple of times a week gets most people there without a "
              "bottle.",
              "Fish twice a week gets most people there", None),
             ("A row of unlabelled amber bottles on a shelf, soft light, muted palette, "
              "clean composition",
              "Light shifts slowly along the shelf.",
              "Supplements are for filling the gap when that does not happen. Freshness "
              "matters more than people think - rancid oil is common.",
              "Freshness matters more than people think", None),
             ("A clean empty plate and a glass of water on a wooden table, morning "
              "light, calm",
              "Still, light drifting.",
              DISCLAIMER, "Not medical advice", None),
         ]),
    dict(id="sup-protein", title="PROTEIN", hook="protein|how much is enough",
         cue="training_montage", voice=V_INFORM, style=STYLE_KITCHEN,
         beats=[
             ("Eggs, chicken, lentils and yoghurt arranged on a wooden board, top-down, "
              "natural light, documentary style",
              "Light moves slowly across the board.",
              "Protein is the one most people already understand and still get slightly "
              "wrong.",
              "Most people get this slightly wrong", "a wooden board set down"),
             ("A kitchen scale with a portion of food on it, close-up, morning light, "
              "shallow focus",
              "The needle settles. Light drifts.",
              "The research points at a daily total, spread across the day - not a "
              "magic window right after training.",
              "The daily total matters most", None),
             ("A protein shaker on a gym bench in warm side light, condensation on the "
              "surface, close-up",
              "A drop of condensation runs down the side.",
              "Powder is a convenience, not a category of its own. It is food that "
              "happens to be easy to carry.",
              "Powder is convenience, not magic", "a shaker set down on a bench"),
             ("A simple home-cooked meal on a plate, warm evening light, honest and "
              "ordinary, documentary style",
              "Steam rises gently.",
              "Needs go up if you are training hard or older. They do not go up to the "
              "numbers on the tub.",
              "Needs go up - not that far up", None),
             ("An empty clean plate on a wooden table, soft light, minimal",
              "Still. Light drifting.",
              DISCLAIMER, "Not medical advice", None),
         ]),
    dict(id="sup-caffeine", title="CAFFEINE + THEANINE", hook="caffeine|the calm version",
         cue="hopeful_rising", voice=V_BRIGHT_F, style=STYLE_CLEAN,
         beats=[
             ("A dark espresso being poured into a small white cup, close-up, warm side "
              "light, steam rising",
              "The coffee pours and swirls. Steam rises.",
              "Caffeine blocks the signal that makes you feel tired. It does not add "
              "energy - it hides the debt.",
              "It hides tiredness, it does not add energy", "espresso pouring into a cup"),
             ("A cup of green tea beside a window in soft morning light, gentle steam, "
              "calm composition",
              "Steam drifts and curls slowly.",
              "Green tea carries theanine alongside it, which is why tea tends to feel "
              "smoother than the same caffeine from coffee.",
              "Theanine is why tea feels smoother", None),
             ("A desk with a notebook, pen and a cup, warm lamp light, focused working "
              "mood, shallow focus",
              "Light steadies. A page lifts slightly.",
              "Together they show up in the research as steadier attention with less of "
              "the jittery edge.",
              "Steadier attention, less jitter", None),
             ("An empty cup beside a dark window at night, low warm light, quiet and "
              "still",
              "Very still. A faint reflection moves.",
              "The catch is the same as always: it has a long tail, and afternoon coffee "
              "is tomorrow's tiredness.",
              "Afternoon coffee is tomorrow's tiredness", None),
             ("A clean cup and saucer on a pale surface, soft daylight, minimal",
              "Still, light drifting gently.",
              DISCLAIMER, "Not medical advice", None),
         ]),
    dict(id="sup-fibre", title="FIBRE", hook="fibre|the boring one that works",
         cue="warm_memory", voice=V_WARM_F, style=STYLE_KITCHEN,
         beats=[
             ("A rustic loaf of wholegrain bread cut open on a wooden board, close-up, "
              "warm morning light, crumb texture visible",
              "Crumbs settle. Light moves across the crust.",
              "Fibre is the least glamorous thing on this list and probably the one "
              "most people are short on.",
              "The least glamorous, most missed", "a bread knife on a board"),
             ("Oats, beans and apples arranged on a pale surface, top-down, natural "
              "light, clean documentary style",
              "Light shifts slowly.",
              "Some of it dissolves and slows digestion. Some of it does not, and keeps "
              "things moving.",
              "Two kinds, two jobs", None),
             ("A bowl of porridge with berries on a wooden table, warm kitchen light, "
              "steam rising, close-up",
              "Steam drifts up from the bowl.",
              "It also feeds the bacteria in your gut, which is where a lot of the "
              "current research is pointed.",
              "It feeds your gut bacteria", None),
             ("A glass of water beside a bowl of oats on a table, soft daylight, simple "
              "composition",
              "Light drifts. Very still.",
              "One practical note: add it slowly and drink water, or you will regret "
              "the enthusiasm.",
              "Add it slowly. Drink water.", None),
             ("An empty wooden board on a table, warm light, minimal",
              "Still, light moving gently.",
              DISCLAIMER, "Not medical advice", None),
         ]),
    dict(id="sup-sleep", title="SLEEP & MELATONIN", hook="melatonin|it is a clock, not a sedative",
         cue="lonely_night_city", voice=V_CALM, style=STYLE_CINE,
         beats=[
             ("A dark bedroom with a single bedside lamp on, warm pool of light, night "
              "outside the window, calm",
              "The lamp glows steadily. Shadows shift very slightly.",
              "Melatonin is a timing signal, not a sedative. It tells your body it is "
              "night.",
              "A timing signal, not a sedative", "a quiet bedroom at night, faint hum"),
             ("A city window at night with blue screen light spilling into a dark room, "
              "moody, cinematic",
              "The blue light flickers faintly.",
              "Bright light late in the evening delays that signal. Which is why the "
              "phone is part of the problem.",
              "Late bright light delays the signal", None),
             ("An airport departure board at night, out of focus, cool light, travel "
              "mood, cinematic",
              "The board flickers and updates.",
              "The clearest use in the research is jet lag and shifted schedules - "
              "moving the clock, not forcing sleep.",
              "Clearest use: moving the clock", "a distant airport hum"),
             ("A dark quiet bedroom with the first grey light at the curtains, calm, "
              "cinematic, no people",
              "The light at the curtain slowly brightens.",
              "For ordinary bad sleep, the dull advice still beats the bottle: same "
              "wake time, dark room, less light at night.",
              "The dull advice still wins", None),
             ("An empty made bed in soft morning light, calm and quiet, minimal",
              "Light brightens slowly.",
              DISCLAIMER, "Not medical advice", None),
         ]),
]

COMMERCIALS = [
    dict(id="ad-northwind-tea", title="NORTHWIND TEA", hook="NORTHWIND|the slow cup",
         cue="warm_memory", voice=V_WARM_F, style=STYLE_KITCHEN,
         beats=[
             ("Loose black tea leaves spilling from a plain paper packet onto a wooden "
              "counter, warm morning light, close-up",
              "The leaves settle. Light drifts across them.",
              "Some mornings you need the day to start slowly.",
              "Some mornings start slowly", "tea leaves poured onto wood"),
             ("Hot water poured over tea leaves in a glass pot, steam rising, backlit, "
              "close-up, the water darkening",
              "The water pours and darkens. Steam rises and curls.",
              "Northwind is a plain black tea. No claims, no ceremony.",
              "A plain black tea", "water pouring into a glass pot"),
             ("A ceramic mug of tea on a windowsill with rain on the glass behind it, "
              "soft grey light, cosy mood",
              "Rain runs down the glass. Steam drifts from the mug.",
              "Grown on a hillside, dried slowly, packed the same week.",
              "Dried slowly. Packed the same week.", "gentle rain on a window"),
             ("Two hands wrapped around a warm mug, close-up, soft window light, quiet "
              "and human",
              "The hands hold still. Steam drifts.",
              "Northwind. Take the long way through the morning.",
              "NORTHWIND - take the long way", None),
         ]),
    dict(id="ad-pace-runner", title="PACE", hook="PACE|built for the fifth mile",
         cue="driving_pulse", voice=V_INFORM, style=STYLE_CINE,
         beats=[
             ("A single running shoe on wet tarmac at dawn, close-up, cold blue light, "
              "water beading on the surface",
              "A drop of water runs off the sole.",
              "The first mile is easy. Anyone can sell you the first mile.",
              "Anyone can sell you mile one", "a shoe set down on wet ground"),
             ("A runner's legs mid-stride on an empty city street at dawn, motion blur, "
              "cinematic, low angle",
              "The legs drive forward hard. Spray kicks up from the road.",
              "PACE is built for the fifth. Where the cushioning usually gives up.",
              "Built for mile five", "fast footsteps on wet tarmac"),
             ("A close-up of a shoe sole showing dense foam structure, studio light, "
              "clean product photography",
              "Light travels slowly across the sole.",
              "A denser midsole that holds its shape when you are tired and sloppy.",
              "Holds its shape when you are tired", None),
             ("A runner stopping at the top of a hill at sunrise, seen from behind, wide "
              "shot, warm light breaking",
              "The runner's chest rises and falls. Light brightens across the hill.",
              "PACE. The mile that counts is the one after you wanted to stop.",
              "PACE - the mile after you wanted to stop", None),
         ]),
    dict(id="ad-lumen-lamp", title="LUMEN", hook="LUMEN|light that knows the hour",
         cue="hopeful_rising", voice=V_BRIGHT_F, style=STYLE_CLEAN,
         beats=[
             ("A minimal desk lamp on an empty desk in a dark room, single warm pool of "
              "light, clean product photography",
              "The light brightens very slowly.",
              "Most desk lamps have one setting: on.",
              "Most lamps have one setting", "a lamp switch clicking"),
             ("The same lamp casting cool bright light across a desk with an open "
              "notebook, daytime mood, crisp",
              "The light shifts gradually cooler and brighter.",
              "LUMEN moves with the day. Cool and bright when you need to think.",
              "Cool and bright to think", None),
             ("The lamp in warm amber light over a desk in a dark evening room, cosy, "
              "shallow focus",
              "The light warms slowly, amber deepening.",
              "Warm and low when you need to stop.",
              "Warm and low to stop", None),
             ("A hand switching the lamp off, room going dark except for a window, "
              "calm, cinematic",
              "The light fades out. The window glows faintly.",
              "LUMEN. Light that knows what time it is.",
              "LUMEN - light that knows the hour", "a soft click"),
         ]),
    dict(id="ad-tidewater", title="TIDEWATER", hook="TIDEWATER|three things, that is all",
         cue="quiet_dawn", voice=V_WARM_F, style=STYLE_CLEAN,
         beats=[
             ("A plain unlabelled glass bottle on a wet stone surface, soft grey "
              "daylight, water droplets, minimal",
              "A droplet runs down the bottle.",
              "The shelf is full of bottles with twenty ingredients.",
              "Twenty ingredients on the shelf", "water dripping on stone"),
             ("A close-up of clear gel on fingertips, soft light, clean and simple, "
              "shallow focus",
              "The gel catches the light as the fingers move.",
              "Tidewater has three. Water, glycerin, and an oil pressed from seed.",
              "Ours has three", None),
             ("A plain bottle beside a window with grey sea light outside, calm coastal "
              "mood, minimal composition",
              "Light shifts slowly. The sea moves far behind.",
              "Nothing that needs explaining. Nothing that needs a chart.",
              "Nothing that needs a chart", "distant surf"),
             ("The bottle alone on a pale stone surface, soft daylight, quiet product "
              "photography",
              "Still. Light drifts gently.",
              "Tidewater. Three things, and none of them is a promise.",
              "TIDEWATER - three things", None),
         ]),
    dict(id="ad-atlas-pack", title="ATLAS", hook="ATLAS|it has been everywhere",
         cue="epic_battle", voice=V_LOW, style=STYLE_CINE,
         beats=[
             ("A worn canvas backpack on a rock at altitude, wide mountain light behind, "
              "cinematic, weathered texture",
              "Wind moves the straps. Cloud drifts behind.",
              "This pack is nine years old.",
              "Nine years old", "high wind over rock"),
             ("Close-up of frayed but intact stitching on a canvas strap, hard side "
              "light, texture detail",
              "Light travels slowly across the stitching.",
              "The stitching is doubled where every other pack tears first.",
              "Doubled where others tear", None),
             ("The pack being lifted onto shoulders, seen from behind, dawn light on a "
              "mountain trail, cinematic",
              "The pack lifts and settles onto the shoulders.",
              "It is heavier than the light ones. That is the trade, and we are not "
              "going to pretend otherwise.",
              "Heavier. That is the trade.", "canvas and buckles shifting"),
             ("The pack silhouetted against a bright sky at a summit, wide shot, "
              "triumphant light",
              "Wind moves the straps against the sky.",
              "ATLAS. Buy it once.",
              "ATLAS - buy it once", None),
         ]),
    dict(id="ad-slow-sunday", title="SLOW SUNDAY", hook="SLOW SUNDAY|nowhere to be",
         cue="warm_memory", voice=V_WARM_F, style=STYLE_KITCHEN,
         beats=[
             ("An unmade bed with morning light across the sheets, empty room, warm and "
              "quiet, no people",
              "Light moves slowly across the sheets.",
              "Sunday used to be a whole day.",
              "Sunday used to be a whole day", "a quiet room, distant birds"),
             ("Coffee brewing slowly in a glass pot on a kitchen counter, steam, warm "
              "morning light, close-up",
              "The coffee drips slowly. Steam rises.",
              "Slow Sunday is a coarse ground for a slow brew. It takes eight minutes.",
              "It takes eight minutes", "coffee dripping into glass"),
             ("A newspaper and a full cup on a kitchen table, morning light, unhurried "
              "domestic scene",
              "A page lifts slightly in a draught. Steam drifts.",
              "That is the point. You cannot rush it, so you do not.",
              "You cannot rush it, so you do not", None),
             ("An empty kitchen in warm late morning light, a single cup on the table, "
              "peaceful",
              "Light drifts across the table.",
              "Slow Sunday. Nowhere to be.",
              "SLOW SUNDAY - nowhere to be", None),
         ]),
]

# Hook grammar: cold image -> question -> whip -> payoff in OUR world. The shape is the
# borrowed part; every frame is ours.
HOOKS = [
    dict(id="hook-door", title="THE DOOR", hook="do not open it|until you know",
         cue="unease", voice=V_LOW, style=STYLE_CINE, transition="whip_pan",
         beats=[
             ("An ordinary door at the end of a dim corridor, single light above it, "
              "cinematic, unsettling stillness",
              "The light above the door flickers once.",
              "Every building has one door nobody opens.",
              "Every building has one", "a faint electrical hum"),
             ("Extreme close-up of a worn brass door handle, hard side light, "
              "high detail, tension",
              "The handle turns very slowly.",
              "In this one, the room on the other side is bigger than the building.",
              "The room is bigger than the building", "a handle turning slowly"),
             ("A vast impossible interior seen through a doorway - cathedral scale, "
              "shafts of light, dust, cinematic",
              "Dust drifts through the shafts of light.",
              "Which is a problem, because somebody is already inside.",
              "Somebody is already inside", "a distant echo in a huge space"),
             ("A single small figure standing far away in the vast space, wide shot, "
              "silhouetted, cinematic",
              "The figure stands completely still. Dust drifts.",
              "", "", None),
         ]),
    dict(id="hook-signal", title="THE SIGNAL", hook="it repeats|every ninety seconds",
         cue="industrial_cold", voice=V_INFORM, style=STYLE_CINE, transition="flash",
         beats=[
             ("An enormous radio dish against a grey moorland sky, wide shot, cold "
              "light, industrial scale",
              "Cloud moves fast behind the dish. The dish holds still.",
              "This dish has pointed at the same patch of sky for forty years.",
              "Forty years, one patch of sky", "wind over open moorland"),
             ("A close-up of an oscilloscope screen with a repeating waveform, green on "
              "black, cool light, detail",
              "The waveform pulses steadily across the screen.",
              "Ninety seconds ago it heard something. It heard it again ninety seconds "
              "before that.",
              "Every ninety seconds", "a soft electronic pulse"),
             ("An empty control room at night with banks of instruments glowing, wide "
              "shot, nobody there, cinematic",
              "Indicator lights blink slowly across the desks.",
              "The building was decommissioned in the spring.",
              "The building is decommissioned", "an empty room, faint hum"),
             ("The dish silhouetted against a dark sky, low angle, single red light on "
              "the rim, ominous",
              "The red light blinks slowly. Cloud drifts.",
              "", "", None),
         ]),
    dict(id="hook-tide", title="LOW TIDE", hook="the sea went out|and did not come back",
         cue="desolate", voice=V_CALM, style=STYLE_CINE, transition="dissolve",
         beats=[
             ("A harbour at low tide with boats resting on wet mud, grey morning light, "
              "wide shot, still",
              "Water trickles in the channels. A boat settles slightly.",
              "The tide goes out twice a day. Everyone here knows the timing by heart.",
              "Twice a day, like clockwork", "gulls and dripping water"),
             ("A close-up of a stopped harbour clock, salt-corroded face, hard light, "
              "high detail",
              "The clock hands do not move. Light shifts across the face.",
              "On Tuesday it went out at nine. On Wednesday it did not come back.",
              "On Wednesday it did not come back", None),
             ("A vast expanse of exposed seabed stretching to the horizon, strange and "
              "wide, cold light, no water",
              "Mist drifts slowly across the seabed.",
              "There is a road down there. There was never a road down there.",
              "There is a road down there", "a low wind across open flats"),
             ("A distant figure walking out along the exposed seabed, tiny in the frame, "
              "wide shot, cinematic",
              "The figure walks slowly away into the mist.",
              "", "", None),
         ]),
    dict(id="hook-library", title="THE RETURN", hook="one book|came back late",
         cue="menace", voice=V_LOW, style=STYLE_CINE, transition="fade_black",
         beats=[
             ("A vast dim library interior with towering shelves, shafts of light, "
              "cinematic, no people",
              "Dust drifts through the light between the shelves.",
              "This library has four hundred thousand books. All of them are accounted "
              "for.",
              "All of them accounted for", "a huge quiet room, faint creaks"),
             ("A close-up of a date stamp card inside an old book cover, hard light, "
              "high detail, aged paper",
              "The card lifts very slightly.",
              "Except one, which was borrowed in 1954 and returned last Thursday.",
              "Borrowed 1954. Returned Thursday.", "a book closing softly"),
             ("An empty reading desk with a single old book on it under a lamp, warm "
              "pool of light, dark around, cinematic",
              "The lamp flickers. The pages settle.",
              "Nobody used a card. The desk was locked. The book is warm.",
              "The book is warm", None),
             ("The book alone on the desk in a dark room, close-up, single light, "
              "ominous stillness",
              "Very still. The light dims slightly.",
              "", "", None),
         ]),
    dict(id="hook-lift", title="FLOOR THIRTEEN", hook="the building has twelve|the lift has thirteen",
         cue="tense_strings", voice=V_INFORM, style=STYLE_CINE, transition="whip_pan",
         beats=[
             ("An old civic building lobby with terrazzo floors and brass fittings, "
              "wide shot, cold daylight, empty",
              "Light shifts slowly across the floor.",
              "This building has twelve floors. The plans say twelve. The windows count "
              "to twelve.",
              "Twelve floors. Count the windows.", "an empty lobby, distant footsteps"),
             ("Close-up of an old brass lift panel with numbered buttons, hard side "
              "light, aged metal, high detail",
              "A button lights up on its own.",
              "The lift has a button for thirteen.",
              "The lift has thirteen", "a lift button clicking"),
             ("The inside of an old open lift compartment moving past a floor landing, "
              "motion, warm interior light, cinematic",
              "The compartment rises slowly past the landing.",
              "It is not a mistake. People have pressed it.",
              "People have pressed it", "an old lift mechanism turning"),
             ("A dark landing lit by one bulb, seen from inside a rising lift, "
              "cinematic, unsettling",
              "The landing slides slowly out of view upward.",
              "", "", None),
         ]),
    dict(id="hook-garden", title="THE GARDEN", hook="it grew overnight|all of it",
         cue="unease", voice=V_WARM_F, style=STYLE_NATURE, transition="dissolve",
         beats=[
             ("A bare winter allotment with dark empty soil, grey morning light, wide "
              "shot, nothing growing",
              "Mist drifts low across the soil.",
              "On Monday there was nothing here but frost and dark soil.",
              "Monday: nothing but frost", "a cold morning, distant birds"),
             ("A close-up of a green shoot pushing through dark earth, macro, soft "
              "light, high detail",
              "The shoot rises very slowly through the soil.",
              "By Tuesday there were shoots. By Wednesday they were at the fence.",
              "Wednesday: at the fence", "soil shifting faintly"),
             ("A dense overgrown garden swallowing a shed, green and wild, soft light, "
              "slightly wrong scale",
              "Leaves move gently. Vines shift.",
              "It is Friday. The shed is gone.",
              "Friday: the shed is gone", "leaves rustling thickly"),
             ("A wall of dense green growth filling the frame, close-up, soft light, "
              "faintly ominous",
              "The leaves shift and settle, as if breathing.",
              "", "", None),
         ]),
]


def build(spec, kind):
    """Expand a spec into the film JSON short.py renders."""
    beats = []
    for i, b in enumerate(spec["beats"]):
        prompt, motion, line, caption, sfx = (list(b) + [None] * 5)[:5]
        beat = {
            "id": "%02d_%s" % (i + 1, ["open", "point", "detail", "turn", "land",
                                       "close", "extra", "extra2"][min(i, 7)]),
            "template": ("hook" if i == 0 else
                         "aftermath" if i == len(spec["beats"]) - 1 else "build"),
            "clip_secs": 5 if i == 0 else 4,
            "prompt": prompt,
            "motion": motion,
        }
        if caption:
            beat["caption"] = caption
        if line:
            beat["line"] = {"who": "V", "text": line}
            beat["audio_lead"] = -0.3
        if sfx:
            beat["sfx"] = sfx
            beat["sfx_secs"] = 3.0
            beat["sfx_level"] = 0.7
        # a transition only where the piece asked for one, and never on beat 1
        if i > 0 and spec.get("transition") and i % 2 == 1:
            beat["transition"] = spec["transition"]
        beats.append(beat)
    total = sum(b["clip_secs"] for b in beats)
    return {
        "title": spec["title"],
        "hook": spec["hook"],
        "canvas": CANVAS,
        "fps": FPS,
        "engine": "higgs_v3",
        "keyframe_engine": "qwen",
        "kind": kind,
        "style": spec["style"],
        "voices": {"V": {"engine": "higgs_v3", "voice": spec["voice"]}},
        "music": [{"at": 0, "prefix": "%s_score" % spec["id"].replace("-", "_"),
                   "bpm": 96, "key": "A minor", "seconds": max(30, total),
                   "level": 0.55, "cue": spec["cue"],
                   "tags": ""}],
        "beats": beats,
    }


def main():
    ap = argparse.ArgumentParser(description="Write the 20 short-form film JSONs.")
    ap.add_argument("--write", default=os.path.join(ROOT, "films", "shorts"))
    a = ap.parse_args()
    os.makedirs(a.write, exist_ok=True)
    sys.path.insert(0, STUDIO)
    import cards
    cues = cards.load("cues")
    n = 0
    for group, kind in ((SUPPLEMENTS, "supplement"), (COMMERCIALS, "commercial"),
                        (HOOKS, "hook")):
        for spec in group:
            film = build(spec, kind)
            # the cue card supplies the real music tags/bpm/key - the library is the
            # source of truth, the spec only names which cue it wants
            c = cues.get(spec["cue"]) or {}
            m = film["music"][0]
            m["tags"] = c.get("tags", "cinematic underscore, instrumental")
            try:
                m["bpm"] = int(float(c.get("bpm") or 96))
            except ValueError:
                pass
            m["key"] = c.get("key") or "A minor"
            m.pop("cue", None)
            p = os.path.join(a.write, "%s.json" % spec["id"])
            with open(p, "w", encoding="utf-8") as f:
                json.dump(film, f, indent=2, ensure_ascii=False)
                f.write("\n")
            n += 1
            print("%-22s %-11s %d beats, %ds" % (spec["id"], kind, len(film["beats"]),
                                                 sum(b["clip_secs"] for b in film["beats"])))
    print("\n%d films written to %s" % (n, a.write))
    return 0


if __name__ == "__main__":
    sys.exit(main())
