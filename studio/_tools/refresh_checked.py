"""Refresh a catalog entry's checked record from the newest shot that entry built."""
import io, json, os, sys
ROOT = os.path.expanduser("~/shared/comfy-studio/studio")
INFO = ("ends closer", "sound borrowed", "words not in the picture", "camera:", "identity:",
        "angle:", "the studio cut the take")
cat = json.load(io.open(os.path.join(ROOT, "shot_catalog.json"), encoding="utf-8"))
films = sys.argv[1:] or ["angles-and-mass"]
newest = {}
for fid in films:
    fp = os.path.join(ROOT, "films", fid, "film.json")
    if not os.path.exists(fp): continue
    film = json.load(io.open(fp, encoding="utf-8"))
    for sid, sh in sorted(film["shots"].items()):
        e = sh.get("template")
        if e:
            newest[e] = (fid, sid, sh)
n = 0
for e, (fid, sid, sh) in newest.items():
    sc = next((x for x in cat["shots"] if x["id"] == e), None)
    if not sc: continue
    old = (sc.get("checked") or {}).get("shot")
    if old == sid: continue
    t = next((x for x in sh.get("takes") or [] if x["id"] == sh.get("picked")), None) or (sh.get("takes") or [None])[-1]
    if not t: continue
    am = t.get("angle_measured") or {}
    notes = [str(q)[:90] for q in (t.get("qc") or [])]
    faults = [q for q in notes if not q.startswith(INFO)]
    sc["checked"] = {"when": "2026-09-05 16:55", "built": True,
                     "camera": (t.get("cam_measured") or {}).get("camera"),
                     "angle": (am.get("angle") if am.get("confidence") not in (None, "none") else None),
                     "identity": (t.get("identity") or {}).get("verdict_end"),
                     "notes": notes[:4], "film": fid, "shot": sid, "clean": not faults}
    print("  %-18s %s -> %s  %s" % (e, old, sid, "clean" if not faults else faults[0][:70]))
    n += 1
io.open(os.path.join(ROOT, "shot_catalog.json"), "w", encoding="utf-8", newline="\n").write(
    json.dumps(cat, indent=1, ensure_ascii=False))
built = sum(1 for x in cat["shots"] if x.get("checked"))
clean = sum(1 for x in cat["shots"] if (x.get("checked") or {}).get("clean"))
print("refreshed %d | %d of %d entries with a record" % (n, built, len(cat["shots"])))
