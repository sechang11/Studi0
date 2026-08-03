import json, sys, os, re

D = '/home/k4shix/ComfyUI/venv/lib/python3.14/site-packages/comfyui_workflow_templates_json/templates/'
for name in sys.argv[1:]:
    w = json.load(open(D + name + '.json'))
    print('=====', name)

    def walk(nodes, tag=''):
        for n in nodes:
            t = n.get('type', '')
            wv = n.get('widgets_values')
            if any(k in t for k in ('Loader', 'Load', 'Checkpoint')) or 'MarkdownNote' == t:
                if t == 'MarkdownNote':
                    txt = str(wv)
                    for m in re.findall(r'models/[A-Za-z0-9_\-/\.]+', txt):
                        print('   NOTE-PATH:', m)
                else:
                    print(f'   {tag}{t}: {wv}')

    walk(w.get('nodes', []))
    for s in w.get('definitions', {}).get('subgraphs', []):
        walk(s.get('nodes', []), tag=f"[{s.get('name')}] ")
