#!/usr/bin/env python3
"""Scene templates - reusable edit patterns lifted from measured reference videos.

A template turns ONE generated clip into a shaped run of micro-shots. Instead of hand
writing a `cuts` array, a beat says:

    { "id": "030_clash", "template": "clash", "intensity": 1.2, ... }

and the expander produces the cuts, the effects and the impact frames.

WHERE THESE COME FROM

Every pattern below was derived by measuring a real short frame by frame, not invented:

    median shot          0.30s      (64% of shots under 1s)
    mean motion          5.87       (a 20-min film built the old way scored 2.25)
    frames near-empty    ~25% inside a burst - abstract colour flashes between hits
    loudness            -9.4 LUFS, LRA 2.8

The single most important finding: the apparent motion is mostly EDITING and COMPOSITING,
not video generation. The characters hold simple poses; the frame around them does the
work. So these templates spend their effort on cut rhythm, punch, glow and flash frames.

ADDING A TEMPLATE

When you find a pattern in a reference you like:
  1. Measure it - `scripts/analyze_shots.py` for motion, scene detection for shot lengths.
  2. Sample consecutive frames ~0.13s apart through the pattern and LOOK at it. That is
     how the flash frames were found; they are invisible at normal speed.
  3. Add an entry here with the measurements in the docstring, so the next person knows
     what evidence it rests on.
"""

# Each template returns (cuts, impact). `cuts` entries are {at, len, fx}.
# `at` is a fraction of the source clip's length so a template works on any clip_secs.


def _scale(cuts, intensity):
    """intensity <1 slower and calmer, >1 faster and harder."""
    out = []
    for c in cuts:
        out.append({"at": c["at"], "len": max(0.06, c["len"] / max(intensity, 0.2)),
                    "fx": list(c["fx"])})
    return out


# ── HOOK ──────────────────────────────────────────────────────────────────────
# The opening. The reference holds its first image longer than anything else in the piece
# - it is the only shot allowed to breathe, because it has to stop a thumb mid-scroll.
def hook(intensity=1.0):
    return _scale([
        {"at": 0.05, "len": 1.60, "fx": ["punch", "hot"]},
        {"at": 0.55, "len": 0.90, "fx": ["hot"]},
    ], intensity), False


# ── TAUNT ─────────────────────────────────────────────────────────────────────
# Character close-up carrying one line. Long enough to read a caption (~1.2-1.8s), with a
# slow punch so it never sits still. This is the pattern that carries all the dialogue.
def taunt(intensity=1.0):
    return _scale([
        {"at": 0.10, "len": 1.30, "fx": ["punch", "hot"]},
        {"at": 0.70, "len": 0.55, "fx": ["aberr"]},
    ], intensity), False


# ── CLASH ─────────────────────────────────────────────────────────────────────
# The core burst: 5-7 shots between 0.10 and 0.30s with shake and aberration, ending on a
# flash. This is where the reference's 0.30s median and 5.87 motion actually come from.
def clash(intensity=1.0):
    return _scale([
        {"at": 0.05, "len": 0.26, "fx": ["punch", "hot"]},
        {"at": 0.30, "len": 0.14, "fx": ["shake", "aberr"]},
        {"at": 0.45, "len": 0.11, "fx": ["shake"]},
        {"at": 0.58, "len": 0.22, "fx": ["punch", "aberr", "hot"]},
        {"at": 0.74, "len": 0.10, "fx": ["shake"]},
        {"at": 0.86, "len": 0.30, "fx": ["glow", "hot"]},
    ], intensity), True


# ── CHARGE ────────────────────────────────────────────────────────────────────
# Accelerating cuts - each shorter than the last. Rhythm alone creates rising tension, and
# it costs nothing because it is one source clip sliced unevenly.
def charge(intensity=1.0):
    return _scale([
        {"at": 0.02, "len": 0.55, "fx": ["punch"]},
        {"at": 0.30, "len": 0.38, "fx": ["punch", "hot"]},
        {"at": 0.52, "len": 0.26, "fx": ["shake"]},
        {"at": 0.68, "len": 0.18, "fx": ["shake", "aberr"]},
        {"at": 0.80, "len": 0.12, "fx": ["shake", "aberr", "hot"]},
    ], intensity), True


# ── IMPACT ────────────────────────────────────────────────────────────────────
# One hit. Wind-up, contact, flash, then a held reaction so the blow lands emotionally.
def impact(intensity=1.0):
    return _scale([
        {"at": 0.10, "len": 0.20, "fx": ["punch"]},
        {"at": 0.40, "len": 0.09, "fx": ["shake", "aberr", "flash"]},
        {"at": 0.62, "len": 0.75, "fx": ["glow", "hot"]},
    ], intensity), True


# ── REVEAL ────────────────────────────────────────────────────────────────────
# A power-up or transformation: slow build with glow, then a flash into the new state.
def reveal(intensity=1.0):
    return _scale([
        {"at": 0.05, "len": 0.95, "fx": ["punch", "glow"]},
        {"at": 0.50, "len": 0.45, "fx": ["glow", "hot"]},
        {"at": 0.78, "len": 0.16, "fx": ["flash", "aberr"]},
    ], intensity), True


# ── FINISHER ──────────────────────────────────────────────────────────────────
# The last beat. Longest hold in the piece, maximum glow, then out. The reference lets its
# final image run several times its median so the ending registers.
def finisher(intensity=1.0):
    return _scale([
        {"at": 0.05, "len": 0.30, "fx": ["shake", "aberr"]},
        {"at": 0.25, "len": 0.12, "fx": ["flash"]},
        {"at": 0.45, "len": 1.90, "fx": ["glow", "punch", "hot"]},
    ], intensity), False


# ── AFTERMATH ─────────────────────────────────────────────────────────────────
# The one place a short is allowed to be still: a beat of quiet after the finisher. Use at
# most once. In a 50-second piece this is the contrast that makes the rest feel fast.
def aftermath(intensity=1.0):
    return _scale([
        {"at": 0.10, "len": 1.40, "fx": ["punch"]},
    ], intensity), False


TEMPLATES = {
    "hook": hook, "taunt": taunt, "clash": clash, "charge": charge,
    "impact": impact, "reveal": reveal, "finisher": finisher, "aftermath": aftermath,
}


def expand(beat, clip_secs):
    """Turn a beat's `template` into concrete cuts. Explicit `cuts` always win."""
    if beat.get("cuts"):
        return beat["cuts"], beat.get("impact", False)
    name = beat.get("template", "taunt")
    if name not in TEMPLATES:
        raise SystemExit(f"{beat['id']}: unknown template {name!r} "
                         f"(have: {', '.join(sorted(TEMPLATES))})")
    cuts, imp = TEMPLATES[name](float(beat.get("intensity", 1.0)))
    out = []
    for c in cuts:
        at = c["at"] * clip_secs
        if at + c["len"] > clip_secs:
            at = max(0.0, clip_secs - c["len"])
        out.append({"at": round(at, 3), "len": round(c["len"], 3), "fx": c["fx"]})
    return out, beat.get("impact", imp)


def summarise():
    print(f"{'template':12} {'shots':>6} {'secs':>7}  effects used")
    for name, fn in sorted(TEMPLATES.items()):
        cuts, imp = fn(1.0)
        fx = sorted({f for c in cuts for f in c["fx"]})
        print(f"{name:12} {len(cuts):6} {sum(c['len'] for c in cuts):7.2f}  "
              f"{','.join(fx)}{'  +impact' if imp else ''}")


if __name__ == "__main__":
    summarise()


# ══════════════════════════════════════════════════════════════════════════════
# ARCS - whole-piece rhythm, measured from a reference
# ══════════════════════════════════════════════════════════════════════════════
# A template shapes one beat. An ARC shapes the whole short: where the bursts go and
# where the breathers go. Uniform speed reads as monotonous however fast it is; the
# reference escalates in waves.
#
# Measured from a 52s vertical short, cuts detected at a tight threshold:
#   182 shots, median 0.10s, 87% under 0.5s
#   cut density per 5s block: 9, 10, 6, 25, 14, 27, 26, 22, 8, 33, 2
#
# Read that as: build, BURST, breathe, sustained assault, breathe, FINAL BURST, resolve.
# The breathers are what make the bursts land - a 33-cut block only reads as violent
# because an 8-cut block preceded it.

SPORTS_CLASH_50S = [
    # (block, template, intensity)   -- durations fall out of the templates
    # Targets are the reference's measured cuts-per-5s. Do not chase them by raising
    # intensity: `clash` at 1.0 is ALREADY 0.19s/shot, which is burst density. Density
    # comes from beat COUNT. Intensity above ~1.3 makes shots too short to read.
    ("setup",   "hook",      0.80),   # 0-15s, target 25 cuts
    ("setup",   "taunt",     0.70),
    ("setup",   "taunt",     0.70),
    ("setup",   "charge",    0.60),
    ("setup",   "taunt",     0.80),
    ("setup",   "clash",     0.65),   # flash-forward: tease the fight before it starts
    ("setup",   "impact",    0.75),
    ("setup",   "reveal",    0.80),
    ("burst1",  "charge",    1.00),   # 15-20s, target 25
    ("burst1",  "clash",     1.00),
    ("burst1",  "clash",     1.10),
    ("burst1",  "clash",     1.00),
    ("breathe", "taunt",     0.80),   # 20-25s, target 14
    ("breathe", "clash",     1.20),
    ("breathe", "taunt",     1.00),
    ("assault", "clash",     1.00),   # 25-40s, target 75
    ("assault", "impact",    1.00),
    ("assault", "clash",     1.10),
    ("assault", "charge",    1.10),
    ("assault", "clash",     1.00),
    ("assault", "impact",    1.10),
    ("assault", "clash",     1.10),
    ("assault", "clash",     1.00),
    ("assault", "charge",    1.00),
    ("assault", "clash",     1.10),
    ("assault", "impact",    1.00),
    ("breathe", "taunt",     0.60),   # 40-45s, target 8
    ("breathe", "taunt",     0.70),
    ("final",   "charge",    1.30),   # 45-50s, target 33
    ("final",   "clash",     1.20),
    ("final",   "clash",     1.20),
    ("final",   "charge",    1.20),
    ("final",   "clash",     1.10),
    ("resolve", "finisher",  1.30),   # 50-55s, target 2 - longest hold in the piece
    ("resolve", "aftermath", 0.60),
]

# Measured cuts per 5s block in the reference, for arc_summary to check against.
REF_BLOCKS = [9, 10, 6, 25, 14, 27, 26, 22, 8, 33, 2]


def arc_summary(arc=SPORTS_CLASH_50S, verbose=True):
    """What an arc will actually produce, before you spend GPU on it."""
    lens, t, rows = [], 0.0, []
    for block, tmpl, inten in arc:
        cuts, imp = TEMPLATES[tmpl](inten)
        ls = [c["len"] for c in cuts] + ([0.083] if imp else [])
        rows.append((block, tmpl, inten, len(ls), sum(ls), t))
        lens += ls
        t += sum(ls)

    if verbose:
        print(f"{'block':9} {'tmpl':10} {'int':>5} {'shots':>6} {'secs':>7} {'at':>7}")
        for r in rows:
            print(f"{r[0]:9} {r[1]:10} {r[2]:5.2f} {r[3]:6} {r[4]:7.2f} {r[5]:7.1f}")

    blocks, at = [0] * (int(t // 5) + 1), 0.0
    for L in lens:
        blocks[min(int(at // 5), len(blocks) - 1)] += 1
        at += L
    lens.sort()
    print(f"\n{'':10}{'ours':>10}   reference")
    print(f"{'shots':10}{len(lens):>10}   182")
    print(f"{'runtime':10}{t:>9.1f}s   51.8s")
    print(f"{'median':10}{lens[len(lens)//2]:>9.2f}s   0.10s")
    print(f"{'<0.5s':10}{sum(1 for L in lens if L<0.5)/len(lens)*100:>9.0f}%   87%")
    print("\ncuts per 5s block")
    print("  ours " + " ".join(f"{b:3}" for b in blocks))
    print("  ref  " + " ".join(f"{b:3}" for b in REF_BLOCKS))
    return t


# ══════════════════════════════════════════════════════════════════════════════
# EPISODE TEMPLATES - the opposite grammar to the ones above
# ══════════════════════════════════════════════════════════════════════════════
# The templates above serve a 60-second vertical short: one clip becomes 6-10 micro-shots
# and the energy comes from cutting. An anime EPISODE is the reverse. Shots are held, the
# camera moves slowly inside them, and the tension comes from what is withheld.
#
# The trap is the 20-minute film that got rejected: held shots with a slow zoom and nothing
# happening, mean motion 2.25. The lesson was NOT "never hold". Real anime is mostly held
# drawings with camera moves - limited animation is the form. The lesson is that a hold must
# be MOTIVATED: it lands a line, it shows a decision being made, it withholds an answer.
# A hold with nothing to hold on to is dead air, and the audience feels the difference.
#
# So every template here is named for the dramatic job it does, not for its length.


def establish(intensity=1.0):
    """Where we are. Slow push, long enough to read the space. Once per scene, never twice."""
    return _scale([{"at": 0.02, "len": 4.20, "fx": ["punch"]}], intensity), False


def master(intensity=1.0):
    """The wide that holds the geography of a scene so cuts inside it stay legible."""
    return _scale([{"at": 0.05, "len": 3.60, "fx": []}], intensity), False


def speak(intensity=1.0):
    """A character delivering a line. Held for the line plus a beat of silence after it.

    The silence is the point. Cutting on the last syllable is the single most common way
    an AI edit betrays itself - real dialogue scenes breathe after a line.
    """
    return _scale([{"at": 0.05, "len": 3.20, "fx": ["punch"]}], intensity), False


def react(intensity=1.0):
    """No dialogue. A face receiving what was just said. This is where an episode earns
    its emotion, and it is exactly what the rejected 20-minute film had none of."""
    return _scale([{"at": 0.10, "len": 2.60, "fx": []}], intensity), False


def pillow(intensity=1.0):
    """The cutaway with no people in it - sky, a flag, an empty seat. Ozu's device, and
    anime uses it constantly to mark a passage of time or let a moment settle."""
    return _scale([{"at": 0.05, "len": 3.00, "fx": ["punch"]}], intensity), False


def insert(intensity=1.0):
    """A detail the audience must notice: a hand tightening, a clock, a ball on the spot."""
    return _scale([{"at": 0.10, "len": 1.80, "fx": ["punch"]}], intensity), False


def build(intensity=1.0):
    """Rising tension. Shots shorten but stay readable - nothing under half a second."""
    return _scale([
        {"at": 0.05, "len": 1.40, "fx": ["punch"]},
        {"at": 0.40, "len": 1.00, "fx": ["hot"]},
        {"at": 0.70, "len": 0.70, "fx": ["punch", "hot"]},
    ], intensity), False


def sakuga(intensity=1.0):
    """THE money sequence. An episode gets one or two - that is what makes them land.

    Named for the anime term: the brief stretch where the animation budget is spent. If
    everything is sakuga, nothing is.
    """
    return _scale([
        {"at": 0.02, "len": 0.50, "fx": ["punch", "hot"]},
        {"at": 0.22, "len": 0.30, "fx": ["shake", "aberr"]},
        {"at": 0.40, "len": 0.22, "fx": ["shake"]},
        {"at": 0.55, "len": 0.34, "fx": ["punch", "aberr", "hot"]},
        {"at": 0.75, "len": 0.60, "fx": ["glow", "hot"]},
    ], intensity), True


def hold_silent(intensity=1.0):
    """The pause before the climax. Longest shot in the episode, no score, no dialogue.
    Silence immediately before an impact makes the impact twice as loud."""
    return _scale([{"at": 0.05, "len": 5.50, "fx": []}], intensity), False


TEMPLATES.update({
    "establish": establish, "master": master, "speak": speak, "react": react,
    "pillow": pillow, "insert": insert, "build": build, "sakuga": sakuga,
    "hold_silent": hold_silent,
})
