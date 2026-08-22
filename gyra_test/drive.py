import json, sys, time, urllib.request, urllib.parse

def load_cookie():
    vals = []
    for line in open('/tmp/gj.txt'):
        line = line.rstrip('\n')
        if not line.strip():
            continue
        parts = line.split('\t')
        if len(parts) < 7:
            continue  # header comment lines e.g. "# Netscape HTTP Cookie File"
        # Netscape: domain ... path secure expiry name value
        vals.append(f"{parts[-2]}={parts[-1]}")
    return "; ".join(vals)
COOKIE = load_cookie()
print("COOKIE_PREFIX", COOKIE[:30])
APP_CODE = "ea7ee88386a14e5ea38edda24a05c1fb"
WORKSPACE_ID = 2
HOST = "127.0.0.1"; PORT = 8888

def new_dialogue():
    body = {"app_code": APP_CODE, "workspace_id": WORKSPACE_ID, "user_code": "admin", "user_name": "admin"}
    req = urllib.request.Request(f"http://{HOST}:{PORT}/api/v1/chat/dialogue/new?app_code={APP_CODE}&workspace_id={WORKSPACE_ID}", data=json.dumps(body).encode(), method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Cookie", COOKIE)
    req.add_header("X-User-ID", "admin")
    with urllib.request.urlopen(req, timeout=60) as resp:
        j = json.loads(resp.read().decode('utf-8','replace'))
    print("[new_dialogue]", json.dumps(j, ensure_ascii=False)[:600])
    conv = j.get("data") or j
    return conv.get("conv_uid") or conv.get("id") or conv.get("conv_id")

conv_uid = new_dialogue()
print("CONV_UID", conv_uid)

prompt = sys.argv[1] if len(sys.argv) > 1 else "请打开 https://example.com 并截图"
workspace_id = sys.argv[2] if len(sys.argv) > 2 else str(WORKSPACE_ID)

body = {
    "app_code": APP_CODE,
    "conv_uid": conv_uid,
    "user_input": prompt,
    "ext_info": {"incremental": True, "workspace_id": int(workspace_id)},
    "incremental": True,
    "work_mode": "simple",
    "temperature": 0.5,
    "max_new_tokens": 4096,
}
pyload = json.dumps(body).encode()
hreq = urllib.request.Request(f"http://{HOST}:{PORT}/api/v1/chat/completions", data=pyload, method="POST")
hreq.add_header("Content-Type", "application/json")
hreq.add_header("Cookie", COOKIE)
hreq.add_header("X-User-ID", "admin")

out_incr = open('/tmp/gyra_test/incr_frames.jsonl','w')
out_raw = open('/tmp/gyra_test/stream_raw.txt','w')
frame_count = 0
print("=== streaming... ===", flush=True)
with urllib.request.urlopen(hreq, timeout=600) as resp:
    for raw in resp:
        line = raw.decode('utf-8','replace')
        out_raw.write(line)
        out_raw.flush()
        for part in line.split("\n"):
            part = part.strip()
            if part.startswith("data: "):
                part = part[6:]
            if not part:
                continue
            try:
                obj = json.loads(part)
            except Exception:
                continue
            vis = obj.get("vis")
            if isinstance(vis, str):
                frame_count += 1
                out_incr.write(json.dumps({"i": frame_count, "vis": vis}, ensure_ascii=False) + "\n")
            elif isinstance(vis, dict):
                frame_count += 1
                out_incr.write(json.dumps({"i": frame_count, "vis": vis}, ensure_ascii=False) + "\n")
out_incr.close()
print("=== stream complete, frames:", frame_count, "===")