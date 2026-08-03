import json

p = '/home/k4shix/ComfyUI/user/__manager/cache/1514988643_custom-node-list.json'
d = json.load(open(p))
nodes = d['custom_nodes'] if isinstance(d, dict) else d
print('catalog size:', len(nodes))
terms = ['tts', 'text-to-speech', 'text to speech', 'voice', 'speech', 'vibevoice',
         'chatterbox', 'f5', 'index-tts', 'indextts', 'higgs', 'kokoro', 'audio']
seen = set()
for n in nodes:
    blob = (str(n.get('title', '')) + ' ' + str(n.get('description', '')) + ' ' +
            ' '.join(n.get('files', []))).lower()
    for t in terms:
        if t in blob:
            key = n.get('title')
            if key in seen:
                break
            seen.add(key)
            print(f"\n[{t}] {n.get('title')}")
            print('   repo:', (n.get('files') or [''])[0])
            print('   ', (n.get('description') or '')[:220])
            break
