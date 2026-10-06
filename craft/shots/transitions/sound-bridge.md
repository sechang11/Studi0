# Sound over the cut - J cut, L cut, a bed (`trans-sound-bridge`)

| family | status | last tested | best result |
|---|---|---|---|
| transitions | works-with-caveats | 2026-10-05 | the fire esper: 5 L cuts and 3 beds through 23 cuts, grade A- |

**Also called:** sound bridge, J cut, L cut, J-cut, L-cut, split edit, audio overlap, background track through the cut, sound glue, a bed under several shots, glue
**Not the same as:**
- [`trans-dissolve`](dissolve.md) - the PICTURES overlap; here the picture cuts and the sound carries on
- [`trans-held-object`](held-object.md) - an element of the picture held across the cut
- [`trans-match-cut`](match-cut.md) - a shape that rhymes across a hard cut

## Recipe (v1, 2026-10-05)

Let the sound cross the cut: the outgoing shot's sound runs on under the next picture (L cut), or the next shot's sound starts under this one (J cut), or one bed runs under a whole leg of the story (LTX_PLAYBOOK §102, a draft).

1. **L cut** after a breath or a whisper: in the plan, the shot's `"out"` is earlier than its take's end and `"audio_out"` is the end - the picture cuts, its sound dies away under the next shot over the tail (0.35-0.5 s).
2. **J cut** for something about to arrive: `"audio_in"` earlier than `"in"`; the sound swells in under the outgoing picture.
3. **A bed** under a range of shots - non-music sound design (Stable Audio, workflow 10: a rumble, a forest fire, wind in ash), 12-14 dB under the takes, faded 1.5-2 s at each end, looped to length in its own pass.
4. **The score** is the strongest bridge of all, but no generated music goes into a film unheard (`craft/SOUND.md` §0): candidates are mixed for the director to pick by ear.
5. `python3 studio/_tools/glue_cut.py PLAN.json` builds it; the plan for THE FIRE ESPER is written from each shot's `"glue"` by `studio/samples/settest/work/esper/cutplan.py`.

## Checks before picking

- Listen across every cut with your eyes shut: does the sound jump, or carry?
- Is the bed under the takes, not over them (12-14 dB down)?

## Progression

### 2026-10-05 · the fire esper · L cuts, beds · grade A-
- **Did:** L cuts on 010 (wind and laugh), 020 (the whisper), 070 (the birds), 120 (the roar into 130), 190 (the crow); a rumble under the summoning (030-130, rising from his look down), a forest fire under the hunt (140-190), wind in the ash under the end and its card (190 to the end card).
- **Got:** the cut plays as one piece: the rumble rises from his look down to the roar in his face, the fire carries the hunt, the ash wind runs under THE END; the L-cut tails die away under the next picture without a jump. A take whose sound ended early left a -67 dB hole at 030 → 040 until the rumble was started one shot earlier.
- **Learned:** check the level every half second across the cut (`studio/samples/settest/work/esper/levels.py`): holes hide at cuts; start a bed one shot before the leg it belongs to, and carry it under the end card.

### 2026-10-05 · the fire esper, the score candidates · the score stays under the takes · grade n/a
- **Did:** a note about the TerraTheme covers ("some sound effect stuff going on in there... not musical") read as one about the film's score: the candidates re-mixed music-forward (`studio/_tools/score_mix.py`: the score leading over the takes' own sound alone, no beds, a gentle duck).
- **Got:** the director: "the music for the video was fine, it's noticeably worse now" - the note had been about the covers.
- **Learned:** a score candidate is mixed by the casting tool (the takes' own sound leading, the score ducked under it, the beds in); the music-forward mix is an option (`music_forward`), not a default; ask which music a note is about.

## Failure modes

| symptom | cause | fix | seen in |
|---|---|---|---|
| the cut hangs at 100% CPU forever | a bed looped with `-stream_loop -1` inside the big filter graph never ends (ffmpeg 8) | loop the bed to length in its own pass first | glue_cut.py, 2026-10-05 |
| an audio-only render never ends | `apad,atrim` without a picture on ffmpeg 8, even with `-t` | `apad=whole_dur` | glue_cut.py stem, 2026-10-05 |

## Evidence

- `studio/_tools/glue_cut.py`; `studio/shotscripts/fire-esper.cut.json`; LTX_PLAYBOOK §102.

## Open questions

- J cuts: none tried yet on a cut where the next sound should lead.
- How long an L cut's tail can run before the two sounds muddy each other.
