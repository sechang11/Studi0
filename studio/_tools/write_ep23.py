#!/usr/bin/env python3
"""Episodes two and three of THE SALT ROAD. Imports the shared world from episode one.

Kept in a second file only so the first one stays readable; the style map, cast, sheets and
voice casting all come from write_salt_road.py so the three episodes cannot drift apart.
That matters more than usual here: the Dungeon Master's voice IS the through-line, and a
narrator who changed between episodes would break the conceit completely.
"""
import json, os, sys

import argparse
argparse.ArgumentParser(description='write ep23').parse_args()
# ^ the CLI contract: --help exits HERE, before any work below runs.
ROOT = "/home/k4shix/shared/comfy-studio"
sys.path.insert(0, os.path.join(ROOT, "studio", "_tools"))
from write_salt_road import s, film            # noqa: E402

# ─── EPISODE TWO ────────────────────────────────────────────────────────────────────
EP2 = [
    s("200_table", "table",
      "Overhead view of a candlelit table, a hand-drawn map now weighted open at a tunnel "
      "system, four pewter miniatures standing just inside the entrance, a fresh mug, a "
      "pencil laid across the map",
      "A hand slides the four miniatures forward together one step into the drawn tunnel. "
      "The candle steadies. Slow push in.",
      "Last week they opened a door that a dwarven order sealed three hundred years ago. "
      "This week they go in. Everyone at the table already knows this is a mistake.",
      sfx="Quiet room, candle, a pencil set down, miniatures on paper",
      titles=[{"text": "EPISODE TWO - WHAT THE DARK KEPT", "at": 1.4, "hold": 3.8,
               "scale": 0.034}]),

    s("210_entry", "dark",
      "Interior of a dwarven tunnel just past the entrance, squared grey stonework running "
      "into blackness, a single lantern held high throwing light a few feet, four figures "
      "small against the scale of it, dust hanging in the beam",
      "Dust drifts through the lantern light. The lantern sways slightly and the shadows "
      "swing with it. Slow push forward into the dark.",
      "The air was dry and dead and three hundred years old, and it moved. Which meant "
      "something, somewhere ahead, was open to the sky.",
      sfx="Boots on dry stone, a lantern handle creaking, a faint draught, deep silence"),

    s("220_hall", "dark",
      "A vast dwarven hall in near darkness, two rows of enormous square pillars "
      "disappearing into blackness, a fallen ceiling slab, lantern light reaching only the "
      "nearest pillar, immense scale",
      "The lantern light slides across one pillar as they pass. The dark beyond does not "
      "change. Very slow push in between the pillars.",
      "Miriel started counting pillars and stopped at forty. Whatever this had been, it was "
      "not a mine. Nobody digs a hall like that to get at salt.",
      sfx="Footsteps echoing in a very large stone space, a slow draught, distant dripping"),

    s("230_carvings", "dark",
      "Close on a carved stone wall lit by a raised lantern, a long relief of small robed "
      "dwarven figures carrying something large and bound in chains, the carving deliberate "
      "and repetitive, moss and dust in the grooves",
      "The lantern light travels slowly along the relief from left to right, revealing more "
      "figures and more chain.",
      "The walls told the story, in the way that walls do, which is to say proudly and "
      "without any of the useful details.",
      sfx="A lantern creaking, a hand brushing dust from stone, echoing drips"),

    s("235_miriel_line", "dark",
      "Close-up of MIRIEL holding a lantern up to a carved wall, her face lit from one "
      "side, silver hair bright in the light, reading the carving with her lips moving",
      "She moves the lantern slightly to light the next section and her eyes track across "
      "it. Slight push in.",
      "They're not carrying it out. Look at the feet. They're all facing in. They carried "
      "it down here on purpose.", who="MIRIEL",
      sfx="A lantern creaking, quiet breathing, a large echoing space"),

    s("240_warren", "fire",
      "A dwarven side chamber crudely converted into a goblin warren, filthy hide "
      "partitions strung between carved pillars, a low fire, stolen sacks of salt stacked "
      "in a corner, bones and refuse, seen from a dark doorway",
      "The fire flickers across the hides. A shadow crosses behind a partition. The camera "
      "holds in the dark doorway, then pushes very slowly forward.",
      "The goblins had been living in it for perhaps forty years. And there, stacked "
      "against a carved pillar older than the kingdom, were six weeks of stolen salt.",
      sfx="A crackling fire, muttering voices in a strange tongue, hides moving, dripping"),

    s("245_salt_stack", "fire",
      "Close on stacked sacks of white salt against ancient carved dwarven stonework, "
      "firelight on the coarse cloth, one sack split with salt spilling out, tally marks "
      "scratched crudely into the pillar beside them",
      "Firelight moves across the sacks. A little salt trickles from the split seam. Slow "
      "push in on the tally marks.",
      "Not eaten. Not sold. Stacked, and counted, and kept. Somebody down here was keeping "
      "a tally.",
      sfx="A distant fire, a faint trickle of grain, low guttural voices far off"),

    s("250_skivv_sneak", "fire",
      "Low angle of SKIVV pressed flat against a carved pillar in shadow, one hand raised "
      "behind him signalling stop, firelight from the chamber beyond edging his face, "
      "entirely serious for once",
      "His raised hand closes into a fist. He does not move. Behind him a goblin shadow "
      "passes across the firelit wall. Very slow push in.",
      sfx="A fire, footsteps passing close, held breath, cloth on stone"),

    s("255_skivv_line", "fire",
      "Close-up of SKIVV in shadow looking back over his shoulder, firelight on half his "
      "face, no grin at all",
      "He mouths the words rather than speaking them, then turns back to the light. Slight "
      "push in.",
      "There's forty of them. Forty. And they're all facing the same way, and it isn't at "
      "us.", who="SKIVV",
      sfx="Distant fire, muttering, very quiet movement"),

    s("260_shaft", "gold",
      "An enormous vertical shaft in the rock lit from far below by a sickly green-gold "
      "glow, a spiral stair of dwarven stone running down the wall of it, the bottom not "
      "visible, four small figures at the lip",
      "The green-gold light from below shifts slowly, as if something enormous had moved "
      "in front of it. The figures do not move. Very slow push out over the drop.",
      "And past the warren, past the hall, the floor simply stopped. And something a long "
      "way down was giving off a light.",
      sfx="A vast open echoing space, a deep slow draught rising, distant chain, no music"),

    s("270_descent", "gold",
      "Four figures descending a narrow dwarven spiral stair carved into the wall of a huge "
      "shaft, no rail, the green-gold glow rising from below and lighting them from "
      "beneath, immense drop beside them",
      "They descend steadily, hands on the rock wall. The light from below strengthens on "
      "their faces as they go. Slow push in and downward.",
      "Nine hundred steps. Durgan counted every one of them, out loud, which the others "
      "found either steadying or unbearable depending on the step.",
      sfx="Boots on stone steps, a great echoing shaft, a rising warm draught, a low hum"),

    s("275_durgan_line", "gold",
      "Close-up of DURGAN on a stone stair lit from below by green-gold light, his face "
      "grim, one hand flat against the rock wall, the sun symbol swinging at his chest",
      "He stops on the step. His hand presses flatter against the wall. He looks down. "
      "Slight push in.",
      "Six hundred and forty. Lass, my order does not build stairs down to salt.",
      who="DURGAN",
      sfx="Boots halting on stone, a great echo, a low resonant hum from below"),

    s("280_chains", "gold",
      "Enormous ancient iron chains, each link as tall as a man, running across a vast "
      "stone floor and disappearing into darkness, corroded and slack, lit green-gold from "
      "one side, a tiny figure standing beside one link for scale",
      "The light shifts slowly along the chains. One chain settles with a deep groan. The "
      "small figure steps back. Very slow drift along the chain into the dark.",
      "At the bottom, chains. Slack ones. And a collar the size of a doorway lying open on "
      "the stone.",
      sfx="A colossal iron chain settling, a vast echo, deep low resonance"),

    s("290_eye", "gold",
      "Extreme close-up of an enormous reptilian eye opening in near darkness, the pupil "
      "narrowing, green-gold light reflecting in it, ancient and intelligent and unhurried, "
      "filling the entire frame",
      "The eye opens fully and the pupil contracts. It moves fractionally, tracking "
      "something small. Nothing else moves. Very slow push in.",
      "And then the dark at the far end of the chamber opened one eye, and looked at them, "
      "and did not attack.",
      sfx="A single vast slow breath in the dark, chain shifting, no music"),

    s("300_reveal", "gold",
      "Wide shot of a colossal ancient green dragon lying in a vast underground chamber, "
      "moss-dark scales, one blind milky eye, a broken iron collar around the neck, "
      "tattered wings folded, four tiny figures frozen at the edge of the light",
      "The dragon's head lowers very slightly toward them. Dust falls from the ceiling. The "
      "four figures do not move at all. Slow push in.",
      "Vessarax. Four hundred years old. Chained under a hill by a dwarven order that has "
      "been dust for three centuries, and still, technically, alive.",
      sfx="An enormous slow breath, scales on stone, dust falling, a deep low rumble"),

    s("310_speak", "gold",
      "Medium shot of the vast dragon's head lowered close to the ground, the blind eye "
      "nearest camera, jaws slightly parted, green-gold light from beneath, terrible and "
      "strangely gentle",
      "The great head settles lower onto the stone. The jaws part slightly further. Very "
      "slow push in.",
      "You brought a priest. Oh, that is funny. That is genuinely funny.", who="VESSARAX",
      sfx="A colossal voice resonating in stone, chain shifting, dust falling"),

    s("320_end_table", "table",
      "Overhead view of the candlelit table, four miniatures now standing in a cleared "
      "space on the map, a very large dragon figure set down opposite them, several hands "
      "frozen mid-reach, one chair pushed back",
      "A hand sets the dragon miniature down heavily. Everyone's hands stop moving. The "
      "candle flame jumps. Slow push in on the dragon.",
      "I put the dragon on the table, and nobody reached for a die. Which is exactly what "
      "I wanted, because Vessarax has no intention of fighting anybody.",
      sfx="A heavy miniature set on wood, a chair, sudden quiet, a candle",
      titles=[{"text": "EPISODE THREE - THE BARGAIN", "at": 2.6, "hold": 3.6, "scale": 0.034}]),
]

MUSIC2 = [
    {"at_shot": "200_table", "prefix": "m01_table2", "bpm": 60, "key": "D minor",
     "seconds": 24.0, "level": 0.85,
     "tags": "warm acoustic guitar with a darker turn, low strings entering, a story "
             "resuming, sparse, instrumental, no drums"},
    {"at_shot": "210_entry", "prefix": "m02_dark", "bpm": 48, "key": "C minor",
     "seconds": 44.0, "level": 0.9,
     "tags": "very low drone, distant metallic resonance, claustrophobic, almost no melody, "
             "dark ambient orchestral, instrumental, no drums"},
    {"at_shot": "260_shaft", "prefix": "m03_shaft", "bpm": 56, "key": "G minor",
     "seconds": 46.0, "level": 0.9,
     "tags": "rising choral pad over a deep drone, vast and awed, slow swelling brass, "
             "immense scale, instrumental"},
    {"at_shot": "300_reveal", "prefix": "m04_dragon", "bpm": 50, "key": "E minor",
     "seconds": 40.0, "level": 1.0,
     "tags": "enormous low brass and dark choir, ancient and sad rather than monstrous, "
             "slow, overwhelming, dark orchestral, instrumental"},
]

# ─── EPISODE THREE ──────────────────────────────────────────────────────────────────
EP3 = [
    s("400_table", "table",
      "Overhead view of a candlelit table, a large dragon miniature facing four small ones "
      "across a cleared map, character sheets pushed aside, a die held in a hand above the "
      "table but not yet rolled",
      "The held die turns slowly between two fingers. It is not rolled. The candle burns "
      "down. Slow push in on the hand.",
      "Here is the thing the rules will not tell you. The most dangerous monster in any "
      "dungeon is the one that wants to have a conversation.",
      sfx="Quiet room, a candle, a die turning in fingers, no music",
      titles=[{"text": "EPISODE THREE - THE BARGAIN", "at": 1.4, "hold": 3.8, "scale": 0.034}]),

    s("410_facing", "gold",
      "Wide shot of four small figures standing in a vast dark chamber facing an enormous "
      "green dragon lying among broken chains, green-gold light between them, nobody "
      "holding a weapon",
      "The dragon breathes slowly. One of the small figures lowers a raised sword very "
      "slightly. Dust drifts. Very slow push in.",
      "So they talked. For an hour and a half of real time, they talked.",
      sfx="A vast slow breath, chain settling, a weapon lowered, deep quiet"),

    s("420_dragon_close", "gold",
      "Close on the enormous dragon's head resting sideways on stone, the blind milky eye "
      "toward camera, the good eye beyond it, ancient scarred scales, green-gold light "
      "from below",
      "The good eye blinks slowly. The blind one does not. The great jaw shifts slightly "
      "against the stone. Slow push in.",
      "They did not chain me for what I did. They chained me for what I would not do.",
      who="VESSARAX",
      sfx="A colossal quiet voice, scales shifting on stone, deep resonance"),

    s("430_flashback", "fire",
      "A dwarven hall three hundred years ago lit by torches, dozens of robed dwarven "
      "priests standing in ranks before an enormous chained green dragon, one priest with "
      "an iron pin raised, a painted memory, warmer and more faded than the present",
      "The torchlight wavers across the ranks. The raised pin does not come down. The image "
      "holds unnaturally still, like a memory. Very slow push in.",
      "The order had bound something under this hill. Not the dragon. Something older, in "
      "the deep rock below the deep rock. And they needed a lock with a mind, because the "
      "thing they were locking in could talk its way past anything that had none.",
      sfx="Torches, many robed figures shifting, a low chant, a great chain"),

    s("440_dragon_bargain", "gold",
      "Medium shot of the dragon's head raised slightly off the stone, both eyes visible, "
      "the broken collar hanging loose at the neck, green-gold light strengthening from "
      "below and behind it",
      "The head lifts further. The broken collar swings. The light behind brightens "
      "slightly. Slow push in.",
      "Three hundred years I have been the lock. The collar broke ninety years ago. I "
      "stayed. Ask yourself why the salt, little priest. Ask what a lock eats.",
      who="VESSARAX",
      sfx="A great head lifting, chain swinging, a low rising resonance"),

    s("450_realise", "gold",
      "Close-up of DURGAN standing very still in green-gold light, looking up, his face "
      "changing as he understands something, the tarnished sun symbol held in his fist",
      "His grip tightens on the symbol. His eyes move down and then up again. He has "
      "understood. Slight push in.",
      "Salt. It's not food. You've been salting the seal. Ninety years alone and you kept "
      "doing the work.", who="DURGAN",
      sfx="A slow breath, a chain far off, a vast quiet room"),

    s("460_the_seal", "dark",
      "A deep circular shaft in black rock far below the dragon's chamber, its rim crusted "
      "thick with white salt, faint red light coming up from inside it, ancient dwarven "
      "runes around the edge worn almost smooth",
      "The red light from within the shaft pulses very slowly, once. Salt crystals glitter "
      "on the rim. Very slow push in over the edge.",
      "Below the chamber, below the chains, a shaft in the rock crusted white. Ninety years "
      "of stolen salt, carried down by goblins who had been taught to do it and had long "
      "since forgotten why.",
      sfx="A deep hollow shaft, a very low pulse, salt crystals, distant dripping"),

    s("470_ask", "gold",
      "Medium shot of BRENNA standing alone in front of the enormous dragon's head, small "
      "and unbowed, hands empty at her sides, green-gold light on her armour",
      "She takes one step forward. Her hands stay open and empty. The dragon's head lowers "
      "fractionally to meet her. Slow push in.",
      "So what do you want. Nobody stays ninety years for nothing. What's the price.",
      who="BRENNA",
      sfx="One boot step on stone, a vast breath, deep quiet"),

    s("480_price", "gold",
      "Close on the dragon's good eye filling much of the frame, the pupil wide, the blind "
      "eye a pale blur beyond, green-gold light, an expression that is almost tired relief",
      "The pupil widens slightly. The great eye closes, and opens again slowly. Very slow "
      "push in.",
      "Someone to take the work. That is all. It was never a prison. It was a post. And I "
      "am so very tired of standing it alone.", who="VESSARAX",
      sfx="A colossal slow exhale, scales settling, a low sustained resonance"),

    s("490_choice", "gold",
      "Wide shot of four small figures standing apart from each other in a vast green-gold "
      "chamber, each looking in a different direction, the dragon a dark mass behind them, "
      "the space between them enormous",
      "Nobody moves toward anybody. One figure turns slowly to look at another. Dust drifts "
      "through the light. Slow push out to reveal the scale.",
      "And that is where I stopped talking and let four adults argue with each other for "
      "forty minutes, which is the best thing that can happen in this game.",
      sfx="A vast quiet space, distant dripping, boots shifting, no music"),

    s("500_durgan_stays", "gold",
      "Medium close-up of DURGAN standing alone at the rim of the salt-crusted shaft, his "
      "warhammer laid down on the stone beside him, unbuckling his breastplate, calm",
      "He sets the breastplate down carefully on the stone. He straightens. He does not "
      "look back. Slow push in.",
      "Sixty years he had waited for his order to give him something to do. It turned out "
      "they had left him a job after all. It was just a very long one.",
      sfx="Armour set down on stone, a buckle, a slow breath, a deep hollow shaft"),

    s("510_goodbye", "gold",
      "Two-shot of DURGAN and BRENNA facing each other in green-gold light, her hand gripping "
      "his forearm, both of them entirely still, the vast chamber blurred behind them",
      "Her grip tightens. Neither of them speaks. After a moment she lets go and steps back. "
      "Slow push in.",
      "Go on. You've got a valley up there that still wants its salt. Somebody has to lie to "
      "them about what's down here.", who="DURGAN",
      sfx="Cloth and mail shifting, a long quiet, a distant low pulse"),

    s("520_leaving", "dark",
      "Three small figures climbing an endless dwarven spiral stair in a vast dark shaft, "
      "seen from far above, the green-gold light now far below them and fading, the top not "
      "yet visible",
      "They climb steadily upward. The light below shrinks. None of them looks down. Very "
      "slow push upward ahead of them.",
      "Three of them went back up the nine hundred steps. Nobody counted them out loud.",
      sfx="Boots on stone stairs, a great echoing shaft, a fading low hum"),

    s("530_daylight", "cold",
      "The dwarven door in the hillside from outside, standing open, three figures emerging "
      "into flat grey daylight and thin rain, blinking, the wet green valley spread out "
      "below them",
      "They step out one at a time and stop. Rain falls on their faces. One of them turns to "
      "look back at the dark doorway. Slow push in on the open door.",
      "It was still raining. It had been raining for three days. It had never looked "
      "better.",
      sfx="Rain on hillside, wind, birds, a stone door settling, breathing"),

    s("540_village", "lamp",
      "The village of Marrow Ford at dusk seen from the road, warm light in many windows "
      "now, a salt cart with a fresh team standing at the gate being loaded, wet cobbles, "
      "three small figures walking toward it",
      "The cart is loaded sack by sack. The three figures walk slowly toward the lights. "
      "Smoke rises. Slow push in on the village.",
      "The carts started again eleven days later. The valley never knew why they had "
      "stopped, and nobody in that room ever told them.",
      sfx="A village at evening, cart wheels, voices, sacks handled, rain easing"),

    s("550_shaft_end", "gold",
      "Deep underground, a small robed figure sitting alone on the rim of the salt-crusted "
      "shaft with a lantern beside him, the enormous dark mass of the dragon lying nearby "
      "in the shadow, both of them still",
      "The lantern flame burns steady. The great dark shape breathes, once, slowly. Neither "
      "of them moves otherwise. Very slow push out to show the scale of the chamber.",
      "And a long way down, in the dark, an old man who had stopped expecting an answer sat "
      "down next to something that had been waiting three hundred years for company.",
      sfx="A vast quiet chamber, one lantern, a single enormous slow breath, deep silence"),

    s("560_end_table", "table",
      "Overhead view of the candlelit table at the end of the night, one character sheet "
      "turned face down and pushed to the centre, three others still out, the dice gathered "
      "into a small pile, the candle very low",
      "A hand rests flat on the face-down sheet for a moment, then withdraws. The candle "
      "gutters and steadies. Slow push in on the turned sheet.",
      "Durgan's player turned his sheet face down at the end of the night and said, that "
      "was a good ending, and started rolling a new character. That is the game. You put "
      "somebody down there so the rest of them can walk out.",
      sfx="A paper sheet turned on wood, dice gathered, a chair, a candle, quiet room",
      titles=[{"text": "THE SALT ROAD", "at": 3.0, "hold": 4.0, "scale": 0.075}]),
]

MUSIC3 = [
    {"at_shot": "400_table", "prefix": "m01_table3", "bpm": 58, "key": "D minor",
     "seconds": 24.0, "level": 0.85,
     "tags": "solo acoustic guitar, quiet and reflective, a story reaching its end, warm, "
             "instrumental, no drums"},
    {"at_shot": "420_dragon_close", "prefix": "m02_talk", "bpm": 50, "key": "E minor",
     "seconds": 50.0, "level": 0.85,
     "tags": "sustained low strings under a single distant cello line, sad and ancient, "
             "patient, dark orchestral, instrumental, no drums"},
    {"at_shot": "460_the_seal", "prefix": "m03_seal", "bpm": 46, "key": "F minor",
     "seconds": 38.0, "level": 0.95,
     "tags": "deep pulsing drone and uneasy metallic shimmer, dread, something enormous "
             "sleeping, dark ambient, instrumental"},
    {"at_shot": "500_durgan_stays", "prefix": "m04_stay", "bpm": 54, "key": "C minor",
     "seconds": 52.0, "level": 1.0,
     "tags": "slow swelling strings and a solo horn, noble and grieving, a sacrifice, "
             "restrained orchestral, building then falling away, instrumental"},
    {"at_shot": "540_village", "prefix": "m05_home", "bpm": 66, "key": "Bb major",
     "seconds": 48.0, "level": 0.9,
     "tags": "warm folk strings resolving to major, tired and homecoming, gentle, "
             "hopeful, instrumental, light percussion"},
]


def main():
    for name, sub, shots, music in (
            ("THE SALT ROAD EP2", "episode two - what the dark kept", EP2, MUSIC2),
            ("THE SALT ROAD EP3", "episode three - the bargain", EP3, MUSIC3)):
        n = name[-1]
        out = os.path.join(ROOT, "films", "salt_road_ep0%s.json" % n)
        json.dump(film(name, sub, shots, music), open(out, "w", encoding="utf-8"),
                  indent=1, ensure_ascii=False)
        print("%s  %d shots, %d spoken, %d cues"
              % (out, len(shots), sum(1 for x in shots if x.get("say")), len(music)))


if __name__ == "__main__":
    main()
