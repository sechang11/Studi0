# The Uplifting Set — piano-led, inspirational, mood-brightening

A second, separate direction from the americana theme in [theme-song.md](theme-song.md).
Where that one is a diner shuffle, this set is **classy piano** — warm, hopeful, the kind
of cue that makes an ordinary morning look like a small good thing.

Five cues, in `music/uplifting/`. **All five are level-matched to −16 LUFS**, so when you
A/B them you're hearing the arrangement, not the loudness — the quiet ones aren't worse,
they're quieter, and raw renders would have misled you by up to 18 dB.

Rendered on ACE-Step 1.5 turbo on the 5090. Every cue is reproducible from
`build/make_uplifting.py` (tags, bpm, key, seed all recorded there).

---

## The five

### 01 · First Light — `01_first_light.mp3`
**0:38 · 72 bpm · C major · solo piano · instrumental**
Close-miked felt piano, alone. A simple singing melody over gentle arpeggios, patient,
soft room around it. The most restrained thing here — no strings, no percussion, nothing
to hide behind.
*Where it fits:* the garden opening, or the whole spot if you want it to feel like a short
film rather than an ad. Also the only cue that would sit comfortably under a voiceover.
*Note:* trimmed to 0:38 with a deliberate 4s fade — see "the 45-second problem" below.

### 02 · Something Good — `02_something_good.mp3`
**1:02 · 78 bpm · F major · piano + strings · instrumental**
Grand piano leads; warm violins and cellos come in around the halfway mark and lift it into
one generous, restrained emotional swell near the end. Classic inspirational film-score
shape without tipping into schmaltz.
*Where it fits:* **the strongest match to the current 60s cut.** It's the full length in one
unbroken take, and its build lands about where the film moves from the garden into the cafe.

### 03 · Make Your Day — `03_make_your_day.mp3`
**0:46 · 96 bpm · G major · piano pop · instrumental**
Bright piano chords, warm acoustic guitar, soft brushed drums, a little glockenspiel
sparkle and handclaps buried low. Sunny, radio-warm, the most commercially conventional
of the set.
*Where it fits:* the 30 and the 15 for paid social, where you want energy immediately.
*Note:* 0:46 only. Extending to 60s is a crossfade in the edit, not another render.

### 04 · Green and Gold — `04_green_and_gold.mp3`
**1:02 · 104 bpm · D major · light and playful · instrumental**
Quick bright piano arpeggios, pizzicato strings, glockenspiel and celesta, a light shaker.
Airy, charming, the literal sound of morning sunlight. The most overtly *mood-brightening*
cue of the five.
*Where it fits:* if the spot should feel delightful rather than moving. Pairs especially
well with the pickle sign coming alive.

### 05 · A Small Good Thing — `05_small_good_thing.mp3`
**1:02 · 80 bpm · B♭ major · piano ballad · WITH VOCAL**
Piano and warm strings under a single warm female vocal, building into a full-hearted
chorus with brushed drums arriving late. The only sung option in this set, with new lyrics
written for it (below) — more inspirational than the americana theme, less jokey.
*Where it fits:* the emotional version of the spot. A vocal carries meaning the pictures
don't have to, which means the film could lose its end-card copy entirely.

---

## The lyric for 05

> **Verse**
> Morning comes up over Store Street,
> same green door, same open sign,
> somebody's been up since the light was grey
> making something good take its time.
>
> **Chorus**
> And it's a small good thing
> in a loud and hurried world —
> just a little green door
> and a plate you can't finish, and more.
> Come on in, come on in…
> it'll make your day.
>
> **Verse**
> Out in the garden the lettuce is waking,
> peppers still holding the dew.
> Everything here had to grow somewhere first,
> and most of it grew for you.
>
> **Chorus** *(repeat, full)*

Original, written for this project.

---

## Recommendation

**02 "Something Good"** under the current 60, **03 "Make Your Day"** under the cutdowns.
If the spot is ever recut around a voice — yours or the owner's — switch to **01 "First
Light"**, which is the only one sparse enough to leave room.

**05** is the wildcard. It changes what the film *is* rather than how it feels, so it's
worth hearing against picture before deciding.

---

## The 45-second problem, corrected

`build/RENDER_NOTES.md` claimed ACE-Step 1.5 turbo no longer fades past 45s, on the evidence
of one 62-second americana render that held level all the way out. **That was wrong — or at
least, not general.** Measuring the last ten seconds of every cue in this set:

| cue | 62s, first seed | after a 4-seed sweep |
|---|---|---|
| 01 first light | −11.5 dB drop | −7.3 dB, best of 4 |
| 02 something good | **−54.6 dB** (silent) | −4.4 dB at seed 88 |
| 03 make your day | −19.5 dB | fades on **all 4 seeds** (37–55 dB) |
| 04 green and gold | −4.0 dB | fine as rendered |
| 05 small good thing | rises into the last chorus | fine as rendered |

So the real rule is: **the fade past ~45s is seed- and content-dependent, not absent and not
guaranteed.** A cue can come back silent for its last ten seconds with no error and no QC
failure — the file exists, runs the right length, and is wrong, which is exactly the class
of failure the playbook warns about everywhere else.

Practical consequence: **measure the tail of every long ACE render.** `build/sweep_uplifting.py`
does it — renders across several seeds, measures head/middle/tail, and keeps whichever holds
within 6 dB. Cues that fade on every seed (03 here) get rendered at 46s instead and extended
in the edit. That check is worth adding to the studio's music path generally, alongside the
existing "audio not flat" QC.
