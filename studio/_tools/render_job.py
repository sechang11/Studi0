#!/usr/bin/env python3
"""Render one rolled job. Reads a job JSON on stdin, writes the artifact and its recipe.

    python3 studio/_tools/roll.py image | python3 studio/_tools/render_job.py
    python3 studio/_tools/roll.py video | python3 studio/_tools/render_job.py --out /tmp/x

One job in, one artifact out, and a sidecar .json carrying the full recipe beside it.
This project's rule is that every artifact carries what made it, so it can be reproduced
and so a gallery teaches rather than decorates.

QUALITY GATE. A render that comes back near-black or near-uniform is a failure, not a
result - the night grade taught us that a picture can be technically produced and contain
nothing. Each image is measured after it lands and rejected if it is dead, with the reason
recorded. Rejections go to a rejected/ subfolder rather than being deleted, because a
failure you can look at is worth more than one you cannot.
"""
import argparse, json, os, re, subprocess, sys, time


def slug(s, n=26):
    s = re.sub(r"[^a-z0-9]+", "-", str(s or "").lower()).strip("-")
    return s[:n].strip("-")


def artifact_name(job, ext):
    """A filename that says what the thing IS.

    `5ae68bb18535.webp` tells you nothing; you have to open the sidecar to find out what
    you are looking at, which means a folder of two hundred of them is unsortable and
    unsearchable. The cards that made it are right there in the job, so they go in the name:

        2026-08-06_1243_image_photorealistic_underwater-city_wide-shot_qwen_5ae68b.webp
        2026-08-06_1244_music_hopeful-rising_92bpm_d-major_a8b26c.flac
        2026-08-06_1244_voice_female-02_that-is-not-what-i-said_4017b3.mp3

    Sorting the folder by name groups a run together and then groups by kind. The short id
    stays on the end so two rolls that drew the same cards still cannot collide, and so the
    artifact can still be traced back to its sidecar and its seed.
    """
    d = job["domain"]
    if d in ("image", "video"):
        bits = [job.get("style"), job.get("place"), job.get("character"),
                job.get("framing"), job.get("engine")]
    elif d == "music":
        bits = [job.get("cue"),
                ("%dbpm" % job["bpm"]) if job.get("bpm") else None, job.get("key")]
    elif d == "voice":
        bits = [job.get("voice"), job.get("line")]
    else:
        bits = [job.get("preset")]
    parts = [time.strftime("%Y-%m-%d_%H%M"), d] + [slug(b) for b in bits if b]
    return "_".join(p for p in parts if p) + "_" + job["id"][:6] + ext

HERE = os.path.dirname(os.path.abspath(__file__))
STUDIO = os.path.dirname(HERE)
ROOT = os.path.dirname(STUDIO)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
sys.path.insert(0, STUDIO)
os.environ.setdefault("COMFY_HOST", "127.0.0.1:8188")

from comfy import run, set_path                       # noqa: E402
from epic import load_wf, ensure_local, HOST, COMFY   # noqa: E402
from engine import image_graph, keyscale, video_graph  # noqa: E402  (Phase 2: the one home)


def sh(*a):
    return subprocess.run(a, capture_output=True, text=True)


def luma_sat(path):
    """Mean luma and saturation. A dead render shows up here and nowhere else."""
    t = "/tmp/_qg_%d.txt" % os.getpid()
    for f in (t,):
        try:
            os.remove(f)
        except OSError:
            pass
    sh("ffmpeg", "-v", "error", "-i", path, "-vf",
       "signalstats,metadata=print:key=lavfi.signalstats.YAVG:file=%s" % t, "-f", "null", "-")
    y = None
    if os.path.exists(t):
        for ln in open(t):
            if "YAVG" in ln:
                try:
                    y = float(ln.strip().split("=")[-1])
                except Exception:
                    pass
    t2 = "/tmp/_qg2_%d.txt" % os.getpid()
    sh("ffmpeg", "-v", "error", "-i", path, "-vf",
       "signalstats,metadata=print:key=lavfi.signalstats.SATAVG:file=%s" % t2, "-f", "null", "-")
    s = None
    if os.path.exists(t2):
        for ln in open(t2):
            if "SATAVG" in ln:
                try:
                    s = float(ln.strip().split("=")[-1])
                except Exception:
                    pass
    return y, s


def render_image(job, outdir):
    wf = image_graph(job)
    _, outs = run(HOST, wf, quiet=True)
    if not outs:
        return None
    return ensure_local(outs[0], os.path.join(outdir, "_raw_%s.png" % job["id"]),
                        required=False)


def render_video(job, outdir):
    """Keyframe first, then LTX image-to-video. This is the measured path, not a shortcut.

    Text-to-video hands the model both jobs at once and it does neither well; every clip in
    this project that held up was a still we had already looked at, moved. It also means a
    rejected keyframe costs six seconds instead of ninety.
    """
    key = render_image(job, outdir)
    if not key:
        return None
    y, _ = luma_sat(key)
    if y is not None and y < 8.0:
        raise RuntimeError("keyframe came back near-black (YAVG %.1f) - not worth moving" % y)

    staged = "rolled_%s.png" % job["id"]
    sh("cp", key, os.path.join(COMFY, "input", staged))
    # 8n+1 frames at 24fps is what LTX accepts. Identity starts drifting past about ten
    # seconds, which is why roll.py never asks for more than six.
    # Graph construction moved to engine.video_graph (Phase 2) - frame math, 16:9
    # sizing and the 24fps audio-latent correction included - and proven to submit
    # a byte-identical wf before the inline block was deleted.
    wf = video_graph(job, staged)
    _, outs = run(HOST, wf, quiet=True)
    try:
        os.remove(key)
    except OSError:
        pass
    if not outs:
        return None
    return ensure_local(outs[0], os.path.join(outdir, "_raw_%s.mp4" % job["id"]),
                        required=False)


def render_audio(job, outdir):
    """Music, SFX and voice, each driven through the node map its own domain card carries.

    The three graphs do NOT share a field name - music wants `tags` plus a tempo and a key,
    SFX wants `text`, voice wants `text` plus a reference `voice` file - so there is no
    generic path here. The domain card is what knows; this reads it rather than hardcoding a
    graph it did not write.
    """
    dom = job["domain"]
    card = json.load(open(os.path.join(STUDIO, "domains", dom + ".json"), encoding="utf-8"))
    wf = load_wf(card["workflow"])
    nodes = card.get("nodes") or {}

    def put(key, val):
        if nodes.get(key) and val not in (None, ""):
            set_path(wf, nodes[key], val)

    if dom == "music":
        put("tags", job["prompt"])
        put("lyrics", "[instrumental]")
        # A cue that measured no tempo must not be handed one. An earlier bug in compile.py
        # defaulted unmetered cues to 140 bpm and turned an ambient bed into a march.
        if job.get("bpm"):
            put("bpm", job["bpm"])
        put("key", keyscale(job.get("key")))
        put("duration", job["seconds"])
        put("seconds", job["seconds"])
        put("seed2", job["seed"] ^ 0x5bf03635)
    elif dom == "voice":
        put("text", job.get("line") or "")
        vid = job.get("voice")
        if vid:
            # The blocked-voice refusal lives in cards.require_voice now - ONE enforcement
            # point instead of a lock re-implemented in every consumer. Same message, same
            # RuntimeError; a missing voice also becomes a named error instead of a raw
            # FileNotFoundError from the open() that used to sit here.
            sys.path.insert(0, STUDIO)
            import cards
            vc = cards.require_voice(vid)
            put("voice", vc.get("file") or vid)
    else:
        put("text", job["prompt"])
        put("seconds", job["seconds"])

    put("seed", job["seed"])
    put("prefix", "claude-generated/rolled/%s" % job["id"])
    _, outs = run(HOST, wf, quiet=True)
    if not outs:
        return None
    ext = os.path.splitext(str(outs[0]))[1] or ".flac"
    return ensure_local(outs[0], os.path.join(outdir, "_raw_%s%s" % (job["id"], ext)),
                        required=False)


def main():
    # ALWAYS emit a verdict, even on an unexpected death. A ComfyUI prompt-validation error
    # used to kill this process before it printed anything, so the harness could only report
    # `failed (no result)` - true, useless, and it hid a one-line fix for twenty jobs.
    try:
        _main()
    except SystemExit:
        raise
    except BaseException as e:
        try:
            print(json.dumps({"ok": False, "error": "%s: %s" % (type(e).__name__, e)[:400]}))
        except Exception:
            pass
        raise


def _main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(STUDIO, "samples", "rolled"))
    ap.add_argument("--min-luma", type=float, default=8.0,
                    help="reject a picture darker than this - the night grade taught us a "
                         "render can be produced and contain nothing")
    a = ap.parse_args()

    job = json.loads(sys.stdin.read())
    outdir = os.path.join(a.out, job["domain"])
    os.makedirs(outdir, exist_ok=True)
    os.makedirs(os.path.join(outdir, "rejected"), exist_ok=True)

    t0 = time.time()
    try:
        if job["domain"] == "image":
            raw = render_image(job, outdir)
        elif job["domain"] == "video":
            raw = render_video(job, outdir)
        else:
            raw = render_audio(job, outdir)
    except Exception as e:
        print(json.dumps({"id": job["id"], "domain": job["domain"], "ok": False,
                          "error": str(e)[:200]}))
        return
    if not raw or not os.path.exists(raw):
        print(json.dumps({"id": job["id"], "domain": job["domain"], "ok": False,
                          "error": "no output"}))
        return

    rec = dict(job)
    rec["seconds_taken"] = round(time.time() - t0, 1)
    ok, why = True, ""

    if job["domain"] in ("image", "video"):
        y, s = luma_sat(raw)
        rec["luma"], rec["sat"] = y, s
        if y is not None and y < a.min_luma:
            ok, why = False, "near-black (YAVG %.1f < %.1f)" % (y, a.min_luma)
        dst_dir = outdir if ok else os.path.join(outdir, "rejected")
        if job["domain"] == "video":
            # Keep the video as it came, audio track and all. A rejected clip is moved, not
            # re-encoded - the point of keeping it is to be able to look at what went wrong.
            dst = os.path.join(dst_dir, artifact_name(job, ".mp4"))
            sh("mv", raw, dst)
        else:
            dst = os.path.join(dst_dir, artifact_name(job, ".webp"))
            sh("ffmpeg", "-y", "-v", "error", "-i", raw, "-vf", "scale=1024:-1",
               "-quality", "88", dst)
            try:
                os.remove(raw)
            except OSError:
                pass
    else:
        dst = os.path.join(outdir, artifact_name(job, os.path.splitext(raw)[1] or ".flac"))
        if raw != dst:
            sh("mv", raw, dst)

    rec["file"] = dst
    rec["ok"] = ok
    rec["rejected_because"] = why
    with open(os.path.splitext(dst)[0] + ".json", "w", encoding="utf-8") as f:
        json.dump(rec, f, indent=1, ensure_ascii=False)
        f.write("\n")

    print(json.dumps({"id": job["id"], "domain": job["domain"], "ok": ok,
                      "file": dst, "seconds": rec["seconds_taken"],
                      "why": why}))


if __name__ == "__main__":
    main()
