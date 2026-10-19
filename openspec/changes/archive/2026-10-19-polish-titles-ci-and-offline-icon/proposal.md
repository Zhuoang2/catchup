# Proposal

## Why

Three small, independent fixes from the backlog. None needs a product decision.

- **#15, double ellipsis in derived titles.** When a feed entry has no title, `_entry_title` (`backend/src/catchup/sources/feeds.py:106-117`) uses the first 80 characters of its text and appends "…". If the cut text already ends in dots, as in a Mastodon post whose text ends "...", the title ends "...…".
- **#21, release builds for documentation-only pushes.** Every push to `main` runs `.github/workflows/release.yml`, which rebuilds the amd64 and arm64 image for the `edge` tag. That includes pushes that change only `docs/process/` or `openspec/`. The image is built only from `frontend/` and `backend/` (`Dockerfile`, the `COPY` lines).
- **#43, part 1: the offline page has no icon.** The service worker serves `frontend/public/offline.html` when the server is not running (`public/sw.js`). That page declares no `<link rel="icon">`, so its tab shows the browser's default icon. Pointing it at `/icon.svg` would not help: the server is down, and the service worker precaches only `/offline.html`.

## What Changes

- **Titles.** When a derived title is cut, trailing dots (`.`) and ellipsis characters (`…`) are removed from the cut text before the single "…" is added. Titles from the feed, and texts of 80 characters or fewer, are unchanged.
- **CI.** The `push` trigger of `release.yml` gets `paths-ignore` for `docs/**`, `openspec/**`, `assets/**`, and `**/*.md`. GitHub does not evaluate path filters for tag pushes, so `v*.*.*` releases still always build (GitHub's workflow syntax reference, `on.push.paths`, checked on 2026-10-19). `ci.yml` is unchanged.
- **Offline icon.** `offline.html` declares the CatchUp icon as an inline `data:` SVG, with the same artwork as `public/icon.svg`. It then needs no request to the stopped server.
- **Out of scope:**
  - #43 part 2, legibility at 16 px, which needs a design decision;
  - caching icon files in the service worker;
  - any change to how titles are derived when no cut happens.

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- `content-collection`, "Readable titles for untitled entries": a cut title ends with exactly one ellipsis. New scenario.
- `local-deployment`, "Offline page when the server is not running": the offline page shows the CatchUp icon in the browser tab, without a network request. New scenario.

## Impact

- `backend/src/catchup/sources/feeds.py` (`_entry_title`) and a test in `backend/tests/` near the existing title tests.
- `.github/workflows/release.yml`.
- `frontend/public/offline.html`, and a test in `frontend/src/install.test.ts`.
- No API, database, or dependency change.
