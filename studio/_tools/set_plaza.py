#!/usr/bin/env python3
"""studio/_tools/set_plaza.py - a small Italian hill-town square, built once as a 3D set.

WHY. Every shot of a scene is drawn from one picture of the place (the plate) plus words, so a
building is only "the same building" while the picture shows it. A reverse angle, an orbit or a
crane invents whatever the plate never saw, and "low angle" is a word the compositor may ignore.
A set answers both: every shot's camera is a position and a lens in ONE world, a building sits
where the map puts it, and what is behind the camera exists. `previz_blender.py --scene set --set
plaza` renders a shot from it; the IC-LoRA control workflow (74) paints the film over its depth.

The square (metres, Z up, +Y north, +X east, the fountain at the origin):

    north   the clock tower (white clock faces, green copper roof); the terracotta town hall with
            an arcade to its west; the pale yellow house with green shutters to its east
    east    the ochre CAFFE building: a red-and-white striped awning, a green sign, tables outside
    south   a stone archway gate onto a road of cypresses and hills; the salmon-pink house (a
            balcony of flowers) to its west; the grey stone bakery with a blue door to its east
    west    the white house with blue shutters and iron balconies; a plane tree in front of it
    middle  the round stone fountain; two benches, four lamp posts, a red scooter by the cafe

Every object carries a "group" - a landmark (tower, fountain, cafe, ...) or ground/props/town/hills -
and a "surface" (group/material: cafe/cafe is the cafe's ochre wall, cafe/awning_red its red stripes),
so a measurement can mask each landmark and each surface in each shot: `previz_blender.py --masks N`
renders the groups in the flat ID colours of GROUPS, and the surfaces in colours of their own, every
N frames.

Run inside Blender by previz_blender.py: build(sc) returns the set's table.
"""
import math

import bpy
from mathutils import Vector

# landmark -> the flat sRGB colour it gets in the ID-mask pass
GROUPS = {
    "tower": (255, 0, 0), "fountain": (0, 255, 0), "cafe": (0, 0, 255), "hall": (255, 255, 0),
    "yellow": (255, 0, 255), "white": (0, 255, 255), "arch": (255, 128, 0), "pink": (128, 0, 255),
    "bakery": (0, 128, 255), "tree": (128, 255, 0), "town": (128, 128, 128), "ground": (64, 64, 64),
    "props": (192, 192, 192), "hills": (0, 128, 0),
}
# the landmarks a measurement compares from shot to shot (the rest is context)
LANDMARKS = ["tower", "fountain", "cafe", "hall", "yellow", "white", "arch", "pink", "bakery", "tree"]

# material -> (sRGB hex, roughness, metallic)
PALETTE = {
    "stone": ("#bfb39c", 0.9, 0.0), "stone_dark": ("#8e8474", 0.9, 0.0), "paving": ("#b7a88f", 0.92, 0.0),
    "road": ("#77716a", 0.95, 0.0), "road_dark": ("#5d5953", 0.95, 0.0), "roof": ("#a5573c", 0.8, 0.0),
    "copper": ("#5e9e88", 0.55, 0.3), "clock": ("#f3f0e6", 0.5, 0.0), "iron": ("#1d1d1f", 0.5, 0.5),
    "glass": ("#26303b", 0.12, 0.0), "frame": ("#f2eee6", 0.6, 0.0),
    "hall": ("#c4683f", 0.85, 0.0), "cafe": ("#d8a13f", 0.85, 0.0), "yellow": ("#eed88c", 0.85, 0.0),
    "white": ("#f1eee6", 0.85, 0.0), "pink": ("#e5a191", 0.85, 0.0), "bakery": ("#aba69c", 0.9, 0.0),
    "shutter_teal": ("#3e8083", 0.6, 0.0), "shutter_green": ("#41703c", 0.6, 0.0),
    "shutter_brown": ("#6c4a2e", 0.7, 0.0), "shutter_blue": ("#3a6fa8", 0.6, 0.0),
    "shutter_olive": ("#6d7b3b", 0.6, 0.0),
    "awning_red": ("#b92429", 0.8, 0.0), "awning_white": ("#f4f0e6", 0.8, 0.0),
    "sign": ("#1e4b36", 0.6, 0.0), "sign_text": ("#ead9a7", 0.5, 0.0),
    "door_blue": ("#2c5f9c", 0.6, 0.0), "door_green": ("#2e5f3d", 0.6, 0.0), "door_wood": ("#5c3b24", 0.7, 0.0),
    "water": ("#3c7d93", 0.05, 0.0), "bark": ("#6b6356", 0.95, 0.0), "leaf": ("#4e7b38", 0.8, 0.0),
    "cypress": ("#2e4b29", 0.8, 0.0), "hill": ("#7f8b56", 0.95, 0.0), "hill_far": ("#93a3aa", 0.95, 0.0),
    "wood": ("#7b5637", 0.8, 0.0), "scooter": ("#c5282d", 0.35, 0.2), "bronze": ("#6e5b3b", 0.4, 0.7),
    "flowers": ("#d8385b", 0.8, 0.0), "table": ("#ebe7dd", 0.5, 0.0),
    "town1": ("#cfa57a", 0.85, 0.0), "town2": ("#e0c9a6", 0.85, 0.0), "town3": ("#c9b8a0", 0.85, 0.0),
    "town4": ("#d9a88b", 0.85, 0.0), "town5": ("#bba58a", 0.85, 0.0), "town6": ("#d4c3a0", 0.85, 0.0),
}
MAT = {}


def lin(hexstr):
    """'#rrggbb' (sRGB) -> linear RGB, what Blender's colour inputs take."""
    h = hexstr.lstrip("#")
    out = []
    for i in (0, 2, 4):
        c = int(h[i:i + 2], 16) / 255.0
        out.append(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4)
    return tuple(out)


def _materials():
    for name, (hx, rough, metal) in PALETTE.items():
        m = bpy.data.materials.new(name)
        try:
            m.use_nodes = True
        except Exception:
            pass
        rgb = lin(hx)
        m.diffuse_color = (*rgb, 1.0)          # what the flat (workbench) previz shows
        bsdf = next((n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None) if m.node_tree else None
        if bsdf is not None:
            bsdf.inputs["Base Color"].default_value = (*rgb, 1.0)
            bsdf.inputs["Roughness"].default_value = rough
            bsdf.inputs["Metallic"].default_value = metal
        MAT[name] = m


class Geo:
    """Geometry gathered per (group, material) and made into one mesh each at the end: thousands of
    boxes as a few dozen objects, which Blender builds in a second instead of a minute."""

    def __init__(self):
        self.parts = {}

    def add(self, group, mat, verts, faces):
        vs, fs = self.parts.setdefault((group, mat), ([], []))
        o = len(vs)
        vs.extend(verts)
        fs.extend(tuple(i + o for i in f) for f in faces)

    def box(self, group, mat, x0, x1, y0, y1, z0, z1):
        v = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
             (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
        self.add(group, mat, v, [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)])

    def cyl(self, group, mat, cx, cy, z0, z1, r, r1=None, n=24):
        """An upright cylinder (or a frustum when r1 is given)."""
        r1 = r if r1 is None else r1
        v = [(cx + r * math.cos(2 * math.pi * i / n), cy + r * math.sin(2 * math.pi * i / n), z0) for i in range(n)]
        v += [(cx + r1 * math.cos(2 * math.pi * i / n), cy + r1 * math.sin(2 * math.pi * i / n), z1) for i in range(n)]
        f = [(i, (i + 1) % n, n + (i + 1) % n, n + i) for i in range(n)]
        f += [tuple(range(n - 1, -1, -1)), tuple(range(n, 2 * n))]
        self.add(group, mat, v, f)

    def cone(self, group, mat, cx, cy, z0, z1, r, n=24):
        v = [(cx + r * math.cos(2 * math.pi * i / n), cy + r * math.sin(2 * math.pi * i / n), z0) for i in range(n)]
        v.append((cx, cy, z1))
        f = [(i, (i + 1) % n, n) for i in range(n)] + [tuple(range(n - 1, -1, -1))]
        self.add(group, mat, v, f)

    def ring(self, group, mat, cx, cy, z0, z1, r_in, r_out, n=48):
        """A solid annulus - a fountain's basin wall."""
        v = []
        for z in (z0, z1):
            for r in (r_out, r_in):
                v += [(cx + r * math.cos(2 * math.pi * i / n), cy + r * math.sin(2 * math.pi * i / n), z)
                      for i in range(n)]
        f = []
        for i in range(n):
            j = (i + 1) % n
            f += [(i, j, 2 * n + j, 2 * n + i), (n + j, n + i, 3 * n + i, 3 * n + j),
                  (2 * n + i, 2 * n + j, 3 * n + j, 3 * n + i), (i, n + i, n + j, j)]
        self.add(group, mat, v, f)

    def gable(self, group, mat, x0, x1, y0, y1, z0, hr, o=0.45, along="x"):
        """A pitched roof over a footprint, ridge along x or y, eaves overhanging by o."""
        x0, x1, y0, y1 = x0 - o, x1 + o, y0 - o, y1 + o
        if along == "x":
            ym = (y0 + y1) / 2
            v = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0), (x0, ym, z0 + hr), (x1, ym, z0 + hr)]
            f = [(0, 1, 5, 4), (2, 3, 4, 5), (0, 4, 3), (1, 2, 5), (0, 3, 2, 1)]
        else:
            xm = (x0 + x1) / 2
            v = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0), (xm, y0, z0 + hr), (xm, y1, z0 + hr)]
            f = [(3, 0, 4, 5), (1, 2, 5, 4), (0, 1, 4), (2, 3, 5), (0, 3, 2, 1)]
        self.add(group, mat, v, f)

    def pyramid(self, group, mat, x0, x1, y0, y1, z0, h):
        v = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0), ((x0 + x1) / 2, (y0 + y1) / 2, z0 + h)]
        self.add(group, mat, v, [(0, 1, 4), (1, 2, 4), (2, 3, 4), (3, 0, 4), (0, 3, 2, 1)])

    def slab(self, group, mat, top, dz):
        """A thin solid under four corner points (a sloping awning stripe)."""
        v = [tuple(p) for p in top] + [(p[0], p[1], p[2] - dz) for p in top]
        self.add(group, mat, v, [(0, 1, 2, 3), (7, 6, 5, 4), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)])

    def prism(self, group, mat, pts, d0, d1, to_world):
        """A convex 2D outline in a facade's own coordinates, extruded out of the wall from d0 to d1."""
        n = len(pts)
        v = [to_world(u, z, d) for d in (d0, d1) for (u, z) in pts]
        f = [tuple(range(n)), tuple(range(2 * n - 1, n - 1, -1))]
        f += [(i, (i + 1) % n, n + (i + 1) % n, n + i) for i in range(n)]
        self.add(group, mat, v, f)

    def flush(self, sc):
        import bmesh
        made = []
        for (group, mat), (vs, fs) in self.parts.items():
            me = bpy.data.meshes.new("%s__%s" % (group, mat))
            me.from_pydata(vs, [], fs)
            me.update()
            bm = bmesh.new()
            bm.from_mesh(me)
            bmesh.ops.recalc_face_normals(bm, faces=bm.faces)      # every box faces outward, whatever its winding
            bm.to_mesh(me)
            bm.free()
            me.materials.append(MAT[mat])
            ob = bpy.data.objects.new(me.name, me)
            sc.collection.objects.link(ob)
            ob["group"] = group
            ob["surface"] = "%s/%s" % (group, mat)
            made.append(ob)
        return made


# ---------------------------------------------------------------- facades
# A facade is named by the way it faces: S (towards -Y), N (+Y), E (+X), W (-X). Along it runs u (x on
# S/N faces, y on E/W faces); d is the distance out of the wall.
def _world(side, plane):
    if side == "S":
        return lambda u, z, d: (u, plane - d, z)
    if side == "N":
        return lambda u, z, d: (u, plane + d, z)
    if side == "E":
        return lambda u, z, d: (plane + d, u, z)
    return lambda u, z, d: (plane - d, u, z)


def _right(side):
    """+1 when u runs to the right of someone looking at the facade, -1 when it runs to their left."""
    return 1 if side in ("S", "E") else -1


def fbox(g, group, mat, side, plane, ua, ub, za, zb, d0, d1):
    if side == "S":
        g.box(group, mat, ua, ub, plane - d1, plane - d0, za, zb)
    elif side == "N":
        g.box(group, mat, ua, ub, plane + d0, plane + d1, za, zb)
    elif side == "E":
        g.box(group, mat, plane + d0, plane + d1, ua, ub, za, zb)
    else:
        g.box(group, mat, plane - d1, plane - d0, ua, ub, za, zb)


def windows(g, group, side, plane, u0, u1, rows, cols, w, h, shutter, skip=(), sill="stone"):
    step = (u1 - u0) / cols
    for ri, z in enumerate(rows):
        for c in range(cols):
            if (ri, c) in skip:
                continue
            u = u0 + (c + 0.5) * step
            fbox(g, group, "frame", side, plane, u - w / 2 - 0.1, u + w / 2 + 0.1, z - 0.1, z + h + 0.1, 0.0, 0.05)
            fbox(g, group, "glass", side, plane, u - w / 2, u + w / 2, z, z + h, 0.0, 0.07)
            if shutter:
                sw = w / 2 + 0.02
                fbox(g, group, shutter, side, plane, u - w / 2 - 0.1 - sw, u - w / 2 - 0.1, z, z + h, 0.0, 0.09)
                fbox(g, group, shutter, side, plane, u + w / 2 + 0.1, u + w / 2 + 0.1 + sw, z, z + h, 0.0, 0.09)
            if sill:
                fbox(g, group, sill, side, plane, u - w / 2 - 0.22, u + w / 2 + 0.22, z - 0.22, z - 0.1, 0.0, 0.16)


def door(g, group, side, plane, u, w, h, mat):
    fbox(g, group, "stone", side, plane, u - w / 2 - 0.25, u + w / 2 + 0.25, 0.0, h + 0.3, 0.0, 0.06)
    fbox(g, group, mat, side, plane, u - w / 2, u + w / 2, 0.0, h, 0.0, 0.09)


def shopfront(g, group, side, plane, ua, ub, za=0.4, zb=2.9):
    fbox(g, group, "frame", side, plane, ua - 0.12, ub + 0.12, za - 0.1, zb + 0.1, 0.0, 0.05)
    fbox(g, group, "glass", side, plane, ua, ub, za, zb, 0.0, 0.07)


def balcony(g, group, side, plane, u, z, bw=1.8):
    fbox(g, group, "stone", side, plane, u - bw / 2, u + bw / 2, z - 0.16, z, 0.0, 0.85)
    k = 0.0
    while k <= bw + 1e-6:
        fbox(g, group, "iron", side, plane, u - bw / 2 + k - 0.02, u - bw / 2 + k + 0.02, z, z + 1.0, 0.78, 0.82)
        k += 0.15
    fbox(g, group, "iron", side, plane, u - bw / 2, u + bw / 2, z + 0.95, z + 1.02, 0.74, 0.84)


def building(g, key, mat, x0, x1, y0, y1, h, along, roof="roof", hr=2.2, cornice="stone"):
    g.box(key, mat, x0, x1, y0, y1, 0.0, h)
    g.box(key, cornice, x0 - 0.3, x1 + 0.3, y0 - 0.3, y1 + 0.3, h - 0.4, h)
    g.gable(key, roof, x0, x1, y0, y1, h, hr, along=along)


def clock(g, group, side, plane, u, z, r):
    """A clock face at ten past ten, the right way round from wherever it is seen."""
    W = _world(side, plane)
    sg = _right(side)
    circle = lambda rr: [(u + rr * math.cos(2 * math.pi * i / 48), z + rr * math.sin(2 * math.pi * i / 48))
                         for i in range(48)]
    g.prism(group, "stone_dark", circle(r + 0.28), 0.0, 0.08, W)
    g.prism(group, "clock", circle(r), 0.0, 0.12, W)
    for k in range(12):
        a = math.radians(90 - 30 * k)
        cu, cz = u + sg * 0.84 * r * math.cos(a), z + 0.84 * r * math.sin(a)
        s = 0.11 if k % 3 == 0 else 0.07
        g.prism(group, "iron", [(cu - s, cz - s), (cu + s, cz - s), (cu + s, cz + s), (cu - s, cz + s)], 0.12, 0.15, W)
    for theta, length, width in ((300.0, 0.55 * r, 0.12), (60.0, 0.82 * r, 0.08)):     # hour at 10, minute at 2
        t = math.radians(theta)
        du, dz = sg * math.sin(t), math.cos(t)
        pu, pz = -dz, du
        tip = (u + du * length, z + dz * length)
        pts = [(u - pu * width - du * 0.15, z - pz * width - dz * 0.15), (tip[0] - pu * width * 0.4, tip[1] - pz * width * 0.4),
               (tip[0] + pu * width * 0.4, tip[1] + pz * width * 0.4), (u + pu * width - du * 0.15, z + pz * width - dz * 0.15)]
        g.prism(group, "iron", pts, 0.15, 0.19, W)


def _ico(sc, group, mat, loc, r, squash=1.0):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=r, location=loc)
    ob = bpy.context.active_object
    ob.scale = (1.0, 1.0, squash)
    ob.data.materials.append(MAT[mat])
    ob["group"] = group
    ob["surface"] = "%s/%s" % (group, mat)
    return ob


def _text(sc, group, mat, body, loc, rot, size):
    cu = bpy.data.curves.new("%s_text" % group, type="FONT")
    cu.body = body
    cu.align_x = "CENTER"
    cu.size = size
    cu.extrude = 0.02
    cu.materials.append(MAT[mat])
    ob = bpy.data.objects.new("%s_text" % group, cu)
    sc.collection.objects.link(ob)
    ob.location = loc
    ob.rotation_euler = rot
    ob["group"] = group
    ob["surface"] = "%s/%s" % (group, mat)
    return ob


def _sky_and_sun(sc):
    """Late afternoon: a warm horizon under a blue sky, the sun low in the west-south-west."""
    w = bpy.data.worlds.new("sky")
    sc.world = w
    try:
        w.use_nodes = True
    except Exception:
        pass
    nt = w.node_tree
    bg = next(n for n in nt.nodes if n.type == "BACKGROUND")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    nt.links.new(tc.outputs["Generated"], sep.inputs[0])
    nt.links.new(sep.outputs["Z"], ramp.inputs["Fac"])
    ramp.color_ramp.elements[0].position = 0.0
    ramp.color_ramp.elements[0].color = (*lin("#f0cf9f"), 1.0)
    ramp.color_ramp.elements[1].position = 0.2
    ramp.color_ramp.elements[1].color = (*lin("#86b0e0"), 1.0)
    nt.links.new(ramp.outputs["Color"], bg.inputs["Color"])
    bg.inputs["Strength"].default_value = 1.2
    sd = bpy.data.lights.new("sun", type="SUN")
    sd.energy = 4.2
    sd.color = (1.0, 0.9, 0.76)
    sd.angle = math.radians(1.2)
    sun = bpy.data.objects.new("sun", sd)
    sc.collection.objects.link(sun)
    # mid-afternoon from the south-west: high enough that the square is mostly in sun
    az, el = math.radians(235.0), math.radians(38.0)       # azimuth from north, clockwise
    to_sun = Vector((math.cos(el) * math.sin(az), math.cos(el) * math.cos(az), math.sin(el)))
    sun.rotation_euler = (-to_sun).to_track_quat("-Z", "Y").to_euler()
    return {"sun_azimuth": 235.0, "sun_elevation": 38.0}


def build(sc, seed=0):
    _materials()
    g = Geo()

    # ------------------------------------------------ the ground
    g.box("ground", "road", -400, 400, -400, 400, -0.2, 0.0)
    g.box("ground", "paving", -16.5, 16.5, -16.5, 16.5, 0.0, 0.03)
    g.cyl("ground", "stone_dark", 0, 0, 0.03, 0.05, 5.2, n=48)
    g.box("ground", "road_dark", -2.2, 2.2, -200, -16.5, 0.0, 0.02)       # the road out through the arch

    # ------------------------------------------------ the fountain
    F = "fountain"
    g.ring(F, "stone", 0, 0, 0.05, 0.85, 2.9, 3.3)
    g.cyl(F, "stone_dark", 0, 0, 0.05, 0.15, 2.9, n=48)
    g.cyl(F, "water", 0, 0, 0.15, 0.62, 2.88, n=48)
    g.cyl(F, "stone", 0, 0, 0.05, 1.4, 0.55, 0.45)
    g.cyl(F, "stone", 0, 0, 1.4, 2.6, 0.28)
    g.cyl(F, "stone", 0, 0, 2.6, 2.9, 0.35, 1.2)
    g.ring(F, "stone", 0, 0, 2.9, 3.1, 1.0, 1.2)
    g.cyl(F, "water", 0, 0, 2.9, 3.02, 1.0)
    g.cyl(F, "bronze", 0, 0, 3.02, 4.3, 0.2, 0.02)

    # ------------------------------------------------ north: the town hall, the clock tower, the yellow house
    H = "hall"
    g.box(H, "hall", -17, -4, 16, 27, 4.2, 11.0)            # upper floors over the arcade
    g.box(H, "hall", -17, -4, 19, 27, 0.0, 4.2)             # ground floor, set back behind it
    for x in (-16.4, -14.05, -11.7, -9.35, -7.0, -4.65):
        g.box(H, "stone", x - 0.35, x + 0.35, 16.15, 16.85, 0.0, 4.2)
    g.box(H, "stone", -17.3, -3.7, 15.7, 27.3, 10.6, 11.0)
    g.box(H, "stone", -17.1, -3.9, 15.9, 16.1, 4.0, 4.4)     # the string course over the arches
    g.gable(H, "roof", -17, -4, 16, 27, 11.0, 2.4, along="x")
    windows(g, H, "S", 16.0, -17, -4, [5.4, 8.3], 5, 1.1, 1.9, "shutter_teal")
    for x in (-13.5, -8.0):
        door(g, H, "S", 19.0, x, 1.6, 3.0, "door_wood")
    windows(g, H, "W", -17.0, 16, 27, [5.4, 8.3], 4, 1.0, 1.8, "shutter_teal")
    windows(g, H, "E", -4.0, 16, 27, [5.4, 8.3], 3, 1.0, 1.8, "shutter_teal")

    T = "tower"
    g.box(T, "stone_dark", -3.6, 3.6, 16.6, 23.8, 0.0, 1.2)
    g.box(T, "stone", -3.2, 3.2, 17.0, 23.4, 1.2, 18.5)
    g.box(T, "stone_dark", -3.5, 3.5, 16.7, 23.7, 18.5, 19.0)
    for (x0, x1) in ((-3.2, -1.9), (1.9, 3.2)):
        for (y0, y1) in ((17.0, 18.3), (22.1, 23.4)):
            g.box(T, "stone", x0, x1, y0, y1, 19.0, 22.8)
    g.box(T, "stone_dark", -3.5, 3.5, 16.7, 23.7, 22.8, 23.4)
    g.cyl(T, "bronze", 0, 20.2, 19.4, 21.8, 1.15, 0.45)                  # the bell
    g.pyramid(T, "copper", -3.4, 3.4, 16.8, 23.6, 23.4, 5.6)
    g.cyl(T, "iron", 0, 20.2, 28.6, 30.8, 0.05)
    door(g, T, "S", 17.0, 0.0, 1.8, 3.2, "door_wood")
    for z in (6.0, 10.2):
        fbox(g, T, "glass", "S", 17.0, -0.35, 0.35, z, z + 1.5, 0.0, 0.05)
    clock(g, T, "S", 17.0, 0.0, 15.3, 1.7)
    clock(g, T, "E", 3.2, 20.2, 15.3, 1.7)
    clock(g, T, "W", -3.2, 20.2, 15.3, 1.7)

    Y = "yellow"
    building(g, Y, "yellow", 4.2, 16.5, 16, 26, 13.0, "x")
    windows(g, Y, "S", 16.0, 4.2, 16.5, [4.5, 7.5, 10.4], 5, 1.0, 1.8, "shutter_green")
    shopfront(g, Y, "S", 16.0, 5.0, 8.2)
    shopfront(g, Y, "S", 16.0, 12.4, 15.6)
    door(g, Y, "S", 16.0, 10.3, 1.3, 2.8, "door_green")
    windows(g, Y, "E", 16.5, 16, 26, [4.5, 7.5, 10.4], 4, 1.0, 1.8, "shutter_green")
    windows(g, Y, "W", 4.2, 16, 26, [4.5, 7.5, 10.4], 3, 1.0, 1.8, "shutter_green")

    # ------------------------------------------------ east: the cafe
    C = "cafe"
    building(g, C, "cafe", 16, 27, -9, 11, 10.5, "y", hr=2.3)
    windows(g, C, "W", 16.0, -9, 11, [4.6, 7.6], 6, 1.0, 1.8, "shutter_brown")
    for (ya, yb) in ((-7.6, -4.4), (0.4, 3.6), (5.6, 8.8)):
        shopfront(g, C, "W", 16.0, ya, yb, 0.4, 2.95)
    door(g, C, "W", 16.0, -2.0, 1.3, 2.9, "door_green")
    windows(g, C, "N", 11.0, 16, 27, [4.6, 7.6], 3, 1.0, 1.8, "shutter_brown")
    windows(g, C, "S", -9.0, 16, 27, [4.6, 7.6], 3, 1.0, 1.8, "shutter_brown")
    ya, k = -8.2, 0
    while ya < 9.8 - 1e-6:                                  # the striped awning, 0.6 m stripes
        yb = min(ya + 0.6, 9.8)
        m = "awning_red" if k % 2 == 0 else "awning_white"
        g.slab(C, m, [(16.0, ya, 3.35), (16.0, yb, 3.35), (13.7, yb, 2.75), (13.7, ya, 2.75)], 0.04)
        g.box(C, m, 13.66, 13.72, ya, yb, 2.48, 2.77)
        ya, k = yb, k + 1
    fbox(g, C, "sign", "W", 16.0, -2.2, 5.2, 3.5, 4.32, 0.0, 0.08)
    _text(sc, C, "sign_text", "CAFFE", (15.9, 1.5, 3.66), (math.pi / 2, 0.0, -math.pi / 2), 0.62)
    for y in (-5.5, 1.0, 7.0):                               # tables outside
        g.cyl("props", "iron", 14.7, y, 0.0, 0.72, 0.05, n=12)
        g.cyl("props", "table", 14.7, y, 0.72, 0.76, 0.38, n=24)
        for dy in (-0.75, 0.75):
            g.box("props", "wood", 14.49, 14.91, y + dy - 0.21, y + dy + 0.21, 0.44, 0.48)
            g.box("props", "wood", 14.49, 14.91, y + dy + (0.19 if dy > 0 else -0.23), y + dy + (0.23 if dy > 0 else -0.19),
                  0.48, 0.92)
            for (lx, ly) in ((14.52, y + dy - 0.18), (14.88, y + dy - 0.18), (14.52, y + dy + 0.18), (14.88, y + dy + 0.18)):
                g.box("props", "iron", lx - 0.02, lx + 0.02, ly - 0.02, ly + 0.02, 0.0, 0.44)
    # a red scooter parked by the cafe
    g.box("props", "scooter", 12.3, 13.5, -9.42, -8.98, 0.28, 0.7)
    g.box("props", "iron", 12.4, 13.0, -9.38, -9.02, 0.7, 0.8)
    g.box("props", "scooter", 13.4, 13.58, -9.4, -9.0, 0.28, 1.02)
    g.box("props", "iron", 13.45, 13.55, -9.55, -8.85, 1.02, 1.07)
    for x0 in (12.22, 13.28):
        g.box("props", "iron", x0, x0 + 0.4, -9.3, -9.1, 0.0, 0.4)

    # ------------------------------------------------ south: the archway gate, the pink house, the bakery
    A = "arch"
    g.box(A, "stone", -4.0, -2.4, -18.5, -16.0, 0.0, 12.5)
    g.box(A, "stone", 2.4, 4.0, -18.5, -16.0, 0.0, 12.5)
    n = 24
    for i in range(n):
        xa = -2.4 + i * 4.8 / n
        xm = xa + 2.4 / n
        zc = 5.5 + math.sqrt(max(0.0, 2.4 ** 2 - xm ** 2))
        g.box(A, "stone", xa, xa + 4.8 / n, -18.5, -16.0, zc, 12.5)
    g.box(A, "stone_dark", -4.3, 4.3, -18.8, -15.7, 12.1, 12.5)
    for i in range(5):
        x = -3.6 + i * 1.8
        g.box(A, "stone", x - 0.45, x + 0.45, -18.5, -16.0, 12.5, 13.4)
    g.box(A, "stone_dark", -0.35, 0.35, -16.2, -16.0, 7.7, 8.5)            # the keystone

    P = "pink"
    building(g, P, "pink", -16.5, -4.0, -27, -16, 12.0, "x")
    windows(g, P, "N", -16.0, -16.5, -4.0, [1.4, 4.4, 7.4], 5, 1.0, 1.8, "shutter_olive", skip=[(0, 0)])
    door(g, P, "N", -16.0, -15.25, 1.3, 2.8, "door_wood")
    balcony(g, P, "N", -16.0, -10.25, 4.2, 2.6)
    for i in range(6):
        u = -11.3 + i * 0.42
        fbox(g, P, "flowers", "N", -16.0, u - 0.16, u + 0.16, 5.2, 5.5, 0.62, 0.84)
    windows(g, P, "E", -4.0, -27, -16, [4.4, 7.4], 2, 1.0, 1.8, "shutter_olive")
    windows(g, P, "W", -16.5, -27, -16, [1.4, 4.4, 7.4], 3, 1.0, 1.8, "shutter_olive")

    B = "bakery"
    building(g, B, "bakery", 4.0, 16.5, -26, -16, 9.5, "x")
    shopfront(g, B, "N", -16.0, 8.5, 14.5, 0.5, 2.8)
    door(g, B, "N", -16.0, 6.3, 1.4, 2.8, "door_blue")
    fbox(g, B, "wood", "N", -16.0, 8.5, 14.5, 3.05, 3.6, 0.0, 0.1)
    windows(g, B, "N", -16.0, 4.0, 16.5, [4.3, 6.9], 4, 1.0, 1.6, "shutter_brown")
    windows(g, B, "W", 4.0, -26, -16, [4.3, 6.9], 2, 1.0, 1.6, "shutter_brown")

    # ------------------------------------------------ west: the white house, the plane tree
    Wh = "white"
    building(g, Wh, "white", -27, -16, -11, 12, 12.5, "y")
    windows(g, Wh, "E", -16.0, -11, 12, [1.4, 4.6, 7.8], 7, 1.0, 1.8, "shutter_blue", skip=[(0, 3)])
    door(g, Wh, "E", -16.0, 0.5, 1.4, 2.9, "door_blue")
    for z in (4.4, 7.6):
        for c in (1, 3, 5):
            balcony(g, Wh, "E", -16.0, -11 + (c + 0.5) * 23 / 7, z, 2.0)
    windows(g, Wh, "N", 12.0, -27, -16, [4.6, 7.8], 3, 1.0, 1.8, "shutter_blue")
    windows(g, Wh, "S", -11.0, -27, -16, [4.6, 7.8], 3, 1.0, 1.8, "shutter_blue")
    g.cyl("tree", "bark", -11.8, 6.8, 0.0, 5.6, 0.38, 0.3, n=16)
    for (x, y, z, r) in ((-11.8, 6.8, 7.2, 3.0), (-10.3, 7.6, 6.4, 2.2), (-13.2, 6.0, 6.6, 2.3),
                         (-11.2, 5.4, 8.4, 2.0), (-12.6, 8.1, 8.2, 2.1)):
        _ico(sc, "tree", "leaf", (x, y, z), r, 0.85)

    # ------------------------------------------------ the rest of the town, the road out, the hills
    for i, (x0, x1, y0, y1, h, al) in enumerate((
            (-31, -20, 15.5, 27, 10.0, "x"), (19.5, 30, 14.5, 27, 11.0, "x"), (-31, -20, -27, -14.5, 9.5, "x"),
            (19.5, 31, -26, -12.5, 10.0, "x"), (-17, -4, 30, 40, 13.0, "x"), (4, 17, 29.5, 40, 12.0, "x"),
            (30, 40, -10, 12, 12.0, "y"), (-40, -30, -12, 12, 11.0, "y"), (-17, -5, -38, -29, 10.0, "x"),
            (5, 17, -37, -29, 11.0, "x"))):
        m = "town%d" % (i % 6 + 1)
        building(g, "town", m, x0, x1, y0, y1, h, al)
        for side, plane, ua, ub in (("S", y0, x0, x1), ("N", y1, x0, x1), ("E", x1, y0, y1), ("W", x0, y0, y1)):
            cols = max(2, int((ub - ua) / 2.6))
            windows(g, "town", side, plane, ua, ub, [z for z in (1.5, 4.5, 7.5, 10.2) if z + 2.2 < h], cols,
                    0.9, 1.6, None, sill=None)
    for y in (-26, -34, -42, -50, -58, -66, -74):
        for x in (-4.2, 4.2):
            g.cyl("hills", "bark", x, y, 0.0, 1.0, 0.15, n=8)
            g.cyl("hills", "cypress", x, y, 0.8, 9.5, 0.95, 0.05, n=12)
    for (x, y, r, h, m) in ((0, -170, 90, 26, "hill"), (-120, -150, 80, 34, "hill_far"), (130, -160, 90, 30, "hill_far"),
                            (0, 190, 110, 40, "hill_far"), (-150, 120, 90, 30, "hill"), (160, 110, 90, 32, "hill"),
                            (200, -20, 100, 36, "hill_far"), (-210, 0, 110, 34, "hill_far")):
        g.cyl("hills", m, x, y, -0.2, h, r, r * 0.12, n=48)

    # ------------------------------------------------ street furniture
    for (x, y) in ((-7.2, -8.6), (8.2, -7.4), (-8.6, 8.8), (11.2, 4.6)):
        g.cyl("props", "iron", x, y, 0.0, 0.4, 0.16, 0.1, n=12)
        g.cyl("props", "iron", x, y, 0.4, 3.6, 0.07, n=12)
        g.box("props", "glass", x - 0.17, x + 0.17, y - 0.17, y + 0.17, 3.6, 4.05)
        g.box("props", "iron", x - 0.22, x + 0.22, y - 0.22, y + 0.22, 4.05, 4.15)
    for (x0, x1, y0, y1, back) in ((-5.85, -5.35, -2.5, -0.5, "x"), (0.5, 2.5, -6.45, -5.95, "y")):
        g.box("props", "wood", x0, x1, y0, y1, 0.42, 0.5)
        if back == "x":
            g.box("props", "wood", x0 - 0.1, x0, y0, y1, 0.5, 0.95)
        else:
            g.box("props", "wood", x0, x1, y0 - 0.1, y0, 0.5, 0.95)
        for (lx, ly) in ((x0 + 0.05, y0 + 0.05), (x1 - 0.05, y0 + 0.05), (x0 + 0.05, y1 - 0.05), (x1 - 0.05, y1 - 0.05)):
            g.box("props", "iron", lx - 0.03, lx + 0.03, ly - 0.03, ly + 0.03, 0.0, 0.42)

    g.flush(sc)
    info = {"set": "plaza", "units": "metres, Z up, +Y north, the fountain at the origin",
            "groups": {k: list(v) for k, v in GROUPS.items()}, "landmarks": LANDMARKS}
    info.update(_sky_and_sun(sc))
    return info
