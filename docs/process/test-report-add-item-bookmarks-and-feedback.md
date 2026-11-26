# Test report: add-item-bookmarks-and-feedback (#8)

## Implementation by Factory Droid, 2026-11-25 to 2026-11-26

Implemented the five task groups in the approved change, including the two
user-approved task amendments described below. This report records implementation
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
   digest page` failed. No existing test was weakened. The user approved Claude
   Code's task amendment in `d39e9da`: use `feedback-${item.id}` instead, retaining
   its derived ids. The complete frontend suite and build then passed.
2. **Task 3.5 stopped for the new Bookmarks accessibility check.** Sharing h3 item
   titles directly under the Bookmarks h1 caused axe `heading-order` to fail
   (**374 passed, 1 failed** in the full frontend suite). The user approved Claude
   Code's amendment in `71ce9a2`: shared ItemContent accepts `headingLevel?: 2 | 3`,
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
