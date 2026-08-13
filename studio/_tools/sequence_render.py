#!/usr/bin/env python3
"""studio/_tools/sequence_render.py - cast a sequence card with our own people and cut it.

    python3 studio/_tools/sequence_render.py upside_down_exit \\
        --character YANSHU --style wuxia_live --place bamboo_grove
    python3 studio/_tools/sequence_render.py upside_down_exit --dry
    python3 studio/_tools/sequence_render.py upside_down_exit --beats 2,4,5

A sequence card is timing and intent with empty slots. This fills the slots, renders one
clip per beat AT THE BEAT'S OWN LENGTH, and concatenates them in order. The output is our
characters in our style, moving to a rhythm measured from a reference - which is the part
that is craft rather than content.

WHY EACH BEAT IS ITS OWN CLIP, TRIMMED TO LENGTH. The whole finding of the card is that six
clips of 0.8-1.5s read as one impossible action. Generating a single long take would throw
away the technique and hit LTX's drift ceiling as well. Short beats are the point, not a
compromise.

THE FRAMING IS REPLACED, NOT APPENDED. roll.py already learned this the hard way: a
character card carries its own framing token, so prefixing another produced "close-up,
terra ... , close-up". The beat's framing is substituted over the card's using roll's own
FRAMING_RE, so one layer wins instead of both being present.

COMPOSITION IS roll.roll_image's JOB, NOT A NEW ONE. Pinning style/character/place through
roll means engine routing, LoRA base-model checks, negative-prompt character counts and the
vista/framing rules all still apply. Building a job by hand here would quietly lose every
one of those.
"""
import argparse, json, os, subprocess, sys, time

TOOLS = os.path.dirname(os.path.abspath(__file__))
STUDIO = os.path.dirname(TOOLS)
ROOT = os.path.dirname(STUDIO)
CARDS = os.path.join(STUDIO, "sequences")
OUT = os.path.join(STUDIO, "samples", "sequences")

for p in (TOOLS, os.path.join(ROOT, "scripts"), STUDIO):
    if p not in sys.path:
        sys.path.insert(0, p)
os.environ.setdefault("COMFY_HOST", "127.0.0.1:8188")


def load(sid):
    p = os.path.join(CARDS, sid + ".json")
    if not os.path.isfile(p):
        return None
    return json.load(open(p, encoding="utf-8"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("sequence")
    ap.add_argument("--character")
    ap.add_argument("--style")
    ap.add_argument("--place")
    ap.add_argument("--seed", type=int, default=4242)
    ap.add_argument("--beats", help="render only these beat numbers, e.g. 1,4,5")
    ap.add_argument("--dry", action="store_true", help="show the plan, render nothing")
    a = ap.parse_args()

    card = load(a.sequence)
    if not card:
        print("  no such sequence: %s" % a.sequence)
        print("  have: %s" % ", ".join(sorted(
            os.path.basename(f)[:-5] for f in os.listdir(CARDS) if f.endswith(".json"))))
        return 1

    import random
    import roll
    import render_job

    libs = roll.load_libs()
    want = None
    if a.beats:
        want = {int(x) for x in a.beats.replace(" ", "").split(",") if x}

    opt = {}
    if a.style:
        opt["style"] = a.style
    if a.character:
        opt["character"] = a.character
        opt["cast_rate"] = 1.0
    if a.place:
        opt["place"] = a.place
    # Snapshot AFTER every option is set. Captured before --place, base_opt would drop the
    # place on every beat - the run would still succeed and quietly ignore an argument the
    # caller passed, which is the worst kind of wrong.
    base_opt = dict(opt)

    run_dir = os.path.join(OUT, "%s_%s" % (a.sequence, time.strftime("%m%d_%H%M")))
    jobs = []
    for b in card["beats"]:
        if want and b["n"] not in want:
            continue
        rng = random.Random(a.seed + b["n"] * 101)
        # SUBJECT MODE DECIDES WHETHER THE FACE IS IN THE PROMPT AT ALL.
        #
        # Measured the hard way: the first render of this card came back as six near
        # identical medium shots of a woman facing camera. Beat 1 asked for an insert of a
        # hand on the floor and beat 4 for a figure receding down a corridor; neither
        # happened. The character card's prose is a PARAGRAPH OF FACE NOUNS - oval face,
        # narrow jaw, high cheekbones, dark brown eyes - and "wide, low angle" is one weak
        # token against it. The model renders nouns, so it drew the nouns.
        #
        # So an insert beat does not get the character at all, and a figure beat gets the
        # framing and the action without the face description. This is the same rule the
        # roller already learned as "the subject is decided first".
        mode = (b.get("subject_mode") or "face").lower()
        opt = dict(base_opt)
        if mode == "insert":
            opt.pop("character", None)
            opt.pop("cast_rate", None)
            opt["no_characters"] = True
        try:
            job = roll.roll_video(rng, libs, opt)
        except SystemExit as e:
            print("  beat %d: %s" % (b["n"], e))
            return 1

        # The beat's own length. LTX renders in frames, and roll already caps duration -
        # this asks for exactly what the grammar measured, floored at a sane minimum.
        job["seconds"] = max(1.0, round(b["seconds"], 2))
        job["seed"] = a.seed + b["n"] * 101
        job["id"] = "%s_b%02d" % (a.seed, b["n"])

        # FIGURE MODE: keep who it is, drop the face inventory.
        #
        # A character card's prose is "<face description>, wearing <clothes>". At a wide
        # shot the face is a dozen pixels, so every one of those face nouns is competing
        # for a frame that cannot show them - and winning, which is why the first render
        # gave six close-ups. Here the face clause is replaced by a short body phrase and
        # the wardrobe is kept, because the wardrobe IS the identity at distance.
        if mode == "figure" and a.character:
            try:
                cc = json.load(open(os.path.join(STUDIO, "characters",
                                                 a.character + ".json"), encoding="utf-8"))
                full = cc.get("prose") or ""
                if full and full[:40] in job["prompt"]:
                    head, sep, wear = full.partition(", wearing ")
                    short = head.split(",")[0].strip()
                    compact = (short + (", wearing " + wear if sep else "")).strip()
                    job["prompt"] = job["prompt"].replace(full, compact, 1)
            except Exception:
                pass          # a missing card must not stop the sequence

        # Framing: REPLACE the token the cards already carry, never add a second one.
        if b.get("framing"):
            f = b["framing"].split(",")[0].strip()
            m = roll.FRAMING_RE.search(job["prompt"])
            if m:
                job["prompt"] = job["prompt"][:m.start()] + f + job["prompt"][m.end():]
            else:
                job["prompt"] = job["prompt"] + " " + f.capitalize() + "."
        # What the person is DOING comes from the beat, appended as its own sentence so it
        # reads as action rather than as another style clause.
        if b.get("subject"):
            if mode == "insert":
                # The beat IS the subject. Lead with it so it is the first noun the model
                # meets, rather than a clause tacked onto a landscape.
                job["prompt"] = b["subject"] + ". " + job["prompt"]
            else:
                job["prompt"] = job["prompt"].rstrip(". ") + ". " + b["subject"] + "."
        if b.get("camera") and job.get("camera"):
            job["camera_note"] = b["camera"]
        job["_beat"] = b
        jobs.append(job)

    print("  %s - %d beat(s), %.1fs total"
          % (card["id"], len(jobs), sum(j["seconds"] for j in jobs)))
    for j in jobs:
        b = j["_beat"]
        print("   %2d  %4.2fs  %-8s %-20s %s"
              % (b["n"], j["seconds"], (b.get("subject_mode") or "face"),
                 (b.get("framing") or "-")[:20], (b.get("subject") or "")[:38]))
        print("       %s" % j["prompt"][:150])
    if a.dry:
        print("\n  --dry: nothing rendered.")
        return 0

    os.makedirs(run_dir, exist_ok=True)
    made = []
    for j in jobs:
        b = j["_beat"]
        t = time.time()
        try:
            got = render_job.render_video(j, run_dir)
        except Exception as e:                                     # noqa: BLE001
            print("   beat %d FAILED: %s: %s" % (b["n"], type(e).__name__, str(e)[:90]))
            continue
        if not got or not os.path.isfile(got):
            print("   beat %d produced nothing" % b["n"])
            continue
        # Trim to the beat's length. LTX renders in whole frames at a fixed rate, so what
        # comes back is close to the ask, not equal to it - and the rhythm is the point.
        dst = os.path.join(run_dir, "beat%02d.mp4" % b["n"])
        r = subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", got,
                            "-t", "%.2f" % j["seconds"], "-c", "copy", dst],
                           capture_output=True, text=True)
        if r.returncode != 0 or not os.path.isfile(dst):
            dst = got
        made.append(dst)
        print("   beat %-2d %5.1fs  %s" % (b["n"], time.time() - t, os.path.basename(dst)))

    if not made:
        print("\n  nothing rendered - not writing a cut.")
        return 1
    if len(made) < len(jobs):
        # Say it. A sequence missing beats is a different sequence, and a silent partial
        # assembly is exactly the kind of success-shaped failure this project keeps finding.
        print("\n  WARNING: %d of %d beats are missing from the cut."
              % (len(jobs) - len(made), len(jobs)))

    lst = os.path.join(run_dir, "_list.txt")
    with open(lst, "w", encoding="utf-8") as f:
        for m in made:
            f.write("file '%s'\n" % os.path.abspath(m).replace("\\", "/"))
    final = os.path.join(run_dir, "%s.mp4" % card["id"])
    r = subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0",
                        "-i", lst, "-c", "copy", final], capture_output=True, text=True)
    if r.returncode != 0:
        print("  concat failed: %s" % r.stderr.strip()[-200:])
        return 1
    d = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "csv=p=0", final], capture_output=True, text=True)
    print("\n  %s  (%.1fs from %d beats)" % (final, float(d.stdout.strip() or 0), len(made)))
    print("  Watch it. The card's claim is that this rhythm reads as one action - only "
          "looking can say whether it does with our cast in it.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
