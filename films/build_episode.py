#!/usr/bin/env python3
"""Build films/episode01.json - THE DERBY Ep.1, "The Last Minute of the Year". ~20 minutes.

Script: films/EPISODE_01.md.  Grammar: craft/ANIME_EPISODE.md.

WHY THIS IS NOT build_derby.py WITH MORE BEATS

The vertical short's rule was "generate few, cut many" - one clip sliced into 6-10 shots,
energy from cutting. An episode is the reverse: shots are HELD, and tension comes from what
is withheld. Every template here is named for the dramatic job it does.

WHAT THE BUILDER DOES FOR YOU

You write SCENES as dialogue and moments. It expands them into coverage:

    ("say", "VIRO", "I know what the record is.")   -> a `speak` beat on VIRO
                                                     -> AND a `react` beat on the listener

That reaction is not decoration. It is where an episode earns its emotion, and it is
exactly what the rejected 20-minute film had none of. Making it automatic means it cannot
be forgotten on a tired scene.

DAMAGE CONTINUITY

Each scene declares a `wear` level. It only ever increases. It is appended to the character
tags, so by minute 17 the audience has watched VIRO be ground down without a word being
said about it. This is the cheapest way to photograph a price, and prices are how an
audience infers desire.
"""
import collections, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "scripts"))
from scene_templates import expand as ex   # noqa: E402

OUT = os.path.join(HERE, "episode01.json")
Q = "masterpiece, best quality, very aesthetic, absurdres"
MALE = "male focus, mature male, masculine"

BASE = {
    "VIRO": "1boy, solo, long dark brown curly hair, ponytail, brown eyes, gold ear stud, "
            "teal soccer jersey, orange trim, number 7",
    "RASK": "1boy, solo, dark red hair, undercut, yellow eyes, scar on eyebrow, "
            "black soccer jersey, silver trim, number 9",
}
# only ever worsens. index into this list is the `wear` level.
WEAR = ["clean uniform, neat hair",
        "sweaty, damp hair, flushed",
        "sweaty, dirt on uniform, messy hair, breathing hard",
        "torn uniform, dirt and grass stains, exhausted, dishevelled",
        "torn bloodied uniform, cut on face, utterly exhausted, trembling"]

# kind -> (template, gets a reaction shot?)
KINDS = {"est": ("establish", False), "master": ("master", False),
         "say": ("speak", True), "think": ("speak", False), "beat": ("react", False),
         "pillow": ("pillow", False), "insert": ("insert", False),
         "build": ("build", False), "sakuga": ("sakuga", False),
         "silent": ("hold_silent", False)}

# ── the episode ───────────────────────────────────────────────────────────────
# (scene id, wear, location tags, [ (kind, subject, text-or-visual) ... ])
# subject is a character name, or a visual description for non-character shots.
SCENES = [
 ("00_cold", 1, "night stadium, empty stands, confetti, rain, cold lighting", [
   ("est", "empty stadium stand, confetti falling, night, wide shot, melancholy", ""),
   ("insert", "referee whistle, close-up, blowing", ""),
   ("beat", "VIRO", "kneeling on grass, head down, defeated, wide shot, small in frame"),
   ("insert", "black soccer boots walking past, low angle, ground level, not stopping", ""),
   ("insert", "hand-painted number 7 sign left on an empty seat, close-up", ""),
   ("say", "VIRO", "...Again."),
   ("pillow", "confetti settling on wet grass, close-up, night, still", ""),
 ]),
 ("01_title", 0, "empty stadium at dawn, mist, golden light", [
   ("est", "empty soccer stadium at dawn, mist, golden light, wide shot, scenery", ""),
   ("pillow", "goal net at dawn, dew, close-up, still, peaceful", ""),
 ]),
 ("02_tunnel", 0, "stadium tunnel, concrete, harsh overhead light", [
   ("est", "stadium tunnel interior, concrete walls, harsh lighting, empty, wide shot", ""),
   ("insert", "hands taping a wrist, close-up, macro, careful", ""),
   ("beat", "VIRO", "sitting alone, taping wrist, quiet, close-up, thoughtful"),
   ("pillow", "crowd noise outside, closed door, light under it, close-up", ""),
 ]),
 ("03_locker", 0, "locker room interior, benches, jerseys hanging, fluorescent light", [
   ("est", "soccer locker room interior, benches, hanging jerseys, wide shot", ""),
   ("say", "MANAGER", "Nine years. Nine years we have come here and gone home quiet."),
   ("beat", "VIRO", "listening, jaw tight, close-up, not looking up"),
   ("say", "VIRO", "I know what the record is."),
   ("say", "MANAGER", "Then stop trying to beat him. Beat the team."),
   ("beat", "VIRO", "close-up, eyes down, the words landing badly, silent"),
   ("think", "VIRO", "He does not understand. It was never about the team."),
 ]),
 ("04_rask", 0, "opposite tunnel, dim concrete, single light", [
   ("est", "dim stadium tunnel, single overhead light, empty, wide shot", ""),
   ("beat", "RASK", "alone, taping own ankle, calm, no expression, close-up"),
   ("say", "RASK", "He will come at me early. He always does."),
   ("beat", "RASK", "looking at nothing, bored expression, close-up, cold"),
 ]),
 ("05_walkout", 0, "tunnel mouth, floodlights blazing beyond, crowd roar", [
   ("est", "tunnel mouth, blinding floodlights beyond, silhouettes, wide shot", ""),
   ("master", "two teams walking out onto pitch, wide shot, floodlights, crowd", ""),
   ("insert", "boy in front row holding hand-painted number 7 sign, close-up, hopeful", ""),
   ("beat", "VIRO", "seeing the boy, small flicker of a smile, close-up"),
   ("pillow", "floodlight tower warming up against black sky, low angle", ""),
 ]),
 ("06_kickoff", 1, "night pitch, floodlights, packed stadium", [
   ("master", "kick off, two teams on pitch, wide shot, night stadium, floodlights", ""),
   ("build", "VIRO", "running with soccer ball, driving forward, determined, from side"),
   ("insert", "soccer ball taken away, boot intercepting, close-up, low angle", ""),
   ("beat", "RASK", "unbothered, already turning away, close-up"),
   ("beat", "VIRO", "frustrated, hands on hips, wide shot, small in frame"),
 ]),
 ("07_goal", 1, "night pitch, floodlights, penalty area", [
   ("master", "soccer attack developing, players in penalty area, wide shot", ""),
   ("insert", "soccer ball crossing the goal line, net, close-up, undramatic", ""),
   ("beat", "RASK", "scoring, no celebration, walking back, close-up, flat expression"),
   ("beat", "VIRO", "standing still, distant, small in frame, wide shot, stunned"),
   ("pillow", "scoreboard glow reflected in a puddle on the grass, close-up", ""),
 ]),
 ("08_futile", 2, "night pitch, floodlights, midfield", [
   ("build", "VIRO", "attacking, running with soccer ball, from side, determined"),
   ("insert", "tackled, ball lost, boots and grass, close-up, low angle", ""),
   ("build", "VIRO", "attacking again, sprinting, gritted teeth, from front"),
   ("insert", "blocked, body between him and ball, close-up", ""),
   ("beat", "VIRO", "hands on knees, breathing hard, close-up, exhausted"),
   ("think", "VIRO", "Nine years. And he has not even looked at me."),
 ]),
 ("09_card", 2, "night pitch, floodlights, midfield", [
   ("build", "VIRO", "rash sliding tackle, reckless, low angle, ground level"),
   ("insert", "yellow card raised against black sky, close-up, low angle", ""),
   ("beat", "VIRO", "on the ground, looking up, realising, close-up"),
   ("say", "RASK", "You are playing me. Play the game."),
   ("beat", "VIRO", "looking up at him, confused, hurt, close-up, from below"),
   ("beat", "RASK", "already walking away, back to viewer, wide shot"),
   ("think", "VIRO", "Even now. Even now he is trying to help me."),
 ]),
 ("10_low", 3, "night pitch, edge of penalty box, crowd blurred", [
   ("beat", "VIRO", "standing alone, edge of box, exhausted, wide shot, small in frame"),
   ("pillow", "empty seat in the front row, hand-painted sign gone, close-up", ""),
   ("beat", "VIRO", "seeing the empty seat, face falling, close-up"),
   ("silent", "VIRO", "standing completely still, crowd blurred behind, close-up, silence"),
   ("pillow", "stadium clock reading 88:00, glowing, close-up, dark", ""),
 ]),
 ("11_decide", 3, "night pitch, floodlights", [
   ("insert", "soccer ball rolling past his feet untouched, close-up, low angle", ""),
   ("beat", "VIRO", "letting it go, something settling in his face, close-up"),
   ("think", "VIRO", "Beat the team."),
   ("beat", "VIRO", "lifting his head, eyes changed, close-up, resolved"),
 ]),
 ("12_lastmin", 3, "night pitch, floodlights, fast play", [
   ("master", "quick passing move, several players, wide shot, night pitch", ""),
   ("build", "VIRO", "one touch pass, head up, calm, from side"),
   ("beat", "RASK", "reading him, finding nothing, slight frown, close-up"),
   ("build", "VIRO", "moving into space, running, controlled, from front"),
   ("insert", "teammate boots passing the ball, close-up, low angle, quick", ""),
 ]),
 ("13_sakuga", 4, "night pitch, floodlights, penalty area, explosive", [
   ("sakuga", "VIRO", "sprinting at full speed, motion lines, dynamic angle, from below"),
   ("sakuga", "soccer ball struck hard, deforming, impact, speed lines, close-up", ""),
   ("sakuga", "RASK", "turning to chase, desperate, dynamic angle, from side"),
   ("sakuga", "turf tearing up, boots, ground level, explosive, close-up", ""),
   ("sakuga", "VIRO", "breaking past the last defender, full body, from below, powerful"),
 ]),
 ("14_silence", 4, "night pitch, penalty area, everything still", [
   ("silent", "VIRO", "alone with the soccer ball, completely still, wide shot, silence"),
   ("insert", "leg drawing back to strike, extreme low angle, tense, close-up", ""),
 ]),
 ("15_goal", 4, "night pitch, goal, explosive", [
   ("insert", "boot striking soccer ball, moment of contact, white flash, close-up", ""),
   ("insert", "soccer ball in the goal net, mesh bulging, from behind goal, close-up", ""),
   ("beat", "boy in the front row standing alone, arms raised, close-up, crowd seated", ""),
   ("beat", "RASK", "watching, something finally showing in his face, close-up"),
   ("beat", "VIRO", "on his knees, exhausted, not celebrating, wide shot"),
 ]),
 ("16_tag", 4, "night pitch, after full time, emptying stadium", [
   ("est", "stadium after full time, players walking off, wide shot, night", ""),
   ("say", "RASK", "You still have not beaten me."),
   ("say", "VIRO", "I know. But you did not beat me either."),
   ("beat", "RASK", "half smiling, offering a handshake, close-up"),
   ("say", "RASK", "...Next year, then."),
   ("beat", "VIRO", "saying nothing, close-up, knowing there is no next year"),
   ("pillow", "hand-painted number 7 sign left on an empty seat, wide shot, night", ""),
   ("pillow", "empty stadium, floodlights going out one by one, wide shot", ""),
 ]),
]

# ── dialogue expansion ────────────────────────────────────────────────────────
# The first assembly came out at 4.4 minutes with 14% of beats saying anything - the exact
# failure the vertical short had. Coverage alone does not fill an episode; DIALOGUE does,
# and dialogue is where want gets expressed.
#
# Rules these lines follow:
#   * Nobody announces that they want to win. They talk about the PRICE of wanting it.
#   * VIRO's interior monologue contradicts his face rather than narrating it.
#   * RASK is never cruel. He is correct, which is worse.
EXTRA = {
 "02_tunnel": [
   ("think", "VIRO", "Same tunnel. Same smell of wet concrete. Nine times now."),
   ("think", "VIRO", "The first year I thought I was unlucky."),
   ("beat", "VIRO", "staring at the floor, still, close-up"),
   ("think", "VIRO", "By the fourth I stopped saying that out loud."),
   ("insert", "boots being laced tight, very tight, close-up, macro, hands shaking", ""),
   ("think", "VIRO", "My hands did not used to do that."),
 ],
 "03_locker": [
   ("say", "MANAGER", "You have got one game left in this shirt. One."),
   ("beat", "VIRO", "close-up, listening, jaw working"),
   ("say", "MANAGER", "And I have watched you play that man nine times."),
   ("say", "MANAGER", "Nine times I have watched a brilliant footballer become a small one."),
   ("beat", "VIRO", "close-up, stung, eyes down"),
   ("say", "VIRO", "You think I do not know that?"),
   ("say", "MANAGER", "I think you know it. I do not think you believe it."),
   ("beat", "VIRO", "close-up, silent, jaw tight"),
   ("say", "VIRO", "He has never even spoken to me. Nine years."),
   ("say", "VIRO", "Not a word. Not once."),
   ("say", "MANAGER", "Because you are not his problem, son. He is yours."),
   ("beat", "VIRO", "close-up, that landing hard, blinking"),
   ("think", "VIRO", "I would give the whole career back for one of these."),
   ("think", "VIRO", "Every goal. Every cap. All of it, for ninety minutes."),
 ],
 "04_rask": [
   ("say", "RASK", "Do not double up on him."),
   ("beat", "RASK", "taping ankle, not looking up, close-up"),
   ("say", "RASK", "He wants the contact. Give him nothing to push against."),
   ("say", "RASK", "He beats himself. He always has."),
   ("beat", "RASK", "close-up, flat, entirely without malice"),
 ],
 "06_kickoff": [
   ("think", "VIRO", "There. Straight at him. Like always."),
   ("beat", "VIRO", "close-up, breathing hard already"),
   ("think", "VIRO", "Eight minutes gone and I have not looked up once."),
 ],
 "07_goal": [
   ("think", "VIRO", "Of course."),
   ("beat", "VIRO", "close-up, hollow, eyes wide"),
   ("think", "VIRO", "He did not even look pleased."),
   ("think", "VIRO", "That is the part nobody understands. It costs him nothing."),
   ("beat", "RASK", "walking back to halfway, expressionless, wide shot"),
 ],
 "08_futile": [
   ("think", "VIRO", "Again."),
   ("build", "VIRO", "attacking a third time, ragged, desperate, from side"),
   ("insert", "dispossessed again, ball rolling clear, close-up, ground level", ""),
   ("think", "VIRO", "Again."),
   ("beat", "VIRO", "close-up, chest heaving, hair stuck to face"),
   ("think", "VIRO", "My legs have gone. Sixty minutes and my legs have gone."),
   ("think", "VIRO", "He has not broken stride once."),
 ],
 "09_card": [
   ("say", "VIRO", "Say something. Nine years and you have never said one word to me."),
   ("beat", "RASK", "stopping, turning back, close-up, considering him"),
   ("say", "RASK", "What would you like me to say?"),
   ("say", "VIRO", "Anything. Tell me I am not good enough. Tell me something."),
   ("beat", "RASK", "close-up, looking at him properly for the first time"),
   ("say", "RASK", "You are the best player on this pitch."),
   ("beat", "VIRO", "close-up, completely thrown, mouth slightly open"),
   ("say", "RASK", "You have been the best player on this pitch for nine years."),
   ("say", "RASK", "And you have spent all nine of them watching me instead of playing."),
   ("beat", "VIRO", "close-up, devastated, the truth arriving"),
 ],
 "10_low": [
   ("think", "VIRO", "He is right."),
   ("beat", "VIRO", "close-up, empty, staring at nothing"),
   ("think", "VIRO", "Nine years of my life, and he is right."),
   ("think", "VIRO", "The boy has gone home. He did not even wait for the end."),
   ("beat", "VIRO", "close-up, looking at the empty seat, breaking"),
   ("think", "VIRO", "I do not blame him. I would not have waited either."),
 ],
 "11_decide": [
   ("think", "VIRO", "So stop."),
   ("beat", "VIRO", "close-up, breathing slowing, something clearing"),
   ("think", "VIRO", "Stop wanting to beat him."),
   ("think", "VIRO", "Just play. One more time. Just play."),
 ],
 "12_lastmin": [
   ("think", "VIRO", "Head up. Where is everyone."),
   ("beat", "VIRO", "close-up, calm, eyes scanning"),
   ("think", "VIRO", "There. And there. They have been there the whole time."),
   ("beat", "RASK", "close-up, frowning slightly, losing him"),
   ("think", "VIRO", "He cannot read me because I am not looking at him."),
 ],
 "16_tag": [
   ("say", "VIRO", "Nine years."),
   ("say", "RASK", "Nine years."),
   ("beat", "VIRO", "close-up, exhausted, almost smiling"),
   ("say", "VIRO", "You could have told me that in the first one."),
   ("say", "RASK", "You would not have heard it in the first one."),
   ("beat", "VIRO", "close-up, conceding that, nodding slowly"),
 ],
}
for _sid, _shots in EXTRA.items():
    for _s in SCENES:
        if _s[0] == _sid:
            _s[3].extend(_shots)
            break


B = []
wear_seen = 0
for sid, wear, loc, shots in SCENES:
    wear_seen = max(wear_seen, wear)          # damage never heals
    for si, (kind, subj, text) in enumerate(shots):
        tmpl, needs_react = KINDS[kind]
        bid = f"{sid}_{si:02d}"
        who = subj if subj in BASE else None
        if who:
            tags = f"{BASE[who]}, {MALE}, {WEAR[wear_seen]}, {text or 'close-up'}, {loc}, {Q}"
        else:
            tags = f"{subj}, {loc}, {Q}"
        d = collections.OrderedDict(id=bid, template=tmpl, clip_secs=6)
        if who:
            d["ref"] = [who]
        d["tags"] = tags
        d["prompt"] = tags
        d["motion"] = "Slow deliberate camera move. Subtle natural movement only."
        if kind == "say" and text:
            d["line"] = {"who": subj, "text": text}
        if kind == "think" and text:
            # voiced interior monologue only. Setting a caption too printed the same line
            # twice, stacked on top of itself.
            d["line"] = {"who": subj, "text": text}
        B.append(d)
        # the reaction shot, automatic so it cannot be forgotten
        if needs_react and text:
            other = "RASK" if subj == "VIRO" else "VIRO"
            if subj in ("VIRO", "RASK"):
                B.append(collections.OrderedDict(
                    id=f"{bid}r", template="react", clip_secs=6, ref=[other],
                    tags=f"{BASE[other]}, {MALE}, {WEAR[wear_seen]}, listening, "
                         f"close-up, reaction, {loc}, {Q}",
                    prompt="", motion="Almost still. Only the eyes and breath move."))

for b in B:
    b.setdefault("prompt", b["tags"])

film = collections.OrderedDict(
    title="THE DERBY EP1", fps=24, engine="higgs_v3",
    # a TV anime episode is widescreen. short.py defaults to 9:16 for the vertical
    # short format, which is simply the wrong form for this.
    canvas=[1920, 1080],
    keyframe_engine="anime", anime_ckpt="animagine-xl-4.0.safetensors",
    ipadapter_weight=0.6,
    style_lora="qwen_image_2512_storybook_anime_lora.safetensors", style_strength=1.0,
    style="modern sports anime, cel shading, cinematic",
    sheets={"RASK": "sheet_rask.png", "VIRO": "sheet_viro.png"},
    anime_sheets={"RASK": "sheet_anime_rask.png", "VIRO": "sheet_anime_viro.png"},
    characters={"RASK": "the red-haired striker", "VIRO": "the curly-haired playmaker"},
    voices={
        "VIRO": {"engine": "higgs_v3", "voice": "voices_examples/higgs_audio/vex.wav"},
        "RASK": {"engine": "higgs_v3", "voice": "voices_examples/male/male_01.wav"},
        "MANAGER": {"engine": "indextts2", "voice": "voices_examples/male/male_01.wav",
                    "emotion": {"Angry": 0.3}},
    },
    music=[
        {"at": 0, "prefix": "ep_cold", "bpm": 70, "key": "A minor", "seconds": 95,
         "level": 0.8, "tags": "sparse melancholy piano, single sustained cello, empty "
         "stadium, defeat, restrained, instrumental"},
        {"at": 120, "prefix": "ep_act1", "bpm": 92, "key": "D minor", "seconds": 240,
         "level": 0.7, "tags": "quiet tense strings, low pulse, anticipation before a "
         "match, restrained orchestral, instrumental"},
        {"at": 700, "prefix": "ep_low", "bpm": 62, "key": "C minor", "seconds": 150,
         "level": 0.75, "tags": "desolate solo piano, distant strings, loss, very sparse, "
         "instrumental"},
        {"at": 950, "prefix": "ep_climax", "bpm": 158, "key": "F minor", "seconds": 180,
         "level": 1.0, "tags": "soaring orchestral build, taiko drums, brass, choir, "
         "triumphant desperate, huge, instrumental"},
    ],
    beats=B,
)
json.dump(film, open(OUT, "w", encoding="utf-8"), indent=2, ensure_ascii=False)

shots = secs = 0
for b in B:
    cuts, imp = ex(b, float(b["clip_secs"]))
    shots += len(cuts) + (1 if imp else 0)
    secs += sum(c["len"] for c in cuts) + (0.083 if imp else 0)
lines = sum(1 for b in B if b.get("line"))
print(f"wrote {OUT}")
print(f"  scenes {len(SCENES)}   beats {len(B)}   shots {shots}")
print(f"  runtime ~{secs/60:.1f} min      spoken lines {lines}")
print(f"  beats that say something: {lines/len(B)*100:.0f}%  (the short managed 14%)")
print(f"  generations: {len(B)} keyframes + {len(B)} clips")
