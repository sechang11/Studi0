#!/usr/bin/env python3
"""Author THE SALT ROAD - three episodes - as films/*.json for epic.py.

    python3 write_salt_road.py            # writes films/salt_road_ep0{1,2,3}.json

AN ORIGINAL STORY IN THE D&D IDIOM. The published adventures are copyrighted text, so
nothing here is lifted from one. What IS borrowed is the furniture of the genre, which
belongs to nobody: the tavern hook, the ruined road, the sealed door, the delve, the thing
in the dark that would rather talk than fight. Written as an ACTUAL PLAY - the narrator is
the Dungeon Master running the table - which is both truer to how these stories are really
told and, usefully, gives the film a single consistent narrating voice.

KEYS ARE SPELLED THE WAY THE NODE SPELLS THEM. ACE-Step's keyscale widget is a fixed
34-item list that wants `Bb minor`, not `B flat minor`, and a value outside the list is a
hard prompt-validation error that kills the render before it prints anything. Twenty jobs
were lost to that earlier today. Every key below is from the list.
"""
import json, os

import argparse
argparse.ArgumentParser(description='write salt road').parse_args()
# ^ the CLI contract: --help exits HERE, before any work below runs.
ROOT = "/home/k4shix/shared/comfy-studio"

STYLE_BASE = ("dark fantasy tabletop illustration, painted in gouache and ink, heavy "
              "shadow, painterly brushwork, muted earth palette, detailed faces, "
              "the look of a roleplaying rulebook plate, cinematic widescreen composition")

LOOKS = {
    "default": STYLE_BASE,
    "lamp":    STYLE_BASE + ", warm lamplight and deep brown shadow, cosy and close",
    "cold":    STYLE_BASE + ", flat grey overcast light, thin rain, desaturated, bleak",
    "dark":    STYLE_BASE + ", near darkness, a single cold light source, crushed shadow",
    "fire":    STYLE_BASE + ", firelight from below, deep orange against black, chiaroscuro",
    "gold":    STYLE_BASE + ", green-gold glow rising from below, sickly and beautiful",
    "table":   ("overhead photograph-style painted illustration of a wooden tabletop, "
                "hand-drawn hex map, scattered polyhedral dice, pewter miniatures, "
                "candlelight, warm and intimate, shallow depth of field"),
}

CHARACTERS = {
    "BRENNA":   "the scarred human woman sellsword in ring-mail from the reference image",
    "MIRIEL":   "the young silver-haired elf wizard in a blue coat from the reference image",
    "DURGAN":   "the old grey-bearded dwarf cleric in a dented breastplate from the "
                "reference image",
    "SKIVV":    "the small ginger-haired halfling rogue in a green cloak from the "
                "reference image",
    "VESSARAX": "the vast ancient green dragon with a broken iron collar from the "
                "reference image",
}

SHEETS = {
    "BRENNA": "sheet_dnd_brenna.png", "MIRIEL": "sheet_dnd_miriel.png",
    "DURGAN": "sheet_dnd_durgan.png", "SKIVV": "sheet_dnd_skivv.png",
    "VESSARAX": "sheet_dnd_vessarax.png",
}

V = "voices_examples/"
VOICES = {
    # The Dungeon Master. One voice carries all three episodes, which is what makes them
    # feel like one table rather than three films.
    "NARRATOR": {"engine": "higgs_v3", "voice": V + "higgs_audio/chadwick.wav"},
    "BRENNA":   {"engine": "higgs_v3", "voice": V + "female/female_01.wav"},
    "MIRIEL":   {"engine": "higgs_v3", "voice": V + "female/female_04_maya.wav"},
    "DURGAN":   {"engine": "higgs_v3", "voice": V + "male/male_04_frank.wav"},
    "SKIVV":    {"engine": "higgs_v3", "voice": V + "male/male_03_carter.wav"},
    "VESSARAX": {"engine": "higgs_v3", "voice": V + "higgs_audio/vex.wav"},
}


def s(id, look, prompt, motion, say=None, who=None, sfx=None, titles=None, seconds=None):
    d = {"id": id, "look": look, "prompt": prompt, "motion": motion}
    if say:
        d["say"] = say
    if who:
        d["who"] = who
    if sfx:
        d["sfx"] = sfx
    if titles:
        d["titles"] = titles
    if seconds:
        d["seconds"] = seconds
    return d


# ─── EPISODE ONE ────────────────────────────────────────────────────────────────────
EP1 = [
    s("010_table", "table",
      "Overhead view of a candlelit wooden table, a hand-drawn hex map of a river valley "
      "weighted down with a tankard, four pewter miniatures standing at the map's edge, a "
      "scatter of dice, one twenty-sided die resting on a twenty",
      "The candle flame wavers. A hand enters frame and sets a fifth miniature down at the "
      "far end of the map. Slow push in on the dice.",
      "Every campaign begins the same way. Four people who should not trust each other, "
      "one road, and a rumour worth more than it ought to be.",
      sfx="A quiet room, a candle guttering, dice settling on wood, no music",
      titles=[{"text": "THE SALT ROAD", "at": 1.2, "hold": 3.4, "scale": 0.075}]),

    s("020_valley", "cold",
      "Extreme wide shot of a river valley under low grey cloud, a rutted trade road "
      "winding between wet green hills, a walled village small in the distance, smoke from "
      "three chimneys, no travellers on the road at all",
      "Rain drifts across the valley in a slow sheet. The smoke bends. Nothing moves on the "
      "road. Very slow push in toward the village.",
      "The valley is called Marrow Ford. For ninety years the salt carts came down that "
      "road from the pans in the east, and for ninety years nothing much happened here. "
      "That is the kind of place a story starts.",
      sfx="Cold rain on open hillside, wind, distant rooks, no voices",
      titles=[{"text": "EPISODE ONE - THE DOOR IN THE HILL", "at": 2.0, "hold": 4.0,
               "scale": 0.034}]),

    s("030_gate", "cold",
      "A village gate of grey timber standing open, unattended, rain darkening the wood, a "
      "hand-lettered notice board beside it thick with curling weathered notices, muddy "
      "ruts leading in",
      "Rain runs off the crossbeam in a thin line. One notice lifts and falls in the wind. "
      "Slow drift left to right along the boards.",
      "Six weeks ago the carts stopped. No word, no wreckage, no ransom. Just an empty road "
      "and a village slowly running out of the one thing it sells.",
      sfx="Rain on timber, wind, wet rope creaking, a distant door"),

    s("040_tavern_ext", "lamp",
      "A low stone tavern at dusk in the rain, warm yellow light in two small windows, a "
      "faded painted sign of a salt barrel swinging above the door, wet cobbles reflecting "
      "the light",
      "The sign swings slowly. Rain falls through the lamplight. The door opens, spilling "
      "light across the wet stones, and closes again. Slow push in.",
      "Which is how four strangers came to be sitting in the same room on the same wet "
      "evening, each of them there for a different reason, none of them saying so.",
      sfx="Heavy rain on cobbles, a wooden sign creaking, muffled voices behind a door"),

    s("050_brenna", "lamp",
      "Interior tavern, medium close-up of BRENNA sitting alone at a corner table with her "
      "back to the wall, a cup untouched in front of her, watching the room over the rim, "
      "warm lamplight, smoke haze",
      "She turns the cup a quarter turn without drinking. Her eyes move to the door and "
      "back. Firelight flickers on the mail at her shoulder. Slow push in.",
      "Brenna Vosk. Sellsword. Eleven years of other people's wars and nothing to show for "
      "it but the scar and the opinions.",
      sfx="Low tavern murmur, a fire, cups on wood"),

    s("055_brenna_line", "lamp",
      "Interior tavern, close-up of BRENNA looking directly across the table at someone "
      "out of frame, unimpressed, one eyebrow slightly raised, warm lamplight",
      "She sets the cup down with a small deliberate movement and leans back. Slight push in.",
      "I don't need to like you. I need you to not run.", who="BRENNA",
      sfx="A cup set down on wood, low murmur"),

    s("060_miriel", "lamp",
      "Interior tavern, medium shot of MIRIEL at a table covered in open books and loose "
      "parchment, ink on her fingers, copying something by candlelight, oblivious to the "
      "room around her",
      "She turns a page, dips the pen, writes. A drop of ink falls on the table and she "
      "does not notice. The candle gutters. Slow drift in.",
      "Miriel of the Ninth Stair. Sent out from her order to survey a valley nobody cared "
      "about, and quietly delighted that something had finally gone wrong in it.",
      sfx="A pen on parchment, pages, a candle, distant murmur"),

    s("070_durgan", "lamp",
      "Interior tavern, medium close-up of DURGAN sitting by the fire with his hands flat "
      "on the table, a tarnished sun symbol on his chest catching the light, staring into "
      "the middle distance, not drinking",
      "The firelight moves across his face. He closes one hand slowly into a fist and opens "
      "it again. Very slow push in.",
      "Durgan Oakenfist had been a priest for sixty years. He would have told you he still "
      "was. He had stopped expecting an answer some time ago.",
      sfx="A fire close by, low tavern murmur, a chair"),

    s("080_skivv", "lamp",
      "Interior tavern, medium shot of SKIVV standing on a bench mid-story with both arms "
      "spread wide, grinning, three villagers laughing around him, one villager quietly "
      "checking his own purse",
      "Skivv throws his arms wider. The villagers laugh. Behind him a hand withdraws from a "
      "coat that is not his. Slow push in.",
      "And Skivv. Who had three names in this valley, two of them owed money.",
      sfx="Laughter, a bench creaking, tankards, general tavern noise"),

    s("085_skivv_line", "lamp",
      "Interior tavern, close-up of SKIVV leaning in over a table conspiratorially, "
      "grinning, firelight on his face",
      "He leans further in, glances left and right, and lowers his voice. Slight push in.",
      "I'm not saying I know where the carts went. I'm saying I know a man who charged me "
      "four silver to say he did.", who="SKIVV",
      sfx="Low tavern murmur, a tankard set down"),

    s("090_map_table", "lamp",
      "Interior tavern, overhead shot of a rough map unrolled on a table between four pairs "
      "of hands, a finger pointing to a mark on it, cups pushed to the edges, lamplight",
      "The finger taps the map twice. A second hand moves a cup out of the way. The map "
      "corner curls up and is flattened again. Slow push in on the marked point.",
      "The tavern keeper had a map. On it, eight miles east where the road bent around a "
      "hill, someone had drawn a small square and written one word. Sealed.",
      sfx="Paper on wood, cups, low voices, a fire"),

    s("100_road_out", "cold",
      "Wide shot of four small figures walking east along a rutted muddy road at first "
      "light, wet hills rising on either side, low mist in the hollows, seen from behind "
      "and far back",
      "They walk. Mist moves across the road ahead of them. A bird lifts from the verge. "
      "Very slow push in.",
      "They left at first light, with the understanding that this was a paid errand and "
      "nothing more.",
      sfx="Boots in mud, wind over open ground, a single bird, no music"),

    s("110_wreck", "cold",
      "A wrecked salt cart lying on its side across a muddy road, one wheel missing, white "
      "salt spilled and dissolving into the mud in long streaks, harness cut clean, no "
      "bodies anywhere, grey rain light",
      "Rain falls on the spilled salt. The cut harness sways slightly. The camera drifts "
      "slowly along the wreck from the wheel to the empty harness.",
      "They found the first cart four miles out. Then the second. Then the third. No blood. "
      "No bodies. No cargo. Every harness cut, not broken.",
      sfx="Rain on wood and mud, wind, leather creaking, no voices"),

    s("115_harness", "cold",
      "Extreme close-up of a cut leather harness strap held in a scarred hand, the cut end "
      "clean and straight, rain on the leather",
      "The hand turns the strap over slowly to show the clean edge. Rain runs off it.",
      "Cut, Brenna said. Not chewed. Cut. Something out here had hands, and patience, and "
      "a knife.",
      sfx="Rain on leather, a slow breath"),

    s("120_tracks", "cold",
      "Low angle close on churned mud beside a road, many small bare footprints overlapping "
      "in a wide trail leading away from the road toward a hillside, rain filling them",
      "Rain slowly fills the prints. The camera drifts along the trail toward the hill.",
      "And the trail went off the road, up the hill, in the wrong direction entirely. Which "
      "is when Miriel said the thing that decided the next three days.",
      sfx="Rain on mud, wind, distant water"),

    s("125_miriel_line", "cold",
      "Medium close-up of MIRIEL crouched at the edge of a muddy trail in the rain, hood "
      "back, looking up and off toward a hillside, rain in her hair",
      "She rises slowly, still looking up the hill, and pushes her wet hair back. Slight "
      "push in.",
      "They're not raiders. Raiders take the cart. Something took the salt and left "
      "everything worth money in the mud.", who="MIRIEL",
      sfx="Rain, wind, a boot in wet ground"),

    s("130_ambush", "cold",
      "Sudden wide shot of six small ragged goblins breaking from the gorse on both sides "
      "of a hillside path with crude spears, mid-charge, mouths open, the four travellers "
      "turning to meet them",
      "The goblins burst from the undergrowth. The party turns. Everything moves at once. "
      "Fast, chaotic, handheld.",
      "The dice, at this point, went very badly for everyone.",
      sfx="Sudden shrieking cries, gorse thrashing, running feet, shouting, no music"),

    s("140_brenna_fight", "cold",
      "Medium shot of BRENNA in the rain with her longsword already moving, one goblin "
      "falling away from her, another coming in low from her left, mud and water thrown up "
      "around her boots",
      "The sword comes across. The first goblin drops. She is already turning toward the "
      "second. Water sprays. Fast, weighty motion.",
      sfx="Steel on wood, a body in mud, shouting, hard breathing"),

    s("145_durgan_fight", "cold",
      "Medium shot of DURGAN swinging a warhammer two-handed in the rain, a goblin "
      "sprawling backward off the blow, his face set and grim, the sun symbol swinging at "
      "his chest",
      "The hammer comes round and connects. The goblin is thrown clear. He plants his feet "
      "and turns. Heavy, slow, deliberate motion.",
      sfx="A heavy impact, a cry, rain, boots in mud"),

    s("150_after", "cold",
      "Wide shot of a hillside path after the fight, four figures standing among fallen "
      "goblin bodies in the rain, one of them bent over with hands on knees, rain washing "
      "the mud",
      "One figure straightens slowly. Rain falls steadily. Nobody speaks. Very slow drift "
      "back and up.",
      "Four goblins dead. Two run off into the gorse. And Skivv with a spear graze along "
      "his ribs he would describe, for the rest of his life, as a mortal wound.",
      sfx="Steady rain, hard breathing slowing, wind, a dropped weapon"),

    s("160_door_find", "cold",
      "A hillside of wet gorse and heather, a low arch of grey dwarven stonework half "
      "buried in the slope, mossed over, deliberately built and long abandoned, small "
      "footprints in the mud leading straight to it",
      "Rain runs down the mossed stone. The camera pushes slowly in on the arch until the "
      "carving on it begins to resolve.",
      "The trail ended at a door that should not have been there. Dwarven work, three "
      "hundred years old at least, and sealed from the outside.",
      sfx="Rain on stone, wind across a hillside, water dripping in a hollow space"),

    s("170_seal", "dark",
      "Extreme close-up of a carved dwarven seal on wet grey stone, a setting sun above two "
      "crossed bars, moss growing in the grooves, an old iron pin driven through the "
      "centre of it",
      "Water runs down the carving. The camera pushes very slowly in on the iron pin.",
      "Durgan went very quiet. Because he knew the mark. It was his own order's, and it did "
      "not mean keep out.",
      sfx="Water dripping on stone, wind, a low hollow resonance"),

    s("175_durgan_line", "dark",
      "Close-up of DURGAN in the rain looking at carved stone just out of frame, his face "
      "lit from below by a lantern, the tarnished sun symbol at his chest, deeply uneasy",
      "He reaches out slowly and touches the stone, then draws his hand back. Slight push in.",
      "It means we put something in here. And it means we meant it to stay.", who="DURGAN",
      sfx="Rain, a lantern creaking, a slow breath"),

    s("180_open", "dark",
      "The dwarven door standing open into total blackness, four figures silhouetted "
      "against the grey rain light at the threshold, lantern light reaching only a few feet "
      "into the dark, stale air visible as faint mist",
      "The door settles fully open. A slow breath of stale air drifts out through the "
      "lantern light. Nobody has stepped in yet. Very slow push toward the dark.",
      "They opened it anyway. They always open it. That is the whole reason there is a game "
      "at all.",
      sfx="Heavy stone grinding, a long low exhale of air, rain behind, silence ahead"),

    s("190_end_table", "table",
      "Overhead view of the candlelit table, four miniatures now standing together at the "
      "mouth of a drawn tunnel on the map, a twenty-sided die rolling to a stop showing a "
      "one, a hand withdrawing",
      "The die rolls, slows, and stops on a one. The hand withdraws from frame. The candle "
      "flame leans. Slow push in on the die.",
      "We stopped there for the night. Somebody had to drive home, and Skivv's player "
      "wanted to look up what a halfling can carry.",
      sfx="A die rolling and stopping on wood, a chair pushed back, quiet room tone",
      titles=[{"text": "EPISODE TWO - WHAT THE DARK KEPT", "at": 2.6, "hold": 3.6,
               "scale": 0.034}]),
]

MUSIC1 = [
    {"at_shot": "010_table", "prefix": "m01_table", "bpm": 62, "key": "D minor",
     "seconds": 26.0, "level": 0.85,
     "tags": "warm solo acoustic guitar and low strings, curious and inviting, a story "
             "beginning, sparse, instrumental, no drums"},
    {"at_shot": "100_road_out", "prefix": "m02_road", "bpm": 84, "key": "A minor",
     "seconds": 34.0, "level": 0.8,
     "tags": "walking pace folk strings and low whistle, grey and determined, travelling "
             "music, light hand percussion, instrumental"},
    {"at_shot": "130_ambush", "prefix": "m03_fight", "bpm": 132, "key": "E minor",
     "seconds": 26.0, "level": 0.95,
     "tags": "urgent driving percussion and harsh low strings, chaotic, dangerous, "
             "orchestral action, instrumental"},
    {"at_shot": "160_door_find", "prefix": "m04_door", "bpm": 54, "key": "C minor",
     "seconds": 40.0, "level": 0.9,
     "tags": "deep drone under a single distant horn, dread and awe, something very old, "
             "sparse dark orchestral, instrumental, no drums"},
]


def film(title, subtitle, shots, music):
    return {
        "title": title, "subtitle": subtitle,
        "ar": "16:9", "fps": 24, "seconds": 6, "tail": 1.1,
        "default_transition": "cut",
        "style_lora": "", "style_strength": 0.0,
        "id_lora": "ltx-2.3-id-lora-talkvid-3k.safetensors", "id_strength": 0.6,
        "engine": "higgs_v3",
        "sheets": SHEETS, "style": LOOKS, "characters": CHARACTERS, "voices": VOICES,
        "music": music, "shots": shots,
    }


def main():
    os.makedirs(os.path.join(ROOT, "films"), exist_ok=True)
    out = os.path.join(ROOT, "films", "salt_road_ep01.json")
    f = film("THE SALT ROAD EP1", "episode one - the door in the hill", EP1, MUSIC1)
    json.dump(f, open(out, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    spoken = sum(1 for x in EP1 if x.get("say"))
    print("%s  %d shots, %d spoken, %d cues" % (out, len(EP1), spoken, len(MUSIC1)))


if __name__ == "__main__":
    main()
