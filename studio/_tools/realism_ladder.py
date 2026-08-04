#!/usr/bin/env python3
"""Realism is a LADDER, not a switch.

    python3 studio/_tools/realism_ladder.py TERRA

"Realistic" is at least three different pictures and this project has been treating it as
one, which is why the first photographic Terra came back as cosplay. There is:

  REAL LIFE       a photograph of a person. An actress in a costume, on a set, on a lens.
                  Skin has pores, fabric has weave, the light comes from somewhere.
  SEMI-REAL       rendered or painted with real anatomy and real light, but not pretending
                  to be a photograph - a 3D animated feature, a painted portrait, a
                  grounded seinen frame. This is where most "realistic anime character"
                  images people actually want live.
  STYLISED        the anime idiom she was drawn in.

The ladder renders the whole spectrum for one character at one seed so a director can point
at the rung they meant instead of arguing about the word.

WHAT THE FIRST ATTEMPT GOT WRONG, and it applies to every rung:
  - it transcribed her anime tags literally, so "gold dress, red cape" returned craft felt
    and upholstery print. Name MATERIAL instead: raw silk, wool, worn leather.
  - it lit her flat and frontal against a grey wall, which is what makes any costume read
    as a costume. Name the LIGHT and where it comes from.
  - "green hair" on a photoreal model returns A WIG. Name it as dyed, with roots and real
    texture.
  - a symmetrical pose with limp arms is a passport photo. Give her weight on one hip.
  Cards carry photo_prose for exactly this, and it is used here as the base for every
  photographic rung.

ENGINE ROUTING. The photographic rungs go to Qwen through the character's PHOTOGRAPHIC
reference sheet - the anime sheet imports its own style and returns illustration no matter
what the prompt says, measured 4 of 4. The stylised rungs go to the illustration engine
with the trained LoRA. The semi-real rungs are rendered BOTH WAYS, because that is exactly
where the two engines overlap and nobody has looked at which one wins.

*** KEEP THE DANBOOU NAME IN THE ANIME PROMPTS. *** Measured, and confirmed by the user on
the full-body sheets: without "terra branford (final fantasy vi)" the LoRA alone returns a
generic green-haired woman. The tag and the weights are complementary.
"""
import argparse, json, os, subprocess, sys

ROOT = os.path.expanduser("~/shared/comfy-studio")
sys.path.insert(0, os.path.join(ROOT, "scripts"))
os.environ.setdefault("COMFY_HOST", "127.0.0.1:8188")

from comfy import run, set_path                      # noqa: E402
from epic import load_wf, ensure_local, HOST         # noqa: E402

SEED = 6120
Q = "masterpiece, best quality, very aesthetic, absurdres"
NEG_A = "1boy, male focus, masculine, multiple girls, lowres, worst quality, bad anatomy, watermark, text"
NEG_Q = "cosplay, costume, wig, plastic, doll, flat lighting, grey backdrop"

SETTING_PROSE = ("standing in a stone hall, a tall window off to camera-left throwing a "
                 "shaft of daylight across the floor, dust in the beam, the depth of the "
                 "room falling into shadow behind her")
SETTING_TAGS = "stone hall, tall window, shaft of light, dust motes, depth of field"

# rung id, label, engine, extra prose or tags
RUNGS = [
    ("1_photo", "1 REAL LIFE  photograph", "qwen",
     "Shot on an 85mm lens at f/2, 35mm colour negative, fine grain, natural skin with "
     "visible pore texture and fine flyaway hair, catchlights in both eyes."),

    ("2_film", "2 REAL LIFE  film still", "qwen",
     "A frame from a feature film. Anamorphic, shallow focal plane, practical light only, "
     "graded warm in the highlights and cool in the shadow, visible grain."),

    ("3_cg", "3 SEMI-REAL  3D animated feature", "qwen",
     "Rendered as a modern 3D animated feature: subsurface scattering in the skin, soft "
     "global illumination, appealing stylised proportion, cloth simulated with real weight."),

    ("4_paint", "4 SEMI-REAL  painted portrait", "qwen",
     "An oil portrait painted from life. Visible brush loading, warm impasto in the "
     "highlights, real anatomy under the paint, canvas tooth showing in the thin passages."),

    ("5_seinen", "5 SEMI-REAL  grounded illustration", "anime",
     "realistic proportions, muted palette, detailed rendering, subtle shading, soft "
     "cel shading, restrained lineart, adult"),

    ("6_anime", "6 STYLISED  her own idiom", "anime",
     "retro artstyle, 1990s (style), cel animation, hard flat shadow"),
]


def sh(*a):
    return subprocess.run(a, capture_output=True, text=True)


def card(cid):
    with open(os.path.join(ROOT, "studio", "characters", cid + ".json"), encoding="utf-8") as f:
        return json.load(f)


def qwen_cell(tag, prose, sheet):
    """Photographic and semi-real rungs, through the character's PHOTOGRAPHIC sheet."""
    wf_name = "14_qwen_edit_ref.json"
    try:
        wf = load_wf(wf_name)
        edit = True
    except Exception:
        wf = load_wf("13_qwen_t2i_styled.json")
        edit = False
    if edit:
        for nid, node in wf.items():
            if isinstance(node, dict) and node.get("class_type") in ("LoadImage",):
                node["inputs"]["image"] = sheet
        for nid, node in wf.items():
            if isinstance(node, dict) and node.get("class_type", "").startswith("TextEncodeQwenImageEdit"):
                node["inputs"]["prompt"] = prose
        for nid, node in wf.items():
            if isinstance(node, dict) and node.get("class_type") == "KSampler":
                node["inputs"]["seed"] = SEED
    else:
        set_path(wf, "10.inputs.text", prose)
        set_path(wf, "11.inputs.text", NEG_Q)
        set_path(wf, "12.inputs.width", 832)
        set_path(wf, "12.inputs.height", 1216)
        set_path(wf, "13.inputs.seed", SEED)
        set_path(wf, "7.inputs.strength_model", 0.0)
    for nid, node in wf.items():
        if isinstance(node, dict) and node.get("class_type") == "SaveImage":
            node["inputs"]["filename_prefix"] = "claude-generated/realism/%s" % tag
    _, outs = run(HOST, wf, quiet=True)
    return outs[0] if outs else None


def anime_cell(tag, tags, lora, st):
    wf = load_wf("22_anime_kf_ipadapter.json")
    set_path(wf, "1.inputs.ckpt_name", "animagine-xl-4.0.safetensors")
    set_path(wf, "4.inputs.weight", 0.0)
    set_path(wf, "5.inputs.text", tags)
    set_path(wf, "6.inputs.text", NEG_A)
    set_path(wf, "8.inputs.seed", SEED)
    for n in ("7", "10"):
        set_path(wf, "%s.inputs.width" % n, 832)
        set_path(wf, "%s.inputs.height" % n, 1216)
    if lora:
        wf["90"] = {"class_type": "LoraLoaderModelOnly",
                    "inputs": {"model": ["1", 0], "lora_name": lora, "strength_model": st}}
        for nid, node in list(wf.items()):
            if nid in ("1", "90") or not isinstance(node, dict):
                continue
            for k, v in (node.get("inputs") or {}).items():
                if isinstance(v, list) and len(v) == 2 and v[0] == "1" and v[1] == 0:
                    node["inputs"][k] = ["90", 0]
    set_path(wf, "11.inputs.filename_prefix", "claude-generated/realism/%s" % tag)
    _, outs = run(HOST, wf, quiet=True)
    return outs[0] if outs else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("character")
    ap.add_argument("--out")
    a = ap.parse_args()

    c = card(a.character)
    lora = c.get("lora")
    st = float(c.get("lora_strength_measured") or 0.5)
    photo = c.get("photo_prose") or c.get("prose") or ""
    sheet = c.get("sheet_photo") or ""
    # The danbooru name is LOAD-BEARING - see the module docstring.
    base_tags = ", ".join(x for x in [c.get("tags", ""), c.get("base_tags", ""),
                                      (c.get("wear_tags") or [""])[0]] if x)

    cells = []
    for rid, label, engine, extra in RUNGS:
        tag = "%s_%s" % (a.character.lower(), rid)
        print("  %-34s %s" % (label, engine), flush=True)
        if engine == "qwen":
            prose = photo + " " + extra + " " + SETTING_PROSE
            rel = qwen_cell(tag, prose, sheet)
        else:
            tags = ", ".join(x for x in [base_tags, extra, SETTING_TAGS, Q] if x)
            rel = anime_cell(tag, tags, lora, st)
        if not rel:
            print("     no output")
            continue
        loc = ensure_local(rel, "/tmp/_rl_%s.png" % tag, required=False)
        if not loc:
            continue
        out = "/tmp/rl_%s.webp" % tag
        sh("ffmpeg", "-y", "-v", "error", "-i", loc, "-vf", "scale=520:-1", "-quality", "86", out)
        cells.append((label, out))

    if not cells:
        raise SystemExit("nothing rendered")
    os.system("rm -rf /tmp/_rlg && mkdir -p /tmp/_rlg")
    for i, (label, p) in enumerate(cells):
        sh("ffmpeg", "-y", "-v", "error", "-i", p, "-vf",
           "scale=500:730,drawtext=text='%s':fontcolor=yellow:fontsize=19:x=6:y=6:"
           "box=1:boxcolor=black@0.85:boxborderw=5" % label.replace(":", "\\:"),
           "/tmp/_rlg/%02d.png" % i)
    dst = a.out or os.path.join(ROOT, "studio", "samples", "cast",
                                "%s_realism_ladder.jpg" % a.character.lower())
    sh("ffmpeg", "-y", "-v", "error", "-pattern_type", "glob", "-i", "/tmp/_rlg/*.png",
       "-filter_complex", "tile=%dx1:margin=6:padding=6:color=0x111111" % len(cells),
       "-frames:v", "1", "-q:v", "3", dst)
    print("\n%s" % dst)


if __name__ == "__main__":
    main()
