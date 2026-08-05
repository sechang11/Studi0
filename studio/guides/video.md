# Video

`/video`

## What this page is for

375 rendered clips, grouped by the question each one was made to answer. This is not a
folder of nice clips. It is the project's evidence file for **what survives the motion
pass** — the step where a still becomes video and things start going wrong.

Seven groups, each with its own measure:

| group | what it varies | measure |
|---|---|---|
| Style through video | 15 styles, everything else held | detail @8.0s |
| Camera moves | 11 camera cards | MAD vs static |
| Motion — the video prompt | 15 motion prompts | activity |
| Transitions | 12 transition filters | MAD vs cut |
| Pacing | 7 pacing patterns | mean shot |
| Engine comparison — LTX vs Wan | 27 clips | zoom estimate |
| Seed replicates | 41 clips, same recipe | video seeds |

## What to do first

Open **Camera moves** and sort by the measure, smallest first. The measure is *MAD vs
static* — mean absolute pixel difference against a clip with no camera move at all. A
camera card scoring 0.00 produced a clip that is byte-identical to holding still.

Three cards do exactly that: `dolly_zoom`, `orbit`, `rack_focus`. You are looking at the
proof of a live bug, laid out as data. That is what this page is for.

## The three things that will confuse you

**1. The strips are more useful than the video players.**

Each entry carries two strips: **keyframe + 8 frames across the clip**, and **the same 9
frames cropped at native resolution**. The cropped one is where you see whether detail
survived to 8 seconds. A clip playing at fit-to-screen size hides everything; the crop
does not. Look at the strips first, and only play the clip once a strip makes you curious.

**2. The headline number is not a quality score.**

Each group measures a *different* thing, and higher is not always better. In "Camera
moves", high MAD means the camera really moved. In "Seed replicates", the whole point is
that a number should be *similar* across seeds. Read the group's blurb before reading its
numbers.

**3. Engine and idiom are confounded, and the page says so.**

The Style group's own blurb admits it: all nine illustration styles held for the full
8.04s, and the axis that predicts survival looks like illustration-vs-photograph — but in
this library engine and idiom are perfectly confounded, so that cannot be separated from
animagine-vs-qwen. A finding that names its own confound is worth more than one that does
not.

## If the page is empty

The index is a built file, not a live scan. Rebuild it:

```
python3 studio/_tools/video_index.py all
```

The API says so itself when the file is missing.

## What good output looks like here

- **Motion is present and it is the motion you named.** Not merely: pixels changed. The
  `cam_pull` card is the cautionary example — real motion across three seeds, but the
  creep measure said the frame never receded, so the pull-back never happened.
- **Detail survives to the end.** Compare the first and last cells of the cropped strip.
  Boiling texture, dissolving faces and mushy edges all appear late.
- **The face is still the right person when you need it.** Identity holds roughly eight
  seconds, but budget by the action: on a head turn, frontal to 5s, profile at 7s,
  back-of-head at 8s.
- **No judder.** It appears only after the whole render is spent, which is why
  `compile.py` refuses some combinations before you pay for them.
