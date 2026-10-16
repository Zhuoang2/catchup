# Improve single-item topics: implementation checks

2026-10-16, branch `improve-single-item-topics`. Commands ran from the repository root unless a directory is specified.

| Check | Actual result |
| --- | --- |
| `cd backend && uv run pytest` | **362 passed**. Coverage is not reported by this command. |
| `cd backend && uv run pytest --cov=catchup --cov-report=term -q` | **362 passed**; **96%** statement coverage (1,879 statements, 77 missed). |
| `cd frontend && npm test -- --run` | **164 passed** in **13 files**; **58 axe scans**, counted with a temporary test-helper probe writing only to a temp directory, then removed. No violations reported. The jsdom color-contrast rule is disabled; the token tests check contrast numerically. |
| `cd frontend && npm run build` | Passed TypeScript and Vite production build (**41 modules**). |
| `python3 frontend/scripts/check-style-coverage.py` | Passed: **11** documented prototype-only selectors, **0** uncovered prototype selectors. |
| `python3 -m unittest discover -s frontend/scripts -p test_check_style_coverage.py` | **3 passed**. |
| `openspec validate improve-single-item-topics --strict` | Valid. |
| `docker build -t catchup-improve-single-item-topics .` | Passed locally with Docker **29.8.0**, including TypeScript and Vite compilation. No image was pushed. |

The four-item DOM test first failed on `item item-long` before the class change, then passed. Both CSS assertions failed before the layout change (the item did not span the grid and the narrow item reset was absent), then passed. The style audit first failed with two uncovered archived selectors (`.item-long`, `.item-short`); its unit test failed with the same command error before the exceptions were added. Both passed afterwards. No real network calls, model keys, or fixed sleeps were used in tests.

**Manual checks not performed:** live measurements at **1440, 1000, 901, 900, and 420 px** on the real Chinese digests and an English digest. DOM/CSS assertions, axe scans, the build, and the Docker build do not verify painted widths, line lengths, title placement, or overflow in a browser. Those checks remain for review.
