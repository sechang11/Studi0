#!/usr/bin/env python3
"""The one generator (ARCHITECTURE Phase 3). Five modes, one CLI, one API route.

    python3 studio/_tools/generate.py roll --hours 2 --weights image=6,video=2
    python3 studio/_tools/generate.py roll --stop | --status
    python3 studio/_tools/generate.py scene --character TERRA --place night_market
    python3 studio/_tools/generate.py grow --kind places --id night_market --n 6
    python3 studio/_tools/generate.py isolate --what characters --per 2 --hours 1
    python3 studio/_tools/generate.py beats --seq window_escape --character TERRA

WHY ONE GENERATOR. "Make something" was answered by nine paths - generate.sh, gallery_gen,
gallery_fill, make-samples.sh, flux2_gallery, isolation_run, sequence_render, the grow
route hand-building a command inside serve.py, and the film scripts - and a fix to one
never reached the others. The modes are the real distinctions:

    roll     time-budgeted variety - draw from the measured libraries until the clock says
             stop (the ported body of bin/generate.sh; the .sh is now a thin wrapper)
    scene    one composed combination, rendered now, result JSON on stdout (the wizard's
             unit, and the caller's building block for anything larger)
    grow     more of ONE card, isolation-style (what /api/library/grow spawns)
    isolate  clean plates per card across a whole kind (delegates to isolation_run)
    beats    a sequence card cast with our subjects (delegates to sequence_render)

isolate and beats delegate by subprocess rather than absorption: each owns real policy
(NEUTRAL pool choice, subject modes) that belongs to its file, and a delegation that
re-implements its callee is how the nine paths happened in the first place.

THE DEADLINE IS STILL THE FIRST FEATURE. A gallery_gen --loop once ran 17h22m unattended,
holding the GPU and starving three jobs, because --loop had no stopping condition. roll
refuses to start without a budget, writes a PID file, honours a STOP file between jobs,
and never begins a job it cannot finish inside the budget. scene/grow/beats are bounded by
their own shape (one card, one sequence, N frames).

CONSOLE FORMAT IS AN INTERFACE. generate_routes.status() counts kept/rejected/failed by
parsing `HH:MM:SS  type verdict ...` lines off the console. The roll port keeps the .sh
line formats byte-for-byte; changing them silently zeroes the page's scoreboard.
"""
import argparse
import json
import os
import random
import signal
import subprocess
import sys
import time
import urllib.request

TOOLS = os.path.dirname(os.path.abspath(__file__))
STUDIO = os.path.dirname(TOOLS)
ROOT = os.path.dirname(STUDIO)
RUNDIR = os.path.join(ROOT, ".generate")
PIDFILE = os.path.join(RUNDIR, "generate.pid")
STOPFILE = os.path.join(RUNDIR, "STOP")
LOGFILE = os.path.join(RUNDIR, "generate.log")
DEFAULT_OUT = os.path.join(STUDIO, "samples", "rolled")
TYPES = ("image", "video", "music", "voice", "sfx")
HOST = os.environ.get("COMFY_HOST", "127.0.0.1:8188")


def comfy_up():
    try:
        urllib.request.urlopen("http://%s/system_stats" % HOST, timeout=5).read(1)
        return True
    except Exception:
        return False


def run_pid():
    try:
        p = int(open(PIDFILE).read().strip())
        os.kill(p, 0)
        return p
    except Exception:
        return None


# ---------------------------------------------------------------- mode: roll -----------
def mode_roll(argv):
    ap = argparse.ArgumentParser(
        prog="generate.py roll",
        description="Time-budgeted variety from the measured libraries, then STOP.")
    ap.add_argument("--hours", type=float)
    ap.add_argument("--minutes", type=float)
    ap.add_argument("--weights", default="image=6,video=2,music=1,voice=1,sfx=1")
    ap.add_argument("--seed", type=int)
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--options", help="JSON file mapping a type to extra roll.py flags")
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--stop", action="store_true")
    ap.add_argument("--status", action="store_true")
    a = ap.parse_args(argv)

    if a.stop:
        os.makedirs(RUNDIR, exist_ok=True)
        open(STOPFILE, "w").close()
        p = run_pid()
        print("asked pid %d to stop after its current job." % p if p
              else "no run in progress; STOP flag set anyway.")
        return 0
    if a.status:
        p = run_pid()
        if p:
            print("running, pid %d" % p)
            try:
                sys.stdout.write("".join(
                    open(LOGFILE, encoding="utf-8", errors="replace").readlines()[-3:]))
            except OSError:
                pass
        else:
            print("not running")
        return 0

    # A budget is mandatory. This is the whole lesson of the 17-hour runaway.
    budget = int((a.hours or 0) * 3600 + (a.minutes or 0) * 60)
    if budget <= 0:
        print("refusing to start without a time budget. pass --hours N or --minutes N.",
              file=sys.stderr)
        print("  (a previous unbounded run held this GPU for 17h22m and starved three "
              "jobs.)", file=sys.stderr)
        return 2

    bag = []
    for pair in a.weights.split(","):
        k, _, v = pair.partition("=")
        if k not in TYPES:
            print("unknown type: %s" % k, file=sys.stderr)
            return 2
        try:
            bag += [k] * int(v)
        except ValueError:
            print("bad weight: %s" % pair, file=sys.stderr)
            return 2
    if not bag:
        print("weights produced an empty bag", file=sys.stderr)
        return 2

    # PREFLIGHT. Without it the loop spins against a dead renderer - a 4-minute run once
    # produced 300+ instant failures at ~10/s. Ask once, up front, and say so.
    if not a.dry and not comfy_up():
        print("ComfyUI is not answering on %s - nothing can be rendered." % HOST,
              file=sys.stderr)
        print("  start it first, then run this again.", file=sys.stderr)
        return 4

    os.makedirs(RUNDIR, exist_ok=True)
    os.makedirs(a.out, exist_ok=True)
    if run_pid():
        print("already running as pid %d. use --status or --stop." % run_pid(),
              file=sys.stderr)
        return 3
    try:
        os.remove(STOPFILE)
    except OSError:
        pass
    open(PIDFILE, "w").write(str(os.getpid()))

    started = time.time()
    deadline = started + budget
    done, rejected, failed = {}, {}, {}
    log = open(LOGFILE, "a", encoding="utf-8")

    def say(line):
        print(line, flush=True)
        log.write(line + "\n")
        log.flush()

    def finish(code=0):
        elapsed = int(time.time() - started)
        print("")
        print("── stopped after %d min ──────────────────────────" % (elapsed // 60))
        for k, v in done.items():
            print("  %-6s kept %s" % (k, v))
        for k, v in rejected.items():
            print("  %-6s rejected %s" % (k, v))
        for k, v in failed.items():
            print("  %-6s failed %s" % (k, v))
        print("  output: %s" % a.out)
        print("  log:    %s" % LOGFILE)
        try:
            os.remove(PIDFILE)
        except OSError:
            pass
        sys.exit(code)

    signal.signal(signal.SIGINT, lambda *_: finish())
    signal.signal(signal.SIGTERM, lambda *_: finish())

    print("generating for %d min into %s" % (budget // 60, a.out))
    print("  weights : %s" % a.weights)
    print("  stop    : ./bin/generate.sh --stop     (or Ctrl-C)")
    print("  watch   : ./bin/generate.sh --status   (or tail -f %s)" % LOGFILE)
    print("  seed    : %s" % ("%d (reproducible)" % a.seed if a.seed is not None
                              else "from the clock, so a re-run differs"))
    print("", flush=True)

    opts = {}
    if a.options and os.path.isfile(a.options):
        try:
            opts = json.load(open(a.options, encoding="utf-8"))
        except Exception:
            say("could not read --options file %s; ignoring it" % a.options)

    rng = random.Random(a.seed)
    # A renderer can also die MID-RUN, which the preflight cannot catch. Consecutive
    # failures back off, and a long enough streak gives up rather than burning the rest of
    # the budget discovering the same thing over and over.
    streak, max_streak = 0, 8
    n = 0
    while True:
        if os.path.exists(STOPFILE):
            print("STOP requested.")
            finish()
        left = int(deadline - time.time())
        # Never start a job that cannot finish. Video is the long pole at roughly 90s.
        if left <= 30:
            print("budget spent.")
            finish()
        typ = rng.choice(bag)
        if typ == "video" and left < 120:
            typ = "image"
        n += 1

        cmd = [sys.executable, os.path.join(TOOLS, "roll.py"), typ]
        if a.seed is not None:
            cmd += ["--seed", str(a.seed + n)]
        cmd += [str(x) for x in (opts.get(typ) or [])]
        r = subprocess.run(cmd, capture_output=True, text=True)
        job = (r.stdout or "").strip()
        log.write(r.stderr or "")
        if not job:
            # roll.py refuses a constraint that matches nothing, and that refusal must be
            # loud. Silently falling back to full-random would give you a folder of
            # perfectly good output that is not what you asked for, with no way to tell.
            say("cannot roll a %s with the options given:" % typ)
            for ln in (r.stderr or "").splitlines()[:2]:
                say("    " + ln)
            finish(2)

        if a.dry:
            d = json.loads(job)
            print("  %-6s %s" % (d["domain"],
                                 (d.get("prompt") or d.get("line") or d.get("cue")
                                  or "")[:110]))
            if n >= 12:
                print("(dry run: 12 shown)")
                finish()
            continue

        r = subprocess.run([sys.executable, os.path.join(TOOLS, "render_job.py"),
                            "--out", a.out], input=job, capture_output=True, text=True)
        log.write(r.stderr or "")
        res = (r.stdout or "").strip()
        stamp = time.strftime("%H:%M:%S")
        if not res:
            failed[typ] = failed.get(typ, 0) + 1
            say("%s  %-6s failed    (no result)" % (stamp, typ))
            streak += 1
        else:
            log.write(res + "\n")
            # ONLY THE LAST LINE IS THE RESULT: run() prints its own progress line first,
            # and parsing the pair once counted five successes as failures.
            try:
                verdict = json.loads(res.splitlines()[-1])
            except Exception:
                verdict = {}
            secs = verdict.get("seconds", 0)
            if verdict.get("ok"):
                streak = 0
                done[typ] = done.get(typ, 0) + 1
                say("%s  %-6s ok        %5ss   kept %s   %dm left"
                    % (stamp, typ, secs, done[typ], left // 60))
                continue
            if str(verdict.get("why") or ""):
                # A rejection is the gate working, not a fault.
                streak = 0
                rejected[typ] = rejected.get(typ, 0) + 1
                say("%s  %-6s rejected  %5ss   %s"
                    % (stamp, typ, secs, verdict.get("why", "")))
                continue
            failed[typ] = failed.get(typ, 0) + 1
            say("%s  %-6s failed    %s"
                % (stamp, typ, str(verdict.get("error", ""))[:90]))
            streak += 1

        if streak >= max_streak:
            print("")
            print("%d jobs failed in a row - something is wrong with the renderer, not "
                  "with the rolls. Giving up rather than spending the rest of the budget "
                  "finding out again." % max_streak)
            print("  last errors:")
            try:
                for ln in open(LOGFILE, encoding="utf-8",
                               errors="replace").readlines()[-3:]:
                    print("    " + ln.rstrip())
            except OSError:
                pass
            finish(5)
        if streak:
            nap = 2 ** min(streak, 5)
            print("  (failure %d of %d - waiting %ds)" % (streak, max_streak, nap))
            time.sleep(nap)


# ---------------------------------------------------------------- mode: scene ----------
def mode_scene(argv):
    ap = argparse.ArgumentParser(
        prog="generate.py scene",
        description="One composed combination, rendered now. Result JSON on stdout - the "
                    "wizard's unit, and the building block for anything larger. Any "
                    "roll.py constraint flag passes through.")
    ap.add_argument("type", nargs="?", default="image", choices=TYPES)
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--n", type=int, default=1,
                    help="renders of the same combination (seed advances each time)")
    a, passthru = ap.parse_known_args(argv)

    if not comfy_up():
        print(json.dumps({"ok": False,
                          "error": "ComfyUI is not answering on %s" % HOST}))
        return 4
    os.makedirs(a.out, exist_ok=True)
    worst = 0
    for i in range(max(1, min(12, a.n))):
        r = subprocess.run([sys.executable, os.path.join(TOOLS, "roll.py"), a.type]
                           + passthru, capture_output=True, text=True)
        job = (r.stdout or "").strip()
        if not job:
            print(json.dumps({"ok": False, "error":
                              (r.stderr or "roll refused the constraints").strip()[:300]}))
            return 2
        r = subprocess.run([sys.executable, os.path.join(TOOLS, "render_job.py"),
                            "--out", a.out], input=job, capture_output=True, text=True)
        res = (r.stdout or "").strip()
        print(res.splitlines()[-1] if res
              else json.dumps({"ok": False,
                               "error": (r.stderr or "no result").strip()[-300:]}))
        if not res:
            worst = 1
    return worst


# ---------------------------------------------------------------- mode: grow ------------
def mode_grow(argv):
    ap = argparse.ArgumentParser(
        prog="generate.py grow",
        description="More of ONE card, isolation-style: the exact run the library's "
                    "'make more' button starts. Bounded by --n, not by a clock.")
    ap.add_argument("--kind", required=True,
                    choices=("places", "characters", "emotions", "styles"))
    ap.add_argument("--id", required=True)
    ap.add_argument("--n", type=int, default=4)
    a = ap.parse_args(argv)
    n = max(1, min(12, a.n))
    return subprocess.call([sys.executable, "-u",
                            os.path.join(TOOLS, "isolation_run.py"),
                            "--what", a.kind, "--only", a.id, "--per", str(n),
                            "--fresh", "--hours", "0.5"])


# ---------------------------------------------------------------- delegations ----------
def mode_isolate(argv):
    """Clean plates per card across a kind. isolation_run owns the policy (NEUTRAL pool,
    faces for emotions, freshness); this is a door, not a re-implementation."""
    return subprocess.call([sys.executable, "-u",
                            os.path.join(TOOLS, "isolation_run.py")] + argv)


def mode_beats(argv):
    """A sequence card cast with our subjects. sequence_render owns subject modes."""
    return subprocess.call([sys.executable, "-u",
                            os.path.join(TOOLS, "sequence_render.py")] + argv)


MODES = {"roll": mode_roll, "scene": mode_scene, "grow": mode_grow,
         "isolate": mode_isolate, "beats": mode_beats}


def main():
    ap = argparse.ArgumentParser(
        description="The one generator: roll | scene | grow | isolate | beats.")
    ap.add_argument("mode", nargs="?", choices=sorted(MODES))
    a, rest = ap.parse_known_args()
    if not a.mode:
        ap.print_help()
        return 2
    return MODES[a.mode](rest)


if __name__ == "__main__":
    sys.exit(main())
