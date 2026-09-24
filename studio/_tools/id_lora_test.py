#!/usr/bin/env python3
"""Does the r/comfyui talking-head recipe say the words, in the chosen voice, with the same face?

THE CLAIM (r/comfyui "RTX 5090 vs. ComfyUI", 2026-09): an influencer talking head on LTX 2.3 is
"very easy" with an ID-LoRA and [VISUAL] / [SPEECH] / [SOUND] tagged prompts, "or the model won't
follow instructions". The ID-LoRA (TalkVid-3K) and ComfyUI's native LTXVReferenceAudio node have
both been on this box for weeks; workflow 70 loads that LoRA onto LTX-2.5 with no reference voice
and no tags, and nothing else uses it.

THE TEST. One start frame (mara-okonjo's portrait, cropped 16:9), one line, one reference voice
(Maya, 5 s), three seeds, three arms that each change one thing:

    prose    the line in quotes inside prose - how the studio writes a spoken line today
    tags     the same words in [VISUAL]: / [SPEECH]: / [SOUNDS]: sections       (format only)
    idlora   tags + the ID-LoRA + LTXVReferenceAudio with Maya's voice            (+ voice)

MEASURED on every take, with tools already on the box, nothing downloaded:
    words    content-word recall of the line, Granite Speech (shorts_asr's scorer; Granite
             paraphrases, so read recall as a floor)
    voice    cosine of Chatterbox's speaker encoder against Maya's reference clip, calibrated
             against a second, disjoint Maya clip (same speaker) and three other voices
    face     identity.py, first and last frame against the portrait

    ~/ComfyUI/venv/bin/python3 studio/_tools/id_lora_test.py [--seeds 11 202 3003] [--measure-only]
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import time

import numpy as np
from PIL import Image

ROOT = os.path.expanduser("~/shared/comfy-studio")
STUDIO = os.path.join(ROOT, "studio")
TOOLS = os.path.join(STUDIO, "_tools")
sys.path.insert(0, TOOLS)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
os.environ.setdefault("COMFY_HOST", "127.0.0.1:8188")
from comfy import run                      # noqa: E402
from epic import COMFY, HOST, load_wf      # noqa: E402
import headbox as HB                       # noqa: E402

PY = os.path.expanduser("~/ComfyUI/venv/bin/python3")
OUT = os.path.join(STUDIO, "samples", "id_lora")
PACK = "mara-okonjo"
PORTRAIT = os.path.join(STUDIO, "foundry", "characters", PACK, "base_portrait.png")
VX = os.path.expanduser("~/ComfyUI/custom_nodes/TTS-Audio-Suite/voices_examples")
VOICE = os.path.join(VX, "female", "female_04_maya.wav")
OTHERS = {"en_woman": os.path.join(VX, "higgs_audio", "en_woman.wav"),
          "mabel": os.path.join(VX, "higgs_audio", "mabel.wav"),
          "carter": os.path.join(VX, "male", "male_03_carter.wav")}
VE_SRC = os.path.expanduser("~/ComfyUI/custom_nodes/ComfyUI-Chatterbox/src")
VE_WEIGHTS = os.path.expanduser("~/ComfyUI/models/tts/chatterbox/resembleai_default_voice/ve.safetensors")
WF = "73_ltx23_id_lora_talking_head.json"

LINE = "Morning, everyone. Here are the three things I pack for every trip."
# The method: never describe what the start frame carries (a described face competes with the
# pictured one). Every arm carries the same information; only its arrangement differs.
LOOK = ("A medium close-up. The person in the frame looks directly at the camera and speaks with a "
        "warm, easy smile, mouth moving naturally with the words.")
CAMERA = "The camera is static with a faint handheld float."
SOUNDS = ("A warm, clear voice at a natural speaking pace; wind in long grass, a skylark far off. "
          "No music.")
PROMPTS = {
    "prose": '%s They say, "%s" %s %s' % (LOOK, LINE, CAMERA, SOUNDS),
    "tags": "[VISUAL]: %s %s\n[SPEECH]: %s\n[SOUNDS]: %s" % (LOOK, CAMERA, LINE, SOUNDS),
}
PROMPTS["idlora"] = PROMPTS["tags"]
ARMS = ("prose", "tags", "idlora")
# The same question on LTX-2.5, the studio's default engine. The ID-LoRA was trained on 2.3; its
# 864 target modules exist with the same names and shapes in the 2.5 transformer, so it LOADS -
# whether a 2.3 delta still carries a voice on 2.5 weights is what these two arms measure.
WF25 = "70_ltx25_i2v_lora.json"
ARMS25 = ("tags25", "idlora25")
PROMPTS["tags25"] = PROMPTS["idlora25"] = PROMPTS["tags"]


def sh(*a):
    return subprocess.run(a, capture_output=True, text=True)


def pcm(path, sr=16000):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-ac", "1", "-ar", str(sr),
                          "-f", "f32le", "-"], capture_output=True).stdout
    return np.frombuffer(raw, dtype=np.float32).copy()


def best_window(path, secs=5.0, avoid=None):
    """The 5 s of a voice file with the most voiced 20 ms frames (and outside `avoid`)."""
    x = pcm(path)
    hop = 320
    n = len(x) // hop
    rms = np.sqrt((x[:n * hop].reshape(n, hop) ** 2).mean(1) + 1e-12)
    voiced = rms > max(1e-4, 0.1 * np.percentile(rms, 95))
    win = int(secs / 0.02)
    best = None
    for s in range(0, max(1, n - win), 25):
        t0 = s * 0.02
        if avoid and not (t0 + secs <= avoid[0] or t0 >= avoid[1]):
            continue
        f = float(voiced[s:s + win].mean())
        if best is None or f > best[0]:
            best = (f, t0)
    return best


def cut(src, start, dst, secs=5.0):
    sh("ffmpeg", "-y", "-v", "error", "-ss", "%.2f" % start, "-t", "%.2f" % secs, "-i", src,
       "-ac", "1", "-ar", "24000", dst)
    return dst


def head_in_crop(box, h, top, ch):
    """The portrait's head box, carried into the 16:9 start frame. headbox.py finds a head at the
    top of a standing silhouette; on a close-up it returns a band of hair, so it is not asked."""
    return [round(box[0], 4), round(max(0.0, (box[1] * h - top) / ch), 4),
            round(box[2], 4), round(min(1.0, (box[3] * h - top) / ch), 4)]


def prepare():
    os.makedirs(OUT, exist_ok=True)
    # start frame: the portrait's full width at 16:9, the head in the upper part of the frame
    im = Image.open(PORTRAIT).convert("RGB")
    w, h = im.size
    ch = int(w * 9 / 16)
    box = HB.head_box(PORTRAIT)
    cy = (box[1] + box[3]) / 2 * h
    top = int(max(0, min(h - ch, cy - 0.38 * ch)))
    start = os.path.join(OUT, "start.png")
    im.crop((0, top, w, top + ch)).resize((1280, 720), Image.LANCZOS).save(start)
    shutil.copy(start, os.path.join(COMFY, "input", "idlora_start.png"))
    # the reference voice and its calibration set
    f, t = best_window(VOICE)
    ref = cut(VOICE, t, os.path.join(OUT, "voice_maya_ref.wav"))
    shutil.copy(ref, os.path.join(COMFY, "input", "idlora_voice.wav"))
    f2, t2 = best_window(VOICE, avoid=(t, t + 5.0))
    calib = {"maya (another 5 s)": cut(VOICE, t2, os.path.join(OUT, "voice_maya_other.wav"))}
    for name, src in OTHERS.items():
        _, tt = best_window(src)
        calib[name] = cut(src, tt, os.path.join(OUT, "voice_%s.wav" % name))
    meta = {"start_frame": start, "crop_top": top, "head_box": head_in_crop(box, h, top, ch),
            "reference": ref, "reference_window": [t, t + 5.0],
            "reference_voiced": round(f, 3), "calibration": calib}
    json.dump(meta, open(os.path.join(OUT, "prepare.json"), "w"), indent=1)
    return meta


def graph25(arm, seed):
    """Workflow 70 (LTX-2.5, two stages) wired the way ComfyUI's 2.3 ID-LoRA template wires 2.3:
    the reference voice conditions both stages, the LoRA and the identity guidance only the first."""
    wf = {k: v for k, v in load_wf(WF25).items() if isinstance(v, dict) and "class_type" in v}
    wf["sg1_383"]["inputs"]["value"] = False           # the Gemma prompt enhancer would rewrite the tags
    wf["sg1_376"]["inputs"]["value"] = PROMPTS[arm]
    wf["395"]["inputs"]["image"] = "idlora_start.png"
    wf["sg1_339"]["inputs"]["noise_seed"] = int(seed)
    wf["sg1_338"]["inputs"]["noise_seed"] = int(seed) + 1
    wf["75"]["inputs"]["filename_prefix"] = "claude-generated/idlora/%s_s%d" % (arm, seed)
    if arm == "idlora25":
        wf["lora"]["inputs"]["lora_name"] = "ltx-2.3-id-lora-talkvid-3k.safetensors"
        wf["lora"]["inputs"]["strength_model"] = 1.0
        wf["ref_audio"] = {"class_type": "LoadAudio", "inputs": {"audio": "idlora_voice.wav"}}
        wf["refa"] = {"class_type": "LTXVReferenceAudio",
                      "inputs": {"model": ["lora", 0], "positive": ["sg1_364", 0], "negative": ["sg1_373", 0],
                                 "reference_audio": ["ref_audio", 0], "audio_vae": ["sg1_386", 0],
                                 "identity_guidance_scale": 3.0, "start_percent": 0.0, "end_percent": 1.0}}
        wf["sg1_365"]["inputs"]["positive"] = ["refa", 1]
        wf["sg1_365"]["inputs"]["negative"] = ["refa", 2]
        wf["sg1_388"]["inputs"]["model"] = ["refa", 0]
        wf["sg1_391"]["inputs"]["model"] = ["sg1_384", 0]
    else:
        wf["sg1_388"]["inputs"]["model"] = ["sg1_384", 0]
        wf["sg1_391"]["inputs"]["model"] = ["sg1_384", 0]
        del wf["lora"]
    return wf


def graph(arm, seed):
    if arm.endswith("25"):
        return graph25(arm, seed)
    wf = {k: v for k, v in load_wf(WF).items() if isinstance(v, dict) and "class_type" in v}
    wf["sg1_319"]["inputs"]["value"] = PROMPTS[arm]
    if arm != "idlora":
        # no LoRA, no reference voice: the guider and the conditioning read around them
        wf["sg1_307"]["inputs"]["positive"] = ["sg1_306", 0]
        wf["sg1_307"]["inputs"]["negative"] = ["sg1_314", 0]
        wf["sg1_315"]["inputs"]["model"] = ["sg1_293", 0]
        for k in ("sg1_346", "sg1_349", "276"):
            del wf[k]
    wf["sg1_286"]["inputs"]["noise_seed"] = int(seed)
    wf["sg1_285"]["inputs"]["noise_seed"] = int(seed) + 1
    wf["341"]["inputs"]["filename_prefix"] = "claude-generated/idlora/%s_s%d" % (arm, seed)
    return wf


def queue_empty(budget=3600):
    import urllib.request
    t0 = time.time()
    while time.time() - t0 < budget:
        q = json.load(urllib.request.urlopen("http://%s/queue" % HOST, timeout=20))
        if not q["queue_running"] and not q["queue_pending"]:
            return True
        print("  ComfyUI is busy with someone else's job - waiting", flush=True)
        time.sleep(30)
    return False


def render(seeds, arms=ARMS):
    import post
    times = {}
    tp = os.path.join(OUT, "times.json")
    if os.path.exists(tp):
        times = json.load(open(tp))
    first = True
    for seed in seeds:
        for arm in arms:
            tag = "%s_s%d" % (arm, seed)
            dst = os.path.join(OUT, tag + ".mp4")
            if os.path.exists(dst):
                continue
            queue_empty()
            if first:
                have, why = post.make_room(need_gb=28.0, budget=240)
                print("GPU before the first LTX-2.3 submit: %.1f GB free (%s)" % (have, why), flush=True)
                first = False
            t0 = time.time()
            _, outs = run(HOST, graph(arm, seed), quiet=True)
            vids = [o for o in outs or [] if str(o).lower().endswith(".mp4")]
            if not vids:
                print("  %s: NO VIDEO (%s)" % (tag, outs), flush=True)
                continue
            shutil.copy(os.path.join(COMFY, "output", vids[0]), dst)
            times[tag] = round(time.time() - t0, 1)
            json.dump(times, open(tp, "w"), indent=1)
            print("  %-14s %5.0fs" % (tag, times[tag]), flush=True)
    return times


def strip(video, dst, n=6, h=144):
    dur = float(sh("ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                   video).stdout.strip() or 0)
    ims = []
    for i in range(n):
        p = dst + ".%d.png" % i
        sh("ffmpeg", "-y", "-v", "error", "-ss", "%.2f" % (dur * (i + 0.5) / n), "-i", video,
           "-frames:v", "1", "-vf", "scale=-2:%d" % h, p)
        if os.path.exists(p):
            ims.append(Image.open(p).convert("RGB"))
            os.remove(p)
    if ims:
        s = Image.new("RGB", (sum(i.width for i in ims), h))
        x = 0
        for im in ims:
            s.paste(im, (x, 0))
            x += im.width
        s.save(dst, quality=86)
    return dur


def voice_encoder():
    sys.path.insert(0, VE_SRC)
    from chatterbox.models.voice_encoder import VoiceEncoder
    from safetensors.torch import load_file
    ve = VoiceEncoder()
    ve.load_state_dict(load_file(VE_WEIGHTS))
    return ve.eval()


def spk(ve, path):
    return ve.embeds_from_wavs([pcm(path, 16000)], sample_rate=16000, as_spk=True)


def measure(meta, seeds, arms=ARMS):
    import post
    from shorts_asr import words
    tags = ["%s_s%d" % (a, s) for s in seeds for a in arms if os.path.exists(os.path.join(OUT, "%s_s%d.mp4" % (a, s)))]
    rows = {t: {"arm": t.rsplit("_s", 1)[0], "seed": int(t.rsplit("_s", 1)[1])} for t in tags}
    wavs = {}
    for t in tags:
        v = os.path.join(OUT, t + ".mp4")
        rows[t]["duration"] = strip(v, os.path.join(OUT, t + "_strip.jpg"))
        w = os.path.join(OUT, t + ".wav")
        sh("ffmpeg", "-y", "-v", "error", "-i", v, "-vn", "-ac", "1", "-ar", "16000", w)
        wavs[t] = w

    # words - Granite, loaded once, on whatever the card can spare
    post.make_room(need_gb=10.0, budget=180)
    from film_audio import _asr_local
    tx = _asr_local([wavs[t] for t in tags])
    want = set(words(LINE))
    for t in tags:
        got = set(words(tx.get(wavs[t], "")))
        rows[t]["transcript"] = tx.get(wavs[t], "")
        rows[t]["recall"] = round(len(want & got) / max(1, len(want)), 3)

    # voice - the speaker encoder, calibrated on the same scale
    ve = voice_encoder()
    ref = spk(ve, meta["reference"])
    calib = {name: round(float(ref @ spk(ve, p)), 3) for name, p in meta["calibration"].items()}
    for t in tags:
        rows[t]["voice_vs_maya"] = round(float(ref @ spk(ve, wavs[t])), 3)
        rows[t]["nearest_other"] = max(((round(float(spk(ve, p) @ spk(ve, wavs[t])), 3), n)
                                        for n, p in meta["calibration"].items() if not n.startswith("maya")))

    # face - identity.py's close-up path: first and last frame against the portrait, and the
    # first-to-last hold, all on the portrait's head box carried into the start frame. The start
    # image itself is scored the same way: it is the ceiling a take can reach at frame 0.
    box = meta.get("head_box")
    if not box:
        im = Image.open(PORTRAIT)
        box = head_in_crop(HB.head_box(PORTRAIT), im.size[1], meta["crop_top"], int(im.size[0] * 9 / 16))
        meta["head_box"] = box
    jobs = [{"id": "start image", "portrait": PORTRAIT, "still": meta["start_frame"], "box": box, "close": True}]
    jobs += [{"id": t, "portrait": PORTRAIT, "video": os.path.join(OUT, t + ".mp4"), "box": box, "close": True}
             for t in tags]
    jp = os.path.join(OUT, "identity_jobs.json")
    json.dump(jobs, open(jp, "w"))
    r = subprocess.run([PY, os.path.join(TOOLS, "identity.py"), jp], capture_output=True, text=True,
                       cwd=os.path.expanduser("~/ComfyUI"))
    face_ceiling = None
    for line in r.stdout.splitlines():
        try:
            d = json.loads(line)
        except Exception:
            continue
        if d.get("id") == "start image":
            face_ceiling = d.get("start")
            continue
        if d.get("id") in rows:
            rows[d["id"]].update({"face_first": d.get("start"), "face_last": d.get("end"),
                                  "face_hold": d.get("hold"), "face_verdict_last": d.get("verdict_end")})

    summary = {}
    for arm in arms:
        rs = [rows[t] for t in tags if rows[t]["arm"] == arm]
        if not rs:
            continue
        s = {}
        for k in ("recall", "voice_vs_maya", "face_first", "face_last", "face_hold"):
            vals = [x[k] for x in rs if isinstance(x.get(k), (int, float))]
            if vals:
                s[k] = {"mean": round(float(np.mean(vals)), 3), "min": round(min(vals), 3),
                        "max": round(max(vals), 3), "spread": round(max(vals) - min(vals), 3)}
        summary[arm] = s
    report = {"line": LINE, "prompts": PROMPTS, "pack": PACK, "voice": "female_04_maya",
              "voice_calibration_vs_reference": calib, "face_ceiling_start_image": face_ceiling,
              "head_box": box, "summary": summary, "takes": rows,
              "times": json.load(open(os.path.join(OUT, "times.json"))) if os.path.exists(os.path.join(OUT, "times.json")) else {}}
    json.dump(report, open(os.path.join(OUT, "results.json"), "w"), indent=1)

    print("\nvoice calibration against Maya's reference clip (Chatterbox speaker encoder):")
    for n, v in calib.items():
        print("   %-22s %.3f" % (n, v))
    print("face ceiling - the start image itself against the portrait: %s" % face_ceiling)
    num = lambda v: ("%.3f" % v) if isinstance(v, (int, float)) else "-"   # noqa: E731
    print("\n%-14s %6s %7s %7s %7s %7s   transcript" % ("take", "words", "voice", "face@0", "face@end", "hold"))
    for t in tags:
        x = rows[t]
        print("%-14s %5.0f%% %7s %7s %7s %7s   %s" % (
            t, 100 * x["recall"], num(x["voice_vs_maya"]), num(x.get("face_first")),
            num(x.get("face_last")), num(x.get("face_hold")), x["transcript"][:70]))
    print("\nper arm (mean, spread over seeds):")
    for arm, s in summary.items():
        print("   %-7s " % arm + "  ".join("%s %.3f±%.3f" % (k, v["mean"], v["spread"] / 2) for k, v in s.items()))
    print("ID_LORA DONE", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, nargs="+", default=[11, 202, 3003])
    ap.add_argument("--measure-only", action="store_true")
    ap.add_argument("--arms", nargs="+", default=list(ARMS), choices=list(ARMS + ARMS25),
                    help="tags25 / idlora25 run the same test on LTX-2.5 (workflow 70)")
    a = ap.parse_args()
    pj = os.path.join(OUT, "prepare.json")
    # the voice window and the start frame must not move between runs that share a report
    meta = json.load(open(pj)) if os.path.exists(pj) else prepare()
    print("start frame %s (crop top %d); Maya reference %.1f-%.1f s, %.0f%% voiced" % (
        meta["start_frame"], meta["crop_top"], meta["reference_window"][0],
        meta["reference_window"][1], 100 * meta["reference_voiced"]), flush=True)
    if not a.measure_only:
        render(a.seeds, a.arms)
    measure(meta, a.seeds, a.arms)


if __name__ == "__main__":
    main()
