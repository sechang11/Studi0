#!/usr/bin/env python3
"""One contact sheet per capability card.

WHY: 206 cards hold 1026 panels, and NOT ONE has ever been looked at. The pass that
was supposed to write each card's verdict from its pixels died on a usage limit having
opened 109 of 976 images. Both predictions that WERE checked against pixels turned out
wrong (extreme_close was predicted to fail and is the best panel in the set;
extreme_wide was predicted to work and loses the figure entirely), so the card claims
cannot be trusted until someone looks.

Eight separate images per card is what made looking expensive. One labelled grid per
card makes it one glance.

    python3 studio/_tools/contact_sheets.py            # all cards
    python3 studio/_tools/contact_sheets.py shot_cam   # only slugs with this prefix

Sheets are written to studio/samples/sheets/<slug>.jpg and the path is stamped onto
the card as "sheet", so the web app can show one image instead of eight.

BYTE BUDGET: sheets are quality-stepped down until they fit MAX_BYTES. That is not
cosmetic - the link between this box and the machine reviewing the sheets drops
transfers above ~50 KB entirely, so an oversized sheet is an invisible sheet.
"""
import json, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
STUDIO = os.path.dirname(HERE)
CARDS = os.path.join(STUDIO, "cards")
OUT = os.path.join(STUDIO, "samples", "sheets")

MAX_BYTES = 46000
COLS = 4
CELL_W = 300
TMP = "/tmp/_sheet_cells"


def sh(*a):
    return subprocess.run(a, capture_output=True, text=True)


def build(card, slug):
    panels = [p for p in (card.get("panels") or []) if p.get("sample")]
    if not panels:
        return None
    os.system("rm -rf %s && mkdir -p %s" % (TMP, TMP))
    cells = []
    for i, p in enumerate(panels):
        rel = p["sample"].split("/samples/")[-1]
        src = os.path.join(STUDIO, "samples", *rel.split("/"))
        if not os.path.isfile(src):
            print("  missing panel: %s" % src)
            continue
        label = str(p.get("value", "?"))
        if p.get("control"):
            label += "  [CONTROL]"
        dst = os.path.join(TMP, "%03d.png" % i)
        # Burn the option value into the cell. Without it a grid of near-identical
        # panels is unreadable - which is exactly the case the cards exist to settle.
        r = sh("ffmpeg", "-y", "-v", "error", "-i", src, "-vf",
               "scale=%d:-1,drawtext=text='%s':fontcolor=yellow:fontsize=19:x=6:y=6:"
               "box=1:boxcolor=black@0.75:boxborderw=5" % (CELL_W, label.replace("'", "")),
               dst)
        if r.returncode == 0:
            cells.append(dst)
    if not cells:
        return None

    rows = (len(cells) + COLS - 1) // COLS
    grid = os.path.join(TMP, "_grid.png")
    r = sh("ffmpeg", "-y", "-v", "error", "-pattern_type", "glob", "-i",
           os.path.join(TMP, "[0-9]*.png"), "-filter_complex",
           "tile=%dx%d:margin=4:padding=4:color=0x111111" % (COLS, rows),
           "-frames:v", "1", grid)
    if r.returncode != 0 or not os.path.exists(grid):
        print("  tile failed: %s" % r.stderr.strip()[:200])
        return None

    os.makedirs(OUT, exist_ok=True)
    dst = os.path.join(OUT, slug + ".jpg")
    # Step quality (and then width) down until it fits the budget.
    for w, q in ((1200, 4), (1100, 5), (1000, 6), (900, 7), (820, 9), (740, 12)):
        sh("ffmpeg", "-y", "-v", "error", "-i", grid, "-vf", "scale=%d:-1" % w,
           "-q:v", str(q), dst)
        if os.path.exists(dst) and os.path.getsize(dst) <= MAX_BYTES:
            return dst, len(cells), os.path.getsize(dst)
    return dst, len(cells), os.path.getsize(dst)


def main():
    prefix = sys.argv[1] if len(sys.argv) > 1 else ""
    made = skipped = 0
    total = 0
    for fn in sorted(os.listdir(CARDS)):
        if not fn.endswith(".json"):
            continue
        slug = fn[:-5]
        if prefix and not slug.startswith(prefix):
            continue
        p = os.path.join(CARDS, fn)
        card = json.load(open(p, encoding="utf-8"))
        res = build(card, slug)
        if not res:
            skipped += 1
            continue
        dst, n, size = res
        card["sheet"] = "/samples/sheets/%s.jpg" % slug
        with open(p, "w", encoding="utf-8") as f:
            json.dump(card, f, indent=2, ensure_ascii=False)
            f.write("\n")
        made += 1
        total += size
        print("  %-34s %2d panels  %5.1f KB" % (slug, n, size / 1024), flush=True)
    print("\n%d sheets written, %d cards skipped (no panels), %.1f MB total"
          % (made, skipped, total / 1048576))


if __name__ == "__main__":
    main()
