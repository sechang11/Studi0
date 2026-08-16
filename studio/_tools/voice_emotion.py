#!/usr/bin/env python3
"""studio/_tools/voice_emotion.py - an emotion card, as something IndexTTS-2 can act.

    python3 studio/_tools/voice_emotion.py            # print the table
    python3 studio/_tools/voice_emotion.py rage       # one row

THE GAP THIS CLOSES. 27 emotion cards each carry a `voice_style` word (roaring, hushed,
breathless...) and a `voice_rate`. The face tags render; the voice never changed. The
healthcheck said so 68 times, and the cards say it themselves: "voice_style applies only
on TTS engines that accept an emotion vector."

We HAVE such an engine. workflows/16_indextts2_voice.json already contains an
IndexTTSEmotionOptionsNode wired into the engine's emotion_control, and it has been
sitting at all-zeros since it was built. What was missing was never the node - it was a
translation from a word a director writes to the eight numbers the model takes.

THE EIGHT ARE FIXED BY THE MODEL: Happy Angry Sad Surprised Afraid Disgusted Calm
Melancholic. So this is a mapping, and it is written out per emotion rather than derived
from the style word, because "hollow", "hard" and "flat" are not adjectives any formula
can turn into a vector - they are judgements about how a person sounds, and the honest
form for that is a table someone can argue with.

BLENDS, NOT ONE-HOT. A single dimension at 1.0 is a caricature. Contempt is disgust with
a little anger under it; defiance is anger with a grin in it; resignation is melancholy
that has stopped fighting. The pairs are the point - they are what stops every angry line
sounding like the same shout.

voice_rate is applied AFTER generation with atempo, which changes duration without moving
pitch. IndexTTS's node exposes no speed input, so the alternative was to ignore a field
the cards have carried all along.
"""
import json
import os
import sys

DIMS = ("Happy", "Angry", "Sad", "Surprised", "Afraid", "Disgusted", "Calm",
        "Melancholic")

# emotion card id -> the blend. Values are deliberately under 1.0 except where the
# emotion IS the extreme (rage): headroom is what keeps a read from clipping into parody.
TABLE = {
    "angry":       {"Angry": 0.85},
    "awe":         {"Surprised": 0.35, "Calm": 0.45},
    "cold":        {"Calm": 0.60, "Disgusted": 0.15},
    "contempt":    {"Disgusted": 0.70, "Angry": 0.20},
    "defiance":    {"Angry": 0.55, "Happy": 0.15},
    "despair":     {"Sad": 0.80, "Melancholic": 0.60},
    "determined":  {"Calm": 0.50, "Angry": 0.20},
    "doubt":       {"Afraid": 0.30, "Calm": 0.30},
    "embarrassed": {"Surprised": 0.40, "Afraid": 0.25, "Happy": 0.15},
    "exhausted":   {"Melancholic": 0.45, "Sad": 0.35, "Calm": 0.30},
    "fear":        {"Afraid": 0.85},
    "focus":       {"Calm": 0.55, "Angry": 0.10},
    "grief":       {"Sad": 0.90, "Melancholic": 0.70},
    "joy":         {"Happy": 0.85},
    "longing":     {"Melancholic": 0.65, "Sad": 0.25, "Calm": 0.20},
    "neutral":     {"Calm": 0.60},
    "panic":       {"Afraid": 0.80, "Surprised": 0.50},
    "pride":       {"Happy": 0.55, "Calm": 0.35},
    "rage":        {"Angry": 1.00},
    "relief":      {"Calm": 0.60, "Happy": 0.30},
    "resignation": {"Melancholic": 0.50, "Calm": 0.40, "Sad": 0.20},
    "resolve":     {"Calm": 0.60, "Angry": 0.15},
    "shame":       {"Sad": 0.50, "Melancholic": 0.40, "Afraid": 0.15},
    "shock":       {"Surprised": 0.85, "Afraid": 0.30},
    "smug":        {"Happy": 0.40, "Calm": 0.30, "Disgusted": 0.20},
    "suspicion":   {"Calm": 0.35, "Disgusted": 0.25, "Afraid": 0.20},
    "tender":      {"Calm": 0.50, "Happy": 0.40},
}

HERE = os.path.dirname(os.path.abspath(__file__))
STUDIO = os.path.dirname(HERE)


def card(emo):
    p = os.path.join(STUDIO, "emotions", str(emo) + ".json")
    try:
        return json.load(open(p, encoding="utf-8"))
    except OSError:
        return {}


def vector(emo, fallback=None):
    """The eight floats for an emotion id.

    Returns None when the emotion is unknown, so the caller can fall back to whatever
    the character was already configured with rather than silently flattening the read
    to neutral - an unrecognised emotion is an authoring typo, not a request for calm.
    """
    if not emo:
        return None
    blend = TABLE.get(str(emo).strip().lower())
    if blend is None:
        return None
    v = {d: 0.0 for d in DIMS}
    v.update({k: float(x) for k, x in blend.items()})
    return v


def rate(emo, default=1.0):
    """The card's own voice_rate. Clamped: atempo below 0.5 or above 2.0 is a chipmunk."""
    r = card(emo).get("voice_rate")
    try:
        r = float(r)
    except (TypeError, ValueError):
        return default
    return max(0.5, min(2.0, r))


def main():
    want = sys.argv[1] if len(sys.argv) > 1 else None
    ids = [want] if want else sorted(TABLE)
    print("%-13s %-11s %5s   %s" % ("emotion", "style", "rate", "blend"))
    print("-" * 78)
    missing = []
    for e in ids:
        v = vector(e)
        if v is None:
            print("%-13s unknown" % e)
            continue
        c = card(e)
        if not c:
            missing.append(e)
        parts = ", ".join("%s %.2f" % (k, x) for k, x in v.items() if x)
        print("%-13s %-11s %5s   %s"
              % (e, c.get("voice_style") or "-", rate(e), parts))
    # a table entry with no card is a typo waiting to be silent; say so
    cards = {os.path.splitext(f)[0] for f in os.listdir(os.path.join(STUDIO, "emotions"))
             if f.endswith(".json")}
    extra = sorted(set(TABLE) - cards)
    absent = sorted(cards - set(TABLE))
    if extra:
        print("\n! in the table but no emotion card: %s" % ", ".join(extra))
    if absent:
        print("\n! emotion cards with no entry (they will fall back): %s" % ", ".join(absent))
    if not extra and not absent:
        print("\nevery emotion card has a blend, and every blend has a card")
    return 0


if __name__ == "__main__":
    sys.exit(main())
