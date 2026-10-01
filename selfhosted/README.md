# Self-hosted baselines

Two ways teams commonly run their own GitHub Actions runners, both on on-demand cloud VMs with
the stock `actions/runner`:

| Baseline | What it is | Cost per run |
|---|---|---|
| `ec2-eph` ([aws/](aws/)) | One fresh EC2 `m8a.large` (2 vCPU / 8 GiB) per job, started when the job is queued and terminated when it ends | Billed instance seconds from launch to termination (60 s minimum), including boot, plus the root volume and public IPv4 ([aws/cost_ec2.py](aws/cost_ec2.py)) |
| `gce-pool` ([gcp/](gcp/)) | An always-on pool of GCE `n4d-standard-2` (2 vCPU / 8 GiB) VMs, each running a persistent runner | The job's run time ÷ U at the VM's per-second price (U = 50%, with 25% and 75% shown) |

Both use the same machine image ([image/](image/)): Ubuntu 24.04, Docker with buildx, git,
build-essential, Python 3, passwordless sudo for the runner user and `actions/runner` 2.337.0.
Toolchains come from each workflow's `setup-*` actions. Prices are in [pricing.json](pricing.json).

## Next memory size

A workload that needs more than 8 GiB without swap (`codex-lint`) runs on each baseline's next
memory size at 2 vCPU and is priced there, the same rule every provider follows:

- EC2: a second launcher with its own label and state directory, overriding the instance type:
  `RB_LABEL=<label>-16g RB_INSTANCE_TYPE=r8a.large RB_STATE_DIR=<dir>-16g aws/launcher.sh start`
- GCE: a second pool from the same Terraform with its own var file and state:
  `name`, `runner_labels` = `<label>-16g`, `machine_type = "n4d-highmem-2"`, a separate `subnet_cidr`.

## Running

1. Bake the image (`image/bake_aws.sh`, `image/bake_gcp.sh`).
2. AWS: `terraform apply` in `aws/` with your values, then `aws/launcher.sh start` (it polls the
   repository's queued jobs for its label and starts one VM per job with a single-use JIT runner
   configuration; your GitHub token never leaves the machine running the launcher).
3. GCP: `gcp/pool.sh up <N>` (mints a short-lived registration token locally) and
   `gcp/pool.sh down` afterwards.

Deployment-specific values (project, repository, image ids) go in untracked `*.tfvars` files.
