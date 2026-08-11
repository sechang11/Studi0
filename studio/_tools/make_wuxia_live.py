#!/usr/bin/env python3
"""A live-action wuxia style card, and two photoreal leads to go with it.

    python3 studio/_tools/make_wuxia_live.py

WHY THIS IS A SEPARATE STYLE CARD AND A SEPARATE CAST, rather than the same one rendered
differently. Two measured facts force it:

  THE ENGINE IS A PROPERTY OF THE STYLE. The existing `wuxia` card routes to animagine,
  which is an illustration model. Photoreal belongs on Qwen, which this project measured
  cannot be steered off photography by prompt at any cfg - that stubbornness is a liability
  when you want a drawing and exactly what you want here.

  A CHARACTER LORA IS A DELTA ON SPECIFIC WEIGHTS. Liwen and Shen were trained on
  animagine; those files attach to nothing on Qwen. They are passed through, quietly never
  read. So a photoreal lead cannot reuse them and needs its own identity, held by a
  reference sheet and prose rather than by trained weights.

THE FACE PROBLEM, AND THE FIX THAT WAS MEASURED. An earlier photoreal attempt here came
back looking like cosplay - a costume worn by a stranger under flat light. The cause was
literal transcription: listing garments and hoping. What fixed it was writing in
MATERIAL, LIGHT, LENS and POSE instead. So the prose below names silk weave and skin
texture, a light direction, a focal length and an aperture, and what the person is doing
with their face - not a shopping list of clothes.

Both characters are invented. No real person is named, referenced, or used as a likeness.
"""
import json, os, sys, time

TOOLS = os.path.dirname(os.path.abspath(__file__))
STUDIO = os.path.dirname(TOOLS)
ROOT = os.path.dirname(STUDIO)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
os.environ.setdefault("COMFY_HOST", "127.0.0.1:8188")
from comfy import run, set_path                       # noqa: E402
from epic import load_wf, ensure_local, HOST, COMFY   # noqa: E402

STYLE_ID = "wuxia_live"
STYLE_PROSE = (
    "a still frame from a live-action wuxia film, shot on 35mm anamorphic at f/2.0, "
    "natural skin with visible pore texture and fine stray hair lit by a single soft "
    "window source from camera left falling off into deep shadow, silk with real weave "
    "and weight catching the light along its folds, atmospheric haze between the subject "
    "and a distant misty ridge, muted jade and ink palette with one warm accent, "
    "shallow focal plane, unforced expression, no makeup gloss")

NEG = ("illustration, drawing, painting, anime, cartoon, cgi, 3d render, plastic skin, "
       "airbrushed, doll, cosplay, costume shop, studio backdrop, flat frontal flash, "
       "lowres, deformed hands, extra fingers, watermark, text")

CAST = {
    "YANSHU": {
        "name": "Yan Shuqing",
        "who": ("a woman in her mid twenties, east asian, oval face with a narrow jaw and "
                "high cheekbones, dark brown eyes, straight black hair pulled back and "
                "pinned with a plain jade pin, a few strands loose at the temple, unpainted "
                "mouth, a small mole below the left eye"),
        "wear": ("layered pale grey and jade silk robes with a dark sash, the collar folded "
                 "close at the throat, sleeves weighted and creased from wear"),
        "doing": "half turned away, looking back over her shoulder without smiling",
    },
    "MUQING": {
        "name": "Mu Qingyun",
        "who": ("a man in his late twenties, east asian, long straight black hair tied high "
                "and falling past the shoulder, deep-set dark eyes, a straight nose and a "
                "hard jaw, faint stubble, a thin old scar across the right eyebrow"),
        "wear": ("dark indigo travelling robes over a black underlayer, a worn leather belt, "
                 "forearms wrapped in linen"),
        "doing": "standing still, weight on the back foot, eyes level with the camera",
    },
    "LINRUO": {
        "name": "Lin Ruoxi",
        "who": ("a woman in her early twenties, east asian, round softer face with a small "
                "chin, wide dark eyes, black hair in a loose braid over one shoulder with "
                "a red cord worked through it, clear unpainted skin, a faint scar on the "
                "bridge of the nose"),
        "wear": ("faded vermilion and cream robes, a short riding jacket over them, "
                 "a wide cloth belt, sleeves pushed to the elbow"),
        "doing": "mid-stride, glancing sideways at something out of frame, mouth set",
    },
    "HERUI": {
        "name": "He Ruilan",
        "who": ("a man in his early thirties, east asian, lean narrow face, hooded tired "
                "eyes, black hair cut shorter and pushed back with grey at the temple, "
                "a healed cut along the jaw, weathered skin"),
        "wear": ("charcoal grey robes worn thin at the elbows, a plain rope belt, "
                 "a travelling cloak pushed back off the shoulders"),
        "doing": "seated, forearms on his knees, looking down and slightly away",
    },
}


def style_card():
    p = os.path.join(STUDIO, "styles", "%s.json" % STYLE_ID)
    card = {
        "id": STYLE_ID, "name": "Wuxia (live action)",
        "engine": "qwen", "status": "ready", "compose": "safe", "family": "photographic",
        "prose": STYLE_PROSE,
        "negative_add": NEG,
        "means": ("The live-action counterpart to the `wuxia` card. That one is an "
                  "illustration style on animagine; this is a photographic one on Qwen. "
                  "They are different cards because the engine is a property of the style, "
                  "not a switch."),
        "note": ("Written in MATERIAL, LIGHT, LENS and POSE rather than as a list of "
                 "garments. An earlier photoreal attempt on this box came back as cosplay - "
                 "a costume worn by a stranger under flat light - and literal transcription "
                 "was the cause. Silk weave, a named light direction, f/2.0 and what the "
                 "face is doing are what stop it."),
        "verdict": "unverified - rendered and looked at below, but not swept.",
        "created": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    with open(p, "w", encoding="utf-8") as f:
        json.dump(card, f, indent=1, ensure_ascii=False)
        f.write("\n")
    return p


def sheet(cid, c, seed):
    prompt = ("%s, wearing %s, %s. %s" % (c["who"], c["wear"], c["doing"], STYLE_PROSE))
    wf = load_wf("13_qwen_t2i_styled.json")
    set_path(wf, "10.inputs.text", prompt)
    set_path(wf, "11.inputs.text", NEG)
    set_path(wf, "12.inputs.width", 1024)
    set_path(wf, "12.inputs.height", 1344)
    set_path(wf, "13.inputs.seed", seed)
    set_path(wf, "7.inputs.strength_model", 0.0)     # words only; no style LoRA
    set_path(wf, "15.inputs.filename_prefix", "claude-generated/wuxia-live/%s" % cid.lower())
    _, outs = run(HOST, wf, quiet=True)
    if not outs:
        return None, prompt
    dst = os.path.join(COMFY, "input", "sheet_%s.png" % cid.lower())
    return ensure_local(outs[0], dst, required=False), prompt


def main():
    print("  style card: %s" % style_card())
    for i, (cid, c) in enumerate(CAST.items()):
        got, prompt = sheet(cid, c, 5150 + i * 47)
        card = {
            "id": cid, "name": c["name"], "status": "ready",
            "desc": c["who"][:150],
            "prose": "%s, wearing %s" % (c["who"], c["wear"]),
            # No tags: this character lives on the PROSE engine. Danbooru tags would be
            # ignored there and would only mislead whoever reads the card next.
            "tags": "", "base_tags": "",
            "wear_tags": [
                c["wear"] + ", clean, freshly pressed",
                c["wear"] + ", road dust in the creases",
                c["wear"] + ", a torn sleeve, mud at the hem",
                c["wear"] + ", cut open at the shoulder, linen used as a bandage",
                c["wear"] + ", in rags, dried blood at the temple",
            ],
            "sheet": ("sheet_%s.png" % cid.lower()) if got else None,
            "engine": "qwen",
            "provenance": "invented",
            "provenance_note": (
                "Invented for the live-action wuxia set. No real person is referenced or "
                "used as a likeness source. Identity is held by the reference sheet and "
                "this prose - NOT by a trained LoRA, because a character LoRA is a delta "
                "on animagine's weights and attaches to nothing on Qwen."),
            "note": ("Photoreal lead for the %s style. Written in material, light, lens "
                     "and pose vocabulary, which is what stopped an earlier photoreal "
                     "attempt reading as cosplay." % STYLE_ID),
            "created": time.strftime("%Y-%m-%dT%H:%M:%S"),
        }
        with open(os.path.join(STUDIO, "characters", "%s.json" % cid), "w",
                  encoding="utf-8") as f:
            json.dump(card, f, indent=1, ensure_ascii=False)
            f.write("\n")
        print("  %-7s %s" % (cid, got or "SHEET FAILED"))


if __name__ == "__main__":
    main()
