#!/usr/bin/env python3
"""Generate character reference sheets into ComfyUI/input/ so films can lock faces to them.

    python3 scripts/make_sheets.py films/derby.json

A sheet is a single clean portrait rendered ONCE. Every keyframe in a film then runs through
14_qwen_edit_ref.json with the sheet as a reference image, which is what keeps a character's
face identical across a whole production. Sheets live in ComfyUI/input/ (not the output
tree) because LoadImage only reads from there.

Sheets are deliberately plain: neutral pose, even light, plain background. A sheet with
dramatic lighting or a strong angle bakes that into every shot that references it.
"""
import argparse, glob, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.environ.setdefault("COMFY_ROOT", os.path.expanduser("~/ComfyUI"))
# Default to the LOCAL ComfyUI. This used to hardcode 192.168.1.46, which broke
# when DHCP moved the box to .45, and which also sent every render request across
# a NIC measured dropping 10% of packets. Nothing here needs the network: these
# scripts run ON the box. Set COMFY_HOST to drive a remote instance.
os.environ.setdefault("COMFY_HOST", "127.0.0.1:8188")
from comfy import run, set_path                       # noqa: E402
from epic import load_wf, COMFY, HOST, ensure_local   # noqa: E402

SHEET = (1328, 1328)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("film")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--seed", type=int, default=770011)
    a = ap.parse_args()

    film = json.load(open(a.film, encoding="utf-8"))
    style = film.get("style", "")
    lora = film.get("style_lora")
    designs = film.get("designs") or {}
    if not designs:
        raise SystemExit("film has no `designs` block - nothing to render")

    for i, (key, desc) in enumerate(designs.items()):
        name = film["sheets"][key]
        dest = f"{COMFY}/input/{name}"
        if os.path.exists(dest) and not a.force:
            print(f"  = {name} (exists)")
            continue
        wf = load_wf("13_qwen_t2i_styled.json")
        if lora:
            set_path(wf, "7.inputs.lora_name", lora)
            set_path(wf, "7.inputs.strength_model", float(film.get("style_strength", 0.0)))
        set_path(wf, "10.inputs.text",
                 f"character reference sheet, single character, {desc}, "
                 f"neutral expression, facing camera, even soft lighting, "
                 f"plain flat grey background, full head and shoulders, {style}")
        set_path(wf, "12.inputs.width", SHEET[0])
        set_path(wf, "12.inputs.height", SHEET[1])
        set_path(wf, "13.inputs.seed", a.seed + i * 13)
        set_path(wf, "15.inputs.filename_prefix", f"claude-generated/sheets/{key}")
        print(f"  > {name}", flush=True)
        # Clear both sides first. ComfyUI derives its _0000N_ counter from what is already
        # in the output directory, so a stale file there makes the new render land on
        # _00002_ while we fetch _00001_; and ensure_local short-circuits when the
        # destination exists, so --force would otherwise regenerate and change nothing.
        for stale in glob.glob(f"{COMFY}/output/claude-generated/sheets/{key}_*.png"):
            os.remove(stale)
        if os.path.exists(dest):
            os.remove(dest)
        run(HOST, wf, quiet=True)
        # Fetch over /view rather than reading the SMB share, which lags the API.
        ensure_local(f"claude-generated/sheets/{key}_00001_.png", dest, required=True)
        print(f"    -> {dest}")

    print("\nsheets ready. Referenced by name from the film's `sheets` block.")


if __name__ == "__main__":
    main()
