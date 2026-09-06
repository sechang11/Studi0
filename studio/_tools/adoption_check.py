"""Is the LoRA actually wired into the studio's own path, or only into the test harness?

Builds the keyframe workflow exactly as _render_shot_keyframe does for an anime film, for a
pack that has a LoRA and one that does not, and reads the graph back: is the LoRA node there,
does everything that should read from it read from it, is the reference weight zero where a
LoRA answers alone, and does the trigger word lead the prompt.
"""
import importlib.util
import json
import os
import sys

ROOT = os.path.expanduser("~/shared/comfy-studio")
sys.path.insert(0, os.path.join(ROOT, "studio", "_tools"))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from comfy import set_path  # noqa: E402
from epic import load_wf  # noqa: E402

sp = importlib.util.spec_from_file_location("fr", os.path.join(ROOT, "studio", "_tools", "film_routes.py"))
FR = importlib.util.module_from_spec(sp)
sp.loader.exec_module(FR)


def build_like_studio(pack, sheet="sheet.png", ipa_plan=0.6):
    """the same few lines _render_shot_keyframe runs for an anime film"""
    wf = load_wf("22_anime_kf_ipadapter.json")
    lo, tr = FR.pack_lora(pack)
    set_path(wf, "2.inputs.image", sheet)
    set_path(wf, "4.inputs.weight", 0.0 if lo else (float(ipa_plan) if sheet else 0.0))
    pre = ("%s, " % tr) if lo else ""
    set_path(wf, "5.inputs.text", "%sa shot, a place, masterpiece" % pre)
    if lo:
        FR._add_lora(wf, set_path, lo)
    return wf, lo, tr


print("%-14s %-8s %-26s %-7s %-24s" % ("pack", "lora?", "lora file", "ref wt", "prompt starts"))
def _adopted():
    """ask the packs, do not carry a list - two of the four this was written with are gone"""
    base = os.path.join(ROOT, "studio", "foundry", "characters")
    out = []
    for cid in sorted(os.listdir(base)):
        try:
            a = json.load(open(os.path.join(base, cid, "asset.json"), encoding="utf-8"))
        except Exception:
            continue
        if (a.get("lora") or {}).get("file"):
            out.append(cid)
    return out


CONTROL = "tomas-reyl"   # carries no face: the no-LoRA path should still look right
for pack in _adopted() + [CONTROL]:
    d = os.path.join(ROOT, "studio", "foundry", "characters", pack)
    if not os.path.isdir(d):
        continue
    wf, lo, tr = build_like_studio(pack)
    node = wf.get("packlora")
    reads = [n for n in ("3", "5", "6")
             if isinstance((wf.get(n, {}).get("inputs") or {}).get("model" if n == "3" else "clip"), list)
             and (wf[n]["inputs"]["model" if n == "3" else "clip"])[0] == "packlora"]
    print("%-14s %-8s %-26s %-7s %-24s" % (
        pack, "yes" if lo else "no", (lo or "-")[:26], wf["4"]["inputs"]["weight"],
        wf["5"]["inputs"]["text"][:24]))
    if lo:
        ok = bool(node) and set(reads) == {"3", "5", "6"} and wf["4"]["inputs"]["weight"] == 0.0 \
            and wf["5"]["inputs"]["text"].startswith(tr)
        print("     node present: %s | fed to %s | %s" % (
            bool(node), ",".join(reads) or "nothing", "WIRED" if ok else "NOT WIRED CORRECTLY"))
