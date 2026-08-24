#!/usr/bin/env python3
"""mesh_doctor.py - diagnose, repair and qualify a generated mesh for 3D printing.

Generated meshes (Hunyuan3D, TripoSR, splat-to-mesh) look fine in a viewer and are
routinely unprintable. This tool measures the things a slicer actually cares about
and repairs the ones that can be repaired.

Subcommands
    diagnose   full topology + geometry report
    repair     weld, de-dupe, drop stray shells, fill holes, fix winding/normals,
               or voxel-remesh to a guaranteed-watertight solid
    scale      convert to Z-up and scale to a target print height in millimetres
    thickness  shape-diameter sampling; what fraction of the surface is too thin to print
    overhang   fraction of surface past the overhang angle, and where it sits
    export     write STL / 3MF / OBJ / PLY / GLB, refusing non-watertight by default

Every subcommand takes --json to emit machine-readable output for the pipeline.

Dependencies (all pip --user, no root):
    trimesh numpy scipy networkx rtree manifold3d shapely
    embreex        (fast raycasting; falls back to pure-python if absent)
    scikit-image   (marching cubes for the voxel repair path)

Written for comfy-studio. See craft/PRINTING.md for the spec these numbers are held to.
"""

import argparse
import json
import math
import os
import sys
import time

# ---------------------------------------------------------------------------
# lazy imports so that --help never pays for a 4 second numpy/trimesh import
# ---------------------------------------------------------------------------


def _np():
    import numpy as np

    return np


def _tm():
    import trimesh

    trimesh.util.log.setLevel(50)  # silence trimesh chatter on stderr
    return trimesh


# ---------------------------------------------------------------------------
# loading
# ---------------------------------------------------------------------------


def load_mesh(path, process=True):
    """Load any mesh file to a single Trimesh. Scenes get flattened with their
    node transforms baked in."""
    trimesh = _tm()
    if not os.path.exists(path):
        raise SystemExit("mesh_doctor: no such file: %s" % path)
    obj = trimesh.load(path, process=process, force="mesh")
    if isinstance(obj, trimesh.Scene):
        geoms = [g for g in obj.dump() if hasattr(g, "faces")]
        if not geoms:
            raise SystemExit("mesh_doctor: %s contains no triangle geometry" % path)
        obj = trimesh.util.concatenate(geoms)
    if not hasattr(obj, "faces"):
        raise SystemExit("mesh_doctor: %s did not load as a triangle mesh" % path)
    return obj


def save_mesh(mesh, path):
    d = os.path.dirname(os.path.abspath(path))
    if d:
        os.makedirs(d, exist_ok=True)
    mesh.export(path)
    return os.path.getsize(path)


# ---------------------------------------------------------------------------
# topology measurement
# ---------------------------------------------------------------------------


def edge_valence(mesh):
    """Histogram of how many faces share each undirected edge.

    1  = boundary edge (a hole)
    2  = manifold edge (what a printable mesh has everywhere)
    3+ = non-manifold edge (two surfaces pinched together; slicers choke)
    """
    np = _np()
    es = np.sort(mesh.edges, axis=1)
    order = np.lexsort(es.T)
    se = es[order]
    if len(se) == 0:
        return {}, 0
    changed = np.any(se[1:] != se[:-1], axis=1)
    starts = np.concatenate([[0], np.nonzero(changed)[0] + 1])
    counts = np.diff(np.concatenate([starts, [len(se)]]))
    hist = {}
    for v, c in zip(*np.unique(counts, return_counts=True)):
        hist[int(v)] = int(c)
    return hist, int(len(starts))


def duplicate_faces(mesh):
    np = _np()
    fs = np.sort(mesh.faces, axis=1)
    if len(fs) == 0:
        return 0
    order = np.lexsort(fs.T)
    sf = fs[order]
    changed = np.any(sf[1:] != sf[:-1], axis=1)
    starts = np.concatenate([[0], np.nonzero(changed)[0] + 1])
    counts = np.diff(np.concatenate([starts, [len(sf)]]))
    return int((counts - 1).sum())


def degenerate_faces(mesh):
    """Faces with zero (or near-zero) area - they carry no surface and confuse
    normal computation."""
    np = _np()
    try:
        good = mesh.nondegenerate_faces()
        return int(len(mesh.faces) - good.sum())
    except Exception:
        a = mesh.area_faces
        return int((a < 1e-12).sum())


def components(mesh):
    """Connected components by FACE ADJACENCY, largest first, as face counts.

    Caution: trimesh builds face adjacency only across edges shared by exactly
    two faces. On a mesh with many non-manifold edges those edges are excluded,
    which shatters the graph and wildly overcounts shells. Always read this
    number next to `vertex_components` below, which is the count of genuinely
    separate islands you would see in a viewer.
    """
    np = _np()
    try:
        parts = mesh.split(only_watertight=False)
    except Exception:
        return [len(mesh.faces)]
    sizes = sorted((len(p.faces) for p in parts), reverse=True)
    return sizes or [len(mesh.faces)]


def vertex_components(mesh):
    """True island count: components of the vertex graph, which does not care
    how many faces meet on an edge. Returns (count, face counts largest first)."""
    np = _np()
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import connected_components as cc

    nv = len(mesh.vertices)
    e = mesh.edges
    if len(e) == 0:
        return 1, [len(mesh.faces)]
    g = coo_matrix(
        (np.ones(len(e), dtype=np.int8), (e[:, 0], e[:, 1])), shape=(nv, nv)
    )
    n, labels = cc(g, directed=False)
    face_label = labels[mesh.faces[:, 0]]
    counts = np.bincount(face_label, minlength=n)
    return int(n), sorted((int(c) for c in counts if c > 0), reverse=True)


def normals_outward(mesh):
    """Positive signed volume means the winding/normals describe a solid seen
    from outside. Only meaningful once the mesh is close to closed."""
    try:
        return bool(mesh.volume > 0)
    except Exception:
        return None


def genus_from_euler(euler, n_components):
    """chi = 2*(components) - 2*genus for a closed orientable surface."""
    try:
        g = (2 * n_components - euler) / 2.0
        return g
    except Exception:
        return None


def measure(mesh, path=None):
    np = _np()
    hist, n_edges = edge_valence(mesh)
    boundary = hist.get(1, 0)
    manifold = hist.get(2, 0)
    nonman = sum(c for v, c in hist.items() if v >= 3)
    comps = components(mesh)
    try:
        n_islands, island_sizes = vertex_components(mesh)
    except Exception:
        n_islands, island_sizes = len(comps), comps
    uniq = len(np.unique(np.round(np.asarray(mesh.vertices, dtype=np.float64), 7), axis=0))
    try:
        vol = float(mesh.volume)
    except Exception:
        vol = float("nan")
    try:
        hull_vol = float(mesh.convex_hull.volume)
    except Exception:
        hull_vol = float("nan")
    d = {
        "path": path,
        "file_bytes": os.path.getsize(path) if path and os.path.exists(path) else None,
        "vertices": int(len(mesh.vertices)),
        "faces": int(len(mesh.faces)),
        "unique_vertex_positions": int(uniq),
        "unwelded_vertices": int(len(mesh.vertices) - uniq),
        "duplicate_faces": duplicate_faces(mesh),
        "degenerate_faces": degenerate_faces(mesh),
        "bounds_min": [float(x) for x in mesh.bounds[0]],
        "bounds_max": [float(x) for x in mesh.bounds[1]],
        "extents": [float(x) for x in mesh.extents],
        "centroid": [float(x) for x in mesh.centroid],
        "unique_edges": n_edges,
        "edge_valence": hist,
        "boundary_edges": boundary,
        "manifold_edges": manifold,
        "nonmanifold_edges": nonman,
        "nonmanifold_fraction": (nonman / n_edges) if n_edges else 0.0,
        "is_watertight": bool(mesh.is_watertight),
        "is_winding_consistent": bool(mesh.is_winding_consistent),
        "is_volume": bool(mesh.is_volume),
        "euler_number": int(mesh.euler_number),
        "components": len(comps),
        "component_face_counts_top10": comps[:10],
        "components_under_1pct": int(sum(1 for c in comps if c < max(comps) * 0.01)),
        "vertex_components": n_islands,
        "vertex_component_face_counts_top10": island_sizes[:10],
        "vertex_components_under_1pct": int(
            sum(1 for c in island_sizes if c < max(island_sizes) * 0.01)
        ),
        "volume": vol,
        "surface_area": float(mesh.area),
        "convex_hull_volume": hull_vol,
        "solidity": (vol / hull_vol) if hull_vol and hull_vol == hull_vol and hull_vol > 0 else None,
        "normals_outward": normals_outward(mesh),
    }
    # genus only means anything on a closed orientable surface
    d["genus"] = genus_from_euler(d["euler_number"], n_islands) if d["is_watertight"] else None
    return d


def verdict(d):
    """Plain-language pass/fail against the printability spec."""
    fails, warns = [], []
    if not d["is_watertight"]:
        fails.append(
            "NOT WATERTIGHT - %d boundary (open) edges. A slicer cannot tell inside from outside."
            % d["boundary_edges"]
        )
    if d["nonmanifold_edges"]:
        fails.append(
            "NON-MANIFOLD - %d of %d edges (%.1f%%) are shared by 3+ faces."
            % (d["nonmanifold_edges"], d["unique_edges"], 100.0 * d["nonmanifold_fraction"])
        )
    if not d["is_winding_consistent"]:
        fails.append("INCONSISTENT WINDING - face orientation flips across the surface.")
    if d["normals_outward"] is False:
        fails.append("NORMALS INVERTED - signed volume is negative; the solid is inside out.")
    n_isl = d.get("vertex_components", d["components"])
    if n_isl > 1:
        (fails if n_isl > 50 else warns).append(
            "%d disconnected islands (%d of them under 1%% of the largest). "
            "Stray shells slice as floating debris."
            % (n_isl, d.get("vertex_components_under_1pct", 0))
        )
    if d["duplicate_faces"]:
        warns.append("%d duplicate faces." % d["duplicate_faces"])
    if d["degenerate_faces"]:
        warns.append("%d degenerate (zero-area) faces." % d["degenerate_faces"])
    if d["genus"] is not None and d["genus"] > 20:
        warns.append(
            "genus ~%.0f - the surface carries a lot of tunnels/handles, usually reconstruction noise."
            % d["genus"]
        )
    return fails, warns


# ---------------------------------------------------------------------------
# repair
# ---------------------------------------------------------------------------


def repair_surface(mesh, min_component_frac=0.01, fill=True, verbose=True):
    """Conservative in-place surface repair. Preserves the original geometry.
    Cannot fix non-manifold edges - nothing surface-local can."""
    trimesh = _tm()
    np = _np()
    log = []

    before = (len(mesh.vertices), len(mesh.faces))
    mesh.merge_vertices()
    log.append("welded coincident vertices: %d -> %d" % (before[0], len(mesh.vertices)))

    try:
        mesh.update_faces(mesh.nondegenerate_faces())
        mesh.update_faces(mesh.unique_faces())
        mesh.remove_unreferenced_vertices()
        log.append("removed degenerate + duplicate faces: %d -> %d faces" % (before[1], len(mesh.faces)))
    except Exception as e:
        log.append("face cleanup skipped: %s" % e)

    if min_component_frac > 0:
        # drop islands by VERTEX connectivity, not face adjacency - face adjacency
        # is meaningless on a mesh with non-manifold edges
        try:
            from scipy.sparse import coo_matrix
            from scipy.sparse.csgraph import connected_components as cc

            e = mesh.edges
            g = coo_matrix(
                (np.ones(len(e), dtype=np.int8), (e[:, 0], e[:, 1])),
                shape=(len(mesh.vertices), len(mesh.vertices)),
            )
            n, labels = cc(g, directed=False)
            if n > 1:
                face_label = labels[mesh.faces[:, 0]]
                counts = np.bincount(face_label, minlength=n)
                keep_lbl = counts >= counts.max() * min_component_frac
                keep_face = keep_lbl[face_label]
                dropped_faces = int((~keep_face).sum())
                if dropped_faces:
                    mesh.update_faces(keep_face)
                    mesh.remove_unreferenced_vertices()
                    log.append(
                        "dropped %d stray islands below %.1f%% of the largest (%d faces removed)"
                        % (int((~keep_lbl).sum()), 100 * min_component_frac, dropped_faces)
                    )
                else:
                    log.append("all %d islands are above the size threshold - none dropped" % n)
            else:
                log.append("single island - nothing to drop")
        except Exception as ex:
            log.append("island filtering skipped: %s" % ex)

    if fill and not mesh.is_watertight:
        try:
            n_before = mesh.euler_number
            mesh.fill_holes()
            log.append("fill_holes ran (euler %d -> %d)" % (n_before, mesh.euler_number))
        except Exception as e:
            log.append("fill_holes failed: %s" % e)

    try:
        trimesh.repair.fix_winding(mesh)
        trimesh.repair.fix_inversion(mesh)
        trimesh.repair.fix_normals(mesh)
        log.append("fixed winding, inversion and normals")
    except Exception as e:
        log.append("normal repair failed: %s" % e)

    return mesh, log


def close_tiny_defects(mesh, rounds=3, verbose=True):
    """Turn an almost-solid back into a solid.

    *** THE DEFECTS THIS CLEANS ARE MINUSCULE AND THEY BLOCK EVERYTHING DOWNSTREAM. ***
    MEASURED on a Poisson reconstruction of a Hunyuan3D figure: **2 non-manifold edges out
    of 3,577,969**, 0.0% by any rounding. `is_watertight` is then False, so `export`
    refuses, `trimesh.boolean` refuses with "Not all meshes are volumes!", and a whole
    print is blocked by two edges.

    Three local operations, repeated until they stop finding anything:
      keep the largest shell        Poisson can shed a stray bubble
      drop faces on an edge with 3+ smallest-area first, because a fin is a sliver and the
                                    real surface is not
      fan every boundary loop       to its own centroid, which closes a loop of any shape -
                                    the boundary of a surface is always a closed curve, so
                                    each boundary edge gains its second face by construction

    Nothing here resamples, so the surface this is handed is the surface it returns, minus
    a few slivers and plus a few fan triangles.
    """
    trimesh = _tm()
    import numpy as np
    log = []
    m = mesh

    def _largest(x):
        parts = x.split(only_watertight=False)
        if len(parts) <= 1:
            return x, 0
        big = max(parts, key=lambda q: len(q.faces))
        return big, len(parts) - 1

    def _overfull_faces(x):
        es = x.edges_sorted
        order = np.lexsort((es[:, 1], es[:, 0]))
        srt = es[order]
        same = np.all(srt[1:] == srt[:-1], axis=1)
        starts = np.r_[0, np.flatnonzero(~same) + 1]
        ends = np.r_[starts[1:], len(srt)]
        bad = []
        for a, b in zip(starts, ends):
            if b - a > 2:
                bad.extend(order[a:b])
        if not bad:
            return np.zeros(0, dtype=np.int64)
        return np.unique(np.array(bad) // 3)

    m, dropped = _largest(m)
    if dropped:
        log.append("dropped %d stray shell(s)" % dropped)

    for _ in range(rounds):
        if m.is_watertight:
            break
        bad = _overfull_faces(m)
        if len(bad):
            keep = np.ones(len(m.faces), dtype=bool)
            keep[bad] = False
            m.update_faces(keep)
            m.remove_unreferenced_vertices()
            log.append("removed %d face(s) on non-manifold edges" % len(bad))
        bi = trimesh.grouping.group_rows(m.edges_sorted, require_count=1)
        if len(bi):
            import networkx as nx
            be = m.edges_sorted[bi]
            g = nx.Graph()
            g.add_edges_from(be)
            comps = list(nx.connected_components(g))
            v = np.asarray(m.vertices, dtype=np.float64)
            f = list(np.asarray(m.faces))
            apex, newv = {}, []
            for k, c in enumerate(comps):
                apex[k] = len(v) + len(newv)
                newv.append(v[list(c)].mean(axis=0))
            v = np.vstack([v, np.array(newv)])
            owner = {n: k for k, c in enumerate(comps) for n in c}
            for a, b in be:
                f.append([a, b, apex[owner[a]]])
            m = trimesh.Trimesh(vertices=v, faces=np.array(f), process=True)
            log.append("fanned %d boundary loop(s) shut" % len(comps))
        m, _d = _largest(m)
    trimesh.repair.fix_winding(m)
    trimesh.repair.fix_normals(m)
    log.append("after cleanup: watertight=%s volume=%s" % (m.is_watertight, m.is_volume))
    return m, log


def repair_poisson(mesh, depth=10, samples_per_node=1.5, verbose=True):
    """Screened Poisson reconstruction - watertight WITHOUT rasterising the surface.

    *** THIS IS THE DEFAULT NOW, AND repair_voxel IS THE FALLBACK. ***

    repair_voxel rasterises to a BINARY occupancy grid and re-extracts, so the 0.5 crossing
    marching cubes solves for always lands exactly halfway between two cell centres. There
    is no sub-voxel information left to place a vertex with: detail finer than the pitch is
    destroyed before the extractor runs, and the result is a staircase whose step size is
    the pitch. Smoothing afterwards cannot invert that - it can only low-pass what was
    already quantised, which turns a staircase into melted wax.

    Poisson fits an implicit surface to the mesh's OWN oriented points, so its accuracy is
    set by the input rather than by a pitch.

    MEASURED on a Hunyuan3D figure at 146.67 mm, as mean distance from the RAW surface:

        repair --method voxel --voxel-res 489, then Taubin 60      0.1500 mm
        repair --method voxel --voxel-res 1202, then Taubin 20     0.0644 mm
        repair --method poisson --poisson-depth 10                 0.0028 mm

    JUDGED at 30M splat samples beside the raw mesh: indistinguishable. Hair strands, lapel
    roll, buttons, pocket flaps and the plinth all survive.

    Depth 10 rather than 12: MEASURED, 12 gives 0.0026 mm - no meaningful difference - and
    costs 30-42 GB of RSS, which OOM-killed a batch. 10 costs a fraction of that.

    Needs pymeshlab. It is optional on purpose: without it every caller falls back to the
    voxel path and still gets a printable solid, just a rougher one.
    """
    trimesh = _tm()
    import numpy
    log = []
    t0 = time.time()
    import pymeshlab as ml
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        src = os.path.join(td, "in.ply")
        mesh.export(src)
        ms = ml.MeshSet()
        ms.load_new_mesh(src)
        ms.generate_surface_reconstruction_screened_poisson(
            depth=int(depth), samplespernode=float(samples_per_node))
        ms.meshing_remove_connected_component_by_face_number(mincomponentsize=2000)
        cm = ms.current_mesh()
        out = trimesh.Trimesh(vertices=cm.vertex_matrix(), faces=cm.face_matrix(),
                              process=True)
    parts = out.split(only_watertight=False)
    if len(parts) > 1:
        out = max(parts, key=lambda q: len(q.faces))
        log.append("kept the largest of %d shells" % len(parts))

    # *** QUANTISE TO float32 BEFORE VALIDATING, BECAUSE GLB WILL DO IT ANYWAY. ***
    # MEASURED and genuinely confusing until traced: this function returned a mesh with
    # watertight=True and 0 non-manifold edges, and to_print then reloaded the GLB it had
    # just written and found 2 non-manifold edges out of 3,577,969. Nothing was wrong with
    # the repair. GLB stores vertex positions as float32; Poisson produces float64; two
    # vertices that were distinct at double precision land on the same float32 and weld,
    # which turns one edge into three-faced.
    #
    # Validating a mesh that is not the mesh that gets saved is a trap the whole tool would
    # keep falling into, so the demotion happens HERE - before the cleanup and before the
    # verdict. What is checked from this point on is what lands on disk.
    out.vertices = numpy.asarray(out.vertices, dtype=numpy.float32).astype(numpy.float64)
    out.merge_vertices()
    out.update_faces(out.nondegenerate_faces())
    out.remove_unreferenced_vertices()
    log.append("screened poisson depth %d -> %d verts / %d faces in %.1fs"
               % (depth, len(out.vertices), len(out.faces), time.time() - t0))
    if not out.is_watertight:
        out, lc = close_tiny_defects(out)
        log += lc
    log.append("watertight=%s  volume=%s" % (out.is_watertight, out.is_volume))
    return out, log


def repair_voxel(mesh, resolution=320, fill_method="orthographic", verbose=True):
    """Destructive but reliable: rasterise the surface into a voxel grid, flood
    the interior, and re-extract with marching cubes. The result is watertight,
    manifold and single-bodied by construction. Costs surface detail roughly
    equal to one voxel (extent / resolution)."""
    trimesh = _tm()
    log = []
    pitch = float(mesh.extents.max()) / float(resolution)
    t0 = time.time()
    vg = mesh.voxelized(pitch=pitch)
    shell = int(vg.filled_count)
    log.append("voxelised at pitch %.6g -> grid %s (%d surface voxels)"
               % (pitch, tuple(int(x) for x in vg.shape), shell))
    try:
        vg = vg.fill(method=fill_method)
    except Exception as e:
        log.append("fill(%s) failed (%s) - falling back to default" % (fill_method, e))
        vg = vg.fill()
    log.append("interior flood fill (%s): %d -> %d voxels solid" % (fill_method, shell, int(vg.filled_count)))
    log.append("  interior membranes and self-intersections are absorbed by the fill")
    out = vg.marching_cubes
    # marching_cubes comes back in voxel index space; put it back in world space
    try:
        out.apply_transform(vg.transform)
    except Exception as e:
        log.append("WARNING could not re-apply voxel transform (%s); scaling by pitch" % e)
        out.apply_scale(pitch)
    out.merge_vertices()
    out.update_faces(out.nondegenerate_faces())
    out.remove_unreferenced_vertices()
    trimesh.repair.fix_winding(out)
    trimesh.repair.fix_normals(out)
    log.append(
        "marching cubes -> %d verts / %d faces in %.1fs" % (len(out.vertices), len(out.faces), time.time() - t0)
    )
    log.append("voxel repair loses detail below ~%.4g model units (one voxel)" % pitch)
    return out, log


# ---------------------------------------------------------------------------
# orientation and scale
# ---------------------------------------------------------------------------


def to_z_up(mesh, source_up):
    """GLB/glTF is Y-up by convention. Slicers and STL are Z-up. Returns the
    axis actually treated as up."""
    np = _np()
    if source_up == "auto":
        # a standing figure is tallest along its up axis
        source_up = "xyz"[int(np.argmax(mesh.extents))]
    if source_up == "y":
        R = np.array(
            [[1, 0, 0, 0], [0, 0, -1, 0], [0, 1, 0, 0], [0, 0, 0, 1]], dtype=np.float64
        )  # +Y -> +Z
        mesh.apply_transform(R)
    elif source_up == "x":
        R = np.array(
            [[0, -1, 0, 0], [1, 0, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]], dtype=np.float64
        )
        mesh.apply_transform(R)
        R2 = np.array([[1, 0, 0, 0], [0, 0, -1, 0], [0, 1, 0, 0], [0, 0, 0, 1]], dtype=np.float64)
        mesh.apply_transform(R2)
    return source_up


def scale_to_height(mesh, height_mm, source_up="auto", center_xy=True, on_plate=True):
    np = _np()
    used_up = to_z_up(mesh, source_up)
    cur = float(mesh.extents[2])
    if cur <= 0:
        raise SystemExit("mesh_doctor: model has zero height after orientation")
    factor = float(height_mm) / cur
    mesh.apply_scale(factor)
    T = np.eye(4)
    if center_xy:
        c = mesh.bounds.mean(axis=0)
        T[0, 3] = -c[0]
        T[1, 3] = -c[1]
    if on_plate:
        T[2, 3] = -mesh.bounds[0][2]
    mesh.apply_transform(T)
    return {
        "source_up_axis": used_up,
        "scale_factor": factor,
        "height_mm": float(mesh.extents[2]),
        "footprint_mm": [float(mesh.extents[0]), float(mesh.extents[1])],
        "bounds_mm_min": [float(x) for x in mesh.bounds[0]],
        "bounds_mm_max": [float(x) for x in mesh.bounds[1]],
        "volume_cm3": float(mesh.volume) / 1000.0 if mesh.is_watertight else None,
        "surface_area_cm2": float(mesh.area) / 100.0,
    }


# ---------------------------------------------------------------------------
# thickness  (shape diameter function)
# ---------------------------------------------------------------------------


def sample_thickness(mesh, n_samples=40000, cone_rays=9, cone_deg=25.0, seed=0):
    """Shape Diameter Function. From each sample point on the surface, fire a
    small cone of rays into the solid along the inward normal and take the
    median distance to the far wall. That distance is the local feature
    thickness - the number that decides whether a hair strand survives a nozzle.

    Returns (thickness_per_sample, sample_points, valid_mask).
    """
    np = _np()
    rng = np.random.default_rng(seed)

    n_samples = min(int(n_samples), max(1000, len(mesh.faces)))
    pts, face_idx = mesh.sample(n_samples, return_index=True)
    nrm = mesh.face_normals[face_idx]

    eps = float(mesh.extents.max()) * 1e-5
    max_d = float(mesh.extents.max()) * 1.5

    # build a cone of directions around -normal
    dirs = [-nrm]
    if cone_rays > 1:
        # an orthonormal frame per sample
        helper = np.tile(np.array([0.0, 0.0, 1.0]), (len(nrm), 1))
        bad = np.abs(nrm[:, 2]) > 0.9
        helper[bad] = np.array([1.0, 0.0, 0.0])
        t1 = np.cross(nrm, helper)
        t1 /= np.linalg.norm(t1, axis=1, keepdims=True) + 1e-12
        t2 = np.cross(nrm, t1)
        half = math.radians(cone_deg)
        for k in range(cone_rays - 1):
            phi = 2.0 * math.pi * k / float(cone_rays - 1)
            theta = half * (0.5 + 0.5 * ((k % 2)))
            d = (
                -nrm * math.cos(theta)
                + t1 * (math.sin(theta) * math.cos(phi))
                + t2 * (math.sin(theta) * math.sin(phi))
            )
            dirs.append(d / (np.linalg.norm(d, axis=1, keepdims=True) + 1e-12))

    origins = pts - nrm * eps
    hits = np.full((len(dirs), len(pts)), np.nan)
    for i, d in enumerate(dirs):
        try:
            loc, ray_i, tri_i = mesh.ray.intersects_location(
                origins, d, multiple_hits=False
            )
        except Exception:
            continue
        if len(ray_i) == 0:
            continue
        dist = np.linalg.norm(loc - origins[ray_i], axis=1)
        # reject grazing hits on a wall facing the same way we are travelling
        far_n = mesh.face_normals[tri_i]
        opposing = np.einsum("ij,ij->i", far_n, d[ray_i]) > 0.05
        ok = opposing & (dist > eps * 5) & (dist < max_d)
        hits[i, ray_i[ok]] = dist[ok]

    import warnings

    with np.errstate(all="ignore"), warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)  # all-NaN columns are expected
        thick = np.nanmedian(hits, axis=0)
    valid = np.isfinite(thick)
    return thick, pts, valid


def thickness_report(mesh, min_mm, n_samples, height_mm=None, source_up="auto", seed=0):
    np = _np()
    scale_note = None

    # A thickness ray finds the first surface it meets. If the mesh carries
    # interior geometry - which is exactly what a large non-manifold edge count
    # means - the ray stops on an internal membrane and reports it as a wall.
    # The result is a wildly pessimistic thickness. Say so loudly rather than
    # quoting a number that describes reconstruction junk.
    hist, n_edges = edge_valence(mesh)
    nonman = sum(c for v, c in hist.items() if v >= 3)
    trust = None
    if not mesh.is_watertight or nonman:
        trust = (
            "UNTRUSTWORTHY - this mesh is not a closed solid (%d boundary edges, "
            "%d non-manifold edges = %.1f%%). Rays stop on interior membranes, so the "
            "numbers below understate real wall thickness, often by several times. "
            "Run `repair` first and re-measure."
            % (hist.get(1, 0), nonman, 100.0 * nonman / n_edges if n_edges else 0.0)
        )

    if height_mm:
        m2 = mesh.copy()
        info = scale_to_height(m2, height_mm, source_up=source_up)
        mesh = m2
        scale_note = "evaluated at a print height of %.1f mm (scale factor %.6g)" % (
            height_mm,
            info["scale_factor"],
        )
    t0 = time.time()
    thick, pts, valid = sample_thickness(mesh, n_samples=n_samples, seed=seed)
    tv = thick[valid]
    pv = pts[valid]
    if len(tv) == 0:
        raise SystemExit("mesh_doctor: no valid thickness samples - the mesh may be open everywhere")
    below = tv < float(min_mm)
    qs = [1, 5, 10, 25, 50, 75, 90, 99]
    out = {
        "samples_requested": int(n_samples),
        "samples_valid": int(valid.sum()),
        "samples_no_far_wall": int((~valid).sum()),
        "min_feature_mm": float(min_mm),
        "fraction_below_min": float(below.mean()),
        "thickness_min": float(tv.min()),
        "thickness_max": float(tv.max()),
        "thickness_mean": float(tv.mean()),
        "percentiles": {str(q): float(np.percentile(tv, q)) for q in qs},
        "seconds": round(time.time() - t0, 2),
        "scale_note": scale_note,
        "trust_warning": trust,
        "input_watertight": bool(mesh.is_watertight),
    }
    if below.any():
        bad = pv[below]
        out["thin_region_bounds"] = {
            "min": [float(x) for x in bad.min(axis=0)],
            "max": [float(x) for x in bad.max(axis=0)],
        }
        # where in Z do the thin bits live - the answer is usually "the hair"
        zs = bad[:, 2]
        lo, hi = float(pv[:, 2].min()), float(pv[:, 2].max())
        span = max(hi - lo, 1e-9)
        deciles = np.clip(((zs - lo) / span * 10).astype(int), 0, 9)
        counts = np.bincount(deciles, minlength=10)
        allz = np.clip(((pv[:, 2] - lo) / span * 10).astype(int), 0, 9)
        totals = np.bincount(allz, minlength=10)
        out["thin_by_height_decile"] = [
            {
                "decile": i,
                "z_from": round(lo + span * i / 10.0, 2),
                "z_to": round(lo + span * (i + 1) / 10.0, 2),
                "thin_frac": float(counts[i] / totals[i]) if totals[i] else 0.0,
            }
            for i in range(10)
        ]
    return out


# ---------------------------------------------------------------------------
# overhang
# ---------------------------------------------------------------------------


def overhang_report(mesh, angle_deg=45.0, source_up="auto", height_mm=None, check_support=True):
    """A face overhangs when its surface tilts more than `angle_deg` away from
    vertical, i.e. its normal points downward by more than that. Everything past
    the threshold needs support material (FDM) or careful orientation.

    Area-weighted, because a million tiny steep faces matter less than one big
    flat ceiling.
    """
    np = _np()
    mesh = mesh.copy()
    if height_mm:
        scale_to_height(mesh, height_mm, source_up=source_up)
    else:
        to_z_up(mesh, source_up)

    n = mesh.face_normals
    area = mesh.area_faces
    total = float(area.sum())
    nz = n[:, 2]  # -1 = surface faces straight down
    zmin, zmax = float(mesh.bounds[0][2]), float(mesh.bounds[1][2])
    span = max(zmax - zmin, 1e-9)
    cz = mesh.triangles_center[:, 2]

    # Faces lying on the build plate face straight down but are supported by the
    # plate itself. Counting them as overhangs is the classic false positive -
    # a model with a flat base would read 25% overhang on its base alone.
    bed_tol = max(0.2, 0.002 * span)
    on_bed = (cz - zmin < bed_tol) & (nz < -0.5)

    thresh = -math.cos(math.radians(angle_deg))  # 45 deg -> -0.7071
    steep = (nz < thresh) & ~on_bed
    near_flat_down = (nz < -0.985) & ~on_bed  # true ceilings / bridges

    dec = np.clip(((cz - zmin) / span * 10).astype(int), 0, 9)

    out = {
        "angle_deg": float(angle_deg),
        "faces": int(len(mesh.faces)),
        "bed_contact_area": float(area[on_bed].sum()),
        "bed_contact_area_fraction": float(area[on_bed].sum() / total) if total else 0.0,
        "bed_tolerance": float(bed_tol),
        "overhang_face_fraction": float(steep.mean()),
        "overhang_area_fraction": float(area[steep].sum() / total) if total else 0.0,
        "overhang_area": float(area[steep].sum()),
        "flat_ceiling_area_fraction": float(area[near_flat_down].sum() / total) if total else 0.0,
        "z_range": [zmin, zmax],
        "by_height_decile": [],
    }
    for i in range(10):
        m = dec == i
        a = float(area[m].sum())
        out["by_height_decile"].append(
            {
                "decile": i,
                "z_from": round(zmin + span * i / 10.0, 2),
                "z_to": round(zmin + span * (i + 1) / 10.0, 2),
                "overhang_area_frac": float(area[m & steep].sum() / a) if a > 0 else 0.0,
            }
        )

    if check_support:
        # for each overhanging face, is there anything directly beneath it?
        # nothing beneath = support has to come all the way up from the plate.
        idx = np.nonzero(steep)[0]
        if len(idx) > 40000:
            sel = np.random.default_rng(0).choice(idx, 40000, replace=False)
        else:
            sel = idx
        if len(sel):
            org = mesh.triangles_center[sel] - np.array([0.0, 0.0, 1e-4 * span])
            dirs = np.tile(np.array([0.0, 0.0, -1.0]), (len(sel), 1))
            try:
                hit = mesh.ray.intersects_any(org, dirs)
                unsupported = ~hit
                out["overhang_sampled"] = int(len(sel))
                out["unsupported_fraction_of_overhangs"] = float(unsupported.mean())
                out["note_support"] = (
                    "%.1f%% of overhanging surface has nothing below it - support "
                    "must be built from the plate." % (100.0 * unsupported.mean())
                )
            except Exception as e:
                out["note_support"] = "support raycast unavailable: %s" % e

    # Will it stay on the plate? Bed contact under ~1.5% of the model's own
    # height squared is the practical danger zone for a tall figure - that is
    # when you add a base rather than argue with the brim settings.
    h = span
    out["bed_contact_vs_height2"] = float(out["bed_contact_area"] / (h * h)) if h else 0.0
    out["needs_base"] = bool(out["bed_contact_vs_height2"] < 0.015)
    return out


# ---------------------------------------------------------------------------
# printing
# ---------------------------------------------------------------------------


def _wrap(text, width=74):
    import textwrap

    return textwrap.wrap(text, width)


def p(label, value, width=34):
    print("  %-*s %s" % (width, label + ":", value))


def print_diagnose(d, fails, warns):
    print("=" * 78)
    print("MESH DOCTOR - DIAGNOSE")
    print("=" * 78)
    print("  %s" % d["path"])
    if d["file_bytes"]:
        p("file size", "%.1f MB" % (d["file_bytes"] / 1e6))
    print("- counts " + "-" * 68)
    p("vertices", "{:,}".format(d["vertices"]))
    p("faces", "{:,}".format(d["faces"]))
    p("unique vertex positions", "{:,}".format(d["unique_vertex_positions"]))
    p("unwelded (duplicate) vertices", "{:,}".format(d["unwelded_vertices"]))
    p("duplicate faces", "{:,}".format(d["duplicate_faces"]))
    p("degenerate (zero-area) faces", "{:,}".format(d["degenerate_faces"]))
    print("- extent " + "-" * 68)
    p("bounds min", "[%.6g, %.6g, %.6g]" % tuple(d["bounds_min"]))
    p("bounds max", "[%.6g, %.6g, %.6g]" % tuple(d["bounds_max"]))
    p("extents (x, y, z)", "[%.6g, %.6g, %.6g]" % tuple(d["extents"]))
    p("centroid", "[%.6g, %.6g, %.6g]" % tuple(d["centroid"]))
    print("- topology " + "-" * 66)
    p("unique edges", "{:,}".format(d["unique_edges"]))
    p("  boundary edges (1 face)", "{:,}".format(d["boundary_edges"]))
    p("  manifold edges (2 faces)", "{:,}".format(d["manifold_edges"]))
    p(
        "  non-manifold edges (3+ faces)",
        "{:,}  ({:.2f}% of edges)".format(d["nonmanifold_edges"], 100 * d["nonmanifold_fraction"]),
    )
    p("edge valence histogram", json.dumps(d["edge_valence"]))
    p("is_watertight", d["is_watertight"])
    p("is_winding_consistent", d["is_winding_consistent"])
    p("is_volume (slicer-ready solid)", d["is_volume"])
    p("euler number", d["euler_number"])
    p("genus", "%.0f" % d["genus"] if d["genus"] is not None else "n/a (only defined when closed)")
    p("islands (vertex-connected)", "{:,}".format(d.get("vertex_components", -1)))
    p("  largest 10 by face count", d.get("vertex_component_face_counts_top10"))
    p("  islands under 1% of largest", d.get("vertex_components_under_1pct"))
    p("face-adjacency components", "{:,}".format(d["components"]))
    print("        (inflated when non-manifold edges exist - trimesh drops those from")
    print("         face adjacency, so one solid can appear as thousands of pieces)")
    print("- volume " + "-" * 68)
    p("volume (signed)", "%.6g" % d["volume"])
    p("normals point outward", d["normals_outward"])
    p("surface area", "%.6g" % d["surface_area"])
    p("convex hull volume", "%.6g" % d["convex_hull_volume"])
    p("solidity (vol / hull vol)", "%.4f" % d["solidity"] if d["solidity"] else "n/a")
    print("- verdict " + "-" * 67)
    if not fails and not warns:
        print("  PRINTABLE - closed, manifold, single solid, normals outward.")
    if fails:
        print("  BLOCKING:")
        for f in fails:
            print("    x %s" % f)
    if warns:
        print("  WARNINGS:")
        for w in warns:
            print("    ! %s" % w)
    if fails:
        print()
        print("  This mesh is NOT sliceable as-is. Run:  mesh_doctor.py repair --method auto")
    print("=" * 78)


# ---------------------------------------------------------------------------
# subcommands
# ---------------------------------------------------------------------------


def cmd_diagnose(args):
    m = load_mesh(args.mesh, process=not args.no_process)
    d = measure(m, args.mesh)
    fails, warns = verdict(d)
    d["blocking"] = fails
    d["warnings"] = warns
    d["printable"] = not fails
    if args.json:
        print(json.dumps(d, indent=2))
    else:
        print_diagnose(d, fails, warns)
    return 0 if not fails else 1


def cmd_repair(args):
    trimesh = _tm()
    m = load_mesh(args.mesh, process=True)
    before = measure(m, args.mesh)
    log = []

    method = args.method
    # auto now means POISSON FIRST. It is both better and cheaper than the voxel path
    # (see repair_poisson), so the only reasons to reach the voxel remesh are a box
    # without pymeshlab, or a mesh Poisson cannot close.
    if method in ("auto", "poisson"):
        try:
            m2, lp = repair_poisson(m, depth=args.poisson_depth)
            if m2.is_watertight:
                m, log = m2, log + ["[poisson] " + x for x in lp]
                method = "done"
            else:
                log.append("[poisson] did not close the surface - falling back")
        except ImportError:
            log.append("[poisson] pymeshlab is not installed - falling back")
        except Exception as e:                                        # noqa: BLE001
            log.append("[poisson] failed (%s) - falling back" % str(e)[:80])
        if method == "poisson" and not m.is_watertight:
            method = "auto"          # an explicit --method poisson still gets a solid
    if method in ("auto", "surface"):
        m, l1 = repair_surface(m, min_component_frac=args.min_component_frac, fill=not args.no_fill)
        log += ["[surface] " + x for x in l1]
    if method == "voxel" or (method == "auto" and not m.is_watertight):
        if method == "auto":
            log.append("[auto] surface repair left the mesh open - falling back to voxel remesh")
        m, l2 = repair_voxel(m, resolution=args.voxel_res, fill_method=args.voxel_fill)
        log += ["[voxel] " + x for x in l2]
        if args.min_component_frac > 0:
            m, l3 = repair_surface(m, min_component_frac=args.min_component_frac, fill=True)
            log += ["[post] " + x for x in l3]

    after = measure(m, None)
    fails, warns = verdict(after)
    size = None
    if args.out:
        size = save_mesh(m, args.out)

    if args.json:
        print(json.dumps({"before": before, "after": after, "log": log, "out": args.out,
                          "out_bytes": size, "blocking": fails, "warnings": warns}, indent=2))
        return 0 if not fails else 1

    print("=" * 78)
    print("MESH DOCTOR - REPAIR (method=%s)" % method)
    print("=" * 78)
    for line in log:
        print("  " + line)
    print("- before / after " + "-" * 60)
    rows = [
        ("vertices", "{:,}", "vertices"),
        ("faces", "{:,}", "faces"),
        ("boundary edges", "{:,}", "boundary_edges"),
        ("non-manifold edges", "{:,}", "nonmanifold_edges"),
        ("islands (vertex-connected)", "{:,}", "vertex_components"),
        ("watertight", "{}", "is_watertight"),
        ("winding consistent", "{}", "is_winding_consistent"),
        ("is_volume", "{}", "is_volume"),
        ("euler", "{}", "euler_number"),
        ("volume", "{:.6g}", "volume"),
    ]
    print("  %-24s %20s %20s" % ("", "BEFORE", "AFTER"))
    for label, fmt, key in rows:
        print("  %-24s %20s %20s" % (label, fmt.format(before[key]), fmt.format(after[key])))
    print("- verdict " + "-" * 67)
    if not fails:
        print("  WATERTIGHT AND SLICEABLE.")
    for f in fails:
        print("    x %s" % f)
    for w in warns:
        print("    ! %s" % w)
    if size:
        print("  wrote %s (%.1f MB)" % (args.out, size / 1e6))
    print("=" * 78)
    return 0 if not fails else 1


def cmd_scale(args):
    m = load_mesh(args.mesh, process=True)
    info = scale_to_height(m, args.height, source_up=args.up,
                           center_xy=not args.no_center, on_plate=not args.no_plate)
    info["is_watertight"] = bool(m.is_watertight)
    size = save_mesh(m, args.out) if args.out else None
    info["out"] = args.out
    info["out_bytes"] = size
    if args.json:
        print(json.dumps(info, indent=2))
        return 0
    print("=" * 78)
    print("MESH DOCTOR - SCALE")
    print("=" * 78)
    p("source up axis", info["source_up_axis"] + "  (rotated to Z-up for slicing)")
    p("scale factor", "%.6g" % info["scale_factor"])
    p("height", "%.2f mm" % info["height_mm"])
    p("footprint (x by y)", "%.2f x %.2f mm" % tuple(info["footprint_mm"]))
    p("bounds min (mm)", "[%.2f, %.2f, %.2f]" % tuple(info["bounds_mm_min"]))
    p("bounds max (mm)", "[%.2f, %.2f, %.2f]" % tuple(info["bounds_mm_max"]))
    p("surface area", "%.1f cm2" % info["surface_area_cm2"])
    p("solid volume", ("%.2f cm3" % info["volume_cm3"]) if info["volume_cm3"] else "n/a (not watertight)")
    if info["volume_cm3"]:
        # rule of thumb: 2 perimeters + 15% infill comes out around 20% of solid
        p("  FDM, 2 walls + 15% infill", "~%.0f g PLA (rule of thumb, ~20%% of solid)"
          % (info["volume_cm3"] * 1.24 * 0.20))
        p("  resin, solid", "~%.0f g" % (info["volume_cm3"] * 1.15))
    if size:
        p("wrote", "%s (%.1f MB)" % (args.out, size / 1e6))
    print("=" * 78)
    return 0


def cmd_thickness(args):
    m = load_mesh(args.mesh, process=True)
    r = thickness_report(m, args.min_mm, args.samples, height_mm=args.height, source_up=args.up, seed=args.seed)
    if args.json:
        print(json.dumps(r, indent=2))
        return 0 if r["fraction_below_min"] < args.fail_over else 1
    print("=" * 78)
    print("MESH DOCTOR - THICKNESS (shape diameter function)")
    print("=" * 78)
    if r["scale_note"]:
        print("  " + r["scale_note"])
    if r.get("trust_warning"):
        print()
        for line in _wrap(r["trust_warning"], 74):
            print("  !! " + line)
        print()
    unit = "mm" if (args.height or args.in_mm) else "model units"
    p("valid samples", "%d of %d" % (r["samples_valid"], r["samples_requested"]))
    p("samples with no far wall", r["samples_no_far_wall"])
    p("minimum feature threshold", "%.2f %s" % (r["min_feature_mm"], unit))
    print("- distribution (%s) " % unit + "-" * 50)
    for q in ["1", "5", "10", "25", "50", "75", "90", "99"]:
        p("  p%s" % q, "%.3f" % r["percentiles"][q])
    p("  min / mean / max", "%.3f / %.3f / %.3f" % (r["thickness_min"], r["thickness_mean"], r["thickness_max"]))
    print("- verdict " + "-" * 67)
    frac = r["fraction_below_min"]
    p("surface below threshold", "%.2f%%" % (100 * frac))
    if frac >= args.fail_over:
        print("  x %.1f%% of the surface is thinner than %.2f %s - those features will not print."
              % (100 * frac, r["min_feature_mm"], unit))
        print("    Fix by: scaling up, thickening the offending parts, or moving to resin.")
    else:
        print("  OK - under the %.0f%% tolerance." % (100 * args.fail_over))
    if "thin_by_height_decile" in r:
        print("- where the thin material is (by height) " + "-" * 34)
        for row in r["thin_by_height_decile"]:
            bar = "#" * int(round(row["thin_frac"] * 40))
            print("  z %8.2f..%-8.2f %5.1f%%  %s" % (row["z_from"], row["z_to"], 100 * row["thin_frac"], bar))
    print("=" * 78)
    return 0 if frac < args.fail_over else 1


def cmd_overhang(args):
    m = load_mesh(args.mesh, process=True)
    r = overhang_report(m, angle_deg=args.angle, source_up=args.up,
                        height_mm=args.height, check_support=not args.no_support_check)
    if args.json:
        print(json.dumps(r, indent=2))
        return 0
    print("=" * 78)
    print("MESH DOCTOR - OVERHANG")
    print("=" * 78)
    p("threshold", "%.0f degrees from vertical" % r["angle_deg"])
    p("faces", "{:,}".format(r["faces"]))
    p("bed contact (on the plate)", "%.1f area units, %.2f%% of surface (excluded from overhangs)"
      % (r["bed_contact_area"], 100 * r["bed_contact_area_fraction"]))
    p("overhanging surface (by area)", "%.2f%%" % (100 * r["overhang_area_fraction"]))
    p("overhanging faces (by count)", "%.2f%%" % (100 * r["overhang_face_fraction"]))
    p("near-horizontal ceilings", "%.2f%% of area (bridging / hard supports)" % (100 * r["flat_ceiling_area_fraction"]))
    if "unsupported_fraction_of_overhangs" in r:
        p("overhangs with nothing below", "%.1f%%" % (100 * r["unsupported_fraction_of_overhangs"]))
    p("bed contact / height squared", "%.4f" % r["bed_contact_vs_height2"])
    if r["needs_base"]:
        print("  ! Bed contact is small for a model this tall. Add a base disc/plinth -")
        print("    a figure standing on two thin soles will snap off the plate mid-print.")
    print("- where the overhangs are (by height) " + "-" * 37)
    for row in r["by_height_decile"]:
        bar = "#" * int(round(row["overhang_area_frac"] * 40))
        print("  z %8.2f..%-8.2f %5.1f%%  %s" % (row["z_from"], row["z_to"], 100 * row["overhang_area_frac"], bar))
    print("=" * 78)
    return 0


def cmd_export(args):
    m = load_mesh(args.mesh, process=True)
    d = measure(m, args.mesh)
    if not d["is_watertight"] and not args.force:
        print("mesh_doctor: refusing to export - mesh is not watertight "
              "(%d boundary edges, %d non-manifold edges)."
              % (d["boundary_edges"], d["nonmanifold_edges"]), file=sys.stderr)
        print("             run `repair` first, or pass --force to export anyway.", file=sys.stderr)
        return 2
    if args.height:
        scale_to_height(m, args.height, source_up=args.up)
    elif args.up != "none":
        to_z_up(m, args.up)

    written = []
    for out in args.out:
        ext = os.path.splitext(out)[1].lower().lstrip(".")
        if ext not in ("stl", "3mf", "obj", "ply", "glb", "gltf", "off"):
            print("mesh_doctor: unsupported output extension .%s" % ext, file=sys.stderr)
            return 2
        size = save_mesh(m, out)
        # re-read to prove the file on disk is still a closed solid
        try:
            rt = load_mesh(out, process=True)
            ok = bool(rt.is_watertight)
            faces = len(rt.faces)
        except Exception as e:
            ok, faces = "reload failed: %s" % e, None
        written.append({"path": out, "bytes": size, "reloaded_watertight": ok, "reloaded_faces": faces})

    if args.json:
        print(json.dumps({"written": written, "height_mm": args.height}, indent=2))
        return 0
    print("=" * 78)
    print("MESH DOCTOR - EXPORT")
    print("=" * 78)
    for w in written:
        p(os.path.basename(w["path"]), "%.1f MB, %s faces, watertight on reload: %s"
          % (w["bytes"] / 1e6, "{:,}".format(w["reloaded_faces"]) if w["reloaded_faces"] else "?",
             w["reloaded_watertight"]))
        print("      %s" % w["path"])
    print("=" * 78)
    return 0


# ---------------------------------------------------------------------------


def build_parser():
    ap = argparse.ArgumentParser(
        prog="mesh_doctor.py",
        description="Diagnose, repair and qualify a generated mesh for 3D printing.",
        epilog="Spec and thresholds: craft/PRINTING.md",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = ap.add_subparsers(dest="cmd", metavar="SUBCOMMAND")
    sub.required = True

    def common(sp):
        sp.add_argument("mesh", help="path to .glb/.gltf/.stl/.obj/.ply/.3mf")
        sp.add_argument("--json", action="store_true", help="machine-readable output")
        return sp

    d = common(sub.add_parser("diagnose", help="full topology and geometry report"))
    d.add_argument("--no-process", action="store_true",
                   help="do not weld/clean on load - shows the file exactly as written")
    d.set_defaults(func=cmd_diagnose)

    r = common(sub.add_parser("repair", help="make the mesh a closed, manifold solid"))
    r.add_argument("--method", choices=["auto", "poisson", "surface", "voxel"],
                   default="auto",
                   help="poisson = screened Poisson, watertight without rasterising, keeps "
                        "the detail (needs pymeshlab). surface = conservative, cannot fix "
                        "non-manifold edges. voxel = rasterise and re-extract, always "
                        "watertight, costs one voxel of detail everywhere. auto = poisson, "
                        "then surface, then voxel (default)")
    r.add_argument("--poisson-depth", type=int, default=10,
                   help="octree depth for the Poisson solve (default 10). 12 measures no "
                        "better and costs 30-42 GB of RSS")
    r.add_argument("--voxel-res", type=int, default=320,
                   help="voxels along the longest axis for the voxel path (default 320)")
    r.add_argument("--voxel-fill", choices=["orthographic", "base", "holes"], default="orthographic",
                   help="interior flood-fill strategy. orthographic fills the most and is the "
                        "default; measured on the Hunyuan3D owl it filled 3.6%% more interior "
                        "than 'base', which matters when the surface leaks")
    r.add_argument("--min-component-frac", type=float, default=0.01,
                   help="drop disconnected shells smaller than this fraction of the largest, "
                        "by face count (default 0.01; 0 disables)")
    r.add_argument("--no-fill", action="store_true", help="skip hole filling")
    r.add_argument("--out", help="write the repaired mesh here (.glb/.stl/.ply/...)")
    r.set_defaults(func=cmd_repair)

    s = common(sub.add_parser("scale", help="orient Z-up and scale to a print height in mm"))
    s.add_argument("--height", type=float, required=True, help="target height in millimetres")
    s.add_argument("--up", choices=["auto", "x", "y", "z"], default="auto",
                   help="which axis is up in the SOURCE file. glTF/GLB is normally y. "
                        "auto picks the longest axis (default)")
    s.add_argument("--no-center", action="store_true", help="do not centre on X/Y")
    s.add_argument("--no-plate", action="store_true", help="do not drop the model onto z=0")
    s.add_argument("--out", help="write the scaled mesh here")
    s.set_defaults(func=cmd_scale)

    t = common(sub.add_parser("thickness", help="feature thickness distribution vs printable minimum"))
    t.add_argument("--min-mm", type=float, default=1.0,
                   help="minimum printable feature (default 1.0; FDM 0.4mm nozzle ~0.8-1.2, resin ~0.3)")
    t.add_argument("--samples", type=int, default=40000, help="surface sample count (default 40000)")
    t.add_argument("--height", type=float,
                   help="evaluate as if printed at this height in mm (scales a copy; does not write)")
    t.add_argument("--up", choices=["auto", "x", "y", "z"], default="auto",
                   help="source up axis, used only with --height")
    t.add_argument("--in-mm", action="store_true",
                   help="the mesh is already in millimetres (label output as mm without rescaling)")
    t.add_argument("--fail-over", type=float, default=0.05,
                   help="exit nonzero if more than this fraction is under the minimum (default 0.05)")
    t.add_argument("--seed", type=int, default=0)
    t.set_defaults(func=cmd_thickness)

    o = common(sub.add_parser("overhang", help="fraction of surface past the overhang angle"))
    o.add_argument("--angle", type=float, default=45.0, help="degrees from vertical (default 45)")
    o.add_argument("--height", type=float, help="evaluate at this print height in mm")
    o.add_argument("--up", choices=["auto", "x", "y", "z"], default="auto", help="source up axis")
    o.add_argument("--no-support-check", action="store_true",
                   help="skip the downward raycast that finds overhangs with nothing beneath them")
    o.set_defaults(func=cmd_overhang)

    e = common(sub.add_parser("export", help="write STL / 3MF, refusing non-watertight input"))
    e.add_argument("--out", action="append", required=True, metavar="PATH",
                   help="output path; repeat for multiple formats (.stl .3mf .obj .ply .glb)")
    e.add_argument("--height", type=float, help="scale to this height in mm before writing")
    e.add_argument("--up", choices=["auto", "x", "y", "z", "none"], default="auto",
                   help="source up axis; 'none' leaves orientation alone")
    e.add_argument("--force", action="store_true", help="export even if the mesh is not watertight")
    e.set_defaults(func=cmd_export)

    return ap


def main(argv=None):
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
