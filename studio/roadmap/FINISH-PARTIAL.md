# Finish the partial ones

**155 variables** and **41 presets** are marked `partial`: the
useful part works, but some of what the name promises is advisory or approximated.

They deliberately have NO samples in the app. A sample would imply the variable is
fully honoured, and a preset that looks finished but is not is worse than one plainly
marked unfinished.

## Partial presets

| group | preset | what is not yet honoured |
|---|---|---|
| `emotions` | `angry` | face, eyes, mouth and body render today as tags; voice_style applies only on TTS engines that accept an emotion vector. |
| `emotions` | `cold` | face, eyes, mouth and body render today as tags; voice_style applies only on TTS engines that accept an emotion vector. |
| `emotions` | `determined` | face, eyes, mouth and body render today as tags; voice_style applies only on TTS engines that accept an emotion vector. |
| `emotions` | `exhausted` | face, eyes, mouth and body render today as tags; voice_style applies only on TTS engines that accept an emotion vector. |
| `emotions` | `fear` | face, eyes, mouth and body render today as tags; voice_style applies only on TTS engines that accept an emotion vector. |
| `emotions` | `grief` | face, eyes, mouth and body render today as tags; voice_style applies only on TTS engines that accept an emotion vector. |
| `emotions` | `joy` | face, eyes, mouth and body render today as tags; voice_style applies only on TTS engines that accept an emotion vector. |
| `emotions` | `neutral` | face, eyes, mouth and body render today as tags; voice_style applies only on TTS engines that accept an emotion vector. |
| `emotions` | `resolve` | face, eyes, mouth and body render today as tags; voice_style applies only on TTS engines that accept an emotion vector. |
| `layers` | `crowded` | plane content and tonal value render today via tags; true per-plane blur and parallax need layer.depth_map, see roadmap. |
| `layers` | `deep` | plane content and tonal value render today via tags; true per-plane blur and parallax need layer.depth_map, see roadmap. |
| `layers` | `flat` | plane content and tonal value render today via tags; true per-plane blur and parallax need layer.depth_map, see roadmap. |
| `layers` | `framed` | plane content and tonal value render today via tags; true per-plane blur and parallax need layer.depth_map, see roadmap. |
| `layers` | `isolated` | plane content and tonal value render today via tags; true per-plane blur and parallax need layer.depth_map, see roadmap. |
| `layers` | `silhouette` | plane content and tonal value render today via tags; true per-plane blur and parallax need layer.depth_map, see roadmap. |
| `layers` | `standard` | plane content and tonal value render today via tags; true per-plane blur and parallax need layer.depth_map, see roadmap. |
| `lighting` | `candle` | key, direction, quality and rim render as prompt tags; ratio and temp also bias the grade. |
| `lighting` | `dramatic` | key, direction, quality and rim render as prompt tags; ratio and temp also bias the grade. |
| `lighting` | `flat` | key, direction, quality and rim render as prompt tags; ratio and temp also bias the grade. |
| `lighting` | `floodlit` | key, direction, quality and rim render as prompt tags; ratio and temp also bias the grade. |
| `lighting` | `moonlight` | key, direction, quality and rim render as prompt tags; ratio and temp also bias the grade. |
| `lighting` | `natural` | key, direction, quality and rim render as prompt tags; ratio and temp also bias the grade. |
| `lighting` | `rim` | key, direction, quality and rim render as prompt tags; ratio and temp also bias the grade. |
| `lighting` | `silhouette` | key, direction, quality and rim render as prompt tags; ratio and temp also bias the grade. |
| `soundscapes` | `night_room` | levels and ducking render today; reverb spaces are approximated. |
| `soundscapes` | `rain_out` | levels and ducking render today; reverb spaces are approximated. |
| `soundscapes` | `room` | levels and ducking render today; reverb spaces are approximated. |
| `soundscapes` | `silence` | levels and ducking render today; reverb spaces are approximated. |
| `soundscapes` | `stadium` | levels and ducking render today; reverb spaces are approximated. |
| `soundscapes` | `street` | levels and ducking render today; reverb spaces are approximated. |
| `soundscapes` | `subjective` | levels and ducking render today; reverb spaces are approximated. |
| `soundscapes` | `tunnel` | levels and ducking render today; reverb spaces are approximated. |
| `weather` | `clear` | tags and atmospherics render today; wind and per-particle motion are prompt-only. |
| `weather` | `drizzle` | tags and atmospherics render today; wind and per-particle motion are prompt-only. |
| `weather` | `dust` | tags and atmospherics render today; wind and per-particle motion are prompt-only. |
| `weather` | `fog` | tags and atmospherics render today; wind and per-particle motion are prompt-only. |
| `weather` | `heat` | tags and atmospherics render today; wind and per-particle motion are prompt-only. |
| `weather` | `overcast` | tags and atmospherics render today; wind and per-particle motion are prompt-only. |
| `weather` | `rain` | tags and atmospherics render today; wind and per-particle motion are prompt-only. |
| `weather` | `snow` | tags and atmospherics render today; wind and per-particle motion are prompt-only. |
| `weather` | `storm` | tags and atmospherics render today; wind and per-particle motion are prompt-only. |

## Partial variables, by namespace

### `anime.*` - 38

- `anime.anim.bank_reuse` - Whether a bank cut is the same footage or re-dressed is a look and a cost decision at once.
- `anime.anim.cycle` - Repeating cycles are how anime buys screen time, and a looped short clip is far cheaper than a long generation.
- `anime.anim.cycle_loops` - How many repeats decides whether a cycle reads as walking or as a stuck GIF.
- `anime.anim.exaggeration` - Squash, stretch, anticipation and overshoot are drawn-animation physics no camera or lens variable can express.
- `anime.anim.hold_style` - The held cel is the backbone of limited animation and deserves a name rather than being the absence of a video pass.
- `anime.anim.motion_budget` - Anime is scheduled art, and capping fully animated cuts keeps the money on screen where it matters.
- `anime.anim.step_scope` - Anime steps the drawings but never the camera, so whole-frame stepping judders the pan.
- `anime.bg.artwork_extent` - An anime pan is performed across one oversized painting, so the art must be wider than the frame.
- `anime.bg.char_integration` - Characters looking pasted onto the background is generated anime's most common failure.
- `anime.bg.hue_relation` - Hue separation keeps a character readable against a busy painting, distinct from value separation.
- `anime.bg.plate_id` - Every cut in a location should sit on the same painting.
- `anime.bg.style_contrast` - The gap between character and background rendering is the defining anime image decision.
- `anime.color.character_lock` - A character's approved colours must survive the scene grade or recognition breaks.
- `anime.color.forbidden` - Withholding one colour until it matters is the oldest device in a colour script.
- `anime.color.harmony` - Stating the palette rule lets accent, background and rim colours be derived rather than guessed.
- `anime.color.motif_map` - Binding each motif to one colour makes a visual callback land without dialogue.
- `anime.color.script` - The colour script is the anime colour designer's actual deliverable, not a per-shot grade preset.
- `anime.color.setting` - Anime approves a separate character colour set per lighting condition, before any grade.
- `anime.draw.cel_artifacts` - Cel-era anime looks old because of how it was photographed, and these artefacts carry it.
- `anime.draw.detail_density` - Line count per drawing is a production tier that should inherit down a sequence.
- `anime.draw.line_color` - Coloured trace lines are a finishing decision that softens an entire film's character art.
- `anime.draw.shadow_hue` - Anime shadow colour is chosen by a colour designer, and the hue shift is half a film's identity.
- `anime.format.broadcast_safe` - Strobe and flash limits exist because broadcast anime injured viewers once.
- `anime.format.ed_style` - The ending is usually the cheapest and most stylised part of an anime.
- `anime.format.next_preview` - The next-episode preview is a fixed anime form with its own voice and pacing rules.
- `anime.format.op_style` - An opening is its own short film with its own grammar.
- `anime.fx.aura` - A character-attached aura is a persistent drawn element held across a shot.
- `anime.fx.deform_scope` - A chibi cutaway and a chibi shot are different jokes with different timing.
- `anime.fx.drawn_effect` - Effects animation is its own craft and looks nothing like photographic fire or water.
- `anime.fx.onomatopoeia` - Drawn sound text on screen is native anime grammar with no live-action equivalent.
- `anime.fx.onomatopoeia_pos` - Where the sound word sits decides whether it reads as impact or as a caption.
- `anime.fx.onomatopoeia_style` - Lettering style is the whole tone, separating a horror rumble from a comedy thud.
- `anime.fx.split_screen` - Multi-panel frames hold three reactions at once, which frame-in-frame cannot express.
- `anime.perf.blink_pattern` - A double blink is surprise and a slow close is resignation; rate alone cannot say which.
- `anime.perf.blink_rate` - Blinks are the cheapest sign of life in a held drawing and anime times them deliberately.
- `anime.perf.mouth_chart` - Anime mouths run on a handful of positions, and the count separates anime from a Western cartoon.
- `anime.perf.mouth_flap_rate` - Flap rate makes mouth movement read as speech even when it is not phoneme-accurate.
- `anime.perf.pose_library` - Named stock poses give repeatable staging without describing anatomy every time.

### `shot.*` - 34

- `shot.cam.dutch_deg` - Continuous amount for the dutch angle instead of a binary on/off.
- `shot.cam.move` - The core motion verb, extending eight native moves to what directors ask for.
- `shot.cam.move_anchor` - A push to frame centre and a push to a character's eye are different shots.
- `shot.cam.move_ease` - Linear moves are the tell of machine-made footage; easing feels operated.
- `shot.cam.move_end_pct` - Lets a move settle before the cut.
- `shot.cam.move_start_pct` - Lets a move begin after a held beat instead of always on the cut.
- `shot.cam.rig` - Baseline motion texture for a sequence so every shot needn't set shake.
- `shot.cam.shake_freq` - Amplitude without frequency gives every shake the same character.
- `shot.cam.subject_distance_m` - Ties focal length and shot size together so the pair stays coherent.
- `shot.comp.balance` - Visual weight distribution is what an author means when a frame feels wrong.
- `shot.comp.depth_stack` - How many depth planes the frame is built from; the contract with layer variables.
- `shot.comp.headroom` - The most common framing error and the most common deliberate tension device.
- `shot.comp.horizon` - Horizon placement sets whether a character dominates sky or is crushed by ground.
- `shot.comp.leading_lines` - Directed lines tell the eye where to go and anime backgrounds lean on them.
- `shot.comp.lookroom` - Space in front of a looking character makes a frame balanced or trapped.
- `shot.comp.negative_space` - Emptiness is the loudest tool for loneliness and dread and needs a dial.
- `shot.comp.perspective` - Perspective construction is an explicit background-art decision in anime.
- `shot.comp.screen_direction` - Keeps travel and chase geometry consistent instead of flipping randomly.
- `shot.comp.subject_scale` - Continuous control between the coarse steps of shot.size.
- `shot.comp.thirds_bias` - Where the subject sits laterally is the composition choice authors most want.
- `shot.focus.bg_blur` - Continuous background separation that survives even without true dof.
- `shot.focus.dof` - How much of the world is sharp is the fastest character/background separation.
- `shot.focus.fg_blur` - Soft foreground occluders are the cheapest depth cue in the language.
- `shot.focus.point` - Names what must be sharp so generator and blur pass agree on the subject.
- `shot.focus.softness` - Global softness for flashbacks and dreams, independent of depth.
- `shot.fx.screentone` - Manga screentone as a mood device is a distinct look from film grain.
- `shot.keyframe_mode` - Controls whether the shot is single-image i2v or interpolation between authored frames.
- `shot.lens.compression` - How flat the background stacks when focal length alone doesn't sell it.
- `shot.lens.filtration` - Diffusion is the cheapest way to unify a look across shots and should inherit.
- `shot.lens.flare` - Flare is a mood signature authors reach for constantly.
- `shot.lens.focal_mm` - A number authors think in, from which compression and dof defaults derive.
- `shot.lens.look` - Lets an author state the feel without knowing millimetres; this maps to tags.
- `shot.match_prev` - Asks for a cut landing on the previous composition instead of hand-copying values.
- `shot.reference` - A reference image is often faster and more reliable than any number of tags.

### `audio.*` - 13

- `audio.amb.layers` - Ambience is built from stacked layers, not a single generated file.
- `audio.mix.duck_mode` - How music gets out of the way of dialogue is a policy, not a per-cue fix.
- `audio.mix.perspective` - Sound perspective is how a subjective POV is actually communicated.
- `audio.music.loop` - Looping a short cue is how a long scene gets scored cheaply.
- `audio.music.mode` - Mode carries emotional valence more reliably than any adjective in the prompt.
- `audio.music.motif` - A named musical theme is how a film's emotional callbacks are built.
- `audio.music.reprise_of` - A reprise must point at the earlier cue rather than be re-described from scratch.
- `audio.music.stinger` - A single musical hit on a cut is the most-used scoring device in anime.
- `audio.music.tempo_bpm` - Tempo is the link between music and cut rate and must be statable.
- `audio.music.transition` - The music-transition variable the author asked for, naming how one cue becomes the next.
- `audio.music.transition_at` - Where the change lands is what makes it feel scored rather than accidental.
- `audio.sfx.auto_foley` - Footsteps and cloth should appear from blocking rather than be authored per shot.
- `audio.sfx.reverb_send` - Effects must sit in the same room as the dialogue or the scene splits apart.

### `layer.*` - 8

- `layer.bg.blur` - Per-plane blur is what actually separates a character from the world.
- `layer.bg.value` - Tonal separation between planes is how a frame reads at a glance.
- `layer.character_plane` - Says which plane the subject occupies so blur and parallax treat them correctly.
- `layer.count` - Declares how many depth planes exist, the root of the whole layers feature.
- `layer.fg.blur` - Foreground elements read as foreground mainly because they are soft.
- `layer.fg.coverage` - How much of the frame the occluder eats, from a hint to a near-total block.
- `layer.fg.motion` - Something crossing the lens is the strongest depth cue in a moving clip.
- `layer.mid.occupancy` - How much midground clutter sits between camera and background.

### `char.*` - 8

- `char.arc_stage` - Where a character sits in their arc biases wardrobe, grade and performance defaults.
- `char.emotion_secondary` - Real performance is usually two feelings at once and the mix is the acting.
- `char.face_weight_by_size` - A face lock that helps a close-up wrecks a wide, so it must vary by shot size.
- `char.gaze_target` - Naming who is looked at keeps eyelines consistent across a reverse.
- `char.height_cm` - Relative height drives two-shot framing and eyeline geometry.
- `char.lora` - A trained character LoRA outperforms any tag bundle when one exists.
- `char.relationship` - Blocking distance, eyelines and voice register all follow from who these people are to each other.
- `char.wear.colors` - Costume colour must be locked or a character reads differently every scene.

### `light.*` - 8

- `light.animate` - Living light stops a still-derived clip feeling like a moving photograph.
- `light.animate_rate` - A candle flicker and a police strobe are the same effect at different rates.
- `light.continuity_lock` - Light must not re-roll between cuts in one location or the scene stops cohering.
- `light.fill` - Explicit fill separates a moody frame from a muddy one.
- `light.haze` - Atmospheric haze is what makes shafts, depth and distance visible at all.
- `light.ratio` - Key-to-fill ratio is the numeric handle on drama.
- `light.rim_color` - A coloured rim ties a character to the location's neon, fire or moonlight.
- `light.shadow_density` - How black the blacks go, separate from overall contrast.

### `time.*` - 7

- `time.chain_overlap_frames` - Overlap between chained clips is the main lever on how visible a join is.
- `time.chapter_s` - Chapter budget so a film can be shaped to a runtime from the top down.
- `time.clip_chain` - Makes the renderer's chaining explicit so long shots are authored knowingly.
- `time.cut_rate` - Numeric handle on editing density when the pace word is too coarse.
- `time.fit_mode` - Says what happens when authored shots do not add up to the declared scene length.
- `time.rhythm` - Shot-length pattern is what makes an edit feel composed rather than uniform.
- `time.scene_s` - The scene-length control, usable as a budget shots are fitted into.

### `block.*` - 6

- `block.contact` - Physical contact is the hardest thing to generate and must be explicitly asked for.
- `block.entrance` - How a character arrives in frame is a directing choice, not an accident of generation.
- `block.exit` - Exits punctuate scenes and decide whether the next shot needs the character at all.
- `block.group_shape` - Group compositions fail without a stated shape and become tag soup.
- `block.pattern` - The blocking variable, describing how bodies move relative to each other.
- `block.positions` - Who stands where in frame is what makes reverses and group shots readable.

### `dialogue.*` - 6

- `dialogue.line.delivery` - How a line is said is the acting, and it is separable from the emotion word.
- `dialogue.line.emotion` - A line can carry a different feeling from the face, and that gap is the drama.
- `dialogue.line.emotion_strength` - Emotion vectors need a magnitude or every line is maximally acted.
- `dialogue.lipsync` - The lipsync variable, stating how hard mouth movement must match audio.
- `dialogue.voice.accent` - Accent and dialect are character facts that must persist across every scene.
- `dialogue.voice.timbre` - Timbre is casting, and casting is not something to leave to a default seed.

### `movie.*` - 5

- `movie.credits` - Credit text is structural furniture the end chapter should build itself.
- `movie.lint` - Author-time warnings for crossed axis lines, impossible lens pairs and audio overruns.
- `movie.lora_stack` - Style and character LoRAs reach looks the base checkpoint cannot.
- `movie.rating` - Auto-populates the negative prompt and gates violence, gore and nudity tags.
- `movie.runtime_target_s` - Lets the resolver warn or auto-trim when the cut overruns intended length.

### `world.*` - 5

- `world.clock_time` - An exact hour lets sun angle and on-screen clocks agree across a scene.
- `world.precip_render` - How precipitation is actually drawn is a look decision separate from whether it falls.
- `world.signage_language` - On-screen text is a constant generation artefact and needs an explicit policy.
- `world.smell_note` - A sensory note the prompt builder can mine for haze, steam and colour cues.
- `world.wind_dir` - Wind without a direction makes every sway contradict the next shot.

### `grade.*` - 5

- `grade.animate` - A grade that moves during a shot is how a mood turns without a cut.
- `grade.animate_at_pct` - When the grade turns is the timing of the emotional beat.
- `grade.grain_size` - Grain size dates a film as sharply as any drawing decision.
- `grade.halation` - Red bleed around highlights is the signature of film-printed anime.
- `grade.lut_id` - A single LUT is the most reliable way to match an external reference look.

### `story.*` - 4

- `story.motif` - Ties a recurring image, colour and musical phrase together under one name.
- `story.theme_tags` - Thematic words that quietly bias imagery when a shot is under-specified.
- `story.title_card` - Cards are structural furniture and should not require a hand-built shot.
- `story.tonality_curve` - States how tone moves across a chapter so grade, music and pace can interpolate.

### `edit.*` - 3

- `edit.cut_on_action` - Cutting mid-movement hides the join between two independently generated clips.
- `edit.match_cut_target` - A match cut needs to name the shape it is matching, not just request one.
- `edit.montage` - Montage is a scene shape with its own pacing and music rules.

### `caption.*` - 3

- `caption.position` - Captions sometimes have to move to avoid the composition.
- `caption.sfx_captions` - Accessibility captions for sound are a distinct output from dialogue subtitles.
- `caption.signs_policy` - On-screen signage in another language needs a stated handling policy.

### `render.*` - 2

- `render.frame_interp` - Interpolation is how a low-fps generation reaches delivery fps, and it fights anime stepping.
- `render.order` - Render order decides how soon an author sees the shots that matter.

## Suggested order

1. **`layer.depth_map`** - unblocks per-plane blur, parallax, `dolly_zoom` and
   `rack_focus` in one piece of work. Depth Anything 3 is already installed, so this
   is the best value on the list by some distance.
2. **`char.emotion` into TTS** - the emotion presets already carry `voice_style` and
   `voice_rate`; routing them into the engines that accept an emotion vector is
   mostly plumbing.
3. **`audio.*` levels and ducking** - the soundscape presets carry bed, music and
   duck levels that nothing currently reads.
4. **`light.ratio` and `light.temp`** - bias the colour grade from the lighting
   preset instead of only emitting prompt tags.
5. **`weather.wind`** - needs particle motion, so it waits on video-level control
   and should be last.
