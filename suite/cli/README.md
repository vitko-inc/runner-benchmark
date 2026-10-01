# cli

- **Project:** cli/cli at `v2.102.0` (`fc4b137cdef0a6bd28fd461b7cf9c84a5812a8cd`), licence MIT. Fetched at run time, not vendored.
- **Upstream job:** `.github/workflows/go.yml`, job build (ubuntu-latest).
- **Benchmark workflow:** [`.github/workflows/wl-cli.yml`](../../.github/workflows/wl-cli.yml).

## Portability edits (identical for every provider)

- One matrix cell (Linux).
- `GOFLAGS=-count=1`: the same commit runs every time, so Go's test-result cache would skip every test. Module and build caches are kept.
