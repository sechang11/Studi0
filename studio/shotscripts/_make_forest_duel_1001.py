#!/usr/bin/env python3
"""THE DUEL IN THE CLEARING (2026-10-01): Terra and the jester fight it out in a clearing of the forest set.

Frames first (playbook §99.10): every shot is a camera in the clearing (studio/_tools/set_duel.py) with
where each of them stands and faces at its first and last frames, and what the physics breaks during it;
set_test.py cast puts them into those two frames from their sheets, and H3 acts between the frames. The
choreography of each beat is in its words - a beat list with the body mechanics and the effect of every
hit (fight_words.py measured how deep that has to go). The physics carries over the cuts: every event of
an earlier shot is re-simulated and frozen where it came to rest (set_duel.act "done").

Writes studio/shotscripts/forest-duel.json and forest-duel.acts.json.
    python3 studio/shotscripts/_make_forest_duel_1001.py [--style shon|wux] [--force]
"""
import argparse
import json
import os

ROOT = os.path.expanduser("~/shared/comfy-studio")
DST = os.path.join(ROOT, "studio", "shotscripts")
FILM = "forest-duel"

GRADE = ("2D anime film, hand-drawn cel animation, painted backgrounds, a forest clearing at dusk, shafts of low "
         "sunlight, drifting mist.")
AVOID = ("lowres, blurry, morphing, warping, melting, flicker, deformed hands, extra fingers, extra limbs, two of the "
         "same person, subtitles, captions, watermark, nsfw")
OTHERS = "3d render, cgi, photorealistic, live action, a crowd, other people, blood, gore"
HER = "the young woman with long wavy sea-green hair, a red dress and red boots"
HIM = "the lanky harlequin jester in a purple-and-yellow diamond costume and two-horned cap"
DRESS = ("Turn <image1> into a frame from a hand-drawn 2D anime film: a forest clearing ringed by huge dark trees "
         "and old standing stones, painted as an anime background, clean line art, flat cel shading, shafts of late "
         "sunlight falling into the clearing, drifting mist at its edges. Keep the camera, the lens, the framing, "
         "the perspective and the layout of <image1> exactly: everything in it stays exactly where it is, at the "
         "same size, with the same colours; add nothing and remove nothing.")
STYLES = {
    "shon": "A fight in the manner of a 90s shonen battle anime - glowing auras, speed lines, afterimages, a white "
            "impact frame on every hit. ",
    "wux": "A fight in the manner of a classic wuxia film - graceful, wire-assisted movement, flowing hair and "
           "fabric, poised stances. ",
}
STAY = " The clearing, the trees, the standing stones and the light stay exactly as they are."
QUIET = {"D01", "E01", "E08", "G01", "G02", "G02b", "G03", "G04", "G05", "G06"}

# marks: where each of them stands (x, y) and what they face, at a shot's first and last frames
J0, J1, J2, J3, J4 = (3.0, 33.0), (-0.6, 34.2), (0.1, 28.8), (-4.4, 29.4), (-2.0, 32.4)
T0, T1, T2, T3, T4, T5 = (0.9, 20.0), (-0.8, 24.2), (0.8, 25.4), (0.6, 27.4), (0.2, 27.9), (1.6, 25.2)


def m(at, to=None, hidden=False):
    return {"hidden": True} if hidden else {"at": list(at), "to": list(to)}


def both(t0, t1, j0, j1, t_hidden=False, j_end_hidden=False, j_hidden=False):
    return {"terra": {"start": m(t0, j0, t_hidden), "end": m(t1, j1, t_hidden)},
            "jester": {"start": m(j0, t0, j_hidden), "end": m(j1, t1, j_hidden or j_end_hidden)}}


# id, name, frames, camera, the beat (words), sound, figures, live physics
SHOTS = [
    ("D01", "into the clearing", 73,
     {"cam": [2.6, 15.5, 1.2], "cam_to": [2.3, 16.8, 1.2], "look": [0.6, 30.0, 1.8], "look_to": [0.6, 30.0, 1.7], "lens": 26},
     "Wide and low, behind %s: she walks into a clearing ringed by standing stones; across it %s waits, juggling "
     "three glowing purple orbs; a gust tears leaves from the canopy and they swirl down between them. The camera "
     "pushes in slowly." % (HER, HIM),
     "wind, rustling leaves, the hum of the orbs, his soft giggle",
     both(T0, T1, J0, J0), [{"ev": "leafrain", "at": [0.8, 28.5], "f": 14, "n": 60, "radius": 7.0}]),
    ("D02", "the orbs", 73,
     {"cam": [1.5, 27.6, 1.55], "cam_to": [1.6, 28.4, 1.55], "look": [3.0, 33.0, 1.75], "lens": 45},
     "Closer on %s: he juggles three glowing purple orbs faster and faster, catches all three in one hand, grins "
     "wide, and hurls them one after another straight at the camera." % HIM,
     "the crackle of the orbs, his rising laughter, three sharp whooshes",
     both(T1, T1, J0, J0, t_hidden=True), []),
    ("D03", "the dodge", 73,
     {"cam": [6.5, 25.5, 1.3], "look": [-1.2, 23.4, 1.5], "lens": 28},
     "Side view: three glowing purple orbs streak in from the right at %s; she flips sideways out of their path "
     "and lands crouched; the orbs fly on and slam into the tree behind her one after another, blasting bark and "
     "splinters out of its trunk in bursts of purple light." % HER,
     "three whooshes, three explosions, splintering wood, her landing",
     both(T1, T2, J0, J0, j_hidden=True), [{"ev": "bark", "tree": "E1", "f": 34, "from_az": 23}]),
    ("D04", "her answer", 73,
     {"cam": [1.5, 27.6, 0.55], "look": [0.8, 25.4, 1.45], "lens": 30},
     "Low angle on %s: flames ignite in both her hands and a bright orange aura flares up around her, her hair "
     "lifting in the heat; she thrusts both palms forward and fires a rapid volley of fireballs past the camera." % HER,
     "the roar of igniting flame, a rising hum, three fiery whooshes",
     both(T2, T2, J0, J0, j_hidden=True), []),
    ("D05", "his dodge", 73,
     {"cam": [7.0, 29.2, 1.5], "look": [1.0, 34.6, 1.6], "lens": 26},
     "Wide: fireballs streak in from the left at %s; he cartwheels and flips out of their way, leaving a trail of "
     "afterimages; the fireballs fly on into the great boulder behind him, which bursts apart in a blast of fire "
     "and flying rock." % HIM,
     "fiery whooshes, his gleeful laugh, a thunderous explosion, rocks crashing down",
     both(T2, T2, J0, J1, t_hidden=True), [{"ev": "shatter", "f": 30, "from_az": 199}]),
    ("D06", "the grin", 73,
     {"cam": [0.0, 31.0, 1.65], "cam_to": [-0.05, 31.4, 1.65], "look": [-0.6, 34.2, 1.75], "lens": 50},
     "Close on %s: soot on his chalk-white face; he wipes it off with his thumb, his grin widening; his eyes flare "
     "purple and a crackling purple aura erupts around him, his costume rippling in it." % HIM,
     "a low laugh, crackling energy rising, a deep rumble",
     both(T2, T2, J1, J1, t_hidden=True), []),
    # v2 (07:30 ET): v1 was wide enough for his whole dash (cam [6.8, 28.6, 1.3]) and the flurry played at a
    # quarter of the frame's height. Now a medium on the flurry: he streaks in from out of the frame, she holds
    # her ground, the beats numbered, the blows keyed (KEYS) and the shot ending posed in the lock.
    ("D07", "the clash", 73,
     {"cam": [3.9, 28.1, 1.3], "look": [0.35, 28.1, 1.35], "lens": 30},
     "Side view: (1) %s streaks in from the right in a blur of purple afterimages and throws a punch at %s that "
     "she blocks on her raised forearm with a white flash; (2) a second punch - she parries it aside; (3) he "
     "spins into a high kick that she catches on both crossed forearms with a white flash; (4) their forearms "
     "lock, straining, and (5) a shockwave of dust, leaves and pebbles bursts outward from them across the "
     "ground." % (HIM, HER),
     "a rush of wind, rapid thuds and cracks, a booming impact, scattering pebbles",
     {"terra": {"start": m(T3, J1), "end": m(T3, J2)}, "jester": {"start": m(J1, T3, True), "end": m(J2, T3)}},
     [{"ev": "shock", "at": [0.35, 28.1], "f": 38, "n": 50, "radius": 3.0}]),
    ("D08", "the kick", 73,
     {"cam": [3.6, 22.8, 0.9], "look": [-2.5, 29.0, 1.6], "lens": 26},
     "Low angle: %s spins and drives a kick into the jester's chest; he is launched backward across the clearing "
     "and smashes into a tree trunk, which snaps with a crack - the whole top of the tree topples away behind him "
     "and crashes into the forest; he drops to his feet, grinning." % HER,
     "the kick's thud, a body slamming into wood, a huge crack, the crash of the falling tree, his giggle",
     both(T3, T4, J2, J3), [{"ev": "snap", "tree": "E2", "f": 30, "fall_az": 285}]),
    ("D09", "in the air", 73,
     {"cam": [0.6, 17.5, 0.5], "look": [-0.8, 29.0, 5.0], "lens": 20},
     "Wide, from low on the ground: %s and %s leap high into the air and meet above the clearing in a burst of "
     "light; the shockwave shakes the treetops and a rain of leaves pours down as they drop back to the ground on "
     "opposite sides." % (HER, HIM),
     "two leaps, a thunderous mid-air impact, the roar of shaken leaves, two landings",
     both(T4, T5, J3, J4), [{"ev": "leafrain", "at": [-1.5, 28.6], "f": 32, "n": 90, "radius": 8.0}]),
    ("D10", "the blast", 105,
     {"cam": [6.0, 17.5, 2.4], "look": [0.0, 31.0, 3.0], "lens": 22},
     "Wide: %s raises both hands and a huge fireball swells above her; across the clearing %s gathers a giant "
     "purple orb; they hurl them and the two spells collide in the middle in a blinding explosion; the blast hurls "
     "the jester out of the clearing and tears three great trees out of the ground behind him, toppling them into "
     "the forest; she stands braced, her hair whipping in the shockwave, as the smoke rolls past." % (HER, HIM),
     "the roar of fire, crackling energy, an enormous explosion, splintering trunks, crashing trees, then wind",
     both(T5, T5, J4, J4, j_end_hidden=True), [{"ev": "topple", "trees": ["E3", "E4", "E5"], "f": 60, "at": [0.0, 30.5]}]),
]


# ------------------------------------------------------------------------------------------- rounds two and three
# south down the path from the clearing: the bend by the trees S1 and S2, the great oak (3.7, 8.2) - which
# her fireball brings down across the path - and the hollow beyond it, by the trees S3 and S5
DRESS_PATH = ("Turn <image1> into a frame from a hand-drawn 2D anime film: a dark fantasy forest path between huge "
              "gnarled trees, painted as an anime background, clean line art, flat cel shading, shafts of late "
              "sunlight through the canopy, drifting mist. Keep the camera, the lens, the framing, the perspective "
              "and the layout of <image1> exactly: everything in it stays exactly where it is, at the same size, with "
              "the same colours; add nothing and remove nothing.")
STAY_PATH = " The forest, the path, the trees and the light stay exactly as they are."


def fig(at, to=None, hidden=False):
    return m(at, to, hidden)


def F2(**who):
    """figures: name=(start, end) with start/end from fig()."""
    return {k: {"start": v[0], "end": v[1]} for k, v in who.items()}


H = fig  # short


TA, TB, TC = (1.6, 25.2), (1.4, 22.6), (1.4, 16.2)
JA = (1.3, 18.6)
CL1, CL2, CL3 = (-0.4, 14.0), (3.2, 14.2), (1.5, 13.0)
SHOTS2 = [
    ("E01", "the giggle", 73, {"cam": [0.2, 23.0, 1.2], "look": [1.6, 25.2, 1.5], "lens": 32},
     "Medium, low: %s lowers her hands, breathing hard, smoke drifting past her; a high giggle echoes from somewhere "
     "behind her and she whirls around." % HER,
     "crackling embers, her breathing, a distant echoing giggle, the swish of her turning",
     F2(terra=(H(TA, (0.5, 32.0)), H(TA, JA)), jester=(H(JA, hidden=True), H(JA, hidden=True))), [], "clearing"),
    ("E02", "three of him", 73, {"cam": [2.2, 27.6, 1.65], "look": [1.3, 18.6, 1.2], "lens": 35},
     "Over her shoulder: at the far edge of the clearing %s stands on the path, unharmed, his costume smoking; he "
     "bows deeply, snaps his fingers, and two more identical grinning jesters step out from behind him; all three "
     "scatter into the trees." % HIM,
     "a sizzle of smoke, his laughter, a finger snap, a shimmering chime, rustling branches",
     F2(terra=(H(TA, JA), H(TA, JA)), jester=(H(JA, TA), H(JA, hidden=True))), [], "clearing"),
    ("E03", "she runs", 73,
     {"cam": [1.25, 19.6, 1.15], "cam_to": [1.3, 13.4, 1.15], "look": [1.4, 23.0, 1.35], "look_to": [1.4, 16.6, 1.35], "lens": 32},
     "%s runs straight at the camera down the forest path, hair streaming, fire flickering around her fists; the "
     "camera rushes backward ahead of her at her speed; purple afterimages of the jester flicker between the trees "
     "on either side." % HER[0].upper() + HER[1:],
     "her running footsteps, rushing wind, crackling flames, giggles panning past",
     F2(terra=(H(TB, (1.4, 10.0)), H(TC, (1.4, 10.0)))), [], "path"),
    ("E04", "the ambush", 73, {"cam": [5.5, 20.0, 6.0], "look": [1.3, 14.5, 0.6], "lens": 24},
     "High angle: as %s reaches the bend in the path, three identical grinning jesters drop out of the trees around "
     "her and land in a ring, crouching, then rise and spread their arms wide." % HER,
     "rustling branches, three thuds, triple laughter in unison",
     F2(terra=(H(TC, (1.4, 10.0)), H(TC, CL3)), jester=(H(CL1, hidden=True), H(CL1, TC)),
        jester2=(H(CL2, hidden=True), H(CL2, TC)), jester3=(H(CL3, hidden=True), H(CL3, TC))), [], "path"),
    ("E05", "the fire ring", 73, {"cam": [-3.6, 17.2, 1.35], "look": [1.5, 14.0, 1.2], "lens": 26},
     "%s spins on one foot and a ring of fire blasts outward from her, ripping up dust and leaves; two of the "
     "jesters burst into puffs of purple smoke and confetti - illusions - and the real one back-flips out of the "
     "flames and lands further down the path, grinning." % HER[0].upper() + HER[1:],
     "a roar of flame, two pops, a shower of confetti, his laugh",
     F2(terra=(H(TC, CL3), H(TC, (1.2, 10.8))), jester=(H(CL1, TC), H(CL1, hidden=True)),
        jester2=(H(CL2, TC), H(CL2, hidden=True)), jester3=(H(CL3, TC), H((1.2, 10.8), TC))),
     [{"ev": "shock", "at": [1.4, 16.2], "f": 26, "n": 60, "radius": 3.5}], "path"),
    ("E05b", "deflected", 73, {"cam": [3.8, 18.6, 1.4], "look": [1.3, 13.4, 1.4], "lens": 30},
     "Over her shoulder: (1) the jester flings a volley of glowing purple orbs at %s; (2) she swats each one aside "
     "with a flaming palm, left, right, left, (3) the deflected orbs ricocheting away into a tree at the bend, which "
     "bursts in sprays of bark and purple sparks; (4) he claps, delighted." % HER,
     "whooshes, three sharp slaps of fire, explosions in the trees, splintering bark, his applause",
     F2(terra=(H(TC, (1.2, 10.8)), H(TC, (1.2, 10.8))), jester3=(H((1.2, 10.8), TC), H((1.2, 10.8), TC))),
     [{"ev": "bark", "tree": "S1", "f": 40, "from_az": 120}], "path"),
    ("E06", "the chase", 73,
     {"cam": [-2.6, 15.0, 1.3], "cam_to": [-2.6, 12.4, 1.3], "look": [1.3, 13.8, 1.2], "look_to": [1.2, 11.4, 1.2], "lens": 28},
     "Tracking alongside them: %s backs away down the path in cartwheels, flinging glowing purple orbs at %s; she "
     "weaves between them and keeps coming; one orb bursts against a tree trunk beside the path in a spray of bark "
     "and purple sparks." % (HIM, HER),
     "running feet, whooshes, an explosion, splintering bark, his cackle",
     F2(terra=(H(TC, (1.2, 10.8)), H((1.3, 13.0), (1.2, 9.8))), jester3=(H((1.2, 10.8), TC), H((1.2, 9.8), (1.3, 13.0)))),
     [{"ev": "bark", "tree": "S2", "f": 34, "from_az": 220}], "path"),
    ("E06b", "up the trunks", 73, {"cam": [0.0, 15.2, 0.5], "look": [1.0, 9.0, 6.0], "lens": 20},
     "Looking up from the path, wuxia style: the jester runs straight up a tree trunk and leaps to the next, and %s "
     "runs up after him; they bound from trunk to trunk high above the path, light and graceful, then drop back "
     "down onto the path facing each other." % HER,
     "quick light footfalls on bark, rushing air, rustling leaves, two soft landings",
     F2(terra=(H((1.3, 13.0), (1.2, 9.8)), H((1.3, 13.0), (1.2, 9.8))), jester3=(H((1.2, 9.8), (1.3, 13.0)), H((1.2, 9.8), (1.3, 13.0)))),
     [], "path"),
    ("E06c", "among the branches", 73, {"cam": [4.6, 12.2, 3.2], "look": [1.0, 11.0, 4.6], "lens": 26},
     "High among the branches: %s and the jester meet in mid-air between the trunks and trade three blows in a "
     "blur - a kick, a block, a palm strike - each with a white impact flash; the shock shakes a shower of leaves "
     "from the canopy as they fall away from each other." % HER,
     "three sharp impacts, rushing wind, a roar of shaken leaves",
     F2(terra=(H((1.3, 13.0), (1.2, 9.8), hidden=True), H((1.3, 13.0), (1.2, 9.8))),
        jester3=(H((1.2, 9.8), (1.3, 13.0), hidden=True), H((1.2, 9.8), (1.3, 13.0)))),
     [{"ev": "leafrain", "at": [1.2, 11.4], "f": 30, "n": 80, "radius": 5.0}], "path"),
    ("E07", "the oak falls", 73, {"cam": [-0.8, 1.5, 1.1], "look": [1.4, 10.0, 2.6], "lens": 24},
     "Wide, from down the path: %s hurls a blazing fireball past the jester into the base of a huge old oak beside "
     "the path; the trunk explodes and the whole tree topples across the path in front of him with a thunderous "
     "crash; he skids to a stop at the fallen trunk and spins around to face her." % HER,
     "a fireball's roar, an explosion, splintering wood, the crash of the oak, his skidding feet",
     F2(terra=(H((1.3, 13.0), (1.2, 9.8)), H((1.3, 12.6), (1.1, 9.6))),
        jester3=(H((1.2, 9.8), (1.1, 2.0)), H((1.1, 9.6), (1.3, 12.6)))),
     [{"ev": "oak", "f": 28}], "path"),
    ("E08", "cornered", 57, {"cam": [0.7, 11.6, 1.75], "look": [1.1, 9.6, 1.85], "lens": 50},
     "Close on %s, cornered against the fallen trunk: he glances back at it, then at her, and his grin stretches "
     "wider; purple flames flicker up around his hands." % HIM,
     "his low chuckle, crackling purple flame, settling wood",
     F2(jester3=(H((1.1, 9.6), (1.3, 12.6)), H((1.1, 9.6), (1.3, 12.6)))), [], "path"),
    ("E09", "at the trunk", 73, {"cam": [6.0, 11.0, 1.3], "look": [1.2, 10.3, 1.2], "lens": 30},
     "Side view: (1) %s rushes him; (2) the jester ducks her flaming punch and snaps a kick at her head; (3) she "
     "blocks it with her forearm in a white flash; (4) she drives her knee into his stomach and (5) he folds and "
     "slides back against the fallen trunk, dust bursting from the bark." % HER,
     "rushing feet, a whoosh of fire, the crack of the block, a thud, his gasp, the trunk shuddering",
     F2(terra=(H((1.3, 12.6), (1.1, 9.6)), H((1.2, 11.0), (1.5, 9.4))), jester3=(H((1.1, 9.6), (1.3, 12.6)), H((1.5, 9.4), (1.2, 11.0)))),
     [{"ev": "shock", "at": [1.3, 10.2], "f": 44, "n": 40, "radius": 2.0}], "path"),
    ("E09b", "trading blows", 73, {"cam": [-3.4, 11.8, 1.2], "look": [1.3, 10.2, 1.3], "lens": 30},
     "(1) The jester answers with a spinning backfist; (2) %s ducks under it and (3) drives two fast punches into his "
     "ribs; (4) he slaps her third punch aside and (5) kicks her in the stomach, sliding her back a step, (6) and "
     "giggles." % HER,
     "a whoosh, two thuds, a slap, a kick, scuffing feet, his giggle",
     F2(terra=(H((1.2, 11.0), (1.5, 9.4)), H((1.2, 11.0), (1.5, 9.4))), jester3=(H((1.5, 9.4), (1.2, 11.0)), H((1.5, 9.4), (1.2, 11.0)))),
     [], "path"),
    ("E09c", "the elbow", 57, {"cam": [4.2, 10.8, 1.5], "look": [1.35, 10.2, 1.45], "lens": 40},
     "Close and fast: %s catches his wrist, steps in and drives her elbow into his jaw in a white flash; his head "
     "snaps back and his cap's bells jangle." % HER,
     "a grab, a sharp crack, jangling bells",
     F2(terra=(H((1.2, 11.0), (1.5, 9.4)), H((1.2, 11.0), (1.5, 9.4))), jester3=(H((1.5, 9.4), (1.2, 11.0)), H((1.5, 9.4), (1.2, 11.0)))),
     [], "path"),
    ("E10", "over the trunk", 73, {"cam": [-3.0, 10.5, 0.8], "look": [1.0, 8.5, 1.3], "lens": 26},
     "Low angle: the jester springs backward off the fallen trunk in a high somersault over it and lands crouched on "
     "the far side, then wags a finger at %s and beckons her on." % HER,
     "a spring, a whoosh, a soft landing, his singsong giggle",
     F2(terra=(H((1.2, 11.0), (1.5, 9.4)), H((1.2, 10.4), (0.9, 6.4))), jester3=(H((1.5, 9.4), (1.2, 11.0)), H((0.9, 6.4), (1.2, 10.4)))),
     [], "path"),
    # round three: the hollow beyond the fallen oak
    ("F01", "auras", 73, {"cam": [-3.6, 1.0, 0.7], "look": [0.8, 5.0, 1.5], "lens": 24},
     "Wide and low: %s vaults over the fallen trunk and lands facing the jester; both their auras flare up - hers "
     "orange fire, his crackling purple - the ground cracking between them and pebbles lifting off it; the leaves "
     "around them are torn from the branches and swirl down." % HER,
     "a leap, a landing, two roaring auras, cracking earth, a rising hum",
     F2(terra=(H((1.2, 10.4), (0.9, 6.4)), H((0.8, 6.2), (0.6, 2.6))), jester3=(H((0.9, 6.4), (1.2, 10.4)), H((0.6, 2.6), (0.8, 6.2)))),
     [{"ev": "leafrain", "at": [0.7, 4.4], "f": 36, "n": 80, "radius": 7.0}], "path"),
    ("F02", "fists meet", 73, {"cam": [5.0, 4.6, 1.2], "look": [0.6, 4.3, 1.3], "lens": 28},
     "Side view: they dash at each other and their fists meet in the middle with a blinding flash; a shockwave ring "
     "of dust and leaves bursts outward across the path; speed lines, the camera shaking.",
     "two rushes of wind, a thunderous impact, a booming shockwave, scattering pebbles",
     F2(terra=(H((0.8, 6.2), (0.6, 2.6)), H((0.8, 4.9), (0.6, 3.7))), jester3=(H((0.6, 2.6), (0.8, 6.2)), H((0.6, 3.7), (0.8, 4.9)))),
     [{"ev": "shock", "at": [0.7, 4.3], "f": 30, "n": 70, "radius": 3.5}], "path"),
    ("F02b", "blur", 73, {"cam": [-3.8, 4.0, 1.0], "look": [0.7, 4.3, 1.3], "lens": 26},
     "At blur speed: they trade a storm of punches and kicks too fast to follow, afterimages smearing behind every "
     "limb, white flashes popping like fireworks between them; dust spirals up from their feet.",
     "a rapid drumroll of impacts, whooshing limbs, crackling energy",
     F2(terra=(H((0.8, 4.9), (0.6, 3.7)), H((0.8, 4.9), (0.6, 3.7))), jester3=(H((0.6, 3.7), (0.8, 4.9)), H((0.6, 3.7), (0.8, 4.9)))),
     [], "path"),
    ("F02c", "the furrows", 73, {"cam": [4.8, 7.6, 0.8], "look": [0.7, 4.0, 1.0], "lens": 26},
     "Low angle: a palm strike from the jester catches %s square in the chest; she is driven back across the path "
     "on her heels, her boots ploughing two long furrows through the dirt in a spray of dust and pebbles, until "
     "she stops, still standing, and wipes her mouth." % HER,
     "a heavy impact, scraping boots, spraying gravel, a breath",
     F2(terra=(H((0.8, 4.9), (0.6, 3.7)), H((0.8, 4.9), (0.6, 3.7))), jester3=(H((0.6, 3.7), (0.8, 4.9)), H((0.6, 3.7), (0.8, 4.9)))),
     [{"ev": "shock", "at": [0.8, 5.8], "f": 20, "n": 50, "radius": 2.5}], "path"),
    ("F03", "locked", 57, {"cam": [2.6, 4.6, 1.35], "look": [0.7, 4.3, 1.3], "lens": 50},
     "Close on their locked fists and forearms, straining against each other; sparks of orange fire and purple "
     "energy spit and crackle from the contact; his grin and her gritted teeth at the edges of the frame.",
     "grinding pressure, crackling sparks, two strained breaths",
     F2(terra=(H((0.8, 4.9), (0.6, 3.7)), H((0.8, 4.9), (0.6, 3.7))), jester3=(H((0.6, 3.7), (0.8, 4.9)), H((0.6, 3.7), (0.8, 4.9)))),
     [], "path"),
    ("F04", "thrown", 73, {"cam": [-3.6, 5.5, 1.3], "look": [1.8, 4.4, 1.6], "lens": 26},
     "(1) The jester twists, seizes her wrist and (2) spins, hurling %s across the path; (3) she smashes back-first "
     "into a tree trunk and it snaps with a crack, (4) the whole top of the tree toppling away into the forest; (5) "
     "she drops to her feet among the splinters." % HER,
     "a grunt, a whoosh, a body hitting wood, a huge crack, the crash of the falling tree",
     F2(terra=(H((0.8, 4.9), (0.6, 3.7)), H((2.3, 4.6), (0.4, 3.9))), jester3=(H((0.6, 3.7), (0.8, 4.9)), H((0.4, 3.9), (2.3, 4.6)))),
     [{"ev": "snap", "tree": "S3", "f": 32, "fall_az": 80}], "path"),
    ("F05", "her eyes", 57, {"cam": [1.0, 4.9, 1.45], "look": [2.3, 4.6, 1.5], "lens": 45},
     "Close on the face of %s as she rises from the splinters: her eyes blaze, and a roaring orange aura erupts "
     "around her head and shoulders, her hair lifting in the heat. The camera stays close on her face the whole "
     "time, one unbroken close-up." % HER,
     "settling splinters, a sharp intake of breath, the roar of her aura",
     F2(terra=(H((2.3, 4.6), (0.4, 3.9)), H((2.3, 4.6), (0.4, 3.9)))), [], "path"),
    ("F05b", "fire comet", 73, {"cam": [-3.0, 7.2, 1.2], "look": [1.4, 4.2, 1.2], "lens": 26},
     "%s launches herself at the jester wreathed in fire like a comet; she tackles him and they tumble over and over "
     "across the path in a rolling ball of flame and dust, then kick apart and spring back to their feet." %
     (HER[0].upper() + HER[1:]),
     "a roaring launch, a crash, tumbling bodies, a burst of flame, two landings",
     F2(terra=(H((2.3, 4.6), (0.4, 3.9)), H((2.3, 4.6), (0.4, 3.9))), jester3=(H((0.4, 3.9), (2.3, 4.6)), H((0.4, 3.9), (2.3, 4.6)))),
     [{"ev": "shock", "at": [1.3, 4.2], "f": 30, "n": 50, "radius": 2.5}], "path"),
    ("F06", "the fire whip", 73, {"cam": [3.8, 9.0, 2.6], "look": [0.9, 2.2, 0.9], "lens": 24},
     "High angle: %s lashes a long whip of fire at the jester; he cartwheels away from it down the path; the whip "
     "slices clean through a tree beside the path, and the severed top crashes down into the forest." % HER,
     "the crack and roar of the fire whip, his cartwheels, a slicing hiss, a falling tree",
     F2(terra=(H((2.3, 4.6), (0.4, 3.9)), H((1.6, 4.4), (0.2, 0.8))), jester3=(H((0.4, 3.9), (2.3, 4.6)), H((0.2, 0.8), (1.6, 4.4)))),
     [{"ev": "snap", "tree": "S5", "f": 36, "fall_az": 100}], "path"),
    ("F06b", "the serpents", 73, {"cam": [4.4, 5.6, 1.4], "look": [0.8, 2.4, 1.5], "lens": 26},
     "The jester juggles three purple orbs, and they stretch into three glowing serpents of purple light that coil "
     "through the air at %s; she spins and her fire catches all three, and they burst into purple sparks." % HER,
     "an eerie hiss, crackling energy, a roar of flame, three bursts",
     F2(terra=(H((1.6, 4.4), (0.2, 0.8)), H((1.6, 4.4), (0.2, 0.8))), jester3=(H((0.2, 0.8), (1.6, 4.4)), H((0.2, 0.8), (1.6, 4.4)))),
     [], "path"),
    ("F07", "the whirlwind", 73, {"cam": [-2.8, -3.5, 0.6], "look": [0.8, 2.8, 2.0], "lens": 22},
     "Wide and low: the jester spins faster and faster until he becomes a howling tornado of purple energy that tears "
     "leaves, dust and pebbles up into a spiral; it surges toward %s and she braces, her hair and dress whipping." % HER,
     "a rising howl of wind, crackling energy, swirling debris",
     F2(terra=(H((1.6, 4.4), (0.2, 0.8)), H((1.4, 5.0), (0.4, 2.6))), jester3=(H((0.2, 0.8), (1.6, 4.4)), H((0.4, 2.6), (1.4, 5.0)))),
     [{"ev": "leafrain", "at": [0.5, 2.5], "f": 10, "n": 90, "radius": 6.0},
      {"ev": "shock", "at": [0.4, 1.8], "f": 22, "n": 60, "radius": 3.0}], "path"),
    ("F07b", "orb rain", 73, {"cam": [-3.4, 8.6, 1.0], "look": [0.8, 3.0, 2.6], "lens": 22},
     "The jester rides the top of his tornado up into the treetops and rains glowing purple orbs down on %s; she "
     "dashes and flips between them as they hit the path behind her one after another, each blowing a crater of "
     "dirt and pebbles into the air." % HER,
     "a howling wind, a rain of whistling orbs, a string of explosions, her quick footsteps",
     F2(terra=(H((1.4, 5.0), (0.4, 2.6)), H((1.4, 5.0), (0.4, 2.6))), jester3=(H((0.4, 2.6), (1.4, 5.0)), H((0.4, 2.6), (1.4, 5.0)))),
     [{"ev": "shock", "at": [0.2, 6.6], "f": 24, "n": 40, "radius": 2.0},
      {"ev": "shock", "at": [2.0, 3.6], "f": 44, "n": 40, "radius": 2.0}], "path"),
    ("F07c", "slow motion", 57, {"cam": [0.92, 3.85, 1.5], "look": [1.4, 5.0, 1.52], "lens": 50},
     "In slow motion, close on %s: a glowing purple orb streaks straight at her face and she sways back from the "
     "waist, the orb passing a hand's width from her nose, its light sliding across her eyes, a strand of her hair "
     "lifting in its wake." % HER,
     "a long, slowed whoosh, a low hum, then sound snapping back to speed",
     F2(terra=(H((1.4, 5.0), (0.4, 2.6)), H((1.4, 5.0), (0.4, 2.6)))), [], "path"),
    ("F08", "through the storm", 73, {"cam": [5.0, 3.6, 1.3], "look": [0.9, 3.8, 1.8], "lens": 26},
     "Side view: %s thrusts both palms into the tornado and a spiral of fire bores straight through it; the "
     "tornado explodes and the jester is flung spinning high into the air." % HER,
     "a roaring fire spiral, an explosion, his surprised yelp spiralling upward",
     F2(terra=(H((1.4, 5.0), (0.4, 2.6)), H((1.4, 5.0), (0.4, 2.6))), jester3=(H((0.4, 2.6), (1.4, 5.0)), H((0.4, 2.6), hidden=True))),
     [{"ev": "shock", "at": [0.5, 2.6], "f": 36, "n": 50, "radius": 3.0}], "path"),
    ("F09", "in the air", 73, {"cam": [2.6, 9.6, 0.4], "look": [0.9, 3.5, 6.0], "lens": 20},
     "Looking up from the ground: %s leaps into the air after the spinning jester and hits him three times in "
     "mid-air - a punch, a knee, a spinning kick - each with a white impact flash and speed lines, then spikes him "
     "straight down out of frame." % HER,
     "a leap, three sharp impacts, a final booming kick, a whoosh downward",
     F2(terra=(H((1.4, 5.0), (0.4, 2.6)), H((1.0, 3.2), (0.6, 1.4)))), [], "path"),
    ("F10", "the crater", 73, {"cam": [-3.5, 0.0, 1.0], "look": [0.8, 2.0, 1.0], "lens": 26},
     "The jester crashes down into the path like a meteor: the dirt blasts open into a crater and a ring of earth, "
     "pebbles and dust sprays outward; a beat later he springs up out of the crater onto his feet, laughing, and "
     "dusts off his cap; %s lands beyond him." % HER,
     "a ground-shaking impact, raining dirt, a spring, his manic laugh, her landing",
     F2(terra=(H((1.0, 3.2), (0.6, 1.4), hidden=True), H((1.0, 3.2), (0.6, 1.4))), jester3=(H((0.6, 1.4), hidden=True), H((0.6, 1.4), (1.0, 3.2)))),
     [{"ev": "shock", "at": [0.6, 1.4], "f": 8, "n": 70, "radius": 4.0}], "path"),
    ("F10b", "pass through", 73, {"cam": [5.6, 2.2, 1.1], "look": [0.8, 2.2, 1.3], "lens": 26},
     "Side view: they charge at each other from either side and pass straight through each other in a blur - a "
     "single white slash of light between them - and land back to back; a beat of stillness, then both stagger, "
     "and the jester laughs." ,
     "two rushing charges, a single sharp ring of steel-like light, silence, a stagger, his laugh",
     F2(terra=(H((1.0, 3.2), (0.6, 1.4)), H((1.0, 3.2), (0.6, 1.4))), jester3=(H((0.6, 1.4), (1.0, 3.2)), H((0.6, 1.4), (1.0, 3.2)))),
     [], "path"),
    ("F11", "gathering", 73, {"cam": [6.5, 2.0, 1.5], "look": [0.6, 2.0, 1.6], "lens": 24},
     "Wide side view: they spring apart; %s draws both hands back and fire gathers between them into a blazing "
     "sphere; the jester raises both hands and a crackling purple orb swells above them." % HER,
     "two leaps, a growing roar of fire, a rising electric whine",
     F2(terra=(H((1.0, 3.2), (0.6, 1.4)), H((1.2, 6.0), (0.2, -2.2))), jester3=(H((0.6, 1.4), (1.0, 3.2)), H((0.2, -2.2), (1.2, 6.0)))),
     [], "path"),
    ("F11b", "the magician", 73, {"cam": [8.6, 1.8, 1.7], "look": [0.6, 2.0, 1.8], "lens": 22},
     "The jester sweeps off his cap with a flourish and pulls from it a long string of glowing purple orbs, like a "
     "magician's knotted scarves, and whips the whole string at %s; the orbs burst one after another in a chain of "
     "purple explosions racing toward her, and she burns through them with a wall of fire." % HER,
     "a flourish, a magician's chime, a chain of popping explosions, a roaring wall of flame",
     F2(terra=(H((1.2, 6.0), (0.2, -2.2)), H((1.2, 6.0), (0.2, -2.2))), jester3=(H((0.2, -2.2), (1.2, 6.0)), H((0.2, -2.2), (1.2, 6.0)))),
     [{"ev": "shock", "at": [0.8, 3.2], "f": 40, "n": 50, "radius": 3.0}], "path"),
    ("F11c", "the fire dragon", 73, {"cam": [7.6, 2.4, 1.9], "look": [0.7, 2.0, 2.2], "lens": 22},
     "%s sweeps both arms in a great circle and a dragon of living fire uncoils from her hands, roaring, and "
     "snakes through the air at the jester; he cartwheels away from its jaws as it plunges into the ground beside "
     "him and bursts into a wall of flame." % (HER[0].upper() + HER[1:]),
     "a rising roar, the dragon's howl, his yelp, a fiery explosion",
     F2(terra=(H((1.2, 6.0), (0.2, -2.2)), H((1.2, 6.0), (0.2, -2.2))), jester3=(H((0.2, -2.2), (1.2, 6.0)), H((0.2, -2.2), (1.2, 6.0)))),
     [{"ev": "shock", "at": [-0.6, -0.6], "f": 46, "n": 50, "radius": 3.0}], "path"),
    ("F11d", "ground pound", 73, {"cam": [-7.5, 2.0, 1.0], "look": [0.7, 2.0, 1.4], "lens": 22},
     "%s leaps high and drives her flaming fist into the path; a ring of fire and a shockwave split the ground "
     "and race outward, throwing dirt and pebbles into the air and knocking the jester off his feet; he flips "
     "back upright, laughing." % (HER[0].upper() + HER[1:]),
     "a leap, a thunderous impact, cracking earth, a rolling shockwave, his laugh",
     F2(terra=(H((1.2, 6.0), (0.2, -2.2)), H((1.2, 6.0), (0.2, -2.2))), jester3=(H((0.2, -2.2), (1.2, 6.0)), H((0.2, -2.2), (1.2, 6.0)))),
     [{"ev": "shock", "at": [1.2, 5.0], "f": 30, "n": 70, "radius": 4.0}], "path"),
    ("F12", "beam struggle", 105, {"cam": [7.5, 2.0, 1.2], "look": [0.7, 2.0, 1.6], "lens": 22},
     "Wide side view: she fires a roaring beam of fire and he fires a crackling beam of purple energy; the two beams "
     "collide midway in a blinding, churning ball of light that pushes back and forth between them; the wind tears "
     "leaves off the trees and the ground beneath the beams splits." ,
     "two roaring beams, a deafening churning blast, howling wind, cracking earth",
     F2(terra=(H((1.2, 6.0), (0.2, -2.2)), H((1.2, 6.0), (0.2, -2.2))), jester3=(H((0.2, -2.2), (1.2, 6.0)), H((0.2, -2.2), (1.2, 6.0)))),
     [{"ev": "leafrain", "at": [0.7, 2.0], "f": 20, "n": 90, "radius": 7.0},
      {"ev": "shock", "at": [0.7, 2.0], "f": 50, "n": 50, "radius": 3.5}], "path"),
    ("F12b", "behind her", 73, {"cam": [1.9, 8.2, 1.7], "look": [0.4, -1.0, 1.5], "lens": 28},
     "From behind %s: her fire beam pours away from her hands into the churning ball of light where it meets his "
     "purple beam; her hair and dress stream back in the gale; the ground cracks under her boots." % HER,
     "the roar of the beams, howling wind, cracking ground",
     F2(terra=(H((1.2, 6.0), (0.2, -2.2)), H((1.2, 6.0), (0.2, -2.2))), jester3=(H((0.2, -2.2), (1.2, 6.0)), H((0.2, -2.2), (1.2, 6.0)))),
     [], "path"),
    ("F13", "she pushes", 57, {"cam": [1.4, 4.3, 1.55], "look": [1.2, 6.0, 1.55], "lens": 45},
     "Close on %s straining, teeth gritted, hair whipping in the blast, both hands driving the fire beam forward as "
     "it flares brighter." % HER,
     "the roar of the beam, her strained cry",
     F2(terra=(H((1.2, 6.0), (0.2, -2.2)), H((1.2, 6.0), (0.2, -2.2)))), [], "path"),
    ("F14", "his grin cracks", 57, {"cam": [0.3, -0.4, 1.8], "look": [0.2, -2.2, 1.85], "lens": 45},
     "Close on %s: sweat running down his chalk-white face paint, which is cracking; his grin falters as the light "
     "in front of him grows." % HIM,
     "the crackle of his beam weakening, the roar of fire growing",
     F2(jester3=(H((0.2, -2.2), (1.2, 6.0)), H((0.2, -2.2), (1.2, 6.0)))), [], "path"),
    ("F15", "the blast", 105, {"cam": [5.5, 9.0, 4.0], "look": [0.6, 0.5, 1.0], "lens": 22},
     "High and wide: with a scream %s pours everything into the fire beam; it surges and drives the ball of light "
     "back into the jester, which explodes in a huge blossom of fire that swallows him; the shockwave flattens the "
     "undergrowth and tears leaves from every tree." % HER,
     "her scream, a surging roar, a colossal explosion, a rolling shockwave",
     F2(terra=(H((1.2, 6.0), (0.2, -2.2)), H((1.2, 6.0), (0.2, -2.2))), jester3=(H((0.2, -2.2), (1.2, 6.0)), H((0.2, -2.2), hidden=True))),
     [{"ev": "shock", "at": [0.2, -1.6], "f": 40, "n": 80, "radius": 5.0},
      {"ev": "leafrain", "at": [0.6, 1.0], "f": 46, "n": 90, "radius": 8.0}], "path"),
    # the end
    ("G01", "ash", 73, {"cam": [-3.0, 9.5, 1.4], "look": [0.8, 2.0, 1.3], "lens": 26},
     "Wide: the smoke rolls away; ash and embers drift down through the shafts of light; %s lowers her hands, "
     "panting, alone on the scorched path." % HER,
     "settling embers, wind, her breathing",
     F2(terra=(H((1.2, 6.0), (0.2, -2.2)), H((1.2, 6.0), (0.2, -2.2)))), [], "path"),
    ("G02", "still laughing", 73, {"cam": [1.4, 4.5, 1.6], "look": [-0.2, 0.8, 1.5], "lens": 40},
     "Out of the smoke staggers %s, scorched and swaying, his cap askew, still laughing weakly." % HIM,
     "a wheezing laugh, crunching footsteps, crackling embers",
     F2(jester3=(H((-0.4, 0.2), (1.2, 6.0)), H((0.0, 1.6), (1.2, 6.0)))), [], "path"),
    ("G02b", "the flame", 57, {"cam": [2.1, 4.9, 1.3], "look": [1.2, 6.0, 1.25], "lens": 50},
     "Close on the hand of %s as it rises, trembling, and a small flame flickers to life in her palm and steadies." % HER,
     "a soft crackle of flame, her breath",
     F2(terra=(H((1.2, 6.0), (0.0, 1.6)), H((1.2, 6.0), (0.0, 1.6)))), [], "path"),
    ("G03", "the bow", 73, {"cam": [5.0, 2.6, 1.3], "look": [0.5, 2.5, 1.4], "lens": 30},
     "Side view: %s walks up to him and raises one hand, a small flame dancing in her palm; the jester looks at the "
     "flame, then at her, grins, and bows deeply." % HER,
     "footsteps, a soft crackle of flame, his chuckle",
     F2(terra=(H((1.2, 6.0), (0.0, 1.6)), H((0.9, 3.4), (0.0, 1.6))), jester3=(H((0.0, 1.6), (1.2, 6.0)), H((0.0, 1.6), (0.9, 3.4)))),
     [], "path"),
    ("G04", "gone", 73, {"cam": [1.9, 4.2, 1.6], "look": [0.0, 1.6, 1.6], "lens": 40},
     "The jester winks, snaps his fingers and bursts into a cloud of purple smoke and confetti - gone; the confetti "
     "flutters down where he stood, and his laughter echoes away into the forest.",
     "a finger snap, a pop, fluttering confetti, echoing laughter fading",
     F2(jester3=(H((0.0, 1.6), (0.9, 3.4)), H((0.0, 1.6), hidden=True))),
     [{"ev": "leafrain", "at": [0.0, 1.6], "f": 30, "n": 60, "radius": 1.8}], "path"),
    ("G05", "her", 73, {"cam": [0.6, 1.9, 1.5], "look": [0.9, 3.4, 1.5], "lens": 50},
     "Close on %s: she lets her hand fall and the flame in it goes out; she looks up at the confetti and leaves "
     "drifting down around her, and breathes out." % HER,
     "a soft hiss as the flame goes out, drifting leaves, a long breath",
     F2(terra=(H((0.9, 3.4), (0.0, 1.6)), H((0.9, 3.4), (0.0, 1.6)))), [], "path"),
    ("G06", "the way home", 105, {"cam": [0.8, -6.0, 4.0], "look": [1.0, 6.0, 1.5], "lens": 24},
     "High and wide: %s turns and walks away up the path toward the fallen oak, small among the huge trees, leaves "
     "drifting down through the evening light; the forest is quiet." % HER,
     "her footsteps, wind in the leaves, a far bird call",
     F2(terra=(H((0.9, 3.4), (1.0, 12.0)), H((1.0, 6.6), (1.0, 12.0)))), [], "path"),
]


KEEP2 = (" Both stay where they stand in the picture, the same size; his hands are empty. Everything else - the "
         "clearing, the trees, the light, both of their costumes, faces and colours - stays exactly as it is; same "
         "camera, same framing.")


# KEY POSES (LTX_PLAYBOOK §100.10): frames of a shot painted into a pose and anchored where the blow lands
# (`set_test.py key`, then `take`). F10 by words was a pillar of light on 4 of 4 seeds; one key of the impact,
# painted from the end frame with her erased first (she lands later), drew him crashing in, 2 of 2.
KEYS = {
    "F10": [{"at": 10, "from": "end",
             "erase": "Edit <image1>: remove the young woman with sea-green hair and fill in the forest and the path "
                      "behind her. The harlequin jester stays exactly as he is; everything else stays exactly as it "
                      "is; same camera, same framing.",
             "pose": "Edit <image1>: the harlequin jester has just crashed down from the sky into the middle of the "
                     "path: he is crouched low on one knee, his fist driven into the ground, and the dirt is erupting "
                     "around him in a ring of earth, rocks and dust flying outward, a white impact flash under his "
                     "fist. His face, costume and colours stay exactly as they are; the forest and the light stay "
                     "exactly as they are; same camera, same framing.",
             "seed": 202}],
    # the flurry, at frames 20 and 42 of 73, and the lock it ends in: each a pose in place at the end marks;
    # seed 11 picked off keys_D07/keys.jpg (seed 202 restyled all three, flagged x4.4-4.5). The end key's
    # first words let the editor turn her to the camera and swap her boots for sandals: the take swung her
    # round to face the camera at frame 46 on its way into the lock (2 of 2) - so her profile and boots are named.
    "D07": [{"at": 20, "from": "end",
             "pose": "Edit <image1>: the harlequin jester has just streaked in, a blur of purple afterimages trailing "
                     "behind him to the right, and his fist meets the raised forearm of the young woman with sea-green "
                     "hair in a white flash of impact." + KEEP2, "seed": 11},
            {"at": 42, "from": "end",
             "pose": "Edit <image1>: the harlequin jester spins into a high kick and the young woman with sea-green "
                     "hair catches his shin on both crossed forearms in a white flash of impact." + KEEP2, "seed": 11},
            {"at": "end", "from": "end",
             "pose": "Edit <image1>: the young woman with sea-green hair and the harlequin jester have locked "
                     "forearms, straining against each other face to face, and a ring of dust, leaves and pebbles "
                     "bursts outward from their feet across the ground. She stays side-on to the camera, in "
                     "profile as she stands now, in her red dress and knee-high red boots." + KEEP2, "seed": 11}],
}


# a take whose own sound the score buries (set_film.py cut, "sound_gain_db"). Tried on F05 (its aura roar -43 dB
# mean on its own): +14 dB moved that stretch of the mix by 0.2 dB - the score carries the moment; the fix is
# ducking the score, not lifting the take. Left empty.
SOUND_GAIN = {}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--style", default="shon", choices=sorted(STYLES))
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    film = {
        "_comment": "The duel in the clearing (2026-10-01): frames first in a set with physics. "
                    "See _make_forest_duel_1001.py.",
        "film": FILM, "title": "THE DUEL IN THE CLEARING", "subtitle": "Terra and the jester",
        "logline": "In a clearing ringed by standing stones, Terra and the jester fight it out with fists, fire and orbs.",
        "grade": GRADE, "avoid": AVOID, "realism": "", "style": a.style,
        "score_tags": "epic anime battle score, fast taiko drums, driving strings, brass stabs, electric guitar, "
                      "instrumental, no vocals",
        "place": {"id": "clearing", "prompt": "A forest clearing ringed by huge trees and standing stones, painted as an "
                                              "anime background."},
        "cast": {"terra": {"role": "Terra", "prompt": "Terra: her character sheet (studio/sheets/terra-in-the-plaza-terra)."},
                 "jester": {"role": "the jester", "prompt": "The jester: his character sheet (studio/sheets/forest-fight-the-jester)."}},
        "shots": [],
    }
    acts, done = {}, []
    for row in [r + ("clearing",) for r in SHOTS] + SHOTS2:
        sid, name, frames, cam, beat, sound, figs, live, where = row
        dress = DRESS if where == "clearing" else DRESS_PATH
        # only the two frames are drawn from the set (previz_blender --endpoints); masks at both of them
        pz = {"scene": "set", "set": "duel", "action": "duel:%s:%s" % (FILM, sid), "frames": frames,
              "masks": 8 if sid.startswith("D") else frames, "endpoints": 1,
              "dress": dress, "dress_place": dress, "grade": GRADE}
        pz.update(cam)
        # the battle dialect only where something is fought: on the establishing shot it fired a white impact
        # frame at nothing and turned her walk into a dash (D01, 2026-10-01)
        style = "" if sid in QUIET else STYLES[a.style]
        prompt = ("2D anime, hand-drawn cel animation. " + style + beat +
                  (STAY if where == "clearing" else STAY_PATH) + " Sound: " + sound + ". No music.")
        film["shots"].append({"id": sid, "name": name, "title": name, "secs": round(frames / 24.0, 2), "face": "none",
                              "engine": "h3f", "refs": ["clearing", "terra", "jester"], "anchor": None,
                              "prompt": prompt, "avoid_extra": OTHERS, "previz": pz})
        if sid in KEYS:
            film["shots"][-1]["keys"] = KEYS[sid]
        if sid in SOUND_GAIN:
            film["shots"][-1]["sound_gain_db"] = SOUND_GAIN[sid]
        acts[sid] = {"figures": figs, "done": list(done), "live": live}
        done += live
    for name, obj in ((FILM + ".json", film), (FILM + ".acts.json", acts)):
        p = os.path.join(DST, name)
        if os.path.exists(p) and not a.force:
            raise SystemExit("keeping %s (it exists - --force to rewrite)" % p)
        json.dump(obj, open(p, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
        print("%s: %d shots -> %s" % (name, len(film["shots"]), p))


if __name__ == "__main__":
    main()
