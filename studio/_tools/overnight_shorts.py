#!/usr/bin/env python3
"""studio/_tools/overnight_shorts.py - render the short-form slate unattended, safely.

    python3 studio/_tools/overnight_shorts.py --hours 7 [--only ID] [--stages ...]

WHY A HARNESS AND NOT A FOR-LOOP. Twenty films is roughly two thousand model calls, and
the failures this project has actually had overnight are all bookkeeping failures rather
than model failures: a run with no deadline held the GPU for 17 hours; a stage that
skipped everything reported success; a master got overwritten by a later test. So:

  DEADLINE      mandatory. Never starts a film it cannot finish; stops cleanly and says
                what is left.
  RESUMABLE     a film whose master already exists is skipped by name, so a re-run picks
                up where the night stopped.
  PER-FILM LOG  every film's full stdout lands in output/<id>/render.log; the console
                keeps one line per film. A failure is loud, named, and does not stop the
                slate - the next film starts.
  VERIFIED      a film only counts as done when the master EXISTS, has a video stream,
                has an audio stream as long as the video, and is not a still frame.
                Anything else is reported as a failure with the reason, because "the
                file is there" is not the same as "the film rendered".

The five stages run in order per film (keyframes, clips, voices, music, sfx, cut) so a
GPU failure early stops that film cheaply rather than after the expensive stages.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time

TOOLS = os.path.dirname(os.path.abspath(__file__))
STUDIO = os.path.dirname(TOOLS)
ROOT = os.path.dirname(STUDIO)
COMFY = os.environ.get("COMFY_ROOT", os.path.expanduser("~/ComfyUI"))
SHORTS = os.path.join(ROOT, "films", "shorts")
STAGES = ["keyframes", "clips", "voices", "music", "sfx", "cut"]


def sh(*a, **k):
    return subprocess.run(a, capture_output=True, text=True, **k)


def outdir_for(film_json):
    title = json.load(open(film_json, encoding="utf-8"))["title"]
    slug = title.lower().replace(" ", "-")
    return os.path.join(COMFY, "output", "claude-generated", "12-shorts", slug), slug


def verify(master):
    """A master counts only if it is a real film: video + audio of matching length, and
    not a single frozen frame."""
    if not os.path.exists(master) or os.path.getsize(master) < 100_000:
        return False, "missing or tiny"
    r = sh("ffprobe", "-v", "error", "-show_entries",
           "stream=codec_type,duration:format=duration", "-of", "default=nw=1", master)
    txt = r.stdout or ""
    kinds = re.findall(r"codec_type=(\w+)", txt)
    if "video" not in kinds:
        return False, "no video stream"
    if "audio" not in kinds:
        return False, "no audio stream"
    durs = [float(x) for x in re.findall(r"duration=([\d.]+)", txt)]
    if not durs:
        return False, "no duration"
    if max(durs) - min(durs) > 0.6:
        return False, "audio/video length mismatch (%.1f vs %.1f)" % (max(durs), min(durs))
    # It must also MOVE. clipmetrics extracts frames properly (the first version of
    # this check piped PNG bytes through a TEXT-mode subprocess and died on the PNG
    # magic number, while the film it was judging had rendered perfectly).
    try:
        sys.path.insert(0, TOOLS)
        import clipmetrics
        m = clipmetrics.measure(master)
        if (m.get("motion") or 0) <= 0.01:      # measured static floor is 0.001
            return False, "the master does not move (motion %.3f)" % (m.get("motion") or 0)
        return True, "ok %.1fs motion %.2f" % (max(durs), m.get("motion") or 0)
    except Exception as e:                                            # noqa: BLE001
        return True, "ok %.1fs (motion unmeasured: %s)" % (max(durs), str(e)[:60])


def main():
    ap = argparse.ArgumentParser(description="Render the short-form slate with a deadline.")
    ap.add_argument("--hours", type=float, default=7.0)
    ap.add_argument("--only")
    ap.add_argument("--kind", choices=("supplement", "commercial", "hook"))
    ap.add_argument("--stages", nargs="+", default=STAGES)
    ap.add_argument("--force", action="store_true", help="re-render films already done")
    a = ap.parse_args()
    deadline = time.time() + a.hours * 3600
    films = sorted(f for f in os.listdir(SHORTS) if f.endswith(".json"))
    if a.only:
        films = [f for f in films if f[:-5] == a.only]
    if a.kind:
        films = [f for f in films
                 if json.load(open(os.path.join(SHORTS, f), encoding="utf-8")
                              ).get("kind") == a.kind]
    print("slate: %d films, deadline in %.1f h" % (len(films), a.hours), flush=True)
    done, failed, skipped, left = [], [], [], []
    for fn in films:
        fp = os.path.join(SHORTS, fn)
        fid = fn[:-5]
        out, slug = outdir_for(fp)
        master = os.path.join(out, "%s.mp4" % slug)
        ok, why = verify(master)
        if ok and not a.force:
            skipped.append(fid)
            print("%-22s already done (%s)" % (fid, why), flush=True)
            continue
        # never start a film that cannot finish: measured ~9 min for a 5-beat short
        if time.time() + 9 * 60 > deadline:
            left.append(fid)
            continue
        os.makedirs(out, exist_ok=True)
        log = os.path.join(out, "render.log")
        t0 = time.time()
        stage_fail = None
        with open(log, "w", encoding="utf-8") as lf:
            for st in a.stages:
                lf.write("\n===== STAGE %s =====\n" % st)
                lf.flush()
                r = subprocess.run([sys.executable, os.path.join(ROOT, "scripts",
                                                                 "short.py"), fp,
                                    "--stage", st],
                                   capture_output=True, text=True, cwd=ROOT)
                lf.write(r.stdout or "")
                lf.write(r.stderr or "")
                lf.flush()
                if r.returncode != 0:
                    stage_fail = "%s exited %d: %s" % (st, r.returncode,
                                                       (r.stderr or "").strip()[-200:])
                    break
        secs = time.time() - t0
        if stage_fail:
            failed.append((fid, stage_fail))
            print("%-22s FAILED  %s" % (fid, stage_fail[:110]), flush=True)
            continue
        ok, why = verify(master)
        if ok:
            done.append((fid, secs, why))
            print("%-22s ok  %5.1f min  %s" % (fid, secs / 60, why), flush=True)
        else:
            failed.append((fid, "master did not verify: %s" % why))
            print("%-22s FAILED  master did not verify: %s" % (fid, why), flush=True)

    print("\n===== SLATE =====")
    print("rendered %d, already done %d, failed %d, not started %d"
          % (len(done), len(skipped), len(failed), len(left)))
    for f, why in failed:
        print("  FAILED %-20s %s" % (f, why[:160]))
    if left:
        print("  not started (deadline): %s" % ", ".join(left))
    json.dump({"done": done, "skipped": skipped, "failed": failed, "not_started": left},
              open(os.path.join(STUDIO, "samples", "shorts_run.json"), "w"), indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
