#!/usr/bin/env python3
"""studio/_tools/faces.py - a browsable library of invented faces, and a way to cast one.

WHY THIS AND NOT DOWNLOADED LORAS. The public face-LoRA supply is overwhelmingly real,
identifiable people; this studio already blocked four voice packs for exactly that reason. So
the library is grown rather than downloaded. Since Flux 2 reference conditioning carries an
identity from a single picture (workflows/68, measured 0.69 mean over thirty posts), a face in
this library is a PORTRAIT, not a set of weights - which also means a new one costs about
sixteen seconds instead of a quarter hour of training that survives the adoption gate 2 times
in 8.

Every face is assembled from typed attributes rather than written by hand, for three reasons:
the spread is even instead of clustering on whatever I happened to think of, the picker can
filter on the same fields that made the face, and nobody real is ever referenced.

    python3 studio/_tools/faces.py --plan 100        # show the spread without rendering
    python3 studio/_tools/faces.py --make 100        # render them
    python3 studio/_tools/faces.py --index           # rebuild faces.json
    python3 studio/_tools/faces.py --cast f0042 --name "MAYA" --slug maya
"""
import argparse
import json
import os
import random
import re
import shutil
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
COMFY = os.path.expanduser("~/ComfyUI")
COMFY_IN = os.path.join(COMFY, "input")
COMFY_OUT = os.path.join(COMFY, "output")
OUT = os.path.join(ROOT, "studio", "foundry", "faces")
WF = "workflows/26_flux2_t2i.json"
W, H = 1024, 1280

REAL = ("Shot on a phone in flat window light, unretouched: visible skin pores and texture, "
        "natural skin tone variation, a few stray hairs, faint sensor noise. Not a studio "
        "portrait, no retouching, no beauty filter.")
FRAME = ("Head and shoulders, square to the camera, indoors beside a large window on an "
         "overcast day, neutral expression, wearing a plain grey t-shirt, plain pale wall "
         "behind her.")
STRIKING = ("She has the bone structure of a working model but is photographed plainly and her "
            "skin is real.")

# ── the beauty tier ────────────────────────────────────────────────────────────────
# The casting tier above is deliberately unflattering: flat overcast light, neutral face,
# square to camera, grey t-shirt. That is what a casting card IS, and it is why those hundred
# read as ordinary people. This tier is the opposite brief and the difference lives in the
# LIGHT and the FRAMING, not in adjectives - a bake-off of three formats on two very different
# colourings settled it (soft single key beat golden hour and bright clean light).
#
# The danger on this side is plastic. So "flawless" is spelled out as clear-and-luminous WITH
# pores, lashes, baby hairs, a catchlight and one asymmetry, and the anti-render clause stays.
BEAUTY_REAL = ("Visible fine skin texture and pores at close range, individual eyelashes, fine "
               "baby hairs at the hairline, a natural catchlight in each eye, one subtle "
               "asymmetry in the face, shot on an 85mm lens at f2 on a full-frame camera, "
               "faint film grain. Not retouched, no skin smoothing, no beauty filter, not a 3d "
               "render, not an illustration.")
# No hair clause here on purpose. The first version said "hair with shape and movement", which
# fought the length axis and turned a shaved head into a bob - the same two-disagreeing-signals
# failure as the crowd clause. The hair is already fully described in the subject line.
BEAUTY_FRAME = ("Photographed indoors against a warm neutral backdrop with a single large soft "
                "light source just off to one side, soft shadow falling across the far cheek, "
                "groomed brows, bare-skin makeup with a defined lip, wearing a simple fine-knit "
                "top, chin slightly lifted, looking straight into the lens with a composed, "
                "self-possessed expression.")
BEAUTY = ("exceptionally beautiful, with the facial proportions people call perfect: high "
          "sculpted cheekbones, a clean defined jawline, a small straight nose, large clear "
          "wide-set eyes, full lips, a long neck, and flawless luminous skin")

# On this tier the extra trait must ADD to the beauty rather than characterise away from it,
# so the character-actor traits (gap teeth, hooded eyes, a high forehead) are not offered.
BEAUTY_FEATURE = [
    ("green-eyes", "unusually vivid green eyes"),
    ("grey-eyes", "pale grey eyes"),
    ("amber-eyes", "light amber eyes"),
    ("heterochromia", "complete heterochromia, one eye lighter than the other"),
    ("freckles", "a fine scatter of freckles across her nose"),
    ("beauty-mark", "a small beauty mark above her lip"),
    ("long-lashes", "exceptionally long dark lashes"),
    ("strong-brows", "strong shapely dark brows"),
    ("cupids-bow", "a sharply defined cupid's bow"),
    ("cheekbones", "extraordinarily high sculpted cheekbones"),
    ("long-neck", "a long elegant neck"),
    ("dimples", "soft dimples when she smiles"),
    ("widows-peak", "a defined widow's peak"),
    ("almond-eyes", "long almond eyes with a slight upward tilt"),
]

TIERS = {
    "casting": {"prefix": "f", "frame": FRAME, "real": REAL, "note": STRIKING,
                "features": None, "subject": None},
    "beauty": {"prefix": "g", "frame": BEAUTY_FRAME, "real": BEAUTY_REAL, "note": "",
               "features": BEAUTY_FEATURE, "subject": BEAUTY},
    # the warm tier builds its prompt from a roster, not from the shared axes; see plan_warm
    "warm": {"prefix": "w", "frame": "", "real": "", "note": "",
             "features": None, "subject": None},
    # likewise roster-driven; see plan_starlet
    "starlet": {"prefix": "s", "frame": "", "real": "", "note": "",
                "features": None, "subject": None},
}

# ── the warm tier ──────────────────────────────────────────────────────────────────
# The beauty tier has exactly one personality in it - composed, chin lifted, straight down the
# lens - which is aloof by construction. The brief here is the opposite: warm, happy, someone
# you can read at a glance. A bake-off crossing light against expression settled which half
# matters: the EXPRESSION carries almost all of it (a composed face under warm window light is
# still cold), but the BACKGROUND decides whether she reads as a person or a product - a
# seamless backdrop says campaign, a lived-in room says someone you know.
#
# So this tier is a curated roster rather than a random sample, because a line-up needs
# guaranteed coverage, and personality gets its own axis instead of one repeated gesture.

WARM_SUBJECT = ("genuinely beautiful, the kind of face people notice and remember, with warm "
                "open features, clear bright eyes and healthy luminous skin")

# "looking at someone out of frame" put an actual second person in the shot on the first run,
# so the frame is now stated to hold her alone - the same lesson as every other time two
# clauses were left to argue: say it once, explicitly, in the place it belongs.
WARM_REAL = ("She is alone in the frame and no one else is visible. Visible fine skin texture "
             "and pores, individual eyelashes, fine baby hairs at the hairline, a natural "
             "catchlight in each eye, one subtle asymmetry, shot on an 85mm lens at f2, faint "
             "film grain. Not retouched, no skin smoothing, no beauty filter, not a 3d render, "
             "not an illustration.")

# Expression, gesture and gaze together - this is what "personality you can infer from a
# picture" actually decomposes into.
PERSONA = [
    ("delighted", "laughing openly with her head tipped back a little, eyes creased almost "
                  "shut, entirely unguarded"),
    ("warm", "smiling a wide easy smile straight into the lens, shoulders relaxed, completely "
             "at ease"),
    ("shy", "chin dipped and eyes coming up to the lens, a small smile she is trying to hold "
            "back, one hand at her collar"),
    # NOT "looking at someone out of frame": the engine drew the someone, twice, even with
    # "she is alone in the frame" stated. Name the head turn, never the companion.
    ("playful", "caught mid-laugh with her head turned to look away to one side, eyebrows up, "
                "one shoulder lifted"),
    ("tender", "a soft closed-lip smile, head tilted gently, looking at the camera with real "
               "affection"),
    ("mischievous", "one eyebrow slightly raised and a half smile, as though she knows exactly "
                    "what you are thinking"),
    ("serene", "eyes half closed towards the light with a calm private smile, perfectly still"),
    ("radiant", "beaming with her whole face, leaning very slightly towards the camera, hands "
                "loose"),
    ("dreamy", "chin resting on her hand looking out of the window with a small private smile, "
               "somewhere else entirely"),
    ("amused", "trying not to laugh and failing, lips pressed together, eyes bright and fixed "
               "on the lens"),
]

SETTING = [
    ("window", "at home beside a big window on a bright day, warm daylight wrapping all the way "
               "round her face, a lived-in room soft and out of focus behind her"),
    ("kitchen", "in a sunlit kitchen leaning against the counter, warm light bouncing off pale "
                "tiles, mugs and plants out of focus behind her"),
    ("morning", "sitting on the end of an unmade bed in soft early morning light, pale linen "
                "and a bedroom window behind her"),
    ("garden", "in a green garden in the last hour of sunlight, warm sun behind her lighting "
               "her hair, leaves and flowers blurred behind"),
    ("balcony", "on a small balcony crowded with plants in late afternoon sun, warm light and "
                "soft shadows across her"),
    ("cafe", "at a corner table in a warm little cafe, low lamps and a window behind her, the "
             "room golden and out of focus"),
]

# A deliberate line-up. Every entry names its own colouring, so nothing is left to a dice roll,
# and the ones asked for by name are all here: albino with blue eyes, blonde with green eyes,
# several East and Southeast Asian, Brazilian. Ages are explicit and all adult.
WARM_ROSTER = [
    ("nordic", "a 24 year old Swedish woman", "long straight golden-blonde hair and bright blue eyes, fair skin"),
    ("albino-blue", "a 25 year old woman with albinism", "very long white-blonde hair, pale blue eyes and very pale skin with faint freckles"),
    ("blonde-green", "a 24 year old Polish woman", "thick honey-blonde hair and clear green eyes, fair skin"),
    ("irish", "a 23 year old Irish woman", "long coppery red hair, green eyes and freckles across her nose, very fair skin"),
    ("slavic", "a 26 year old Ukrainian woman", "long ash-blonde hair and grey-blue eyes, fair skin"),
    ("italian", "a 27 year old Italian woman", "long dark brown waves and warm brown eyes, olive skin"),
    ("spanish", "a 25 year old Spanish woman", "dark chocolate-brown hair to her shoulders and dark eyes, olive skin"),
    ("greek", "a 26 year old Greek woman", "thick dark wavy hair and hazel-green eyes, light olive skin"),
    ("lebanese", "a 25 year old Lebanese woman", "long dark hair, strong brows and light grey-green eyes, olive skin"),
    ("persian", "a 27 year old Iranian woman", "long glossy black hair and very large dark eyes, warm olive skin"),
    ("moroccan", "a 24 year old Moroccan woman", "dark curly hair and amber-brown eyes, warm golden-brown skin"),
    ("ethiopian", "a 25 year old Ethiopian woman", "long dark curls and warm brown eyes, deep golden-brown skin"),
    ("somali", "a 26 year old Somali woman", "black hair in long twists and dark almond eyes, deep brown skin"),
    ("nigerian", "a 25 year old Nigerian woman", "a full natural afro and dark brown eyes, deep dark brown skin"),
    ("ghanaian", "a 24 year old Ghanaian woman", "black hair in neat braids and warm dark eyes, deep brown skin"),
    ("caribbean", "a 26 year old Jamaican woman", "loose dark curls with lighter ends and hazel eyes, warm brown skin"),
    ("african-american", "a 25 year old African-American woman", "long dark curls and light brown eyes, medium brown skin"),
    ("brazilian", "a 25 year old Brazilian woman", "long wavy sun-lightened brown hair and hazel eyes, warm golden-brown skin"),
    ("brazilian-2", "a 24 year old Afro-Brazilian woman", "a big natural curl pattern and dark eyes, warm brown skin"),
    ("colombian", "a 26 year old Colombian woman", "long dark hair and dark brown eyes, warm tan skin"),
    ("mexican", "a 25 year old Mexican woman", "long black hair and deep brown eyes, warm brown skin"),
    ("argentinian", "a 27 year old Argentinian woman", "chestnut brown hair and green-brown eyes, light olive skin"),
    ("korean", "a 24 year old Korean woman", "long glossy black hair and dark almond eyes, warm fair skin"),
    ("japanese", "a 25 year old Japanese woman", "a soft dark bob and dark eyes, fair skin"),
    ("chinese", "a 24 year old Chinese woman", "very long straight black hair and dark eyes, fair skin"),
    ("thai", "a 25 year old Thai woman", "long dark brown hair and warm dark eyes, golden tan skin"),
    ("vietnamese", "a 24 year old Vietnamese woman", "long black hair and dark eyes, warm light skin"),
    ("filipina", "a 25 year old Filipina woman", "long dark wavy hair and dark brown eyes, warm tan skin"),
    ("indian", "a 25 year old Indian woman", "very long thick black hair and large dark eyes, warm brown skin"),
    ("pakistani", "a 26 year old Pakistani woman", "long dark hair and light hazel eyes, warm tan skin"),
    ("kazakh", "a 25 year old Kazakh woman", "long black hair and dark eyes with a soft epicanthic fold, fair skin"),
    ("samoan", "a 26 year old Samoan woman", "long thick black wavy hair and dark eyes, warm brown skin"),
    ("maori", "a 25 year old Maori woman", "long dark wavy hair and dark brown eyes, warm brown skin"),
    ("native", "a 26 year old Native American woman", "long straight black hair and dark eyes, warm brown skin"),
    ("mixed-1", "a 24 year old woman of Black and Japanese heritage", "dark loose curls and dark eyes, light golden-brown skin"),
    ("mixed-2", "a 25 year old woman of Nordic and Ethiopian heritage", "loose dark-blonde curls and pale green eyes, light brown skin"),
]

# Each axis is (filter value, prompt fragment). The filter value is what the picker shows.
#
# Colouring is NOT sampled independently of heritage. The first version of this did that and
# produced a Northern European with very deep skin and an East African with bleached fair hair:
# the engine is handed two signals that disagree and picks one, which is the same failure the
# film compiler had when it wrote a crowd into an empty shot. So each heritage carries the
# tones and natural hair colours that actually go with it, and anything else has to arrive as
# an explicit DYE, which is both true to life and a good source of variety.
HERITAGE = [
    ("west-african", "a West African woman", ["deep", "brown"], ["black", "dark-brown"]),
    ("east-african", "an East African woman", ["deep", "brown"], ["black", "dark-brown"]),
    ("north-african", "a North African woman", ["brown", "olive", "tan"],
     ["black", "dark-brown", "chestnut"]),
    ("afro-caribbean", "an Afro-Caribbean woman", ["deep", "brown"], ["black", "dark-brown"]),
    ("southern-european", "a Southern European woman", ["olive", "tan", "fair"],
     ["black", "dark-brown", "chestnut", "auburn"]),
    ("northern-european", "a Northern European woman", ["fair", "very-fair"],
     ["blonde", "platinum", "copper", "auburn", "chestnut", "dark-brown"]),
    ("eastern-european", "an Eastern European woman", ["fair", "very-fair", "olive"],
     ["dark-brown", "chestnut", "blonde", "auburn"]),
    ("east-asian", "an East Asian woman", ["fair", "tan"], ["black", "dark-brown"]),
    ("south-asian", "a South Asian woman", ["brown", "tan", "olive"], ["black", "dark-brown"]),
    ("southeast-asian", "a Southeast Asian woman", ["brown", "tan"], ["black", "dark-brown"]),
    ("central-asian", "a Central Asian woman", ["tan", "olive", "fair"],
     ["black", "dark-brown", "chestnut"]),
    ("middle-eastern", "a Middle Eastern woman", ["olive", "tan", "fair"],
     ["black", "dark-brown", "chestnut"]),
    ("latin-american", "a Latin American woman", ["brown", "tan", "olive", "fair"],
     ["black", "dark-brown", "chestnut", "auburn"]),
    ("pacific-islander", "a Pacific Islander woman", ["deep", "brown", "tan"],
     ["black", "dark-brown"]),
    ("mixed", "a woman of mixed heritage", ["deep", "brown", "tan", "olive", "fair"],
     ["black", "dark-brown", "chestnut", "auburn", "copper"]),
]
TONE = dict([("deep", "very deep dark brown skin"), ("brown", "warm brown skin"),
             ("tan", "deep tan skin"), ("olive", "olive skin"), ("fair", "fair skin"),
             ("very-fair", "very pale skin")])
HAIR_COLOUR = dict([("black", "black"), ("dark-brown", "dark brown"),
                    ("chestnut", "chestnut brown"), ("auburn", "auburn"),
                    ("copper", "coppery red"), ("blonde", "dark blonde"),
                    ("platinum", "platinum blonde"), ("silver", "dyed silver-grey"),
                    ("bleached", "bleached white-blonde")])
DYES = ["silver", "bleached", "platinum", "copper"]     # arrive as a dye job, on anyone
HAIR_TEXTURE = [("straight", "straight"), ("wavy", "wavy"), ("curly", "curly"),
                ("coiled", "tightly coiled"), ("locs", "in locs")]
HAIR_LENGTH = [("shaved", "shaved close to the head"), ("crop", "cropped short"),
               ("bob", "cut to a jaw-length bob"), ("shoulder", "to her shoulders"),
               ("long", "long, past her shoulder blades"), ("waist", "very long, to her waist")]
AGE = [("early-20s", "in her early twenties"), ("late-20s", "in her late twenties"),
       ("early-30s", "in her early thirties")]
FEATURE = [
    ("freckles", "a dense spray of freckles across her nose and cheeks"),
    ("mole", "a small dark mole just below one eye"),
    ("gap-teeth", "a small gap between her front teeth"),
    ("heterochromia", "complete heterochromia, one eye noticeably lighter than the other"),
    ("vitiligo", "pale vitiligo patches across one cheek and her jaw"),
    ("albinism", "albinism, with near-white hair and very pale eyes"),
    ("strong-nose", "a strong straight aquiline nose"),
    ("wide-set", "unusually wide-set eyes"),
    ("sharp-jaw", "an extremely sharp defined jawline"),
    ("full-brows", "very thick strong eyebrows"),
    ("beauty-mark", "a beauty mark above her upper lip"),
    ("dimples", "deep dimples"),
    ("long-neck", "an unusually long neck"),
    ("high-forehead", "a high broad forehead"),
    ("hooded-eyes", "heavy hooded eyelids"),
    ("full-lips", "very full lips"),
    ("cheekbones", "very high wide cheekbones"),
    ("pointed-chin", "a small pointed chin"),
]


def sh(*a, **kw):
    return subprocess.run(a, capture_output=True, text=True, **kw)


# ── the starlet tier ───────────────────────────────────────────────────────────────
# Same format as warm, two deliberate moves: the roster's ages land in 20-23, and beauty is
# asked for as the mainstream consensus markers rather than as memorability. See patch notes.

STARLET_SUBJECT = ("conventionally beautiful in the way most people mean it, with a symmetrical "
                   "face, large bright eyes, a small straight nose, full lips, high soft "
                   "cheekbones and a delicate jaw, clear even skin and thick glossy hair")

# The realism clause has to work harder here, because asking for the consensus markers is
# exactly what makes a model reach for the retouched plastic version of them.
STARLET_REAL = ("She is alone in the frame and no one else is visible. Visible fine skin "
                "texture and pores, individual eyelashes, fine baby hairs at the hairline, a "
                "natural catchlight in each eye, one subtle asymmetry, shot on an 85mm lens at "
                "f2, faint film grain. Not retouched, no skin smoothing, no beauty filter, not "
                "a 3d render, not an illustration.")


def _younger(who):
    """the same person at the younger end of adult: a stated 23-27 lands in 20-23

    Derived rather than retyped so the starlet roster cannot drift out of step with the warm
    one - every heritage keeps its place, its colouring and its wording, and the only thing
    that moves is the number.
    """
    m = re.search(r"a (\d+) year old", who)
    if not m:
        return who
    a = int(m.group(1))
    return who.replace(m.group(0), "a %d year old" % (20 + (a - 23) % 4), 1)


STARLET_ROSTER = [(k, _younger(who), look) for k, who, look in WARM_ROSTER]


def plan_starlet(n, seed=20260923):
    """plan_warm's line-up, on the starlet roster and subject."""
    out = []
    for i in range(n):
        lap = i // len(STARLET_ROSTER)
        hkey, who, look = STARLET_ROSTER[i % len(STARLET_ROSTER)]
        pkey, pose = PERSONA[i % len(PERSONA)]
        skey, place = SETTING[(i + lap) % len(SETTING)]
        out.append({
            "id": "s%04d" % (i + 1), "tier": "starlet", "heritage": hkey, "persona": pkey,
            "setting": skey, "look": look,
            "prompt": ("Photo of %s who is %s, with %s. She is %s, %s. Wearing a simple soft "
                       "knit top. %s"
                       % (who, STARLET_SUBJECT, look, place, pose, STARLET_REAL)),
        })
    return out


def plan_warm(n, seed=20260923):
    """A line-up: the roster in order, each paired with a different persona and setting.

    Round-robin rather than random, so every heritage on the roster appears before any appears
    twice, and every persona and every setting gets used. With 36 on the roster, 10 personas
    and 6 settings, nothing repeats a (heritage, persona) pair until the roster is exhausted.
    """
    out = []
    for i in range(n):
        lap = i // len(WARM_ROSTER)          # which pass through the roster we are on
        hkey, who, look = WARM_ROSTER[i % len(WARM_ROSTER)]
        pkey, pose = PERSONA[i % len(PERSONA)]
        # 36 is a multiple of 6, so without the lap offset the second pass would hand every
        # face the same setting it had on the first
        skey, place = SETTING[(i + lap) % len(SETTING)]
        out.append({
            "id": "w%04d" % (i + 1), "tier": "warm", "heritage": hkey, "persona": pkey,
            "setting": skey, "look": look,
            "prompt": ("Photo of %s who is %s, with %s. She is %s, %s. Wearing a simple soft "
                       "knit top. %s"
                       % (who, WARM_SUBJECT, look, place, pose, WARM_REAL)),
        })
    return out


def plan(n, seed=20260922, tier="beauty"):
    """n attribute combinations, spread rather than clustered."""
    if tier == "warm":
        return plan_warm(n, seed)
    if tier == "starlet":
        return plan_starlet(n, seed)
    t = TIERS[tier]
    feats = t["features"] or FEATURE
    rng = random.Random(seed)
    out, seen = [], set()
    tries = 0
    while len(out) < n and tries < n * 200:
        tries += 1
        hkey, hphrase, tones, naturals = rng.choice(HERITAGE)
        feat = rng.choice(feats)
        dyed = rng.random() < 0.18
        if feat[0] == "albinism":
            # albinism decides its own colouring; it cannot also be "deep skin, black hair"
            tone, hc, dyed = "very-fair", "bleached", False
        else:
            tone = rng.choice(tones)
            hc = rng.choice(DYES) if dyed else rng.choice(naturals)
        ht = rng.choice(HAIR_TEXTURE)
        hl = rng.choice(HAIR_LENGTH)
        age = rng.choice(AGE)
        if hl[0] == "shaved" and ht[0] in ("locs", "curly", "wavy"):
            continue
        if ht[0] == "locs" and hl[0] in ("crop", "bob"):
            continue
        key = (hkey, tone, hc, ht[0], hl[0], feat[0])
        if key in seen:
            continue
        seen.add(key)
        # "in locs" is a placement, not an adjective: "black hair in locs", not "in locs hair"
        if ht[0] == "locs":
            hair = ("hair dyed %s and worn in locs" % HAIR_COLOUR[hc]) if dyed else \
                   ("%s hair in locs" % HAIR_COLOUR[hc])
        else:
            hair = ("%s hair dyed %s" % (ht[1], HAIR_COLOUR[hc])) if dyed else \
                   ("%s %s hair" % (ht[1], HAIR_COLOUR[hc]))
        # the beauty tier names the subject as exceptional up front; the casting tier does not
        who = ("%s who is %s" % (hphrase, t["subject"])) if t["subject"] else hphrase
        out.append({"id": "%s%04d" % (t["prefix"], len(out) + 1), "tier": tier,
                    "heritage": hkey, "tone": tone,
                    "hair_colour": hc, "hair_texture": ht[0], "hair_length": hl[0],
                    "age": age[0], "feature": feat[0], "dyed": dyed,
                    "prompt": ("Photo of %s, %s, with %s, %s %s, and %s. %s %s %s"
                               % (who, age[1], TONE[tone], hair, hl[1], feat[1],
                                  t["frame"], t["note"], t["real"])).replace("  ", " ")})
    return out


def make(n, seed=20260922, tier="beauty"):
    os.makedirs(OUT, exist_ok=True)
    rows = plan(n, seed, tier)
    for i, r in enumerate(rows):
        d = os.path.join(OUT, r["id"])
        os.makedirs(d, exist_ok=True)
        dest = os.path.join(d, "portrait.png")
        meta = os.path.join(d, "face.json")
        if os.path.exists(dest):
            continue
        cmd = [sys.executable, os.path.join(ROOT, "scripts", "comfy.py"), "run",
               os.path.join(ROOT, WF),
               "-s", "6.inputs.text=%s" % r["prompt"],
               "-s", "9.inputs.width=%d" % W, "-s", "9.inputs.height=%d" % H,
               "-s", "12.inputs.width=%d" % W, "-s", "12.inputs.height=%d" % H,
               "-s", "11.inputs.noise_seed=%d" % (seed + i * 17),
               "-s", "15.inputs.filename_prefix=claude-generated/faces/%s" % r["id"]]
        if tier == "beauty":
            cmd += ["-s", "7.inputs.guidance=3.2"]      # a touch less push than the default 4
        t0 = time.time()
        out = sh(*cmd, cwd=ROOT)
        m = re.search(r"-> (\S+\.png)", out.stdout or "")
        if not m:
            print("      FAILED %s: %s" % (r["id"], ((out.stderr or out.stdout or "")
                                                     .strip()[-200:])))
            continue
        shutil.copy(os.path.join(COMFY_OUT, m.group(1)), dest)
        r["seed"] = seed + i * 17
        json.dump(r, open(meta, "w"), indent=1)
        if r.get("persona"):          # roster-driven tiers: warm, starlet
            print("  %s %-8s %-18s %-13s %-9s %5.1fs"
                  % (r["id"], tier, r["heritage"], r["persona"], r["setting"],
                     time.time() - t0))
        else:
            print("  %s %-8s %-17s %-10s %-9s %-8s %-13s %5.1fs"
                  % (r["id"], tier, r["heritage"], r["tone"], r["hair_colour"],
                     r["hair_length"], r["feature"], time.time() - t0))


def index():
    rows = []
    for d in sorted(os.listdir(OUT)) if os.path.isdir(OUT) else []:
        p = os.path.join(OUT, d, "face.json")
        if os.path.exists(p) and os.path.exists(os.path.join(OUT, d, "portrait.png")):
            rows.append(json.load(open(p)))
    json.dump(rows, open(os.path.join(OUT, "faces.json"), "w"), indent=1)
    print("  %d faces -> %s" % (len(rows), os.path.join(OUT, "faces.json")))
    return rows


def cast(face_id, name, slug):
    """Stage a library face as a castable character: the portrait becomes the hero reference
    the whole pipeline already knows how to use."""
    src = os.path.join(OUT, face_id, "portrait.png")
    if not os.path.exists(src):
        print("  no such face: %s" % face_id)
        return
    meta = json.load(open(os.path.join(OUT, face_id, "face.json")))
    d = os.path.join(ROOT, "studio", "samples", "agency", slug)
    os.makedirs(d, exist_ok=True)
    shutil.copy(src, os.path.join(d, "hero.png"))
    shutil.copy(src, os.path.join(COMFY_IN, "agency_%s_hero.png" % slug))
    meta.update({"cast_as": name, "slug": slug, "from_face": face_id})
    json.dump(meta, open(os.path.join(d, "cast.json"), "w"), indent=1)
    print("  %s cast as %s (%s)" % (face_id, name, slug))
    print("  hero staged: %s" % os.path.join(d, "hero.png"))
    print("  now: python3 studio/_tools/agency.py --posts --who %s" % slug)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", type=int, default=0)
    ap.add_argument("--make", type=int, default=0)
    ap.add_argument("--index", action="store_true")
    ap.add_argument("--cast", default=None)
    ap.add_argument("--name", default="")
    ap.add_argument("--slug", default="")
    ap.add_argument("--seed", type=int, default=20260922)
    ap.add_argument("--tier", default="beauty", choices=sorted(TIERS))
    a = ap.parse_args()
    if a.plan:
        for r in plan(a.plan, a.seed, a.tier):
            print("  %s %-17s %-9s %-11s %-9s %-9s %-13s %s"
                  % (r["id"], r["heritage"], r["tone"], r["hair_colour"], r["hair_texture"],
                     r["hair_length"], r["age"], r["feature"]))
    if a.make:
        make(a.make, a.seed, a.tier)
        index()
    if a.index:
        index()
    if a.cast:
        cast(a.cast, a.name or a.cast, a.slug or a.cast)
    if not (a.plan or a.make or a.index or a.cast):
        ap.print_help()


if __name__ == "__main__":
    main()
