# Scene variables - the complete census

**461 variables** across 16 namespaces. Every one has a default, so a scene
that specifies nothing still renders. Set anything at MOVIE, CHAPTER, SCENE or SHOT
level; scenes inherit from chapters, chapters from the movie. Tags append down the
tree, everything else overrides.

Produced by a six-department census - cinematography, production design, performance,
sound, editing, story - plus three completeness passes: anime-specific conventions,
continuity across a whole film, and a non-programmer author listing what they would
try to type and be frustrated to find absent.

| status | meaning |
|---|---|
| `OK` | renders today (280) |
| `~` | partially honoured - the useful part works, the rest is advisory (155) |
| `TODO` | accepted and warned about, degrades to a named fallback (26) |

Nothing silently does nothing. A `TODO` variable compiles, prints one warning, falls
back to something stated, and points at `studio/roadmap/`.

---

## `movie.*` - 17

| variable | level | type | default | | what it does |
|---|---|---|---|---|---|
| `movie.aspect` | movie | enum: 16:9 \| 1.85:1 \| 2:1 \| 2.39:1 \| 4:3 \| 1:1 \| 9:16 | `16:9` | OK | Framing decision independent of pixel canvas that drives every composition default. |
| `movie.canvas` | movie | enum: 768x432 \| 832x480 \| 1024x576 \| 1280x720 \| 1920x1080 | `1280x720` | OK | Delivery resolution, separate from aspect and from the oversized render frame. |
| `movie.checkpoint` | any | string (model id) | `anime_sdxl_base` | OK | The image model is the true source of house style and must be overridable per chapter. |
| `movie.credits` | movie | list of [role, name] | `[]` | ~ | Credit text is structural furniture the end chapter should build itself. |
| `movie.fps` | movie | enum: 8 \| 12 \| 16 \| 24 \| 25 \| 30 \| 60 | `24` | OK | Fixes the frame clock every duration, ease and fx interval is quantised against. |
| `movie.language` | movie | enum: en \| ja \| zh \| ko \| es \| fr \| de \| other | `en` | OK | Sets TTS voice pools, caption font and on-screen signage language at once. |
| `movie.lint` | movie | bool | `true` | ~ | Author-time warnings for crossed axis lines, impossible lens pairs and audio overruns. |
| `movie.logline` | movie | string | `""` | OK | One sentence the resolver falls back on when a scene gives no description. |
| `movie.lora_stack` | any | list of [lora_id, weight] | `[]` | ~ | Style and character LoRAs reach looks the base checkpoint cannot. |
| `movie.negative` | any | list of tags | `[worst quality, low quality, bad anatomy, extra digits, watermark, text]` | OK | A global negative floor so no author has to remember the boilerplate. |
| `movie.prompt_budget` | movie | number (tokens) | `75` | OK | Caps prompt length so late variables cannot silently push out character tags. |
| `movie.prompt_priority` | any | enum: character_first \| world_first \| style_first \| balanced | `character_first` | OK | Decides what survives truncation when the prompt budget is hit. |
| `movie.rating` | movie | enum: g \| pg \| pg13 \| r | `pg13` | ~ | Auto-populates the negative prompt and gates violence, gore and nudity tags. |
| `movie.runtime_target_s` | movie | number (seconds) | `auto (sum of chapters)` | ~ | Lets the resolver warn or auto-trim when the cut overruns intended length. |
| `movie.seed_root` | movie | number | `auto (hash of movie.title)` | OK | One root seed makes a whole film reproducible and derives every per-shot seed. |
| `movie.tag_style` | movie | enum: danbooru \| natural \| hybrid | `danbooru` | OK | Decides whether resolved variables emit tags or prose, changing every prompt builder. |
| `movie.title` | movie | string | `Untitled` | OK | Names the film for slates, filenames and the optional title card. |

## `story.*` - 21

| variable | level | type | default | | what it does |
|---|---|---|---|---|---|
| `story.beat` | scene | enum: setup \| inciting \| rising \| complication \| turn \| climax \| falling \| resolution \| button \| breather | `rising` | OK | Dramatic function of the scene, driving shot-size and pacing defaults. |
| `story.chapter_role` | chapter | enum: cold_open \| ki \| sho \| ten \| ketsu \| act1 \| act2 \| act3 \| interlude \| epilogue \| credits | `auto (from position in structure)` | OK | One word tells pacing, music and grade what this chapter is for. |
| `story.content_flags` | any | list of enum: violence \| blood \| death \| injury \| flashing_lights \| body_horror \| drowning \| sexual_content \| substance_use | `[]` | OK | Drives content warnings and softens flash and strobe fx automatically. |
| `story.genre` | movie | enum: slice_of_life \| drama \| romance \| comedy \| action \| thriller \| horror \| mystery \| fantasy \| sci_fi \| mecha \| sports \| isekai \| historical \| supernatural \| documentary | `slice_of_life` | OK | Seeds defaults for pace, lens, grade, music and sound across the film. |
| `story.mood` | any | enum: neutral \| warm \| hopeful \| lonely \| anxious \| grieving \| angry \| euphoric \| numb \| nostalgic \| ominous \| intimate \| chaotic | `neutral` | OK | Scene-level emotional colour biasing tags, grade, music and lighting together. |
| `story.mood_intensity` | any | number 0.0-1.0 | `0.5` | OK | Separates faint unease from panic without changing the mood word. |
| `story.motif` | any | list of named motif ids | `[]` | ~ | Ties a recurring image, colour and musical phrase together under one name. |
| `story.narrator` | any | enum: none \| char_vo \| omniscient_vo \| text_card \| diary \| letter | `none` | OK | Declares that voice-over exists so the mix reserves headroom for it. |
| `story.pov` | scene | enum: objective \| subjective \| first_person \| omniscient \| unreliable \| shared | `objective` | OK | Decides whose experience the camera, sound and grade are aligned to. |
| `story.pov_char` | scene | string (char.id) | `auto (first character present)` | OK | Names whose eyeline, hearing perspective and emotional grade the scene follows. |
| `story.reality_layer` | scene | enum: real \| dream \| memory \| flashback \| hallucination \| imagined \| story_within \| digital \| afterlife | `real` | OK | Non-real layers need a consistent visual and audio treatment applied automatically. |
| `story.register` | any | enum: naturalistic \| heightened \| stylised \| melodrama \| comedic_broad \| poetic \| clinical \| mythic | `naturalistic` | OK | How big performance, camera and music may be, separate from what they express. |
| `story.scene_goal` | scene | string | `""` | OK | One line of intent the prompt builder mines when a shot has no description. |
| `story.structure` | movie | enum: kishotenketsu \| three_act \| four_act \| vignette \| loop \| anthology \| freeform | `kishotenketsu` | OK | Gives chapters default dramatic roles so pacing and music arcs can be derived. |
| `story.tension` | scene | number 0.0-1.0 | `0.4` | OK | One dial cut rate, music intensity, shake and contrast can all key off. |
| `story.theme_tags` | movie | list of tags | `[]` | ~ | Thematic words that quietly bias imagery when a shot is under-specified. |
| `story.time_position` | scene | enum: linear \| earlier \| later \| parallel \| timeless \| recurring | `linear` | OK | Tells the viewer-facing devices (cards, grade shifts, reprise) when we are. |
| `story.title_card` | any | enum: none \| main_title \| chapter_title \| location_card \| time_card \| end_card | `none` | ~ | Cards are structural furniture and should not require a hand-built shot. |
| `story.tonality_curve` | chapter | enum: flat \| rising \| falling \| arc \| inverted_arc \| bittersweet \| whiplash \| spiral | `arc` | ~ | States how tone moves across a chapter so grade, music and pace can interpolate. |
| `story.tone` | any | enum: earnest \| wistful \| melancholy \| tender \| tense \| dread \| playful \| comedic \| absurd \| cold \| bittersweet \| triumphant \| eerie \| serene \| savage | `earnest` | OK | The single tonality word every department reads when nothing more specific is set. |
| `story.type` | movie | enum: short \| episode \| feature \| music_video \| trailer \| pv \| loop \| anthology | `short` | OK | Sets structural expectations, default scene lengths and whether an ending is required. |

## `edit.*` - 12

| variable | level | type | default | | what it does |
|---|---|---|---|---|---|
| `edit.audio_lead_s` | shot | number (seconds, negative = J-cut) | `0` | OK | Letting sound arrive before picture is the standard way to bind two shots. |
| `edit.chapter_transition` | chapter | enum: cut \| fade_black \| fade_white \| title_card \| iris \| long_dissolve | `fade_black` | OK | Chapter breaks are structural punctuation the audience must feel. |
| `edit.cut_on_action` | shot | bool | `true` | ~ | Cutting mid-movement hides the join between two independently generated clips. |
| `edit.insert_flash_frames` | shot | number (count) | `0` | OK | Subliminal single-frame inserts are a horror and memory device already renderable. |
| `edit.match_cut_target` | shot | string (shot id) or none | `none` | ~ | A match cut needs to name the shape it is matching, not just request one. |
| `edit.montage` | scene | enum: none \| time_passing \| training \| travel \| memory \| investigation \| ruin | `none` | ~ | Montage is a scene shape with its own pacing and music rules. |
| `edit.repeat` | shot | number (count) | `1` | OK | Repeating a cut is how a loop, a stutter or an obsession is edited. |
| `edit.scene_transition` | scene | enum: cut \| dissolve \| fade_black \| fade_white \| iris \| wipe \| match_cut \| smash \| time_card | `fade_black` | OK | Scene boundaries deserve a stronger default than shot boundaries. |
| `edit.transition_dir` | shot | enum: auto \| left \| right \| up \| down \| in \| out \| radial | `auto` | OK | Wipes, irises and whip pans are meaningless without a direction. |
| `edit.transition_in` | shot | enum: cut \| dissolve \| fade_black \| fade_white \| flash \| whip_pan \| wipe \| iris \| smash \| match_cut | `cut` | OK | How this shot arrives, authored on the shot that owns the change. |
| `edit.transition_out` | shot | enum: cut \| dissolve \| fade_black \| fade_white \| flash \| whip_pan \| wipe \| iris \| smash \| hold | `cut` | OK | How this shot leaves, so a scene's last shot can fade without a phantom shot. |
| `edit.transition_s` | any | number (seconds) | `0.5` | OK | Transition length is the difference between a blink and a chapter break. |

## `time.*` - 21

| variable | level | type | default | | what it does |
|---|---|---|---|---|---|
| `time.beat_grid` | scene | enum: free \| music_beat \| music_bar \| music_phrase \| metronome | `free` | TODO | Lets cuts snap to the generated music instead of floating against it. **Falls back to:** Cuts stay on authored times; the resolver reports nearest musical grid offsets. |
| `time.chain_overlap_frames` | any | number (frames) | `4` | ~ | Overlap between chained clips is the main lever on how visible a join is. |
| `time.chapter_s` | chapter | number (seconds) | `auto (sum of scenes)` | ~ | Chapter budget so a film can be shaped to a runtime from the top down. |
| `time.clip_chain` | shot | number (count of ~5s LTX clips) | `auto (ceil(time.shot_s / 5))` | ~ | Makes the renderer's chaining explicit so long shots are authored knowingly. |
| `time.cut_rate` | scene | number (shots per minute) | `auto (from time.pace)` | ~ | Numeric handle on editing density when the pace word is too coarse. |
| `time.fit_mode` | scene | enum: free \| fit_to_budget \| stretch_to_budget \| trim_tail \| drop_lowest_priority | `free` | ~ | Says what happens when authored shots do not add up to the declared scene length. |
| `time.freeze_at_pct` | shot | number (0-100) | `50` | OK | Where a freeze lands is the whole joke or the whole impact. |
| `time.freeze_hold_s` | shot | number (seconds) | `0.4` | OK | How long a freeze holds separates a stutter from a title beat. |
| `time.hold_in_s` | shot | number (seconds) | `0.2` | OK | A held beat before motion starts makes a cut land instead of lurching. |
| `time.hold_out_s` | shot | number (seconds) | `0.2` | OK | Settling before the cut makes the outgoing frame feel composed. |
| `time.max_shot_s` | movie | number (seconds) | `12` | OK | Ceiling keeping a single LTX chain from drifting beyond usable coherence. |
| `time.min_shot_s` | movie | number (seconds) | `0.5` | OK | Floor that stops generated pacing producing unreadable flash cuts. |
| `time.pace` | any | enum: languid \| slow \| steady \| brisk \| fast \| frantic | `steady` | OK | One inheritable word setting default shot lengths and cut rate for a sequence. |
| `time.post_roll_s` | scene | number (seconds) | `0` | OK | Tail after the last shot so a scene can end on held air. |
| `time.pre_roll_s` | scene | number (seconds) | `0` | OK | Silent lead-in before the first shot for breathing room after a transition. |
| `time.rhythm` | scene | enum: even \| accelerating \| decelerating \| syncopated \| stuttered \| long_short \| breathing | `even` | ~ | Shot-length pattern is what makes an edit feel composed rather than uniform. |
| `time.scene_s` | scene | number (seconds) | `auto (sum of shots, else 30)` | ~ | The scene-length control, usable as a budget shots are fitted into. |
| `time.shot_s` | shot | number (seconds) | `auto (from shot.purpose, else 5)` | OK | Clip length; every camera ease, fx keyframe and audio cue depends on it. |
| `time.speed` | shot | number (playback rate, 0.1-4.0) | `1.0` | OK | Straight retime of the rendered clip, the cheapest slow-motion available. |
| `time.speed_ramp` | shot | enum: none \| ramp_down \| ramp_up \| freeze_then_go \| slowmo_hit \| stutter \| ramp_in_out | `none` | OK | Time manipulation is core anime action grammar and needs a first-class name. |
| `time.sync_to_music` | shot | bool | `false` | TODO | Marks the individual shots that must land on a musical hit. **Falls back to:** Ignored; shot uses its authored duration. |

## `world.*` - 27

| variable | level | type | default | | what it does |
|---|---|---|---|---|---|
| `world.air_particles` | scene | list of enum: none \| dust \| pollen \| petals \| ash \| embers \| snow \| leaves \| bubbles \| fireflies \| steam \| spores | `[]` | OK | Drifting particles are the standard anime way to fill dead air in a frame. |
| `world.ambient_life` | scene | list of enum: none \| cicadas \| birds \| crickets \| frogs \| wind_chimes \| distant_traffic \| school_noise \| machinery \| waves \| river | `auto (from biome and season)` | OK | Living background sound is what makes a location feel inhabited between lines. |
| `world.biome` | scene | enum: urban \| suburb \| rural \| school \| coastal \| mountain \| forest \| desert \| snowfield \| industrial \| transit \| domestic \| fantasy_realm \| space \| ruins | `urban` | OK | Coarse world class from which dressing, ambience and practicals are seeded. |
| `world.celestial` | scene | enum: none \| sun_visible \| moon_full \| moon_crescent \| stars \| comet \| eclipse \| twin_moons | `none` | OK | A visible sun or moon anchors direction, time and often the whole composition. |
| `world.clock_time` | scene | string (HH:MM) or none | `none` | ~ | An exact hour lets sun angle and on-screen clocks agree across a scene. |
| `world.cloud_cover` | scene | number 0.0-1.0 | `auto (from world.weather)` | OK | Cloud cover decides shadow hardness even when weather is otherwise clear. |
| `world.crowd_density` | scene | enum: empty \| sparse \| moderate \| busy \| packed | `sparse` | OK | How populated a place is changes composition, ambience and generation difficulty. |
| `world.era` | movie | enum: ancient \| feudal \| victorian \| early_20c \| showa \| modern \| near_future \| far_future \| post_apocalyptic \| timeless | `modern` | OK | Period drives architecture, wardrobe, props and signage without per-shot tagging. |
| `world.fog_density` | scene | number 0.0-1.0 | `0` | OK | Atmospheric depth is the cheapest way to separate planes in a painting. |
| `world.ground_state` | scene | enum: dry \| damp \| wet_reflective \| puddled \| muddy \| snow \| ice \| sand \| grass \| tatami \| tile | `dry` | OK | Wet ground doubles the light in a night scene and must be stated, not implied. |
| `world.interior_exterior` | scene | enum: interior \| exterior \| threshold \| vehicle \| underground \| underwater \| aerial \| void | `exterior` | OK | Interior or exterior decides light motivation, reverb and weather visibility at once. |
| `world.place` | scene | string (description or tags) | `""` | OK | Where we are is the first thing a background prompt needs. |
| `world.place_id` | scene | string (location id) | `auto (hash of world.place)` | OK | A named location lets every scene there share plates, light and ambience. |
| `world.precip_render` | shot | enum: none \| tag_only \| streaks \| droplets_on_lens \| splashes \| drawn_lines \| sheet_rain | `tag_only` | ~ | How precipitation is actually drawn is a look decision separate from whether it falls. |
| `world.scale_cue` | shot | enum: none \| human_figure \| vehicle \| building \| horizon \| giant_object | `none` | OK | Anime sells scale by putting a known object in frame, not by focal length. |
| `world.season` | any | enum: spring \| early_summer \| summer \| late_summer \| autumn \| winter \| rainy_season \| dry_season | `spring` | OK | Season sets foliage, wardrobe, light angle and ambience in one word. |
| `world.set_dressing` | scene | list of tags | `[]` | OK | Named props and furniture keep a location recognisable across shots. |
| `world.signage_language` | any | enum: inherit \| ja \| en \| none \| invented \| blurred | `inherit` | ~ | On-screen text is a constant generation artefact and needs an explicit policy. |
| `world.sky_state` | shot | enum: auto \| clear_blue \| cirrus \| cumulus \| storm \| sunset_gradient \| starfield \| moonlit \| red_sky \| no_sky | `auto` | OK | The sky is a designed graphic element in anime, not a byproduct of weather. |
| `world.smell_note` | scene | string | `""` | ~ | A sensory note the prompt builder can mine for haze, steam and colour cues. |
| `world.tech_level` | any | enum: pre_industrial \| industrial \| electric \| digital \| networked \| cyber \| spacefaring \| magitech | `digital` | OK | Separates technology from period so a fantasy world can carry modern devices. |
| `world.time_of_day` | scene | enum: pre_dawn \| dawn \| morning \| midday \| afternoon \| golden_hour \| dusk \| blue_hour \| night \| deep_night | `afternoon` | OK | Time of day is the single strongest driver of colour temperature and mood. |
| `world.traffic` | scene | enum: none \| occasional \| steady \| congested \| rush | `none` | OK | Vehicle presence drives background motion, ambience and passing-light cues. |
| `world.weather` | scene | enum: clear \| fair \| overcast \| rain \| drizzle \| downpour \| thunderstorm \| snow \| blizzard \| fog \| mist \| wind \| heat_haze \| sandstorm \| ash \| aurora | `clear` | OK | The weather variable the author asked for, seeding light, particles and ambience. |
| `world.weather_intensity` | scene | number 0.0-1.0 | `0.5` | OK | Drizzle and downpour are the same word at different strengths. |
| `world.wind_dir` | scene | enum: none \| l_to_r \| r_to_l \| toward_camera \| away \| swirling \| updraft | `none` | ~ | Wind without a direction makes every sway contradict the next shot. |
| `world.wind_speed` | scene | enum: still \| breeze \| steady \| gusty \| strong \| gale | `breeze` | OK | Wind drives hair, cloth, foliage and particle motion prompts together. |

## `layer.*` - 17

| variable | level | type | default | | what it does |
|---|---|---|---|---|---|
| `layer.bg.blur` | shot | number 0.0-1.0 | `auto (from shot.focus.bg_blur)` | ~ | Per-plane blur is what actually separates a character from the world. |
| `layer.bg.content` | scene | string (description or tags) | `auto (from world.place and world.biome)` | OK | The background is most of the frame and should be authored once per scene. |
| `layer.bg.motion` | shot | enum: static \| drift \| parallax_slow \| parallax_fast \| scroll_l \| scroll_r | `static` | TODO | A moving background plane is the signature of the anime pan. **Falls back to:** Renders as a single-plane push or pan on the flat keyframe. |
| `layer.bg.render` | any | enum: sketch \| simple \| detailed \| ultra_detailed \| painted_bg \| photobash | `detailed` | OK | Background finish level is a deliberate contrast tool against character line quality. |
| `layer.bg.value` | shot | enum: darker \| matched \| lighter \| washed \| silhouette | `matched` | ~ | Tonal separation between planes is how a frame reads at a glance. |
| `layer.character_plane` | shot | enum: fg \| mid \| bg \| between_fg_mid | `mid` | ~ | Says which plane the subject occupies so blur and parallax treat them correctly. |
| `layer.count` | shot | number (1-5) | `2` | ~ | Declares how many depth planes exist, the root of the whole layers feature. |
| `layer.depth_map` | shot | string (path) or auto | `none` | TODO | An explicit depth pass is the prerequisite for real per-plane blur and parallax. **Falls back to:** Not generated; all depth effects fall back to tags. |
| `layer.fg.blur` | shot | number 0.0-1.0 | `0.6` | ~ | Foreground elements read as foreground mainly because they are soft. |
| `layer.fg.content` | shot | enum or string: none \| foliage \| railing \| crowd \| glass \| curtain \| doorframe \| rain \| dust \| shoulder \| hand \| custom | `none` | OK | A foreground occluder is the cheapest way to make a flat generation feel deep. |
| `layer.fg.coverage` | shot | number 0.0-1.0 | `0.2` | ~ | How much of the frame the occluder eats, from a hint to a near-total block. |
| `layer.fg.motion` | shot | enum: static \| sway \| pass_through \| drift \| parallax | `static` | ~ | Something crossing the lens is the strongest depth cue in a moving clip. |
| `layer.mid.content` | scene | string (description or tags) | `auto (from world dressing)` | OK | The midground is where the set lives and where characters stand. |
| `layer.mid.occupancy` | shot | number 0.0-1.0 | `0.4` | ~ | How much midground clutter sits between camera and background. |
| `layer.mode` | any | enum: baked \| tag_hinted \| masked \| generated_separate | `tag_hinted` | TODO | Says whether layers are only described or actually rendered and composited apart. **Falls back to:** tag_hinted works today; masked and generated_separate degrade to it with a warning. |
| `layer.parallax_strength` | shot | number 0.0-1.0 | `0` | TODO | How far the planes separate during a move, the whole point of 2.5D. **Falls back to:** Ignored; the move applies uniformly to the flat frame. |
| `layer.sky_plane` | shot | bool | `auto (true when sky visible)` | TODO | Sky as its own plane lets clouds move while the ground stays locked. **Falls back to:** Sky renders inside the background plate. |

## `light.*` - 23

| variable | level | type | default | | what it does |
|---|---|---|---|---|---|
| `light.ambient_level` | scene | number 0.0-1.0 | `0.5` | OK | Overall base illumination, the difference between night and unreadable night. |
| `light.animate` | shot | enum: none \| flicker \| pulse \| strobe \| passing_lights \| lightning \| breathing_glow \| candle \| tv_wash | `none` | ~ | Living light stops a still-derived clip feeling like a moving photograph. |
| `light.animate_rate` | shot | number (Hz) | `2` | ~ | A candle flicker and a police strobe are the same effect at different rates. |
| `light.bloom` | shot | number 0.0-1.0 | `0.15` | OK | Highlight blooming makes anime highlights luminous rather than clipped. |
| `light.continuity_lock` | scene | bool | `true` | ~ | Light must not re-roll between cuts in one location or the scene stops cohering. |
| `light.contrast_scheme` | scene | enum: neutral \| warm_key_cool_fill \| cool_key_warm_rim \| teal_orange \| magenta_cyan \| sodium_night \| monochrome_wash \| candle_vs_moon | `neutral` | OK | Colour contrast between key and fill gives depth without extra lights. |
| `light.exposure_ev` | shot | number (stops, -3..+3) | `0` | OK | Per-shot exposure trim keeps a sequence matched when the generator drifts. |
| `light.eye_light` | shot | enum: none \| subtle \| strong \| anime_sparkle \| dead_flat | `subtle` | OK | Catchlights separate a living character from a doll, and killing them reads as death or menace. |
| `light.eye_shadow_bar` | shot | enum: none \| half \| full \| glint_only | `none` | OK | The shadow bar across the eyes is anime's standard dread and villainy device. |
| `light.fill` | scene | enum: none \| bounce \| soft_fill \| negative_fill \| ambient_sky | `bounce` | ~ | Explicit fill separates a moody frame from a muddy one. |
| `light.god_rays` | shot | enum: none \| subtle \| strong \| dusty \| underwater | `none` | OK | Visible light shafts are a stock anime beat deserving a first-class name. |
| `light.haze` | scene | number 0.0-1.0 | `0` | ~ | Atmospheric haze is what makes shafts, depth and distance visible at all. |
| `light.key_dir` | shot | enum: front \| front_l \| front_r \| side_l \| side_r \| back_l \| back_r \| back \| top \| bottom \| ambient_none | `front_l` | OK | Key direction is the primary shape of a face and must be shot-addressable. |
| `light.key_elev` | shot | enum: below \| eye \| above \| steep_above \| overhead | `above` | OK | Underlighting versus toplighting reads as horror versus grace. |
| `light.motivation` | scene | enum: sun \| moon \| sky_ambient \| practical \| firelight \| screen_glow \| neon \| fluorescent \| streetlamp \| headlights \| magic \| bioluminescence \| unmotivated \| mixed | `auto (from world.time_of_day and world.interior_exterior)` | OK | One scene-level answer to where light comes from, seeding direction, colour and quality. |
| `light.practicals` | scene | list of enum: neon_sign \| desk_lamp \| ceiling_fluoro \| candle \| fireplace \| monitor \| phone_screen \| streetlight \| lantern \| headlights \| moon_window \| stage_light \| vending_machine | `auto (from world.time_of_day and world.biome)` | OK | In-frame sources declared once keep every shot agreeing where glow comes from. |
| `light.quality` | scene | enum: hard \| medium \| soft \| very_soft \| overcast_flat \| specular_wet | `auto (hard for sun, very_soft for overcast)` | OK | Shadow edge hardness sets the emotional temperature of a whole location. |
| `light.ratio` | scene | enum: flat_1_1 \| low_2_1 \| normal_4_1 \| dramatic_8_1 \| chiaroscuro_16_1 \| silhouette | `low_2_1` | ~ | Key-to-fill ratio is the numeric handle on drama. |
| `light.rim` | shot | enum: none \| subtle \| strong \| halo \| kiss \| double_rim | `subtle` | OK | Rim light is the defining separation device of anime and should be on by default. |
| `light.rim_color` | shot | string (hex or named colour) | `warm_white` | ~ | A coloured rim ties a character to the location's neon, fire or moonlight. |
| `light.shadow_density` | scene | number 0.0-1.0 | `0.5` | ~ | How black the blacks go, separate from overall contrast. |
| `light.shadow_gobo` | scene | enum: none \| blinds \| foliage \| branches \| grate \| curtain \| crowd \| rain_streaks \| water_caustics \| window_cross | `none` | OK | Patterned shadow is the highest-value-per-token lighting device in tag space. |
| `light.temp_k` | scene | number (Kelvin, 1500-12000) | `auto (from light.motivation and world.time_of_day)` | OK | Colour temperature is the most reliable time-of-day and interior signal. |

## `grade.*` - 22

| variable | level | type | default | | what it does |
|---|---|---|---|---|---|
| `grade.animate` | shot | enum: none \| to_warm \| to_cool \| to_desat \| to_dark \| to_bright \| to_preset | `none` | ~ | A grade that moves during a shot is how a mood turns without a cut. |
| `grade.animate_at_pct` | shot | number (0-100) | `50` | ~ | When the grade turns is the timing of the emotional beat. |
| `grade.black_point` | any | number 0.0-0.2 | `0` | OK | Where black actually starts, which decides how deep a night reads. |
| `grade.contrast` | any | number 0.5-2.0 | `1.0` | OK | Direct contrast trim on top of the preset, the most-used grade adjustment. |
| `grade.curve` | any | enum: linear \| film_s \| soft_s \| strong_s \| lifted_matte \| crushed \| inverted | `soft_s` | OK | The tone curve shape is the personality of a grade, above any single slider. |
| `grade.gain` | any | number 0.5-2.0 | `1.0` | OK | Highlight scaling so a bright sky can be tamed without crushing the face. |
| `grade.gamma` | any | number 0.5-2.0 | `1.0` | OK | Midtone weight, where a face's brightness actually lives. |
| `grade.grain` | any | number 0.0-1.0 | `0.08` | OK | A little grain unifies generated frames and hides model artefacts. |
| `grade.grain_size` | any | enum: fine \| normal \| coarse \| clumpy | `normal` | ~ | Grain size dates a film as sharply as any drawing decision. |
| `grade.halation` | any | number 0.0-1.0 | `0.1` | ~ | Red bleed around highlights is the signature of film-printed anime. |
| `grade.highlight_hue` | any | string (hex or named colour) | `none` | OK | Tinted highlights carry time of day more convincingly than midtones. |
| `grade.lift` | any | number -0.2..0.2 | `0` | OK | Lifting blacks is the whole difference between digital video and film. |
| `grade.lut_id` | any | string (lut id) or none | `none` | ~ | A single LUT is the most reliable way to match an external reference look. |
| `grade.match_ref` | shot | string (shot id or image) or none | `none` | TODO | Matching one shot's grade to another is the routine fix for a mismatched cut. **Falls back to:** Copies the reference's grade values verbatim; no histogram matching. |
| `grade.preset` | any | enum: neutral \| warm_film \| cool_film \| teal_orange \| bleach_bypass \| sepia \| monochrome \| high_key \| low_key \| faded_memory \| night_blue \| sodium_street \| pastel_soft \| vivid_pop \| horror_green | `neutral` | OK | The look variable, one word that sets an entire eq/curves stack. |
| `grade.saturation` | any | number 0.0-2.0 | `1.0` | OK | Desaturation is the fastest signal for memory, illness and drained hope. |
| `grade.scope` | any | enum: full_frame \| exclude_characters \| shadows_only \| highlights_only \| hue_range | `full_frame` | TODO | Grading everything equally is what destroys locked character colours. **Falls back to:** Only full_frame runs; others warn and apply full_frame with reduced strength. |
| `grade.shadow_hue` | any | string (hex or named colour) | `none` | OK | Tinted shadows are the core of a designed anime palette. |
| `grade.sharpen` | any | number 0.0-1.0 | `0.1` | OK | Video passes soften lines and a small sharpen restores anime's edge. |
| `grade.temp_shift` | any | number -100..100 | `0` | OK | Warm/cool trim per shot keeps cuts matched when generations drift. |
| `grade.tint_shift` | any | number -100..100 | `0` | OK | Green/magenta trim is what fixes fluorescent and neon scenes. |
| `grade.white_point` | any | number 0.8-1.2 | `1.0` | OK | Ceiling control that stops whiteouts clipping into mush. |

## `shot.*` - 80

| variable | level | type | default | | what it does |
|---|---|---|---|---|---|
| `shot.action` | shot | string (short description) | `""` | OK | Free-text beat description filling any gap the structured variables leave. |
| `shot.cam.angle` | shot | enum: level \| low \| high \| birds_eye \| worms_eye \| top_down \| dutch | `level` | OK | Tilt relative to the subject is the classic dominance lever. |
| `shot.cam.dutch_deg` | shot | number (degrees, -45..45) | `0` | ~ | Continuous amount for the dutch angle instead of a binary on/off. |
| `shot.cam.height` | shot | enum: ground \| ankle \| knee \| waist \| chest \| eye \| high \| overhead \| aerial | `eye` | OK | Camera height reads as power and scale, authored independently of tilt. |
| `shot.cam.motion_blur` | shot | number 0.0-1.0 | `0.3` | TODO | Direct override when shutter angle is too indirect for the author. **Falls back to:** Drives smear fx strength only; LTX supplies whatever native blur it produces. |
| `shot.cam.move` | shot | enum: static \| push \| pull \| pan_l \| pan_r \| tilt_u \| tilt_d \| handheld \| zoom_in \| zoom_out \| dolly_l \| dolly_r \| crane_up \| crane_down \| orbit_l \| orbit_r \| whip_pan \| roll \| rack_zoom \| follow | `static` | ~ | The core motion verb, extending eight native moves to what directors ask for. |
| `shot.cam.move_amount` | shot | number (percent of frame travelled) | `8` | OK | Speed alone cannot distinguish a 3% breathing push from a 40% lunge. |
| `shot.cam.move_anchor` | shot | enum: center \| face \| subject \| thirds_l \| thirds_r \| horizon \| custom_xy | `center` | ~ | A push to frame centre and a push to a character's eye are different shots. |
| `shot.cam.move_ease` | shot | enum: linear \| ease_in \| ease_out \| ease_in_out \| snap \| overshoot \| settle | `ease_in_out` | ~ | Linear moves are the tell of machine-made footage; easing feels operated. |
| `shot.cam.move_end_pct` | shot | number (0-100 of duration) | `100` | ~ | Lets a move settle before the cut. |
| `shot.cam.move_speed` | shot | enum: still \| crawl \| slow \| medium \| fast \| whip | `slow` | OK | Separates how fast from what direction so one move serves whisper and chase. |
| `shot.cam.move_start_pct` | shot | number (0-100 of duration) | `0` | ~ | Lets a move begin after a held beat instead of always on the cut. |
| `shot.cam.rig` | any | enum: locked \| tripod \| handheld_light \| handheld_heavy \| shoulder \| steadicam \| gimbal \| drone \| crane \| dolly_track | `locked` | ~ | Baseline motion texture for a sequence so every shot needn't set shake. |
| `shot.cam.rolling_shutter` | any | number 0.0-1.0 | `0` | TODO | Skew on fast pans is a specific found-footage signature some films want. **Falls back to:** Ignored. |
| `shot.cam.shake_amp` | shot | number 0.0-1.0 | `0` | OK | Explicit instability for impacts and panic without changing the move type. |
| `shot.cam.shake_freq` | shot | enum: slow_drift \| breath \| walk \| run \| impact \| rumble | `breath` | ~ | Amplitude without frequency gives every shake the same character. |
| `shot.cam.shutter_angle` | any | enum: 45 \| 90 \| 180 \| 270 \| 360 | `180` | TODO | How crisp or smeared motion reads, the difference between a war film and a dream. **Falls back to:** Buckets into smear fx amount; 45 renders as none, 360 as heavy. |
| `shot.cam.subject_distance_m` | shot | number (metres) | `3` | ~ | Ties focal length and shot size together so the pair stays coherent. |
| `shot.cam.zoom_kind` | shot | enum: optical_feel \| digital_crop | `digital_crop` | OK | Documents that post zooms crop resolution, which is why overscan matters. |
| `shot.cfg` | any | number (1.0-12.0) | `6.0` | OK | Prompt adherence versus image quality, the main generation trade-off. |
| `shot.comp.axis_line` | scene | string (named axis id) | `auto` | TODO | Declares the 180-degree line so reverses can be checked rather than eyeballed. **Falls back to:** Author-time lint warning only; render unchanged. |
| `shot.comp.balance` | shot | enum: symmetrical \| asym_left \| asym_right \| weighted_bottom \| weighted_top \| diagonal \| radial \| chaotic | `asym_left` | ~ | Visual weight distribution is what an author means when a frame feels wrong. |
| `shot.comp.depth_stack` | shot | enum: flat \| two_plane \| three_plane \| deep_stack | `two_plane` | ~ | How many depth planes the frame is built from; the contract with layer variables. |
| `shot.comp.eyeline` | shot | enum: into_lens \| left \| right \| up \| down \| off_left \| off_right \| closed \| at_object | `off_left` | OK | Where a character looks carries the emotional read and stitches reverses together. |
| `shot.comp.frame_in_frame` | shot | enum: none \| doorway \| window \| mirror \| foliage \| crowd \| curtain \| tunnel \| fence | `none` | OK | Framing a character inside an in-world aperture compactly states confinement. |
| `shot.comp.headroom` | shot | enum: tight \| normal \| loose \| cropped_top | `normal` | ~ | The most common framing error and the most common deliberate tension device. |
| `shot.comp.horizon` | shot | enum: none \| low \| lower_third \| center \| upper_third \| high | `lower_third` | ~ | Horizon placement sets whether a character dominates sky or is crushed by ground. |
| `shot.comp.leading_lines` | shot | enum: none \| one_point \| diagonal \| radial \| vertical \| horizontal \| spiral \| converging_rails | `none` | ~ | Directed lines tell the eye where to go and anime backgrounds lean on them. |
| `shot.comp.lookroom` | shot | enum: auto \| left \| right \| center \| none | `auto` | ~ | Space in front of a looking character makes a frame balanced or trapped. |
| `shot.comp.negative_space` | shot | number 0.0-1.0 | `0.3` | ~ | Emptiness is the loudest tool for loneliness and dread and needs a dial. |
| `shot.comp.perspective` | shot | enum: flat \| one_point \| two_point \| three_point \| isometric \| fisheye \| overhead_map | `two_point` | ~ | Perspective construction is an explicit background-art decision in anime. |
| `shot.comp.screen_direction` | scene | enum: l_to_r \| r_to_l \| to_camera \| away_from_camera \| static | `static` | ~ | Keeps travel and chase geometry consistent instead of flipping randomly. |
| `shot.comp.subject_scale` | shot | number 0.0-1.0 (fraction of frame height) | `0.5` | ~ | Continuous control between the coarse steps of shot.size. |
| `shot.comp.thirds_bias` | shot | enum: center \| left_third \| right_third \| golden_l \| golden_r \| symmetrical \| edge_left \| edge_right | `center` | ~ | Where the subject sits laterally is the composition choice authors most want. |
| `shot.facing` | shot | enum: to_camera \| three_quarter_left \| three_quarter_right \| profile_left \| profile_right \| back_three_quarter \| back | `three_quarter_left` | OK | Body orientation is a separate axis from camera angle and the main read on a character. |
| `shot.focus.behavior` | shot | enum: locked \| rack_to_bg \| rack_to_fg \| follow_subject \| soft_throughout \| snap_focus | `locked` | TODO | A rack focus is a dramatic beat that currently cannot be authored at all. **Falls back to:** Two keyframes joined by a short dissolve, or a single end-focus frame with a warning. |
| `shot.focus.bg_blur` | shot | number 0.0-1.0 | `0.25` | ~ | Continuous background separation that survives even without true dof. |
| `shot.focus.dof` | shot | enum: deep \| medium \| shallow \| very_shallow \| split_diopter | `medium` | ~ | How much of the world is sharp is the fastest character/background separation. |
| `shot.focus.fg_blur` | shot | number 0.0-1.0 | `0` | ~ | Soft foreground occluders are the cheapest depth cue in the language. |
| `shot.focus.point` | shot | enum: eyes \| face \| subject \| hands \| prop \| foreground \| midground \| background \| hyperfocal | `face` | ~ | Names what must be sharp so generator and blur pass agree on the subject. |
| `shot.focus.rack_at_pct` | shot | number (0-100) | `50` | TODO | A rack that lands on a line of dialogue needs its timing authored. **Falls back to:** Ignored; the substitute dissolve is centred. |
| `shot.focus.softness` | any | number 0.0-1.0 | `0` | ~ | Global softness for flashbacks and dreams, independent of depth. |
| `shot.frame.aspect_override` | shot | enum: inherit \| 16:9 \| 1.85:1 \| 2:1 \| 2.39:1 \| 4:3 \| 1:1 \| 9:16 | `inherit` | OK | A single shot in a different ratio shouldn't restructure the chapter. |
| `shot.frame.caption_safe` | movie | enum: bottom_10 \| bottom_15 \| bottom_20 \| top \| none | `bottom_15` | OK | Reserves the zone burnt-in captions occupy so compositions survive delivery. |
| `shot.frame.letterbox` | any | enum: none \| bars_2_39 \| bars_2_1 \| pillars_4_3 \| dynamic_widen | `none` | OK | Aspect change as a dramatic device needs to be authorable mid-film. |
| `shot.framing_type` | shot | enum: single \| two_shot \| three_shot \| group \| over_shoulder \| pov \| reaction \| insert_object \| empty_frame \| crowd | `single` | OK | How many bodies are in frame and from whose vantage, changing the whole tag stack. |
| `shot.fx` | shot | list of enum: punch \| shake \| aberr \| glow \| flash \| hot \| ramp \| smear \| whiteout | `[]` | OK | Direct access to the native fx set, appended down the hierarchy. |
| `shot.fx.bg_treatment` | shot | enum: matched \| watercolor \| photobash \| abstract_color \| radial_burst \| pattern \| void_black \| white_void \| emotional_wash | `matched` | OK | Dropping the real background for an emotional field is standard anime grammar. |
| `shot.fx.emote_symbols` | shot | list of enum: sweatdrop \| vein_pop \| blush_lines \| shock_lines \| sparkles \| teardrop \| steam \| question_mark \| chibi_pop | `[]` | OK | Anime's symbolic emotion vocabulary is a real expressive channel, not decoration. |
| `shot.fx.impact_frame` | shot | enum: none \| white_flash \| black_flash \| negative \| sketch_frame \| silhouette_pop | `none` | OK | The one-frame graphic hit is a defining anime action beat already supported. |
| `shot.fx.screentone` | shot | enum: none \| dots \| hatch \| gradient \| flash_lines \| mood_tone | `none` | ~ | Manga screentone as a mood device is a distinct look from film grain. |
| `shot.fx.speed_lines` | shot | enum: none \| radial \| horizontal \| vertical \| impact \| motion_trail | `none` | OK | Graphic motion overlays are native anime language with no photographic equivalent. |
| `shot.fx_at_pct` | shot | list of numbers (0-100) | `[0]` | OK | Where in the shot each effect fires, the whole timing of an impact. |
| `shot.fx_intensity` | shot | number 0.0-1.0 | `0.5` | OK | One strength dial so the same fx list can whisper or scream. |
| `shot.hero` | shot | bool | `false` | OK | Marks shots worth extra steps, upscaling and retries without setting each by hand. |
| `shot.keyframe_mode` | shot | enum: start_only \| start_end \| start_mid_end | `start_only` | ~ | Controls whether the shot is single-image i2v or interpolation between authored frames. |
| `shot.lens.bokeh_shape` | any | enum: circular \| hexagonal \| oval_anamorphic \| swirly \| cats_eye \| bloom_blobs | `circular` | TODO | Out-of-focus highlight shape is much of a night film's identity. **Falls back to:** Generic bokeh tag; shape ignored. |
| `shot.lens.breathing` | shot | number 0.0-1.0 | `0` | TODO | Focus pulls that change framing are a realism cue for handheld passages. **Falls back to:** Ignored; framing stays locked. |
| `shot.lens.compression` | shot | enum: expanded \| natural \| compressed \| hyper_compressed | `natural` | ~ | How flat the background stacks when focal length alone doesn't sell it. |
| `shot.lens.distortion` | any | enum: none \| mild_barrel \| strong_barrel \| fisheye \| pincushion | `none` | TODO | Wide-angle bulge is a deliberate anime device for panic and comedy. **Falls back to:** Baked as a fisheye/distortion tag; no post-warp pass. |
| `shot.lens.filtration` | any | enum: none \| light_diffusion \| pro_mist \| heavy_diffusion \| glimmer \| smoke_glass | `none` | ~ | Diffusion is the cheapest way to unify a look across shots and should inherit. |
| `shot.lens.flare` | shot | enum: none \| subtle \| anamorphic_streak \| warm_bloom \| starburst \| veiling | `none` | ~ | Flare is a mood signature authors reach for constantly. |
| `shot.lens.focal_mm` | shot | number (mm, 35mm-equivalent) | `auto (from shot.lens.look, else 50)` | ~ | A number authors think in, from which compression and dof defaults derive. |
| `shot.lens.look` | any | enum: ultra_wide \| wide \| normal \| portrait \| tele \| super_tele \| fisheye \| anamorphic \| macro | `normal` | ~ | Lets an author state the feel without knowing millimetres; this maps to tags. |
| `shot.lens.vignette` | any | number 0.0-1.0 | `0.10` | TODO | Corner falloff quietly focuses attention and is expected in cinematic grades. **Falls back to:** Global gamma pull plus a vignetting tag; no radial mask. |
| `shot.match_prev` | shot | enum: none \| match_frame \| match_action \| match_graphic \| match_eyeline \| match_light | `none` | ~ | Asks for a cut landing on the previous composition instead of hand-copying values. |
| `shot.motion_prompt` | shot | string | `auto (from action, camera and weather)` | OK | The text the i2v pass sees, a different sentence from the keyframe prompt. |
| `shot.motion_strength` | shot | number 0.0-1.0 | `0.4` | OK | How much the video model may move the frame, the main coherence dial. |
| `shot.negative_add` | any | list of tags | `[]` | OK | Scoped negatives so one artefact dies without touching the global list. |
| `shot.priority` | shot | enum: filler \| normal \| important \| critical | `normal` | OK | Tells budget allocators and trimmers which shots to sacrifice first. |
| `shot.purpose` | shot | enum: establish \| reveal \| react \| action \| dialogue \| transition \| detail \| beat \| mood \| insert | `beat` | OK | One word from which size, move, lens, duration and audio defaults derive. |
| `shot.reference` | any | string (image id or path) | `none` | ~ | A reference image is often faster and more reliable than any number of tags. |
| `shot.reference_weight` | any | number 0.0-1.0 | `0.6` | OK | How hard the reference pulls against the prompt, per shot. |
| `shot.retries` | any | number | `1` | OK | How many times a failed or rejected generation is re-rolled before giving up. |
| `shot.seed` | shot | number | `auto (seed_root + shot index)` | OK | Deterministic per-shot noise and the handle for re-rolling exactly one frame. |
| `shot.size` | shot | enum: extreme_close_up \| close_up \| medium_close_up \| medium \| medium_wide \| wide \| extreme_wide \| insert \| macro \| establishing | `medium` | OK | The most-used image decision; without it every keyframe is a random crop. |
| `shot.steps` | any | number | `28` | OK | Quality/time trade so hero shots can cost more than filler. |
| `shot.still` | shot | bool | `false` | OK | A held drawing with no video pass is legitimate anime and saves render time. |
| `shot.subject` | shot | list of char.id or object id | `auto (characters present, in order)` | OK | Names who the shot is about so face refs and focus target the right body. |
| `shot.tags` | any | list of tags (appends down the hierarchy) | `[]` | OK | The escape hatch that keeps the format from blocking a prompt the model can do. |

## `block.*` - 8

| variable | level | type | default | | what it does |
|---|---|---|---|---|---|
| `block.contact` | shot | enum: none \| near_touch \| hand_touch \| hand_hold \| embrace \| grab \| strike \| carry \| lean_on | `none` | ~ | Physical contact is the hardest thing to generate and must be explicitly asked for. |
| `block.distance` | shot | enum: intimate \| personal \| social \| public \| distant | `social` | OK | Proxemics is the fastest read on a relationship and needs its own word. |
| `block.entrance` | shot | enum: none \| walks_in_l \| walks_in_r \| enters_bg \| rises_into \| reveal_by_pan \| already_present | `already_present` | ~ | How a character arrives in frame is a directing choice, not an accident of generation. |
| `block.exit` | shot | enum: none \| walks_out_l \| walks_out_r \| exits_bg \| drops_out \| left_behind | `none` | ~ | Exits punctuate scenes and decide whether the next shot needs the character at all. |
| `block.group_shape` | shot | enum: line \| wedge \| cluster \| circle \| scattered \| tiered \| isolated_one | `cluster` | ~ | Group compositions fail without a stated shape and become tag soup. |
| `block.orientation` | shot | enum: facing \| angled \| side_by_side \| back_to_back \| one_turned_away \| over_shoulder | `angled` | OK | How two bodies face each other is a separate axis from where they stand. |
| `block.pattern` | scene | enum: static \| approach \| retreat \| circle \| side_by_side \| face_off \| pass_by \| cross \| gather \| scatter \| follow | `static` | ~ | The blocking variable, describing how bodies move relative to each other. |
| `block.positions` | shot | list of [char.id, screen_position] | `auto (from framing and order)` | ~ | Who stands where in frame is what makes reverses and group shots readable. |

## `char.*` - 39

| variable | level | type | default | | what it does |
|---|---|---|---|---|---|
| `char.age_read` | any | enum: child \| preteen \| teen \| young_adult \| adult \| middle_aged \| elderly \| ageless | `teen` | OK | Apparent age is a tag-level decision that must never drift between shots. |
| `char.arc_stage` | chapter | enum: introduced \| stable \| pressured \| breaking \| changed \| resolved \| absent | `stable` | ~ | Where a character sits in their arc biases wardrobe, grade and performance defaults. |
| `char.blush` | shot | number 0.0-1.0 | `0` | OK | Blush is a first-class emotional signal in anime, not an incidental detail. |
| `char.brow` | shot | enum: neutral \| raised \| furrowed \| one_raised \| flat \| pleading \| angry_v | `auto (from emotion)` | OK | Brows carry more of an anime face's read than the mouth does. |
| `char.build` | any | enum: petite \| slim \| average \| athletic \| stocky \| heavy \| tall_lean \| muscular | `average` | OK | Body type is part of a silhouette and is otherwise re-rolled every generation. |
| `char.condition` | any | enum: healthy \| tired \| injured \| bleeding \| ill \| soaked \| freezing \| overheated \| drunk \| possessed | `healthy` | OK | Physical state must persist across shots or continuity collapses. |
| `char.design_tags` | any | list of tags | `[]` | OK | The canonical appearance tag bundle re-injected into every prompt. |
| `char.distinguishing` | any | list of tags | `[]` | OK | Scars, moles, glasses and ahoge are the details that survive stylisation. |
| `char.emotion` | shot | enum: neutral \| happy \| sad \| angry \| afraid \| surprised \| disgusted \| contempt \| tender \| embarrassed \| determined \| exhausted \| numb \| anxious \| relieved \| joyful \| grieving | `neutral` | OK | The per-character emotion the author asked for, driving face, voice and pose together. |
| `char.emotion_intensity` | shot | number 0.0-1.0 | `0.5` | OK | Anger at 0.2 and 0.9 are different performances, not different emotions. |
| `char.emotion_mask` | shot | enum: none \| suppressed \| forced_smile \| fake_calm \| breaking \| deadpan \| performative | `none` | OK | A character hiding a feeling is a distinct expression from having it. |
| `char.emotion_secondary` | shot | enum: none \| plus any char.emotion value | `none` | ~ | Real performance is usually two feelings at once and the mix is the acting. |
| `char.energy` | shot | number 0.0-1.0 | `0.5` | OK | One dial for how much a body is doing, feeding motion strength and voice pace. |
| `char.expression` | shot | string (explicit face tags) | `auto (from char.emotion)` | OK | Direct override for when the derived expression is not the drawing wanted. |
| `char.eyes` | any | string (colour and shape tags) | `""` | OK | Eye colour and shape carry identity even when the face style changes. |
| `char.face_sheet` | any | string (image set id) | `none` | OK | The IPAdapter sheet is the only real mechanism for face consistency today. |
| `char.face_weight` | any | number 0.0-1.0 | `0.65` | OK | How hard the face reference pulls against expression and angle. |
| `char.face_weight_by_size` | any | list of [shot.size, weight] | `auto (lower on wide shots)` | ~ | A face lock that helps a close-up wrecks a wide, so it must vary by shot size. |
| `char.gaze_target` | shot | string (char.id, object id, camera, away) | `auto (from shot.comp.eyeline)` | ~ | Naming who is looked at keeps eyelines consistent across a reverse. |
| `char.gesture` | shot | string or enum: none \| pointing \| reaching \| covering_face \| clenched_fists \| hands_in_pockets \| arms_crossed \| waving \| bowing \| shielding \| holding_out | `none` | OK | Hands are where performance lives and where generation fails without direction. |
| `char.hair` | any | string (colour, length, style tags) | `""` | OK | Hair is the primary recognition cue in anime and must be locked explicitly. |
| `char.height_cm` | any | number | `165` | ~ | Relative height drives two-shot framing and eyeline geometry. |
| `char.id` | any | string | `auto (slug of char.name)` | OK | A stable handle every shot, line and face reference points at. |
| `char.lora` | any | string (lora id) or none | `none` | ~ | A trained character LoRA outperforms any tag bundle when one exists. |
| `char.mouth` | shot | enum: closed \| slight_open \| open \| wide_open \| smile \| smirk \| frown \| grimace \| gritted \| trembling \| wavy | `auto (from emotion)` | OK | Mouth shape must be separable from dialogue so silent reactions can be authored. |
| `char.movement` | shot | enum: still \| idle \| walking \| running \| sprinting \| turning \| rising \| sitting_down \| falling \| fighting \| dancing \| flying | `still` | OK | What the body does is the core of the i2v motion prompt. |
| `char.name` | any | string | `"Character"` | OK | Display name for captions, credits and speaker labels. |
| `char.posture` | shot | enum: standing \| slouched \| upright \| leaning \| sitting \| seiza \| crouched \| kneeling \| lying \| curled \| floating \| falling | `standing` | OK | Posture states character before the face is even visible. |
| `char.present` | scene | list of char.id | `[]` | OK | Declares who exists in the scene so shots can default their subjects. |
| `char.props_held` | shot | list of tags | `[]` | OK | What is in a character's hands drives both framing and hand-drawing failures. |
| `char.relationship` | scene | list of [char.id, char.id, relation] | `[]` | ~ | Blocking distance, eyelines and voice register all follow from who these people are to each other. |
| `char.role` | any | enum: lead \| deuteragonist \| support \| antagonist \| foil \| mentor \| extra \| crowd \| narrator | `support` | OK | Role decides prompt priority, face-weight budget and how often the character anchors a shot. |
| `char.skin` | any | string (tone tag) | `""` | OK | Skin tone drifts between generations unless it is restated each prompt. |
| `char.tears` | shot | enum: none \| welling \| single \| streaming \| wiped \| dried_tracks \| comedic_fountain | `none` | OK | Crying has discrete drawn stages that a generic emotion word cannot select. |
| `char.wear.accessories` | any | list of tags | `[]` | OK | Small repeated objects are identity anchors and often motif carriers. |
| `char.wear.colors` | any | list of colours | `auto (from anime.color.script)` | ~ | Costume colour must be locked or a character reads differently every scene. |
| `char.wear.layer` | any | list of enum: none \| coat \| jacket \| scarf \| hood \| apron \| armour \| cloak \| bag \| umbrella | `[]` | OK | Outer layers change silhouette and are added or removed as dramatic action. |
| `char.wear.outfit` | any | string (outfit id or tags) | `""` | OK | The wardrobe variable, inheritable so a chapter can change clothes once. |
| `char.wear.state` | shot | enum: neat \| casual \| rumpled \| soaked \| dusty \| bloodied \| torn \| burnt \| half_dressed \| formal | `neat` | OK | Costume condition is how a story's damage stays visible on screen. |

## `dialogue.*` - 24

| variable | level | type | default | | what it does |
|---|---|---|---|---|---|
| `dialogue.line.at_pct` | shot | number (0-100) | `auto (sequential)` | OK | Where a line starts inside the shot is timing, and timing is comedy and tension. |
| `dialogue.line.delivery` | shot | enum: neutral \| soft \| warm \| flat \| clipped \| urgent \| shouted \| whispered \| trembling \| laughing \| crying \| breathless \| sarcastic \| tender \| cold | `neutral` | ~ | How a line is said is the acting, and it is separable from the emotion word. |
| `dialogue.line.emotion` | shot | enum: inherit \| plus any char.emotion value | `inherit` | ~ | A line can carry a different feeling from the face, and that gap is the drama. |
| `dialogue.line.emotion_strength` | shot | number 0.0-1.0 | `0.5` | ~ | Emotion vectors need a magnitude or every line is maximally acted. |
| `dialogue.line.language` | shot | enum: inherit \| en \| ja \| zh \| ko \| es \| fr \| de \| other | `inherit` | OK | A single foreign line is common and needs its own voice and caption handling. |
| `dialogue.line.offscreen` | shot | enum: on_screen \| off_screen \| back_to_camera \| behind_door \| over_phone | `on_screen` | OK | Off-screen lines need different mixing and no mouth animation at all. |
| `dialogue.line.overlap` | shot | bool | `false` | OK | Overlapping speech is how arguments and crowds sound real. |
| `dialogue.line.pause_after_s` | shot | number (seconds) | `0.3` | OK | Trailing air decides whether a line lands or is stepped on. |
| `dialogue.line.pause_before_s` | shot | number (seconds) | `0.2` | OK | The beat before a line is often the performance. |
| `dialogue.line.pitch_shift` | shot | number (semitones, -6..6) | `0` | OK | Small pitch moves cover age, stress and non-human characters cheaply. |
| `dialogue.line.processing` | shot | enum: none \| phone \| radio \| pa \| tv \| muffled \| reverb \| underwater \| distorted | `none` | OK | Source colouring on a line is often the entire storytelling point. |
| `dialogue.line.rate` | shot | number 0.5-2.0 | `1.0` | OK | Speaking rate is character, and it also decides whether the line fits the shot. |
| `dialogue.line.speaker` | shot | string (char.id) | `auto (shot.subject first)` | OK | Every line needs an owner so voice, emotion and mouth follow the right body. |
| `dialogue.line.subtitle` | shot | string or auto | `auto (from text)` | OK | Subtitle text often differs from spoken text, especially across languages. |
| `dialogue.line.text` | shot | string | `""` | OK | The spoken text itself, feeding TTS, captions and flap timing. |
| `dialogue.line.volume` | shot | enum: whisper \| quiet \| normal \| raised \| shout \| scream | `normal` | OK | Volume changes both the performance and the mix, so it must be one field. |
| `dialogue.lines` | shot | list of line objects | `[]` | OK | The dialogue variable, holding what is actually said in this shot. |
| `dialogue.lipsync` | any | enum: none \| flap \| loose \| tight \| closed | `loose` | ~ | The lipsync variable, stating how hard mouth movement must match audio. |
| `dialogue.style` | any | enum: naturalistic \| formal \| archaic \| slangy \| terse \| florid \| childlike \| military \| keigo \| rough | `naturalistic` | OK | Speech register belongs above the line so a whole character or scene inherits it. |
| `dialogue.turn_gap_s` | scene | number (seconds) | `0.35` | OK | The gap between speakers is the rhythm of a conversation. |
| `dialogue.voice.accent` | any | string or none | `none` | ~ | Accent and dialect are character facts that must persist across every scene. |
| `dialogue.voice.engine` | any | enum: auto \| engine_a \| engine_b \| engine_emotion \| engine_ja | `auto` | OK | Engines differ in language and emotion support, so the choice must be authorable. |
| `dialogue.voice.id` | any | string (voice id) | `auto (from char.role, age_read and language)` | OK | A stable voice per character is as important as a stable face. |
| `dialogue.voice.timbre` | any | enum: bright \| warm \| dark \| breathy \| nasal \| rough \| clear \| childlike \| aged | `clear` | ~ | Timbre is casting, and casting is not something to leave to a default seed. |

## `audio.*` - 52

| variable | level | type | default | | what it does |
|---|---|---|---|---|---|
| `audio.amb.bed` | scene | string (prompt) or auto | `auto (from world.biome, weather and time_of_day)` | OK | The continuous ambience bed is what makes cuts inside one location feel continuous. |
| `audio.amb.continuity` | scene | enum: continuous \| per_shot \| crossfade \| reset_on_cut | `continuous` | OK | Ambience that restarts every cut is the loudest sign of machine assembly. |
| `audio.amb.layers` | scene | list of tags | `auto (from world.ambient_life)` | ~ | Ambience is built from stacked layers, not a single generated file. |
| `audio.amb.level_db` | scene | number (dB) | `-24` | OK | Ambience level is the floor everything else is judged against. |
| `audio.amb.room_tone` | scene | enum: none \| small_room \| large_room \| hall \| corridor \| classroom \| street \| forest \| cave \| vehicle \| underwater | `auto (from world)` | OK | Room tone is what makes silence sound like a place rather than a missing file. |
| `audio.amb.weather_sound` | scene | enum: auto \| none \| rain_light \| rain_heavy \| thunder \| wind \| snow_muffle \| storm | `auto` | OK | Weather is heard more than seen and should follow the weather variable automatically. |
| `audio.mix.dialogue_db` | any | number (dB) | `-6` | OK | Dialogue is the anchor every other element is set relative to. |
| `audio.mix.duck_mode` | any | enum: none \| static \| sidechain \| manual_curve | `sidechain` | ~ | How music gets out of the way of dialogue is a policy, not a per-cue fix. |
| `audio.mix.dynamics` | movie | enum: wide \| cinematic \| broadcast \| compressed \| loud | `cinematic` | OK | Dynamic range policy decides whether quiet scenes stay quiet. |
| `audio.mix.fade_in_s` | chapter | number (seconds) | `0.5` | OK | Audio needs its own fade separate from picture at structural boundaries. |
| `audio.mix.fade_out_s` | chapter | number (seconds) | `1.0` | OK | An audio tail after picture ends is how a chapter releases. |
| `audio.mix.music_db` | any | number (dB) | `-14` | OK | A stated music level stops every scene needing a manual balance. |
| `audio.mix.perspective` | shot | enum: objective \| subject_pov \| distant \| muffled \| underwater \| tinnitus \| inside_head | `objective` | ~ | Sound perspective is how a subjective POV is actually communicated. |
| `audio.mix.silence` | any | enum: none \| soft \| full \| absolute \| pre_impact \| after_shock | `none` | OK | The silence variable, a deliberate dropout that is one of the strongest audio devices. |
| `audio.mix.silence_s` | shot | number (seconds) | `0.6` | OK | How long the silence holds is the whole effect. |
| `audio.mix.stereo_width` | any | number 0.0-1.5 | `1.0` | OK | Width is a mood tool: narrow for claustrophobia, wide for scale. |
| `audio.mix.target_lufs` | movie | number (LUFS) | `-16` | OK | One loudness target so the whole film normalises consistently. |
| `audio.mix.true_peak_db` | movie | number (dBTP) | `-1.5` | OK | Peak ceiling that keeps the master from clipping on delivery. |
| `audio.music.build_s` | scene | number (seconds) | `0` | TODO | A build before a climax is a scored event with its own duration. **Falls back to:** Approximated by a rising gain ramp on the outgoing cue. |
| `audio.music.cue` | any | string (cue id) or none | `none` | OK | The music variable, naming which cue plays so it can start, stop and recur. |
| `audio.music.duck_db` | any | number (dB) | `-6` | OK | How far music drops under dialogue is the most consequential mix number. |
| `audio.music.genre` | any | enum: none \| orchestral \| piano_solo \| strings \| ambient \| synth \| city_pop \| jazz \| rock \| metal \| electronic \| lofi \| choral \| folk \| traditional_ja \| chiptune \| drone | `piano_solo` | OK | Genre is the fastest handle on a score and seeds instrumentation and tempo. |
| `audio.music.instrumentation` | any | list of tags | `[]` | OK | Naming the instruments is what stops every generated cue sounding the same. |
| `audio.music.intensity` | any | number 0.0-1.0 | `auto (from story.tension)` | OK | One dial for how loud and busy the score is, independent of what it plays. |
| `audio.music.key` | any | enum: auto \| c \| d \| e \| f \| g \| a \| b (with sharps/flats) | `auto` | TODO | A stated key lets reprises and stingers actually match the main theme. **Falls back to:** Prompt hint only; no key extraction or enforcement. |
| `audio.music.length_s` | scene | number (seconds) | `auto (scene length plus tails)` | OK | Generated cues need a target length or they must be crudely cut. |
| `audio.music.loop` | any | bool | `false` | ~ | Looping a short cue is how a long scene gets scored cheaply. |
| `audio.music.mode` | any | enum: major \| minor \| modal \| atonal \| pentatonic \| whole_tone | `auto (minor when story.tone is dark)` | ~ | Mode carries emotional valence more reliably than any adjective in the prompt. |
| `audio.music.motif` | any | string (motif id) or none | `none` | ~ | A named musical theme is how a film's emotional callbacks are built. |
| `audio.music.prompt` | any | string (ACE-Step text prompt) | `auto (from genre, mood, tone and intensity)` | OK | The generator takes text, so the resolved prompt must be an authorable field. |
| `audio.music.reprise_of` | scene | string (cue id) or none | `none` | ~ | A reprise must point at the earlier cue rather than be re-described from scratch. |
| `audio.music.role` | any | enum: none \| score \| source \| diegetic \| anthem \| theme \| underscore \| sting \| silence_bed | `score` | OK | Whether music exists in the world changes mixing, filtering and perspective. |
| `audio.music.seed` | any | number | `auto (from seed_root and cue id)` | OK | Reproducible music matters as much as reproducible images. |
| `audio.music.start_at_pct` | scene | number (0-100 of scene) | `0` | OK | Where music enters within a scene is a directing choice, not a technical one. |
| `audio.music.stinger` | shot | enum: none \| hit \| riser \| reverse_swell \| dread_low \| comedy_slide \| choir_hit \| taiko_hit | `none` | ~ | A single musical hit on a cut is the most-used scoring device in anime. |
| `audio.music.tempo_bpm` | any | number or auto | `auto (from time.pace and story.tension)` | ~ | Tempo is the link between music and cut rate and must be statable. |
| `audio.music.transition` | any | enum: cut \| crossfade \| fade_in \| fade_out \| hard_stop \| stinger \| build \| drop \| tempo_shift \| key_change \| reprise \| bridge \| overlap_hold \| silence_into | `crossfade` | ~ | The music-transition variable the author asked for, naming how one cue becomes the next. |
| `audio.music.transition_at` | any | enum: on_cut \| on_scene_start \| on_scene_end \| at_pct \| on_beat \| on_line_end | `on_scene_start` | ~ | Where the change lands is what makes it feel scored rather than accidental. |
| `audio.music.transition_s` | any | number (seconds) | `1.5` | OK | Music transition length is the difference between a stumble and a turn. |
| `audio.sfx.auto_foley` | any | bool | `true` | ~ | Footsteps and cloth should appear from blocking rather than be authored per shot. |
| `audio.sfx.category` | shot | enum: none \| foley \| impact \| whoosh \| ui \| nature \| mechanical \| magic \| vocal_nonverbal \| destruction \| vehicle | `none` | OK | Category selects generation settings, EQ and default level in one word. |
| `audio.sfx.gain_db` | any | number (dB) | `-12` | OK | A default effects level so nothing needs mixing to be audible. |
| `audio.sfx.impact_sync` | shot | bool | `true` | OK | An impact effect must land on the same frame as the impact flash. |
| `audio.sfx.list` | shot | list of [sfx_id, at_pct, gain_db] | `[]` | OK | The sound-effects variable, placing named one-shots inside a shot. |
| `audio.sfx.pan` | shot | number -1.0..1.0 | `0` | OK | Placing a sound off-centre is free depth and follows screen direction. |
| `audio.sfx.prompt` | shot | string (Stable Audio prompt) | `auto (from shot.action and world)` | OK | Generated SFX need text, so the derived prompt must be overridable. |
| `audio.sfx.reverb_send` | any | number 0.0-1.0 | `auto (from world.interior_exterior)` | ~ | Effects must sit in the same room as the dialogue or the scene splits apart. |
| `audio.sfx.tail_s` | shot | number (seconds) | `0.5` | OK | Sound that continues past the cut is what binds two shots together. |
| `audio.sfx.transition_whoosh` | shot | enum: none \| auto \| soft \| hard \| reverse \| doppler | `auto` | OK | Whip pans and smash cuts are half sound, and the sound is what sells them. |
| `audio.vo.char` | any | string (char.id) or none | `auto (story.pov_char)` | OK | Whose inner voice we hear must be explicit or the POV blurs. |
| `audio.vo.mode` | any | enum: none \| narration \| inner_monologue \| letter \| phone \| radio \| announcement \| memory_echo | `none` | OK | Voice-over is processed and mixed differently from in-scene dialogue. |
| `audio.vo.processing` | any | enum: dry \| close_intimate \| reverb_wash \| telephone \| radio \| distant \| doubled \| whisper_layer | `close_intimate` | OK | Processing is what tells the audience a voice is interior rather than spoken. |

## `anime.*` - 67

| variable | level | type | default | | what it does |
|---|---|---|---|---|---|
| `anime.anim.bank_id` | shot | string (bank sequence id) | `none` | OK | Transformations, henshin and attack cut-ins are reused stock cuts, and anime reuses them on purpose. |
| `anime.anim.bank_reuse` | shot | enum: rerender \| reuse_exact \| reuse_regrade \| reuse_reframe | `reuse_exact` | ~ | Whether a bank cut is the same footage or re-dressed is a look and a cost decision at once. |
| `anime.anim.cg_mix` | any | enum: none \| props_3d \| vehicles_3d \| crowd_3d \| environment_3d \| camera_3d \| full_3dcg | `none` | TODO | Modern anime mixes cel-shaded 3D with 2D characters, and the mix must be declarable before it can be matched. **Falls back to:** Requested as tags such as cel-shaded mecha; no 3D pass and no camera solve. |
| `anime.anim.cycle` | shot | enum: none \| walk \| run \| breathing \| idle_sway \| blink_loop \| flag \| water_loop \| fire_loop \| crowd_loop \| sparkle_loop | `none` | ~ | Repeating cycles are how anime buys screen time, and a looped short clip is far cheaper than a long generation. |
| `anime.anim.cycle_loops` | shot | number (count) | `auto (enough to fill time.shot_s)` | ~ | How many repeats decides whether a cycle reads as walking or as a stuck GIF. |
| `anime.anim.exaggeration` | any | number 0.0-1.0 | `0.2` | ~ | Squash, stretch, anticipation and overshoot are drawn-animation physics no camera or lens variable can express. |
| `anime.anim.hold_style` | shot | enum: none \| held_cel \| held_pan \| held_partial \| held_fx \| pose_hold \| stills_montage | `none` | ~ | The held cel is the backbone of limited animation and deserves a name rather than being the absence of a video pass. |
| `anime.anim.motion_budget` | chapter | number 0.0-1.0 (fraction of shots allowed full or showcase) | `0.15` | ~ | Anime is scheduled art, and capping fully animated cuts keeps the money on screen where it matters. |
| `anime.anim.on_n` | any | enum: 1 \| 2 \| 3 \| 4 \| mixed | `auto (3; 2 when shot.purpose=action; 1 when anime.anim.sakuga_level=showcase)` | OK | Drawings-per-second stepping is the loudest tell that a clip is anime, and it is orthogonal to movie.fps. |
| `anime.anim.partial` | shot | list of enum: blink \| mouth \| eyes \| hair_sway \| cloth_sway \| breath \| flame \| water \| steam \| smoke \| leaves \| rain \| crowd_idle \| hands | `[]` | TODO | Animating one isolated element over a held drawing is what limited animation actually is. **Falls back to:** Named elements are pushed into shot.motion_prompt with motion_strength clamped low; nothing guarantees only that element moves. |
| `anime.anim.pose_hold_frames` | shot | number (frames) | `auto (6 at 24fps)` | OK | Anime action lands by snapping to a pose and holding it; without the hold the motion reads as mush. |
| `anime.anim.sakuga_level` | any | enum: held \| limited \| standard \| full \| showcase | `standard` | OK | One word allocating frame rate, motion strength, clip links, steps and retries to the cuts that deserve them. |
| `anime.anim.smear_frames` | shot | number (count, 1-3) | `2` | TODO | A smear lives one to three frames; longer and it becomes a blur. **Falls back to:** Ignored; the substitute smear fx uses its own duration. |
| `anime.anim.smear_style` | shot | enum: none \| multiples \| stretch \| streak \| ghost_trail \| brush_smear \| dissolve_limb | `none` | TODO | A drawn smear is a distortion drawing, a different thing from the post-process smear fx. **Falls back to:** Motion-distortion tags on the mid keyframe when keyframe_mode allows one, plus the smear fx at the same percentage. |
| `anime.anim.step_scope` | any | enum: whole_frame \| content_only \| character_only \| fx_only \| none | `content_only` | ~ | Anime steps the drawings but never the camera, so whole-frame stepping judders the pan. |
| `anime.bg.artwork_extent` | shot | enum: frame \| 1_5x \| 2x \| 3x \| panorama | `frame` | ~ | An anime pan is performed across one oversized painting, so the art must be wider than the frame. |
| `anime.bg.char_integration` | any | enum: none \| line_match \| color_bleed \| shared_grain \| ao_contact \| full_comp | `line_match` | ~ | Characters looking pasted onto the background is generated anime's most common failure. |
| `anime.bg.hue_relation` | scene | enum: matched \| cooler \| warmer \| desaturated \| higher_key \| lower_key \| complementary | `matched` | ~ | Hue separation keeps a character readable against a busy painting, distinct from value separation. |
| `anime.bg.line` | any | enum: none \| soft_line \| full_line \| ink_line | `none` | OK | Whether the background carries line art signals which anime tradition a film belongs to. |
| `anime.bg.plate_id` | scene | string (plate id) or auto | `auto (one plate per world location)` | ~ | Every cut in a location should sit on the same painting. |
| `anime.bg.style` | any | enum: cel_flat \| poster_color \| watercolor \| gouache \| acrylic_matte \| airbrush_soft \| digital_painted \| photoreal_painted \| photobash \| line_and_wash \| ukiyo_e \| graphic_flat | `digital_painted` | OK | Background medium is a separate axis from finish level and is what makes a film look painted. |
| `anime.bg.style_contrast` | any | number 0.0-1.0 | `0.4` | ~ | The gap between character and background rendering is the defining anime image decision. |
| `anime.color.accent` | any | string (hex or named colour) | `auto (harmony partner of anime.color.key)` | OK | The single colour allowed to break the scheme is where the audience's eye goes. |
| `anime.color.character_lock` | any | bool | `true` | ~ | A character's approved colours must survive the scene grade or recognition breaks. |
| `anime.color.count` | any | number (palette size limit, 0 = unlimited) | `0` | TODO | Limited palettes were a cel-era constraint authors now choose for a flat designed look. **Falls back to:** Ignored at generation; optionally applied as a posterise pass at the grade stage. |
| `anime.color.forbidden` | any | list of colours | `[]` | ~ | Withholding one colour until it matters is the oldest device in a colour script. |
| `anime.color.harmony` | any | enum: free \| analogous \| complementary \| split_complementary \| triad \| monochrome \| duotone \| warm_cool_split | `analogous` | ~ | Stating the palette rule lets accent, background and rim colours be derived rather than guessed. |
| `anime.color.key` | any | string (hex or named colour) | `auto (from anime.color.script, else story.mood)` | OK | One dominant colour per scene makes a film feel designed instead of generated. |
| `anime.color.motif_map` | movie | list of [motif_id, colour] | `[]` | ~ | Binding each motif to one colour makes a visual callback land without dialogue. |
| `anime.color.script` | movie | list of [chapter_or_scene_id, key_color, accent_color, note] | `auto (from story.mood and story.tonality_curve per chapter)` | ~ | The colour script is the anime colour designer's actual deliverable, not a per-shot grade preset. |
| `anime.color.setting` | scene | enum: normal \| night \| dusk \| dawn \| interior_warm \| fluorescent \| backlit \| moonlight \| firelight \| underwater \| storm \| monochrome_memory \| sepia_memory \| flashbulb | `auto (from world.time_of_day and light.motivation)` | ~ | Anime approves a separate character colour set per lighting condition, before any grade. |
| `anime.draw.cel_artifacts` | any | list of enum: film_grain \| registration_jitter \| dust_scratches \| halation \| telecine_wobble \| paper_texture \| gate_weave | `auto (from anime.draw.era)` | ~ | Cel-era anime looks old because of how it was photographed, and these artefacts carry it. |
| `anime.draw.detail_density` | any | enum: minimal \| tv_standard \| ova \| film \| ultra | `tv_standard` | ~ | Line count per drawing is a production tier that should inherit down a sequence. |
| `anime.draw.era` | any | enum: cel_70s \| cel_80s \| ova_90s \| early_digital_00s \| modern_digital \| modern_web \| film_stock_retro | `modern_digital` | OK | Production era bundles line, colour, artefacts and finish into the word authors think in. |
| `anime.draw.eye_render` | any | enum: moe_round \| shoujo_large \| shounen_bold \| seinen_sharp \| ova_90s \| minimal_dot \| realistic | `moe_round` | OK | Eye construction is house style, set once above the character list. |
| `anime.draw.hair_highlight` | any | enum: none \| soft \| angel_ring \| segmented \| glossy \| multi_band | `segmented` | OK | The hair highlight band is a recognisable convention that dates a film to a decade. |
| `anime.draw.line_color` | any | enum: black \| dark_neutral \| color_trace \| per_region_trace \| none | `black` | ~ | Coloured trace lines are a finishing decision that softens an entire film's character art. |
| `anime.draw.line_weight` | any | enum: hairline \| thin \| normal \| thick \| variable \| brush \| rough_genga | `normal` | OK | Line weight is the character-art equivalent of lens choice and is read first. |
| `anime.draw.shading_steps` | any | enum: flat_0 \| cel_1 \| cel_2 \| cel_3 \| soft_gradient \| painterly | `cel_2` | OK | How many hard shadow steps a drawing carries is the structural difference between anime and photography. |
| `anime.draw.shadow_edge` | any | enum: hard \| slightly_soft \| soft \| airbrush | `hard` | OK | Cel shadow edges are hard by construction, so softening them is an explicit period decision. |
| `anime.draw.shadow_hue` | any | enum: darker_same_hue \| blue_shift \| purple_shift \| complementary \| warm_shift \| grey_multiply | `blue_shift` | ~ | Anime shadow colour is chosen by a colour designer, and the hue shift is half a film's identity. |
| `anime.format.broadcast_safe` | movie | bool | `true` | ~ | Strobe and flash limits exist because broadcast anime injured viewers once. |
| `anime.format.ed_style` | chapter | enum: none \| still_pan \| single_take_walk \| illustration_gallery \| epilogue_scene \| dance \| credits_over_black | `illustration_gallery` | ~ | The ending is usually the cheapest and most stylised part of an anime. |
| `anime.format.episode_no` | movie | number or none | `none` | OK | Episode numbering drives titles, previews and file naming for a series. |
| `anime.format.eyecatch` | chapter | enum: none \| single \| pair | `none` | OK | The eyecatch is the act break of an anime episode and its absence is felt. |
| `anime.format.eyecatch_style` | chapter | enum: logo_card \| character_pose \| prop_still \| chibi_gag \| title_typography \| silhouette_card | `logo_card` | OK | The eyecatch is a tiny authored image that tells the audience what kind of show this is. |
| `anime.format.next_preview` | chapter | enum: none \| clips_vo \| still_vo \| tease_only \| gag | `none` | ~ | The next-episode preview is a fixed anime form with its own voice and pacing rules. |
| `anime.format.op_style` | chapter | enum: none \| montage \| character_intro \| abstract_graphic \| dance \| still_frames \| action_showcase \| typography | `montage` | ~ | An opening is its own short film with its own grammar. |
| `anime.format.sequence_role` | chapter | enum: none \| avant \| op \| a_part \| eyecatch \| b_part \| c_part \| ed \| next_preview \| post_credit | `auto (none for short; avant/a_part/b_part/ed for episode)` | OK | Broadcast furniture is a different axis from dramatic role and drives different music and caption rules. |
| `anime.fx.aura` | shot | enum: none \| glow \| flame \| electric \| dark_miasma \| sparkle \| pressure_ripple | `none` | ~ | A character-attached aura is a persistent drawn element held across a shot. |
| `anime.fx.deform_mode` | shot | enum: none \| sd_chibi \| head_pop \| noodle_limbs \| rubber_hose \| mini_inset | `none` | OK | Super-deformed comedy mode is an alternate character design, not an effect. |
| `anime.fx.deform_scope` | shot | enum: whole_shot \| inset \| punch_in_beat | `whole_shot` | ~ | A chibi cutaway and a chibi shot are different jokes with different timing. |
| `anime.fx.drawn_effect` | shot | enum: none \| cel_fire \| ink_smoke \| crystal_water \| geometric_debris \| stylised_lightning \| sparks \| wind_lines \| petals \| glass_shatter \| energy_beam | `none` | ~ | Effects animation is its own craft and looks nothing like photographic fire or water. |
| `anime.fx.face_fault` | shot | enum: none \| jaw_drop \| swirl_eyes \| dot_eyes \| shadowed_eyes \| nosebleed \| half_face_shock \| crying_river \| ghost_leaving | `none` | OK | A comedy face fault redraws the face itself, a different channel from sticker-like emote symbols. |
| `anime.fx.onomatopoeia` | shot | list of strings (on-screen sound words) | `[]` | ~ | Drawn sound text on screen is native anime grammar with no live-action equivalent. |
| `anime.fx.onomatopoeia_pos` | shot | enum: auto \| tl \| tr \| bl \| br \| center \| over_subject \| diagonal | `auto` | ~ | Where the sound word sits decides whether it reads as impact or as a caption. |
| `anime.fx.onomatopoeia_style` | any | enum: katakana_brush \| kanji_heavy \| latin_comic \| hand_scrawl \| glitch \| none | `katakana_brush` | ~ | Lettering style is the whole tone, separating a horror rumble from a comedy thud. |
| `anime.fx.silhouette_mode` | shot | enum: none \| full_silhouette \| color_silhouette \| strobe_silhouette \| rim_only | `none` | OK | Reducing a character to a flat shape is stock anime grammar for reveals and dread. |
| `anime.fx.split_screen` | shot | enum: none \| two_v \| two_h \| three_v \| grid_4 \| diagonal_shards \| inset_pip \| manga_panels \| radial_wedges | `none` | ~ | Multi-panel frames hold three reactions at once, which frame-in-frame cannot express. |
| `anime.fx.technique_card` | shot | string (technique or attack name) | `""` | OK | Naming the attack on screen is a genre staple currently faked through captions. |
| `anime.perf.blink_pattern` | shot | enum: single \| double \| slow_close \| held_shut \| none | `single` | ~ | A double blink is surprise and a slow close is resignation; rate alone cannot say which. |
| `anime.perf.blink_rate` | any | number (blinks per minute) | `auto (12, rising with story.tension)` | ~ | Blinks are the cheapest sign of life in a held drawing and anime times them deliberately. |
| `anime.perf.head_tilt` | shot | number (degrees, -30..30) | `0` | OK | The head tilt is anime's smallest and most-used performance beat. |
| `anime.perf.mouth_chart` | any | enum: closed_only \| 2_pos \| 3_pos_ja \| 5_vowel_ja \| 8_phoneme \| full_viseme | `3_pos_ja` | ~ | Anime mouths run on a handful of positions, and the count separates anime from a Western cartoon. |
| `anime.perf.mouth_flap_rate` | any | number (Hz) | `auto (from dialogue syllable rate, else 5)` | ~ | Flap rate makes mouth movement read as speech even when it is not phoneme-accurate. |
| `anime.perf.mouth_sync_style` | any | enum: prescored_tight \| postscored_loose \| flap_only \| closed_narration | `postscored_loose` | OK | Japanese anime records after animation, so loose sync is correct rather than a defect. |
| `anime.perf.pose_library` | shot | string (pose id) or none | `none` | ~ | Named stock poses give repeatable staging without describing anatomy every time. |

## `caption.*` - 13

| variable | level | type | default | | what it does |
|---|---|---|---|---|---|
| `caption.font` | movie | string (font id) | `auto (from caption.language)` | OK | Font choice is both legibility and tone, and CJK needs a specific face. |
| `caption.language` | any | enum: inherit \| en \| ja \| zh \| ko \| es \| fr \| de | `inherit` | OK | Caption language is separate from spoken language for subtitled films. |
| `caption.max_chars` | movie | number (per line) | `42` | OK | Line length is the main readability control for burnt-in text. |
| `caption.max_lines` | movie | number | `2` | OK | More than two lines covers the picture and stops being a caption. |
| `caption.mode` | any | enum: none \| dialogue \| full \| forced_only \| signs_only \| karaoke | `none` | OK | The captions variable, deciding what text is burnt into the picture. |
| `caption.offset_s` | any | number (seconds) | `0` | OK | Global timing trim when TTS and caption timings drift apart. |
| `caption.position` | any | enum: bottom \| top \| bottom_left \| bottom_right \| center \| under_speaker | `bottom` | ~ | Captions sometimes have to move to avoid the composition. |
| `caption.reading_speed` | movie | number (chars per second) | `17` | OK | Minimum on-screen time so captions can actually be read. |
| `caption.sfx_captions` | any | bool | `false` | ~ | Accessibility captions for sound are a distinct output from dialogue subtitles. |
| `caption.signs_policy` | any | enum: none \| translate_important \| translate_all \| overlay_note | `none` | ~ | On-screen signage in another language needs a stated handling policy. |
| `caption.size_pct` | movie | number (percent of frame height) | `4.5` | OK | Caption size must scale with canvas rather than be a fixed pixel value. |
| `caption.speaker_labels` | any | bool | `false` | OK | Off-screen and crowded scenes need attribution the audience can follow. |
| `caption.style` | movie | enum: plain_white \| outlined \| boxed \| drop_shadow \| anime_yellow \| soft_grey | `outlined` | OK | Caption styling is what keeps text readable over a bright anime frame. |

## `render.*` - 18

| variable | level | type | default | | what it does |
|---|---|---|---|---|---|
| `render.bitrate` | movie | string (e.g. 12M) or auto | `auto` | OK | Flat anime colour banding is a bitrate problem before it is an art problem. |
| `render.cache_policy` | any | enum: reuse \| reuse_unless_changed \| force \| never | `reuse_unless_changed` | OK | Re-rendering unchanged shots is the single largest waste in an iterative film. |
| `render.codec` | movie | enum: h264 \| h265 \| prores \| vp9 \| av1 | `h264` | OK | Delivery codec decides compatibility and how much the grade survives. |
| `render.color_space` | movie | enum: srgb \| rec709 \| rec2020 | `rec709` | OK | A stated colour space keeps grades consistent between preview and delivery. |
| `render.face_detailer` | any | bool | `true` | OK | Faces at small scale are where anime generation fails most visibly. |
| `render.frame_interp` | any | enum: none \| to_movie_fps \| double \| smooth | `to_movie_fps` | ~ | Interpolation is how a low-fps generation reaches delivery fps, and it fights anime stepping. |
| `render.i2v_cfg` | any | number | `3.5` | OK | Motion adherence versus stability is a distinct dial from image CFG. |
| `render.i2v_steps` | any | number | `30` | OK | The video pass has its own quality/time trade separate from the keyframe. |
| `render.on_fail` | any | enum: warn_continue \| retry \| placeholder \| halt | `retry` | OK | A failed shot in a long render must not silently produce a broken film. |
| `render.order` | movie | enum: sequential \| hero_first \| cheap_first \| dependency | `dependency` | ~ | Render order decides how soon an author sees the shots that matter. |
| `render.overscan_pct` | any | number (percent) | `15` | OK | Extra rendered margin is what makes post pans, crops and shakes possible without softening. |
| `render.placeholder` | any | enum: black \| slate \| last_good \| keyframe_still | `keyframe_still` | OK | What stands in for a failed shot decides whether a rough cut is still watchable. |
| `render.proxy_mode` | movie | bool | `false` | OK | Fast low-resolution passes are how an author iterates on structure before committing. |
| `render.sampler` | any | string (sampler name) | `dpmpp_2m` | OK | Sampler choice changes line quality noticeably on anime checkpoints. |
| `render.scheduler` | any | string (scheduler name) | `karras` | OK | Scheduler pairs with sampler and belongs beside it as an inheritable default. |
| `render.upscale` | any | enum: none \| 1_5x \| 2x \| 4x | `none` | OK | Hero shots deserve resolution that filler shots would waste. |
| `render.version_tag` | movie | string | `auto (timestamp)` | OK | Versioned outputs are how an author compares two cuts instead of overwriting one. |
| `render.watermark` | movie | enum: none \| draft \| version_slate \| custom | `none` | OK | Draft marking prevents a work-in-progress cut being mistaken for the final film. |

