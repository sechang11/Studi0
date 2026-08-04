#!/usr/bin/env python3
"""Train a character LoRA from a turnaround set.

    python3 studio/_tools/train_character.py VIRO
    python3 studio/_tools/train_character.py VIRO --steps 1500 --rank 16
    python3 studio/_tools/train_character.py VIRO --dry      # check without spending GPU
    python3 studio/_tools/train_character.py VIRO --no-card  # train, but do not adopt it

This is the step that turns a character from a description into a model. Everything else
in the cast pipeline exists to feed it: the turnaround produces a consistent set of one
person, and this learns them.

TIME. Unlike everything else in this project, training is minutes not seconds - roughly
1000 steps on a 16-40 image set. It runs detached and is polled, like a film render.

WHAT TO CHECK AFTERWARDS, and it is not the loss curve. Generate the same prompt with
and without the LoRA at the same seed and LOOK. A LoRA that overfits reproduces its
training images rather than the character; a LoRA that undertrains changes nothing. Both
show immediately in a side-by-side and neither shows in a number.

AND READ THE CAPTIONS IT PRINTS BEFORE IT STARTS. A caption is a subtraction: whatever it
names stays separable, whatever it omits gets absorbed into the trigger and becomes part
of the character forever. TERRA was trained with captions reading "terra, front" and
nothing else, so "terra" quietly came to mean the woman AND her gold dress AND the flat
grey wall behind her - which is why her costumes would not change and why raising her
strength greyed out the scenery. That cost a retrain to find and would have cost nothing
to see. See turnaround.py caption().
"""
import argparse, json, os, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
STUDIO = os.path.dirname(HERE)
ROOT = os.path.dirname(STUDIO)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
os.environ.setdefault("COMFY_HOST", "127.0.0.1:8188")

from comfy import set_path                             # noqa: E402
from epic import load_wf, submit, COMFY, HOST          # noqa: E402

WF = "33_train_character_lora.json"
CAST = os.path.join(STUDIO, "characters")


def dataset_dir(name):
    return os.path.join(COMFY, "input", name.lower() + "_train")


def free_name(dst_dir, fname):
    """A name in models/loras that will not overwrite an existing LoRA.

    SaveLoRA numbers its output by what is already in ComfyUI/output/loras, and that
    directory gets emptied every time a trained LoRA is moved out of it. So the SECOND
    training of a character produces character_x_00001_.safetensors all over again and
    collides with the one already installed.

    The first version of this skipped the move when the destination existed. That was the
    worst possible choice: the new weights stayed stranded in output/ where no loader can
    see them, the old file was still sitting in models/loras, and the script reported that
    old file as the result - so a retrain appeared to succeed, was adopted onto the card,
    and had in fact changed nothing. Measured the hard way on TERRA's recaption retrain.

    Overwriting would be just as bad: keeping the previous LoRA is the only way to report
    a regression honestly. So a colliding retrain gets a fresh suffix and both survive.
    """
    if not os.path.exists(os.path.join(dst_dir, fname)):
        return fname
    base = fname[:-len(".safetensors")].rstrip("_")
    i = 2
    while os.path.exists(os.path.join(dst_dir, "%s_v%d.safetensors" % (base, i))):
        i += 1
    return "%s_v%d.safetensors" % (base, i)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("character")
    ap.add_argument("--steps", type=int, default=1000)
    ap.add_argument("--rank", type=int, default=16)
    ap.add_argument("--lr", type=float)
    ap.add_argument("--dataset", help="train from this directory under ComfyUI/input "
                                      "instead of <character>_train")
    ap.add_argument("--no-card", action="store_true",
                    help="do not write the result onto the character card. Use when the "
                         "retrain is a candidate that still has to be looked at - an "
                         "adopted LoRA is live for every other tool immediately.")
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()

    name = a.character
    card_p = os.path.join(CAST, name + ".json")
    if not os.path.exists(card_p):
        have = sorted(f[:-5] for f in os.listdir(CAST) if f.endswith(".json"))
        raise SystemExit(f"unknown character {name!r}\n  have: {', '.join(have)}")

    d = os.path.join(COMFY, "input", a.dataset) if a.dataset else dataset_dir(name)
    if not os.path.isdir(d):
        raise SystemExit(
            f"no training set for {name}.\n"
            f"  expected: {d}\n"
            f"  build one first:  python3 studio/_tools/turnaround.py {name}")
    imgs = sorted(f for f in os.listdir(d) if f.endswith(".png"))
    txts = sorted(f for f in os.listdir(d) if f.endswith(".txt"))
    pairs = [f for f in imgs if f[:-4] + ".txt" in txts]

    print("character : %s" % name)
    print("dataset   : %s" % d)
    print("            %d images, %d captions, %d complete pairs" % (len(imgs), len(txts), len(pairs)))
    if len(pairs) < 8:
        print("  ! %d pairs is thin for a character. 16-40 is the usual range; below "
              "about 8 the LoRA tends to memorise rather than generalise." % len(pairs))
    if not pairs:
        raise SystemExit("nothing to train on")

    # SHOW THE CAPTIONS. They decide what the trigger comes to mean, and they are the one
    # input to training that is invisible everywhere else in the pipeline.
    print("\ncaptions - whatever these do NOT name gets absorbed into %r:" % name.lower())
    for f in pairs[:3]:
        print("    %s" % open(os.path.join(d, f[:-4] + ".txt"), encoding="utf-8").read().strip())
    if len(pairs) > 3:
        print("    ... %d more" % (len(pairs) - 3))
    words = set()
    for f in pairs:
        words.update(w.strip().lower()
                     for w in open(os.path.join(d, f[:-4] + ".txt"),
                                   encoding="utf-8").read().replace("\n", ",").split(","))
    words.discard("")
    if len(words) < len(pairs) + 2:
        print("  ! these captions name little beyond the trigger and the view. Anything\n"
              "    worn or behind the subject in every image will become part of the\n"
              "    character and will not be changeable later.")

    wf = load_wf(WF)
    set_path(wf, "1.inputs.folder", os.path.basename(d))
    set_path(wf, "5.inputs.steps", int(a.steps))
    set_path(wf, "5.inputs.rank", int(a.rank))
    if a.lr:
        set_path(wf, "5.inputs.learning_rate", float(a.lr))
    set_path(wf, "6.inputs.prefix", "loras/character_%s" % name.lower())

    print("\nsteps %d, rank %d, lr %s" % (a.steps, a.rank, wf["5"]["inputs"]["learning_rate"]))
    print("output    : ComfyUI/models/loras/character_%s*.safetensors" % name.lower())
    if a.dry:
        print("\n(dry run - nothing submitted)")
        return

    print("\nsubmitting. this is minutes, not seconds.")
    t0 = time.time()
    pid = submit(wf)
    print("  prompt id %s" % pid)
    # poll rather than block, so a long train can be watched
    import urllib.request
    last = None
    while True:
        time.sleep(15)
        try:
            with urllib.request.urlopen("http://%s/history/%s" % (HOST, pid),
                                        timeout=20) as r:
                h = json.load(r) or {}
        except Exception:
            continue
        if pid in h:
            st = h[pid].get("status", {})
            ok = st.get("status_str") == "success"
            print("\n%s after %.1f min" % ("DONE" if ok else "ENDED: %s" % st.get("status_str"),
                                           (time.time() - t0) / 60))
            if not ok:
                for m in st.get("messages", [])[-4:]:
                    print("   ", str(m)[:180])
            break
        el = (time.time() - t0) / 60
        if last is None or el - last >= 1:
            print("  ... %.0f min" % el, flush=True)
            last = el

    # SaveLoRA's `prefix` is relative to ComfyUI's OUTPUT directory, not models/. So a
    # freshly trained LoRA lands somewhere LoraLoader cannot see it, and the training
    # looks like it silently produced nothing. Move it where loaders actually look.
    src_dir = os.path.join(COMFY, "output", "loras")
    dst_dir = os.path.join(COMFY, "models", "loras")
    moved = []
    if os.path.isdir(src_dir):
        for f in sorted(os.listdir(src_dir)):
            if f.startswith("character_%s" % name.lower()) and f.endswith(".safetensors"):
                dst_name = free_name(dst_dir, f)
                subprocess.run(["mv", os.path.join(src_dir, f),
                                os.path.join(dst_dir, dst_name)])
                moved.append(dst_name)
                print("  moved %s -> models/loras/%s" % (f, dst_name))
    out = [f for f in os.listdir(dst_dir)
           if f.startswith("character_%s" % name.lower()) and f.endswith(".safetensors")]
    if not moved:
        print("  ! nothing came out of training - no new LoRA in %s" % src_dir)
        if out:
            print("    (models/loras still holds the PREVIOUS %s - it is not this run's "
                  "work and has not been adopted)" % sorted(out)[-1])
        return

    newest = sorted(moved)[-1]
    if a.no_card:
        print("\n  trained %s - NOT written onto the card (--no-card)." % newest)
        print("  Look at it first, then set the card's lora field by hand if it wins.")
        return
    card = json.load(open(card_p, encoding="utf-8"))
    card["lora"] = newest
    card["lora_trained_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    card["lora_dataset"] = "%d images" % len(pairs)
    card["lora_steps"] = int(a.steps)
    card["lora_rank"] = int(a.rank)
    json.dump(card, open(card_p, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    open(card_p, "a").write("\n")
    print("  wrote %s onto %s" % (newest, name))
    print("\nNOW LOOK AT IT. Generate the same prompt with and without the LoRA at "
          "the same seed and compare. Overfitting reproduces the training images; "
          "undertraining changes nothing. Neither shows up in a loss number.")


if __name__ == "__main__":
    main()
