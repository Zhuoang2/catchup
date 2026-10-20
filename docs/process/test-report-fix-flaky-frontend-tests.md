# Test report: fix-flaky-frontend-tests (#52)

2026-10-20. Tests only; temporary runtime mutations were reverted before each commit. Existing fetch mocks and fake-timer setup were retained.

## Causes and mutation checks

| Task | Cause and temporary mutation | Red, before changing the test | Green, with mutation; after revert |
| --- | --- | --- | --- |
| 1.1 Titles | `useDocumentTitle` writes in a passive effect, so a DOM wait does not guarantee the title is updated. Temporarily wrapped its assignment in `setTimeout(() => { … }, 50)`. | The unmodified two-file suite failed at `DigestView.test.tsx:185` and seven Home test cases (`:150`, both `:377` cases, both `:631` cases, `:920`, and `:1054`), plus an unrelated `DigestView.test.tsx:139` assertion, 9 failures total. `Home.test.tsx:130` passed in the full run because the preceding test left the same title; isolated with `-t 'shows the latest article and one compact action above its headline without a rail'`, it failed, receiving an empty title instead of `Latest · No. 4 · CatchUp`. `Home.test.tsx:406` passed even when isolated with the original synchronous assertion under the mutation: the title stays at the prior edition and the test's fake-timer advance plus async wait for the detail error allow the 50 ms title timer to finish. | All selected title cases passed under the mutation (10 test cases). After the revert, `npm test -- --run src/pages/DigestView.test.tsx src/pages/Home.test.tsx`: **101 passed**. |
| 1.2 Delete focus | The focus transfer runs in a passive effect after deleting a source, so a list refresh does not guarantee focus moved yet. Temporarily wrapped the focus call in `setTimeout(() => { … }, 50)` inside the `focusAfterDelete` effect. | Both original assertions at `Sources.test.tsx:230,268` failed: `document.activeElement` was `<body>` instead of the empty-state heading (2 failed, 30 skipped). | Both selected tests passed with the mutation (2 passed, 30 skipped). After the revert, `npm test -- --run src/pages/Sources.test.tsx`: **32 passed**. |
| 2.1 Icon regeneration | The Python icon-generation subprocess can exceed Vitest's default 5-second test timeout when six complete suites contend for the machine. No runtime mutation; the red check was six parallel full-suite runs. | Before adding the explicit timeout, **0 passed, 6 failed**, each at `install.test.ts`'s icon-regeneration test with `Test timed out in 5000ms.` | After adding `30_000` as the third argument of that `it`, the same six-parallel full-suite check **6 passed, 0 failed**. |

The `DigestView.test.tsx:139` failure in the full mutated run came from a previous test's delayed title assignment. It is not a change of title during that test; it passed after reverting the artificial delay. The two assertions in that test were left alone as required. Of the eight named title assertion sites, six failed in the full mutated run, a seventh (`Home.test.tsx:130`) failed when isolated, and `Home.test.tsx:406` did not fail even when isolated. The latter was still wrapped in `waitFor` as the task requires. Its original synchronous assertion passed with the mutation; the changed test passed after reversion. This check cannot prove that particular wrapper needed changing.

## Assertions left alone

- `Sources.test.tsx:220,224,226`: their preceding `fireEvent` is wrapped in `act`, which flushes the corresponding effects.
- `ui.test.tsx:60`, `DigestView.test.tsx:314`, and `App.test.tsx:63`: a click handler sets focus directly, not an effect. At review, the reason for `ui.test.tsx:60` was corrected from "fireEvent flushes effects" to "focus is set in the `useJump` click handler".
- `App.test.tsx:21`: reads a title right after `render`, which runs inside `act`.
- `DigestView.test.tsx:137,139`: the expected title stays `Digest · CatchUp` while the unavailable digest loads and fails.
- `Home.test.tsx:382`: checks that focus *did not move* after a user focused a link. Waiting could not make a no-movement check fail.

## Stress and final checks

Three additional rounds of six parallel full `npx vitest run` commands from `frontend/`:

| Round | Passed | Failed |
| --- | ---: | ---: |
| 1 | 6 | 0 |
| 2 | 6 | 0 |
| 3 | 6 | 0 |
| **Total** | **18** | **0** |

| Command | Result |
| --- | --- |
| `cd frontend && npm run build` | Passed, TypeScript and Vite (41 modules transformed). |
| `cd frontend && npm test -- --run` | **219 passed** in 13 files. |
| `cd backend && uv run pytest` | **559 passed**. |
| `openspec validate fix-flaky-frontend-tests --strict` | Passed; zero spec deltas accepted with `skip_specs: true`. |

No coverage instrumentation was run in this test-only change. The previous measured backend statement coverage was 96% (see `coverage-summary.md`).

## Fix round 1 (2026-10-20)

| Task | Red check | Green check |
| --- | --- | --- |
| 4.1 Title isolation | New `setup.test.ts`: the second of two ordered tests failed, receiving `Left by an earlier test` instead of `''` (1 failed, 1 passed). | Reset `document.title` in the shared `beforeEach`. The two focused tests passed, then `npm test -- --run`: **221 passed** in 14 files. No existing test relied on an earlier test's title. |
| 4.2 Poll registration | In "keeps a startup latest-digest error visible through successful progress polls", a temporary assertion immediately after `findByRole('alert')` failed: the `window.setInterval` spy had seen only Testing Library's 50 ms interval, not Home's 1000 ms poll interval (1 failed, 79 skipped). | The same temporary assertion passed after waiting for a 1000 ms `setInterval` call (1 passed, 79 skipped). Removed the assertion; `npm test -- --run src/pages/Home.test.tsx`: **80 passed**. The spy works with the existing fake timers. |
| 4.3 Unchanged title | No named red step: this removes an unneeded wait, rather than fixing a failing assertion. | Restored the synchronous title assertion in "keeps the previous article and links to the new edition when detail loading fails": **1 passed**, 79 skipped. |

The poll-registration helper runs before the first fake-clock advance in each of these tests (including each parameterized case):

1. "swaps the existing article after a run, retaining status and focus";
2. "swaps the first article after a run, retaining status and focus";
3. "keeps the previous article and links to the new edition when detail loading fails";
4. "drops the startup latest-digest error when a run delivers a digest";
5. "retains page-details failure separately when a failed latest load is replaced";
6. "keeps a fetched edition when the next run ends no_new_content";
7. "keeps a fetched edition when the next run ends succeeded";
8. "hides an older digest fetch error after an overlapping run shows a newer edition";
9. "hides an older fetch error when the newer digest resolves in the same tick";
10. "keeps the higher digest error when an older pending fetch also fails";
11. "polls from summarizing to success with a persistent status region using fake timers";
12. "announces a polled run failure only through the persistent status region";
13. "announces 16 saved items (14 summarized, 2 in Creator updates)";
14. "announces 3 saved items (3 summarized, 0 in Creator updates)";
15. "announces 2 saved items (0 summarized, 2 in Creator updates)";
16. "keeps a startup latest-digest error visible through successful progress polls";
17. "starts one run and shows its saved article without requesting the list";
18. "uses action-specific alerts when starting or checking a run fails".

Three rounds of six parallel full `npx vitest run` commands from `frontend/`:

| Round | Passed | Failed |
| --- | ---: | ---: |
| 1 | 6 | 0 |
| 2 | 6 | 0 |
| 3 | 6 | 0 |
| **Total** | **18** | **0** |

Final commands: `cd frontend && npm run build` passed (41 modules transformed); `cd frontend && npm test -- --run` passed **221 tests in 14 files**; `openspec validate fix-flaky-frontend-tests --strict` passed. Backend tests and coverage were not rerun in this test-only fix round.
