#!/usr/bin/env python3
"""THE CYBER-ALCHEMIST'S DESCENT (2026-09-30) - the "even harder" test: one character in layered
velvet, brass and leather held through a 360-degree orbit, a mercury shatter in zero gravity, a
first-person helmet view down a shaft, a free fall down a city canyon and a jetpack landing. ~3 min.

What the brief's own hints assume (SVD-XT, CogVideoX, AnimateDiff, TemporalNet, IP-Adapter weights)
is not on this box; what it asks for underneath - image-to-video only, the character drawn first and
held by her picture - is how this pipeline already works, with newer parts:

  the ORBIT       built, not asked for: the whole 360-degree move rendered once in Blender around a
                  stand-in figure (coat, cape, braid, jetpack) in a room laid out like the master
                  (previz_blender.py --scene orbit), cut into eight 45-degree pieces, each painted by
                  LTX-2.3 with the IC-LoRA union control reading the piece's depth and starting on the
                  last frame of the piece before (previz_chain.py). Turning the master with the angles
                  LoRA and rendering between the keys (flf_shots.py keys) was tried first: both engines
                  cross-faded the room, because every key invents the room again.
  THE DOLLY ZOOM  previz too (--scene canyon): the lens widens as the camera closes in, her size held
                  constant, the canyon's lines stretching behind her.
  UP TO HER FACE  previz (--scene street), drawn as a move DOWN from the first frame of the close-up that
                  follows it (311, her face composed from her references) and played backwards ("reverse"):
                  the rise from her boots lands exactly on that frame, so the face it ends on is hers.
  CAMERA MOVES    the tilt from her eye to her hands, from the railing up the shaft, from her boots to
                  her face: the same, between two composed start frames ("engine": "key" shots exist
                  only to draw those end frames; they have no takes and the finish skips them)
  IDENTITY        her reference and her character sheet (sheet_refs.py): the back view for every shot
                  from behind, the three-quarter face for every close-up; the helmet has its own
                  reference so it is the same helmet in every shot it is in
  EFFECTS         shatter, zero-g mercury, whipping cloth, splashes: rendered on H3 as well as LTX-2.5

Ids come from position within each phase (101.. 201.. 301..); a "key" shot is named after the shot
that ends on it (112e). Symbolic references ("@eye") become anchor_<id>.png after numbering.
"""
import json
import os

ROOT = os.path.expanduser("~/shared/comfy-studio")
DST = os.path.join(ROOT, "studio", "shotscripts")

REAL = ("Unretouched photograph, available light, visible skin texture and pores, fine film grain, "
        "shallow depth of field, no retouching, no gloss.")
AVOID = ("lowres, blurry, deformed limbs, fused fingers, extra fingers, extra limbs, doubled figure, "
         "two of the same person, melting face, morphing, warping, clothes melting into skin, text, "
         "subtitles, captions, watermark, nsfw")
NOBODY = "people, a person, a figure, a crowd, a face, hands"

G_WORK = ("Cinematic film, a dark stone workshop at night, Rembrandt lighting from one warm key with deep "
          "shadows, neon blue tubes, haze and drifting smoke, hyper-detailed textures, 35mm film grain, anamorphic.")
G_SHAFT = ("Cinematic film, a colossal dark elevator shaft, cold blue work lights receding into blackness, "
           "haze, high contrast, 35mm film grain, anamorphic.")
G_CITY = ("Cinematic film, night, a narrow cyberpunk city canyon, streaking neon in magenta and cyan, rain, "
          "motion blur, high contrast, 35mm film grain, anamorphic.")
G_STREET = ("Cinematic film, night, a wet asphalt street at the bottom of a city canyon, neon reflections in "
            "puddles, blue jet light, steam, 35mm film grain, anamorphic.")


def still(framing, body, grade):
    return "A still frame from a live-action film, %s %s %s" % (framing, body, grade)


def shot(phase, name, title, secs, refs, anchor, prompt, engine="ltx", face="none", **kw):
    d = {"id": str(phase), "name": name, "title": title, "secs": secs, "refs": refs, "engine": engine,
         "face": face, "anchor": anchor, "prompt": prompt}
    d.update(kw)
    return d


GLB = "studio/sheets/the-cyber-alchemist-s-descent-alch/model.glb"      # her shape, from her character sheet

ORBIT_WORDS = ("A slow, steady camera orbit all the way around a woman standing perfectly still in a dark stone "
               "alchemist's workshop at night: a crimson velvet coat over a brass corset, mechanical leather "
               "gauntlets with glowing blue wires, a patched dark cape hanging from her right shoulder, a long dark "
               "braid, a compact brass jetpack of two tanks strapped to her back. The camera circles her at an even "
               "pace. Neon blue tubes on the stone piers all around the room rim-light her from every side, so from "
               "behind the velvet, the patched cape, the braid and the brass jetpack stay clearly visible; the warm "
               "lamp on the workbench stays where it is. Around the room: a wooden workbench of glassware, tall "
               "wooden shelves of old books and jars against the far wall, wooden barrels in the corners, a small "
               "table with a candle lantern, a steel railing at the edge of a dark shaft, smoke drifting. Low hum, "
               "her slow breath. No music.")

cast = {
    "alch": {"role": "the alchemist", "prompt": (
        "Full-length reference photograph of a woman of about thirty against a plain mid-grey backdrop, even soft "
        "light, standing still, facing the camera, arms at her sides. A cyber-alchemist with a strong, striking face, "
        "a glowing silver cybernetic iris in her left eye, long dark hair in one thick braid over her right shoulder. "
        "She wears a heavily textured crimson velvet coat, open, over a complex brass steampunk corset of riveted "
        "plates and small gears; intricate mechanical leather gauntlets up to the elbows with brass gears, visible "
        "stitching and thin glowing blue wires running along them; a dynamic asymmetric cape of patched dark fabrics "
        "hanging from her left shoulder; a compact folded brass jetpack strapped to her back; dark leather trousers "
        "and heavy buckled boots. " + REAL)},
    "alch_back": {"role": "the alchemist from behind", "sheet_view": ["alch", "turn_back"],
                  "prompt": "The back view from the alchemist's character sheet."},
    "alch_face": {"role": "the alchemist's face", "sheet_view": ["alch", "face_front_r"],
                  "prompt": "The three-quarter face from the alchemist's character sheet."},
    "helmet": {"role": "her helmet", "prompt": (
        "Reference photograph of a single object against a plain mid-grey backdrop, even soft light: a round "
        "brass mechanical helmet with riveted plates and small gears at the temples, its whole front one large "
        "curved clear glass visor like a diving helmet's faceplate, so the inside of the helmet shows through "
        "it, a faint glowing blue heads-up display of thin lines and small readouts projected on the inside of "
        "the glass, empty, standing on its own, the whole helmet in frame, three-quarter view. "
        "Unretouched photograph, available light, fine film grain, shallow depth of field, no gloss.")},
    "shaft": {"role": "the shaft (a second place)", "place": True, "prompt": (
        "Wide photograph looking straight down a colossal vertical elevator shaft inside a megastructure, nobody in "
        "it: steel walls ribbed with girders and cables, rows of cold blue work lights receding down into total "
        "darkness, a steel railing edge in the foreground. Deep perspective, anamorphic. " + REAL)},
    "canyon": {"role": "the city canyon (a third place)", "place": True, "prompt": (
        "Wide photograph looking straight down a narrow cyberpunk city canyon at night from high above, nobody in "
        "it: sheer towers on both sides covered in neon signs in magenta and cyan, rain falling, sky bridges and "
        "cables crossing, the glowing street far below. Deep perspective, anamorphic. " + REAL)},
    "street": {"role": "the street (a fourth place)", "place": True, "prompt": (
        "Wide photograph of a narrow wet asphalt street at the bottom of a cyberpunk city canyon at night, nobody in "
        "it: deep puddles reflecting magenta and cyan neon, steam rising from grates, towers climbing out of frame. "
        "Low angle, deep perspective, anamorphic. " + REAL)},
}

shots = [
    # ======================================================== PHASE 1: the wardrobe and the orbit
    shot(1, "workshop", "the workshop", 5, ["workshop"], None,
         "Smoke drifts slowly through the dark stone workshop; the neon blue tubes hum and flicker; the warm lamp throws "
         "hard light and deep shadow across the bench of glass and brass; beyond the railing the shaft is black. Nobody "
         "is here. The camera pushes slowly in. Room tone, a low electrical hum, bubbling glass, a distant mechanical "
         "groan from the shaft. No music.", avoid_extra=NOBODY),
    shot(1, "master", "the master", 4, ["alch", "alch", "workshop"],
         still("a MEDIUM SHOT", "of the woman of reference one standing in the dark stone workshop of reference three "
               "beside the workbench, facing the camera, a single warm key light from her right in Rembrandt style "
               "casting deep shadow across the other half of her face, her crimson velvet coat, brass corset and "
               "glowing blue gauntlets catching the light, neon blue tubes behind her, smoke drifting.", G_WORK),
         "She stands completely still, breathing slowly; only the smoke moves around her and the blue wires on her "
         "gauntlets pulse faintly. The camera is locked off, perfectly still. Low hum, her slow breath, bubbling "
         "glass. No music.", face="medium"),
] + [
    shot(1, "orbit%d" % i, "the orbit, %d of 8" % i, 4, ["workshop"], None, ORBIT_WORDS, engine="previz",
         **({"previz": {"scene": "orbit", "chain": "103-110", "degrees": 360, "radius": 3.3, "lens": 42,
                        "cam_z": 1.45, "look_z": 1.25,
                        "figure_glb": GLB}} if i == 1 else {}))
    for i in range(1, 9)
] + [
    shot(1, "eye", "the iris", 4, ["alch_face", "alch", "workshop"],
         still("an EXTREME MACRO CLOSE-UP", "of the left eye of the woman of reference one in the dark stone workshop "
               "of reference three: a glowing silver cybernetic iris with fine mechanical rings, the pupil adjusting, "
               "individual lashes and skin pores in hard Rembrandt light, smoke drifting across.", G_WORK),
         "The silver cybernetic iris rotates and refocuses, its fine rings turning with a faint whir; she blinks once; "
         "smoke drifts across the lens. Macro lens, static. A tiny mechanical whir, her breath. No music.", face="close"),
    shot(1, "tilt_hands", "down to the hands", 3, ["workshop"], None,
         "The camera tilts smoothly down from her eye, past the collar of the crimson velvet coat and the brass corset, "
         "to her gloved hands at the workbench as they pick up a small glass vial of liquid mercury. Smoke drifts. "
         "A soft whir, the clink of glass. No music.", engine="flf", flf={"first": "end:shot_111_s11.mp4", "last": "@hands"}),
    shot(1, "hands", "(end frame: the hands)", 4, ["alch", "alch", "workshop"],
         still("an EXTREME MACRO CLOSE-UP", "of the hands of the woman of reference one at the workbench of the stone "
               "workshop of reference three: her intricate mechanical leather gauntlets with visible stitching, small "
               "brass gears at the knuckles and thin glowing blue wires, the fingers closing around a small glass vial "
               "of liquid mercury, smoke drifting across.", G_WORK), "", engine="key", key_for="tilt_hands"),
    shot(1, "gauntlet", "the gauntlet", 4, ["alch", "alch", "workshop"],
         still("an EXTREME MACRO CLOSE-UP", "of the right mechanical leather gauntlet of the woman of reference one "
               "holding a glass vial of liquid mercury at the workbench of the stone workshop of reference three: the "
               "leather creasing at the knuckles, the stitching, the small brass gears and the glowing blue wires "
               "bending with her fingers.", G_WORK),
         "Her fingers flex around the vial; the leather creases and the tiny brass gears at the knuckles turn; the "
         "blue wires brighten as they bend; smoke drifts across the frame. Macro lens, a slow tracking move. Leather "
         "creaking, tiny gears ticking. No music.", engine="both"),
    shot(1, "mercury", "mercury", 4, ["alch", "alch", "workshop"],
         still("a CLOSE-UP", "of the woman of reference one in the stone workshop of reference three holding a small "
               "glass vial of liquid mercury up at eye level, the silver liquid rolling heavily inside the glass and "
               "reflecting the neon blue light, her silver iris reflected in it.", G_WORK),
         "She tilts the vial slowly and the mercury rolls inside the glass like a heavy mirror, reflecting the neon "
         "blue light; she watches it intently. Static camera. Glass tinkling, a low hum. No music.", face="close"),
    # ======================================================== PHASE 2: the physics break and the POV switch
    shot(2, "slip", "it slips", 4, ["alch", "alch", "workshop"],
         still("an EXTREME CLOSE-UP", "of the gloved mechanical fingers of the woman of reference one in the stone "
               "workshop of reference three, a small glass vial of mercury slipping out of them, the blue wires "
               "flaring.", G_WORK),
         "The vial slips out of her gloved fingers and drops out of the bottom of the frame; her fingers snap closed a "
         "moment too late. Static camera. A sharp intake of breath. No music."),
    shot(2, "shatter", "the shatter", 5, ["workshop", "workshop", "workshop"],
         still("a HIGH-SPEED SLOW-MOTION CLOSE SHOT", "at floor level on the stone floor of the workshop of reference "
               "one: a small glass vial of liquid mercury just touching the stone as it begins to shatter, neon blue "
               "light reflected in the glass.", G_WORK),
         "In extreme slow motion, a thousand frames a second, the vial hits the stone floor and the glass bursts into "
         "glittering shards; the mercury flies out in heavy silver beads. The camera is locked at floor level. A "
         "slowed crystalline crack, a deep low boom. No music.", engine="both", avoid_extra=NOBODY),
    shot(2, "zero_g", "zero gravity", 5, ["workshop", "workshop", "workshop"],
         still("a HIGH-SPEED SLOW-MOTION CLOSE SHOT", "above the stone floor of the workshop of reference one: beads of "
               "liquid mercury rising upward off the floor into the air like weightless silver droplets, broken glass "
               "hanging among them, every droplet refracting the neon blue light.", G_WORK),
         "The mercury rises upward off the floor in zero gravity, splitting into trembling silver droplets that hang "
         "and turn in the air, each one bending the blue neon light like a lens; shards of glass drift up among them. "
         "Slow motion, the camera drifting slowly upward with them. A deep hum, a crystalline shimmer. No music.",
         engine="both", avoid_extra=NOBODY),
    shot(2, "shockwave", "the shockwave", 5, ["alch", "alch", "workshop"],
         still("a WIDE SHOT", "of the woman of reference one standing in the stone workshop of reference three as a "
               "shockwave of reversed gravity ripples outward from the floor: her crimson velvet coat tails and her "
               "patched cape billowing up above her, silver droplets of mercury floating all around her, smoke "
               "swirling upward.", G_WORK),
         "A pulse of reversed gravity ripples out from the floor: her coat tails and patched cape lift and billow "
         "upward, silver droplets and loose papers float up around her, her braid rises off her shoulder; she spreads "
         "her arms to keep her balance. Slow motion, static camera. A deep thrum, fabric snapping, glass tinkling. "
         "No music.", engine="both", face="medium"),
    shot(2, "floating", "everything floats", 5, ["alch", "alch", "workshop"],
         still("a WIDE HIGH SHOT", "of the whole stone workshop of reference three with everything floating: glass "
               "alembics, books, brass tools and droplets of mercury drifting up off the bench toward the vaulted "
               "ceiling, and the woman of reference one standing among them, small in the middle of the room.", G_WORK),
         "Everything in the workshop drifts slowly upward: books turning over, glass alembics tumbling, silver droplets "
         "rising toward the vaulted ceiling; she turns slowly on the spot, watching it go. The camera cranes slowly "
         "up. Glass clinking softly, pages fluttering, a deep hum. No music.", engine="both", face="wide"),
    shot(2, "iris_up", "the iris, looking up", 4, ["alch_face", "alch", "workshop"],
         still("a CLOSE-UP", "of the woman of reference one in the stone workshop of reference three looking up in "
               "astonishment at silver droplets of mercury floating in the air above her, her silver cybernetic iris "
               "glowing brighter, the droplets reflected in it.", G_WORK),
         "She looks up at the floating mercury; her silver iris whirs and glows brighter as it focuses; a droplet "
         "drifts past her face. Static camera, close. A soft whir, a deep hum. No music.", face="close"),
    shot(2, "helmet_on", "the helmet", 5, ["alch", "helmet", "workshop"],
         still("a MEDIUM SHOT", "of the woman of reference one in the stone workshop of reference three lifting the "
               "round brass mechanical helmet of reference two with both gloved hands, about to lower it over her head, "
               "floating droplets of mercury around her.", G_WORK),
         "She lowers the brass helmet over her head and it seals with a hiss; the curved glass visor slides down and a "
         "faint blue display flickers on inside it. Static camera. A mechanical clunk, a hiss of air, a rising "
         "electronic chime. No music.", face="medium"),
    shot(2, "hud", "inside the helmet", 4, ["alch", "alch", "workshop"],
         still("a FIRST-PERSON POINT-OF-VIEW SHOT", "from inside a brass mechanical helmet looking out through its "
               "curved glass visor at the dark stone workshop of reference three: the rim of the helmet framing the view, "
               "a glowing blue heads-up display across the glass with targeting lines, readouts and a gravity warning, "
               "the display glitching with digital static, droplets of mercury floating beyond; the gloved hands of the "
               "woman of reference one at the bottom of the frame.", G_WORK),
         "First-person view from inside the helmet: the blue heads-up display boots up across the visor, flickers and "
         "glitches with bursts of digital static and scanlines, then steadies; the view sways as she breathes. "
         "Handheld. Her breath loud inside the helmet, electronic chirps, static crackle. No music."),
    shot(2, "railing", "the railing", 4, ["shaft", "alch", "alch"],
         still("a FIRST-PERSON POINT-OF-VIEW SHOT", "from inside a brass mechanical helmet looking down through its "
               "curved glass visor, a glitching blue heads-up display across the glass: two hands in intricate "
               "mechanical leather gauntlets with glowing blue wires gripping a steel railing at the edge of the "
               "colossal shaft of reference one, as worn by the woman of reference two.", G_SHAFT),
         "First-person view: her gauntleted hands grip the steel railing and tighten; the heads-up display glitches "
         "with static; the view shakes. Handheld, chaotic. Her breath inside the helmet, metal creaking, static. "
         "No music."),
    shot(2, "tilt_shaft", "the shaft", 5, ["shaft"], None,
         "First-person view: the camera tilts rapidly up from her hands on the railing to face the colossal vertical "
         "shaft, its rows of blue lights plunging down into darkness; the view shakes and blurs with the speed of the "
         "move; the display flickers. Handheld, chaotic, natural motion blur. Her breath, a deep wind moaning up the "
         "shaft. No music.", engine="flf", flf={"first": "end:shot_209_s11.mp4", "last": "@shaft_view"}),
    shot(2, "shaft_view", "(end frame: the shaft)", 4, ["shaft", "shaft", "shaft"],
         still("a FIRST-PERSON POINT-OF-VIEW SHOT", "from inside a brass mechanical helmet looking out and down into the "
               "colossal vertical shaft of reference one, rows of cold blue lights plunging away into total darkness, a "
               "glitching blue heads-up display across the visor glass.", G_SHAFT), "", engine="key",
         key_for="tilt_shaft"),
    shot(2, "over", "over the rail", 4, ["shaft", "alch_back", "helmet"],
         still("a MEDIUM SHOT", "from behind the woman of reference two, wearing the round brass helmet of reference "
               "three, climbing over the steel railing at the edge of the colossal shaft of reference one, her crimson "
               "coat and patched cape hanging over the drop, blue lights falling away below.", G_SHAFT),
         "She swings one leg over the railing and then the other, and stands on the edge with her back to us, holding "
         "the rail behind her; wind rushes up and lifts her cape. Static camera. Wind moaning up the shaft, metal "
         "creaking. No music."),
    shot(2, "drop", "the drop", 4, ["shaft", "alch_back", "helmet"],
         still("a HIGH ANGLE SHOT", "looking down the colossal shaft of reference one past the woman of reference two, "
               "wearing the brass helmet of reference three, as she lets go of the railing and falls forward into the "
               "dark, her coat and cape streaming up.", G_SHAFT),
         "She lets go and falls forward into the shaft; the camera tips down after her as she drops away into the rows "
         "of blue light, her coat and cape streaming upward. Wind roaring. No music.", engine="both"),
    # ======================================================== PHASE 3: the fall and the landing
    shot(3, "freefall", "free fall", 5, ["canyon", "alch_back", "helmet"],
         still("a HIGH-VELOCITY FPV DRONE SHOT", "looking straight down the narrow cyberpunk city canyon of reference "
               "one from just behind and above the woman of reference two, wearing the brass helmet of reference three, "
               "free-falling head first toward the neon street far below, her crimson velvet coat, long braid and "
               "patched cape whipping upward in the wind.", G_CITY),
         "She plunges head first down the canyon and the camera dives right behind her at the same speed; her coat, "
         "braid and patched cape whip and snap violently in the wind; neon signs streak past on both sides into long "
         "bright trails. Roaring wind, the rush of air. No music.", engine="both"),
    shot(3, "whip", "whipping", 4, ["canyon", "alch", "helmet"],
         still("a CLOSE TRACKING SHOT", "beside the woman of reference two falling through the narrow neon city canyon "
               "of reference one, wearing the brass helmet of reference three: the crimson velvet coat, the long braid "
               "and the patched cape whipping violently in the wind against her mechanical gauntlets, neon streaking "
               "past.", G_CITY),
         "The fabric whips and hammers in the wind: velvet coat tails, the patched cape and her long braid snapping "
         "violently, the edges staying sharp; her gauntlets glow blue; neon smears past behind her. The camera falls "
         "alongside her. Deafening wind, flapping fabric. No music.", engine="both"),
    shot(3, "below", "from below", 4, ["canyon", "alch", "helmet"],
         still("a LOW ANGLE SHOT", "looking straight up the narrow neon city canyon of reference one as the woman of "
               "reference two, wearing the brass helmet of reference three, plunges head first down toward the camera, "
               "her coat and cape streaming above her against the neon.", G_CITY),
         "She hurtles down toward the camera out of the neon canyon, growing fast, coat and cape streaming; rain streaks "
         "past the lens. Static camera looking straight up. A rising roar of wind. No music.", engine="both"),
    shot(3, "streaks", "the city streaks", 4, ["canyon", "canyon", "canyon"],
         still("a FIRST-PERSON FALLING SHOT", "straight down the narrow cyberpunk city canyon of reference one at "
               "terrifying speed, neon signs stretching into long streaks, the street rushing up.", G_CITY),
         "First-person view diving straight down the canyon; the neon signs stretch into long streaks of magenta and "
         "cyan and the street rushes up; rain streaks past. A roaring rush of air. No music.", avoid_extra=NOBODY),
    shot(3, "visor", "her face", 4, ["canyon", "alch_face", "helmet"],
         still("a CLOSE-UP", "of the face of the woman of reference two seen through the curved glass visor of the "
               "brass helmet of reference three as she free-falls down the neon city canyon of reference one, the blue "
               "display glowing on the glass, her silver iris bright, neon streaking behind.", G_CITY),
         "Wind hammers the helmet as she falls; behind the visor her eyes are fierce and steady, her silver iris "
         "glowing; neon streaks past in the glass. The camera falls with her, close. Roaring wind, her breath. "
         "No music.", face="close"),
    shot(3, "jetpack", "the jetpack", 4, ["canyon", "alch_back", "helmet"],
         still("a CLOSE SHOT", "from behind the woman of reference two, wearing the brass helmet of reference three, "
               "falling down the neon city canyon of reference one as the compact brass jetpack on her back unfolds, "
               "its nozzles opening.", G_CITY),
         "She pulls a cord at her chest and the brass jetpack on her back unfolds with a mechanical clatter, its "
         "nozzles swinging open and igniting in bright blue flame. The camera falls with her. A clatter of metal, then "
         "a roaring ignition. No music.", engine="both"),
    shot(3, "vertigo", "vertigo", 5, ["canyon", "alch", "helmet"],
         still("a TRACKING SHOT", "of the woman of reference two, wearing the brass helmet of reference three, in the "
               "neon city canyon of reference one, her jetpack firing bright blue flames as she brakes in mid-air, her "
               "coat and cape flung upward.", G_CITY),
         "Reverse dolly zoom: she stays the same size in the centre of the frame while the canyon around her seems to "
         "stretch and tunnel away, as the jetpack roars bright blue and she brakes hard in mid-air, her coat and cape "
         "flung upward. A vertigo effect. The roar of the jets, the wind dropping. No music.", engine="previz",
         previz={"scene": "canyon", "seconds": 5, "radius": 14.0, "radius_to": 3.5, "lens": 100, "lens_to": 25,
                 "cam_z": 1.1, "look_z": 1.1, "figure_glb": GLB, "grade": G_CITY, "dress": (
                     "Turn <image1> into a still frame from a live-action film. Keep the camera, the perspective and "
                     "the layout of <image1> exactly. The grey figure is the woman of <image3> wearing the brass helmet "
                     "of <image4>, hovering upright in mid-air in exactly that place and at that size, facing the "
                     "camera, a brass jetpack on her back firing two bright blue flames downward, her crimson coat and "
                     "patched cape blown upward. The grey towers are the towers of the narrow neon city canyon of "
                     "<image2>, covered in magenta and cyan neon signs, rain falling, the street glowing far below.")}),

    shot(3, "descent", "descent", 4, ["street", "alch", "helmet"],
         still("a WIDE AERIAL SHOT", "looking down into the narrow wet street of reference one from above: the woman of "
               "reference two, wearing the brass helmet of reference three, descending slowly on two bright blue jets, "
               "the downdraft blowing the puddles into rings.", G_STREET),
         "She descends slowly on the blue jets toward the wet street; the downdraft ripples the puddles and blows the "
         "steam aside; the camera cranes down with her. The jets roaring and slowing. No music."),
    shot(3, "touchdown", "touchdown", 4, ["street", "alch", "helmet"],
         still("a LOW-ANGLE GROUND SHOT", "at puddle level on the wet asphalt street of reference one: the heavy buckled "
               "boots of the woman of reference two touching down in a deep puddle reflecting the neon, blue jet flames "
               "just above, spray starting to fly outward.", G_STREET),
         "Her boots hit the wet asphalt and the puddle explodes outward in a ring of neon-lit spray; the jets cut out "
         "with a sigh; steam curls around her boots. Low camera, tracking. A heavy splash, the jets dying. No music.",
         engine="both"),
    shot(3, "tilt_face", "up to her face", 5, ["street", "alch", "helmet"], None,
         "The camera sinks smoothly from her face, past the brass corset and the crimson velvet coat hanging open over "
         "her dark leather trousers, past the glowing gauntlets, down to her heavy buckled leather boots standing in a "
         "shallow puddle on the wet asphalt, drawing back a little as it goes. She is fully dressed: dark leather "
         "trousers, the long crimson velvet coat, heavy boots. She stands completely still, breathing slowly; steam "
         "drifts slowly sideways past her; neon shimmers in the puddle. The low hum of the city, the tick of the "
         "cooling jetpack. No music.", engine="previz",
         avoid_extra="bare legs, bare thighs, underwear, briefs, lingerie, shorts, skirt",
         previz={"scene": "street", "seconds": 5, "radius": 1.0, "radius_to": 1.4, "lens": 35, "lens_to": 24,
                 "cam_z": 1.58, "cam_z_to": 0.22, "look_z": 1.47, "look_z_to": 0.12, "figure_turn": 35,
                 "reverse": True, "figure_glb": GLB, "start": "anchor_311.png"}),
    shot(3, "standing", "(end frame: standing)", 4, ["street", "alch", "helmet"],
         still("a LOW-ANGLE SHOT", "looking up at the woman of reference two standing on the wet neon street of reference "
               "one, the brass helmet of reference three held under one arm, her face bare, her long braid over her "
               "shoulder, her silver iris glowing, steam around her.", G_STREET), "", engine="key", key_for="tilt_face"),
    shot(3, "her", "her", 5, ["alch_face", "alch", "street"],
         still("a CLOSE-UP", "of the face of the woman of reference one standing on the wet neon street of reference "
               "three, her silver cybernetic iris glowing, rain on her skin, her crimson velvet collar and a glowing "
               "gauntlet at the edge of the frame.", G_STREET),
         "She looks up the canyon she fell down, breathing hard, then lowers her gaze to the camera; a slow, satisfied "
         "smile. Static camera, close. Rain, distant sirens, the hiss of the cooling jetpack. No music.", face="close"),
    shot(3, "street_end", "the street", 5, ["street", "alch", "helmet"],
         still("a WIDE SHOT", "of the wet neon street of reference one, the woman of reference two standing in the middle "
               "of it with the brass helmet of reference three under her arm, steam rising, neon reflected in the "
               "puddles around her, the towers climbing out of frame.", G_STREET),
         "She stands in the middle of the street as steam drifts past and the neon flickers in the puddles; she turns "
         "and walks away into the haze. The camera pulls back slowly. Rain, steam, a distant city. No music.",
         face="wide"),
]


def number(shots):
    """Ids by position within each phase; key shots take the id of the shot they end plus 'e'; '@name' in
    a flf spec becomes that shot's anchor file."""
    seen, ids = {}, {}
    for x in shots:
        if x["engine"] == "key":
            continue
        ph = x["id"]
        seen[ph] = seen.get(ph, 0) + 1
        x["id"] = "%s%02d" % (ph, seen[ph])
        ids[x["name"]] = x["id"]
    for x in shots:
        if x["engine"] == "key":
            x["id"] = ids[x["key_for"]] + "e"
            ids[x["name"]] = x["id"]
    for x in shots:
        for end in ("first", "last"):
            v = (x.get("flf") or {}).get(end)
            if v and v.startswith("@"):
                x["flf"][end] = "anchor_%s.png" % ids[v[1:]]
    return shots


film = {
    "_comment": "The 'even harder' test (2026-09-30): one character in layered velvet, brass and leather held through a "
                "built 360-degree orbit, zero-g mercury, a helmet POV, a free fall and a jetpack landing.",
    "film": "cyber-alchemist", "title": "THE CYBER-ALCHEMIST'S DESCENT",
    "logline": "An alchemist breaks gravity with a drop of mercury, and follows it down.",
    "grade": G_WORK, "avoid": AVOID, "realism": REAL,
    "score_tags": ("dark cinematic score, deep brass drones, ticking mechanical percussion, eerie glass harmonics, "
                   "slow build of tension, low strings, instrumental, no vocals"),
    "score_tags_b": ("epic cinematic score, pounding drums, soaring strings and synth, a vast rush of speed, then a "
                     "triumphant landing and a quiet resolution, instrumental, no vocals"),
    "place": {"id": "workshop", "prompt": (
        "Wide photograph of a dark alchemist's workshop carved from stone at night, nobody in it: rough stone walls and a "
        "vaulted ceiling, a long workbench crowded with glass alembics, brass apparatus and small glass vials of liquid "
        "mercury, neon blue tubes along the walls, a single warm lamp casting hard Rembrandt light, drifting smoke, and "
        "at the far side a steel railing at the edge of a vast dark vertical shaft. Deep perspective, anamorphic. "
        + REAL)},
    "cast": cast,
    "shots": number(shots),
}

if __name__ == "__main__":
    p = os.path.join(DST, film["film"] + ".json")
    if os.path.exists(p):
        raise SystemExit("keeping %s (it exists - delete it to rewrite)" % p)
    json.dump(film, open(p, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    real = [x for x in film["shots"] if x["engine"] != "key"]
    print("%s: %d shots (+%d end frames), %d s -> %s" % (film["film"], len(real), len(film["shots"]) - len(real),
                                                        sum(x["secs"] for x in real), p))
