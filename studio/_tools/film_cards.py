#!/usr/bin/env python3
"""studio/_tools/film_cards.py - the title card, and an ANNOTATED cut that shows the pipeline at work.

After fight.py --finish has written <film>_filmic.mp4 (and --master its 2x), this writes:

  <film>_final.mp4        a three-second title card, then the film
  <film>_final_2x.mp4     the same on the 2x master, when the master exists
  <film>_annotated.mp4    the film with a caption under every shot: which engine drew it, what the
                          start frame was composed with, which take was picked and why - and, in
                          amber, the shots the paid engine would have taken (the SEEDANCE notation)

The shot boundaries come from the picked takes' own frame counts, the same counts fight.py's finish
checks its invariant against, so a caption cannot drift off its shot.

    python3 studio/_tools/film_cards.py --sequence temper --picks "010=11,020=h3:202,..."
    python3 studio/_tools/film_cards.py --sequence temper            # picks from picks.txt
"""
import argparse
import json
import os
import subprocess
import sys

ROOT = os.path.expanduser("~/shared/comfy-studio")
TOOLS = os.path.join(ROOT, "studio", "_tools")
sys.path.insert(0, TOOLS)
import fight                                  # noqa: E402  (reads --sequence off argv)
import post                                   # noqa: E402

FONTS = "/usr/share/fonts/julietaula-montserrat-fonts"


def font(name):
    for cand in (os.path.join(FONTS, "Montserrat-%s.otf" % name),
                 "/usr/share/fonts/liberation-sans-fonts/LiberationSans-Regular.ttf"):
        if os.path.exists(cand):
            return cand
    return cand


ENGINE = {"shot": "LTX-2.5 (image to video, joint audio)",
          "h3": "MiniMax H3 (image to video, keeps the start frame)",
          "pv": "Blender physics previz -> LTX-2.3 depth control",
          "pvb": "Blender physics previz -> LTX-2.3 depth control, no start frame"}
COMPOSITOR = {"flux2": "Flux 2, three references", "qwen21": "Qwen-Image-2.1, reference edit"}


def sh(*a):
    r = subprocess.run(a, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stderr[-1500:], flush=True)
    return r


def txt(path, s):
    open(path, "w", encoding="utf-8").write(s)
    return path


def card(dst, w, h, title, lines, secs=3.0):
    """Black, the title, a logline, a credit line; silent stereo audio so it concatenates."""
    work = os.path.dirname(dst)
    fs_title, fs_sub, fs_small = int(h * 0.095), int(h * 0.030), int(h * 0.022)
    parts = ["color=c=black:s=%dx%d:d=%.2f:r=24,format=yuv420p" % (w, h, secs)]
    t1 = txt(os.path.join(work, "_card_title.txt"), title)
    parts.append("drawtext=fontfile=%s:textfile=%s:fontsize=%d:fontcolor=white:x=(w-text_w)/2:y=h*0.36"
                 % (font("Bold"), t1, fs_title))
    y = 0.36 + 0.095 + 0.05
    wrapped = []
    for s, size, colour in lines:
        if size == "sub" and len(s) > 84:          # a logline longer than the frame: two lines
            mid = len(s) // 2
            cut = min((i for i, ch in enumerate(s) if ch == " "), key=lambda i: abs(i - mid))
            wrapped += [(s[:cut], size, colour), (s[cut + 1:], size, colour)]
        else:
            wrapped.append((s, size, colour))
    lines = wrapped
    for i, (s, size, colour) in enumerate(lines):
        tf = txt(os.path.join(work, "_card_line%d.txt" % i), s)
        fs = {"sub": fs_sub, "small": fs_small}[size]
        parts.append("drawtext=fontfile=%s:textfile=%s:fontsize=%d:fontcolor=%s:x=(w-text_w)/2:y=h*%.3f"
                     % (font("Light"), tf, fs, colour, y))
        y += 0.055 if size == "sub" else 0.042
    parts.append("fade=t=in:st=0:d=0.4,fade=t=out:st=%.2f:d=0.5" % (secs - 0.5))
    graph = ",".join(parts)
    sh("ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", graph, "-f", "lavfi", "-i",
       "anullsrc=r=48000:cl=stereo", "-t", "%.2f" % secs, "-c:v", "libx264", "-crf", "16",
       "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-shortest", dst)
    return dst


def join(a, b, dst):
    sh("ffmpeg", "-y", "-v", "error", "-i", a, "-i", b, "-filter_complex",
       "[0:v][0:a][1:v][1:a]concat=n=2:v=1:a=1[v][a]", "-map", "[v]", "-map", "[a]",
       "-c:v", "libx264", "-crf", "16", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", dst)
    return dst


def first_sentence(s):
    s = (s or "").strip()
    for stop in (". ", "; "):
        if stop in s:
            return s.split(stop)[0].rstrip(".") + "."
    return s


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sequence", required=True)
    ap.add_argument("--picks", default="")
    a = ap.parse_args()
    out, film = fight.OUT, fight.FILM
    raw = a.picks or (open(os.path.join(out, "picks.txt")).read().strip()
                      if os.path.exists(os.path.join(out, "picks.txt")) else "")
    picks = dict(kv.split("=", 1) for kv in raw.split(",") if "=" in kv)
    anchors = {}
    ap_ = os.path.join(out, "anchors.json")
    if os.path.exists(ap_):
        anchors = json.load(open(ap_))
    ranked = {}
    rp = os.path.join(out, "ranked.json")
    if os.path.exists(rp):
        ranked = json.load(open(rp))
    # a pick made by eye over the ranker says so, with its reason, instead of the ranker's score
    op = os.path.join(out, "picks_overrides.json")
    if os.path.exists(op):
        for sid, o in json.load(open(op)).items():
            ranked.setdefault(sid, {})["why"] = "by eye - " + o["why"]
    seq = fight._seq
    title = seq.get("title") or film.upper()
    filmic = os.path.join(out, "%s_filmic.mp4" % film)
    if not os.path.exists(filmic):
        sys.exit("finish first: %s missing" % filmic)

    # the shot boundaries, from the picked takes' frame counts (what the finish concatenated)
    spans, t = [], 0.0
    for s in fight.SHOTS:
        want = str(picks.get(s["id"], 11))
        engine, _, seed = want.rpartition(":")
        stem = {"h3": "h3", "": "shot"}.get(engine, engine)
        p = os.path.join(out, "%s_%s_s%s.mp4" % (stem, s["id"], seed))
        if not os.path.exists(p):
            continue
        d = post.frames(p) / 24.0
        spans.append((s, stem, seed, t, t + d))
        t += d

    work = os.path.join(out, "_cards")
    os.makedirs(work, exist_ok=True)
    credit = "Made on one RTX 5090 with open-weight models. Nothing paid for."
    c1 = card(os.path.join(work, "card.mp4"), 1280, 704, title,
              [(seq.get("logline", ""), "sub", "0xDDDDDD"), (credit, "small", "0x9A9A9A")])
    final = join(c1, filmic, os.path.join(out, "%s_final.mp4" % film))
    print("final     -> %s  (%.1f s)" % (final, post.duration(final)), flush=True)
    master = os.path.join(out, "%s_filmic_2x.mp4" % film)
    if os.path.exists(master):
        c2 = card(os.path.join(work, "card_2x.mp4"), 2560, 1408, title,
                  [(seq.get("logline", ""), "sub", "0xDDDDDD"), (credit, "small", "0x9A9A9A")])
        f2 = join(c2, master, os.path.join(out, "%s_final_2x.mp4" % film))
        print("final 2x  -> %s" % f2, flush=True)

    # the annotated cut: a caption band under every shot
    filters = []
    for i, (s, stem, seed, t0, t1) in enumerate(spans):
        ch = (anchors.get(s["id"]) or {}).get("chosen", "")
        if s.get("engine") == "previz":
            start = "Qwen-Image-2.1 dressing the simulation's first frame"
        elif s.get("anchor") is None:
            start = "the place's plate itself"
        else:
            start = COMPOSITOR.get(ch.split("_")[0], ch or "composed")
            if ch:
                start += " (%s)" % ch.replace("qwen21_", "").replace("flux2", "one seed")
        r = (ranked.get(s["id"]) or {})
        l1 = "%s   %s" % (s["id"], s["title"])
        l2 = "%s  |  start frame: %s  |  take: seed %s" % (ENGINE.get(stem, stem), start, seed)
        why = r.get("why") or ""
        l3 = ("picked: " + why) if why else ""
        if len(l3) > 150:
            l3 = l3[:147].rsplit(" ", 1)[0] + " ..."
        sd = s.get("seedance")
        l4 = ""
        if sd:
            l4 = "SEEDANCE CANDIDATE - %s" % first_sentence(sd.get("why"))
            if len(l4) > 140:
                l4 = l4[:137].rsplit(" ", 1)[0] + " ..."
        band = 112 if l4 else 90
        en = "enable='between(t,%.3f,%.3f)'" % (t0, t1 - 0.001)
        filters.append("drawbox=x=0:y=ih-%d:w=iw:h=%d:color=black@0.62:t=fill:%s" % (band, band, en))
        y = band - 8
        filters.append("drawtext=fontfile=%s:textfile=%s:fontsize=22:fontcolor=white:x=24:y=h-%d:%s"
                       % (font("Bold"), txt(os.path.join(work, "_l1_%d.txt" % i), l1), y, en))
        y -= 32
        filters.append("drawtext=fontfile=%s:textfile=%s:fontsize=15:fontcolor=0xE6E6E6:x=24:y=h-%d:%s"
                       % (font("Regular"), txt(os.path.join(work, "_l2_%d.txt" % i), l2), y, en))
        if l3:
            y -= 22
            filters.append("drawtext=fontfile=%s:textfile=%s:fontsize=14:fontcolor=0xB8B8B8:x=24:y=h-%d:%s"
                           % (font("Regular"), txt(os.path.join(work, "_l3_%d.txt" % i), l3), y, en))
        if l4:
            y -= 22
            filters.append("drawtext=fontfile=%s:textfile=%s:fontsize=15:fontcolor=0xF0B43C:x=24:y=h-%d:%s"
                           % (font("SemiBold"), txt(os.path.join(work, "_l4_%d.txt" % i), l4), y, en))
    gp = txt(os.path.join(work, "_annot.graph"), "[0:v]" + ",".join(filters) + "[v]")
    ann_body = os.path.join(work, "annotated_body.mp4")
    sh("ffmpeg", "-y", "-v", "error", "-i", filmic, "-filter_complex_script", gp, "-map", "[v]",
       "-map", "0:a", "-c:v", "libx264", "-crf", "17", "-pix_fmt", "yuv420p", "-c:a", "copy", ann_body)
    c3 = card(os.path.join(work, "card_annot.mp4"), 1280, 704, title,
              [("ANNOTATED - the engine, the start frame and the pick under every shot", "sub", "0xDDDDDD"),
               ("Amber marks the shots we would send to Seedance 2.5, and did not.", "small", "0xF0B43C")])
    ann = join(c3, ann_body, os.path.join(out, "%s_annotated.mp4" % film))
    print("annotated -> %s  (%.1f s)" % (ann, post.duration(ann)), flush=True)
    json.dump([{"shot": s["id"], "title": s["title"], "engine": stem, "seed": seed,
                "start": round(t0, 3), "end": round(t1, 3)} for s, stem, seed, t0, t1 in spans],
              open(os.path.join(out, "timeline.json"), "w"), indent=1)
    print("CARDS DONE", flush=True)


if __name__ == "__main__":
    main()
