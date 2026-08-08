#!/usr/bin/env python3
"""Drive the story editor from the shell: takes, selection, staleness, export.

    story_tool.py new "THE SALT ROAD"
    story_tool.py import-film films/salt_road_ep01.json --story the-salt-road
    story_tool.py show the-salt-road
    story_tool.py scene the-salt-road 01/010-table          # resolved inputs + provenance
    story_tool.py take the-salt-road 01/010-table -n 4      # four keyframes to choose from
    story_tool.py select the-salt-road 01/010-table t03
    story_tool.py clip the-salt-road 01/010-table           # animate the SELECTED take only
    story_tool.py plan the-salt-road                        # what is stale, and what is locked
    story_tool.py export the-salt-road

KEYFRAMES FOR ALL TAKES, CLIPS FOR THE WINNER. A keyframe is about 6 seconds and a clip is
about 60, and the keyframe decides the clip. Rendering four keyframes to choose from and
animating only the chosen one is a 10x saving on the loop you run most - so `take` makes
keyframes and `clip` is a separate, deliberate step.
"""
import argparse, json, os, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
STUDIO = os.path.dirname(HERE)
ROOT = os.path.dirname(STUDIO)
sys.path.insert(0, STUDIO)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
os.environ.setdefault("COMFY_HOST", "127.0.0.1:8188")
import story as S                                          # noqa: E402


def _comfy():
    from comfy import run, set_path
    from epic import load_wf, ensure_local, HOST, COMFY
    return run, set_path, load_wf, ensure_local, HOST, COMFY


# ─── commands ───────────────────────────────────────────────────────────────────────

def cmd_new(a):
    st = S.create(a.title)
    print("%s  ->  %s" % (st.id, st.dir))


def cmd_import(a):
    """Turn an existing films/*.json into a chapter of scenes.

    The point of importing rather than starting fresh: a story with real shots in it is
    testable today, and the migration proves the two models actually describe the same film.
    """
    film = json.load(open(a.film, encoding="utf-8"))
    st = S.create(a.story or film["title"])
    # Cast, voices and aspect belong to the STORY - they are the things that must not drift
    # between chapters. The narrator's voice is the through-line of the whole thing.
    st.data.setdefault("characters", {}).update(film.get("characters") or {})
    st.data.setdefault("voices", {}).update(film.get("voices") or {})
    st.data.setdefault("sheets", {}).update(film.get("sheets") or {})
    for k in ("ar", "fps", "id_lora", "id_strength"):
        if film.get(k) is not None:
            st.data.setdefault(k, film[k])
    # `engine` in a films/*.json is the TTS engine, not the picture engine. Copying it
    # straight across put `higgs_v3` in the slot the picture path reads - inert today only
    # because `take` hardcodes its workflow, and a wrong-engine render waiting to happen.
    if film.get("engine"):
        st.data.setdefault("voice_engine", film["engine"])
    st.save()

    title = a.chapter_title or film.get("subtitle") or film["title"]
    ch = S.add_chapter(st, title)
    # Style is a CHAPTER-level fact: an act looks like itself.
    ch.data["style_map"] = film.get("style") or {}
    ch.data["look"] = "default"
    ch.data["seconds"] = film.get("seconds")
    ch.data["transition"] = film.get("default_transition", "cut")
    ch.data["music"] = film.get("music") or []
    ch.save()

    prev = None
    for sh in film.get("shots", []):
        sid = S.slug(sh["id"])
        kw = {k: sh[k] for k in ("prompt", "motion", "say", "who", "sfx", "titles")
              if sh.get(k)}
        if sh.get("look"):
            kw["look"] = sh["look"]
        sc = S.add_scene(ch, sid, **kw)
        if prev:
            ch.set_transition(prev, sid, kind=ch.data["transition"], generated=False)
        prev = sid
    print("%s / %s  <-  %s   (%d scenes, %d cues)"
          % (st.id, ch.id, os.path.basename(a.film), len(ch.scene_ids()),
             len(ch.data["music"])))


def cmd_show(a):
    st = S.load(a.story)
    print("%s   %s" % (st.data.get("title"), st.dir))
    print("  cast   : %s" % ", ".join(sorted(st.data.get("characters") or {})) or "-")
    print("  voices : %s" % ", ".join(sorted(st.data.get("voices") or {})) or "-")
    for ch in st.chapters():
        scenes = ch.scenes()
        done = sum(1 for s in scenes if s.selected())
        stale = sum(1 for s in scenes for t in s.takes() if t.stale())
        print("\n  %s  %s" % (ch.id, ch.data.get("title", "")))
        print("     %d scenes, %d with a selected take, %d stale takes"
              % (len(scenes), done, stale))
        for s in scenes:
            ts = s.takes()
            sel = s.selected_id or "-"
            flags = ("LOCKED " if s.locked else "") + \
                    ("STALE " if any(t.stale() for t in ts) else "")
            print("       %-22s takes %-2d  selected %-4s %s%s"
                  % (s.id, len(ts), sel, flags,
                     (s.data.get("say") or s.data.get("prompt") or "")[:44]))


def cmd_scene(a):
    st = S.load(a.story)
    sc = st.scene(a.path)
    print("%s  (hash %s)%s\n" % (sc.id, sc.inputs_hash(), "  LOCKED" if sc.locked else ""))
    for k, v in sorted(sc.resolved().items()):
        val = v["value"]
        if isinstance(val, (dict, list)):
            val = json.dumps(val, ensure_ascii=False)
        print("  %-14s %-9s %s" % (k, "[%s]" % v["from"], str(val)[:96]))
    ts = sc.takes()
    if ts:
        print("\n  takes:")
        for t in ts:
            print("    %-5s seed %-12s %-9s %s%s"
                  % (t.id, t.meta.get("seed"), t.meta.get("status", "?"),
                     "STALE " if t.stale() else "",
                     "<- selected" if t.id == sc.selected_id else ""))


def cmd_take(a):
    """Render N keyframes for a scene. Cheap on purpose - this is the loop you live in."""
    run, set_path, load_wf, ensure_local, HOST, COMFY = _comfy()
    st = S.load(a.story)
    sc = st.scene(a.path)
    if sc.locked and not a.force:
        print("%s is locked. Pass --force to take anyway." % sc.id)
        return 1
    f = sc.flat()
    styles = sc.chapter.data.get("style_map") or {}
    look = f.get("look", "default")
    style_txt = styles.get(look) or styles.get("default") or ""
    for i in range(a.n):
        t = sc.new_take(seed=(a.seed + i) if a.seed else int(time.time() * 1000) % 2 ** 31)
        prompt = ("%s. %s" % (f.get("prompt", ""), style_txt)).strip(". ")
        wf = load_wf("13_qwen_t2i_styled.json")
        set_path(wf, "10.inputs.text", prompt)
        set_path(wf, "11.inputs.text", f.get("negative") or
                 "lowres, blurry, watermark, text, extra fingers, deformed hands")
        set_path(wf, "12.inputs.width", 1280)
        set_path(wf, "12.inputs.height", 704)
        set_path(wf, "13.inputs.seed", t.meta["seed"])
        set_path(wf, "7.inputs.strength_model", float(f.get("style_strength") or 0.0))
        set_path(wf, "15.inputs.filename_prefix",
                 "claude-generated/stories/%s/%s" % (st.id, sc.id))
        _, outs = run(HOST, wf, quiet=True)
        if not outs:
            t.save(status="failed")
            print("  %s  FAILED" % t.id)
            continue
        ensure_local(outs[0], t.keyframe, required=False)
        t.save(status="rendered", prompt=prompt)
        print("  %s  seed %-11s %s" % (t.id, t.meta["seed"], t.keyframe))
    # First take of a fresh scene becomes the selection, so an un-curated story still
    # exports. An explicit `select` always wins over this.
    if not sc.selected_id and sc.takes():
        sc.select(sc.takes()[0].id)
    return 0


def cmd_clip(a):
    """Animate the SELECTED take only.

    Deliberately separate from `take`. A keyframe is ~3s and a clip is ~60s, so rendering
    every take as video would make choosing twenty times more expensive than it needs to be
    - and the keyframe is what the choice is actually made on.
    """
    run, set_path, load_wf, ensure_local, HOST, COMFY = _comfy()
    st = S.load(a.story)
    sc = st.scene(a.path)
    t = sc.selected()
    if not t or not t.has("keyframe"):
        print("%s has no selected take with a keyframe - run `take` first" % sc.id)
        return 1
    f = sc.flat()
    staged = "story_%s_%s_%s.png" % (st.id, sc.id, t.id)
    subprocess.run(["cp", t.keyframe, os.path.join(COMFY, "input", staged)], check=False)
    secs = float(f.get("seconds") or 6)
    frames = int(round(secs * 24 / 8)) * 8 + 1
    wf = load_wf("12_ltx23_i2v_audio.json")
    set_path(wf, "8.inputs.image", staged)
    set_path(wf, "10.inputs.text", f.get("motion") or "gentle natural motion")
    set_path(wf, "20.inputs.width", 1216)
    set_path(wf, "20.inputs.height", 704)
    set_path(wf, "20.inputs.length", frames)
    set_path(wf, "21.inputs.frames_number", frames)
    # The shipped graph asks the audio latent for 25fps against 24fps video - a 4% drift.
    set_path(wf, "21.inputs.frame_rate", 24)
    set_path(wf, "32.inputs.noise_seed", t.meta.get("seed") or 1)
    set_path(wf, "43.inputs.filename_prefix",
             "claude-generated/stories/%s/%s_%s" % (st.id, sc.id, t.id))
    _, outs = run(HOST, wf, quiet=True)
    if not outs:
        print("  clip failed")
        return 1
    ensure_local(outs[0], t.clip, required=False)
    t.save(clip_seconds=secs, clip_frames=frames)
    print("  %s  %s" % (t.id, t.clip))
    return 0


def cmd_select(a):
    st = S.load(a.story)
    sc = st.scene(a.path)
    print("%s -> %s" % (sc.id, sc.select(a.take)))


def cmd_lock(a):
    st = S.load(a.story)
    sc = st.scene(a.path)
    sc.data["locked"] = not a.unlock
    sc.save()
    print("%s %s" % (sc.id, "locked" if sc.data["locked"] else "unlocked"))


def cmd_plan(a):
    """What would change, before anything is spent. The whole point of the hash."""
    st = S.load(a.story)
    stale_open, stale_locked, missing = [], [], []
    for sc in st.all_scenes():
        ts = sc.takes()
        if not ts:
            missing.append(sc.id)
        elif any(t.stale() for t in ts):
            (stale_locked if sc.locked else stale_open).append(sc.id)
    print("%s\n" % st.data.get("title"))
    print("  %-28s %d" % ("scenes with no take at all", len(missing)))
    print("  %-28s %d" % ("stale, unlocked", len(stale_open)))
    print("  %-28s %d   (will be skipped)" % ("stale, LOCKED", len(stale_locked)))
    for lbl, xs in (("no take", missing), ("stale", stale_open), ("locked+stale", stale_locked)):
        if xs:
            print("\n  %s: %s%s" % (lbl, ", ".join(xs[:12]),
                                    " ..." if len(xs) > 12 else ""))
    if not (missing or stale_open or stale_locked):
        print("\n  everything matches its inputs.")


def cmd_export(a):
    """Assemble the selected takes. A build, never a save - always a new timestamped file
    with a manifest of exactly which takes went into it."""
    st = S.load(a.story)
    stamp = time.strftime("%Y-%m-%d_%H%M")
    out = os.path.join(st.dir, "exports")
    os.makedirs(out, exist_ok=True)
    used, missing = [], []
    for ch in st.chapters():
        for sc in ch.scenes():
            t = sc.selected()
            if t and t.has("clip"):
                used.append({"scene": "%s/%s" % (ch.id, sc.id), "take": t.id,
                             "file": t.clip, "seed": t.meta.get("seed"),
                             "stale": t.stale()})
            else:
                missing.append("%s/%s" % (ch.id, sc.id))
    man = {"story": st.id, "built": stamp, "scenes": len(used),
           "missing_clips": missing, "takes": used}
    mp = os.path.join(out, "%s_manifest.json" % stamp)
    json.dump(man, open(mp, "w", encoding="utf-8"), indent=1)
    print("%d scenes ready, %d without a rendered clip" % (len(used), len(missing)))
    print("  %s" % mp)
    if missing:
        print("  missing: %s%s" % (", ".join(missing[:8]), " ..." if len(missing) > 8 else ""))
    return 0


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("new"); p.add_argument("title"); p.set_defaults(fn=cmd_new)
    p = sub.add_parser("import-film"); p.add_argument("film")
    p.add_argument("--story"); p.add_argument("--chapter-title")
    p.set_defaults(fn=cmd_import)
    p = sub.add_parser("show"); p.add_argument("story"); p.set_defaults(fn=cmd_show)
    p = sub.add_parser("scene"); p.add_argument("story"); p.add_argument("path")
    p.set_defaults(fn=cmd_scene)
    p = sub.add_parser("take"); p.add_argument("story"); p.add_argument("path")
    p.add_argument("-n", type=int, default=1); p.add_argument("--seed", type=int)
    p.add_argument("--force", action="store_true"); p.set_defaults(fn=cmd_take)
    p = sub.add_parser("clip"); p.add_argument("story"); p.add_argument("path")
    p.set_defaults(fn=cmd_clip)
    p = sub.add_parser("select"); p.add_argument("story"); p.add_argument("path")
    p.add_argument("take"); p.set_defaults(fn=cmd_select)
    p = sub.add_parser("lock"); p.add_argument("story"); p.add_argument("path")
    p.add_argument("--unlock", action="store_true"); p.set_defaults(fn=cmd_lock)
    p = sub.add_parser("plan"); p.add_argument("story"); p.set_defaults(fn=cmd_plan)
    p = sub.add_parser("export"); p.add_argument("story"); p.set_defaults(fn=cmd_export)

    a = ap.parse_args()
    return a.fn(a) or 0


if __name__ == "__main__":
    sys.exit(main())
