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
        ".svg": "image/svg+xml"}

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
                items.append(json.load(open(f"{d}/{fn}", encoding="utf-8")))
            except Exception as e:
                items.append({"id": fn[:-5], "desc": f"UNREADABLE: {e}", "status": "error"})
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
    return {"todo": todo, "done": done, "total": len(todo) + len(done)}


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
    p = f"{HERE}/gallery/manifest.jsonl"
    if not os.path.exists(p):
        return []
    out = []
    with open(p, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except Exception:
                continue
    out.reverse()
    return out


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
    return (out, 200)


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


class H(http.server.SimpleHTTPRequestHandler):
    def _page(self, name):
        """Serve one of the hand-written pages, with the video and dossier links injected
        into its nav, and the per-character dossier link into the cast page's card."""
        p = f"{HERE}/{name}"
        if not os.path.exists(p):
            return self._send(f"{name} is missing".encode(), 500, "text/plain")
        with open(p, encoding="utf-8") as f:
            html = f.read()
        html = nav_dossier(nav_video(html))
        # Every page gets the link except the capabilities page itself, which
        # writes its own nav and omits itself the way styles.html omits /styles.
        if name != "capabilities.html":
            html = nav_capabilities(html)
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
            rel = os.path.normpath(path[1:]).replace("\\", "/")
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
            return self._page("gallery.html")
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
        if path == "/api/library":
            return self._send(library())
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
                     "/api/verify", "/api/tag/reroll", "/api/compose"):
            return self._send({"error": "not found"}, 404)
        n = int(self.headers.get("Content-Length", 0))
        try:
            data = json.loads(self.rfile.read(n) or b"{}")
        except Exception as e:
            return self._send({"error": f"bad json: {e}"}, 400)
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
