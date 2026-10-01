# vite

- **Project:** vitejs/vite at `v8.3.1` (`39ddf7ccf7e7469ff6a3ba37bca38c32ea804d6e`), licence MIT. Fetched at run time, not vendored.
- **Upstream job:** `.github/workflows/ci.yml`, job "Build&Test: node-24, ubuntu-latest".
- **Benchmark workflow:** [`.github/workflows/wl-vite.yml`](../../.github/workflows/wl-vite.yml).

## Portability edits (identical for every provider)

- Node is set up before pnpm, so pnpm's installer never runs on a runner image's own Node.
- `pnpm playwright install --with-deps chromium`: installs Chromium's system libraries, which GitHub's image already has.
- One matrix cell (Node 24, Linux); the `changed` gate job is dropped.
