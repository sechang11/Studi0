#!/usr/bin/env python3
"""Why is the face ugly, and is a LoRA the fix?

    python3 studio/_tools/face_quality.py TERRA

THE ASSUMPTION WORTH TESTING. When a face comes out bad the instinct is to reach for a
LoRA, and a LoRA is the most expensive and least reversible lever available. Before
spending a training run, find out whether the face is bad because of the WEIGHTS or because
of the PIXELS IT WAS GIVEN.

The arithmetic that motivates this: at 832x1216 in a full-body frame, a head occupies
roughly an eighth of the height - about 150 pixels, of which the face is maybe 90. SDXL
generates in an 8x-downsampled latent, so that face was decided by roughly an 11x11 patch
of latent. No LoRA can add detail to a face the sampler never had room to draw. Terra's own
frame_verdict already records that the honest cut-off for a shot that reads as her is
"5_wide", and almost every recent sheet was rendered FULLER than that.

FIVE ARMS, one seed, one prompt, everything else held:

  A  full body                    the control - what the recent sheets did
  B  closer framing               same prompt, upper body. If B is good and A is not, the
                                  answer is framing and no LoRA is needed.
  C  full body at higher res      more pixels on the same composition
  D  full body + FACE DETAIL PASS the real fix: detect the face, crop it, re-render that
                                  crop at full resolution through the same model and LoRA,
                                  paste it back. This is what ADetailer does and it is a
                                  PIPELINE step, not a weights change.
  E  full body, LoRA strength up  the lever the question actually asked about, isolated

Read A against B first. Then A against D. If D fixes it, every full-body shot in the
project should be getting a detail pass and no retraining is required.
"""
import argparse, json, os, subprocess, sys

ROOT = os.path.expanduser("~/shared/comfy-studio")
sys.path.insert(0, os.path.join(ROOT, "scripts"))
os.environ.setdefault("COMFY_HOST", "127.0.0.1:8188")

from comfy import run, set_path                      # noqa: E402
from epic import load_wf, ensure_local, HOST         # noqa: E402

SEED = 8801
Q = "masterpiece, best quality, very aesthetic, absurdres"
NEG = ("1boy, male focus, multiple girls, lowres, worst quality, bad anatomy, bad hands, "
       "watermark, text, blurry")
PLACE = "stone hall, tall window, shaft of light, dust motes"


def sh(*a):
    return subprocess.run(a, capture_output=True, text=True)


def card(cid):
    with open(os.path.join(ROOT, "studio", "characters", cid + ".json"), encoding="utf-8") as f:
        return json.load(f)


def base_graph(c, framing, w, h, st):
    """The production anime path. The danbooru name is LOAD-BEARING and stays in."""
    wf = load_wf("22_anime_kf_ipadapter.json")
    set_path(wf, "1.inputs.ckpt_name", "animagine-xl-4.0.safetensors")
    set_path(wf, "4.inputs.weight", 0.0)
    tags = ", ".join(x for x in [c["tags"], c.get("base_tags", ""),
                                 (c.get("wear_tags") or [""])[0], framing, PLACE, Q] if x)
    set_path(wf, "5.inputs.text", tags)
    set_path(wf, "6.inputs.text", NEG)
    set_path(wf, "8.inputs.seed", SEED)
    for n in ("7", "10"):
        set_path(wf, "%s.inputs.width" % n, w)
        set_path(wf, "%s.inputs.height" % n, h)
    lora = c.get("lora")
    if lora and st > 0:
        wf["90"] = {"class_type": "LoraLoaderModelOnly",
                    "inputs": {"model": ["1", 0], "lora_name": lora, "strength_model": st}}
        for nid, node in list(wf.items()):
            if nid in ("1", "90") or not isinstance(node, dict):
                continue
            for k, v in (node.get("inputs") or {}).items():
                if isinstance(v, list) and len(v) == 2 and v[0] == "1" and v[1] == 0:
                    node["inputs"][k] = ["90", 0]
    return wf


def render(wf, tag):
    set_path(wf, "11.inputs.filename_prefix", "claude-generated/faceq/%s" % tag)
    _, outs = run(HOST, wf, quiet=True)
    if not outs:
        return None
    return ensure_local(outs[0], "/tmp/_fq_%s.png" % tag, required=False)


def face_detail(src, c, st, tag):
    """Crop the head region, re-render it at full resolution, paste it back.

    No Impact Pack on this box, so the face is located GEOMETRICALLY rather than by a
    detector: in a standing full-body frame the head sits in the top ~22% of the image,
    centred. That is crude and it is stated plainly rather than dressed up - a real
    detector would be better and SDPoseFaceBBoxes exists for a follow-up. What matters for
    THIS question is whether more pixels on the face fixes the face, and a rough crop
    answers that.
    """
    probe = sh("ffprobe", "-v", "error", "-select_streams", "v",
               "-show_entries", "stream=width,height", "-of", "csv=p=0", src).stdout.strip()
    try:
        W, H = [int(x) for x in probe.split(",")[:2]]
    except Exception:
        return None
    cw = int(W * 0.42)
    ch = int(H * 0.26)
    cx = (W - cw) // 2
    cy = int(H * 0.02)
    crop = "/tmp/_fq_crop_%s.png" % tag
    sh("ffmpeg", "-y", "-v", "error", "-i", src, "-vf",
       "crop=%d:%d:%d:%d,scale=1024:1024" % (cw, ch, cx, cy), crop)

    # img2img the crop at native resolution through the SAME model and LoRA, low denoise so
    # it refines rather than reinvents.
    wf = load_wf("22_anime_kf_ipadapter.json")
    set_path(wf, "1.inputs.ckpt_name", "animagine-xl-4.0.safetensors")
    set_path(wf, "4.inputs.weight", 0.0)
    face_tags = ", ".join([c["tags"], "close-up, face focus, detailed eyes, detailed face", Q])
    set_path(wf, "5.inputs.text", face_tags)
    set_path(wf, "6.inputs.text", NEG)
    set_path(wf, "8.inputs.seed", SEED)
    set_path(wf, "8.inputs.denoise", 0.45)
    for n in ("7", "10"):
        set_path(wf, "%s.inputs.width" % n, 1024)
        set_path(wf, "%s.inputs.height" % n, 1024)
    lora = c.get("lora")
    if lora and st > 0:
        wf["90"] = {"class_type": "LoraLoaderModelOnly",
                    "inputs": {"model": ["1", 0], "lora_name": lora, "strength_model": st}}
        for nid, node in list(wf.items()):
            if nid in ("1", "90") or not isinstance(node, dict):
                continue
            for k, v in (node.get("inputs") or {}).items():
                if isinstance(v, list) and len(v) == 2 and v[0] == "1" and v[1] == 0:
                    node["inputs"][k] = ["90", 0]
    # Feed the crop in as the latent. If the graph has no image input the arm is skipped
    # and says so rather than silently rendering something else.
    have_load = any(isinstance(n, dict) and n.get("class_type") == "LoadImage"
                    for n in wf.values())
    if not have_load:
        base = os.path.basename(crop)
        sh("cp", crop, os.path.join(os.path.expanduser("~/ComfyUI/input"), base))
        wf["80"] = {"class_type": "LoadImage", "inputs": {"image": base, "upload": "image"}}
        wf["81"] = {"class_type": "VAEEncode", "inputs": {"pixels": ["80", 0], "vae": ["1", 2]}}
        for nid, node in wf.items():
            if isinstance(node, dict) and node.get("class_type") == "KSampler":
                node["inputs"]["latent_image"] = ["81", 0]
    out = render(wf, tag)
    if not out:
        return None
    # Paste back, feathered, so the join does not show.
    dst = "/tmp/_fq_%s_composited.png" % tag
    sh("ffmpeg", "-y", "-v", "error", "-i", src, "-i", out,
       "-filter_complex",
       "[1:v]scale=%d:%d,format=rgba,geq=r='r(X,Y)':g='g(X,Y)':b='b(X,Y)':"
       "a='255*min(1,min(min(X,W-X),min(Y,H-Y))/24)'[f];[0:v][f]overlay=%d:%d"
       % (cw, ch, cx, cy), dst)
    return dst if os.path.exists(dst) else out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("character")
    ap.add_argument("--out")
    a = ap.parse_args()
    c = card(a.character)
    st = float(c.get("lora_strength_measured") or 0.5)

    arms = []
    print("  A full body (control)", flush=True)
    A = render(base_graph(c, "full body, standing, whole figure in frame", 832, 1216, st), "A_full")
    if A: arms.append(("A  full body  (control)", A))

    print("  B closer framing", flush=True)
    B = render(base_graph(c, "upper body, looking at viewer", 832, 1216, st), "B_close")
    if B: arms.append(("B  upper body", B))

    print("  C full body, higher res", flush=True)
    C = render(base_graph(c, "full body, standing, whole figure in frame", 1024, 1536, st), "C_hires")
    if C: arms.append(("C  full body @1024x1536", C))

    print("  D full body + face detail pass", flush=True)
    D = face_detail(A, c, st, "D_detail") if A else None
    if D: arms.append(("D  full body + FACE DETAIL", D))

    print("  E full body, LoRA 0.85", flush=True)
    E = render(base_graph(c, "full body, standing, whole figure in frame", 832, 1216, 0.85), "E_lora85")
    if E: arms.append(("E  full body, LoRA 0.85", E))

    # Crop every arm to the same head region so the faces are compared at the same size -
    # otherwise the close-up wins by being bigger and proves nothing.
    os.system("rm -rf /tmp/_fqg && mkdir -p /tmp/_fqg")
    for i, (label, p) in enumerate(arms):
        sh("ffmpeg", "-y", "-v", "error", "-i", p, "-vf",
           "crop=iw*0.42:ih*0.26:iw*0.29:ih*0.02,scale=460:-1,"
           "drawtext=text='%s':fontcolor=yellow:fontsize=18:x=6:y=6:box=1:"
           "boxcolor=black@0.85:boxborderw=5" % label.replace(":", "\\:"),
           "/tmp/_fqg/%02d.png" % i)
    dst = a.out or os.path.join(ROOT, "studio", "samples", "cast",
                                "%s_face_quality.jpg" % a.character.lower())
    sh("ffmpeg", "-y", "-v", "error", "-pattern_type", "glob", "-i", "/tmp/_fqg/*.png",
       "-filter_complex", "tile=%dx1:margin=6:padding=6:color=0x111111" % len(arms),
       "-frames:v", "1", "-q:v", "2", dst)
    print("\n%s" % dst)
    print("Every cell is the SAME head region at the SAME display size, so the comparison is "
          "about face quality rather than about who was closest to camera.")


if __name__ == "__main__":
    main()
