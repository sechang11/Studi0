#!/usr/bin/env python3
"""
video_engines.py - settle LTX-2.3 vs Wan 2.2 for this project's keyframe-first i2v pipeline.

THE QUESTION
------------
CAPABILITIES.md asserts "Wan still wins on image-to-video fidelity - if you have an exact
keyframe you want animated faithfully, Wan holds it better."  Nothing in the repo measured
that.  This project is keyframe-first: every clip starts from a keyframe that cost a full
style+place+character compose.  If the assertion is true, short.py is using the wrong engine
for its own shape.

WHAT THIS TOOL DOES
-------------------
  stage    scale N keyframes to ONE resolution both engines take natively, no distortion.
           The staged PNG is the reference for every later measurement - both engines are
           handed the same file, and clip frames are compared to it with no rescaling.
  render   submit a config matrix to ComfyUI, non-blocking, record wall clock per job.
  measure  two families of number (see below), written to results.json.
  strips   frame strips (keyframe | f0 | 25% | 50% | 75% | last) for LOOKING at.

THE TWO FAMILIES OF NUMBER
--------------------------
FIDELITY - "did the engine redraw my keyframe".  Reference is the staged PNG.
  kf_ssim_f0      SSIM of clip frame 0 vs keyframe.  THE CLEAN NUMBER: at frame 0 nothing
                  should have moved yet, so everything lost here is codec + VAE + redraw.
  kf_psnr_f0      same in dB.
  kf_ssim_last    SSIM of the final frame vs keyframe.  CONFOUNDED BY INTENDED MOTION - a
                  clip that correctly animates scores low here.  Read it against motion.
  pal_drift       mean |delta| of the 3x64-bin RGB histogram, keyframe vs final frame,
                  normalised to [0,1].  Motion-TOLERANT: things moving around inside the
                  frame barely change the histogram, but a palette shift does.  This is the
                  number that catches "the style left" without punishing animation.
  detail_kf       high-band amplitude of final frame / that of the keyframe.  Did the fine
                  texture survive, independent of where it went.

TEMPORAL - MAP 2's metric, reimplemented.  Frame-to-frame luma diff split by a sigma=2
gaussian at 512px into a LOW band (structure = real motion) and a HIGH band (fine texture).
  motion  mean low-band YDIF          churn  sd(low)/mean(low)
  boil    mean high-band YDIF / mean high-band amplitude
  detail  high-band amplitude, last eighth / frame 0

  NOTE THE REGEX.  MAP 2 found that `YDIF=([\\d.]+)` truncates scientific notation, so
  `YDIF=1.9e-06` reads as 1.9 and a frozen clip measures as fast motion.  That bug is live
  in scripts/analyze_shots.py:55.  This file uses `=([-+0-9.eE]+)`.

  NOTE THE FPS PROBLEM.  LTX renders 24fps, Wan 16fps, both hardcoded in their graphs.
  Per-frame YDIF is not comparable across different frame rates: the same physical motion
  gives a bigger per-frame delta at 16fps.  So every temporal number is ALSO computed on a
  common 8fps time base (LTX keeps every 3rd frame, Wan every 2nd - exact integer decimation,
  no interpolation, no resampling artifacts).  The `_t8` numbers are the cross-engine ones.
  The native numbers are only comparable within an engine.
"""
import argparse, json, math, os, re, statistics, subprocess, sys, time, urllib.request, uuid
from pathlib import Path

COMFY_HOST = os.environ.get("COMFY_HOST", "127.0.0.1:8188")
COMFY_ROOT = Path(os.environ.get("COMFY_ROOT", str(Path.home() / "ComfyUI")))
HERE = Path(__file__).resolve().parent
STUDIO = HERE.parent
OUT = STUDIO / "samples" / "video_engines"
STAGE_DIR = COMFY_ROOT / "input" / "ve"
CLIENT = str(uuid.uuid4())

# ----------------------------------------------------------------- shared render constants
W, H = 896, 512          # /32 for LTX, /16 for Wan, and 1.75 - a 1624x928 centre crop of a
                         # 1664x928 keyframe scales here with NO aspect distortion.
LTX_FPS, WAN_FPS = 24, 16
LTX_FRAMES, WAN_FRAMES = 97, 65     # 4.042s @24 (8n+1) and 4.063s @16 (4n+1)
COMMON_FPS = 8                      # 24/3 == 16/2, exact for both

# The one negative both engines get.  short.py sets node 11 on NEITHER of its workflows, so
# every LTX clip ever rendered here used the file default while film.py's Wan path used
# NEG_VID.  Comparing those two would measure the bug, not the engines.  Both get this.
NEG = ("static, frozen, blurry, distorted, morphing, warping, ugly, low quality, "
       "watermark, text overlay")

KEYFRAMES = {
    "kfA": dict(
        src="claude-generated/12-shorts/the-clash/keyframes/150_lock_00001_.png",
        motion=("Two fighters strain against each other, blades locked and grinding. "
                "Sparks spray from the point of contact. Their arms tremble with effort."),
        note="two faces, hard-edged sword, sparks, armour and fur texture - the hard case"),
    "kfB": dict(
        src="claude-generated/12-shorts/the-derby/keyframes/020_rask_00001_.png",
        motion=("He breathes out slowly and blinks once. His hair shifts slightly in the "
                "air. The light behind him flickers."),
        note="single face, flat cel anime, mid crop - the identity case"),
    "kfC": dict(
        src="claude-generated/12-shorts/the-clash/keyframes/010_ridge_00001_.png",
        motion=("Wind tears at his cloak and hair. Storm clouds boil and move fast behind "
                "him. Embers blow past. He does not move."),
        note="wide, atmospheric sky and embers - the environment case"),
    "kfD": dict(
        src="claude-generated/12-shorts/the-clash/keyframes/020_beast_00001_.png",
        motion="The beast roars.",
        note="transition endpoint only - the-clash beat 020, the real cut after kfC"),
    "kfE": dict(
        src="claude-generated/12-shorts/the-clash/keyframes/160_answer_00001_.png",
        motion="He answers the blow.",
        note="transition endpoint only - the-clash beat 160, the real cut after kfA"),
    # SHIPPING RESOLUTION.  short.py:66 hardcodes VID = (1280, 704) for every clip in every
    # film, so the cost ratio that matters is the one measured there, not at 896x512.
    # 1280/704 = 1.818, so the source crop is 1664x915 - again no aspect distortion.
    "kfCbig": dict(
        src="claude-generated/12-shorts/the-clash/keyframes/010_ridge_00001_.png",
        motion=("Wind tears at his cloak and hair. Storm clouds boil and move fast behind "
                "him. Embers blow past. He does not move."),
        res=(1280, 704), crop=(1664, 915),
        note="kfC at short.py's actual render size"),
    "kfAbig": dict(
        src="claude-generated/12-shorts/the-clash/keyframes/150_lock_00001_.png",
        motion=("Two fighters strain against each other, blades locked and grinding. "
                "Sparks spray from the point of contact. Their arms tremble with effort."),
        res=(1280, 704), crop=(1664, 915),
        note="kfA at short.py's actual render size"),
}


# THE PROMPT COMPILED FILMS ACTUALLY GET.  compile.py:603 assigns this identical string to
# every beat of every .movie file - it is the only assignment to `motion` in the compiler.
# The drift measured above used authored per-beat prose, so it has to be re-checked under
# the string production really sends, at the resolution production really renders.
for _k, _big in (("kfCslow", "kfCbig"), ("kfAslow", "kfAbig")):
    KEYFRAMES[_k] = dict(KEYFRAMES[_big], motion="Slow deliberate movement only.",
                         note=f"{_big} with compile.py:603's constant motion string")


def kf_res(kf):
    return KEYFRAMES[kf].get("res", (W, H))

# Region boxes for the IDENTITY test.  A whole-frame SSIM cannot see a face: the face is a
# few percent of the pixels, so a face that melts moves the global number by almost nothing.
# ltx-2.3-id-lora-talkvid-3k targets exactly that, so it has to be scored on the face alone.
# w:h:x:y in staged 896x512 coordinates, read off the staged PNG by eye.
FACE_BOX = {
    "kfB": (288, 256, 360, 40),      # eyes, grin, jaw
    "kfA": (256, 224, 200, 96),      # the human fighter's head
    "kfC": (160, 160, 380, 150),     # the distant figure on the ridge - small on purpose
}

# Real consecutive cuts from films/clash.json, used as transition endpoints.
TRANSITIONS = {
    "trA": dict(start="kfC", end="kfD",
                motion="The camera whips from the ridge to the beast as it rears up."),
    "trB": dict(start="kfA", end="kfE",
                motion="The blade lock breaks and he swings back into the answering blow."),
}

# --------------------------------------------------------------------------- graph builders
def ltx_graph(kf_file, motion, frames=LTX_FRAMES, seed=1234, distill=0.5,
              img_compression=18, i2v_strength=1.0, steps=None, prefix="ve/x",
              id_lora=None, id_strength=1.0, w=W, h=H):
    """workflows/12_ltx23_i2v_audio.json, parameterised.

    distill=None removes the speed LoRA entirely and swaps node 30's ManualSigmas (the
    8-step distilled schedule) for LTXVScheduler at `steps`.  workflows/11._notes says not
    to do this because 'the distilled LoRA on node 5 expects these exact sigmas' - which is
    true, and is exactly why removing the LoRA means the sigmas must go too.
    """
    g = {
        "1": {"class_type": "CheckpointLoaderSimple",
              "inputs": {"ckpt_name": "ltx-2.3-22b-dev-fp8.safetensors"}},
        "2": {"class_type": "LTXAVTextEncoderLoader",
              "inputs": {"text_encoder": "gemma_3_12B_it_fp4_mixed.safetensors",
                         "ckpt_name": "ltx-2.3-22b-dev-fp8.safetensors", "device": "default"}},
        "3": {"class_type": "LTXVAudioVAELoader",
              "inputs": {"ckpt_name": "ltx-2.3-22b-dev-fp8.safetensors"}},
        "8": {"class_type": "LoadImage", "inputs": {"image": kf_file, "upload": "image"}},
        "9": {"class_type": "LTXVPreprocess",
              "inputs": {"image": ["8", 0], "img_compression": img_compression}},
        "10": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["2", 0], "text": motion}},
        "11": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["2", 0], "text": NEG}},
        "12": {"class_type": "LTXVConditioning",
               "inputs": {"positive": ["10", 0], "negative": ["11", 0],
                          "frame_rate": float(LTX_FPS)}},
        "20": {"class_type": "EmptyLTXVLatentVideo",
               "inputs": {"width": w, "height": h, "length": frames, "batch_size": 1}},
        "23": {"class_type": "LTXVImgToVideoInplace",
               "inputs": {"vae": ["1", 2], "image": ["9", 0], "latent": ["20", 0],
                          "strength": i2v_strength, "bypass": False}},
        "21": {"class_type": "LTXVEmptyLatentAudio",
               "inputs": {"audio_vae": ["3", 0], "frames_number": frames,
                          "frame_rate": 25, "batch_size": 1}},
        "22": {"class_type": "LTXVConcatAVLatent",
               "inputs": {"video_latent": ["23", 0], "audio_latent": ["21", 0]}},
        "31": {"class_type": "CFGGuider",
               "inputs": {"model": None, "positive": ["12", 0], "negative": ["12", 1],
                          "cfg": 1.0}},
        "32": {"class_type": "RandomNoise", "inputs": {"noise_seed": seed}},
        "34": {"class_type": "KSamplerSelect", "inputs": {"sampler_name": "euler"}},
        "35": {"class_type": "SamplerCustomAdvanced",
               "inputs": {"noise": ["32", 0], "guider": ["31", 0], "sampler": ["34", 0],
                          "sigmas": ["30", 0], "latent_image": ["22", 0]}},
        "33": {"class_type": "LTXVSeparateAVLatent", "inputs": {"av_latent": ["35", 0]}},
        "40": {"class_type": "VAEDecode", "inputs": {"samples": ["33", 0], "vae": ["1", 2]}},
        "41": {"class_type": "LTXVAudioVAEDecode",
               "inputs": {"samples": ["33", 1], "audio_vae": ["3", 0]}},
        "42": {"class_type": "CreateVideo",
               "inputs": {"images": ["40", 0], "audio": ["41", 0], "fps": float(LTX_FPS)}},
        "43": {"class_type": "SaveVideo",
               "inputs": {"video": ["42", 0], "filename_prefix": prefix,
                          "format": "auto", "codec": "auto"}},
    }
    if distill is None:
        g["31"]["inputs"]["model"] = ["1", 0]
        g["30"] = {"class_type": "LTXVScheduler",
                   "inputs": {"steps": steps or 30, "max_shift": 2.05, "base_shift": 0.95,
                              "stretch": True, "terminal": 0.1, "latent": ["22", 0]}}
    else:
        g["5"] = {"class_type": "LoraLoaderModelOnly",
                  "inputs": {"model": ["1", 0],
                             "lora_name": "ltx_2.3_22b_distilled_1.1_lora_dynamic_"
                                          "fro09_avg_rank_111_bf16.safetensors",
                             "strength_model": distill}}
        g["31"]["inputs"]["model"] = ["5", 0]
        g["30"] = {"class_type": "ManualSigmas",
                   "inputs": {"sigmas": "1.0, 0.99375, 0.9875, 0.98125, 0.975, "
                                        "0.909375, 0.725, 0.421875, 0.0"}}
    if id_lora:
        # epic.py:458-466's pattern: a second LoraLoaderModelOnly as node 50, chained onto
        # whatever the model currently is.  short.py has no equivalent slot on the clip
        # stage at all, which is why none of the three extra LTX video LoRAs is wired.
        g["50"] = {"class_type": "LoraLoaderModelOnly",
                   "inputs": {"model": g["31"]["inputs"]["model"],
                              "lora_name": id_lora, "strength_model": id_strength}}
        g["31"]["inputs"]["model"] = ["50", 0]
    return g


def ltx_transition_graph(start_file, end_file, motion, frames=LTX_FRAMES, seed=1234,
                         distill=0.5, tr_strength=0.0, prefix="ve/x"):
    """First-frame + last-frame conditioning via LTXVAddGuide, optionally with
    ltx2.3-transition on top.

    TRANSCRIBED FROM ComfyUI's own `video_ltx2_3_flf2v.json` template subgraph
    "First-Last-Frame to Video (LTX-2.3)".  My first attempt was hand-built and died with
    `SamplerCustomAdvanced: cannot reshape tensor of 0 elements into shape [1, 0, 32, -1]`.
    Three things were wrong, all visible in the template:
      1. THE AV LATENT IS MANDATORY.  LTX-2.3 is an audio-video model; the sampler must be
         fed LTXVConcatAVLatent, never a bare video latent.  I had dropped the audio branch
         to avoid a frame-count coupling, and that is what produced the 0-element tensor.
      2. LTXVSeparateAVLatent takes SamplerCustomAdvanced output slot 1 in the template, not
         slot 0.  (workflows/12 in this repo uses slot 0 and works, so this is not
         load-bearing for plain i2v - recorded because it differs.)
      3. LTXVCropGuides runs AFTER the AV split, on the video latent, not on the raw
         sampler output.  Guide frames are removed there; decoding before that decodes them.
    Guide strength is 0.7 in the template, not 1.0 - kept as the template has it.
    """
    g = {
        "1": {"class_type": "CheckpointLoaderSimple",
              "inputs": {"ckpt_name": "ltx-2.3-22b-dev-fp8.safetensors"}},
        "2": {"class_type": "LTXAVTextEncoderLoader",
              "inputs": {"text_encoder": "gemma_3_12B_it_fp4_mixed.safetensors",
                         "ckpt_name": "ltx-2.3-22b-dev-fp8.safetensors", "device": "default"}},
        "5": {"class_type": "LoraLoaderModelOnly",
              "inputs": {"model": ["1", 0],
                         "lora_name": "ltx_2.3_22b_distilled_1.1_lora_dynamic_"
                                      "fro09_avg_rank_111_bf16.safetensors",
                         "strength_model": distill}},
        "8": {"class_type": "LoadImage", "inputs": {"image": start_file, "upload": "image"}},
        "18": {"class_type": "LoadImage", "inputs": {"image": end_file, "upload": "image"}},
        "9": {"class_type": "LTXVPreprocess",
              "inputs": {"image": ["8", 0], "img_compression": 18}},
        "19": {"class_type": "LTXVPreprocess",
               "inputs": {"image": ["18", 0], "img_compression": 18}},
        "10": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["2", 0], "text": motion}},
        "11": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["2", 0], "text": NEG}},
        "12": {"class_type": "LTXVConditioning",
               "inputs": {"positive": ["10", 0], "negative": ["11", 0],
                          "frame_rate": float(LTX_FPS)}},
        "20": {"class_type": "EmptyLTXVLatentVideo",
               "inputs": {"width": w, "height": h, "length": frames, "batch_size": 1}},
        "24": {"class_type": "LTXVAddGuide",
               "inputs": {"positive": ["12", 0], "negative": ["12", 1], "vae": ["1", 2],
                          "latent": ["20", 0], "image": ["9", 0],
                          "frame_idx": 0, "strength": 0.7}},
        "25": {"class_type": "LTXVAddGuide",
               "inputs": {"positive": ["24", 0], "negative": ["24", 1], "vae": ["1", 2],
                          "latent": ["24", 2], "image": ["19", 0],
                          "frame_idx": -1, "strength": 0.7}},
        "3": {"class_type": "LTXVAudioVAELoader",
              "inputs": {"ckpt_name": "ltx-2.3-22b-dev-fp8.safetensors"}},
        "21": {"class_type": "LTXVEmptyLatentAudio",
               "inputs": {"audio_vae": ["3", 0], "frames_number": frames,
                          "frame_rate": 25, "batch_size": 1}},
        "22": {"class_type": "LTXVConcatAVLatent",
               "inputs": {"video_latent": ["25", 2], "audio_latent": ["21", 0]}},
        "30": {"class_type": "ManualSigmas",
               "inputs": {"sigmas": "1.0, 0.99375, 0.9875, 0.98125, 0.975, "
                                    "0.909375, 0.725, 0.421875, 0.0"}},
        "31": {"class_type": "CFGGuider",
               "inputs": {"model": ["5", 0], "positive": ["25", 0], "negative": ["25", 1],
                          "cfg": 1.0}},
        "32": {"class_type": "RandomNoise", "inputs": {"noise_seed": seed}},
        "34": {"class_type": "KSamplerSelect", "inputs": {"sampler_name": "euler"}},
        "35": {"class_type": "SamplerCustomAdvanced",
               "inputs": {"noise": ["32", 0], "guider": ["31", 0], "sampler": ["34", 0],
                          "sigmas": ["30", 0], "latent_image": ["22", 0]}},
        "33": {"class_type": "LTXVSeparateAVLatent", "inputs": {"av_latent": ["35", 1]}},
        "36": {"class_type": "LTXVCropGuides",
               "inputs": {"positive": ["25", 0], "negative": ["25", 1],
                          "latent": ["33", 0]}},
        "40": {"class_type": "VAEDecode", "inputs": {"samples": ["36", 2], "vae": ["1", 2]}},
        "41": {"class_type": "LTXVAudioVAEDecode",
               "inputs": {"samples": ["33", 1], "audio_vae": ["3", 0]}},
        "42": {"class_type": "CreateVideo",
               "inputs": {"images": ["40", 0], "audio": ["41", 0], "fps": float(LTX_FPS)}},
        "43": {"class_type": "SaveVideo",
               "inputs": {"video": ["42", 0], "filename_prefix": prefix,
                          "format": "auto", "codec": "auto"}},
    }
    if tr_strength > 0:
        g["51"] = {"class_type": "LoraLoaderModelOnly",
                   "inputs": {"model": ["5", 0],
                              "lora_name": "ltx2.3-transition.safetensors",
                              "strength_model": tr_strength}}
        g["31"]["inputs"]["model"] = ["51", 0]
    return g


def wan_graph(kf_file, motion, frames=WAN_FRAMES, seed=1234, shift=8.0,
              lora_strength=1.0, prefix="ve/x", w=W, h=H):
    """workflows/04_wan22_i2v_turbo.json, parameterised.  Same node ids."""
    return {
        "1": {"class_type": "UNETLoader",
              "inputs": {"unet_name": "wan2.2_i2v_high_noise_14B_fp8_scaled.safetensors",
                         "weight_dtype": "default"}},
        "2": {"class_type": "UNETLoader",
              "inputs": {"unet_name": "wan2.2_i2v_low_noise_14B_fp8_scaled.safetensors",
                         "weight_dtype": "default"}},
        "3": {"class_type": "CLIPLoader",
              "inputs": {"clip_name": "umt5_xxl_fp8_e4m3fn_scaled.safetensors",
                         "type": "wan", "device": "default"}},
        "4": {"class_type": "VAELoader", "inputs": {"vae_name": "wan_2.1_vae.safetensors"}},
        "5": {"class_type": "LoraLoaderModelOnly",
              "inputs": {"model": ["1", 0],
                         "lora_name": "wan2.2_i2v_lightx2v_4steps_lora_v1_high_noise.safetensors",
                         "strength_model": lora_strength}},
        "6": {"class_type": "LoraLoaderModelOnly",
              "inputs": {"model": ["2", 0],
                         "lora_name": "wan2.2_i2v_lightx2v_4steps_lora_v1_low_noise.safetensors",
                         "strength_model": lora_strength}},
        "7": {"class_type": "ModelSamplingSD3", "inputs": {"model": ["5", 0], "shift": shift}},
        "8": {"class_type": "ModelSamplingSD3", "inputs": {"model": ["6", 0], "shift": shift}},
        "10": {"class_type": "LoadImage", "inputs": {"image": kf_file, "upload": "image"}},
        "11": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["3", 0], "text": motion}},
        "12": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["3", 0], "text": NEG}},
        "13": {"class_type": "WanImageToVideo",
               "inputs": {"positive": ["11", 0], "negative": ["12", 0], "vae": ["4", 0],
                          "width": w, "height": h, "length": frames, "batch_size": 1,
                          "start_image": ["10", 0]}},
        "14": {"class_type": "KSamplerAdvanced",
               "inputs": {"model": ["7", 0], "add_noise": "enable", "noise_seed": seed,
                          "steps": 4, "cfg": 1.0, "sampler_name": "euler",
                          "scheduler": "simple", "positive": ["13", 0],
                          "negative": ["13", 1], "latent_image": ["13", 2],
                          "start_at_step": 0, "end_at_step": 2,
                          "return_with_leftover_noise": "enable"}},
        "15": {"class_type": "KSamplerAdvanced",
               "inputs": {"model": ["8", 0], "add_noise": "disable", "noise_seed": 0,
                          "steps": 4, "cfg": 1.0, "sampler_name": "euler",
                          "scheduler": "simple", "positive": ["13", 0],
                          "negative": ["13", 1], "latent_image": ["14", 0],
                          "start_at_step": 2, "end_at_step": 4,
                          "return_with_leftover_noise": "disable"}},
        "16": {"class_type": "VAEDecode", "inputs": {"samples": ["15", 0], "vae": ["4", 0]}},
        "17": {"class_type": "CreateVideo",
               "inputs": {"images": ["16", 0], "fps": float(WAN_FPS)}},
        "18": {"class_type": "SaveVideo",
               "inputs": {"video": ["17", 0], "filename_prefix": prefix,
                          "format": "auto", "codec": "auto"}},
    }


# --------------------------------------------------------------------------- comfy plumbing
def post(path, payload):
    req = urllib.request.Request(f"http://{COMFY_HOST}{path}",
                                 data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req, timeout=60).read())


def get(path):
    return json.loads(urllib.request.urlopen(f"http://{COMFY_HOST}{path}", timeout=60).read())


def submit(graph):
    return post("/prompt", {"prompt": graph, "client_id": CLIENT})["prompt_id"]


def wait(pids, poll=4, timeout=7200):
    """Poll until every prompt id is out of the queue.  Returns {pid: record}."""
    done, t0 = {}, time.time()
    pending = set(pids)
    while pending:
        if time.time() - t0 > timeout:
            raise SystemExit(f"timeout, still pending: {pending}")
        h = get("/history?max_items=400")
        for pid in list(pending):
            if pid in h:
                done[pid] = h[pid]
                pending.discard(pid)
        if pending:
            time.sleep(poll)
    return done


def job_secs(rec):
    """Wall clock from ComfyUI's own execution messages - not from my poll loop."""
    msgs = rec.get("status", {}).get("messages", [])
    start = end = None
    for m in msgs:
        if not isinstance(m, list) or len(m) < 2:
            continue
        kind, data = m[0], m[1]
        ts = data.get("timestamp")
        if ts is None:
            continue
        if kind == "execution_start":
            start = ts
        elif kind in ("execution_success", "execution_error"):
            end = ts
    if start is None or end is None:
        return None
    return round((end - start) / 1000.0, 2)


def job_file(rec):
    for nid, o in rec.get("outputs", {}).items():
        for key in ("images", "videos", "gifs"):
            for item in o.get(key, []) or []:
                sub = item.get("subfolder", "")
                return COMFY_ROOT / "output" / sub / item["filename"]
    return None


def job_error(rec):
    for m in rec.get("status", {}).get("messages", []):
        if isinstance(m, list) and m and m[0] == "execution_error":
            d = m[1]
            return f"{d.get('node_type')}#{d.get('node_id')}: {str(d.get('exception_message'))[:300]}"
    if rec.get("status", {}).get("status_str") == "error":
        return "error (no message)"
    return None


# -------------------------------------------------------------------------------- measuring
NUM = r"=([-+0-9.eE]+)"     # NOT [\d.]+ - see module docstring
MW, SIGMA = 512, 2.0


def _ff(args):
    return subprocess.run(["ffmpeg", "-hide_banner", "-v", "error"] + args + ["-f", "null", "-"],
                          capture_output=True, text=True)


def _stat(path, vf, key, pre=""):
    vf = f"{pre}{vf},signalstats,metadata=print:key=lavfi.signalstats.{key}:file=-"
    r = _ff(["-i", str(path), "-vf", vf])
    return [float(x) for x in re.findall(key + NUM, r.stdout)]


def temporal(path, decimate=1):
    """MAP 2's metric.  decimate=n keeps every nth frame (integer, no interpolation)."""
    pre = "" if decimate == 1 else f"select='not(mod(n\\,{decimate}))',setpts=N/FRAME_RATE/TB,"
    lo_vf = f"scale={MW}:-2,format=gray,gblur=sigma={SIGMA}"
    hi_vf = (f"scale={MW}:-2,format=gray,split[a][b];[b]gblur=sigma={SIGMA}[lo];"
             f"[a][lo]blend=all_mode=grainextract")
    lo = _stat(path, lo_vf, "YDIF", pre)[1:]
    hi = _stat(path, hi_vf, "YDIF", pre)[1:]
    amp = _stat(path, hi_vf + ",lutyuv=y=abs(val-128)", "YAVG", pre)
    if not lo or not amp:
        return {}
    motion = statistics.mean(lo)
    tail = max(1, len(amp) // 8)
    return {
        "n": len(amp),
        "motion": round(motion, 4),
        "churn": round(statistics.pstdev(lo) / motion, 3) if motion > 1e-6 else 0.0,
        "boil": round(statistics.mean(hi) / statistics.mean(amp), 4)
                if statistics.mean(amp) > 1e-6 else 0.0,
        "detail": round(statistics.mean(amp[-tail:]) / amp[0], 3) if amp[0] > 1e-6 else 0.0,
        "hi_amp": round(statistics.mean(amp), 2),
    }


def _frame_png(clip, idx, dest):
    """Extract frame `idx` (0-based, negative = from end) losslessly."""
    if idx >= 0:
        sel = f"select='eq(n\\,{idx})'"
    else:
        sel = f"select='eq(n\\,{nframes(clip) + idx})'"
    subprocess.run(["ffmpeg", "-y", "-hide_banner", "-v", "error", "-i", str(clip),
                    "-vf", sel, "-vsync", "0", "-frames:v", "1",
                    "-pix_fmt", "rgb24", str(dest)], check=True)
    return dest


def nframes(clip):
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0",
                        "-count_frames", "-show_entries", "stream=nb_read_frames",
                        "-of", "csv=p=0", str(clip)], capture_output=True, text=True)
    return int(r.stdout.strip().split(",")[0])


def _pair(test_png, ref_png, filt):
    """`filt` must carry its own input labels, e.g. "[0][1]ssim".

    TWO BUGS LIVED HERE, both silent, both caught by checking the numbers rather than the
    exit code:
      1. -v error suppresses the ssim/psnr summary line (they log at INFO), so every score
         parsed as None.
      2. this function used to prepend "[0][1]" to a filter that already had it, producing
         "[0][1][0][1]ssim" -> "More input link labels than it has inputs: 4 > 2".
    Both returned None rather than raising.  If you touch this, assert on a known pair.
    """
    return subprocess.run(
        ["ffmpeg", "-hide_banner", "-v", "info", "-i", str(test_png), "-i", str(ref_png),
         "-lavfi", filt, "-f", "null", "-"],
        capture_output=True, text=True).stderr


def _selfcheck():
    """A PNG compared to itself must read SSIM 1.0.  Anything else means the metric is
    broken, and a broken metric here returns a plausible number, not an error."""
    p = STAGE_DIR / "kfA.png"
    if not p.exists():
        return
    m = re.search(r"All:([0-9.]+)", _pair(p, p, "[0][1]ssim"))
    if not m or abs(float(m.group(1)) - 1.0) > 1e-6:
        raise SystemExit(f"SSIM self-check FAILED (got {m.group(1) if m else None}, want 1.0)")


def fidelity(clip, kf_png, tmp, size=None):
    """Compare clip frame 0 and final frame to the reference keyframe PNG.

    Everything here is at native resolution - the staged keyframe IS the render resolution,
    so no rescaling enters the comparison.
    """
    f0 = _frame_png(clip, 0, tmp / "f0.png")
    fl = _frame_png(clip, -1, tmp / "fl.png")
    out = {}
    for tag, png in (("f0", f0), ("last", fl)):
        m = re.search(r"All:([0-9.]+)", _pair(png, kf_png, "[0][1]ssim"))
        out[f"kf_ssim_{tag}"] = round(float(m.group(1)), 4) if m else None
        m = re.search(r"average:([0-9.]+)", _pair(png, kf_png, "[0][1]psnr"))
        out[f"kf_psnr_{tag}"] = round(float(m.group(1)), 2) if m else None
    out["pal_drift"] = round(hist_dist(kf_png, fl), 4)
    a_kf, a_l = hi_amp(kf_png), hi_amp(fl)
    out["detail_kf"] = round(a_l / a_kf, 3) if a_kf > 1e-6 else None
    z, zs, s1 = zoom_est(kf_png, fl, tmp, size=size)
    out["zoom_est"] = z            # 1.0 = framing held; 1.25 = crept in 25%
    out["kf_ssim_last_dezoom"] = zs  # ssim after undoing that drift - fidelity WITHOUT the
    out["kf_ssim_last_z1"] = s1      # framing penalty.  s1 is the raw (== kf_ssim_last).
    return out


def zoom_est(kf_png, last_png, tmp, size=None, lo=1.00, hi=1.45, step=0.025):
    """Estimate how far the engine CREPT IN over the clip.

    Watching the strips, every config drifts toward a push-in - the subject is bigger in the
    last frame than in the keyframe, with no camera move requested anywhere.  That is an eye
    judgement, so this turns it into a number: scale the keyframe by z, centre-crop back to
    WxH, and take the z that best matches the final frame.  argmax SSIM over z.

    WHY IT MATTERS BEYOND THE ENGINE QUESTION: short.py's fx_chain adds `push`/`pull` as an
    ffmpeg zoompan AFTER generation.  If the model already drifts in, `push` compounds a
    move nobody asked for and `pull` fights it.
    Returns (best_z, ssim_at_best, ssim_at_z1).
    """
    size = size or (W, H)
    best, s1 = (1.0, -1.0), None
    z = lo
    while z <= hi + 1e-9:
        cand = tmp / "zoom_cand.png"
        # scale up by z then centre-crop back - i.e. simulate a push-in of z
        subprocess.run(["ffmpeg", "-y", "-hide_banner", "-v", "error", "-i", str(kf_png),
                        "-vf", f"scale=iw*{z:.4f}:ih*{z:.4f},crop={size[0]}:{size[1]}",
                        "-pix_fmt", "rgb24", str(cand)], check=True)
        m = re.search(r"All:([0-9.]+)", _pair(last_png, cand, "[0][1]ssim"))
        v = float(m.group(1)) if m else -1.0
        if abs(z - 1.0) < 1e-9:
            s1 = v
        if v > best[1]:
            best = (round(z, 3), round(v, 4))
        z += step
    return best[0], best[1], (round(s1, 4) if s1 is not None else None)


def crop_png(src, box, dest):
    w, h, x, y = box
    subprocess.run(["ffmpeg", "-y", "-hide_banner", "-v", "error", "-i", str(src),
                    "-vf", f"crop={w}:{h}:{x}:{y}", "-pix_fmt", "rgb24", str(dest)],
                   check=True)
    return dest


def face_fidelity(clip, kf_png, box, tmp):
    """Same fidelity numbers, restricted to the face box.

    WHY THIS EXISTS: the face is ~14% of kfB's pixels.  A face that melts completely moves
    whole-frame SSIM by a couple of points - inside the spread between seeds.  Any claim
    about an identity LoRA has to be scored where the identity is.
    """
    ref = crop_png(kf_png, box, tmp / "ref_face.png")
    out = {}
    for tag, idx in (("f0", 0), ("last", -1)):
        f = _frame_png(clip, idx, tmp / f"face_src_{tag}.png")
        c = crop_png(f, box, tmp / f"face_{tag}.png")
        m = re.search(r"All:([0-9.]+)", _pair(c, ref, "[0][1]ssim"))
        out[f"face_ssim_{tag}"] = round(float(m.group(1)), 4) if m else None
    return out


def face_temporal(clip, box, decimate=1):
    """MAP 2's temporal metric over the face box only.  Note the crop happens BEFORE the
    512px normalise, so the face is measured at higher effective resolution than it would
    be in the whole-frame pass - face numbers are comparable to each other, not to global."""
    w, h, x, y = box
    pre = f"crop={w}:{h}:{x}:{y},"
    if decimate != 1:
        pre = f"select='not(mod(n\\,{decimate}))',setpts=N/FRAME_RATE/TB,{pre}"
    lo_vf = f"scale={MW}:-2,format=gray,gblur=sigma={SIGMA}"
    hi_vf = (f"scale={MW}:-2,format=gray,split[a][b];[b]gblur=sigma={SIGMA}[lo];"
             f"[a][lo]blend=all_mode=grainextract")
    lo = _stat(clip, lo_vf, "YDIF", pre)[1:]
    hi = _stat(clip, hi_vf, "YDIF", pre)[1:]
    amp = _stat(clip, hi_vf + ",lutyuv=y=abs(val-128)", "YAVG", pre)
    if not lo or not amp:
        return {}
    mo = statistics.mean(lo)
    return {"face_motion": round(mo, 4),
            "face_churn": round(statistics.pstdev(lo) / mo, 3) if mo > 1e-6 else 0.0,
            "face_boil": round(statistics.mean(hi) / statistics.mean(amp), 4)
                         if statistics.mean(amp) > 1e-6 else 0.0}


def hi_amp(png):
    vf = (f"scale={MW}:-2,format=gray,split[a][b];[b]gblur=sigma={SIGMA}[lo];"
          f"[a][lo]blend=all_mode=grainextract,lutyuv=y=abs(val-128)")
    v = _stat(png, vf, "YAVG")
    return v[0] if v else 0.0


def hist_dist(png_a, png_b, bins=64):
    """L1 distance between 3x`bins` RGB histograms, normalised to [0,1].

    Motion-tolerant by construction: moving content around the frame leaves the histogram
    almost unchanged, but losing the palette does not.
    """
    def h(p):
        r = subprocess.run(
            ["ffmpeg", "-hide_banner", "-v", "error", "-i", str(p), "-vf",
             "format=rgb24,signalstats,metadata=print:file=-", "-f", "null", "-"],
            capture_output=True, text=True)
        # signalstats does not give a full histogram; do it with a raw pipe instead.
        raw = subprocess.run(
            ["ffmpeg", "-hide_banner", "-v", "error", "-i", str(p), "-vf", "format=rgb24",
             "-f", "rawvideo", "-"], capture_output=True)
        d = raw.stdout
        counts = [[0] * bins for _ in range(3)]
        step = 256 // bins
        for i in range(0, len(d) - 2, 3):
            counts[0][d[i] // step] += 1
            counts[1][d[i + 1] // step] += 1
            counts[2][d[i + 2] // step] += 1
        n = max(1, len(d) // 3)
        return [[c / n for c in ch] for ch in counts]
    ha, hb = h(png_a), h(png_b)
    tot = sum(abs(a - b) for ca, cb in zip(ha, hb) for a, b in zip(ca, cb))
    return tot / 6.0     # 3 channels x max L1 of 2 each


# ------------------------------------------------------------------------------ subcommands
def cmd_stage(a):
    STAGE_DIR.mkdir(parents=True, exist_ok=True)
    for k, v in KEYFRAMES.items():
        src = COMFY_ROOT / "output" / v["src"]
        if not src.exists():
            raise SystemExit(f"missing keyframe {src}")
        dst = STAGE_DIR / f"{k}.png"
        rw, rh = v.get("res", (W, H))
        cw, ch = v.get("crop", (1624, 928))
        subprocess.run(["ffmpeg", "-y", "-hide_banner", "-v", "error", "-i", str(src),
                        "-vf", f"crop={cw}:{ch},scale={rw}:{rh}:flags=lanczos",
                        "-pix_fmt", "rgb24", str(dst)], check=True)
        print(f"staged {dst}  {v['note']}")


def matrix(name):
    """Config matrix.  Every row: (id, engine, kwargs).  Same seed everywhere."""
    rows = []
    kfs = ["kfA", "kfB", "kfC"]
    if name == "main":
        for kf in kfs:
            rows += [
                (f"{kf}__ltx_distill05", "ltx", dict(distill=0.5)),
                (f"{kf}__ltx_distill10", "ltx", dict(distill=1.0)),
                (f"{kf}__ltx_nodistill30", "ltx", dict(distill=None, steps=30)),
                (f"{kf}__wan_lightx2v", "wan", dict()),
            ]
    elif name == "wanshift":
        for kf in kfs:
            rows += [(f"{kf}__wan_shift5", "wan", dict(shift=5.0))]
    elif name == "ltxstrength":
        for kf in kfs:
            rows += [(f"{kf}__ltx_str06", "ltx", dict(distill=0.5, i2v_strength=0.6)),
                     (f"{kf}__ltx_crf0", "ltx", dict(distill=0.5, img_compression=0))]
    elif name == "idlora":
        # ltx-2.3-id-lora-talkvid-3k, on the face keyframes.  0.0 is the control and is the
        # SAME GRAPH with the LoRA node absent, not strength 0 - a LoRA at 0 still perturbs.
        LID = "ltx-2.3-id-lora-talkvid-3k.safetensors"
        for kf in ("kfB", "kfA"):
            rows += [
                (f"{kf}__id_off", "ltx", dict(distill=0.5)),
                (f"{kf}__id_050", "ltx", dict(distill=0.5, id_lora=LID, id_strength=0.5)),
                (f"{kf}__id_100", "ltx", dict(distill=0.5, id_lora=LID, id_strength=1.0)),
            ]
    elif name == "bigres":
        # short.py hardcodes 1280x704 (VID, line 66).  Everything above is 896x512, where
        # Wan costs 2.4x LTX - but CAPABILITIES.md's 8x claim is a 720p number, and the
        # recommendation turns on the cost at the resolution the project actually renders.
        for kf in ("kfCbig", "kfAbig"):
            rows += [(f"{kf}__big_ltx", "ltx", dict(distill=0.5)),
                     (f"{kf}__big_wan", "wan", dict())]
    elif name == "prodprompt":
        for kf in ("kfCslow", "kfAslow"):
            for sd in (1234, 777, 31337):
                rows += [(f"{kf}__pp{sd}_ltx", "ltx", dict(distill=0.5, seed=sd)),
                         (f"{kf}__pp{sd}_wan", "wan", dict(seed=sd))]
    elif name == "bigseeds":
        # THE DECIDING RUN.  At 896x512 LTX's unrequested push-in ranged 1.0-1.45 across
        # seeds while Wan sat at 1.0-1.05.  At 1280x704 - the size short.py actually renders
        # - the first LTX sample showed almost no drift.  One sample cannot settle that
        # against a spread that wide, and the recommendation depends on it, so the seed
        # sweep is repeated at the shipping resolution.
        for kf in ("kfCbig", "kfAbig"):
            for s in (777, 31337, 90210):
                rows += [(f"{kf}__bs{s}_ltx", "ltx", dict(distill=0.5, seed=s)),
                         (f"{kf}__bs{s}_wan", "wan", dict(seed=s))]
    elif name == "seeds":
        # The zoom-drift gap is the headline result, so it does not get to rest on one seed.
        # kfA and kfC are the two keyframes that drifted; kfB drifted on neither engine.
        for kf in ("kfA", "kfC"):
            for s in (777, 31337, 90210):
                rows += [(f"{kf}__s{s}_ltx", "ltx", dict(distill=0.5, seed=s)),
                         (f"{kf}__s{s}_wan", "wan", dict(seed=s))]
    elif name == "transition":
        for t in TRANSITIONS:
            rows += [(f"{t}__tr_off", "tr", dict(tr_strength=0.0)),
                     (f"{t}__tr_100", "tr", dict(tr_strength=1.0))]
    else:
        raise SystemExit(f"unknown matrix {name}")
    # GROUP BY ENGINE.  Interleaving LTX and Wan makes ComfyUI evict and reload a 14B model
    # family on nearly every job; CAPABILITIES.md:110 puts that swap at ~90s.  Grouping means
    # each family loads once, and only the first job of each family carries the load cost -
    # which is why `cold` is recorded per job rather than averaged away.
    rows.sort(key=lambda r: (r[1], r[0].split("__")[1], r[0]))
    return [(rid, eng, rid.split("__")[0], kw) for rid, eng, kw in rows]


def cmd_render(a):
    OUT.mkdir(parents=True, exist_ok=True)
    rows = matrix(a.matrix)
    if a.only:
        rows = [r for r in rows if a.only in r[0]]
    jobs, meta, seen_engine = [], {}, set()
    for rid, eng, kf, kw in rows:
        kw = dict(kw)
        seed = kw.pop("seed", a.seed)      # a matrix row may pin its own seed
        prefix = f"ve/{rid}"
        if eng == "tr":
            t = TRANSITIONS[kf]
            g = ltx_transition_graph(f"ve/{t['start']}.png", f"ve/{t['end']}.png",
                                     t["motion"], seed=seed, prefix=prefix, **kw)
        elif eng == "ltx":
            rw, rh = kf_res(kf)
            g = ltx_graph(f"ve/{kf}.png", KEYFRAMES[kf]["motion"], seed=seed,
                          prefix=prefix, w=rw, h=rh, **kw)
        else:
            rw, rh = kf_res(kf)
            g = wan_graph(f"ve/{kf}.png", KEYFRAMES[kf]["motion"], seed=seed,
                          prefix=prefix, w=rw, h=rh, **kw)
        pid = submit(g)
        jobs.append(pid)
        meta[pid] = dict(id=rid, engine=eng, kf=kf, cfg=str(kw), seed=seed,
                         cold=eng not in seen_engine)
        seen_engine.add(eng)
        print(f"submitted {rid} -> {pid}")
    print(f"waiting on {len(jobs)} jobs ...", flush=True)
    recs = wait(jobs)
    manifest = []
    for pid in jobs:
        rec = recs[pid]
        m = meta[pid]
        err = job_error(rec)
        f = job_file(rec)
        m["secs"] = job_secs(rec)
        m["file"] = str(f) if f else None
        m["error"] = err
        manifest.append(m)
        print(f"{m['id']:34s} {str(m['secs']):>8s}s  {err or (f.name if f else 'NO OUTPUT')}")
    p = OUT / f"manifest_{a.matrix}.json"
    prev = json.loads(p.read_text()) if p.exists() and a.append else []
    p.write_text(json.dumps(prev + manifest, indent=2))
    print(f"wrote {p}")


def cmd_measure(a):
    _selfcheck()
    tmp = Path("/tmp/ve_measure"); tmp.mkdir(exist_ok=True)
    rows = []
    for mp in sorted(OUT.glob("manifest_*.json")):
        rows += json.loads(mp.read_text())
    res = []
    for m in rows:
        if not m.get("file") or not Path(m["file"]).exists():
            print(f"skip {m['id']}: no file"); continue
        clip = Path(m["file"])
        r = dict(m)
        dec = WAN_FPS // COMMON_FPS if m["engine"] == "wan" else LTX_FPS // COMMON_FPS

        if m["engine"] == "tr":
            # A transition is scored on whether it LANDS: frame 0 against the start
            # keyframe, final frame against the END keyframe.  Nothing else about it
            # matters if it does not arrive.
            t = TRANSITIONS[m["kf"]]
            s_png, e_png = STAGE_DIR / f"{t['start']}.png", STAGE_DIR / f"{t['end']}.png"
            f0 = _frame_png(clip, 0, tmp / "f0.png")
            fl = _frame_png(clip, -1, tmp / "fl.png")
            for tag, png, ref in (("start", f0, s_png), ("end", fl, e_png),
                                  ("end_vs_start", fl, s_png)):
                mm = re.search(r"All:([0-9.]+)", _pair(png, ref, "[0][1]ssim"))
                r[f"ssim_{tag}"] = round(float(mm.group(1)), 4) if mm else None
            r["native"] = temporal(clip, 1)
            r["t8"] = temporal(clip, dec)
            print(f"{m['id']:34s} ssim_to_START={r['ssim_start']} "
                  f"ssim_to_END={r['ssim_end']} (end-vs-start {r['ssim_end_vs_start']}) "
                  f"motion8={r['t8'].get('motion')}")
            res.append(r); continue

        kf_png = STAGE_DIR / f"{m['kf']}.png"
        r.update(fidelity(clip, kf_png, tmp, size=kf_res(m["kf"])))
        r["native"] = temporal(clip, 1)
        r["t8"] = temporal(clip, dec)
        box = FACE_BOX.get(m["kf"])
        if box:
            r.update(face_fidelity(clip, kf_png, box, tmp))
            r.update(face_temporal(clip, box, dec))
        res.append(r)
        print(f"{m['id']:22s} f0={r['kf_ssim_f0']} last={r['kf_ssim_last']} "
              f"zoom={r['zoom_est']} dezoom={r['kf_ssim_last_dezoom']} "
              f"pal={r['pal_drift']} det={r['detail_kf']} "
              f"mo8={r['t8'].get('motion')} boil8={r['t8'].get('boil')} "
              f"face={r.get('face_ssim_last')}")
    (OUT / "results.json").write_text(json.dumps(res, indent=2))
    print(f"wrote {OUT/'results.json'}  ({len(res)} clips)")


def cmd_floor(a):
    """THE MEASUREMENT CEILING.  No engine can score above this.

    Both engines save through the identical path - ComfyUI SaveVideo, h264, yuv420p, same
    WxH (verified with ffprobe) - so the ENGINE COMPARISON is clean no matter what this
    number is.  The floor only tells you how to read the absolute value: an RGB PNG through
    h264 4:2:0 loses chroma resolution before any model is involved.
    """
    _selfcheck()
    tmp = Path("/tmp/ve_floor"); tmp.mkdir(exist_ok=True)
    print(f"{'ref':6s} {'crf':>4s} {'ssim':>8s} {'psnr':>7s}")
    rows = {}
    for kf in KEYFRAMES:
        png = STAGE_DIR / f"{kf}.png"
        for crf in (18, 23):
            mp4 = tmp / f"{kf}_{crf}.mp4"
            subprocess.run(["ffmpeg", "-y", "-hide_banner", "-v", "error", "-loop", "1",
                            "-i", str(png), "-t", "1", "-r", "24", "-c:v", "libx264",
                            "-crf", str(crf), "-pix_fmt", "yuv420p", str(mp4)], check=True)
            f0 = _frame_png(mp4, 0, tmp / "f0.png")
            s = re.search(r"All:([0-9.]+)", _pair(f0, png, "[0][1]ssim"))
            p = re.search(r"average:([0-9.]+)", _pair(f0, png, "[0][1]psnr"))
            s, p = float(s.group(1)), float(p.group(1))
            rows[f"{kf}_crf{crf}"] = dict(ssim=round(s, 4), psnr=round(p, 2))
            print(f"{kf:6s} {crf:>4d} {s:>8.4f} {p:>7.2f}")
    (OUT / "floor.json").write_text(json.dumps(rows, indent=2))


def cmd_strips(a):
    """keyframe | f0 | 25% | 50% | 75% | last, one strip per clip."""
    rows = json.loads((OUT / "results.json").read_text())
    sd = OUT / "strips"; sd.mkdir(parents=True, exist_ok=True)
    tmp = Path("/tmp/ve_strip"); tmp.mkdir(exist_ok=True)
    for m in rows:
        clip = Path(m["file"]); n = nframes(clip)
        idxs = [0, n // 4, n // 2, (3 * n) // 4, n - 1]
        if m["engine"] == "tr":
            t = TRANSITIONS[m["kf"]]
            # bookend the strip: START keyframe | clip | END keyframe, so a transition that
            # fails to arrive is visible without cross-referencing anything.
            parts = ([str(STAGE_DIR / f"{t['start']}.png")], [str(STAGE_DIR / f"{t['end']}.png")])
            parts, tail = parts[0], parts[1]
        else:
            parts, tail = [str(STAGE_DIR / f"{m['kf']}.png")], []
        for i, ix in enumerate(idxs):
            p = tmp / f"{m['id']}_{i}.png"
            _frame_png(clip, ix, p); parts.append(str(p))
        parts += tail
        args = ["ffmpeg", "-y", "-hide_banner", "-v", "error"]
        for p in parts:
            args += ["-i", p]
        args += ["-filter_complex",
                 "".join(f"[{i}]scale=440:-1,pad=iw+4:ih+4:2:2:0x303030[v{i}];"
                         for i in range(len(parts)))
                 + "".join(f"[v{i}]" for i in range(len(parts)))
                 + f"hstack=inputs={len(parts)}",
                 "-frames:v", "1", str(sd / f"{m['id']}.png")]
        subprocess.run(args, check=True)
        print(f"strip {m['id']}")


def cmd_summary(a):
    """Aggregate results.json into the table the recommendation is actually read off.

    Grouped by (keyframe, engine-config) and reported as mean [min-max] across seeds,
    because the single most important number here - LTX's unrequested push-in - has a
    seed spread wider than its own mean at 896x512.  A mean without its range would have
    hidden that completely.
    """
    rows = [r for r in json.loads((OUT / "results.json").read_text())
            if r["engine"] != "tr"]
    groups = {}
    for r in rows:
        cfg = r["id"].split("__")[1]
        cfg = re.sub(r"^[a-z]{0,2}\d+_", "", cfg)   # strip any seed tag: s777_, bs777_, pp777_
        groups.setdefault((r["kf"], cfg), []).append(r)

    def agg(rs, key, nested=None):
        vals = [(r[nested][key] if nested else r[key]) for r in rs
                if (r.get(nested, {}) if nested else r).get(key) is not None]
        if not vals:
            return "  -  "
        if len(vals) == 1:
            return f"{vals[0]:.3f}"
        return f"{statistics.mean(vals):.3f}[{min(vals):.2f}-{max(vals):.2f}]"

    hdr = (f"{'keyframe':9s} {'config':16s} {'n':>2s} {'secs':>6s} {'ssim_f0':>17s} "
           f"{'ZOOM_DRIFT':>17s} {'detail_kf':>17s} {'face_last':>17s} {'boil8':>17s}")
    print(hdr); print("-" * len(hdr))
    out = {}
    for (kf, cfg), rs in sorted(groups.items()):
        secs = [r["secs"] for r in rs if r.get("secs")]
        line = (f"{kf:9s} {cfg:16s} {len(rs):>2d} "
                f"{(statistics.mean(secs) if secs else 0):>6.1f} "
                f"{agg(rs,'kf_ssim_f0'):>17s} {agg(rs,'zoom_est'):>17s} "
                f"{agg(rs,'detail_kf'):>17s} {agg(rs,'face_ssim_last'):>17s} "
                f"{agg(rs,'boil',nested='t8'):>17s}")
        print(line)
        out[f"{kf}|{cfg}"] = dict(
            n=len(rs), secs_mean=round(statistics.mean(secs), 2) if secs else None,
            zoom=[r["zoom_est"] for r in rs],
            ssim_f0=[r["kf_ssim_f0"] for r in rs],
            detail_kf=[r["detail_kf"] for r in rs],
            face_last=[r.get("face_ssim_last") for r in rs],
            boil8=[r["t8"].get("boil") for r in rs])
    (OUT / "summary.json").write_text(json.dumps(out, indent=2))
    print(f"\nwrote {OUT/'summary.json'}")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("stage")
    r = sub.add_parser("render")
    r.add_argument("--matrix", default="main")
    r.add_argument("--seed", type=int, default=1234)
    r.add_argument("--only", default=None)
    r.add_argument("--append", action="store_true")
    sub.add_parser("measure")
    sub.add_parser("strips")
    sub.add_parser("floor")
    sub.add_parser("summary")
    a = ap.parse_args()
    {"stage": cmd_stage, "render": cmd_render, "measure": cmd_measure,
     "strips": cmd_strips, "floor": cmd_floor,
     "summary": cmd_summary}[a.cmd](a)


if __name__ == "__main__":
    main()
