#!/usr/bin/env python3
"""studio/_tools/set_duel.py - a clearing in the forest, for a fight (2026-10-01).

The forest of set_forest.py with a clearing cut around a point on its path, ringed by standing stones, a
boulder and six edge trees built in parts the fight can break. Frames first (playbook §99.10): a shot in
this set carries its camera, where each character stands and which way they face at its first and last
frames, and what the physics breaks - the characters are put into those two frames by set_test.py cast,
and the engine acts between them.

Each shot's choreography comes from its film's acts file (studio/shotscripts/<film>.acts.json), named by
the shot's "action": "duel:<film>:<shot>":

    {"figures": {"terra": {"start": {"at": [x, y], "to": [x, y]}, "end": {...}}, "jester": {...}},
     "done": [event, ...],     every event of the shots before - re-simulated and frozen where it settled
     "live": [event, ...]}     what breaks during this shot, at its own frames

An event: {"ev": "bark"|"snap"|"shock"|"shatter"|"topple"|"leafrain", "f": frame, ...} (see EVENTS).
A figure end can be {"hidden": true}: out of the shot by its last frame. Run inside Blender.
"""
import hashlib
import json
import math
import os
import random

import bpy
from mathutils import Matrix, Vector

import set_actors as A
import set_forest as F

HERE = os.path.dirname(os.path.abspath(__file__))


def _root():
    d = HERE
    for _ in range(8):
        if os.path.isdir(os.path.join(d, "studio", "shotscripts")):
            return d
        d = os.path.dirname(d)
    return os.path.expanduser("~/shared/comfy-studio")


ROOT = _root()
C = (0.5, 28.0)          # the clearing's centre, on the path
R = 9.5                  # its radius
EDGE = {"E1": (-2.1, 21.1), "E2": (-5.6, 29.6), "E3": (-1.2, 39.0), "E4": (2.6, 39.4), "E5": (-4.8, 37.4),
        "E6": (6.6, 33.0),
        # along the path south of the clearing, in the strip the forest leaves bare beside it (round two)
        "S1": (-1.0, 16.0), "S2": (3.7, 13.5), "S3": (2.9, 4.5), "S5": (2.6, 1.0)}
BOULDER = (4.4, 36.0)
STONES = [(8.6, 25.0), (9.4, 28.6), (8.8, 31.8), (-8.2, 32.6)]
GROUPS = {"edgetree": (128, 255, 0), "stones": (255, 128, 128), "rock2": (0, 128, 255), "debris": (255, 0, 128),
          "clearing": (128, 64, 0)}
HEIGHTS = {"terra": 1.62, "jester": 1.88}


def _who(name):
    """jester2, jester3: his illusions - the same sheet, the same height."""
    return name.rstrip("0123456789")
SETTLE = 110             # frames a done event is given to come to rest


def _in_clearing(x, y, pad=0.0):
    return (x - C[0]) ** 2 + (y - C[1]) ** 2 < (R + pad) ** 2


# ------------------------------------------------------------------------------------------- the set
def _edge_tree(name, x, y, r=0.46, h=15.0, seed=1):
    """A tree the fight can break, in parts like the big oak (set_forest._big_tree): a stump and roots, six
    wedges of trunk at 0.9-1.7 m, the rest (trunk, branches, crown) as one object, and an unseen trunk the
    physics moves."""
    rng = random.Random(seed)
    roots = [(*A._tube((x, y, 0.25), (x + 1.6 * r * 3 * math.cos(a), y + 1.6 * r * 3 * math.sin(a), -0.05),
                       r * 0.42, r * 0.12, n=6), 0) for a in (0.4, 1.7, 3.0, 4.3, 5.5)]
    stump = F._object(name + "_stump", [(*A._tube((x, y, -0.1), (x, y, 0.9), r * 1.1, r, n=12), 0)] + roots,
                      ["bark"], "edgetree")
    wedges = []
    for i in range(6):
        a0, a1 = 2 * math.pi * i / 6, 2 * math.pi * (i + 1) / 6
        pts = [(x, y)] + [(x + r * math.cos(a0 + (a1 - a0) * t), y + r * math.sin(a0 + (a1 - a0) * t)) for t in (0, 0.5, 1)]
        n = len(pts)
        v = [(px, py, 0.9) for px, py in pts] + [(px, py, 1.7) for px, py in pts]
        f = [tuple(range(n)), tuple(range(2 * n - 1, n - 1, -1))] + [(k, (k + 1) % n, n + (k + 1) % n, n + k) for k in range(n)]
        wedges.append(F._object("%s_wedge%d" % (name, i), [(v, f, 0)], ["bark"], "edgetree"))
    top = (x + rng.uniform(-0.4, 0.4), y + rng.uniform(-0.4, 0.4), h)
    parts = [(*A._tube((x, y, 1.7), top, r * 0.98, r * 0.45, n=12), 0)]
    for _ in range(3):
        z0 = rng.uniform(0.35, 0.6) * h
        a = rng.uniform(0, 2 * math.pi)
        segs, _ = F._crooked(rng, (x, y, z0), (math.cos(a), math.sin(a), 0.6), rng.uniform(2.2, 3.6), r * 0.4, r * 0.1)
        parts += [(v, f, 0) for v, f in segs]
    for _ in range(4):
        rr = rng.uniform(2.2, 3.4)
        c = (top[0] + rng.uniform(-1.5, 1.5), top[1] + rng.uniform(-1.5, 1.5), rng.uniform(0.62, 0.95) * h)
        parts.append((*F._lumpy(rng, c, rr, rr, rr * 0.7), 1))
    upper = F._object(name + "_upper", parts, ["bark", "leaf_mid"], "edgetree")
    col = F._object(name + "_collider", [(*A._tube((x, y, 1.7), top, r * 0.9, r * 0.5, n=10), 0)], ["bark"], "edgetree")
    col.hide_render = True
    return stump, wedges, upper, col


def _boulder():
    """The clearing's boulder, already cracked into the chunks a blow can throw apart."""
    rng = random.Random(41)
    x, y = BOULDER
    chunks = []
    for i in range(10):
        a = 2 * math.pi * i / 7 + rng.uniform(-0.2, 0.2)
        ring = 0.0 if i >= 7 else 0.75
        z = 0.55 if i < 7 else 0.55 + 0.6 * (i - 6)
        c = (x + ring * math.cos(a), y + ring * math.sin(a), z)
        if i >= 7:
            c = (x + rng.uniform(-0.3, 0.3), y + rng.uniform(-0.3, 0.3), 0.6 + 0.45 * (i - 7))
        rr = rng.uniform(0.55, 0.75)
        chunks.append(F._object("boulder2_chunk%d" % i, [(*F._lumpy(rng, c, rr, rr * 0.9, rr * 0.8, 0.15), 0)],
                                [rng.choice(["rock", "rock", "moss"])], "rock2"))
    return chunks


def build(sc, seed=0):
    old = F._near_landmark
    F._near_landmark = lambda x, y: old(x, y) or _in_clearing(x, y)
    try:
        info = F.build(sc, seed)
    finally:
        F._near_landmark = old
    rng = random.Random(23)
    g = F.P.Geo()
    # the clearing's floor: a lighter ring of grass and leaf litter around the path, tufts, a few stones
    for k in range(70):
        a, d = rng.uniform(0, 2 * math.pi), R * math.sqrt(rng.uniform(0.0, 1.0))
        x, y = C[0] + d * math.cos(a), C[1] + d * math.sin(a)
        if abs(x - F.x_path(y)) < 1.6:
            continue
        g.add("clearing", rng.choice(["moss", "leaf_light", "leaf_mid"]),
              *F._lumpy(rng, (x, y, 0.02), rng.uniform(0.25, 0.6), rng.uniform(0.25, 0.6), 0.06, 0.3))
    for (sx, sy) in STONES:
        hgt = rng.uniform(2.2, 3.0)
        g.add("stones", "stone", *A._tube((sx, sy, -0.1), (sx + rng.uniform(-0.15, 0.15), sy, hgt), 0.45, 0.32, n=7))
        g.add("stones", "moss", *F._lumpy(rng, (sx, sy, hgt * 0.92), 0.4, 0.35, 0.16, 0.2))
    g.add("clearing", "bark_dark", *A._tube((-7.2, 24.5, 0.32), (-6.0, 27.8, 0.36), 0.34, 0.3, n=10))   # a fallen log
    g.flush(sc)
    for i, (name, (x, y)) in enumerate(sorted(EDGE.items())):
        _edge_tree(name, x, y, seed=11 + i)
    _boulder()
    info["groups"].update({k: list(v) for k, v in GROUPS.items()})
    info["landmarks"] = list(info.get("landmarks", [])) + ["edgetree", "stones", "rock2"]
    info["set"] = "duel"
    info["clearing"] = {"centre": list(C), "radius": R, "edge_trees": EDGE, "boulder": list(BOULDER)}
    return info


# ------------------------------------------------------------------------------------------- physics events
def _ob(name):
    return bpy.data.objects[name]


_DRY = False      # building a cached event's pieces: no physics on them at all


def _rel(ob, f0, f1, move=(0, 0, 0), spin=(0, 0, 0)):
    if not _DRY:
        F._release(ob, f0, f1, move=move, spin=spin)


def _rb(ob, **kw):
    if _DRY:
        return ob
    if ob.rigid_body is None:
        F._rigid(ob, **kw)
    return ob


def _passive(name):
    ob = _ob(name)
    if ob.rigid_body is None:
        F._rigid(ob, kind="PASSIVE", shape="CONVEX_HULL")


def _dir(az):
    a = math.radians(az)
    return Vector((math.sin(a), math.cos(a), 0.0))


def ev_bark(e):
    """A blow (an orb, a fireball) takes a bite out of a tree: the wedges on the struck side blown out, bark
    flying. The tree stands. e: tree, f, from_az (the compass bearing the blow comes FROM)."""
    t, f = e["tree"], int(e["f"])
    x, y = EDGE[t]
    _passive(t + "_stump")
    push = -_dir(e.get("from_az", 0))
    rng = random.Random(f + len(t))
    moved = []
    for i in range(6):
        w = _ob("%s_wedge%d" % (t, i))
        a = 2 * math.pi * (i + 0.5) / 6
        side = Vector((math.cos(a), math.sin(a), 0.0))
        if side.dot(-push) < 0.2:            # only the face the blow strikes
            continue
        _rb(w, mass=8.0)
        _rel(w, f, f + 2, move=tuple(side * 0.25 + push * 0.45 + Vector((0, 0, 0.1))),
                   spin=(rng.uniform(-30, 30), rng.uniform(-30, 30), rng.uniform(-50, 50)))
        moved.append(w)
    for k in range(18):
        a = math.atan2(-push.y, -push.x) + rng.uniform(-0.9, 0.9)
        src = Vector((x + 0.45 * math.cos(a), y + 0.45 * math.sin(a), rng.uniform(0.9, 1.8)))
        v, fa = A._blob((0, 0, 0), rng.uniform(0.05, 0.12), rng.uniform(0.04, 0.09), rng.uniform(0.03, 0.05), nl=4, nu=6)
        ob = F._object("%s_chip%d_%d" % (t, f, k), [(v, fa, 0)], ["bark"], "debris")
        ob.location = src
        _rb(ob, mass=0.4, lin=0.1)
        d = (src - Vector((x, y, src.z))).normalized()
        _rel(ob, f, f + 2, move=tuple(d * rng.uniform(0.3, 0.7) + push * 0.3 + Vector((0, 0, rng.uniform(0.1, 0.35)))))
        moved.append(ob)
    return moved


def ev_snap(e):
    """A tree broken at the wedges by a body or a blast: the wedges blown out and the tree above them falling
    toward fall_az. e: tree, f, fall_az."""
    t, f = e["tree"], int(e["f"])
    moved = ev_bark({"tree": t, "f": f, "from_az": (e["fall_az"] + 180) % 360})
    for i in range(6):
        w = _ob("%s_wedge%d" % (t, i))
        if w.rigid_body is None:
            _rb(w, mass=8.0)
            _rel(w, f, f + 2, move=tuple(_dir(e["fall_az"]) * 0.2 + Vector((0, 0, 0.05))))
            moved.append(w)
    up, col = _ob(t + "_upper"), _ob(t + "_collider")
    _rb(col, mass=500.0, lin=0.02, ang=0.08, friction=0.9, bounce=0.02)
    bpy.context.view_layer.update()
    up.parent = col
    up.matrix_parent_inverse = col.matrix_world.inverted()
    d = _dir(e["fall_az"])
    axis = Vector((0, 0, 1)).cross(d)                # tip toward fall_az
    tilt = 9.0
    _rel(col, f + 1, f + 4, move=tuple(d * 0.45 + Vector((0, 0, -0.05))),
               spin=(axis.x * tilt, axis.y * tilt, 0.0))
    moved.append(col)
    return moved


def ev_topple(e):
    """Several trees blown over at once by a blast at `at`: each falls away from it. e: trees, f, at."""
    moved = []
    cx, cy = e["at"]
    for k, t in enumerate(e["trees"]):
        x, y = EDGE[t]
        az = math.degrees(math.atan2(x - cx, y - cy))
        moved += ev_snap({"tree": t, "f": int(e["f"]) + 3 * k, "fall_az": az})
    return moved


def ev_shock(e):
    """A shockwave on the ground at `at`: leaves, twigs and pebbles lying around it thrown outward and up.
    e: at, f, n, radius."""
    f = int(e["f"])
    cx, cy = e["at"]
    rng = random.Random(f * 7 + int(cx * 10))
    moved = []
    for k in range(int(e.get("n", 46))):
        a, d = rng.uniform(0, 2 * math.pi), rng.uniform(0.4, e.get("radius", 3.0))
        p = Vector((cx + d * math.cos(a), cy + d * math.sin(a), 0.04))
        kind = rng.random()
        if kind < 0.5:
            v, fa = A._box((0, 0, 0), rng.uniform(0.1, 0.16), rng.uniform(0.07, 0.11), 0.006)
            mat = rng.choice(["leaf_mid", "leaf_light"])
            lin, mass = 0.9, 0.01
        elif kind < 0.8:
            v, fa = F._lumpy(rng, (0, 0, 0), rng.uniform(0.05, 0.12), rng.uniform(0.05, 0.1), rng.uniform(0.04, 0.08))
            mat, lin, mass = "rock", 0.05, 0.3
        else:
            v, fa = A._tube((0, 0, 0), (rng.uniform(0.2, 0.4), 0, 0), 0.02, 0.01, n=5)
            mat, lin, mass = "bark", 0.3, 0.05
        ob = F._object("shock%d_%d" % (f, k), [(v, fa, 0)], [mat], "debris")
        ob.location = p
        ob.rotation_euler = (rng.uniform(0, 3), rng.uniform(0, 3), rng.uniform(0, 3))
        _rb(ob, mass=mass, lin=lin, ang=0.4)
        out = Vector((math.cos(a), math.sin(a), 0.0))
        _rel(ob, f, f + 2, move=tuple(out * rng.uniform(0.25, 0.6) * (3.2 - d / 2) / 2.5 +
                                            Vector((0, 0, rng.uniform(0.15, 0.4)))),
                   spin=(rng.uniform(-90, 90), rng.uniform(-90, 90), 0))
        moved.append(ob)
    return moved


def ev_shatter(e):
    """The boulder hit from from_az: its chunks thrown away from the blow. e: f, from_az."""
    f = int(e["f"])
    rng = random.Random(f)
    push = -_dir(e.get("from_az", 180))
    moved = []
    x, y = BOULDER
    for i in range(10):
        ob = _ob("boulder2_chunk%d" % i)
        _rb(ob, mass=40.0, lin=0.06, friction=0.8)
        c = Vector(ob.matrix_world.translation)
        out = (c - Vector((x, y, 0.4))).normalized()
        _rel(ob, f, f + 2, move=tuple(out * rng.uniform(0.3, 0.6) + push * rng.uniform(0.35, 0.7) +
                                            Vector((0, 0, rng.uniform(0.15, 0.4)))),
                   spin=(rng.uniform(-60, 60), rng.uniform(-60, 60), rng.uniform(-60, 60)))
        moved.append(ob)
    return moved


def ev_leafrain(e):
    """Leaves shaken loose from the canopy by a blast, drifting down; unseen until they fall. e: at, f, n."""
    f = int(e["f"])
    cx, cy = e["at"]
    rng = random.Random(f * 3 + 1)
    moved = []
    for k in range(int(e.get("n", 70))):
        a, d = rng.uniform(0, 2 * math.pi), rng.uniform(1.0, e.get("radius", 8.0))
        v, fa = A._box((0, 0, 0), rng.uniform(0.11, 0.17), rng.uniform(0.07, 0.11), 0.006)
        ob = F._object("rain%d_%d" % (f, k), [(v, fa, 0)], [rng.choice(["leaf_mid", "leaf_light", "leaf_dark"])], "debris")
        ob.location = (cx + d * math.cos(a), cy + d * math.sin(a), rng.uniform(6.0, 11.0))
        ob.rotation_euler = (rng.uniform(0, 3), rng.uniform(0, 3), rng.uniform(0, 3))
        _rb(ob, mass=0.01, lin=0.95, ang=0.6)
        if not _DRY:
            ob.hide_render = True
            ob.keyframe_insert("hide_render", frame=1)
            ob.hide_render = False
            ob.keyframe_insert("hide_render", frame=f)
        _rel(ob, f, f + 2, move=(rng.uniform(-0.1, 0.1), rng.uniform(-0.1, 0.1), -0.06),
                   spin=(rng.uniform(-40, 40), rng.uniform(-40, 40), rng.uniform(-40, 40)))
        moved.append(ob)
    return moved


def ev_oak(e):
    """The great oak of the first film (set_forest._big_tree) blown at its base and falling west across the
    path. e: f."""
    sc = bpy.context.scene
    return F._fire_physics(int(e["f"]), max(sc.rigidbody_world.point_cache.frame_end, int(e["f"]) + SETTLE))


EVENTS = {"bark": ev_bark, "snap": ev_snap, "topple": ev_topple, "shock": ev_shock, "shatter": ev_shatter,
          "leafrain": ev_leafrain, "oak": ev_oak}


# ------------------------------------------------------------------------------------------- a shot
def _turn(at, mark):
    if "to" in mark:
        tx, ty = mark["to"]
        return A.bearing_turn((at[0], at[1]), (tx, ty))
    return 180.0 - float(mark.get("az", 0.0))


def act(name, sc, frames, info):
    """`duel:<film>:<shot>` - the shot's marks and events from studio/shotscripts/<film>.acts.json."""
    _, film, sid = name.split(":")
    spec = json.load(open(os.path.join(ROOT, "studio", "shotscripts", film + ".acts.json"), encoding="utf-8"))[sid]
    rbw = sc.rigidbody_world
    F._floor()
    for t in EDGE:
        _passive(t + "_stump")
    # everything broken before this shot, where it came to rest - one event at a time, in order. The first
    # shot to need an event's wreckage simulates it and writes where every piece settled; later ones read it
    wdir = os.path.join(ROOT, "studio", "samples", "fight", film, "wreck")
    for e in spec.get("done", []):
        key = hashlib.md5(json.dumps(e, sort_keys=True).encode()).hexdigest()[:12]
        wp = os.path.join(wdir, "%s_%s.json" % (e["ev"], key))
        global _DRY
        _DRY = os.path.exists(wp) and e["ev"] != "oak"
        try:
            moved = EVENTS[e["ev"]](dict(e, f=2))
        finally:
            _DRY = False
        if e["ev"] == "leafrain":
            for ob in moved:
                ob.animation_data_clear()
                ob.hide_render = False
                if ob.rigid_body is not None:
                    ob.rigid_body.linear_damping = 0.1  # down to the ground inside the settling time
        if os.path.exists(wp):
            saved = json.load(open(wp))
            for ob in moved:
                if ob.rigid_body is not None:
                    F._select(ob)
                    bpy.ops.rigidbody.object_remove()
                ob.animation_data_clear()
                if ob.name in saved:
                    ob.matrix_world = Matrix(saved[ob.name])
            continue
        rbw.point_cache.frame_end = max(rbw.point_cache.frame_end, 2 + SETTLE + 5)
        F._freeze(moved, 2 + SETTLE)
        os.makedirs(wdir, exist_ok=True)
        # written whole, then renamed: two renders can need the same wreckage at once
        tmp = "%s.%d.tmp" % (wp, os.getpid())
        with open(tmp, "w") as fh:
            json.dump({ob.name: [list(r) for r in ob.matrix_world] for ob in moved}, fh)
        os.replace(tmp, wp)
    rbw.point_cache.frame_end = max(frames, 2)
    for e in spec.get("live", []):
        rbw.point_cache.frame_end = max(rbw.point_cache.frame_end, frames)
        EVENTS[e["ev"]](e)
    for who, m in spec.get("figures", {}).items():
        s, en = m["start"], m.get("end") or m["start"]
        fig = {"name": who, "sheet": F.SHEETS[_who(who)], "height": HEIGHTS[_who(who)]}
        for tag, mk in (("start", s), ("end", en)):
            if mk.get("hidden"):
                fig[tag] = {"hidden": True, "at": [0.0, 0.0, 0.0], "turn": 0.0}
            else:
                at = [float(mk["at"][0]), float(mk["at"][1]), float(mk["at"][2]) if len(mk["at"]) > 2 else 0.0]
                fig[tag] = {"at": at, "turn": _turn(at, mk)}
        info.setdefault("figures", []).append(fig)
    info["action"] = name
