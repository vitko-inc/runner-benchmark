# Pilot (2026-10-05)

One round of the v1 plan, run on 2026-10-05 before the `prereg-v1` tag, to check the harness, the collectors and the cost rules. It is disclosed here and is **not part of the result set**. Every number is a single run with cold caches and no warm-up.

## Changes it led to before the tag

- All-in pricing for self-hosted options (public IPv4, accelerator storage, internet egress and fixed monthly costs were left out of the earlier rule).
- RunsOn's `codex-lint` on its next memory size (2 vCPU / 16 GiB), applying METHOD.md's next-size rule after it ran out of memory at 8 GiB.
- Harness and analysis fixes.
- One Vitko Runners service change: when a host is full, a pool with queued jobs takes the capacity that another pool's idle standby runners were holding. In the pilot, the second Vitko arm's burst had waited for the first arm's idle standbys to expire.

## Pilot indices (single run; time / cost relative to GitHub-hosted 2 vCPU, all-in pricing)

| Configuration | Time | Cost |
|---|---|---|
| Vitko Runners, recommended configuration (warm starts + split tests) | 0.38 | 0.13 |
| Vitko Runners | 0.53 | 0.15 |
| Blacksmith, 2 vCPU | 0.57 | 0.39 |
| GitHub-hosted, 4 vCPU | 0.64 | 1.24 |
| Self-hosted: GCE n4d-standard-2 always-on pool (on-demand, U = 50%, all-in) | 0.72 | 0.78 |
| Ubicloud standard, 2 vCPU | 0.84 | 0.16 |
| RunsOn (self-hosted on AWS, defaults: spot), 2 vCPU | 0.88 | 0.17 |
| Self-hosted: AWS EC2 m8a.large, one VM per job (on-demand) | 0.95 | 0.39 |
| GitHub-hosted, 2 vCPU | 1.00 | 1.00 |

Compare with the official indices in [README.md](README.md); a single run can move individual workloads by tens of percent.
