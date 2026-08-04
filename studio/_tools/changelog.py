#!/usr/bin/env python3
"""Build the app's changelog from git history.

    python3 studio/_tools/changelog.py            # -> studio/changelog.json
    python3 studio/_tools/changelog.py --limit 60
    python3 studio/_tools/changelog.py --print

GENERATED, NOT MAINTAINED BY HAND. A changelog somebody has to remember to update is a
changelog that goes stale, and this project already has enough places where a card claims
something the pixels do not support. The git history is the only record that cannot drift
from what actually happened, so it is the source.

It also happens to be unusually good source material here, because this project's commit
messages record what was MEASURED rather than what was intended - what was rendered, what
was looked at, what turned out to be wrong. Those bodies are the interesting half of the
changelog and they are kept whole rather than truncated to a one-liner.

AREAS are derived from the paths a commit touched, so the tags are a fact about the diff
rather than a label someone chose. A commit that edits studio/styles/ is tagged Styles
whether or not its subject mentions styles.
"""
import argparse, json, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
STUDIO = os.path.dirname(HERE)
ROOT = os.path.dirname(STUDIO)
OUT = os.path.join(STUDIO, "changelog.json")

REC = "\x1e"   # record separator - cannot appear in a commit message
FLD = "\x1f"   # field separator

# (path fragment, area). First match wins, so put the specific ones first.
AREAS = [
    ("studio/styles/",        "Styles"),
    ("studio/places/",        "Places"),
    ("studio/characters/",    "Cast"),
    ("studio/cast.html",      "Cast"),
    ("studio/templates/",     "Templates"),
    ("studio/loras/",         "LoRAs"),
    ("studio/loras.html",     "LoRAs"),
    ("studio/motions/",       "Motion"),
    ("studio/wizard.html",    "Wizard"),
    ("studio/compose.py",     "Pipeline"),
    ("studio/compile.py",     "Pipeline"),
    ("scripts/",              "Pipeline"),
    ("workflows/",            "Pipeline"),
    ("studio/serve.py",       "App"),
    ("studio/app.html",       "App"),
    ("studio/_tools/",        "Tooling"),
    ("craft/",                "Docs"),
    ("studio/samples/",       "Samples"),
    (".html",                 "App"),
    ("studio/",               "Libraries"),
]

# Samples alone is noise - a commit is rarely ABOUT its samples. Dropped when the commit
# also touched something more specific.
WEAK = {"Samples", "Libraries"}


def sh(*a):
    return subprocess.run(a, cwd=ROOT, capture_output=True, text=True).stdout


def areas_for(files):
    found = []
    for f in files:
        for frag, area in AREAS:
            if frag in f:
                if area not in found:
                    found.append(area)
                break
    strong = [a for a in found if a not in WEAK]
    return strong or found


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=200)
    ap.add_argument("--print", dest="show", action="store_true")
    a = ap.parse_args()

    fmt = FLD.join(["%H", "%h", "%ad", "%an", "%s", "%b"]) + REC
    raw = sh("git", "log", "--date=iso-strict", "-n", str(a.limit), "--pretty=format:" + fmt)
    if not raw.strip():
        sys.exit("no git history found - is this a repo?")

    entries = []
    for rec in raw.split(REC):
        rec = rec.strip("\n")
        if not rec.strip():
            continue
        parts = rec.split(FLD)
        if len(parts) < 6:
            continue
        full, short, date, author, subject, body = parts[0], parts[1], parts[2], parts[3], parts[4], parts[5]

        stat = sh("git", "show", "--numstat", "--format=", full)
        files, added, removed = [], 0, 0
        for line in stat.splitlines():
            bits = line.split("\t")
            if len(bits) != 3:
                continue
            files.append(bits[2])
            for n, tgt in ((bits[0], "a"), (bits[1], "r")):
                if n.isdigit():
                    if tgt == "a":
                        added += int(n)
                    else:
                        removed += int(n)

        # Drop the trailer - it is on every commit and says nothing a reader needs.
        lines = [l for l in body.strip().splitlines()
                 if not l.strip().lower().startswith("co-authored-by:")]
        clean = "\n".join(lines).strip()
        paras = [p.strip() for p in clean.split("\n\n") if p.strip()]

        entries.append({
            "hash": short, "full": full, "date": date[:10], "time": date[11:16],
            "author": author, "subject": subject,
            "body": clean, "paragraphs": paras,
            "areas": areas_for(files),
            "files": len(files), "added": added, "removed": removed,
        })

    by_date = {}
    for e in entries:
        by_date.setdefault(e["date"], 0)
        by_date[e["date"]] += 1

    doc = {
        "generated_from": "git log",
        "count": len(entries),
        "days": sorted(by_date.items(), reverse=True),
        "areas": sorted({x for e in entries for x in e["areas"]}),
        "entries": entries,
        "note": ("Generated from git history by studio/_tools/changelog.py, not written by "
                 "hand. The bodies record what was measured - what was rendered, what was "
                 "looked at, and where a claim turned out to be wrong."),
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=1, ensure_ascii=False)
        f.write("\n")

    print("%s  (%d entries, %d days, %d areas)"
          % (OUT, len(entries), len(by_date), len(doc["areas"])))
    if a.show:
        for e in entries[:14]:
            print("  %s  %-9s %-30s %s" % (e["date"], e["hash"],
                                           ",".join(e["areas"])[:30], e["subject"][:70]))


if __name__ == "__main__":
    main()
