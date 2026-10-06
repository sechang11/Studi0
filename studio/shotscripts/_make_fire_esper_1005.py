#!/usr/bin/env python3
"""THE FIRE ESPER (2026-10-05): one moment - Terra summons a fire esper - told as a RELAY of shots.

The director, after THE EMBER THIEF: "the fighting sequence still has many moves that don't connect with one
another... try a multi-shot sequence where terra is using a hand praying incantation and magic energy circles
her... powering up her mana to channel into a magical fire spell - a demonic esper spirit that comes out to fight
[the jester]... flames, a small comet, pillars through the ground, breaking the forest into a volcanic warzone...
each shot prior has to tell a story leading up to the next shot".

A RELAY (LTX_PLAYBOOK §101): one story moment carried through a chain of shots like a baton. Every shot is a LEG
of one of five kinds, and covers a window of STORY time (written t 9-12):
  advance  story time moves on (0-3, 3-4, 4-6)
  echo     the same moment again from another angle - the same story time - for emphasis
  answer   the other side reacts (his face, his step back)
  breath   a cutaway that lets time pass (birds, wind, an overview)
  reveal   the payoff from the angle that shows it best
Every leg hands the next one a BATON (a look, a sound, a motion, an object, a light), and every cut is held by
GLUE (§102): a sound that runs through it, an object that stays while the rest changes, a flash, a dissolve.

Frames first in the clearing of set_duel.py, as THE EMBER THIEF: one line of action (Terra and the esper south,
the jester north, every camera east of the line), marks chained, facing checked - and the place's STATE
progresses shot by shot through the dress (dusk -> a sky turning red -> burning -> a volcanic warzone).
Writes studio/shotscripts/fire-esper.json, .acts.json and .md (the script). The cut's glue (fire-esper.cut.json for
studio/_tools/glue_cut.py) is written after the takes, from each shot's "glue" - it needs the takes' timing.
    python3 studio/shotscripts/_make_fire_esper_1005.py [--check-only]
"""
import argparse
import json
import math
import os
import sys

ROOT = os.path.expanduser("~/shared/comfy-studio")
DST = os.path.join(ROOT, "studio", "shotscripts")
FILM = "fire-esper"

GRADE = ("2D anime film, hand-drawn cel animation, painted backgrounds, a forest clearing at dusk, shafts of low "
         "sunlight, drifting mist.")
AVOID = ("lowres, blurry, morphing, warping, melting, flicker, deformed hands, extra fingers, extra limbs, two of the "
         "same person, subtitles, captions, watermark, nsfw")
OTHERS = "3d render, cgi, photorealistic, live action, a crowd, other people, blood, gore"
HER = "the young woman with long wavy sea-green hair, a red dress and red boots"
HIM = "the lanky harlequin jester in a purple-and-yellow diamond costume and two-horned cap"
ESPER = ("the fire esper - a towering horned demon of living flame, its dark obsidian skin cracked with glowing lava "
         "veins, a mane of fire, glowing white-gold eyes")
BIG = "the towering fire demon"

_D = ("Turn <image1> into a frame from a hand-drawn 2D anime film: a forest clearing ringed by huge dark trees and old "
      "standing stones, painted as an anime background, clean line art, flat cel shading, %s Keep the camera, the "
      "lens, the framing, the perspective and the layout of <image1> exactly: everything in it stays exactly where it "
      "is, at the same size; add nothing and remove nothing.")
# the place's STATE through the relay - the same set, dressed further each time
PLACE = {
    "dusk": _D % "shafts of late sunlight falling into the clearing, drifting mist at its edges.",
    "red": _D % "the sky above it turning blood red, an orange glow on the trunks, embers drifting in the air.",
    "burning": _D % "the trees at its edge on fire, the ground scorched and cracked with glowing seams, smoke under a "
                     "blood-red sky.",
    "volcanic": _D % "turned into a volcanic warzone: the ground split into glowing rivers of lava, trees burning and "
                      "fallen, ash falling like snow, columns of black smoke rising into a blood-red sky.",
}
MAGIC = ("A summoning in the manner of a 90s fantasy anime - glowing runes, swirling embers, rays of light, the air "
         "shimmering with heat. ")
FIGHT = ("Battle in the manner of a 90s shonen fantasy anime - roaring flames, speed lines, a white impact frame on "
         "every blast. ")
STAY = " The clearing, the trees, the standing stones and the light stay as they are."
# KEY POSES (set_test.py key): the cast draws everyone standing, arms down - the prayer is painted in
KEEP = (" Her face, hair, dress and colours stay exactly as they are; the forest and the sky stay exactly as they are; "
        "same camera, same framing.")
PRAYING = ("Edit <image1>: the young woman with sea-green hair stands with her eyes closed and her palms pressed "
           "together in front of her chest in prayer, her fingers pointing up." + KEEP)

# ---------------------------------------------------------------------------------------------- the marks
T = (0.9, 23.2)                                    # she never leaves her circle of runes
E = (0.8, 19.6)                                    # the esper rises behind her
J0, J1, J2, J3 = (1.3, 29.4), (2.4, 31.2), (3.0, 33.4), (2.6, 32.2)
HID = None
HEIGHT = {"terra": 1.62, "jester": 1.88, "esper": 6.5}

SCRIPT = """# THE FIRE ESPER

*Terra and the jester - one moment told as a relay of shots. Written 2026-10-05 before a frame was drawn.*

**The moment.** Losing to the jester, Terra stops fighting and starts praying - and something answers: a fire
esper, a towering horned demon of living flame, that hunts him across the clearing and turns the forest into a
volcanic warzone.

**How it is told: a relay.** The one moment is passed from shot to shot like a baton. Each shot is a LEG -
*advance* (story time moves on), *echo* (the same moment from another angle), *answer* (the other side reacts),
*breath* (a cutaway while time passes), *reveal* (the payoff) - and covers a window of story time (t, seconds).
Every cut is held by GLUE: a sound that runs through it, an object that stays, a flash, a dissolve.

**The camera rule** (as THE EMBER THIEF): Terra - and the esper behind her - on the LEFT of the screen; the
jester on the RIGHT; every camera east of the line between them.

## Leg 1 - the prayer (t 0-21)

1. **010 · breath · t 0-4 · wide.** Dusk in the clearing. The jester juggles three purple orbs, laughing. Terra,
   bruised and breathing hard, takes a step back. *Glue: the wind and his laugh run on under the cut.*
2. **020 · advance · t 4-7 · medium.** She closes her eyes and presses her palms together - a prayer. Her lips
   move. *Glue: her whisper runs on under the next shot.*
3. **030 · answer · t 6-9 · medium.** He catches his orbs, tilts his head, amused - and his eyes drop to her feet.
   *Baton: his look down.*
4. **040 · advance · t 9-12 · at ground level.** A circle of glowing runes ignites around her boots and begins to
   turn; embers lift. *Glue: the circle itself.*
5. **050 · echo · t 9-12 · from above.** The same moment from high above: the circle turning round her, embers
   spiralling up, her hair beginning to lift. *Glue: embers that keep drifting through every cut from here.*
6. **060 · advance · t 12-15 · close.** Her face lit from below, eyes closed, whispering; her hair floats.
   *Glue: a deep rumble rises under the cut.*
7. **070 · breath · t 15-19 · the treetops.** Birds burst from the trees and flee under a sky turning red; the
   ground trembles. *Glue: the bird cries run on.*
8. **080 · answer · t 19-21 · close.** His grin falters. The orbs in his hand flicker out. He swallows.
   *Glue: a flash.*

## Leg 2 - the summoning (t 21-30)

9. **090 · advance · t 21-24 · medium.** Her eyes snap open, glowing orange. She drops to one knee and slams her
   joined hands onto the ground - the circle erupts into a column of fire - and she rises again, palms together.
   *Glue: the column's light.*
10. **100 · reveal · t 24-28 · low, in front of her.** Out of the fire behind her the esper rises - horns, head,
    shoulders - unfolds its huge clawed arms and towers over her.
11. **110 · echo · t 24-28 · from behind him.** The same rising, from his side of the clearing: the giant filling
    the red sky behind the small figure of Terra; the jester small in the foreground.
12. **120 · echo · t 27-28 · its face.** Its eyes ignite white-gold; it roars. *Glue: the roar runs into the next
    shot. Baton: her eyes opened in 090, its eyes open here.*
13. **130 · answer · t 28-30 · medium.** The roar's hot wind hits him - cap flapping, he stumbles back a step,
    shielding his eyes - then grins wider. He is thrilled.

## Leg 3 - the hunt (t 30-49)

14. **140 · advance · t 30-33 · wide.** The esper sweeps its arm at him: pillars of fire burst out of the ground one
    after another, racing at him. He cartwheels away to the right. *Baton: his motion to the right.*
15. **150 · advance · t 33-36 · with him.** He runs and flips to the right; pillars erupt at his heels; the trees
    beside him catch fire.
16. **160 · advance · t 36-38 · low on the esper.** It raises a hand to the sky: a ball of molten rock forms above
    its palm - and it hurls it high to the right. *Baton: the throw.*
17. **170 · advance · t 38-40 · the sky.** The ball streaks across the red sky like a comet and plunges down.
    *Glue: a flash on the impact.*
18. **180 · advance · t 40-43 · wide by the boulder.** The comet slams down beside him: the boulder bursts, burning
    trees topple, the blast throws him into the air; he lands in a crouch. *Glue: a slow dissolve - time passes.*
19. **190 · breath · t 43-49 · high overview.** The forest is a volcanic warzone: rivers of lava, burning trees, ash
    falling like snow, smoke into a blood-red sky; the esper stands in the middle like a mountain of fire beside
    her. A crow circles, cawing. *Glue: the caw runs on.*

## Leg 4 - the end (t 49-62)

20. **200 · answer · t 49-52 · medium.** The jester, singed and smoking among the glowing cracks, looks up at the
    giant, then at her - sweeps off his cap, bows deeply, snaps his fingers and vanishes in purple smoke.
21. **210 · advance · t 52-56 · the two of them.** The esper looks down at her and bows its horned head - then
    bursts into a whirlwind of embers that swirl down into her joined hands. *Glue: the embers.*
22. **220 · echo · t 54-56 · her hands.** The last embers pour into her palms; the glow between her fingers fades.
    *Glue: a slow dissolve.*
23. **230 · breath · t 56-62 · wide.** Terra alone in the burning clearing. Wind blows ash past her; she sinks to
    her knees, lowers her hands, breathes out, and looks up at the red sky.
"""

S = []


def shot(sid, name, frames, cam, place, style, beat, sound, figs, leg, t, glue="", baton="", note="", live=(),
         jump="", keys=None, over_shoulder=()):
    S.append(dict(sid=sid, name=name, frames=frames, cam=cam, place=place, style=style, beat=beat, sound=sound,
                  figs=figs, leg=leg, t=t, glue=glue, baton=baton, note=note, live=list(live), jump=jump,
                  keys=keys, over=over_shoulder))


# figs: who -> (start, end); HID = out of the shot at that end
shot("010", "losing", 105, {"cam": [7.0, 26.0, 1.4], "look": [1.3, 26.4, 1.5], "lens": 22}, "dusk", "",
     "Wide side view of the clearing at dusk, she on the left, he on the right: (1) %s juggles three glowing purple "
     "orbs, laughing; (2) %s, bruised and breathing hard, takes a step back; (3) wind stirs the leaves between "
     "them." % (HIM, HER),
     "wind, his giggle, the hum of the orbs", {"terra": (T, T), "jester": (J0, J0)},
     "breath", (0, 4), glue="L-cut: the wind and his laugh run on under 020",
     note="Where we are: he is winning, she is hurt.")
# 020 without the summoning's style line: with it, H3 lit a ring of runes round her as she began to pray - the magic
# arrived before 040, where the runes ignite (2026-10-05, the first takes)
shot("020", "the prayer", 73, {"cam": [2.7, 24.9, 1.45], "look": [0.9, 23.2, 1.4], "lens": 40}, "dusk", "",
     "Medium shot on %s: (1) she closes her eyes; (2) she presses her palms together in front of her chest as if in "
     "prayer; (3) her lips move in a whispered incantation." % HER,
     "a whispered incantation, wind", {"terra": (T, T)},
     "advance", (4, 7), glue="L-cut: her whisper runs on under 030",
     note="She stops fighting and starts praying.",
     keys=[{"at": "end", "from": "end", "pose": PRAYING, "seed": 202}])
shot("030", "amused", 57, {"cam": [3.1, 27.5, 1.6], "look": [1.3, 29.4, 1.6], "lens": 40}, "dusk", "",
     "Medium shot on %s: (1) he catches his three glowing purple orbs and stops juggling; (2) he tilts his head, "
     "curious, his grin "
     "widening; (3) his eyes drop toward her feet." % HIM,
     "a faint whispered incantation, his amused hum", {"jester": (J0, J0)},
     "answer", (6, 9), baton="his look down - to the ground at her feet (040)",
     note="He thinks it is a trick, and he likes tricks.")
shot("040", "the runes", 57, {"cam": [2.2, 24.2, 0.35], "look": [0.9, 23.2, 0.2], "lens": 30}, "dusk", MAGIC,
     "Low shot at ground level on the red boots of %s: (1) a circle of glowing orange runes ignites on the ground "
     "around her feet; (2) the runes begin to turn slowly; (3) embers lift from the circle into the air." % HER,
     "a low rising hum, crackling embers", {"terra": (T, T)},
     "advance", (9, 12), glue="object: the circle of runes (and 050 sees the same circle)",
     note="The spell begins where he looked.")
shot("050", "from above", 57, {"cam": [3.4, 25.4, 4.6], "look": [0.9, 23.2, 0.4], "lens": 28}, "dusk", MAGIC,
     "High angle looking down on %s standing with her palms pressed together: (1) the circle of glowing orange runes "
     "turns around her on the ground; (2) embers spiral up around her; (3) her long hair begins to lift and "
     "float." % HER,
     "the rising hum, the whisper of the incantation", {"terra": (T, T)},
     "echo", (9, 12), glue="object: embers drift through every cut from here to 130 (an overlay across the cuts)",
     note="The same moment as 040, from above: how big the circle is round her.",
     # the first takes drew the circle on the open ground in front of her, not round her feet as 040 has it: an
     # echo must show the same thing, so the circle is painted in where it is (2026-10-05)
     keys=[{"at": "start", "from": "start", "seed": 11,
            "pose": "Edit <image1>: a circle of glowing orange runes on the ground around the feet of the young woman "
                    "with sea-green hair, centred on her, about three metres across, with her standing in its middle; "
                    "she stands with her palms pressed together in front of her chest. Everything else stays exactly "
                    "as it is; same camera, same framing."},
           {"at": "end", "from": "key:start", "seed": 11,
            "pose": "Edit <image1>: the circle of runes around her glows brighter, embers rise from it in a spiral "
                    "around her and her long hair lifts and floats upward. Everything else stays exactly as it is; "
                    "same camera, same framing."}])
shot("060", "her face", 73, {"cam": [2.1, 24.3, 1.42], "look": [0.9, 23.2, 1.36], "lens": 55}, "red", MAGIC,
     "Close-up on %s, eyes closed, palms pressed together under her chin: (1) she whispers the incantation, lit "
     "from below by an orange glow; (2) strands of her hair float upward; (3) embers drift past her face." % HER,
     "a whispered chant, a deep rising hum", {"terra": (T, T)},
     "advance", (12, 15), glue="sound: a deep rumble rises under the cut into 070",
     note="The power building in her.",
     keys=[{"at": "start", "from": "start", "seed": 202,
            "pose": "Edit <image1>: the young woman with sea-green hair has her eyes closed and her palms pressed "
                    "together under her chin in prayer, her fingers pointing up; a warm orange glow from below lights "
                    "her face; a few strands of her hair float upward." + KEEP},
           {"at": "end", "from": "key:start", "seed": 202,
            "pose": "Edit <image1>: the orange glow lighting her face from below is brighter, more strands of her hair "
                    "float upward and a few glowing embers drift past her face; she keeps her eyes closed and her palms "
                    "pressed together exactly as they are." + KEEP}])
shot("070", "the birds flee", 105, {"cam": [3.6, 26.4, 1.0], "look": [-2.6, 33.5, 7.0], "lens": 24}, "red", "",
     "Low angle looking up at the treetops at the edge of the clearing under a sky turning red: (1) a flock of birds "
     "bursts from the branches and flees across the sky; (2) the leaves shiver; (3) the trees sway as the ground "
     "trembles.",
     "a deep rumble, a burst of flapping wings and bird cries, wind", {},
     "breath", (15, 19), glue="L-cut: the bird cries run on under 080",
     note="The forest knows before he does - and time passes while the power builds.",
     live=[{"ev": "leafrain", "at": [-2.0, 33.0], "f": 30, "n": 60, "radius": 6.0}],
     keys=[{"at": "end", "from": "end", "seed": 11,
            "pose": "Edit <image1>: a big flock of dark birds flies up out of the treetops and away across the red "
                    "sky, small black silhouettes with spread wings, scattered across the upper half of the picture. "
                    "The trees, the standing stones and the red sky stay exactly as they are; same camera, same "
                    "framing."}])
shot("080", "his grin falters", 57, {"cam": [2.5, 28.3, 1.75], "look": [1.3, 29.4, 1.78], "lens": 55}, "red", "",
     "Close-up on %s: (1) his grin falters; (2) the purple orbs in his hand flicker and go out; (3) he swallows, "
     "his eyes wide." % HIM,
     "the deep rumble, a nervous swallow", {"jester": (J0, J0)},
     "answer", (19, 21), glue="flash into 090",
     note="For the first time, he is afraid.",
     keys=[{"at": "end", "from": "end", "seed": 11,
            "pose": "Edit <image1>: the jester's grin is gone - his mouth is shut in a tight, nervous line and his "
                    "eyes are wide with fear, a bead of sweat on his temple. His face paint, his hair, his cap and "
                    "his costume stay exactly as they are; the forest and the red sky stay exactly as they are; same "
                    "camera, same framing."}])
shot("090", "the call", 73, {"cam": [3.6, 24.6, 1.1], "look": [0.9, 23.2, 1.1], "lens": 28}, "red", MAGIC,
     "Medium shot on %s: (1) her eyes snap open, glowing orange; (2) she drops to one knee and slams her joined "
     "hands onto the ground; (3) the circle of runes erupts into a roaring column of fire around her and she rises "
     "to her feet again, palms pressed together." % HER,
     "a burst of flame, a roaring column of fire", {"terra": (T, T)},
     "advance", (21, 24), glue="light: the column's flash covers the cut into 100",
     baton="her eyes opening (the esper's open in 120)", note="She calls - and the fire answers.",
     keys=[{"at": "start", "from": "start", "pose": PRAYING, "seed": 11},
           {"at": "end", "from": "key:start", "seed": 11,
            "pose": "Edit <image1>: the young woman's eyes are wide open and glowing bright orange, her palms still "
                    "pressed together in front of her chest; a roaring column of orange fire rises from the ground "
                    "behind her into the red sky; her hair blows upward in the heat." + KEEP}])
shot("100", "it rises", 105, {"cam": [3.2, 27.6, 0.9], "look": [0.85, 20.8, 2.9], "lens": 22}, "red", MAGIC,
     "Low angle on %s standing with her palms pressed together, a column of fire roaring behind her: (1) out of the "
     "fire behind her rises %s - first its great curved horns, then its head and shoulders; (2) it unfolds its huge "
     "clawed arms; (3) it towers over her, flames streaming from its mane." % (HER, ESPER),
     "a deep roar of fire, a rumbling growl, crackling flames", {"terra": (T, T), "esper": (HID, E)},
     "reveal", (24, 28), jump="esper: out of the fire",
     note="The reveal: the esper, from in front of her - she is small, it is everything behind her.",
     keys=[{"at": "end", "from": "end", "seed": 11,
            "pose": "Edit <image1>: the young woman with sea-green hair stands with her palms pressed together in "
                    "front of her chest, her eyes glowing orange; the towering fire demon behind her stays exactly as "
                    "it is." + KEEP},
           {"at": "start", "from": "key:end", "seed": 11,
            "pose": "Edit <image1>: replace the towering fire demon with a roaring column of orange fire rising from "
                    "the ground into the red sky in the same place, as tall as the demon; the young woman with "
                    "sea-green hair stays exactly as she is, her palms pressed together, in front of the fire." + KEEP}])
shot("110", "it rises - his side", 73, {"cam": [3.0, 31.6, 1.7], "look": [0.9, 21.5, 3.2], "lens": 26}, "red", MAGIC,
     "Wide shot from behind %s, small in the foreground on the right: across the clearing, behind the young woman "
     "with sea-green hair, %s rises out of a column of fire, unfolding its arms and towering into the red sky." % (HIM, ESPER),
     "a deep roar of fire, a rumbling growl", {"terra": (T, T), "jester": (J0, J0), "esper": (HID, E)},
     "echo", (24, 28), over_shoulder=("jester",),
     note="The same rising as 100, from his side of the clearing: how big it is to him.")
shot("120", "its eyes", 57, {"cam": [3.0, 23.4, 4.2], "look": [0.8, 19.6, 4.7], "lens": 35}, "red", MAGIC,
     "Close on the horned head and shoulders of %s: (1) its eyes ignite, burning white-gold; (2) it opens its jaws "
     "and roars, sparks pouring from its mouth." % ESPER,
     "a thunderous roar", {"esper": (E, E)},
     "echo", (27, 28), glue="J/L: the roar runs into 130",
     baton="its eyes opening - as hers did in 090", note="The moment it wakes.")
shot("130", "the hot wind", 57, {"cam": [3.1, 28.0, 1.5], "look": [1.3, 29.4, 1.6], "lens": 38}, "red", "",
     "Medium shot on %s: (1) a blast of hot wind from the roar hits him and his cap and costume flap wildly; (2) he "
     "stumbles back a step, shielding his eyes; (3) then he grins wider, thrilled." % HIM,
     "the end of a thunderous roar, rushing hot wind, his giggle", {"jester": (J0, J0)},
     "answer", (28, 30), note="He is scared - and thrilled. He will not run yet.")
shot("140", "the pillars", 73, {"cam": [9.0, 25.4, 2.4], "look": [1.0, 25.2, 3.0], "lens": 18}, "burning", FIGHT,
     "Wide side view, she and the giant behind her on the left, he on the right: (1) %s sweeps its clawed arm toward "
     "him; (2) a line of fire pillars bursts out of the ground one after another, racing toward him across the "
     "clearing; (3) %s cartwheels away to the right." % (BIG, HIM),
     "a roar, explosions of fire bursting from the ground one after another", {"terra": (T, T), "esper": (E, E),
                                                                                "jester": (J0, J1)},
     "advance", (30, 33), baton="his motion to the right (150 runs on with it)",
     note="The hunt begins.", live=[{"ev": "shock", "at": [1.2, 27.5], "f": 30, "n": 30, "radius": 2.0}])
shot("150", "the chase", 73, {"cam": [6.0, 29.6, 1.3], "cam_to": [6.2, 31.6, 1.3], "look": [2.2, 30.6, 1.3],
                              "look_to": [2.9, 33.0, 1.3], "lens": 26}, "burning", FIGHT,
     "The camera pans right with %s: (1) he flips and runs to the right; (2) pillars of fire burst out of the ground "
     "right behind his heels, one after another; (3) the trees beside him catch fire." % HIM,
     "running footsteps, explosions of fire, crackling trees", {"jester": (J1, J2)},
     "advance", (33, 36), note="It is faster than him.",
     live=[{"ev": "shock", "at": [2.6, 32.0], "f": 40, "n": 30, "radius": 1.6}])
shot("160", "the comet", 73, {"cam": [5.8, 25.0, 1.6], "look": [0.8, 19.6, 4.0], "lens": 18}, "burning", FIGHT,
     "Low angle on %s: (1) it raises one huge clawed hand to the red sky; (2) a ball of molten rock forms above its "
     "palm, glowing white-hot; (3) it hurls the ball high into the sky to the right." % ESPER,
     "a deep growl, a rushing whoosh", {"esper": (E, E)},
     "advance", (36, 38), baton="the throw to the right (170 carries the ball across the sky)",
     note="The finishing blow.")
shot("170", "across the sky", 57, {"cam": [2.4, 27.0, 1.0], "look": [3.0, 33.0, 8.5], "lens": 24}, "burning", FIGHT,
     "Looking up past burning treetops into the blood-red sky: a ball of molten rock streaks across the sky to the "
     "right like a comet, trailing fire and smoke, and plunges down out of the frame.",
     "a rising whistling roar", {},
     "advance", (38, 40), glue="flash: the impact covers the cut into 180", note="Falling on him.")
shot("180", "the impact", 73, {"cam": [6.8, 29.0, 2.2], "look": [3.2, 34.0, 1.5], "lens": 24}, "burning", FIGHT,
     "Wide shot by the great boulder: (1) the comet slams into the ground beside %s; (2) the explosion shatters the "
     "boulder and the burning trees topple; (3) the shockwave throws him into the air and he lands in a crouch." % HIM,
     "a colossal explosion, shattering rock, falling trees", {"jester": (J2, J3)},
     "advance", (40, 43), glue="dissolve: time passes into 190",
     note="The clearing breaks.", live=[{"ev": "shatter", "f": 14, "from_az": 210},
                                        {"ev": "topple", "trees": ["E4", "E6"], "f": 18, "at": [3.6, 34.8]},
                                        {"ev": "shock", "at": [3.6, 34.8], "f": 12, "n": 50, "radius": 3.0}])
shot("190", "the warzone", 105, {"cam": [9.0, 17.0, 9.0], "look": [1.2, 27.0, 0.0], "lens": 22}, "volcanic", "",
     "High wide view over the clearing: the forest has become a volcanic warzone - the ground split into glowing "
     "rivers of lava, trees burning and fallen, ash falling like snow, columns of black smoke rising into a "
     "blood-red sky; in the middle %s stands like a mountain of fire behind the small figure of the young woman; a "
     "crow circles overhead." % BIG,
     "crackling fire, a distant rumble, a crow cawing, wind", {"terra": (T, T), "esper": (E, E), "jester": (J3, J3)},
     "breath", (43, 49), glue="L-cut: the crow's caw runs on under 200",
     note="What she has done - time passes in the ruin.", over_shoulder=("terra",))
shot("200", "the bow", 73, {"cam": [4.6, 30.6, 1.4], "look": [2.6, 32.2, 1.3], "lens": 36}, "volcanic", "",
     "Medium shot on %s among glowing cracks in the ground, singed and smoking: (1) he looks up at the giant of "
     "fire; (2) he looks at her, sweeps off his cap and bows deeply; (3) he snaps his fingers and vanishes in a puff "
     "of purple smoke." % HIM,
     "crackling fire, a cough, a finger snap, a pop", {"jester": (J3, HID)},
     "answer", (49, 52), note="He knows when he is beaten - and leaves like a showman.")
shot("210", "embers", 105, {"cam": [4.6, 25.6, 1.3], "look": [0.85, 21.2, 2.6], "lens": 20}, "volcanic", MAGIC,
     "The fire esper - a towering horned demon of living flame with glowing white-gold eyes - stands behind the "
     "young woman with sea-green hair: (1) it looks down at her and bows its horned head; (2) its whole body "
     "bursts into a whirlwind of embers; (3) the embers swirl down into her joined hands.",
     "a soft rumble, a rushing whirl of embers", {"terra": (T, T), "esper": (E, HID)},
     "advance", (52, 56), glue="object: the embers (into 220)", note="It goes back where it came from: into her.",
     keys=[{"at": "start", "from": "start", "seed": 202,
            "pose": "Edit <image1>: the young woman with sea-green hair stands with her palms pressed together in "
                    "front of her chest, looking up at the fire demon; the towering fire demon stays exactly as it "
                    "is." + KEEP},
           {"at": "end", "from": "end", "seed": 202,
            "pose": "Edit <image1>: the young woman with sea-green hair stands with her hands joined in front of her "
                    "chest, a bright orange glow shining between her fingers and glowing embers swirling down into "
                    "them." + KEEP}])
shot("220", "her hands", 57, {"cam": [2.0, 24.0, 1.25], "look": [0.9, 23.2, 1.2], "lens": 60}, "volcanic", MAGIC,
     "Close-up on the joined hands of %s in front of her chest: the last embers pour into her palms and the glow "
     "between her fingers fades." % HER,
     "a soft hiss, a faint chime", {"terra": (T, T)},
     "echo", (54, 56), glue="dissolve into 230", note="The same moment, close: the power going home.",
     keys=[{"at": "start", "from": "start", "seed": 202,
            "pose": "Edit <image1>: the young woman's two hands are joined in front of her chest, cupped together, "
                    "a bright orange glow shining between her fingers and glowing embers pouring down into her palms."
                    + KEEP},
           {"at": "end", "from": "key:start", "seed": 202,
            "pose": "Edit <image1>: the light is gone: her cupped hands are empty and unlit, no glow, no sparks and no "
                    "embers anywhere, no orange light on her hands or her dress; her hands stay joined exactly as they "
                    "are." + KEEP}])
shot("230", "alone", 105, {"cam": [6.2, 26.8, 2.0], "look": [0.9, 23.2, 1.0], "lens": 24}, "volcanic", "",
     "Wide shot of %s alone in the burning clearing: (1) wind blows ash past her; (2) she sinks to her knees and "
     "lowers her hands; (3) she breathes out and looks up at the red sky." % HER,
     "wind, crackling fire, a distant rumble", {"terra": (T, T)},
     "breath", (56, 62), note="The cost.",
     keys=[{"at": "end", "from": "end", "seed": 202,
            "pose": "Edit <image1>: the young woman with sea-green hair kneels on the ground, sitting back on her heels, "
                    "her hands resting on her knees, her head raised to the sky. Her face, hair, dress and colours "
                    "stay exactly as they are; the burning clearing and the light stay exactly as they are; same "
                    "camera, same framing."}])

LEGS = ("advance", "echo", "answer", "breath", "reveal")


# ------------------------------------------------------------------------------------------------ the checks
def _basis(cam, look):
    f = [look[i] - cam[i] for i in range(3)]
    n = math.sqrt(sum(v * v for v in f))
    f = [v / n for v in f]
    rn = math.hypot(f[1], f[0]) or 1.0
    r = [f[1] / rn, -f[0] / rn, 0.0]
    u = [r[1] * f[2] - r[2] * f[1], r[2] * f[0] - r[0] * f[2], r[0] * f[1] - r[1] * f[0]]
    return f, r, u


def _proj(cam, look, lens, p, w=1280, h=720):
    f, r, u = _basis(cam, look)
    d = [p[i] - cam[i] for i in range(3)]
    z = sum(d[i] * f[i] for i in range(3))
    if z <= 0.05:
        return None
    k = lens / 36.0 * w
    return w / 2 + sum(d[i] * r[i] for i in range(3)) / z * k, h / 2 - sum(d[i] * u[i] for i in range(3)) / z * k


def to_of(who, pos):
    """What each faces: the two of them each other; the esper the jester (it fights on her side)."""
    return pos["jester"] if who in ("terra", "esper") else pos["terra"]


def check(shots, acts, lines):
    bad, rows, last = [], [], {}
    for sh, x in zip(shots, S):
        sid, pz = sh["id"], sh["previz"]
        for tag in ("start", "end"):
            cam = pz.get("cam_to") if tag == "end" and pz.get("cam_to") else pz["cam"]
            look = pz.get("look_to") if tag == "end" and pz.get("look_to") else pz["look"]
            f, r, u = _basis(cam, look)
            tp, jp = lines[sid][tag]
            v, w = (jp[0] - tp[0], jp[1] - tp[1]), (cam[0] - tp[0], cam[1] - tp[1])
            if v[0] * w[1] - v[1] * w[0] >= 0:
                bad.append("%s %s: the camera is WEST of the line" % (sid, tag))
            desc = []
            for who, m in acts[sid]["figures"].items():
                mk = m.get(tag) or {}
                if mk.get("hidden") or "at" not in mk:
                    continue
                at = list(mk["at"]) + [0.0] * (3 - len(mk["at"]))
                feet = _proj(cam, look, pz["lens"], at)
                head = _proj(cam, look, pz["lens"], (at[0], at[1], at[2] + HEIGHT[who]))
                if feet is None or head is None:
                    bad.append("%s %s: %s is BEHIND the camera" % (sid, tag, who))
                    continue
                cx = (feet[0] + head[0]) / 2
                if cx < 20 or cx > 1260 or head[1] > 700 or feet[1] < 20:
                    bad.append("%s %s: %s out of the picture (x %.0f, head %.0f, feet %.0f)" % (sid, tag, who, cx,
                                                                                                 head[1], feet[1]))
                fx, fy = mk["to"][0] - at[0], mk["to"][1] - at[1]
                n = math.hypot(fx, fy) or 1.0
                on = (fx * r[0] + fy * r[1]) / n
                want = -1 if who == "jester" else 1
                if on * want < -0.2:
                    bad.append("%s %s: %s faces screen-%s" % (sid, tag, who, "right" if on > 0 else "left"))
                rel = (math.degrees(math.atan2(cam[0] - at[0], cam[1] - at[1])) - math.degrees(math.atan2(fx, fy))
                       + 540) % 360 - 180
                view = "back" if abs(rel) > 112.5 else "side" if abs(rel) > 67.5 else "3/4" if abs(rel) > 22.5 else "front"
                if view == "back" and who not in x["over"]:
                    bad.append("%s %s: %s seen from BEHIND" % (sid, tag, who))
                desc.append("%s x%4.0f %4.0fpx %s %s" % (who[0].upper(), cx, feet[1] - head[1],
                                                         "->" if on > 0.2 else "<-" if on < -0.2 else "^^", view))
                if tag == "start" and who in last and math.dist(last[who][:2], at[:2]) > 0.05 and who not in x["jump"]:
                    bad.append("%s: %s starts at %s, the last shot left them at %s" % (sid, who, at[:2], last[who][:2]))
                if tag == "end":
                    last[who] = at
            rows.append("  %s %-5s %-7s %s" % (sid, tag, x["leg"], " | ".join(desc) or "(nobody)"))
    # the relay: story time never runs backwards except on an echo; an echo repeats time already told
    told = 0
    for x in S:
        t0, t1 = x["t"]
        if x["leg"] not in LEGS:
            bad.append("%s: leg %r" % (x["sid"], x["leg"]))
        if x["leg"] == "echo":
            if t0 >= told:
                bad.append("%s: an echo must repeat story time already told (t %s, told to %s)" % (x["sid"], t0, told))
        elif t0 < told - 1.0 and x["leg"] != "answer":
            bad.append("%s: story time runs backwards (t %s, told to %s) on a %s" % (x["sid"], t0, told, x["leg"]))
        told = max(told, t1)
    return rows, bad


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check-only", action="store_true")
    a = ap.parse_args()
    film = {
        "_comment": "THE FIRE ESPER (2026-10-05): one moment told as a relay of shots, frames first in the clearing "
                    "set. See _make_fire_esper_1005.py and fire-esper.md.",
        "film": FILM, "title": "THE FIRE ESPER", "subtitle": "Terra and the jester",
        "logline": "Losing to the jester, Terra stops fighting and starts praying - and something answers.",
        "grade": GRADE, "avoid": AVOID, "realism": "", "style": "shon",
        "score_tags": "picked by ear (craft/SOUND.md section 0) - none yet",
        "place": {"id": "clearing", "prompt": "A forest clearing ringed by huge trees and standing stones, painted as an "
                                              "anime background."},
        "cast": {"terra": {"role": "Terra", "prompt": "Terra: her character sheet (studio/sheets/terra-in-the-plaza-terra)."},
                 "jester": {"role": "the jester", "prompt": "The jester: his character sheet (studio/sheets/forest-fight-the-jester)."},
                 "esper": {"role": "the fire esper", "prompt": "The fire esper: its character sheet (studio/sheets/the-fire-esper), "
                                                                "made from one Flux 2 picture."}},
        "shots": [],
    }
    acts, done, lines = {}, [], {}
    pos = {"terra": T, "jester": J0, "esper": E}
    for k, x in enumerate(S):
        sid = x["sid"]
        figs = {}
        start_pos = dict(pos)
        end_pos = dict(pos)
        for who, (s0, s1) in x["figs"].items():
            if s0 is not HID:
                start_pos[who] = s0
            if s1 is not HID:
                end_pos[who] = s1
            elif s0 is not HID:
                end_pos[who] = s0
        for who, (s0, s1) in x["figs"].items():
            m0 = {"hidden": True} if s0 is HID else {"at": list(s0), "to": list(to_of(who, start_pos)[:2])}
            m1 = {"hidden": True} if s1 is HID else {"at": list(s1), "to": list(to_of(who, end_pos)[:2])}
            figs[who] = {"start": m0, "end": m1}
        lines[sid] = {"start": (start_pos["terra"], start_pos["jester"]), "end": (end_pos["terra"], end_pos["jester"])}
        pos = end_pos
        pz = {"scene": "set", "set": "duel", "action": "duel:%s:%s" % (FILM, sid), "frames": x["frames"], "masks": 8,
              "endpoints": 1, "dress": PLACE[x["place"]], "dress_place": PLACE[x["place"]], "grade": GRADE}
        pz.update(x["cam"])
        stay = STAY if x["place"] == "dusk" else ""
        prompt = ("2D anime, hand-drawn cel animation. " + x["style"] + x["beat"] + stay + " Sound: " + x["sound"] +
                  ". No music.")
        t0, t1 = x["t"]
        note = "%s [%s · story t %g-%g s%s%s] (shot %d of %d)" % (
            x["note"], x["leg"], t0, t1, " · glue: " + x["glue"] if x["glue"] else "",
            " · baton: " + x["baton"] if x["baton"] else "", k + 1, len(S))
        sh = {"id": sid, "name": x["name"], "title": x["name"], "secs": round(x["frames"] / 24.0, 2), "face": "none",
              "engine": "h3f", "refs": ["clearing"] + [w for w in ("terra", "esper", "jester") if w in x["figs"]],
              "anchor": None, "prompt": prompt,
              "avoid_extra": OTHERS, "note": note, "leg": x["leg"], "story_time": [t0, t1], "glue": x["glue"],
              "baton": x["baton"], "place_state": x["place"], "previz": pz}
        if x["keys"]:
            sh["keys"] = x["keys"]
        film["shots"].append(sh)
        acts[sid] = {"figures": figs, "done": list(done), "live": x["live"]}
        done += x["live"]
    rows, bad = check(film["shots"], acts, lines)
    print("\n".join(rows))
    print("%d shots, %.1f s of takes, %g s of story" % (len(S), sum(s["secs"] for s in film["shots"]), S[-1]["t"][1]))
    if bad:
        print("CHECK FAILED:\n  " + "\n  ".join(bad))
        sys.exit(1)
    print("check: line, picture, facing, no back views, marks chained, story time a relay")
    if a.check_only:
        return
    for name, obj in ((FILM + ".json", film), (FILM + ".acts.json", acts)):
        json.dump(obj, open(os.path.join(DST, name), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
        print("%s -> %s" % (name, os.path.join(DST, name)))
    open(os.path.join(DST, FILM + ".md"), "w", encoding="utf-8").write(SCRIPT)
    print("script ->", os.path.join(DST, FILM + ".md"))


if __name__ == "__main__":
    main()
