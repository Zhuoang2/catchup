# Tasks

Implementer notes:
- **Read first.** Read `proposal.md`, `design.md` (D1–D9), and the four spec deltas under `specs/`. If something looks wrong or contradictory, stop and report instead of redesigning.
- **Work test-first with the `tdd` skill** (D-016). For each task, first write its verification items as failing tests and watch them fail, then implement until they pass. The seams to test are named in each task; they count as agreed.
- **Test rules.**
  - Backend: `respx` and the autouse DNS block, no real network. Model calls use the existing `FakeModel` (`backend/tests/test_digest_runner.py:24-49`), or a scripted client. Use virtual sleeps as `conftest.py` already does.
  - Fixtures: invented HTML and feeds, shaped like the research's examples. Do not copy text from real sites.
  - Frontend: mock `fetch`, run `expectAccessible` on new rendered states, and no real timers.
- **Out of scope:**
  - the user-facing depth setting
  - X (#41)
  - comment systems loaded by script
  - podcast episodes with audio, and YouTube items
  - re-gathering context for already-summarized items
  - the item's own article fetch (`article_text`)
- **Commits.** Commit after each task group. Do not push, tag, or open a PR.

## 1. Parse and store links and comment pointers

- [x] 1.1 In `backend/tests/test_discovery.py`, add failing parse tests with invented fixtures:
  - **An Atom entry whose HTML has 5 links:** a GitHub release, a project page, a changelog, and 2 same-site `/tags/` links. `FeedEntry.links` holds all 5 in body order, with their anchor text, resolved to absolute URLs, and duplicates dropped.
  - **An RSS 2.0 item with `comments`, `wfw:commentRss`, `slash:comments` = 12, and `dc:creator`.** The entry's `comments_url`, `comment_feed_url`, `comment_count == 12`, and `author` are set.
  - **An entry without these elements** gets an empty `links`, and `None` for each pointer.

  Verify: the tests fail before 1.2.
- [x] 1.2 Implement design D1 in `backend/src/catchup/sources/feeds.py`: the `EntryLink` dataclass, the new `FeedEntry` fields with defaults, and link extraction from the same HTML that `plain_text` reads.

  Verify: the 1.1 tests and all existing parse tests pass.
- [x] 1.3 Add migration `backend/src/catchup/migrations/versions/0004_item_context.py` and the model changes in `models.py` for design D6:
  - the `items` columns;
  - the `item_contexts` table, as an `ItemContext` model with a cascade from `Item`;
  - `digest_items.context_links`;
  - `digest_runs.context_total` and `context_done`.

  Tests first:
  - `backend/tests/test_db.py`: the migration head is `0004_item_context`.
  - An upgrade from `0003` keeps existing rows, with `context_status` null.
  - A downgrade removes the new table and columns.

  Verify: the tests pass, and `uv run pytest` passes.
- [x] 1.4 Store the parsed links and pointers on new items, in both `check_source` (`backend/src/catchup/collection.py`) and source confirmation (`backend/src/catchup/api/sources.py`).

  Tests first:
  - `test_collection.py`: a new website item has `entry_links`, `comment_count`, and `entry_author`.
  - `test_sources_api.py`: a confirmed pending item has the same.

  Verify: the tests pass.

## 2. Link rules and robots.txt

- [x] 2.1 Create `backend/src/catchup/context/__init__.py` and `context/links.py` with `related_links` (design D2). The tests in a new `backend/tests/test_context_links.py` come first, and cover:
  - each dropped kind: the item itself, `/tags/` and the other taxonomy paths, share and login pages, x.com, image and PDF URLs, and non-http schemes;
  - Hacker News kept;
  - body order kept;
  - the `limit` argument;
  - the research example: of the 5 `llm-tools-datasette`-shaped links, the release, project, and changelog are kept, and the 2 tag links are dropped.

  Verify: the tests fail first, then pass.
- [x] 2.2 Create `context/robots.py` with `RobotsCache` (design D3). The tests in a new `backend/tests/test_context_robots.py` come first, with `respx`:
  - `Disallow` for `CatchUp` on a path refuses that URL and allows others;
  - a 404 robots.txt allows;
  - 401 and 403 disallow;
  - a fetch error allows;
  - one robots.txt request per host per cache;
  - the robots.txt request counts against the shared budget and uses the spacer.

  Verify: the tests fail first, then pass.

## 3. Author replies

- [x] 3.1 Create `context/comments.py` (design D5). The tests in a new `backend/tests/test_context_comments.py` come first, with invented fixtures:
  - A WordPress-style post page with 6 comments, 2 of them `bypostauthor` and nested under a reader's comment. It returns 2 replies, each with its parent's text.
  - The same page without `bypostauthor`, where one comment's `.fn` equals the entry author. That comment is returned.
  - A page with no comment markup: the comment feed (RSS items "By: <name>" with `dc:creator`) is used. Only the author's items are kept, and pingbacks are skipped.
  - The limits: at most 10 replies and 4,000 characters, and each text cut to 600.
  - No author replies at all: nothing is returned.

  Verify: the tests fail first, then pass.

## 4. The context pass in the run

- [x] 4.1 Add the settings to `backend/src/catchup/config.py`: `links_per_item` (`CATCHUP_LINKS_PER_ITEM`, default 8), `context_fetches_per_run` (`CATCHUP_CONTEXT_FETCHES_PER_RUN`, default 60), and `author_replies` (`CATCHUP_AUTHOR_REPLIES`, default on; `0`, `false`, and `no` turn it off). The first two use `positive_env`.

  Tests first in `backend/tests/test_config.py`: the defaults, overrides, and rejection of values ≤ 0.

  Verify: the tests pass.
- [x] 4.2 Create `context/gather.py`, and call it from `backend/src/catchup/digest/runner.py` after the caption pass and before `select_pending` (design D4). Also update `run_detail` to return `context_total` and `context_done`.

  Write the tests first, in a new `backend/tests/test_context_gather.py`, and through the runner in `test_digest_runner.py`, with `respx`:
  1. A pending website item with 3 related links and 2 tag links: 3 `link` contexts are stored (`L1`–`L3`), each cut to 3,000 characters with its page title, and the tag pages are not requested.
  2. An item whose linked texts exceed 16,000 characters stops adding pages at that limit.
  3. An item with `comment_count > 0` gets one `author_replies` context (`A1`).
  4. robots.txt disallowing one link skips it.
  5. A link answering 404, or timing out, is skipped, and the run still succeeds.
  6. With `CATCHUP_CONTEXT_FETCHES_PER_RUN=2`, only 2 fetches happen. Items not reached keep `context_status` null, and the run succeeds.
  7. A second run after a failed one does not fetch the links again (`context_status == "gathered"`).
  8. Podcast episodes with audio and YouTube items get no context, and are not requested.
  9. `context_total` and `context_done` in `run_detail` count the planned and finished fetches.
  10. With `CATCHUP_AUTHOR_REPLIES=0`, no post page is fetched for comments.
  11. Requests to one host are spaced by the run's `HostSpacer` (patch it as `test_digest_runner.py:658-698` does).

  Verify: the tests fail first, then pass, and `uv run pytest` passes.

## 5. Summaries use the context

- [ ] 5.1 In `backend/src/catchup/llm/prompts.py` and `backend/src/catchup/digest/summarize.py`, implement design D7:
  - `SummaryInput` gains `context` (a list of `{ref, kind, title, host, text}`);
  - the runner fills it from `ItemContext` rows;
  - `summary_messages` adds the labeled blocks and the rules;
  - the output includes `used`;
  - split items send context to the combine call;
  - the splitting budget subtracts the context's length, with a 2,000-character floor.

  Tests first, in `backend/tests/test_digest_stages.py` and `test_long_summaries.py`:
  - the user message contains "Context L1 — linked page:" with the title and host;
  - the system prompt has the three new rules;
  - `used` refs are returned;
  - an unknown ref is dropped;
  - an item without context has no "Context" block, and its prompt is unchanged;
  - for a split item, the context appears only in the combine call;
  - the budget includes the context.

  Verify: the tests fail first, then pass.
- [ ] 5.2 In `record()` (`digest/runner.py`), set `ItemContext.used` from the validated refs, and clear the others. A cached summary keeps its flags.

  Tests first, in `test_digest_runner.py`: after a run, the used rows are flagged; a second run that reuses the cached summary keeps the flags.

  Verify: the tests pass.

## 6. Snapshot, API, and reading layout

- [ ] 6.1 Snapshot and API (design D8).
  - The snapshot (`digest/runner.py`) copies the used contexts, `{title, url, kind}` in ref order, into `DigestItem.context_links`.
  - `api/digests.py` returns `also_read` for each summarized item (`[]` when there is none, and for older digests).

  Tests first in `backend/tests/test_digest_history.py`:
  - a digest item shows `also_read` with the used page only;
  - a digest saved before the migration returns `[]`;
  - deleting the item's source keeps `also_read`;
  - update the exact item dict at `:289-292`.

  Verify: the tests pass.
- [ ] 6.2 In `frontend/src/components/DigestArticle.tsx`, its type, and the CSS, render the "Also read" line after the summary when `also_read` is not empty (design D8).

  Tests first, in `frontend/src/components/DigestArticle.test.tsx` and `frontend/src/pages/DigestView.test.tsx`:
  - The text is "Also read:" followed by the linked titles, separated by "·".
  - Each link has `href`, `target="_blank"`, and `rel="noopener noreferrer"`.
  - There is no line when the list is empty.
  - The axe check passes.
  - Update the item-children test at `DigestView.test.tsx:248-276`, and add a case with an "Also read" line.

  If a CSS structure guard in `src/styles/tokens.test.ts` needs the new class, extend it, and name the change in the report.

  Verify: `npm test -- --run` and `npm run build` pass.
- [ ] 6.3 In `frontend/src/pages/Home.tsx`, show "Linked pages read: n of N" as the progress label when the run is `collecting`, every source is checked, and `context_total > 0` (design D8).

  Tests first in `frontend/src/pages/Home.test.tsx`:
  - the label and the progress bar show 7 of 20;
  - "Sources checked" still shows while sources are being checked;
  - the status region text stays as it is today.

  Verify: the tests pass.

## 7. Docs and checks

- [ ] 7.1 In `README.md`, next to the other run settings (near `CATCHUP_CAPTIONS_PER_RUN`), document:
  - the three settings;
  - that context fetches honor robots.txt;
  - that they read only public pages.

  Verify: the README states the defaults from 4.1.
- [ ] 7.2 Run `npm run build` in `frontend/` first. Then run:
  - `uv run pytest --cov=catchup --cov-report=term` in `backend/`
  - `npm test -- --run` in `frontend/`
  - `openspec validate add-linked-pages-and-author-replies --strict`
  - a local `docker build`, if available

  Write the commands and their real results to `docs/process/test-report-add-linked-pages-and-author-replies.md`, with the red-first results for each group. Name the manual checks that were not performed: a real run on Simon Willison and Terry Tao feeds, and a real-model token comparison.

  Add this change's line to `docs/process/coverage-summary.md`. Add your entry to `docs/process/ai-usage-log.md` after the latest entry, with a faithful excerpt of the prompt you actually received, and the tool and model. Leave out the session id.

  Verify: every command passes, and the report has the actual numbers.
