# Overnight run - 2026-08-16

## The short-form slate

**20 of 20 films rendered.** Vertical 1080x1920, each with keyframes, an i2v pass, a spoken script, a scored cue, effects, and a mastered mix.

- total runtime 6.8 min across 20 films (20.2 s mean, 11.0-32.8 s)
- loudness -10.0 to -9.5 LUFS (target -9.5, feed-loud not broadcast)
- **supplement**: 8 - CAFFEINE + THEANINE, CREATINE, FIBRE, MAGNESIUM, OMEGA-3, PROTEIN, SLEEP & MELATONIN, VITAMIN D
- **commercial**: 6 - ATLAS, LUMEN, NORTHWIND TEA, PACE, SLOW SUNDAY, TIDEWATER
- **hook**: 6 - THE DOOR, THE GARDEN, THE RETURN, FLOOR THIRTEEN, THE SIGNAL, LOW TIDE

### Where things are

- `Z:\shared\SHORTS\` - the films, by kind, plus `contact/` frame strips, `INDEX.md` (table + every script) and `shorts.json`
- `/library` in the app - filter collection **shorts**; each carries its script, voice, cue and measurements
- `films/shorts/*.json` - the 20 scripts, editable; re-render any one with `python3 studio/_tools/overnight_shorts.py --only <id> --force`

### Content rules I applied (worth agreeing or overriding)

- **Supplements** are neutral and evidence-framed: no dosing prescriptions, no cure claims, no invented citations, and every piece closes on a not-medical-advice beat. If you want a harder sell, that is a deliberate decision to make rather than a default.
- **Commercials** use invented brands only (NORTHWIND, PACE, LUMEN, TIDEWATER, ATLAS, SLOW SUNDAY) - the project's standing no-real-brands rule.
- **Hooks** borrow the SHAPE of a scroll-stopping open (cold image, question, whip, payoff) and cast it with our own places. No third-party footage is used; that is the same rule the Dragon Ball breakdown set.

## What else the night measured

### LTX-2.5 is here and multi-shot is real

| | LTX-2.3 | LTX-2.5 |
|---|---|---|
| time (4 s clip) | 27.0s | 25.7s |
| holds the keyframe (drift) | 0.141 - walks away | -0.004 - holds |
| in-frame motion | 8.79 | 1.54 (static floor 0.001) |

**Native multi-shot confirmed**: asked for three viewpoints with 'CUT TO', 2.5 produced a wide, an extreme close-up of the same face and a high overhead in ONE pass, identity holding across the cuts (`samples/multishot/linruo_views_strip.png`). Cuts fire on different VIEWPOINTS; three descriptions of one continuous action correctly render as one continuous shot. It is in the capability gallery as folder 51, and selectable as `video_engine: ltx25` - the default is unchanged, because 2.5 is differently better rather than strictly better.

### The motion shelf

All 34 cards re-measured on both engines: {'alive': 34} on 2.3. Every card renders and moves - which makes the seven `unavailable` labels false, and they are now `weak`. I did NOT promote anything to `ready`: my test measures liveness (something moved, the world held), not whether the card's specific claim happened. Verifying the claims needs the direction-aware instrument and is written down as the next step.

### Reverse angles (you asked for more samples)

15 derived angles across 5 heroes: palette distance mean 0.0073 (the world holds), and the VLM still names the subject in 14 of 15. BRACK is the proof - from one close-up: him from behind down the deck, in profile at the wheel, and from above. Sheet: `samples/reverse_battery/reverse_battery.jpg`.

### Two bugs the night's own output exposed

- **Captions overlapped** each other and the story band in the first films - visible as text rendered on top of itself. Both fixed in the cutter and the early films re-cut.
- **The drift instrument was wrong**: SSIM drift punishes a clip for animating, so it called correct motion 'drift'. Replaced with palette distance, which this project had already found and written down during the video_engines session.

## Open

- `radio_dish` is style-sensitive, not weak: 4/12 frames recognisable, and every miss rolled a decorative style. Recorded on the card; regenerate with photographic styles when you want it.
- Motion claims still unverified (see above).
- The one-page shell / serve.py split still wants a session with eyes on the UI.
