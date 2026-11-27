# Test report: add-item-bookmarks-and-feedback (#8)

## Implementation by Factory Droid, 2026-11-25 to 2026-11-26

Implemented the five task groups in the approved change, including the two
task amendments Claude Code committed during the run, described below. This report records implementation
checks, not Claude Code's independent review, Docker smoke, or live-browser checks.

### Final verification (task 5.1)

All commands below exited 0. Backend commands ran in `backend/`; frontend and
extension commands ran in their respective directories. Node commands used
`export PATH="$HOME/.nvm/versions/node/v22.17.1/bin:$PATH"`; both final Node
version checks printed `v22.17.1`. No packages or lockfiles were changed.

| Directory | Command | Actual result |
| --- | --- | --- |
| `backend/` | `uv run --offline pytest` | **1392 passed, 2 warnings in 36.95s**, Python 3.12.13, pytest 9.1.1 |
| `frontend/` | `npm test -- --run` | **376 passed in 15 files**, 6.72s |
| `frontend/` | `npm run build` | `tsc --noEmit` and Vite passed; 41 modules, 97ms |
| `extension/` | `npm ci --offline --no-audit --no-fund` | 120 locked packages installed from cache |
| `extension/` | `npm test -- --run` | **169 passed in 7 files**, 2.66s |
| `extension/` | `npm run build` | TypeScript, Vite, and `scripts/check-build.mjs` passed; 10 modules, 109ms |
| Repository root | `DO_NOT_TRACK=1 openspec validate add-item-bookmarks-and-feedback --strict` | `Change 'add-item-bookmarks-and-feedback' is valid` |
| Repository root | `git diff --check` | Passed, no output |

Frontend `npm ci --offline --no-audit --no-fund` had already succeeded before
frontend checks, installing 124 locked packages. The npm installation warning was
the existing `whatwg-encoding` deprecation. The two backend warnings came from
`test_anthropic_client.py::test_usage_of_the_wrong_shape_is_not_counted` cases
using deliberately malformed `input_tokens='seven'`; Pydantic warned during
serialization. Neither warning represents a failed check.

Final frontend build output: HTML 0.82 kB, CSS 21.41 kB (gzip 5.41 kB), JavaScript
328.38 kB (gzip 100.23 kB). The extension source is unchanged; its checks match CI.

### Test-first evidence

The existing pytest/Vitest suites and build commands were retained. New tests
were written at the seams named in tasks.md:

- `backend/tests/test_item_marks.py`: digest item identity and marks; persistence,
  idempotence, validation and security; one bulk marks query; feedback privacy
  through the existing runner seam; Bookmarks order, contents and image filtering.
- `backend/tests/test_db.py`: migration upgrade, exact columns and cascading
  foreign key, unchanged digest snapshots, and downgrade.
- `backend/tests/test_x_settings_api.py`: deleting X data removes only X marks.
- `backend/tests/test_readme_marks.py`: Bookmarks discoverability and privacy text.
- `frontend/src/components/DigestArticle.test.tsx`: accessible toggles, saved marks,
  busy and error behavior, announcements, keyed state, feedback validation and focus.
- `frontend/src/pages/Bookmarks.test.tsx`: accessible list, digest links and language,
  retained unbookmarked entry, empty/error states, and image preference.
- New History, App navigation, and Home focus tests. Only the existing-test edits
  explicitly permitted by tasks.md were made.

| Group | Before implementation | Verified green |
| --- | --- | --- |
| 1, Bookmark and Like | Missing model/module collection failure; migration/history checks failed; frontend selection had 10 failed, 52 passed because controls/layout were absent | Backend **1378 passed**, frontend **360 passed**, build passed |
| 2, feedback | Backend feedback selection **8 failed, 12 deselected** because the endpoint was absent; frontend **6 failed, 21 skipped** because no panel opened | Backend **1386 passed**, frontend **366 passed**, build passed after authorized panel-id amendment |
| 3, Bookmarks | API selection **4 failed, 20 deselected**, with 404s; frontend could not import Bookmarks, and navigation/History checks had **3 failed, 11 passed**; the title-table import also failed collection | Backend **1390 passed**, frontend **375 passed in 15 files**, build passed after authorized heading amendment |
| 4, deletion/focus/README | New README and Home focus tests each failed before D10/D9. The X-deletion test passed immediately, as the plan explicitly expected; M3 proved its sensitivity | Backend **1392 passed**, frontend **376 passed** |

The group 4 backend red selection was **1 failed, 1 passed**. The Home red
selection was **1 failed, 101 skipped**: focus landed on the body rather than
Generate after digest No. 8 replaced No. 7. Group 4's green backend run took
36.69s; the final task 5 run above repeated the complete suites after mutations
were restored. A Bookmarks-only check after making the new fixture text English
also passed all **5 tests**.

### Named mutations (tasks 1.3, 1.6, 2.3, 2.6, 3.3, 3.6, 4.3)

**All 35 mutations were run individually and detected. No named mutation
survived.** Every mutation was restored by editing the file back. Full restored
file content and the saved pre-mutation `git diff` were compared after each
mutation; both matched exactly. Multi-file M3 was one mutation, restored in both
the model and migration. No mutation code remains.

Test file abbreviations in this table:

- `db`: `backend/tests/test_db.py`
- `marks`: `backend/tests/test_item_marks.py`
- `x`: `backend/tests/test_x_settings_api.py`
- `readme`: `backend/tests/test_readme_marks.py`
- `article`: `frontend/src/components/DigestArticle.test.tsx`
- `view`: `frontend/src/pages/DigestView.test.tsx`
- `tokens`: `frontend/src/styles/tokens.test.ts`
- `bookmarks`: `frontend/src/pages/Bookmarks.test.tsx`
- `app`: `frontend/src/App.test.tsx`
- `home`: `frontend/src/pages/Home.test.tsx`

Each row records the failure count from its targeted mutation run, not a full
suite run.

| ID | Temporary fault | Tests that failed | Count |
| --- | --- | --- | --- |
| M1 | Migration foreign key without CASCADE | db: `test_item_marks_migration_creates_empty_table_and_downgrades` | 1 |
| M2 | Migration downgrade does nothing | db: `test_item_marks_migration_creates_empty_table_and_downgrades` | 1 |
| M3 | Model and migration foreign keys without CASCADE | x: `test_delete_all_x_data_removes_marks_on_x_items_only`, SQLite/SQLAlchemy `IntegrityError: FOREIGN KEY constraint failed` | 1 |
| A1 | Repeated bookmark replaces its timestamp | marks: `test_repeated_bookmark_keeps_its_first_time` | 1 |
| A2 | Remove Creator updates guard | marks: `test_unknown_item_and_creator_updates_are_refused`, PUT/DELETE for bookmark/like | 4 |
| A3 | Digest answer always says unbookmarked | marks: `test_bookmark_and_like_are_saved_and_returned` | 1 |
| A4 | One marks query per item | marks: `test_digest_answer_loads_marks_in_one_query` | 1 |
| A5 | Delete an empty marks row | marks: `test_removing_marks_keeps_an_empty_row` | 1 |
| A6 | Allow extension-token mark writes | marks: `test_cross_site_and_extension_token_cannot_mark` | 1 |
| A7 | Store note without trimming | marks: `test_feedback_is_saved_stripped_and_replaced` | 1 |
| A8 | Check note length before trimming | marks: `test_note_of_500_characters_after_trimming_is_kept` | 1 |
| A9 | Remove no-summary guard | marks: `test_feedback_needs_a_markable_item_with_a_summary` | 1 |
| A10 | Append all mark notes to model summary input | marks: `test_marks_are_not_sent_to_the_model` | 1 |
| A11 | Omitted note retains earlier note | marks: `test_feedback_is_saved_stripped_and_replaced` | 1 |
| U1 | Optimistically change bookmark state | article: `bookmarks an item once the server saves it` | 1 |
| U2 | Remove busy guard | article: `bookmarks an item once the server saves it` | 1 |
| U3 | Announce Saved instead of Bookmarked | article: `bookmarks an item once the server saves it` | 1 |
| U4 | Hide server error | article: `shows the server's message and keeps the state when a change fails` | 1 |
| U5 | Render actions before body | article: `shows Bookmark and Like on topic items and Feedback only with a summary`; view: `keeps the images inside the summary cell and before Also read`; view: `keeps every item in one markup order regardless of summary length or availability` | 3 |
| U6 | Remove wide actions rule | tokens: `places digest headings beside summaries only above 1100px` | 1 |
| U7 | Remove Bookmark's screen-reader title | article: `shows Bookmark and Like on topic items and Feedback only with a summary` | 1 |
| U8 | Do not restore Feedback focus after saving | article: `saves rating and note together and returns focus to Feedback` | 1 |
| U9 | Send feedback without a rating | article: `asks for a rating before saving` | 1 |
| U10 | Show Remove feedback on an unrated item | article: `saves rating and note together and returns focus to Feedback` | 1 |
| U11 | Omit ItemActions key | article: `does not carry an item's marks into the next digest` | 1 |
| U12 | Do not clear announcement when starting a change | article: `likes and unlikes an item` | 1 |
| U13 | Omit check icons from pressed toggles | article: `starts from the saved marks` | 1 |
| B1 | Sort bookmark timestamps ascending | marks: `test_bookmarks_list_newest_first_with_digest` | 1 |
| B2 | Filter liked rather than bookmarked items | marks: `test_bookmarks_list_holds_only_bookmarked_items` | 1 |
| B3 | Skip bookmark image filtering | marks: `test_bookmarks_list_filters_images_like_the_digest` | 1 |
| B4 | Remove an entry immediately after unbookmarking | bookmarks: `keeps an entry after its bookmark is removed` | 1 |
| B5 | Map Bookmarks screen to Latest | app: `marks History current on the Bookmarks screen` | 1 |
| B6 | Omit digest language from summary | bookmarks: `lists bookmarked items with their digest link` | 1 |
| H1 | Remove D9 focus restoration | home: `moves focus to run-bar Generate when a new digest replaces the shown one while an item control has focus` | 1 |
| Doc | Remove Privacy sentence | readme: `test_readme_describes_bookmarks_and_their_privacy` | 1 |

A10 was the explicitly authorized temporary runner edit. A6 temporarily changed
the extension-operation allowlist for the named security mutation. Both were
restored exactly; neither area has a durable implementation change.

### Authorized amendments and other deviations

1. **Task 2.5 stopped for the existing exact-markup comparison.** React `useId`
   generated different panel ids between Home and the saved digest rendering.
   The existing test `shows the same digest reading markup on Home and the saved
   digest page` failed. No existing test was weakened. Claude Code amended the
   task in `d39e9da`: use `feedback-${item.id}` instead, retaining
   its derived ids. The complete frontend suite and build then passed.
2. **Task 3.5 stopped for the new Bookmarks accessibility check.** Sharing h3 item
   titles directly under the Bookmarks h1 caused axe `heading-order` to fail
   (**374 passed, 1 failed** in the full frontend suite). Claude Code amended the
   task in `71ce9a2`: shared ItemContent accepts `headingLevel?: 2 | 3`,
   default 3; digest titles stay h3, Bookmarks uses h2, and the class stays
   `item-title`. The complete frontend suite and build then passed.
3. The new Bookmarks fixture's summary text was made English while preserving
   `lang="zh-Hans"` and its assertion, to satisfy the repository-additions rule.
4. No other plan behavior was dropped, narrowed, or deferred. Protected
   proposal/design/spec, decision-log and requirements-change files were not
   edited by Droid. Only task checkboxes were changed in tasks.md by Droid;
   the two substantive task amendments above were authored by Claude Code.

### Group commits and remaining work

| Group | Commit |
| --- | --- |
| 1 | `bf52a3c feat: bookmark and like saved digest items (#8)` |
| 2 | `91ff9ca feat: save summary ratings and feedback notes (#8)` |
| 3 | `f7154a7 feat: list bookmarked items with links to their digests (#8)` |
| 4 | `08e0642 feat: keep item controls safe across deletion and digest changes (#8)` |
| 5 | The documentation commit containing this report, AI usage entry and final task checkboxes |

All implementation tasks are complete. No dependencies, Settings, extension
source, digest generation, or model-provider code were durably changed. Tests
used synthetic data and no real network/provider calls or credentials.

Per the implementation instructions, **no Docker command, Docker smoke, container
or volume operation, or port 8800 access was performed**. Independent code/spec
review, Docker smoke and live-browser checks remain for Claude Code. No push,
merge, tag, PR, archive or other outside-platform write was performed. Session
id, turns and minutes are left for Claude Code to add to the AI usage log.

## Fix round 1

### Scope and diagnosis

Factory Droid (GPT-6.1 Sol), 2026-11-26, resumed in Claude Code's review worktree
from `b3519a0`. Completed task group 6 only, following `openspec-apply-change`,
`tdd`, and the supplied review diagnosis with `diagnosing-bugs`. Claude Code
authored the task/design amendments in `723fa0a` and `b3519a0` under the user's
plan approval. The amendments during the initial implementation were likewise
made by Claude Code under that approval, not approved separately by the user.

The busy-control invariant is that a pressed toggle keeps its check mark and
strong border, but its text takes the same muted color as any other busy button.
Ranked hypotheses and their predictions:

1. **Pressed color overrides the busy color.** Restricting only the pressed color
   declaration to controls without `aria-disabled="true"` should fix the busy
   appearance without removing the pressed border. Confirmed: the existing
   pressed rule had the higher-specificity `color: var(--fg) !important`;
   the prescribed CSS guard failed before the fix and passed after it. R1
   reproduced the failure by restoring that old rule.
2. **Generic busy styling is incorrect.** This would also affect non-pressed
   controls. The existing `.btn[aria-disabled="true"]` rule already uses the
   disabled background and muted text, matching `.btn:disabled`. The existing
   busy-style checks remained green in the full suite.
3. **The control lacks its busy attribute.** This would fail the held Like
   request's `aria-disabled` assertion before any CSS edit. That test already
   passed in 6.1; R3 showed it detects the missing attribute.

The prescribed CSS-source seam provided the minimal deterministic check; no
debugger, extra instrumentation, or temporary helper files were needed. The other
production correction moves "From" into the Bookmarks digest link, matching the
spec and amended D7 rather than the earlier contradictory design line.

### 6.1: tests before implementation

The frontend selection had **2 failed, 4 passed, 153 skipped in 4 files**, 941ms.
The backend selection had **20 passed**, 3.53s. Production code had not yet changed.

| Test or cases | Initial result |
| --- | --- |
| tokens: `does not let the pressed style override a busy control` | Failed: no exact pressed/non-busy selector existed; the received color block was empty |
| Bookmarks: `lists bookmarked items with their digest link` | Failed: no link named `From No. 5 · 3 Oct 2026`; "From" was outside the link |
| DigestArticle: `ignores a second Like while the change is saved` | Passed |
| DigestArticle: `ignores Save feedback while the feedback is saved` | Passed |
| DigestArticle: `shows the saved rating's own word` | Passed |
| Home: `keeps focus on an item's title link when a new digest replaces the shown one` | Passed |
| marks: `test_cross_site_and_extension_token_cannot_mark` | All 18 cases passed: six writes crossed with Origin, Sec-Fetch-Site alone, and extension-token refusals |
| marks: `test_marks_survive_source_deletion_and_restart` | Passed, now including Poor feedback and the note Kept |
| X settings: `test_delete_all_x_data_removes_marks_with_an_emptied_digest` | Passed, including the X-only item's valid summary, bookmark and Good rating before deletion |

New tests were five frontend cases and the X-only digest case. Existing tests
were strengthened only where 6.1 permits: the Bookmarks link name, the security
matrix, and source-deletion/restart feedback persistence. No other existing test
was modified. The existing pytest/Vitest suites and build checks were retained.

### 6.2: implementation and green checks

The only durable production edits are:

- Split the pressed-toggle CSS into an unconditional strong border rule and a
  foreground-color rule restricted to non-busy toggles.
- Include the whole "From No. … · date" inside the Bookmarks digest link.

Full backend verification passed **1410 tests, 2 warnings in 41.18s**. The full
frontend suite passed **381 tests in 15 files**, 7.52s, and its TypeScript/Vite
build passed, 41 modules, 166ms. This includes all 6.1 tests. No unrelated existing
test failed.

### 6.3: named mutations

All **R1–R11** were detected. R8 has two prescribed variants, so there were
**12 isolated mutation runs**. After each run, including between R8 variants,
the file was edited back; the complete file and complete `git diff --binary`
matched their saved pre-mutation versions exactly. No mutation survived or
remains in the worktree.

The file abbreviations from the initial implementation table apply below.

| Mutation | Fault | Actual failing checks | Result |
| --- | --- | --- | --- |
| R1 | Restore the single pressed rule with unconditional color | tokens: `does not let the pressed style override a busy control` | 1 failed, 20 skipped |
| R2 | Put From outside the digest link | bookmarks: `lists bookmarked items with their digest link` | 1 failed, 4 skipped |
| R3 | Omit Like's busy aria-disabled | article: `ignores a second Like while the change is saved` | 1 failed, 29 skipped |
| R4 | Remove the feedbackBusy early return | article: `ignores Save feedback while the feedback is saved`, observing two requests instead of one | 1 failed, 29 skipped |
| R5 | Omit Remove feedback's busy aria-disabled | article: `ignores Save feedback while the feedback is saved` | 1 failed, 29 skipped |
| R6 | Always display Rated good | article: `shows the saved rating's own word` | 1 failed, 29 skipped |
| R7 | Move Home focus for any .item descendant | home: `keeps focus on an item's title link when a new digest replaces the shown one`, Generate incorrectly focused | 1 failed, 102 skipped |
| R8, DELETE only | Permit extension DELETEs on digest-item paths | marks: `test_cross_site_and_extension_token_cannot_mark[extension-DELETE-<mark>]`, for bookmark, like and feedback | 3 failed, 15 passed |
| R8, PUT and DELETE | Permit both extension write methods | marks: all six extension cases of `test_cross_site_and_extension_token_cannot_mark` | 6 failed, 12 passed |
| R9 | Remove the Sec-Fetch-Site refusal condition | marks: all six fetch-site cases of `test_cross_site_and_extension_token_cannot_mark` | 6 failed, 12 passed |
| R10 | Omit change_feedback's commit | marks: `test_marks_survive_source_deletion_and_restart` and all four `test_invalid_feedback_changes_nothing` cases, because saved feedback read back as None | 5 failed |
| R11 | Remove CASCADE from the migration foreign key | x: `test_delete_all_x_data_removes_marks_with_an_emptied_digest` and `test_delete_all_x_data_removes_marks_on_x_items_only`, both with foreign-key IntegrityError; db: `test_item_marks_migration_creates_empty_table_and_downgrades`, with missing ondelete metadata | 3 failed |

The security mutants returned 200 where 403 was required. DELETE cases started
with Bookmark, Like and Good feedback saved, so allowing the request through
would change a real mark. R10 also demonstrates that the strengthened persistence
check is not satisfied merely by the feedback PUT's response.

### 6.4: final checks

All checks below exited 0 after every mutation had been restored. Backend
commands ran in `backend/`. Frontend and extension commands ran in their own
directories, each using
`export NVM_DIR="$HOME/.nvm"; . "$NVM_DIR/nvm.sh"; nvm use 22.17.1`
before installing and checking. Both printed Node `v22.17.1`, npm `10.9.2`.

| Directory | Command | Actual result |
| --- | --- | --- |
| `backend/` | `uv run --offline pytest` | **1410 passed, 2 warnings in 38.72s** |
| `frontend/` | `npm ci --offline` | 124 locked packages installed, 125 audited, 0 vulnerabilities reported |
| `frontend/` | `npm test -- --run` | **381 passed in 15 files**, 6.51s |
| `frontend/` | `npm run build` | TypeScript/Vite passed; 41 modules, 152ms |
| `extension/` | `npm ci --offline` | 120 locked packages installed, 121 audited, 0 vulnerabilities reported |
| `extension/` | `npm test -- --run` | **169 passed in 7 files**, 3.54s |
| `extension/` | `npm run build` | TypeScript/Vite/build checker passed; 10 modules, 111ms |
| Repository root | `DO_NOT_TRACK=1 openspec validate add-item-bookmarks-and-feedback --strict` | `Change 'add-item-bookmarks-and-feedback' is valid` |
| Repository root | `git diff --check` | Passed with no output |

The two backend warnings are the existing intentional malformed-token-usage
Pydantic serialization warnings noted above. Both npm installs emitted the
existing `whatwg-encoding` deprecation warning. Frontend output was HTML 0.82 kB,
CSS 21.47 kB (gzip 5.42 kB), and JavaScript 328.38 kB (gzip 100.23 kB).

Only group 6 task checkboxes, its prescribed tests, the two production files and
the two process logs changed in this round. No protected planning artifact,
dependency manifest/lockfile, backend production code, migration, Home source,
DigestArticle source, Settings, extension source or smoke script was durably
changed. No plan deviation, unexpected failure, invalid mutation attempt, or
concurrency rerun occurred. No temporary helper or debug instrumentation remains.
Docker smoke and live-browser review stay with Claude Code; no Docker command,
container/volume operation, port 8800 access, push, merge, tag or PR was performed.
The commit containing this section completes group 6; session metrics remain
for Claude Code.

## Review by Claude Code

Reviewed in worktree `review8` on the branch. Droid's first run started at the plan commit `0546693` and ended at `613140d`; it stopped twice for gaps in the plan, which Claude Code closed in `d39e9da` and `71ce9a2`. Fix round 1 started at Claude Code's round plan `723fa0a` (refined in `b3519a0` after the fresh-eyes check) and ended at `bb44cfe`.

### Checks

| Check | Result |
| --- | --- |
| Backend `uv run --offline pytest` | 1392 passed on `613140d`; 1410 after fix round 1 |
| Frontend `npm test -- --run`, `npm run build` | 376 passed on `613140d`, 381 after fix round 1; build passed |
| Extension `npm test -- --run`, `npm run build` | 169 passed; build passed |
| `DO_NOT_TRACK=1 openspec validate --all --strict` | 12 passed |
| `git diff --check 0546693..HEAD` | clean |
| `scripts/docker-smoke.sh catchup:fix8-local` (built from `613140d`, then from `bb44cfe`) | 12 of 12 both times |

### Live check

Scratch containers from `catchup:fix8-local` ran on their own volumes and ports 8858 and 8859. Saved digests were written into the scratch database with a short script run inside the container, because a run needs a model.

- **Main screen, digest No. 2:** the item with a summary had Bookmark, Like, and Feedback; the item whose summary was unavailable had Bookmark and Like only. Bookmark became pressed with a check mark after the answer, focus stayed on it, and "Bookmarked." was announced.
- **Feedback:** Save feedback without a rating showed "Choose Good or Poor." as an alert and marked both options invalid. Poor with a note saved both, closed the panel, returned focus to Feedback, showed "Rated poor", and announced "Feedback saved."; the digest answer held the rating and the note.
- **Bookmarks:** History's Bookmarks link opened "Bookmarks · CatchUp" with History as the current navigation item; the entry's title was an `h2`, its digest link went to `/digests/2`, and it kept "Rated poor". Removing the bookmark kept the entry, unpressed, with focus on Bookmark and "Bookmark removed." announced; after a reload the screen showed "No bookmarks yet" and "Open the latest digest".
- **Layout:** at 375 px the controls followed the summary and the page did not scroll sideways; at 1440 px they sat under the title, beside the summary.
- **After fix round 1 (port 8859):** a pressed Bookmark with `aria-disabled="true"` set for the check took the same muted text and background as a busy unpressed button (text rgb(184, 178, 165)) and kept its strong border and check mark; before the fix it kept the full text color. The Bookmarks entry's link was named "From No. 1 · 26 Nov 2026".

The containers, their volumes, the seed script, and the browser tabs were removed afterwards.

### Findings

- **Droid stopped twice, both times rightly**, on gaps in Claude Code's plan:
  - at task 2.5, React `useId` gave the feedback panel different ids on the main screen and the saved digest page, so the existing markup comparison failed; the panel id now comes from the digest item id (`d39e9da`);
  - at task 3.5, the Bookmarks screen's item titles were `h3` directly under its `h1`, which axe reports as `heading-order`; `ItemContent` now takes a heading level, and Bookmarks uses `h2` (`71ce9a2`).
- **`/code-review` (high) on `0546693..613140d`:** two nits, not changed: an item's controls keep the marks they were first shown with if another tab changes them (one local user; a repeated request is harmless), and removing a mark that does not exist leaves an empty row (the plan's mutation A5 keeps it). **On the fix round:** no findings.
- **Spec sub-agent** (independent, detached worktree): all 35 named mutations failed their tests. Claude checked its findings against the code:
  - **Fixed in fix round 1 (Droid; D-023 class a):** a busy pressed toggle did not look disabled, because the pressed rule's `!important` text color outranked `.btn[aria-disabled="true"]`.
  - **Fixed in fix round 1 (Droid; class b):** design D7 linked only "No. … · date", while the spec makes the whole "From No. … · date" the link; D7 was corrected and the code follows the spec.
  - **Fixed in fix round 1 (Droid; spec scenarios no test covered):** Like while saving, Save feedback and Remove feedback while saving, the word "poor" after a Poor rating, focus on an item's title link staying put when a new digest arrives, every mark write refused cross-site (Origin, `Sec-Fetch-Site`, and a browser connection token), a rating kept after its source is deleted, and marks removed with a digest that deleting X data leaves empty. Mutations R1–R11 each failed their named tests.
  - **Fixed by Claude (wording):** the Droid entry and this report said the user had approved the two task amendments; they were Claude Code's, under the plan approval. The prompt excerpt now quotes the prompts as run.
  - **Recorded, not fixed:** not writing `rated_at` (an internal column the spec does not name), the Bookmarks query's topic-kind filter (equivalent: the API refuses marks on Creator updates), and Feedback for an item whose summary is empty but not marked unavailable (a data shape the runner does not produce).
- **Fresh-eyes check of the round plan:** no blocker; its six findings were checked and applied before Droid ran (a seed that could not be rated, mutations R9–R11 for the tests that pass on today's code, design D6 matching the two CSS rules, an exact CSS check, a stronger focus check, and marked items before each refused `DELETE`).
