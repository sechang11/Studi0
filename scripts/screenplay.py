#!/usr/bin/env python3
"""screenplay.py - a human-editable film script, compiled into the render pipeline.

    python3 scripts/screenplay.py films/episode01.film            # compile -> .json
    python3 scripts/screenplay.py films/episode01.film --timeline # show the timeline
    python3 scripts/screenplay.py films/episode01.json --export   # .json -> .film

WHY THIS EXISTS

Until now a film was a Python builder script: to change one line of dialogue you edited
code, and to re-time a scene you edited a template table. That puts the author outside
the work. This is the editable layer - a screenplay you can open, read top to bottom,
and change without knowing anything about the renderer.

THE FORMAT

Header directives, then scenes. Indentation is not significant; blank lines separate
shots. Anything after `//` is a comment.

    TITLE: THE DERBY - Episode 1
    CANVAS: 1920x1080
    FPS: 24
    CHECKPOINT: animagine-xl-4.0.safetensors

    CHARACTER VIRO
      tags:  1boy, long dark brown curly hair, ponytail, brown eyes, number 7
      voice: higgs_v3 voices_examples/higgs_audio/vex.wav
      sheet: sheet_anime_viro.png

    MUSIC ep_cold @0 90s level:0.8
      sparse melancholy piano, single sustained cello, restrained, instrumental

    SCENE 03_locker | INT. LOCKER ROOM - NIGHT | wear:0
      set: locker room interior, benches, hanging jerseys, fluorescent light

      EST 6s static
        soccer locker room interior, benches, wide shot

      MANAGER: Nine years. Nine years we have come here and gone home quiet.

      REACT VIRO 3s push
        listening, jaw tight, close-up

      VIRO (thinking): He does not understand. It was never about the team.

SHOT TYPES map to the episode templates in scene_templates.py:

    EST      establish     where we are. Once per scene.
    MASTER   master        the wide that holds the geography.
    SPEAK    speak         a line, held past the last syllable.
    REACT    react         a face receiving what was just said.
    PILLOW   pillow        cutaway with no people. Ozu's device.
    INSERT   insert        a detail the audience must notice.
    BUILD    build         rising tension, shots shorten.
    SAKUGA   sakuga        the money sequence. One or two per episode.
    SILENT   hold_silent   the long quiet shot before an impact.

DIALOGUE is written `NAME: line`, which generates the speaking shot AND a reaction shot
on the listener automatically - reactions are where an episode earns its emotion and are
too easy to forget. Suppress with `NAME (no react):`. `NAME (thinking):` is interior
monologue, voiced without a reaction.

CAMERA is the last word of a shot line: static, push, pull, pan_l, pan_r, tilt_u,
tilt_d, handheld. Default is static, which is correct more often than people expect.

WEAR is per scene and only ever increases - damage continuity. See craft/ANIME_EPISODE.md.
"""
import argparse, collections, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from scene_templates import expand as ex   # noqa: E402

Q = "masterpiece, best quality, very aesthetic, absurdres"
MALE = "male focus, mature male, masculine"
SHOTS = {"EST": "establish", "MASTER": "master", "SPEAK": "speak", "REACT": "react",
         "PILLOW": "pillow", "INSERT": "insert", "BUILD": "build", "SAKUGA": "sakuga",
         "SILENT": "hold_silent"}
CAMERAS = {"static", "push", "pull", "pan_l", "pan_r", "tilt_u", "tilt_d", "handheld"}
WEAR = ["clean uniform, neat hair",
        "sweaty, damp hair, flushed",
        "sweaty, dirt on uniform, messy hair, breathing hard",
        "torn uniform, dirt and grass stains, exhausted, dishevelled",
        "torn bloodied uniform, cut on face, utterly exhausted, trembling"]


def parse(path):
    head, chars, music, scenes = {}, {}, [], []
    scene = cur_char = cur_music = None
    pending = None          # a shot awaiting its description line
    lines = open(path, encoding="utf-8").read().splitlines()

    def flush():
        nonlocal pending
        if pending:
            scene["shots"].append(pending)
            pending = None

    for raw in lines:
        line = raw.split("//")[0].rstrip()
        if not line.strip():
            continue
        stripped = line.strip()
        indented = line[0] in " \t"

        m = re.match(r"^(TITLE|CANVAS|FPS|CHECKPOINT|STYLE|HOOK):\s*(.+)$", stripped)
        if m and not indented:
            head[m.group(1).lower()] = m.group(2).strip()
            continue
        m = re.match(r"^CHARACTER\s+(\w+)$", stripped)
        if m:
            flush()
            cur_char = m.group(1)
            chars[cur_char] = {}
            cur_music = None
            continue
        m = re.match(r"^MUSIC\s+(\S+)\s+@(\d+)\s+(\d+)s(?:\s+level:([\d.]+))?$", stripped)
        if m:
            flush()
            cur_music = {"prefix": m.group(1), "at": int(m.group(2)),
                         "seconds": int(m.group(3)),
                         "level": float(m.group(4) or 1.0), "tags": ""}
            music.append(cur_music)
            cur_char = None
            continue
        m = re.match(r"^SCENE\s+(\S+)\s*\|\s*([^|]+?)\s*(?:\|\s*wear:(\d+))?$", stripped)
        if m:
            flush()
            scene = {"id": m.group(1), "slug": m.group(2).strip(),
                     "wear": int(m.group(3) or 0), "set": "", "shots": []}
            scenes.append(scene)
            cur_char = cur_music = None
            continue

        if cur_char is not None:
            k, _, v = stripped.partition(":")
            chars[cur_char][k.strip()] = v.strip()
            continue
        if cur_music is not None:
            cur_music["tags"] = (cur_music["tags"] + " " + stripped).strip()
            continue
        if scene is None:
            continue
        if stripped.lower().startswith("set:"):
            scene["set"] = stripped.split(":", 1)[1].strip()
            continue

        # NAME: dialogue   /   NAME (thinking): ...   /   NAME (no react): ...
        m = re.match(r"^([A-Z][A-Z0-9_]*)\s*(?:\(([^)]+)\))?\s*:\s*(.+)$", stripped)
        if m and m.group(1) not in SHOTS:
            flush()
            mode = (m.group(2) or "").lower()
            scene["shots"].append({"kind": "speak", "who": m.group(1),
                                   "text": m.group(3).strip(),
                                   "thinking": "think" in mode,
                                   "react": "no react" not in mode, "camera": "static",
                                   "desc": "", "secs": None})
            continue

        # SHOTTYPE [WHO] [Ns] [camera]
        parts = stripped.split()
        if parts[0].upper() in SHOTS:
            flush()
            kind = SHOTS[parts[0].upper()]
            who = secs = None
            camera = "static"
            for tok in parts[1:]:
                if re.match(r"^\d+(\.\d+)?s$", tok):
                    secs = float(tok[:-1])
                elif tok.lower() in CAMERAS:
                    camera = tok.lower()
                elif re.match(r"^[A-Z][A-Z0-9_]*$", tok):
                    who = tok
            pending = {"kind": kind, "who": who, "text": "", "thinking": False,
                       "react": False, "camera": camera, "desc": "", "secs": secs}
            continue

        if pending is not None:           # description line under a shot
            pending["desc"] = (pending["desc"] + " " + stripped).strip()

    flush()
    return head, chars, music, scenes


def compile_film(path):
    head, chars, music, scenes = parse(path)
    B = []
    wear = 0
    for sc in scenes:
        wear = max(wear, sc["wear"])            # damage never heals
        loc = sc["set"] or sc["slug"]
        for i, sh in enumerate(sc["shots"]):
            bid = f"{sc['id']}_{i:02d}"
            who = sh["who"] if sh["who"] in chars else None
            desc = sh["desc"] or ("close-up" if who else sc["slug"])
            if who:
                tags = (f"{chars[who].get('tags','')}, {MALE}, {WEAR[min(wear,4)]}, "
                        f"{desc}, {loc}, {Q}")
            else:
                tags = f"{desc}, {loc}, {Q}"
            d = collections.OrderedDict(id=bid, template=sh["kind"], clip_secs=6)
            if who:
                d["ref"] = [who]
            d["tags"] = tags
            d["prompt"] = tags
            d["motion"] = "Slow deliberate camera move. Subtle natural movement only."
            d["camera"] = sh["camera"]
            if sh["secs"]:
                d["hold"] = sh["secs"]
            if sh["text"]:
                d["line"] = {"who": sh["who"], "text": sh["text"]}
            B.append(d)
            if sh["react"] and sh["text"]:
                other = next((c for c in chars if c != sh["who"] and c != "MANAGER"), None)
                if other:
                    B.append(collections.OrderedDict(
                        id=f"{bid}r", template="react", clip_secs=6, ref=[other],
                        tags=f"{chars[other].get('tags','')}, {MALE}, {WEAR[min(wear,4)]}, "
                             f"listening, close-up, reaction, {loc}, {Q}",
                        prompt="", motion="Almost still. Only the eyes and breath move.",
                        camera="static"))
    for b in B:
        b.setdefault("prompt", b["tags"])

    cw, ch = (head.get("canvas", "1920x1080").lower().split("x"))
    film = collections.OrderedDict(
        title=head.get("title", "UNTITLED"), fps=int(head.get("fps", 24)),
        canvas=[int(cw), int(ch)], engine="higgs_v3", keyframe_engine="anime",
        anime_ckpt=head.get("checkpoint", "animagine-xl-4.0.safetensors"),
        ipadapter_weight=0.6, style=head.get("style", "modern sports anime, cel shading"),
        anime_sheets={k: v["sheet"] for k, v in chars.items() if v.get("sheet")},
        sheets={k: v["sheet"] for k, v in chars.items() if v.get("sheet")},
        characters={k: k for k in chars},
        voices={k: {"engine": v.get("voice", "higgs_v3 ").split()[0],
                    "voice": v.get("voice", " ").split()[-1]}
                for k, v in chars.items() if v.get("voice")},
        music=music, beats=B)
    return film, scenes


def timeline(film, scenes):
    """What the author actually needs to see: where every scene starts and how long it runs."""
    print(f"{'at':>8} {'len':>7} {'shots':>6} {'lines':>6}  scene")
    t = 0.0
    idx = 0
    for sc in scenes:
        n = sum(1 for b in film["beats"] if b["id"].startswith(sc["id"]))
        secs = 0.0
        for b in film["beats"][idx:idx + n]:
            cuts, imp = ex(b, float(b["clip_secs"]))
            secs += sum(c["len"] for c in cuts) + (0.083 if imp else 0)
        lines = sum(1 for b in film["beats"][idx:idx + n] if b.get("line"))
        print(f"{int(t)//60:>5}:{int(t)%60:02d} {secs:7.1f} {n:6} {lines:6}  "
              f"{sc['slug']}")
        t += secs
        idx += n
    print(f"\ntotal {t/60:.1f} min, {len(film['beats'])} beats, "
          f"{sum(1 for b in film['beats'] if b.get('line'))} spoken lines")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("--timeline", action="store_true")
    a = ap.parse_args()
    film, scenes = compile_film(a.path)
    out = os.path.splitext(a.path)[0] + ".json"
    json.dump(film, open(out, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    print(f"compiled {a.path} -> {out}")
    if a.timeline:
        print()
        timeline(film, scenes)


if __name__ == "__main__":
    main()
