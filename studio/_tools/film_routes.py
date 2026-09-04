"""Routes behind /film - the shot-by-shot editor.

Kept out of serve.py because it owns RENDER JOBS, story_routes-style: every render runs on
a worker thread and reports through a small in-memory job table, so the page can ask for
six takes across three engines and keep answering while they render. ComfyUI queues GPU
work internally, so concurrent submissions serialize there rather than here.

WHAT A TAKE IS. One attempt at one shot on one engine with one seed, immutable, QC-checked
the moment it lands (streams present, audio not flat, nothing frozen) - because this
project's worst bugs are files that exist, run the right length, and are wrong.

THE PIPELINE PER TAKE:  resolve anchor -> stage to ComfyUI input -> compile (film.py owns
the rulebook) -> run engine workflow -> pull the file local (never trust the SMB share) ->
poster + filmstrip -> QC -> record in film.json.

ComfyUI dying mid-batch is normal here - the LTX envelope kills the PROCESS, not the job -
so every render goes through ensure_comfy(), which restarts it by script and waits.
"""
import json, os, re, shutil, subprocess, sys, threading, time, traceback
import urllib.request

TOOLS = os.path.dirname(os.path.abspath(__file__))
STUDIO = os.path.dirname(TOOLS)
ROOT = os.path.dirname(STUDIO)
sys.path.insert(0, STUDIO)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
sys.path.insert(0, TOOLS)
os.environ.setdefault("COMFY_HOST", "127.0.0.1:8188")

# scripts/film.py exists too, and scripts sits first on sys.path - load the studio
# model by explicit path so the collision can never bite.
import importlib.util as _ilu                                # noqa: E402
_spec = _ilu.spec_from_file_location("studio_film", os.path.join(STUDIO, "film.py"))
F = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(F)

JOBS = {}
_LOCK = threading.Lock()
_SEQ = [0]


def _comfy():
    from comfy import run, set_path
    from epic import load_wf, ensure_local, HOST, COMFY
    return run, set_path, load_wf, ensure_local, HOST, COMFY


def _job(kind, total=1, **extra):
    with _LOCK:
        _SEQ[0] += 1
        jid = "j%d" % _SEQ[0]
        JOBS[jid] = {"id": jid, "kind": kind, "state": "running", "done": 0,
                     "total": total, "log": [], "error": "", "started": time.time()}
        JOBS[jid].update(extra)
    return jid


def _log(jid, msg):
    with _LOCK:
        JOBS[jid]["log"].append(msg)
        JOBS[jid]["log"] = JOBS[jid]["log"][-30:]


def _finish(jid, error=""):
    with _LOCK:
        JOBS[jid]["state"] = "failed" if error else "done"
        JOBS[jid]["error"] = error


def ensure_comfy(tries=3):
    for _ in range(tries):
        try:
            urllib.request.urlopen("http://127.0.0.1:8188/system_stats", timeout=5).read()
            return True
        except Exception:
            subprocess.run(["bash", os.path.join(ROOT, "scripts", "restart-comfy.sh")],
                           capture_output=True)
            for _ in range(60):
                try:
                    urllib.request.urlopen("http://127.0.0.1:8188/system_stats",
                                           timeout=5).read()
                    time.sleep(3)
                    return True
                except Exception:
                    time.sleep(5)
    return False


def _sh(*a):
    return subprocess.run(a, capture_output=True, text=True)


def _thumbs(mp4, base):
    """poster + a 6-frame strip; the strip is what makes a takes grid judgeable."""
    _sh("ffmpeg", "-y", "-v", "error", "-i", mp4, "-vf", "thumbnail=90,scale=480:-2",
        "-frames:v", "1", "-update", "1", base + ".png")
    _sh("ffmpeg", "-y", "-v", "error", "-i", mp4,
        "-vf", "fps=6/%s,scale=200:-2,tile=6x1" % max(_dur(mp4), 0.5),
        "-frames:v", "1", "-update", "1", base + "_strip.png")


def _dur(p):
    r = _sh("ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "csv=p=0", p)
    try:
        return float(r.stdout.strip())
    except ValueError:
        return 0.0


def _polish_mod():
    """studio/_tools/polish.py by explicit path - same collision-proofing as the model."""
    spec = _ilu.spec_from_file_location("film_polish", os.path.join(TOOLS, "polish.py"))
    m = _ilu.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _fps(p):
    r = _sh("ffprobe", "-v", "error", "-select_streams", "v:0",
            "-show_entries", "stream=r_frame_rate", "-of", "csv=p=0", p)
    try:
        a, _, b = (r.stdout.strip() or "24/1").partition("/")
        return round(float(a) / float(b or 1))
    except (ValueError, ZeroDivisionError):
        return 24


def _qc(path):
    try:
        import qc_films
        return qc_films.check(path)
    except Exception as e:
        return ["qc unavailable: %s" % e]


# ─── reads ──────────────────────────────────────────────────────────────────────────

def list_films():
    out = []
    for f in F.list_films():
        shots = f.data["shots"]
        out.append({"id": f.id, "title": f.data.get("title", f.id),
                    "look": f.data.get("look"),
                    "scenes": len(f.data["scenes"]), "shots": len(shots),
                    "picked": sum(1 for s in shots.values() if s.get("picked")),
                    "film": bool(_film_file(f))})
    return {"films": out}, 200


def _film_file(f):
    p = os.path.join(f.dir, "assets", "film.mp4")
    return p if os.path.exists(p) else ""


def tree(fid):
    f = F.load(fid)
    scenes = []
    for sc in f.data["scenes"]:
        shots = []
        for shid in sc["shots"]:
            sh = f.data["shots"].get(shid)
            if not sh:
                continue
            picked = next((t for t in sh["takes"] if t["id"] == sh.get("picked")), None)
            shots.append({"id": shid, "title": sh.get("title"),
                          "duration": sh.get("duration"),
                          "beats": len(sh.get("beats") or []),
                          "takes": len(sh["takes"]),
                          "engines": sorted({t["engine"] for t in sh["takes"]}),
                          "picked": sh.get("picked") or "",
                          "poster": picked and picked.get("poster") or "",
                          "picked_file": picked and picked.get("file") or "",
                          "picked_qc": len(picked.get("qc") or []) if picked else 0,
                          "picked_warnings": len(picked.get("warnings") or [])
                          if picked else 0,
                          "picked_fps": picked.get("fps", 24) if picked else 0,
                          "picked_dur": picked.get("duration", 0) if picked else 0,
                          "transition_out": sh.get("transition_out", "cut")})
        scenes.append({k: sc.get(k) for k in ("id", "title", "location", "time_of_day", "place", "plate",
                                              "weather", "ambience", "palette", "music",
                                              "cast_present", "no_people", "anchor",
                                              "anchor_candidates")}
                      | {"shots": shots})
    return {"id": f.id, "title": f.data.get("title"), "look": f.data.get("look"),
            "resolution": f.data.get("resolution", "auto"),
            "deliver": f.data.get("deliver", "native"),
            "look_clause": f.data.get("look_clause"), "grade": f.data.get("grade"),
            "logline": f.data.get("logline"), "negative": f.data.get("negative"),
            "cast": f.data.get("cast"), "scenes": scenes,
            "film": bool(_film_file(f)),
            "angles": F.ANGLES, "moves": sorted(F.MOVES),
            "transitions_out": F.TRANSITIONS_OUT}, 200


def shot_detail(fid, shid):
    f = F.load(fid)
    sh = f.shot(shid)
    return {"shot": sh, "resolved": f.resolved(shid),
            "keyframe_plan": F.keyframe_plan(f, shid)}, 200


def compile_shot(fid, shid):
    f = F.load(fid)
    flat = f.flat(shid)
    out = {}
    for eng in ("ltx", "h3", "wan", "cam"):
        try:
            out[eng] = F.compile_shot(flat, eng)
        except Exception as e:
            out[eng] = {"error": str(e)}
    return {"compiled": out, "keyframe_plan": F.keyframe_plan(f, shid)}, 200


def libraries():
    """Everything the editor can offer from disk: characters, ready voices, templates."""
    chars = []
    if os.path.isdir(F.CHARDIR):
        for fn in sorted(os.listdir(F.CHARDIR)):
            if not fn.endswith(".json"):
                continue
            try:
                d = json.load(open(os.path.join(F.CHARDIR, fn), encoding="utf-8"))
                chars.append({"id": d.get("id", fn[:-5]), "name": d.get("name"),
                              "sheet": d.get("sheet") or "", "desc": (d.get("desc") or "")[:90]})
            except Exception:
                continue
    voices = []
    vdir = os.path.join(STUDIO, "voices")
    if os.path.isdir(vdir):
        for fn in sorted(os.listdir(vdir)):
            if not fn.endswith(".json"):
                continue
            try:
                d = json.load(open(os.path.join(vdir, fn), encoding="utf-8"))
            except Exception:
                continue
            # blocked packs are real-person clones and are never offered anywhere
            if d.get("status") != "ready":
                continue
            voices.append({"id": fn[:-5], "name": d.get("name")})
    locations = []
    ldir = os.path.join(STUDIO, "locations")
    if os.path.isdir(ldir):
        for fn in sorted(os.listdir(ldir)):
            if fn.endswith(".json"):
                try:
                    d = json.load(open(os.path.join(ldir, fn), encoding="utf-8"))
                    d["id"] = fn[:-5]
                    locations.append(d)
                except Exception:
                    continue
    templates = []
    if os.path.isdir(F.TEMPLATES):
        for fn in sorted(os.listdir(F.TEMPLATES)):
            if fn.endswith(".json"):
                try:
                    d = json.load(open(os.path.join(F.TEMPLATES, fn), encoding="utf-8"))
                    templates.append({"id": fn[:-5], "title": d.get("title", fn[:-5]),
                                      "hint": d.get("hint", ""), "shot": d.get("shot")})
                except Exception:
                    continue
    return {"characters": chars, "voices": voices, "templates": templates,
            "locations": locations}, 200


def job_status(jid):
    with _LOCK:
        j = JOBS.get(jid)
        return (dict(j), 200) if j else ({"error": "no such job"}, 404)


def jobs_all():
    with _LOCK:
        running = [j for j in JOBS.values() if j.get("state") == "running"]
        done = [j for j in JOBS.values() if j.get("state") != "running"]
        rows = (sorted(running, key=lambda j: j["started"], reverse=True) +
                sorted(done, key=lambda j: j["started"], reverse=True)[:24])
        return {"jobs": rows}, 200


# ─── writes: structure ──────────────────────────────────────────────────────────────

def new_film(data):
    f = F.new_film(data["title"], look=data.get("look", "photoreal"),
                   resolution=data.get("resolution", "auto"),
                   deliver=data.get("deliver", "native"))
    return {"ok": True, "id": f.id}, 200


def edit_film(data):
    f = F.load(data["film"])
    for k in ("title", "logline", "look", "look_clause", "grade", "negative",
              "resolution", "deliver"):
        if k in data:
            f.data[k] = data[k]
    if "cast" in data:
        f.data["cast"] = data["cast"]
    if data.get("look") == "anime" and not data.get("look_clause"):
        f.data["look_clause"] = F.LOOK_ANIME
    f.save()
    return {"ok": True}, 200


def triage(data):
    """Per shot: local / trade-off / api, with the reasons in words. Read-only."""
    f = F.load(data["film"])
    return F.triage_film(f), 200


def new_scene(data):
    f = F.load(data["film"])
    sc = f.new_scene(data.get("title") or "scene")
    return {"ok": True, "id": sc["id"]}, 200


def edit_scene(data):
    f = F.load(data["film"])
    sc = f.scene(data["scene"])
    for k in ("title", "location", "time_of_day", "weather", "ambience", "palette", "place", "plate",
              "music", "cast_present", "no_people"):
        if k in data:
            sc[k] = data[k]
    if data.get("anchor") and data["anchor"] in (sc.get("anchor_candidates") or []):
        # picking a candidate COPIES it over the canonical anchor path, so every shot
        # that says "anchor: scene" follows the pick with no other change
        shutil.copy(os.path.join(f.dir, data["anchor"]),
                    os.path.join(f.dir, "assets", "anchor_%s.png" % sc["id"]))
        sc["anchor"] = "assets/anchor_%s.png" % sc["id"]
    f.save()
    return {"ok": True}, 200


def new_shot(data):
    f = F.load(data["film"])
    kw = {}
    if data.get("template"):
        tp = os.path.join(F.TEMPLATES, data["template"] + ".json")
        if os.path.exists(tp):
            kw = json.load(open(tp, encoding="utf-8")).get("shot") or {}
            kw = json.loads(json.dumps(kw))          # deep copy
    sh = f.new_shot(data["scene"], after=data.get("after") or None, **kw)
    return {"ok": True, "id": sh["id"]}, 200


def edit_shot(data):
    f = F.load(data["film"])
    sh = f.shot(data["shot"])
    for k in ("title", "duration", "aspect", "anchor", "keyframe_prompt", "beats",
              "sfx", "no_people", "enhance", "transition_out", "engine_notes",
              "cam"):
        if k in data:
            sh[k] = data[k]
    f.save()
    return {"ok": True}, 200


def reorder(data):
    f = F.load(data["film"])
    sc = f.scene(data["scene"])
    want = [s for s in data["order"] if s in sc["shots"]]
    sc["shots"] = want + [s for s in sc["shots"] if s not in want]
    f.save()
    return {"ok": True}, 200


def delete_shot(data):
    f = F.load(data["film"])
    shid = data["shot"]
    for sc in f.data["scenes"]:
        if shid in sc["shots"]:
            sc["shots"].remove(shid)
    f.data["shots"].pop(shid, None)
    f.save()
    return {"ok": True}, 200


def pick(data):
    f = F.load(data["film"])
    sh = f.shot(data["shot"])
    if data["take"] and not any(t["id"] == data["take"] for t in sh["takes"]):
        return {"error": "no such take"}, 404
    sh["picked"] = data["take"]
    f.save()
    return {"ok": True}, 200


# ─── anchors and keyframes ──────────────────────────────────────────────────────────

def _stage(comfy_dir, src, name):
    shutil.copy(src, os.path.join(comfy_dir, "input", name))
    return name


ANCHOR_SEEDS = (5, 21, 77)


def _render_scene_anchor(jid, fid, scid):
    run, set_path, load_wf, ensure_local, HOST, COMFY = _comfy()
    f = F.load(fid)
    sc = f.scene(scid)
    try:
        if not ensure_comfy():
            raise RuntimeError("ComfyUI will not come up")
        look = f.data.get("look")
        ground = ", ".join(x for x in (sc.get("location"), sc.get("time_of_day"),
                                       sc.get("weather"), sc.get("palette")) if x)
        present = [c for c in (sc.get("cast_present") or []) if c in f.data["cast"]]
        clauses = [f.data["cast"][c]["clause"] for c in present]
        prompt = ", ".join([x for x in [", ".join(clauses), ground] if x])
        dest = os.path.join(f.dir, "assets", "anchor_%s.png" % scid)
        _log(jid, "anchor prompt: %s" % prompt[:120])
        if look == "anime" and len(present) >= 2:
            wf = load_wf("45_anime_two_char_ipadapter.json")
            sheets = [f.data["cast"][c].get("sheet") or "" for c in present[:2]]
            set_path(wf, "2.inputs.image", sheets[0])
            set_path(wf, "12.inputs.image", sheets[1])
            set_path(wf, "20.inputs.width", 1216)
            set_path(wf, "20.inputs.height", 832)
            set_path(wf, "21.inputs.width", 608)
            set_path(wf, "21.inputs.height", 832)
            set_path(wf, "23.inputs.x", 608)
            set_path(wf, "5.inputs.text",
                     "2people, on the LEFT %s, and on the RIGHT %s, %s, %s"
                     % (clauses[0], clauses[1], ground, F.LOOK_ANIME))
            set_path(wf, "6.inputs.text", F.NEG_ANIME)
            set_path(wf, "7.inputs.width", 1216)
            set_path(wf, "7.inputs.height", 832)
            set_path(wf, "8.inputs.seed", int(time.time()) % 99991)
            set_path(wf, "10.inputs.width", 1216)
            set_path(wf, "10.inputs.height", 832)
            set_path(wf, "11.inputs.filename_prefix",
                     "claude-generated/films/%s/anchor_%s" % (fid, scid))
        elif look == "anime":
            wf = load_wf("22_anime_kf_ipadapter.json")
            ch = f.data["cast"].get(present[0]) if present else {}
            set_path(wf, "2.inputs.image", (ch or {}).get("sheet") or "")
            set_path(wf, "4.inputs.weight", 0.3)
            set_path(wf, "5.inputs.text", "%s, %s, masterpiece, best quality, anime key "
                     "visual, %s" % ((ch or {}).get("tags") or prompt, ground,
                                     F.LOOK_ANIME))
            set_path(wf, "6.inputs.text", F.NEG_ANIME)
            set_path(wf, "7.inputs.width", 1216)
            set_path(wf, "7.inputs.height", 832)
            set_path(wf, "8.inputs.seed", int(time.time()) % 99991)
            set_path(wf, "10.inputs.width", 1216)
            set_path(wf, "10.inputs.height", 832)
            set_path(wf, "11.inputs.filename_prefix",
                     "claude-generated/films/%s/anchor_%s" % (fid, scid))
        else:
            ports = [f.data["cast"][c].get("portrait") for c in present
                     if f.data["cast"][c].get("portrait")][:2]
            if ports:
                # the measured identity route: portraits in, the scene out with the same
                # faces. One portrait doubles as both references for a single character.
                p0 = _stage(COMFY, os.path.join(f.dir, ports[0]),
                            "film_port_%s_0.png" % fid)
                p1 = _stage(COMFY, os.path.join(f.dir, ports[-1]),
                            "film_port_%s_1.png" % fid)
                wf = load_wf("14_qwen_edit_ref.json")
                set_path(wf, "8.inputs.image", p0)
                set_path(wf, "9.inputs.image", p1)
                set_path(wf, "7.inputs.strength_model", 0.0)
                # each reference must be BOUND to its person by name, or the edit keeps
                # one face and invents the other - sc01 proved it with a crowd behind
                if len(ports) > 1 and len(present) > 1:
                    # the binding that MEASURED as holding both faces: sides, with
                    # "exact same face unchanged" adjacent to each person. "The first
                    # reference is X" and photo-language both lost one face.
                    ca = f.data["cast"][present[0]]
                    cb = f.data["cast"][present[1]]
                    prompt14 = ("On the left stands the woman from the first reference "
                                "image with her exact same face unchanged, %s. On the "
                                "right stands the man from the second reference image "
                                "with his exact same face unchanged, %s. %s. %s"
                                % (ca["clause"], cb["clause"], ground,
                                   f.data.get("look_clause") or F.LOOK_PHOTO))
                else:
                    ca = f.data["cast"][present[0]]
                    prompt14 = ("Keep the exact face and identity of the person in the "
                                "reference images. Place %s in a new scene: %s. %s"
                                % (ca["clause"], ground,
                                   f.data.get("look_clause") or F.LOOK_PHOTO))
                set_path(wf, "10.inputs.prompt", prompt14)
                set_path(wf, "11.inputs.prompt", F.NEG_PHOTO)
                set_path(wf, "20.inputs.width", 1472)
                set_path(wf, "20.inputs.height", 832)
                set_path(wf, "13.inputs.seed", int(time.time()) % 99991)
                set_path(wf, "15.inputs.filename_prefix",
                         "claude-generated/films/%s/anchor_%s" % (fid, scid))
            else:
                wf = load_wf("01_qwen_t2i_turbo.json")
                set_path(wf, "10.inputs.text", "%s. %s"
                         % (prompt, f.data.get("look_clause") or F.LOOK_PHOTO))
                set_path(wf, "11.inputs.text", F.NEG_PHOTO)
                set_path(wf, "12.inputs.width", 1472)
                set_path(wf, "12.inputs.height", 832)
                set_path(wf, "13.inputs.seed", int(time.time()) % 99991)
                set_path(wf, "15.inputs.filename_prefix",
                         "claude-generated/films/%s/anchor_%s" % (fid, scid))
        cands = []
        for i, sd in enumerate(ANCHOR_SEEDS):
            for node in ("13", "8"):
                try:
                    set_path(wf, "%s.inputs.seed" % node, sd)
                except (KeyError, TypeError):
                    pass
            _, outs = run(HOST, wf, quiet=True)
            if not outs:
                continue
            cp = os.path.join(f.dir, "assets", "anchor_%s_c%d.png" % (scid, i))
            ensure_local(outs[0], cp)
            cands.append("assets/anchor_%s_c%d.png" % (scid, i))
            _log(jid, "candidate %d (seed %d)" % (i + 1, sd))
        if not cands:
            raise RuntimeError("no candidates rendered")
        shutil.copy(os.path.join(f.dir, cands[0]), dest)
        f2 = F.load(fid)
        sc2 = f2.scene(scid)
        sc2["anchor"] = "assets/anchor_%s.png" % scid
        sc2["anchor_candidates"] = cands
        f2.save()
        _finish(jid)
    except Exception as e:
        _finish(jid, str(e)[:300])


def scene_anchor(data):
    jid = _job("anchor", film=data["film"], scene=data["scene"])
    threading.Thread(target=_render_scene_anchor,
                     args=(jid, data["film"], data["scene"]), daemon=True).start()
    return {"job": jid}, 200


def _resolve_anchor_file(f, shid, jid):
    """Absolute path of the start image for this shot, generating nothing: the scene
    anchor and prev_last are files that already exist or an error the caller can show."""
    plan = F.keyframe_plan(f, shid)
    if plan["mode"] == "scene":
        p = plan.get("path")
        if not p:
            raise RuntimeError("scene has no anchor yet - generate one in the Scene tab")
        return os.path.join(f.dir, p)
    if plan["mode"] == "file":
        return os.path.expanduser(plan["path"])
    if plan["mode"] == "prev_last":
        tf = plan.get("take_file")
        if not tf:
            raise RuntimeError("prev_last: previous shot has no picked take")
        src = os.path.join(f.dir, tf)
        dest = os.path.join(f.dir, "assets", "last_%s.png" % shid)
        _sh("ffmpeg", "-y", "-v", "error", "-sseof", "-0.2", "-i", src,
            "-update", "1", "-frames:v", "1", dest)
        if not os.path.exists(dest):
            raise RuntimeError("could not extract last frame")
        return dest
    if plan["mode"] == "generate":
        return _render_shot_keyframe(f, shid, plan)
    raise RuntimeError(plan.get("error") or "no anchor")


def _render_shot_keyframe(f, shid, plan):
    """A shot-specific start image through the right identity path, cached by content:
    photoreal through Qwen, anime through the character sheet with the IPAdapter weight
    the framing calls for (0.6 portrait, 0.3 wide - PLUS FACE hijacks composition)."""
    import hashlib
    run, set_path, load_wf, ensure_local, HOST, COMFY = _comfy()
    sh = f.shot(shid)
    flat = f.flat(shid)
    prompt = plan.get("prompt") or ""
    if not prompt:
        raise RuntimeError("anchor=generate needs a keyframe prompt on the shot")
    ports = [f.data["cast"][c].get("portrait") for c in (plan.get("present") or [])
             if f.data["cast"].get(c, {}).get("portrait")][:2]
    key = hashlib.sha1(("%s|%s|%s|%s" % (prompt, plan.get("ipa"), f.data.get("look"),
                                         "|".join(ports))).encode()).hexdigest()[:10]
    dest = os.path.join(f.dir, "assets", "kf_%s_%s.png" % (shid, key))
    if os.path.exists(dest):
        return dest
    if not ensure_comfy():
        raise RuntimeError("ComfyUI will not come up")
    w, h = (896, 1216) if flat.get("aspect") == "portrait" else (1472, 832)
    ground = ", ".join(x for x in (flat.get("location"), flat.get("time_of_day"),
                                   flat.get("weather")) if x)
    if f.data.get("look") == "anime":
        present = plan.get("present") or []
        ch = f.data["cast"].get(present[0]) if present else {}
        wf = load_wf("22_anime_kf_ipadapter.json")
        set_path(wf, "2.inputs.image", (ch or {}).get("sheet") or "")
        set_path(wf, "4.inputs.weight", float(plan.get("ipa") or 0.3)
                 if (ch or {}).get("sheet") else 0.0)
        set_path(wf, "5.inputs.text", "%s, %s, masterpiece, best quality, anime key "
                 "visual, %s" % (prompt, ground, F.LOOK_ANIME))
        set_path(wf, "6.inputs.text", F.NEG_ANIME)
        set_path(wf, "7.inputs.width", min(w, 1216))
        set_path(wf, "7.inputs.height", h if h <= 832 else 1216)
        set_path(wf, "8.inputs.seed", 31)
        set_path(wf, "10.inputs.width", min(w, 1216))
        set_path(wf, "10.inputs.height", h if h <= 832 else 1216)
        set_path(wf, "11.inputs.filename_prefix",
                 "claude-generated/films/%s/kf_%s" % (f.id, shid))
    elif ports:
        p0 = _stage(COMFY, os.path.join(f.dir, ports[0]), "film_kfp_%s_0.png" % f.id)
        p1 = _stage(COMFY, os.path.join(f.dir, ports[-1]), "film_kfp_%s_1.png" % f.id)
        wf = load_wf("14_qwen_edit_ref.json")
        set_path(wf, "8.inputs.image", p0)
        set_path(wf, "9.inputs.image", p1)
        set_path(wf, "7.inputs.strength_model", 0.0)
        set_path(wf, "10.inputs.prompt",
                 "Keep the exact faces and identities of the person in the first "
                 "reference image%s. Place them in a new scene: %s, %s. %s"
                 % (" and the person in the second reference image"
                    if len(ports) > 1 else "", prompt, ground,
                    f.data.get("look_clause") or F.LOOK_PHOTO))
        set_path(wf, "11.inputs.prompt", F.NEG_PHOTO)
        set_path(wf, "20.inputs.width", w)
        set_path(wf, "20.inputs.height", h)
        set_path(wf, "13.inputs.seed", 31)
        set_path(wf, "15.inputs.filename_prefix",
                 "claude-generated/films/%s/kf_%s" % (f.id, shid))
    else:
        wf = load_wf("01_qwen_t2i_turbo.json")
        set_path(wf, "10.inputs.text", "%s, %s. %s" % (prompt, ground,
                 f.data.get("look_clause") or F.LOOK_PHOTO))
        set_path(wf, "11.inputs.text", F.NEG_PHOTO)
        set_path(wf, "12.inputs.width", w)
        set_path(wf, "12.inputs.height", h)
        set_path(wf, "13.inputs.seed", 31)
        set_path(wf, "15.inputs.filename_prefix",
                 "claude-generated/films/%s/kf_%s" % (f.id, shid))
    _, outs = run(HOST, wf, quiet=True)
    if not outs:
        raise RuntimeError("keyframe render returned nothing")
    ensure_local(outs[0], dest)
    return dest


# ─── takes ──────────────────────────────────────────────────────────────────────────

def _last_frame(video, dest):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-sseof", "-0.3", "-i", video,
                    "-frames:v", "1", "-update", "1", dest], capture_output=True)
    return dest if os.path.exists(dest) else None


def _scene_drift(video, start_img, tag):
    """How much of the start picture's content the last frame has lost.
    -> {"lost": 0..1, "missing": [...], "kept": n} or None if it cannot be judged."""
    try:
        run, set_path, load_wf, ensure_local, HOST, comfy_dir = _comfy()
        last = _last_frame(video, os.path.join(comfy_dir, "input", "drift_%s_last.png" % tag))
        if not last:
            return {"error": "could not extract the last frame of %s" % os.path.basename(video)}
        shutil.copy(start_img, os.path.join(comfy_dir, "input", "drift_%s_start.png" % tag))
        a = _caption_scene("drift_%s_start.png" % tag)
        time.sleep(1.1)   # the caption stamp is per second; two calls must not share one
        b = _caption_scene("drift_%s_last.png" % tag)
        if not a or not b:
            return {"error": "caption empty (start %d chars, last %d chars)" % (len(a or ""), len(b or ""))}
        A = {_stem(w) for w in _content_words(a)}
        B = {_stem(w) for w in _content_words(b)}
        if len(A) < 4:
            return {"error": "start caption too thin: %r" % a[:80]}
        missing = []
        for w in sorted(A):
            if w in B or any(w[:5] == x[:5] for x in B if len(x) >= 5):
                continue
            syn = _SYN.get(w, ())
            if any(_stem(x) in B for x in syn):
                continue
            missing.append(w)
        lost = len(missing) / float(len(A))
        return {"lost": round(lost, 2), "missing": missing[:12], "kept": len(A) - len(missing),
                "last_caption": b[:400]}
    except Exception as e:
        return {"error": str(e)[:160]}


# calibrated on 2026-09-04: a take that turned a bridge into a marina lost 0.72;
# takes that held their scene lost 0.09-0.29; one uncertain take 0.50
# 2026-09-04 09:15: a take flagged at 0.61 held its scene; two more at 0.62 held. Margin.
DRIFT_LIMIT = 0.65


def _cut_off(frame_png):
    """Is the subject in this frame flush against an edge? -> (bool, detail).
    Flush means the mask fills more than 35% of an edge's length, or touches the
    bottom edge along more than 25% of it (feet out of frame)."""
    try:
        sys.path.insert(0, TOOLS) if TOOLS not in sys.path else None
        import pack_qc
        alpha = pack_qc._subject_alpha(frame_png)
        if alpha is None:
            return False, "no segmenter"
        a = alpha.resize((160, int(160 * alpha.size[1] / alpha.size[0])))
        w, h = a.size
        px = a.load()
        top = sum(1 for x in range(w) if px[x, 0] > 40 or px[x, 1] > 40) / float(w)
        bottom = sum(1 for x in range(w) if px[x, h - 1] > 40 or px[x, h - 2] > 40) / float(w)
        left = sum(1 for y in range(h) if px[0, y] > 40 or px[1, y] > 40) / float(h)
        right = sum(1 for y in range(h) if px[w - 1, y] > 40 or px[w - 2, y] > 40) / float(h)
        detail = "top=%.2f bottom=%.2f left=%.2f right=%.2f" % (top, bottom, left, right)
        return (top > 0.35 or bottom > 0.25 or left > 0.35 or right > 0.35), detail
    except Exception as e:
        return False, "qc unavailable: %s" % str(e)[:60]
# a spoken line peaks well above ambience: measured -6.5 / -7.4 dB for lines against
# -19.7 for an empty street. Below this, the line was probably not spoken.
SPEECH_PEAK_DB = -14.0


def _peak_db(video):
    """Peak loudness of the take's audio in dB (0 = full scale), or None."""
    try:
        out = subprocess.run(["ffmpeg", "-v", "info", "-i", video, "-vn", "-af", "volumedetect",
                              "-f", "null", "-"], capture_output=True, text=True).stderr
        for l in out.splitlines():
            if "max_volume" in l:
                return float(l.split("max_volume:")[1].split("dB")[0].strip())
    except Exception:
        return None
    return None


def _sound_donor(f, sh):
    """the newest sounding, unvoiced take in the shot's scene, else in the film:
    (path, take id, shot id) or None"""
    def cands(shots):
        out = []
        for s in shots:
            for t in (s.get("takes") or []):
                if (t.get("engine") or "").endswith("+vo"):
                    continue
                if any("SILENT" in str(n) for n in (t.get("qc") or [])):
                    continue
                rel = t.get("file") or ""
                p = os.path.join(f.dir, rel)
                if rel and os.path.exists(p):
                    out.append((t.get("created") or "", p, t["id"], s["id"]))
        return out
    shots = list((f.data.get("shots") or {}).values())
    same = [s for s in shots if s.get("scene") == sh.get("scene") and s.get("id") != sh.get("id")]
    others = [s for s in shots if s.get("id") != sh.get("id")]
    for pool in (same, others):
        c = sorted(cands(pool), key=lambda x: x[0])
        if c:
            return c[-1][1:]
    return None


def _borrow_audio(dest, donor):
    """dest keeps its picture and takes the donor's soundtrack, looped to length"""
    tmp = dest[:-4] + "_bed.mp4"
    try:
        _sh("ffmpeg", "-y", "-v", "error", "-i", dest, "-stream_loop", "-1", "-i", donor,
            "-map", "0:v", "-map", "1:a", "-shortest", "-c:v", "copy",
            "-c:a", "aac", "-b:a", "192k", tmp)
        if os.path.exists(tmp) and os.path.getsize(tmp) > 1000:
            os.replace(tmp, dest)
            return True
    except Exception:
        pass
    if os.path.exists(tmp):
        os.remove(tmp)
    return False


def _render_take(jid, f, sh, eng, seed):
    run, set_path, load_wf, ensure_local, HOST, COMFY = _comfy()
    flat = f.flat(sh["id"])
    c = F.compile_shot(flat, eng)
    tid = "t%d" % (int(time.time() * 1000) % 10 ** 9)
    tdir = os.path.join(f.dir, "takes", sh["id"])
    os.makedirs(tdir, exist_ok=True)
    rel = os.path.join("takes", sh["id"], "%s_%s.mp4" % (eng, tid))
    dest = os.path.join(f.dir, rel)
    anchor = _resolve_anchor_file(f, sh["id"], jid)
    staged = _stage(COMFY, anchor, "film_%s_%s.png" % (f.id, sh["id"]))
    prefix = "claude-generated/films/%s/%s_%s" % (f.id, sh["id"], tid)
    if not ensure_comfy():
        raise RuntimeError("ComfyUI will not come up")

    if eng == "ltx":
        wf = load_wf(c["workflow"])
        set_path(wf, "395.inputs.image", staged)
        set_path(wf, "sg1_376.inputs.value", c["prompt"])
        set_path(wf, "sg1_373.inputs.text", c["negative"])
        set_path(wf, "sg1_383.inputs.value", bool(c["enhance"]))
        set_path(wf, "sg1_362.inputs.value", int(c["seconds"]))
        set_path(wf, "403.inputs.megapixels", float(c["megapixels"]))
        set_path(wf, "403.inputs.aspect_ratio", c["aspect"])
        set_path(wf, "sg1_339.inputs.noise_seed", seed)
        set_path(wf, "75.inputs.filename_prefix", prefix)
    elif eng == "h3":
        wf = load_wf(c["workflow"])
        set_path(wf, "8.inputs.image", staged)
        set_path(wf, "20.inputs.prompt", c["prompt"])
        set_path(wf, "20.inputs.width", c["width"])
        set_path(wf, "20.inputs.height", c["height"])
        set_path(wf, "20.inputs.length", c["length"])
        set_path(wf, "33.inputs.noise_seed", seed)
        set_path(wf, "51.inputs.filename_prefix", prefix)
    elif eng == "cam":
        # A camera rig: the motion is arithmetic, the plate is this shot's anchor. No
        # ComfyUI, no seed lottery - the same parameters always give the same pixels.
        import importlib.util
        _cp = os.path.join(STUDIO, "_tools", "camrig.py")
        _sp = importlib.util.spec_from_file_location("camrig", _cp)
        camrig = importlib.util.module_from_spec(_sp)
        _sp.loader.exec_module(camrig)
        cam = sh.get("cam") or {}
        rig = cam.get("rig") or "still_push"
        silent = dest[:-4] + "_silent.mp4"
        camrig.render(rig, anchor, silent, params=cam.get("params") or {},
                      preset=cam.get("preset") or None, fps=int(f.data.get("fps") or 24))
        # arithmetic has no sound. Mux whatever the shot names, or a silent bed,
        # so the take still assembles and QC is informative rather than fatal.
        aud = cam.get("audio")
        if aud and os.path.exists(os.path.expanduser(aud)):
            _sh("ffmpeg", "-y", "-v", "error", "-i", silent, "-i",
                os.path.expanduser(aud), "-map", "0:v", "-map", "1:a",
                "-shortest", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", dest)
        else:
            _sh("ffmpeg", "-y", "-v", "error", "-i", silent, "-f", "lavfi",
                "-i", "anullsrc=r=48000:cl=stereo", "-shortest", "-c:v", "copy",
                "-c:a", "aac", "-b:a", "96k", dest)
        if os.path.exists(silent):
            os.remove(silent)
        _thumbs(dest, dest[:-4])
        qc = _qc(dest)
        try:
            _start = _resolve_anchor_file(f, sh["id"], jid)
            _d = _scene_drift(dest, _start, "%s_%s" % (f.id, sh["id"])) if _start else None
        except Exception as e:
            _d = {"error": "anchor: %s" % str(e)[:120]}
        if _d and _d.get("error"):
            _log(jid, "drift check unavailable: %s" % _d["error"])
            _d = None
        if _d and _d["lost"] > DRIFT_LIMIT and len(sh.get("beats") or []) <= 1:
            qc = list(qc) + ["scene drift: the last frame has lost %d%% of the start "
                             "picture (%s)" % (int(_d["lost"] * 100), ", ".join(_d["missing"][:5]))]
            _log(jid, "scene drift %d%% - %s" % (int(_d["lost"] * 100), ", ".join(_d["missing"][:5])))
        elif _d:
            _log(jid, "scene held (%d%% of the start picture's content in the last frame)"
                 % int((1 - _d["lost"]) * 100))
        v = camrig.verdict(rig, cam.get("params") or {}, cam.get("preset") or None)
        take = {"id": tid, "engine": "cam", "seed": 0,
                "created": time.strftime("%H:%M"), "file": rel,
                "poster": rel[:-4] + ".png", "strip": rel[:-4] + "_strip.png",
                "duration": round(_dur(dest), 2), "fps": _fps(dest), "qc": qc,
                "drift": _d,
                "warnings": ([] if v.get("pass", True) else
                             ["camrig shape test FAILED: %s" % v]),
                "prompt": "camrig %s%s %s" % (rig,
                                              "/" + cam["preset"] if cam.get("preset") else "",
                                              cam.get("params") or "")}
        f2 = F.load(f.id)
        sh2 = f2.shot(sh["id"])
        sh2["takes"].append(take)
        if not sh2.get("picked") and not qc:
            sh2["picked"] = tid
        f2.save()
        return tid
    elif eng == "wan":
        wf = load_wf(c["workflow"])
        set_path(wf, "10.inputs.image", staged)
        set_path(wf, "11.inputs.text", c["prompt"])
        set_path(wf, "12.inputs.text", c["negative"])
        set_path(wf, "13.inputs.length", c["frames"])
        set_path(wf, "13.inputs.width", 1280)
        set_path(wf, "13.inputs.height", 720)
        set_path(wf, "14.inputs.noise_seed", seed)
        set_path(wf, "17.inputs.fps", float(c["fps"]))
        set_path(wf, "18.inputs.filename_prefix", prefix)
    else:
        raise RuntimeError("unknown engine %r" % eng)

    _, outs = run(HOST, wf, quiet=True)
    vids = [o for o in outs or [] if o.endswith(".mp4")]
    if not vids:
        raise RuntimeError("no video output")
    ensure_local(vids[0], dest)
    _thumbs(dest, dest[:-4])
    qc = _qc(dest)
    if any("SILENT" in str(n) for n in qc):
        donor = _sound_donor(f, sh)
        if donor and _borrow_audio(dest, donor[0]):
            qc = [n for n in qc if "SILENT" not in str(n)] + [
                "sound borrowed from take %s of shot %s - the render was silent" % (donor[1], donor[2])]
            _log(jid, "the render was silent; its soundtrack is borrowed from take %s of shot %s"
                 % (donor[1], donor[2]))
        elif not donor:
            _log(jid, "the render was silent and no other take of this film has sound to lend")
    try:
        _start = _resolve_anchor_file(f, sh["id"], jid)
        _d = _scene_drift(dest, _start, "%s_%s" % (f.id, sh["id"])) if _start else None
    except Exception as e:
        _d = {"error": "anchor: %s" % str(e)[:120]}
    if _d and _d.get("error"):
        _log(jid, "drift check unavailable: %s" % _d["error"])
        _d = None
    if _d and _d["lost"] > DRIFT_LIMIT and len(sh.get("beats") or []) <= 1:
        qc = list(qc) + ["scene drift: the last frame has lost %d%% of the start picture (%s)"
                         % (int(_d["lost"] * 100), ", ".join(_d["missing"][:5]))]
        _log(jid, "scene drift %d%% - %s" % (int(_d["lost"] * 100), ", ".join(_d["missing"][:5])))
    elif _d:
        _log(jid, "scene held (%d%% of the start picture's content in the last frame)" % int((1 - _d["lost"]) * 100))
    # an empty shot that grew people: the last frame's caption names a person
    _empty = bool(sh.get("no_people")) or (sh.get("no_people") is None and bool(
        (f.scene(sh["scene"]) or {}).get("no_people")))
    if _empty and _d and _d.get("last_caption"):
        _cap = " " + re.sub(r"[^a-z ]", " ", _d["last_caption"].lower()) + " "
        _who = [w for w in ("man", "men", "woman", "women", "people", "person", "girl", "boy",
                            "child", "children", "figure", "figures", "pedestrian", "pedestrians",
                            "crowd", "couple", "student", "students") if " %s " % w in _cap]
        if _who:
            qc = list(qc) + ["people appeared in an empty shot (%s)" % ", ".join(_who[:4])]
            _log(jid, "people appeared in an empty shot: %s" % ", ".join(_who[:4]))
    _cast_here = any((b.get("subject") or "") in (f.data.get("cast") or {}) for b in (sh.get("beats") or []))
    if _cast_here and eng == "ltx":
        try:
            _lf = _last_frame(dest, dest[:-4] + "_last.png")
            _co, _cd = _cut_off(_lf) if _lf else (False, "no frame")
            if _co:
                # LTX pushes in on nearly every take; ending closer than it started is
                # information for the director, not a fault to re-roll
                qc = list(qc) + ["ends closer than it started - the person fills the frame edge at the end (%s)" % _cd]
                _log(jid, "ends closer than it started: %s" % _cd)
            else:
                _log(jid, "framing held at the end (%s)" % _cd)
        except Exception:
            pass
    _line = any(((b.get("dialogue") or {}).get("line") or "").strip() for b in (sh.get("beats") or []))
    if _line and eng == "ltx":
        _pk = _peak_db(dest)
        if _pk is not None and _pk < SPEECH_PEAK_DB:
            qc = list(qc) + ["the line may not have been spoken (audio peaks at %.1f dB)" % _pk]
            _log(jid, "quiet for a dialogue shot: peak %.1f dB" % _pk)
        elif _pk is not None:
            _log(jid, "speech level ok: peak %.1f dB" % _pk)
    take = {"id": tid, "engine": eng, "seed": seed, "created": time.strftime("%H:%M"),
            "file": rel, "poster": rel[:-4] + ".png", "strip": rel[:-4] + "_strip.png",
            "duration": round(_dur(dest), 2), "fps": _fps(dest), "qc": qc,
            "drift": _d,
            "warnings": c.get("warnings") or [], "prompt": c["prompt"][:400]}
    f2 = F.load(f.id)                          # re-load: takes may have landed meanwhile
    sh2 = f2.shot(sh["id"])
    sh2["takes"].append(take)
    if not sh2.get("picked") and not qc:
        sh2["picked"] = tid
    f2.save()
    return tid


def _takes_job(jid, fid, shid, engines, n, seed):
    try:
        f = F.load(fid)
        sh = f.shot(shid)
        base = seed or (int(time.time()) % 99991)
        k = 0
        for eng in engines:
            for i in range(n):
                k += 1
                _log(jid, "take %d/%d %s seed %d" % (k, len(engines) * n, eng, base + i))
                try:
                    _render_take(jid, f, sh, eng, base + i)
                except Exception as e:
                    _log(jid, "FAILED %s: %s" % (eng, str(e)[:160]))
                    with _LOCK:
                        JOBS[jid]["error"] = str(e)[:200]
                with _LOCK:
                    JOBS[jid]["done"] += 1
        _finish(jid, JOBS[jid].get("error", ""))
    except Exception as e:
        _finish(jid, str(e)[:300])


def takes(data):
    engines = [e for e in (data.get("engines") or ["ltx"]) if e in ("ltx", "h3", "wan", "cam")]
    n = max(1, min(int(data.get("n") or 1), 4))
    jid = _job("takes", total=len(engines) * n, film=data["film"], shot=data["shot"])
    threading.Thread(target=_takes_job,
                     args=(jid, data["film"], data["shot"], engines, n,
                           int(data.get("seed") or 0)), daemon=True).start()
    return {"job": jid}, 200


# ─── auto-next ──────────────────────────────────────────────────────────────────────

_PROGRESSION = {"wide establishing shot": "medium shot", "wide shot": "medium shot",
                "medium shot": "close-up", "medium two-shot": "close-up",
                "close-up": "medium shot", "tight close-up": "medium shot",
                "over-the-shoulder shot": "close-up", "low-angle shot": "wide shot",
                "high-angle shot": "medium shot", "overhead view": "wide shot",
                "extreme macro shot": "wide shot", "low tracking shot": "medium shot"}


def auto_next(data):
    """A DRAFT of the next shot, derived from the previous one: the anchor continues from
    the picked take's last frame, the framing advances one step (wide -> medium -> close
    and back out), and with two characters present the subject alternates - a plain
    shot-reverse-shot. A heuristic, not an oracle: it exists to be edited."""
    f = F.load(data["film"])
    prev = f.shot(data["shot"])
    sc = f.scene(prev["scene"])
    lastbeat = (prev.get("beats") or [{}])[-1]
    framing = _PROGRESSION.get(lastbeat.get("framing") or "wide shot", "medium shot")
    subject = lastbeat.get("subject") or ""
    present = [c for c in (sc.get("cast_present") or []) if c in f.data["cast"]]
    if len(present) >= 2 and subject in present:
        subject = next((c for c in present if c != subject), subject)
    sh = f.new_shot(prev["scene"], after=prev["id"],
                    title="after %s" % prev.get("title", prev["id"]),
                    duration=prev.get("duration", 6),
                    anchor="prev_last" if prev.get("picked") else "scene",
                    beats=[{"framing": framing, "move": "static", "transition_in": "",
                            "subject": subject,
                            "action": "continues from the previous shot - describe the "
                                      "next beat",
                            "background": lastbeat.get("background") or "",
                            "dialogue": {"char": "", "line": "", "delivery": ""}}],
                    sfx=prev.get("sfx") or "")
    return {"ok": True, "id": sh["id"],
            "note": "draft: anchor=%s, framing=%s, subject=%s"
                    % (sh["anchor"], framing, subject or "-")}, 200


# ─── dialogue VO (consistent character voices) ──────────────────────────────────────

FEMALE_VOICES = ["female_03_alice", "female_04_maya", "female_01", "female_02", "en_woman", "mabel"]
MALE_VOICES = ["male_02", "male_03_carter", "male_01", "male_04_frank", "male_05_samuel", "en_man", "vex"]


def _voice_ready(vid):
    p = os.path.join(STUDIO, "voices", (vid or "") + ".json")
    try:
        return bool(vid) and json.load(open(p, encoding="utf-8")).get("status") == "ready"
    except Exception:
        return False


def _default_voice(f, cast_id):
    """A READY synthetic pack for a cast member without one, chosen by the pack's
    archetype and fixed by the cast id, so the character keeps it across films."""
    ent = (f.data.get("cast") or {}).get(cast_id) or {}
    arche = ""
    try:
        import importlib.util
        p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "foundry.py")
        spec = importlib.util.spec_from_file_location("fy_mod6", p)
        FY = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(FY)
        cid = ent.get("foundry") or _foundry_for(f, cast_id, FY)
        if cid:
            arche = ((FY.load_asset("character", cid).get("selections") or {}).get("archetype") or "")
    except Exception:
        arche = ""
    pool = FEMALE_VOICES if "female" in arche else MALE_VOICES if "male" in arche else (FEMALE_VOICES + MALE_VOICES)
    pool = [v for v in pool if _voice_ready(v)] or [v for v in FEMALE_VOICES + MALE_VOICES if _voice_ready(v)]
    if not pool:
        return ""
    h = sum(ord(c) for c in cast_id) % len(pool)
    return pool[h]


def _inherit_qc(take):
    """the picture's notes still hold for its voiced copy; the speech notes do not"""
    return [n for n in (take.get("qc") or [])
            if "spoken" not in n and "silent" not in n and "no sound" not in n]


def _faults(take):
    """notes that count against a take; 'ends closer' is information, not a fault"""
    return [n for n in (take.get("qc") or []) if not n.startswith("ends closer")]


def _cleanest(sh, takes):
    """the automatic pick: for a shot with a line only voiced takes are eligible
    (when any exist); then fewest faults, then the newest"""
    has_line = any(((b.get("dialogue") or {}).get("line") or "").strip() for b in (sh.get("beats") or []))
    pool = [t for t in takes if (t.get("engine") or "").endswith("+vo")] if has_line else []
    pool = pool or list(takes)
    return sorted(pool, key=lambda t: (len(_faults(t)), -len(t["id"]), t["id"]))[0]


def _vo_job(jid, fid, shid, tid, duck=0.35):
    run, set_path, load_wf, ensure_local, HOST, COMFY = _comfy()
    try:
        f = F.load(fid)
        sh = f.shot(shid)
        take = next((t for t in sh["takes"] if t["id"] == tid), None)
        if not take:
            raise RuntimeError("no such take")
        beats_all = sh.get("beats") or []
        lines = [(i, (b.get("dialogue") or {})) for i, b in enumerate(beats_all)]
        lines = [(i, d) for i, d in lines if (d.get("line") or "").strip()]
        if not lines:
            raise RuntimeError("shot has no dialogue lines")
        if not ensure_comfy():
            raise RuntimeError("ComfyUI will not come up")
        vo_paths = []
        for n_, (bi, d) in enumerate(lines):
            i = n_
            ch = f.data["cast"].get(d.get("char") or "") or {}
            vid = ch.get("voice") or ""
            if not _voice_ready(vid):
                # no voice, or a blocked one: pick a ready synthetic pack by archetype
                # and remember it on the cast entry
                vid = _default_voice(f, d.get("char") or "")
                if vid and ch:
                    ch["voice"] = vid
                    f.save()
                    _log(jid, "%s has no voice pack - using %s" % (d.get("char"), vid))
            vmeta = {}
            vp = os.path.join(STUDIO, "voices", vid + ".json")
            if vid and os.path.exists(vp):
                vmeta = json.load(open(vp, encoding="utf-8"))
            if not vmeta or vmeta.get("status") != "ready":
                raise RuntimeError("character %r has no READY voice pack (blocked packs "
                                   "are never used)" % (d.get("char") or "?"))
            wf = load_wf("17_higgs_v3_voice.json")
            set_path(wf, "30.inputs.text", d["line"])
            set_path(wf, "30.inputs.narrator_voice", vmeta["file"])
            set_path(wf, "30.inputs.seed", 4242)
            set_path(wf, "40.inputs.filename_prefix",
                     "claude-generated/films/%s/vo_%s_%d" % (fid, shid, i))
            _, outs = run(HOST, wf, quiet=True)
            auds = [o for o in outs or [] if o.endswith((".wav", ".mp3", ".flac"))]
            if not auds:
                raise RuntimeError("voice render returned nothing")
            vo = os.path.join(f.dir, "assets", "vo_%s_%s_%d%s"
                              % (shid, tid, i, os.path.splitext(auds[0])[1]))
            ensure_local(auds[0], vo)
            vo_paths.append(vo)
            _log(jid, "line %d voiced (%s)" % (i + 1, vmeta.get("name")))
        # mix: native track ducked under the VO lines laid end to end from 0.6s
        src = os.path.join(f.dir, take["file"])
        rel = take["file"][:-4] + "_vo.mp4"
        dest = os.path.join(f.dir, rel)
        inputs, fc, amix = ["-i", src], [], "[a0]"
        for i, vp in enumerate(vo_paths):
            inputs += ["-i", vp]
        fc.append("[0:a]volume=%.2f[a0]" % duck)
        # each line starts where its BEAT starts (beats divide the shot evenly on LTX),
        # nudged 0.4s in so the cut lands first and the voice follows it
        tdur = _dur(src)
        nb = max(len(beats_all), 1)
        floor = 0.0
        for i in range(len(vo_paths)):
            bi = lines[i][0]
            at = max(bi * (tdur / nb) + 0.4, floor)
            fc.append("[%d:a]adelay=%d|%d,volume=1.0[v%d]"
                      % (i + 1, int(at * 1000), int(at * 1000), i))
            amix += "[v%d]" % i
            floor = at + _dur(vo_paths[i]) + 0.3
        fc.append("%samix=inputs=%d:duration=first:normalize=0[out]"
                  % (amix, len(vo_paths) + 1))
        r = _sh("ffmpeg", "-y", "-v", "error", *inputs,
                "-filter_complex", ";".join(fc), "-map", "0:v", "-map", "[out]",
                "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", dest)
        if not os.path.exists(dest):
            raise RuntimeError("mix failed: %s" % r.stderr[-160:])
        _thumbs(dest, dest[:-4])
        take2 = dict(take)
        take2.update({"id": take["id"] + "v", "engine": take["engine"] + "+vo",
                      "file": rel, "poster": rel[:-4] + ".png",
                      "strip": rel[:-4] + "_strip.png", "qc": _qc(dest) + _inherit_qc(take),
                      "created": time.strftime("%H:%M")})
        f2 = F.load(fid)
        sh2 = f2.shot(shid)
        sh2["takes"].append(take2)
        # a VO variant of the picked take supersedes it - that is what the button is for
        if sh2.get("picked") == take["id"] and not take2["qc"]:
            sh2["picked"] = take2["id"]
        f2.save()
        _finish(jid)
    except Exception as e:
        _finish(jid, str(e)[:300])


def vo_mix(data):
    jid = _job("vo", film=data["film"], shot=data["shot"])
    threading.Thread(target=_vo_job, args=(jid, data["film"], data["shot"],
                                           data["take"]), daemon=True).start()
    return {"job": jid}, 200


# ─── the master pass ────────────────────────────────────────────────────────────────

def _master_job(jid, fid, shid):
    """Finish the picked take: FILM interpolation to 48fps with the audio re-muxed. Lands
    as a new immutable take that supersedes the pick - drafts stay cheap, keepers get
    finished."""
    try:
        f = F.load(fid)
        sh = f.shot(shid)
        take = next((t for t in sh["takes"] if t["id"] == sh.get("picked")), None)
        if not take:
            raise RuntimeError("no picked take to master")
        if take.get("fps", 24) >= 47:
            raise RuntimeError("picked take is already 48fps")
        src = os.path.join(f.dir, take["file"])
        if _dur(src) > 25:
            raise RuntimeError("interpolation ceiling is 25s - master the shots, not "
                               "an assembly")
        if not ensure_comfy():
            raise RuntimeError("ComfyUI will not come up")
        pol = _polish_mod()
        rel = take["file"][:-4] + "_48.mp4"
        dest = os.path.join(f.dir, rel)
        _log(jid, "interpolating to 48fps")
        out, info = pol.polish(src, dest)
        if not out:
            raise RuntimeError("polish failed: %s" % info)
        _thumbs(dest, dest[:-4])
        take2 = dict(take)
        take2.update({"id": take["id"] + "m", "engine": take["engine"] + "@48",
                      "file": rel, "poster": rel[:-4] + ".png",
                      "strip": rel[:-4] + "_strip.png", "fps": _fps(dest),
                      "duration": round(_dur(dest), 2), "qc": _qc(dest),
                      "created": time.strftime("%H:%M")})
        f2 = F.load(fid)
        sh2 = f2.shot(shid)
        sh2["takes"].append(take2)
        if not take2["qc"]:
            sh2["picked"] = take2["id"]
        f2.save()
        _finish(jid, "" if not take2["qc"] else "QC: " + "; ".join(take2["qc"])[:180])
    except Exception as e:
        _finish(jid, str(e)[:300])


def master(data):
    jid = _job("master", film=data["film"], shot=data["shot"])
    threading.Thread(target=_master_job, args=(jid, data["film"], data["shot"]),
                     daemon=True).start()
    return {"job": jid}, 200


def _draftall_job(jid, fid, engines, seed):
    try:
        f = F.load(fid)
        todo = [sh["id"] for sh in f.ordered_shots() if not sh["takes"]]
        with _LOCK:
            JOBS[jid]["total"] = max(len(todo) * len(engines), 1)
        for shid in todo:
            f = F.load(fid)
            sh = f.shot(shid)
            for eng in engines:
                _log(jid, "draft %s %s" % (shid, eng))
                try:
                    _render_take(jid, f, sh, eng, seed)
                except Exception as e:
                    _log(jid, "FAILED %s: %s" % (shid, str(e)[:140]))
                    with _LOCK:
                        JOBS[jid]["error"] = str(e)[:200]
                with _LOCK:
                    JOBS[jid]["done"] += 1
        _finish(jid, JOBS[jid].get("error", ""))
    except Exception as e:
        _finish(jid, str(e)[:300])


def draft_all(data):
    engines = [e for e in (data.get("engines") or ["ltx"]) if e in ("ltx", "h3", "wan", "cam")]
    jid = _job("draftall", film=data["film"])
    threading.Thread(target=_draftall_job,
                     args=(jid, data["film"], engines, int(data.get("seed") or 11)),
                     daemon=True).start()
    return {"job": jid}, 200


def _portrait_job(jid, fid, cid):
    """A portrait card per cast member - the reference the identity route hangs on."""
    run, set_path, load_wf, ensure_local, HOST, COMFY = _comfy()
    try:
        f = F.load(fid)
        ch = f.data["cast"].get(cid)
        if not ch:
            raise RuntimeError("no cast member %r" % cid)
        if not ensure_comfy():
            raise RuntimeError("ComfyUI will not come up")
        dest = os.path.join(f.dir, "assets", "cast_%s.png" % cid)
        if f.data.get("look") == "anime":
            wf = load_wf("22_anime_kf_ipadapter.json")
            set_path(wf, "2.inputs.image", ch.get("sheet") or "")
            set_path(wf, "4.inputs.weight", 0.6 if ch.get("sheet") else 0.0)
            set_path(wf, "5.inputs.text", "%s, head and shoulders portrait, plain "
                     "background, masterpiece, best quality, %s"
                     % (ch["clause"], F.LOOK_ANIME))
            set_path(wf, "6.inputs.text", F.NEG_ANIME)
            set_path(wf, "7.inputs.width", 896)
            set_path(wf, "7.inputs.height", 1216)
            set_path(wf, "8.inputs.seed", 21)
            set_path(wf, "10.inputs.width", 896)
            set_path(wf, "10.inputs.height", 1216)
            set_path(wf, "11.inputs.filename_prefix",
                     "claude-generated/films/%s/cast_%s" % (fid, cid))
        else:
            wf = load_wf("01_qwen_t2i_turbo.json")
            set_path(wf, "10.inputs.text",
                     "A head and shoulders portrait of %s, plain grey background, soft "
                     "key light, natural skin texture, sharp focus. %s"
                     % (ch["clause"], f.data.get("look_clause") or F.LOOK_PHOTO))
            set_path(wf, "11.inputs.text", F.NEG_PHOTO)
            set_path(wf, "12.inputs.width", 896)
            set_path(wf, "12.inputs.height", 1216)
            set_path(wf, "13.inputs.seed", 21)
            set_path(wf, "15.inputs.filename_prefix",
                     "claude-generated/films/%s/cast_%s" % (fid, cid))
        _, outs = run(HOST, wf, quiet=True)
        if not outs:
            raise RuntimeError("no output")
        ensure_local(outs[0], dest)
        f2 = F.load(fid)
        f2.data["cast"][cid]["portrait"] = "assets/cast_%s.png" % cid
        f2.save()
        _finish(jid)
    except Exception as e:
        _finish(jid, str(e)[:300])


def portrait(data):
    jid = _job("portrait", film=data["film"], cast=data["cast"])
    threading.Thread(target=_portrait_job, args=(jid, data["film"], data["cast"]),
                     daemon=True).start()
    return {"job": jid}, 200


# ─── assembly ───────────────────────────────────────────────────────────────────────

def _norm(src, dst, w=1472, h=832, fps=24):
    """Uniform canvas and rate, plus 0.1s audio fades either end: each take generates its
    own ambience texture, and the fades are what stop the texture JUMPING at every cut."""
    d = max(_dur(src), 0.3)
    _sh("ffmpeg", "-y", "-v", "error", "-i", src,
        "-vf", "scale=%d:%d:force_original_aspect_ratio=decrease,"
               "pad=%d:%d:(ow-iw)/2:(oh-ih)/2,fps=%d" % (w, h, w, h, fps),
        "-af", "afade=t=in:st=0:d=0.1,afade=t=out:st=%.2f:d=0.1" % (d - 0.1),
        "-c:v", "libx264", "-crf", "18", "-preset", "veryfast", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2", dst)
    return os.path.exists(dst)


def _xfade(a, b, dst, kind, d=0.5):
    da = _dur(a)
    off = max(da - d, 0.1)
    trans = {"dissolve": "dissolve", "fade": "fade", "dip to black": "fadeblack"}\
        .get(kind, "fade")
    _sh("ffmpeg", "-y", "-v", "error", "-i", a, "-i", b, "-filter_complex",
        "[0:v][1:v]xfade=transition=%s:duration=%s:offset=%s[v];"
        "[0:a][1:a]acrossfade=d=%s[a]" % (trans, d, off, d),
        "-map", "[v]", "-map", "[a]",
        "-c:v", "libx264", "-crf", "18", "-preset", "veryfast", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000", dst)
    return os.path.exists(dst)


def _assemble_job(jid, fid, music_on):
    run, set_path, load_wf, ensure_local, HOST, COMFY = _comfy()
    try:
        f = F.load(fid)
        tmp = os.path.join(f.dir, "assets", "_asm")
        shutil.rmtree(tmp, ignore_errors=True)
        os.makedirs(tmp, exist_ok=True)
        scene_files = []
        picked_files = []
        for sc in f.data["scenes"]:
            for shid in sc["shots"]:
                sh = f.data["shots"].get(shid) or {}
                tk = next((t for t in sh.get("takes", [])
                           if t["id"] == sh.get("picked")), None)
                if tk:
                    picked_files.append(os.path.join(f.dir, tk["file"]))
        # what the picked takes say about themselves, so nothing wrong ships silently
        notes = []
        for sh in f.ordered_shots():
            tk = next((t for t in sh.get("takes") or [] if t["id"] == sh.get("picked")), None)
            if tk and tk.get("qc"):
                notes.append("%s: %s" % (sh["id"], "; ".join(str(q) for q in tk["qc"])[:120]))
        if notes:
            _log(jid, "picked takes with notes (%d): %s" % (len(notes), " | ".join(notes)[:600]))
        else:
            _log(jid, "no picked take reports a fault")
        # the film runs at 48 only when EVERY pick is mastered - a mix would stutter
        target_fps = 48 if picked_files and all(_fps(p) >= 47 for p in picked_files) \
            else 24
        _log(jid, "assembling at %dfps" % target_fps)
        for sc in f.data["scenes"]:
            parts = []
            for shid in sc["shots"]:
                sh = f.data["shots"].get(shid) or {}
                take = next((t for t in sh.get("takes", [])
                             if t["id"] == sh.get("picked")), None)
                if not take:
                    _log(jid, "skip %s - no picked take" % shid)
                    continue
                np = os.path.join(tmp, "n_%s.mp4" % shid)
                if not _norm(os.path.join(f.dir, take["file"]), np,
                             fps=target_fps):
                    raise RuntimeError("normalize failed on %s" % shid)
                parts.append((np, sh.get("transition_out", "cut")))
            if not parts:
                continue
            cur = parts[0][0]
            for i in range(1, len(parts)):
                nxt, kind = parts[i][0], parts[i - 1][1]
                if kind and kind != "cut":
                    out = os.path.join(tmp, "x_%s_%d.mp4" % (sc["id"], i))
                    if not _xfade(cur, nxt, out, kind):
                        raise RuntimeError("xfade failed in %s" % sc["id"])
                    cur = out
                else:
                    lst = os.path.join(tmp, "c_%s_%d.txt" % (sc["id"], i))
                    open(lst, "w").write("file '%s'\nfile '%s'\n" % (cur, nxt))
                    out = os.path.join(tmp, "cc_%s_%d.mp4" % (sc["id"], i))
                    _sh("ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0",
                        "-i", lst, "-c", "copy", out)
                    if not os.path.exists(out):
                        raise RuntimeError("concat failed in %s" % sc["id"])
                    cur = out
            scene_out = os.path.join(tmp, "scene_%s.mp4" % sc["id"])
            shutil.copy(cur, scene_out)
            # scene music: ACE-Step tags mixed under at 0.5, cut to the scene
            tags = (sc.get("music") or "").strip()
            if music_on and tags:
                secs = min(_dur(scene_out), 46.0)
                if not ensure_comfy():
                    raise RuntimeError("ComfyUI will not come up")
                wf = load_wf("06_acestep_music.json")
                set_path(wf, "10.inputs.tags", tags + ", instrumental, no vocals, "
                         "continuous throughout")
                set_path(wf, "11.inputs.seconds", float(int(secs) + 1))
                set_path(wf, "12.inputs.seed", 21)
                set_path(wf, "14.inputs.filename_prefix",
                         "claude-generated/films/%s/music_%s" % (fid, sc["id"]))
                _, outs = run(HOST, wf, quiet=True)
                auds = [o for o in outs or [] if o.endswith((".mp3", ".wav", ".flac"))]
                if auds:
                    mp3 = os.path.join(tmp, "music_%s.mp3" % sc["id"])
                    ensure_local(auds[0], mp3)
                    mixed = os.path.join(tmp, "scenem_%s.mp4" % sc["id"])
                    d = _dur(scene_out)
                    _sh("ffmpeg", "-y", "-v", "error", "-i", scene_out, "-i", mp3,
                        "-filter_complex",
                        "[1:a]atrim=0:%s,asetpts=N/SR/TB,volume=0.5[m];"
                        "[0:a][m]amix=inputs=2:duration=first:normalize=0[a]" % d,
                        "-map", "0:v", "-map", "[a]", "-c:v", "copy",
                        "-c:a", "aac", "-b:a", "192k", mixed)
                    if os.path.exists(mixed):
                        scene_out = mixed
                    _log(jid, "music mixed under %s" % sc["id"])
            scene_files.append(scene_out)
            with _LOCK:
                JOBS[jid]["done"] += 1
        if not scene_files:
            raise RuntimeError("nothing to assemble - pick takes first")
        lst = os.path.join(tmp, "film.txt")
        open(lst, "w").write("".join("file '%s'\n" % p for p in scene_files))
        final = os.path.join(f.dir, "assets", "film.mp4")
        # single-pass loudnorm on the whole film: scenes with dialogue, music beds and
        # raw ambience land at very different levels, and this is the delivery leveller
        _sh("ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", lst,
            "-af", "loudnorm=I=-16:TP=-1.5:LRA=11,alimiter=limit=0.94",
            "-c:v", "libx264", "-crf", "18", "-preset", "veryfast",
            "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", final)
        if not os.path.exists(final):
            raise RuntimeError("final concat failed")
        qc = _qc(final)
        _log(jid, "assembled %.1fs; QC: %s" % (_dur(final), "; ".join(qc) or "clean"))
        _finish(jid, "" if not qc else "QC: " + "; ".join(qc)[:200])
    except Exception as e:
        _finish(jid, str(e)[:300])


def assemble(data):
    f = F.load(data["film"])
    jid = _job("assemble", total=max(len(f.data["scenes"]), 1), film=data["film"])
    threading.Thread(target=_assemble_job,
                     args=(jid, data["film"], bool(data.get("music", True))),
                     daemon=True).start()
    return {"job": jid}, 200


# ─── the compositor, behind a shot ──────────────────────────────────────────────────

def _compose_mod():
    import importlib.util
    p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "compose.py")
    spec = importlib.util.spec_from_file_location("compose_tool", p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _compose_anchor_job(jid, fid, shid, char_id, place_id, plate, view,
                        stand, cx, props=None, framing=None):
    try:
        CM = _compose_mod()
        _log(jid, "composing %s into %s%s" % (
            char_id, place_id,
            (" with " + ", ".join(p.get("id") or p.get("character") for p in props))
            if props else ""))
        if framing == "close":
            if props:
                _log(jid, "a close-up holds one face; the second layer is left out of this shot")
            out, plate_p = CM.compose_close(char_id, place_id, plate, "base_portrait", cx,
                                            quiet=True, stand=stand if stand and stand > 0.15 else 0.22)
        else:
            out, plate_p = CM.compose(char_id, place_id, plate, view, "full", cx,
                                      stand=stand, quiet=True, props=props or None)
        l, r = CM.fidelity(plate_p, out)
        _log(jid, "plate fidelity L=%.4f R=%.4f" % (l, r))
        f = F.load(fid)
        rel = "assets/anchor_shot_%s.png" % shid
        shutil.copy(out, os.path.join(f.dir, rel))
        sh = f.shot(shid)
        sh["anchor"] = "file:" + os.path.join(f.dir, rel)
        # the compositor may have moved her to solid footing; the pin's held
        # geometry must use where she actually stands
        try:
            recipe = json.load(open(os.path.join(os.path.dirname(out), "recipe.json")))
            if recipe.get("stand") is not None:
                if (recipe["stand"], recipe["cx"]) != (stand, cx):
                    _log(jid, "footing moved her to stand %.2f across %.2f (%s)"
                         % (recipe["stand"], recipe["cx"], recipe.get("surface")))
                stand, cx = recipe["stand"], recipe["cx"]
        except Exception:
            pass
        sh["anchor_source"] = {"character": char_id, "framing": framing or "full", "place": place_id,
                               "stand": stand, "cx": cx, "view": ("base_portrait" if framing == "close" else view),
                               "plate": plate_p, "props": props or []}
        f.save()
        with _LOCK:
            JOBS[jid]["result"] = {"anchor": rel, "fidelity": [l, r]}
        _finish(jid)
    except Exception as e:
        _finish(jid, str(e)[:300])


def compose_anchor(data):
    """Composite a foundry character into a foundry place and pin it to a shot."""
    jid = _job("compose", film=data["film"], shot=data["shot"])
    threading.Thread(
        target=_compose_anchor_job,
        args=(jid, data["film"], data["shot"], data["character"],
              data["place"], data.get("plate") or None,
              data.get("view") or "turn_front",
              float(data.get("stand", 0.35)), float(data.get("cx", 0.42)),
              [p for p in (data.get("props") or []) if p.get("id") or p.get("character")],
              data.get("framing") or None),
        daemon=True).start()
    return {"job": jid}, 200


def _pin_job(jid, fid, shid, change, seconds, seed, force=False, hold_feet=None):
    try:
        CM = _compose_mod()
        f = F.load(fid)
        sh = f.shot(shid)
        anchor = str(sh.get("anchor") or "")
        if not anchor.startswith("file:"):
            raise RuntimeError("a pinned shot needs a composed anchor first - "
                               "the end state is an edit of it")
        start = anchor[5:]
        work = os.path.join(f.dir, "assets")
        os.makedirs(work, exist_ok=True)
        pv = sh.get("pin_preview") or {}
        end = os.path.join(f.dir, pv.get("end") or "")
        plate_p = _plate_of(sh, CM)
        if pv.get("change") == change and pv.get("end") and os.path.exists(end):
            # the frame the director looked at is the frame that gets interpolated
            _log(jid, "using the previewed end frame")
        else:
            _log(jid, "editing the end state%s"
                 % (" on the pristine plate" if plate_p else ""))
            end = CM.end_state(start, change,
                               os.path.join(work, "pin_end_%s.png" % shid),
                               plate_path=plate_p, src=sh.get("anchor_source"),
                               hold_feet=hold_feet)
            _log_geom(jid, CM, start, end)
        ok, rate, longest = CM.pin_feasible(start, end, seconds,
                                            on_plate=bool(plate_p))
        _log(jid, "pin rate %.4f/s (floor %.4f), carries %.1fs"
             % (rate, CM.pin_floor(bool(plate_p)), longest))
        if not ok and force:
            _log(jid, "below the floor, pinned anyway on the director's word")
            ok = True
        if not ok:
            raise RuntimeError(
                "the two frames are too alike for %.1fs: %.4f/s, below %.3f the "
                "model invents rather than interpolates. Pick a bigger change or "
                "use %.1fs or less." % (seconds, rate, CM.MIN_PIN_RATE, longest))
        _log(jid, "interpolating on H3")
        tid = "pin_%d" % int(time.time())
        rel = "takes/%s/%s.mp4" % (shid, tid)
        dest = os.path.join(f.dir, rel)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        scene_desc = ""
        try:
            src = sh.get("anchor_source") or {}
            if src.get("place"):
                import importlib.util
                p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "foundry.py")
                spec = importlib.util.spec_from_file_location("fy_mod4", p)
                FY = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(FY)
                place = FY.load_asset("place", src["place"])
                scene_desc = (place.get("compiled") or {}).get("description", "") or ""
        except Exception:
            scene_desc = ""
        prompt = ("%s. The scene is %s, and it stays exactly as it is. The camera does not move."
                  % (change, scene_desc)) if scene_desc else ("%s. The camera does not move." % change)
        _log(jid, "pin prompt: %s" % prompt[:140])
        CM.pin_shot(start, end, prompt, dest, seconds=seconds, seed=seed, force=True)
        f = F.load(fid)
        sh = f.shot(shid)
        sh.setdefault("takes", []).append({
            "id": tid, "engine": "h3-pinned", "file": rel,
            "duration": CM.h3_length(seconds) / 24.0, "fps": 24,
            "seed": seed, "qc": [], "warnings": [],
            "pin": {"change": change, "rate": round(rate, 4),
                    "end": "assets/pin_end_%s.png" % shid}})
        sh["picked"] = tid
        f.save()
        with _LOCK:
            JOBS[jid]["result"] = {"take": tid, "file": rel}
        _finish(jid)
    except Exception as e:
        _finish(jid, str(e)[:300])


def _plate_of(sh, CM):
    """The pristine plate a composed anchor was built on, if we can know it."""
    src = sh.get("anchor_source") or {}
    if src.get("plate") and os.path.exists(str(src["plate"])):
        return src["plate"]
    if src.get("place"):
        try:
            return CM.plate_for(src["place"])
        except Exception:
            return None
    return None


def _log_geom(jid, CM, start, end):
    """What end_state did with the figure, and the change inside its region."""
    try:
        g = json.load(open(end[:-4] + "_geom.json"))
    except Exception:
        return
    if g.get("hold_feet"):
        _log(jid, "end figure held in place: scale %.2f (head %s -> %s px), feet y=%s"
             % (g.get("scale", 1.0), g.get("head_start", "?"), g.get("head_end", "?"),
                g.get("y_feet", "?")))
    elif g.get("rel_scale") is not None:
        _log(jid, "end figure moved: %.2fx the start figure by head width (clamped), "
                  "feet y=%s from y=%s by the plate's depth"
             % (g.get("rel_scale", 1.0), g.get("y_feet", "?"), g.get("y_feet_start", "?")))
    else:
        _log(jid, "end figure keeps the regeneration's placement (moving motion)")
    rb = g.get("raw_box")
    if rb and g.get("y_feet") is not None:
        try:
            from PIL import Image
            W, H = Image.open(end).size
            x0 = max(0, min(rb[0], g["cx"] - (rb[2] - rb[0]) // 2) - 20)
            x1 = min(W, max(rb[2], g["cx"] + (rb[2] - rb[0]) // 2) + 20)
            y0 = max(0, min(rb[1], g["y_feet"] - (rb[3] - rb[1])) - 20)
            y1 = min(H, g["y_feet"] + 20)
            sc = CM.subject_change(start, end, (x0, y0, x1, y1))
            _log(jid, "subject-region change %.3f (logged for calibration, not gating)" % sc)
        except Exception:
            pass


_STOP = set("""a an the and or but of to in on at by for with from into onto over under
across through behind beside between along toward towards against about around as is are
was were be been being it its this that these those there here then while when where who
which what whose very more most some any each every all both few many much other such only
own same so than too can will just also still yet again ever never once now already slowly
gently steadily quickly suddenly softly quietly continuously slightly little few first last
one two three camera frame shot scene background foreground beat light lights lighting
his her their our your my she he they we you them him himself herself itself image picture
start end same before after moment""".split())


SCENE_ASK = (
    "Describe what is physically in this image as a list of nouns: the kind of place, "
    "the main structures and objects, materials, vehicles, plants, water, weather, time "
    "of day, light sources, signs, and any people or animals. Be literal and complete. "
    "Comma-separated nouns and short noun phrases only, no sentences, no apologies.")

_VERBISH = set("""listening listens listen watching watches watch waiting waits wait thinking thinks
think staring stares stare gazing gazes gaze hearing hears hear remembering remembers remember
hesitating hesitates hesitate breathing breathes breathe smiling smiles smile frowning frowns frown
talking talks talk whispering whispers whisper wondering wonders wonder noticing notices notice
falls fall hammers hammer comes come moving moves move drifts drift passes
pass trembling tremble rocking rock spreads spread glittering glitter lapping lap thins thin
softens soften turns turn walks walk reads read unfolds unfold crouches crouch picks pick
running runs run standing stands stand sways sway flickers flicker rises rise sits sit lies
lie looks look reaching reach holding holds hold carrying carries carry crossing crosses cross
lowers lower straightens nods nod laughs laugh speaks speak changing changes change coming
going goes gone leaving leaves flowing flows flow shining shines shine glowing glows glow
hanging hangs hang blowing blows blow hitting hits hit pouring pours pour dripping drips drip
slow slowly quick quickly thick thin narrow wide soaked wet dry empty full gentle gently
steady old young small large big tiny huge distant near close far dark bright dim warm cold
heavy soft hard quiet loud still calm rough smooth deep shallow high low long short early late
beneath below above under over behind between across through along toward towards away
against inside outside around continuous continuously visible invisible
moored swaying sway hazing haze hazy weathered bound black white grey gray red blue green
yellow orange brown dark light pale faint bright wet damp drenched sodden streaked trembling
flickering flicker glittering shimmering rippling drifting rolling curling rising lifting
sitting standing lying leaning waiting watching looking staring holding carrying wearing
empty crowded busy quiet still silent distant nearby far near first last single few several
many more most every each whole entire same other another new old ancient young little big
small large tall short long wide narrow thick thin heavy light soft hard
sodium points point facing faces raises raise sees see steps step closer covered down left
right forward back toward stir stirs town streaks ripples ripple wind breeze gust expression
face hair hand hands arm arms chest head eyes eye shoulder shoulders knee knees feet foot leg
legs body mouth lips brow skin fingers finger""".split())


def _caption_scene(staged):
    """One vision call with a scene question. Same graph as the character
    captioner, different ask; SaveText appended so the answer lands in a file."""
    import glob
    run, set_path, load_wf, ensure_local, HOST, comfy_dir = _comfy()
    wf = load_wf("30_vision_caption.json")
    set_path(wf, "2.inputs.image", staged)
    set_path(wf, "3.inputs.prompt", SCENE_ASK)
    stamp = "anchorcap_%d" % (int(time.time()) % 100000)
    wf["90"] = {"class_type": "SaveText",
                "inputs": {"text": ["3", 0], "filename_prefix": stamp, "format": "txt"}}
    run(HOST, wf, quiet=True)
    hits = sorted(glob.glob(os.path.join(comfy_dir, "output", "**", stamp + "*"),
                            recursive=True))
    return open(hits[-1], encoding="utf-8", errors="replace").read().strip() if hits else ""


# what the prose may call a thing the caption calls otherwise
_SYN = {
    "shrine": ("temple", "building", "structure"), "temple": ("shrine", "building"),
    "cedar": ("tree", "pine", "forest"), "cedars": ("tree", "pine", "forest"),
    "trunk": ("tree", "forest"), "pine": ("tree", "forest"), "willow": ("tree",),
    "moss": ("vegetation", "grass", "stone"), "quay": ("dock", "pier", "harbour", "harbor", "wharf"),
    "harbour": ("harbor", "dock", "boat", "pier"), "harbor": ("harbour", "dock", "boat", "pier"),
    "tarmac": ("asphalt", "road", "street"), "asphalt": ("road", "street", "tarmac"),
    "puddle": ("water", "rain", "wet", "reflection"), "reflection": ("water", "wet", "puddle"),
    "neon": ("sign", "light"), "sign": ("signage", "neon", "text"), "shop": ("store", "storefront"),
    "car": ("vehicle", "traffic"), "vehicle": ("car", "traffic"), "traffic": ("car", "vehicle"),
    "lamp": ("light", "lantern", "streetlight"), "lantern": ("lamp", "light"),
    "river": ("water", "stream", "canal"), "canal": ("water", "river"), "stream": ("water", "river"),
    "arch": ("bridge",), "bridge": ("arch", "footbridge"), "quayside": ("dock", "harbour"),
    "boat": ("ship", "vessel", "hull"), "ship": ("boat", "vessel"), "mist": ("fog", "haze"),
    "fog": ("mist", "haze"), "rain": ("wet", "water", "storm"), "bank": ("shore", "grass", "river"),
    "stone": ("rock", "brick", "masonry"), "iron": ("metal", "steel"), "steel": ("metal", "iron"),
    "wind": ("air",), "letter": ("paper", "envelope"), "envelope": ("paper", "letter"),
    "person": ("man", "woman", "people", "figure"), "woman": ("person", "people", "figure"),
    "man": ("person", "people", "figure"),
    "hull": ("boat", "ship", "vessel"), "rigging": ("rope", "mast", "boat", "ship"),
    "mast": ("boat", "ship", "rigging"), "deck": ("boat", "ship", "wood"),
    "buoy": ("water", "harbour", "harbor"), "quayside": ("dock", "pier"),
    "platform": ("station", "train", "railway"), "canopy": ("roof", "station"),
    "departures": ("board", "sign", "station"), "board": ("sign", "text"),
    "line": ("track", "rail", "railway"), "track": ("rail", "railway", "line"),
    "lamppost": ("lamp", "light", "pole"), "streetlight": ("lamp", "light", "pole"),
    "pole": ("post", "lamp", "mast"), "cable": ("wire",), "wire": ("cable",),
    "awning": ("shop", "storefront", "canopy"), "shutter": ("shop", "storefront", "door"),
    "storefront": ("shop", "store"), "puddles": ("water", "reflection", "wet"),
}


def _content_words(text):
    import re
    out = []
    for w in re.findall(r"[a-zA-Z]+", (text or "").lower()):
        if len(w) < 4 or w in _STOP or w in _VERBISH or w.endswith("ly"):
            continue
        out.append(w)
    return out


def _stem(w):
    for suf in ("ings", "ing", "es", "s", "ed"):
        if w.endswith(suf) and len(w) - len(suf) >= 4:
            return w[:-len(suf)]
    return w


def _anchor_check_job(jid, fid, shid):
    try:
        f = F.load(fid)
        sh = f.shot(shid)
        anchor = _resolve_anchor_file(f, shid, jid)
        _log(jid, "captioning the anchor")
        here = os.path.dirname(os.path.abspath(__file__))
        if here not in sys.path:
            sys.path.insert(0, here)
        _run, _sp, _lw, _el, _host, comfy_dir = _comfy()
        staged = "anchor_check_%d.png" % (int(time.time()) % 100000)
        shutil.copy(anchor, os.path.join(comfy_dir, "input", staged))
        cap = (_caption_scene(staged) or "").strip()
        if not cap:
            raise RuntimeError("the captioner returned nothing")
        flat = f.flat(shid)
        # the shot's own words - not the scene description, which coverage writes
        # from the place and which would flag the same nouns on every shot
        prose = " ".join(
            [(b.get("action") or "") + " " + (b.get("background") or "")
             for b in (sh.get("beats") or [])])
        seen = {_stem(w) for w in _content_words(cap)}
        # the cast is what the compositor put there; their names are not things
        # the picture can lack. Nor are coverage's own blanks.
        cast_words = set()
        for cid, ent in (f.data.get("cast") or {}).items():
            cast_words.add(cid.lower())
            for part in str((ent or {}).get("name") or "").lower().split():
                cast_words.add(part)
            for part in str((ent or {}).get("short") or "").lower().split():
                cast_words.add(part)
        cast_words |= {"describe", "beat", "scene", "lived", "worn", "alive", "detail"}
        missing, dup = [], set()
        for w in _content_words(prose):
            s = _stem(w)
            if w in cast_words or s in cast_words:
                continue
            if s in seen or s in dup:
                continue
            if any(s[:5] == c[:5] for c in seen if len(c) >= 5):
                continue
            syn = _SYN.get(w, ()) + _SYN.get(s, ())
            if any(_stem(x) in seen or x in seen for x in syn):
                continue
            dup.add(s)
            missing.append(w)
        _log(jid, "caption: %s" % cap[:160])
        _log(jid, ("not in the anchor: %s" % ", ".join(missing)) if missing
             else "every content word in the prose is also in the caption")
        f = F.load(fid)
        sh = f.shot(shid)
        sh["anchor_check"] = {"caption": cap, "missing": missing,
                              "when": int(time.time())}
        f.save()
        with _LOCK:
            JOBS[jid]["result"] = dict(sh["anchor_check"])
        _finish(jid)
    except Exception as e:
        _finish(jid, str(e)[:300])


def anchor_check(data):
    """Caption the shot's anchor and list the prose words it does not contain."""
    jid = _job("anchorcheck", film=data["film"], shot=data["shot"])
    threading.Thread(target=_anchor_check_job,
                     args=(jid, data["film"], data["shot"]), daemon=True).start()
    return {"job": jid}, 200


# ─── coverage: the standard shots of a scene, from selectors ─────────────────────────

def _ambient_for(weather, place_sel):
    w = (weather or "").lower()
    amb = ["light"]
    if "rain" in w or "storm" in w:
        amb.append("rain")
    if "snow" in w:
        amb.append("snow")
    if "wind" in w or "storm" in w:
        amb.append("cloth")
    base = (place_sel or {}).get("base", "")
    if base in ("boat", "beach", "bridge") or "harbour" in base or "harbor" in base:
        amb.append("water")
    if base in ("market", "station", "cityscape", "cafe_exterior") and \
            (place_sel or {}).get("crowd") in ("sparse", "busy"):
        amb.append("crowd")
    return amb


def _coverage_job(jid, fid, scid, place_id, plate, chars, prop):
    """chars: [{"cast": "MARA", "foundry": "mara-okonjo"}] (1-2). Creates the shots,
    composes the anchors one after another, checks each against its prose."""
    try:
        CM = _compose_mod()
        f = F.load(fid)
        sc = f.scene(scid)
        import importlib.util
        p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "foundry.py")
        spec = importlib.util.spec_from_file_location("fy_mod2", p)
        FY = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(FY)
        place = FY.load_asset("place", place_id)
        psel = place.get("selections") or {}
        pdesc = (place.get("compiled") or {}).get("description", "") or place.get("name", place_id)
        plate_p = CM.plate_for(place_id, plate or None)
        sc["place"], sc["plate"] = place_id, os.path.basename(plate_p)[:-4]
        detail = None
        try:
            detail = CM.plate_for(place_id, os.path.basename(plate_p).replace("_wide", "_detail")[:-4])
        except Exception:
            detail = None
        amb = _ambient_for(sc.get("weather") or psel.get("weather"), psel)
        a, b = (chars + [None, None])[:2]
        names = [c["cast"] for c in chars]
        # remember the foundry pack on the cast entry, so the next coverage needs no asking
        for c in chars:
            ent = f.data["cast"].get(c["cast"])
            if ent is not None and c.get("foundry"):
                ent["foundry"] = c["foundry"]
        made = []

        def shot(title, dur, beats, anchor=None, no_people=False, sfx=""):
            sh = f.new_shot(scid, title=title, duration=dur, beats=beats, sfx=sfx,
                            anchor=anchor or "scene", no_people=no_people,
                            transition_out="cut")
            made.append(sh["id"])
            return sh

        def beat(framing, subject, action, bg):
            return {"framing": framing, "move": "static", "transition_in": "",
                    "subject": subject, "action": action, "background": bg,
                    "motion": "", "ambient": amb,
                    "dialogue": {"char": "", "line": "", "delivery": ""}}

        _log(jid, "coverage for %s: %s%s" % (sc.get("title") or scid, ", ".join(names) or "no cast",
                                              (" with " + prop) if prop else ""))
        # 1 the wide, empty
        shot("wide - establishing", 8,
             [beat("wide establishing shot", "", "the place as it is, alive",
                   "what moves here moves: " + ", ".join(amb))],
             anchor="file:" + plate_p, no_people=True, sfx=sc.get("ambience") or "")
        plan = []
        if a:
            # 2 the wide with the cast in it (two-shot when there are two)
            layers = []
            if b:
                layers.append({"character": b["foundry"], "view": "turn_front_three_quarter",
                               "stand": 0.40, "cx": 0.62})
            if prop:
                layers.append({"id": prop, "stand": 0.30, "cx": 0.50 if b else 0.60})
            s2 = shot("wide - %s" % (" and ".join(names)), 6,
                      [beat("wide shot" if not b else "medium two-shot", a["cast"],
                            ("and %s stand in the scene - describe what they do" % b["cast"]) if b
                            else "stands in the scene - describe what they do",
                            "the scene moves behind them")])
            plan.append((s2["id"], a["foundry"], "turn_front_three_quarter" if b else "turn_front",
                         0.40, 0.38 if b else 0.42, layers))
            # 3 single on A
            s3 = shot("medium - %s" % a["cast"], 6,
                      [beat("medium shot", a["cast"], "describe the beat", "the scene moves behind them")])
            plan.append((s3["id"], a["foundry"], "turn_front", 0.22, 0.45, []))
            # 4 single on B
            if b:
                s4 = shot("medium - %s" % b["cast"], 6,
                          [beat("medium shot", b["cast"], "describe the beat", "the scene moves behind them")])
                plan.append((s4["id"], b["foundry"], "turn_front", 0.22, 0.50, []))
        # 5 the insert
        if detail and os.path.exists(detail):
            shot("insert - detail", 6,
                 [beat("wide shot", "", "a close detail of the place", "what moves here moves: " + ", ".join(amb))],
                 anchor="file:" + detail, no_people=True, sfx=sc.get("ambience") or "")
        f.save()
        _log(jid, "%d shots created: %s" % (len(made), ", ".join(made)))
        for shid, cid, view, stand, cx, layers in plan:
            sub = _job("compose", film=fid, shot=shid)
            _log(jid, "composing %s for %s" % (cid, shid))
            _compose_anchor_job(sub, fid, shid, cid, place_id, plate or None, view, stand, cx,
                                layers or None)
            with _LOCK:
                err = JOBS.get(sub, {}).get("error")
            if err:
                _log(jid, "  compose failed on %s: %s" % (shid, err))
        for shid in made:
            sub = _job("anchorcheck", film=fid, shot=shid)
            _anchor_check_job(sub, fid, shid)
            with _LOCK:
                res = JOBS.get(sub, {}).get("result") or {}
            if res.get("missing"):
                _log(jid, "  %s: prose names what the anchor lacks: %s"
                     % (shid, ", ".join(res["missing"][:6])))
        with _LOCK:
            JOBS[jid]["result"] = {"shots": made}
        _finish(jid)
    except Exception as e:
        traceback.print_exc()
        _finish(jid, str(e)[:300])


def coverage(data):
    """Standard coverage for a scene from selectors: place (+plate), one or two
    cast members with their foundry packs, an optional prop."""
    chars = [c for c in (data.get("characters") or []) if c.get("cast") and c.get("foundry")][:2]
    jid = _job("coverage", film=data["film"], scene=data["scene"])
    threading.Thread(target=_coverage_job,
                     args=(jid, data["film"], data["scene"], data["place"],
                           data.get("plate") or None, chars, data.get("prop") or None),
                     daemon=True).start()
    return {"job": jid}, 200


# ─── make this shot: the one button ────────────────────────────────────────────────

IN_PLACE = ("crouch", "crouching", "rise", "turn_to", "look_up", "look_off", "reach",
            "gesture", "nod", "laugh", "recoil", "stumble", "speak")


def _foundry_for(f, cast_id, FY):
    """The foundry pack behind a cast entry: recorded, or matched by name."""
    ent = (f.data.get("cast") or {}).get(cast_id) or {}
    if ent.get("foundry"):
        return ent["foundry"]
    name = (ent.get("name") or cast_id).strip().lower()
    for a in FY.list_assets("character"):
        if a["id"] == name.replace(" ", "-") or (a.get("name") or "").strip().lower() == name:
            return a["id"]
    return None


def _make_job(jid, fid, shid, seconds=None, seed=0, variants=1):
    try:
        import importlib.util, random
        f = F.load(fid)
        sh = f.shot(shid)
        sc = f.scene(sh["scene"])
        beats = sh.get("beats") or []
        b = beats[0] if beats else {}
        subject = (b.get("subject") or "").strip()
        p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "foundry.py")
        spec = importlib.util.spec_from_file_location("fy_mod3", p)
        FY = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(FY)
        cast_ids = set((f.data.get("cast") or {}).keys())
        dur = float(seconds or sh.get("duration") or 6)

        # 1 the character into the scene
        if subject in cast_ids and not sh.get("anchor_source"):
            cid = _foundry_for(f, subject, FY)
            place, plate = sc.get("place"), sc.get("plate")
            if not (place and plate):
                anc = str(sh.get("anchor") or "")
                m = re.search(r"/foundry/places/([^/]+)/([^/]+)\.png$", anc)
                if m:
                    place, plate = m.group(1), m.group(2)
            if not cid:
                raise RuntimeError("%s has no character pack yet - build one on the "
                                   "Characters page, then try again" % subject)
            if not (place and plate):
                raise RuntimeError("this scene has no place yet - pick one on the Scene "
                                   "tab (place and background picture), then try again")
            others = [c for c in cast_ids if c != subject and c in
                      (" ".join([b.get("action", ""), b.get("background", "")])).upper().split()]
            layers = []
            for o in others[:1]:
                oc = _foundry_for(f, o, FY)
                if oc:
                    layers.append({"character": oc, "view": "turn_front_three_quarter",
                                   "stand": 0.35, "cx": 0.62})
            _log(jid, "putting %s into %s%s" % (subject, sc.get("title") or place,
                                                (" with " + others[0]) if layers else ""))
            sub = _job("compose", film=fid, shot=shid)
            _compose_anchor_job(sub, fid, shid, cid, place, plate,
                                "turn_front_three_quarter" if layers else "turn_front",
                                0.35, 0.38 if layers else 0.42, layers or None)
            with _LOCK:
                err = JOBS.get(sub, {}).get("error")
            if err:
                raise RuntimeError("could not put %s into the scene: %s" % (subject, err))
            f = F.load(fid)
            sh = f.shot(shid)
        elif subject and subject not in cast_ids:
            _log(jid, "'%s' is not in the cast, so the words describe them; add them to "
                      "the cast (Film tab) to use a character pack" % subject)

        # 2 the words against the picture
        missing_words = []
        if sh.get("anchor") or sh.get("anchor_source") or (sc.get("anchor")):
            sub = _job("anchorcheck", film=fid, shot=shid)
            _log(jid, "checking the words against the picture")
            _anchor_check_job(sub, fid, shid)
            with _LOCK:
                res = JOBS.get(sub, {}).get("result") or {}
            if res.get("missing"):
                _log(jid, "the picture does not show: %s - the shot may drift toward them"
                     % ", ".join(res["missing"][:6]))
                missing_words = list(res["missing"][:6])
            else:
                _log(jid, "the words match the picture")
            f = F.load(fid)
            sh = f.shot(shid)

        # 3 animate a pose change, or render
        motion = (b.get("motion") or "").strip()
        done = False
        if motion in IN_PLACE and sh.get("anchor_source") and (sh.get("anchor_source") or {}).get("framing") != "close":
            end = F.motion_option("action", motion).get("end") or ""
            change = ("the subject " + end) if end else (b.get("action") or "")
            secs = min(dur, 8.0)
            _log(jid, "animating the pose change (%s, %.0fs): first the end pose" % (motion, secs))
            sub = _job("pinpreview", film=fid, shot=shid)
            _pin_preview_job(sub, fid, shid, change, secs, 11, True)
            f = F.load(fid)
            sh = f.shot(shid)
            pv = sh.get("pin_preview") or {}
            if pv.get("ok"):
                sub = _job("pin", film=fid, shot=shid)
                _log(jid, "interpolating between the two poses")
                _pin_job(sub, fid, shid, change, secs, 42, False, True)
                with _LOCK:
                    err = JOBS.get(sub, {}).get("error")
                if not err:
                    done = True
                else:
                    _log(jid, "the pose change did not take (%s) - rendering instead" % err[:80])
            else:
                _log(jid, "too small a change to animate as a pose (%.4f/s, floor %.4f) - "
                          "rendering instead; forced pins below the floor came back wrong"
                     % (pv.get("rate", 0), 0.002))
        if not done:
            f = F.load(fid)
            sh = f.shot(shid)
            _log(jid, "rendering the shot (%.0fs)" % dur)
            _render_take(jid, f, sh, "ltx", seed or random.randint(1, 10 ** 9))
            f = F.load(fid)
            sh = f.shot(shid)
            takes = sorted(sh.get("takes") or [], key=lambda t: t["id"])
            newest = takes[-1] if takes else None
            if newest and any(str(q).startswith(("scene drift", "the line may not", "people appeared", "audio is effectively SILENT")) for q in newest.get("qc") or []):
                _log(jid, "the take has a fault (%s) - rendering once more on a new seed"
                     % ("; ".join(newest.get("qc") or [])[:80]))
                _render_take(jid, f, sh, "ltx", random.randint(1, 10 ** 9))
                f = F.load(fid)
                sh = f.shot(shid)
                takes = sorted(sh.get("takes") or [], key=lambda t: t["id"])
                cands = takes[-2:]
                newest = sorted(cands, key=lambda t: (len(t.get("qc") or []),
                                                      (t.get("drift") or {}).get("lost", 0)))[0]
            if newest and any(str(q).startswith("people appeared") for q in newest.get("qc") or []):
                # generation keeps filling the empty frame; the rig cannot
                _log(jid, "the picture kept growing people - this shot becomes the plate itself, "
                          "moving slowly, with the rendered sound under it")
                try:
                    f = F.load(fid)
                    sh = f.shot(shid)
                    prev_cam = sh.get("cam")
                    # the rig's default window is sized for a 4K plate; on our plates it
                    # covered the whole image and the push showed nothing. Window = the
                    # plate itself, centred, pushing in 12% over the shot's own length.
                    try:
                        from PIL import Image as _Im
                        _pw, _ph = _Im.open(_resolve_anchor_file(f, shid, jid)).size
                    except Exception:
                        _pw, _ph = 1216, 832
                    sh["cam"] = {"rig": "still_push", "audio": os.path.join(f.dir, newest["file"]),
                                 "params": {"seconds": float(sh.get("duration") or dur), "zoom_start": 1.0,
                                            "zoom_end": 1.12, "win_w": _pw, "win_h": _ph,
                                            "cx": _pw // 2, "cy": _ph // 2}}
                    f.save()
                    _render_take(jid, f, sh, "cam", 0)
                    f = F.load(fid)
                    sh = f.shot(shid)
                    sh["cam"] = prev_cam
                    cams = [t for t in sh.get("takes") or [] if t.get("engine") == "cam"]
                    if cams:
                        newest = sorted(cams, key=lambda t: t["id"])[-1]
                        newest.setdefault("qc", [])
                        newest["qc"] = [q for q in newest["qc"] if not str(q).startswith("people appeared")]
                        newest["qc"].append("the plate itself, moving slowly - generation kept adding people")
                    f.save()
                except Exception as e:
                    _log(jid, "rig fallback failed: %s" % str(e)[:120])
            if newest and missing_words:
                note = "words not in the picture: %s" % ", ".join(missing_words)
                for t in takes[-2:]:
                    if note not in (t.get("qc") or []):
                        t.setdefault("qc", []).append(note)
                f.save()
            if newest:
                sh["picked"] = newest["id"]
                f.save()
                _log(jid, "done - %s%s" % (newest["id"], (" (QC: %s)" % "; ".join(newest["qc"]))
                                           if newest.get("qc") else ""))
        else:
            _log(jid, "done - the pose change is the picked take")
        # a line is spoken through the character's voice pack, not left to the engine
        f = F.load(fid)
        sh = f.shot(shid)
        has_line = any(((bb.get("dialogue") or {}).get("line") or "").strip() for bb in (sh.get("beats") or []))
        picked = sh.get("picked")
        if has_line and picked and not str(picked).endswith("v"):
            _log(jid, "voicing the line through the character's voice pack")
            sub = _job("vo", film=fid, shot=shid)
            _vo_job(sub, fid, shid, picked, 0.12)
            with _LOCK:
                err = JOBS.get(sub, {}).get("error")
            if err:
                _log(jid, "the line could not be voiced: %s" % err[:120])
            else:
                f = F.load(fid)
                sh = f.shot(shid)
                vo = [t for t in sh.get("takes") or [] if t["id"] == picked + "v"]
                if vo:
                    sh["picked"] = vo[0]["id"]
                    f.save()
                    _log(jid, "done - the voiced take is picked")
        # more variants: same anchor, same promises, new seeds
        for k in range(1, max(1, int(variants or 1))):
            f = F.load(fid)
            sh = f.shot(shid)
            _log(jid, "variant %d: rendering on a new seed" % (k + 1))
            _render_take(jid, f, sh, "ltx", random.randint(1, 10 ** 9))
        if int(variants or 1) > 1:
            f = F.load(fid)
            sh = f.shot(shid)
            takes = sh.get("takes") or []
            if takes:
                best = _cleanest(sh, takes)
                sh["picked"] = best["id"]
                f.save()
                _log(jid, "%d variants; picked %s (%s)" % (len(takes), best["id"],
                                                             "; ".join(best.get("qc") or []) or "no faults"))
        with _LOCK:
            JOBS[jid]["result"] = {"shot": shid}
        _finish(jid)
    except Exception as e:
        traceback.print_exc()
        _finish(jid, str(e)[:300])


def _make_all_job(jid, fid, assemble):
    try:
        f = F.load(fid)
        todo = [sh["id"] for sh in f.ordered_shots() if not sh.get("picked")]
        with _LOCK:
            JOBS[jid]["total"] = max(len(todo) + (1 if assemble else 0), 1)
        _log(jid, "%d shot(s) to make" % len(todo))
        for shid in todo:
            sub = _job("make", film=fid, shot=shid)
            _log(jid, "-- shot %s" % shid)
            _make_job(sub, fid, shid)
            with _LOCK:
                err = JOBS.get(sub, {}).get("error")
                lines = list(JOBS.get(sub, {}).get("log") or [])
                JOBS[jid]["done"] += 1
            for l in lines[-3:]:
                _log(jid, "   " + l)
            if err:
                _log(jid, "   shot %s did not finish: %s" % (shid, err[:120]))
        if assemble:
            _log(jid, "-- assembling the film")
            sub = _job("assemble", film=fid)
            _assemble_job(sub, fid, True)
            with _LOCK:
                err = JOBS.get(sub, {}).get("error")
                JOBS[jid]["done"] += 1
            _log(jid, "assembled" if not err else "assembly failed: %s" % err[:120])
        with _LOCK:
            JOBS[jid]["result"] = {"made": todo}
        _finish(jid)
    except Exception as e:
        traceback.print_exc()
        _finish(jid, str(e)[:300])


def make_all(data):
    """Make every shot without a picked take, in order, then assemble."""
    jid = _job("makeall", film=data["film"])
    threading.Thread(target=_make_all_job,
                     args=(jid, data["film"], bool(data.get("assemble", True))),
                     daemon=True).start()
    return {"job": jid}, 200


def _cast_entry_from_pack(FY, cid):
    a = FY.load_asset("character", cid)
    c = a.get("compiled") or {}
    cdir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "foundry", "characters", cid)
    return {"name": a.get("name", cid), "clause": c.get("clause", ""),
            "short": c.get("short", "") or a.get("name", cid).split()[0],
            "sheet": os.path.join(cdir, "base_portrait.png"),
            "portrait": os.path.join(cdir, "base_portrait.png"),
            "voice": "", "voice_desc": c.get("voice", "") or "", "foundry": cid}


def _quickstart_job(jid, fid, scid, place, plate, chars, prop):
    _coverage_job(jid, fid, scid, place, plate, chars, prop)


def quickstart(data):
    """Film + cast from packs + first scene with its place + coverage, from one form."""
    import importlib.util
    p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "foundry.py")
    spec = importlib.util.spec_from_file_location("fy_mod5", p)
    FY = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(FY)
    f = F.new_film(data["title"], look=data.get("look", "photoreal"),
                   resolution=data.get("resolution", "auto"))
    fid = f.id
    chars = []
    for cid in [c for c in (data.get("characters") or []) if c][:2]:
        try:
            ent = _cast_entry_from_pack(FY, cid)
        except Exception:
            continue
        # the cast id comes from the NAME (RENJI, INES, KEEPER), never from the
        # appearance clause - "black-haired man" made a cast member called BLACK
        words = [w for w in re.findall(r"[A-Za-z]+", ent["name"] or cid)]
        roles = {"master", "keeper", "seller", "ferryman", "captain", "doctor", "officer", "guard",
                 "teacher", "king", "queen", "prince", "princess", "priest", "monk", "nurse",
                 "driver", "pilot", "sailor", "soldier", "knight", "merchant", "boy", "girl",
                 "man", "woman", "stranger", "traveller", "traveler", "child", "elder"}
        skip = {"the", "a", "an", "mr", "mrs", "ms", "dr"}
        core = [w for w in words if w.lower() not in skip] or words or [cid]
        if any(w.lower() in roles for w in core):
            cast_id = "_".join(w.upper() for w in core)[:24]      # STATION_MASTER, OLD_SHRINE_KEEPER
        else:
            cast_id = core[0].upper()[:12]                          # INES, RENJI
        n = 2
        while cast_id in f.data["cast"]:
            cast_id = "%s%d" % (cast_id.rstrip("0123456789"), n); n += 1
        f.data["cast"][cast_id] = ent
        chars.append({"cast": cast_id, "foundry": cid})
    place = data.get("place") or ""
    plate = data.get("plate") or ""
    sc = f.new_scene(data.get("scene_title") or "scene 1")
    if place:
        try:
            place_a = FY.load_asset("place", place)
            sel = place_a.get("selections") or {}
            sc["location"] = (place_a.get("compiled") or {}).get("description", "") or place_a.get("name", "")
            sc["weather"] = sel.get("weather", "")
            sc["time_of_day"] = (sel.get("time_of_day") or [""])[0] if isinstance(sel.get("time_of_day"), list) else (sel.get("time_of_day") or "")
            beds = {"school": "distant voices in corridors, a bell far off, birds outside",
                    "classroom": "a clock ticking, chalk on a board, muffled voices beyond the door",
                    "park": "wind in the trees, birds, distant traffic", "house": "a clock, a fridge hum, the street outside",
                    "boat": "water against the hull, rope creaking, gulls", "cityscape": "traffic, distant sirens, footsteps",
                    "library": "pages turning, a chair creaking, the hush of a large room",
                    "market": "voices haggling, a cart wheel, cloth flapping", "rooftops": "wind, distant traffic, a flag snapping",
                    "alley": "dripping water, a fan humming, distant traffic", "temple": "wind in high trees, a bell, water",
                    "beach": "waves, wind, gulls", "forest": "wind in leaves, birds, a stream",
                    "bridge": "water below, wind, footsteps on planks", "station": "wind under the canopy, a board clicking, a distant train",
                    "diner": "a coffee machine hiss, cutlery, rain on the window", "cafe_exterior": "street chatter, cups, traffic",
                    "cafe_interior": "an espresso machine, cups, low voices"}
            sc["ambience"] = ((place_a.get("compiled") or {}).get("ambience", "") or
                              beds.get(sel.get("base", ""), "wind, distant sounds of the place"))
        except Exception:
            pass
        sc["place"], sc["plate"] = place, plate
    sc["cast_present"] = [c["cast"] for c in chars]
    f.save()
    jid = None
    if place:
        jid = _job("coverage", film=fid, scene=sc["id"])
        threading.Thread(target=_quickstart_job,
                         args=(jid, fid, sc["id"], place, plate or None, chars,
                               data.get("prop") or None), daemon=True).start()
    return {"ok": True, "id": fid, "scene": sc["id"], "job": jid,
            "cast": [c["cast"] for c in chars]}, 200


def delete_film(data):
    """Move the film's folder to studio/films/_trash/<id>-<stamp>. Reversible."""
    fid = data["film"]
    f = F.load(fid)
    trash = os.path.join(F.FILMS, "_trash")
    os.makedirs(trash, exist_ok=True)
    dest = os.path.join(trash, "%s-%d" % (fid, int(time.time())))
    shutil.move(f.dir, dest)
    return {"ok": True, "moved_to": os.path.relpath(dest, F.FILMS)}, 200


FRAMING_STAND = {"wide": 0.40, "medium": 0.22, "close": 0.10}
FRAMING_NAME = {"wide": "wide shot", "medium": "medium shot", "close": "close-up"}
CAMERA_VARIANTS = ["static", "push in", "pan", "pull back"]


def _spec_md(title, beat, built, promises, flair):
    """A spec in the markdown the spec sheet parses (specmd.parse_md)."""
    out = ["# Shot %s" % title, "", "## WHAT HAPPENS", "", beat, "", "## BUILT WITH", "", built, "",
           "## MUST NEVER CHANGE", "", "*These are the promises. They do not change without a conversation.*", ""]
    for p in promises:
        out += ["### %s" % p["title"], p["rule"], "WHY: %s" % p["why"]]
        if p.get("check"):
            out.append("CHECK: %s" % p["check"])
        out.append("")
    out += ["## CAN CHANGE", "", "*Free to move. Add MAKE PERMANENT under any of these to promote it above.*", ""]
    for fl in flair:
        out += ["### %s" % fl["title"], fl["value"], ""]
    return "\n".join(out)


def _write_spec(fid, shid, title, beat, built, promises, flair, jid):
    try:
        sr = _load_sibling("spec_routes")
        body, code = sr.save({"film": fid, "shot": shid,
                              "md": _spec_md(title, beat, built, promises, flair)})
        if code == 200:
            _log(jid, "spec written: %d promises, %d free" % (body.get("invariants", 0), body.get("flair", 0)))
        else:
            _log(jid, "spec not written: %s" % str(body)[:120])
    except Exception as e:
        _log(jid, "spec not written: %s" % str(e)[:120])


def _load_sibling(name):
    import importlib.util
    p = os.path.join(os.path.dirname(os.path.abspath(__file__)), name + ".py")
    spec = importlib.util.spec_from_file_location("sib_" + name, p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _build_job(jid, data):
    try:
        import importlib.util, random
        p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "foundry.py")
        spec = importlib.util.spec_from_file_location("fy_mod7", p)
        FY = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(FY)
        CM = _compose_mod()
        # the film and scene: given, or made
        fid = data.get("film")
        if fid:
            f = F.load(fid)
        else:
            f = F.new_film(data.get("title") or "Shot builds %s" % time.strftime("%m-%d"),
                           look=data.get("look", "photoreal"), resolution=data.get("resolution", "auto"))
            fid = f.id
        place, plate = data.get("place") or "", data.get("plate") or ""
        chars_in = [c for c in (data.get("characters") or []) if c][:2]
        cast_ids = []
        for cid in chars_in:
            if cid in (f.data.get("cast") or {}):
                cast_ids.append(cid); continue
            try:
                ent = _cast_entry_from_pack(FY, cid)
            except Exception:
                _log(jid, "no character pack %r - skipped" % cid); continue
            words = re.findall(r"[A-Za-z]+", ent["name"] or cid)
            core = [w for w in words if w.lower() not in {"the", "a", "an"}] or words
            cast_id = core[0].upper()[:12]
            n = 2
            while cast_id in f.data["cast"] and f.data["cast"][cast_id].get("foundry") != cid:
                cast_id = "%s%d" % (core[0].upper()[:10], n); n += 1
            f.data["cast"][cast_id] = ent
            cast_ids.append(cast_id)
        scid = data.get("scene")
        if not scid:
            sc = f.new_scene(data.get("scene_title") or ("build %s" % time.strftime("%H:%M")))
            scid = sc["id"]
            try:
                pa = FY.load_asset("place", place) if place else {}
                sel = pa.get("selections") or {}
                sc["location"] = (pa.get("compiled") or {}).get("description", "") or place
                sc["weather"] = sel.get("weather", "")
                sc["ambience"] = (pa.get("compiled") or {}).get("ambience", "") or "wind, distant sounds of the place"
            except Exception:
                pass
            sc["place"], sc["plate"], sc["cast_present"] = place, plate, cast_ids
        f.save()
        plate_p = CM.plate_for(place, plate or None) if place else None
        framings = [x for x in (data.get("framings") or ["wide"]) if x in FRAMING_STAND] or ["wide"]
        camera = data.get("camera") or "static"
        motion = (data.get("motion") or "").strip()
        line = (data.get("line") or "").strip()
        who = (data.get("who") or (cast_ids[0] if cast_ids else "")).strip()
        amb = [a for a in (data.get("ambient") or []) if a]
        dur = float(data.get("duration") or 6)
        n = max(1, min(int(data.get("variants") or 3), 6))
        vary = set(data.get("vary") or ["seed"])
        action = (data.get("action") or "").strip()
        made = []
        for fr in framings:
            f = F.load(fid)
            subject = cast_ids[0] if cast_ids else ""
            beat = {"framing": FRAMING_NAME[fr], "move": camera if camera in ("static", "push in", "pull back", "pan", "tilt up", "tilt down", "follow", "circle", "handheld") else "static",
                    "transition_in": "", "subject": subject,
                    "action": action or ("stands in the scene" if subject else "the place as it is, alive"),
                    "background": "what moves here moves: " + ", ".join(amb) if amb else "",
                    "motion": motion, "ambient": amb,
                    "dialogue": {"char": who, "line": line, "delivery": ""} if line else {"char": "", "line": "", "delivery": ""}}
            sh = f.new_shot(scid, title="%s - %s" % (fr, " / ".join(cast_ids) or "empty"), duration=dur,
                            beats=[beat], sfx=(f.scene(scid) or {}).get("ambience") or "",
                            anchor=("file:" + plate_p) if (plate_p and not cast_ids) else "scene",
                            no_people=not cast_ids, transition_out="cut")
            f.save()
            shid = sh["id"]
            made.append(shid)
            _log(jid, "-- %s shot %s" % (fr, shid))
            # the anchor: character into the place, footing checked, whole views only
            if cast_ids and plate_p:
                layers = []
                if len(cast_ids) > 1:
                    oc = (f.data["cast"].get(cast_ids[1]) or {}).get("foundry")
                    if oc:
                        layers.append({"character": oc, "view": "turn_front_three_quarter",
                                       "stand": FRAMING_STAND[fr], "cx": 0.62})
                cid0 = (f.data["cast"].get(cast_ids[0]) or {}).get("foundry")
                sub = _job("compose", film=fid, shot=shid)
                _compose_anchor_job(sub, fid, shid, cid0, place, plate or None,
                                    "turn_front_three_quarter" if layers else "turn_front",
                                    FRAMING_STAND[fr], 0.38 if layers else 0.45, layers or None,
                                    framing=fr)
                with _LOCK:
                    err = JOBS.get(sub, {}).get("error")
                if err:
                    _log(jid, "   could not place the character: %s" % err[:140]); continue
            # the spec: selections as promises
            f = F.load(fid)
            sh = f.shot(shid)
            promises = []
            if cast_ids:
                promises.append({"title": "The people are these people", "rule": "%s%s, from their packs, are in the start picture; no one else."
                                 % (cast_ids[0], (" and " + cast_ids[1]) if len(cast_ids) > 1 else ""),
                                 "why": "identity comes from the composited anchor, not from the engine's prior",
                                 "check": "anchor contains anchor_shot_%s" % shid})
            else:
                promises.append({"title": "Nobody is in the frame", "rule": "The shot is the place alone.",
                                 "why": "an empty shot that grows a person is a different shot",
                                 "check": "qc is clean"})
            if place:
                promises.append({"title": "The place is %s" % place, "rule": "The background is the %s plate %s and stays that place for the whole take."
                                 % (place, plate or "wide"), "why": "words that name what the plate lacks make the engine rewrite it",
                                 "check": "qc is clean"})
            promises.append({"title": "Camera: %s" % camera, "rule": "The camera %s." % ("does not move" if camera in ("static", "pinned") else camera + "s"),
                             "why": "a camera move on LTX is advisory; a pinned shot enforces it", "check": None})
            promises.append({"title": "Length", "rule": "%.0f seconds, within the measured envelope." % dur,
                             "why": "resolution and length trade inside a fixed envelope", "check": "duration between %.1f and %.1f" % (max(0.5, dur - 1.5), dur + 1.5)})
            flair = [{"title": "Seed", "value": "free - the variants differ by seed"},
                     {"title": "Motion", "value": motion or "none named"},
                     {"title": "Ambient", "value": ", ".join(amb) or "none named"}]
            _write_spec(fid, shid, "%s - %s" % (shid, fr), beat["action"], "Make this shot: %s anchor, %s" % ("composed" if cast_ids else "plate", camera), promises, flair, jid)
            # the variants: same anchor, same promises; only what vary allows changes
            for k in range(n):
                f = F.load(fid)
                sh = f.shot(shid)
                if "camera" in vary and k > 0:
                    sh["beats"][0]["move"] = CAMERA_VARIANTS[k % len(CAMERA_VARIANTS)]
                    f.save()
                    _log(jid, "   variant %d: camera %s" % (k + 1, sh["beats"][0]["move"]))
                if k == 0:
                    sub = _job("make", film=fid, shot=shid)
                    _make_job(sub, fid, shid)
                    with _LOCK:
                        err = JOBS.get(sub, {}).get("error")
                    if err:
                        _log(jid, "   variant 1 failed: %s" % err[:120])
                else:
                    _log(jid, "   variant %d: rendering on a new seed" % (k + 1))
                    _render_take(jid, f, sh, "ltx", random.randint(1, 10 ** 9))
                f = F.load(fid)
                sh = f.shot(shid)
                takes = sh.get("takes") or []
                if takes:
                    best = _cleanest(sh, takes)
                    sh["picked"] = best["id"]
                    f.save()
            with _LOCK:
                JOBS[jid]["done"] += 1
        with _LOCK:
            JOBS[jid]["result"] = {"film": fid, "scene": scid, "shots": made}
        _log(jid, "built %d shot(s) with %d variant(s) each" % (len(made), n))
        _finish(jid)
    except Exception as e:
        traceback.print_exc()
        _finish(jid, str(e)[:300])


def build_shot(data):
    """Select; the studio builds the shot and its variants, holding the promises."""
    jid = _job("build", total=max(len(data.get("framings") or ["wide"]), 1), film=data.get("film") or "")
    threading.Thread(target=_build_job, args=(jid, data), daemon=True).start()
    return {"job": jid}, 200


def make_shot(data):
    """Make this shot: character into the scene, words checked, pose change or
    render, picked - in plain words, one button."""
    jid = _job("make", film=data["film"], shot=data["shot"])
    threading.Thread(target=_make_job, args=(jid, data["film"], data["shot"],
                                             data.get("seconds"), int(data.get("seed") or 0),
                                             max(1, min(int(data.get("variants") or 1), 6))),
                     daemon=True).start()
    return {"job": jid}, 200


def _pin_preview_job(jid, fid, shid, change, seconds, seed, hold_feet=None):
    try:
        CM = _compose_mod()
        f = F.load(fid)
        sh = f.shot(shid)
        anchor = str(sh.get("anchor") or "")
        if not anchor.startswith("file:"):
            raise RuntimeError("a pinned shot needs a composed anchor first - "
                               "the end state is an edit of it")
        start = anchor[5:]
        work = os.path.join(f.dir, "assets")
        os.makedirs(work, exist_ok=True)
        rel = "assets/pin_end_%s.png" % shid
        plate_p = _plate_of(sh, CM)
        _log(jid, "editing the end state%s"
             % (" on the pristine plate" if plate_p else ""))
        end = CM.end_state(start, change, os.path.join(f.dir, rel), seed=seed,
                           plate_path=plate_p, src=sh.get("anchor_source"),
                           hold_feet=hold_feet)
        _log_geom(jid, CM, start, end)
        ok, rate, longest = CM.pin_feasible(start, end, seconds,
                                            on_plate=bool(plate_p))
        _log(jid, "pin rate %.4f/s (floor %.4f%s), carries %.1fs"
             % (rate, CM.pin_floor(bool(plate_p)),
                " on the pristine plate" if plate_p else "", longest))
        f = F.load(fid)
        sh = f.shot(shid)
        sh["pin_preview"] = {"change": change, "seconds": seconds, "end": rel,
                             "rate": round(rate, 4), "ok": bool(ok),
                             "longest": round(longest, 1), "seed": seed,
                             "hold_feet": hold_feet, "when": int(time.time())}
        f.save()
        with _LOCK:
            JOBS[jid]["result"] = dict(sh["pin_preview"])
        _finish(jid)
    except Exception as e:
        _finish(jid, str(e)[:300])


def pin_preview(data):
    """Edit the end state and judge feasibility, then stop. Nothing is spent on
    H3 until the director has seen the frame."""
    fid, shid = data["film"], data["shot"]
    change = (data.get("change") or "").strip()
    if not change:
        raise ValueError("say what changes by the end of the shot")
    seconds = float(data.get("seconds") or 8)
    seed = int(data.get("seed") or 11)
    hold = data.get("hold_feet")
    hold_feet = None if hold is None else bool(hold)
    jid = _job("pinpreview", film=fid, shot=shid)
    threading.Thread(target=_pin_preview_job,
                     args=(jid, fid, shid, change, seconds, seed, hold_feet),
                     daemon=True).start()
    return {"ok": True, "job": jid}, 200


def pin_shot(data):
    """Both ends chosen: the shot's anchor, and an edit of it. H3 interpolates."""
    jid = _job("pin", film=data["film"], shot=data["shot"])
    threading.Thread(
        target=_pin_job,
        args=(jid, data["film"], data["shot"], data["change"],
              float(data.get("seconds", 8)), int(data.get("seed", 42)), bool(data.get("force")),
              None if data.get("hold_feet") is None else bool(data.get("hold_feet"))),
        daemon=True).start()
    return {"job": jid}, 200


def foundry_assets(kind=None):
    """What the Shot tab can offer: the foundry's built assets, so the picker
    lists what exists rather than asking anyone to remember ids."""
    import importlib.util
    p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                     "foundry.py")
    spec = importlib.util.spec_from_file_location("fy_mod", p)
    FY = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(FY)
    out = {}
    for t in ("character", "place", "prop"):
        rows = []
        for a in FY.list_assets(t):
            imgs = a.get("images") or {}
            rows.append({"id": a["id"], "name": a["name"],
                         "style": a.get("style", ""),
                         "views": sorted(imgs.keys()),
                         "plates": sorted(v for v in imgs.values()
                                          if not str(v).endswith("_depth.png"))
                         if t == "place" else []})
        out[t] = rows
    return {"assets": out}, 200
