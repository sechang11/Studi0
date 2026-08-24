#!/usr/bin/env python3
"""studio/_tools/technique_routes.py - the technique library.

A scene template (studio/templates/) says WHAT a shot is: the beats, the mood, the genre.
This says HOW one was built - the rig, the compositing chain, the plate trick - for the
cases where a shot turned out to be a reusable TECHNIQUE rather than a one-off.

The rule it exists to serve: when something works and would work again, it gets written
down here with the shot itself attached, so the next film can use it without rebuilding it
and, more importantly, without rediscovering the traps. Every entry carries the gotcha that
cost the most time, because that is the part nobody writes down and everybody pays for
twice.

Routes: /api/technique/list          every technique, with its example take resolved
        /api/technique/<id>          one of them
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
STUDIO = os.path.dirname(HERE)
DIR = os.path.join(STUDIO, "techniques")
FILMS = os.path.join(STUDIO, "films")


def _resolve(t):
    """Attach the example take's video and poster, so the page can just play it."""
    ex = t.get("example") or {}
    film, shot, take = ex.get("film"), ex.get("shot"), ex.get("take")
    if not (film and shot):
        return t
    fj = os.path.join(FILMS, film, "film.json")
    if not os.path.exists(fj):
        t["example_missing"] = "no film %s" % film
        return t
    d = json.load(open(fj, encoding="utf-8"))
    sh = d.get("shots", {}).get(shot) or {}
    tk = next((x for x in sh.get("takes", []) if x["id"] == (take or sh.get("picked"))),
              None)
    if not tk:
        # the take was replaced since this was written - say so rather than 404 quietly
        t["example_missing"] = "take %s is gone from %s/%s" % (take, film, shot)
        return t
    t["example"] = dict(ex, video="/film/media/%s/%s" % (film, tk["file"]),
                        poster="/film/media/%s/%s" % (film, tk.get("poster", "")),
                        duration=tk.get("duration"), engine=tk.get("engine"),
                        shot_title=sh.get("title", ""), film_title=d.get("title", film))
    return t


def _all():
    if not os.path.isdir(DIR):
        return []
    out = []
    for f in sorted(os.listdir(DIR)):
        if f.endswith(".json"):
            out.append(_resolve(json.load(open(os.path.join(DIR, f), encoding="utf-8"))))
    return out


def listing():
    return {"techniques": _all()}, 200


def one(tid):
    p = os.path.join(DIR, "%s.json" % "".join(
        c for c in tid if c.isalnum() or c in "_-"))
    if not os.path.exists(p):
        return {"error": "no technique %r" % tid}, 404
    return _resolve(json.load(open(p, encoding="utf-8"))), 200
