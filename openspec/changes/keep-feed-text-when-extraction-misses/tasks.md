# Tasks

Implementer notes:
- **Read first.** Read `proposal.md`, `design.md` (D1–D3), and `specs/content-collection/spec.md`. If something looks wrong or contradictory, stop and report instead of redesigning.
- **Work test-first with the `tdd` skill** (D-016). For each task, first write its verification items as failing tests and watch them fail, then implement until they pass. The seams to test are the ones named in each task; they count as agreed.
- **Test rules.** Use `respx` and the existing DNS fixtures, with no real network. Where a case needs a specific extraction result, monkeypatch `catchup.collection.extract`, as `test_extractor_exception_falls_back_to_feed` does. Use invented feed and page text. Do not copy text from real sites.
- **Out of scope:**
  - `safe_fetch`
  - the threshold (`short_text_chars`)
  - the extractor and its settings
  - podcast and YouTube handling
  - items already stored
  - following the links inside an entry (#48)
- **Commits.** Commit after each task group. Do not push, tag, or open a PR.

## 1. Keep the feed text when the extraction misses it

- [x] 1.1 Add failing tests.

  **In `backend/tests/test_collection.py`,** each test runs a check through `run_check` on a website feed whose entry has a short feed text (below the threshold), and inspects the stored `Item`:
  1. **Extraction misses the post.**
     - The feed text is an invented release note of about 250 characters.
     - `extract` returns a sidebar-like text: a date line, "Recent articles", and three invented post titles.
     - The stored text is the feed text, then one blank line, then the sidebar text, and `content_origin` is `"article"`.
  2. **Excerpt covered.** The feed text is the opening sentence of the extracted text. The stored text equals the extracted text exactly, with no copy of the feed text before it.
  3. **The 60% boundary.** The feed text has exactly 10 distinct words of 3 or more characters.
     - If the extraction contains 6 of them, it covers the feed text, and only the extracted text is stored.
     - If it contains 5, the feed text is kept first.
  4. **The 3-character boundary.**
     - Every word of the feed text has exactly 3 characters, and the extraction contains none of them. The feed text is kept first.
     - A feed text whose words all have 1 or 2 characters counts as covered, so only the extracted text is stored.
  5. **Case.** The feed text is "Rust Release Notes For October", and the extraction contains the same words in lower case. It covers the feed text.
  6. **CJK.** The feed text is the Chinese sentence "这是一段摘要，介绍新版本的变化。". The extraction contains it inside a longer Chinese paragraph, with no punctuation after "变化". It covers the feed text.
  7. **No feed text.** The entry has an empty description, and only the extracted text is stored.
  8. **The existing replacement test.** In `test_short_feed_excerpt_is_replaced_with_extracted_article`, change the article fixture so that its paragraph begins with the feed excerpt "Short excerpt". Assert that the stored text contains "Short excerpt" exactly once. The existing fallback tests stay unchanged.

  **In `backend/tests/test_sources_api.py`,** for the confirm path:
  9. Call `article_text` directly, next to `test_large_article_keeps_feed_text`. Use an entry with a short excerpt, and an article route whose page extracts to text that does not contain the excerpt's words. Monkeypatch `extract`, or use a page whose body is only a list of other titles. The result is `(excerpt + "\n\n" + extracted, "article")`.

  Verify: the report lists which tests fail before 1.2 and which already pass as guards. Cases 1, 3 (5 of 10), the first case of 4, and 9 must fail before 1.2.
- [x] 1.2 Implement design D1 and D2 in `backend/src/catchup/collection.py`:
  - one helper, for example `_covers(feed_text, extracted)`;
  - module constants for the 60% share and the 3-character minimum;
  - `article_text` stores the extracted text alone when it covers the feed text, and `feed text + "\n\n" + extracted text` otherwise.

  Keep every existing fallback as it is.

  Verify: the 1.1 tests pass, the existing `test_collection.py` and `test_sources_api.py` tests pass, and `uv run pytest` passes in `backend/`.

## 2. Checks and report

- [x] 2.1 Run the full checks:
  - `npm run build` in `frontend/` first, so that backend coverage is measured with `frontend/dist` present
  - `uv run pytest --cov=catchup --cov-report=term` in `backend/`
  - `openspec validate keep-feed-text-when-extraction-misses --strict`

  Write the commands and their real results to `docs/process/test-report-keep-feed-text-when-extraction-misses.md`. Include the red-first results of 1.1, and the coverage of `collection.py`. Name the manual check that was not performed: a real run on a local instance that includes the #47 post.

  Add your entry to `docs/process/ai-usage-log.md` after the latest entry, with a faithful excerpt of the prompt you actually received, and the tool and model. Leave out the session id; Claude Code adds it at review.

  Verify: every command passes, and the report has the actual numbers.

## 3. Fix round 1 (test gaps from review)

Review found no wrong behavior, but three decisions in design D1 are not pinned by any test. This group changes only `backend/tests/test_collection.py` and the docs. Do not change `collection.py`. The code is already correct, so the red step for each new check is a named temporary mutation of `collection.py`, applied by hand:
1. Write the check and see it pass.
2. Apply the mutation, and see the check fail.
3. Revert the mutation, and see the check pass again.

Record each check, its mutation, and the failing result in the report.

- [ ] 3.1 Add these tests, through the same `stored_article_from_short_feed` helper:
  1. **CJK not covered.** The feed text is "这是一段摘要，介绍新版本的变化。". `extract` returns an unrelated Chinese sidebar, "最近文章\n花园笔记\n晨间路线". The stored text is the feed text, a blank line, then the sidebar. Mutation: the word pattern becomes `[A-Za-z0-9]+`.
  2. **Distinct words.** The feed text is "Update update update update update alpha beta". The extraction is "Weekly update digest". Only 1 of the 3 distinct words is found, so the feed text is kept first. Mutation: count the words as a list, with duplicates.
  3. **Case on the article side.** The feed text is "rust release notes for october", in lower case. The extraction contains "RUST RELEASE NOTES FOR OCTOBER" in upper case. It covers the feed text. Mutation: drop `casefold()` on the extracted text only.
  4. **Surrounding whitespace.** `extract` returns "\n  A complete report about the new instrument.  \n". The stored text is the stripped string, for an empty feed text. Mutation: drop the `strip()` of the extracted text.
  5. **The podcast text-post path.** A pending podcast item without audio is re-checked, through the existing prior-item path (`collection.py`, `prior.content_text, prior.content_origin = article_text(...)`). Its short feed text is not covered by the extraction, and its stored text becomes the feed text, a blank line, then the extracted text. Use the existing podcast test helpers. If this path cannot be reached with short feed text and no audio, stop and report. Mutation: in that path, store only the extracted text.

  Verify:
  - All new tests pass on the current code.
  - Each named mutation fails its test.
  - Every mutation is reverted: `git diff` shows only test files and docs.
  - `uv run pytest` passes in `backend/`.
- [ ] 3.2 Add a "Fix round 1" section to `docs/process/test-report-keep-feed-text-when-extraction-misses.md`, with:
  - the commands and their real results;
  - the mutation table;
  - the coverage of `collection.py`, measured with `frontend/dist` present.

  Add a fix-round entry to `docs/process/ai-usage-log.md` after the latest entry, with a faithful excerpt of the prompt you actually received, and the tool and model. Leave out the session id.

  Verify: every command passes, and the report has the actual numbers.
