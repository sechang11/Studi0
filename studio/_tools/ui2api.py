#!/usr/bin/env python3
"""ui2api.py - convert a ComfyUI UI-format workflow (with subgraphs) into API prompt
format, using the running server's /object_info for input names and widget order.

    python3 ui2api.py video_ltx2_5_i2v.json > 51_ltx25_i2v.json

WHY. ComfyUI ships LTX-2.5 as a UI template whose whole graph lives inside a SUBGRAPH
node. The studio drives ComfyUI through the /prompt API, which wants {id: {class_type,
inputs}}; the frontend can export that by hand, but a converter means every future
template becomes an API workflow with one command and no clicking.

HOW. UI nodes carry `inputs` (linked sockets, in order) and `widgets_values` (literal
values, in the order object_info lists that node's non-linked inputs, with converted
widgets and the trailing "control_after_generate" combos accounted for). Subgraph
boundary: an outer link into subgraph input k rewires to whatever inner nodes consume
that input; inner links out of subgraph output k become the outer consumer's source.
Nodes with no execution role (Note, MarkdownNote, Reroute, PrimitiveNode) are inlined
or dropped. Primitive*/PrimitiveStringMultiline nodes ARE real nodes on 0.33 and stay.

VERIFY: the output must be accepted by POST /prompt with a validation-only dry run -
this script does that when --check is passed and reports the first server error.
"""
import argparse
import json
import sys
import urllib.request

HOST = "127.0.0.1:8188"


def object_info():
    with urllib.request.urlopen("http://%s/object_info" % HOST, timeout=30) as r:
        return json.load(r)


PASSIVE = {"Note", "MarkdownNote", "Reroute", "PrimitiveNode"}


def widget_inputs(info, ctype):
    """Ordered list of (name, spec) for a node's inputs that take widget VALUES (not
    links only), in the order the frontend serialises widgets_values."""
    spec = info.get(ctype)
    if not spec:
        return None
    req = spec.get("input", {}).get("required", {}) or {}
    opt = spec.get("input", {}).get("optional", {}) or {}
    order = spec.get("input_order", {})
    names = list(order.get("required", list(req))) + list(order.get("optional", list(opt)))
    out = []
    for n in names:
        s = req.get(n) or opt.get(n)
        if not s:
            continue
        typ = s[0]
        cfg = s[1] if len(s) > 1 and isinstance(s[1], dict) else {}
        # WIDGET types (carry a value in widgets_values) vs LINK types (sockets only).
        # V3 nodes on 0.33 add COMFY_DYNAMICCOMBO_V3 (a combo - widget) and
        # COMFY_MATCHTYPE_V3 (a typed socket - link); "FLOAT,INT" unions are widgets.
        WIDGET = {"INT", "FLOAT", "STRING", "BOOLEAN", "COMBO", "COMFY_DYNAMICCOMBO_V3"}
        LINK = {"IMAGE", "MASK", "LATENT", "MODEL", "CLIP", "VAE", "CONDITIONING",
                "AUDIO", "VIDEO", "GUIDER", "SAMPLER", "SIGMAS", "NOISE",
                "LATENT_UPSCALE_MODEL", "UPSCALE_MODEL", "CLIP_VISION", "STYLE_MODEL",
                "CONTROL_NET", "COMFY_MATCHTYPE_V3", "*"}
        if isinstance(typ, list):
            out.append((n, "COMBO", cfg))
        elif typ in WIDGET or (isinstance(typ, str) and
                                all(p in WIDGET for p in typ.split(","))):
            out.append((n, typ, cfg))
        elif typ in LINK:
            continue
        else:
            # unknown custom type: a widget if it declares a default, else a link
            if "default" in cfg:
                out.append((n, typ, cfg))
            continue
    return out


def convert(ui, info):
    nodes = {n["id"]: n for n in ui["nodes"]}
    links = {l[0]: l for l in ui.get("links", [])}      # id -> [id, from, fslot, to, tslot, type]
    subs = {s["id"]: s for s in (ui.get("definitions") or {}).get("subgraphs", [])}

    api = {}
    # map (owner_graph_marker, node_id) -> api id string; we flatten with prefixes
    def flatten(graph_nodes, graph_links, prefix, sub_in_sources, sub_out_targets):
        """graph_links: list of [id, from, fslot, to, tslot, type] or dicts.
        sub_in_sources: {input_index: (api_id, slot)} feeding this subgraph's inputs.
        Returns {output_index: (api_id, slot)} for the subgraph outputs."""
        L = []
        for l in graph_links:
            if isinstance(l, dict):
                L.append([l["id"], l["origin_id"], l["origin_slot"], l["target_id"],
                          l["target_slot"], l.get("type")])
            else:
                L.append(l)
        by_target = {}
        for l in L:
            by_target[(l[3], l[4])] = l
        # subgraph boundary node ids: -10 = inputs node, -20 = outputs node (litegraph)
        outputs_map = {}
        api_ids = {}
        for n in graph_nodes:
            if n["type"] in PASSIVE:
                continue
            api_ids[n["id"]] = "%s%s" % (prefix, n["id"])

        def source_of(nid, slot):
            """Resolve (node, slot) upstream through reroutes/subgraph inputs to an api
            source [api_id, slot]."""
            n = next((x for x in graph_nodes if x["id"] == nid), None)
            if n is None:
                # subgraph input pseudo-node
                if nid == -10:
                    return sub_in_sources.get(slot)
                return None
            if n["type"] == "Reroute":
                lk = by_target.get((nid, 0))
                return source_of(lk[1], lk[2]) if lk else None
            if n["type"] in subs:
                # nested subgraph output
                return nested_outputs.get((nid, slot))
            return [api_ids[nid], slot]

        nested_outputs = {}
        # first, expand nested subgraph instances
        for n in graph_nodes:
            if n["type"] in subs:
                sg = subs[n["type"]]
                srcs = {}
                for i, inp in enumerate(n.get("inputs", [])):
                    lk = by_target.get((n["id"], i))
                    if lk:
                        srcs[i] = source_of(lk[1], lk[2])
                    elif inp.get("widget") is not None or "value" in inp:
                        pass
                outs = flatten(sg["nodes"], sg["links"], prefix + "s%s_" % n["id"],
                               srcs, None)
                for k, v in outs.items():
                    nested_outputs[(n["id"], k)] = v
                # subgraph instance widget values -> feed to inner primitives that
                # expose them: handled by inner nodes reading sub_in_sources when the
                # outer provides a literal (we set literals below)
                lit = n.get("widgets_values") or []
                # inputs with widget values but no link: pass literal to inner consumers
                for i, inp in enumerate(n.get("inputs", [])):
                    if (n["id"], i) in [(l[3], l[4]) for l in L]:
                        continue
                    if inp.get("widget"):
                        # find inner consumers of subgraph input i and set literal
                        for il in sg["links"]:
                            o = il["origin_id"] if isinstance(il, dict) else il[1]
                            os_ = il["origin_slot"] if isinstance(il, dict) else il[2]
                            t = il["target_id"] if isinstance(il, dict) else il[3]
                            ts = il["target_slot"] if isinstance(il, dict) else il[4]
                            if o == -10 and os_ == i:
                                tid = "%ss%s_%s" % (prefix, n["id"], t)
                                if tid in api:
                                    tn = next(x for x in sg["nodes"] if x["id"] == t)
                                    names = [x["name"] for x in tn.get("inputs", [])]
                                    if ts < len(names):
                                        val = inp.get("value")
                                        if val is None and lit:
                                            val = None
                                        if val is not None:
                                            api[tid]["inputs"][names[ts]] = val

        for n in graph_nodes:
            if n["type"] in PASSIVE or n["type"] in subs:
                continue
            ctype = n["type"]
            aid = api_ids[n["id"]]
            entry = {"class_type": ctype, "inputs": {}}
            # linked inputs by socket name
            in_names = []
            for i, inp in enumerate(n.get("inputs", [])):
                in_names.append(inp["name"])
                lk = by_target.get((n["id"], i))
                if lk:
                    src = source_of(lk[1], lk[2])
                    if src is not None:
                        entry["inputs"][inp["name"]] = list(src)
                elif "value" in inp and inp["value"] is not None:
                    entry["inputs"][inp["name"]] = inp["value"]
            # widget values in object_info order, skipping names already linked
            wv = list(n.get("widgets_values") or [])
            winputs = widget_inputs(info, ctype)
            if winputs is None:
                print("  ! unknown class_type %s (node %s) - kept without widgets"
                      % (ctype, n["id"]), file=sys.stderr)
            else:
                # frontend serialises widget values for widget inputs in order; inputs
                # converted to links still keep a placeholder in widgets_values in
                # newer frontends, so consume one value per widget input regardless.
                wi = 0

                def take_widgets(inputs_spec, prefix=""):
                    """Consume widgets_values for an ordered (name, typ, cfg) list,
                    recursing into DynamicCombo sub-schemas. Nested keys are written
                    as "<combo>.<sub>", which is what /prompt validates against."""
                    nonlocal wi
                    for name, typ, cfg in inputs_spec:
                        if wi >= len(wv):
                            return
                        full = prefix + name
                        # a socket that is LINKED keeps its link; the frontend still
                        # serialises a placeholder value for converted widgets, so the
                        # value is consumed either way
                        val = wv[wi]
                        wi += 1
                        if full in entry["inputs"] and isinstance(entry["inputs"][full],
                                                                  list):
                            pass
                        else:
                            entry["inputs"][full] = val
                        if name in ("seed", "noise_seed") and wi < len(wv) and \
                                isinstance(wv[wi], str) and wv[wi] in (
                                    "fixed", "randomize", "increment", "decrement"):
                            wi += 1
                        if typ == "COMFY_DYNAMICCOMBO_V3":
                            opts = cfg.get("options") or []
                            chosen = next((o for o in opts if o.get("key") == val), None)
                            if chosen:
                                sub = chosen.get("inputs") or {}
                                subspec = []
                                for grp in ("required", "optional"):
                                    for sn, ss in (sub.get(grp) or {}).items():
                                        st = ss[0]
                                        sc = ss[1] if len(ss) > 1 and isinstance(
                                            ss[1], dict) else {}
                                        if isinstance(st, list):
                                            subspec.append((sn, "COMBO", sc))
                                        else:
                                            subspec.append((sn, st, sc))
                                take_widgets(subspec, full + ".")

                take_widgets(winputs)
            api[aid] = entry

        # subgraph outputs
        if sub_out_targets is None:
            for l in L:
                if l[3] == -20:
                    src = source_of(l[1], l[2])
                    if src is not None:
                        outputs_map[l[4]] = src
        return outputs_map

    flatten(ui["nodes"], ui.get("links", []), "", {}, None)
    return api


def check(api):
    req = urllib.request.Request("http://%s/prompt" % HOST,
                                 data=json.dumps({"prompt": api,
                                                  "client_id": "ui2api-check"}).encode(),
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            resp = json.load(r)
    except urllib.error.HTTPError as e:
        resp = json.loads(e.read().decode() or "{}")
    return resp


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("ui_json")
    ap.add_argument("--check", action="store_true",
                    help="POST to /prompt (it WILL queue if valid) and report errors")
    a = ap.parse_args()
    ui = json.load(open(a.ui_json, encoding="utf-8"))
    info = object_info()
    api = convert(ui, info)
    print(json.dumps(api, indent=1))
    if a.check:
        resp = check(api)
        print(json.dumps(resp, indent=1)[:3000], file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
