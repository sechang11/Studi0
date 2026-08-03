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
