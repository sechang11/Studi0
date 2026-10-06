#!/usr/bin/env python3
"""studio/_tools/lyric_check.py - can the words be heard? (2026-10-06)

The director, round 9: "the current one's lyrics aren't really audible". A speech recognizer listens to the sung
track line by line (the segment times sing.py wrote) and the words it hears are matched against the lyrics:
word accuracy = 1 - word error rate (edits / words). IBM Granite Speech 4.1 2B (Apache-2.0; on the box at
~/ComfyUI/models/TTS/granite_asr), on the GPU under a memory cap.
    python3 lyric_check.py SUNG.wav SUNG.json [MIX.wav] [--tempo=2.5]   (MIX: the same words in the finished mix;
    --tempo: each line played faster first - for slow, held singing a speech recognizer cannot parse)"""
import json
import os
import re
import sys

import numpy as np
import torch

GRANITE = os.path.expanduser("~/ComfyUI/models/TTS/granite_asr/granite-speech-4.1-2b")


def norm(s):
    return [w for w in re.sub(r"[^a-z' ]", " ", s.lower().replace("’", "'")).split() if w]


def wer(ref, hyp):
    r, h = norm(ref), norm(hyp)
    d = np.zeros((len(r) + 1, len(h) + 1), dtype=int)
    d[:, 0], d[0, :] = range(len(r) + 1), range(len(h) + 1)
    for i in range(1, len(r) + 1):
        for j in range(1, len(h) + 1):
            d[i, j] = min(d[i - 1, j] + 1, d[i, j - 1] + 1, d[i - 1, j - 1] + (r[i - 1] != h[j - 1]))
    return d[len(r), len(h)] / max(1, len(r))


def main():
    import librosa
    from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    tempo = float(next((a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("--tempo=")), 1.0))
    sung, meta = args[0], json.load(open(args[1]))
    mix = args[2] if len(args) > 2 else None
    proc = AutoProcessor.from_pretrained(GRANITE)
    tok = proc.tokenizer
    model = AutoModelForSpeechSeq2Seq.from_pretrained(GRANITE, dtype=torch.bfloat16).to("cuda").eval()
    chat = [{"role": "user", "content": "<|audio|>can you transcribe the speech into a written format?"}]
    prompt = tok.apply_chat_template(chat, tokenize=False, add_generation_prompt=True)
    tracks = [("vocal", sung)] + ([("mix", mix)] if mix else [])
    for name, path in tracks:
        y, _ = librosa.load(path, sr=16000, mono=True)
        accs = []
        for seg in meta["segments"]:
            a, b = seg["time"][0] / 1000.0, seg["time"][1] / 1000.0
            clip = y[max(0, int(a * 16000)): int((b + 0.25) * 16000)]
            if tempo != 1.0:
                # a recognizer trained on speech misses words held for seconds (a slow chorus scored 0 %): the
                # line played faster, its pitch kept, so the words come at speaking length
                clip = librosa.effects.time_stretch(clip, rate=tempo)
            inputs = proc(prompt, torch.from_numpy(clip).unsqueeze(0), device="cuda", return_tensors="pt").to("cuda")
            with torch.no_grad():
                outp = model.generate(**inputs, max_new_tokens=60, num_beams=1, do_sample=False)
            heard = tok.batch_decode(outp[:, inputs["input_ids"].shape[1]:], skip_special_tokens=True)[0].strip()
            acc = max(0.0, 1.0 - wer(seg["lyric"], heard))
            accs.append(acc)
            print("  %-5s %-48s heard: %s  (%.0f%%)" % (name, seg["lyric"][:48], heard[:60], 100 * acc), flush=True)
        print("%s: words heard %.0f%% (lines at 100%%: %d of %d)" % (name, 100 * float(np.mean(accs)),
                                                                   sum(1 for x in accs if x >= 0.999), len(accs)))


if __name__ == "__main__":
    main()
