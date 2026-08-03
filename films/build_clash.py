#!/usr/bin/env python3
"""Build films/clash.json - THE CLASH, a ~45s vertical short. Test piece for short.py.

Reuses the Berserk character sheets, so casting costs nothing. Original story: the
swordsman and the beast, one fight, no narration - every line is spoken by a character.

Built entirely from scene templates, which is the point: 26 beats become ~70 shots without
a single hand-written cut. Compare to the 20-minute film, where 133 shots needed 133
generations.
"""
import collections, json, os

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "clash.json")

STYLE = ("dark gritty seinen anime illustration, heavy ink shadow, extreme high contrast, "
         "saturated rim light, dramatic low angle, painterly, cinematic")

B = []


def beat(bid, tpl, prompt, motion, ref=None, line=None, secs=4, intensity=1.0):
    d = collections.OrderedDict(id=bid, template=tpl)
    if intensity != 1.0:
        d["intensity"] = intensity
    if ref:
        d["ref"] = ref
    d["clip_secs"] = secs
    d["prompt"] = prompt
    d["motion"] = motion
    if line:
        d["line"] = {"who": line[0], "text": line[1]}
    B.append(d)


beat("010_ridge", "hook",
     "Epic low angle of {GUTS} standing alone on a wind-scoured ridge at blood-red dusk, enormous sword planted in the rock beside him, storm clouds boiling behind, rim lit in red",
     "Wind tears at his cloak and hair. Storm clouds boil and move fast behind him. Embers blow past. He does not move.",
     ["GUTS"], secs=5)
beat("020_beast", "reveal",
     "Terrifying low angle of {ZODD} rising to full height on the ridge opposite, horns against the storm sky, muscles flexing, eyes burning white-hot",
     "It rises to full height and rolls its shoulders. Its eyes flare brighter. Dust blasts outward from its feet.",
     ["ZODD"], secs=4)
beat("030_taunt_z", "taunt",
     "Extreme close-up of the bestial face of {ZODD}, fangs bared in something like a grin, one burning eye filling half the frame",
     "The eye narrows and the grin widens. Steam rises from its nostrils. Firelight moves across the fangs.",
     ["ZODD"], ("ZODD", "Little man. You brought a sword to this."), secs=4)
beat("040_taunt_g", "taunt",
     "Extreme close-up of the face of {GUTS}, jaw set, one eye lit red by the storm light, blood already on his cheek",
     "His jaw tightens. Blood runs slowly down his cheek. His eye does not blink or move.",
     ["GUTS"], ("GUTS", "I brought worse than that."), secs=4)
beat("050_charge_g", "charge",
     "Dynamic low tracking shot of {GUTS} sprinting flat out across broken rock, enormous sword dragging behind him throwing a wall of sparks, red storm light",
     "He sprints toward camera, blade dragging and throwing a continuous wall of sparks. The camera races backward ahead of him.",
     ["GUTS"], secs=4)
beat("060_clash1", "clash",
     "Explosive impact shot of an enormous sword meeting a monstrous clawed arm, shockwave ring blasting outward, rock shattering beneath, white-hot sparks",
     "The blade and the claw meet and a shockwave ring blasts outward. Rock shatters under them. Sparks fill the frame.",
     ["GUTS", "ZODD"], secs=4)
beat("070_impact_z", "impact",
     "Brutal shot of {ZODD} taking a full sword blow across the chest, body twisting with the force, blood and sparks spraying, low angle",
     "The blow lands and its whole body twists with the force. Blood and sparks spray outward. It staggers a full step back.",
     ["ZODD"], secs=4)
beat("080_taunt_z2", "taunt",
     "Close shot of {ZODD} looking down at the wound across its chest, then up at camera, entirely unbothered, storm behind",
     "It looks down at the wound, then slowly back up at camera. The wound is already closing. It laughs silently.",
     ["ZODD"], ("ZODD", "Good. Now it is a fight."), secs=4)
beat("090_clash2", "clash",
     "Chaotic mid-air clash between a huge armoured swordsman and an enormous horned beast, both weightless at the top of an exchange, debris suspended around them",
     "Both are momentarily weightless mid-exchange, debris hanging in the air around them, then everything drops at once.",
     ["GUTS", "ZODD"], secs=4, intensity=1.2)
beat("100_impact_g", "impact",
     "Devastating shot of {GUTS} taking a clawed backhand and being hurled sideways through a standing rock formation, stone exploding around him",
     "The backhand connects and hurls him sideways through the rock. Stone explodes outward. He is thrown out of frame.",
     ["GUTS"], secs=4)
beat("110_down", "taunt",
     "Low shot of {GUTS} face down in shattered rock and dust, one hand already closing on the hilt of the great sword beside him",
     "Dust settles over him. His hand closes slowly on the hilt. His shoulders begin to push up.",
     ["GUTS"], ("GUTS", "That all?"), secs=4)
beat("120_rise", "reveal",
     "Powerful low angle of {GUTS} hauling himself upright out of the rubble, blood streaming, eyes burning, sword coming up, red light building behind him",
     "He hauls himself upright out of the rubble. Blood streams. Red light builds behind him and floods the frame.",
     ["GUTS"], secs=4)
beat("130_charge_z", "charge",
     "Terrifying shot of {ZODD} charging on all fours across the ridge toward camera, horns lowered, rock cratering under each stride",
     "It charges on all fours straight at camera, rock cratering under each stride, closing fast and filling the frame.",
     ["ZODD"], secs=4, intensity=1.15)
beat("140_clash3", "clash",
     "Enormous collision of sword and horn, blinding white impact flash at the centre, both figures silhouetted, the entire ridge cracking",
     "Sword and horn collide in a blinding white flash. Both are silhouetted. Cracks race outward across the ridge.",
     ["GUTS", "ZODD"], secs=4, intensity=1.25)
beat("150_lock", "taunt",
     "Tight two-shot of {GUTS} and {ZODD} locked chest to chest, blade against claw, both straining, faces inches apart, sparks between them",
     "Both strain against each other, shaking with the effort. Sparks pour from where blade meets claw. Neither gives.",
     ["GUTS", "ZODD"], ("ZODD", "Why do you not run?"), secs=4)
beat("160_answer", "taunt",
     "Extreme close-up of the face of {GUTS} in the lock, teeth bared, eye blazing, blood running freely",
     "His teeth bare further. The eye blazes. Blood runs freely down his face. He pushes forward against the lock.",
     ["GUTS"], ("GUTS", "Because there is nowhere left to run to."), secs=4)
beat("170_break", "impact",
     "Explosive shot of the lock breaking, {GUTS} driving forward and up, the beast's guard thrown wide open, debris blasting outward",
     "The lock breaks. He drives forward and up. The beast's guard is thrown wide open. Debris blasts outward.",
     ["GUTS", "ZODD"], secs=4, intensity=1.2)
beat("180_finish", "finisher",
     "Climactic shot of the enormous sword coming down through the frame in a blazing arc onto the beast, white-gold light exploding from the point of contact",
     "The great sword comes down through the frame in a blazing arc. White-gold light explodes outward from the contact and floods everything.",
     ["GUTS", "ZODD"], secs=5)
beat("190_after", "aftermath",
     "Wide shot of {GUTS} standing alone on the cracked ridge at last light, sword point down in the rock, the enormous body behind him, ash falling",
     "Ash falls steadily. His cloak moves in the wind. He does not turn to look back at the body. Slow crane up.",
     ["GUTS"], secs=5)
beat("200_last", "taunt",
     "Final extreme close-up of the face of {GUTS} at last light, blood drying, breathing hard, the faintest edge of something like satisfaction",
     "He breathes hard. Blood dries on his skin. His eye shifts fractionally toward camera and holds.",
     ["GUTS"], ("GUTS", "Next."), secs=4)

film = collections.OrderedDict(
    title="THE CLASH",
    hook="the swordsman|vs the beast",
    fps=24,
    engine="higgs_v3",
    style_lora="qwen_image_2512_storybook_anime_lora.safetensors",
    style_strength=0.0,
    style=STYLE,
    sheets={"GUTS": "sheet_guts.png", "ZODD": "sheet_zodd.png"},
    characters={
        "GUTS": "the black-haired swordsman with the enormous slab sword from the reference image",
        "ZODD": "the enormous red-brown horned beast from the reference image",
    },
    voices={
        "GUTS": {"engine": "higgs_v3", "voice": "voices_examples/male/male_01.wav"},
        "ZODD": {"engine": "indextts2", "voice": "voices_examples/higgs_audio/vex.wav",
                 "emotion": {"Angry": 0.4, "Happy": 0.3},
                 "filter": "lowpass=f=3400,aecho=0.8:0.85:55:0.3"},
    },
    music=[{"at": 0, "prefix": "clash_theme", "bpm": 150, "key": "D minor", "seconds": 60,
            "level": 1.0,
            "tags": "relentless orchestral battle, thundering taiko and timpani, "
                    "distorted brass stabs, driving low strings ostinato, choir shouting "
                    "one syllable, industrial metal hits, overwhelming, instrumental"}],
    beats=B,
)
json.dump(film, open(OUT, "w", encoding="utf-8"), indent=2, ensure_ascii=False)

import sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
from scene_templates import expand as ex
shots = 0
secs = 0.0
for b in B:
    cuts, imp = ex(b, float(b["clip_secs"]))
    shots += len(cuts) + (1 if imp else 0)
    secs += sum(c["len"] for c in cuts) + (0.083 if imp else 0)
print(f"wrote {OUT}")
print(f"  beats {len(B)}  ->  {shots} shots, ~{secs:.0f}s")
print(f"  median shot ~{secs/shots:.2f}s   (reference: 0.30s, our 20-min film: ~9s)")
print(f"  generations needed: {len(B)} keyframes + {len(B)} clips")
print(f"  dialogue lines: {sum(1 for b in B if b.get('line'))}")
