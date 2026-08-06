#!/usr/bin/env python3
"""The whole film as one 4x5 board, in beat order, from the promoted keyframes."""
import json, os, subprocess, sys

H = os.path.expanduser("~")
KF = f"{H}/ComfyUI/output/claude-generated/12-shorts/the-coat/keyframes"
D = f"{H}/shared/comfy-studio/studio/samples/the_film"
film = json.load(open(f"{D}/terra_field_coat.json", encoding="utf-8"))
ins, fc = [], []
for i, b in enumerate(film["beats"]):
    ins += ["-i", f"{KF}/{b['id']}_00001_.png"]
    fc.append(f"[{i}:v]scale=470:-2,drawtext=text={i+1}:fontsize=42:fontcolor=yellow:"
              f"box=1:boxcolor=black:x=6:y=6[v{i}]")
for r in range(5):
    fc.append("".join(f"[v{r*4+c}]" for c in range(4)) + f"hstack=4[r{r}]")
fc.append("".join(f"[r{r}]" for r in range(5)) + "vstack=5")
subprocess.run(["ffmpeg", "-y", "-v", "error", *ins, "-filter_complex", ";".join(fc),
                "-q:v", "3", f"{D}/FINAL_KEYFRAMES.jpg"], check=True)
print("ok")
