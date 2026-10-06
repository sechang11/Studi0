#!/usr/bin/env python3
"""studio/_tools/sing.py - words sung on a song's own melody (2026-10-06).

SoulX-Singer (Soul AI Lab, Feb 2026, Apache-2.0) sings exact notes and words in the voice of a prompt clip. This
fits a song's lyrics onto the lead sheet (notes_cover.py `prepare`) and sings them:
  - a SONG is sections of the original (a verse on the main theme, a chorus on the second theme), each with its
    lines; a line spans `line_bars` bars and starts with the pickups just before its first bar (0.6 s);
  - ONE WORD PER NOTE (a held note carries the line's stressed word; more words than notes split the longest
    note, more notes than words slur the last word on); the tune shifted per section into a voice's range;
  - a breath (<SP>) at the end of each line; one segment per line, written at its time into one track.
    python3 sing.py SPEC.json OUT.wav        (writes OUT.json too: the words and their times, for lyric_check.py)
SPEC: {"song": "terra", "speed": 0.9, "transpose": 0, "mode": null, "seed": 1,
       "sections": [{"start": 6.93, "end": 54.83, "shift": -12, "line_bars": 2, "lines": ["...", ...]}, ...]}
The code was written for transformers 4.41 / torchaudio 2.2; ComfyUI's Python has 5.x / 2.11 - the shims below
(the vendored code at ~/music-tools/svs/SoulX-Singer untouched), and the checkpoint is loaded WEIGHTS ONLY.
The voice is the model's example English prompt: a TEST voice - an AI-made voice before anything is kept.
"""
import json
import os
import re
import sys

import numpy as np
import soundfile as sf
import torch

MT = os.path.expanduser("~/music-tools")
SX = os.path.join(MT, "svs", "SoulX-Singer")
BREATH, LEAD = 0.18, 0.12
CMU = {  # ARPAbet for the words of the songs written so far; a missing word stops the run (add it here)
    "through": "TH R UW1", "the": "DH AH0", "snow": "S N OW1", "a": "AH0", "lone": "L OW1 N",
    "spark": "S P AA1 R K", "still": "S T IH1 L", "burns": "B ER1 N Z", "and": "AH0 N D", "no": "N OW1",
    "one": "W AH1 N", "knows": "N OW1 Z", "how": "HH AW1", "it": "IH1 T", "glows": "G L OW1 Z", "all": "AO1 L",
    "long": "L AO1 NG", "night": "N AY1 T", "i": "AY1", "hold": "HH OW1 L D", "on": "AA1 N",
    "calling": "K AO1 L IH0 NG", "me": "M IY1", "home": "HH OW1 M", "storm": "S T AO1 R M", "walk": "W AO1 K",
    "where": "W EH1 R", "rivers": "R IH1 V ER0 Z", "run": "R AH1 N", "cold": "K OW1 L D", "sees": "S IY1 Z",
    "fire": "F AY1 ER0", "grow": "G R OW1", "am": "AE1 M", "not": "N AA1 T", "light": "L AY1 T",
    "finding": "F AY1 N D IH0 NG", "my": "M AY1", "way": "W EY1", "in": "IH0 N", "darkness": "D AA1 R K N AH0 S",
    "i'll": "AY1 L", "be": "B IY1", "your": "Y AO1 R", "always": "AO1 L W EY2 Z", "under": "AH1 N D ER0",
    "moon": "M UW1 N", "white": "W AY1 T", "fields": "F IY1 L D Z", "lie": "L AY1", "hear": "HH IY1 R",
    "you": "Y UW1", "call": "K AO1 L", "name": "N EY1 M", "over": "OW1 V ER0", "hills": "HH IH1 L Z",
    "far": "F AA1 R", "away": "AH0 W EY1", "from": "F R AH1 M", "ember": "EH1 M B ER0", "of": "AH1 V",
    "so": "S OW1", "will": "W IH1 L", "follow": "F AA1 L OW0", "road": "R OW1 D", "to": "T UW1",
    "bright": "B R AY1 T", "stars": "S T AA1 R Z", "lead": "L IY1 D", "carry": "K AE1 R IY0",
    "heart": "HH AA1 R T", "never": "N EH1 V ER0", "alone": "AH0 L OW1 N", "embers": "EH1 M B ER0 Z",
    "burning": "B ER1 N IH0 NG", "while": "W AY1 L", "there": "DH EH1 R", "is": "IH1 Z", "breath": "B R EH1 TH",
    "for": "F AO1 R", "close": "K L OW1 Z", "eyes": "AY1 Z", "now": "N AW1", "are": "AA1 R", "near": "N IH1 R",
    "warm": "W AO1 R M", "falls": "F AO1 L Z", "soft": "S AA1 F T", "tonight": "T AH0 N AY1 T",
    "sleep": "S L IY1 P", "little": "L IH1 T AH0 L", "when": "W EH1 N", "wake": "W EY1 K",
    "morning": "M AO1 R N IH0 NG", "bring": "B R IH1 NG", "stay": "S T EY1", "right": "R AY1 T", "by": "B AY1",
    "go": "G OW1", "love": "L AH1 V", "leave": "L IY1 V", "dream": "D R IY1 M", "spring": "S P R IH1 NG",
    "flowers": "F L AW1 ER0 Z", "world": "W ER1 L D", "with": "W IH1 DH", "dear": "D IH1 R", "open": "OW1 P AH0 N",
    "new": "N UW1", "here": "HH IH1 R", "whole": "HH OW1 L", "sings": "S IH1 NG Z", "out": "AW1 T",
    "loud": "L AW1 D", "up": "AH1 P", "blue": "B L UW1", "sky": "S K AY1", "birds": "B ER1 D Z", "fly": "F L AY1",
    "sun": "S AH1 N", "melting": "M EH1 L T IH0 NG", "golden": "G OW1 L D AH0 N", "gone": "G AO1 N",
    "comes": "K AH1 M Z", "come": "K AH1 M", "rise": "R AY1 Z", "into": "IH1 N T UW0", "this": "DH IH1 S",
    "day": "D EY1", "hush": "HH AH1 SH", "safe": "S EY1 F", "arms": "AA1 R M Z", "keep": "K IY1 P",
    "falling": "F AO1 L IH0 NG", "lonely": "L OW1 N L IY0", "can": "K AE1 N", "back": "B AE1 K", "as": "AE1 Z",
    "grows": "G R OW1 Z", "let": "L EH1 T", "shelter": "SH EH1 L T ER0", "wait": "W EY1 T", "for": "F AO1 R",
    "every": "EH1 V R IY0", "breathe": "B R IY1 DH", "until": "AH0 N T IH1 L", "morning": "M AO1 R N IH0 NG",
    "feel": "F IY1 L", "dance": "D AE1 N S", "sing": "S IH1 NG", "song": "S AO1 NG", "we": "W IY1",
    "our": "AW1 ER0", "us": "AH1 S", "fly": "F L AY1", "free": "F R IY1", "time": "T AY1 M", "do": "D UW1",
    "know": "N OW1", "that": "DH AE1 T", "stand": "S T AE1 N D", "side": "S AY1 D", "silver": "S IH1 L V ER0",
    "glow": "G L OW1", "gentle": "JH EH1 N T AH0 L", "softly": "S AO1 F T L IY0", "dreams": "D R IY1 M Z",
    "watch": "W AA1 CH", "over": "OW1 V ER0", "slowly": "S L OW1 L IY0", "starlight": "S T AA1 R L AY2 T",
    "brave": "B R EY1 V", "rise": "R AY1 Z", "high": "HH AY1", "march": "M AA1 R CH", "together": "T AH0 G EH1 DH ER0",
    "hearts": "HH AA1 R T S", "strong": "S T R AO1 NG", "dawn": "D AO1 N", "shine": "SH AY1 N",
    "brighter": "B R AY1 T ER0", "sunlight": "S AH1 N L AY2 T", "laugh": "L AE1 F", "smile": "S M AY1 L",
    "open": "OW1 P AH0 N", "wide": "W AY1 D", "colors": "K AH1 L ER0 Z", "skies": "S K AY1 Z",
    "warmer": "W AO1 R M ER0", "winter": "W IH1 N T ER0", "is": "IH1 Z", "over": "OW1 V ER0",
    "follow": "F AA1 L OW0", "beside": "B IH0 S AY1 D", "fear": "F IH1 R", "far": "F AA1 R", "all": "AO1 L",
    "an": "AE1 N", "brand": "B R AE1 N D", "clear": "K L IH1 R", "color": "K AH1 L ER0", "down": "D AW1 N",
    "finally": "F AY1 N AH0 L IY0", "gently": "JH EH1 N T L IY0", "glowing": "G L OW1 IH0 NG",
    "holding": "HH OW1 L D IH0 NG", "low": "L OW1", "nothing": "N AH1 TH IH0 NG", "quiet": "K W AY1 AH0 T",
    "shining": "SH AY1 N IH0 NG", "singing": "S IH1 NG IH0 NG", "sleeping": "S L IY1 P IH0 NG", "take": "T EY1 K",
    "inside": "IH0 N S AY1 D", "see": "S IY1",
}


def words(line):
    return [w for w in re.sub(r"[^a-zA-Z' ]", " ", line).split() if w]


def build(spec, sh):
    """the target metadata: one segment per line, times in the OUTPUT (sections back to back, at spec speed)"""
    speed = float(spec.get("speed", 1.0))
    tr = int(spec.get("transpose", 0))
    segs, offset = [], 0.0
    for sec in spec["sections"]:
        a, b = float(sec["start"]), float(sec["end"])
        lb = int(sec.get("line_bars", 2))
        bars = [x for x in sh["bars"] if a - 0.05 <= x < b - 0.05]
        mel = [n for n in sh["melody"] if a - 0.01 <= n[0] < b - 0.6]
        lines = sec["lines"]
        starts = [a] + [bars[lb * k] - 0.6 for k in range(1, len(lines)) if lb * k < len(bars)]
        starts.append(b)
        T = (lambda o: (lambda t: o + (t - a) / speed))(offset)
        for k, line in enumerate(lines):
            ws = words(line)
            notes = [list(n) for n in mel if starts[k] - 1e-6 <= n[0] < starts[k + 1] - 1e-6]
            if not notes:
                continue
            if sec.get("even"):
                # a VOCAL rhythm (2026-10-06, the words unheard at 46 %): a run of sixteenth pickups becomes one
                # note on the run's last pitch, and the long notes are split below for more words - the contour
                # kept, the words at a steady, speech-like rate instead of swallowed or stretched into vowels
                e8, merged, run = sh["eighth"], [], []
                for n in notes:
                    if n[1] - n[0] < 0.75 * e8:
                        run.append(n)
                        continue
                    if run:
                        merged.append([run[0][0], run[-1][1]] + run[-1][2:])
                        run = []
                    merged.append(n)
                if run:
                    merged.append([run[0][0], run[-1][1]] + run[-1][2:])
                notes = merged
            while len(notes) < len(ws):
                i = max(range(len(notes)), key=lambda j: notes[j][1] - notes[j][0])
                x, y = notes[i][0], notes[i][1]
                notes[i:i + 1] = [[x, (x + y) / 2] + notes[i][2:], [(x + y) / 2, y] + notes[i][2:]]
            toks = [("<SP>", "<SP>", LEAD, 0, 1)]
            seg0 = T(notes[0][0]) - LEAD
            for j, n in enumerate(notes):
                w = ws[min(j, len(ws) - 1)]
                if w.lower() not in CMU:
                    sys.exit("no phonemes for %r - add it to CMU in sing.py" % w)
                nxt = notes[j + 1][0] if j + 1 < len(notes) else starts[k + 1]
                dur = T(min(n[1], nxt)) - T(n[0])
                gap = T(nxt) - T(n[1]) if j + 1 < len(notes) and T(nxt) - T(n[1]) > 0.02 else 0.0
                if j == len(notes) - 1:
                    dur = max(0.15, T(starts[k + 1]) - T(n[0]) - BREATH - LEAD)
                toks.append((w, "en_" + CMU[w.lower()].replace(" ", "-"), dur,
                             n[2] + int(sec.get("shift", -12)) + tr, 2 if j < len(ws) else 3))
                if gap > 0:
                    toks.append(("<SP>", "<SP>", gap, 0, 1))
            seg_end = T(starts[k + 1]) - LEAD
            toks.append(("<SP>", "<SP>", max(0.02, seg_end - seg0 - sum(t[2] for t in toks)), 0, 1))
            segs.append({"index": "line_%d" % (len(segs) + 1), "language": "English",
                         "time": [int(round(seg0 * 1000)), int(round(seg_end * 1000))],
                         "duration": " ".join("%.3f" % t[2] for t in toks),
                         "text": " ".join(t[0] for t in toks), "phoneme": " ".join(t[1] for t in toks),
                         "note_pitch": " ".join(str(int(t[3])) for t in toks),
                         "note_type": " ".join(str(t[4]) for t in toks), "f0": "", "lyric": line})
        offset += (b - a) / speed
    return segs, offset


def shims():
    import transformers
    import torchaudio
    from transformers.models.llama import configuration_llama as cl
    LC = cl.LlamaConfig

    def llama_config(*args, **kw):          # 4.41 took positional arguments; 5.x keywords only
        kw.update(dict(zip(["vocab_size", "hidden_size", "intermediate_size", "num_hidden_layers",
                            "num_attention_heads"], args)))
        return LC(**kw)
    transformers.LlamaConfig = llama_config

    def load(path, *a, **k):                # torchaudio 2.11 has no load without torchcodec
        y, sr = sf.read(path, dtype="float32", always_2d=True)
        return torch.from_numpy(y.T.copy()), sr
    torchaudio.load = load
    sys.path.insert(0, SX)
    from soulxsinger.models.modules import llama as sx_llama
    from transformers.models.llama.modeling_llama import LlamaRotaryEmbedding

    def nar_forward(self, hidden_states, cond_embedding, attention_mask=None, position_ids=None,
                    past_key_value=None, output_attentions=False, use_cache=False):
        # 5.x LlamaAttention takes the rotary embeddings as an argument and returns two values
        residual = hidden_states
        hidden_states = self.input_layernorm(hidden_states, cond_embedding=cond_embedding)
        if getattr(self, "_rope", None) is None:
            self._rope = LlamaRotaryEmbedding(config=self.self_attn.config).to(hidden_states.device)
        cos, sin = self._rope(hidden_states, position_ids)
        hidden_states = residual + self.self_attn(hidden_states=hidden_states, position_embeddings=(cos, sin),
                                                  attention_mask=attention_mask)[0]
        residual = hidden_states
        hidden_states = self.post_attention_layernorm(hidden_states, cond_embedding=cond_embedding)
        return (residual + self.mlp(hidden_states), None, None)
    sx_llama.LlamaNARDecoderLayer.forward = nar_forward


def sing(segs, total, out, seed=1, prompt="en", cfg=None, steps=None):
    shims()
    from soulxsinger.models.soulxsinger import SoulXSinger
    from soulxsinger.utils.data_processor import DataProcessor
    from soulxsinger.utils.file_utils import load_config
    config = load_config(os.path.join(SX, "soulxsinger", "config", "soulxsinger.yaml"))
    model = SoulXSinger(config).to("cuda")
    ck = torch.load(os.path.join(SX, "pretrained_models", "SoulX-Singer", "model.pt"), weights_only=True,
                    map_location="cpu")
    model.load_state_dict(ck["state_dict"], strict=True)
    model.half()
    model.mel.float()
    model.eval()
    dp = DataProcessor(hop_size=config.audio.hop_size, sample_rate=config.audio.sample_rate,
                       phoneset_path=os.path.join(SX, "soulxsinger", "utils", "phoneme", "phone_set.json"),
                       device="cuda")
    pw = os.path.join(MT, "svs", "%s_prompt.wav" % prompt)
    if not os.path.exists(pw):
        import subprocess
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", os.path.join(SX, "example", "audio",
                        "%s_prompt.mp3" % prompt), "-ac", "1", "-ar", "24000", pw], check=True)
    pmeta = json.load(open(os.path.join(SX, "example", "audio", "%s_prompt.json" % prompt)))[0]
    pdata = dp.process(pmeta, pw)
    sr = config.audio.sample_rate
    y_all = np.zeros(int((total + 2) * sr), dtype=np.float32)
    torch.manual_seed(seed)
    for seg in segs:
        s0 = int(seg["time"][0] / 1000 * sr)
        with torch.no_grad():
            y = model.infer({"prompt": pdata, "target": dp.process(dict(seg), None)}, auto_shift=False,
                            pitch_shift=0, n_steps=steps or config.infer.n_steps, cfg=cfg or config.infer.cfg,
                            control="score",
                            use_fp16=True)
        y = y.squeeze().float().cpu().numpy()
        if s0 < 0:
            y, s0 = y[-s0:], 0
        n = min(len(y), len(y_all) - s0)
        f = min(int(0.02 * sr), n // 2)
        y = y[:n].copy()
        y[:f] *= np.linspace(0, 1, f)
        y[n - f:n] *= np.linspace(1, 0, f)
        y_all[s0:s0 + n] += y
    sf.write(out, y_all, sr)


def main():
    spec_p, out = sys.argv[1], sys.argv[2]
    spec = json.load(open(spec_p))
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    sh = json.load(open(os.path.join(MT, "work", spec.get("song", "terra"), "leadsheet.json")))
    if spec.get("mode") == "major":
        import notes_cover
        sh = notes_cover.to_major(sh)
    segs, total = build(spec, sh)
    json.dump({"segments": segs, "total": total, "speed": spec.get("speed", 1.0)}, open(out[:-4] + ".json", "w"),
              indent=1)
    sing(segs, total, out, int(spec.get("seed", 1)), spec.get("prompt", "en"), spec.get("cfg"), spec.get("steps"))
    print("sung %d lines, %.1f s -> %s" % (len(segs), total, out))


if __name__ == "__main__":
    main()
