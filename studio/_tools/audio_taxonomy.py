#!/usr/bin/env python3
"""Give the audio libraries a taxonomy: what KIND of sfx, what KIND of music, and tags.

Every category below is derived from the cards that exist, not invented ahead of them -
20 sfx, 22 cues, 8 soundscapes, 25 voices were read and grouped by what they actually
are. If a category has one member that is honest, not a gap to pad.

FIELD NAMING, and there is a trap. On a CUE card `tags` is ALREADY TAKEN: it holds the
ACE-Step prompt ("festive celebration orchestra, bright brass, tambourine and snare").
Overloading it would silently corrupt music generation. So the taxonomy fields are
`category` and `keywords` everywhere, on every audio kind, and `tags` keeps meaning
"the generation prompt" on the cards that had it.

`tempo` on cues is DERIVED from the bpm already on the card rather than authored, so it
cannot drift away from the number it describes.
"""
import json
import os
import sys

# ---- SFX: grouped by what makes the sound -----------------------------------------
SFX = {
    "breath":             ("body", "human close tension subjective"),
    "heartbeat":          ("body", "human tension subjective loopable"),
    "cloth_movement":     ("body", "human close texture"),
    "footsteps_concrete": ("body", "human interior hard-floor loopable"),
    "footsteps_grass":    ("body", "human exterior soft-ground loopable"),
    "crowd_murmur":       ("crowd", "human interior loopable background"),
    "crowd_roar":         ("crowd", "human exterior loud release"),
    "impact_hit":         ("impact", "percussive editorial punctuation"),
    "glass_break":        ("impact", "percussive violence brittle"),
    "metal_clang":        ("impact", "percussive metal industrial"),
    "rain_on_roof":       ("weather", "exterior interior-heard loopable wet"),
    "thunder_distant":    ("weather", "exterior dread off-screen"),
    "wind_open":          ("weather", "exterior exposed loopable"),
    "fire_crackle":       ("element", "warmth threat loopable interior"),
    "water_splash":       ("element", "wet impact exterior"),
    "door_wood":          ("object", "interior entrance reveal"),
    "paper":              ("object", "interior close intimate"),
    "keyboard":           ("object", "interior work loopable occupied"),
    "electrical_hum":     ("room_tone", "interior loopable bed powered"),
    "whoosh":             ("editorial", "transition pan non-diegetic"),
}

# ---- CUES: grouped by dramatic function --------------------------------------------
CUES = {
    "menace":            ("tension", "antagonist low dread"),
    "tense_strings":     ("tension", "anticipation strings suspense"),
    "unease":            ("tension", "wrong unresolved ambient"),
    "chase":             ("action", "pursuit fast percussion"),
    "epic_battle":       ("action", "armies sustained orchestral"),
    "driving_pulse":     ("action", "momentum electronic sequence"),
    "triumphant_build":  ("action", "climax arrival orchestral"),
    "training_montage":  ("action", "montage effort progress"),
    "desolate":          ("grief", "loss sparse aftermath"),
    "melancholy_piano":  ("grief", "piano sparse defeat"),
    "sombre_funeral":    ("grief", "formal public slow"),
    "romantic":          ("warmth", "intimate two-hander unhurried"),
    "warm_memory":       ("warmth", "flashback nostalgic unreliable"),
    "hopeful_rising":    ("warmth", "turn optimism build"),
    "quiet_dawn":        ("warmth", "morning calm reset"),
    "celebration":       ("triumph", "public joy festive brass"),
    "heroic_fanfare":    ("triumph", "arrival brass announcement"),
    "comedic_light":     ("levity", "no-stakes light playful"),
    "playful_mischief":  ("levity", "sneaky comic pizzicato"),
    "industrial_cold":   ("atmosphere", "machine indifferent texture"),
    "lonely_night_city": ("atmosphere", "neon nocturne urban"),
    "silence":           ("atmosphere", "absence negative-space"),
}

# ---- SOUNDSCAPES: the bed under a scene, grouped by where you are -------------------
SCAPES = {
    "room":       ("interior", "neutral bed dialogue"),
    "night_room": ("interior", "night quiet bed"),
    "tunnel":     ("interior", "concrete reverberant"),
    "street":     ("exterior", "urban bed traffic"),
    "rain_out":   ("exterior", "wet weather bed"),
    "stadium":    ("crowd", "packed loud exterior"),
    "subjective": ("subjective", "interiority breath dropout"),
    "silence":    ("subjective", "absence pre-impact"),
}

# ---- VOICES: grouped by what you would cast them for --------------------------------
# `category` is the casting role. Language and register go in keywords, because a
# Mandarin narrator is still a narrator and should sort with them.
VOICES = {
    "female_01":       ("narration", "english female level neutral"),
    "female_04_maya":  ("narration", "english female technical measured"),
    "male_04_frank":   ("narration", "english male level analyst"),
    "male_02":         ("narration", "english male deep calm authority"),
    "en_woman":        ("narration", "english female instructional"),
    "zh_bowen_man":    ("narration", "mandarin male clean"),
    "zh_xinran_woman": ("narration", "mandarin female clean"),
    "male_03_carter":  ("host", "english male warm american presenter"),
    "female_03_alice": ("host", "english female young conversational"),
    "en_man":          ("host", "english male brisk corporate"),
    "female_02":       ("host", "english female brisk formal"),
    "belinda":         ("character", "english child excited"),
    "broom_salesman":  ("character", "english male eccentric trader"),
    "chadwick":        ("character", "english male arch comic"),
    "mabel":           ("character", "english female bright teasing"),
    "vex":             ("character", "english bored drawl deadpan"),
    "male_01":         ("character", "english male radio wry"),
    "male_05_samuel":  ("character", "indian-english male"),
    "zh_man_sichuan":  ("character", "mandarin male sichuan comic"),
    # measured as unusable; kept visible so the gap is legible rather than mysterious
    "anchen_man_bgm":  ("unusable", "mandarin male music-bed rejected-by-node"),
    "mary_woman_bgm":  ("unusable", "english female music-bed rejected-by-node"),
    # The four likeness clones of real people. They stay category `blocked`, they are not
    # castable, and nothing here un-blocks them or serves their reference audio.
    "clint_eastwood_cc3":     ("blocked", "real-person-likeness do-not-cast"),
    "david_attenborough_cc3": ("blocked", "real-person-likeness do-not-cast"),
    "morgan_freeman_cc3":     ("blocked", "real-person-likeness do-not-cast"),
    "sophie_anderson_cc3":    ("blocked", "real-person-likeness do-not-cast"),
}

TABLE = {"sfx": SFX, "cues": CUES, "soundscapes": SCAPES, "voices": VOICES}


def tempo_of(bpm):
    """Derived from the card's own bpm so the word and the number cannot disagree."""
    try:
        b = float(bpm)
    except (TypeError, ValueError):
        return None
    if b <= 0:
        return "still"
    if b < 70:
        return "slow"
    if b < 100:
        return "walking"
    if b < 140:
        return "driving"
    return "fast"


def main():
    root = "studio"
    total = missing = extra = 0
    for folder, table in TABLE.items():
        d = os.path.join(root, folder)
        on_disk = {os.path.splitext(f)[0] for f in os.listdir(d) if f.endswith(".json")}
        named = set(table)
        for cid in sorted(named - on_disk):
            print("  ! %s/%s is in the taxonomy but not on disk" % (folder, cid))
            extra += 1
        for cid in sorted(on_disk - named):
            print("  ! %s/%s has no taxonomy entry" % (folder, cid))
            missing += 1
        n = 0
        for cid in sorted(on_disk & named):
            p = os.path.join(d, cid + ".json")
            card = json.load(open(p, encoding="utf-8"))
            cat, kw = table[cid]
            card["category"] = cat
            card["keywords"] = kw
            if folder == "cues":
                t = tempo_of(card.get("bpm"))
                if t:
                    card["tempo"] = t
            json.dump(card, open(p, "w", encoding="utf-8"), indent=2)
            n += 1
        cats = {}
        for cid in sorted(on_disk & named):
            cats.setdefault(table[cid][0], []).append(cid)
        print("%-12s %2d cards, %d categories" % (folder, n, len(cats)))
        for c in sorted(cats):
            print("     %-12s %d  %s" % (c, len(cats[c]), " ".join(sorted(cats[c]))[:70]))
        total += n
    print("\n%d cards categorised; %d on disk with no entry, %d entries with no card"
          % (total, missing, extra))
    return 1 if (missing or extra) else 0


if __name__ == "__main__":
    sys.exit(main())
