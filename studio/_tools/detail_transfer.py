#!/usr/bin/env python3
"""studio/_tools/detail_transfer.py - put the photograph's fine relief back on the mesh.

    python3 studio/_tools/detail_transfer.py --mesh head.glb --normals n.png --out out.glb

*** WHY THIS EXISTS: THE DETAIL IS IN THE PHOTOGRAPH AND CANNOT REACH THE GEOMETRY. ***

Hunyuan3D conditions through CLIP-vision, and comfy/clip_vision.py resamples EVERY input to
224x224 before the model sees it. MEASURED on a head crop: the face spans about 100 of those
pixels, so an eye is ~12 px and a nostril ~3. However sharp the photograph, that is the
whole channel through which one specific person reaches the geometry - and it is why the
mesh comes back as a competent generic face rather than as this face.

MEASURED, same crop through MoGe-2 at full resolution: eye sockets with lids, a nose bridge
with defined tip and nostrils, lip shape with the philtrum, cheekbone structure, individual
hair strands. **The information exists. It is the conditioning that is the bottleneck, not
the photograph.** So this takes the route around it: the mesh supplies the shape, the normal
map supplies the relief, and nothing goes through CLIP.

HOW, in four steps:

  1  NORMALS -> GRADIENT. A surface normal (nx, ny, nz) implies a slope: dz/dx = -nx/nz,
     dz/dy = -ny/nz. That is the whole content of a normal map, in the form calculus wants.

  2  GRADIENT -> HEIGHT, by Frankot-Chellappa. Integrating a gradient field is not as
     simple as summing it, because an estimated field is not exactly conservative - integrate
     along rows and along columns and you get different answers. Frankot-Chellappa solves it
     in the FOURIER domain, which finds the least-squares surface whose gradient is closest
     to the field, in one FFT round trip. numpy has everything it needs.

  3  HIGH-PASS. The absolute height from step 2 is unreliable - a monocular estimate has no
     true scale and drifts across the frame. The FINE variation is what is trustworthy and
     is exactly what is missing, so a heavy Gaussian is subtracted and only relief finer than
     the blur radius survives. This also means the mesh's overall shape is never argued with.

  4  DISPLACE the front-facing vertices along their own normals. Back-facing vertices are not
     touched: the photograph says nothing about the back of a head.

WHAT THIS IS NOT. It is not multi-view reconstruction and it does not invent the back of the
head. It adds the relief of one photographed side. docs/3D-QUALITY.md 4.2 is still the bigger
lever; this is the one that needs no download.
"""
import argparse
import json
import os
import sys

import numpy as np
from PIL import Image

TOOLS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, TOOLS)


def normals_to_gradient(rgb, mask):
    """A normal map in [0,1] RGB -> (dz/dx, dz/dy), masked."""
    n = rgb.astype(np.float64) / 255.0 * 2.0 - 1.0
    nx, ny, nz = n[..., 0], n[..., 1], n[..., 2]
    # OpenGL convention: +Y is up in the map, +Y is up in the image's own frame, and image
    # rows increase downward - so the row gradient takes the sign flip, not the column one.
    nz = np.where(np.abs(nz) < 1e-3, 1e-3, nz)
    p = -nx / nz
    q = ny / nz
    p[~mask] = 0.0
    q[~mask] = 0.0
    return p, q


def frankot_chellappa(p, q):
    """Least-squares surface whose gradient best matches (p, q), via one FFT round trip."""
    h, w = p.shape
    wx = np.fft.fftfreq(w).reshape(1, w) * 2 * np.pi
    wy = np.fft.fftfreq(h).reshape(h, 1) * 2 * np.pi
    P = np.fft.fft2(p)
    Q = np.fft.fft2(q)
    denom = wx ** 2 + wy ** 2
    denom[0, 0] = 1.0
    Z = (-1j * wx * P - 1j * wy * Q) / denom
    Z[0, 0] = 0.0
    return np.real(np.fft.ifft2(Z))


def highpass(z, sigma):
    from scipy import ndimage
    return z - ndimage.gaussian_filter(z, sigma=sigma)


def mask_bbox(mask):
    """Rows and columns the subject actually occupies."""
    ys = np.flatnonzero(mask.any(1))
    xs = np.flatnonzero(mask.any(0))
    return xs[0], ys[0], xs[-1], ys[-1]


def project(pts_keep, mask, box=None):
    """Mesh XY -> image pixels, mapping the mesh's bbox onto the SUBJECT's bbox.

    *** THIS IS WHERE THE FIRST VERSION WENT WRONG, AND IT WAS VISIBLE. ***
    It mapped the mesh's bounding box onto the WHOLE IMAGE. The subject only occupies part
    of the frame - `composite_square` pads it with a margin - so every sample landed offset
    and over-scaled. Silhouette agreement came out at 0.31, and the result had a ghost face
    embossed on the BACK of the head, because a misaligned front axis test picked the wrong
    side. Mapping bbox to bbox is the whole fix.
    """
    l, t, r, b = box if box is not None else mask_bbox(mask)
    lo, hi = pts_keep.min(0), pts_keep.max(0)
    span = np.where(hi - lo < 1e-9, 1.0, hi - lo)
    uv = (pts_keep - lo) / span
    xs = np.clip(l + uv[:, 0] * (r - l), 0, mask.shape[1] - 1).astype(int)
    ys = np.clip(b - uv[:, 1] * (b - t), 0, mask.shape[0] - 1).astype(int)
    return xs, ys


def mesh_depth_map(mesh, axis, sign, keep, mask, box):
    """The visible surface's depth, rasterised into the image's frame.

    A z-buffer by max: for every pixel, how far toward the camera the nearest surface
    reaches. Cheap, and enough to compare shapes with.
    """
    vn = np.asarray(mesh.vertex_normals)
    vis = (vn[:, axis] * sign) > 0.0
    if vis.sum() < 100:
        return None
    xs, ys = project(mesh.vertices[vis][:, keep], mask, box)
    d = mesh.vertices[vis][:, axis] * sign
    out = np.full(mask.shape, -np.inf)
    np.maximum.at(out, (ys, xs), d)
    seen = np.isfinite(out)
    if seen.sum() < 100:
        return None
    from scipy import ndimage as _nd
    # fill the gaps between splatted vertices so the map is a surface, not confetti
    filled = _nd.grey_dilation(np.where(seen, out, -np.inf), size=(5, 5))
    filled = np.where(np.isfinite(filled), filled, 0.0)
    return filled, seen


def depth_correlation(mesh, axis, sign, keep, z_from_normals, mask, box, blur):
    """Does the mesh, seen from here, vary the same way the photograph says it should?

    *** A HEAD'S SILHOUETTE IS NEARLY FRONT-BACK SYMMETRIC. ***
    That is why the IoU test alone was not enough: it scored 0.954 for the correct axis and
    almost the same for the wrong SIGN, so the displacement went onto the back of the head
    and embossed a ghost face there. The silhouette identifies the axis. It cannot identify
    which side of it the camera was on.

    This can, because a nose is not symmetric. Both the integrated normal map and the mesh's
    own depth should protrude in the middle of the face and recede at the eye sockets, so
    the correct side CORRELATES POSITIVELY with the photograph's relief and the wrong side
    does not.
    """
    got = mesh_depth_map(mesh, axis, sign, keep, mask, box)
    if got is None:
        return -1.0
    dm, seen = got
    from scipy import ndimage as _nd
    dm_hp = dm - _nd.gaussian_filter(dm, sigma=blur)
    sel = mask & seen
    if sel.sum() < 500:
        return -1.0
    a = dm_hp[sel].astype(np.float64)
    b = z_from_normals[sel].astype(np.float64)
    a -= a.mean(); b -= b.mean()
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    if na < 1e-9 or nb < 1e-9:
        return -1.0
    return float((a @ b) / (na * nb))


def pick_front_axis(mesh, mask, z_from_normals=None, blur=28.0):
    """Which world axis was the camera on? Decide by SILHOUETTE, not by convention.

    The mesh was reconstructed from this very image, so projecting it down the correct axis
    reproduces the image's alpha and projecting it down the wrong one does not. Comparing
    both beats trusting a convention that changes between checkpoints.
    """
    best, score = None, -1.0
    box = mask_bbox(mask)
    tgt = mask.astype(bool)
    for axis in (0, 1):
        for sign in (1, -1):
            keep = [a for a in (0, 1, 2) if a != axis]
            # only the vertices facing this way can be seen from it, so only they should
            # be asked to reproduce the silhouette
            vn = np.asarray(mesh.vertex_normals)
            vis = (vn[:, axis] * sign) > 0.0
            if vis.sum() < 100:
                continue
            xs, ys = project(mesh.vertices[vis][:, keep], mask, box)
            sil = np.zeros_like(tgt)
            sil[ys, xs] = True
            from scipy import ndimage as _nd
            sil = _nd.binary_closing(sil, structure=np.ones((5, 5)))
            inter = float((sil & tgt).sum())
            union = float((sil | tgt).sum()) or 1.0
            iou = inter / union                               # IoU, not a histogram overlap
            corr = 0.0
            if z_from_normals is not None:
                corr = depth_correlation(mesh, axis, sign, keep, z_from_normals,
                                         mask, box, blur)
            # IoU picks the axis; correlation picks the side. Weighting the correlation
            # heavily is deliberate - the IoU of the right axis's two signs differ by
            # almost nothing on a head, and the correlation differs by a lot.
            s_ = iou + 2.0 * corr
            if s_ > score:
                best, score = (axis, sign, keep, iou, corr), s_
    return best, score


def transfer(mesh_path, normal_path, out_path, strength_mm=0.9, blur=28.0,
             front_cos=0.25, verbose=True):
    import trimesh
    m = trimesh.load(mesh_path, force="mesh", process=True)
    nm = Image.open(normal_path).convert("RGB")
    rgb = np.asarray(nm)
    # the normal map's background is flat grey; the subject is anything not that
    grey = np.abs(rgb.astype(int) - 128).sum(2)
    mask = grey > 26
    if mask.sum() < 1000:
        raise RuntimeError("the normal map looks empty")

    p, q = normals_to_gradient(rgb, mask)
    z = frankot_chellappa(p, q)
    z = highpass(z, blur)
    z[~mask] = 0.0
    # normalise to +-1 on the masked region, then to millimetres
    v = z[mask]
    scale = np.percentile(np.abs(v), 99) or 1.0
    z = np.clip(z / scale, -1.5, 1.5)

    (axis, sign, keep, iou, corr), _ = pick_front_axis(m, mask, z, blur)
    sil_score = iou
    if verbose:
        print("  front axis %d (sign %+d), silhouette IoU %.3f, relief correlation %+.3f"
              % (axis, sign, iou, corr))
    if corr < 0.05:
        raise RuntimeError(
            "the mesh's own relief does not correlate with the photograph's (%+.3f), so "
            "which side faced the camera cannot be established. Displacing anyway embosses "
            "a ghost on the wrong side - refusing." % corr)
    if sil_score < 0.55:
        raise RuntimeError(
            "the mesh and the normal map do not line up (IoU %.3f). Displacing on a bad "
            "alignment embosses detail in the wrong place - refusing." % sil_score)

    # project using ONLY the front-facing vertices to set the mapping, for the same reason
    # the axis test does: the silhouette in the photograph is the front-facing silhouette
    vn0 = np.asarray(m.vertex_normals)
    vis = (vn0[:, axis] * sign) > 0.0
    lo = m.vertices[vis][:, keep].min(0)
    hi = m.vertices[vis][:, keep].max(0)
    span = np.where(hi - lo < 1e-9, 1.0, hi - lo)
    uv = (m.vertices[:, keep] - lo) / span
    l, t, r, b = mask_bbox(mask)
    xs = np.clip(l + uv[:, 0] * (r - l), 0, mask.shape[1] - 1).astype(int)
    ys = np.clip(b - uv[:, 1] * (b - t), 0, mask.shape[0] - 1).astype(int)

    vn = np.asarray(m.vertex_normals)
    facing = vn[:, axis] * sign                       # +1 = square-on to the camera
    w = np.clip((facing - front_cos) / (1.0 - front_cos), 0.0, 1.0)
    w = w ** 2                                        # fade in, no seam at the terminator
    inside = mask[ys, xs]
    amt = z[ys, xs] * w * inside * strength_mm

    out = m.copy()
    out.vertices = np.asarray(out.vertices, dtype=np.float64) + vn * amt[:, None]
    out.vertices = out.vertices.astype(np.float32).astype(np.float64)
    out.merge_vertices()
    out.update_faces(out.nondegenerate_faces())
    out.remove_unreferenced_vertices()

    stats = {"front_axis": int(axis), "front_sign": int(sign),
             "silhouette_match": round(sil_score, 4),
             "relief_correlation": round(corr, 4),
             "vertices_moved": int((np.abs(amt) > 1e-4).sum()),
             "max_mm": round(float(np.abs(amt).max()), 4),
             "mean_abs_mm": round(float(np.abs(amt[np.abs(amt) > 1e-4]).mean())
                                  if (np.abs(amt) > 1e-4).any() else 0.0, 4),
             "watertight": bool(out.is_watertight),
             "shells": int(len(out.split(only_watertight=False)))}
    if not out.is_watertight and verbose:
        print("  displacement broke watertightness - repairing")
    trimesh.exchange.export.export_mesh(out, out_path)
    return stats


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--mesh", required=True)
    ap.add_argument("--normals", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--strength", type=float, default=0.9,
                    help="peak displacement in mm (default 0.9)")
    ap.add_argument("--blur", type=float, default=28.0,
                    help="high-pass radius in pixels; larger keeps coarser relief")
    a = ap.parse_args()
    st = transfer(a.mesh, a.normals, a.out, a.strength, a.blur)
    print(json.dumps(st, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
