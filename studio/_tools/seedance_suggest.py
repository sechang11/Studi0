#!/usr/bin/env python3
"""studio/_tools/seedance_suggest.py - does this shot want the paid engine? A suggestion, with reasons.

The studio spends nothing by default, and the paid engine is for what the local engines measurably
cannot do (playbook §96.4, §98, §0.3). This reads a shot's words and its takes' measurements for those
things and says so, with the evidence:

  speed      a fast body - running, striking, leaping, fighting, a flurry. The one gap measured
             every time: motion fidelity at speed (§98).
  distance   a walk or an entrance over distance: our engines hold the walker, not the walk (§95).
  instant    an effect that must arrive at an instant and clear - sparks at each blow, a burst, a
             splash (the breakdown's rule 3; LTX accumulates effects, H3 only partly clears, §98.3).
  contact    two people touching - a grab, a push, a fight, a dance (identity through contact is
             where two faces get swapped or merged).
  crowd      three or more people, or a crowd (the studio holds two faces per frame, not three).
  camera     a fast or travelling camera - tracking, orbiting, a whip pan.
  measured   every take so far carries a fault (a drifted face, an unheard line).

    level:  "strong" (send it), "consider" (a paid take might beat ours), "none"

and a Seedance 2.5 reference-mode prompt to start from - the shot's own hand-written `seedance.prompt`
when the script has one, otherwise one built from its words with [image 1] the composed start frame,
[image 2] the character and [image 3] the place, which is what fight.py --seedance sends.
"""
import re

RATE = 0.09      # $/s: Seedance 2.0 Fast, the last rate verified here (playbook §0.1); 2.5's is not

# bare "runs" is left out: "a bead of sweat runs down", "her thumb runs along the edge"
SPEED = ("run", "running", "runs at", "runs toward", "runs towards", "runs across", "runs off", "runs away",
         "runs past", "runs into", "sprint", "sprints", "sprinting", "dash", "dashes", "chase", "chases",
         "chasing", "leap", "leaps", "jump", "jumps", "dive", "dives", "flip", "flips", "somersault",
         "spin", "spins", "kick", "kicks", "punch", "punches", "strike", "strikes", "swing", "swings",
         "fight", "fights", "dodge", "dodges", "tackle", "tackles", "tumble", "tumbles", "hurls", "slams",
         "lunge", "lunges", "charge", "charges", "flurry", "rapid", "fast", "whirl", "whirls")
# verbs of travel only: "far down the aisle a man stands still" is a place, not a walk, and "a smile
# crosses her face" is not a crossing - so "crosses" only counts with somewhere to cross
DISTANCE = ("walks", "walk", "walking", "strides", "stride", "steps into", "step into", "comes down",
            "crosses the room", "crosses the street", "crosses the floor", "crosses the aisle", "crosses the road",
            "walks across", "approaches", "enters", "walks in", "paces", "wanders", "climbs", "descends",
            "walks toward", "walks towards", "comes toward", "comes towards", "runs toward")
INSTANT = ("burst", "bursts", "explode", "explodes", "explosion", "erupts", "erupt", "flash", "flashes",
           "sparks", "spray", "sprays", "shatter", "shatters", "splash", "splashes", "impact", "at the instant",
           "at each blow", "at the exact instant", "debris", "shockwave", "steam bursts", "flare", "flares")
CONTACT = ("grabs", "grab", "hugs", "embrace", "embraces", "pushes", "shoves", "wrestle", "wrestles",
           "dance", "dances", "dancing", "catches", "shake hands", "kiss", "kisses", "fight", "fights",
           "punches", "strikes", "carries", "lifts her", "lifts him", "holds her", "holds him")
CROWD = ("crowd", "crowds", "audience", "everyone", "a group of", "people run", "bystanders")
CAMERA = ("tracking", "tracks", "follows", "orbit", "orbits", "circles", "whip pan", "whip-pan",
          "crane", "fpv", "drone", "handheld run", "camera running")

WEIGHT = {"speed": 3, "instant": 2, "contact": 2, "crowd": 2, "distance": 1, "camera": 1, "measured": 1}
WHY = {
    "speed": "a fast body ({}) - motion fidelity at speed is the gap we measured every time (§98)",
    "instant": "an effect keyed to an instant ({}) - LTX lets effects accumulate, H3 only partly clears them "
               "(§98.3, §0.3)",
    "contact": "two people in contact ({}) - where two faces get swapped or merged",
    "crowd": "three or more people ({}) - the studio holds two faces per frame",
    "distance": "a walk or an entrance over distance ({}) - our engines hold the walker, not the walk (§95)",
    "camera": "a travelling camera ({}) - our camera moves are measured and small",
    "measured": "every take so far is faulted ({})",
}


def _hits(text, words):
    t = " " + re.sub(r"[^a-z' ]", " ", text.lower()) + " "
    return sorted({w for w in words if (" %s " % w) in t})


def suggest(shot, place_id, cast, ranked_row=None):
    """shot: a shot-script shot. cast: {id: {...}}. ranked_row: this shot's ranked.json entry, if any."""
    words = " ".join(str(shot.get(k) or "") for k in ("prompt", "title"))
    # what is SAID is not what happens: "Put it down and walk out of here" is a line, not a walk
    words = re.sub(r'"[^"]*"|“[^”]*”', " ", words)
    chars = []
    for r in shot.get("refs", []):
        if r != place_id and r in cast and r not in chars:
            chars.append(r)
    found = {}
    for key, bank in (("speed", SPEED), ("instant", INSTANT), ("distance", DISTANCE), ("camera", CAMERA),
                      ("crowd", CROWD)):
        if key == "distance" and not chars:
            continue            # "down the aisle" in an empty room is the camera's path, not a walk
        h = _hits(words, bank)
        if h:
            found[key] = h
    if len(chars) >= 2:
        h = _hits(words, CONTACT)
        if h:
            found["contact"] = h
    if len(chars) >= 3:
        found.setdefault("crowd", []).append("%d people" % len(chars))
    takes = (ranked_row or {}).get("takes") or []
    if takes and all(t.get("faults") for t in takes):
        found["measured"] = ["%d of %d takes" % (len(takes), len(takes))]
    score = sum(WEIGHT[k] for k in found)
    level = "strong" if score >= 3 else ("consider" if score >= 1 else "none")
    reasons = [WHY[k].format(", ".join(v[:4])) for k, v in sorted(found.items(), key=lambda kv: -WEIGHT[kv[0]])]
    hand = shot.get("seedance") or {}
    secs = int(hand.get("secs") or shot.get("secs") or 5)
    if hand.get("prompt"):
        prompt, source = hand["prompt"], "written by hand in the shot script"
    else:
        who = ""
        if chars:
            c = cast.get(chars[0]) or {}
            who = " [image 2] is %s (%s)." % (chars[0], c.get("role", "the character"))
        prompt = ("[image 1] is the first frame.%s [image 3] is the place. %s Keep the people and the place "
                  "exactly as they are in the pictures." % (who, (shot.get("prompt") or "").strip()))
        source = "built from the shot's words - edit it before sending"
    if hand.get("why"):
        reasons = [hand["why"]] + reasons
        if level == "none":
            level = "consider"
    return {"level": level, "score": score, "reasons": reasons, "found": found, "prompt": prompt,
            "prompt_source": source, "secs": secs, "cost": round(secs * RATE, 2), "rate": RATE,
            "resolution": "1080p", "images": ["anchor_%s.png" % shot.get("id"),
                                               "ref_%s.png" % (chars[0] if chars else place_id),
                                               "ref_%s.png" % place_id]}
