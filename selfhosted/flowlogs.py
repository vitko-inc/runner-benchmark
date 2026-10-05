"""Per-instance internet egress from VPC flow logs delivered to S3 (all-in cost, METHOD.md).

Flow log format (selfhosted/aws/main.tf, and the RunsOn VPC's flow log):
  version interface-id instance-id srcaddr dstaddr bytes start end flow-direction pkt-dst-aws-service action

For each instance: bytes it sent out of the VPC (flow-direction "egress", destination outside the
VPC's CIDRs, action ACCEPT), split into S3 in the same region (pkt-dst-aws-service "S3": free, through
the gateway endpoint or same-region transfer) and everything else (charged as internet egress).
"""
import collections
import gzip
import ipaddress
import json
import subprocess


def _aws(region, *a):
    out = subprocess.run(["aws", "--region", region, *a, "--output", "json"], capture_output=True, text=True)
    if out.returncode != 0:
        raise RuntimeError(f"aws {' '.join(a[:2])}: {out.stderr.strip()[:300]}")
    return json.loads(out.stdout) if out.stdout.strip() else {}


def vpc_cidrs(region, vpc_id):
    v = _aws(region, "ec2", "describe-vpcs", "--vpc-ids", vpc_id)["Vpcs"][0]
    nets = [ipaddress.ip_network(c["CidrBlock"]) for c in v.get("CidrBlockAssociationSet", [])]
    nets += [ipaddress.ip_network(c["Ipv6CidrBlock"]) for c in v.get("Ipv6CidrBlockAssociationSet", [])]
    return nets


def egress_by_instance(region, bucket, vpc_id, start, end, workdir):
    """Return {instance_id: {"internet": bytes, "s3": bytes}} for flows that started in [start, end]."""
    nets = vpc_cidrs(region, vpc_id)
    t0, t1 = int(start.timestamp()), int(end.timestamp())
    keys = []
    for day in sorted({start.strftime("%Y/%m/%d"), end.strftime("%Y/%m/%d")}):
        token = None
        while True:
            args = ["s3api", "list-objects-v2", "--bucket", bucket, "--prefix", "AWSLogs/"]
            if token:
                args += ["--starting-token", token]
            d = _aws(region, *args)
            keys += [o["Key"] for o in d.get("Contents", []) if f"/{day}/" in o["Key"]]
            token = d.get("NextToken")
            if not token:
                break
    out = collections.defaultdict(lambda: {"internet": 0, "s3": 0})
    for k in sorted(set(keys)):
        local = f"{workdir}/{k.replace('/', '_')}"
        subprocess.run(["aws", "--region", region, "s3", "cp", "--quiet", f"s3://{bucket}/{k}", local], check=True)
        with gzip.open(local, "rt") as f:
            for line in f:
                p = line.split()
                if len(p) < 11 or p[0] == "version" or p[8] != "egress" or p[10] != "ACCEPT":
                    continue
                iid, dst, nbytes, fstart = p[2], p[4], p[5], p[6]
                if iid == "-" or nbytes == "-" or not (t0 - 120 <= int(fstart) <= t1 + 120):
                    continue
                try:
                    ip = ipaddress.ip_address(dst)
                except ValueError:
                    continue
                if any(ip in n for n in nets if n.version == ip.version):
                    continue
                out[iid]["s3" if p[9] == "S3" else "internet"] += int(nbytes)
    return out
