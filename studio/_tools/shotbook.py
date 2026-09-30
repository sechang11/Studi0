#!/usr/bin/env python3
"""studio/_tools/shotbook.py - the shot encyclopedia's checker and index (craft/shots/).

    python3 studio/_tools/shotbook.py            # check every entry, write craft/shots/INDEX.md
    python3 studio/_tools/shotbook.py --check    # check only; exit 1 on the first problem list
    python3 studio/_tools/shotbook.py --find orbit   # which entry answers to a word

WHY. What the studio learns about a KIND of shot - an orbit, a glass shatter, a helmet POV -
was spread over a 5,000-line playbook in the order it was learned, a builder's catalog of
templates, and the notes of whichever film taught it. Nobody about to make an orbit reads
all of that, so the same mistakes came back. craft/shots/ holds one file per kind of shot:
the recipe to follow today, the checks before a take is picked, and the PROGRESSION - every
attempt, dated and graded, with what went wrong and what fixed it.

WHAT IT ENFORCES, and why each rule exists:

  one kind per entry         an id is a single kind of shot; its prefix names its family
  names are unique           an alias ("360", "vertigo") answers to exactly ONE entry, so a
                             lookup can never land on two recipes, and two kinds can never be
                             quietly merged under one name
  neighbours are named,      every entry lists the kinds it is most easily confused with and
  both ways                  says in one line how they differ; if A names B, B must name A -
                             this is what keeps a tilt from being filed as a pan, or a shatter
                             as a splash, when the recipes and failures are different
  the sections exist         recipe, checks, progression, failure modes, evidence
  progression is dated       each attempt heading starts YYYY-MM-DD and carries a grade
  tools exist                every studio/_tools/*.py, scripts/*.py and workflows/*.json an
                             entry names is on disk (a recipe that names a missing tool sends
                             someone looking - the same discipline as recipes.py)

Renders are box-local and out of git, so evidence paths to takes are listed, not checked.
"""
import argparse
import glob
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BOOK = os.path.join(ROOT, "craft", "shots")
INDEX = os.path.join(BOOK, "INDEX.md")

FAMILIES = {            # folder: (title, id prefixes, what belongs here)
    "camera": ("Camera moves", ("cam-",), "the camera travels, turns or zooms"),
    "framing": ("Framings and angles", ("frame-",), "where the camera stands and how much it sees"),
    "pov": ("Point of view", ("pov-",), "the camera IS a character's eyes"),
    "fx": ("Physical effects", ("fx-",), "liquids, glass, light, weather, particles, flame"),
    "cloth": ("Cloth and hair", ("cloth-", "hair-"), "fabric and hair under force"),
    "motion": ("Body motion", ("move-",), "what the body does"),
    "continuity": ("Continuity", ("cont-",), "what must stay the same from shot to shot"),
    "text": ("Text and graphics", ("text-",), "letters and interface in the picture"),
    "dialogue": ("Dialogue", ("dia-",), "a line spoken on screen"),
    "style": ("Style and masters", ("style-", "master-"), "the look of the whole film"),
    "transitions": ("Transitions", ("trans-",), "how one shot hands over to the next"),
    "pipeline": ("Pipeline steps", ("pipe-",), "not shots: the steps every shot passes through"),
}
STATUSES = {
    "proven": "a recipe that has worked on the films it names, checks and all",
    "works-with-caveats": "works; the caveats are in the entry and in its failure modes",
    "partial": "part of what is asked comes out; the entry says which part",
    "fails": "no recipe on this box delivers it yet; the entry says what was tried",
    "untested": "known only from the builder's catalog or from prose; no film has used it",
    "retired": "kept for its history; the entry names what replaced it",
}
GRADES = {"A+", "A", "A-", "B+", "B", "B-", "C+", "C", "C-", "D", "F", "n/a"}
SECTIONS = ["## Recipe", "## Checks before picking", "## Progression", "## Failure modes", "## Evidence"]
TOOL_RE = re.compile(r"`((?:studio/_tools|studio|scripts)/[\w./-]+\.py|workflows/[\w./-]+\.json)`")
LINK_RE = re.compile(r"\[`([a-z0-9-]+)`\]\(([^)]+)\)")


def parse(path):
    text = open(path, encoding="utf-8").read()
    rel = os.path.relpath(path, BOOK).replace(os.sep, "/")
    e = {"path": path, "rel": rel, "family": rel.split("/")[0], "text": text, "problems": []}
    m = re.match(r"# (.+?) \(`([a-z0-9-]+)`\)\s*\n", text)
    if not m:
        e["problems"].append("first line must be '# Title (`id`)'")
        return e
    e["title"], e["id"] = m.group(1).strip(), m.group(2)
    row = re.search(r"\n\|\s*family\s*\|\s*status\s*\|\s*last tested\s*\|\s*best result\s*\|\s*\n\|[-| ]+\|\s*\n"
                    r"\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|", text)
    if not row:
        e["problems"].append("the header table (family | status | last tested | best result) is missing")
    else:
        e["fam_cell"], e["status"], e["tested"], e["best"] = [x.strip() for x in row.groups()]
    a = re.search(r"\*\*Also called:\*\*\s*(.+)", text)
    e["aliases"] = [x.strip().lower() for x in a.group(1).split(",") if x.strip()] if a else []
    if not a:
        e["problems"].append("'**Also called:**' is missing")
    n = re.search(r"\*\*Not the same as:\*\*\s*\n((?:\s*- .+\n?)+)", text)
    e["neighbours"] = LINK_RE.findall(n.group(1)) if n else []
    if not n:
        e["problems"].append("'**Not the same as:**' with at least one linked neighbour is missing")
    for s in SECTIONS:
        if "\n" + s not in text:
            e["problems"].append("section '%s' is missing" % s)
    rec = re.search(r"\n## Recipe[^\n]*\n+(.+)", text)
    e["recipe_line"] = rec.group(1).strip() if rec else ""
    prog = text.split("\n## Progression", 1)[1].split("\n## ", 1)[0] if "\n## Progression" in text else ""
    e["attempts"] = re.findall(r"\n### (\d{4}-\d{2}-\d{2})\b[^\n]*?grade ([A-F][+-]?|n/a)", prog)
    heads = re.findall(r"\n### ([^\n]+)", prog)
    for h in heads:
        if not re.match(r"\d{4}-\d{2}-\d{2}\b", h) or not re.search(r"grade ([A-F][+-]?|n/a)\b", h):
            e["problems"].append("progression heading needs 'YYYY-MM-DD ... grade X': %r" % h[:70])
    e["tools"] = sorted(set(TOOL_RE.findall(text)))
    return e


def load():
    entries = [parse(p) for p in sorted(glob.glob(os.path.join(BOOK, "*", "*.md")))
               if os.path.basename(os.path.dirname(p)) in FAMILIES]
    by_id = {}
    for e in entries:
        if "id" not in e:
            continue
        fam = FAMILIES[e["family"]]
        if not e["id"].startswith(fam[1]):
            e["problems"].append("id %s does not belong in %s/ (prefixes %s)" % (e["id"], e["family"], fam[1]))
        if e.get("status") and e["status"] not in STATUSES:
            e["problems"].append("status %r is not one of %s" % (e["status"], ", ".join(STATUSES)))
        if e.get("fam_cell") and e["fam_cell"] != e["family"]:
            e["problems"].append("the table says family %r, the folder says %r" % (e["fam_cell"], e["family"]))
        if e["id"] in by_id:
            e["problems"].append("id %s is used twice (%s)" % (e["id"], by_id[e["id"]]["rel"]))
        by_id[e["id"]] = e
        slug = os.path.basename(e["path"])[:-3]
        if not e["id"].endswith(slug):
            e["problems"].append("file name %s.md should be the id without its prefix" % slug)
    owner = {}
    for e in by_id.values():
        for name in e["aliases"] + [e["title"].lower(), e["id"]]:
            if name in owner and owner[name] is not e:
                e["problems"].append("the name %r already answers to %s - one name, one entry" % (name, owner[name]["id"]))
            owner.setdefault(name, e)
        for nid, href in e["neighbours"]:
            other = by_id.get(nid)
            if other is None:
                e["problems"].append("neighbour %s has no entry" % nid)
                continue
            target = os.path.normpath(os.path.join(os.path.dirname(e["path"]), href))
            if target != os.path.normpath(other["path"]):
                e["problems"].append("the link to %s points at %s" % (nid, href))
            if e["id"] not in [x for x, _ in other["neighbours"]]:
                e["problems"].append("%s names %s as a neighbour but %s does not name it back" % (e["id"], nid, nid))
        for t in e["tools"]:
            if not os.path.exists(os.path.join(ROOT, t)):
                e["problems"].append("names %s, which is not on disk" % t)
    return by_id, owner, [e for e in entries if "id" not in e]


def dead_links():
    """Every relative .md link in the book - entries, README, reviews - must land on a file."""
    bad = []
    for p in glob.glob(os.path.join(BOOK, "**", "*.md"), recursive=True):
        if os.path.normpath(p) == os.path.normpath(INDEX):
            continue
        text = re.sub(r"```.*?```", "", open(p, encoding="utf-8").read(), flags=re.S)   # templates are examples
        for href in re.findall(r"\]\(([^)#\s]+\.md)(?:#[^)]*)?\)", text):
            if href.startswith("http") or os.path.basename(href) == "INDEX.md":     # INDEX.md is generated
                continue
            if not os.path.exists(os.path.normpath(os.path.join(os.path.dirname(p), href))):
                bad.append((os.path.relpath(p, BOOK).replace(os.sep, "/"), "dead link to %s" % href))
    return bad


def catalog_ids():
    p = os.path.join(ROOT, "studio", "shot_catalog.json")
    try:
        return [(x["id"], x.get("title", "")) for x in json.load(open(p))["shots"]]
    except Exception:
        return []


def write_index(by_id, owner):
    out = ["# The shot encyclopedia - index",
           "",
           "Generated by `python3 studio/_tools/shotbook.py` from the entries in this folder; edit the entries, "
           "not this file. How an entry is written, and the rules the checker holds it to: [README.md](README.md).",
           "",
           "Status: " + " · ".join("**%s** %d" % (s, sum(1 for e in by_id.values() if e.get("status") == s))
                                  for s in STATUSES) + " · **%d entries**" % len(by_id),
           ""]
    for fam, (title, _, what) in FAMILIES.items():
        rows = sorted((e for e in by_id.values() if e["family"] == fam), key=lambda e: e["title"].lower())
        if not rows:
            continue
        out += ["## %s (`%s/`)" % (title, fam), "", "_%s._" % what, "",
                "| entry | status | last tested | best result | the recipe in one line |", "|---|---|---|---|---|"]
        for e in rows:
            out.append("| [%s](%s) `%s` | %s | %s | %s | %s |" % (
                e["title"], e["rel"], e["id"], e.get("status", "?"), e.get("tested", "?"), e.get("best", "?"),
                e["recipe_line"].replace("|", "/")[:170]))
        out.append("")
    out += ["## Look up by name", "",
            "Every name a director might use, and the ONE entry it answers to.", "",
            "| name | entry |", "|---|---|"]
    for name in sorted(owner):
        e = owner[name]
        out.append("| %s | [%s](%s) |" % (name, e["title"], e["rel"]))
    out += ["", "## Easily confused - kept apart on purpose", "",
            "Each pair below is two kinds of shot with different recipes and different failures. "
            "The difference is written in both entries.", ""]
    pairs = sorted({tuple(sorted((e["id"], n))) for e in by_id.values() for n, _ in e["neighbours"]})
    for a, b in pairs:
        if a in by_id and b in by_id:
            out.append("- [%s](%s) ≠ [%s](%s)" % (by_id[a]["title"], by_id[a]["rel"], by_id[b]["title"], by_id[b]["rel"]))
    missing = [(i, t) for i, t in catalog_ids() if not any(i.replace("_", "-") in e["id"] or
                                                           i.replace("_", " ") in e["aliases"] for e in by_id.values())]
    if missing:
        out += ["", "## Builder templates with no entry yet", "",
                "Templates in `studio/shot_catalog.json` (the /film builder's shelf) that no entry here claims "
                "by id or alias:", ""] + ["- `%s` - %s" % (i, t) for i, t in missing]
    open(INDEX, "w", encoding="utf-8").write("\n".join(out) + "\n")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--check", action="store_true", help="check only, do not write INDEX.md")
    ap.add_argument("--find", default="", help="which entry answers to this word")
    a = ap.parse_args()
    by_id, owner, broken = load()
    if a.find:
        w = a.find.lower()
        hits = sorted({e["id"] for n, e in owner.items() if w in n})
        for h in hits:
            print("%-26s %s" % (h, by_id[h]["rel"]))
        return 0 if hits else 1
    problems = [(e["rel"], p) for e in list(by_id.values()) + broken for p in e["problems"]] + dead_links()
    for rel, p in problems:
        print("  %s: %s" % (rel, p))
    if not a.check:
        write_index(by_id, owner)
    print("SHOTBOOK: %d entries, %d names, %d problem(s)%s" % (
        len(by_id), len(owner), len(problems), "" if a.check else " - index written to craft/shots/INDEX.md"))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
