#!/usr/bin/env python3
"""Re-check an already-adopted LoRA on more seeds, without retraining it.

The first three were adopted on a single rendered comparison, which is the seed lottery this
project spends its time avoiding everywhere else.  This re-runs only the comparison - the same
four routes, several seeds - and un-adopts anything whose margin does not survive.

    python3 verify_pack_lora.py bai-liwen renji terra
    python3 verify_pack_lora.py --seeds 5 terra
"""
import argparse
import json
import os
import statistics
import sys

ROOT = os.path.expanduser("~/shared/comfy-studio")
TOOLS = os.path.join(ROOT, "studio", "_tools")
sys.path.insert(0, TOOLS)
import pack_lora as PL  # noqa: E402

CHARS = os.path.join(ROOT, "studio", "foundry", "characters")


def verify(pack, seeds):
    p = os.path.join(CHARS, pack, "asset.json")
    a = json.load(open(p, encoding="utf-8"))
    lo = a.get("lora") or {}
    if not lo.get("file"):
        print("%s: no LoRA on the pack" % pack)
        return None
    trigger = lo.get("trigger") or pack.replace("-", "")
    tags = (a.get("compiled") or {}).get("tags") or "1girl, solo"
    tags = ", ".join(t.strip() for t in tags.split(",")[:6] if t.strip())
    print("\n=== %s (%s) ===" % (pack, lo["file"]), flush=True)
    got = {"ipadapter": [], "lora": []}
    for seed in seeds:
        files = {"ipadapter": PL.close_up(pack, trigger, tags, None, 0.6, "v_ipa%d" % seed, seed),
                 "lora": PL.close_up(pack, trigger, tags, lo["file"], 0.0, "v_lora%d" % seed, seed)}
        sc = PL.score(pack, files)
        for k in got:
            if sc.get(k) is not None:
                got[k].append(sc[k])
        print("  seed %-5d reference %s | the LoRA %s" % (
            seed, ("%.3f" % sc["ipadapter"]) if sc.get("ipadapter") else "-",
            ("%.3f" % sc["lora"]) if sc.get("lora") else "-"), flush=True)
    if not got["lora"] or not got["ipadapter"]:
        print("  could not score - left as it was")
        return None
    ipa, lora = statistics.mean(got["ipadapter"]), statistics.mean(got["lora"])
    spread = max(got["lora"]) - min(got["lora"])
    keep = lora > ipa + max(0.02, spread / 2.0)
    print("  reference %.3f | the LoRA %.3f | spread %.3f over %d seeds -> %s"
          % (ipa, lora, spread, len(got["lora"]), "STANDS" if keep else "UN-ADOPTED"), flush=True)
    lo["measured"] = ("a close-up scores %.3f against the pack portrait where the reference-image "
                      "path scores %.3f, averaged over %d seeds (spread %.3f)"
                      % (lora, ipa, len(got["lora"]), spread))
    lo["seeds"] = len(got["lora"])
    if keep:
        a["lora"] = lo
    else:
        a["lora_withdrawn"] = lo
        a.pop("lora", None)
    json.dump(a, open(p, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    return {"pack": pack, "reference": round(ipa, 3), "lora": round(lora, 3),
            "spread": round(spread, 3), "stands": keep, "seeds": len(got["lora"])}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("packs", nargs="+")
    ap.add_argument("--seeds", type=int, default=3)
    args = ap.parse_args()
    pool = [4242, 7, 913, 20260906, 31]
    seeds = pool[:max(2, min(args.seeds, len(pool)))]
    rows = []
    for pk in args.packs:
        try:
            r = verify(pk, seeds)
            if r:
                rows.append(r)
        except Exception as e:
            print("%s FAILED: %s" % (pk, str(e)[:200]), flush=True)
    if rows:
        print("\n%-16s %10s %10s %8s %6s  %s" % ("pack", "reference", "LoRA", "spread", "seeds", ""))
        for r in rows:
            print("%-16s %10.3f %10.3f %8.3f %6d  %s" % (
                r["pack"], r["reference"], r["lora"], r["spread"], r["seeds"],
                "stands" if r["stands"] else "UN-ADOPTED"))
        json.dump(rows, open(os.path.join(ROOT, "studio", "pack_loras_verified.json"), "w"), indent=1)
    print("VERIFY DONE", flush=True)
