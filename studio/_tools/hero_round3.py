#!/usr/bin/env python3
"""Lantern Night, third pass: the two empty shots go to the camera rig, the close-up gets its
words cut to the face alone and the prompt enhancer switched off.

The studio's own rule for an empty shot the engine keeps filling with people is "this shot
becomes the plate itself, moving slowly, with the rendered sound under it".  Its automatic path
crashed on the retake (fixed in film_routes today), and the sound it would have used was a
borrowed soundtrack that carried the engine's version of Terra's line (also fixed).  Here the
rule is applied by hand, through the same _render_take the studio uses, with the market's own
ambience from the first take of shot 010 as the bed.

    python3 studio/_tools/hero_round3.py
"""
import importlib.util
import json
import os
import sys
import time
import urllib.request

ROOT = os.path.expanduser("~/shared/comfy-studio")
STUDIO = os.path.join(ROOT, "studio")
API = "http://127.0.0.1:8777/api/film"
FID = "lantern-night"
for p in (os.path.join(ROOT, "scripts"), os.path.join(STUDIO, "_tools")):
    if p not in sys.path:
        sys.path.insert(0, p)


def api(path, body):
    req = urllib.request.Request(API + path, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req, timeout=120))


def jobs():
    return json.load(urllib.request.urlopen(API + "/jobs", timeout=60)).get("jobs") or []


def wait(jid, budget=2400, label=""):
    t0 = time.time()
    while time.time() - t0 < budget:
        time.sleep(8)
        for j in jobs():
            if j.get("id") == jid and j.get("state") not in ("running", "queued"):
                print("  %s %s: %s %s" % (label, jid, j.get("state"), (j.get("error") or "")[:200]), flush=True)
                for ln in j.get("log") or []:
                    print("     |", ln[:220], flush=True)
                return j
    print("  %s %s: TIMED OUT" % (label, jid), flush=True)
    return None


def quiet(budget=1800):
    t0 = time.time()
    while time.time() - t0 < budget:
        if not any(j.get("state") in ("running", "queued") for j in jobs()):
            return True
        time.sleep(8)
    return False


def load_routes():
    spec = importlib.util.spec_from_file_location("film_routes", os.path.join(STUDIO, "_tools", "film_routes.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def rig_takes():
    fr = load_routes()
    F = fr.F
    bed = os.path.join(STUDIO, "films", FID, "assets", "amb_market.m4a")
    assert os.path.exists(bed), "market ambience bed missing"
    made = {}
    for sid in ("010", "050"):
        f = F.load(FID)
        sh = f.shot(sid)
        try:
            from PIL import Image
            pw, ph = Image.open(fr._resolve_anchor_file(f, sid, None)).size
        except Exception:
            pw, ph = 1216, 832
        secs = float(sh.get("duration") or 4)
        sh["cam"] = {"rig": "still_push", "audio": bed,
                     "params": {"seconds": secs, "zoom_start": 1.0, "zoom_end": 1.12,
                                "win_w": pw, "win_h": ph, "cx": pw // 2, "cy": ph // 2}}
        f.save()
        jid = fr._job("make", film=FID, shot=sid)
        print("== rig take for %s (%dx%d window, %.0fs, push 12%%)" % (sid, pw, ph, secs), flush=True)
        tid = fr._render_take(jid, f, sh, "cam", 0)
        for ln in fr.JOBS[jid]["log"]:
            print("     |", ln[:220], flush=True)
        f = F.load(FID)
        sh = f.shot(sid)
        tk = next((t for t in sh.get("takes") or [] if t["id"] == tid), None)
        print("   take %s qc=%s" % (tid, "; ".join((tk or {}).get("qc") or [])[:400]), flush=True)
        made[sid] = tid
    return made


def main():
    quiet()
    made = rig_takes()
    # the close-up: words about the face only, three seconds, the enhancer off
    f = json.load(open(os.path.join(STUDIO, "films", FID, "film.json"), encoding="utf-8"))
    b = dict((f["shots"]["040"].get("beats") or [{}])[0])
    b.update({"framing": "close-up", "move": "static", "subject": "TERRA",
              "action": "smiles slowly; her eyes close for a moment and open again; lantern light glows on her "
                        "face and the camera holds a tight close-up on her face for the whole shot",
              "background": "soft lantern bokeh behind her and nothing else"})
    r = api("/editshot", {"film": FID, "shot": "040", "beats": [b], "duration": 3, "enhance": False,
                          "sfx": "the soft creak of lanterns overhead, the market murmur far away, no music"})
    print("  editshot 040 ->", r, flush=True)
    quiet()
    print("== make 040 (3 s, enhancer off)", flush=True)
    m = api("/make", {"film": FID, "shot": "040", "variants": 1})
    wait(m["job"], label="make 040")
    f = json.load(open(os.path.join(STUDIO, "films", FID, "film.json"), encoding="utf-8"))
    sh = f["shots"]["040"]
    for t in sh.get("takes") or []:
        print("   take %s%s qc=%s" % (t["id"], " PICKED" if t["id"] == sh.get("picked") else "",
                                      "; ".join(t.get("qc") or [])[:400]), flush=True)
    print("rig takes:", json.dumps(made), flush=True)
    print("ROUND3 DONE", flush=True)


if __name__ == "__main__":
    main()
