"""Routes behind /foundry - the selector-driven asset creator.

Same architecture as film_routes: reads synchronous, renders on worker threads through an
in-memory job table, ComfyUI brought back by script when the envelope kills it.

WHAT RENDERS WHAT. Every asset is generated IN its style, because a photoreal seed pack
cannot serve an anime film:

  character  qwen styles: portrait + full body from the compiled clause, then the
             multiple-angles LoRA (workflow 32) turns the full body to 3/4, side and
             back - one concept in, all angles out.
             anime: animagine renders the full body from compiled TAGS, then re-renders
             the other views with the full body as its own IPAdapter reference - the
             self-reference chain that holds a drawn identity.
  place      three angles at every selected time of day, straight from the description.
  costume    a card of the garment alone on a stand; assigning it to a character renders
             the character WEARING it (two-reference edit for qwen styles, sheet +
             costume tags for anime) - and that combined image is what films anchor on.
  prop       a hero shot and a macro.

SEND TO FILM is the bridge: characters become cast entries (clause, short, voice,
portrait, sheet - files COPIED into the film so films stay self-contained), places become
scenes with the pack's angles injected as anchor candidates, costumes swap a cast
member's wear clause and reference image. The same place can be sent to two films, which
is the point.
"""
import json, os, re, shutil, subprocess, sys, threading, time
import urllib.request

TOOLS = os.path.dirname(os.path.abspath(__file__))
STUDIO = os.path.dirname(TOOLS)
ROOT = os.path.dirname(STUDIO)
sys.path.insert(0, STUDIO)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
os.environ.setdefault("COMFY_HOST", "127.0.0.1:8188")

import importlib.util as _ilu                                # noqa: E402
_spec = _ilu.spec_from_file_location("studio_foundry", os.path.join(STUDIO, "foundry.py"))
FY = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(FY)
_fspec = _ilu.spec_from_file_location("studio_film", os.path.join(STUDIO, "film.py"))
FM = _ilu.module_from_spec(_fspec)
_fspec.loader.exec_module(FM)

JOBS = {}
_LOCK = threading.Lock()
_SEQ = [0]

QUALITY_TAGS = "masterpiece, best quality, anime key visual, detailed"
ANIME_NEG = ("photorealistic, photograph, 3d render, cgi, realistic skin, blurry, "
             "lowres, bad anatomy, bad hands, extra limbs, watermark, signature, text, "
             "multiple views, nsfw")


def _comfy():
    from comfy import run, set_path
    from epic import load_wf, ensure_local, HOST, COMFY
    return run, set_path, load_wf, ensure_local, HOST, COMFY


def _job(kind, total=1, **extra):
    with _LOCK:
        _SEQ[0] += 1
        jid = "f%d" % _SEQ[0]
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


# ─── reads ──────────────────────────────────────────────────────────────────────────

def dictionary():
    D = FY.load_dict()
    # the voice sub is dynamic: ready packs only, blocked ones never offered
    voices = []
    vdir = os.path.join(STUDIO, "voices")
    if os.path.isdir(vdir):
        for fn in sorted(os.listdir(vdir)):
            if fn.endswith(".json"):
                try:
                    v = json.load(open(os.path.join(vdir, fn), encoding="utf-8"))
                    if v.get("status") == "ready":
                        voices.append({"id": fn[:-5], "label": v.get("name")})
                except Exception:
                    continue
    D["character"]["subs"]["voice"]["options"] = [
        {"id": v["id"], "label": v["label"], "frag": ""} for v in voices]
    return D, 200


def listing():
    out = {}
    for t in FY.TYPES:
        out[t] = [{"id": a["id"], "name": a["name"], "style": a.get("style"),
                   "images": a.get("images", {}), "compiled": a.get("compiled", {}),
                   "assignments": a.get("assignments", {}),
                   "level": a.get("level", 3), "built_level": FY.level_of(a),
                   "parent": a.get("parent", ""),
                   "variant_note": a.get("variant_note", "")}
                  for a in FY.list_assets(t)]
    films = [{"id": f.id, "title": f.data.get("title")} for f in FM.list_films()]
    return {"assets": out, "films": films}, 200


def detail(atype, aid):
    a = FY.load_asset(atype, aid)
    a["built_level"] = FY.level_of(a)
    return {"asset": a}, 200


def job_status(jid):
    with _LOCK:
        j = JOBS.get(jid)
        return (dict(j), 200) if j else ({"error": "no such job"}, 404)


def jobs_all():
    with _LOCK:
        return {"jobs": sorted(JOBS.values(), key=lambda j: j["started"],
                               reverse=True)[:12]}, 200


# ─── writes ─────────────────────────────────────────────────────────────────────────

def new(data):
    a = FY.new_asset(data["type"], data["name"], data.get("style", "cinematic"),
                     data.get("selections") or {}, data.get("notes", ""),
                     level=int(data.get("level") or 3),
                     parent=data.get("parent", ""),
                     overrides=data.get("overrides") or {})
    return {"ok": True, "id": a["id"], "compiled": a["compiled"],
            "level": a["level"]}, 200


def levels(data=None):
    """The ladder itself, so the UI never hardcodes it."""
    return {"levels": FY.LEVELS}, 200


def variant(data):
    """A character that inherits its parent and differs in named ways.

    Everything the overrides do not mention is the parent's, including the notes
    and the style - a variant is the same person under a change, not a new one.
    Its first render references the parent's own full body so the face carries.
    """
    parent = FY.load_asset("character", data["parent"])
    overrides = data.get("overrides") or {}
    if not overrides:
        return {"error": "a variant needs at least one difference"}, 400
    D = FY.load_dict()
    sel = FY.variant_selections(parent, overrides)
    a = FY.new_asset("character", data["name"], parent["style"], sel,
                     data.get("notes", parent.get("notes", "")),
                     level=int(data.get("level") or 2),
                     parent=parent["id"], overrides=overrides)
    a["variant_note"] = FY.variant_summary(D, parent, overrides)
    FY.save_asset(a)
    return {"ok": True, "id": a["id"], "differs": a["variant_note"],
            "compiled": a["compiled"]}, 200


# ─── the two ways in that are not a form ────────────────────────────────────────────

def _caption_image(path):
    """One vision call: a photograph in, physical facts out. The image is never kept
    as an identity reference - see the module docstring."""
    import shutil
    sys.path.insert(0, TOOLS) if TOOLS not in sys.path else None
    import character_new as CN
    from epic import COMFY
    staged = "foundry_src_%d.png" % (int(time.time()) % 100000)
    shutil.copy(path, os.path.join(COMFY, "input", staged))
    return (CN.caption(staged) or "").strip()


def describe(data):
    """Free prose in, a character out. The paragraph becomes the notes, which compile
    into BOTH the prose clause and the tag stack, so it reaches every engine. Any
    selectors the caller also set still apply; the description refines them."""
    text = (data.get("description") or "").strip()
    if not text:
        return {"error": "describe the person first"}, 400
    a = FY.new_asset("character", data["name"], data.get("style", "anime"),
                     data.get("selections") or {}, text,
                     level=int(data.get("level") or 2))
    return {"ok": True, "id": a["id"], "compiled": a["compiled"]}, 200


def from_image(data):
    """An uploaded photograph in, a character out, by way of a caption.

    Consent is the gate for a real person's photograph, exactly as character_new.py
    requires it: the caller must pass consent=True and it is recorded on the asset.
    """
    path = data.get("path") or ""
    if not os.path.isfile(path):
        return {"error": "no such image: %r" % path}, 400
    if not data.get("consent"):
        return {"error": "a photograph of a real person needs consent=true; "
                         "invented references still need it set, so the record "
                         "always says who agreed"}, 400
    jid = _job("from_image", asset="character/%s" % data.get("name", "?"))
    threading.Thread(target=_from_image_job,
                     args=(jid, path, data["name"], data.get("style", "anime"),
                           int(data.get("level") or 2),
                           data.get("consent_note", "")), daemon=True).start()
    return {"job": jid}, 200


def _from_image_job(jid, path, name, style, level, consent_note):
    try:
        with _LOCK:
            JOBS[jid]["total"] = 2
        if not ensure_comfy():
            raise RuntimeError("ComfyUI will not come up")
        _log(jid, "captioning the source")
        text = _caption_image(path)
        if not text:
            raise RuntimeError("the vision model returned nothing")
        _log(jid, text[:90])
        with _LOCK:
            JOBS[jid]["done"] = 1
        a = FY.new_asset("character", name, style, {}, text, level=level)
        a["provenance"] = "from a supplied image"
        a["provenance_note"] = consent_note or "consent recorded at creation"
        a["source_caption"] = text
        FY.save_asset(a)
        with _LOCK:
            JOBS[jid]["done"] = 2
            JOBS[jid]["result"] = {"id": a["id"], "caption": text}
        _finish(jid)
    except Exception as e:
        _finish(jid, str(e)[:300])



def edit(data):
    a = FY.load_asset(data["type"], data["id"])
    if "selections" in data:
        a["selections"] = data["selections"]
    if "notes" in data:
        a["notes"] = data["notes"]
    if "name" in data:
        a["name"] = data["name"]
    if "level" in data:
        a["level"] = int(data["level"])
    FY.recompile(a)
    return {"ok": True, "compiled": a["compiled"]}, 200


def delete(data):
    shutil.rmtree(FY.asset_dir(data["type"], data["id"]), ignore_errors=True)
    return {"ok": True}, 200


# ─── seed pack rendering ────────────────────────────────────────────────────────────

def _stage(comfy_dir, src, name):
    shutil.copy(src, os.path.join(comfy_dir, "input", name))
    return name


# How hard to hold the identity reference, by what the view is for. A view that
# must VARY cannot be rendered at the weight that holds a turnaround still.
IPA_BY_KIND = {"turn": 0.55, "face": 0.5, "expr": 0.32, "pres": 0.28,
               "base": 0.55}


def _ipa_for(key):
    for prefix, w in IPA_BY_KIND.items():
        if key.startswith(prefix):
            return w
    return 0.55

# Views that must show the whole figure. A photographic model needs telling in
# these words; "full-length standing shot" alone returns a thigh-up crop.
FULL_LENGTH_KEYS = ("base_fullbody", "turn_", "pres_wide")
FULL_LENGTH = ("full body shot, head to toe, the entire figure inside the frame, "
               "both feet visible on the ground, standing at a distance from the "
               "camera, wide framing with empty space above the head and below "
               "the feet")
NOT_CROPPED = ("cropped, cropped legs, cut off at the waist, cut off at the "
               "thigh, close-up, portrait crop, bust shot, headshot")


def _is_full_length(key):
    return any(key.startswith(k) or key == k for k in FULL_LENGTH_KEYS)


def _fullbody_ok(path):
    """-> (ok, detail) via pack_qc's truncation detector; ok when unsure."""
    try:
        sys.path.insert(0, TOOLS) if TOOLS not in sys.path else None
        import pack_qc
        trunc, detail = pack_qc._truncated(path)
        if trunc is None:
            return True, detail
        return (not trunc), detail
    except Exception as e:
        return True, "qc unavailable: %s" % str(e)[:60]


FAR_FRAMING = ("photographed from far away, the whole person small in the middle of "
               "the frame with empty space above the head and the floor visible under "
               "both shoes, wide-angle full-length shot")


def _render_full_length(a, prompt, dest, jid, seeds=(21, 22, 23, 24)):
    """Render a must-be-whole figure and re-roll while the subject runs off the
    bottom of the frame. Two seeds on the prompt as written, then two with a
    far framing sentence - a composition prior does not move for a seed, it
    moves for words. The last attempt stands whatever it shows."""
    for i, seed in enumerate(seeds):
        p = prompt if i < 2 else "%s, %s" % (FAR_FRAMING, prompt)
        _render_direct(a, p, dest, seed=seed, full_length=True)
        ok, detail = _fullbody_ok(dest)
        if ok:
            if i:
                _log(jid, "full length on seed %d%s (%s)"
                     % (seed, " with far framing" if i >= 2 else "", detail))
            return True
        _log(jid, "cropped on seed %d%s (%s) - re-rolling"
             % (seed, " with far framing" if i >= 2 else "", detail))
    _log(jid, "still cropped after %d attempts - keeping the last" % len(seeds))
    return False


def _prop_ok(path):
    """One whole object inside the frame? -> (ok, detail), from the segmenter's
    mask: no edge contact, one contiguous horizontal run."""
    try:
        sys.path.insert(0, TOOLS) if TOOLS not in sys.path else None
        import pack_qc
        alpha = pack_qc._subject_alpha(path)
        if alpha is None:
            return True, "no segmenter"
        a = alpha.resize((160, int(160 * alpha.size[1] / alpha.size[0])))
        w, h = a.size
        px = a.load()
        cols = [any(px[x, y] > 40 for y in range(h)) for x in range(w)]
        rows = [any(px[x, y] > 40 for x in range(w)) for y in range(h)]
        if not any(cols):
            return False, "nothing segmented"
        x0, x1 = cols.index(True), w - 1 - cols[::-1].index(True)
        y0, y1 = rows.index(True), h - 1 - rows[::-1].index(True)
        edge = min(x0, w - 1 - x1, y0, h - 1 - y1) / float(w)
        # gaps inside the bbox: a second object shows as a run of empty columns
        gap, best = 0, 0
        for c in cols[x0:x1 + 1]:
            gap = gap + 1 if not c else 0
            best = max(best, gap)
        detail = "edge=%.3f gap=%.2f" % (edge, best / float(w))
        return (edge >= 0.02 and best / float(w) <= 0.03), detail
    except Exception as e:
        return True, "qc unavailable: %s" % str(e)[:60]


def _render_prop_hero(a, prompt, dest, jid, seeds=(41, 42, 43, 44)):
    """A prop's hero view must be one whole object: re-roll while it is not,
    saying 'a single' louder on the later tries."""
    for i, seed in enumerate(seeds):
        p = prompt if i < 2 else ("exactly one single %s, the whole object centred with "
                                  "empty space around it, nothing else in the picture"
                                  % prompt)
        _render_direct(a, p, dest, seed=seed, wide=True)
        ok, detail = _prop_ok(dest)
        if ok:
            if i:
                _log(jid, "prop whole on seed %d (%s)" % (seed, detail))
            return True
        _log(jid, "prop not one whole object on seed %d (%s) - re-rolling" % (seed, detail))
    _log(jid, "prop still not clean after %d attempts - keeping the last" % len(seeds))
    return False


def _render_direct(a, prompt, dest, seed, wide=False, full_length=False):
    """One image in the asset's style: qwen for everything except anime, which goes
    through animagine so the whole pack shares the cel prior."""
    run, set_path, load_wf, ensure_local, HOST, COMFY = _comfy()
    st = FY.style_info(a["style"])
    w, h = (1216, 832) if wide else (896, 1216)
    if st["kf_engine"] == "animagine":
        wf = load_wf("22_anime_kf_ipadapter.json")
        set_path(wf, "2.inputs.image", a.get("_ipa_ref") or "sheet_liwen.png")
        set_path(wf, "4.inputs.weight",
                 (a.get("_ipa_weight", 0.55)) if a.get("_ipa_ref") else 0.0)
        set_path(wf, "5.inputs.text", "%s, %s" % (prompt, QUALITY_TAGS))
        set_path(wf, "6.inputs.text", ANIME_NEG)
        set_path(wf, "7.inputs.width", w)
        set_path(wf, "7.inputs.height", h)
        set_path(wf, "8.inputs.seed", seed)
        set_path(wf, "10.inputs.width", w)
        set_path(wf, "10.inputs.height", h)
        set_path(wf, "11.inputs.filename_prefix",
                 "claude-generated/foundry/%s_%s" % (a["type"], a["id"]))
    else:
        wf = load_wf("01_qwen_t2i_turbo.json")
        body = ("%s, %s" % (prompt, FULL_LENGTH)) if full_length else prompt
        set_path(wf, "10.inputs.text", "%s. %s" % (body, st["look_clause"]))
        set_path(wf, "11.inputs.text", "blurry, low quality, watermark, text, "
                 + (NOT_CROPPED + ", " if full_length else "")
                 + st["neg"] + ", nsfw")
        set_path(wf, "12.inputs.width", w)
        set_path(wf, "12.inputs.height", h)
        set_path(wf, "13.inputs.seed", seed)
        set_path(wf, "15.inputs.filename_prefix",
                 "claude-generated/foundry/%s_%s" % (a["type"], a["id"]))
    _, outs = run(HOST, wf, quiet=True)
    if not outs:
        raise RuntimeError("no output")
    if os.path.exists(dest):
        os.remove(dest)  # ensure_local skips existing files
    ensure_local(outs[0], dest)
    return dest


def _render_turnaround(a, src_rel, prompt, dest, seed):
    """The multiple-angles LoRA: one image of the subject in, the same subject from a
    named angle out."""
    run, set_path, load_wf, ensure_local, HOST, COMFY = _comfy()
    staged = _stage(COMFY, os.path.join(FY.asset_dir(a["type"], a["id"]), src_rel),
                    "foundry_turn_%s.png" % a["id"])
    wf = load_wf("32_qwen_turnaround.json")
    set_path(wf, "7.inputs.image", staged)
    set_path(wf, "10.inputs.prompt", prompt)
    set_path(wf, "15.inputs.seed", seed)
    set_path(wf, "17.inputs.filename_prefix",
             "claude-generated/foundry/turn_%s" % a["id"])
    _, outs = run(HOST, wf, quiet=True)
    if not outs:
        raise RuntimeError("turnaround: no output")
    if os.path.exists(dest):
        os.remove(dest)  # ensure_local skips existing files
    ensure_local(outs[0], dest)
    return dest


def _seeds_job(jid, atype, aid):
    try:
        a = FY.load_asset(atype, aid)
        st = FY.style_info(a["style"])
        if not ensure_comfy():
            raise RuntimeError("ComfyUI will not come up")
        plan = FY.seed_plan(a)
        with _LOCK:
            JOBS[jid]["total"] = len(plan) + (1 if atype == "character" else 0)
        adir = FY.asset_dir(atype, aid)
        run, set_path, load_wf, ensure_local, HOST, COMFY = _comfy()

        for key, kind, prompt in plan:
            dest = os.path.join(adir, key + ".png")
            _log(jid, key)
            if atype == "character":
                if kind == "direct":
                    full = "%s, %s" % (a["compiled"]["tags"], prompt) \
                        if st["kf_engine"] == "animagine" else \
                        "%s of %s, %s" % ("a" if key != "base_portrait" else "a",
                                          a["compiled"]["clause"], prompt)
                    if st["kf_engine"] == "animagine":
                        # self-reference chain: the full body becomes the pack's ref
                        a["_ipa_weight"] = _ipa_for(key)
                        a["_ipa_ref"] = None
                        fb = os.path.join(adir, "base_fullbody.png")
                        if key != "base_fullbody" and os.path.exists(fb):
                            ref = _stage(COMFY, fb, "foundry_ref_%s.png" % aid)
                            a["_ipa_ref"] = ref
                        elif a.get("parent"):
                            # a variant has no body of its own yet - borrow the
                            # parent's so the face survives the change
                            pfb = os.path.join(FY.asset_dir("character",
                                                            a["parent"]),
                                               "base_fullbody.png")
                            if os.path.exists(pfb):
                                a["_ipa_ref"] = _stage(
                                    COMFY, pfb, "foundry_pref_%s.png" % aid)
                    if st["kf_engine"] == "animagine":
                        # an expression tag has to LEAD, not trail a long identity
                        # string - a danbooru model weights by position
                        et = FY.EXPR_TAGS.get(key[5:]) if key.startswith("expr_") \
                            else None
                        drawn = ("%s, %s, %s" % (et, a["compiled"]["tags"], prompt)
                                 if et else
                                 "%s, %s" % (a["compiled"]["tags"], prompt))
                        if _is_full_length(key):
                            drawn = "full body, cowboy shot off, " + drawn
                        if key == "base_fullbody":
                            _render_full_length(a, drawn, dest, jid)
                        else:
                            _render_direct(a, drawn, dest, seed=21,
                                           full_length=_is_full_length(key))
                    else:
                        if key == "base_fullbody":
                            _render_full_length(
                                a, "%s, %s" % (a["compiled"]["clause"], prompt),
                                dest, jid)
                        else:
                            _render_direct(a, "%s, %s" % (a["compiled"]["clause"],
                                                          prompt), dest, seed=21,
                                           full_length=_is_full_length(key))
                else:
                    if st["kf_engine"] == "animagine":
                        # a drawn identity turns through its own IPAdapter, not the LoRA
                        fb = os.path.join(adir, "base_fullbody.png")
                        a["_ipa_weight"] = _ipa_for(key)
                        a["_ipa_ref"] = _stage(COMFY, fb,
                                               "foundry_ref_%s.png" % aid)
                        # the plan carries the view text - no key table to fall
                        # out of step with CHAR_TURN_VIEWS
                        _render_direct(a, "%s, full body, %s, plain background"
                                       % (a["compiled"]["tags"], prompt),
                                       dest, seed=23, full_length=True)
                    else:
                        _render_turnaround(a, "base_fullbody.png", prompt, dest,
                                           seed=21)
            elif atype == "place":
                a["_ipa_ref"] = None
                if st["kf_engine"] == "animagine":
                    _render_direct(a, "no humans, scenery, %s" % prompt, dest,
                                   seed=31, wide=True)
                else:
                    _render_direct(a, prompt, dest, seed=31, wide=True)
            else:
                a["_ipa_ref"] = None
                if atype == "prop" and key == "hero":
                    _render_prop_hero(a, prompt, dest, jid)
                else:
                    _render_direct(a, prompt, dest, seed=41,
                                   wide=(atype == "prop"))
            a2 = FY.load_asset(atype, aid)
            a2["images"][key] = key + ".png"
            FY.save_asset(a2)
            with _LOCK:
                JOBS[jid]["done"] += 1
        if atype == "character":
            _log(jid, "mesh")
            try:
                _render_mesh(FY.load_asset(atype, aid), adir, jid)
                a3 = FY.load_asset(atype, aid)
                a3["mesh"] = "mesh.glb"
                FY.save_asset(a3)
            except Exception as e:
                # a pack without geometry is still worth keeping - it reports 95%
                # and says why, rather than throwing away nineteen good renders
                _log(jid, "mesh failed: %s" % str(e)[:120])
        _finish(jid)
    except Exception as e:
        _finish(jid, str(e)[:300])


def seeds(data):
    jid = _job("seeds", asset="%s/%s" % (data["type"], data["id"]))
    threading.Thread(target=_seeds_job, args=(jid, data["type"], data["id"]),
                     daemon=True).start()
    return {"job": jid}, 200


# ─── costume onto character ─────────────────────────────────────────────────────────

def _apply_job(jid, char_id, costume_id):
    run, set_path, load_wf, ensure_local, HOST, COMFY = _comfy()
    try:
        ch = FY.load_asset("character", char_id)
        co = FY.load_asset("costume", costume_id)
        if not ensure_comfy():
            raise RuntimeError("ComfyUI will not come up")
        st = FY.style_info(ch["style"])
        wear = co["compiled"]["wear_clause"]
        key = "wearing_%s" % costume_id
        dest = os.path.join(FY.asset_dir("character", char_id), key + ".png")
        if st["kf_engine"] == "animagine":
            fb = os.path.join(FY.asset_dir("character", char_id),
                              "base_fullbody.png")
            if not os.path.exists(fb):
                raise RuntimeError("render the character's seed pack first")
            ch["_ipa_ref"] = _stage(COMFY, fb, "foundry_ref_%s.png" % char_id)
            _render_direct(ch, "%s, wearing %s, full body, standing, plain background"
                           % (ch["compiled"]["tags"], wear), dest, seed=25)
        else:
            port = os.path.join(FY.asset_dir("character", char_id),
                                "base_portrait.png")
            card = os.path.join(FY.asset_dir("costume", costume_id), "card.png")
            if not (os.path.exists(port) and os.path.exists(card)):
                raise RuntimeError("both seed packs must exist first")
            p0 = _stage(COMFY, port, "foundry_ap_%s.png" % char_id)
            p1 = _stage(COMFY, card, "foundry_ac_%s.png" % costume_id)
            wf = load_wf("14_qwen_edit_ref.json")
            set_path(wf, "8.inputs.image", p0)
            set_path(wf, "9.inputs.image", p1)
            set_path(wf, "7.inputs.strength_model", 0.0)
            set_path(wf, "10.inputs.prompt",
                     "The person from the first reference image with their exact same "
                     "face unchanged, now wearing the outfit from the second reference "
                     "image (%s), full body, standing, plain grey background. %s"
                     % (wear, st["look_clause"]))
            set_path(wf, "11.inputs.prompt", "blurry, low quality, watermark, text, "
                     + st["neg"] + ", nsfw")
            set_path(wf, "20.inputs.width", 896)
            set_path(wf, "20.inputs.height", 1216)
            set_path(wf, "13.inputs.seed", 25)
            set_path(wf, "15.inputs.filename_prefix",
                     "claude-generated/foundry/apply_%s" % char_id)
            _, outs = run(HOST, wf, quiet=True)
            if not outs:
                raise RuntimeError("apply render returned nothing")
            if os.path.exists(dest):
                os.remove(dest)  # ensure_local skips existing files
            ensure_local(outs[0], dest)
        ch2 = FY.load_asset("character", char_id)
        ch2["images"][key] = key + ".png"
        ch2["assignments"][costume_id] = {"wear": wear, "image": key + ".png"}
        FY.save_asset(ch2)
        _finish(jid)
    except Exception as e:
        _finish(jid, str(e)[:300])


def apply_costume(data):
    jid = _job("apply", char=data["character"], costume=data["costume"])
    threading.Thread(target=_apply_job, args=(jid, data["character"],
                                              data["costume"]), daemon=True).start()
    return {"job": jid}, 200


# ─── the bridge into /film ──────────────────────────────────────────────────────────

def send_to_film(data):
    """Inject foundry assets into a film. Files are COPIED so films stay
    self-contained; the same asset can therefore serve many films."""
    fid = data["film"]
    f = FM.load(fid)
    added = {"cast": [], "scenes": []}

    for spec in data.get("characters") or []:
        cid = spec["id"] if isinstance(spec, dict) else spec
        costume = (spec.get("costume") if isinstance(spec, dict) else None) or ""
        ch = FY.load_asset("character", cid)
        c = ch["compiled"]
        clause = c["clause"]
        if costume and costume in ch.get("assignments", {}):
            clause = "%s, wearing %s" % (clause,
                                         ch["assignments"][costume]["wear"])
        key = cid.upper().replace("-", "_")[:12]
        entry = {"name": ch["name"], "clause": clause, "short": c["short"],
                 "sheet": "", "voice": c.get("voice", ""),
                 "voice_desc": c.get("voice_desc", ""), "portrait": ""}
        adir = FY.asset_dir("character", cid)
        # the identity images: outfit-applied beats the base when it exists
        body_img = None
        if costume and costume in ch.get("assignments", {}):
            body_img = os.path.join(adir, ch["assignments"][costume]["image"])
        elif os.path.exists(os.path.join(adir, "base_fullbody.png")):
            body_img = os.path.join(adir, "base_fullbody.png")
        port_img = os.path.join(adir, "base_portrait.png")
        if os.path.exists(port_img):
            dst = os.path.join(f.dir, "assets", "cast_%s.png" % key)
            shutil.copy(port_img, dst)
            entry["portrait"] = "assets/cast_%s.png" % key
        if body_img and os.path.exists(body_img):
            if FY.style_info(ch["style"])["kf_engine"] == "animagine":
                # the sheet the anime identity route hangs on, staged where 22 loads it
                from epic import COMFY
                sheet_name = "foundry_sheet_%s.png" % cid
                shutil.copy(body_img, os.path.join(COMFY, "input", sheet_name))
                entry["sheet"] = sheet_name
            dstb = os.path.join(f.dir, "assets", "cast_%s_body.png" % key)
            shutil.copy(body_img, dstb)
        f.data["cast"][key] = entry
        added["cast"].append(key)

    for spec in data.get("places") or []:
        pid = spec["id"] if isinstance(spec, dict) else spec
        time_key = (spec.get("time") if isinstance(spec, dict) else None) or ""
        pl = FY.load_asset("place", pid)
        c = pl["compiled"]
        times = [time_key] if time_key else c["times"][:1]
        t = times[0]
        sc = f.new_scene("%s (%s)" % (pl["name"], t),
                         location=c["description"], time_of_day=c["time_frags"].get(t, t),
                         ambience=c["ambience"], palette=c.get("palette", ""))
        adir = FY.asset_dir("place", pid)
        cands = []
        for akey in ("wide", "reverse", "detail"):
            src = os.path.join(adir, "%s_%s.png" % (t, akey))
            if os.path.exists(src):
                rel = "assets/anchor_%s_c%d.png" % (sc["id"], len(cands))
                shutil.copy(src, os.path.join(f.dir, rel))
                cands.append(rel)
        if cands:
            shutil.copy(os.path.join(f.dir, cands[0]),
                        os.path.join(f.dir, "assets", "anchor_%s.png" % sc["id"]))
            sc["anchor"] = "assets/anchor_%s.png" % sc["id"]
            sc["anchor_candidates"] = cands
        added["scenes"].append(sc["id"])

    for spec in data.get("music") or []:
        mid = spec["id"] if isinstance(spec, dict) else spec
        scid = spec.get("scene") if isinstance(spec, dict) else None
        mu = FY.load_asset("music", mid)
        if scid:
            f.scene(scid)["music"] = mu["compiled"]["tags"]

    f.save()
    return {"ok": True, "added": added}, 200


# ─── one roster over both character systems ─────────────────────────────────────────

CAST_DIR = os.path.join(os.path.dirname(TOOLS), "characters")


def _legacy_rows():
    """The legacy cast cards, read off disk. Only the fields the roster shows."""
    rows = []
    if not os.path.isdir(CAST_DIR):
        return rows
    for fn in sorted(os.listdir(CAST_DIR)):
        if not fn.endswith(".json"):
            continue
        try:
            d = json.load(open(os.path.join(CAST_DIR, fn), encoding="utf-8"))
        except Exception:
            continue
        cid = d.get("id") or fn[:-5]
        sheet = d.get("sheet") or ""
        turn = os.path.join(COMFY_INPUT(), "turnaround_%s" % cid.lower())
        views = len([f for f in os.listdir(turn)
                     if f.endswith(".png")]) if os.path.isdir(turn) else 0
        rows.append({"id": cid, "name": d.get("name") or cid,
                     "desc": (d.get("desc") or d.get("prose") or "")[:200],
                     "status": d.get("status", ""), "sheet": sheet,
                     "lora": bool(d.get("lora")), "views": views,
                     "provenance": d.get("provenance", ""),
                     "sheet_url": _sheet_url(sheet),
                     "evidence": (d.get("evidence") or {}).get("verdict", "")})
    return rows


REFSHEETS = os.path.join(os.path.dirname(TOOLS), "samples", "_refsheets")


def _sheet_url(name):
    """serve.py mirrors cast sheets into samples/_refsheets so the app can show
    them. Use the mirror when it exists; a card whose sheet was never mirrored
    simply has no thumbnail rather than a broken image."""
    if not name or os.path.basename(name) != name:
        return ""
    return ("/samples/_refsheets/%s" % name
            if os.path.isfile(os.path.join(REFSHEETS, name)) else "")


def COMFY_INPUT():
    try:
        from epic import COMFY
        return os.path.join(COMFY, "input")
    except Exception:
        return "/nonexistent"


def _legacy_pack(row):
    """Score a legacy card on the level-1 pack: an audit, not a judgement."""
    have = {"turnaround": min(row["views"], len(FY.CHAR_TURN_VIEWS)),
            "face": len(FY.CHAR_FACE_VIEWS) if row["sheet"] else 0,
            "expressions": 0,          # legacy suites never rendered a named set
            "presentation": 0,
            "mesh": 0}
    want = {"turnaround": len(FY.CHAR_TURN_VIEWS), "face": len(FY.CHAR_FACE_VIEWS),
            "expressions": len(FY.CHAR_EXPRESSIONS),
            "presentation": len(FY.CHAR_PRESENTATION), "mesh": 1}
    missing = [k for k in want if have[k] < want[k]]
    return {"have": have, "want": want, "missing": missing,
            "complete": not missing}


_PACK_ORDER = ("base_portrait", "base_fullbody", "turn_front", "turn_front_three_quarter",
               "turn_side", "turn_back_three_quarter", "turn_back", "face_front",
               "face_three_quarter", "face_side", "expr_neutral", "expr_joy", "expr_sorrow",
               "expr_anger", "expr_fear", "expr_surprise", "pres_hero", "pres_low", "pres_wide")


def _pack_files(cid, imgs):
    """Every render in the character's folder: the pack in its natural order, then
    costume variants (wearing_<costume>.png), then anything else."""
    d = os.path.join(FY.ASSETS if hasattr(FY, "ASSETS") else
                     os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                  "foundry"), "characters", cid)
    try:
        on_disk = sorted(f for f in os.listdir(d) if f.endswith(".png") and not f.endswith("_depth.png"))
    except OSError:
        on_disk = []
    order = {k: i for i, k in enumerate(_PACK_ORDER)}
    pack = sorted([f for f in on_disk if f[:-4] in order], key=lambda f: order[f[:-4]])
    wearing = [f for f in on_disk if f.startswith("wearing_")]
    rest = [f for f in on_disk if f not in pack and f not in wearing]
    return pack + wearing + rest


def roster():
    """Everyone, from both stores, on one ladder."""
    out = []
    for a in FY.list_assets("character"):
        rep = FY.pack_report(a)
        imgs = a.get("images") or {}
        thumb = imgs.get("base_portrait") or imgs.get("face_front") \
            or (list(imgs.values())[0] if imgs else "")
        out.append({
            "id": a["id"], "name": a["name"], "source": "foundry",
            "style": a.get("style", ""), "level": FY.level_of(a),
            "pack": rep, "parent": a.get("parent", ""),
            "variant_note": a.get("variant_note", ""),
            "voice": (a.get("compiled") or {}).get("voice", ""),
            "lora": bool(a.get("lora")), "mesh": bool(a.get("mesh")),
            "thumb": ("/foundry/media/characters/%s/%s" % (a["id"], thumb))
                     if thumb else "",
            "images": len(imgs),
            "files": _pack_files(a["id"], imgs),
            "desc": (a.get("compiled") or {}).get("clause", "")[:200]})

    for row in _legacy_rows():
        rep = _legacy_pack(row)
        out.append({
            "id": row["id"], "name": row["name"], "source": "cast",
            "style": "", "level": 1 if rep["complete"] else 0,
            "pack": rep, "parent": "", "variant_note": "",
            "voice": "", "lora": row["lora"], "mesh": False,
            "thumb": row["sheet_url"],
            "images": row["views"], "desc": row["desc"],
            "status": row["status"], "provenance": row["provenance"],
            "evidence": row["evidence"]})

    out.sort(key=lambda r: (-r["level"], r["name"].lower()))
    return {"characters": out, "levels": FY.LEVELS,
            "counts": {"total": len(out),
                       "castable": sum(1 for r in out if r["level"] >= 1),
                       "draft": sum(1 for r in out if r["level"] < 1)}}, 200


# ─── the mesh step ──────────────────────────────────────────────────────────────────

def _render_mesh(a, adir, jid):
    """base_fullbody -> a GLB. The recipe is terra_3d's measured winner, reached
    through the shipped workflow rather than a second opinion about settings."""
    run, set_path, load_wf, ensure_local, HOST, COMFY = _comfy()
    src = os.path.join(adir, "base_fullbody.png")
    if not os.path.exists(src):
        raise RuntimeError("no base_fullbody to mesh from")
    staged = _stage(COMFY, src, "foundry_mesh_%s.png" % a["id"])
    wf = load_wf("24_hunyuan3d_mesh.json")
    set_path(wf, "2.inputs.image", staged)
    set_path(wf, "10.inputs.filename_prefix",
             "claude-generated/foundry/mesh_%s" % a["id"])
    _, outs = run(HOST, wf, quiet=True)
    glb = next((o for o in outs if str(o).lower().endswith(".glb")), None)
    if not glb:
        raise RuntimeError("the mesh graph returned no glb")
    dest = os.path.join(adir, "mesh.glb")
    if os.path.exists(dest):
        os.remove(dest)
    ensure_local(glb, dest)
    return dest


# ─── legacy cast -> foundry ─────────────────────────────────────────────────────────

def import_legacy(data):
    """Lift a legacy cast card onto the ladder. Its words come across; its pixels
    are re-rendered, because the pack wants one consistent set and a legacy sheet
    was made by a different tool at a different size."""
    cid = data["id"]
    p = os.path.join(CAST_DIR, cid + ".json")
    if not os.path.isfile(p):
        return {"error": "no legacy card %r" % cid}, 404
    d = json.load(open(p, encoding="utf-8"))
    name = data.get("name") or d.get("name") or cid
    style = data.get("style", "anime")

    # the words: prose first because it reads as a person, tags after because they
    # are what the drawn engines actually consume
    notes = data.get("notes")
    if notes is None:
        bits = [d.get("prose") or d.get("desc") or "", d.get("tags") or ""]
        notes = ", ".join(b.strip() for b in bits if b and b.strip())
    a = FY.new_asset("character", name, style, data.get("selections") or {}, notes,
                     level=int(data.get("level") or 1),
                     tag_notes=data.get("tag_notes", ""))
    a["imported_from"] = cid
    a["provenance"] = d.get("provenance", "")
    a["provenance_note"] = d.get("provenance_note", "")
    if d.get("lora"):
        a["legacy_lora"] = d["lora"]
    sheet = d.get("sheet") or ""
    if sheet:
        try:
            from epic import COMFY
            src = os.path.join(COMFY, "input", sheet)
            if os.path.isfile(src):
                shutil.copy(src, os.path.join(FY.asset_dir("character", a["id"]),
                                              "seed_source.png"))
                a["seed_source"] = "seed_source.png"
        except Exception:
            pass
    FY.save_asset(a)
    return {"ok": True, "id": a["id"], "compiled": a["compiled"]}, 200


def rename(data):
    """Change the display name. The id is a slug that films already reference, so
    it does NOT move - renaming must not orphan a cast entry pointing at it."""
    a = FY.load_asset(data["type"], data["id"])
    new = (data.get("name") or "").strip()
    if not new:
        return {"error": "a name cannot be empty"}, 400
    a["name"] = new
    FY.save_asset(a)
    return {"ok": True, "id": a["id"], "name": new}, 200
