# The story editor

A scene-by-scene editor, so a film is built one good shot at a time instead of being
re-rolled whole and hoped over.

**Status.** The model, the folder tree, the inheritance resolver, takes and selection are
built and working (`studio/story.py`, `studio/_tools/story_tool.py`). THE SALT ROAD is
migrated into it as a real three-chapter story. The web editor is not built yet; what
exists is the thing a web editor would have to sit on. See *What is not built* at the end.

---

## Why this shape

The current pipeline renders a whole film from one JSON in one go. That is fine for a
first pass and wrong for everything after it, because the unit you actually want to fix is
one shot. Re-rolling a 59-shot film to improve shot 34 costs an hour and changes 58 shots
you were happy with.

So the unit of work becomes the **take**, and everything else exists to serve it.

```
story  = the video                  characters, voice casting, look of the whole thing
  └── chapter                       an act. Style usually belongs here.
        └── scene                   one shot. The unit you actually judge.
              └── take              one attempt at that shot. Many per scene, one selected.
```

Between scenes sit **transitions**, which belong to the chapter because they are a property
of the join, not of either shot.

## Inheritance

Every input resolves down the chain, nearest wins:

    story → chapter → scene → take override

A scene never *stores* the style it inherited. It stores only what it overrides. That way
changing a chapter's style genuinely changes its scenes, instead of changing a default that
nothing reads any more.

This is deliberately the same idea as `compose.resolve()` one level up, and it reuses it:
once story/chapter/scene are flattened into a single selection dict, that dict goes through
the existing card resolver, so the story editor inherits every measured rule already in
there — engine routing, base-model locking, the compose taxonomy, all of it.

**Every resolved value carries where it came from.** `resolve()` returns the value *and*
the level that supplied it, so a UI can show `style: dark_fantasy (from chapter 02)` and
grey out what is inherited. Not knowing why a shot looks the way it does is the single most
expensive thing in a long project.

## The folder tree

One folder per story, organised by scene, everything about a scene inside its scene folder.

```
stories/the-salt-road/
  story.json                    cast, voice casting, defaults, chapter order
  cast/
    BRENNA.json                 per-story character, points at its sheet
    sheets/BRENNA.png
  chapters/
    01-the-door-in-the-hill/
      chapter.json              style, look, music cues, scene order
      scenes/
        010-table/
          scene.json            prompt, motion, say/who, sfx, overrides
          takes/
            t01/  keyframe.png  clip.mp4  inputs.json  measured.json
            t02/  ...
          SELECTED -> t02       a file naming the chosen take
          voice/line.mp3        scene-local: a line belongs to its shot
          sfx/effect.mp3
        020-valley/
      transitions/
        010-table__020-valley.json
      audio/
        m01_table.mp3           cue anchored to a scene, spans forward
  exports/
    2026-08-08_1412_full.mp4
    2026-08-08_1412_manifest.json
```

Two rules about the tree:

- **`story.json` is the truth, the tree is the cache.** Anything under `takes/` can be
  deleted and rebuilt. Nothing that cannot be rebuilt lives outside a `.json`.
- **A take is immutable.** Changing an input never edits a take; it makes a new one. That is
  what makes "generate four and pick one" and "go back to the one from Tuesday" the same
  feature.

## Takes

```json
{ "id": "t03", "seed": 918273, "created": "2026-08-08T11:02:14",
  "inputs_hash": "9f2c…", "status": "rendered",
  "measured": { "luma": 84.9, "sat": 11.0, "seconds": 6.0 },
  "note": "hands are wrong on the left figure" }
```

`inputs_hash` is a hash of the fully resolved inputs. It buys three things:

1. **Nothing re-renders unless something really changed.** Editing a scene's note, or a
   chapter's title, does not invalidate a take.
2. **Stale detection.** When a chapter's style changes, every take whose hash no longer
   matches is marked `stale` — visibly, not silently. The old picture is still there and
   still watchable; it is just flagged as no longer matching its inputs.
3. **Honest provenance.** A take records the inputs it was actually made from, not the
   inputs currently in the file.

**Selection is a pointer, never a copy.** `SELECTED` names a take id. Export reads it.

## Transitions

A transition is an object on the chapter, keyed by the pair it joins:

```json
{ "from": "010-table", "to": "020-valley", "kind": "dissolve", "seconds": 0.7 }
```

Be clear about a distinction the UI should not blur: **most transitions are free and some
are expensive.** `cut`, `dissolve`, `fadeblack`, `wipe` are ffmpeg filters — instant, no
GPU, re-render as fast as you can click. A *generated* transition (a morph, an AI tween) is
a render with takes of its own, like a scene. Same object, wildly different cost. The UI
must say which it is or people will wait ninety seconds for a cut.

## Audio, honestly

The user's instinct that audio "is a bit tougher to have their own layer" is right, and it
is worth saying exactly why, because the three kinds do not behave the same way.

**Voice is scene-local and fits fine.** A line belongs to a shot. It lives in the scene
folder, it has takes like a picture does, and it can be re-rolled without touching
anything else. The one asymmetry: **narration length drives picture length**, so a
re-narrated line may change the shot's duration and therefore the export. That is already
how `epic.py` works and it is the right way round — never freeze a frame to cover a line.

**Music is not scene-local and should not pretend to be.** A cue spans scenes. Modelling it
per scene would mean chopping a 40-second cue into six pieces that have to stay in sync
forever. So a cue is a chapter-level object *anchored* to a scene:
`{ "at_scene": "010-table", "until_scene": "060-tavern" }`. It starts there and runs until
told to stop. Move the scene and the cue moves with it.

**SFX is scene-local to author and global to mix.** The effect belongs to the shot, but it
must be laid as one stem across the whole timeline so it can be ducked under speech — that
is `SOUND-01` in `craft/VIDEO_RULES.md`, and it was a real bug: effects baked per-segment
could not be ducked and played at full level straight through narration. So: authored in
the scene folder, mixed at the story level. Never bake audio into a picture segment.

**Lip sync inverts the dependency, and nothing here does it yet.** Today picture and voice
are independent — you can re-roll either. Lip sync would weld them: the mouth has to be
driven by a specific audio file, so **the voice take must be locked before the picture take
is rendered**, and re-rolling the line invalidates the picture. That is a genuine cost, not
a detail. The recommendation is to keep it opt-in per scene (`"lipsync": true`), applied as
a *post-pass on the selected take* rather than a property of generation, so that scenes
without dialogue — which is most of them in a narrated film — keep the cheap independent
model. No lip-sync node is installed; this is a design slot, not a feature.

## What to do about locking

The failure mode of an inheritance system on a long project: you fix a chapter's style in
week three and silently invalidate forty approved shots.

So a scene can be **locked**. A locked scene ignores inherited changes and keeps its
selected take, and the tool reports what it skipped rather than quietly obeying. Before any
story-level change, `story_tool.py plan` prints how many takes it would make stale, split
by locked and unlocked, and you decide.

## Suggestions

Things worth doing, roughly in the order I would do them.

1. **Build the picture loop before the audio loop.** Scene → four takes → pick → next scene
   is the whole value proposition, and it works today with no UI at all. A web editor for
   picture-only would already change how this feels to use.
2. **Make the take grid the home screen of a scene**, not a detail view. Four keyframes side
   by side with their seeds under them is the interface. Clips are slow to scan; keyframes
   are not, and the keyframe decides the clip.
3. **Render keyframes for all takes, clips only for the selected one.** A keyframe is about
   6 seconds and a clip is about 60. Judging on keyframes and only animating the winner is a
   10× saving on the loop you will run most.
4. **Show inherited values greyed with their source**, and make "override here" one click
   that copies the inherited value down. People need to see what they are diverging from.
5. **Diff before regenerate.** When inputs change, show which fields changed and how many
   takes go stale, before spending a GPU-minute.
6. **Keep a reject bin, not a delete.** The rejected take is evidence. This project has been
   wrong twice about what a model can do and both times the proof was an old render nobody
   had thrown away.
7. **Put `filmrules.py` on the save path.** The rules file already exists and already
   catches real bugs; running it when a scene is edited is nearly free and stops a violation
   at authoring time instead of after an hour of rendering.
8. **Do not build a timeline scrubber first.** It is the most familiar part of CapCut and
   the least valuable here, because the expensive decisions are per-scene, not per-frame.
   A list of scenes with thumbnails is enough for a long time.
9. **Export is a build, not a save.** Always assemble from selected takes into a new
   timestamped export with a manifest of exactly which takes went in. Never overwrite.

---

## Reference

```bash
python3 studio/_tools/story_tool.py new "THE SALT ROAD"
python3 studio/_tools/story_tool.py show the-salt-road
python3 studio/_tools/story_tool.py scene the-salt-road 01/010-table      # resolved inputs
python3 studio/_tools/story_tool.py take the-salt-road 01/010-table -n 4  # four takes
python3 studio/_tools/story_tool.py select the-salt-road 01/010-table t03
python3 studio/_tools/story_tool.py plan the-salt-road                    # what is stale
python3 studio/_tools/story_tool.py export the-salt-road
python3 studio/_tools/story_tool.py import-film films/salt_road_ep01.json --story the-salt-road --chapter 01
```
