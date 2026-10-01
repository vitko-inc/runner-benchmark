# ts

- **Project:** microsoft/TypeScript at `v6.0.3` (`050880ce59e30b356b686bd3144efe24f875ebc8`), licence Apache-2.0. Fetched at run time, not vendored.
- **Upstream job:** `.github/workflows/ci.yml`, job Test Node 24 on ubuntu-latest.
- **Benchmark workflow:** [`.github/workflows/wl-ts.yml`](../../.github/workflows/wl-ts.yml).

## Portability edits (identical for every provider)

- One matrix cell (Node 24, Linux).
- The test bundle is built in its own step before the tests (the test step's own build is then a no-op).
