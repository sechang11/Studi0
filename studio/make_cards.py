#!/usr/bin/env python3
"""Build a capability card per variable: what every option value actually LOOKS like.

    python3 studio/make_cards.py
    python3 studio/make_cards.py --only shot.size,light.direction

Modelled on the CAPABILITY.json cards in output/claude-generated. Same discipline:

    claim     what this variable does, stated plainly
    panels    one render per option value, same seed and same subject sentence, so the
              ONLY difference is the option
    look_at   what to notice, including which options do not work
    verdict   works / mixed / weak - honest, because a variable that reads as a no-op is
              worth knowing about before you spend a render on it

Options that fail are KEPT and labelled. A card showing only the ones that worked teaches
you nothing about where the edges are.
"""
import argparse, io, json, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
os.environ.setdefault("COMFY_ROOT", "Z:/ComfyUI")
os.environ.setdefault("COMFY_HOST", "192.168.1.46:8188")

OUT = f"{HERE}/samples/vars"
CARDS = f"{HERE}/cards"
W, H = 640, 360
Q = "masterpiece, best quality, very aesthetic, absurdres"
NEG = ("1girl, female, lowres, worst quality, bad anatomy, bad hands, watermark, text, "
       "multiple views, photorealistic, 3d, western comic, blurry")

# The subject sentence is IDENTICAL in every panel of a card. Only the option clause moves.
SUBJ = ("1boy, solo, male focus, dark red hair, undercut, yellow eyes, black soccer jersey, "
        "number 9, soccer stadium, floodlights, crowd")

CARDS_SPEC = {
 "shot.size": dict(
   claim="How much of the subject the frame contains. The single most load-bearing "
         "compositional choice - it decides whether a shot is about a person or about a place.",
   look_at="extreme_wide and wide reliably put the figure small in frame. medium_close and "
           "close are dependable. extreme_close is the weak one: the model often pulls back "
           "to a normal close-up rather than filling frame with one feature.",
   options=[("extreme_wide","extremely wide shot, tiny figure, vast environment, scenery"),
            ("wide","wide shot, full body, environment dominant"),
            ("medium_wide","medium wide shot, full body, knees up"),
            ("medium","medium shot, waist up"),
            ("medium_close","medium close-up, chest up"),
            ("close","close-up, head and shoulders"),
            ("extreme_close","extreme close-up, eyes only, macro detail")]),
 "shot.angle": dict(
   claim="Camera height relative to the subject. Low makes a figure powerful, high makes "
         "them small. This is how a frame states a power relationship without dialogue.",
   look_at="low_angle and high_angle are strong and reliable. dutch works. worms_eye and "
           "birds_eye are extreme and the model sometimes settles for merely low or high.",
   options=[("eye_level","eye level shot, neutral angle"),
            ("low_angle","from below, low angle, looking up at subject"),
            ("high_angle","from above, high angle, looking down at subject"),
            ("worms_eye","worms eye view, extreme low angle, ground level"),
            ("birds_eye","birds eye view, from directly above, overhead shot"),
            ("dutch","dutch angle, tilted horizon, canted frame")]),
 "light.direction": dict(
   claim="Where the key light sits. Direction does more for mood than colour does.",
   look_at="backlighting and rim are the most visually decisive. bottom (uplight) is the "
           "least reliable - the model tends to revert to conventional key lighting.",
   options=[("front","front lighting, flat even light on the face"),
            ("side","side lighting, half the face in shadow, chiaroscuro"),
            ("back","backlighting, subject against the light, rim lit"),
            ("top","top lighting, harsh overhead, shadows under the eyes"),
            ("bottom","uplight, lit from below, unsettling")]),
 "weather.type": dict(
   claim="Precipitation and atmosphere. Renders as prompt tags today - intensity and wind "
         "are not yet honoured, so this card shows the type only.",
   look_at="rain, snow and fog are strong. dust and heat haze are subtle and easily lost "
           "behind floodlights. clear is the control panel.",
   options=[("clear","clear sky, dry"),("overcast","overcast, grey sky, flat light"),
            ("rain","heavy rain, wet ground, reflections"),
            ("storm","storm, torrential rain, lightning"),
            ("snow","falling snow, cold"),("fog","thick fog, low visibility"),
            ("dust","dust in the air, dry wind, particles"),
            ("heat","heat haze, shimmering air")]),
 "char.emotion": dict(
   claim="The performance. Drives face, eyes, mouth and posture tags together, and on TTS "
         "engines that accept an emotion vector it will drive the voice too.",
   look_at="anger, joy, fear and exhaustion read instantly. cold and resolve are quiet by "
           "design and are easy to mistake for neutral - which is the point of them, but it "
           "means they need a held shot to land.",
   options=[("neutral","neutral expression, calm"),
            ("determined","determined expression, furrowed brow, sharp eyes"),
            ("angry","angry expression, glaring, gritted teeth"),
            ("exhausted","exhausted, half-closed eyes, panting, sweat"),
            ("grief","crying, grieving, tears, downcast eyes"),
            ("joy","smiling, happy, bright eyes"),
            ("fear","afraid, wide eyes, shrunken pupils, shocked"),
            ("cold","expressionless, blank, flat eyes, looking away"),
            ("resolve","calm resolve, quiet certainty, steady gaze")]),
 "time.of_day": dict(
   claim="Hour of the day. Note this fights the grade: prompting darkness barely works, so "
         "night here is reinforced by the look/grade, not by the tag alone.",
   look_at="dawn, dusk and night are distinct. morning and afternoon are nearly identical - "
           "if you need those to differ, use light.direction rather than this.",
   options=[("dawn","dawn, early morning light, mist"),
            ("morning","morning, bright clear daylight"),
            ("noon","noon, harsh overhead sun, short shadows"),
            ("afternoon","afternoon, warm angled light"),
            ("dusk","dusk, golden hour, long shadows"),
            ("night","night, dark, floodlights, artificial light")]),
 "shot.focus": dict(
   claim="Depth of field. Shallow focus separates a subject from the world; deep focus "
         "keeps the world present and pressing in.",
   look_at="shallow works well. deep focus is hard to force - the model likes a blurred "
           "background by default, so deep often looks like medium.",
   options=[("deep","deep focus, everything sharp, background in focus"),
            ("medium","medium depth of field"),
            ("shallow","shallow depth of field, bokeh, blurred background"),
            ("rack","selective focus, foreground sharp, background heavily blurred")]),
 "char.gaze": dict(
   claim="Where the character is looking. Gaze is how a frame directs the audience's "
         "attention and how two shots are stitched into one conversation.",
   look_at="at_viewer and away are reliable. off_screen is the useful one for dialogue - "
           "it implies a second person without needing to render them.",
   options=[("at_viewer","looking at viewer, direct eye contact"),
            ("away","looking away, eyes averted"),
            ("down","looking down, downcast eyes"),
            ("up","looking up, eyes raised"),
            ("off_screen","looking off screen to the side, at someone out of frame")]),
}


def sh(*a):
    r = subprocess.run(a, capture_output=True, text=True)
    if r.returncode:
        raise SystemExit(f"failed {' '.join(a[:4])}\n{(r.stderr or '')[-400:]}")


def gen(prompt, dest, seed):
    from comfy import run
    from epic import ensure_local, COMFY, HOST
    if os.path.exists(dest):
        return
    tag = os.path.splitext(os.path.basename(dest))[0]
    wf = {"1": {"class_type": "CheckpointLoaderSimple",
                "inputs": {"ckpt_name": "animagine-xl-4.0.safetensors"}},
          "2": {"class_type": "EmptyLatentImage",
                "inputs": {"width": 1344, "height": 768, "batch_size": 1}},
          "3": {"class_type": "CLIPTextEncode",
                "inputs": {"clip": ["1", 1], "text": f"{prompt}, {Q}"}},
          "4": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["1", 1], "text": NEG}},
          "5": {"class_type": "KSampler",
                "inputs": {"model": ["1", 0], "positive": ["3", 0], "negative": ["4", 0],
                           "latent_image": ["2", 0], "seed": seed, "steps": 28, "cfg": 5.0,
                           "sampler_name": "euler_ancestral", "scheduler": "normal",
                           "denoise": 1.0}},
          "6": {"class_type": "VAEDecode", "inputs": {"samples": ["5", 0], "vae": ["1", 2]}},
          "7": {"class_type": "SaveImage",
                "inputs": {"images": ["6", 0],
                           "filename_prefix": f"claude-generated/studio_cards/{tag}"}}}
    run(HOST, wf, quiet=True)
    tmp = f"{COMFY}/output/claude-generated/studio_cards/{tag}_00001_.png"
    ensure_local(f"claude-generated/studio_cards/{tag}_00001_.png", tmp, required=True)
    sh("ffmpeg", "-y", "-v", "error", "-i", tmp, "-vf", f"scale={W}:{H}", dest)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="")
    a = ap.parse_args()
    want = set(x.strip() for x in a.only.split(",") if x.strip())
    os.makedirs(CARDS, exist_ok=True)

    for var, spec in CARDS_SPEC.items():
        if want and var not in want:
            continue
        slug = var.replace(".", "_")
        d = f"{OUT}/{slug}"
        os.makedirs(d, exist_ok=True)
        print(f"  {var}  ({len(spec['options'])} options)", flush=True)
        panels = []
        for i, (val, clause) in enumerate(spec["options"]):
            dest = f"{d}/{val}.png"
            # same seed + same subject sentence in every panel: only the option moves
            gen(f"{SUBJ}, {clause}", dest, seed=9001)
            panels.append({"value": val, "clause": clause,
                           "sample": f"/samples/vars/{slug}/{val}.png"})
        card = {"variable": var, "claim": spec["claim"], "look_at": spec["look_at"],
                "method": "identical subject sentence and seed in every panel; only the "
                          "option clause changes",
                "model": "animagine-xl-4.0, 28 steps, cfg 5.0, euler_ancestral",
                "panels": panels}
        io.open(f"{CARDS}/{slug}.json", "w", encoding="utf-8").write(
            json.dumps(card, indent=2, ensure_ascii=False) + "\n")

    n = len([f for f in os.listdir(CARDS) if f.endswith(".json")])
    imgs = sum(len(os.listdir(f"{OUT}/{x}")) for x in os.listdir(OUT)) if os.path.isdir(OUT) else 0
    print(f"\n{n} cards, {imgs} option renders")


if __name__ == "__main__":
    main()
