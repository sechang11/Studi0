#!/usr/bin/env python3
"""Index every document in the project so the app can serve them.

    python3 studio/_tools/docs.py            # -> studio/docs.json
    python3 studio/_tools/docs.py --check    # report only, exit 1 on a problem
    python3 studio/_tools/docs.py --print

WHY THIS EXISTS. There are around thirty markdown documents in this repository holding
almost everything that was ever measured here - STATE.md is over a thousand lines,
STYLE_AND_LAYERS.md over eight hundred - and NOT ONE of them is reachable from the app. They
can only be read over SSH. Meanwhile the app has thirteen how-to guides at /guide, a
capability catalogue at /capabilities and a changelog at /changelog, and nothing ties the
four together.

So this walks the repo, classifies every document by what it is FOR, and emits an index the
/docs page renders. The classification is the useful part: a reader wants to know whether a
document tells them HOW TO DO something, WHAT WAS MEASURED, WHAT THE BOX CAN DO, or WHAT
CHANGED - and those are four different needs that the flat file listing cannot express.

TITLES AND SUMMARIES COME FROM THE FILES. The title is the first H1; the summary is the
first real paragraph under it. Nothing is invented here - a document with no H1 is reported
as such rather than given a title someone made up, because a hand-written index drifts from
the files the moment anyone edits one.
"""
import argparse, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
STUDIO = os.path.dirname(HERE)
ROOT = os.path.dirname(STUDIO)
OUT = os.path.join(STUDIO, "docs.json")

# (section id, title, blurb) - the order is the reading order on the page.
SECTIONS = [
    ("start", "Start here",
     "The shortest routes in, and the one page that explains why the app asks what it asks."),
    ("howto", "How to use each section",
     "One guide per page of the app. What it is for, what to do first, what will confuse you."),
    ("measured", "What was measured",
     "The findings this project is actually built on - each one established by rendering "
     "something and looking at it, and several of them corrections to earlier claims."),
    ("capability", "What the box can do",
     "The models, workflows and capabilities installed here, including the ones the app "
     "does not expose yet."),
    ("state", "State, health and history",
     "Where the project actually stands, what is broken, and what changed when."),
    ("reference", "Reference",
     "Inventories, audits and working notes."),
]

# Explicit routing by filename. Anything not listed is classified by a heuristic and
# reported, so a new document shows up rather than vanishing.
ROUTE = {
    "QUICKSTART.md": "start", "README.md": "start",
    "PROMPTING.md": "measured", "STYLE_AND_LAYERS.md": "measured",
    "KNOWN_CHARACTERS.md": "measured", "CHARACTER_ON_QWEN.md": "measured",
    "TRAINING_CAPTIONS.md": "measured", "CURRENT_PRACTICE.md": "measured",
    "INSPIRATION.md": "measured", "FILMCRAFT.md": "measured",
    "FILM-CRAFT-AUDIT.md": "measured",
    "CAPABILITIES.md": "capability", "NEW-CAPABILITIES.md": "capability",
    "WORKFLOWS.md": "capability", "LORAS.md": "capability",
    "TEMPLATES.md": "capability", "AUDIO.md": "capability", "VOICE.md": "capability",
    "FILMMAKING.md": "capability",
    "STATE.md": "state", "HEALTH.md": "state", "HANDOVER.md": "state",
    "GENERATED.md": "state",
    "MODEL-SHOPPING-LIST.md": "reference", "AI-CONTENT-MAP.md": "reference",
    "STORY.md": "reference",
}

SKIP = {"MEMORY.md", "CLAUDE.md", "LICENSE.md"}
SKIP_DIRS = {".git", "node_modules", "__pycache__", "samples", "output", "_staging"}


def classify(name, text):
    if name in ROUTE:
        return ROUTE[name], "routed"
    # The camera-*.md stubs are per-variable notes, several of them about moves that do
    # NOT work - dolly_zoom, orbit and rack_focus are byte-identical to static. Filing
    # them under "what the box can do" would read as a claim the project has measured to
    # be false, so they go to reference with the rest of the working notes.
    if name.startswith("camera-") or name in ("lipsync.md", "blocking.md",
                                              "audio-picture-offset.md"):
        return "reference", "stub"
    low = (name + " " + text[:600]).lower()
    if any(w in low for w in ("measured", "verdict", "rendered and looked", "we tested")):
        return "measured", "heuristic"
    if any(w in low for w in ("capability", "workflow", "model", "installed")):
        return "capability", "heuristic"
    if any(w in low for w in ("how to", "guide", "getting started", "first")):
        return "howto", "heuristic"
    return "reference", "fallback"


def title_and_summary(text, fallback):
    title, summary = None, ""
    lines = text.splitlines()
    for i, ln in enumerate(lines):
        if ln.startswith("# "):
            title = ln[2:].strip()
            for nxt in lines[i + 1:]:
                s = nxt.strip()
                if not s or s.startswith(("#", "|", "-", "*", ">", "```", "=")):
                    continue
                summary = s
                break
            break
    return (title or fallback), summary


def walk():
    found = []
    for base, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".")]
        for fn in files:
            if not fn.endswith(".md") or fn in SKIP:
                continue
            p = os.path.join(base, fn)
            rel = os.path.relpath(p, ROOT).replace("\\", "/")
            # The 13 how-to guides have their own page and their own reader at /guide.
            # Index them so /docs can point at them, but do not duplicate their bodies.
            is_guide = rel.startswith("studio/guides/")
            try:
                with open(p, encoding="utf-8") as f:
                    text = f.read()
            except Exception as e:
                found.append({"rel": rel, "error": str(e)[:120]})
                continue
            sec, how = ("howto", "guide-dir") if is_guide else classify(fn, text)
            title, summary = title_and_summary(text, fn[:-3].replace("-", " ").title())
            slug = re.sub(r"[^a-z0-9]+", "-", rel.lower().replace(".md", "")).strip("-")
            found.append({
                "rel": rel, "slug": slug, "file": fn, "section": sec, "classified_by": how,
                "title": title, "summary": summary,
                "lines": text.count("\n") + 1, "bytes": len(text.encode("utf-8")),
                "has_h1": text.lstrip().startswith("# ") or "\n# " in text,
                "guide_slug": (fn[:-3] if is_guide else None),
            })
    return found


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--print", dest="show", action="store_true")
    a = ap.parse_args()

    docs = walk()
    problems = [d for d in docs if d.get("error") or not d.get("has_h1")]

    by_sec = {}
    for d in docs:
        if d.get("error"):
            continue
        by_sec.setdefault(d["section"], []).append(d)
    for v in by_sec.values():
        v.sort(key=lambda d: (-d["lines"], d["title"]))

    doc = {
        "sections": [{"id": s, "title": t, "blurb": b,
                      "docs": by_sec.get(s, [])} for s, t, b in SECTIONS],
        "count": len([d for d in docs if not d.get("error")]),
        "problems": [{"rel": d["rel"], "why": d.get("error") or "no H1 title"}
                     for d in problems],
        "note": ("Generated from the repository by studio/_tools/docs.py. Titles and "
                 "summaries are read from the files themselves, so this index cannot "
                 "drift from what the documents actually say."),
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=1, ensure_ascii=False)
        f.write("\n")

    print("%s  (%d documents, %d sections, %d problems)"
          % (OUT, doc["count"], len(SECTIONS), len(problems)))
    if a.show:
        for s in doc["sections"]:
            print("\n  %s (%d)" % (s["title"], len(s["docs"])))
            for d in s["docs"][:40]:
                print("    %-30s %5d lines  %s" % (d["file"], d["lines"], d["title"][:44]))
    for p in doc["problems"]:
        print("  ! %-40s %s" % (p["rel"], p["why"]))
    if a.check and problems:
        sys.exit(1)


if __name__ == "__main__":
    main()
