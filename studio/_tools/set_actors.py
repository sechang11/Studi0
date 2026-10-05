#!/usr/bin/env python3
"""studio/_tools/set_actors.py - jointed stand-ins for characters who MOVE in a set.

A Hunyuan3D model of a character is a statue: it stands where it is put. A set's shot where she walks,
dodges, punches or casts needs a body that bends. So each character gets a PUPPET: a jointed body in her
own height and silhouette (her hair's mass, a skirt, a jester's cap), posed by keyframes. Its depth is
what the IC-LoRA (workflow 74) follows - the engine paints the character from the start frame over the
puppet's motion, the way it paints a cafe over a box.

    p = Puppet("terra", height=1.62, kind="terra", at=(0, 0, 0), turn=180)
    p.key(1, "stand"); p.key(13, "walk_a", at=(0, 0.7, 0)); ...

Facing: like an imported figure, a puppet faces -Y at turn 0 and turns by `turn` degrees (it faces the
compass bearing 180 - turn). Poses are joint rotations in degrees in each joint's own frame, with the
conventions the poses below use: a limb swings FORWARD on a negative X, a knee bends on a positive X, the
spine leans forward on a positive X, the head turns to her left on a positive Z. Run inside Blender.
"""
import math

import bpy

# joint -> (parent, offset from the parent in units of the height, at rest)
JOINTS = {
    "hips": ("root", (0.0, 0.0, 0.53)),
    "spine": ("hips", (0.0, 0.0, 0.06)),
    "neck": ("spine", (0.0, 0.0, 0.27)),
    "l_shoulder": ("spine", (0.11, 0.0, 0.24)), "r_shoulder": ("spine", (-0.11, 0.0, 0.24)),
    "l_elbow": ("l_shoulder", (0.0, 0.0, -0.18)), "r_elbow": ("r_shoulder", (0.0, 0.0, -0.18)),
    "l_hip": ("hips", (0.055, 0.0, -0.02)), "r_hip": ("hips", (-0.055, 0.0, -0.02)),
    "l_knee": ("l_hip", (0.0, 0.0, -0.245)), "r_knee": ("r_hip", (0.0, 0.0, -0.245)),
    "l_ankle": ("l_knee", (0.0, 0.0, -0.245)), "r_ankle": ("r_knee", (0.0, 0.0, -0.245)),
}

# poses: joint -> (x, y, z) degrees; "drop" lowers the hips by that share of the height
POSES = {
    "stand": {"l_shoulder": (0, -8, 0), "r_shoulder": (0, 8, 0), "l_elbow": (-10, 0, 0), "r_elbow": (-10, 0, 0)},
    "walk_a": {"l_hip": (-24, 0, 0), "l_knee": (6, 0, 0), "r_hip": (16, 0, 0), "r_knee": (22, 0, 0),
               "r_shoulder": (-18, 8, 0), "l_shoulder": (16, -8, 0), "l_elbow": (-15, 0, 0), "r_elbow": (-25, 0, 0)},
    "walk_b": {"r_hip": (-24, 0, 0), "r_knee": (6, 0, 0), "l_hip": (16, 0, 0), "l_knee": (22, 0, 0),
               "l_shoulder": (-18, -8, 0), "r_shoulder": (16, 8, 0), "r_elbow": (-15, 0, 0), "l_elbow": (-25, 0, 0)},
    "pass_a": {"l_hip": (-4, 0, 0), "r_hip": (-12, 0, 0), "r_knee": (38, 0, 0), "l_shoulder": (0, -8, 0),
               "r_shoulder": (0, 8, 0), "l_elbow": (-15, 0, 0), "r_elbow": (-15, 0, 0)},
    "pass_b": {"r_hip": (-4, 0, 0), "l_hip": (-12, 0, 0), "l_knee": (38, 0, 0), "l_shoulder": (0, -8, 0),
               "r_shoulder": (0, 8, 0), "l_elbow": (-15, 0, 0), "r_elbow": (-15, 0, 0)},
    "wary": {"spine": (6, 0, 0), "neck": (-4, 0, 0), "l_shoulder": (-25, -14, 0), "r_shoulder": (-25, 14, 0),
             "l_elbow": (-50, 0, 0), "r_elbow": (-50, 0, 0), "l_hip": (-10, 0, 0), "l_knee": (14, 0, 0),
             "r_hip": (8, 0, 0), "r_knee": (12, 0, 0), "drop": 0.03},
    "crouch": {"spine": (24, 0, 0), "l_hip": (-70, -6, 0), "l_knee": (110, 0, 0), "l_ankle": (-40, 0, 0),
               "r_hip": (-60, 6, 0), "r_knee": (105, 0, 0), "r_ankle": (-45, 0, 0), "l_shoulder": (-40, -30, 0),
               "r_shoulder": (-40, 30, 0), "l_elbow": (-40, 0, 0), "r_elbow": (-40, 0, 0), "drop": 0.28},
    "leap": {"spine": (14, 0, 0), "neck": (-10, 0, 0), "l_hip": (-80, 0, 0), "l_knee": (100, 0, 0),
             "r_hip": (-50, 0, 0), "r_knee": (90, 0, 0), "l_shoulder": (-150, -40, 0), "r_shoulder": (-150, 40, 0),
             "l_elbow": (-20, 0, 0), "r_elbow": (-20, 0, 0)},
    "punch_r": {"spine": (10, 0, -22), "r_shoulder": (-88, 6, 0), "r_elbow": (0, 0, 0), "l_shoulder": (-45, -12, 0),
                "l_elbow": (-105, 0, 0), "l_hip": (-38, 0, 0), "l_knee": (32, 0, 0), "r_hip": (24, 0, 0),
                "r_knee": (8, 0, 0), "drop": 0.05},
    "block": {"spine": (-6, 0, 0), "neck": (8, 0, 0), "l_shoulder": (-75, -18, 0), "r_shoulder": (-75, 18, 0),
              "l_elbow": (-115, 0, 0), "r_elbow": (-115, 0, 0), "l_hip": (-14, 0, 0), "l_knee": (22, 0, 0),
              "r_hip": (14, 0, 0), "r_knee": (16, 0, 0), "drop": 0.04},
    "kick_r": {"spine": (-12, 0, 0), "r_hip": (-88, 0, 0), "r_knee": (12, 0, 0), "r_ankle": (20, 0, 0),
               "l_knee": (14, 0, 0), "l_shoulder": (-20, -55, 0), "r_shoulder": (-20, 55, 0),
               "l_elbow": (-40, 0, 0), "r_elbow": (-40, 0, 0)},
    "hit": {"spine": (-22, 0, 8), "neck": (-18, 0, 0), "l_shoulder": (-35, -55, 0), "r_shoulder": (-20, 50, 0),
            "l_elbow": (-30, 0, 0), "r_elbow": (-30, 0, 0), "r_hip": (24, 0, 0), "r_knee": (20, 0, 0),
            "l_hip": (-10, 0, 0), "l_knee": (18, 0, 0), "drop": 0.03},
    "cast": {"spine": (6, 0, 0), "l_shoulder": (-82, -8, 0), "r_shoulder": (-82, 8, 0), "l_elbow": (-12, 0, 0),
             "r_elbow": (-12, 0, 0), "l_hip": (-16, 0, 0), "l_knee": (12, 0, 0), "r_hip": (12, 0, 0),
             "r_knee": (10, 0, 0), "drop": 0.03},
    "shield": {"spine": (14, 0, 0), "neck": (20, 0, 0), "l_shoulder": (-95, -30, 0), "r_shoulder": (-95, 30, 0),
               "l_elbow": (-120, 0, 0), "r_elbow": (-120, 0, 0), "l_hip": (-20, 0, 0), "l_knee": (35, 0, 0),
               "r_hip": (10, 0, 0), "r_knee": (30, 0, 0), "drop": 0.08},
    "creep": {"spine": (26, 0, 0), "neck": (-22, 18, 0), "l_shoulder": (-35, -62, 0), "r_shoulder": (-35, 62, 0),
              "l_elbow": (-70, 0, 0), "r_elbow": (-70, 0, 0), "l_hip": (-18, 0, 0), "l_knee": (34, 0, 0),
              "r_hip": (12, 0, 0), "r_knee": (30, 0, 0), "drop": 0.07},
    "giggle": {"spine": (30, 0, 6), "neck": (-26, -16, 0), "l_shoulder": (-45, -58, 0), "r_shoulder": (-40, 66, 0),
               "l_elbow": (-80, 0, 0), "r_elbow": (-65, 0, 0), "l_hip": (-18, 0, 0), "l_knee": (34, 0, 0),
               "r_hip": (12, 0, 0), "r_knee": (30, 0, 0), "drop": 0.07},
}

KINDS = {
    "terra": {"skin": "#f2d0b8", "body": "#d22b2b", "limb": "#f2d0b8", "leg": "#f2d0b8", "foot": "#b8302a",
              "hair": "#57d9b5", "width": 1.0},
    "jester": {"skin": "#f4f4f2", "body": "#6a3fa0", "limb": "#f2c230", "leg": "#6a3fa0", "foot": "#151515",
               "hair": "#d0307a", "width": 0.85, "hand": "#151515"},
}
_MATS = {}


def _mat(hexstr):
    if hexstr in _MATS:
        return _MATS[hexstr]
    h = hexstr.lstrip("#")
    lin = []
    for i in (0, 2, 4):
        c = int(h[i:i + 2], 16) / 255.0
        lin.append(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4)
    m = bpy.data.materials.new("puppet_" + h)
    try:
        m.use_nodes = True
    except Exception:
        pass
    m.diffuse_color = (*lin, 1.0)
    b = next((n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None) if m.node_tree else None
    if b is not None:
        b.inputs["Base Color"].default_value = (*lin, 1.0)
        b.inputs["Roughness"].default_value = 0.6
    _MATS[hexstr] = m
    return m


def _mesh(name, verts, faces, mat, parent, group):
    import bmesh
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.update()
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me)
    bm.free()
    me.materials.append(mat)
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    ob.parent = parent
    ob["group"] = group
    ob["surface"] = "%s/figure" % group
    return ob


def _tube(a, b, r0, r1, n=10, squash=1.0):
    """A tapered tube between two points (local), its cross-section squashed front to back by `squash`."""
    import numpy as np
    a, b = np.array(a, float), np.array(b, float)
    ax = b - a
    ln = np.linalg.norm(ax) or 1.0
    ax /= ln
    ref = np.array([0.0, 1.0, 0.0]) if abs(ax[1]) < 0.9 else np.array([1.0, 0.0, 0.0])
    u = np.cross(ax, ref)
    u /= np.linalg.norm(u)
    w = np.cross(ax, u)
    v = []
    for c, r in ((a, r0), (b, r1)):
        for i in range(n):
            t = 2 * math.pi * i / n
            p = c + r * math.cos(t) * u + r * squash * math.sin(t) * w
            v.append(tuple(p))
    f = [(i, (i + 1) % n, n + (i + 1) % n, n + i) for i in range(n)]
    f += [tuple(range(n - 1, -1, -1)), tuple(range(n, 2 * n))]
    return v, f


def _blob(c, rx, ry, rz, nl=7, nu=12):
    v = [(c[0], c[1], c[2] - rz)]
    for i in range(1, nl):
        ph = math.pi * i / nl - math.pi / 2
        for j in range(nu):
            th = 2 * math.pi * j / nu
            v.append((c[0] + rx * math.cos(ph) * math.cos(th), c[1] + ry * math.cos(ph) * math.sin(th),
                      c[2] + rz * math.sin(ph)))
    v.append((c[0], c[1], c[2] + rz))
    f = [(0, 1 + (j + 1) % nu, 1 + j) for j in range(nu)]
    for i in range(nl - 2):
        a0, b0 = 1 + i * nu, 1 + (i + 1) * nu
        f += [(a0 + j, a0 + (j + 1) % nu, b0 + (j + 1) % nu, b0 + j) for j in range(nu)]
    top = len(v) - 1
    last = 1 + (nl - 2) * nu
    f += [(last + j, last + (j + 1) % nu, top) for j in range(nu)]
    return v, f


def _box(c, sx, sy, sz):
    x0, x1, y0, y1, z0, z1 = c[0] - sx / 2, c[0] + sx / 2, c[1] - sy / 2, c[1] + sy / 2, c[2] - sz / 2, c[2] + sz / 2
    v = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0), (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
    return v, [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]


class Puppet:
    def __init__(self, name, height, kind, at=(0.0, 0.0, 0.0), turn=0.0):
        self.name, self.h, self.kind = name, height, KINDS[kind]
        H, k = height, self.kind
        wd = k["width"]
        self.root = bpy.data.objects.new(name + "_root", None)
        bpy.context.scene.collection.objects.link(self.root)
        self.root.location = at
        self.root.rotation_euler = (0.0, 0.0, math.radians(turn))
        self.j = {"root": self.root}
        for jn, (par, off) in JOINTS.items():
            e = bpy.data.objects.new("%s_%s" % (name, jn), None)
            bpy.context.scene.collection.objects.link(e)
            e.parent = self.j[par]
            e.location = (off[0] * H * (wd if "shoulder" in jn else 1.0), off[1] * H, off[2] * H)
            self.j[jn] = e
        self.rest_hips = self.j["hips"].location.z
        P = lambda part, v, f, col: _mesh("%s_%s" % (name, part), v, f, _mat(col), self.j[part.split(":")[0]], name)
        P("hips:pelvis", *_box((0, 0, -0.01 * H), 0.17 * H * wd, 0.1 * H, 0.11 * H), k["body"])
        P("spine:torso", *_tube((0, 0, 0), (0, 0, 0.25 * H), 0.075 * H * wd, 0.09 * H * wd, squash=0.62), k["body"])
        P("neck:head", *_blob((0, 0, 0.07 * H), 0.06 * H, 0.065 * H, 0.075 * H), k["skin"])
        for s in ("l", "r"):
            P("%s_shoulder:uarm" % s, *_tube((0, 0, 0), (0, 0, -0.18 * H), 0.024 * H * wd, 0.02 * H * wd), k["limb"])
            P("%s_elbow:farm" % s, *_tube((0, 0, 0), (0, 0, -0.15 * H), 0.02 * H * wd, 0.017 * H * wd), k["limb"])
            P("%s_elbow:hand" % s, *_blob((0, 0, -0.18 * H), 0.024 * H, 0.016 * H, 0.032 * H), k.get("hand", k["skin"]))
            P("%s_hip:thigh" % s, *_tube((0, 0, 0), (0, 0, -0.245 * H), 0.042 * H * wd, 0.03 * H * wd), k["leg"])
            P("%s_knee:shin" % s, *_tube((0, 0, 0), (0, 0, -0.245 * H), 0.03 * H * wd, 0.022 * H * wd), k["leg"])
            foot_len = 0.15 if kind == "jester" else 0.11
            P("%s_ankle:foot" % s, *_box((0, -foot_len / 2 * H + 0.02 * H, -0.012 * H), 0.045 * H, foot_len * H,
                                          0.035 * H), k["foot"])
        if kind == "terra":
            # waist-length hair, a mass behind her head and down her back; a short flared skirt
            P("neck:hair", *_blob((0, 0.055 * H, -0.08 * H), 0.12 * H, 0.07 * H, 0.2 * H), k["hair"])
            P("neck:fringe", *_blob((0, 0.005 * H, 0.1 * H), 0.075 * H, 0.075 * H, 0.06 * H), k["hair"])
            P("hips:skirt", *_tube((0, 0, 0.02 * H), (0, 0, -0.2 * H), 0.085 * H, 0.15 * H, squash=0.8), k["body"])
        if kind == "jester":
            # a two-horned cap, a ruffled collar, spiky hair
            for s in (1, -1):
                P("neck:horn%d" % (s > 0), *_tube((0, 0, 0.12 * H), (s * 0.1 * H, 0.0, 0.2 * H), 0.032 * H, 0.008 * H),
                  "#6a3fa0" if s > 0 else "#f2c230")
            P("neck:collar", *_tube((0, 0, 0.005 * H), (0, 0, -0.02 * H), 0.1 * H, 0.1 * H), "#f4f4f2")
            P("neck:hair", *_blob((0, 0.01 * H, 0.1 * H), 0.075 * H, 0.07 * H, 0.05 * H), k["hair"])

    def pose(self, name_or_dict):
        p = POSES[name_or_dict] if isinstance(name_or_dict, str) else name_or_dict
        for jn in JOINTS:
            r = p.get(jn, (0, 0, 0))
            self.j[jn].rotation_euler = tuple(math.radians(x) for x in r)
        self.j["hips"].location.z = self.rest_hips - p.get("drop", 0.0) * self.h

    def key(self, frame, pose=None, at=None, turn=None, lift=None):
        """Keyframe the puppet at `frame`: a pose (name or dict), where it stands, which way it faces, and
        `lift` metres off the ground (a leap)."""
        if pose is not None:
            self.pose(pose)
            for jn in JOINTS:
                self.j[jn].keyframe_insert("rotation_euler", frame=frame)
            self.j["hips"].keyframe_insert("location", frame=frame)
        if at is not None:
            self.root.location = (at[0], at[1], (at[2] if len(at) > 2 else 0.0) + (lift or 0.0))
            self.root.keyframe_insert("location", frame=frame)
        if turn is not None:
            self.root.rotation_euler = (0.0, 0.0, math.radians(turn))
            self.root.keyframe_insert("rotation_euler", frame=frame)

    def walk(self, f0, f1, path, turn_of=None, step=12, start="a"):
        """Walk from f0 to f1 along path(t) -> (x, y, z), t from 0 to 1, a step every `step` frames."""
        seq = ["walk_a", "pass_a", "walk_b", "pass_b"] if start == "a" else ["walk_b", "pass_b", "walk_a", "pass_a"]
        f, i = f0, 0
        while f <= f1:
            t = (f - f0) / max(1, f1 - f0)
            self.key(f, seq[i % 4], at=path(t), turn=turn_of(t) if turn_of else None)
            f += step // 2
            i += 1


def bearing_turn(frm, to):
    """The `turn` that faces a puppet (or an imported figure) standing at `frm` toward `to`."""
    az = math.degrees(math.atan2(to[0] - frm[0], to[1] - frm[1]))
    return 180.0 - az
