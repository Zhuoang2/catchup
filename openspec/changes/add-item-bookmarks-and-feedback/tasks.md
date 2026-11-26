# Tasks

Implementer notes:
- **Read first.** Read `proposal.md`, all of `design.md` (the Context with the probes, D1–D10, the user's decisions U1–U7 as recorded at plan approval, Risks, and Testing), and the spec deltas `specs/digest-history/spec.md`, `specs/user-interface/spec.md`, and `specs/x-accounts/spec.md`. If something looks wrong or contradictory, stop and report instead of redesigning.
- **Work test-first with the `tdd` skill** (D-016). In each group, first write the group's tests, run them, and watch each fail for the reason the task gives. Then change the code. The seams are named in each task, and they count as agreed. They are:
  - `TestClient(create_app(test_settings))`, the `test_settings` fixture of `backend/tests/conftest.py`, and `client.app.state.session_factory()`;
  - the Alembic `Config` and `command` pattern of `backend/tests/test_db.py:118-144`;
  - from `backend/tests/test_digest_runner.py`: `environment`, `seed`, `stub_collection`, `execute`, and `FakeModel` (its `calls` list holds `(messages, max_tokens)` for every call);
  - `seed_mixed_digest` in `backend/tests/test_x_settings_api.py:167-210`, and that module's `client` fixture;
  - `catchup.api.marks.utc_now`, monkeypatched to return fixed times;
  - in the frontend: `fetchMock` and `respond`, written like those of `frontend/src/pages/DigestView.test.tsx:7-23`; `MemoryRouter`; `expectAccessible`. In `frontend/src/pages/Home.test.tsx`: `mockPage`, `watchPollTimer`, and the pattern of `moves focus to run-bar Generate when the first digest replaces the Generate screen`.
- **Test rules:**
  - **No real network.** Tests touch no network, and no real keys.
  - **A held request.** To hold a request, return a pending promise from `fetchMock` for that path, and resolve it inside `act`.
  - **Request bodies.** Read them with `JSON.parse(options.body)` in the frontend.
  - **Change no existing test,** except for these edits, which are allowed:
    - `backend/tests/test_db.py`:
      - in `test_model_reasoning_migration_defaults_existing_config_and_downgrades`, change `command.upgrade(config, "head")` (line 133) to `command.upgrade(config, "0011_model_reasoning")`;
      - in `test_startup_migrates_database_and_enables_wal` (lines 150-154), add `"digest_item_marks"` to the expected set of table names;
      - in `test_migrations_live_inside_package`, add `assert (migrations / "versions" / "0012_digest_item_marks.py").is_file()` after line 186;
      - in lines 204, 373, 413, and 554 (numbered before any other edit), change the head revision `"0011_model_reasoning"` to `"0012_digest_item_marks"`.
    - `backend/tests/test_digest_history.py:357-362`, in `test_digest_detail_uses_snapshot_positions_and_survives_source_deletion`. Read the id of the "Saved first" row with `session.scalar(select(DigestItem.id).where(DigestItem.title == "Saved first"))`. The expected dict gains `"id"` (that value), `"bookmarked": False`, `"liked": False`, `"rating": None`, and `"note": None`.
    - `frontend/src/components/DigestArticle.test.tsx:11-14`: the fixture item gains `id: 11, bookmarked: false, liked: false, rating: null, note: null`.
    - `frontend/src/pages/DigestView.test.tsx`:
      - lines 76-78: the expected list becomes `['item-meta', 'item-title', 'item-body', 'item-actions']`;
      - lines 341-345: the expected list gains `'div.item-actions'` as the last entry, for all four articles.
    - `frontend/src/styles/tokens.test.ts`:
      - add `'item-actions'` to the class list in `targetsItemChild` (line 249);
      - in `places digest headings beside summaries only above 1100px`, after the loop at lines 287-290, add: `wideRule('.items > .item > .item-actions')` matches `/grid-column:\s*1\s*\/\s*span\s+3/` and `/grid-row:\s*3\s*;/`.
    - `frontend/src/App.test.tsx:11-16`: the `titles the %s screen` table gains `['/bookmarks', 'Bookmarks · CatchUp', <Bookmarks/>]`, with the import.
    - `frontend/src/pages/History.test.tsx:28`, in `shows saved digests with time, item and source counts and detail links`: replace `const links = await screen.findAllByRole('link')` with `await screen.findByRole('heading', { name: 'Archive' })` followed by `const links = Array.from(container.querySelectorAll<HTMLAnchorElement>('.history-list a'))`. The new Bookmarks link would otherwise be counted.
    - `frontend/src/pages/Home.test.tsx`: the main screen then has two status regions, the run's (`StatusRegion`, `id="run-status"`, `Home.tsx:342`) and the digest's. After the `respond` helper (line 9), add `const runStatus = () => document.getElementById('run-status') as HTMLElement`, and replace each `screen.getByRole('status')` (22 calls) with `runStatus()`. The one `await screen.findByRole('status')` (line 1097) stays: no digest is shown yet at that point. Do not share the run's region with the digest.

    If any other existing test fails because of this change, stop and report.
  - **Typed fixtures.** Digest fixtures passed straight to `DigestArticle` are type-checked by `npm run build` (`tsc --noEmit`). Write literal marks with `as const`, for example `rating: 'good' as const`, or `tsc` reports TS2322.
  - **Imports.** Adding names to a test module's imports is always allowed. Importing `DigestItemMark` or `catchup.api.marks` before they exist makes the module fail to collect; that is the expected failure.
- **Mutations.** For each named mutation, apply it alone, run the named tests, record the result, and restore the code exactly. Compare with `git diff` after restoring.
- **Environment:**
  - **Backend.** Run `uv run --offline pytest …` in `backend/`. Do not add, remove, or upgrade packages.
  - **Frontend and extension.** Use Node 22.17.1 with `export PATH="$HOME/.nvm/versions/node/v22.17.1/bin:$PATH"`. Then run `npm ci --offline --no-audit --no-fund` in `frontend/` (and in `extension/` for task 5.1). It installs the locked packages from the local npm cache. If it fails, stop and report. Do not change any `package.json` or `package-lock.json`.
- **Do not run** `docker build`, `scripts/docker-smoke.sh`, `docker system prune`, or any `docker` command, and do not touch port 8800. Claude Code runs Docker at review.
- **Out of scope.** Do not change:
  - digest generation (`backend/src/catchup/digest/`, `backend/src/catchup/llm/`, `backend/src/catchup/collection.py`);
  - `_extension_operation` in `main.py`;
  - Settings (`frontend/src/pages/Settings.tsx`);
  - the extension;
  - `scripts/docker-smoke.sh`.
- **Do not edit:**
  - `proposal.md`, `design.md`, or the spec deltas;
  - `docs/process/decision-log.md` or `docs/process/requirements-changes.md`. Claude Code wrote D-045 and the requirements row with the plan.
- **OpenSpec.** Prefix every OpenSpec CLI call with `DO_NOT_TRACK=1`.
- **Commits.** Commit after each task group. Do not push, tag, or open a PR. No secrets in code, tests, or commits.

## 1. Bookmark and Like, end to end (D1–D4, D6 toggles; digest-history "Bookmark, like, and rate digest items"; user-interface "Bookmark, like, and give feedback on digest items", "Digest reading layout")

- [x] 1.1 Write these backend tests and watch them fail. They fail because the table, the model, and `catchup.api.marks` do not exist, and because the digest answer has no `id`.

  **In `backend/tests/test_db.py`:**
  - **`test_item_marks_migration_creates_empty_table_and_downgrades`.** Upgrade to `0011_model_reasoning`. Insert, with SQL, one digest run, one digest, one topic, and one digest item, giving every NOT NULL column that has no server default. Read all `digest_items` rows as dicts. Then upgrade to `head`, and check:
    - `alembic_version` is `0012_digest_item_marks`;
    - `inspect(engine).get_columns("digest_item_marks")` names exactly `{"digest_item_id", "bookmarked_at", "liked_at", "rating", "note", "rated_at", "updated_at"}`;
    - `inspect(engine).get_foreign_keys("digest_item_marks")` is one key, from `["digest_item_id"]` to `digest_items` `["id"]`, with `options == {"ondelete": "CASCADE"}`;
    - the table has no rows, and the `digest_items` rows are unchanged.

    Downgrade to `0011_model_reasoning`. The table is gone, and the `digest_items` rows are unchanged.

  Also make the allowed edits to `test_db.py` listed in the notes.

  **In a new file `backend/tests/test_item_marks.py`.** Write a helper `seed_digest(client, *, created_at=None, language="en")`. It adds:
  - one source, with three stored `Item` rows in state `delivered`;
  - one `DigestRun` with its `Digest`, with `run.digest_id` set;
  - a `topic`-kind topic holding digest item A (title "Article A", summary "Summary A") and digest item B (title "Article B", `summary=None`, `summary_unavailable=True`);
  - a `creator_updates` topic holding digest item C (title "Episode C", `update_reason="no_transcript"`).

  Each digest item's `item_id` points at its own stored item. The helper returns a dict with the source id, the digest id, and the three digest item ids. Then write:
  - **`test_digest_answer_carries_unmarked_ids`.** In `GET /api/digests/{id}`, the topic's items have `id` equal to A's and B's ids, and `bookmarked` False, `liked` False, `rating` None, `note` None. `GET /api/digests/latest` equals the detail answer. Creator updates entries have no `id` key.
  - **`test_bookmark_and_like_are_saved_and_returned`.**
    - `PUT /api/digest-items/{A}/bookmark` answers 200 with `{"id": A, "bookmarked": True, "liked": False, "rating": None, "note": None}`.
    - `PUT …/{A}/like` answers with `bookmarked` and `liked` both True.
    - The digest answer then shows A bookmarked and liked, and B unmarked.
  - **`test_repeated_bookmark_keeps_its_first_time`.** Monkeypatch `catchup.api.marks.utc_now` with `lambda: next(times)`, where `times` yields `datetime(2026, 11, 25, 9, tzinfo=timezone.utc)`, then `… 10 …`, then `… 11 …`. Each request reads it once (design D3).
    - `PUT …/{A}/bookmark` twice: both answer 200. The row's `bookmarked_at` is 09:00, and its `updated_at` is 10:00.
    - `DELETE …/{A}/like` on the unliked item then answers 200, with `liked` False and `bookmarked` True.
  - **`test_removing_marks_keeps_an_empty_row`.** Bookmark and like A, then `DELETE …/bookmark`: the answer has `bookmarked` False and `liked` True. Then `DELETE …/like`: all marks are false or None. One `DigestItemMark` row for A still exists, with every mark column None.
  - **`test_unknown_item_and_creator_updates_are_refused`**, parametrized over `bookmark` and `like`, and over `PUT` and `DELETE`:
    - `/api/digest-items/999/<mark>` answers 404, code `not_found`, message "Digest item not found.";
    - `/api/digest-items/{C}/<mark>` answers 422, code `not_markable`, message "Items in Creator updates cannot be bookmarked or rated.".

    No `DigestItemMark` row exists afterwards.
  - **`test_unavailable_summary_can_be_bookmarked_and_liked`.** `PUT …/{B}/bookmark` and `PUT …/{B}/like` answer 200, with True.
  - **`test_marks_survive_source_deletion_and_restart`.** Bookmark and like A, then `DELETE /api/sources/{source id}`. The digest answer still shows A bookmarked and liked. A new `TestClient(create_app(test_settings))` on the same data directory shows the same.
  - **`test_cross_site_and_extension_token_cannot_mark`.**
    - `PUT …/{A}/bookmark` with the header `Origin: http://localhost:3000` answers 403 `cross_site_request`.
    - With `Authorization: Bearer <token>`, where the token comes from `POST /api/settings/extension-tokens` with `{"name": "Chrome"}`, it also answers 403 `cross_site_request`.
    - A is unmarked afterwards.
  - **`test_digest_answer_loads_marks_in_one_query`.** Bookmark A and like B. Record the statements of `GET /api/digests/{id}` with `event.listen(engine, "before_cursor_execute", …)`, as `backend/tests/test_digest_history.py:255-283` does. Exactly one recorded statement contains `FROM digest_item_marks`.

  **In `backend/tests/test_digest_history.py`,** make the allowed edit.
- [x] 1.2 Implement design D1–D4 for bookmarks and likes:
  - `DigestItemMark` in `models.py`;
  - the migration `0012_digest_item_marks.py` (D2), with its docstring;
  - `item_answer` and the marks query in `api/digests.py`;
  - `api/marks.py`, with `utc_now` imported into its namespace, the four bookmark and like endpoints, and the insert-or-ignore write of D1;
  - the router included in `main.py`.

  Run `uv run --offline pytest` in `backend/`. Everything passes.
- [x] 1.3 Run these backend mutations one at a time, and record which tests fail:
  - **M1:** the migration's foreign key without `ondelete="CASCADE"`. Expect `test_item_marks_migration_creates_empty_table_and_downgrades` to fail.
  - **M2:** `downgrade()` does nothing. Expect the same test to fail.
  - **A1:** `PUT …/bookmark` always sets `bookmarked_at = utc_now()`. Expect `test_repeated_bookmark_keeps_its_first_time` to fail.
  - **A2:** the `creator_updates` check removed. Expect `test_unknown_item_and_creator_updates_are_refused` to fail.
  - **A3:** `item_answer` always returns `"bookmarked": False`. Expect `test_bookmark_and_like_are_saved_and_returned` to fail.
  - **A4:** the marks loaded with one query per item. Expect `test_digest_answer_loads_marks_in_one_query` to fail.
  - **A5:** `DELETE …/like` deletes the row when no mark is left. Expect `test_removing_marks_keeps_an_empty_row` to fail.
  - **A6:** `_extension_operation` also accepts `PUT` on paths starting with `/api/digest-items/`. Expect `test_cross_site_and_extension_token_cannot_mark` to fail.
- [x] 1.4 In `frontend/src/components/DigestArticle.test.tsx`, make the allowed fixture edit. Then write these tests and watch them fail, because there are no controls.

  The tests use a `fetchMock` stubbed with `vi.stubGlobal('fetch', …)`, and a digest whose topic holds item 11 ("Article", with a summary) and item 12 ("Missing", `summary: null`, `summary_unavailable: true`), and whose Creator updates hold one entry.
  - **`shows Bookmark and Like on topic items and Feedback only with a summary`.**
    - Item 11's article has, as its last child, `div.item-actions`, holding buttons named "Bookmark Article", "Like Article", and "Feedback on Article", in that order. Bookmark and Like have `aria-pressed="false"`, and Feedback has `aria-expanded="false"`.
    - Item 12 has "Bookmark Missing" and "Like Missing", and no Feedback button.
    - The Creator updates section has no button.
    - `expectAccessible(container)` passes.
  - **`starts from the saved marks`.** With item 11 `bookmarked: true, liked: true, rating: 'good' as const`:
    - Bookmark and Like have `aria-pressed="true"`, and each contains an `svg` (the check icon);
    - the text "Rated good" follows the Feedback button inside `.item-actions`.

    In `shows Bookmark and Like on topic items and Feedback only with a summary`, the unpressed toggles contain no `svg`.
  - **`does not carry an item's marks into the next digest`.** Render digest No. 7 with item 11 ("Article", unmarked). Then `rerender` with digest No. 8, whose one item has id 81, the same title "Article", and `bookmarked: true`. "Bookmark Article" has `aria-pressed="true"`.
  - **`keeps an empty status region on the page`.** The article's section contains one `[role="status"]` with empty text, before any click.
  - **`bookmarks an item once the server saves it`.**
    - Hold `PUT /api/digest-items/11/bookmark`. Focus "Bookmark Article" and click it. While the request is held:
      - the button has `aria-disabled="true"` and `aria-pressed="false"`, and keeps focus;
      - a second click sends no second request;
      - the call was `('/api/digest-items/11/bookmark', { method: 'PUT' })`.
    - Resolve the request with `respond({ id: 11, bookmarked: true, liked: false, rating: null, note: null })`. Then `aria-pressed` is `"true"`, `aria-disabled` is absent or `"false"`, and the status region reads "Bookmarked.".
    - Click again. The request is `DELETE` on the same path, answered with `bookmarked: false`. Then `aria-pressed` is `"false"`, and the status region reads "Bookmark removed.".
  - **`likes and unlikes an item`.** The same for "Like Article", `/api/digest-items/11/like`, "Liked.", and "Like removed.". Then like it again, with the request held: while it is held, the status region is empty, so that the next "Liked." is announced again. After it resolves, the region reads "Liked.".
  - **`shows the server's message and keeps the state when a change fails`.** `PUT …/11/bookmark` answers `respond({ error: { code: 'not_found', message: 'Digest item not found.' } }, 404)`. Then:
    - a `role="alert"` inside item 11's `.item-actions` reads "Digest item not found.";
    - `aria-pressed` stays `"false"`;
    - the status region is empty.

  Make the allowed edits to `frontend/src/pages/DigestView.test.tsx` and `frontend/src/styles/tokens.test.ts`, and watch them fail.
- [x] 1.5 Implement design D6 for Bookmark and Like:
  - the `DigestItem` and `Marks` types;
  - `ItemActions`, keyed by `` `${digest.id}-${item.id}` ``;
  - the status region, the busy rule, and the error;
  - the CSS in `components.css`, and the one new rule inside `@container (width > 1100px)` in `layout.css`.

  Render the Feedback button with `aria-expanded="false"`; its panel comes in group 2. In `frontend/`, run `npm test -- --run` and `npm run build`. Both pass.
- [x] 1.6 Run these frontend mutations one at a time, and record which tests fail:
  - **U1:** set `bookmarked` from the click before the answer. Expect `bookmarks an item once the server saves it` to fail.
  - **U2:** no busy guard. Expect the same test to fail on the second request.
  - **U3:** announce "Saved." instead of "Bookmarked.". Expect the same test to fail.
  - **U4:** the error not shown. Expect `shows the server's message and keeps the state when a change fails` to fail.
  - **U5:** `.item-actions` rendered before the body. Expect `DigestView.test.tsx`'s two order tests and `shows Bookmark and Like on topic items and Feedback only with a summary` to fail.
  - **U6:** the wide `.item-actions` rule removed. Expect `places digest headings beside summaries only above 1100px` to fail.
  - **U7:** the sr-only title removed from Bookmark. Expect `shows Bookmark and Like on topic items and Feedback only with a summary` to fail.
  - **U11:** `ItemActions` rendered without its `key`. Expect `does not carry an item's marks into the next digest` to fail.
  - **U12:** the status region not cleared when a change starts. Expect `likes and unlikes an item` to fail.
  - **U13:** the check icon left out of pressed toggles. Expect `starts from the saved marks` to fail.

## 2. Feedback, end to end (D3 feedback, D6 panel; digest-history "Bookmark, like, and rate digest items"; user-interface "Bookmark, like, and give feedback on digest items")

- [x] 2.1 In `backend/tests/test_item_marks.py`, write these tests and watch them fail, because there is no feedback endpoint (405 or 404).
  - **`test_feedback_is_saved_stripped_and_replaced`.** Bookmark A. Then:
    - `PUT …/{A}/feedback` with `{"rating": "poor", "note": "  Misses the price  "}` answers `rating` "poor" and `note` "Misses the price";
    - `PUT` with `{"rating": "good"}` answers `rating` "good" and `note` None;
    - `PUT` with `{"rating": "good", "note": "   "}` answers `note` None;
    - `DELETE …/{A}/feedback` answers `rating` None and `note` None, with `bookmarked` still True. The row's `rated_at` is None.
  - **`test_note_of_500_characters_after_trimming_is_kept`.** `{"rating": "good", "note": " " + "x" * 500 + " "}` answers 200, with a note of length 500.
  - **`test_invalid_feedback_changes_nothing`.** First save `{"rating": "poor", "note": "Earlier"}`. Then, parametrized:
    - `{"rating": "excellent"}`: 422 `invalid_feedback`, "Choose Good or Poor for the summary.";
    - `{"rating": "good", "note": "x" * 501}`: 422 `invalid_feedback`, "Keep the note to 500 characters or fewer.";
    - `{"rating": 1}`: 422 `invalid_request`;
    - `{"note": "x"}`: 422 `invalid_request`.

    After each refusal, the digest answer still shows "poor" and "Earlier".
  - **`test_feedback_needs_a_markable_item_with_a_summary`.** Every request sends `{"rating": "good"}`; without a valid body, FastAPI answers 422 `invalid_request` before the item checks.
    - `PUT …/{B}/feedback` answers 422 `no_summary`, "This item has no summary to rate.".
    - `PUT …/{C}/feedback` answers 422 `not_markable`.
    - `PUT …/999/feedback` answers 404 `not_found`.
  - **`test_marks_are_not_sent_to_the_model`.**
    - In the `environment` fixture of `backend/tests/test_digest_runner.py`, with `stub_collection`, `seed(environment, count=2)` and `execute(environment)`.
    - Rate the first saved digest item Poor with the note "NOTE-MARKER-41", and bookmark and like it.
    - Add one new pending `Item` to the first source, set `model = FakeModel()` and `environment.app.state.model_client_factory = lambda *_: model`, and run `execute(environment)` again.
    - The run's status is `succeeded`. No message content in `model.calls` contains "NOTE-MARKER-41".

    This test passes once the feedback endpoint exists; mutation A10 shows that it can fail.
- [x] 2.2 Implement the feedback endpoints of D3, with `FeedbackInput`. Run `uv run --offline pytest`; it passes.
- [x] 2.3 Run these mutations one at a time, and record which tests fail:
  - **A7:** the note stored without `strip()`. Expect `test_feedback_is_saved_stripped_and_replaced` to fail.
  - **A8:** the length checked before `strip()`. Expect `test_note_of_500_characters_after_trimming_is_kept` to fail.
  - **A9:** the `no_summary` check removed. Expect `test_feedback_needs_a_markable_item_with_a_summary` to fail.
  - **A10:** in `backend/src/catchup/digest/runner.py`, where the run builds each item's summary input, append the text of every `DigestItemMark.note` to the item's content. This is a temporary edit for the mutation only, the one allowed exception to "Out of scope"; restore it exactly. Expect `test_marks_are_not_sent_to_the_model` to fail.
  - **A11:** `PUT …/feedback` without a note keeps the old note. Expect `test_feedback_is_saved_stripped_and_replaced` to fail.
- [x] 2.4 In `frontend/src/components/DigestArticle.test.tsx`, write these tests and watch them fail, because Feedback opens nothing.
  - **`opens the feedback panel with the saved rating and note`.** Item 11 has `rating: 'poor', note: 'Earlier note'`. Click "Feedback on Article". Then:
    - the button has `aria-expanded="true"`, and keeps focus;
    - a group named "Feedback on Article" holds `getByRole('group', { name: 'How was this summary?' })` (the fieldset), whose radios are "Poor", checked, and "Good", not checked;
    - a textbox named "Note (optional)" has the value "Earlier note", `maxLength` 500, and the accessible description "Only kept in CatchUp. Up to 500 characters.";
    - the panel's buttons are exactly "Save feedback", "Remove feedback", and "Cancel";
    - `expectAccessible` passes.
  - **`saves rating and note together and returns focus to Feedback`.** Item 11 is unrated. Open the panel: its buttons are exactly "Save feedback" and "Cancel". Choose "Good", and type "Clear" in the note. Hold `PUT /api/digest-items/11/feedback`, and click "Save feedback".
    - While it is held: the request body is `{ "rating": "good", "note": "Clear" }`, and "Save feedback" has `aria-disabled="true"`.
    - Resolve the request with `{ id: 11, bookmarked: false, liked: false, rating: 'good', note: 'Clear' }`. Then the panel is gone, "Feedback on Article" has focus and `aria-expanded="false"`, "Rated good" follows it, and the status region reads "Feedback saved.".
  - **`asks for a rating before saving`.** Open the unrated panel, and click "Save feedback". Then:
    - `fetchMock` was not called;
    - "Choose Good or Poor." is shown, with `role="alert"`;
    - both radios have `aria-invalid="true"` and the accessible description "Choose Good or Poor.".
  - **`removes feedback`.** Item 11 is rated "good". Open the panel, and click "Remove feedback". The request is `DELETE` on `/api/digest-items/11/feedback`, answered with `rating: null, note: null`. Then the panel is gone, Feedback has focus, no "Rated" text is shown, and the status region reads "Feedback removed.".
  - **`cancel closes the panel without a request`.** Item 11 is rated "poor". Open the panel, choose "Good", and click "Cancel". `fetchMock` was not called, and Feedback has focus. Reopen the panel: "Poor" is checked.
  - **`keeps the panel open with the error when saving fails`.** `PUT …/feedback` answers 422 with message "This item has no summary to rate.". The panel stays open, an alert in item 11's `.item-actions` shows that message, and no "Rated" text is added.
- [x] 2.5 Implement the panel of D6. The panel's `panelId` is `` `feedback-${item.id}` `` (the digest item id), not React's `useId`: `Home.test.tsx` "shows the same digest reading markup on Home and the saved digest page" compares the two pages' `outerHTML`, and `useId` values differ between the two renders. The ids built from `panelId` stay as they are. Run `npm test -- --run` and `npm run build` in `frontend/`; they pass.
- [x] 2.6 Run these mutations one at a time, and record which tests fail:
  - **U8:** focus not moved back to Feedback after a save. Expect `saves rating and note together and returns focus to Feedback` to fail.
  - **U9:** Save feedback without a rating sends the request. Expect `asks for a rating before saving` to fail.
  - **U10:** Remove feedback shown also without a saved rating. Expect `saves rating and note together and returns focus to Feedback` to fail.

## 3. Bookmarks list and screen (D5, D7, D8; digest-history "List bookmarked items"; user-interface "Bookmarks screen")

- [x] 3.1 In `backend/tests/test_item_marks.py`, write these tests and watch them fail, because `GET /api/bookmarks` is a 404.
  - **`test_bookmarks_list_newest_first_with_digest`.**
    - Seed two digests with `seed_digest`: No. 1, with `language="zh-Hans"`, and No. 2.
    - With `utc_now` monkeypatched to 09:00 and then 10:00, bookmark No. 1's item A, then No. 2's item A.
    - `GET /api/bookmarks` lists No. 2's item first.
    - The second entry equals exactly the digest answer's entry for No. 1's item A, with `bookmarked` True, plus `"bookmarked_at"` (09:00 as the API serializes times) and `"digest": {"id": 1, "created_at": <No. 1's created_at>, "language": "zh-Hans"}`.
  - **`test_bookmarks_list_breaks_ties_by_higher_id`.** With `utc_now` fixed, bookmark A, then B, of one digest. B comes first.
  - **`test_bookmarks_list_holds_only_bookmarked_items`.**
    - With nothing marked, the list is `[]`.
    - Like A and rate it: still `[]`.
    - Bookmark A and B, then remove B's bookmark: only A is listed.
  - **`test_bookmarks_list_filters_images_like_the_digest`.** Item A has `images` `[{"url": "http://192.168.1.2/a.png", "alt": "Local"}, {"url": "https://cdn.example/b.png", "alt": "Chart"}]`. Once A is bookmarked, its entry's `images` is only the second image.
- [x] 3.2 Implement D5. Run `uv run --offline pytest`; it passes.
- [x] 3.3 Run these mutations one at a time, and record which tests fail:
  - **B1:** order by `bookmarked_at` ascending. Expect `test_bookmarks_list_newest_first_with_digest` to fail.
  - **B2:** filter on `liked_at` instead of `bookmarked_at`. Expect `test_bookmarks_list_holds_only_bookmarked_items` to fail.
  - **B3:** the entry built without `item_answer`'s image filter. Expect `test_bookmarks_list_filters_images_like_the_digest` to fail.
- [x] 3.4 Write these frontend tests and watch them fail, because there is no Bookmarks page, route, or link.

  **In a new file, `frontend/src/pages/Bookmarks.test.tsx`.** Render `<MemoryRouter initialEntries={['/bookmarks']}><Routes><Route path="/bookmarks" element={<Bookmarks/>}/></Routes></MemoryRouter>`. `fetchMock` answers:
  - `/api/bookmarks` with two entries: id 21, from digest No. 5 (`language: null`), and id 22, from digest No. 3 (`language: 'zh-Hans'`);
  - `/api/settings/preferences` with `{ show_images: true }`.

  Tests:
  - **`lists bookmarked items with their digest link`.**
    - `document.title` is "Bookmarks · CatchUp", and the heading level 1 is "Bookmarks".
    - The first article holds:
      - the title link "<entry 21 title> (opens the original)";
      - its summary;
      - a link with the text "No. 5 · <shortDate of No. 5's created_at>", whose `href` is `/digests/5`, inside a paragraph starting "From";
      - "Bookmark <title>", with `aria-pressed="true"`.
    - The second entry's `div.summary` (rendered by `SummaryText`) has `lang="zh-Hans"`.
    - `expectAccessible` passes.
  - **`keeps an entry after its bookmark is removed`.** Before any click, the page's section holds one empty `[role="status"]`. Click Bookmark on the first entry. `DELETE /api/digest-items/21/bookmark` answers with `bookmarked: false`. The entry is still listed, its Bookmark has `aria-pressed="false"` and keeps focus, and that status region reads "Bookmark removed.".
  - **`shows the empty state`.** `/api/bookmarks` answers `[]`. The page shows the heading "No bookmarks yet", and the link "Open the latest digest", whose `href` is `/`.
  - **`hides images when they are turned off`.** The preferences answer `{ show_images: false }`, and entry 21 has one image. The page shows no `img`.
  - **`reports a load error`.** `/api/bookmarks` answers 500 with `{ error: { code: 'x', message: 'Could not load.' } }`. The page shows an alert "Could not load.".

  **In `frontend/src/pages/History.test.tsx`:**
  - **`links to Bookmarks`.** Both with saved digests and with none, a link "Bookmarks" with `href` `/bookmarks` is in the page head.

  **In `frontend/src/App.test.tsx`,** inside `describe('navigation')`:
  - **`marks History current on the Bookmarks screen`.** `shell('/bookmarks')`:
    - the navigation's links are still `['Latest', 'Sources', 'History', 'Settings']`;
    - History has `aria-current="page"`;
    - `.app` has `data-screen="bookmarks"`. This is the effective check of the full masthead, which the CSS keys on `data-screen`;
    - `.masthead-line time` is present. jsdom applies no CSS, so this checks presence only.

  Make the allowed edit to the title table.
- [x] 3.5 Implement D7 and D8:
  - `ItemContent`, shared by `DigestArticle` and `Bookmarks.tsx`. It also takes `headingLevel` (`2 | 3`, default `3`) for the item title: `DigestArticle` keeps `h3` under its topic `h2`s, and `Bookmarks.tsx` passes `2`, because the Bookmarks screen has no `h2` between its `h1` and the item titles (axe `heading-order` fails otherwise). The title keeps its `item-title` class, so it looks the same; a Bookmarks test that names a heading level uses 2;
  - `Bookmarks.tsx`;
  - the route in `App.tsx`;
  - the screen mapping in `AppShell.tsx`;
  - the link in `History.tsx`;
  - the `.bookmark-list` CSS.

  Run `npm test -- --run` and `npm run build`. Both pass.
- [x] 3.6 Run these mutations one at a time, and record which tests fail:
  - **B4:** on the Bookmarks screen, removing a bookmark drops the entry. Expect `keeps an entry after its bookmark is removed` to fail.
  - **B5:** `AppShell` maps `/bookmarks` to `latest`. Expect `marks History current on the Bookmarks screen` to fail.
  - **B6:** the summary rendered without its digest's `lang`. Expect `lists bookmarked items with their digest link` to fail.

## 4. X deletion, main-screen focus, and README (D1, D9, D10; x-accounts "Delete all X data"; user-interface "Bookmark, like, and give feedback on digest items")

- [ ] 4.1 Write these tests.

  **In `backend/tests/test_x_settings_api.py`:**
  - **`test_delete_all_x_data_removes_marks_on_x_items_only`.** It passes once group 1 is done; mutation M3 shows that it can fail.
    - Save the X token, as the existing delete-all tests do, and `seed_mixed_digest(client)`.
    - Read the ids of the "X title" and "Feed" digest items.
    - Bookmark, like, and rate the X item Poor with the note "about the post". Bookmark the feed item.
    - `POST /api/settings/x/delete-all` answers 200.
    - Afterwards, the only `DigestItemMark` row belongs to the feed item, with `bookmarked_at` set. `GET /api/bookmarks` lists only "Feed".

  **In `frontend/src/pages/Home.test.tsx`:**
  - **`moves focus to run-bar Generate when a new digest replaces the shown one while an item control has focus`.**
    - Follow the pattern of `moves focus to run-bar Generate when the first digest replaces the Generate screen`, with `vi.useFakeTimers({ shouldAdvanceTime: true })` and `watchPollTimer`.
    - Use `mockPage` with `latest` set to a digest No. 7, whose one topic item has `id: 71` and unmarked marks, and `detail` set to digest No. 8 with item `id: 81`.
    - Focus "Like <item title>" of No. 7, start a run, and let it succeed with `digest_id: 8`.
    - Once No. 8 is shown, the run bar's "Generate digest" has focus.

    It fails before D9.

  **In a new file, `backend/tests/test_readme_marks.py`:**
  - **`test_readme_describes_bookmarks_and_their_privacy`.** In the README, with whitespace collapsed as `test_readme_providers.py` does, check two things:
    - the intro contains "bookmarked items are listed under Bookmarks, linked from History";
    - the Privacy section contains "They are never sent to the model provider, and they do not change later digests.".

    It fails before D10.
- [ ] 4.2 Implement D9 in `Home.tsx` and D10 in `README.md`. Run the backend and frontend suites; they pass.
- [ ] 4.3 Run these mutations one at a time, and record which tests fail:
  - **M3:** `DigestItemMark.digest_item_id`'s foreign key, in the model and in the migration, without `ondelete="CASCADE"`. Each test builds its database through the migration. Expect `test_delete_all_x_data_removes_marks_on_x_items_only` to fail, with an integrity error or a 500.
  - **H1:** the D9 line removed. Expect the Home test above to fail.
  - **Doc:** the Privacy sentence removed. Expect `test_readme_describes_bookmarks_and_their_privacy` to fail.

## 5. Checks and report

- [ ] 5.1 Run these checks and keep their output for the final report:
  - in `backend/`: `uv run --offline pytest`;
  - in `frontend/`: `npm test -- --run` and `npm run build`;
  - in `extension/`: `npm ci --offline --no-audit --no-fund`, then `npm test -- --run` and `npm run build`. The extension is unchanged; this matches CI;
  - `DO_NOT_TRACK=1 openspec validate add-item-bookmarks-and-feedback --strict`;
  - `git diff --check`.

  All pass.
- [ ] 5.2 Write `docs/process/test-report-add-item-bookmarks-and-feedback.md`. It holds:
  - the commands of 5.1, with their counts;
  - every mutation (M1–M3, A1–A11, U1–U13, B1–B6, H1, Doc), with the tests that failed;
  - any deviation from this plan.
- [ ] 5.3 Add one Droid entry for this run to `docs/process/ai-usage-log.md`, after the latest entry, in the format of the Droid entry for `add-reasoning-setting`. It holds:
  - the prompt (a verbatim excerpt in quotation marks);
  - the tool and model;
  - the outcome;
  - what failed and how it was handled.

  Leave the session line (session id, turns, minutes) to Claude Code.
