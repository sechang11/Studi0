import json, sys

D = '/home/k4shix/ComfyUI/venv/lib/python3.14/site-packages/comfyui_workflow_templates_json/templates/'
w = json.load(open(D + sys.argv[1] + '.json'))


def dump(nodes, links, tag=''):
    byid = {n['id']: n for n in nodes}
    for n in nodes:
        if n.get('type') == 'MarkdownNote':
            continue
        ins = [i.get('name') for i in n.get('inputs', [])] if n.get('inputs') else []
        print(f"  {n['id']:>4} {n.get('type'):<34} wv={str(n.get('widgets_values'))[:90]} in={ins}")
    print('  -- links: origin[id].slot -> target[id].input --')
    for l in links:
        if not isinstance(l, list) or len(l) < 6:
            continue
        _, src, sslot, dst, dslot, typ = l[:6]
        s = byid.get(src, {}).get('type', src)
        t = byid.get(dst, {}).get('type', dst)
        tn = byid.get(dst, {}).get('inputs', [])
        iname = tn[dslot].get('name') if isinstance(dslot, int) and dslot < len(tn) else dslot
        print(f"    {s}[{src}].{sslot} -> {t}[{dst}].{iname}  ({typ})")


print('=== TOP ===')
dump(w.get('nodes', []), w.get('links', []))
for s in w.get('definitions', {}).get('subgraphs', []):
    print(f"=== SUBGRAPH {s.get('name')} ===")
    dump(s.get('nodes', []), s.get('links', []))
