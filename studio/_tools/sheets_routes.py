"""Routes behind /sheets - one picture in, every angle out. studio/sheets.py does the work; this file
is the page's API, a job queue, and the bridges to the films and the Foundry.

GET  /api/sheets                  every sheet, newest first
GET  /api/sheets/one?id=          one sheet: each view, what it was asked, what the check measured
GET  /api/sheets/status           the running job, the queue, how the last job ended
GET  /api/sheets/estimate?kind=&item_type=&faces=&expressions=&times=&hd=   seconds for a new sheet
GET  /api/sheets/films            shot-script films a sheet can go to, with their cast and place
POST /api/sheets/new              {name, kind, subject, item_type, options, pictures:[{dataurl, role}], make}
POST /api/sheets/make             {id}                       make what it lacks, lay the sheet out
POST /api/sheets/redo             {id, views:[...]}          remake these on new seeds
POST /api/sheets/options          {id, options}              change what it includes, then make
POST /api/sheets/rename           {id, name}
POST /api/sheets/delete           {id}                       into studio/sheets/_trash; restore undoes it
POST /api/sheets/restore          {id}
POST /api/sheets/stop             {queue_id} | {all: true} | {} (the running job, after its current view)
POST /api/sheets/send             {id, film, target, view, new_id, role}   a view becomes a film's reference
POST /api/sheets/unsend           {id, at}                   undo that: the replaced picture comes back
POST /api/sheets/foundry          {id, style}                a Foundry asset whose pack is this sheet
POST /api/sheets/extra            {id, what: turntable | model}

One job runs at a time (one GPU); asking while one runs QUEUES it, the same contract as
shots_routes. The job table lives in a module kept in sys.modules, so serve.py reloading this file on
mtime does not orphan a running job.
"""
import base64
import importlib.util
import io
import json
import os
import re
import shutil
import sys
import threading
import time
import traceback
import types

TOOLS = os.path.dirname(os.path.abspath(__file__))
STUDIO = os.path.dirname(TOOLS)
ROOT = os.path.dirname(STUDIO)
for p in (TOOLS, STUDIO, os.path.join(ROOT, "scripts")):
    if p not in sys.path:
        sys.path.insert(0, p)

_STATE = sys.modules.get("_sheets_routes_state")
if _STATE is None:
    _STATE = types.ModuleType("_sheets_routes_state")
    _STATE.JOB, _STATE.LOCK, _STATE.QUEUE, _STATE.LAST, _STATE.SEQ = None, threading.Lock(), [], None, [0]
    sys.modules["_sheets_routes_state"] = _STATE

_ENG = {"mod": None, "mtime": None}
ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,60}$")
MAX_BYTES = 25 * 1024 * 1024


def E():
    """studio/sheets.py, loaded by path and reloaded when it changes."""
    p = os.path.join(STUDIO, "sheets.py")
    mt = os.path.getmtime(p)
    if _ENG["mod"] is None or _ENG["mtime"] != mt:
        spec = importlib.util.spec_from_file_location("studio_sheets", p)
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        _ENG.update(mod=m, mtime=mt)
    return _ENG["mod"]


def _media(sid, rel, stamp=None):
    p = os.path.join(E().sheet_dir(sid), rel)
    if not os.path.isfile(p):
        return None
    return "/sheets/media/%s/%s?v=%d" % (sid, rel, stamp or int(os.path.getmtime(p)))


# ─── reading ──────────────────────────────────────────────────────────────────────────────────

def _card(s):
    e = E()
    views = e.plan(s)
    done = [v for v in views if (s["views"].get(v["key"]) or {}).get("status") == "done"]
    thumb = None
    for key in ("turn_front", "angle_left"):
        if (s["views"].get(key) or {}).get("status") == "done":
            thumb = _media(s["id"], "_work/thumbs/%s.jpg" % key)
            break
    thumb = thumb or _media(s["id"], "_work/thumbs/base.jpg") or _media(s["id"], "_work/thumbs/source_1.jpg")
    return {"id": s["id"], "name": s["name"], "kind": s["kind"], "subject": s.get("subject"),
            "item_type": s.get("item_type"), "done": len(done), "planned": len(views),
            "flagged": sum(1 for v in done if s["views"][v["key"]].get("flag")),
            "thumb": thumb, "updated": s.get("updated"), "sheet": bool(s.get("sheet")),
            "elsewhere": _elsewhere(s["id"])}


def _elsewhere(sid):
    """True while another process (the command line) is making this sheet."""
    pid = E().locked_by(sid)
    return bool(pid and pid != os.getpid())


def listing():
    return {"sheets": [_card(s) for s in E().listing()], "job": status()[0]}, 200


def one(sid):
    e = E()
    try:
        s = e.load(sid)
    except KeyError as err:
        return {"error": str(err)}, 404
    views = []
    for v in e.plan(s):
        rec = s["views"].get(v["key"]) or {}
        at = rec.get("at")
        views.append({"key": v["key"], "group": v["group"], "group_title": e.GROUP_TITLES.get(v["group"], v["group"]),
                      "label": v["label"], "prompt": v["prompt"], "lora": bool(v["angles"]), "status": rec.get("status") or "todo",
                      "flag": rec.get("flag") or "", "check": rec.get("check") or {}, "seed": rec.get("seed"),
                      "tries": rec.get("tries", 0), "secs": rec.get("secs"),
                      "thumb": _media(sid, "_work/thumbs/%s.jpg" % v["key"], at),
                      "file": _media(sid, rec["file"], at) if rec.get("file") else None,
                      "hd": _media(sid, rec["hd"], at) if rec.get("hd") else None,
                      "hd_size": rec.get("hd_size")})
    srcs = [{"role": x["role"], "size": x.get("size"),
             "thumb": _media(sid, "_work/thumbs/source_%d.jpg" % (i + 1)), "file": _media(sid, x["file"])}
            for i, x in enumerate(s["sources"])]
    extras = {}
    for k, rec in (s.get("extras") or {}).items():
        extras[k] = dict(rec, url=_media(sid, rec["file"]) if rec.get("file") else None)
    return {"sheet": {"id": sid, "name": s["name"], "kind": s["kind"], "subject": s.get("subject"),
                      "item_type": s.get("item_type"), "options": s.get("options"), "created": s.get("created"),
                      "updated": s.get("updated"), "prep": s.get("prep"), "sent": s.get("sent") or [],
                      "foundry": s.get("foundry"), "elsewhere": _elsewhere(sid),
                      "base": _media(sid, "_work/thumbs/base.jpg"), "face": _media(sid, "_work/thumbs/face.jpg"),
                      "preview": _media(sid, "_work/sheet_preview.jpg"),
                      "full": _media(sid, "sheet.png") if s.get("sheet") else None,
                      "full_size": (s.get("sheet") or {}).get("size"),
                      "estimate": e.estimate(s), "extras": extras},
            "sources": srcs, "views": views,
            "times": [{"key": k, "label": e.TIMES[k][0]} for k in e.TIME_ORDER],
            "job": status()[0]}, 200


def estimate(q):
    e = E()
    kind = (q.get("kind") or ["character"])[0]
    it = (q.get("item_type") or ["object"])[0]
    o = {"faces": (q.get("faces") or ["1"])[0] == "1", "expressions": (q.get("expressions") or ["1"])[0] == "1",
         "times": [t for t in (q.get("times") or [""])[0].split(",") if t in e.TIMES],
         "hd": (q.get("hd") or ["x2"])[0]}
    fake = {"id": "x", "kind": kind if kind in e.KINDS else "character", "item_type": it, "subject": "",
            "options": o, "sources": [{"file": "", "role": "main"}]
            + ([{"file": "", "role": "closeup"}] if (q.get("closeup") or ["0"])[0] == "1" else []),
            "views": {}, "prep": {}}
    return {"seconds": e.estimate(fake), "views": len(e.plan(fake))}, 200


def films():
    try:
        import shots_routes as SR
    except Exception as err:
        return {"error": "the shots page's routes are unavailable: %s" % err}, 500
    out = []
    for film in SR._films():
        s = SR._load(film) or {}
        refs = SR._json(os.path.join(SR._out(film), "refs.json"), {})
        cast = [{"id": k, "role": (v or {}).get("role", ""), "has": os.path.exists(os.path.join(SR._out(film), "ref_%s.png" % k)),
                 "from": (refs.get(k) or {}).get("engine")} for k, v in (s.get("cast") or {}).items()]
        pl = (s.get("place") or {}).get("id")
        out.append({"film": film, "title": s.get("title") or film, "cast": cast,
                    "place": {"id": pl, "has": os.path.exists(os.path.join(SR._out(film), "ref_%s.png" % pl)),
                              "from": (refs.get(pl) or {}).get("engine")} if pl else None})
    return {"films": out}, 200


# ─── the queue ────────────────────────────────────────────────────────────────────────────────

def status():
    with _STATE.LOCK:
        j = _STATE.JOB
        run = None
        if j:
            run = {k: j[k] for k in ("id", "sheet", "op", "done", "total", "now", "started")}
            run["log"] = j["log"][-14:]
            run["elapsed"] = int(time.time() - j["started"])
        return {"running": run, "queue": [{k: q[k] for k in ("id", "sheet", "op")} for q in _STATE.QUEUE],
                "last": _STATE.LAST}, 200


def _enqueue(sid, op, **kw):
    if _elsewhere(sid):
        return {"error": "this sheet is being made by another process (the command line?) - "
                         "the page picks it up when that finishes"}, 409
    with _STATE.LOCK:
        for q in ([_STATE.JOB] if _STATE.JOB else []) + _STATE.QUEUE:
            if q["sheet"] == sid and q["op"] == op and not kw.get("views"):
                return {"ok": True, "queued": q["id"], "already": True}, 200
        _STATE.SEQ[0] += 1
        item = {"id": "s%d" % _STATE.SEQ[0], "sheet": sid, "op": op, "kw": kw, "log": [], "done": 0,
                "total": 0, "now": "waiting", "started": time.time(), "stop": False}
        if _STATE.JOB:
            _STATE.QUEUE.append(item)
            return {"ok": True, "queued": item["id"], "position": len(_STATE.QUEUE)}, 200
        _STATE.JOB = item
    _launch(item)
    return {"ok": True, "started": item["id"]}, 200


def _launch(item):
    item["started"] = time.time()

    def log(msg):
        with _STATE.LOCK:
            item["log"].append("%s  %s" % (time.strftime("%H:%M:%S"), msg))
            item["log"] = item["log"][-200:]
            item["now"] = msg

    def progress(i, n, msg):
        with _STATE.LOCK:
            item["done"], item["total"] = i, n
            if msg:
                item["now"] = msg

    def work():
        ok, err = True, ""
        try:
            e = E()
            op, sid, kw = item["op"], item["sheet"], item["kw"]
            if op in ("make", "redo"):
                e.make(sid, log=log, progress=progress, stopped=lambda: item["stop"], redo=kw.get("views"))
            elif op == "turntable":
                _turntable(sid, log, progress)
            elif op == "model":
                _model(sid, log, progress)
            elif op == "foundry":
                _to_foundry(sid, kw.get("style") or "cinematic", log, progress)
            else:
                raise RuntimeError("unknown job %s" % op)
        except Exception as ex:
            ok = False
            stopped = type(ex).__name__ == "Stopped"
            err = "stopped" if stopped else str(ex)[:300]
            if not stopped:
                traceback.print_exc()
            log("stopped" if stopped else "failed: %s" % err)
        finally:
            with _STATE.LOCK:
                _STATE.LAST = {"id": item["id"], "sheet": item["sheet"], "op": item["op"], "ok": ok,
                               "error": err, "secs": int(time.time() - item["started"]), "at": int(time.time()),
                               "log": item["log"][-6:]}
                nxt = _STATE.QUEUE.pop(0) if _STATE.QUEUE else None
                _STATE.JOB = nxt
            if nxt:
                _launch(nxt)

    threading.Thread(target=work, daemon=True, name="sheets-" + item["id"]).start()


def stop(data):
    with _STATE.LOCK:
        if data.get("all"):
            n = len(_STATE.QUEUE)
            _STATE.QUEUE[:] = []
            if _STATE.JOB:
                _STATE.JOB["stop"] = True
            return {"ok": True, "dropped": n, "stopping": bool(_STATE.JOB)}, 200
        qid = data.get("queue_id")
        if qid:
            before = len(_STATE.QUEUE)
            _STATE.QUEUE[:] = [q for q in _STATE.QUEUE if q["id"] != qid]
            return ({"ok": True} if len(_STATE.QUEUE) < before else {"error": "nothing waiting as %s" % qid}), \
                (200 if len(_STATE.QUEUE) < before else 404)
        if _STATE.JOB:
            _STATE.JOB["stop"] = True
            return {"ok": True, "stopping": _STATE.JOB["id"]}, 200
    return {"error": "nothing is running"}, 404


# ─── writing ──────────────────────────────────────────────────────────────────────────────────

def _picture(dataurl):
    from PIL import Image
    m = re.match(r"^data:image/(png|jpeg|jpg|webp);base64,(.+)$", str(dataurl or ""), re.S)
    if not m:
        raise ValueError("send a PNG, JPEG or WebP picture")
    raw = base64.b64decode(m.group(2))
    if len(raw) > MAX_BYTES:
        raise ValueError("that picture is over 25 MB")
    im = Image.open(io.BytesIO(raw))
    im.load()
    return im


def new(data):
    e = E()
    kind = data.get("kind")
    if kind not in e.KINDS:
        return {"error": "choose a character, an item or a place"}, 400
    pics = data.get("pictures") or []
    if not pics:
        return {"error": "add a picture - every angle is turned from it"}, 400
    if len(pics) > 3:
        return {"error": "up to three pictures"}, 400
    got, roles = [], set()
    try:
        for i, p in enumerate(pics):
            role = p.get("role") if p.get("role") in ("main", "closeup", "extra") else ("main" if i == 0 else "extra")
            if role in roles and role != "extra":
                role = "extra"
            roles.add(role)
            got.append((_picture(p.get("dataurl")), role))
    except Exception as err:
        return {"error": str(err)[:200]}, 400
    if "main" not in roles:
        got[0] = (got[0][0], "main")
    opts = _clean_options(e, data.get("options") or {}, kind, data.get("item_type") or "object")
    name = (data.get("name") or "").strip() or "Untitled %s" % kind
    try:
        s = e.new(kind, name, got, data.get("subject") or "", data.get("item_type") or "object", opts)
    except ValueError as err:
        return {"error": str(err)}, 400
    out = {"ok": True, "id": s["id"], "estimate": e.estimate(s)}
    if data.get("make", True):
        body, _ = _enqueue(s["id"], "make")
        out.update({k: v for k, v in body.items() if k != "ok"})
    return out, 200


def _clean_options(e, o, kind, item_type):
    out = {}
    for k in ("faces", "expressions", "finish_body", "upright"):
        if k in o:
            out[k] = bool(o[k])
    if "hd" in o and o["hd"] in ("off", "x2", "x4"):
        out["hd"] = o["hd"]
    if "times" in o:
        out["times"] = [t for t in (o["times"] or []) if t in e.TIMES]
    return out


def _sheet(data):
    sid = str(data.get("id") or "")
    if not ID_RE.match(sid):
        raise KeyError("no such sheet")
    return E().load(sid)


def make(data):
    try:
        s = _sheet(data)
    except KeyError as err:
        return {"error": str(err)}, 404
    return _enqueue(s["id"], "make")


def redo(data):
    try:
        s = _sheet(data)
    except KeyError as err:
        return {"error": str(err)}, 404
    keys = {v["key"] for v in E().plan(s)}
    views = [k for k in (data.get("views") or []) if k in keys]
    if not views:
        return {"error": "say which views to remake"}, 400
    return _enqueue(s["id"], "redo", views=views)


def options(data):
    e = E()
    try:
        s = _sheet(data)
    except KeyError as err:
        return {"error": str(err)}, 404
    if _busy_with(s["id"]):
        return {"error": "this sheet is being made - change it when the job ends"}, 409
    new_o = _clean_options(e, data.get("options") or {}, s["kind"], s.get("item_type"))
    old = dict(s.get("options") or {})
    merged = dict(old, **new_o)
    remade = False
    # what the angles are turned FROM changes: the whole sheet is made again
    if any(merged.get(k) != old.get(k) for k in ("upright", "finish_body")):
        s["prep"], s["views"], remade = {}, {}, True
    elif merged.get("hd") != old.get("hd"):
        for v in s["views"].values():
            v["hd"] = ""
    s["options"] = merged
    e.save(s)
    body, _ = _enqueue(s["id"], "make")
    return dict(body, remade=remade, estimate=e.estimate(s)), 200


def _busy_with(sid):
    if _elsewhere(sid):
        return True
    with _STATE.LOCK:
        return any(q["sheet"] == sid for q in ([_STATE.JOB] if _STATE.JOB else []) + _STATE.QUEUE)


def rename(data):
    try:
        s = _sheet(data)
    except KeyError as err:
        return {"error": str(err)}, 404
    name = (data.get("name") or "").strip()[:80]
    if not name:
        return {"error": "a sheet needs a name"}, 400
    s["name"] = name
    E().save(s)
    # the name is printed on the sheet: lay it out again, unless a job is about to anyway
    if s.get("sheet") and not _busy_with(s["id"]):
        try:
            E().compose(s["id"])
        except Exception as err:
            return {"ok": True, "name": name, "warning": "renamed, but the sheet was not redrawn: %s" % err}, 200
    return {"ok": True, "name": name}, 200


def delete(data):
    e = E()
    try:
        s = _sheet(data)
    except KeyError as err:
        return {"error": str(err)}, 404
    if _busy_with(s["id"]):
        return {"error": "this sheet is being made - stop the job first"}, 409
    os.makedirs(e.TRASH, exist_ok=True)
    dst = os.path.join(e.TRASH, s["id"])
    if os.path.exists(dst):
        shutil.rmtree(dst)
    shutil.move(e.sheet_dir(s["id"]), dst)
    return {"ok": True, "id": s["id"]}, 200


def restore(data):
    e = E()
    sid = str(data.get("id") or "")
    src = os.path.join(e.TRASH, sid)
    if not ID_RE.match(sid) or not os.path.isdir(src):
        return {"error": "nothing to restore"}, 404
    if os.path.exists(e.sheet_dir(sid)):
        return {"error": "a sheet called %s exists again" % sid}, 409
    shutil.move(src, e.sheet_dir(sid))
    return {"ok": True, "id": sid}, 200


def extra(data):
    try:
        s = _sheet(data)
    except KeyError as err:
        return {"error": str(err)}, 404
    what = data.get("what")
    if what not in ("turntable", "model"):
        return {"error": "turntable or model"}, 400
    if s["kind"] == "place":
        return {"error": "a place has no single object to turn - the 3D tools are for characters and items"}, 400
    return _enqueue(s["id"], what)


# ─── 3D, from the clean front view ────────────────────────────────────────────────────────────

def _front(s):
    d = E().sheet_dir(s["id"])
    rec = s["views"].get("turn_front") or {}
    for rel in (rec.get("hd"), rec.get("file"), (s.get("prep") or {}).get("base")):
        if rel and os.path.isfile(os.path.join(d, rel)):
            return os.path.join(d, rel)
    raise RuntimeError("make the sheet first - the 3D tools start from its front view")


def _extras_save(sid, key, rec):
    e = E()
    s = e.load(sid)
    s.setdefault("extras", {})[key] = rec
    e.save(s)


def _turntable(sid, log, progress):
    """TripoSplat (workflow 25): a gaussian splat and its 360-degree orbit as a video."""
    e = E()
    s = e.load(sid)
    run, set_path, load_wf, _, HOST, _ = e._comfy()
    progress(0, 1, "turning it into a splat")
    log("TripoSplat from the front view")
    wf = load_wf("25_triposplat.json")
    set_path(wf, "1.inputs.image", e._stage(_front(s), "sheet_tt_%s.png" % sid[:30]))
    set_path(wf, "15.inputs.filename_prefix", "claude-generated/sheets/tt_%s" % sid[:30])
    set_path(wf, "17.inputs.filename_prefix", "claude-generated/sheets/splat_%s" % sid[:30])
    t0 = time.time()
    _, outs = run(HOST, wf, quiet=True)
    d = e.sheet_dir(sid)
    vid = next((o for o in outs if o.lower().endswith((".mp4", ".webm", ".mov"))), None)
    if not vid:
        raise RuntimeError("TripoSplat returned no video")
    e._fetch([vid], os.path.join(d, "turntable" + os.path.splitext(vid)[1].lower()))
    spl = next((o for o in outs if o.lower().endswith((".spz", ".ply", ".glb"))), None)
    rec = {"file": "turntable" + os.path.splitext(vid)[1].lower(), "secs": round(time.time() - t0, 1),
           "at": int(time.time())}
    if spl:
        e._fetch([spl], os.path.join(d, "splat" + os.path.splitext(spl)[1].lower()))
        rec["splat"] = "splat" + os.path.splitext(spl)[1].lower()
    _extras_save(sid, "turntable", rec)
    progress(1, 1, "turntable made")


def _model(sid, log, progress):
    """Hunyuan3D 2.1 (workflow 24): a textured mesh from the front view."""
    e = E()
    s = e.load(sid)
    run, set_path, load_wf, _, HOST, _ = e._comfy()
    progress(0, 1, "building a 3D model")
    log("Hunyuan3D 2.1 from the front view")
    wf = load_wf("24_hunyuan3d_mesh.json")
    set_path(wf, "2.inputs.image", e._stage(_front(s), "sheet_mesh_%s.png" % sid[:30]))
    set_path(wf, "10.inputs.filename_prefix", "claude-generated/sheets/mesh_%s" % sid[:30])
    t0 = time.time()
    _, outs = run(HOST, wf, quiet=True)
    glb = next((o for o in outs if o.lower().endswith(".glb")), None)
    if not glb:
        raise RuntimeError("Hunyuan3D returned no mesh")
    e._fetch([glb], os.path.join(e.sheet_dir(sid), "model.glb"))
    _extras_save(sid, "model", {"file": "model.glb", "secs": round(time.time() - t0, 1), "at": int(time.time())})
    progress(1, 1, "model made")


# ─── to a film, to the Foundry ────────────────────────────────────────────────────────────────

def _cover(im, size):
    from PIL import Image
    r = max(size[0] / im.width, size[1] / im.height)
    im = im.resize((round(im.width * r), round(im.height * r)), Image.LANCZOS)
    left, top = (im.width - size[0]) // 2, (im.height - size[1]) // 2
    return im.crop((left, top, left + size[0], top + size[1]))


def _fit(im, size, fill=(118, 118, 118)):
    """Letterbox rather than crop: a standing figure keeps its feet in a 9:16 reference."""
    from PIL import Image
    r = min(size[0] / im.width, size[1] / im.height)
    im = im.resize((round(im.width * r), round(im.height * r)), Image.LANCZOS)
    out = Image.new("RGB", size, fill)
    out.paste(im, ((size[0] - im.width) // 2, (size[1] - im.height) // 2))
    return out


def send(data):
    """A view becomes one of a shot-script film's reference pictures - the same file the shots
    page's own upload writes (samples/fight/<film>/ref_<id>.png), recorded as from this sheet."""
    from PIL import Image
    try:
        s = _sheet(data)
    except KeyError as err:
        return {"error": str(err)}, 404
    try:
        import shots_routes as SR
    except Exception as err:
        return {"error": "the shots page's routes are unavailable: %s" % err}, 500
    film = str(data.get("film") or "")
    script = SR._load(film) if SR.FILM_RE.match(film) else None
    if script is None:
        return {"error": "no such film"}, 404
    key = data.get("view") or ("turn_front" if s["kind"] != "place" else "")
    d = E().sheet_dir(s["id"])
    if key:
        rec = s["views"].get(key) or {}
        rel = rec.get("hd") or rec.get("file")
        if not rel:
            return {"error": "that view is not made yet"}, 400
        src = os.path.join(d, rel)
    else:
        src = os.path.join(d, (s.get("prep") or {}).get("base") or s["sources"][0]["file"])
    target = str(data.get("target") or "")
    place = (script.get("place") or {}).get("id")
    if target == "new":
        ident = re.sub(r"[^a-z0-9_]+", "_", str(data.get("new_id") or s["name"]).lower()).strip("_")[:24]
        if not ident:
            return {"error": "name the new reference"}, 400
        if ident in (script.get("cast") or {}) or ident == place:
            return {"error": "%s is already in this film - choose it instead" % ident}, 409
        script.setdefault("cast", {})[ident] = {
            "role": (data.get("role") or s["name"])[:60],
            "prompt": "Full-length reference picture of %s against a plain mid-grey backdrop, from the sheet %s."
                      % (s["name"], s["id"]),
            "sheet": s["id"]}
        body, code = SR.save({"film": film, "script": script})
        if code != 200:
            return body, code
    elif target == place and place:
        ident = place
    elif target in (script.get("cast") or {}):
        ident = target
    else:
        return {"error": "choose who or what in the film this picture is"}, 400
    im = Image.open(src).convert("RGB")
    out = SR._out(film)
    os.makedirs(out, exist_ok=True)
    now = int(time.time())
    ref = os.path.join(out, "ref_%s.png" % ident)
    rp = os.path.join(out, "refs.json")
    refs = SR._json(rp, {})
    # the picture it replaces is kept, so the send can be undone rather than confirmed
    kept = None
    if os.path.exists(ref):
        kept = os.path.join("_replaced", "ref_%s.%d.png" % (ident, now))
        os.makedirs(os.path.join(out, "_replaced"), exist_ok=True)
        shutil.move(ref, os.path.join(out, kept))
    if ident == place:
        _cover(im, (1280, 720)).save(ref)
    else:
        _fit(im, (768, 1344)).save(ref)
    prev = refs.get(ident)
    refs[ident] = {"engine": "sheet", "sheet": s["id"], "view": key or "source", "seed": None, "prompt": None,
                   "at": now}
    json.dump(refs, open(rp, "w"), indent=1)
    s = E().load(s["id"])
    s.setdefault("sent", []).append({"film": film, "as": ident, "view": key or "source", "at": now,
                                     "new": target == "new", "kept": kept, "prev": prev})
    E().save(s)
    return {"ok": True, "film": film, "as": ident, "new": target == "new", "at": now}, 200


def unsend(data):
    """Undo a send: the picture it replaced comes back (or, for a new reference, the reference goes)."""
    try:
        s = _sheet(data)
    except KeyError as err:
        return {"error": str(err)}, 404
    import shots_routes as SR
    rec = next((x for x in s.get("sent") or [] if x.get("at") == data.get("at")), None)
    if not rec:
        return {"error": "nothing to undo"}, 404
    film, ident = rec["film"], rec["as"]
    out = SR._out(film)
    ref = os.path.join(out, "ref_%s.png" % ident)
    rp = os.path.join(out, "refs.json")
    refs = SR._json(rp, {})
    if (refs.get(ident) or {}).get("at") != rec["at"]:
        return {"error": "%s's picture in %s has changed since - nothing undone" % (ident, film)}, 409
    if rec.get("new"):
        script = SR._load(film) or {}
        if ident in (script.get("cast") or {}):
            del script["cast"][ident]
            body, code = SR.save({"film": film, "script": script})
            if code != 200:
                return {"error": "the film would not let %s go: %s" % (ident, body.get("error"))}, code
        if os.path.exists(ref):
            os.remove(ref)
        refs.pop(ident, None)
    else:
        if rec.get("kept") and os.path.exists(os.path.join(out, rec["kept"])):
            shutil.move(os.path.join(out, rec["kept"]), ref)
        elif os.path.exists(ref):
            os.remove(ref)
        if rec.get("prev"):
            refs[ident] = rec["prev"]
        else:
            refs.pop(ident, None)
    json.dump(refs, open(rp, "w"), indent=1)
    s = E().load(s["id"])
    s["sent"] = [x for x in s.get("sent") or [] if x.get("at") != rec["at"]]
    E().save(s)
    return {"ok": True}, 200


def foundry(data):
    try:
        s = _sheet(data)
    except KeyError as err:
        return {"error": str(err)}, 404
    if s["kind"] == "place":
        return {"error": "places go to a film from here; the Foundry's places are built from its own choices"}, 400
    if not (s["views"].get("turn_front") or {}).get("status") == "done":
        return {"error": "make the sheet first"}, 400
    return _enqueue(s["id"], "foundry", style=str(data.get("style") or "cinematic"))


_FY = {"mod": None, "mtime": None}


def _foundry_mod():
    p = os.path.join(STUDIO, "foundry.py")
    mt = os.path.getmtime(p)
    if _FY["mod"] is None or _FY["mtime"] != mt:
        spec = importlib.util.spec_from_file_location("studio_foundry_sheets", p)
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        _FY.update(mod=m, mtime=mt)
    return _FY["mod"]


def _styles():
    return (_foundry_mod().load_dict().get("style") or {}).get("options") or {}


def styles():
    return {"styles": [{"key": k, "label": v.get("label") or k} for k, v in _styles().items()]}, 200


ASK_OBJECT = ("Describe the {s} in this image as a prop reference for an image prompt. Physical facts only: "
              "what it is, its shape, materials, colours, markings and any distinctive details. One or two "
              "dense sentences. No background, no story, no camera language.")
REFUSAL = re.compile(r"^\W*(i am unable|i'm unable|i cannot|i can't|i can not|sorry|unfortunately)", re.I)


def _caption(e, path, atype, subject, sid):
    """One vision call (workflow 30). The Foundry's own captioner asks about a PERSON and, shown a
    radio, answered "I am unable to fulfill that request... depicts a radio, not a person" - which
    then became the prop's description. An object gets its own question, and a refusal is never
    kept as a description."""
    import glob
    staged = e._stage(path, "sheet_cap_%s.png" % sid[:30])
    if atype == "character":
        import character_new as CN
        text = CN.caption(staged) or ""
    else:
        run, set_path, load_wf, _, HOST, COMFY = e._comfy()
        wf = load_wf("30_vision_caption.json")
        set_path(wf, "2.inputs.image", staged)
        set_path(wf, "3.inputs.prompt", ASK_OBJECT.format(s=subject or "object"))
        stamp = "sheetcap_%d" % (time.time() % 100000)
        wf["90"] = {"class_type": "SaveText", "inputs": {"text": ["3", 0], "filename_prefix": stamp, "format": "txt"}}
        run(HOST, wf, quiet=True)
        hits = sorted(glob.glob(os.path.join(COMFY, "output", "**", stamp + "*"), recursive=True))
        text = open(hits[-1], encoding="utf-8", errors="replace").read() if hits else ""
    text = text.strip()
    return "" if REFUSAL.match(text) else text


def _to_foundry(sid, style, log, progress):
    """A Foundry asset whose pack IS this sheet: a character's turnaround, faces and expressions
    under the Foundry's own names; an object or weapon as a prop (hero + macro); clothing as a
    costume card. The words come from one vision caption of the source."""
    e = E()
    FY = _foundry_mod()
    s = e.load(sid)
    d = e.sheet_dir(sid)
    progress(0, 3, "describing it")
    log("asking the vision model to describe the source")
    atype = "character" if s["kind"] == "character" else "costume" if s.get("item_type") == "clothing" else "prop"
    try:
        caption = _caption(e, os.path.join(d, s["prep"]["base"]), atype, s.get("subject"), sid)
    except Exception as err:
        caption = ""
        log("no caption (%s)" % str(err)[:80])
    if not caption:
        log("no description came back - the asset keeps only its name")
    if style not in _styles():
        style = "cinematic"
    progress(1, 3, "creating the asset")
    name = s["name"]
    try:
        a = FY.new_asset(atype, name, style, {}, caption or name, level=1)
    except ValueError:
        a = FY.new_asset(atype, "%s %s" % (name, time.strftime("%m%d-%H%M")), style, {}, caption or name, level=1)
    images = e.foundry_images(sid, atype, FY.asset_dir(atype, a["id"]))
    a = FY.load_asset(atype, a["id"])
    a["images"] = images
    a["sheet"] = sid
    a["provenance"] = "from the sheet %s (your picture, turned)" % sid
    a["source_caption"] = caption
    FY.save_asset(a)
    s = e.load(sid)
    s["foundry"] = {"type": atype, "id": a["id"], "at": int(time.time())}
    e.save(s)
    log("Foundry %s %s: %d pictures" % (atype, a["id"], len(images)))
    progress(3, 3, "in the Foundry")


# ─── dispatch ─────────────────────────────────────────────────────────────────────────────────

def get(path, query):
    rest = path.strip("/")
    if rest == "":
        return listing()
    if rest == "one":
        return one((query.get("id") or [""])[0])
    if rest == "status":
        return status()
    if rest == "estimate":
        return estimate(query)
    if rest == "films":
        return films()
    if rest == "styles":
        return styles()
    return {"error": "unknown sheets route"}, 404


POSTS = {"new": new, "make": make, "redo": redo, "options": options, "rename": rename, "delete": delete,
         "restore": restore, "stop": stop, "send": send, "unsend": unsend, "foundry": foundry, "extra": extra}


def post(path, data):
    fn = POSTS.get(path.strip("/"))
    if not fn:
        return {"error": "unknown sheets route"}, 404
    return fn(data)
