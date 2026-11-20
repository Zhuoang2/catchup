# Test report: merge-extension-page-extractors

Date: 2026-11-20. Implementer: Factory Droid, GPT-6.1 Sol.
Starting commit: `95e963c`. Scope: OpenSpec task groups 1–4, implemented in order.

## Environment and final checks

All extension commands ran from `extension/` after:

```sh
export PATH="$HOME/.nvm/versions/node/v22.17.1/bin:$PATH"
```

`node --version` reported `v22.17.1`. `npm ci --offline --no-audit --no-fund`
passed, installing 120 locked packages from the local cache. It printed the
existing `whatwg-encoding` deprecation warning. No package downloads or
dependency-file changes were made. The installed tools reported Vitest 4.1.12
and Vite 8.3.5.

| Command | Actual result |
| --- | --- |
| `npm test -- --run` | PASS, exit 0: 7 files, 162 tests passed. |
| `npm run build` | PASS, exit 0: `tsc --noEmit`, Vite production build (10 modules transformed), and `node scripts/check-build.mjs`. |
| `DO_NOT_TRACK=1 openspec validate merge-extension-page-extractors --strict` (repository root, existing PATH) | PASS, exit 0: change is valid. |
| Source search for `extractReadable\|extractGeneric\|extract/readable\|extract/generic` in `extension/src` using the dedicated search tool | No matches after group 2. |
| `git diff -- README.md` before group 3 commit | Exactly the planned three-line paragraph addition and two-line sponsor-bullet removal. |
| `git diff --check` before each group commit | PASS after removing trailing whitespace introduced while copying the new test file. |
| `git diff 95e963c --exit-code -- extension/package.json extension/package-lock.json extension/src/extract/fixtures openspec/changes/merge-extension-page-extractors/proposal.md openspec/changes/merge-extension-page-extractors/design.md openspec/changes/merge-extension-page-extractors/specs docs/process/decision-log.md docs/process/requirements-changes.md` | PASS, exit 0: protected files unchanged. |

No real network requests were made by tests. Backend and frontend checks were
not run because neither application changed.

## Test-first observations

| Group | Red command and observed result | Green command and observed result |
| --- | --- | --- |
| 1 | `npx vitest run src/extract/page.test.ts`: exit 1, one failed suite, no tests collected, only the missing `./page` import error. No production code had been changed. | After adding `page.ts`, `npx vitest run src/extract`: exit 0, 4 files and 76 tests passed. This still included the old extractor tests, as required. |
| 2 | `npx vitest run src/test/popup.test.ts --reporter=json`: exit 1, all 9 changed/new cases failed, the other 80 cases passed. The tiny-note test saved sponsor text; order checks still saw the old extractors; the X-null mock could not save through the old chain. | After changing the popup and deleting the four old extractor files, `npx vitest run`: exit 0, 7 files and 162 tests passed. |
| 3 | `npx vitest run src/test/docs.test.ts`: exit 1, the changed contract failed on missing `only text the page shows`; 3 other tests passed. | After the two README edits, the same command passed: 1 file, 4 tests. |
| 4 | Reporting/checks only; no new behavior or tests. | Final test, build, and strict validation results are above. |

### Extractor tests

`extension/src/extract/page.test.ts` contains 23 behavioral cases, each run
directly and serialized, for 46 tests. Every successful extraction asserts that
the live `document.body.outerHTML` is unchanged through the shared `run`
wrapper. P5 removes the fixture's note body before that snapshot. Readability
is loaded with `window.eval(library)` and removed in `afterEach`; the head and
body are cleared there too. The six committed new fixtures were not edited.

These names also define the selectors used in the mutation runs below.

| ID | Test name (after `direct: ` or `serialized: `) | Mutations caught in the named runs |
| --- | --- | --- |
| P1 | saves a tiny note, not the longer sponsor banner beside it | E1 |
| P2 | saves a post before an indented sponsor block | E1 |
| P3 | saves a short link post, not the sidebar | E1, E2, E11 |
| P4 | saves the release link from the title row first | E6, E8 |
| P5 | saves the title row of a release note without a body | E1, E2, E6, E8, E9 |
| P6 | leaves out hidden text and links with Readability | E3, E4, E5 |
| P7 | leaves out hidden text and links without Readability | E3, E4, E5 |
| P8 | reads the date from the article header | E10 |
| P9 | does not put a title link to the page itself first | E7 |
| P10 | saves each link address once | E11 |
| P11 | saves the image address the page loaded | E3, E12 |
| P12 | saves the short post instead of the longer sponsor banner | Existing reader case copied with assertions preserved; date assertion added. Not selected for a named mutation. |
| P13 | keeps only post text, links and images from a page without article | Existing reader case and assertions preserved. Not selected for a named mutation. |
| P14 | falls back to the main region when Readability finds no text | E13 |
| P15 | falls back to the main region when Readability throws | E14 |
| P16 | reads a page without main text from its body, without navigation | Replaces the former navigation-only rejection. Not selected for a named mutation. |
| P17 | matches the title without its site name, and skips a header link | E15, E16 |

The following six existing generic cases were copied with their assertions
unchanged and run without Readability, in both modes. They passed in the full
checks; no named mutation run selected them:

- reads article metadata, text, images and links without changing the page;
- falls back to title, host and main text when metadata is absent;
- limits content, images, links and rejects non-HTTP URLs;
- reads a main region inside a form without its outside form ancestor excluding it;
- excludes nav text, links and images strictly inside the selected root;
- does not exclude the selected root even if it is a form.

The obsolete reader-only missing-Readability/null case was removed with its
file, as planned. P7 and the six generic cases now cover extraction without
the library. `x.ts` and its tests were unchanged.

### Popup and README tests

The shared `genericResult` mock now returns the supplied page for every
function injection and `[]` for library-file injection.

| Changed/new test | Observed verification and named mutations |
| --- | --- |
| injects the generic extractor and saves a checked page, then removes it | Red on old injection order; green on `readability.js → extractPage`, save and removal. No named mutation selected. |
| still saves an X profile as a generic page when Add is chosen | Red on old injection order; green on unified chain and one save. No named mutation selected. |
| uses generic page extraction for a help.x.com URL that looks like a post | Red on old injection order; green on unified chain. No named mutation selected. |
| reads the page with readability.js and extractPage after the X extractor returns null | Red on old chain; green on `extractX → readability.js → extractPage` and exactly one save. Kills U1. |
| saves only reader-view post content on a page without an article element | Existing real-Readability/jsdom-tab assertions kept; changed order red then green; tab body unchanged. No named mutation selected. |
| saves only a tiny note, not the sponsor banner, through the popup | New real-Readability/jsdom-tab test: red saved sponsor text; green saves the exact tiny-note text and seed link, with the unified order and unchanged tab body. No named mutation selected. |
| reads https://garden.example/post with readability.js and extractPage | Renamed parameterized case; red on old order, green on unified chain. No named mutation selected. |
| reads https://x.com/someone with readability.js and extractPage | Renamed parameterized case; red on old order, green on unified chain. No named mutation selected. |
| still runs extractPage when injecting readability.js rejects | Red on old extractor name; green on unified order and exactly one save despite injection rejection. Kills U2. |
| documents collection boundaries, reader license and the linked-pages wait | Red before README edits; green after; requires `only text the page shows` and forbids `sponsor text`. Kills R1. |

## Isolated mutation results

Every mutation was applied **alone**, tested, and restored before the next one.
For each restoration, the complete source was compared byte-for-byte with the
pre-mutation source, and a fresh `git diff -- <mutated-file>` was compared with
the baseline diff. All 19 restorations were identical. No mutated source was
committed.

For E1–E16 the exact command form was:

```sh
npx vitest run src/extract/page.test.ts -t '<selector>' --reporter=json
```

`<selector>` was the `|`-joined, regex-escaped full test names of the P IDs
listed in each row above, without the mode prefix. Thus both modes ran, with
all other cases skipped. The failed counts below include both modes. Every
selected case failed, none passed, and every run exited 1 as expected.

| ID | Single mutation | Selected cases | Failed / skipped | Observed failure |
| --- | --- | --- | --- | --- |
| E1 | Omit `charThreshold: 1` | P1, P2, P3, P5 | 8 / 38 | Sponsor/sidebar text replaces the short post or bare title row. |
| E2 | Set `linkDensityModifier: 0` | P3, P5 | 4 / 42 | Link post is only the date; bare release text lacks its title. |
| E3 | Skip the live/copy walk and removals | P6, P7, P11 | 6 / 40 | Hidden text is saved and the image uses the small address. |
| E4 | Disable the visibility branch | P6, P7 | 4 / 42 | Ghost text/paragraphs remain. |
| E5 | Remove a visibility-hidden element with all descendants | P6, P7 | 4 / 42 | `Shown inside ghost` is lost. |
| E6 | Skip the title-link loop | P4, P5 | 4 / 42 | The release address is not first. |
| E7 | Remove both own-address comparisons | P9 | 2 / 44 | The page's own canonical/fragment title link is prepended. |
| E8 | Match title by containment, with text length at least 3 | P4, P5 | 4 / 42 | The `Release` label address is first instead of the release address. |
| E9 | Parse `shown` rather than its clone | P5 | 2 / 44 | Readability's changes prevent preserving the release title link first. |
| E10 | Remove the fallback-region date lookup | P8 | 2 / 44 | Publication time is null instead of the expected timestamp. |
| E11 | Remove the `seen` membership guard | P10, P3 | 4 / 42 | Repeated link addresses are saved. |
| E12 | Disable copying `currentSrc` | P11 | 2 / 44 | The small image address is returned instead of the loaded large address. |
| E13 | Accept Readability content without checking non-space text | P14 | 2 / 44 | Empty text is returned instead of the main-region paragraphs. |
| E14 | Remove the parse try/catch | P15 | 2 / 44 | The stand-in's `broken` error escapes. |
| E15 | Remove excluded-ancestor check from title-link lookup | P17 | 2 / 44 | The header's title link is saved instead of the masthead link. |
| E16 | Remove trailing-site-name title forms | P17 | 2 / 44 | The external title link is missing. |

Additional mutation commands:

```sh
npx vitest run src/test/popup.test.ts -t 'reads the page with readability\.js and extractPage after the X extractor returns null' --reporter=json
npx vitest run src/test/popup.test.ts -t 'still runs extractPage when injecting readability\.js rejects' --reporter=json
npx vitest run src/test/docs.test.ts -t 'documents collection boundaries, reader license and the linked-pages wait' --reporter=json
```

| ID | Single mutation | Actual result |
| --- | --- | --- |
| U1 | Inject Readability only when `!xPost`, leaving the X-null fallback to call `extractPage` directly | KILLED, exit 1: 1 failed, 0 passed, 88 skipped. Order is `extractX → extractPage`, missing the library. |
| U2 | Remove the Readability-injection try/catch | KILLED, exit 1: 1 failed, 0 passed, 88 skipped. The rejection prevents the expected saved confirmation. |
| R1 | Restore only the old two-line sponsor bullet | KILLED, exit 1: 1 failed, 0 passed, 3 skipped. The README contains forbidden `sponsor text`. |

### Recorded survivors, not tested

These are the plan's recorded survivors, not new claims from this run.
No mutation was applied for them:

- **X3:** do not skip script/style/template/noscript during visibility copying;
- **X5:** take the date from body instead of the fallback region;
- **X8:** omit `visibility: collapse`;
- **X9:** prefer `og:title` to Readability's title;
- **X10:** resolve against `location.href` instead of `document.baseURI`;
- **X11:** prefer the fallback region whenever present.

## Preflight and tooling notes

- A read-only independent Droid preflight of code and group 1 found no concrete
  false assumptions, and noted that P13's `blog-no-article` setup must be kept.
  A second fresh, read-only preflight covered groups 2–4 and found none.
- A short jsdom/Readability probe passed. It confirmed live stylesheet
  `display: none`, hidden visibility, and a child's restored visible visibility.
  Strict Readability alone still included stylesheet-hidden text, confirming
  the need for the live-style copy pass.
- The first attempted independent preflight using `claude -p` exited 1 because
  its OAuth session had expired and could not refresh. It read no task files;
  the successful read-only Droid preflights replaced it.
- The first mutation harness patch had invalid line context and was rejected
  before any mutation test ran. Source remained unchanged. The harness was
  corrected to generate full-line hunks, then all E1–E16 ran successfully as
  documented above.
- An initial `git diff --check` found whitespace on blank lines in the copied,
  newly created test file. Those lines were cleaned before the group commit;
  later whitespace checks passed.
- There were no unexpected test red/green results, plan changes, package
  changes, or additional application fixes.

## Not performed, deferred to Claude Code review

As explicitly requested, this run did **not** perform:

- `docker build`;
- `scripts/docker-smoke.sh`;
- the built branch extractor's jsdom comparison on the 11 locally saved real
  pages and their variants;
- the built-in-browser visibility census on the same four live pages;
- a manual Chrome save of a short Simon Willison post and a Tao or Python post.

The build and jsdom fixture/popup tests above are not substitutes for those
live checks. The change is not archived, merged, pushed, tagged, or opened as
a pull request by this run.
