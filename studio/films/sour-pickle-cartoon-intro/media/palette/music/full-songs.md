# The fourteen, at full length

All 62 seconds, all singing the complete lyric — two verses, two choruses, an outro — all
levelled to −16 LUFS. The tag strings are imported from `build/style_bank.py` rather than
retyped, so what you're hearing at full length is the same arrangement you picked at 22s.

Files in `music/full-songs/`. Every seed rendered is kept in `music/full-songs/all-seeds/`.

---

## The lyric they all sing

> **Verse** — Down on Store Street, second door, / green as green and gold on the sign — /
> there's a pickle on the wall who's been dancing since before / you or me or anyone in line.
>
> **Chorus** — **Sour Pickle! Sour Pickle Cafe!** / Ain't a sour thing about it, no way. /
> Big plate, warm plate, come as you are — / the little cafe that'll make your day.
>
> **Verse** — She grew the lettuce in her own back yard, / he's been cracking the eggs
> since dawn. / Nothing here is fast and nothing here is hard, / just good and hot and gone.
>
> **Chorus** *(repeat)* → **Outro** — the little cafe that'll make your day.

---

## The fourteen

**Cartoon / character**
| file | what it is | bpm |
|---|---|---|
| `CT02_bigband_chase` | screaming brass, driving swing drums, xylophone runs | 152 |
| `CT03_klezmer` | wailing clarinet, accordion, upright bass, headlong | 140 |
| `CT09_ragtime` | solo saloon piano with light snare, syncopated | 108 |
| `SB08_bassoon_romp` | comic bassoon, staccato strings, xylophone, triangle | 140 |

**Jazz / Fly Me To The Moon**
| file | what it is | bpm |
|---|---|---|
| `FS02_jazz_trio` | brushes, upright bass, soft piano, smoky club | 104 |
| `FS03_bossa` | nylon guitar, brush kit, muted flugelhorn, breathy | 122 |
| `FS04_lounge_vibes` | vibraphone lead, cocktail piano, velvet | 112 |
| `FS06_cool_jazz` | west coast cool, muted trumpet, relaxed | 96 |
| `FS07_torch` | slow torch ballad, lush strings, aching | 68 |
| `FS08_organ_swing` | hammond organ, greasy bass, playful | 126 |
| `MX03_gypsy_jazz` | fast manouche guitar comping, violin lead | 138 |

**Modern**
| file | what it is | bpm |
|---|---|---|
| `E801_synthpop` | gated drums, DX7 bells, fat analog bass | 118 |
| `E802_city_pop` | slap bass, chorus guitar, electric piano, sax fills | 112 |
| `MX08_funk` | tight drum break, slap bass, clavinet, horn hits | 108 |

---

## Notes from the render

**Thirteen of the fourteen held level across the full 62 seconds on the first seed.** Only
`MX08_funk` faded — seed 48 dropped **49 dB** in its last ten seconds, effectively silent,
and seed 205 fixed it. That's the same trap as before: the file exists, runs the right
length, and is wrong. Every take here is tail-checked, so none of the delivered fourteen
have it.

**Tempo is doing a lot of the work.** The four fastest (`CT02` at 152, `CT03` and `SB08` at
140, `MX03` at 138) make the cafe feel frantic and funny; the four slowest (`FS07` at 68,
`FS06` at 96, `FS02` at 104, `CT09` at 108) make it feel like somewhere you'd go every
Sunday for twenty years. Both readings are supported by the reviews — but the 12-second
intro cut can only carry a fast one, and a 60-second spot can only carry a slow one. It may
genuinely be two pieces of music rather than one.

**If you want more seeds** of any of these, `python3 full_songs.py FS02_jazz_trio` on the
box re-renders just that one across seeds 48 / 205 / 911 and keeps whichever holds best.
