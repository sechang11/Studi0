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
            v = d.get(field)
            if not v:
                continue
            for one in (v if isinstance(v, list) else [v]):
                if not isinstance(one, str) or not one.strip():
                    continue
                checked += 1
                if one not in have:
                    dangling["%s.%s -> %s" % (group, field, target)].append(
                        "%s references %r" % (d.get("id", os.path.basename(p)), one))

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

    total = sum(len(v) for v in dangling.values())
    print("\n%d references checked, %d dangling, %d rules skipped (group absent)"
          % (checked, total, skipped))
    if total and strict:
        sys.exit(1)


if __name__ == "__main__":
    main()
