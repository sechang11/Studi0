#!/usr/bin/env python3
"""Where do 2.2 seconds a frame go?  One 1920x1088 frame through RealESRGAN x4, timed by part.

A 5090 should push a 1080p frame through RRDBNet x4 in well under a second in fp16.  We measure
2.2 s a frame in the finish.  Before changing the maths (half-then-x4) or accepting a slow
master, find out whether it is even running in half precision, and what the tiles and the
resample cost against the model itself.
"""
import os
import sys
import time

import numpy as np
import torch
import spandrel
from PIL import Image

sys.path.insert(0, os.path.expanduser("~/shared/comfy-studio/studio/_tools"))
import post  # noqa: E402

ESRGAN = post.ESRGAN
frame = sys.argv[1] if len(sys.argv) > 1 else None
if not frame:
    sys.exit("give a frame png")
free, total = torch.cuda.mem_get_info()
print("free %.1f GB of %.1f" % (free / 2**30, total / 2**30))

desc = spandrel.ModelLoader().load_from_file(ESRGAN).eval().to("cuda")
print("arch", type(desc.model).__name__, "scale", desc.scale, "supports_half",
      getattr(desc, "supports_half", None), "supports_bfloat16",
      getattr(desc, "supports_bfloat16", None))
p = next(desc.model.parameters())
print("param dtype before:", p.dtype)

arr = np.asarray(Image.open(frame).convert("RGB"), dtype=np.float32) / 255.0
x32 = torch.from_numpy(arr).permute(2, 0, 1).unsqueeze(0).cuda()
h, w = arr.shape[:2]
print("frame %dx%d" % (w, h))


def timeit(label, fn, n=3):
    torch.cuda.synchronize()
    fn()                                # warm-up (cudnn autotune, allocator)
    torch.cuda.synchronize()
    t0 = time.time()
    for _ in range(n):
        fn()
    torch.cuda.synchronize()
    dt = (time.time() - t0) / n
    print("  %-44s %6.3f s" % (label, dt), flush=True)
    return dt


with torch.no_grad():
    # fp32, tiled 768 (what the finish does if supports_half is False)
    timeit("fp32  tile 768", lambda: post.tiled(desc, x32, tile=768, scale=4))
    # fp16
    desc.model.half()
    x16 = x32.half()
    print("param dtype after half():", next(desc.model.parameters()).dtype)
    timeit("fp16  tile 768", lambda: post.tiled(desc, x16, tile=768, scale=4))
    timeit("fp16  tile 1088 (two tiles)", lambda: post.tiled(desc, x16, tile=1088, scale=4))
    try:
        timeit("fp16  whole frame, no tiles", lambda: desc(x16))
    except torch.OutOfMemoryError:
        print("  whole frame: OOM")
        torch.cuda.empty_cache()
    torch.backends.cudnn.benchmark = True
    timeit("fp16  tile 768 + cudnn.benchmark", lambda: post.tiled(desc, x16, tile=768, scale=4))
    m_cl = desc.model.to(memory_format=torch.channels_last)
    x_cl = x16.contiguous(memory_format=torch.channels_last)
    timeit("fp16  tile 768 + benchmark + channels_last",
           lambda: post.tiled(desc, x_cl, tile=768, scale=4))
    # the half-then-x4 alternative: same 2x result size, a quarter of the output pixels
    xh = torch.nn.functional.interpolate(x16.float(), scale_factor=0.5, mode="area").half()
    timeit("fp16  HALF input then x4 (= 2x), tile 768",
           lambda: post.tiled(desc, xh, tile=768, scale=4))
    y = post.tiled(desc, x16, tile=768, scale=4)
    timeit("resample x4 -> 2x (bicubic antialias)",
           lambda: torch.nn.functional.interpolate(y.float(), size=(h * 2, w * 2), mode="bicubic",
                                                   antialias=True, align_corners=False))
print("BENCH DONE")
