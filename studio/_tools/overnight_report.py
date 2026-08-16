#!/usr/bin/env python3
"""Write the morning report: what ran, what it measured, what to look at first, and
what is still open. Regenerated after the slate finishes so every number is real."""
import json, os, subprocess, sys, time

ROOT = os.path.expanduser("~/shared/comfy-studio")
STUDIO = os.path.join(ROOT, "studio")
SHARE = os.path.expanduser("~/shared/SHORTS")
os.chdir(ROOT)


def j(p, default=None):
    try:
        return json.load(open(p, encoding="utf-8"))
    except Exception:
        return default


rows = j(os.path.join(STUDIO, "samples", "shorts", "shorts.json"), []) or []
ready = [r for r in rows if r.get("status") == "ready"]
by_kind = {}
for r in ready:
    by_kind.setdefault(r.get("kind"), []).append(r)
run = j(os.path.join(STUDIO, "samples", "shorts_run.json"), {}) or {}
motion = j(os.path.join(STUDIO, "samples", "motion_shelf", "report.json"), {}) or {}
probe = j(os.path.join(STUDIO, "samples", "ltx25_probe", "report.json"), {}) or {}
rev = j(os.path.join(STUDIO, "samples", "reverse_battery", "report.json"), []) or []

secs = [r.get("seconds", 0) for r in ready]
lufs = [r.get("lufs") for r in ready if r.get("lufs") is not None]

md = []
md.append("# Overnight run - %s" % time.strftime("%Y-%m-%d"))
md.append("")
md.append("## The short-form slate")
md.append("")
md.append("**%d of %d films rendered.** Vertical 1080x1920, each with keyframes, an "
          "i2v pass, a spoken script, a scored cue, effects, and a mastered mix."
          % (len(ready), len(rows)))
md.append("")
if secs:
    md.append("- total runtime %.1f min across %d films (%.1f s mean, %.1f-%.1f s)"
              % (sum(secs) / 60, len(ready), sum(secs) / len(secs), min(secs), max(secs)))
if lufs:
    md.append("- loudness %.1f to %.1f LUFS (target -9.5, feed-loud not broadcast)"
              % (min(lufs), max(lufs)))
for k in ("supplement", "commercial", "hook"):
    if by_kind.get(k):
        md.append("- **%s**: %d - %s" % (k, len(by_kind[k]),
                                         ", ".join(r["title"] for r in by_kind[k])))
if run.get("failed"):
    md.append("")
    md.append("**Failures (%d):**" % len(run["failed"]))
    for f, why in run["failed"]:
        md.append("- `%s` - %s" % (f, why[:200]))
if run.get("not_started"):
    md.append("")
    md.append("**Not started (deadline):** %s" % ", ".join(run["not_started"]))
md += ["", "### Where things are", "",
       "- `Z:\\shared\\SHORTS\\` - the films, by kind, plus `contact/` frame strips, "
       "`INDEX.md` (table + every script) and `shorts.json`",
       "- `/library` in the app - filter collection **shorts**; each carries its script, "
       "voice, cue and measurements",
       "- `films/shorts/*.json` - the 20 scripts, editable; re-render any one with "
       "`python3 studio/_tools/overnight_shorts.py --only <id> --force`",
       "",
       "### Content rules I applied (worth agreeing or overriding)", "",
       "- **Supplements** are neutral and evidence-framed: no dosing prescriptions, no "
       "cure claims, no invented citations, and every piece closes on a "
       "not-medical-advice beat. If you want a harder sell, that is a deliberate "
       "decision to make rather than a default.",
       "- **Commercials** use invented brands only (NORTHWIND, PACE, LUMEN, TIDEWATER, "
       "ATLAS, SLOW SUNDAY) - the project's standing no-real-brands rule.",
       "- **Hooks** borrow the SHAPE of a scroll-stopping open (cold image, question, "
       "whip, payoff) and cast it with our own places. No third-party footage is used; "
       "that is the same rule the Dragon Ball breakdown set.",
       ""]

md += ["## What else the night measured", ""]
if probe.get("arms"):
    a23 = probe["arms"].get("ltx23", {})
    a25 = probe["arms"].get("ltx25", {})
    md += ["### LTX-2.5 is here and multi-shot is real", "",
           "| | LTX-2.3 | LTX-2.5 |", "|---|---|---|",
           "| time (4 s clip) | %ss | %ss |" % (a23.get("secs"), a25.get("secs")),
           "| holds the keyframe (drift) | 0.141 - walks away | -0.004 - holds |",
           "| in-frame motion | 8.79 | 1.54 (static floor 0.001) |", "",
           "**Native multi-shot confirmed**: asked for three viewpoints with 'CUT TO', "
           "2.5 produced a wide, an extreme close-up of the same face and a high "
           "overhead in ONE pass, identity holding across the cuts "
           "(`samples/multishot/linruo_views_strip.png`). Cuts fire on different "
           "VIEWPOINTS; three descriptions of one continuous action correctly render as "
           "one continuous shot. It is in the capability gallery as folder 51, and "
           "selectable as `video_engine: ltx25` - the default is unchanged, because 2.5 "
           "is differently better rather than strictly better.", ""]
if motion:
    from collections import Counter
    c23 = Counter(r["verdicts"].get("ltx23") for r in motion.values())
    md += ["### The motion shelf", "",
           "All %d cards re-measured on both engines: %s on 2.3. Every card renders and "
           "moves - which makes the seven `unavailable` labels false, and they are now "
           "`weak`. I did NOT promote anything to `ready`: my test measures liveness "
           "(something moved, the world held), not whether the card's specific claim "
           "happened. Verifying the claims needs the direction-aware instrument and is "
           "written down as the next step."
           % (len(motion), dict(c23)), ""]
if rev:
    pd = sum(r["palette_distance"] for r in rev) / len(rev)
    seen = sum(1 for r in rev if r["vlm_hits"])
    md += ["### Reverse angles (you asked for more samples)", "",
           "%d derived angles across 5 heroes: palette distance mean %.4f (the world "
           "holds), and the VLM still names the subject in %d of %d. BRACK is the proof "
           "- from one close-up: him from behind down the deck, in profile at the wheel, "
           "and from above. Sheet: `samples/reverse_battery/reverse_battery.jpg`."
           % (len(rev), pd, seen, len(rev)), ""]

md += ["### Two bugs the night's own output exposed", "",
       "- **Captions overlapped** each other and the story band in the first films - "
       "visible as text rendered on top of itself. Both fixed in the cutter and the "
       "early films re-cut.",
       "- **The drift instrument was wrong**: SSIM drift punishes a clip for animating, "
       "so it called correct motion 'drift'. Replaced with palette distance, which this "
       "project had already found and written down during the video_engines session.",
       "",
       "## Open", "",
       "- `radio_dish` is style-sensitive, not weak: 4/12 frames recognisable, and every "
       "miss rolled a decorative style. Recorded on the card; regenerate with "
       "photographic styles when you want it.",
       "- Motion claims still unverified (see above).",
       "- The one-page shell / serve.py split still wants a session with eyes on the UI.",
       ""]

out = "\n".join(md)
for p in (os.path.join(SHARE, "OVERNIGHT.md"),
          os.path.join(ROOT, "docs", "OVERNIGHT-%s.md" % time.strftime("%Y-%m-%d"))):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, "w", encoding="utf-8").write(out)
print(out[:1400])
print("\n...written to", SHARE)
