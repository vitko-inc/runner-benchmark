# Runner benchmark

An open benchmark of GitHub Actions runners: GitHub-hosted runners, third-party runner
services and self-hosted cloud VMs, measured on the CI jobs of well-known open-source projects.

**Maintained by Vitko**, which sells one of the products measured here (Vitko Runners). The
method, the workflows, the analysis and every raw job record are in this repository so that
anyone can check or rerun the numbers. Corrections are welcome; see [CONTRIBUTING.md](CONTRIBUTING.md).

**Status:** method and harness in place; no result set has been published yet.

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
| okhttp | square/okhttp parent-5.5.0 | Gradle tests (JDK 21) |
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
export GITHUB_TOKEN=...   # a token with actions:write on the target repositories
python3 harness/run.py --plan plans/<plan>.json --targets targets.json --out work/<set>/dispatch.jsonl
python3 harness/collect.py --dispatch work/<set>/dispatch.jsonl --out work/<set>/raw/jobs.jsonl.gz
python3 analysis/aggregate.py --raw work/<set>/raw/jobs.jsonl.gz --providers providers \
    --prices prices/<date>.json --out work/<set>/ --reference gh2
```

Self-hosted baselines are set up with the Terraform and launcher in [selfhosted/](selfhosted/).

## Licences

Code: Apache-2.0 ([LICENSE](LICENSE)). Result data: CC BY 4.0 ([LICENSE-DATA](LICENSE-DATA)).
The benchmarked projects keep their own licences.
