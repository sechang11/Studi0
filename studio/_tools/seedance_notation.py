#!/usr/bin/env python3
"""studio/_tools/seedance_notation.py - the prompts we would have sent to Seedance 2.5, and did not.

Reads the `seedance` field of every shot (and every `not_shot` entry) in the shot scripts named, and
writes one notation beside the films: which shot, what we did locally instead and which take was
picked, why the paid engine would do it better, the exact prompt, the pictures it would receive, the
settings, and the one command that would send it once someone signs in to a Comfy account.

    python3 studio/_tools/seedance_notation.py dead-stock house-rules temper
"""
import json
import os
import sys

ROOT = os.path.expanduser("~/shared/comfy-studio")
STUDIO = os.path.join(ROOT, "studio")
OUTP = os.path.join(STUDIO, "samples", "fight", "SEEDANCE_NOTATION.md")
RATE = 0.09      # $/s - Seedance 2.0 Fast, the last rate verified here (playbook §0.1); 2.5's is not
ENGINE = {"shot": "LTX-2.5", "h3": "MiniMax H3", "pv": "Blender previz -> LTX-2.3 depth control",
          "pvb": "Blender previz -> LTX-2.3 depth control (no start frame)"}


def main(films):
    L = ["# Seedance notation - what we would have sent, and did not", "",
         "*Written 2026-09-29 beside the three demo films. Every shot below was rendered LOCALLY; nothing "
         "here was sent to a paid engine. For each: why the paid engine would do it better, the exact "
         "prompt, the pictures it would get, and the command that would send it.*", "",
         "**How it would run.** Workflow `76_seedance25_ref.json` (ComfyUI's `ByteDance2ReferenceNodeV2`, "
         "model *Seedance 2.5*, task *reference*, 1080p, 16:9, audio on). It needs the Comfy account token "
         "the ComfyUI frontend supplies after someone signs in at http://192.168.0.45:8188 - none is on "
         "the box, and it charges per second. `fight.py --seedance SHOT` sends [image 1] = the shot's "
         "composed start frame (`anchor_SHOT.png`), [image 2] = the character's reference, [image 3] = "
         "the place's plate, with the prompt below.", "",
         "**Price.** Seedance 2.5's per-second rate was not verified tonight; at the last verified rate "
         "(Seedance 2.0 Fast, $%.2f/s, playbook §0.1) each estimate below is per take - three seeds, "
         "the studio's floor for a pick, is three times that." % RATE, ""]
    total = 0.0
    for film in films:
        p = os.path.join(STUDIO, "shotscripts", film + ".json")
        seq = json.load(open(p, encoding="utf-8"))
        out = os.path.join(STUDIO, "samples", "fight", film)
        ranked = {}
        if os.path.exists(os.path.join(out, "ranked.json")):
            ranked = json.load(open(os.path.join(out, "ranked.json")))
        # the take in the film is the FINAL pick (picks.txt), which may be a by-eye override
        if os.path.exists(os.path.join(out, "picks.txt")):
            for kv in open(os.path.join(out, "picks.txt")).read().strip().split(","):
                if "=" in kv:
                    sid, tok = kv.split("=", 1)
                    ranked.setdefault(sid, {})["pick"] = tok
        if os.path.exists(os.path.join(out, "picks_overrides.json")):
            for sid, o in json.load(open(os.path.join(out, "picks_overrides.json"))).items():
                ranked.setdefault(sid, {})["why"] = "picked by eye - " + o["why"]
        place = seq["place"]["id"]
        L += ["## %s  (`%s`)" % (seq.get("title", film), film), "", "*%s*" % seq.get("logline", ""), ""]
        cands = [s for s in seq["shots"] if s.get("seedance")]
        if not cands and not seq.get("not_shot"):
            L += ["No shot in this film needs the paid engine.", ""]
        for s in cands:
            sd = s["seedance"]
            secs = sd.get("secs", s["secs"])
            total += secs * RATE
            chars = []
            for r in s["refs"]:
                if r != place and r not in chars:
                    chars.append(r)
            pick = (ranked.get(s["id"]) or {}).get("pick")
            if pick:
                stem = pick.split(":")[0] if ":" in pick else "shot"
                seed = pick.split(":")[-1]
                did = "%s, seed %s (%s)" % (ENGINE.get(stem, stem), seed, (ranked[s["id"]] or {}).get("why", ""))
            else:
                did = {"previz": ENGINE["pv"], "h3": "MiniMax H3", "both": "LTX-2.5 and MiniMax H3, picked by "
                       "measurement"}.get(s.get("engine", "ltx"), "LTX-2.5")
            L += ["### %s - %s" % (s["id"], s["title"]), "",
                  "- **What we did instead:** %s." % did.rstrip("."),
                  "- **Why Seedance:** %s" % sd["why"],
                  "- **Pictures:** [image 1] `anchor_%s.png` (the start frame) - [image 2] `ref_%s.png` - "
                  "[image 3] `ref_%s.png`" % (s["id"], chars[0] if chars else place, place),
                  "- **Settings:** Seedance 2.5, reference, %d s, 1080p, 16:9, audio on - about $%.2f a take "
                  "at the 2.0 Fast rate" % (secs, secs * RATE),
                  "- **Command (after signing in):** `python3 studio/_tools/fight.py --sequence %s --seedance "
                  "%s --resolution 1080p`" % (film, s["id"]), "",
                  "```text", sd["prompt"], "```", ""]
        for ns in seq.get("not_shot", []):
            total += ns.get("secs", 5) * RATE
            L += ["### not shot - %s" % ns["title"], "",
                  "- **Why it is not in the film:** %s" % ns["why"],
                  "- **Settings:** Seedance 2.5, reference, %d s, 1080p, 16:9, audio on - about $%.2f a take"
                  % (ns.get("secs", 5), ns.get("secs", 5) * RATE), "",
                  "```text", ns["seedance"], "```", ""]
    L += ["---", "",
          "**If all of it were sent once:** about $%.2f at the 2.0 Fast rate (three seeds each: $%.2f). The "
          "studio's rule for spending it is unchanged (playbook §96.4): start frames before video, by "
          "scene not by shot, and a bought take must beat the local take on the same beat, scored by the "
          "same tools, or it is decoration." % (total, 3 * total), ""]
    open(OUTP, "w", encoding="utf-8").write("\n".join(L))
    print("wrote", OUTP, "(%d lines, est. $%.2f once)" % (len(L), total))


if __name__ == "__main__":
    main(sys.argv[1:] or ["dead-stock", "house-rules", "temper"])
