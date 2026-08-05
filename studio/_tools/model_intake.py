#!/usr/bin/env python3
"""Decide whether a model is worth its disk, and prove the decision from pixels.

    python3 studio/_tools/model_intake.py base --ckpt animagine-xl-4.0.safetensors
    python3 studio/_tools/model_intake.py base --ckpt Illustrious-XL-v2.0.safetensors --size 1536
    python3 studio/_tools/model_intake.py ladder --lora foo.safetensors --probe pixel_art \
            --strengths 0 0.6 0.9 --ckpt animagine-xl-4.0.safetensors
    python3 studio/_tools/model_intake.py probes

WHY THIS EXISTS, AND WHY IT RUNS `base` FIRST

A download earns its place only if the models already on disk measurably CANNOT do the
thing. The temptation is to install the LoRA, render one nice image, and call it proven -
which proves nothing, because a LoRA is a delta on base weights and a single with-the-LoRA
image has no control. Worse, the usual failure here is not "the LoRA is bad", it is "the
base could already do this from a prompt and nobody checked".

So intake is two passes and the order is not negotiable:

  base    render the style probes on the installed checkpoint with NO LoRA. This is the
          gate. Anything the base renders convincingly is a REJECT: buying it again as a
          LoRA is a marginal aesthetic preference, and this project has a standing rule
          against those.
  ladder  only for probes the base failed. Same seed, same prompt, same subject, one
          column per strength with the control at 0.0 in the left column. If the ladder
          does not visibly beat column 0, the card is marked weak or unavailable and the
          file is reported as not having earned its place.

WHY THE SUBJECT IS HELD CONSTANT ACROSS EVERY PROBE

Style is the only variable under test, so the subject, the seed, the sampler, the size and
the quality tail are all pinned. A probe that changes the subject as well as the style
cannot tell you which one moved the pixels. The subject is deliberately mundane (a woman
in a kitchen with a mug) - a dramatic subject hides a weak style behind its own interest.

THE NEGATIVE IS REAL HERE AND ONLY HERE. This box has four prompt dialects and SDXL is the
only one where a negative prompt is load-bearing (Qwen conditions on Qwen2.5-VL, Z-Image
discards the field, FLUX.2 has no negative branch at all). These probes are SDXL, so the
negative is used - but it deliberately does NOT contain style words, because negating
"anime" is a different experiment from asking for oil paint and would confound the gate.

READ THE OUTPUT
  base grid: cell looks like the named style      -> REJECT any LoRA for that style
             cell looks like anime wearing a hat  -> the gate is open, a LoRA may earn it
  ladder:    all columns identical                -> the LoRA is inert, mark unavailable
             column 0 already looks right         -> you skipped the gate, go back
             style arrives and the subject holds  -> it earned its place at that strength
             style arrives and the subject dies   -> record the cost, pick a lower column

Standard library only, same as lora_scan.py: this has to run on the box with no venv.
"""
import argparse
import json
import os
import re
import struct
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
STUDIO = os.path.dirname(HERE)
ROOT = os.path.dirname(STUDIO)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
os.environ.setdefault("COMFY_HOST", "127.0.0.1:8188")

from comfy import api, set_path                        # noqa: E402
from epic import load_wf, ensure_local, HOST, submit   # noqa: E402

WF = "22_anime_kf_ipadapter.json"
OUT = os.path.join(STUDIO, "samples", "model_intake")
LEDGER = os.path.join(OUT, "ledger.json")

Q = "masterpiece, best quality, very aesthetic, absurdres"

# One subject, every probe. Danbooru tag order: subject -> action -> setting -> light.
SUBJECT = ("1girl, solo, adult woman, long brown hair, plain grey sweater, "
           "standing in a small kitchen, holding a ceramic mug, "
           "kitchen counter, window, morning light")

# No style words in the negative. See the module docstring - negating "anime" would be a
# different experiment and would contaminate the gate this tool exists to run.
NEG = ("lowres, worst quality, bad anatomy, bad hands, extra limbs, extra fingers, "
       "watermark, signature, text, multiple views, jpeg artifacts")

# The probes are named for what the styles library actually asks for, and every one of them
# is written as NOUNS. The project's measured law is that the model renders nouns, not
# adjectives, so a probe phrased as adjectives would fail for the wrong reason and would
# frame the base model for a crime the prompt committed.
PROBES = {
    "none": "",
    "oil_impasto": ("oil painting, impasto, thick visible brushstrokes, palette knife "
                    "ridges, canvas weave, cracked varnish"),
    "pixel_art": ("pixel art, 8-bit sprite, visible square pixels, hard pixel edges, "
                  "limited 16 colour palette, dithering"),
    "coloring_book": ("coloring book page, black ink lineart on white paper, thick "
                      "uniform outlines, no shading, no colour, monochrome, greyscale"),
    "claymation": ("claymation, stop motion puppet, plasticine figure, fingerprints in "
                   "the clay, felt and cardboard set, tabletop miniature"),
    "risograph": ("risograph print, two ink layers, visible halftone dot screen, "
                  "misregistered ink, paper grain, spot colour"),
    "photo": ("colour photograph, 35mm film, visible film grain, skin pores, "
              "shallow depth of field, available window light"),
    "woodcut": ("woodcut print, carved black ink lines, hatching, gouged white marks, "
                "rough paper, no gradients"),
    "watercolour": ("watercolour painting, wet pigment pooling at the edges, wash bleed, "
                    "paper tooth, water stains, visible brush water marks"),
    "lowpoly_ps1": ("playstation 1 game graphics, low polygon count mesh, flat shaded "
                    "triangles, 256x224 texture warping, jagged polygon edges"),
    "comic_halftone": ("vintage comic book print, Ben-Day halftone dot shading, bold "
                       "black ink outlines, cross-hatching, four colour offset "
                       "misregistration, newsprint paper"),
}


# The same subject in the prose dialect, for the cross-engine gate. This box has four
# prompt dialects and a probe written in danbooru tags would fail on Qwen and FLUX.2 for a
# reason that has nothing to do with the style - so the subject is rewritten rather than
# reused, and only the style noun phrase is shared between the two versions.
SUBJECT_PROSE = ("An adult woman with long brown hair in a plain grey sweater stands in a "
                 "small kitchen holding a ceramic mug. A counter and a window are behind "
                 "her. Morning light.")
NEG_PROSE = "blurry, low quality, watermark, jpeg artifacts, deformed hands"

CROSS = {
    "flux2": {"wf": "40_flux2_t2i.json", "pos": "6", "seed": "11.inputs.noise_seed",
              "size": [("9.inputs.width", "9.inputs.height"),
                       ("12.inputs.width", "12.inputs.height")],
              "save": "15.inputs.filename_prefix", "neg": None},
    "qwen": {"wf": "02_qwen_t2i_quality.json", "pos": "10", "seed": "13.inputs.seed",
             "size": [("12.inputs.width", "12.inputs.height")],
             "save": "15.inputs.filename_prefix", "neg": "11"},
}


def sh(*a):
    return subprocess.run(a, capture_output=True, text=True)


def prompt_for(probe, trigger=None):
    """The trigger goes in EVERY cell of a ladder, including the strength-0 control.

    It is a prompt token, not part of the LoRA, so putting it only in the LoRA-on cells
    would vary two things at once and the sheet would prove nothing. This project already
    has a card (qwen-modern-anime) that went from apparently inert to a genuine style
    change on nothing but the trigger being present, so an untriggered ladder is not a
    fair test of a LoRA that ships one.
    """
    style = PROBES[probe]
    bits = [SUBJECT]
    if style:
        bits.insert(0, style)
    if trigger:
        bits.insert(0, trigger)
    bits.append(Q)
    return ", ".join(bits)


def build(ckpt, probe, seed, size, lora=None, strength=0.0, steps=28, cfg=5.0,
          trigger=None):
    wf = load_wf(WF)
    set_path(wf, "1.inputs.ckpt_name", ckpt)
    set_path(wf, "4.inputs.weight", 0.0)      # IPAdapter off: isolate checkpoint + LoRA
    set_path(wf, "5.inputs.text", prompt_for(probe, trigger))
    set_path(wf, "6.inputs.text", NEG)
    set_path(wf, "8.inputs.seed", seed)
    set_path(wf, "8.inputs.steps", steps)
    set_path(wf, "8.inputs.cfg", cfg)
    for n in ("7", "10"):
        set_path(wf, "%s.inputs.width" % n, size)
        set_path(wf, "%s.inputs.height" % n, size)
    if lora and strength > 0:
        wf["90"] = {"class_type": "LoraLoaderModelOnly",
                    "inputs": {"model": ["1", 0], "lora_name": lora,
                               "strength_model": float(strength)}}
        for nid, node in list(wf.items()):
            if nid in ("1", "90") or not isinstance(node, dict):
                continue
            for k, v in (node.get("inputs") or {}).items():
                if isinstance(v, list) and len(v) == 2 and v[0] == "1" and v[1] == 0:
                    node["inputs"][k] = ["90", 0]
    return wf


def label(src, dst, text, size=640):
    sh("ffmpeg", "-y", "-v", "error", "-i", src, "-vf",
       "scale=%d:%d,drawtext=text='%s':fontcolor=yellow:fontsize=26:x=12:y=12:"
       "box=1:boxcolor=black@0.85:boxborderw=7" % (size, size, text.replace("'", "")), dst)
    return dst


def wait_for(pids):
    """Wait on a whole batch. The box is shared and ComfyUI is FIFO, so everything is
    submitted up front - one-at-a-time puts every cell behind someone else's queue and a
    foreign model family costs a 60-150 s reload on each alternation."""
    done, t0 = {}, time.time()
    pending = list(pids)
    while pending:
        time.sleep(2.0)
        for pid in list(pending):
            hist = api(HOST, "/history/%s" % pid)
            if pid not in hist:
                continue
            entry = hist[pid]
            st = entry.get("status", {})
            if st.get("status_str") == "error":
                print("  FAILED %s" % pid, file=sys.stderr)
                for m in st.get("messages", [])[:4]:
                    print("   ", str(m)[:300], file=sys.stderr)
                done[pid] = None
                pending.remove(pid)
                continue
            if st.get("completed"):
                outs = []
                for _nid, out in entry["outputs"].items():
                    for f in out.get("images", []):
                        outs.append("%s/%s" % (f.get("subfolder", ""), f["filename"]))
                done[pid] = outs[0].lstrip("/") if outs else None
                pending.remove(pid)
        print("  [%6.1fs] %d/%d done" % (time.time() - t0, len(done), len(pids)),
              file=sys.stderr)
    return done


def ledger_write(entry):
    os.makedirs(OUT, exist_ok=True)
    data = []
    if os.path.exists(LEDGER):
        try:
            data = json.load(open(LEDGER, encoding="utf-8"))
        except ValueError:
            data = []
    data.append(entry)
    with open(LEDGER, "w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, indent=2)
        f.write("\n")


def stack(inputs, out, mode):
    """hstack/vstack that REFUSES to leave a stale file behind.

    ffmpeg's hstack and vstack both reject inputs=1, and this project has already been
    bitten once by an ffmpeg tile silently dropping cells. The first version of this
    function ignored that: with a single cell the filter errored, nothing was written, and
    the previous run's temp file was picked up and published as if it were the new sheet.
    Two contact sheets were built from the wrong render before the pixels gave it away. So
    the single-input case is a plain copy, every temp name is unique to its sheet, and a
    non-zero ffmpeg exit is raised rather than swallowed.
    """
    if len(inputs) == 1:
        r = sh("ffmpeg", "-y", "-v", "error", "-i", inputs[0], out)
    else:
        r = sh("ffmpeg", "-y", "-v", "error", *sum((["-i", i] for i in inputs), []),
               "-filter_complex", "%s=inputs=%d" % (mode, len(inputs)), out)
    if r.returncode != 0 or not os.path.exists(out):
        raise SystemExit("ffmpeg %s failed (%d cells): %s" % (mode, len(inputs), r.stderr))
    return out


def grid(cells, dst, cols):
    """Rows are PADDED to equal width before vstack, and that is not cosmetic.

    vstack refuses rows of differing widths, so 11 cells at 4 columns leaves a 3-wide last
    row and the whole sheet silently fails to be written - the same family of ffmpeg
    failure as the tile filter that once dropped cells from a comparison in this repo. A
    short final row is padded with a black cell of the exact cell size so every row is the
    same width and the count stays visible: a blank cell reads as "nothing rendered here",
    which is true, where a dropped cell reads as nothing at all.
    """
    if not cells:
        raise SystemExit("no cells rendered - nothing to build a sheet from")
    key = os.path.basename(dst).rsplit(".", 1)[0]
    pad = None
    if len(cells) > cols and len(cells) % cols:
        pad = "/tmp/_mi_%s_pad.png" % key
        probe = sh("ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                   "stream=width,height", "-of", "csv=p=0", cells[0])
        wh = (probe.stdout or "").strip().split(",")
        size = "%sx%s" % (wh[0], wh[1]) if len(wh) == 2 else "640x640"
        sh("ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i",
           "color=c=black:s=%s:d=1" % size, "-frames:v", "1", pad)
    rows = []
    for i in range(0, len(cells), cols):
        chunk = list(cells[i:i + cols])
        while pad and len(chunk) < cols:
            chunk.append(pad)
        rows.append(stack(chunk, "/tmp/_mi_%s_row%d.png" % (key, i), "hstack"))
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    tmp = "/tmp/_mi_%s_full.png" % key
    stack(rows, tmp, "vstack")
    r = sh("ffmpeg", "-y", "-v", "error", "-i", tmp, "-q:v", "3", dst)
    if r.returncode != 0:
        raise SystemExit("ffmpeg jpeg encode failed: %s" % r.stderr)
    return dst


def cmd_base(a):
    probes = a.probes or list(PROBES.keys())
    tag = a.ckpt.split(".")[0].replace(".", "_")
    print("GATE RUN. checkpoint %s, no LoRA, seed %d, %dpx" % (a.ckpt, a.seed, a.size))
    print("probes: %s" % ", ".join(probes))
    pids, order = {}, []
    for p in probes:
        wf = build(a.ckpt, p, a.seed, a.size, steps=a.steps, cfg=a.cfg)
        set_path(wf, "11.inputs.filename_prefix",
                 "claude-generated/model_intake/base_%s_%s" % (tag, p))
        pids[submit(wf)] = p
        order.append(p)
    print("submitted %d cells" % len(pids))
    got = wait_for(list(pids.keys()))
    cells, missing = [], []
    for pid, p in pids.items():
        rel = got.get(pid)
        if not rel:
            missing.append(p)
            continue
        loc = ensure_local(rel, "/tmp/_mi_%s_%s.png" % (tag, p), required=False)
        if loc:
            cells.append((order.index(p), label(loc, "/tmp/_mil_%s_%s.png" % (tag, p),
                                                "BASE %s | %s" % (tag[:18], p))))
    cells = [c for _, c in sorted(cells)]
    # A partial run must not overwrite the full sheet. The first version named every base
    # run base_<ckpt>.jpg, so a two-probe follow-up silently replaced the eight-probe gate.
    dst = os.path.join(OUT, "base_%s%s.jpg" % (tag, "" if a.probes is None
                                               else "__" + "_".join(sorted(probes))))
    grid(cells, dst, a.cols)
    ledger_write({"mode": "base", "ckpt": a.ckpt, "seed": a.seed, "size": a.size,
                  "steps": a.steps, "cfg": a.cfg, "probes": probes,
                  "missing": missing, "sheet": dst})
    print("\n%s (%.0f KB)" % (dst, os.path.getsize(dst) / 1024.0))
    print("LOOK AT IT. Any probe the base renders convincingly is a REJECT.")


def cmd_ladder(a):
    if not a.probe:
        raise SystemExit("ladder needs --probe (one of: %s)" % ", ".join(PROBES))
    # The cache key MUST carry the checkpoint. ensure_local() returns early when the
    # destination already exists, so a key built only from lora+probe+strength silently
    # served the previous checkpoint's PNGs when the same ladder was re-run on a second
    # base - producing a sheet labelled Illustrious that was animagine pixels throughout.
    # Caught by eye, not by any error. Anything that varies a cell must be in this key.
    tag = os.path.basename(a.lora).split(".")[0][:28]
    ck = os.path.basename(a.ckpt).split(".safetensors")[0][:20].replace(".", "")
    print("LADDER. lora %s on %s, probe %s, strengths %s, trigger %r" %
          (a.lora, a.ckpt, a.probe, a.strengths, a.trigger))
    print("prompt: %s" % prompt_for(a.probe, a.trigger)[:160])
    pids, order = {}, []
    for st in a.strengths:
        wf = build(a.ckpt, a.probe, a.seed, a.size, lora=a.lora, strength=st,
                   steps=a.steps, cfg=a.cfg, trigger=a.trigger)
        set_path(wf, "11.inputs.filename_prefix",
                 "claude-generated/model_intake/ladder_%s_%s_%s_%s" %
                 (ck, tag, a.probe, str(st).replace(".", "")))
        pids[submit(wf)] = st
        order.append(st)
    got = wait_for(list(pids.keys()))
    cells = []
    for pid, st in pids.items():
        rel = got.get(pid)
        if not rel:
            continue
        key = "%s_%s_%s_%s" % (ck, tag, a.probe, str(st).replace(".", ""))
        loc = ensure_local(rel, "/tmp/_ml_%s.png" % key, required=False)
        if loc:
            txt = "CONTROL strength 0" if st == 0 else "strength %.2f" % st
            cells.append((order.index(st),
                          label(loc, "/tmp/_mll_%s.png" % key, "%s | %s" % (a.probe, txt))))
    cells = [c for _, c in sorted(cells)]
    dst = os.path.join(OUT, "ladder_%s_%s_%s.jpg" % (ck, tag, a.probe))
    grid(cells, dst, len(cells))
    ledger_write({"mode": "ladder", "lora": a.lora, "ckpt": a.ckpt, "probe": a.probe,
                  "sheet_key": ck,
                  "trigger": a.trigger, "strengths": a.strengths, "seed": a.seed, "size": a.size,
                  "steps": a.steps, "cfg": a.cfg, "sheet": dst})
    print("\n%s (%.0f KB)" % (dst, os.path.getsize(dst) / 1024.0))
    print("LOOK AT IT. Column 0 is the control; if it already looks right, the LoRA is "
          "not what changed the image.")


def cmd_cross(a):
    """The second gate, and the one that stops a download by itself.

    A style the anime checkpoints cannot render is not automatically a missing LoRA - it
    may simply be a style that belongs on another engine. This project routes styles per
    card, so before buying a delta for SDXL, ask FLUX.2 and Qwen for the same look. If one
    of them already renders it, the correct fix is a one-line engine change in a style
    card and the download is rejected.
    """
    spec = CROSS[a.engine]
    probes = a.probes or ["claymation", "risograph", "woodcut", "photo"]
    print("CROSS-ENGINE GATE. engine %s, wf %s, seed %d" % (a.engine, spec["wf"], a.seed))
    pids, order = {}, []
    for p in probes:
        wf = load_wf(spec["wf"])
        style = PROBES[p]
        text = (style + ". " + SUBJECT_PROSE) if style else SUBJECT_PROSE
        set_path(wf, "%s.inputs.text" % spec["pos"], text)
        if spec["neg"]:
            set_path(wf, "%s.inputs.text" % spec["neg"], NEG_PROSE)
        set_path(wf, spec["seed"], a.seed)
        for w, h in spec["size"]:
            set_path(wf, w, a.size)
            set_path(wf, h, a.size)
        set_path(wf, spec["save"],
                 "claude-generated/model_intake/cross_%s_%s" % (a.engine, p))
        pids[submit(wf)] = p
        order.append(p)
    print("submitted %d cells" % len(pids))
    got = wait_for(list(pids.keys()))
    cells = []
    for pid, p in pids.items():
        rel = got.get(pid)
        if not rel:
            continue
        loc = ensure_local(rel, "/tmp/_mx_%s_%s.png" % (a.engine, p), required=False)
        if loc:
            cells.append((order.index(p),
                          label(loc, "/tmp/_mxl_%s_%s.png" % (a.engine, p),
                                "%s | %s" % (a.engine.upper(), p))))
    cells = [c for _, c in sorted(cells)]
    dst = os.path.join(OUT, "cross_%s%s.jpg" % (a.engine, "" if a.probes is None
                                                else "__" + "_".join(sorted(probes))))
    grid(cells, dst, a.cols)
    ledger_write({"mode": "cross", "engine": a.engine, "wf": spec["wf"], "seed": a.seed,
                  "size": a.size, "probes": probes, "sheet": dst})
    print("\n%s (%.0f KB)" % (dst, os.path.getsize(dst) / 1024.0))
    print("LOOK AT IT. A style another engine already renders is a REJECTED download.")


# ---------------------------------------------------------------------------------------
# keyfix: the difference between "this LoRA is bad" and "our loader cannot read it"
# ---------------------------------------------------------------------------------------
# A LoRA whose tensor keys ComfyUI does not recognise loads without error and renders
# exactly as if it were absent - the failure this project already has 68,628 log lines of.
# Two of the three files in this intake were inert for that reason and only that reason:
# they are diffusers ATTENTION-PROCESSOR LoRAs, and ComfyUI's SDXL key map
# (comfy/lora.py:208-213) builds  unet.<block>.attnN.processor.to_k  while these files
# store  unet.<block>.attnN.to_k . The suffix .lora.down.weight is already accepted
# (comfy/weight_adapter/lora.py:163,183). So the fix is a rename of the base key, nothing
# more, and it is worth doing precisely because it separates a bad LoRA from a misnamed one
# - a rejection should name the real cause.
#
# The tensor DATA BLOCK IS COPIED BYTE FOR BYTE and no offset is touched: only the header's
# key strings change. The original file is never modified; a new _cfy.safetensors is
# written beside it. If the renamed file still does nothing, the LoRA itself is the problem.
ATTN_RE = re.compile(r"^(unet\..*\.attn\d+)\.(to_[qkv]|to_out)(\.0)?((?:\.lora\.(?:up|down)\.weight)|\.alpha)$")


def keyfix_name(k):
    m = ATTN_RE.match(k)
    if not m:
        return None
    head, proj, _zero, tail = m.groups()
    return "%s.processor.%s%s" % (head, proj, tail)


def cmd_keyfix(a):
    src = a.path if os.path.sep in a.path else os.path.join(a.loras, a.path)
    if not os.path.exists(src):
        raise SystemExit("no such file: %s" % src)
    dst = a.out or (src[:-len(".safetensors")] + "_cfy.safetensors")
    if os.path.exists(dst):
        raise SystemExit("refusing to overwrite %s" % dst)
    with open(src, "rb") as fh:
        hlen = struct.unpack("<Q", fh.read(8))[0]
        header = json.loads(fh.read(hlen))
    renamed, kept = {}, 0
    for k, v in header.items():
        if k == "__metadata__":
            renamed[k] = v
            continue
        nk = keyfix_name(k)
        if nk is None:
            renamed[k] = v
            kept += 1
        else:
            renamed[nk] = v
    changed = sum(1 for k in header if k != "__metadata__" and keyfix_name(k))
    print("%s: %d tensors, %d renamed, %d left alone" %
          (os.path.basename(src), len(header) - (1 if "__metadata__" in header else 0),
           changed, kept))
    if not changed:
        raise SystemExit("nothing matched the diffusers attention-processor pattern - "
                         "this file is not the case keyfix handles")
    blob = json.dumps(renamed, separators=(",", ":")).encode()
    blob += b" " * ((8 - len(blob) % 8) % 8)
    with open(src, "rb") as fh, open(dst, "wb") as out:
        fh.seek(8 + hlen)
        out.write(struct.pack("<Q", len(blob)))
        out.write(blob)
        while True:
            chunk = fh.read(1 << 22)
            if not chunk:
                break
            out.write(chunk)
    print("  -> %s (%.1f MB)" % (dst, os.path.getsize(dst) / 1e6))
    print("  the data block was copied verbatim; only header key strings changed.")
    print("  NOW RUN A LADDER ON IT. A file that loads is not a file that works.")


def cmd_probes(a):
    for k, v in PROBES.items():
        print("%-14s %s" % (k, v or "(no style words - the plain subject)"))
    print("\nsubject : %s" % SUBJECT)
    print("negative: %s" % NEG)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)

    def common(p):
        p.add_argument("--ckpt", default="animagine-xl-4.0.safetensors")
        p.add_argument("--seed", type=int, default=5150)
        p.add_argument("--size", type=int, default=1024)
        p.add_argument("--steps", type=int, default=28)
        p.add_argument("--cfg", type=float, default=5.0)

    b = sub.add_parser("base", help="the gate: what the checkpoint already does, no LoRA")
    common(b)
    b.add_argument("--probes", nargs="+", choices=sorted(PROBES), default=None)
    b.add_argument("--cols", type=int, default=4)
    b.set_defaults(func=cmd_base)

    l = sub.add_parser("ladder", help="strength ladder with the control at 0")
    common(l)
    l.add_argument("--lora", required=True)
    l.add_argument("--probe", choices=sorted(PROBES))
    l.add_argument("--strengths", type=float, nargs="+", default=[0.0, 0.5, 0.8, 1.0])
    l.add_argument("--trigger", default=None,
                   help="the LoRA's trigger phrase. Goes in every cell including the "
                        "control, so that strength stays the only variable.")
    l.set_defaults(func=cmd_ladder)

    x = sub.add_parser("cross", help="second gate: does another installed engine already "
                                     "render this style?")
    x.add_argument("--engine", choices=sorted(CROSS), required=True)
    x.add_argument("--probes", nargs="+", choices=sorted(PROBES), default=None)
    x.add_argument("--seed", type=int, default=5150)
    x.add_argument("--size", type=int, default=1024)
    x.add_argument("--cols", type=int, default=4)
    x.set_defaults(func=cmd_cross)

    k = sub.add_parser("keyfix", help="rewrite diffusers attention-processor keys into "
                                     "the names ComfyUI's SDXL map expects")
    k.add_argument("path", help="a .safetensors in models/loras, or a full path")
    k.add_argument("--loras", default=os.path.expanduser("~/ComfyUI/models/loras"))
    k.add_argument("--out", default=None)
    k.set_defaults(func=cmd_keyfix)

    p = sub.add_parser("probes", help="print the probe prompts and exit")
    p.set_defaults(func=cmd_probes)

    a = ap.parse_args()
    a.func(a)


if __name__ == "__main__":
    main()
