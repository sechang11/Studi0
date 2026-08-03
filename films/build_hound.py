#!/usr/bin/env python3
"""Build films/hound.json - THE HOUND, an original side-story episode.

    python3 films/build_hound.py

An ORIGINAL story of mine set after the Golden Age, reusing the character sheets that film
already produced (Guts, Zodd) plus two new ones. This is the payoff of reference-locked
characters: once a sheet exists, casting the same actor in a new production is free.

The idea: Guts arrives to save a village from the monster feeding on it, and the village
fights him for it - because they voted. It rhymes deliberately with the Skull Knight's line
in the first film, that the price of one man's bargain is always paid by other people. Here
the people paying it have decided the price is worth it, which makes Guts the villain of
their story.

The relationship beat is Zodd. He is the only other creature who knows what Griffith became,
he keeps declining to kill Guts, and he is the closest thing to a friend Guts has left -
which is the joke, and the point.
"""
import collections, json, os

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hound.json")

BASE = ("dark gritty seinen anime illustration, heavy ink shadow, high contrast, muted "
        "desaturated palette, painterly, grim medieval, epic widescreen composition")
STYLE = collections.OrderedDict([
    ("default", BASE),
    ("cold", BASE + ", flat grey overcast light, desaturated to near monochrome, no warm light"),
    ("fire", BASE + ", firelight from below, deep orange and black, heavy chiaroscuro"),
    ("dawn", BASE + ", pale cold dawn light, thin mist, restrained colour"),
    ("green", BASE + ", unnaturally lush green, warm gold afternoon light, too healthy, subtly wrong"),
    ("blood", BASE + ", crushed blacks and arterial red, near abstract, hellish"),
])
CHARS = collections.OrderedDict([
    ("GUTS", "the one-eyed black-haired swordsman with an iron left hand from the reference image"),
    ("ZODD", "the enormous red-brown horned beast from the reference image"),
    ("MIRA", "the young village woman with a dark braid from the reference image"),
    ("VASK", "the silver-bearded lord in a fur-collared coat from the reference image"),
])
SHEETS = {"GUTS": "sheet_guts.png", "ZODD": "sheet_zodd.png",
          "MIRA": "sheet_mira.png", "VASK": "sheet_vask.png"}
VOICES = {
    "NARRATOR": {"exaggeration": 0.30, "cfg_weight": 0.35, "temperature": 0.6,
                 "pitch": 0.86, "rate": 0.86},
    "GUTS": {"exaggeration": 0.55, "cfg_weight": 0.35, "temperature": 0.7, "pitch": 0.70,
             "rate": 0.92, "filter": "lowpass=f=7200,acompressor=threshold=-18dB:ratio=4"},
    "MIRA": {"exaggeration": 0.62, "cfg_weight": 0.38, "temperature": 0.8, "pitch": 1.26,
             "rate": 1.0},
    "VASK": {"exaggeration": 0.35, "cfg_weight": 0.32, "temperature": 0.65, "pitch": 0.82,
             "rate": 0.82},
    "ZODD": {"exaggeration": 0.70, "cfg_weight": 0.30, "temperature": 0.8, "pitch": 0.55,
             "rate": 0.80, "filter": "lowpass=f=3000,aecho=0.8:0.85:60:0.35"},
}
S = []


def sh(sid, prompt, motion, say=None, who=None, ref=None, sfx=None, look=None, seconds=None,
       chain=None, motions=None, tin=None, in_dur=None, titles=None):
    d = collections.OrderedDict(id=sid)
    for k, v in (("in", tin), ("in_dur", in_dur), ("look", look), ("ref", ref),
                 ("chain", chain), ("seconds", seconds)):
        if v:
            d[k] = v
    d["prompt"] = prompt
    d["motion"] = motion
    for i, m in enumerate(motions or [], start=2):
        d[f"motion{i}"] = m
    if say:
        d["say"] = say
        if who:
            d["who"] = who
    if sfx:
        d["sfx"] = sfx
    if titles:
        d["titles"] = titles
    S.append(d)


# ── ACT I: the road ─────────────────────────────────────────────────────────
sh("010_road", "Wide shot of a narrow forest road at night, bare branches closing overhead, thin moonlight, a single armoured figure walking away from camera with an enormous sword on his back",
   "He walks steadily away down the road. Branches shift overhead. Something moves in the trees on both sides and does not show itself.",
   say="There is a mark on his neck that bleeds when the dead come close. It has not stopped bleeding in two years.",
   ref=["GUTS"], look="cold",
   titles=[{"text": "THE HOUND", "at": 1.4, "hold": 3.4, "scale": 0.058, "y": 0.42},
           {"text": "a Berserk side story", "at": 2.1, "hold": 2.8, "scale": 0.024, "y": 0.56}],
   sfx="A night forest road, bare branches, something large moving through undergrowth on both sides, no birds")

sh("020_brand", "Extreme macro close-up of a brand at the base of a neck in moonlight, a small mark shaped like a wound, fresh blood welling out of it and running down",
   "Blood wells out of the mark and runs down the skin. The mark seems to pulse faintly. Steam rises off it in the cold.",
   say="It is a summons, and everything on the other side can read it.",
   look="cold", tin="cut", sfx="A wet trickle, a faint impossible heartbeat, cold air, dread")

sh("030_ambush", "Violent night action shot of a hunched grotesque creature lunging out of the treeline at {GUTS}, all limbs and teeth, the enormous sword already swinging up to meet it, moonlight",
   "The thing comes out of the trees fast and low. He brings the great sword round into it without breaking stride.",
   motions=["Two more come from behind; he turns the swing into a full circle and clears the road around him",
            "The last one drags itself away into the dark; he stands in the road breathing, and starts walking again"],
   ref=["GUTS"], look="cold", tin="cut", chain=3, seconds=20,
   sfx="Something bursting out of undergrowth, a huge blade meeting flesh, inhuman shrieking, then a road at night again")

sh("040_valley", "Breathtaking wide establishing shot at dawn of a green mountain valley from above, terraced fields impossibly lush, a prosperous stone village at the centre, orchards heavy with fruit, mist in the low ground",
   "Mist lifts off the terraces. The fields move in the wind, unnaturally green and heavy. Smoke rises straight up from the chimneys.",
   say="In the morning he came over a ridge and found a valley that had not had a bad harvest in nineteen years.",
   look="green", tin="fade", in_dur=1.6, seconds=7,
   sfx="A mountain valley at dawn, birdsong, wind through heavy crops, a distant bell, everything too pleasant")

sh("050_gate", "Shot of {GUTS} walking through a stone village gate, villagers in good clothes stopping to stare at him, well-fed children, baskets of fruit, warm morning light",
   "The villagers stop what they are doing and watch him pass. Nobody greets him. A woman pulls a child behind her skirts.",
   say="They were fed, and clothed, and afraid of him rather than of anything else.",
   ref=["GUTS"], look="green", tin="dissolve",
   sfx="A prosperous village morning, carts, livestock, conversation dropping to silence as someone passes")

sh("060_mira", "Medium shot of {MIRA} in an inn doorway with a cloth over one shoulder, watching the stranger in the street with open direct curiosity rather than fear",
   "She leans in the doorway and looks him up and down without dropping her eyes. She says something short. The cloth shifts on her shoulder.",
   say="You are the first person to come up that road in nine months. Nobody comes here. Nobody leaves either.",
   who="MIRA", ref=["MIRA"], look="green", tin="cut",
   sfx="An inn doorway, a street beyond, cloth, a young woman's voice, cups inside")

sh("070_no_children", "Unsettling shot of a village square in afternoon light, adults and older children going about their business, and a conspicuous absence, no small children anywhere in the frame",
   "The square is busy with adults and teenagers. Nothing under about ten years old crosses the frame at any point. Slow drift across.",
   say="It took him half a day to work out what was wrong with the place.",
   look="green", tin="dissolve",
   sfx="A busy square, adults, older children, no infant sounds at all, a well, birds")

# ── ACT II: the arrangement ────────────────────────────────────────────────
sh("100_bell", "Ominous shot of a bronze bell in a stone tower being rung at dusk, the village below assembling in the square in complete silence, long shadows",
   "The bell swings and tolls. Below, the villagers file into the square without being told, and stand still, and wait.",
   say="At dusk the bell rang, and the whole valley came to the square without being called twice.",
   look="fire", tin="fade", in_dur=1.4, seconds=6,
   sfx="A bronze bell tolling over a valley, hundreds of feet on stone, then total silence")

sh("110_vask", "Imposing shot of {VASK} on a stone balcony above the square, a tall silver-bearded lord in a heavy fur-collared coat, hands resting on the balustrade, torches on either side of him",
   "He rests both hands on the balustrade and looks down over them without hurrying. The torches gutter. Nobody in the square looks up.",
   say="Lord Vask had held the valley for nineteen years, which was exactly as long as the good harvests had lasted.",
   ref=["VASK"], look="fire", tin="cut",
   sfx="A stone balcony above a crowd, torches, a heavy coat, a crowd holding its breath")

sh("120_lottery", "Shot of a small girl's hand drawing a wooden token from a clay jar held by a village elder, the crowd pressed close around, torchlight, absolute stillness",
   "The hand goes into the jar and comes out with a token. The elder takes it and reads it. Nobody moves at all.",
   say="They drew a name the way other places draw lots for who mends the road.",
   look="fire", tin="cut",
   sfx="A hand in a clay jar, a wooden token, a name read out flatly, a crowd not reacting")

sh("130_name", "Devastating shot of {MIRA} in the crowd going completely still, one hand closing on the shoulder of a small boy beside her, the crowd around them already looking away",
   "Her hand closes hard on the boy's shoulder. Around her, people lower their eyes and begin to turn away. She does not make a sound.",
   say="Her brother was six.",
   ref=["MIRA"], look="fire", tin="cut", sfx="A crowd beginning to disperse, cloth, a hand gripping a shoulder, no crying")

sh("140_bow", "Wrenching wide shot of the square as the crowd bows toward the balcony in unison, {MIRA} standing upright and alone in the middle of the bowing crowd holding the boy",
   "The whole crowd bows in one motion. She stays standing, holding the boy against her, the only vertical figure in the frame.",
   say="Then they bowed, and thanked him, and went home to their suppers.",
   ref=["MIRA"], look="fire", tin="cut", seconds=6,
   sfx="Hundreds of people bowing in unison, a murmured formula of thanks, feet dispersing on stone")

sh("150_inn", "Tense interior shot of a lamplit inn at night, {GUTS} at a table and a heavy grey-haired innkeeper across from him with a jug, other villagers listening from the shadows",
   "The innkeeper sets the jug down and sits without being asked. He speaks steadily. The listeners in the shadows do not move.",
   say="One child a year. Nineteen years. No famine, no plague, no army has ever come up that road.",
   who="VASK", look="fire", tin="dissolve",
   sfx="A quiet lamplit inn, a jug set on wood, a low steady voice, people listening without moving")

sh("160_guts_asks", "Close-up of {GUTS} at the table, one hand around a cup he is not drinking from, iron hand flat on the wood, listening with a flat dangerous expression",
   "The iron hand flexes slowly on the table. He does not touch the cup. His eye stays on the man opposite.",
   say="And you agreed to it.",
   who="GUTS", ref=["GUTS"], look="fire", tin="cut",
   sfx="An iron hand on wood, a cup untouched, a room gone quiet")

sh("170_we_voted", "Shot of the innkeeper leaning back, absolutely unashamed, gesturing at the room and the village beyond with one hand, other villagers nodding in the shadows behind him",
   "He leans back and gestures around the room, and the people in the shadows nod slowly along with him. He is not defending himself. He is explaining.",
   say="We voted. Twice. My own daughter's name has been in that jar nineteen times. Before him we buried four children a winter.",
   who="VASK", look="fire", tin="cut", seconds=7,
   sfx="A room agreeing quietly, cups, a fire, nodding, terrible reasonableness")

sh("180_mira_alone", "Quiet devastating shot of {MIRA} outside in the dark behind the inn, back against the wall, the small boy asleep in her arms, her face wet and furious",
   "She holds the sleeping boy and stares at nothing. Her jaw works. She does not let herself make any noise that would carry.",
   say="I voted for it too. Last year. When it was someone else's brother.",
   who="MIRA", ref=["MIRA"], look="cold", tin="dissolve",
   sfx="A cold yard at night, a child breathing asleep, someone crying without sound, wind")

sh("190_procession", "Eerie wide shot of a torchlit procession climbing a mountain path at night, the villagers walking in an orderly line, a small figure carried at the front, mist and rock",
   "The line of torches winds up the path steadily. Nobody hurries. Nobody speaks. The mist swallows the head of the procession.",
   say="They took him up the mountain at midnight, and they went willingly, and that was the part he could not get past.",
   look="fire", tin="dissolve", seconds=7,
   sfx="A slow torchlit procession on rock, many feet, no voices, wind, a bell somewhere below")

# ── ACT III: the fight ─────────────────────────────────────────────────────
sh("200_altar", "Ominous shot of a flat stone shelf high on the mountain, a shallow bowl worn into the rock, the villagers ringed around it with torches, {VASK} standing at its edge with his coat off",
   "He folds the heavy coat and hands it to someone. The ring of torches closes. He steps to the edge of the worn bowl and waits.",
   look="fire", tin="cut", ref=["VASK"], seconds=5,
   sfx="A high stone shelf, wind, torches guttering, cloth folded, a crowd arranged in a ring")

sh("210_reveal", "Terrifying transformation shot on the mountain shelf, the lord's body splitting open and unfolding upward into something enormous and many-limbed, torches blown flat, villagers on their knees",
   "The body comes apart and opens upward into something far too large for it, unfolding limb after limb. The torches blow flat. The villagers go down on their knees.",
   motions=["The thing settles onto its new limbs and lowers a long head toward the small figure at the centre of the ring",
            "{GUTS} comes through the ring of kneeling villagers at a run with the enormous sword already up and takes the head off its approach"],
   say="What Lord Vask had traded away, he had traded a long time ago.",
   look="blood", tin="cut", chain=3, seconds=24,
   sfx="Flesh and bone unfolding wetly on a huge scale, torches blown out, a crowd falling to its knees, then a huge blade")

sh("220_fight", "Explosive action shot of {GUTS} mid-air bringing the enormous sword down onto the many-limbed creature on the mountain shelf, torch fire scattered, rock cracking beneath them",
   "He comes down on it with the whole weight of the sword. Rock splits under the impact. The thing screams and throws him off.",
   motions=["It catches him with a limb and drives him across the shelf into the rock face; he comes out of the dust already moving",
            "He goes in under its guard and takes two limbs off at the joint; it rears back and the whole shelf shakes",
            "It pins him under one huge limb and leans down over him; he gets the iron hand into its jaw and holds it off",
            "He tears free, comes up the length of its body and drives the sword down through the base of the long head"],
   ref=["GUTS"], look="blood", tin="cut", chain=5, seconds=40,
   sfx="A colossal blade on rock and flesh, a creature screaming, stone cracking, a body thrown into a cliff, sustained brutal combat")

sh("230_villagers_turn", "Shocking shot of the villagers rising from their knees and coming at {GUTS} from behind with torches, stones and farm tools, faces contorted with rage, the wounded creature behind him",
   "They come up off their knees and rush him from behind with whatever they are holding. He turns and sees them coming, and for a second does not understand.",
   say="Then the village came at him. Not at the thing on the rock. At him.",
   ref=["GUTS"], look="blood", tin="cut", seconds=6,
   sfx="A crowd turning violent, stones, tools, screaming, feet on rock, complete confusion")

sh("240_choice", "Close-up of the face of {GUTS} half lit by scattered torch fire, blood across it, understanding exactly what is happening and deciding to finish anyway",
   "His face changes as he understands. He looks past the crowd to the thing behind them. He makes the decision and turns back toward it.",
   say="He could have walked down the mountain. Nobody there wanted saving.",
   ref=["GUTS"], look="blood", tin="cut",
   sfx="Chaos held slightly back, breathing, fire, a decision")

sh("250_kill", "Final brutal shot of the enormous creature collapsing onto the stone shelf, the great sword driven through it, {GUTS} standing on its body, the villagers frozen around them in torchlight",
   "The huge body comes down onto the rock and stops moving. He stands on it with both hands on the hilt. The crowd goes completely still around him.",
   look="blood", tin="cut", ref=["GUTS"], seconds=6,
   sfx="An enormous body collapsing onto stone, a blade driven home, then absolute silence and wind")

# ── ACT IV: the cost ───────────────────────────────────────────────────────
sh("300_dawn", "Bleak dawn wide shot of the same green valley from the ridge, but the colour already draining out of the terraces, the crops greying at the edges, mist gone",
   "The light comes up on the terraces and the green in them is already wrong, greying at the edges. The wind moves through them differently.",
   say="By dawn the fields had already started to turn.",
   look="cold", tin="fade", in_dur=1.6, seconds=7,
   sfx="A valley at dawn, wind through crops that sound dry, no birds, a village waking badly")

sh("310_hate", "Devastating shot of the village street in grey morning light, villagers lining both sides in silence watching {GUTS} walk out, faces full of open hatred, one man holding a stone he does not throw",
   "They line the street and watch him go. Nobody speaks. A man turns a stone over in his hand and does not throw it. He walks through it.",
   say="Nineteen years of harvests had been bought and paid for, and he had just refused the last instalment on their behalf.",
   ref=["GUTS"], look="cold", tin="cut", seconds=7,
   sfx="A silent street, many people not speaking, boots on stone, a stone turned over in a hand")

sh("320_mira_end", "Close two-shot at the village gate, {MIRA} holding her small brother's hand, looking at {GUTS} with something that is not gratitude and not hatred either",
   "She stops in front of him with the boy's hand in hers. She looks up at him for a long moment and does not thank him. The boy stares.",
   say="I do not know whether to kiss you or kill you. Neither does anyone else. Go, before they decide.",
   who="MIRA", ref=["MIRA", "GUTS"], look="cold", tin="cut", seconds=7,
   sfx="A village gate in the morning, two people close, a child, wind, an unresolved goodbye")

sh("330_leaves", "Wide shot from behind of {GUTS} walking out of the valley up the ridge road, the greying terraces below him, the village small behind, grey sky",
   "He walks up the ridge road away from camera. Below him the valley colour keeps draining. He does not look back at it.",
   look="cold", tin="dissolve", ref=["GUTS"], seconds=6,
   sfx="Boots on a ridge road, wind, a valley behind, emptiness ahead")

# ── ACT V: Zodd ────────────────────────────────────────────────────────────
sh("400_zodd_waits", "Striking shot on a high bare ridge at dusk of {ZODD} sitting on a boulder with its arms across its knees, entirely relaxed, watching the road, horns against the sky",
   "It sits on the boulder without moving as he comes up the road, and turns only its head to follow him. It is not crouched to attack.",
   say="Something was waiting on the ridge, and it had not come to fight.",
   ref=["ZODD"], look="dawn", tin="fade", in_dur=1.6, seconds=6,
   sfx="A high bare ridge at dusk, wind, something very large shifting its weight on stone")

sh("410_why", "Two-shot on the ridge of {GUTS} standing with the sword still on his back and {ZODD} seated on the boulder above him, neither of them in a fighting posture, cold sky behind",
   "Neither of them moves toward the other. The beast tilts its head. He stands with his weight even, hand nowhere near the hilt.",
   say="They spat at you. Threw stones at your back. Why spend anything on them at all.",
   who="ZODD", ref=["GUTS", "ZODD"], look="dawn", tin="cut", seconds=7,
   sfx="Wind on a ridge, a low inhuman voice, no weapons drawn, an odd calm")

sh("420_army", "Ominous wide shot from the ridge of a distant plain at dusk with an enormous host of lights moving across it, far too many, a white winged shape hanging in the air above them",
   "The lights on the plain move in a single vast column. Above them the small white winged shape hangs perfectly still. Everything below it follows.",
   say="The thing wearing your friend's face is gathering an army. Whole cities are opening their gates to it and calling it mercy.",
   who="ZODD", look="cold", tin="cut", seconds=8,
   sfx="A vast distant host on the move, thousands of feet and horses, a chorus of adoration on the wind, dread")

sh("430_guts_answer", "Close-up of {GUTS} on the ridge in the last light, the brand at his neck bleeding again, looking out at the distant host rather than at the creature beside him",
   "Blood runs from the mark at his neck. He watches the distant lights. He answers without turning his head.",
   say="Then there will be more valleys like that one. Someone once told me a friend is somebody going somewhere of his own. I am going somewhere.",
   who="GUTS", ref=["GUTS"], look="dawn", tin="cut", seconds=8,
   sfx="Wind on a high ridge, blood running, a low steady voice, distance")

sh("440_zodd_laughs", "Shot of {ZODD} rising off the boulder to its full height against the dusk sky, head back, something like amusement on the bestial face, wings or arms spread",
   "It stands up to its full height and throws its head back. The sound it makes is not quite a laugh. Then it looks down at him almost fondly.",
   say="Good. Get stronger. When it finally kills you I want it to have cost something.",
   who="ZODD", ref=["ZODD"], look="dawn", tin="cut", seconds=7,
   sfx="Something enormous standing up on stone, a laugh that is not a laugh, wind, wings")

sh("450_alone", "Final wide shot of {GUTS} walking down off the ridge into a darkening valley, the enormous sword on his back, the distant lights of the host on the horizon ahead of him, one small figure",
   "He walks down off the ridge toward the distant lights. The sword rides on his back. The dark comes up around him. Very slow crane back.",
   say="He was the only thing left walking toward it.",
   ref=["GUTS"], look="cold", tin="dissolve", seconds=9,
   titles=[{"text": "THE HOUND", "at": 4.2, "hold": 3.4, "scale": 0.048, "y": 0.44}],
   sfx="Boots descending a ridge, wind, a vast distant host far ahead, one man alone")

MUSIC = [
 ("h01_road", "010_road", "night road dread, sub bass pulse, bowed metal, sparse low strings, something following, dark ambient orchestral, instrumental"),
 ("h02_fight", "030_ambush", "short violent skirmish, hammered percussion, brass stabs, snarling low strings, over quickly, orchestral, instrumental"),
 ("h03_valley", "040_valley", "deceptively beautiful pastoral theme, warm strings, solo oboe, harp, golden and just slightly too sweet, orchestral, instrumental, no drums"),
 ("h04_wrong", "070_no_children", "quiet unease under a pretty surface, music box slowing, sustained strings with one sour note held, instrumental, no drums"),
 ("h05_bell", "100_bell", "ritual dread, a slow tolling bell, low male choir on one syllable, deep drum heartbeat, ceremonial and awful, orchestral, instrumental"),
 ("h06_lottery", "120_lottery", "almost nothing, a single sustained cello note and a ticking, unbearable restraint, instrumental, no drums"),
 ("h07_vote", "170_we_voted", "reasonable people explaining an atrocity, warm strings played too gently, low piano, sickening calm, instrumental, no drums"),
 ("h08_climb", "190_procession", "processional, muffled drum, low voices humming, wind, inevitable, orchestral, instrumental"),
 ("h09_reveal", "210_reveal", "monstrous transformation, brass clusters, bowed metal screaming, sub bass, chaotic percussion, orchestral industrial, instrumental"),
 ("h10_battle", "220_fight", "sustained brutal boss battle, relentless taiko and timpani, atonal brass, driving low strings, no melody, overwhelming, orchestral, instrumental"),
 ("h11_turn", "230_villagers_turn", "the betrayal, strings turning sour and rising, panicked percussion, a crowd becoming a mob, orchestral, instrumental"),
 ("h12_cost", "300_dawn", "grief with no comfort in it, solo violin unaccompanied, cold strings entering, a valley dying, instrumental, no drums"),
 ("h13_gate", "320_mira_end", "unresolved farewell, solo piano and warm low strings, tender and unfinished, instrumental, no drums"),
 ("h14_ridge", "400_zodd_waits", "strange calm between enemies, low brass held long, sparse harp, wind, almost companionable, orchestral, instrumental"),
 ("h15_host", "420_army", "vast approaching horror, enormous choir, organ, bells rung wrong, sub bass, ecstatic and vile, orchestral, instrumental"),
 ("h16_walk", "430_guts_answer", "grim resolve, low string ostinato building, one defiant horn, drums entering late, walking toward it, orchestral, instrumental"),
]

film = collections.OrderedDict(
    title="THE HOUND", subtitle="a Berserk side story, episode one",
    ar="16:9", fps=24, seconds=6, tail=1.1, default_transition="cut",
    style_lora="qwen_image_2512_storybook_anime_lora.safetensors", style_strength=0.0,
    id_lora="ltx-2.3-id-lora-talkvid-3k.safetensors", id_strength=0.6,
    sheets=SHEETS, style=STYLE, characters=CHARS, voices=VOICES,
    music=[collections.OrderedDict(at_shot=a, prefix=p, bpm=b, key="D minor",
                                   seconds=40, level=1.0, tags=t)
           for (p, a, t), b in zip(MUSIC, [50, 140, 72, 56, 46, 40, 58, 66, 132, 144, 130, 48, 54, 44, 60, 88])],
    shots=S,
)
json.dump(film, open(OUT, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
ids = [x["id"] for x in S]
assert len(ids) == len(set(ids))
print(f"wrote {OUT}")
print(f"  shots {len(S)}   clips {sum(max(1,int(x.get('chain',1))) for x in S)}"
      f"   chained {sum(1 for x in S if x.get('chain'))}")
print(f"  narration words {sum(len(x['say'].split()) for x in S if x.get('say'))}"
      f"   dialogue lines {sum(1 for x in S if x.get('who'))}")
print(f"  ref-locked {sum(1 for x in S if x.get('ref'))}   cues {len(MUSIC)}")
