# monorepo

- **Project:** vercel/ai at `ai@7.0.126` (`45e1fbc3ea10d22f852e12b1c1851e289c85e835`), licence Apache-2.0. Fetched at run time, not vendored.
- **Upstream job:** `.github/workflows/ci.yml`, job Build Examples (next-core).
- **Benchmark workflow:** [`.github/workflows/wl-monorepo.yml`](../../.github/workflows/wl-monorepo.yml).

## Portability edits (identical for every provider)

- One shard (next-core) of the four.
- Node is set up before pnpm.
- The .turbo/.next build-cache restore is omitted: with the same commit every run it would replay every task. This is the full build a change to shared packages triggers. The pnpm store cache is kept.
