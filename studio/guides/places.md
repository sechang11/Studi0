# Places

`/places`

## What this page is for

64 cards, each one a setting a scene can happen in. A place card carries two prompts,
not one: a **tags** list for the illustration engine and a **prose** paragraph for the
photographic engine. That is the two-engine rule made concrete — the same forest has to
be described twice, in two languages.

Each card also carries what it suits: which looks, which times of day, and whether it
reads wide or close.

## What to do first

Open one card and read its `tags` and `prose` fields side by side. `pine_forest` is a
good one. Notice they say the same thing in completely different grammar:

- tags: `scenery, no humans, dense pine forest, moss covered trunks, ferns, low fog, fallen log, dirt path, pine needles on ground, shafts of light through canopy`
- prose: *"a dense pine forest with moss-covered trunks and ferns underfoot, low fog drifting between the trees, a fallen log across a dirt path and shafts of light falling through the canopy"*

Then use the two engine buttons at the top — **illustration** and **photographic** — and
compare the two sample images on the same card.

## The three things that will confuse you

**1. A place is a list of nouns, and it collapses if the list gets short.**

The `pine_forest` card's own note says it: *"Thins out to three decorative trees on a
lawn the moment the tag list gets short."* Trunk density, undergrowth and fog all have to
stay named. The ground layer is what makes it a forest rather than a backdrop of trees.
If you trim a place prompt to make room for something else, this is what you lose.

**2. A `replaces` style will overrule your place.**

16 of the 131 style cards re-render the scene *and* override the setting. Pick one of
those and your place card is decoration. Check the style's `compose` field before
blaming the place.

**3. You cannot darken a place with words.**

Same card, same note: *"Do not try to darken it with words; reach for the cold or
overcast grade instead."* Time of day and mood belong to the **look** layer, which is
graded after generation. Words like "dark" and "gloomy" are adjectives, and the model
renders nouns.

## What good output looks like here

- The setting is recognisable as the thing the card names, at a glance, without being
  told.
- The **ground** is present. A forest with no needles, ferns or fallen log is a row of
  trees.
- If a character is in the shot, the place is behind them and they are still the subject.
  A place that swallows the character is a framing problem, not a place problem — go
  closer.
- The two engine samples on the card look like the same location shot two ways, not like
  two different locations.

## A cosmetic bug

Place card descriptions clip mid-word with no ellipsis. `pine_forest` is a visible
example. The text is complete in the JSON; only the display truncates.
