# fd

- **Project:** sharkdp/fd at `v10.5.0` (`4f81778774463bf414a184cbe6d5219ad2229646`), licence Apache-2.0 OR MIT. Fetched at run time, not vendored.
- **Upstream job:** `.github/workflows/CICD.yml`, job x86_64-unknown-linux-gnu (ubuntu-24.04).
- **Benchmark workflow:** [`.github/workflows/wl-fd.yml`](../../.github/workflows/wl-fd.yml).

## Portability edits (identical for every provider)

- `cargo` instead of `cross` for the native x86_64 target (cross wraps the same build in Docker).
- Release packaging steps after the tests are omitted.
