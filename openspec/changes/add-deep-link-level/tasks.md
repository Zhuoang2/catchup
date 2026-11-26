# Tasks

Implementer notes:
- **Read first.** Read `proposal.md`, `design.md` (all of "Context", D1–D6, "Testing"), and the two spec deltas under `specs/`. The plan follows the recommendations of U1–U4. If something looks wrong or contradictory, stop and report instead of redesigning.
- **Work test-first with the `tdd` skill** (D-016). For each group, first write its tests, run them, and watch them fail as the task says. Then change the code. The seams are listed in design "Testing", and they count as agreed.
- **Test rules.**
  - No real network: every context fetch goes through `respx.mock(assert_all_mocked=True, assert_all_called=False)` with the `public_dns` fixture, as the tests in `backend/tests/test_context_gather.py` do. `assert_all_called=False` is required wherever a test mocks a route that must not be called.
  - Change no existing test, except where a task says so. Adding imports and small helpers to an existing test file is allowed.
  - For each named mutation, apply it alone, run the named tests, record the result, and restore the code exactly. Compare with `git diff` after restoring.
  - Set the level in backend run tests with the existing helper `set_level(environment, "deep")` (`backend/tests/test_context_gather.py:45-48`), and server numbers with `environment.app.state.settings = replace(environment.app.state.settings, ...)`.
- **Environment.**
  - Backend: run commands in `backend/` with `uv run --offline`, without installing new packages.
  - Frontend: use Node 22.17.1 with `export PATH="$HOME/.nvm/versions/node/v22.17.1/bin:$PATH"`. Then run `npm ci --offline --no-audit --no-fund` in `frontend/`, and again in `extension/`. Both install the locked packages from the local npm cache. If either fails, stop and report. Do not download packages, and do not change `package.json` or `package-lock.json`.
- **Out of scope:**
  - backend files other than `context/depth.py`, `context/gather.py`, and `api/settings.py`, and the tests named below; no migration, no change to `models.py`, `config.py`, `digest/runner.py`, `context/links.py`, or `context/comments.py`;
  - frontend files other than `src/pages/Settings.tsx` and `src/pages/Settings.test.tsx`;
  - the extension, the progress formula, and dependency versions.
- **Do not edit** `proposal.md`, `design.md`, the spec deltas, `docs/process/decision-log.md`, or `docs/process/requirements-changes.md`. Claude Code wrote D-044 and the requirements row with the plan.
- **Do not** run `docker build`, `scripts/docker-smoke.sh`, `docker system prune`, or any other Docker command, and do not touch port 8800. You edit `scripts/docker-smoke.sh` in task 2.2 but never run it; Claude Code runs it at review. Do not push, tag, or open a PR. Never write keys, tokens, or secrets anywhere.
- **Commits.** Commit after each task group.

## 1. Deep in the context pass (content-collection; design D1, D2)

- [x] 1.1 Write failing tests:
  - in `backend/tests/test_context_depth.py`, rewrite the rows of `test_context_limits` so that every expected value names all five fields, `ContextLimits(links_per_item, fetches_per_run, author_replies, page_chars, item_chars)` (design D1: a row that relies on the defaults cannot catch mutation E6). Keep the parameters and ids, and use these rows:
    - `off`: `("off", 8, 60, True, ContextLimits(0, 0, False, 3000, 16000))`;
    - `shallow`: `("shallow", 8, 60, True, ContextLimits(3, 60, True, 3000, 16000))`;
    - `shallow_under_2`: `("shallow", 2, 60, True, ContextLimits(2, 60, True, 3000, 16000))`;
    - `shallow_no_replies`: `("shallow", 8, 60, False, ContextLimits(3, 60, False, 3000, 16000))`;
    - `normal`: `("normal", 8, 60, True, ContextLimits(8, 60, True, 3000, 16000))`;
    - `normal_server`: `("normal", 5, 40, False, ContextLimits(5, 40, False, 3000, 16000))`;
    - `deep` (new): `("deep", 8, 60, True, ContextLimits(16, 120, True, 6000, 32000))`;
    - `deep_server` (new): `("deep", 5, 40, True, ContextLimits(10, 80, True, 6000, 32000))`;
    - `deep_no_replies` (new): `("deep", 8, 60, False, ContextLimits(16, 120, False, 6000, 32000))`;
    - `unknown`: the level changes from `"deep"` to `"maximum"`: `("maximum", 8, 60, True, ContextLimits(8, 60, True, 3000, 16000))`;
    - `empty`: `("", 8, 60, True, ContextLimits(8, 60, True, 3000, 16000))`.

    These rows and the `ids=[...]` list, which becomes `["off", "shallow", "shallow_under_2", "shallow_no_replies", "normal", "normal_server", "deep", "deep_server", "deep_no_replies", "unknown", "empty"]`, are the only existing lines of this file that change in this group.
  - in `backend/tests/test_context_gather.py`, using `setup`, `html`, `set_level`, `stub_collection`, and `execute`:
    - `test_deep_reads_twice_normals_links` ("Deep reads twice Normal's links"): `setup(environment, [(f"https://h{i}.example/p", str(i)) for i in range(17)])`, level `deep`; each site's robots.txt answers 404 and each page answers `html(str(i), "Linked text " * 40)`. The run succeeds; the page routes are called `[1] * 16 + [0]` times and the robots.txt routes `[1] * 16 + [0]` times; `(context_total, context_done) == (16, 16)`.
    - `test_page_cut_follows_the_level` ("Deep keeps more of each page"), parametrized over `(level, expected)` = `("shallow", 3000)`, `("normal", 3000)`, `("deep", 6000)` with ids `shallow`, `normal`, `deep`: one link `https://docs.example/long`, robots.txt 404, the page answers `html("Long", "x" * 10000)`. The run succeeds, and the item has exactly one `ItemContext` row, whose `text` has `expected` characters. (The probe in design "Context" shows that `extract` keeps all 10,000 characters of this page.)
    - `test_deep_caps_an_items_linked_context` ("Deep caps an item's linked context"): eight links `https://docs.example/{i}` for `i` in `range(8)`, level `deep`, robots.txt 404, each page `html(str(i), "x" * 7000)`. The run succeeds; the stored `ItemContext` texts, ordered by `position`, have lengths `[6000, 6000, 6000, 6000, 6000, 2000]`; the page routes are called `[1, 1, 1, 1, 1, 1, 0, 0]` times.
    - `test_deep_doubles_the_run_limit` ("Deep doubles the per-run limit"), parametrized over `(level, calls)` = `("normal", [1, 1, 1, 1, 0, 0, 0, 0])` and `("deep", [1] * 8)` with ids `normal`, `deep`: `context_fetches_per_run=5`; eight links `https://docs.example/{i}`, robots.txt 404, each page `html(str(i), "Linked text " * 40)`. The run succeeds, and the page routes are called `calls` times (robots.txt takes one unit of the limit: 5 at Normal, 10 at Deep).
    - `test_deep_reads_author_replies` ("Deep reads author replies"): `setup(environment, [], comments=2)`, level `deep`; robots.txt of `https://s0.example` answers 404, and the post page `https://s0.example/0` answers the comment body of `test_author_reply_context_and_disable_switch` (`backend/tests/test_context_gather.py:841-856`). The run succeeds, and the item's contexts are exactly `[("A1", "author_replies")]` as `(ref, kind)`, with `"Because of the update."` in the text.

  Verify: `test_context_depth.py` fails to collect with `TypeError: ContextLimits.__init__() takes 4 positional arguments but 6 were given`, because the parametrize rows build five-field `ContextLimits` objects at import time; pytest reports one collection error and runs none of the file's tests. Run `test_context_gather.py` in a separate pytest command, because a collection error interrupts the whole run. In `test_context_gather.py`, `test_deep_reads_twice_normals_links`, `test_page_cut_follows_the_level[deep]`, `test_deep_caps_an_items_linked_context`, and `test_deep_doubles_the_run_limit[deep]` fail, because a stored `"deep"` gets Normal's numbers today (`depth.py:22-23`). `test_page_cut_follows_the_level[shallow]`, `[normal]`, `test_deep_doubles_the_run_limit[normal]`, and `test_deep_reads_author_replies` pass already; mutations E5 and E6 in 1.2 show that they can fail.
- [x] 1.2 Implement design D1 and D2:
  - in `backend/src/catchup/context/depth.py`: the constants `DEEP_FACTOR = 2`, `PAGE_CHARS = 3_000`, `ITEM_CHARS = 16_000`, `DEEP_PAGE_CHARS = 6_000`, and `DEEP_ITEM_CHARS = 32_000`; `ContextLimits` gains `page_chars: int = PAGE_CHARS` and `item_chars: int = ITEM_CHARS`; `context_limits` returns D1's Deep row for `"deep"` and keeps every other row. Leave `LINK_DEPTHS` and `link_depth_pages` as they are (group 2 changes them);
  - in `backend/src/catchup/context/gather.py`, `gather_item` uses `limits.item_chars` in the loop check (`:172`) and in the cut (`:191`), and `limits.page_chars` in the cut, as D2 shows. Change nothing else in the pass.

  Verify: the tests from 1.1 pass, and `uv run --offline pytest` passes in `backend/`, with every other existing test unchanged. Mutations E1–E6 and G1–G3 each fail the tests named in design "Testing" (E1–E6 on `depth.py`, G1–G3 on `gather.py`). Restore the code after each.

## 2. The levels in the API, the smoke script, and the README (content-collection, user-interface; design D1, D3, D5, D6)

- [ ] 2.1 Write failing tests:
  - in `backend/tests/test_context_depth.py`:
    - `test_link_depths`: `LINK_DEPTHS == ("off", "shallow", "normal", "deep")`;
    - `test_link_depth_pages`: every expected dict gains `"deep"`: `(8, {"off": 0, "shallow": 3, "normal": 8, "deep": 16})`, `(5, {"off": 0, "shallow": 3, "normal": 5, "deep": 10})`, `(2, {"off": 0, "shallow": 2, "normal": 2, "deep": 4})`, `(1, {"off": 0, "shallow": 1, "normal": 1, "deep": 2})`;
  - in `backend/tests/test_settings_api.py`:
    - in `test_preference_save_and_read`, `test_partial_preference_updates_keep_other_values`, and `test_image_preference_can_be_saved_without_changing_others`, every expected answer's `link_depth_pages` becomes `{"off": 0, "shallow": 3, "normal": 8, "deep": 16}` and gains `"deep_context_fetches_per_run": 120`;
    - `test_link_depth_save_and_read`: after the existing steps, `PUT {"link_depth": "deep"}` answers 200 with `link_depth` `"deep"`, and `GET` answers `"deep"`;
    - `test_invalid_link_depth`: the values become `"maximum"`, `""`, `"OFF"`, `"Deep"`, and `"none"` (`"deep"` is now a level); each answer also has `response.json()["error"]["message"] == "Choose Off, Shallow, Normal, or Deep for linked pages."`;
    - `test_preferences_report_the_server_numbers`: with `links_per_item=5, context_fetches_per_run=40`, `GET` answers `"link_depth_pages": {"off": 0, "shallow": 3, "normal": 5, "deep": 10}`, `"context_fetches_per_run": 40`, and `"deep_context_fetches_per_run": 80`; with `links_per_item=2`, `{"off": 0, "shallow": 2, "normal": 2, "deep": 4}`;
    - `test_preference_numbers_cannot_be_written`: the `PUT` also sends `"deep_context_fetches_per_run": 1`; `GET` still answers `"link_depth_pages": {"off": 0, "shallow": 3, "normal": 8, "deep": 16}`, `"context_fetches_per_run": 60`, and `"deep_context_fetches_per_run": 120`.

    These are the only existing tests in this file that change.
  - in `backend/tests/test_readme_context.py`, add the phrases `"**Deep** reads up to twice"` and `"with a small model, prefer Normal or Shallow"` to the checked list, keeping the existing phrases.

  Verify: every changed and new test fails: `LINK_DEPTHS` and `link_depth_pages` lack Deep, the `GET` answer lacks `deep_context_fetches_per_run`, `"deep"` is refused, and the README lacks both phrases.
- [ ] 2.2 Implement design D1 (the list and the pages), D3, D5, and D6:
  - in `backend/src/catchup/context/depth.py`, `LINK_DEPTHS = ("off", "shallow", "normal", "deep")`, and `link_depth_pages` adds `"deep": DEEP_FACTOR * settings.links_per_item`;
  - in `backend/src/catchup/api/settings.py`, `read_preferences` adds `"deep_context_fetches_per_run": context_limits("deep", request.app.state.settings).fetches_per_run` after `context_fetches_per_run`, and the refusal message becomes "Choose Off, Shallow, Normal, or Deep for linked pages."; import `context_limits` from `catchup.context.depth` next to `LINK_DEPTHS` (`api/settings.py:14`);
  - in `README.md`, in the paragraph that starts "Settings → Digest → **Linked pages** chooses how much of this a run reads." (`README.md:716`, one unwrapped line), insert after the Shallow sentence: "**Deep** reads up to twice `CATCHUP_LINKS_PER_ITEM` links per item, keeps up to 6,000 characters of each page and 32,000 per item, and allows twice `CATCHUP_CONTEXT_FETCHES_PER_RUN` requests per run; author replies are read as at Normal." Insert at the end of the paragraph, after "A run uses the level saved when it starts.": "Deep's larger context leaves less of each summary request for the item's own text, so long items are summarized in more parts; with a small model, prefer Normal or Shallow." In the same paragraph, replace "Every level keeps the per-run limit." with "Shallow and Normal keep the per-run limit." Keep the paragraph on one line, because `test_readme_context.py` matches exact phrases;
  - in `scripts/docker-smoke.sh`, both expected preferences answers (`:86-90` and `:122-126`) get `"link_depth_pages": {"off": 0, "shallow": 3, "normal": 8, "deep": 16}` and `"deep_context_fetches_per_run": 120`. Do not run the script.

  Verify: the tests from 2.1 pass, and `uv run --offline pytest` passes in `backend/`. `bash -n scripts/docker-smoke.sh` passes. Mutations E7, E8, A1, A2, and R1 each fail the tests named in design "Testing". Restore the code after each.

## 3. The Settings choice (user-interface; design D4)

- [ ] 3.1 Write failing tests in `frontend/src/pages/Settings.test.tsx`:
  - in every preferences `GET` answer that the page applies, `link_depth_pages` gains `deep: 16` and the answer gains `deep_context_fetches_per_run: 120`: `mockLinkedPages` (`:55-64`), the default answer in `beforeEach` (`:80-83`), and the `GET` answers of `loads stored images off and preserves off when saving without changing it` (`:457`), `explains authentication errors` (`:535`), and `shows the first-run key hint and saves preferences without exposing the key` (`:625`). These answers are the only existing lines that change, apart from the two tests below;
  - `shows the linked-pages choice with its numbers and cost note` (changed; "Default choice"): the options' texts are exactly `['Off — no linked pages or author replies', 'Shallow — up to 3 pages per item', 'Normal — up to 8 pages per item', 'Deep — up to 16 pages per item']`, and the select `toHaveAccessibleDescription("Each page read adds time to a run, and up to 3,000 characters to that item's summary request (6,000 at Deep, and up to 4,000 for author replies), which uses more tokens. A run makes at most 60 page requests (120 at Deep), robots.txt files included.")`; the rest of the test stays;
  - `names the server's own numbers` (changed; "Server numbers"): the first answer has `link_depth_pages: { off: 0, shallow: 3, normal: 5, deep: 10 }`, `context_fetches_per_run: 40`, and `deep_context_fetches_per_run: 80`; the options include `'Deep — up to 10 pages per item'`, and the description matches `/A run makes at most 40 page requests \(80 at Deep\), robots\.txt files included\.$/`. The second answer has `{ off: 0, shallow: 1, normal: 1, deep: 2 }`, and the options include `'Deep — up to 2 pages per item'`;
  - `saves Deep with the other digest preferences` (new; "Save Deep"): `fireEvent.change(select, { target: { value: 'deep' } })`, click Save, wait for "Settings saved.", and the preferences `PUT` body `toMatchObject({ link_depth: 'deep', digest_language: 'en', show_images: true, youtube_captions: false, youtube_skip_shorts: true })`;
  - `loads a saved Deep and keeps it when saving without changing it` (new): `mockLinkedPages({ link_depth: 'deep' })`; the select has the value `deep`; after Save, it still has `deep`, and the `PUT` body has `link_depth: 'deep'`.

  Verify: the two changed and two new tests fail (there is no Deep option); the other existing tests still pass with the changed answers.
- [ ] 3.2 In `frontend/src/pages/Settings.tsx`, as in design D4:
  - `Preferences` (`:12-14`): `link_depth: 'off' | 'shallow' | 'normal' | 'deep'`, `link_depth_pages: { off: number; shallow: number; normal: number; deep: number }`, and `deep_context_fetches_per_run: number`; the initial `linkDepthPages` state gains `deep: 0`, and a new `deepContextFetchesPerRun` state starts at 0 and is set from the loaded preferences next to `setContextFetchesPerRun` (`:136-138`);
  - after the Normal option (`:485`), add `<option value="deep">Deep — up to {plural(linkDepthPages.deep, 'page')} per item</option>`;
  - the note (`:487-490`) becomes design D4's text: "(6,000 at Deep, and up to 4,000 for author replies)" in place of "(up to 4,000 for author replies)", and "page requests (… at Deep)" with `{deepContextFetchesPerRun}` after `{plural(contextFetchesPerRun, 'page request')}`.

  Verify: the tests from 3.1 pass; `npm test -- --run` and `npm run build` pass in `frontend/`. Mutations F1–F4 each fail the tests named in design "Testing". Restore the code after each.

## 4. Checks and report

- [ ] 4.1 Run the full checks:
  - `uv run --offline pytest` in `backend/` (record the count);
  - `npm test -- --run` and `npm run build` in `frontend/` and in `extension/`, with Node 22.17.1 (record the counts);
  - `DO_NOT_TRACK=1 openspec validate add-deep-link-level --strict`;
  - `git diff --check`.

  Do not run `docker build`, `scripts/docker-smoke.sh`, or any Docker command, and do not touch port 8800: Claude Code runs the Docker smoke and the live check at review.

  Write the commands and their real results to `docs/process/test-report-add-deep-link-level.md`:
  - each new or changed test, the spec scenario it covers, and the mutations that it kills;
  - mutations E1–E8, G1–G3, A1–A2, F1–F4, and R1, with their results;
  - the Docker smoke and the live check of design "Rollout", listed as not performed (Claude Code runs them at review), and the user's token comparison as the user's check after the merge.

  Add your entry to `docs/process/ai-usage-log.md` after the latest entry, with a faithful prompt excerpt. Leave out the session id; Claude Code adds it at review.

  Verify: every command that ran passes, and the report has the actual numbers.
