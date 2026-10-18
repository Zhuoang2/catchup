# Tasks

Implementer notes:
- **Read first.** Read `proposal.md` and `specs/local-deployment/spec.md`. There is no design document.
- **Work test-first with the `tdd` skill** (D-016). Write the test in 1.1, watch it fail, then make it pass in 1.2.
- **Out of scope:**
  - the icon files themselves (no new design)
  - the manifest
  - the service worker
  - the backend SPA fallback
- **Commits.** Commit after the task group. Do not push, tag, or open a PR.

## 1. Browser-tab icon

- [x] 1.1 In `frontend/src/install.test.ts`, add a failing test that reads `frontend/index.html`. It must find:
  - `<link rel="icon" type="image/svg+xml" href="/icon.svg">`
  - `<link rel="icon" type="image/png" sizes="192x192" href="/icon-192.png">`

  Match the attributes in any order. For each link, also check that the target exists in `public/`: `icon.svg` contains `<svg`, and `icon-192.png` starts with the PNG signature.

  Verify: the test fails before 1.2.
- [x] 1.2 In `frontend/index.html`, add the two `<link rel="icon">` tags next to the existing `apple-touch-icon` (`:7`).

  Verify:
  - The 1.1 test passes.
  - `npm test -- --run` and `npm run build` pass.
  - `dist/index.html` keeps both links.
- [x] 1.3 Record the commands and results in `docs/process/test-report-add-browser-tab-icon.md`, a new file. List the manual check that was not performed: opening the app in a browser tab and seeing the icon.

  Add your entry to `docs/process/ai-usage-log.md` after the latest entry, with a faithful prompt excerpt. For the session id, use the `session_id` that `droid exec -o json` reports, not any `CLAUDE_CODE_*` environment variable; if you cannot find it, leave it out.

  Verify: every command passes, and the report exists with the actual numbers.
