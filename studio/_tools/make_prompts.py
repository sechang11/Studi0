#!/usr/bin/env python3
"""Write studio/prompts/ - a demo prompt library, each entry with a rendered sample.

WHY A LIBRARY RATHER THAN A LIST OF NICE PROMPTS

The two model families on this box want OPPOSITE prompt formats, and the single most
expensive mistake available is using one dialect on the other. Feeding Animagine the
cinematic prose Qwen wants returns abstract coloured shapes. So every entry here
declares its DIALECT and the workflow it belongs to, and the sample proves it.

    python3 studio/_tools/make_prompts.py           # write + render
    python3 studio/_tools/make_prompts.py --dry     # write only, no GPU
"""
import json, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
STUDIO = os.path.dirname(HERE)
ROOT = os.path.dirname(STUDIO)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
OUT = os.path.join(STUDIO, "prompts")
SAMP = os.path.join(STUDIO, "samples", "prompts")

ANIME_Q = "masterpiece, best quality, very aesthetic, absurdres"
ANIME_NEG = ("lowres, worst quality, bad anatomy, bad hands, watermark, text, "
             "multiple views, motion blur, blurry")

DEMOS = [
    {
        "id": "anime_establish",
        "title": "Anime establishing wide",
        "dialect": "danbooru",
        "model": "animagine-xl-4.0",
        "workflow": "22_anime_kf_ipadapter / 13_qwen_t2i_styled",
        "prompt": "no humans, empty soccer stadium at night, floodlights, empty stands, "
                  "confetti on wet grass, wide shot, scenery, cinematic lighting, "
                  + ANIME_Q,
        "why": "Danbooru grammar: comma-separated tags, subject first, camera word "
               "('wide shot') as a tag rather than a sentence. `no humans` is a real "
               "danbooru tag and the reliable way to get an empty frame - it is NOT "
               "negation, which SDXL cannot do in a positive prompt.",
        "render": "anime",
    },
    {
        "id": "anime_macro_insert",
        "title": "Macro insert - the cheapest shot you can make",
        "dialect": "danbooru",
        "model": "animagine-xl-4.0",
        "workflow": "13_qwen_t2i_styled",
        "prompt": "no humans, extreme close-up, soccer ball on wet grass, water droplets, "
                  "shallow depth of field, object focus, floodlight rim light, " + ANIME_Q,
        "why": "No character, no face, no consistency risk, near-perfect prompt adherence, "
               "about 4.5s of GPU. One insert per act minimum, and make it an object - "
               "this is also how you fake coverage, since no model here has a persistent "
               "3D space to cut around.",
        "render": "anime",
    },
    {
        "id": "anime_reaction_close",
        "title": "Reaction close-up",
        "dialect": "danbooru",
        "model": "animagine-xl-4.0",
        "workflow": "22_anime_kf_ipadapter",
        "prompt": "1boy, solo, male focus, dark red hair, undercut, yellow eyes, "
                  "black soccer jersey, number 9, close-up, wide-eyed, parted lips, "
                  "sweat, night stadium background, bokeh, " + ANIME_Q,
        "why": "Character tags FIRST, then the emotion, then framing, then background. "
               "Two specified identity items beat five. Note the emotion is carried by "
               "physical tags (wide-eyed, parted lips, sweat) not by an abstract word - "
               "'shocked' alone is routinely ignored.",
        "render": "anime",
    },
    {
        "id": "anime_extreme_close",
        "title": "Extreme close-up - the strongest panel in the whole card set",
        "dialect": "danbooru",
        "model": "animagine-xl-4.0",
        "workflow": "13_qwen_t2i_styled",
        "prompt": "extreme close-up, single eye, yellow eye, detailed iris, reflection of "
                  "floodlights in the eye, eyelashes, skin texture, " + ANIME_Q,
        "why": "Verified against pixels: extreme_close was PREDICTED to fail and is the "
               "best panel in the set, while extreme_wide was predicted to work and loses "
               "the figure from frame entirely. When you want intensity, go closer than "
               "feels sensible.",
        "render": "anime",
    },
    {
        "id": "anime_empty_frame",
        "title": "Empty frame / pillow shot",
        "dialect": "danbooru",
        "model": "animagine-xl-4.0",
        "workflow": "13_qwen_t2i_styled",
        "prompt": "no humans, empty locker room, wooden benches, hanging jerseys, "
                  "fluorescent light, scenery only, still, " + ANIME_Q,
        "why": "Ozu's cutaway with no people in it. Gives an edit somewhere to breathe, "
               "and costs nothing in consistency. `no humans` again - and note it must "
               "NOT be blanked by any negation rule, because it is a positive tag.",
        "render": "anime",
    },
    {
        "id": "anime_wear_damage",
        "title": "Damage continuity (wear level 4)",
        "dialect": "danbooru",
        "model": "animagine-xl-4.0",
        "workflow": "22_anime_kf_ipadapter",
        "prompt": "1boy, solo, male focus, dark red hair, undercut, yellow eyes, "
                  "torn black soccer jersey, dirt and grass stains, bloodied lip, "
                  "cut on cheek, sweat, heavy breathing, exhausted, dishevelled hair, "
                  "medium close-up, " + ANIME_Q,
        "why": "The WEAR vocabulary spelled out as physical damage rather than the word "
               "'exhausted'. Verified 2026-08-03: a scene set wear:4 through the tag list "
               "alone still rendered a clean uniform, so the damage has to be named as "
               "objects - torn, stains, blood, cut - not as a state.",
        "render": "anime",
    },
    {
        "id": "ltx_motion",
        "title": "LTX image-to-video motion clause",
        "dialect": "ltx-motion",
        "model": "LTX-2.3 22B",
        "workflow": "12_ltx23_i2v_audio",
        "prompt": "A slow forward dolly shot. The player lifts his head and looks up. "
                  "Confetti drifts down through the floodlight beams, his hair moves "
                  "slightly in the wind. Distant crowd murmur and a low wind.",
        "why": "ORDER IS LOAD-BEARING: camera clause first and ONE move only, then subject "
               "motion, then ambient motion, then a soundscape clause (LTX generates audio "
               "natively). Nine motion shapes reliably fail - sequential beats ('X, then "
               "Y'), two actors doing separate things, motion contradicting the keyframe, "
               "subjects entering or leaving frame, dematerialisation, prop hand-offs, "
               "screen content changes, time-lapse and split-screen. Ambient motion is "
               "safe three or four at a time.",
        "render": None,
    },
    {
        "id": "music_cue",
        "title": "ACE-Step score cue",
        "dialect": "music-tags",
        "model": "ACE-Step 1.5 Turbo",
        "workflow": "06_acestep_music",
        "prompt": "sparse melancholy piano, single sustained cello, empty stadium, defeat, "
                  "restrained, instrumental",
        "why": "Tags plus bpm plus key, and cfg 1.0 - which is CORRECT for a distilled "
               "turbo model, not a bug. Always say 'instrumental' unless you want it to "
               "invent lyrics. ACE-Step has no hit-point conditioning and cannot spot to "
               "picture, so generate longer than the scene and trim in the mix.",
        "render": None,
    },
    {
        "id": "sfx_hit",
        "title": "Stable Audio one-shot",
        "dialect": "sfx",
        "model": "Stable Audio 3 Medium",
        "workflow": "10_stableaudio_sfx",
        "prompt": "a single sharp leather football being struck hard, close, dry, no music",
        "why": "ONE sound per bed. 100 steps, cfg 7, dpmpp_3m_sde - unlike ACE-Step this "
               "model is NOT distilled, so cfg 1.0 is wrong here and clips. Normalise every "
               "result: measured spread across generations is ~15 dB, with some files "
               "peaking at exactly 0.0 dBFS.",
        "render": None,
    },
]


def sh(*a):
    return subprocess.run(a, capture_output=True, text=True)


def render_anime(prompt, tag, dest):
    from comfy import run
    from epic import ensure_local, COMFY, HOST
    wf = {"1": {"class_type": "CheckpointLoaderSimple",
                "inputs": {"ckpt_name": "animagine-xl-4.0.safetensors"}},
          "2": {"class_type": "EmptyLatentImage",
                "inputs": {"width": 1344, "height": 768, "batch_size": 1}},
          "3": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["1", 1], "text": prompt}},
          "4": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["1", 1], "text": ANIME_NEG}},
          "5": {"class_type": "KSampler",
                "inputs": {"model": ["1", 0], "positive": ["3", 0], "negative": ["4", 0],
                           "latent_image": ["2", 0], "seed": 4242, "steps": 28, "cfg": 5.0,
                           "sampler_name": "euler_ancestral", "scheduler": "normal",
                           "denoise": 1.0}},
          "6": {"class_type": "VAEDecode", "inputs": {"samples": ["5", 0], "vae": ["1", 2]}},
          "7": {"class_type": "SaveImage",
                "inputs": {"images": ["6", 0],
                           "filename_prefix": "claude-generated/studio_prompts/%s" % tag}}}
    run(HOST, wf, quiet=True)
    rel = "claude-generated/studio_prompts/%s_00001_.png" % tag
    tmp = os.path.join(COMFY, "output", rel)
    ensure_local(rel, tmp, required=True)
    sh("ffmpeg", "-y", "-v", "error", "-i", tmp, "-vf", "scale=640:360", "-q:v", "80", dest)


def main():
    dry = "--dry" in sys.argv
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(SAMP, exist_ok=True)
    for d in DEMOS:
        doc = dict(d)
        doc.pop("render", None)
        doc["status"] = "ready"
        if d.get("render") == "anime":
            dest = os.path.join(SAMP, d["id"] + ".webp")
            doc["sample"] = "/samples/prompts/%s.webp" % d["id"]
            if not dry and not os.path.exists(dest):
                print("  rendering %s ..." % d["id"], flush=True)
                try:
                    render_anime(d["prompt"], d["id"], dest)
                except Exception as e:
                    print("    FAILED: %s" % str(e)[:160])
                    doc.pop("sample", None)
        with open(os.path.join(OUT, d["id"] + ".json"), "w", encoding="utf-8") as f:
            json.dump(doc, f, indent=2, ensure_ascii=False)
            f.write("\n")
        print("  wrote %s" % d["id"])
    print("\n%d demo prompts in %s" % (len(DEMOS), OUT))


if __name__ == "__main__":
    main()
