#!/usr/bin/env python3
"""All-in cost of the RunsOn arm (METHOD.md, "Cost"): everything the jobs use in the AWS account
RunsOn runs in, measured per job, plus the stack's fixed monthly cost.

Per job (variable):
  instance  EC2 seconds from launch to the first observation of shutting-down/terminated
            (monitor.py), 60 s minimum, x the spot price for that type and AZ at launch
            (describe-spot-price-history), or the on-demand list price (AWS Price List API)
  disk      root EBS GB x gp3 $/GB-month, prorated per second
  ipv4      public IPv4 $/hour over the instance's life, when the instance had a public address
  s3        storage: every object written to the stack's cache bucket during the session (object
            listing) x $/GB-month x the bucket's expiry for its prefix, attributed to jobs in
            proportion to the bytes each job's instance sent to S3 (VPC flow logs);
            requests: the bucket's CloudWatch request metrics (GET/PUT/LIST/HEAD, 1-minute sums)
            split evenly between the RunsOn jobs running in each minute
  egress    bytes the instance sent out of the VPC except to S3 (free through the stack's S3
            gateway endpoint), from the VPC's flow logs (selfhosted/flowlogs.py), x the egress $/GB
  control   usage-driven control plane over the session window (Lambda requests and GB-seconds,
            SQS requests, API Gateway requests, DynamoDB request units, CloudWatch Logs
            ingestion), split evenly between the session's RunsOn jobs
Fixed per month (written to --fixed-out, amortised by analysis/aggregate.py):
  the stack's always-on worker (Fargate vCPU and memory, from its task definition), the worker's
  public IPv4, Secrets Manager secrets, CloudWatch Logs storage, and the licence.

Usage:
  cost_runson.py --raw results/<set>/raw/jobs.jsonl.gz --instances runson_instances.jsonl \
      --prices prices/<date>.json --stack runs-on-<name> --out runson-cost.csv --fixed-out runson-fixed.json
"""
import argparse
import collections
import csv
import datetime as dt
import gzip
import json
import math
import re
import subprocess


def t(s):
    return dt.datetime.fromisoformat(s.replace("Z", "+00:00"))


class AWS:
    def __init__(self, region):
        self.region = region

    def __call__(self, *a):
        out = subprocess.run(["aws", "--region", self.region, *a, "--output", "json"],
                             capture_output=True, text=True)
        if out.returncode != 0:
            raise RuntimeError(f"aws {' '.join(a[:2])}: {out.stderr.strip()[:300]}")
        return json.loads(out.stdout) if out.stdout.strip() else {}


def metric_sum(aws, namespace, name, dims, start, end, period=60, stat="Sum"):
    d = aws("cloudwatch", "get-metric-statistics", "--namespace", namespace, "--metric-name", name,
            "--dimensions", *[f"Name={k},Value={v}" for k, v in dims.items()],
            "--start-time", start.isoformat(), "--end-time", end.isoformat(),
            "--period", str(period), "--statistics", stat)
    return {t(p["Timestamp"]): p[stat] for p in d.get("Datapoints", [])}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--raw", required=True)
    ap.add_argument("--instances", required=True)
    ap.add_argument("--prices", required=True)
    ap.add_argument("--price-ref", default="runson-aws")
    ap.add_argument("--provider", default="runson2")
    ap.add_argument("--stack", required=True)
    ap.add_argument("--region", default="us-east-2")
    ap.add_argument("--out", required=True)
    ap.add_argument("--fixed-out", required=True)
    ap.add_argument("--flowlogs-bucket", required=True, help="S3 bucket receiving the RunsOn VPC's flow logs")
    ap.add_argument("--workdir", default="/tmp")
    a = ap.parse_args()
    P = json.load(open(a.prices))["providers"][a.price_ref]
    aws = AWS(a.region)

    inst = {}
    for line in open(a.instances):
        r = json.loads(line)
        inst[r["instance_id"]] = r

    jobs = []  # (job, run record)
    for line in gzip.open(a.raw, "rt"):
        r = json.loads(line)
        if r.get("provider") != a.provider:
            continue
        for j in r["jobs"]:
            if j.get("started_at") and j.get("completed_at"):
                jobs.append((j, r))
    if not jobs:
        raise SystemExit("no RunsOn jobs")
    win_start = min(t(j["started_at"]) for j, _ in jobs) - dt.timedelta(minutes=5)
    win_end = max(t(j["completed_at"]) for j, _ in jobs) + dt.timedelta(minutes=10)

    # ---- stack resources
    res = aws("cloudformation", "list-stack-resources", "--stack-name", a.stack)["StackResourceSummaries"]
    by_type = collections.defaultdict(list)
    for x in res:
        by_type[x["ResourceType"]].append(x["PhysicalResourceId"])
    bucket = next(b for b in by_type["AWS::S3::Bucket"] if "cache" in b)
    expiry = {}
    for rule in aws("s3api", "get-bucket-lifecycle-configuration", "--bucket", bucket).get("Rules", []):
        pre = (rule.get("Filter") or {}).get("Prefix")
        if pre is not None and rule.get("Expiration", {}).get("Days"):
            expiry[pre] = rule["Expiration"]["Days"]

    # ---- S3 objects written during the session
    objs = []
    token = None
    while True:
        args = ["s3api", "list-objects-v2", "--bucket", bucket, "--max-items", "1000"]
        if token:
            args += ["--starting-token", token]
        d = aws(*args)
        objs += [o for o in d.get("Contents", []) if win_start <= t(o["LastModified"]) <= win_end]
        token = d.get("NextToken")
        if not token:
            break

    def days_for(key):
        best = max((p for p in expiry if key.startswith(p)), key=len, default=None)
        return expiry.get(best, P["s3_default_retention_days"])

    # storage cost of everything written during the session (object listing x the expiry of its prefix)
    store_total = sum(o["Size"] / 1e9 * P["s3_usd_per_gb_month"] * days_for(o["Key"]) / 30.4 for o in objs)
    written_total = sum(o["Size"] for o in objs)

    # ---- S3 requests (CloudWatch request metrics, 1-minute sums), split by active jobs per minute
    req_usd_by_min = collections.defaultdict(float)
    for name, price_key in (("GetRequests", "s3_get_usd_per_1000"), ("PutRequests", "s3_put_usd_per_1000"),
                            ("ListRequests", "s3_put_usd_per_1000"), ("HeadRequests", "s3_get_usd_per_1000"),
                            ("PostRequests", "s3_put_usd_per_1000")):
        for ts_, v in metric_sum(aws, "AWS/S3", name, {"BucketName": bucket, "FilterId": "EntireBucket"},
                                 win_start, win_end).items():
            req_usd_by_min[ts_] += v / 1000 * P[price_key]
    s3_req_usd = collections.defaultdict(float)
    for minute, usd in req_usd_by_min.items():
        active = [j for j, _ in jobs if t(j["started_at"]) - dt.timedelta(minutes=1) <= minute <= t(j["completed_at"])]
        if not active:
            active = [j for j, _ in jobs]
        for j in active:
            s3_req_usd[j["id"]] += usd / len(active)

    # ---- internet egress per instance (VPC flow logs)
    import os
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
    import flowlogs  # noqa: E402
    vpc = by_type["AWS::EC2::VPC"][0]
    flows = flowlogs.egress_by_instance(a.region, a.flowlogs_bucket, vpc, win_start, win_end, a.workdir)

    # storage is attributed to jobs in proportion to the bytes each job's instance sent to S3
    def iid_of(j):
        m = re.search(r"(i-[0-9a-f]{8,})", j.get("runner_name") or "")
        return m.group(1) if m else None
    s3_up = {j["id"]: flows.get(iid_of(j), {}).get("s3", 0) for j, _ in jobs}
    up_total = sum(s3_up.values())
    s3_store_usd = {jid: (store_total * b / up_total if up_total else store_total / len(jobs)) for jid, b in s3_up.items()}

    # ---- usage-driven control plane over the window, split evenly
    control = 0.0
    for fn in by_type["AWS::Lambda::Function"]:
        cfg = aws("lambda", "get-function-configuration", "--function-name", fn)
        gb = cfg["MemorySize"] / 1024
        arm = "arm64" in cfg.get("Architectures", [])
        inv = sum(metric_sum(aws, "AWS/Lambda", "Invocations", {"FunctionName": fn}, win_start, win_end, 3600).values())
        ms = sum(metric_sum(aws, "AWS/Lambda", "Duration", {"FunctionName": fn}, win_start, win_end, 3600).values())
        control += inv * P["lambda_usd_per_request"] + ms / 1000 * gb * P["lambda_arm_usd_per_gb_s" if arm else "lambda_x86_usd_per_gb_s"]
    for q in by_type["AWS::SQS::Queue"]:
        qn = q.rsplit("/", 1)[-1]
        reqs = sum(sum(metric_sum(aws, "AWS/SQS", m, {"QueueName": qn}, win_start, win_end, 3600).values())
                   for m in ("NumberOfMessagesSent", "NumberOfMessagesReceived", "NumberOfMessagesDeleted",
                             "NumberOfEmptyReceives"))
        control += reqs / 1e6 * P["sqs_usd_per_million"]
    for api in by_type["AWS::ApiGateway::RestApi"]:
        name = aws("apigateway", "get-rest-api", "--rest-api-id", api)["name"]
        cnt = sum(metric_sum(aws, "AWS/ApiGateway", "Count", {"ApiName": name}, win_start, win_end, 3600).values())
        control += cnt / 1e6 * P["apigw_usd_per_million"]
    for tbl in by_type["AWS::DynamoDB::Table"]:
        w = sum(metric_sum(aws, "AWS/DynamoDB", "ConsumedWriteCapacityUnits", {"TableName": tbl}, win_start, win_end, 3600).values())
        r = sum(metric_sum(aws, "AWS/DynamoDB", "ConsumedReadCapacityUnits", {"TableName": tbl}, win_start, win_end, 3600).values())
        control += w / 1e6 * P["ddb_usd_per_million_wru"] + r / 1e6 * P["ddb_usd_per_million_rru"]
    log_groups = by_type["AWS::Logs::LogGroup"]
    for lg in log_groups:
        b = sum(metric_sum(aws, "AWS/Logs", "IncomingBytes", {"LogGroupName": lg}, win_start, win_end, 3600).values())
        control += b / 1e9 * P["logs_ingest_usd_per_gb"]
    control_per_job = control / len(jobs)

    # ---- per job
    rows = []
    spot_cache = {}
    for j, r in jobs:
        m = re.search(r"(i-[0-9a-f]{8,})", j.get("runner_name") or "")
        if not m or m.group(1) not in inst:
            raise SystemExit(f"no instance record for job {j['id']} (runner {j.get('runner_name')})")
        i = inst[m.group(1)]
        start, end = t(i["launch"]), t(i["end"])
        secs = max(60.0, (end - start).total_seconds())
        key = (i["type"], i["az"], start.replace(second=0, microsecond=0))
        if i["lifecycle"] == "spot":
            if key not in spot_cache:
                h = aws("ec2", "describe-spot-price-history", "--instance-types", i["type"],
                        "--availability-zone", i["az"], "--product-descriptions", "Linux/UNIX",
                        "--start-time", start.isoformat(), "--end-time", start.isoformat())["SpotPriceHistory"]
                spot_cache[key] = float(sorted(h, key=lambda x: x["Timestamp"])[-1]["SpotPrice"])
            hourly = spot_cache[key]
        else:
            d = AWS("us-east-1")("pricing", "get-products", "--service-code", "AmazonEC2", "--filters",
                                 f"Type=TERM_MATCH,Field=instanceType,Value={i['type']}",
                                 f"Type=TERM_MATCH,Field=regionCode,Value={a.region}",
                                 "Type=TERM_MATCH,Field=operatingSystem,Value=Linux",
                                 "Type=TERM_MATCH,Field=tenancy,Value=Shared",
                                 "Type=TERM_MATCH,Field=preInstalledSw,Value=NA",
                                 "Type=TERM_MATCH,Field=capacitystatus,Value=Used")
            item = json.loads(d["PriceList"][0])
            od = next(iter(item["terms"]["OnDemand"].values()))
            hourly = float(next(iter(od["priceDimensions"].values()))["pricePerUnit"]["USD"])
        ec2 = secs / 3600 * hourly
        disk = (i["root_gb"] or 0) * P["ebs_usd_per_gb_month"] / (730 * 3600) * secs
        ipv4 = secs / 3600 * P["ipv4_usd_per_hour"] if i.get("public_ip", True) else 0.0
        fl = flows.get(i["instance_id"], {"internet": 0, "s3": 0})
        out_b = fl["internet"]
        egress = out_b / 1e9 * P["egress_usd_per_gb"]
        total = ec2 + disk + ipv4 + s3_store_usd[j["id"]] + s3_req_usd[j["id"]] + egress + control_per_job
        rows.append({"job_id": j["id"], "instance_id": i["instance_id"], "type": i["type"],
                     "lifecycle": i["lifecycle"], "billed_seconds": round(secs, 1), "usd_per_hour": hourly,
                     "ec2_usd": round(ec2, 6), "disk_usd": round(disk, 6), "ipv4_usd": round(ipv4, 6),
                     "s3_storage_usd": round(s3_store_usd[j["id"]], 6),
                     "s3_request_usd": round(s3_req_usd[j["id"]], 6), "internet_egress_bytes": int(out_b),
                     "s3_transfer_bytes": int(fl["s3"]),
                     "egress_usd": round(egress, 6), "control_usd": round(control_per_job, 6),
                     "usd": round(total, 6)})
    with open(a.out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    # ---- fixed monthly
    fixed = {}
    for c in aws("ecs", "list-clusters")["clusterArns"]:
        if a.stack not in c:
            continue
        for s in aws("ecs", "list-services", "--cluster", c)["serviceArns"]:
            sv = aws("ecs", "describe-services", "--cluster", c, "--services", s)["services"][0]
            td = aws("ecs", "describe-task-definition", "--task-definition", sv["taskDefinition"])["taskDefinition"]
            arm = (td.get("runtimePlatform") or {}).get("cpuArchitecture") == "ARM64"
            n = sv["desiredCount"]
            vcpu, gb = int(td["cpu"]) / 1024, int(td["memory"]) / 1024
            fixed["fargate_worker"] = n * 730 * (vcpu * P["fargate_arm_vcpu_hour" if arm else "fargate_x86_vcpu_hour"]
                                                 + gb * P["fargate_arm_gb_hour" if arm else "fargate_x86_gb_hour"])
            if sv["networkConfiguration"]["awsvpcConfiguration"].get("assignPublicIp") == "ENABLED":
                fixed["fargate_worker_ipv4"] = n * 730 * P["ipv4_usd_per_hour"]
    fixed["secrets"] = len(by_type["AWS::SecretsManager::Secret"]) * P["secrets_usd_per_month"]
    stored = 0
    for lg in log_groups:
        g = aws("logs", "describe-log-groups", "--log-group-name-prefix", lg)["logGroups"]
        stored += sum(x.get("storedBytes", 0) for x in g if x["logGroupName"] == lg)
    fixed["logs_storage"] = stored / 1e9 * P["logs_storage_usd_per_gb_month"]
    fixed["licence"] = P["licence_usd_per_year"] / 12
    out = {a.provider: {"usd_per_month": round(sum(fixed.values()), 4), "items": {k: round(v, 4) for k, v in fixed.items()}}}
    json.dump(out, open(a.fixed_out, "w"), indent=1)
    print(f"{len(rows)} RunsOn jobs priced; control plane usage ${control:.4f} over the session "
          f"(${control_per_job:.6f}/job); fixed ${out[a.provider]['usd_per_month']}/month; "
          f"{written_total} bytes written to the cache bucket")


if __name__ == "__main__":
    main()
