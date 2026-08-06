"""Routes behind /generate - start, stop and watch an unattended generation run.

Kept out of serve.py because it owns a CHILD PROCESS, which nothing else in the app does.
The page can start a run, ask how it is going and ask it to stop; it cannot do anything the
shell script would not also do, and every limit below is enforced here as well as in the
script, so a crafted POST is no more dangerous than a typo at the prompt.

WHY A BUDGET IS NON-NEGOTIABLE. An earlier generation loop on this box ran 17h22m unattended
because --loop had no stopping condition, holding the GPU and starving three other jobs. The
page cannot express "forever", MAX_MINUTES caps what it can ask for, and the run stops
itself even if this server is killed.
"""
import json, os, re, signal, subprocess, time

TOOLS = os.path.dirname(os.path.abspath(__file__))
STUDIO = os.path.dirname(TOOLS)
ROOT = os.path.dirname(STUDIO)
SCRIPT = os.path.join(ROOT, "bin", "generate.sh")
RUNDIR = os.path.join(ROOT, ".generate")
PIDFILE = os.path.join(RUNDIR, "generate.pid")
STOPFILE = os.path.join(RUNDIR, "STOP")
LOG = os.path.join(RUNDIR, "generate.log")
CONSOLE = os.path.join(RUNDIR, "console.log")
STARTED = os.path.join(RUNDIR, "started.json")

TYPES = ("image", "video", "music", "voice", "sfx")
MAX_MINUTES = 12 * 60          # the page's slider tops out at 12h; enforced here too
WEIGHT_RE = re.compile(r"^[a-z]+=\d{1,2}(,[a-z]+=\d{1,2})*$")


def _pid():
    try:
        p = int(open(PIDFILE).read().strip())
    except Exception:
        return None
    try:
        os.kill(p, 0)
    except OSError:
        return None
    return p


def _tail(path, n=40):
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            return "".join(f.readlines()[-n:])
    except Exception:
        return ""


def status():
    """What the page polls. Counts are read back off the console the script prints, so they
    describe what actually happened rather than what was asked for."""
    pid = _pid()
    kept, rejected, failed = {}, {}, {}
    for ln in _tail(CONSOLE, 400).splitlines():
        parts = ln.split()
        if len(parts) < 3 or ":" not in parts[0]:
            continue
        t, verdict = parts[1], parts[2]
        bucket = {"ok": kept, "rejected": rejected, "failed": failed}.get(verdict)
        if bucket is not None and t in TYPES:
            bucket[t] = bucket.get(t, 0) + 1
    left = None
    try:
        s = json.load(open(STARTED, encoding="utf-8"))
        if pid:
            left = max(0, int((s["deadline"] - time.time()) / 60))
    except Exception:
        s = {}
    return {
        "running": bool(pid), "pid": pid,
        "kept": kept, "rejected": rejected, "failed": failed,
        "minutes_left": left,
        "weights": s.get("weights"), "started_at": s.get("started_at"),
        "stopping": os.path.exists(STOPFILE) and bool(pid),
        "log": _tail(CONSOLE, 40) or _tail(LOG, 20) or "idle.",
    }


def _weights(data):
    raw = str(data.get("weights") or "").strip()
    if not raw:
        return "image=6,video=2,music=1,voice=1,sfx=1", None
    if not WEIGHT_RE.match(raw):
        return None, "weights must look like image=6,video=2 - letters, digits and commas"
    total = 0
    for pair in raw.split(","):
        k, v = pair.split("=")
        if k not in TYPES:
            return None, "unknown type %r - expected one of %s" % (k, ", ".join(TYPES))
        total += int(v)
    if total <= 0:
        return None, "every weight is zero, so there is nothing to draw"
    return raw, None


def _comfy_up():
    import urllib.request
    host = os.environ.get("COMFY_HOST", "127.0.0.1:8188")
    try:
        urllib.request.urlopen("http://%s/system_stats" % host, timeout=5).read(1)
        return True, host
    except Exception:
        return False, host


def start(data):
    if _pid():
        return {"error": "a run is already going - stop it first"}, 409
    if not os.path.exists(SCRIPT):
        return {"error": "bin/generate.sh is missing"}, 500
    # Ask before starting. ComfyUI was down during testing and a four-minute run produced
    # over three hundred instant failures, reporting nothing more useful than "failed" on
    # every line. One question up front turns that into a sentence the page can show.
    up, host = _comfy_up()
    if not up:
        return {"error": "ComfyUI is not answering on %s, so nothing can be rendered. "
                         "Start it and try again." % host}, 503

    weights, err = _weights(data)
    if err:
        return {"error": err}, 400

    minutes = data.get("minutes")
    if minutes is None and data.get("hours") is not None:
        try:
            minutes = round(float(data["hours"]) * 60)
        except (TypeError, ValueError):
            return {"error": "hours must be a number"}, 400
    try:
        minutes = int(minutes)
    except (TypeError, ValueError):
        return {"error": "a time budget is required - pass hours or minutes"}, 400
    if minutes < 1:
        return {"error": "a time budget is required - pass hours or minutes"}, 400
    if minutes > MAX_MINUTES:
        # Refuse rather than clamp. Silently shortening a run someone asked for is how you
        # end up not trusting the number on the screen.
        return {"error": "%d minutes is over the %d hour ceiling this page will start. "
                         "Run bin/generate.sh from a shell if you genuinely want longer."
                         % (minutes, MAX_MINUTES // 60)}, 400

    cmd = [SCRIPT, "--minutes", str(minutes), "--weights", weights]
    seed = str(data.get("seed") or "").strip()
    if seed:
        if not seed.isdigit():
            return {"error": "seed must be a whole number, or blank for a clock seed"}, 400
        cmd += ["--seed", seed]

    os.makedirs(RUNDIR, exist_ok=True)
    try:
        os.remove(STOPFILE)
    except OSError:
        pass
    out = open(CONSOLE, "w", encoding="utf-8")
    # start_new_session detaches it from this server's process group, so restarting or
    # killing the studio does not take a running generation down with it. The script owns
    # its own deadline, so an orphan still stops on time.
    p = subprocess.Popen(cmd, stdout=out, stderr=subprocess.STDOUT,
                         cwd=ROOT, start_new_session=True)
    json.dump({"deadline": time.time() + minutes * 60, "minutes": minutes,
               "weights": weights, "seed": seed or None,
               "started_at": time.strftime("%Y-%m-%dT%H:%M:%S")},
              open(STARTED, "w", encoding="utf-8"))
    time.sleep(0.6)                       # let it write its pid file, or die visibly
    if p.poll() not in (None, 0):
        return {"error": "it exited immediately: " + (_tail(CONSOLE, 6) or "no output")}, 500
    return {"ok": True, "minutes": minutes, "weights": weights}, 200


def stop(_data=None):
    """Ask for a stop; do not kill. The script checks the flag between jobs, so the render
    in flight finishes and its artifact is kept instead of being thrown away half-written."""
    os.makedirs(RUNDIR, exist_ok=True)
    open(STOPFILE, "w").close()
    pid = _pid()
    return {"ok": True, "pid": pid,
            "note": ("it will finish the job it is on and exit" if pid
                     else "nothing was running; the flag is set anyway")}, 200


def preview(data):
    """Twelve rolls, rendering nothing. The honest way to see what a mix will produce."""
    weights, err = _weights(data)
    if err:
        return {"error": err}, 400
    p = subprocess.run([SCRIPT, "--minutes", "5", "--dry", "--weights", weights],
                       capture_output=True, text=True, cwd=ROOT, timeout=90)
    return {"text": (p.stdout or p.stderr or "").strip()}, 200


def space():
    """What the libraries can draw from, counted from the cards rather than hardcoded."""
    p = subprocess.run(["python3", os.path.join(TOOLS, "roll.py"), "--explain"],
                       capture_output=True, text=True, cwd=ROOT, timeout=60)
    return {"text": (p.stdout or p.stderr or "").strip()}, 200
