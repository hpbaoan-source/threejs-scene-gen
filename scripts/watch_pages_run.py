#!/usr/bin/env python3
"""Poll the GitHub Actions run for the pages workflow."""
import json
import sys
import time
import urllib.error
import urllib.request

REPO = "hpbaoan-source/threejs-scene-gen"
TOKEN_FILE = "/home/anhuynh/.gh_finevideo_token"
token = open(TOKEN_FILE).read().strip()


def call(url):
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode(errors="replace")[:400]


deadline = time.time() + 420
seen = None
while time.time() < deadline:
    st, runs = call(f"https://api.github.com/repos/{REPO}/actions/workflows/pages.yml/runs?per_page=3")
    if st != 200 or not isinstance(runs, dict) or not runs.get("workflow_runs"):
        print(f"[{time.strftime('%H:%M:%S')}] runs -> {st} {runs}")
        time.sleep(15)
        continue
    run = runs["workflow_runs"][0]
    key = (run["id"], run["status"], run.get("conclusion"))
    if key != seen:
        seen = key
        print(f"[{time.strftime('%H:%M:%S')}] run {run['id']} {run['status']}/{run.get('conclusion')} head={run['head_sha'][:7]} url={run['html_url']}")
    if run["status"] == "completed":
        # job breakdown
        _, jobs = call(f"https://api.github.com/repos/{REPO}/actions/runs/{run['id']}/jobs")
        if isinstance(jobs, dict):
            for j in jobs.get("jobs", []):
                print(f"  job {j['name']}: {j['status']}/{j.get('conclusion')}")
                for s in j.get("steps", []):
                    print(f"    - {s['name']}: {s.get('conclusion')}")
        # try pages info
        st2, pages = call(f"https://api.github.com/repos/{REPO}/pages")
        print("pages api ->", st2, json.dumps(pages, indent=1)[:600] if isinstance(pages, dict) else pages)
        sys.exit(0)
    time.sleep(12)

print("TIMEOUT")
sys.exit(1)
