#!/usr/bin/env python3
"""studio/_tools/bobble.py - bobblehead bodies and heads, seed image to printable pair.

    python3 studio/_tools/bobble.py catalog                 what bodies are specified
    python3 studio/_tools/bobble.py body  --id hero_suit    one body, every stage
    python3 studio/_tools/bobble.py head  --photo p.jpg     one supersized head
    python3 studio/_tools/bobble.py fill  --n 12            build the library
    python3 studio/_tools/bobble.py report                  measurements, per item

WHAT A BOBBLEHEAD IS, MECHANICALLY, AND WHY THE PIPELINE IS SHAPED THIS WAY.

A bobblehead is two printed solids and one spring. The body carries a SOCKET in its neck
stump; the head carries a matching socket in its underside; a compression spring glues
into both. So the two things this tool must guarantee are not artistic - they are that a
socket of a known diameter exists at a known place on a flat face, on both parts, at the
same size in millimetres.

THE HEAD IS CUT OFF GEOMETRICALLY, NOT PROMPTED AWAY. An earlier plan asked the image
model for "a headless body". Image models render nouns and are poor at absence: the seed
comes back with a head anyway, or with a stump drawn as a wound. So the seed asks for a
COMPLETE figure - which is what the model is good at - and the head is removed from the
MESH by a plane cut at the narrowest cross-section above the shoulders. A plane cut cannot
misunderstand the instruction. It also leaves a real neck cross-section to bore into,
which a prompted stump would not.

    The neck finder is `neck_plane`. It measures the enclosed cross-sectional area at 220
    heights between 0.52H and 0.94H and takes the minimum that still has a head above it.
    It reports the diameter it found, so a bad cut is visible in the report as a neck
    that is 40 mm wide rather than discovered later on the printer.

THE MESH RECIPE IS NOT A NEW OPINION. octree 512, threshold 0.45, latent 4096, surface
net, 30 steps, cfg 5.0, repair at voxel-res 900 are the settings MEASURED as the winner in
studio/samples/terra_3d/mesh/VERDICT.md sections 1-2, on this box, on a figure. This tool
calls terra_mesh.graph_hunyuan rather than rebuilding the wiring, for the reason
make3d_routes.py already gives: one builder, or two graphs that drift.

WHAT THE SEED PROMPT ENFORCES, AND WHERE EACH RULE WAS LEARNED.
  hair as ONE closed mass       terra_3d_source_v2: separated locks became stacked tubes
                                and the mesh read as Medusa. A mould cannot release free
                                strands and a printer cannot support them.
  arms close to the body        RULE OF THUMB, print: an outstretched arm is an overhang
                                and a thin unsupported part. The figurine literature and
                                every vinyl toy agree; we are not testing this one.
  "cast shadow" in the NEGATIVE terra_3d_source_v2 MEASURED that asking for "no cast
                                shadow" in the POSITIVE does not work - the word has to
                                move to the negative to land.
  no held thin objects          a sword or a cane at 110 mm is under the printable
                                minimum and the matte eats it anyway.
  full figure with margin       so composite_square's alpha crop has something to find.
"""
import argparse
import glob
import json
import math
import os
import shutil
import subprocess
import sys
import time

TOOLS = os.path.dirname(os.path.abspath(__file__))
STUDIO = os.path.dirname(TOOLS)
ROOT = os.path.dirname(STUDIO)
LIB = os.path.join(STUDIO, "bobblehead")
BODIES = os.path.join(LIB, "bodies")
HEADS = os.path.join(LIB, "heads")
FIGURES = os.path.join(LIB, "figures")
SPECS = os.path.join(LIB, "specs.json")

sys.path.insert(0, TOOLS)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
os.environ.setdefault("COMFY_HOST", "127.0.0.1:8188")

# The measured recipe. Named constants so the report can print what it used and a sweep
# can move one of them without a search-and-replace through the file.
RECIPE = {"latent_resolution": 4096, "octree_resolution": 512, "threshold": 0.45,
          "algorithm": "surface net", "steps": 30, "cfg": 5.0}

# *** THE REPAIR RESOLUTION IS A FACE DIAL, NOT A BODY DIAL. MEASURED HERE. ***
#
# to_print.py records that `repair --voxel-res 320` returns "a terraced Minecraft mass
# with no eyes and no nose" and prescribes 900 for everything. Repeating that comparison
# on suit_male's raw mesh at 500 and 900, and opening both head crops at 520 px:
#
#   voxel-res 500  820,366 faces  the face is an unambiguous voxel staircase - the eyelids
#                                 are terraced, the nostrils are steps, the ear is a stack
#   voxel-res 900  2,644,212      eyelids, nostril, ear cartilage all read as surfaces
#
# JUDGED, on the SAME two renders, cropped to the torso instead: at 500 the suit holds
# every feature it has - lapel roll, four waistcoat buttons, both pocket flaps, the trouser
# crease. The terracing that ruins a face is invisible on cloth.
#
# So 900 everywhere is 3.2x the triangles to protect detail this pipeline THROWS AWAY: the
# body's head is cut off and replaced. The dial is therefore set from the target voxel size
# in millimetres, per part and per process, rather than from one number.
#
# The mm figures are RULE OF THUMB against the printers, not measured prints: a 0.4 mm
# nozzle cannot resolve below about 0.3 mm in XY, so a finer voxel than that buys file size
# and nothing else; resin at 0.035 mm XY can still use 0.10.
# *** THE REPAIR GRID IS A FIDELITY DIAL AGAIN, BECAUSE DECIMATION NOW HANDLES SIZE. ***
#
# These were loosened once stage_smooth existed, on the reasoning that smoothing does the
# anti-aliasing resolution used to pay for. MEASURED against the RAW mesh as ground truth,
# that reasoning was wrong in the direction that matters - a coarse grid plus heavy
# smoothing is the WORST of both worlds, because the grid throws detail away permanently
# and the smoothing then removes whatever survived:
#
#     path                    mean distance from RAW      what it looks like
#     v489 + taubin60           0.1512 mm                 melted wax
#     v900 + taubin25           0.0888 mm                 finer ripple, hair legible
#     v1200 + taubin20          0.0678 mm                 finest ripple, most hair kept
#
# Finer grid, LESS smoothing, then decimate back to a sane file size. stage_decimate showed
# face count and fidelity are independent: decimating 4.7M -> 800k left the mean distance
# at 0.0678 mm, unchanged to four decimals. So there is no reason to buy the size saving
# with a coarse grid when it can be had for free afterwards.
VOXEL_MM = {"fdm": {"body": 0.122, "head": 0.095},
            "resin": {"body": 0.105, "head": 0.085}}
# head 0.095 rather than 0.080: MEASURED, 0.080 puts a 95 mm head at voxel-res 1187,
# which OOM-killed the repair on a long-haired head whose raw mesh is 43 MB. 0.095
# lands at 1000 and leaves headroom; stage_solid steps down further if even that is
# too heavy for a particular mesh.
# Raised from 1000: MEASURED, repair at 1200 completes in 69 s of CPU and 4.7M faces. This
# is mesh_doctor's own voxeliser, NOT ComfyUI's decoder, so it has nothing to do with the
# 640-octree memory wall in docs/3D-QUALITY.md.
VOXEL_RES_CLAMP = (320, 1400)

# Faces to decimate down to after smoothing. The fidelity is already banked by then; this
# only decides how big the download is. Roughly matches what the old coarse-grid path
# produced, so files do not grow.
TARGET_FACES = {"body": 800000, "head": 900000}

# The neck lands around three-quarters of the way up a figure in these proportions
# (MEASURED 0.762 on suit_male). Only used to guess the full figure's height so the voxel
# count can be set before the cut; the body is rescaled to its exact target afterwards.
NECK_FRACTION_GUESS = 0.75

# *** THE OCTREE THAT FITS IS PER-SUBJECT, NOT PER-SETTING. ***
# MEASURED on a full standing figure: octree 512 OOM-killed ComfyUI twice - available
# memory fell from 34.7 GB to 841 MB inside one six-second sample - while 448, 384 and 320
# all completed in 20-37 s at 9.4 GB of VRAM and produced 415k, 307k and 213k faces. The
# spike is in the VoxelToMesh extraction, not the decode, and it is not proportional: 448
# is fine and 512 takes the machine down.
#
# A headless bobblehead body is chunky and meshes at 512 without trouble; a tall slender
# person with separated legs does not. So the ladder is walked downward on failure rather
# than the setting being lowered for everyone, and the record says which rung ran.
OCTREE_LADDER = [512, 448, 384, 320]
# Where a WHOLE FIGURE starts on that ladder. 512 has failed on every full
# standing figure tried, and each failure costs a ComfyUI restart.
FIGURE_OCTREE = 448

# Millimetres. A 1:1 classic bobblehead is roughly 180-200 mm overall; supersizing the
# head shifts the split rather than the total.
GEOM = {"body_mm": 110.0, "head_mm": 95.0,
        "socket_d": 8.4,      # a 8.0 mm OD spring plus 0.4 mm of glue and print slop
        "socket_depth": 12.0,  # into the body neck
        "head_socket_depth": 14.0,
        "mouth_chamfer": 1.2,  # a lead-in so the spring finds the hole
        # Taubin passes over the repaired solid, to take off the staircase the voxel
        # repair puts on. See stage_smooth.
        #
        # 20, not 60. 60 was tuned against a 0.30 mm grid, where the steps are so coarse
        # that removing them takes enough smoothing to melt the model with them. On the
        # 0.122 mm grid the steps are a quarter the size and 20 passes clears them - and
        # MEASURED, the pair (finer grid, less smoothing) lands 55% closer to the raw mesh
        # than the pair it replaces.
        # ZERO. Screened Poisson leaves no staircase to remove, so a smoothing
        # pass would only cost detail. Kept as a dial because the voxel
        # fallback still needs it - stage_smooth is skipped when it is 0.
        "taubin_iters": 0}

PLATE_WHITE = (255, 255, 255)

# Points the preview splatter throws at each item. See stage_views for why this is a
# correctness setting and not a cosmetic one.
RENDER_SAMPLES = 9000000


def log(m):
    print("  " + m, flush=True)


# ─── the seed prompt ────────────────────────────────────────────────────────────────

FIGURINE_SPINE = (
    "chunky simplified toy proportions, smooth continuous sculpted surfaces, "
    "hair sculpted as one solid closed mass with carved grooves, "
    "arms held close to the body, feet together on a small round plinth, "
    "the complete figure from the top of the head to the base with clear margin on all "
    "sides, straight-on front view at eye level, even soft frontal studio light, "
    "flat plain light grey background, "
    "studio product photograph of a hand-painted resin collectible figure, sharp focus")

# MEASURED, and the fix is one word: v1 negated "flowing cape" and "billowing fabric", and
# the superhero came back WEARING A CAPE - a thin sheet the size of the figure. The model
# reads "flowing cape" as a cape that is flowing, and gives you a cape that is not. Negate
# the NOUN, not the noun with an adjective attached. Same correction applied to hair.
FIGURINE_NEG = (
    "cast shadow, drop shadow, shadow on the floor, contact shadow, "
    "floating hair strands, separated hair locks, loose flowing hair, "
    "cape, cloak, flowing cape, billowing fabric, scarf, ribbons, "
    "thin wispy details, trailing fabric, "
    "splayed fingers, outstretched arms, holding a thin object, sword, staff, cane, "
    "cropped, cut off, close-up, portrait crop, multiple views, turnaround sheet, "
    "two figures, text, watermark, signature, logo, "
    "busy background, scenery, gradient background, vignette, "
    "low quality, blurry, bad anatomy, extra limbs, extra arms, deformed")


def prompt_for(spec):
    """Subject and costume vary; the figurine grammar does not."""
    bits = [b for b in (spec.get("subject"), spec.get("costume"), spec.get("pose"))
            if b]
    return "a stylized collectible vinyl figurine of %s, %s" % (
        ", ".join(bits), FIGURINE_SPINE)


# ─── stages ─────────────────────────────────────────────────────────────────────────

def _comfy():
    from comfy import run, set_path                                    # noqa: E402
    from epic import load_wf, ensure_local, HOST, COMFY                # noqa: E402
    return run, set_path, load_wf, ensure_local, HOST, COMFY


def free_models():
    """Ask ComfyUI to drop its cached model weights.

    *** THIS CALL IS WHY THE PIPELINE RUNS IN PHASES, AND IT WAS MEASURED THE HARD WAY. ***
    Generating the Qwen seed image and then meshing it in the same ComfyUI process
    OOM-killed the server: `Out of memory: Killed process (python) anon-rss:55280608kB`,
    journalctl 2026-08-22 16:29. Not VRAM - HOST RAM, on a 60 GB box. Qwen Image stages
    ~19.5 GB of weights and ComfyUI keeps them cached after the job; VoxelToMesh at octree
    512 then asks for its own ~11 GB and the kernel picks the biggest process.

    The symptom is a bare `URLError: Connection refused` mid-run with no traceback, which
    reads like a network fault and is not one. Freeing first costs one model reload per
    phase; not freeing costs the whole run.
    """
    import urllib.request
    host = os.environ.get("COMFY_HOST", "127.0.0.1:8188")
    try:
        req = urllib.request.Request(
            "http://%s/free" % host,
            data=json.dumps({"unload_models": True,
                             "free_memory": True}).encode(),
            headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=60).read()
        time.sleep(2)
        return True
    except Exception:
        return False


def stage_source(d, spec, seed):
    """The seed image. Qwen turbo: 4 steps, and the figurine grammar is doing the work
    here, not the sampler."""
    run, set_path, load_wf, ensure_local, HOST, COMFY = _comfy()
    wf = load_wf("01_qwen_t2i_turbo.json")
    set_path(wf, "10.inputs.text", prompt_for(spec))
    set_path(wf, "11.inputs.text", FIGURINE_NEG)
    set_path(wf, "12.inputs.width", 1024)
    set_path(wf, "12.inputs.height", 1408)      # a standing figure is tall
    set_path(wf, "13.inputs.seed", seed)
    set_path(wf, "15.inputs.filename_prefix", "claude-generated/bobble/%s" % spec["id"])
    _, outs = run(HOST, wf, quiet=True)
    if not outs:
        raise RuntimeError("the seed image produced no output")
    dst = os.path.join(d, "source.png")
    if os.path.exists(dst):
        os.remove(dst)
    ensure_local(outs[0], dst)
    return dst


# The head's figurine pass. A PHOTOGRAPH IS NOT A SCULPT-READY IMAGE and the three ways
# it is not are the three clauses below.
#
#   Loose hair. Every lesson terra_3d_source_v2 learned about drawn hair applies harder to
#   photographed hair: individual strands become tubes and a flyaway becomes a spike.
#
#   Baked light. Hunyuan3D sculpts what it sees. A hard shadow under a cheekbone is read as
#   geometry, so a portrait shot with a key light comes back with the key light carved into
#   it. This is the "delighting" step a commercial pipeline runs and docs/3D-QUALITY.md §3.4
#   lists as untested here - the head path is where it gets tested.
#
#   Shoulders and background. The mesh should be a head, not a bust in a room.
#
# Run with --style raw to skip it and mesh the photograph as-is. Keeping both is the point:
# the two source images sit side by side in the item folder, so the pass can be judged
# rather than assumed.
HEAD_FIGURINE = (
    "Turn this into a collectible figurine head. Keep the face, the likeness and the "
    "hairstyle exactly. Remove the background completely and replace it with flat plain "
    "light grey. Crop to the head and the top of the neck only, no shoulders. Relight with "
    "completely even flat frontal light: no cast shadow, no hard shadow under the chin or "
    "the nose, no specular highlight, no rim light. Sculpt the hair as one solid closed "
    "mass with carved grooves, no loose or flyaway strands. Smooth the skin into continuous "
    "sculpted surfaces like painted resin. Face the camera straight on at eye level.")


def stage_stylize(d, src, seed=777):
    """Photo -> figurine head, through the 4-step Qwen edit. Writes source_styled.png and
    returns it; the original stays as source.png so both can be looked at."""
    run, set_path, load_wf, ensure_local, HOST, COMFY = _comfy()
    staged = "bobble_head_src_%d.png" % (int(time.time() * 1000) % 10 ** 8)
    shutil.copy(src, os.path.join(COMFY, "input", staged))
    wf = load_wf("22_qwen_edit_2511.json")
    set_path(wf, "7.inputs.image", staged)
    set_path(wf, "10.inputs.prompt", HEAD_FIGURINE)
    set_path(wf, "12.inputs.prompt", "")
    set_path(wf, "15.inputs.seed", int(seed))
    set_path(wf, "17.inputs.filename_prefix", "claude-generated/bobble/head_styled")
    _, outs = run(HOST, wf, quiet=True)
    if not outs:
        raise RuntimeError("the figurine pass produced no output")
    dst = os.path.join(d, "source_styled.png")
    if os.path.exists(dst):
        os.remove(dst)
    ensure_local(outs[0], dst)
    return dst


def stage_matte(d, src=None):
    """BiRefNet to RGBA, then alpha-crop and square on white - the exact shape
    VERDICT.md section 1 fed the winning mesh."""
    from PIL import Image
    import terra_mesh
    run, set_path, load_wf, ensure_local, HOST, COMFY = _comfy()
    src = src or os.path.join(d, "source.png")
    staged = "bobble_matte_%d.png" % (int(time.time() * 1000) % 10 ** 8)
    shutil.copy(src, os.path.join(COMFY, "input", staged))

    wf = load_wf("14_birefnet_matte.json")
    set_path(wf, "1.inputs.image", staged)
    im = Image.open(src)
    set_path(wf, "8.inputs.width", im.width)
    set_path(wf, "8.inputs.height", im.height)
    set_path(wf, "10.inputs.filename_prefix", "claude-generated/bobble/matte/rgba")
    _, outs = run(HOST, wf, quiet=True)
    if not outs:
        raise RuntimeError("the matte produced no output")
    rgba_p = os.path.join(d, "source_rgba.png")
    if os.path.exists(rgba_p):
        os.remove(rgba_p)
    # node 10 writes the RGBA cutout; ensure_local takes the first, so pick by name.
    pick = next((o for o in outs if "rgba" in str(o).lower()), outs[0])
    ensure_local(pick, rgba_p)

    rgba = Image.open(rgba_p).convert("RGBA")
    box = terra_mesh.alpha_bbox(rgba)
    if box is None:
        raise RuntimeError("the matte came back empty - nothing was cut out")
    cov = (box[2] - box[0]) * (box[3] - box[1]) / float(rgba.width * rgba.height)
    sq = terra_mesh.composite_square(rgba, PLATE_WHITE, 1024, box=box, margin=0.06)
    sq_p = os.path.join(d, "source_square.png")
    sq.save(sq_p)
    return sq_p, {"alpha_box": list(box), "alpha_coverage": round(cov, 4)}


def stage_mesh(d, sq_p, seed, tag="body", octree_start=None):
    """Hunyuan3D at the measured recipe. The image is already square, so the node's
    center crop has nothing left to cut - which is the whole reason for squaring here
    rather than letting CLIPVisionEncode do it."""
    import terra_mesh
    from epic import COMFY
    stage_dir = os.path.join(COMFY, "input", "terra3d")
    os.makedirs(stage_dir, exist_ok=True)
    staged = "bobble_%s_%d.png" % (tag, int(time.time() * 1000) % 10 ** 8)
    shutil.copyfile(sq_p, os.path.join(stage_dir, staged))

    g = terra_mesh.graph_hunyuan(
        {"single": staged},
        latent_res=RECIPE["latent_resolution"], octree=RECIPE["octree_resolution"],
        threshold=RECIPE["threshold"], seed=seed, algorithm=RECIPE["algorithm"],
        prefix="claude-generated/bobble/%s" % tag, crop="center",
        steps=RECIPE["steps"], cfg=RECIPE["cfg"])

    free_models()
    outs = wall = vram = None
    used_octree = None
    # A caller that already knows its subject class can start lower. MEASURED: a full
    # standing figure has taken the server down at 512 on every attempt, and each
    # attempt costs a ComfyUI restart - about a minute of nothing. Starting figures at
    # 448 skips two restarts an item and loses nothing, because 512 never held.
    top = int(octree_start or RECIPE["octree_resolution"])
    ladder = [o for o in OCTREE_LADDER if o <= top] or [top]
    last = None
    for oct_res in ladder:
        g["8"]["inputs"]["octree_resolution"] = oct_res
        for attempt in (1, 2):
            try:
                outs, wall, vram = terra_mesh.run_graph(g, "bobble/%s" % tag)
                used_octree = oct_res
                break
            except Exception as e:                                    # noqa: BLE001
                # A dead socket here is the OOM described in free_models, not a bug in the
                # graph. Stand the server back up and try once more at this rung before
                # stepping down - the same contract terra_mesh's own grid runner works under.
                last = e
                log("comfy went away at octree %d - reviving (attempt %d)"
                    % (oct_res, attempt))
                terra_mesh.revive()
                free_models()
        if used_octree:
            break
        log("octree %d did not survive - stepping down" % oct_res)
    if not used_octree:
        raise RuntimeError("the mesh failed at every octree down to %d: %s"
                           % (ladder[-1], last))
    if used_octree != top:
        log("meshed at octree %d instead of %d" % (used_octree, top))
    files = terra_mesh.collect_files(outs) if outs else []
    if not files:
        raise RuntimeError("the mesh job produced no file")
    src = terra_mesh.resolve(files[0])
    dst = os.path.join(d, "raw.glb")
    shutil.copyfile(src, dst)
    return dst, {"mesh_secs": round(wall, 1), "octree": used_octree,
                 "octree_stepped_down": used_octree != top,
                 "mesh_vram_mib": (vram or {}).get("peak_mib")
                 if isinstance(vram, dict) else None}


def md(subcmd, mesh, *extra):
    """mesh_doctor, as a subprocess, parsed from its --json. The same call shape
    terra_mesh.md uses, repeated here so this file has no import cycle with it."""
    r = subprocess.run([sys.executable, os.path.join(TOOLS, "mesh_doctor.py"),
                        subcmd, mesh, "--json", *[str(x) for x in extra]],
                       capture_output=True, text=True, cwd=ROOT, timeout=3600)
    try:
        return json.loads(r.stdout[r.stdout.index("{"):r.stdout.rindex("}") + 1])
    except Exception:
        raise RuntimeError("mesh_doctor %s failed: %s"
                           % (subcmd, (r.stderr or r.stdout)[-400:]))


def voxel_res(part, mm_tall, process="fdm"):
    """Voxels along the longest axis, derived from the target voxel size in mm rather
    than pinned to one number. See VOXEL_MM for the measurement behind the split."""
    target = VOXEL_MM.get(process, VOXEL_MM["fdm"])[part]
    v = int(round(mm_tall / target))
    return max(VOXEL_RES_CLAMP[0], min(VOXEL_RES_CLAMP[1], v))


# Octree depth for the Poisson solve, passed through to mesh_doctor. MEASURED: depth 10 gives dev 0.0028 mm and depth 12
# gives 0.0026 - no meaningful difference, and near-identical face counts (2.39M vs 2.49M).
# Depth 12 costs 30-42 GB of RSS and OOM-KILLED the batch on its fourth body while ComfyUI
# held its usual 20 GB. Depth 10 buys the same surface for a fraction of the memory.
POISSON_DEPTH = {"body": 10, "head": 10}


def stage_solid(d, part, mm_tall, process="fdm", cache=True):
    """Repair to a closed manifold solid at the resolution this part actually needs.

    Cached on the voxel resolution, written beside the mesh. The repair is 30-60 s of CPU
    and it is a pure function of (raw.glb, voxel_res) - so re-running the finish phase
    after a change to the NECK FINDER, which is what that phase is usually re-run for,
    should not pay for it again. A change to the resolution invalidates it by value."""
    raw = os.path.join(d, "raw.glb")
    solid = os.path.join(d, "solid.glb")
    stamp = os.path.join(d, ".solid_voxel_res")
    vr = voxel_res(part, mm_tall, process)
    if cache and os.path.isfile(solid) and os.path.isfile(stamp):
        try:
            if int(open(stamp).read().strip()) == vr and \
                    os.path.getmtime(solid) >= os.path.getmtime(raw):
                return solid, vr
        except Exception:
            pass

    # *** ONE REPAIR, IN ONE PLACE. ***
    # This file used to carry its own screened-Poisson implementation. mesh_doctor now owns
    # it - `repair --method auto` is poisson, then surface, then the voxel remesh - so every
    # tool in the studio gets the same surface: to_print, terra_mesh, /make3d and this one.
    # Two copies of a repair is how a project ends up with two that drift, which is the
    # argument make3d_routes.py already makes for not rebuilding terra_mesh's graph.
    depth = POISSON_DEPTH.get(part, 10)
    try:
        md("repair", raw, "--method", "auto", "--poisson-depth", depth,
           "--voxel-res", vr, "--out", solid)
        import trimesh
        chk = trimesh.load(solid, force="mesh", process=True)
        if chk.is_watertight:
            open(stamp, "w").write("auto%d_%d" % (depth, vr))
            return solid, -depth           # negative marks the poisson path
        log("%s: repair returned an open mesh - stepping the grid down"
            % os.path.basename(d))
    except Exception as e:                                            # noqa: BLE001
        log("%s: repair failed (%s) - stepping the grid down"
            % (os.path.basename(d), str(e)[:70]))

    # *** THE REPAIR GRID HAS A RAM CEILING AND IT IS PER-MESH, NOT PER-SETTING. ***
    # MEASURED: repair at 1187 succeeded on two heads (5.6M and 7.4M faces out) and was
    # OOM-KILLED on a third - exit 137, on a 60 GB box - because that head has long hair and
    # a much denser raw mesh. The setting is fine; the mesh is heavier.
    #
    # A run that dies takes the whole item with it and writes ok:false over work that was
    # otherwise sound, so a failure steps the grid down and says so rather than giving up.
    # Fidelity degrades; the item still ships.
    last = None
    for step in (1.0, 0.78, 0.6):
        try_vr = max(VOXEL_RES_CLAMP[0], int(vr * step))
        try:
            md("repair", raw, "--method", "voxel", "--voxel-res", try_vr, "--out", solid)
            open(stamp, "w").write(str(try_vr))
            if try_vr != vr:
                log("%s: repair fell back to voxel-res %d (from %d)"
                    % (os.path.basename(d), try_vr, vr))
            return solid, try_vr
        except Exception as e:                                        # noqa: BLE001
            last = e
            log("%s: repair at voxel-res %d failed (%s) - stepping down"
                % (os.path.basename(d), try_vr, str(e)[:60]))
    raise RuntimeError("the repair failed at every resolution down to %d: %s"
                       % (int(vr * 0.6), last))


def stage_smooth(d, src, iterations=None, out_name="smooth.glb"):
    """Take the staircase off the repaired solid.

    *** THE TERRACING IS THE REPAIR, NOT THE MODEL, AND NOT THE OCTREE. ***

    MEASURED by rendering the same shoulder crop off four meshes at 12M splat samples:
    Hunyuan3D's own output is SMOOTH - surface-net places vertices at sub-cell positions,
    so a 512 octree does not have to look like 512 steps. Every `repair --method voxel`
    result is stepped: 489, 900 and 1200 differ only in how fine the staircase is, never in
    whether there is one. Voxel repair rasterises to binary occupancy and re-extracts, and
    the steps are that rasterisation.

    This matters beyond cosmetics: it means the octree ceiling in docs/3D-QUALITY.md - the
    one blocked by system RAM - was never what made these surfaces rough. A dial nobody
    could turn was being blamed for damage done two stages later by a dial that was free.

    Taubin rather than Laplacian. Plain Laplacian contracts a closed solid on every pass;
    on a figurine that is lost millimetres and lost silhouette. Taubin alternates a positive
    shrinking step (lamb) with a negative inflating one (nu), which low-passes the surface
    instead of shrinking it.

    MEASURED, suit_male at 60 iterations, against the unsmoothed repair:
        volume       100.03%          watertight   still true
        surface moved  mean 0.024 mm, p99 0.085 mm, max 0.117 mm   (mesh-to-mesh)
        cost         under a second
    JUDGED at 560 px: the staircase is gone, and the clasped hands, individual fingers,
    jacket vent, sleeve folds and pocket flaps are all still there. 0.117 mm of worst-case
    movement is a quarter of an FDM extrusion width.

    RUN BEFORE THE CUT AND THE BORE, never after: smoothing a bored socket would round its
    walls and dome its flat seating face, which is the one surface on the part that has to
    stay flat.
    """
    import trimesh
    n = GEOM["taubin_iters"] if iterations is None else iterations
    m = trimesh.load(src, force="mesh", process=True)
    before = float(m.volume)
    if n > 0:
        trimesh.smoothing.filter_taubin(m, lamb=0.5, nu=0.53, iterations=int(n))
    dst = os.path.join(d, out_name)
    trimesh.exchange.export.export_mesh(m, dst)
    return dst, {"taubin_iters": int(n),
                 "volume_kept_pct": round(100.0 * m.volume / before, 3) if before else None,
                 "watertight_after": bool(m.is_watertight)}


def ensure_solid(mesh):
    """Make a mesh a closed volume again after an operation that nearly kept it one.

    *** THE DEFECTS THIS CLEANS ARE TINY AND THEY BREAK EVERYTHING DOWNSTREAM. ***
    MEASURED on the astronaut: `mesh_doctor scale` took a watertight Poisson solid and
    returned it with FOUR two-face shells and three boundary edges. Three edges out of ten
    million. But `is_volume` is then False, `trimesh.boolean` refuses with "Not all meshes
    are volumes!", and the socket bore fails - so the whole item fails, on a mesh that is
    99.9999% fine.

    Cleaning is cheap and the failure is not, so this runs after every step that rewrites
    the geometry: keep the largest shell, weld, drop degenerate faces, fan whatever
    boundary loops remain, and fix the winding. MEASURED on that astronaut: watertight and
    a volume again, 3,562,151 -> 3,562,154 faces. Three faces.
    """
    import networkx as nx
    import numpy as np
    import trimesh
    m = mesh
    parts = m.split(only_watertight=False)
    if len(parts) > 1:
        m = max(parts, key=lambda q: len(q.faces))
    m.merge_vertices()
    m.update_faces(m.nondegenerate_faces())
    m.update_faces(m.unique_faces())
    m.remove_unreferenced_vertices()

    for _ in range(3):
        bi = trimesh.grouping.group_rows(m.edges_sorted, require_count=1)
        if not len(bi):
            break
        be = m.edges_sorted[bi]
        g = nx.Graph()
        g.add_edges_from(be)
        comps = list(nx.connected_components(g))
        v = np.asarray(m.vertices, dtype=np.float64)
        f = list(np.asarray(m.faces))
        apex, newv = {}, []
        for k, c in enumerate(comps):
            apex[k] = len(v) + len(newv)
            newv.append(v[list(c)].mean(axis=0))
        v = np.vstack([v, np.array(newv)])
        owner = {n: k for k, c in enumerate(comps) for n in c}
        for a, b in be:
            f.append([a, b, apex[owner[a]]])
        m = trimesh.Trimesh(vertices=v, faces=np.array(f), process=True)
        parts = m.split(only_watertight=False)
        if len(parts) > 1:
            m = max(parts, key=lambda q: len(q.faces))
    trimesh.repair.fix_winding(m)
    trimesh.repair.fix_normals(m)
    return m


def stage_decimate(d, src, part, out_name="decimated.glb"):
    """Quadric-decimate the smoothed solid back to a sane file size.

    THIS IS WHY THE REPAIR GRID CAN BE FINE. MEASURED on suit_male: decimating
    voxel1200 + taubin20 from 4,695,510 faces to 800,000 left the mean distance from the
    RAW mesh at 0.0678 mm - unchanged to four decimal places. Face count and fidelity are
    independent once the geometry is banked, so paying for the size saving with a coarse
    grid, as the old path did, was buying nothing.

    *** DECIMATION IS NOT RELIABLE AND IS THEREFORE CHECKED, NOT TRUSTED. ***
    MEASURED across the same sweep: voxel1200 + taubin20 decimates to 800k and stays
    watertight with zero non-manifold edges, while voxel900 + taubin25 and + taubin40
    decimate to the same target and come back NOT watertight. It is a property of the
    particular mesh, not of the target. An earlier attempt on an unsmoothed coarse mesh
    failed at every target, which is why this was written off once already.

    So the result is verified and the undecimated mesh is kept when it fails. A smaller
    file is worth having; it is not worth shipping a part a slicer will argue with.
    """
    import numpy as np
    import trimesh
    target = TARGET_FACES.get(part)
    m = trimesh.load(src, force="mesh", process=True)
    n0 = len(m.faces)
    if not target or n0 <= target * 1.1:
        return src, {"decimated": False, "faces": n0, "why": "already at or under target"}

    # *** SCALE FIRST. QUADRIC ERROR IS QUADRATIC IN THE COORDINATES. ***
    # The same mesh and the same target decimates cleanly at 147 units across and comes
    # back NOT watertight at 2 units across, which is the size Hunyuan3D output arrives in.
    # That is a conditioning problem in the error metric, not a property of the mesh - and
    # it is why the standalone test passed while the first wiring into the pipeline failed:
    # the test had scaled to millimetres first and the pipeline had not.
    span = float(m.extents[int(np.argmax(m.extents))]) or 1.0
    k = 150.0 / span
    m.apply_scale(k)

    def _clean(s):
        s.merge_vertices()
        s.update_faces(s.nondegenerate_faces())
        s.update_faces(s.unique_faces())
        s.remove_unreferenced_vertices()
        return s

    def _good(s):
        return s.is_watertight and len(s.split(only_watertight=False)) == 1

    # *** DECIMATE PROGRESSIVELY, NOT IN ONE JUMP. MEASURED, AND IT WAS AN 18/24 FAILURE. ***
    #
    # Asked for the target in a single pass, quadric decimation collapses edges in error
    # order and, on a mesh with thin features, leaves non-manifold configurations behind.
    # MEASURED across the library at a 1200 grid: one-shot reached the target on 6 of 24
    # bodies and the other 18 kept their full 4-7 MILLION face meshes, which is a 250 MB STL.
    #
    # Halving is a gentler ask and each step is checked, so a mesh that cannot reach the
    # target still gets most of the way rather than staying where it started. Two refinements
    # on top, both of which earned their place - plain halving still stalled astronaut at
    # 3.29M and pirate at 3.02M:
    #
    #   ADAPTIVE STEP  a failed halving is not the end. Try 0.65, then 0.82, before stopping.
    #   DEBRIS RESCUE  decimation sometimes sheds a speck shell rather than breaking the
    #                  surface. That is repairable: keep the largest shell and re-check.
    #
    # MEASURED with both: astronaut 7,305,594 -> 800,000, pirate 6,722,168 -> 800,000,
    # suit_male 4,710,846 -> 800,000, every one watertight, 8-19 s.
    cur = m
    steps = []
    while len(cur.faces) > target * 1.05:
        moved = False
        for frac in (0.45, 0.65, 0.82):
            nxt = max(int(target), int(len(cur.faces) * frac))
            if nxt >= len(cur.faces):
                continue
            try:
                s = _clean(cur.copy().simplify_quadric_decimation(face_count=nxt))
            except Exception:                                         # noqa: BLE001
                continue
            if not _good(s):
                # The rescue used to be a debris strip only. MEASURED on the Poisson
                # meshes, three items - astronaut, pilot and stand_in - failed EVERY
                # decimation step and kept 2.8-4.8M faces (a 53 MB 3MF) because what
                # decimation left behind was a handful of boundary edges rather than a
                # stray shell. ensure_solid handles both, and it is the same helper that
                # rescued the astronaut after mesh_doctor's scale.
                try:
                    s = _clean(ensure_solid(s))
                except Exception:                                     # noqa: BLE001
                    continue
                if not _good(s):
                    continue
            cur, moved = s, True
            steps.append(len(cur.faces))
            break
        if not moved:
            break

    if len(cur.faces) >= n0:
        return src, {"decimated": False, "faces": n0,
                     "why": "no decimation step held watertight - kept the full mesh"}
    cur.apply_scale(1.0 / k)                          # back to the units it arrived in
    dst = os.path.join(d, out_name)
    trimesh.exchange.export.export_mesh(cur, dst)
    return dst, {"decimated": True, "faces_before": n0, "faces": len(cur.faces),
                 "target": int(target), "steps": steps,
                 "reached_target": len(cur.faces) <= target * 1.05}


def scale_to(d, src, height_mm, out_name="scaled.glb"):
    """Millimetres, Z up, sitting on z=0. Doing this BEFORE the cut is deliberate: every
    socket dimension below is in real millimetres, and the other order means boring an
    8.4 mm hole in a model that is two units tall."""
    dst = os.path.join(d, out_name)
    md("scale", src, "--height", height_mm, "--up", "y", "--out", dst)
    # mesh_doctor's scale has been MEASURED to return a watertight solid with a handful of
    # two-face shells and a few boundary edges. See ensure_solid for what that costs.
    import trimesh
    m = trimesh.load(dst, force="mesh", process=True)
    if not m.is_volume:
        m = ensure_solid(m)
        trimesh.exchange.export.export_mesh(m, dst)
    return dst


def _keep_largest(mesh, frac=0.01):
    """Drop shells under `frac` of the largest. The neck cut can shear off a chip of
    collar or a lock of hair, and mesh_doctor's own warning for that case is exact:
    'stray shells slice as floating debris'. Returns (mesh, dropped_face_counts)."""
    parts = mesh.split(only_watertight=False)
    if len(parts) <= 1:
        return mesh, []
    parts = sorted(parts, key=lambda p: -len(p.faces))
    keep, drop = [parts[0]], []
    for p in parts[1:]:
        (keep if len(p.faces) >= frac * len(parts[0].faces) else drop).append(p)
    if not drop:
        return mesh, []
    import trimesh
    out = keep[0] if len(keep) == 1 else trimesh.util.concatenate(keep)
    return out, [len(p.faces) for p in drop]


# ─── the mechanical part: neck plane and spring socket ──────────────────────────────

def _section_area(mesh, z):
    """Enclosed area of the horizontal cross-section at height z, in mm^2. Zero when the
    plane misses the mesh."""
    try:
        sec = mesh.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1])
        if sec is None:
            return 0.0, None
        p2, to3 = sec.to_2D()
        a = float(abs(p2.area))
        # the centroid of the biggest polygon, lifted back to 3D
        try:
            polys = p2.polygons_full
            big = max(polys, key=lambda q: q.area)
            c2 = big.centroid
            import numpy as np
            c3 = to3 @ np.array([c2.x, c2.y, 0.0, 1.0])
            return a, (float(c3[0]), float(c3[1]))
        except Exception:
            return a, None
    except Exception:
        return 0.0, None


def neck_plane(mesh, lo=0.40, hi=0.97, n=240,
               shoulder_lo=0.58, shoulder_hi=0.86, neck_lo=0.66, crown_hi=0.92):
    """Find the neck: the narrowest horizontal cross-section ABOVE THE SHOULDERS that
    still has a head above it.

    Returns (z, area_mm2, centre_xy, info). The 240-row profile is kept in `info` so the
    report and the page can show the curve that produced the decision rather than
    asserting the number.

    *** "ABOVE THE SHOULDERS" IS DOING THE WORK, AND THE FIRST VERSION LEFT IT OUT. ***

    v1 took the global minimum of the band and required only that something above it was
    1.35x wider - "there is a head up there". MEASURED across all 24 bodies, that is not
    enough, and the failure is legible in one column of `bobble.py report`:

        astronaut   joint 50.2 mm      cut through the chest of the suit
        sundress    joint 34.7 mm      cut through the shoulders
        pilot       joint 30.5 mm      cut low, at the collar line

    A bulky costume has no waist narrower than its own chest, so on the astronaut the
    global minimum of the band landed at the hips - and the chest and helmet above it
    passed the 1.35x test easily. The test was true and the answer was wrong.

    v2 finds the shoulders first. The widest section in the upper torso IS the shoulder
    line; the neck is the minimum above it. That is a statement about how a standing human
    figure is shaped, so it holds for a suit, a spacesuit and a ballgown alike, and it
    cannot select a waist because a waist is never above the shoulders.

    THE FOUR BANDS ARE RULES OF THUMB ABOUT HUMAN PROPORTION, and each earned its place:

      shoulder_lo 0.58  MEASURED: searching the shoulders from 0.40 found the KNIGHT's
                        tabard skirt instead of his pauldrons, so the neck search started
                        at the skirt and the "neck" came out at 0.624 - the waist, 50 mm
                        wide. A wide hem, a ballgown skirt or a firefighter's coat all do
                        this. Nothing below 0.58 of a standing figure is a shoulder.
      shoulder_hi 0.86  above every real shoulder and below every hat brim.
      neck_lo     0.66  a hard floor. No standing figure has its neck in the bottom two
                        thirds, so a candidate below this is a waist however prominent.
      crown_hi    0.92  a hard ceiling, so the top of a head can never be selected - not
                        even by the fallback, which is how v2 shipped six headed bodies.
    """
    zmin, zmax = float(mesh.bounds[0][2]), float(mesh.bounds[1][2])
    H = zmax - zmin
    prof = []
    for i in range(n):
        f = lo + (hi - lo) * i / (n - 1.0)
        z = zmin + f * H
        a, c = _section_area(mesh, z)
        prof.append({"f": round(f, 4), "z": round(z, 3), "area": round(a, 2), "c": c})
    real = [p for p in prof if p["area"] > 1.0]
    if not real:
        raise RuntimeError("no cross-section found in the neck band - is the mesh solid?")

    # The shoulder line, kept as a REPORTED DIAGNOSTIC only.
    #
    # An earlier version used it to gate the search - "the neck is the minimum above the
    # shoulders" - and that is true but unusable, because finding the shoulders is harder
    # than finding the neck. MEASURED both ways it fails at both ends: searching from 0.40
    # picks the KNIGHT's tabard skirt, and raising the floor to 0.58 to fix that lets the
    # PILOT's peaked cap and the NURSE's hair become "the shoulders", after which there is
    # nothing above them and the cut runs to the ceiling at 0.920. Three bodies kept their
    # heads that way.
    #
    # `neck_lo` already does the only job the shoulder gate was needed for - keeping the
    # search out of the waist - and it does it with a constant that cannot be fooled by a
    # hat. So the gate is gone and this number is printed rather than obeyed.
    torso = [p for p in real if shoulder_lo <= p["f"] <= shoulder_hi] or real
    shoulder = max(torso, key=lambda p: p["area"])

    # 2. the neck: the MOST PROMINENT constriction between the shoulders and the crown.
    #
    # *** v2 USED "NARROWEST WITH SOMETHING 1.35x WIDER ABOVE" AND IT REGRESSED SIX ***
    # *** BODIES. THIS IS v3 AND THE MEASUREMENT THAT KILLED v2 IS WORTH KEEPING.   ***
    #
    # MEASURED, astronaut, sections above the shoulder line of the suit:
    #
    #     f=0.743  2022      f=0.786  2168      f=0.858  1469
    #     f=0.758  2012 <-   f=0.801  2151      f=0.915  1195
    #     f=0.772  2097      f=0.829  1654      f=0.970   587
    #
    # The neck IS there, at 0.758. But the head above it is only 1.078x wider, because a
    # spacesuit's head is barely wider than its collar - so the 1.35x test rejected it,
    # every other section failed too, and the fallback took the narrowest section above
    # the shoulders. That is the CROWN, at f=0.970. Five other bodies did the same:
    # firefighter, knight, nurse_scrubs, pilot, wizard all cut at 0.970 and kept their
    # heads. A threshold tuned on a business suit does not survive a spacesuit.
    #
    # PROMINENCE has no such threshold to tune. For each candidate, take the smaller of
    # the two peaks flanking it - the widest section below within the band, and the widest
    # above - and divide by the candidate. A neck scores high because it has shoulders
    # below AND a head above; the crown scores ~1.0 because it has nothing above it; a
    # shoulder scores ~1.0 because it IS the peak. Taking the maximum needs no constant.
    #
    # The band stops at `crown_hi` so the top of a head can never be selected at all, not
    # even by the fallback. RULE OF THUMB: no figure's neck is in the top 8% of its height.
    band = [p for p in real if neck_lo <= p["f"] <= crown_hi]
    best, why, prom = None, "", 0.0
    for p in band:
        below = [q["area"] for q in real if q["z"] < p["z"]]
        higher = [q["area"] for q in band if q["z"] > p["z"]]
        if not below or not higher or p["area"] <= 0:
            continue
        s = min(max(below), max(higher)) / p["area"]
        if s > prom:
            best, prom = p, s
    if best is None or prom < 1.05:
        # No real constriction: a figure whose head sits straight on its torso. Take the
        # narrowest section in the band and SAY that is what happened, rather than
        # reporting a neck that was never found.
        best = min(band, key=lambda p: p["area"]) if band else \
            min(real, key=lambda p: p["area"])
        why = ("no constriction between the shoulder line and %d%% of height stood out "
               "from its neighbours - cut at the narrowest section in that band instead"
               % int(crown_hi * 100))
    if best is None:
        raise RuntimeError("no cross-section in the neck band - is the mesh a figure?")

    d_eq = 2.0 * math.sqrt(max(best["area"], 0.0) / math.pi)
    return best["z"], best["area"], (best.get("c") or (0.0, 0.0)), {
        "profile": prof, "neck_f": best["f"],
        "neck_area_mm2": round(best["area"], 2),
        "neck_equiv_diameter_mm": round(d_eq, 2),
        "neck_prominence": round(prom, 3),
        "shoulder_f": shoulder["f"],
        "shoulder_area_mm2": round(shoulder["area"], 2),
        "fallback": bool(why), "fallback_why": why,
    }


def _cyl(radius, height, z0, cx, cy, sections=64):
    import numpy as np
    import trimesh
    c = trimesh.creation.cylinder(radius=radius, height=height, sections=sections)
    c.apply_translation([cx, cy, z0 + height / 2.0])
    return c


def _socket_tool(d_mm, depth_mm, z_face, cx, cy, downward, chamfer):
    """The negative solid to subtract: a blind hole of d_mm x depth_mm starting at the
    flat face z_face and running into the part, plus a chamfered mouth.

    `downward` True bores from the face down into a body neck; False bores up into a
    head's underside."""
    import trimesh
    r = d_mm / 2.0
    sgn = -1.0 if downward else 1.0
    # A hair of overshoot past the face so the boolean makes a clean opening rather than
    # a coincident-face sliver, which is the classic way a CSG hole comes out capped.
    over = 0.6
    if downward:
        body = _cyl(r, depth_mm + over, z_face - depth_mm, cx, cy)
    else:
        body = _cyl(r, depth_mm + over, z_face - over, cx, cy)
    parts = [body]
    if chamfer > 0:
        cone = trimesh.creation.cone(radius=r + chamfer, height=chamfer, sections=64)
        # cone apex points +z with its base at z=0
        if downward:
            cone.apply_translation([cx, cy, z_face - chamfer])
        else:
            cone.apply_transform(trimesh.transformations.rotation_matrix(
                math.pi, [1, 0, 0]))
            cone.apply_translation([cx, cy, z_face + chamfer])
        parts.append(cone)
    return trimesh.util.concatenate(parts) if len(parts) > 1 else parts[0]


def stage_neck(d, scaled, target_mm, socket_d=None, socket_depth=None):
    """Cut the head off at the neck, rescale the body to its target height, drop debris,
    then bore the spring socket.

    THE ORDER MATTERS AND THE FIRST VERSION HAD IT WRONG. Scaling the whole figure to
    110 mm and then removing the head leaves a body 83.8 mm tall while the record still
    claims 110 - the number a person reads off the library and slices to. The body is
    therefore rescaled to `target_mm` after the cut, and only then is the socket bored,
    so 8.4 mm means 8.4 mm on the part that gets printed.

    Writes body.glb (what you print) and head_offcut.glb (what came off, kept so the cut
    can be judged by looking rather than by trusting the number)."""
    import trimesh
    m = trimesh.load(scaled, force="mesh", process=True)
    socket_d = GEOM["socket_d"] if socket_d is None else socket_d
    socket_depth = GEOM["socket_depth"] if socket_depth is None else socket_depth

    z, area, (cx, cy), info = neck_plane(m)

    lower = trimesh.intersections.slice_mesh_plane(
        m, plane_normal=[0, 0, -1], plane_origin=[0, 0, z], cap=True)
    upper = trimesh.intersections.slice_mesh_plane(
        m, plane_normal=[0, 0, 1], plane_origin=[0, 0, z], cap=True)
    if lower is None or lower.is_empty:
        raise RuntimeError("the neck cut removed everything")
    trimesh.exchange.export.export_mesh(upper, os.path.join(d, "head_offcut.glb"))

    cut_h = float(lower.bounds[1][2] - lower.bounds[0][2])
    k = float(target_mm) / cut_h
    lower.apply_scale(k)
    lower.apply_translation([0, 0, -float(lower.bounds[0][2])])
    cx, cy = cx * k, cy * k
    neck_d = info["neck_equiv_diameter_mm"] * k

    # The socket must fit inside the neck with wall left over. If the neck is narrower
    # than the spring plus 2.4 mm of wall, shrink the socket and record that we did -
    # silently boring a hole wider than the neck is how a part arrives hollow.
    want = socket_d
    max_d = max(neck_d - 2.4, 3.0)
    if want > max_d:
        socket_d = round(max_d, 2)
    tool = _socket_tool(socket_d, socket_depth, float(target_mm), cx, cy, True,
                        GEOM["mouth_chamfer"])
    try:
        bored = trimesh.boolean.difference([lower, tool], engine="manifold")
    except Exception:
        bored = trimesh.boolean.difference([lower, tool])
    if bored is None or bored.is_empty:
        raise RuntimeError("boring the socket emptied the mesh")

    # AFTER the boolean, not before. The first version stripped debris off `lower` and
    # still shipped a 128-face island: the shell is produced BY the CSG, not inherited
    # from the cut, so stripping upstream of it cleans a mesh that is about to be dirtied
    # again. mesh_doctor's warning ("stray shells slice as floating debris") is what
    # caught it.
    bored, dropped = _keep_largest(bored)

    out = os.path.join(d, "body.glb")
    trimesh.exchange.export.export_mesh(bored, out)
    info.update({
        "cut_at_mm": round(z, 2), "full_figure_mm": round(float(m.extents[2]), 2),
        "rescaled_by": round(k, 4),
        "neck_centre": [round(cx, 2), round(cy, 2)],
        "neck_diameter_mm": round(neck_d, 2),
        "socket_d_mm": socket_d, "socket_depth_mm": socket_depth,
        "socket_reduced": want != socket_d, "socket_wanted_mm": want,
        "debris_dropped": dropped,
        "body_watertight": bool(bored.is_watertight),
        "body_extents_mm": [round(float(x), 2) for x in bored.extents],
    })
    return out, info


def stage_head_socket(d, scaled, target_mm, socket_d=None, depth=None):
    """A supersized head, flattened underneath and bored for the same spring.

    The flat is cut at the lowest height whose cross-section is at least 55% of the
    widest section below the mid-line - i.e. just under the jaw/neck - so the head sits
    on a real face rather than balancing on a chin."""
    import trimesh
    m = trimesh.load(scaled, force="mesh", process=True)
    socket_d = GEOM["socket_d"] if socket_d is None else socket_d
    depth = GEOM["head_socket_depth"] if depth is None else depth

    zmin, zmax = float(m.bounds[0][2]), float(m.bounds[1][2])
    H = zmax - zmin
    prof = []
    for i in range(220):
        f = 0.02 + 0.68 * i / 219.0
        za = zmin + f * H
        a, c = _section_area(m, za)
        prof.append({"f": round(f, 4), "z": round(za, 3), "area": round(a, 2), "c": c})
    real = [p for p in prof if p["area"] > 1.0]
    if not real:
        raise RuntimeError("no cross-section under the head's mid-line")

    # *** HUNYUAN3D INVENTS SHOULDERS, AND THE FIRST RULE HERE MEASURED AGAINST THEM. ***
    #
    # MEASURED on the `pickle` head. The figurine pass did exactly what it was asked -
    # source_styled.png is a head and the top of a neck, no shoulders, on a flat plate -
    # and the MESH came back a full bust with shoulders and an upper chest. A bust is a
    # very common 3D subject and the model has a strong prior for one; given a floating
    # head it supplies the body the head is usually attached to.
    #
    # v1 cut at "the lowest section that is at least 55% of the widest section below the
    # mid-line". On a bust the widest section below the mid-line IS the shoulders, so 55%
    # of that is still down in the chest, and the part came out 95 mm of mostly shoulder
    # with a small head on top. Which is not a bobblehead.
    #
    # v2 looks for the NECK, using the same prominence test as neck_plane and for the same
    # reason - a neck is a constriction with something wider below it and something wider
    # above it, and that is true whether the wider thing below is a pair of shoulders or a
    # whole body. It needs no threshold tuned to how much shoulder the model decided to add.
    #
    # If there is no prominent constriction - the model returned a head on a neck stub, the
    # thing that was actually asked for - there is no neck to find, and the old rule is
    # correct. So it stays as the fallback, and the record says which one fired.
    best, prom = None, 0.0
    for p in real:
        below = [q["area"] for q in real if q["z"] < p["z"]]
        above = [q["area"] for q in prof if q["area"] > 1.0 and q["z"] > p["z"]]
        if not below or not above or p["area"] <= 0:
            continue
        s = min(max(below), max(above)) / p["area"]
        if s > prom:
            best, prom = p, s
    if best is not None and prom >= 1.12:
        cut, how = best, "neck found by prominence (%.2f) - shoulders removed" % prom
    else:
        widest = max(p["area"] for p in real)
        cut = next((p for p in real if p["area"] >= 0.55 * widest), real[-1])
        how = ("no neck constriction - the mesh is a head on a stub, cut at the first "
               "section reaching 55% of the widest below the mid-line")

    kept = trimesh.intersections.slice_mesh_plane(
        m, plane_normal=[0, 0, 1], plane_origin=[0, 0, cut["z"]], cap=True)
    if kept is None or kept.is_empty:
        raise RuntimeError("flattening the head removed everything")
    # Rescale so `target_mm` is the height of the HEAD, not of the head plus the neck that
    # was just cut away - the same correction stage_neck carries, and for the same reason:
    # the number in the record is the number somebody slices to.
    cut_h = float(kept.bounds[1][2] - kept.bounds[0][2])
    k = float(target_mm) / cut_h
    kept.apply_scale(k)
    kept.apply_translation([0, 0, -float(kept.bounds[0][2])])   # back onto the plate

    face_d = 2.0 * math.sqrt(max(cut["area"], 0.0) / math.pi) * k
    max_d = max(face_d - 3.0, 3.0)
    want = socket_d
    if socket_d > max_d:
        socket_d = round(max_d, 2)
    cx, cy = cut.get("c") or (0.0, 0.0)
    cx, cy = cx * k, cy * k
    tool = _socket_tool(socket_d, depth, 0.0, cx, cy, False, GEOM["mouth_chamfer"])
    try:
        bored = trimesh.boolean.difference([kept, tool], engine="manifold")
    except Exception:
        bored = trimesh.boolean.difference([kept, tool])
    if bored is None or bored.is_empty:
        raise RuntimeError("boring the head socket emptied the mesh")
    bored, dropped = _keep_largest(bored)     # after the CSG - see stage_neck

    out = os.path.join(d, "head.glb")
    trimesh.exchange.export.export_mesh(bored, out)
    return out, {"flat_f": cut["f"], "flat_area_mm2": round(cut["area"] * k * k, 2),
                 "flat_equiv_diameter_mm": round(face_d, 2),
                 "cut_rule": how, "cut_prominence": round(prom, 3),
                 "rescaled_by": round(k, 4),
                 "full_mesh_mm": round(float(m.extents[2]), 2),
                 "socket_d_mm": socket_d, "socket_depth_mm": depth,
                 "socket_reduced": want != socket_d, "debris_dropped": dropped,
                 "head_watertight": bool(bored.is_watertight),
                 "head_extents_mm": [round(float(x), 2) for x in bored.extents]}


def stage_print(d, mesh, name, height=None):
    """STL and 3MF. 3MF is what Bambu Studio should get - it carries units, so the model
    arrives at the size meant rather than at whatever the slicer assumes."""
    pd = os.path.join(d, "print")
    os.makedirs(pd, exist_ok=True)
    stl = os.path.join(pd, "%s.stl" % name)
    tmf = os.path.join(pd, "%s.3mf" % name)
    extra = ["--up", "none", "--out", stl, "--out", tmf, "--force"]
    if height:
        extra = ["--height", str(height)] + extra
    r = md("export", mesh, *extra)
    return {"stl": stl, "3mf": tmf, "export": r}


def stage_views(d, mesh, name, kind="body"):
    """The point-splat orbit strip, so the library shows the object rather than a
    filename. terra_mesh's rasteriser, not a second renderer.

    *** THE SAMPLE COUNT IS NOT COSMETIC. IT WAS MISREPRESENTING THE MESH. ***

    render_one samples a point cloud once and splats it. Too few points over too many
    pixels and the gaps between splats read as a fine, even grain that looks exactly like
    surface texture - and is not. MEASURED on one head, same mesh, same crop, sample count
    the only thing that moved:

        2.6M (render_one's default)  a uniform speckle over every surface
        10M                          largely clean; real hair strands legible
        40M                          clean; eyelids, brows and forehead read as surfaces

    Geometry cannot change with sample count, so all three are the same object. The first
    one simply lies about it, and it was what the library had been showing all along - so
    every judgement anybody made about "surface quality" from a library card was partly a
    judgement about this number.

    9M is a cost decision rather than a quality one. MEASURED at size 420 / 6 frames:
    2.6M takes 6-12 s, 9M takes 38 s, 16M takes 110-122 s. Two minutes an item is not worth
    the last of the grain across a 24-item library.

    THE CLOSE-UP IS DROPPED FOR HEADS. render_one also writes a `_head.jpg` by slicing the
    top 26% of the mesh and giving it the whole sample budget. On a body that is the head,
    which is the point. On a head it is the top of the scalp - and it was being shown on
    the card next to the orbit as though it meant something.
    """
    import terra_mesh
    vd = os.path.join(d, "views")
    os.makedirs(vd, exist_ok=True)
    try:
        terra_mesh.render_one(mesh, name, vd, size=420, frames=6, ss=2, up="z",
                              samples=RENDER_SAMPLES)
    except TypeError:
        terra_mesh.render_one(mesh, name, vd, size=420, frames=6, ss=2)
    if kind == "head":
        scalp = os.path.join(vd, "%s_head.jpg" % name)
        if os.path.isfile(scalp):
            os.remove(scalp)
    hits = sorted(glob.glob(os.path.join(vd, "%s*" % name)))
    return [os.path.relpath(h, d) for h in hits]


# ─── whole items ────────────────────────────────────────────────────────────────────

def _rec_path(spec):
    return os.path.join(BODIES, spec["id"], "body.json")


def _load_rec(spec, seed=None, height=None):
    """The record is the item's state, on disk. A phase reads it, does its stage, and
    writes it back - so an interrupted batch resumes at the phase it reached rather than
    regenerating a mesh that already exists."""
    jp = _rec_path(spec)
    if os.path.exists(jp):
        try:
            r = json.load(open(jp, encoding="utf-8"))
            r["spec"] = spec
            if seed:
                r["seed"] = seed
            if height:
                r["height_mm"] = height
            return r
        except Exception:
            pass
    return {"id": spec["id"], "kind": "body", "spec": spec, "recipe": dict(RECIPE),
            "seed": seed or spec.get("seed") or 777,
            "height_mm": height or GEOM["body_mm"], "stages": {}, "phases": {},
            "built": time.time()}


def _save_rec(rec):
    d = os.path.join(BODIES, rec["id"])
    os.makedirs(d, exist_ok=True)
    json.dump(rec, open(os.path.join(d, "body.json"), "w", encoding="utf-8"), indent=1)
    return rec


def _phase(rec, name, fn, redo=False):
    """Run one phase, record that it ran, and record honestly if it did not."""
    d = os.path.join(BODIES, rec["id"])
    os.makedirs(d, exist_ok=True)
    ph = rec.setdefault("phases", {})
    if ph.get(name) == "ok" and not redo:
        return True
    t0 = time.time()
    try:
        fn(d, rec)
        ph[name] = "ok"
        rec.setdefault("secs", {})[name] = round(time.time() - t0, 1)
        rec.pop("error", None)
        rec.pop("trace", None)
    except Exception as e:                                          # noqa: BLE001
        import traceback
        ph[name] = "failed"
        rec["ok"] = False
        rec["error"] = "%s in %s: %s" % (type(e).__name__, name, e)
        rec["trace"] = traceback.format_exc()[-1500:]
        log("%s FAILED at %s: %s" % (rec["id"], name, e))
        _save_rec(rec)
        return False
    _save_rec(rec)
    return True


def phase_seed(d, rec):
    """Qwen + BiRefNet. Batched across the whole catalogue so the image weights load
    once rather than once per body."""
    log("%s: seed image" % rec["id"])
    stage_source(d, rec["spec"], rec["seed"])
    log("%s: matte and square" % rec["id"])
    _, minfo = stage_matte(d)
    rec["stages"]["matte"] = minfo


def phase_mesh(d, rec):
    """Hunyuan3D. free_models() runs inside stage_mesh, so this phase is safe to enter
    straight after a seed phase."""
    log("%s: Hunyuan3D" % rec["id"])
    sq = os.path.join(d, "source_square.png")
    _, ginfo = stage_mesh(d, sq, rec["seed"], tag="body_%s" % rec["id"])
    rec["stages"]["mesh"] = ginfo


def phase_finish(d, rec):
    """Repair, scale, cut, bore, export, render. No GPU and no ComfyUI - this phase can
    run while the next batch is meshing."""
    proc = rec.get("process", "fdm")
    nominal = rec["height_mm"] / NECK_FRACTION_GUESS
    log("%s: repair" % rec["id"])
    solid, vr = stage_solid(d, "body", nominal, proc)
    rec["recipe"]["voxel_res"] = vr
    rec["recipe"]["process"] = proc
    smooth, sminfo = stage_smooth(d, solid)
    rec["stages"]["smooth"] = sminfo
    thin, dcinfo = stage_decimate(d, smooth, "body")
    rec["stages"]["decimate"] = dcinfo
    scaled = scale_to(d, thin, nominal)
    log("%s: neck cut and socket" % rec["id"])
    body, ninfo = stage_neck(d, scaled, rec["height_mm"])
    rec["stages"]["neck"] = ninfo
    rec["diagnose"] = md("diagnose", body)
    rec["stages"]["print"] = stage_print(
        d, body, "%s_%dmm" % (rec["id"], int(rec["height_mm"])))
    rec["views"] = stage_views(d, body, rec["id"], kind="body")
    rec["ok"] = True


def build_body(spec, seed=None, height=None, redo=False):
    """One body, all three phases. `fill` runs the same phases across the catalogue."""
    rec = _load_rec(spec, seed, height)
    if redo:
        rec["phases"] = {}
    t0 = time.time()
    for name, fn in (("seed", phase_seed), ("mesh", phase_mesh),
                     ("finish", phase_finish)):
        if not _phase(rec, name, fn, redo=redo):
            return rec
    rec["wall_secs"] = round(time.time() - t0, 1)
    return _save_rec(rec)


def build_head(photo, hid=None, height=None, redo=False, style="figurine",
               name=None, from_raw=False):
    hid = hid or os.path.splitext(os.path.basename(photo))[0].lower()
    hid = "".join(c if c.isalnum() or c in "._-" else "_" for c in hid)
    d = os.path.join(HEADS, hid)
    os.makedirs(d, exist_ok=True)
    rec = {"id": hid, "kind": "head", "source_photo": os.path.basename(photo),
           "spec": {"name": name or hid.replace("_", " ").title(), "group": "head",
                    "subject": "from a photograph", "costume": "", "pose": ""},
           "recipe": dict(RECIPE), "seed": 777, "style": style,
           "height_mm": height or GEOM["head_mm"], "stages": {}, "built": time.time()}
    jp = os.path.join(d, "head.json")
    if os.path.exists(jp) and not redo:
        try:
            old = json.load(open(jp, encoding="utf-8"))
            if old.get("ok"):
                return old
        except Exception:
            pass
    t0 = time.time()
    try:
        # Rebuilding from the item's OWN source.png is a normal thing to want - it is how
        # you re-run a head after a pipeline change without going back to the upload - and
        # shutil.copy raises SameFileError on it. That killed a rebuild that had nothing
        # else wrong with it, and wrote ok:false over a head that was fine.
        src = os.path.join(d, "source.png")
        if os.path.abspath(photo) != os.path.abspath(src):
            shutil.copy(photo, src)
        # --from-raw skips everything that needs ComfyUI. Re-running a head after a change
        # to the REPAIR is the common case, and re-generating a figurine pass and a mesh
        # that are already on disk costs two GPU minutes and risks the OOM that killed the
        # last batch - the Poisson solve and ComfyUI's cached weights do not fit together.
        if from_raw and os.path.isfile(os.path.join(d, "raw.glb")):
            log("%s: reusing raw.glb - skipping the figurine pass and the mesh" % hid)
        elif style == "figurine":
            log("%s: figurine pass" % hid)
            src = stage_stylize(d, src)
        if not (from_raw and os.path.isfile(os.path.join(d, "raw.glb"))):
            log("%s: matte and square" % hid)
            sq, minfo = stage_matte(d, src)
            rec["stages"]["matte"] = minfo
            log("%s: Hunyuan3D" % hid)
            _, ginfo = stage_mesh(d, sq, rec["seed"], tag="head_%s" % hid)
            rec["stages"]["mesh"] = ginfo
        log("%s: repair" % hid)
        solid, vr = stage_solid(d, "head", rec["height_mm"],
                                rec.get("process", "fdm"))
        rec["recipe"]["voxel_res"] = vr
        smooth, sminfo = stage_smooth(d, solid)
        rec["stages"]["smooth"] = sminfo
        thin, dcinfo = stage_decimate(d, smooth, "head")
        rec["stages"]["decimate"] = dcinfo
        scaled = scale_to(d, thin, rec["height_mm"])
        log("%s: flat and socket" % hid)
        head, sinfo = stage_head_socket(d, scaled, rec["height_mm"])
        rec["stages"]["socket"] = sinfo
        rec["diagnose"] = md("diagnose", head)
        rec["stages"]["print"] = stage_print(d, head, "%s_%dmm"
                                             % (hid, int(rec["height_mm"])))
        rec["views"] = stage_views(d, head, hid, kind="head")
        rec["ok"] = True
    except Exception as e:                                          # noqa: BLE001
        import traceback
        rec["ok"] = False
        rec["error"] = "%s: %s" % (type(e).__name__, e)
        rec["trace"] = traceback.format_exc()[-1500:]
        log("%s FAILED: %s" % (hid, rec["error"]))
    rec["wall_secs"] = round(time.time() - t0, 1)
    json.dump(rec, open(jp, "w", encoding="utf-8"), indent=1)
    return rec




# ═══ FIGURES: one photo of a person, split into a matched head and body ═════════════
#
# A BODY comes from a generated seed and its head is thrown away. A HEAD comes from a photo
# and its body never existed. A FIGURE is the third thing: one photograph of a whole person,
# meshed ONCE, and cut into the two halves of a bobblehead that were always meant to fit.
#
# Meshing once rather than twice is the entire point. Two separate generations of the same
# person agree on nothing - not the neck width, not the shoulder line, not the style - so
# the joint between them is a guess. One mesh cut in half has ONE neck cross-section, and
# both sockets are bored into the same measurement.

# *** THE FIGURINE FRAMING WAS EATING THE LIKENESS. IT IS GONE. ***
#
# The first version opened with "Turn this into a full-length collectible vinyl figurine"
# and went on to ask for hair "as one solid closed mass with carved grooves" and skin
# "smoothed into continuous sculpted surfaces like painted resin".
#
# MEASURED, reading the original photograph and the result side by side at the same crop:
#
#   hair colour   mid-brown, sun-lightened        ->  near BLACK
#   hair shape    wavy, voluminous, falling       ->  straight, sleek, flat to the skull
#                 forward over both shoulders
#   face          narrow, defined cheekbones,     ->  rounder, fuller, every line removed
#                 nasolabial lines, small mouth
#
# None of that is drift. It is the prompt doing what it was told. "Turn this into a
# figurine" means idealise the face; "one solid closed mass" means straighten and darken;
# "smooth like painted resin" means delete the lines that make a face that person's face.
#
# *** AND NEGATION DID NOT SAVE IT - THE THIRD TIME THIS PROJECT HAS LEARNED THAT. ***
# A version pinning "keep her hair the same colour, do not darken it, do not lighten the
# ends, do not add highlights or an ombre" came back WITH A STRONG OMBRE. Same failure as
# the superhero's cape in section 3 and as terra_3d_source_v2's hair tags: a negative
# cannot remove what the framing puts there. The answer is never another clause. It is to
# delete the instruction causing it.
#
# So the pass no longer asks for a figurine. It asks for two things a photograph genuinely
# needs before it can be meshed - even lighting and no background - and says explicitly
# that nothing else may change. MEASURED on the same photo: hair colour, waves, parting,
# face shape and skin lines all survive.
#
# The resin-smoothing had no justification anyway. Hunyuan3D reconstructs a smooth surface
# from any photograph, and the Poisson repair smooths it again. Pre-smoothing the IMAGE
# bought the mesh nothing and cost the likeness everything.

FIGURE_PRESERVE = (
    "Keep this photograph of this exact person completely unchanged except for the "
    "lighting and the background. PRESERVE THE PERSON EXACTLY. Keep her hair the colour it "
    "already is. Keep the exact parting, the exact waves and the exact way the hair falls "
    "around the face and over the shoulders. Keep the exact face shape, jawline, "
    "cheekbones, eyes, eyebrows, nose and mouth, and the natural lines and texture of the "
    "skin. The person must remain recognisably the same individual. Do not restyle "
    "anything. Only: replace the background with flat plain light grey, and even out the "
    "lighting so there are no cast shadows and no hard shadows.")

# Added ONLY when stage_detect_crop says the photograph is cut off. Asking a complete
# photograph to "show the complete figure" is an invitation to redraw it, and redrawing is
# exactly what costs the likeness.
FIGURE_COMPLETE = (
    " The photograph is cut off. Extend it so the COMPLETE figure is visible from the top "
    "of the head to the feet, standing, with clear margin above and below. Invent only the "
    "parts that are missing from the frame and keep everything already visible exactly as "
    "it is.")

# Also conditional: a body needs a flat base, but a photo of someone standing on a pavement
# already has feet on a plane and does not need to be told about a plinth.
FIGURE_PLINTH = (" Place the feet together on a small round plinth.")


def stage_figure_style(d, src, seed=777, out_name="styled.png",
                      complete=False, plinth=True):
    """Prepare a photograph for meshing WITHOUT restyling the person.

    Two things a photo genuinely needs: even lighting, because Hunyuan3D sculpts what it
    sees and a hard shadow becomes a groove, and no background. Everything else the earlier
    version asked for - figurine framing, closed hair, resin skin - was destroying the
    likeness for no downstream benefit. See FIGURE_PRESERVE.

    `complete` and `plinth` add a clause each, and both are OPT-IN because an unnecessary
    instruction is an invitation to redraw.
    """
    run, set_path, load_wf, ensure_local, HOST, COMFY = _comfy()
    staged = "bobble_fig_%d.png" % (int(time.time() * 1000) % 10 ** 8)
    shutil.copy(src, os.path.join(COMFY, "input", staged))
    wf = load_wf("22_qwen_edit_2511.json")
    set_path(wf, "7.inputs.image", staged)
    prompt = FIGURE_PRESERVE + (FIGURE_COMPLETE if complete else "") \
        + (FIGURE_PLINTH if plinth else "")
    set_path(wf, "10.inputs.prompt", prompt)
    set_path(wf, "12.inputs.prompt", "")
    set_path(wf, "15.inputs.seed", int(seed))
    set_path(wf, "17.inputs.filename_prefix", "claude-generated/bobble/figure_styled")
    _, outs = run(HOST, wf, quiet=True)
    if not outs:
        raise RuntimeError("the figurine pass produced no output")
    dst = os.path.join(d, out_name)
    if os.path.exists(dst):
        os.remove(dst)
    ensure_local(outs[0], dst)
    return dst


def _face_centre(mesh, z, fallback=(0.0, 0.0)):
    """Centroid of the largest cross-section at height z, for placing a socket."""
    _a, c = _section_area(mesh, z)
    return c or fallback


def stage_figure_split(d, scaled, body_mm, head_mm,
                       socket_d=None, body_depth=None, head_depth=None):
    """Cut one figure at the neck and socket BOTH halves.

    The neck comes from `neck_plane` - the same finder the body path uses, not a second
    one. What is new is that the UPPER half is kept and turned into a head instead of being
    written out as evidence and forgotten.

    The head needs no flat-finding of its own: the cut face IS its flat, already capped by
    the slice and already perpendicular to Z. It is dropped onto z=0, scaled to its own
    target height, and bored upward from the centre of that face.

    *** ONE DIAMETER, DECIDED ONCE, FOR BOTH SOCKETS. ***
    Each half has its own limit - the body needs 2.4 mm of wall around the neck, the head
    needs 3.0 mm around its seating face - and clamping them independently is how you get a
    body bored at 8.4 and a head bored at 6.0, which no single spring fits. The two limits
    are computed, the SMALLER wins, and both halves are bored to it.
    """
    import trimesh
    socket_d = GEOM["socket_d"] if socket_d is None else socket_d
    body_depth = GEOM["socket_depth"] if body_depth is None else body_depth
    head_depth = GEOM["head_socket_depth"] if head_depth is None else head_depth

    m = trimesh.load(scaled, force="mesh", process=True)
    z, area, (cx, cy), info = neck_plane(m)

    lower = trimesh.intersections.slice_mesh_plane(
        m, plane_normal=[0, 0, -1], plane_origin=[0, 0, z], cap=True)
    upper = trimesh.intersections.slice_mesh_plane(
        m, plane_normal=[0, 0, 1], plane_origin=[0, 0, z], cap=True)
    if lower is None or lower.is_empty or upper is None or upper.is_empty:
        raise RuntimeError("the neck cut did not produce two halves")

    # scale each half to its own target first, so every millimetre below is real
    hb = float(lower.bounds[1][2] - lower.bounds[0][2])
    kb = float(body_mm) / hb
    lower.apply_scale(kb)
    lower.apply_translation([0, 0, -float(lower.bounds[0][2])])
    lower = ensure_solid(lower)

    upper.apply_translation([0, 0, -float(upper.bounds[0][2])])
    kh = float(head_mm) / float(upper.bounds[1][2])
    upper.apply_scale(kh)
    upper.apply_translation([0, 0, -float(upper.bounds[0][2])])
    upper = ensure_solid(upper)

    neck_d = info["neck_equiv_diameter_mm"] * kb           # on the body, in mm
    seat_d = info["neck_equiv_diameter_mm"] * kb * kh      # the same face, on the head
    fit = min(socket_d, max(neck_d - 2.4, 3.0), max(seat_d - 3.0, 3.0))

    def bore(mesh, z_face, centre, depth, downward):
        tool = _socket_tool(fit, depth, z_face, centre[0], centre[1], downward,
                            GEOM["mouth_chamfer"])
        try:
            r = trimesh.boolean.difference([mesh, tool], engine="manifold")
        except Exception:
            r = trimesh.boolean.difference([mesh, tool])
        if r is None or r.is_empty:
            raise RuntimeError("boring the socket emptied a half")
        return _keep_largest(r)

    b_top = float(lower.bounds[1][2])
    body, bdrop = bore(lower, b_top, _face_centre(lower, b_top - 0.4, (cx * kb, cy * kb)),
                       body_depth, True)
    head, hdrop = bore(upper, 0.0, _face_centre(upper, 0.4, (0.0, 0.0)),
                       head_depth, False)

    bp = os.path.join(d, "body.glb")
    hp = os.path.join(d, "head.glb")
    trimesh.exchange.export.export_mesh(body, bp)
    trimesh.exchange.export.export_mesh(head, hp)

    common = {"socket_d_mm": round(fit, 2), "socket_reduced": fit != socket_d,
              "socket_wanted_mm": socket_d, "cut_f": info["neck_f"],
              "neck_prominence": info.get("neck_prominence")}
    return ({"body": (bp, dict(common, socket_depth_mm=body_depth,
                               neck_diameter_mm=round(neck_d, 2),
                               debris_dropped=bdrop,
                               watertight=bool(body.is_watertight),
                               extents_mm=[round(float(x), 2) for x in body.extents])),
             "head": (hp, dict(common, socket_depth_mm=head_depth,
                               seat_diameter_mm=round(seat_d, 2),
                               debris_dropped=hdrop,
                               watertight=bool(head.is_watertight),
                               extents_mm=[round(float(x), 2) for x in head.extents]))},
            info)


def stage_detect_crop(d, src, out_name="source_matte.png"):
    """Is this photograph cut off, and where?

    *** COMPLETION ALREADY HAPPENS. WHAT WAS MISSING IS BEING TOLD. ***
    MEASURED: handed the same photograph cropped at mid-thigh, the figurine pass in
    stage_figure_style returned a COMPLETE standing figure - it invented the legs, the
    shoes and the plinth, and kept the jacket, the face and the pose. That is the feature
    working. It is also the model inventing a third of a person and saying nothing.

    So this runs first and reports. A subject whose matte touches an edge of the frame with
    real width is cut off there, and the record says which edges and how much - which turns
    "the legs look wrong" into "the legs were never in the photograph".

    It costs one BiRefNet pass on the ORIGINAL, before any styling, because after the
    styling the evidence is gone.
    """
    from PIL import Image
    import numpy as np
    import terra_mesh
    run, set_path, load_wf, ensure_local, HOST, COMFY = _comfy()
    staged = "bobble_crop_%d.png" % (int(time.time() * 1000) % 10 ** 8)
    shutil.copy(src, os.path.join(COMFY, "input", staged))
    im = Image.open(src)
    wf = load_wf("14_birefnet_matte.json")
    set_path(wf, "1.inputs.image", staged)
    set_path(wf, "8.inputs.width", im.width)
    set_path(wf, "8.inputs.height", im.height)
    set_path(wf, "10.inputs.filename_prefix", "claude-generated/bobble/crop/rgba")
    _, outs = run(HOST, wf, quiet=True)
    if not outs:
        raise RuntimeError("the crop matte produced no output")
    dst = os.path.join(d, out_name)
    if os.path.exists(dst):
        os.remove(dst)
    pick = next((o for o in outs if "rgba" in str(o).lower()), outs[0])
    ensure_local(pick, dst)

    a = np.asarray(Image.open(dst).convert("RGBA").getchannel("A")) > 24
    if not a.any():
        return {"detected": False, "why": "the matte came back empty"}
    h, w = a.shape
    # a subject is "cut off" at an edge when it occupies a real span of that edge, not a
    # stray pixel or two of matte noise
    edges = {"bottom": a[-1, :].mean(), "top": a[0, :].mean(),
             "left": a[:, 0].mean(), "right": a[:, -1].mean()}
    cut = sorted([(k, round(float(v), 3)) for k, v in edges.items() if v > 0.06],
                 key=lambda kv: -kv[1])
    box = terra_mesh.alpha_bbox(Image.open(dst).convert("RGBA"))
    aspect = (box[3] - box[1]) / max(box[2] - box[0], 1) if box else None
    return {"detected": True, "cut_edges": cut,
            "subject_aspect_h_over_w": round(float(aspect), 2) if aspect else None,
            "is_cropped": bool(cut),
            "note": ("cut off at: %s - the figurine pass will invent what is missing"
                     % ", ".join("%s (%.0f%% of that edge)" % (k, v * 100)
                                 for k, v in cut)) if cut
            else "the whole subject is inside the frame"}


def stage_figure_head_crop(d, neck_f, out_name="head_crop.png"):
    """Crop the styled figure to its head, using the neck the MESH found.

    *** WHY THE HEAD IS MESHED TWICE AND THE BODY IS NOT. ***
    MEASURED on the first figure: meshing a whole standing person at octree 448 produced
    415k faces, and the head - about an eighth of the figure's height - came out of the cut
    with **49,002 of them**. The dedicated head path gives a head 768k. The face was
    visibly soft, and the face is the entire reason anyone wants their own bobblehead.

    Resolution is spent per-mesh, not per-object, so a head that shares a mesh with a pair
    of legs gets an eighth of the budget. Cropping to the head and meshing that crop on its
    own spends the whole budget on the part that carries the likeness.

    The crop comes from the MESH, not from a guess about where heads are. `neck_plane`
    already returned the neck as a fraction of figure height; the alpha box from the matte
    says where the figure sits in the picture. Between them the neck line is a pixel row.

    The BODY is not re-meshed: it keeps the figure mesh, so the neck cross-section that
    both sockets are sized from is still measured once, on one mesh.
    """
    from PIL import Image
    import terra_mesh
    rgba = Image.open(os.path.join(d, "source_rgba.png")).convert("RGBA")
    box = terra_mesh.alpha_bbox(rgba)
    if box is None:
        raise RuntimeError("the matte is empty - cannot locate the head")
    l, t, r, b = box
    h = b - t
    # image y grows downward; neck_f is measured up from the feet
    neck_y = int(round(b - neck_f * h))
    pad = int(round(h * 0.03))
    top = max(t - pad, 0)
    bot = min(neck_y + pad, rgba.height)
    band = rgba.crop((0, top, rgba.width, bot))
    bb = terra_mesh.alpha_bbox(band)
    if bb is None:
        raise RuntimeError("nothing above the neck line to crop")
    sq = terra_mesh.composite_square(band, PLATE_WHITE, 1024, box=bb, margin=0.08)
    dst = os.path.join(d, out_name)
    sq.save(dst)
    return dst, {"neck_row": neck_y, "crop_box": [int(x) for x in bb],
                 "figure_box": [int(x) for x in box]}


# ═══ POSES ══════════════════════════════════════════════════════════════════════════
#
# *** A POSE CHANGES THE BODY. IT DOES NOT CHANGE THE HEAD. ***
# That is not a simplification, it is what a bobblehead is: one head on a spring, and the
# head does not know what the body is doing. So a figure builds its head ONCE and then a
# body per pose, and every body is bored to the diameter the head was bored to. N poses
# cost N bodies, not N figures.
#
# MEASURED, and it is why there is no ControlNet here: asking `22_qwen_edit_2511` for a
# different pose in words held the identity on the first try - face, hairstyle, jacket,
# jeans, shoes, plinth, background and lighting all survived across arms-folded, fists-on-
# hips and a raised-arm wave, in 6-12 s each. The box also has sdpose and a qwen
# controlnet-union, which is the heavyweight route - detect a skeleton, edit it, regenerate
# conditioned on it - and it is three workflows instead of one. It is worth reaching for
# only if a pose the words cannot express turns up.

FIGURE_POSE_KEEP = (
    "Keep the same person, the same face, the same hairstyle and the same clothing "
    "exactly. Keep the flat plain light grey background, the even flat frontal lighting "
    "with no shadows, and the small round plinth. Full length, head to feet, standing.")

FIGURE_POSES = {
    "arms_down": {
        "say": "the figure stands with both arms relaxed at the sides",
        "print": "safe - nothing projects"},
    "arms_crossed": {
        "say": "the figure stands with both arms folded across the chest",
        "print": "safe - the arms rest on the torso"},
    "hands_hips": {
        "say": "the figure stands with both fists on the hips, elbows out",
        "print": "the elbows enclose a gap on each side; check overhang before slicing"},
    "hands_pockets": {
        "say": "the figure stands with both hands pushed into the trouser pockets",
        "print": "safe - the arms rest against the body"},
    "waving": {
        "say": "the figure stands with the right arm raised in a wave, "
               "the left arm at the side",
        "print": "RISKY - a raised arm is an unsupported overhang and a thin section at "
                 "110 mm. Check mesh_doctor overhang and expect to need supports"},
    "arms_out": {
        "say": "the figure stands with both arms held out low and away from the body, "
               "palms forward",
        "print": "RISKY - both arms are unsupported overhangs"},
}


def stage_pose(d, styled, pose_id, seed=4242, out_name=None):
    """Re-pose an already-styled figure. One edit, in words."""
    if pose_id not in FIGURE_POSES:
        raise RuntimeError("no such pose: %s (have %s)"
                           % (pose_id, ", ".join(sorted(FIGURE_POSES))))
    run, set_path, load_wf, ensure_local, HOST, COMFY = _comfy()
    staged = "bobble_pose_%d.png" % (int(time.time() * 1000) % 10 ** 8)
    shutil.copy(styled, os.path.join(COMFY, "input", staged))
    wf = load_wf("22_qwen_edit_2511.json")
    set_path(wf, "7.inputs.image", staged)
    set_path(wf, "10.inputs.prompt", "Change only the pose: %s. %s"
             % (FIGURE_POSES[pose_id]["say"], FIGURE_POSE_KEEP))
    set_path(wf, "12.inputs.prompt", "")
    set_path(wf, "15.inputs.seed", int(seed))
    set_path(wf, "17.inputs.filename_prefix",
             "claude-generated/bobble/pose_%s" % pose_id)
    _, outs = run(HOST, wf, quiet=True)
    if not outs:
        raise RuntimeError("the pose edit produced no output")
    dst = os.path.join(d, out_name or "styled.png")
    if os.path.exists(dst):
        os.remove(dst)
    ensure_local(outs[0], dst)
    return dst


def build_pose(fid, pose_id, socket_d, body_mm, seed=4242, process="fdm", redo=False):
    """One posed BODY for an existing figure, bored to the figure's socket diameter.

    The socket is passed in rather than re-derived. Each pose meshes separately, so each
    has its own neck cross-section - and if they were each clamped to their own neck the
    library would end up with bodies at 8.4, 8.1 and 7.6 mm that no single spring fits.
    The figure's diameter is the contract; a pose whose neck cannot take it is REPORTED,
    not silently re-bored.
    """
    fdir = os.path.join(FIGURES, fid)
    styled = os.path.join(fdir, "styled.png")
    if not os.path.isfile(styled):
        raise RuntimeError("figure %s has no styled.png - build the figure first" % fid)
    d = os.path.join(fdir, "poses", pose_id)
    os.makedirs(d, exist_ok=True)
    jp = os.path.join(d, "pose.json")
    if os.path.exists(jp) and not redo:
        try:
            old = json.load(open(jp, encoding="utf-8"))
            if old.get("ok"):
                return old
        except Exception:
            pass
    rec = {"id": pose_id, "figure": fid, "kind": "pose", "seed": seed,
           "body_mm": body_mm, "socket_target_mm": socket_d,
           "print_note": FIGURE_POSES[pose_id]["print"],
           "recipe": dict(RECIPE), "stages": {}, "built": time.time()}
    t0 = time.time()
    try:
        log("%s/%s: pose edit" % (fid, pose_id))
        stage_pose(d, styled, pose_id, seed)
        log("%s/%s: matte and square" % (fid, pose_id))
        sq, minfo = stage_matte(d, os.path.join(d, "styled.png"))
        rec["stages"]["matte"] = minfo
        log("%s/%s: Hunyuan3D" % (fid, pose_id))
        _, ginfo = stage_mesh(d, sq, seed, tag="pose_%s_%s" % (fid, pose_id),
                              octree_start=FIGURE_OCTREE)
        rec["stages"]["mesh"] = ginfo
        nominal = body_mm / NECK_FRACTION_GUESS
        solid, vr = stage_solid(d, "body", nominal, process)
        rec["recipe"]["voxel_res"] = vr
        smooth, sm = stage_smooth(d, solid)
        thin, dc = stage_decimate(d, smooth, "body")
        rec["stages"]["decimate"] = dc
        scaled = scale_to(d, thin, nominal)
        log("%s/%s: neck cut and socket" % (fid, pose_id))
        body, ninfo = stage_neck(d, scaled, body_mm, socket_d=socket_d)
        rec["stages"]["neck"] = {k: v for k, v in ninfo.items() if k != "profile"}
        if ninfo.get("socket_reduced"):
            rec["socket_mismatch"] = (
                "this pose's neck could only take %.2f mm, but the figure's head is bored "
                "to %.2f mm - they will not share a spring"
                % (ninfo["socket_d_mm"], socket_d))
            log("  %s" % rec["socket_mismatch"])
        rec["diagnose"] = md("diagnose", body)
        rec["print"] = stage_print(d, body, "%s_%s_%dmm" % (fid, pose_id, int(body_mm)))
        rec["views"] = stage_views(d, body, "%s_%s" % (fid, pose_id), kind="body")
        rec["ok"] = bool(rec["diagnose"].get("printable"))
    except Exception as e:                                            # noqa: BLE001
        import traceback
        rec["ok"] = False
        rec["error"] = "%s: %s" % (type(e).__name__, e)
        rec["trace"] = traceback.format_exc()[-1200:]
        log("%s/%s FAILED: %s" % (fid, pose_id, rec["error"]))
    rec["wall_secs"] = round(time.time() - t0, 1)
    json.dump(rec, open(jp, "w", encoding="utf-8"), indent=1)
    return rec


def build_figure(photo, fid=None, body_mm=None, head_mm=None, style="figurine",
                 redo=False, name=None, process="fdm"):
    """One photograph of a person -> a matched, socketed head and body."""
    fid = fid or os.path.splitext(os.path.basename(photo))[0].lower()
    fid = "".join(c if c.isalnum() or c in "._-" else "_" for c in fid)
    d = os.path.join(FIGURES, fid)
    os.makedirs(d, exist_ok=True)
    jp = os.path.join(d, "figure.json")
    rec = {"id": fid, "kind": "figure", "source_photo": os.path.basename(photo),
           "name": name or fid.replace("_", " ").title(),
           "recipe": dict(RECIPE), "seed": 777, "style": style, "process": process,
           "body_mm": body_mm or GEOM["body_mm"], "head_mm": head_mm or GEOM["head_mm"],
           "stages": {}, "built": time.time()}
    if os.path.exists(jp) and not redo:
        try:
            old = json.load(open(jp, encoding="utf-8"))
            if old.get("ok"):
                return old
        except Exception:
            pass
    t0 = time.time()
    try:
        src = os.path.join(d, "source.png")
        if os.path.abspath(photo) != os.path.abspath(src):
            shutil.copy(photo, src)
        try:
            rec["stages"]["crop_check"] = stage_detect_crop(d, src)
            if rec["stages"]["crop_check"].get("is_cropped"):
                log("%s: %s" % (fid, rec["stages"]["crop_check"]["note"]))
        except Exception as e:                                        # noqa: BLE001
            rec["stages"]["crop_check"] = {"detected": False, "why": str(e)[:100]}
        if style == "figurine":
            cropped = bool((rec["stages"].get("crop_check") or {}).get("is_cropped"))
            log("%s: preserve pass%s" % (fid, " + completion" if cropped else ""))
            src = stage_figure_style(d, src, rec["seed"], complete=cropped)
        log("%s: matte and square" % fid)
        sq, minfo = stage_matte(d, src)
        rec["stages"]["matte"] = minfo
        log("%s: Hunyuan3D" % fid)
        _, ginfo = stage_mesh(d, sq, rec["seed"], tag="fig_%s" % fid,
                              octree_start=FIGURE_OCTREE)
        rec["stages"]["mesh"] = ginfo

        log("%s: repair" % fid)
        nominal = rec["body_mm"] / NECK_FRACTION_GUESS
        solid, vr = stage_solid(d, "body", nominal, process)
        rec["recipe"]["voxel_res"] = vr
        rec["recipe"]["process"] = process
        smooth, sm = stage_smooth(d, solid)
        rec["stages"]["smooth"] = sm
        thin, dc = stage_decimate(d, smooth, "body")
        rec["stages"]["decimate"] = dc
        scaled = scale_to(d, thin, nominal)

        log("%s: neck cut, both sockets" % fid)
        halves, ninfo = stage_figure_split(d, scaled, rec["body_mm"], rec["head_mm"])
        rec["stages"]["split"] = {k: v for k, v in ninfo.items() if k != "profile"}
        rec["profile"] = ninfo.get("profile")

        # The head from the figure mesh is correctly CUT but under-resolved; re-mesh a
        # crop of it at the full octree and use that instead. The body keeps the figure
        # mesh, so the neck both sockets are sized from is still measured once.
        try:
            log("%s: re-meshing the head at full resolution" % fid)
            crop, cinfo = stage_figure_head_crop(d, ninfo["neck_f"])
            rec["stages"]["head_crop"] = cinfo
            hd = os.path.join(d, "_head")
            os.makedirs(hd, exist_ok=True)
            _, hg = stage_mesh(hd, crop, rec["seed"], tag="fighead_%s" % fid)
            rec["stages"]["head_mesh"] = hg
            hsolid, hvr = stage_solid(hd, "head", rec["head_mm"], process)
            hsm, _ = stage_smooth(hd, hsolid)
            hthin, hdc = stage_decimate(hd, hsm, "head")
            rec["stages"]["head_decimate"] = hdc
            hscaled = scale_to(hd, hthin, rec["head_mm"])
            hpath, hinfo2 = stage_head_socket(
                hd, hscaled, rec["head_mm"],
                socket_d=halves["body"][1]["socket_d_mm"])
            shutil.copyfile(hpath, os.path.join(d, "head.glb"))
            hinfo2["socket_d_mm"] = halves["body"][1]["socket_d_mm"]
            hinfo2["remeshed"] = True
            hinfo2["extents_mm"] = hinfo2.pop("head_extents_mm", None)
            hinfo2["watertight"] = hinfo2.pop("head_watertight", None)
            halves["head"] = (os.path.join(d, "head.glb"), hinfo2)
        except Exception as e:                                        # noqa: BLE001
            log("%s: head re-mesh failed (%s) - keeping the split head"
                % (fid, str(e)[:70]))
            halves["head"][1]["remeshed"] = False

        rec["parts"] = {}
        for half, (path, hinfo) in halves.items():
            mm = rec["body_mm"] if half == "body" else rec["head_mm"]
            dg = md("diagnose", path)
            rec["parts"][half] = dict(
                hinfo, diagnose=dg, height_mm=mm,
                print=stage_print(d, path, "%s_%s_%dmm" % (fid, half, int(mm))),
                views=stage_views(d, path, "%s_%s" % (fid, half),
                                  kind="head" if half == "head" else "body"))
        rec["ok"] = all(p["diagnose"].get("printable") for p in rec["parts"].values())
    except Exception as e:                                            # noqa: BLE001
        import traceback
        rec["ok"] = False
        rec["error"] = "%s: %s" % (type(e).__name__, e)
        rec["trace"] = traceback.format_exc()[-1500:]
        log("%s FAILED: %s" % (fid, rec["error"]))
    rec["wall_secs"] = round(time.time() - t0, 1)
    json.dump(rec, open(jp, "w", encoding="utf-8"), indent=1)
    return rec


# ─── the catalogue ──────────────────────────────────────────────────────────────────

def specs():
    if os.path.exists(SPECS):
        return json.load(open(SPECS, encoding="utf-8"))["bodies"]
    return []


def load_items(kind):
    root = BODIES if kind == "body" else HEADS
    name = "body.json" if kind == "body" else "head.json"
    out = []
    for p in sorted(glob.glob(os.path.join(root, "*", name))):
        try:
            out.append(json.load(open(p, encoding="utf-8")))
        except Exception:
            continue
    return out


# ─── cli ────────────────────────────────────────────────────────────────────────────

def cmd_catalog(a):
    ss = specs()
    print("  %d body specs" % len(ss))
    for s in ss:
        print("    %-22s %s" % (s["id"], s.get("subject", "")[:70]))
    return 0


def _summary(r):
    """The record without the two fields nobody reads at a terminal: the 220-row neck
    profile (the page draws it) and the traceback (the json keeps it)."""
    out = json.loads(json.dumps({k: v for k, v in r.items()
                                 if k not in ("trace", "spec")}))
    for k in ("neck", "socket"):
        if isinstance(out.get("stages", {}).get(k), dict):
            out["stages"][k].pop("profile", None)
    return out


def cmd_body(a):
    ss = {s["id"]: s for s in specs()}
    if a.id not in ss:
        print("no such spec: %s" % a.id, file=sys.stderr)
        return 2
    r = build_body(ss[a.id], seed=a.seed, height=a.height, redo=a.redo)
    print(json.dumps(_summary(r), indent=1))
    return 0 if r.get("ok") else 1


def _batch_lock():
    """Refuse to start a second batch while one is already running.

    *** THIS IS NOT DEFENSIVE PROGRAMMING. IT HAPPENED, THREE TIMES OVER. ***
    Three `fill --phase finish` runs ended up alive at once - each launched after the
    previous one appeared to have died, because a `pgrep` between two items reported
    nothing. MEASURED consequence: 48 GB resident, swap completely full, and a Poisson
    solve that takes 13 s alone taking over twenty minutes. Nothing crashed and nothing
    logged an error; the library simply stopped making progress.

    A PID file with a liveness check turns that into a message. Stale locks from a killed
    run clear themselves, so this cannot wedge the tool.
    """
    lp = os.path.join(LIB, ".batch.pid")
    try:
        old = int(open(lp).read().strip())
        os.kill(old, 0)                       # signal 0 just tests existence
        return None, ("a batch is already running as pid %d. Wait for it, or stop it "
                      "with `kill %d`." % (old, old))
    except (FileNotFoundError, ValueError, ProcessLookupError):
        pass
    except PermissionError:                   # someone else's pid - treat as live
        return None, "a batch appears to be running under another user"
    os.makedirs(LIB, exist_ok=True)
    open(lp, "w").write(str(os.getpid()))
    return lp, None


def cmd_fill(a):
    """The catalogue, PHASE BY PHASE ACROSS ALL ITEMS rather than item by item.

    Two reasons, one measured and one arithmetic. Measured: interleaving Qwen and
    Hunyuan3D per item is what OOM-killed the server (see free_models). Arithmetic: each
    switch costs a ~20 GB model load, so N bodies item-by-item pay 2N loads where phases
    pay 2.
    """
    lp, busy = _batch_lock()
    if busy:
        print("  " + busy, file=sys.stderr)
        return 2
    try:
        return _fill(a)
    finally:
        try:
            os.remove(lp)
        except OSError:
            pass


def _fill(a):
    ss = specs()
    if a.only:
        want = set(a.only.split(","))
        ss = [s for s in ss if s["id"] in want]
    if a.n:
        ss = ss[:a.n]
    recs = [_load_rec(s, height=a.height) for s in ss]
    if a.redo:
        for r in recs:
            r["phases"] = {}
    # --phase re-runs ONE phase over items that already have the earlier ones. The finish
    # phase touches no GPU, so a change to the neck finder or the socket can be re-applied
    # across the whole library in the time the mesh phase takes for two items.
    only = set((a.phase or "").split(",")) if a.phase else None
    if only:
        for r in recs:
            for k in list(r.get("phases", {})):
                if k in only:
                    r["phases"].pop(k)

    for name, fn in (("seed", phase_seed), ("mesh", phase_mesh),
                     ("finish", phase_finish)):
        todo = [r for r in recs if r.get("phases", {}).get(name) != "ok" or a.redo]
        if not todo:
            continue
        print("\n  PHASE %s - %d item(s)" % (name, len(todo)), flush=True)
        # The finish phase touches no GPU, but the Poisson solve is the most host-RAM
        # hungry thing in this tool - and ComfyUI sits on ~20 GB of cached weights it does
        # not need while that runs. MEASURED: leaving them there OOM-killed the batch on
        # its fourth body. Free before BOTH phases, not only the one that reloads.
        if name in ("mesh", "finish"):
            free_models()
        for r in todo:
            t0 = time.time()
            if _phase(r, name, fn, redo=a.redo) and name == "finish":
                r["wall_secs"] = round(sum((r.get("secs") or {}).values()), 1)
                _save_rec(r)
            del t0

    ok = sum(1 for r in recs if r.get("ok"))
    print("\n  %d/%d bodies complete" % (ok, len(recs)))
    for r in recs:
        if not r.get("ok"):
            print("    %-22s %s" % (r["id"], (r.get("error") or "incomplete")[:80]))
    return 0


def cmd_head(a):
    r = build_head(a.photo, hid=a.id, height=a.height, redo=a.redo,
                   style=a.style, name=a.name, from_raw=a.from_raw)
    print(json.dumps(_summary(r), indent=1))
    return 0 if r.get("ok") else 1


def cmd_sweep(a):
    """Move ONE dial on ONE held seed image and read the mesh back.

    This exists because docs/3D-QUALITY.md §4.1 names raising the octree above 512 as the
    cheapest untaken quality win on this box, and naming it is not measuring it.
    VERDICT.md §2 measured 256/384/512 and stopped there; the 512 run peaks at 9.9 GiB on
    a 32 GiB card, so the ceiling was never found.

    Everything except the swept dial is held, INCLUDING THE SEED - VERDICT.md §2 measured
    that seed variance alone changes leg thickness, skirt length and hair fall, so a sweep
    that lets the seed move is measuring two things and attributing both to one.

    Each cell frees ComfyUI's model cache first and revives the server if a cell kills it.
    High octree is the stage that OOM-killed this box once already (see free_models), and
    a sweep that dies on cell three and reports nothing is worse than one that records the
    death as the result.
    """
    import terra_mesh
    d = os.path.join(BODIES, a.id)
    sq = os.path.join(d, "source_square.png")
    if not os.path.isfile(sq):
        print("no squared seed for %s - build it first" % a.id, file=sys.stderr)
        return 2
    out = os.path.join(LIB, "sweeps", "%s_octree" % a.id)
    os.makedirs(out, exist_ok=True)
    rows, seed = [], a.seed or 1101

    from epic import COMFY
    stage_dir = os.path.join(COMFY, "input", "terra3d")
    os.makedirs(stage_dir, exist_ok=True)
    staged = "sweep_%s.png" % a.id
    shutil.copyfile(sq, os.path.join(stage_dir, staged))

    for oct_res in [int(x) for x in a.values.split(",")]:
        log("octree %d" % oct_res)
        row = {"octree": oct_res, "seed": seed}
        t0 = time.time()
        try:
            free_models()
            g = terra_mesh.graph_hunyuan(
                {"single": staged}, latent_res=RECIPE["latent_resolution"],
                octree=oct_res, threshold=RECIPE["threshold"], seed=seed,
                algorithm=RECIPE["algorithm"],
                prefix="claude-generated/bobble/sweep_%d" % oct_res,
                crop="center", steps=RECIPE["steps"], cfg=RECIPE["cfg"])
            outs, wall, vram = terra_mesh.run_graph(g, "sweep/oct%d" % oct_res)
            files = terra_mesh.collect_files(outs) if outs else []
            if not files:
                raise RuntimeError("no file")
            got = os.path.join(out, "oct%d.glb" % oct_res)
            shutil.copyfile(terra_mesh.resolve(files[0]), got)
            row.update(secs=round(wall, 1),
                       vram_mib=(vram or {}).get("peak_mib")
                       if isinstance(vram, dict) else None)
            dg = md("diagnose", got)
            row.update(faces=dg.get("faces"), islands=dg.get("components"),
                       nonmanifold=dg.get("nonmanifold_edges"),
                       nonmanifold_pct=round(100 * (dg.get("nonmanifold_fraction") or 0), 3),
                       boundary=dg.get("boundary_edges"),
                       watertight=dg.get("is_watertight"))
            try:
                terra_mesh.render_one(got, "oct%d" % oct_res, out, size=520,
                                      frames=2, ss=2, up="y")
            except Exception as e:                                  # noqa: BLE001
                row["render_error"] = str(e)[:120]
        except Exception as e:                                      # noqa: BLE001
            row.update(error="%s: %s" % (type(e).__name__, e),
                       secs=round(time.time() - t0, 1))
            log("octree %d FAILED: %s" % (oct_res, e))
            terra_mesh.revive()
        rows.append(row)
        json.dump({"id": a.id, "dial": "octree", "held": dict(RECIPE), "rows": rows},
                  open(os.path.join(out, "RESULT.json"), "w"), indent=1)

    print("\n  octree sweep on %s, seed %d, everything else held\n" % (a.id, seed))
    print("  %-8s %10s %8s %9s %12s %8s %10s" %
          ("octree", "faces", "islands", "nonman", "nonman %", "wall s", "VRAM MiB"))
    for r in rows:
        if r.get("error"):
            print("  %-8s  %s" % (r["octree"], r["error"][:60]))
            continue
        print("  %-8s %10s %8s %9s %12s %8s %10s" %
              (r["octree"], r["faces"], r["islands"], r["nonmanifold"],
               r["nonmanifold_pct"], r["secs"], r["vram_mib"]))
    print("\n  meshes and renders in %s" % out)
    return 0


def cmd_figure(a):
    r = build_figure(a.photo, fid=a.id, body_mm=a.body, head_mm=a.head,
                     style=a.style, redo=a.redo, name=a.name)
    print(json.dumps(_summary(r), indent=1))
    return 0 if r.get("ok") else 1


def cmd_pose(a):
    fdir = os.path.join(FIGURES, a.figure)
    fp = os.path.join(fdir, "figure.json")
    if not os.path.isfile(fp):
        print("no such figure: %s" % a.figure, file=sys.stderr)
        return 2
    fig = json.load(open(fp, encoding="utf-8"))
    sock = ((fig.get("parts") or {}).get("body") or {}).get("socket_d_mm") \
        or GEOM["socket_d"]
    want = [x.strip() for x in (a.poses or "").split(",") if x.strip()] \
        or sorted(FIGURE_POSES)
    bad = [x for x in want if x not in FIGURE_POSES]
    if bad:
        print("no such pose(s): %s\n  have: %s"
              % (", ".join(bad), ", ".join(sorted(FIGURE_POSES))), file=sys.stderr)
        return 2
    ok = 0
    for pid in want:
        r = build_pose(a.figure, pid, sock, fig.get("body_mm") or GEOM["body_mm"],
                       redo=a.redo)
        ok += 1 if r.get("ok") else 0
    print("  %d/%d poses built for %s" % (ok, len(want), a.figure))
    return 0 if ok == len(want) else 1


def cmd_poses(a):
    print("  %d poses" % len(FIGURE_POSES))
    for k in sorted(FIGURE_POSES):
        print("    %-16s %s" % (k, FIGURE_POSES[k]["say"]))
        print("    %-16s   print: %s" % ("", FIGURE_POSES[k]["print"]))
    return 0


def cmd_report(a):
    """One line per item, and the failures are lines too. A library that only prints
    what worked is the thing this project keeps having to un-learn."""
    for kind in ("body", "head"):
        items = load_items(kind)
        if not items:
            continue
        print("\n  %s (%d)" % (kind.upper(), len(items)))
        for it in items:
            if not it.get("ok"):
                print("    %-16s FAILED  %s" % (it["id"], (it.get("error") or "")[:64]))
                continue
            dg = it.get("diagnose") or {}
            st = it.get("stages") or {}
            n = st.get("neck") or st.get("socket") or {}
            ext = n.get("body_extents_mm") or n.get("head_extents_mm") or []
            print("    %-16s %7s faces  wt=%-5s isl=%-2s  %sx%sx%s mm  "
                  "joint d=%-5s socket=%-4s  print=%s  %ss"
                  % (it["id"], dg.get("faces"), dg.get("is_watertight"),
                     dg.get("components"),
                     *( [("%.0f" % x) for x in ext[:3]] + ["?"] * (3 - len(ext[:3])) ),
                     n.get("neck_diameter_mm") or n.get("flat_equiv_diameter_mm"),
                     n.get("socket_d_mm"), dg.get("printable"),
                     it.get("wall_secs")))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", metavar="SUBCOMMAND")
    sub.add_parser("catalog").set_defaults(fn=cmd_catalog)
    b = sub.add_parser("body"); b.add_argument("--id", required=True)
    b.add_argument("--seed", type=int); b.add_argument("--height", type=float)
    b.add_argument("--redo", action="store_true"); b.set_defaults(fn=cmd_body)
    f = sub.add_parser("fill"); f.add_argument("--n", type=int, default=0)
    f.add_argument("--only"); f.add_argument("--height", type=float)
    f.add_argument("--phase", help="re-run only these phases (seed,mesh,finish) over "
                                   "items that already have the earlier ones")
    f.add_argument("--redo", action="store_true"); f.set_defaults(fn=cmd_fill)
    h = sub.add_parser("head"); h.add_argument("--photo", required=True)
    h.add_argument("--id"); h.add_argument("--name")
    h.add_argument("--height", type=float)
    h.add_argument("--style", choices=("figurine", "raw"), default="figurine",
                   help="figurine runs the delight-and-close-the-hair pass first; "
                        "raw meshes the photograph as it is")
    h.add_argument("--from-raw", dest="from_raw", action="store_true",
                   help="reuse the existing raw.glb and re-run only the repair onward; "
                        "needs no GPU and no ComfyUI")
    h.add_argument("--redo", action="store_true"); h.set_defaults(fn=cmd_head)
    w = sub.add_parser("sweep", help="move one dial on one held seed and measure")
    w.add_argument("--id", required=True, help="a built body whose squared seed to reuse")
    w.add_argument("--values", default="512,640,768,1024")
    w.add_argument("--seed", type=int)
    w.set_defaults(fn=cmd_sweep)
    g = sub.add_parser("figure", help="one photo of a person -> a matched head and body")
    g.add_argument("--photo", required=True)
    g.add_argument("--id"); g.add_argument("--name")
    g.add_argument("--body", type=float, help="body height in mm")
    g.add_argument("--head", type=float, help="head height in mm")
    g.add_argument("--style", choices=("figurine", "raw"), default="figurine")
    g.add_argument("--redo", action="store_true"); g.set_defaults(fn=cmd_figure)
    q = sub.add_parser("pose", help="build posed bodies for an existing figure")
    q.add_argument("--figure", required=True)
    q.add_argument("--poses", help="comma-separated ids; default is all of them")
    q.add_argument("--redo", action="store_true"); q.set_defaults(fn=cmd_pose)
    sub.add_parser("poses", help="list the pose catalogue").set_defaults(fn=cmd_poses)
    sub.add_parser("report").set_defaults(fn=cmd_report)
    a = ap.parse_args(argv)
    if not getattr(a, "fn", None):
        ap.print_help()
        return 2
    os.makedirs(BODIES, exist_ok=True)
    os.makedirs(HEADS, exist_ok=True)
    os.makedirs(FIGURES, exist_ok=True)
    return a.fn(a)


if __name__ == "__main__":
    raise SystemExit(main())
