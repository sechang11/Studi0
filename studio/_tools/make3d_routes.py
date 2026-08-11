#!/usr/bin/env python3
"""studio/_tools/make3d_routes.py - the payload and jobs behind /make3d.

    python3 studio/_tools/make3d_routes.py            a human summary of the presets

WHAT CHANGED, AND WHY IT IS THE WHOLE POINT OF THIS PAGE.

Hunyuan3D HAS NO TEXT ENCODER. Read the graph: LoadImage -> CLIPVisionEncode ->
Hunyuan3Dv2Conditioning -> KSampler. Nowhere does a string reach the model. The
`source_prompt` on every preset card was never fed to the mesh model - it was fed to an
IMAGE model, whose picture was then meshed. So "can I use an image instead of text" is not
a new feature request: text was always the detour. Handing it your own image removes a
lossy generation step rather than adding a path.

MULTI-VIEW IS OFFERED AS OFF, WITH THE REASON, BECAUSE IT DOES NOT WORK ON THIS BOX.
studio/samples/terra_3d/mesh/VERDICT.md section 3 measured it: `Hunyuan3Dv2ConditioningMultiView`
fed four normalised cardinals returned 12,108 faces in 134 islands, 26% non-manifold -
noise, not a worse mesh. The decisive cell was MV1_single_img: the SAME pixels that make an
excellent figure through the single-view node make specks through the multi-view node. The
node adds a sincos view embedding that belongs to the Hunyuan3D-2mv checkpoint; this box
has hunyuan_3d_v2.1, which has never seen one. Tiling four views into one image fails too -
CLIP-vision does not decompose a contact sheet into viewpoints.

That is why the page states the requirement instead of exposing a switch that returns
rubbish. This project has already shipped a wizard offering three cameras that did nothing.

THE GRAPH IS terra_mesh.graph_hunyuan, NOT A COPY OF IT. An earlier draft of this file
rebuilt the same node wiring by hand; that is how a project ends up with two graphs that
drift. One builder, called from here.
"""
import argparse, glob, json, os, re, sys, threading, time

TOOLS = os.path.dirname(os.path.abspath(__file__))
STUDIO = os.path.dirname(TOOLS)
ROOT = os.path.dirname(STUDIO)
MESH_CARDS = os.path.join(STUDIO, "mesh")
UPLOADS = os.path.join(STUDIO, "uploads")
OUT = os.path.join(STUDIO, "samples", "make3d")

JOBS = {}
_LOCK = threading.Lock()

# Defaults that were MEASURED as the winning recipe in terra_3d/mesh/VERDICT.md section 1,
# not guessed. threshold 0.45 and octree 512 beat the template's 0.6/256 on a real figure.
DEFAULTS = {"latent_resolution": 4096, "octree_resolution": 512,
            "threshold": 0.45, "algorithm": "surface net", "steps": 30, "cfg": 5.0}

# Every dial, in the words of what it does to the object you hold. These are the tooltips.
DIALS = {
    "latent_resolution": (
        "How much shape budget the model gets before anything is turned into a surface. "
        "4096 is the measured sweet spot here. Lower loses small features; higher costs "
        "VRAM without a visible gain on a single figure."),
    "octree_resolution": (
        "How finely the shape field is sampled when it becomes geometry. 512 resolves a "
        "face; 256 is faster and reads blockier. This is the dial you raise when detail "
        "is missing, and it is the main cost driver."),
    "threshold": (
        "Where the surface is judged to be. LOWER keeps thin parts - a blade, a ribbon, a "
        "finger - that a higher value erodes to nothing. HIGHER gives a cleaner, chunkier "
        "solid. 0.45 rescued a longsword blade that vanished at 0.6."),
    "algorithm": (
        "How the sampled field is turned into triangles. `surface net` is smooth and "
        "rounds every hard edge - it cannot give you a sharp bevel at any setting. "
        "`marching cubes` is the blockier classic."),
    "steps": "Sampler steps. 30 is the measured default; more has not paid here.",
    "cfg": ("How hard the model is pushed toward the image. 5.0 measured best. Higher "
            "tends to exaggerate and distort rather than sharpen."),
}

CROP = {
    "center": ("Squashes to square by cutting the middle out. MEASURED on a 1664x2432 "
               "portrait: it removes 15.8% off the top AND bottom - the top of a hairband "
               "and the tips of boots. The mesh survives but comes back stockier, with "
               "11 surface islands instead of 1."),
    "none": ("Letterboxes instead of cutting. Safer for a tall subject. The other fix is "
             "to pad your image square yourself before uploading."),
}


def presets():
    """The mesh cards ARE the presets. They already carry the honest text a tooltip
    wants - what it is for, what it is NOT for, and the trap in it - so nothing here is
    re-authored; it is read."""
    out = []
    for p in sorted(glob.glob(os.path.join(MESH_CARDS, "*.json"))):
        if os.path.basename(p).startswith("_"):
            continue
        try:
            c = json.load(open(p, encoding="utf-8"))
        except Exception:
            continue
        d = dict(DEFAULTS)
        d.update(c.get("dials") or {})
        for k in ("steps", "cfg"):
            if c.get(k) is not None:
                d[k] = c[k]
        out.append({
            "id": c.get("id", os.path.basename(p)[:-5]),
            "desc": c.get("desc", ""), "status": c.get("status", ""),
            "dials": d,
            "source_prompt": c.get("source_prompt", ""),
            "output": c.get("output", ""),
            "usable_for": c.get("usable_for", ""),
            "not_usable_for": c.get("not_usable_for", ""),
            "note": c.get("note", ""),
        })
    return out


def payload():
    return {
        "presets": presets(),
        "dial_help": DIALS,
        "crop_help": CROP,
        "defaults": DEFAULTS,
        "multiview": {
            "available": False,
            "needs": "a hunyuan3d-2mv checkpoint in ComfyUI/models/checkpoints/",
            "why": ("MEASURED in studio/samples/terra_3d/mesh/VERDICT.md section 3. The "
                    "MultiView node fed four cardinals returned 12,108 faces in 134 "
                    "islands, 26% non-manifold - noise, not a worse mesh. The same pixels "
                    "through the single-view node make an excellent figure, so the node "
                    "is the variable, not the images. It adds a view embedding that "
                    "belongs to the 2mv checkpoint; this box has the single-view 2.1."),
            "also_fails": ("Tiling four views into one image and sending it down the "
                           "ordinary path: 1.16M faces of floating slabs. CLIP-vision "
                           "does not decompose a contact sheet into viewpoints."),
        },
        "text_input": {
            "supported": False,
            "why": ("Hunyuan3D has no text encoder - the graph is LoadImage -> "
                    "CLIPVisionEncode -> conditioning. A preset's source_prompt is fed to "
                    "an IMAGE model first, and that picture is what gets meshed. Giving it "
                    "your own image removes that step rather than adding one."),
        },
    }


def _job(jid, img_name, dials, crop, seed):
    """Run one mesh. Progress is written as it happens, so a poll reports the stage the
    job is really in rather than a spinner that means nothing."""
    def mark(**kw):
        with _LOCK:
            JOBS[jid].update(kw)
    try:
        sys.path.insert(0, os.path.join(ROOT, "scripts"))
        sys.path.insert(0, TOOLS)
        os.environ.setdefault("COMFY_HOST", "127.0.0.1:8188")
        import shutil
        from epic import COMFY                                   # noqa: E402
        import terra_mesh                                        # noqa: E402

        src = os.path.join(UPLOADS, img_name)
        if not os.path.isfile(src):
            return mark(state="error", error="the uploaded image is gone: %s" % img_name)

        # Stage where terra_mesh's graph expects to find it: ComfyUI/input/terra3d/.
        stage_dir = os.path.join(COMFY, "input", "terra3d")
        os.makedirs(stage_dir, exist_ok=True)
        staged = "make3d_%s.png" % jid
        shutil.copyfile(src, os.path.join(stage_dir, staged))

        mark(state="meshing", stage="Hunyuan3D")
        g = terra_mesh.graph_hunyuan(
            {"single": staged},
            latent_res=int(dials["latent_resolution"]),
            octree=int(dials["octree_resolution"]),
            threshold=float(dials["threshold"]),
            seed=int(seed), algorithm=dials["algorithm"],
            prefix="claude-generated/make3d/%s" % jid,
            crop=crop, steps=int(dials["steps"]), cfg=float(dials["cfg"]))

        # run_graph returns (outputs, wall_seconds, vram) - not just outputs. Unpacking it
        # as one value handed collect_files a tuple and it died on .items().
        t0 = time.time()
        outs, wall, vram = terra_mesh.run_graph(g, "make3d/%s" % jid)
        files = terra_mesh.collect_files(outs) if outs else []
        mark(vram_mib=(vram or {}).get("peak_mib") if isinstance(vram, dict) else None)
        if not files:
            return mark(state="error", error="the mesh job produced no file")

        # collect_files yields ComfyUI file RECORDS ({filename, subfolder, type}), not
        # paths. terra_mesh.resolve turns one into a path; ensure_local is for a different
        # shape entirely and died on .rpartition when handed the dict.
        os.makedirs(OUT, exist_ok=True)
        src_glb = terra_mesh.resolve(files[0])
        dst = os.path.join(OUT, "%s.glb" % jid)
        if not os.path.isfile(src_glb):
            return mark(state="error", error="the mesh landed somewhere unreadable: %s"
                                             % src_glb)
        shutil.copyfile(src_glb, dst)
        got = dst
        mark(state="diagnosing", stage="mesh_doctor", secs=round(wall, 1))

        # Diagnose through mesh_doctor, the one checker, rather than a second opinion.
        import subprocess
        d = {}
        try:
            r = subprocess.run([sys.executable, os.path.join(TOOLS, "mesh_doctor.py"),
                                "diagnose", got, "--json"],
                               capture_output=True, text=True, cwd=ROOT, timeout=1800)
            d = json.loads(r.stdout[r.stdout.index("{"):r.stdout.rindex("}") + 1])
        except Exception as e:                                    # noqa: BLE001
            d = {"error": str(e)[-200:]}

        mark(state="done",
             glb="/samples/make3d/%s.glb" % jid,
             faces=d.get("faces"), watertight=d.get("is_watertight"),
             components=d.get("components"),
             printable=d.get("printable"),
             blocking=d.get("blocking") or [], warnings=d.get("warnings") or [],
             mm=[round(float(x), 2) for x in (d.get("extents") or [])])
    except Exception as e:                                        # noqa: BLE001
        import traceback
        mark(state="error", error="%s: %s" % (type(e).__name__, e),
             trace=traceback.format_exc()[-1200:])


def mesh(data):
    img = re.sub(r"[^A-Za-z0-9._-]", "_", str(data.get("image") or ""))
    if not img:
        return {"error": "no image - upload one first"}, 400
    dials = dict(DEFAULTS)
    dials.update({k: v for k, v in (data.get("dials") or {}).items() if k in DEFAULTS})
    crop = data.get("crop") if data.get("crop") in ("center", "none") else "center"
    try:
        seed = int(data.get("seed") or 777)
    except Exception:
        seed = 777
    jid = "m3d_%d" % (int(time.time() * 1000) % 10 ** 9)
    with _LOCK:
        JOBS[jid] = {"state": "queued", "job": jid, "image": img,
                     "dials": dials, "crop": crop, "seed": seed}
    threading.Thread(target=_job, args=(jid, img, dials, crop, seed),
                     daemon=True).start()
    return {"ok": True, "job": jid}, 200


def job_status(job):
    with _LOCK:
        j = JOBS.get(job)
    return (j or {"error": "no such job"}), (200 if j else 404)


def main():
    argparse.ArgumentParser().parse_args()
    ps = presets()
    print("  %d mesh presets" % len(ps))
    for p in ps:
        print("    %-24s %-9s thr %.2f  octree %s"
              % (p["id"][:24], p["status"], p["dials"]["threshold"],
                 p["dials"]["octree_resolution"]))
    print("\n  text input : NOT supported - Hunyuan3D has no text encoder")
    print("  multi-view : NOT available - needs a hunyuan3d-2mv checkpoint")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
