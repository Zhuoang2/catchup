# Proposal

## Why

CatchUp's interface is almost unstyled HTML (`frontend/src/style.css` is 4 lines). Pages show raw status values such as "Stage: no_new_content", give screen-reader and keyboard users little support, and cannot be installed as an app.

Reading the digest is the main activity and the first thing the 2026-12-10 demo audience sees. D-014 decided on a local web app that is installable as a PWA.

The user chose the visual direction **C7 · Front page grid** after two prototype rounds and an independent Design plugin review (`prototypes/`, `design-review-c7.md`).

## What Changes

- **A newspaper-style interface built from the C7 prototype.**
  - Layout: a shared container and a 12-column grid for masthead, navigation, and content, with topics as section rows (title column plus items in columns). Narrow windows get a single column. Light and dark themes follow the system.
- **Digest reading:**
  - a compact masthead
  - a headline with edition number, date, and time
  - an index of sections
  - content-driven item widths
  - key-point lists for long transcripts
  - Creator updates with sentence-case reason labels
  - an explanation when a digest has only Creator updates
- **Every screen and state of the prototype:**
  - Generate: first run, idle, collecting, summarizing, succeeded, no new content, failed
  - Sources: list, previews, error, delete confirmation, empty
  - Settings: saved, first run, tested, error
  - History: list, empty
  - offline

  Each state has one primary action and state-aware side information.
- **Accessibility to WCAG 2.1 AA:**
  - contrast of 4.5:1 for text and 3:1 for UI boundaries in both themes
  - generated text marked with its language
  - focus moves for the skip link and the digest index
  - a status region for run progress and results
  - errors linked to their fields
  - reduced motion respected
- **Installable app:** a web app manifest and icons, plus a minimal service worker that shows an offline page when the CatchUp server is not running. It never caches app code or API responses.
- **Saved digests keep two more facts:** the digest language and each item's source kind. A migration adds both to the snapshot, and the digest API returns them, so the interface can mark language and show source types even after settings or sources change.

## Capabilities

### New Capabilities
- `user-interface`: layout and themes, digest reading, screen states and primary actions, side information, accessibility behavior, and the copy shown for each state.

### Modified Capabilities
- `local-deployment`: CatchUp is installable as an app, and shows an offline page when its server is not running.
- `digest-history`: a reopened digest shows its edition number and time, and keeps the language and source kinds it was saved with.

## Impact

- **Frontend:** a rewrite of `frontend/src/pages/*.tsx`, `App.tsx`, and the styles. New `frontend/src/styles/` and `frontend/src/components/`. New `frontend/public/` (manifest, icons, `sw.js`, `offline.html`). An icon script under `frontend/scripts/`. `index.html` links the manifest.
- **Frontend dev dependencies:** `vitest-axe` and `axe-core`. No runtime dependencies are added.
- **Backend:** Alembic migration `0003` (`digests.language`, `digest_items.source_kind`), `digest/runner.py` (writes the snapshot), and `api/digests.py` (returns it). No change to static serving.
- **CI and packaging:** `scripts/docker-smoke.sh` also checks the manifest, the service worker, and the offline page. The CI job names are unchanged.
- **Docs:** a README section on installing the app.
- **Not changed:** API endpoints, routes, and backend behavior outside the snapshot fields.
