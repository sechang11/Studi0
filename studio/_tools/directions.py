#!/usr/bin/env python3
"""studio/_tools/directions.py - the director's notes, and how to make a film obey them.

    "write down the pointers somewhere so when we generate new commercials, we can have
     templates to choose from based on my director instructions"

A note on its own is history. A note a new film can be TOLD to obey is a tool, so this
does both: it prints what was said and what it changed, and it applies a named bundle to a
film spec.

    python3 studio/_tools/directions.py                     what has been said
    python3 studio/_tools/directions.py --looks             the templates
    python3 studio/_tools/directions.py --explain vivid
    python3 studio/_tools/directions.py --apply outdoor_hero films/shorts/ad-atlas-pack.json
    python3 studio/_tools/directions.py --check films/shorts/*.json

THE THREE KINDS ARE NOT THE SAME FACT, which is why they are labelled:

    fix    produced a change; carries the setting and the measurement
    keep   praised; written down so a later "improvement" cannot quietly remove it. The
           punch/shake layer was added to make films livelier and made them worse, and
           nothing recorded that the calm version had been preferred.
    want   asked for and NOT delivered. Kept visible rather than silently dropped.

--check is the one that earns its place over time: it reads a film and reports which
directions it currently disobeys, so a spec written before a note existed can be found
rather than remembered.
"""
import argparse
import glob
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
STUDIO = os.path.dirname(HERE)
ROOT = os.path.dirname(STUDIO)
DIRS = os.path.join(STUDIO, "directions")
LOOKS = os.path.join(STUDIO, "looks_directed.json")

C = {"fix": "\033[36m", "keep": "\033[32m", "want": "\033[33m", "off": "\033[0m"}


def load_directions():
    out = {}
    for p in sorted(glob.glob(os.path.join(DIRS, "*.json"))):
        d = json.loads(io.open(p, encoding="utf-8").read())
        out[d["id"]] = d
    return out


def load_looks():
    if not os.path.exists(LOOKS):
        return {}
    return json.loads(io.open(LOOKS, encoding="utf-8").read()).get("looks", {})


def wrap(s, w=74, indent=9):
    words, lines, cur = str(s).split(), [], ""
    for x in words:
        if len(cur) + len(x) + 1 > w and cur:
            lines.append(cur)
            cur = x
        else:
            cur = (cur + " " + x).strip()
    if cur:
        lines.append(cur)
    return ("\n" + " " * indent).join(lines)


def show_all(ds):
    for kind, title in (("fix", "FIXES - a note that changed the renderer"),
                        ("keep", "KEEPS - praised; do not let an 'improvement' remove it"),
                        ("want", "WANTS - asked for, not delivered")):
        got = [d for d in ds.values() if d.get("kind") == kind]
        if not got:
            continue
        print("\n%s%s%s" % (C[kind], title, C["off"]))
        for d in sorted(got, key=lambda x: x["id"]):
            print("  %-22s %s" % (d["id"], wrap('"%s"' % d["note"], indent=25)))
            if d.get("status", "").startswith("OUTSTANDING"):
                print("  %-22s %s%s%s" % ("", C["want"], d["status"], C["off"]))


def explain(ds, i):
    d = ds.get(i)
    if not d:
        sys.exit("no direction %r. try --list" % i)
    print("%s%s  [%s]%s" % (C.get(d["kind"], ""), d["id"], d["kind"], C["off"]))
    print("  heard    %s" % d.get("heard"))
    print("  said     %s" % wrap('"%s"' % d["note"]))
    print("  means    %s" % wrap(d.get("means")))
    if d.get("sets"):
        print("  sets     %s" % json.dumps(d["sets"]))
    if d.get("grade"):
        print("  grade    %s" % wrap(d["grade"]))
    if d.get("evidence"):
        print("  evidence %s" % wrap(d["evidence"]))
    print("  status   %s" % d.get("status"))


def apply_look(look_id, film_path, looks, ds):
    lk = looks.get(look_id)
    if not lk:
        sys.exit("no look %r. try --looks" % look_id)
    film = json.loads(io.open(film_path, encoding="utf-8").read())
    before = {k: film.get(k) for k in lk["sets"]}
    film.update(lk["sets"])
    film["look_template"] = look_id
    io.open(film_path, "w", encoding="utf-8", newline="\n").write(
        json.dumps(film, indent=2, ensure_ascii=False) + "\n")
    print("%s <- %s" % (os.path.basename(film_path), look_id))
    for k, v in lk["sets"].items():
        print("   %-10s %s -> %s" % (k, before.get(k), v))
    print("   obeys: %s" % ", ".join(lk["directions"]))
    if lk.get("warning"):
        print("   %s! %s%s" % (C["want"], wrap(lk["warning"], indent=6), C["off"]))


def check(paths, ds):
    """Which directions does each film currently disobey?"""
    rows = []
    for p in sorted(paths):
        if os.path.basename(p).startswith("_"):
            continue
        f = json.loads(io.open(p, encoding="utf-8").read())
        bad = []
        for d in ds.values():
            for k, want in (d.get("sets") or {}).items():
                if f.get(k, False) != want:
                    bad.append("%s wants %s=%s" % (d["id"], k, want))
        rows.append((os.path.basename(p)[:-5], f.get("look_template"), bad))
    print("%-22s %-18s %s" % ("film", "look", "disobeys"))
    for name, lk, bad in rows:
        print("%-22s %-18s %s" % (name, lk or "-",
                                  "; ".join(sorted(set(bad))) or "nothing"))
    n = sum(1 for _n, _l, b in rows if b)
    print("\n%d of %d films disobey at least one direction." % (n, len(rows)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--looks", action="store_true")
    ap.add_argument("--explain", default="")
    ap.add_argument("--apply", nargs=2, metavar=("LOOK", "FILM"))
    ap.add_argument("--check", nargs="*")
    a = ap.parse_args()
    ds, looks = load_directions(), load_looks()
    if not ds:
        sys.exit("no directions in %s" % DIRS)

    if a.explain:
        return explain(ds, a.explain)
    if a.apply:
        return apply_look(a.apply[0], a.apply[1], looks, ds)
    if a.check is not None:
        paths = a.check or glob.glob(os.path.join(ROOT, "films", "shorts", "*.json"))
        return check(paths, ds)
    if a.looks:
        print("LOOK TEMPLATES - a film wears one with \"look_template\": \"<id>\"\n")
        for k, v in looks.items():
            print("  %s%s%s  %s" % (C["fix"], k, C["off"], v["name"]))
            print("     for    %s" % wrap(v["for"], indent=12))
            print("     sets   %s" % json.dumps(v["sets"]))
            print("     obeys  %s" % ", ".join(v["directions"]))
            if v.get("warning"):
                print("     %s!      %s%s" % (C["want"], wrap(v["warning"], indent=12),
                                              C["off"]))
            print()
        return
    show_all(ds)
    print("\n%d directions, %d look templates. --looks, --explain <id>, "
          "--apply <look> <film>, --check" % (len(ds), len(looks)))


if __name__ == "__main__":
    main()
