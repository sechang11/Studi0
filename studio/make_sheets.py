#!/usr/bin/env python3
"""Montage each card's option panels into ONE labelled contact sheet.

    python3 studio/make_sheets.py

Why: verifying a card means comparing its options side by side. Opening eight separate
files to do that is slow for a person and expensive for an agent - the first attempt at
agent verification burned a usage limit loading 976 images individually. One sheet per
card turns 976 image loads into 126.

The sheets are also what the app shows at the top of each card, so the comparison the card
is making is visible before you scroll through the panels.
"""
import io, json, os, subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
VARS = f"{HERE}/samples/vars"
SHEETS = f"{HERE}/samples/sheets"
CARDS = f"{HERE}/cards"
CW, CH = 300, 169          # per-panel size in the sheet
FONT = "C\\:/Windows/Fonts/consola.ttf"


def sh(*a):
    return subprocess.run(a, capture_output=True, text=True).returncode == 0


def main():
    os.makedirs(SHEETS, exist_ok=True)
    made = skipped = 0
    for slug in sorted(os.listdir(VARS)):
        d = f"{VARS}/{slug}"
        if not os.path.isdir(d):
            continue
        pngs = sorted(f for f in os.listdir(d) if f.endswith(".png"))
        if len(pngs) < 2:
            skipped += 1
            continue
        dst = f"{SHEETS}/{slug}.png"
        cols = 4 if len(pngs) > 6 else min(len(pngs), 3)
        rows = (len(pngs) + cols - 1) // cols

        ins, filt, labels = [], [], []
        for i, p in enumerate(pngs):
            ins += ["-i", f"{d}/{p}"]
            name = p[:-4].replace("'", "").replace(":", "")
            # burn the option value onto each panel so a sheet is self-describing
            filt.append(
                f"[{i}]scale={CW}:{CH},pad={CW}:{CH+22}:0:0:color=black,"
                f"drawtext=fontfile='{FONT}':text='{name}':fontcolor=white:fontsize=13:"
                f"x=6:y={CH+4}:box=1:boxcolor=black@0.7[p{i}]")
            labels.append(f"[p{i}]")
        # pad the last row so hstack/vstack line up
        while len(labels) < rows * cols:
            i = len(labels)
            filt.append(f"color=c=black:s={CW}x{CH+22}:d=1[p{i}]")
            labels.append(f"[p{i}]")

        rowlabels = []
        for r in range(rows):
            cells = "".join(labels[r * cols:(r + 1) * cols])
            filt.append(f"{cells}hstack=inputs={cols}[r{r}]")
            rowlabels.append(f"[r{r}]")
        if rows > 1:
            filt.append("".join(rowlabels) + f"vstack=inputs={rows}[out]")
        else:
            filt.append("[r0]copy[out]")

        ok = sh("ffmpeg", "-y", "-v", "error", *ins, "-filter_complex", ";".join(filt),
                "-map", "[out]", "-frames:v", "1", dst)
        if not ok:
            skipped += 1
            continue
        made += 1
        cp = f"{CARDS}/{slug}.json"
        if os.path.exists(cp):
            c = json.load(io.open(cp, encoding="utf-8"))
            c["sheet"] = f"/samples/sheets/{slug}.png"
            io.open(cp, "w", encoding="utf-8").write(
                json.dumps(c, indent=2, ensure_ascii=False) + "\n")

    print(f"{made} contact sheets in {SHEETS}  ({skipped} skipped)")


if __name__ == "__main__":
    main()
