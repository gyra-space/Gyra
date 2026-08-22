import json, re, sys

path = sys.argv[1] if len(sys.argv) > 1 else '/tmp/gyra_test/stream_raw.txt'
frames = []
for line in open(path):
    line = line.strip()
    if not line.startswith('data:'):
        continue
    payload = line[5:].strip()
    try:
        obj = json.loads(payload)
    except Exception:
        continue
    frames.append(obj.get('vis'))

print('total frames:', len(frames))
dict_types = {}
for v in frames:
    if isinstance(v, dict):
        dict_types[v.get('type')] = dict_types.get(v.get('type'), 0) + 1
print('dict frames:', dict_types)

# Identify render_name and analysis fields
def extract(v):
    if not isinstance(v, str):
        return None
    m = re.search(r'```([a-z_]+)\n([\s\S]*?)```', v)
    if not m:
        return None
    try:
        return json.loads(m.group(2))
    except Exception:
        return None

# Summary growth over time + execution node outputs
print('--- summary & answer growth per frame (dedup) ---')
prev_summary = None
prev_exec = None
for i, v in enumerate(frames):
    d = extract(v)
    if d is None:
        continue
    sm = d.get('summary')
    execs = d.get('execution')
    # only print when summary changes
    if sm != prev_summary:
        prev_summary = sm
        print(f'  f{i}: summary({len(sm) if sm else 0})={sm!r}'[:160])
    # detect new/changed execution node types over time
    if execs and execs != prev_exec:
        prev_exec = execs
        nodeinfo = [(e.get('type'), e.get('title'), (e.get('output') or '')[:60]) for e in execs]
        print(f'  f{i}: exec_nodes={nodeinfo}')

print('--- render_name set ---')
names = set()
for v in frames:
    d = extract(v)
    if d:
        names.add(d.get('render_name'))
print(names)