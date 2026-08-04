#!/usr/bin/env python3
"""Find a photographic reference sheet that looks CAST rather than COSPLAYED.

THE FAILURE THIS EXISTS TO FIX. qwen_sheet.py transcribes a character's anime vocabulary
straight into a photo prompt - "gold dress, red cape, red boots" - and Qwen renders exactly
that: a green wig, a craft-felt cape, upholstery-print fabric and shiny vinyl boots, lit
flat against a grey wall. Technically correct and completely wrong. It is a costume
photographed, not a character.

THE TRANSLATION THAT IS ACTUALLY NEEDED. A photographic sheet is a CASTING decision plus a
COSTUME DEPARTMENT decision. Nobody films a drawing; they build the thing out of real
material and light it. So the prompt has to name:

  MATERIAL   not "gold dress" but what it is made of - raw silk, brocade, wool, waxed
             canvas, worn leather. Material is the single biggest tell between cosplay and
             wardrobe, and it is a noun, which is why it lands.
  LIGHT      not "photorealistic" but where the light is - a window left and behind, deep
             falloff on the shadow side. Flat frontal light is what makes a costume look
             like a costume.
  LENS       85mm at f/2 gives the compression and separation an audience reads as film.
  POSE       weight on one hip, a three-quarter turn. Symmetry with limp arms is a passport
             photo.
  HAIR       "green hair" on a photoreal model returns a wig. Naming it as dyed, with roots
             and real texture, returns hair.

This renders several treatments of one character at one seed and they get LOOKED AT. The
literal transcription is kept as cell 1 so the comparison is honest - if the elaborate
versions are no better, that is the finding.

    python3 studio/_tools/photo_sheet_probe.py TERRA
"""
import argparse, json, os, subprocess, sys

ROOT = os.path.expanduser("~/shared/comfy-studio")
sys.path.insert(0, os.path.join(ROOT, "scripts"))
os.environ.setdefault("COMFY_HOST", "127.0.0.1:8188")

from comfy import run, set_path                      # noqa: E402
from epic import load_wf, ensure_local, HOST         # noqa: E402

SEED = 3311
NEG = "cosplay, costume, wig, plastic, doll, cartoon, anime, illustration, flat lighting"

# id, label, prose. All describe THE SAME PERSON AND THE SAME OUTFIT - only the translation
# from drawing to photograph changes.
TREATMENTS = [
    ("literal", "1 literal transcription (the current sheet)",
     "a waist-up photograph of a young woman with long wavy green hair and a red hair "
     "ribbon, wearing a gold patterned dress, a red cape, a wide red sash and red boots, "
     "standing against a plain grey background"),

    ("material", "2 real materials, window light",
     "an 85mm portrait at f/2 of a young woman in her early twenties, dark green hair worn "
     "loose with a natural wave and visible roots, a narrow oxblood ribbon tied back at the "
     "crown. She wears a heavy raw-silk tabard in faded ochre with a woven red and indigo "
     "border, a soft wool cape in dull carmine pinned at one shoulder, and a wide belt of "
     "worn brown leather. Soft daylight from a tall window camera-left, deep falloff on the "
     "shadow side, warm grey seamless behind her. Weight on one hip, a slight three-quarter "
     "turn, one hand resting at the belt."),

    ("film_still", "3 production still, practical light",
     "a film production still, 85mm at f/2, of a young woman in her early twenties with "
     "dark green hair falling in loose waves past her shoulders, a thin dark red ribbon at "
     "the crown. Heavy ochre raw-silk tunic with a red and indigo woven border, a dull "
     "carmine wool half-cape, worn leather belt, tall scuffed brown leather boots. Standing "
     "in a stone hall lit by a single high window, dust in the shaft of light, shadow "
     "filling the room behind her. Shallow focal plane, grain, natural skin."),

    ("close", "4 close portrait, the face is the sheet",
     "a close portrait, 85mm at f/2, of a young woman in her early twenties. Dark green "
     "hair in loose natural waves, fine flyaway strands catching the light, visible darker "
     "roots. Grey-green eyes, pale skin with real texture and faint freckles across the "
     "nose, no makeup. A narrow oxblood ribbon just visible at the crown, the shoulder of a "
     "carmine wool cape at the bottom of frame. Soft window light from camera-left, catch "
     "light in both eyes, deep shadow on the right side of the face, warm grey behind."),
]


def sh(*a):
    return subprocess.run(a, capture_output=True, text=True)


def cell(tag, prose, w, h):
    wf = load_wf("13_qwen_t2i_styled.json")
    set_path(wf, "10.inputs.text", prose)
    set_path(wf, "11.inputs.text", NEG)
    set_path(wf, "12.inputs.width", w)
    set_path(wf, "12.inputs.height", h)
    set_path(wf, "13.inputs.seed", SEED)
    # Node 7 is the style-LoRA slot and defaults to 0. Keep it off - a style LoRA would
    # pull this off photography, which is the opposite of what a photo sheet needs.
    set_path(wf, "7.inputs.strength_model", 0.0)
    set_path(wf, "15.inputs.filename_prefix", "claude-generated/photo_sheet/%s" % tag)
    _, outs = run(HOST, wf, quiet=True)
    if not outs:
        return None
    loc = ensure_local(outs[0], "/tmp/_ps_%s.png" % tag, required=False)
    if not loc:
        return None
    out = "/tmp/ps_%s.webp" % tag
    sh("ffmpeg", "-y", "-v", "error", "-i", loc, "-vf", "scale=620:-1", "-quality", "86", out)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("character")
    ap.add_argument("--out")
    a = ap.parse_args()

    cells = []
    for tid, label, prose in TREATMENTS:
        w, h = (832, 1216) if tid != "close" else (1024, 1024)
        print("  %-11s %s" % (tid, prose[:78]), flush=True)
        p = cell("%s_%s" % (a.character.lower(), tid), prose, w, h)
        if p:
            cells.append((label, p))

    if not cells:
        raise SystemExit("nothing rendered")
    os.system("rm -rf /tmp/_psg && mkdir -p /tmp/_psg")
    for i, (label, p) in enumerate(cells):
        sh("ffmpeg", "-y", "-v", "error", "-i", p, "-vf",
           "scale=560:820,drawtext=text='%s':fontcolor=yellow:fontsize=20:x=7:y=7:"
           "box=1:boxcolor=black@0.85:boxborderw=5" % label.replace(":", "\\:"),
           "/tmp/_psg/%02d.png" % i)
    dst = a.out or ("/tmp/photo_sheet_%s.jpg" % a.character.lower())
    sh("ffmpeg", "-y", "-v", "error", "-pattern_type", "glob", "-i", "/tmp/_psg/*.png",
       "-filter_complex", "tile=%dx1:margin=6:padding=6:color=0x111111" % len(cells),
       "-frames:v", "1", "-q:v", "3", dst)
    print("\n%s" % dst)
    print("Cell 1 is the current sheet. If 2-4 are not visibly better, say so.")


if __name__ == "__main__":
    main()
