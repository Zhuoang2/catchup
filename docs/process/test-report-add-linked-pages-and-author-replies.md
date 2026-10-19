# Test report: add-linked-pages-and-author-replies

2026-10-19. All automated fixtures use invented feeds/pages, mocked network and DNS, and fake model responses. No live feed or model was called.

## Red-first checks

| Group | Initial failing check, before implementation | Green verification |
| --- | --- | --- |
| 1, parsing and persistence | Three parser tests failed with missing `FeedEntry` fields; four DB tests failed before migration `0004`; both collection/confirmation tests failed with `entry_links=None`. | `test_discovery.py`: 71 passed. Full backend suite after migration: 449 passed. Both storage tests passed. |
| 2, link rules and robots | `test_context_links.py` and `test_context_robots.py` failed to import the not-yet-created modules. | 8 tests passed. The first robots green run revealed an unused `respx` route in the zero-budget test; its fixture now permits that deliberately unused route. |
| 3, author replies | `test_context_comments.py` failed to import the not-yet-created module. | 5 tests passed. An initial name-match attempt selected the parent comment because it saw a nested `.fn`; restricting matches to the nearest comment fixed it. |
| 4, settings and run context | Seven config tests failed (missing fields or accepted invalid limits); gather tests failed to import the not-yet-created module. A subsequent zero-budget regression failed because a robots request exhausted the budget and marked the item `none`. | 40 config tests, 7 gather tests, 2 focused runner tests, and 480 backend tests passed. Fixed the zero-budget status to leave the item eligible for the next run. A comment fixture initially had invalid nested `<li>` markup and was corrected before green. |
| 5, summaries and used flags | Two contextual-summary tests failed on unsupported context arguments; used-ref recording failed (`L1` was still false). | 22 focused summary/runner tests passed. |
| 6, snapshot and UI | Both history tests failed without `also_read`; two frontend citation tests failed before rendering. The collecting progress test failed before the new label. | 15 history tests; 32 focused citation/layout tests; 205 frontend tests and build passed. The first full frontend check found a test asserting `aria-valuenow` on a native `<progress>` element; the fixture assertion was corrected to its `value`/`max` attributes. The CSS structure guard was extended for `.item-body`. |
| 7, docs | The README defaults check failed before documentation. | The README check passed. |

## Final checks

The frontend was built **before** running backend coverage, so static-asset branches were measured with `frontend/dist` present.

| Command | Result |
| --- | --- |
| `cd frontend && npm run build` | Passed, TypeScript and Vite build. |
| `cd backend && uv run pytest --cov=catchup --cov-report=term` | **485 passed**, **96%** statement coverage (2,218 statements, 93 missed, 2,125 covered). New modules: comments 80%, gather 88%, links 93%, robots 100%; feeds 97%, runner 99%, summarize 95%. |
| `cd frontend && npm test -- --run` | **205 passed**, 13 test files. |
| `openspec validate add-linked-pages-and-author-replies --strict` | Passed: change is valid. |
| `docker build -t catchup:item-context-local .` | Passed. Local image only; not pushed. |

## Manual checks not performed

- A real run on the Simon Willison and Terry Tao feeds.
- A real-model token comparison with and without context.
- A live browser visual check of the reading layout and a runtime Docker smoke check. The Docker image was built, not started.
