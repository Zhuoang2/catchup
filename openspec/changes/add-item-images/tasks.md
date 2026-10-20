# Tasks

Implementer notes:
- **Prerequisite.** `add-linked-pages-and-author-replies` (#48) must be merged into `main` first. This change uses migration `0005`, after `0004_item_context`, and extends #48's summary output and "Also read" layout. If #48 is not in your base, stop and report.
- **Read first.** Read `proposal.md`, `design.md` (D1–D8), and the four spec deltas under `specs/`. If something looks wrong or contradictory, stop and report instead of redesigning.
- **Work test-first with the `tdd` skill** (D-016). For each task, first write its verification items as failing tests and watch them fail, then implement until they pass. The seams to test are named in each task; they count as agreed.
- **Test rules.**
  - Backend: `respx`, the autouse DNS block, and `FakeModel`. No image is ever fetched by the backend; tests assert that.
  - Fixtures: invented, shaped like the research's sources. Do not copy text from real sites.
  - Frontend: mock `fetch`, run `expectAccessible` on new rendered states, and no real timers.
- **Out of scope:**
  - image copies or a proxy
  - `og:image`
  - podcast cover art
  - Creator updates
  - a cap per digest
- **Commits.** Commit after each task group. Do not push, tag, or open a PR.

## 1. Image candidates

- [x] 1.1 In `backend/tests/test_discovery.py`, add failing parse tests (design D1):
  - **An entry whose HTML has 2 `<img>`, one inside a `<figure>` with a `<figcaption>`:** both are candidates in order, with alt and caption.
  - **A WordPress-style item:** its `media:content` holds a `gravatar.com/avatar/…` image and one post image, and the channel `<image>` is a blavatar. Only the post image is kept.
  - **A YouTube entry with `media:thumbnail`:** one candidate, with origin `thumbnail`.
  - **A podcast entry with an audio enclosure and `itunes:image`:** no candidates.
  - **Edge cases:** `data:` and 1×1 images are skipped; duplicates are dropped; the cap is 8.
  - **No image fetched:** the respx routes see no image request.

  Verify: the tests fail before 1.2.
- [x] 1.2 Implement D1 in `backend/src/catchup/sources/feeds.py`: the `EntryImage` dataclass and `FeedEntry.images`, filled by an HTML image collector for the same HTML that `plain_text` reads.

  Verify: the 1.1 tests and all existing parse tests pass.
- [x] 1.3 Add migration `backend/src/catchup/migrations/versions/0005_item_images.py` and the model columns (D3).

  Tests first:
  - `backend/tests/test_db.py`: the head is `0005_item_images`.
  - An upgrade from `0004` keeps existing rows, and `app_settings.show_images` defaults to true.
  - A downgrade removes the columns.

  Store `image_candidates` for new items in `collection.py` and `api/sources.py`, with tests in `test_collection.py` and `test_sources_api.py`.

  Verify: the tests pass, and `uv run pytest` passes.

## 2. The summary chooses images

- [x] 2.1 Implement D2 in `backend/src/catchup/llm/prompts.py` and `backend/src/catchup/digest/summarize.py`:
  - `SummaryInput.images`, filled by the runner from `image_candidates`;
  - the `Images:` lines, with alt and caption cut to 200 characters;
  - the rules;
  - the `images` output;
  - for split items, the images go in the combine call.

  Tests first, in `backend/tests/test_digest_stages.py` and `test_long_summaries.py`:
  - the user message lists `I1`, `I2` with their alt and caption;
  - the system prompt has the rules;
  - an item without candidates has no `Images:` block;
  - more than 3 choices are cut to 3;
  - unknown and duplicate refs are dropped;
  - an empty model alt falls back to the feed alt, then to "Image from <source name>".

  Verify: the tests fail first, then pass.
- [x] 2.2 In `record()` (`digest/runner.py`), store `summary_images`, a list of `{url, alt}`, with the summary. A reused summary keeps them.

  Tests first in `test_digest_runner.py`.

  Verify: the tests pass.

## 3. Snapshot, API, and the setting

- [x] 3.1 The snapshot copies `summary_images` into `DigestItem.images`, and `api/digests.py` returns `images` for each summarized item (D4).

  Tests first in `backend/tests/test_digest_history.py`:
  - a digest item returns its images in order;
  - an older digest returns `[]`;
  - deleting the source keeps the images;
  - update the exact item dict.

  Verify: the tests pass.
- [x] 3.2 Add `show_images` to `GET` and `PUT /api/settings/preferences` (`backend/src/catchup/api/settings.py`).

  Tests first in `backend/tests/test_settings_api.py`: the default is true, it can be saved, and the other preferences stay unchanged.

  Verify: the tests pass.

## 4. Reading layout and Settings

- [x] 4.1 In `frontend/src/components/DigestArticle.tsx`, its type, and the CSS, render the images block after the summary and before "Also read" (D5).

  Tests first, in `frontend/src/components/DigestArticle.test.tsx` and `frontend/src/pages/DigestView.test.tsx`:
  - each image has its `src` and `alt`, `loading="lazy"`, `decoding="async"`, and `referrerpolicy="no-referrer"`;
  - the order is kept;
  - a fired `error` event hides that figure;
  - there is no block when the list is empty;
  - there is no `img` at all when `show_images` is false;
  - axe passes.

  Update `DigestView.test.tsx:47` (no `img`, now with images turned off, or with no images) and `:248-276` (item children). Extend the `tokens.test.ts` guards for the new class, and name each change in the report.

  Verify: `npm test -- --run` and `npm run build` pass.
- [x] 4.2 Read `show_images` with the other startup requests, in `frontend/src/pages/DigestView.tsx` and `frontend/src/pages/Home.tsx`. A failed read shows images.

  Tests first: off → no `img`; the read fails → images are shown.

  Verify: the tests pass.
- [x] 4.3 In `frontend/src/pages/Settings.tsx`, add the toggle "Show images from source sites", with its note, to the Digest group (D6).

  Tests first in `frontend/src/pages/Settings.test.tsx`:
  - the toggle is on by default;
  - the note is associated through `aria-describedby`;
  - saving sends `show_images`;
  - the clickable area is limited to the control and its label;
  - axe passes.

  Verify: the tests pass.

## 5. Docs and checks

- [ ] 5.1 In `README.md`, add a privacy note: images are loaded from their source sites when a digest is opened, with no referrer, and can be turned off in Settings.

  Verify: the README states the setting's name and default.
- [ ] 5.2 Run `npm run build` in `frontend/` first. Then run:
  - `uv run pytest --cov=catchup --cov-report=term` in `backend/`
  - `npm test -- --run` in `frontend/`
  - `openspec validate add-item-images --strict`
  - a local `docker build`, if available

  Write the commands and their real results to `docs/process/test-report-add-item-images.md`, with the red-first results for each group. Name the manual checks that were not performed: a real run on Simon Willison and The Verge, and the layout at 1440, 900, and 420 px in both themes.

  Add this change's line to `docs/process/coverage-summary.md`. Add your entry to `docs/process/ai-usage-log.md` after the latest entry, with a faithful excerpt of the prompt you actually received, and the tool and model. Leave out the session id.

  Verify: every command passes, and the report has the actual numbers.
