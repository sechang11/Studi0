# Prompting anime checkpoints (Animagine / Illustrious)

Everything here was established by rendering, not assumed. It is written down because the
same checkpoint produced abstract garbage and clean anime on the same GPU minutes apart,
and the only difference was prompt format.

## The finding that mattered

Qwen-Image and SDXL anime checkpoints want OPPOSITE prompt styles:

    Qwen         cinematic natural language
                 "Low hero angle of a tall striker standing on the halfway line, steam
                  rising off him, floodlights flaring behind his head"

    Animagine    danbooru tags, subject first, then camera, then scene
                 "1boy, solo, dark red hair, undercut, yellow eyes, scar on eyebrow,
                  black soccer uniform, number 9, from below, dynamic angle,
                  night stadium, floodlights, crowd, cinematic lighting"

Feeding Qwen-style prompts to Animagine produced **abstract coloured shapes** at denoise
1.0 - not a bad image, no image at all. It is easy to misread that as "the model is
broken" or "this approach does not work". It is a prompt-format failure.

## Quality tokens are load-bearing

    masterpiece, best quality, very aesthetic, absurdres

Not decoration for this model family. Without them output is markedly softer and flatter.
Append to every positive prompt.

## motion blur belongs in the NEGATIVE

Putting `motion blur` in the positive - the obvious thing to do for an action short -
hazes the ENTIRE frame and blows out the highlights. Four otherwise-good keyframes came
back washed out and unusable. Motion comes from the EDIT anyway (see EDITING.md), so:

    negative: motion blur, blurry, overexposed, washed out, white background,
              photorealistic, 3d, western comic, multiple views, lowres, worst quality,
              bad anatomy, bad hands, watermark, text

## Settings that work

    resolution   1344x768 or 1216x832 for 16:9, 1024x1024 for sheets
                 (SDXL native is ~1 MP; going far above invents duplicate limbs)
    steps        28
    cfg          5.0
    sampler      euler_ancestral / normal

## Character consistency

IPAdapter PLUS FACE with an anime-drawn character sheet, weight ~0.6.

Two things worth knowing before tuning it:

  * A detailed tag block (`dark red hair, undercut, yellow eyes, scar on eyebrow`) carries
    MOST of the identity by itself. A weight sweep at 0.0 / 0.4 / 0.7 / 1.0 showed the
    character already recognisable at ZERO. IPAdapter refines the face; it is not what
    makes the character. Do not expect it to rescue a vague description.
  * The sheet must be drawn in the SAME style it will be used in. Feeding a Western-comic
    sheet to an anime checkpoint fights itself - regenerate sheets with the anime model.

  * The `_vit-h` adapter needs the ViT-H encoder (h94 `models/image_encoder/`). The
    ViT-bigG one under `sdxl_models/` loads silently and produces garbage.

## Still open

Night and dark-background tags are not reliably obeyed - stadium backgrounds come back
bright regardless. Fix before the next full render.
