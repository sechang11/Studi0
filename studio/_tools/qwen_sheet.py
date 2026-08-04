#!/usr/bin/env python3
"""Render a qwen reference sheet for ONE character card.

    python3 studio/_tools/qwen_sheet.py HALE                  # photographic, style OFF
    python3 studio/_tools/qwen_sheet.py HALE --views 3        # front / three-quarter / profile
    python3 studio/_tools/qwen_sheet.py VIRO --style illustration-1.0-qwen-image.safetensors \
                                             --strength 1.0 --tag illus
    python3 studio/_tools/qwen_sheet.py HALE --dry            # print the prompt, spend nothing

WHY THIS EXISTS

`studio/cast.html`, `studio/compose.py` and `studio/compile.py` all tell the user that the
fix for a missing sheet is `python3 scripts/make_sheets.py`. That command cannot work:
make_sheets.py takes a FILM as a required positional and reads the film's `designs` block,
so run against a bare character card it exits on argparse, and run against a film that has
no designs it exits with "film has no `designs` block - nothing to render". Three places in
the app print an instruction that fails. Nothing on this box renders a sheet for a
character that is not already written into a film.

THE TWO THINGS THIS TOOL EXISTS TO GET RIGHT

1.  THE STYLE SLOT IS EXPLICITLY ZEROED unless you ask for a style.

    Measured 2026-08-03 and again 2026-08-04: a qwen reference sheet carries STYLE as
    forcefully as it carries IDENTITY. `sheet_viro.png` was rendered through workflow 13
    back when node 7 carried the storybook LoRA at 0.8, so the sheet is itself a drawing -
    and every film referencing it came back as a comic illustration in all four cells even
    though the prompt said "waist-up photograph". The reference overrode an explicit
    instruction in the prompt.

    So node 7 is set to 0.0 here by hand rather than trusted to be off, and the output
    filename records what was used. A sheet whose style you cannot read off its own name is
    a trap; that is precisely how the first one got made.

2.  THE SHEET'S STYLE MUST MATCH THE FILM'S TARGET STYLE, which means an illustrated sheet
    is sometimes the RIGHT answer, not a bug. If a film is stylised anyway, render the
    sheet with the same style LoRA the film uses - `--style` is there for that, and the
    B1 arm measured that an illustrated sheet actually locks a face HARDER than a
    photographic one (a drawn face has fewer degrees of freedom). It only misfires when
    the sheet's style and the film's style disagree.

WHAT IT WILL NOT DO

It does not write the character card. Card files are owned elsewhere in this wave and a
sheet filename is a one-line edit; the tool prints the exact line to add. `--write-card`
exists for whoever does own the cards and is off by default.
"""
import argparse, json, os, subprocess, sys, time, uuid

HERE = os.path.dirname(os.path.abspath(__file__))
STUDIO = os.path.dirname(HERE)
ROOT = os.path.dirname(STUDIO)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
os.environ.setdefault("COMFY_HOST", "127.0.0.1:8188")

from comfy import api, set_path                       # noqa: E402
from epic import load_wf, ensure_local, COMFY, HOST   # noqa: E402

T2I = "13_qwen_t2i_styled.json"
CARDS = os.path.join(STUDIO, "characters")
SAMPLES = os.path.join(STUDIO, "samples", "cast")

# Square, and large. A sheet is cropped and re-encoded by every downstream consumer, so it
# is the one image in the pipeline worth rendering above delivery resolution.
SIDE = 1328

# Multi-view sheets. One view is the default because that is what LoadImage feeds
# TextEncodeQwenImageEditPlus as image1, and because the multiple-angles LoRA
# (studio/_tools/turnaround.py) is the better way to get more views once a sheet exists.
VIEWS = [
    "facing the camera directly, neutral expression",
    "turned three-quarters to their left, neutral expression",
    "in profile facing left, neutral expression",
]


def load_card(cid):
    p = os.path.join(CARDS, cid.upper() + ".json")
    if not os.path.isfile(p):
        # case-tolerant, the way compose.py:_card() resolves
        for fn in sorted(os.listdir(CARDS)):
            if fn.lower() == cid.lower() + ".json":
                p = os.path.join(CARDS, fn)
                break
    if not os.path.isfile(p):
        raise SystemExit("no character card for %s (looked in %s)" % (cid, CARDS))
    return p, json.load(open(p))


def describe(card):
    """The subject clause. `prose` is the qwen field; danbooru tags mean nothing to a
    photographic model, so falling back to `tags` is a last resort and says so out loud."""
    prose = (card.get("prose") or "").strip()
    if prose:
        return prose, None
    tags = (card.get("tags") or "").strip()
    if tags:
        return tags, ("%s has no `prose`, so this sheet was built from danbooru `tags`. "
                      "Qwen is a prose model - the sheet will be weaker than it needs to "
                      "be. Add a `prose` field to the card." % card.get("id", "?"))
    raise SystemExit("card has neither `prose` nor `tags` - nothing to draw")


def garment(card):
    """wear_tags[0] is the undamaged rung. A sheet is always the undamaged state: it is
    the identity reference, not a story beat."""
    wt = card.get("wear_tags") or []
    if not wt:
        return None
    w = wt[0].strip()
    if w.lower().startswith("wearing"):
        return w
    # wear_tags are authored as danbooru fragments for the ANIME path ("clean teal soccer
    # jersey, orange trim, number 7"). Spliced raw into a qwen sentence that reads
    # "wearing clean teal soccer jersey" - no article. Qwen is a prose model and the
    # article is free, so add one when the fragment starts with a bare adjective/noun.
    if not w[:2].lower() in ("a ", "an") and not w.lower().startswith("the "):
        w = ("an " if w[0].lower() in "aeiou" else "a ") + w
    return "wearing " + w


def build_prompt(card, nviews, styled=False):
    """The word "photograph" is in this prompt ONLY when the style slot is off.

    It would otherwise fight the very thing the caller asked for: with a style LoRA loaded
    the prompt would be demanding a photograph while the weights pull toward a drawing, and
    the measured behaviour of this stack is that the visual signal wins and the prompt term
    is wasted. Worse, the resulting sheet would then carry a half-committed style into every
    keyframe that references it."""
    subj, warn = describe(card)
    wear = garment(card)
    head = "A character reference sheet of " if styled else \
           "A character reference sheet photograph of "
    bits = [head + subj]
    if wear:
        bits.append(wear)
    if nviews > 1:
        bits.append("the same person shown %d times side by side, %s"
                    % (nviews, ", then ".join(VIEWS[:nviews])))
    else:
        bits.append(VIEWS[0])
    bits += ["even soft lighting", "plain flat neutral grey background",
             "head and shoulders", "sharp focus"]
    return ", ".join(bits) + ".", warn


def wf_sheet(prompt, seed, style, strength, side):
    wf = load_wf(T2I)
    set_path(wf, "10.inputs.text", prompt)
    set_path(wf, "12.inputs.width", side)
    set_path(wf, "12.inputs.height", side)
    set_path(wf, "13.inputs.seed", seed)
    # THE WHOLE POINT. Node 7 is the style slot. It is set every time, to 0.0 when no
    # style was asked for, so a stale default in the workflow file cannot contaminate a
    # sheet the way it contaminated sheet_viro.png.
    if style:
        set_path(wf, "7.inputs.lora_name", style)
    set_path(wf, "7.inputs.strength_model", float(strength if style else 0.0))
    set_path(wf, "15.inputs.filename_prefix", "claude-generated/sheets/qwen")
    return wf


def render(wf, dst, timeout=600):
    resp = api(HOST, "/prompt", {"prompt": wf, "client_id": str(uuid.uuid4()), "front": True})
    if "error" in resp:
        raise SystemExit(json.dumps(resp, indent=2)[:2000])
    pid = resp["prompt_id"]
    t0 = time.time()
    while time.time() - t0 < timeout:
        time.sleep(2.5)
        hist = api(HOST, "/history/%s" % pid)
        if pid not in hist:
            continue
        st = hist[pid].get("status", {})
        if st.get("status_str") == "error":
            for m in st.get("messages", [])[:3]:
                print("   ", str(m)[:250], file=sys.stderr)
            raise SystemExit("render failed")
        if not st.get("completed"):
            continue
        for _n, out in hist[pid].get("outputs", {}).items():
            for f in out.get("images", []):
                rel = ("%s/%s" % (f.get("subfolder", ""), f["filename"])).lstrip("/")
                if ensure_local(rel, dst, required=False):
                    return time.time() - t0
        raise SystemExit("job completed but produced no image")
    raise SystemExit("timed out after %ds" % timeout)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("character")
    ap.add_argument("--views", type=int, default=1, choices=(1, 2, 3))
    ap.add_argument("--seed", type=int, default=990)
    ap.add_argument("--side", type=int, default=SIDE)
    ap.add_argument("--style", default=None, help="style LoRA filename; omit for photographic")
    ap.add_argument("--strength", type=float, default=1.0, help="only used with --style")
    ap.add_argument("--tag", default=None,
                    help="filename tag; defaults to 'photo', or 'styled' when --style is set")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--dry", action="store_true", help="print the prompt and exit")
    ap.add_argument("--write-card", action="store_true",
                    help="also set `sheet` on the character card (off by default: card "
                         "files are owned elsewhere)")
    a = ap.parse_args()

    card_p, card = load_card(a.character)
    cid = str(card.get("id") or os.path.basename(card_p)[:-5])
    prompt, warn = build_prompt(card, a.views, styled=bool(a.style))

    tag = a.tag or ("styled" if a.style else "photo")
    name = "sheet_%s_%s.png" % (tag, cid.lower())
    staged = os.path.join(COMFY, "input", name)
    keep = os.path.join(SAMPLES, cid, "_sheet_%s.png" % tag)

    print("character   %s   (%s)" % (cid, card_p))
    print("style slot  %s" % ("%s @ %.2f" % (a.style, a.strength) if a.style
                              else "OFF (0.0) - photographic"))
    print("output      %s" % staged)
    print("prompt      %s" % prompt)
    if warn:
        print("\nWARNING: %s\n" % warn)
    if a.dry:
        return

    if os.path.exists(staged) and not a.force:
        print("\nalready exists - pass --force to re-render")
    else:
        os.makedirs(os.path.dirname(keep), exist_ok=True)
        el = render(wf_sheet(prompt, a.seed, a.style, a.strength, a.side), keep)
        # ComfyUI's LoadImage reads ONLY from its own input dir, so the sheet has to live
        # there to be referenceable at all. The copy under samples/ is the browsable one.
        subprocess.run(["cp", keep, staged], check=False)
        print("\nrendered in %.1fs -> %s" % (el, staged))
        print("browsable copy  %s" % keep)

    if a.write_card:
        card["sheet"] = name
        with open(card_p, "w") as f:
            json.dump(card, f, indent=2, ensure_ascii=False)
            f.write("\n")
        print("card updated: %s -> sheet = %s" % (card_p, name))
    else:
        print("\nadd this to %s:\n    \"sheet\": \"%s\"" % (card_p, name))
        print("(not written automatically - re-run with --write-card if you own that file)")

    if not a.style:
        print("\nNOTE: this sheet is PHOTOGRAPHIC. A qwen reference sheet imports its style\n"
              "into every keyframe that references it, so use it for a photographic film.\n"
              "For a stylised film, re-render with --style <the film's style LoRA>.")


if __name__ == "__main__":
    main()
