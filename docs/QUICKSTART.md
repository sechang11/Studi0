# Running the studio

Everything runs on the machine the models live on. Nothing needs to be installed on
your laptop — you drive it from a browser.

## Start it

    cd ~/shared/comfy-studio
    bash scripts/boot-services.sh

That starts both services and only reports what it has actually verified:

    comfyui UP after 1s
    studio UP after 2s

It is idempotent — run it any time; anything already listening is left alone.

## Open it

| what | where |
|---|---|
| **Direct a scene** (the step-by-step wizard) | http://THIS-BOX:8777/wizard |
| Browse the library and capability cards | http://THIS-BOX:8777/ |
| ComfyUI itself | http://THIS-BOX:8188 |

Find `THIS-BOX` with `hostname -I | awk '{print $1}'`. Both services bind `0.0.0.0`,
so any machine on the LAN can reach them. To keep it local only:
`STUDIO_BIND=127.0.0.1 python3 studio/serve.py`.

## Make a film

1. Open `/wizard` and walk the six steps: format, look and pace, place and time, cast,
   shots, review. Each choice is labelled with **where it takes effect** — deterministic
   post-processing, a graph parameter, a prompt tag, or not implemented.
2. Press **Save**. It writes `studio/movies/<name>.movie`.
3. Compile and render:

        python3 studio/compile.py studio/movies/<name>.movie --timeline
        python3 scripts/short.py  studio/movies/<name>.json

The finished film lands in
`~/ComfyUI/output/claude-generated/12-shorts/<title-slug>/<title-slug>.mp4`.

Roughly 30s of GPU per beat: a 12-beat scene is about 8 minutes.

## Render one stage at a time

`short.py` takes `--stage keyframes | clips | voices | music | cut`. Stages skip work
that already exists, so re-running is cheap. The useful pattern is to render keyframes,
LOOK at them, fix the prompts, and only then spend GPU on clips:

    python3 scripts/short.py studio/movies/<name>.json --stage keyframes
    # inspect ~/ComfyUI/output/claude-generated/12-shorts/<slug>/keyframes/
    python3 scripts/short.py studio/movies/<name>.json

To force a re-render after changing prompts, delete the stale outputs first — a beat
whose keyframe already exists is skipped:

    rm -f ~/ComfyUI/output/claude-generated/12-shorts/<slug>/{keyframes/*.png,clips/*.mp4}

## After a reboot

A `@reboot` crontab entry runs `scripts/boot-services.sh` automatically. Check it with
`crontab -l`, and see `/tmp/boot-services.log` for what happened.

## The one rule worth knowing

**The image model renders nouns, not adjectives.** A shot line is
`shot: TEMPLATE | what is happening`, and what goes after the `|` is what you actually
get. "leaping mid-air volley, boot striking the ball, motion lines" renders.
"triumphant, heroic" does not — and a shot with no description at all renders a portrait
of whoever is in the scene, standing still.

Anything you want to be exact — colour, camera move, pacing, captions, loudness — should
live in a deterministic stage rather than the prompt. `studio/effects.json` records which
tier every variable lands in and cites the code that consumes it.

## Building a character that stays the same person

Open **/cast**. A character is a reusable identity, not a description you retype, and
there are three stages of making one hold. Each is stronger than the last.

### 1 · A reference sheet

One portrait, used by IPAdapter to refine faces during a render.

    python3 scripts/make_sheets.py

Worth knowing what this buys, because it is less than it appears: a weight sweep on this
box found the character was *already recognisable at zero* IPAdapter strength. The sheet
refines a face; it is not what makes the character.

### 2 · A turnaround

Sixteen views of the same person — angles first, then expressions, with framing held
constant throughout.

    python3 studio/_tools/turnaround.py VIRO

This uses `qwen-image-edit-2511-multiple-angles-lora` to RE-POSE the person in your source
image rather than generating someone new who matches the description. That distinction is
the whole point. It produces two things at once: a far stronger reference, and the
training set for stage 3.

The framing is written into every prompt on purpose. A LoRA learns whatever the set holds
constant as "the character" and whatever it varies as "not the character" — so a set that
is half close-up and half full-body teaches a muddle, and a costume that changes across
the set teaches that the costume is optional.

### 3 · A trained LoRA

The character stops being a prompt and becomes a model.

    python3 studio/_tools/train_character.py VIRO
    python3 studio/_tools/train_character.py VIRO --steps 1500 --rank 16

About ten minutes for 1000 steps on sixteen images, at roughly 1.7 steps/sec and 20 GB of
VRAM. It trains against `animagine-xl-4.0` because a LoRA is a delta on specific weights —
trained against one base and applied to another it degrades or does nothing.

### Then look at it

    python3 studio/_tools/lora_check.py VIRO

Same prompt, same seed, with and without the LoRA, side by side, in a scene the character
was never trained in. A loss curve cannot tell you whether this worked; the two failure
modes are invisible in a number and obvious in a picture.

    identical pair            undertrained — the LoRA is doing nothing
    the training portrait     overfit — it memorised instead of learning
    same person, new scene    it worked
