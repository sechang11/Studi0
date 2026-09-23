#!/usr/bin/env python3
"""Find the format for warmth, the way the beauty tier's format was found.

The beauty tier has exactly one personality in it: composed, chin lifted, straight into the
lens. That is aloof by construction, and aloof is the opposite of the brief - warm, happy,
lovable, a person you can read at a glance.

Two things could be responsible and they need separating, so this crosses them:

    LIGHT       hard-ish soft key (what the beauty tier uses)  vs  warm wrapping window light
                vs  late golden hour
    EXPRESSION  composed (the control)  vs  a genuine Duchenne smile that reaches the eyes

Six renders, three heritages including two the brief named specifically. If the warmth comes
from the expression, the beauty tier only needs a new expression clause; if it comes from the
light, the whole format changes again.

    python3 bake_warm.py
"""
import os
import re
import subprocess
import sys
import time

ROOT = os.path.expanduser("~/shared/comfy-studio")
WF = "workflows/26_flux2_t2i.json"

BEAUTY = ("exceptionally beautiful, with high cheekbones, a clean jawline, large clear eyes, "
          "full lips and flawless luminous skin")

REAL = ("Visible fine skin texture and pores at close range, individual eyelashes, fine baby "
        "hairs at the hairline, a natural catchlight in each eye, one subtle asymmetry in the "
        "face, shot on an 85mm lens at f2, faint film grain. Not retouched, no skin smoothing, "
        "no beauty filter, not a 3d render, not an illustration.")

LIGHT = {
    "key": ("Photographed indoors against a warm neutral backdrop with a single large soft "
            "light source just off to one side, soft shadow across the far cheek."),
    "window": ("Photographed at home beside a big window on a bright day, warm daylight "
               "wrapping softly all the way around her face with almost no shadow, a lived-in "
               "room soft and out of focus behind her."),
    "golden": ("Photographed outdoors in the last hour of sunlight, warm low sun behind her "
               "lighting her hair, soft golden bounce filling her face, a park blurred behind."),
}
EXPR = {
    "composed": ("Chin slightly lifted, looking straight into the lens with a composed, "
                 "self-possessed expression."),
    "smile": ("Laughing at something just off camera and turning back towards the lens, a wide "
              "genuine smile that creases the corners of her eyes, head tilted a little, "
              "shoulders relaxed, one hand pushing her hair back."),
}
WHO = {
    "albino": ("a 25 year old woman with albinism, very pale skin, long white-blonde hair and "
               "pale blue eyes"),
    "easian": ("a 25 year old Korean woman with warm fair skin, long glossy black hair and dark "
               "almond eyes"),
    "brazil": ("a 25 year old Brazilian woman with warm golden-brown skin, long wavy dark hair "
               "and hazel eyes"),
}
# the six that matter: the control, then light and expression varied one at a time
COMBOS = [("albino", "key", "composed"), ("albino", "window", "smile"),
          ("easian", "key", "smile"), ("easian", "window", "smile"),
          ("brazil", "golden", "smile"), ("brazil", "window", "smile")]


def main():
    for wk, lk, ek in COMBOS:
        prompt = ("Photo of %s, %s. %s %s Wearing a simple soft knit top. %s"
                  % (WHO[wk], BEAUTY, LIGHT[lk], EXPR[ek], REAL))
        cmd = [sys.executable, os.path.join(ROOT, "scripts", "comfy.py"), "run",
               os.path.join(ROOT, WF),
               "-s", "6.inputs.text=%s" % prompt,
               "-s", "9.inputs.width=1024", "-s", "9.inputs.height=1280",
               "-s", "12.inputs.width=1024", "-s", "12.inputs.height=1280",
               "-s", "7.inputs.guidance=3.2",
               "-s", "11.inputs.noise_seed=4242",
               "-s", "15.inputs.filename_prefix=claude-generated/warm/%s_%s_%s" % (wk, lk, ek)]
        t0 = time.time()
        r = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT)
        m = re.search(r"-> (\S+\.png)", r.stdout or "")
        print("  %-7s %-7s %-9s %5.1fs %s" % (wk, lk, ek, time.time() - t0,
                                              "ok" if m else "FAILED"))


if __name__ == "__main__":
    main()
