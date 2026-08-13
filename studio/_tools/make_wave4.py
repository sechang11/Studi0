#!/usr/bin/env python3
"""studio/_tools/make_wave4.py - ten new characters and twelve new places, deliberately
spread across eras and media so the library stops looking like one film.

    python3 studio/_tools/make_wave4.py            author the cards
    python3 studio/_tools/make_wave4.py --list     show what it would write

WHY THIS SPREAD. The cast is currently wuxia leads and a handful of anime figures, so every
new frame looks adjacent to the last one. These ten are chosen to sit in different WORLDS -
a 1920s stage, a salvage deck, an ossuary, a bioluminescent cave - which forces different
palettes, different light and different wardrobe rather than the same face in a new room.

WRITTEN FOR THE ENGINE EACH ONE WANTS. The photoreal characters carry PROSE in material,
light, lens and pose vocabulary, because that is what stopped an earlier photoreal attempt
reading as cosplay. The illustrated ones carry danbooru TAGS, because animagine reads tags
and ignores paragraphs. A card that carries the wrong dialect is a card that renders as
someone else.

EVERY WEAR LADDER HAS FIVE RUNGS, clean through to ruined, because that field is a LADDER
and not a costume string - flattening it across nine cards was a real mistake here once.

ALL INVENTED. No real person is named, described or used as a likeness, and nothing is
drawn from an existing franchise.
"""
import argparse, json, os, time

TOOLS = os.path.dirname(os.path.abspath(__file__))
STUDIO = os.path.dirname(TOOLS)

def rungs(base):
    return [base + ", clean and well kept",
            base + ", worn in, dust in the creases",
            base + ", frayed at the cuffs, a repaired seam",
            base + ", torn, stained, a makeshift binding",
            base + ", in ruins, barely holding together"]

CHARS = [
    ("ODALIE", "Odalie Renard", "prose",
     "a woman in her thirties, deep brown skin, close-cropped hair with a marcel wave, "
     "strong brows, a small gap between her front teeth, tired knowing eyes",
     "a bias-cut silver lame gown with a dropped waist, long jet bead ropes, elbow gloves",
     "a jazz singer between sets. Shot on 35mm at f2, hard key from a single stage lamp "
     "raking across one cheek, the rest falling into smoke and darkness, silver lame "
     "catching hard specular highlights"),
    ("THRANE", "Thrane Bokk", "prose",
     "a heavyset man in his fifties, weathered pale skin scoured red at the cheeks, "
     "grey stubble, a flattened nose, one milky eye",
     "a patched canvas dive suit with brass fittings, a rubber collar ring, heavy boots",
     "a salvage diver on a working deck. Overcast north light, wet rubber and oxidised "
     "brass, salt crust on canvas, shot on 50mm at f4, no glamour"),
    ("NEVE", "Neve Ashcombe", "prose",
     "a young woman with pale freckled skin, red hair pinned under a wool cap, "
     "wind-chapped cheeks, a direct unsmiling gaze",
     "a heavy oilskin coat over layered wool, fingerless gloves, a leather satchel",
     "a field naturalist in cold light. Flat arctic daylight, no shadows, breath visible, "
     "shot on 85mm at f2.8, wool and oilskin texture legible"),
    ("KASIMIR", "Kasimir Vole", "prose",
     "an elderly man, gaunt, olive skin, a long grey beard, deep-set dark eyes, "
     "ink-stained fingers",
     "a heavy brocade coat over a plain linen shirt, a stiff collar, a fur-lined mantle",
     "a court astronomer by candlelight. Single warm candle source from below left, deep "
     "chiaroscuro, brocade thread catching the light, painted rather than photographed"),
    ("RUZI", "Ruzi Almas", "prose",
     "a wiry person in their twenties, sun-dark skin, a shaved head under a wrapped cloth, "
     "a scar across the bridge of the nose, pale grey eyes",
     "a layered indigo robe over loose trousers, a wide cloth belt, a face wrap at the neck",
     "a salt-caravan navigator at noon. Brutal overhead sun, hard short shadows, "
     "indigo bleached at the shoulders, heat shimmer behind, shot on 35mm at f8"),
    ("TOLLY", "Tolly Bram", "tags",
     "1boy, solo, male child, child, round face, big eyes, freckles, dark curly hair, "
     "gap teeth, cheerful",
     "knitted jumper, short trousers, scuffed boots, oversized scarf",
     None),
    ("MERIBEL", "Meribel Cruz", "tags",
     "1girl, solo, young woman, short black hair, undercut, sharp eyes, cybernetic ear, "
     "neon reflections on face, determined expression",
     "cropped weatherproof jacket, harness straps, courier bag, fingerless gloves",
     None),
    ("AUGUSTIN", "Augustin Perrey", "tags",
     "1boy, solo, old man, weathered face, deep wrinkles, thin white beard, squinting eyes, "
     "sun-darkened skin",
     "simple work robe, straw rain cape, rope belt, bare feet",
     None),
    ("SABLE", "Sable Okonjo", "prose",
     "a tall woman in her forties, dark skin, tightly braided hair pulled back, "
     "a broad jaw, a burn scar along the left forearm, level unimpressed stare",
     "a patched flight jacket over a mesh underlayer, a tool harness, heavy gloves",
     "a scavenger in a dead industrial yard. Low sun through particulate haze, orange "
     "backlight and cold fill, oil-stained leather, shot on 35mm at f2.8"),
    ("LUMEN", "Lumen Ptak", "prose",
     "a slight person of indeterminate age, very pale skin, white-blonde hair cropped "
     "short, wide light eyes adapted to the dark",
     "a close-fitting caving suit with reflective tape, a helmet with a dead lamp, "
     "a rope coil at the hip",
     "a cave guide lit only by bioluminescence. The sole light is cold blue-green from "
     "below and behind, skin rendered in that colour, deep black elsewhere, shot on 50mm "
     "at f1.4, grain from the low light"),
]

PLACES = [
    ("salt_flat_mirror", "Salt flat mirror",
     "an endless salt flat under a shallow film of water, the ground a perfect mirror of "
     "the sky, a hexagonal crust pattern showing through where the water thins, a distant "
     "mountain ridge doubled at the horizon, no vegetation, no structures",
     "vista", "day"),
    ("paternoster_lift", "Paternoster lift",
     "the shaft of a continuous-loop paternoster lift in an old civic building, open "
     "doorless compartments moving slowly past each floor, brass handrails, terrazzo "
     "landings, a warning sign at each opening, worn parquet visible beyond",
     "interior", "day"),
    ("tidal_organ", "Tidal organ",
     "a concrete sea-wall organ where the tide drives air through rows of steel pipes, "
     "barnacle-crusted mouths at the waterline, a stepped promenade above, grey swell "
     "breaking against it, salt spray in the air",
     "exterior", "overcast"),
    ("bone_library", "Bone library",
     "a vaulted ossuary chapel where the walls are stacked with catalogued bones behind "
     "glass, brass reading lamps on a long oak table, index drawers set into the stonework, "
     "a ladder on a rail, dust motes in a single high window shaft",
     "interior", "day"),
    ("funicular_in_fog", "Funicular in fog",
     "a steep mountain funicular track vanishing upward into thick fog, a single wooden "
     "car half seen on the incline, wet rails, a passing loop, pines as grey silhouettes "
     "on either side, no horizon",
     "exterior", "fog"),
    ("flooded_ballroom", "Flooded ballroom",
     "a grand ballroom standing in knee-deep still water, a chandelier reflected perfectly "
     "in the surface, gilt mirrors clouded with damp, parquet lifting beneath the water, "
     "tall windows with peeling shutters",
     "interior", "day"),
    ("radio_dish", "Radio telescope dish",
     "the underside of an enormous parabolic radio dish on a concrete pivot, a lattice of "
     "white-painted steel ribs converging on the feed horn, service ladders and cable runs, "
     "moorland grass below, a wide pale sky",
     "vista", "day"),
    ("wax_storage", "Wax figure storage",
     "a storage room of unfinished wax figures on rolling racks, heads on shelves in rows, "
     "dust sheets half draped, bare bulbs on a cable, one figure lit and the rest in "
     "shadow, a workbench with tools and pigment",
     "interior", "night"),
    ("glacier_cave", "Glacier ice cave",
     "the inside of a glacier cave, walls of compressed blue ice with trapped air in bands, "
     "meltwater channels cut into the floor, grit and stone frozen into the ceiling, "
     "daylight filtering through metres of ice",
     "interior", "day"),
    ("pigeon_lofts", "Rooftop pigeon lofts",
     "a flat city rooftop crowded with hand-built pigeon lofts of scrap timber and wire, "
     "washing lines strung between them, water tanks, aerials, a low parapet with a view "
     "over tiled roofs, birds circling",
     "exterior", "golden hour"),
    ("water_park", "Abandoned water park",
     "an abandoned water park reclaimed by scrub, faded blue slides cracked and stained "
     "green, an empty wave pool with silt at the bottom, a ticket kiosk with broken glass, "
     "weeds through the paving",
     "exterior", "overcast"),
    ("clock_mechanism", "Clock tower mechanism",
     "the interior mechanism of a tower clock, huge brass gears and a swinging pendulum, "
     "an iron frame bolted to stone, the translucent glass dial lit from outside so the "
     "numerals read backwards, oil cans and rags on a ledge",
     "interior", "day"),
]


def write_char(c):
    cid, name, dialect, who, wear, look = c
    card = {
        "id": cid, "name": name, "status": "ready",
        "desc": who[:150],
        "provenance": "invented",
        "provenance_note": ("Invented for wave 4. No real person is referenced or used as a "
                            "likeness, and this is not a figure from any existing work."),
        "wear_tags": rungs(wear),
        "created": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    if dialect == "prose":
        # Qwen and flux2 read sentences. Material, light, lens and pose - not a list of
        # garments, which is what made an earlier photoreal cast read as costume hire.
        card["prose"] = "%s, wearing %s" % (who, wear)
        card["note"] = look
        card["tags"] = ""
        card["base_tags"] = ""
    else:
        # animagine reads danbooru tags and ignores paragraphs.
        card["tags"] = who
        card["base_tags"] = who.split(",")[0].strip()
        card["prose"] = "%s, wearing %s" % (who, wear)
    return card


def write_place(p):
    pid, name, prose, family, tod = p
    return {
        "id": pid, "name": name, "status": "ready",
        "family": family, "scale": "wide" if family == "vista" else "medium",
        "time_of_day": tod,
        "prose": prose,
        "tags": ", ".join(x.strip() for x in prose.split(",")[:8]),
        "desc": prose[:140],
        "note": "Wave 4. Chosen to be somewhere the library did not already go.",
        "created": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true")
    a = ap.parse_args()
    if a.list:
        print("  characters: %s" % ", ".join(c[0] for c in CHARS))
        print("  places    : %s" % ", ".join(p[0] for p in PLACES))
        return 0
    n = 0
    for c in CHARS:
        p = os.path.join(STUDIO, "characters", c[0] + ".json")
        if os.path.exists(p):
            print("  skip existing character %s" % c[0]); continue
        json.dump(write_char(c), open(p, "w", encoding="utf-8"), indent=1,
                  ensure_ascii=False)
        open(p, "a", encoding="utf-8").write("\n")
        n += 1
    m = 0
    for pl in PLACES:
        p = os.path.join(STUDIO, "places", pl[0] + ".json")
        if os.path.exists(p):
            print("  skip existing place %s" % pl[0]); continue
        json.dump(write_place(pl), open(p, "w", encoding="utf-8"), indent=1,
                  ensure_ascii=False)
        open(p, "a", encoding="utf-8").write("\n")
        m += 1
    print("  wrote %d characters, %d places" % (n, m))
    print("  now: python3 studio/_tools/isolation_run.py --what characters --per 20 --hours 1")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
