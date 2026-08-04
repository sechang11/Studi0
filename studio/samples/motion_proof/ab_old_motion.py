#!/usr/bin/env python3
"""ab_old_motion.py - re-render chosen beats of MOTION PROOF with the RETIRED constant.

WHY THIS IS A SCRIPT AND NOT A --stage FLAG. scripts/short.py:526 motion_of() now
intercepts "Slow deliberate movement only." and substitutes the measured hold, so a film
carrying the old constant can no longer be rendered through the normal path even on
purpose. That interception is correct - but it also makes the A/B impossible from the
outside, so this reproduces exactly what clips() does and changes ONE input: the string at
node 10 of workflows/12_ltx23_i2v_audio.json.

EVERYTHING ELSE IS HELD: the same keyframe file, the same noise seed (seed0 + i*13 with
seed0=4200, i the beat's index in the film), the same 97-frame length, the same 1280x704.
So a difference between the pair is the motion string and nothing else.

    python3 studio/samples/motion_proof/ab_old_motion.py 0 1 2 6 8 10
"""
import json, os, shutil, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
os.environ.setdefault("COMFY_ROOT", os.path.expanduser("~/ComfyUI"))
os.environ.setdefault("COMFY_HOST", "127.0.0.1:8188")

from comfy import set_path                                    # noqa: E402
from epic import load_wf, submit, wait_all, COMFY             # noqa: E402

OLD = "Slow deliberate movement only."      # the constant compile.py used to assign
FILM = os.path.join(ROOT, "studio", "movies", "motion-proof.json")
SLUG = "motion-proof"
REL = f"claude-generated/12-shorts/{SLUG}"
OUT = f"{COMFY}/output/{REL}"


def main():
    idx = [int(x) for x in sys.argv[1:]] or [0, 2, 8]
    film = json.load(open(FILM, encoding="utf-8"))
    os.makedirs(f"{OUT}/_old", exist_ok=True)
    pids = []
    for i in idx:
        b = film["beats"][i]
        kf = f"{OUT}/keyframes/{b['id']}_00001_.png"
        if not os.path.exists(kf):
            sys.exit(f"no keyframe for beat {i} {b['id']} - run the film first")
        if os.path.exists(f"{OUT}/_old/{b['id']}_00001_.mp4"):
            print(f"  = {b['id']} already rendered")
            continue
        staged = f"oldc_{b['id']}.png"
        shutil.copy(kf, f"{COMFY}/input/{staged}")
        wf = load_wf("12_ltx23_i2v_audio.json")
        set_path(wf, "8.inputs.image", staged)
        set_path(wf, "10.inputs.text", OLD)
        set_path(wf, "20.inputs.width", 1280)
        set_path(wf, "20.inputs.height", 704)
        set_path(wf, "20.inputs.length", 97)
        set_path(wf, "21.inputs.frames_number", 97)
        set_path(wf, "32.inputs.noise_seed", 4200 + i * 13)
        set_path(wf, "43.inputs.filename_prefix", f"{REL}/_old/{b['id']}")
        print(f"  > OLD  beat {i:2d} {b['id']}  seed {4200 + i * 13}")
        print(f"         new was: {b['motion']}")
        pids.append(submit(wf))
    if pids:
        wait_all(pids, "old-constant clips")


if __name__ == "__main__":
    main()
