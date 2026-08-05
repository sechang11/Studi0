# Motions

`/tags#motions`, and the motion field on the wizard's **Shots** step

## What this page is for

34 cards, each one a sentence that makes something move. A motion card is the **one
string the video model reads**. Everything else about a clip — style, place, character —
is decided in the still that seeds it. Motion is decided here.

The cards live in `studio/motions/` and are reached from the tag library page. Nine are
`ready`, 18 are `weak`, 7 are `unavailable`, and each carries the numbers that put it in
that bucket.

## What to do first

Open one card and read its `grammar` field. Every card has one, and they all look like
this:

```
[MOVER] [ACTION VERB] [PATH/SPATIAL RELATION]
```

Then read the `text` it produces: *"The camera pulls back away from her."* A named thing,
a verb, and where it goes. That is the whole grammar.

## The three things that will confuse you

**1. Manner words do nothing.**

*Slowly. Gracefully. Menacingly. Dramatically.* All measured as no-ops. A named **mover**
plus an **action** works; the adverb attached to it does not. If you want a slow move,
you cannot ask for one — you pick a different action, or you change the frame count.

This is the noun rule again: the model renders things, not qualities.

**2. A beat that names no motion is a still.**

Not a subtle one. Across the three real films in the project, **21 of 29 beats resolve to
a motion hold**, and not one beat in any of the three names a motion card. The control
film `motion-proof.movie` uses six motion cards and holds only 3 of 12.

The mechanism works. Nobody had been using it. If your clip does not move, check whether
the beat named a motion before checking anything else.

**3. `weak` and `unavailable` mean the numbers disagreed with the name.**

Look at `cam_pull` — "Camera pulls back". It is marked `unavailable`, and its verdict
says why: motion was present across three seeds (0.78 / 1.70 / 1.44), but **creep** —
the measure that says whether the frame is actually receding — came back 1.00, 1.05, 1.00.
*"A pull-back must give a creep below 1.00 and none of the three does."*

So it moved. It just did not pull back. That is what a `weak` or `unavailable` motion
card is telling you: something happened, but not the thing on the label.

## What good output looks like here

- Something in frame moves, and it is the thing the card names. Not merely: pixels
  changed.
- The face survives to the moment you need it. Identity holds about eight seconds, but
  **budget by the action** — on a head turn the face is frontal to 5s, profile at 7s,
  back-of-head at 8s.
- No judder. Judder shows up after the entire render is spent, which is why `compile.py`
  refuses some combinations up front.

## The other tag libraries live on the same page

`/tags` also holds looks, cameras, transitions, lighting, weather, emotions, shots and
layers. Two warnings carried from measurement:

- **cameras**: `dolly_zoom`, `orbit` and `rack_focus` produce clips byte-identical to
  static. `orbit` is not achievable after the fact at all; the other two need a depth
  pass that does not exist yet.
- **transitions**: six real filters exist and nothing in the pipeline consumes them yet.
