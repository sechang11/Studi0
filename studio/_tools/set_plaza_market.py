#!/usr/bin/env python3
"""studio/_tools/set_plaza_market.py - the plaza (set_plaza.py) on a market afternoon: the same square with
things added, so a scene can test whether ADDED things stay put from shot to shot as well as the buildings:

    a fruit stall      a yellow-and-white striped canopy over crates of oranges, lemons and apples, in
                       front of the town hall's arcade (north-west)
    a red bicycle      a wicker basket of flowers on the front, leaning on the fountain's west side
    flower pots        terracotta pots of red flowers along the cafe and either side of the yellow
                       house's door
    string lights      two strings of bulbs across the square, one over the fountain

Each is its own group (stall, bicycle, pots, lights) with its own ID colour, so set_measure.py masks it.
Run inside Blender by previz_blender.py --scene set --set plaza_market.
"""
import math

import set_plaza as P

P.PALETTE.update({
    "canopy_yellow": ("#e9c23c", 0.8, 0.0), "oranges": ("#e8741e", 0.7, 0.0), "lemons": ("#f2d23a", 0.7, 0.0),
    "apples": ("#7fb33a", 0.7, 0.0), "bike_red": ("#c0262b", 0.35, 0.3), "tire": ("#1b1b1b", 0.8, 0.0),
    "wicker": ("#b88a4e", 0.9, 0.0), "terracotta": ("#b5552f", 0.85, 0.0), "foliage": ("#3f7a35", 0.8, 0.0),
    "bloom": ("#e04a6a", 0.8, 0.0), "bulb": ("#fff3cf", 0.3, 0.0), "wire": ("#2a2a2a", 0.6, 0.0),
})
EXTRA_GROUPS = {"stall": (255, 0, 128), "bicycle": (0, 255, 128), "pots": (128, 255, 255),
                "lights": (255, 255, 128)}


def _quad(g, group, mat, W, p, q, w, d0, d1):
    """A straight tube between two points in a vertical plane (a bicycle's frame), w wide."""
    du, dz = q[0] - p[0], q[1] - p[1]
    n = math.hypot(du, dz) or 1.0
    pu, pz = -dz / n * w / 2, du / n * w / 2
    g.prism(group, mat, [(p[0] + pu, p[1] + pz), (q[0] + pu, q[1] + pz), (q[0] - pu, q[1] - pz),
                         (p[0] - pu, p[1] - pz)], d0, d1, W)


def _tyre(g, group, W, cu, cz, r, t=0.045, n=28):
    for i in range(n):
        a0, a1 = 2 * math.pi * i / n, 2 * math.pi * (i + 1) / n
        pts = [(cu + (r + t) * math.cos(a0), cz + (r + t) * math.sin(a0)),
               (cu + (r + t) * math.cos(a1), cz + (r + t) * math.sin(a1)),
               (cu + r * math.cos(a1), cz + r * math.sin(a1)), (cu + r * math.cos(a0), cz + r * math.sin(a0))]
        g.prism(group, "tire", pts, -0.025, 0.025, W)


def _string(g, a, b, sag, step=0.9):
    """A string of bulbs from a to b (x, y, z), sagging by `sag` in the middle."""
    length = math.dist(a[:2], b[:2])
    for k in range(int(length / 0.12) + 1):           # the wire, as a chain of small cubes
        t = k * 0.12 / length
        x, y = a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t
        z = a[2] + (b[2] - a[2]) * t - 4 * sag * t * (1 - t)
        g.box("lights", "wire", x - 0.018, x + 0.018, y - 0.018, y + 0.018, z - 0.018, z + 0.018)
    for k in range(1, int(length / step)):
        t = k * step / length
        x, y = a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t
        z = a[2] + (b[2] - a[2]) * t - 4 * sag * t * (1 - t)
        g.box("lights", "bulb", x - 0.07, x + 0.07, y - 0.07, y + 0.07, z - 0.2, z - 0.06)


def build(sc, seed=0):
    info = P.build(sc, seed)
    g = P.Geo()

    # the fruit stall, in front of the hall's arcade, its customers' side facing south
    S = "stall"
    x0, x1, y0, y1 = -10.4, -7.6, 11.0, 12.1
    g.box(S, "wood", x0, x1, y0, y1, 0.82, 0.9)
    for (x, y) in ((x0 + 0.1, y0 + 0.1), (x1 - 0.1, y0 + 0.1), (x0 + 0.1, y1 - 0.1), (x1 - 0.1, y1 - 0.1)):
        g.box(S, "wood", x - 0.04, x + 0.04, y - 0.04, y + 0.04, 0.0, 0.82)
        g.cyl(S, "iron", x, y, 0.9, 2.35, 0.035, n=10)
    for i, fruit in enumerate(("oranges", "lemons", "apples", "oranges", "lemons")):
        cx = x0 + 0.35 + i * 0.52
        g.box(S, "wood", cx - 0.23, cx + 0.23, y0 + 0.12, y0 + 0.62, 0.9, 1.12)
        g.box(S, fruit, cx - 0.2, cx + 0.2, y0 + 0.15, y0 + 0.59, 1.12, 1.2)
    ya, k = x0 - 0.25, 0
    while ya < x1 + 0.25 - 1e-6:                     # the canopy, 0.4 m stripes, sloping to the front
        xb = min(ya + 0.4, x1 + 0.25)
        m = "canopy_yellow" if k % 2 == 0 else "awning_white"
        g.slab(S, m, [(ya, y1 + 0.25, 2.45), (xb, y1 + 0.25, 2.45), (xb, y0 - 0.45, 2.15), (ya, y0 - 0.45, 2.15)], 0.03)
        g.box(S, m, ya, xb, y0 - 0.48, y0 - 0.42, 1.95, 2.17)
        ya, k = xb, k + 1

    # a red bicycle leaning on the fountain's west side, front wheel to the north, a basket of flowers on it
    B = "bicycle"
    W = P._world("W", -3.72)
    rear, front = (-0.55, 0.34), (0.55, 0.34)
    _tyre(g, B, W, rear[0], rear[1], 0.31)
    _tyre(g, B, W, front[0], front[1], 0.31)
    bb, seat, head = (0.0, 0.3), (-0.13, 0.8), (0.42, 0.8)
    for p, q in ((bb, seat), (seat, head), (bb, (0.42, 0.72)), (bb, rear), (seat, rear), (head, front)):
        _quad(g, B, "bike_red", W, p, q, 0.045, -0.02, 0.02)
    _quad(g, B, "iron", W, (0.42, 0.8), (0.44, 0.98), 0.035, -0.02, 0.02)
    P.fbox(g, B, "iron", "W", -3.72, 0.38, 0.5, 0.96, 1.0, -0.26, 0.26)            # handlebar
    P.fbox(g, B, "tire", "W", -3.72, -0.24, -0.02, 0.82, 0.88, -0.07, 0.07)        # saddle
    P.fbox(g, B, "wicker", "W", -3.72, 0.5, 0.86, 0.8, 1.04, -0.17, 0.17)          # the basket
    P.fbox(g, B, "bloom", "W", -3.72, 0.54, 0.82, 1.04, 1.13, -0.14, 0.14)          # flowers in it

    # terracotta pots of flowers along the cafe, and either side of the yellow house's door
    for (x, y) in ((15.45, -8.6), (15.45, -3.0), (15.45, 4.8), (15.45, 9.6), (9.2, 15.55), (11.4, 15.55)):
        g.cyl("pots", "terracotta", x, y, 0.0, 0.55, 0.26, 0.34, n=16)
        g.cyl("pots", "foliage", x, y, 0.55, 0.95, 0.36, 0.22, n=16)
        g.cyl("pots", "bloom", x, y, 0.95, 1.02, 0.22, 0.12, n=12)

    # two strings of lights across the square
    _string(g, (-4.2, 16.1, 7.2), (16.0, 10.8, 7.0), 1.2)
    _string(g, (-16.0, 6.0, 7.0), (16.0, 3.0, 7.0), 1.6)

    g.flush(sc)
    info["set"] = "plaza_market"
    info["groups"].update({k: list(v) for k, v in EXTRA_GROUPS.items()})
    info["landmarks"] = list(info["landmarks"]) + ["stall", "bicycle", "pots"]
    return info
