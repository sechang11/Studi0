#!/usr/bin/env python3
"""studio/_tools/isolation_run.py - render each card ALONE, so the library can show it.

    python3 studio/_tools/isolation_run.py --plan
    python3 studio/_tools/isolation_run.py --what places --per 6 --hours 1
    python3 studio/_tools/isolation_run.py --what all --hours 3

WHY. /library can now sort a card's frames by how alone the card is in them, and the
measurement that made the feature also showed the library cannot feed it:

    bamboo_grove   48 frames, exactly ONE with nothing else in it
    all 27 emotions bound to a named cast member - no generic face anywhere

So the page works and the pictures are missing. This makes the missing pictures.

FOUR KINDS, each isolating one card:

  places      the place with nobody in it, several seeds, varied hour and angle, shot
              through a NEUTRAL style. A place rendered in vaporwave teaches you about
              vaporwave; the point here is the place.
  characters  the lead at several scales and wardrobe rungs against a plain ground, so the
              frame is about them rather than about where they are standing.
  emotions    on INVENTED, UNNAMED faces, two different people per emotion. Every emotion
              frame we have is LIWEN or SHEN, which means the card has never been what you
              were actually looking at - you were reading a face you already knew.
  styles      the style on an ordinary subject in an ordinary place, so what varies between
              two style plates is the style.

Every render writes a recipe beside it in the shape roll.py writes, so library_index picks
it up with no change and the purity sort works on it immediately.

TIME-BOUNDED AND RESUMABLE. It refuses to start without --hours, checks the deadline before
each render, and skips anything already on disk - so it can be stopped and restarted.
"""
import argparse, glob, json, os, random, re, sys, time

TOOLS = os.path.dirname(os.path.abspath(__file__))
STUDIO = os.path.dirname(TOOLS)
ROOT = os.path.dirname(STUDIO)
OUT = os.path.join(STUDIO, "samples", "isolation")

for p in (TOOLS, os.path.join(ROOT, "scripts"), STUDIO):
    if p not in sys.path:
        sys.path.insert(0, p)
os.environ.setdefault("COMFY_HOST", "127.0.0.1:8188")

# Styles that get out of the way. A clean plate wants the place legible, not interpreted.
NEUTRAL = ["cinematic_film_still", "documentary_photo", "photojournalism", "kodachrome",
           "natural_light_portrait", "wuxia_live"]

# Invented people for the emotion plates. Deliberately ordinary and deliberately not any
# cast member: the card is the expression, and a familiar face would be read instead of it.
# No real person is described, named or referenced.
FACES = [
    "a man in his forties with short greying hair and a lined face, plain dark jumper",
    "a woman in her late twenties with a round face and hair tied back, plain grey shirt",
    "an older woman with deep-set eyes and white hair cut short, plain collarless blouse",
    "a young man with close-cropped hair and a broad jaw, plain white t-shirt",
]
FACE_FRAME = ("head and shoulders, plain mid-grey seamless background, soft even frontal "
              "light, sharp focus on the eyes, 85mm at f4, natural colour")


def slug(s):
    return re.sub(r"[^a-z0-9]+", "_", str(s).lower()).strip("_")[:44]


def cards(group, ready_only=True):
    out = []
    for f in sorted(glob.glob(os.path.join(STUDIO, group, "*.json"))):
        b = os.path.basename(f)
        if b.startswith("_"):
            continue
        try:
            c = json.load(open(f, encoding="utf-8"))
        except Exception:
            continue
        if ready_only and c.get("status") not in (None, "ready"):
            continue
        out.append(c)
    return out


def write_recipe(path, rec):
    with open(os.path.splitext(path)[0] + ".json", "w", encoding="utf-8") as f:
        json.dump(rec, f, indent=1, ensure_ascii=False)
        f.write("\n")


def render(job, outdir, kind, tag):
    """One image, plus the recipe beside it in roll.py's shape so /library indexes it."""
    import render_job
    d = os.path.join(outdir, kind)
    os.makedirs(d, exist_ok=True)
    dst = os.path.join(d, tag + ".png")
    if os.path.exists(dst):
        return "skip"
    got = render_job.render_image(job, d)
    if not got or not os.path.isfile(got):
        return None
    os.replace(got, dst)
    rec = dict(job)
    rec.pop("_beat", None)
    rec.update({"domain": "image", "isolation": kind,
                "rolled_at": time.strftime("%Y-%m-%dT%H:%M:%S")})
    write_recipe(dst, rec)
    return dst


def plan(a):
    places = cards("places")
    chars = [c for c in cards("characters") if c.get("status") == "ready"]
    # NOT ready-only. Every emotion card is status "partial" - that is their normal state
    # and the reason this run exists. Filtering on ready excluded all 27 and the plan
    # reported "emotions 0 frames" for the exact gap the run was built to close.
    emos = cards("emotions", ready_only=False)
    styles = [c for c in cards("styles") if c.get("id") != "_control"]
    n = {"places": len(places) * a.per,
         "characters": len(chars) * a.per,
         "emotions": len(emos) * 2,
         "styles": len(styles)}
    return {"places": places, "characters": chars, "emotions": emos, "styles": styles,
            "counts": n}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--what", default="all",
                    choices=["all", "places", "characters", "emotions", "styles"])
    ap.add_argument("--per", type=int, default=6, help="seeds per place / per character")
    ap.add_argument("--hours", type=float)
    ap.add_argument("--plan", action="store_true")
    ap.add_argument("--seed", type=int, default=31337)
    ap.add_argument("--only", help="one card id - grow just this card")
    ap.add_argument("--wide-styles", dest="wide", action="store_true",
                    help="draw from every drawable style, not the neutral few")
    ap.add_argument("--fresh", action="store_true",
                    help="prefer styles this card has not been rendered in yet")
    a = ap.parse_args()

    p = plan(a)
    if a.only:
        # Grow ONE card. "Make more of this" is the only sane thing to want when you are
        # looking at a place with two frames, and browse has a button per card.
        for k in ("places", "characters", "emotions", "styles"):
            p[k] = [c for c in p[k] if c.get("id") == a.only]
        if not sum(len(p[k]) for k in ("places", "characters", "emotions", "styles")):
            print("  no card named %s" % a.only)
            return 1
    if a.plan:
        tot = 0
        for k, n in p["counts"].items():
            if a.what in ("all", k):
                print("  %-11s %4d frames" % (k, n))
                tot += n
        print("  %-11s %4d frames  (~%.1f h at 8s each)" % ("TOTAL", tot, tot * 8 / 3600))
        return 0
    if not a.hours:
        # The deadline is the first feature. A loop with no stopping condition ran three
        # jobs at once on this box once and nothing showed it was happening.
        print("  refusing to start without --hours (use --plan to size it first)")
        return 1

    import roll
    import compose
    libs = roll.load_libs()
    deadline = time.time() + a.hours * 3600
    os.makedirs(OUT, exist_ok=True)
    done = {"places": 0, "characters": 0, "emotions": 0, "styles": 0}
    skipped = failed = 0

    def out_of_time():
        return time.time() >= deadline

    neutral = [s for s in NEUTRAL if s in libs["styles"]] or \
              [s for s in libs["styles"] if libs["styles"][s].get("family") == "photographic"]
    _seen_cache = {}

    def pick_style(pool, facet, cid, rng):
        """Prefer a style this card has NOT been rendered in yet.

        Random choice repeats itself - six rolls across six styles land on about four - so
        "more frames" and "more of what is missing" are different things. This asks what
        already exists and fills the gaps first, which is what growing a card is for.
        """
        if not a.fresh:
            return rng.choice(pool)
        key = (facet, cid)
        if key not in _seen_cache:
            seen = set()
            for f in glob.glob(os.path.join(STUDIO, "samples", "**", "*.json"),
                               recursive=True):
                if os.path.basename(f).startswith("_"):
                    continue
                try:
                    r = json.load(open(f, encoding="utf-8"))
                except Exception:
                    continue
                if isinstance(r, dict) and r.get(facet) == cid and r.get("style"):
                    seen.add(r["style"])
            _seen_cache[key] = seen
        gap = [s for s in pool if s not in _seen_cache[key]]
        if gap:
            pick = rng.choice(gap)
            _seen_cache[key].add(pick)     # do not hand the same gap out twice in one run
            return pick
        return rng.choice(pool)

    # A character package wants a SPREAD, not six frames of the same photographic look.
    # The neutral pool exists so a place plate shows the place; a character set is the
    # opposite question - does this face survive being drawn six different ways.
    if a.wide:
        neutral = sorted(roll.drawable_styles(libs))

    # A CHARACTER CARD IS WRITTEN IN ONE DIALECT, so it may only meet styles on that
    # engine. A card carrying prose and no tags contributes NOTHING to an animagine prompt:
    # the person is silently deleted and what renders is the place plus whatever emotion
    # tags survived. Measured, not guessed - 82 of 200 frames in the first wave-4 run came
    # back with no character in the prompt at all, including a woman rendered as
    # "male focus, mature male".
    #
    # This is the same rule as a LoRA being a delta on specific weights, one level up: the
    # card is a delta on a specific PROMPT LANGUAGE, and crossing engines drops it.
    _style_engine = {}

    def styles_for(card):
        want_tags = bool((card.get("tags") or "").strip())
        want_prose = bool((card.get("prose") or "").strip())
        out = []
        for s in neutral:
            # A SELF-CONTAINED style is already the whole picture - a sign, a printed page,
            # a menu - and roll drops the character when it meets one. Leaving them in a
            # character's pool is the same bug as the dialect mismatch wearing a different
            # hat: the frame renders, and the person is not in it.
            if (libs["styles"].get(s) or {}).get("self_contained"):
                continue
            if s not in _style_engine:
                try:
                    _style_engine[s] = compose.resolve(libs, {"style": s})["engine"]
                except Exception:
                    _style_engine[s] = None
            e = _style_engine[s]
            if e == "anime" and want_tags:
                out.append(s)
            elif e in ("qwen", "flux2") and want_prose:
                out.append(s)
        return out or neutral
    if not neutral:
        print("  no neutral style available - a clean plate needs one")
        return 1

    def go(kind, tag, job):
        nonlocal skipped, failed
        if out_of_time():
            return False
        r = render(job, OUT, kind, tag)
        if r == "skip":
            skipped += 1
        elif r:
            done[kind] += 1
        else:
            failed += 1
        left = (deadline - time.time()) / 60.0
        print("  %-11s %-34s %s   %3.0fm left"
              % (kind, tag[:34], "ok" if r and r != "skip" else r or "FAILED", left))
        return True

    # ---- places: nobody in frame, several seeds, a neutral style ---------------------
    if a.what in ("all", "places"):
        for c in p["places"]:
            for i in range(a.per):
                rng = random.Random(a.seed + hash(c["id"]) % 9999 + i)
                job = roll.roll_image(rng, libs, {
                    "place": c["id"], "no_characters": True, "no_look": True,
                    "style": pick_style(neutral, "place", c["id"], rng)})
                # Growing uses a time-derived offset so a second run of the same card makes
                # NEW frames instead of skipping the ones it already has.
                base = a.seed + (int(time.time()) % 9973 if a.only else 0)
                job["seed"] = base + i * 7919
                job["id"] = ("grow_%s_%d_%d" % (slug(c["id"]), base % 9973, i) if a.only
                             else "clean_%s_%d" % (slug(c["id"]), i))
                if not go("places", job["id"], job):
                    break
            if out_of_time():
                break

    # ---- characters: them, at several scales, against as little as possible ----------
    if a.what in ("all", "characters") and not out_of_time():
        SCALES = ["close-up", "medium close-up", "medium shot", "wide shot"]
        for c in p["characters"]:
            for i in range(a.per):
                rng = random.Random(a.seed + hash(c["id"]) % 9999 + i * 31)
                pool = styles_for(c)
                job = roll.roll_image(rng, libs, {
                    "character": c["id"], "cast_rate": 1.0,
                    "style": pick_style(pool, "character", c["id"], rng)})
                base = a.seed + (int(time.time()) % 9973 if a.only else 0)
                job["seed"] = base + i * 6151
                job["id"] = ("grow_%s_%d_%d" % (slug(c["id"]), base % 9973, i) if a.only
                             else "char_%s_%d" % (slug(c["id"]), i))
                # One scale per seed, cycled - the point of a character's own set is to see
                # them at several distances, not six close-ups.
                want = SCALES[i % len(SCALES)]
                m = roll.FRAMING_RE.search(job["prompt"])
                if m:
                    job["prompt"] = job["prompt"][:m.start()] + want + job["prompt"][m.end():]
                if not go("characters", job["id"], job):
                    break
            if out_of_time():
                break

    # ---- emotions: invented faces, two people each ----------------------------------
    if a.what in ("all", "emotions") and not out_of_time():
        eng_style = neutral[0]
        for c in p["emotions"]:
            # The expression is spread across four fields on these cards - face, eyes,
            # mouth, body - not a single line. Reading only `desc` would have prompted
            # "emotion preset: angry", which is a label, not a description of a face.
            emits = ", ".join(x for x in (c.get("face"), c.get("eyes"), c.get("mouth"),
                                          c.get("body")) if x) or c.get("desc") or c["id"]
            for i in range(2):
                # Growing rotates onto a DIFFERENT invented face and a new id. Without
                # this the ids are deterministic, every frame already exists, and the run
                # reports "skipped 2" as a success while making nothing.
                off = (int(time.time()) % 9973) if a.only else 0
                face = FACES[(hash(c["id"]) + i + off) % len(FACES)]
                rng = random.Random(a.seed + hash(c["id"]) % 9999 + i * 17)
                r = compose.resolve(libs, {"style": eng_style})
                job = {
                    "domain": "image", "engine": r["engine"], "style": eng_style,
                    "place": None, "look": None, "character": None,
                    "emotion": c["id"], "framing": "close-up",
                    # The EXPRESSION leads. It is the card being shown, so it is the first
                    # thing in the prompt rather than a clause after a person's description.
                    "prompt": "%s. %s. %s" % (emits, face, FACE_FRAME),
                    "negative": r.get("negative") or "",
                    "width": 1024, "height": 1024,
                    "seed": a.seed + off + i * 5417 + hash(c["id"]) % 1000,
                    "id": ("grow_%s_%d_%d" % (slug(c["id"]), off, i) if a.only
                           else "emo_%s_%d" % (slug(c["id"]), i)),
                    "generic_face": True,
                    "provenance": "invented face, not a cast member and not a real person",
                }
                if not go("emotions", job["id"], job):
                    break
            if out_of_time():
                break

    # ---- styles: one ordinary subject, so what differs between plates is the style ---
    if a.what in ("all", "styles") and not out_of_time():
        # ASK ROLL WHICH STYLES IT WILL ACTUALLY DRAW. Its drawable set excludes anything
        # not ready and anything whose compose mode is injects or inert - and handing it an
        # excluded card makes _narrow refuse, by design. Passing every card on disk killed
        # the whole styles phase on its first card, american_comic, after places,
        # characters and emotions had already completed. 105 frames lost to one bad id.
        drawable = set(roll.drawable_styles(libs))
        # SELF-CONTAINED CARDS ARE INCLUDED, just rendered differently. They are their own
        # whole picture and take no place, so pinning market_street would fight them - but
        # skipping them entirely is why the ten flux2 physical-media styles sat on 4-8
        # frames while every other style had dozens. They were excluded, not unpopular.
        want = [c for c in p["styles"] if c["id"] in drawable]
        print("  styles: %d of %d cards are drawable and not self-contained"
              % (len(want), len(p["styles"])))
        for c in want:
            rng = random.Random(a.seed + hash(c["id"]) % 9999)
            solo = bool(c.get("self_contained"))
            try:
                job = roll.roll_image(rng, libs, dict(
                    {"style": c["id"], "no_characters": True, "no_look": True},
                    **({} if solo else {"place": "market_street"})))
            except SystemExit as e:
                # One card that cannot be composed must not end the phase. The run has
                # already spent two hours by the time it reaches here.
                print("  styles      %-34s SKIPPED (%s)" % (c["id"][:34], str(e)[:60]))
                continue
            soff = (int(time.time()) % 9973) if a.only else 0
            job["seed"] = a.seed + soff
            job["id"] = ("grow_%s_%d" % (slug(c["id"]), soff) if a.only
                         else "style_%s" % slug(c["id"]))
            if not go("styles", job["id"], job):
                break

    print("\n  done: %s | skipped %d | failed %d"
          % (", ".join("%s %d" % (k, v) for k, v in done.items() if v), skipped, failed))
    if not sum(done.values()):
        # "skipped 12, failed 0" reads as success at a glance and means nothing was made.
        print("  !! NOTHING WAS RENDERED - every frame already existed. Use --only to grow "
              "a card, which offsets the ids, or delete what is there.")
    print("  rebuild the index:  python3 studio/_tools/library_index.py --build")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
