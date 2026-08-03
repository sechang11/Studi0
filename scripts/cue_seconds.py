#!/usr/bin/env python3
"""Set every music cue's length from the film's real timeline.

    python3 scripts/cue_seconds.py films/berserk.json

Cue length is a FUNCTION of the timeline, not a thing to pick by eye. Picking by eye once
produced 13 of 16 cue pairs overlapping by 20-40s - two orchestral cues in different keys
playing at once under the narration - and a finale that ran 43s past the end of the film.

Each cue gets `span-to-next + OVERLAP`, so consecutive cues meet in a crossfade and nothing
stacks. A cue carrying `until_shot` stops dead there instead, which is how you author a
deliberate silence (see craft/SOUND.md).

Run AFTER `--stage narrate` (shot lengths depend on measured narration) and BEFORE
`--stage music` (cue length is a generation parameter, so changing it means re-rendering).
"""
import collections, json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("COMFY_ROOT", "Z:/ComfyUI")
os.environ.setdefault("COMFY_HOST", "192.168.1.46:8188")
from epic import part_frames, TRANSITIONS, COMFY   # noqa: E402

OVERLAP = 6.0
MINLEN, MAXLEN = 10.0, 120.0


def main(path):
    film = json.load(open(path, encoding="utf-8"), object_pairs_hook=collections.OrderedDict)
    slug = film["title"].lower().replace(" ", "-")
    nd_path = f"{COMFY}/output/claude-generated/11-short-film/{slug}/narration.json"
    nd = json.load(open(nd_path)) if os.path.exists(nd_path) else {}
    if not nd:
        raise SystemExit(f"no narration.json at {nd_path} - run --stage narrate first")

    fps = int(film.get("fps", 24))
    shots = film["shots"]
    t, starts = 0.0, {}
    for i, s in enumerate(shots):
        starts[s["id"]] = t
        seg = sum(part_frames(s, film, fps, nd)) / fps
        d = 0.0
        if i + 1 < len(shots):
            nx = shots[i + 1]
            d = float(nx.get("in_dur",
                             TRANSITIONS[nx.get("in", film.get("default_transition", "cut"))][1]))
        t += seg - d
    total = t

    cues = sorted(film.get("music", []), key=lambda c: starts.get(c.get("at_shot"), 0.0))
    for i, c in enumerate(cues):
        at = starts.get(c.get("at_shot"), float(c.get("at", 0)))
        if c.get("until_shot") in starts:
            secs = starts[c["until_shot"]] - at + 2.0
        elif i + 1 < len(cues):
            secs = starts[cues[i + 1]["at_shot"]] - at + OVERLAP
        else:
            secs = total - at + 2.0
        c["seconds"] = round(max(MINLEN, min(secs, MAXLEN)), 1)
    film["music"] = cues
    json.dump(film, open(path, "w", encoding="utf-8"), indent=2, ensure_ascii=False)

    m, s_ = divmod(total, 60)
    print(f"{film['title']}  {int(m)}m{s_:04.1f}s   {len(cues)} cues, "
          f"{sum(c['seconds'] for c in cues):.0f}s of cue")
    bad = 0
    for a, b in zip(cues, cues[1:]):
        ov = (starts[a["at_shot"]] + a["seconds"]) - starts[b["at_shot"]]
        if ov > OVERLAP + 1.5:
            bad += 1
            print(f"  ! {a['prefix']} overlaps {b['prefix']} by {ov:.1f}s")
    for c in cues:
        print(f"  {c['prefix']:16} {starts[c['at_shot']]:7.1f}s  len {c['seconds']:5.1f}"
              f"{'   (hard stop)' if c.get('until_shot') else ''}")
    print(f"\noverlaps beyond the crossfade: {bad}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "films/berserk.json")
