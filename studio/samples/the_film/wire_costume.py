#!/usr/bin/env python3
"""Apply the costume: wiring that compile.py does not do yet, WITHOUT touching compile.py.

compose.resolve() already reads sel["costume"] and looks it up in the character's
`costumes` map (studio/compose.py:2366, :2427). compile.py never passes it, so every
beat of terra_field_coat renders in the DEFAULT traveller costume - including the four
beats of act four, where the film is named after the coat she is not wearing.

The fix in compile.py is two lines and I do not own that file. What I do own is the
render. This script reproduces the resolver's own behaviour exactly - wear_text is
costumes[costume_id]["wear_tags"][wear] instead of character["wear_tags"][wear] - by
substring substitution on the compiled beat tags, and writes a patched film to
studio/samples/the_film/. studio/movies/terra_field_coat.json is not modified.

Every substitution asserts that the string it is replacing is actually present, so a
recompile that changes a wear rung breaks this loudly instead of silently rendering the
wrong clothes, which is the exact failure being fixed.
"""
import json, os, sys

ROOT = os.path.expanduser("~/shared/comfy-studio")
SRC = f"{ROOT}/studio/movies/terra_field_coat.json"
DST = f"{ROOT}/studio/samples/the_film/terra_field_coat.json"

# beat id -> (costume id, wear rung), read off the CHAPTER blocks of the .movie.
# Beats with no character in the prompt (the five inserts and the two empty wides)
# carry no wear text at all and are absent here.
PLAN = {
    "i_issued_dressed_01":            ("armour", 0),
    "i_issued_sent_00":               ("armour", 2),
    "ii_decided_decided_00":          ("court",  1),
    "ii_decided_she_says_it_00":      ("court",  2),
    "ii_decided_her_fist_00":         ("court",  2),
    "iii_the_road_the_road_00":       ("default", 2),
    "iii_the_road_the_ford_00":       ("default", 3),
    "iii_the_road_what_it_cost_00":   ("default", 4),
    "iv_chosen_she_asks_00":          ("field",  1),
    "iv_chosen_the_sleeve_00":        ("field",  1),
    "iv_chosen_she_walks_00":         ("field",  1),
    "iv_chosen_the_moor_again_00":    ("field",  2),
}

terra = json.load(open(f"{ROOT}/studio/characters/TERRA.json", encoding="utf-8"))
costumes = terra["costumes"]
default = terra.get("wear_tags") or costumes["default"]["wear_tags"]

film = json.load(open(SRC, encoding="utf-8"))
changed = 0
for b in film["beats"]:
    plan = PLAN.get(b["id"])
    if not plan:
        continue
    cid, rung = plan
    have = default[rung]
    want = costumes[cid]["wear_tags"][rung]
    if have not in b["tags"]:
        sys.exit(f"FAIL {b['id']}: expected default rung {rung} text in the prompt and it "
                 f"is not there. Recompile changed something; re-derive PLAN.\n  {have!r}")
    if have == want:
        continue
    b["tags"] = b["tags"].replace(have, want, 1)
    changed += 1
    print(f"  {b['id']:32s} {cid}/{rung}\n      - {have}\n      + {want}")

os.makedirs(os.path.dirname(DST), exist_ok=True)
json.dump(film, open(DST, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
print(f"\n{changed} beats re-dressed -> {DST}")
