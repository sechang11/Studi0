# THE REST OF THE LIBRARY - eleven items, finishing the catalogue at the new quality.
#
# Same shape as the product and hook sets: 12s, one generation, two hard cuts - wide,
# macro, wide. Every rule the night produced is applied up front rather than discovered
# again:
#
#   no human noun anywhere               a named hand grows a whole model who takes the shot
#   the absence restated at EVERY cut    saying it once in the opening is not enough
#   no action that implies an agent      "poured", "cracked", "torn" all summon someone
#   a force with a direction             the difference between a shot and a product photo
#
# Where a beat genuinely needs something done to the subject, it is done by weather,
# gravity or machinery - never by a person.
LOOK = ("shot on 35mm, shallow depth of field, high detail, colour photograph, commercial "
        "product cinematography, no people in frame")
NEG = ("cartoon, childish, ugly, video game, blurry, watermark, text, logo, brand name, "
       "person, model, hands, arms, face, crowd, animal, cat, dog, bird, creature")
E = "the frame completely empty of people and hands"


def spot(sid, seed, keyframe, opening, c1, c2, sound):
    return {"id": sid, "seconds": 12, "megapixels": 1.2, "seed": seed, "neg": NEG,
            "engine": "photo", "note": sid, "keyframe": keyframe + ". " + LOOK,
            "prompt": beats(opening + " " + LOOK, [c1, c2], sound)}


def m(who, what):
    return ("A hard cut transitions to", "a tight macro shot", who, what + ", " + E)


def w(who, what):
    return ("Another hard cut transitions to", "a wide shot", who, what + ", " + E)


FILM = {"assemble": "REST_LTX", "scenes": [

    spot("lib_caffeine", 301,
         "extreme macro straight down into a small white cup of espresso, the crema filling the "
         "whole frame, nothing else in shot",
         "An extreme macro shot looking straight down into a small white cup, the crema filling "
         "the entire frame: a last thread of dark espresso falls in from above and the crema "
         "swirls and closes over itself. Nothing but the cup is in shot - no machine, no "
         "counter, no hands, no arms.",
         m("the surface of the same espresso", "as the crema turns and closes over itself"),
         w("the same cup on the steel counter", "steaming, the machine dark behind it"),
         "an espresso machine hissing under pressure, liquid filling a cup, then the pump "
         "stopping and a quiet cafe"),

    spot("lib_creatine", 302,
         "a steel scoop heaped with fine white powder above a clean steel surface",
         "A close shot with no people in frame: a heaped steel scoop tips over and fine "
         "white powder cascades down onto the steel surface in a soft heap.",
         m("the surface of the same powder heap", "as the last grains slide down its side"),
         w("the same steel surface", "with the heap settled and a fine haze still hanging "
           "over it"),
         "fine dry powder falling on metal, a scoop set down, and a very quiet room"),

    spot("lib_fibre", 303,
         "a dark wholegrain loaf on a scarred wooden board, flour dust, low side light",
         "A close shot with no people in frame: a dark wholegrain loaf splits open along "
         "its crust as it cools and steam escapes from the crack.",
         m("the open crumb of the same loaf", "with steam rising out of the torn structure"),
         w("the same loaf on the wooden board", "cooling, flour dust settling around it"),
         "a crust ticking and splitting as it cools, crumbs falling on wood, a quiet kitchen"),

    spot("lib_magnesium", 304,
         "several small amber glass jars in a row on a pale stone surface, soft light",
         "A slow wide shot with no people in frame: a row of small amber glass jars stands "
         "on pale stone as a shaft of light moves across them and lights each one in turn.",
         m("the shoulder of one of the same jars",
           "where the light refracts through the amber glass"),
         w("the same row of jars", "as the light passes off the end of the row and they go "
           "back to shadow"),
         "a very quiet room, glass ticking faintly as it warms, a distant street"),

    spot("lib_omega3", 305,
         "a fillet of oily fish on crushed ice on a steel counter, cold light",
         "A close shot with no people in frame: crushed ice slides and settles around a "
         "fillet of oily fish and meltwater runs off the edge of the steel counter.",
         m("the surface of the same fillet", "where the light breaks across the wet skin"),
         w("the same fillet on the ice", "as more meltwater runs off the steel and the ice "
           "sinks around it"),
         "ice shifting and cracking, water running on metal, and a cold quiet room"),

    spot("lib_protein", 306,
         "eggs, a raw chicken breast, dried lentils and a bowl of yoghurt arranged on a "
         "scarred wooden board",
         "A slow wide shot with no people in frame: dried lentils pour down onto a wooden "
         "board beside eggs and a bowl of yoghurt, scattering and coming to rest.",
         m("the surface of the same lentils", "as the last of them roll and stop"),
         w("the same board", "with everything settled and a shaft of light across it"),
         "dry lentils falling and scattering on wood, then stillness and a quiet kitchen"),

    spot("lib_sleep", 307,
         "a dark bedroom with a single bedside lamp lit, a made bed, curtains drawn",
         "A slow wide shot of a dark bedroom with no people in frame: the bedside lamp "
         "dims steadily down and the room falls away into darkness around it.",
         m("the filament of the same lamp", "as it cools from orange to nothing"),
         w("the same dark bedroom", "with only the faint edge of the curtains still visible"),
         "a switch turning slowly, a room settling into silence, and faint traffic far away"),

    spot("lib_vitamind", 308,
         "low winter sun through a bare window onto a wooden floor, long shadows, empty room",
         "A slow wide shot of an empty room with no people in frame: a band of low winter "
         "sun moves across the bare floorboards and the window's shadow travels with it.",
         m("the same floorboards", "with dust turning slowly through the shaft of light"),
         w("the same empty room", "as the band of light reaches the far wall and climbs it"),
         "a quiet empty room, floorboards ticking as they warm, and birds outside"),

    spot("lib_morningoat", 309,
         "extreme macro straight down into a white bowl of oats, the oats filling the whole "
         "frame, nothing else in shot",
         "An extreme macro shot looking straight down into a bowl of oats that fills the entire "
         "frame: milk falls in from above and floods between the oats, lifting and turning "
         "them. Nothing but the bowl is in shot - no table, no kitchen, no hands, no arms, "
         "no spoon.",
         m("the surface of the same bowl", "where the milk settles between the oats"),
         w("the same bowl on the counter", "still, in flat morning light"),
         "milk pouring into a bowl, a soft splash, and a quiet bright kitchen"),

    spot("lib_paperlight", 310,
         "a slim pale notebook lying closed on a seamless white surface, soft light",
         "A close shot with no people in frame: a slim pale notebook falls open and its "
         "pages fan across and settle completely flat.",
         m("the edge of the same open pages", "as the last one settles and stops moving"),
         w("the same notebook", "lying open and flat on the seamless white surface"),
         "paper riffling and settling, a soft knock on a hard surface, then silence"),

    spot("lib_trailhead", 311,
         "extreme low macro on the surface of a dry dirt trail, grit and pine needles filling "
         "the whole frame, no path receding into the distance",
         "An extreme low macro shot on the surface of a dry dirt trail, the grit and pine "
         "needles filling the entire frame: dappled sunlight moves slowly across the ground "
         "as the canopy shifts overhead, and loose dust lifts and drifts on the wind. "
         "Nothing walks through, nothing crosses the frame, and no creature, animal, bird, "
         "cat, dog, person, legs or feet appear at any point.",
         m("the same trail surface", "where grit and needles skitter across the packed dirt"),
         w("the same trail", "as the dust clears and the sun comes through the pines onto it"),
         "a gust through pines, grit moving across dry dirt, and open forest ambience"),
]}
