# Generating content without asking anyone

Three shell scripts that fill the demo library on their own, and what was measured while
building them.

## The scripts

```
./bin/generate.sh --hours 8                    fill the library for eight hours, then stop
./bin/generate.sh --minutes 20 --dry           show twelve rolls, render nothing
./bin/generate.sh --status                     from another shell
./bin/generate.sh --stop                       finish the current job and quit
./bin/collect.sh                               contact sheets + index.html over the output
python3 studio/_tools/roll.py --explain        what the randomiser can draw from, and why
```

Weights choose the mix: `--weights image=6,video=2,music=1,voice=1,sfx=1` is the default.
Each entry becomes that many tickets in a bag, and every job draws one.

## There is no prompt to write

The question "is there a randomizer prompt" has a better answer than a random sentence
generator: **the libraries are the randomiser.**

```
styles       91 of 130   weak and unavailable excluded, plus compose injects/inert
places       64
looks        24 of 25    night excluded - it clips to black
cameras       8 of 11    dolly_zoom, orbit, rack_focus excluded - identical to static
motions       9 ready of 34
cues 22   sfx 20   voices 21 castable   characters 7

distinct image jobs before motion or camera: 3,773,952
```

Every one of those cards was rendered and looked at before it became drawable. An LLM
writing prompt sentences would produce fluent text with no idea that `night` crushes to
black, or that a style named after an object puts the object in the subject's hands. The
cards carry that knowledge; a roll inherits it for free.

Run the same script again and you get different work - the seed comes from the clock.
`--seed 4242` reproduces a run exactly, which is what you want when something good comes out.

## The deadline is the first feature

`generate.sh` refuses to start without `--hours` or `--minutes`, and says why in the error.

A `gallery_gen.py --loop` was started on this box with no stopping condition and ran for
**17 hours 22 minutes**, holding the GPU and starving three other jobs. Nothing showed it
was running. So: a mandatory budget, a PID file, a STOP file, signal traps, and a refusal to
*begin* a job that cannot finish - a video roll inside the last two minutes downgrades to an
image rather than being killed halfway.

## What the first live renders taught

Two renders, two defects, both found by looking at the picture rather than the exit code.
Both returned `ok: true` with healthy luma.

### 1. A style card can be a person in disguise

`photorealistic` over the `underwater_city` place: a sunken city with a man's face across
60% of the frame, in a prompt whose first three words are `scenery, no humans`.

The style card emits *"natural skin with visible pore texture and fine stray hair,
catchlights in the eyes, 50mm lens ... falling off behind the subject."* That is not a look,
it is a person. The place said no humans, the style said eyes, and the eyes won.

**This is the noun-as-prop rule one layer up.** 16 of the 92 drawable style cards read this
way: `photorealistic`, `studio_portrait`, `cinematic_film_still`, `pixar_3d`,
`infrared_photo`, `webtoon_flat`, `concept_art`, `cubism`, `impressionist`, `polaroid`,
`pre_raphaelite`, `silhouette_poster`, and the four shoujo/shonen/seinen cards.

Fixed by deciding the SUBJECT before anything else: a style that wants a person is given
one. Detected by regex over the card text, not a hardcoded list, so a new card written in
the same voice is caught the day it lands.

### 2. `solo` is a request, not a constraint - and framing loses to the place

TERRA close-up over `floating_islands` came back with **two** people: her face filling the
left, and a different figure (red hair, not green) on a distant bridge. The prompt said
`1girl, solo`.

Two causes. First, `close-up` appeared **twice** - the character card emits its own framing
token through `compose`, and the roll prepended a second. Two layers, same instruction.
Framing now *replaces* the card's token, longest-match-first so `medium close-up` is not
half-matched as `close-up`.

Second, the count was only ever asserted. Moving it to the negative
(`2girls, multiple girls, duplicate, background people`) removed the duplicate.

**But the same seed then produced a wide landscape with the figure at ~8% of frame height,
when the roll had asked for a close-up.** The framing token never won either round: first it
split the frame into two subjects, then it lost outright.

The finding: **a place written at landscape scale beats a framing token.** Rather than keep
arguing with it, the place now sets the scale - a cast character over a vista place draws
only `medium shot` or `wide shot`. Verified across ten rolls: zero violations.

This one is measured on a single seed. It is a strong enough effect to act on and a thin
enough sample to say so.

## What held up

- **Base-model locking works.** `compose` reported TERRA's LoRA inactive on qwen: *"a
  modification of the anime checkpoint ... the file is passed through and quietly never
  read."* The roll now records `character_lora` only when the weights are genuinely in play,
  because an inactive name in the recipe would be a lie on the gallery page.
- **The quality gate works.** Near-black renders go to `rejected/` with the reason recorded,
  not deleted - a failure you can look at is worth more than one you cannot.
- **Blocked voices are locked out twice**, in `roll.py` and again in `render_job.py`, so a
  hand-written job cannot reach the four packs that clone real people either.

## Two defects found in existing files

- **`workflows/12_ltx23_i2v_audio.json` asks its audio latent for 25fps against 24fps
  video** - 4% drift, a second of slip over half a minute. Corrected in the render path;
  the workflow file itself is still wrong. This is open task #45.
- **A LoRA hung off the checkpoint in `22_anime_kf_ipadapter.json` would dangle unused** -
  node 8 reads its model from node 4, not node 1. Spliced correctly in `render_job.py`.
  Fails silently, exactly like a LoRA on the wrong base model.
