"""Routes behind character creation from an image.

Renders on a worker thread like the story editor does, because the pipeline is a caption
plus a redraw and takes about twenty seconds - long enough that a synchronous request would
look like a hung page.
"""
import base64, json, os, re, sys, threading, time

TOOLS = os.path.dirname(os.path.abspath(__file__))
STUDIO = os.path.dirname(TOOLS)
ROOT = os.path.dirname(STUDIO)
sys.path.insert(0, TOOLS)

JOBS = {}
_LOCK = threading.Lock()

# Where an uploaded starting image lands. Kept inside the repo rather than in ComfyUI's
# input dir so it is obvious what was uploaded by a person and what the app generated.
UPLOADS = os.path.join(STUDIO, "uploads")


def sources():
    """Images already on the box that can be used as a starting point.

    Browsing beats typing a path: most of the good starting points are things this app
    already made, and nobody remembers where ComfyUI puts them.
    """
    import glob
    out = []
    roots = [
        (os.path.join(STUDIO, "uploads"), "uploaded", "/api/character/src/uploads/%s"),
        (os.path.join(STUDIO, "samples", "rolled", "image"), "rolled",
         "/samples/rolled/image/%s"),
        (os.path.expanduser("~/ComfyUI/input"), "comfy input",
         "/api/character/src/comfy/%s"),
    ]
    for d, label, url in roots:
        if not os.path.isdir(d):
            continue
        files = [f for f in sorted(os.listdir(d))
                 if f.lower().endswith((".png", ".jpg", ".jpeg", ".webp"))
                 and not f.startswith("_")]
        for f in files[:120]:
            out.append({"name": f, "where": label, "url": url % f,
                        "path": os.path.join(d, f)})
    return {"sources": out, "count": len(out)}, 200


def src_file(kind, name):
    if not re.match(r"^[A-Za-z0-9._-]+$", name or ""):
        return None
    base = {"uploads": UPLOADS,
            "comfy": os.path.expanduser("~/ComfyUI/input")}.get(kind)
    if not base:
        return None
    p = os.path.join(base, name)
    return p if os.path.isfile(p) else None


def upload(data):
    """Accept a base64 image from the page. Small and simple beats multipart here."""
    name = re.sub(r"[^A-Za-z0-9._-]", "_", str(data.get("name") or "upload.png"))
    blob = str(data.get("data") or "")
    if "," in blob:
        blob = blob.split(",", 1)[1]
    try:
        raw = base64.b64decode(blob)
    except Exception as e:
        return {"error": "could not decode the image: %s" % e}, 400
    if not raw:
        return {"error": "empty image"}, 400
    os.makedirs(UPLOADS, exist_ok=True)
    p = os.path.join(UPLOADS, name)
    with open(p, "wb") as f:
        f.write(raw)
    return {"ok": True, "name": name, "path": p,
            "url": "/api/character/src/uploads/%s" % name}, 200


def _build(job, path, name, style, voice, consent, seed):
    import character_new as CN
    try:
        class A:
            pass
        a = A()
        # A missing style must fall back to the house style, not to None - the redraw
        # prompt interpolates it, and "Redraw this as a None" is a real prompt.
        a.image, a.name, a.voice = path, name, voice
        a.style = style or CN.HOUSE_STYLE
        a.desc, a.seed, a.consent = "", seed, consent
        a.caption_only, a.force = False, True
        CN.build(a)
        with _LOCK:
            JOBS[job]["id"] = re.sub(r"[^A-Z0-9_]", "", name.upper().replace(" ", "_"))
    except BaseException as e:
        with _LOCK:
            JOBS[job]["error"] = str(e)[:250]
    with _LOCK:
        JOBS[job]["state"] = "done"
        JOBS[job]["done"] = 1


def create(data):
    path = data.get("path") or ""
    if not os.path.isfile(path):
        return {"error": "pick a starting image first"}, 400
    name = (data.get("name") or "").strip()
    if not name:
        return {"error": "the character needs a name"}, 400
    job = "c%d" % (len(JOBS) + 1)
    with _LOCK:
        JOBS[job] = {"state": "running", "want": 1, "done": 0, "error": None,
                     "name": name}
    threading.Thread(target=_build, daemon=True,
                     args=(job, path, name, data.get("style") or None,
                           data.get("voice") or "", bool(data.get("consent")),
                           int(data.get("seed") or 4242))).start()
    return {"ok": True, "job": job}, 200


def job_status(job):
    with _LOCK:
        j = JOBS.get(job)
    return (j or {"error": "no such job"}), (200 if j else 404)


def house_style():
    import character_new as CN
    return {"style": CN.HOUSE_STYLE}, 200


# ── the picture suite ────────────────────────────────────────────────────────────────

def _suite(job, cid, which, wear, styles, views):
    import subprocess
    args = [sys.executable, os.path.join(TOOLS, "character_suite.py"), cid]
    if which == "identity":
        args += ["--identity", "--views", str(views)]
    elif which == "presentation":
        args += ["--presentation"]
    if wear:
        args += ["--wear", wear]
    if styles:
        args += ["--styles", styles]
    r = subprocess.run(args, cwd=ROOT, capture_output=True, text=True)
    with _LOCK:
        if r.returncode:
            JOBS[job]["error"] = (r.stderr.strip()[-250:] or r.stdout.strip()[-250:]
                                  or "suite failed")
        JOBS[job]["log"] = r.stdout.strip()[-900:]
        JOBS[job]["state"] = "done"


def suite(data):
    """Build a character's picture suite. Identity and presentation are separate jobs on
    purpose - they want opposite things, and running presentation before identity is
    locked produces a grid that has to be thrown away when the LoRA lands."""
    cid = re.sub(r"[^A-Z0-9_]", "", str(data.get("id") or "").upper())
    if not os.path.isfile(os.path.join(STUDIO, "characters", "%s.json" % cid)):
        return {"error": "no such character"}, 404
    which = data.get("which") or "both"
    job = "s%d" % (len(JOBS) + 1)
    with _LOCK:
        JOBS[job] = {"state": "running", "error": None, "id": cid, "which": which}
    threading.Thread(target=_suite, daemon=True,
                     args=(job, cid, which, data.get("wear") or "",
                           data.get("styles") or "",
                           int(data.get("views") or 16))).start()
    return {"ok": True, "job": job}, 200


def suite_state(cid):
    """What has already been built, so the page can show it rather than re-render it."""
    cid = re.sub(r"[^A-Z0-9_]", "", str(cid or "").upper())
    d = os.path.join(STUDIO, "samples", "cast", cid)
    man = os.path.join(d, "suite.json")
    out = {"id": cid, "identity": 0, "presentation": 0, "sheets": []}
    if os.path.isfile(man):
        try:
            m = json.load(open(man, encoding="utf-8"))
            out["identity"] = len(m.get("identity") or [])
            out["presentation"] = len(m.get("presentation") or [])
        except Exception:
            pass
    for kind in ("identity", "presentation"):
        f = os.path.join(d, "CONTACT_%s.jpg" % kind)
        if os.path.isfile(f):
            out["sheets"].append({"kind": kind,
                                  "url": "/api/character/sheet/%s/%s" % (cid, kind)})
    return out, 200


def sheet_file(cid, kind):
    cid = re.sub(r"[^A-Z0-9_]", "", str(cid or "").upper())
    if kind not in ("identity", "presentation"):
        return None
    p = os.path.join(STUDIO, "samples", "cast", cid, "CONTACT_%s.jpg" % kind)
    return p if os.path.isfile(p) else None
