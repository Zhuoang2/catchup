# Proposal

## Why

The browser tab for CatchUp shows the browser's default globe icon (issue #37, found while the user was testing on 2026-10-17).
- `frontend/index.html` declares the manifest and an `apple-touch-icon`, but no `<link rel="icon">`.
- Browsers then request `/favicon.ico`, which the SPA fallback answers with `index.html` (`backend/src/catchup/main.py:93-102`).
- The app's icon already exists in `frontend/public/` (`icon.svg` and PNGs), but nothing points the tab at it.

## What Changes

- **Declare the icon for the browser tab** in `frontend/index.html`, reusing the existing files (the user's decision on 2026-10-18, with no new design):
  - `/icon.svg` as `image/svg+xml`
  - `/icon-192.png` as a 192 × 192 PNG fallback for browsers without SVG favicons
- **Out of scope:**
  - a new icon design
  - changing what the SPA fallback returns for `/favicon.ico`. Browsers stop requesting it once a page declares an icon, and changing the fallback would be a separate backend behavior change.

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- `local-deployment`, "Installable as an app": the page also declares the app icon for the browser tab. A scenario covers the tab icon.

## Impact

- `frontend/index.html`: two `<link rel="icon">` tags.
- `frontend/src/install.test.ts`: a test that `index.html` declares both icons, and that each points at an existing file of the declared type.
- No backend, API, manifest, or service-worker change.
