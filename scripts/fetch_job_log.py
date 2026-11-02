#!/usr/bin/env python3
"""Download job logs: follow the S3/Azure redirect WITHOUT forwarding the GitHub token."""
import io
import json
import sys
import urllib.error
import urllib.request
import zipfile

REPO = "hpbaoan-source/threejs-scene-gen"
token = open("/home/anhuynh/.gh_finevideo_token").read().strip()
run_id = sys.argv[1] if len(sys.argv) > 1 else "41458311830"

AUTH = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def api(url, raw=False, follow=True):
    req = urllib.request.Request(url, headers=AUTH)
    opener = urllib.request.build_opener() if follow else urllib.request.build_opener(NoRedirect)
    try:
        with opener.open(req, timeout=60) as r:
            data = r.read()
            return r.status, (data if raw else json.loads(data or b"{}")), r.geturl()
    except urllib.error.HTTPError as e:
        return e.code, e.read(), e.geturl()


st, jobs, _ = api(f"https://api.github.com/repos/{REPO}/actions/runs/{run_id}/jobs")
job_ids = [j["id"] for j in jobs.get("jobs", [])]

for jid in job_ids:
    st, blob, url = api(f"https://api.github.com/repos/{REPO}/actions/jobs/{jid}/logs", raw=True, follow=False)
    if st in (301, 302, 307, 308):
        loc = blob.decode(errors="replace")[:200]
        # real Location header
        req = urllib.request.Request(f"https://api.github.com/repos/{REPO}/actions/jobs/{jid}/logs", headers=AUTH)
        try:
            urllib.request.build_opener(NoRedirect).open(req, timeout=60)
        except urllib.error.HTTPError as e:
            real = e.headers.get("Location")
        if not real:
            print("no location:", loc)
            continue
        req2 = urllib.request.Request(real, headers={"User-Agent": "curl/8"})
        with urllib.request.urlopen(req2, timeout=120) as r:
            blob = r.read()
        st = 200
    print(f"=== job {jid} -> {st} ===")
    if blob[:2] == b"PK":
        zf = zipfile.ZipFile(io.BytesIO(blob))
        for n in zf.namelist():
            txt = zf.read(n).decode(errors="replace")
            for line in txt.splitlines():
                if any(k in line for k in ("##[error", "Error:", "HttpError", "not accessible", "enablement", "Get Pages site", "Failed to")):
                    print(f"  {n}: {line.strip()[:400]}")
    else:
        txt = blob.decode(errors="replace")
        for line in txt.splitlines():
            if any(k in line for k in ("##[error", "Error:", "HttpError", "not accessible", "enablement", "Get Pages site", "Failed to")):
                print(f"  {line.strip()[:400]}")
