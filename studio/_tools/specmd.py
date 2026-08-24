#!/usr/bin/env python3
"""studio/_tools/specmd.py - shot specs in English, both directions.

The .md is what a person edits; the .json is what the checker reads. This is the only
thing that knows how to turn one into the other, so the two can never drift.

Shared by the /specs editor and by build/spec_md.py in the film repo.
"""
import json, os, re


# ── check grammar, both directions ──────────────────────────────────────────────────

def check_to_json(line):
    s = line.strip().rstrip(".")
    m = re.match(r"anchor contains\s+(.+)$", s, re.I)
    if m:
        return {"kind": "anchor_contains", "value": m.group(1).strip("`' ")}
    m = re.match(r"engine is\s+(.+)$", s, re.I)
    if m:
        return {"kind": "engine", "value": m.group(1).strip("`' ")}
    m = re.match(r"duration between\s+([\d.]+)\s+and\s+([\d.]+)$", s, re.I)
    if m:
        return {"kind": "duration_between", "min": float(m.group(1)),
                "max": float(m.group(2))}
    m = re.match(r"camrig preset is\s+(.+)$", s, re.I)
    if m:
        return {"kind": "camrig_preset", "value": m.group(1).strip("`' ")}
    m = re.match(r"provenance mentions\s+(.+)$", s, re.I)
    if m:
        return {"kind": "take_prompt_contains", "value": m.group(1).strip("`' ")}
    if re.match(r"qc is clean$", s, re.I):
        return {"kind": "qc_clean"}
    return {"kind": "UNKNOWN", "raw": s}


def check_to_md(c):
    if not c:
        return None
    k = c.get("kind")
    if k == "anchor_contains":
        return "anchor contains %s" % c["value"]
    if k == "engine":
        return "engine is %s" % c["value"]
    if k == "duration_between":
        return "duration between %s and %s" % (c["min"], c["max"])
    if k == "camrig_preset":
        return "camrig preset is %s" % c["value"]
    if k == "take_prompt_contains":
        return "provenance mentions %s" % c["value"]
    if k == "qc_clean":
        return "qc is clean"
    return c.get("raw")


def slug(title):
    return re.sub(r"[^a-z0-9]+", "_", title.lower()).strip("_")[:40]


# ── markdown -> json ────────────────────────────────────────────────────────────────

def parse_md(text):
    out = {"invariants": [], "flair": []}
    lines = text.splitlines()
    shot = title = None
    m = re.match(r"#\s+Shot\s+(\S+)\s*[-—:]*\s*(.*)$", lines[0] if lines else "")
    if m:
        shot, title = m.group(1), m.group(2).strip()
    out["shot"], out["title"] = shot, title

    section, item = None, None
    body = []

    def close():
        if item is None:
            return
        txt = "\n".join(body).strip()
        why = check = None
        keep = []
        promote = False
        for ln in txt.splitlines():
            if re.match(r"\s*WHY\s*:", ln, re.I):
                why = ln.split(":", 1)[1].strip()
            elif re.match(r"\s*CHECK\s*:", ln, re.I):
                check = check_to_json(ln.split(":", 1)[1])
            elif re.match(r"\s*MAKE PERMANENT\s*$", ln, re.I):
                promote = True
            else:
                keep.append(ln)
        rule = " ".join(x.strip() for x in keep if x.strip())
        d = {"id": slug(item), "title": item, "rule": rule}
        if why:
            d["why"] = why
        if check:
            d["check"] = check
        if section == "flair":
            d = {"id": d["id"], "title": item, "note": rule}
            if check:
                d["check"] = check
            d["promote"] = promote
        out[section].append(d)

    for ln in lines[1:]:
        h2 = re.match(r"##\s+(.+)$", ln)
        h3 = re.match(r"###\s+(.+)$", ln)
        if h2 and not h3:
            close(); item = None; body = []
            name = h2.group(1).strip().upper()
            if "MUST NEVER" in name or "INVARIANT" in name:
                section = "invariants"
            elif "CAN CHANGE" in name or "FLAIR" in name:
                section = "flair"
            elif name.startswith("WHAT HAPPENS"):
                section = "_beat"
            elif name.startswith("BUILT") or name.startswith("ENGINE"):
                section = "_build"
            else:
                section = "_other"
            continue
        if h3:
            close(); item = h3.group(1).strip(); body = []
            continue
        if section == "_beat":
            out["beat"] = (out.get("beat", "") + " " + ln.strip()).strip()
        elif section == "_build":
            if ln.strip():
                out.setdefault("build", {}).setdefault("script", "")
                out["build"]["script"] = (out["build"]["script"] + " " + ln.strip()).strip()
        elif item is not None:
            body.append(ln)
    close()
    return out


# ── json -> markdown ────────────────────────────────────────────────────────────────

def to_md(d):
    L = ["# Shot %s — %s" % (d.get("shot", "?"), d.get("title", "")), ""]
    L += ["## WHAT HAPPENS", "", d.get("beat", "").strip(), ""]
    b = d.get("build") or {}
    if b:
        L += ["## BUILT WITH", "",
              " · ".join("%s" % v for k, v in b.items() if v), ""]
    L += ["## MUST NEVER CHANGE", "",
          "*These are the promises. I do not change one without telling you first.*", ""]
    for i in d.get("invariants", []):
        L.append("### %s" % (i.get("title") or i["id"].replace("_", " ")))
        L.append(i.get("rule", ""))
        if i.get("why"):
            L.append("WHY: %s" % i["why"])
        c = check_to_md(i.get("check"))
        if c:
            L.append("CHECK: %s" % c)
        L.append("")
    L += ["## CAN CHANGE", "",
          "*Free to move. Add `MAKE PERMANENT` under any of these to promote it above.*", ""]
    for i in d.get("flair", d.get("flare", [])):
        L.append("### %s" % (i.get("title") or i["id"].replace("_", " ")))
        L.append(i.get("note", ""))
        if i.get("options"):
            for o in i["options"]:
                L.append("  - option: %s" % o)
        c = check_to_md(i.get("check"))
        if c:
            L.append("CHECK: %s" % c)
        if i.get("promote"):
            L.append("MAKE PERMANENT")
        L.append("")
    return "\n".join(L).rstrip() + "\n"




SKELETON = """# Shot {shot} — {title}

## WHAT HAPPENS

Describe the beat in a sentence or two, the way you would say it out loud.

## BUILT WITH

(script or engine, and the plate it starts from)

## MUST NEVER CHANGE

*These are the promises. They do not change without a conversation.*

### Name this promise
Write the rule as a sentence.
WHY: why it matters. This is what stops the rule being argued away later.
CHECK: anchor contains something

## CAN CHANGE

*Free to move. Add MAKE PERMANENT under any of these to promote it above.*

### Name this setting
What it currently is.
"""


def skeleton(shot, title=""):
    return SKELETON.format(shot=shot, title=title or "untitled")


def write_json(directory, shot, parsed):
    """Write the machine-readable half beside the English one, applying any
    MAKE PERMANENT promotions on the way through. Returns any checks it could not
    understand, so the editor can say so instead of failing silently."""
    p = os.path.join(directory, shot + ".json")
    old = json.load(open(p, encoding="utf-8")) if os.path.exists(p) else {}
    old.pop("flare", None)
    keep, moved = [], 0
    for it in parsed["flair"]:
        if it.pop("promote", False):
            parsed["invariants"].append(
                {"id": it["id"], "title": it.get("title"), "rule": it.get("note", ""),
                 "why": "promoted by the director", "check": it.get("check")})
            moved += 1
        else:
            keep.append(it)
    parsed["flair"] = keep
    parsed["_promoted"] = moved
    warn = [c.get("raw") for i in parsed["invariants"] + parsed["flair"]
            if (c := i.get("check")) and c.get("kind") == "UNKNOWN"]
    old.update({k: v for k, v in parsed.items() if not k.startswith("_")})
    old["shot"] = shot
    json.dump(old, open(p, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    return warn
