#!/usr/bin/env python3
"""char_extract.py - turn one or many reference images into character seeds.

    python3 studio/_tools/char_extract.py --images a.jpg b.jpg c.jpg
    python3 studio/_tools/char_extract.py --dir studio/uploads/margit --json
    python3 studio/_tools/char_extract.py --images a.jpg --apply margit

NO MODEL BEYOND THE BOX IS INVOLVED. Every image is captioned by the local vision
graph (workflow 30) exactly as character_new.py does it. This tool adds the part
that one image cannot give you: AGREEMENT. One photograph is an opinion - a
shadow reads as a scar, a wet head reads as dark hair. Several photographs of the
same person let the facts vote, and the ones that do not agree get reported
instead of guessed.

HOW THE VOTE WORKS, and why it is deliberately dumb:
  * every caption is scanned for the option words the dictionary already knows,
    so extraction speaks the same vocabulary the selectors do;
  * a fact seen in more images wins;
  * face facts (eye colour, face shape, marks) are weighted toward images the
    captioner called a close-up, because a full-length shot guesses at eyes;
  * anything where the top two candidates are within one vote is NOT decided. It
    lands in `conflicts` for a person to settle. A confident wrong answer costs
    more than a question.

WHAT IT WRITES: nothing, unless --apply names a character, in which case the
merged description becomes that character's notes and the agreed options become
its selections. Without --apply it prints and exits.
"""
import argparse, glob, json, os, re, sys

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(TOOLS))
for p in (TOOLS, os.path.join(ROOT, "scripts")):
    if p not in sys.path:
        sys.path.insert(0, p)

CLOSE_HINTS = ("portrait", "head", "face", "close-up", "close up", "headshot",
               "shoulders")
FACE_SUBS = {"eye_color", "eye_shape", "face_shape", "brows", "marks",
             "facial_hair", "hair_color", "hair_style"}

# A colour is meaningless without its noun: "a teal blue dress" is not blue hair.
# An option only scores when its word sits within WINDOW characters of an anchor.
ANCHORS = {
    "hair_color": ("hair", "bangs", "fringe", "mane", "ponytail", "braid", "locks"),
    "hair_style": ("hair", "bangs", "fringe", "mane", "cut", "bob", "braid"),
    "eye_color": ("eye", "eyes", "iris", "irises", "gaze"),
    "eye_shape": ("eye", "eyes", "eyelid", "gaze"),
    "brows": ("brow", "brows", "eyebrow", "eyebrows"),
    "face_shape": ("face", "jaw", "jawline", "chin", "cheekbones", "muzzle"),
    "skin": ("skin", "complexion", "tone", "fur", "scales", "chrome"),
    "facial_hair": ("beard", "moustache", "mustache", "stubble", "goatee", "chin"),
    "marks": ("scar", "tattoo", "birthmark", "freckle", "freckles", "earring",
              "glasses", "eyepatch", "marking", "markings"),
}
WINDOW = 60


# anchor noun -> the sub it belongs to, built once from ANCHORS
_OWNER = {}
for _sub, _nouns in ANCHORS.items():
    for _n in _nouns:
        _OWNER.setdefault(_n, set()).add(_sub)


def _owner_at(low, pos):
    """Which sub does the word at `pos` describe? The nearest anchor noun wins,
    and only within WINDOW - beyond that the word is describing something we do
    not model (a garment, a background) and must not vote at all."""
    import re as _re
    best, best_d = None, WINDOW + 1
    for noun, subs in _OWNER.items():
        for m in _re.finditer(r"\b%s\b" % _re.escape(noun), low):
            d = 0 if m.start() <= pos <= m.end() else min(abs(m.start() - pos),
                                                          abs(m.end() - pos))
            if d < best_d:
                best, best_d = subs, d
    return best or set()


def _scores(low, word, sub, anchors):
    """How many times `word` is used to describe `sub` in this caption."""
    import re as _re
    n = 0
    for m in _re.finditer(r"\b%s\b" % _re.escape(word), low):
        if not anchors:
            n += 1
        elif sub in _owner_at(low, m.start()):
            n += 1
    return n


def _dict():
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "foundry", os.path.join(ROOT, "studio", "foundry.py"))
    FY = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(FY)
    return FY, FY.load_dict()


def caption_images(paths):
    """One vision call per image. Returns [(path, caption)] - failures are kept as
    empty strings so the count of sources stays honest."""
    import shutil
    import character_new as CN
    from epic import COMFY
    out = []
    for i, p in enumerate(paths):
        staged = "charx_%d_%s" % (i, os.path.basename(p))
        staged = re.sub(r"[^A-Za-z0-9._-]", "_", staged)
        shutil.copy(p, os.path.join(COMFY, "input", staged))
        try:
            out.append((p, (CN.caption(staged) or "").strip()))
        except Exception as e:
            print("  ! %s: %s" % (os.path.basename(p), e), file=sys.stderr)
            out.append((p, ""))
    return out


def _terms(D, entity, sub):
    """The words that stand for each option: its label and its prompt fragment.
    Extraction and selection therefore share one vocabulary."""
    spec = (D.get(entity) or {}).get("subs", {}).get(sub) or {}
    for o in spec.get("options", []):
        words = {o["label"].lower()}
        frag = (o.get("frag") or "").lower()
        frag = re.sub(r"^(a|an|the)\s+", "", frag)
        if frag:
            words.add(frag)
            head = re.split(r"[,(]", frag)[0].strip()
            if head:
                words.add(head)
        yield o["id"], {w for w in words if len(w) > 2}


def vote(D, captions):
    """Score every option against every caption. Returns (agreed, conflicts)."""
    subs = (D.get("character") or {}).get("subs", {})
    tally, seen_in = {}, {}
    for path, text in captions:
        if not text:
            continue
        low = text.lower()
        close = any(h in low[:200] for h in CLOSE_HINTS)
        for sub in subs:
            if sub == "voice":
                continue
            anchors = ANCHORS.get(sub)
            for oid, words in _terms(D, "character", sub):
                if not any(_scores(low, w, sub, anchors) for w in words):
                    continue
                w = 2 if (close and sub in FACE_SUBS) else 1
                tally.setdefault(sub, {}).setdefault(oid, 0)
                tally[sub][oid] += w
                seen_in.setdefault((sub, oid), []).append(os.path.basename(path))

    agreed, conflicts = {}, []
    for sub, opts in tally.items():
        ranked = sorted(opts.items(), key=lambda kv: -kv[1])
        top, score = ranked[0]
        runner = ranked[1] if len(ranked) > 1 else None
        if runner and score - runner[1] <= 1:
            conflicts.append({"sub": sub, "candidates": [
                {"id": o, "score": s, "seen_in": seen_in.get((sub, o), [])}
                for o, s in ranked[:3]]})
            continue
        if subs[sub].get("multi"):
            agreed[sub] = [o for o, s in ranked if s >= score]
        else:
            agreed[sub] = top
    return agreed, conflicts


def merge_text(captions):
    """The captions as one block, deduplicated by sentence. The words are what
    survive to every engine, so nothing is thrown away - only repeated."""
    seen, keep = set(), []
    for _, text in captions:
        for s in re.split(r"(?<=[.;])\s+", text or ""):
            k = re.sub(r"[^a-z ]", "", s.lower()).strip()
            if len(k) > 12 and k not in seen:
                seen.add(k)
                keep.append(s.strip())
    return " ".join(keep)


def main():
    ap = argparse.ArgumentParser(
        description="Turn reference images into character seeds by agreement.")
    ap.add_argument("--images", nargs="*", default=[])
    ap.add_argument("--dir", help="a folder of reference images")
    ap.add_argument("--apply", metavar="CHARACTER_ID",
                    help="write the result onto an existing foundry character")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    paths = list(a.images)
    if a.dir:
        for ext in ("png", "jpg", "jpeg", "webp"):
            paths += sorted(glob.glob(os.path.join(a.dir, "*." + ext)))
    paths = [p for p in paths if os.path.isfile(p)]
    if not paths:
        raise SystemExit("no images. pass --images a.png b.png or --dir folder/")

    FY, D = _dict()
    caps = caption_images(paths)
    got = [c for c in caps if c[1]]
    if not got:
        raise SystemExit("the vision model returned nothing for any image")

    agreed, conflicts = vote(D, caps)
    text = merge_text(caps)
    result = {"sources": len(paths), "captioned": len(got),
              "description": text, "selections": agreed,
              "conflicts": conflicts,
              "captions": [{"image": os.path.basename(p), "text": c}
                           for p, c in caps]}

    if a.apply:
        asset = FY.load_asset("character", a.apply)
        asset["selections"].update(agreed)
        asset["notes"] = text
        asset["source_images"] = [os.path.basename(p) for p in paths]
        FY.recompile(asset)
        FY.save_asset(asset)
        result["applied_to"] = a.apply

    if a.json:
        print(json.dumps(result, indent=1))
        return
    print("sources    : %d image(s), %d captioned" % (len(paths), len(got)))
    print("description: %s" % (text[:400] or "-"))
    print("agreed     :")
    for k, v in sorted(agreed.items()):
        print("   %-14s %s" % (k, v))
    if conflicts:
        print("conflicts  : (not decided - settle these yourself)")
        for c in conflicts:
            names = ", ".join("%s=%d" % (x["id"], x["score"])
                              for x in c["candidates"])
            print("   %-14s %s" % (c["sub"], names))
    if a.apply:
        print("applied to : %s" % a.apply)


if __name__ == "__main__":
    main()
