#!/usr/bin/env python3
"""Probe the Moon dropbox API to read the real leaf-app runtime config."""
import json
import urllib.error
import urllib.parse
import urllib.request

key = open("/home/anhuynh/.moon_agent_key").read().strip()
BASE = "https://moon.id.vn/api"


def call(path, params=None, method="GET"):
    url = f"{BASE}/{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"X-Agent-Key": key, "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, r.read().decode(errors="replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode(errors="replace")


st, body = call("dropbox/list")
print("GET /api/dropbox/list ->", st)
print(body[:3000])
print("=" * 60)

for probe in ("dropbox/read?path=leaf_app/run.sh", "dropbox/read?path=/home/anhuynh/botspace/leaf_app/run.sh",
              "dropbox/list?path=/home/anhuynh/botspace/leaf_app"):
    st, body = call("dropbox/read" if "read" in probe else "dropbox/list",
                    dict(probe.split("?", 1)[1].split("&")[0].split("=")))
    print(f"\n{probe} -> {st}")
    print(body[:1200])
