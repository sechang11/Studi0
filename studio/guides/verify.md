# Verify

`/verify`

## What this page is for

Deciding whether a variable actually does anything. It is the app's quality gate, and it
is deliberately a human one — the question is "can you tell these apart", and only a
person can answer that.

A capability card claims that some variable — say `anime.anim.cg_mix` — changes the
picture. The card comes with one panel per value. Verify shows you the panels side by
side and asks you to look.

Three tabs across the top: **Capability cards**, **Tag examples**, **Already answered**.
A progress bar runs under the header.

## What to do first

Answer ten cards. That is enough to calibrate you.

Each card asks three questions, and only the first is required:

**1. Are these N pictures different from each other?**
Five buttons: **Yes — clearly different** · **Some are, some look the same** ·
**No — they all look the same** · **Not sure** · **Skip**.
Keys `1` `2` `3` `4` and `s`. Once you know what you are doing, this is a keyboard job.

**2. Optional — is any single one obviously wrong?**
Click the picture. Use it for a broken render, or for one that is a duplicate of its
neighbour.

**3. Optional — anything worth telling the next person?**
A free-text box. This is where the value is.

## The three things that will confuse you

**1. You are not being asked whether it looks good.**

The page says so under the question: *"Ignore whether they look good. Just: could you
tell them apart if the labels were removed?"*

A beautiful set of panels you cannot tell apart is a **no**. An ugly set that is clearly
different is a **yes**. Judging beauty here is the commonest way to poison the data.

**2. "Not sure" and "Skip" are real answers, and they are different.**

*Not sure* is a recorded verdict — you looked and could not decide. *Skip* moves on
without recording anything. Use them. An uncertain yes becomes a green badge elsewhere
in the app and stops anybody looking again.

**3. The queue is not the whole library.**

**72 of 209 capability cards have no rendered panels at all**, so they cannot appear
here — there is nothing to look at. The counter has read *"4 of 137 cards verified, 133
left"*. An empty queue would mean everything *renderable* has been judged, not
everything.

## The notes written before the render

Some cards carry a collapsed block labelled *"N note(s) written BEFORE these were
rendered — predictions, not observations"*. Those are somebody's guess about how the
variable would behave, recorded in advance so it could be checked.

Read them **after** you answer, not before. That is the point of keeping them folded.

## Nothing here is permanent

Stated on the page in bold: a verdict is stored as data, with who set it. You can change
one. **Already answered** is where you go back.

## What good output looks like here

The answer is the cheap part. The note is the valuable part.

A good note names **where in the frame** you saw the difference:

- Good: *"the last two are identical"*, *"the wide one loses the character completely"*,
  *"the dots read as falling snow rather than optical mixing"*.
- Useless: *"kind of works"*, *"nice"*.

The single most valuable thing you can produce here is a well-written **no**. It is what
stops a card being marked ready on the strength of an opinion — which this project has
done twice.
