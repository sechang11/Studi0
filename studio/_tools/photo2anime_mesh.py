#!/usr/bin/env python3
"""photo2anime_mesh.py - test the stylisation thesis AT THE MESH.

    python3 studio/_tools/photo2anime_mesh.py prep
    python3 studio/_tools/photo2anime_mesh.py gen
    python3 studio/_tools/photo2anime_mesh.py diagnose
    python3 studio/_tools/photo2anime_mesh.py render
    python3 studio/_tools/photo2anime_mesh.py sheet
    python3 studio/_tools/photo2anime_mesh.py print --arm <photo|anime>
    python3 studio/_tools/photo2anime_mesh.py report

Every subcommand does one thing. A bare invocation and --help do NOTHING but print
help - seventeen tools in this directory run their whole job on any argument and this
is not one of them.

THIS TOOL OWNS, and writes nowhere else:
    studio/samples/photo2anime/mesh/*
    studio/samples/photo2anime/print/*

It IMPORTS mesh_doctor.py and mesh_prep.py through their command line with --json
(that is how terra_mesh.py consumes them too) and terra_mesh.py's software rasteriser
through a real python import for the argument sheet. None of those three files is
edited by anything here.

--------------------------------------------------------------------------------
THE QUESTION

craft/CHARACTER_TO_PRINT.md argues that anime stylisation IS geometric simplification:
hair stops being ten thousand fine strands and becomes a closed mass, cloth folds stop
being noise and become clean planes. Terra's mesh failed on the opposite problem -
DRAWING artefacts, separated hair locks that meshed as tubes, a bad hand in the seed
that became a bad hand in the mesh. So the prediction is that

    photo -> anime -> mesh   should beat   photo -> mesh

and the only honest way to know is to build both from the same person with everything
else nailed down, and look at them.

THE CONTROLLED PAIR

    A. PHOTO DIRECT   standin/ideal/cut_rgba_00001_.png - the sculpt-ready A-pose,
                      already matted, 1152x2048.
    B. ANIME FIRST    sweep/alt/qwen_ideal_apose.png - THE SAME FRAME through the
                      winning stylisation route (Qwen-Image-Edit 2511, redraw prompt,
                      style LoRA off), matted here with the same BiRefNet graph.

Identical downstream, every dial: grey plate, alpha-bbox crop, 5% margin, squared to
1024, CLIPVisionEncode crop=center, latent 4096, seed 20260806, 30 steps, cfg 5.0,
octree 512, surface net, VoxelToMesh threshold 0.45, single view.

A RESOLUTION NOTE, because it looks like a confound and is not. The anime seed is
752x1392 against the photo's 1152x2048, because Qwen-Image-Edit renders near 1 MP.
Both are squared and downscaled to 1024, and CLIPVisionEncode then centre-crops and
resamples to 518 px before the model sees anything. Both arms are DOWNSAMPLING into
that. Neither is upsampled to reach it, so the extra photo pixels are discarded
before conditioning and cannot be the cause of any difference.

--------------------------------------------------------------------------------
WHAT IT MEASURED, 2026-08-06. mesh/VERDICT.json carries the same thing as data;
mesh/sheets/ carries the pictures every claim below was read off, and every one of
them was opened and looked at.
--------------------------------------------------------------------------------

THE ANSWER IS SPLIT, AND THE THESIS IS WRONG ABOUT ITS OWN MECHANISM.
The photograph makes the better OBJECT. The drawing makes the better FACE.

1. HAIR - THE THESIS IS REFUTED, AND BACKWARDS.  sheets/HEAD_HAIR.jpg, 180 deg.
   The PHOTOGRAPH produced the closed hair mass the thesis predicted from the
   drawing: one continuous shell crown to shoulder blade, soft ripples, no
   separations. The DRAWING reproduced Terra's exact failure - the hair ends came
   through as a row of discrete curled TUBES on the shoulders with gaps between
   them. Ligne-claire art OUTLINES each lock and this mesher reads a closed outline
   as a closed volume. Real hair has no outlines, so photographic hair has nothing
   to separate along. FINE STRANDS WERE NEVER THE RISK. DRAWN CONTOURS ARE.

2. FACE - THE DRAWING WINS, AND IT REVERSES THE VERDICT.  sheets/LIKENESS.jpg.
   The photo mesh's face is a blank: the nose has almost no projection (the 75 deg
   profile is nearly flat), the mouth is a dent, and the glasses are one thick
   squarish slab over the whole midface. It is not somebody else, it is nobody.
   The anime mesh has a nose with a bridge and a tip, lips, a chin, a brow, and
   ROUND correctly-scaled glasses sitting on that nose - her strongest marker.
   WHY: facial relief in a photograph is carried by SHADING, which is a millimetre
   of real depth, and the mesher smooths it away as noise. The redraw turns that
   shading into LINES, and lines are what this mesher builds relief from. The same
   property that ruins the hair rescues the face.

3. HANDS - A TIE.  sheets/FISTS.jpg. Both arms gave correct closed fists with a
   thumb at all three angles, no extra digits, no fusion into the hip. Neither
   reproduced Terra's bad hand, because the A-pose SEED had closed hands - a
   property of the source, not of the stylisation.

4. CLOTH - THE THESIS HOLDS.  sheets/HANDS.jpg, sheets/ORBITS.jpg. Corduroy became
   soft undifferentiated mush on the photo arm; on the anime arm the jacket has
   crisp panel seams, readable pocket flaps, a defined placket and cuffs.

5. PRINTABLE BY THE NUMBERS - PHOTO WINS THE RAW MESH, AND THE GAP THEN CLOSES.
   Raw:  components 2634 vs 5169, non-manifold edges 6361 vs 11417, boundary edges
   36 vs 116, surface below minimum feature 0.17% vs 0.87%, 1st-percentile
   thickness 1.64 vs 1.03 mm, overhang 2.24% vs 2.93%. Photo wins every column.
   AFTER mesh_prep solidify, both are watertight, one body, zero non-manifold, no
   blocking issues and no warnings: 96.9 cm3 / 0.00% sub-0.8 mm (photo) against
   93.8 cm3 / 0.01% (anime). RAW HUNYUAN3D TOPOLOGY IS AN ARGUMENT ABOUT HOW MUCH
   WORK THE REPAIR HAS TO DO, NOT ABOUT WHAT YOU CAN PRINT. Judge after the voxel
   pass, and the anime arm's only remaining thin material is the hair-lock tubes at
   120-130 mm (print/STANDIN_150mm_thinmap.jpg - it is a dozen red dots).

DECISION: B_anime, because the brief says a beautiful mesh of somebody else is a
failure, so likeness decides it. Every raw deficit B carries is the kind mesh_prep
removes by construction; a face that was never in the geometry cannot be repaired
back in. Shipped as print/STANDIN_150mm.stl/.3mf/.glb, each re-verified watertight
by RELOADING it from disk. If the face does NOT have to be hers - a background
figure, a scale body - photo direct wins outright and should be used.

HONEST LIMIT: neither mesh is a portrait likeness at 150 mm. B is more recognisably
her; it is not recognisable AS her.

ONE OPERATIONAL FINDING, PAID FOR HERE. The box is shared and ComfyUI was restarted
under this run twice. A restart WIPES /history AND /queue, so a submitted prompt id
stops existing - and epic.wait_all, which only asks /history whether a pid has
finished, waits for it forever. Twelve minutes of silence that looked exactly like a
slow surface-net extraction. stage_gen instead asks whether the pid is still
SOMETHING the server admits to and resubmits after two consecutive 'gone' polls.
Both meshes then landed in 312 s with one resubmit each.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
STUDIO = os.path.dirname(HERE)
ROOT = os.path.dirname(STUDIO)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
os.environ.setdefault("COMFY_HOST", "127.0.0.1:8188")

from epic import load_wf, ensure_local, submit, wait_all, HOST   # noqa: E402

COMFY = os.path.expanduser("~/ComfyUI")
COMFY_IN = os.path.join(COMFY, "input", "p2amesh")
COMFY_OUT = os.path.join(COMFY, "output")

BASE = os.path.join(STUDIO, "samples", "photo2anime")
STANDIN = os.path.join(BASE, "standin")
SWEEP = os.path.join(BASE, "sweep")
MESH = os.path.join(BASE, "mesh")
PRINT = os.path.join(BASE, "print")
WORK = os.path.join(MESH, "_work")
VIEWS = os.path.join(MESH, "views")
SHEETS = os.path.join(MESH, "sheets")
PWORK = os.path.join(PRINT, "_work")

MESH_DOCTOR = os.path.join(HERE, "mesh_doctor.py")
MESH_PREP = os.path.join(HERE, "mesh_prep.py")

# ---- the two arms, and everything they share -------------------------------
SRC_PHOTO = os.path.join(STANDIN, "ideal", "cut_rgba_00001_.png")
SRC_ANIME = os.path.join(SWEEP, "alt", "qwen_ideal_apose.png")

PLATE = (132, 132, 132)      # the #848484 grey this project uses everywhere
PLATE_NAME = "grey"
MARGIN = 0.05
PLATE_PX = 1024

SEED = 20260806
LATENT = 4096
OCTREE = 512
THRESHOLD = 0.45
ALGO = "surface net"
STEPS = 30
CFG = 5.0

ARMS = [
    ("A_photo", "PHOTO DIRECT - control"),
    ("B_anime", "ANIME FIRST - treatment"),
]


def log(m):
    print(m, flush=True)


def ensure_dirs():
    for d in (MESH, PRINT, WORK, VIEWS, SHEETS, PWORK, COMFY_IN):
        os.makedirs(d, exist_ok=True)


def read_json(p, default=None):
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def write_json(p, obj):
    os.makedirs(os.path.dirname(os.path.abspath(p)), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=1, default=str)
    log("  wrote %s" % p)


# ---------------------------------------------------------------------------
# prep
# ---------------------------------------------------------------------------

def composite_square(im, plate, out_w, margin=MARGIN):
    """RGBA -> opaque square RGB, cropped to the subject and padded.

    Cropping to the ALPHA BBOX first and only then squaring is what makes the two
    arms comparable: it removes the framing difference between a 1152x2048 photo
    and a 752x1392 drawing, so the subject occupies the same fraction of both
    plates. CLIPVisionEncode crop=center would otherwise centre-crop two different
    amounts of body away.
    """
    from PIL import Image
    if im.mode != "RGBA":
        im = im.convert("RGBA")
    bb = im.getbbox()
    if bb:
        im = im.crop(bb)
    w, h = im.size
    side = max(w, h)
    pad = int(round(side * margin))
    side += 2 * pad
    canvas = Image.new("RGBA", (side, side), plate + (255,))
    canvas.paste(im, ((side - w) // 2, (side - h) // 2), im)
    canvas = canvas.convert("RGB")
    if out_w and out_w != side:
        canvas = canvas.resize((out_w, out_w), Image.LANCZOS)
    return canvas, bb, side


def matte(src, dst, tag):
    """BiRefNet (workflow 14) on an OPAQUE image, returning RGBA.

    The anime seed comes back from Qwen-Image-Edit as flat RGB on a near-white
    ground, and a luminance key would eat her white t-shirt and her white sneakers.
    BiRefNet is the same matter that produced the photo arm's cut_rgba, so both
    arms carry the same class of edge.
    """
    from PIL import Image
    if os.path.exists(dst):
        log("  matte already on disk: %s" % dst)
        return dst
    im = Image.open(src)
    name = "p2amesh_%s_src.png" % tag
    shutil.copy(src, os.path.join(COMFY_IN, name))
    wf = load_wf("14_birefnet_matte.json")
    wf["1"]["inputs"]["image"] = "p2amesh/" + name
    wf["8"]["inputs"]["width"], wf["8"]["inputs"]["height"] = im.size
    wf["10"]["inputs"]["filename_prefix"] = "claude-generated/p2amesh/%s_rgba" % tag
    for n in ("11", "12"):
        wf[n]["inputs"]["filename_prefix"] = "claude-generated/p2amesh/%s_%s" % (tag, n)
    pid = submit(wf)
    wait_all([pid], "matte-%s" % tag)
    h = json.load(urllib.request.urlopen("http://%s/history/%s" % (HOST, pid), timeout=60))
    for nid, out in (h.get(pid, {}).get("outputs") or {}).items():
        if nid != "10":
            continue
        for f in out.get("images", []):
            rel = ("%s/%s" % (f.get("subfolder", ""), f["filename"])).lstrip("/")
            ensure_local(rel, dst, required=True)
            return dst
    raise SystemExit("matte produced no RGBA for %s" % tag)


def stage_prep(args):
    from PIL import Image
    ensure_dirs()
    rec = {"plate": PLATE_NAME, "plate_rgb": list(PLATE), "margin": MARGIN,
           "plate_px": PLATE_PX, "arms": {}}

    anime_rgba = os.path.join(WORK, "anime_rgba.png")
    matte(SRC_ANIME, anime_rgba, "anime")

    for arm, src in (("A_photo", SRC_PHOTO), ("B_anime", anime_rgba)):
        im = Image.open(src)
        sq, bb, side = composite_square(im, PLATE, PLATE_PX)
        name = "p2amesh_%s_plate.png" % arm
        sq.save(os.path.join(COMFY_IN, name))
        sq.save(os.path.join(WORK, name))
        rec["arms"][arm] = {
            "source": os.path.relpath(src, ROOT),
            "source_px": list(im.size), "source_mode": im.mode,
            "alpha_bbox": list(bb) if bb else None,
            "subject_px": [bb[2] - bb[0], bb[3] - bb[1]] if bb else None,
            "square_before_resize": side, "plate_file": name,
        }
        log("  %-8s %s  bbox %s  -> %dpx square -> %d" %
            (arm, im.size, bb, side, PLATE_PX))
    write_json(os.path.join(MESH, "PREP.json"), rec)
    return 0


# ---------------------------------------------------------------------------
# gen
# ---------------------------------------------------------------------------

def graph_hunyuan(image_name, prefix):
    """Workflow 24's graph, rebuilt in memory so the dials are explicit and the
    two arms are provably identical apart from the LoadImage filename."""
    return {
        "1": {"class_type": "ImageOnlyCheckpointLoader",
              "inputs": {"ckpt_name": "hunyuan_3d_v2.1.safetensors"}},
        "2": {"class_type": "LoadImage", "inputs": {"image": "p2amesh/" + image_name}},
        "3": {"class_type": "ModelSamplingAuraFlow",
              "inputs": {"model": ["1", 0], "shift": 1.0}},
        "4": {"class_type": "CLIPVisionEncode",
              "inputs": {"clip_vision": ["1", 1], "image": ["2", 0], "crop": "center"}},
        "5": {"class_type": "Hunyuan3Dv2Conditioning",
              "inputs": {"clip_vision_output": ["4", 0]}},
        "6": {"class_type": "EmptyLatentHunyuan3Dv2",
              "inputs": {"resolution": LATENT, "batch_size": 1}},
        "7": {"class_type": "KSampler",
              "inputs": {"model": ["3", 0], "seed": SEED, "steps": STEPS, "cfg": CFG,
                         "sampler_name": "euler", "scheduler": "normal",
                         "positive": ["5", 0], "negative": ["5", 1],
                         "latent_image": ["6", 0], "denoise": 1.0}},
        "8": {"class_type": "VAEDecodeHunyuan3D",
              "inputs": {"samples": ["7", 0], "vae": ["1", 2],
                         "num_chunks": 8000, "octree_resolution": OCTREE}},
        "9": {"class_type": "VoxelToMesh",
              "inputs": {"voxel": ["8", 0], "algorithm": ALGO, "threshold": THRESHOLD}},
        "10": {"class_type": "SaveGLB",
               "inputs": {"mesh": ["9", 0], "filename_prefix": prefix}},
    }


def _get(path, timeout=60):
    return json.load(urllib.request.urlopen("http://%s%s" % (HOST, path), timeout=timeout))


def _known(pid):
    """Is this prompt id still something the server admits to? Returns
    'queued' | 'running' | 'done' | 'error' | 'gone'."""
    try:
        h = _get("/history/%s" % pid, timeout=60)
    except Exception:
        return "unknown"
    if pid in h:
        st = h[pid].get("status", {})
        if st.get("status_str") == "error":
            return "error"
        if st.get("completed"):
            return "done"
    try:
        q = _get("/queue", timeout=30)
    except Exception:
        return "unknown"
    for it in q.get("queue_running", []):
        if len(it) > 1 and it[1] == pid:
            return "running"
    for it in q.get("queue_pending", []):
        if len(it) > 1 and it[1] == pid:
            return "queued"
    return "gone"


def _pull_glb(pid, dst):
    h = _get("/history/%s" % pid, timeout=120)
    for _nid, out in (h.get(pid, {}).get("outputs") or {}).items():
        for key in ("result", "3d", "meshes", "gltf", "images"):
            for it in (out.get(key) or []):
                fn = it["filename"] if isinstance(it, dict) else os.path.basename(it)
                if not fn.endswith(".glb"):
                    continue
                sub = it.get("subfolder", "") if isinstance(it, dict) else ""
                local = os.path.join(COMFY_OUT, sub, fn)
                if os.path.exists(local):
                    shutil.copy(local, dst)
                else:
                    ensure_local(("%s/%s" % (sub, fn)).lstrip("/"), dst, required=True)
                return True
    return False


def stage_gen(args):
    """Submit both arms, then wait ON A LEASH THAT SURVIVES A SERVER RESTART.

    PAID FOR HERE. The box is shared. Both meshes were submitted as one batch,
    the first got through KSampler and 35 s of volume decoding, and then another
    session restarted ComfyUI. A restart WIPES /history AND /queue, so both
    prompt ids simply stopped existing - and epic.wait_all, which only ever asks
    /history whether a pid has finished, waited for them forever. Twelve minutes
    of silence that looked exactly like a slow surface-net extraction.

    So the wait below asks a different question: is this pid still SOMETHING the
    server admits to - running, queued, or in history? A pid that is in none of
    those three is not slow, it is gone, and the only correct response is to
    submit it again. Two consecutive 'gone' polls (12 s apart) before resubmitting,
    because there is a real window between /prompt returning and the id appearing
    in the queue.
    """
    ensure_dirs()
    prep = read_json(os.path.join(MESH, "PREP.json"))
    if not prep:
        raise SystemExit("run `prep` first - no mesh/PREP.json")

    todo = []
    for arm, _ in ARMS:
        dst = os.path.join(MESH, "%s.glb" % arm)
        if os.path.exists(dst) and not args.force:
            log("  %s already meshed" % arm)
            continue
        todo.append((arm, dst))
    if not todo:
        return 0

    graphs = {arm: graph_hunyuan(prep["arms"][arm]["plate_file"],
                                 "claude-generated/p2amesh/%s" % arm)
              for arm, _ in todo}
    pid = {arm: submit(graphs[arm]) for arm, _ in todo}
    log("queued %d meshes as one batch: %s" %
        (len(pid), ", ".join("%s=%s" % (a, p[:8]) for a, p in pid.items())))

    t0, got, gone, resubs = time.time(), {}, {a: 0 for a, _ in todo}, {a: 0 for a, _ in todo}
    left = dict(todo)
    while left and time.time() - t0 < args.timeout:
        time.sleep(12)
        for arm in list(left):
            st = _known(pid[arm])
            if st == "done":
                if _pull_glb(pid[arm], left[arm]):
                    got[arm] = {"glb": left[arm], "bytes": os.path.getsize(left[arm]),
                                "resubmits": resubs[arm]}
                    log("  %-8s -> %s  (%.1f MB, %.0fs, %d resubmits)" %
                        (arm, left[arm], got[arm]["bytes"] / 1e6,
                         time.time() - t0, resubs[arm]))
                    del left[arm]
                continue
            if st in ("error", "gone"):
                gone[arm] += 1
                if gone[arm] >= 2:
                    resubs[arm] += 1
                    if resubs[arm] > args.max_resubmit:
                        log("  %s: gave up after %d resubmits" % (arm, resubs[arm] - 1))
                        del left[arm]
                        continue
                    log("  %s: prompt %s vanished (%s) - the server restarted under us; "
                        "resubmitting (#%d)" % (arm, pid[arm][:8], st, resubs[arm]))
                    for _try in range(20):
                        try:
                            pid[arm] = submit(graphs[arm])
                            break
                        except Exception as e:
                            log("    server not answering (%s); retrying" % str(e)[:60])
                            time.sleep(15)
                    gone[arm] = 0
            else:
                gone[arm] = 0
        if left:
            log("  [%5.0fs] waiting on %s" % (time.time() - t0, ",".join(left)))
    write_json(os.path.join(WORK, "gen.json"),
               {"seed": SEED, "latent": LATENT, "octree": OCTREE,
                "threshold": THRESHOLD, "algorithm": ALGO, "steps": STEPS,
                "cfg": CFG, "views": "single", "crop": "center",
                "wall_seconds": round(time.time() - t0, 1), "got": got,
                "unfinished": sorted(left)})
    return 0 if not left else 1


# ---------------------------------------------------------------------------
# diagnose
# ---------------------------------------------------------------------------

def md(subcmd, mesh, *extra):
    r = subprocess.run([sys.executable, MESH_DOCTOR, subcmd, mesh, "--json"] +
                       list(extra), capture_output=True, text=True, timeout=3600)
    try:
        return json.loads(r.stdout)
    except Exception:
        return {"error": (r.stderr or r.stdout)[-800:]}


def stage_diagnose(args):
    ensure_dirs()
    out = {}
    for arm, why in ARMS:
        p = os.path.join(MESH, "%s.glb" % arm)
        if not os.path.exists(p):
            log("  %s: no glb" % arm)
            continue
        log("  %s ..." % arm)
        out[arm] = {
            "why": why,
            "diagnose": md("diagnose", p),
            "thickness": md("thickness", p, "--height", "150"),
            "overhang": md("overhang", p, "--height", "150"),
        }
    write_json(os.path.join(MESH, "DIAGNOSE.json"), out)
    for arm in out:
        d = out[arm]["diagnose"]
        log("  %-8s faces=%s watertight=%s bodies=%s" %
            (arm, d.get("faces"), d.get("is_watertight"),
             d.get("components") or d.get("bodies")))
    return 0


# ---------------------------------------------------------------------------
# render
# ---------------------------------------------------------------------------

def stage_render(args):
    ensure_dirs()
    res = {}
    for arm, _ in ARMS:
        p = os.path.join(MESH, "%s.glb" % arm)
        if not os.path.exists(p):
            continue
        log("  rendering %s ..." % arm)
        r = subprocess.run([sys.executable, MESH_PREP, "render", p,
                            "--name", arm, "--outdir", VIEWS,
                            "--size", str(args.size), "--frames", str(args.frames),
                            "--up", args.up, "--json"],
                           capture_output=True, text=True, timeout=3600)
        try:
            res[arm] = json.loads(r.stdout)
        except Exception:
            res[arm] = {"error": (r.stderr or r.stdout)[-800:]}
        log("    %s" % json.dumps(res[arm])[:260])
    write_json(os.path.join(WORK, "render.json"), res)
    return 0


# ---------------------------------------------------------------------------
# sheets
# ---------------------------------------------------------------------------

def _tm_render(path, up, az, el, size, band=None, samples=2600000):
    """One frame from terra_mesh's software rasteriser. Imported, never edited.

    band: keep only the top `band` fraction of the up axis (the head).

    SAMPLES IS NOT COSMETIC. This is a point splat, not a triangle rasteriser: too
    few samples spread over a full frame and the sampling noise reads as surface
    texture that is not on the model - which is fatal when the whole question is
    whether one surface is smoother than another. The face sheets run 12M.
    """
    import numpy as np
    if HERE not in sys.path:
        sys.path.insert(0, HERE)
    import terra_mesh as tm
    pts, nrm, bounds, nf, nv = tm._sample_mesh(path, samples)
    ext = bounds[1] - bounds[0]
    uidx = int(np.argmax(ext)) if up == "auto" else tm._axis_index(up)
    if band:
        if isinstance(band, (tuple, list)):
            # an arbitrary window measured DOWN from the crown, so the hands can be
            # framed as tightly as the head is
            lo, hi = band
            top = bounds[1][uidx]
            sel = ((pts[:, uidx] <= top - ext[uidx] * lo) &
                   (pts[:, uidx] >= top - ext[uidx] * hi))
            pts, nrm = pts[sel], nrm[sel]
        else:
            try:
                pts, nrm = tm._sample_band(path, uidx, band, samples)
            except Exception:
                top = bounds[1][uidx]
                sel = pts[:, uidx] >= (top - ext[uidx] * band)
                pts, nrm = pts[sel], nrm[sel]
        b = np.stack([pts.min(0), pts.max(0)])
        centre = (b[0] + b[1]) / 2.0
        half = float(max(b[1] - b[0])) / 2.0
    else:
        centre = (bounds[0] + bounds[1]) / 2.0
        half = float(max(ext)) / 2.0
    arr = tm._render_frame(pts, nrm, centre, half, uidx, az, el, size, 2, "clay")
    return tm._to_pil(arr, size, 2)


def _label(im, text):
    from PIL import ImageDraw, ImageFont
    d = ImageDraw.Draw(im)
    try:
        f = ImageFont.truetype("/usr/share/fonts/dejavu-sans-fonts/DejaVuSans-Bold.ttf", 22)
    except Exception:
        try:
            f = ImageFont.truetype(
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 22)
        except Exception:
            f = ImageFont.load_default()
    d.rectangle([0, 0, im.width, 34], fill=(18, 18, 22))
    d.text((8, 6), text, fill=(255, 255, 255), font=f)
    return im


def sheet(images, labels, dst, cols, cw, ch):
    """Contact sheet with the CELL COUNT ASSERTED. ffmpeg tile= with a glob silently
    drops cells of differing size; so does a zip() over mismatched lists. Count what
    was actually pasted and fail loudly if it is not what was asked for."""
    from PIL import Image
    assert len(images) == len(labels), "%d images vs %d labels" % (len(images),
                                                                  len(labels))
    n = len(images)
    rows = (n + cols - 1) // cols
    pad = 6
    W = cols * cw + (cols + 1) * pad
    H = rows * ch + (rows + 1) * pad
    canvas = Image.new("RGB", (W, H), (24, 24, 30))
    placed = 0
    for i, (im, lab) in enumerate(zip(images, labels)):
        im = im.convert("RGB")
        im.thumbnail((cw, ch - 34), Image.LANCZOS)
        cell = Image.new("RGB", (cw, ch), (36, 36, 44))
        cell.paste(im, ((cw - im.width) // 2, 34 + (ch - 34 - im.height) // 2))
        _label(cell, lab)
        x = pad + (i % cols) * (cw + pad)
        y = pad + (i // cols) * (ch + pad)
        canvas.paste(cell, (x, y))
        placed += 1
    assert placed == n, "placed %d of %d cells" % (placed, n)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    canvas.save(dst, quality=92)
    log("  %s  (%d cells, %dx%d)" % (dst, placed, W, H))
    return dst


def stage_sheet(args):
    """The one image the whole argument has to be visible in, plus the two
    close-read sheets: hair/head and hands."""
    from PIL import Image
    ensure_dirs()
    up = args.up
    made = []

    # --- ARGUMENT.jpg : photo | anime seed | photo-mesh | anime-mesh ---------
    photo = Image.open(SRC_PHOTO).convert("RGBA")
    bgp = Image.new("RGBA", photo.size, PLATE + (255,))
    bgp.paste(photo, (0, 0), photo)
    anime = Image.open(SRC_ANIME).convert("RGB")
    ma = _tm_render(os.path.join(MESH, "A_photo.glb"), up, 0.0, 8.0, 900, samples=9000000)
    mb = _tm_render(os.path.join(MESH, "B_anime.glb"), up, 0.0, 8.0, 900, samples=9000000)
    made.append(sheet(
        [bgp.convert("RGB"), anime, ma, mb],
        ["1. PHOTO  (standin ideal A-pose)",
         "2. ANIME SEED  (Qwen edit 2511, same frame)",
         "3. PHOTO -> MESH   (control)",
         "4. ANIME -> MESH   (treatment)"],
        os.path.join(SHEETS, "ARGUMENT.jpg"), 4, 520, 940))

    # --- HEAD_HAIR.jpg : the hair question, three angles per arm ------------
    ims, labs = [], []
    for arm, _ in ARMS:
        p = os.path.join(MESH, "%s.glb" % arm)
        for az in (0.0, 45.0, 180.0):
            ims.append(_tm_render(p, up, az, 0.0, 620, band=0.26, samples=9000000))
            labs.append("%s  head %d deg" % (arm, int(az)))
    made.append(sheet(ims, labs, os.path.join(SHEETS, "HEAD_HAIR.jpg"), 3, 560, 600))

    # --- FACE.jpg : the question that decides it, as big as the mesh allows -
    # A face is a pixel problem at render time too. Top 14% of the figure only,
    # 12M samples, 900 px cells, and no elevation so the read is head-on.
    ims, labs = [], []
    for arm, _ in ARMS:
        p = os.path.join(MESH, "%s.glb" % arm)
        for az, el in ((0.0, 0.0), (30.0, 0.0), (75.0, 0.0)):
            ims.append(_tm_render(p, up, az, el, 900, band=0.14, samples=12000000))
            labs.append("%s  face %d deg" % (arm, int(az)))
    made.append(sheet(ims, labs, os.path.join(SHEETS, "FACE.jpg"), 3, 840, 880))

    # --- HANDS.jpg : mid-band, the other place Terra failed -----------------
    ims, labs = [], []
    for arm, _ in ARMS:
        p = os.path.join(MESH, "%s.glb" % arm)
        for az in (0.0, 90.0, 270.0):
            ims.append(_tm_render(p, up, az, -12.0, 620, band=0.62, samples=9000000))
            labs.append("%s  torso+arms %d deg" % (arm, int(az)))
    made.append(sheet(ims, labs, os.path.join(SHEETS, "HANDS.jpg"), 3, 560, 600))

    # --- FISTS.jpg : just the hands, tight. Terra's mesh inherited a bad hand
    # straight out of its seed, so this is the second place stylisation could
    # plausibly help or hurt.
    ims, labs = [], []
    for arm, _ in ARMS:
        p = os.path.join(MESH, "%s.glb" % arm)
        for az in (0.0, 60.0, 300.0):
            ims.append(_tm_render(p, up, az, -8.0, 820, band=(0.42, 0.60),
                                  samples=12000000))
            labs.append("%s  hands %d deg" % (arm, int(az)))
    made.append(sheet(ims, labs, os.path.join(SHEETS, "FISTS.jpg"), 3, 760, 800))

    # --- LIKENESS.jpg : THE SHEET THAT DECIDES IT ---------------------------
    # Her face in all four states at the same height on the page. A beautiful mesh
    # of somebody else is a failure here, so the two mesh faces are put next to the
    # two things they are supposed to be a likeness OF, not next to each other.
    def head_crop(path, plate=None):
        im = Image.open(path)
        if im.mode == "RGBA" and plate:
            bg = Image.new("RGBA", im.size, plate + (255,))
            bg.paste(im, (0, 0), im)
            im = bg
        im = im.convert("RGB")
        w, h = im.size
        # both sources are the same full-body A-pose framing: head is the top ~13%
        return im.crop((int(w * 0.28), int(h * 0.055), int(w * 0.72), int(h * 0.30)))

    ims = [head_crop(SRC_PHOTO, PLATE), head_crop(SRC_ANIME),
           _tm_render(os.path.join(MESH, "A_photo.glb"), up, 0.0, 0.0, 900,
                      band=0.13, samples=12000000),
           _tm_render(os.path.join(MESH, "B_anime.glb"), up, 0.0, 0.0, 900,
                      band=0.13, samples=12000000)]
    made.append(sheet(ims, ["1. PHOTO - the face to match",
                            "2. ANIME SEED - still her, drawn",
                            "3. PHOTO -> MESH", "4. ANIME -> MESH"],
                      os.path.join(SHEETS, "LIKENESS.jpg"), 4, 700, 740))

    # --- ORBITS.jpg : the two orbit strips stacked --------------------------
    strips = [os.path.join(VIEWS, "%s_orbit.jpg" % a) for a, _ in ARMS]
    if all(os.path.exists(s) for s in strips):
        made.append(sheet([Image.open(s) for s in strips],
                          ["A_photo orbit", "B_anime orbit"],
                          os.path.join(SHEETS, "ORBITS.jpg"), 1, 1900, 560))
    write_json(os.path.join(WORK, "sheets.json"), {"sheets": made})
    return 0


# ---------------------------------------------------------------------------
# print
# ---------------------------------------------------------------------------

def mp(*a):
    r = subprocess.run([sys.executable, MESH_PREP] + list(a),
                       capture_output=True, text=True, timeout=7200)
    sys.stdout.write(r.stdout[-4000:])
    if r.returncode != 0:
        sys.stderr.write(r.stderr[-4000:])
    return r


def stage_print(args):
    """Take an arm to a finished STL, on Terra's measured print recipe: 145 mm
    figure on a 6 mm plinth to 150 mm total, 0.15 mm voxel pitch, 0.6 mm
    morphological close, 1.0 mm minimum feature. Terra's own numbers, so the two
    figures are comparable as prints as well as as meshes.

    --no-export runs solidify and audit and stops. That is how the LOSING arm is
    measured, and it is not busywork: raw Hunyuan3D topology counts (components,
    non-manifold edges, sub-millimetre surface) are an argument about what the
    REPAIR will have to do, not about what you can print. mesh_prep's single voxel
    pass drops strays, closes crevices and grows everything to the minimum feature
    by construction, so both arms have to be re-measured on the far side of it
    before "more printable" means anything.
    """
    ensure_dirs()
    arm = args.arm
    src = os.path.join(MESH, "%s.glb" % arm)
    if not os.path.exists(src):
        raise SystemExit("no mesh at %s" % src)
    stem = args.name
    solid = os.path.join(PWORK, "%s_solid.glb" % stem)
    if not os.path.exists(solid) or args.force:
        mp("solidify", src, "--out", solid,
           "--report", os.path.join(PWORK, "%s_solidify.json" % stem),
           "--figure-mm", "145", "--total-mm", "150", "--pitch", "0.15",
           "--close-mm", "0.6", "--min-mm", "1.0", "--thin-min-mm3", "1.0",
           "--up", args.up, "--json")
    mp("audit", solid, "--report", os.path.join(PWORK, "%s_audit.json" % stem),
       "--thinmap", os.path.join(PRINT, "%s_thinmap.jpg" % stem),
       "--name", stem, "--json")
    if args.no_export:
        d = md("diagnose", solid)
        log("  %s SOLID: watertight=%s faces=%s components=%s" %
            (stem, d.get("is_watertight"), d.get("faces"), d.get("components")))
        return 0
    outs = []
    for ext in ("stl", "3mf", "glb"):
        outs += ["--out", os.path.join(PRINT, "%s.%s" % (stem, ext))]
    mp("export", solid, *(outs + ["--report", os.path.join(PWORK, "%s_export.json" % stem),
                                  "--json"]))
    # re-verify every written file by RELOADING it from disk, not by trusting export
    verify = {}
    for ext in ("stl", "3mf", "glb"):
        p = os.path.join(PRINT, "%s.%s" % (stem, ext))
        if os.path.exists(p):
            d = md("diagnose", p)
            verify[ext] = {"bytes": os.path.getsize(p),
                           "watertight": d.get("is_watertight"),
                           "faces": d.get("faces"),
                           "boundary_edges": d.get("boundary_edges"),
                           "nonmanifold_edges": d.get("nonmanifold_edges"),
                           "volume_cm3": d.get("volume_cm3") or d.get("volume"),
                           "bbox": d.get("bbox") or d.get("extents")}
            log("  %-4s watertight=%s faces=%s" % (ext, verify[ext]["watertight"],
                                                   verify[ext]["faces"]))
    write_json(os.path.join(PRINT, "VERIFY.json"), verify)
    mp("render", solid, "--name", stem, "--outdir", os.path.join(PRINT, "views"),
       "--size", "520", "--frames", "8", "--up", "z", "--json")
    card = os.path.join(PRINT, "PRINT_CARD.md")
    mp("card", "--solidify", os.path.join(PWORK, "%s_solidify.json" % stem),
       "--audit", os.path.join(PWORK, "%s_audit.json" % stem),
       "--export", os.path.join(PWORK, "%s_export.json" % stem),
       "--primary", "%s.stl" % stem, "--out", card)
    # mesh_prep.card hardcodes "TERRA" in its H1 - it was written for one figure and
    # has no --title. mesh_prep belongs to another agent and is not edited here, so
    # the heading is corrected on the OUTPUT FILE, which this tool owns.
    if os.path.exists(card):
        with open(card, encoding="utf-8") as f:
            txt = f.read()
        if txt.startswith("# TERRA"):
            txt = txt.replace("# TERRA - print card",
                              "# THE STAND-IN - print card\n\n"
                              "*Anime-first arm (B_anime). The photo-direct control is "
                              "measured at `_work/CONTROL_photo_150mm_audit.json`; see "
                              "`../mesh/VERDICT.json` for why this one shipped.*", 1)
            with open(card, "w", encoding="utf-8") as f:
                f.write(txt)
            log("  corrected the card heading (mesh_prep hardcodes TERRA)")
    return 0


# ---------------------------------------------------------------------------
# report
# ---------------------------------------------------------------------------

def stage_report(args):
    ensure_dirs()
    rep = {
        "question": "does photo -> anime -> mesh beat photo -> mesh?",
        "held_constant": {"plate": PLATE_NAME, "plate_px": PLATE_PX,
                          "margin": MARGIN, "crop": "center", "views": "single",
                          "latent": LATENT, "seed": SEED, "steps": STEPS,
                          "cfg": CFG, "octree": OCTREE, "threshold": THRESHOLD,
                          "algorithm": ALGO},
        "prep": read_json(os.path.join(MESH, "PREP.json")),
        "gen": read_json(os.path.join(WORK, "gen.json")),
        "diagnose": read_json(os.path.join(MESH, "DIAGNOSE.json")),
        "render": read_json(os.path.join(WORK, "render.json")),
        "sheets": read_json(os.path.join(WORK, "sheets.json")),
        "print_verify": read_json(os.path.join(PRINT, "VERIFY.json")),
    }
    write_json(os.path.join(MESH, "REPORT.json"), rep)
    return 0


# ---------------------------------------------------------------------------

def main(argv=None):
    ap = argparse.ArgumentParser(
        description=__doc__.split("\n")[0],
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="stages: prep gen diagnose render sheet print report")
    sub = ap.add_subparsers(dest="cmd")

    sub.add_parser("prep", help="matte the anime seed, build the two square plates")
    g = sub.add_parser("gen", help="Hunyuan3D on both arms, one batch")
    g.add_argument("--force", action="store_true")
    g.add_argument("--timeout", type=float, default=5400.0)
    g.add_argument("--max-resubmit", type=int, default=6)
    sub.add_parser("diagnose", help="mesh_doctor diagnose/thickness/overhang, both arms")
    r = sub.add_parser("render", help="orbit + head strips, both arms")
    r.add_argument("--size", type=int, default=520)
    r.add_argument("--frames", type=int, default=8)
    r.add_argument("--up", default="auto", choices=["auto", "x", "y", "z"])
    s = sub.add_parser("sheet", help="the argument sheet plus hair/hands close reads")
    s.add_argument("--up", default="auto", choices=["auto", "x", "y", "z"])
    p = sub.add_parser("print", help="winner -> solid -> STL/3MF/GLB, each re-verified")
    p.add_argument("--arm", required=True, choices=[a for a, _ in ARMS])
    p.add_argument("--name", default="STANDIN_150mm")
    p.add_argument("--up", default="y", choices=["auto", "x", "y", "z"])
    p.add_argument("--force", action="store_true")
    p.add_argument("--no-export", action="store_true",
                   help="solidify + audit only - how the losing arm is measured")
    sub.add_parser("report", help="assemble mesh/REPORT.json")

    a = ap.parse_args(argv)
    if not a.cmd:
        ap.print_help()
        return 2
    return {"prep": stage_prep, "gen": stage_gen, "diagnose": stage_diagnose,
            "render": stage_render, "sheet": stage_sheet, "print": stage_print,
            "report": stage_report}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
