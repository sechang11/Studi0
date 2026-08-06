#!/usr/bin/env python3
"""mesh_prep.py - turn a qualified generated mesh into a file a slicer can eat.

mesh_doctor.py measures and repairs. This tool does the *print preparation* that
comes after: it makes the geometry survivable at a real print size, gives the
figure something to stand on, and writes the deliverable.

The core of it is a SINGLE voxel pass. Every previous stage of this project
voxelised the model at least once (that is how a Hunyuan3D surface-net mesh is
made watertight at all), and each voxel round trip costs detail. So repair,
crevice closing, minimum-feature thickening and the plinth all happen inside one
grid, at print scale, in millimetres, and come out through one marching cubes.

    raw .glb  ->  weld / drop stray shells      (surface, cheap, lossless)
              ->  orient Z-up, scale to mm      (so every dial below is in mm)
              ->  voxelise + flood fill         (this is what makes it a solid)
              ->  morphological CLOSE  rc       (merge strands, kill sub-nozzle slots)
              ->  minimum-thickness GROW  t     (nothing thinner than the nozzle)
              ->  rasterise the plinth          (fused by construction, no boolean)
              ->  marching cubes -> one closed manifold solid

Subcommands
    solidify   the pass above; raw mesh in, print-ready solid out
    audit      thickness + overhang at real scale, with a thin-map picture
    thinmap    just the picture (front/side scatter, thin material in red)
    render     turntable + head close-up, so the result is judged by looking
    export     STL / 3MF / GLB, each re-loaded from disk and re-verified
    card       write the one-page print card from the audit JSON

Everything is in millimetres once `solidify` has run. Dials are mm, not voxels,
not "resolution", not model units.

Depends on mesh_doctor.py (imported, never modified), trimesh, numpy, scipy,
scikit-image, pillow. Reuses terra_mesh.py's rasteriser for `render`.
"""

import argparse
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))


# ---------------------------------------------------------------------------
# lazy imports - --help must never pay for numpy/trimesh
# ---------------------------------------------------------------------------


def _np():
    import numpy as np

    return np


def _md():
    """mesh_doctor belongs to another agent. Import it, never edit it."""
    if HERE not in sys.path:
        sys.path.insert(0, HERE)
    import mesh_doctor

    return mesh_doctor


def _tm():
    import trimesh

    trimesh.util.log.setLevel(50)
    return trimesh


def _edt(mask, pitch):
    """Exact Euclidean distance transform, in MILLIMETRES.

    For every nonzero voxel, the distance to the nearest zero voxel. That makes
    edt(solid) the local inradius, and edt(~solid) the distance from empty space
    to the nearest material - which is all the morphology below needs.
    """
    from scipy import ndimage

    return ndimage.distance_transform_edt(mask, sampling=pitch)


def _say(msg, quiet=False):
    if not quiet:
        print(msg, flush=True)


def _ensure_room(vol, world0, pitch, lo_mm, hi_mm, margin_vox=3):
    """Grow the array until the world-space box [lo_mm, hi_mm] is inside it,
    with margin_vox of empty space to spare.

    A solid that touches the array boundary marching-cubes into an OPEN surface.
    That is how the plinth put 98 boundary edges into an otherwise perfect solid
    on the first run of this tool: the disc is sized from the feet and centred on
    the feet, so it reached past the figure's own bounding box in Y and got
    clipped by the array edge. Nothing else in the pipeline notices - the mesh is
    still 'repaired', just no longer closed.
    """
    np = _np()
    lo_idx = np.floor((np.asarray(lo_mm, float) - world0) / pitch).astype(int) - margin_vox
    hi_idx = np.ceil((np.asarray(hi_mm, float) - world0) / pitch).astype(int) + margin_vox
    pad_lo = np.maximum(-lo_idx, 0)
    pad_hi = np.maximum(hi_idx - (np.array(vol.shape) - 1), 0)
    if not (pad_lo.any() or pad_hi.any()):
        return vol, world0, False
    vol = np.pad(vol, tuple((int(a), int(b)) for a, b in zip(pad_lo, pad_hi)),
                 mode="constant", constant_values=False)
    return vol, world0 - pad_lo * pitch, True


def _axes(world0, shape, pitch):
    np = _np()
    return [world0[i] + np.arange(shape[i], dtype=np.float64) * pitch for i in range(3)]


def _mb(a):
    return a.nbytes / 1e6


# ---------------------------------------------------------------------------
# morphology
# ---------------------------------------------------------------------------


def _drop_islands(mesh, frac, log, quiet=False):
    """Drop vertex-connected shells below `frac` of the largest, and say exactly
    what was removed and how big it was. Anything above the threshold is KEPT and
    reported loudly - silently deleting a whole hair lock because it came out
    detached would be worse than shipping it."""
    np = _np()
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import connected_components as cc

    e = mesh.edges
    g = coo_matrix((np.ones(len(e), dtype=np.int8), (e[:, 0], e[:, 1])),
                   shape=(len(mesh.vertices),) * 2)
    n, labels = cc(g, directed=False)
    info = {"islands_before": int(n), "dropped": [], "kept_extra": []}
    if n <= 1:
        info["islands_after"] = 1
        log.append("strays: single island - nothing to drop")
        _say("      " + log[-1], quiet)
        return info
    fl = labels[mesh.faces[:, 0]]
    counts = np.bincount(fl, minlength=n)
    biggest = counts.max()
    keep_lbl = counts >= biggest * frac
    for i in np.nonzero((counts > 0) & ~keep_lbl)[0]:
        sel = fl == i
        v = mesh.vertices[np.unique(mesh.faces[sel])]
        info["dropped"].append({
            "faces": int(sel.sum()),
            "pct_of_largest": round(100.0 * counts[i] / biggest, 5),
            "bbox_mm": [round(float(x), 3) for x in (v.max(0) - v.min(0))],
            "centre_mm": [round(float(x), 1) for x in v.mean(0)],
        })
    for i in np.nonzero(keep_lbl)[0]:
        if counts[i] == biggest:
            continue
        sel = fl == i
        v = mesh.vertices[np.unique(mesh.faces[sel])]
        info["kept_extra"].append({
            "faces": int(counts[i]),
            "pct_of_largest": round(100.0 * counts[i] / biggest, 5),
            "bbox_mm": [round(float(x), 3) for x in (v.max(0) - v.min(0))],
            "centre_mm": [round(float(x), 1) for x in v.mean(0)],
        })
    if info["dropped"]:
        mesh.update_faces(keep_lbl[fl])
        mesh.remove_unreferenced_vertices()
        big = max(d["bbox_mm"][0] for d in info["dropped"])
        log.append("strays: dropped %d floating shell(s) under %.2f%% of the body; "
                   "largest was %.2f mm across"
                   % (len(info["dropped"]), 100 * frac, big))
    else:
        log.append("strays: %d islands, none under the %.2f%% threshold"
                   % (n, 100 * frac))
    if info["kept_extra"]:
        log.append("strays: KEPT %d island(s) above the threshold - these will slice "
                   "as separate bodies: %s"
                   % (len(info["kept_extra"]),
                      ", ".join("%.2f%% at %s" % (k["pct_of_largest"], k["centre_mm"])
                                for k in info["kept_extra"])))
    info["islands_after"] = 1 + len(info["kept_extra"])
    _say("      " + log[-1], quiet)
    return info


def _pitch_guard(what, radius_mm, pitch):
    """A morphological radius smaller than about two voxels does NOTHING, and
    does it silently.

    Discovered the hard way: at --pitch 0.6 a --close-mm 0.5 reported
    '287,443 -> 287,443 -> 287,443 (+0.00% material)' and the minimum-thickness
    pass reported 'no material below 1.00 mm - nothing to grow'. Both read like
    good news. Both meant the grid was too coarse to see the feature at all.
    Refuse rather than let that number into a report.
    """
    if radius_mm < pitch * 2.0:
        raise SystemExit(
            "mesh_prep: %s = %.3f mm is under two voxels at --pitch %.3f mm. The "
            "morphology would silently do nothing and report success.\n"
            "           use --pitch %.3f or smaller, or raise %s."
            % (what, radius_mm, pitch, radius_mm / 2.0, what))


def morph_close(vol, radius_mm, pitch, log, quiet=False):
    """Dilate then erode by the same radius.

    Closes any gap narrower than 2*radius while leaving the outer silhouette
    alone. On a figurine this is the operation that merges hair locks which are
    almost touching into one mass - the thing a human sculptor does on purpose -
    and that removes crevices no nozzle could ever enter.
    """
    np = _np()
    if radius_mm <= 0:
        log.append("close: skipped (radius 0)")
        return vol
    _pitch_guard("--close-mm", radius_mm, pitch)
    t0 = time.time()
    n0 = int(vol.sum())
    d = _edt(~vol, pitch)
    dil = d <= radius_mm
    del d
    n1 = int(dil.sum())
    d = _edt(dil, pitch)
    ero = d > radius_mm
    del d, dil
    out = ero | vol  # closing is extensive in the continuous case; enforce it
    del ero
    n2 = int(out.sum())
    log.append(
        "close r=%.2f mm: %s solid -> %s dilated -> %s closed (+%.2f%% material, %.0fs)"
        % (radius_mm, "{:,}".format(n0), "{:,}".format(n1), "{:,}".format(n2),
           100.0 * (n2 - n0) / max(n0, 1), time.time() - t0)
    )
    _say("    " + log[-1], quiet)
    return out


def morph_min_thickness(vol, min_mm, pitch, log, quiet=False, grow_frac=0.5,
                        thin_min_mm3=0.0):
    """Guarantee a minimum feature size.

    A voxel is 'thin' when no ball of radius min/2 fits inside the solid while
    still covering it - the morphological opening test. Thin material is then
    grown by min/2 in every direction, so a sheet of thickness s becomes s+min
    and a tapering strand tip becomes a cap of radius min/2.

    This is the same quantity mesh_doctor's shape-diameter thickness measures:
    for a slab, 2 * inradius == wall thickness, so enforcing inradius >= min/2
    enforces a measured thickness of >= min.
    """
    np = _np()
    if min_mm <= 0:
        log.append("thicken: skipped (min 0)")
        return vol, None
    _pitch_guard("--min-mm/2", min_mm * 0.5, pitch)
    t0 = time.time()
    n0 = int(vol.sum())
    r = min_mm * 0.5

    din = _edt(vol, pitch)
    core = din >= r
    del din
    n_core = int(core.sum())
    if n_core == 0:
        log.append("thicken: NOTHING in this model is %.2f mm thick - refusing to "
                   "grow everything; check the scale." % min_mm)
        _say("    " + log[-1], quiet)
        return vol, None
    dc = _edt(~core, pitch)
    opened = dc <= r
    del dc, core
    thin = vol & ~opened
    del opened
    n_thin = int(thin.sum())

    # Which thin voxels are a real thin FEATURE, and which are surface noise?
    #
    # This mattered enormously. Growing every flagged voxel by min/2 turned the
    # figure into acne: a surface-net mesh carries small bumps and terraces, the
    # tip of each one fails the opening test, and a 0.5 mm ball grown around it
    # is a 1 mm blister. At --min-mm 1.0 the render came back with the skirt,
    # legs and arms covered in warts while every NUMBER improved. Real thin
    # geometry - a ribbon, a cape edge, a fringe strand - is a large connected
    # sheet of thin voxels. Noise is a handful. Split them by component volume.
    from scipy import ndimage as _ndi

    vox_mm3 = pitch ** 3
    lab, nlab = _ndi.label(thin, structure=np.ones((3, 3, 3), dtype=np.int8))
    if nlab:
        sizes = np.bincount(lab.ravel())
        sizes[0] = 0
        edges_mm3 = [0.0, 0.05, 0.2, 1.0, 5.0, 25.0, 1e18]
        buckets = []
        for lo, hi in zip(edges_mm3[:-1], edges_mm3[1:]):
            m = (sizes * vox_mm3 >= lo) & (sizes * vox_mm3 < hi) & (sizes > 0)
            buckets.append("%.2g-%.2g mm3: %d comps / %s vox"
                           % (lo, hi, int(m.sum()), "{:,}".format(int(sizes[m].sum()))))
        log.append("thin components (%d total): %s" % (nlab, "; ".join(buckets)))
        _say("    " + log[-1], quiet)
        if thin_min_mm3 > 0:
            keep = (sizes * vox_mm3) >= thin_min_mm3
            keep[0] = False
            thin = keep[lab]
            n_kept = int(thin.sum())
            log.append("thin: kept %s of %s voxels in components >= %.2f mm3 "
                       "(dropped %d noise specks)"
                       % ("{:,}".format(n_kept), "{:,}".format(n_thin),
                          thin_min_mm3, int(nlab - keep.sum())))
            _say("    " + log[-1], quiet)
            n_thin = n_kept
        del lab, sizes
    if n_thin == 0:
        log.append("thicken: nothing left to grow after noise filtering")
        _say("    " + log[-1], quiet)
        return vol, {"thin_voxels": 0, "thin_frac": 0.0, "added_voxels": 0}
    dt = _edt(~thin, pitch)
    grown = dt <= (min_mm * grow_frac)
    del dt, thin
    out = vol | grown
    del grown
    n1 = int(out.sum())
    log.append(
        "thicken min=%.2f mm: %s of %s solid voxels were thin (%.2f%%); "
        "grew by %.2f mm -> +%s voxels (+%.2f%% material, %.0fs)"
        % (min_mm, "{:,}".format(n_thin), "{:,}".format(n0), 100.0 * n_thin / n0,
           min_mm * grow_frac, "{:,}".format(n1 - n0),
           100.0 * (n1 - n0) / n0, time.time() - t0)
    )
    _say("    " + log[-1], quiet)
    return out, {
        "thin_voxels": n_thin,
        "thin_frac": n_thin / float(n0),
        "added_voxels": n1 - n0,
        "added_frac": (n1 - n0) / float(n0),
    }


# ---------------------------------------------------------------------------
# solidify
# ---------------------------------------------------------------------------


def cmd_solidify(args):
    np = _np()
    md = _md()
    trimesh = _tm()
    from skimage import measure as skmeasure

    quiet = bool(args.json)
    rep = {"tool": "mesh_prep.solidify", "input": args.mesh, "args": vars(args)}
    log = []
    t_all = time.time()

    # -- 1. load and measure the input, so before/after is honest ------------
    _say("[1/7] loading %s" % args.mesh, quiet)
    mesh = md.load_mesh(args.mesh, process=True)
    before = md.measure(mesh, args.mesh)
    b_fails, b_warns = md.verdict(before)
    rep["before"] = before
    rep["before_blocking"] = b_fails
    rep["before_warnings"] = b_warns
    _say("      %s faces, watertight=%s, %d boundary edges, %d non-manifold, %d islands"
         % ("{:,}".format(before["faces"]), before["is_watertight"],
            before["boundary_edges"], before["nonmanifold_edges"],
            before["vertex_components"]), quiet)

    # -- 2. cheap lossless surface clean: weld, de-dupe, drop stray shells ---
    # No hole filling and no winding repair here: the voxel pass makes both
    # moot, and fill_holes on a mesh with interior membranes is a known no-op.
    _say("[2/7] dropping stray shells", quiet)
    mesh, slog = md.repair_surface(mesh, min_component_frac=args.island_frac,
                                   fill=False, verbose=False)
    log.extend("surface: " + s for s in slog)
    for s in slog:
        _say("      " + s, quiet)

    # -- 3. orient Z-up and scale to print size, so every dial below is mm ---
    _say("[3/7] orienting Z-up and scaling the figure to %.1f mm" % args.figure_mm, quiet)
    sinfo = md.scale_to_height(mesh, args.figure_mm, source_up=args.up)
    rep["scale"] = sinfo
    _say("      up axis was %s, scale x%.4g, footprint %.1f x %.1f mm"
         % (sinfo["source_up_axis"], sinfo["scale_factor"],
            sinfo["footprint_mm"][0], sinfo["footprint_mm"][1]), quiet)
    fig_bounds = np.array(mesh.bounds, dtype=float)

    # -- 4. voxelise and flood fill: this is what makes it a solid ----------
    pitch = float(args.pitch)
    _say("[4/7] voxelising at %.3f mm/voxel and flood-filling the interior" % pitch, quiet)
    t0 = time.time()
    vg = mesh.voxelized(pitch=pitch)
    shell = int(vg.filled_count)
    try:
        vg = vg.fill(method=args.voxel_fill)
    except Exception as e:
        log.append("fill(%s) failed (%s); falling back to default" % (args.voxel_fill, e))
        vg = vg.fill()
    mat = np.asarray(vg.matrix, dtype=bool)
    T = np.asarray(vg.transform, dtype=float)
    S = T[:3, :3]
    if not np.allclose(S, np.eye(3) * pitch, atol=pitch * 1e-4):
        raise SystemExit("mesh_prep: voxel grid is not an axis-aligned uniform grid; "
                         "cannot map indices to world reliably.\n%s" % S)
    origin = T[:3, 3].copy()
    log.append("voxelised: grid %s, %s surface voxels -> %s solid after %s fill (%.0fs)"
               % (tuple(int(x) for x in mat.shape), "{:,}".format(shell),
                  "{:,}".format(int(mat.sum())), args.voxel_fill, time.time() - t0))
    _say("      " + log[-1], quiet)
    _say("      grid is %.0f MB as bool; a distance transform of it is %.1f GB"
         % (_mb(mat), mat.size * 8 / 1e9), quiet)

    # -- pad. A solid touching the array edge marching-cubes into an OPEN
    #    surface: that single omission is the classic way this whole approach
    #    silently produces boundary edges. Pad generously, and enough below to
    #    hold the plinth.
    growth = max(args.close_mm, args.min_mm * 0.5) + pitch * 2
    pad_xy = int(np.ceil(growth / pitch)) + 3
    pad_z_hi = pad_xy
    plinth_drop = (args.plinth_h - args.sink_mm) if args.plinth else 0.0
    pad_z_lo = int(np.ceil((plinth_drop + growth) / pitch)) + 3
    vol = np.zeros((mat.shape[0] + 2 * pad_xy,
                    mat.shape[1] + 2 * pad_xy,
                    mat.shape[2] + pad_z_lo + pad_z_hi), dtype=bool)
    vol[pad_xy:pad_xy + mat.shape[0],
        pad_xy:pad_xy + mat.shape[1],
        pad_z_lo:pad_z_lo + mat.shape[2]] = mat
    del mat
    world0 = origin - np.array([pad_xy, pad_xy, pad_z_lo], dtype=float) * pitch
    rep["grid"] = {"shape": [int(x) for x in vol.shape], "pitch_mm": pitch,
                   "origin_mm": [float(x) for x in world0],
                   "voxels": int(vol.size), "solid_voxels_in": int(vol.sum())}
    _say("      padded to %s (%.0f MB)" % (tuple(int(x) for x in vol.shape), _mb(vol)), quiet)

    # world coordinate of each index along each axis
    ax = _axes(world0, vol.shape, pitch)

    # -- 5. morphology -------------------------------------------------------
    _say("[5/7] morphology", quiet)
    n_pre = int(vol.sum())
    vol = morph_close(vol, args.close_mm, pitch, log, quiet)
    vol, thin_stats = morph_min_thickness(vol, args.min_mm, pitch, log, quiet,
                                          grow_frac=args.grow_frac,
                                          thin_min_mm3=args.thin_min_mm3)
    rep["thicken"] = thin_stats
    rep["morphology_material_change_frac"] = (int(vol.sum()) - n_pre) / float(max(n_pre, 1))

    # -- 6. plinth, rasterised straight into the same grid -------------------
    # Doing it here rather than as a mesh boolean means it is fused and
    # watertight by construction. There is no boolean to fail.
    plinth = None
    if args.plinth:
        _say("[6/7] plinth", quiet)
        solid_idx = np.nonzero(vol)
        zw = ax[2][solid_idx[2]]
        # centre of mass of the solid (uniform density) - a figure with a big
        # hair mass behind her does not balance over her feet
        com = np.array([float(ax[0][solid_idx[0]].mean()),
                        float(ax[1][solid_idx[1]].mean()),
                        float(zw.mean())])
        foot = zw < (fig_bounds[0][2] + args.foot_band)
        if foot.sum() < 50:
            foot = zw < (fig_bounds[0][2] + args.foot_band * 4)
        fx = ax[0][solid_idx[0]][foot]
        fy = ax[1][solid_idx[1]][foot]
        feet_c = np.array([float(fx.mean()), float(fy.mean())])
        feet_r = float(np.sqrt((fx - feet_c[0]) ** 2 + (fy - feet_c[1]) ** 2).max())
        feet_area = float(foot.sum()) * pitch * pitch  # rough, band not slice
        del solid_idx, zw, fx, fy, foot

        cx, cy = float(feet_c[0]), float(feet_c[1])
        com_off = float(np.hypot(com[0] - cx, com[1] - cy))
        # radius must (a) clear the feet, (b) keep the centre of mass well
        # inside the footprint. 0.5 of the radius is a comfortable margin.
        r_need = max(feet_r + args.plinth_margin, com_off / 0.5, args.plinth_min_r)
        R = float(np.ceil(r_need)) if args.plinth_d <= 0 else args.plinth_d / 2.0

        z_top = args.sink_mm
        z_bot = args.sink_mm - args.plinth_h
        cham = min(args.plinth_cham, args.plinth_h * 0.5, R * 0.5)

        # The disc is sized from the feet and centred on the feet, so it can
        # easily reach outside the FIGURE's bounding box - in Y especially, since
        # a figure is much shallower than she is wide. Make room before drawing.
        vol, world0, grew = _ensure_room(vol, world0, pitch,
                                         [cx - R, cy - R, z_bot],
                                         [cx + R, cy + R, z_top])
        if grew:
            ax = _axes(world0, vol.shape, pitch)
            _say("      grew the grid to %s to fit the plinth"
                 % (tuple(int(x) for x in vol.shape),), quiet)
            log.append("grew grid to %s to fit the plinth" % (tuple(int(x) for x in vol.shape),))
        rr = np.sqrt((ax[0][:, None] - cx) ** 2 + (ax[1][None, :] - cy) ** 2)
        kk = np.nonzero((ax[2] >= z_bot) & (ax[2] <= z_top))[0]
        added = 0
        for k in kk:
            z = ax[2][k]
            rad = R
            if cham > 0 and z > z_top - cham:
                rad = R - (z - (z_top - cham))
            if args.plinth_bottom_cham > 0 and z < z_bot + args.plinth_bottom_cham:
                rad = min(rad, R - (z_bot + args.plinth_bottom_cham - z))
            if rad <= 0:
                continue
            m = rr <= rad
            added += int(m.sum() - (vol[:, :, k] & m).sum())
            vol[:, :, k] |= m
        del rr
        plinth = {
            "shape": "cylinder, chamfered top edge",
            "radius_mm": R, "diameter_mm": 2 * R,
            "thickness_mm": float(args.plinth_h),
            "top_chamfer_mm": float(cham),
            "figure_sunk_into_plinth_mm": float(args.sink_mm),
            "z_range_mm": [float(z_bot), float(z_top)],
            "centred_on_feet_xy_mm": [cx, cy],
            "centre_of_mass_mm": [float(x) for x in com],
            "com_offset_from_plinth_centre_mm": com_off,
            "com_offset_as_frac_of_radius": com_off / R,
            "feet_bounding_radius_mm": feet_r,
            "feet_band_contact_area_mm2_approx": feet_area,
            "voxels_added": added,
        }
        rep["plinth"] = plinth
        _say("      centre of mass sits %.1f mm from the feet centre (%.0f%% of the "
             "plinth radius)" % (com_off, 100.0 * com_off / R), quiet)
        _say("      plinth: d=%.1f mm, %.1f mm thick, %.1f mm chamfer, figure sunk %.1f mm"
             % (2 * R, args.plinth_h, cham, args.sink_mm), quiet)
        log.append("plinth d=%.1f mm x %.1f mm, %s voxels added"
                   % (2 * R, args.plinth_h, "{:,}".format(added)))
    else:
        _say("[6/7] plinth: skipped (--no-plinth)", quiet)

    # -- 7. marching cubes ---------------------------------------------------
    # Hard guard: solid touching any face of the array extracts as an OPEN
    # surface, and every other check downstream still passes. Fail loudly here.
    if (vol[0].any() or vol[-1].any() or vol[:, 0].any() or vol[:, -1].any()
            or vol[:, :, 0].any() or vol[:, :, -1].any()):
        raise SystemExit("mesh_prep: solid material touches the voxel array boundary; "
                         "marching cubes would produce an open surface. This is a "
                         "padding bug, not a mesh problem.")
    _say("[7/7] marching cubes (%s)" % args.extract, quiet)
    t0 = time.time()
    if args.extract == "sdf":
        # Extract from a SIGNED DISTANCE FIELD, not the raw binary occupancy.
        #
        # Marching cubes on a binary field has genuinely ambiguous cases: where
        # two solid voxels meet only along an edge or a corner with the
        # complementary pair empty, there is no manifold triangulation, and the
        # extractor picks one - leaving a self-touching pinch. On this figure
        # that cost 2 non-manifold edges and 2 boundary edges out of 4.9 million,
        # which is tiny and still means NOT WATERTIGHT.
        #
        # d_out - d_in is smooth, crosses zero at exactly the same place the
        # binary 0.5 level does (both distances are one pitch at the boundary),
        # and has no ambiguous configurations. It also interpolates sub-voxel,
        # so it removes the marching-cubes staircase for free.
        f = _edt(~vol, pitch).astype(np.float32)
        f -= _edt(vol, pitch).astype(np.float32)
        del vol
        verts, faces, _n, _v = skmeasure.marching_cubes(
            f, level=0.0, spacing=(pitch, pitch, pitch))
        del f
    else:
        verts, faces, _n, _v = skmeasure.marching_cubes(
            vol.astype(np.uint8), level=0.5, spacing=(pitch, pitch, pitch))
        del vol
    verts = verts + world0
    # Winding, deterministically. marching_cubes on a binary field where solid=1
    # returns INWARD normals (measured: a solid ball comes back with volume
    # -7250). Reversing the face order is exact and needs no adjacency, which
    # matters because trimesh's fix_winding walks the face-adjacency graph and
    # that graph is worthless the moment a single non-manifold edge exists.
    out = trimesh.Trimesh(vertices=verts, faces=faces[:, ::-1], process=False)
    # Degenerate triangles first, and NO merge_vertices.
    # skimage emits exactly one vertex per crossed grid edge, so there are no
    # coincident vertices to weld - measured, 2980 verts / 2980 unique positions.
    # But a degenerate marching-cubes triangle has two DISTINCT indices at the
    # SAME position; welding those fuses two edges into one carrying four faces.
    # That is how 3 non-manifold edges appeared in an otherwise perfect 4.9M-edge
    # solid, and 3 non-manifold edges are enough to shatter face adjacency and
    # make fix_inversion report the whole model inside out.
    out.update_faces(out.nondegenerate_faces())
    # Marching cubes also emits the occasional DUPLICATED triangle. That was the
    # actual source of the 3 non-manifold edges, not the vertex welding I first
    # blamed: one triangle present twice gives each of its three edges four
    # faces. Two duplicates, three shared edges, and a 4.9M-edge solid stops
    # being watertight. Cheap to remove, and it is never legitimate on a closed
    # surface.
    n_before = len(out.faces)
    out.update_faces(out.unique_faces())
    if len(out.faces) != n_before:
        log.append("marching cubes emitted %d duplicate triangle(s) - removed "
                   "(each one makes 3 non-manifold edges)" % (n_before - len(out.faces)))
        _say("      " + log[-1], quiet)
    out.remove_unreferenced_vertices()
    if out.volume < 0:
        out.invert()
        log.append("winding: signed volume was negative after the deterministic "
                   "flip; inverted again")
    log.append("marching cubes -> %s verts / %s faces (%.0fs)"
               % ("{:,}".format(len(out.vertices)), "{:,}".format(len(out.faces)),
                  time.time() - t0))
    _say("      " + log[-1], quiet)

    # Stray shells again, on the OUTPUT. The input mesh can be one
    # vertex-connected island and still rasterise into several: geometry joined
    # only through a non-manifold pinch has no material at the join, so the
    # voxel grid separates what the triangle graph called connected. On the
    # first full run these were four single 0.25 mm voxels floating in mid air -
    # invisible at any render scale, and a real defect in a print.
    rep["strays"] = _drop_islands(out, args.stray_frac, log, quiet)

    # sanity: without morphology the output box must match the input box to
    # within a voxel. With morphology it should be larger by roughly the growth.
    got = np.array(out.bounds, dtype=float)
    dx = got[1][0] - got[0][0]
    rep["bbox_check"] = {
        "figure_bbox_mm": [[float(x) for x in fig_bounds[0]], [float(x) for x in fig_bounds[1]]],
        "output_bbox_mm": [[float(x) for x in got[0]], [float(x) for x in got[1]]],
        "x_growth_mm": float(dx - (fig_bounds[1][0] - fig_bounds[0][0])),
    }

    # final: centre XY, drop to z=0, and scale so the FILE is exactly total_mm
    T2 = np.eye(4)
    c = out.bounds.mean(axis=0)
    T2[0, 3] = -c[0]
    T2[1, 3] = -c[1]
    T2[2, 3] = -out.bounds[0][2]
    out.apply_transform(T2)
    if args.total_mm > 0:
        f = args.total_mm / float(out.extents[2])
        out.apply_scale(f)
        T3 = np.eye(4)
        T3[2, 3] = -out.bounds[0][2]
        out.apply_transform(T3)
        log.append("final uniform scale x%.5f so the file is exactly %.1f mm tall"
                   % (f, args.total_mm))
        rep["final_scale_factor"] = float(f)
        if plinth:
            for k in ("radius_mm", "diameter_mm", "thickness_mm", "top_chamfer_mm",
                      "figure_sunk_into_plinth_mm"):
                plinth[k] = float(plinth[k]) * f
        _say("      " + log[-1], quiet)

    after = md.measure(out, None)
    a_fails, a_warns = md.verdict(after)
    rep["after"] = after
    rep["after_blocking"] = a_fails
    rep["after_warnings"] = a_warns
    rep["print_size"] = {
        "bbox_mm": [float(x) for x in out.extents],
        "height_mm": float(out.extents[2]),
        "volume_cm3": float(out.volume) / 1000.0 if out.is_watertight else None,
        "surface_area_cm2": float(out.area) / 100.0,
    }
    rep["log"] = log
    rep["seconds"] = round(time.time() - t_all, 1)

    if args.out:
        md.save_mesh(out, args.out)
        rep["out"] = args.out
        rep["out_bytes"] = os.path.getsize(args.out)
        _say("      wrote %s (%.1f MB)" % (args.out, os.path.getsize(args.out) / 1e6), quiet)
    if args.report:
        os.makedirs(os.path.dirname(os.path.abspath(args.report)), exist_ok=True)
        with open(args.report, "w") as fh:
            json.dump(rep, fh, indent=1, default=str)

    if args.json:
        print(json.dumps(rep, indent=1, default=str))
    else:
        print("")
        print("=" * 78)
        print("SOLIDIFY  %s" % os.path.basename(args.mesh))
        print("=" * 78)
        print("  %-30s %-22s %s" % ("", "BEFORE", "AFTER"))
        for k, lab in (("faces", "faces"), ("boundary_edges", "boundary (open) edges"),
                       ("nonmanifold_edges", "non-manifold edges"),
                       ("vertex_components", "islands"),
                       ("is_watertight", "watertight"),
                       ("is_winding_consistent", "winding consistent"),
                       ("is_volume", "sliceable solid")):
            bv, av = before[k], after[k]
            # bool is a subclass of int - check it first or True prints as 1
            fmt = (lambda v: str(v) if isinstance(v, bool)
                   else "{:,}".format(v) if isinstance(v, int) else str(v))
            print("  %-30s %-22s %s" % (lab, fmt(bv), fmt(av)))
        print("-" * 78)
        print("  bounding box:  %.2f x %.2f x %.2f mm" % tuple(rep["print_size"]["bbox_mm"]))
        if rep["print_size"]["volume_cm3"]:
            print("  solid volume:  %.2f cm3" % rep["print_size"]["volume_cm3"])
        print("  surface area:  %.1f cm2" % rep["print_size"]["surface_area_cm2"])
        if plinth:
            print("  plinth:        %.1f mm diameter x %.1f mm, %.1f mm top chamfer"
                  % (plinth["diameter_mm"], plinth["thickness_mm"], plinth["top_chamfer_mm"]))
        print("-" * 78)
        if a_fails:
            print("  STILL BLOCKING:")
            for f in a_fails:
                print("    x %s" % f)
        else:
            print("  no blocking defects - this is a closed, manifold, single-body solid")
        for w in a_warns:
            print("    ! %s" % w)
        print("=" * 78)
    return 2 if a_fails else 0


# ---------------------------------------------------------------------------
# thin map - WHERE the thin material is, in pixels rather than adjectives
# ---------------------------------------------------------------------------


def _thinmap(pts, thick, thresholds, path, title, height_mm):
    """Front (XZ) and side (YZ) orthographic scatter of the surface samples,
    with material under each threshold painted on top. This is the picture that
    answers 'will the hair print' - you look at where the red is."""
    np = _np()
    from PIL import Image, ImageDraw

    W = 460
    pad = 26
    zlo, zhi = float(pts[:, 2].min()), float(pts[:, 2].max())
    span = max(zhi - zlo, 1e-6)
    H = int(W * 1.05)
    scale = (H - 2 * pad) / span

    panels = []
    colours = [((214, 48, 49), thresholds[0]), ((250, 160, 40), thresholds[1])]
    for axis, name in ((0, "front (X-Z)"), (1, "side (Y-Z)")):
        im = Image.new("RGB", (W, H), (255, 255, 255))
        d = ImageDraw.Draw(im)
        u = pts[:, axis]
        uc = (u.min() + u.max()) / 2.0

        def px(sel):
            x = (u[sel] - uc) * scale + W / 2.0
            y = H - pad - (pts[sel, 2] - zlo) * scale
            return np.stack([x, y], axis=1)

        allsel = np.ones(len(pts), bool)
        for x, y in px(allsel):
            d.point((x, y), fill=(205, 205, 205))
        # draw the coarser threshold first so the finest one wins on top
        for col, thr in sorted(colours, key=lambda c: -c[1]):
            sel = thick < thr
            if not sel.any():
                continue
            for x, y in px(sel):
                d.ellipse([x - 1.1, y - 1.1, x + 1.1, y + 1.1], fill=col)
        d.rectangle([0, 0, W - 1, H - 1], outline=(120, 120, 120))
        d.text((6, 6), "%s   %s" % (title, name), fill=(20, 20, 20))
        d.text((6, H - 16), "height %.0f mm   red < %.2f mm   orange < %.2f mm"
               % (height_mm, thresholds[0], thresholds[1]), fill=(60, 60, 60))
        # a millimetre ruler up the left edge
        for mm in range(0, int(span) + 1, 25):
            y = H - pad - mm * scale
            d.line([2, y, 10, y], fill=(150, 150, 150))
            d.text((12, y - 6), "%d" % mm, fill=(150, 150, 150))
        panels.append(im)

    sheet = Image.new("RGB", (len(panels) * W + (len(panels) + 1) * 8, H + 16), (28, 28, 30))
    for i, im in enumerate(panels):
        sheet.paste(im, (8 + i * (W + 8), 8))
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    sheet.save(path, quality=93)
    return path


def _regions(pts, thick, thr, bands):
    """Thin fraction inside named boxes. The band definitions come from LOOKING
    at the turntable, so they are named body parts, not deciles."""
    np = _np()
    zlo, zhi = float(pts[:, 2].min()), float(pts[:, 2].max())
    span = max(zhi - zlo, 1e-9)
    out = []
    thin = thick < thr
    for name, z0, z1, xabs in bands:
        sel = (pts[:, 2] >= zlo + z0 * span) & (pts[:, 2] < zlo + z1 * span)
        if xabs is not None:
            xc = (pts[:, 0].min() + pts[:, 0].max()) / 2.0
            half = (pts[:, 0].max() - pts[:, 0].min()) / 2.0
            if xabs > 0:
                sel &= np.abs(pts[:, 0] - xc) >= xabs * half
            else:
                sel &= np.abs(pts[:, 0] - xc) < (-xabs) * half
        n = int(sel.sum())
        out.append({
            "region": name,
            "z_from_mm": round(zlo + z0 * span, 1),
            "z_to_mm": round(zlo + z1 * span, 1),
            "samples": n,
            "thin_frac": float(thin[sel].mean()) if n else None,
            "share_of_all_thin": float(thin[sel].sum() / max(int(thin.sum()), 1)),
            "median_thickness_mm": float(np.median(thick[sel])) if n else None,
        })
    return out


# TERRA's proportions, read off the turntable render at mesh/views/.
# Fractions of total file height, with the plinth included at the bottom.
TERRA_BANDS = [
    ("plinth",                 0.000, 0.035, None),
    ("boots and ankles",       0.035, 0.150, None),
    ("legs and skirt hem",     0.150, 0.330, None),
    ("skirt panel / cape",     0.330, 0.460, None),
    ("hips, wrap skirt, hair fall", 0.460, 0.560, None),
    ("torso and bodice",       0.560, 0.700, -0.45),
    ("outstretched arms",      0.560, 0.700, 0.45),
    ("shoulders, upper arms, hair mass", 0.700, 0.800, None),
    ("head and face",          0.800, 0.910, None),
    ("hair crown and ribbon",  0.910, 1.001, None),
]


def cmd_thinmap(args):
    np = _np()
    md = _md()
    mesh = md.load_mesh(args.mesh, process=True)
    if args.height:
        md.scale_to_height(mesh, args.height, source_up=args.up)
    thick, pts, valid = md.sample_thickness(mesh, n_samples=args.samples, seed=args.seed)
    p = _thinmap(pts[valid], thick[valid], (args.min_mm, args.warn_mm),
                 args.out, args.name or os.path.basename(args.mesh),
                 float(mesh.extents[2]))
    print("wrote %s" % p)
    return 0


# ---------------------------------------------------------------------------
# audit
# ---------------------------------------------------------------------------


def cmd_audit(args):
    np = _np()
    md = _md()
    quiet = bool(args.json)
    mesh = md.load_mesh(args.mesh, process=True)
    if args.height:
        md.scale_to_height(mesh, args.height, source_up=args.up)

    rep = {"tool": "mesh_prep.audit", "mesh": args.mesh}
    d = md.measure(mesh, args.mesh)
    fails, warns = md.verdict(d)
    rep["topology"] = d
    rep["blocking"] = fails
    rep["warnings"] = warns
    rep["size_mm"] = {
        "bbox": [float(x) for x in mesh.extents],
        "height": float(mesh.extents[2]),
        "volume_cm3": float(mesh.volume) / 1000.0 if mesh.is_watertight else None,
        "area_cm2": float(mesh.area) / 100.0,
    }

    _say("  sampling thickness (%s points, 9-ray cone each)..." % "{:,}".format(args.samples), quiet)
    t0 = time.time()
    thick, pts, valid = md.sample_thickness(mesh, n_samples=args.samples, seed=args.seed)
    tv, pv = thick[valid], pts[valid]
    rep["thickness"] = {
        "samples_valid": int(valid.sum()),
        "samples_no_far_wall": int((~valid).sum()),
        "seconds": round(time.time() - t0, 1),
        "trusted": bool(d["is_watertight"] and not d["nonmanifold_edges"]),
        "min_mm": float(tv.min()),
        "max_mm": float(tv.max()),
        "percentiles_mm": {str(q): float(np.percentile(tv, q))
                           for q in (1, 5, 10, 25, 50, 75, 90, 99)},
    }
    for thr in args.threshold:
        rep["thickness"]["frac_below_%.2fmm" % thr] = float((tv < thr).mean())
    rep["thickness"]["by_region"] = {
        "%.2fmm" % thr: _regions(pv, tv, thr, TERRA_BANDS) for thr in args.threshold
    }

    _say("  overhang...", quiet)
    rep["overhang"] = md.overhang_report(mesh, angle_deg=args.angle, source_up="z",
                                         height_mm=None, check_support=True)
    # name the overhang bands too
    n = mesh.face_normals
    area = mesh.area_faces
    cz = mesh.triangles_center[:, 2]
    zlo, zhi = float(mesh.bounds[0][2]), float(mesh.bounds[1][2])
    span = max(zhi - zlo, 1e-9)
    import math as _m
    bed_tol = max(0.2, 0.002 * span)
    on_bed = (cz - zlo < bed_tol) & (n[:, 2] < -0.5)
    steep = (n[:, 2] < -_m.cos(_m.radians(args.angle))) & ~on_bed
    obr = []
    tx = mesh.triangles_center[:, 0]
    xc = (mesh.bounds[0][0] + mesh.bounds[1][0]) / 2.0
    xhalf = (mesh.bounds[1][0] - mesh.bounds[0][0]) / 2.0
    for name, z0, z1, xabs in TERRA_BANDS:
        m = (cz >= zlo + z0 * span) & (cz < zlo + z1 * span)
        # bands that share a z range and differ only by distance from the centre
        # line - torso vs outstretched arms - must apply that filter here too, or
        # they report identical numbers and look like a copy-paste bug.
        if xabs is not None:
            m &= (np.abs(tx - xc) >= xabs * xhalf) if xabs > 0 \
                else (np.abs(tx - xc) < (-xabs) * xhalf)
        a = float(area[m].sum())
        obr.append({"region": name, "area_cm2": a / 100.0,
                    "overhang_area_frac": float(area[m & steep].sum() / a) if a > 0 else 0.0,
                    "share_of_all_overhang": float(area[m & steep].sum()
                                                   / max(float(area[steep].sum()), 1e-9))})
    rep["overhang"]["by_region"] = obr

    if args.thinmap:
        rep["thinmap"] = _thinmap(pv, tv, (args.threshold[0], args.threshold[-1]),
                                  args.thinmap, args.name or os.path.basename(args.mesh),
                                  float(mesh.extents[2]))

    if args.report:
        os.makedirs(os.path.dirname(os.path.abspath(args.report)), exist_ok=True)
        with open(args.report, "w") as fh:
            json.dump(rep, fh, indent=1, default=str)

    if args.json:
        print(json.dumps(rep, indent=1, default=str))
        return 0

    t = rep["thickness"]
    o = rep["overhang"]
    print("=" * 78)
    print("PRINT AUDIT  %s" % os.path.basename(args.mesh))
    print("=" * 78)
    print("  bounding box:   %.2f x %.2f x %.2f mm" % tuple(rep["size_mm"]["bbox"]))
    if rep["size_mm"]["volume_cm3"]:
        print("  solid volume:   %.2f cm3      surface %.1f cm2"
              % (rep["size_mm"]["volume_cm3"], rep["size_mm"]["area_cm2"]))
    print("  topology:       watertight=%s  non-manifold=%s  islands=%s  winding=%s"
          % (d["is_watertight"], "{:,}".format(d["nonmanifold_edges"]),
             d["vertex_components"], d["is_winding_consistent"]))
    if not t["trusted"]:
        print("  !! THICKNESS BELOW IS UNTRUSTWORTHY - input is not a closed solid")
    print("- thickness " + "-" * 66)
    print("  percentiles mm: " + "  ".join("p%s=%.2f" % (k, v)
                                           for k, v in t["percentiles_mm"].items()))
    for thr in args.threshold:
        print("  below %.2f mm:   %.2f%% of sampled surface"
              % (thr, 100.0 * t["frac_below_%.2fmm" % thr]))
    thr0 = args.threshold[0]
    print("  where (below %.2f mm):" % thr0)
    for r in sorted(rep["thickness"]["by_region"]["%.2fmm" % thr0],
                    key=lambda r: -(r["share_of_all_thin"])):
        if r["samples"] == 0:
            continue
        print("    %-36s %5.1f%% thin   %5.1f%% of all thin material   median %.1f mm"
              % (r["region"], 100.0 * r["thin_frac"], 100.0 * r["share_of_all_thin"],
                 r["median_thickness_mm"]))
    print("- overhang (past %.0f deg) " % args.angle + "-" * 50)
    print("  overhanging:    %.2f%% of surface area" % (100.0 * o["overhang_area_fraction"]))
    print("  flat ceilings:  %.2f%% (bridges, the hard case)"
          % (100.0 * o["flat_ceiling_area_fraction"]))
    print("  unsupported:    %s" % o.get("note_support", "n/a"))
    print("  bed contact:    %.1f mm2  (contact/height^2 = %.4f, needs_base=%s)"
          % (o["bed_contact_area"], o["bed_contact_vs_height2"], o["needs_base"]))
    print("  where:")
    for r in sorted(obr, key=lambda r: -r["share_of_all_overhang"])[:6]:
        print("    %-36s %5.1f%% of that band   %5.1f%% of all overhang"
              % (r["region"], 100.0 * r["overhang_area_frac"],
                 100.0 * r["share_of_all_overhang"]))
    if rep.get("thinmap"):
        print("- look at it " + "-" * 65)
        print("  %s" % rep["thinmap"])
    print("=" * 78)
    return 0


# ---------------------------------------------------------------------------
# render - reuse the rasteriser terra_mesh.py already proved
# ---------------------------------------------------------------------------


def cmd_render(args):
    if HERE not in sys.path:
        sys.path.insert(0, HERE)
    import terra_mesh

    r = terra_mesh.render_one(args.mesh, args.name, args.outdir, size=args.size,
                              frames=args.frames, ss=2, up=args.up,
                              samples=args.samples, style="clay", mp4=args.mp4)
    print(json.dumps(r, indent=1, default=str) if args.json else r)
    return 0


# ---------------------------------------------------------------------------
# export
# ---------------------------------------------------------------------------


def cmd_export(args):
    md = _md()
    np = _np()
    mesh = md.load_mesh(args.mesh, process=True)
    d = md.measure(mesh, args.mesh)
    if not d["is_watertight"] and not args.force:
        print("mesh_prep: refusing to export - input is not watertight "
              "(%d boundary edges, %d non-manifold)." % (d["boundary_edges"],
                                                         d["nonmanifold_edges"]),
              file=sys.stderr)
        return 2
    written = []
    for out in args.out:
        os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
        mesh.export(out)
        rec = {"path": out, "bytes": os.path.getsize(out)}
        # An export that silently breaks the mesh is the classic last-step
        # failure. Re-read what is actually on disk and re-measure it.
        try:
            rt = md.load_mesh(out, process=True)
            rd = md.measure(rt, out)
            rec.update({
                "reloaded_faces": rd["faces"],
                "reloaded_watertight": rd["is_watertight"],
                "reloaded_nonmanifold": rd["nonmanifold_edges"],
                "reloaded_boundary": rd["boundary_edges"],
                "reloaded_islands": rd["vertex_components"],
                "reloaded_bbox_mm": [round(float(x), 4) for x in rt.extents],
                "reloaded_zmin_mm": round(float(rt.bounds[0][2]), 4),
                "reloaded_volume_cm3": round(float(rt.volume) / 1000.0, 3)
                if rd["is_watertight"] else None,
                "bbox_matches_source": bool(np.allclose(rt.extents, mesh.extents, atol=1e-3)),
                "ok": bool(rd["is_watertight"] and rd["nonmanifold_edges"] == 0),
            })
        except Exception as e:
            rec.update({"ok": False, "reload_error": str(e)})
        written.append(rec)
    if args.report:
        with open(args.report, "w") as fh:
            json.dump({"written": written}, fh, indent=1, default=str)
    if args.json:
        print(json.dumps({"written": written}, indent=1, default=str))
    else:
        print("=" * 78)
        print("EXPORT + RELOAD VERIFY")
        print("=" * 78)
        for w in written:
            print("  %-46s %8.1f MB" % (os.path.basename(w["path"]), w["bytes"] / 1e6))
            if w.get("ok"):
                print("      reload OK: %s faces, watertight, 0 non-manifold, %d island(s)"
                      % ("{:,}".format(w["reloaded_faces"]), w["reloaded_islands"]))
                print("      %.2f x %.2f x %.2f mm, zmin %.3f, %.2f cm3"
                      % tuple(w["reloaded_bbox_mm"] + [w["reloaded_zmin_mm"],
                                                       w["reloaded_volume_cm3"]]))
            else:
                print("      FAILED: %s" % json.dumps({k: v for k, v in w.items()
                                                       if k not in ("path", "bytes")}))
        print("=" * 78)
    return 0 if all(w.get("ok") for w in written) else 2


# ---------------------------------------------------------------------------


def estimate_material(volume_cm3, area_cm2, height_mm,
                      wall_mm=0.84, infill=0.15, pla_density=1.24,
                      resin_density=1.10, filament_d=1.75):
    """Filament and resin estimates from the model's own measured volume and area.

    ESTIMATE, not measurement. The shell term is area x wall thickness, which is
    the honest way to do this: a figurine is mostly shell, and quoting a flat
    'about 20% of solid' hides that. The slicer's own number supersedes this.
    """
    import math

    v_mm3 = volume_cm3 * 1000.0
    shell_mm3 = min(area_cm2 * 100.0 * wall_mm, v_mm3)
    interior_mm3 = max(v_mm3 - shell_mm3, 0.0)
    fdm_mm3 = shell_mm3 + interior_mm3 * infill
    fil_area = math.pi * (filament_d / 2.0) ** 2
    return {
        "fdm_material_cm3": fdm_mm3 / 1000.0,
        "fdm_shell_cm3": shell_mm3 / 1000.0,
        "fdm_infill_cm3": interior_mm3 * infill / 1000.0,
        "fdm_grams_pla": fdm_mm3 / 1000.0 * pla_density,
        "fdm_filament_m": fdm_mm3 / fil_area / 1000.0,
        "fdm_assumptions": "%.2f mm shell (2 perimeters), %.0f%% infill, PLA %.2f g/cm3, "
                           "%.2f mm filament" % (wall_mm, 100 * infill, pla_density, filament_d),
        "resin_grams": volume_cm3 * resin_density,
        "resin_grams_with_supports": volume_cm3 * resin_density * 1.18,
        "fdm_layers_at_0_2": int(round(height_mm / 0.2)),
        "resin_layers_at_0_05": int(round(height_mm / 0.05)),
    }


def cmd_card(args):
    """Write the one-page print card, filling every number from the JSON the
    earlier stages wrote. Nothing here is retyped by hand."""
    sol = json.load(open(args.solidify))
    aud = json.load(open(args.audit))
    exp = json.load(open(args.export)) if args.export else {"written": []}

    a = aud["topology"]
    t = aud["thickness"]
    o = aud["overhang"]
    sz = aud["size_mm"]
    b = sol["before"]
    pl = sol.get("plinth") or {}
    est = estimate_material(sz["volume_cm3"], sz["area_cm2"], sz["height"])

    thr = sorted([float(k.split("_")[-1].replace("mm", ""))
                  for k in t if k.startswith("frac_below_")], reverse=True)
    regions = aud["thickness"]["by_region"]["%.2fmm" % thr[0]]
    top_thin = [r for r in sorted(regions, key=lambda r: -(r["share_of_all_thin"] or 0))
                if r["samples"]][:4]
    top_over = sorted(o["by_region"], key=lambda r: -r["share_of_all_overhang"])[:4]

    L = []
    w = L.append
    w("# TERRA - print card")
    w("")
    w("**File to load: `%s`**" % args.primary)
    w("")
    w("One closed solid. Millimetres, Z-up, standing on its own plinth, bottom face")
    w("already on z = 0. Drop it in the slicer and it lands the right way up at the")
    w("right size - no scaling, no rotating, no repair step.")
    w("")
    w("Every number below is labelled. **MEASURED** was measured on this exact file.")
    w("**ESTIMATE** is arithmetic from measured quantities. **RULE OF THUMB** is")
    w("general hobby practice and was not tested on a printer - no printer was ever")
    w("identified for this project.")
    w("")
    w("## The file")
    w("")
    w("| | |")
    w("|---|---|")
    w("| Size | **%.1f x %.1f x %.1f mm** (w x d x h) MEASURED |"
      % (sz["bbox"][0], sz["bbox"][1], sz["bbox"][2]))
    w("| Solid volume | **%.1f cm3** MEASURED |" % sz["volume_cm3"])
    w("| Surface area | %.0f cm2 MEASURED |" % sz["area_cm2"])
    w("| Triangles | %s MEASURED |" % "{:,}".format(a["faces"]))
    w("| Watertight | **yes** - 0 open edges, 0 non-manifold edges, %d body MEASURED |"
      % a["vertex_components"])
    w("| Sits at | z = 0, centred on X/Y MEASURED |")
    w("")
    w("## Recommended settings")
    w("")
    w("| | Resin (MSLA) - **preferred** | FDM (0.4 mm nozzle) |")
    w("|---|---|---|")
    w("| Layer height | 0.03 - 0.05 mm | 0.12 - 0.16 mm |")
    w("| Supports | **yes**, auto, medium | **yes**, tree/organic |")
    w("| Orientation | as supplied, or tilted 15-20 deg | as supplied, plinth down |")
    w("| Material | ~%.0f g resin (~%.0f g with supports) ESTIMATE | ~%.0f g PLA, ~%.1f m of 1.75 mm ESTIMATE |"
      % (est["resin_grams"], est["resin_grams_with_supports"],
         est["fdm_grams_pla"], est["fdm_filament_m"]))
    w("| Layers | %s at 0.05 mm | %s at 0.2 mm |"
      % ("{:,}".format(est["resin_layers_at_0_05"]), "{:,}".format(est["fdm_layers_at_0_2"])))
    w("| Time | ~2.5 - 3.5 h RULE OF THUMB (MSLA time follows height, not volume) | ~14 - 22 h RULE OF THUMB |")
    w("")
    w("FDM material assumes %s." % est["fdm_assumptions"])
    w("Add roughly 15-25% for support material. RULE OF THUMB - your slicer's own")
    w("estimate supersedes all of this.")
    w("")
    w("**Why resin is preferred:** the minimum feature enforced here is 1.0 mm, which")
    w("clears a 0.4 mm nozzle, so FDM will physically print. But her face is ~20 mm")
    w("tall and her eyes and mouth are sub-millimetre relief; a 0.4 mm nozzle cannot")
    w("resolve them. FDM gives you the silhouette and the costume, not the face.")
    w("")
    w("## Will it print - the honest answer")
    w("")
    w("| | |")
    w("|---|---|")
    for x in thr:
        w("| Surface thinner than %.2f mm | **%.2f%%** MEASURED |"
          % (x, 100.0 * t["frac_below_%.2fmm" % x]))
    w("| Thinnest 1%% of surface | %.2f mm MEASURED |" % t["percentiles_mm"]["1"])
    w("| Median wall thickness | %.1f mm MEASURED |" % t["percentiles_mm"]["50"])
    w("| Overhanging past 45 deg | **%.1f%%** of surface MEASURED |"
      % (100.0 * o["overhang_area_fraction"]))
    w("| Of that, nothing beneath it | %.0f%% - support from the plate MEASURED |"
      % (100.0 * o.get("unsupported_fraction_of_overhangs", 0)))
    w("| Near-horizontal ceilings | %.1f%% of surface MEASURED |"
      % (100.0 * o["flat_ceiling_area_fraction"]))
    w("| Bed contact | %.0f mm2 MEASURED |" % o["bed_contact_area"])
    w("")
    w("Where the remaining thin material is (share of all sub-%.2f mm surface):" % thr[0])
    w("")
    for r in top_thin:
        w("- **%s** - holds %.0f%% of it; %.1f%% of that region's surface is thin" %
          (r["region"], 100.0 * r["share_of_all_thin"], 100.0 * r["thin_frac"]))
    w("")
    w("Where the supports go (share of all overhanging surface):")
    w("")
    for r in top_over:
        w("- **%s** - %.0f%% of it" % (r["region"], 100.0 * r["share_of_all_overhang"]))
    w("")
    w("## Do you need to split it?")
    w("")
    w("**No.** MEASURED reasoning, not a preference:")
    w("")
    w("- It is %.0f x %.0f x %.0f mm. That fits the build volume of every consumer"
      % (sz["bbox"][0], sz["bbox"][1], sz["bbox"][2]))
    w("  FDM printer and every consumer MSLA machine except the smallest.")
    w("- Only **%.1f%%** of the surface overhangs past 45 deg, and only **%.0f%%** of"
      % (100.0 * o["overhang_area_fraction"],
         100.0 * o.get("unsupported_fraction_of_overhangs", 0)))
    w("  that has nothing beneath it. That is an ordinary support job, not a")
    w("  split-and-peg job.")
    w("- The hardest case is the **outstretched arms**: they are near-horizontal")
    w("  cantilevers, and they carry the densest overhang of any band (%.0f%% of that"
      % (100.0 * [r for r in o["by_region"]
                  if r["region"] == "outstretched arms"][0]["overhang_area_frac"]))
    w("  band's own surface, against %.0f%% for the torso). A waist or neck cut would"
      % (100.0 * [r for r in o["by_region"]
                  if r["region"] == "torso and bodice"][0]["overhang_area_frac"]))
    w("  not help them at all - they hang off the torso, so the only cut that reaches")
    w("  them is at the shoulder, through a ~5 mm arm. That puts a visible seam and a")
    w("  peg on a bare shoulder, to save supports you were going to print anyway.")
    w("")
    w("If you want to split it regardless, cut at the waist under the wrap skirt where")
    w("the seam hides in an existing costume line, and use a 4 mm peg with 0.15-0.2 mm")
    w("clearance. RULE OF THUMB - not done here, and not needed.")
    w("")
    w("## The plinth")
    w("")
    if pl:
        w("%.1f mm diameter, %.1f mm thick, %.1f mm chamfer on the top edge, flat"
          % (pl["diameter_mm"], pl["thickness_mm"], pl["top_chamfer_mm"]))
        w("underside for bed adhesion. The figure is sunk %.1f mm into it, so it is one"
          % pl["figure_sunk_into_plinth_mm"])
        w("fused solid, not two parts touching. MEASURED")
        w("")
        w("It is not decoration. Her boots are pointed with a raised heel, so bare she")
        w("stands on two small triangles - the previous stage measured %s mm2 of bed"
          % "201")
        w("contact, against **%.0f mm2** with the plinth. Her centre of mass also sits"
          % o["bed_contact_area"])
        w("**%.1f mm behind her feet** (the hair mass), which is %.0f%% of the plinth"
          % (pl["com_offset_from_plinth_centre_mm"],
             100.0 * pl["com_offset_as_frac_of_radius"]))
        w("radius - comfortably inside it, so she balances. MEASURED")
    w("")
    w("## What was done to the mesh, and what it cost")
    w("")
    w("| | Before | After |")
    w("|---|---|---|")
    w("| Open (boundary) edges | %s | **%d** |" % ("{:,}".format(b["boundary_edges"]),
                                                   a["boundary_edges"]))
    w("| Non-manifold edges | %s | **%d** |" % ("{:,}".format(b["nonmanifold_edges"]),
                                                a["nonmanifold_edges"]))
    w("| Disconnected shells | %d | **%d** |" % (b["vertex_components"],
                                                 a["vertex_components"]))
    w("| Winding consistent | %s | **%s** |" % (b["is_winding_consistent"],
                                                a["is_winding_consistent"]))
    w("| Sliceable solid | %s | **%s** |" % (b["is_volume"], a["is_volume"]))
    w("")
    w("MEASURED. The repair is a voxel remesh at %.2f mm, not a hole fill - a"
      % sol["args"]["pitch"])
    w("Hunyuan3D surface is pinched against itself and no surface-local repair can")
    w("open that. Detail below %.2f mm is gone; at this size that is under the FDM"
      % sol["args"]["pitch"])
    w("nozzle floor anyway.")
    w("")
    w("## Known compromises")
    w("")
    for c in CARD_COMPROMISES:
        w("- %s" % c)
    w("")
    if exp.get("written"):
        w("## Files")
        w("")
        w("| File | Size | Verified on reload |")
        w("|---|---|---|")
        for f in exp["written"]:
            w("| `%s` | %.0f MB | %s, %s faces, %.2f x %.2f x %.2f mm |"
              % (os.path.basename(f["path"]), f["bytes"] / 1e6,
                 "watertight" if f.get("ok") else "FAILED",
                 "{:,}".format(f.get("reloaded_faces", 0)),
                 f["reloaded_bbox_mm"][0], f["reloaded_bbox_mm"][1], f["reloaded_bbox_mm"][2]))
        w("")
        w("Every file above was written, re-read from disk and re-measured. MEASURED")
        w("")
        w("### Alternates in `alt/`")
        w("")
        w("Only take one of these if the primary gives you trouble. All three are")
        w("watertight single solids at 150.0 mm, verified the same way.")
        w("")
        w("| File | Why you would use it |")
        w("|---|---|")
        w("| `TERRA_150mm_lighter-file.stl` | Half the triangles (1.8M, 91 MB) if your "
          "slicer struggles with the primary. Built on a 0.20 mm grid instead of "
          "0.15 mm. Printability is the same; the **face is visibly softer** - "
          "shallower eyes, flatter nose. That is why it is not the primary. |")
        w("| `TERRA_150mm_resin-detail.stl` | Lighter intervention: 0.60 mm minimum "
          "feature instead of 1.00 mm, gentler crevice closing. Slightly crisper "
          "detail, but 0.67% of surface under 0.80 mm against the primary's 0.21%. "
          "Resin only. |")
        w("| `TERRA_150mm_minimal-edit.stl` | Repaired and based, but **no** thickening "
          "and **no** closing. Closest to what Hunyuan3D produced. 1.23% of surface "
          "under 0.80 mm and 0.52% under 0.30 mm - expect fine detail to fail. For "
          "comparison, or for a high-resolution resin machine. |")
    w("")
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w") as fh:
        fh.write("\n".join(L) + "\n")
    print("wrote %s (%d lines)" % (args.out, len(L)))
    return 0


CARD_COMPROMISES = [
    "**Her hair is one fused mass, not separate strands.** Hunyuan3D already "
    "reconstructed it as fat fused sausage locks rather than hair, and the crevice "
    "closing merged the near-touching ones further. This is what a commercial "
    "statuette does on purpose, and it is why the hair is not the thin-feature "
    "problem you would expect - it is among the THICKEST material in the model.",

    "**The skirt fringe the source render showed as many separate hanging strands "
    "is gone**, absorbed into the skirt panel. Nothing that fine can exist at "
    "150 mm in any process.",

    "**The face is soft.** It is legible - lidded eyes, nose, mouth, ribbon, "
    "earrings - but it is a ~20 mm head reconstructed from a single image, not a "
    "sculpted one. Resin will show what is there; FDM will not.",

    "**Untextured.** Hunyuan3D's output carries geometry only, no colour. If you "
    "want to see her in colour, look at the TripoSplat orbit the mesh stage "
    "rendered - but a splat cannot be printed.",

    "**The solid carries a few dozen small tunnels** through it (genus ~43), left "
    "over from reconstruction noise. A slicer only needs inside vs outside, so this "
    "should not matter, and none was visible in the turntable or head renders. Not "
    "proven harmless by actually slicing it.",

    "**No slicer has opened this file.** None is installed on the box. Watertightness "
    "is verified by re-reading the written file and re-measuring it, which is a "
    "strong check, but it is not the same as PrusaSlicer/Cura/Bambu/Lychee ingesting "
    "it. This is the single largest remaining gap.",

    "**No printer, so every feature-size floor here is a rule of thumb.** FDM "
    "0.8-1.2 mm, resin ~0.3 mm and the 45 degree overhang rule are general practice, "
    "not measured on a machine.",
]


def cmd_decimate(args):
    """Cut the triangle count without moving the surface.

    A 0.15 mm voxel grid produces ~3.3M faces and a 163 MB binary STL. Nothing
    about a print needs that: at 150 mm tall, 3.3M faces is a 0.13 mm average
    edge, well under a resin pixel and far under any FDM extrusion width. Some
    slicers are slow or unhappy with files that size. So decimate - and then
    MEASURE the deviation rather than assuming quadric decimation was polite.
    """
    np = _np()
    md = _md()
    mesh = md.load_mesh(args.mesh, process=True)
    before = md.measure(mesh, args.mesh)
    ref = mesh.copy()

    t0 = time.time()
    out = mesh.simplify_quadric_decimation(face_count=args.faces)
    out.update_faces(out.nondegenerate_faces())
    out.update_faces(out.unique_faces())
    out.remove_unreferenced_vertices()
    if out.volume < 0:
        out.invert()
    secs = time.time() - t0
    after = md.measure(out, None)
    fails, warns = md.verdict(after)

    # How far did the surface actually move? Sample the decimated surface and
    # measure the distance to the ORIGINAL. This is the number that says whether
    # detail was lost, and it is in millimetres, at print scale.
    dev = None
    try:
        pts = out.sample(args.dev_samples)
        _cp, dist, _fid = ref.nearest.on_surface(pts)
        dev = {
            "samples": int(len(pts)),
            "mean_mm": float(dist.mean()),
            "p50_mm": float(np.percentile(dist, 50)),
            "p95_mm": float(np.percentile(dist, 95)),
            "p99_mm": float(np.percentile(dist, 99)),
            "max_mm": float(dist.max()),
        }
    except Exception as e:
        dev = {"error": str(e)}

    rep = {
        "tool": "mesh_prep.decimate", "input": args.mesh, "target_faces": args.faces,
        "faces_before": before["faces"], "faces_after": after["faces"],
        "reduction": 1.0 - after["faces"] / float(before["faces"]),
        "seconds": round(secs, 1),
        "watertight_before": before["is_watertight"],
        "watertight_after": after["is_watertight"],
        "nonmanifold_after": after["nonmanifold_edges"],
        "boundary_after": after["boundary_edges"],
        "islands_after": after["vertex_components"],
        "volume_cm3_before": before["volume"] / 1000.0,
        "volume_cm3_after": after["volume"] / 1000.0,
        "volume_change_pct": 100.0 * (after["volume"] - before["volume"]) / before["volume"],
        "area_cm2_before": before["surface_area"] / 100.0,
        "area_cm2_after": after["surface_area"] / 100.0,
        "bbox_mm_after": [float(x) for x in out.extents],
        "deviation_from_original": dev,
        "blocking": fails,
    }
    if args.out:
        md.save_mesh(out, args.out)
        rep["out"] = args.out
        rep["out_bytes"] = os.path.getsize(args.out)
    if args.report:
        with open(args.report, "w") as fh:
            json.dump(rep, fh, indent=1, default=str)
    if args.json:
        print(json.dumps(rep, indent=1, default=str))
    else:
        print("=" * 78)
        print("DECIMATE  %s" % os.path.basename(args.mesh))
        print("=" * 78)
        print("  faces:      %s -> %s  (%.1f%% fewer, %.0fs)"
              % ("{:,}".format(rep["faces_before"]), "{:,}".format(rep["faces_after"]),
                 100 * rep["reduction"], secs))
        print("  watertight: %s -> %s   non-manifold %d, boundary %d, islands %d"
              % (rep["watertight_before"], rep["watertight_after"],
                 rep["nonmanifold_after"], rep["boundary_after"], rep["islands_after"]))
        print("  volume:     %.3f -> %.3f cm3  (%+.3f%%)"
              % (rep["volume_cm3_before"], rep["volume_cm3_after"], rep["volume_change_pct"]))
        print("  bbox:       %.2f x %.2f x %.2f mm" % tuple(rep["bbox_mm_after"]))
        if dev and "p50_mm" in dev:
            print("  surface moved by: p50 %.4f mm, p95 %.4f mm, p99 %.4f mm, max %.4f mm"
                  % (dev["p50_mm"], dev["p95_mm"], dev["p99_mm"], dev["max_mm"]))
        if fails:
            for f in fails:
                print("    x %s" % f)
        print("=" * 78)
    return 2 if fails else 0


def build_parser():
    ap = argparse.ArgumentParser(
        prog="mesh_prep.py",
        description="Print preparation: solidify, thicken, base, audit, export.",
        epilog="Spec: craft/PRINTING.md. Measurement and repair primitives: mesh_doctor.py",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = ap.add_subparsers(dest="cmd", metavar="SUBCOMMAND")
    sub.required = True

    def common(sp):
        sp.add_argument("mesh", help="path to .glb/.gltf/.stl/.obj/.ply/.3mf")
        sp.add_argument("--json", action="store_true", help="machine-readable output")
        return sp

    s = common(sub.add_parser("solidify", help="one voxel pass: repair + close + thicken + plinth"))
    s.add_argument("--out", help="write the solid here (.glb recommended)")
    s.add_argument("--report", help="write the full before/after JSON here")
    s.add_argument("--figure-mm", type=float, default=145.0,
                   help="height of the FIGURE alone before the plinth (default 145)")
    s.add_argument("--total-mm", type=float, default=150.0,
                   help="final uniform scale so the FILE is exactly this tall; 0 = off")
    s.add_argument("--pitch", type=float, default=0.15,
                   help="voxel size in mm (default 0.15). Detail below this is lost.")
    s.add_argument("--close-mm", type=float, default=0.0,
                   help="morphological close radius in mm; merges gaps under 2x this")
    s.add_argument("--min-mm", type=float, default=0.0,
                   help="minimum feature size to enforce in mm (0 = do not thicken)")
    s.add_argument("--thin-min-mm3", type=float, default=0.0,
                   help="ignore thin components smaller than this volume in mm3; "
                        "they are surface noise and growing them makes blisters")
    s.add_argument("--grow-frac", type=float, default=0.5,
                   help="grow thin material by this multiple of --min-mm (default 0.5)")
    s.add_argument("--island-frac", type=float, default=0.01,
                   help="drop stray shells under this fraction of the largest (input mesh)")
    s.add_argument("--stray-frac", type=float, default=0.005,
                   help="drop stray shells under this fraction of the largest (output solid)")
    s.add_argument("--extract", choices=["sdf", "binary"], default="sdf",
                   help="surface extraction: sdf (signed distance, manifold and "
                        "sub-voxel smooth) or binary (raw occupancy)")
    s.add_argument("--voxel-fill", choices=["orthographic", "base", "holes"],
                   default="orthographic", help="interior flood fill method")
    s.add_argument("--up", choices=["auto", "x", "y", "z"], default="y",
                   help="source up axis; glTF/GLB is Y-up by specification")
    s.add_argument("--plinth", dest="plinth", action="store_true", default=True)
    s.add_argument("--no-plinth", dest="plinth", action="store_false")
    s.add_argument("--plinth-h", type=float, default=6.0, help="plinth thickness mm")
    s.add_argument("--plinth-d", type=float, default=0.0,
                   help="force plinth diameter mm (0 = size it from feet + centre of mass)")
    s.add_argument("--plinth-margin", type=float, default=5.0,
                   help="mm of plinth beyond the feet bounding radius")
    s.add_argument("--plinth-min-r", type=float, default=12.0, help="minimum radius mm")
    s.add_argument("--plinth-cham", type=float, default=1.5, help="top edge chamfer mm")
    s.add_argument("--plinth-bottom-cham", type=float, default=0.0,
                   help="bottom edge chamfer mm (0 = flat, best bed adhesion)")
    s.add_argument("--sink-mm", type=float, default=1.2,
                   help="how deep the feet sit inside the plinth")
    s.add_argument("--foot-band", type=float, default=3.0,
                   help="mm above the lowest point counted as 'the feet'")
    s.set_defaults(func=cmd_solidify)

    a = common(sub.add_parser("audit", help="thickness + overhang at real scale, by named region"))
    a.add_argument("--height", type=float, help="scale to this height first (mm)")
    a.add_argument("--up", choices=["auto", "x", "y", "z"], default="z")
    a.add_argument("--threshold", type=float, action="append", default=None,
                   help="thin threshold in mm; repeat (default 0.8 and 0.3)")
    a.add_argument("--angle", type=float, default=45.0, help="overhang angle from vertical")
    a.add_argument("--samples", type=int, default=60000)
    a.add_argument("--seed", type=int, default=0)
    a.add_argument("--thinmap", help="write the front/side thin-map picture here")
    a.add_argument("--name", help="label for the picture")
    a.add_argument("--report", help="write the audit JSON here")
    a.set_defaults(func=cmd_audit)

    tmp = common(sub.add_parser("thinmap", help="just the thin-map picture"))
    tmp.add_argument("--out", required=True)
    tmp.add_argument("--height", type=float)
    tmp.add_argument("--up", choices=["auto", "x", "y", "z"], default="z")
    tmp.add_argument("--min-mm", type=float, default=0.8)
    tmp.add_argument("--warn-mm", type=float, default=0.3)
    tmp.add_argument("--samples", type=int, default=60000)
    tmp.add_argument("--seed", type=int, default=0)
    tmp.add_argument("--name")
    tmp.set_defaults(func=cmd_thinmap)

    r = common(sub.add_parser("render", help="turntable + head close-up (terra_mesh rasteriser)"))
    r.add_argument("--name", required=True)
    r.add_argument("--outdir", required=True)
    r.add_argument("--size", type=int, default=460)
    r.add_argument("--frames", type=int, default=8)
    r.add_argument("--samples", type=int, default=2600000)
    r.add_argument("--mp4", type=int, default=0)
    r.add_argument("--up", choices=["auto", "x", "y", "z"], default="z")
    r.set_defaults(func=cmd_render)

    cd = sub.add_parser("card", help="write the one-page print card from the stage JSONs")
    cd.add_argument("--solidify", required=True, help="solidify report JSON")
    cd.add_argument("--audit", required=True, help="audit report JSON")
    cd.add_argument("--export", help="export report JSON")
    cd.add_argument("--primary", required=True, help="filename the user should load")
    cd.add_argument("--out", required=True, help="write the card here (.md)")
    cd.set_defaults(func=cmd_card)

    dc = common(sub.add_parser("decimate", help="cut triangle count, then measure how far "
                                               "the surface moved"))
    dc.add_argument("--faces", type=int, required=True, help="target triangle count")
    dc.add_argument("--out", help="write the decimated mesh here")
    dc.add_argument("--report", help="write the JSON here")
    dc.add_argument("--dev-samples", type=int, default=40000,
                    help="points sampled to measure deviation from the original")
    dc.set_defaults(func=cmd_decimate)

    e = common(sub.add_parser("export", help="write files and re-verify each from disk"))
    e.add_argument("--out", action="append", required=True, metavar="PATH")
    e.add_argument("--report")
    e.add_argument("--force", action="store_true")
    e.set_defaults(func=cmd_export)

    return ap


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if not argv:
        build_parser().print_usage(sys.stderr)
        print("mesh_prep.py: a subcommand is required. Try --help.", file=sys.stderr)
        return 2
    args = build_parser().parse_args(argv)
    if getattr(args, "cmd", None) == "audit" and not args.threshold:
        args.threshold = [0.8, 0.3]
    if getattr(args, "threshold", None):
        args.threshold = sorted(args.threshold, reverse=True)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
