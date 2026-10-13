# CI Bench v1: results

**Status:** three official sessions complete (2026-10-07 to 2026-10-11), analysed as pre-registered ([PREREGISTRATION.md](../../PREREGISTRATION.md), tag `prereg-v1`). Maintained by Vitko, which sells Vitko Runners; see the [conflict-of-interest note](../../PREREGISTRATION.md).

**Headline.** Measured October 7–11, 2026: Vitko Runners with warm starts and test parallelization ran 2.29x as fast as GitHub-hosted 2 vCPU at 84% lower cost per job; plain Vitko Runners ran 1.74x as fast at 84% lower cost. One self-hosted configuration, RunsOn on AWS, has a lower cost index at high volume (see the table and the cost notes).

## Result in one table

Time and cost per job relative to GitHub-hosted 2 vCPU (= 1.00); geometric mean over 12 workloads; lower is better; 95% intervals from a block bootstrap over sessions and rounds. Sorted by time index.

| Configuration | Time index | 95% CI | Cost index | 95% CI | Faster than GitHub 2 vCPU | Lower cost | Time x cost |
|---|---|---|---|---|---|---|---|
| Vitko Runners, recommended configuration (warm starts + split tests) | 0.436 | 0.423–0.459 | 0.158 | 0.156–0.160 | 2.29x (2.18–2.36x) | 84% | 0.069 |
| Vitko Runners | 0.574 | 0.556–0.602 | 0.157 | 0.155–0.159 | 1.74x (1.66–1.80x) | 84% | 0.090 |
| GitHub-hosted, 4 vCPU | 0.642 | 0.629–0.669 | 1.387 | 1.350–1.424 | 1.56x (1.50–1.59x) | 39% higher | 0.891 |
| Blacksmith, 2 vCPU | 0.645 | 0.606–0.759 | 0.482 | 0.435–0.537 | 1.55x (1.32–1.65x) | 52% | 0.311 |
| Self-hosted: GCE n4d-standard-2 always-on pool (on-demand, U = 50%, all-in) | 0.667 | 0.658–0.692 | 0.409 | 0.386–0.440 | 1.50x (1.45–1.52x) | 59% | 0.273 |
| RunsOn (self-hosted on AWS, defaults: spot), 2 vCPU | 0.828 | 0.816–0.859 | 0.121 | 0.117–0.125 | 1.21x (1.16–1.23x) | 88% | 0.100 |
| Self-hosted: AWS EC2 m8a.large, one VM per job (on-demand) | 0.869 | 0.833–0.947 | 0.383 | 0.358–0.405 | 1.15x (1.06–1.20x) | 62% | 0.333 |
| Ubicloud standard, 2 vCPU | 0.879 | 0.847–0.921 | 0.173 | 0.167–0.180 | 1.14x (1.09–1.18x) | 83% | 0.152 |
| GitHub-hosted, 2 vCPU | 1.000 | 1.000–1.000 | 1.000 | 1.000–1.000 | — | — | 1.000 |

Reading the table:

- **Vitko Runners with warm starts and test parallelization** (`vitko-opt`; these are Vitko Runners' own features) ran 2.29x as fast as GitHub-hosted 2 vCPU (2.18–2.36x) at 84% lower cost per job. It has the lowest time index of the nine configurations, so it is the fastest in this benchmark by that measure. Its time-index interval (0.423–0.459) does not overlap that of any other configuration; the next fastest is GitHub-hosted, 4 vCPU at 0.629–0.669 (plain Vitko Runners is at 0.556–0.602).
- **Vitko Runners, plain** (`vitko`) ran 1.74x as fast (1.66–1.80x) at 84% lower cost per job.
- **The self-hosted RunsOn arm has the lowest cost index in this table (0.121, against 0.157 for plain Vitko Runners and 0.158 for the saved-setup arm)**, priced all-in at 100,000 jobs per month. That index depends on volume: its fixed monthly costs (control plane, licence) are spread over the job count, giving 0.250 at 10,000 and 1.431 at 1,000 jobs per month. Vitko Runners' indices do not change with volume. Self-hosted options also run in the customer's own cloud account and need the customer to operate them.
- GitHub-hosted 4 vCPU is a different machine size. Its speed advantage over 2 vCPU is a difference in machine size, not in speed per vCPU.
- Best time x cost: Vitko Runners, recommended configuration (warm starts + split tests) (0.069), Vitko Runners (0.090), RunsOn (self-hosted on AWS, defaults: spot), 2 vCPU (0.100).

## What was measured

Twelve workloads (eleven open-source projects' own CI jobs and a burst of 20 concurrent runs), nine configurations, three sessions of 10 measured rounds after 2 warm-up rounds: 930 measured runs per configuration (330 single-job runs and 30 bursts of 20). Times come from GitHub's own job timestamps. Definitions, statistics and fairness rules: [METHOD.md](../../METHOD.md). The plan and the workflows are in this repository at the tag `prereg-v1`.

## Per session

Time / cost index per session (the pooled value above is computed from all three).

| Configuration | Session 1 | Session 2 | Session 3 | Pooled |
|---|---|---|---|---|
| Vitko Runners, recommended configuration (warm starts + split tests) | 0.43 / 0.16 | 0.45 / 0.16 | 0.43 / 0.16 | 0.44 / 0.16 |
| Vitko Runners | 0.57 / 0.16 | 0.58 / 0.16 | 0.57 / 0.16 | 0.57 / 0.16 |
| GitHub-hosted, 4 vCPU | 0.66 / 1.41 | 0.64 / 1.37 | 0.64 / 1.38 | 0.64 / 1.39 |
| Blacksmith, 2 vCPU | 0.77 / 0.54 | 0.66 / 0.47 | 0.60 / 0.43 | 0.64 / 0.48 |
| Self-hosted: GCE n4d-standard-2 always-on pool (on-demand, U = 50%, all-in) | 0.68 / 0.43 | 0.67 / 0.39 | 0.66 / 0.39 | 0.67 / 0.41 |
| RunsOn (self-hosted on AWS, defaults: spot), 2 vCPU | 0.85 / 0.12 | 0.83 / 0.12 | 0.82 / 0.12 | 0.83 / 0.12 |
| Self-hosted: AWS EC2 m8a.large, one VM per job (on-demand) | 0.94 / 0.40 | 0.90 / 0.39 | 0.83 / 0.36 | 0.87 / 0.38 |
| Ubicloud standard, 2 vCPU | 0.89 / 0.17 | 0.91 / 0.18 | 0.85 / 0.17 | 0.88 / 0.17 |
| GitHub-hosted, 2 vCPU | 1.00 / 1.00 | 1.00 / 1.00 | 1.00 / 1.00 | 1.00 / 1.00 |

## Pairwise ratios

Time and cost of the two Vitko Runners configurations relative to each other configuration (below 1.00 = Vitko Runners is faster / cheaper), with 95% intervals.

| Compared with | vitko-opt time | CI | vitko-opt cost | CI | vitko time | CI | vitko cost | CI |
|---|---|---|---|---|---|---|---|---|
| GitHub-hosted, 4 vCPU | 0.68 | 0.65–0.71 | 0.11 | 0.11–0.12 | 0.89 | 0.85–0.94 | 0.11 | 0.11–0.12 |
| Blacksmith, 2 vCPU | 0.68 | 0.57–0.71 | 0.33 | 0.29–0.36 | 0.89 | 0.75–0.97 | 0.33 | 0.29–0.36 |
| Self-hosted: GCE n4d-standard-2 always-on pool (on-demand, U = 50%, all-in) | 0.65 | 0.63–0.68 | 0.39 | 0.36–0.41 | 0.86 | 0.83–0.90 | 0.38 | 0.36–0.41 |
| RunsOn (self-hosted on AWS, defaults: spot), 2 vCPU | 0.53 | 0.51–0.55 | 1.30 | 1.26–1.35 | 0.69 | 0.67–0.72 | 1.30 | 1.26–1.35 |
| Self-hosted: AWS EC2 m8a.large, one VM per job (on-demand) | 0.50 | 0.46–0.52 | 0.41 | 0.39–0.44 | 0.66 | 0.61–0.71 | 0.41 | 0.39–0.44 |
| Ubicloud standard, 2 vCPU | 0.50 | 0.48–0.51 | 0.91 | 0.88–0.94 | 0.65 | 0.63–0.69 | 0.91 | 0.87–0.94 |
| GitHub-hosted, 2 vCPU | 0.44 | 0.42–0.46 | 0.16 | 0.16–0.16 | 0.57 | 0.56–0.60 | 0.16 | 0.15–0.16 |

All pairs are in `out/results.json` (`pairwise`).

## Leave one workload out

The time index with each workload dropped in turn (the cost index is in `out/results.json`).

| Dropped | vitko-opt | vitko | gh4 | blacksmith2 | gce-pool | runson2 | ec2-eph | ubicloud2 | gh2 |
|---|---|---|---|---|---|---|---|---|---|
| burst | 0.43 | 0.57 | 0.65 | 0.68 | 0.67 | 0.84 | 0.90 | 0.89 | 1.00 |
| cli | 0.44 | 0.56 | 0.65 | 0.63 | 0.65 | 0.82 | 0.86 | 0.87 | 1.00 |
| codex-lint | 0.43 | 0.59 | 0.65 | 0.66 | 0.67 | 0.84 | 0.90 | 0.89 | 1.00 |
| container | 0.42 | 0.56 | 0.63 | 0.59 | 0.66 | 0.84 | 0.86 | 0.88 | 1.00 |
| fd | 0.43 | 0.58 | 0.64 | 0.64 | 0.66 | 0.82 | 0.84 | 0.87 | 1.00 |
| flask | 0.43 | 0.56 | 0.62 | 0.62 | 0.69 | 0.78 | 0.78 | 0.83 | 1.00 |
| guava | 0.43 | 0.58 | 0.63 | 0.65 | 0.66 | 0.83 | 0.90 | 0.89 | 1.00 |
| monorepo | 0.44 | 0.59 | 0.65 | 0.66 | 0.66 | 0.84 | 0.88 | 0.89 | 1.00 |
| pydantic | 0.44 | 0.57 | 0.63 | 0.65 | 0.67 | 0.83 | 0.87 | 0.88 | 1.00 |
| ts | 0.45 | 0.58 | 0.65 | 0.66 | 0.67 | 0.84 | 0.91 | 0.90 | 1.00 |
| vite | 0.45 | 0.57 | 0.66 | 0.65 | 0.67 | 0.84 | 0.89 | 0.88 | 1.00 |
| vue | 0.46 | 0.58 | 0.65 | 0.65 | 0.67 | 0.83 | 0.86 | 0.87 | 1.00 |

## Per workload

### Median wall time (seconds)

| Workload | vitko-opt | vitko | gh4 | blacksmith2 | gce-pool | runson2 | ec2-eph | ubicloud2 | gh2 |
|---|---|---|---|---|---|---|---|---|---|
| burst | 131 | 160 | 154 | **97** | 153 | 177 | 160 | 203 | 259 |
| cli | **140** | 272 | 192 | 286 | 310 | 327 | 357 | 359 | 368 |
| codex-lint | 405 | **404** | 476 | 448 | 580 | 622 | 512 | 682 | 884 |
| container | 178 | 179 | 185 | 386 | 178 | **174** | 246 | 213 | 238 |
| fd | **45** | 49 | 66 | 64 | 64 | 88 | 114 | 87 | 92 |
| flask | 13 | 16 | 21 | 22 | **11** | 38 | 70 | 36 | 23 |
| guava | **650** | 655 | 946 | 735 | 820 | 896 | 716 | 881 | 1166 |
| monorepo | **172** | 180 | 220 | 176 | 278 | 288 | 280 | 276 | 384 |
| pydantic | **68** | 105 | 154 | 103 | 119 | 146 | 154 | 158 | 179 |
| ts | **243** | 372 | 434 | 400 | 532 | 570 | 433 | 560 | 784 |
| vite | **199** | 350 | 288 | 360 | 401 | 437 | 402 | 502 | 603 |
| vue | **32** | 63 | 67 | 76 | 76 | 101 | 116 | 114 | 120 |

Lowest median wall time per workload (bold): `vitko-opt` 8 of 12 (cli, fd, guava, monorepo, pydantic, ts, vite, vue); `blacksmith2` 1 of 12 (burst); `vitko` 1 of 12 (codex-lint); `runson2` 1 of 12 (container); `gce-pool` 1 of 12 (flask).
Lowest mean cost per workload: `runson2` 7 of 12 (burst, cli, codex-lint, guava, monorepo, ts, vite); `vitko-opt` 4 of 12 (fd, flask, pydantic, vue); `ubicloud2` 1 of 12 (container).
`vitko-opt` versus GitHub-hosted 2 vCPU: median wall time lower on 12 of 12 workloads; mean cost lower on 12 of 12.
`vitko` versus GitHub-hosted 2 vCPU: median wall time lower on 12 of 12 workloads; mean cost lower on 12 of 12.

### 95th-percentile wall time (seconds)

| Workload | vitko-opt | vitko | gh4 | blacksmith2 | gce-pool | runson2 | ec2-eph | ubicloud2 | gh2 |
|---|---|---|---|---|---|---|---|---|---|
| burst | 191 | 372 | 179 | 190 | **165** | 340 | 182 | 271 | 283 |
| cli | **145** | 326 | 198 | 323 | 326 | 334 | 398 | 429 | 382 |
| codex-lint | **425** | 441 | 511 | 748 | 625 | 662 | 598 | 881 | 934 |
| container | 208 | 199 | 215 | 663 | 201 | **188** | 300 | 262 | 282 |
| fd | **48** | 56 | 81 | 81 | 72 | 93 | 139 | 125 | 120 |
| flask | **14** | 20 | 24 | 36 | 32 | 40 | 134 | 46 | 28 |
| guava | **661** | 661 | 983 | 875 | 854 | 919 | 783 | 1086 | 1249 |
| monorepo | **191** | 211 | 235 | 291 | 297 | 313 | 342 | 366 | 401 |
| pydantic | **119** | 140 | 173 | 145 | 129 | 152 | 184 | 204 | 196 |
| ts | **332** | 404 | 548 | 570 | 582 | 597 | 467 | 844 | 824 |
| vite | **212** | 389 | 315 | 511 | 457 | 456 | 503 | 594 | 753 |
| vue | **33** | 64 | 88 | 104 | 109 | 108 | 155 | 152 | 129 |

### Mean cost per job (USD, 100,000 jobs per month for self-hosted)

| Workload | vitko-opt | vitko | gh4 | blacksmith2 | gce-pool | runson2 | ec2-eph | ubicloud2 | gh2 |
|---|---|---|---|---|---|---|---|---|---|
| burst | 0.0520 | 0.0556 | 0.6356 | 0.1656 | 0.1351 | **0.0511** | 0.1112 | 0.0623 | 0.4998 |
| cli | 0.0117 | 0.0097 | 0.0452 | 0.0204 | 0.0173 | **0.0041** | 0.0139 | 0.0078 | 0.0394 |
| codex-lint | 0.0135 | 0.0135 | 0.0989 | 0.0336 | 0.0636 | **0.0101** | 0.0489 | 0.0149 | 0.0872 |
| container | 0.0061 | 0.0060 | 0.0424 | 0.0307 | 0.0532 | 0.0060 | 0.0436 | **0.0047** | 0.0266 |
| fd | **0.0014** | 0.0016 | 0.0192 | 0.0055 | 0.0035 | 0.0018 | 0.0047 | 0.0021 | 0.0120 |
| flask | **0.0004** | 0.0005 | 0.0120 | 0.0040 | 0.0011 | 0.0014 | 0.0036 | 0.0013 | 0.0060 |
| guava | 0.0216 | 0.0218 | 0.1808 | 0.0512 | 0.0449 | **0.0096** | 0.0318 | 0.0192 | 0.1090 |
| monorepo | 0.0056 | 0.0058 | 0.0464 | 0.0140 | 0.0158 | **0.0039** | 0.0116 | 0.0061 | 0.0396 |
| pydantic | **0.0022** | 0.0034 | 0.0332 | 0.0087 | 0.0065 | 0.0024 | 0.0064 | 0.0037 | 0.0196 |
| ts | 0.0274 | 0.0122 | 0.0992 | 0.0299 | 0.0290 | **0.0061** | 0.0168 | 0.0120 | 0.0774 |
| vite | 0.0127 | 0.0115 | 0.0604 | 0.0264 | 0.0231 | **0.0053** | 0.0163 | 0.0107 | 0.0609 |
| vue | **0.0017** | 0.0020 | 0.0200 | 0.0077 | 0.0044 | 0.0020 | 0.0051 | 0.0027 | 0.0140 |

### Success rate (cells below 100%)

| Workload | Configuration | Runs | Successful |
|---|---|---|---|
| codex-lint | GitHub-hosted, 4 vCPU | 30 | 29 |
| vite | Blacksmith, 2 vCPU | 30 | 27 |
| vite | Self-hosted: GCE n4d-standard-2 always-on pool (on-demand, U = 50%, all-in) | 30 | 29 |
| vite | GitHub-hosted, 2 vCPU | 30 | 27 |
| vite | GitHub-hosted, 4 vCPU | 30 | 28 |
| vite | RunsOn (self-hosted on AWS, defaults: spot), 2 vCPU | 30 | 29 |
| vite | Ubicloud standard, 2 vCPU | 30 | 29 |
| vite | Vitko Runners, recommended configuration (warm starts + split tests) | 30 | 27 |

## Cost notes

List prices with their sources and dates are in [prices/2026-10-05.json](../../prices/2026-10-05.json). Managed providers are priced at list price under their own billing rule. Self-hosted options are priced all-in: everything their jobs use in the customer's cloud account, measured per job, plus fixed monthly costs spread over 100,000 jobs per month (sensitivity at 10,000 and 1,000). Test parallelization is billed on the parts only while a split step runs (METHOD.md).

| Configuration | 100,000 jobs/month | 10,000 | 1,000 |
|---|---|---|---|
| Vitko Runners, recommended configuration (warm starts + split tests) | 0.158 | 0.158 | 0.158 |
| Vitko Runners | 0.157 | 0.157 | 0.157 |
| GitHub-hosted, 4 vCPU | 1.387 | 1.387 | 1.387 |
| Blacksmith, 2 vCPU | 0.482 | 0.482 | 0.482 |
| Self-hosted: GCE n4d-standard-2 always-on pool (on-demand, U = 50%, all-in) | 0.409 | 0.409 | 0.409 |
| RunsOn (self-hosted on AWS, defaults: spot), 2 vCPU | 0.121 | 0.250 | 1.431 |
| Self-hosted: AWS EC2 m8a.large, one VM per job (on-demand) | 0.383 | 0.395 | 0.508 |
| Ubicloud standard, 2 vCPU | 0.173 | 0.173 | 0.173 |
| GitHub-hosted, 2 vCPU | 1.000 | 1.000 | 1.000 |

The always-on Google Cloud pool is priced by its utilization U (run time / U): cost index 0.745 at U = 25%, 0.409 at 50% (as in the table) and 0.293 at 75%.

## Configurations

| Id | Name | Size |
|---|---|---|
| `vitko-opt` | Vitko Runners, recommended configuration (warm starts + split tests) | up to 2 vCPU / 8 GB |
| `vitko` | Vitko Runners | up to 2 vCPU / 8 GB |
| `gh4` | GitHub-hosted, 4 vCPU | 4 vCPU / 16 GB |
| `blacksmith2` | Blacksmith, 2 vCPU | 2 vCPU / 8 GB |
| `gce-pool` | Self-hosted: GCE n4d-standard-2 always-on pool (on-demand, U = 50%, all-in) | 2 vCPU / 8 GiB |
| `runson2` | RunsOn (self-hosted on AWS, defaults: spot), 2 vCPU | 2 vCPU / 8 GB |
| `ec2-eph` | Self-hosted: AWS EC2 m8a.large, one VM per job (on-demand) | 2 vCPU / 8 GiB |
| `ubicloud2` | Ubicloud standard, 2 vCPU | 2 vCPU / 8 GB |
| `gh2` | GitHub-hosted, 2 vCPU | 2 vCPU / 8 GB |

`vitko-opt` uses Vitko Runners' own features: a saved setup restored for each job (warm starts) and test parallelization, both through open-source actions. The plain `vitko` configuration uses neither.

## Burst

Twenty runs dispatched at once, per round: queue time and dispatch spread (harness clock, first to last dispatch request).

| Configuration | Queue p50 (s) | Queue p95 (s) | Median wall (s) | Dispatch spread median / max (s) |
|---|---|---|---|---|
| Vitko Runners, recommended configuration (warm starts + split tests) | 17 | 115 | 131 | 0.26 / 0.43 |
| Vitko Runners | 18 | 295 | 160 | 0.29 / 2.21 |
| GitHub-hosted, 4 vCPU | 3 | 39 | 154 | 0.27 / 0.39 |
| Blacksmith, 2 vCPU | 9 | 16 | 97 | 0.28 / 0.62 |
| Self-hosted: GCE n4d-standard-2 always-on pool (on-demand, U = 50%, all-in) | 2 | 3 | 153 | 0.26 / 0.34 |
| RunsOn (self-hosted on AWS, defaults: spot), 2 vCPU | 22 | 194 | 177 | 0.28 / 0.64 |
| Self-hosted: AWS EC2 m8a.large, one VM per job (on-demand) | 65 | 93 | 160 | 0.29 / 0.39 |
| Ubicloud standard, 2 vCPU | 18 | 127 | 203 | 0.26 / 0.43 |
| GitHub-hosted, 2 vCPU | 3 | 31 | 259 | 0.28 / 0.58 |

## Hardware seen

Most common CPU family, vCPUs, memory (GiB) and swap (GiB) reported by each job's hardware probe.

| Configuration | CPU family | vCPUs | Memory | Swap | Share of jobs |
|---|---|---|---|---|---|
| Vitko Runners, recommended configuration (warm starts + split tests) | AMD EPYC | 2 | 8 | 8 | 100% |
| Vitko Runners | AMD EPYC | 2 | 8 | 8 | 100% |
| GitHub-hosted, 4 vCPU | AMD EPYC | 4 | 16 | 3 | 85% |
| Blacksmith, 2 vCPU | AMD EPYC | 2 | 8 | 11 | 89% |
| Self-hosted: GCE n4d-standard-2 always-on pool (on-demand, U = 50%, all-in) | AMD EPYC | 2 | 8 | 8 | 100% |
| RunsOn (self-hosted on AWS, defaults: spot), 2 vCPU | Intel Xeon | 2 | 8 | 0 | 71% |
| Self-hosted: AWS EC2 m8a.large, one VM per job (on-demand) | AMD EPYC | 2 | 8 | 8 | 100% |
| Ubicloud standard, 2 vCPU | AMD Ryzen | 2 | 8 | 4 | 99% |
| GitHub-hosted, 2 vCPU | AMD EPYC | 2 | 8 | 3 | 86% |

## Losses and deviations

Every failed, voided or re-run run is listed in [losses.md](losses.md). Every change after the `prereg-v1` tag, dated with its reason, is in [deviations.md](deviations.md). Failures are counted and never replaced; only runs voided by a failure of the benchmark's own harness were re-run.

## Limits of this result set

- 2 vCPU class (plus one 4 vCPU reference), Linux x64, one region per provider, public repositories; no GPU, macOS, Windows or ARM.
- Our own benchmark: Vitko maintains it and sells one of the products measured. Method, data and workflows are open; providers may report errors (CONTRIBUTING.md); corrections are recorded in a dated changelog.
- The saved-setup configuration was measured on a Vitko Runners host build that predates later cleanup of restored setups (deviations.md).
- Self-hosted options were operated by us, with the settings in [providers/](../../providers/) and [selfhosted/](../../selfhosted/).

## Reproduce

See "Running it" in the [main README](../../README.md). `raw/split-copies.jsonl` holds the timing of every split-test copy, keyed by the id of the job that started it (the billing input for the split configuration). The aggregate output in `out/` is produced by:

```
python3 analysis/aggregate.py --raw results/v1/raw/jobs.jsonl.gz --providers providers --prices prices/2026-10-05.json \
  --extra-cost results/v1/raw/selfhosted-cost.csv --split-copies results/v1/raw/split-copies.jsonl \
  --fixed-costs results/v1/raw/fixed-costs.json --reference gh2 --boot 10000 --out results/v1/out
```

