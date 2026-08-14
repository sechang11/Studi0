#!/usr/bin/env python3
"""field_fix.py - does REMOVING the gold dress from the field coat's own text fix it?

    ~/ComfyUI/venv/bin/python3 studio/_tools/field_fix.py

Two agents independently diagnosed the same thing and neither tested the fix. The field
coat costume lands at damage 1 and 2 and fails at 0 and 3, in every LoRA arm, at every
seed, with and without the danbooru name. Levels 1 and 2 are the only two whose wear_tags
do NOT name the gold dress; levels 0 and 3 name it explicitly:

    0  "heavy brown travelling coat OVER THE GOLD DRESS, leather satchel ..."
    3  "coat missing a sleeve, satchel gone, GOLD DRESS SHOWING THROUGH THE TEAR ..."

The model renders nouns. Naming the garment a costume exists to REPLACE renders that
garment. That was an inference from two levels that already worked. This makes it a
measurement: the same five levels rendered twice, once with the shipped text and once with
the gold dress taken out of levels 0 and 3 and nothing else changed, across both name
arms and two seeds. 40 cells.

Level 4 is deliberately left alone in BOTH arms. Its text says "no coat, gold dress in
rags" and that is correct - the last rung of a damage ladder is the costume destroyed and
the default showing through. It is the control that proves this probe is not simply
deleting every mention of the word.
"""
import os, sys

import argparse
argparse.ArgumentParser(description='field fix').parse_args()
# ^ the CLI contract: --help exits HERE, before any work below runs.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import terra_wardrobe as tw   # noqa: E402  (sets COMFY_ROOT before importing epic)

OUT = tw.OUT_W
LAB = tw.LAB_W
REL = tw.REL_W

# The shipped text, read off the card at runtime so this cannot drift from it.
# The proposed text: levels 0 and 3 reworded to name only what is WORN.
NEW = {
    0: "heavy brown travelling coat buttoned to the collar, leather satchel across the "
       "body, worn boots, dry and clean",
    3: "coat missing a sleeve, satchel gone, torn linen shirt showing through the tear, "
       "boots split",
}


def prompt_for(c, wear, keep_name):
    tags = c["tags"] if keep_name else tw.nameless(c["tags"])
    return ", ".join(x for x in [tags, c.get("base_tags", ""), wear,
                                 tw.FRAME_COSTUME, tw.PLACE_COSTUME, tw.Q] if x)


def main():
    c = tw.card()
    lora = c["lora"]
    w = tw.strength()
    old = c["costumes"]["field"]["wear_tags"]
    tw.need(LAB, OUT)

    arms = []
    for seed in (4242, 1337):
        for keep in (True, False):
            arms.append((seed, keep))

    jobs, meta = [], {}
    for seed, keep in arms:
        for text_id in ("shipped", "reworded"):
            for lv in range(5):
                wear = old[lv] if text_id == "shipped" else NEW.get(lv, old[lv])
                tag = "fieldfix_%s_%s_%d_s%d" % (
                    text_id, "name" if keep else "noname", lv, seed)
                if tw.latest(LAB, tag, "png"):
                    continue
                j = tw.submit(tw.wf_still(prompt_for(c, wear, keep), lora, w, seed, tag,
                                          REL, tw.CW, tw.CH))
                jobs.append(j)
                meta[j] = tag
                print("  > %s" % tag, flush=True)
    if jobs:
        recs = tw.wait_all(jobs, "fieldfix")
        for j in jobs:
            e = tw.job_error(recs.get(j, {}))
            if e:
                print("  !! %s FAILED %s" % (meta[j], e))

    for seed, keep in arms:
        nm = "name" if keep else "noname"
        files, tmp = [], "/tmp/_ff_%d_%s_%d" % (os.getpid(), nm, seed)
        tw.sh("rm", "-rf", tmp)
        tw.need(tmp)
        ok = True
        for text_id in ("shipped", "reworded"):
            for lv in range(5):
                src = tw.latest(LAB, "fieldfix_%s_%s_%d_s%d" % (text_id, nm, lv, seed),
                                "png")
                if not src:
                    print("  !! missing %s %s %d s%d" % (text_id, nm, lv, seed))
                    ok = False
                    continue
                d = "%s/%s_%d.png" % (tmp, text_id, lv)
                changed = " *REWORDED*" if (text_id == "reworded" and lv in NEW) else ""
                tw._cell(src, d, 420, 614,
                         "%s | wear %s%s" % (text_id, tw.WEAR_LABEL[lv], changed))
                files.append(d)
        if not ok:
            continue
        tw._tile(files, "%s/field_fix_%s_s%d.jpg" % (OUT, nm, seed), 5,
                 "TERRA field coat - shipped text (top) vs gold dress removed from levels "
                 "0 and 3 (bottom)",
                 "seed %d, danbooru name %s, LoRA %s @ %.2f. Level 4 unchanged in both "
                 "rows - it is meant to show the dress."
                 % (seed, "KEPT" if keep else "STRIPPED", lora, w))
        tw.sh("rm", "-rf", tmp)


if __name__ == "__main__":
    main()
