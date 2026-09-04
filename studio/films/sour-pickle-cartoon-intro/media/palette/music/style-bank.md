# The style bank — 50 short auditions

Each is **22 seconds**, all singing the same chorus, all levelled to −16 LUFS, all on the
same seed (48). The only variable is style, so the comparison is fair.

> Sour Pickle! Sour Pickle Cafe! / Ain't a sour thing about it, no way /
> Big plate, warm plate, come as you are / The little cafe that'll make your day

Files in `music/style-bank/`. Rebuild any of them from `build/style_bank.py`, which holds
every tag string, bpm and key. `python3 style_bank.py SB FS` re-renders just those families.

---

## SB · SpongeBob — nautical, silly, bouncy

| | style | bpm |
|---|---|---|
| `SB01_hornpipe` | sailor hornpipe, tin whistle, fiddle, tuba, snare rolls | 132 |
| `SB02_ukulele_steel` | ukulele + steel drums, marimba, bongos | 118 |
| `SB03_hawaiian_surf` | slack key hawaiian + twangy surf reverb guitar | 108 |
| `SB04_brass_band` | sousaphone, trombone slides, clarinet, seaside bandstand | 124 |
| `SB05_tuba_clarinet` | bouncing tuba, squawking clarinet, woodblock, slapstick | 128 |
| `SB06_whistle_tune` | whistled melody over ukulele and upright bass | 112 |
| `SB07_calypso` | steel pan lead, congas, walking bass | 116 |
| `SB08_bassoon_romp` | comic bassoon, staccato strings, xylophone, chase energy | 140 |

## FS · Fly Me To The Moon — female jazz vocal

| | style | bpm |
|---|---|---|
| `FS01_swing_bigband` | big band swing, brushed drums, muted trumpets, sax section | 118 |
| `FS02_jazz_trio` | intimate trio, brushes, upright bass, soft piano, smoky club | 104 |
| `FS03_bossa` | bossa nova, nylon guitar, flugelhorn, breathy vocal | 122 |
| `FS04_lounge_vibes` | vibraphone lead, cocktail piano, velvet vocal | 112 |
| `FS05_vegas` | showroom swing, brass stabs, shout chorus, belting vocal | 132 |
| `FS06_cool_jazz` | west coast cool, muted trumpet, relaxed vocal | 96 |
| `FS07_torch` | slow torch ballad, lush strings, aching vocal | 68 |
| `FS08_organ_swing` | hammond organ swing, greasy bass, playful vocal | 126 |

## E8 · 1980s

`E801_synthpop` · `E802_city_pop` · `E803_soft_rock` · `E804_boogie_funk` ·
`E805_new_wave` · `E806_sax_ac` · `E807_italo` · `E808_power_ballad`

## N9 · 1990s

`N901_smooth_rnb` · `N902_acid_jazz` · `N903_trip_hop` · `N904_pop_rock` ·
`N905_house_diva` · `N906_neo_soul` · `N907_britpop` · `N908_jangle`

## CT · classic cartoon and americana

`CT01_rubberhose` (1930s ragtime/banjo/tuba, scratchy) · `CT02_bigband_chase` ·
`CT03_klezmer` · `CT04_polka` · `CT05_western_swing` · `CT06_bluegrass` ·
`CT07_doowop` · `CT08_motown` · `CT09_ragtime` · `CT10_mariachi`

## MX · everything else worth hearing once

`MX01_exotica` · `MX02_chanson` · `MX03_gypsy_jazz` · `MX04_rockabilly` ·
`MX05_ska` · `MX06_reggae` · `MX07_disco` · `MX08_funk`

---

## How to use this

Pick two or three, and I'll render those at full length (46–62s) with the complete lyric
and several seeds each — the same treatment the waltz got. A 22-second audition tells you
whether a *style* is right; it doesn't tell you whether a particular take is good, because
the seed lottery matters more than the tags once the style is settled.

Worth noting: the SpongeBob family and the Fly Me family pull the cafe in opposite
directions. SB says "this place is fun and a bit daft" — which matches the pickle. FS says
"this place is warm and a little classy" — which matches the twenty-year-regulars and the
food. Both are true about the cafe; they can't both be the theme.
