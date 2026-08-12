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
from epic import (sh, dur, adur, measure, norm_to, ensure_local, load_wf, expand,
                  submit, wait_all, keyscale, FONT, fgpath, ffesc, COMFY, HOST)   # noqa: E402

KF = (1664, 928)          # keyframes: 16:9, letterboxed into the vertical canvas later
VID = (1280, 704)         # generated clip size
CANVAS = (1080, 1920)     # 9:16 delivery
FPS = 24
NIGHT = True              # day-for-night grade, see make_cut
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
              "handheld"}
FX_EFFECTS = {"shake", "aberr", "glow", "flash", "ramp", "smear", "whiteout", "hot"}
# Named cameras that exist as cards and render nothing here. Reported differently from a
# typo because the author did not make a mistake - the app offered them the move.
FX_CAMERAS_UNBUILT = {
    "dolly_zoom": "needs a depth map. On a flat plate a dolly-in and a zoom-in are the "
                  "SAME transform and cancel exactly to the identity - the whole effect "
                  "is the near/far parallax differential, which a flat image does not "
                  "have. No zoompan can fake it.",
    "orbit":      "not achievable after the fact at all. Depth parallax gives a lateral "
                  "slide, not an arc, and cannot reveal a surface the plate never saw; "
                  "the mesh route needs a headless rasterizer this box does not have.",
    "rack_focus": "needs a depth ordering. The filter chain is known (fixed-sigma gblur "
                  "plus a depth-derived time-ramped mask through maskedmerge) and the "
                  "depth pass to feed it does not exist yet.",
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


def fx_chain(fx, w, h, fps, seed=0, length=2.0):
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
    if "push" in fx or "punch" in fx:          # slow push in: interest, intimacy
        out.append(f"zoompan=z='1+0.10*on/{n}':d=1:x='iw/2-(iw/zoom/2)':"
                   f"y='ih/2-(ih/zoom/2)':s={w}x{h}:fps={fps}")
    if "pull" in fx:                            # pull back: isolation, reveal, endings
        out.append(f"zoompan=z='1.12-0.10*on/{n}':d=1:x='iw/2-(iw/zoom/2)':"
                   f"y='ih/2-(ih/zoom/2)':s={w}x{h}:fps={fps}")
    if "pan_l" in fx or "pan_r" in fx:
        d = 1 if "pan_r" in fx else -1
        out.append(f"scale={int(w*1.16)}:{int(h*1.16)},"
                   f"crop={w}:{h}:'(iw-{w})/2+{d}*(iw-{w})/2*(t/{max(length,0.1):.2f})':"
                   f"'(ih-{h})/2'")
    if "tilt_u" in fx or "tilt_d" in fx:
        d = 1 if "tilt_d" in fx else -1
        out.append(f"scale={int(w*1.16)}:{int(h*1.16)},"
                   f"crop={w}:{h}:'(iw-{w})/2':"
                   f"'(ih-{h})/2+{d}*(ih-{h})/2*(t/{max(length,0.1):.2f})'")
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


def wrap_caption(txt, width=46):
    """drawtext does not wrap. A long line runs straight off the side of the frame and the
    start of it is simply lost - which is worse than useless, because it looks deliberate."""
    words, lines, cur = txt.split(), [], ""
    for w in words:
        if len(cur) + len(w) + 1 > width and cur:
            lines.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}".strip()
    if cur:
        lines.append(cur)
    return lines


def make_cut(src, at, length, fx, dst, seed=0, grade=None):
    w, h = VID
    chain = fx_chain(fx, w, h, FPS, seed, length)
    # Every cut is graded the same so the short reads as one piece. Keep this GENTLE:
    # it multiplies with the `hot` effect, and at 1.12x1.45 saturation whole shots
    # turned neon magenta.
    base = "eq=contrast=1.06:saturation=1.12"
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
    return dst


def slam(src, dst, target=TARGET_LUFS, ceiling=0.87, tries=6):
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
            set_path(wf, "20.inputs.width", KF[0])
            set_path(wf, "20.inputs.height", KF[1])
            set_path(wf, "13.inputs.seed", int(b.get("seed", seed0 + i * 7)))
            set_path(wf, "15.inputs.filename_prefix",
                     f"{out.split('output/')[1]}/keyframes/{b['id']}")
        else:
            wf = load_wf("13_qwen_t2i_styled.json")
            style_lora_slot(wf, film)
            set_path(wf, "10.inputs.text", f"{expand(b['prompt'], chars)}, {style}")
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
        length = max(9, int(math.ceil(secs * FPS / 8)) * 8 + 1)
        wf = load_wf("12_ltx23_i2v_audio.json")
        set_path(wf, "8.inputs.image", staged)
        # expand() is kept on the way out for the hand-authored films/*.json that write
        # {HERO} into their motion string. Compiled films no longer contain braces -
        # compose.resolve_motion() fills the pronoun, because naming the mover in full
        # measured as ADDED off-brief drift and film["characters"] maps a name to itself.
        set_path(wf, "10.inputs.text",
                 expand(motion_of(b), film.get("characters", {})))
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
        if eng == "indextts2":
            for k in ("Happy", "Angry", "Sad", "Surprised", "Afraid", "Disgusted",
                      "Calm", "Melancholic"):
                set_path(wf, f"20.inputs.{k}", float((cfg.get("emotion") or {}).get(k, 0)))
        set_path(wf, "30.inputs.text", b["line"]["text"])
        set_path(wf, "30.inputs.narrator_voice", cfg["voice"])
        set_path(wf, "30.inputs.seed", seed0 + i * 17)
        set_path(wf, "40.inputs.filename_prefix",
                 f"{out.split('output/')[1]}/voice/raw_{b['id']}")
        print(f"  > {b['id']} ({b['line']['who']})", flush=True)
        _, outs = run(HOST, wf, quiet=True)
        raw = ensure_local(outs[0], f"{out}/voice/_raw_{b['id']}.mp3", required=True)
        pre = cfg.get("filter", "")
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
        # A per-shot camera choice from the screenplay overrides whatever move the
        # template happened to carry. Without this every template that used `punch`
        # produced the same drift, which read as a rendering artefact rather than style.
        cam = b.get("camera")
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
            make_cut(src, at, ln, c.get("fx", []), p, seed=n, grade=b.get("grade"))
            if line_start is None:
                line_start = t
            pieces.append(p)
            t += dur(p)
            n += 1
        if beat_impact and pieces:
            p = f"{work}/{n:04d}_impact.mp4"
            make_impact(pieces[-1], p)
            pieces.append(p)
            t += dur(p)
            n += 1
        if b.get("caption"):
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
            cue_start = max(0.0, line_start + lead)
            cues.append((cue_start, min(vd, max(t - cue_start, 0.4)), b["line"], vp))
    print(f"  {len(pieces)} shots, {t:.1f}s, median "
          f"{sorted(dur(p) for p in pieces)[len(pieces)//2]:.2f}s")

    # Once cues can move they can collide, and two voices talking over each other is
    # not an L-cut, it is a mistake. Check against the REAL audio length rather than the
    # caption length, because the voice keeps playing after its caption disappears.
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

    # ---- composite to the vertical canvas ------------------------------------
    cw, ch = film.get("canvas") or CANVAS
    ff = f"fontfile='{fgpath(FONT)}':" if FONT else ""
    hook = film.get("hook", "")
    # The reference letterboxes as well, so black bars are correct for the format - but
    # its inner content is about 1.38:1 rather than 16:9, filling ~40% of the canvas
    # against our 31%. Cropping the sides to match buys back a third of the picture.
    if cw >= ch:
        # widescreen: the generated clips are already 16:9, so fill the frame
        vf = [f"scale={cw}:{ch}:force_original_aspect_ratio=increase",
              f"crop={cw}:{ch}"]
    else:
        vf = [f"crop=ih*1.38:ih", f"scale={cw}:-2",
              f"pad={cw}:{ch}:0:({ch}-ih)/2:color=black"]
    if hook:
        # a hook that never leaves the screen - the reference keeps its title up for the
        # entire runtime, which is what stops a scroller from swiping away
        for li, line in enumerate(hook.split("|")):
            vf.append(f"drawtext={ff}text='{ffesc(line.strip())}':fontcolor=white:"
                      f"fontsize={int(cw*0.078)}:x=(w-text_w)/2:"
                      f"y={int(ch*0.045) + li*int(cw*0.092)}:"
                      f"shadowcolor=black@0.9:shadowx=3:shadowy=3")
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
                      f"box=1:boxcolor=black@0.62:boxborderw=12:"
                      f"enable='between(t,{lo:.2f},{hi:.2f})'")
        # clock ticks 89:00 -> 90:00 across the film, so the countdown is SHOWN not claimed
        vf.append(rf"drawtext={ff}text='89\:%{{eif\:min(59,floor(t*60/{total:.2f}))\:d\:2}}':"
                  f"fontcolor=yellow:fontsize={int(cw*0.036)}:x=(w-text_w)/2:"
                  f"y={top - int(cw*0.055)}:box=1:boxcolor=black@0.62:boxborderw=10")

    # STORY CAPTIONS - one per beat, held for the whole beat. At a 0.2s median shot the
    # images cannot carry a plot on their own; these are what stop the film reading as a
    # random pile of pretty frames. Placed just under the picture area, above the spoken
    # lines, so the two never collide.
    band = (int(ch * 0.88) if cw >= ch
            else int((ch + int(cw / 1.38)) / 2) + int(ch * 0.035))
    for cs, ce, txt in caps:
        for li, ln in enumerate(wrap_caption(txt)):
            vf.append(f"drawtext={ff}text='{ffesc(ln)}':fontcolor=white:"
                  f"fontsize={int(cw*0.026)}:x=(w-text_w)/2:"
                  f"y={band + li*int(cw*0.034)}:"
                  f"box=1:boxcolor=black@0.55:boxborderw=10:"
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
    for start, length, line, _ in cues:
        lines = wrap_caption(line["text"], width=34)
        for li, ln in enumerate(lines):
            y = int(ch * 0.70) - (len(lines) - 1 - li) * int(dlg_size * 1.35)
            vf.append(f"drawtext={ff}text='{ffesc(ln)}':fontcolor=white:fontsize={dlg_size}:"
                      f"x=(w-text_w)/2:y={y}:box=1:boxcolor=black@0.55:boxborderw=12:"
                      f"enable='between(t,{start:.2f},{start+max(length,0.8):.2f})'")
    vertical = f"{work}/_vertical.mp4"
    sh("ffmpeg", "-y", "-v", "error", "-i", joined, "-vf", ",".join(vf),
       "-c:v", "libx264", "-crf", "17", "-preset", "medium", "-pix_fmt", "yuv420p",
       "-an", vertical)

    # ---- audio: dialogue + score, mastered LOUD ------------------------------
    ins, filt, labels = ["-i", vertical], [], []
    k = 1
    for start, _, line, vp in cues:
        if not os.path.exists(vp):
            continue
        ins += ["-i", vp]
        ms = int(start * 1000)
        filt.append(f"[{k}:a]volume=1.0,adelay={ms}|{ms}[v{k}]")
        labels.append(f"[v{k}]")
        k += 1
    for c in film.get("music", []):
        p = f"{out}/music/{c['prefix']}_00001.mp3"
        if not os.path.exists(p):
            continue
        np_ = f"{work}/_m_{c['prefix']}.wav"
        norm_to(p, np_, -20.0, tp=-3.0)
        ins += ["-i", np_]
        at = float(c.get("at", 0))
        ms = int(at * 1000)
        filt.append(f"[{k}:a]volume={c.get('level',1.0)},adelay={ms}|{ms}[m{k}]")
        labels.append(f"[m{k}]")
        k += 1
    slug = film["title"].lower().replace(" ", "-")
    final = f"{out}/{slug}.mp4"
    # The output directory is derived from the TITLE alone, so two films that share a
    # title silently overwrite each other's master. A 334 MB, 8m46s delivered episode
    # was one `ffmpeg -y` away from being replaced by a 40-second test render. Archive
    # instead of clobbering: renders are expensive and a master is not reproducible
    # once its inputs have moved on.
    if os.path.exists(final):
        n = 1
        while os.path.exists(f"{out}/{slug}.prev{n}.mp4"):
            n += 1
        os.rename(final, f"{out}/{slug}.prev{n}.mp4")
        print(f"    archived previous master -> {slug}.prev{n}.mp4")
    if labels:
        # Master in three explicit steps, NOT as one filter_complex.
        #
        # `loudnorm` inside a filter_complex runs SINGLE-PASS, where it is an adaptive
        # compressor working blind on a lookahead window - it cannot know the programme
        # loudness in advance, so it under-delivers badly. Asking for -9 that way measured
        # -16. Only the two-pass form (measure, then apply a computed static gain) actually
        # hits a target, which is what norm_to does.
        raw = f"{work}/_mix_raw.wav"
        filt.append("".join(labels) +
                    f"amix=inputs={len(labels)}:duration=longest:normalize=0,"
                    f"apad[mix]")
        # keep the video as input 0 so the [k:a] labels built above stay valid
        sh("ffmpeg", "-y", "-v", "error", *ins, "-filter_complex", ";".join(filt),
           "-map", "[mix]", "-c:a", "pcm_s24le", "-ar", "48000",
           "-t", f"{total:.2f}", raw)

        mastered = f"{work}/_mix_master.wav"
        slam(raw, mastered)

        sh("ffmpeg", "-y", "-v", "error", "-i", vertical, "-i", mastered,
           "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "256k",
           "-t", f"{total:.2f}", "-movflags", "+faststart", final)
    elif film.get("silent"):
        # Declared silent. Intent is stated in the film, never inferred from an empty
        # list, because "no audio was found" and "no audio was wanted" look identical
        # here and mean opposite things.
        print("    (silent film, as declared)")
        shutil.copy(vertical, final)
    else:
        # Every voice and music file was missing. Copying `vertical` here would ship a
        # SILENT deliverable with exit code 0 - `vertical` is built with -an. Name what
        # was actually looked for, so the cause is one look away rather than a hunt.
        missing = [vp for _s, _e, _l, vp in cues if not os.path.exists(vp)]
        want_music = [f"{out}/music/{c['prefix']}_00001.mp3"
                      for c in film.get("music", [])]
        missing += [p for p in want_music if not os.path.exists(p)]
        raise SystemExit(
            "the film has no audio at all: %d voice cue(s) and %d music cue(s) were "
            "expected and none of the files exist.\n"
            "  first missing: %s\n"
            "  Render the voices and music first, or set \"silent\": true in the film "
            "if it is meant to have no sound.\n"
            "  Refusing to write a silent %s - a silent film that reports success is "
            "the failure this check exists for."
            % (len(cues), len(film.get("music", [])),
               "\n                 ".join(missing[:4]) or "(none listed)",
               os.path.basename(final)))

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
        off = float(m.get("input_i")) - TARGET_LUFS
        if abs(off) > 1.5:
            print(f"    !! loudness is {off:+.1f} LU off target - the master did not take")
        if float(m.get("input_tp")) > -0.5:
            print(f"    !! true peak {m.get('input_tp')} dBTP - raise the limiter's headroom")
    except (TypeError, ValueError):
        print("    !! could not measure the master")
    return final


STAGES = {"keyframes": keyframes, "clips": clips, "voices": voices, "music": music}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("film")
    ap.add_argument("--stage", default="all",
                    choices=["all", "keyframes", "clips", "voices", "music", "cut"])
    ap.add_argument("--seed", type=int, default=4200)
    a = ap.parse_args()
    film = json.load(open(a.film, encoding="utf-8"))
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
