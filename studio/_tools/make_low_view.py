"""A whole-figure low view, made with a retry that does not throw the angle away.

The first attempt used the pack's own must-be-whole renderer, whose fallback is a
FAR FRAMING sentence: "stand well back, the whole figure in frame".  It works - all four
packs came back whole - and on three of the four the far framing had quietly moved the
camera back to eye level, and on one it had turned a standing figure into a crouch.  The
detector was satisfied because the detector measures wholeness and nothing else.

The law: a retry sentence must restate what the shot must NOT lose.  So the fallback here
says the framing AND the angle AND the pose, and the result is gated on both rulers - the
truncation detector for wholeness, and the silhouette's bottom-heaviness against the pack's
own eye-level full body for the angle.
"""
import importlib.util
import json
import os
import sys
import time

ROOT = os.path.expanduser("~/shared/comfy-studio")
STUDIO = os.path.join(ROOT, "studio")
TOOLS = os.path.join(STUDIO, "_tools")
sys.path.insert(0, TOOLS)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
sys.path.insert(0, "/tmp")

spec = importlib.util.spec_from_file_location("fr_mod2", os.path.join(TOOLS, "foundry_routes.py"))
FR = importlib.util.module_from_spec(spec)
spec.loader.exec_module(FR)
FY = FR.FY
import lowview_probe as LV

KEY = "pres_low_full"
ANGLE = ("a low-angle shot, the camera set close to the ground and tilted up at them, "
         "looking up at the underside of the jaw, the head high against the sky")
WHOLE = "the whole figure from the top of the head to the soles of the shoes inside the frame"
POSE = "standing upright at ease, both feet on the ground"
FAR = ("photographed from far enough away that %s, the camera still low to the ground and "
       "still tilted up at them" % WHOLE)
MIN_DELTA = 0.04
FR._log = lambda jid, msg: print("      %s" % msg, flush=True)   # no job board out here


def score(cid, path):
    try:
        s = LV.silhouette(path)
        if s is None:
            return None
        return LV.weight(s)
    except Exception:
        return None


def make(cid, seeds=(31, 32, 33, 34, 35, 36)):
    a = FY.load_asset("character", cid)
    adir = FY.asset_dir("character", cid)
    dest = os.path.join(adir, KEY + ".png")
    base = os.path.join(adir, "base_fullbody.png")
    w_base = score(cid, base)
    if not FR.ensure_comfy():
        raise SystemExit("ComfyUI will not come up")
    st = FY.style_info(a["style"])
    best, best_d = None, -9
    t0 = time.time()
    for i, seed in enumerate(seeds):
        body = "%s, %s, %s" % (ANGLE, POSE, WHOLE if i < 3 else FAR)
        if st["kf_engine"] == "animagine":
            prompt = "full body, cowboy shot off, from below, %s, %s" % (a["compiled"]["tags"], body)
        else:
            prompt = "%s, %s" % (a["compiled"]["clause"], body)
        FR._render_direct(a, prompt, dest, seed=seed, full_length=True)
        ok, detail = FR._fullbody_ok(dest)
        w = score(cid, dest)
        d = (w - w_base) if (w is not None and w_base is not None) else None
        print("   %s seed %d: whole=%-5s (%s) bottom-heavy %+.3f" % (cid, seed, ok, detail, d if d is not None else 0), flush=True)
        if ok and d is not None and d >= MIN_DELTA:
            import shutil
            shutil.copy2(dest, dest + ".keep")
            best, best_d = seed, d
            break
        if ok and d is not None and d > best_d:
            import shutil
            shutil.copy2(dest, dest + ".keep")
            best, best_d = seed, d
        if (not ok) and d is not None and d >= MIN_DELTA:
            # the angle is right and the feet are outside the frame: extend the picture
            # downward rather than throw the angle away with a far-framing sentence
            print("   %s seed %d: angle is right, extending the picture downward" % (cid, seed), flush=True)
            FR._extend_down(a, dest, "cli")
            ok2, det2 = FR._fullbody_ok(dest)
            w2 = score(cid, dest)
            d2 = (w2 - w_base) if (w2 is not None and w_base is not None) else None
            print("   %s extended: whole=%-5s (%s) bottom-heavy %+.3f" % (cid, ok2, det2, d2 or 0), flush=True)
            if ok2 and d2 is not None and d2 >= MIN_DELTA:
                import shutil
                shutil.copy2(dest, dest + ".keep")
                best, best_d = seed, d2
                break
    if best is not None and os.path.exists(dest + ".keep"):
        os.replace(dest + ".keep", dest)
    good = best_d >= MIN_DELTA
    print("%s: %s (seed %s, bottom-heavy %+.3f) in %.0fs"
          % (cid, "a low view" if good else "WHOLE BUT NOT LOW - kept the best", best, best_d, time.time() - t0), flush=True)
    a.setdefault("images", {})[KEY] = KEY + ".png"
    json.dump(a, open(os.path.join(adir, "asset.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    return {"pack": cid, "seed": best, "delta": round(best_d, 3), "low": bool(good)}


if __name__ == "__main__":
    out = []
    for cid in (sys.argv[1:] or ["ines-varga", "bai-liwen", "mara-okonjo"]):
        try:
            out.append(make(cid))
        except Exception as e:
            print("%s FAILED %s" % (cid, str(e)[:200]), flush=True)
    json.dump(out, open("/tmp/lowview2.json", "w"), indent=1)
    print("LOW VIEWS 2 DONE", flush=True)
