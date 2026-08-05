# Make

`/make`

## What this page is for

The makers that are not films. Five of them:

| tile | what it does |
|---|---|
| **Image** | One still, using the same look, lighting, weather and emotion libraries the films use. |
| **Voice** | Speak a line in a chosen voice. The one place a character's emotion reaches the performance. |
| **Music** | A score cue. Fast enough to try five and keep one. |
| **Sound effect** | One sound, dry, to sit under picture. |
| **3D asset** | Turn one image into 3D geometry. Read the limits before planning around it. |

This is the fastest way to get anything out of the box. There is no wizard, no beats, no
`.movie` file — a tile, a form, and a button.

## What to do first

Click **Image**. Fill in the description. Click **Preview workflow** *before* you click
**Generate** — it shows you the exact graph that will be sent to ComfyUI, and queues
nothing. There is a **Download JSON** button next to it if you want to keep the graph.

Then click **Generate**. The **Result** panel on the right fills in when it lands.

Do music second. It is fast enough that trying five and keeping one is the intended
workflow, and it teaches you more about how prompts land than one careful image will.

## The three things that will confuse you

**1. The audition strip under the tiles is showing you a fraction of what exists.**

The strip is meant to let you hear or see examples before committing. It reads the
gallery, and only **48 of 1828** gallery entries carry a `domain` field — 21 sfx, 19
voice, 8 music. Everything else is invisible to it. A strip that looks thin is not a
sign the library is thin.

**2. The counts in the headers do not match the players below them.**

Two of the strips announce 19 and 21 items and then render nine players. There is an
undisclosed `slice(0, 9)` in the page. The missing ones are on disk.

**3. Image here is a still, not a frame of a film.**

It uses the same libraries as the film path — look, lighting, weather, emotion — but it
does not go through `compose.py`'s layer stack or `compile.py`. If you want the engine
picked by a style card and the layers resolved in order, that is the wizard, not this.

## What good output looks like here

- **Image** — the description is legible in the frame, in the engine's own language.
  Prose if you are on qwen, tags if you are on anime. If you wrote tags and got a worse
  photograph, that is the format mismatch, not the model.
- **Voice** — the line is intelligible at normal volume and the emotion is audible in the
  reading rather than only in the text. This is the only place emotion reaches a
  performance rather than a face.
- **Music** — it survives being played under picture without pulling attention. Generate
  five, keep one; that is the intended ratio.
- **Sound effect** — dry. If it arrives with its own reverb you cannot place it in a
  scene.
- **3D asset** — the side the source image never showed is coherent. That is the whole
  test, and the honest measured case in this project is a brass clockwork owl whose
  invented back holds feather detail through a full 360.
