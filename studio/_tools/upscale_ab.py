#!/usr/bin/env python3
"""Fast against fine against nothing, on the same frame, at 100%: does six times faster cost anything you can see?

    ~/ComfyUI/venv/bin/python3 upscale_ab.py FRAME.png OUT.jpg

Three 2x results of one 1920x1088 frame - plain bicubic (what a player would do), fast (half the
frame then x4), fine (x4 then down) - cropped to the same three regions at 1:1 so the eye judges
pixels and not a thumbnail.  A thumbnail flatters everything; that is how a grade got shipped
that was a regression.
"""
import os
import sys
import time

import numpy as np
import torch
import spandrel
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.expanduser("~/shared/comfy-studio/studio/_tools"))
import post  # noqa: E402

src, out = sys.argv[1], sys.argv[2]
arr = np.asarray(Image.open(src).convert("RGB"), dtype=np.float32) / 255.0
h, w = arr.shape[:2]
x = torch.from_numpy(arr).permute(2, 0, 1).unsqueeze(0).cuda().half()
desc = spandrel.ModelLoader().load_from_file(post.ESRGAN).eval().cuda()
desc.model.half()

with torch.no_grad():
    t0 = time.time()
    fine = post.tiled(desc, x, tile=768, scale=4).clamp_(0, 1)
    fine = torch.nn.functional.interpolate(fine.float(), size=(h * 2, w * 2), mode="bicubic",
                                           antialias=True, align_corners=False).clamp_(0, 1)
    t_fine = time.time() - t0
    t0 = time.time()
    xh = torch.nn.functional.interpolate(x.float(), scale_factor=0.5, mode="area").half()
    fast = post.tiled(desc, xh, tile=768, scale=4).clamp_(0, 1).float()
    t_fast = time.time() - t0
    bic = torch.nn.functional.interpolate(x.float(), size=(h * 2, w * 2), mode="bicubic",
                                          align_corners=False).clamp_(0, 1)


def to_img(t):
    return Image.fromarray((t[0].permute(1, 2, 0).cpu().numpy() * 255).round().astype(np.uint8))


imgs = {"bicubic 2x (a player)": to_img(bic),
        "fast: half then x4  (%.2fs)" % t_fast: to_img(fast),
        "fine: x4 then down  (%.2fs)" % t_fine: to_img(fine)}
# three regions of the 2x frame, 1:1 - centre, a top-left detail, a lower-right detail
W2, H2 = w * 2, h * 2
cw, ch = 640, 400
regions = [((W2 - cw) // 2, (H2 - ch) // 2), (W2 // 6, H2 // 8), (W2 * 2 // 3, H2 * 3 // 5)]
sheet = Image.new("RGB", (cw * len(regions) + 8 * (len(regions) - 1),
                          (ch + 22) * len(imgs)), (16, 16, 20))
d = ImageDraw.Draw(sheet)
for r, (label, im) in enumerate(imgs.items()):
    y = r * (ch + 22)
    d.text((4, y + 4), label, fill=(230, 230, 235))
    for c, (rx, ry) in enumerate(regions):
        crop = im.crop((rx, ry, rx + cw, ry + ch))
        sheet.paste(crop, (c * (cw + 8), y + 22))
sheet.save(out, quality=92)
print("fine %.2fs  fast %.2fs  -> %s %s" % (t_fine, t_fast, out, sheet.size))
