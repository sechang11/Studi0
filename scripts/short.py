#!/usr/bin/env python3
"""short.py - vertical anime short. The motion comes from the EDIT, not the generation.

    python3 scripts/short.py films/clash.json
    python3 scripts/short.py films/clash.json --stage cut

WHY THIS EXISTS, AND WHY IT IS NOT epic.py

A reference short was measured against a 20-minute film built with epic.py:

                        reference     epic.py film
    mean motion            5.87           2.25
    median shot            0.30s          ~9s
    shots under 1s          64%            ~0%
    loudness             -9.4 LUFS      -18.7 LUFS
    dynamic range (LRA)     2.8            11

Sampling eight consecutive frames of the reference 0.13s apart showed where that motion
actually comes from, and it is not better video generation:

  * two of the eight frames were nearly EMPTY - abstract colour flashes between hits.
  * the apparent violence is radial glow, rim light and camera punch, i.e. COMPOSITING.
  * the characters themselves hold fairly simple poses.

So the reference is not beating us at image-to-video. It is cutting thirty times faster,
inserting impact frames, and layering effects - all of which are ffmpeg operations. That is
the entire thesis of this script:

    GENERATE FEW CLIPS. CUT THEM INTO MANY SHOTS. ADD THE ENERGY IN POST.

One 4-second generated clip becomes 6-10 shots of 0.2-0.4s. Ten generated clips make a
90-shot short. epic.py's assumption - one shot per generation, held long - is exactly
backwards for this format.

STRUCTURE OF A BEAT

    { "id": "030_clash",
      "ref": ["HERO"], "prompt": "...", "motion": "...",
      "clip_secs": 4,
      "cuts": [ {"at": 0.2, "len": 0.30, "fx": ["punch"]},
                {"at": 1.6, "len": 0.22, "fx": ["shake","aberr"]},
                {"at": 3.1, "len": 0.28, "fx": ["glow"]} ],
      "impact": true,
      "line": {"who": "HERO", "text": "You are not ready."} }

`cuts` slices the generated clip at `at` for `len` seconds, applying `fx`. `impact` appends
a 2-frame flash derived from the outgoing frame. `line` becomes both a spoken line and a
burnt-in caption.
"""
import argparse, collections, json, math, os, random, re, shutil, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
# Default to the LOCAL install, matching epic.py. This used to default to "Z:/ComfyUI",
# which is only correct when driving the box from Windows over the SMB share - and that
# share is exactly what craft/ notes say never to read a just-written file from. Driving
# from the box is the reliable mode; set COMFY_ROOT explicitly for the remote case.
os.environ.setdefault("COMFY_ROOT", os.path.expanduser("~/ComfyUI"))
os.environ.setdefault("COMFY_HOST", "127.0.0.1:8188")
from comfy import run, set_path                                        # noqa: E402
from scene_templates import expand as expand_template   # noqa: E402
import sound_dept                                        # noqa: E402  (scripts/)
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "studio"))
from engine import set_negative                         # noqa: E402  (the negative reaches the graph)
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "studio", "_tools"))
# THE ORDER OF THIS BLOCK IS LOAD-BEARING. Three source directories feed this module -
# scripts/, studio/ and studio/_tools/ - and each import has to come after the line that
# puts its directory on the path. voice_emotion was once placed beside sound_dept, four
# lines before _tools was added, and short.py stopped importing at all: every film render
# died on a ModuleNotFoundError while the unit tests, which never import this file, went
# on passing.
import voice_emotion                                    # noqa: E402  (studio/_tools/)
from epic import (sh, dur, adur, measure, norm_to, ensure_local, load_wf, expand,
                  submit, wait_all, keyscale, FONT, fgpath, ffesc, COMFY, HOST)   # noqa: E402

CANVAS = (1080, 1920)     # 9:16 delivery
# Generation sizes, SET FROM THE CANVAS by set_format() before any stage runs.
# These are the landscape defaults; a portrait canvas swaps them, because generating
# 16:9 for a 9:16 delivery put the picture on 40% of the frame and filled the other
# 60% with black - which is most of what "the shorts look dark" turned out to mean.
KF = (1664, 928)          # keyframe size
VID = (1280, 704)         # generated clip size


def set_night(film):
    """Day-for-night is a property of a film, not of the renderer. Off unless asked."""
    global NIGHT
    NIGHT = bool(film.get("night", False))
    return NIGHT


def set_format(canvas):
    """Point the generators at the shape we actually deliver.

    Both engines take arbitrary sizes at the same cost - measured on this box, a Qwen
    keyframe is 3.4s at either orientation and an LTX clip is ~23s at either - so there
    is no reason to generate a shape that has to be padded. Sizes stay on the multiple
    of 32 both models want.
    """
    global KF, VID, CANVAS
    CANVAS = (int(canvas[0]), int(canvas[1]))
    portrait = CANVAS[1] > CANVAS[0]
    KF = (928, 1664) if portrait else (1664, 928)
    VID = (704, 1280) if portrait else (1280, 704)
    return KF, VID
FPS = 24
# How long a hit beat holds its line back, so the impact and the score swell
# play into silence. The moment is made by the gap, not by the gain.
HIT_VOICE_GAP = 0.45
# Mastering target for a film built around a moment. slam() raises gain into a limiter
# until the film measures TARGET_LUFS, which lifts the QUIET parts up to meet the loud
# ones - so the louder the target, the less a hit stands out. Measured on LUMEN's own raw
# mix, impact level over median level:
#
#     raw   x8.19      -9.5  x1.81      -12.5  x2.94      -16.0  x4.15
#
# -12.5 keeps two thirds more of the moment than feed-loud does and is still louder than
# Spotify's -14. A film with no hit keeps TARGET_LUFS; nothing was wrong with it.
HIT_TARGET_LUFS = -12.5
# DAY-FOR-NIGHT, and it is OFF by default now. This was True from the initial commit,
# and because no beat sets a per-beat grade it beat the base grade on every film ever
# rendered: brightness -0.15, gamma 0.92, saturation 0.72. A 28% desaturation applied to
# the whole library by a flag nobody set per film. The reasoning beside the grade itself
# is sound - Animagine renders bright stadiums whatever the prompt says, so night must be
# graded - it was simply never scoped to films that wanted night.
#
# set_format() reads `night` off the film, the same way it reads the canvas.
NIGHT = False
TARGET_LUFS = -9.5        # the reference short measures -9.43 LUFS. Feed-loud, not
                          # broadcast-safe. Do not round this to a nicer number - it is
                          # a measurement, and the tolerance below is judged against it.


# ─────────────────────────────────────────────────────────── effects

# EVERY NAME fx_chain() CAN ACTUALLY RENDER. This table exists because fx_chain is a run
# of `if "name" in fx` tests with no else and no validation, which means an unrecognised
# name produces an EMPTY filter chain and the clip passes through untouched - identical,
# byte for byte, to static. Three consequences, all of them measured rather than guessed:
#
#   * studio/cameras/{static,dolly_zoom,orbit,rack_focus}.mp4 all share MD5
#     85540954967b671562c3efa5f4c28cec. The three roadmap moves are not weak. They ARE the
#     static file.
#   * so is a typo. `pan_left`, `dolly-zoom` and `Push` are indistinguishable from a
#     working move, silently, and this is the wider blast radius: the roadmap moves are at
#     least written down somewhere.
#   * compile.py does validate (lib() raises on an unknown card) but a hand-authored
#     films/*.json never goes through compile.py. It reaches this function directly, and
#     the wizard's scene-level grid offers all three roadmap moves as clickable choices.
#
# A silent no-op is the worst outcome available. It costs a full generation and looks like
# a rendering choice. So: anything not in one of these two sets is reported, loudly, once.
FX_CAMERAS = {"static", "push", "punch", "pull", "pan_l", "pan_r", "tilt_u", "tilt_d",
              "handheld", "dolly_zoom", "rack_focus"}
FX_EFFECTS = {"shake", "aberr", "glow", "flash", "ramp", "smear", "whiteout", "hot"}
# Named cameras that exist as cards and render nothing here. Reported differently from a
# typo because the author did not make a mistake - the app offered them the move.
# dolly_zoom and rack_focus moved OUT of this set (task 22): studio/_tools/depth_pass.py
# maps the keyframe's depth through Depth Anything 3 (core nodes on ComfyUI 0.33) and
# make_cut applies them as a post step. Their limit is stated on their cards: the depth
# is the KEYFRAME's, so they read best on cuts that hold the keyframe's framing.
FX_CAMERAS_DEPTH = {"dolly_zoom", "rack_focus", "parallax_l", "parallax_r"}
FX_CAMERAS_UNBUILT = {
    "orbit":      "not achievable after the fact at all. Depth parallax gives a lateral "
                  "slide, not an arc, and cannot reveal a surface the plate never saw; "
                  "the mesh route needs a headless rasterizer this box does not have.",
}
_FX_SAID = set()


def _fx_unknown(name):
    """Say it once, name it exactly, and say what you got instead."""
    if name in _FX_SAID:
        return
    _FX_SAID.add(name)
    if name in FX_CAMERAS_UNBUILT:
        print(f"  !! camera '{name}' RENDERS NOTHING - this clip is byte-identical to "
              f"static. {FX_CAMERAS_UNBUILT[name]} See studio/cameras/{name}.json.",
              file=sys.stderr)
    else:
        print(f"  !! '{name}' is not a camera or an effect this renderer knows, so it "
              f"does nothing and the clip is byte-identical to static. "
              f"cameras: {', '.join(sorted(FX_CAMERAS))}. "
              f"effects: {', '.join(sorted(FX_EFFECTS))}.", file=sys.stderr)


def fx_chain(fx, w, h, fps, seed=0, length=2.0, phase=(0, 1)):
    """Filter fragments that make a static-ish generated clip read as violent motion.

    Deliberately cheap and per-cut. The reference gets its energy here, not from the model.
    """
    out = []
    # Validate FIRST, so the warning is emitted even when the rest of the chain is empty -
    # which is exactly the case that used to be invisible.
    for name in fx:
        if name not in FX_CAMERAS and name not in FX_EFFECTS:
            _fx_unknown(name)
    # ── camera moves ──────────────────────────────────────────────────────────
    # `punch` used to be the ONLY move, hardcoded to drift one direction, and four of the
    # seven episode templates used it - so almost every shot in the episode panned left in
    # exactly the same way. A camera move must be a CHOICE per shot, and most of the time
    # the right choice is not to move at all.
    n = max(int(length * fps), 2)
    # WHERE THIS CUT SITS IN ITS BEAT. A beat is one clip sliced into micro-shots, and
    # every move used to restart on each slice - zoom in, snap back to wide, zoom in
    # again, the same gesture two or three times in four seconds. A move now covers only
    # its own slice of the travel, so the beat reads as ONE continuous move through its
    # cuts. p0/p1 are the fractions of the whole move this cut is responsible for.
    _pi, _pn = (int(phase[0]), max(1, int(phase[1])))
    p0, p1 = _pi / float(_pn), (_pi + 1) / float(_pn)
    if "push" in fx or "punch" in fx:          # slow push in: interest, intimacy
        out.append(f"zoompan=z='{1 + 0.10 * p0:.4f}+{0.10 * (p1 - p0):.4f}*on/{n}':d=1:"
                   f"x='iw/2-(iw/zoom/2)':"
                   f"y='ih/2-(ih/zoom/2)':s={w}x{h}:fps={fps}")
    if "pull" in fx:                            # pull back: isolation, reveal, endings
        out.append(f"zoompan=z='{1.12 - 0.10 * p0:.4f}-{0.10 * (p1 - p0):.4f}*on/{n}':d=1:"
                   f"x='iw/2-(iw/zoom/2)':"
                   f"y='ih/2-(ih/zoom/2)':s={w}x{h}:fps={fps}")
    if "pan_l" in fx or "pan_r" in fx:
        d = 1 if "pan_r" in fx else -1
        out.append(f"scale={int(w*1.16)}:{int(h*1.16)},"
                   f"crop={w}:{h}:'(iw-{w})/2+{d}*(iw-{w})/2*"
                   f"({p0:.4f}+{p1 - p0:.4f}*(t/{max(length,0.1):.2f}))':"
                   f"'(ih-{h})/2'")
    if "tilt_u" in fx or "tilt_d" in fx:
        d = 1 if "tilt_d" in fx else -1
        out.append(f"scale={int(w*1.16)}:{int(h*1.16)},"
                   f"crop={w}:{h}:'(iw-{w})/2':"
                   f"'(ih-{h})/2+{d}*(ih-{h})/2*"
                   f"({p0:.4f}+{p1 - p0:.4f}*(t/{max(length,0.1):.2f}))'")
    if "handheld" in fx:                        # documentary unease, very subtle
        a = 3
        out.append(f"crop={w-2*a}:{h-2*a}:'{a}+{a-1}*sin(t*3.1)':'{a}+{a-1}*cos(t*2.3)',"
                   f"scale={w}:{h}")
    if "shake" in fx:
        a = 6 + (seed % 5)
        out.append(f"crop={w-2*a}:{h-2*a}:'{a}+{a}*sin(t*90)':'{a}+{a}*cos(t*77)',"
                   f"scale={w}:{h}")
    if "aberr" in fx:
        out.append("rgbashift=rh=4:bh=-4:rv=-2:bv=2")
    if "glow" in fx:
        out.append("split[g0][g1];[g1]gblur=sigma=18,eq=brightness=0.02:saturation=0.7[gb];"
                   "[g0][gb]blend=all_mode=screen:all_opacity=0.38")
    if "flash" in fx:
        out.append("eq=brightness='0.55*max(0,1-t*8)':saturation=1.2")
    if "ramp" in fx:
        # Slow into the wind-up, snap to full speed. The CONTRAST is the impact - a fast
        # shot among fast shots reads as nothing. Force is only visible as a change of rate.
        out.append("setpts='if(lt(T,0.55*%f),2.0*PTS,0.45*PTS)'" % 1.0)
    if "smear" in fx:
        # anime smear frames: directional blur through the moment of contact
        out.append("gblur=sigma=6:steps=1,eq=contrast=1.15")
    if "whiteout" in fx:
        # Cut away AT contact. The audience supplies a bigger hit than we could render.
        out.append("eq=brightness='min(1,2.2*max(0,t-0.10))':saturation='max(0,1-6*max(0,t-0.10))'")
    if "hot" in fx:
        # `hot` is appended LAST, so it lands on whatever the earlier effects produced.
        # Stacked on a brightening effect it is what turns a shot magenta: `glow` screen-
        # blends a blurred bright copy, then `hot` pushes saturation 1.18 and vibrance
        # 0.22 on the already-blown result. The sakuga template asks for exactly that
        # pair on its final cut, which destroyed the climax of the first film compiled
        # from the studio layer - the single most important shot came back an unreadable
        # purple smear.
        #
        # The grade above already carries the film's colour intent, so when something has
        # already lifted the image, `hot` keeps its contrast and gives up its saturation.
        # This is the same lesson the day-for-night comment records: these filters
        # MULTIPLY, and the fix is to stop compounding, not to re-tune each one.
        if any(f in fx for f in ("glow", "flash", "whiteout")):
            out.append("eq=contrast=1.08")
        else:
            out.append("eq=contrast=1.10:saturation=1.18,vibrance=intensity=0.22")
    return ",".join(out)


def _restates(caption, line):
    """True when a story caption only says again what the voice already says.

    Both layers are legitimate - story captions carry plot under a 0.2s cut, dialogue
    captions serve sound-off viewing - but a beat carrying both prints one sentence
    twice in two sizes, which is what the short films were doing on every frame.

    Only an exact restatement is suppressed: if the caption contains a single word the
    spoken line does not, it is carrying information and it stays. Beats with no line
    keep their caption unconditionally, which is the case this layer was built for.
    Trailing "s" is stripped because the authored restatements drift by exactly that
    ("others tear" against "other pack tears").
    """
    if not caption or not line:
        return False
    said = (line or {}).get("text") or ""
    if not said:
        return False

    def bag(s):
        return {w[:-1] if len(w) > 3 and w.endswith("s") else w
                for w in re.findall(r"[a-z]+", s.lower())}

    cap = bag(caption)
    return bool(cap) and not (cap - bag(said))


def wrap_caption(txt, width=46, balance=False):
    """drawtext does not wrap. A long line runs straight off the side of the frame and the
    start of it is simply lost - which is worse than useless, because it looks deliberate.

    balance=True additionally refuses to leave ONE short word alone on the last line.
    "three things, that is all" is 25 characters against the hook's width of 24 and broke
    as "three things, that is" / "all", with the orphan sitting over the subject for the
    whole film. Used for the hook, which is the one text layer on screen throughout;
    dialogue and story captions wrap at 34 and 46 where an orphan is cheap and widening
    would run them off the frame.
    """
    def _wrap(w_):
        words, lines, cur = txt.split(), [], ""
        for w in words:
            if len(cur) + len(w) + 1 > w_ and cur:
                lines.append(cur)
                cur = w
            else:
                cur = f"{cur} {w}".strip()
        if cur:
            lines.append(cur)
        return lines

    lines = _wrap(width)
    if not balance or len(lines) < 2:
        return lines
    # relax the width a little at a time; accept the first wrap with no orphan, and never
    # go past 25% over, which is where the hook starts touching the frame edge
    for extra in range(1, int(width * 0.25) + 1):
        if len(lines[-1].split()) > 1:
            break
        cand = _wrap(width + extra)
        if len(cand) < len(lines) or len(cand[-1].split()) > 1:
            lines = cand
            break
    return lines


def make_cut(src, at, length, fx, dst, seed=0, grade=None, phase=(0, 1)):
    w, h = VID
    # phase says which slice of its beat this cut is, so a camera move continues across
    # the beat's micro-shots instead of restarting on each one.
    chain = fx_chain(fx, w, h, FPS, seed, length, phase)
    # Every cut is graded the same so the short reads as one piece.
    #
    # An S-CURVE, not linear contrast. The old base was eq=contrast=1.06:saturation=1.12,
    # kept timid because it multiplies with the per-shot `hot` effect and at 1.12x1.45
    # saturation whole shots went neon magenta. Timid is also what "it doesn't feel
    # alive" meant: a delivered frame measured mean RGB 83/81/71 - about a third of the
    # way up the scale, with a +4.2 green lean in the mids.
    #
    # This lifts the MIDTONES rather than crushing the ends, so shadows keep their
    # detail while the picture opens; takes the green out; puts a little warmth back.
    # Chosen by rendering four candidates against a delivered frame and looking at all
    # of them BOTH alone and stacked with `hot` - the magenta case is checked, not
    # assumed. See studio/_tools/grade_options.py, sheet in ~/shared/AB/grades.
    # VIBRANCE, not saturation. Measured over four frames of real footage:
    #
    #     none          sat 0.351  val 0.333
    #     old base      sat 0.426  val 0.318
    #     filmic_warm   sat 0.377  val 0.390     <- shipped, and LESS vivid than old base
    #     this          sat 0.501  val 0.413     sat +43%, val +24% against no grade
    #
    # `vibrance` lifts muted colours much harder than saturated ones, so the greens and
    # golds come up without pinning the strong colours at full chroma - eq=saturation
    # strong enough to match this drives sat_p90 to 1.00, which is poster paint. Here it
    # is 0.902: strong, not pegged. See studio/_tools/vibrancy.py.
    base = ("curves=all='0/0.02 0.22/0.28 0.5/0.60 0.78/0.88 1/0.995',"
            "vibrance=intensity=0.60,eq=saturation=1.12")
    # A PER-BEAT grade from the authored `look` wins. studio/looks/*.json each carry a
    # distinct, tuned grade string, compile.py writes one onto every beat - and until
    # now nothing read it, so night / cold / golden / day_for_night all produced exactly
    # the same picture. That is the whole reason `look` appeared not to work: it was
    # being applied as a prompt tag ("night, dark, moonlight") to a model that ignores
    # such tags, while the deterministic half of it sat unused on the beat.
    #
    # Confirmed by rendering: a scene set look:night came back in bright daylight.
    # Grading is deterministic; prompting is not - so let the grade do the work.
    if grade:
        base = grade
    elif NIGHT:
        # DAY-FOR-NIGHT. Animagine renders bright stadiums no matter what the prompt says
        # - "night, dark, dark background" plus a full daylight negative moved mean luma
        # from 170 to 161, i.e. nothing. Grading is deterministic; prompting is not.
        # Keep this RESTRAINED. The first version used colorbalance bs=+0.14/rs=-0.10 and
        # saturation 0.85; stacked with `hot` (+sat), `glow` (screen blend) and `aberr`
        # (red/blue channel shift) it compounded into solid magenta on a third of the film.
        # Darkness must come from luma, and saturation must come DOWN to leave headroom
        # for the effects that follow.
        base = ("eq=brightness=-0.15:contrast=1.20:saturation=0.72,"
                "colorbalance=bs=0.05:rs=-0.03,eq=gamma=0.92")
    vf = ",".join(x for x in [base, chain] if x)
    sh("ffmpeg", "-y", "-v", "error", "-ss", f"{at:.3f}", "-t", f"{length:.3f}", "-i", src,
       "-vf", vf, "-an", "-r", str(FPS), "-c:v", "libx264", "-crf", "16",
       "-preset", "veryfast", "-pix_fmt", "yuv420p", dst)
    # Depth cameras (task 22): applied AFTER the flat chain, from the beat keyframe's
    # depth map. `depth_key` is set by the caller (cut()) when it knows the keyframe;
    # without one the move is reported and skipped, never silently a no-op.
    want = [f for f in fx if f in FX_CAMERAS_DEPTH]
    if want:
        key = getattr(make_cut, "depth_key", None)
        if not key or not os.path.exists(key):
            print(f"    ! {want[0]} asked but no keyframe for a depth map - hard cut",
                  file=sys.stderr)
            return dst
        import depth_pass as _dp
        dmap = os.path.splitext(key)[0] + "_depth.png"
        if not os.path.exists(dmap):
            if not _dp.depth(key, dmap):
                print(f"    ! depth pass failed for {os.path.basename(key)}",
                      file=sys.stderr)
                return dst
        tmp = dst + ".depthcam.mp4"
        if want[0] == "rack_focus":
            got = _dp.rack_focus(dst, dmap, tmp)
        elif want[0].startswith("parallax_"):
            # the honest lateral move orbit's card asks for; direction is the suffix
            got = _dp.parallax(dst, dmap, tmp, direction=want[0].split("_")[1])
        else:
            got = _dp.dolly_zoom(dst, dmap, tmp)
        if got:
            os.replace(tmp, dst)
        else:
            print(f"    ! {want[0]} post step failed - flat cut kept", file=sys.stderr)
    return dst


# 0.78 is -2.16 dBFS, and it is set for the file that SHIPS rather than the one in the
# work directory. Measured on the same audio, twice:
#     _mix_master.wav   -9.8 LUFS   Peak -1.2 dBFS      <- what the limiter delivers
#     pace.mp4          -9.8 LUFS   Peak -0.2 dBFS      <- the same audio, after AAC
# AAC adds about 1.0 dB of true peak, because a lossy codec reconstructs a waveform that
# does not pass through the original sample points and overshoots between them. That is
# the same inter-sample problem the docstring below describes for 48kHz reconstruction,
# one stage further down the chain, where nothing was measuring. At 0.87 the delivered
# masters came out at -0.10 and -0.20 dBTP, which survives here and crunches after a
# platform re-encodes it. Integrated loudness is unchanged: slam iterates to the LUFS
# target either way, this only moves where peaks are clamped.
def slam(src, dst, target=TARGET_LUFS, ceiling=0.78, tries=6):
    """Push a mix to a feed-loud target. Measures after every pass.

    THREE THINGS THAT DEFEAT NAIVE ATTEMPTS AT THIS, all of them silent:

    1. `loudnorm` inside a filter_complex is SINGLE-PASS - an adaptive compressor working
       blind on a lookahead window. It cannot hit a target it has not measured. Asking it
       for -9 gave -16.

    2. Two-pass `loudnorm` measures correctly but, in linear mode, REFUSES any gain that
       would breach its true-peak ceiling. On a dynamic mix that means it quietly returns
       something several LU under target and reports success. That gave -13.9.

    3. `alimiter` caps SAMPLE peak, not TRUE peak. A waveform reconstructed from 48kHz
       samples overshoots between them - measured at over +1 dBTP against a 0 dBFS sample
       ceiling. Resampling to 192k first is what makes the limiter see those peaks.

    So loudness here is made the way records are: raise gain INTO a ceiling and let the
    peaks be clamped. Limiting itself changes integrated loudness, so it iterates.
    """
    # NOTE: a compressor pass was tried here and removed. It bought no loudness
    # (-10.31 -> -10.34) while cutting LRA from 2.5 to 1.50, i.e. flatter than the
    # reference it was meant to imitate. The binding constraint is the limiter
    # ceiling, not dynamic range - so raise the ceiling, do not squash the mix.
    cur, tmps = src, []
    for i in range(tries):
        I = float(measure(cur).get("input_i", -70.0))
        d = target - I
        if abs(d) < 0.3:
            break
        d = max(min(d, 6.0), -12.0)     # cap per-pass gain so the limiter is not slammed
        nxt = f"{dst}.p{i}.wav"
        sh("ffmpeg", "-y", "-v", "error", "-i", cur, "-af",
           f"volume={d:.2f}dB,aresample=192000,"
           f"alimiter=limit={ceiling}:attack=1:release=60:level=disabled,aresample=48000",
           "-c:a", "pcm_s24le", nxt)
        cur, _ = nxt, tmps.append(nxt)
    shutil.copy(cur, dst)
    for p in tmps:
        os.remove(p)
    return dst


def apply_transition(prev, cur, card_id, dst):
    """Task 24: the transition cards' six real filters, finally consumed.

    A beat may declare {"transition": "dissolve"}; the card's own xfade template joins
    the LAST micro-shot of the previous beat to the FIRST of this one. The filter comes
    from studio/transitions/<id>.json - the card is the claim AND the implementation, so
    a transition that works is a card that earned its `ready`. Too-short pieces skip the
    join (a 0.2s micro-shot cannot host a 0.25s dissolve) rather than dying: a missing
    flourish is a style loss, a dead cut stage is a broken film.
    """
    card_path = os.path.join(os.path.dirname(HERE), "studio", "transitions",
                             card_id + ".json")
    try:
        card = json.load(open(card_path, encoding="utf-8"))
    except OSError:
        print(f"    ! unknown transition card: {card_id}", file=sys.stderr)
        return None
    tpl = card.get("filter")
    if not tpl:
        print(f"    ! transition {card_id} has no filter (tier: "
              f"{card.get('tier')}) - hard cut instead", file=sys.stderr)
        return None
    d = float(card.get("seconds", 0.25) or 0.25)
    a, b = dur(prev), dur(cur)
    d = min(d, a - 0.08, b - 0.08)
    if d < 0.04:
        print(f"    ({card_id} skipped: {a:.2f}s/{b:.2f}s pieces are too short to "
              f"host it - hard cut instead)", file=sys.stderr)
        return None
    sh("ffmpeg", "-y", "-v", "error", "-i", prev, "-i", cur, "-filter_complex",
       f"[0:v][1:v]{tpl.format(d=f'{d:.2f}')}:offset={a - d:.2f}[v]",
       "-map", "[v]", "-c:v", "libx264", "-crf", "17", "-preset", "veryfast",
       "-pix_fmt", "yuv420p", "-an", dst)
    return dst if os.path.exists(dst) else None


def make_impact(src_cut, dst, frames=2):
    """A 2-frame abstract flash derived from the outgoing frame.

    This is the device that made the reference feel violent: in eight consecutive frames,
    two were nearly empty. Deriving it from the shot it follows keeps the colour of the
    scene, so it reads as part of the action rather than a dropped frame.
    """
    w, h = VID
    sh("ffmpeg", "-y", "-v", "error", "-sseof", "-0.2", "-i", src_cut, "-frames:v", "1",
       "-vf", "gblur=sigma=40,eq=brightness=0.45:saturation=2.2:contrast=1.4",
       dst + ".png")
    sh("ffmpeg", "-y", "-v", "error", "-loop", "1", "-i", dst + ".png",
       "-t", f"{frames/FPS:.3f}", "-vf", f"scale={w}:{h}", "-r", str(FPS),
       "-c:v", "libx264", "-crf", "16", "-preset", "veryfast", "-pix_fmt", "yuv420p", dst)
    os.remove(dst + ".png")
    return dst


# ─────────────────────────────────────────────────────────── generation
_WORD = re.compile(r"[a-z0-9]+")


def film_negative(film, beat, kind="picture"):
    """The negative a film and a beat ask for, assembled ONCE. Film-level `negative`
    (or `negative_audio` for music/sfx), plus the beat's own `negative`, plus the style
    card's negative_add when the film names a style card id. Empty string means "leave
    the shipped baseline alone"."""
    parts = []
    key = "negative_audio" if kind == "audio" else "negative"
    if film.get(key):
        parts.append(str(film[key]))
    if beat is not None and beat.get("negative"):
        parts.append(str(beat["negative"]))
    if kind == "picture" and film.get("style_card"):
        try:
            sc = json.load(open(os.path.join(os.path.dirname(HERE), "studio", "styles",
                                             film["style_card"] + ".json"),
                                encoding="utf-8"))
            if sc.get("negative_add"):
                parts.append(str(sc["negative_add"]))
        except OSError:
            pass
    return ", ".join(p for p in parts if p.strip())


def _negative(shipped, positive):
    """Drop from the negative any clause the positive prompt is asking for.

    THE DEFECT THIS FIXES, and it was a blocker for a whole class of character.
    workflows/22_anime_kf_ipadapter.json ships a negative that opens
    "1girl, girl, female, feminine, breasts". That is a sensible default for a film about
    two teenage boys and it is fatal for anyone else: NIKA's card carries "1girl, solo" in
    `tags` and "female focus, teenage girl" in `base_tags`, so the renderer was asking for
    a girl in the positive and forbidding one in the negative, on the same beat, at the
    same weight. Her sheet, turnaround, LoRA and every sweep in this project were rendered
    by hand with that negative replaced; nothing an author could write on a card or a film
    could reach it, because short.py never wrote node 6 at all.

    THE RULE, deliberately narrow: a clause is removed only when every word in it also
    appears in the positive. Nothing is added, nothing is invented, and the shipped text
    stays the single source of truth. For a male character the positive contains none of
    those words and the negative comes back byte-identical - verified against VIRO.

    This is not the whole fix. PIP also wants "adult, mature male, muscular" pushed INTO
    the negative, which no card can express and this function will not invent. That needs
    a `negative_add` field on the character card and a compose layer to assemble it.
    """
    if not positive:
        return shipped
    have = set(_WORD.findall(positive.lower()))
    keep = []
    for clause in shipped.split(","):
        words = _WORD.findall(clause.lower())
        if words and all(w in have for w in words):
            continue
        keep.append(clause.strip())
    return ", ".join(k for k in keep if k)


def anime_keyframe(film, b, out, seed):
    """Keyframe via an anime-native SDXL checkpoint + IPAdapter, driven by danbooru tags.

    This is a separate path from the Qwen one, not a replacement, because the two model
    families want OPPOSITE prompt formats - Animagine returns abstract colour shapes when
    fed the cinematic prose Qwen wants. See craft/ANIME_MODELS.md.

    Beats with no character get IPAdapter weight 0, which passes the model through
    untouched - simpler and less fragile than building a second graph without the node.
    """
    wf = load_wf("22_anime_kf_ipadapter.json")
    set_path(wf, "1.inputs.ckpt_name", film.get("anime_ckpt",
                                                "animagine-xl-4.0.safetensors"))
    refs = b.get("ref") or []
    sheets = film.get("anime_sheets", {})

    # A TRAINED CHARACTER LORA, if this beat's character has one.
    #
    # This is the payoff of the whole cast pipeline. IPAdapter refines a face from one
    # reference and a weight sweep on this box found the character "already recognisable
    # at ZERO" - so the sheet was carrying much less than assumed and identity drifted
    # anyway. A LoRA trained on that character is a change to the weights, not a hint,
    # and it holds across scenes the sheet never covered.
    #
    # Inserted between the checkpoint and whatever consumes its MODEL, so the graph stays
    # valid regardless of node order. IPAdapter still runs alongside: they are refining
    # the same thing from different directions, and the sheet costs nothing when a LoRA
    # is present.
    #
    # STRENGTH IS PER CHARACTER, and this used to be a single film-wide default of 0.85
    # that nothing in the authoring layer could set. That is not a cosmetic gap: 0.85 was
    # MEASURED on this box to collapse NIKA's "sunlit field" into a dark grey void, because
    # a character LoRA drags its own training backdrop's value and hue along with the face,
    # and 0.5 was measured to keep the face and give the scene back. Her card records
    # lora_strength_measured 0.5 and had no way to reach the renderer.
    #
    # Order of precedence: the character's own measured strength, then a film-wide
    # override, then 0.85. A character with no measured strength renders exactly as before.
    loras = film.get("character_loras") or {}
    lora_w = film.get("character_lora_weights") or {}
    if refs and loras.get(refs[0]):
        strength = lora_w.get(refs[0], film.get("character_lora_weight", 0.85))
        wf["90"] = {"class_type": "LoraLoaderModelOnly",
                    "inputs": {"model": ["1", 0], "lora_name": loras[refs[0]],
                               "strength_model": float(strength)}}
        for nid, node in list(wf.items()):
            if nid in ("1", "90") or not isinstance(node, dict):
                continue
            for k, v in (node.get("inputs") or {}).items():
                if isinstance(v, list) and len(v) == 2 and v[0] == "1" and v[1] == 0:
                    node["inputs"][k] = ["90", 0]
    if refs and refs[0] in sheets:
        set_path(wf, "2.inputs.image", sheets[refs[0]])
        set_path(wf, "4.inputs.weight", float(film.get("ipadapter_weight", 0.6)))
    else:
        set_path(wf, "4.inputs.weight", 0.0)
    set_path(wf, "5.inputs.text", b["tags"])
    set_path(wf, "6.inputs.text", _negative(wf["6"]["inputs"]["text"], b["tags"]))
    set_path(wf, "8.inputs.seed", int(b.get("seed", seed)))
    set_path(wf, "7.inputs.width", 1344)
    set_path(wf, "7.inputs.height", 768)
    set_path(wf, "10.inputs.width", KF[0])
    set_path(wf, "10.inputs.height", KF[1])
    set_path(wf, "11.inputs.filename_prefix",
             f"{out.split('output/')[1]}/keyframes/{b['id']}")
    return wf


def style_lora_slot(wf, film):
    """Node 7 of BOTH qwen keyframe workflows is the style-LoRA slot. Set it, always.

    Always, including to nothing, because the alternative is what this project shipped
    with for its whole life: workflows/13 hard-loaded qwen_image_2512_storybook_anime_lora
    at 0.8, this function only ran when a film set style_lora, and no compiled film could
    set it - so every qwen keyframe carried a style LoRA nobody chose, underneath whatever
    style the author did choose. Leaving the else branch out is what made that invisible.

    The workflow file now ships at 0.0 as well, so the two agree, but the explicit write
    is the one that cannot be undone by someone editing the JSON.

    ComfyUI's LoraLoader returns the model untouched when strength is 0 and never opens
    the file (comfy nodes.py, LoraLoader.load_lora), so leaving a name in the slot at 0.0
    costs nothing and documents what the slot is for.

    Which LoRA, and whether it is allowed on this engine at all, is decided in
    studio/compose.py resolve_style_lora() and arrives here already resolved: a LoRA
    trained on the wrong base model never reaches this function.
    """
    lora = film.get("style_lora")
    if not lora:
        set_path(wf, "7.inputs.strength_model", 0.0)
        return
    strength = float(film.get("style_strength", 0.0))
    set_path(wf, "7.inputs.lora_name", lora)
    set_path(wf, "7.inputs.strength_model", strength)
    if not strength:
        print(f"  ! style_lora {lora} is set but style_strength is 0 - it will do nothing",
              flush=True)


def keyframes(film, out, seed0):
    chars, style = film.get("characters", {}), film.get("style", "")
    print(f"\n=== KEYFRAMES: {len(film['beats'])} ===")
    for i, b in enumerate(film["beats"]):
        if os.path.exists(f"{out}/keyframes/{b['id']}_00001_.png"):
            continue
        if film.get("keyframe_engine") == "anime":
            print(f"  > {b['id']} ({i+1}/{len(film['beats'])})", flush=True)
            run(HOST, anime_keyframe(film, b, out, seed0 + i * 7), quiet=True)
            continue
        refs = b.get("ref") or []
        if refs:
            wf = load_wf("14_qwen_edit_ref.json")
            sheets = film.get("sheets", {})
            for n, key in enumerate(refs[:3], start=1):
                node = {1: "8", 2: "9", 3: "16"}[n]
                if node not in wf:
                    wf[node] = {"class_type": "LoadImage",
                                "inputs": {"image": sheets[key], "upload": "image"}}
                set_path(wf, f"{node}.inputs.image", sheets[key])
                for enc in ("10", "11"):
                    wf[enc]["inputs"][f"image{n}"] = [node, 0]
            for n in range(len(refs[:3]) + 1, 4):
                for enc in ("10", "11"):
                    wf[enc]["inputs"].pop(f"image{n}", None)
            style_lora_slot(wf, film)
            set_path(wf, "10.inputs.prompt", f"{expand(b['prompt'], chars)}, {style}")
            set_negative(wf, film_negative(film, b), positive=expand(b['prompt'], chars))
            set_path(wf, "20.inputs.width", KF[0])
            set_path(wf, "20.inputs.height", KF[1])
            set_path(wf, "13.inputs.seed", int(b.get("seed", seed0 + i * 7)))
            set_path(wf, "15.inputs.filename_prefix",
                     f"{out.split('output/')[1]}/keyframes/{b['id']}")
        else:
            wf = load_wf("13_qwen_t2i_styled.json")
            style_lora_slot(wf, film)
            set_path(wf, "10.inputs.text", f"{expand(b['prompt'], chars)}, {style}")
            set_negative(wf, film_negative(film, b), positive=expand(b['prompt'], chars))
            set_path(wf, "12.inputs.width", KF[0])
            set_path(wf, "12.inputs.height", KF[1])
            set_path(wf, "13.inputs.seed", int(b.get("seed", seed0 + i * 7)))
            set_path(wf, "15.inputs.filename_prefix",
                     f"{out.split('output/')[1]}/keyframes/{b['id']}")
        print(f"  > {b['id']} ({i+1}/{len(film['beats'])})", flush=True)
        run(HOST, wf, quiet=True)


# ─────────────────────────────────────────────────────────── motion
#
# THE ONE STRING THE VIDEO MODEL READS. It goes into node 10 of
# workflows/12_ltx23_i2v_audio.json and it is the only major variable in this project that
# reaches the generator as free text with nothing else alongside it.
#
# For the life of the project every beat of every film carried the same eleven words,
# because studio/compile.py assigned them as a constant. Measured against an empty-prompt
# control at 0.614, that constant came back 0.520 - one of the three STILLEST cells in an
# 81-clip sweep. So the video pass, which costs roughly 8x the keyframe, has been spent
# asking the model to hold still on every shot ever rendered here.
#
# An empty string is therefore strictly better than the constant, and that is what a film
# carrying the constant now gets - said out loud, with the fix, once.
DEAD_MOTION = "slow deliberate movement only."
# What a legacy film gets instead. NOT an empty string: over the 3-beat proof
# render the empty prompt drifted 18.60 first-to-last, the worst of the three,
# and the strip shows the shot dissolving. This sentence is the one carried by
# the three holding cells the 81-clip sweep measured as its quietest, and it
# names no person - "Nobody moves." drew one into an empty corridor.
LEGACY_HOLD = "Nothing in the frame moves."


def motion_of(b):
    """The video prompt for one beat, with the two failure modes named rather than run."""
    m = str(b.get("motion") or "").strip()
    if not m:
        print(f"  !! {b['id']} has no motion at all. Sending the measured hold instead of "
              f"nothing - an EMPTY prompt is not neutral, it is unsupervised, and it "
              f"measured the worst first-to-last drift of any beat in the proof render "
              f"(18.60). Recompile from the .movie with studio/compile.py, which resolves "
              f"a real motion per beat.", file=sys.stderr)
        return LEGACY_HOLD
    if m.rstrip(".").lower() == DEAD_MOTION.rstrip("."):
        print(f"  !! {b['id']} carries the retired constant {m!r}, which measured 0.520 "
              f"against an empty-prompt control of 0.614 - it asks for LESS than saying "
              f"nothing. Sending {LEGACY_HOLD!r} instead, which is the best-evidenced "
              f"string available and is what that constant was reaching for. Recompile "
              f"from the .movie to get a real per-beat motion.", file=sys.stderr)
        return LEGACY_HOLD
    return m


# Scale words for the extra shots multi-shot is asked for. Deliberately anchored to the
# beat's OWN subject - "the same X, closer" rather than a new setup - because asking
# LTX-2.5 for a genuinely different setup is what makes it leave the keyframe and invent
# a scene. Measured: three different setups produced a man in a suit who was not in the
# plate; three views of one subject produced a take that progressed and held at 0.879.
MS_SCALES = ["", "closer on the same subject", "a detail of the same subject",
             "wider on the same subject"]


def multishot_prompt(b, film, n):
    """The beat's motion, then n-1 anchored variations of it."""
    base = expand(motion_of(b), film.get("characters", {})).rstrip(". ")
    shots = [base]
    for i in range(1, max(1, n)):
        shots.append("%s, %s" % (base, MS_SCALES[i % len(MS_SCALES)] or "continuing"))
    return shots


def clips(film, out, seed0):
    """One generated clip per beat. Deliberately few - the edit multiplies them."""
    rel = out.split("output/")[1]
    print(f"\n=== CLIPS: {len(film['beats'])} source clips ===")
    pids = []
    for i, b in enumerate(film["beats"]):
        if os.path.exists(f"{out}/clips/{b['id']}_00001_.mp4"):
            continue
        kf = ensure_local(f"{rel}/keyframes/{b['id']}_00001_.png",
                          f"{out}/keyframes/{b['id']}_00001_.png", required=True)
        staged = f"short_{b['id']}.png"
        shutil.copy(kf, f"{COMFY}/input/{staged}")
        secs = float(b.get("clip_secs", 4))
        # LTX-2.5 multi-shot, opt-in per film. It runs SYNCHRONOUSLY through its own
        # tool rather than joining the batch below, because it is one pass per beat and
        # the batching exists to overlap many small LTX-2.3 jobs.
        if str(film.get("video_engine") or "").lower() == "ltx25_multishot":
            import multishot as _ms
            n_cuts = len(expand_template(b, secs)[0]) or 2
            got, _p = _ms.render(
                multishot_prompt(b, film, n_cuts), kf,
                max(secs, 6.0),                       # it needs room to progress
                f"{out}/clips/{b['id']}_00001_.mp4",
                seed=seed0 + i * 13)
            print(f"  > {b['id']} multi-shot, {n_cuts} shots asked -> "
                  f"{'ok' if got else 'FAILED'}", flush=True)
            if not got:
                print(f"  !! {b['id']} multi-shot produced nothing - this beat will be "
                      f"missing from the edit rather than silently held",
                      file=sys.stderr)
            continue
        length = max(9, int(math.ceil(secs * FPS / 8)) * 8 + 1)
        wf = load_wf("12_ltx23_i2v_audio.json")
        set_path(wf, "8.inputs.image", staged)
        # expand() is kept on the way out for the hand-authored films/*.json that write
        # {HERO} into their motion string. Compiled films no longer contain braces -
        # compose.resolve_motion() fills the pronoun, because naming the mover in full
        # measured as ADDED off-brief drift and film["characters"] maps a name to itself.
        set_path(wf, "10.inputs.text",
                 expand(motion_of(b), film.get("characters", {})))
        set_negative(wf, film_negative(film, b),
                     positive=expand(motion_of(b), film.get("characters", {})))
        set_path(wf, "20.inputs.width", VID[0])
        set_path(wf, "20.inputs.height", VID[1])
        set_path(wf, "20.inputs.length", length)
        set_path(wf, "21.inputs.frames_number", length)
        set_path(wf, "32.inputs.noise_seed", seed0 + i * 13)
        set_path(wf, "43.inputs.filename_prefix", f"{rel}/clips/{b['id']}")
        pids.append(submit(wf))
    if pids:
        print(f"  submitted {len(pids)} as one batch", flush=True)
        wait_all(pids, "clips")


def voices(film, out, seed0):
    vo = film.get("voices", {})
    lines = [b for b in film["beats"] if b.get("line")]
    if not lines:
        return
    os.makedirs(f"{COMFY}/temp", exist_ok=True)   # ComfyUI wipes this on every restart
    print(f"\n=== VOICES: {len(lines)} lines ===")
    for i, b in enumerate(lines):
        final = f"{out}/voice/{b['id']}.mp3"
        if os.path.exists(final):
            continue
        cfg = vo.get(b["line"]["who"], {})
        eng = cfg.get("engine", film.get("engine", "higgs_v3"))
        wf = load_wf("16_indextts2_voice.json" if eng == "indextts2"
                     else "17_higgs_v3_voice.json")
        # THE BEAT'S EMOTION DRIVES THE READ, falling back to the character's config.
        # That precedence is the point: a cast setting is a default for the film, a
        # shot's emotion is a decision about one line. Before this, a character had one
        # emotion for the whole film and the 27 emotion cards' voice_style never left
        # the page.
        emo_id = str(b.get("emotion") or "").strip()
        vec = voice_emotion.vector(emo_id) if emo_id else None
        if vec is None:
            vec = cfg.get("emotion") or {}
        if eng == "indextts2":
            for k in ("Happy", "Angry", "Sad", "Surprised", "Afraid", "Disgusted",
                      "Calm", "Melancholic"):
                set_path(wf, f"20.inputs.{k}", float(vec.get(k, 0)))
        set_path(wf, "30.inputs.text", b["line"]["text"])
        set_path(wf, "30.inputs.narrator_voice", cfg["voice"])
        set_path(wf, "30.inputs.seed", seed0 + i * 17)
        set_path(wf, "40.inputs.filename_prefix",
                 f"{out.split('output/')[1]}/voice/raw_{b['id']}")
        print(f"  > {b['id']} ({b['line']['who']})", flush=True)
        _, outs = run(HOST, wf, quiet=True)
        raw = ensure_local(outs[0], f"{out}/voice/_raw_{b['id']}.mp3", required=True)
        pre = cfg.get("filter", "")
        # The card's own voice_rate, in the pass that was already happening. atempo moves
        # duration without moving pitch, which is what a rate is; IndexTTS exposes no
        # speed input, so the alternative was to keep ignoring the field. Panic is 1.35,
        # despair is 0.75 - those are the cards' numbers, not invented here.
        rate = voice_emotion.rate(emo_id) if emo_id else 1.0
        if abs(rate - 1.0) > 0.02:
            pre = (pre + "," if pre else "") + f"atempo={rate:.3f}"
        pre = (pre + "," if pre else "") + \
            "acompressor=threshold=-18dB:ratio=4:attack=5:release=120:makeup=1"
        norm_to(raw, final, -18.0, tp=-3.0, pre=pre)


def music(film, out, seed0):
    cues = film.get("music", [])
    print(f"\n=== MUSIC: {len(cues)} ===")
    for i, c in enumerate(cues):
        if os.path.exists(f"{out}/music/{c['prefix']}_00001.mp3"):
            continue
        wf = load_wf("06_acestep_music.json")
        set_negative(wf, film_negative(film, None, "audio"))
        set_path(wf, "10.inputs.tags", c["tags"])
        set_path(wf, "10.inputs.lyrics", "")
        # An unmetered cue keeps the node default rather than being handed a
        # tempo it never had - 140 turned ambient beds into marches.
        if c.get("bpm"):
            set_path(wf, "10.inputs.bpm", int(c["bpm"]))
        set_path(wf, "10.inputs.keyscale", keyscale(c.get("key")))
        set_path(wf, "10.inputs.duration", float(c["seconds"]))
        set_path(wf, "11.inputs.seconds", float(c["seconds"]))
        set_path(wf, "10.inputs.seed", seed0 + i * 41)
        set_path(wf, "12.inputs.seed", seed0 + i * 41)
        set_path(wf, "14.inputs.filename_prefix",
                 f"{out.split('output/')[1]}/music/{c['prefix']}")
        print(f"  > {c['prefix']}", flush=True)
        run(HOST, wf, quiet=True)


# Post-motion. CALM MODE strips these: they are the layer that makes a clip read as
# violent, and on calm material they read as a fault instead. `hot`, `glow` and the
# colour effects are NOT here - those change the picture without moving it.
CALM_STRIP = {"punch", "push", "pull", "pan_l", "pan_r", "tilt_u", "tilt_d",
              "handheld", "shake", "aberr", "flash"}


def calm_beat(beat_cuts, avail):
    """One shot for the whole beat, with the post-motion taken out.

    The templates the shorts draw on came from an anime action reference at a 0.30s
    median shot. A four-second product beat cut into three punch-ins on re-crops of one
    plate is that instinct applied to material it was never measured on.
    """
    fx = [f for c in beat_cuts for f in c.get("fx", []) if f not in CALM_STRIP]
    seen, keep = set(), []
    for f in fx:
        if f not in seen:
            seen.add(f)
            keep.append(f)
    return [{"at": 0.0, "len": float(avail), "fx": keep}]


def _transition_card(name):
    """The transition's card, for the fields the renderer honours. None when unknown."""
    p = os.path.join(os.path.dirname(HERE), "studio", "transitions", "%s.json" % name)
    if not os.path.exists(p):
        return None
    try:
        return json.load(open(p, encoding="utf-8"))
    except Exception:
        return None


# ─────────────────────────────────────────────────────────── the cut
def cut(film, out):
    rel = out.split("output/")[1]
    work = f"{out}/_work"
    os.makedirs(work, exist_ok=True)
    for f in os.listdir(work):
        # os.remove raises IsADirectoryError on a folder, which killed the whole cut
        # before a single shot was sliced - for a reason unrelated to the film.
        p = f"{work}/{f}"
        (shutil.rmtree if os.path.isdir(p) else os.remove)(p)

    print("\n=== SLICING: source clips -> micro-shots ===")
    pieces, cues, caps, t = [], [], [], 0.0
    sfx_cues = []
    hit_times = []
    hit_sfx_cues = []
    audio_drops = []
    n = 0
    for b in film["beats"]:
        src = ensure_local(f"{rel}/clips/{b['id']}_00001_.mp4",
                           f"{out}/clips/{b['id']}_00001_.mp4")
        if not src:
            print(f"  ! no clip for {b['id']}", file=sys.stderr)
            continue
        avail = dur(src)
        beat_start = t
        line_start = None
        # a template turns one generated clip into a shaped run of micro-shots
        beat_cuts, beat_impact = expand_template(b, float(b.get("clip_secs", 4)))
        _calm = str(film.get("energy") or "").lower() == "calm"
        if _calm:
            # one shot per beat, no post-motion: let the generated clip be the shot
            beat_cuts = calm_beat(beat_cuts, dur(src))
            beat_impact = False
        # PACE THE PICTURE TO THE READ. The template chose these lengths knowing nothing
        # about the line that plays over them, so a 6.2s read landed on 3.2s of picture
        # and the film ran out of images long before it ran out of words. The surplus
        # used to be absorbed by freezing the final frame - 4.2s of frozen picture on
        # ATLAS, 6.0s on CREATINE, about a quarter of each film.
        #
        # The footage to fix it is already here: these are slices of a ~4s generated
        # clip and the template was using roughly three quarters of it, at a 1.04s
        # median, which is a machine-gun cut under a calm voice. So stretch this beat's
        # shots until they cover this beat's line.
        #
        # Bounded three ways: only stretch (never compress, the templates' fast runs are
        # deliberate), never past 3x, and make_cut still clamps every shot inside its
        # source clip. A beat that cannot stretch far enough falls through to the
        # held-frame warning, which now fires on a real shortage instead of on every film.
        if b.get("line"):
            _vd = adur(f"{out}/voice/{b['id']}.mp3")
            _pic = sum(float(c["len"]) for c in beat_cuts)
            if _vd > _pic + 0.1 and _pic > 0.1:
                _k = min(_vd / _pic, 3.0)
                beat_cuts = [dict(c, len=float(c["len"]) * _k) for c in beat_cuts]
        # A per-shot camera choice from the screenplay overrides whatever move the
        # template happened to carry. Without this every template that used `punch`
        # produced the same drift, which read as a rendering artefact rather than style.
        cam = b.get("camera")
        # the depth cameras need this beat's keyframe (see make_cut)
        make_cut.depth_key = ensure_local(f"{rel}/keyframes/{b['id']}_00001_.png",
                                          f"{out}/keyframes/{b['id']}_00001_.png")
        for ci, c in enumerate(beat_cuts):
            if cam:
                c = dict(c, fx=[f for f in c["fx"]
                                if f not in ("punch", "push", "pull", "pan_l", "pan_r",
                                             "tilt_u", "tilt_d", "handheld")]
                              + ([] if cam == "static" else [cam]))
            at, ln = float(c["at"]), float(c["len"])
            if at + ln > avail:
                at = max(0.0, avail - ln)
            p = f"{work}/{n:04d}_{b['id']}_{ci}.mp4"
            make_cut(src, at, ln, c.get("fx", []), p, seed=n, grade=b.get("grade"),
                     phase=(ci, len(beat_cuts)))
            if line_start is None:
                line_start = t
            pieces.append(p)
            t += dur(p)
            n += 1
            # Beat boundary transition (task 24): joins this beat's FIRST shot to the
            # previous beat's last. Times after the join shrink by the overlap, and `t`
            # is corrected from the real durations so captions and cues stay honest.
            if ci == 0 and b.get("transition") and len(pieces) >= 2:
                merged = f"{work}/{n:04d}_x_{b['id']}.mp4"
                before = dur(pieces[-2]) + dur(pieces[-1])
                got = apply_transition(pieces[-2], pieces[-1], b["transition"], merged)
                if got:
                    t -= before - dur(got)
                    pieces[-2:] = [got]
                    n += 1
        if beat_impact and pieces:
            p = f"{work}/{n:04d}_impact.mp4"
            make_impact(pieces[-1], p)
            pieces.append(p)
            t += dur(p)
            n += 1
        if b.get("sfx"):
            sp = f"{out}/sfx/{b['id']}_00001.mp3"
            _cue = (beat_start + float(b.get("sfx_at", 0.0) or 0.0),
                    float(b.get("sfx_level", 1.0) or 1.0), sp)
            # A hit's effect rides its own bus - louder, and never ducked under the
            # voiceover. Ordinary effects keep the ordinary treatment.
            (hit_sfx_cues if b.get("hit") else sfx_cues).append(_cue)
        # THE FILM'S MOMENT. `hit: true` on a beat makes the cut into it the point the
        # score builds to, drops away from, and slams back on. `hit_at` moves it inside
        # the shot for a gesture rather than a cut. No hit on any beat leaves the score
        # exactly as it was.
        if b.get("hit"):
            hit_times.append(beat_start + float(b.get("hit_at", 0.0) or 0.0))
        # A transition that declares audio_drop finally gets a consumer. `smash` has
        # carried 0.4 since it was written and only an index ever read it, so every
        # smash in every film compiled to a plain cut with a label on it.
        _tr = b.get("transition")
        if _tr:
            _tc = _transition_card(_tr)
            _ad = (_tc or {}).get("audio_drop")
            if _ad is not None:
                audio_drops.append((beat_start, float(_ad)))
        if b.get("caption") and not _restates(b.get("caption"), b.get("line")):
            caps.append((beat_start, t, b["caption"]))
        if b.get("line"):
            vp = f"{out}/voice/{b['id']}.mp3"
            vd = adur(vp) if os.path.exists(vp) else 1.2
            # AUDIO / PICTURE OFFSET. Cutting picture and sound on the same frame at
            # every transition is the loudest tell of an amateur edit; real dialogue
            # scenes overlap.
            #
            # Note what is actually welded to the picture here, because it is not what
            # you would guess: the voice is mixed with `adelay` at `start` and then plays
            # its WHOLE file, so audio already runs past the end of its own shot. The
            # `length` below only drives how long the caption stays up. So the one thing
            # that needs to move is the START.
            #
            # audio_lead is in seconds, NEGATIVE to bring the line in early (you hear the
            # next scene before you see it). Clamped at 0 so a lead longer than everything
            # before it cannot push the cue to a negative timestamp, which adelay would
            # reject.
            lead = float(b.get("audio_lead", 0.0) or 0.0)
            # A HIT NEEDS A GAP. Shaping the score alone does nothing on a film whose
            # score is quiet under dialogue - measured on LUMEN, where the swell moved
            # the mix by less than the noise. A trailer's hit is not the music getting
            # louder, it is everything else stopping: the impact and the score get the
            # moment to themselves and the line comes in after. Only a default; a beat
            # that states its own audio_lead has made a deliberate choice and keeps it.
            # A zero lead is the absence of a choice, not a choice. Testing for the
            # KEY was wrong: shorts_specs writes audio_lead on every beat, so the guard
            # was false everywhere and the gap never once applied.
            if b.get("hit") and not lead:
                lead = HIT_VOICE_GAP
            cue_start = max(0.0, line_start + lead)
            cues.append((cue_start, min(vd, max(t - cue_start, 0.4)), b["line"], vp))
    print(f"  {len(pieces)} shots, {t:.1f}s, median "
          f"{sorted(dur(p) for p in pieces)[len(pieces)//2]:.2f}s")

    # Once cues can move they can collide, and two voices talking over each other is
    # not an L-cut, it is a mistake.
    #
    # This used to only REPORT the collision and then ship it, and every one of the
    # first 13 short films tripped the warning. On ATLAS the entire last line was
    # playing underneath the previous one:
    #     voice stem 04_turn.mp3   -> "atlas buy it once"
    #     master, final 3.5s       -> "the trade and we are not going to pretend..."
    # The warning had no consumer, which is the same bug shape as the truncated last
    # line above: measured, printed, delivered.
    #
    # So the schedule is enforced now. A line may not begin until the previous line has
    # finished, plus a breath. audio_lead stays a PREFERENCE: it can pull a line early
    # into silence, never into the line before it.
    #
    # This does not fix the root cause, which is authoring - a 6.2s read on a 3.2s beat
    # is too much copy for the picture, and the held-frame warning at the end of the cut
    # is where that shows up. But a late line is a late line, and two simultaneous lines
    # are neither line.
    #
    # Then: a caption may not still be on screen when the next one arrives (the text
    # renders on top of itself, seen in the first rendered shorts), so display length is
    # clamped to the gap to the next cue. That clamp runs AFTER the re-timing, on the
    # corrected starts.
    cues.sort(key=lambda c: c[0])
    BREATH = 0.12
    floor, pushed = 0.0, 0.0
    for i, (start, length, line, vp) in enumerate(cues):
        s = max(start, floor)
        pushed = max(pushed, s - start)
        cues[i] = (s, length, line, vp)
        floor = s + (adur(vp) if os.path.exists(vp) else 1.2) + BREATH
    if pushed > 0.05:
        print(f"    voices re-timed: worst line moved {pushed:.2f}s later "
              f"so it does not play under the one before it")
    for i in range(len(cues) - 1):
        start, length, line, vp = cues[i]
        gap = cues[i + 1][0] - start - 0.08
        if gap > 0.3 and length > gap:
            cues[i] = (start, gap, line, vp)

    ordered = sorted(cues, key=lambda c: c[0])
    for (s1, _, l1, p1), (s2, _, l2, _) in zip(ordered, ordered[1:]):
        end1 = s1 + (adur(p1) if os.path.exists(p1) else 1.2)
        if end1 > s2 + 0.05:
            print(f"    !! voice overlap: {l1['who']} runs {end1 - s2:.2f}s into "
                  f"{l2['who']} at {s2:.2f}s - reduce the audio_lead on that beat",
                  file=sys.stderr)

    # ---- concat: this format is ALL hard cuts, no dissolves anywhere ----------
    lst = f"{work}/list.txt"
    with open(lst, "w", encoding="utf-8") as f:
        for p in pieces:
            f.write("file '" + os.path.abspath(p).replace("\\", "/") + "'\n")
    joined = f"{work}/_joined.mp4"
    sh("ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", lst,
       "-c", "copy", joined)
    total = dur(joined)

    # THE LAST LINE MUST FINISH. The master is written with -t total, so a voice that
    # starts near the end is truncated mid-word - and nothing catches it: loudness is on
    # target and the audio/video coverage check compares two numbers that are both the
    # picture length. Found by ASR on a delivered film ("Take the long way through the
    # morning" arrived as "take the"). Hold the final frame for the overhang so the read
    # finishes over a held image, which is an ordinary outro. Capped so a runaway read
    # cannot stretch the film.
    audio_end = 0.0
    for cstart, _cl, _line, cvp in cues:
        if os.path.exists(cvp):
            audio_end = max(audio_end, cstart + adur(cvp))
    # Raised from 4.0s: with voices scheduled sequentially the final line can
    # start later than it used to, and a cut-off last word is worse than a
    # longer outro on a held frame.
    over = min(6.0, audio_end - total)
    if over > 0.05:
        held = f"{work}/_joined_held.mp4"
        r = sh("ffmpeg", "-y", "-v", "error", "-i", joined, "-vf",
               f"tpad=stop_mode=clone:stop_duration={over:.2f}",
               "-c:v", "libx264", "-crf", "16", "-preset", "veryfast",
               "-pix_fmt", "yuv420p", "-an", held)
        if os.path.exists(held):
            print(f"    held the last frame {over:.2f}s so the final line finishes")
            if over > 2.0:
                print(f"    !! {over:.2f}s of that is held frame - there is more\n"
                      f"       copy than picture in this film; shorten the read\n"
                      f"       or give the last beats more shots")
            joined = held
            total = dur(joined)
        else:
            print(f"    !! the last line runs {over:.2f}s past the picture and the hold "
                  f"failed - it will be cut off", file=sys.stderr)

    # ---- composite to the vertical canvas ------------------------------------
    cw, ch = film.get("canvas") or CANVAS
    ff = f"fontfile='{fgpath(FONT)}':" if FONT else ""
    hook = film.get("hook", "")
    # THE PAD IS NOW A FALLBACK, NOT THE PLAN. set_format() points the generators at the
    # delivery shape, so a portrait film arrives here already portrait and the crop/pad
    # below is a no-op. It still runs, because a hand-authored film may set a canvas that
    # does not match its clips, and a mismatched clip has to go somewhere.
    #
    # It used to be the plan, and it cost 59% of every delivered frame: crop to 1.38:1
    # into a 9:16 canvas puts the picture on ~40% of the height and fills the rest with
    # black. Measured on LUMEN - whole frame mean luma 33.9, picture band alone 79.2,
    # 1020 of 1920 rows pure black. That is most of what "the shorts look dark" meant.
    # Pick the composite from the two shapes rather than assuming the clip is wider than
    # the canvas. The old code cropped the sides unconditionally before padding, which
    # asked for a 1766px-wide crop out of a 704px-wide portrait clip and died.
    src_ar = VID[0] / float(VID[1])
    dst_ar = cw / float(ch)
    if abs(src_ar - dst_ar) < 0.12 or cw >= ch:
        # the shapes agree (or it is widescreen, where they always did): cover and crop.
        # This is the path a natively-portrait film takes, and it leaves no bars at all.
        vf = [f"scale={cw}:{ch}:force_original_aspect_ratio=increase",
              f"crop={cw}:{ch}"]
    else:
        # a clip whose shape does not match the canvas - a hand-authored film, or
        # anything rendered before the generators followed the canvas. Take what sides
        # there are and bar the rest.
        vf = [f"crop=ih*1.38:ih", f"scale={cw}:-2",
              f"pad={cw}:{ch}:0:({ch}-ih)/2:color=black"]
    if hook:
        # a hook that never leaves the screen - the reference keeps its title up for the
        # entire runtime, which is what stops a scroller from swiping away
        # THE HOOK WRAPS TOO. drawtext does not, so a long line runs off BOTH sides -
        # "breakfast that respects your time" rendered as "eakfast that respects your ti",
        # losing the first word and the last while still looking deliberate. This is the
        # one line on screen for the entire film and it was the only text layer never put
        # through wrap_caption. Width 24 rather than the caption default of 46, because
        # the hook is set at cw*0.078 against the dialogue's cw*0.036.
        _hl = 0
        for line in hook.split("|"):
            for part in wrap_caption(line.strip(), width=24, balance=True):
                # OUTLINE, not just a shadow. A shadow is offset - it darkens one
                # side and leaves the opposite edge touching the background - so
                # over the bright films (10 of 23 now measure >140 luma behind
                # their text, paperlight 245) the hook dissolved. An outline
                # surrounds every stroke and holds at any brightness; on the dark
                # films it is black on black and costs nothing.
                vf.append(f"drawtext={ff}text='{ffesc(part)}':fontcolor=white:"
                          f"fontsize={int(cw*0.078)}:x=(w-text_w)/2:"
                          f"y={int(ch*0.045) + _hl*int(cw*0.092)}:"
                          f"borderw=3:bordercolor=black@0.8:"
                          f"shadowcolor=black@0.9:shadowx=3:shadowy=3")
                _hl += 1
    # BROADCAST HUD - score and a running clock, drawn in post.
    #
    # These were first generated as scoreboard shots and came back as garbled digits
    # ("8?.99.10"). Diffusion models cannot render specific text; asking them to is a
    # waste of a beat. Drawn here it is exact, legible, and - crucially - PERSISTENT,
    # so the stakes are on screen continuously rather than being asserted by a caption
    # that has already gone. This is the thing that gives the images context without words.
    hud = film.get("hud")
    if hud:
        top = int((ch - int(cw / 1.38)) / 2) - int(ch * 0.045)
        goal_at = float(hud.get("goal_at", total))
        for lo, hi, txt in ((0, goal_at, hud["before"]), (goal_at, total + 1, hud["after"])):
            vf.append(f"drawtext={ff}text='{ffesc(txt)}':fontcolor=white:"
                      f"fontsize={int(cw*0.040)}:x=(w-text_w)/2:y={top}:"
                      f"box=1:boxcolor=black@0.78:boxborderw=12:"
                      f"enable='between(t,{lo:.2f},{hi:.2f})'")
        # clock ticks 89:00 -> 90:00 across the film, so the countdown is SHOWN not claimed
        vf.append(rf"drawtext={ff}text='89\:%{{eif\:min(59,floor(t*60/{total:.2f}))\:d\:2}}':"
                  f"fontcolor=yellow:fontsize={int(cw*0.036)}:x=(w-text_w)/2:"
                  f"y={top - int(cw*0.055)}:box=1:boxcolor=black@0.78:boxborderw=10")

    # STORY CAPTIONS - one per beat, held for the whole beat. At a 0.2s median shot the
    # images cannot carry a plot on their own; these are what stop the film reading as a
    # random pile of pretty frames. Placed just under the picture area, above the spoken
    # lines, so the two never collide.
    # Where the captions sit. The old portrait expression - (ch + cw/1.38)/2 - was the
    # bottom edge of the LETTERBOXED picture, so captions landed in the black bar with
    # the bar to themselves. With the picture filling the frame that number is arbitrary
    # and the story and dialogue captions crowd each other over live footage. When there
    # is no bar, use the same safe area from the bottom the landscape branch always used.
    _barred = not (abs(VID[0] / float(VID[1]) - cw / float(ch)) < 0.12 or cw >= ch)
    band = (int((ch + int(cw / 1.38)) / 2) + int(ch * 0.035) if _barred
            else int(ch * 0.88))
    for cs, ce, txt in caps:
        for li, ln in enumerate(wrap_caption(txt)):
            vf.append(f"drawtext={ff}text='{ffesc(ln)}':fontcolor=white:"
                  f"fontsize={int(cw*0.026)}:x=(w-text_w)/2:"
                  f"y={band + li*int(cw*0.034)}:"
                  f"box=1:boxcolor=black@0.72:boxborderw=10:"
                  f"shadowcolor=black@0.9:shadowx=2:shadowy=2:"
                  f"enable='between(t,{cs:.2f},{ce:.2f})'")
    # DIALOGUE CAPTIONS WRAP TOO.
    #
    # Story captions have gone through wrap_caption since it was written; spoken lines
    # never did, and drawtext does not wrap - it runs a long line straight off both
    # sides of the frame. "Nine years. Nine years we have come here and gone home quiet."
    # rendered as "ne years. Nine years we have come here and gone home qui", losing the
    # beginning AND the end of the sentence, which is worse than useless because it still
    # looks deliberate.
    #
    # These are set at fontsize cw*0.036 against the story captions' cw*0.026, so they
    # need a TIGHTER wrap than the 46-char default, not the same one. Lines are stacked
    # upward from the baseline so a two-line caption grows away from the bottom edge
    # instead of through it.
    dlg_size = int(cw * 0.036)
    # The dialogue block grows UPWARD from its baseline, so the baseline must sit a full
    # caption height above the story band or the two collide - measured: a three-line
    # dialogue caption reached 1420 on the vertical canvas and the band starts at 1418.
    dlg_base = min(int(ch * 0.70), band - int(dlg_size * 1.6))
    for start, length, line, _ in cues:
        lines = wrap_caption(line["text"], width=34)
        for li, ln in enumerate(lines):
            y = dlg_base - (len(lines) - 1 - li) * int(dlg_size * 1.35)
            vf.append(f"drawtext={ff}text='{ffesc(ln)}':fontcolor=white:fontsize={dlg_size}:"
                      f"x=(w-text_w)/2:y={y}:box=1:boxcolor=black@0.72:boxborderw=12:"
                      f"enable='between(t,{start:.2f},{start+max(length,0.8):.2f})'")
    vertical = f"{work}/_vertical.mp4"
    sh("ffmpeg", "-y", "-v", "error", "-i", joined, "-vf", ",".join(vf),
       "-c:v", "libx264", "-crf", "17", "-preset", "medium", "-pix_fmt", "yuv420p",
       "-an", vertical)

    # ---- audio: the sound department (Phase 6, task 47) ----------------------
    # Three buses, each stem NORMALISED to its bus target before any level trim, with
    # score and effects sidechain-ducked under dialogue - sound_dept.py holds the
    # machinery epic.py proved on the episodes. What this replaced mixed raw files at
    # fixed multipliers, which is how a bang and a footstep arrived 20 dB apart.
    voices_l = [(start, vp) for start, _, _line, vp in cues if os.path.exists(vp)]
    musics_l = []
    for c in film.get("music", []):
        p = f"{out}/music/{c['prefix']}_00001.mp3"
        if os.path.exists(p):
            musics_l.append((float(c.get("at", 0)), float(c.get("level", 1.0)), p))
    sfxs_l = [(at, lv, p) for at, lv, p in sfx_cues if os.path.exists(p)]
    hits_l = [(at, lv, p) for at, lv, p in hit_sfx_cues if os.path.exists(p)]

    slug = film["title"].lower().replace(" ", "-")
    final = f"{out}/{slug}.mp4"
    # Archive instead of clobbering: renders are expensive and a master is not
    # reproducible once its inputs have moved on.
    if os.path.exists(final):
        n = 1
        while os.path.exists(f"{out}/{slug}.prev{n}.mp4"):
            n += 1
        os.rename(final, f"{out}/{slug}.prev{n}.mp4")
        print(f"    archived previous master -> {slug}.prev{n}.mp4")

    # A film may name a soundscape; its card carries the scene's mix intention. Loaded
    # here rather than inside the mixer so an unknown id fails loudly at the film, which
    # is where the typo is.
    _scape = None
    if film.get("soundscape"):
        _sp = os.path.join(os.path.dirname(HERE), "studio", "soundscapes",
                           str(film["soundscape"]) + ".json")
        try:
            _scape = json.load(open(_sp, encoding="utf-8"))
        except OSError:
            print(f"    ! no soundscape card: {film['soundscape']}", file=sys.stderr)
    # A film built around a moment masters with room for it. See HIT_TARGET_LUFS: at
    # -9.5 the limiter lifts the quiet parts until the hit is only 1.8x its surroundings;
    # at -12.5 it is 2.9x. `loudness` on the film overrides, because this is a real trade
    # between carrying on a scroll and having a moment at all.
    _target = film.get("loudness")
    if _target is None:
        _target = HIT_TARGET_LUFS if hit_times else TARGET_LUFS
    _target = float(_target)
    if abs(_target - TARGET_LUFS) > 0.01:
        print(f"    mastering at {_target:.1f} LUFS rather than {TARGET_LUFS:.1f} - "
              f"{'the film declares a hit' if hit_times else 'the film asks for it'}")

    def _slam(a, b):
        return slam(a, b, target=_target)

    got = sound_dept.mix_master(work, vertical, total, voices_l, musics_l, sfxs_l,
                                final, _slam, scape=_scape, hits=hit_times, drops=audio_drops, hit_sfx=hits_l)
    if not got:
        if film.get("silent"):
            # Declared silent. Intent is stated in the film, never inferred from an
            # empty list - "no audio found" and "no audio wanted" look identical here
            # and mean opposite things.
            print("    (silent film, as declared)")
            shutil.copy(vertical, final)
        else:
            missing = [vp for _s, _e, _l, vp in cues if not os.path.exists(vp)]
            missing += [f"{out}/music/{c['prefix']}_00001.mp3"
                        for c in film.get("music", [])
                        if not os.path.exists(f"{out}/music/{c['prefix']}_00001.mp3")]
            missing += [p for _at, _lv, p in sfx_cues if not os.path.exists(p)]
            raise SystemExit(
                "the film has no audio at all: %d voice, %d music and %d sfx cue(s) "
                "were expected and none of the files exist.\n"
                "  first missing: %s\n"
                "  Render the voices/music/sfx first (--stage voices|music|sfx), or "
                "set \"silent\": true in the film if it is meant to have no sound.\n"
                "  Refusing to ship a silent film that reports success."
                % (len(cues), len(film.get("music", [])), len(sfx_cues),
                   "\n                 ".join(missing[:4]) or "(none listed)"))

    # Check the mix actually COVERS the film before checking how loud it is. `amix` defaults
    # to duration=first, which once truncated a 63s short to 5.2s of audio - and every
    # loudness check still passed, because loudnorm measured those 5 seconds and gated the
    # silence out. A level measurement cannot tell you the track stopped.
    va, aa = dur(final), adur(final)
    if abs(va - aa) > 0.5:
        print(f"    !! audio is {aa:.1f}s on a {va:.1f}s film - the mix stopped early",
              file=sys.stderr)

    m = measure(final)
    print(f"\n>>> {final}")
    print(f"    {total:.1f}s  {cw}x{ch}  {len(pieces)} shots  {aa:.1f}s audio  "
          f"{m.get('input_i','?')} LUFS / {m.get('input_tp','?')} dBTP")
    try:
        # against the target THIS FILM was mastered to, not the global constant -
        # a film that declares a hit masters at HIT_TARGET_LUFS, and comparing it
        # to -9.5 made the check fire on every correct render.
        off = float(m.get("input_i")) - _target
        if abs(off) > 1.5:
            print(f"    !! loudness is {off:+.1f} LU off target - the master did not take")
        if float(m.get("input_tp")) > -0.5:
            print(f"    !! true peak {m.get('input_tp')} dBTP - raise the limiter's headroom")
    except (TypeError, ValueError):
        print("    !! could not measure the master")
    return final


def sfx(film, out, seed0):
    """The stage short.py never had (task 47): every beat's named effect, rendered
    through 10_stableaudio_sfx by the shared sound department."""
    return sound_dept.render_sfx(film, out, seed0)


STAGES = {"keyframes": keyframes, "clips": clips, "voices": voices, "music": music,
          "sfx": sfx}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("film")
    ap.add_argument("--stage", default="all",
                    choices=["all", "keyframes", "clips", "voices", "music", "sfx", "cut"])
    ap.add_argument("--seed", type=int, default=4200)
    a = ap.parse_args()
    film = json.load(open(a.film, encoding="utf-8"))
    kf, vid = set_format(film.get("canvas") or CANVAS)
    if set_night(film):
        print("  day-for-night grade ON (the film asks for it)")
    print("  format: canvas %dx%d -> keyframes %dx%d, clips %dx%d"
          % (CANVAS[0], CANVAS[1], kf[0], kf[1], vid[0], vid[1]))
    slug = film["title"].lower().replace(" ", "-")
    out = f"{COMFY}/output/claude-generated/12-shorts/{slug}"
    for d in ("keyframes", "clips", "voice", "music", "_work"):
        os.makedirs(f"{out}/{d}", exist_ok=True)
    for name, fn in STAGES.items():
        if a.stage in ("all", name):
            fn(film, out, a.seed)
    if a.stage in ("all", "cut"):
        cut(film, out)


if __name__ == "__main__":
    main()
