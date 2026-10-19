# Attention sources after a run: implementation checks

2026-10-18, branch `show-attention-sources-after-run`. Frontend commands ran from `frontend/`, backend commands from `backend/`, and OpenSpec commands from the repository root.

| Check | Actual result |
| --- | --- |
| `npm test -- --run src/pages/Home.test.tsx` before installing dependencies | Could not run: `vitest: command not found` (exit 127). |
| `npm ci` | Installed 124 locked frontend packages; 0 vulnerabilities reported. |
| `npm test -- --run src/pages/Home.test.tsx` after adding tests, before implementation | Expected red: **8 failed, 61 passed** in 1 file (69 tests). All eight ended-run variants in cases 1–4 failed. Both case-5 collecting-run variants passed as guards. |
| `npm test -- --run` after implementation (task 1.2) | **193 passed** in **13 files**. |
| `npm run build` after implementation (task 1.2) | Passed TypeScript and Vite build; **41 modules** transformed. |
| `npm run build` (task 2.1, first) | Passed TypeScript and Vite build; **41 modules** transformed. |
| `npm test -- --run` (task 2.1, second) | **193 passed** in **13 files**. |
| `uv run pytest` (task 2.1, third) | **411 passed** in 13.20 s; created the worktree's backend virtual environment and installed 60 packages. |
| `openspec validate show-attention-sources-after-run --strict` (task 2.1, fourth) | Valid. |
| `test -f docs/process/test-report-show-attention-sources-after-run.md && rg -q 'show-attention-sources-after-run.*implementation \(Factory Droid' docs/process/ai-usage-log.md` before writing | Expected red: exit 1, report absent. |

No existing after-run test fixture was changed. All existing after-run tests stayed green. The new tests use mocked startup requests and run accessibility checks on each rendered state.

**Manual check not performed:** a real run on a local instance. The mocked run checks do not verify a live feed or model.

## Fix round 1

2026-10-18. This round changed only Home tests, task checkboxes, and process docs. No implementation, backend, or API change was committed.

| Check | Actual result |
| --- | --- |
| `npm test -- --run src/pages/Home.test.tsx` after the 12-row restructuring | **73 passed** in 1 file. |
| Focused mutation checks from tasks 3.1 and 3.2 | Each check passed before mutation, failed under its named mutation (below), and passed after restoring `Home.tsx`. |
| `npm test -- --run src/pages/Home.test.tsx` after both 3.2 checks | **75 passed** in 1 file. |
| `npm run build` | TypeScript and Vite passed; **41 modules** transformed. |
| `npm test -- --run` | **199 passed** in **13 files**. |
| `openspec validate show-attention-sources-after-run --strict` | Valid. |
| `rg -q '^## Fix round 1' docs/process/test-report-show-attention-sources-after-run.md` before writing | Expected red: exit 1; the section was absent. The chained log-header check did not run because the first check failed. |

Test counts: before restructuring, **69 Home / 193 frontend** (8 ended-run variants); after the 12-row table, **73 Home / 197 frontend** (4 added combinations); after the two additional checks, **75 Home / 199 frontend**. The 197 figure is the prior full-suite count plus four table rows, not a separate full-suite run.

| Task | Temporary mutation in `Home.tsx` | Focused red result |
| --- | --- | --- |
| 3.1 | Pass all `run.source_checks` to the succeeded/no-new-content card. | `no_new_content` card: **2 failed** (three rows instead of two; all-fine list shown). |
| 3.1 | Pass all `run.source_checks` to the failed card. | `failed` card: **2 failed** (three rows instead of two; all-fine list shown). |
| 3.1 | Use "Sources" for the succeeded/no-new-content card label. | `no_new_content` card, needs attention: **1 failed** (missing "Needs attention" heading). |
| 3.1 | Use "Sources" for the failed card label. | `failed` card, needs attention: **1 failed** (missing "Needs attention" heading). |
| 3.1 | Render the ended compact "Needs attention" label as `h2`. | `succeeded` compact, needs attention: **1 failed** (`H2` instead of `P`). |
| 3.1 | Count only attention checks in the succeeded result line. | `succeeded` compact, needs attention: **1 failed** ("2 sources" instead of "3 sources"). |
| 3.1 | Clear check errors for `no_new_content`. | `no_new_content` compact, needs attention: **1 failed** (missing "offline"). |
| 3.2 | Use "Needs attention" for active compact runs. | Collecting run with a saved digest: **1 failed** (missing "Sources" label). |
| 3.2 | Show `check.error` for rate-limited checks. | Rate-limited compact row: **1 failed** (error repeated after "Rate limited · try later"). |

All nine mutations were reverted after their failing check, and their focused checks passed again. `git diff -- frontend/src/pages/Home.tsx` was empty before committing. No real local run was performed in this fix round.
