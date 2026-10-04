# vite

- **Project:** vitejs/vite at `v8.3.1` (`39ddf7ccf7e7469ff6a3ba37bca38c32ea804d6e`), licence MIT. Fetched at run time, not vendored.
- **Upstream job:** `.github/workflows/ci.yml`, job "Build&Test: node-24, ubuntu-latest".
- **Benchmark workflow:** [`.github/workflows/wl-vite.yml`](../../.github/workflows/wl-vite.yml).

## Portability edits (identical for every provider)

- Node is set up before pnpm, so pnpm's installer never runs on a runner image's own Node.
- `pnpm playwright install --with-deps chromium`: installs Chromium's system libraries, which GitHub's image already has.
- One matrix cell (Node 24, Linux); the `changed` gate job is dropped.
- `environment-react-ssr > pre-bundling > deps reload`: the assertion on the two "dependencies optimized" log lines is made order-insensitive (sorted). Upstream logs the server line after a fixed `setTimeout(…, 2 * debounceMs)` (200 ms) and the client line after a browser reload and re-bundle, so the order is a race that faster machines lose. The assertion is unchanged otherwise: both lines must appear.
- `legacy > watch > rebuilds styles only entry on change`: after upstream's own waits, the test also waits (up to 10 s, polling every 100 ms) until the rebuilt CSS files referenced by the manifest exist and contain the new colour. Upstream counts watcher END events and races a second one against 100 ms (a workaround for rolldown issue 10613); the number and timing of those events vary, so on any machine the files are sometimes read before the rebuild has written them. The assertions are unchanged.

## Split-test arm (Track B)

On the arm that uses `vitko-inc/split-tests`, the unit step and the three end-to-end steps (serve, bundled dev, build) are shared out by test file. Spec files whose pages load resources from the internet (`playground/assets/`, `playground/css/`, `playground/css-lightningcss/`) run in an unsplit step right after each split step, because the parts have no outside network. Together the two steps run the same spec files and the same tests as the plain steps.
