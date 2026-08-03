# The 20-minute anime episode

A different form from the vertical short, not a longer one. The short's rule was "generate
few, cut many". Here the rule is the opposite: **most shots are held, and tension comes from
what is withheld.**

## Why the first 20-minute attempt failed

It was rejected with "it's terrible, I don't think anyone would watch it." Mean motion 2.25,
median shot ~9s, no dialogue, wall-to-wall narration.

The wrong lesson to draw is "never hold a shot." Real anime is largely held drawings with
camera moves - limited animation is the form, not a shortcut. The right lesson:

> **A hold must be motivated.** It lands a line, shows a decision being made, or withholds
> an answer. A held establishing shot with nothing happening is dead air, and an audience
> feels the difference immediately even if they cannot name it.

The rejected film held shots that were doing no dramatic work. That is the failure, and it
is a *writing* failure that no amount of motion would have rescued.

## Act structure (TV anime, ~20 min)

    0:00-1:30   COLD OPEN      A hook that poses a question. Never exposition.
    1:30-2:00   TITLE          Title card. Buys a tonal reset.
    2:00-7:00   ACT ONE        World, protagonist, antagonist, stakes. The audience must
                               be able to state what the character WANTS by 7:00.
    7:00-7:15   EYECATCH       Mid-episode break. Anime convention; also a real breath.
    7:15-15:00  ACT TWO        Escalation, then a genuine setback. The protagonist must
                               lose something here or the climax is unearned.
    15:00-19:00 ACT THREE      Climax. This is where the SAKUGA goes - one or two bursts.
    19:00-20:00 TAG            Denouement. Answer the cold open's question, pose the next.

## The director's toolkit

**Scene grammar.** Every scene: establish (where) -> master (geography) -> into coverage
(close-ups, over-shoulder, reactions). Cutting to a close-up before the audience knows the
space is disorienting - which is exactly what the vertical short did deliberately, and what
an episode must not do.

**Dialogue.** Shot / reverse-shot, and hold a beat of SILENCE after each line. Cutting on the
last syllable is the most common way an AI edit betrays itself. Reactions are where an
episode earns its emotion; the rejected film had none.

**Pillow shots.** The cutaway with no people - sky, a flag, an empty seat. Marks a passage of
time and lets a moment settle. Anime uses these constantly and they are cheap.

**Withhold.** Do not show the antagonist's face in the cold open. Do not resolve the
question posed at 1:30 until 19:00. Suspense is information deliberately delayed.

**Sakuga discipline.** One or two bursts per episode. If everything is fast, nothing is. The
entire vertical short was sakuga - which is correct for 60 seconds and wrong for 20 minutes.

**Silence before impact.** The longest, quietest shot in the episode goes immediately before
the climax. Contrast makes the hit land twice as hard.

**Rule of three.** Plant something in Act One, echo it in Act Two, pay it off in Act Three.

## Templates

`scripts/scene_templates.py` provides the episode grammar: `establish`, `master`, `speak`,
`react`, `pillow`, `insert`, `build`, `sakuga`, `hold_silent`. Named for the dramatic job
each does, not for length.

## Scale, honestly

    20 min = 1200s at ~3s average shot   ->  ~400 shots
    ~350 generated clips at ~25s each    ->  ~2.5 hours GPU
    ~150 voice lines, music cues, SFX    ->  ~30 min more

Roughly a three-hour render. Worth confirming the script reads before committing that.

## Measurement

`analyze_shots.py` still applies, but the target changes. In the short, low motion meant
failure. Here, a low-motion shot is fine IF it is carrying a line or a reaction - so read
the DEAD list against the script, not on its own. The real check for an episode is
different and cannot be automated: can a viewer state what the protagonist wants, and what
is stopping them, at the halfway mark?

---

# Showing want, effort, struggle and success

The default failure is to have a character SAY they want it. Saying it is the weakest
possible version. Anime shows want through **cost** and force through **effect**.

## "How badly do they want it?" — show the cost, not the wish

A character who says "I want this more than anything" is asking to be believed. A character
who plays on a rolled ankle is not asking.

  * **Damage continuity.** The single most effective device available to us, and it is free
    - it lives in the prompt. Track a per-character STATE that only ever worsens across the
    episode: clean -> sweat -> dirt -> torn kit -> blood -> limping. By minute 17 the
    audience has watched him be ground down without a word being spoken about it. Reset it
    and the episode silently loses its spine, so it is worth encoding rather than trusting
    to memory.
  * **What he gives up.** VIRO is booked; one more and he is off. He keeps going. The
    yellow card is not a plot beat, it is a price tag on his desire.
  * **Breath.** Hands on knees, chest heaving, shoulders. Exhaustion is want made visible.
  * **Interior monologue over a held face.** An anime staple and cheap for us - we have TTS
    and the shot is a still. But it must contradict or complicate the surface, never
    narrate it. Over a blank face: *"He's not even tired."* That is want.

## "Attacking the ball with all their might" — show the effect, not the act

Force is invisible. Only its consequences are photographable.

  * **Cut away at the moment of contact.** The most powerful strike in anime is often not
    shown. Wind-up -> WHITE FRAME -> the net already bulging. The audience supplies a hit
    bigger than anything we could render.
  * **Deformation.** The ball flattening against the boot. Anime smear frames. A body
    twisting past what a real body does.
  * **The world reacting.** Turf tearing, the crossbar still ringing, a defender's hair
    blown back, the keeper not moving because he never saw it. Cheaper to generate than a
    good action pose and reads as more powerful.
  * **Speed ramping.** Slow into the wind-up, snap to full speed on contact. The contrast
    is the impact. `ramp` in fx_chain.
  * **Low angle.** Camera below the subject makes a figure powerful; above makes them
    small. Use it deliberately - low for the strike, high for the low point.
  * **Silence, then crack.** Drop the score entirely for the half-second before contact.
    An impact is as loud as the quiet before it.

## Struggle — repetition with diminishing returns

  * **Visual rhyme.** He attempts the same thing three times. Give each attempt LESS screen
    time than the last. The edit itself runs out of patience with him, and the audience
    feels the futility without being told.
  * **The obstacle stays in frame.** RASK at the edge of shot even when the scene is not
    about him. Presence is pressure.
  * **The intrusive flashback.** At maximum effort, cut one or two frames of last year's
    defeat. Not a memory the character is enjoying - a memory attacking him.
  * **Subjective sound.** Crowd drops to nothing, only breathing left. Puts the audience
    inside his head with no line of dialogue.

## Obstacles — make them act, not exist

An obstacle that merely stands there is scenery. RASK reads VIRO's runs before he makes
them, helps him up, gives him advice that is *correct*. He is hardest to beat when he is
being decent - a wall you cannot even resent.

Also: the clock. A countdown converts every shot into a shot with a deadline.

## Success — delay, then release, then withhold again

  * **Earn it with silence.** The longest quietest shot in the episode goes immediately
    before the goal.
  * **Show it on other faces.** Do not cut to the scorer first. Cut to the boy in the
    stand, the keeper on the ground, RASK. Reflected success is bigger than the act.
  * **Collapse, do not celebrate.** Release reads as exhaustion, not triumph.
  * **Give back the withheld thing.** RASK's face has shown nothing for nineteen minutes.
    At 18:50 it shows something. That single frame is the payoff of the whole runtime.
  * **Do not resolve everything.** He drew; he did not win. "Next year, then" - and there
    is no next year.

## The one rule under all of it

**Show the price, and the audience infers the desire.** Every device above is a way of
photographing a price.
