#!/usr/bin/env python3
"""Second half of the worked example: keep section J's three shots, finish, and report.

quickstart also proposed the studio's own five coverage shots (010-050) before the three the
guide describes (060-080), and makeall rendered all eight - useful as a test of auto-coverage on
the same anchor, but the guide's example is the three.  This removes the five, assembles the
three with the filmic look and the 2x master, and writes the strip and the numbers the guide
quotes.  Nothing is force-picked.
"""
import json
import os
import subprocess
import sys
import time
import urllib.request

API = "http://127.0.0.1:8777/api/film"
STUDIO = os.path.expanduser("~/shared/comfy-studio/studio")
OUT = os.path.join(STUDIO, "samples", "docs")
FID = sys.argv[1] if len(sys.argv) > 1 else "the-method---worked-example"
KEEP = ("060", "070", "080")


def api(path, body):
    req = urllib.request.Request(API + path, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req, timeout=120))


def jobs():
    return json.load(urllib.request.urlopen(API + "/jobs", timeout=60)).get("jobs") or []


def wait(jid, budget=1800):
    t0 = time.time()
    while time.time() - t0 < budget:
        time.sleep(8)
        for j in jobs():
            if j.get("id") == jid and j.get("state") not in ("running", "queued"):
                return j
    return None


def film():
    return json.load(open(os.path.join(STUDIO, "films", FID, "film.json"), encoding="utf-8"))


f = film()
if any(j.get("state") in ("running", "queued") for j in jobs()):
    sys.exit("a film job is still running - wait for it")
extra = [sid for sid in f["shots"] if sid not in KEEP]
print("auto-coverage shots the studio proposed (kept out of the example):")
for sid in extra:
    sh = f["shots"][sid]
    tk = next((t for t in sh.get("takes") or [] if t["id"] == sh.get("picked")), None)
    idn = (tk or {}).get("identity") or {}
    print("  %s %-26s picked=%s identity=%s qc=%s" % (
        sid, (sh.get("title") or "")[:26], bool(tk), [idn.get("start"), idn.get("end")],
        ((tk or {}).get("qc") or [])[:2]))
    api("/delete", {"film": FID, "shot": sid})

f = film()
report = {"film": FID, "shots": []}
ok = True
for sid in KEEP:
    sh = f["shots"][sid]
    tk = next((t for t in sh.get("takes") or [] if t["id"] == sh.get("picked")), None)
    row = {"shot": sid, "title": sh.get("title"), "anchor": sh.get("anchor"),
           "takes": len(sh.get("takes") or []), "picked": bool(tk)}
    if tk:
        idn = tk.get("identity") or {}
        row.update({"engine": tk.get("engine"), "duration": tk.get("duration"),
                    "identity": [idn.get("start"), idn.get("end")],
                    "verdict": [idn.get("verdict_start"), idn.get("verdict_end")],
                    "qc": tk.get("qc") or []})
    else:
        ok = False
        row["faults_on_takes"] = [t.get("qc") for t in sh.get("takes") or []][:3]
    report["shots"].append(row)
    print("  %s %-14s %s" % (sid, sh.get("title"), json.dumps(row, ensure_ascii=False)[:300]))

if ok:
    a = api("/assemble", {"film": FID, "music": False, "grade": "filmic", "upscale": True})
    j = wait(a["job"])
    print("assemble:", (j or {}).get("state"), (j or {}).get("error") or "")
    final = os.path.join(STUDIO, "films", FID, "assets", "film.mp4")
    if os.path.exists(final):
        r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-count_frames",
                            "-show_entries", "stream=width,height,nb_read_frames",
                            "-of", "csv=p=0", final], capture_output=True, text=True)
        report["film_mp4"] = r.stdout.strip()
        frames = sum(int(round((s.get("duration") or 0) * 24)) for s in report["shots"])
        report["frames_expected_from_takes"] = frames
        d = "/tmp/method_strip"
        subprocess.run(["rm", "-rf", d]); os.makedirs(d)
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", final, "-vf", "fps=1,scale=256:-2",
                        os.path.join(d, "f%03d.png")])
        strip = os.path.join(OUT, "method_example_strip.jpg")
        subprocess.run([os.path.expanduser("~/ComfyUI/venv/bin/python3"), "-c",
                        "from PIL import Image;import sys,os\n"
                        "d=sys.argv[1];fs=sorted(os.listdir(d));ims=[Image.open(os.path.join(d,f)).convert('RGB') for f in fs]\n"
                        "w,h=ims[0].size;S=Image.new('RGB',(w*len(ims),h),(16,16,20))\n"
                        "[S.paste(im,(i*w,0)) for i,im in enumerate(ims)];S.save(sys.argv[2],quality=86);print(S.size)",
                        d, strip])
        report["strip"] = os.path.relpath(strip, STUDIO)
        print("film.mp4:", report["film_mp4"], "| strip:", strip)
else:
    print("NOT assembled: a shot has no clean take; the example is not force-picked")
json.dump(report, open(os.path.join(OUT, "method_example.json"), "w"), indent=1)
print("FINISH EXAMPLE DONE")
