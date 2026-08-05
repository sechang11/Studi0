# Wizard — Direct a scene

`/wizard`

## What this page is for

It turns a set of picks into a `.movie` file and then renders it. It is the main way
into the app. Everything else is either a library the wizard draws from, or a place to
look at what came out.

Eight steps run across the top: **Start · Format · Layer stack · Look & pace ·
Place & time · Cast · Shots · Review**. The right-hand column is live — it shows the
layer stack you have built, the `.movie` text as you author it, and where each choice
lands.

## What to do first

Click **Next →** all the way to **Review** without changing anything. Read the review
panel. You now know what a complete scene looks like and which fields the app fills in
for you.

Then go back to **Layer stack** and pick a **Style**. Style first, always. It decides
which model renders, and every later field means something different depending on that
answer.

## The three things that will confuse you

**1. Style is not a look. It is the engine switch.**

The Style band is at depth 0 of the stack because it is the outermost layer. Picking one
picks `animagine-xl-4.0` or `Qwen-Image 2512`, and with it the prompt format, what LoRAs
can attach, and whether a reference sheet will work. If you start from a template, check
this: 20 of the 82 templates set no style, and an empty style falls back to anime
without asking you.

**2. Look is not prompt text.**

The Look band sits at depth 0, outside the stack, deliberately. It is an ffmpeg colour
grade run on the finished frames. No model sees it. It cannot add anything to the frame
and it can be changed later without re-rendering.

**3. Style LoRA empty does not mean "no LoRA".**

The Style LoRA band is drawn indented under Style because it is the *same layer* reached
through the weights instead of the prompt. It has no clear button like the other bands,
because empty here means "follow the style's recommendation". It has its own reset
instead.

## One live defect to know about

The camera list offers **dolly_zoom**, **orbit** and **rack_focus**. In `scripts/short.py`
none of the three has a branch in `fx_chain()`, so a clip using them is byte-identical to
static — mean absolute pixel difference exactly 0.00. `compile.py` downgrades them for
compiled films, but a hand-authored `films/*.json` reaches `short.py` directly and gets
nothing. This is open task #21. Until it is fixed, treat those three as decoration.

## What good output looks like here

- The **Review** panel names an engine, and it is the engine you meant to pick.
- The **Where your choices land** tally accounts for every layer you filled in. A layer
  that appears in your stack but not in the tally was silently dropped.
- No conflict warning. The commonest one is a style whose `compose` field is `replaces`
  fighting the place you chose — the style will overrule the setting.
- The **Your .movie** box reads like something you could hand to someone else. If you
  cannot tell from the text what the shot is, neither can the compiler.
- Every beat under **Shots** names a motion, unless you want a still.
