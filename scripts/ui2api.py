#!/usr/bin/env python3
"""scripts/ui2api.py - turn a ComfyUI UI workflow into a flat API graph, subgraphs and all.

WHY THIS EXISTS. Every good template ComfyUI ships now hides its actual pipeline inside a
SUBGRAPH. H3 cost a night of hand-transcription for exactly that, and LTX-2.5 hides 47
nodes the same way - a two-stage sampler with a latent upscaler between the passes, which
nobody should retype. This converts any of them, so the whole shipped template library
becomes drivable from the API.

THE FOUR THINGS THAT MAKE IT NON-TRIVIAL:

  TWO LINK FORMATS. Top-level links are arrays [id, from, fromslot, to, toslot, type];
  links inside a subgraph definition are dicts. Both are normalised here.

  THE SUBGRAPH BOUNDARY IS SIGNED. Inside a definition, `origin_id: -10` means "this comes
  from the subgraph's input slot N" and `target_id: -20` means "this leaves by output slot
  N". Inlining means rewriting -10 to whatever the parent fed in, and repointing every
  parent consumer of the instance's output to the real internal producer.

  WIDGETS ARE POSITIONAL. The UI stores `widgets_values` as a bare array; the API needs
  names. They come from /object_info in schema order - and an INT with
  `control_after_generate` silently eats a SECOND array entry for the control itself, which
  is how a seed ends up one slot out and every widget after it shifts by one.

  MODE 4 IS A REAL BYPASS. In the UI it means the node is skipped and its input is passed
  through. Transcribed as an ordinary node it becomes mandatory - this project has already
  lost a night to that. Bypassed and muted nodes are dropped here and their links bridged.
"""
import argparse
import io
import json
import os
import urllib.request

OI_URL = "http://127.0.0.1:8188/object_info"
# ComfyUI now encodes a dropdown as ["COMBO", {...options}] rather than a bare list of
# choices. Missing that skips every dropdown, and because widgets_values is POSITIONAL
# each skipped dropdown shifts every widget after it by one - ResolutionSelector came
# out with the aspect string sitting in the megapixels field.
WIDGETISH = ("INT", "FLOAT", "STRING", "BOOLEAN", "COMBO", "COMFY_DYNAMICCOMBO_V3")
NOT_WIDGET = ("COMFY_AUTOGROW_V3",)   # a growable set of LINKS, not a widget slot
SKIP = ("MarkdownNote", "Note", "PreviewAny", "PreviewImage", "PrimitiveNode")

SG_IN, SG_OUT = -10, -20


def object_info(cache="/tmp/oi.json"):
    if os.path.exists(cache) and os.path.getsize(cache) > 10000:
        return json.load(io.open(cache, encoding="utf-8"))
    d = json.loads(urllib.request.urlopen(OI_URL, timeout=90).read().decode())
    io.open(cache, "w", encoding="utf-8").write(json.dumps(d))
    return d


def norm_links(ls):
    out = []
    for l in ls or []:
        if isinstance(l, dict):
            out.append({"id": l["id"], "o": l["origin_id"], "os": l["origin_slot"],
                        "t": l["target_id"], "ts": l["target_slot"]})
        else:
            out.append({"id": l[0], "o": l[1], "os": l[2], "t": l[3], "ts": l[4]})
    return out


def _is_widget(t):
    """A union type is written as one string: "FLOAT,INT" is still a widget."""
    if isinstance(t, list):
        return True
    if not isinstance(t, str):
        return False
    if t in NOT_WIDGET:
        return False
    return any(part in WIDGETISH for part in t.split(","))


def widget_slots(oi, ctype):
    """(name, type, eats_an_extra_control_entry) for every input with a widget slot."""
    spec = oi.get(ctype)
    if not spec:
        return None
    out = []
    for sec in ("required", "optional"):
        for name, s in (spec.get("input", {}).get(sec, {}) or {}).items():
            t = s[0]
            opts = s[1] if len(s) > 1 and isinstance(s[1], dict) else {}
            if _is_widget(t):
                out.append((name, t, bool(opts.get("control_after_generate"))))
    return out


def _accepts(t, v):
    if isinstance(t, list) or t == "COMBO" or t == "COMFY_DYNAMICCOMBO_V3":
        return isinstance(v, str)
    parts = t.split(",") if isinstance(t, str) else []
    if isinstance(v, bool):
        return "BOOLEAN" in parts
    if isinstance(v, (int, float)):
        return "INT" in parts or "FLOAT" in parts
    if isinstance(v, str):
        return "STRING" in parts or "COMBO" in parts
    return False


def map_widgets(oi, ctype, values):
    slots = widget_slots(oi, ctype)
    if not slots or not values:
        return {}
    # Fast path: the array lines up with the schema one for one.
    res, i, ok = {}, 0, True
    for name, t, ctrl in slots:
        if i >= len(values):
            break
        v = values[i]
        i += 1
        if ctrl:
            i += 1
        if isinstance(v, (dict, list)):
            continue
        if not _accepts(t, v):
            ok = False
            break
        res[name] = v
    if ok and i >= len(values):
        return res
    # Fallback: the counts disagree. That happens when a COMFY_DYNAMICCOMBO_V3 widget
    # carries dependent values of its own in the slots straight after it -
    # ResizeImageMaskNode stores ["scale longer dimension", 1536, "lanczos"] against two
    # declared widgets, because picking that option adds a `size` widget between them.
    res, filled = {}, set()
    dyn = None                       # (option_inputs, [names left to fill])
    for v in values:
        if isinstance(v, (dict, list)):
            continue
        if dyn and dyn[1] and _accepts(dyn[0][1][dyn[1][0]][0], v):
            res["%s.%s" % (dyn[0][0], dyn[1][0])] = v
            dyn[1].pop(0)
            continue
        hit = None
        for si, (name, ty, _c) in enumerate(slots):
            if si in filled or not _accepts(ty, v):
                continue
            hit = si
            break
        if hit is None:
            continue
        name, ty, _c = slots[hit]
        res[name] = v
        filled.add(hit)
        dyn = None
        if ty == "COMFY_DYNAMICCOMBO_V3":
            spec = oi.get(ctype, {}).get("input", {})
            for sec in ("required", "optional"):
                s = (spec.get(sec, {}) or {}).get(name)
                if not s:
                    continue
                for opt in (s[1] or {}).get("options", []):
                    if opt.get("key") == v:
                        oin = (opt.get("inputs", {}).get("required", {}) or {})
                        dyn = ((name, oin), list(oin.keys()))
    return res


class Flat(object):
    def __init__(self, ui):
        self.defs = {sg["id"]: sg
                     for sg in ui.get("definitions", {}).get("subgraphs", [])}
        self.nodes = {}          # id -> node dict
        self.links = []          # normalised, ids already unique
        self.n = 0
        self._expand(ui.get("nodes", []), norm_links(ui.get("links", [])), "")

    def _expand(self, nodes, links, prefix):
        pid = lambda x: "%s%s" % (prefix, x)
        local = []
        for l in links:
            m = dict(l)
            m["id"] = pid(l["id"])
            m["o"] = l["o"] if l["o"] in (SG_IN, SG_OUT) else pid(l["o"])
            m["t"] = l["t"] if l["t"] in (SG_IN, SG_OUT) else pid(l["t"])
            local.append(m)
        self.links.extend(local)

        for nd in nodes:
            t = nd.get("type", "")
            nid = pid(nd["id"])
            if t not in self.defs:
                m = dict(nd)
                m["id"] = nid
                self.nodes[nid] = m
                continue

            sg = self.defs[t]
            self.n += 1
            inner = "%ssg%d_" % (prefix, self.n)
            self._expand(sg.get("nodes", []), norm_links(sg.get("links", [])), inner)

            # -10: an inner link that starts at the subgraph's input slot N gets its
            # origin replaced by whatever the parent connected to that slot.
            feeds = {}
            for l in self.links:
                if l["t"] == nid:
                    feeds[l["ts"]] = (l["o"], l["os"])
            for l in self.links:
                if l["o"] == SG_IN and str(l["id"]).startswith(inner):
                    src = feeds.get(l["os"])
                    if src:
                        l["o"], l["os"] = src
            # -20: whoever inside produces output slot N becomes the new source for
            # every parent link leaving the instance on that slot.
            prod = {}
            for l in self.links:
                if l["t"] == SG_OUT and str(l["id"]).startswith(inner):
                    prod[l["ts"]] = (l["o"], l["os"])
            for l in self.links:
                if l["o"] == nid:
                    src = prod.get(l["os"])
                    if src:
                        l["o"], l["os"] = src

    def link(self, lid):
        for l in self.links:
            if str(l["id"]) == str(lid):
                return l
        return None


def to_api(ui, oi):
    f = Flat(ui)
    dead = {k for k, n in f.nodes.items()
            if n.get("mode") in (2, 4) or n.get("type") in SKIP or n.get("type") not in oi}

    def resolve(nid, slot, guard=0):
        if nid in (SG_IN, SG_OUT) or guard > 32:
            return None
        if nid not in dead:
            return [str(nid), slot]
        n = f.nodes.get(nid)
        if not n:
            return None
        # a bypassed node passes its first type-matching input straight through
        for d in (n.get("inputs") or []):
            if d.get("link") is None:
                continue
            l = f.link("%s" % d["link"]) or f.link(d["link"])
            if l:
                return resolve(l["o"], l["os"], guard + 1)
        return None

    api = {}
    for nid, n in f.nodes.items():
        if nid in dead:
            continue
        ctype = n["type"]
        ins = map_widgets(oi, ctype, n.get("widgets_values") or [])
        for l in f.links:
            if l["t"] != nid:
                continue
            decl = (n.get("inputs") or [])
            name = None
            if l["ts"] < len(decl):
                d = decl[l["ts"]]
                name = (d.get("widget") or {}).get("name") or d.get("name")
            if not name:
                continue
            r = resolve(l["o"], l["os"])
            if r:
                ins[name] = r
        api[str(nid)] = {"class_type": ctype, "inputs": ins,
                         "_meta": {"title": n.get("title") or ctype}}
    return api


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("dst")
    ap.add_argument("--comment", default="")
    a = ap.parse_args()
    oi = object_info()
    ui = json.load(io.open(a.src, encoding="utf-8"))
    api = to_api(ui, oi)
    out = {}
    if a.comment:
        out["_comment"] = a.comment
    out.update(api)
    io.open(a.dst, "w", encoding="utf-8").write(json.dumps(out, indent=2))
    real = [k for k in api]
    print("%s -> %s  (%d nodes)" % (os.path.basename(a.src), a.dst, len(real)))
    unresolved = []
    for k in real:
        spec = oi[api[k]["class_type"]].get("input", {}).get("required", {}) or {}
        for name, s in spec.items():
            t = s[0]
            if isinstance(t, list) or t in WIDGETISH or t in NOT_WIDGET:
                continue
            if name not in api[k]["inputs"]:
                unresolved.append("%s.%s(%s)" % (k, name, api[k]["class_type"]))
    if unresolved:
        print("  UNRESOLVED required links:", unresolved[:10])
    else:
        print("  all required links resolved")


if __name__ == "__main__":
    main()
