#!/usr/bin/env python3
"""studio/_tools/previz_blender.py - a physics previz from Blender, as a control video.

WHY. The video engines draw a convincing body and a convincing room, and lose the plot the
moment several things have to move in a physically consistent way at once - a wall of crates
that comes down, a thrown object that lands where it must, a camera that arcs while it happens.
A physics engine does exactly that part for free. So: simulate the beat in Blender with proxy
geometry (boxes, a sphere, a figure made of a cylinder and a ball), render it flat, and hand
that video to the IC-LoRA control workflow (74 on LTX-2.3), which reads its DEPTH and draws the
real scene over it - the crates become crates, the proxy becomes the character, and every
collision lands on the frame the simulation says it lands. Blender is the choreographer; the
engine is the painter.

    python3 studio/_tools/previz_blender.py --out studio/samples/previz/crates --scene crates \
        --seconds 4 --fps 24

Run with plain python it is the WRAPPER: it launches Blender headless on itself (the flatpak
org.blender.Blender on this box, or `blender` on PATH), which renders a PNG sequence, then it
assembles <out>/previz.mp4 with ffmpeg (the flatpak's Blender has no video encoder built in).
Writes 8n+1 frames so LTX takes the clip whole, and <out>/previz.json with the scene's numbers
(the frame the sphere strikes) so a measurement can check the render against the simulation
rather than against an opinion.
"""
import argparse
import json
import math
import os
import subprocess
import sys

try:
    import bpy
    from mathutils import Vector
    IN_BLENDER = True
except ImportError:      # the wrapper, outside Blender
    IN_BLENDER = False


def _wrapper(argv):
    """Outside Blender: run Blender on this file, then encode the frames."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--fps", type=int, default=24)
    a, _ = ap.parse_known_args(argv)
    out = os.path.abspath(os.path.expanduser(a.out))
    os.makedirs(out, exist_ok=True)
    me = os.path.abspath(__file__)
    passthrough = []
    for x in argv:
        passthrough.append(out if (passthrough and passthrough[-1] == "--out") else x)
    if subprocess.run(["which", "blender"], capture_output=True).returncode == 0:
        cmd = ["blender"]
    else:
        cmd = ["flatpak", "run", "org.blender.Blender"]
    cmd += ["-b", "-P", me, "--"] + passthrough
    r = subprocess.run(cmd, capture_output=True, text=True)
    tail = "\n".join(l for l in r.stdout.splitlines() if not l.startswith("Fra:"))[-3000:]
    if r.returncode != 0 or not os.path.isdir(os.path.join(out, "frames")):
        print(tail)
        print(r.stderr[-2000:])
        raise SystemExit("blender failed (%s)" % r.returncode)
    mp4 = os.path.join(out, "previz.mp4")
    e = subprocess.run(["ffmpeg", "-y", "-v", "error", "-framerate", str(a.fps),
                        "-i", os.path.join(out, "frames", "f_%04d.png"),
                        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "16", "-r", str(a.fps), mp4],
                       capture_output=True, text=True)
    if e.returncode != 0:
        raise SystemExit("ffmpeg failed: " + e.stderr[-800:])
    jp = os.path.join(out, "previz.json")
    info = json.load(open(jp)) if os.path.exists(jp) else {}
    info["video"] = mp4
    json.dump(info, open(jp, "w"), indent=1)
    print("previz:", json.dumps(info))


def _interp(mode):
    """Blender 5 keeps F-curves in layered actions (`action.fcurves` is gone), so the interpolation
    of the keyframes about to be inserted is set through the preference instead of edited after."""
    try:
        bpy.context.preferences.edit.keyframe_new_interpolation_type = mode
    except Exception:
        pass


def _args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--scene", default="crates", choices=["crates", "fall"])
    ap.add_argument("--seconds", type=float, default=4.0)
    ap.add_argument("--fps", type=int, default=24)
    ap.add_argument("--width", type=int, default=1280)
    ap.add_argument("--height", type=int, default=704)
    ap.add_argument("--seed", type=int, default=7)
    return ap.parse_args(argv)


def _clear():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    return sc


def _mat(name, rgb):
    m = bpy.data.materials.new(name)
    m.diffuse_color = (*rgb, 1.0)
    return m


def _box(name, loc, size, mat, active=True, mass=1.0):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=loc)
    ob = bpy.context.active_object
    ob.name = name
    ob.scale = size
    ob.data.materials.append(mat)
    bpy.ops.rigidbody.object_add()
    ob.rigid_body.type = "ACTIVE" if active else "PASSIVE"
    ob.rigid_body.mass = mass
    ob.rigid_body.friction = 0.6
    ob.rigid_body.restitution = 0.05
    ob.rigid_body.collision_shape = "BOX"
    return ob


def _sphere(name, loc, r, mat, mass=8.0):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=r, location=loc, segments=24, ring_count=12)
    ob = bpy.context.active_object
    ob.name = name
    ob.data.materials.append(mat)
    bpy.ops.object.shade_smooth()
    bpy.ops.rigidbody.object_add()
    ob.rigid_body.type = "ACTIVE"
    ob.rigid_body.mass = mass
    ob.rigid_body.friction = 0.5
    ob.rigid_body.restitution = 0.2
    ob.rigid_body.collision_shape = "SPHERE"
    return ob


def _figure(name, loc, mat):
    """A standing proxy: a capsule-ish body and a head. Depth reads it as a person-shaped
    volume, which is all the control needs; the prompt says who it is."""
    x, y, z = loc
    bpy.ops.mesh.primitive_cylinder_add(radius=0.22, depth=1.5, location=(x, y, z + 0.75))
    body = bpy.context.active_object
    body.name = name + "_body"
    body.data.materials.append(mat)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.14, location=(x, y, z + 1.65))
    head = bpy.context.active_object
    head.name = name + "_head"
    head.data.materials.append(mat)
    bpy.ops.mesh.primitive_cylinder_add(radius=0.06, depth=0.7, location=(x - 0.3, y, z + 1.1),
                                        rotation=(0, math.radians(20), 0))
    arm = bpy.context.active_object
    arm.name = name + "_arm"
    arm.data.materials.append(mat)
    return body, head


def _camera(sc, path_pts, look_at, frames):
    cam_data = bpy.data.cameras.new("cam")
    cam_data.lens = 35
    cam = bpy.data.objects.new("cam", cam_data)
    sc.collection.objects.link(cam)
    sc.camera = cam
    tgt = bpy.data.objects.new("look", None)
    tgt.location = look_at
    sc.collection.objects.link(tgt)
    c = cam.constraints.new("TRACK_TO")
    c.target = tgt
    c.track_axis = "TRACK_NEGATIVE_Z"
    c.up_axis = "UP_Y"
    n = len(path_pts)
    _interp("BEZIER")
    for i, p in enumerate(path_pts):
        f = 1 + int(round(i * (frames - 1) / max(1, n - 1)))
        cam.location = p
        cam.keyframe_insert("location", frame=f)
    return cam


def build_crates(sc, seed):
    """A wall of crates, a heavy ball rolled into it, a figure watching from the side."""
    import random
    random.seed(seed)
    ground = _mat("ground", (0.35, 0.33, 0.30))
    crate = _mat("crate", (0.62, 0.45, 0.25))
    ball = _mat("ball", (0.15, 0.15, 0.17))
    skin = _mat("figure", (0.55, 0.55, 0.6))

    _box("ground", (0, 0, -0.5), (30, 30, 1), ground, active=False)
    # a back wall so the depth has something behind the action
    _box("wall", (0, 6, 2), (30, 0.4, 4), ground, active=False)

    cols, rows = 4, 4
    s = 0.6
    strike_frame = None
    for r in range(rows):
        for c in range(cols):
            x = (c - (cols - 1) / 2) * (s + 0.02) + random.uniform(-0.01, 0.01)
            z = r * (s + 0.01) + s / 2
            _box("crate_%d_%d" % (r, c), (x, 1.5, z), (s, s, s), crate, mass=1.0)

    sph = _sphere("ball", (-6.0, -3.0, 0.45), 0.45, ball, mass=12.0)
    # kinematic for the first frames so it arrives with a velocity, then dynamic
    _interp("LINEAR")
    sph.rigid_body.kinematic = True
    sph.location = (-6.0, -3.0, 0.45)
    sph.keyframe_insert("location", frame=1)
    sph.location = (-2.4, -0.6, 0.45)
    sph.keyframe_insert("location", frame=13)
    sph.rigid_body.keyframe_insert("kinematic", frame=13)
    sph.rigid_body.kinematic = False
    sph.rigid_body.keyframe_insert("kinematic", frame=14)
    strike_frame = 20   # roughly; measured after the bake below

    _figure("watcher", (3.2, -0.5, 0.0), skin)
    return {"strike_frame_planned": strike_frame, "crates": cols * rows}


def build_fall(sc, seed):
    """A column of crates that topples on its own from a nudge - the quietest physics beat."""
    ground = _mat("ground", (0.35, 0.33, 0.30))
    crate = _mat("crate", (0.62, 0.45, 0.25))
    skin = _mat("figure", (0.55, 0.55, 0.6))
    _box("ground", (0, 0, -0.5), (30, 30, 1), ground, active=False)
    _box("wall", (0, 6, 2), (30, 0.4, 4), ground, active=False)
    s = 0.6
    for r in range(7):
        _box("crate_%d" % r, (0.02 * r, 1.5, r * (s + 0.01) + s / 2), (s, s, s), crate, mass=1.0)
    nudge = _box("nudge", (-1.2, 1.5, 3.9), (0.3, 0.3, 0.3), crate, mass=3.0)
    _interp("LINEAR")
    nudge.rigid_body.kinematic = True
    nudge.keyframe_insert("location", frame=1)
    nudge.location = (-0.45, 1.5, 3.9)
    nudge.keyframe_insert("location", frame=10)
    nudge.rigid_body.keyframe_insert("kinematic", frame=10)
    nudge.rigid_body.kinematic = False
    nudge.rigid_body.keyframe_insert("kinematic", frame=11)
    _figure("watcher", (2.6, -0.3, 0.0), skin)
    return {"crates": 7}


def main():
    a = _args()
    out = os.path.abspath(os.path.expanduser(a.out))
    os.makedirs(out, exist_ok=True)
    sc = _clear()
    frames = int(round(a.seconds * a.fps))
    frames = ((frames - 1) // 8) * 8 + 1          # 8n+1, what LTX takes whole
    sc.frame_start, sc.frame_end = 1, frames
    sc.render.fps = a.fps
    sc.render.resolution_x, sc.render.resolution_y = a.width, a.height
    sc.render.resolution_percentage = 100

    # rigid-body world before objects are added
    bpy.ops.rigidbody.world_add()
    sc.rigidbody_world.substeps_per_frame = 10
    sc.rigidbody_world.solver_iterations = 20
    sc.rigidbody_world.point_cache.frame_start = 1
    sc.rigidbody_world.point_cache.frame_end = frames

    info = {"crates": build_crates, "fall": build_fall}[a.scene](sc, a.seed)

    # camera: a slow arc from front-left to front-right, slightly above, looking at the wall
    look = Vector((0.0, 1.5, 1.0))
    pts = []
    for i in range(5):
        t = i / 4
        ang = math.radians(-35 + 70 * t)
        pts.append(Vector((7.5 * math.sin(ang), 1.5 - 7.5 * math.cos(ang), 2.0 - 0.4 * t)))
    _camera(sc, pts, look, frames)

    # flat, quick, unambiguous shading: workbench, studio light, object colours
    sc.render.engine = "BLENDER_WORKBENCH"
    sh = sc.display.shading
    sh.light = "STUDIO"
    sh.color_type = "MATERIAL"
    sh.show_shadows = True
    sh.show_cavity = False
    sc.display_settings.display_device = "sRGB"
    try:
        sc.view_settings.view_transform = "Standard"
    except Exception:
        pass

    # bake so the strike frame can be read off the simulation
    bpy.ops.ptcache.bake_all(bake=True)
    sph = bpy.data.objects.get("ball")
    if sph is not None:
        first_hit = None
        prev = None
        for f in range(1, frames + 1):
            sc.frame_set(f)
            v = sph.matrix_world.translation.copy()
            if prev is not None and f > 14:
                # the ball decelerates sharply on the frame it meets the wall
                if (v - prev).length < 0.6 * step_len:
                    first_hit = f
                    break
            if prev is not None:
                step_len = (v - prev).length
            prev = v
        info["strike_frame"] = first_hit
    sc.frame_set(1)

    # a PNG sequence: the flatpak Blender has no video encoder; the wrapper encodes it
    fdir = os.path.join(out, "frames")
    os.makedirs(fdir, exist_ok=True)
    for f in os.listdir(fdir):
        if f.startswith("f_") and f.endswith(".png"):
            os.remove(os.path.join(fdir, f))
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGB"
    sc.render.filepath = os.path.join(fdir, "f_")
    bpy.ops.render.render(animation=True)

    info.update({"frames": frames, "fps": a.fps, "width": a.width, "height": a.height,
                 "scene": a.scene, "seed": a.seed})
    json.dump(info, open(os.path.join(out, "previz.json"), "w"), indent=1)
    print("previz (blender side):", json.dumps(info))


if __name__ == "__main__":
    if IN_BLENDER:
        main()
    else:
        _wrapper(sys.argv[1:])
