#!/usr/bin/env python3
"""Write the studio/cues/ library.

A cue is a named piece of score a SCENE can ask for (`cue: melancholy_piano`).
It carries only the MUSICAL identity - tags, tempo, key, level. Start time and
duration are NOT stored here: compile.py measures the real timeline and fills
them in, because a cue authored as "@120 240s" goes wrong the moment you insert
a scene above it. That was the single most expensive class of edit in the old
hand-written MUSIC blocks.

ACE-Step 1.5 turbo, 20 steps, cfg 1.0. It has no hit-point conditioning, so it
CANNOT spot to picture - compile.py always asks for slightly more than the scene
needs and lets the mix trim in. See craft/SOUND.md.
"""
import json, os

import argparse
argparse.ArgumentParser(description='make cues').parse_args()
# ^ the CLI contract: --help exits HERE, before any work below runs.
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), "cues")

CUES = [
    ("silence", "No score at all. The most under-used cue in the library.",
     "", 0, "", 0.0,
     "Silence immediately before an impact makes the impact twice as loud. "
     "A scene with `silence: true` gets this automatically."),

    ("melancholy_piano", "Defeat, aftermath, an empty room. Sparse and restrained.",
     "sparse melancholy piano, single sustained cello, restrained, instrumental",
     72, "D minor", 0.8,
     "Leave space. If it fills every bar it stops reading as loss and starts reading as a montage."),

    ("tense_strings", "Anticipation. Something is about to be decided.",
     "quiet tense strings, low pulse, anticipation, restrained orchestral, instrumental",
     88, "A minor", 0.7,
     "Sits under dialogue without fighting it - the pulse carries the tension, not the melody."),

    ("desolate", "Loss that has already happened. Very sparse.",
     "desolate solo piano, distant strings, loss, very sparse, instrumental",
     60, "F minor", 0.75,
     "Slower than melancholy_piano and emptier. Use when the character has stopped fighting."),

    ("triumphant_build", "The climax. Everything arrives at once.",
     "soaring orchestral build, taiko drums, brass, choir, triumphant desperate, huge, instrumental",
     140, "D minor", 1.0,
     "One per film. A second one makes the first mean nothing - same discipline as sakuga."),

    ("driving_pulse", "Momentum. A sequence that is going somewhere.",
     "driving percussion, ostinato strings, insistent low brass, forward motion, instrumental",
     128, "E minor", 0.85,
     "Good under fast pacing. Its regularity is what makes a cut ON the beat feel deliberate."),

    ("warm_memory", "Flashback, a better time, an unreliable one.",
     "warm nostalgic strings, soft piano, gentle, hazy, wistful, instrumental",
     76, "C major", 0.7,
     "Pair with look:memory or look:golden. Major key against a minor-key film reads as 'then', not 'now'."),

    ("unease", "Something is wrong and nobody has said so yet.",
     "low drone, dissonant sustained strings, sparse metallic hits, unsettling, instrumental",
     0, "C minor", 0.65,
     "bpm 0 means unmetered - do not try to cut to this one."),
]

os.makedirs(OUT, exist_ok=True)
for cid, desc, tags, bpm, key, level, note in CUES:
    doc = {
        "id": cid,
        "desc": desc,
        "status": "ready",
        "tags": tags,
        "bpm": bpm,
        "key": key,
        "level": level,
        "note": note,
    }
    if cid == "silence":
        doc["status"] = "ready"
        doc["silent"] = True
    with open(os.path.join(OUT, cid + ".json"), "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=2, ensure_ascii=False)
        f.write("\n")

print("wrote %d cues to %s" % (len(CUES), OUT))
