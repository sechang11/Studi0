#!/usr/bin/env python3
"""Shot four of Lantern Night: cut the take where the camera left her face.

Five takes of the close-up held Terra's face for about a second and a half and then pulled back
to the street, whatever the words said (a lantern named, a lantern not named, three seconds, the
enhancer off).  The studio's own remedy for a take that goes wrong late is arithmetic on the file:
"cutting is the only remedy the studio owns outright" (_trim_to_face).  That function cuts where
the FACE was lost; here the face was kept and the FRAMING was lost, so the cut is placed by eye
from the frames - 1.5 s, eyes closed, the smile - and the cut take is then measured exactly as a
fresh render would be (QC, camera, angle, identity, scene drift) and picked only if nothing counts
against it.  The report card says what was done.

    python3 studio/_tools/hero_cut_040.py [take_id] [seconds]
"""
import importlib.util
import os
import sys
import time

ROOT = os.path.expanduser("~/shared/comfy-studio")
STUDIO = os.path.join(ROOT, "studio")
for p in (os.path.join(ROOT, "scripts"), os.path.join(STUDIO, "_tools")):
    if p not in sys.path:
        sys.path.insert(0, p)
FID, SID = "lantern-night", "040"
SRC = sys.argv[1] if len(sys.argv) > 1 else "t801635593"
AT = float(sys.argv[2]) if len(sys.argv) > 2 else 1.5


def main():
    spec = importlib.util.spec_from_file_location("film_routes", os.path.join(STUDIO, "_tools", "film_routes.py"))
    fr = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fr)
    F = fr.F
    f = F.load(FID)
    sh = f.shot(SID)
    src_take = next(t for t in sh.get("takes") or [] if t["id"] == SRC)
    src = os.path.join(f.dir, src_take["file"])
    tid = SRC + "c"
    rel = "takes/%s/ltx_%s.mp4" % (SID, tid)
    dest = os.path.join(f.dir, rel)
    fr._sh("ffmpeg", "-y", "-v", "error", "-i", src, "-t", "%.2f" % AT, "-c:v", "libx264", "-crf", "16",
           "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", dest)
    assert os.path.exists(dest), "cut failed"
    fr._thumbs(dest, dest[:-4])
    jid = fr._job("make", film=FID, shot=SID)
    qc = list(fr._qc(dest))
    cam_m, cn = fr._camera_pass(jid, sh, dest, "ltx")
    if cn:
        qc.append(cn)
    angle_m, an = fr._angle_pass(jid, sh, dest)
    if an:
        qc.append(an)
    ident_m, inote, _ifault = fr._identity_pass(jid, f, sh, dest, cam_m)
    if inote:
        qc.append(inote)
    start = fr._resolve_anchor_file(f, SID, jid)
    d = fr._scene_drift(dest, start, "%s_%s_cut" % (FID, SID)) if start else None
    if d and d.get("error"):
        fr._log(jid, "drift check unavailable: %s" % d["error"]); d = None
    dq, dl = fr._drift_verdict(sh, d, ident_m)     # the studio's own decision, one helper
    if dq:
        qc.append(dq)
    if dl:
        fr._log(jid, dl)
    qc.append("the studio cut the take at %.1f s of %.1f, where the camera left her face"
              % (AT, float(src_take.get("duration") or 0)))
    take = {"id": tid, "engine": "ltx", "seed": src_take.get("seed"), "created": time.strftime("%H:%M"),
            "file": rel, "poster": rel[:-4] + ".png", "strip": rel[:-4] + "_strip.png",
            "duration": round(fr._dur(dest), 2), "fps": fr._fps(dest), "qc": qc, "cam_measured": cam_m,
            "identity": ident_m, "angle_measured": angle_m, "drift": d, "warnings": [],
            "prompt": src_take.get("prompt"), "cut_from": SRC}
    for ln in fr.JOBS[jid]["log"]:
        print("   |", ln[:200], flush=True)
    faults = fr._faults(take)
    f2 = F.load(FID)
    sh2 = f2.shot(SID)
    # a re-run replaces the earlier cut of the same take, never duplicates its id
    sh2["takes"] = [t for t in sh2.get("takes") or [] if t["id"] != tid]
    sh2["takes"].append(take)
    if not faults:
        sh2["picked"] = tid
    f2.save()
    print("take %s  duration %.2f  faults=%d" % (tid, take["duration"], len(faults)), flush=True)
    for q in qc:
        print("   qc:", q[:220], flush=True)
    print("PICKED" if not faults else "NOT PICKED", flush=True)


if __name__ == "__main__":
    main()
