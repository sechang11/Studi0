#!/usr/bin/env python3
"""
plan-models.py - build a verified download manifest from ComfyUI's own templates.

ComfyUI embeds {name, url, directory} on every loader node so its missing-models
dialog can offer a download. That is the authoritative source for where a model
lives and what it is called - far safer than hand-written URLs, which rot.

This reads those entries for the templates you name, drops anything already on
disk, HEADs each URL for a real Content-Length, and writes a manifest.

    python3 scripts/plan-models.py image_qwen_image_edit_2511 3d_hunyuan3d-v2.1
    python3 scripts/plan-models.py --tier edit3d          # a named set below
    python3 scripts/plan-models.py --tier edit3d -o /tmp/manifest.tsv

The manifest is TSV: directory <TAB> filename <TAB> bytes <TAB> url
Feed it to fetch-manifest.sh.
"""
import argparse
import json
import os
import sys
import urllib.error
import urllib.request

TPL = os.path.expanduser(
    "~/ComfyUI/venv/lib/python3.14/site-packages/"
    "comfyui_workflow_templates_json/templates"
)
MODELS = os.path.expanduser("~/ComfyUI/models")

TIERS = {
    # newest Qwen edit model + its own Lightning LoRA (supersedes 2509)
    "edit": ["image_qwen_image_edit_2511"],
    # control maps for images and video
    "control": [
        "utility_depth_anything3_image_depth_estimation",
        "utility_sdpose_ood_image_to_pose",
    ],
    # LTX-2.3-native video control and identity lock
    "ltxcontrol": ["video_ltx2_3_ic_lora", "video_ltx2_3_id_lora"],
    # physics/motion specialist to sit alongside LTX and Wan
    "hunyuanvideo": [
        "video_hunyuan_video_1.5_720p_t2v",
        "video_hunyuan_video_1.5_720p_i2v",
    ],
    # meshes with PBR, Unity/Blender-ready
    "3d": ["3d_hunyuan3d-v2.1", "3d_hunyuan3d_image_to_model"],
    # second aesthetic
    "flux2": ["image_flux2_fp8", "image_flux2"],
    # diffusion upscaler, better than GAN on faces and text
    "upscale": ["utility_seedvr2_3b_int8_upscale_image"],
}


def installed():
    have = set()
    for root, _dirs, files in os.walk(MODELS):
        for f in files:
            have.add(f)
    return have


def entries_for(template):
    path = os.path.join(TPL, template + ".json")
    if not os.path.exists(path):
        print(f"  ! no such template: {template}", file=sys.stderr)
        return []
    try:
        d = json.loads(open(path, encoding="utf-8").read())
    except Exception as e:
        print(f"  ! unreadable {template}: {e}", file=sys.stderr)
        return []
    if not isinstance(d, dict):
        return []
    out = []

    def scan(nodes):
        for n in nodes:
            for m in (n.get("properties") or {}).get("models") or []:
                if m.get("url") and m.get("name"):
                    out.append((m.get("directory") or "", m["name"], m["url"]))

    scan(d.get("nodes", []))
    for sg in d.get("definitions", {}).get("subgraphs", []) or []:
        scan(sg.get("nodes", []))
    return out


def head_size(url):
    req = urllib.request.Request(url, method="HEAD")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return int(r.headers.get("Content-Length") or 0)
    except (urllib.error.URLError, ValueError, OSError) as e:
        print(f"  ! HEAD failed {url.rsplit('/', 1)[-1]}: {e}", file=sys.stderr)
        return 0


def main():
    p = argparse.ArgumentParser()
    p.add_argument("templates", nargs="*")
    p.add_argument("--tier", action="append", default=[],
                   help=f"one of: {', '.join(sorted(TIERS))}")
    p.add_argument("-o", "--out", default=None)
    p.add_argument("--no-head", action="store_true", help="skip size lookups")
    p.add_argument("--exclude", action="append", default=[],
                   help="filename to leave out, repeatable")
    p.add_argument("--why", action="store_true",
                   help="show which template pulled in each file")
    a = p.parse_args()

    names = list(a.templates)
    for t in a.tier:
        if t not in TIERS:
            p.error(f"unknown tier {t!r}; have {', '.join(sorted(TIERS))}")
        names += TIERS[t]
    if not names:
        p.error("name at least one template or --tier")

    have = installed()
    seen, rows, skipped, attr = set(), [], [], {}

    for t in names:
        for directory, name, url in entries_for(t):
            attr.setdefault(name, []).append(t)
            if name in seen:
                continue
            seen.add(name)
            if name in have:
                skipped.append(name)
                continue
            if name in a.exclude:
                continue
            rows.append([directory, name, 0, url])

    if not a.no_head:
        print(f"checking sizes for {len(rows)} file(s)...", file=sys.stderr)
        for r in rows:
            r[2] = head_size(r[3])

    total = sum(r[2] for r in rows)
    print(f"\n{len(skipped)} already installed, {len(rows)} to fetch, "
          f"{total / 2**30:.1f} GiB total\n", file=sys.stderr)
    for directory, name, size, _url in sorted(rows, key=lambda r: -r[2]):
        print(f"  {size / 2**30:8.2f} GiB  {directory or '?':<18} {name}",
              file=sys.stderr)
        if a.why:
            print(f"{'':14}<- {', '.join(sorted(set(attr.get(name, []))))}",
                  file=sys.stderr)

    out = a.out or os.path.join(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))), "manifest.tsv")
    with open(out, "w", encoding="utf-8") as f:
        for directory, name, size, url in rows:
            f.write(f"{directory}\t{name}\t{size}\t{url}\n")
    print(f"\nmanifest -> {out}", file=sys.stderr)
    if skipped:
        print(f"skipped (already present): {', '.join(sorted(skipped)[:8])}"
              + (" ..." if len(skipped) > 8 else ""), file=sys.stderr)


if __name__ == "__main__":
    main()
