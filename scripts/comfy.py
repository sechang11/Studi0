#!/usr/bin/env python3
"""
comfy.py - minimal ComfyUI API client for the k4shix 5090 box.

Submit an API-format workflow, stream progress, report timing + outputs.

Usage:
    python comfy.py run workflow.json [-s key=value ...] [--host HOST]
    python comfy.py nodes [filter]        # list available node types
    python comfy.py models                # list installed model files
    python comfy.py stats                 # system / VRAM stats

The -s flag patches the workflow before submit, e.g.:
    -s 6.inputs.text="a red fox"  -s 9.inputs.seed=1234
"""
import argparse
import json
import sys
import time
import urllib.request
import urllib.parse
import uuid

DEFAULT_HOST = "127.0.0.1:8188"


def api(host, path, payload=None):
    url = f"http://{host}{path}"
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        try:
            err = json.loads(body)
            print(json.dumps(err, indent=2)[:4000], file=sys.stderr)
        except ValueError:
            print(body[:4000], file=sys.stderr)
        sys.exit(1)


def set_path(wf, dotted, value):
    """set_path(wf, '9.inputs.seed', 42)"""
    keys = dotted.split(".")
    node = wf
    for k in keys[:-1]:
        node = node[k]
    # coerce numeric strings so KSampler gets ints not strings
    if isinstance(value, str):
        try:
            value = int(value)
        except ValueError:
            try:
                value = float(value)
            except ValueError:
                pass
    node[keys[-1]] = value


def run(host, wf, quiet=False):
    client_id = str(uuid.uuid4())
    t0 = time.time()
    resp = api(host, "/prompt", {"prompt": wf, "client_id": client_id})
    if "error" in resp:
        print(json.dumps(resp, indent=2), file=sys.stderr)
        sys.exit(1)
    pid = resp["prompt_id"]
    if not quiet:
        print(f"queued {pid}", file=sys.stderr)

    last = None
    while True:
        time.sleep(1.5)
        hist = api(host, f"/history/{pid}")
        if pid in hist:
            entry = hist[pid]
            status = entry.get("status", {})
            if status.get("status_str") == "error":
                for m in status.get("messages", []):
                    print(m, file=sys.stderr)
                sys.exit(1)
            if status.get("completed"):
                break
        q = api(host, "/queue")
        running = q.get("queue_running") or []
        pend = len(q.get("queue_pending") or [])
        state = f"running={len(running)} pending={pend}"
        if state != last and not quiet:
            print(f"  [{time.time()-t0:6.1f}s] {state}", file=sys.stderr)
            last = state

    elapsed = time.time() - t0
    outs = []
    for node_id, out in api(host, f"/history/{pid}")[pid]["outputs"].items():
        for kind in ("images", "videos", "audio", "gifs", "3d"):
            for f in out.get(kind, []):
                outs.append(f"{f.get('subfolder','')}/{f['filename']}".lstrip("/"))
    print(f"DONE in {elapsed:.1f}s -> {', '.join(outs) or '(no file outputs)'}")
    return elapsed, outs


def main():
    p = argparse.ArgumentParser()
    p.add_argument("cmd", choices=["run", "nodes", "models", "stats"])
    p.add_argument("arg", nargs="?")
    p.add_argument("-s", "--set", action="append", default=[])
    p.add_argument("--host", default=DEFAULT_HOST)
    a = p.parse_args()

    if a.cmd == "stats":
        s = api(a.host, "/system_stats")
        d = s["devices"][0]
        print(f"{d['name']}")
        print(f"  VRAM  {d['vram_free']/2**30:.1f} / {d['vram_total']/2**30:.1f} GiB free")
        print(f"  RAM   {s['system']['ram_free']/2**30:.1f} / {s['system']['ram_total']/2**30:.1f} GiB free")
        print(f"  Comfy {s['system']['comfyui_version']}  torch {s['system']['pytorch_version']}")
        return

    if a.cmd == "nodes":
        info = api(a.host, "/object_info")
        f = (a.arg or "").lower()
        hits = sorted(k for k in info if f in k.lower())
        print(f"{len(hits)} node(s)")
        for h in hits:
            print(" ", h)
        return

    if a.cmd == "models":
        info = api(a.host, "/object_info")
        for node, key in [
            ("UNETLoader", "unet_name"), ("CheckpointLoaderSimple", "ckpt_name"),
            ("CLIPLoader", "clip_name"), ("VAELoader", "vae_name"),
            ("LoraLoaderModelOnly", "lora_name"), ("ControlNetLoader", "control_net_name"),
            ("UpscaleModelLoader", "model_name"), ("CLIPVisionLoader", "clip_name"),
            ("AudioEncoderLoader", "audio_encoder_name"),
        ]:
            n = info.get(node)
            if not n:
                continue
            vals = n["input"]["required"].get(key, [[]])[0]
            print(f"-- {node}.{key}: {len(vals)}")
            for v in vals:
                print("   ", v)
        return

    wf = json.load(open(a.arg))
    # keys starting with "_" are documentation, not nodes
    wf = {k: v for k, v in wf.items() if not k.startswith("_")}
    for kv in a.set:
        k, _, v = kv.partition("=")
        set_path(wf, k, v)
    run(a.host, wf)


if __name__ == "__main__":
    main()
