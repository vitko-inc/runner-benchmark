"""Minimal GitHub REST client (stdlib only). Reads the token from GITHUB_TOKEN, or runs
GITHUB_TOKEN_CMD to get one (refreshed every 10 minutes, and at once after an HTTP 401); never logs it."""
import http.client
import json
import os
import subprocess
import threading
import time
import urllib.error
import urllib.request

API = os.environ.get("GITHUB_API_URL", "https://api.github.com")


_CACHE = {"token": None, "at": 0.0}
_LOCK = threading.Lock()


def _token():
    """GITHUB_TOKEN, or the output of GITHUB_TOKEN_CMD (for short-lived tokens such as a GitHub
    App installation token), re-run every 20 minutes so long sessions keep a valid token."""
    cmd = os.environ.get("GITHUB_TOKEN_CMD")
    if cmd:
        with _LOCK:
            if not _CACHE["token"] or time.time() - _CACHE["at"] > 600:
                out = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60)
                tok = out.stdout.strip()
                if out.returncode != 0 or not tok:
                    raise SystemExit("GITHUB_TOKEN_CMD failed")
                _CACHE.update(token=tok, at=time.time())
            return _CACHE["token"]
    tok = os.environ.get("GITHUB_TOKEN")
    if not tok:
        raise SystemExit("GITHUB_TOKEN (or GITHUB_TOKEN_CMD) is not set")
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
            if e.code == 401 and os.environ.get("GITHUB_TOKEN_CMD"):
                # A short-lived token expired before its scheduled refresh: the next request
                # (this retry, or the caller's) fetches a new one.
                with _LOCK:
                    _CACHE["token"] = None
                if attempt < retries - 1:
                    continue
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


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def get_log(path):
    """Fetch a job log: the API answers with a redirect to a signed URL, which must be fetched
    without the Authorization header."""
    req = urllib.request.Request(API + path, method="GET")
    req.add_header("Authorization", "Bearer " + _token())
    req.add_header("Accept", "application/vnd.github+json")
    opener = urllib.request.build_opener(_NoRedirect)
    try:
        with opener.open(req, timeout=60) as resp:
            return resp.read()
    except urllib.error.HTTPError as e:
        if e.code in (301, 302, 303, 307, 308) and e.headers.get("Location"):
            with urllib.request.urlopen(e.headers["Location"], timeout=120) as resp:
                return resp.read()
        raise
