#!/usr/bin/env python3
"""Grow a gallery of generations, each carrying the exact recipe that made it.

    python3 studio/_tools/gallery_gen.py --vary look            # every look, every template
    python3 studio/_tools/gallery_gen.py --vary emotion --template sports_climax
    python3 studio/_tools/gallery_gen.py --vary all --loop      # idle-time corpus builder

THE POINT

A picture on its own teaches nothing you can act on. A picture next to the variable that
produced it, with every other variable held still, teaches you exactly what that knob
does - and if it comes with its full recipe you can reproduce it, change one thing, and
see what happened.

So every generation writes a record to studio/gallery/manifest.jsonl containing the
template, the ONE variable being demonstrated, the complete resolved variable set, the
literal positive and negative prompt, the seed, the model, the sampler settings and the
grade. Nothing about a picture in this gallery is a mystery.

HOLD EVERYTHING ELSE STILL

Within one template, the subject and the seed never change - only the varied value does.
That is the whole reason the images are comparable. This project has now made the
opposite mistake twice: 133 of 134 capability cards vary composition between options
because changing any clause re-rolls SDXL's conditioning, and the first camera sweep was
useless because it swept a clip whose own content changed more than the camera did.

RESUMABLE AND IDEMPOTENT

Every record has a deterministic id, and an id already in the manifest is skipped. Kill it
at any point and re-run; it picks up where it stopped. --loop keeps cycling so the GPU has
something to do whenever nothing else is queued.
"""
import argparse, json, os, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
STUDIO = os.path.dirname(HERE)
ROOT = os.path.dirname(STUDIO)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
os.environ.setdefault("COMFY_HOST", "127.0.0.1:8188")

from comfy import run, set_path                       # noqa: E402
from epic import load_wf, ensure_local, HOST          # noqa: E402

GAL = os.path.join(STUDIO, "gallery")
IMG = os.path.join(STUDIO, "samples", "gallery")
MANIFEST = os.path.join(GAL, "manifest.jsonl")

SEED = 7311
CKPT = "animagine-xl-4.0.safetensors"
WF = "22_anime_kf_ipadapter.json"
STEPS, CFG, SAMPLER = 28, 5.0, "euler_ancestral"
SIZE = (1344, 768)
Q = "masterpiece, best quality, very aesthetic, absurdres"
NEG = ("lowres, worst quality, bad anatomy, bad hands, watermark, text, "
       "multiple views, photorealistic, 3d, western comic, blurry")
SUBJ = ("1boy, solo, male focus, dark red hair, undercut, yellow eyes, "
        "black soccer jersey, silver trim, number 9")
PEOPLELESS = {"establish", "insert", "pillow"}

# Which library each varyable variable draws its values from.
VARIES = {"look": "looks", "emotion": "emotions",
          "lighting": "lighting", "weather": "weather"}


def sh(*a):
    return subprocess.run(a, capture_output=True, text=True)


def load_dir(name):
    d = os.path.join(STUDIO, name)
    out = {}
    if os.path.isdir(d):
        for fn in sorted(os.listdir(d)):
            if fn.endswith(".json"):
                try:
                    out[fn[:-5]] = json.load(open(os.path.join(d, fn), encoding="utf-8"))
                except Exception:
                    pass
    return out


def seen_ids():
    if not os.path.exists(MANIFEST):
        return set()
    s = set()
    with open(MANIFEST, encoding="utf-8") as f:
        for line in f:
            try:
                s.add(json.loads(line)["id"])
            except Exception:
                pass
    return s


def build_prompt(shot, sets, libs, vary_key, vary_val):
    """Assemble tags in the SAME ORDER the compiler uses.

    identity -> face -> action -> world. Order is load-bearing: an earlier, more specific
    tag wins when two conflict, which is why the garment lives in the character's wear
    tags and why the action sits before the place.
    """
    resolved = dict(sets)
    resolved[vary_key] = vary_val
    look = libs["looks"].get(resolved.get("look", "neutral"), {})
    emo = libs["emotions"].get(resolved.get("emotion", ""), {})
    lit = libs["lighting"].get(resolved.get("lighting", ""), {})
    wea = libs["weather"].get(resolved.get("weather", ""), {})

    peopleless = shot.get("template") in PEOPLELESS
    bits = [] if peopleless else [SUBJ]
    if emo and not peopleless:
        bits += [emo.get("face", ""), emo.get("eyes", ""), emo.get("mouth", "")]
    bits += [(shot.get("desc") or "").strip(),
             resolved.get("place", ""),
             lit.get("tags", ""), wea.get("tags", ""), look.get("tags", ""),
             "modern sports anime, cel shading, cinematic", Q]
    return ", ".join(x for x in bits if x), resolved, look


def generate(tpl_id, tpl, shot_i, vary_key, vary_val, libs, dry=False):
    shot = tpl["shots"][shot_i]
    prompt, resolved, look = build_prompt(shot, tpl.get("sets", {}), libs, vary_key, vary_val)
    rid = f"{tpl_id}__{vary_key}-{vary_val}__s{shot_i}"
    if dry:
        print("  would generate", rid)
        return None

    wf = load_wf(WF)
    set_path(wf, "1.inputs.ckpt_name", CKPT)
    set_path(wf, "4.inputs.weight", 0.0)
    set_path(wf, "5.inputs.text", prompt)
    set_path(wf, "8.inputs.seed", SEED)
    set_path(wf, "7.inputs.width", SIZE[0])
    set_path(wf, "7.inputs.height", SIZE[1])
    set_path(wf, "10.inputs.width", SIZE[0])
    set_path(wf, "10.inputs.height", SIZE[1])
    set_path(wf, "11.inputs.filename_prefix", f"claude-generated/studio_gallery/{rid}")
    _, outs = run(HOST, wf, quiet=True)
    if not outs:
        return None
    local = ensure_local(outs[0], f"/tmp/_gal_{rid}.png", required=False)
    if not local:
        return None

    os.makedirs(IMG, exist_ok=True)
    grade = look.get("grade") or "eq=contrast=1.06:saturation=1.12"
    dst = os.path.join(IMG, rid + ".webp")
    # Graded, because the grade is part of what the settings produce - showing the
    # ungraded keyframe would misrepresent every look in the library.
    sh("ffmpeg", "-y", "-v", "error", "-i", local, "-vf", f"{grade},scale=760:-1",
       "-quality", "80", dst)
    try:
        os.remove(local)
    except OSError:
        pass
    if not os.path.exists(dst):
        return None

    # MEASURE THE RESULT, do not assume it.
    #
    # The look grades were validated as valid ffmpeg against testsrc2 - a bright synthetic
    # pattern. That proves a chain PARSES, not that it produces a usable picture. Applied
    # to a night scene, bleach_bypass (contrast 1.30, gamma 0.95) crushed the subject to a
    # near-black silhouette while still being perfectly valid ffmpeg.
    #
    # So every generation records its own mean luma and saturation, and flags itself when
    # it lands outside a readable range. That makes the corpus self-auditing: a look that
    # only fails on dark scenes shows up as a cluster of flagged records rather than as
    # something a human has to notice.
    y = s = None
    st = sh("ffprobe", "-v", "error", "-f", "lavfi",
            "-i", f"movie={dst},signalstats", "-show_entries",
            "frame_tags=lavfi.signalstats.YAVG,lavfi.signalstats.SATAVG",
            "-of", "default=nw=1", "-read_intervals", "%+#1")
    for line in (st.stdout or "").splitlines():
        if "YAVG" in line:
            y = float(line.split("=")[1])
        elif "SATAVG" in line:
            s = float(line.split("=")[1])
    flags = []
    if y is not None:
        if y < 28:
            flags.append("too_dark")
        elif y > 210:
            flags.append("blown_out")
    # NO SATURATION FLAG.
    #
    # There was one, at sat < 6, and it produced 76 of the first 79 flags - every one a
    # false positive. The values it fired on hardest were bleach, bleach_bypass and noir,
    # at 100%: looks whose entire job is to remove colour. Flagging those is flagging a
    # black-and-white film as broken.
    #
    # The giveaway was in the corpus itself. Every weather value came back flagged in
    # exactly one of two templates, which cannot be a property of weather - it was the
    # template's LOOK driving saturation. The measure was reading intent and calling it
    # failure.
    #
    # `sat` is still recorded, because it is genuinely useful for comparing looks against
    # each other. It is just not evidence of a defect on its own.

    return {
        "id": rid,
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "template": tpl_id,
        "template_name": tpl.get("name", tpl_id),
        "genre": tpl.get("genre", []),
        # the ONE variable this image demonstrates, and its value
        "demonstrates": {"variable": vary_key, "value": vary_val},
        # everything, so it can be reproduced exactly
        "vars": resolved,
        "shot": {"template": shot.get("template"), "camera": shot.get("camera", ""),
                 "desc": shot.get("desc", "")},
        "prompt": prompt,
        "negative": NEG,
        "seed": SEED,
        "model": CKPT,
        "workflow": WF,
        "steps": STEPS, "cfg": CFG, "sampler": SAMPLER,
        "size": list(SIZE),
        "grade": grade,
        "file": f"/samples/gallery/{rid}.webp",
        "bytes": os.path.getsize(dst),
        "luma": y, "sat": s, "flags": flags,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--vary", default="look",
                    help="look | emotion | lighting | weather | all")
    ap.add_argument("--template", help="only this template id (prefix match)")
    ap.add_argument("--shot", type=int, default=None,
                    help="which shot of the template (default: the most visual one)")
    ap.add_argument("--limit", type=int, default=0, help="stop after N generations")
    ap.add_argument("--loop", action="store_true", help="keep cycling forever")
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()

    libs = {k: load_dir(k) for k in ("looks", "emotions", "lighting", "weather")}
    tpls = load_dir("templates")
    if a.template:
        tpls = {k: v for k, v in tpls.items() if k.startswith(a.template)}
    if not tpls:
        raise SystemExit("no templates found")

    keys = list(VARIES) if a.vary == "all" else [a.vary]
    for k in keys:
        if k not in VARIES:
            raise SystemExit(f"cannot vary {k!r}; try: {', '.join(VARIES)} or all")

    os.makedirs(GAL, exist_ok=True)
    done = seen_ids()
    made = skipped = failed = 0
    t0 = time.time()

    while True:
        for tpl_id, tpl in sorted(tpls.items()):
            shots = tpl.get("shots") or []
            if not shots:
                continue
            # Default to the shot most likely to SHOW the variable: one with a person in
            # it, since emotion and lighting need a face to read on.
            if a.shot is not None:
                idxs = [min(a.shot, len(shots) - 1)]
            else:
                idxs = [next((i for i, s in enumerate(shots)
                              if s.get("template") not in PEOPLELESS), 0)]
            for k in keys:
                for val in sorted(libs[VARIES[k]]):
                    for i in idxs:
                        rid = f"{tpl_id}__{k}-{val}__s{i}"
                        if rid in done:
                            skipped += 1
                            continue
                        try:
                            rec = generate(tpl_id, tpl, i, k, val, libs, a.dry)
                        except Exception as e:
                            print("  FAIL %s: %s" % (rid, str(e)[:110]), flush=True)
                            failed += 1
                            continue
                        if not rec:
                            failed += 1
                            continue
                        with open(MANIFEST, "a", encoding="utf-8") as f:
                            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                        done.add(rid)
                        made += 1
                        print("  %-4d %-52s %5.1f KB" %
                              (made, rid, rec["bytes"] / 1024), flush=True)
                        if a.limit and made >= a.limit:
                            print("\nlimit reached")
                            return summary(made, skipped, failed, t0)
        if not a.loop:
            break
        print("  ... pass complete, nothing new. sleeping 300s", flush=True)
        time.sleep(300)
        done = seen_ids()
    summary(made, skipped, failed, t0)


def summary(made, skipped, failed, t0):
    el = time.time() - t0
    print("\n%d generated, %d already present, %d failed, %.1f min (%.1fs each)"
          % (made, skipped, failed, el / 60, el / max(made, 1)))
    print("manifest: %s" % MANIFEST)


if __name__ == "__main__":
    main()
