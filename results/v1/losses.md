# Losses

Every failed, timed-out, voided or re-run run of the three official sessions. Failures are counted in the results and never replaced; only runs lost to a failure of the benchmark's own harness were re-run, as pre-registered.

## Failed measured runs (counted)

| Session | Configuration | Workload | Round | Conclusion | Failing step | Run id |
|---|---|---|---|---|---|---|
| s1 | Blacksmith, 2 vCPU | vite | 6 | failure | Test build | 37665364638 |
| s1 | GitHub-hosted, 4 vCPU | codex-lint | 6 | cancelled | — | 37666516324 |
| s1 | Ubicloud standard, 2 vCPU | vite | 9 | failure | Test build | 37703496105 |
| s2 | Vitko Runners, recommended configuration (warm starts + split tests) | vite | 5 | failure | Test build (network, unsplit) | 37886184896 |
| s2 | GitHub-hosted, 2 vCPU | vite | 8 | failure | Test build | 37903532653 |
| s2 | RunsOn (self-hosted on AWS, defaults: spot), 2 vCPU | vite | 9 | failure | Test serve | 37910716629 |
| s2 | Vitko Runners, recommended configuration (warm starts + split tests) | vite | 10 | failure | Test serve (split) | 37917965739 |
| s2 | Blacksmith, 2 vCPU | vite | 10 | failure | Test build | 37917978296 |
| s2 | GitHub-hosted, 2 vCPU | vite | 11 | failure | Test build | 37929841834 |
| s2 | GitHub-hosted, 4 vCPU | vite | 11 | failure | Test serve (bundled dev) | 37929844429 |
| s2 | Self-hosted: GCE n4d-standard-2 always-on pool (on-demand, U = 50%, all-in) | vite | 12 | failure | Test build | 37937820337 |
| s3 | GitHub-hosted, 2 vCPU | vite | 9 | failure | Test build | 38112389494 |
| s3 | Vitko Runners, recommended configuration (warm starts + split tests) | vite | 11 | failure | Test build (split) | 38119611179 |
| s3 | GitHub-hosted, 4 vCPU | vite | 12 | failure | Test serve | 38123494651 |
| s3 | Blacksmith, 2 vCPU | vite | 12 | failure | Test build | 38123502327 |

15 runs. All but one are `vite` (one step of its end-to-end tests); the same step failed on several providers in several rounds, which looks like a flaky upstream test. The exception is a GitHub-hosted 4 vCPU `codex-lint` run that hung and was cancelled after the 2-hour timeout. The plain Vitko Runners configuration had no failed measured run in any session.

## Failed warm-up runs (not measured)

| Session | Configuration | Workload | Round | Conclusion | Failing step | Run id |
|---|---|---|---|---|---|---|
| s1 | GitHub-hosted, 4 vCPU | vite | 1 | failure | Test serve | 37625468553 |

## Runs lost to the harness and run again (replacement rounds)

- **Session 1, rounds 2 to 4:** GitHub's API returned HTTP 500 for some dispatch requests during an incident, so 16 dispatches were not accepted. After the session, the cells that had no accepted run were dispatched again in a replacement round (8 workloads in round 3, and the burst for four configurations in round 4). See `s1/dispatch.jsonl` (`error`, `replacement_start` events) and deviations.md.
- **Session 3, round 5, `ec2-eph` burst:** the self-hosted EC2 launcher's GitHub token expired, and the 20 runs of the burst waited about 45 minutes with no runner. They are voided (the harness failed, not the provider) and the burst was run again in the replacement round. The 20 voided runs are kept in `raw/voided-jobs.jsonl.gz` and are not analysed; the run ids are in `s3/dispatch.jsonl` (`superseded_partial`).

## Not voided

Provider-side failures and slow starts were never voided: for example the registration-cap refusals on the Vitko Runners host in sessions 2 and 3 (deviations.md), and the failed `vite` runs above.

