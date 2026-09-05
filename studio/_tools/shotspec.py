#!/usr/bin/env python3
"""studio/_tools/shotspec.py - what a shot must never lose, and what it may.

THE GAP THIS CLOSES. A film's shots are described in three places at once: the prose in
film.json, the parameters of whatever built them, and a person's memory of the notes that
produced them. The third is where the important half lives - "the camera never rotates",
"the characters must be the cafe's own pictures", "the landing has to be pixel-exact" - and
it is the half that gets lost, so the same correction gets made twice.

A shotspec writes that half down and splits it in two:

  INVARIANTS  what the shot IS. Break one and it is a different shot, or a mistake that has
              already been made once. Each carries the reason and, where possible, a check
              that can be run.
  FLARE       what the shot happens to be wearing. Timings, intensities, which take, which
              song. Free to change. `promote: true` marks flare the director has decided
              should become invariant - the mechanism by which taste hardens into a rule.

  shotspec.py list <film>
  shotspec.py show <film> <shot>
  shotspec.py check <film> [shot]      # verify the machine-checkable invariants
  shotspec.py promote <film> <shot> <flare-id>

Specs live in studio/shotspecs/<film>/<shot>.json. They are documentation that the checker
can read, which is the only kind that stays true.
"""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
STUDIO = os.path.dirname(HERE)
SPECS = os.path.join(STUDIO, "shotspecs")
FILMS = os.path.join(STUDIO, "films")


def spec_dir(film):
    return os.path.join(SPECS, film)


def load(film, shot):
    p = os.path.join(spec_dir(film), shot + ".json")
    if not os.path.exists(p):
        raise KeyError("no shotspec for %s/%s" % (film, shot))
    return json.load(open(p, encoding="utf-8"))


def save(film, shot, d):
    os.makedirs(spec_dir(film), exist_ok=True)
    json.dump(d, open(os.path.join(spec_dir(film), shot + ".json"), "w",
                      encoding="utf-8"), indent=1, ensure_ascii=False)


def shots(film):
    d = spec_dir(film)
    # .json only - the directory also holds the .md a person edits, and f[:-5] on
    # "010.md" yields "0"
    return sorted(f[:-5] for f in os.listdir(d)
                  if f.endswith(".json")) if os.path.isdir(d) else []


def film_json(film):
    return json.load(open(os.path.join(FILMS, film, "film.json"), encoding="utf-8"))


# ── checks ──────────────────────────────────────────────────────────────────────────
# A check is a small declarative statement the spec can carry. Anything not expressible
# this way still belongs in the spec as prose - an unrunnable invariant is still worth
# more than an unwritten one.

def run_check(chk, sh, take):
    kind = chk.get("kind")
    if kind == "engine":
        got = (take or {}).get("engine", "")
        return got.startswith(chk["value"]), "engine=%s" % got
    if kind == "anchor_contains":
        got = sh.get("anchor", "")
        return chk["value"] in got, "anchor=%s" % got.split("/")[-1]
    if kind == "duration_between":
        got = (take or {}).get("duration", 0)
        return chk["min"] <= got <= chk["max"], "duration=%.2f" % got
    if kind == "camrig_preset":
        cam = sh.get("cam") or {}
        return cam.get("preset") == chk["value"], "preset=%s" % cam.get("preset")
    if kind == "take_prompt_contains":
        got = (take or {}).get("prompt", "")
        return chk["value"].lower() in got.lower(), "prompt=%s..." % got[:48]
    if kind == "angle":
        # where the camera IS.  Measured on the take's own first frame by the vertical
        # vanishing point; a place with no vertical lines cannot be judged and says so
        # rather than passing or failing on nothing.
        m = (take or {}).get("angle_measured") or {}
        if not m or m.get("confidence") in (None, "none"):
            return None, "this place has no verticals to measure an angle by"
        p = float(m.get("pitch", 0.0))
        want = (chk.get("want") or "eye level").replace("a ", "").strip()
        # relative to the plate this shot was built on: an ordinary photograph already has
        # upward-converging verticals, so an absolute threshold passes shots nobody angled
        base = ((sh.get("cam") or {}).get("angle") or {}).get("source_plate")
        d = (p - base) if base is not None else p
        got = ("pitch=%+.2f against the plate's %+.2f (change %+.2f)" % (p, base, d)) if base is not None \
            else "pitch=%+.2f (%s)" % (p, m.get("angle", "?"))
        if want.startswith("low"):
            ok = d >= 0.15
        elif want.startswith("high"):
            ok = d <= -0.15
        else:
            ok = abs(d) < 0.15
        if m.get("confidence") == "low":
            got += " - measured with low confidence"
        return ok, got
    if kind == "camera":
        m = (take or {}).get("cam_measured") or {}
        if not m:
            return False, "camera not measured on this take"
        z, pan, tilt = float(m.get("zoom", 1.0)), float(m.get("pan", 0.0)), float(m.get("tilt", 0.0))
        want = chk.get("want", "is static")
        got = "zoom=%.2f pan=%+.2f tilt=%+.2f (%s)" % (z, pan, tilt, m.get("camera", "?"))
        if want == "is static":
            ok = abs(z - 1.0) <= 0.08 and abs(pan) <= 0.08 and abs(tilt) <= 0.08
        elif want == "pushes in":
            ok = z >= 1.06
        elif want == "pulls back":
            ok = z <= 0.94
        elif want == "pans":
            ok = abs(pan) >= 0.06
        elif want == "pans left":
            ok = pan <= -0.06
        elif want == "pans right":
            ok = pan >= 0.06
        elif want == "tilts up":
            ok = tilt <= -0.06
        elif want == "tilts down":
            ok = tilt >= 0.06
        else:
            ok = False
        if m.get("confidence") == "low":
            got += " - measured with low confidence"
        return ok, got
    if kind == "qc_clean":
        # information and advisories are not faults: a take that ended closer than
        # it started, borrowed its soundtrack, or was warned before rendering that
        # a word is not in its picture has kept every promise the picture makes
        notes = list((take or {}).get("qc") or [])
        info_prefixes = ("ends closer", "sound borrowed", "words not in the picture")
        faults = [n for n in notes if not str(n).startswith(info_prefixes)]
        info = len(notes) - len(faults)
        return not faults, "qc=%s%s" % (faults or "clean", (" (+%d information)" % info) if info else "")
    return None, "no runnable check"


def check(film, only=None):
    f = film_json(film)
    bad = 0
    for shot in shots(film):
        if only and shot != only:
            continue
        s = load(film, shot)
        sh = f["shots"].get(shot) or {}
        take = next((t for t in sh.get("takes", []) if t["id"] == sh.get("picked")), None)
        lk = "   [LOCKED %s]" % s.get("locked_at", "") if s.get("locked") else ""
        print(chr(10) + "%s  %s%s" % (shot, s.get("title", ""), lk))
        # what a lock protects is not the spec text - it is that the TAKE the shot
        # was approved against is still the one the film points at
        if s.get("locked"):
            want, got = s.get("locked_take", ""), sh.get("picked", "")
            if want != got:
                print("   FAIL %-21s picked=%s, locked against %s"
                      % ("locked_take_changed", got or "(none)", want or "(none)"))
                bad += 1
            else:
                print("   OK %-23s take unchanged since lock" % "locked")
        if not take:
            print("   ! no picked take")
            bad += 1
        for inv in s.get("invariants", []):
            chk = inv.get("check")
            if not chk:
                print("   ~ %-24s (prose only)" % inv["id"])
                continue
            ok, detail = run_check(chk, sh, take)
            if ok is None:
                print("   ~ %-24s %s" % (inv["id"], detail))
            elif ok:
                print("   OK %-23s %s" % (inv["id"], detail))
            else:
                print("   FAIL %-21s %s   <- %s" % (inv["id"], detail, inv["rule"]))
                bad += 1
    print("\n%s" % ("all invariants hold" if not bad else "%d problem(s)" % bad))
    return bad


def show(film, shot):
    s = load(film, shot)
    print("\n%s  %s\n%s\n" % (shot, s.get("title", ""), s.get("beat", "")))
    print("INVARIANTS - break one and it is a different shot")
    for i in s.get("invariants", []):
        print("  * %s" % i["rule"])
        if i.get("why"):
            print("      why: %s" % i["why"])
    print("\nFLAIR - free to change")
    for i in s.get("flair", s.get("flare", [])):
        star = " [PROMOTED -> invariant]" if i.get("promote") else ""
        print("  - %-22s %s%s" % (i["id"], i.get("note", ""), star))
    b = s.get("build") or {}
    if b:
        print("\nBUILT BY  %s" % b.get("script", "?"))
        for k, v in b.items():
            if k != "script":
                print("  %-10s %s" % (k, v))


def promote(film, shot, fid):
    s = load(film, shot)
    for i in s.get("flair", s.get("flare", [])):
        if i["id"] == fid:
            s.setdefault("invariants", []).append(
                {"id": fid, "rule": i.get("note", fid),
                 "why": "promoted from flare by the director",
                 "check": i.get("check")})
            s["flair"] = [x for x in s.get("flair", s.get("flare", [])) if x["id"] != fid]
            save(film, shot, s)
            print("promoted %s -> invariant on %s/%s" % (fid, film, shot))
            return
    print("no flare %r on %s/%s" % (fid, film, shot))


a = sys.argv[1:]
if not a:
    print(__doc__)
elif a[0] == "list":
    for sh in shots(a[1]):
        s = load(a[1], sh)
        print("%-6s %-28s %d invariants, %d flare"
              % (sh, s.get("title", ""), len(s.get("invariants", [])),
                 len(s.get("flair", s.get("flare", [])))))
elif a[0] == "show":
    show(a[1], a[2])
elif a[0] == "check":
    sys.exit(1 if check(a[1], a[3] if len(a) > 3 else (a[2] if len(a) > 2 else None)) else 0)
elif a[0] == "promote":
    promote(a[1], a[2], a[3])
else:
    print(__doc__)
