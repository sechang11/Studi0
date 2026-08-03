#!/usr/bin/env python3
"""Build films/derby.json - THE DERBY, a ~55s vertical short.

STRUCTURAL RECREATION of a measured reference short. The reference put two real, named
footballers into anime and crossed them over with a character from a licensed series. This
reproduces the reference's EDIT - its rhythm, density curve, effect vocabulary and shot
grammar - with two invented players, RASK and VIRO, who are not anybody.

What is copied is the structure, which is what actually made the reference work:

    182 shots / 51.8s        median 0.10s        87% of shots under 0.5s
    cuts per 5s block:  9 10 6 | 25 | 14 | 27 26 22 | 8 | 33 | 2
                        build    BURST  rest  ASSAULT  rest FINAL resolve

Every beat below is one entry of SPORTS_CLASH_50S in scripts/scene_templates.py, in order.
The arc decides the cutting; this file only decides what is on screen. That separation is
the point of the template system: to re-time the piece, edit the arc, not this file.

    python3 films/build_derby.py
    python3 scripts/make_sheets.py films/derby.json
    python3 scripts/short.py films/derby.json
"""
import collections, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from scene_templates import SPORTS_CLASH_50S, expand as ex   # noqa: E402

OUT = os.path.join(HERE, "derby.json")

STYLE = ("modern sports anime, bold cel shading, heavy black ink outlines, "
         "extreme high contrast, stadium floodlight rim light, saturated teal and orange, "
         "speed lines, dramatic perspective, cinematic")

# ── content, one entry per arc beat ───────────────────────────────────────────
# (id, prompt, motion, refs, line-or-None). Order must match SPORTS_CLASH_50S.
CONTENT = [
    # ── setup: 0-15s. Establish both players, the stadium, and the stakes.
    ("010_stadium",
     "Vast night stadium from pitch level, hundred thousand phone lights in the stands, "
     "floodlights blazing through drifting haze, a single figure walking out of the tunnel "
     "into the light, enormous scale",
     "Light haze drifts through the floodlight beams. The crowd lights ripple across the stands "
     "in a slow wave. The figure walks steadily out of the tunnel toward camera.",
     None, None),
    ("020_rask",
     "Low hero angle of {RASK} standing on the halfway line, black and silver "
     "kit number 9, shoulders squared, steam rising off him, floodlights flaring behind "
     "his head",
     "Steam rises off his shoulders. Sweat runs down his face. He rolls his neck once and "
     "sets his jaw. The floodlight flares behind him.",
     ["RASK"], ("RASK", "You have never beaten me.")),
    ("030_viro",
     "Low hero angle of {VIRO} bouncing on his toes at the centre circle, teal and orange "
     "kit number 7, grinning, ball spinning on the grass at his feet",
     "He bounces on his toes and grins wider. The ball spins on the grass. Water beads "
     "fly off his hair as he shakes his head.",
     ["VIRO"], ("VIRO", "You have never had to.")),
    ("040_walkup",
     "Two players walking toward each other down the centre line from opposite ends, "
     "backlit by opposing floodlight banks, long shadows converging, dust drifting",
     "Both walk toward each other from opposite ends of frame, shadows converging on the "
     "centre line. Dust drifts through the beams. The camera pushes in low and fast between them.",
     ["RASK", "VIRO"], None),
    ("050_crowd",
     "Roaring crowd wall packed to the roof, faces lit teal and orange, scarves raised, "
     "flares smoking in the upper tier",
     "The whole stand rises at once. Scarves whip overhead. Orange flare smoke rolls "
     "across the upper tier and lights the faces from below.",
     None, None),
    # flash-forward: the fight teased before it starts
    ("060_flashfwd",
     "Blurred impressionistic collision of two players mid-air over the pitch, turf "
     "exploding outward, motion streaked, faces indistinct, pure kinetic abstraction",
     "Two blurred figures collide mid-air and turf explodes outward in a ring. Everything "
     "streaks. The frame is pure motion.",
     None, None),
    ("070_whistle",
     "Extreme macro of a referee whistle at the instant of the blast, spray "
     "atomising off the metal, everything behind thrown out of focus",
     "The whistle blasts and a burst of spray atomises off the metal. The background snaps "
     "out of focus. The sound hits like a starting gun.",
     None, None),
    ("080_ignite",
     "Full body shot of {RASK} exploding into his first stride, turf tearing up in a spray "
     "behind his boot, aura of white-hot light building around him",
     "Turf tears up behind his boot in a spray. White-hot light builds around him and "
     "floods outward. He explodes forward out of frame.",
     ["RASK"], None),

    # ── burst1: 15-20s. First exchange. This is where the piece changes gear.
    ("090_drive",
     "Low tracking shot racing alongside {VIRO} at full sprint with the ball, dry turf "
     "spraying up in his wake, defenders smearing past out of focus",
     "He sprints flat out with the ball, turf spraying behind him. Defenders smear past out "
     "of focus. The camera races alongside and cannot quite keep up.",
     ["VIRO"], None),
    ("100_clash1",
     "Violent shoulder-to-shoulder collision between two players at full speed, turf "
     "blasting outward in a ring, both bodies deforming with the force, low angle",
     "The two collide shoulder to shoulder at full speed. Turf blasts outward in a ring. "
     "Both bodies twist with the force and keep driving.",
     ["RASK", "VIRO"], None),
    ("110_nutmeg",
     "Ground-level macro of a soccer ball threaded between two boots on dry grass, loose turf "
     "spraying off it, studs skidding past on either side",
     "The ball threads between two boots, loose turf spraying off it. Studs skid past "
     "on either side and tear up the grass.",
     None, None),
    ("120_recover",
     "Explosive shot of {RASK} pivoting and tearing back into the chase, one hand down in "
     "the turf, spray flying, rage on his face",
     "He plants one hand in the turf, pivots hard and tears back into the chase. Spray "
     "flies. His face contorts with effort.",
     ["RASK"], None),

    # ── breathe: 20-25s. Let the crowd back in so the next burst lands.
    ("130_bench",
     "Close shot of a stadium crowd frozen mid-roar, one child in the front row "
     "with both hands pressed to the glass",
     "The crowd roars. The child presses both hands to the glass and does not blink. The noise shakes the barrier between them.",
     None, None),
    ("140_scramble",
     "Chaotic goalmouth scramble, four sets of legs and a ball, churned turf everywhere, "
     "shot from inside the six-yard box at ground level",
     "Legs and studs thrash through the mud around the ball. Turf sprays in every "
     "direction. The ball squirts loose and out of frame.",
     None, None),
    ("150_eyes_v",
     "Extreme close-up of the eyes of {VIRO}, sweat on his lashes, pupils locked on "
     "something off frame, absolute focus",
     "Sweat runs off his lashes. His pupils narrow and lock. Nothing else on his face moves.",
     ["VIRO"], ("VIRO", "Now watch.")),

    # ── assault: 25-40s. The long sustained sequence. Nine beats, almost no relief.
    ("160_clash2",
     "Two players airborne in a full aerial duel above a floodlit box, both twisting for "
     "the ball, floodlight flare streaking past them",
     "Both leave the ground together and twist for the ball in mid-air, light streaking past "
     "horizontally. They hang, then drop hard.",
     ["RASK", "VIRO"], None),
    ("170_header",
     "Devastating slow-motion header, ball deforming against a forehead, water blasting off "
     "in a corona, neck muscles corded",
     "The ball deforms against his forehead and sweat blasts off in a corona. His neck "
     "muscles cord. The ball rockets away.",
     ["RASK"], None),
    ("180_clash3",
     "Two players sliding through dry turf in a full-blooded tackle, twin walls of "
     "grass thrown up on either side, low ground-level angle",
     "Both slide through the turf and throw twin walls of grass. The ball pops "
     "vertically out of the collision.",
     ["RASK", "VIRO"], None),
    ("190_run",
     "Accelerating tracking shot behind {VIRO} weaving through a collapsing defensive line, "
     "bodies flashing past on both sides, the goal growing ahead",
     "He weaves through the collapsing line, bodies flashing past on both sides. The goal "
     "grows fast ahead. The camera accelerates behind him.",
     ["VIRO"], None),
    ("200_clash4",
     "Brutal mid-air collision of two players over the penalty spot, both fully extended, "
     "shockwave ring of turf blasting outward beneath them",
     "Both fully extend and collide over the penalty spot. A shockwave of turf blasts "
     "outward beneath them. Everything freezes, then drops.",
     ["RASK", "VIRO"], None),
    ("210_save",
     "Goalkeeper fully extended in mid-air, fingertips on the ball, floodlights behind "
     "turning the air into a curtain of white sparks",
     "The keeper extends fully and gets fingertips to the ball. The air behind turns to a "
     "curtain of white sparks in the floodlights. The ball spins away.",
     None, None),
    ("220_clash5",
     "Two players locked shoulder to shoulder driving through the turf, neither "
     "giving ground, turf fanning out behind them both",
     "Both drive forward locked together, neither giving ground, turf fanning out behind "
     "them. Their boots tear parallel furrows in the turf.",
     ["RASK", "VIRO"], None),
    ("230_clash6",
     "A soccer ball struck at full power from close range, the leather visibly compressing, air "
     "distortion ring around it, boot buried in it",
     "The ball compresses against the boot and a ring of distorted air blasts outward. It "
     "leaves the frame faster than the eye can follow.",
     ["RASK"], None),
    ("240_counter",
     "Accelerating tracking shot of {RASK} breaking upfield with the ball, "
     "the whole opposition turning behind him, stadium light streaking",
     "He breaks upfield with the ball and the whole opposition turns behind him. Stadium "
     "light streaks past. Each stride covers more ground than the last.",
     ["RASK"], None),
    ("250_bar",
     "Crossbar shuddering violently after a strike, dust shaking loose off it, "
     "the whole goal frame ringing",
     "The bar shudders violently and dust shakes loose off it. The whole frame "
     "of the goal rings and keeps vibrating.",
     None, None),
    ("260_down",
     "Player hitting the turf hard and sliding through the grass, sheet of "
     "loose turf thrown up over him, ground-level angle",
     "He hits the turf hard and slides, throwing a sheet of loose turf "
     "over himself. He skids to a stop face down.",
     ["VIRO"], None),

    # ── breathe: 40-45s. The two slowest beats in the piece, right before the end.
    ("270_breath_r",
     "Close shot of {RASK} bent double with hands on his knees, chest heaving, sweat "
     "dripping off his face onto the grass",
     "He is bent double, chest heaving. Sweat drips off his face onto the grass. He lifts "
     "his head slowly.",
     ["RASK"], ("RASK", "Is that all you have?")),
    ("280_breath_v",
     "Close shot of {VIRO} straightening up, shirt clinging with sweat, smiling with "
     "his chest still heaving, floodlight behind him",
     "He straightens up, chest heaving. The smile arrives "
     "slowly. The floodlight burns behind his head.",
     ["VIRO"], ("VIRO", "I have the last minute.")),

    # ── final: 45-50s. The densest block in the piece.
    ("290_lastrun",
     "Furious final sprint of {VIRO} down the touchline, the entire stadium "
     "blurred into streaks of light behind him",
     "He sprints down the touchline and the entire stadium blurs into streaks of light "
     "behind him. Floodlights tear past in streaks.",
     ["VIRO"], None),
    ("300_clash7",
     "Two players colliding at the corner of the box at full pace, turf exploding "
     "upward between them, both refusing to fall",
     "They collide at full pace and turf explodes upward between them. Both "
     "stagger and neither goes down.",
     ["RASK", "VIRO"], None),
    ("310_clash8",
     "A soccer ball ripping through a wall of loose turf at knee height, carving a visible "
     "channel through it, motion-blurred",
     "The ball rips through loose turf at knee height and carves a visible channel "
     "through it. Everything blurs behind it.",
     None, None),
    ("320_windup",
     "Extreme low angle of a leg drawing back for the strike, every muscle taut, the goal "
     "and keeper tiny in the deep background, grass suspended mid-air",
     "The leg draws back and every muscle goes taut. Loose grass hangs in the air. The "
     "whole frame compresses toward the strike.",
     ["VIRO"], None),
    ("330_clash9",
     "The instant of contact between boot and ball, blinding white flash at the point of "
     "impact, everything else silhouetted black",
     "Boot meets ball and a blinding white flash erupts at the point of contact. Everything "
     "else goes to black silhouette.",
     ["VIRO"], None),

    # ── resolve: the longest hold in the piece, then silence.
    ("340_goal",
     "Wide view from behind a soccer goal at the instant the ball hits the back of the net, "
     "the white mesh bulging outward, goalkeeper sprawled on the grass, packed stadium "
     "crowd erupting behind, floodlights",
     "The ball punches into the back of the net and the mesh bulges outward. The keeper "
     "lands sprawling on the grass. The crowd behind erupts to its feet.",
     None, None),
    ("350_after",
     "Wide final shot of two exhausted players on the grass at the final whistle, one on his "
     "knees, one standing with a hand out to him, empty stadium light, floodlights dimming",
     "The stadium noise falls away. One kneels, the other stands over him and puts out a hand. "
     "Neither says anything. Slow crane up and away.",
     ["RASK", "VIRO"], None),
]


# ── danbooru tags for the anime checkpoint ────────────────────────────────────
# Animagine/Illustrious want TAGS, not the cinematic prose above - fed Qwen-style
# prompts they return abstract colour shapes. See craft/ANIME_MODELS.md. The prose
# prompts are kept because they still drive the Qwen path; this is a parallel track.
#
# Character tags live in ONE place and are pasted in automatically from each beat's
# `ref` list, so a character cannot drift by being described differently in shot 30
# than in shot 3. The tag block does most of the identity work - a weight sweep showed
# the character recognisable even at IPAdapter weight 0.
CHAR_TAGS = {
    "RASK": ("dark red hair, undercut, yellow eyes, scar on eyebrow, "
             "black soccer jersey, dark uniform, silver trim, number 9"),
    "VIRO": ("long dark brown curly hair, ponytail, brown eyes, gold ear stud, "
             "teal soccer jersey, orange trim, teal shirt, number 7"),
}
SCENE = "soccer stadium, floodlights, crowd, night"
# Animagine skews feminine: "1boy, solo" alone rendered VIRO as an androgynous
# female character. `male focus` plus a female negative is what actually holds it.
MALE = "male focus, mature male, masculine"
QUALITY = "masterpiece, best quality, very aesthetic, absurdres"

# action + camera per beat, in CONTENT order. Scene, character and quality tags append.
TAGS = [
    # Each entry must depict its CAPS line LITERALLY. These were previously written as
    # generic action shots and the story was added afterwards, so caption and image
    # disagreed and the film read as random clips with words over them. A viewer should
    # be able to follow this with the sound off and the captions covered.
    #
    # Two devices do the wordless work: a SCOREBOARD showing 1-0 then 1-1, and a visible
    # match CLOCK. Broadcasts use both for exactly this reason.
    #
    # Also note almost every beat now has a character in it. Beats with nobody in them
    # read as stock b-roll, and there were eleven of them.
    "no humans, scoreboard, stadium jumbotron, glowing numbers, score 1-0, 89:00 on clock, wide shot, night",
    "standing, arms crossed, confident smirk, looking at viewer, from below, close-up",
    "standing, clenched fist, frustrated, gritted teeth, looking away, close-up, from side",
    "no humans, scoreboard, stadium jumbotron, score 1-0, 89:00, close-up, glowing numbers",
    "crowd, many people, cheering, standing, arms raised, scarves, wide shot, spectators",
    "close-up, determined expression, eyes narrowed, sweat, looking forward, dramatic lighting",
    "no humans, soccer ball on centre spot, green grass, close-up, referee whistle, low angle",
    "shielding soccer ball, arms spread wide, back to viewer, protecting ball, wide stance",
    "running with soccer ball, dribbling forward, determined, full body, from side, speed lines",
    "shoulder barge, pushing opponent away, aggressive, from below, action pose, full body",
    "on the ground, fallen, reaching out, soccer ball rolling away, low angle, ground level",
    "sprinting, running back, chasing, urgent, from behind, full body, motion lines",
    "child, boy, crowd, front row, hands on barrier, watching, close-up, spectator",
    "no humans, scoreboard clock, 00:50, glowing numbers, close-up, dark",
    "standing still, stopped, breathing hard, eyes wide, realisation, close-up, from front",
    "running toward viewer, sprinting, intense stare, foreshortening, from below, speed lines",
    "no humans, scoreboard clock, 00:40, glowing numbers, close-up, dark",
    "sliding tackle, stretched out, leg extended, low angle, ground level, turf spray",
    "dribbling soccer ball, turning, weaving, dynamic pose, full body, from side",
    "shooting, kicking soccer ball, follow through, full body, from side, action pose",
    "goalkeeper, diving, mid-air, gloves on soccer ball, goal net, from side, save",
    "no humans, scoreboard clock, 00:30, glowing numbers, close-up, dark",
    "long range shot, kicking, leaning back, full body, from side, powerful",
    "running with soccer ball, breaking away, counter attack, from behind, wide shot",
    "no humans, soccer ball hitting crossbar, goal frame, close-up, impact, low angle",
    "on hands and knees, getting up, exhausted, determined, low angle, ground level",
    "bent over, hands on knees, exhausted, sweat dripping, close-up, from side",
    "standing up straight, wiping face, exhausted, small smile, close-up, backlighting",
    "running with soccer ball, sprinting alone, full body, from side, tracking, speed lines",
    "defensive stance, arms out, blocking, wide stance, from front, full body, last defender",
    "no humans, soccer ball loose on grass, close-up, low angle, motion",
    "winding up to shoot, leg back, tense, full body, from side, about to kick",
    "kicking soccer ball, moment of impact, close-up, foot and ball, white flash, impact",
    "no humans, soccer ball in goal net, mesh bulging, scoreboard 1-1 in background, from behind goal",
    "2boys, one kneeling, one standing offering hand, handshake, wide shot, empty stadium, aftermath",
]

# ── the story spine ───────────────────────────────────────────────────────────
# One caption per beat, in CONTENT order. THIS IS THE FIX FOR "it feels random".
#
# The reference cuts at a 0.10s median and still reads, because it cuts over things the
# viewer already recognises - real footballers, a famous anime character. Recognition is
# free there. Our characters are invented, so at 0.2s a shot is gone before it means
# anything, and 86% of beats previously said nothing at all. The story existed only in
# the prompts.
#
# So the words carry the story and the images illustrate it, not the other way round.
# There is also a CLOCK - the film is the last minute of a match - because a countdown
# gives every cut a reason to exist and turns 174 disconnected images into one event.
CAPS = [
    "FINAL. 89th minute.",
    "RASK has never lost this fixture.",
    "VIRO has never won it.",
    "One minute left. RASK leads 1-0.",
    "Ninety thousand people. One goal in it.",
    "It will be decided in sixty seconds.",
    "Restart.",
    "RASK only has to run out the clock.",
    "So VIRO stops waiting to be passed to.",
    "RASK puts him straight back down.",
    "Ball gone.",
    "RASK recovers. He always recovers.",
    "The kid in the front row has never seen VIRO win.",
    "Fifty seconds.",
    "So VIRO stops chasing the ball.",
    "And starts chasing RASK.",
    "Forty seconds.",
    "Every tackle now is a foul waiting to be given.",
    "VIRO goes again.",
    "And again.",
    "The keeper keeps it out.",
    "Thirty seconds.",
    "VIRO shoots from anywhere now.",
    "RASK breaks. One pass and it is over.",
    "Off the bar.",
    "VIRO goes down. He does not stay down.",
    "Twenty seconds.",
    "Ten.",
    "VIRO takes it himself. Nobody else touches it.",
    "Last man.",
    "The ball comes loose.",
    "Five.",
    "Now.",
    "1-1.",
    "He still has not beaten him. He has not lost to him either.",
]
assert len(CAPS) == len(CONTENT), f"{len(CAPS)} captions vs {len(CONTENT)} beats"

assert len(TAGS) == len(CONTENT), f"{len(TAGS)} tag entries vs {len(CONTENT)} beats"

assert len(CONTENT) == len(SPORTS_CLASH_50S), \
    f"{len(CONTENT)} content entries vs {len(SPORTS_CLASH_50S)} arc beats - they must pair"

B = []
REFMAP = {1: ["RASK"], 2: ["VIRO"], 5: ["VIRO"], 7: ["RASK"], 8: ["VIRO"], 9: ["RASK"],
          10: ["VIRO"], 11: ["RASK"], 14: ["VIRO"], 15: ["VIRO"], 17: ["VIRO"],
          18: ["VIRO"], 19: ["VIRO"], 22: ["VIRO"], 23: ["RASK"], 25: ["VIRO"],
          26: ["RASK"], 27: ["VIRO"], 28: ["VIRO"], 29: ["RASK"], 31: ["VIRO"],
          32: ["VIRO"], 34: ["RASK", "VIRO"]}

for (block, tmpl, inten), (bid, prompt, motion, refs, line) in zip(SPORTS_CLASH_50S, CONTENT):
    refs = REFMAP.get(len(B))
    d = collections.OrderedDict(id=bid, template=tmpl, intensity=round(inten, 2), block=block)
    if refs:
        d["ref"] = refs
    d["clip_secs"] = 4
    d["prompt"] = prompt
    d["motion"] = motion
    if line:
        d["line"] = {"who": line[0], "text": line[1]}
    ct = ", ".join(CHAR_TAGS[r] for r in (refs or []))
    lead = "1boy, solo, " if len(refs or []) == 1 else ""
    d["caption"] = CAPS[len(B)]
    d["tags"] = ", ".join(x for x in
                          [lead.rstrip(", "), ct, MALE if refs else "", TAGS[len(B)],
                           SCENE, QUALITY] if x)
    B.append(d)

film = collections.OrderedDict(
    title="THE DERBY",
    hook="he has never|been beaten",
    # drawn in post, not generated - diffusion cannot render specific numbers
    hud={"before": "RASK  1 - 0  VIRO", "after": "RASK  1 - 1  VIRO",
         "goal_at": 60.2},
    fps=24,
    engine="higgs_v3",
    style_lora="qwen_image_2512_storybook_anime_lora.safetensors",
    style_strength=1.0,
    style=STYLE,
    sheets={"RASK": "sheet_rask.png", "VIRO": "sheet_viro.png"},
    # anime-drawn sheets for the SDXL/IPAdapter path. A sheet must be drawn in the
    # style it will be used in - a comic sheet fights an anime checkpoint.
    anime_sheets={"RASK": "sheet_anime_rask.png", "VIRO": "sheet_anime_viro.png"},
    keyframe_engine="anime",
    anime_ckpt="animagine-xl-4.0.safetensors",
    ipadapter_weight=0.6,
    # `designs` feeds make_sheets.py. `characters` is what the per-shot prompts expand to,
    # and must point AT the sheet rather than re-describe the face - re-describing is how
    # a character drifts between shots.
    designs={
        "RASK": "a tall broad-shouldered young male footballer, short dark red hair shaved "
                "at the sides, pale amber eyes, hard unsmiling face, small scar through one "
                "eyebrow, black and silver football kit with the number 9",
        "VIRO": "a lean agile young male footballer, long dark curls tied back, deep brown "
                "eyes, easy confident half-smile, single gold ear stud, teal and orange "
                "football kit with the number 7",
    },
    characters={
        "RASK": "the tall red-haired striker in the black and silver number 9 kit from the "
                "reference image",
        "VIRO": "the curly-haired playmaker in the teal and orange number 7 kit from the "
                "reference image",
    },
    voices={
        "RASK": {"engine": "higgs_v3", "voice": "voices_examples/male/male_01.wav"},
        "VIRO": {"engine": "higgs_v3", "voice": "voices_examples/higgs_audio/vex.wav"},
    },
    music=[{"at": 0, "prefix": "derby_theme", "bpm": 174, "key": "F minor", "seconds": 70,
            "level": 1.0,
            "tags": "aggressive hybrid trap orchestral, hard 808 slides, distorted brass "
                    "stabs, driving string ostinato, stadium crowd roar texture, "
                    "chanting choir, huge drop, instrumental"}],
    beats=B,
)
json.dump(film, open(OUT, "w", encoding="utf-8"), indent=2, ensure_ascii=False)

shots = secs = 0
for b in B:
    cuts, imp = ex(b, float(b["clip_secs"]))
    shots += len(cuts) + (1 if imp else 0)
    secs += sum(c["len"] for c in cuts) + (0.083 if imp else 0)
print(f"wrote {OUT}")
print(f"  beats {len(B)}  ->  {shots} shots, {secs:.1f}s, median ~{secs/shots:.2f}s")
print(f"  reference:              182 shots, 51.8s, median 0.10s")
print(f"  generations: {len(B)} keyframes + {len(B)} clips")
print(f"  dialogue lines: {sum(1 for b in B if b.get('line'))}")
