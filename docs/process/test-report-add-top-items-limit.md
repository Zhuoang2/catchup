# Test report: add-top-items-limit (#9)

## Implementation by Factory Droid

Date: 2026-11-27. Tool: Factory Droid. Model identifier not exposed in this run.
Starting commit: `4ba109d`. Branch: `add-top-items-limit`.

The user approved the plan and U1–U7 recommendations at plan approval.
This run implemented that plan with `openspec-apply-change` and `tdd`, in
task-group order. No additional user approval is claimed for implementation
or test choices made by Droid.

| Group | Commit | Scope |
| --- | --- | --- |
| 1 | `96b58bc` | Summary prompts, strict rating parsing, cached ratings. |
| 2 | `728109a` | Item storage, digest snapshots and answers, migration 0013. |
| 3 | `31f8f99` | Preferences API, Settings choice, README, smoke expectations. |
| 4 | `01c05bc` | Ranking, limited article, Latest and saved-digest integration. |
| 5 | This report's commit | Final checks and process evidence. |

Proposal, design, spec deltas, decision log, and requirements-changes log
were not edited. Existing tests changed only where the tasks permit.
Collection, grouping, delivery, progress, Bookmarks implementation, History
list, extension implementation, dependencies, manifests, and lockfiles
were not changed.

### Environment and isolation

- Backend: Python 3.12.13, pytest 9.1.1; every backend command used
  `uv run --offline` in `backend/`. uv created the worktree's environment
  using the cached locked packages (62 packages), with no new dependency.
- Each frontend/extension shell used
  `export PATH="$HOME/.nvm/versions/node/v22.17.1/bin:$PATH"`.
  Both reported `v22.17.1`.
- `npm ci --offline --no-audit --no-fund` succeeded in `frontend/`
  (124 packages) and `extension/`
  (120 packages). Both emitted the existing
  `whatwg-encoding@3.1.1` deprecation warning.
- Tests used local test databases, existing offline collection fixtures,
  fake model clients, and mocked browser fetches. No real provider,
  network request, or real credential was used. `RatingModel` answers by
  item title, not by the order of concurrent summary calls.
- The rating lifecycle was traced before changing persistence: a new
  summary stores its rating; failed grouping leaves it pending; the next
  run passes that rating with the cached summary into its snapshot.
  Summary invalidation can leave a stale item rating, but only a reused
  summary reads it; a replacement summary overwrites it, and unavailable
  snapshots use the run's unrated result. Creator updates are unrated.

## Red/green evidence

Commands below identify the suites run in their indicated directory;
incidental traceback, quiet, and reporter options are omitted. Expected
red and mutation runs deliberately exited 1; final ordinary checks all
exited 0. Final command output is recorded separately below.

| Task / directory | Command | Actual result |
| --- | --- | --- |
| 1.1, backend | `uv run --offline pytest tests/test_digest_stages.py` | **18 failed, 73 passed**. The two changed prompts and new prompt test lacked the rating instruction/example; the other new cases raised missing-field `AttributeError` or constructor `TypeError`. |
| 1.2, backend | `uv run --offline pytest` | **1438 passed, 2 warnings in 38.72s**. |
| 1.2, backend, after restoring mutations | `uv run --offline pytest tests/test_digest_stages.py` | **91 passed**. |
| 2.1, backend | `uv run --offline pytest tests/test_db.py tests/test_digest_runner.py tests/test_digest_history.py` | **13 failed, 114 passed**. Missing revision/columns, missing model attributes, missing answer field; constructing the new rated history snapshot failed first with `TypeError` because its model column did not exist yet. H1 later verified both history tests against omission from answers. |
| 2.2, backend | `uv run --offline pytest` | **1445 passed, 2 warnings in 42.34s**. |
| 2.2, backend, after restoring mutations | `uv run --offline pytest tests/test_db.py tests/test_digest_runner.py tests/test_digest_history.py` | **127 passed**. |
| 3.1, backend | `uv run --offline pytest tests/test_settings_api.py tests/test_readme_top_items.py` | **14 failed, 42 passed**. The three changed response tests lacked `top_items`, save/read lacked the field, invalid values were accepted, README sentence absent. |
| 3.1, frontend | `npm test -- --run src/pages/Settings.test.tsx` | **3 failed, 83 passed (86)**, exactly the three new tests: Items to show combobox absent. |
| 3.2, backend | `uv run --offline pytest` | **1456 passed, 2 warnings in 42.56s**. |
| 3.2, frontend | `npm test -- --run` and `npm run build` | **386 passed in 15 files**; TypeScript/Vite succeeded, **41 modules transformed**, built in **182ms**. |
| 3.2, root | `bash -n scripts/docker-smoke.sh` | Exit 0, no output. Syntax only, script never executed. |
| 3.2, backend, after restoring mutations | `uv run --offline pytest tests/test_settings_api.py tests/test_readme_top_items.py` | **56 passed**. |
| 3.2, frontend, after restoring mutations | `npm test -- --run src/pages/Settings.test.tsx` | **86 passed in 1 file**. |
| 4.1, frontend | `DEBUG_PRINT_LIMIT=0 npm test -- --run src/components/topItems.test.ts src/components/DigestArticle.test.tsx src/pages/Home.test.tsx src/pages/DigestView.test.tsx src/pages/Bookmarks.test.tsx` | **1 failed suite** (missing `topItems.ts` import), **6 failed, 162 passed**. The six feature tests failed on missing filtering/button; the three specified full-view guards and all other existing cases passed. |
| 4.2, frontend | `npm test -- --run` and `npm run build` | **399 passed in 16 files**; TypeScript/Vite succeeded, **42 modules transformed**, built in **84ms**. |
| 4.2, frontend, after restoring mutations | `npm test -- --run` and `npm run build` | **399 passed in 16 files**; **42 modules transformed**, built in **79ms**. |

While drafting group 3 tests, an initial replacement briefly added
`top_items` to image PUT fixtures rather than just the expected response.
Droid corrected the test edit before implementing the API and reran red:
all 14 intended backend failures were then observed. The committed test
requests remain unchanged.

## Test inventory and scenario mapping

There are **34 new backend cases** (1422 → 1456) and **16 new frontend
cases** (383 → 399). Counts include parametrized cases. All extension tests
are pre-existing. A dash below means no named mutation targets that test;
it is not a claim of mutation coverage.

### Backend

Names in this table are literal pytest function names.

| File / test | New or changed | Spec scenario / contract | Named mutations killed |
| --- | --- | --- | --- |
| `test_digest_stages.py::test_no_context_system_prompt_matches_original_main_bytes` | Changed literal expected prompt only | Rated item, fixed rating scale | — |
| `test_digest_stages.py::test_no_image_long_transcript_prompt_matches_original_main_bytes` | Changed literal expected prompt only | Rated item, transcript rating scale | S5 |
| `test_digest_stages.py::test_summary_prompts_ask_for_an_importance_rating` | New | Rated item, ordinary/context/image/transcript prompts; parts not rated | S5, S6 |
| `test_digest_stages.py::test_summary_rating_is_kept_when_valid` [1, 3, 5] | New | Rated item | — |
| `test_digest_stages.py::test_invalid_rating_leaves_the_item_unrated` [zero, six, seven, string, fraction, float, true, null, missing] | New | Invalid rating, summary kept and one call | S1 [six, seven], S2 [true], S4 [null, missing] |
| `test_digest_stages.py::test_cached_summary_keeps_its_rating` | New | Rating kept with a reused summary; Summary written before ratings | S3 |
| `test_digest_stages.py::test_split_text_rating_comes_from_the_combining_call` | New | Long-text rating from combining call, no added rating call | — |
| `test_digest_stages.py::test_unavailable_summary_is_unrated` | New | Summary unavailable | — |
| `test_db.py::test_migrations_live_inside_package` | Added 0013 file assertion | Migration deployment | — |
| `test_db.py::test_existing_database_at_old_revision_is_unchanged` | Changed head revision assertion | Existing installations upgrade | — |
| `test_db.py::test_image_migration_from_0004_preserves_rows_and_downgrades` | Changed head revision assertion | Existing installations upgrade | — |
| `test_db.py::test_capture_migration_preserves_rows_and_removes_capture_sources_on_downgrade` | Changed head revision assertion | Existing installations upgrade | — |
| `test_db.py::test_migrate_copy_of_0006_database` | Changed head revision assertion | Existing installations upgrade | — |
| `test_db.py::test_item_marks_migration_creates_empty_table_and_downgrades` | Changed upgrade target to 0012 only | Keep historical migration test at its own schema | — |
| `test_db.py::test_item_importance_migration_adds_columns_and_downgrades` | New | Existing items unrated; All default; non-null preference; rollback preserves prior rows | M1, M2, M3 |
| `test_digest_runner.py::test_digest_records_each_items_rating` | New | Rated item; Invalid rating | R1, R2 |
| `test_digest_runner.py::test_rating_survives_a_failed_grouping` | New | Rating kept with a reused summary | R1, R2 |
| `test_digest_runner.py::test_unavailable_summary_is_saved_unrated` | New | Summary unavailable, including a stale stored rating | R3 |
| `test_digest_runner.py::test_summary_written_before_ratings_is_reused_unrated` | New | Summary written before ratings, no extra call | — |
| `test_digest_runner.py::test_creator_updates_are_unrated` | New | Creator updates never rated | R4 |
| `test_digest_history.py::test_digest_detail_uses_snapshot_positions_and_survives_source_deletion` | Added `importance: None` to pinned answer | Digest saved before ratings; Source deleted after saving | H1 |
| `test_digest_history.py::test_digest_answers_give_each_items_saved_rating` | New | Reopen a rated digest; Digest saved before ratings; latest and detail after source deletion | H1 |
| `test_settings_api.py::test_preference_save_and_read` | Added `top_items: 0` to expected answers only | Default choice | P4 |
| `test_settings_api.py::test_partial_preference_updates_keep_other_values` | Added `top_items: 0` to expected answers only | Default choice, preserve other preferences | — |
| `test_settings_api.py::test_image_preference_can_be_saved_without_changing_others` | Added `top_items: 0` to expected answer only | Default choice, preserve other preferences | — |
| `test_settings_api.py::test_top_items_save_and_read` | New, checks 5, 10, 20, 30, 0 sequentially | Save a number; All items | P1 |
| `test_settings_api.py::test_invalid_top_items` [seven, negative, one, hundred, false, true, string, float, fraction] | New | Value refused, saved choice retained | P2 [seven, negative, one, hundred], P3 [false, true, string, float] |
| `test_readme_top_items.py::test_readme_describes_top_items` | New | README intro sentence, design D10 | Doc |

Test paths in this table are under `backend/tests/`. The smoke script's
two pinned preferences answers also gain `top_items: 0`; these were edited
and syntax-checked, not executed.

### Frontend

| File / test | New or changed | Spec scenario / contract | Named mutations killed |
| --- | --- | --- | --- |
| `Settings.test.tsx`: `shows the items-to-show choice with its note` | New | Default choice, option order, associated note, field order | F3 |
| `Settings.test.tsx`: `saves Items to show with the other digest preferences` | New | Save a number; Settings saved result | F1 |
| `Settings.test.tsx`: `loads a saved number and keeps it when saving without changing it` | New | Save a number, saved choice loaded | F2 |
| `topItems.test.ts`: `ranks by rating, an unrated summary as 3, and an unavailable one last` | New | Limited digest, exact selected IDs | T1 |
| `topItems.test.ts`: `keeps reading order among equal ranks` | New | Limited digest, stable ties | T3 |
| `topItems.test.ts`: `ranks an unavailable summary below a rating of 1` | New | Limited digest, unavailable last | T2 |
| `topItems.test.ts`: `shows everything without a limit, for a short digest, or without ratings` | New | Short digest (including equality); Digest saved before ratings; All items | T4, T5 |
| `DigestArticle.test.tsx`: `shows only the most important items in their topics` | New | Limited digest, title order, index/counts, full Creator updates and headline count, button description, axe accessibility | A1, A2, A4, A6 |
| `DigestArticle.test.tsx`: `shows every item and limits again` | New | Show all, same button/focus, status announcements both ways | A5 |
| `DigestArticle.test.tsx`: `starts limited again for the next digest` | New | New digest starts limited | A3 |
| `DigestArticle.test.tsx`: `shows short and unrated digests in full` | New; passed before implementation | Short digest; Digest saved before ratings | — |
| `Home.test.tsx`: `limits the latest digest to the saved number of items` | New | Limited digest on main screen | V1 |
| `Home.test.tsx`: `moves focus to run-bar Generate when a new digest replaces the shown one while Show all has focus` | New | Show all has focus when a new digest arrives | V2 |
| `DigestView.test.tsx`: `limits a saved digest to the saved number of items` | New | Reopen a saved digest, limited view | V3 |
| `DigestView.test.tsx`: `shows every item when the preferences cannot be read` | New; passed before implementation | Choice cannot be read | — |
| `Bookmarks.test.tsx`: `lists every bookmark whatever Items to show says` | New; passed before implementation | Bookmarks lists all eight | — |

`Settings.test.tsx`'s `mockLinkedPages` helper gains the default field;
`Home.test.tsx`'s `mockPage` helper gains optional preferences responses.
No existing frontend test body changed.
The shared new `src/test/limitedDigest.ts` fixture and `unrated` helper
encode the specified Alpha/Beta/Gamma example.

Three **existing, unchanged** tests in `DigestView.test.tsx` kill A7:
`renders creator updates after topics with saved wait labels`,
`marks Chinese generated text and focuses index targets`, and
`omits all digest language marks when the saved preference is original`.
They guard preserved empty saved topics in full views, including the
modified Reopen a saved digest requirement.

## Named mutation results

Each mutation was applied **alone**, followed by exactly its named tests
from `tasks.md` (pytest node IDs, or Vitest file plus `-t` exact test name;
A7 used the three names as an alternation). Backend runs used
`uv run --offline pytest -q <named tests> --tb=short`; frontend runs used
`DEBUG_PRINT_LIMIT=0 npm test -- --run <file> -t '<name>'` with Node 22.17.1.
Each was then reversed by explicit edits, not a Git restore command.
The file's `git diff` before and after was compared byte-for-byte
and matched for every experiment. For newly created files not yet staged,
the comparison used `git diff --no-index -- /dev/null <file>` so an
untracked file could not hide an unrestored edit. Each group's tests
passed again after restoration.

| Mutation | Change | Named-test result |
| --- | --- | --- |
| S1 | Remove rating upper bound | **Killed: 2 failed**, six and seven. |
| S2 | Accept `isinstance(value, int)` | **Killed: 1 failed**, true. |
| S3 | Omit cached rating | **Killed: 1 failed**, cached rating missing. |
| S4 | Raise for null/missing rating | **Killed: 2 failed**, summary lost for null and missing. |
| S5 | Omit transcript importance rule | **Killed: 2 failed**, prompt rule and exact transcript prompt. |
| S6 | Add importance rule to part notes | **Killed: 1 failed**, parts must not ask for rating. |
| M1 | Omit digest item migration column | **Killed: 1 failed**, full upgraded row mismatch. |
| M2 | Migration default becomes 5 | **Killed: 1 failed**, settings row default mismatch. |
| M3 | Downgrade keeps item importance | **Killed: 1 failed**, column still present. |
| R1 | Do not persist item rating | **Killed: 2 failed**, failed-run rating and stored item ratings. |
| R2 | Omit snapshot rating | **Killed: 2 failed**, new and cached snapshot ratings. |
| R3 | Snapshot uses unguarded `item.importance` | **Killed: 1 failed**, unavailable snapshot incorrectly rated 5. |
| R4 | Rate Creator updates from item | **Killed: 1 failed**, Creator update incorrectly rated 4. |
| H1 | Omit answer importance | **Killed: 2 failed**, rated answer KeyError and old pinned answer mismatch. |
| P1 | Remove 30 from allowed values | **Killed: 1 failed**, save 30 returns 422. |
| P2 | Remove membership check | **Killed: 4 failed**, seven, negative, one, hundred accepted. |
| P3 | Use coercive `int` field | **Killed: 4 failed**, false/string/float accepted; true has wrong error code. |
| P4 | Default answer 10 without settings | **Killed: 1 failed**, expected All/0. |
| F1 | Omit choice from save body | **Killed: 1 failed**, PUT body missing choice. |
| F2 | Ignore loaded choice | **Killed: 1 failed**, select 0 instead of 20. |
| F3 | Omit select description link | **Killed: 1 failed**, accessible description absent. |
| Doc | Remove README sentence | **Killed: 1 failed**, intro assertion. |
| T1 | Unrated summary ranks 0 | **Killed: 1 failed**, IDs include 3 instead of 6. |
| T2 | Unavailable summary ranks 3 | **Killed: 1 failed**, selects unavailable ID 1. |
| T3 | Reverse tie reading order | **Killed: 1 failed**, [3, 2] instead of [1, 2]. |
| T4 | Remove at-least-one-rating check | **Killed: 1 failed**, unrated digest limited. |
| T5 | Limit at exact equality | **Killed: 1 failed**, eight-item limit returns a set, not null. |
| A1 | Keep topics with no shown item | **Killed: 1 failed**, Beta heading remains. |
| A2 | Index counts all topic items | **Killed: 1 failed**, Gamma 4 instead of 3. |
| A3 | Replace digest-keyed state with boolean | **Killed: 1 failed**, next digest retains all eight. |
| A4 | Hide Creator updates when limited | **Killed: 1 failed**, Creator index entry missing. |
| A5 | Omit toggle announcement | **Killed: 1 failed**, status text absent. |
| A6 | Headline counts shown topic items | **Killed: 1 failed**, headline 5 instead of 10. |
| A7 | Drop empty topics also in full views | **Killed: 3 failed**, all three named existing DigestView tests. |
| V1 | Home omits topItems prop | **Killed: 1 failed**, Show all absent on Latest. |
| V2 | Home focus rule omits digest-limit | **Killed: 1 failed**, focus stays on Show all instead of Generate. |
| V3 | DigestView omits topItems prop | **Killed: 1 failed**, Show all absent in saved digest. |

**37/37 named non-equivalent mutations killed.** No named mutation
survived unexpectedly. Two specified equivalent experiments were also
run separately on the three runner tests for recording, retry, and
unavailable results:

- **R3 guarded source swap**, `item.importance` with the original
  summary/unavailable condition: **3 passed in 1.84s**, equivalent.
  For a usable result, `record` has already stored that same rating.
- **R3 guard removal only**, unguarded `summary.importance`:
  **3 passed in 1.86s**, equivalent. Unavailable results already carry
  `None`; successful summary results contain nonempty text.

Both equivalent mutations were restored exactly; no extra test was added
to distinguish unreachable states.

## Final checks, task 5.1

These are the actual final command output lines, not predicted counts.
All seven commands exited **0**.

### Backend, `uv run --offline pytest`

```text
collected 1456 items
====================== 1456 passed, 2 warnings in 45.45s =======================
```

The two warnings are from existing Anthropic malformed-usage tests
(`PydanticSerializationUnexpectedValue` for a deliberately non-integer
`input_tokens`), not new failures.

### Frontend, `npm test -- --run`

```text
 Test Files  16 passed (16)
      Tests  399 passed (399)
   Duration  7.41s (transform 1.95s, setup 3.46s, import 5.67s, tests 21.19s, environment 9.00s)
```

### Frontend, `npm run build`

```text
> tsc --noEmit && vite build
✓ 42 modules transformed.
✓ built in 196ms
```

### Extension, `npm test -- --run`

```text
 Test Files  7 passed (7)
      Tests  169 passed (169)
   Duration  3.74s (transform 322ms, setup 735ms, import 1.46s, tests 4.88s, environment 4.49s)
```

### Extension, `npm run build`

```text
> tsc --noEmit && vite build && node scripts/check-build.mjs
✓ 10 modules transformed.
✓ built in 171ms
```

### Root, `DO_NOT_TRACK=1 openspec validate add-top-items-limit --strict`

```text
Change 'add-top-items-limit' is valid
```

### Root, `git diff --check`

No output, exit 0. Staged diffs were also checked before each group commit.

## Not performed in this run

- Docker build and `scripts/docker-smoke.sh`: **not performed**, as
  explicitly instructed. Claude Code runs Docker smoke at review.
  Only the smoke script's syntax was checked here.
- Design Testing live check: **not performed**, reserved for Claude Code
  review on fresh volumes and a scratch port other than 8800. Review
  should generate at least eight items with a local per-item-rating stub,
  check limit 5, chosen IDs/order, index, line, Show all/back, announcement,
  History reopening, All items, and 375px/1440px layouts.
- The user's own Rollout check, trying the choice on two or three real
  digests and judging the selected items: **the user's check after merge**,
  not performed or claimed by Droid.
- No Docker command, port 8800 operation, push, merge, tag, archive, or PR
  was performed. Claude Code's independent code/spec review remains pending.
