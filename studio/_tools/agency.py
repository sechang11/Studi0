#!/usr/bin/env python3
"""studio/_tools/agency.py - three invented people, a hero portrait each, then a feed.

The identity route here is Flux 2's own reference conditioning (workflows/68_flux2_ref.json):
the hero portrait is VAE-encoded and chained through ReferenceLatent, so the face is carried by
a picture rather than by a description or a trained LoRA. That is the same principle as the
film pipeline's composed start frame - the picture carries the person, the words carry what
happens - done with the image engine instead of the compositor.

WHAT MAKES THESE READ AS PHOTOGRAPHS, measured by looking at bake-offs first:
  - the prompt asks for a phone snapshot, not a portrait session. Studio light is the tell.
  - it names skin: pores, texture, a mole, faint under-eye shadow. "Beautiful" alone returns
    the airbrushed symmetric face that everyone recognises instantly as generated.
  - it asks for off-centre framing and sensor noise. Perfect composition is a tell.
  - no negative prompt exists on this graph (BasicGuider), so everything is said positively.

Every character is invented. No real person is referenced, named or used as a token.

    python3 studio/_tools/agency.py --heroes          # three hero portraits
    python3 studio/_tools/agency.py --posts           # the feed, from the heroes
    python3 studio/_tools/agency.py --posts --who rhea-sunwoo
    python3 studio/_tools/agency.py --score           # identity of each post vs its hero
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
COMFY = os.path.expanduser("~/ComfyUI")
COMFY_IN = os.path.join(COMFY, "input")
COMFY_OUT = os.path.join(COMFY, "output")
OUT = os.path.join(ROOT, "studio", "samples", "agency")

# The realism clause every prompt ends with. Kept in one place so a change is one change.
REAL = ("Shot on a phone in available light, unretouched: visible skin pores and texture, "
        "natural skin tone variation, a few stray hairs, slightly off-centre framing, shallow "
        "depth of field, faint sensor noise and a little motion in the hands. Not a studio "
        "portrait, not retouched, no beauty filter.")

# The brief is two things that fight each other: unusually beautiful, and indistinguishable
# from a real photograph. Asking only for realism returns an ordinary face; asking only for
# beauty returns the airbrushed symmetric one everybody can spot. So beauty is asked for as
# BONE STRUCTURE, which is what actually reads as striking, and every realism anchor stays.
STRIKING = ("She is unusually beautiful in a way people turn to look at, with the bone "
            "structure of a working model, but she is photographed casually by a friend and "
            "her skin is real and unretouched, not smoothed.")

PEOPLE = {
    "rhea-sunwoo": {
        "name": "Rhea Sunwoo",
        "handle": "rheasunwoo",
        "bio": "Seoul → LA. Film photos, late dinners, too much coffee.",
        "look": ("a 24 year old Korean woman with long straight black hair parted in the middle, "
                 "very high wide cheekbones, a sharp narrow jawline, long almond eyes with a "
                 "slight upward tilt, straight dark brows, a small dark mole below her left eye "
                 "and another on her right cheek, full lips and a long neck"),
        "hero": ("Phone photo of {look}, on a Seoul side street in the early evening, soft blue "
                 "hour light on her face, shop signs out of focus behind her, turned slightly "
                 "away and glancing back at the lens without smiling, wearing a plain black "
                 "crew-neck jumper."),
        "posts": [
            ("morning-light", "6am and the light was doing that thing again",
             "sitting cross-legged on a bed by a window in the early morning, wrapped in a grey "
             "duvet, holding a mug with both hands, looking down at it, low warm sun across the "
             "duvet and one side of her face"),
            ("noodle-shop", "second bowl. no regrets",
             "sitting at the counter of a small noodle shop at night, steam rising from a bowl in "
             "front of her, warm overhead light, she is laughing at something off to the side, "
             "chopsticks in one hand"),
            ("subway", "the long way home",
             "standing on a subway platform holding the strap of a canvas bag, fluorescent light "
             "overhead, a train blurred behind her, she is looking down the platform away from "
             "the camera, wearing a black jacket"),
            ("film-camera", "shot a whole roll of nothing",
             "crouched on a pavement in the afternoon changing the film in a small silver camera, "
             "looking down at her hands, hair falling forward across her face, parked cars behind"),
            ("rooftop", "he said the view was worth the stairs. it was fine",
             "standing on a rooftop at dusk in a long coat, city lights starting to come on "
             "behind her, wind moving her hair across her face, looking out over the edge"),
            ("bookshop", "bought three. needed none",
             "standing in a narrow second-hand bookshop aisle reading the back of a paperback, "
             "warm yellow light from a bulb overhead, shelves crowded on both sides"),
            ("rain-window", "rained the entire week",
             "sitting by a café window on a rainy afternoon with her chin on her hand, rain "
             "running down the glass beside her, grey flat daylight, a half-finished coffee on "
             "the table"),
            ("market", "the aunties always give me extra",
             "at an outdoor market in the late afternoon holding a paper bag of fruit, talking to "
             "someone out of frame, stalls and hanging produce behind her, low golden sun"),
            ("mirror", "outfit check before the thing",
             "taking a mirror photo in a hallway with her phone half covering her face, plain "
             "white wall behind, wearing a black slip dress over a white t-shirt, soft daylight "
             "from a window off to the left"),
            ("late-walk", "walked 9km and called it a personality",
             "walking along a quiet street at night past a lit convenience store, caught mid-step "
             "looking back over her shoulder, neon and streetlight on her face, slight motion blur"),
        ],
    },
    "naia-ferreira": {
        "name": "Naia Ferreira",
        "handle": "naiaferreira",
        "bio": "Lisbon. Salt water, ceramics, my grandmother's recipes.",
        "look": ("a 26 year old Afro-Brazilian woman with dark tightly-curled shoulder-length "
                 "hair, warm deep brown skin, high sculpted cheekbones and a strong jaw, a long "
                 "neck, a light spray of freckles across her nose and cheeks, wide-set dark "
                 "brown eyes with long lashes, a wide full mouth and a small gap between her "
                 "front teeth"),
        "hero": ("Phone photo of {look}, leaning against a pale yellow plastered wall in Lisbon "
                 "in the late afternoon, warm low sun raking across her face from the right, "
                 "chin slightly lifted, looking at the lens with a small amused smile, wearing "
                 "a white linen shirt with the collar open."),
        "posts": [
            ("surf-morning", "water was freezing. went in anyway",
             "standing on a beach at sunrise in a towel over a plain black swimsuit with a "
             "surfboard upright beside her, wet hair pushed back, cold pale morning light, "
             "laughing at the cold"),
            ("ceramics", "wobbly but mine",
             "sitting at a pottery wheel in a bright studio with clay on her hands and forearms, "
             "leaning in to look at the pot she is shaping, dusty daylight from a high window"),
            ("tram", "28 at 8am, empty for once",
             "sitting by the open window of an old yellow tram, arm resting on the sill, looking "
             "out at the street going past, morning sun striping across her face"),
            ("kitchen", "grandmother's recipe, my chaos",
             "in a small kitchen cooking, one hand stirring a pot and the other holding a wooden "
             "spoon up to taste, steam around her, warm overhead light, tiles behind her"),
            ("cliff-path", "took the long path on purpose",
             "walking a coastal cliff path in the afternoon in a loose linen dress, wind pulling "
             "her hair and dress sideways, ocean far below and behind her, strong sunlight"),
            ("market-flowers", "he threw in the extra bunch",
             "at a flower stall in the morning holding a wrapped bunch of eucalyptus and "
             "sunflowers against her chest, talking to the seller out of frame, dappled light"),
            ("rooftop-dinner", "everyone brought dessert. nobody brought bread",
             "at a crowded rooftop table at dusk mid-conversation with a glass in her hand, "
             "string lights overhead, plates and bottles across the table, friends blurred around"),
            ("laundry-line", "the wind does it better than any dryer",
             "hanging washing on a line on a small balcony in bright midday sun, reaching up with "
             "a peg in her mouth, white sheets moving around her"),
            ("record-shop", "spent the grocery money",
             "flipping through records in a narrow shop, head tilted reading a sleeve, warm "
             "tungsten light, crates and posters behind her"),
            ("night-swim", "last swim of the year probably",
             "sitting on a harbour wall at night wrapped in a big towel with wet hair, feet bare, "
             "lights of the water behind her, laughing at whoever is holding the camera"),
        ],
    },
    "elin-dahlqvist": {
        "name": "Elin Dahlqvist",
        "handle": "elindahlqvist",
        "bio": "Copenhagen. Bikes, bread, grey mornings. Slow things.",
        "look": ("a 27 year old Swedish woman with strawberry-blonde hair cut to her jaw and "
                 "tucked behind one ear, very fair skin with a light scatter of freckles across "
                 "her nose, pale grey-green eyes, high flat cheekbones and a sharp defined jaw, "
                 "a long straight nose, arched pale brows and a wide mouth"),
        "hero": ("Phone photo of {look}, indoors by a tall window on an overcast day, flat soft "
                 "north light from her left, head turned three-quarters to the window and eyes "
                 "coming back to the lens, wearing an oatmeal wool jumper."),
        "posts": [
            ("bakery", "queued 20 minutes. worth it",
             "standing outside a bakery on a cold grey morning holding a paper bag and a coffee, "
             "breath faintly visible, wearing a heavy grey coat and a thin scarf, flat daylight"),
            ("bike-canal", "flat city, no excuses",
             "riding an old bicycle along a canal path in the afternoon, one hand on the bars, "
             "looking off to the side, coloured townhouses across the water behind her"),
            ("studio-desk", "deadline face",
             "at a plain wooden desk by a window working on a laptop with a pencil in her mouth, "
             "grey daylight across the desk, plants on the sill, papers everywhere"),
            ("sauna-dock", "4 degrees. screamed. recommend",
             "sitting on a wooden dock wrapped in a towel after a cold swim, hair wet and pushed "
             "back, steam off the water behind her, pale winter light, laughing"),
            ("bread", "fourth attempt. finally",
             "holding a round loaf of bread up towards the camera in a kitchen, flour on her "
             "hands and one cheek, soft window light, wooden counter behind"),
            ("gallery", "stood in front of this for ten minutes",
             "standing in a white gallery room looking at a painting out of frame, hands in coat "
             "pockets, even diffuse ceiling light, polished concrete floor"),
            ("allotment", "tomatoes: ambitious. radishes: realistic",
             "kneeling in a small allotment garden in the morning with soil on her gloves, "
             "looking up at the camera squinting slightly in the light, plants and a shed behind"),
            ("tram-window", "grey on grey on grey",
             "sitting on a bus with her head resting against the window, watching the street, "
             "flat overcast light on her face, reflections in the glass"),
            ("dinner-candles", "she made it look easy. it was not",
             "at a small dinner table indoors in the evening lit mostly by candles, leaning on "
             "her elbows listening to someone off frame, warm low light, wine glasses and plates"),
            ("winter-walk", "the dog picked the route",
             "walking in a bare winter park at dusk in a long coat with her hands in her pockets, "
             "cold blue light, breath visible, bare trees behind her"),
        ],
    },
}

HERO_WF = "workflows/26_flux2_t2i.json"
POST_WF = "workflows/68_flux2_ref.json"


def sh(*a, **kw):
    return subprocess.run(a, capture_output=True, text=True, **kw)


def run_wf(wf, sets, label=""):
    cmd = [sys.executable, os.path.join(ROOT, "scripts", "comfy.py"), "run", os.path.join(ROOT, wf)]
    for k, v in sets:
        cmd += ["-s", "%s=%s" % (k, v)]
    t0 = time.time()
    r = sh(*cmd, cwd=ROOT)
    m = re.search(r"-> (\S+\.png)", r.stdout or "")
    if not m:
        print("      FAILED %s: %s" % (label, ((r.stderr or r.stdout or "").strip()[-300:])))
        return None, time.time() - t0
    return os.path.join(COMFY_OUT, m.group(1)), time.time() - t0


def heroes(who=None, seed=None):
    os.makedirs(OUT, exist_ok=True)
    for slug, p in PEOPLE.items():
        if who and slug != who:
            continue
        d = os.path.join(OUT, slug)
        os.makedirs(d, exist_ok=True)
        prompt = p["hero"].format(look=p["look"]) + " " + STRIKING + " " + REAL
        s = seed if seed is not None else (abs(hash(slug)) % 90000 + 1000)
        src, secs = run_wf(HERO_WF, [
            ("6.inputs.text", prompt), ("9.inputs.width", 1024), ("9.inputs.height", 1280),
            ("12.inputs.width", 1024), ("12.inputs.height", 1280),
            ("11.inputs.noise_seed", s),
            ("15.inputs.filename_prefix", "claude-generated/agency/%s_hero" % slug)], slug)
        if not src:
            continue
        dest = os.path.join(d, "hero.png")
        shutil.copy(src, dest)
        shutil.copy(src, os.path.join(COMFY_IN, "agency_%s_hero.png" % slug))
        print("  %-16s hero  %5.1fs  seed %s  -> %s" % (p["name"], secs, s, dest))


def posts(who=None, only=None, seed_base=7000):
    for slug, p in PEOPLE.items():
        if who and slug != who:
            continue
        d = os.path.join(OUT, slug)
        ref = "agency_%s_hero.png" % slug
        if not os.path.exists(os.path.join(COMFY_IN, ref)):
            print("  %s: no hero staged; run --heroes first" % slug)
            continue
        for i, (key, caption, scene) in enumerate(p["posts"]):
            if only and key not in only:
                continue
            dest = os.path.join(d, "post_%02d_%s.png" % (i + 1, key))
            if os.path.exists(dest):
                print("  %-16s %-14s exists" % (p["name"], key))
                continue
            prompt = ("A candid phone photo of the same woman as in the reference images: %s. "
                      "She is %s. Keep her face, bone structure, hair and freckles exactly as in "
                      "the references. %s" % (p["look"], scene, REAL))
            src, secs = run_wf(POST_WF, [
                ("42.inputs.image", ref), ("46.inputs.image", ref),
                ("sg1_6.inputs.text", prompt),
                ("sg1_25.inputs.noise_seed", seed_base + i * 37),
                ("sg1_95.inputs.value", "true"),
                ("9.inputs.filename_prefix", "claude-generated/agency/%s_%s" % (slug, key))],
                "%s/%s" % (slug, key))
            if not src:
                continue
            shutil.copy(src, dest)
            print("  %-16s %-14s %5.1fs -> %s" % (p["name"], key, secs, os.path.basename(dest)))


def score(who=None):
    """Identity of every post against its own hero, with the studio's CLIP scorer."""
    sys.path.insert(0, os.path.join(ROOT, "studio", "_tools"))
    import identity as ID
    rows = []
    for slug, p in PEOPLE.items():
        if who and slug != who:
            continue
        d = os.path.join(OUT, slug)
        hero = os.path.join(d, "hero.png")
        if not os.path.exists(hero):
            continue
        from PIL import Image
        he = ID.embed(Image.open(hero))
        for f in sorted(os.listdir(d)):
            if not f.startswith("post_"):
                continue
            im = Image.open(os.path.join(d, f))
            s = float((he * ID.embed(im)).sum())
            rows.append({"who": slug, "post": f, "identity": round(s, 3)})
            print("  %-16s %-34s %.3f%s" % (p["name"], f, s, "   <-- LOW" if s < 0.55 else ""))
    json.dump(rows, open(os.path.join(OUT, "identity.json"), "w"), indent=1)
    if rows:
        v = [r["identity"] for r in rows]
        print("\n  %d posts, identity mean %.3f, min %.3f, below 0.55: %d"
              % (len(v), sum(v) / len(v), min(v), sum(1 for x in v if x < 0.55)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--heroes", action="store_true")
    ap.add_argument("--posts", action="store_true")
    ap.add_argument("--score", action="store_true")
    ap.add_argument("--who", default=None)
    ap.add_argument("--only", default=None, help="comma-separated post keys")
    ap.add_argument("--seed", type=int, default=None)
    a = ap.parse_args()
    only = [x for x in (a.only or "").split(",") if x]
    if a.heroes:
        heroes(a.who, a.seed)
    if a.posts:
        posts(a.who, only)
    if a.score:
        score(a.who)
    if not (a.heroes or a.posts or a.score):
        ap.print_help()


if __name__ == "__main__":
    main()
