#!/usr/bin/env python3
"""probe.py - re-render one beat of MOTION PROOF with an arbitrary motion string.

Two questions the single pass of the film could not answer, both worth a clip:

  1. confetti DREW A PERSON into a keyframe the author wrote as "no humans". n=1 is a
     story; n=3 is a property of the card. Same keyframe, two fresh seeds.

  2. compose.resolve_motion() prefers hold_all when a character is declared and hold_frame
     when nobody is. Both hold_all beats in the film CREPT the framing in (drift 19.3 and
     15.3) while the one hold_frame beat sat at 2.4. Is that the card or the shot? Send
     hold_frame's exact string over the two hold_all keyframes at their own seeds and see.

    python3 studio/samples/motion_proof/probe.py
"""
import json, os, shutil, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
os.environ.setdefault("COMFY_ROOT", os.path.expanduser("~/ComfyUI"))
os.environ.setdefault("COMFY_HOST", "127.0.0.1:8188")
from comfy import set_path                                    # noqa: E402
from epic import load_wf, submit, wait_all, COMFY             # noqa: E402

SLUG, REL = "motion-proof", "claude-generated/12-shorts/motion-proof"
OUT = f"{COMFY}/output/{REL}"
FILM = json.load(open(os.path.join(ROOT, "studio", "movies", "motion-proof.json"),
                      encoding="utf-8"))

CELLS = [
    # (tag, beat index, motion text, seed)
    ("confetti_s2",   0, "Confetti falls through the frame.", 5200),
    ("confetti_s3",   0, "Confetti falls through the frame.", 6200),
    ("holdframe_she", 4, "Nothing in the frame moves.", 4200 + 4 * 13),
    ("holdframe_he",  9, "Nothing in the frame moves.", 4200 + 9 * 13),
]


def main():
    os.makedirs(f"{OUT}/_probe", exist_ok=True)
    pids = []
    for tag, i, text, seed in CELLS:
        b = FILM["beats"][i]
        if os.path.exists(f"{OUT}/_probe/{tag}_00001_.mp4"):
            print("  = %s already rendered" % tag)
            continue
        kf = f"{OUT}/keyframes/{b['id']}_00001_.png"
        staged = f"probe_{tag}.png"
        shutil.copy(kf, f"{COMFY}/input/{staged}")
        wf = load_wf("12_ltx23_i2v_audio.json")
        set_path(wf, "8.inputs.image", staged)
        set_path(wf, "10.inputs.text", text)
        set_path(wf, "20.inputs.width", 1280)
        set_path(wf, "20.inputs.height", 704)
        set_path(wf, "20.inputs.length", 97)
        set_path(wf, "21.inputs.frames_number", 97)
        set_path(wf, "32.inputs.noise_seed", seed)
        set_path(wf, "43.inputs.filename_prefix", f"{REL}/_probe/{tag}")
        print("  > %-14s beat %2d  seed %5d  %r" % (tag, i, seed, text))
        pids.append(submit(wf))
    if pids:
        wait_all(pids, "probe clips")


if __name__ == "__main__":
    main()
