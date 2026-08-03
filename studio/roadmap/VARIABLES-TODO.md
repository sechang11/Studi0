# Roadmap - accepted but not yet renderable

26 of 461 variables. Each one compiles, warns once, and degrades to a
named fallback. A knob that quietly has no effect is worse than no knob.

| variable | falls back to | why it matters |
|---|---|---|
| `anime.anim.cg_mix` | Requested as tags such as cel-shaded mecha; no 3D pass and no camera solve. | Modern anime mixes cel-shaded 3D with 2D characters, and the mix must be declarable before it can be matched. |
| `anime.anim.partial` | Named elements are pushed into shot.motion_prompt with motion_strength clamped low; nothing guarantees only that element moves. | Animating one isolated element over a held drawing is what limited animation actually is. |
| `anime.anim.smear_frames` | Ignored; the substitute smear fx uses its own duration. | A smear lives one to three frames; longer and it becomes a blur. |
| `anime.anim.smear_style` | Motion-distortion tags on the mid keyframe when keyframe_mode allows one, plus the smear fx at the same percentage. | A drawn smear is a distortion drawing, a different thing from the post-process smear fx. |
| `anime.color.count` | Ignored at generation; optionally applied as a posterise pass at the grade stage. | Limited palettes were a cel-era constraint authors now choose for a flat designed look. |
| `audio.music.build_s` | Approximated by a rising gain ramp on the outgoing cue. | A build before a climax is a scored event with its own duration. |
| `audio.music.key` | Prompt hint only; no key extraction or enforcement. | A stated key lets reprises and stingers actually match the main theme. |
| `grade.match_ref` | Copies the reference's grade values verbatim; no histogram matching. | Matching one shot's grade to another is the routine fix for a mismatched cut. |
| `grade.scope` | Only full_frame runs; others warn and apply full_frame with reduced strength. | Grading everything equally is what destroys locked character colours. |
| `layer.bg.motion` | Renders as a single-plane push or pan on the flat keyframe. | A moving background plane is the signature of the anime pan. |
| `layer.depth_map` | Not generated; all depth effects fall back to tags. | An explicit depth pass is the prerequisite for real per-plane blur and parallax. |
| `layer.mode` | tag_hinted works today; masked and generated_separate degrade to it with a warning. | Says whether layers are only described or actually rendered and composited apart. |
| `layer.parallax_strength` | Ignored; the move applies uniformly to the flat frame. | How far the planes separate during a move, the whole point of 2.5D. |
| `layer.sky_plane` | Sky renders inside the background plate. | Sky as its own plane lets clouds move while the ground stays locked. |
| `shot.cam.motion_blur` | Drives smear fx strength only; LTX supplies whatever native blur it produces. | Direct override when shutter angle is too indirect for the author. |
| `shot.cam.rolling_shutter` | Ignored. | Skew on fast pans is a specific found-footage signature some films want. |
| `shot.cam.shutter_angle` | Buckets into smear fx amount; 45 renders as none, 360 as heavy. | How crisp or smeared motion reads, the difference between a war film and a dream. |
| `shot.comp.axis_line` | Author-time lint warning only; render unchanged. | Declares the 180-degree line so reverses can be checked rather than eyeballed. |
| `shot.focus.behavior` | Two keyframes joined by a short dissolve, or a single end-focus frame with a warning. | A rack focus is a dramatic beat that currently cannot be authored at all. |
| `shot.focus.rack_at_pct` | Ignored; the substitute dissolve is centred. | A rack that lands on a line of dialogue needs its timing authored. |
| `shot.lens.bokeh_shape` | Generic bokeh tag; shape ignored. | Out-of-focus highlight shape is much of a night film's identity. |
| `shot.lens.breathing` | Ignored; framing stays locked. | Focus pulls that change framing are a realism cue for handheld passages. |
| `shot.lens.distortion` | Baked as a fisheye/distortion tag; no post-warp pass. | Wide-angle bulge is a deliberate anime device for panic and comedy. |
| `shot.lens.vignette` | Global gamma pull plus a vignetting tag; no radial mask. | Corner falloff quietly focuses attention and is expected in cinematic grades. |
| `time.beat_grid` | Cuts stay on authored times; the resolver reports nearest musical grid offsets. | Lets cuts snap to the generated music instead of floating against it. |
| `time.sync_to_music` | Ignored; shot uses its authored duration. | Marks the individual shots that must land on a musical hit. |

## Deep-dives already written

- [audio-picture-offset.md](audio-picture-offset.md) - L-cuts and J-cuts. The highest-value item here.
- [lipsync.md](lipsync.md)
- [blocking.md](blocking.md)
- [camera-dolly_zoom.md](camera-dolly_zoom.md), [camera-rack_focus.md](camera-rack_focus.md), [camera-orbit.md](camera-orbit.md)

Add a file here when work starts on one: what blocks it, and the cheapest path.
