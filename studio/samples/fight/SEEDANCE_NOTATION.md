# Seedance notation - what we would have sent, and did not

*Written 2026-09-29 beside the three demo films. Every shot below was rendered LOCALLY; nothing here was sent to a paid engine. For each: why the paid engine would do it better, the exact prompt, the pictures it would get, and the command that would send it.*

**How it would run.** Workflow `76_seedance25_ref.json` (ComfyUI's `ByteDance2ReferenceNodeV2`, model *Seedance 2.5*, task *reference*, 1080p, 16:9, audio on). It needs the Comfy account token the ComfyUI frontend supplies after someone signs in at http://192.168.0.45:8188 - none is on the box, and it charges per second. `fight.py --seedance SHOT` sends [image 1] = the shot's composed start frame (`anchor_SHOT.png`), [image 2] = the character's reference, [image 3] = the place's plate, with the prompt below.

**Price.** Seedance 2.5's per-second rate was not verified tonight; at the last verified rate (Seedance 2.0 Fast, $0.09/s, playbook §0.1) each estimate below is per take - three seeds, the studio's floor for a pick, is three times that.

## DEAD STOCK  (`dead-stock`)

*A courier cornered in a warehouse at night brings the stock down between herself and the man sent to collect it.*

### 030 - the door

- **What we did instead:** LTX-2.5, seed 11 (no faults, highest score 0.700).
- **Why Seedance:** A walk. Measured: our engines hold the picture and the person but not the walk itself - he takes one step and stops because we wrote it that way. Seedance would walk him the whole aisle.
- **Pictures:** [image 1] `anchor_030.png` (the start frame) - [image 2] `ref_hale.png` - [image 3] `ref_warehouse.png`
- **Settings:** Seedance 2.5, reference, 5 s, 1080p, 16:9, audio on - about $0.45 a take at the 2.0 Fast rate
- **Command (after signing in):** `python3 studio/_tools/fight.py --sequence dead-stock --seedance 030 --resolution 1080p`

```text
[image 1] is the first frame. The man of [image 2] walks in out of the rain through the loading door of the warehouse of [image 3] and comes slowly down the long aisle toward the camera, unhurried, gloved hands loose at his sides, lamplight passing over him lamp by lamp until he stops ten metres from us. Static camera, anamorphic, night, sodium orange and blue shadow. Sound: rain roaring outside, the door on its rails, his footsteps on wet concrete getting closer. No music.
```

### 070 - the fall

- **What we did instead:** Blender previz -> LTX-2.3 depth control, seed 3003 (picked by eye - a plume of dust bursts at the impact; the same motion agreement with the simulation as seed 11 (r 0.918)).
- **Why Seedance:** A physical event with dozens of bodies in contact. We choreographed it in Blender and drew it through depth control, so every crate lands where the simulation put it; Seedance would invent the physics from words - better texture at speed, no guarantee where anything lands.
- **Pictures:** [image 1] `anchor_070.png` (the start frame) - [image 2] `ref_hale.png` - [image 3] `ref_warehouse.png`
- **Settings:** Seedance 2.5, reference, 5 s, 1080p, 16:9, audio on - about $0.45 a take at the 2.0 Fast rate
- **Command (after signing in):** `python3 studio/_tools/fight.py --sequence dead-stock --seedance 070 --resolution 1080p`

```text
[image 1] is the first frame: the warehouse of [image 3] with the man of [image 2] far down the aisle. A towering stack of old wooden crates beside the camera tips over and falls across the aisle; the crates crash onto the wet concrete, burst apart, tumble and pile up into a wall of broken wood that cuts the aisle in two, splinters and dust bursting into the orange lamplight, the man beyond it raising an arm. Camera low and static, slight shake at the impact. Sound: a long groan of wood, a thunderous crash, boards splintering, debris settling, rain. No music.
```

### 080 - the dust

- **What we did instead:** MiniMax H3, seed 202 (no faults, highest score 0.704).
- **Why Seedance:** An effect that must arrive at an instant and then clear (the breakdown's rule 3). Measured: LTX lets dust accumulate whatever the words say; H3 plateaus and clears, which is why this shot is on H3. Seedance keys the effect to the impact frame.
- **Pictures:** [image 1] `anchor_080.png` (the start frame) - [image 2] `ref_hale.png` - [image 3] `ref_warehouse.png`
- **Settings:** Seedance 2.5, reference, 4 s, 1080p, 16:9, audio on - about $0.36 a take at the 2.0 Fast rate
- **Command (after signing in):** `python3 studio/_tools/fight.py --sequence dead-stock --seedance 080 --resolution 1080p`

```text
[image 1] is the first frame. A wave of dust and splinters from the fallen crates hits the man of [image 2] at the instant it arrives - he flinches behind his raised arm - and in a second the air clears; he lowers the arm and squints through the last of it. Medium shot, static camera, the sodium lamp swinging above him. Sound: the dust's rush, debris pattering, his cough, rain. No music.
```

### not shot - the sprint

- **Why it is not in the film:** The obvious action beat - she runs the length of the aisle as the stack comes down behind her - is the one this box measurably cannot do (motion fidelity at speed). The script was written around it: she brings the stack down and is simply on the other side of it.
- **Settings:** Seedance 2.5, reference, 6 s, 1080p, 16:9, audio on - about $0.54 a take

```text
[image 1] is the woman of [image 2] at the foot of the crates in the warehouse of [image 3]. She sprints flat out down the aisle toward the camera as the tower of crates behind her tips and crashes down, splinters and dust chasing her, lamplight strobing over her as she passes under each lamp; she dives through the last gap as the crates close it. Camera tracking backward low and fast. Sound: her feet slapping wet concrete, her breath, the roar of falling crates. No music.
```

## HOUSE RULES  (`house-rules`)

*At three in the morning a soaked stranger walks into a roadside diner, and the waitress remembers him before he says who he is.*

### 030 - the stranger

- **What we did instead:** LTX-2.5, seed 3003 (no faults, highest score 0.654).
- **Why Seedance:** The only candidate in this film, and a weak one: an entrance is a walk, and our engines hold the walker rather than the walk - so he is already inside when the shot begins. Dialogue, faces and a room at night are what this box does best; nothing else here needs paying for.
- **Pictures:** [image 1] `anchor_030.png` (the start frame) - [image 2] `ref_theo.png` - [image 3] `ref_diner.png`
- **Settings:** Seedance 2.5, reference, 5 s, 1080p, 16:9, audio on - about $0.45 a take at the 2.0 Fast rate
- **Command (after signing in):** `python3 studio/_tools/fight.py --sequence house-rules --seedance 030 --resolution 1080p`

```text
[image 1] is the first frame. The young man of [image 2] pushes the glass door of the diner of [image 3] open against the wind and steps in out of the rain, the bell jingling above him; he stops on the mat, dripping, and looks toward the counter. Static camera, medium shot, warm tungsten inside, blue rain and neon outside. Sound: the bell, a gust of rain, the door easing shut. No music.
```

## TEMPER  (`temper`)

*One night at the forge: fire, hammer, water, and a blade that holds its edge.*

### 050 - first blow

- **What we did instead:** MiniMax H3, seed 202 (no faults, highest score 0.625).
- **Why Seedance:** Sparks that exist at the instant of each blow and are gone before the next - the breakdown's rule 3, which we measured does not transfer to LTX-2.5 (the effect accumulates) and partly does to H3. This shot is rendered on both and picked; Seedance is the engine that keys an effect to an impact frame.
- **Pictures:** [image 1] `anchor_050.png` (the start frame) - [image 2] `ref_maren.png` - [image 3] `ref_forge.png`
- **Settings:** Seedance 2.5, reference, 5 s, 1080p, 16:9, audio on - about $0.45 a take at the 2.0 Fast rate
- **Command (after signing in):** `python3 studio/_tools/fight.py --sequence temper --seedance 050 --resolution 1080p`

```text
[image 1] is the first frame. The woman of [image 2] brings the hammer down on the glowing blade on the anvil of the forge of [image 3] three times in a steady rhythm; at the exact instant each blow lands a burst of white-orange sparks explodes off the steel and is gone before the hammer rises again; between the blows the air is clear. Medium shot, static camera, firelight and blue moonlight. Sound: three ringing clangs, each with the spit of sparks, the fire's roar. No music.
```

### 060 - the rhythm

- **What we did instead:** LTX-2.5, seed 3003 (no faults, highest score 0.610).
- **Why Seedance:** Several angles on fast repeated strikes in one generation. LTX-2.5 does the cuts (measured: the word cut makes the cut, and the face holds when it is in the start frame) but not the speed of the swing; Seedance's 15-second multi-shot with references is built for exactly this.
- **Pictures:** [image 1] `anchor_060.png` (the start frame) - [image 2] `ref_maren.png` - [image 3] `ref_forge.png`
- **Settings:** Seedance 2.5, reference, 10 s, 1080p, 16:9, audio on - about $0.90 a take at the 2.0 Fast rate
- **Command (after signing in):** `python3 studio/_tools/fight.py --sequence temper --seedance 060 --resolution 1080p`

```text
[image 1] is the first frame. The woman of [image 2] works the glowing blade on the anvil of the forge of [image 3] in a fast, heavy rhythm. Shot one, medium: three hard blows, sparks bursting at each. Cut to shot two, an extreme close-up: the hammer face meeting the orange steel, sparks spraying at the lens. Cut to shot three, a close-up of her face in the firelight, eyes narrowed, sweat running. Cut to shot four, medium: she turns the blade with the tongs and brings the hammer down again. Sound: the ringing rhythm of the hammer, her breath, the fire's roar. No music.
```

### 070 - quench

- **What we did instead:** MiniMax H3, seed 11 (no faults, highest score 0.700).
- **Why Seedance:** A burst of steam at the instant of contact that must then roll away and clear - rule 3 again. Rendered here on H3 and LTX and picked.
- **Pictures:** [image 1] `anchor_070.png` (the start frame) - [image 2] `ref_maren.png` - [image 3] `ref_forge.png`
- **Settings:** Seedance 2.5, reference, 4 s, 1080p, 16:9, audio on - about $0.36 a take at the 2.0 Fast rate
- **Command (after signing in):** `python3 studio/_tools/fight.py --sequence temper --seedance 070 --resolution 1080p`

```text
[image 1] is the first frame. The glowing blade held by the woman of [image 2] plunges into the water trough of the forge of [image 3]; at the instant it touches, the water erupts into a violent boil and a burst of white steam, which rolls away and thins in a second to show the dark blade under the water. Insert close-up, static camera. Sound: a sharp angry hiss at the instant of contact, bubbling, then quiet. No music.
```

### not shot - the full forging, one take

- **Why it is not in the film:** A whole forging in one continuous 15-second take - heat, strike, turn, strike, quench - is a chain of fast motions with effects at each instant. We cut it into one beat per shot, which is what this box does well; Seedance would attempt it in one.
- **Settings:** Seedance 2.5, reference, 15 s, 1080p, 16:9, audio on - about $1.35 a take

```text
[image 1] is the woman of [image 2] at the anvil of the forge of [image 3]. In one continuous take she draws the glowing blade from the coals, strikes it four times with sparks bursting at each blow, turns it, strikes twice more, then plunges it into the trough in an eruption of steam. Handheld camera circling her slowly. Sound: the fire, six ringing blows, the hiss of the quench. No music.
```

---

**If all of it were sent once:** about $5.31 at the 2.0 Fast rate (three seeds each: $15.93). The studio's rule for spending it is unchanged (playbook §96.4): start frames before video, by scene not by shot, and a bought take must beat the local take on the same beat, scored by the same tools, or it is decoration.
