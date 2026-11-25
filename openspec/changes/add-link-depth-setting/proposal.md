# Proposal

## Why

Since #48 (D-020), every run reads up to 8 related linked pages per item and the author's replies on the post page, within 60 context requests per run. Only environment settings change these numbers (`backend/src/catchup/config.py:99-101`), so a user who wants faster runs or fewer tokens has to edit the server's environment and restart it. When the user chose #48's design on 2026-10-19, they asked for a later choice between deep and shallow reading (translated: "later we can give users the option to choose deep or shallow crawling"). Issue #54 tracks that choice. D-036 deferred it again for #64.

## What Changes

- **A "Linked pages" choice in Settings**, in the Digest group: **Off**, **Shallow**, or **Normal** (the default). It is stored with the other Digest settings (`app_settings.link_depth`, migration `0010_link_depth`).
  - **Normal** is today's behavior: up to `CATCHUP_LINKS_PER_ITEM` links per item (default 8), and author replies.
  - **Shallow** reads up to 3 links per item, or `CATCHUP_LINKS_PER_ITEM` when that is lower, and author replies.
  - **Off** makes no context request at all: no linked page, post page, comment feed, or robots.txt. Replies saved with a page from the browser, or kept from a followed X account's thread, need no request and are still used. Other items are left not gathered, so a later run that still finds them pending reads them at the level then chosen.
  - Every level keeps the per-run limit `CATCHUP_CONTEXT_FETCHES_PER_RUN` (default 60), the 3,000-character cut per page, the 16,000-character cap per item, robots.txt, and `CATCHUP_AUTHOR_REPLIES`.
- **The run reads the level once, when it starts**, like the digest language. A change during a run applies to the next run. Items already gathered keep their context.
- **The cost is shown next to the choice.** Each option names how many pages per item it reads, with the server's numbers. A note says that each page read adds time to the run and up to 3,000 characters to that item's summary request, which uses more tokens, and names the per-run limit.
- **The preferences API** (`GET`/`PUT /api/settings/preferences`) gains `link_depth`, and the `GET` answer gains the read-only numbers `link_depth_pages` and `context_fetches_per_run`. An unknown level is refused with `invalid_link_depth`.
- **Deep is not in this change.** It is decision point U1 in `design.md`: the recommendation keeps #54 open for a Deep level designed on its own (the PR says "Part of #54"). Option B adds a Deep level without a model call to this change; option C adds #48's model-picked links.
- README: the Settings choice, and what the environment settings now mean.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `content-collection`: new requirement "Choose how many linked pages a run reads" (the three levels, Off, and the level read once per run). "Gather related context for website items" now gathers at the run's level, and its author replies apply at every level except Off.
- `user-interface`: new requirement "Choose linked pages in Settings" (the Digest group's choice, its numbers, and its cost note).

## Impact

- Code:
  - `backend/src/catchup/models.py` (`AppSettings.link_depth`), `backend/src/catchup/migrations/versions/0010_link_depth.py`;
  - `backend/src/catchup/context/depth.py` (new: the levels and `context_limits`), `backend/src/catchup/context/links.py` (`related_links` returns nothing for a limit of 0), `backend/src/catchup/context/gather.py` (`gather_context` takes the level);
  - `backend/src/catchup/digest/runner.py` (reads the level with the digest language);
  - `backend/src/catchup/api/settings.py` (preferences);
  - `frontend/src/pages/Settings.tsx`.
- Tests: `backend/tests/test_db.py`, `test_context_links.py`, `test_context_depth.py` (new), `test_context_gather.py`, `test_settings_api.py`, `test_readme_context.py`; `frontend/src/pages/Settings.test.tsx`.
- Docs: `README.md`, decision log (D-042), requirements-changes table, a test report, the AI usage log.
- Shared with the other changes planned at the same time: #4 (`add-reasoning-setting`) may also add migration `0010` and edit `api/settings.py`, `models.py`, and `Settings.tsx` (its Model provider group). See `design.md` "Risks".
- Out of scope: the Deep level (U1), a per-run limit per level, removing or renaming the environment settings, the browser extension, the progress formula (D-036), and any change to how context is used in summaries.
