#!/usr/bin/env python3
"""studio/_tools/three_routes.py - the payload and jobs behind /three, the 3D section.

    python3 studio/_tools/three_routes.py         a human summary of what the page shows

WHY THIS IS A SECTION AND NOT A THIRD 3D PAGE.

There were already two: /make3d queues one mesh from one uploaded image, and /model3d is a
frozen report on the one character that got furthest through the terra_3d run. Neither is a
LIBRARY - neither answers "what 3D objects exist here, which of them can actually be
printed, and what is the recipe". Adding a third single-purpose page would have made that
worse.

So /three owns the three things a section owns and the other two pages do not:

  A LIBRARY with a ledger. Bobblehead bodies and heads, each with its orbit render, its
  measured topology, its neck or seating diameter, its socket size and its files. The
  ledger counts printable against not, the same honesty bar every other library in this
  project carries, because a mesh that is watertight and a mesh that is printable are
  different claims and this project has shipped the first as the second before.

  DOCS that are read off disk, not re-authored here. craft/PRINTING.md is the print spec,
  craft/BOBBLEHEAD.md is how the two-part assembly works, docs/3D-QUALITY.md is the
  honest comparison against Meshy and Tripo and what would actually close the gap. If a
  file is missing the page says so rather than rendering an empty tab.

  THE RECIPE, stated with its provenance. Every dial on this page traces to a measurement
  in studio/samples/terra_3d/mesh/VERDICT.md or to a comparison run for this section, and
  the page says which.

WHAT THIS MODULE DOES NOT DO. It does not mesh anything. Building is bobble.py's job and
it takes minutes per item; the page starts a job and polls, exactly the way /make3d and
/foundry already do, and the job table lives here because a module reloaded per request
would lose it (the comment in serve.py's _load_tool_module has the full story).
"""
import glob
import json
import os
import subprocess
import sys
import threading
import time

TOOLS = os.path.dirname(os.path.abspath(__file__))
STUDIO = os.path.dirname(TOOLS)
ROOT = os.path.dirname(STUDIO)
LIB = os.path.join(STUDIO, "bobblehead")

sys.path.insert(0, TOOLS)

JOBS = {}
_LOCK = threading.Lock()
_SEQ = [0]

# The docs the section owns, in the order the page shows them. Read off disk every
# request: editing the markdown and refreshing shows the change, which is the contract
# the rest of this server works under.
DOC_TABS = [
    ("bobblehead", "Bobblehead", "craft/BOBBLEHEAD.md",
     "How the two parts and the spring go together, and every dimension involved."),
    ("quality", "Rivalling Meshy", "docs/3D-QUALITY.md",
     "Where open image-to-3D actually stands against the paid tools, and the ordered "
     "list of things that would close the gap on this box."),
    ("printing", "Printing", "craft/PRINTING.md",
     "The print spec and the thresholds mesh_doctor checks against."),
    ("mesh", "The mesh recipe", "studio/samples/terra_3d/mesh/VERDICT.md",
     "The run that measured every dial this section uses."),
]


def _bobble():
    import importlib
    import bobble
    if getattr(bobble, "__file__", "").startswith(TOOLS):
        bobble = importlib.reload(bobble)
    return bobble


def _rel(p):
    return os.path.relpath(p, LIB).replace(os.sep, "/")


def _files_for(kind, rid, d):
    """Everything downloadable, as /three/media URLs. Only files that exist are listed -
    a dead link on a library page is worse than a missing one."""
    out = {}
    mesh = "body.glb" if kind == "body" else "head.glb"
    cand = {"glb": mesh, "raw": "raw.glb", "offcut": "head_offcut.glb",
            "source": "source.png", "styled": "source_styled.png",
            "square": "source_square.png"}
    for key, name in cand.items():
        p = os.path.join(d, name)
        if os.path.isfile(p):
            out[key] = "/three/media/%s/%s/%s" % (kind, rid, name)
    for p in sorted(glob.glob(os.path.join(d, "print", "*"))):
        ext = os.path.splitext(p)[1].lstrip(".").lower()
        if ext in ("stl", "3mf", "obj"):
            out[ext] = "/three/media/%s/%s/print/%s" % (kind, rid, os.path.basename(p))
            out[ext + "_bytes"] = os.path.getsize(p)
    for p in sorted(glob.glob(os.path.join(d, "views", "*.jpg"))):
        b = os.path.basename(p)
        key = "orbit" if "orbit" in b else ("closeup" if "head" in b else None)
        if key:
            out[key] = "/three/media/%s/%s/views/%s" % (kind, rid, b)
    return out


def _card(kind, rec, d):
    """One library row. Flat, because the page should not have to walk a nested record
    to draw a card - and because what is flattened here is exactly what the ledger and
    the sort are allowed to depend on."""
    dg = rec.get("diagnose") or {}
    st = rec.get("stages") or {}
    j = st.get("neck") or st.get("socket") or {}
    ext = j.get("body_extents_mm") or j.get("head_extents_mm") or dg.get("extents") or []
    spec = rec.get("spec") or {}
    return {
        "id": rec.get("id"), "kind": kind,
        "name": spec.get("name") or rec.get("id"),
        "group": spec.get("group", ""), "sex": spec.get("sex", ""),
        "subject": spec.get("subject", ""), "costume": spec.get("costume", ""),
        "pose": spec.get("pose", ""),
        "ok": bool(rec.get("ok")), "error": rec.get("error", ""),
        # A record with phases but no error has not failed - it is part-way through.
        # Counting it as a failure is the same class of mistake as counting an untested
        # card as ready, so the two states stay apart all the way to the ledger.
        "phases": rec.get("phases") or {},
        "state": ("done" if rec.get("ok") else
                  "failed" if rec.get("error") else "building"),
        "printable": dg.get("printable"),
        "watertight": dg.get("is_watertight"),
        "faces": dg.get("faces"), "components": dg.get("components"),
        "nonmanifold": dg.get("nonmanifold_edges"),
        "blocking": dg.get("blocking") or [], "warnings": dg.get("warnings") or [],
        "mm": [round(float(x), 1) for x in ext[:3]],
        "height_mm": rec.get("height_mm"),
        "joint_mm": j.get("neck_diameter_mm") or j.get("flat_equiv_diameter_mm"),
        "joint_kind": "neck" if "neck_diameter_mm" in j else "seat",
        "socket_mm": j.get("socket_d_mm"), "socket_depth_mm": j.get("socket_depth_mm"),
        "socket_reduced": bool(j.get("socket_reduced")),
        "cut_f": j.get("neck_f") or j.get("flat_f"),
        "debris_dropped": j.get("debris_dropped") or [],
        "recipe": rec.get("recipe") or {}, "seed": rec.get("seed"),
        "secs": rec.get("secs") or {}, "wall_secs": rec.get("wall_secs"),
        "mesh_secs": (st.get("mesh") or {}).get("mesh_secs"),
        "vram_mib": (st.get("mesh") or {}).get("mesh_vram_mib"),
        "alpha_coverage": (st.get("matte") or {}).get("alpha_coverage"),
        "files": _files_for(kind, rec.get("id"), d),
    }


def _items(kind):
    root = os.path.join(LIB, "bodies" if kind == "body" else "heads")
    name = "body.json" if kind == "body" else "head.json"
    out = []
    for p in sorted(glob.glob(os.path.join(root, "*", name))):
        try:
            rec = json.load(open(p, encoding="utf-8"))
        except Exception:
            continue
        out.append(_card(kind, rec, os.path.dirname(p)))
    return out


def ledger(cards):
    """printable / built-but-not-printable / building / failed. Four states, because
    'built' and 'printable' are not the same claim and collapsing them is the specific
    mistake this project's front page exists to prevent - and because a run still in
    progress is not a run that failed."""
    c = {"printable": 0, "built": 0, "building": 0, "failed": 0}
    for x in cards:
        if x.get("state") == "failed":
            c["failed"] += 1
        elif x.get("state") == "building":
            c["building"] += 1
        elif x.get("printable"):
            c["printable"] += 1
        else:
            c["built"] += 1
    return c


def docs():
    out = []
    for did, title, rel, blurb in DOC_TABS:
        p = os.path.join(ROOT, rel)
        try:
            body = open(p, encoding="utf-8").read()
            out.append({"id": did, "title": title, "path": rel, "blurb": blurb,
                        "body": body, "bytes": len(body)})
        except Exception:
            out.append({"id": did, "title": title, "path": rel, "blurb": blurb,
                        "body": "", "missing": True})
    return out


def assemblies():
    """Preview stacks written by assemble.py: a body, a spring and a head at their real
    heights. PREVIEW ONLY - the three parts print separately, which is the entire point of
    the socket, and the spring is drawn rather than modelled. Carried in the payload
    because it is the one view that answers 'does this actually look like a bobblehead'."""
    out = []
    for p in sorted(glob.glob(os.path.join(LIB, "assembled", "*", "assembled.json"))):
        try:
            rec = json.load(open(p, encoding="utf-8"))
        except Exception:
            continue
        d = os.path.dirname(p)
        name = os.path.basename(d)
        rec["id"] = name
        rec["files"] = {"glb": "/three/media/assembled/%s/assembled.glb" % name}
        for v in sorted(glob.glob(os.path.join(d, "*_orbit.jpg"))):
            rec["files"]["orbit"] = ("/three/media/assembled/%s/%s"
                                     % (name, os.path.basename(v)))
        out.append(rec)
    return out


def _fig_files(fid, d, sub=""):
    """Downloadables for a figure or one of its poses, as /three/media URLs."""
    base = "/three/media/figure/%s" % fid
    pre = (sub + "/") if sub else ""
    out = {}
    for key, name in (("body", "body.glb"), ("head", "head.glb"),
                      ("source", "source.png"), ("styled", "styled.png"),
                      ("head_crop", "head_crop.png"), ("raw", "raw.glb")):
        fp = os.path.join(d, name)
        if os.path.isfile(fp):
            out[key] = "%s/%s%s" % (base, pre, name)
    for fp in sorted(glob.glob(os.path.join(d, "print", "*"))):
        ext = os.path.splitext(fp)[1].lstrip(".").lower()
        if ext in ("stl", "3mf"):
            b = os.path.basename(fp)
            half = "head" if "_head_" in b else "body"
            out["%s_%s" % (half, ext)] = "%s/%sprint/%s" % (base, pre, b)
            out["%s_%s_bytes" % (half, ext)] = os.path.getsize(fp)
    for fp in sorted(glob.glob(os.path.join(d, "views", "*_orbit.jpg"))):
        b = os.path.basename(fp)
        half = "head" if b.endswith("_head_orbit.jpg") else "body"
        out["%s_orbit" % half] = "%s/%sviews/%s" % (base, pre, b)
    return out


def figures():
    """Every figure, with its two halves and any posed bodies.

    A figure is one photograph of a person cut into a matched head and body; a pose is
    another BODY for the same head. So the poses hang off the figure rather than being
    library items in their own right - they share its head, its socket and its person.
    """
    out = []
    for fp in sorted(glob.glob(os.path.join(LIB, "figures", "*", "figure.json"))):
        try:
            rec = json.load(open(fp, encoding="utf-8"))
        except Exception:
            continue
        d = os.path.dirname(fp)
        fid = rec.get("id") or os.path.basename(d)
        parts = rec.get("parts") or {}
        crop = rec.get("stages", {}).get("crop_check") or {}
        poses = []
        for pp in sorted(glob.glob(os.path.join(d, "poses", "*", "pose.json"))):
            try:
                pr = json.load(open(pp, encoding="utf-8"))
            except Exception:
                continue
            pd = os.path.dirname(pp)
            dg = pr.get("diagnose") or {}
            poses.append({
                "id": pr.get("id"), "ok": bool(pr.get("ok")),
                "error": pr.get("error", ""),
                "print_note": pr.get("print_note", ""),
                "socket_mismatch": pr.get("socket_mismatch", ""),
                "faces": dg.get("faces"), "printable": dg.get("printable"),
                "watertight": dg.get("is_watertight"),
                "mm": [round(float(x), 1)
                       for x in ((pr.get("stages", {}).get("neck") or {})
                                 .get("body_extents_mm") or [])],
                "files": _fig_files(fid, pd, "poses/%s" % pr.get("id")),
                "secs": pr.get("wall_secs"),
            })
        out.append({
            "id": fid, "name": rec.get("name") or fid,
            "ok": bool(rec.get("ok")), "error": rec.get("error", ""),
            "state": ("done" if rec.get("ok") else
                      "failed" if rec.get("error") else "building"),
            "body_mm": rec.get("body_mm"), "head_mm": rec.get("head_mm"),
            "was_cropped": bool(crop.get("is_cropped")),
            "crop_note": crop.get("note", ""),
            "head_remeshed": bool((parts.get("head") or {}).get("remeshed")),
            "socket_mm": (parts.get("body") or {}).get("socket_d_mm"),
            "cut_f": (rec.get("stages", {}).get("split") or {}).get("neck_f"),
            "halves": {k: {"mm": v.get("extents_mm"),
                           "faces": (v.get("diagnose") or {}).get("faces"),
                           "printable": (v.get("diagnose") or {}).get("printable"),
                           "watertight": (v.get("diagnose") or {}).get("is_watertight")}
                       for k, v in parts.items()},
            "files": _fig_files(fid, d),
            "poses": poses, "secs": rec.get("wall_secs"),
        })
    return out


def pose_catalogue():
    b = _bobble()
    return [{"id": k, "say": v["say"], "print": v["print"]}
            for k, v in sorted(b.FIGURE_POSES.items())]


def figure(data):
    """POST /api/three/figure - one uploaded photo -> a matched head and body."""
    name = "".join(c for c in str(data.get("image") or "")
                   if c.isalnum() or c in "._-")
    src = os.path.join(STUDIO, "uploads", name)
    if not name or not os.path.isfile(src):
        return {"error": "no such upload: %s" % (name or "(none)")}, 400
    argv = ["figure", "--photo", src]
    for flag, key in (("--id", "id"), ("--name", "name")):
        if data.get(key):
            argv += [flag, str(data[key])]
    for flag, key in (("--body", "body_mm"), ("--head", "head_mm")):
        if data.get(key):
            argv += [flag, str(float(data[key]))]
    if data.get("style") in ("figurine", "raw"):
        argv += ["--style", data["style"]]
    if data.get("redo"):
        argv.append("--redo")
    return _start("figure", argv, target=name)


def pose(data):
    """POST /api/three/pose - more bodies for a figure that already exists."""
    fid = "".join(c for c in str(data.get("figure") or "")
                  if c.isalnum() or c in "._-")
    if not fid or not os.path.isdir(os.path.join(LIB, "figures", fid)):
        return {"error": "no such figure: %s" % (fid or "(none)")}, 400
    argv = ["pose", "--figure", fid]
    poses = data.get("poses")
    if isinstance(poses, (list, tuple)):
        poses = ",".join(str(x) for x in poses)
    if poses:
        argv += ["--poses", str(poses)]
    if data.get("redo"):
        argv.append("--redo")
    return _start("pose", argv, target=fid)


def payload():
    b = _bobble()
    bodies = _items("body")
    heads = _items("head")
    built = {x["id"] for x in bodies}
    pending = [s for s in b.specs() if s["id"] not in built]
    return {
        "bodies": bodies, "heads": heads,
        "figures": figures(), "pose_catalogue": pose_catalogue(),
        "assemblies": assemblies(),
        "pending": pending,
        "ledger": {"bodies": ledger(bodies), "heads": ledger(heads)},
        "recipe": dict(b.RECIPE), "geom": dict(b.GEOM),
        "voxel_mm": b.VOXEL_MM,
        "docs": docs(),
        "engine": {
            "model": "hunyuan_3d_v2.1.safetensors",
            "conditioning": "single view, Hunyuan3Dv2Conditioning",
            "text": False,
            "why_no_text": ("Hunyuan3D has no text encoder. The graph is LoadImage -> "
                            "CLIPVisionEncode -> conditioning; no string reaches the "
                            "model. A prompt on this page is fed to an IMAGE model and "
                            "that picture is what gets meshed."),
            "multiview": False,
            "why_no_multiview": ("MEASURED in terra_3d/mesh/VERDICT.md section 3: the "
                                 "MultiView node fed four cardinals returned 12,108 "
                                 "faces in 134 islands, 26% non-manifold. It needs a "
                                 "hunyuan3d-2mv checkpoint; this box has 2.1."),
        },
    }


def item(kind, rid):
    """One item in full, including the 220-row neck profile the library card omits. The
    profile is the evidence for where the cut went, so the detail view can draw the curve
    rather than assert the number."""
    kind = "body" if kind.startswith("bod") else "head"
    safe = "".join(c for c in str(rid) if c.isalnum() or c in "._-")
    d = os.path.join(LIB, "bodies" if kind == "body" else "heads", safe)
    p = os.path.join(d, "body.json" if kind == "body" else "head.json")
    if not os.path.isfile(p):
        return {"error": "no such %s: %s" % (kind, rid)}, 404
    rec = json.load(open(p, encoding="utf-8"))
    card = _card(kind, rec, d)
    st = rec.get("stages") or {}
    prof = ((st.get("neck") or st.get("socket") or {}).get("profile")) or []
    card["profile"] = prof
    card["trace"] = rec.get("trace", "")
    return card, 200


# ─── jobs ───────────────────────────────────────────────────────────────────────────

def _run(jid, argv):
    def mark(**kw):
        with _LOCK:
            JOBS[jid].update(kw)
    try:
        p = subprocess.Popen([sys.executable, os.path.join(TOOLS, "bobble.py")] + argv,
                             cwd=ROOT, stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT, text=True, bufsize=1)
        lines = []
        for line in p.stdout:
            lines.append(line.rstrip())
            with _LOCK:
                JOBS[jid]["log"] = lines[-40:]
                JOBS[jid]["stage"] = line.strip()[:120]
        p.wait()
        mark(state="done" if p.returncode == 0 else "error",
             returncode=p.returncode,
             error="" if p.returncode == 0 else "bobble.py exited %d" % p.returncode)
    except Exception as e:                                          # noqa: BLE001
        mark(state="error", error="%s: %s" % (type(e).__name__, e))


def _start(kind, argv, **extra):
    with _LOCK:
        _SEQ[0] += 1
        jid = "t3_%d" % _SEQ[0]
        JOBS[jid] = {"id": jid, "kind": kind, "state": "running", "log": [],
                     "stage": "starting", "started": time.time(), **extra}
    threading.Thread(target=_run, args=(jid, argv), daemon=True).start()
    return {"ok": True, "job": jid}, 200


def build(data):
    """POST /api/three/build - one body by id, or the whole catalogue."""
    b = _bobble()
    known = {s["id"] for s in b.specs()}
    bid = str(data.get("id") or "").strip()
    if bid:
        if bid not in known:
            return {"error": "no such body spec: %s" % bid}, 400
        argv = ["body", "--id", bid]
        if data.get("redo"):
            argv.append("--redo")
        if data.get("height"):
            argv += ["--height", str(float(data["height"]))]
        return _start("body", argv, target=bid)
    argv = ["fill"]
    if data.get("redo"):
        argv.append("--redo")
    if data.get("n"):
        argv += ["--n", str(int(data["n"]))]
    return _start("fill", argv, target="catalogue")


def head(data):
    """POST /api/three/head - a photo already in studio/uploads, meshed and socketed."""
    name = "".join(c for c in str(data.get("image") or "")
                   if c.isalnum() or c in "._-")
    if not name:
        return {"error": "no image - upload one first"}, 400
    src = os.path.join(STUDIO, "uploads", name)
    if not os.path.isfile(src):
        return {"error": "the uploaded image is gone: %s" % name}, 400
    argv = ["head", "--photo", src]
    if data.get("id"):
        argv += ["--id", str(data["id"])]
    if data.get("name"):
        argv += ["--name", str(data["name"])]
    if data.get("height"):
        argv += ["--height", str(float(data["height"]))]
    if data.get("style") in ("figurine", "raw"):
        argv += ["--style", data["style"]]
    if data.get("redo"):
        argv.append("--redo")
    return _start("head", argv, target=name)


def job(jid):
    with _LOCK:
        j = JOBS.get(jid)
    return (j or {"error": "no such job"}), (200 if j else 404)


def jobs():
    with _LOCK:
        return {"jobs": sorted(JOBS.values(), key=lambda j: -j["started"])[:20]}, 200


def main():
    p = payload()
    print("  bodies %d  heads %d  pending %d"
          % (len(p["bodies"]), len(p["heads"]), len(p["pending"])))
    for k in ("bodies", "heads"):
        c = p["ledger"][k]
        print("    %-7s %d printable  %d built-not-printable  %d building  %d failed"
              % (k, c["printable"], c["built"], c["building"], c["failed"]))
    print("  docs:")
    for d in p["docs"]:
        print("    %-12s %-42s %s"
              % (d["id"], d["path"], "MISSING" if d.get("missing")
                 else "%.1f KB" % (d["bytes"] / 1024.0)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
