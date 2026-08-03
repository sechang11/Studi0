#!/usr/bin/env python3
"""Second pass on films/berserk.json - restores the arc the first pass compressed away.

Run AFTER build_berserk.py. Inserts by anchor id so the running order stays readable.

The first pass came out at 10m10s and, worse, had cut Doldrey - the Band of the Hawk's
defining victory and the film's best available set-piece. Also restored: the hundred-man
stand, Casca's rescue at the river (the beat that makes her and Guts real to each other),
the court intrigue that actually destroys Griffith, and the small Hawks who make the
Eclipse cost something.
"""
import collections, json, os

P = os.path.join(os.path.dirname(os.path.abspath(__file__)), "berserk.json")
film = json.load(open(P, encoding="utf-8"), object_pairs_hook=collections.OrderedDict)
shots = film["shots"]
by = {s["id"]: s for s in shots}


def mk(sid, prompt, motion, say=None, who=None, ref=None, sfx=None, look=None,
       seconds=None, chain=None, motions=None, tin=None, in_dur=None):
    d = collections.OrderedDict(id=sid)
    if tin:
        d["in"] = tin
    if in_dur:
        d["in_dur"] = in_dur
    if look:
        d["look"] = look
    if ref:
        d["ref"] = ref
    if chain:
        d["chain"] = chain
    if seconds:
        d["seconds"] = seconds
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
    return d


NEW = []   # (anchor_id, [shots to insert after it])

# ── the hundred-man stand ────────────────────────────────────────────────────
NEW.append(("250_guts_fights", [
 mk("252_bridge",
    "Wide shot of a narrow stone bridge over a gorge at dusk, {GUTS} standing alone at the near end with the enormous sword, and a hundred armoured soldiers packed on the far side coming toward him",
    "The mass of soldiers starts across the bridge. He sets his feet and lifts the huge blade. Nobody behind him. Wind through the gorge.",
    motions=["The first rank reaches him and he clears the width of the bridge in one arc; bodies go over the parapet into the gorge",
             "They come again in a press and he gives ground a single step at a time, the sword never stopping, dead piling at his feet",
             "He is bleeding from a dozen places and still standing when the far end of the bridge finally empties"],
    say="At a bridge whose name nobody bothered to write down, Guts held a hundred men on his own until they stopped coming.",
    ref=["GUTS"], look="fire", tin="dissolve", chain=4, seconds=32,
    sfx="A narrow stone bridge, a hundred armoured men advancing, a huge blade clearing an arc repeatedly, bodies falling into a gorge"),
 mk("254_griffith_sees",
    "Close shot of {GRIFFITH} on horseback at the far ridge lowering a spyglass, his face unreadable, the smoke of the bridge fight behind him",
    "He lowers the spyglass slowly and does not hand it to anyone. His horse shifts. Something crosses his face and is put away.",
    say="Griffith watched all of it, and said nothing at all for a long time afterwards.",
    ref=["GRIFFITH"], look="fire", tin="cut",
    sfx="Wind on a ridge, a horse, leather, distant fighting ending"),
]))

# ── the Hawks as people, and the river ───────────────────────────────────────
NEW.append(("290_price", [
 mk("292_pippin",
    "Warm shot in camp of an enormous quiet bald soldier sitting on an anvil eating, dwarfing the men around him, and a boy of about fourteen working a bellows beside him, firelight",
    "The huge man eats without hurrying. The boy pumps the bellows and grins up at him. The forge glows and throws light across both.",
    say="Pippin, who never raised his voice and could lift a horse. Rickert, who was fourteen and kept the horses.",
    look="fire", tin="dissolve",
    sfx="A camp forge, bellows, a big man eating, a boy laughing, iron"),
 mk("294_corkus",
    "Shot of a lean sneering soldier holding court over a dice game in camp, a cup in one hand, other men laughing at whatever he is saying, lamplight",
    "He throws the dice, spreads his hands at the result and says something that makes the others laugh. He is performing and knows it.",
    say="Corkus, who resented Guts from the first day and was not entirely wrong to.",
    look="fire", tin="cut",
    sfx="Dice on wood, men laughing, cups, a boastful voice pitched to carry"),
 mk("296_river",
    "Dramatic shot of a fast river in spate at night, {GUTS} waist deep in it with {CASCA} unconscious over his shoulder, fighting the current toward a rock shelf",
    "He forces one step at a time against the current with her weight over his shoulder. Water breaks over both of them. He does not let go.",
    say="Casca took a fever in the field and went into a river. Guts went in after her, which surprised everyone including him.",
    ref=["GUTS", "CASCA"], look="cold", tin="dissolve", seconds=7,
    sfx="A river in spate at night, water breaking over a man, laboured effort, stones underfoot"),
 mk("298_riverbank",
    "Intimate shot on a rock shelf by the river at dawn, {CASCA} wrapped in a wet cloak awake and shivering, {GUTS} sitting a careful distance away, mist on the water",
    "She surfaces from the fever and looks at him. He looks at the river. Mist moves. Neither of them says the obvious thing.",
    say="I have been afraid every single day since I was fourteen. He is the only place I put it down.",
    who="CASCA",
    ref=["CASCA", "GUTS"], look="dawn", tin="cut", seconds=7,
    sfx="A river at dawn, mist, someone shivering, birds beginning, quiet"),
]))

# ── Doldrey: the set-piece the first pass omitted ────────────────────────────
NEW.append(("330_casca_truth", [
 mk("332_doldrey",
    "Epic establishing wide shot of an enormous hill fortress at dawn, tiered stone walls and towers above a plain, thousands of defenders on the battlements, siege lines far below",
    "Banners lift on every tower. The camera pushes slowly in on the immense walls. Dust rises from the siege lines below. Utterly forbidding.",
    say="Doldrey. A fortress that had held for a hundred years against armies ten times the size of theirs.",
    look="dawn", tin="fade", in_dur=1.6, seconds=7,
    sfx="A vast fortress at dawn, banners, thousands of men on walls, a war horn far off"),
 mk("334_plan",
    "Shot of {GRIFFITH} in a command tent with a map spread on a table, pointing at one place on it, officers around him including {CASCA} and {GUTS}, lamplight",
    "He sets one finger on the map and holds it there. The officers lean in. Casca looks up at him sharply. Nobody argues.",
    say="Griffith split his own outnumbered force in half, which every officer present told him was suicide.",
    ref=["GRIFFITH", "CASCA"], look="fire", tin="cut", seconds=6,
    sfx="A command tent, a map, low urgent voices, lamplight, armour"),
 mk("336_casca_charge",
    "Dynamic wide shot of {CASCA} leading a cavalry wing at full gallop across the plain toward the fortress gate, sabre out, riders in a wedge behind her, dust and dawn light",
    "She rides at the head of the wedge, sabre up. The riders behind her hold formation. Dust boils up behind them. Full speed.",
    motions=["The wedge hits the defending line and splits it; horses and men go down on both sides as she cuts through and keeps going",
             "Her horse is killed under her; she rolls clear, comes up with the sabre and fights on foot in the press"],
    say="Casca took the field.",
    ref=["CASCA"], look="dawn", tin="cut", chain=3, seconds=24,
    sfx="A cavalry charge at full gallop, hundreds of hooves, two lines colliding, horses screaming, a woman shouting orders"),
 mk("338_adon",
    "Tense duel shot of {CASCA} on foot facing a large ornately armoured enemy commander with an elaborate helmet, both mid-fight, dust and bodies around them",
    "The big commander swings heavily and she turns it aside, circling. He talks while he fights. She does not answer.",
    motions=["He beats her back with sheer weight, and she lets him, giving ground and reading him",
             "She steps inside the next swing and puts the sabre through the gap in his ornate armour; he goes down mid-sentence"],
    say="Their commander made a long speech about her being a woman. She let him finish it.",
    ref=["CASCA"], look="dawn", tin="cut", chain=3, seconds=22,
    sfx="A duel on foot in a battlefield press, heavy blade on light blade, a boastful voice, a final wet stroke"),
 mk("340_guts_wall",
    "Vertiginous shot of {GUTS} climbing the sheer outer wall of the fortress alone with the enormous sword on his back, hand over hand up wet stone, the drop enormous below him",
    "He hauls himself up the sheer face hand over hand. Stones come loose and fall away below. The huge sword shifts on his back.",
    motions=["He reaches the battlement, comes over it into a knot of defenders and clears the walkway in two arcs",
             "He fights along the wall to the gatehouse, throws the winch bar over and the great gate begins to grind open below"],
    say="Guts went up the wall.",
    ref=["GUTS"], look="dawn", tin="cut", chain=3, seconds=24,
    sfx="Hands on wet stone, stones falling a long way, then close fighting on a battlement, a huge gate winch grinding"),
 mk("342_gate",
    "Spectacular wide shot from inside the fortress as the enormous gates grind open and the Hawk cavalry pours through into the courtyard, banner at the front, defenders scattering",
    "The gates grind wide and the cavalry floods through the gap. The banner comes through first. Defenders break and run. Overwhelming momentum.",
    motions=["The charge spreads through the courtyard and up the tiers; the defence comes apart in front of it",
             "The hawk banner is carried up onto the highest tower and run up the pole as the fortress falls"],
    say="Doldrey fell in a single morning.",
    look="dawn", tin="cut", chain=3, seconds=26,
    sfx="Enormous gates grinding open, a cavalry charge into a stone courtyard, a rout, a banner raised, cheering"),
 mk("344_cheer",
    "Triumphant wide shot of thousands of soldiers filling the fortress courtyard with weapons raised, {GRIFFITH} on the steps above them in white armour, morning light, banners everywhere",
    "The whole courtyard raises weapons and roars. He stands above them, still, and lets it come. Banners snap overhead.",
    say="The kingdom had a hero. The nobility had a problem.",
    ref=["GRIFFITH"], look="dawn", tin="dissolve", seconds=6,
    sfx="Thousands of soldiers cheering in a stone courtyard, weapons on shields, banners, bells"),
]))

# ── court, Charlotte, the plot ───────────────────────────────────────────────
NEW.append(("350_court", [
 mk("352_charlotte",
    "Delicate shot in a palace garden of a young princess in pale blue speaking with {GRIFFITH}, both formal and careful, courtiers watching from a distance",
    "She says something and looks down. He answers without moving closer. A servant watches from the colonnade. Everything is observed.",
    say="The king's daughter found him fascinating. Griffith let her, because a throne can be reached by more than one road.",
    ref=["GRIFFITH"], tin="dissolve", seconds=6,
    sfx="A formal garden, fountain, distant courtly voices, careful footsteps on gravel"),
 mk("354_nobles",
    "Conspiratorial shot in a dim panelled room of three richly dressed nobles leaning together over wine, one of them older and calm, candlelight from below",
    "The three lean in together. The calm older one speaks and the other two go still. Candlelight throws their shadows up the panelling.",
    say="The court could not beat him in the field, so they went looking for a way to do it indoors.",
    tin="cut", seconds=6,
    sfx="A small panelled room, wine poured, low conspiratorial voices, a fire"),
 mk("356_assassins",
    "Violent night shot of four hooded assassins with long knives coming over a balcony rail into a lamplit bedchamber, {GRIFFITH} already turning from a desk",
    "The hooded figures come over the rail fast and low. Griffith turns from the desk. The lamp goes over. Immediate violence.",
    motions=["{GUTS} comes through the door into the middle of it and the enormous sword takes two of them off their feet",
             "The last one goes through the window; Guts stands in the wreckage of the room breathing hard, Griffith untouched behind him"],
    ref=["GRIFFITH", "GUTS"], look="fire", tin="cut", chain=3, seconds=20,
    sfx="Glass and a lamp going over, fast knife work, a huge blade in a small room, a body through a window, sudden quiet"),
 mk("358_after_assassins",
    "Two-shot in the wrecked bedchamber, {GUTS} breathing hard among the dead and {GRIFFITH} calmly righting the fallen lamp, blood on the floor between them",
    "Griffith picks the lamp up, sets it straight and adjusts the wick. Guts stares at him. The room steadies into lamplight again.",
    say="This is what I meant. You are the only one I do not have to explain myself to.",
    who="GRIFFITH",
    ref=["GUTS", "GRIFFITH"], look="fire", tin="cut",
    sfx="A lamp righted and trimmed, blood dripping, one man breathing hard, calm quiet"),
]))

# ── the Skull Knight ────────────────────────────────────────────────────────
NEW.append(("440_zodd_warning", [
 mk("442_skull",
    "Eerie shot on a moonlit road of a skeletal armoured rider on a black horse, its helm a bare skull, a great sword across its back, blocking the way, mist to the knees",
    "The horse steps once and stops. The skull helm turns toward camera. Mist curls around the hooves. It is entirely unhurried.",
    say="Something else on that road had been trying to stop this for four hundred years.",
    look="cold", tin="fade", in_dur=1.4, seconds=6,
    sfx="A horse on a moonlit road, armour that sounds hollow, mist, a voice like stone"),
 mk("444_skull_warn",
    "Close shot of the skeletal helm, empty sockets lit faintly from within, the moon behind it, mist drifting across the frame",
    "The empty sockets kindle very faintly. The helm tilts. It speaks briefly and turns the horse away without waiting.",
    say="Every thousand years the world lets one man buy what he wants. The price is always the same, and it is always paid by other people.",
    who="ZODD",
    look="cold", tin="cut",
    sfx="A hollow resonant voice, harness, hooves turning away on a road, mist"),
]))

# ── the break, seen by the Hawks ────────────────────────────────────────────
NEW.append(("540_tell_casca", [
 mk("542_judeau_knows",
    "Quiet two-shot at a camp table of {JUDEAU} across from {GUTS}, Judeau turning a knife over and not looking up, both of them aware of what is being said",
    "Judeau turns the knife over and over without looking up. He says something short and finally does look up, with a sad half smile.",
    say="She will never say it to you, so I will. She is in love with him and she is in love with you and it is going to tear her in half.",
    who="JUDEAU",
    ref=["JUDEAU", "GUTS"], look="fire", tin="cut",
    sfx="A camp table at night, a knife turned on wood, low voices, a fire outside"),
]))

# ── Griffith's ruin ────────────────────────────────────────────────────────
NEW.append(("580_griffith_alone", [
 mk("582_charlotte_night",
    "Restrained shot of a palace corridor at night, a door standing half open with warm light behind it, a white cloak discarded across a chair, no figures in frame",
    "The door stands half open. Warm light falls across the corridor stone. The cloak on the chair does not move. Nothing else happens.",
    say="That night Griffith did something reckless with the king's daughter, and by morning the whole court knew.",
    look="fire", tin="dissolve", seconds=6,
    sfx="A quiet palace corridor at night, a distant door, fabric settling, stillness"),
 mk("584_king",
    "Shot of an aging king on a throne gripping the arms of it, face dark with fury, courtiers pressed back against the walls of the hall",
    "His hands close hard on the throne arms. He says one thing, quietly. The courtiers go absolutely still. Candle flames stand straight.",
    say="The king had loved him like a son, right up until the moment he had a reason not to.",
    tin="cut", seconds=5,
    sfx="A great hall gone silent, one quiet furious voice, hands on wood, candles"),
]))

# ── the run, and the jealousy that triggers everything ─────────────────────
NEW.append(("680_cart", [
 mk("682_almost",
    "Tender restrained two-shot at a night camp of {CASCA} asleep against {GUTS}'s shoulder by a low fire, his arm awkwardly still so as not to wake her",
    "She sleeps against his shoulder. He holds absolutely still, arm frozen where it is. The fire burns low. He looks at nothing.",
    say="Somewhere in those weeks, without either of them deciding to, they became the thing that kept the other one upright.",
    ref=["CASCA", "GUTS"], look="fire", tin="dissolve", seconds=7,
    sfx="A low fire at night, two people breathing, a cart settling, wind"),
 mk("684_watching",
    "Chilling shot from inside the cart of the hooded ruined figure sitting motionless, and past it in the firelight the two figures asleep together, the hood turned exactly toward them",
    "The hooded head is turned exactly toward the two by the fire and does not move at all. One thin hand closes slowly on the blanket.",
    say="From the cart, the ruined thing that had been Griffith watched them, and understood that he had lost even this.",
    look="fire", tin="cut", seconds=7,
    sfx="A cart at night, a blanket gripped, a fire beyond, breathing that is not quite steady"),
]))

# ── the Eclipse: Pippin and Corkus, so it costs something ─────────────────
NEW.append(("750_judeau", [
 mk("752_pippin_dies",
    "Silhouette shot in red darkness of an enormous soldier holding a stone doorway shut against a mass of shapes with his own body, arms braced wide, others escaping behind him",
    "He braces across the doorway with both arms and takes the whole weight of what is on the other side. Behind him figures run. He holds.",
    say="Pippin held a doorway with his body so the others could get through it, and never said a word about it.",
    look="eclipse", tin="cut", seconds=5,
    sfx="An enormous man braced against a door, something vast pressing on the other side, stone cracking"),
 mk("754_corkus",
    "Shot in red darkness of the lean sneering soldier on his knees in the open, all his bravado gone, staring up at something enormous off frame",
    "He is on his knees with his sword forgotten in the dirt beside him, looking up. Everything he used to say is gone out of his face.",
    say="Corkus, who had never believed in any of it, died still explaining that none of this was possible.",
    look="eclipse", tin="cut",
    sfx="A man on his knees talking too fast, something enormous approaching, chaos beyond"),
]))

# ── coda: Rickert ─────────────────────────────────────────────────────────
NEW.append(("810_casca_after", [
 mk("812_rickert",
    "Quiet shot of a boy of about fourteen alone on a hillside above an empty valley at dawn, holding a horse's bridle, waiting for a company that is not coming",
    "He stands holding the bridle and watching the empty valley road. The horse shifts behind him. The road stays empty. He keeps waiting.",
    say="Rickert had been sent away with the wounded a week earlier. He was the only Hawk who was not there, and he waited on that hill for three days.",
    look="dawn", tin="dissolve", seconds=7,
    sfx="A hillside at dawn, a horse shifting, wind in grass, an empty road, birds"),
]))

added = 0
for anchor, block in NEW:
    if anchor not in by:
        raise SystemExit(f"anchor {anchor} not found")
    i = next(k for k, s in enumerate(shots) if s["id"] == anchor) + 1
    for off, sd in enumerate(block):
        if sd["id"] in by:
            continue
        shots.insert(i + off, sd)
        by[sd["id"]] = sd
        added += 1

# extend the two biggest existing fights now that the film has room for them
for sid, ch, sec in (("410_zodd_fight", 5, 40), ("550_duel2", 5, 38)):
    if sid in by:
        by[sid]["chain"] = ch
        by[sid]["seconds"] = sec
if "410_zodd_fight" in by:
    by["410_zodd_fight"]["motion5"] = ("The beast breaks off, hurls Guts aside and leaps for the "
                                       "broken roof; Guts lands hard and drags himself up on the sword")
if "550_duel2" in by:
    by["550_duel2"]["motion5"] = ("Guts lowers the great sword and stands in the falling snow; "
                                  "neither of them moves, and the watching walls stay silent")

# extra cues for the new sequences
film["music"].extend([
 collections.OrderedDict(at_shot="252_bridge", prefix="m20_bridge", bpm=132, key="D minor",
   seconds=40, level=1.0,
   tags="relentless last-stand battle music, driving low string ostinato, war drums, brass held long, exhausted and unbroken, orchestral, instrumental"),
 collections.OrderedDict(at_shot="332_doldrey", prefix="m21_doldrey", bpm=126, key="C minor",
   seconds=90, level=1.0,
   tags="grand assault on a fortress, full orchestra, hammered timpani, soaring heroic brass over driving strings, choir on one syllable, triumphant and enormous, instrumental"),
 collections.OrderedDict(at_shot="296_river", prefix="m22_river", bpm=64, key="A minor",
   seconds=44, level=1.0,
   tags="urgent then tender, tremolo strings resolving to solo cello and harp, water, care rather than romance, orchestral, instrumental, no drums"),
 collections.OrderedDict(at_shot="442_skull", prefix="m23_skull", bpm=48, key="F minor",
   seconds=40, level=1.0,
   tags="ancient warning, hollow low brass, bowed metal, a slow tolling bell, sub bass, something older than the story, dark orchestral, instrumental"),
 collections.OrderedDict(at_shot="812_rickert", prefix="m24_rickert", bpm=56, key="C major",
   seconds=50, level=1.0,
   tags="quiet unbearable hope, solo flute over sustained strings, a boy waiting, warm and wrong, orchestral, instrumental, no drums"),
])

json.dump(film, open(P, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
ids = [s["id"] for s in shots]
assert len(ids) == len(set(ids)), "duplicate ids"
clips = sum(max(1, int(s.get("chain", 1))) for s in shots)
print(f"inserted {added} shots -> {len(shots)} total, {clips} clips")
print(f"  chained scenes {sum(1 for s in shots if s.get('chain'))}")
print(f"  narration words {sum(len(s['say'].split()) for s in shots if s.get('say'))}")
print(f"  music cues {len(film['music'])}")
