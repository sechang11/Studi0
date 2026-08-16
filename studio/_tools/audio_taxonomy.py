#!/usr/bin/env python3
"""studio/_tools/audio_taxonomy.py - the sound library, filed the way sound libraries are.

    python3 studio/_tools/audio_taxonomy.py           # assign, file, report
    python3 studio/_tools/audio_taxonomy.py --dry     # report only, move nothing

WHAT CHANGED FROM THE FIRST VERSION. That one gave every card a single `category` string
derived from what the cards happened to be. Useful, but not how anyone actually shops for
music: stock libraries let you come at a track from either side - the MOOD you need
(uplifting, epic, tense) or the GENRE you want it played in (orchestral, lo-fi, chiptune)
- and they file the audio itself under one of them so a folder is browsable on disk.

So:

  MOOD is the filing axis for music. It is the folder, because a director picks music by
  what the scene must feel like, not by instrumentation. Eleven moods, named in the
  vocabulary these libraries use, including the negative half that most collections are
  short of: uplifting happy epic driving emotional sad dark tense calm quirky silence.

  GENRE, ENERGY and USE are tags, because a track has one mood and several of each. A
  cue can be orchestral AND hybrid_trailer, and be right for a trailer AND a montage.

  CATEGORY is the filing axis for sfx, with a SUBCATEGORY under it, which is exactly how
  a foley library is laid out - foley/footsteps, impacts/glass, weather/thunder.

FILES MOVE. studio/samples/cues/chase.mp3 becomes samples/cues/driving/chase.mp3, and its
render record moves with it, because a sidecar that loses its audio is how provenance
gets orphaned. Nothing is deleted and nothing is renamed - only filed.

THE EMPTY SLOTS ARE THE POINT. Declaring `weapons`, `vehicles`, `animals`, `ui` and
`magic_scifi` with nothing in them is not padding: it is the generation worklist, printed
by this tool, and it is the honest shape of a 20-effect library that wants to be a real
one. A taxonomy that only describes what you already own cannot tell you what is missing.
"""
import argparse
import glob
import json
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
STUDIO = os.path.dirname(HERE)
SAMPLES = os.path.join(STUDIO, "samples")

# --------------------------------------------------------------------- MUSIC
# mood -> the folder. The negative half is deliberately as wide as the positive half.
MUSIC_MOODS = ["uplifting", "happy", "epic", "driving", "emotional",
               "sad", "dark", "tense", "calm", "quirky", "silence"]

# id: (mood, genre tags, energy, use tags)
CUES = {
    "celebration":       ("uplifting", "orchestral brass festive", "high",   "titles montage trailer"),
    "hopeful_rising":    ("uplifting", "orchestral strings hybrid_trailer", "medium", "montage corporate documentary"),
    "heroic_fanfare":    ("epic",      "orchestral brass fanfare", "high",   "titles trailer gaming"),
    "epic_battle":       ("epic",      "orchestral percussion hybrid_trailer", "high", "trailer gaming action"),
    "triumphant_build":  ("epic",      "orchestral hybrid_trailer", "high",  "trailer titles montage"),
    "chase":             ("driving",   "orchestral strings percussion", "high", "action trailer gaming"),
    "driving_pulse":     ("driving",   "electronic synth percussion", "high", "montage corporate vlog"),
    "training_montage":  ("driving",   "rock electronic percussion", "high", "montage vlog gaming"),
    "comedic_light":     ("quirky",    "acoustic pizzicato folk", "medium",  "vlog podcast documentary"),
    "playful_mischief":  ("quirky",    "pizzicato acoustic woodwind", "medium", "vlog gaming podcast"),
    "romantic":          ("emotional", "piano strings acoustic", "low",      "underscore documentary"),
    "warm_memory":       ("emotional", "piano strings ambient", "low",       "underscore documentary vlog"),
    "lonely_night_city": ("emotional", "lofi jazz electronic nocturne", "low", "underscore vlog podcast"),
    "melancholy_piano":  ("sad",       "piano solo sparse", "low",           "underscore documentary"),
    "desolate":          ("sad",       "ambient strings sparse", "low",      "underscore documentary"),
    "sombre_funeral":    ("sad",       "orchestral strings choir", "low",    "underscore titles"),
    "menace":            ("dark",      "orchestral low_brass drone", "medium", "trailer gaming underscore"),
    "industrial_cold":   ("dark",      "electronic industrial drone", "medium", "underscore gaming documentary"),
    "tense_strings":     ("tense",     "orchestral strings ostinato", "medium", "trailer underscore gaming"),
    "unease":            ("tense",     "ambient drone electronic", "low",    "underscore documentary"),
    "quiet_dawn":        ("calm",      "ambient piano strings", "low",       "underscore vlog documentary"),
    "silence":           ("silence",   "none", "still",                      "underscore"),
}

# Moods with nothing in them yet are still declared: they are the worklist.
MUSIC_WANTED = {
    "happy": "feel-good, bright, major-key - the single most requested mood in any "
             "library and this one has none of it",
    "uplifting": "more inspirational/motivational corporate beds; two is thin",
    "calm": "lo-fi chill, ambient study beds, sleep - a whole genre this box can render",
    "quirky": "more comedy variety; two cues cannot carry a comedic edit",
}

# --------------------------------------------------------------------- SFX
# category -> subcategories. Categories with no cards yet are the generation worklist.
SFX_TREE = {
    "foley":       ["footsteps", "cloth", "handling"],
    "human":       ["breath", "body", "voice_nonverbal"],
    "impacts":     ["hit", "break", "metal"],
    "weather":     ["rain", "wind", "thunder"],
    "elements":    ["fire", "water", "earth"],
    "objects":     ["door", "paper", "keyboard", "tool"],
    "ambience":    ["room_tone", "interior", "exterior"],
    "crowd":       ["murmur", "roar", "applause"],
    "transitions": ["whoosh", "riser", "stinger"],
    "ui":          ["click", "notification", "error"],
    "weapons":     ["blade", "firearm", "bow"],
    "vehicles":    ["car", "engine", "aircraft"],
    "animals":     ["dog", "bird", "horse"],
    "magic_scifi": ["spell", "energy", "machine"],
}

# id: (category, subcategory, keywords)
SFX = {
    "footsteps_concrete": ("foley", "footsteps", "human interior hard_floor loopable"),
    "footsteps_grass":    ("foley", "footsteps", "human exterior soft_ground loopable"),
    "cloth_movement":     ("foley", "cloth", "human close texture"),
    "breath":             ("human", "breath", "close tension subjective"),
    "heartbeat":          ("human", "body", "tension subjective loopable"),
    "impact_hit":         ("impacts", "hit", "percussive editorial punctuation"),
    "glass_break":        ("impacts", "break", "percussive violence brittle"),
    "metal_clang":        ("impacts", "metal", "percussive industrial"),
    "rain_on_roof":       ("weather", "rain", "exterior interior_heard loopable wet"),
    "wind_open":          ("weather", "wind", "exterior exposed loopable"),
    "thunder_distant":    ("weather", "thunder", "exterior dread off_screen"),
    "fire_crackle":       ("elements", "fire", "warmth threat loopable interior"),
    "water_splash":       ("elements", "water", "wet impact exterior"),
    "door_wood":          ("objects", "door", "interior entrance reveal"),
    "paper":              ("objects", "paper", "interior close intimate"),
    "keyboard":           ("objects", "keyboard", "interior work loopable occupied"),
    "electrical_hum":     ("ambience", "room_tone", "interior loopable bed powered"),
    "crowd_murmur":       ("crowd", "murmur", "interior loopable background"),
    "crowd_roar":         ("crowd", "roar", "exterior loud release"),
    "whoosh":             ("transitions", "whoosh", "pan non_diegetic editorial"),
}


def tempo_of(bpm):
    try:
        b = float(bpm)
    except (TypeError, ValueError):
        return None
    if b <= 0:
        return "still"
    return "slow" if b < 70 else "walking" if b < 100 else "driving" if b < 140 else "fast"


def file_into(folder, cid, sub, dry):
    """Move <samples>/<folder>/<cid>.mp3 and its render record into <folder>/<sub>/.

    Returns what happened. The sidecar travels with the audio: a render record that has
    lost the file it describes is how provenance quietly rots.
    """
    moved = []
    for ext in (".mp3", ".json", ".wav", ".flac"):
        src = os.path.join(SAMPLES, folder, cid + ext)
        if not os.path.exists(src):
            continue
        dst_dir = os.path.join(SAMPLES, folder, sub)
        dst = os.path.join(dst_dir, cid + ext)
        if os.path.abspath(src) == os.path.abspath(dst):
            continue
        if not dry:
            os.makedirs(dst_dir, exist_ok=True)
            shutil.move(src, dst)
        moved.append(ext)
    return moved


def main():
    ap = argparse.ArgumentParser(description="File the sound library by mood and category.")
    ap.add_argument("--dry", action="store_true", help="report only, move nothing")
    a = ap.parse_args()

    moved_n = 0

    # ---- music
    print("MUSIC - filed by mood")
    by_mood = {}
    on_disk = sorted(os.path.splitext(os.path.basename(x))[0]
                     for x in glob.glob(os.path.join(STUDIO, "cues", "*.json")))
    for cid in sorted(set(CUES) | set(on_disk)):
        p = os.path.join(STUDIO, "cues", cid + ".json")
        if not os.path.exists(p):
            print("  ! in the table but no card on disk: %s" % cid)
            continue
        card = json.load(open(p, encoding="utf-8"))
        if cid in CUES:
            mood, genre, energy, use = CUES[cid]
        else:
            # authored after this table was written - it files itself
            mood = card.get("mood") or card.get("category")
            genre = card.get("genre") or ""
            energy = card.get("energy") or ""
            use = card.get("use") or ""
            if not mood:
                print("  ! %s has no mood and no table entry - not filed" % cid)
                continue
        card["category"] = mood          # the folder, and the primary browse axis
        card["mood"] = mood
        card["genre"] = genre
        card["energy"] = energy
        card["use"] = use
        card["keywords"] = " ".join(sorted(set((genre + " " + use).split())))
        t = tempo_of(card.get("bpm"))
        if t:
            card["tempo"] = t
        if not a.dry:
            json.dump(card, open(p, "w", encoding="utf-8"), indent=2)
        if file_into("cues", cid, mood, a.dry):
            moved_n += 1
        by_mood.setdefault(mood, []).append(cid)
    for m in MUSIC_MOODS:
        ids = by_mood.get(m, [])
        note = "" if ids else "   <-- EMPTY"
        print("  %-11s %2d  %s%s" % (m, len(ids), " ".join(sorted(ids))[:58], note))

    # ---- sfx
    print("\nSFX - filed by category/subcategory")
    by_cat = {}
    sfx_disk = sorted(os.path.splitext(os.path.basename(x))[0]
                      for x in glob.glob(os.path.join(STUDIO, "sfx", "*.json")))
    for cid in sorted(set(SFX) | set(sfx_disk)):
        p = os.path.join(STUDIO, "sfx", cid + ".json")
        if not os.path.exists(p):
            print("  ! in the table but no card on disk: %s" % cid)
            continue
        card = json.load(open(p, encoding="utf-8"))
        if cid in SFX:
            cat, sub, kw = SFX[cid]
        else:
            cat = card.get("category")
            sub = card.get("subcategory") or (cat or "")
            kw = card.get("keywords") or ""
            if not cat:
                print("  ! %s has no category and no table entry - not filed" % cid)
                continue
        card["category"] = cat
        card["subcategory"] = sub
        card["keywords"] = kw
        if not a.dry:
            json.dump(card, open(p, "w", encoding="utf-8"), indent=2)
        if file_into("sfx", cid, cat, a.dry):
            moved_n += 1
        by_cat.setdefault(cat, []).append((sub, cid))
    for cat, subs in SFX_TREE.items():
        got = by_cat.get(cat, [])
        note = "   <-- EMPTY" if not got else ""
        print("  %-12s %2d  %s%s"
              % (cat, len(got),
                 " ".join("%s/%s" % (s, i) for s, i in sorted(got))[:58], note))

    # ---- what to render next
    print("\nWORKLIST - declared and empty, which is the point of declaring them")
    empty_moods = [m for m in MUSIC_MOODS if not by_mood.get(m)]
    thin = [m for m in MUSIC_WANTED if len(by_mood.get(m, [])) < 3]
    empty_cats = [c for c in SFX_TREE if not by_cat.get(c)]
    if empty_moods:
        print("  music moods with nothing in them: %s" % ", ".join(empty_moods))
    for m in thin:
        print("  music %-10s thin (%d) - %s" % (m, len(by_mood.get(m, [])), MUSIC_WANTED[m]))
    if empty_cats:
        print("  sfx categories with nothing in them: %s" % ", ".join(empty_cats))
        for c in empty_cats:
            print("      %-12s wants %s" % (c, ", ".join(SFX_TREE[c])))

    print("\n%d cards had audio filed%s" % (moved_n, " (dry run)" if a.dry else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
