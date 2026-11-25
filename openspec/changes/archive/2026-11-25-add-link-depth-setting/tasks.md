# Tasks

Implementer notes:
- **Read first.** Read `proposal.md`, `design.md` (all of "Context", D1–D8, "Testing"), and the two spec deltas under `specs/`. The plan follows the recommendations of U1–U3. If something looks wrong or contradictory, stop and report instead of redesigning.
- **Work test-first with the `tdd` skill** (D-016). For each group, first write its tests, run them, and watch them fail as the task says. Then change the code. The seams are listed in design "Testing", and they count as agreed.
- **Test rules.**
  - No real network: every context fetch goes through `respx.mock(assert_all_mocked=True, assert_all_called=False)` with the `public_dns` fixture, as the tests in `backend/tests/test_context_gather.py` do. `assert_all_called=False` is required wherever a test mocks a route that must not be called; otherwise respx raises "RESPX: some routes were not called!" when the block exits.
  - Change no existing test, except where a task says so. Adding imports and small helpers to an existing test file is allowed.
  - For each named mutation, apply it alone, run the named tests, record the result, and restore the code exactly. Compare with `git diff` after restoring.
  - Set the level in backend tests by writing `link_depth` on the `AppSettings` row with id 1 through `environment.app.state.session_factory()`; `seed` creates that row.
- **Environment.**
  - Backend: run commands in `backend/` with `uv run --offline`, without installing new packages.
  - Frontend: use Node 22.17.1 with `export PATH="$HOME/.nvm/versions/node/v22.17.1/bin:$PATH"`. Then run `npm ci --offline --no-audit --no-fund` in `frontend/`, and again in `extension/`. Both install the locked packages from the local npm cache. If either fails, stop and report. Do not download packages, and do not change `package.json` or `package-lock.json`.
- **Out of scope:**
  - backend files other than `context/depth.py` (new), `context/links.py`, `context/gather.py`, `digest/runner.py`, `api/settings.py`, `models.py`, and `migrations/versions/0010_link_depth.py` (new), and the tests named below;
  - frontend files other than `src/pages/Settings.tsx` and `src/pages/Settings.test.tsx`;
  - the extension, the progress formula, the caps (3,000 and 16,000 characters), `config.py`, and dependency versions.
- **Do not edit** `proposal.md`, `design.md`, the spec deltas, `docs/process/decision-log.md`, or `docs/process/requirements-changes.md`. Claude Code wrote D-042 and the requirements row with the plan.
- **Do not** run `docker build`, `scripts/docker-smoke.sh`, `docker system prune`, or any other Docker command, and do not touch port 8800. Do not push, tag, or open a PR. Never write keys, tokens, or secrets anywhere.
- **Commits.** Commit after each task group.

## 1. The levels (content-collection; design D1, D2)

- [x] 1.1 Write failing tests:
  - in `backend/tests/test_context_depth.py` (new), importing `LINK_DEPTHS`, `ContextLimits`, `context_limits`, and `link_depth_pages` from `catchup.context.depth`, and building settings with `dataclasses.replace(test_settings, ...)` from the `test_settings` fixture:
    - `test_link_depths`: `LINK_DEPTHS == ("off", "shallow", "normal")`;
    - `test_context_limits`, parametrized over `(level, links_per_item, context_fetches_per_run, author_replies, expected)`, with ids:
      - `off`: `("off", 8, 60, True, ContextLimits(0, 0, False))`;
      - `shallow`: `("shallow", 8, 60, True, ContextLimits(3, 60, True))`;
      - `shallow_under_2`: `("shallow", 2, 60, True, ContextLimits(2, 60, True))`;
      - `shallow_no_replies`: `("shallow", 8, 60, False, ContextLimits(3, 60, False))`;
      - `normal`: `("normal", 8, 60, True, ContextLimits(8, 60, True))`;
      - `normal_server`: `("normal", 5, 40, False, ContextLimits(5, 40, False))`;
      - `unknown`: `("deep", 8, 60, True, ContextLimits(8, 60, True))`;
      - `empty`: `("", 8, 60, True, ContextLimits(8, 60, True))`;
    - `test_link_depth_pages`, parametrized over `(links_per_item, expected)`: `(8, {"off": 0, "shallow": 3, "normal": 8})`, `(5, {"off": 0, "shallow": 3, "normal": 5})`, `(2, {"off": 0, "shallow": 2, "normal": 2})`, `(1, {"off": 0, "shallow": 1, "normal": 1})`;
  - in `backend/tests/test_context_links.py`, `test_limit_zero_keeps_no_links`: with two links that the rules keep (`https://docs.example/a` and `https://docs.example/b`), `related_links(ITEM, SITE, links, 0) == []` and `related_links(ITEM, SITE, links, -1) == []`.

  Verify: `uv run --offline pytest tests/test_context_depth.py` fails with `ModuleNotFoundError: No module named 'catchup.context.depth'`; run `tests/test_context_links.py` on its own, because a collection error stops the whole run: `test_limit_zero_keeps_no_links` fails, because a limit of 0 returns the first link today (design "Context", probe).
- [x] 1.2 Add `backend/src/catchup/context/depth.py` as in design D1: `LINK_DEPTHS`, `SHALLOW_LINKS = 3`, the frozen dataclass `ContextLimits(links_per_item, fetches_per_run, author_replies)`, `context_limits(level, settings)` following the D1 table, with any other level treated as `normal`, and `link_depth_pages(settings)`. In `related_links` (`backend/src/catchup/context/links.py`), return `[]` at the start when `limit <= 0`.

  Verify: the tests from 1.1 pass, and `uv run --offline pytest` passes in `backend/`. Mutations L1–L5 and L7 (design "Testing") each fail the depth or links tests named there. Restore the code after each.

## 2. Storing the level, and the preferences API (content-collection, user-interface; design D6)

- [x] 2.1 Write failing tests:
  - in `backend/tests/test_db.py`, `test_link_depth_migration_defaults_existing_settings_and_downgrades`, following `test_model_provider_migration_defaults_existing_config_and_downgrades`: upgrade a temporary engine to `0009_model_provider`; insert `INSERT INTO app_settings (id, digest_language, youtube_captions, youtube_skip_shorts, show_images, updated_at) VALUES (1, 'zh-Hans', 1, 0, 0, '2026-11-01')`; keep the row as a dict; upgrade to `head`; the row's `link_depth` is `"normal"`, the rest equals the kept row, and `alembic_version` is `0010_link_depth`; downgrade to `0009_model_provider`; `app_settings` has no `link_depth` column, and the row equals the kept row.

    Also change the existing head checks in `test_db.py`: add `assert (migrations / "versions" / "0010_link_depth.py").is_file()` after the `0009` line (`:127`), and change the four assertions that the head is `"0009_model_provider"` (`:145`, `:314`, `:354`, `:495`) to `"0010_link_depth"`. These are the only existing assertions in this file that change.
  - in `backend/tests/test_settings_api.py`:
    - in `test_preference_save_and_read`, `test_partial_preference_updates_keep_other_values`, and `test_image_preference_can_be_saved_without_changing_others`, add to every expected answer `"link_depth": "normal"`, `"link_depth_pages": {"off": 0, "shallow": 3, "normal": 8}`, and `"context_fetches_per_run": 60`. These are the only existing tests in this file that change;
    - `test_link_depth_save_and_read`: `PUT {"link_depth": "off"}` answers 200 with `link_depth` `"off"` and the other preferences unchanged, and `GET` answers the same; `PUT {"link_depth": "shallow"}` then answers `"shallow"`; `PUT {"digest_language": "zh-Hans"}` keeps `"shallow"`;
    - `test_invalid_link_depth`, parametrized over `"deep"`, `""`, `"OFF"`, and `"none"`: `PUT {"link_depth": value, "digest_language": "fr"}` answers 422 with error code `invalid_link_depth`, and `GET` still answers `"digest_language": "en"` and `"link_depth": "normal"`;
    - `test_preferences_report_the_server_numbers`: set `client.app.state.settings = replace(client.app.state.settings, links_per_item=5, context_fetches_per_run=40)`; `GET` answers `"link_depth_pages": {"off": 0, "shallow": 3, "normal": 5}` and `"context_fetches_per_run": 40`; with `links_per_item=2`, `{"off": 0, "shallow": 2, "normal": 2}`;
    - `test_preference_numbers_cannot_be_written`: `PUT {"link_depth_pages": {"normal": 99}, "context_fetches_per_run": 1}` answers 200, and `GET` still answers the server's numbers.

  Verify: the migration test fails (there is no `0010_link_depth` revision, so the upgraded row has no `link_depth`), and so do the changed head checks; every changed and new preferences test fails, `test_preference_numbers_cannot_be_written` included, because its `GET` lacks the numbers.
- [x] 2.2 Implement design D6:
  - `backend/src/catchup/migrations/versions/0010_link_depth.py` with `revision = "0010_link_depth"` and `down_revision = "0009_model_provider"`, adding `app_settings.link_depth` (`String(16)`, not null, `server_default="normal"`); the downgrade drops it with `batch_alter_table("app_settings", recreate="never")`. Give it a one-line docstring, as `0005_item_images.py` has;
  - `AppSettings.link_depth` in `backend/src/catchup/models.py`, with `default="normal", server_default="normal"`;
  - in `backend/src/catchup/api/settings.py`: `PreferenceInput.link_depth: str | None = None`; `read_preferences` takes `request: Request` and adds `link_depth` (`"normal"` without a row), `link_depth_pages` (`link_depth_pages(request.app.state.settings)`), and `context_fetches_per_run` (`request.app.state.settings.context_fetches_per_run`); `save_preferences` takes `request: Request`, refuses a `link_depth` not in `LINK_DEPTHS` with `AppError("invalid_link_depth", "Choose Off, Shallow, or Normal for linked pages.", 422)` before it writes anything, stores a valid one, and returns `read_preferences(request, session)`.

  Verify: the tests from 2.1 pass, and `uv run --offline pytest` passes in `backend/`. Mutations L6, A1, A2, and M1 each fail the tests named in design "Testing". Restore the code after each.

## 3. The run uses the level (content-collection; design D2, D3, D4, D5)

- [x] 3.1 Write tests in `backend/tests/test_context_gather.py`, with a helper `set_level(client, level)` that writes `link_depth` on the `AppSettings` row with id 1. Import `AuthFailed` from `catchup.llm.client`, as `test_digest_runner.py` does.
  - `test_shallow_reads_the_first_three_links` ("Shallow reads three links"): `setup(environment, [(f"https://h{i}.example/p", str(i)) for i in range(5)])`, level `shallow`, `stub_collection(monkeypatch)`; each site's robots.txt answers 404 and each page answers `html(str(i), "Linked text " * 40)`. The run succeeds; the page routes are called `[1, 1, 1, 0, 0]` times and the robots.txt routes `[1, 1, 1, 0, 0]` times; `(context_total, context_done) == (3, 3)`.
  - `test_shallow_follows_a_lower_server_setting` ("Shallow under a lower server setting"): three links on `https://docs.example/`, level `shallow`, `links_per_item=2` through `replace(environment.app.state.settings, ...)`. The pages are called `[1, 1, 0]` times.
  - `test_normal_follows_the_server_setting` ("Normal follows the server setting"): six links on `https://docs.example/`, level `normal`, `links_per_item=5`. The pages are called `[1, 1, 1, 1, 1, 0]` times.
  - `test_off_makes_no_context_request` ("Off makes no request"): `setup(environment, [("https://docs.example/one", "One"), ("https://docs.example/two", "Two")], comments=2)`, then set the item's `entry_author` to `"Writer"` through a session (`setup` has no such parameter), level `off`. Mock both pages, both sites' robots.txt, and the post page `https://s0.example/0` with an author reply. The run succeeds; `result["digest_item_count"] == 1`; `router.calls.call_count == 0`; `(context_total, context_done) == (0, 0)`; the item's `context_status` is `None`, and no `ItemContext` row exists.
  - `test_off_keeps_saved_replies` ("Off keeps saved replies"): `capture_with_context(environment, links=[("https://docs.example/article", "Article")], replies=["First reply", "Second reply"])`, level `off`, with the article and its robots.txt mocked. The run succeeds; no request is made; `(context_total, context_done) == (1, 1)`; the capture is `gathered`, and its contexts are exactly `[("A1", "First reply\n\nSecond reply")]` as `(ref, text)`.
  - `test_item_left_by_off_is_read_later` ("Item left by Off is read later"): one link on `https://docs.example/one`, level `off`, and `environment.app.state.model_client_factory = lambda *_: FakeModel([AuthFailed("bad key")])`. The run fails and the page is not requested. Then set `model_client_factory` back to `lambda *_: FakeModel()` and the level to `normal`; the next run succeeds, requests the page once, and the item is `gathered`.
  - `test_level_saved_during_a_run_applies_to_the_next_run` ("Level changed during a run"): one link on `https://docs.example/one`, level `off`, and `stub_collection(monkeypatch, on_check=lambda: set_level(environment, "normal"))`. The run succeeds without requesting the page, and the stored level is then `"normal"`. Set the item back to `state="pending"` and `summary=None`, as `test_budget_leaves_unreached_items_ungathered_and_retries_do_not_refetch` does, call `stub_collection(monkeypatch)` again, and run again: the page is requested once.
  - `test_run_without_saved_digest_settings_reads_at_normal` ("No level saved", for an instance that saved a model with Test connection but never saved Settings): `setup(environment, [("https://docs.example/one", "One")])`, then delete the `AppSettings` row with id 1 through `environment.app.state.session_factory()`; `stub_collection(monkeypatch)`; robots.txt answers 404 and the page answers `html("One", "Linked text " * 40)`. The run succeeds and requests the page once.

  Verify: `test_shallow_reads_the_first_three_links`, `test_off_makes_no_context_request`, `test_off_keeps_saved_replies`, `test_item_left_by_off_is_read_later`, and `test_level_saved_during_a_run_applies_to_the_next_run` fail on the code of group 2, because the run ignores the level. `test_shallow_follows_a_lower_server_setting`, `test_normal_follows_the_server_setting`, and `test_run_without_saved_digest_settings_reads_at_normal` pass already, because Normal reads the same links; mutations L4, L7, and R3 show that they can fail.
- [x] 3.2 Implement design D2 and D3:
  - `gather_context(factory, run_id, settings, spacer, level="normal")` in `backend/src/catchup/context/gather.py` computes `limits = context_limits(level, settings)` and uses `limits.fetches_per_run` for the budget (`gather.py:109`), `limits.links_per_item` in the `related_links` call of the plan (`:126-130`), and `limits.author_replies` in place of `settings.author_replies` (`:131`). Change nothing else in the pass;
  - `run_digest` in `backend/src/catchup/digest/runner.py` reads `link_depth` from the same `AppSettings` row as the language (`runner.py:259-262`), `"normal"` without a row, and passes `level=link_depth` to `gather_context` (`runner.py:353`).

  Verify: the tests from 3.1 pass, and `uv run --offline pytest` passes in `backend/`, with every existing test in `test_context_gather.py` and `test_digest_runner.py` unchanged. Mutations G1, R1, R2, and R3, and L1, L3, L4, and L7 again, each fail the run tests named in design "Testing". Restore the code after each.
- [x] 3.3 Document the levels in `README.md`:
  - after the sentence "Pages that cannot be read are skipped without failing the digest.", which ends the context paragraph that names `CATCHUP_AUTHOR_REPLIES` (wrapped over `README.md:703-705`), add this paragraph as a single unwrapped line. `test_readme_context.py` matches exact phrases, so a line break inside a checked phrase fails it:

    > Settings → Digest → **Linked pages** chooses how much of this a run reads. **Normal**, the default, reads up to `CATCHUP_LINKS_PER_ITEM` links per item, and author replies. **Shallow** reads up to 3 links per item, or fewer when `CATCHUP_LINKS_PER_ITEM` is lower, and author replies. **Off** sends no context request at all, so no linked pages or author replies are read; replies saved with a page from the browser, or kept from a followed X account's thread, are still used. Every level keeps the per-run limit. A run uses the level saved when it starts.

  - in the browser-extension section, replace "reads up to `CATCHUP_LINKS_PER_ITEM` links recorded on each saved page, as it does for website items" (wrapped over `README.md:179-181`) with "reads the links recorded on each saved page at the **Linked pages** level chosen in Settings, as it does for website items".
  - in `backend/tests/test_readme_context.py`, add the phrases `"**Linked pages** chooses how much of this a run reads"`, `"**Shallow** reads up to 3 links per item"`, `"**Off** sends no context request at all"`, and `"A run uses the level saved when it starts"` to the checked list, keeping the existing phrases.

  Verify: `uv run --offline pytest tests/test_readme_context.py` fails before the README edit and passes after it.

## 4. The Settings choice (user-interface; design D7)

- [x] 4.1 Write failing tests in `frontend/src/pages/Settings.test.tsx`:
  - add `link_depth: 'normal', link_depth_pages: { off: 0, shallow: 3, normal: 8 }, context_fetches_per_run: 60` to every preferences `GET` answer that the page applies: the default answer in `beforeEach` (`:61-63`), the `GET` answer of `loads stored images off and preserves off when saving without changing it` (`:378-381`), and the fallback answers of `explains authentication errors` (`:457`) and `shows the first-run key hint and saves preferences without exposing the key` (`:546`). Without the last two, the page reads `link_depth_pages` of `undefined` and those tests fail. These four answers are the only existing test lines that change. The fallback of `shows load failures above the Model provider heading` (`:521`) and the `PUT` answers (`:540`, `:1182`) stay as they are, because the page never applies them;
  - `shows the linked-pages choice with its numbers and cost note` ("Default choice"): `screen.findByRole('combobox', { name: 'Linked pages' })` is inside the "Step 2: Digest" section, has the value `normal`, and its options' texts are exactly `['Off — no linked pages or author replies', 'Shallow — up to 3 pages per item', 'Normal — up to 8 pages per item']`; it `toHaveAccessibleDescription("Each page read adds time to a run, and up to 3,000 characters to that item's summary request (up to 4,000 for author replies), which uses more tokens. A run makes at most 60 page requests, robots.txt files included.")`; `expectAccessible(container)` passes;
  - `names the server's own numbers` ("Server numbers"): the preferences answer has `link_depth_pages: { off: 0, shallow: 3, normal: 5 }` and `context_fetches_per_run: 40`; the Shallow and Normal options read `'Shallow — up to 3 pages per item'` and `'Normal — up to 5 pages per item'`, and the description ends with `'A run makes at most 40 page requests, robots.txt files included.'`. After unmounting the first render, with `{ off: 0, shallow: 1, normal: 1 }` they read `'Shallow — up to 1 page per item'` and `'Normal — up to 1 page per item'`;
  - `saves Off with the other digest preferences` ("Save Off"): `fireEvent.change(select, { target: { value: 'off' } })`, click Save, wait for "Settings saved.", and the preferences `PUT` body `toMatchObject({ link_depth: 'off', digest_language: 'en', show_images: true, youtube_captions: false, youtube_skip_shorts: true })`;
  - `loads a saved Off and keeps it when saving without changing it`: the `GET` answer has `link_depth: 'off'` (with the numbers); the select has the value `off`; after Save, it still has `off`, and the `PUT` body has `link_depth: 'off'`.

  Verify: the four new tests fail; the existing tests still pass with the four changed answers.
- [x] 4.2 In `frontend/src/pages/Settings.tsx`:
  - extend `Preferences` with `link_depth: 'off' | 'shallow' | 'normal'`, `link_depth_pages: { off: number; shallow: number; normal: number }`, and `context_fetches_per_run: number`; keep a `linkDepth` state and the two numbers, set from the loaded preferences (`:104-123`);
  - in the Digest group, after the language field and before the images switch, add the field of design D7: a `<label className="field-label" htmlFor="link-depth">Linked pages</label>`, a `<select className="input select" id="link-depth" aria-describedby="link-depth-note">` with the three options (values `off`, `shallow`, `normal`), labels built with `plural` from `../components/format`, and `<p className="field-hint" id="link-depth-note">` with the note;
  - send `link_depth: linkDepth` in the preferences `PUT` (`:346-352`).

  Verify: the tests from 4.1 pass; `npm test -- --run` and `npm run build` pass in `frontend/`. Mutations U1–U4 each fail the tests named in design "Testing". Restore the code after each.

## 5. Checks and report

- [x] 5.1 Run the full checks:
  - `uv run --offline pytest` in `backend/` (record the count);
  - `npm test -- --run` and `npm run build` in `frontend/` and in `extension/`, with Node 22.17.1 (record the counts);
  - `DO_NOT_TRACK=1 openspec validate add-link-depth-setting --strict`;
  - `git diff --check`.

  Do not run `docker build`, `scripts/docker-smoke.sh`, or any Docker command, and do not touch port 8800: Claude Code runs the Docker smoke and the live check at review.

  Write the commands and their real results to `docs/process/test-report-add-link-depth-setting.md`:
  - each new or changed test, the spec scenario it covers, and the mutations that it kills;
  - mutations L1–L7, G1, R1–R3, A1–A2, M1, and U1–U4, with their results;
  - the Docker smoke and the live check of design "Rollout", listed as not performed (Claude Code runs them at review), and the user's token comparison as the user's check after the merge.

  Add your entry to `docs/process/ai-usage-log.md` after the latest entry, with a faithful prompt excerpt. Leave out the session id; Claude Code adds it at review.

  Verify: every command that ran passes, and the report has the actual numbers.
