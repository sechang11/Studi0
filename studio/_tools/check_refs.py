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
REFS = [
    ("styles",     "suits_looks",   "looks"),
    ("templates",  "look",          "looks"),
    ("templates",  "style",         "styles"),
    ("movies",     "style",         "styles"),
    ("characters", "default_wear",  "wear"),
    ("places",     "suits_looks",   "looks"),
]


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

    total = sum(len(v) for v in dangling.values())
    print("\n%d references checked, %d dangling, %d rules skipped (group absent)"
          % (checked, total, skipped))
    if total and strict:
        sys.exit(1)


if __name__ == "__main__":
    main()
