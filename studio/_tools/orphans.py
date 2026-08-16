#!/usr/bin/env python3
"""studio/_tools/orphans.py - which card libraries have a consumer, and which do not.

This project's recurring defect is not "broken", it is "built, correct, and nothing reads
it". The voice-overlap warning printed and was ignored. LTX-2.5 sat verified in the
catalogue and unpublished. The whole audio library was enumerated on every boot to print
a number. Each was found by accident, one at a time.

So: ask every card folder three questions, mechanically.

  READ    does any Python outside the card tooling load this folder?
  USED    does any authored film or movie name a card from it?
  SHOWN   is it reachable in the app - a library KIND, or a serve.py GROUP?

A folder that is none of the three is inventory nobody can spend. That is not
automatically wrong: a library can legitimately run ahead of its consumer. But it should
be a decision someone made, not a thing nobody noticed, which is what it has been.

Deliberately crude. It greps. A false positive here costs a minute of reading; the
alternative is another silent orphan found by accident in six months.
"""
import glob
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
STUDIO = os.path.dirname(HERE)
ROOT = os.path.dirname(STUDIO)

# Files that merely CATALOGUE cards would make everything look consumed, so they do not
# count as a reader. cards.py validates schemas, library_index browses, the taxonomy and
# this file name every folder by definition.
NOT_A_READER = {"cards.py", "library_index.py", "audio_taxonomy.py", "orphans.py",
                "healthcheck.py", "check_refs.py", "make_cards.py", "gen_cards.py",
                "capability_scan.py", "_write_caps.py", "page_snapshot.py"}


def py_files():
    for pat in ("*.py", "scripts/*.py", "studio/*.py", "studio/_tools/*.py"):
        for p in glob.glob(os.path.join(ROOT, pat)):
            if os.path.basename(p) not in NOT_A_READER:
                yield p


def film_blobs():
    out = []
    for pat in ("films/*.json", "films/**/*.json", "studio/movies/*.json"):
        for p in glob.glob(os.path.join(ROOT, pat), recursive=True):
            try:
                out.append((p, open(p, encoding="utf-8").read()))
            except OSError:
                pass
    return out


def main():
    folders = sorted(d for d in os.listdir(STUDIO)
                     if os.path.isdir(os.path.join(STUDIO, d))
                     and not d.startswith(("_", "."))
                     and glob.glob(os.path.join(STUDIO, d, "*.json")))

    src = [(p, open(p, encoding="utf-8", errors="ignore").read()) for p in py_files()]
    films = film_blobs()

    # what the app can show
    try:
        sys.path.insert(0, HERE)
        import library_index as L
        shown_lib = set(L.KINDS.values())
    except Exception:
        shown_lib = set()
    try:
        serve = open(os.path.join(STUDIO, "serve.py"), encoding="utf-8").read()
        m = re.search(r"GROUPS = \[(.*?)\]", serve, re.S)
        groups = set(re.findall(r'"([a-z0-9_]+)"', m.group(1))) if m else set()
    except OSError:
        groups = set()

    rows = []
    for f in folders:
        ids = [os.path.splitext(os.path.basename(p))[0]
               for p in glob.glob(os.path.join(STUDIO, f, "*.json"))
               if not os.path.basename(p).startswith("_")]
        # READ: a python file that names the folder as a path
        readers = [os.path.basename(p) for p, t in src
                   if re.search(r'["\'/]%s["\'/]' % re.escape(f), t)]
        # USED: an authored film naming one of its ids, as a value not a substring
        used = 0
        for _p, blob in films:
            if any(re.search(r'"%s"' % re.escape(i), blob) for i in ids):
                used += 1
        rows.append({"folder": f, "cards": len(ids), "readers": sorted(set(readers)),
                     "films": used,
                     "in_library": f in shown_lib, "in_groups": f in groups})

    rows.sort(key=lambda r: (bool(r["readers"]) + bool(r["films"])
                             + (r["in_library"] or r["in_groups"]), -r["cards"]))

    print("%-14s %5s  %-5s %-5s %-6s  %s"
          % ("folder", "cards", "read", "films", "shown", "readers"))
    print("-" * 96)
    orphan = []
    for r in rows:
        shown = "library" if r["in_library"] else ("picker" if r["in_groups"] else "-")
        score = bool(r["readers"]) + bool(r["films"]) + (r["in_library"] or r["in_groups"])
        print("%-14s %5d  %-5s %-5s %-6s  %s"
              % (r["folder"], r["cards"], "yes" if r["readers"] else "NO",
                 r["films"] or "NO", shown, ", ".join(r["readers"][:3]) or "-"))
        if score == 0:
            orphan.append(r["folder"])
    print()
    if orphan:
        print("NO CONSUMER AT ALL: %s" % ", ".join(orphan))
    else:
        print("every card folder has at least one consumer")
    return 0


if __name__ == "__main__":
    sys.exit(main())
