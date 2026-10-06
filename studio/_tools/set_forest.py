#!/usr/bin/env python3
"""studio/_tools/set_forest.py - a dense, dangerous forest with a path down the middle, and the fight in it.

The set (metres, Z up, +Y north; the path winds north along x = 1.4 sin(y / 10)):

    the big old tree   a huge oak at the path's east edge (3.7, 8.2), a long low branch reaching over the
                       path - the jester waits on it; its trunk is PRE-FRACTURED at fireball height (eight
                       wedges), so the physics can blow it apart and drop the tree across the path
    the dead tree      a crooked grey snag on the west side (-3.4, -4.6)
    the boulder        a mossy boulder on the west side (-3.4, 12)
    the stone lantern  a moss-covered stone lantern on the east side (2.9, -11.5)
    the fallen log     a mossy log along the path's west edge (-2.9, 2)
    the forest         ~700 trees with crowns and low branches, dead snags, undergrowth, brambles, roots
                       across the path, rocks, glowing mushrooms, fog; low warm sun through the canopy

The shots' choreography lives here too (`act(name, ...)`, previz_blender.py --action NAME): Terra and the
jester as jointed puppets (set_actors.py) the IC-LoRA paints over, and Blender's rigid bodies for what
the fight breaks - leaves and twigs falling with his leap, pebbles kicked up, the fireball's explosion,
the tree coming down. Every action records where the characters stand and face at its first and last
frames (info["figures"]) for set_test.py cast.
"""
import math
import random

import bpy
from mathutils import Vector

import set_actors as A
import set_plaza as P

PALETTE = {
    "floor": ("#3b3a2a", 0.95, 0.0), "dirt": ("#8a6e4b", 0.95, 0.0), "bark": ("#4a3b2e", 0.9, 0.0),
    "bark_dark": ("#352a22", 0.9, 0.0), "leaf_dark": ("#1f3b25", 0.85, 0.0), "leaf_mid": ("#2e5232", 0.85, 0.0),
    "leaf_light": ("#4b6f37", 0.85, 0.0), "deadwood": ("#6b6359", 0.9, 0.0), "moss": ("#4f6b33", 0.95, 0.0),
    "rock": ("#7a7a72", 0.9, 0.0), "stone": ("#8c877a", 0.9, 0.0), "thorn": ("#5a2d2a", 0.8, 0.0),
    "vine": ("#2c4a2a", 0.85, 0.0), "glow": ("#7ff5e6", 0.4, 0.0), "magic": ("#ffb347", 0.3, 0.0),
    "lamp_dark": ("#1d1d1a", 0.8, 0.0),
}
EMIT = {"glow": 3.0, "magic": 30.0}
GROUPS = {"bigtree": (255, 0, 0), "deadtree": (0, 255, 255), "boulder": (0, 0, 255), "lantern": (255, 255, 0),
          "log": (255, 0, 255), "path": (255, 128, 0), "forest": (128, 128, 128), "ground": (64, 64, 64),
          "props": (192, 192, 192), "terra": (255, 255, 255), "jester": (0, 255, 0), "magic": (128, 0, 255)}
LANDMARKS = ["bigtree", "deadtree", "boulder", "lantern", "log", "path"]
SHEETS = {"terra": "studio/sheets/terra-in-the-plaza-terra", "jester": "studio/sheets/forest-fight-the-jester",
          "esper": "studio/sheets/the-fire-esper"}
BIG = (3.7, 8.2)


def x_path(y):
    return 1.4 * math.sin(y / 10.0)


def _materials():
    for name, (hx, rough, metal) in PALETTE.items():
        m = bpy.data.materials.new(name)
        try:
            m.use_nodes = True
        except Exception:
            pass
        rgb = P.lin(hx)
        m.diffuse_color = (*rgb, 1.0)
        b = next((n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None) if m.node_tree else None
        if b is not None:
            b.inputs["Base Color"].default_value = (*rgb, 1.0)
            b.inputs["Roughness"].default_value = rough
            if name in EMIT:
                for key in ("Emission Color", "Emission"):
                    if key in b.inputs:
                        b.inputs[key].default_value = (*rgb, 1.0)
                        break
                if "Emission Strength" in b.inputs:
                    b.inputs["Emission Strength"].default_value = EMIT[name]
        P.MAT[name] = m


def _object(name, parts, mats, group):
    """One mesh object from several (verts, faces, material index) parts - a rigid body must be one object."""
    import bmesh
    vs, fs, mi = [], [], []
    for v, f, k in parts:
        o = len(vs)
        vs += v
        fs += [tuple(i + o for i in face) for face in f]
        mi += [k] * len(f)
    me = bpy.data.meshes.new(name)
    me.from_pydata(vs, [], fs)
    me.update()
    for poly, k in zip(me.polygons, mi):
        poly.material_index = k
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me)
    bm.free()
    for m in mats:
        me.materials.append(P.MAT[m])
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    ob["group"] = group
    ob["surface"] = "%s/%s" % (group, mats[0])
    return ob


def _crooked(rng, base, up, length, r0, r1, bends=2):
    """A crooked branch: `bends` tube segments, each turned a little at random."""
    out = []
    p = Vector(base)
    d = Vector(up).normalized()
    seg = length / bends
    for i in range(bends):
        d = (d + Vector((rng.uniform(-0.45, 0.45), rng.uniform(-0.45, 0.45), rng.uniform(-0.15, 0.3)))).normalized()
        q = p + d * seg
        ra = r0 + (r1 - r0) * i / bends
        rb = r0 + (r1 - r0) * (i + 1) / bends
        out.append(A._tube(tuple(p), tuple(q), ra, rb, n=7))
        p = q
    return out, tuple(p)


def _lumpy(rng, c, rx, ry, rz, j=0.12):
    v, f = A._blob(c, rx, ry, rz, nl=6, nu=10)
    v = [(x + rng.uniform(-j, j) * rx, y + rng.uniform(-j, j) * ry, z + rng.uniform(-j, j) * rz) for (x, y, z) in v]
    return v, f


def _near_landmark(x, y):
    for (lx, ly, r) in ((BIG[0], BIG[1], 3.5), (-3.4, -4.6, 2.2), (-3.4, 12.0, 2.4), (2.9, -11.5, 1.8), (-2.9, 2.0, 3.6)):
        if (x - lx) ** 2 + (y - ly) ** 2 < r * r:
            return True
    return False


def _big_tree():
    """The big oak, in parts the fire can take apart: stump and roots (static), eight wedges of trunk at
    fireball height, and the rest of it - trunk, crown and the long low branch - as ONE object."""
    rng = random.Random(77)
    x, y = BIG
    stump = _object("bigtree_stump", [(*A._tube((x, y, -0.1), (x, y, 1.0), 1.05, 0.98, n=16), 0)] +
                    [(*A._tube((x, y, 0.3), (x + 2.2 * math.cos(a), y + 2.2 * math.sin(a), -0.05), 0.42, 0.12, n=7), 0)
                     for a in (0.3, 1.5, 2.6, 3.7, 5.0)], ["bark"], "bigtree")
    wedges = []
    for i in range(8):
        a0, a1 = 2 * math.pi * i / 8, 2 * math.pi * (i + 1) / 8
        rim = [(x + 0.98 * math.cos(a0 + (a1 - a0) * t), y + 0.98 * math.sin(a0 + (a1 - a0) * t)) for t in (0, 0.5, 1)]
        pts = [(x, y)] + rim
        n = len(pts)
        v = [(px, py, 1.0) for px, py in pts] + [(px, py, 2.3) for px, py in pts]
        f = [tuple(range(n)), tuple(range(2 * n - 1, n - 1, -1))] + [(k, (k + 1) % n, n + (k + 1) % n, n + k) for k in range(n)]
        wedges.append(_object("bigtree_wedge%d" % i, [(v, f, 0)], ["bark"], "bigtree"))
    parts = [(*A._tube((x, y, 2.3), (x - 0.4, y + 0.3, 21.0), 0.97, 0.45, n=16), 0)]
    parts.append((*A._tube((x - 0.15, y - 0.1, 4.1), (0.4, 6.7, 4.55), 0.34, 0.16, n=10), 0))     # the low branch
    parts.append((*A._tube((x - 0.25, y + 0.2, 7.5), (x + 3.5, y + 2.5, 11.0), 0.3, 0.12, n=8), 0))
    parts.append((*A._tube((x - 0.3, y + 0.25, 9.0), (x - 3.2, y + 3.0, 12.5), 0.28, 0.12, n=8), 0))
    for (dx, dy, z, r) in ((0, 0, 18.0, 5.0), (-3.0, 1.5, 15.5, 3.8), (3.0, 2.0, 15.0, 3.6), (-1.0, -2.8, 16.0, 3.5),
                           (1.5, 3.5, 19.5, 3.4), (-2.6, 3.6, 12.6, 2.6), (3.3, 3.0, 11.6, 2.4)):
        parts.append((*_lumpy(rng, (x + dx, y + dy, z), r, r, r * 0.72), 1))
    upper = _object("bigtree_upper", parts, ["bark", "leaf_mid"], "bigtree")
    # what the physics moves: the trunk alone, unseen. With the whole tree's convex hull as its shape it
    # landed on its crown and rolled over onto its back; the crown rides along, parented, in _fire_physics
    col = _object("bigtree_collider", [(*A._tube((x, y, 2.3), (x - 0.4, y + 0.3, 21.0), 0.9, 0.5, n=12), 0)],
                  ["bark"], "bigtree")
    col.hide_render = True
    return stump, wedges, upper


def build(sc, seed=0):
    _materials()
    rng = random.Random(seed or 7)
    g = P.Geo()
    # the ground and the path
    g.box("ground", "floor", -90, 90, -90, 100, -0.3, 0.0)
    pv, pf = [], []
    ys = [y * 1.0 for y in range(-70, 81)]
    for k, y in enumerate(ys):
        w = 1.3 + 0.15 * math.sin(y * 0.7)
        pv += [(x_path(y) - w, y, 0.02), (x_path(y) + w, y, 0.02)]
        if k:
            pf.append((2 * k - 2, 2 * k - 1, 2 * k + 1, 2 * k))
    g.add("path", "dirt", pv, pf)
    # the forest
    gx = -46.0
    while gx <= 46.0:
        gy = -50.0
        while gy <= 62.0:
            x, y = gx + rng.uniform(-1.3, 1.3), gy + rng.uniform(-1.3, 1.3)
            gy += 3.2
            if abs(x - x_path(y)) < 2.8 or _near_landmark(x, y):
                continue
            h = rng.uniform(11, 20)
            r = rng.uniform(0.22, 0.55)
            top = (x + rng.uniform(-1, 1), y + rng.uniform(-1, 1), h)
            dead = rng.random() < 0.12
            g.add("forest", "deadwood" if dead else "bark", *A._tube((x, y, -0.1), top, r, r * 0.45, n=8))
            for _ in range(2 if not dead else 4):
                z0 = rng.uniform(0.3, 0.6) * h
                a = rng.uniform(0, 2 * math.pi)
                parts, _ = _crooked(rng, (x, y, z0), (math.cos(a), math.sin(a), 0.6), rng.uniform(1.8, 3.6),
                                    r * 0.45, r * 0.12, bends=2)
                for v, f in parts:
                    g.add("forest", "deadwood" if dead else "bark", v, f)
            if not dead:
                for _ in range(rng.randint(3, 5)):
                    rr = rng.uniform(2.0, 3.4)
                    c = (top[0] + rng.uniform(-1.4, 1.4), top[1] + rng.uniform(-1.4, 1.4), rng.uniform(0.6, 0.95) * h)
                    g.add("forest", rng.choice(["leaf_dark", "leaf_dark", "leaf_mid"]), *_lumpy(rng, c, rr, rr, rr * 0.7))
        gx += 3.2
    # undergrowth along the path, brambles, rocks, roots, mushrooms, vines
    for y in range(-48, 62):
        for s in (-1, 1):
            if rng.random() < 0.7:
                x = x_path(y) + s * rng.uniform(2.1, 6.0)
                if _near_landmark(x, y):
                    continue
                g.add("props", rng.choice(["leaf_dark", "leaf_mid", "leaf_light"]),
                      *_lumpy(rng, (x, y + rng.uniform(-0.4, 0.4), 0.3), rng.uniform(0.6, 1.2), rng.uniform(0.6, 1.2),
                              rng.uniform(0.45, 0.85)))
    for _ in range(26):
        y = rng.uniform(-30, 40)
        x = x_path(y) + rng.choice([-1, 1]) * rng.uniform(1.6, 3.2)
        if _near_landmark(x, y):
            continue
        for _ in range(6):
            parts, _ = _crooked(rng, (x, y, 0.0), (rng.uniform(-1, 1), rng.uniform(-1, 1), 0.7), rng.uniform(0.8, 1.6),
                                0.03, 0.012, bends=3)
            for v, f in parts:
                g.add("props", "thorn", v, f)
    for _ in range(34):
        y = rng.uniform(-40, 50)
        x = x_path(y) + rng.choice([-1, 1]) * rng.uniform(1.8, 9.0)
        if _near_landmark(x, y):
            continue
        rr = rng.uniform(0.25, 0.8)
        g.add("props", rng.choice(["rock", "moss"]), *_lumpy(rng, (x, y, rr * 0.3), rr * 1.3, rr, rr * 0.75, 0.2))
    for y0 in (-8.0, -2.5, 4.5, 10.5, 15.0, -15.0):
        s = 1 if y0 % 2 else -1
        a = (x_path(y0) + s * 2.6, y0, 0.05)
        b = (x_path(y0) + s * 0.6, y0 + rng.uniform(-0.8, 0.8), 0.06)
        g.add("props", "bark_dark", *A._tube(a, b, 0.16, 0.06, n=6))
    for _ in range(22):
        y = rng.uniform(-25, 30)
        x = x_path(y) + rng.choice([-1, 1]) * rng.uniform(2.2, 4.5)
        for _ in range(rng.randint(3, 5)):
            px, py = x + rng.uniform(-0.3, 0.3), y + rng.uniform(-0.3, 0.3)
            hh = rng.uniform(0.08, 0.2)
            g.add("props", "deadwood", *A._tube((px, py, 0), (px, py, hh), 0.015, 0.012, n=6))
            g.add("props", "glow", *A._blob((px, py, hh), 0.05, 0.05, 0.025, nl=4, nu=8))
    for _ in range(18):
        y = rng.uniform(-20, 25)
        x = x_path(y) + rng.choice([-1, 1]) * rng.uniform(2.6, 5.0)
        z = rng.uniform(5.0, 8.0)
        g.add("props", "vine", *A._tube((x, y, z), (x + rng.uniform(-0.3, 0.3), y, z - rng.uniform(2.0, 4.0)), 0.025, 0.015, n=5))

    # the landmarks
    D = "deadtree"
    g.add(D, "deadwood", *A._tube((-3.4, -4.6, -0.1), (-3.0, -4.3, 4.5), 0.42, 0.3, n=10))
    g.add(D, "deadwood", *A._tube((-3.0, -4.3, 4.5), (-3.7, -3.8, 8.0), 0.3, 0.16, n=10))
    drng = random.Random(5)
    for (z0, a) in ((2.8, 0.4), (3.9, 2.4), (5.4, 4.0), (6.8, 1.2), (7.6, 5.3)):
        parts, _ = _crooked(drng, (-3.2, -4.4, z0), (math.cos(a), math.sin(a), 0.5), 2.8, 0.14, 0.03, bends=3)
        for v, f in parts:
            g.add(D, "deadwood", v, f)
    Bd = "boulder"
    brng = random.Random(9)
    g.add(Bd, "rock", *_lumpy(brng, (-3.4, 12.0, 0.6), 1.6, 1.3, 1.1, 0.1))
    g.add(Bd, "moss", *_lumpy(brng, (-3.4, 12.0, 1.25), 1.25, 1.0, 0.55, 0.1))
    L = "lantern"
    lx, ly = 2.9, -11.5
    g.box(L, "stone", lx - 0.45, lx + 0.45, ly - 0.45, ly + 0.45, 0.0, 0.25)
    g.add(L, "stone", *A._tube((lx, ly, 0.25), (lx, ly, 1.05), 0.16, 0.14, n=10))
    g.box(L, "stone", lx - 0.42, lx + 0.42, ly - 0.42, ly + 0.42, 1.05, 1.15)
    g.box(L, "stone", lx - 0.3, lx + 0.3, ly - 0.3, ly + 0.3, 1.15, 1.6)
    g.box(L, "lamp_dark", lx - 0.31, lx + 0.31, ly - 0.16, ly + 0.16, 1.25, 1.5)
    g.add(L, "stone", *A._tube((lx, ly, 1.6), (lx, ly, 1.95), 0.62, 0.08, n=8))
    g.add(L, "moss", *_lumpy(random.Random(3), (lx + 0.1, ly, 1.68), 0.45, 0.4, 0.12, 0.2))
    Lg = "log"
    g.add(Lg, "bark", *A._tube((-3.0, -0.9, 0.38), (-2.6, 4.8, 0.42), 0.44, 0.37, n=12))
    for t in (0.1, 0.45, 0.8):
        g.add(Lg, "moss", *_lumpy(random.Random(int(t * 10)), (-3.0 + 0.4 * t, -0.9 + 5.7 * t, 0.78), 0.35, 0.8, 0.12, 0.2))
    g.flush(sc)
    _big_tree()
    _light(sc)
    return {"set": "forest", "units": "metres, Z up, +Y north, the path along x = 1.4 sin(y/10)",
            "groups": {k: list(v) for k, v in GROUPS.items()}, "landmarks": list(LANDMARKS)}


def _light(sc):
    """Late afternoon under a dense canopy: a dim teal world, a low warm sun through the gaps, fog."""
    w = bpy.data.worlds.new("forest_sky")
    sc.world = w
    try:
        w.use_nodes = True
    except Exception:
        pass
    nt = w.node_tree
    bg = next(n for n in nt.nodes if n.type == "BACKGROUND")
    bg.inputs["Color"].default_value = (*P.lin("#7fa8a0"), 1.0)
    # no world volume: Eevee rendered the whole forest black under even a light fog (density 0.012); the
    # dress paints the mist from its words instead
    bg.inputs["Strength"].default_value = 1.5
    sd = bpy.data.lights.new("sun", type="SUN")
    sd.energy = 4.6
    sd.color = (1.0, 0.86, 0.66)
    sd.angle = math.radians(2.0)
    sun = bpy.data.objects.new("sun", sd)
    sc.collection.objects.link(sun)
    az, el = math.radians(210.0), math.radians(34.0)
    to_sun = Vector((math.cos(el) * math.sin(az), math.cos(el) * math.cos(az), math.sin(el)))
    sun.rotation_euler = (-to_sun).to_track_quat("-Z", "Y").to_euler()


# ---------------------------------------------------------------- physics
def _select(ob):
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    bpy.context.view_layer.objects.active = ob
    ob.select_set(True)


def _rigid(ob, kind="ACTIVE", shape="CONVEX_HULL", mass=1.0, lin=0.04, ang=0.1, friction=0.6, bounce=0.1):
    _select(ob)
    # a rigid body turns about its ORIGIN: the oak's parts are built in world coordinates (origin at the
    # world's), so the origin goes to the part's own centre of mass first
    try:
        bpy.ops.object.origin_set(type="ORIGIN_CENTER_OF_MASS", center="BOUNDS")
    except Exception:
        pass
    bpy.ops.rigidbody.object_add()
    rb = ob.rigid_body
    rb.type, rb.collision_shape, rb.mass = kind, shape, mass
    rb.linear_damping, rb.angular_damping, rb.friction, rb.restitution = lin, ang, friction, bounce
    return rb


def _floor():
    ob = bpy.data.objects.get("ground__floor")
    if ob is not None and ob.rigid_body is None:
        _rigid(ob, kind="PASSIVE", shape="BOX")


def _release(ob, f0, f1, move=(0, 0, 0), spin=(0, 0, 0)):
    """Held still (kinematic) until f0, moved by `move` (and turned by `spin` degrees) by f1, then free: the
    body leaves with the velocity of that last push."""
    rb = ob.rigid_body
    rb.kinematic = True
    rb.keyframe_insert("kinematic", frame=1)
    ob.keyframe_insert("location", frame=f0)
    ob.keyframe_insert("rotation_euler", frame=f0)
    ob.location = Vector(ob.location) + Vector(move)
    ob.rotation_euler = tuple(r + math.radians(s) for r, s in zip(ob.rotation_euler, spin))
    ob.keyframe_insert("location", frame=f1)
    ob.keyframe_insert("rotation_euler", frame=f1)
    rb.keyframe_insert("kinematic", frame=f1)
    rb.kinematic = False
    rb.keyframe_insert("kinematic", frame=f1 + 1)


def _magic(name, keys):
    """A glowing orb keyed through (frame, (x, y, z), scale) - a fireball, then its blast."""
    v, f = A._blob((0, 0, 0), 1.0, 1.0, 1.0, nl=8, nu=14)
    ob = _object(name, [(v, f, 0)], ["magic"], "magic")
    for fr, loc, s in keys:
        ob.location = loc
        ob.scale = (max(s, 1e-3),) * 3
        ob.keyframe_insert("location", frame=fr)
        ob.keyframe_insert("scale", frame=fr)
    return ob


def _fire_physics(f_hit, frames_total):
    """The fireball's impact on the big oak at f_hit: the wedges blown out, bark flying, and the tree -
    pushed west - falling across the path."""
    sc = bpy.context.scene
    sc.rigidbody_world.point_cache.frame_end = max(sc.rigidbody_world.point_cache.frame_end, frames_total)
    _floor()
    stump = bpy.data.objects["bigtree_stump"]
    _rigid(stump, kind="PASSIVE", shape="CONVEX_HULL")
    rng = random.Random(31)
    moved = []
    for i in range(8):
        w = bpy.data.objects["bigtree_wedge%d" % i]
        _rigid(w, mass=25.0, shape="CONVEX_HULL")
        a = 2 * math.pi * (i + 0.5) / 8
        toward = Vector((math.cos(a), math.sin(a), 0.0))
        # the side facing the blast (south-west) goes in hardest
        k = 0.55 + 0.45 * max(0.0, -toward.y * 0.6 - toward.x * 0.8)
        _release(w, f_hit, f_hit + 2, move=tuple(toward * 0.55 * k + Vector((0, 0, 0.12))),
                 spin=(rng.uniform(-25, 25), rng.uniform(-25, 25), rng.uniform(-40, 40)))
        moved.append(w)
    up = bpy.data.objects["bigtree_upper"]
    col = bpy.data.objects["bigtree_collider"]
    _rigid(col, mass=900.0, shape="CONVEX_HULL", lin=0.02, ang=0.08, friction=0.9, bounce=0.02)
    bpy.context.view_layer.update()
    up.parent = col
    up.matrix_parent_inverse = col.matrix_world.inverted()
    # pushed hard enough to land inside a five-second shot (a 20 m tree tipped gently takes over four)
    _release(col, f_hit + 1, f_hit + 4, move=(-0.5, -0.08, -0.05), spin=(0, -8.0, 0))
    moved.append(col)
    for k in range(26):
        a = rng.uniform(math.pi * 0.9, math.pi * 1.6)
        src = Vector((BIG[0] + 0.9 * math.cos(a), BIG[1] + 0.9 * math.sin(a), rng.uniform(1.2, 2.2)))
        v, f = A._blob((0, 0, 0), rng.uniform(0.05, 0.14), rng.uniform(0.04, 0.1), rng.uniform(0.03, 0.06), nl=4, nu=6)
        ob = _object("bigtree_bark%d" % k, [(v, f, 0)], ["bark"], "bigtree")
        ob.location = src
        _rigid(ob, mass=0.6, shape="CONVEX_HULL", lin=0.1)
        d = (src - Vector((BIG[0], BIG[1], src.z))).normalized()
        _release(ob, f_hit, f_hit + 2, move=tuple(d * rng.uniform(0.4, 0.9) + Vector((0, 0, rng.uniform(0.1, 0.4)))))
        moved.append(ob)
    return moved


def _freeze(obs, frame):
    """Bake, read where everything came to rest at `frame`, and make it the set: the wreckage of one shot
    is the scenery of the next."""
    sc = bpy.context.scene
    bpy.ops.ptcache.bake_all(bake=True)
    sc.frame_set(frame)
    mats = {o.name: o.matrix_world.copy() for o in obs}
    bpy.ops.ptcache.free_bake_all()
    for o in obs:
        if o.rigid_body is not None:
            _select(o)
            bpy.ops.rigidbody.object_remove()
        o.animation_data_clear()
        o.matrix_world = mats[o.name]
    stump = bpy.data.objects.get("bigtree_stump")
    if stump is not None and stump.rigid_body is not None:
        _select(stump)
        bpy.ops.rigidbody.object_remove()
    sc.frame_set(1)


# ---------------------------------------------------------------- the shots
def _fig(info, name, height, start, end=None):
    info.setdefault("figures", []).append({"name": name, "sheet": SHEETS[name], "height": height,
                                           "start": {"at": list(start[0]), "turn": start[1]},
                                           "end": {"at": list((end or start)[0]), "turn": (end or start)[1]}})


def _on_path(y, dx=0.0):
    return (x_path(y) + dx, y, 0.0)


def _path_turn(y):
    """The turn that faces north along the path at y."""
    return 180.0 - math.degrees(math.atan2(0.14 * math.cos(y / 10.0), 1.0))


def act(name, sc, frames, info):
    return {"walk_far": _walk_far, "walk_toward": _walk_toward, "watched": _watched, "drop": _drop,
            "blows": _blows, "fire": _fire, "aftermath": _aftermath}[name](sc, frames, info)


def _walk_far(sc, frames, info):
    t = A.Puppet("terra", 1.62, "terra")
    y0, y1 = -7.0, -1.6
    t.walk(1, frames, lambda u: _on_path(y0 + (y1 - y0) * u), lambda u: _path_turn(y0 + (y1 - y0) * u))
    _fig(info, "terra", 1.62, (_on_path(y0), _path_turn(y0)), (_on_path(y1), _path_turn(y1)))


def _walk_toward(sc, frames, info):
    t = A.Puppet("terra", 1.62, "terra")
    y0, y1 = -4.4, -0.8
    t.walk(1, frames, lambda u: _on_path(y0 + (y1 - y0) * u), lambda u: _path_turn(y0 + (y1 - y0) * u))
    # she looks round as she walks: the head turned left, then right
    for f, yaw in ((1, 0), (30, 28), (60, -24), (frames, 0)):
        t.j["neck"].rotation_euler = (0.0, 0.0, math.radians(yaw))
        t.j["neck"].keyframe_insert("rotation_euler", frame=f)
    _fig(info, "terra", 1.62, (_on_path(y0), _path_turn(y0)), (_on_path(y1), _path_turn(y1)))


def _watched(sc, frames, info):
    t = A.Puppet("terra", 1.62, "terra")
    y0, y1 = -2.8, 0.6
    t.walk(1, frames, lambda u: _on_path(y0 + (y1 - y0) * u), lambda u: _path_turn(y0 + (y1 - y0) * u))
    rng = random.Random(4)
    g = P.Geo()
    # his view from the oak's low branch: leaves right at the lens
    for (x, y, z, r) in ((1.0, 6.45, 4.5, 0.2), (2.75, 6.55, 4.95, 0.22), (1.25, 6.35, 4.05, 0.16)):
        g.add("props", "leaf_mid", *_lumpy(rng, (x, y, z), r, r * 0.8, r * 0.6, 0.25))
    g.flush(sc)
    _fig(info, "terra", 1.62, (_on_path(y0), _path_turn(y0)), (_on_path(y1), _path_turn(y1)))


def _drop(sc, frames, info):
    """He waits on the oak's low branch, crouches and drops onto the path in front of her; leaves and twigs
    come down with him; she stops."""
    t = A.Puppet("terra", 1.62, "terra")
    t.walk(1, 25, lambda u: _on_path(0.2 + 1.4 * u), lambda u: _path_turn(0.2 + 1.4 * u))
    tpos = _on_path(1.6)
    t.key(32, "stand", at=tpos)
    t.key(48, "wary", at=tpos)
    t.key(frames, "wary", at=tpos)
    branch = (1.7, 7.35, 4.48)
    land = _on_path(5.4)
    jt = A.bearing_turn(branch, tpos)
    j = A.Puppet("jester", 1.88, "jester", at=branch, turn=jt)
    j.key(1, "creep", at=branch, turn=jt)
    j.key(22, "giggle", at=branch)
    j.key(30, "crouch", at=branch)
    for fr, u, pose in ((36, 0.25, "leap"), (42, 0.55, "leap"), (48, 0.85, "leap")):
        p = (branch[0] + (land[0] - branch[0]) * u, branch[1] + (land[1] - branch[1]) * u,
             branch[2] * (1 - u) + 1.1 * math.sin(math.pi * u))
        j.key(fr, pose, at=p)
    j.key(53, "crouch", at=land, turn=A.bearing_turn(land, tpos))
    j.key(72, "creep", at=land)
    j.key(frames, "giggle", at=land)
    _floor()
    rng = random.Random(12)
    for k in range(34):
        v, f = A._box((0, 0, 0), rng.uniform(0.09, 0.14), rng.uniform(0.06, 0.1), 0.006)
        ob = _object("leaf%d" % k, [(v, f, 0)], [rng.choice(["leaf_mid", "leaf_light"])], "props")
        ob.location = (branch[0] + rng.uniform(-1.2, 1.4), branch[1] + rng.uniform(-0.8, 0.8), branch[2] + rng.uniform(0.0, 1.6))
        ob.rotation_euler = (rng.uniform(0, 3), rng.uniform(0, 3), rng.uniform(0, 3))
        _rigid(ob, mass=0.01, shape="BOX", lin=0.93, ang=0.6)
        _release(ob, 28, 31, move=(rng.uniform(-0.1, 0.1), rng.uniform(-0.1, 0.1), -0.05), spin=(40, 30, 20))
    for k in range(6):
        a = (branch[0] + rng.uniform(-0.6, 0.6), branch[1] + rng.uniform(-0.4, 0.4), branch[2] + 0.2)
        v, f = A._tube(a, (a[0] + rng.uniform(-0.3, 0.3), a[1] + rng.uniform(-0.3, 0.3), a[2] + rng.uniform(0.1, 0.3)), 0.02, 0.01, n=5)
        ob = _object("twig%d" % k, [(v, f, 0)], ["bark"], "props")
        _rigid(ob, mass=0.05, shape="CONVEX_HULL", lin=0.25)
        _release(ob, 30, 33, move=(rng.uniform(-0.1, 0.1), -0.1, -0.08))
    _fig(info, "terra", 1.62, (_on_path(0.2), _path_turn(0.2)), (tpos, _path_turn(1.6)))
    _fig(info, "jester", 1.88, (branch, jt), (land, A.bearing_turn(land, tpos)))


def _blows(sc, frames, info):
    """He lunges and punches; she blocks; she kicks him back; pebbles kicked up where he skids."""
    tpos = _on_path(2.0)
    t = A.Puppet("terra", 1.62, "terra")
    j0, j1, j2 = _on_path(4.9), _on_path(3.15), _on_path(5.3)
    tt = A.bearing_turn(tpos, j0)
    t.key(1, "wary", at=tpos, turn=tt)
    t.key(14, "wary")
    t.key(22, "block")
    t.key(32, "block")
    t.key(40, "wary")
    t.key(48, "kick_r")
    t.key(56, "kick_r")
    t.key(68, "wary")
    t.key(frames, "wary")
    j = A.Puppet("jester", 1.88, "jester")
    jt = A.bearing_turn(j0, tpos)
    j.key(1, "creep", at=j0, turn=jt)
    j.key(12, "creep", at=j0)
    j.key(22, "punch_r", at=j1)
    j.key(30, "punch_r", at=j1)
    j.key(40, "creep", at=j1)
    j.key(50, "hit", at=(j1[0], j1[1] + 0.4, 0.0))
    j.key(62, "hit", at=j2)
    j.key(78, "creep", at=j2)
    j.key(frames, "giggle", at=j2)
    _floor()
    rng = random.Random(21)
    for k in range(14):
        p = (j1[0] + rng.uniform(-0.4, 0.4), j1[1] + rng.uniform(0.2, 1.6), 0.05)
        v, f = _lumpy(rng, (0, 0, 0), rng.uniform(0.03, 0.07), rng.uniform(0.03, 0.06), rng.uniform(0.02, 0.05), 0.2)
        ob = _object("pebble%d" % k, [(v, f, 0)], ["rock"], "props")
        ob.location = p
        _rigid(ob, mass=0.2, shape="CONVEX_HULL", lin=0.05)
        _release(ob, 52, 54, move=(rng.uniform(-0.15, 0.15), rng.uniform(0.15, 0.45), rng.uniform(0.15, 0.35)))
    _fig(info, "terra", 1.62, (tpos, tt), (tpos, tt))
    _fig(info, "jester", 1.88, (j0, jt), (j2, A.bearing_turn(j2, tpos)))


FIRE_T = (0.3, 1.5, 0.0)
FIRE_J = (2.0, 4.85, 0.0)
FIRE_DODGE = (0.35, 5.7, 0.0)
FIRE_HIT = 40
FIRE_FRAMES = 121          # the fire shot's length: the aftermath freezes the wreckage where it ends


def _fire(sc, frames, info):
    """She casts: a fireball from her hands; he flips aside; it strikes the oak behind him - the trunk bursts
    and the tree comes down across the path."""
    t = A.Puppet("terra", 1.62, "terra")
    tt = A.bearing_turn(FIRE_T, FIRE_J)
    t.key(1, "wary", at=FIRE_T, turn=tt)
    t.key(13, "cast")
    t.key(36, "cast")
    t.key(44, "shield")
    t.key(70, "shield")
    t.key(96, "wary")
    t.key(frames, "wary")
    j = A.Puppet("jester", 1.88, "jester")
    jt = A.bearing_turn(FIRE_J, FIRE_T)
    j.key(1, "creep", at=FIRE_J, turn=jt)
    j.key(14, "giggle", at=FIRE_J)
    j.key(19, "crouch", at=FIRE_J)
    j.key(24, "leap", at=((FIRE_J[0] + FIRE_DODGE[0]) / 2, (FIRE_J[1] + FIRE_DODGE[1]) / 2, 0.0), lift=0.9)
    j.key(30, "crouch", at=FIRE_DODGE, turn=A.bearing_turn(FIRE_DODGE, FIRE_T))
    j.key(48, "crouch", at=FIRE_DODGE)
    j.key(76, "creep", at=FIRE_DODGE)
    j.key(frames, "giggle", at=FIRE_DODGE)
    face = math.radians(180.0 - tt)
    hands = (FIRE_T[0] + 0.5 * math.sin(face), FIRE_T[1] + 0.5 * math.cos(face), 1.22)
    hit = (BIG[0] - 0.95, BIG[1] - 0.55, 1.65)
    _magic("fireball", [(11, hands, 0.0), (14, hands, 0.12), (21, hands, 0.32),
                        (FIRE_HIT - 1, hit, 0.36), (FIRE_HIT + 4, hit, 2.2), (FIRE_HIT + 12, hit, 1.6),
                        (FIRE_HIT + 20, hit, 0.0)])
    _fire_physics(FIRE_HIT, frames)
    _fig(info, "terra", 1.62, (FIRE_T, tt), (FIRE_T, tt))
    _fig(info, "jester", 1.88, (FIRE_J, jt), (FIRE_DODGE, A.bearing_turn(FIRE_DODGE, FIRE_T)))


def _aftermath(sc, frames, info):
    """The same fire, simulated again and frozen where it came to rest: the tree lies across the path. He
    crouches on its trunk, giggling; she faces him over it."""
    hit = 4
    stop = hit + (FIRE_FRAMES - FIRE_HIT)       # the same moment after the impact as the fire shot's last frame
    moved = _fire_physics(hit, stop + 2)
    up = bpy.data.objects["bigtree_upper"]
    sc.frame_set(1)
    bpy.context.view_layer.update()
    rest = up.matrix_world.inverted()           # world -> the trunk's own coordinates, before it falls
    base_l = rest @ Vector((BIG[0], BIG[1], 2.3))
    top_l = rest @ Vector((BIG[0] - 0.4, BIG[1] + 0.3, 21.0))
    _freeze(moved, stop)
    sc.rigidbody_world.point_cache.frame_end = frames
    bpy.context.view_layer.update()
    # where the fallen trunk crosses the path: the top of the trunk there
    base = up.matrix_world @ base_l
    top = up.matrix_world @ top_l
    best, perch = 1e9, None
    for k in range(200):
        u = k / 199
        p = base.lerp(top, u)
        d = abs(p.x - x_path(p.y))
        if d < best:
            best, perch = d, p
    perch = (perch.x, perch.y, perch.z + 0.75)
    tpos = _on_path(perch[1] - 3.2)
    t = A.Puppet("terra", 1.62, "terra")
    tt = A.bearing_turn(tpos, perch)
    t.key(1, "wary", at=tpos, turn=tt)
    t.key(frames, "cast", at=tpos)
    j = A.Puppet("jester", 1.88, "jester")
    jt = A.bearing_turn(perch, tpos)
    j.key(1, "crouch", at=perch, turn=jt)
    j.key(30, "giggle", at=perch)
    j.key(60, "crouch", at=perch)
    j.key(frames, "giggle", at=perch)
    info["fallen_trunk"] = {"base": list(base), "top": list(top), "perch": list(perch)}
    _fig(info, "terra", 1.62, (tpos, tt), (tpos, tt))
    _fig(info, "jester", 1.88, (perch, jt), (perch, jt))
