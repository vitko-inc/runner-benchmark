#!/usr/bin/env python3
"""Per-job all-in cost of the always-on GCE pool baseline (METHOD.md, "Cost").

  compute = job run time / U x (VM + boot disk + external IPv4) $/hour
            (an always-on pool is paid for whether busy or idle; U is its utilization)
  egress  = bytes the job's VM sent during the job (Cloud Monitoring
            compute.googleapis.com/instance/network/sent_bytes_count, 1-minute sums over the
            job's minutes) x the internet egress $/GB
  total   = compute + egress

Usage:
  cost_gce.py --raw results/<set>/raw/jobs.jsonl.gz --prices prices/<date>.json \
      --price-ref gcp-n4d-standard-2-pool --project <gcp project> --out gce-cost.csv
Uses `gcloud auth print-access-token` for the Monitoring API.
"""
import argparse
import csv
import datetime as dt
import gzip
import json
import subprocess
import urllib.parse
import urllib.request


def ts(s):
    return dt.datetime.fromisoformat(s.replace("Z", "+00:00"))


def sent_bytes(project, token, vm, start, end):
    start = start.replace(second=0)
    end = (end + dt.timedelta(minutes=1)).replace(second=0)
    q = urllib.parse.urlencode({
        "filter": ('metric.type="compute.googleapis.com/instance/network/sent_bytes_count" '
                   f'AND metric.labels.instance_name="{vm}"'),
        "interval.startTime": start.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "interval.endTime": end.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "aggregation.alignmentPeriod": "60s",
        "aggregation.perSeriesAligner": "ALIGN_SUM",
    })
    req = urllib.request.Request(f"https://monitoring.googleapis.com/v3/projects/{project}/timeSeries?{q}")
    req.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(req, timeout=60) as r:
        data = json.loads(r.read())
    total = 0
    for series in data.get("timeSeries", []):
        for p in series.get("points", []):
            total += int(p["value"].get("int64Value", 0))
    return total


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--raw", required=True)
    ap.add_argument("--prices", required=True)
    ap.add_argument("--price-ref", default="gcp-n4d-standard-2-pool")
    ap.add_argument("--provider", default="gce-pool")
    ap.add_argument("--project", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    pr = json.load(open(a.prices))["providers"][a.price_ref]
    hourly = pr["usd_per_hour"] + pr["disk_gib"] * pr["disk_usd_per_gib_month"] / 730 + pr["ipv4_usd_per_hour"]
    u, egress_gb = pr["utilization"], pr["egress_usd_per_gb"]
    token = subprocess.run(["gcloud", "auth", "print-access-token"], check=True, capture_output=True,
                           text=True).stdout.strip()
    rows = []
    for line in gzip.open(a.raw, "rt"):
        r = json.loads(line)
        if r.get("provider") != a.provider:
            continue
        for j in r["jobs"]:
            if not (j.get("started_at") and j.get("completed_at")):
                continue
            st, en = ts(j["started_at"]), ts(j["completed_at"])
            run_s = max(1.0, (en - st).total_seconds())
            billed = run_s / u
            compute = billed * hourly / 3600
            out_b = sent_bytes(a.project, token, j["runner_name"], st, en)
            egress = out_b / 1e9 * egress_gb
            rows.append({"job_id": j["id"], "runner_name": j["runner_name"], "run_s": round(run_s, 1),
                         "billed_s": round(billed, 1), "compute_usd": round(compute, 6),
                         "egress_bytes": out_b, "egress_usd": round(egress, 6),
                         "total_usd": round(compute + egress, 6)})
    with open(a.out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"{len(rows)} GCE pool jobs priced")


if __name__ == "__main__":
    main()
