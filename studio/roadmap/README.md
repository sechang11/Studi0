# Roadmap — variables the format accepts but the renderer cannot honour yet

Every file here is a variable an author can already write. The compiler accepts it, warns
once, and falls back to something sane. Nothing silently does nothing — a knob that quietly
has no effect is worse than no knob, because you spend a render believing you changed
something.

Each entry states: what it is, why it matters, what blocks it, and the cheapest known path.

| variable | falls back to | difficulty |
|---|---|---|
| `transition: l_cut` / `j_cut` | hard cut | medium — the highest-value item here |
| `camera: dolly_zoom` | push | medium |
| `camera: rack_focus` | static | hard |
| `camera: orbit` | pan | hard |
| `lipsync` | mouths do not match dialogue | hard |
| `shot_size` progression | authored per shot by hand | easy |
| `blocking` (who stands where) | prompt text only | hard |
