#!/usr/bin/env python3
"""Repoint every card's panel sample from .png to .webp, then drop the PNGs.

The 640x360 panels were saved as PNG, which is the wrong codec for photographic
content: 458 MB across 1026 files, averaging 447 KB each. The same panels as WebP
q82 are 30.9 MB - 14.8x smaller - which is the difference between a repo GitHub is
happy with and one it is not, and between a card page that loads instantly and one
that pulls 40 MB to show eight thumbnails.

SAFE: the full-size originals are untouched in
~/ComfyUI/output/claude-generated/studio_cards/ (1026 files, 1.3 GB). These panels
are derived thumbnails and can be regenerated from those at any time.

Idempotent. Run with --dry to see what it would do.
"""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
STUDIO = os.path.dirname(HERE)
CARDS = os.path.join(STUDIO, "cards")
VARS = os.path.join(STUDIO, "samples", "vars")

dry = "--dry" in sys.argv

changed = panels = missing = 0
for fn in sorted(os.listdir(CARDS)):
    if not fn.endswith(".json"):
        continue
    p = os.path.join(CARDS, fn)
    card = json.load(open(p, encoding="utf-8"))
    dirty = False
    for panel in card.get("panels") or []:
        s = panel.get("sample")
        if not s or not s.endswith(".png"):
            continue
        panels += 1
        webp = s[:-4] + ".webp"
        # sample paths are web paths like /samples/vars/<slug>/<val>.png
        disk = os.path.join(VARS, *webp.split("/samples/vars/")[-1].split("/"))
        if not os.path.exists(disk):
            missing += 1
            print("  MISSING %s (leaving .png)" % webp)
            continue
        panel["sample"] = webp
        dirty = True
    if dirty:
        changed += 1
        if not dry:
            with open(p, "w", encoding="utf-8") as f:
                json.dump(card, f, indent=2, ensure_ascii=False)
                f.write("\n")

print("cards repointed: %d   panels: %d   missing webp: %d%s"
      % (changed, panels, missing, "  (DRY RUN)" if dry else ""))

if dry or missing:
    print("not deleting any PNGs")
    sys.exit(0)

freed = n = 0
for dirpath, _, names in os.walk(VARS):
    for name in names:
        if not name.endswith(".png"):
            continue
        png = os.path.join(dirpath, name)
        if os.path.exists(png[:-4] + ".webp"):
            freed += os.path.getsize(png)
            os.remove(png)
            n += 1
print("removed %d PNGs, freed %.1f MB" % (n, freed / 1048576))
