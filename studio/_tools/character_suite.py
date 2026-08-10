#!/usr/bin/env python3
"""Build a new cast member's full picture suite: identity first, presentation second.

    python3 studio/_tools/character_suite.py MARGIT                 # both sets
    python3 studio/_tools/character_suite.py MARGIT --identity      # angles only
    python3 studio/_tools/character_suite.py MARGIT --presentation  # outfits/styles only
    python3 studio/_tools/character_suite.py MARGIT --wear cloak,armour --styles 3

THE SUITE IS TWO SETS, NOT ONE PILE, AND THEY WANT OPPOSITE THINGS.

  IDENTITY SET   angles and expressions of ONE person in ONE outfit under ONE light.
                 Everything that is not the person is held still on purpose. This is what
                 a reference sheet and a character LoRA are built from, and the rule is
                 unforgiving: anything the set varies that is not the person is something
                 the training learns AS the person. Put two outfits in and the coat becomes
                 part of their face. turnaround.py already produces this - 16 views on a
                 flat backdrop - so this tool calls it rather than reinventing it.

  PRESENTATION   outfits, styles, seeds, places. Built AFTER identity is locked, on top of
                 the sheet or the LoRA. This is the part you browse when casting a shot,
                 and it is allowed to vary everything precisely because nothing is training
                 on it.

Doing them in the wrong order is the expensive mistake: a presentation grid built before
identity is locked is a grid of people who merely resemble each other, and it has to be
thrown away when the LoRA lands.

WHAT COMES OUT
    studio/samples/cast/<ID>/identity/       the angle and expression views
    studio/samples/cast/<ID>/presentation/   the wardrobe and style grid
    studio/samples/cast/<ID>/CONTACT_*.jpg   one sheet per set, to judge at a glance
    studio/samples/cast/<ID>/suite.json      what was rendered, and from what
"""
import argparse, glob, json, os, subprocess, sys, time

TOOLS = os.path.dirname(os.path.abspath(__file__))
STUDIO = os.path.dirname(TOOLS)
ROOT = os.path.dirname(STUDIO)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
sys.path.insert(0, STUDIO)
os.environ.setdefault("COMFY_HOST", "127.0.0.1:8188")
from comfy import run, set_path                       # noqa: E402
from epic import load_wf, ensure_local, HOST, COMFY   # noqa: E402

OUT = os.path.join(STUDIO, "samples", "cast")

# Wardrobe is a PRESENTATION axis only. Each entry is garment nouns, because the model
# renders nouns rather than adjectives - "well dressed" produces nothing, "a high-collared
# black coat" produces a coat.
WEAR = {
    "default":   "",
    "travelling": "a heavy hooded travelling cloak over worn leathers, a satchel strap "
                  "across the chest",
    "armour":    "battered steel plate over a padded gambeson, pauldrons, a sword belt",
    "court":     "fine embroidered court dress, a high collar, silver chain at the throat",
    "ruined":    "torn and mud-stained clothing, a bloodied sleeve, hair come loose",
}

STYLES = {
    "house":     "dark fantasy tabletop illustration, painted in gouache and ink, heavy "
                 "shadow, painterly brushwork, muted earth palette",
    "ink":       "stark black ink drawing, heavy hatching, high contrast, no colour",
    "oil":       "classical oil portrait, thick visible brushwork, warm varnish, "
                 "chiaroscuro lighting",
    "storybook": "soft watercolour storybook illustration, gentle line, warm paper texture",
}


def sh(*a):
    return subprocess.run(a, capture_output=True, text=True)


def card(cid):
    p = os.path.join(STUDIO, "characters", "%s.json" % cid)
    if not os.path.isfile(p):
        raise SystemExit("no character card %s" % cid)
    return json.load(open(p, encoding="utf-8"))


def identity(cid, views):
    """Delegate to turnaround.py. It already holds the set still in the ways that matter."""
    d = os.path.join(OUT, cid, "identity")
    os.makedirs(d, exist_ok=True)
    print("  identity set: turnaround, %d views" % views)
    r = subprocess.run([sys.executable, os.path.join(TOOLS, "turnaround.py"), cid,
                        "--views", str(views)], cwd=ROOT, capture_output=True, text=True)
    if r.returncode:
        print("    turnaround failed: %s" % (r.stderr.strip()[-300:] or r.stdout[-300:]))
        return []
    # turnaround writes into its own place; collect whatever it produced for the manifest.
    found = sorted(glob.glob(os.path.join(STUDIO, "samples", "turnaround", cid, "*.png")))
    for f in found:
        dst = os.path.join(d, os.path.basename(f))
        if not os.path.exists(dst):
            sh("cp", f, dst)
    print("    %d views" % len(found))
    return sorted(glob.glob(os.path.join(d, "*.png")))


def presentation(cid, c, wears, styles, seeds):
    """Wardrobe x style x seed, on top of the locked sheet."""
    d = os.path.join(OUT, cid, "presentation")
    os.makedirs(d, exist_ok=True)
    sheet = c.get("sheet")
    if not sheet:
        raise SystemExit("%s has no sheet - build identity first" % cid)
    made = []
    who = (c.get("prose") or c.get("desc") or "").strip()
    for w in wears:
        for s in styles:
            for i in range(seeds):
                tag = "%s__%s__s%d" % (w, s, i + 1)
                dst = os.path.join(d, tag + ".png")
                if os.path.exists(dst):
                    made.append(dst)
                    continue
                wf = load_wf("22_qwen_edit_2511.json")
                set_path(wf, "7.inputs.image", sheet)
                garment = WEAR.get(w) or ""
                # The medium goes in the FIRST sentence - naming it late leaves the model
                # in whatever medium the sheet was in.
                p = ("Redraw this as a %s. Keep the same person: same face, same hair, "
                     "same build.%s Bust portrait, plain dark backdrop."
                     % (STYLES.get(s, s),
                        (" They are wearing %s." % garment) if garment else ""))
                set_path(wf, "10.inputs.prompt", p)
                set_path(wf, "15.inputs.seed", 5000 + i * 137)
                set_path(wf, "17.inputs.filename_prefix",
                         "claude-generated/cast/%s_%s" % (cid.lower(), tag))
                _, outs = run(HOST, wf, quiet=True)
                if outs:
                    ensure_local(outs[0], dst, required=False)
                    made.append(dst)
                    print("    %s" % tag)
                else:
                    print("    %s FAILED" % tag)
    return made


def contact(paths, out, cols=4):
    """One sheet to judge a set at a glance. Cells are forced to a fixed size and the
    layout is explicit pixel offsets - an xstack layout built from w0/h0 expressions can
    only ever address a 2x2 grid, and silently paints later cells over earlier ones."""
    if not paths:
        return None
    cw, ch = 320, 400
    args, fc = [], ""
    for i, p in enumerate(paths[:24]):
        args += ["-i", p]
        lbl = os.path.basename(p)[:-4].replace("_", " ")[:26]
        fc += ("[%d:v]scale=%d:%d:force_original_aspect_ratio=decrease,"
               "pad=%d:%d:(ow-iw)/2:(oh-ih)/2:color=0x111111,"
               "drawtext=text='%s':fontsize=19:fontcolor=white:box=1:"
               "boxcolor=black@0.65:x=8:y=8[c%d];" % (i, cw, ch, cw, ch, lbl, i))
    n = min(len(paths), 24)
    layout = "|".join("%d_%d" % ((i % cols) * cw, (i // cols) * ch) for i in range(n))
    fc += "".join("[c%d]" % i for i in range(n))
    fc += "xstack=inputs=%d:fill=0x111111:layout=%s[v]" % (n, layout)
    r = sh("ffmpeg", "-y", "-v", "error", *args, "-filter_complex", fc,
           "-map", "[v]", "-frames:v", "1", out)
    return out if os.path.exists(out) else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("character")
    ap.add_argument("--identity", action="store_true")
    ap.add_argument("--presentation", action="store_true")
    ap.add_argument("--views", type=int, default=16)
    ap.add_argument("--wear", default="default,travelling,armour,ruined")
    ap.add_argument("--styles", default="house,ink,oil")
    ap.add_argument("--seeds", type=int, default=1)
    a = ap.parse_args()

    cid = a.character.upper()
    c = card(cid)
    both = not (a.identity or a.presentation)
    os.makedirs(os.path.join(OUT, cid), exist_ok=True)
    man = {"character": cid, "built": time.strftime("%Y-%m-%dT%H:%M:%S"),
           "sheet": c.get("sheet"), "identity": [], "presentation": []}
    t0 = time.time()

    if a.identity or both:
        man["identity"] = [os.path.basename(p) for p in identity(cid, a.views)]
        s = contact(sorted(glob.glob(os.path.join(OUT, cid, "identity", "*.png"))),
                    os.path.join(OUT, cid, "CONTACT_identity.jpg"))
        if s:
            print("  %s" % s)

    if a.presentation or both:
        wears = [w.strip() for w in a.wear.split(",") if w.strip()]
        styles = [s.strip() for s in a.styles.split(",") if s.strip()]
        print("  presentation set: %d wear x %d styles x %d seeds"
              % (len(wears), len(styles), a.seeds))
        made = presentation(cid, c, wears, styles, a.seeds)
        man["presentation"] = [os.path.basename(p) for p in made]
        s = contact(made, os.path.join(OUT, cid, "CONTACT_presentation.jpg"))
        if s:
            print("  %s" % s)

    man["seconds"] = round(time.time() - t0, 1)
    man["note"] = ("The identity set holds everything but the person still, because a "
                   "training set learns whatever varies. The presentation set varies "
                   "everything on purpose, because nothing trains on it.")
    with open(os.path.join(OUT, cid, "suite.json"), "w", encoding="utf-8") as f:
        json.dump(man, f, indent=1, ensure_ascii=False)
        f.write("\n")
    print("  %d identity, %d presentation, %.0fs"
          % (len(man["identity"]), len(man["presentation"]), man["seconds"]))


if __name__ == "__main__":
    main()
