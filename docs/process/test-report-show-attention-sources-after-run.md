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
