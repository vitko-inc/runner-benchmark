#!/usr/bin/env python3
"""Trigger guard: benchmark runs may start only by workflow_dispatch, which needs write access to
the repository. No workflow may start on push, pull_request, pull_request_target, issue_comment,
schedule, workflow_call, workflow_run or any other event, so nobody outside the project can make
a benchmark account run (or bill) anything.

  python3 harness/trigger_guard.py --local .github/workflows
      Checks a checkout. The only exception is this repository's own check workflow (scan.yml),
      which must start on push and pull_request only, run on GitHub-hosted ubuntu-latest with
      read-only permissions, and is never copied to the run repositories.

  GITHUB_TOKEN=... python3 harness/trigger_guard.py --repo owner/name [--ref main] [--settings]
      Checks a run repository through the API: every workflow file on the ref (and on the default
      branch) must be workflow_dispatch only, with no exception. --settings also checks the
      repository's lock-down settings (see harness/README or CONTRIBUTING).
Exit status is non-zero on any finding.
"""
import argparse
import base64
import glob
import os
import sys

import yaml

sys.path.insert(0, os.path.dirname(__file__))

SOURCE_CHECK = "scan.yml"


def triggers(text):
    doc = yaml.safe_load(text) or {}
    on = doc.get("on", doc.get(True))  # YAML 1.1 reads a bare `on` key as True
    if isinstance(on, str):
        return {on}, doc
    if isinstance(on, list):
        return set(on), doc
    if isinstance(on, dict):
        return set(on), doc
    return set(), doc


def check_file(name, text, allow_source_check):
    found = []
    try:
        on, doc = triggers(text)
    except yaml.YAMLError as e:
        return [f"{name}: not valid YAML ({e})"]
    if allow_source_check and os.path.basename(name) == SOURCE_CHECK:
        if on != {"push", "pull_request"}:
            found.append(f"{name}: the check workflow must start on push and pull_request only, has {sorted(on)}")
        if doc.get("permissions") != {"contents": "read"}:
            found.append(f"{name}: the check workflow must have permissions contents: read")
        for jid, job in (doc.get("jobs") or {}).items():
            if job.get("runs-on") != "ubuntu-latest":
                found.append(f"{name}: job {jid} must run on ubuntu-latest")
        return found
    if on != {"workflow_dispatch"}:
        found.append(f"{name}: must start on workflow_dispatch only, has {sorted(on) or 'nothing'}")
    return found


def local(path):
    files = sorted(glob.glob(os.path.join(path, "*.yml")) + glob.glob(os.path.join(path, "*.yaml")))
    out = []
    for f in files:
        with open(f) as fh:
            out += check_file(f, fh.read(), allow_source_check=True)
    return out, len(files)


def remote(repo, refs, settings):
    import gh
    out, n = [], 0
    for ref in refs:
        try:
            items = gh.get(f"/repos/{repo}/contents/.github/workflows?ref={ref}")
        except Exception as e:
            if "404" in str(e):
                items = []
            else:
                raise
        for it in items:
            if not it["name"].endswith((".yml", ".yaml")):
                continue
            body = gh.get(f"/repos/{repo}/contents/{it['path']}?ref={ref}")
            text = base64.b64decode(body["content"]).decode()
            out += check_file(f"{repo}@{ref}:{it['path']}", text, allow_source_check=False)
            n += 1
    if settings:
        r = gh.get(f"/repos/{repo}")
        if r.get("has_issues"):
            out.append(f"{repo}: issues are enabled")
        if r.get("has_pull_requests", True) and r.get("pull_request_creation_policy") != "collaborators_only":
            out.append(f"{repo}: pull requests are open to everyone")
        for k in ("has_wiki", "has_projects", "has_discussions"):
            if r.get(k):
                out.append(f"{repo}: {k} is on")
        ap = gh.get(f"/repos/{repo}/actions/permissions/fork-pr-contributor-approval")
        if ap.get("approval_policy") != "all_external_contributors":
            out.append(f"{repo}: fork pull request runs do not need approval for all outside contributors")
        wp = gh.get(f"/repos/{repo}/actions/permissions/workflow")
        if wp.get("default_workflow_permissions") != "read" or wp.get("can_approve_pull_request_reviews"):
            out.append(f"{repo}: the default GITHUB_TOKEN may write or approve pull requests")
    return out, n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--local")
    ap.add_argument("--repo", action="append", default=[])
    ap.add_argument("--ref", action="append", default=[])
    ap.add_argument("--settings", action="store_true")
    a = ap.parse_args()
    findings, n = [], 0
    if a.local:
        f, k = local(a.local)
        findings += f
        n += k
    for repo in a.repo:
        import gh
        default = gh.get(f"/repos/{repo}")["default_branch"]
        f, k = remote(repo, sorted(set(a.ref + [default])), a.settings)
        findings += f
        n += k
    for f in findings:
        print("TRIGGER GUARD:", f)
    print(f"trigger guard: {n} workflow files checked, {len(findings)} findings")
    sys.exit(1 if findings or n == 0 else 0)


if __name__ == "__main__":
    main()
