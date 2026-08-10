"""Routes behind /voices - hear every voice, and add a new one.

WHY A PAGE AT ALL. Casting is the one decision in this app that cannot be made from text.
A card can tell you a voice sits at 115 Hz with a 6.9-semitone range and 4.5 onsets per
second, and that is genuinely useful, but nobody picks a narrator that way. They listen.
So the page's job is to put every voice one click from playing, on the same line, saying
the same words.

REFERENCE LENGTH IS THE ONE MEASURED PREDICTOR HERE. The cloning docs ask for 24-30
seconds. Auditioned across the library, the voices that held up - carter, frank, maya,
samuel - are all over 24s, and the ones that sound synthetic are the short ones. The
narrator carrying all three episodes of THE SALT ROAD is a 10.4s sample. So the page shows
reference length next to every voice and says plainly when it is short, because that is
actionable in a way that a subjective note is not.
"""
import base64, glob, json, os, re, subprocess, sys, threading, time

TOOLS = os.path.dirname(os.path.abspath(__file__))
STUDIO = os.path.dirname(TOOLS)
ROOT = os.path.dirname(STUDIO)
sys.path.insert(0, TOOLS)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
os.environ.setdefault("COMFY_HOST", "127.0.0.1:8188")

CARDS = os.path.join(STUDIO, "voices")
DEMOS = os.path.join(STUDIO, "samples", "audition")
GOOD_REF = 24.0          # seconds; the cloning docs ask for 24-30

JOBS = {}
_LOCK = threading.Lock()

DEFAULT_LINE = ("Every campaign begins the same way. Four people who should not trust "
                "each other, one road, and a rumour worth more than it ought to be.")


def _voices_dir():
    from epic import COMFY
    return os.path.join(COMFY, "custom_nodes", "TTS-Audio-Suite", "voices_examples")


def _dur(p):
    try:
        out = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                              "format=duration", "-of", "csv=p=0", p],
                             capture_output=True, text=True).stdout.strip()
        return round(float(out), 1)
    except Exception:
        return 0.0


def listing():
    out = []
    vd = _voices_dir()
    for f in sorted(glob.glob(os.path.join(CARDS, "*.json"))):
        try:
            c = json.load(open(f, encoding="utf-8"))
        except Exception:
            continue
        vid = c.get("id") or os.path.basename(f)[:-5]
        ref = os.path.join(vd, str(c.get("file") or "").replace("voices_examples/", ""))
        reflen = _dur(ref) if os.path.isfile(ref) else 0.0
        tag = vid.replace("/", "_")
        demo = None
        for cand in (os.path.join(DEMOS, "%s.mp3" % str(c.get("file", ""))
                                  .replace("voices_examples/", "")
                                  .replace("/", "_").replace(".wav", "")),
                     os.path.join(DEMOS, "%s.mp3" % tag)):
            if os.path.isfile(cand):
                demo = "/api/voice/demo/" + os.path.basename(cand)
                break
        blocked = c.get("status") == "blocked"
        out.append({
            "id": vid, "name": c.get("name") or vid,
            "status": c.get("status") or "ready",
            "blocked": blocked,
            # Blocked packs clone named real people. They are listed so the roster is
            # honest about what is on disk, but never made playable or castable.
            "castable": not blocked and c.get("status") != "unavailable",
            "engine": c.get("engine") or "",
            "sounds_like": c.get("sounds_like") or "",
            "casts_well_as": c.get("casts_well_as") or "",
            "avoid_for": c.get("avoid_for") or "",
            "note": c.get("note") or "",
            "ref_seconds": reflen,
            "ref_thin": bool(reflen and reflen < GOOD_REF),
            "ref_url": (None if blocked else
                        ("/api/voice/ref/%s" % vid if os.path.isfile(ref) else None)),
            "demo_url": None if blocked else demo,
        })
    out.sort(key=lambda v: (v["blocked"], not v["castable"], -v["ref_seconds"]))
    return {"voices": out,
            "castable": sum(1 for v in out if v["castable"]),
            "good_reference": sum(1 for v in out if v["castable"] and not v["ref_thin"]),
            "good_reference_seconds": GOOD_REF,
            "line": DEFAULT_LINE}, 200


def ref_file(vid):
    p = os.path.join(CARDS, "%s.json" % re.sub(r"[^A-Za-z0-9._-]", "", vid or ""))
    if not os.path.isfile(p):
        return None
    c = json.load(open(p, encoding="utf-8"))
    if c.get("status") == "blocked":
        return None                      # never serve a cloned real person's reference
    f = os.path.join(_voices_dir(), str(c.get("file") or "")
                     .replace("voices_examples/", ""))
    return f if os.path.isfile(f) else None


def demo_file(name):
    if not re.match(r"^[A-Za-z0-9._-]+\.mp3$", name or ""):
        return None
    p = os.path.join(DEMOS, name)
    return p if os.path.isfile(p) else None


def _speak(job, vid, line):
    from comfy import run, set_path
    from epic import load_wf, ensure_local, HOST
    try:
        c = json.load(open(os.path.join(CARDS, "%s.json" % vid), encoding="utf-8"))
        if c.get("status") == "blocked":
            raise RuntimeError("this pack clones a real person and is never cast")
        os.makedirs(DEMOS, exist_ok=True)
        wf = load_wf("17_higgs_v3_voice.json")
        set_path(wf, "30.inputs.text", line)
        set_path(wf, "30.inputs.narrator_voice", c["file"])
        set_path(wf, "30.inputs.seed", 4242)
        set_path(wf, "40.inputs.filename_prefix", "claude-generated/audition/%s" % vid)
        _, outs = run(HOST, wf, quiet=True)
        if not outs:
            raise RuntimeError("no output")
        ensure_local(outs[0], os.path.join(DEMOS, "%s.mp3" % vid), required=False)
    except Exception as e:
        with _LOCK:
            JOBS[job]["error"] = str(e)[:200]
    with _LOCK:
        JOBS[job]["state"] = "done"


def demo(data):
    vid = re.sub(r"[^A-Za-z0-9._-]", "", str(data.get("id") or ""))
    if not os.path.isfile(os.path.join(CARDS, "%s.json" % vid)):
        return {"error": "no such voice"}, 404
    job = "v%d" % (len(JOBS) + 1)
    with _LOCK:
        JOBS[job] = {"state": "running", "error": None, "id": vid}
    threading.Thread(target=_speak, daemon=True,
                     args=(job, vid, (data.get("line") or DEFAULT_LINE)[:400])).start()
    return {"ok": True, "job": job}, 200


def job_status(job):
    with _LOCK:
        j = JOBS.get(job)
    return (j or {"error": "no such job"}), (200 if j else 404)


def add(data):
    """Add a voice from an uploaded reference recording.

    The card is written with what can be MEASURED - duration, and whether it clears the
    24s the docs ask for. The qualitative description is left to whoever adds it, because
    inventing a `sounds_like` the tool did not actually measure is how a library fills up
    with confident nonsense.
    """
    name = (data.get("name") or "").strip()
    if not name:
        return {"error": "the voice needs a name"}, 400
    vid = re.sub(r"[^a-z0-9_]", "", name.lower().replace(" ", "_").replace("-", "_"))
    if not vid:
        return {"error": "that name has no usable characters"}, 400
    if os.path.exists(os.path.join(CARDS, "%s.json" % vid)):
        return {"error": "a voice called %r already exists" % vid}, 409
    blob = str(data.get("data") or "")
    if "," in blob:
        blob = blob.split(",", 1)[1]
    try:
        raw = base64.b64decode(blob)
    except Exception as e:
        return {"error": "could not decode the audio: %s" % e}, 400
    if not raw:
        return {"error": "empty file"}, 400

    dest_dir = os.path.join(_voices_dir(), "custom")
    os.makedirs(dest_dir, exist_ok=True)
    wav = os.path.join(dest_dir, "%s.wav" % vid)
    tmp = wav + ".upload"
    with open(tmp, "wb") as f:
        f.write(raw)
    # Normalise to a plain 44.1k mono wav whatever came in. A reference in a container the
    # TTS node cannot open fails at cast time, which is far away from here.
    r = subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", tmp,
                        "-ac", "1", "-ar", "44100", wav], capture_output=True, text=True)
    os.remove(tmp)
    if not os.path.isfile(wav):
        return {"error": "could not read that as audio: %s"
                         % (r.stderr.strip()[:160] or "unknown")}, 400
    secs = _dur(wav)
    card = {
        "id": vid, "name": name, "file": "voices_examples/custom/%s.wav" % vid,
        "engine": "higgs_v3", "status": "ready",
        "ref_seconds": secs,
        "sounds_like": (data.get("sounds_like") or "").strip(),
        "casts_well_as": (data.get("casts_well_as") or "").strip(),
        "avoid_for": "",
        "added": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "note": ("Added from an uploaded recording. %s"
                 % ("Reference is %.1fs, which clears the 24-30s the cloning docs ask for."
                    % secs if secs >= GOOD_REF else
                    "Reference is only %.1fs; the cloning docs ask for 24-30s, and every "
                    "voice in this library that sounds synthetic is a short one. Expect "
                    "less stable cloning until it is replaced with a longer sample."
                    % secs)),
    }
    with open(os.path.join(CARDS, "%s.json" % vid), "w", encoding="utf-8") as f:
        json.dump(card, f, indent=1, ensure_ascii=False)
        f.write("\n")
    return {"ok": True, "id": vid, "ref_seconds": secs,
            "thin": secs < GOOD_REF}, 200
