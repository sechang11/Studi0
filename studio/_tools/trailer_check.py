#!/usr/bin/env python3
"""studio/_tools/trailer_check.py - does the sound land on the picture?

    "what makes them draw attention in? the epic crescendo in the music maybe, the sound
     effects at the right time, the perfect transitions"

Every one of those is a TIMING claim, and this project has never measured timing. It has
instruments for brightness, drift, motion, loudness and vocal intelligibility - all of
which describe a single moment or a whole file, and none of which can see whether the
loudest thing in the mix happens at the same instant as the biggest cut.

WHAT THIS MEASURES, on the delivered file, with no access to the project that made it:

    cuts        where the picture changes hard - frame-to-frame difference spikes above
                the clip's own median + k*MAD, the same robust threshold multishot uses
    peaks       where the sound gets loud - RMS in 50ms windows, peaks picked as local
                maxima that stand clear of the running level
    lag         for every cut, the distance to the nearest audio peak, signed. NEGATIVE
                means the sound arrived first.
    hit rate    the share of cuts with a peak within 120ms. That window is chosen
                because it is roughly the limit at which an audience stops perceiving
                sound and picture as simultaneous.
    climax      where the film is loudest, and whether a cut happens there. A trailer's
                whole shape is a build to one moment; if the loudest instant of the mix
                is not a cut, there is no moment, only a bed.

NO THRESHOLD IS ASSERTED AS A TARGET. A calm product film that never hits anything is not
broken. The number exists so "the sound effects at the right time" stops being a taste
argument and becomes something you can be wrong about.

    python3 studio/_tools/trailer_check.py FILM.mp4
    python3 studio/_tools/trailer_check.py ~/shared/SHORTS-v4/*.mp4 --json out.json
"""
import argparse
import array
import json
import os
import statistics
import subprocess
import sys

SYNC_WINDOW = 0.120     # beyond this, sound and picture stop reading as one event


def sh(*a):
    return subprocess.run(a, capture_output=True, text=True)


def duration(p):
    r = sh("ffprobe", "-v", "error", "-show_entries", "format=duration",
           "-of", "csv=p=0", p)
    try:
        return float((r.stdout or "0").strip())
    except ValueError:
        return 0.0


def envelope(path, hz=8000, win=0.050):
    """RMS per window, straight off decoded mono PCM. No numpy needed."""
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-vn",
                        "-ac", "1", "-ar", str(hz), "-f", "s16le", "-"],
                       capture_output=True)
    pcm = array.array("h")
    pcm.frombytes(r.stdout[:len(r.stdout) // 2 * 2])
    if not len(pcm):
        return [], win
    n = max(1, int(hz * win))
    out = []
    for i in range(0, len(pcm) - n, n):
        s = 0
        for v in pcm[i:i + n]:
            s += v * v
        out.append((s / n) ** 0.5)
    return out, win


def _pct(vals, p):
    """The p-th percentile of vals, p in 0..1. No numpy on the critical path."""
    if not vals:
        return 0.0
    s = sorted(vals)
    return s[min(len(s) - 1, max(0, int(round(p * (len(s) - 1)))))]


def peaks(env, win, top=0.88, gap=0.08):
    """Where something SUDDENLY arrives - an SFX hit, a musical accent, a downbeat.

    Onset strength, not level. "A sound effect at the right time" is about arrival, and
    a mix can be loud for ten seconds without a single event in it.

    The threshold is a PERCENTILE of the file's own onsets. The first version of this
    used median + 2.5*MAD on the level, which on speech - constantly swinging between
    full and silence - put the threshold above the loudest sample in the file and
    reported every mix as having no peaks at all. A percentile cannot do that: some
    fraction of the data is always above it.
    """
    if len(env) < 5:
        return []
    onset = [max(0.0, env[i] - env[i - 1]) for i in range(1, len(env))]
    thr = _pct([o for o in onset if o > 0], top)
    if thr <= 0:
        return []
    out = []
    for i in range(1, len(onset) - 1):
        if onset[i] >= thr and onset[i] >= onset[i - 1] and onset[i] > onset[i + 1]:
            if out and (i - out[-1]) * win < gap:      # one event, not two
                if onset[i] > onset[out[-1]]:
                    out[-1] = i
                continue
            out.append(i)
    return [(i + 1) * win for i in out]


SLICE_RE = None          # set lazily; the cutter names slices NNNN_<beat>_<i>.mp4
ROOT_FILMS = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "films", "shorts")


def true_cut_count(film_path, work_root=None):
    """How many cuts the film REALLY has, from the cutter's own slice files.

    A frame-difference spike is not a cut. Measured against four films whose shot counts
    are known from disk, spike detection scored 3, 17, 33 and 25 against a true 3 every
    time - right once, and wrong by an order of magnitude twice. Motion, a light flare or
    noise in a dark plate all spike.
    """
    import re
    global SLICE_RE
    if SLICE_RE is None:
        SLICE_RE = re.compile(r"^\d{4}_.+_\d+\.mp4$")
    root = work_root or os.path.expanduser(
        "~/ComfyUI/output/claude-generated/12-shorts")
    if not os.path.isdir(root):
        return None
    stem = os.path.splitext(os.path.basename(film_path))[0]
    # The work directory is named from the film's TITLE, not its slug - "hook-door.mp4"
    # renders into "the-door" because its title is THE DOOR. Read it rather than guess:
    # guessing produced `door` and `atlas-pack`, neither of which exists, and both films
    # then fell through to the detector that over-counts by an order of magnitude.
    cands = [stem]
    spec = os.path.join(ROOT_FILMS, stem + ".json")
    if os.path.exists(spec):
        try:
            title = json.load(open(spec, encoding="utf-8")).get("title") or ""
            if title:
                cands.insert(0, title.lower().replace(" ", "-"))
        except Exception:
            pass
    if "-" in stem:
        cands.append("-".join(stem.split("-")[1:]))
    for c in cands:
        d = os.path.join(root, c, "_work")
        if os.path.isdir(d):
            n = len([f for f in os.listdir(d) if SLICE_RE.match(f)])
            if n:
                return max(0, n - 1)
    return None


def cuts(path, fps=12, k=5.0, n_expected=None):
    """Hard picture changes.

    With n_expected, returns the n LARGEST frame-difference spikes - the count comes from
    ground truth and only the timing is inferred. Without it, falls back to a threshold,
    which over-triggers badly on motion and must be treated as an estimate.
    """
    from PIL import Image, ImageChops
    d = "/tmp/_tc_%d" % (abs(hash(path)) % 99999)
    os.makedirs(d, exist_ok=True)
    for f in os.listdir(d):
        os.remove(os.path.join(d, f))
    sh("ffmpeg", "-y", "-v", "error", "-i", path, "-vf",
       "fps=%d,scale=160:-2" % fps, os.path.join(d, "f%05d.png"))
    fs = sorted(os.path.join(d, f) for f in os.listdir(d))
    if len(fs) < 3:
        return []
    diffs = []
    for a, b in zip(fs, fs[1:]):
        ia, ib = Image.open(a).convert("L"), Image.open(b).convert("L")
        px = ImageChops.difference(ia, ib).getdata()
        diffs.append(sum(px) / len(px))
    if n_expected:
        # the n biggest jumps, in time order - count from truth, timing from pixels
        idx = sorted(range(len(diffs)), key=lambda i: -diffs[i])[:int(n_expected)]
        out = [(i + 1) / float(fps) for i in sorted(idx)]
    else:
        med = statistics.median(diffs)
        mad = statistics.median([abs(v - med) for v in diffs]) or 1.0
        thr = med + k * mad
        out = [(i + 1) / float(fps) for i, v in enumerate(diffs) if v > thr]
    for f in fs:
        os.remove(f)
    return out


def check(path):
    dur = duration(path)
    env, win = envelope(path)
    pk = peaks(env, win)
    n_true = true_cut_count(path)
    ct = cuts(path, n_expected=n_true)
    row = {"film": os.path.basename(path), "secs": round(dur, 1),
           "cuts": len(ct), "peaks": len(pk),
           "cuts_from": "the cutter's slice files" if n_true is not None
                        else "ESTIMATED from pixels - over-triggers on motion"}
    if not ct or not pk:
        row["note"] = ("no cuts detected" if not ct else "no audio peaks detected")
        return row
    lags = []
    for c in ct:
        near = min(pk, key=lambda p: abs(p - c))
        lags.append(near - c)
    hits = [l for l in lags if abs(l) <= SYNC_WINDOW]
    row["hit_rate"] = round(len(hits) / len(ct), 3)
    row["median_lag_ms"] = int(round(statistics.median([abs(l) for l in lags]) * 1000))
    # the climax: loudest window, and whether a cut is near it
    loud_i = max(range(len(env)), key=lambda i: env[i])
    loud_t = loud_i * win
    row["climax_s"] = round(loud_t, 2)
    row["climax_at_pct"] = round(100.0 * loud_t / max(dur, 0.01))
    row["climax_on_cut"] = bool(ct and min(abs(c - loud_t) for c in ct) <= SYNC_WINDOW)
    # is there a build at all: last third's mean level against the first third's
    third = max(1, len(env) // 3)
    a, b = env[:third], env[-third:]
    row["build_ratio"] = round((sum(b) / len(b)) / max(sum(a) / len(a), 1e-6), 2)
    return row


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("films", nargs="+")
    ap.add_argument("--json", default="")
    a = ap.parse_args()
    rows = []
    for p in a.films:
        if not os.path.exists(p):
            print("  missing: %s" % p)
            continue
        rows.append(check(p))
        r = rows[-1]
        if "hit_rate" in r:
            print("  %-28s cuts %2d%s peaks %2d  on-beat %3.0f%%  lag %4dms  "
                  "climax %4.1fs (%d%%)%s  build x%.2f"
                  % (r["film"][:28], r["cuts"],
                     "~" if r["cuts_from"].startswith("EST") else " ",
                     r["peaks"], 100 * r["hit_rate"],
                     r["median_lag_ms"], r["climax_s"], r["climax_at_pct"],
                     " ON A CUT" if r["climax_on_cut"] else "", r["build_ratio"]))
        else:
            print("  %-28s %s" % (r["film"][:28], r.get("note")))
    ok = [r for r in rows if "hit_rate" in r]
    if len(ok) > 1:
        n = len(ok)
        print("\n%d films - mean on-beat %.0f%%, median lag %dms, "
              "%d with the climax on a cut, mean build x%.2f"
              % (n, 100 * sum(r["hit_rate"] for r in ok) / n,
                 statistics.median([r["median_lag_ms"] for r in ok]),
                 sum(1 for r in ok if r["climax_on_cut"]),
                 sum(r["build_ratio"] for r in ok) / n))
        print("on-beat = share of cuts with an audio peak within %dms. build = last third"
              " loudness over first third; 1.00 is a flat bed, not a trailer."
              % int(SYNC_WINDOW * 1000))
    if a.json:
        json.dump(rows, open(a.json, "w"), indent=1)
        print("-> %s" % a.json)


if __name__ == "__main__":
    main()
