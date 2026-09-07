#!/usr/bin/env python3
"""Build docs/METHOD.md section J through the studio's own routes, and see whether it holds.

A template whose worked example was never run is a belief with a diagram.  This builds the
example exactly as a person would in the editor - quickstart a film with Terra at the forest
shrine, one scene, three one-beat shots, make them, pick by the studio's own QC, finish with the
filmic look and the 2x master - and reports what came out.  It never force-picks: a shot the QC
faulted stays unpicked and is reported, because rule 13 applies to the example too.

    python3 build_method_example.py            # ~30-40 minutes on the card
"""
import json
import os
import subprocess
import sys
import time
import urllib.request

API = "http://127.0.0.1:8777/api/film"
ROOT = os.path.expanduser("~/shared/comfy-studio")
STUDIO = os.path.join(ROOT, "studio")
OUT = os.path.join(STUDIO, "samples", "docs")


def api(path, body):
    req = urllib.request.Request(API + path, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req, timeout=120))


def jobs():
    return json.load(urllib.request.urlopen(API + "/jobs", timeout=60)).get("jobs") or []


def wait(jid, budget=3600, label=""):
    t0 = time.time()
    while time.time() - t0 < budget:
        time.sleep(8)
        for j in jobs():
            if j.get("id") == jid and j.get("state") not in ("running", "queued"):
                print("  %s %s: %s %s" % (label, jid, j.get("state"),
                                          (j.get("error") or "")[:160]), flush=True)
                return j
    print("  %s %s: TIMED OUT" % (label, jid), flush=True)
    return None


def film(fid):
    return json.load(open(os.path.join(STUDIO, "films", fid, "film.json"), encoding="utf-8"))


def main():
    os.makedirs(OUT, exist_ok=True)
    print("== quickstart: Terra at the forest shrine, dawn", flush=True)
    q = api("/quickstart", {"title": "The Method - worked example", "look": "anime",
                            "characters": ["terra"], "place": "forest-shrine",
                            "plate": "dawn_wide", "scene_title": "the shrine at dawn"})
    fid, scid, ajob = q["id"], q["scene"], q.get("job")
    f = film(fid)
    cast_id = next((k for k, v in (f.get("cast") or {}).items()
                    if (v or {}).get("foundry") == "terra"), None) or next(iter(f["cast"]))
    print("  film %s scene %s cast id %r anchor job %s" % (fid, scid, cast_id, ajob), flush=True)

    api("/editscene", {"film": fid, "scene": scid, "time_of_day": "dawn",
                       "ambience": "wind in the cedars, gravel underfoot, a single bell far off",
                       "cast_present": [cast_id], "music": ""})
    api("/edit", {"film": fid, "negative": "lowres, bad anatomy, extra limbs, text, watermark, nsfw"})
    if ajob:
        wait(ajob, label="scene anchor")

    shots = [
        ("the arrival", 6, "scene", {
            "framing": "wide shot", "move": "static", "subject": cast_id,
            "action": "walks in from the left along the stone path and stops at the foot of "
                      "the shrine steps",
            "background": "wind moves the cedar branches; gravel underfoot; a single bell far off",
            "dialogue": {"char": "", "line": "", "delivery": ""}, "transition_in": ""},
         "wind in the cedars, gravel underfoot, a single distant bell, no music"),
        ("the look up", 5, "scene", {
            "framing": "medium shot", "move": "slow push in", "subject": cast_id,
            "action": "looks up at the shrine gate, her hand resting on the rope rail",
            "background": "the same wind, closer; the bell again",
            "dialogue": {"char": cast_id, "line": "So this is where he left it.",
                         "delivery": "quiet"}, "transition_in": ""},
         "wind, closer; the bell again, no music"),
        ("the decision", 4, "prev_last", {
            "framing": "close-up", "move": "handheld, a faint float", "subject": cast_id,
            "action": "closes her eyes for a breath, opens them, and starts up the steps",
            "background": "the wind dropping away",
            "dialogue": {"char": "", "line": "", "delivery": ""}, "transition_in": ""},
         "her breath, the wind dropping away, no music"),
    ]
    ids = []
    for title, secs, anchor, beat, sfx in shots:
        s = api("/shot", {"film": fid, "scene": scid, "template": ""})
        api("/editshot", {"film": fid, "shot": s["id"], "title": title, "duration": secs,
                          "anchor": anchor, "beats": [beat], "sfx": sfx})
        ids.append(s["id"])
        print("  shot %s %-14s %ds anchor=%s" % (s["id"], title, secs, anchor), flush=True)

    print("== make every shot (the studio picks a clean take itself)", flush=True)
    m = api("/makeall", {"film": fid, "assemble": False})
    wait(m["job"], budget=3600, label="makeall")

    f = film(fid)
    report = {"film": fid, "shots": []}
    ok = True
    for sid in ids:
        sh = f["shots"][sid]
        tk = next((t for t in sh.get("takes") or [] if t["id"] == sh.get("picked")), None)
        row = {"shot": sid, "title": sh.get("title"), "takes": len(sh.get("takes") or []),
               "picked": bool(tk)}
        if tk:
            idn = tk.get("identity") or {}
            row.update({"engine": tk.get("engine"), "duration": tk.get("duration"),
                        "identity": [idn.get("start"), idn.get("end")],
                        "verdict": [idn.get("verdict_start"), idn.get("verdict_end")],
                        "qc": tk.get("qc") or []})
        else:
            ok = False
            row["unpicked_faults"] = [t.get("qc") for t in sh.get("takes") or []][:3]
        report["shots"].append(row)
        print("  %s %-14s %s" % (sid, sh.get("title"), json.dumps(row, ensure_ascii=False)[:260]),
              flush=True)

    if ok:
        print("== finish: filmic, 2x master", flush=True)
        a = api("/assemble", {"film": fid, "music": False, "grade": "filmic", "upscale": True})
        wait(a["job"], budget=1800, label="assemble")
        final = os.path.join(STUDIO, "films", fid, "assets", "film.mp4")
        if os.path.exists(final):
            r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-count_frames",
                                "-show_entries", "stream=width,height,nb_read_frames",
                                "-of", "csv=p=0", final], capture_output=True, text=True)
            report["film_mp4"] = r.stdout.strip()
            strip = os.path.join(OUT, "method_example_strip.jpg")
            d = "/tmp/method_strip"
            subprocess.run(["rm", "-rf", d]); os.makedirs(d)
            subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", final, "-vf", "fps=1,scale=256:-2",
                            os.path.join(d, "f%03d.png")])
            fs = sorted(os.listdir(d))
            subprocess.run([os.path.expanduser("~/ComfyUI/venv/bin/python3"), "-c",
                            "from PIL import Image;import sys,os\n"
                            "d=sys.argv[1];fs=sorted(os.listdir(d));ims=[Image.open(os.path.join(d,f)).convert('RGB') for f in fs]\n"
                            "w,h=ims[0].size;S=Image.new('RGB',(w*len(ims),h),(16,16,20))\n"
                            "[S.paste(im,(i*w,0)) for i,im in enumerate(ims)];S.save(sys.argv[2],quality=86);print(S.size)",
                            d, strip])
            report["strip"] = os.path.relpath(strip, STUDIO)
            print("  film.mp4:", report["film_mp4"], "| strip:", strip, flush=True)
    else:
        print("== NOT assembled: a shot has no clean take - the example does not get force-picked",
              flush=True)
    json.dump(report, open(os.path.join(OUT, "method_example.json"), "w"), indent=1)
    print("METHOD EXAMPLE DONE", flush=True)


if __name__ == "__main__":
    main()
