# Titles, release trigger, and offline icon: implementation checks

2026-10-19, branch `polish-titles-ci-and-offline-icon`. All commands ran in this worktree; backend and frontend commands ran in their respective directories.

## Red-first checks

| Check | Actual result before implementation |
| --- | --- |
| `uv run pytest -q tests/test_discovery.py -k 'untitled_cut_text_ending_in_ellipsis or untitled_short_text_ending_in_dots or untitled_social_post_uses_plain_text_at_word_boundary'` | **2 failed, 2 passed, 49 deselected**. The ASCII `...` cut produced `...…`, and the Unicode `…` cut produced `……`. The short-text guard and existing hockey title passed. |
| `ruby -e 'require "yaml"; push = YAML.load_file(".github/workflows/release.yml").fetch(true).fetch("push"); expected = ["docs/**", "openspec/**", "assets/**", "**/*.md"]; abort "missing paths-ignore: #{expected.inspect}" unless push["paths-ignore"] == expected; abort "changed branches or tags" unless push["branches"] == ["main"] && push["tags"] == ["v*.*.*"]; puts "push: #{push.inspect}"'` (repository root) | Exited 1: `missing paths-ignore: ["docs/**", "openspec/**", "assets/**", "**/*.md"]`. Ruby's YAML parser treats the unquoted `on` key as boolean `true`; `.fetch(true)` selects that trigger. |
| `npm test -- --run src/install.test.ts` | **1 failed, 4 passed**. The offline page had zero icon links, rather than the one inline link required by the test. |
| `test -f docs/process/test-report-polish-titles-ci-and-offline-icon.md` | Exited 1 before writing this report. |

## Passing checks

| Check | Actual result |
| --- | --- |
| `uv run pytest` (backend, after title fix) | **414 passed**. |
| `actionlint .github/workflows/release.yml` (repository root) | Exit 0, no output. |
| The Ruby trigger check above (repository root, after workflow edit) | Exit 0: `push: {"branches"=>["main"], "tags"=>["v*.*.*"], "paths-ignore"=>["docs/**", "openspec/**", "assets/**", "**/*.md"]}`. |
| `git diff --name-only -- .github/workflows` (after workflow edit) | `.github/workflows/release.yml` only; `ci.yml` and other workflows unchanged. |
| `npm test -- --run src/install.test.ts` (after icon edit) | **5 passed**. The decoded data SVG matches `public/icon.svg` exactly, including its viewBox and both fill colors; the page declares no other icon link. |
| `npm test -- --run` (after icon edit) | **200 passed** in **13 files**. |
| `npm run build` (after icon edit) | TypeScript/Vite passed, **41 modules** transformed. |
| `npm run build` (frontend, final checks, run first) | Passed, **41 modules** transformed. |
| `uv run pytest --cov=catchup --cov-report=term` (backend, final checks) | **414 passed**, **96% statement coverage** (1,855/1,926 statements; 71 missed). `sources/feeds.py`: 97% (141 statements, 4 missed). |
| `npm test -- --run` (frontend, final checks) | **200 passed** in **13 files**. |
| `actionlint` (repository root, final checks) | Exit 0, no output. |
| `openspec validate polish-titles-ci-and-offline-icon --strict` (repository root) | `Change 'polish-titles-ci-and-offline-icon' is valid`. |

`npm ci` installed 124 locked frontend packages and reported 0 vulnerabilities. The first frontend build after adding the icon test failed with TypeScript TS2591 because the test used `Buffer` without Node types; it was changed to the browser `TextDecoder`/`atob` APIs, and the focused test, full suite, and build then passed. Tests did not fetch a real feed or model.

**Not run before merge:** a documentation-only push to `main` proving it does not start "Release image"; a real-browser check that the offline page's tab icon appears when the server is stopped. The YAML and DOM tests verify configuration and asset content, not GitHub's live trigger or the browser's rendered tab.

## Fix round 1 (2026-10-19)

Commands below ran in this worktree; `uv run pytest` ran in `backend/`, `npm` commands in `frontend/`, and `actionlint` and `openspec` in the repository root. All mutations were applied temporarily by hand and reverted before committing.

| Check and command | Actual result |
| --- | --- |
| `uv run pytest -q tests/test_discovery.py -k untitled_cut_cjk_dots_gets_only_one_ellipsis` before the backend change | Expected red: **3 failed, 53 deselected** (`。。。`, `．．．`, and `⋯⋯` remained before `…`). |
| `uv run pytest -q tests/test_discovery.py -k 'untitled_cut_keeps_part_of_long_word or untitled_cut_of_all_dots'` before the backend change | **1 failed, 1 passed, 56 deselected**. `"... " + "A" * 100` yielded bare `…`; 100 dots already yielded `…`. |
| `uv run pytest -q tests/test_discovery.py -k 'untitled_cut_with_space_before_dots or untitled_cut_just_over_80_characters or untitled_cut_of_all_dots'` before mutations | **3 passed, 57 deselected**. |
| `uv run pytest -q tests/test_discovery.py -k untitled_cut_with_space_before_dots` with `rstrip(".…")` (no space), then after reverting | Mutation: **1 failed, 59 deselected** (`B` prefix ended in ` ... …`); reverted: **1 passed, 59 deselected**. |
| `uv run pytest -q tests/test_discovery.py -k untitled_cut_just_over_80_characters` with trailing-dot stripping moved to the whole text before the cut, then after reverting | Mutation: **1 failed, 59 deselected** (title ended in `..…`); reverted: **1 passed, 59 deselected**. |
| `uv run pytest -q tests/test_discovery.py -k 'untitled_cut or untitled_social_post or untitled_long_cjk_text'` after the backend change | **11 passed, 49 deselected**. |
| `uv run pytest -q tests/test_discovery.py -k untitled_cut_of_all_dots` with stripping after the fallback 80-character cut skipped | Mutation: **1 failed, 59 deselected** (80 dots before `…`); after reverting, the title-focused run above passed again. |
| `uv run pytest` after reverting mutations | **421 passed**. |
| `npm test -- --run src/install.test.ts` on the unchanged offline page | **5 passed** after `npm ci` installed 124 locked packages (0 vulnerabilities). Before installation, Vitest was missing and the command exited 127. |
| `npm test -- --run src/install.test.ts` with temporary `<img src="/icon.svg">` in `public/offline.html` | Expected mutation failure: **1 failed, 4 passed**; the new assertion detected the external icon file request. The mutation was reverted, and `git diff -- frontend/public/offline.html` was empty. |
| `npm test -- --run` and `npm run build` after reverting | **200 passed** in **13 files**; TypeScript/Vite build passed with **41 modules** transformed. |
| `npm run build` (first in final check sequence) | Passed; **41 modules** transformed. |
| `uv run pytest --cov=catchup --cov-report=term -q` | **421 passed**, **96% statement coverage** (1,858/1,929 statements; 71 missed). `sources/feeds.py`: 97% (144 statements, 4 missed). |
| `npm test -- --run` (final check sequence) | **200 passed** in **13 files**. |
| `actionlint` (final check sequence) | Exit 0, no output. |
| `openspec validate polish-titles-ci-and-offline-icon --strict` (final check sequence) | `Change 'polish-titles-ci-and-offline-icon' is valid`. |

**Plan amendment and pause:** The first version of task 5.1 called 100 dots a red-first behavior change. Its test already passed before implementation, so work stopped with the tests left uncommitted rather than inventing a mutation. The follow-up amendment (`6b317a8`) recast it as a passing guard and named the post-fallback-strip mutation. The guard then failed under that mutation, which was reverted.

**Known limits:** An entry with no guid, no unique link, and no title derives its identity key from its title and date. If this change alters that title, it can be collected once more after upgrade. `release.yml` has no committed trigger test; its configuration was checked with `actionlint` and a one-off YAML parse, not a real documentation-only push to `main`. The real-browser offline-tab check also remains unperformed.

## Fix round 2 (2026-10-19)

This round changed only `backend/tests/test_discovery.py` and these process documents. Commands with `uv run pytest` ran in `backend/`; validation and Git checks ran from the repository root. Every named mutation was applied temporarily to `feeds.py` by hand, run against its new test, then reverted. `git diff -- backend/src/catchup/sources/feeds.py` was empty afterward.

| New test and focused command (`uv run pytest -q tests/test_discovery.py -k <name>`) | Before mutation | Temporary mutation and red result |
| --- | --- | --- |
| `untitled_cut_preserves_word_boundary_before_long_word` | **1 passed, 60 deselected** | `if not trimmed:` → `if True:`: **1 failed, 60 deselected**; 80-character cut included `super` instead of stopping after the last whole `word`. |
| `untitled_cut_at_81_characters_strips_dots_after_cut` | **1 passed, 61 deselected** | Insert `content_text = content_text.rstrip(" .…。．⋯") or content_text` before the cut: **1 failed, 61 deselected**; premature trimming left 78 characters and caused an `IndexError` at `content_text[80]`. |
| `untitled_cut_of_cjk_full_stops_is_a_single_ellipsis` | **1 passed, 62 deselected** | Fallback strip set → `" .…"`: **1 failed, 62 deselected**; 80 `。` remained before `…`. |
| `untitled_cut_of_dots_and_spaces_is_a_single_ellipsis` | **1 passed, 63 deselected** | Remove the space from the fallback strip set: **1 failed, 63 deselected**; spaced dots remained before `…`. |

After the four reversions:

| Command | Actual result |
| --- | --- |
| `uv run pytest -q tests/test_discovery.py -k 'untitled_cut_preserves_word_boundary_before_long_word or untitled_cut_at_81_characters_strips_dots_after_cut or untitled_cut_of_cjk_full_stops_is_a_single_ellipsis or untitled_cut_of_dots_and_spaces_is_a_single_ellipsis'` | **4 passed, 60 deselected**. |
| `uv run pytest -q` | **425 passed**. |
| `git diff --name-only` (before the 6.1 commit) | Only `backend/tests/test_discovery.py`; no `feeds.py` diff. |
| `uv run pytest --cov=catchup --cov-report=term -q` | **425 passed**, **96% statement coverage** (1,858/1,929; 71 missed). `sources/feeds.py`: 97% (144 statements, 4 missed). |
| `openspec validate polish-titles-ci-and-offline-icon --strict` | `Change 'polish-titles-ci-and-offline-icon' is valid`. |

The frontend suite and build were not repeated in this test-only round; neither frontend nor runtime files changed.
