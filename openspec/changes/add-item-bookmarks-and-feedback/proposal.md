# Proposal

## Why

The proposal promised "bookmarks, likes, and feedback once the core workflow for collecting content and generating digests is functional" (`docs/proposal.md:42`, handoff §3 step 6, requirements change "before 2026-10-01"). The core flow is done, but a reader still cannot keep an item for later, say that they liked it, or say that a summary was good or poor (#8). Summary feedback is also the first real-user signal on summary quality that #10 can start from.

## What Changes

This describes the recommended option of each decision point U1–U7 in `design.md`.

- **Marks on digest items.** Each summarized item in a saved digest (an item in one of its topics, also when its summary is unavailable) gets three controls after its summary:
  - **Bookmark**, a toggle;
  - **Like**, a toggle, with no negative counterpart;
  - **Feedback**, which opens a small panel: "How was this summary?" Good or Poor, an optional note of up to 500 characters, then **Save feedback**, **Remove feedback**, or **Cancel**. Items whose summary is unavailable get Bookmark and Like only.

  Creator updates have no controls. The marks belong to the item as it appears in that digest. An item is delivered in one digest only, so it never collects marks in two places.
- **Bookmarks screen** at `/bookmarks`, linked from History. It lists bookmarked items, newest bookmark first, as their digest saved them: source, title, summary, images, and "Also read", with a link to their digest ("From No. 12 · 3 Oct 2026"). Their controls work there too. An item whose bookmark is removed there stays listed, unpressed, until the screen is opened again. The navigation keeps its four items, and History is marked current on the Bookmarks screen.
- **Record only.** Marks change nothing in later runs. Nothing about them is sent to the model provider. #10 decides how to export ratings and notes.
- **Removal.** Marks are removed with their digest item: by **Delete all X data** for X items, and when a digest is left empty. Deleting a source keeps its saved digest items, and therefore their marks.
- **Accessibility.**
  - The toggles use `aria-pressed`. Each control's name includes the item's title.
  - A control stays focusable and is announced as unavailable while its request runs.
  - Results are announced through a status region, and errors as alerts.
  - Closing the panel returns focus to Feedback.
  - When a new digest replaces the one on the main screen while one of its controls has focus, focus moves to Generate.
- **API.**
  - `PUT` and `DELETE` on `/api/digest-items/{id}/bookmark`, `/like`, and `/feedback`; each answers with the item's marks.
  - `GET /api/bookmarks`.
  - The digest answers (`/api/digests/{id}`, `/api/digests/latest`) give each topic item its `id`, `bookmarked`, `liked`, `rating`, and `note`.
- **Data.** A new table `digest_item_marks` (migration `0012_digest_item_marks`), one row per marked digest item.
- **README.** The intro names bookmarks and feedback. Privacy says that marks and notes stay in the local database and are never sent to the model provider.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `digest-history`: new requirements "Bookmark, like, and rate digest items" (what can be marked, how marks are stored, returned, validated, and removed) and "List bookmarked items". No existing requirement text changes.
- `user-interface`: new requirements "Bookmark, like, and give feedback on digest items" (the controls, the feedback panel, names, busy state, announcements, and focus) and "Bookmarks screen". Two requirements are modified:
  - "Digest reading layout": each summarized item also shows its controls, after its summary when stacked, and under its title in windows wider than 1100 px;
  - "Keyboard and screen-reader support": focus still stays put when a new digest replaces the shown one, except when it is on a control of an item in the replaced digest. It then moves to Generate, and the "Run finishes" scenario says so.
- `x-accounts`: "Delete all X data" is modified: it also removes the bookmarks, likes, ratings, and notes on the X items it deletes.

## Impact

- **Backend.**
  - `backend/src/catchup/models.py`: a new `DigestItemMark` model.
  - A new migration, `backend/src/catchup/migrations/versions/0012_digest_item_marks.py`.
  - `backend/src/catchup/api/digests.py`: an item serializer shared with the bookmarks list; the marks in the digest answers.
  - A new module, `backend/src/catchup/api/marks.py`: the six mark endpoints and `GET /api/bookmarks`. It is registered in `backend/src/catchup/main.py`.
- **Frontend.**
  - `frontend/src/components/DigestArticle.tsx`: a new `ItemActions` component and the article's status region.
  - A new page, `frontend/src/pages/Bookmarks.tsx`, and its test.
  - `frontend/src/App.tsx`, `frontend/src/components/AppShell.tsx`, and `frontend/src/pages/History.tsx`.
  - `frontend/src/pages/Home.tsx`: focus when a new digest replaces the shown one.
  - `frontend/src/styles/layout.css` and `frontend/src/styles/components.css`.
- **Tests changed.**
  - `backend/tests/test_db.py`: head revision, the migration list, and the table set at startup.
  - `backend/tests/test_digest_history.py`: the pinned item answer.
  - `frontend/src/components/DigestArticle.test.tsx`: the typed fixture.
  - `frontend/src/pages/DigestView.test.tsx`: two item-children orders.
  - `frontend/src/styles/tokens.test.ts`: the wide-layout guard.
  - `frontend/src/pages/History.test.tsx`: one test that counted every link.
  - `frontend/src/pages/Home.test.tsx`: the run's status region is found by its id, because the main screen gains a second status region.
  - `frontend/src/App.test.tsx`: the title table.
- **Docs.** `README.md`.
- **API.** New endpoints, and new fields in the digest answers. Clients that ignore the new fields keep working. The cross-site write rule covers the new writes, and the browser extension may not call them.
- **No new dependencies.** **Not changed:** digest generation, prompts, the extension, Settings, `scripts/docker-smoke.sh` (it pins no digest answer).
