#!/usr/bin/env python3
"""studio/_tools/review_clock.py - is the playbook's periodic review due, and what should it look at?

The playbook's first section is a clock: the date the studio last checked for new models, nodes
and workflows, and how many days may pass before it must check again. This reads that clock,
says whether the review is due, lists the things a review must look at - and, because the most
expensive misses this project has made were assets sitting on disk that nothing called (the
ref2va weights, twenty gigabytes, unnoticed for weeks), it also lists every model file under
ComfyUI/models that no workflow in workflows/ references.

    python3 studio/_tools/review_clock.py            # status, orphans, checklist; exit 3 if due
    python3 studio/_tools/review_clock.py --checked  # stamp today's date into the playbook
    python3 studio/_tools/review_clock.py --quiet    # one line, for a session-start hook

CLAUDE.md asks the agent to run this at the start of any session that touches generation. The
studio docs page shows the same status. Updating the stamp is a deliberate act: it means the
checklist below was actually walked, not that the tool was run.
"""
import argparse
import datetime as dt
import glob
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PLAYBOOK = os.path.join(ROOT, "studio", "LTX_PLAYBOOK.md")
COMFY = os.path.expanduser("~/ComfyUI")
MODEL_DIRS = ("diffusion_models", "checkpoints", "loras", "text_encoders", "vae", "upscale_models",
              "clip_vision", "controlnet", "audio_encoders")

STAMP_RE = re.compile(r"^last_checked:\s*(\d{4}-\d{2}-\d{2})\s*$", re.M)
CADENCE_RE = re.compile(r"^cadence_days:\s*(\d+)\s*$", re.M)

CHECKLIST = [
    "New or updated weights for the engines in use: LTX, Wan, MiniMax H3, HunyuanVideo, Qwen-Image / "
    "Qwen-Edit, Flux, the SDXL finetunes, ACE-Step, the TTS voices, the upscalers. HF, the ComfyUI "
    "release notes, the model cards.",
    "ComfyUI itself and its comfy_extras: a `git log` since last_checked, and any new node class "
    "(the ref2va node was in comfy_extras for weeks before anyone looked).",
    "Orphans: every model file below that no workflow references. Wire it, measure it, or say why not "
    "- in the playbook, with a date.",
    "The paid engines' capability and price (Seedance, Nano Banana, Veo, Kling): does the hybrid "
    "decision in §96 still hold? The rule is measured, not assumed - hybrid_frame_test.py --frame.",
    "Re-run the standard battery on anything new before it enters the pipeline: identity clock, cut "
    "and timecode test, sound presence, the LTX_SAFE-style envelope, frame count through the finish.",
    "Update docs/WHERE-WE-STAND.md's table and §96 of the playbook; run method_check.py; then stamp "
    "the clock with --checked.",
]


def read_clock(text):
    m = STAMP_RE.search(text)
    c = CADENCE_RE.search(text)
    if not m or not c:
        return None, None
    return dt.date.fromisoformat(m.group(1)), int(c.group(1))


# Only things that BUILD graphs or CAST a model count as a reference. A tool that merely talks
# about a model (the downloads page, the collector's notes, the intake ladder) would otherwise hide
# an orphan behind its own description of it - which is exactly how ref2va stayed invisible.
GRAPH_BUILDERS = ("studio/_tools/film_routes.py", "studio/compose.py", "studio/_tools/post.py",
                  "studio/_tools/face_detail.py", "studio/_tools/pack_lora.py",
                  "studio/_tools/train_pack_lora.py", "studio/_tools/lora_train.py",
                  "studio/_tools/lora_train_sdxl.py", "studio/_tools/lora_photoreal.py",
                  "studio/_tools/engine_ab.py", "studio/_tools/multishot.py",
                  "studio/_tools/dress_keep_face.py", "studio/_tools/polish.py")


def workflow_text():
    out = []
    pats = [os.path.join(ROOT, "workflows", "*.json"),
            os.path.join(ROOT, "studio", "loras", "*.json"),            # the LoRA library cards
            os.path.join(ROOT, "studio", "foundry", "*", "*", "asset.json")]  # a pack's adopted face
    for pat in pats:
        for p in glob.glob(pat):
            try:
                out.append(open(p, encoding="utf-8").read())
            except OSError:
                pass
    for rel in GRAPH_BUILDERS:
        p = os.path.join(ROOT, rel)
        if os.path.exists(p):
            try:
                out.append(open(p, encoding="utf-8").read())
            except OSError:
                pass
    return "\n".join(out)


def orphans():
    """model files nothing in workflows/ or the studio's own tools names"""
    text = workflow_text()
    found = []
    for d in MODEL_DIRS:
        base = os.path.join(COMFY, "models", d)
        if not os.path.isdir(base):
            continue
        for fn in sorted(os.listdir(base)):
            if fn.startswith("put_") or fn.startswith("."):
                continue
            p = os.path.join(base, fn)
            if os.path.isdir(p):
                # a directory model (TTS engines, some VAEs): referenced by directory name
                if fn not in text:
                    found.append((d, fn, sum(os.path.getsize(os.path.join(r, f)) for r, _, fs in os.walk(p) for f in fs)))
                continue
            stem = os.path.splitext(fn)[0]
            if fn not in text and stem not in text:
                found.append((d, fn, os.path.getsize(p)))
    return found


def status(text, today=None):
    today = today or dt.date.today()
    last, cadence = read_clock(text)
    if last is None:
        return {"ok": False, "reason": "no clock in the playbook", "due": True}
    days = (today - last).days
    return {"ok": True, "last_checked": last.isoformat(), "cadence_days": cadence, "days_since": days,
            "due": days >= cadence, "days_over": max(0, days - cadence), "days_left": max(0, cadence - days)}


def stamp(text, today=None):
    today = (today or dt.date.today()).isoformat()
    new, n = STAMP_RE.subn("last_checked: %s" % today, text, count=1)
    if n != 1:
        raise SystemExit("no last_checked line to update")
    return new


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--checked", action="store_true", help="the checklist was walked today; stamp it")
    ap.add_argument("--quiet", action="store_true")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    text = open(PLAYBOOK, encoding="utf-8").read()
    if a.checked:
        open(PLAYBOOK, "w", encoding="utf-8", newline="\n").write(stamp(text))
        print("playbook clock stamped %s" % dt.date.today().isoformat())
        return
    st = status(text)
    orph = orphans()
    st["orphans"] = [{"dir": d, "file": f, "gb": round(b / 2 ** 30, 2)} for d, f, b in orph]
    if a.json:
        print(json.dumps(st, indent=1))
        sys.exit(3 if st["due"] else 0)
    if not st["ok"]:
        print("REVIEW CLOCK: %s - add §0 to the playbook" % st["reason"])
        sys.exit(3)
    line = ("PLAYBOOK REVIEW DUE - %d day(s) over (last checked %s, cadence %d days)"
            % (st["days_over"], st["last_checked"], st["cadence_days"])) if st["due"] else \
           ("playbook review in %d day(s) (last checked %s, cadence %d days)"
            % (st["days_left"], st["last_checked"], st["cadence_days"]))
    print(line)
    if a.quiet:
        sys.exit(3 if st["due"] else 0)
    print("\n%d model file(s) on disk that no workflow or tool names:" % len(orph))
    for d, f, b in orph:
        print("  %-18s %-64s %6.2f GB" % (d, f[:64], b / 2 ** 30))
    print("\nthe review, in order:")
    for i, item in enumerate(CHECKLIST, 1):
        print("  %d. %s" % (i, item))
    print("\nwhen it is done: python3 studio/_tools/review_clock.py --checked")
    sys.exit(3 if st["due"] else 0)


if __name__ == "__main__":
    main()
