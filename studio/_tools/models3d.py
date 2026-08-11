#!/usr/bin/env python3
"""A library of free, printable 3D models - catalogued with their licence, not just grabbed.

    python3 studio/_tools/models3d.py sources          # where models can come from, and why
    python3 studio/_tools/models3d.py index nasa       # catalogue a source (no files yet)
    python3 studio/_tools/models3d.py list             # what is catalogued
    python3 studio/_tools/models3d.py fetch bennu      # download one, then measure it
    python3 studio/_tools/models3d.py fetch --all --limit 20
    python3 studio/_tools/models3d.py check bennu      # printability, from the mesh

LICENCE IS A FIELD, NOT AN AFTERTHOUGHT. Most "free" 3D print models are free to DOWNLOAD
under terms that are not free to redistribute - CC-BY needs attribution, CC-BY-NC forbids
commercial use, and a lot of popular sites host models whose terms are set per upload
rather than per site. A library that does not record which is which is a liability the
first time anything leaves this machine. So every card carries its licence, its source URL
and whether attribution is required, and the indexer refuses a source it cannot state a
licence for.

CATALOGUE FIRST, DOWNLOAD SECOND. Indexing writes metadata only. Nothing is fetched until
it is asked for by name, or with an explicit --limit. Mass-downloading someone's whole
catalogue is rude to the host and fills a disk with models nobody chose.
"""
import argparse, json, os, re, subprocess, sys, time, urllib.parse, urllib.request

TOOLS = os.path.dirname(os.path.abspath(__file__))
STUDIO = os.path.dirname(TOOLS)
ROOT = os.path.dirname(STUDIO)
CARDS = os.path.join(STUDIO, "models3d")
FILES = os.path.join(STUDIO, "samples", "models3d")

UA = {"User-Agent": "comfy-studio/1.0 (personal 3d print library)"}

# Only sources whose licence can be stated plainly. A source that says "free to download"
# without naming terms does not go in this table, because "free" is not a licence.
SOURCES = {
    "nasa": {
        "name": "NASA 3D Resources",
        "url": "https://github.com/nasa/NASA-3D-Resources",
        "licence": "public domain (US Government work)",
        "attribution": False,
        "commercial_ok": True,
        "why": "US Government works are not under copyright. Printable STLs live in the "
               "'3D Printing' folder of the GitHub repo, so there is no scraping and no "
               "API key - it is a git repository.",
        "api": "github",
    },
    "smithsonian": {
        "name": "Smithsonian Open Access",
        "url": "https://www.si.edu/openaccess",
        "licence": "CC0 for Open Access items",
        "attribution": False,
        "commercial_ok": True,
        "why": "Around 3,000 CC0 3D scans of real artefacts, which print beautifully. "
               "NEEDS AN api.data.gov KEY, so it is listed rather than indexed here.",
        "api": "needs_key",
    },
    "nih3d": {
        "name": "NIH 3D",
        "url": "https://3d.nih.gov",
        "licence": "mixed - many public domain / CC0, some CC-BY",
        "attribution": True,
        "commercial_ok": None,
        "why": "Biomedical and anatomical models. Licence is PER ENTRY, so each one has to "
               "be read before use. The old public API path now 404s; the site is a "
               "JavaScript app, so indexing it would mean scraping.",
        "api": "none",
    },
    "thingiverse": {
        "name": "Thingiverse",
        "url": "https://www.thingiverse.com",
        "licence": "per upload - usually CC-BY, CC-BY-SA or CC-BY-NC",
        "attribution": True,
        "commercial_ok": None,
        "why": "Huge, but the licence is chosen by each uploader and a lot of it forbids "
               "commercial use or requires share-alike. Needs an API key. Fine to browse "
               "and download by hand; wrong to bulk-mirror.",
        "api": "needs_key",
    },
}


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", str(s).lower()).strip("-")[:60]


def _get(url, tries=3):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=45) as r:
                return r.read()
        except Exception:
            if i == tries - 1:
                raise
            time.sleep(1.5 * (i + 1))


REPO = "nasa/NASA-3D-Resources"
BRANCH = "master"


def index_nasa(limit=None):
    """Walk the repo's 3D Printing folder. Metadata only - nothing is downloaded.

    ONE request for the whole tree, not one per folder. The contents API needs a call per
    directory, and unauthenticated GitHub allows 60 an hour - indexing 106 folders that way
    got 80 of them and then 403ed on the rest, which would have left a library that looked
    complete and silently was not. The recursive tree endpoint returns every path in the
    repository in a single response.
    """
    tree = json.loads(_get("https://api.github.com/repos/%s/git/trees/%s?recursive=1"
                           % (REPO, BRANCH)))
    if tree.get("truncated"):
        print("  ! GitHub truncated the tree; this index is incomplete")
    groups, groups_img = {}, {}
    for node in tree.get("tree", []):
        p = node.get("path", "")
        if node.get("type") != "blob" or not p.startswith("3D Printing/"):
            continue
        parts_i = p.split("/")
        # The preview images the source ships next to the mesh. Skipping these produced a
        # visual catalogue in which every one of 105 cards read NO PREVIEW - technically
        # complete, useless to look at.
        if p.lower().endswith((".png", ".jpg", ".jpeg")) and len(parts_i) >= 3:
            groups_img.setdefault(parts_i[1], []).append(
                {"name": parts_i[-1], "bytes": node.get("size"),
                 "url": "https://raw.githubusercontent.com/%s/%s/%s"
                        % (REPO, BRANCH, urllib.parse.quote(p))})
            continue
        # .7z counts as a mesh source. Eleven folders - Cassini, Perseverance, the Webb
        # mirror, Earth - ship their STLs inside an archive and nothing else, so an
        # extension filter alone drops exactly the models most worth printing.
        if not p.lower().endswith((".stl", ".obj", ".3mf", ".7z")):
            continue
        parts = p.split("/")
        if len(parts) < 3:
            continue
        groups.setdefault(parts[1], []).append(
            {"name": parts[-1], "bytes": node.get("size"),
             "url": "https://raw.githubusercontent.com/%s/%s/%s"
                    % (REPO, BRANCH, urllib.parse.quote(p))})

    os.makedirs(CARDS, exist_ok=True)
    n = 0
    for folder in sorted(groups):
        if limit and n >= limit:
            break
        meshes = sorted(groups[folder], key=lambda f: f["name"])
        entry = {"name": folder}
        sid = slug(entry["name"])
        # MERGE, DO NOT OVERWRITE. Re-indexing must not throw away measurements that cost
        # forty minutes of mesh_doctor to produce. Only the fields the index actually owns
        # are refreshed; everything fetch/measure wrote is carried across.
        prev = {}
        cp = os.path.join(CARDS, sid + ".json")
        if os.path.isfile(cp):
            try:
                prev = json.load(open(cp, encoding="utf-8"))
            except Exception:
                prev = {}
        card = {
            "id": sid, "name": entry["name"],
            "source": "nasa",
            "source_url": "https://github.com/nasa/NASA-3D-Resources/tree/master/"
                          + urllib.parse.quote("3D Printing/" + entry["name"]),
            "licence": SOURCES["nasa"]["licence"],
            "attribution_required": SOURCES["nasa"]["attribution"],
            "commercial_ok": SOURCES["nasa"]["commercial_ok"],
            "files": meshes,
            "images": groups_img.get(folder, []),
            "fetched": False,
            "indexed": time.strftime("%Y-%m-%dT%H:%M:%S"),
        }
        for k in ("fetched", "local_dir", "measured", "measured_file", "verdict", "parts"):
            if k in prev:
                card[k] = prev[k]
        with open(os.path.join(CARDS, sid + ".json"), "w", encoding="utf-8") as f:
            json.dump(card, f, indent=1, ensure_ascii=False)
            f.write("\n")
        n += 1
        print("  %-44s %d file(s)" % (entry["name"][:44], len(meshes)))
    return n


def cards():
    if not os.path.isdir(CARDS):
        return []
    out = []
    for fn in sorted(os.listdir(CARDS)):
        if fn.endswith(".json"):
            try:
                out.append(json.load(open(os.path.join(CARDS, fn), encoding="utf-8")))
            except Exception:
                pass
    return out


def measure(path):
    """Printability comes from mesh_doctor, not from a second opinion written here.

    mesh_doctor.py already diagnoses meshes against craft/PRINTING.md - manifold edges,
    winding, stray shells, solidity, and its own `printable` / `blocking` / `warnings`
    verdict. An earlier draft of this file reimplemented a thinner version with a trimesh
    one-liner, which is how a project ends up with two printability checkers that disagree
    and no way to tell which is right. There is one checker; this calls it.
    """
    # A slow mesh must not take the library down with it. A million-face nebula blew the
    # timeout and the raised TimeoutExpired killed the whole pass, so every model after it
    # alphabetically was silently left unmeasured - and the summary still printed, counting
    # those as results. One unmeasurable model is a fact to record, not a reason to stop.
    try:
        r = subprocess.run([sys.executable, os.path.join(TOOLS, "mesh_doctor.py"),
                            "diagnose", path, "--json"],
                           capture_output=True, text=True, cwd=ROOT, timeout=1800)
    except subprocess.TimeoutExpired:
        return {"error": "mesh_doctor timed out - too heavy to diagnose here"}
    except Exception as e:
        return {"error": ("mesh_doctor could not be run: %s" % e)[-200:]}
    try:
        d = json.loads(r.stdout[r.stdout.index("{"):r.stdout.rindex("}") + 1])
    except Exception:
        return {"error": (r.stderr.strip() or "mesh_doctor could not read the mesh")[-200:]}
    return {
        "mm": [round(float(x), 2) for x in d.get("extents", [0, 0, 0])],
        "faces": d.get("faces"), "vertices": d.get("vertices"),
        "watertight": d.get("is_watertight"),
        "winding_consistent": d.get("is_winding_consistent"),
        "components": d.get("components", 1),
        "volume_cm3": round(d["volume"] / 1000.0, 2) if d.get("volume") else None,
        "printable": d.get("printable"),
        "blocking": d.get("blocking") or [],
        "warnings": d.get("warnings") or [],
    }


BED_MM = 256.0   # a common bed; anything past this needs splitting


def verdict(m):
    """Say what would actually happen on the printer, not just what the file contains.

    AN STL CARRIES NUMBERS, NOT UNITS. Slicers assume millimetres, but plenty of these
    models - asteroids, nebulae, the Webb mirror - were exported in normalised or
    astronomical units, so the mesh honestly measures 1 x 1 x 1 and would slice to a speck.
    Reporting that as 'a 1mm model' would be true about the file and false about the world.
    A scale factor is not a defect; being silent about it is.
    """
    if "error" in m:
        return {"state": "unreadable", "printable": None,
                "why": ["the mesh could not be read"]}
    mm = m.get("mm") or [0, 0, 0]
    if "printable" not in m:
        # A measurement taken before mesh_doctor was wired in carries dimensions but no
        # verdict. Saying nothing is the honest answer; the previous version fell through
        # to the empty-`why` branch and called such a card READY TO PRINT on no evidence.
        return {"state": "not judged", "printable": None, "needs_scale": None,
                "oversize": None,
                "why": ["measured before mesh_doctor was wired in - run remeasure"]}
    ok = m.get("printable")
    why = list(m.get("blocking") or []) + list(m.get("warnings") or [])
    big = max(mm) if mm else 0
    # TWO TIERS, BECAUSE ONE THRESHOLD CANNOT TELL THE TWO CASES APART. Below 2 mm nothing
    # is a real object, so the file is certainly in normalised units. Between 2 and 15 mm
    # is genuinely ambiguous - a cubesat part really is that small, an asteroid is not -
    # and a single cutoff has to guess. It guessed wrong: a 5.11 mm asteroid cleared a
    # 5 mm rule and was reported READY TO PRINT. So the ambiguous band is flagged as a
    # question rather than resolved by a number pretending to know.
    needs_scale = bool(big < 2)
    check_scale = bool(2 <= big < 15)
    oversize = bool(big > BED_MM)
    # The one judgement mesh_doctor has no reason to make. It diagnoses meshes this project
    # generated, which are already scaled; these are downloaded from elsewhere.
    if needs_scale:
        why.append("no real-world scale: this measures %.2f mm at its widest, which means "
                   "the file is in normalised or astronomical units. Scale it to the size "
                   "you want before slicing." % big)
    elif check_scale:
        why.append("check the scale: %.1f mm at its widest. That is a plausible size for a "
                   "small part and an implausible one for anything the model depicts, so "
                   "the units may not be millimetres." % big)
    elif oversize:
        why.append("%.0f mm at its widest, past a %.0f mm bed - scale it down or split it"
                   % (big, BED_MM))
    # STATE IS COMPUTED FROM FLAGS, NOT FROM len(why). An earlier version called a model
    # ready when its `why` list had one entry - so a mesh whose single note was "no
    # real-world scale" was reported as ready to print AND as needing scaling, in the same
    # summary. Counting the reasons is not the same as reading them.
    v = {"printable": ok, "needs_scale": needs_scale, "check_scale": check_scale,
         "oversize": oversize, "why": why}
    if ok is None:
        v["state"] = "unreadable"
    elif not ok:
        v["state"] = "not printable"
    elif needs_scale or check_scale or oversize or len(why) > 0:
        v["state"] = "printable, needs a step"
    else:
        v["state"] = "ready as-is"
    if not why:
        why.append("watertight, sensibly scaled, no warnings from mesh_doctor")
    return v


def fetch(sid):
    p = os.path.join(CARDS, sid + ".json")
    if not os.path.isfile(p):
        print("  no such model: %s" % sid)
        return False
    c = json.load(open(p, encoding="utf-8"))
    d = os.path.join(FILES, sid)
    os.makedirs(d, exist_ok=True)
    got = []
    for f in c.get("images", []):
        dst = os.path.join(d, f["name"])
        if os.path.exists(dst):
            continue
        try:
            with open(dst, "wb") as fh:
                fh.write(_get(f["url"]))
        except Exception:
            pass          # a missing preview is cosmetic; it must not fail the model
    for f in c["files"]:
        dst = os.path.join(d, f["name"])
        if not os.path.exists(dst):
            try:
                data = _get(f["url"])
            except Exception as e:
                print("  %-40s FAILED %s" % (f["name"][:40], str(e)[:50]))
                continue
            with open(dst, "wb") as fh:
                fh.write(data)
        got.append(dst)
        # The licence travels WITH the file. A folder of meshes with no terms beside them
        # is exactly how a library becomes unusable six months later.
        with open(os.path.join(d, "LICENCE.txt"), "w", encoding="utf-8") as fh:
            fh.write("%s\n%s\n\nLicence: %s\nAttribution required: %s\n"
                     % (c["name"], c["source_url"], c["licence"],
                        "yes" if c["attribution_required"] else "no"))
    # Unpack any archives, then treat what came out as part of the model.
    for a in [g for g in got if g.lower().endswith(".7z")]:
        r = subprocess.run(["7z", "x", "-y", "-o" + d, a],
                           capture_output=True, text=True)
        if r.returncode != 0:
            print("  %-30s could not unpack %s (is p7zip installed?)"
                  % (sid[:30], os.path.basename(a)))
    for dirpath, _, names in os.walk(d):
        for nm in names:
            if nm.lower().endswith((".stl", ".obj", ".3mf")):
                fp = os.path.join(dirpath, nm)
                if fp not in got:
                    got.append(fp)

    meshes = [g for g in got if not g.lower().endswith(".7z")]
    if meshes:
        # Measure the LARGEST mesh, not the first by name. Multi-part models list a dozen
        # bolts and brackets before the body, and reporting a bracket's dimensions as the
        # model's would be a confident, wrong answer about what comes off the printer.
        c["fetched"] = True
        c["local_dir"] = d
        c["parts"] = len(meshes)
        biggest = max(meshes, key=lambda p: os.path.getsize(p))
        c["measured_file"] = os.path.relpath(biggest, d)
        c["measured"] = measure(biggest)
        c["verdict"] = verdict(c["measured"])
        with open(p, "w", encoding="utf-8") as fh:
            json.dump(c, fh, indent=1, ensure_ascii=False)
            fh.write("\n")
        m = c["measured"]
        if "error" in m:
            print("  %-30s fetched, unmeasurable: %s" % (sid[:30], m["error"][:50]))
        else:
            print("  %-30s %s  %s  %d faces%s"
                  % (sid[:30], " x ".join("%.0f" % x for x in m["mm"]) + " mm",
                     "watertight" if m["watertight"] else "NOT watertight",
                     m["faces"],
                     "" if m["components"] == 1 else "  %d parts" % m["components"]))
    return bool(got)


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("sources")
    p = sub.add_parser("index"); p.add_argument("source", choices=sorted(SOURCES))
    p.add_argument("--limit", type=int)
    p = sub.add_parser("list"); p.add_argument("--fetched", action="store_true")
    p = sub.add_parser("fetch"); p.add_argument("id", nargs="?")
    p.add_argument("--all", action="store_true"); p.add_argument("--limit", type=int, default=10)
    p = sub.add_parser("check"); p.add_argument("id")
    sub.add_parser("remeasure")
    sub.add_parser("reverdict")
    sub.add_parser("images")
    a = ap.parse_args()

    if a.cmd == "sources":
        for k, s in SOURCES.items():
            ok = {"github": "indexable here", "needs_key": "needs an API key",
                  "none": "no usable API"}[s["api"]]
            print("\n%s  (%s)" % (s["name"], k))
            print("  licence     : %s" % s["licence"])
            print("  attribution : %s   commercial: %s"
                  % ("required" if s["attribution"] else "not required",
                     {True: "yes", False: "no", None: "per item"}[s["commercial_ok"]]))
            print("  status      : %s" % ok)
            print("  %s" % s["why"])
        return 0

    if a.cmd == "index":
        s = SOURCES[a.source]
        if s["api"] != "github":
            print("%s is listed but not indexable here: %s" % (s["name"], s["why"]))
            return 1
        n = index_nasa(a.limit)
        print("\n  %d models catalogued (metadata only - nothing downloaded)" % n)
        return 0

    if a.cmd == "list":
        cs = cards()
        if a.fetched:
            cs = [c for c in cs if c.get("fetched")]
        for c in cs:
            m = c.get("measured") or {}
            v = c.get("verdict") or {}
            size = (" x ".join("%.0f" % x for x in m["mm"]) + " mm") if m.get("mm") else ""
            print("  %-34s %-24s %-20s %s"
                  % (c["id"][:34], v.get("state", "-"), size,
                     (v.get("why") or [""])[0][:44]))
        print("\n  %d models, %d fetched" % (len(cards()),
                                             sum(1 for c in cards() if c.get("fetched"))))
        return 0

    if a.cmd == "fetch":
        if a.all:
            todo = [c["id"] for c in cards() if not c.get("fetched")][:a.limit]
            print("  fetching %d" % len(todo))
            for sid in todo:
                fetch(sid)
        elif a.id:
            fetch(a.id)
        else:
            print("  give an id, or --all --limit N")
        return 0

    if a.cmd == "images":
        # Previews only. Separate from `fetch` because fetch skips a model that is already
        # on disk - correct for meshes, but it meant adding image support to the indexer
        # downloaded nothing at all for the 105 already-fetched models. And separate from
        # `remeasure` because re-running mesh_doctor over 3.3 GB to collect some JPEGs is
        # forty minutes to do a job that takes one.
        n = 0
        for c in cards():
            d = os.path.join(FILES, c["id"])
            if not os.path.isdir(d):
                continue
            for f in c.get("images", []):
                dst = os.path.join(d, f["name"])
                if os.path.exists(dst):
                    continue
                try:
                    with open(dst, "wb") as fh:
                        fh.write(_get(f["url"]))
                    n += 1
                except Exception as e:
                    print("  %-30s %s" % (c["id"][:30], str(e)[:50]))
        print("  %d preview images downloaded" % n)
        return 0

    if a.cmd == "reverdict":
        # verdict() is a pure function of the stored measurement, so re-judging costs
        # nothing and does not need the meshes. Only `remeasure` re-runs mesh_doctor.
        n = 0
        for c in cards():
            if not c.get("measured"):
                continue
            c["verdict"] = verdict(c["measured"])
            with open(os.path.join(CARDS, c["id"] + ".json"), "w", encoding="utf-8") as f:
                json.dump(c, f, indent=1, ensure_ascii=False)
                f.write("\n")
            n += 1
        print("  re-judged %d" % n)
        return 0

    if a.cmd == "remeasure":
        # Re-judge what is already on disk, without re-downloading it. fetch() skips files
        # that exist, so this is just fetch over the fetched set.
        done = [c["id"] for c in cards() if c.get("fetched")]
        print("  remeasuring %d" % len(done))
        for sid in done:
            fetch(sid)
        return 0

    if a.cmd == "check":
        c = [x for x in cards() if x["id"] == a.id]
        if not c:
            print("  no such model")
            return 1
        c = c[0]
        if not c.get("fetched"):
            print("  not fetched yet")
            return 1
        m, v = c.get("measured") or {}, c.get("verdict") or {}
        print("\n  %s\n  %s\n  licence: %s\n" % (c["name"], c["source_url"], c["licence"]))
        if m.get("mm"):
            print("  %s mm   %d faces   %d part(s)   measured from %s"
                  % (" x ".join("%.1f" % x for x in m["mm"]), m["faces"],
                     m.get("components", 1), c.get("measured_file", "?")))
        for w in v.get("why", []):
            print("  - %s" % w)
        return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
