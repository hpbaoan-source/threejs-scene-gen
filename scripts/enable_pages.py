#!/usr/bin/env python3
"""Enable GitHub Pages for a repo via the REST API (token never printed)."""
import json
import sys
import urllib.error
import urllib.request

REPO = sys.argv[1] if len(sys.argv) > 1 else "hpbaoan-source/threejs-scene-gen"
TOKEN_FILE = "/home/anhuynh/.gh_finevideo_token"


def call(method, url, payload=None):
    token = open(TOKEN_FILE).read().strip()
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    if data:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read() or b"{}")
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        try:
            body = json.loads(body).get("message", body)
        except Exception:
            pass
        return e.code, body


base = f"https://api.github.com/repos/{REPO}"

status, body = call("GET", f"{base}/pages")
print("GET /pages ->", status)
if status == 200:
    print(json.dumps({k: body.get(k) for k in ("url", "status", "html_url", "build_type", "source")}, indent=1))
else:
    print("  ", body)

if status != 200:
    print("\n-> tao moi Pages (branch=main, path=/docs)")
    st, bd = call(
        "POST",
        f"{base}/pages",
        {"source": {"branch": "main", "path": "/docs"}},
    )
    print("POST /pages ->", st)
    print(json.dumps(bd, indent=1) if isinstance(bd, dict) else bd)
else:
    print("\n-> Pages da ton tai, dung nguyen config (branch/path)")
