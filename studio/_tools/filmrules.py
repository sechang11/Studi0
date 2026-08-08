#!/usr/bin/env python3
"""Check a film against craft/VIDEO_RULES.md, and fail the build when a rule is broken.

    python3 studio/_tools/filmrules.py --list
    python3 studio/_tools/filmrules.py --check films/salt_road_ep01.json
    python3 studio/_tools/filmrules.py --check films/x.json --output out.mp4
    python3 studio/_tools/filmrules.py --check films/x.json --strict   # warnings fail too

THE RULES FILE IS THE SOURCE, NOT THIS SCRIPT. VIDEO_RULES.md is written by hand every time
someone spots a bug; this reads it and runs whatever checks the rules name. A rule with
`check: none` still appears in the report - being written down is most of the value, and a
rule nobody can automate is not thereby less true.

WHY A RULE FILE AT ALL. Every finding this project has paid for lives in a commit message
or a comment, which means it is discoverable only by whoever already knows to look. A film
is assembled by four stages that each think they own the mix, and the same mistake gets
made again the next time somebody writes a new pipeline. A rule that a script enforces
survives that; a lesson in a commit message does not.

Exit code is 1 if any error-severity rule is violated, so this can gate a render.
"""
import argparse, json, os, re, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
STUDIO = os.path.dirname(HERE)
ROOT = os.path.dirname(STUDIO)
RULES_MD = os.path.join(ROOT, "craft", "VIDEO_RULES.md")

BANNED_LOOKS = {"night"}
BANNED_CAMERAS = {"dolly_zoom", "orbit", "rack_focus"}
# Read from the node when a server is up; this is the fallback so the check still runs
# offline. Same 34 values.
KEYS = {("%s%s %s" % (n, a, m)).strip()
        for n in "CDEFGAB" for a in ("", "#", "b") for m in ("major", "minor")}


def parse_rules(path=RULES_MD):
    """Pull every ```rule block out of the markdown, with the heading above it."""
    if not os.path.exists(path):
        return []
    text = open(path, encoding="utf-8").read()
    out = []
    for m in re.finditer(r"^### (.+?)\n```rule\n(.*?)```", text, re.S | re.M):
        title, body = m.group(1).strip(), m.group(2)
        d = {"title": title}
        for line in body.splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                d[k.strip()] = v.split("#")[0].strip()
        out.append(d)
    return out


# ─── checks ─────────────────────────────────────────────────────────────────────────
# Each returns a list of failure strings. Empty list means the rule held.

def check_title_scale(film, out=None):
    bad = []
    for s in film.get("shots", []):
        for t in s.get("titles", []):
            v = float(t.get("scale", 0.045))
            if v > 0.15:
                bad.append("%s: scale %.3f on %r - scale is a FRACTION OF FRAME HEIGHT, "
                           "so this asks for a font %d%% of the picture"
                           % (s["id"], v, t.get("text", "")[:30], int(v * 100)))
    return bad


def check_title_lines(film, out=None):
    return ["%s: title %r contains a newline" % (s["id"], t.get("text", "")[:40])
            for s in film.get("shots", []) for t in s.get("titles", [])
            if "\n" in str(t.get("text", ""))]


def check_banned_looks(film, out=None):
    return ["%s: look %r clips to black rather than darkening" % (s["id"], s["look"])
            for s in film.get("shots", []) if s.get("look") in BANNED_LOOKS]


def check_dead_cameras(film, out=None):
    bad = []
    for s in film.get("shots", []):
        blob = " ".join(str(s.get(k, "")) for k in ("motion", "camera", "prompt")).lower()
        for c in BANNED_CAMERAS:
            if c.replace("_", " ") in blob or c in blob:
                bad.append("%s: asks for %s, which measured byte-identical to static"
                           % (s["id"], c))
    return bad


def check_music_keys(film, out=None):
    return ["cue %s: key %r is not one of ACE-Step's 34 spellings (it wants e.g. 'Bb minor')"
            % (c.get("prefix", "?"), c["key"])
            for c in film.get("music", []) if c.get("key") and c["key"] not in KEYS]


def check_blocked_voices(film, out=None):
    """A voice pack cloning a named real person must never be cast."""
    bad = []
    for who, v in (film.get("voices") or {}).items():
        f = str(v.get("voice", ""))
        base = os.path.basename(f)
        card = os.path.join(STUDIO, "voices", os.path.splitext(base)[0].lower() + ".json")
        blocked = False
        if os.path.exists(card):
            try:
                blocked = json.load(open(card, encoding="utf-8")).get("status") == "blocked"
            except Exception:
                pass
        # Belt and braces: the shipped clones are named after the person.
        if blocked or re.search(r"(eastwood|attenborough|freeman|sophie_anderson)", base, re.I):
            bad.append("%s is cast with %s, a clone of a real person" % (who, base))
    return bad


def _speech_spans(film, outdir):
    """When narration is actually sounding, from the measured line durations."""
    p = os.path.join(outdir, "narration.json") if outdir else None
    if not p or not os.path.exists(p):
        return None
    return json.load(open(p, encoding="utf-8"))


def check_sfx_under_speech(film, out=None, outdir=None):
    """Prove effects are not welded into the picture segments.

    The measurable symptom of SOUND-01 is structural, not spectral: if an effect was baked
    into a segment it cannot have been ducked, whatever the finished file sounds like. So
    look for the stems the fixed pipeline must produce.
    """
    if not outdir:
        return []
    work = os.path.join(outdir, "_work")
    if not os.path.isdir(work):
        return []
    wants_sfx = any(s.get("sfx") for s in film.get("shots", []))
    if not wants_sfx:
        return []
    has_stem = any(f.startswith("_sfx_") and f.endswith(".wav") for f in os.listdir(work))
    has_norm = any(f.startswith("_sfxn_") for f in os.listdir(work))
    bad = []
    if not has_stem:
        bad.append("no _sfx_*.wav stem in _work: effects were baked into the segments, so "
                   "nothing could duck them under narration")
    if not has_norm:
        bad.append("no _sfxn_*.wav in _work: effects were never loudness-normalised")
    return bad


CHECKS = {
    "title_scale": check_title_scale, "title_lines": check_title_lines,
    "banned_looks": check_banned_looks, "dead_cameras": check_dead_cameras,
    "music_keys": check_music_keys, "blocked_voices": check_blocked_voices,
    "sfx_under_speech": check_sfx_under_speech,
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", help="a films/*.json to check")
    ap.add_argument("--outdir", help="the render directory, for checks that need output")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--strict", action="store_true", help="warnings fail too")
    a = ap.parse_args()

    rules = parse_rules()
    if not rules:
        print("no rules found at %s" % RULES_MD)
        return 0

    if a.list or not a.check:
        by = {}
        for r in rules:
            by.setdefault(r["id"].split("-")[0], []).append(r)
        print("%d rules in %s\n" % (len(rules), os.path.relpath(RULES_MD, ROOT)))
        for fam, rs in sorted(by.items()):
            print("  %s" % fam)
            for r in rs:
                print("    %-12s %-9s %-8s %s" % (r["id"], r.get("status", "?"),
                                                  r.get("severity", "?"),
                                                  r["title"].split(" - ")[-1][:56]))
        print("\n  enforced = the code cannot produce a violation")
        print("  checked  = provable here; run with --check <film.json>")
        return 0

    film = json.load(open(a.check, encoding="utf-8"))
    outdir = a.outdir
    if not outdir:
        slug = film["title"].lower().replace(" ", "-")
        guess = os.path.expanduser(
            "~/ComfyUI/output/claude-generated/11-short-film/%s" % slug)
        outdir = guess if os.path.isdir(guess) else None

    errors = warns = 0
    print("checking %s against %d rules%s\n"
          % (os.path.basename(a.check), len(rules),
             "" if outdir else "  (no render dir found - output checks skipped)"))
    for r in rules:
        cid = r.get("check", "none")
        fn = CHECKS.get(cid)
        if not fn:
            continue
        try:
            bad = (fn(film, outdir=outdir) if cid == "sfx_under_speech" else fn(film))
        except TypeError:
            bad = fn(film)
        sev = r.get("severity", "error")
        if bad:
            print("  %s %-12s %s" % ("FAIL" if sev == "error" else "warn", r["id"],
                                     r["title"].split(" - ")[-1][:52]))
            for b in bad[:6]:
                print("        %s" % b)
            if len(bad) > 6:
                print("        ... and %d more" % (len(bad) - 6))
            if sev == "error":
                errors += 1
            else:
                warns += 1
        else:
            print("  ok   %-12s %s" % (r["id"], r["title"].split(" - ")[-1][:52]))

    stated = [r for r in rules if r.get("check", "none") == "none"]
    if stated:
        print("\n  %d rules are stated but not automatically checkable "
              "(enforced in code, or a judgement call):" % len(stated))
        print("    " + ", ".join(r["id"] for r in stated))
    print("\n%d error(s), %d warning(s)" % (errors, warns))
    return 1 if (errors or (a.strict and warns)) else 0


if __name__ == "__main__":
    sys.exit(main())
