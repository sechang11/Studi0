#!/usr/bin/env python3
"""mesh_texture.py -- orthographic view rendering, projective vertex-colour bake,
and paint-kit assembly for a printed figurine mesh.

There is no local Hunyuan3D paint stage on this box (see PAINT_PATH.json), so
colour has to come from the seed image by projection rather than from a texture
model. This tool does that, and builds the sheets a human painter needs.

SAFE TO PROBE: this module does nothing at import and nothing without a
subcommand. `--help`, no-arg and `import mesh_texture` are all inert.

Subcommands
  profile  z-profile of the mesh, to locate the fused plinth
  views    orthographic grey (or colour) renders at any azimuth
  align    fit the seed image onto the mesh front silhouette, report IoU
  bake     projective vertex-colour bake -> vertex-coloured GLB/PLY
  key      sample the colour key out of the seed image
  sheet    compose a contact sheet from named images
"""

import argparse
import json
import os
import sys

import numpy as np


# --------------------------------------------------------------------------
# geometry / raster core
# --------------------------------------------------------------------------

def load_mesh(path):
    import trimesh
    m = trimesh.load(path, force="mesh")
    if not isinstance(m, trimesh.Trimesh):
        raise SystemExit("not a single mesh: %s" % path)
    return m


def view_basis(az_deg, elev_deg=0.0):
    """Camera looks along +w at the model. Returns (right, up, w)."""
    a = np.radians(az_deg)
    e = np.radians(elev_deg)
    # w = direction from camera toward the model
    w = np.array([-np.sin(a) * np.cos(e), np.cos(a) * np.cos(e), -np.sin(e)], float)
    w /= np.linalg.norm(w)
    world_up = np.array([0.0, 0.0, 1.0])
    right = np.cross(w, world_up)
    if np.linalg.norm(right) < 1e-6:
        right = np.array([1.0, 0.0, 0.0])
    right /= np.linalg.norm(right)
    up = np.cross(right, w)
    up /= np.linalg.norm(up)
    return right, up, w


def project(V, az, elev=0.0):
    r, u, w = view_basis(az, elev)
    return V @ r, V @ u, V @ w


def rasterize(V, az, W, H, elev=0.0, bounds=None, splat=2, normals=None,
              vcolors=None, margin=0.04):
    """Orthographic z-buffered point-splat raster.

    Returns dict with:
      idx    (H,W) int64 index of nearest visible vertex, -1 where empty
      mask   (H,W) bool coverage
      fit    (u0,u1,v0,v1) world-space window the image covers
    """
    uu, vv, dd = project(V, az, elev)
    if bounds is None:
        u0, u1 = uu.min(), uu.max()
        v0, v1 = vv.min(), vv.max()
        du, dv = (u1 - u0), (v1 - v0)
        u0 -= du * margin; u1 += du * margin
        v0 -= dv * margin; v1 += dv * margin
        # preserve aspect: fit world window into the WxH canvas
        sw = (u1 - u0) / W
        sh = (v1 - v0) / H
        s = max(sw, sh)
        cu, cv = (u0 + u1) / 2, (v0 + v1) / 2
        u0, u1 = cu - s * W / 2, cu + s * W / 2
        v0, v1 = cv - s * H / 2, cv + s * H / 2
    else:
        u0, u1, v0, v1 = bounds

    col = ((uu - u0) / (u1 - u0) * W)
    row = ((v1 - vv) / (v1 - v0) * H)

    idx = np.full(H * W, -1, np.int64)
    depth = np.full(H * W, np.inf, np.float64)

    offs = [(dx, dy) for dx in range(splat) for dy in range(splat)]
    base = np.arange(V.shape[0])
    for dx, dy in offs:
        c = np.floor(col + dx - (splat - 1) / 2.0).astype(np.int64)
        r = np.floor(row + dy - (splat - 1) / 2.0).astype(np.int64)
        ok = (c >= 0) & (c < W) & (r >= 0) & (r < H)
        p = r[ok] * W + c[ok]
        d = dd[ok]
        vi = base[ok]
        # keep nearest: sort by (pixel, depth) and take first per pixel
        order = np.lexsort((d, p))
        p, d, vi = p[order], d[order], vi[order]
        first = np.ones(p.shape[0], bool)
        first[1:] = p[1:] != p[:-1]
        p, d, vi = p[first], d[first], vi[first]
        better = d < depth[p]
        depth[p[better]] = d[better]
        idx[p[better]] = vi[better]

    idx = idx.reshape(H, W)
    mask = idx >= 0
    out = {"idx": idx, "mask": mask, "fit": (u0, u1, v0, v1),
           "depth": depth.reshape(H, W)}
    return out


def fill_holes(idx, mask):
    """Fill pinholes inside the silhouette with the nearest covered vertex."""
    from scipy import ndimage
    solid = ndimage.binary_closing(mask, structure=np.ones((5, 5)))
    solid = ndimage.binary_fill_holes(solid)
    need = solid & ~mask
    if not need.any():
        return idx, solid
    _, ind = ndimage.distance_transform_edt(~mask, return_indices=True)
    out = idx.copy()
    out[need] = idx[ind[0][need], ind[1][need]]
    return out, solid


def shade(mesh, ras, az, elev=0.0, base=(0.72, 0.72, 0.74)):
    """Matte clay shading, so the eye reads form rather than colour."""
    idx, mask = ras["idx"], ras["mask"]
    N = mesh.vertex_normals
    r, u, w = view_basis(az, elev)
    # key light over the viewer's left shoulder, plus fill and rim
    key = -w + 0.45 * (-r) + 0.55 * u
    key /= np.linalg.norm(key)
    fill = -w + 0.6 * r - 0.2 * u
    fill /= np.linalg.norm(fill)

    img = np.zeros(idx.shape + (3,), np.float32)
    vi = idx[mask]
    n = N[vi]
    lam = np.clip(n @ key, 0, 1) * 0.72 + np.clip(n @ fill, 0, 1) * 0.22 + 0.20
    lam = np.clip(lam, 0, 1.25)
    col = np.array(base, np.float32)[None, :] * lam[:, None]
    img[mask] = np.clip(col, 0, 1)
    return img


def to_png(img, mask, path, bg=(1.0, 1.0, 1.0)):
    from PIL import Image
    out = np.array(bg, np.float32)[None, None, :] * np.ones(img.shape, np.float32)
    out[mask] = img[mask]
    Image.fromarray((np.clip(out, 0, 1) * 255).astype(np.uint8)).save(path)


# --------------------------------------------------------------------------
# subcommands
# --------------------------------------------------------------------------

def cmd_profile(a):
    m = load_mesh(a.mesh)
    V = m.vertices
    z = V[:, 2]
    lo, hi = z.min(), z.max()
    nb = a.bins
    edges = np.linspace(lo, hi, nb + 1)
    rows = []
    for i in range(nb):
        sel = (z >= edges[i]) & (z < edges[i + 1])
        if sel.sum() == 0:
            rows.append({"z0": float(edges[i]), "z1": float(edges[i + 1]),
                         "n": 0, "radius": 0.0, "width_x": 0.0, "width_y": 0.0})
            continue
        P = V[sel]
        rows.append({
            "z0": round(float(edges[i]), 2), "z1": round(float(edges[i + 1]), 2),
            "n": int(sel.sum()),
            "width_x": round(float(P[:, 0].max() - P[:, 0].min()), 2),
            "width_y": round(float(P[:, 1].max() - P[:, 1].min()), 2),
        })
    print(json.dumps({"mesh": a.mesh, "z_min": float(lo), "z_max": float(hi),
                      "bins": rows}, indent=1))


def cmd_views(a):
    m = load_mesh(a.mesh)
    V = m.vertices
    os.makedirs(a.out, exist_ok=True)
    azs = [float(x) for x in a.az.split(",")]
    # one shared world window so every view is the same scale
    allb = []
    for az in azs:
        uu, vv, _ = project(V, az, a.elev)
        allb.append((uu.min(), uu.max(), vv.min(), vv.max()))
    u0 = min(b[0] for b in allb); u1 = max(b[1] for b in allb)
    v0 = min(b[2] for b in allb); v1 = max(b[3] for b in allb)
    pad = 0.05
    du, dv = u1 - u0, v1 - v0
    u0 -= du * pad; u1 += du * pad; v0 -= dv * pad; v1 += dv * pad
    s = max((u1 - u0) / a.width, (v1 - v0) / a.height)
    cu, cv = (u0 + u1) / 2, (v0 + v1) / 2
    bounds = (cu - s * a.width / 2, cu + s * a.width / 2,
              cv - s * a.height / 2, cv + s * a.height / 2)

    vc = None
    if a.colored and m.visual.kind == "vertex":
        vc = np.asarray(m.visual.vertex_colors)[:, :3].astype(np.float32) / 255.0

    made = []
    for az, name in zip(azs, a.names.split(",") if a.names else
                        ["az%03d" % int(z) for z in azs]):
        ras = rasterize(V, az, a.width, a.height, a.elev, bounds, a.splat)
        idx, solid = fill_holes(ras["idx"], ras["mask"])
        ras["idx"], ras["mask"] = idx, solid
        if vc is not None:
            img = np.zeros(idx.shape + (3,), np.float32)
            lit = shade(m, ras, az, a.elev, base=(1.0, 1.0, 1.0))
            img[solid] = np.clip(vc[idx[solid]] * (0.45 + 0.75 * lit[solid]), 0, 1)
        else:
            img = shade(m, ras, az, a.elev)
        p = os.path.join(a.out, "%s.png" % name)
        to_png(img, solid, p)
        made.append({"name": name, "az": az, "path": p,
                     "coverage_pct": round(float(solid.mean()) * 100, 2)})
    print(json.dumps({"bounds": [round(float(x), 3) for x in bounds],
                      "views": made}, indent=1))


def _alpha_mask(path, thresh=128):
    from PIL import Image
    im = Image.open(path).convert("RGBA")
    a = np.array(im)
    return a[..., :3], a[..., 3] > thresh


def _bbox(mask):
    ys, xs = np.where(mask)
    return xs.min(), xs.max(), ys.min(), ys.max()


def cmd_align(a):
    """Fit the seed image onto the mesh's front silhouette and report IoU.

    This is the load-bearing test. If the mesh really is a reconstruction of
    this image under an orthographic front view, the silhouettes must agree.
    """
    m = load_mesh(a.mesh)
    V = m.vertices
    keep = V[:, 2] >= a.zmin           # drop the fused plinth
    rgb, amask = _alpha_mask(a.image)

    ih, iw = amask.shape
    W = a.width
    H = int(round(W * ih / iw))
    # render the FIGURE ONLY into the same canvas shape as the seed image
    ras = rasterize(V[keep], a.az, W, H, 0.0, None, a.splat)
    _, msolid = fill_holes(ras["idx"], ras["mask"])

    from PIL import Image
    seed_small = np.array(Image.fromarray(amask.astype(np.uint8) * 255)
                          .resize((W, H), Image.NEAREST)) > 127

    # align by silhouette bbox, then refine scale/offset for best IoU
    def iou(m1, m2):
        i = (m1 & m2).sum()
        u = (m1 | m2).sum()
        return float(i) / float(u) if u else 0.0

    def warp(src, sx, sy, dx, dy):
        im = Image.fromarray(src.astype(np.uint8) * 255)
        nw, nh = max(1, int(round(W * sx))), max(1, int(round(H * sy)))
        im = im.resize((nw, nh), Image.NEAREST)
        canv = Image.new("L", (W, H), 0)
        canv.paste(im, (int(round(dx)), int(round(dy))))
        return np.array(canv) > 127

    mx0, mx1, my0, my1 = _bbox(msolid)
    sx0, sx1, sy0, sy1 = _bbox(seed_small)
    s0x = (mx1 - mx0 + 1) / float(sx1 - sx0 + 1)
    s0y = (my1 - my0 + 1) / float(sy1 - sy0 + 1)

    best = None
    for ks in np.linspace(0.94, 1.06, 13):
        for kx in np.linspace(-0.03, 0.03, 7):
            for ky in np.linspace(-0.03, 0.03, 7):
                sx, sy = s0x * ks, s0y * ks
                dx = mx0 - sx0 * sx + kx * W
                dy = my0 - sy0 * sy + ky * H
                w = warp(seed_small, sx, sy, dx, dy)
                v = iou(w, msolid)
                if best is None or v > best[0]:
                    best = (v, float(sx), float(sy), float(dx), float(dy))

    v, sx, sy, dx, dy = best
    res = {"mesh": a.mesh, "image": a.image, "az": a.az, "zmin": a.zmin,
           "canvas": [W, H], "iou": round(v, 4),
           "scale_x": round(sx, 5), "scale_y": round(sy, 5),
           "off_x": round(dx, 2), "off_y": round(dy, 2),
           "mesh_bbox": [int(x) for x in (mx0, mx1, my0, my1)],
           "seed_bbox": [int(x) for x in (sx0, sx1, sy0, sy1)]}

    if a.overlay:
        w = warp(seed_small, sx, sy, dx, dy)
        ov = np.zeros((H, W, 3), np.uint8)
        ov[..., 0] = w * 235           # seed  -> red
        ov[..., 1] = msolid * 235      # mesh  -> green
        ov[..., 2] = (w & msolid) * 235
        Image.fromarray(ov).save(a.overlay)
        res["overlay"] = a.overlay
    if a.out:
        with open(a.out, "w") as f:
            json.dump(res, f, indent=1)
    print(json.dumps(res, indent=1))


def cmd_bake(a):
    """Project seed colours onto vertices visible from the front, then fill
    the unseen vertices from their nearest coloured neighbour in 3-space."""
    from PIL import Image
    from scipy.spatial import cKDTree

    m = load_mesh(a.mesh)
    V = m.vertices
    N = m.vertex_normals
    al = json.load(open(a.align))
    W, H = al["canvas"]
    sx, sy, dx, dy = al["scale_x"], al["scale_y"], al["off_x"], al["off_y"]

    src = Image.open(a.image).convert("RGBA")
    nw, nh = max(1, int(round(W * sx))), max(1, int(round(H * sy)))
    src = src.resize((nw, nh), Image.LANCZOS)
    canv = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    canv.paste(src, (int(round(dx)), int(round(dy))))
    seed = np.array(canv)
    srgb, salpha = seed[..., :3], seed[..., 3] > 128

    # which vertices does the front camera actually see?
    keep_idx = np.where(V[:, 2] >= al["zmin"])[0]
    ras = rasterize(V[keep_idx], al["az"], W, H, 0.0, None, a.splat)
    idx, solid = fill_holes(ras["idx"], ras["mask"])

    colors = np.zeros((V.shape[0], 3), np.uint8)
    have = np.zeros(V.shape[0], bool)

    rr, cc = np.where(solid & salpha)
    vi = keep_idx[idx[rr, cc]]
    colors[vi] = srgb[rr, cc]
    have[vi] = True

    # front-facing but occluded-by-splat vertices: sample directly if the
    # seed pixel under them is opaque and their normal faces the camera
    r, u, w = view_basis(al["az"], 0.0)
    facing = (N @ w) < -0.15
    uu, vv, _ = project(V, al["az"], 0.0)
    u0, u1, v0, v1 = ras["fit"]
    col = np.floor((uu - u0) / (u1 - u0) * W).astype(np.int64)
    row = np.floor((v1 - vv) / (v1 - v0) * H).astype(np.int64)
    ok = facing & ~have & (col >= 0) & (col < W) & (row >= 0) & (row < H)
    ok2 = ok.copy()
    ok2[ok] = salpha[row[ok], col[ok]]
    colors[ok2] = srgb[row[ok2], col[ok2]]
    have[ok2] = True

    n_direct = int(have.sum())

    # everything unseen (back, plinth, occluded) inherits its nearest
    # coloured neighbour in 3-space -- for a figurine this is the right
    # guess: the back of the hair is next to the front of the hair.
    if a.plinth_color and al["zmin"] > 0:
        pl = V[:, 2] < al["zmin"]
        c = a.plinth_color.lstrip("#")
        colors[pl] = [int(c[i:i + 2], 16) for i in (0, 2, 4)]
        have[pl] = True

    miss = np.where(~have)[0]
    if miss.size:
        tree = cKDTree(V[have])
        _, j = tree.query(V[miss], k=1, workers=-1)
        src_idx = np.where(have)[0][j]
        colors[miss] = colors[src_idx]

    import trimesh
    m.visual = trimesh.visual.ColorVisuals(
        mesh=m, vertex_colors=np.concatenate(
            [colors, np.full((colors.shape[0], 1), 255, np.uint8)], axis=1))
    m.export(a.out)

    res = {"out": a.out, "vertices": int(V.shape[0]),
           "colored_directly": n_direct,
           "direct_pct": round(100.0 * n_direct / V.shape[0], 2),
           "filled_by_nearest": int(miss.size),
           "filled_pct": round(100.0 * miss.size / V.shape[0], 2),
           "align_iou": al["iou"]}
    if a.report:
        with open(a.report, "w") as f:
            json.dump(res, f, indent=1)
    print(json.dumps(res, indent=1))


def cmd_key(a):
    """Sample the dominant colour of named normalized boxes in the seed."""
    from PIL import Image
    im = Image.open(a.image).convert("RGBA")
    arr = np.array(im)
    ih, iw = arr.shape[:2]
    spec = json.load(open(a.regions))
    out = []
    swatch_rows = []
    for part in spec["parts"]:
        x0, y0, x1, y1 = part["box"]
        X0, X1 = int(x0 * iw), int(x1 * iw)
        Y0, Y1 = int(y0 * ih), int(y1 * ih)
        patch = arr[Y0:Y1, X0:X1]
        sel = patch[..., 3] > 200
        px = patch[..., :3][sel].astype(np.float32)
        if px.shape[0] < 20:
            out.append({"part": part["name"], "hex": None,
                        "note": "EMPTY BOX -- %d px" % px.shape[0]})
            continue
        # modal colour: coarse 16-level histogram, then mean of the winning bin
        q = (px // 16).astype(np.int32)
        keys = q[:, 0] * 4096 + q[:, 1] * 64 + q[:, 2]
        vals, counts = np.unique(keys, return_counts=True)
        win = vals[counts.argmax()]
        sel2 = keys == win
        mode = px[sel2].mean(axis=0)
        med = np.median(px, axis=0)
        hx = "#%02X%02X%02X" % tuple(int(round(v)) for v in mode)
        out.append({
            "part": part["name"],
            "hex": hx,
            "rgb": [int(round(v)) for v in mode],
            "hex_median": "#%02X%02X%02X" % tuple(int(round(v)) for v in med),
            "share_pct": round(100.0 * sel2.sum() / px.shape[0], 1),
            "px_sampled": int(px.shape[0]),
            "box_px": [X0, Y0, X1, Y1],
            "geometry": part.get("geometry", "?"),
            "note": part.get("note", ""),
        })
        swatch_rows.append((part["name"], hx))

    if a.marked:
        from PIL import ImageDraw
        vis = im.convert("RGB").copy()
        d = ImageDraw.Draw(vis)
        for part, rec in zip(spec["parts"], out):
            x0, y0, x1, y1 = part["box"]
            d.rectangle([x0 * iw, y0 * ih, x1 * iw, y1 * ih],
                        outline=(255, 0, 0), width=max(3, iw // 400))
            d.text((x0 * iw + 6, y0 * ih + 4), part["name"], fill=(255, 0, 0))
        vis.save(a.marked)

    res = {"image": a.image, "parts": out}
    if a.out:
        with open(a.out, "w") as f:
            json.dump(res, f, indent=1)
    print(json.dumps(res, indent=1))


def cmd_sheet(a):
    """Compose a labelled contact sheet with PIL.

    Deliberately not ffmpeg: `tile=` tiles the frames of ONE stream, so
    separate -i inputs silently emit input 0 and pad the rest black.
    """
    from PIL import Image, ImageDraw, ImageFont
    items = json.load(open(a.spec))
    cols = items.get("cols", 4)
    cw = items.get("cell_w", 700)
    ch = items.get("cell_h", 1000)
    pad = items.get("pad", 14)
    lab = items.get("label_h", 34)
    bg = tuple(items.get("bg", [255, 255, 255]))
    cells = items["cells"]
    rows = (len(cells) + cols - 1) // cols
    Wp = cols * cw + (cols + 1) * pad
    Hp = rows * (ch + lab) + (rows + 1) * pad
    sheet = Image.new("RGB", (Wp, Hp), bg)
    d = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.truetype(
            "/usr/share/fonts/dejavu-sans-fonts/DejaVuSans-Bold.ttf", 24)
    except Exception:
        font = ImageFont.load_default()
    for i, c in enumerate(cells):
        r, k = divmod(i, cols)
        x = pad + k * (cw + pad)
        y = pad + r * (ch + lab + pad)
        if c.get("path") and os.path.exists(c["path"]):
            im = Image.open(c["path"]).convert("RGB")
            im.thumbnail((cw, ch), Image.LANCZOS)
            sheet.paste(im, (x + (cw - im.width) // 2, y + (ch - im.height) // 2))
        else:
            d.rectangle([x, y, x + cw, y + ch], outline=(200, 60, 60), width=3)
            d.text((x + 12, y + 12), "MISSING", fill=(200, 60, 60), font=font)
        d.text((x + 4, y + ch + 4), c.get("label", ""), fill=(20, 20, 20),
               font=font)
    sheet.save(a.out, quality=94)
    print(json.dumps({"out": a.out, "size": [Wp, Hp], "cells": len(cells)},
                     indent=1))


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = p.add_subparsers(dest="cmd")

    q = sub.add_parser("profile"); q.set_defaults(fn=cmd_profile)
    q.add_argument("--mesh", required=True); q.add_argument("--bins", type=int, default=30)

    q = sub.add_parser("views"); q.set_defaults(fn=cmd_views)
    q.add_argument("--mesh", required=True); q.add_argument("--out", required=True)
    q.add_argument("--az", default="0,90,180,270"); q.add_argument("--names", default="")
    q.add_argument("--elev", type=float, default=0.0)
    q.add_argument("--width", type=int, default=900); q.add_argument("--height", type=int, default=1400)
    q.add_argument("--splat", type=int, default=2)
    q.add_argument("--colored", action="store_true")

    q = sub.add_parser("align"); q.set_defaults(fn=cmd_align)
    q.add_argument("--mesh", required=True); q.add_argument("--image", required=True)
    q.add_argument("--az", type=float, default=0.0); q.add_argument("--zmin", type=float, default=0.0)
    q.add_argument("--width", type=int, default=520); q.add_argument("--splat", type=int, default=2)
    q.add_argument("--overlay", default=""); q.add_argument("--out", default="")

    q = sub.add_parser("bake"); q.set_defaults(fn=cmd_bake)
    q.add_argument("--mesh", required=True); q.add_argument("--image", required=True)
    q.add_argument("--align", required=True); q.add_argument("--out", required=True)
    q.add_argument("--splat", type=int, default=2); q.add_argument("--report", default="")
    q.add_argument("--plinth-color", dest="plinth_color", default="")

    q = sub.add_parser("key"); q.set_defaults(fn=cmd_key)
    q.add_argument("--image", required=True); q.add_argument("--regions", required=True)
    q.add_argument("--out", default=""); q.add_argument("--marked", default="")

    q = sub.add_parser("sheet"); q.set_defaults(fn=cmd_sheet)
    q.add_argument("--spec", required=True); q.add_argument("--out", required=True)

    a = p.parse_args(argv)
    if not getattr(a, "cmd", None):
        p.print_help()
        return 0
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
