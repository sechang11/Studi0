# LTX-2.5 runbook - the four commands that finish the job

LTX-2.5 (released 2026-08-12) is the routed video engine's successor and brings NATIVE
MULTI-SHOT generation - connected shots in one pass that hold character, environment,
lighting and voice across cuts. That is the local answer to the multi-shot consistency
question. Everything except the weights is done:

- ComfyUI is on 0.33.1 (LTX-2.5 needs >= 0.32).
- `workflows/51_ltx25_i2v.json` is converted from ComfyUI's own template and validated
  by the server - the only remaining validation errors are the five gated files.
- `text_encoders/gemma4_e2b_it_bf16.safetensors` (ungated, 10.3 GB) is on disk.

The Lightricks repo is GATED. This is the one step only you can do:

1. Log in to HuggingFace, open https://huggingface.co/Lightricks/LTX-2.5 and accept the
   LTX-2.x Community License (free for commercial use under $10M/yr revenue).
2. Create a READ token at https://huggingface.co/settings/tokens.
3. On the box, put the token where the fetch script reads it - NEVER on a command line
   or in a commit:

       echo 'hf_xxx' > ~/.cache/huggingface/token && chmod 600 ~/.cache/huggingface/token

4. Fetch (about 45 GB; resumes if interrupted) and validate:

       bash scripts/fetch-ltx25.sh
       python3 studio/_tools/model_cards.py          # cards flip unavailable -> untested
       python3 studio/_tools/ltx25_probe.py          # renders the same keyframe through
                                                     # 2.3 and 2.5, reports time + SSIM

If step 4's probe is good, the next session routes `video` to 51_ltx25 in engine.video_graph
behind a card flag and builds the multi-shot workflow from `video_ltx2_5_flf2v.json`
(first/last-frame chaining is what the master-frame kit already does with 2.3).

What is NOT worth fetching yet, and why (measured, not guessed):
- MiniMax H3 (open weights 2026-08-03): 62 GB diffusion + 48 GB encoder at bf16, a whole
  new stack; LTX stays the routed family until 2.5 is measured here.
- Wan 2.5/2.6/2.7: not open weights (2.2 remains the ceiling; already on disk, measured
  ~equal fidelity to LTX at 2.5x the time).
- HunyuanVideo 1.5 (on disk, unrouted): would need an A/B against LTX to earn a route.
