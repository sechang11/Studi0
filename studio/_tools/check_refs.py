#!/usr/bin/env python3
"""Check that every card's cross-references point at a card that exists.

    python3 studio/_tools/check_refs.py          # report
    python3 studio/_tools/check_refs.py --strict # exit 1 if anything dangles

WHY THIS EXISTS. 19 style cards shipped listing a look called 'warm'. There is no such
look - the 25 ids include golden, firelight and sunset, but not warm. It was invented
during authoring and nothing caught it, because nothing reads suits_looks at render time
yet. A reference that is never resolved is a reference that is never checked, so it sits
there until the day something starts reading it and then fails quietly.

The pattern generalises: this project authors cards in bulk, often by agents working from a
brief, and a plausible-but-nonexistent id is exactly the kind of mistake that survives
review. Cheap to check, so check it every time.
"""
import json, glob, os, sys, collections

HERE = os.path.dirname(os.path.abspath(__file__))
STUDIO = os.path.dirname(HERE)

# (group holding the reference, field on the card, group the id must exist in)
# A field may hold a bare id or a list of ids; both are handled.
#
# NOTE `movies.style` is deliberately absent. It is DUAL-PURPOSE and both meanings are
# valid: if the value resolves to a card in styles/ the compiler uses that card (and takes
# the engine from it); if it does not, the value is legacy free-text house-style tags and
# is appended to the prompt on the anime path. derby-ep1 relies on the second meaning and
# renders correctly. A checker that demanded an id here would flag working films.
REFS = [
    ("styles",     "suits_looks",   "looks"),
    ("templates",  "look",          "looks"),
    ("templates",  "style",         "styles"),
    ("characters", "default_wear",  "wear"),
    ("places",     "suits_looks",   "looks"),
    # A style card may now recommend a style LoRA by card id. Three cards do
    # (stop_motion_felt, pointillism, comic_halftone), and nothing cross-checked
    # the id until this rule existed - the exact shape of mistake this file was
    # written to catch.
    ("styles",     "lora",          "loras"),
    # A template sets the whole layer stack, so every layer it names is a reference.
    ("templates",  "cue",           "cues"),
    ("templates",  "emotion",       "emotions"),
    ("templates",  "camera",        "cameras"),
    ("templates",  "transition",    "transitions"),
    ("templates",  "lighting",      "lighting"),
    ("templates",  "weather",       "weather"),
    ("templates",  "style_lora",    "loras"),
    ("templates",  "character",     "characters"),
]

# Templates are the one group whose references do NOT live at the card root. The wizard
# reads them out of a `sets` object and the per-shot ids out of `shots[]`, but this file
# read d.get(field) at the root - so the two template rules above it declared matched
# nothing and every template reference was invisible.
#
# This was not theoretical. 62 template cards carrying 1077 checkable ids were authored in
# one pass and the count printed at the bottom of this report did not move off 636. A
# checker that silently validates zero of the group it claims to cover is worse than no
# checker, because the green line is read as proof.
NESTED = {"templates": "sets"}

# (group, list field, id field on each item, group the id must exist in)
# A template beat names a shot template and may name its own camera.
ITEM_REFS = [
    ("templates", "shots", "template", "shots"),
    ("templates", "shots", "camera",   "cameras"),
]

# An id has no spaces or commas. Used to tell a mistyped id apart from free text in the
# dual-purpose fields, so those can be reported as a hint rather than as an error.
def looks_like_id(s):
    return " " not in s and "," not in s


def ids(group):
    d = os.path.join(STUDIO, group)
    if not os.path.isdir(d):
        return None
    return {os.path.basename(p)[:-5] for p in glob.glob(os.path.join(d, "*.json"))}


def main():
    strict = "--strict" in sys.argv
    dangling = collections.defaultdict(list)
    checked = skipped = 0

    for group, field, target in REFS:
        src = os.path.join(STUDIO, group)
        have = ids(target)
        if not os.path.isdir(src) or have is None:
            skipped += 1
            continue
        for p in sorted(glob.glob(os.path.join(src, "*.json"))):
            try:
                d = json.load(open(p, encoding="utf-8"))
            except Exception as e:
                dangling["%s (unparseable)" % group].append("%s: %s" % (os.path.basename(p), e))
                continue
            box = d.get(NESTED[group]) if group in NESTED else None
            v = (box if isinstance(box, dict) else d).get(field)
            if not v:
                continue
            for one in (v if isinstance(v, list) else [v]):
                if not isinstance(one, str) or not one.strip():
                    continue
                checked += 1
                if one not in have:
                    dangling["%s.%s -> %s" % (group, field, target)].append(
                        "%s references %r" % (d.get("id", os.path.basename(p)), one))

    # Per-shot ids: shots[].template and shots[].camera.
    for group, listfield, itemfield, target in ITEM_REFS:
        src_dir = os.path.join(STUDIO, group)
        have = ids(target)
        if not os.path.isdir(src_dir) or have is None:
            skipped += 1
            continue
        for p in sorted(glob.glob(os.path.join(src_dir, "*.json"))):
            try:
                d = json.load(open(p, encoding="utf-8"))
            except Exception:
                continue          # already reported by the loop above
            for i, item in enumerate(d.get(listfield) or []):
                if not isinstance(item, dict):
                    continue
                one = item.get(itemfield)
                if not isinstance(one, str) or not one.strip():
                    continue
                checked += 1
                if one not in have:
                    dangling["%s.%s[].%s -> %s" % (group, listfield, itemfield, target)].append(
                        "%s beat %d references %r" % (d.get("id", os.path.basename(p)), i, one))

    for k, v in sorted(dangling.items()):
        print("%s  (%d)" % (k, len(v)))
        for line in v[:12]:
            print("    %s" % line)
        if len(v) > 12:
            print("    ... and %d more" % (len(v) - 12))

    # movies.style is dual-purpose, so it is not an error - but a value that LOOKS like an
    # id and does not resolve is almost certainly a typo, and that is worth saying.
    hints = []
    mdir, styles = os.path.join(STUDIO, "movies"), ids("styles")
    if os.path.isdir(mdir) and styles:
        for p in sorted(glob.glob(os.path.join(mdir, "*.json"))):
            try:
                d = json.load(open(p, encoding="utf-8"))
            except Exception:
                continue
            v = str((d.get("vars") or d).get("style", "")).strip()
            if v and looks_like_id(v) and v not in styles:
                hints.append("%s sets style: %r which looks like a card id but does not "
                             "resolve - free text is fine here, a typo is not"
                             % (os.path.basename(p), v))
    if hints:
        print("movies.style  (%d to eyeball)" % len(hints))
        for h in hints:
            print("    %s" % h)

    # `place` on a template is an id OR free text - compose.py implements both - so an
    # unresolved value cannot simply be an error. But a value SHAPED like an id that does
    # not resolve is a typo, and it reaches the prompt as a literal token like "locker_rom".
    # Same treatment as movies.style: report it to be eyeballed, do not fail on it.
    tdir, places = os.path.join(STUDIO, "templates"), ids("places")
    if os.path.isdir(tdir) and places:
        loose = []
        for p in sorted(glob.glob(os.path.join(tdir, "*.json"))):
            try:
                d = json.load(open(p, encoding="utf-8"))
            except Exception:
                continue
            v = str((d.get("sets") or {}).get("place", "")).strip()
            if v and looks_like_id(v) and v not in places:
                loose.append("%s sets place: %r which looks like a card id but does not "
                             "resolve - free text is fine here, a typo is not"
                             % (os.path.basename(p), v))
        if loose:
            print("templates.place  (%d to eyeball)" % len(loose))
            for h in loose:
                print("    %s" % h)

    total = sum(len(v) for v in dangling.values())
    print("\n%d references checked, %d dangling, %d rules skipped (group absent)"
          % (checked, total, skipped))
    if total and strict:
        sys.exit(1)


if __name__ == "__main__":
    main()
