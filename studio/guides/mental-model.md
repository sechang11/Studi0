# The mental model

Read this first. Five ideas run the whole app. None of them are guessable from the
screen, and everything else makes sense once you have them.

---

## 1. A shot is a stack of layers, not a sentence

You do not write a prompt here. You pick layers, and the app assembles the prompt.

The stack, outermost first:

```
Style          how it is drawn        <- decides which model renders at all
  Style LoRA   the same layer, reached through the weights
  Place        where it happens
    Character  who is in it
      Wear     how battered they are
      Light    where the light comes from
      Weather  what the air is doing
Look           a colour grade run AFTER generation
```

Order is not decoration. An inner layer is inside an outer one. A character is inside
a place; both are inside a style. That containment is what `studio/compose.py` walks
when it turns your picks into text, and it is why a style can overrule a place but a
place can never overrule a style.

You can see the resolution for yourself. `POST /api/compose` takes a stack and returns
the prompt it produced, the engine it chose, and any conflicts. The wizard's **Review**
step calls it on every change.

**Concrete:** on an empty stack, `/api/compose` answers *"nothing chose an engine, so
this falls back to anime."* That is the stack telling you a layer you never filled in
still made a decision for you.

---

## 2. Style picks the engine

This is the one that surprises everyone. Style looks like a visual preference. It is
actually a routing decision.

There are 130 style cards. 85 route to **anime**, 45 route to **qwen**. Pick "watercolour" and you have picked `animagine-xl-4.0`. Pick
"cinematic-photo" and you have picked `Qwen-Image 2512`. Everything downstream changes:
the prompt format, what a LoRA can attach to, whether a reference sheet works.

Despite the name, **anime is the general illustration engine**. It does watercolour,
ukiyo-e, oil paint, gouache. Do not read "anime" as a genre. Read it as "the drawing
model".

**Concrete:** 20 of the 82 scene templates set no style at all. Those 20 commit you to
animagine without ever showing you the choice. If you started from a template and the
output looks drawn when you wanted a photograph, this is why.

---

## 3. The two engines want opposite prompt formats

They are not interchangeable back-ends. They read different languages.

| | anime (`animagine-xl-4.0`) | qwen (`Qwen-Image 2512`) |
|---|---|---|
| format | danbooru **tags**, comma separated | **prose**, full sentences |
| example | `1girl, red hair ribbon, rain, night, city street` | `A woman with a red ribbon in her hair stands on a wet city street at night.` |
| native medium | illustration | photography |
| character LoRA | works | does nothing |
| reference sheet | via IPAdapter | via the qwen edit path |

Write tags at qwen and you get a worse photograph. Write prose at animagine and most of
it is ignored.

**Measured, and worth knowing before you fight it:** qwen cannot be steered off
photography by prompt at any cfg. Asking it politely for an oil painting returns a
photograph. A LoRA can do it — `illustration-1.0-qwen-image` at strength 1.5 gives
painted illustration. Prompt fails, weights succeed.

The consequence nobody expects: **a semi-real character has to be made on the
illustration engine**, not the photographic one. Name plus character LoRA plus a
painterly or CG style, with IPAdapter at 0.0. That is the opposite engine from where
anyone would look for it.

---

## 4. Looks are graded after generation. They are not prompts

A **look** is an ffmpeg colour grade applied to finished frames. No model ever sees it.
That is why it sits outside the prompt in the stack diagram, at depth 0, next to style
rather than under it.

What follows:

- A look cannot change what is in the frame. It can only change the colour of what came
  out. If you want a lantern in the shot, a warm look will not put one there.
- A look costs no GPU time and can be changed without re-rendering.
- A look can destroy a frame that generated fine.

**Concrete, and currently a live defect:** the `night` grade does not darken, it clips
to black. Measured on flat grey plates, input luma 16, 32 and 48 all come out as 0; 64
comes out as 1; 80 as 15. Anything at or below about 60 becomes pure black with nothing
to recover. The arithmetic is exact — `brightness=-0.15` then `contrast=1.20` about the
0.5 midpoint drives anything under 0.233 negative. If a dark shot came back as a black
rectangle, the render was fine and the grade ate it.

---

## 5. The model renders nouns, not adjectives

The governing rule of this whole project. If a word in your prompt names a **thing**,
the model is liable to draw the thing, even when you meant it as a manner or a medium.

**Concrete:** the `graffiti` style put a spray can in the subject's hands. The style
card is marked `compose: injects` and rates it the highest noun risk in its batch. 20
of the 130 style cards carry that mark.

**Concrete:** in the style-range probe, `bronze-sculpture` returned a desaturated
photograph of a live heron. Bronze is a medium, but it is also a plausible object, so
the model reached for the object. Same trap as the spray can.

The mirror image is also true. Manner words — *slowly*, *gracefully*, *menacingly* —
do essentially nothing. In the motion library, a named **mover** plus an **action**
works; the adverb attached to it does not.

So: to get a quality, find the noun that carries it. To avoid drawing a thing, do not
name the thing.

---

## A sixth thing, because it saves the most time

**A bad face is a pixel problem, not a weights problem.**

At 832x1216 full-body, the head is about one eighth of frame height. That makes the face
roughly 90 pixels, decided by an 11x11 patch in latent space. There is nowhere for a
face to be.

Fix it in this order:

1. Frame closer.
2. Raise resolution.
3. Add a face-detail pass.
4. Only then touch LoRA strength.

Raising the character LoRA strength is the intuitive first move and it does almost
nothing. Closer framing fixes it on both engines.
