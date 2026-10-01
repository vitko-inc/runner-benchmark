# vite

- **Project:** vitejs/vite at `v8.3.1` (`39ddf7ccf7e7469ff6a3ba37bca38c32ea804d6e`), licence MIT. Fetched at run time, not vendored.
- **Upstream job:** `.github/workflows/ci.yml`, job "Build&Test: node-24, ubuntu-latest".
- **Benchmark workflow:** [`.github/workflows/wl-vite.yml`](../../.github/workflows/wl-vite.yml).

## Portability edits (identical for every provider)

- Node is set up before pnpm, so pnpm's installer never runs on a runner image's own Node.
- `pnpm playwright install --with-deps chromium`: installs Chromium's system libraries, which GitHub's image already has.
- One matrix cell (Node 24, Linux); the `changed` gate job is dropped.
- `environment-react-ssr > pre-bundling > deps reload`: the assertion on the two "dependencies optimized" log lines is made order-insensitive (sorted). Upstream logs the server line after a fixed `setTimeout(…, 2 * debounceMs)` (200 ms) and the client line after a browser reload and re-bundle, so the order is a race that faster machines lose. The assertion is unchanged otherwise: both lines must appear.
