#!/usr/bin/env python3
"""Table test for the medium detector, including the case that was wrong."""
import sys
sys.path.insert(0, "studio/_tools")
sys.path.insert(0, "scripts")
import character_new as C

CASES = [
    (True,  "A 35mm colour photograph with shallow depth of field."),
    (True,  "A photographic portrait, studio lighting, 85mm lens."),
    (True,  "A polaroid snapshot, washed out, slight blur."),
    (False, "A digital painting with photorealistic rendering and a cool palette."),
    (False, "A painted digital illustration with soft airbrushed shading."),
    (False, "A stark black ink drawing with heavy hatching."),
    (False, "A 3d render, clay material, soft studio lighting."),
    (False, "A hyper-photorealistic oil painting of a face."),
]
bad = 0
for want, m in CASES:
    got = C.looks_photographic(m)
    ok = got == want
    bad += not ok
    print("  %-4s want %-5s got %-5s  %s" % ("ok" if ok else "FAIL", want, got, m[:58]))
print("\n  %d wrong of %d" % (bad, len(CASES)))
sys.exit(1 if bad else 0)
