# Proposal

## Why

Reading the digest is CatchUp's main activity, but the main screen (`/`, Generate) shows only the run controls and side information. After a run, the user has to open the digest from "View digest" or from History. Issue #27, raised by the user after the UI redesign's manual test, asks that the main screen show the latest digest.

## What Changes

- **The main screen becomes the front page.** `/` shows the newest saved digest in the existing reading layout, with no further click needed.
  - A compact run bar sits above the digest. It holds Generate, the number of sources, and, during and after a run, the current run's progress, per-source outcomes, and result.
  - While a run is active, or after it ends with no new content or fails, the shown digest stays visible.
  - When the run saves a digest, the new digest replaces the shown one in place. Keyboard focus does not move, and the status region announces it as it does today.
  - When no digest has been saved yet, `/` keeps today's Generate guidance: first run, no sources yet, or "Generate digest" with the rail.
- **The finished-digest state has no primary action.** "View digest" is removed, because the digest is already on screen.
- **No side rail when a digest is shown.** The reading layout uses the full width, and the source count moves into the run bar.
- **Navigation and titles.**
  - The first navigation item is renamed from "Generate" to "Latest" and still points to `/`.
  - The document title on `/` is "Latest · No. {id} · CatchUp" when a digest is shown, and "Latest · CatchUp" otherwise.
  - `/` keeps the full masthead with the date; saved digests opened from History keep the compact masthead.
- **New API endpoint:** `GET /api/digests/latest` returns the newest saved digest in the same shape as `GET /api/digests/{id}`, or JSON `null` when none is saved. The main screen no longer requests the full digest list.
- **Out of scope:**
  - The single-item topic layout (#25), which stays a separate change.
  - Keeping the last run's outcome across a reload.

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- `user-interface`: a new requirement for the main screen showing the latest digest. Changes to "Digest reading layout" (masthead on the main screen), "One primary action per state" (no "View digest"), "Side information reflects the state" (no rail beside a shown digest), and "Keyboard and screen-reader support" (main-screen title; the digest replaced without moving focus).
- `digest-history`: a new requirement to open the latest digest with a single request.

## Impact

- **Backend.** `backend/src/catchup/api/digests.py` gets a new `latest` route, declared before `/{digest_id}`, reusing the detail serialization. New tests go in `backend/tests/test_digest_history.py`. No schema change and no migration.
- **Frontend.**
  - The reading layout moves from `frontend/src/pages/DigestView.tsx` (`DigestBody`) into a shared exported component.
  - `frontend/src/pages/Generate.tsx` and its tests become the main-screen page.
  - Also changed: `frontend/src/App.tsx` (route), `frontend/src/components/AppShell.tsx` (nav label, `data-screen`, `aria-current`), and `frontend/src/styles/*.css` (run bar inside the digest grid).
  - Tests: `frontend/src/App.test.tsx` and `frontend/src/pages/DigestView.test.tsx`.
- **Docs.** README wording that refers to the Generate screen.
- **No change to runs**, the service worker, the PWA manifest (`start_url` stays `/`), or Docker packaging.
