# Self-hosted baselines

Two ways teams commonly run their own GitHub Actions runners, both on on-demand cloud VMs with
the stock `actions/runner`:

| Baseline | What it is | Cost per run |
|---|---|---|
| `ec2-eph` ([aws/](aws/)) | One fresh EC2 `m8a.large` (2 vCPU / 8 GiB) per job, started when the job is queued and terminated when it ends | Billed instance seconds from launch to termination (60 s minimum), including boot, plus the root volume and public IPv4 ([aws/cost_ec2.py](aws/cost_ec2.py)) |
| `gce-pool` ([gcp/](gcp/)) | An always-on pool of GCE `n4d-standard-2` (2 vCPU / 8 GiB) VMs, each running a persistent runner | The job's run time ÷ U at the VM's per-second price (U = 50%, with 25% and 75% shown) |

Both use the same machine image ([image/](image/)): Ubuntu 24.04, Docker with buildx, git,
build-essential, Python 3, passwordless sudo for the runner user, `actions/runner` 2.337.0 and
zram swap (below).
Toolchains come from each workflow's `setup-*` actions. Prices are in [pricing.json](pricing.json).

## Memory and swap

The image has swap: zram (compressed, in RAM, no disk), zstd, size min(RAM, 8 GiB), swap
priority 100, `vm.swappiness = 100`, `vm.page-cluster = 0`, set up by `systemd-zram-generator`
([image/install-runner-base.sh](image/install-runner-base.sh)). That is the same swap
configuration as the Vitko Runners guest, so every workload, `codex-lint` included, runs on the
2 vCPU / 8 GiB size and is priced there.

## Running

1. Bake the image (`image/bake_aws.sh`, `image/bake_gcp.sh`).
2. AWS: `terraform apply` in `aws/` with your values, then `aws/launcher.sh start` (it polls the
   repository's queued jobs for its label and starts one VM per job with a single-use JIT runner
   configuration; your GitHub token never leaves the machine running the launcher).
3. GCP: `gcp/pool.sh up <N>` (mints a short-lived registration token locally) and
   `gcp/pool.sh down` afterwards.

Deployment-specific values (project, repository, image ids) go in untracked `*.tfvars` files.

Credentials: the launcher and `gcp/pool.sh` need a token that can register runners on the run
repository (repository Administration: write; the launcher also reads Actions). The launcher takes
`GITHUB_TOKEN`, or `GITHUB_TOKEN_CMD` (a command that prints a short-lived token, re-run every 20
minutes, for example a GitHub App installation token); `pool.sh` uses the `gh` command line's login.
