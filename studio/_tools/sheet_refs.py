#!/usr/bin/env python3
"""sheet_refs.py - the references a shot script asks to be MADE, rather than drawn from words.

    python3 studio/_tools/sheet_refs.py --sequence FILM [--only ID] [--force] [--cast-engine qwen21]

A cast entry in a shot script can ask for one of three things `fight.py --cast` does not draw:

  "place": true                 a SECOND place, drawn wide (1280x720) from its prompt - --cast would
                                draw it as a 768x1344 standing figure
  "place_view": [place, view]   a place from another angle: the film's own plate turned by the
                                multiple-angles LoRA through studio/sheets.py, so it is the SAME room
                                (views: angle_left angle_right angle_reverse angle_back_r angle_high_l
                                angle_high_r angle_aerial)
  "sheet_view": [cast, view]    a character from another angle: the view from their character sheet,
                                so a shot from behind is handed the back of THEIR coat instead of the
                                compositor inventing one (views: turn_front_r turn_right turn_back_r
                                turn_back turn_back_l turn_left turn_front_l face_front face_front_r
                                face_right face_back_l)

Each lands as ref_<id>.png where fight.py looks for references, so --cast leaves it alone and the
anchors use it like any other. Run it after the base references exist and before --anchors. The
character sheets it makes are whole sheets - turnaround, faces, expressions, HD - so every film's
cast also gets a model sheet on /sheets.
"""
import argparse
import importlib.util
import json
import os
import shutil
import sys
import time

TOOLS = os.path.dirname(os.path.abspath(__file__))
STUDIO = os.path.dirname(TOOLS)
GREY = (118, 118, 118)


def engine():
    spec = importlib.util.spec_from_file_location("studio_sheets_refs", os.path.join(STUDIO, "sheets.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def fit(src, dst, size, crop):
    """A standing figure is letterboxed onto grey (its feet stay in); a place is cropped to fill."""
    from PIL import Image
    im = Image.open(src).convert("RGB")
    if crop:
        r = max(size[0] / im.width, size[1] / im.height)
        im = im.resize((round(im.width * r), round(im.height * r)), Image.LANCZOS)
        left, top = (im.width - size[0]) // 2, (im.height - size[1]) // 2
        im.crop((left, top, left + size[0], top + size[1])).save(dst)
        return
    r = min(size[0] / im.width, size[1] / im.height)
    im = im.resize((round(im.width * r), round(im.height * r)), Image.LANCZOS)
    out = Image.new("RGB", size, GREY)
    out.paste(im, ((size[0] - im.width) // 2, (size[1] - im.height) // 2))
    out.save(dst)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--sequence", required=True)
    ap.add_argument("--only", default="")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--cast-engine", default="qwen21", help="for a second place drawn from its prompt")
    ap.add_argument("--seed", type=int, default=4242)
    a = ap.parse_args()

    film = a.sequence
    script = json.load(open(os.path.join(STUDIO, "shotscripts", film + ".json"), encoding="utf-8"))
    out = os.path.join(STUDIO, "samples", "fight", film)
    os.makedirs(out, exist_ok=True)
    rp = os.path.join(out, "refs.json")
    refs = json.load(open(rp)) if os.path.exists(rp) else {}
    made_p = os.path.join(out, "sheet_refs.json")
    made = json.load(open(made_p)) if os.path.exists(made_p) else {}      # base ref -> sheet id
    E = engine()
    wanted = [(k, v) for k, v in (script.get("cast") or {}).items()
              if v.get("place") or v.get("place_view") or v.get("sheet_view")]
    if a.only:
        wanted = [w for w in wanted if w[0] == a.only] or sys.exit("no made reference called %s" % a.only)

    def sheet_for(base, kind):
        """One sheet per base reference per film, reused on every later run."""
        sid = made.get(base)
        try:
            if sid:
                E.load(sid)
                return sid
        except KeyError:
            pass
        src = os.path.join(out, "ref_%s.png" % base)
        if not os.path.exists(src):
            sys.exit("ref_%s.png is not there yet - run fight.py --cast first" % base)
        name = "%s - %s" % (script.get("title") or film, base.replace("_", " "))
        opts = {"faces": True, "expressions": True, "hd": "x2"} if kind == "character" else {"times": [], "hd": "off"}
        s = E.new(kind, name, [(src, "main")], options=opts)
        made[base] = s["id"]
        json.dump(made, open(made_p, "w"), indent=1)
        print("  sheet %s from ref_%s.png" % (s["id"], base), flush=True)
        t0 = time.time()
        E.make(s["id"], log=lambda m: print("    " + m, flush=True))
        print("  sheet %s made in %.0fs" % (s["id"], time.time() - t0), flush=True)
        return s["id"]

    for rid, spec in wanted:
        dst = os.path.join(out, "ref_%s.png" % rid)
        if os.path.exists(dst) and not a.force:
            print("  ref_%s.png already there" % rid, flush=True)
            continue
        if spec.get("sheet_view") or spec.get("place_view"):
            base, view = spec.get("sheet_view") or spec.get("place_view")
            kind = "character" if spec.get("sheet_view") else "place"
            sid = sheet_for(base, kind)
            rec = (E.load(sid)["views"].get(view) or {})
            rel = rec.get("hd") or rec.get("file")
            if not rel:
                sys.exit("sheet %s has no %s view (see its plan in studio/sheets.py)" % (sid, view))
            fit(os.path.join(E.sheet_dir(sid), rel), dst, (1280, 720) if kind == "place" else (768, 1344),
                crop=kind == "place")
            refs[rid] = {"engine": "sheet", "sheet": sid, "view": view, "from": base, "at": int(time.time())}
            print("  ref_%-16s <- sheet %s, %s" % (rid, sid, view), flush=True)
        else:
            # a second place, drawn wide from its own words through fight.py's own cast engines
            sys.argv = [sys.argv[0], "--sequence", film]
            sys.path.insert(0, TOOLS)
            import fight
            wf = fight._cast_graph(a.cast_engine, spec["prompt"], 1280, 720, a.seed,
                                   "claude-generated/fight/ref_%s" % rid)
            fight.wait_for_queue()
            t0 = time.time()
            if not fight.collect(fight.submit(wf, "ref_" + rid), dst):
                sys.exit("ref_%s: the engine returned nothing" % rid)
            if a.cast_engine == "qwen21":
                fight._to_canvas(dst, (1280, 720))
            refs[rid] = {"engine": a.cast_engine, "seed": a.seed, "prompt": spec["prompt"], "at": int(time.time())}
            print("  ref_%-16s %4.0fs  1280x720 %s s%d" % (rid, time.time() - t0, a.cast_engine, a.seed), flush=True)
        json.dump(refs, open(rp, "w"), indent=1)


if __name__ == "__main__":
    main()
