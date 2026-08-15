"""studio/cards.py - the one card loader, and the schema each kind is held to.

    import cards
    libs = cards.load_all(GROUPS)          # drop-in for roll.load_libs's shape
    probs = cards.validate_all()           # [(sev, kind, id, message)]
    cards.dialect_of(char_card)            # {"tags"}, {"prose"}, or both
    cards.legal(char_card, engine)         # (ok, reason) - the wave-4 guard
    cards.require_voice(libs, vid)         # raises on a blocked voice

WHY A LOADER AND NOT TWENTY GLOBS (ARCHITECTURE Phase 1). Every card consumer read its
directory directly, so every rule about what a card means lived wherever someone last
needed it: the wear ladder got flattened because nothing knew it was a ladder, wave 4 lost
82 frames because nothing knew a character card is written in one prompt dialect, and the
blocked-voice rule is enforced in each picker separately. One loader means one place where
a card's shape and meaning are stated - and refused.

THE SCHEMA IS MEASURED, NOT ASPIRATIONAL. Required fields below are the fields that are
ALREADY universal on every card of that kind (measured across all 609 before writing
this); types come from the same survey, with None permitted exactly where the data already
uses it (a voice's `engine`, a motion's `needs`). A schema that demands what the data does
not have would declare the whole library broken on day one and teach everyone to ignore
it.

SEVERITY. `error` means a consumer will misbehave: missing id, a style without an engine,
a character with no usable dialect, a wear ladder that is not a list, a LoRA without its
base model. `warn` means the card is poorer than it should be: unknown status, a short
ladder, missing provenance where its kind normally has one. The Phase 1 gate is zero
errors; warns are backlog.
"""
import glob
import json
import os

STUDIO = os.path.dirname(os.path.abspath(__file__))

S, L, D, N = str, list, dict, (int, float)
NS = (str, type(None))          # nullable string - measured in the data, not invented

# Required fields per kind = the measured universal core. `types` constrains any field it
# names, required or not. `statuses` is per kind because kinds genuinely differ: every
# emotion is "partial" by design, voices use "blocked" as a hard rule.
KINDS = {
    # Every kind may carry `evidence` (Phase 4) - the dated verdict dict written by
    # cards.stamp - and `evidence_history`. Typed globally below in validate_card rather
    # than repeated in twenty kind entries.
    "styles": {
        "required": {"id": S, "name": S, "engine": S, "status": S, "compose": S,
                     "family": S, "prose": S, "negative_add": S},
        "types": {"tags": S, "self_contained": bool, "words": S, "verdict": S},
        "statuses": {"ready", "weak", "unavailable"},
        "enums": {"engine": {"anime", "qwen", "flux2", "either"},
                  "compose": {"safe", "replaces", "injects", "inert"}},
    },
    "places": {
        "required": {"id": S, "name": S, "status": S, "family": S, "scale": S,
                     "prose": S, "tags": S, "time_of_day": L},
        "statuses": {"ready", "weak", "unavailable"},
    },
    "characters": {
        "required": {"id": S, "name": S, "status": S, "desc": S, "tags": S, "prose": S,
                     "wear_tags": L, "provenance": S},
        "types": {"voice": NS, "sheet": NS, "lora": S, "base_tags": S},
        "statuses": {"ready", "draft", "blocked"},
    },
    "emotions": {
        "required": {"id": S, "status": S, "face": S, "eyes": S, "mouth": S, "body": S},
        "statuses": {"partial", "ready"},
    },
    # Statuses below are MEASURED per kind, not wished. weather/lighting/soundscapes/
    # layers are wholly "partial" - like emotions, that is their designed state (tags that
    # render today, richer behaviour promised). The first draft imposed {ready, weak} on
    # them and warned on every single card, which is a checker training people to ignore
    # it.
    "looks": {"required": {"id": S, "status": S, "tags": S, "grade": S},
              "statuses": {"ready", "partial"}},
    "lighting": {"required": {"id": S, "status": S}, "statuses": {"partial", "ready"}},
    "weather": {"required": {"id": S, "status": S, "tags": S},
                "statuses": {"partial", "ready"}},
    "motions": {
        "required": {"id": S, "name": S, "status": S, "family": S, "text": S,
                     "grammar": S, "verdict": S},
        "types": {"needs": NS},
        "statuses": {"ready", "weak", "unavailable"},
    },
    "cameras": {"required": {"id": S, "status": S, "verdict": S},
                "types": {"filter": NS},
                "statuses": {"ready", "unavailable"}},
    # tier is a DICT - {"picture": "post", "audio": "none"} - on all twelve cards. The
    # first draft of this schema assumed a string and declared every transition broken;
    # when all twelve agree, that is the convention and the schema submits to it.
    "transitions": {"required": {"id": S, "status": S, "verdict": S, "tier": D},
                    "types": {"filter": NS},
                    "statuses": {"ready", "partial", "needs_authoring"}},
    "shots": {"required": {"id": S, "status": S, "desc": S},
              "statuses": {"ready"}},
    "sequences": {"required": {"id": S, "kind": S, "beats": L, "seconds": N,
                               "provenance": S},
                  "statuses": set()},
    "loras": {
        "required": {"id": S, "name": S, "status": S, "kind": S, "file": S,
                     "base_model": S, "trigger": S},
        "types": {"engine": NS},
        "enums": {"kind": {"character", "style", "speedup", "edit", "utility",
                           "experiment"}},
        "statuses": {"ready", "untested", "weak", "unavailable"},
    },
    "voices": {
        "required": {"id": S, "name": S, "status": S, "file": S, "engine": S},
        "statuses": {"ready", "unsupported", "blocked"},
    },
    "cues": {"required": {"id": S, "status": S, "tags": S},
             "statuses": {"ready", "partial"}},
    "sfx": {"required": {"id": S, "status": S, "prompt": S, "seconds": N},
            "statuses": {"ready", "partial"}},
    "soundscapes": {"required": {"id": S, "status": S}, "statuses": {"partial", "ready"}},
    "pacing": {"required": {"id": S, "status": S, "rhythm": S}, "statuses": {"ready"}},
    "layers": {"required": {"id": S, "status": S}, "statuses": {"partial", "ready"}},
    "domains": {"required": {"id": S, "name": S, "workflow": S, "nodes": D},
                "statuses": set()},
    # Phase 5: a model is a card, earned by content - dialect, measured strengths, size,
    # reachability. Rebuilt from disk by _tools/model_cards.py; measured text is keyed
    # by filename there and survives rescans.
    "models": {
        "required": {"id": S, "name": S, "file": S, "folder": S, "status": S,
                     "role": S, "desc": S},
        "types": {"engine": NS, "dialect": NS, "size_gb": N, "workflows": L,
                  "reachable": bool, "strip": NS, "strengths": S, "weaknesses": S},
        "statuses": {"ready", "untested", "weak", "unavailable"},
    },
}


def load(kind):
    """Every card of a kind, keyed by filename stem - byte-for-byte what load_libs read.

    Underscore files (`_control`, `_capability`) ARE included, because roll.load_libs
    included them and downstream code (drawable_styles) skips them by name. A loader that
    silently dropped them would change behaviour while claiming to be a drop-in.
    Validation, separately, skips them: they are templates, not cards.
    """
    d = os.path.join(STUDIO, kind)
    out = {}
    if not os.path.isdir(d):
        return out
    for fn in sorted(os.listdir(d)):
        if not fn.endswith(".json"):
            continue
        try:
            with open(os.path.join(d, fn), encoding="utf-8") as f:
                out[fn[:-5]] = json.load(f)
        except Exception:
            # load_libs swallowed these too; validate_all() reports them as errors, so the
            # silence here is not silence overall.
            pass
    return out


def load_all(groups):
    """The libs dict, in exactly roll.load_libs's shape, for the given group list."""
    return {g: load(g) for g in groups}


def dialect_of(card):
    """Which prompt language(s) a card actually carries. Empty strings carry nothing.

    This is the wave-4 lesson as a function: a character whose tags are "" contributes
    NOTHING on the tag engine, so the dialect is what is non-empty, not what keys exist.
    """
    out = set()
    if str(card.get("tags") or "").strip():
        out.add("tags")
    if str(card.get("prose") or "").strip():
        out.add("prose")
    return out


ENGINE_DIALECT = {"anime": "tags", "qwen": "prose", "flux2": "prose"}


def engines_for(card):
    """The engines this character can actually appear on."""
    d = dialect_of(card)
    return {e for e, need in ENGINE_DIALECT.items() if need in d}


def legal(char_card, engine):
    """(ok, reason). False means the character would be silently deleted on this engine."""
    if engine == "either":
        return True, ""
    need = ENGINE_DIALECT.get(engine)
    if need is None:
        return False, "unknown engine %r" % engine
    if need in dialect_of(char_card):
        return True, ""
    return False, ("%s is written in %s and engine %r reads %s - the character would "
                   "contribute nothing and be silently deleted from the frame"
                   % (char_card.get("id", "the character"),
                      "/".join(sorted(dialect_of(char_card))) or "nothing",
                      engine, need))


def require_voice(vid, libs=None):
    """The voice card, or a refusal. THE one enforcement point for blocked voices.

    Four packs are clones of real people and marked blocked; every picker filters them for
    display, but display filters are not enforcement - a hand-written job bypasses them
    all. This is where a blocked voice actually cannot pass. Callers without a libs dict
    in hand (render_job) omit it and the voices load on demand.
    """
    if libs is None:
        libs = {"voices": load("voices")}
    vc = (libs.get("voices") or {}).get(vid)
    if vc is None:
        raise RuntimeError("no such voice: %s" % vid)
    if vc.get("status") == "blocked":
        raise RuntimeError("voice %s is blocked (clone of a real person)" % vid)
    return vc


EVIDENCE_VERDICTS = ("MEASURED", "JUDGED", "UNVERIFIED")


def stamp(kind, cid, verdict, method, note="", when=None):
    """Write a dated evidence verdict onto a card, preserving the previous one in
    evidence_history. THE one writer (Phase 4) - checkers call this instead of each
    inventing a field, which is how `verdict` came to mean four different things.

    verdict: MEASURED (an instrument computed it), JUDGED (someone looked at pixels),
    UNVERIFIED (the honest default). There is no PREDICTED - every predicted verdict in
    this project that was later checked was wrong.
    """
    import time
    if verdict not in EVIDENCE_VERDICTS:
        raise ValueError("verdict must be one of %s" % (EVIDENCE_VERDICTS,))
    path = os.path.join(STUDIO, kind, cid + ".json")
    with open(path, encoding="utf-8") as f:
        card = json.load(f)
    old = card.get("evidence")
    if old:
        hist = card.get("evidence_history") or []
        hist.append(old)
        card["evidence_history"] = hist[-8:]
    card["evidence"] = {"verdict": verdict, "method": str(method)[:120],
                        "date": when or time.strftime("%Y-%m-%d"),
                        "note": str(note)[:300]}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(card, f, indent=2, ensure_ascii=False)
        f.write("\n")
    return card["evidence"]


def evidence_of(card):
    """The card's evidence dict, or an UNVERIFIED placeholder if nothing ever checked
    it. Never None, so readers need no guard."""
    e = card.get("evidence")
    if isinstance(e, dict) and e.get("verdict") in EVIDENCE_VERDICTS and e.get("date"):
        return e
    return {"verdict": "UNVERIFIED", "method": "", "date": "", "note": ""}


def validate_card(kind, cid, card):
    """[(sev, message)] for one card. error = a consumer will misbehave."""
    spec = KINDS.get(kind)
    if spec is None:
        return [("warn", "kind %r has no schema yet" % kind)]
    probs = []
    if not isinstance(card, dict):
        return [("error", "not a JSON object")]
    e = card.get("evidence")
    if e is not None and (not isinstance(e, dict)
                          or e.get("verdict") not in EVIDENCE_VERDICTS
                          or not e.get("date")):
        probs.append(("error", "evidence must be a dict with a verdict in %s and a "
                               "date" % (EVIDENCE_VERDICTS,)))
    if card.get("id") != cid:
        probs.append(("error", "id %r does not match filename %r" % (card.get("id"), cid)))
    for field, typ in spec.get("required", {}).items():
        if field not in card:
            probs.append(("error", "missing required field %r" % field))
        elif not isinstance(card[field], typ):
            probs.append(("error", "field %r is %s, expected %s"
                          % (field, type(card[field]).__name__,
                             getattr(typ, "__name__", str(typ)))))
    for field, typ in spec.get("types", {}).items():
        if field in card and not isinstance(card[field], typ):
            probs.append(("error", "field %r is %s, expected %s"
                          % (field, type(card[field]).__name__, str(typ))))
    for field, allowed in spec.get("enums", {}).items():
        v = card.get(field)
        if v is not None and v not in allowed:
            probs.append(("error", "field %r is %r, expected one of %s"
                          % (field, v, sorted(allowed))))
    sts = spec.get("statuses")
    if sts and card.get("status") not in sts:
        probs.append(("warn", "status %r is not one of %s for this kind"
                      % (card.get("status"), sorted(sts))))

    if kind == "characters":
        if not dialect_of(card):
            probs.append(("error", "no usable dialect: both tags and prose are empty - "
                                   "this character cannot appear on any engine"))
        wt = card.get("wear_tags")
        if isinstance(wt, list) and 0 < len(wt) < 5:
            probs.append(("warn", "wear ladder has %d rungs; the convention is 5, "
                                  "clean through ruined" % len(wt)))
    if kind == "styles" and not str(card.get("prose") or "").strip() \
            and not str(card.get("tags") or "").strip():
        probs.append(("error", "style has neither prose nor tags - it can draw nothing"))
    return probs


def validate_all():
    """[(sev, kind, id, message)] across every kind. Underscore files are templates."""
    out = []
    for kind in KINDS:
        d = os.path.join(STUDIO, kind)
        if not os.path.isdir(d):
            continue
        for f in sorted(glob.glob(os.path.join(d, "*.json"))):
            stem = os.path.basename(f)[:-5]
            if stem.startswith("_"):
                continue
            try:
                card = json.load(open(f, encoding="utf-8"))
            except Exception as e:
                out.append(("error", kind, stem, "unparseable: %s" % str(e)[:80]))
                continue
            for sev, msg in validate_card(kind, stem, card):
                out.append((sev, kind, stem, msg))
    return out
