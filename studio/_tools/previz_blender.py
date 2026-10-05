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

`--scene orbit` is a camera move rather than physics: a figure dressed in proxies (a flared coat,
shoulders, a braid, a cape on one side, two tanks on her back) stands in a vaulted stone room with a
workbench on her right and a railing at the edge of a shaft behind her, and the camera circles her
at a constant rate (`--degrees`, `--radius`, `--lens`, `--cam-z`, `--look-z`; `--frames` sets the
length exactly). The video engines turn a prompted orbit into a morph; with the move's depth as the
guide, the room has to stay one room and the back of the figure has a shape to be painted on.

`--scene set` stands the camera in a SET: a whole place built once (a set module beside this file,
`--set plaza` = set_plaza.py) or imported (`--set <file.glb>`), so every shot of a scene is a camera
position and a lens in the same world - `--cam x,y,z --look x,y,z --lens 35`, and for a move their
`--cam-to` / `--look-to` / `--lens-to` ends (eased), or an orbit of `--arc` degrees about
`--arc-center`; `--ortho W` makes a map, W metres across. A set renders lit (`--render beauty`: Eevee,
the set's own sun and sky), which is both the picture a start frame is dressed from and the control
whose depth the IC-LoRA reads. `--masks N` also renders every Nth frame with each landmark in a flat
ID colour (masks/m_NNNN.png), and previz.json carries the camera of every frame, so a take can be
measured against the set rather than against an opinion.
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
    ap.add_argument("--joints", type=int, default=0)
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
    if a.joints:
        # keypoints only: nothing was rendered, so there is nothing to encode
        if r.returncode != 0 or not os.path.exists(os.path.join(out, "joints.json")):
            print(tail)
            print(r.stderr[-2000:])
            raise SystemExit("blender failed (%s)" % r.returncode)
        print("joints:", os.path.join(out, "joints.json"))
        return
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
    ap.add_argument("--scene", default="crates",
                    choices=["crates", "fall", "aisle", "orbit", "street", "canyon", "set"])
    ap.add_argument("--seconds", type=float, default=4.0)
    ap.add_argument("--frames", type=int, default=0, help="the exact length (8n+1); overrides --seconds")
    ap.add_argument("--fps", type=int, default=24)
    ap.add_argument("--width", type=int, default=1280)
    ap.add_argument("--height", type=int, default=704)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--degrees", type=float, default=360.0, help="orbit: how far the camera goes round")
    ap.add_argument("--radius", type=float, default=3.3, help="orbit: metres from the figure")
    ap.add_argument("--lens", type=float, default=42.0, help="orbit, set: focal length, mm")
    ap.add_argument("--cam-z", type=float, default=1.45, help="orbit: camera height, m")
    ap.add_argument("--look-z", type=float, default=1.25, help="orbit: the height it looks at, m")
    ap.add_argument("--radius-to", type=float, default=None, help="street/canyon: the distance it ends at")
    ap.add_argument("--lens-to", type=float, default=None, help="street/canyon, set: the focal length it ends at")
    ap.add_argument("--cam-z-to", type=float, default=None, help="street/canyon: the height it ends at")
    ap.add_argument("--look-z-to", type=float, default=None, help="street/canyon: where it ends up looking")
    ap.add_argument("--figure-turn", type=float, default=0.0,
                    help="degrees the figure is turned about its own axis (+ turns her front toward the right of frame)")
    ap.add_argument("--figure-glb", default="", help="orbit: the figure's real shape (a mesh from her "
                    "character sheet) instead of the proxy")
    ap.add_argument("--set", default="plaza", help="set: a set module (set_<name>.py beside this file) or a .glb")
    ap.add_argument("--cam", default="0,-12,1.6", help="set: where the camera stands, x,y,z in metres")
    ap.add_argument("--cam-to", default="", help="set: where it ends up (a move)")
    ap.add_argument("--look", default="0,0,1.5", help="set: the point it looks at")
    ap.add_argument("--look-to", default="", help="set: the point it ends up looking at (a pan or a tilt)")
    ap.add_argument("--arc", type=float, default=0.0, help="set: degrees the camera travels round --arc-center")
    ap.add_argument("--arc-center", default="0,0,0", help="set: the vertical axis an --arc turns about")
    ap.add_argument("--ease", default="smooth", choices=["smooth", "linear"])
    ap.add_argument("--ortho", type=float, default=0.0, help="set: an orthographic camera this many metres across")
    ap.add_argument("--render", default="", choices=["", "flat", "beauty"],
                    help="flat = workbench object colours (the default), beauty = Eevee lit (a set's default)")
    ap.add_argument("--masks", type=int, default=0, help="set: also render every Nth frame in landmark ID colours")
    ap.add_argument("--figure-at", default="", help="set: where --figure-glb stands, x,y,z (her feet)")
    ap.add_argument("--figure-height", type=float, default=1.66, help="set: the figure's height, m")
    ap.add_argument("--figure-name", default="figure", help="set: the figure's landmark group (her name)")
    ap.add_argument("--action", default="", help="set: the set module's choreography for this shot (act(name))")
    ap.add_argument("--hide-figures", type=int, default=0,
                    help="set: render without the characters (the place a character is put into, set_test.py cast)")
    ap.add_argument("--joints", type=int, default=0,
                    help="set: write every puppet's 18 pose keypoints on every frame, as the camera sees them, to "
                         "joints.json - and render nothing (what a pose skeleton is drawn from)")
    ap.add_argument("--depth", type=int, default=0,
                    help="also render each rendered frame as the camera's view-Z depth, 16-bit grey, 0 at the lens and "
                         "1 at DEPTH_FAR m, to depth/d_NNNN.png (what hides a character behind the set, set_test cast)")
    ap.add_argument("--endpoints", type=int, default=0,
                    help="render only the first and the last frame (the physics still runs through every frame "
                         "between): all a shot drawn between two frames needs from the set")
    return ap.parse_args(argv)


def _vec(s):
    return Vector([float(x) for x in str(s).split(",")])


def build_set(sc, a, frames):
    """A whole place: a set module beside this file (set_<name>.py, whose build() returns its landmark
    table, and whose act(name, ...) choreographs a shot in it) or a glTF file, whose objects are grouped
    by the first word of their names."""
    if a.set.lower().endswith((".glb", ".gltf")):
        bpy.ops.import_scene.gltf(filepath=os.path.abspath(os.path.expanduser(a.set)))
        for ob in bpy.data.objects:
            if ob.type in ("MESH", "FONT") and "group" not in ob.keys():
                ob["group"] = ob.name.replace(".", "_").split("_")[0].lower()
        if not any(o.type == "LIGHT" for o in bpy.data.objects):
            sd = bpy.data.lights.new("sun", type="SUN")
            sd.energy = 3.5
            sun = bpy.data.objects.new("sun", sd)
            sc.collection.objects.link(sun)
            sun.rotation_euler = (math.radians(55), 0.0, math.radians(35))
        if sc.world is None:
            sc.world = bpy.data.worlds.new("sky")
        return {"set": os.path.basename(a.set), "groups": {}, "landmarks": []}
    here = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else \
        os.path.dirname(os.path.abspath(sys.argv[sys.argv.index("-P") + 1]))
    if here not in sys.path:
        sys.path.insert(0, here)
    import importlib
    mod = importlib.import_module("set_" + a.set)
    info = mod.build(sc, a.seed)
    if a.action:
        mod.act(a.action, sc, frames, info)
        info["action"] = a.action
    if a.figure_glb and a.figure_at:
        # a character standing in the set: her real shape (a Hunyuan3D mesh from her sheet), light grey so
        # the dress paints her from her reference picture; her own group and surface for the masks
        mat = _mat("figure", (0.62, 0.62, 0.64))
        ob = _import_figure(a.figure_glb, mat, height=a.figure_height, turn=a.figure_turn)
        ob.location = _vec(a.figure_at)
        ob["group"] = a.figure_name
        ob["surface"] = "%s/figure" % a.figure_name
        info.setdefault("groups", {})[a.figure_name] = [255, 255, 255]
        info.setdefault("landmarks", []).append(a.figure_name)
        info["figure"] = {"name": a.figure_name, "at": [float(x) for x in a.figure_at.split(",")],
                          "turn": a.figure_turn, "height": a.figure_height, "glb": os.path.basename(a.figure_glb)}
    if a.hide_figures:
        names = {f["name"] for f in info.get("figures", [])} | ({a.figure_name} if a.figure_glb else set())
        for ob in bpy.data.objects:
            if ob.get("group") in names:
                ob.hide_render = True
    return info


def _set_camera(sc, a, frames):
    """A camera keyed on every frame: from --cam to --cam-to (and round --arc-center by --arc degrees),
    looking from --look to --look-to, the lens from --lens to --lens-to. Returns the camera of every
    frame, so the render can be checked against where the camera was said to be."""
    cd = bpy.data.cameras.new("cam")
    cd.clip_start, cd.clip_end = 0.05, 2000.0
    if a.ortho:
        cd.type = "ORTHO"
        cd.ortho_scale = a.ortho
    cam = bpy.data.objects.new("cam", cd)
    sc.collection.objects.link(cam)
    sc.camera = cam
    p0 = _vec(a.cam)
    p1 = _vec(a.cam_to) if a.cam_to else p0.copy()
    l0 = _vec(a.look)
    l1 = _vec(a.look_to) if a.look_to else l0.copy()
    f0 = a.lens
    f1 = a.lens_to if a.lens_to is not None else a.lens
    centre = _vec(a.arc_center)
    rows = []
    for f in range(1, frames + 1):
        t = (f - 1) / max(1, frames - 1)
        e = t if a.ease == "linear" else t * t * (3 - 2 * t)
        p = p0.lerp(p1, e)
        if a.arc:
            ang = math.radians(a.arc) * e
            d = p - centre
            c, s = math.cos(ang), math.sin(ang)
            p = Vector((centre.x + d.x * c - d.y * s, centre.y + d.x * s + d.y * c, p.z))
        look = l0.lerp(l1, e)
        cam.location = p
        cam.rotation_euler = (look - p).to_track_quat("-Z", "Y").to_euler()
        cam.keyframe_insert("location", frame=f)
        cam.keyframe_insert("rotation_euler", frame=f)
        cd.lens = f0 + (f1 - f0) * e
        cd.keyframe_insert("lens", frame=f)
        rows.append({"f": f, "cam": [round(x, 3) for x in p], "look": [round(x, 3) for x in look],
                     "lens": round(cd.lens, 2)})
    return rows


def _beauty(sc):
    """Lit the way the set's own sun and sky light it: Eevee."""
    sc.render.engine = "BLENDER_EEVEE"
    try:
        sc.eevee.taa_render_samples = 24
    except Exception:
        pass
    for look in ("AgX - Punchy", "Punchy", "None"):
        try:
            sc.view_settings.view_transform = "AgX"
            sc.view_settings.look = look
            break
        except Exception:
            continue


def _masks(sc, out, frames, every, groups):
    """Every Nth frame again as flat ID colours, no anti-aliasing and no dither, for measuring where
    everything falls in a take: masks/m_NNNN.png colours each landmark GROUP (the table the set
    returns), masks/s_NNNN.png each SURFACE (an object's "surface", group/material - the cafe's wall,
    its awning's red stripes), in colours from a 6-level grid listed in previz.json."""
    def lin(c):
        c = c / 255.0
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    obs = [ob for ob in bpy.data.objects if ob.type in ("MESH", "FONT")]
    names = sorted(set(ob.get("surface") or ("%s/-" % ob.get("group", "other")) for ob in obs))
    grid = [(r, g, b) for r in range(0, 256, 51) for g in range(0, 256, 51) for b in range(0, 256, 51)][1:]
    surfaces = {n: grid[(i * 97) % len(grid)] for i, n in enumerate(names)}   # neighbours in name far apart in colour
    passes = [("m", {ob.name: groups.get(ob.get("group", ""), (192, 192, 192)) for ob in obs}),
              ("s", {ob.name: surfaces[ob.get("surface") or ("%s/-" % ob.get("group", "other"))] for ob in obs})]
    sc.render.engine = "BLENDER_WORKBENCH"
    sh = sc.display.shading
    sh.light = "FLAT"
    sh.color_type = "OBJECT"
    for attr in ("show_shadows", "show_cavity", "show_object_outline", "show_specular_highlight"):
        try:
            setattr(sh, attr, False)
        except Exception:
            pass
    sc.display.render_aa = "OFF"
    sc.render.dither_intensity = 0.0
    sc.view_settings.view_transform = "Standard"
    try:
        sc.view_settings.look = "None"
    except Exception:
        pass
    if sc.world is not None:
        sc.world.color = (0.0, 0.0, 0.0)
    mdir = os.path.join(out, "masks")
    os.makedirs(mdir, exist_ok=True)
    picked = sorted(set(list(range(1, frames + 1, every)) + [frames]))
    for prefix, colour in passes:
        for ob in obs:
            rgb = colour[ob.name]
            ob.color = (lin(rgb[0]), lin(rgb[1]), lin(rgb[2]), 1.0)
        for f in picked:
            sc.frame_set(f)
            sc.render.filepath = os.path.join(mdir, "%s_%04d.png" % (prefix, f))
            bpy.ops.render.render(write_still=True)
    return picked, {n: list(c) for n, c in surfaces.items()}


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


def build_aisle(sc, seed):
    """DEAD STOCK 070: an aisle between two walls of crates; the tall stack on the right is pushed
    over into the aisle and piles up across it; a proxy figure stands far down the aisle beyond.
    The walls are PASSIVE rigid bodies so the falling crates collide with them; the pusher is
    kinematic, hidden from the render, and retracts upward once the stack is committed."""
    import random
    random.seed(seed)
    ground = _mat("ground", (0.30, 0.30, 0.31))
    crate = _mat("crate", (0.62, 0.45, 0.25))
    crate2 = _mat("crate2", (0.52, 0.38, 0.21))
    skin = _mat("figure", (0.55, 0.55, 0.6))
    _box("ground", (0, 12, -0.5), (40, 70, 1), ground, active=False)
    _box("back", (0, 34, 4), (40, 0.4, 8), ground, active=False)
    s, half = 0.7, 1.6
    for side in (-1, 1):
        for i in range(30):
            y = 1.0 + i * (s + 0.02)
            if side == 1 and 3.3 <= y <= 6.2:
                continue                    # the gap the toppling stack stands in
            for k in range(4):
                _box("wall_%d_%d_%d" % (side, i, k), (side * (half + s / 2), y, k * (s + 0.005) + s / 2),
                     (s, s, s), crate2 if (i + k) % 2 else crate, active=False)
    tops = []
    for c in range(3):
        y = 3.6 + c * (s + 0.02)
        for k in range(6):
            ob = _box("fall_%d_%d" % (c, k),
                      (half + s / 2 + random.uniform(-0.01, 0.01), y, k * (s + 0.005) + s / 2),
                      (s, s, s), crate if (c + k) % 2 else crate2, mass=2.0)
            if k == 5:
                tops.append(ob)
    z_top = 5 * (s + 0.005) + s / 2
    pusher = _box("pusher", (half + s + 0.35, 4.35, z_top), (0.3, 2.4, 0.5), crate, mass=20.0)
    _interp("LINEAR")
    pusher.rigid_body.kinematic = True
    pusher.keyframe_insert("location", frame=1)
    pusher.keyframe_insert("location", frame=10)
    pusher.location = (half - 0.15, 4.35, z_top)
    pusher.keyframe_insert("location", frame=22)
    pusher.location = (half - 0.15, 4.35, z_top + 8.0)
    pusher.keyframe_insert("location", frame=28)
    pusher.hide_render = True
    _figure("far_figure", (0.0, 14.5, 0.0), skin)
    return {"falling_crates": 18, "tops": [t.name for t in tops]}


def _solid(name, loc, size, mat, rot=(0, 0, 0)):
    """A box with no rigid body: set dressing for a camera move."""
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=loc, rotation=rot)
    ob = bpy.context.active_object
    ob.name = name
    ob.scale = size
    ob.data.materials.append(mat)
    return ob


def _cyl(name, loc, r, depth, mat, rot=(0, 0, 0), r2=None, scale=None):
    if r2 is None:
        bpy.ops.mesh.primitive_cylinder_add(vertices=24, radius=r, depth=depth, location=loc, rotation=rot)
    else:
        bpy.ops.mesh.primitive_cone_add(vertices=32, radius1=r, radius2=r2, depth=depth, location=loc,
                                        rotation=rot)
    ob = bpy.context.active_object
    ob.name = name
    if scale:
        ob.scale = scale
    ob.data.materials.append(mat)
    bpy.ops.object.shade_smooth()
    return ob


def _ball(name, loc, r, mat, scale=None):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=r, location=loc, segments=24, ring_count=12)
    ob = bpy.context.active_object
    ob.name = name
    if scale:
        ob.scale = scale
    ob.data.materials.append(mat)
    bpy.ops.object.shade_smooth()
    return ob


def _dressed_figure(mat, kit):
    """A standing woman in a long coat, facing -y (her right hand on the picture's left at the start):
    the shapes that decide what the painter draws from behind - the flare of the coat, a cape on her
    right side, a braid over her left shoulder, two tanks on her back."""
    _cyl("coat", (0, 0, 0.70), 0.29, 1.30, mat, r2=0.19, scale=(1.0, 0.80, 1.0))
    _ball("chest", (0, 0, 1.33), 1.0, mat, scale=(0.21, 0.14, 0.16))
    _cyl("neck", (0, 0, 1.50), 0.05, 0.14, mat)
    _ball("head", (0, -0.01, 1.63), 0.115, mat, scale=(0.9, 1.0, 1.12))
    _cyl("braid", (0.11, -0.09, 1.30), 0.035, 0.52, mat, rot=(math.radians(-8), math.radians(10), 0))
    for side in (-1, 1):
        _cyl("arm_%d" % side, (side * 0.25, 0, 1.07), 0.045, 0.62, mat, rot=(0, math.radians(side * -6), 0))
        _ball("hand_%d" % side, (side * 0.29, -0.01, 0.75), 0.045, mat)
    _solid("cape", (-0.21, 0.09, 0.92), (0.08, 0.26, 1.05), mat, rot=(math.radians(-5), math.radians(-6), 0))
    for side in (-1, 1):
        _cyl("tank_%d" % side, (side * 0.10, 0.25, 1.18), 0.08, 0.54, kit)
    _solid("pack", (0, 0.19, 1.20), (0.30, 0.08, 0.34), kit)


def _import_figure(path, mat, height=1.72, turn=0.0):
    """The figure's real shape - a Hunyuan3D mesh from the front view of her character sheet (/sheets,
    "3D model") - joined, stood on the floor at the origin, scaled to her height. glTF's front (+Z)
    comes in as -y, which is the way the proxy faces."""
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=path)
    new = [o for o in bpy.data.objects if o not in before and o.type == "MESH"]
    if not new:
        raise SystemExit("no mesh in %s" % path)
    bpy.ops.object.select_all(action="DESELECT")
    for o in new:
        o.select_set(True)
    bpy.context.view_layer.objects.active = new[0]
    bpy.ops.object.parent_clear(type="CLEAR_KEEP_TRANSFORM")
    if len(new) > 1:
        bpy.ops.object.join()
    ob = bpy.context.view_layer.objects.active
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    zs = [v.co.z for v in ob.data.vertices]
    k = height / (max(zs) - min(zs))
    ob.scale = (k, k, k)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    xs, ys, zs = zip(*[(v.co.x, v.co.y, v.co.z) for v in ob.data.vertices])
    ob.location = (-(min(xs) + max(xs)) / 2, -(min(ys) + max(ys)) / 2, -min(zs))
    bpy.ops.object.transform_apply(location=True, rotation=False, scale=False)
    if turn:
        # the glTF importer leaves its objects in QUATERNION mode, where an euler is silently ignored: until
        # 2026-09-30 every --figure-turn did nothing (found turning Terra in the plaza)
        ob.rotation_mode = "XYZ"
        ob.rotation_euler = (0.0, 0.0, math.radians(turn))
        bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)
    ob.data.materials.clear()
    ob.data.materials.append(mat)
    bpy.ops.object.shade_smooth()
    ob.name = "figure"
    return ob


def build_orbit(sc, seed, figure_glb="", turn=0.0):
    """A vaulted stone workshop laid out like the film's master: the workbench on her right from the
    near left of the first frame toward the back, the railing behind her at the edge of a shaft that
    falls away, neon tubes on the piers, shelves and barrels round the rest of the room. Nothing moves
    but the camera."""
    stone = _mat("stone", (0.42, 0.40, 0.38))
    wood = _mat("wood", (0.45, 0.32, 0.20))
    glass = _mat("glass", (0.70, 0.78, 0.80))
    metal = _mat("metal", (0.55, 0.50, 0.40))
    neon = _mat("neon", (0.80, 0.92, 1.0))
    fig = _mat("figure", (0.55, 0.55, 0.60))
    # the floor stops at the shaft (y = 4.1); the shaft's bottom is far below
    _solid("floor", (0, -0.25, -0.25), (8.8, 8.7, 0.5), stone)
    _solid("pit", (0, 5.8, -30.0), (8.8, 3.4, 1.0), stone)
    # walls, running down into the shaft; the vault's ribs and a ceiling
    _solid("wall_l", (-4.4, 1.4, -12.0), (0.4, 12.2, 36.0), stone)
    _solid("wall_r", (4.4, 1.4, -12.0), (0.4, 12.2, 36.0), stone)
    _solid("wall_near", (0, -4.8, -12.0), (9.2, 0.4, 36.0), stone)
    _solid("wall_far", (0, 7.6, -12.0), (9.2, 0.4, 36.0), stone)
    _solid("ceiling", (0, 1.4, 6.2), (9.2, 12.6, 0.4), stone)
    for i, y in enumerate((-3.3, -0.4, 2.4, 5.4)):
        _solid("rib_%d" % i, (0, y, 5.7), (9.0, 0.45, 0.6), stone)
        for side in (-1, 1):
            _solid("pier_%d_%d" % (i, side), (side * 4.0, y, 2.8), (0.45, 0.55, 5.6), stone)
            if y < 4.0:
                _solid("neon_%d_%d" % (i, side), (side * 3.72, y + 0.7, 1.75), (0.06, 0.06, 1.35), neon)
    # the railing at the edge of the shaft
    x = -4.1
    while x <= 4.11:
        _solid("post_%.1f" % x, (x, 4.05, 0.5), (0.05, 0.05, 1.0), metal)
        x += 0.55
    _solid("rail_top", (0, 4.05, 1.0), (8.3, 0.06, 0.06), metal)
    _solid("rail_mid", (0, 4.05, 0.55), (8.3, 0.04, 0.04), metal)
    # the workbench on her right, short glassware only: the camera passes over it on that side of the
    # circle, and a lamp or a tall flask there stands between the lens and her for a quarter of the turn
    _solid("bench_top", (-1.05, -0.9, 0.88), (0.75, 2.4, 0.08), wood)
    _solid("bench_shelf", (-1.05, -0.9, 0.25), (0.70, 2.3, 0.05), wood)
    for lx in (-1.38, -0.72):
        for ly in (-2.05, 0.25):
            _solid("leg_%.2f_%.2f" % (lx, ly), (lx, ly, 0.42), (0.07, 0.07, 0.84), wood)
    for i, (fx, fy, kind, r, h) in enumerate([(-1.20, -1.65, "ball", 0.09, 0.0), (-0.90, -1.15, "tube", 0.05, 0.18),
                                              (-1.25, -0.60, "tube", 0.07, 0.16), (-0.88, -0.10, "ball", 0.08, 0.0),
                                              (-1.25, 0.05, "tube", 0.04, 0.20)]):
        if kind == "ball":
            _ball("flask_%d" % i, (fx, fy, 0.92 + r), r, glass)
        else:
            _cyl("flask_%d" % i, (fx, fy, 0.92 + h / 2), r, h, glass)
    # the rest of the room: shelves on the right wall, barrels in the near corners, a small table
    _solid("shelves", (3.85, -0.6, 1.1), (0.5, 2.2, 2.2), wood)
    _cyl("barrel_1", (-3.5, -3.8, 0.4), 0.32, 0.8, wood)
    _cyl("barrel_2", (-2.9, -4.0, 0.4), 0.30, 0.8, wood)
    _cyl("barrel_3", (3.4, -3.9, 0.4), 0.32, 0.8, wood)
    _solid("table", (3.2, 2.4, 0.4), (0.9, 0.9, 0.8), wood)
    if figure_glb:
        _import_figure(figure_glb, fig, turn=turn)
    else:
        _dressed_figure(fig, metal)
    return {"figure_at": [0, 0, 0], "faces": "-y", "figure": os.path.basename(figure_glb) or "proxy"}


def build_street(sc, seed, figure_glb="", turn=0.0):
    """A narrow city street at night with the figure standing in the middle of it: asphalt and kerbs,
    building fronts with blade signs, awnings and doors, the street running away behind her."""
    asphalt = _mat("asphalt", (0.25, 0.25, 0.27))
    wall = _mat("facade", (0.42, 0.40, 0.42))
    sign = _mat("sign", (0.75, 0.55, 0.70))
    metal = _mat("metal", (0.55, 0.50, 0.40))
    fig = _mat("figure", (0.55, 0.55, 0.60))
    _solid("road", (0, 30, -0.25), (16, 100, 0.5), asphalt)
    for side in (-1, 1):
        _solid("kerb_%d" % side, (side * 4.6, 30, 0.07), (1.8, 100, 0.14), asphalt)
        _solid("facade_%d" % side, (side * 6.5, 30, 20), (1.6, 100, 40), wall)
        for i in range(18):
            y = -8 + i * 5.2
            _solid("door_%d_%d" % (side, i), (side * 5.66, y, 1.2), (0.1, 1.4, 2.4), asphalt)
            _solid("sign_%d_%d" % (side, i), (side * 5.2, y + 1.8, 3.2 + (i % 3) * 0.9),
                   (0.9, 0.12, 1.6 + (i % 2) * 0.8), sign)
            _solid("awning_%d_%d" % (side, i), (side * 5.1, y + 3.6, 2.7), (1.2, 1.8, 0.06), metal)
    _solid("facade_back", (0, -14, 20), (16, 2, 40), wall)
    _solid("grate", (1.4, 1.2, 0.01), (0.9, 0.6, 0.02), metal)
    if figure_glb:
        _import_figure(figure_glb, fig, turn=turn)
    else:
        _dressed_figure(fig, metal)
    return {"figure_at": [0, 0, 0], "faces": "-y", "figure": os.path.basename(figure_glb) or "proxy"}


def build_canyon(sc, seed, figure_glb="", turn=0.0):
    """A narrow canyon of towers with the figure hanging in mid-air in it: two walls of towers either
    side, blade signs and ledges on their faces, sky bridges across, the street far below, all running
    a long way ahead - the lines a dolly zoom stretches."""
    import random
    random.seed(seed)
    tower = _mat("tower", (0.36, 0.36, 0.40))
    sign = _mat("sign", (0.75, 0.55, 0.70))
    street = _mat("street", (0.25, 0.25, 0.27))
    metal = _mat("metal", (0.55, 0.50, 0.40))
    fig = _mat("figure", (0.55, 0.55, 0.60))
    _solid("street", (0, 150, -120.5), (30, 400, 1), street)
    for side in (-1, 1):
        _solid("towers_%d" % side, (side * 11, 150, -30), (6, 400, 180), tower)
        for i in range(60):
            y = -20 + i * 6.5 + random.uniform(-1, 1)
            z = random.uniform(-60, 25)
            _solid("sign_%d_%d" % (side, i), (side * 7.6, y, z), (0.8, 0.2, random.uniform(3, 8)), sign)
            if i % 3 == 0:
                _solid("ledge_%d_%d" % (side, i), (side * 7.8, y, z + 5), (0.6, 5, 0.4), tower)
    for i in range(8):
        _solid("bridge_%d" % i, (0, 25 + i * 40, random.uniform(-40, 15)), (16, 3, 1.2), tower)
    _solid("towers_back", (0, -40, -30), (30, 2, 180), tower)
    if figure_glb:
        _import_figure(figure_glb, fig, turn=turn)
    else:
        _dressed_figure(fig, metal)
    return {"figure_at": [0, 0, 0], "faces": "-y", "figure": os.path.basename(figure_glb) or "proxy"}


def _move_camera(sc, a, frames):
    """One eased move from a start to an end - distance, height, the height it looks at, focal length.
    A tilt keeps the distance and moves the look; a dolly zoom moves the distance and the lens together
    (lens / distance constant) so the figure stays one size while everything behind her stretches."""
    cam_data = bpy.data.cameras.new("cam")
    cam_data.clip_start = 0.02
    cam_data.clip_end = 500.0
    cam = bpy.data.objects.new("cam", cam_data)
    sc.collection.objects.link(cam)
    sc.camera = cam
    tgt = bpy.data.objects.new("look", None)
    sc.collection.objects.link(tgt)
    c = cam.constraints.new("TRACK_TO")
    c.target = tgt
    c.track_axis = "TRACK_NEGATIVE_Z"
    c.up_axis = "UP_Y"
    end = (a.radius if a.radius_to is None else a.radius_to, a.cam_z if a.cam_z_to is None else a.cam_z_to,
           a.look_z if a.look_z_to is None else a.look_z_to, a.lens if a.lens_to is None else a.lens_to)
    _interp("BEZIER")
    for f, (r, z, look, lens) in ((1, (a.radius, a.cam_z, a.look_z, a.lens)), (frames, end)):
        cam.location = (0.0, -r, z)
        cam.keyframe_insert("location", frame=f)
        tgt.location = (0.0, 0.0, look)
        tgt.keyframe_insert("location", frame=f)
        cam_data.lens = lens
        cam_data.keyframe_insert("lens", frame=f)
    return cam


def _orbit_camera(sc, a, frames):
    """A camera on a pivot at the figure, turned at a constant rate (linear keys), looking at her."""
    pivot = bpy.data.objects.new("pivot", None)
    sc.collection.objects.link(pivot)
    cam_data = bpy.data.cameras.new("cam")
    cam_data.lens = a.lens
    cam_data.clip_end = 200.0
    cam = bpy.data.objects.new("cam", cam_data)
    sc.collection.objects.link(cam)
    sc.camera = cam
    cam.parent = pivot
    cam.location = (0.0, -a.radius, a.cam_z)
    tgt = bpy.data.objects.new("look", None)
    tgt.location = (0.0, 0.0, a.look_z)
    sc.collection.objects.link(tgt)
    c = cam.constraints.new("TRACK_TO")
    c.target = tgt
    c.track_axis = "TRACK_NEGATIVE_Z"
    c.up_axis = "UP_Y"
    _interp("LINEAR")
    pivot.rotation_euler = (0.0, 0.0, 0.0)
    pivot.keyframe_insert("rotation_euler", frame=1)
    pivot.rotation_euler = (0.0, 0.0, math.radians(a.degrees))
    pivot.keyframe_insert("rotation_euler", frame=frames)
    return cam


# OpenPose's 18 body keypoints, in its order, from a puppet's joints (set_actors.py): a joint's origin, the
# midpoint of the shoulders (OpenPose's neck), or a point in a joint's own frame in units of the puppet's
# height - the face sits on the "neck" joint, whose head blob is centred 0.07 above it, and a puppet faces -Y
POSE18 = [("nose", "neck", (0.0, -0.065, 0.065)), ("neck", None, None),
          ("r_shoulder", "r_shoulder", None), ("r_elbow", "r_elbow", None), ("r_wrist", "r_elbow", (0.0, 0.0, -0.16)),
          ("l_shoulder", "l_shoulder", None), ("l_elbow", "l_elbow", None), ("l_wrist", "l_elbow", (0.0, 0.0, -0.16)),
          ("r_hip", "r_hip", None), ("r_knee", "r_knee", None), ("r_ankle", "r_ankle", None),
          ("l_hip", "l_hip", None), ("l_knee", "l_knee", None), ("l_ankle", "l_ankle", None),
          ("r_eye", "neck", (-0.022, -0.055, 0.085)), ("l_eye", "neck", (0.022, -0.055, 0.085)),
          ("r_ear", "neck", (-0.06, 0.0, 0.075)), ("l_ear", "neck", (0.06, 0.0, 0.075))]


def _joints(sc, out, frames):
    """Every puppet's 18 keypoints on every frame, in pixels as the camera sees them. A face point the camera
    cannot see is left out, the way a pose detector leaves it out - so a skeleton says which way a face
    points, which a depth map cannot (the forest's jester, 2026-09-30, turned his back mid-leap)."""
    from bpy_extras.object_utils import world_to_camera_view
    roots = [o for o in bpy.data.objects if o.type == "EMPTY" and o.name.endswith("_root")
             and bpy.data.objects.get(o.name[:-5] + "_hips") is not None]
    W, H = sc.render.resolution_x, sc.render.resolution_y
    res = {"width": W, "height": H, "frames": frames, "keypoints": [k[0] for k in POSE18],
           "puppets": {r.name[:-5]: [] for r in roots}}
    for f in range(1, frames + 1):
        sc.frame_set(f)
        cam = sc.camera
        cpos = cam.matrix_world.translation
        for r in roots:
            n = r.name[:-5]
            J = lambda j: bpy.data.objects[n + "_" + j].matrix_world
            h = (J("l_ankle").translation - J("l_knee").translation).length / 0.245
            head = J("neck") @ Vector((0.0, 0.0, 0.07 * h))
            to_cam = (cpos - head).normalized()
            row = []
            for name, joint, off in POSE18:
                if joint is None:
                    w = (J("l_shoulder").translation + J("r_shoulder").translation) / 2
                elif off is None:
                    w = J(joint).translation.copy()
                else:
                    w = J(joint) @ Vector((off[0] * h, off[1] * h, off[2] * h))
                seen = True
                if name in ("nose", "r_eye", "l_eye", "r_ear", "l_ear"):
                    d = (w - head).normalized().dot(to_cam)
                    seen = d > {"nose": -0.3, "r_ear": -0.25, "l_ear": -0.25}.get(name, 0.2)
                v = world_to_camera_view(sc, cam, w)
                inside = v.z > 0 and -0.05 <= v.x <= 1.05 and -0.05 <= v.y <= 1.05
                row.append([round(v.x * W, 1), round((1 - v.y) * H, 1), round(v.z, 3)] if seen and inside else None)
            res["puppets"][n].append(row)
    json.dump(res, open(os.path.join(out, "joints.json"), "w"))
    print("joints:", {k: len(v) for k, v in res["puppets"].items()})


DEPTH_FAR = 80.0


def _depth(sc, out, frames):
    """The rendered frames again with every surface replaced by its distance along the camera's axis: an
    emission material over the whole view layer, raw view transform, 16-bit greyscale, the sky as far."""
    m = bpy.data.materials.new("depth_override")
    try:
        m.use_nodes = True
    except Exception:
        pass
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    cd = nt.nodes.new("ShaderNodeCameraData")
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.inputs["From Min"].default_value = 0.0
    mr.inputs["From Max"].default_value = DEPTH_FAR
    mr.inputs["To Min"].default_value = 0.0
    mr.inputs["To Max"].default_value = 1.0
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Strength"].default_value = 1.0
    mo = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(cd.outputs["View Z Depth"], mr.inputs["Value"])
    nt.links.new(mr.outputs["Result"], em.inputs["Color"])
    nt.links.new(em.outputs["Emission"], mo.inputs["Surface"])
    vl = sc.view_layers[0]
    keep = (vl.material_override, sc.view_settings.view_transform, sc.render.image_settings.color_depth,
            sc.render.image_settings.color_mode, sc.world)
    vl.material_override = m
    try:
        sc.view_settings.view_transform = "Raw"
    except Exception:
        sc.view_settings.view_transform = "Standard"
    sc.render.image_settings.color_mode = "BW"
    sc.render.image_settings.color_depth = "16"
    sky = bpy.data.worlds.new("depth_sky")                 # nothing hit = as far as it gets
    try:
        sky.use_nodes = True
        bg = next(n for n in sky.node_tree.nodes if n.type == "BACKGROUND")
        bg.inputs["Color"].default_value = (1.0, 1.0, 1.0, 1.0)
        bg.inputs["Strength"].default_value = 1.0
    except Exception:
        sky.color = (1.0, 1.0, 1.0)
    sc.world = sky
    ddir = os.path.join(out, "depth")
    os.makedirs(ddir, exist_ok=True)
    for f in frames:
        sc.frame_set(f)
        sc.render.filepath = os.path.join(ddir, "d_%04d.png" % f)
        bpy.ops.render.render(write_still=True)
    (vl.material_override, sc.view_settings.view_transform, sc.render.image_settings.color_depth,
     sc.render.image_settings.color_mode, sc.world) = keep


def main():
    a = _args()
    out = os.path.abspath(os.path.expanduser(a.out))
    os.makedirs(out, exist_ok=True)
    sc = _clear()
    frames = a.frames or int(round(a.seconds * a.fps))
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

    if a.scene == "set":
        info = build_set(sc, a, frames)
    elif a.scene in ("orbit", "street", "canyon"):
        info = {"orbit": build_orbit, "street": build_street, "canyon": build_canyon}[a.scene](
            sc, a.seed, a.figure_glb, a.figure_turn)
    else:
        info = {"crates": build_crates, "fall": build_fall, "aisle": build_aisle}[a.scene](sc, a.seed)

    if a.scene == "set":
        info["camera"] = _set_camera(sc, a, frames)
    elif a.scene in ("street", "canyon"):
        _move_camera(sc, a, frames)
        info.update({"radius": [a.radius, a.radius_to], "lens": [a.lens, a.lens_to], "cam_z": [a.cam_z, a.cam_z_to],
                     "look_z": [a.look_z, a.look_z_to]})
    elif a.scene == "orbit":
        _orbit_camera(sc, a, frames)
        info.update({"degrees": a.degrees, "radius": a.radius, "lens": a.lens, "cam_z": a.cam_z,
                     "look_z": a.look_z})
    elif a.scene == "aisle":
        # eye height at the near end of the aisle, drifting a little forward: the stack comes down
        # across the frame between us and the far figure
        look = Vector((0.0, 11.0, 1.35))
        pts = [Vector((0.35, -1.6, 1.6)), Vector((0.3, -1.3, 1.58)), Vector((0.25, -1.0, 1.56))]
    else:
        # a slow arc from front-left to front-right, slightly above, looking at the wall
        look = Vector((0.0, 1.5, 1.0))
        pts = []
        for i in range(5):
            t = i / 4
            ang = math.radians(-35 + 70 * t)
            pts.append(Vector((7.5 * math.sin(ang), 1.5 - 7.5 * math.cos(ang), 2.0 - 0.4 * t)))
    if a.scene not in ("orbit", "street", "canyon", "set"):
        _camera(sc, pts, look, frames)

    if (a.render or ("beauty" if a.scene == "set" else "flat")) == "beauty":
        _beauty(sc)
    else:
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
    if a.scene == "aisle":
        # the impact: the first frame a top crate comes down below 1.2 m
        tops = [bpy.data.objects[n] for n in info.get("tops", []) if n in bpy.data.objects]
        for f in range(1, frames + 1):
            sc.frame_set(f)
            if any(t.matrix_world.translation.z < 1.2 for t in tops):
                info["impact_frame"] = f
                break
    sc.frame_set(1)
    if a.joints:
        _joints(sc, out, frames)
        return

    # a PNG sequence: the flatpak Blender has no video encoder; the wrapper encodes it
    fdir = os.path.join(out, "frames")
    os.makedirs(fdir, exist_ok=True)
    for f in os.listdir(fdir):
        if f.startswith("f_") and f.endswith(".png"):
            os.remove(os.path.join(fdir, f))
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGB"
    sc.render.filepath = os.path.join(fdir, "f_")
    if a.endpoints and frames > 1:
        sc.frame_step = frames - 1          # frames 1 and N: the rigid-body cache is baked through all of them
    bpy.ops.render.render(animation=True)
    sc.frame_step = 1
    if a.depth:
        _depth(sc, out, [1, frames] if a.endpoints and frames > 1 else list(range(1, frames + 1)))
    if a.scene == "set" and a.masks:
        info["mask_frames"], info["surfaces"] = _masks(sc, out, frames, a.masks, info.get("groups", {}))

    info.update({"frames": frames, "fps": a.fps, "width": a.width, "height": a.height,
                 "scene": a.scene, "seed": a.seed})
    json.dump(info, open(os.path.join(out, "previz.json"), "w"), indent=1)
    print("previz (blender side):", json.dumps(info))


if __name__ == "__main__":
    if IN_BLENDER:
        main()
    else:
        _wrapper(sys.argv[1:])
