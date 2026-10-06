#!/usr/bin/env python3
"""studio/_tools/shot_options.py - SHOT OPTIONS: the treatments a film or a shot ASKS for (2026-10-05).

The director, after THE FIRE ESPER: "when I prompt you for a video, will you be moving the camera or designing sound
for the key beats? What if I don't want that for every case? ... make the general improvement, but for specialized
things it should be an option and not a default." So there are two kinds of improvement (LTX_PLAYBOOK §103):

  ALWAYS - every film, no switch: H3 takes at 12 steps (no mosaic over small figures); the maker's checks (one line
  of action, everyone in the picture, facing on screen, marks chained, story time) and the frame check's warning
  for figures too small to read; the glue each shot's script asks for; score candidates mixed by the casting tool,
  the takes' own sound leading.
  OPTIONS - off unless asked: the OPTIONS below, set for a whole film and/or per shot on shots & specs (the Options
  tab), stored beside the shot script in studio/shotscripts/<film>.options.json - never in the script itself,
  which a film's maker rewrites. A film with no options file gets none of them.

Where each one acts: camera_move changes the shot's camera path when a tool loads the script (fight.py calls
apply_script) - the shot must be rendered again (set_test render --force, cast --ends --force, its keys, its
takes); the rest act in the cut (studio/_tools/glue_cut.py) or the score mixes, and need no render.

    python3 studio/_tools/shot_options.py show FILM     what is on, film-wide and per shot
    python3 studio/_tools/shot_options.py sounds FILM   make the beat sounds asked for and not made yet (ComfyUI)
"""
import copy
import hashlib
import json
import math
import os
import sys

TOOLS = os.path.dirname(os.path.abspath(__file__))
STUDIO = os.path.dirname(TOOLS)
ROOT = os.path.dirname(STUDIO)
SEQ_DIR = os.path.join(STUDIO, "shotscripts")

MOVES = ["push_in", "pull_back", "tilt_up", "tilt_down", "pan_left", "pan_right", "orbit_left", "orbit_right",
         "crane_up", "crane_down"]
# per-shot grades, all built on the studio's "filmic" base (post.py) so a cut keeps one family of looks
_FILMIC = "curves=all='0/0.02 0.22/0.26 0.5/0.58 0.78/0.88 1/0.995'"
GRADES = {
    "dusk": _FILMIC + ",eq=saturation=1.12,colorbalance=bs=0.07:bm=0.03:rh=-0.02:gm=-0.03",
    "ember": _FILMIC + ",eq=saturation=1.2,colorbalance=rs=0.06:rm=0.07:gm=-0.04:bh=-0.03",
    "fire": _FILMIC + ",eq=saturation=1.26:contrast=1.05,colorbalance=rs=0.08:rm=0.09:gm=0.01:bs=-0.05:bh=-0.06",
    "ash": _FILMIC + ",eq=saturation=0.9:contrast=1.04,colorbalance=rh=0.05:gm=-0.02:bs=0.03:bh=-0.05",
    "night": _FILMIC + ",eq=saturation=0.88:brightness=-0.03,colorbalance=bs=0.1:bm=0.05:rh=-0.04",
    "day": _FILMIC + ",eq=saturation=1.18,colorbalance=rh=0.02:bh=-0.02",
}
PLACE_GRADES = {"dusk": "dusk", "red": "ember", "burning": "fire", "volcanic": "ash", "night": "night", "day": "day"}

# what the page offers - each with what it does, where it acts and what it costs; "scope": film = one value for the
# whole film (a default for every shot where the option is also per shot), shot = per shot
OPTIONS = [
    {"id": "camera_move", "label": "Camera move", "scope": "shot", "kind": "object", "stage": "frames + takes",
     "what": "The camera moves during the shot - a push in, a pull back, a tilt, a pan, an orbit, a crane - "
             "instead of holding still.",
     "cost": "the shot is rendered again: the set's two frames from the moving camera, its key poses, its takes",
     "fields": [{"id": "move", "label": "move", "type": "enum", "choices": MOVES, "default": "push_in"},
                {"id": "amount", "label": "how far (0.1-1)", "type": "number", "min": 0.1, "max": 1.0, "step": 0.05,
                 "default": 0.3}],
     "note": "push/pull: up to 40% of the way to the subject; tilt/pan: up to 25-30 degrees; orbit: up to 30 "
             "degrees round the subject; crane: up to 40% of the distance up or down. Set films only (a camera "
             "in the 3D set)."},
    {"id": "beat_sounds", "label": "Designed sound for the beats", "scope": "shot", "kind": "object",
     "stage": "cut",
     "what": "A sound made for a beat and placed on its moment - the runes igniting, a roar, an impact - on top of "
             "the take's own sound.",
     "cost": "a few seconds per sound (Stable Audio), made by `shot_options.py sounds FILM`; then a new cut",
     "fields": [{"id": "beats", "label": "beats", "type": "list",
                 "item": [{"id": "at", "label": "at (s into the take)", "type": "number", "min": 0, "max": 30,
                           "step": 0.05, "default": 0.5},
                          {"id": "sound", "label": "the sound", "type": "text", "default": ""},
                          {"id": "gain_db", "label": "dB", "type": "number", "min": -24, "max": 6, "step": 1,
                           "default": -3},
                          {"id": "secs", "label": "length (s)", "type": "number", "min": 0.5, "max": 8,
                           "step": 0.5, "default": 2.5}]}]},
    {"id": "impact_frames", "label": "Anime impact frames", "scope": "shot", "kind": "object", "stage": "cut",
     "what": "Two or three frames of a stylised negative (or a white flash) on the hit, the way 90s anime marks "
             "the biggest blows.",
     "cost": "nothing to render; a new cut",
     "fields": [{"id": "at", "label": "at (s into the take, comma-separated)", "type": "numbers", "default": [0.5]},
                {"id": "frames", "label": "frames", "type": "number", "min": 1, "max": 6, "step": 1, "default": 2},
                {"id": "style", "label": "style", "type": "enum", "choices": ["invert", "flash"],
                 "default": "invert"}]},
    {"id": "grade", "label": "Grade", "scope": "both", "kind": "object", "stage": "cut",
     "what": "A colour grade per shot. On the film: follow the place - each shot graded by its place's state "
             "(dusk, red, burning, volcanic...). On a shot: one look for it alone.",
     "cost": "nothing to render; a new cut",
     "fields": [{"id": "look", "label": "look", "type": "enum", "choices": ["by place"] + sorted(GRADES),
                 "default": "by place"}],
     "note": "Unset, the film keeps its one grade (filmic)."},
    {"id": "music_forward", "label": "Music forward", "scope": "film", "kind": "bool", "stage": "score mixes",
     "what": "Score candidates mixed with the music leading over the takes' own sound, no beds under it "
             "(studio/_tools/score_mix.py), instead of the casting tool's mix where the takes lead.",
     "cost": "nothing to render; the score candidates mixed again",
     "note": "The director found it worse on THE FIRE ESPER (2026-10-05): for a film that wants the music in "
             "front, not by default."},
]
BY_ID = {o["id"]: o for o in OPTIONS}


# ------------------------------------------------------------------------------ the file
def path(film):
    return os.path.join(SEQ_DIR, film + ".options.json")


def load(film):
    """The film's options as stored: {"film": {id: value}, "shots": {sid: {id: value}}}; empty when none."""
    p = path(film)
    try:
        d = json.load(open(p, encoding="utf-8"))
    except (OSError, ValueError):
        d = {}
    return {"film": d.get("film") or {}, "shots": d.get("shots") or {}}


def _num(v, f, name):
    try:
        x = float(v)
    except (TypeError, ValueError):
        raise ValueError("%s: a number" % name)
    if "min" in f and x < f["min"] or "max" in f and x > f["max"]:
        raise ValueError("%s: between %s and %s" % (name, f.get("min"), f.get("max")))
    return x


def _clean_value(opt, v):
    """One option's value checked against its fields; raises ValueError with what is wrong."""
    if opt["kind"] == "bool":
        return bool(v)
    if not isinstance(v, dict):
        raise ValueError("%s: an object" % opt["id"])
    out = {"on": bool(v.get("on", True))}
    for f in opt.get("fields", []):
        val = v.get(f["id"], f.get("default"))
        name = "%s %s" % (opt["label"], f["label"])
        if f["type"] == "enum":
            if val not in f["choices"]:
                raise ValueError("%s: one of %s" % (name, ", ".join(f["choices"])))
        elif f["type"] == "number":
            val = _num(val, f, name)
        elif f["type"] == "numbers":
            if isinstance(val, str):
                val = [x for x in val.replace(";", ",").split(",") if x.strip()]
            val = [round(float(x), 3) for x in (val or [])]
        elif f["type"] == "text":
            val = str(val or "")[:300]
        elif f["type"] == "list":
            items = []
            for it in val or []:
                if not isinstance(it, dict):
                    raise ValueError("%s: a list of objects" % name)
                row = {}
                for g in f["item"]:
                    x = it.get(g["id"], g.get("default"))
                    if g["type"] == "number":
                        x = _num(x, g, "%s %s" % (name, g["label"]))
                    else:
                        x = str(x or "")[:300]
                    row[g["id"]] = x
                items.append(row)
            val = items
        out[f["id"]] = val
    return out


def clean(data):
    """The whole options document checked; returns it cleaned, or raises ValueError."""
    if not isinstance(data, dict):
        raise ValueError("options must be an object")
    out = {"film": {}, "shots": {}}
    for k, v in (data.get("film") or {}).items():
        opt = BY_ID.get(k)
        if not opt or opt["scope"] not in ("film", "both"):
            raise ValueError("no film-wide option %r" % k)
        out["film"][k] = _clean_value(opt, v)
    for sid, opts in (data.get("shots") or {}).items():
        if not (isinstance(sid, str) and len(sid) == 3 and sid.isdigit()):
            raise ValueError("shot ids are three digits")
        row = {}
        for k, v in (opts or {}).items():
            opt = BY_ID.get(k)
            if not opt or opt["scope"] not in ("shot", "both"):
                raise ValueError("no per-shot option %r" % k)
            row[k] = _clean_value(opt, v)
        if row:
            out["shots"][sid] = row
    return out


def save(film, data):
    d = clean(data)
    d = {"_comment": "Shot options for %s - the treatments asked for, off unless set here (studio/_tools/"
                     "shot_options.py, LTX_PLAYBOOK §103). Written by shots & specs." % film, **d}
    with open(path(film), "w", encoding="utf-8", newline="\n") as f:
        json.dump(d, f, indent=1, ensure_ascii=False)
    return d


def effective(opts, sid):
    """What is ON for a shot: its own values, and the film-wide value for options that are both - only the ones on."""
    opts = opts or {}
    out = {}
    for o in OPTIONS:
        v = None
        if o["scope"] in ("shot", "both"):
            v = ((opts.get("shots") or {}).get(sid) or {}).get(o["id"])
        if v is None and o["scope"] in ("film", "both"):
            v = (opts.get("film") or {}).get(o["id"])
        if v is None or v is False or (isinstance(v, dict) and not v.get("on", True)):
            continue
        out[o["id"]] = v
    return out


# ------------------------------------------------------------------------------ camera moves
def move_camera(cam, look, move, amount):
    """The end of a camera move from a still camera (cam, look): returns (cam_to, look_to)."""
    c, l = [float(v) for v in cam], [float(v) for v in look]
    d = [l[i] - c[i] for i in range(3)]
    dist = math.sqrt(sum(v * v for v in d)) or 1.0
    a = max(0.0, min(1.0, float(amount)))
    if move in ("push_in", "pull_back"):
        k = (0.4 if move == "push_in" else -0.4) * a
        return [c[i] + d[i] * k for i in range(3)], l
    if move in ("crane_up", "crane_down"):
        dz = (1 if move == "crane_up" else -1) * 0.4 * a * dist
        return [c[0], c[1], max(0.2, c[2] + dz)], l
    if move in ("tilt_up", "tilt_down"):
        horiz = math.hypot(d[0], d[1]) or 1.0
        ang = math.atan2(d[2], horiz) + (1 if move == "tilt_up" else -1) * math.radians(25 * a)
        return c, [l[0], l[1], c[2] + horiz * math.tan(ang)]
    # yaw: a pan turns the view round the camera, an orbit carries the camera round the subject; "right" is the
    # screen's right, the side the camera's right vector points to
    right = [d[1], -d[0]]
    if move in ("pan_left", "pan_right"):
        th = math.radians(30 * a) * (1 if move == "pan_right" else -1)
        best = None
        for sg in (1, -1):
            x, y = _rot(d[0], d[1], sg * th)
            if best is None or (x * right[0] + y * right[1]) * (1 if move == "pan_right" else -1) > best[0]:
                best = ((x * right[0] + y * right[1]) * (1 if move == "pan_right" else -1), x, y)
        return c, [c[0] + best[1], c[1] + best[2], l[2]]
    if move in ("orbit_left", "orbit_right"):
        th = math.radians(30 * a)
        rx, ry = c[0] - l[0], c[1] - l[1]
        best = None
        for sg in (1, -1):
            x, y = _rot(rx, ry, sg * th)
            mv = ((l[0] + x - c[0]) * right[0] + (l[1] + y - c[1]) * right[1]) * (1 if move == "orbit_right" else -1)
            if best is None or mv > best[0]:
                best = (mv, x, y)
        return [l[0] + best[1], l[1] + best[2], c[2]], l
    raise ValueError("no camera move %r" % move)


def _rot(x, y, th):
    return x * math.cos(th) - y * math.sin(th), x * math.sin(th) + y * math.cos(th)


def apply_script(seq):
    """The shot script with its options applied, for the tools that render it (fight.py calls this at load):
    a shot with a camera move gets the end of the move as its previz cam_to / look_to; every shot carries what is on
    for it as "options". Without an options file the script comes back unchanged."""
    film = seq.get("film")
    if not film or not os.path.exists(path(film)):
        return seq
    opts = load(film)
    seq = copy.deepcopy(seq)
    for sh in seq.get("shots", []):
        eff = effective(opts, sh["id"])
        if eff:
            sh["options"] = eff
        mv = eff.get("camera_move")
        pz = sh.get("previz")
        if mv and isinstance(pz, dict) and pz.get("cam") and pz.get("look") and not pz.get("cam_to") \
                and not pz.get("look_to"):
            pz["cam_to"], pz["look_to"] = move_camera(pz["cam"], pz["look"], mv["move"], mv["amount"])
            pz["cam_to"] = [round(v, 3) for v in pz["cam_to"]]
            pz["look_to"] = [round(v, 3) for v in pz["look_to"]]
    return seq


# ------------------------------------------------------------------------------ the cut
def beat_file(film, sid, beat):
    key = hashlib.sha1(("%s|%.2f" % (beat["sound"], float(beat.get("secs", 2.5)))).encode("utf-8")).hexdigest()[:10]
    return os.path.join(STUDIO, "samples", "fight", film, "_beats", "beat_%s_%s.mp3" % (sid, key))


def grade_for(opts, sh):
    """The ffmpeg grade for a shot when the grade option is on for it, else None (the film's one grade)."""
    eff = effective(opts, sh["id"])
    g = eff.get("grade")
    if not g:
        return None
    look = g.get("look", "by place")
    if look == "by place":
        look = PLACE_GRADES.get(sh.get("place_state") or "", "")
    return GRADES.get(look)


def sounds(film):
    """Make every beat sound that is asked for and not made yet (Stable Audio, workflow 10, on the ComfyUI queue)."""
    import shutil
    sys.path.insert(0, os.path.join(ROOT, "scripts"))
    import comfy
    opts = load(film)
    made = 0
    for sid, row in sorted(opts["shots"].items()):
        b = row.get("beat_sounds")
        if not b or not b.get("on", True):
            continue
        for beat in b.get("beats", []):
            if not beat.get("sound"):
                continue
            dst = beat_file(film, sid, beat)
            if os.path.exists(dst):
                continue
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            wf = {k: v for k, v in json.load(open(os.path.join(ROOT, "workflows", "10_stableaudio_sfx.json"))).items()
                  if isinstance(v, dict) and "class_type" in v}
            wf["3"]["inputs"]["text"] = beat["sound"].rstrip(". ") + ". A single sound effect, no music."
            wf["4"]["inputs"]["text"] = "music, melody, singing, speech, voices"
            wf["5"]["inputs"]["seconds"] = float(beat.get("secs", 2.5))
            wf["6"]["inputs"]["seed"] = 4242
            wf["8"]["inputs"]["filename_prefix"] = "claude-generated/beats/%s_%s" % (film, sid)
            _, outs = comfy.run("127.0.0.1:8188", wf, quiet=True)
            got = [o for o in outs or [] if str(o).endswith(".mp3")]
            if got:
                shutil.copy(os.path.join(os.path.expanduser("~/ComfyUI"), "output", got[0]), dst)
                made += 1
                print("  %s %.2fs  %s -> %s" % (sid, beat["at"], beat["sound"][:60], os.path.basename(dst)), flush=True)
            else:
                print("  %s: FAILED %s" % (sid, beat["sound"][:60]), flush=True)
    print("beat sounds: %d made" % made)


def show(film):
    opts = load(film)
    print("%s - options file %s" % (film, path(film) if os.path.exists(path(film)) else "(none: nothing is on)"))
    for k, v in opts["film"].items():
        print("  film  %-14s %s" % (k, json.dumps(v)))
    for sid, row in sorted(opts["shots"].items()):
        for k, v in row.items():
            print("  %s   %-14s %s" % (sid, k, json.dumps(v)))


if __name__ == "__main__":
    if len(sys.argv) != 3 or sys.argv[1] not in ("show", "sounds"):
        sys.exit(__doc__)
    {"show": show, "sounds": sounds}[sys.argv[1]](sys.argv[2])
