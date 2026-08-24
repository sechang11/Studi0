#!/usr/bin/env python3
"""studio/_tools/assemble.py - a body, a spring and a head, stacked as they would print.

    python3 studio/_tools/assemble.py --body suit_male --head stand_in
    python3 studio/_tools/assemble.py --body suit_male --head stand_in --spring 22

WHY THIS IS NOT A PRINT FILE. The three parts print SEPARATELY - that is the whole point
of the socket - so this writes a preview, not a deliverable. What it is for is the one
question the library cannot otherwise answer: do these two parts, sized independently and
socketed independently, actually look like a bobblehead when you put them together?

The spring is drawn as a helix swept into a tube so the preview shows the real gap. It is
NOT modelled for printing and never should be: a printed spring in PLA is a spring once.

The stack is exact, and that is the check. The body's socket mouth is at its own top face;
the head's is at its own bottom face; the spring's free length is the only number between
them. If the two sockets disagree about their diameter this preview cannot hide it, because
both are drawn at the diameter their own record claims.
"""
import argparse
import json
import math
import os
import sys

TOOLS = os.path.dirname(os.path.abspath(__file__))
STUDIO = os.path.dirname(TOOLS)
ROOT = os.path.dirname(STUDIO)
LIB = os.path.join(STUDIO, "bobblehead")
sys.path.insert(0, TOOLS)


def _rec(kind, rid):
    p = os.path.join(LIB, "bodies" if kind == "body" else "heads", rid,
                     "body.json" if kind == "body" else "head.json")
    return json.load(open(p, encoding="utf-8")), os.path.dirname(p)


def spring_mesh(d_mm, free_mm, coils=6, wire=1.4, seg=28):
    """A helix swept as a tube. Cosmetic - see the docstring."""
    import numpy as np
    import trimesh
    r = d_mm / 2.0 - wire / 2.0
    n = coils * seg
    t = np.linspace(0.0, coils * 2 * math.pi, n)
    pts = np.stack([r * np.cos(t), r * np.sin(t),
                    np.linspace(0.0, free_mm, n)], axis=1)
    path = trimesh.load_path(np.stack([pts[:-1], pts[1:]], axis=1))
    segs = []
    for a, b in zip(pts[:-1], pts[1:]):
        v = b - a
        h = float(np.linalg.norm(v))
        if h <= 0:
            continue
        c = trimesh.creation.cylinder(radius=wire / 2.0, height=h, sections=8)
        c.apply_transform(trimesh.geometry.align_vectors([0, 0, 1], v / h))
        c.apply_translation((a + b) / 2.0)
        segs.append(c)
    del path
    return trimesh.util.concatenate(segs)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--body", required=True)
    ap.add_argument("--head", required=True)
    ap.add_argument("--spring", type=float, default=22.0,
                    help="spring free length in mm (default 22)")
    ap.add_argument("--out")
    a = ap.parse_args()

    import trimesh
    import terra_mesh

    brec, bdir = _rec("body", a.body)
    hrec, hdir = _rec("head", a.head)
    bn = brec["stages"]["neck"]
    hs = hrec["stages"]["socket"]

    body = trimesh.load(os.path.join(bdir, "body.glb"), force="mesh")
    head = trimesh.load(os.path.join(hdir, "head.glb"), force="mesh")

    b_top = float(body.bounds[1][2])
    cx, cy = bn["neck_centre"]
    # the head is centred on the body's socket, then lifted by the spring's free length
    hc = (head.bounds[0] + head.bounds[1]) / 2.0
    head.apply_translation([cx - hc[0], cy - hc[1],
                            b_top + a.spring - float(head.bounds[0][2])])
    sp = spring_mesh(bn["socket_d_mm"], a.spring)
    sp.apply_translation([cx, cy, b_top])

    out = a.out or os.path.join(LIB, "assembled", "%s__%s" % (a.body, a.head))
    os.makedirs(out, exist_ok=True)
    whole = trimesh.util.concatenate([body, sp, head])
    glb = os.path.join(out, "assembled.glb")
    trimesh.exchange.export.export_mesh(whole, glb)

    total = float(whole.bounds[1][2] - whole.bounds[0][2])
    terra_mesh.render_one(glb, "%s__%s" % (a.body, a.head), out,
                          size=460, frames=4, ss=2, up="z")
    rec = {"body": a.body, "head": a.head, "spring_free_mm": a.spring,
           "body_mm": brec["height_mm"], "head_mm": hrec["height_mm"],
           "total_mm": round(total, 1),
           "body_socket_mm": bn["socket_d_mm"], "head_socket_mm": hs["socket_d_mm"],
           "sockets_agree": abs(bn["socket_d_mm"] - hs["socket_d_mm"]) < 0.01,
           "preview_only": True}
    json.dump(rec, open(os.path.join(out, "assembled.json"), "w"), indent=1)
    print("  %s + %s" % (a.body, a.head))
    print("  body %.0f mm + spring %.0f mm + head %.0f mm = %.1f mm standing"
          % (brec["height_mm"], a.spring, hrec["height_mm"], total))
    print("  sockets: body %.2f mm, head %.2f mm -> %s"
          % (bn["socket_d_mm"], hs["socket_d_mm"],
             "AGREE" if rec["sockets_agree"] else "DISAGREE - the spring will not fit both"))
    print("  %s" % out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
