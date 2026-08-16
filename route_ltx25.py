#!/usr/bin/env python3
"""LTX-2.5 becomes a SELECTABLE video engine, and the measurement that justifies the
choice is written where a chooser will read it.

NOT a silent default swap. The constitution's rule is that outputs stay comparable, and
2.5 is not strictly better - it is differently better:

    engine   hold_f0   drift            motion   time
    2.3      0.317     0.141 walks away  8.79    27.0s
    2.5      0.308    -0.004 HOLDS       1.54    25.7s
    (static floor for reference: motion 0.001 - so 2.5 moves, gently)

Drift is the failure this pipeline pays for: you approve a keyframe and the picture walks
off it. 2.5 does not drift. But it moves ~5x less, so a film that needs visible action in
the frame may still want 2.3 - and camera moves are ffmpeg post passes here either way.

So: job["video_engine"] = "ltx23" (default, unchanged) | "ltx25". engine.video_graph
routes on it, the numbers live on the model card and in craft/VIDEO_RULES.md, and the
next film decides by A/B rather than by anyone's taste at 2am.
"""
import ast, io, json, os, sys

os.chdir(os.path.dirname(os.path.abspath(__file__)))

# ---- engine.video_graph learns the second engine ------------------------------------
P = "studio/engine.py"
t = io.open(P, encoding="utf-8", newline="").read()
old = '''def video_graph(job, staged_image):
    """The LTX image-to-video pass over a staged keyframe - extracted verbatim from
    render_job.render_video's build block, frame math and the 24fps audio-latent
    correction included (see task #45)."""'''
new = '''def video_graph(job, staged_image):
    """The LTX image-to-video pass over a staged keyframe.

    job["video_engine"] picks the model, default unchanged:
      "ltx23" (default) - 12_ltx23_i2v_audio. More motion (8.79 vs 1.54 measured), but
                          the picture DRIFTS off the approved keyframe (0.141 SSIM lost
                          across 4s).
      "ltx25"           - 51_ltx25_i2v. Holds the keyframe (drift -0.004, i.e. the last
                          frame is as close as the first) with gentler motion, and is
                          the only engine here that can generate CONNECTED SHOTS with a
                          cut inside one pass (studio/_tools/multishot.py).
    Numbers from samples/ltx25_probe/report.json, one keyframe, same seed and motion
    text; the static floor is motion 0.001, so 2.5 moves, it just moves less."""
    if str(job.get("video_engine") or "ltx23") == "ltx25":
        return video_graph_25(job, staged_image)'''
assert old in t
t = t.replace(old, new, 1)

# the 2.5 builder, appended
t = t.rstrip("\n") + '''


def video_graph_25(job, staged_image):
    """LTX-2.5 i2v (51_ltx25_i2v.json). Node ids are the template's own, recorded in the
    workflow's `_` block: 395 image, 376 prompt, 373 negative, 362 seconds, 361 fps,
    383 the LLM prompt-expander switch, 339/338 the two sampler seeds, 75 prefix.

    The expander is left OFF by default: it rewrites the motion text into a long cinematic
    caption, which is lovely for a one-off and fatal for a film, where the same motion card
    must mean the same thing on every beat."""
    wf = load_wf("51_ltx25_i2v.json")
    seconds = float(job.get("seconds") or 4)
    set_path(wf, "395.inputs.image", staged_image)
    set_path(wf, "376.inputs.value", job.get("motion_text") or "gentle natural motion")
    if job.get("negative"):
        set_path(wf, "373.inputs.text", job["negative"])
    set_path(wf, "383.inputs.value", bool(job.get("prompt_expander")))
    set_path(wf, "362.inputs.value", max(1, int(round(seconds))))
    set_path(wf, "361.inputs.value", 24)
    set_path(wf, "339.inputs.noise_seed", int(job.get("seed") or 0))
    set_path(wf, "338.inputs.noise_seed", int(job.get("seed") or 0))
    set_path(wf, "75.inputs.filename_prefix",
             "claude-generated/rolled/%s" % job.get("id", "ltx25"))
    return wf
'''
ast.parse(t)
io.open(P, "w", encoding="utf-8", newline="").write(t)
print("engine: video_engine ltx23|ltx25")

# ---- the model card carries the measurement -----------------------------------------
sys.path.insert(0, "studio")
import cards
cid = "ltx_2_5_22b_distilled_transformer_comfy_int8_convrot"
p = "studio/models/%s.json" % cid
c = json.load(open(p, encoding="utf-8"))
c["status"] = "ready"
c["size_gb"] = round(os.path.getsize(os.path.expanduser(
    "~/ComfyUI/models/diffusion_models/"
    "ltx-2.5-22b-distilled-transformer-comfy-int8-convrot.safetensors")) / 1e9, 2)
c["desc"] = ("MEASURED on this box 2026-08-15 against LTX-2.3, one keyframe, same seed "
             "and motion text: 2.5 HOLDS the approved keyframe (drift -0.004 - the last "
             "frame is as close as the first) where 2.3 walks off it (drift 0.141); 2.5 "
             "moves less (motion 1.54 vs 8.79; static floor 0.001, so it does move); "
             "25.7s vs 27.0s for 4s at 1280x704 with audio. NATIVE MULTI-SHOT CONFIRMED: "
             "asked for three viewpoints with 'CUT TO', it produced wide -> extreme "
             "close-up of the same face -> high overhead, in ONE pass, character and "
             "world holding across the cuts (samples/multishot/linruo_views_strip.png). "
             "That capability did not exist on this box before. Cuts fire on different "
             "VIEWPOINTS; three descriptions of one continuous action render as one "
             "continuous shot, correctly.")
c["strengths"] = ("keyframe fidelity (no drift), native multi-shot with a real cut, "
                  "4K-capable, synchronised audio, distilled 8-step speed")
c["weaknesses"] = ("~5x less in-frame motion than 2.3; the LLM prompt expander rewrites "
                   "motion text (leave off for films); 38 GB of weights")
c["strip"] = "samples/multishot/linruo_views_strip.png"
with open(p, "w", encoding="utf-8") as f:
    json.dump(c, f, indent=2, ensure_ascii=False)
    f.write("\\n")
cards.stamp("models", cid, "MEASURED",
            "ltx25_probe + clipmetrics vs 2.3, and multishot.py cut detection",
            note="holds the keyframe (drift -0.004 vs 2.3's 0.141), moves less (1.54 vs "
                 "8.79), 25.7s vs 27.0s; native multi-shot confirmed on viewpoint cuts")
print("model card: ltx-2.5 ready + measured")
