# Dolly zoom (vertigo effect)

Track in while zooming out (or the reverse) so the subject stays the same size while the
background expands or collapses. Dread, realisation, the ground dropping away. Used once in
an episode it is unforgettable; used twice it is a gimmick.

## Why it is blocked

It needs the subject to hold scale while the background changes perspective — a genuine
parallax change, not a crop. `zoompan` scales the whole frame uniformly, so the effect
cannot be faked from a single flat image.

## Paths, cheapest first

1. **Depth-warped 2.5D.** Depth Anything 3 is already installed (`fetch-models.sh control`).
   Estimate depth, displace foreground and background at different rates, then zoom. This is
   the standard "2.5D parallax" trick and is very likely good enough for a 2-second beat.
2. Generate the move directly in the video model by describing it. Unreliable — LTX does not
   take direction this specific.
3. Multi-view generation and a real camera path. Overkill.

Path 1 is a contained experiment: one still, one depth map, one ffmpeg `displace` chain.

## Falls back to

`push`, which is the closest legitimate move.
