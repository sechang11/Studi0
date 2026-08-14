#!/usr/bin/env python3
"""damage_nouns.py - is a damage rung written as a REMOVAL renderable at all?

    ~/ComfyUI/venv/bin/python3 studio/_tools/damage_nouns.py

field_fix.py settled one half of the field coat: taking "over the gold dress" out of level
0 puts the coat on her in all four arms. It did NOT settle level 3, where taking the gold
dress out removed the dress but did not reliably put the coat back - and level 3's text
begins "coat missing a sleeve, satchel gone". Those are SUBTRACTIONS. The costume grid
found imperial plate collapsing at exactly the two rungs written the same way
("one pauldron gone", "breastplate discarded", "one gauntlet missing").

So the hypothesis is one rule, not two bugs: THE MODEL RENDERS NOUNS, AND "GONE" IS NOT A
NOUN. A rung that names what is absent gives the sampler nothing to draw and it falls back
on whatever the trigger and the tag already know - which is the default costume. A rung
that names a DAMAGED THING gives it something to draw.

This tests that on two costumes at once, which is what makes it a rule rather than an
anecdote: field level 3 and imperial plate levels 3 and 4, each rendered with the shipped
subtractive wording and with the same state written as damaged objects, across both
danbooru-name arms and two seeds. 24 cells.
"""
import os, sys

import argparse
argparse.ArgumentParser(description='damage nouns').parse_args()
# ^ the CLI contract: --help exits HERE, before any work below runs.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import terra_wardrobe as tw   # noqa: E402

OUT, LAB, REL = tw.OUT_W, tw.LAB_W, tw.REL_W

# (costume id, level, label) -> positive rewrite naming the same state as objects present
POSITIVE = {
    ("field", 3): "torn brown coat hanging open with one sleeve ripped away, "
                  "torn linen shirt showing beneath, split boots",
    ("armour", 3): "dented steel breastplate buckled at the ribs, one steel pauldron, "
                   "torn mail sleeves, one steel gauntlet with dried blood on it, "
                   "steel greaves",
    ("armour", 4): "battered mail shirt under a torn red tabard, bare left arm bound in "
                   "cloth, one steel greave, split boots",
}
CELLS = [("field", 3), ("armour", 3), ("armour", 4)]


def prompt_for(c, wear, keep_name):
    tags = c["tags"] if keep_name else tw.nameless(c["tags"])
    return ", ".join(x for x in [tags, c.get("base_tags", ""), wear,
                                 tw.FRAME_COSTUME, tw.PLACE_COSTUME, tw.Q] if x)


def main():
    c = tw.card()
    lora, w = c["lora"], tw.strength()
    tw.need(LAB, OUT)
    arms = [(s, k) for s in (4242, 1337) for k in (True, False)]

    jobs, meta = [], {}
    for seed, keep in arms:
        for cid, lv in CELLS:
            for kind in ("subtractive", "objects"):
                wear = (c["costumes"][cid]["wear_tags"][lv] if kind == "subtractive"
                        else POSITIVE[(cid, lv)])
                tag = "dnoun_%s%d_%s_%s_s%d" % (
                    cid, lv, kind, "name" if keep else "noname", seed)
                if tw.latest(LAB, tag, "png"):
                    continue
                j = tw.submit(tw.wf_still(prompt_for(c, wear, keep), lora, w, seed, tag,
                                          REL, tw.CW, tw.CH))
                jobs.append(j)
                meta[j] = tag
                print("  > %s" % tag, flush=True)
    if jobs:
        recs = tw.wait_all(jobs, "damage_nouns")
        for j in jobs:
            e = tw.job_error(recs.get(j, {}))
            if e:
                print("  !! %s FAILED %s" % (meta[j], e))

    for seed, keep in arms:
        nm = "name" if keep else "noname"
        files, tmp = [], "/tmp/_dn_%d_%s_%d" % (os.getpid(), nm, seed)
        tw.sh("rm", "-rf", tmp)
        tw.need(tmp)
        ok = True
        for kind in ("subtractive", "objects"):
            for cid, lv in CELLS:
                src = tw.latest(LAB, "dnoun_%s%d_%s_%s_s%d" % (cid, lv, kind, nm, seed),
                                "png")
                if not src:
                    print("  !! missing %s%d %s" % (cid, lv, kind))
                    ok = False
                    continue
                d = "%s/%s_%s%d.png" % (tmp, kind, cid, lv)
                tw._cell(src, d, 420, 614, "%s | %s wear %d"
                         % (kind, c["costumes"][cid]["name"], lv))
                files.append(d)
        if not ok:
            continue
        tw._tile(files, "%s/damage_nouns_%s_s%d.jpg" % (OUT, nm, seed), 3,
                 "Is a damage rung written as a REMOVAL renderable? shipped subtractive "
                 "wording (top) vs the same state as objects (bottom)",
                 "seed %d, danbooru name %s, LoRA %s @ %.2f. Two costumes, three rungs."
                 % (seed, "KEPT" if keep else "STRIPPED", lora, w))
        tw.sh("rm", "-rf", tmp)


if __name__ == "__main__":
    main()
