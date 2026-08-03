#!/usr/bin/env python3
"""Run any domain from its descriptor, and record the recipe.

    python3 studio/_tools/domain_gen.py voice --set text="Not this year." --set voice=vex
    python3 studio/_tools/domain_gen.py music --set cue=triumphant_build
    python3 studio/_tools/domain_gen.py sfx   --set preset=impact_hit
    python3 studio/_tools/domain_gen.py image --set subject="a wet empty terrace" --set look=noir

    python3 studio/_tools/domain_gen.py voice --vary voice     # a card: every voice, one line
    python3 studio/_tools/domain_gen.py sfx   --vary preset    # every sfx preset

ONE RUNNER, NOT FIVE

Voice, music, sfx, image and mesh differ in exactly three ways: which workflow runs, which
node inputs the fields map to, and what comes out. All three live in
studio/domains/<id>.json, so adding a sixth domain is a JSON file rather than code.

--vary is what builds a capability card. It holds every field still and steps one library
through all its values, which is the only way a comparison means anything. This project
has made the opposite mistake twice: 133 of 134 image cards vary composition between
options because changing any clause re-rolls conditioning, and the first camera sweep was
useless because the clip's own content moved more than the camera did.

Everything lands in the same manifest the film gallery uses, so one page browses all of it
and every artifact carries the settings that made it.
"""
import argparse, json, os, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
STUDIO = os.path.dirname(HERE)
ROOT = os.path.dirname(STUDIO)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
os.environ.setdefault("COMFY_HOST", "127.0.0.1:8188")

from comfy import run, set_path                       # noqa: E402
from epic import load_wf, ensure_local, HOST          # noqa: E402

DOMAINS = os.path.join(STUDIO, "domains")
OUTDIR = os.path.join(STUDIO, "samples", "domains")
MANIFEST = os.path.join(STUDIO, "gallery", "manifest.jsonl")
SEED = 7311


def sh(*a):
    return subprocess.run(a, capture_output=True, text=True)


def load_lib(name):
    d = os.path.join(STUDIO, name)
    out = {}
    if os.path.isdir(d):
        for fn in sorted(os.listdir(d)):
            if fn.endswith(".json"):
                try:
                    out[fn[:-5]] = json.load(open(os.path.join(d, fn), encoding="utf-8"))
                except Exception:
                    pass
    return out


def seen():
    if not os.path.exists(MANIFEST):
        return set()
    s = set()
    for line in open(MANIFEST, encoding="utf-8"):
        try:
            s.add(json.loads(line)["id"])
        except Exception:
            pass
    return s


def resolve(dom, sets):
    """Field values, after spreading any chosen library preset into the fields it fills.

    A preset spreads FIRST and an explicit --set overrides it, so picking a cue and then
    changing its bpm does what you expect.
    """
    vals = {}
    for f in dom["fields"]:
        if "default" in f:
            vals[f["key"]] = f["default"]
    for f in dom["fields"]:
        k = f["key"]
        if k in sets and f.get("spreads"):
            card = load_lib(f["library"]).get(sets[k], {})
            for target, source in f["spreads"].items():
                if card.get(source) is not None:
                    vals[target] = card[source]
        if k in sets:
            vals[k] = sets[k]
    for k, v in (dom.get("defaults") or {}).items():
        vals.setdefault(k, v)
    return vals


def build(dom, vals):
    """Map resolved values onto the workflow's real node inputs."""
    wf_name = dom["workflow"]
    alt = dom.get("alt_workflow")
    if alt and vals.get("engine") == alt.get("engine"):
        wf_name = alt["workflow"]
    wf = load_wf(wf_name)
    nodes = dom["nodes"]

    for key, path in nodes.items():
        if key == "prefix":
            continue
        v = vals.get(key)
        # a library field stores an id; the workflow wants the card's real value
        f = next((x for x in dom["fields"] if x["key"] == key), None)
        if f and f.get("type") == "library" and f.get("value_field") and v is not None:
            v = load_lib(f["library"]).get(v, {}).get(f["value_field"], v)
        if v is None:
            continue
        try:
            set_path(wf, path, v)
        except Exception as e:
            print("    ! could not set %s = %r (%s)" % (path, v, str(e)[:60]))
    for skey in ("seed", "seed2"):
        if skey in nodes:
            try:
                set_path(wf, nodes[skey], SEED)
            except Exception:
                pass
    # An emotion vector only exists on the engine that has one. On the other it is
    # recorded in the manifest and does nothing, which the descriptor says out loud.
    en = dom.get("emotion_nodes")
    if en and vals.get("emotion") and vals.get("engine") == "indextts2":
        card = load_lib("emotions").get(vals["emotion"], {})
        for dim in en["dims"]:
            try:
                set_path(wf, en["prefix"] + dim, float(card.get(dim.lower(), 0)))
            except Exception:
                pass
    return wf, wf_name


def generate(dom, vals, rid, dry=False):
    if dry:
        print("  would generate", rid)
        return None
    wf, wf_name = build(dom, vals)
    try:
        set_path(wf, dom["nodes"]["prefix"], f"claude-generated/studio_domains/{rid}")
    except Exception:
        pass
    _, outs = run(HOST, wf, quiet=True)
    if not outs:
        return None
    ext = os.path.splitext(outs[0])[1] or ".bin"
    os.makedirs(OUTDIR, exist_ok=True)
    dst = os.path.join(OUTDIR, rid + ext)
    local = ensure_local(outs[0], dst, required=False)
    if not local or not os.path.exists(dst):
        return None
    return {
        "id": rid,
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "domain": dom["id"],
        "domain_name": dom["name"],
        "output": dom["output"],
        "demonstrates": {"variable": vals.get("_vary", "-"),
                         "value": vals.get(vals.get("_vary", ""), "-")},
        "vars": {k: v for k, v in vals.items() if not k.startswith("_")},
        "workflow": wf_name,
        "seed": SEED,
        "file": f"/samples/domains/{rid}{ext}",
        "bytes": os.path.getsize(dst),
        "note": dom.get("note", ""),
        "warning": dom.get("warning", ""),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("domain")
    ap.add_argument("--set", action="append", default=[], metavar="k=v")
    ap.add_argument("--vary", help="step one library field through every value")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()

    p = os.path.join(DOMAINS, a.domain + ".json")
    if not os.path.exists(p):
        have = sorted(f[:-5] for f in os.listdir(DOMAINS) if f.endswith(".json"))
        raise SystemExit(f"unknown domain {a.domain!r}\n  have: {', '.join(have)}")
    dom = json.load(open(p, encoding="utf-8"))

    sets = {}
    for s in a.set:
        if "=" not in s:
            raise SystemExit(f"--set wants k=v, got {s!r}")
        k, _, v = s.partition("=")
        sets[k.strip()] = v

    if dom.get("warning"):
        print("  !! %s\n" % dom["warning"])

    done, made, failed = seen(), 0, 0
    t0 = time.time()

    if a.vary:
        f = next((x for x in dom["fields"] if x["key"] == a.vary), None)
        if not f or f.get("type") != "library":
            raise SystemExit(f"cannot vary {a.vary!r}; library fields are: " +
                             ", ".join(x["key"] for x in dom["fields"]
                                       if x.get("type") == "library"))
        lib = load_lib(f["library"])
        # never demonstrate something the library itself says not to use
        vals_list = [k for k, c in sorted(lib.items())
                     if c.get("status") not in ("blocked",)]
        skipped = len(lib) - len(vals_list)
        if skipped:
            print("  (%d entries skipped: status blocked)" % skipped)
        for val in vals_list:
            vals = resolve(dom, dict(sets, **{a.vary: val}))
            vals["_vary"] = a.vary
            rid = f"{dom['id']}__{a.vary}-{val}"
            if rid in done:
                continue
            rec = generate(dom, vals, rid, a.dry)
            if not rec:
                if not a.dry:
                    failed += 1
                continue
            with open(MANIFEST, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
            made += 1
            print("  %-46s %6.1f KB" % (rid, rec["bytes"] / 1024), flush=True)
            if a.limit and made >= a.limit:
                break
    else:
        vals = resolve(dom, sets)
        rid = f"{dom['id']}__{int(time.time())}"
        rec = generate(dom, vals, rid, a.dry)
        if rec:
            with open(MANIFEST, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
            made = 1
            print("  %s -> %s (%.1f KB)" % (rid, rec["file"], rec["bytes"] / 1024))
        elif not a.dry:
            failed = 1

    print("\n%d generated, %d failed, %.1fs" % (made, failed, time.time() - t0))


if __name__ == "__main__":
    main()
