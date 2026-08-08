#!/usr/bin/env python3
"""Speak the same lines in every castable voice, measure them, and build one file to judge.

    python3 studio/_tools/voice_audition.py
    python3 studio/_tools/voice_audition.py --line "Your own test line."

WHY. "The voices sound awkward and unnatural" is a judgement, and judgements need a
comparison to be actionable. This renders identical narration through every voice that is
allowed to be cast, measures what can be measured, and concatenates the lot into one file
with a gap between takes so they can be judged back to back.

THE MEASURABLE PART. Reference length is the one variable already known to matter here and
it is not a small effect: the cloning docs ask for 24-30 seconds of reference audio, and the
narrator carrying all three episodes of THE SALT ROAD is a 10.4 second sample. The dragon is
5.9. Every voice that sounded fine in earlier work - carter, frank, maya - is over 24. That
is a strong enough pattern to test deliberately rather than assume.

THE UNMEASURABLE PART. Whether a voice is pleasant is not a number. Pitch variance and
speech rate are reported because they are real and cheap, but the file is the deliverable
and the listener decides.

BLOCKED PACKS ARE NEVER AUDITIONED. Four voices on this box clone named real people. They
are skipped here exactly as they are skipped everywhere else.
"""
import argparse, json, os, subprocess, sys, time

ROOT = "/home/k4shix/shared/comfy-studio"
sys.path.insert(0, os.path.join(ROOT, "scripts"))
os.environ.setdefault("COMFY_HOST", "127.0.0.1:8188")
from comfy import run, set_path                              # noqa: E402
from epic import load_wf, ensure_local, HOST, COMFY, adur    # noqa: E402

VOICES_DIR = os.path.join(
    COMFY, "custom_nodes", "TTS-Audio-Suite", "voices_examples")

# Named after real people. Never cast, never auditioned.
BLOCKED = ("eastwood", "attenborough", "freeman", "sophie_anderson")

DEFAULT_LINE = ("Every campaign begins the same way. Four people who should not trust "
                "each other, one road, and a rumour worth more than it ought to be.")


def castable():
    out = []
    for base, _, files in os.walk(VOICES_DIR):
        for fn in sorted(files):
            if not fn.endswith(".wav"):
                continue
            rel = os.path.relpath(os.path.join(base, fn), VOICES_DIR).replace("\\", "/")
            if any(b in rel.lower() for b in BLOCKED):
                continue
            out.append(rel)
    return sorted(out)


def say(rel, line, outdir, seed):
    tag = rel.replace("/", "_").replace(".wav", "")
    dst = os.path.join(outdir, "%s.mp3" % tag)
    if os.path.exists(dst):
        return dst
    wf = load_wf("17_higgs_v3_voice.json")
    set_path(wf, "30.inputs.text", line)
    set_path(wf, "30.inputs.narrator_voice", "voices_examples/" + rel)
    set_path(wf, "30.inputs.seed", seed)
    set_path(wf, "40.inputs.filename_prefix", "claude-generated/audition/%s" % tag)
    _, outs = run(HOST, wf, quiet=True)
    if not outs:
        return None
    return ensure_local(outs[0], dst, required=False)


def measure(path):
    """Speech rate and pitch movement - cheap, real, and not the whole story."""
    # NOT -v error: silencedetect reports at info level, so quieting ffmpeg hides the very
    # thing being measured. This read 0 pauses on a control file containing 0.9s of true
    # digital silence before it was caught.
    p = subprocess.run(
        ["ffmpeg", "-hide_banner", "-i", path, "-af",
         "silencedetect=n=-32dB:d=0.12", "-f", "null", "-"],
        capture_output=True, text=True)
    pauses = p.stderr.count("silence_start")
    d = adur(path) or 0.0
    return d, pauses


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--line", default=DEFAULT_LINE)
    ap.add_argument("--seed", type=int, default=4242)
    ap.add_argument("--out", default=os.path.join(ROOT, "studio", "samples", "audition"))
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)

    rows = []
    for rel in castable():
        if rel.startswith("vibevoice/"):
            # A different engine's packs. Feeding one to the higgs graph raises and, before
            # this guard, took the whole audition down after the last higgs voice - so the
            # summary and the comparison file never got written and nothing said why.
            continue
        ref = os.path.join(VOICES_DIR, rel)
        reflen = adur(ref) or 0.0
        try:
            got = say(rel, a.line, a.out, a.seed)
        except Exception as e:
            print("  %-32s FAILED  %s" % (rel, str(e)[:60]))
            continue
        if not got:
            print("  %-32s FAILED" % rel)
            continue
        d, pauses = measure(got)
        words = len(a.line.split())
        rows.append({"voice": rel, "ref_seconds": round(reflen, 1),
                     "spoken_seconds": round(d, 2), "pauses": pauses,
                     "words_per_second": round(words / d, 2) if d else 0,
                     "file": got,
                     "reference_thin": reflen < 24.0})
        print("  %-32s ref %5.1fs   said %5.2fs   %4.2f w/s   %d pauses%s"
              % (rel, reflen, d, words / d if d else 0, pauses,
                 "   <- THIN REFERENCE" if reflen < 24 else ""))

    # One file, takes separated by silence, in the order printed above.
    if rows:
        lst = os.path.join(a.out, "_concat.txt")
        gap = os.path.join(a.out, "_gap.mp3")
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i",
                        "anullsrc=r=44100:cl=mono", "-t", "0.9", gap], check=False)
        with open(lst, "w") as f:
            for r in rows:
                f.write("file '%s'\nfile '%s'\n" % (r["file"], gap))
        comp = os.path.join(a.out, "AUDITION.mp3")
        r = subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0",
                            "-i", lst, "-c:a", "libmp3lame", "-q:a", "3", comp],
                           capture_output=True, text=True)
        if not os.path.exists(comp):
            print("  could not build the comparison file: %s"
                  % (r.stderr.strip()[:200] or "no error given"))
        json.dump({"line": a.line, "order": [r["voice"] for r in rows], "takes": rows},
                  open(os.path.join(a.out, "audition.json"), "w"), indent=1)
        thin = [r["voice"] for r in rows if r["reference_thin"]]
        print("\n  %s" % comp)
        print("  %d takes, in the printed order." % len(rows))
        print("  %d of %d have a reference under the 24s the docs ask for: %s"
              % (len(thin), len(rows), ", ".join(thin[:6]) + (" ..." if len(thin) > 6 else "")))


if __name__ == "__main__":
    main()
