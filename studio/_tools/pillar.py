#!/usr/bin/env python3
"""studio/_tools/pillar.py - the occlusion swap, built the way the method says to build it.

The trick everyone posts: someone walks behind a pillar and comes back as a different person,
then a different person again, then the world changes. It is not one clever generation. It is
an EDIT. While the subject is fully hidden the frame holds only pillar and wall, so a cut
placed there is invisible and everything after it can be different.

What makes it read as one continuous take is the thing this repo already measured: H3 keeps
the picture it is given (SSIM 0.95 against the start frame, against LTX's 0.29), so both sides
of a cut can be pinned to the SAME empty frame and the join is seamless by construction.

    frame E   - the colonnade with nobody visible (she is behind the pillar)
    shot 1    - first = Rhea standing in view,   last = E      (she steps out of sight)
    shot 2    - first = E, last = Naia in view                 (someone else steps out)
    shot 3    - first = Naia in view, last = E
    shot 4    - first = E, last = Elin in view
    ...

Cut shot 1 to shot 2 on E and the audience sees one unbroken move behind a pillar.

Every start frame is made by Flux 2 reference conditioning from ONE scene plate plus that
person's hero portrait, so the colonnade is the same colonnade in all of them and only the
person changes. That is the same principle as the film pipeline's composed start frame.

    python3 studio/_tools/pillar.py --plates     # the scene, empty and with each woman
    python3 studio/_tools/pillar.py --shots      # the H3 transitions
    python3 studio/_tools/pillar.py --cut        # assemble, grade, grain
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
COMFY = os.path.expanduser("~/ComfyUI")
COMFY_IN = os.path.join(COMFY, "input")
COMFY_OUT = os.path.join(COMFY, "output")
OUT = os.path.join(ROOT, "studio", "samples", "pillar")

W, H = 1344, 768                      # H3 wants multiples of 32; this is its native 768p class
SECONDS = 3.0

SCENE = ("a wide covered stone colonnade on a bright overcast afternoon, a thick round stone "
         "pillar close to the camera on the right side of the frame, more pillars receding "
         "down the walkway on the left, worn stone floor, a courtyard and green trees visible "
         "beyond the arches, flat soft daylight, no direct sun")

REAL = ("Shot on a phone, handheld, unretouched: visible skin pores and texture, natural skin "
        "tone variation, slight camera shake, faint sensor noise, shallow depth of field. Not "
        "a studio photograph, no retouching, no beauty filter.")

# (key, who or None for the empty plate, what the frame shows)
PLATES = [
    ("empty", None,
     "The walkway is completely empty, nobody is in the frame at all, just the pillar, the "
     "stone floor and the arches."),
    ("rhea", "rhea-sunwoo",
     "She is standing in the middle of the walkway a few steps beyond the near pillar, facing "
     "the camera, weight on one hip, hands at her sides, wearing a long black coat over a "
     "black jumper and dark trousers."),
    ("naia", "naia-ferreira",
     "She is standing in the middle of the walkway a few steps beyond the near pillar, facing "
     "the camera, weight on one hip, hands at her sides, wearing a long camel coat over a "
     "white shirt and dark trousers."),
    ("elin", "elin-dahlqvist",
     "She is standing in the middle of the walkway a few steps beyond the near pillar, facing "
     "the camera, weight on one hip, hands at her sides, wearing a long grey wool coat over an "
     "oatmeal jumper and dark trousers."),
]

# (name, first frame, last frame, what happens) - every shot begins or ends on the empty plate,
# which is where the cuts go.
SHOTS = [
    ("01_rhea_out", "rhea", "empty",
     "the woman walks to her right and passes behind the near stone pillar, leaving the walkway "
     "empty; the camera holds still"),
    ("02_naia_in", "empty", "naia",
     "a woman steps out from behind the near stone pillar into the empty walkway and stops, "
     "facing the camera; the camera holds still"),
    ("03_naia_out", "naia", "empty",
     "the woman walks to her right and passes behind the near stone pillar, leaving the walkway "
     "empty; the camera holds still"),
    ("04_elin_in", "empty", "elin",
     "a woman steps out from behind the near stone pillar into the empty walkway and stops, "
     "facing the camera; the camera holds still"),
]

SCENE_WF = "workflows/26_flux2_t2i.json"
REF_WF = "workflows/68_flux2_ref.json"
H3_WF = "workflows/65_minimax_h3_fl_turbo_v4.json"


def sh(*a, **kw):
    return subprocess.run(a, capture_output=True, text=True, **kw)


def run_wf(wf, sets, want="png", label=""):
    cmd = [sys.executable, os.path.join(ROOT, "scripts", "comfy.py"), "run", os.path.join(ROOT, wf)]
    for k, v in sets:
        cmd += ["-s", "%s=%s" % (k, v)]
    t0 = time.time()
    r = sh(*cmd, cwd=ROOT)
    m = re.search(r"-> (\S+\.%s)" % want, r.stdout or "")
    if not m:
        print("      FAILED %s: %s" % (label, ((r.stderr or r.stdout or "").strip()[-300:])))
        return None, time.time() - t0
    return os.path.join(COMFY_OUT, m.group(1)), time.time() - t0


def h3_length(seconds, fps=24):
    n = max(0, (int(seconds * fps) - 5) // 17)
    return int(17 * n + 5)


def plates(seed=5150):
    os.makedirs(OUT, exist_ok=True)
    base = os.path.join(OUT, "plate_empty.png")
    if not os.path.exists(base):
        p = "%s %s %s" % (SCENE, PLATES[0][2], REAL)
        src, secs = run_wf(SCENE_WF, [
            ("6.inputs.text", p), ("9.inputs.width", W), ("9.inputs.height", H),
            ("12.inputs.width", W), ("12.inputs.height", H), ("11.inputs.noise_seed", seed),
            ("15.inputs.filename_prefix", "claude-generated/pillar/empty")], label="empty")
        if not src:
            return
        shutil.copy(src, base)
        print("  plate empty        %5.1fs" % secs)
    shutil.copy(base, os.path.join(COMFY_IN, "pillar_scene.png"))

    for key, who, what in PLATES[1:]:
        dest = os.path.join(OUT, "plate_%s.png" % key)
        if os.path.exists(dest):
            print("  plate %-12s exists" % key)
            continue
        hero = os.path.join(COMFY_IN, "agency_%s_hero.png" % who)
        if not os.path.exists(hero):
            print("  plate %s: hero missing (%s)" % (key, hero))
            continue
        # reference 1 is the SCENE (it also sets the canvas), reference 2 is the face
        p = ("Use the colonnade from the first reference image exactly as it is, unchanged - "
             "same pillar, same floor, same arches, same light. Add the woman from the second "
             "reference image into it, keeping her face, bone structure and hair exactly. %s %s"
             % (what, REAL))
        src, secs = run_wf(REF_WF, [
            ("42.inputs.image", "pillar_scene.png"),
            ("46.inputs.image", "agency_%s_hero.png" % who),
            ("sg1_6.inputs.text", p), ("sg1_25.inputs.noise_seed", seed + 11),
            ("sg1_95.inputs.value", "true"),
            ("9.inputs.filename_prefix", "claude-generated/pillar/%s" % key)], label=key)
        if not src:
            continue
        shutil.copy(src, dest)
        shutil.copy(src, os.path.join(COMFY_IN, "pillar_%s.png" % key))
        print("  plate %-12s %5.1fs" % (key, secs))
    for key, _, _ in PLATES:
        p = os.path.join(OUT, "plate_%s.png" % key)
        if os.path.exists(p):
            shutil.copy(p, os.path.join(COMFY_IN, "pillar_%s.png" % key))


def shots(seed=909):
    os.makedirs(OUT, exist_ok=True)
    length = h3_length(SECONDS)
    for name, first, last, what in SHOTS:
        dest = os.path.join(OUT, "%s.mp4" % name)
        if os.path.exists(dest):
            print("  shot %-14s exists" % name)
            continue
        f1, f2 = "pillar_%s.png" % first, "pillar_%s.png" % last
        for f in (f1, f2):
            if not os.path.exists(os.path.join(COMFY_IN, f)):
                print("  shot %s: missing %s" % (name, f))
                break
        else:
            prompt = ("%s. %s. Sound: quiet footsteps on stone and a faint courtyard ambience."
                      % (what, SCENE))
            src, secs = run_wf(H3_WF, [
                ("8.inputs.image", f1), ("9.inputs.image", f2),
                ("20.inputs.prompt", prompt), ("20.inputs.width", W), ("20.inputs.height", H),
                ("20.inputs.length", length), ("33.inputs.noise_seed", seed),
                ("51.inputs.filename_prefix", "claude-generated/pillar/%s" % name)],
                want="mp4", label=name)
            if src:
                shutil.copy(src, dest)
                print("  shot %-14s %5.1fs  %s -> %s" % (name, secs, first, last))


def _frames(mp4, work):
    """explode a clip to pngs, return the sorted list"""
    shutil.rmtree(work, ignore_errors=True)
    os.makedirs(work, exist_ok=True)
    sh("ffmpeg", "-y", "-v", "error", "-i", mp4, os.path.join(work, "f%04d.png"))
    return sorted(os.path.join(work, f) for f in os.listdir(work) if f.endswith(".png"))


def _emptiest(frames, plate, lo, hi):
    """index of the frame least different from the empty plate, searched in [lo, hi)"""
    from PIL import Image, ImageChops, ImageStat
    ref = Image.open(plate).convert("RGB")
    best, best_d = lo, None
    for i in range(max(0, lo), min(len(frames), hi)):
        im = Image.open(frames[i]).convert("RGB").resize(ref.size)
        d = sum(ImageStat.Stat(ImageChops.difference(im, ref)).mean) / 3.0
        if best_d is None or d < best_d:
            best, best_d = i, d
    return best, best_d


def cut(grain=True):
    """Join the shots, cutting each one on the frame where the walkway is emptiest.

    A shot that ENDS on the empty plate is trimmed to that frame; a shot that BEGINS on it is
    trimmed from that frame. The search is confined to the half of the clip where the empty
    frame must be, so a static opening cannot win by accident."""
    plate = os.path.join(OUT, "plate_empty.png")
    if not os.path.exists(plate):
        print("  no empty plate")
        return
    pieces = []
    for name, first, last, _ in SHOTS:
        mp4 = os.path.join(OUT, "%s.mp4" % name)
        if not os.path.exists(mp4):
            continue
        work = os.path.join(OUT, "_frames_%s" % name)
        fr = _frames(mp4, work)
        if not fr:
            continue
        n = len(fr)
        if last == "empty":                      # she leaves: keep the head, cut where she's gone
            i, d = _emptiest(fr, plate, n // 2, n)
            keep = fr[:i + 1]
            print("  %-14s %3d frames -> keep 0..%d   (emptiest diff %.2f)" % (name, n, i, d))
        else:                                    # she arrives: drop the head up to the empty frame
            i, d = _emptiest(fr, plate, 0, max(1, n // 2))
            keep = fr[i:]
            print("  %-14s %3d frames -> keep %d..end (emptiest diff %.2f)" % (name, n, i, d))
        seq = os.path.join(OUT, "_seq_%s" % name)
        shutil.rmtree(seq, ignore_errors=True)
        os.makedirs(seq, exist_ok=True)
        for k, f in enumerate(keep):
            shutil.copy(f, os.path.join(seq, "f%04d.png" % k))
        part = os.path.join(OUT, "_part_%s.mp4" % name)
        sh("ffmpeg", "-y", "-v", "error", "-framerate", "24", "-i",
           os.path.join(seq, "f%04d.png"), "-c:v", "libx264", "-crf", "14",
           "-pix_fmt", "yuv420p", part)
        pieces.append(part)
        shutil.rmtree(work, ignore_errors=True)
        shutil.rmtree(seq, ignore_errors=True)
    if not pieces:
        print("  nothing to cut")
        return
    lst = os.path.join(OUT, "_concat.txt")
    with open(lst, "w") as f:
        for c in pieces:
            f.write("file '%s'\n" % c)
    joined = os.path.join(OUT, "_joined.mp4")
    sh("ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", lst,
       "-c:v", "libx264", "-crf", "15", "-pix_fmt", "yuv420p", joined)
    final = os.path.join(OUT, "pillar.mp4")
    # A handheld float and grain: a locked-off, grainless frame reads synthetic, which is the
    # playbook's own rule for photoreal shots. The move is tiny and arithmetic, so it cannot drift.
    vf = ("crop=iw-24:ih-24:12+6*sin(2*PI*t/7):12+5*sin(2*PI*t/5+1),"
          "eq=saturation=1.03:contrast=1.02,noise=alls=5:allf=t+u,unsharp=5:5:0.25"
          ) if grain else "null"
    sh("ffmpeg", "-y", "-v", "error", "-i", joined, "-vf", vf,
       "-c:v", "libx264", "-crf", "16", "-pix_fmt", "yuv420p", final)
    r = sh("ffprobe", "-v", "error", "-select_streams", "v:0", "-count_frames",
           "-show_entries", "stream=width,height,nb_read_frames", "-of", "csv=p=0", final)
    print("  %d shots -> %s  (%s)" % (len(pieces), final, (r.stdout or "").strip()))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plates", action="store_true")
    ap.add_argument("--shots", action="store_true")
    ap.add_argument("--cut", action="store_true")
    ap.add_argument("--seed", type=int, default=5150)
    a = ap.parse_args()
    if a.plates:
        plates(a.seed)
    if a.shots:
        shots()
    if a.cut:
        cut()
    if not (a.plates or a.shots or a.cut):
        ap.print_help()


if __name__ == "__main__":
    main()
