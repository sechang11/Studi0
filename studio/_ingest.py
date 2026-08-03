#!/usr/bin/env python3
"""One-off: ingest the variable-census workflow result into studio/variables.json."""
import collections, io, json, os, sys

src = sys.argv[1]
raw = io.open(src, encoding="utf-8", errors="replace").read()

start = raw.find('{"count"')
if start < 0:
    start = raw.find('"variables"')
    start = raw.rfind("{", 0, start)

dec = json.JSONDecoder()
obj = None
try:
    obj, _ = dec.raw_decode(raw[start:])
except ValueError:
    # result was truncated in the notification; recover objects one at a time
    obj = None

if obj and obj.get("variables"):
    V = obj["variables"]
else:
    V = []
    i = raw.find('{"name"', start if start > 0 else 0)
    while i >= 0:
        try:
            o, n = dec.raw_decode(raw[i:])
            if isinstance(o, dict) and "name" in o and "level" in o:
                V.append(o)
            i = raw.find('{"name"', i + max(n, 1))
        except ValueError:
            i = raw.find('{"name"', i + 1)

seen, out = set(), []
for v in V:
    if v.get("name") in seen:
        continue
    seen.add(v["name"])
    out.append({k: v.get(k, "") for k in
                ("name", "level", "type", "default", "why", "status", "fallback")})

here = os.path.dirname(os.path.abspath(__file__))
io.open(f"{here}/variables.json", "w", encoding="utf-8").write(
    json.dumps(out, indent=1, ensure_ascii=False) + "\n")

groups = collections.OrderedDict()
for v in out:
    groups.setdefault(v["name"].split(".")[0], []).append(v)
st = collections.Counter(v["status"] for v in out)
print(f"{len(out)} variables, {len(groups)} namespaces, status={dict(st)}")
for k, items in sorted(groups.items(), key=lambda x: -len(x[1])):
    print(f"  {k:16}{len(items):4}")
