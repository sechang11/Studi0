"""Where was the camera, on every take the studio has already made?

The angle ruler arrived after most of the box's takes were rendered, so the catalog's
`checked` blocks say what the camera DID and are silent about where it stood.  This reads
the first frame of every take in every film and writes the reading onto the take, so the
encyclopedia can carry both.

Pure measurement: no renders, no GPU, and a take that has already been scored is skipped.
"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.expanduser("~/shared/comfy-studio/studio/_tools"))
import anglemeasure as A

ROOT = os.path.expanduser("~/shared/comfy-studio/studio")
FILMS = os.path.join(ROOT, "films")


def backfill(fid, only_picked=False):
    fp = os.path.join(FILMS, fid, "film.json")
    if not os.path.exists(fp):
        return None
    film = json.load(open(fp, encoding="utf-8"))
    done = skipped = 0
    t0 = time.time()
    for sid, sh in sorted(film["shots"].items()):
        for t in sh.get("takes") or []:
            if only_picked and t["id"] != sh.get("picked"):
                continue
            if t.get("angle_measured"):
                skipped += 1
                continue
            v = os.path.join(FILMS, fid, t.get("file") or "")
            if not t.get("file") or not os.path.exists(v):
                continue
            m = A.measure(v)
            t["angle_measured"] = {k: m.get(k) for k in ("pitch", "angle", "confidence", "lines", "inliers")}
            n = A.note(m)
            if n and m.get("confidence") not in (None, "none") and m.get("angle") != "eye level":
                qc = [x for x in (t.get("qc") or []) if not str(x).startswith("angle:")]
                t["qc"] = qc + [n]
            done += 1
    if done:
        json.dump(film, open(fp, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print("%-22s measured %3d, already had %3d  (%.0fs)" % (fid, done, skipped, time.time() - t0), flush=True)
    return {"film": fid, "measured": done, "skipped": skipped}


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    only = "--picked" in sys.argv
    films = args or sorted(d for d in os.listdir(FILMS)
                           if os.path.exists(os.path.join(FILMS, d, "film.json")))
    out = []
    for fid in films:
        try:
            r = backfill(fid, only_picked=only)
            if r:
                out.append(r)
        except Exception as e:
            print("%-22s failed: %s" % (fid, str(e)[:110]), flush=True)
    print("\nfilms: %d | takes measured: %d" % (len(out), sum(r["measured"] for r in out)))
    json.dump(out, open("/tmp/angle_backfill.json", "w"), indent=1)
