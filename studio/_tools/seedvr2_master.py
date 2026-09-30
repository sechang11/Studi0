#!/usr/bin/env python3
"""seedvr2_master.py - the 2x master by SeedVR2 instead of RealESRGAN, one shot at a time.

    python3 studio/_tools/seedvr2_master.py --sequence FILM [--grade filmic] [--scale 2] [--test N]

`fight.py --finish --master` enlarges the finished film with RealESRGAN x4 (post.upscale). On a
still, SeedVR2 3B restores real skin and wool detail where ESRGAN paints it smooth (MEASURED,
craft/SHEETS.md, studio/samples/sheets_lab/18_hd_seedvr2_vs_esrgan.jpg). This does the same for
the film: it cuts the graded film back into its shots (at the frame counts of the takes that
made it, listed in _concat.txt, so no segment boundary falls inside a shot), runs each through
SeedVR2 (the graph of ComfyUI's own "Upscale Video (SeedVR2 3B Int8)" blueprint, un-chunked),
joins them and lays the film's own finished soundtrack back on.

Writes OUT/<film>_<grade>_2x_seedvr2.mp4. --test N does only the first N shots.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import time

TOOLS = os.path.dirname(os.path.abspath(__file__))
STUDIO = os.path.dirname(TOOLS)
ROOT = os.path.dirname(STUDIO)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
sys.path.insert(0, TOOLS)


def sh(*a):
    return subprocess.run(a, check=True, capture_output=True, text=True)


def frames(p):
    r = sh("ffprobe", "-v", "error", "-select_streams", "v:0", "-count_packets", "-show_entries",
           "stream=nb_read_packets", "-of", "csv=p=0", p).stdout.strip()
    return int(r or 0)


def graph(src_name, scale, prefix):
    return {
        "1": {"class_type": "LoadVideo", "inputs": {"file": src_name}},
        "2": {"class_type": "GetVideoComponents", "inputs": {"video": ["1", 0]}},
        "3": {"class_type": "ImageScaleBy", "inputs": {"image": ["2", 0], "upscale_method": "lanczos",
                                                       "scale_by": float(scale)}},
        "4": {"class_type": "SeedVR2Preprocess", "inputs": {"resized_images": ["3", 0]}},
        "5": {"class_type": "VAELoader", "inputs": {"vae_name": "seedvr2_ema_vae_fp16.safetensors"}},
        "6": {"class_type": "VAEEncodeTiled", "inputs": {"pixels": ["4", 0], "vae": ["5", 0], "tile_size": 512,
                                                         "overlap": 128, "temporal_size": 64, "temporal_overlap": 8}},
        "7": {"class_type": "UNETLoader", "inputs": {"unet_name": "seedvr2_3b_int8_convrot.safetensors",
                                                     "weight_dtype": "default"}},
        # MEASURED: a 121-frame shot at 2560x1408 in one pass is out of memory on the 5090 (28.3 GB held,
        # 2 GB more asked). The blueprint's own switch: chunk the latent in time, sized to free VRAM
        # ("auto"), two latent frames crossfaded at each join.
        "6c": {"class_type": "SeedVR2TemporalChunk", "inputs": {"latent": ["6", 0], "temporal_overlap": 2,
                                                                "chunking_mode": "auto"}},
        "8": {"class_type": "SeedVR2Conditioning", "inputs": {"model": ["7", 0], "vae_conditioning": ["6c", 0]}},
        "9": {"class_type": "KSampler", "inputs": {"model": ["7", 0], "positive": ["8", 0], "negative": ["8", 1],
                                                   "latent_image": ["6c", 0], "seed": 7, "steps": 1, "cfg": 1.0,
                                                   "sampler_name": "euler", "scheduler": "simple", "denoise": 1.0}},
        "9m": {"class_type": "SeedVR2TemporalMerge", "inputs": {"latents": ["9", 0], "temporal_overlap": ["6c", 1]}},
        "10": {"class_type": "VAEDecodeTiled", "inputs": {"samples": ["9m", 0], "vae": ["5", 0], "tile_size": 512,
                                                          "overlap": 128, "temporal_size": 64, "temporal_overlap": 8}},
        "11": {"class_type": "SeedVR2PostProcessing", "inputs": {"images": ["10", 0], "original_resized_images": ["3", 0],
                                                                 "color_correction_method": "lab"}},
        "12": {"class_type": "CreateVideo", "inputs": {"images": ["11", 0], "fps": ["2", 2], "bit_depth": ["2", 3],
                                                       "color_space": ["2", 4]}},
        "13": {"class_type": "SaveVideo", "inputs": {"video": ["12", 0], "filename_prefix": prefix,
                                                     "format": "auto", "codec": "auto"}},
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--sequence", required=True)
    ap.add_argument("--grade", default="filmic")
    ap.add_argument("--scale", type=float, default=2.0)
    ap.add_argument("--test", type=int, default=0)
    a = ap.parse_args()
    from comfy import run
    from epic import COMFY, HOST, ensure_local

    out = os.path.join(STUDIO, "samples", "fight", a.sequence)
    film = os.path.join(out, "%s_%s.mp4" % (a.sequence, a.grade))
    lst = os.path.join(out, "_concat.txt")
    if not (os.path.exists(film) and os.path.exists(lst)):
        sys.exit("finish the film first (fight.py --finish): need %s and _concat.txt" % os.path.basename(film))
    takes = [ln.split("'", 2)[1] for ln in open(lst) if ln.startswith("file '")]
    counts = [frames(p) for p in takes]
    total = frames(film)
    if sum(counts) != total:
        print("  the takes count %d frames and the film %d - cutting every 96 frames instead" % (sum(counts), total))
        counts = [96] * (total // 96) + ([total % 96] if total % 96 else [])
    work = os.path.join(out, "_seedvr2")
    os.makedirs(work, exist_ok=True)
    segs, start = [], 0
    for i, n in enumerate(counts):
        segs.append((i, start, start + n))
        start += n
    if a.test:
        segs = segs[:a.test]
    done = []
    t_all = time.time()
    for i, f0, f1 in segs:
        dst = os.path.join(work, "seg_%02d_2x.mp4" % i)
        if os.path.exists(dst) and frames(dst) == f1 - f0:
            done.append(dst)
            continue
        name = "sv2_%s_%02d.mp4" % (a.sequence, i)
        src = os.path.join(COMFY, "input", name)
        sh("ffmpeg", "-y", "-v", "error", "-i", film, "-vf",
           "trim=start_frame=%d:end_frame=%d,setpts=PTS-STARTPTS" % (f0, f1), "-an",
           "-c:v", "libx264", "-crf", "8", "-pix_fmt", "yuv420p", src)
        t0 = time.time()
        _, outs = run(HOST, graph(name, a.scale, "claude-generated/seedvr2/%s_%02d" % (a.sequence, i)), quiet=True)
        # the history also lists LoadVideo's own preview of the INPUT file; take the saved one
        vid = next((o for o in outs if o.startswith("claude-generated/seedvr2/")), None)
        if not vid:
            sys.exit("segment %d: SeedVR2 returned no video" % i)
        if os.path.exists(dst):
            os.remove(dst)
        ensure_local(vid, dst)
        got = frames(dst)
        secs = time.time() - t0
        print("  shot %02d  frames %d-%d  %d frames in %.0fs (%.2f s a frame)%s" % (
            i, f0, f1, got, secs, secs / max(1, got), "" if got == f1 - f0 else "  FRAME COUNT %d != %d" % (got, f1 - f0)),
            flush=True)
        done.append(dst)
    if a.test:
        print("test done: %d shots in %.0fs" % (len(done), time.time() - t_all))
        return
    joined = os.path.join(work, "joined.txt")
    open(joined, "w").write("".join("file '%s'\n" % p for p in done))
    final = os.path.join(out, "%s_%s_2x_seedvr2.mp4" % (a.sequence, a.grade))
    sh("ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", joined, "-i", film,
       "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-crf", "16", "-preset", "slow", "-pix_fmt", "yuv420p",
       "-c:a", "copy", final)
    print("2x master (SeedVR2) -> %s  frames %d (film %d)  %.0fs" % (final, frames(final), total, time.time() - t_all))


if __name__ == "__main__":
    main()
