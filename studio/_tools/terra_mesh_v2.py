#!/usr/bin/env python3
"""
terra_mesh_v2.py - re-mesh TERRA from the v2 seeds and TEST the source-fault thesis.

v1 shipped studio/samples/terra_3d/print/TERRA_150mm.stl from ONE seed image,
G_out_dark_s1_rgba.png, through single-view Hunyuan3D at octree 512 / threshold
0.45.  The user looked at it and named two faults: Medusa hair, and wrong fingers
on the right hand.  The source stage (terra_3d_source_v2.py) argued both faults
are already present in the SEED and fixed all three of its new candidates in 2D.

That argument is not yet proven.  This tool proves or breaks it, and the only way
that works is to hold EVERYTHING except the seed fixed:

    v1 winner cell:  single view, latent 4096, octree 512, threshold 0.45,
                     seed 777, surface net, crop=center, white plate, bbox fit,
                     1024 px square.

Every base candidate here runs exactly that cell.  The v1 mesh it is compared
against is not re-run - studio/samples/terra_3d/mesh/I_s512_thr045.glb is still
on disk and IS the v1 winner, so it is read as the control rather than
approximated.

This tool OWNS:
    studio/samples/terra_3d_v2/mesh/*
    studio/samples/terra_3d_v2/print/*
It reads (never writes) studio/samples/terra_3d_v2/source/, and it IMPORTS
terra_mesh.py, mesh_doctor.py and mesh_prep.py rather than editing them - every
topology number comes from mesh_doctor, every print operation from mesh_prep,
and the rasteriser is terra_mesh's.

STAGES, in run order:

    prep      composite each RGBA seed onto a white plate and pad SQUARE, into
              ComfyUI/input/terra3dv2/.  Square matters: CLIPVisionEncode with
              crop=center centre-crops, so a 1664x2432 portrait would lose the
              head and the feet before the model ever saw her.
    gen       drive Hunyuan3D for the candidate table.
    diagnose  mesh_doctor diagnose / repair / thickness / overhang on each.
    render    turntable + head + HAND close-up strips, by software rasterisation.
    contact   one sheet, every candidate, same angles.
    compare   the v1 mesh and the v2 winner side by side, body / head / hands.
    solidify  mesh_prep, the v1 primary recipe exactly, to a printable solid.
    export    STL + 3MF + GLB, each re-read from disk and re-verified.
    report    REPORT.json + a TSV table.

Every subcommand has --help and does nothing else.  A bare invocation prints
usage and exits 2.  All heavy imports are lazy.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

STUDIO = os.path.dirname(HERE)                        # .../studio
ROOT = os.path.dirname(STUDIO)                        # .../comfy-studio
SAMP = os.path.join(STUDIO, "samples", "terra_3d_v2")
SRC = os.path.join(SAMP, "source")
OUT = os.path.join(SAMP, "mesh")
WORK = os.path.join(OUT, "_work")
VIEWS = os.path.join(OUT, "views")
PRINT = os.path.join(SAMP, "print")
PWORK = os.path.join(PRINT, "_work")

MESH_DOCTOR = os.path.join(HERE, "mesh_doctor.py")
MESH_PREP = os.path.join(HERE, "mesh_prep.py")

V1_DIR = os.path.join(STUDIO, "samples", "terra_3d")
V1_RAW = os.path.join(V1_DIR, "mesh", "I_s512_thr045.glb")     # THE v1 winner
V1_SOLID = os.path.join(V1_DIR, "print", "TERRA_150mm.glb")    # v1 shipped solid
V1_SEED = os.path.join(V1_DIR, "source", "G_out_dark_s1_rgba.png")

COMFY = os.path.expanduser("~/ComfyUI")
COMFY_IN = os.path.join(COMFY, "input", "terra3dv2")

# The three seeds the source stage published, in its own order of preference.
SEEDS = [
    ("K3trim", "K3_bun_trim_rgba.png", "FIRST CHOICE. hair H3_bun, hand D4_outfist, "
                                       "seed 4242, plus the NO_TRIM negative."),
    ("K6", "K6_crown_rgba.png", "RUNNER-UP. crown braid, cleanest alpha, most "
                                "definite fists; keeps the shin-length sash panels."),
    ("K3", "K3_bun_rgba.png", "THIRD. identical hair and hands to K3trim with the "
                              "NO_TRIM negative off - isolates that negative."),
]

# The v1 winning cell, verbatim.  Nothing below is a preference.
V1_CELL = dict(octree=512, latent=4096, threshold=0.45, seed=777,
               algorithm="surface net", crop="center")

# The v1 PRIMARY print recipe, read out of terra_3d/print/_work/P_fdm.json.
V1_SOLIDIFY = dict(figure_mm=145.0, total_mm=150.0, pitch=0.15, close_mm=0.6,
                   min_mm=1.0, thin_min_mm3=1.0, grow_frac=0.5, island_frac=0.01,
                   stray_frac=0.005, extract="sdf", voxel_fill="orthographic",
                   up="y", plinth_h=6.0, plinth_margin=5.0, plinth_min_r=12.0,
                   plinth_cham=1.5, sink_mm=1.2, foot_band=3.0)


def _tm():
    """terra_mesh.py belongs to the v1 agent.  Import it, never edit it."""
    import terra_mesh
    return terra_mesh


def log(msg):
    sys.stderr.write("[terra_mesh_v2] %s\n" % msg)
    sys.stderr.flush()


def ensure_dirs():
    for d in (OUT, WORK, VIEWS, PRINT, PWORK, COMFY_IN):
        os.makedirs(d, exist_ok=True)


def read_json(p, default=None):
    try:
        with open(p) as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def write_json(p, obj):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w") as f:
        json.dump(obj, f, indent=2, sort_keys=False)
    return p


def _dig(d, *path):
    cur = d
    for k in path:
        if not isinstance(cur, dict) or k not in cur:
            return None
        cur = cur[k]
    return cur


# ---------------------------------------------------------------------------
# stage: prep
# ---------------------------------------------------------------------------

def stage_prep(args):
    from PIL import Image
    tm = _tm()
    ensure_dirs()
    plate = tm.PLATES[args.plate]
    made = {"plate": {"name": args.plate, "rgb": list(plate)},
            "fit": args.fit, "margin": args.margin, "size": args.size,
            "_": "One crop rectangle per seed (its own alpha bbox) then padded "
                 "square, exactly as v1's prep did for its single view.",
            "seeds": {}}
    for key, fn, why in SEEDS:
        p = os.path.join(SRC, fn)
        im = Image.open(p).convert("RGBA")
        bb = tm.alpha_bbox(im)
        box = bb if args.fit == "bbox" else None
        sq = tm.composite_square(im, plate, args.size, box=box, margin=args.margin)
        name = "v2_%s_%s.png" % (key, args.plate)
        sq.save(os.path.join(COMFY_IN, name))
        made["seeds"][key] = {"file": name, "src": fn, "why": why,
                              "src_px": list(im.size),
                              "alpha_bbox": list(bb) if bb else None,
                              "out_px": list(sq.size)}
        log("prep %s -> %s" % (key, name))

    # The v1 seed put through the SAME preprocessing, so a re-run of the v1 cell
    # is available if the archived v1 mesh is ever doubted.
    im = Image.open(V1_SEED).convert("RGBA")
    bb = tm.alpha_bbox(im)
    sq = tm.composite_square(im, plate, args.size,
                             box=bb if args.fit == "bbox" else None,
                             margin=args.margin)
    sq.save(os.path.join(COMFY_IN, "v2_V1SEED_%s.png" % args.plate))
    made["seeds"]["V1SEED"] = {
        "file": "v2_V1SEED_%s.png" % args.plate, "src": V1_SEED,
        "why": "THE v1 SEED, put through identical preprocessing. Only used if the "
               "archived v1 mesh needs re-deriving; the archived mesh is the control.",
        "src_px": list(im.size), "alpha_bbox": list(bb) if bb else None,
        "out_px": list(sq.size)}

    p = write_json(os.path.join(WORK, "prep.json"), made)
    log("prep -> %s" % p)
    print(json.dumps(made, indent=2))
    return 0


# ---------------------------------------------------------------------------
# the candidate table
# ---------------------------------------------------------------------------

def build_candidates(prep, only=None):
    s = {k: v["file"] for k, v in prep["seeds"].items()}
    C = []

    def add(name, img, why, **kw):
        c = dict(V1_CELL)
        c.update(kw)
        c.update({"name": name, "image": img, "why": why})
        C.append(c)

    # --- THE TEST. Three seeds, one cell, nothing else moved. ---------------
    for key, fn, why in SEEDS:
        add("V2_%s" % key, s[key],
            "THE TEST CELL. v1's winning settings verbatim (single view, latent "
            "4096, octree 512, threshold 0.45, seed 777, surface net). The seed is "
            "the ONLY thing that differs from the v1 mesh. %s" % why)

    # --- second-order dials, on the first choice only -----------------------
    add("V2_K3trim_o640", s["K3trim"], octree=640,
        why="Octree 640. VAEDecodeHunyuan3D declares max=512 in its schema, so this "
            "is expected to be REFUSED by the server rather than to run. Recorded "
            "because 'try a higher octree' has to be answered with what the node "
            "actually permits, not with a guess.")
    add("V2_K3trim_l8192", s["K3trim"], latent=8192,
        why="Latent token count doubled to 8192 at octree 512. The other detail dial, "
            "and the only one left once octree is at its ceiling.")
    add("V2_K3trim_s12345", s["K3trim"], seed=12345,
        why="Second sampler seed at the winning cell, so run-to-run variance is "
            "measured rather than mistaken for a seed-image effect.")

    # --- the archived v1 mesh, re-derived, only if asked --------------------
    add("V2_V1SEED_rerun", s["V1SEED"],
        why="OPTIONAL. The v1 seed through this tool's own preprocessing. Not run by "
            "default - terra_3d/mesh/I_s512_thr045.glb IS the v1 winner and is read "
            "from disk as the control.")

    if only:
        want = set(only)
        C = [c for c in C if c["name"] in want]
    else:
        C = [c for c in C if c["name"] != "V2_V1SEED_rerun"]
    return C


# ---------------------------------------------------------------------------
# stage: gen
# ---------------------------------------------------------------------------

def stage_gen(args):
    tm = _tm()
    ensure_dirs()
    prep = read_json(os.path.join(WORK, "prep.json"))
    if not prep:
        log("no prep.json - run `prep` first")
        return 2
    cands = build_candidates(prep, only=args.only)
    if args.list:
        for c in cands:
            print("%-20s octree=%-4d latent=%-5d thr=%.2f seed=%-6d img=%-22s %s"
                  % (c["name"], c["octree"], c["latent"], c["threshold"],
                     c["seed"], c["image"], c["why"][:60]))
        return 0

    runs = read_json(os.path.join(WORK, "gen.json"), {}) or {}
    for c in cands:
        prev = runs.get(c["name"])
        if prev and not prev.get("error") and not args.force:
            log("skip %s (already done)" % c["name"])
            continue
        prefix = "claude-generated/terra3dv2/%s" % c["name"]
        g = tm.graph_hunyuan({"single": c["image"]}, c["latent"], c["octree"],
                             c["threshold"], c["seed"], c["algorithm"], prefix,
                             crop=c["crop"])
        # terra_mesh prefixes the LoadImage name with "terra3d/"; our plates live
        # in terra3dv2/, so rewrite the one node rather than fork the builder.
        g["2"]["inputs"]["image"] = "terra3dv2/" + c["image"]
        log("RUN %s octree=%d latent=%d thr=%.2f seed=%d"
            % (c["name"], c["octree"], c["latent"], c["threshold"], c["seed"]))
        try:
            outs, wall, vram = tm.run_graph(g, c["name"], timeout=args.timeout)
        except Exception as e:
            msg = str(e)
            log("FAIL %s: %s" % (c["name"], msg[:600]))
            killed = "Connection refused" in msg or "timeout" in msg.lower()
            if killed and not args.no_revive:
                log("  server appears dead - restarting and retrying once")
                tm.revive()
                try:
                    outs, wall, vram = tm.run_graph(g, c["name"], timeout=args.timeout)
                    msg = None
                except Exception as e2:
                    msg = str(e2)
                    tm.revive()
            if msg:
                runs[c["name"]] = dict(c, error=msg[:3000], killed_server=bool(killed))
                write_json(os.path.join(WORK, "gen.json"), runs)
                continue
        files = tm.collect_files(outs)
        glbs = [tm.resolve(f) for f in files
                if f["filename"].lower().endswith((".glb", ".gltf"))]
        local = None
        if glbs:
            local = os.path.join(OUT, "%s.glb" % c["name"])
            shutil.copyfile(glbs[0], local)
        rec = dict(c)
        rec.update({"wall_s": round(wall, 2), "vram": vram,
                    "glb": local, "bytes": os.path.getsize(local) if local else None})
        runs[c["name"]] = rec
        write_json(os.path.join(WORK, "gen.json"), runs)
        log("  done %.1fs peak %s MiB -> %s"
            % (wall, vram.get("peak_mib"), os.path.basename(local or "NOTHING")))
    print(json.dumps(runs, indent=2))
    return 0


# ---------------------------------------------------------------------------
# stage: diagnose - every number from mesh_doctor
# ---------------------------------------------------------------------------

def md(subcmd, mesh, *extra):
    cmd = [sys.executable, MESH_DOCTOR, subcmd, mesh, "--json"] + list(extra)
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=7200)
    out = (p.stdout or "").strip()
    obj = None
    if out:
        i = out.find("{")
        if i >= 0:
            try:
                obj = json.loads(out[i:])
            except ValueError:
                obj = None
    return {"rc": p.returncode, "json": obj,
            "stderr": (p.stderr or "")[-1500:] if p.returncode else ""}


def _targets(args, include_v1=True):
    gen = read_json(os.path.join(WORK, "gen.json"), {}) or {}
    t = []
    for name, rec in sorted(gen.items()):
        if rec.get("glb") and os.path.exists(rec["glb"]):
            t.append((name, rec["glb"]))
    if include_v1 and os.path.exists(V1_RAW):
        t.append(("V1_I_s512_thr045", V1_RAW))
    for p in getattr(args, "extra", None) or []:
        t.append((os.path.splitext(os.path.basename(p))[0], p))
    only = getattr(args, "only", None)
    if only:
        want = set(only)
        t = [x for x in t if x[0] in want]
    return t


def stage_diagnose(args):
    ensure_dirs()
    targets = _targets(args)
    diag = read_json(os.path.join(WORK, "diag.json"), {}) or {}
    for name, path in targets:
        if name in diag and not args.force:
            log("skip diagnose %s" % name)
            continue
        log("diagnose %s" % name)
        t0 = time.time()
        rec = {"path": path, "bytes": os.path.getsize(path)}
        rec["raw"] = md("diagnose", path)
        if args.repair:
            fixed = os.path.join(OUT, "%s_fixed.glb" % name)
            log("  repair -> %s" % os.path.basename(fixed))
            rp = subprocess.run(
                [sys.executable, MESH_DOCTOR, "repair", path, "--out", fixed, "--json"],
                capture_output=True, text=True, timeout=7200)
            rec["repair_rc"] = rp.returncode
            rec["repair_stderr"] = (rp.stderr or "")[-1500:]
            if os.path.exists(fixed):
                rec["fixed"] = fixed
                rec["fixed_bytes"] = os.path.getsize(fixed)
                rec["fixed_diag"] = md("diagnose", fixed)
                rec["thickness"] = md("thickness", fixed, "--height", str(args.height),
                                      "--up", args.up, "--min-mm", str(args.min_mm),
                                      "--samples", str(args.samples))
                rec["overhang"] = md("overhang", fixed, "--height", str(args.height),
                                     "--up", args.up)
        rec["seconds"] = round(time.time() - t0, 1)
        diag[name] = rec
        write_json(os.path.join(WORK, "diag.json"), diag)
    print(json.dumps({k: diag_row(k, v) for k, v in sorted(diag.items())}, indent=2))
    return 0


def diag_row(name, rec):
    r = _dig(rec, "raw", "json") or {}
    f = _dig(rec, "fixed_diag", "json") or {}
    t = _dig(rec, "thickness", "json") or {}
    o = _dig(rec, "overhang", "json") or {}
    return {
        "raw_faces": r.get("faces"),
        "raw_watertight": r.get("is_watertight"),
        "raw_nonmanifold": r.get("nonmanifold_edges"),
        "raw_boundary": r.get("boundary_edges"),
        "raw_islands": r.get("vertex_components"),
        "raw_volume": r.get("volume"),
        "fixed_faces": f.get("faces"),
        "fixed_watertight": f.get("is_watertight"),
        "fixed_islands": f.get("vertex_components"),
        "fixed_volume": f.get("volume"),
        "thickness_p50_mm": _dig(t, "percentiles", "50"),
        "thickness_p10_mm": _dig(t, "percentiles", "10"),
        "thickness_frac_under_min": t.get("fraction_below_min"),
        "overhang_area_frac": o.get("overhang_area_fraction"),
        "flat_ceiling_frac": o.get("flat_ceiling_area_fraction"),
        "bed_contact_mm2": o.get("bed_contact_area"),
    }


# ---------------------------------------------------------------------------
# region sampling - the hands are the point of this iteration, so they get
# their own close-up rather than being squinted at in a body orbit.
# ---------------------------------------------------------------------------

def _load(path):
    import trimesh
    return trimesh.load(path, force="mesh", process=False)


def _slab(m, axis, lo, hi):
    """Keep the part of m between two planes on `axis`, in world units."""
    import numpy as np
    import trimesh
    n = np.zeros(3)
    n[axis] = 1.0
    o = np.zeros(3)
    o[axis] = lo
    m = trimesh.intersections.slice_mesh_plane(m, plane_normal=n, plane_origin=o,
                                               cap=False)
    if m is None or len(getattr(m, "faces", [])) == 0:
        return None
    o[axis] = hi
    m = trimesh.intersections.slice_mesh_plane(m, plane_normal=-n, plane_origin=o,
                                               cap=False)
    if m is None or len(getattr(m, "faces", [])) == 0:
        return None
    return m


def region_points(path, uidx, region, n):
    """region: {axis_index: (lo_frac, hi_frac)} in the mesh's own bbox fractions.
    Slices first, THEN samples, so a close-up gets the whole point budget instead
    of the fraction of a body sample that happened to land on it."""
    import numpy as np
    import trimesh
    m = _load(path)
    b = m.bounds
    ext = b[1] - b[0]
    for ax, (lo, hi) in region.items():
        m = _slab(m, ax, b[0][ax] + ext[ax] * lo, b[0][ax] + ext[ax] * hi)
        if m is None:
            raise RuntimeError("region empty on axis %d" % ax)
    if len(m.faces) < 50:
        raise RuntimeError("region has %d faces" % len(m.faces))
    pts, fid = trimesh.sample.sample_surface(m, n)
    return (np.asarray(pts, dtype="float32"),
            np.asarray(m.face_normals[fid], dtype="float32"),
            np.asarray(m.bounds, dtype="float64"))


def auto_axes(path):
    """Return (up_index, spread_index, depth_index).  Up is the longest extent;
    spread is the longer of the two remaining - for an A-pose figure that is the
    arm span, which is where the hands are."""
    import numpy as np
    m = _load(path)
    ext = m.bounds[1] - m.bounds[0]
    u = int(np.argmax(ext))
    rest = [i for i in (0, 1, 2) if i != u]
    s = rest[0] if ext[rest[0]] >= ext[rest[1]] else rest[1]
    d = rest[0] if s == rest[1] else rest[1]
    return u, s, d, [float(x) for x in ext]


def render_tiles(pts, nrm, bounds, uidx, angles, size, ss, style, label, el=0.0):
    import numpy as np
    tm = _tm()
    c = (bounds[0] + bounds[1]) / 2.0
    half = float(max(bounds[1] - bounds[0])) / 2.0
    ims = []
    for a in angles:
        arr = tm._render_frame(pts, nrm, c, half, uidx, a, el, size, ss, style)
        im = tm._to_pil(arr, size, ss)
        tm._label(im, "%s %d" % (label, int(a)))
        ims.append(im)
    return ims


def stage_hands(args):
    """A sheet of both hands, per mesh, at full point budget."""
    tm = _tm()
    ensure_dirs()
    targets = _targets(args)
    rows = []
    got = {}
    for name, path in targets:
        u, s, d, ext = auto_axes(path)
        log("hands %s  up=%s spread=%s ext=%s" % (name, "xyz"[u], "xyz"[s],
                                                  [round(x, 3) for x in ext]))
        for side, (lo, hi) in (("A", (0.0, args.slab)), ("B", (1.0 - args.slab, 1.0))):
            region = {s: (lo, hi), u: (args.vlo, args.vhi)}
            try:
                pts, nrm, bb = region_points(path, u, region, args.samples)
            except Exception as e:
                log("  %s hand %s: %s" % (name, side, e))
                continue
            ims = render_tiles(pts, nrm, bb, u, args.angles, args.size, args.ss,
                               args.style, "%s %s" % (name, side))
            rows.extend(ims)
            got.setdefault(name, []).append(side)
    if not rows:
        log("nothing rendered")
        return 1
    sheet = tm._strip(rows, len(args.angles))
    p = os.path.join(VIEWS, args.name)
    sheet.save(p, quality=93)
    log("hands -> %s" % p)
    print(p)
    return 0


def stage_render(args):
    tm = _tm()
    ensure_dirs()
    targets = _targets(args, include_v1=args.with_v1)
    got = read_json(os.path.join(WORK, "render.json"), {}) or {}
    for name, path in targets:
        if name in got and not args.force:
            log("skip render %s" % name)
            continue
        log("render %s" % name)
        t0 = time.time()
        try:
            r = tm.render_one(path, name, VIEWS, size=args.size, frames=args.frames,
                              ss=args.ss, up=args.up, samples=args.samples,
                              style=args.style, mp4=args.mp4, el=args.elevation)
        except Exception as e:
            log("  FAIL %s: %s" % (name, str(e)[:400]))
            got[name] = {"error": str(e)[:800]}
            write_json(os.path.join(WORK, "render.json"), got)
            continue
        r["seconds"] = round(time.time() - t0, 1)
        r["src"] = path
        got[name] = r
        write_json(os.path.join(WORK, "render.json"), got)
        log("  %.1fs -> %s" % (r["seconds"], os.path.basename(r["orbit"])))
    print(json.dumps(got, indent=2))
    return 0


def stage_contact(args):
    tm = _tm()
    ensure_dirs()
    targets = _targets(args, include_v1=args.with_v1)
    tiles = []
    for name, path in targets:
        import numpy as np
        pts, nrm, bounds, nf, nv = tm._sample_mesh(path, args.samples)
        ext = bounds[1] - bounds[0]
        u = int(np.argmax(ext))
        ims = render_tiles(pts, nrm, bounds, u, args.angles, args.size, args.ss,
                           args.style, name, el=args.elevation)
        for im in ims:
            tm._label(im, "", "%dk f" % (nf // 1000))
        tiles.extend(ims)
    sheet = tm._strip(tiles, len(args.angles))
    p = os.path.join(VIEWS, args.name)
    sheet.save(p, quality=90)
    log("contact -> %s" % p)
    print(p)
    return 0


def stage_compare(args):
    """v1 and v2 side by side: body row, head row, hands row.  One sheet, so the
    difference is visible at a glance rather than argued."""
    from PIL import Image
    tm = _tm()
    ensure_dirs()
    pairs = []
    for spec in args.mesh:
        if "=" in spec:
            label, path = spec.split("=", 1)
        else:
            label, path = os.path.splitext(os.path.basename(spec))[0], spec
        if not os.path.exists(path):
            log("missing %s" % path)
            return 2
        pairs.append((label, path))

    rows = []
    for label, path in pairs:
        import numpy as np
        u, s, d, ext = auto_axes(path)
        # body
        pts, nrm, bounds, nf, nv = tm._sample_mesh(path, args.samples)
        body = render_tiles(pts, nrm, bounds, u, args.angles, args.size, args.ss,
                            args.style, "%s BODY" % label, el=args.elevation)
        rows.append(body)
        # head
        try:
            hp, hn, hb = region_points(path, u, {u: (1.0 - args.head, 1.0)},
                                       args.samples)
            head = render_tiles(hp, hn, hb, u, args.angles, args.size, args.ss,
                                args.style, "%s HEAD" % label)
            rows.append(head)
        except Exception as e:
            log("head %s: %s" % (label, e))
        # hands, both, framed together on one axis-aligned pair of tiles
        for side, (lo, hi) in (("HAND A", (0.0, args.slab)),
                               ("HAND B", (1.0 - args.slab, 1.0))):
            try:
                hp, hn, hb = region_points(path, u,
                                           {s: (lo, hi), u: (args.vlo, args.vhi)},
                                           args.samples)
            except Exception as e:
                log("%s %s: %s" % (label, side, e))
                continue
            rows.append(render_tiles(hp, hn, hb, u, args.angles, args.size, args.ss,
                                     args.style, "%s %s" % (label, side)))

    ncol = len(args.angles)
    flat = []
    for r in rows:
        flat.extend(r)
    sheet = tm._strip(flat, ncol)
    p = os.path.join(VIEWS, args.name)
    sheet.save(p, quality=93)
    log("compare -> %s" % p)
    print(p)
    return 0


# ---------------------------------------------------------------------------
# print: mesh_prep, the v1 primary recipe, verbatim
# ---------------------------------------------------------------------------

def mp(sub, mesh, *extra):
    cmd = [sys.executable, MESH_PREP, sub, mesh] + list(extra)
    log("  mesh_prep %s %s" % (sub, " ".join(str(x) for x in extra[:6])))
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=14400)
    if p.returncode:
        sys.stderr.write((p.stderr or "")[-4000:] + "\n")
    return {"rc": p.returncode, "stdout": (p.stdout or "")[-4000:],
            "stderr": (p.stderr or "")[-4000:]}


def stage_solidify(args):
    ensure_dirs()
    r = V1_SOLIDIFY
    out = os.path.join(PWORK, "%s.glb" % args.name)
    rep = os.path.join(PWORK, "%s.json" % args.name)
    res = mp("solidify", args.mesh, "--out", out, "--report", rep, "--json",
             "--figure-mm", str(r["figure_mm"]), "--total-mm", str(r["total_mm"]),
             "--pitch", str(args.pitch or r["pitch"]),
             "--close-mm", str(r["close_mm"]), "--min-mm", str(r["min_mm"]),
             "--thin-min-mm3", str(r["thin_min_mm3"]),
             "--grow-frac", str(r["grow_frac"]),
             "--island-frac", str(r["island_frac"]),
             "--stray-frac", str(r["stray_frac"]),
             "--extract", r["extract"], "--voxel-fill", r["voxel_fill"],
             "--up", r["up"], "--plinth", "--plinth-h", str(r["plinth_h"]),
             "--plinth-margin", str(r["plinth_margin"]),
             "--plinth-min-r", str(r["plinth_min_r"]),
             "--plinth-cham", str(r["plinth_cham"]),
             "--sink-mm", str(r["sink_mm"]), "--foot-band", str(r["foot_band"]))
    print(json.dumps({"solid": out, "report": rep, "rc": res["rc"],
                      "recipe": "v1 primary, verbatim"}, indent=2))
    return res["rc"]


def stage_audit(args):
    ensure_dirs()
    rep = os.path.join(PWORK, "audit_%s.json" % args.name)
    thin = os.path.join(PWORK, "thinmap_%s.png" % args.name)
    res = mp("audit", args.mesh, "--json", "--up", "z", "--report", rep,
             "--thinmap", thin, "--name", args.name)
    print(json.dumps({"report": rep, "thinmap": thin, "rc": res["rc"]}, indent=2))
    return res["rc"]


def stage_export(args):
    ensure_dirs()
    outs = []
    for ext in args.formats:
        outs += ["--out", os.path.join(PRINT, "%s.%s" % (args.name, ext))]
    rep = os.path.join(PWORK, "export_%s.json" % args.name)
    res = mp("export", args.mesh, "--json", "--force", "--report", rep, *outs)
    print(res["stdout"])
    return res["rc"]


def stage_card(args):
    ensure_dirs()
    res = mp("card", "--solidify", args.solidify, "--audit", args.audit,
             "--export", args.export, "--primary", args.primary, "--out", args.out)
    return res["rc"]


# ---------------------------------------------------------------------------
# report
# ---------------------------------------------------------------------------

def stage_report(args):
    ensure_dirs()
    gen = read_json(os.path.join(WORK, "gen.json"), {}) or {}
    diag = read_json(os.path.join(WORK, "diag.json"), {}) or {}
    ren = read_json(os.path.join(WORK, "render.json"), {}) or {}
    prep = read_json(os.path.join(WORK, "prep.json"), {}) or {}
    rows = []
    names = sorted(set(list(gen) + list(diag)))
    for name in names:
        g = gen.get(name, {})
        row = {"name": name, "octree": g.get("octree"), "latent": g.get("latent"),
               "threshold": g.get("threshold"), "seed": g.get("seed"),
               "image": g.get("image"), "why": g.get("why"),
               "wall_s": g.get("wall_s"),
               "vram_peak_mib": _dig(g, "vram", "peak_mib"),
               "glb_bytes": g.get("bytes"), "error": g.get("error")}
        row.update(diag_row(name, diag.get(name, {})))
        row["orbit_sheet"] = _dig(ren, name, "orbit")
        row["head_sheet"] = _dig(ren, name, "head")
        rows.append(row)
    rep = {"_": "terra_mesh_v2.py report. Topology numbers are mesh_doctor's; renders "
                "are terra_mesh's point-splat rasteriser. Verdict text is written by "
                "hand into VERDICT.md after the sheets have been opened.",
           "control": {"v1_winner_mesh": V1_RAW, "v1_shipped_solid": V1_SOLID,
                       "v1_cell": V1_CELL},
           "prep": prep, "candidates": rows}
    p = write_json(os.path.join(OUT, "REPORT.json"), rep)
    log("report -> %s" % p)
    hdr = ["name", "octree", "latent", "wall_s", "vram_peak_mib", "raw_faces",
           "raw_watertight", "raw_islands", "raw_volume", "fixed_faces",
           "fixed_watertight", "fixed_islands", "thickness_p50_mm",
           "thickness_frac_under_min", "overhang_area_frac", "bed_contact_mm2"]
    print("\t".join(hdr))
    for r in rows:
        print("\t".join(str(r.get(h)) for h in hdr))
    return 0


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="terra_mesh_v2.py",
        description="Re-mesh TERRA from the v2 seeds, holding v1's winning cell "
                    "fixed, and test whether the two faults were source faults.",
        epilog="Run order: prep, gen, diagnose, render, hands, contact, compare, "
               "solidify, audit, export, card, report.")
    sub = ap.add_subparsers(dest="cmd", metavar="STAGE")

    p = sub.add_parser("prep", help="composite each seed onto a plate, pad square")
    p.add_argument("--plate", default="white",
                   help="white|grey|black|dark - v1 won with white")
    p.add_argument("--fit", choices=["bbox", "canvas"], default="bbox")
    p.add_argument("--margin", type=float, default=0.06)
    p.add_argument("--size", type=int, default=1024)
    p.set_defaults(fn=stage_prep)

    p = sub.add_parser("gen", help="run Hunyuan3D over the candidate table")
    p.add_argument("--only", nargs="*")
    p.add_argument("--list", action="store_true")
    p.add_argument("--force", action="store_true")
    p.add_argument("--no-revive", action="store_true")
    p.add_argument("--timeout", type=int, default=2400)
    p.set_defaults(fn=stage_gen)

    p = sub.add_parser("diagnose", help="mesh_doctor over every candidate")
    p.add_argument("--only", nargs="*")
    p.add_argument("--extra", nargs="*")
    p.add_argument("--repair", action="store_true")
    p.add_argument("--height", type=float, default=150.0)
    p.add_argument("--up", default="y", choices=["auto", "x", "y", "z"])
    p.add_argument("--min-mm", type=float, default=1.0)
    p.add_argument("--samples", type=int, default=40000)
    p.add_argument("--force", action="store_true")
    p.set_defaults(fn=stage_diagnose)

    p = sub.add_parser("render", help="turntable + head strips per candidate")
    p.add_argument("--only", nargs="*")
    p.add_argument("--extra", nargs="*")
    p.add_argument("--with-v1", action="store_true",
                   help="include the archived v1 winner mesh")
    p.add_argument("--size", type=int, default=460)
    p.add_argument("--frames", type=int, default=8)
    p.add_argument("--ss", type=int, default=2)
    p.add_argument("--up", default="auto", choices=["auto", "x", "y", "z"])
    p.add_argument("--samples", type=int, default=2600000)
    p.add_argument("--style", default="clay", choices=["clay", "normal"])
    p.add_argument("--elevation", type=float, default=8.0)
    p.add_argument("--mp4", type=int, default=0)
    p.add_argument("--force", action="store_true")
    p.set_defaults(fn=stage_render)

    p = sub.add_parser("hands", help="close-up of both hands, full point budget")
    p.add_argument("--only", nargs="*")
    p.add_argument("--extra", nargs="*")
    p.add_argument("--angles", nargs="*", type=int, default=[0, 60, 120, 180])
    p.add_argument("--slab", type=float, default=0.14,
                   help="fraction of the arm-span axis kept at each end")
    p.add_argument("--vlo", type=float, default=0.35)
    p.add_argument("--vhi", type=float, default=0.80)
    p.add_argument("--size", type=int, default=420)
    p.add_argument("--ss", type=int, default=2)
    p.add_argument("--samples", type=int, default=1400000)
    p.add_argument("--style", default="clay", choices=["clay", "normal"])
    p.add_argument("--name", default="HANDS.jpg")
    p.set_defaults(fn=stage_hands)

    p = sub.add_parser("contact", help="one sheet, all candidates, same angles")
    p.add_argument("--only", nargs="*")
    p.add_argument("--extra", nargs="*")
    p.add_argument("--with-v1", action="store_true")
    p.add_argument("--angles", nargs="*", type=int, default=[0, 90, 180, 270])
    p.add_argument("--size", type=int, default=380)
    p.add_argument("--ss", type=int, default=2)
    p.add_argument("--samples", type=int, default=1800000)
    p.add_argument("--style", default="clay", choices=["clay", "normal"])
    p.add_argument("--elevation", type=float, default=8.0)
    p.add_argument("--name", default="CONTACT.jpg")
    p.set_defaults(fn=stage_contact)

    p = sub.add_parser("compare", help="LABEL=path ... body/head/hands rows, one sheet")
    p.add_argument("mesh", nargs="+", help="LABEL=path")
    p.add_argument("--angles", nargs="*", type=int, default=[0, 90, 180])
    p.add_argument("--head", type=float, default=0.26)
    p.add_argument("--slab", type=float, default=0.14)
    p.add_argument("--vlo", type=float, default=0.35)
    p.add_argument("--vhi", type=float, default=0.80)
    p.add_argument("--size", type=int, default=420)
    p.add_argument("--ss", type=int, default=2)
    p.add_argument("--samples", type=int, default=1800000)
    p.add_argument("--style", default="clay", choices=["clay", "normal"])
    p.add_argument("--elevation", type=float, default=8.0)
    p.add_argument("--name", default="V1_VS_V2.jpg")
    p.set_defaults(fn=stage_compare)

    p = sub.add_parser("solidify", help="mesh_prep solidify, v1 primary recipe verbatim")
    p.add_argument("mesh")
    p.add_argument("--name", required=True)
    p.add_argument("--pitch", type=float, default=None,
                   help="override the 0.15 mm grid (for a cheap smoke test)")
    p.set_defaults(fn=stage_solidify)

    p = sub.add_parser("audit", help="mesh_prep audit + thin map at real scale")
    p.add_argument("mesh")
    p.add_argument("--name", required=True)
    p.set_defaults(fn=stage_audit)

    p = sub.add_parser("export", help="write STL/3MF/GLB and re-verify each from disk")
    p.add_argument("mesh")
    p.add_argument("--name", required=True)
    p.add_argument("--formats", nargs="*", default=["stl", "3mf", "glb"])
    p.set_defaults(fn=stage_export)

    p = sub.add_parser("card", help="write the print card from the stage JSONs")
    p.add_argument("--solidify", required=True)
    p.add_argument("--audit", required=True)
    p.add_argument("--export", required=True)
    p.add_argument("--primary", required=True)
    p.add_argument("--out", required=True)
    p.set_defaults(fn=stage_card)

    p = sub.add_parser("report", help="assemble REPORT.json")
    p.set_defaults(fn=stage_report)

    args = ap.parse_args(argv)
    if not getattr(args, "fn", None):
        ap.print_usage(sys.stderr)
        sys.stderr.write("terra_mesh_v2.py: a STAGE is required\n")
        return 2
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
