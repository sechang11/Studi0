"""Re-score identity on the picked takes of a film with the head box carried into the
studio's first-frame window (the post move's zoom and offset), then rewrite the notes,
the check table and the catalog's `checked` blocks. Run when no job is writing the film.

    python3 rescore_identity.py encyclopedia-check [builder-test ...]
"""
import json
import os
import subprocess
import sys
import time

ROOT = os.path.expanduser("~/shared/comfy-studio/studio")
sys.path.insert(0, os.path.join(ROOT, "_tools"))
import compose as C  # noqa: E402
from PIL import Image  # noqa: E402

PY = os.path.expanduser("~/ComfyUI/venv/bin/python")
INFO_PREFIX = ("ends closer", "sound borrowed", "words not in the picture", "camera:", "identity:")


def head_box(src):
    if src.get("framing") == "close":
        return [0.30, 0.03, 0.70, 0.60]
    try:
        plate_p = src.get("plate") or ""
        if not (isinstance(plate_p, str) and plate_p.startswith("/")):
            plate_p = C.plate_for(src["place"], src.get("plate") or None)
            if isinstance(plate_p, tuple):
                plate_p = plate_p[0]
        plate = Image.open(plate_p).convert("RGB")
        W, H = plate.size
        dpath = C.depth_for_plate(plate_p)
        y_feet, th, _ = C.place_by_depth(plate, dpath, float(src.get("stand", 0.3)), float(src.get("cx", 0.45)))
        hw = th * 0.16
        cx = float(src.get("cx", 0.45)) * W
        return [(cx - hw * 0.75) / W, (y_feet - th) / H, (cx + hw * 0.75) / W, (y_feet - th + hw * 1.25) / H]
    except Exception:
        return None


def window0(post):
    """the studio's first-frame window for a recorded post move (older takes lack cx/cy)"""
    if not post:
        return None
    z = float(post.get("zoom_start", 1.0) or 1.0)
    cx, cy = post.get("cx_start"), post.get("cy_start")
    if cx is None or cy is None:
        mv, amt = post.get("move"), float(post.get("amount") or 0)
        room = (1.0 - 1.0 / z) / 2.0 if z > 1 else 0.0
        cx, cy = 0.5, 0.5
        if mv == "pan":
            cx = 0.5 - min(abs(amt), 2 * room) / 2 * (1 if amt > 0 else -1)
        elif mv == "tilt":
            cy = 0.5 - min(abs(amt), 2 * room) / 2 * (1 if amt > 0 else -1)
        elif mv == "whip":
            cx = 0.5 - min(abs(amt), 2 * room) / 2 * (1 if amt > 0 else -1)
    return {"zoom": z, "cx": float(cx), "cy": float(cy)}


HEAD_MOVERS = {"crouch", "kneel", "sit", "sit_down", "bow", "lie", "lie_down", "stand_up", "fall", "duck", "pick_up"}


def verdict_note(res, cid, covered, mover=None):
    vs, ve = res.get("verdict_start"), res.get("verdict_end") or ""
    if mover and ve in ("a different face", "uncertain") and vs != "a different face":
        ve = "unmeasured (the %s moves the head and the end box is not followed; %.2f not judged)" % (mover, res.get("end") or 0)
        res["verdict_end"] = ve
    if vs == "a different face" and covered:
        note, fault = "identity: the near figure may cover the face at the start (%.2f); end %s" % (res["start"], ve or "unmeasured"), False
    elif vs == "a different face":
        note, fault = "the face is not %s's from the first frame (identity %.2f)" % (cid, res["start"]), True
    elif ve == "a different face":
        note, fault = "the face is a different one by the end (identity %.2f -> %.2f)" % (res["start"], res["end"]), True
    elif ve.startswith("unmeasured"):
        note, fault = "identity: %s at the start (%.2f); %s" % (vs, res["start"], ve), False
    elif ve == "uncertain":
        note, fault = "identity: uncertain by the end (%.2f -> %.2f)" % (res["start"], res["end"]), False
    else:
        note, fault = "identity: same person, start %.2f, end %.2f" % (res["start"], res["end"]), False
    if res.get("place_hold") is not None:
        note = "%s; place %s (%.2f first to last)" % (note, res.get("place_verdict") or "?", res["place_hold"])
    return note, fault


def rescore(fid):
    fp = os.path.join(ROOT, "films", fid, "film.json")
    film = json.load(open(fp, encoding="utf-8"))
    jobs, where = [], []
    for shid, sh in sorted(film["shots"].items()):
        src = sh.get("anchor_source") or {}
        cid = src.get("character")
        if not cid:
            continue
        portrait = os.path.join(ROOT, "foundry", "characters", cid, "base_portrait.png")
        if not os.path.exists(portrait):
            continue
        sc = next((s for s in film["scenes"] if s["id"] == sh.get("scene")), {}) if isinstance(film.get("scenes"), list) else (film.get("scenes") or {}).get(sh.get("scene"), {})
        plate = os.path.join(ROOT, "foundry", "places", sc.get("place") or "", (sc.get("plate") or "") + ".png") if sc.get("place") and sc.get("plate") else None
        for t in sh.get("takes") or []:
            if t["id"] != sh.get("picked") or not t.get("file"):
                continue
            video = os.path.join(ROOT, "films", fid, t["file"])
            if not os.path.exists(video):
                continue
            cam = t.get("cam_measured") or {}
            jobs.append({"id": "%s/%s/%s" % (fid, shid, t["id"]), "portrait": portrait, "video": video, "box": head_box(src),
                         "close": src.get("framing") == "close", "cam": {k: cam.get(k) for k in ("zoom", "pan", "tilt")} if cam else None,
                         "plate": plate if plate and os.path.exists(plate) else None, "window0": window0(cam.get("post"))})
            _mv = next((str(b.get("motion") or "").lower() for b in (sh.get("beats") or []) if str(b.get("motion") or "").lower().replace(" ", "_") in HEAD_MOVERS), None)
            where.append((shid, t["id"], cid, any(bool(p.get("ots")) for p in (src.get("props") or []) if isinstance(p, dict)), _mv))
    if not jobs:
        print(fid, "nothing to rescore")
        return
    jp = "/tmp/rescore_%s.json" % fid
    json.dump(jobs, open(jp, "w"))
    p = subprocess.run([PY, os.path.join(ROOT, "_tools", "identity.py"), jp], capture_output=True, text=True, cwd=os.path.expanduser("~/ComfyUI"))
    results = {}
    for line in p.stdout.splitlines():
        try:
            d = json.loads(line)
            results[d.get("id")] = d
        except Exception:
            pass
    film = json.load(open(fp, encoding="utf-8"))   # fresh, in case a job wrote meanwhile
    changed = 0
    for (shid, tid, cid, covered, mover), job in zip(where, jobs):
        res = results.get(job["id"])
        if not res or res.get("error"):
            continue
        sh = film["shots"][shid]
        t = next((x for x in sh["takes"] if x["id"] == tid), None)
        if not t:
            continue
        old_ident = t.get("identity") or {}
        ident = {k: res.get(k) for k in ("start", "end", "hold", "verdict_start", "verdict_end", "place_hold", "place_verdict", "place_start")}
        ident["who"] = cid
        note, fault = verdict_note(res, cid, covered, mover)
        ident["verdict_end"] = res.get("verdict_end")
        qc = [n for n in (t.get("qc") or []) if not (n.startswith("identity:") or n.startswith("the face is"))]
        qc.append(note)
        t["identity"], t["qc"] = ident, qc
        changed += 1
        print("  %s/%s %s: start %s -> %s | end %s -> %s | %s" % (fid, shid, tid, old_ident.get("start"), res.get("start"), old_ident.get("end"), res.get("end"), res.get("verdict_end")), flush=True)
    json.dump(film, open(fp, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print(fid, "rescored", changed, "picked takes")


if __name__ == "__main__":
    for fid in sys.argv[1:] or ["encyclopedia-check"]:
        rescore(fid)
    # the check table and the catalog follow the film
    chk_p = os.path.join(ROOT, "shot_catalog_check.json")
    if os.path.exists(chk_p):
        chk = json.load(open(chk_p, encoding="utf-8"))
        film = json.load(open(os.path.join(ROOT, "films", "encyclopedia-check", "film.json"), encoding="utf-8"))
        cat_p = os.path.join(ROOT, "shot_catalog.json")
        cat = json.load(open(cat_p, encoding="utf-8"))
        for entry, r in chk.items():
            for tk in r.get("takes", []):
                for sid in r.get("shots", []):
                    t = next((x for x in film["shots"].get(sid, {}).get("takes", []) if x["id"] == tk["id"]), None)
                    if t:
                        tk["identity"] = (t.get("identity") or {}).get("verdict_end") or (t.get("identity") or {}).get("verdict_start")
                        tk["notes"] = [n[:90] for n in (t.get("qc") or [])]
        json.dump(chk, open(chk_p, "w", encoding="utf-8"), indent=1)
        for s in cat["shots"]:
            r = chk.get(s["id"])
            if not r:
                continue
            p = next((t for t in r.get("takes", []) if t.get("picked")), {})
            s["checked"] = {"when": r["when"], "built": r.get("built"), "camera": p.get("camera"), "identity": p.get("identity"), "notes": p.get("notes", [])[:4], "spec": r.get("spec")}
        json.dump(cat, open(cat_p, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
        lines = ["# The encyclopedia, checked", "", "Every entry built once through the builder into `encyclopedia-check`, one variant; faces re-scored with the head box carried into the studio's first-frame window. Regenerated %s." % time.strftime("%Y-%m-%d %H:%M"), "",
                 "| entry | built | s | picked engine | camera measured | face | notes |", "|---|---|---|---|---|---|---|"]
        for s in cat["shots"]:
            r = chk.get(s["id"])
            if not r:
                continue
            p = next((t for t in r.get("takes", []) if t.get("picked")), {})
            lines.append("| %s | %s | %s | %s | %s | %s | %s |" % (s["id"], "yes" if r.get("built") else "NO", r.get("seconds") or "", p.get("engine", ""), p.get("camera", ""), p.get("identity", ""), "; ".join(p.get("notes", []))[:120]))
        open(os.path.join(ROOT, "shot_catalog_check.md"), "w", encoding="utf-8").write("\n".join(lines) + "\n")
        print("check table and catalog refreshed")
