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
