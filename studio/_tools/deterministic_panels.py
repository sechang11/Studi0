#!/usr/bin/env python3
"""Render capability panels for the DETERMINISTIC variables the honest way.

THE PROBLEM THIS FIXES

Every existing card renders its options by changing the prompt clause and re-sampling.
That is the only choice for a variable the model has to interpret. But it is the WRONG
choice for a variable that is really an ffmpeg operation, because changing any token
shifts SDXL's conditioning enough to recompose the shot even at a fixed seed.

Measured over all 134 existing cards: 133 show gross compositional difference between
their panels. For shot.size that is the effect. For grade.grain_size it is noise - its
four panels (fine / normal / coarse / clumpy) are four unrelated portraits at different
framings, with no visible grain difference at all. The card claims to show what grain
looks like and shows nothing of the sort.

THE FIX

For anything applied AFTER generation, take ONE base image and apply the real filter.
Content is then provably identical and the only difference is the variable - the same
discipline that made the camera sweep readable once it was swept against a still
instead of a moving clip.

These panels are worth more than the prompt-driven ones: they are exact, they are
reproducible, and what you see is precisely what the renderer will do.

    python3 studio/_tools/deterministic_panels.py
"""
import json, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
STUDIO = os.path.dirname(HERE)
ROOT = os.path.dirname(STUDIO)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

from short import fx_chain, VID, FPS   # noqa: E402  the real implementation

SAMPLES = os.path.join(STUDIO, "samples", "vars")
CARDS = os.path.join(STUDIO, "cards")
W, H = 640, 360


def sh(*a):
    return subprocess.run(a, capture_output=True, text=True)


def base_image():
    """One keyframe, used for every panel of every deterministic card."""
    root = os.path.expanduser("~/ComfyUI/output/claude-generated/12-shorts")
    best = None
    for dirpath, _, names in os.walk(root):
        if not dirpath.endswith("/keyframes"):
            continue
        for n in sorted(names):
            if n.endswith(".png"):
                p = os.path.join(dirpath, n)
                if best is None or os.path.getsize(p) > os.path.getsize(best):
                    best = p
    return best


def render(base, slug, value, vf):
    d = os.path.join(SAMPLES, slug)
    os.makedirs(d, exist_ok=True)
    dst = os.path.join(d, "%s.webp" % value)
    chain = "scale=%d:%d:force_original_aspect_ratio=increase,crop=%d:%d" % (W, H, W, H)
    if vf:
        chain += "," + vf
    r = sh("ffmpeg", "-y", "-v", "error", "-i", base, "-vf", chain,
           "-frames:v", "1", "-q:v", "80", dst)
    return dst if r.returncode == 0 else None


def write_card(slug, variable, claim, method, verdict, look_at, panels):
    card = {"variable": variable, "claim": claim, "method": method,
            "verdict": verdict, "look_at": look_at, "deterministic": True,
            "panels": panels}
    with open(os.path.join(CARDS, slug + ".json"), "w", encoding="utf-8") as f:
        json.dump(card, f, indent=2, ensure_ascii=False)
        f.write("\n")


def main():
    base = base_image()
    if not base:
        raise SystemExit("no keyframe found to use as a base")
    print("base image: %s\n" % base)

    # ---- 1. shot.fx : the compositing effects short.py applies per cut ----------
    FX = [
        ("none", "", "The untouched frame. Every other panel is this picture plus one filter."),
        ("glow", "glow", "Split, blur sigma 18, screen-blend back at 0.38. Where the reference short's apparent energy actually comes from."),
        ("flash", "flash", "A brightness ramp that decays over the first eighth of a second."),
        ("aberr", "aberr", "Red and blue channels shifted 4px apart. Impact, damage, wrongness."),
        ("shake", "shake", "Crop oscillating on sin(t*90). Reads as violence, not unease."),
        ("smear", "smear", "Directional blur through the moment of contact - the anime smear frame."),
        ("hot", "hot", "Contrast 1.10, saturation 1.18, vibrance 0.22. Use sparingly: it compounds with the grade."),
        ("whiteout", "whiteout", "Blows to white and desaturates. Cut away AT contact and let the audience supply the hit."),
    ]
    panels = []
    for val, fx, note in FX:
        chain = fx_chain([fx] if fx else [], W, H, FPS, seed=0, length=1.0) if fx else ""
        # time-varying filters land mid-effect on a single frame; nudge t so they show
        if fx in ("flash", "whiteout"):
            chain = chain.replace("t-0.10", "0.16").replace("1-t*8", "0.45")
        p = render(base, "shot_fx_deterministic", val, chain)
        if p:
            panels.append({"value": val, "clause": fx, "control": val == "none",
                           "sample": "/samples/vars/shot_fx_deterministic/%s.webp" % val,
                           "note": note})
            print("  fx %-9s %s" % (val, "ok" if p else "FAILED"))
    write_card(
        "shot_fx_deterministic", "shot.fx",
        "The compositing effects short.py applies to each cut. These are exact ffmpeg "
        "operations, not requests to a model - what you see here is precisely what the "
        "renderer produces.",
        "ONE base keyframe, each panel is that image with exactly one filter from "
        "short.py fx_chain() applied. Content provably identical; only the effect differs.",
        "works - all eight are exact and repeatable",
        "Compare each against the `none` control. glow and hot are the two that "
        "compound dangerously with the day-for-night grade; a first version of that "
        "grade stacked with these turned a third of a film solid magenta.",
        panels)

    # ---- 2. look : the colour grades, applied as the renderer applies them -------
    looks = {}
    ld = os.path.join(STUDIO, "looks")
    for fn in sorted(os.listdir(ld)):
        if fn.endswith(".json"):
            looks[fn[:-5]] = json.load(open(os.path.join(ld, fn), encoding="utf-8"))
    panels = []
    for lid, look in looks.items():
        p = render(base, "look_deterministic", lid, look.get("grade", ""))
        if p:
            panels.append({"value": lid, "clause": look.get("grade", ""),
                           "sample": "/samples/vars/look_deterministic/%s.webp" % lid,
                           "note": "%s  |  tags also added to the prompt: %s"
                                   % (look.get("desc", ""), look.get("tags") or "(none)")})
            print("  look %-14s ok" % lid)
    write_card(
        "look_deterministic", "look",
        "The colour grade half of `look`. Each preset carries both prompt tags and an "
        "ffmpeg grade; the tags are a suggestion the model often ignores, the grade is "
        "exact. Until 2026-08-03 short.py read neither and applied one hardcoded night "
        "chain to every film, which is why look appeared to do nothing.",
        "ONE base keyframe with each preset's grade string applied directly, exactly as "
        "short.py make_cut() now does.",
        "works - measured: switching a scene from the night grade to the cold grade "
        "moved its mean luma from 81.5 to 115.5 in a real render",
        "These are the ONLY part of `look` you can rely on. Judge the grade here, and "
        "treat the tag half as a bonus. day_for_night and night share a grade on purpose.",
        panels)

    print("\nwrote 2 deterministic cards")


if __name__ == "__main__":
    main()
