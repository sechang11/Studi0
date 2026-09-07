#!/usr/bin/env python3
"""Do the three copies of the method agree with each other and with the code?

Written the morning the three copies diverged within hours of being written: one dropped a
rung of the length table, one overstated the adoption gate, one told a person a level-1 pack
could not be cast.  Prose about the code was written by hand three times; this makes the
numbers come from the code and the copies answer for each other.

    python3 studio/_tools/method_check.py          # exit 1 on the first disagreement

Checks, in order: every LTX_SAFE rung appears in the guide and in §95; every named grade in
post.GRADES appears in the guide; the adoption gate in the playbook says what pack_lora.py does;
statements measured false are absent from every copy; the facts a reader most needs are present
in every copy.  Run before committing any change to METHOD.md, §95 or CLAUDE.md.
"""
import importlib.util
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "studio"))
sys.path.insert(0, os.path.join(ROOT, "studio", "_tools"))

FILES = {
    "guide": os.path.join(ROOT, "docs", "METHOD.md"),
    "playbook": os.path.join(ROOT, "studio", "LTX_PLAYBOOK.md"),
    "agent": os.path.join(ROOT, "CLAUDE.md"),
}


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def section_95(pb):
    i = pb.find("## §95")
    j = pb.find("\n## §", i + 6)
    return pb[i:j if j > 0 else None]


problems = []


def need(cond, msg):
    if not cond:
        problems.append(msg)


def main():
    texts = {k: open(p, encoding="utf-8").read() for k, p in FILES.items()}
    guide, agent = texts["guide"], texts["agent"]
    s95 = section_95(texts["playbook"])
    need(s95, "playbook has no §95")

    # 1  the length table comes from the code, in every copy that states it
    film = load("film_mod", os.path.join(ROOT, "studio", "film.py"))
    for mp, secs in film.LTX_SAFE:
        need(re.search(r"%d\s*s\b" % secs, guide), "guide: LTX_SAFE rung %.1f MP -> %d s missing" % (mp, secs))
        need(re.search(r"%d\s*s\b" % secs, s95), "§95: LTX_SAFE rung %.1f MP -> %d s missing" % (mp, secs))
        need(re.search(r"%d\s*s\b" % secs, agent), "CLAUDE.md: LTX_SAFE rung %.1f MP -> %d s missing" % (mp, secs))

    # 2  the grades a person can choose are the ones post.py offers
    post = load("post_mod", os.path.join(ROOT, "studio", "_tools", "post.py"))
    for name in post.GRADES:
        need(re.search(r"\*%s\*|`%s`|\b%s\b" % (name, name, name), guide), "guide: grade %r not described" % name)
    need(post.DEFAULT_GRADE in guide and "default" in guide, "guide: default grade not named")

    # 3  the adoption gate says what the code does
    src = open(os.path.join(ROOT, "studio", "_tools", "pack_lora.py"), encoding="utf-8").read()
    m = re.search(r"better\s*=.*max\(([\d.]+),\s*spread\s*/\s*([\d.]+)\)", src)
    if m:
        floor, div = m.group(1), m.group(2)
        fl, dv = float(floor), float(div)
        forms = {"max(%s, spread/%s)" % (a, b) for a in {floor, "%g" % fl} for b in {div, "%g" % dv}}
        forms |= {f.replace("/", " / ") for f in set(forms)}
        need(any(f in s95 for f in forms) or "half its spread" in s95 or "half of its spread" in s95,
             "§95: adoption gate must say margin > max(%g, spread/%g)" % (fl, dv))
        need("above its own spread" not in s95, "§95: 'above its own spread' overstates the gate")
    else:
        problems.append("pack_lora.py: adoption gate not found where expected")

    # 4  things measured false must be absent everywhere
    forbidden = [
        ("editor picks the engine", "the engine is caller-chosen, default LTX; in-place motions are pinned"),
        ("below level 2 will not hold", "level 1 is the casting floor"),
        ("trainer's base model is the anime one; photoreal packs use", "photoreal faces train on RealVisXL; the gap is the render route"),
        ("For photoreal a single 4-second take typically holds", "the face clock is by motion, not by look"),
        ("nothing takes N tagged identities", "H3 ref2va takes up to nine tagged reference images"),
        ("one anchor per scene,", "one source per scene; the studio composes a start frame per shot"),
    ]
    for phrase, why in forbidden:
        for k, t in (("guide", guide), ("§95", s95), ("CLAUDE.md", agent)):
            need(phrase not in t, "%s still says %r - %s" % (k, phrase, why))

    # 5  the facts a reader most needs, present in every copy
    must = {
        "guide": ["level 1", "still 4.3", "walk 4.0", "RealVisXL", "Qwen", "ref2va", "spread"],
        "§95": ["1.2 MP", "RealVisXL", "ref2va", "spread/2", "level 1"],
        "CLAUDE.md": ["ref2va", "RealVisXL", "spread"],
    }
    for k, words in must.items():
        t = {"guide": guide, "§95": s95, "CLAUDE.md": agent}[k].lower()
        for w in words:
            need(w.lower() in t, "%s: missing %r" % (k, w))

    # 6  the review clock exists, parses, and the agent is told to run it
    pb = texts["playbook"]
    mclk = re.search(r"^last_checked:\s*(\d{4}-\d{2}-\d{2})\s*$", pb, re.M)
    mcad = re.search(r"^cadence_days:\s*(\d+)\s*$", pb, re.M)
    need(mclk is not None and mcad is not None, "playbook: §0 review clock (last_checked / cadence_days) missing")
    need("## §0" in pb and pb.find("## §0") < pb.find("## 1."), "playbook: §0 must come before §1")
    need("review_clock.py" in agent, "CLAUDE.md: must tell the agent to run review_clock.py")
    need("## §96" in pb, "playbook: §96 (the standard pipeline) missing")

    if problems:
        print("METHOD CHECK: %d problem(s)" % len(problems))
        for p in problems:
            print("  -", p)
        sys.exit(1)
    print("METHOD CHECK: the three copies agree with each other and with the code")


if __name__ == "__main__":
    main()
