#!/usr/bin/env python3
"""Dispatch benchmark rounds and record every dispatched run.

Usage:
  GITHUB_TOKEN=... python3 harness/run.py --plan plans/<name>.json --targets <targets.json> \
      --out results/<set>/dispatch.jsonl [--session s1] [--dry-run]

The plan says which workloads and providers run, how many warm-up and measured rounds, and
which workloads run in which lane. The targets file (kept outside this repository) maps each
provider id to the repository where its runs happen and the runs-on label to use.

Within a round, every lane runs in parallel. A lane takes its workloads one at a time: it
dispatches the workload to every provider within a few seconds, in random order, and waits
until all of those runs have finished. Burst workloads run after the lanes, as their own step:
each provider gets N copies dispatched at once, in parallel, and the spread of those dispatch
times is recorded ("burst_dispatch" events). With "burst_groups", each group bursts after the
previous one has finished.

A target may carry a monthly minute budget, for a provider whose account has no spend cap of
its own:

  "minute_budget": {"month_limit": 4500, "ledger": "/path/outside/repo/blacksmith-minutes.json",
                    "default_estimate_min": 10}

Before each dispatch the harness reserves an estimate of the run's billed minutes (the largest
billed total seen so far for that workload, or the default) and refuses the dispatch if the
month's billed minutes plus open reservations would pass the limit; the refusal is recorded as a
"budget_skip" event. After each run finishes, its billed minutes (every job, rounded up to the
minute, from the GitHub jobs API) replace the reservation in the ledger. --usage-observed
provider=minutes raises the month's total to what the provider's own usage page shows, when
that is higher (for example minutes used outside the harness).
"""
import argparse
import datetime as dt
import json
import math
import os
import random
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(__file__))
import gh  # noqa: E402

LOCK = threading.Lock()
POLL_S = 30  # a full session stays well inside a GitHub App's 5,000 requests/hour


def now():
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load(path):
    with open(path) as f:
        return json.load(f)


def record(out, rec):
    with LOCK:
        with open(out, "a") as f:
            f.write(json.dumps(rec, sort_keys=True) + "\n")


class MinuteBudget:
    """Monthly billed-minute ledger for one provider (see the module docstring)."""

    def __init__(self, provider, cfg):
        self.provider, self.limit = provider, float(cfg["month_limit"])
        self.path, self.default = cfg["ledger"], float(cfg.get("default_estimate_min", 10))
        self.reserved = 0.0
        self.data = load(self.path) if os.path.exists(self.path) else {}

    def _month(self):
        m = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m")
        return self.data.setdefault(m, {"billed_min": 0, "observed_min": 0, "runs": {}, "max_by_workload": {}})

    def used(self):
        m = self._month()
        return max(m["billed_min"], m["observed_min"])

    def _save(self):
        tmp = self.path + ".tmp"
        with open(tmp, "w") as f:
            json.dump(self.data, f, indent=1, sort_keys=True)
        os.replace(tmp, self.path)

    def observe(self, minutes):
        with LOCK:
            m = self._month()
            m["observed_min"] = max(m["observed_min"], float(minutes))
            self._save()

    def fits(self, workload_id, n):
        with LOCK:
            est = float(self._month()["max_by_workload"].get(workload_id, self.default))
            return self.used() + self.reserved + n * est <= self.limit

    def reserve(self, workload_id):
        """Returns the reserved estimate, or None when the run would pass the month's limit."""
        with LOCK:
            est = float(self._month()["max_by_workload"].get(workload_id, self.default))
            if self.used() + self.reserved + est > self.limit:
                return None
            self.reserved += est
            return est

    def settle(self, workload_id, repo, run_id, est):
        """Replace a reservation with the run's billed minutes (each job rounded up)."""
        billed = 0
        if run_id:
            try:
                jobs = gh.paginate(f"/repos/{repo}/actions/runs/{run_id}/jobs?filter=all", "jobs")
            except Exception as e:  # keep the estimate counted rather than lose it
                print(f"[{now()}] budget: jobs lookup failed for {run_id}: {e}", file=sys.stderr)
                jobs = None
            if jobs is None:
                billed = est
            else:
                for j in jobs:
                    if j.get("started_at") and j.get("completed_at"):
                        a = dt.datetime.fromisoformat(j["started_at"].replace("Z", "+00:00"))
                        b = dt.datetime.fromisoformat(j["completed_at"].replace("Z", "+00:00"))
                        billed += max(1, math.ceil((b - a).total_seconds() / 60))
        with LOCK:
            self.reserved -= est
            m = self._month()
            key = str(run_id)
            if run_id and key in m["runs"]:
                return  # already counted
            m["billed_min"] += billed
            if run_id:
                m["runs"][key] = billed
                if billed > m["max_by_workload"].get(workload_id, 0):
                    m["max_by_workload"][workload_id] = billed
            self._save()
        print(f"[{now()}] budget {self.provider}: {self.used():.0f}/{self.limit:.0f} min this month",
              flush=True)


BUDGETS = {}


def find_run(repo, workflow, tag, since, timeout=300):
    """Find the run whose run-name is the tag (dispatch returns no id on older API versions)."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        runs = gh.get(f"/repos/{repo}/actions/workflows/{workflow}/runs?event=workflow_dispatch"
                      f"&created=>={since}&per_page=100")["workflow_runs"]
        for r in runs:
            if r.get("display_title") == tag or r.get("name") == tag:
                return r["id"]
        time.sleep(3)
    return None


def dispatch(target, workload, tag, split, dry):
    repo = target["repo"]
    label = target.get("runs_on_by_workload", {}).get(workload["id"], target["runs_on"])
    inputs = {"runs_on": label, "tag": tag}
    # Only workloads with a splittable test step have the workflow input `split`; sending it to
    # any other workflow is rejected by GitHub (HTTP 422).
    if workload.get("splittable"):
        inputs["split"] = "true" if split else "false"
    # Extra workflow inputs a provider needs (for example a Track B option), as strings.
    for k, v in target.get("inputs", {}).items():
        inputs[k] = v
    if dry:
        return {"run_id": None, "dispatched_at": now(), "dispatched_at_ms": round(time.time() * 1000)}
    since = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(seconds=30)).strftime("%Y-%m-%dT%H:%M:%SZ")
    at = now()
    at_ms = round(time.time() * 1000)
    body = {"ref": target.get("ref", "main"), "inputs": inputs, "return_run_details": True}
    path = f"/repos/{repo}/actions/workflows/{workload['workflow']}/dispatches"
    try:
        # One attempt only: a retried POST could dispatch twice. On a connection error, look the
        # run up by its tag, and dispatch again only if GitHub never created it.
        resp = gh.request("POST", path, body=body, retries=1)
    except Exception as e:
        print(f"[{now()}] dispatch error for {tag}: {e}; checking whether the run exists", file=sys.stderr)
        rid = find_run(repo, workload["workflow"], tag, since, timeout=60)
        if rid:
            return {"run_id": rid, "dispatched_at": at, "dispatched_at_ms": at_ms, "since": since}
        at, at_ms = now(), round(time.time() * 1000)  # the dispatch that counts is this one
        resp = gh.request("POST", path, body=body, retries=1)
    run_id = (resp or {}).get("workflow_run_id")
    return {"run_id": run_id, "dispatched_at": at, "dispatched_at_ms": at_ms, "since": since}


class _ActiveRuns:
    """Shared view of each repository's queued and running runs, refreshed at most every POLL_S
    seconds and shared by every lane, so the API cost of waiting does not grow with the number of
    runs in flight: two list calls per repository per refresh, plus one call to confirm each run
    that has left the lists (a run in a rarer state such as "waiting" is simply confirmed as not
    finished yet and checked again)."""

    def __init__(self):
        self.lock = threading.Lock()
        self.seen = {}  # repo -> (fetched_at, ids of queued or running runs)

    def unfinished(self, repo):
        with self.lock:
            at, ids = self.seen.get(repo, (0.0, None))
            if ids is not None and time.time() - at < POLL_S:
                return ids
            ids = set()
            for status in ("queued", "in_progress"):
                data = gh.get(f"/repos/{repo}/actions/runs?status={status}&per_page=100")
                ids |= {r["id"] for r in data.get("workflow_runs", [])}
            self.seen[repo] = (time.time(), ids)
            return ids


ACTIVE = _ActiveRuns()


def wait_all(items, timeout_s):
    """items: list of dicts with repo, run_id. Blocks until every run is completed or times out."""
    deadline = time.time() + timeout_s
    pending = {(i["repo"], i["run_id"]) for i in items if i.get("run_id")}
    while pending and time.time() < deadline:
        for repo in sorted({r for r, _ in pending}):
            try:
                active = ACTIVE.unfinished(repo)
            except Exception as e:  # transient; retry on the next poll
                print(f"[{now()}] poll error {repo}: {e}", file=sys.stderr)
                continue
            for rp, rid in [x for x in pending if x[0] == repo and x[1] not in active]:
                try:
                    if gh.get(f"/repos/{rp}/actions/runs/{rid}").get("status") == "completed":
                        pending.discard((rp, rid))
                except Exception as e:
                    print(f"[{now()}] poll error {rp} {rid}: {e}", file=sys.stderr)
        if pending:
            time.sleep(POLL_S)
    return pending


def run_group(plan, targets, workload, providers, meta, out, dry, copies=1):
    """Dispatch one workload to the providers, then wait for every run to finish.

    A single run (copies=1) goes to every provider within a few seconds, in random order. A burst
    (copies>1) goes to one provider at a time, in random order: all of that provider's copies are
    dispatched at once, in parallel, and the spread of their dispatch times is recorded as a
    "burst_dispatch" event, so it can be checked that every provider got the same tight start.
    """
    kind = "burst" if copies > 1 else "single"
    if copies > 1:
        # A burst is measured whole or not at all: drop a budgeted provider that cannot afford
        # every copy.
        for p in [p for p in providers if p in BUDGETS and not BUDGETS[p].fits(workload["id"], copies)]:
            print(f"[{now()}] BUDGET STOP {p}: burst {workload['id']} x{copies} not dispatched",
                  file=sys.stderr, flush=True)
            record(out, dict(meta, workload=workload["id"], provider=p, event="budget_skip",
                             copies=copies, used_min=BUDGETS[p].used(), limit_min=BUDGETS[p].limit))
        providers = [p for p in providers if p not in BUDGETS or BUDGETS[p].fits(workload["id"], copies)]

    def reserve(p, c, tag):
        """Budget reservation: (True, estimate) to go ahead, (False, None) when over budget."""
        if p not in BUDGETS:
            return True, None
        est = BUDGETS[p].reserve(workload["id"])
        if est is None:
            print(f"[{now()}] BUDGET STOP {p}: {tag} not dispatched "
                  f"({BUDGETS[p].used():.0f}/{BUDGETS[p].limit:.0f} min used this month)",
                  file=sys.stderr, flush=True)
            record(out, dict(meta, workload=workload["id"], provider=p, copy=c, tag=tag,
                             event="budget_skip", used_min=BUDGETS[p].used(), limit_min=BUDGETS[p].limit))
            return False, None
        return True, est

    def send(p, c, tag, est):
        t = targets[p]
        d = dispatch(t, workload, tag, bool(t.get("split")), dry)
        if not dry and d["run_id"] is None:
            d["run_id"] = find_run(t["repo"], workload["workflow"], tag, d["since"])
        rec = dict(meta, workload=workload["id"], provider=p, copy=c, tag=tag, repo=t["repo"],
                   workflow=workload["workflow"], run_id=d["run_id"], dispatched_at=d["dispatched_at"],
                   dispatched_at_ms=d.get("dispatched_at_ms"), kind=kind)
        record(out, rec)
        rec["_est"] = est
        return rec

    def tag_of(p, c):
        return "rb/{set}/{session}/{round}/{wl}/{p}/{c}".format(wl=workload["id"], p=p, c=c, **meta)

    sent = []
    if copies == 1:
        order = list(providers)
        random.shuffle(order)
        for p in order:
            tag = tag_of(p, 0)
            ok, est = reserve(p, 0, tag)
            if ok:
                sent.append(send(p, 0, tag, est))
    else:
        order = list(providers)
        random.shuffle(order)
        for p in order:
            batch = []
            for c in range(copies):
                tag = tag_of(p, c)
                ok, est = reserve(p, c, tag)
                if ok:
                    batch.append((p, c, tag, est))
            with ThreadPoolExecutor(max_workers=max(1, len(batch))) as ex:
                recs = list(ex.map(lambda b: send(*b), batch))
            sent += recs
            ms = [r["dispatched_at_ms"] for r in recs if r.get("dispatched_at_ms")]
            if ms:
                spread = (max(ms) - min(ms)) / 1000
                record(out, dict(meta, workload=workload["id"], provider=p, event="burst_dispatch",
                                 copies=len(recs), first_ms=min(ms), last_ms=max(ms),
                                 spread_s=round(spread, 3)))
                print(f"[{now()}] burst {workload['id']} {p}: {len(recs)} dispatched within "
                      f"{spread:.2f} s", flush=True)
    if dry:
        for r in sent:
            if r["_est"] is not None:
                with LOCK:
                    BUDGETS[r["provider"]].reserved -= r["_est"]
        return
    left = wait_all(sent, plan.get("run_timeout_s", 7200))
    for r in sent:
        if r["_est"] is not None and (r["repo"], r["run_id"]) not in left:
            BUDGETS[r["provider"]].settle(workload["id"], r["repo"], r["run_id"], r["_est"])
        # A run that timed out keeps its reservation counted for the rest of the session.
    if left:
        print(f"[{now()}] TIMEOUT {workload['id']} {sorted(left)}", file=sys.stderr)
        record(out, dict(meta, workload=workload["id"], event="timeout", runs=sorted(map(list, left))))


def lane_worker(plan, targets, wls, providers_for, meta, out, dry):
    for wid in wls:
        w = plan["workloads"][wid]
        print(f"[{now()}] {meta['phase']} r{meta['round']} {wid}", flush=True)
        try:
            run_group(plan, targets, w, providers_for(wid), meta, out, dry)
        except Exception as e:  # log, record and continue with the next workload
            print(f"[{now()}] ERROR {wid}: {e!r}", file=sys.stderr, flush=True)
            record(out, dict(meta, workload=wid, event="error", error=repr(e)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", required=True)
    ap.add_argument("--targets", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--session", default="s1")
    ap.add_argument("--start-round", type=int, default=1)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--usage-observed", action="append", default=[], metavar="PROVIDER=MINUTES",
                    help="minutes this month shown on the provider's own usage page")
    a = ap.parse_args()
    plan, targets = load(a.plan), load(a.targets)
    targets = {k: v for k, v in targets.items() if not k.startswith("_")}  # "_note" and similar
    if not a.dry_run:
        # Refuse to start unless every run repository is still locked down: workflows start on
        # workflow_dispatch only, and outside contributors cannot open issues or pull requests.
        import trigger_guard
        bad = []
        for repo in sorted({t["repo"] for t in targets.values()}):
            refs = sorted({t.get("ref", "main") for t in targets.values() if t["repo"] == repo}
                          | {gh.get(f"/repos/{repo}")["default_branch"]})
            bad += trigger_guard.remote(repo, refs, settings=True)[0]
        if bad:
            for b in bad:
                print("TRIGGER GUARD:", b, file=sys.stderr)
            raise SystemExit("run repositories are not locked down; not dispatching anything")
    for p, t in targets.items():
        if t.get("minute_budget"):
            BUDGETS[p] = MinuteBudget(p, t["minute_budget"])
    for kv in a.usage_observed:
        p, mins = kv.split("=", 1)
        BUDGETS[p].observe(mins)
    for p, b in BUDGETS.items():
        print(f"[{now()}] budget {p}: {b.used():.0f}/{b.limit:.0f} min used this month", flush=True)
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    rng_seed = plan.get("seed")
    if rng_seed is not None:
        random.seed(f"{rng_seed}/{a.session}")

    def providers_for(wid):
        only = plan["workloads"][wid].get("providers")
        ps = [p for p in plan["providers"] if (only is None or p in only)]
        return [p for p in ps if p in targets and wid not in targets[p].get("skip", [])
                and ("only" not in targets[p] or wid in targets[p]["only"])]

    total = plan["warmup_rounds"] + plan["measured_rounds"]
    for rnd in range(a.start_round, total + 1):
        phase = "warmup" if rnd <= plan["warmup_rounds"] else "measure"
        meta = {"set": plan["set"], "session": a.session, "round": rnd, "phase": phase}
        record(a.out, dict(meta, event="round_start", at=now()))
        threads = []
        for lane in plan["lanes"]:
            wls = list(lane)
            th = threading.Thread(target=lane_worker,
                                  args=(plan, targets, wls, providers_for, meta, a.out, a.dry_run))
            th.start()
            threads.append(th)
        for th in threads:
            th.join()
        for wid in plan.get("bursts", []):
            w = plan["workloads"][wid]
            print(f"[{now()}] {phase} r{rnd} burst {wid} x{w['copies']}", flush=True)
            # Optional "burst_groups": provider groups that burst one after another, e.g. when two
            # providers share one account-wide concurrency limit.
            groups = [list(g) for g in (plan.get("burst_groups") or [providers_for(wid)])]
            if plan.get("burst_group_order") == "random":
                random.shuffle(groups)  # seeded per session, like the rest of the order
            for g in groups:
                ps = [p for p in g if p in providers_for(wid)]
                if ps:
                    try:
                        run_group(plan, targets, w, ps, meta, a.out, a.dry_run, copies=w["copies"])
                    except Exception as e:
                        print(f"[{now()}] ERROR burst {wid}: {e!r}", file=sys.stderr, flush=True)
                        record(a.out, dict(meta, workload=wid, event="error", error=repr(e)))
        record(a.out, dict(meta, event="round_end", at=now()))


if __name__ == "__main__":
    main()
