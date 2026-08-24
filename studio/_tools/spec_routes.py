#!/usr/bin/env python3
"""studio/_tools/spec_routes.py - the shot-spec editor's back end.

A film's shots are already on a timeline in /film. What was missing is the other half of
each shot: the promises it has to keep. This serves those as ENGLISH, editable in the
browser, and writes them straight back to studio/shotspecs/<film>/<shot>.md.

The .md is the source of truth. The .json beside it is regenerated on every save, because
the checker reads JSON and a person should never have to.

LOCKING. A locked shot records the take that was picked when it was locked. `save` refuses
to touch it, and the checker FAILS if the picked take has since changed - which is the
actual protection, because the way a finished shot gets lost is not someone editing its
spec, it is someone quietly re-picking a take underneath it.

Routes (GET):   /api/spec/films
                /api/spec/tree/<film>
                /api/spec/md/<film>/<shot>
                /api/spec/check/<film>
        (POST): /api/spec/save    {film, shot, md}
                /api/spec/new     {film, shot, title}
"""
import json, os, re, time

HERE = os.path.dirname(os.path.abspath(__file__))
STUDIO = os.path.dirname(HERE)
SPECS = os.path.join(STUDIO, "shotspecs")
FILMS = os.path.join(STUDIO, "films")


def _mod(name, path):
    import importlib.util
    sp = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(m)
    return m


def _specmd():
    return _mod("specmd", os.path.join(HERE, "specmd.py"))


def _shotspec():
    return _mod("shotspec_mod", os.path.join(HERE, "shotspec.py"))


# ── reads ───────────────────────────────────────────────────────────────────────────

def films():
    """Every film, flagged with whether it has specs yet - so the editor can offer to
    start a set rather than looking empty."""
    out = []
    if os.path.isdir(FILMS):
        for f in sorted(os.listdir(FILMS)):
            fj = os.path.join(FILMS, f, "film.json")
            if not os.path.exists(fj):
                continue
            d = json.load(open(fj, encoding="utf-8"))
            sd = os.path.join(SPECS, f)
            n = len([x for x in os.listdir(sd) if x.endswith(".md")]) \
                if os.path.isdir(sd) else 0
            out.append({"id": f, "title": d.get("title", f),
                        "shots": len(d.get("shots", {})), "specs": n})
    return {"films": out}, 200


def tree(film):
    """The film's shots in scene order, with everything the timeline needs: poster,
    duration, engine, and whether a spec exists."""
    fj = os.path.join(FILMS, film, "film.json")
    if not os.path.exists(fj):
        return {"error": "no such film"}, 404
    d = json.load(open(fj, encoding="utf-8"))
    sd = os.path.join(SPECS, film)
    out = []
    for sc in d.get("scenes", []):
        for shid in sc.get("shots", []):
            sh = d["shots"].get(shid) or {}
            take = next((t for t in sh.get("takes", [])
                         if t["id"] == sh.get("picked")), None)
            mdp = os.path.join(sd, shid + ".md")
            spec = {}
            if os.path.exists(os.path.join(sd, shid + ".json")):
                spec = json.load(open(os.path.join(sd, shid + ".json"),
                                      encoding="utf-8"))
            out.append({
                "shot": shid, "scene": sc["id"], "scene_title": sc.get("title", ""),
                "title": sh.get("title", ""),
                "duration": (take or {}).get("duration", sh.get("duration", 0)),
                "engine": (take or {}).get("engine", ""),
                "poster": (take or {}).get("poster", ""),
                # the picked take's video, so the editor can play the shot next to the
                # words that describe it - reading a promise and watching it break is
                # the whole point
                "video": (take or {}).get("file", ""),
                "takes": [{"id": t["id"], "engine": t.get("engine", ""),
                           "duration": t.get("duration", 0),
                           "file": t.get("file", ""), "poster": t.get("poster", "")}
                          for t in sh.get("takes", []) if t.get("file")],
                "has_spec": os.path.exists(mdp),
                "n_invariants": len(spec.get("invariants", [])),
                "n_flair": len(spec.get("flair", spec.get("flare", []))),
                "locked": bool(spec.get("locked")),
                "locked_take": spec.get("locked_take", ""),
                "picked": sh.get("picked", ""),
                "drifted": bool(spec.get("locked")) and
                           spec.get("locked_take") != sh.get("picked"),
            })
    return {"film": film, "title": d.get("title", film), "shots": out,
            "runtime": round(sum(s["duration"] for s in out), 2)}, 200


def md(film, shot):
    p = os.path.join(SPECS, film, shot + ".md")
    if os.path.exists(p):
        return {"md": open(p, encoding="utf-8").read(), "exists": True}, 200
    # no spec yet: hand back a filled-in skeleton rather than a blank page
    t, code = tree(film)
    title = next((s["title"] for s in t.get("shots", []) if s["shot"] == shot), "")
    return {"exists": False, "md": _specmd().skeleton(shot, title)}, 200


def check(film):
    ss = _shotspec()
    import io, contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        try:
            bad = ss.check(film)
        except Exception as e:
            return {"error": str(e)[:300]}, 500
    return {"report": buf.getvalue(), "problems": bad}, 200


# ── writes ──────────────────────────────────────────────────────────────────────────

def _spec_json(film, shot):
    p = os.path.join(SPECS, film, shot + ".json")
    return (json.load(open(p, encoding="utf-8")) if os.path.exists(p) else {}), p


def lock(data):
    """Freeze a shot. Records WHICH take was picked at the moment of locking, so the
    checker can tell the difference between 'still the shot you approved' and 'same spec,
    different film'."""
    film = re.sub(r"[^a-z0-9_-]", "", str(data.get("film", "")))
    shot = re.sub(r"[^A-Za-z0-9_-]", "", str(data.get("shot", "")))
    want = bool(data.get("locked", True))
    d, p = _spec_json(film, shot)
    if not d:
        return {"error": "no spec for %s/%s - save one first" % (film, shot)}, 404
    fj = os.path.join(FILMS, film, "film.json")
    picked = ""
    if os.path.exists(fj):
        picked = (json.load(open(fj, encoding="utf-8"))["shots"]
                  .get(shot, {}) or {}).get("picked", "")
    if want:
        d["locked"] = True
        d["locked_take"] = picked
        d["locked_at"] = time.strftime("%Y-%m-%d %H:%M")
    else:
        d.pop("locked", None); d.pop("locked_take", None); d.pop("locked_at", None)
    json.dump(d, open(p, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    return {"ok": True, "locked": want, "locked_take": picked}, 200


def save(data):
    film = re.sub(r"[^a-z0-9_-]", "", str(data.get("film", "")))
    shot = re.sub(r"[^A-Za-z0-9_-]", "", str(data.get("shot", "")))
    if not film or not shot:
        return {"error": "film and shot required"}, 400
    cur, _ = _spec_json(film, shot)
    if cur.get("locked") and not data.get("force"):
        return {"error": "shot %s is LOCKED (since %s). Unlock it to edit."
                         % (shot, cur.get("locked_at", "?"))}, 409
    d = os.path.join(SPECS, film)
    os.makedirs(d, exist_ok=True)
    text = data.get("md", "")
    open(os.path.join(d, shot + ".md"), "w", encoding="utf-8").write(text)
    sm = _specmd()
    parsed = sm.parse_md(text)
    warn = sm.write_json(d, shot, parsed)
    return {"ok": True, "invariants": len(parsed["invariants"]),
            "flair": len(parsed["flair"]), "promoted": parsed.get("_promoted", 0),
            "warnings": warn}, 200


def new(data):
    film = re.sub(r"[^a-z0-9_-]", "", str(data.get("film", "")))
    shot = re.sub(r"[^A-Za-z0-9_-]", "", str(data.get("shot", "")))
    if not film or not shot:
        return {"error": "film and shot required"}, 400
    return save({"film": film, "shot": shot,
                 "md": _specmd().skeleton(shot, data.get("title", ""))})
