#!/usr/bin/env python3
"""studio/_tools/shorts_asr.py - prove the delivered films actually SAY their scripts.

    python3 studio/_tools/shorts_asr.py [--limit N] [--only ID]

WHY. Everything measured so far proves the audio EXISTS and is at the right level. None
of it proves the words are right, and the failure this project has already recorded is a
TTS engine dropping a clause - which leaves loudness, duration and coverage all perfect
and the film wrong. So: transcribe each film's own mix with the Granite speech weights
already on the box, and score the transcript against the script that was written.

SCORING is deliberately blunt and honest. Word-level recall of the script's CONTENT words
(stopwords dropped, because "the" matching proves nothing): what fraction of the words we
asked for come back. A film that scores high is saying its script. A film that scores low
is either mis-speaking it or the mix has buried it under the score - and the report says
which by also reporting the voice stem's own level.

WHAT THE SCORE CANNOT TELL YOU, learned from the transcripts. Granite Speech is an LLM
with an audio input, not an acoustic transcriber, and it PARAPHRASES: "less settled"
came back as "less well-studied", "borrowed in 1954" as "copyrighted in 1950". An
acoustic model mangles phonemes; this one rewrites meaning. So a middling recall score is
NOT evidence of a dropout and must not be read as one.

WHAT IT IS GOOD FOR is the signature it did catch: a whole clause missing from the END
while everything before it transcribes cleanly. That is truncation, and it found the
cut-off last line in all six films rendered before the cutter was fixed. So `tail` -
the recall of the LAST line alone - is reported beside the overall recall, because that
is the number that separates "cut off" from "paraphrased". A low tail with a healthy
body is a real defect; a low overall with a healthy tail is the model being chatty.
"""
import argparse
import json
import os
import re
import subprocess
import sys

TOOLS = os.path.dirname(os.path.abspath(__file__))
STUDIO = os.path.dirname(TOOLS)
ROOT = os.path.dirname(STUDIO)
sys.path.insert(0, TOOLS)

STOP = set("a an the and or but if of to in on at for with from by is are was were be "
           "been it its this that these those you your we our they them he she his her "
           "as so not no do does did can will would could should have has had one two "
           "up out about into over than then there here what which who when".split())


# ASR writes numbers as digits; scripts write them as words. Without this every number
# word counts as a miss - hook-lift, a film about the number twelve, scored 40% on a
# perfectly good read.
NUM = {"zero": "0", "one": "1", "two": "2", "three": "3", "four": "4", "five": "5",
       "six": "6", "seven": "7", "eight": "8", "nine": "9", "ten": "10",
       "eleven": "11", "twelve": "12", "thirteen": "13", "fourteen": "14",
       "fifteen": "15", "sixteen": "16", "seventeen": "17", "eighteen": "18",
       "nineteen": "19", "twenty": "20", "thirty": "30", "forty": "40", "fifty": "50",
       "sixty": "60", "seventy": "70", "eighty": "80", "ninety": "90",
       "hundred": "100", "thousand": "1000"}


def words(s):
    out = []
    for w in re.findall(r"[a-z']+|\d+", str(s).lower()):
        w = NUM.get(w, w)
        if w in STOP:
            continue
        if w.isdigit() or len(w) > 2:
            out.append(w)
    return out


def main():
    ap = argparse.ArgumentParser(description="Do the delivered shorts say their scripts?")
    ap.add_argument("--only")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--device", default=None)
    a = ap.parse_args()
    rows = json.load(open(os.path.join(STUDIO, "samples", "shorts", "shorts.json"),
                          encoding="utf-8"))
    ready = [r for r in rows if r.get("status") == "ready"]
    if a.only:
        ready = [r for r in ready if r["id"] == a.only]
    if a.limit:
        ready = ready[:a.limit]
    if not ready:
        print("nothing delivered yet")
        return 0
    # extract each master's audio once
    wavs, meta = [], {}
    tmp = "/tmp/shorts_asr"
    os.makedirs(tmp, exist_ok=True)
    for r in ready:
        src = os.path.join(STUDIO, r["file"])
        w = os.path.join(tmp, r["id"] + ".wav")
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", src, "-ac", "1",
                        "-ar", "16000", w], capture_output=True)
        if os.path.exists(w):
            wavs.append(w)
            meta[w] = r
    sys.path.insert(0, TOOLS)
    from film_audio import _asr_local
    print("transcribing %d films..." % len(wavs), flush=True)
    got = _asr_local(wavs, device=a.device)

    out, scores = [], []
    for w, text in got.items():
        r = meta[w]
        script = " ".join(r.get("script") or [])
        want, heard = words(script), set(words(text))
        hit = [x for x in want if x in heard]
        score = len(hit) / max(1, len(want))
        # The LAST line alone. A low tail with a healthy body is truncation - a real
        # defect. A low overall with a healthy tail is the LLM paraphrasing.
        last = (r.get("script") or [""])[-1]
        lw = words(last)
        tail = (len([x for x in lw if x in heard]) / len(lw)) if lw else None
        scores.append(score)
        out.append({"id": r["id"], "recall": round(score, 3),
                    "tail": round(tail, 3) if tail is not None else None,
                    "words": len(want), "script": script, "transcript": text})
        print("%-22s recall %.0f%%  tail %s  (%d/%d content words)"
              % (r["id"], 100 * score,
                 "%3.0f%%" % (100 * tail) if tail is not None else "  -",
                 len(hit), len(want)))
        if tail is not None and tail < 0.5:
            print("   LOW TAIL - the last line may be cut off: %r" % last[:120])
        if score < 0.6:
            print("   SCRIPT: %s" % script[:200])
            print("   HEARD : %s" % text[:200])
    p = os.path.join(STUDIO, "samples", "shorts", "asr.json")
    json.dump(out, open(p, "w"), indent=1)
    print("\nmean recall %.0f%% over %d films -> %s"
          % (100 * sum(scores) / len(scores), len(scores), p))
    return 0


if __name__ == "__main__":
    sys.exit(main())
