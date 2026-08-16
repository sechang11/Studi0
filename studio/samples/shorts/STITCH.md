# Hook transitions: open on an existing clip, whip into one of these

Two different things both get called a "hook", and you have both.

## 1. The six hook-* films in `hook/`

These are complete films that open on their own hook. The grammar of a stitch without
anybody else's footage in them - a cold first line, a hard turn, a payoff. Post them
as they are.

## 2. Putting a clip you already have in FRONT of any of these

That is `stitch_hook.py`, and it needs one thing this folder cannot contain: the lead
clip. It has to be footage you have the right to use - your own, licensed, or public
domain. The tool does not ship any and will not go looking. The reusable part of
somebody else's video is its grammar, not its frames.

    cd ~/shared/comfy-studio
    python3 studio/_tools/stitch_hook.py --lead /path/to/your_clip.mp4 \
        --into films/shorts/ad-atlas-pack.json

Useful flags:

    --seconds 2.5        how much of the lead to use (default 2.0)
    --from-seconds 4     start that far into the lead, to skip a slate or a slow start
    --transition whip_pan   or dip_black, flash, cross, slide_l, slide_r, hard
    --out /path/out.mp4  default lands in studio/samples/shorts/stitched/

What it does for you, each one a thing that goes wrong by hand:

- **format match** - the lead is cropped and scaled to the film's canvas, so a landscape
  clip does not letterbox into a different shape than the piece it introduces
- **level match** - the lead is measured and normalised to the film's own loudness,
  two-pass. Single-pass loudnorm works blind and measured 7 LU off on this machine.
  Verified: a -19.7 LUFS lead joined a -9.8 LUFS film and came out at -10.0
- **one transition language** - the join uses the same transition cards the cutter uses
  inside a film, so a stitch and a cut are the same vocabulary
- **it re-measures the result** and tells you if the audio does not cover the picture

Tested end to end on our own deck3 clip into the ATLAS commercial: 13.2s, 1080x1920,
-10.0 LUFS.
