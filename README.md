# Runner benchmark: an open, reproducible benchmark of GitHub Actions runners

An open benchmark of GitHub Actions runners: GitHub-hosted runners, third-party runner
services and self-hosted cloud VMs, measured on the CI jobs of well-known open-source projects.
Time and cost per job, with the method, the workflows, the analysis and every raw job record in
this repository.

**Maintained by Vitko**, which sells one of the products measured here (Vitko Runners). The
method, the workflows, the analysis and every raw job record are in this repository so that
anyone can check or rerun the numbers. Corrections are welcome; see [CONTRIBUTING.md](CONTRIBUTING.md).

## What is Vitko Runners?

Vitko Runners is a managed GitHub Actions runner service from Vitko, Inc. You change one
`runs-on` line in a workflow to run its jobs on Vitko Runners, and the same line to go back to
GitHub-hosted runners. It costs $0.002 per minute for a runner with up to 2 vCPU and 8 GB, billed
per second with no per-job minimum, and includes 2,000 free minutes a month. It runs Ubuntu 24.04
on x64 for private repositories and is in private beta. It has a hard monthly spend limit, and two
optional features: warm starts (jobs start with your toolchains and dependencies already in place)
and test parallelization (one workflow step runs a test suite as parallel parts).

- Site and waitlist: <https://runners.vitko.inc>. Pricing, dated and machine-readable:
  <https://runners.vitko.inc/pricing.json>.
- Public repositories: [`vitko-inc/split-tests`](https://github.com/vitko-inc/split-tests) (test
  parallelization), [`vitko-inc/checkpoint`](https://github.com/vitko-inc/checkpoint) (warm
  starts) and [`vitko-inc/setup-vitko`](https://github.com/vitko-inc/setup-vitko) (the command-line
  tool).
- It is one of the configurations measured below. This benchmark is the only place its measured
  numbers are published; the other pages on the site link here.

## Results: CI Bench v1

**Measured October 7–11, 2026** (three sessions, 930 measured runs per configuration):
Vitko Runners with warm starts and test parallelization ran 2.29x as fast as GitHub-hosted
2 vCPU at 84% lower cost per job; plain Vitko Runners ran 1.74x as fast at 84% lower cost. One
self-hosted configuration, RunsOn on AWS, has a lower cost index at high volume (see the cost
notes in the results).

**At a glance:** time and cost per job of each runner against GitHub-hosted 2 vCPU, at list price
(self-hosted options all-in at 100,000 jobs a month; RunsOn's cost index is 0.250 at 10,000 and
1.431 at 1,000 jobs a month, because its fixed monthly costs are spread over fewer jobs).

| Runner | Time per job vs GitHub-hosted 2 vCPU | Cost per job vs GitHub-hosted 2 vCPU |
|---|---|---|
| Vitko Runners, warm starts + test parallelization | 2.29x faster | 84% lower |
| Vitko Runners | 1.74x faster | 84% lower |
| GitHub-hosted, 4 vCPU | 1.56x faster | 39% higher |
| Blacksmith, 2 vCPU | 1.55x faster | 52% lower |
| Self-hosted Google Cloud pool (all-in) | 1.50x faster | 59% lower |
| RunsOn, self-hosted on AWS (all-in) | 1.21x faster | 88% lower |
| Self-hosted AWS EC2, one VM per job (all-in) | 1.15x faster | 62% lower |
| Ubicloud standard, 2 vCPU | 1.14x faster | 83% lower |
| GitHub-hosted, 2 vCPU | baseline | baseline |

**Full table.** Time and cost per job relative to GitHub-hosted 2 vCPU (= 1.00); geometric mean over 12
workloads; lower is better; 95% intervals from a block bootstrap over sessions and rounds. Sorted
by time index.

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

- Full results, per-workload tables, limitations and pairwise ratios: [results/v1/](results/v1/)
  (tag [`results-v1`](https://github.com/vitko-inc/runner-benchmark/tree/results-v1/results/v1)).
- Every measured run: [results/v1/out/](results/v1/out/) (`runs.csv`, `summary.csv`, `results.json`).
- Dated changes after pre-registration: [results/v1/deviations.md](results/v1/deviations.md).
- The same results, with charts: <https://runners.vitko.inc/benchmarks/>.

## What is measured

Twelve workloads, each the project's own CI job at a pinned release, with small portability
edits that are identical for every provider ([suite/](suite/)):

| Workload | Project | Job |
|---|---|---|
| vite | vitejs/vite v8.3.1 | build and test (Node 24) |
| vue | vuejs/core v3.5.43 | unit tests |
| flask | pallets/flask 3.1.3 | tests (Python 3.13) |
| pydantic | pydantic/pydantic v2.13.5 | tests (Python 3.13), including its Rust core build |
| fd | sharkdp/fd v10.5.0 | release build and tests |
| codex-lint | openai/codex rust-v0.159.3 | clippy over the Rust workspace |
| cli | cli/cli v2.102.0 | `go test -race` and build |
| guava | google/guava v33.7.2 | Maven build and tests (JDK 25) |
| monorepo | vercel/ai ai@7.0.126 | turbo build of the Next.js examples (one shard) |
| container | mastodon/mastodon v4.7.2 | Docker image build (linux/amd64) |
| ts | microsoft/TypeScript v6.0.3 | full test suite (Node 24) |
| burst | psf/black 26.5.1 | 20 test runs dispatched at once |

For every run: queue time, wall time and cost at each provider's public list price, with that
provider's own billing rule. Definitions, statistics and fairness rules are in [METHOD.md](METHOD.md).

## Providers

Provider definitions are in [providers/](providers/) and list prices with their sources in
[prices/](prices/). A provider is included only if its terms of service allow publishing
benchmark results.

## Running it

1. Copy this repository (the workflows must be on the default branch of the repository where
   the runs happen). Each provider should run in its own copy, so caches are never shared.
2. Install or connect the provider's runners to that repository.
3. Write a targets file (not committed) mapping provider ids to `{"repo": "<owner>/<name>", "runs_on": "<label>"}`.
4. Dispatch, collect and analyse:

```sh
export GITHUB_TOKEN=...   # a token with actions:write on the target repositories, or
# export GITHUB_TOKEN_CMD="<command that prints a short-lived token>"   # re-run every 20 minutes
python3 harness/run.py --plan plans/<plan>.json --targets targets.json --out work/<set>/dispatch.jsonl
python3 harness/collect.py --dispatch work/<set>/dispatch.jsonl --out work/<set>/raw/jobs.jsonl.gz
python3 analysis/aggregate.py --raw work/<set>/raw/jobs.jsonl.gz --providers providers \
    --prices prices/<date>.json --out work/<set>/ --reference gh2
```

Self-hosted baselines are set up with the Terraform and launcher in [selfhosted/](selfhosted/).

### Locking down the run repositories

A public run repository is connected to a paid runner account, so nobody outside the project may
be able to start anything in it:

- Every benchmark workflow starts on `workflow_dispatch` only, which needs write access. No
  workflow starts on push, pull requests, comments, schedules or calls from other workflows.
  `harness/trigger_guard.py` enforces this: CI runs it on this repository, and `harness/run.py`
  runs it against every run repository (and its settings) before dispatching, and refuses to
  start if anything is off.
- Copy only `.github/workflows/wl-*.yml` into a run repository, not `scan.yml`.
- In each run repository: issues, pull requests, wiki, projects and discussions off;
  "Require approval for all external contributors" for fork pull request runs; read-only
  default `GITHUB_TOKEN` that cannot approve pull requests; interaction limit
  "collaborators only"; write access only for the people who run the benchmark.
- Warm-start checkpoints are saved with `harness/capture.py`, which dispatches each workload
  on the default branch.

## Licences

Code: Apache-2.0 ([LICENSE](LICENSE)). Result data: CC BY 4.0 ([LICENSE-DATA](LICENSE-DATA)).
The benchmarked projects keep their own licences.
