# Tasks

Implementer notes:
- **Read first.** Read `proposal.md`, `design.md` (all of "Context", the Probe, D1–D10, "Testing"), and the three spec deltas under `specs/`. The plan follows the recommendations of U1–U7. If something looks wrong or contradictory, stop and report instead of redesigning.
- **Work test-first with the `tdd` skill** (D-016). For each group, first write its tests, run them, and watch them fail as the task says. Then change the code. The seams are listed in design "Testing", and they count as agreed.
- **Test rules.**
  - No real network. Backend tests use the existing fixtures and test models; summary calls in runs go to a test model, never to a provider.
  - Change no existing test, except where a task says so. Adding imports, fixtures, and small helpers to an existing test file is allowed.
  - Summary calls run in four threads, so a test that gives different items different answers must answer by the item's title (design "Context", "Test doubles"), not by call order.
  - For each named mutation, apply it alone, run the named tests, record the result, and restore the code exactly. Compare with `git diff` after restoring.
- **Environment.**
  - Backend: run commands in `backend/` with `uv run --offline`, without installing new packages.
  - Frontend: use Node 22.17.1 with `export PATH="$HOME/.nvm/versions/node/v22.17.1/bin:$PATH"`. Then run `npm ci --offline --no-audit --no-fund` in `frontend/`, and again in `extension/`. Both install the locked packages from the local npm cache. If either fails, stop and report. Do not download packages, and do not change `package.json` or `package-lock.json`.
  - Prefix every OpenSpec command with `DO_NOT_TRACK=1`.
- **Out of scope:**
  - grouping (`digest/group.py`), topic order, collection, the context pass, the extension, the progress formula, and dependency versions;
  - `frontend/src/pages/Bookmarks.tsx` and `frontend/src/pages/History.tsx`;
  - any change to how a run selects, delivers, or groups items.
- **Do not edit** `proposal.md`, `design.md`, the spec deltas, `docs/process/decision-log.md`, or `docs/process/requirements-changes.md`. Claude Code wrote D-046 and the requirements row with the plan.
- **Do not** run `docker build`, `scripts/docker-smoke.sh`, `docker system prune`, or any other Docker command, and do not touch port 8800. You edit `scripts/docker-smoke.sh` in task 3.2 but never run it; Claude Code runs it at review. Do not push, tag, or open a PR. Never write keys, tokens, or secrets anywhere.
- **Commits.** Commit after each task group.

## 1. The rating in the summary call (digest-generation; design D1, D2)

- [x] 1.1 Write failing tests in `backend/tests/test_digest_stages.py`, using its `FakeModel` (`:16-31`) and `summarize_items`:
  - change `test_no_context_system_prompt_matches_original_main_bytes` (`:219-230`): `original` becomes the summary prompt of design D1, written out literally: the existing text up to and including "say so in one short sentence. ", then "Rate how important the item is to someone following its field, as importance, a whole number from 1 to 5: 5 a major release, finding, decision, or event; 4 a significant development; 3 a useful update; 2 a minor or routine update; 1 little or no substance, such as a bare link or a promotion. ", then "Write the summary in English. Return only json. ", then `'Example output: {"summary": "A short factual summary.", "importance": 3}'`. Keep both assertions;
  - change `test_no_image_long_transcript_prompt_matches_original_main_bytes` (`:233-242`) the same way: the existing text up to and including "Do not describe visuals: no visual content was seen. ", then the same rating sentence, then "Write the summary in English. Return only json. ", then `'Example output: {"summary": "Overview.\\n- Key point one\\n- Key point two", "importance": 3}'`.

    These two `original` strings are the only existing lines of this file that change.
  - `test_summary_prompts_ask_for_an_importance_rating` (new; "Rated item"): with the rating sentence above written out literally as `RULE` in the test (not imported), for each of `summary_messages("Post", "Text", "en")`, `summary_messages("Post", "Text", "en", [{"ref": "L1", "kind": "link", "title": "Release", "host": "github.com", "text": "Fixes."}])`, `summary_messages("Post", "Text", "en", images=[{"origin": "html", "alt": "Chart", "caption": ""}])`, `long_transcript_messages("Talk", "Transcript", "en")`, and `long_transcript_messages("Talk", "Transcript", "en", images=[{"origin": "html", "alt": "Chart", "caption": ""}])`: the system message contains `RULE` once, `RULE` comes before "Write the summary in English.", and the system message contains `'"importance": 3'`. The context case contains `'"importance": 3, "used": ["L1"]'`; both image cases contain `'"importance": 3, "images": [{"ref": "I1"'`. And `part_messages("Post", "Text", "en", 1, 2)[0]["content"]` does not contain `"importance"` (import `part_messages` from `catchup.llm.prompts`);
  - `test_summary_rating_is_kept_when_valid` (new; "Rated item"), parametrized over `value` = 1, 3, 5: `summarize_items(FakeModel([{"summary": "S", "importance": value}]), [SummaryInput(1, "Post", "Text", None, None)], "en", 5000, results.append)`; `results[0].summary == "S"`, `results[0].unavailable is False`, and `results[0].importance == value`;
  - `test_invalid_rating_leaves_the_item_unrated` (new; "Invalid rating"), parametrized over `extra` = `{"importance": 0}`, `{"importance": 6}`, `{"importance": 7}`, `{"importance": "4"}`, `{"importance": 4.5}`, `{"importance": 4.0}`, `{"importance": True}`, `{"importance": None}`, `{}` with ids `zero`, `six`, `seven`, `string`, `fraction`, `float`, `true`, `null`, `missing`: the model `FakeModel([{"summary": "Kept", **extra}])` is called once, and the result has `summary == "Kept"`, `unavailable is False`, and `importance is None`;
  - `test_cached_summary_keeps_its_rating` (new; "Rating kept with a reused summary", "Summary written before ratings"): `summarize_items(FakeModel([]), [SummaryInput(1, "Cached", "content", "In English", "en", importance=5), SummaryInput(2, "Old", "content", "Old summary", "en")], "en", 5000, results.append)`; no call is made; both results are `cached`; item 1's importance is 5 and item 2's is `None`;
  - `test_split_text_rating_comes_from_the_combining_call` (new): a test model whose `chat_json` records the call and answers `{"summary": "Notes", "importance": 1}` when the system message contains "This is part", and `{"summary": "Combined", "importance": 4}` otherwise; `SummaryInput(1, "Long", "word " * 40, None, None)` with `max_chars` 60. More than one call is made, the result has `summary == "Combined"` and `importance == 4`, and the last call's system message contains `'"importance": 3'`;
  - `test_unavailable_summary_is_unrated` (new; "Summary unavailable"): `FakeModel([ProviderError("failed")])`; the result is `unavailable` and its `importance is None`.

  Verify: the two changed tests and `test_summary_prompts_ask_for_an_importance_rating` fail (the prompts have no rating); the other new tests fail with `TypeError` or `AttributeError` (`SummaryInput` takes no `importance`, `SummaryResult` has none).
- [x] 1.2 Implement design D1 and D2:
  - in `backend/src/catchup/llm/prompts.py`: `IMPORTANCE_RULE` exactly as D1 shows, placed in `summary_messages` and `long_transcript_messages` as D1 says, and the two example outputs with `"importance": 3` after `"summary"`. Do not change `part_messages`, `combine_messages`, or the grouping prompts;
  - in `backend/src/catchup/digest/summarize.py`: `importance` as the last field of `SummaryInput` and of `SummaryResult` (default `None`), `_importance` as D2 shows, the rating in `_summarize`'s result, and `importance=item.importance` in the cached result.

  Verify: the tests from 1.1 pass, and `uv run --offline pytest` passes in `backend/`, with every other existing test unchanged. Mutations S1–S6 each fail the tests named for them:
  - S1: `_importance` drops the upper bound (accepts any `int` of at least 1) → `test_invalid_rating_leaves_the_item_unrated[six]` and `[seven]`;
  - S2: `_importance` uses `isinstance(value, int)` instead of `type(value) is int` → `[true]`;
  - S3: the cached result leaves out `importance=item.importance` → `test_cached_summary_keeps_its_rating`;
  - S4: a missing or `None` rating raises `ProviderError` → `[null]` and `[missing]`;
  - S5: `long_transcript_messages` leaves out `IMPORTANCE_RULE` → `test_summary_prompts_ask_for_an_importance_rating` and `test_no_image_long_transcript_prompt_matches_original_main_bytes`;
  - S6: `part_messages` adds `IMPORTANCE_RULE` → `test_summary_prompts_ask_for_an_importance_rating`.

  Restore the code after each.

## 2. Stored and saved ratings (digest-generation, digest-history; design D3, D4, D6)

- [x] 2.1 Write failing tests:
  - in `backend/tests/test_db.py`:
    - the head assertions at `:205`, `:374`, `:414`, and `:555` become `"0013_item_importance"`;
    - in `test_item_marks_migration_creates_empty_table_and_downgrades`, `command.upgrade(config, "head")` at `:587` becomes `command.upgrade(config, "0012_digest_item_marks")`; its assertion at `:589` stays `"0012_digest_item_marks"` (design "Context": it compares whole `digest_items` rows);
    - `test_migrations_live_inside_package` also asserts `0013_item_importance.py`;

      these are the only existing lines of this file that change;
    - `test_item_importance_migration_adds_columns_and_downgrades` (new): upgrade to `"0012_digest_item_marks"`; insert the seven rows of `test_upgrade_existing_rows_and_downgrade` (`:223-255`: app settings, a source, an item, a run, a digest, a topic, a digest item) with the same SQL; keep `before` as the dicts of `SELECT * FROM items`, `SELECT * FROM digest_items`, and `SELECT * FROM app_settings`. Upgrade to `"0013_item_importance"`: the version is `"0013_item_importance"`; the item row equals its `before` plus `"importance": None`, the digest item row its `before` plus `"importance": None`, and the settings row its `before` plus `"top_items": 0`; `top_items` is not nullable (`inspect(engine).get_columns("app_settings")`). Downgrade to `"0012_digest_item_marks"`: none of the three columns remain, and the three tables' rows equal `before`.
  - in `backend/tests/test_digest_runner.py`, using `seed`, `stub_collection`, `execute`, `all_rows`, and `FakeModel`:
    - a test model `RatingModel(FakeModel)` defined in the file: it takes a dict from item title to extra answer fields; for a summary call (`'"summary"' in messages[0]["content"]`) it records the call, reads the title from the first line of `messages[1]["content"]` (`"Title: <title>"`), and answers `{"summary": f"Summary of {title}", **ratings.get(title, {})}`; any other call is answered as `FakeModel.chat_json` answers it;
    - `test_digest_records_each_items_rating` ("Rated item", "Invalid rating"): `seed(environment, count=3)`, `stub_collection(monkeypatch)`, `RatingModel({"Item 0": {"importance": 5}, "Item 1": {"importance": "4"}})`. The run succeeds; the `DigestItem` ratings by title are `{"Item 0": 5, "Item 1": None, "Item 2": None}`; the `Item` rows have the same ratings; and `GET /api/digests/{digest_id}` gives the same `importance` by title;
    - `test_rating_survives_a_failed_grouping` ("Rating kept with a reused summary"): as `test_group_failure_preserves_pending_and_retry_uses_cached_summary` (`:762-779`), with the first model `FakeModel([{"summary": "Cached", "importance": 5}, AuthFailed("group failed")])`. After the failed run the `Item` has `importance == 5`. The retry `FakeModel([{"topics": [{"title": "Topic", "overview": "Overview", "item_refs": ["i1"]}]}])` succeeds with one call, and the `DigestItem` has `importance == 5`;
    - `test_unavailable_summary_is_saved_unrated` ("Summary unavailable"): `seed(environment)`; set the `Item`'s `importance` to 5 and leave its `summary` empty, as after a cleared summary; model `FakeModel([ProviderError("failed"), {"topics": [{"title": "Topic", "overview": "Overview", "item_refs": ["i1"]}]}])`. The run succeeds, and the `DigestItem` has `summary_unavailable is True` and `importance is None`;
    - `test_summary_written_before_ratings_is_reused_unrated` ("Summary written before ratings"): `seed(environment)`; set the `Item`'s `summary` to `"Old summary"` and `summary_language` to `"en"`, with no rating; model `FakeModel([{"topics": [{"title": "Topic", "overview": "Overview", "item_refs": ["i1"]}]}])`. The run succeeds with that one call, and the `DigestItem` has `summary == "Old summary"` and `importance is None`;
    - `test_creator_updates_are_unrated`: `seed(environment, count=2, sources=2)`; set the item of source 2 to `transcript_status = "no_transcript"` and `importance = 4`; the default `FakeModel`. The run succeeds, and the `DigestItem` in the `creator_updates` topic has `importance is None`.
  - in `backend/tests/test_digest_history.py`:
    - in `test_digest_detail_uses_snapshot_positions_and_survives_source_deletion`, the pinned item answer (`:359-365`) gains `"importance": None`. This is the only existing line that changes;
    - `test_digest_answers_give_each_items_saved_rating` (new; "Reopen a rated digest", "Digest saved before ratings"): `seed_history(client)`; then add a newer digest (`created_at` 2026-10-03, its own `DigestRun`) with one topic and one `DigestItem` titled "Rated" with `item_id` of the stored item and `importance=4`. `GET /api/digests/latest` and `GET /api/digests/<its id>` give "Rated" `importance == 4`; every topic item of `GET /api/digests/1` has `importance is None`. After `DELETE /api/sources/<source id>`, both still give 4.

  Verify: the changed `test_db.py` assertions and the new migration test fail (there is no `0013_item_importance`); the new runner tests fail (`Item` and `DigestItem` have no `importance`); both `test_digest_history.py` tests fail (the answers have no `importance`).
- [x] 2.2 Implement design D3, D4, and D6:
  - in `backend/src/catchup/models.py`: `Item.importance`, `DigestItem.importance`, and `AppSettings.top_items` as D3 shows;
  - the migration `backend/src/catchup/migrations/versions/0013_item_importance.py` as D4 shows;
  - in `backend/src/catchup/digest/runner.py`: `importance=item.importance` in each `SummaryInput`, `item.importance = result.importance` in `record` for a new summary, and the snapshot rating as D3 shows. Creator update rows set none;
  - in `backend/src/catchup/api/digests.py`: `"importance": item.importance` in `item_answer`.

  Verify: the tests from 2.1 pass, and `uv run --offline pytest` passes in `backend/`. Mutations each fail the tests named for them:
  - M1: the migration does not add `digest_items.importance` → `test_item_importance_migration_adds_columns_and_downgrades`;
  - M2: `top_items` gets `server_default="5"` in the migration → `test_item_importance_migration_adds_columns_and_downgrades`;
  - M3: the downgrade leaves `items.importance` in place → `test_item_importance_migration_adds_columns_and_downgrades`;
  - R1: `record` does not set `item.importance` → `test_rating_survives_a_failed_grouping` and `test_digest_records_each_items_rating`;
  - R2: the snapshot leaves out `importance` → `test_digest_records_each_items_rating` and `test_rating_survives_a_failed_grouping`;
  - R3: the snapshot's `importance=` becomes `item.importance`, without the summary/unavailable condition → `test_unavailable_summary_is_saved_unrated`;
  - R4: Creator update rows get `importance=item.importance` → `test_creator_updates_are_unrated`;
  - H1: `item_answer` leaves out `importance` → `test_digest_answers_give_each_items_saved_rating` and `test_digest_detail_uses_snapshot_positions_and_survives_source_deletion`.

  Restore the code after each.

## 3. "Items to show" in Settings (user-interface; design D5, D9 Settings, D10)

- [x] 3.1 Write failing tests:
  - in `backend/tests/test_settings_api.py`:
    - in `test_preference_save_and_read`, `test_partial_preference_updates_keep_other_values`, and `test_image_preference_can_be_saved_without_changing_others`, every expected answer gains `"top_items": 0`. These are the only existing tests in this file that change;
    - `test_top_items_save_and_read` (new; "Save a number"): `PUT {"top_items": n}` for `n` in 5, 10, 20, 30, and 0, in that order, each answers 200 with `top_items == n` and `link_depth == "normal"`, and `GET` answers `top_items == n`;
    - `test_invalid_top_items` (new; "Value refused"), parametrized over `(value, code)` = `(7, "invalid_top_items")`, `(-5, "invalid_top_items")`, `(1, "invalid_top_items")`, `(100, "invalid_top_items")`, `(False, "invalid_request")`, `(True, "invalid_request")`, `("10", "invalid_request")`, `(10.0, "invalid_request")`, `(10.5, "invalid_request")` with ids `seven`, `negative`, `one`, `hundred`, `false`, `true`, `string`, `float`, `fraction`: after `PUT {"top_items": 10}`, `PUT {"top_items": value}` answers 422 with `error.code == code`; for `invalid_top_items` the message is "Choose All, 5, 10, 20, or 30 items to show."; `GET` still answers `top_items == 10`.
  - in `scripts/docker-smoke.sh`, both expected preferences answers (`:86-91` and `:123-128`) gain `"top_items": 0`. Do not run the script.
  - `backend/tests/test_readme_top_items.py` (new), like `backend/tests/test_readme_marks.py`: the README intro, with whitespace collapsed, contains "In Settings → Digest, **Items to show** can limit each digest to its most important items: each summary rates its item from 1 to 5, and a button shows the rest."
  - in `frontend/src/pages/Settings.test.tsx`, using `mockLinkedPages` and `preferencePuts`:
    - `mockLinkedPages`'s default answer gains `top_items: 0` (a helper change; no test changes);
    - `shows the items-to-show choice with its note` (new; "Default choice"): with the `beforeEach` answer, which has no `top_items`, the combobox "Items to show" has the value `'0'`; its options' texts are exactly `['All items', 'The 5 most important', 'The 10 most important', 'The 20 most important', 'The 30 most important']`; it `toHaveAccessibleDescription("Each summary also rates how important its item is, from 1 to 5. A digest with more items in its topics than this shows only the most important ones, with a button that shows the rest. Creator updates are always shown, and digests saved before ratings show every item.")`; and it follows the "Linked pages" combobox and precedes the "Show images from source sites" switch in document order;
    - `saves Items to show with the other digest preferences` (new; "Save a number"): choose `10`, click Save, wait for "Settings saved.", and the one preferences `PUT` body `toMatchObject({ top_items: 10, link_depth: 'normal', digest_language: 'en', show_images: true, youtube_captions: false, youtube_skip_shorts: true })`;
    - `loads a saved number and keeps it when saving without changing it` (new): `mockLinkedPages({ top_items: 20 })`; the combobox has the value `'20'`; after Save, the `PUT` body has `top_items: 20`.

  Verify: the changed backend tests, the two new backend tests, the README test, and the three new frontend tests fail; the other existing tests still pass.
- [x] 3.2 Implement design D5, the Settings part of D9, and D10:
  - in `backend/src/catchup/api/settings.py`: `TOP_ITEMS`, the `StrictInt` field, the check and the save, and `top_items` in the answer, as D5 shows;
  - in `frontend/src/pages/Settings.tsx`: the `Preferences` field, the state, the load, the save body, and the field, as D9 shows;
  - in `README.md`: the sentence of D10, appended to the intro paragraph;
  - the smoke script lines from 3.1.

  Verify: the tests from 3.1 pass; `uv run --offline pytest` passes in `backend/`; `npm test -- --run` and `npm run build` pass in `frontend/`; `bash -n scripts/docker-smoke.sh` passes. Mutations each fail the tests named for them:
  - P1: `TOP_ITEMS` leaves out 30 → `test_top_items_save_and_read`;
  - P2: the membership check is removed → `test_invalid_top_items[seven]`, `[negative]`, `[one]`, and `[hundred]`;
  - P3: the field is `int | None` instead of `StrictInt | None` → `test_invalid_top_items[false]`, `[true]`, `[string]`, and `[float]`;
  - P4: `read_preferences` answers 10 when no settings row exists → `test_preference_save_and_read`;
  - F1: the save body leaves out `top_items` → `saves Items to show with the other digest preferences`;
  - F2: the load ignores the saved value → `loads a saved number and keeps it when saving without changing it`;
  - F3: the select loses `aria-describedby` → `shows the items-to-show choice with its note`;
  - Doc: the README sentence is removed → `test_readme_top_items.py`.

  Restore the code after each.

## 4. The limited digest (user-interface; design D7, D8, D9 Home and DigestView)

- [x] 4.1 Write failing tests:
  - `frontend/src/test/limitedDigest.ts` (new), typed with `Digest` from `../components/DigestArticle`:
    - `limitedDigest`: `id: 7`, `created_at: '2026-11-20T10:00:00Z'`, `model_id: 'test'`, `language: 'en'`, `item_count: 10`, `source_count: 3`, `transcript_wait_days: 7`, and three topics, with overviews `'Alpha overview'`, `'Beta overview'`, and `'Gamma overview'`:
      - Alpha: items 1 "A1" rated 2, and 2 "A2" rated 5;
      - Beta: items 3 "B1" rated 1, and 4 "B2" rated 1;
      - Gamma: items 5 "C1" rated 4, 6 "C2" with `importance: null`, 7 "C3" with `summary: null`, `summary_unavailable: true`, and `importance: null`, and 8 "C4" rated 3.

      Every item has `bookmarked: false`, `liked: false`, `rating: null`, `note: null`, `link: 'https://example.test/<id>'`, `source_name: 'Blog'`, `published_at: null`, and, except C3, `summary: 'Summary <title>'` and `summary_unavailable: false`. `creator_updates` is one group `{ source_name: 'Channel', source_kind: 'youtube', items: [...] }` with "Video one" and "Video two" (`link: 'https://example.test/v1'` and `'…/v2'`, `published_at: null`, `reason: 'no_captions'`);
    - `unrated(digest)`: a copy of `digest` with every topic item's `importance` set to `null`.
  - `frontend/src/components/topItems.test.ts` (new), with a small item factory:
    - `ranks by rating, an unrated summary as 3, and an unavailable one last` ("Limited digest"): `[...shownItemIds(limitedDigest.topics, 5)!].sort((a, b) => a - b)` equals `[1, 2, 5, 6, 8]`;
    - `keeps reading order among equal ranks`: topics `[{ items: [id 1 rated 3, id 2 rated 3] }, { items: [id 3 rated 3] }]` with the limit 2 give `[1, 2]`;
    - `ranks an unavailable summary below a rating of 1`: one topic with `[id 1 unavailable, id 2 rated 1]` and the limit 1 gives `[2]`;
    - `shows everything without a limit, for a short digest, or without ratings` ("Short digest", "Digest saved before ratings"): `null` for `limitedDigest.topics` with the limits 0, 8, and 10; for `unrated(limitedDigest).topics` with the limit 5; and for 8 items that have no `importance` field at all with the limit 5.
  - in `frontend/src/components/DigestArticle.test.tsx` (new tests, with `limitedDigest` and `unrated`):
    - `shows only the most important items in their topics` ("Limited digest"): render `<DigestArticle digest={limitedDigest} topItems={5}/>` in a `MemoryRouter`. The item titles (the `textContent` of each `article.item .item-title a`, with its ` (opens the original)` suffix removed) are, in order, `['A1', 'A2', 'C1', 'C2', 'C4']`; there is no heading "Beta"; the index entries (`li` texts of the "In this digest" navigation) are `['Alpha 2', 'Gamma 3', 'Creator updates 2']`; "Video one" and "Video two" are shown; `.digest-meta` contains "10 items"; the text "Showing the 5 most important of the 8 items in topics." is shown; the button "Show all 8" has that text as its accessible description; `expectAccessible` passes;
    - `shows every item and limits again` ("Show all"): focus "Show all 8" and click it. There are 8 items and the heading "Beta"; `#digest-limit-note` reads "Showing all 8 items in topics."; the same button element now reads "Show the 5 most important" and has focus; the digest's status region has the text "Showing all 8 items in topics.". Click it again: 5 items, and the status region has "Showing the 5 most important of the 8 items in topics.";
    - `starts limited again for the next digest` ("New digest starts limited"): click "Show all 8", then `rerender` with `{ ...limitedDigest, id: 8 }` and `topItems={5}`: 5 items, and the limited line;
    - `shows short and unrated digests in full` ("Short digest", "Digest saved before ratings"): `limitedDigest` with `topItems={10}`, and `unrated(limitedDigest)` with `topItems={5}`, each show 8 items and no `.digest-limit`.
  - in `frontend/src/pages/Home.test.tsx`:
    - `mockPage` gains an option `preferences?: unknown`: when it is given, `/api/settings/preferences` answers it; otherwise the request still throws as today. This is the only change to existing code;
    - `limits the latest digest to the saved number of items`: `mockPage({ latest: limitedDigest, preferences: { show_images: true, top_items: 5 } })`; the button "Show all 8" appears, with 5 items;
    - `moves focus to run-bar Generate when a new digest replaces the shown one while Show all has focus` ("Show all has focus when a new digest arrives"): as the test at `:942-965`, with `latest: limitedDigest`, `detail: { ...limitedDigest, id: 8 }`, and the same `preferences`; focus "Show all 8" before Generate is clicked; after "No. 8" is shown, Generate has focus.
  - in `frontend/src/pages/DigestView.test.tsx`, with `page()`:
    - `limits a saved digest to the saved number of items`: `/api/digests/7` answers `limitedDigest`, the preferences answer `{ show_images: true, top_items: 5 }`; "Show all 8" appears, with 5 items;
    - `shows every item when the preferences cannot be read` ("Choice cannot be read"): the preferences request answers 500; 8 items are shown, and there is no "Show all 8".
  - in `frontend/src/pages/Bookmarks.test.tsx`: `lists every bookmark whatever Items to show says` ("Bookmarks"): 8 entries built from the first entry of `entries` (ids 31–38, titles "Saved 1" to "Saved 8", with `importance` 1 to 5 in turn: ids 31–35 get 1–5, ids 36–38 get 1–3), and the preferences answer `{ show_images: true, top_items: 5 }`; all 8 titles are shown. This test passes before and after the change; it guards the spec scenario.

  Verify: the new tests fail (there is no `topItems.ts`, no `topItems` prop, and no line), except three tests that check a digest shown in full and pass before and after the change: `shows short and unrated digests in full` in `DigestArticle.test.tsx`, `shows every item when the preferences cannot be read` in `DigestView.test.tsx`, and the Bookmarks test. The existing tests still pass.
- [x] 4.2 Implement design D7, D8, and the Home and DigestView parts of D9:
  - `frontend/src/components/topItems.ts` as D7 shows, and `importance?: number | null` on `DigestItem`;
  - in `frontend/src/components/DigestArticle.tsx`: the prop, the state, the visible topics (dropping a topic with no shown item only while the digest is limited), the index, and the line with its button, as D8 shows;
  - in `frontend/src/styles/components.css`: the two `.digest-limit` rules of D8;
  - in `frontend/src/pages/Home.tsx` and `frontend/src/pages/DigestView.tsx`: the saved choice and the focus rule, as D9 shows.

  Verify: the tests from 4.1 pass; `npm test -- --run` and `npm run build` pass in `frontend/`. Mutations each fail the tests named for them:
  - T1: an unrated item with a summary ranks as 0 → `ranks by rating, an unrated summary as 3, and an unavailable one last`;
  - T2: an unavailable item ranks as 3 → `ranks an unavailable summary below a rating of 1`;
  - T3: equal ranks are taken in reverse reading order → `keeps reading order among equal ranks`;
  - T4: the "at least one rated item" check is removed → `shows everything without a limit, for a short digest, or without ratings`;
  - T5: a digest with exactly `limit` items is limited → `shows everything without a limit, for a short digest, or without ratings`;
  - A1: topics with no shown item are kept → `shows only the most important items in their topics`;
  - A2: an index entry counts all of its topic's items → `shows only the most important items in their topics`;
  - A3: the "show all" state is a boolean that is not tied to the digest → `starts limited again for the next digest`;
  - A4: Creator updates are hidden while the digest is limited → `shows only the most important items in their topics`;
  - A5: the click does not announce → `shows every item and limits again`;
  - A6: the headline counts only the shown items → `shows only the most important items in their topics`;
  - A7: topics with no shown item are dropped also when the digest is shown in full → `renders creator updates after topics with saved wait labels`, `marks Chinese generated text and focuses index targets`, and `omits all digest language marks when the saved preference is original` in `frontend/src/pages/DigestView.test.tsx` (their fixtures have saved topics with no items);
  - V1: Home does not pass `topItems` → `limits the latest digest to the saved number of items`;
  - V2: Home's focus rule leaves out `.digest-limit` → `moves focus to run-bar Generate when a new digest replaces the shown one while Show all has focus`;
  - V3: DigestView does not pass `topItems` → `limits a saved digest to the saved number of items`.

  Restore the code after each.

## 5. Checks and report

- [x] 5.1 Run the full checks:
  - `uv run --offline pytest` in `backend/` (record the count);
  - `npm test -- --run` and `npm run build` in `frontend/` and in `extension/`, with Node 22.17.1 (record the counts);
  - `DO_NOT_TRACK=1 openspec validate add-top-items-limit --strict`;
  - `git diff --check`.

  Do not run `docker build`, `scripts/docker-smoke.sh`, or any Docker command, and do not touch port 8800: Claude Code runs the Docker smoke and the live check at review.

  Write the commands and their real results to `docs/process/test-report-add-top-items-limit.md`:
  - each new or changed test, the spec scenario it covers, and the mutations that it kills;
  - mutations S1–S6, M1–M3, R1–R4, H1, P1–P4, F1–F3, Doc, T1–T5, A1–A7, and V1–V3, with their results; record the guarded variant of R3 (only the source swapped to `item.importance`) and the removal of the summary/unavailable condition as equivalent mutants;
  - the Docker smoke and the live check of design "Testing", listed as not performed (Claude Code runs them at review), and the user's check of design "Rollout" as the user's, after the merge.

  Add your entry to `docs/process/ai-usage-log.md` after the latest entry, with a faithful prompt excerpt. Leave out the session id; Claude Code adds it at review.

  Verify: every command that ran passes, and the report has the actual numbers.
