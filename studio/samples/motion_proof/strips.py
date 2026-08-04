#!/usr/bin/env python3
"""strips.py - pull frame strips off MOTION PROOF so a human can LOOK at every beat.

Numbers rank candidates; they do not decide. A previous wave's stability metric scored an
anime control best in its sweep while the subject's hair had covered her face and her eyes
were closed. So this writes strips first and prints the numbers beside them, and the
verdict is written from the strips.

    python3 studio/samples/motion_proof/strips.py            # the film
    python3 studio/samples/motion_proof/strips.py --old      # the old-constant A/B pairs
"""
import json, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
os.environ.setdefault("COMFY_ROOT", os.path.expanduser("~/ComfyUI"))
os.environ.setdefault("COMFY_HOST", "127.0.0.1:8188")
from analyze_shots import motion            # noqa: E402
from epic import COMFY                      # noqa: E402

FILM = os.path.join(ROOT, "studio", "movies", "motion-proof.json")
OUT = f"{COMFY}/output/claude-generated/12-shorts/motion-proof"
N = 8                                       # frames per strip


def nframes(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-count_frames", "-select_streams",
                        "v:0", "-show_entries", "stream=nb_read_frames", "-of",
                        "csv=p=0", path], capture_output=True, text=True)
    try:
        return int((r.stdout or "0").strip().strip(","))
    except ValueError:
        return 0


def strip(src, dst, cols=4, w=480, crop=None):
    n = nframes(src)
    if n < 2:
        return 0
    picks = [round(i * (n - 1) / (N - 1)) for i in range(N)]
    sel = "+".join("eq(n\\,%d)" % p for p in picks)
    vf = "select='%s'" % sel
    if crop:
        vf += ",crop=%s" % crop
    vf += ",scale=%d:-1,tile=%dx%d" % (w, cols, -(-N // cols))
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", src, "-vf", vf,
                    "-frames:v", "1", "-fps_mode", "passthrough", dst],
                   check=True)
    return n


def drift(src):
    """first-to-last-frame difference: how far the picture has walked by the end."""
    n = nframes(src)
    if n < 2:
        return 0.0
    for i, f in ((0, f"{HERE}/_d0.png"), (n - 1, f"{HERE}/_d1.png")):
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", src, "-vf",
                        "select='eq(n\\,%d)',scale=320:-2" % i, "-frames:v", "1",
                        "-fps_mode", "passthrough", f], check=True)
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", f"{HERE}/_d0.png", "-i",
                        f"{HERE}/_d1.png", "-lavfi",
                        "[0:v][1:v]blend=all_mode=difference,signalstats,"
                        "metadata=print:key=lavfi.signalstats.YAVG",
                        "-f", "null", "-"], capture_output=True, text=True)
    import re
    v = re.findall(r"YAVG=([-+0-9.eE]+)", r.stderr or "")
    return float(v[-1]) if v else 0.0


def main():
    old = "--old" in sys.argv
    film = json.load(open(FILM, encoding="utf-8"))
    sub = "_old" if old else "clips"
    dest = f"{HERE}/{'old' if old else 'wide'}"
    os.makedirs(dest, exist_ok=True)
    rows = []
    for i, b in enumerate(film["beats"]):
        src = f"{OUT}/{sub}/{b['id']}_00001_.mp4"
        if not os.path.exists(src):
            continue
        short = b["id"].replace("after_the_party_", "")
        n = strip(src, f"{dest}/{i:02d}_{short}.png")
        m, sd = motion(src)
        rows.append((i, short, b["template"], n, m, sd, drift(src),
                     b["motion"] if not old else "Slow deliberate movement only.",
                     b.get("motion_src", "")))
    print("%-3s %-24s %-10s %5s %8s %8s %8s" %
          ("i", "beat", "template", "frms", "motion", "sd", "drift"))
    for r in rows:
        print("%-3d %-24s %-10s %5d %8.3f %8.3f %8.3f" % r[:7])
        print("      %s" % r[7])
        if r[8]:
            print("      src: %s" % r[8])
    json.dump([dict(zip(("i", "beat", "template", "frames", "motion_mean",
                         "motion_sd", "drift", "prompt", "src"), r)) for r in rows],
              open(f"{HERE}/{'old' if old else 'new'}_results.json", "w"), indent=1)
    print("\nstrips -> %s" % dest)


if __name__ == "__main__":
    main()
