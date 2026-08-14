"""Re-encode the derived 640x360 card panels from PNG to WebP.

Additive and safe: writes <name>.webp beside <name>.png and never deletes.
The full-size originals live in ~/ComfyUI/output/claude-generated/studio_cards/.
"""
import os, sys, time
from PIL import Image

import argparse
argparse.ArgumentParser(description='to webp').parse_args()
# ^ the CLI contract: --help exits HERE, before any work below runs.
ROOT = os.path.expanduser("~/shared/comfy-studio/studio/samples/vars")
Q = 82

png_bytes = webp_bytes = 0
done = skipped = failed = 0
t0 = time.time()

for dirpath, _, names in os.walk(ROOT):
    for n in sorted(names):
        if not n.endswith(".png"):
            continue
        src = os.path.join(dirpath, n)
        dst = src[:-4] + ".webp"
        try:
            sz = os.path.getsize(src)
            if os.path.exists(dst):
                skipped += 1
                png_bytes += sz
                webp_bytes += os.path.getsize(dst)
                continue
            Image.open(src).convert("RGB").save(dst, "WEBP", quality=Q, method=6)
            png_bytes += sz
            webp_bytes += os.path.getsize(dst)
            done += 1
        except Exception as e:
            failed += 1
            print("FAIL", src, e, flush=True)
        if (done + skipped) % 100 == 0:
            print("%d converted, %d skipped, %.0fs" % (done, skipped, time.time() - t0), flush=True)

print("DONE converted=%d skipped=%d failed=%d in %.0fs" % (done, skipped, failed, time.time() - t0))
print("PNG  %.1f MB" % (png_bytes / 1048576))
print("WEBP %.1f MB  (%.1fx smaller)" % (webp_bytes / 1048576, png_bytes / max(webp_bytes, 1)))
