#!/usr/bin/env python3
"""studio/serve.py - a local web UI for browsing the variable library and building scenes.

    python3 studio/serve.py            then open http://localhost:8777

No dependencies, no build step. The library is read from disk on every request, so editing
a preset file and refreshing the page shows the change immediately - the point is that the
JSON files stay the source of truth and this is only a window onto them.

Endpoints:
    /                 the app
    /api/library      every preset folder, expanded
    /api/variables    the 461-variable census
    /api/cards        capability cards - what each option value looks like
    /api/loras        the LoRA library, each card checked against models/loras
    /api/movies       .movie files found in studio/movies
    /api/save         POST {name, text} -> writes studio/movies/<name>.movie
    /video            every rendered clip, grouped by what it demonstrates
    /api/video        the clip index - studio/samples/video.json, built by
                      studio/_tools/video_index.py
    /character        the cast, each with a state per dossier section
    /character/<ID>   one character's dossier - who she is, what holds her face on each
                      engine, how she looks, wears, is drawn, moves and sounds, and what
                      is still unknown
    /api/character[/<ID>]   the payload behind those, assembled by
                      studio/_tools/dossier.py from what is on disk
    /character/<ID>/clip/<clip>.mp4   one motion clip, resolved through that character's
                      manifest and streamed with Range - the mp4s live in ComfyUI's output
                      tree, outside anything the static handler will open

Samples are served through _send_file, which honours Range. Video needs that: without it
`preload="metadata"` pulls whole mp4s and no clip can be seeked. The page routes go through
_page, which injects the /video nav link rather than editing ten hand-written HTML files.
"""
import http.server, importlib, inspect, json, os, re, socket, socketserver, subprocess, \
       sys, traceback, urllib.parse
import shutil
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
PORT = int(os.environ.get("STUDIO_PORT", "8777"))
# Bind on all interfaces so the studio is usable from the machine you actually sit at,
# not only from a browser on the render box. Set STUDIO_BIND=127.0.0.1 to keep it local.
BIND = os.environ.get("STUDIO_BIND", "0.0.0.0")

# Serving a .webp as image/png happens to work in most browsers because they sniff the
# magic bytes, but it is wrong, it defeats caching heuristics, and it breaks anything
# that trusts the header. Be explicit.
MIME = {".webp": "image/webp", ".png": "image/png", ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg", ".gif": "image/gif", ".mp4": "video/mp4",
        ".webm": "video/webm", ".mp3": "audio/mpeg", ".wav": "audio/wav",
        ".svg": "image/svg+xml",
        # The 3D deliverables, served through the same /samples/ route as every other
        # sample. Given real types rather than octet-stream so a browser and a slicer
        # both know what they were handed. None of them renders inline in a browser, so
        # in practice every one of these is a download - which is the point: a 133 MB
        # STL streams through _send_file with Range, never read into memory.
        ".glb": "model/gltf-binary", ".gltf": "model/gltf+json", ".stl": "model/stl",
        ".3mf": "model/3mf", ".obj": "model/obj",
        ".ply": "application/octet-stream", ".spz": "application/octet-stream"}

# folders that hold pickable presets, in the order the UI should show them
GROUPS = ["shots", "cameras", "transitions", "motions", "looks", "lighting", "layers",
          "weather", "emotions", "soundscapes", "pacing", "places", "characters", "cues",
          "prompts", "checkpoints", "voices", "sfx", "mesh"]


def library():
    out = {}
    for g in GROUPS:
        d = f"{HERE}/{g}"
        if not os.path.isdir(d):
            continue
        items = []
        for fn in sorted(os.listdir(d)):
            if not fn.endswith(".json"):
                continue
            try:
                card = json.load(open(f"{d}/{fn}", encoding="utf-8"))
            except Exception as e:
                items.append({"id": fn[:-5], "desc": f"UNREADABLE: {e}", "status": "error"})
                continue
            # A file that PARSES but is not card-shaped used to take the whole app down
            # at import - studio/looks/_luma.json was a bare list of measurements and
            # every page went with it, silently, until the next restart hours later.
            # Report it in place, the same courtesy an unparseable file already got.
            if not isinstance(card, dict) or "id" not in card:
                items.append({"id": fn[:-5], "status": "error",
                              "desc": "NOT A CARD: %s with no usable id. A .json in a "
                                      "card directory must be an object with an `id`; "
                                      "measurement output belongs in studio/samples/."
                                      % type(card).__name__})
                continue
            items.append(card)
        for it in items:
            # .webp first: the panels were re-encoded from PNG (14.8x smaller) and a
            # stale .png beside a .webp should not win.
            for ext in (".webp", ".png", ".mp4"):
                if os.path.exists(f"{HERE}/samples/{g}/{it['id']}{ext}"):
                    it["sample"] = f"/samples/{g}/{it['id']}{ext}"
                    break
        if items:
            out[g] = items
    return out


ROOT = os.path.dirname(HERE)
# Where ComfyUI is listening, for queueing a graph onto its render queue.
COMFY = os.environ.get("COMFY_URL", "http://127.0.0.1:8188")
COMFY_OUT = os.path.expanduser(
    os.environ.get("COMFY_ROOT", "~/ComfyUI")) + "/output/claude-generated/12-shorts"


def safe_name(s):
    """Names come off the network and are used to build paths and a shell command, so
    strip everything that is not plainly a filename. No dots, so `..` cannot form."""
    return "".join(c for c in str(s) if c.isalnum() or c in "-_")[:64]


# ---------------------------------------------------------------------------
# the cast payload
#
# A character card is a set of CLAIMS - it names a sheet, a LoRA, a voice. Every one of
# those claims is checked against the filesystem here rather than trusted, because the
# cast page used to render a green tick for a string being non-empty and a card naming a
# deleted .safetensors looked exactly like a trained one.
# ---------------------------------------------------------------------------

# Reference sheets live in ComfyUI/input and nowhere else, because ComfyUI's LoadImage
# reads only from there. The static handler below serves paths under studio/ only. Rather
# than widen it into an arbitrary-path file server, the one file a card actually names is
# mirrored into samples/sheets/ - see _mirror_sheet.
CAST_INPUT = os.path.expanduser(
    os.environ.get("COMFY_ROOT", "~/ComfyUI")) + "/input"
# Its own directory, NOT samples/sheets - that name is already taken by the capability-card
# contact sheets and a mirror dropped in there would be indistinguishable from them.
CAST_SHEETS = f"{HERE}/samples/_refsheets"
CAST_IMG_EXT = (".png", ".webp", ".jpg", ".jpeg")
# A sheet name off a card is used to build a path. Bare filenames only.
_BARE_FILE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


def _mirror_sheet(name):
    """Copy a reference sheet into samples/ so the app can show it. -> (url, on_disk).

    Re-copied whenever size or mtime move, so a sheet being rendered by another process
    while this page is open appears on the next refresh instead of going stale.
    """
    if not name:
        return None, False
    base = str(name)
    if os.path.basename(base) != base or not _BARE_FILE.match(base) \
            or not base.lower().endswith(CAST_IMG_EXT):
        return None, False
    src = f"{CAST_INPUT}/{base}"
    try:
        st = os.stat(src)
    except OSError:
        return None, False                      # named on the card, absent from disk
    dst = f"{CAST_SHEETS}/{base}"
    try:
        d = os.stat(dst)
        stale = d.st_size != st.st_size or d.st_mtime < st.st_mtime
    except OSError:
        stale = True
    if stale:
        try:
            os.makedirs(CAST_SHEETS, exist_ok=True)
            with open(src, "rb") as a, open(dst + ".part", "wb") as b:
                b.write(a.read())
            os.replace(dst + ".part", dst)
            os.utime(dst, (st.st_atime, st.st_mtime))
        except OSError:
            return None, True                   # it exists, we just cannot show it
    return f"/samples/_refsheets/{base}", True


def _dataset(cid):
    """The training set for a character, counted rather than assumed.

    turnaround.py writes ComfyUI/input/<id>_train/ as png+txt pairs and train_character.py
    reads exactly that path. A png with no caption is not a usable example, so `pairs` -
    not the file count - is the number that decides whether training can run.
    """
    d = f"{CAST_INPUT}/{str(cid).lower()}_train"
    if not os.path.isdir(d):
        return {"dir": d, "exists": False, "images": 0, "captions": 0, "pairs": 0}
    imgs, caps = set(), set()
    try:
        for f in os.listdir(d):
            stem, ext = os.path.splitext(f)
            ext = ext.lower()
            if ext in CAST_IMG_EXT:
                imgs.add(stem)
            elif ext == ".txt":
                caps.add(stem)
    except OSError:
        pass
    return {"dir": d, "exists": True, "images": len(imgs), "captions": len(caps),
            "pairs": len(imgs & caps)}


def _cards_in(group):
    """Every json card in studio/<group>/, keyed by id. Unreadable ones are skipped."""
    d = f"{HERE}/{group}"
    out = {}
    if not os.path.isdir(d):
        return out
    for fn in sorted(os.listdir(d)):
        if not fn.endswith(".json"):
            continue
        try:
            c = json.load(open(f"{d}/{fn}", encoding="utf-8"))
        except Exception:
            continue
        if isinstance(c, dict):
            out[str(c.get("id") or fn[:-5])] = c
    return out


def _resolve_voice(raw, voices):
    """A character's `voice` is the string "<engine> <path/to.wav>" - compile.py splits it
    on whitespace and uses [0] and [-1]. Resolve it back to the voice card, because the
    single hard rule in this project is about voices: four packs in the library are clones
    of real, identifiable people, they are marked status blocked, and a cast page that
    prints the raw string cannot tell you that the character you are about to shoot is
    cast with one of them.
    """
    if not raw:
        return None
    parts = str(raw).split()
    if not parts:
        return None
    engine, wav = parts[0], parts[-1]
    base = os.path.basename(wav).lower()
    exact = [v for v in voices.values()
             if v.get("engine") == engine and str(v.get("file", "")) == wav]
    if exact:
        return exact[0]
    byfile = [v for v in voices.values()
              if os.path.basename(str(v.get("file", ""))).lower() == base]
    return byfile[0] if byfile else None


_TOKEN = "[^a-z0-9]"


def _demos(cid, sheet_base):
    """Rendered evidence for one character, discovered rather than listed.

    Everything under samples/ whose filename or containing directory names this character,
    minus the turnaround directory itself. That is how the with-LoRA / without-LoRA control
    pair gets onto the page: those are .jpg files one level above samples/cast/<ID>/ and
    the old view glob could not see them.
    """
    low = str(cid).lower()
    pat = re.compile("(^|%s)%s(%s|$)" % (_TOKEN, re.escape(low), _TOKEN))
    hits, seen = [], set()
    for root in ("cast", "qwen_character", "loras", "characters"):
        base = f"{HERE}/samples/{root}"
        if not os.path.isdir(base):
            continue
        for dirpath, dirnames, files in os.walk(base):
            rel_dir = os.path.relpath(dirpath, base).replace("\\", "/")
            if rel_dir == ".":
                rel_dir = ""
            # the turnaround views are reported separately, and the mirror is not evidence
            dirnames[:] = [x for x in dirnames if x.lower() != low]
            for f in sorted(files):
                if not f.lower().endswith(CAST_IMG_EXT):
                    continue
                if sheet_base and f == sheet_base:
                    continue
                where = (rel_dir + "/" + f).lower()
                if not pat.search(where):
                    continue
                url = "/samples/%s/%s" % (root, (rel_dir + "/" + f).lstrip("/"))
                if url in seen:
                    continue
                seen.add(url)
                hits.append({"name": os.path.splitext(f)[0],
                             "file": url,
                             "where": "samples/%s%s" % (root, "/" + rel_dir if rel_dir else "")})
    return hits[:24]


# The instruction three places in this app print for a missing sheet - "run
# scripts/make_sheets.py" - cannot be followed: that script takes a FILM as a required
# positional and reads its `designs` block, so it exits on argparse for a bare character
# card. Rather than print a command that fails, the page is told which sheet-making tool
# is ACTUALLY on disk, checked per request so a tool appearing while the page is open is
# picked up on refresh.
#
# TWO tools landed, one per engine, and neither under the name this probe was written
# against - so the page went on printing "THERE IS NO TOOL FOR THIS YET" while both sat in
# _tools. They are listed anime-first because five of the six cards in the library are
# anime cards, and a sheet imports its style, so an anime character wants an anime sheet.
SHEET_TOOLS = ("studio/_tools/make_anime_sheet.py",     # animagine, IPAdapter at 0.0
               "studio/_tools/qwen_sheet.py",           # qwen, photographic
               "studio/_tools/make_character_sheet.py",
               "studio/_tools/make_sheet.py",
               "scripts/make_character_sheet.py")


def _sheet_tool():
    for rel in SHEET_TOOLS:
        if os.path.isfile(f"{ROOT}/{rel}"):
            return rel
    return None


def _sheet_tools():
    """Every sheet tool on disk, not just the first. The two that exist render on
    DIFFERENT engines and produce visibly different sheets, so a character card whose
    engine is qwen must not be told to run the animagine one."""
    return [rel for rel in SHEET_TOOLS if os.path.isfile(f"{ROOT}/{rel}")]


def _composer():
    """The resolver, or None. Reloaded per request for the same reason the library is read
    per request: this page's whole job is to agree with what a render would actually do."""
    if HERE not in sys.path:
        sys.path.insert(0, HERE)
    try:
        import compose as composer
        if getattr(composer, "__file__", "").startswith(HERE):
            composer = importlib.reload(composer)
        if not callable(getattr(composer, "resolve", None)):
            return None
        return composer
    except Exception:
        return None


def _identity(composer, libs, cid):
    """What is actually holding this character's face, ON EACH ENGINE, from the resolver.

    This is the one fact the page exists to state and it differs per engine: a trained
    character LoRA is a delta on animagine's weights, so it is live on the anime path and
    silently discarded on the qwen path. Asking compose.resolve() rather than re-deciding
    here is deliberate - a second implementation would drift from what gets rendered, and
    the wizard and the cast page disagreeing about the same character is exactly the bug
    this replaces.
    """
    out = {}
    for eng in ("anime", "qwen"):
        try:
            r = composer.resolve(libs, {"character": cid, "engine": eng})
        except Exception as e:
            out[eng] = {"error": f"{type(e).__name__}: {e}"}
            continue
        out[eng] = {
            "engine": r.get("engine"),
            "prompt": r.get("prompt"),
            "lora": r.get("lora"),
            "lora_active": bool(r.get("lora_active")),
            "lora_reason": r.get("lora_reason"),
            "conflicts": [x for x in (r.get("conflicts") or [])
                          if "character" in (x.get("layers") or [])],
        }
    return out


def cast():
    """Characters, each with whatever identity assets actually exist for them.

    The card on disk is the source of truth for tags, voice and sheet; the turnaround
    views are discovered from samples/cast/<id>/ rather than recorded, so the page cannot
    claim views that were deleted. Same reason the LoRA is reported from the card only
    after training wrote it there.

    Everything the card CLAIMS is then checked: the sheet against ComfyUI/input, the LoRA
    against models/loras, the dataset against ComfyUI/input/<id>_train, the voice against
    studio/voices/. And compose.resolve() is called once per engine so the page reports
    the same identity mechanism the renderer will use rather than a second guess at it.

    THE SHAPE IS APPEND-ONLY. wizard.html reads this endpoint as a bare array and takes
    views[0].file as a character's thumbnail, so `views` stays turnaround-only and stays
    numerically ordered; the demo grids arrive on a separate `demos` key.
    """
    d = f"{HERE}/characters"
    if not os.path.isdir(d):
        return []
    voices = _cards_in("voices")
    lora_cards = _cards_in("loras")
    by_file = {str(v.get("file")): v for v in lora_cards.values() if v.get("file")}
    try:
        on_disk = {f: os.path.getsize(f"{LORA_FILES}/{f}")
                   for f in os.listdir(LORA_FILES) if f.endswith(".safetensors")}
    except OSError:
        on_disk = None
    composer = _composer()
    sheet_tool = _sheet_tool()
    sheet_tools = _sheet_tools()
    libs = None
    if composer is not None:
        try:
            libs = composer.load_libs()
        except Exception:
            libs = None
    out = []
    for fn in sorted(os.listdir(d)):
        if not fn.endswith(".json"):
            continue
        try:
            c = json.load(open(f"{d}/{fn}", encoding="utf-8"))
            if not isinstance(c, dict):
                raise ValueError("not a JSON object")
        except Exception as e:
            out.append({"id": fn[:-5], "name": fn[:-5], "desc": f"UNREADABLE: {e}",
                        "unreadable": True, "views": [], "demos": []})
            continue
        cid = str(c.get("id") or fn[:-5])
        c["id"] = cid
        vd = f"{HERE}/samples/cast/{cid}"
        views = []
        if os.path.isdir(vd):
            # A leading underscore marks a file that is deliberately NOT a
            # turnaround view. samples/cast/VIRO/_sheet_photo.png is a photographic
            # REFERENCE SHEET written here by another tool; without this filter it
            # was served as a 17th view, so the page claimed 17 turnaround views
            # where 16 were rendered and put a photograph in the turnaround grid.
            names = [v for v in os.listdir(vd)
                     if v.lower().endswith(CAST_IMG_EXT) and not v.startswith("_")]
            # numeric prefixes first and in order, so views[0] stays 00_front and the
            # wizard's thumbnail does not become whatever sorted last into the folder.
            names.sort(key=lambda v: (0 if v[:1].isdigit() else 1, v))
            for v in names:
                views.append({"name": os.path.splitext(v)[0].split("_", 1)[-1],
                              "file": f"/samples/cast/{cid}/{v}"})
        c["views"] = views

        sheet = str(c.get("sheet") or "")
        c["sheet_url"], c["sheet_exists"] = _mirror_sheet(sheet)
        c["sheet_dir"] = CAST_INPUT
        c["sheet_tool"] = sheet_tool
        c["sheet_tools"] = sheet_tools
        c["dataset"] = _dataset(cid)

        lf = str(c.get("lora") or "")
        c["lora_exists"] = None if on_disk is None else (bool(lf) and lf in on_disk)
        c["lora_size"] = (on_disk or {}).get(lf)
        c["lora_dir"] = LORA_FILES
        c["lora_card"] = by_file.get(lf)

        vc = _resolve_voice(c.get("voice"), voices)
        c["voice_card"] = vc
        c["voice_status"] = (vc.get("status") or "unknown") if vc else (
            "unresolved" if c.get("voice") else "none")

        c["demos"] = _demos(cid, os.path.basename(sheet) if sheet else "")
        c["identity"] = _identity(composer, libs, cid) if composer else None
        # What the resolver will substitute when the card is silent. Shown greyed, so a
        # character with no wear_tags reads as "dressed in a uniform at every damage
        # level" instead of as an empty space where the ladder should be.
        c["wear_fallback"] = list(getattr(composer, "WEAR", []) or []) \
            if (composer and not c.get("wear_tags")) else []
        c["base_tags_fallback"] = (getattr(composer, "MALE", "") or "") \
            if (composer and not c.get("base_tags")) else ""
        out.append(c)
    return out


def verify_queue():
    """Cards that have panels but no human verdict, plus the ones already done.

    This is the project's largest honest gap: 1026 rendered comparison panels that
    nobody has looked at. Both predictions ever checked against pixels turned out WRONG
    (extreme_close was predicted to fail and is the best panel in the set; extreme_wide
    was predicted to work and loses the figure entirely), so the claims cannot be trusted
    until someone looks. Predicting is worse than useless here.

    Unverified first, since that is the work. Cards with no panels are excluded - there
    is nothing to look at.
    """
    d = f"{HERE}/cards"
    if not os.path.isdir(d):
        return {"todo": [], "done": [], "total": 0}
    todo, done = [], []
    for fn in sorted(os.listdir(d)):
        if not fn.endswith(".json"):
            continue
        try:
            c = json.load(open(f"{d}/{fn}", encoding="utf-8"))
        except Exception:
            continue
        if c.get("not_visual") or not (c.get("panels") or c.get("sheet")):
            continue
        item = {
            "slug": fn[:-5],
            "variable": c.get("variable", fn[:-5]),
            "claim": c.get("claim", ""),
            "sheet": c.get("sheet"),
            # the clause is what the option ASKED FOR, in the model's own words. Showing
            # it means a reviewer does not need to know the term to judge the picture.
            "panels": [{"value": p.get("value"), "sample": p.get("sample"),
                        "control": bool(p.get("control")),
                        "clause": p.get("clause") or ""}
                       for p in (c.get("panels") or [])],
            "verdict": c.get("verdict"),
            "look_at": c.get("look_at"),
            "review": c.get("review") or [],
        }
        (done if c.get("verdict") else todo).append(item)
    # Phase 4: the kind libraries report their evidence here too - /verify is the page
    # whose whole job is honest gaps, and the UNVERIFIED ready cards are exactly that.
    kinds = {}
    try:
        sys.path.insert(0, HERE)
        import cards as _cards
        for kind in _cards.KINDS:
            tally = {"MEASURED": 0, "JUDGED": 0, "UNVERIFIED": 0}
            debt = []
            for cid, card in _cards.load(kind).items():
                if cid.startswith("_"):
                    continue
                v = _cards.evidence_of(card)["verdict"]
                tally[v] += 1
                if v == "UNVERIFIED" and card.get("status") == "ready":
                    debt.append(cid)
            if sum(tally.values()):
                kinds[kind] = {"tally": tally, "unverified_ready": sorted(debt)[:40]}
    except Exception:
        traceback.print_exc()
    return {"todo": todo, "done": done, "total": len(todo) + len(done),
            "kinds": kinds}


def domains():
    """The non-film makers: voice, music, sfx, image, mesh.

    Each is a descriptor naming its workflow, its node mapping and its fields. The page
    is generic - adding a sixth is a JSON file, not a feature.
    """
    d = f"{HERE}/domains"
    if not os.path.isdir(d):
        return []
    out = []
    for fn in sorted(os.listdir(d)):
        if not fn.endswith(".json"):
            continue
        try:
            out.append(json.load(open(f"{d}/{fn}", encoding="utf-8")))
        except Exception as e:
            out.append({"id": fn[:-5], "name": fn[:-5], "desc": f"UNREADABLE: {e}"})
    return out


def gallery():
    """Every generation, newest first, with the full recipe that produced it.

    Read fresh from the append-only manifest on each request, so a run in progress shows
    up on refresh without restarting anything. A malformed line is skipped rather than
    taking the whole endpoint down - the writer appends while this reads, so a torn final
    line is normal rather than exceptional.
    """
    # Phase 5: the manifest recorded 1,828 of 3,612 real generations - the library's
    # disk discovery is the canonical record, so this endpoint reads THAT. The manifest
    # file survives only as the /make flow's newest-record handshake with domain_gen.
    try:
        sys.path.insert(0, f"{HERE}/_tools")
        import library_index as _li
        return _li.payload().get("items", [])
    except Exception:
        traceback.print_exc()
        return []


def templates():
    """Clickable scene templates - a bundle that sets many variables at once AND brings
    its own shots, so you start from something that works instead of a blank page.

    Each is shown with a rendered example and its full settings visible, the way a model
    page shows the prompt that made the picture. The settings are not hidden behind the
    thumbnail: seeing exactly which knobs produced it is the point, because that is what
    lets you change one of them on purpose.

    A template is expanded by the WIZARD into ordinary .movie text. Nothing downstream
    knows templates exist, so a film stays a readable text file you can hand-edit.
    """
    d = f"{HERE}/templates"
    if not os.path.isdir(d):
        return []
    out = []
    for fn in sorted(os.listdir(d)):
        if not fn.endswith(".json"):
            continue
        try:
            t = json.load(open(f"{d}/{fn}", encoding="utf-8"))
        except Exception as e:
            out.append({"id": fn[:-5], "name": fn[:-5],
                        "desc": f"UNREADABLE: {e}", "status": "error"})
            continue
        for ext in (".webp", ".jpg", ".png", ".mp4"):
            p = f"{HERE}/samples/templates/{t.get('id', fn[:-5])}{ext}"
            if os.path.exists(p):
                t["sample"] = f"/samples/templates/{t.get('id', fn[:-5])}{ext}"
                break
        out.append(t)
    return out


SAMPLE_URL = re.compile(r"^/samples/styles/[A-Za-z0-9._-]+$")



def places():
    """Every place card, with whatever renders exist stamped on it.

    Places carry BOTH a danbooru `tags` string and a `prose` string because the two image
    engines want opposite prompt formats, and place_examples.py renders each location on
    both. The page shows the pair side by side, so the API hands back the card unchanged
    and lets the page decide - the examples dict is already written onto the card by the
    renderer, keyed by engine.
    """
    d = f"{HERE}/places"
    out = []
    if os.path.isdir(d):
        for fn_ in sorted(os.listdir(d)):
            if not fn_.endswith(".json"):
                continue
            try:
                with open(os.path.join(d, fn_), encoding="utf-8") as f:
                    out.append(json.load(f))
            except Exception:
                pass
    fams = sorted({p.get("family") or p.get("kind") for p in out if p.get("family") or p.get("kind")})
    return {"places": out, "families": fams, "count": len(out)}

def styles():
    """The style library, with each card's per-engine example CHECKED AGAINST DISK.

    Deliberately not part of GROUPS/library(). That loop resolves one `sample` string by
    trying <id>.webp, and for styles the plain copy beside the two suffixed ones is not
    reliably the render from the engine the card routes to - 19 of 131 disagree with their
    own `engine` field. A page that wants to show "what this style looks like" has to pick
    through the card, so it needs both engines, not one guess. Hence `examples` here rather
    than `sample`, and hence a separate endpoint.

    _control is returned separately: it is the no-style baseline every other example in the
    library is read against, not a style you can pick.
    """
    d = f"{HERE}/styles"
    if not os.path.isdir(d):
        return {"styles": [], "families": [], "count": 0, "control": None}
    out, control = [], None
    for fn in sorted(os.listdir(d)):
        if not fn.endswith(".json"):
            continue
        try:
            c = json.load(open(f"{d}/{fn}", encoding="utf-8"))
        except Exception as e:
            c = {"id": fn[:-5], "name": fn[:-5], "status": "error",
                 "means": f"UNREADABLE: {e}"}
        if not c.get("id"):
            c["id"] = fn[:-5]
        # Only claim an example the browser can actually load. The card is authored by
        # hand, so a path in it may name a file that was never rendered or was deleted.
        declared = c.get("examples") if isinstance(c.get("examples"), dict) else {}
        have = {}
        for eng, url in declared.items():
            if isinstance(url, str) and SAMPLE_URL.match(url) \
                    and os.path.isfile(f"{HERE}{url}"):
                have[eng] = url
        for eng in ("anime", "qwen"):
            if eng not in have:
                url = f"/samples/styles/{c['id']}__{eng}.webp"
                if os.path.isfile(f"{HERE}{url}"):
                    have[eng] = url
        c["examples"] = have
        if c["id"] == "_control":
            control = c
        else:
            out.append(c)
    fams = sorted({c.get("family") for c in out if c.get("family")})
    return {"styles": out, "families": fams, "count": len(out), "control": control}


LORA_FILES = os.path.expanduser(
    os.environ.get("COMFY_ROOT", "~/ComfyUI")) + "/models/loras"


def loras():
    """The LoRA library, with every card CHECKED AGAINST THE FILES ON DISK.

    A LoRA is a delta on specific weights, so a card is only useful if the .safetensors it
    names is actually there - and a library that lists a file nobody can load is worse than
    no library, because it looks authoritative. Hence `installed` on every card, recomputed
    from the directory on every request rather than recorded in the JSON.

    `installed` is None, not False, when the loras directory cannot be read at all: not
    knowing is a different claim from knowing it is absent, and the page says so differently.

    `uncarded` is the other half of the same honesty - safetensors sitting in models/loras
    that no card describes. Those are the ones nobody can find.
    """
    d = f"{HERE}/loras"
    try:
        on_disk = {f: os.path.getsize(f"{LORA_FILES}/{f}")
                   for f in os.listdir(LORA_FILES) if f.endswith(".safetensors")}
    except OSError:
        on_disk = None
    out = []
    if os.path.isdir(d):
        for fn in sorted(os.listdir(d)):
            if not fn.endswith(".json"):
                continue
            try:
                c = json.load(open(f"{d}/{fn}", encoding="utf-8"))
                if not isinstance(c, dict):
                    raise ValueError("not a JSON object")
            except Exception as e:
                c = {"id": fn[:-5], "name": fn[:-5], "status": "unavailable",
                     "means": f"UNREADABLE CARD: {e}"}
            if not c.get("id"):
                c["id"] = fn[:-5]
            f = c.get("file") or ""
            if on_disk is None:
                c["installed"], c["file_size"] = None, None
            else:
                c["installed"] = bool(f) and f in on_disk
                c["file_size"] = on_disk.get(f)
            out.append(c)
    carded = {c.get("file") for c in out}
    return {"loras": out,
            "kinds": sorted({c.get("kind") for c in out if c.get("kind")}),
            "bases": sorted({c.get("base_model") for c in out if c.get("base_model")}),
            "count": len(out),
            "uncarded": sorted(f for f in (on_disk or {}) if f not in carded),
            "lora_dir": LORA_FILES}


def capabilities():
    """What this box can generate, taught rather than listed.

    Two files, deliberately kept separate:

      studio/capabilities.json         written by capability_scan.py. A read-only
        catalogue of ~/ComfyUI/output/claude-generated. Every model name, cost, VRAM
        figure, workflow file and exposure judgement comes from there and nothing here
        invents any of them.

      studio/samples/capabilities/index.json   written by capability_publish.py. The
        teaching layer: which group a capability belongs to, where it sits in that group
        from simplest to most advanced, one plain sentence, why you would want it, and
        the PUBLISHED COPIES of the samples.

    The split is the point. The archive lives outside git and gets cleaned, so a page
    built straight off the catalogue would show empty boxes the first time somebody tidies
    the output tree. The page renders copies under /samples/capabilities/ instead, and if
    the index has not been built this route says which command builds it rather than
    answering 200 with cards that have no pictures.

    Read from disk per request like every other route here, so re-running either tool
    shows up on a refresh instead of on a restart.

    Returns (payload, status) - the only route that needs a status the caller can vary.
    """
    cat_p = f"{HERE}/capabilities.json"
    idx_p = f"{HERE}/samples/capabilities/index.json"
    if not os.path.exists(cat_p):
        return ({"error": "studio/capabilities.json has not been built",
                 "fix": "python3 studio/_tools/capability_scan.py",
                 "groups": [], "capabilities": []}, 404)
    try:
        with open(cat_p, encoding="utf-8") as f:
            cat = json.load(f)
    except Exception as e:                                          # noqa: BLE001
        return ({"error": "capabilities.json is unreadable: %r" % (e,),
                 "groups": [], "capabilities": []}, 500)

    idx, idx_error = None, None
    if not os.path.exists(idx_p):
        idx_error = ("studio/samples/capabilities/index.json has not been built - the page "
                     "has no pictures until it is")
    else:
        try:
            with open(idx_p, encoding="utf-8") as f:
                idx = json.load(f)
        except Exception as e:                                      # noqa: BLE001
            idx_error = "index.json is unreadable: %r" % (e,)

    entries = (idx or {}).get("entries") or {}
    groups = (idx or {}).get("groups") or []
    rank = {g["id"]: i for i, g in enumerate(groups)}

    merged, untaught = [], []
    for c in cat.get("capabilities", []):
        c = dict(c)
        t = entries.get(c.get("id"))
        if t:
            # The curriculum owns presentation, the catalogue owns facts, and the two
            # never write the same key - so a merge conflict is impossible by design.
            c["group"] = t.get("group")
            c["order"] = t.get("order")
            c["one_line"] = t.get("one_line")
            c["why_you_want_it"] = t.get("why")
            c["published"] = t.get("sample")
            c["companions"] = t.get("companions") or []
            c["text_companion"] = t.get("text_companion")
            c["no_sample"] = t.get("no_sample")
        else:
            # A capability the archive knows about that the curriculum has not placed.
            # Reported rather than dropped: silently disappearing is how a page ends up
            # claiming to be complete while it is not.
            c["group"] = None
            untaught.append(c.get("id"))
        merged.append(c)
    merged.sort(key=lambda c: (rank.get(c.get("group"), 99),
                               99 if c.get("order") is None else c["order"],
                               c.get("id") or ""))

    out = dict(cat)
    out["capabilities"] = merged
    out["groups"] = groups
    out["untaught"] = untaught
    out["published"] = {
        "generated": (idx or {}).get("generated"),
        "files": (idx or {}).get("published_files"),
        "missing": (idx or {}).get("missing_files"),
        "log": (idx or {}).get("log") or [],
        "error": idx_error,
        "fix": "python3 studio/_tools/capability_publish.py",
    }
    return (capabilities_3d(out), 200)


def capabilities_3d(cat):
    """Tell the capabilities page where the 3D work became visible.

    studio/capabilities.json is capability_scan.py's output. It records
    21-3d-generation as `script-only` with `app_page: null`, which was true when it was
    scanned. Half of it still is: GENERATING a mesh is script-only - terra_mesh.py drives
    ComfyUI and no page queues a Hunyuan3D job - so the exposure VALUE is left alone
    rather than upgraded, because upgrading it would have the page claim something the
    app cannot do.

    What changed is that the results are no longer invisible: /model3d shows the source
    set, every mesh candidate with its renders and diagnostics, the failures, the
    printability audit and the files. That is exactly what `app_page` is for on this
    catalogue - 17-lora-mechanics and 31-character-identity already use it the same way -
    so it is filled in here and the capability card renders it in its own exposure box.

    Corrected in the server rather than in capabilities.json because that file is a
    scanner's output and the next scan would silently drop an edit. Applied only when
    the page is actually on disk, so deleting model3d.html takes the claim with it.
    """
    if not os.path.exists(f"{HERE}/model3d.html"):
        return cat
    page = {
        "page": "/model3d",
        "tier": "app",
        "note": "The RESULTS are in the app: /model3d shows the source images, every "
                "mesh candidate with its orbit render and its diagnostics, the nine that "
                "failed, the printability audit and the STL/3MF/GLB downloads. "
                "GENERATING a new one is still script-only - studio/_tools/terra_mesh.py "
                "drives ComfyUI and no page queues it, which is why the exposure above "
                "still reads script only. The recipe for the next character is "
                "craft/CHARACTER_TO_PRINT.md.",
    }
    for key in ("capabilities", "not_exposed_in_app"):
        for c in cat.get(key) or []:
            if isinstance(c, dict) and c.get("id") == "21-3d-generation":
                c["app_page"] = page
    return cat


def cards():
    d = f"{HERE}/cards"
    if not os.path.isdir(d):
        return []
    return [json.load(open(f"{d}/{f}", encoding="utf-8"))
            for f in sorted(os.listdir(d)) if f.endswith(".json")]


def variables():
    p = f"{HERE}/variables.json"
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else []


# Parameter names that mean "the layer selection", for _call_resolve below.
SELECTION_ARGS = ("sel", "selection", "req", "request", "body", "spec", "picks", "layers")


def _call_resolve(fn, req):
    """Call compose.resolve() however it ended up being written.

    This endpoint and studio/compose.py were built in parallel against a written contract.
    The contract fixes the request KEYS and the response SHAPE, which are what this page and
    the wizard depend on; it does not fix the argument style, which nothing depends on. As
    shipped it is resolve(libs, sel) - a library handle the module loads for itself when it
    is not given one, then the selection - so that is what the last branch handles.
    """
    try:
        params = inspect.signature(fn).parameters
    except (TypeError, ValueError):
        return fn(req)
    if any(p.kind == p.VAR_KEYWORD for p in params.values()):
        return fn(**req)                                    # resolve(**kw)
    named = [n for n, p in params.items()
             if p.kind in (p.POSITIONAL_OR_KEYWORD, p.KEYWORD_ONLY)]
    if set(named) & set(req):                               # resolve(style=..., place=...)
        return fn(**{k: v for k, v in req.items() if k in named})
    if len(named) == 1:                                     # resolve(sel)
        return fn(req)
    # resolve(libs, sel). Pass the selection by name so its position does not matter, and
    # leave every other argument to its own default handling.
    for n in named:
        if n.lower() in SELECTION_ARGS:
            return fn(**{n: req, **{o: None for o in named if o != n}})
    return fn(*([None] * (len(named) - 1)), req)            # last argument wins


def movies():
    d = f"{HERE}/movies"
    if not os.path.isdir(d):
        return []
    return [{"name": f[:-6], "text": open(f"{d}/{f}", encoding="utf-8").read()}
            for f in sorted(os.listdir(d)) if f.endswith(".movie")]


def nav_video(html):
    """Put a `video` link in the header nav of a page that has one, without editing it.

    /video is a page like /styles or /gallery and belongs in the same nav, but the nav
    lives inside ten hand-written HTML files owned by other work. Injecting here means the
    route is the only thing that changed: no page file is touched, and a page that later
    grows its own /video link is left exactly as it is.

    Conservative on purpose - it inserts before the first nav anchor it recognises and
    otherwise returns the document byte-for-byte unchanged, because a nav link is not worth
    the risk of corrupting a page.
    """
    if 'href="/video"' in html:
        return html
    for anchor in ('<a href="/gallery"', '<a href="/">'):
        i = html.find(anchor)
        if i < 0:
            continue
        # Match the case of the neighbour so `Gallery` does not sit next to `video`.
        m = re.search(r">\s*([A-Za-z])", html[i:i + 200])
        word = "Video" if (m and m.group(1).isupper()) else "video"
        return html[:i] + '<a href="/video">%s</a>' % word + html[i:]
    return html


def nav_dossier(html):
    """Put a `dossier` link in the nav, the same way and for the same reason as nav_video.

    /character/<id> is a page like /styles or /cast and belongs in the same nav, and the
    nav lives in ten hand-written files owned by other work. Injected rather than edited.
    """
    if 'href="/character' in html:
        return html
    for anchor in ('<a href="/cast"', '<a href="/gallery"', '<a href="/">'):
        i = html.find(anchor)
        if i < 0:
            continue
        m = re.search(r">\s*([A-Za-z])", html[i:i + 200])
        word = "Dossier" if (m and m.group(1).isupper()) else "dossier"
        return html[:i] + '<a href="/character">%s</a>' % word + html[i:]
    return html


# The cast page's per-character action row, and the dossier link that belongs beside its
# "direct a scene" link. Matched against the exact anchor cast.html writes, inside a JS
# template literal, so `${esc(c.id)}` resolves in the page's own scope. If cast.html ever
# rewrites that line the match simply fails and the page is served untouched - the same
# contract nav_video works under, because a cross-page link is not worth the risk of
# corrupting somebody else's file.
CAST_ACT = '<a href="/wizard" title="open the wizard, then pick ${esc(c.id)} on its cast step">'
CAST_DOSSIER = ('<a href="/character/${esc(c.id)}" title="everything measured about '
                '${esc(c.id)}">dossier &rarr;</a>')


def cast_dossier_link(html):
    if "/character/" in html or CAST_ACT not in html:
        return html
    return html.replace(CAST_ACT, CAST_DOSSIER + CAST_ACT, 1)


def nav_model3d(html):
    """Put a `3D print` link in the header nav, the same way and for the same reason as
    nav_video and nav_dossier above.

    /model3d is a page like /video or /gallery and belongs in the same nav, but the nav
    lives inside sixteen hand-written HTML files owned by other work. Injecting here
    means the route is the only thing that changed: no page file is touched, and a page
    that later grows its own link is left exactly as it is.

    Anchored beside /video because it is the other page of rendered output, and because
    _page runs nav_video first - so on a page that had neither, the two arrive next to
    each other rather than at opposite ends of the row.
    """
    if 'href="/model3d"' in html:
        return html
    for anchor in ('<a href="/video"', '<a href="/gallery"', '<a href="/">'):
        i = html.find(anchor)
        if i < 0:
            continue
        return html[:i] + '<a href="/model3d">3D print</a>' + html[i:]
    return html


def nav_library(html):
    """A `library` link in the header nav, the same way as nav_model3d."""
    if 'href="/library"' in html:
        return html
    for a in ('<a href="/gallery"', '<a href="/make3d"', '<a href="/">'):
        i = html.find(a)
        if i < 0:
            continue
        return html[:i] + '<a href="/library">library</a>' + html[i:]
    return html


def nav_encyclopedia(html):
    """An `encyclopedia` link in the header nav, the same way as nav_library."""
    if 'href="/encyclopedia"' in html:
        return html
    for a in ('<a href="/library"', '<a href="/gallery"', '<a href="/">'):
        i = html.find(a)
        if i < 0:
            continue
        return html[:i] + '<a href="/encyclopedia">encyclopedia</a>' + html[i:]
    return html


def nav_three(html):
    """A `3d` link in the header nav, the same way and for the same reason as
    nav_model3d: the nav lives inside eighteen hand-written HTML files owned by other
    work, so injecting here means the route is the only thing that changed.

    Anchored BEFORE /make3d and /model3d because /three is the section those two pages
    are tools inside - a reader who lands on either should be able to see the way up."""
    if 'href="/three"' in html:
        return html
    for a in ('<a href="/make3d"', '<a href="/model3d"', '<a href="/gallery"',
              '<a href="/">'):
        i = html.find(a)
        if i < 0:
            continue
        return html[:i] + '<a href="/three">3d</a>' + html[i:]
    return html


def nav_make3d(html):
    """A `make 3d` link in the header nav, the same way as nav_model3d."""
    if 'href="/make3d"' in html:
        return html
    for a in ('<a href="/model3d"', '<a href="/make"', '<a href="/gallery"', '<a href="/">'):
        i = html.find(a)
        if i < 0:
            continue
        return html[:i] + '<a href="/make3d">make 3d</a>' + html[i:]
    return html


def nav_capabilities(html):
    """Put a `capabilities` link in the header nav, the same way and for the same reason
    as nav_video and nav_dossier.

    /capabilities is the introduction to everything the box can generate and belongs in
    the nav of every page, but the nav lives inside fourteen hand-written HTML files owned
    by other work - and another agent is editing several of them right now. Injecting here
    means the route is the only thing that changed: no page file is touched, and a page
    that later grows its own link is left exactly as it is.

    Anchored early in the nav on purpose. This is the page you send someone to first.
    """
    if 'href="/capabilities"' in html:
        return html
    for anchor in ('<a href="/styles"', '<a href="/loras"', '<a href="/gallery"',
                   '<a href="/">'):
        i = html.find(anchor)
        if i < 0:
            continue
        m = re.search(r">\s*([A-Za-z])", html[i:i + 200])
        word = "Capabilities" if (m and m.group(1).isupper()) else "capabilities"
        return html[:i] + '<a href="/capabilities">%s</a>' % word + html[i:]
    return html


# The hub's hero row, and the capabilities link that belongs beside it. A nav link alone
# is not enough for the front page: "what can this thing even do" is the first question a
# newcomer has, and it deserves a button next to "Direct a scene" rather than one word in
# a row of thirteen. Matched against the exact anchor app.html writes; if that file ever
# rewrites the line the match simply fails and the page is served untouched - the same
# contract nav_video works under.
HUB_MAKE = '<a class="go alt" href="/make">Make something else</a>'
HUB_CAPS = ('<a class="go alt" href="/capabilities">See everything it can generate '
            '&rarr;</a>')


def hub_capabilities(html):
    # Test for the BUTTON, not for any link to the route. _page runs
    # nav_capabilities first, so by the time this sees the hub there is already a
    # /capabilities link in the header nav - guarding on that made this a no-op
    # and the hero button silently never appeared.
    if HUB_CAPS in html or HUB_MAKE not in html:
        return html
    return html.replace(HUB_MAKE, HUB_MAKE + "\n      " + HUB_CAPS, 1)





def _charnew_routes():
    """studio/_tools/charnew_routes.py on demand, like the other _tools importers."""
    return _load_tool_module('charnew_routes')


def _voice_routes():
    """studio/_tools/voice_routes.py on demand, like the other _tools importers."""
    return _load_tool_module('voice_routes')


def _toolbox():
    """studio/_tools/toolbox.py on demand, like the other _tools importers."""
    return _load_tool_module('toolbox')

def _technique_routes():
    """studio/_tools/technique_routes.py - how shots were built, and the
    example take that proves each one works."""
    return _load_tool_module('technique_routes')


def _spec_routes():
    """studio/_tools/spec_routes.py - the shot-spec editor, English side and machine side."""
    return _load_tool_module('spec_routes')


def _foundry_routes():
    """studio/_tools/foundry_routes.py on demand - the selector-driven asset creator."""
    return _load_tool_module('foundry_routes')


def _film_routes():
    """studio/_tools/film_routes.py on demand, like _story_routes. The shot-by-shot
    editor: films/scenes/shots/takes across the 2.5-era engines."""
    return _load_tool_module('film_routes')


def _story_routes():
    """studio/_tools/story_routes.py on demand, like _guides and _generate_routes.

    Returning None rather than raising keeps a broken editor from taking the whole studio
    down: every other page still serves and /story reports plainly that it is unavailable.
    """
    return _load_tool_module('story_routes')

def _generate_routes():
    """Import studio/_tools/generate_routes.py on demand, the same way _guides does.

    Returning None rather than raising keeps a missing or broken module from taking the
    whole studio down - every other page still serves, and /generate reports plainly that
    its backend is unavailable.
    """
    return _load_tool_module('generate_routes')

# Route modules are imported once and reloaded ONLY when their file changes on disk.
#
# They were being reloaded on every request, and each of them keeps its job table in a
# module-level dict - so the table was reset between the POST that started a job and the
# GET that asked how it was going, and every progress poll in the app answered "no such
# job". The renders still completed, because the worker thread holds its own reference to
# the old module, so the symptom looked like a routing bug rather than a state bug.
_MODCACHE = {}


def _load_tool_module(name):
    import importlib.util
    path = os.path.join(HERE, "_tools", name + ".py")
    try:
        mtime = os.path.getmtime(path)
    except OSError:
        return None
    mod, seen = _MODCACHE.get(name, (None, None))
    if mod is not None and seen == mtime:
        return mod
    try:
        sys.path.insert(0, os.path.join(HERE, "_tools"))
        if mod is None:
            mod = importlib.import_module(name)
        else:
            mod = importlib.reload(mod)
        _MODCACHE[name] = (mod, mtime)
        return mod
    except Exception:
        traceback.print_exc()
        return None


def _guides():
    """studio/_tools/guides.py, or None. Reloaded per request like the composer, so
    editing a guide markdown file and refreshing shows the change - the same contract
    the rest of this server works under.

    Optional on purpose. If the tool is missing or broken every page still serves; the
    only thing lost is the `how this page works` link and the /guide route."""
    d = f"{HERE}/_tools"
    if d not in sys.path:
        sys.path.insert(0, d)
    try:
        import guides as g
        if getattr(g, "__file__", "").startswith(d):
            g = importlib.reload(g)
        return g if callable(getattr(g, "payload", None)) else None
    except Exception:
        return None



# ── the one nav ─────────────────────────────────────────────────────────────────────
# Every page route renders this same bar. Grouped only so thirty links stay legible;
# the groups carry no meaning yet and the duplicates (make/make3d/model3d/three,
# cast/character/newchar, library/gallery/encyclopedia) are deliberately all listed
# rather than quietly dropped - organising them is a separate pass.
STUDIO_NAV = [
    ("studio", [
        ("/", "studio", "app.html"),
        ("/capabilities", "capabilities", "capabilities.html"),
        ("/guide", "guide", "guide.html"),
        ("/docs", "docs", "docs.html"),
        ("/changelog", "changelog", "changelog.html"),
    ]),
    ("direct", [
        ("/wizard", "wizard", "wizard.html"),
        ("/story", "story", "story_editor.html"),
        ("/film", "film", "film_editor.html"),
        ("/specs", "specs", "specs.html"),
        ("/techniques", "techniques", "techniques.html"),
        ("/foundry", "foundry", "foundry.html"),
        ("/generate", "generate", "generate.html"),
    ]),
    ("cast", [
        ("/characters", "characters", "characters.html"),
        ("/verify/motion", "motion", "motion.html"),
        ("/voices", "voices", "voices.html"),
        ("/identity", "identity", "identity.html"),
        ("/verify", "verify", "verify.html"),
    ]),
    ("look", [
        ("/styles", "styles", "styles.html"),
        ("/places", "places", "places.html"),
        ("/loras", "loras", "loras.html"),
        ("/tags", "tags", "tags.html"),
    ]),
    ("make", [
        ("/make", "make", "make.html"),
        ("/video", "video", "video.html"),
        ("/shorts", "shorts", "shorts.html"),
    ]),
    ("3d", [
        ("/make3d", "make 3d", "make3d.html"),
        ("/model3d", "models", "model3d.html"),
        ("/three/", "three", "three.html"),
    ]),
    ("library", [
        ("/library", "library", "library.html"),
        ("/gallery", "gallery", None),
        ("/encyclopedia", "encyclopedia", "encyclopedia.html"),
    ]),
    ("tools", [
        ("/tools", "tools", "tools.html"),
    ]),
]

STUDIO_NAV_CSS = """<style id="studionav-css">
#studionav{position:sticky;top:0;z-index:9999;background:#0b0b10;
  border-bottom:1px solid #2a2a36;padding:6px 14px;display:flex;flex-wrap:wrap;
  align-items:center;gap:2px 0;
  font:13px/1.4 system-ui,-apple-system,"Segoe UI",sans-serif}
#studionav .g{display:flex;align-items:center;gap:2px;padding:0 9px;
  border-right:1px solid #23232e}
#studionav .g:last-child{border-right:0}
#studionav .gl{color:#585868;font-size:9px;letter-spacing:.11em;
  text-transform:uppercase;margin-right:5px;user-select:none}
#studionav a{color:#9aa0b4;text-decoration:none;padding:3px 7px;border-radius:5px;
  white-space:nowrap}
#studionav a:hover{color:#eaeaf2;background:#1c1c26}
#studionav a.on{color:#0d0d12;background:#9fb3ff;font-weight:600}
</style>"""


def studio_nav(page=None, path=None):
    """The bar itself. `page` is the html filename being served, `path` the URL -
    either identifies the current entry."""
    out = ['<nav id="studionav">']
    for label, items in STUDIO_NAV:
        out.append('<span class="g"><span class="gl">%s</span>' % label)
        for href, text, owner in items:
            on = (owner and owner == page) or (path and path == href)
            out.append('<a href="%s"%s>%s</a>'
                       % (href, ' class="on"' if on else "", text))
        out.append("</span>")
    out.append("</nav>")
    return STUDIO_NAV_CSS + "".join(out)


# Links a page hand-wrote to any endpoint the bar now owns. Stripped from the page's
# own header so the bar is not shadowed by a second, staler copy of itself.
_NAV_HREFS = {href for _, items in STUDIO_NAV for href, _, _ in items}
_NAV_HREFS |= {h.rstrip("/") for h in _NAV_HREFS if h != "/"}
_NAV_HREFS |= {h + ".html" for h in list(_NAV_HREFS) if h != "/"}
_A_TAG = re.compile(r'<a\s[^>]*href="([^"]+)"[^>]*>.*?</a>', re.S | re.I)
_HEADER = re.compile(r"<header\b.*?</header>", re.S | re.I)
_OLD_NAV = re.compile(r'<nav\b(?![^>]*id="studionav")[^>]*>.*?</nav>', re.S | re.I)


def _owns(href):
    return href in _NAV_HREFS or href.rstrip("/") in _NAV_HREFS


# Anything that means the container earns its keep: a control, a heading, an image,
# a live region a script writes into. story_editor's toolbar and docs' JS rail both
# live inside the very elements a naive nav-stripper would delete.
_KEEPS = re.compile(r"<(select|button|input|textarea|form|img|svg|h1|h2|h3|canvas|"
                    r"video|table)\b", re.I)
_HAS_ID = re.compile(r'<[a-z]+\b[^>]*\sid="', re.I)
_TAGS = re.compile(r"<[^>]+>")


def _strip_links(chunk):
    """Remove only the endpoint links, then the shell if nothing real is left."""
    stripped = _A_TAG.sub(lambda a: "" if _owns(a.group(1)) else a.group(0), chunk)
    if stripped == chunk:
        return chunk
    inner = re.sub(r"^<[^>]+>|</[a-z]+>$", "", stripped.strip(), flags=re.I)
    if _KEEPS.search(inner) or _HAS_ID.search(inner) or _TAGS.sub("", inner).strip():
        return stripped                      # it holds something else - keep it
    return ""                                # an empty shell, drop it


def _strip_page_nav(html):
    html = _OLD_NAV.sub(lambda m: _strip_links(m.group(0)), html, count=1)
    return _HEADER.sub(lambda m: _A_TAG.sub(
        lambda a: "" if _owns(a.group(1)) else a.group(0), m.group(0)), html, count=1)


def apply_studio_nav(html, page=None, path=None):
    html = _strip_page_nav(html)
    bar = studio_nav(page, path)
    m = re.search(r"<body\b[^>]*>", html, re.I)
    if m:
        return html[:m.end()] + bar + html[m.end():]
    return bar + html



class H(http.server.SimpleHTTPRequestHandler):
    def _page(self, name):
        """Serve one of the hand-written pages, with the video and dossier links injected
        into its nav, and the per-character dossier link into the cast page's card."""
        p = f"{HERE}/{name}"
        if not os.path.exists(p):
            return self._send(f"{name} is missing".encode(), 500, "text/plain")
        with open(p, encoding="utf-8") as f:
            html = f.read()
        # One canonical bar for every page, from STUDIO_NAV. This replaces the seven
        # nav_* splicers that used to hunt for an anchor link in each hand-written
        # header - they could only add an endpoint to the pages that happened to
        # carry the right anchor, which is why nothing linked to /foundry.
        html = apply_studio_nav(html, page=name)
        if name == "cast.html":
            html = cast_dossier_link(html)
        if name == "app.html":
            html = hub_capabilities(html)
        # A `how this page works` link, injected the same way and for the same reason as
        # nav_video and nav_dossier above: the nav lives in ten hand-written files owned
        # by other work. guides.page_link returns the document unchanged if it does not
        # recognise the nav, so a page rewritten later simply stops carrying the link.
        g = _guides()
        if g:
            try:
                html = g.page_link(html, name)
            except Exception:
                pass
        return self._send(html.encode("utf-8"), 200, "text/html; charset=utf-8")

    def _send_file(self, fp, ctype):
        """Send a file, honouring a Range request.

        Video needs this. `_send` answers every request with the whole file and no
        Accept-Ranges, so a browser cannot seek a clip without downloading all of it, and
        `preload="metadata"` - which asks for a few KB of header - pulls the entire mp4
        instead. Across a page of 165 clips that is the difference between a few hundred KB
        and about a gigabyte.
        """
        size = os.path.getsize(fp)
        rng = self.headers.get("Range", "")
        m = re.match(r"bytes=(\d*)-(\d*)$", rng.strip()) if rng else None
        start, end = 0, size - 1
        partial = False
        if m and (m.group(1) or m.group(2)):
            if m.group(1):
                start = int(m.group(1))
                if m.group(2):
                    end = min(int(m.group(2)), size - 1)
            else:                                   # bytes=-N -> the last N bytes
                start = max(size - int(m.group(2)), 0)
            if start >= size or start > end:
                self.send_response(416)
                self.send_header("Content-Range", "bytes */%d" % size)
                self.send_header("Content-Length", "0")
                self.end_headers()
                return
            partial = True
        length = end - start + 1
        self.send_response(206 if partial else 200)
        self.send_header("Content-Type", ctype)
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Length", str(length))
        if partial:
            self.send_header("Content-Range", "bytes %d-%d/%d" % (start, end, size))
        # Samples are immutable render output keyed by filename, so unlike the JSON
        # routes they are worth caching - the page reloads a lot while you compare clips.
        self.send_header("Cache-Control", "public, max-age=3600")
        self.end_headers()
        if getattr(self, "_head_only", False):
            return
        with open(fp, "rb") as f:
            f.seek(start)
            left = length
            while left > 0:
                chunk = f.read(min(262144, left))
                if not chunk:
                    break
                try:
                    self.wfile.write(chunk)
                except (BrokenPipeError, ConnectionResetError):
                    return          # the browser stopped the clip; not an error
                left -= len(chunk)

    def _send(self, obj, code=200, ctype="application/json"):
        body = obj if isinstance(obj, bytes) else json.dumps(obj).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        # A HEAD reply carries the headers and no body, so the same route table can
        # answer both without every branch having to know which it is serving.
        if not getattr(self, "_head_only", False):
            self.wfile.write(body)

    def do_HEAD(self):
        """Answer HEAD off the same routes as GET.

        Without this the class inherits SimpleHTTPRequestHandler's do_HEAD, which
        resolves against the process working directory instead of the route table -
        so every route in the app answered `404 File not found` to HEAD while GET
        returned 200. Browsers fetch with GET so nothing visibly broke, but any
        health check, uptime monitor or link checker saw the whole app as missing.
        """
        self._head_only = True
        try:
            self.do_GET()
        finally:
            self._head_only = False

    def do_GET(self):
        path = urllib.parse.urlparse(self.path).path
        if path in ("/", "/index.html"):
            return self._page("app.html")
        # The guides. /guide is the index and /guide/<slug> one guide; both serve the same
        # shell, which reads the slug off its own path. The markdown lives in
        # studio/guides/ and is rendered by studio/_tools/guides.py.
        if path == "/guide" or path.startswith("/guide/"):
            return self._page("guide.html")
        # /generate - start, watch and stop an unattended generation run. The routes live
        # in studio/_tools/generate_routes.py because they own a CHILD PROCESS, which
        # nothing else in this server does.
        if path == "/generate":
            return self._page("generate.html")
        if path.startswith("/api/generate/"):
            gr = _generate_routes()
            if not gr:
                return self._send({"error": "studio/_tools/generate_routes.py is "
                                            "unavailable"}, 500)
            leaf = path[len("/api/generate/"):]
            if leaf == "status":
                return self._send(gr.status())
            if leaf == "space":
                body, code = gr.space()
                return self._send(body, code)
            if leaf == "options":
                body, code = gr.options()
                return self._send(body, code)
            if leaf == "list":
                body, code = gr.listing()
                return self._send(body, code)
            if leaf.startswith("zip/"):
                fp = gr.zip_path(leaf[4:])
                if not fp:
                    return self._send({"error": "no such bundle"}, 404)
                return self._send_file(fp, "application/zip")
            return self._send({"error": "unknown generate route"}, 404)
        # /foundry - build characters, places, costumes and props from selectors,
        # render their seed packs, and send them into films.
        # /techniques - how shots were built, with the shot attached
        if path == "/techniques":
            return self._page("techniques.html")
        if path == "/api/technique" or path.startswith("/api/technique/"):
            tr = _technique_routes()
            if not tr:
                return self._send({"error": "technique_routes.py unavailable"}, 500)
            rest = path[len("/api/technique"):].strip("/").split("/")
            try:
                if rest[0] in ("", "list"):
                    body, code = tr.listing()
                else:
                    body, code = tr.one(rest[0])
            except Exception as e:
                traceback.print_exc()
                return self._send({"error": str(e)[:300]}, 500)
            return self._send(body, code)

        # /specs - the promises each shot has to keep, editable in English
        if path == "/specs":
            return self._page("specs.html")
        if path == "/api/spec" or path.startswith("/api/spec/"):
            sr = _spec_routes()
            if not sr:
                return self._send({"error": "studio/_tools/spec_routes.py is "
                                            "unavailable"}, 500)
            rest = path[len("/api/spec"):].strip("/").split("/")
            try:
                if rest[0] == "films":
                    body, code = sr.films()
                elif rest[0] == "tree":
                    body, code = sr.tree(rest[1])
                elif rest[0] == "media":
                    body, code = sr.media(rest[1])
                elif rest[0] == "md":
                    body, code = sr.md(rest[1], rest[2])
                elif rest[0] == "check":
                    body, code = sr.check(rest[1])
                else:
                    body, code = {"error": "unknown spec route"}, 404
            except Exception as e:
                traceback.print_exc()
                return self._send({"error": str(e)[:300]}, 500)
            return self._send(body, code)
        # /characters - the merged roster+dossier. /cast and /character/new are the
        # same page now and redirect, because both are linked from ten hand-written
        # navs and sit in people's history.
        # /verify/motion - the same claim/evidence/verdict shape as the card
        # verifier, for clips instead of panels.
        if path in ("/verify/motion", "/motion", "/motion.html"):
            return self._page("motion.html")
        if path == "/api/motion/clips":
            p = f"{HERE}/motion_verify.json"
            if not os.path.isfile(p):
                return self._send([])
            return self._send(json.load(open(p, encoding="utf-8")))
        if path == "/api/motion/verdicts":
            p = f"{HERE}/motion_verdicts.json"
            if not os.path.isfile(p):
                return self._send({})
            return self._send(json.load(open(p, encoding="utf-8")))
        if path.startswith("/api/motion/media/"):
            rel = urllib.parse.unquote(path[len("/api/motion/media/"):])
            base = os.path.realpath(HERE)
            fp = os.path.realpath(os.path.join(base, rel))
            if not (fp.startswith(base + os.sep) and os.path.isfile(fp)):
                return self._send({"error": "no such clip"}, 404)
            return self._send_file(fp, MIME.get(os.path.splitext(fp)[1].lower(),
                                                "application/octet-stream"))
        if path in ("/characters", "/characters.html"):
            return self._page("characters.html")
        if path in ("/cast", "/cast.html", "/character/new", "/newchar"):
            self.send_response(302)
            self.send_header("Location", "/characters")
            self.end_headers()
            return
        if path == "/foundry":
            return self._page("foundry.html")
        if path.startswith("/foundry/media/"):
            rel = urllib.parse.unquote(path[len("/foundry/media/"):])
            base = os.path.realpath(os.path.join(HERE, "foundry"))
            fp = os.path.realpath(os.path.join(base, rel))
            if not (fp.startswith(base + os.sep) and os.path.isfile(fp)):
                return self._send({"error": "no such file"}, 404)
            ext = os.path.splitext(fp)[1].lower()
            return self._send_file(fp, MIME.get(ext, "application/octet-stream"))
        if path == "/api/foundry" or path.startswith("/api/foundry/"):
            fo = _foundry_routes()
            if not fo:
                return self._send({"error": "studio/_tools/foundry_routes.py is "
                                            "unavailable"}, 500)
            rest = path[len("/api/foundry"):].strip("/")
            try:
                if not rest:
                    body, code = fo.listing()
                    return self._send(body, code)
                bits = rest.split("/")
                if bits[0] == "dictionary":
                    body, code = fo.dictionary()
                    return self._send(body, code)
                if bits[0] == "levels":
                    body, code = fo.levels()
                    return self._send(body, code)
                if bits[0] == "roster":
                    body, code = fo.roster()
                    return self._send(body, code)
                if bits[0] == "jobs":
                    body, code = fo.jobs_all()
                    return self._send(body, code)
                if bits[0] == "job" and len(bits) == 2:
                    body, code = fo.job_status(bits[1])
                    return self._send(body, code)
                if len(bits) == 2:
                    body, code = fo.detail(bits[0], bits[1])
                    return self._send(body, code)
            except KeyError as e:
                return self._send({"error": str(e)}, 404)
            except Exception as e:
                traceback.print_exc()
                return self._send({"error": str(e)[:300]}, 500)
            return self._send({"error": "unknown foundry route"}, 404)
        # /film - the shot-by-shot editor on the 2.5-era engines. Same shape as
        # /story: reads are synchronous, renders go through a job table in film_routes.
        if path == "/film":
            return self._page("film_editor.html")
        if path.startswith("/film/media/"):
            # a film's takes and assets, served off its own folder with Range - posters,
            # strips and mp4s. The realpath check keeps it inside that folder.
            rel = urllib.parse.unquote(path[len("/film/media/"):])
            fid, _, sub = rel.partition("/")
            base = os.path.realpath(os.path.join(HERE, "films", fid))
            fp = os.path.realpath(os.path.join(base, sub))
            if not (fp.startswith(base + os.sep) and os.path.isfile(fp)):
                return self._send({"error": "no such file"}, 404)
            ext = os.path.splitext(fp)[1].lower()
            return self._send_file(fp, MIME.get(ext, "application/octet-stream"))
        if path == "/api/film" or path.startswith("/api/film/"):
            fr = _film_routes()
            if not fr:
                return self._send({"error": "studio/_tools/film_routes.py is "
                                            "unavailable"}, 500)
            rest = path[len("/api/film"):].strip("/")
            try:
                if not rest:
                    body, code = fr.list_films()
                    return self._send(body, code)
                bits = rest.split("/")
                if bits[0] == "jobs":
                    body, code = fr.jobs_all()
                    return self._send(body, code)
                if bits[0] == "job" and len(bits) == 2:
                    body, code = fr.job_status(bits[1])
                    return self._send(body, code)
                if bits[0] == "libraries":
                    body, code = fr.libraries()
                    return self._send(body, code)
                if bits[0] == "foundry_assets":
                    body, code = fr.foundry_assets()
                    return self._send(body, code)
                if len(bits) == 1:
                    body, code = fr.tree(bits[0])
                    return self._send(body, code)
                if bits[1] == "shot" and len(bits) == 3:
                    body, code = fr.shot_detail(bits[0], bits[2])
                    return self._send(body, code)
                if bits[1] == "compile" and len(bits) == 3:
                    body, code = fr.compile_shot(bits[0], bits[2])
                    return self._send(body, code)
            except KeyError as e:
                return self._send({"error": str(e)}, 404)
            except Exception as e:
                traceback.print_exc()
                return self._send({"error": str(e)[:300]}, 500)
            return self._send({"error": "unknown film route"}, 404)
        # /story - the scene-by-scene editor. Reads are cheap and synchronous; renders
        # go through a job table in story_routes so the page stays responsive.
        if path == "/story" or path.startswith("/story/"):
            return self._page("story_editor.html")
        if path == "/api/story" or path.startswith("/api/story/"):
            sr = _story_routes()
            if not sr:
                return self._send({"error": "studio/_tools/story_routes.py is "
                                            "unavailable"}, 500)
            rest = path[len("/api/story"):].strip("/")
            try:
                if not rest:
                    body, code = sr.list_stories()
                    return self._send(body, code)
                bits = rest.split("/")
                sid = bits[0]
                if bits[0] == "job" and len(bits) == 2:
                    body, code = sr.job_status(bits[1])
                    return self._send(body, code)
                if bits[0] == "libraries":
                    body, code = sr.libraries()
                    return self._send(body, code)
                if len(bits) == 1:
                    body, code = sr.story_tree(sid)
                    return self._send(body, code)
                if bits[1] == "looks" and len(bits) == 3:
                    body, code = sr.chapter_looks(sid, bits[2])
                    return self._send(body, code)
                if bits[1] == "trans" and len(bits) == 5:
                    fp = sr.trans_file(sid, bits[2], bits[3], bits[4])
                    if not fp:
                        return self._send({"error": "no such transition"}, 404)
                    return self._send_file(fp, "video/mp4")
                if bits[1] == "file" and len(bits) == 2:
                    body, code = sr.save_file(sid)
                    return self._send(body, code)
                if bits[1] == "job" and len(bits) == 3:
                    body, code = sr.job_status(bits[2])
                    return self._send(body, code)
                if bits[1] == "scene" and len(bits) == 4:
                    body, code = sr.scene_detail(sid, bits[2], bits[3])
                    return self._send(body, code)
                if bits[1] == "thumb" and len(bits) == 4:
                    fp = sr.thumb(sid, bits[2], bits[3])
                    if not fp:
                        return self._send({"error": "no thumb"}, 404)
                    return self._send_file(fp, "image/png")
                if bits[1] == "take" and len(bits) == 6:
                    fp = sr.take_file(sid, bits[2], bits[3], bits[4], bits[5])
                    if not fp:
                        return self._send({"error": "no such file"}, 404)
                    return self._send_file(fp, "video/mp4" if fp.endswith(".mp4")
                                           else "image/png")
            except KeyError as e:
                return self._send({"error": str(e)}, 404)
            except Exception as e:
                traceback.print_exc()
                return self._send({"error": str(e)[:300]}, 500)
            return self._send({"error": "unknown story route"}, 404)
        if path in ("/character/new", "/newchar"):
            return self._page("newchar.html")
        if path.startswith("/api/character/"):
            cr = _charnew_routes()
            if cr:
                rest = path[len("/api/character/"):].strip("/")
                bits = rest.split("/")
                try:
                    if rest == "sources":
                        body, code = cr.sources()
                        return self._send(body, code)
                    if rest == "style":
                        body, code = cr.house_style()
                        return self._send(body, code)
                    if bits[0] == "job" and len(bits) == 2:
                        body, code = cr.job_status(bits[1])
                        return self._send(body, code)
                    if bits[0] == "suite" and len(bits) == 2:
                        body, code = cr.suite_state(bits[1])
                        return self._send(body, code)
                    if bits[0] == "sheet" and len(bits) == 3:
                        fp = cr.sheet_file(bits[1], bits[2])
                        if not fp:
                            return self._send({"error": "no sheet"}, 404)
                        return self._send_file(fp, "image/jpeg")
                    if bits[0] == "src" and len(bits) == 3:
                        fp = cr.src_file(bits[1], bits[2])
                        if not fp:
                            return self._send({"error": "no such image"}, 404)
                        return self._send_file(fp, "image/png")
                except Exception as e:
                    traceback.print_exc()
                    return self._send({"error": str(e)[:300]}, 500)
            # anything else falls through to the existing dossier API below
        if path in ("/voices", "/voices.html"):
            return self._page("voices.html")
        if path == "/api/voice" or path.startswith("/api/voice/"):
            vr = _voice_routes()
            if not vr:
                return self._send({"error": "voice_routes.py is unavailable"}, 500)
            rest = path[len("/api/voice"):].strip("/")
            bits = rest.split("/") if rest else []
            try:
                if not bits:
                    body, code = vr.listing()
                    return self._send(body, code)
                if bits[0] == "ref" and len(bits) == 2:
                    fp = vr.ref_file(bits[1])
                    if not fp:
                        return self._send({"error": "no reference"}, 404)
                    return self._send_file(fp, "audio/wav")
                if bits[0] == "demo" and len(bits) == 2:
                    fp = vr.demo_file(bits[1])
                    if not fp:
                        return self._send({"error": "no demo"}, 404)
                    return self._send_file(fp, "audio/mpeg")
                if bits[0] == "job" and len(bits) == 2:
                    body, code = vr.job_status(bits[1])
                    return self._send(body, code)
            except Exception as e:
                traceback.print_exc()
                return self._send({"error": str(e)[:300]}, 500)
            return self._send({"error": "unknown voice route"}, 404)
        if path in ("/tools", "/tools.html"):
            return self._page("tools.html")
        if path == "/api/tool" or path.startswith("/api/tool/"):
            tb = _toolbox()
            if not tb:
                return self._send({"error": "toolbox.py is unavailable"}, 500)
            rest = path[len("/api/tool"):].strip("/")
            bits = rest.split("/") if rest else []
            try:
                if not bits:
                    body, code = tb.catalogue()
                    return self._send(body, code)
                if bits[0] == "styles":
                    body, code = tb.styles()
                    return self._send(body, code)
                if bits[0] == "job" and len(bits) == 2:
                    body, code = tb.job_status(bits[1])
                    return self._send(body, code)
            except Exception as e:
                traceback.print_exc()
                return self._send({"error": str(e)[:300]}, 500)
            return self._send({"error": "unknown tool route"}, 404)
        if path == "/api/guides":
            g = _guides()
            if not g:
                return self._send({"error": "studio/_tools/guides.py is unavailable",
                                   "guides": []}, 500)
            return self._send(g.index())
        if path.startswith("/api/guide/"):
            g = _guides()
            if not g:
                return self._send({"error": "studio/_tools/guides.py is unavailable"}, 500)
            got = g.payload(urllib.parse.unquote(path[len("/api/guide/"):]))
            if not got:
                return self._send({"error": "no such guide"}, 404)
            return self._send(got)
        if path.startswith("/samples/"):
            # Percent-decode BEFORE normpath, so a filename with a space or a parenthesis
            # resolves. The abspath guard below then runs on the decoded path, which is
            # the only order in which an encoded traversal can be caught.
            rel = os.path.normpath(urllib.parse.unquote(path)[1:]).replace("\\", "/")
            fp = os.path.join(HERE, rel)
            if not os.path.abspath(fp).startswith(HERE) or not os.path.isfile(fp):
                return self._send({"error": "no sample"}, 404)
            ct = MIME.get(os.path.splitext(fp)[1].lower(), "application/octet-stream")
            return self._send_file(fp, ct)
        if path in ("/video", "/video.html"):
            return self._page("video.html")
        if path == "/api/video":
            # Built by studio/_tools/video_index.py, which reads every sample directory and
            # every metric file and resolves each clip's recipe out of the tool that
            # rendered it. Read from disk per request like every other route here, so
            # re-running the tool shows up on a refresh.
            p = f"{HERE}/samples/video.json"
            if not os.path.exists(p):
                return self._send(
                    {"error": "studio/samples/video.json has not been built",
                     "fix": "python3 studio/_tools/video_index.py all",
                     "groups": [], "clips": 0}, 404)
            try:
                with open(p, encoding="utf-8") as f:
                    return self._send(json.load(f))
            except Exception as e:                                  # noqa: BLE001
                return self._send({"error": "video.json is unreadable: %r" % (e,),
                                   "groups": [], "clips": 0}, 500)
        if path in ("/wizard", "/wizard.html"):
            return self._page("wizard.html")
        if path == "/api/effects":
            p = f"{HERE}/effects.json"
            if not os.path.exists(p):
                return self._send({"tiers": {}, "vars": {}})
            return self._send(json.load(open(p, encoding="utf-8")))
        if path in ("/gallery", "/gallery.html"):
            # Phase 5: the library is the one browsing surface; the manifest
            # page under-reported by half and is retired.
            self.send_response(302)
            self.send_header("Location", "/library")
            self.end_headers()
            return
        if path in ("/make", "/make.html"):
            return self._page("make.html")
        if path in ("/cast", "/cast.html"):
            return self._page("cast.html")
        if path == "/api/cast":
            return self._send(cast())
        # ---- the character dossier ------------------------------------------------
        # /character            the cast, each with a state per dossier section
        # /character/<ID>       one character's dossier
        # /api/character[/<ID>] the payload behind either
        # /character/<ID>/clip/<clip>.mp4   one motion clip, streamed with Range
        #
        # The page is a single file for every character, so the id lives in the path and
        # the page reads it back out of location.pathname - no template rendering, and a
        # dossier URL is shareable and bookmarkable.
        if path == "/character" or path.startswith("/character/"):
            m = re.match(r"^/character/([A-Za-z0-9_-]{1,64})/clip/"
                         r"([A-Za-z0-9_-]{1,64})\.mp4$", path)
            if m:
                return self._clip(m.group(1), m.group(2))
            return self._page("character.html")
        if path == "/api/character" or path.startswith("/api/character/"):
            cid = path[len("/api/character/"):] if len(path) > len("/api/character") else ""
            return self._dossier(cid)
        if path in ("/verify", "/verify.html"):
            return self._page("verify.html")
        if path == "/api/verify/queue":
            return self._send(verify_queue())
        if path in ("/tags", "/tags.html"):
            return self._page("tags.html")
        if path == "/api/tags":
            d = f"{HERE}/tags"
            if not os.path.isdir(d):
                return self._send([])
            out = []
            for fn in sorted(os.listdir(d)):
                if fn.endswith(".json"):
                    try:
                        out.append(json.load(open(f"{d}/{fn}", encoding="utf-8")))
                    except Exception:
                        pass
            return self._send(out)
        if path in ("/styles", "/styles.html"):
            return self._page("styles.html")
        if path == "/api/styles":
            return self._send(styles())
        if path in ("/places", "/places.html"):
            return self._page("places.html")
        if path == "/api/places":
            return self._send(places())
        if path in ("/docs", "/docs.html"):
            p = f"{HERE}/docs.html"
            if not os.path.exists(p):
                return self._send(b"docs.html is missing", 500, "text/plain")
            html = apply_studio_nav(open(p, encoding="utf-8").read(),
                                    page="docs.html", path="/docs")
            return self._send(html.encode("utf-8"), 200,
                              "text/html; charset=utf-8")
        if path == "/api/docs":
            # Built by studio/_tools/docs.py by walking the repository. A stale index is
            # better than a 500, so a missing one reports itself rather than crashing.
            p = f"{HERE}/docs.json"
            if not os.path.exists(p):
                return self._send({"error": "docs.json not built",
                                   "hint": "python3 studio/_tools/docs.py"}, 503)
            with open(p, encoding="utf-8") as f:
                return self._send(json.load(f))
        if path.startswith("/api/doc/"):
            # Serve one markdown file by slug. The slug is resolved against the INDEX
            # rather than against the filesystem, so a path cannot be traversed in - only
            # documents docs.py chose to index are reachable.
            want = urllib.parse.unquote(path[len("/api/doc/"):])
            idx = f"{HERE}/docs.json"
            if not os.path.exists(idx):
                return self._send({"error": "docs.json not built"}, 503)
            with open(idx, encoding="utf-8") as f:
                doc = json.load(f)
            hit = None
            for sec in doc.get("sections", []):
                for d in sec.get("docs", []):
                    if d.get("slug") == want:
                        hit = d
                        break
                if hit:
                    break
            if not hit:
                return self._send({"error": "no such document", "slug": want}, 404)
            full = os.path.normpath(os.path.join(ROOT, hit["rel"]))
            if not full.startswith(os.path.normpath(ROOT)) or not os.path.exists(full):
                return self._send({"error": "document missing on disk",
                                   "rel": hit["rel"]}, 410)
            with open(full, encoding="utf-8", errors="replace") as f:
                return self._send({"slug": want, "rel": hit["rel"], "text": f.read()})
        if path in ("/changelog", "/changelog.html"):
            # Served through _page like every other page. It used to be read
            # straight off disk, which is why it was the one page in the app with
            # no injected nav links - no /video, no /character, no /capabilities.
            return self._page("changelog.html")
        if path == "/api/changelog":
            # Built by studio/_tools/changelog.py from git log. Regenerate after committing;
            # a stale file is better than a 500, so a missing one is reported as such.
            p = f"{HERE}/changelog.json"
            if not os.path.exists(p):
                return self._send({"error": "changelog.json not built",
                                   "hint": "python3 studio/_tools/changelog.py"}, 503)
            with open(p, encoding="utf-8") as f:
                return self._send(json.load(f))
        # ---- the 3D pipeline ------------------------------------------------------
        # /model3d             the character that got furthest
        # /model3d/<ID>        one character, so the link is shareable
        # /api/model3d[/<ID>]  the payload behind either
        #
        # The meshes, turntables, orbit strips and STL/3MF files are already reachable:
        # they live under studio/samples/<slug>_3d/ and the /samples/ route above serves
        # them through _send_file, which honours Range - so a 133 MB STL streams in
        # 256 KB chunks instead of being read into memory. No new file route is needed
        # and none is added.
        if path in ("/library", "/library.html"):
            return self._page("library.html")
        if path in ("/encyclopedia", "/encyclopedia.html"):
            return self._page("encyclopedia.html")
        if path in ("/shorts", "/shorts.html"):
            return self._page("shorts.html")
        if path == "/api/shorts":
            fp = os.path.join(HERE, "samples", "shorts_v5.json")
            if not os.path.exists(fp):
                return self._send(
                    {"error": "run studio/_tools/shorts_page.py"}, 500)
            with open(fp, encoding="utf-8") as f:
                return self._send(json.load(f))
        if path in ("/identity", "/identity.html"):
            return self._page("identity.html")
        if path == "/api/identity":
            ip = _load_tool_module("identity_proof")
            return self._send({"samples": ip.load()})
        if path == "/api/workflows":
            try:
                wi = _load_tool_module("workflow_index")
                if hasattr(wi, "main_quiet"):
                    wi.main_quiet()
            except Exception as e:
                return self._send({"error": "workflow_index: %s" % e}, 500)
            fp = os.path.join(HERE, "samples", "_workflows.json")
            if not os.path.exists(fp):
                return self._send({"error": "run studio/_tools/workflow_index.py"}, 500)
            with open(fp, encoding="utf-8") as f:
                return self._send(json.load(f))
        if path.startswith("/api/wf/file"):
            q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            name = re.sub(r"[^A-Za-z0-9_.-]", "", q.get("name", [""])[0])
            fp = os.path.join(ROOT, "workflows", name)
            if not name or not os.path.exists(fp):
                return self._send({"error": "no such workflow"}, 404)
            with open(fp, "rb") as f:
                return self._send(f.read(), 200, "application/json")
        if path == "/api/atlas":
            # Rebuilt per request like the encyclopedia, and for the same reason: a
            # reference that lags what it describes is the failure it exists to fix.
            try:
                at = _load_tool_module("model_atlas")
                if hasattr(at, "main_quiet"):
                    at.main_quiet()
            except Exception as e:
                return self._send({"error": "model_atlas: %s" % e}, 500)
            fp = os.path.join(HERE, "samples", "_atlas.json")
            if not os.path.exists(fp):
                return self._send({"error": "run studio/_tools/model_atlas.py"}, 500)
            with open(fp, encoding="utf-8") as f:
                return self._send(json.load(f))
        if path == "/api/encyclopedia":
            # Rebuilt per request. It is a join over three files already on disk, it
            # costs milliseconds, and a reference that lags what it describes is the
            # exact failure this page was written about.
            try:
                ency = _load_tool_module("encyclopedia")
                ency.main_quiet() if hasattr(ency, "main_quiet") else None
            except Exception as e:
                return self._send({"error": "encyclopedia tool: %s" % e}, 500)
            fp = os.path.join(HERE, "samples", "_encyclopedia.json")
            if not os.path.exists(fp):
                return self._send({"error": "run studio/_tools/encyclopedia.py"}, 500)
            with open(fp, encoding="utf-8") as f:
                return self._send(json.load(f))
        if path == "/api/library":
            return self._library("index", "")
        if path.startswith("/api/library/"):
            # Parsed here rather than relying on an outer `qs`: this handler reads only
            # `path`, and the query string is not in scope at this point in do_GET.
            _q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            _id = _q.get("id", [""])[0]
            if path == "/api/library/recipe":
                return self._library("recipe", _id)
            if path == "/api/library/workflow":
                return self._library("workflow", _id, download=bool(_q.get("download")))
            if path == "/api/library/set":
                m = _load_tool_module("library_index")
                if m is None:
                    return self._send({"error": "library_index.py is unavailable"}, 500)
                got = m.packset(_q.get("facet", [""])[0], _q.get("value", [""])[0])
                if got is None:
                    return self._send({"error": "no set defined for that facet"}, 404)
                return self._send(got)
            if path == "/api/library/browse":
                return self._library("browse", _q.get("kind", [""])[0])
            if path == "/api/library/reasons":
                m = _load_tool_module("library_index")
                if m is None:
                    return self._send({"error": "library_index.py is unavailable"}, 500)
                return self._send({"reasons": [{"slug": s, "label": l, "why": w}
                                               for s, l, w in m.REASONS]})
            if path == "/api/library/rejects":
                m = _load_tool_module("library_index")
                if m is None:
                    return self._send({"error": "library_index.py is unavailable"}, 500)
                return self._send(m.reject_report())
            if path == "/api/library/favourites":
                return self._library("favourites", "")
        # /three  the 3D SECTION: bobblehead bodies and heads, their ledger, the
        # recipe with its provenance, and the docs read off disk. /make3d queues one mesh
        # and /model3d is a frozen report on one character; neither is a LIBRARY, which
        # is what this route adds. studio/_tools/three_routes.py carries the why.
        if path in ("/three", "/three.html") or (
                path.startswith("/three/") and not path.startswith("/three/media/")):
            return self._page("three.html")
        if path.startswith("/three/media/"):
            # kind/id/sub - one bobblehead item's renders, meshes and print files, served
            # off studio/bobblehead with Range so a 33 MB STL streams rather than being
            # read into memory. The realpath check keeps it inside that folder, the same
            # contract /film/media works under.
            rel = urllib.parse.unquote(path[len("/three/media/"):])
            bits = rel.split("/", 2)
            if len(bits) < 3 or bits[0] not in ("body", "head", "assembled", "figure"):
                return self._send({"error": "no such file"}, 404)
            kind, rid, sub = bits
            folder = {"body": "bodies", "head": "heads",
                      "assembled": "assembled", "figure": "figures"}[kind]
            base = os.path.realpath(os.path.join(HERE, "bobblehead", folder, rid))
            fp = os.path.realpath(os.path.join(base, sub))
            if not (fp.startswith(base + os.sep) and os.path.isfile(fp)):
                return self._send({"error": "no such file"}, 404)
            ext = os.path.splitext(fp)[1].lower()
            return self._send_file(fp, MIME.get(ext, "application/octet-stream"))
        if path == "/api/three":
            return self._three_payload()
        if path.startswith("/api/three/item/"):
            rest = path[len("/api/three/item/"):].split("/")
            if len(rest) != 2:
                return self._send({"error": "want /api/three/item/<kind>/<id>"}, 400)
            return self._three_call("item", rest[0], rest[1])
        if path.startswith("/api/three/job/"):
            return self._three_call("job", path[len("/api/three/job/"):])
        if path == "/api/three/jobs":
            return self._three_call("jobs")
        if path in ("/make3d", "/make3d.html"):
            return self._page("make3d.html")
        if path == "/api/make3d":
            return self._make3d_payload()
        if path.startswith("/api/make3d/job/"):
            return self._make3d_job(path[len("/api/make3d/job/"):])
        if path == "/model3d" or path.startswith("/model3d/"):
            return self._page("model3d.html")
        if path == "/api/model3d" or path.startswith("/api/model3d/"):
            cid = path[len("/api/model3d/"):] if len(path) > len("/api/model3d") else ""
            return self._model3d(cid)
        if path in ("/loras", "/loras.html"):
            return self._page("loras.html")
        if path == "/api/loras":
            return self._send(loras())
        if path in ("/capabilities", "/capabilities.html"):
            return self._page("capabilities.html")
        if path == "/api/capabilities":
            # The only route that varies its status from the payload builder: a catalogue
            # that has never been built is a 404 carrying the command that builds it, not
            # an empty 200 the page would have to guess about.
            payload, code = capabilities()
            return self._send(payload, code)
        if path == "/api/domains":
            return self._send(domains())
        if path == "/api/render/status":
            q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            return self._render_status(q.get("name", [""])[0])
        if path.startswith("/render/") and path.endswith(".mp4"):
            # The finished film lives under ComfyUI's output tree, keyed by the film's
            # TITLE slug rather than the .movie name, so resolve it through the film json.
            name = safe_name(path[len("/render/"):-4])
            fj = f"{HERE}/movies/{name}.json"
            if not os.path.exists(fj):
                return self._send({"error": "unknown render"}, 404)
            try:
                slug = json.load(open(fj, encoding="utf-8"))["title"].lower().replace(" ", "-")
            except Exception:
                return self._send({"error": "unreadable film"}, 500)
            fp = f"{COMFY_OUT}/{slug}/{slug}.mp4"
            if not os.path.isfile(fp):
                return self._send({"error": "not rendered yet"}, 404)
            return self._send(open(fp, "rb").read(), 200, "video/mp4")
        if path == "/api/gallery":
            return self._send(gallery())
        if path == "/api/templates":
            return self._send(templates())
        # NOTE: there is no second "/api/library" here. There used to be, returning
        # library() - the GROUPS enumeration of every preset folder - and it was
        # unreachable, because the handler at the top of do_GET claims that path first.
        # That is why the whole sound department was enumerated on every boot and
        # rendered nowhere: its only other caller is the startup banner, which prints a
        # count and discards the result. sfx, cues, voices and soundscapes now reach the
        # UI as library KINDS instead. Do not re-add a route here without checking
        # whether the path is already taken above.
        if path == "/api/cards":
            return self._send(cards())
        if path == "/api/variables":
            return self._send(variables())
        if path == "/api/movies":
            return self._send(movies())
        return self._send({"error": "not found"}, 404)

    # ---- the character dossier ------------------------------------------------
    def _dossier(self, cid):
        """/api/character/<id>, or the index when no id is given.

        Assembled by studio/_tools/dossier.py, imported per request for the same reason
        the library is read per request: a render that lands while the page is open should
        show up on a refresh, not on a restart. An import failure is reported as itself
        rather than as an empty dossier, because a page full of 'nothing rendered yet'
        that is really a broken import is exactly the kind of silent wrong answer this
        project keeps finding.
        """
        d = f"{HERE}/_tools"
        if d not in sys.path:
            sys.path.insert(0, d)
        try:
            import dossier
            if getattr(dossier, "__file__", "").startswith(d):
                dossier = importlib.reload(dossier)
        except Exception as e:                                      # noqa: BLE001
            return self._send({"error": "studio/_tools/dossier.py did not import",
                               "detail": "%s: %s" % (type(e).__name__, e),
                               "trace": traceback.format_exc()[-1500:]}, 500)
        cid = safe_name(cid)
        try:
            payload = dossier.index() if not cid else dossier.build(cid)
        except Exception as e:                                      # noqa: BLE001
            return self._send({"error": "dossier failed to assemble %s" % (cid or "index"),
                               "detail": "%s: %s" % (type(e).__name__, e),
                               "trace": traceback.format_exc()[-1500:]}, 500)
        if payload.get("error"):
            return self._send(payload, 404)
        return self._send(payload)

    def _library(self, what, ident, download=False):
        """/library - every generation on disk, its recipe, and the graph that made it.

        Loaded on mtime like the other _tools importers, never importlib.reload() per
        request: that is what made story progress polls answer "no such job" by wiping the
        module's state each time.

        `ident` arrives from a query string and is untrusted. library_index resolves it and
        refuses anything outside studio/samples/ before opening a file.
        """
        m = _load_tool_module("library_index")
        if m is None:
            return self._send({"error": "studio/_tools/library_index.py is unavailable"},
                              500)
        try:
            if what == "index":
                return self._send(m.payload())
            if what == "favourites":
                return self._send({"ids": sorted(m.favourites())})
            if what == "browse":
                got = m.browse(ident)
                if not got:
                    return self._send({"error": "no such card kind: %s" % ident}, 404)
                return self._send(got)
            if not ident:
                return self._send({"error": "no id"}, 400)
            got = m.recipe(ident) if what == "recipe" else m.workflow(ident)
            if not got:
                return self._send({"error": "no such item, or it has no recipe"}, 404)
            if what == "workflow" and download and got.get("graph"):
                body = json.dumps(got["graph"], indent=1).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Disposition",
                                 'attachment; filename="workflow.json"')
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                return self.wfile.write(body)
            return self._send(got)
        except Exception as e:                                      # noqa: BLE001
            traceback.print_exc()
            return self._send({"error": "the library failed to assemble",
                               "detail": "%s: %s" % (type(e).__name__, e)}, 500)

    def _three(self):
        """studio/_tools/three_routes.py on demand, like the other _tools importers.

        Cached on mtime by _load_tool_module, which matters here for the same reason it
        matters for /foundry: the module holds the build-job table, and reloading it per
        request would lose the job between the POST that starts it and the poll that asks
        how it is going."""
        return _load_tool_module("three_routes")

    def _three_payload(self):
        m = self._three()
        if m is None:
            return self._send({"error": "studio/_tools/three_routes.py is unavailable"},
                              500)
        try:
            return self._send(m.payload())
        except Exception as e:                                      # noqa: BLE001
            traceback.print_exc()
            return self._send({"error": "%s: %s" % (type(e).__name__, e)}, 500)

    def _three_call(self, fn, *args):
        m = self._three()
        if m is None:
            return self._send({"error": "three_routes.py is unavailable"}, 500)
        try:
            body, code = getattr(m, fn)(*args)
        except Exception as e:                                      # noqa: BLE001
            traceback.print_exc()
            return self._send({"error": "%s: %s" % (type(e).__name__, e)}, 500)
        return self._send(body, code)

    def _make3d(self):
        """The /make3d tool module, loaded on mtime like the other _tools importers.

        NOT importlib.reload() per request: that is what made every story progress poll
        answer "no such job" - each request rebuilt the module and wiped its JOBS table.
        A mesh job lives in that table for a minute, so this route would have been the
        same bug a second time.
        """
        return _load_tool_module("make3d_routes")

    def _make3d_payload(self):
        m = self._make3d()
        if m is None:
            return self._send({"error": "studio/_tools/make3d_routes.py is unavailable"},
                              500)
        try:
            return self._send(m.payload())
        except Exception as e:                                      # noqa: BLE001
            return self._send({"error": "the 3D maker payload failed to assemble",
                               "detail": "%s: %s" % (type(e).__name__, e),
                               "trace": traceback.format_exc()[-1500:]}, 500)

    def _make3d_job(self, job):
        m = self._make3d()
        if m is None:
            return self._send({"error": "make3d_routes.py is unavailable"}, 500)
        body, code = m.job_status(safe_name(job))
        return self._send(body, code)

    def _model3d(self, cid):
        """/api/model3d/<id>, or the character that got furthest when no id is given.

        Assembled by studio/_tools/model3d_index.py, imported per request for the same
        reason the dossier is: re-running the pipeline should show up on a refresh, not
        on a restart. An import failure is reported as itself rather than as an empty
        page, because "nothing has been generated yet" that is really a broken import is
        exactly the silent wrong answer this project keeps finding.
        """
        d = f"{HERE}/_tools"
        if d not in sys.path:
            sys.path.insert(0, d)
        try:
            import model3d_index
            if getattr(model3d_index, "__file__", "").startswith(d):
                model3d_index = importlib.reload(model3d_index)
        except Exception as e:                                      # noqa: BLE001
            return self._send({"error": "studio/_tools/model3d_index.py did not import",
                               "detail": "%s: %s" % (type(e).__name__, e),
                               "trace": traceback.format_exc()[-1500:]}, 500)
        try:
            return self._send(model3d_index.payload(safe_name(cid) or None))
        except Exception as e:                                      # noqa: BLE001
            return self._send({"error": "the 3D index failed to assemble",
                               "detail": "%s: %s" % (type(e).__name__, e),
                               "trace": traceback.format_exc()[-1500:]}, 500)

    def _clip(self, cid, clip_id):
        """One motion clip. The mp4s live in ComfyUI's output tree, which the static
        handler will not open and should not be widened to - so the path is resolved
        THROUGH THE MANIFEST for this character and never built from the id. An id that
        the manifest does not vouch for is a 404, not a file read."""
        d = f"{HERE}/_tools"
        if d not in sys.path:
            sys.path.insert(0, d)
        try:
            import dossier
        except Exception:                                           # noqa: BLE001
            return self._send({"error": "dossier.py did not import"}, 500)
        fp = dossier.clip_path(safe_name(cid), safe_name(clip_id))
        if not fp:
            return self._send({"error": "no such clip"}, 404)
        return self._send_file(fp, "video/mp4")

    def _render_start(self, data):
        """Compile a .movie and launch the render, so a beginner never has to open a
        terminal to see their own scene.

        compile runs SYNCHRONOUSLY - it takes about a tenth of a second and its errors
        are the ones an author can actually act on (unknown character, unknown cue, a
        movie-level variable set on a scene). Those come straight back to the page.
        The render itself is minutes long, so it is detached and polled.
        """
        name = safe_name(data.get("name", ""))
        if not name:
            return self._send({"error": "name required"}, 400)
        movie = f"{HERE}/movies/{name}.movie"
        if not os.path.exists(movie):
            return self._send({"error": f"no such scene: {name}.movie"}, 404)

        r = subprocess.run([sys.executable, f"{HERE}/compile.py", movie],
                           capture_output=True, text=True, cwd=ROOT, timeout=120)
        out = (r.stdout or "") + (r.stderr or "")
        if r.returncode != 0:
            return self._send({"error": "compile failed", "detail": out.strip()[-1200:]}, 400)

        film = f"{HERE}/movies/{name}.json"
        if not os.path.exists(film):
            return self._send({"error": "compile produced no film", "detail": out[-600:]}, 500)

        log = f"/tmp/render-{name}.log"
        # setsid so it survives this request, and its own log so status can be polled
        subprocess.Popen(
            f"setsid nohup {sys.executable} {ROOT}/scripts/short.py {film} > {log} 2>&1 < /dev/null &",
            shell=True, cwd=ROOT)
        warns = [l.strip(" !") for l in out.splitlines() if l.strip().startswith("!")]
        return self._send({"ok": True, "name": name, "log": log,
                           "compile": out.strip()[-1200:], "warnings": warns})

    def _make(self, data):
        """Run one domain generation and return the artifact.

        These are SECONDS, not minutes - 3s for a voice line, 7.6s for a music cue, 4.5s
        for a still - so unlike a film render this is answered inline rather than polled.
        Values are passed as argv, never interpolated into a shell string.
        """
        dom = safe_name(data.get("domain", ""))
        if not dom or not os.path.exists(f"{HERE}/domains/{dom}.json"):
            return self._send({"error": f"unknown domain: {dom}"}, 404)
        cmd = [sys.executable, f"{HERE}/_tools/domain_gen.py", dom]
        for k, v in (data.get("set") or {}).items():
            k = "".join(c for c in str(k) if c.isalnum() or c == "_")[:40]
            if k and v not in (None, ""):
                cmd += ["--set", f"{k}={v}"]
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT, timeout=420)
        except subprocess.TimeoutExpired:
            return self._send({"error": "generation timed out"}, 504)
        out = (r.stdout or "") + (r.stderr or "")
        # the runner appends to the manifest; the newest record for this domain is ours
        rec = None
        mp = f"{HERE}/gallery/manifest.jsonl"
        if os.path.exists(mp):
            for line in open(mp, encoding="utf-8"):
                try:
                    j = json.loads(line)
                except Exception:
                    continue
                if j.get("domain") == dom:
                    rec = j
        if rec and "1 generated" in out:
            return self._send({"ok": True, "record": rec})
        return self._send({"error": "generation failed",
                           "detail": out.strip()[-1500:]}, 500)

    def _verify(self, data):
        """Record a HUMAN verdict on a card, straight into the card's own JSON.

        Written back to studio/cards/<slug>.json rather than to a side file, so the
        verdict travels with the claim it judges and shows up in a git diff. `verified_by`
        marks it as observed rather than predicted - that distinction is the entire point,
        since every predicted verdict in this project that was later checked was wrong.
        """
        slug = safe_name(data.get("slug", ""))
        p = f"{HERE}/cards/{slug}.json"
        if not slug or not os.path.exists(p):
            return self._send({"error": f"unknown card: {slug}"}, 404)
        verdict = str(data.get("verdict", "")).strip()[:40]
        # "unsure" is a first-class answer, not a failure to answer. A reviewer who does
        # not know the term should be able to say so, and that is far more useful than a
        # guess - every predicted verdict here that was later checked was wrong.
        if verdict not in ("works", "mixed", "fails", "unsure", ""):
            return self._send({"error": "verdict must be works, mixed, fails, unsure "
                                        "or empty"}, 400)
        try:
            c = json.load(open(p, encoding="utf-8"))
        except Exception as e:
            return self._send({"error": f"unreadable card: {e}"}, 500)
        if verdict == "unsure":
            # record that a human looked and could not judge, WITHOUT claiming a verdict.
            # The card stays in the queue for someone who knows the term.
            c["seen_unsure"] = int(c.get("seen_unsure", 0)) + 1
            c.pop("verdict", None)
        elif verdict:
            c["verdict"] = verdict
            c["verified_by"] = "human"
            c["verified_at"] = __import__("time").strftime("%Y-%m-%dT%H:%M:%S")
        else:                       # clearing a verdict re-opens the card
            for k in ("verdict", "verified_by", "verified_at"):
                c.pop(k, None)
        look = str(data.get("look_at", "")).strip()[:600]
        if look:
            c["look_at"] = look
        broken = [str(x)[:60] for x in (data.get("broken_options") or [])][:40]
        if broken:
            c["broken_options"] = broken
        elif "broken_options" in c and data.get("broken_options") is not None:
            c.pop("broken_options")
        with open(p, "w", encoding="utf-8") as f:
            json.dump(c, f, indent=2, ensure_ascii=False)
            f.write("\n")
        return self._send({"ok": True, "slug": slug, "verdict": c.get("verdict")})

    def _reroll(self, data):
        """Re-render a tag's with/without pair on a different seed.

        An example only earns its place if it DEMONSTRATES the tag. Sometimes the base
        image happens to hide the effect - the jacket is already flat, the background
        already blurred - and no amount of rewording fixes that. The fix is a different
        roll of the same comparison, not a different definition.

        Takes about 6s (two 3s renders), so it is answered inline.
        """
        tag = safe_name(data.get("tag", ""))
        if not tag or not os.path.exists(f"{HERE}/tags/{tag}.json"):
            return self._send({"error": f"unknown tag: {tag}"}, 404)
        try:
            seed = int(data.get("seed") or 0)
        except (TypeError, ValueError):
            seed = 0
        if not seed:
            # deterministic per-attempt, so a reroll is reproducible rather than random
            prev = json.load(open(f"{HERE}/tags/{tag}.json", encoding="utf-8")) \
                       .get("example_seed", 4242)
            seed = int(prev) + 1111
        # "slop" and "doesn't show the tag" are different failures. The first says the
        # comparison worked but the picture is not worth showing; recording it means a tag
        # that keeps producing weak images can be found later and given a better base,
        # rather than being rerolled forever.
        reason = str(data.get("reason", ""))[:20]
        if reason == "slop":
            try:
                tp = f"{HERE}/tags/{tag}.json"
                t = json.load(open(tp, encoding="utf-8"))
                t["slop_rerolls"] = int(t.get("slop_rerolls", 0)) + 1
                with open(tp, "w", encoding="utf-8") as f:
                    json.dump(t, f, indent=2, ensure_ascii=False)
                    f.write("\n")
            except Exception:
                pass
        cmd = [sys.executable, f"{HERE}/_tools/tag_examples.py", tag, "--seed", str(seed)]
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT, timeout=300)
        except subprocess.TimeoutExpired:
            return self._send({"error": "reroll timed out"}, 504)
        out = (r.stdout or "") + (r.stderr or "")
        if "1 rendered" not in out:
            return self._send({"error": "reroll failed", "detail": out.strip()[-1200:]}, 500)
        return self._send({"ok": True, "tag": tag, "seed": seed,
                           "example": f"/samples/tags/{tag}.webp"})

    def _workflow(self, data):
        """The exact ComfyUI graph this would submit, without submitting it.

        Built by the same code path as a real run, so it cannot drift from what actually
        executes. Useful for three things: seeing which node a setting lands on, checking
        a prompt before spending GPU, and loading the graph into ComfyUI itself to tweak
        by hand (its Load-API-format menu takes this JSON directly).
        """
        dom = safe_name(data.get("domain", ""))
        if not dom or not os.path.exists(f"{HERE}/domains/{dom}.json"):
            return self._send({"error": f"unknown domain: {dom}"}, 404)
        cmd = [sys.executable, f"{HERE}/_tools/domain_gen.py", dom, "--show"]
        for k, v in (data.get("set") or {}).items():
            k = "".join(c for c in str(k) if c.isalnum() or c == "_")[:40]
            if k and v not in (None, ""):
                cmd += ["--set", f"{k}={v}"]
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT, timeout=90)
        except subprocess.TimeoutExpired:
            return self._send({"error": "timed out building the workflow"}, 504)
        try:
            # the runner prints warnings before the JSON, so take from the first brace
            txt = r.stdout[r.stdout.index("{"):]
            return self._send(json.loads(txt))
        except Exception:
            return self._send({"error": "could not build the workflow",
                               "detail": ((r.stdout or "") + (r.stderr or ""))[-1200:]}, 500)

    def _render_status(self, name):
        name = safe_name(name)
        log = f"/tmp/render-{name}.log"
        if not os.path.exists(log):
            return self._send({"state": "none"})
        txt = open(log, encoding="utf-8", errors="replace").read()
        stage, done, total = "starting", 0, 0
        for line in txt.splitlines():
            s = line.strip()
            if s.startswith("=== "):
                stage = s.strip("= ").split(":")[0].lower()
            m = re.search(r"\((\d+)/(\d+)\)", s)
            if m:
                done, total = int(m.group(1)), int(m.group(2))
            m = re.search(r"clips (\d+)/(\d+)", s)
            if m:
                done, total = int(m.group(1)), int(m.group(2))
        final = None
        for line in txt.splitlines():
            if line.strip().startswith(">>>"):
                final = line.strip()[3:].strip()
        state = "done" if final else ("failed" if "Traceback" in txt else "running")
        return self._send({
            "state": state, "stage": stage, "done": done, "total": total,
            "final": final,
            # the video is under ComfyUI's output, not ours, so expose a play URL
            "play": f"/render/{name}.mp4" if final else None,
            "tail": "\n".join(txt.splitlines()[-24:]),
        })

    def _compose(self, data):
        """Resolve a set of picked cards into one prompt, its negative, and the arguments
        between the layers. RESOLUTION ONLY - this never renders and never touches the GPU.

        The logic lives in studio/compose.py because the compiler uses the same code path.
        A second implementation here would drift from what actually gets rendered, which is
        the exact failure this endpoint exists to prevent - so if that module will not
        import, say so plainly rather than guessing an answer that looks authoritative.

        Reloaded per request for the same reason the library is read from disk per request:
        editing the resolver and refreshing should show the change.
        """
        if HERE not in sys.path:
            sys.path.insert(0, HERE)
        try:
            import compose as composer
            if getattr(composer, "__file__", "").startswith(HERE):
                composer = importlib.reload(composer)
        except Exception as e:
            return self._send({
                "error": "the compositor is not wired up yet",
                "detail": f"{type(e).__name__}: {e}",
                "hint": "studio/compose.py must exist and define resolve()"}, 503)
        fn = getattr(composer, "resolve", None)
        if not callable(fn):
            return self._send({
                "error": "the compositor is not wired up yet",
                "detail": "studio/compose.py imported but has no resolve()",
                "hint": "studio/compose.py must define resolve()"}, 503)
        req = {}
        for k in ("style", "place", "character", "look", "wear",
                  "lighting", "weather", "engine",
                  # The style-LoRA layer. resolve() has accepted these two since
                  # compose.py grew resolve_style_lora(), and compile.py already
                  # passes them, but they were missing here - so a style LoRA the
                  # wizard posted was dropped before the resolver saw it and every
                  # base-model mismatch came back as "this style is words only",
                  # with no conflict at all. That is the one check this layer
                  # exists to perform.
                  "style_lora", "style_lora_strength"):
            v = data.get(k)
            req[k] = (v.strip() or None) if isinstance(v, str) else v
        try:
            out = _call_resolve(fn, req)
        except Exception as e:
            return self._send({
                "error": "the compositor could not resolve that combination",
                "detail": f"{type(e).__name__}: {e}",
                "trace": "".join(traceback.format_exc()).splitlines()[-6:]}, 500)
        if not isinstance(out, dict):
            return self._send({
                "error": "the compositor returned something unexpected",
                "detail": f"resolve() returned {type(out).__name__}, expected a dict"}, 500)
        # resolve() hands back the full text of every card it touched so the COMPILER can
        # use them in-process. Over HTTP that is dead weight: measured at 6604 bytes of a
        # 12781-byte reply, 52% of the payload, on a request the wizard fires every 180ms
        # while you type. Nothing in either page reads it, and the same data is already on
        # /api/library. compose.py's own docstring asks serve.py to drop it.
        out = {k: v for k, v in out.items() if k != "cards"}
        return self._send(out)

    def do_POST(self):
        p = urllib.parse.urlparse(self.path).path
        if p not in ("/api/save", "/api/render", "/api/make", "/api/workflow",
                     "/api/verify", "/api/tag/reroll", "/api/compose",
                     "/api/generate/start", "/api/generate/stop",
                     "/api/generate/preview", "/api/generate/bundle",
                     "/api/story/take", "/api/story/clip", "/api/story/select",
                     "/api/story/edit", "/api/story/lock", "/api/story/new",
                     "/api/story/chapter", "/api/story/scene", "/api/story/load",
                     "/api/story/transition",
                     "/api/film/new", "/api/film/edit", "/api/film/scene",
                     "/api/film/editscene", "/api/film/shot", "/api/film/editshot",
                     "/api/film/reorder", "/api/film/delete", "/api/film/pick",
                     "/api/film/takes", "/api/film/anchor", "/api/film/autonext",
                     "/api/film/vo", "/api/film/assemble",
                     "/api/film/portrait", "/api/film/master", "/api/film/draftall",
                     "/api/film/compose", "/api/film/pin",
                     "/api/spec/save", "/api/spec/new", "/api/spec/lock",
                     "/api/foundry/new", "/api/foundry/edit", "/api/foundry/delete",
                     "/api/foundry/seeds", "/api/foundry/apply",
                     "/api/foundry/send", "/api/foundry/variant",
                     "/api/foundry/describe", "/api/foundry/from_image",
                     "/api/foundry/import_legacy", "/api/foundry/rename",
                     "/api/motion/verdict",
                     "/api/character/upload", "/api/character/create",
                     "/api/voice/demo", "/api/voice/add",
                     "/api/character/suite", "/api/character/analyse",
                     "/api/tool/run", "/api/tool/random",
                     "/api/three/figure", "/api/three/pose",
                     "/api/three/build", "/api/three/head",
                     "/api/make3d/mesh", "/api/library/star",
                     "/api/library/grow", "/api/library/reject",
                     "/api/library/check", "/api/verify/card", "/api/remake",
                     "/api/wf/send", "/api/wf/queue",
                     "/api/identity/verdict"):
            return self._send({"error": "not found"}, 404)
        n = int(self.headers.get("Content-Length", 0))
        try:
            data = json.loads(self.rfile.read(n) or b"{}")
        except Exception as e:
            return self._send({"error": f"bad json: {e}"}, 400)
        if p in ("/api/wf/send", "/api/wf/queue"):
            name = re.sub(r"[^A-Za-z0-9_.-]", "", str(data.get("name") or ""))
            fp = os.path.join(ROOT, "workflows", name)
            if not name or not os.path.exists(fp):
                return self._send({"error": "no such workflow"}, 404)
            if p == "/api/wf/send":
                # A copy where ComfyUI can see it. These are API graphs, so its EDITOR
                # may not open them - the page says exactly that rather than promising
                # more than the format supports.
                dst_dir = os.path.join(os.path.expanduser(
                    os.environ.get("COMFY_ROOT", "~/ComfyUI")),
                    "user", "default", "workflows", "studio")
                os.makedirs(dst_dir, exist_ok=True)
                shutil.copy(fp, os.path.join(dst_dir, name))
                return self._send({"ok": True,
                                   "path": "user/default/workflows/studio/" + name})
            # Underscore keys are METADATA, and ComfyUI's validate_prompt walks every
            # top-level key expecting a node - a `_notes` list produces
            # "AttributeError: 'list' object has no attribute 'get'" and a bare 500.
            # engine.load_wf is the one rule for this; a second copy here would drift.
            sys.path.insert(0, HERE)
            from engine import load_wf as _load_wf
            graph = _load_wf(name)
            try:
                req = urllib.request.Request(
                    COMFY + "/prompt",
                    data=json.dumps({"prompt": graph}).encode(),
                    headers={"Content-Type": "application/json"})
                with urllib.request.urlopen(req, timeout=25) as r:
                    out = json.loads(r.read() or b"{}")
                return self._send({"ok": True, "prompt_id": out.get("prompt_id"),
                                   "comfy": COMFY})
            except Exception as e:
                # A validation failure is real information about the graph, so it travels
                # back to the page instead of becoming a generic 500.
                body = b""
                try:
                    body = e.read()
                except Exception:
                    pass
                return self._send({"error": str(e),
                                   "detail": (body or b"").decode()[:600]}, 502)
        if p == "/api/identity/verdict":
            # Through identity_proof's own load/save so the page and `--mark` write the
            # same file. A verdict is a HUMAN judgement - nothing here computes one,
            # because no instrument on this box can tell whether a face is the right
            # person, and a guessed verdict would be worse than an empty column.
            ip = _load_tool_module("identity_proof")
            cid = str(data.get("id") or "")
            v = data.get("verdict")
            if v not in (None, "ok", "close", "x"):
                return self._send(
                    {"error": "verdict must be ok, close, x or null"}, 400)
            rows = ip.load()
            hit = [r for r in rows if r.get("id") == cid]
            if not hit:
                return self._send({"error": "no such sample: %s" % cid}, 404)
            hit[0]["verdict"] = v
            ip.save(rows)
            return self._send({"ok": True, "id": cid, "verdict": v})
        if p == "/api/remake":
            # Straight through remake.py so the app and the CLI share one store: a flag
            # raised while listening here is listed and cleared by the same tool there.
            rm = _load_tool_module("remake")
            kind = "cues" if str(data.get("kind")) in ("cues", "music") else "sfx"
            cid = re.sub(r"[^A-Za-z0-9_.-]", "", str(data.get("id") or ""))
            on = bool(data.get("on"))
            if not cid:
                return self._send({"error": "need a card id"}, 400)
            rc = rm.flag(kind, cid, str(data.get("reason") or "")[:200], on)
            if rc:
                return self._send({"error": "no such card: %s/%s" % (kind, cid)}, 404)
            return self._send({"ok": True, "id": cid, "kind": kind, "flagged": on})
        if p == "/api/verify/card":
            # A human judgement on a KIND card - same eye as the panel queue, one writer.
            sys.path.insert(0, HERE)
            import cards as _cards
            kind = re.sub(r"[^a-z]", "", str(data.get("kind") or ""))
            cid = re.sub(r"[^A-Za-z0-9_.-]", "", str(data.get("id") or ""))
            verdict = str(data.get("verdict") or "").strip()
            if kind not in _cards.KINDS or not cid:
                return self._send({"error": "need a kind and a card id"}, 400)
            if verdict not in ("works", "mixed", "fails"):
                return self._send({"error": "verdict must be works, mixed or fails"}, 400)
            try:
                e = _cards.stamp(kind, cid, "JUDGED", "human, via /verify",
                                 note="%s. %s" % (verdict,
                                                  str(data.get("note") or "")[:200]))
            except FileNotFoundError:
                return self._send({"error": "no such card: %s/%s" % (kind, cid)}, 404)
            return self._send({"ok": True, "evidence": e})

        if p == "/api/library/grow":
            # Spawned DETACHED, not run inline. A render takes ten seconds a frame and the
            # server is single-threaded for pages; holding the request open would freeze
            # the whole app while the GPU works.
            kind = re.sub(r"[^a-z]", "", str(data.get("kind") or ""))
            cid = re.sub(r"[^A-Za-z0-9_.-]", "", str(data.get("id") or ""))
            try:
                n = max(1, min(12, int(data.get("n") or 4)))
            except Exception:
                n = 4
            if kind not in ("places", "characters", "emotions", "styles") or not cid:
                return self._send({"error": "need a kind and a card id"}, 400)
            import subprocess
            # The one generator, mode grow (Phase 3). serve.py no longer knows what
            # command grows a card - it knows who to ask.
            cmd = [sys.executable, "-u", f"{HERE}/_tools/generate.py", "grow",
                   "--kind", kind, "--id", cid, "--n", str(n)]
            log = f"{HERE}/samples/isolation/_grow_{kind}_{cid}.log"
            try:
                os.makedirs(os.path.dirname(log), exist_ok=True)
                with open(log, "w", encoding="utf-8") as lf:
                    subprocess.Popen(cmd, stdout=lf, stderr=lf,
                                     cwd=os.path.dirname(HERE), start_new_session=True)
            except Exception as e:                                  # noqa: BLE001
                traceback.print_exc()
                return self._send({"error": "could not start: %s" % str(e)[:160]}, 500)
            return self._send({"ok": True, "kind": kind, "id": cid, "frames": n,
                               "note": "rendering in the background - refresh in a minute"})
        if p == "/api/library/check":
            # One frame through frame_check (Gemma-4 VLM description vs the recipe's
            # place/character nouns). Written onto the recipe; nothing is rejected -
            # the answer sits beside the reject control and the human decides.
            m = _load_tool_module("library_index")
            ident = str(data.get("id") or "")
            if m is None or not ident:
                return self._send({"error": "no id"}, 400)
            rec = m.recipe(ident)
            if not rec:
                return self._send({"error": "no such frame, or it has no recipe"}, 404)
            raw = rec.get("raw") or {}
            fc = _load_tool_module("frame_check")
            if fc is None:
                return self._send({"error": "frame_check.py is unavailable"}, 500)
            sys.path.insert(0, HERE)
            import cards as _cards
            want, kind = [], None
            if raw.get("place"):
                pc = _cards.load("places").get(str(raw["place"])) or {}
                want += fc.nouns_of(pc.get("name"), pc.get("family"),
                                    (pc.get("tags") or "").split(",")[:6],
                                    (pc.get("prose") or "")[:120])
                kind = "place"
            if raw.get("character"):
                cc = _cards.load("characters").get(str(raw["character"])) or {}
                want += fc.nouns_of((cc.get("tags") or "").split(",")[:10],
                                    (cc.get("prose") or "")[:220],
                                    "person woman man girl boy figure character",
                                    limit=18)
                kind = (kind + "+character") if kind else "character"
            png = os.path.join(HERE, ident) if not ident.startswith("/") else ident
            if not os.path.isfile(png):
                png = os.path.join(HERE, "samples", ident.split("samples/", 1)[-1])
            try:
                desc = fc.describe(png)
            except Exception as e:                                  # noqa: BLE001
                return self._send({"error": "VLM failed: %s" % str(e)[:160]}, 500)
            hits = fc.check(desc, want) if want else []
            person = fc.check(desc, ["person", "woman", "man", "girl", "boy", "figure",
                                     "character", "people", "portrait", "face"])
            out = {"description": desc, "expect": want, "hits": hits,
                   "seen": bool(hits) if want else None,
                   "person_present": bool(person), "checked": kind or "nothing to check"}
            # write it beside the frame, like the sweep does
            rp = os.path.splitext(png)[0] + ".json"
            try:
                r = json.load(open(rp, encoding="utf-8"))
                r["frame_check"] = dict(out, model="gemma4-e2b via TextGenerate")
                with open(rp, "w", encoding="utf-8") as f:
                    json.dump(r, f, indent=1, ensure_ascii=False)
            except Exception:
                traceback.print_exc()
            return self._send(out)

        if p == "/api/library/reject":
            m = _load_tool_module("library_index")
            if m is None:
                return self._send({"error": "library_index.py is unavailable"}, 500)
            ident = str(data.get("id") or "")
            if not ident:
                return self._send({"error": "no id"}, 400)
            try:
                got = m.reject(ident, str(data.get("reason") or "")[:60],
                               str(data.get("note") or "")[:300])
            except Exception as e:                                  # noqa: BLE001
                traceback.print_exc()
                return self._send({"error": str(e)[:200]}, 500)
            if not got:
                return self._send({"error": "no such frame, or it is outside samples/"}, 404)
            return self._send(got)
        if p == "/api/library/star":
            m = _load_tool_module("library_index")
            if m is None:
                return self._send({"error": "library_index.py is unavailable"}, 500)
            ident = str(data.get("id") or "")
            if not ident:
                return self._send({"error": "no id"}, 400)
            try:
                return self._send(m.star(ident, bool(data.get("on", True))))
            except Exception as e:                                  # noqa: BLE001
                traceback.print_exc()
                return self._send({"error": str(e)[:200]}, 500)
        if p in ("/api/three/build", "/api/three/head", "/api/three/figure",
                 "/api/three/pose"):
            m = self._three()
            if m is None:
                return self._send({"error": "three_routes.py is unavailable"}, 500)
            fn = {"build": m.build, "head": m.head,
                  "figure": m.figure, "pose": m.pose}[p.rsplit("/", 1)[1]]
            try:
                body, code = fn(data)
            except Exception as e:                                  # noqa: BLE001
                traceback.print_exc()
                return self._send({"error": "the build could not start",
                                   "detail": "%s: %s" % (type(e).__name__, e)}, 500)
            return self._send(body, code)
        if p == "/api/make3d/mesh":
            m = self._make3d()
            if m is None:
                return self._send({"error": "make3d_routes.py is unavailable"}, 500)
            try:
                body, code = m.mesh(data)
            except Exception as e:                                  # noqa: BLE001
                traceback.print_exc()
                return self._send({"error": "the mesh job could not start",
                                   "detail": "%s: %s" % (type(e).__name__, e)}, 500)
            return self._send(body, code)
        if p.startswith("/api/tool/"):
            tb = _toolbox()
            if not tb:
                return self._send({"error": "toolbox.py is unavailable"}, 500)
            fn = {"run": tb.run_tool, "random": tb.randomize}[p[len("/api/tool/"):]]
            try:
                body, code = fn(data)
            except Exception as e:
                traceback.print_exc()
                return self._send({"error": str(e)[:300]}, 500)
            return self._send(body, code)
        if p.startswith("/api/voice/"):
            vr = _voice_routes()
            if not vr:
                return self._send({"error": "voice_routes.py is unavailable"}, 500)
            fn = {"demo": vr.demo, "add": vr.add}[p[len("/api/voice/"):]]
            try:
                body, code = fn(data)
            except Exception as e:
                traceback.print_exc()
                return self._send({"error": str(e)[:300]}, 500)
            return self._send(body, code)
        if p.startswith("/api/character/"):
            cr = _charnew_routes()
            if not cr:
                return self._send({"error": "charnew_routes.py is unavailable"}, 500)
            fn = {"upload": cr.upload, "create": cr.create,
                  "suite": cr.suite,
                  "analyse": cr.analyse}[p[len("/api/character/"):]]
            try:
                body, code = fn(data)
            except Exception as e:
                traceback.print_exc()
                return self._send({"error": str(e)[:300]}, 500)
            return self._send(body, code)
        if p.startswith("/api/spec/"):
            sr = _spec_routes()
            if not sr:
                return self._send({"error": "studio/_tools/spec_routes.py is "
                                            "unavailable"}, 500)
            fn = {"save": sr.save, "new": sr.new, "lock": sr.lock}.get(p[len("/api/spec/"):])
            if not fn:
                return self._send({"error": "unknown spec route"}, 404)
            try:
                body, code = fn(data)
            except Exception as e:
                traceback.print_exc()
                return self._send({"error": str(e)[:300]}, 500)
            return self._send(body, code)
        if p == "/api/motion/verdict":
            fp = f"{HERE}/motion_verdicts.json"
            cur = {}
            if os.path.isfile(fp):
                try:
                    cur = json.load(open(fp, encoding="utf-8"))
                except Exception:
                    cur = {}
            vid = str(data.get("id") or "")
            verdict = str(data.get("verdict") or "")
            if not vid or verdict not in ("yes", "partly", "no"):
                return self._send({"error": "id and a yes/partly/no verdict"}, 400)
            cur[vid] = verdict
            json.dump(cur, open(fp, "w", encoding="utf-8"), indent=1)
            return self._send({"ok": True, "answered": len(cur)})
        if p.startswith("/api/foundry/"):
            fo = _foundry_routes()
            if not fo:
                return self._send({"error": "studio/_tools/foundry_routes.py is "
                                            "unavailable"}, 500)
            fn = {"new": fo.new, "edit": fo.edit, "delete": fo.delete,
                  "seeds": fo.seeds, "apply": fo.apply_costume,
                  "send": fo.send_to_film, "variant": fo.variant,
                  "describe": fo.describe,
                  "from_image": fo.from_image,
                  "import_legacy": fo.import_legacy,
                  "rename": fo.rename}[p[len("/api/foundry/"):]]
            try:
                body, code = fn(data)
            except KeyError as e:
                return self._send({"error": str(e)}, 404)
            except Exception as e:
                traceback.print_exc()
                return self._send({"error": str(e)[:300]}, 500)
            return self._send(body, code)
        if p.startswith("/api/film/"):
            fr = _film_routes()
            if not fr:
                return self._send({"error": "studio/_tools/film_routes.py is "
                                            "unavailable"}, 500)
            fn = {"new": fr.new_film, "edit": fr.edit_film, "scene": fr.new_scene,
                  "editscene": fr.edit_scene, "shot": fr.new_shot,
                  "editshot": fr.edit_shot, "reorder": fr.reorder,
                  "delete": fr.delete_shot, "pick": fr.pick, "takes": fr.takes,
                  "anchor": fr.scene_anchor, "autonext": fr.auto_next,
                  "vo": fr.vo_mix, "assemble": fr.assemble,
                  "portrait": fr.portrait, "master": fr.master,
                  "draftall": fr.draft_all,
                  "compose": fr.compose_anchor,
                  "pin": fr.pin_shot}[p[len("/api/film/"):]]
            try:
                body, code = fn(data)
            except KeyError as e:
                return self._send({"error": str(e)}, 404)
            except Exception as e:
                traceback.print_exc()
                return self._send({"error": str(e)[:300]}, 500)
            return self._send(body, code)
        if p.startswith("/api/story/"):
            sr = _story_routes()
            if not sr:
                return self._send({"error": "studio/_tools/story_routes.py is "
                                            "unavailable"}, 500)
            fn = {"take": sr.start_take, "clip": sr.start_clip, "select": sr.select,
                  "edit": sr.edit_scene, "lock": sr.lock, "new": sr.new_story,
                  "chapter": sr.new_chapter, "scene": sr.new_scene,
                  "load": sr.load_file,
                  "transition": sr.transition}[p[len("/api/story/"):]]
            try:
                body, code = fn(data)
            except KeyError as e:
                return self._send({"error": str(e)}, 404)
            except Exception as e:
                traceback.print_exc()
                return self._send({"error": str(e)[:300]}, 500)
            return self._send(body, code)
        if p.startswith("/api/generate/"):
            gr = _generate_routes()
            if not gr:
                return self._send({"error": "studio/_tools/generate_routes.py is "
                                            "unavailable"}, 500)
            fn = {"start": gr.start, "stop": gr.stop, "preview": gr.preview,
                  "bundle": gr.bundle}[p[len("/api/generate/"):]]
            try:
                body, code = fn(data)
            except subprocess.TimeoutExpired:
                return self._send({"error": "the roll timed out"}, 504)
            except Exception as e:
                return self._send({"error": str(e)[:300]}, 500)
            return self._send(body, code)
        if p == "/api/render":
            try:
                return self._render_start(data)
            except subprocess.TimeoutExpired:
                return self._send({"error": "compile timed out"}, 504)
        if p == "/api/make":
            return self._make(data)
        if p == "/api/workflow":
            return self._workflow(data)
        if p == "/api/verify":
            return self._verify(data)
        if p == "/api/tag/reroll":
            return self._reroll(data)
        if p == "/api/compose":
            return self._compose(data)
        name = "".join(c for c in str(data.get("name", "")) if c.isalnum() or c in "-_")
        if not name:
            return self._send({"error": "name required"}, 400)
        os.makedirs(f"{HERE}/movies", exist_ok=True)
        p = f"{HERE}/movies/{name}.movie"
        open(p, "w", encoding="utf-8").write(data.get("text", ""))
        return self._send({"ok": True, "path": p})

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    lib = library()
    print(f"studio  http://localhost:{PORT}"
          + (f"   (also http://{socket.gethostbyname(socket.gethostname())}:{PORT})"
             if BIND == "0.0.0.0" else ""))
    print(f"  {sum(len(v) for v in lib.values())} presets in {len(lib)} groups, "
          f"{len(variables())} variables")
    # Refuse to start if something is already listening. On Windows SO_REUSEADDR lets a
    # SECOND process bind the same port instead of erroring, and the OS then round-robins
    # between them - so a stale server keeps serving old code and edits appear to do
    # nothing at random. Check first, and leave reuse off.
    probe = socket.socket()
    probe.settimeout(0.4)
    if probe.connect_ex(("127.0.0.1", PORT)) == 0:
        probe.close()
        raise SystemExit(
            f"something is already serving on {PORT}.\n"
            f"  stop it first, or run with a different port:  STUDIO_PORT=8778 python3 studio/serve.py")
    probe.close()
    # THREADED. The card page pulls one JSON plus dozens of panel images; on a
    # single-threaded TCPServer those serialise behind each other and the page appears
    # to hang.
    #
    # SO_REUSEADDR is platform-dependent and the difference matters here. On WINDOWS it
    # genuinely lets a second process bind a live port, which is the bug the probe above
    # was written for - three servers once bound 8777 at once and the OS round-robined
    # between them, so a stale one served old code at random. On LINUX it does no such
    # thing (that needs SO_REUSEPORT); it only permits rebinding a socket sitting in
    # TIME_WAIT, which is exactly what you want when restarting a dev server. Refusing it
    # on Linux just means every restart fails for ~60s. The probe is the real guard.
    class Studio(socketserver.ThreadingTCPServer):
        daemon_threads = True
        allow_reuse_address = (os.name == "posix")

    with Studio((BIND, PORT), H) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nstopped")
