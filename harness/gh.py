"""Minimal GitHub REST client (stdlib only). Reads the token from GITHUB_TOKEN; never logs it."""
import http.client
import json
import os
import time
import urllib.error
import urllib.request

API = os.environ.get("GITHUB_API_URL", "https://api.github.com")


def _token():
    tok = os.environ.get("GITHUB_TOKEN")
    if not tok:
        raise SystemExit("GITHUB_TOKEN is not set")
    return tok


def request(method, path, body=None, accept="application/vnd.github+json", raw=False, retries=5):
    url = path if path.startswith("http") else API + path
    data = json.dumps(body).encode() if body is not None else None
    for attempt in range(retries):
        req = urllib.request.Request(url, data=data, method=method)
        req.add_header("Authorization", "Bearer " + _token())
        req.add_header("Accept", accept)
        req.add_header("X-GitHub-Api-Version", "2022-11-28")
        if data is not None:
            req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                payload = resp.read()
                if raw:
                    return payload
                return json.loads(payload) if payload else None
        except urllib.error.HTTPError as e:
            if e.code in (403, 429) and e.headers.get("X-RateLimit-Remaining") == "0":
                reset = int(e.headers.get("X-RateLimit-Reset", time.time() + 60))
                time.sleep(max(5, reset - time.time() + 2))
                continue
            if e.code >= 500 and attempt < retries - 1:
                time.sleep(2 * (attempt + 1))
                continue
            raise
        except (urllib.error.URLError, TimeoutError, http.client.HTTPException, ConnectionError):
            if attempt < retries - 1:
                time.sleep(2 * (attempt + 1))
                continue
            raise


def get(path, **kw):
    return request("GET", path, **kw)


def post(path, body, **kw):
    return request("POST", path, body=body, **kw)


def paginate(path, key):
    sep = "&" if "?" in path else "?"
    page, out = 1, []
    while True:
        data = get(f"{path}{sep}per_page=100&page={page}")
        items = data[key] if key else data
        out.extend(items)
        if len(items) < 100:
            return out
        page += 1
