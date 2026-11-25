# Submitted run: Skipbox S, 4 vCPU (skipbox), with gh4 side by side

Submitted by Fluxenic Inc., which makes Skipbox. Status: submitted, not reproduced (CONTRIBUTING.md).

- **Provider definition:** [`providers/skipbox.json`](../../providers/skipbox.json) (copy: `provider.json`).
- **Price source:** <https://skipbox.dev/pricing>, read on 2026-11-13; entry `skipbox-s` in [`prices/2026-11-13.json`](../../prices/2026-11-13.json) (copy: `prices.json`).
- **Plan:** [`plans/skipbox-2026-11.json`](../../plans/skipbox-2026-11.json) (copy: `plan.json`).
- **Terms:** customers may run and publish benchmarks of Skipbox without asking: <https://docs.skipbox.dev/benchmarks#publish-your-own-benchmarks>.
- **Files:** `dispatch.jsonl` (harness/run.py), `raw/jobs.jsonl.gz` (harness/collect.py), `out/` (analysis/aggregate.py with `--reference gh4`), `RESULTS.md` (per-workload table, failed runs, hardware seen, every run id).

## Run

- **Dates:** see `RESULTS.md` (first and last dispatch, UTC).
- **Repositories (public):** skipbox in [`tomoyaf/runner-benchmark`](https://github.com/tomoyaf/runner-benchmark) (default branch `rb-runs`: this repository's `wl-*.yml` without `scan.yml`); gh4 in [`tomoyaf/rb-runs-gh4`](https://github.com/tomoyaf/rb-runs-gh4) (the same `wl-*.yml` only). Each arm in its own repository, so no cache is shared (METHOD.md, Isolation).
- **Labels:** `skipbox`; `ubuntu-24.04`.
- **Commands:**

```sh
python3 harness/run.py --plan plans/skipbox-2026-11.json --targets targets.json --out work/skipbox-2026-11/dispatch.jsonl --session s1
python3 harness/collect.py --dispatch work/skipbox-2026-11/dispatch.jsonl --out work/skipbox-2026-11/raw/jobs.jsonl.gz
python3 analysis/aggregate.py --raw work/skipbox-2026-11/raw/jobs.jsonl.gz --providers providers --prices prices/2026-11-13.json --out work/skipbox-2026-11/out --reference gh4
```

## Deviations from METHOD.md

1. **One session, 2 warm-up and 3 measured rounds** (an official set has 3 sessions of 10 measured rounds): 3 measured runs per cell.
2. **No burst.** An S plan runs 1 job at a time; 20 jobs at once need 20 S plans.
3. **One lane.** Workloads run one after another, so at most one job per arm runs at a time.
4. **Reference arm gh4, not gh2.** The runs are in public repositories under a personal account. There, `ubuntu-24.04` is GitHub's 4 vCPU / 16 GB runner (gh4), and a 2-core larger runner (gh2 in a public repository) needs an organization on a paid GitHub plan. gh4 has the same vCPU count as Skipbox S and twice its memory.
5. **The account.** The runs come from Fluxenic's own GitHub account, which holds 4 S plans (not billed). Up to 4 of its jobs can run at once and a job can land on any of its 4 own machines, each with its own kept disk; the harness ran one Skipbox job at a time. Fluxenic's own deploy jobs use the same account and host, so they can run beside the session's jobs.
6. **Hardware.** That account's jobs run only on Fluxenic's host home-1 in Japan (Intel Core Ultra 7 265F, 8 performance and 12 efficiency cores, 64 GB; one host core per vCPU, performance cores first). The host runs other Skipbox jobs at the same time. A customer's own machine may run on Hetzner Cloud (Finland or Germany) on other CPUs, which this run did not measure.
7. **Kept build output.** By default an own machine keeps git checkouts with cargo's `target/` directories between an account's jobs (from 2026-11-13), as well as dependency, Docker and tool caches. The benchmark rebuilds one commit, so on Skipbox the Rust builds (fd, codex-lint, pydantic's Rust core) of measured rounds start from the previous round's build output. METHOD.md disables source-keyed caches in the workflows; this reuse is the runner's default, with no workflow change, and it can't be turned off for build output alone ("Clean every job" runs every job on a fresh VM with no cache at all). Read those three workloads with this in mind.
8. **Cost.** Skipbox has no per-minute price. `aggregate.py`'s rule `flat-monthly` prices the plans a monthly volume of a job needs (its concurrency at U = 50%, as for gce-pool) at $39 a month each, spread over the volume, at 100,000, 10,000 and 1,000 jobs a month.
