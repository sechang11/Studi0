"""Routes behind /story - the scene-by-scene editor.

Kept out of serve.py because it owns RENDER JOBS, which nothing else in the app does. Every
render runs on a worker thread and reports through a small job table, so the page can ask
four takes for a scene and keep answering while they render.

WHAT THIS DELIBERATELY DOES NOT DO. There is no timeline scrubber and no frame-level
editing. The expensive decisions here are per-scene, not per-frame: which of four takes is
the shot. A list of scenes and a grid of takes is the whole interface, and building the
familiar-looking part first would have cost a week and answered nothing.
"""
import json, os, subprocess, sys, threading, time

TOOLS = os.path.dirname(os.path.abspath(__file__))
STUDIO = os.path.dirname(TOOLS)
ROOT = os.path.dirname(STUDIO)
sys.path.insert(0, STUDIO)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
os.environ.setdefault("COMFY_HOST", "127.0.0.1:8188")

import story as S                                            # noqa: E402

# job id -> {state, scene, want, done, error}. Small and in-memory on purpose: a render
# queue that survives a restart is a different, much larger feature, and this one is
# allowed to be forgotten.
JOBS = {}
_LOCK = threading.Lock()


def _comfy():
    from comfy import run, set_path
    from epic import load_wf, ensure_local, HOST, COMFY
    return run, set_path, load_wf, ensure_local, HOST, COMFY


# ─── reads ──────────────────────────────────────────────────────────────────────────

def list_stories():
    out = []
    if os.path.isdir(S.STORIES):
        for sid in sorted(os.listdir(S.STORIES)):
            try:
                st = S.load(sid)
            except KeyError:
                continue
            scenes = st.all_scenes()
            out.append({
                "id": sid, "title": st.data.get("title", sid),
                "chapters": len(st.chapter_ids()), "scenes": len(scenes),
                "selected": sum(1 for s in scenes if s.selected_id),
                "clips": sum(1 for s in scenes
                             if (s.selected() or None) and s.selected().has("clip")),
            })
    return {"stories": out}, 200


def story_tree(sid):
    st = S.load(sid)
    chapters = []
    for ch in st.chapters():
        scenes = []
        for sc in ch.scenes():
            t = sc.selected()
            rv = sc.rule_violations()
            scenes.append({
                "id": sc.id, "takes": len(sc.takes()),
                "selected": sc.selected_id,
                "has_clip": bool(t and t.has("clip")),
                "thumb": ("/api/story/%s/thumb/%s/%s" % (sid, ch.id, sc.id)) if t and t.has() else None,
                "stale": any(x.stale() for x in sc.takes()),
                "locked": sc.locked,
                "violations": len(rv["violations"]),
                "line": (sc.data.get("say") or sc.data.get("prompt") or "")[:110],
                "who": sc.data.get("who"),
            })
        chapters.append({"id": ch.id, "title": ch.data.get("title", ch.id),
                         "look": ch.data.get("look"), "scenes": scenes,
                         "cues": len(ch.data.get("music") or [])})
    return {"id": sid, "title": st.data.get("title", sid),
            "characters": st.data.get("characters") or {},
            "voices": sorted((st.data.get("voices") or {})),
            "chapters": chapters}, 200


def scene_detail(sid, cid, scid):
    st = S.load(sid)
    sc = st.chapter(cid).scene(scid)
    takes = []
    for t in sc.takes():
        takes.append({"id": t.id, "seed": t.meta.get("seed"),
                      "status": t.meta.get("status"), "stale": t.stale(),
                      "selected": t.id == sc.selected_id,
                      "has_clip": t.has("clip"),
                      "note": t.meta.get("note", ""),
                      "img": "/api/story/%s/take/%s/%s/%s/keyframe.png" % (sid, cid, scid, t.id),
                      "clip": ("/api/story/%s/take/%s/%s/%s/clip.mp4" % (sid, cid, scid, t.id))
                              if t.has("clip") else None})
    return {"story": sid, "chapter": cid, "id": scid,
            "hash": sc.inputs_hash(), "locked": sc.locked,
            "resolved": sc.resolved(), "rules": sc.rule_violations(),
            "editable": {k: sc.data.get(k) for k in
                         ("prompt", "motion", "say", "who", "sfx", "look", "note",
                          "seconds", "negative")},
            "takes": takes}, 200


def take_file(sid, cid, scid, tid, name):
    st = S.load(sid)
    sc = st.chapter(cid).scene(scid)
    p = os.path.join(sc.dir, "takes", tid, name)
    return p if os.path.isfile(p) else None


def thumb(sid, cid, scid):
    st = S.load(sid)
    t = st.chapter(cid).scene(scid).selected()
    return t.keyframe if t and t.has() else None


# ─── authoring ──────────────────────────────────────────────────────────────────────
# Everything here is cheap and synchronous. Creating a story, a chapter or a scene touches
# only JSON - no GPU, no job table. The editor should feel like a text editor until the
# moment you ask it to render something.

def new_story(data):
    title = (data.get("title") or "").strip()
    if not title:
        return {"error": "a title is required"}, 400
    sid = S.slug(title)
    if os.path.isdir(os.path.join(S.STORIES, sid)):
        return {"error": "a story called %r already exists" % sid}, 409
    # Deliberately EMPTY. No template chapter, no placeholder scene - an empty story is a
    # blank page, and inventing a "Chapter 1" nobody asked for is how a tool starts
    # deciding what you are making.
    st = S.create(title)
    return {"ok": True, "id": st.id}, 200


def new_chapter(data):
    st = S.load(data["story"])
    title = (data.get("title") or "").strip() or "untitled chapter"
    ch = S.add_chapter(st, title)
    return {"ok": True, "id": ch.id}, 200


def new_scene(data):
    st = S.load(data["story"])
    ch = st.chapter(data["chapter"])
    sid = S.next_scene_id(ch, data.get("name", ""))
    sc = S.add_scene(ch, sid, prompt=data.get("prompt", ""))
    prev = [s for s in ch.scene_ids() if s != sid]
    if prev:
        ch.set_transition(prev[-1], sid, kind=ch.data.get("transition", "cut"),
                          generated=False)
    return {"ok": True, "id": sc.id}, 200


def save_file(sid):
    """The whole story as one .story document, ready to download."""
    st = S.load(sid)
    return S.to_doc(st), 200


def load_file(data):
    """Take a .story document and write it out as a tree.

    Refuses to silently overwrite. Loading a story whose id already exists is almost always
    a mistake - you meant to open it, not replace it - so it asks for an explicit new id
    instead of quietly clobbering fifty scenes.
    """
    doc = data.get("doc")
    if not isinstance(doc, dict):
        return {"error": "no document"}, 400
    want = (data.get("as") or "").strip()
    sid = S.slug(want) if want else (doc.get("id") or S.slug(
        doc.get("story", {}).get("title", "untitled")))
    if os.path.isdir(os.path.join(S.STORIES, sid)) and not data.get("overwrite"):
        return {"error": "a story called %r already exists - load it under a different "
                         "name, or pass overwrite" % sid, "existing": sid}, 409
    try:
        st = S.from_doc(doc, new_id=sid)
    except ValueError as e:
        return {"error": str(e)}, 400
    missing = sum(1 for sc in st.all_scenes() for t in sc.takes()
                  if t.meta.get("status") == "missing")
    return {"ok": True, "id": st.id, "scenes": len(st.all_scenes()),
            "takes_needing_rerender": missing}, 200


# ─── writes ─────────────────────────────────────────────────────────────────────────

def edit_scene(data):
    st = S.load(data["story"])
    sc = st.chapter(data["chapter"]).scene(data["scene"])
    before = sc.inputs_hash()
    for k, v in (data.get("fields") or {}).items():
        if k not in ("prompt", "motion", "say", "who", "sfx", "look", "note",
                     "seconds", "negative"):
            continue
        if v in (None, ""):
            sc.data.pop(k, None)          # clearing a field restores what it inherits
        else:
            sc.data[k] = v
    sc.save()
    after = sc.inputs_hash()
    n_stale = sum(1 for t in sc.takes() if t.stale())
    return {"ok": True, "hash": after, "changed": before != after,
            "stale_takes": n_stale, "rules": sc.rule_violations()}, 200


def select(data):
    st = S.load(data["story"])
    sc = st.chapter(data["chapter"]).scene(data["scene"])
    sc.select(data["take"])
    return {"ok": True, "selected": data["take"]}, 200


def lock(data):
    st = S.load(data["story"])
    sc = st.chapter(data["chapter"]).scene(data["scene"])
    sc.data["locked"] = bool(data.get("locked"))
    sc.save()
    return {"ok": True, "locked": sc.data["locked"]}, 200


def _render_takes(job, sid, cid, scid, n, seed):
    run, set_path, load_wf, ensure_local, HOST, COMFY = _comfy()
    st = S.load(sid)
    sc = st.chapter(cid).scene(scid)
    f = sc.flat()
    styles = sc.chapter.data.get("style_map") or {}
    style_txt = styles.get(f.get("look", "default")) or styles.get("default") or ""
    for i in range(n):
        t = sc.new_take(seed=(seed + i) if seed else int(time.time() * 1000) % 2 ** 31)
        try:
            wf = load_wf("13_qwen_t2i_styled.json")
            set_path(wf, "10.inputs.text",
                     ("%s. %s" % (f.get("prompt", ""), style_txt)).strip(". "))
            set_path(wf, "11.inputs.text", f.get("negative") or
                     "lowres, blurry, watermark, text, extra fingers, deformed hands")
            set_path(wf, "12.inputs.width", 1280)
            set_path(wf, "12.inputs.height", 704)
            set_path(wf, "13.inputs.seed", t.meta["seed"])
            set_path(wf, "7.inputs.strength_model", float(f.get("style_strength") or 0.0))
            set_path(wf, "15.inputs.filename_prefix",
                     "claude-generated/stories/%s/%s" % (sid, scid))
            _, outs = run(HOST, wf, quiet=True)
            if not outs:
                raise RuntimeError("no output")
            ensure_local(outs[0], t.keyframe, required=False)
            t.save(status="rendered")
        except Exception as e:
            t.save(status="failed", error=str(e)[:200])
            with _LOCK:
                JOBS[job]["error"] = str(e)[:200]
        with _LOCK:
            JOBS[job]["done"] += 1
    if not sc.selected_id and sc.takes():
        sc.select(sc.takes()[0].id)
    with _LOCK:
        JOBS[job]["state"] = "done"


def _render_clip(job, sid, cid, scid):
    run, set_path, load_wf, ensure_local, HOST, COMFY = _comfy()
    st = S.load(sid)
    sc = st.chapter(cid).scene(scid)
    t = sc.selected()
    try:
        if not t or not t.has():
            raise RuntimeError("no selected take with a keyframe")
        f = sc.flat()
        staged = "story_%s_%s_%s.png" % (sid, scid, t.id)
        subprocess.run(["cp", t.keyframe, os.path.join(COMFY, "input", staged)], check=False)
        secs = float(f.get("seconds") or 6)
        frames = int(round(secs * 24 / 8)) * 8 + 1
        wf = load_wf("12_ltx23_i2v_audio.json")
        set_path(wf, "8.inputs.image", staged)
        set_path(wf, "10.inputs.text", f.get("motion") or "gentle natural motion")
        set_path(wf, "20.inputs.width", 1216)
        set_path(wf, "20.inputs.height", 704)
        set_path(wf, "20.inputs.length", frames)
        set_path(wf, "21.inputs.frames_number", frames)
        set_path(wf, "21.inputs.frame_rate", 24)     # the graph ships 25 against 24fps video
        set_path(wf, "32.inputs.noise_seed", t.meta.get("seed") or 1)
        set_path(wf, "43.inputs.filename_prefix",
                 "claude-generated/stories/%s/%s_%s" % (sid, scid, t.id))
        _, outs = run(HOST, wf, quiet=True)
        if not outs:
            raise RuntimeError("no output")
        ensure_local(outs[0], t.clip, required=False)
        t.save(clip_seconds=secs)
    except Exception as e:
        with _LOCK:
            JOBS[job]["error"] = str(e)[:200]
    with _LOCK:
        JOBS[job]["done"] = 1
        JOBS[job]["state"] = "done"


def start_take(data):
    st = S.load(data["story"])
    sc = st.chapter(data["chapter"]).scene(data["scene"])
    if sc.locked and not data.get("force"):
        return {"error": "scene is locked"}, 409
    n = max(1, min(8, int(data.get("n", 4))))
    job = "j%d" % (len(JOBS) + 1)
    with _LOCK:
        JOBS[job] = {"state": "running", "kind": "take", "want": n, "done": 0,
                     "scene": data["scene"], "error": None}
    threading.Thread(target=_render_takes, daemon=True,
                     args=(job, data["story"], data["chapter"], data["scene"], n,
                           data.get("seed"))).start()
    return {"ok": True, "job": job, "n": n}, 200


def start_clip(data):
    job = "j%d" % (len(JOBS) + 1)
    with _LOCK:
        JOBS[job] = {"state": "running", "kind": "clip", "want": 1, "done": 0,
                     "scene": data["scene"], "error": None}
    threading.Thread(target=_render_clip, daemon=True,
                     args=(job, data["story"], data["chapter"], data["scene"])).start()
    return {"ok": True, "job": job}, 200


def job_status(job):
    with _LOCK:
        j = JOBS.get(job)
    return (j or {"error": "no such job"}), (200 if j else 404)
