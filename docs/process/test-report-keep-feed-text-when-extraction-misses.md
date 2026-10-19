# Keep feed text when extraction misses: implementation checks

2026-10-19, branch `keep-feed-text-when-extraction-misses`. Backend commands run from `backend/`; frontend commands from `frontend/`; OpenSpec commands from the repository root.

## Red-first tests (before implementation)

`uv run pytest tests/test_collection.py tests/test_sources_api.py -q`: **4 failed, 74 passed**. The failures all compared the extracted text alone with the expected feed text, blank line, and extraction:

| Failing check | Behavior missing before 1.2 |
| --- | --- |
| `test_short_feed_release_note_survives_sidebar_extraction` | The invented release note was lost to the sidebar. |
| `test_short_feed_sixty_percent_word_boundary` (5 of 10 words) | Five matching words still replaced all feed text. |
| `test_short_feed_three_character_word_boundary` (three-character words) | The unmatched words were lost. |
| `test_short_excerpt_not_in_extracted_article_keeps_both` | The direct `article_text` confirmation path lost the excerpt. |

The following new cases **passed as guards before 1.2**: excerpt covered, 6 of 10 words, only 1–2 character words, case-insensitive words, CJK substring, and empty feed text. The updated existing short-excerpt replacement check passed too. Existing fallback tests in the focused files passed unchanged. The backend environment was created from the lockfile during this run (60 packages installed); requests were intercepted by `respx` and the existing DNS fixtures.

**Diagnosis:** The plan already identified the failing branch, so no extra instrumentation or live page was needed. Ranked hypotheses: (1) `article_text` replaces a short feed text whenever extraction is non-empty, predicting the original feed words disappear even when the saved origin is `"article"`; (2) feed parsing drops the description, predicting the stored item lacks feed text even when extraction fails; (3) fetching or extraction fails, predicting `"feed"` origin. The red assertions showed the complete sidebar with `"article"` origin and none of the feed text. This confirms (1) and rules out (2) and (3) for the reproduced case. The release-note test exercises the full `run_check` path and is the regression check.

## Implementation verification (task 1.2)

| Command | Actual result |
| --- | --- |
| `uv run pytest tests/test_collection.py tests/test_sources_api.py -q` | **78 passed** (both existing test files and all new checks). |
| `uv run pytest -q` | **421 passed** (full backend suite). |

## Full checks (task 2.1)

The initial `npm run build` could not run because this worktree had no frontend dependencies (`tsc: command not found`, exit 127). `npm ci` installed **124 locked packages** and reported **0 vulnerabilities**. The next `npm run build` passed TypeScript and Vite, transforming **41 modules** and creating `frontend/dist` before backend coverage.

| Command | Actual result |
| --- | --- |
| `npm run build` in `frontend/` after `npm ci` | Passed; TypeScript and Vite built **41 modules**. |
| `uv run pytest --cov=catchup --cov-report=term` in `backend/` | **421 passed**; `collection.py`: **109 statements, 5 missed, 95% coverage**; total: **1,938 statements, 72 missed, 96% coverage**. |
| `openspec validate keep-feed-text-when-extraction-misses --strict` at the repository root | Passed: change is valid. |

**Manual check not performed:** a real run on a local instance that includes the #47 post. The tests use invented text, mocked DNS and `respx`; they do not demonstrate live extraction or model output on that post.
