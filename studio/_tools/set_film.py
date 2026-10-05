#!/usr/bin/env python3
"""studio/_tools/set_film.py - a film shot frames first in a 3D set (LTX_PLAYBOOK §99.10, §100): the set gives
every shot's first and last frames, H3 acts between them, the picks are cut with one grade and a score.
Written for the duel in the clearing (2026-10-01) as the work script duel.py; the shot script is a sequence
whose shots are cameras in a set with an acts file (studio/shotscripts/_make_forest_duel_1001.py).

    python3 studio/_tools/set_film.py --sequence forest-duel check
    python3 studio/_tools/set_film.py --sequence forest-duel frames [--only D01,D02]
    python3 studio/_tools/set_film.py --sequence forest-duel takes [--only ...] [--seeds 11 202]
    python3 studio/_tools/set_film.py --sequence forest-duel boards
    python3 studio/_tools/set_film.py --sequence forest-duel cut --picks picks_long.json --score score_long.mp3 --titles

check     before anything renders: every character projected through every shot's first and last camera
frames    set_test.py render (the set's previz, masks and map) and cast --ends: the place dressed without them
          at both ends, each character put in from their sheet where the set says they stand
takes     H3 first-last (workflow 65) between anchor_<id>.png and anchor_<id>_end.png: h3f_<id>_s<seed>.mp4
          (a shot with key poses: set_test.py key / take, h3k_<id>_s<seed>.mp4 - pick it as "k<seed>")
boards    every shot's frames and takes, for picking by eye
music     RETIRED 2026-10-01 (music and sections both): they wrote the score from tags, unheard - the duel in
          the clearing's score, never again. The score is the cue the director picked by ear, placed at
          OUT/<--score> (craft/SOUND.md section 0); the cut refuses nothing, it just uses what is there
cut       picks.json {"D01": 11, "D07": "k11", ...} in shot order, audio conformed to 48 kHz, one filmic grade,
          the picked score under the takes' own sound, --titles for a title and an end card, --duck for the
          score ducking under the takes' own sound (an A/B on the 30-second cut: the hits ~1 dB further forward)
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import time

ROOT = os.path.expanduser("~/shared/comfy-studio")
TOOLS = os.path.join(ROOT, "studio", "_tools")
sys.path.insert(0, TOOLS)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import fight                      # noqa: E402  (reads --sequence off argv)
import previz_shot as ps          # noqa: E402
import set_measure as sm          # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402

OUT = fight.OUT
COMFY = fight.COMFY


def ids(only):
    return [s["id"] for s in fight.SHOTS if not only or s["id"] in only]


def take_path(sid, q):
    """A pick: a seed (h3f_, the take between the two frames) or "k<seed>" (h3k_, the take with key poses)."""
    if isinstance(q, str) and q.startswith("k"):
        return os.path.join(OUT, "h3k_%s_s%d.mp4" % (sid, int(q[1:])))
    return os.path.join(OUT, "h3f_%s_s%d.mp4" % (sid, int(q)))


def run(cmd):
    t0 = time.time()
    r = subprocess.run(cmd, capture_output=True, text=True)
    tail = "\n".join(l for l in (r.stdout + r.stderr).splitlines() if l.strip())[-1800:]
    print(tail, flush=True)
    if r.returncode != 0:
        sys.exit("failed (%ds): %s" % (time.time() - t0, " ".join(cmd[:5])))


def stage_frames(only, seeds):
    st = os.path.join(TOOLS, "set_test.py")
    run(["python3", st, "--sequence", fight.SEQUENCE, "render", "--only"] + ids(only))
    run(["python3", st, "--sequence", fight.SEQUENCE, "cast", "--ends", "--only"] + ids(only) +
        ["--seeds"] + [str(q) for q in seeds])


def stage_check():
    """Before anything is rendered: every character who should be in a shot's first or last frame, projected
    through that frame's camera - out of frame, or behind the lens (where cast would paste them anywhere).
    Five of the duel's 58 cameras were wrong in a way only the frames showed, 30 minutes of frames later."""
    import numpy as np
    acts = json.load(open(os.path.join(ROOT, "studio", "shotscripts", fight.FILM + ".acts.json")))
    heights = {"terra": 1.62, "jester": 1.88}

    def proj(cam, look, lens, p, w=1280, h=720):
        c, l, q = (np.array(v, float) for v in (cam, look, p))
        f = (l - c) / np.linalg.norm(l - c)
        r = np.cross(f, [0, 0, 1.0])
        r /= np.linalg.norm(r)
        u = np.cross(r, f)
        d = q - c
        z = d @ f
        if z <= 0.05:
            return None
        k = lens / 36.0 * w
        return w / 2 + (d @ r) / z * k, h / 2 - (d @ u) / z * k

    bad = 0
    for s in fight.SHOTS:
        pz, sid = s["previz"], s["id"]
        for tag in ("start", "end"):
            cam = pz["cam_to"] if tag == "end" and pz.get("cam_to") else pz["cam"]
            look = pz["look_to"] if tag == "end" and pz.get("look_to") else pz["look"]
            for who, m in (acts.get(sid) or {}).get("figures", {}).items():
                mk = m.get(tag) or {}
                if mk.get("hidden") or "at" not in mk:
                    continue
                at = list(mk["at"]) + [0.0] * (3 - len(mk["at"]))
                hh = heights.get(who.rstrip("0123456789"), 1.7)
                feet, head = proj(cam, look, pz["lens"], at), proj(cam, look, pz["lens"], (at[0], at[1], at[2] + hh))
                if feet is None or head is None:
                    print("  %s %-5s %s: BEHIND the camera" % (sid, tag, who))
                    bad += 1
                    continue
                cx = (feet[0] + head[0]) / 2
                if cx < -40 or cx > 1320 or head[1] > 720 or feet[1] < 0:
                    print("  %s %-5s %s: out of frame (x %.0f, head y %.0f, feet y %.0f, %d px tall)" % (
                        sid, tag, who, cx, head[1], feet[1], feet[1] - head[1]))
                    bad += 1
    print("check: %d character-frames out of the picture across %d shots" % (bad, len(fight.SHOTS)))


def h3_len(frames):
    n = max(1, -(-(frames - 6) // 17))
    return 17 * n + 5


def _inp(src, name):
    shutil.copy(src, os.path.join(COMFY, "input", name))
    return name


def stage_takes(only, seeds, force=False):
    jobs = [(sid, q) for sid in ids(only) for q in seeds]
    print("%d takes" % len(jobs), flush=True)
    for sid, q in jobs:
        s = fight.shot(sid)
        dst = os.path.join(OUT, "h3f_%s_s%d.mp4" % (sid, q))
        if os.path.exists(dst) and not force:
            continue
        a, b = os.path.join(OUT, "anchor_%s.png" % sid), os.path.join(OUT, "anchor_%s_end.png" % sid)
        if not (os.path.exists(a) and os.path.exists(b)):
            print("  %s: no frames yet" % sid, flush=True)
            continue
        tag = "film_%s_s%d" % (sid, q)
        wf = {k: v for k, v in fight.load_wf("65_minimax_h3_fl_turbo_v4.json").items()
              if isinstance(v, dict) and "class_type" in v}
        wf["8"]["inputs"]["image"] = _inp(a, tag + "_a.png")
        wf["9"]["inputs"]["image"] = _inp(b, tag + "_b.png")
        wf["20"]["inputs"].update({"prompt": s["prompt"], "width": 1280, "height": 704,
                                   "length": h3_len(int(s["previz"]["frames"]))})
        wf["33"]["inputs"]["noise_seed"] = int(q)
        wf["51"]["inputs"]["filename_prefix"] = "claude-generated/fight/" + tag
        fight.wait_for_queue()
        ps._room(26.0, 240)
        t0 = time.time()
        ok = fight.collect(fight.submit(wf, tag), dst, kinds=(".mp4",))
        print("  %s s%-4d %4.0fs %s" % (sid, q, time.time() - t0, "ok" if ok else "FAILED"), flush=True)


def stage_boards(only):
    rel = [i / 9 for i in range(10)]
    tw, th = 230, 126
    rows = []
    for sid in ids(only):
        rows.append(("frames", sid, None))
        for q in (11, 202, 3003):
            p = os.path.join(OUT, "h3f_%s_s%d.mp4" % (sid, q))
            if os.path.exists(p):
                rows.append(("take", sid, q))
    b = Image.new("RGB", (80 + tw * len(rel), (th + 3) * len(rows) + 16), (16, 16, 16))
    d = ImageDraw.Draw(b)
    d.text((4, 2), "%s - each shot: its two frames from the set, then its takes (0..100%%)" % fight.FILM, fill=(255, 220, 90))
    for r, (kind, sid, q) in enumerate(rows):
        y = 16 + r * (th + 3)
        if kind == "frames":
            d.text((4, y + 4), "%s\nframes" % sid, fill=(255, 220, 90))
            for c, p in enumerate([os.path.join(OUT, "anchor_%s.png" % sid), os.path.join(OUT, "anchor_%s_end.png" % sid)]):
                if os.path.exists(p):
                    b.paste(Image.open(p).convert("RGB").resize((tw, th)), (80 + c * (len(rel) - 1) * tw, y))
            continue
        d.text((4, y + 4), "%s\ns%d" % (sid, q), fill=(255, 255, 255))
        ims, _ = sm.video_frames(os.path.join(OUT, "h3f_%s_s%d.mp4" % (sid, q)), rel)
        for c, im in enumerate(ims):
            if im is not None:
                b.paste(sm.to704(im).resize((tw, th)), (80 + c * tw, y))
    dst = os.path.join(OUT, "board%s.jpg" % ("_" + "_".join(sorted(only)) if only else ""))
    b.save(dst, quality=86)
    print("board ->", dst, flush=True)


def stage_music(seconds, seed):
    """Retired 2026-10-01: this wrote the score from tags, unheard (fight.NO_UNHEARD_MUSIC). The cut takes the
    cue the director picked by ear, placed at OUT/<--score>; craft/SOUND.md section 0."""
    sys.exit(fight.NO_UNHEARD_MUSIC % os.path.join(OUT, "score.mp3"))


def stage_music_sections(picks_file, dst_name):
    """Retired 2026-10-01: five unheard tag-only cues, one per act, crossfaded at the act breaks - the duel in the
    clearing's score, the one that must never be heard in our work again (fight.NO_UNHEARD_MUSIC)."""
    sys.exit(fight.NO_UNHEARD_MUSIC % os.path.join(OUT, dst_name))


def _font(size, bold=True):
    from PIL import ImageFont
    for f in ("/usr/share/fonts/julietaula-montserrat-fonts/Montserrat-%s.otf" % ("Bold" if bold else "Medium"),
              "/usr/share/fonts/julietaula-montserrat-fonts/Montserrat-%s.otf" % ("Bold" if bold else "Regular"),
              "/usr/share/fonts/open-sans/OpenSans-%s.ttf" % ("Semibold" if bold else "Regular"),
              "/usr/share/fonts/dejavu-sans-fonts/DejaVuSans%s.ttf" % ("-Bold" if bold else ""),
              "/usr/share/fonts/dejavu/DejaVuSans%s.ttf" % ("-Bold" if bold else ""),
              "/usr/share/fonts/truetype/dejavu/DejaVuSans%s.ttf" % ("-Bold" if bold else "")):
        if os.path.exists(f):
            return ImageFont.truetype(f, size)
    return ImageFont.load_default()


def title_clip(lines, base_png, secs, dst):
    """A card: the base frame blurred and darkened, the lines centred; silent 48 kHz stereo so it concatenates."""
    from PIL import ImageFilter
    im = Image.open(base_png).convert("RGB").resize((1280, 704)).filter(ImageFilter.GaussianBlur(7))
    im = Image.eval(im, lambda v: int(v * 0.42))
    d = ImageDraw.Draw(im)
    y = 352 - sum(sz + 18 for _, sz in lines) // 2
    for text, sz in lines:
        f = _font(sz, bold=sz > 40)
        w = d.textlength(text, font=f)
        d.text(((1280 - w) / 2 + 3, y + 3), text, font=f, fill=(0, 0, 0))
        d.text(((1280 - w) / 2, y), text, font=f, fill=(255, 236, 196) if sz > 40 else (225, 225, 225))
        y += sz + 18
    png = dst[:-4] + ".png"
    im.save(png)
    fight.sh("ffmpeg", "-y", "-v", "error", "-loop", "1", "-i", png, "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo",
             "-t", "%.2f" % secs, "-vf", "fade=in:0:10,fade=out:st=%.2f:d=0.6" % (secs - 0.6), "-r", "24",
             "-c:v", "libx264", "-crf", "16", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
             "-shortest", dst)
    return dst


def stage_cut(name, picks_file="picks.json", score_name="score.mp3", titles=False, duck=False):
    """The picked takes in shot order, audio conformed to 48 kHz, one filmic grade, the score under at 0.5."""
    import post
    picks = json.load(open(os.path.join(OUT, picks_file)))
    chosen = []
    for s in fight.SHOTS:
        q = picks.get(s["id"])
        if q is None:
            continue
        p = take_path(s["id"], q)
        rate = fight.sh("ffprobe", "-v", "error", "-select_streams", "a:0", "-show_entries", "stream=sample_rate",
                        "-of", "csv=p=0", p).stdout.strip()
        # a take whose own sound is buried under the score (F05's aura roar, -43 dB) is lifted by the shot
        # script's "sound_gain_db" before the mix
        gain = float(s.get("sound_gain_db") or 0)
        if rate != "48000" or gain:
            c = os.path.join(OUT, "_conform_%s%s" % ("g%+g_" % gain if gain else "", os.path.basename(p)))
            fight.sh("ffmpeg", "-y", "-v", "error", "-i", p, "-c:v", "copy", "-c:a", "aac", "-ar", "48000", "-ac", "2",
                     "-b:a", "192k", *(["-af", "volume=%gdB" % gain] if gain else []), c)
            p = c
        chosen.append(p)
    lead = 0.0
    if titles and chosen:
        # a title card over the first frame, an end card over the last; the score waits for the title
        first = [s["id"] for s in fight.SHOTS if s["id"] in picks][0]
        last = [s["id"] for s in fight.SHOTS if s["id"] in picks][-1]
        lead = 3.0
        chosen = ([title_clip([(fight._seq["title"], 64)] + ([(fight._seq["subtitle"], 28)]
                                                                if fight._seq.get("subtitle") else []),
                              os.path.join(OUT, "anchor_%s.png" % first), lead, os.path.join(OUT, "_title.mp4"))] +
                  chosen + [title_clip([("THE END", 60)], os.path.join(OUT, "anchor_%s_end.png" % last), 3.0,
                                       os.path.join(OUT, "_end.mp4"))])
    lst = os.path.join(OUT, "_concat_%s.txt" % name)
    open(lst, "w").write("".join("file '%s'\n" % p for p in chosen))
    cut = os.path.join(OUT, "%s_cut.mp4" % name)
    fight.sh("ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", lst, "-c:v", "libx264", "-crf", "16",
             "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", cut)
    dur = post.duration(cut)
    out = os.path.join(OUT, "%s.mp4" % name)
    score = os.path.join(OUT, score_name)
    cmd = ["ffmpeg", "-y", "-v", "error", "-i", cut]
    if os.path.exists(score):
        # --duck: the score ducks under the takes' own sound (sidechain keyed by them) - on the 30-second cut the
        # mix over the takes' loudest moments rose from +0.7 to +1.8 dB over the rest (LTX_PLAYBOOK §100.9)
        takes = "[0:a]asplit=2[sc][fx];[m][sc]sidechaincompress=threshold=0.03:ratio=6:attack=8:release=350[md];" \
                "[fx][md]" if duck else "[0:a][m]"
        cmd += ["-i", score, "-filter_complex",
                "[1:a]adelay=%d|%d,volume=0.55,afade=t=out:st=%.2f:d=1.5[m];%samix=inputs=2:duration=first:"
                "dropout_transition=0,loudnorm=I=-15:TP=-1.5:LRA=11[a]" % (int(lead * 1000), int(lead * 1000),
                                                                           max(0.0, dur - 1.5), takes),
                "-map", "0:v", "-map", "[a]"]
    else:
        cmd += ["-af", "loudnorm=I=-15:TP=-1.5:LRA=11"]
    # loudnorm resamples to 192 kHz internally; without -ar the film came out at 96 kHz
    cmd += ["-vf", post.grade_filter("filmic"), "-c:v", "libx264", "-crf", "16", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k", "-ar", "48000", out]
    fight.sh(*cmd)
    print("cut %d shots -> %s (%.1f s, %d frames)" % (len(chosen), out, post.duration(out), post.frames(out)), flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sequence", required=True)
    ap.add_argument("stage", choices=["check", "frames", "takes", "boards", "music", "sections", "cut"])
    ap.add_argument("--picks", default="picks.json")
    ap.add_argument("--score", default="score.mp3")
    ap.add_argument("--titles", action="store_true")
    ap.add_argument("--duck", action="store_true", help="cut: the score ducks under the takes' own sound")
    ap.add_argument("--only", default="")
    ap.add_argument("--seeds", type=int, nargs="+", default=[11, 202])
    ap.add_argument("--seconds", type=float, default=34.0)
    ap.add_argument("--seed", type=int, default=77)
    ap.add_argument("--name", default="")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    only = set(x for x in a.only.split(",") if x)
    if a.stage == "check":
        stage_check()
    elif a.stage == "frames":
        stage_frames(only, a.seeds)
    elif a.stage == "takes":
        stage_takes(only, a.seeds, a.force)
    elif a.stage == "boards":
        stage_boards(only)
    elif a.stage == "music":
        stage_music(a.seconds, a.seed)
    elif a.stage == "sections":
        stage_music_sections(a.picks, a.score)
    else:
        stage_cut(a.name or fight.FILM, a.picks, a.score, a.titles, a.duck)


if __name__ == "__main__":
    main()
