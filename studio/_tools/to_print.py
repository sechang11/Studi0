#!/usr/bin/env python3
"""studio/_tools/to_print.py - a generated .glb to something a Bambu X1C can print.

    python3 studio/_tools/to_print.py studio/samples/make3d/m3d_123.glb
    python3 studio/_tools/to_print.py mesh.glb --height 120 --name owl
    python3 studio/_tools/to_print.py mesh.glb --no-repair      # already a solid

WHY THIS EXISTS. A GLB is not a printable file. It is a rendering format: it can be an
open surface, it can be inside-out, it can be 47,000 disconnected shells, and it carries no
real-world size - Hunyuan3D output measures about 2 units across whatever the subject is.
Bambu Studio will happily import one and slice nonsense from it.

So this runs the route that was MEASURED to work on this box, recorded in
studio/samples/terra_3d/mesh/VERDICT.md, and refuses to pretend when it fails:

    repair  --method voxel --voxel-res 900   NOT the default 320
    export  --height <mm> --up y             to .3mf AND .stl

THE VOXEL RESOLUTION IS THE WHOLE FINDING. At the default 320 one voxel is 0.47 mm at
150 mm tall, and a face comes back as a terraced Minecraft mass with no eyes and no nose.
It is watertight and it is ruined - the exact failure this project keeps meeting, where the
check passes and the thing is wrong. 900 costs about 40 s and ~11 GB of host RAM.

3MF IS THE FORMAT TO HAND BAMBU STUDIO, not STL. It carries units and orientation
explicitly, so the model arrives at the size you meant. The STL is written alongside for
any other slicer.
"""
import argparse, json, os, subprocess, sys, time

TOOLS = os.path.dirname(os.path.abspath(__file__))
STUDIO = os.path.dirname(TOOLS)
ROOT = os.path.dirname(STUDIO)
OUT = os.path.join(STUDIO, "samples", "print_ready")
MD = os.path.join(TOOLS, "mesh_doctor.py")

# The X1C build volume. Anything past this cannot print in one piece, and saying so here is
# cheaper than finding out after a slice.
BED = (256.0, 256.0, 256.0)


def md(*args, timeout=2400):
    r = subprocess.run([sys.executable, MD] + list(args),
                       capture_output=True, text=True, cwd=ROOT, timeout=timeout)
    return r


def diagnose(path):
    r = md("diagnose", path, "--json")
    try:
        return json.loads(r.stdout[r.stdout.index("{"):r.stdout.rindex("}") + 1])
    except Exception:
        return {"error": (r.stderr.strip() or "mesh_doctor could not read it")[-200:]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mesh")
    ap.add_argument("--height", type=float, default=150.0,
                    help="printed height in mm (default 150)")
    ap.add_argument("--voxel-res", type=int, default=900,
                    help="repair resolution; 900 measured, 320 destroys a face")
    ap.add_argument("--up", default="y", choices=["auto", "x", "y", "z", "none"])
    ap.add_argument("--name")
    ap.add_argument("--no-repair", action="store_true")
    a = ap.parse_args()

    if not os.path.isfile(a.mesh):
        print("  no such mesh: %s" % a.mesh)
        return 1
    name = a.name or os.path.splitext(os.path.basename(a.mesh))[0]
    os.makedirs(OUT, exist_ok=True)

    d0 = diagnose(a.mesh)
    if "error" in d0:
        print("  cannot read the mesh: %s" % d0["error"])
        return 1
    print("  in  : %s faces, watertight=%s, %s parts"
          % (f"{d0.get('faces', 0):,}", d0.get("is_watertight"), d0.get("components")))

    src = a.mesh
    if not a.no_repair and not d0.get("is_watertight"):
        rp = os.path.join(OUT, "%s_repaired.glb" % name)
        print("  repairing at voxel-res %d (this takes a minute and a lot of RAM)…"
              % a.voxel_res)
        t = time.time()
        r = md("repair", a.mesh, "--method", "voxel",
               "--voxel-res", str(a.voxel_res), "--out", rp)
        if r.returncode != 0 or not os.path.isfile(rp):
            print("  REPAIR FAILED: %s" % (r.stderr.strip()[-300:] or "no output written"))
            return 1
        print("  repaired in %.0fs -> %s" % (time.time() - t, os.path.basename(rp)))
        src = rp

    d1 = diagnose(src)
    if not d1.get("is_watertight"):
        # Do not export a non-solid and call it print-ready. mesh_doctor's --force exists,
        # but a slicer given an open surface guesses at what is inside, and the guess is
        # what comes out of the printer.
        print("  STILL NOT WATERTIGHT after repair - not writing a print file.")
        for b in (d1.get("blocking") or [])[:3]:
            print("    · %s" % b)
        print("  Try a higher --voxel-res, or regenerate the mesh at octree 512.")
        return 1

    stl = os.path.join(OUT, "%s_%.0fmm.stl" % (name, a.height))
    tmf = os.path.join(OUT, "%s_%.0fmm.3mf" % (name, a.height))
    r = md("export", src, "--height", str(a.height), "--up", a.up,
           "--out", stl, "--out", tmf)
    if r.returncode != 0:
        print("  EXPORT FAILED: %s" % r.stderr.strip()[-300:])
        return 1

    d2 = diagnose(tmf if os.path.isfile(tmf) else stl)
    mm = [round(float(x), 1) for x in (d2.get("extents") or [])]
    print("\n  out : %s" % tmf)
    print("        %s" % stl)
    print("        %s mm, %s faces, %.1f cm3 solid"
          % (" x ".join("%.1f" % x for x in mm), f"{d2.get('faces', 0):,}",
             (d2.get("volume") or 0) / 1000.0))
    over = [i for i, x in enumerate(mm) if x > BED[i]] if len(mm) == 3 else []
    if over:
        print("        ! bigger than the X1C's 256 x 256 x 256 bed on %d axis(es) - "
              "scale down with --height, or split it in the slicer"
              % len(over))
    print("\n  Open the .3mf in Bambu Studio. It carries units and orientation, so it "
          "arrives at the size meant; the .stl is there for any other slicer.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
