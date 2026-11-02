#!/usr/bin/env python3
"""Check the Moon leaf-app slot using the agent key file (never prints the key)."""
import json
import urllib.error
import urllib.request

key = open("/home/anhuynh/.moon_agent_key").read().strip()
print(f"key len: {len(key)}")

req = urllib.request.Request(
    "https://moon.id.vn/api/leaf-app-check",
    headers={"X-Agent-Key": key, "Accept": "application/json"},
)
try:
    with urllib.request.urlopen(req, timeout=30) as resp:
        body = resp.read().decode()
        print("HTTP", resp.status)
        try:
            data = json.loads(body)
            print(json.dumps(data, indent=1)[:2000])
        except Exception:
            print(body[:2000])
except urllib.error.HTTPError as e:
    print("HTTP", e.code)
    print(e.read().decode(errors="replace")[:1000])
