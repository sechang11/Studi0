#!/usr/bin/env python3
"""
terra_mesh.py - generate TERRA's 3D geometry several ways and pick a winner on evidence.

This tool OWNS:
    studio/samples/terra_3d/mesh/*

It reads (never writes) the source set published by studio/_tools/terra_3d_source.py at
studio/samples/terra_3d/source/, and it shells out to studio/_tools/mesh_doctor.py for
every topology / printability number so there is exactly one implementation of those.

STAGES, in run order:

    prep       composite the RGBA sources onto an opaque plate and pad them SQUARE,
               writing into ComfyUI/input/terra3d/.  Square matters: CLIPVisionEncode
               with crop="center" centre-crops to a square, so a 1664x2432 portrait
               would lose 384 px off the top and 384 off the bottom - her head and her
               feet - before the model ever sees her.
    gen        drive Hunyuan3D (workflow 24's graph, rebuilt in memory so the
               multi-view conditioner can be wired) for a named list of candidates.
    splat      drive TripoSplat (workflow 25's graph) for comparison.
    diagnose   run mesh_doctor diagnose/thickness/overhang on every candidate.
    render     turntable + head close-up frame strips and mp4s, by software
               rasterisation - no OpenGL, no Blender, nothing to install.
    report     assemble everything into mesh/REPORT.json and mesh/REPORT.md.

Every subcommand has --help and does nothing else.  A bare invocation prints usage and
exits 2.  All heavy imports (numpy, trimesh, PIL) are lazy, inside the functions that
need them, so --help costs nothing and a missing library cannot stop you reading the
help.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request

HOST = os.environ.get("COMFY_HOST", "127.0.0.1:8188")

HERE = os.path.dirname(os.path.abspath(__file__))
STUDIO = os.path.dirname(HERE)                       # .../studio
ROOT = os.path.dirname(STUDIO)                       # .../comfy-studio
SRC = os.path.join(STUDIO, "samples", "terra_3d", "source")
OUT = os.path.join(STUDIO, "samples", "terra_3d", "mesh")
WORK = os.path.join(OUT, "_work")
MESH_DOCTOR = os.path.join(HERE, "mesh_doctor.py")

COMFY = os.path.expanduser("~/ComfyUI")
COMFY_IN = os.path.join(COMFY, "input", "terra3d")
COMFY_OUT = os.path.join(COMFY, "output")

# The four cardinals the source stage recommended, mapped onto the four slots
# Hunyuan3Dv2ConditioningMultiView actually declares (front, left, back, right).
MV_VIEWS = {
    "front": "mvq_Q0_front_mv.png",
    "left": "mvq_Q2_side_l_mv.png",
    "back": "mvq_Q3_back_mv.png",
    "right": "mvq_Q4_side_r_mv.png",
}
SINGLE = "G_out_dark_s1_rgba.png"

PLATES = {
    "white": (255, 255, 255),
    "grey": (132, 132, 132),      # the #848484 this project uses everywhere
    "black": (0, 0, 0),
    "dark": (24, 34, 60),         # the dark blue plate that saved the forearm
}


# ---------------------------------------------------------------------------
# small utilities
# ---------------------------------------------------------------------------

def log(msg):
    sys.stderr.write("[terra_mesh] %s\n" % msg)
    sys.stderr.flush()


def ensure_dirs():
    for d in (OUT, WORK, COMFY_IN):
        os.makedirs(d, exist_ok=True)


def api(path, payload=None, timeout=120):
    url = "http://%s%s" % (HOST, path)
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        sys.stderr.write(body[:6000] + "\n")
        raise


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


# ---------------------------------------------------------------------------
# VRAM sampler
# ---------------------------------------------------------------------------

class VramWatch(object):
    """Polls nvidia-smi in a thread.  Reports peak and delta over baseline."""

    def __init__(self, period=0.4):
        self.period = period
        self._stop = threading.Event()
        self.samples = []
        self.t = None

    @staticmethod
    def _read():
        try:
            o = subprocess.check_output(
                ["nvidia-smi", "--query-gpu=memory.used",
                 "--format=csv,noheader,nounits"],
                stderr=subprocess.DEVNULL, timeout=10)
            return int(o.decode().strip().splitlines()[0])
        except Exception:
            return None

    def _loop(self):
        while not self._stop.is_set():
            v = self._read()
            if v is not None:
                self.samples.append(v)
            self._stop.wait(self.period)

    def __enter__(self):
        self.baseline = self._read()
        self.t = threading.Thread(target=self._loop, daemon=True)
        self.t.start()
        return self

    def __exit__(self, *a):
        self._stop.set()
        if self.t:
            self.t.join(timeout=3)
        return False

    def result(self):
        if not self.samples:
            return {"peak_mib": None, "baseline_mib": self.baseline,
                    "delta_mib": None, "n_samples": 0}
        peak = max(self.samples)
        return {
            "peak_mib": peak,
            "baseline_mib": self.baseline,
            "delta_mib": (peak - self.baseline) if self.baseline is not None else None,
            "n_samples": len(self.samples),
        }


# ---------------------------------------------------------------------------
# stage: prep
# ---------------------------------------------------------------------------

def alpha_bbox(im):
    a = im.getchannel("A")
    bb = a.getbbox()
    return bb


def composite_square(im, plate, out_w, box=None, margin=0.05):
    """RGBA -> opaque square RGB.

    box: (l, t, r, b) crop applied BEFORE squaring.  Passing the SAME box for
    every view of a turnaround is what preserves scale agreement between them -
    a per-view alpha bbox would silently rescale each view independently.
    """
    from PIL import Image
    if im.mode != "RGBA":
        im = im.convert("RGBA")
    if box is not None:
        im = im.crop(box)
    w, h = im.size
    side = max(w, h)
    pad = int(round(side * margin))
    side = side + 2 * pad
    canvas = Image.new("RGBA", (side, side), plate + (255,))
    canvas.paste(im, ((side - w) // 2, (side - h) // 2), im)
    canvas = canvas.convert("RGB")
    if out_w and out_w != side:
        canvas = canvas.resize((out_w, out_w), Image.LANCZOS)
    return canvas


def stage_prep(args):
    from PIL import Image
    ensure_dirs()
    plate = PLATES[args.plate]
    made = {}

    # -- single view -------------------------------------------------------
    sp = os.path.join(SRC, args.single)
    im = Image.open(sp).convert("RGBA")
    bb = alpha_bbox(im)
    box = bb if args.fit == "bbox" else None
    sq = composite_square(im, plate, args.size, box=box, margin=args.margin)
    name = "terra_single_%s_%s.png" % (args.plate, args.fit)
    sq.save(os.path.join(COMFY_IN, name))
    made["single"] = {
        "file": name, "src": args.single, "src_px": list(im.size),
        "alpha_bbox": list(bb) if bb else None, "out_px": list(sq.size),
    }

    # the deliberate control: the SAME image left portrait, so the finding that
    # centre-crop mutilates it is measured rather than asserted.
    flat = Image.new("RGBA", im.size, plate + (255,))
    flat.paste(im, (0, 0), im)
    flat.convert("RGB").save(os.path.join(COMFY_IN, "terra_single_portrait.png"))
    made["single_portrait"] = {
        "file": "terra_single_portrait.png", "out_px": list(im.size),
        "why": "control - fed to CLIPVisionEncode crop=center to measure what the "
               "centre crop costs",
    }

    # -- multi view --------------------------------------------------------
    mv = {}
    ims = {}
    for slot, fn in MV_VIEWS.items():
        p = os.path.join(SRC, "multiview_qwen", fn)
        ims[slot] = Image.open(p).convert("RGBA")
    if args.fit == "bbox":
        boxes = [alpha_bbox(v) for v in ims.values()]
        ubox = (min(b[0] for b in boxes), min(b[1] for b in boxes),
                max(b[2] for b in boxes), max(b[3] for b in boxes))
    else:
        ubox = None
    for slot, v in ims.items():
        sq = composite_square(v, plate, args.size, box=ubox, margin=args.margin)
        nm = "terra_mv_%s_%s_%s.png" % (slot, args.plate, args.fit)
        sq.save(os.path.join(COMFY_IN, nm))
        mv[slot] = {"file": nm, "src": MV_VIEWS[slot],
                    "src_px": list(v.size), "out_px": list(sq.size)}
    made["multiview"] = mv

    # -- the four cardinals tiled into ONE square image ----------------------
    # A fallback route for putting several angles in front of a model whose
    # conditioning node only accepts one image.
    side = args.size or 1024
    grid = Image.new("RGB", (side, side), plate)
    for i, slot in enumerate(("front", "left", "back", "right")):
        t = Image.open(os.path.join(COMFY_IN, mv[slot]["file"])).convert("RGB")
        t = t.resize((side // 2, side // 2), Image.LANCZOS)
        grid.paste(t, ((i % 2) * (side // 2), (i // 2) * (side // 2)))
    gname = "terra_grid2x2_%s.png" % args.plate
    grid.save(os.path.join(COMFY_IN, gname))
    made["grid2x2"] = {"file": gname, "out_px": [side, side],
                       "order": ["front", "left", "back", "right"]}

    made["multiview_shared_box"] = list(ubox) if ubox else None
    made["_note_shared_box"] = (
        "One crop rectangle, the union of the four alpha bboxes, applied to all four "
        "views. A per-view bbox would rescale each view independently and destroy the "
        "scale agreement the source stage was built to give us."
    )
    made["plate"] = {"name": args.plate, "rgb": list(plate)}
    made["margin"] = args.margin
    made["fit"] = args.fit
    p = write_json(os.path.join(WORK, "prep.json"), made)
    log("prep -> %s" % p)
    print(json.dumps(made, indent=2))
    return 0


# ---------------------------------------------------------------------------
# workflow graphs
# ---------------------------------------------------------------------------

def graph_hunyuan(images, latent_res, octree, threshold, seed, algorithm,
                  prefix, crop="center", steps=30, cfg=5.0):
    """images: {"single": name} or {"front":..., "left":..., "back":..., "right":...}"""
    g = {
        "1": {"class_type": "ImageOnlyCheckpointLoader",
              "inputs": {"ckpt_name": "hunyuan_3d_v2.1.safetensors"}},
        "3": {"class_type": "ModelSamplingAuraFlow",
              "inputs": {"model": ["1", 0], "shift": 1.0}},
        "6": {"class_type": "EmptyLatentHunyuan3Dv2",
              "inputs": {"resolution": latent_res, "batch_size": 1}},
        "7": {"class_type": "KSampler",
              "inputs": {"model": ["3", 0], "seed": seed, "steps": steps,
                         "cfg": cfg, "sampler_name": "euler",
                         "scheduler": "normal",
                         "positive": ["5", 0], "negative": ["5", 1],
                         "latent_image": ["6", 0], "denoise": 1.0}},
        "8": {"class_type": "VAEDecodeHunyuan3D",
              "inputs": {"samples": ["7", 0], "vae": ["1", 2],
                         "num_chunks": 8000, "octree_resolution": octree}},
        "9": {"class_type": "VoxelToMesh",
              "inputs": {"voxel": ["8", 0], "algorithm": algorithm,
                         "threshold": threshold}},
        "10": {"class_type": "SaveGLB",
               "inputs": {"mesh": ["9", 0], "filename_prefix": prefix}},
    }
    if "single" in images:
        g["2"] = {"class_type": "LoadImage",
                  "inputs": {"image": "terra3d/" + images["single"]}}
        g["4"] = {"class_type": "CLIPVisionEncode",
                  "inputs": {"clip_vision": ["1", 1], "image": ["2", 0],
                             "crop": crop}}
        g["5"] = {"class_type": "Hunyuan3Dv2Conditioning",
                  "inputs": {"clip_vision_output": ["4", 0]}}
    else:
        mv_inputs = {}
        n = 100
        for slot in ("front", "left", "back", "right"):
            if slot not in images:
                continue
            li, ce = str(n), str(n + 1)
            n += 2
            g[li] = {"class_type": "LoadImage",
                     "inputs": {"image": "terra3d/" + images[slot]}}
            g[ce] = {"class_type": "CLIPVisionEncode",
                     "inputs": {"clip_vision": ["1", 1], "image": [li, 0],
                                "crop": crop}}
            mv_inputs[slot] = [ce, 0]
        g["5"] = {"class_type": "Hunyuan3Dv2ConditioningMultiView",
                  "inputs": mv_inputs}
    return g


def graph_triposplat(image, num_gaussians, seed, prefix, frames=90):
    return {
        "1": {"class_type": "LoadImage", "inputs": {"image": "terra3d/" + image}},
        "2": {"class_type": "LoadBackgroundRemovalModel",
              "inputs": {"bg_removal_name": "birefnet.safetensors"}},
        "3": {"class_type": "RemoveBackground",
              "inputs": {"bg_removal_model": ["2", 0], "image": ["1", 0]}},
        "4": {"class_type": "TripoSplatPreprocessImage",
              "inputs": {"image": ["1", 0], "mask": ["3", 0],
                         "erode_radius": 1, "size": 1024}},
        "5": {"class_type": "UNETLoader",
              "inputs": {"unet_name": "triposplat_fp16.safetensors",
                         "weight_dtype": "default"}},
        "6": {"class_type": "CLIPVisionLoader",
              "inputs": {"clip_name": "dino_v3_vit_h.safetensors"}},
        "7": {"class_type": "VAELoader", "inputs": {"vae_name": "flux2-vae.safetensors"}},
        "8": {"class_type": "VAELoader",
              "inputs": {"vae_name": "triposplat_vae_decoder_fp16.safetensors"}},
        "9": {"class_type": "TripoSplatConditioning",
              "inputs": {"clip_vision": ["6", 0], "vae": ["7", 0], "image": ["4", 0]}},
        "10": {"class_type": "KSampler",
               "inputs": {"model": ["5", 0], "seed": seed, "steps": 20, "cfg": 3.0,
                          "sampler_name": "dpmpp_2m", "scheduler": "simple",
                          "positive": ["9", 0], "negative": ["9", 1],
                          "latent_image": ["9", 2], "denoise": 1.0}},
        "11": {"class_type": "VAEDecodeTripoSplat",
               "inputs": {"samples": ["10", 0], "vae": ["8", 0],
                          "num_gaussians": num_gaussians, "seed": 790219963981395}},
        "12": {"class_type": "CreateCameraInfo",
               "inputs": {"mode": "orbit", "mode.yaw": 35.0, "mode.pitch": 12.0,
                          "mode.distance": 2.6, "target_x": 0.0, "target_y": 0.0,
                          "target_z": 0.0, "roll": 0.0, "fov": 35.0, "zoom": 1.0,
                          "camera_type": "perspective"}},
        "13": {"class_type": "RenderSplat",
               "inputs": {"splat": ["11", 0], "width": 1024, "height": 1024,
                          "frames": frames, "splat_scale": 1.0, "sharpen": 2.0,
                          "headlight_shading": 0.0, "opacity_threshold": 0.0,
                          "render_style": "color", "background": "#848484",
                          "camera_info": ["12", 0]}},
        "14": {"class_type": "CreateVideo", "inputs": {"images": ["13", 0], "fps": 25.0}},
        "15": {"class_type": "SaveVideo",
               "inputs": {"video": ["14", 0], "filename_prefix": prefix + "_orbit",
                          "format": "auto", "codec": "auto"}},
        "16": {"class_type": "SplatToFile3D", "inputs": {"splat": ["11", 0], "format": "spz"}},
        "17": {"class_type": "SaveGLB",
               "inputs": {"mesh": ["16", 0], "filename_prefix": prefix + "_splat"}},
    }


def run_graph(graph, label, timeout=1800):
    """Submit, wait, return (outputs, wall_seconds, vram)."""
    import uuid
    cid = str(uuid.uuid4())
    t0 = time.time()
    with VramWatch() as vw:
        r = api("/prompt", {"prompt": graph, "client_id": cid})
        pid = r["prompt_id"]
        last = 0.0
        while True:
            time.sleep(1.0)
            h = api("/history/%s" % pid)
            if pid in h:
                st = h[pid].get("status", {})
                if st.get("status_str") == "error" or (
                        st.get("completed") is False and st.get("status_str") == "error"):
                    raise RuntimeError("comfy error for %s: %s" %
                                       (label, json.dumps(st)[:3000]))
                if st.get("completed"):
                    outs = h[pid].get("outputs", {})
                    break
                if st.get("status_str") == "error":
                    raise RuntimeError("comfy error: %s" % json.dumps(st)[:3000])
            if time.time() - t0 > timeout:
                raise RuntimeError("timeout after %.0fs on %s" % (timeout, label))
            if time.time() - last > 30:
                last = time.time()
                log("  %s ... %.0fs" % (label, time.time() - t0))
    wall = time.time() - t0
    return outs, wall, vw.result()


def revive(wait=90):
    """Restart ComfyUI and block until it answers.  Some octree settings kill the
    process outright - no traceback, just a dead socket - so a grid runner has to
    be able to stand it back up."""
    sh = os.path.join(ROOT, "scripts", "restart-comfy.sh")
    subprocess.run(["bash", sh], capture_output=True, text=True, timeout=300)
    for _ in range(wait):
        try:
            api("/system_stats", timeout=5)
            log("  server back up")
            return True
        except Exception:
            time.sleep(1)
    log("  server did NOT come back")
    return False


def collect_files(outs):
    """Pull every file reference out of a history outputs blob."""
    got = []
    for _nid, o in outs.items():
        for key in ("images", "result", "3d", "meshes", "videos", "gltf", "model_file"):
            v = o.get(key)
            if not v:
                continue
            if isinstance(v, list):
                for it in v:
                    if isinstance(it, dict) and "filename" in it:
                        got.append(it)
                    elif isinstance(it, str) and "." in it:
                        got.append({"filename": os.path.basename(it),
                                    "subfolder": os.path.dirname(it), "type": "output"})
    return got


def resolve(f):
    base = COMFY_OUT if f.get("type", "output") == "output" else os.path.join(COMFY, "input")
    return os.path.join(base, f.get("subfolder", ""), f["filename"])


# ---------------------------------------------------------------------------
# the candidate table
# ---------------------------------------------------------------------------

def build_candidates(prep, only=None, plate=None, fit=None):
    plate = plate or prep["plate"]["name"]
    fit = fit or prep["fit"]
    s = prep["single"]["file"]
    mv = {k: v["file"] for k, v in prep["multiview"].items()}
    portrait = prep["single_portrait"]["file"]

    C = []

    def add(name, kind, images, octree, latent=4096, thr=0.6, seed=777,
            algo="surface net", crop="center", why=""):
        C.append({"name": name, "kind": kind, "images": images, "octree": octree,
                  "latent": latent, "threshold": thr, "seed": seed,
                  "algorithm": algo, "crop": crop, "why": why})

    # --- the framing control -------------------------------------------------
    add("A_portrait_crop", "single", {"single": portrait}, 256,
        why="CONTROL. The raw 1664x2432 portrait handed straight to CLIPVisionEncode "
            "with crop=center, i.e. what a naive run of workflow 24 would do. Measures "
            "what the centre crop costs.")
    add("B_square", "single", {"single": s}, 256,
        why="Same seed and settings as A, only the framing changed: padded square first "
            "so the whole figure survives the preprocessor.")

    # --- octree ladder, single view -----------------------------------------
    add("C_s384", "single", {"single": s}, 384,
        why="Octree 384 - the main geometry-detail dial, single view.")
    add("D_s512", "single", {"single": s}, 512,
        why="Octree 512, the node maximum, single view.")

    # --- octree ladder, multi view ------------------------------------------
    add("E_mv256", "multi", mv, 256,
        why="MULTI-VIEW at the same octree as B. The head-to-head nobody here has run.")
    add("F_mv384", "multi", mv, 384, why="Multi-view at octree 384.")
    add("G_mv512", "multi", mv, 512, why="Multi-view at octree 512.")

    # --- WHY multi-view fails: a ladder in the number of views ---------------
    # E came back as a cloud of disconnected specks, not a worse figure.  These
    # three isolate the cause.  Hunyuan3Dv2ConditioningMultiView adds a 1-D
    # sincos view embedding and CONCATENATES the per-view token sequences, so
    # four views hand the sampler a 4x-longer conditioning tensor than the
    # single-view checkpoint has ever seen.  If one view through the same node
    # also fails, the node is incompatible with this checkpoint outright; if one
    # works and four do not, it is the sequence length.
    add("MV1_single_img", "multi", {"front": s}, 256,
        why="DIAGNOSTIC. The MultiView node with ONE slot filled, holding the exact "
            "image B_square used. Same pixels as B, different conditioning node - so "
            "any difference is the node, not the image.")
    add("MV1_mv_img", "multi", {"front": mv["front"]}, 256,
        why="DIAGNOSTIC. One slot, the multi-view front render. Controls for the image "
            "having come from the qwen rotation rather than the original renderer.")
    add("MV2_front_back", "multi", {"front": mv["front"], "back": mv["back"]}, 256,
        why="DIAGNOSTIC. Two slots. Places the failure on the view-count axis.")
    add("MV4_lrswap", "multi",
        {"front": mv["front"], "left": mv["right"], "back": mv["back"],
         "right": mv["left"]}, 256,
        why="DIAGNOSTIC. Four slots with left and right exchanged. The node names its "
            "slots but documents no handedness; if the convention were the only "
            "problem this would differ from E.")

    # --- second-order dials, on the single-view path that actually works -----
    add("H_s384_l8192", "single", {"single": s}, 384, latent=8192,
        why="Latent token count doubled to 8192. Latent resolution and octree "
            "resolution are different dials; this separates them.")
    add("I_s512_thr045", "single", {"single": s}, 512, thr=0.45,
        why="Iso-surface threshold lowered to 0.45. Workflow 24's own notes say lower "
            "this if thin parts go missing - Terra is nothing but thin parts.")
    add("K_s512_thr070", "single", {"single": s}, 512, thr=0.70,
        why="Threshold raised to 0.70, the other end of the same dial.")
    add("J_s512_seed", "single", {"single": s}, 512, seed=12345,
        why="Second seed at the best cell, so run-to-run variance is measured rather "
            "than mistaken for a settings effect.")
    add("L_s512_basic", "single", {"single": s}, 512, algo="basic",
        why="VoxelToMesh algorithm 'basic' instead of 'surface net'. Blockier, but "
            "surface net is the extractor the other agent blamed for 190k "
            "non-manifold edges on the owl - worth one run to see if basic is cleaner.")
    add("N_grid2x2", "single", {"single": prep.get("grid2x2", {}).get("file", s)}, 512,
        why="The four cardinals tiled into ONE square image and fed down the ordinary "
            "single-view path. If the MultiView node is unusable, this is the only "
            "way left to put more than one angle in front of the model.")

    if only:
        want = set(only)
        C = [c for c in C if c["name"] in want or c["name"].split("_")[0] in want]
    return C


# ---------------------------------------------------------------------------
# stage: gen
# ---------------------------------------------------------------------------

def stage_gen(args):
    ensure_dirs()
    prep = read_json(os.path.join(WORK, "prep.json"))
    if not prep:
        log("no prep.json - run `--stage prep` first")
        return 2
    cands = build_candidates(prep, only=args.only)
    if args.list:
        for c in cands:
            print("%-18s %-6s octree=%-4d latent=%-5d thr=%.2f seed=%-6d  %s"
                  % (c["name"], c["kind"], c["octree"], c["latent"],
                     c["threshold"], c["seed"], c["why"][:70]))
        return 0

    runs = read_json(os.path.join(WORK, "gen.json"), {}) or {}
    for c in cands:
        prev = runs.get(c["name"])
        # A cached FAILURE is not a result.  Only a run that produced a mesh is
        # allowed to suppress a re-run, or one crash poisons the whole grid.
        if prev and not prev.get("error") and not args.force:
            log("skip %s (already done)" % c["name"])
            continue
        prefix = "claude-generated/terra3d/%s" % c["name"]
        g = graph_hunyuan(c["images"], c["latent"], c["octree"], c["threshold"],
                          c["seed"], c["algorithm"], prefix, crop=c["crop"])
        log("RUN %s  octree=%d latent=%d thr=%.2f %s"
            % (c["name"], c["octree"], c["latent"], c["threshold"], c["kind"]))
        try:
            outs, wall, vram = run_graph(g, c["name"], timeout=args.timeout)
        except Exception as e:
            msg = str(e)
            log("FAIL %s: %s" % (c["name"], msg[:800]))
            # Some settings take the whole ComfyUI process down rather than
            # raising.  Bring it back so the next candidate still gets a fair
            # run, and record that this cell was the one that killed it.
            killed = "Connection refused" in msg or "timeout" in msg.lower()
            if killed and not args.no_revive:
                log("  server appears dead - restarting and retrying once")
                revive()
                try:
                    outs, wall, vram = run_graph(g, c["name"], timeout=args.timeout)
                    msg = None
                except Exception as e2:
                    msg = str(e2)
                    log("  retry also failed: %s" % msg[:400])
                    revive()
            if msg:
                runs[c["name"]] = dict(c, error=msg[:2000],
                                       killed_server=bool(killed))
                write_json(os.path.join(WORK, "gen.json"), runs)
                continue
        files = collect_files(outs)
        glbs = [resolve(f) for f in files if f["filename"].lower().endswith((".glb", ".gltf"))]
        local = None
        if glbs:
            local = os.path.join(OUT, "%s.glb" % c["name"])
            shutil.copyfile(glbs[0], local)
        rec = dict(c)
        rec.update({"wall_s": round(wall, 2), "vram": vram,
                    "comfy_glb": glbs[0] if glbs else None, "glb": local,
                    "bytes": os.path.getsize(local) if local else None})
        runs[c["name"]] = rec
        write_json(os.path.join(WORK, "gen.json"), runs)
        log("  done %.1fs peak %s MiB -> %s"
            % (wall, vram.get("peak_mib"), os.path.basename(local or "NOTHING")))
    print(json.dumps({k: {kk: vv for kk, vv in v.items() if kk != "images"}
                      for k, v in runs.items()}, indent=2))
    return 0


def stage_splat(args):
    ensure_dirs()
    prep = read_json(os.path.join(WORK, "prep.json"))
    if not prep:
        log("no prep.json")
        return 2
    img = prep["single"]["file"]
    runs = read_json(os.path.join(WORK, "splat.json"), {}) or {}
    for ng in args.gaussians:
        name = "SPLAT_%d" % ng
        if name in runs and not args.force:
            log("skip %s" % name)
            continue
        prefix = "claude-generated/terra3d/%s" % name
        g = graph_triposplat(img, ng, 46, prefix, frames=args.frames)
        log("RUN %s  gaussians=%d" % (name, ng))
        try:
            outs, wall, vram = run_graph(g, name, timeout=args.timeout)
        except Exception as e:
            log("FAIL %s: %s" % (name, str(e)[:800]))
            runs[name] = {"error": str(e)[:2000], "num_gaussians": ng}
            write_json(os.path.join(WORK, "splat.json"), runs)
            continue
        files = collect_files(outs)
        saved = {}
        for f in files:
            p = resolve(f)
            ext = os.path.splitext(p)[1].lower()
            if not os.path.exists(p):
                continue
            dst = os.path.join(OUT, "%s%s" % (name, ext))
            shutil.copyfile(p, dst)
            saved[ext] = {"path": dst, "bytes": os.path.getsize(dst)}
        runs[name] = {"num_gaussians": ng, "wall_s": round(wall, 2), "vram": vram,
                      "files": saved}
        write_json(os.path.join(WORK, "splat.json"), runs)
        log("  done %.1fs peak %s MiB  files=%s"
            % (wall, vram.get("peak_mib"), list(saved)))
    print(json.dumps(runs, indent=2))
    return 0


# ---------------------------------------------------------------------------
# stage: diagnose  (every number comes from mesh_doctor, none from here)
# ---------------------------------------------------------------------------

def md(subcmd, mesh, *extra):
    cmd = [sys.executable, MESH_DOCTOR, subcmd, mesh, "--json"] + list(extra)
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
    out = (p.stdout or "").strip()
    obj = None
    if out:
        # tolerate a leading banner line before the JSON body
        i = out.find("{")
        if i >= 0:
            try:
                obj = json.loads(out[i:])
            except ValueError:
                obj = None
    return {"rc": p.returncode, "json": obj,
            "stderr": (p.stderr or "")[-1500:] if p.returncode else ""}


def stage_diagnose(args):
    ensure_dirs()
    gen = read_json(os.path.join(WORK, "gen.json"), {}) or {}
    targets = []
    for name, rec in sorted(gen.items()):
        if rec.get("glb") and os.path.exists(rec["glb"]):
            targets.append((name, rec["glb"]))
    for p in args.extra or []:
        targets.append((os.path.splitext(os.path.basename(p))[0], p))
    if args.only:
        want = set(args.only)
        targets = [t for t in targets if t[0] in want]

    diag = read_json(os.path.join(WORK, "diag.json"), {}) or {}
    for name, path in targets:
        if name in diag and not args.force:
            log("skip diagnose %s" % name)
            continue
        log("diagnose %s" % name)
        rec = {"path": path, "bytes": os.path.getsize(path)}
        t0 = time.time()
        rec["raw"] = md("diagnose", path)
        if args.repair:
            fixed = os.path.join(OUT, "%s_fixed.glb" % name)
            log("  repair -> %s" % os.path.basename(fixed))
            rp = subprocess.run(
                [sys.executable, MESH_DOCTOR, "repair", path, "--out", fixed,
                 "--json"] + (["--voxel-res", str(args.voxel_resolution)]
                              if args.voxel_resolution else []),
                capture_output=True, text=True, timeout=7200)
            rec["repair_rc"] = rp.returncode
            rec["repair_stderr"] = (rp.stderr or "")[-1500:]
            if os.path.exists(fixed):
                rec["fixed"] = fixed
                rec["fixed_bytes"] = os.path.getsize(fixed)
                rec["fixed_diag"] = md("diagnose", fixed)
                rec["thickness"] = md("thickness", fixed, "--height",
                                      str(args.height), "--up", args.up,
                                      "--min-mm", str(args.min_mm),
                                      "--samples", str(args.samples))
                rec["overhang"] = md("overhang", fixed, "--height", str(args.height),
                                     "--up", args.up)
        rec["seconds"] = round(time.time() - t0, 1)
        diag[name] = rec
        write_json(os.path.join(WORK, "diag.json"), diag)
    print(json.dumps({k: _diag_row(k, v) for k, v in sorted(diag.items())}, indent=2))
    return 0


def _dig(d, *path):
    cur = d
    for k in path:
        if not isinstance(cur, dict) or k not in cur:
            return None
        cur = cur[k]
    return cur


def _diag_row(name, rec):
    r = _dig(rec, "raw", "json") or {}
    f = _dig(rec, "fixed_diag", "json") or {}
    t = _dig(rec, "thickness", "json") or {}
    o = _dig(rec, "overhang", "json") or {}
    # Key names are mesh_doctor's own, verified against a dumped diagnose blob -
    # guessing at them is how a report ends up full of nulls that look like
    # missing measurements rather than a broken reader.
    return {
        "raw_faces": r.get("faces"),
        "raw_watertight": r.get("is_watertight"),
        "raw_nonmanifold": r.get("nonmanifold_edges"),
        "raw_nonmanifold_pct": (round(r["nonmanifold_fraction"] * 100, 2)
                                if r.get("nonmanifold_fraction") is not None else None),
        "raw_boundary": r.get("boundary_edges"),
        "raw_islands": r.get("vertex_components"),
        "raw_islands_under_1pct": r.get("vertex_components_under_1pct"),
        "raw_volume": r.get("volume"),
        "fixed_faces": f.get("faces"),
        "fixed_watertight": f.get("is_watertight"),
        "fixed_islands": f.get("vertex_components"),
        "fixed_volume": f.get("volume"),
        "fixed_blocking": f.get("blocking"),
        "thickness_p50_mm": _dig(t, "percentiles", "50"),
        "thickness_p10_mm": _dig(t, "percentiles", "10"),
        "thickness_frac_under_1mm": t.get("fraction_below_min"),
        "thickness_trusted": t.get("input_watertight"),
        "overhang_area_frac": o.get("overhang_area_fraction"),
        "flat_ceiling_frac": o.get("flat_ceiling_area_fraction"),
        "bed_contact_mm2": o.get("bed_contact_area"),
    }


def _first(d, *keys):
    if not isinstance(d, dict):
        return None
    for k in keys:
        if k in d:
            return d[k]
    for v in d.values():
        if isinstance(v, dict):
            got = _first(v, *keys)
            if got is not None:
                return got
    return None


# ---------------------------------------------------------------------------
# stage: render - software point-splat rasteriser
# ---------------------------------------------------------------------------

def _axis_index(name):
    return {"x": 0, "y": 1, "z": 2}[name]


def _sample_mesh(path, n, seed=0):
    import numpy as np
    import trimesh
    m = trimesh.load(path, force="mesh", process=False)
    if m.faces is None or len(m.faces) == 0:
        raise RuntimeError("no faces in %s" % path)
    rs = np.random.RandomState(seed)
    pts, fid = trimesh.sample.sample_surface(m, n, seed=seed) if _accepts_seed() \
        else _sample_fallback(m, n, rs)
    nrm = m.face_normals[fid]
    return (np.asarray(pts, dtype="float32"), np.asarray(nrm, dtype="float32"),
            np.asarray(m.bounds, dtype="float64"), len(m.faces), len(m.vertices))


def _accepts_seed():
    import inspect
    import trimesh
    try:
        return "seed" in inspect.signature(trimesh.sample.sample_surface).parameters
    except (TypeError, ValueError):
        return False


def _sample_band(path, uidx, frac, n, seed=1):
    """Slice off the top `frac` of the mesh along axis uidx and sample THAT with
    the full point budget, so a close-up is resolved rather than speckled."""
    import numpy as np
    import trimesh
    m = trimesh.load(path, force="mesh", process=False)
    b = m.bounds
    ext = b[1] - b[0]
    normal = np.zeros(3)
    normal[uidx] = 1.0
    origin = np.zeros(3)
    origin[uidx] = b[1][uidx] - ext[uidx] * frac
    sub = trimesh.intersections.slice_mesh_plane(
        m, plane_normal=normal, plane_origin=origin, cap=False)
    if sub is None or len(getattr(sub, "faces", [])) < 100:
        raise RuntimeError("slice produced nothing")
    pts, fid = trimesh.sample.sample_surface(sub, n)
    return (np.asarray(pts, dtype="float32"),
            np.asarray(sub.face_normals[fid], dtype="float32"))


def _sample_fallback(m, n, rs):
    import numpy as np
    area = m.area_faces
    p = area / area.sum()
    fid = rs.choice(len(p), size=n, p=p)
    tri = m.triangles[fid]
    u = rs.random_sample((n, 1))
    v = rs.random_sample((n, 1))
    over = (u + v) > 1
    u[over] = 1 - u[over]
    v[over] = 1 - v[over]
    pts = tri[:, 0] + u * (tri[:, 1] - tri[:, 0]) + v * (tri[:, 2] - tri[:, 0])
    return pts, fid


def _render_frame(pts, nrm, centre, half, up, az_deg, el_deg, size, ss, style):
    """Orthographic point-splat with a painter's-algorithm depth sort."""
    import numpy as np
    u = up
    a, b = [i for i in (0, 1, 2) if i != u]        # the two horizontal axes
    P = pts - centre
    N = nrm
    ca, sa = np.cos(np.radians(az_deg)), np.sin(np.radians(az_deg))
    # screen basis: X = right, Y = up, Z = toward camera
    sx = ca * P[:, a] - sa * P[:, b]
    sz = sa * P[:, a] + ca * P[:, b]
    sy = P[:, u].copy()
    nx = ca * N[:, a] - sa * N[:, b]
    nz = sa * N[:, a] + ca * N[:, b]
    ny = N[:, u].copy()
    if el_deg:
        ce, se = np.cos(np.radians(el_deg)), np.sin(np.radians(el_deg))
        sy, sz = ce * sy - se * sz, se * sy + ce * sz
        ny, nz = ce * ny - se * nz, se * ny + ce * nz

    W = H = size * ss
    scale = (W * 0.46) / half
    px = np.rint(sx * scale + W * 0.5).astype("int64")
    py = np.rint(H * 0.5 - sy * scale).astype("int64")
    ok = (px >= 0) & (px < W) & (py >= 0) & (py < H)
    px, py, sz = px[ok], py[ok], sz[ok]
    nx, ny, nz = nx[ok], ny[ok], nz[ok]

    if style == "normal":
        col = np.stack([nx * 0.5 + 0.5, ny * 0.5 + 0.5, nz * 0.5 + 0.5], axis=1)
    else:
        L1 = np.array([-0.45, 0.60, 0.66], dtype="float32")
        L1 /= np.linalg.norm(L1)
        L2 = np.array([0.70, 0.10, 0.40], dtype="float32")
        L2 /= np.linalg.norm(L2)
        nn = np.stack([nx, ny, nz], axis=1)
        d1 = np.clip(nn @ L1, 0, 1)
        d2 = np.clip(nn @ L2, 0, 1)
        rim = np.clip(1.0 - np.abs(nz), 0, 1) ** 3
        lum = 0.16 + 0.70 * d1 + 0.22 * d2 + 0.25 * rim
        lum = np.clip(lum, 0, 1) ** (1 / 2.2)
        col = np.stack([lum * 1.00, lum * 0.97, lum * 0.93], axis=1)
    col = (np.clip(col, 0, 1) * 255).astype("uint8")

    buf = np.full((H * W, 3), 236, dtype="uint8")
    order = np.argsort(sz, kind="stable")          # far first, near last wins
    flat = (py * W + px)[order]
    buf[flat] = col[order]
    return buf.reshape(H, W, 3)


def _to_pil(arr, size, ss):
    from PIL import Image
    im = Image.fromarray(arr)
    if ss > 1:
        im = im.resize((size, size), Image.LANCZOS)
    return im


def _label(im, text, sub=None):
    from PIL import ImageDraw
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, im.size[0], 20], fill=(28, 28, 34))
    d.text((5, 5), text, fill=(245, 245, 245))
    if sub:
        d.text((im.size[0] - 8 - 6 * len(sub), 5), sub, fill=(170, 190, 220))
    return im


def _strip(images, cols, pad=4, bg=(28, 28, 34)):
    from PIL import Image
    if not images:
        return None
    w, h = images[0].size
    rows = (len(images) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * w + (cols + 1) * pad,
                              rows * h + (rows + 1) * pad), bg)
    for i, im in enumerate(images):
        r, c = divmod(i, cols)
        sheet.paste(im, (pad + c * (w + pad), pad + r * (h + pad)))
    return sheet


def render_one(path, name, outdir, size=460, frames=8, ss=2, up="auto",
               samples=2600000, style="clay", mp4=0, el=8.0):
    import numpy as np
    os.makedirs(outdir, exist_ok=True)
    pts, nrm, bounds, nfaces, nverts = _sample_mesh(path, samples)
    ext = bounds[1] - bounds[0]
    if up == "auto":
        uidx = int(np.argmax(ext))
    else:
        uidx = _axis_index(up)
    centre = (bounds[0] + bounds[1]) / 2.0
    half = float(max(ext)) / 2.0

    az = [i * (360.0 / frames) for i in range(frames)]
    ims = []
    for a in az:
        arr = _render_frame(pts, nrm, centre, half, uidx, a, el, size, ss, style)
        im = _to_pil(arr, size, ss)
        _label(im, "%s  %d deg" % (name, int(a)))
        ims.append(im)
    sheet = _strip(ims, min(frames, 4))
    sheet_p = os.path.join(outdir, "%s_orbit.jpg" % name)
    sheet.save(sheet_p, quality=90)

    # Head close-up.  Reusing the body's point cloud here looks like speckled
    # noise: the head is a quarter of the figure, so it gets a quarter of the
    # samples spread over a full frame, and the sampling noise reads as surface
    # texture that is not there.  Slice the head off and give it the whole
    # budget instead.
    heads = []
    head_p = None
    try:
        hp, hn = _sample_band(path, uidx, 0.26, samples)
    except Exception:
        top = bounds[1][uidx]
        sel = pts[:, uidx] >= (top - ext[uidx] * 0.26)
        hp, hn = pts[sel], nrm[sel]
    if len(hp) > 5000:
        hb = np.stack([hp.min(0), hp.max(0)])
        hc = (hb[0] + hb[1]) / 2.0
        hh = float(max(hb[1] - hb[0])) / 2.0
        for a in (0, 45, 90, 180, 270, 315):
            arr = _render_frame(hp, hn, hc, hh, uidx, a, 0.0, size, ss, style)
            im = _to_pil(arr, size, ss)
            _label(im, "%s head %d deg" % (name, a))
            heads.append(im)
        hs = _strip(heads, 3)
        head_p = os.path.join(outdir, "%s_head.jpg" % name)
        hs.save(head_p, quality=92)

    mp4_p = None
    if mp4:
        fd = os.path.join(outdir, "_frames_%s" % name)
        os.makedirs(fd, exist_ok=True)
        for i in range(mp4):
            a = i * (360.0 / mp4)
            arr = _render_frame(pts, nrm, centre, half, uidx, a, el, size, ss, style)
            _to_pil(arr, size, ss).save(os.path.join(fd, "f%04d.png" % i))
        mp4_p = os.path.join(outdir, "%s_turntable.mp4" % name)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", "24",
                        "-i", os.path.join(fd, "f%04d.png"),
                        "-c:v", "libx264", "-pix_fmt", "yuv420p", mp4_p],
                       check=False, timeout=600)
        shutil.rmtree(fd, ignore_errors=True)

    return {"orbit": sheet_p, "head": head_p, "mp4": mp4_p,
            "up_axis": "xyz"[uidx], "extents": [float(x) for x in ext],
            "faces": nfaces, "vertices": nverts}


def stage_render(args):
    ensure_dirs()
    outdir = os.path.join(OUT, "views")
    gen = read_json(os.path.join(WORK, "gen.json"), {}) or {}
    diag = read_json(os.path.join(WORK, "diag.json"), {}) or {}
    todo = []
    for name, rec in sorted(gen.items()):
        if rec.get("glb") and os.path.exists(rec["glb"]):
            todo.append((name, rec["glb"]))
        if args.fixed:
            fx = _dig(diag, name, "fixed")
            if fx and os.path.exists(fx):
                todo.append((name + "_fixed", fx))
    for p in args.extra or []:
        todo.append((os.path.splitext(os.path.basename(p))[0], p))
    if args.only:
        want = set(args.only)
        todo = [t for t in todo if t[0] in want or t[0].replace("_fixed", "") in want]

    got = read_json(os.path.join(WORK, "render.json"), {}) or {}
    for name, path in todo:
        if name in got and not args.force:
            log("skip render %s" % name)
            continue
        log("render %s" % name)
        t0 = time.time()
        try:
            r = render_one(path, name, outdir, size=args.size, frames=args.frames,
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
    """One sheet: the same azimuth of every candidate side by side."""
    from PIL import Image
    ensure_dirs()
    outdir = os.path.join(OUT, "views")
    gen = read_json(os.path.join(WORK, "gen.json"), {}) or {}
    names = args.only or sorted(k for k, v in gen.items() if v.get("glb"))
    tiles = []
    for name in names:
        rec = gen.get(name, {})
        path = rec.get("glb")
        if not path or not os.path.exists(path):
            continue
        pts, nrm, bounds, nf, nv = _sample_mesh(path, args.samples)
        import numpy as np
        ext = bounds[1] - bounds[0]
        uidx = int(np.argmax(ext)) if args.up == "auto" else _axis_index(args.up)
        centre = (bounds[0] + bounds[1]) / 2.0
        half = float(max(ext)) / 2.0
        for a in args.angles:
            arr = _render_frame(pts, nrm, centre, half, uidx, a, args.elevation,
                                args.size, args.ss, args.style)
            im = _to_pil(arr, args.size, args.ss)
            _label(im, "%s %d" % (name, a), "%dk f" % (nf // 1000))
            tiles.append(im)
    sheet = _strip(tiles, len(args.angles))
    p = os.path.join(outdir, args.name)
    os.makedirs(outdir, exist_ok=True)
    sheet.save(p, quality=90)
    log("contact -> %s" % p)
    print(p)
    return 0


def stage_report(args):
    ensure_dirs()
    gen = read_json(os.path.join(WORK, "gen.json"), {}) or {}
    diag = read_json(os.path.join(WORK, "diag.json"), {}) or {}
    ren = read_json(os.path.join(WORK, "render.json"), {}) or {}
    splat = read_json(os.path.join(WORK, "splat.json"), {}) or {}
    prep = read_json(os.path.join(WORK, "prep.json"), {}) or {}
    rows = []
    for name in sorted(gen):
        g = gen[name]
        row = {"name": name, "kind": g.get("kind"), "octree": g.get("octree"),
               "latent": g.get("latent"), "threshold": g.get("threshold"),
               "seed": g.get("seed"), "why": g.get("why"),
               "wall_s": g.get("wall_s"),
               "vram_peak_mib": _dig(g, "vram", "peak_mib"),
               "glb_bytes": g.get("bytes"), "error": g.get("error")}
        row.update(_diag_row(name, diag.get(name, {})))
        row["orbit_sheet"] = _dig(ren, name, "orbit")
        row["head_sheet"] = _dig(ren, name, "head")
        rows.append(row)
    rep = {"_": "terra_mesh.py report. Numbers from mesh_doctor.py; renders from the "
                "built-in point-splat rasteriser. Verdict text is written by hand into "
                "VERDICT.md after the sheets have been opened.",
           "prep": prep, "candidates": rows, "splat": splat}
    p = write_json(os.path.join(OUT, "REPORT.json"), rep)
    log("report -> %s" % p)
    hdr = ["name", "kind", "octree", "latent", "wall_s", "vram_peak_mib",
           "raw_faces", "raw_watertight", "raw_nonmanifold_pct", "raw_islands",
           "fixed_faces", "fixed_watertight", "fixed_islands",
           "thickness_p50_mm", "thickness_frac_under_1mm",
           "overhang_area_frac", "bed_contact_mm2"]
    print("\t".join(hdr))
    for r in rows:
        print("\t".join(str(r.get(h)) for h in hdr))
    return 0


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="terra_mesh.py",
        description="Generate TERRA's geometry several ways and pick a winner on "
                    "evidence.",
        epilog="Run order: prep, gen, splat, diagnose, render, contact, report.")
    sub = ap.add_subparsers(dest="cmd", metavar="STAGE")

    p = sub.add_parser("prep", help="composite sources onto a plate and pad square")
    p.add_argument("--plate", choices=sorted(PLATES), default="white")
    p.add_argument("--fit", choices=["bbox", "canvas"], default="bbox",
                   help="bbox: crop to the alpha bounding box first (one shared box "
                        "across the multi-view set). canvas: keep the render canvas.")
    p.add_argument("--margin", type=float, default=0.06)
    p.add_argument("--size", type=int, default=1024,
                   help="output square edge (0 = leave native)")
    p.add_argument("--single", default=SINGLE)
    p.set_defaults(fn=stage_prep)

    p = sub.add_parser("gen", help="run Hunyuan3D candidates")
    p.add_argument("--only", nargs="*", help="candidate names")
    p.add_argument("--list", action="store_true", help="print the table and exit")
    p.add_argument("--force", action="store_true")
    p.add_argument("--no-revive", action="store_true",
                   help="do not restart ComfyUI and retry when a cell kills it")
    p.add_argument("--timeout", type=int, default=2400)
    p.set_defaults(fn=stage_gen)

    p = sub.add_parser("splat", help="run TripoSplat for comparison")
    p.add_argument("--gaussians", nargs="*", type=int, default=[262144])
    p.add_argument("--frames", type=int, default=90)
    p.add_argument("--force", action="store_true")
    p.add_argument("--timeout", type=int, default=2400)
    p.set_defaults(fn=stage_splat)

    p = sub.add_parser("diagnose", help="mesh_doctor over every candidate")
    p.add_argument("--only", nargs="*")
    p.add_argument("--extra", nargs="*", help="extra mesh paths")
    p.add_argument("--repair", action="store_true")
    p.add_argument("--voxel-resolution", type=int, default=0)
    p.add_argument("--height", type=float, default=150.0)
    p.add_argument("--up", default="y", choices=["auto", "x", "y", "z"])
    p.add_argument("--min-mm", type=float, default=1.0)
    p.add_argument("--samples", type=int, default=40000)
    p.add_argument("--force", action="store_true")
    p.set_defaults(fn=stage_diagnose)

    p = sub.add_parser("render", help="turntable + head strips per candidate")
    p.add_argument("--only", nargs="*")
    p.add_argument("--extra", nargs="*")
    p.add_argument("--fixed", action="store_true", help="also render repaired meshes")
    p.add_argument("--size", type=int, default=460)
    p.add_argument("--frames", type=int, default=8)
    p.add_argument("--ss", type=int, default=2)
    p.add_argument("--up", default="auto", choices=["auto", "x", "y", "z"])
    p.add_argument("--samples", type=int, default=2600000)
    p.add_argument("--style", default="clay", choices=["clay", "normal"])
    p.add_argument("--elevation", type=float, default=8.0)
    p.add_argument("--mp4", type=int, default=0, help="frame count for an mp4 (0=off)")
    p.add_argument("--force", action="store_true")
    p.set_defaults(fn=stage_render)

    p = sub.add_parser("contact", help="one sheet, all candidates, same angles")
    p.add_argument("--only", nargs="*")
    p.add_argument("--angles", nargs="*", type=int, default=[0, 90, 180])
    p.add_argument("--size", type=int, default=380)
    p.add_argument("--ss", type=int, default=2)
    p.add_argument("--up", default="auto", choices=["auto", "x", "y", "z"])
    p.add_argument("--samples", type=int, default=1800000)
    p.add_argument("--style", default="clay", choices=["clay", "normal"])
    p.add_argument("--elevation", type=float, default=8.0)
    p.add_argument("--name", default="CONTACT.jpg")
    p.set_defaults(fn=stage_contact)

    p = sub.add_parser("report", help="assemble REPORT.json")
    p.set_defaults(fn=stage_report)

    args = ap.parse_args(argv)
    if not getattr(args, "fn", None):
        ap.print_usage(sys.stderr)
        sys.stderr.write("terra_mesh.py: a STAGE is required\n")
        return 2
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
