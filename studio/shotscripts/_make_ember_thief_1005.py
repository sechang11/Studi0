#!/usr/bin/env python3
"""THE EMBER THIEF (2026-10-05): one minute of Terra and the jester, written as a STORY before it was shot.

The director on THE DUEL IN THE CLEARING: awkward striking, characters facing the wrong way, and shots that play
"like many individual scenes strung together randomly, not a story where each shot led to the next". So:
  1. a script first (SCRIPT below, written out as ember-thief.md): one goal - the jester has stolen Terra's
     ember pendant, she wants it back - and every shot caused by the one before it;
  2. ONE LINE OF ACTION: she comes from the south of the clearing, he waits in the north, and every camera stands
     east of the line between them - she is always on the left of the screen and attacks to the right, he is
     always on the right and attacks to the left; `check` refuses a camera on the wrong side;
  3. ONE CHAIN OF MARKS: where a character ends a shot is where they start the next (unless the story moves
     them: a vanishing trick, a leap, a blast), checked;
  4. both of them FACE the one they fight in every frame the set draws (set_test.py's turnaround views were
     mirrored until today - patch_1005), checked on screen;
  5. one beat list per shot with the body mechanics and the direction of every move (fight_words.py: numbered
     beats render 6 of 6), the battle style line only where something is hit.

Frames first in the clearing of set_duel.py (playbook §99.10, §100); set_film.py check / frames / takes / cut.
Writes studio/shotscripts/ember-thief.json, ember-thief.acts.json and ember-thief.md.
    python3 studio/shotscripts/_make_ember_thief_1005.py [--force]
"""
import argparse
import json
import math
import os
import sys

ROOT = os.path.expanduser("~/shared/comfy-studio")
DST = os.path.join(ROOT, "studio", "shotscripts")
FILM = "ember-thief"

GRADE = ("2D anime film, hand-drawn cel animation, painted backgrounds, a forest clearing at dusk, shafts of low "
         "sunlight, drifting mist.")
AVOID = ("lowres, blurry, morphing, warping, melting, flicker, deformed hands, extra fingers, extra limbs, two of the "
         "same person, subtitles, captions, watermark, nsfw")
OTHERS = "3d render, cgi, photorealistic, live action, a crowd, other people, blood, gore"
HER = "the young woman with long wavy sea-green hair, a red dress and red boots"
HIM = "the lanky harlequin jester in a purple-and-yellow diamond costume and two-horned cap"
PEND = "a small stone pendant glowing like a live coal on a thin gold chain"
DRESS = ("Turn <image1> into a frame from a hand-drawn 2D anime film: a forest clearing ringed by huge dark trees "
         "and old standing stones, painted as an anime background, clean line art, flat cel shading, shafts of late "
         "sunlight falling into the clearing, drifting mist at its edges. Keep the camera, the lens, the framing, "
         "the perspective and the layout of <image1> exactly: everything in it stays exactly where it is, at the "
         "same size, with the same colours; add nothing and remove nothing.")
FIGHT = ("A fight in the manner of a 90s shonen battle anime - glowing auras, speed lines, afterimages, a white "
         "impact frame on every hit. ")
MOVE = "Fast action in the manner of a 90s shonen battle anime - speed lines and afterimages. "
STAY = " The clearing, the trees, the standing stones and the light stay exactly as they are."

# ---------------------------------------------------------------------------------------------- the marks
# set coordinates (metres; +y north). The clearing's centre (0.5, 28.0), radius 9.5; the great boulder (4.4, 36.0)
# north-east of it, standing stones on its east rim. She comes up the path from the south; he waits in the north.
T0, T1, T2, T3 = (0.9, 19.0), (0.8, 22.4), (1.2, 26.6), (1.3, 26.9)
T4, T5, T6, T7 = (1.0, 24.4), (0.8, 22.6), (0.85, 23.0), (0.9, 23.3)
J0, J1, J2, J3 = (3.2, 33.0), (1.9, 28.4), (1.9, 28.2), (2.7, 29.4)
# J4: where her uppercut catches him (110 ends ON the blow, close enough for a key pose of the contact) and where
# he springs from (130) and lands (160) - J5 the top of his leap above it
J4, J5, J7 = (1.0, 23.95), (1.0, 23.95, 4.2), (1.0, 38.2)
J4air = (1.0, 23.95, 2.2)      # 130 ends with him in the air above her, on his way up (his body, not a streak)
HID = None


def mk(at, to):
    return {"hidden": True} if at is HID else {"at": list(at), "to": list(to[:2])}


def F(t=(HID, HID), j=(HID, HID), tt=None, jt=None):
    """The figures of a shot: Terra's and the jester's (start, end) marks; each faces the other's mark at the
    same end unless tt / jt names what they face."""
    out = {}
    ts, te = t
    js, je = j
    tgt_t = (tt or (js if js is not HID else J_LAST[0]), tt or (je if je is not HID else J_LAST[1]))
    tgt_j = (jt or (ts if ts is not HID else T_LAST[0]), jt or (te if te is not HID else T_LAST[1]))
    if not (ts is HID and te is HID):
        out["terra"] = {"start": mk(ts, tgt_t[0]), "end": mk(te, tgt_t[1])}
    if not (js is HID and je is HID):
        out["jester"] = {"start": mk(js, tgt_j[0]), "end": mk(je, tgt_j[1])}
    return out


# where the other one is while out of the picture (what an unseen opponent's facing is aimed at); set per shot
T_LAST, J_LAST = [T1, T1], [J0, J0]

# ------------------------------------------------------------------------------------------------ the script
SCRIPT = """# THE EMBER THIEF

*Terra and the jester - one minute, twenty shots. Written 2026-10-05 before a frame was drawn.*

**The story in one line.** The jester has stolen Terra's ember pendant - a small stone that glows like a live
coal, the one thing she always wears - and she wants it back.

**Who.** TERRA: a young woman with long wavy sea-green hair, a red dress and red boots; she fights with fire.
THE JESTER: lanky, chalk-white grin, a purple-and-yellow diamond costume and a two-horned cap; a trickster who
fights with glowing purple orbs, flips and vanishing tricks, and never stops laughing.

**Where.** A forest clearing ringed by old standing stones, at dusk. A great mossy boulder on its north side.

**The rule of the camera.** Terra comes from the south, the jester waits in the north, and every camera stands
on the east side of the line between them: Terra is always on the LEFT of the screen and attacks to the right;
the jester is always on the RIGHT and attacks to the left. Where a shot ends is where the next one begins.

## Act one - the theft (0:00-0:12)

1. **010 - wide, 4 s.** Dusk. Terra walks up the path into the clearing. Across it, in front of the great
   boulder, the jester stands waiting, lazily swinging something on a chain. It glows like a coal.
2. **020 - close, 2 s.** Terra stops. Her hand flies to her throat: bare. Her pendant is gone. Her eyes narrow
   and sparks crackle around her fingers. *(She has seen what he is swinging.)*
3. **030 - medium, 3 s.** The jester giggles, dangles her pendant in front of his grin, loops the chain over
   his own head so it hangs on his chest, and beckons with one curling finger: come and get it.

## Act two - the fight (0:12-0:35)

4. **040 - wide, side, 3 s.** She charges, flames streaming from her fists. He springs into a flying
   somersault toward her and lands right in front of her.
5. **050 - medium, side, 3 s.** She throws a flaming hook at his face; he bends backward like a reed and the
   fist sweeps over his nose; he snaps back upright, grinning.
6. **060 - medium, side, 3 s.** His palm flares purple. He drives it into her shoulder - a white flash - and she
   is blasted backward, boots gouging the grass, sliding to a stop crouched. *(He is better at this than she is.)*
7. **070 - close, low, 2 s.** She lifts her head, wipes her mouth with her wrist, rises - and both fists burst
   into roaring flame. *(Now she is angry.)*
8. **080 - wide, 3 s.** Three fireballs. He cartwheels past the first, flips over the second - the third flies
   past him and blows the great boulder apart in fire and flying rock.
9. **090 - medium, 3 s.** Out of the smoke where the boulder was, he straightens, coughs out a puff of soot,
   laughs. Three purple orbs blink into being over his palm; he juggles them, then flicks them at her.
10. **100 - medium, side, 3 s.** She bats the first orb aside with a flaming forearm, ducks the second; the third
    bursts at her feet and throws her into a backward roll. *(He is winning.)*

## Act three - the turn (0:35-0:51)

11. **110 - low, 4 s.** She springs up out of the roll - and a puff of purple smoke bursts right in front of
    her: the jester leaps out of it, kicking at her head. She ducks the kick and drives a flaming uppercut into
    his chest. The chain snaps; the pendant flips up into the air.
12. **120 - insert, the sky, 2 s.** The glowing pendant spins up into the evening sky, trailing sparks and its
    broken chain.
13. **130 - wide, side, 3 s.** Both look up. He springs straight up after it, purple aura blazing, out of the
    top of the frame. She jumps too - far short - and lands, staring up.
14. **140 - looking up, 2 s.** Against the sky he snatches the pendant at the top of his leap and cackles.
15. **150 - close, 2 s.** Below, Terra raises her open hand toward it. Her eyes blaze orange. *(It is her
    pendant, and its fire is hers.)*
16. **160 - medium, 3 s.** He lands - and the pendant in his fist blazes white-hot. Smoke pours from his glove;
    he yelps, juggles it hand to hand like a hot coal and flings it away.
17. **170 - medium, 2 s.** The pendant arcs down into Terra's open palm. Her fingers close around it; light
    glows between them.

## Act four - the end (0:51-1:02)

18. **180 - wide, side, 4 s.** She holds the pendant to her chest and thrusts her other palm forward: a roaring
    torrent of fire crosses the clearing, sweeps him off his feet and hurls him tumbling out into the trees.
19. **190 - medium, 3 s.** At the forest edge he staggers out between the trunks, scorched black, cap
    smouldering; pats out a flame on his sleeve, grins, sweeps off his cap in a deep bow - and vanishes in a
    puff of purple smoke and confetti.
20. **200 - medium, 4 s.** Terra opens her hand. The pendant glows warm in her palm. She fastens it around her
    neck, looks toward the trees where he vanished, breathes out, and smiles as leaves drift down in the last
    light.
"""

# id, name, frames, camera, words (style, beats), sound, (terra start, end), (jester start, end), facing overrides,
# live physics, why the marks jump here (or ""), the story note for the page
S = []


def shot(sid, name, frames, cam, style, beat, sound, t, j, live=(), jump="", note="", tt=None, jt=None):
    S.append(dict(sid=sid, name=name, frames=frames, cam=cam, style=style, beat=beat, sound=sound, t=t, j=j,
                  live=list(live), jump=jump, note=note, tt=tt, jt=jt))


shot("010", "the thief", 105,
     {"cam": [2.2, 16.6, 1.25], "cam_to": [2.1, 17.6, 1.25], "look": [2.0, 30.0, 1.7], "look_to": [2.0, 30.0, 1.65],
      "lens": 26},
     "", "Wide and low, from behind %s as she walks up the path into a clearing ringed by old standing stones and "
         "stops. Across the clearing, in front of a great mossy boulder, %s stands waiting, lazily swinging %s back "
         "and forth, its glow flickering. Leaves drift down through shafts of late sunlight. The camera pushes in "
         "slowly." % (HER, HIM, PEND),
     "wind in the trees, her footsteps on dry leaves, the faint tinkle of a chain, a soft giggle",
     (T0, T1), (J0, J0), live=[{"ev": "leafrain", "at": [1.5, 27.5], "f": 20, "n": 50, "radius": 7.0}],
     note="She arrives; he is waiting for her with something that glows. Cuts to her face (020).")
shot("020", "her pendant", 57,
     {"cam": [2.4, 23.6, 1.5], "look": [0.8, 22.4, 1.48], "lens": 55},
     "", "Close on %s: (1) she stops, staring to the right; (2) her hand flies up to her bare throat - her pendant "
         "is gone; (3) her eyes narrow and a few sparks crackle around her fingers." % HER,
     "a sharp breath, crackling sparks",
     (T1, T1), (HID, HID),
     note="She realises the glowing thing is HER pendant. Her look to the right cuts to him (030).")
shot("030", "come and get it", 73,
     {"cam": [4.8, 30.0, 1.6], "look": [3.2, 33.0, 1.6], "lens": 40},
     "", "Medium shot on %s in front of a great mossy boulder: (1) he dangles %s in front of his wide grin and "
         "giggles; (2) he loops the chain over his own head so the glowing pendant hangs on his chest; (3) he curls "
         "one finger toward the left, beckoning: come and get it." % (HIM, PEND),
     "a mocking giggle, the clink of a chain",
     (HID, HID), (J0, J0),
     note="The provocation: he wears her pendant and dares her. Cuts to her charge (040).")
shot("040", "the charge", 73,
     {"cam": [6.9, 26.6, 1.3], "look": [1.6, 25.4, 1.3], "look_to": [1.6, 27.6, 1.35], "lens": 22},
     MOVE, "Wide side view across the clearing, the camera panning right with her: (1) %s breaks into a sprint toward "
           "the right, flames streaming from both her fists; (2) %s comes flying in from the right in a somersault, "
           "a glowing pendant swinging on his chest; (3) he lands lightly on his feet right in front of her and they "
           "face each other, a few steps apart." % (HER, HIM),
     "running footsteps, the roar of flames, a whoosh, a light landing",
     (T1, T2), (HID, J1), jump="jester: somersaults in from out of the picture",
     note="She answers the dare; he meets her halfway. They end face to face where 050 begins.")
shot("050", "the hook", 73,
     {"cam": [4.4, 27.6, 1.25], "look": [1.55, 27.5, 1.3], "lens": 30},
     MOVE, "Medium side view, the two of them face to face, she on the left, he on the right: (1) %s throws a "
           "flaming right hook at his face; (2) %s bends far backward from the knees like a reed and her burning "
           "fist sweeps just over his nose; (3) he springs back upright, grinning, the glowing pendant bouncing on "
           "his chest." % (HER, HIM),
     "the roar of a flaming punch, a whoosh, his giggle",
     (T2, T3), (J1, J2),
     note="Her first blow misses - he is too quick. His grin sets up the counter (060).")
shot("060", "his counter", 73,
     {"cam": [5.6, 26.3, 1.2], "look": [1.4, 26.3, 1.2], "lens": 24},
     FIGHT, "Medium side view, she on the left, he on the right: (1) the right palm of %s flares with purple light "
            "and he drives it into her shoulder with a white flash of impact; (2) %s is blasted backward to the "
            "left, her boots skidding and gouging two furrows in the grass; (3) she skids to a stop, still on her feet, "
            "and straightens up." % (HIM, HER),
     "a crackling burst, a heavy impact, boots scraping across earth",
     (T3, T4), (J2, J2), live=[{"ev": "shock", "at": [1.0, 24.6], "f": 52, "n": 24, "radius": 1.4}],
     note="He hits back and she is thrown. She ends on her feet at the spot 070 starts on.")
shot("070", "now she is angry", 57,
     {"cam": [2.4, 25.6, 0.95], "look": [1.0, 24.4, 1.15], "lens": 45},
     "", "Low close-up on %s: (1) breathing hard, she glares to the right; (2) she wipes her mouth with the back of "
         "her wrist; (3) both her fists burst into roaring orange flames." % HER,
     "a low breath, the whoosh of igniting fire",
     (T4, T4), (HID, HID),
     note="The turn of act two: she stops playing. Her burning fists lead straight into the fireballs (080).")
shot("080", "the boulder", 73,
     {"cam": [2.8, 20.4, 1.6], "look": [2.4, 30.4, 1.35], "lens": 34},
     FIGHT, "Wide, from behind %s on the left, %s ahead of her on the right with a great mossy boulder behind him: "
            "(1) she hurls a fireball from her right hand and he cartwheels aside; (2) she hurls another from her "
            "left hand and he flips over it; (3) the third streaks past him into the great boulder, which explodes "
            "in a burst of fire and flying rock." % (HER, HIM),
     "three fiery whooshes, a thunderous explosion, rocks crashing down",
     (T4, T4), (J2, J3), live=[{"ev": "shatter", "f": 50, "from_az": 196}],
     note="Her answer - and he dodges all three. The wrecked boulder stays wrecked from here on.")
shot("090", "out of the smoke", 73,
     {"cam": [4.6, 27.2, 1.5], "look": [2.7, 29.6, 1.6], "lens": 40},
     MOVE, "Medium on %s, smoke and dust drifting past behind him where the boulder was: (1) he straightens up, "
           "coughs out a puff of soot and laughs; (2) three glowing purple orbs blink into being above his palm and "
           "he juggles them; (3) he flicks them one after another to the left, toward her." % HIM,
     "coughing, a cackle, a rising electric hum, three whooshes",
     (HID, HID), (J3, J3),
     note="Unhurt and laughing: his magic now. The orbs fly left into 100.")
shot("100", "his orbs", 73,
     {"cam": [3.8, 24.0, 1.15], "look": [1.0, 24.2, 1.0], "lens": 30},
     FIGHT, "Medium side view on %s, facing right: (1) a small glowing purple orb, the size of a fist, streaks in "
            "from the right and she bats it aside with a flaming forearm in a shower of sparks; (2) she ducks under the second orb; (3) the "
            "third bursts against the ground at her feet in a white flash and the blast throws her into a backward "
            "roll to the left; she comes up on her feet again." % HER,
     "a crackling impact, a whoosh, an explosion, her body rolling over earth",
     (T4, T5), (HID, HID), live=[{"ev": "shock", "at": [1.0, 24.6], "f": 46, "n": 40, "radius": 2.0}],
     note="He is winning. She ends thrown back, just back on her feet - where 110 picks her up.")
shot("110", "the uppercut", 105,
     {"cam": [3.7, 23.3, 0.7], "look": [0.95, 23.45, 1.15], "lens": 28},
     FIGHT, "Low side view, she on the left, he on the right: (1) %s, just back on her feet, braces herself; (2) a "
            "puff of purple smoke bursts right in front of her and %s leaps out of it, swinging a high kick at her "
            "head from the right; (3) she ducks under the kick; (4) she drives a flaming uppercut into his chest "
            "with a white flash - the chain around his neck snaps and the glowing pendant flips up into the air." % (HER, HIM),
     "a pop of smoke, a whoosh, a crunching impact, a snapping chain, a startled yelp",
     (T5, T6), (HID, J4), jump="jester: out of a puff of smoke (his vanishing trick)",
     note="The turn: his trick, her counter - and the pendant is free. It flies up into 120.")
shot("120", "the pendant flies", 57,
     {"cam": [2.2, 23.4, 1.0], "look": [1.2, 25.4, 6.5], "lens": 28},
     "", "Looking straight up into the evening sky ringed by treetops: %s spins upward through the frame, trailing "
         "sparks and its broken chain, slows at the top of its arc and hangs there for a moment." % PEND,
     "a soft whistling spin, a faint chime",
     (HID, HID), (HID, HID),
     note="Everything stops for the pendant. Both of them look up at it in 130.")
shot("130", "the leap", 73,
     {"cam": [6.2, 24.2, 1.1], "look": [1.1, 24.3, 2.0], "lens": 24},
     MOVE, "Wide side view, she on the left, he on the right, both looking up: (1) %s staggers back a step from her "
           "blow, then crouches and leaps straight up into the air, his whole body clearly visible as he rises high "
           "above her, arms reaching up, a thin purple glow around him; (2) %s leaps after him a moment later, but "
           "falls far short and lands, staring up at him." % (HIM, HER),
     "a rushing leap, a crackling aura, a thud of landing",
     (T6, T6), (J4, J4air), live=[{"ev": "shock", "at": [1.0, 23.95], "f": 18, "n": 26, "radius": 1.4}],
     note="A race for it - and he is faster: he ends high in the air above her, still rising into 140.")
shot("140", "he catches it", 57,
     {"cam": [4.4, 22.9, 1.4], "look": [1.0, 23.95, 5.15], "lens": 45},
     MOVE, "Looking up into the evening sky: (1) %s shoots up into the frame from below, trailing a purple aura; "
           "(2) at the top of his leap he snatches the spinning glowing pendant out of the air; (3) he cackles, "
           "holding it up in his fist." % HIM,
     "a rushing whoosh, a clink, a cackle echoing",
     (HID, HID), (HID, J5), jump="", jt=T6,
     note="He has it again. But below him (150) she does not chase - she calls it.")
shot("150", "she calls it", 57,
     {"cam": [2.1, 24.1, 1.38], "look": [0.85, 23.0, 1.45], "lens": 50},
     "", "Close on %s, looking up to the right at him: (1) she raises her open right hand toward the sky; (2) her "
         "eyes blaze orange and the air above her palm ripples with heat; (3) a warm glow spreads through her "
         "fingers." % HER,
     "a deep rising hum, crackling heat",
     (T6, T6), (HID, HID), tt=J4,
     note="The idea that wins the fight: the pendant's fire answers her. 160 shows what it does to him.")
shot("160", "too hot to hold", 73,
     {"cam": [3.0, 22.6, 1.4], "look": [1.0, 23.95, 1.45], "lens": 36},
     MOVE, "Medium on %s: (1) he drops down into the frame and lands lightly, the glowing pendant clutched in his "
           "fist; (2) the pendant blazes white-hot and smoke pours from his glove; (3) he yelps, juggles it "
           "frantically from hand to hand like a hot coal and flings it away to the left." % HIM,
     "a light landing, a sizzle, a yelp, frantic juggling",
     (HID, HID), (HID, J4), jump="jester: drops in from above the picture",
     note="Her fire burns him through her own pendant; he throws it away - to the left, to her (170).")
shot("170", "back in her hand", 57,
     {"cam": [2.4, 22.4, 1.4], "look": [0.85, 23.0, 1.45], "lens": 40},
     "", "Medium on %s, her right hand raised and open: (1) the glowing pendant arcs in from the right and drops "
         "into her palm; (2) her fingers close around it and warm light glows between them; (3) she looks to the "
         "right, fierce." % HER,
     "a soft chime, a warm crackle",
     (T6, T6), (HID, HID),
     note="She has it back. Now she can answer him properly (180).")
shot("180", "the torrent", 105,
     {"cam": [6.4, 24.6, 1.3], "look": [1.2, 25.4, 1.6], "lens": 22},
     FIGHT, "Wide side view, she on the left, he on the right: (1) %s clutches the glowing pendant to her chest with "
            "one hand and thrusts her other palm toward him; (2) a roaring torrent of fire bursts from her palm "
            "across the clearing to the right; (3) it engulfs %s and sweeps him off his feet, tumbling head over "
            "heels away to the right, out of the clearing into the trees; (4) leaves and embers rain down as the "
            "fire dies." % (HER, HIM),
     "a roaring blast of fire, a yelp fading away, crashing branches, crackling embers",
     (T6, T7), (J4, HID), live=[{"ev": "shock", "at": [1.0, 24.2], "f": 40, "n": 40, "radius": 2.5},
                                {"ev": "leafrain", "at": [1.2, 36.0], "f": 70, "n": 60, "radius": 5.0}],
     note="The finish. He is blown out of the clearing - to the north, where 190 finds him.")
shot("190", "the bow", 73,
     {"cam": [2.6, 34.4, 1.5], "look": [1.0, 37.6, 1.5], "lens": 38},
     "", "Medium shot at the edge of the forest: (1) %s staggers out from between the tree trunks, scorched black, "
         "smoke curling from his smouldering cap; (2) he pats out a flame on his sleeve and grins sheepishly; (3) he "
         "sweeps off his cap in a deep bow and bursts into a puff of purple smoke and confetti - gone." % HIM,
     "crunching leaves, a cough, a chuckle, a pop, fluttering confetti",
     (HID, HID), (J7, HID), live=[{"ev": "leafrain", "at": [1.0, 38.2], "f": 58, "n": 40, "radius": 1.6}],
     jump="jester: blown out of the clearing to the forest edge (180)",
     note="A good loser, and still a trickster: he bows and vanishes. 200 returns to her.")
shot("200", "the pendant", 105,
     {"cam": [2.6, 26.2, 1.45], "cam_to": [1.95, 25.1, 1.45], "look": [0.9, 23.3, 1.3], "look_to": [0.9, 23.3, 1.38],
      "lens": 35},
     "", "Medium shot on %s in the clearing as the light fades, the camera pushing in slowly to her face: (1) she opens her hand and the pendant glows warm in "
         "her palm; (2) she fastens it around her neck; (3) she looks off to the right toward the trees where he "
         "vanished, breathes out, and smiles as leaves drift down around her." % HER,
     "a soft breath, the clasp of a chain, wind in the leaves, a distant bird",
     (T7, T7), (HID, HID), tt=J7, live=[{"ev": "leafrain", "at": [0.9, 23.3], "f": 6, "n": 36, "radius": 4.0}],
     note="The pendant is home. The end.")


# ------------------------------------------------------------------------------------------- the key poses
# LTX_PLAYBOOK §100.10: a blow that must land is painted into its own frame (Qwen edit, set_test.py key) and
# anchored where it lands (MiniMaxH3AddGuide); the beat list stays the words. "seed" is set after looking at
# keys_<id>/keys.jpg (studio/samples/fight/ember-thief/).
KEEP = (" Both stay where they stand in the picture, the same size. Everything else - the clearing, the trees, the "
        "light, both of their costumes, faces and colours - stays exactly as it is; same camera, same framing.")
FLASH = ("Edit <image1>: a white flash of impact bursts at the point of contact, with short white speed lines around "
         "it. Everything else stays exactly as it is; same camera, same framing.")
KEYS = {
    "050": [{"at": 30, "from": "end",
             "pose": "Edit <image1>: the young woman with sea-green hair throws a flaming right hook, her right arm "
                     "fully extended toward the jester's face in a trail of fire; the harlequin jester bends far "
                     "backward from the knees, his back arched like a reed, and her burning fist sweeps just over his "
                     "face. She stays side-on, facing right; he faces left." + KEEP, "seed": 202}],
    "060": [{"at": 14, "from": "start",
             "pose": "Edit <image1>: the harlequin jester lunges forward and drives his open right palm, glowing with "
                     "purple light, into the shoulder of the young woman with sea-green hair, his long arm fully "
                     "extended to the left; she recoils, knocked off balance to the left. She faces right; he faces "
                     "left." + KEEP,
             # seed 202 kept the look but drew him twice - lunging, and still standing where he was: the copy goes
             "fx": [FLASH, "Edit <image1>: remove the second harlequin jester, the one standing still at the far right "
                           "of the picture, and fill in the forest behind where he stood. The jester lunging forward "
                           "with his arm stretched out to the woman stays exactly as he is; everything else stays "
                           "exactly as it is; same camera, same framing."], "seed": 202}],
    "140": [{"at": "end", "from": "end",
             "pose": "Edit <image1>: the harlequin jester at the top of his leap high in the evening sky, one fist "
                     "raised above his head holding a small glowing pendant on a broken gold chain, his other arm "
                     "flung out, his knees tucked up, cackling, a purple aura flaring around him. His face, costume "
                     "and colours stay exactly as they are; the sky, the treetops and the light stay exactly as "
                     "they are; same camera, same framing.", "seed": 11}],
    "110": [{"at": "end", "from": "end",
             "pose": "Edit <image1>: the young woman with sea-green hair drives a flaming uppercut into the chest of "
                     "the harlequin jester: her right fist, wreathed in fire, strikes his chest, her arm driving "
                     "upward, her knees bent; he is lifted onto his toes, doubled over her fist, mouth open in shock; "
                     "the thin gold chain around his neck snaps and a small glowing pendant flies up into the air "
                     "above them. She faces right; he faces left." + KEEP, "fx": FLASH, "seed": 11}],
}


# ------------------------------------------------------------------------------------------------ the checks
def _cam_basis(cam, look):
    c = [float(v) for v in cam]
    f = [look[i] - c[i] for i in range(3)]
    n = math.sqrt(sum(v * v for v in f))
    f = [v / n for v in f]
    r = [f[1], -f[0], 0.0]                          # forward x up
    rn = math.hypot(r[0], r[1]) or 1.0
    r = [r[0] / rn, r[1] / rn, 0.0]
    u = [r[1] * f[2] - r[2] * f[1], r[2] * f[0] - r[0] * f[2], r[0] * f[1] - r[1] * f[0]]
    return c, f, r, u


def _proj(cam, look, lens, p, w=1280, h=720):
    c, f, r, u = _cam_basis(cam, look)
    d = [p[i] - c[i] for i in range(3)]
    z = sum(d[i] * f[i] for i in range(3))
    if z <= 0.05:
        return None
    k = lens / 36.0 * w
    return (w / 2 + sum(d[i] * r[i] for i in range(3)) / z * k, h / 2 - sum(d[i] * u[i] for i in range(3)) / z * k)


def check(shots, acts):
    """Every frame the set draws: the camera east of the line (she left, he right), each of them inside the
    picture, each facing the other on screen; the marks chained from shot to shot."""
    bad = []
    last = {}
    heights = {"terra": 1.62, "jester": 1.88}
    rows = []
    for sh in shots:
        sid, pz = sh["id"], sh["previz"]
        figs = acts[sid]["figures"]
        for tag in ("start", "end"):
            cam = pz.get("cam_to") if tag == "end" and pz.get("cam_to") else pz["cam"]
            look = pz.get("look_to") if tag == "end" and pz.get("look_to") else pz["look"]
            c, f, r, u = _cam_basis(cam, look)
            # the line: from where she is (or was) to where he is (or was)
            tp = (figs.get("terra", {}).get(tag) or {}).get("at") or LINE[sid][tag][0]
            jp = (figs.get("jester", {}).get(tag) or {}).get("at") or LINE[sid][tag][1]
            v, w = (jp[0] - tp[0], jp[1] - tp[1]), (c[0] - tp[0], c[1] - tp[1])
            side = v[0] * w[1] - v[1] * w[0]
            if side >= 0:
                bad.append("%s %s: the camera is WEST of the line - she would be on the right" % (sid, tag))
            desc = []
            for who in ("terra", "jester"):
                m = figs.get(who, {}).get(tag) or {}
                if m.get("hidden") or "at" not in m:
                    continue
                at = list(m["at"]) + [0.0] * (3 - len(m["at"]))
                feet = _proj(cam, look, pz["lens"], at)
                head = _proj(cam, look, pz["lens"], (at[0], at[1], at[2] + heights[who]))
                if feet is None or head is None:
                    bad.append("%s %s: %s is BEHIND the camera" % (sid, tag, who))
                    continue
                cx = (feet[0] + head[0]) / 2
                tall = feet[1] - head[1]
                if cx < 20 or cx > 1260 or head[1] > 700 or feet[1] < 20:
                    bad.append("%s %s: %s out of the picture (x %.0f, head %.0f, feet %.0f)" % (sid, tag, who, cx,
                                                                                                 head[1], feet[1]))
                to = m["to"]
                fx, fy = to[0] - at[0], to[1] - at[1]
                n = math.hypot(fx, fy) or 1.0
                onscreen = (fx * r[0] + fy * r[1]) / n            # + faces screen-right
                want = 1 if who == "terra" else -1
                if onscreen * want < -0.2:
                    bad.append("%s %s: %s faces screen-%s (should face %s)" % (
                        sid, tag, who, "right" if onscreen > 0 else "left", "right" if want > 0 else "left"))
                # the view the cast will paste (set_test.py VIEWS8): seen from behind is a fault on any shot that
                # is not over that character's shoulder (ember-thief 160 first drew the jester from behind)
                face = math.degrees(math.atan2(fx, fy))
                rel = (math.degrees(math.atan2(c[0] - at[0], c[1] - at[1])) - face + 540) % 360 - 180
                view = "back" if abs(rel) > 112.5 else "side" if abs(rel) > 67.5 else "3/4" if abs(rel) > 22.5 else "front"
                if view == "back" and sid not in OVER_SHOULDER.get(who, ()):
                    bad.append("%s %s: %s is seen from BEHIND (camera %+.0f deg from his/her front)" % (sid, tag, who, rel))
                desc.append("%s x%4.0f %4.0fpx %s %s" % (who[0].upper(), cx, tall,
                                                         "->" if onscreen > 0.2 else "<-" if onscreen < -0.2 else "^^", view))
                # the chain: a start mark is where the last shot left them, unless the story moves them
                if tag == "start" and who in last and math.dist(last[who][:2], at[:2]) > 0.05 and \
                        who not in (sh.get("_jump") or ""):
                    bad.append("%s: %s starts at %s but the last shot left her/him at %s" % (sid, who, at[:2],
                                                                                              last[who][:2]))
                if tag == "end":
                    last[who] = at
            rows.append("  %s %-5s %s" % (sid, tag, " | ".join(desc) or "(nobody)"))
    return rows, bad


LINE = {}
# shots that look over a character's shoulder on purpose: a back view of them is wanted there
OVER_SHOULDER = {"terra": ("010", "080")}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--check-only", action="store_true")
    a = ap.parse_args()
    global T_LAST, J_LAST
    film = {
        "_comment": "THE EMBER THIEF (2026-10-05): a story written before it was shot, frames first in the clearing "
                    "set, one line of action. See _make_ember_thief_1005.py and ember-thief.md.",
        "film": FILM, "title": "THE EMBER THIEF", "subtitle": "Terra and the jester",
        "logline": "The jester has stolen Terra's ember pendant, and she wants it back.",
        "grade": GRADE, "avoid": AVOID, "realism": "", "style": "shon",
        "score_tags": "picked by ear (craft/SOUND.md section 0) - none yet",
        "place": {"id": "clearing", "prompt": "A forest clearing ringed by huge trees and standing stones, painted as an "
                                              "anime background."},
        "cast": {"terra": {"role": "Terra", "prompt": "Terra: her character sheet (studio/sheets/terra-in-the-plaza-terra)."},
                 "jester": {"role": "the jester", "prompt": "The jester: his character sheet (studio/sheets/forest-fight-the-jester)."}},
        "shots": [],
    }
    acts, done = {}, []
    tpos, jpos = T0, J0                    # where each of them is, seen or not
    for k, x in enumerate(S):
        sid = x["sid"]
        ts, te = x["t"]
        js, je = x["j"]
        T_LAST = [ts if ts is not HID else tpos, te if te is not HID else (ts if ts is not HID else tpos)]
        J_LAST = [js if js is not HID else jpos, je if je is not HID else (js if js is not HID else jpos)]
        figs = F(x["t"], x["j"], tt=x["tt"], jt=x["jt"])
        LINE[sid] = {"start": (T_LAST[0], J_LAST[0]), "end": (T_LAST[1], J_LAST[1])}
        tpos, jpos = T_LAST[1], J_LAST[1]
        pz = {"scene": "set", "set": "duel", "action": "duel:%s:%s" % (FILM, sid), "frames": x["frames"],
              "masks": 8, "endpoints": 1, "dress": DRESS, "dress_place": DRESS, "grade": GRADE}
        pz.update(x["cam"])
        prompt = ("2D anime, hand-drawn cel animation. " + x["style"] + x["beat"] + STAY + " Sound: " + x["sound"] +
                  ". No music.")
        prev = S[k - 1]["sid"] if k else None
        nxt = S[k + 1]["sid"] if k + 1 < len(S) else None
        note = "%s (shot %d of %d%s%s)" % (x["note"], k + 1, len(S), ", after %s" % prev if prev else "",
                                           ", before %s" % nxt if nxt else "")
        film["shots"].append({"id": sid, "name": x["name"], "title": x["name"], "secs": round(x["frames"] / 24.0, 2),
                              "face": "none", "engine": "h3f", "refs": ["clearing", "terra", "jester"],
                              "anchor": None, "prompt": prompt, "avoid_extra": OTHERS, "note": note, "previz": pz,
                              "_jump": x["jump"]})
        if sid in KEYS:
            film["shots"][-1]["keys"] = KEYS[sid]
        acts[sid] = {"figures": figs, "done": list(done), "live": x["live"]}
        done += x["live"]
    rows, bad = check(film["shots"], acts)
    print("\n".join(rows))
    for sh in film["shots"]:
        sh.pop("_jump", None)
    runtime = sum(s["secs"] for s in film["shots"])
    print("%d shots, %.1f s" % (len(film["shots"]), runtime))
    if bad:
        print("CHECK FAILED:\n  " + "\n  ".join(bad))
        if not a.force:
            sys.exit(1)
    else:
        print("check: every camera east of the line, everyone in the picture and facing the other, marks chained")
    if a.check_only:
        return
    for name, obj in ((FILM + ".json", film), (FILM + ".acts.json", acts)):
        p = os.path.join(DST, name)
        json.dump(obj, open(p, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
        print("%s -> %s" % (name, p))
    open(os.path.join(DST, FILM + ".md"), "w", encoding="utf-8").write(SCRIPT)
    print("script -> %s" % os.path.join(DST, FILM + ".md"))


if __name__ == "__main__":
    main()
