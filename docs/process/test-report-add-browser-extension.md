# Test report: add-browser-extension (#58)

2026-10-21. Implemented in task order, with tests written and observed failing before the corresponding implementation. The backend uses offline HTTP and model fakes. Extension tests use invented DOM fixtures, a fake Chrome API, and mocked `fetch`; no real X page or authenticated content was copied into the tests.

## Red-first results by group

| Group | Observed before implementation | After implementation |
| --- | --- | --- |
| 1. Tokens and middleware | Migration, token CRUD, restricted Bearer access, and status checks failed before their implementation. | **601 backend tests passed**. |
| 2. Saved-page API | Capture validation/replacement/removal, built-in source, waiting count, and image-filter checks failed first. | **615 backend tests passed**. |
| 3. Digest and context | Saved-page-only run and captured context scenarios failed first. | **623 backend tests passed**. |
| 4. Frontend | Built-in source and waiting-page UI, model-form isolation, connection, copy and disconnect tests failed first. | **229 frontend tests passed**; build passed. |
| 5. Extension foundation and Follow | Missing manifest/options/popup imports failed the package tests; connected popup checks then failed (11 of 12) until Follow was implemented. A first manifest read used Vite's non-file `import.meta.url` and was corrected to a filesystem path. | **19 extension tests passed**; build passed. |
| 6. Generic extractor and Add | The generic extractor import was missing, then seven add-page popup cases failed before the button and save path existed. | **32 extension tests passed**; build passed. |
| 7. X posts | The X extractor import and three popup routing checks failed first. A quoted-status regression then failed in both direct and serialized modes before matching all status anchors. | **41 extension tests passed**; build passed. |
| 8. CI and guide | Both CI-job and README contract tests failed before the extension job and loading instructions were added. | **43 extension tests passed**, `actionlint` and build passed. |

The three named temporary backend mutations in task 1.3 were each observed failing and reverted: accepting a valid token on every route, skipping token lookup, and not updating `last_used_at`. The task 6.1 named mutation moved `httpUrl` out of `extractGeneric`: all three serialized fixture checks failed with `ReferenceError` while direct checks passed. Restoring the helper inside the function made all six generic checks green. No mutation remains in the branch.

An initial `uv run pytest` selected Python 3.11 and failed to collect an unchanged test using Python 3.12 f-string syntax. `uv sync --python 3.12` fixed the environment without editing the test. For the new extension package, npm 10.8.2's peer resolver threw `Cannot read properties of null (reading 'edgesOut')` when first creating the lockfile. Generating it with `npm install --legacy-peer-deps` resolved that install-time issue; a subsequent plain `npm ci` succeeded. The package test fixture was corrected to wait for the asynchronous connection response and use the project's axe-violation assertion style. The first type check needed `@types/node`, and an anchor selector needed an `HTMLAnchorElement` type; both were corrected before checking off the task.

## Final automated checks

Commands were run in the order specified by task 8.2:

| Command | Result |
| --- | --- |
| `cd frontend && npm run build` | Passed; 41 modules transformed. |
| `cd backend && uv run pytest --cov=catchup --cov-report=term` | **623 passed**, **96%** statement coverage, 2,494/2,586 statements covered (92 missed). `api/extension.py` **95%** (137/144), `main.py` **99%** (121/122), `digest/runner.py` **99%** (271/274), `sources/feeds.py` **97%** (248/256). |
| `cd frontend && npm test -- --run` | **229 passed** in 14 files. |
| `cd extension && npm test -- --run` | **43 passed** in 7 files, including the three missing-build-file checks and direct/serialized extractor fixtures. |
| `cd extension && npm run build` | Passed; type check and Vite build, with `dist/manifest.json`, popup, options and PNG icon present. |
| `docker build -t catchup:extension-local .` | Passed locally; no push. |
| `scripts/docker-smoke.sh catchup:extension-local` | Passed: health, API, HTML/PWA files, saved preference, non-root process, volume database, image exclusions and persistence after restart. The script cleans its throwaway container and volume. |
| `openspec validate add-browser-extension --strict` | Passed. |
| `actionlint .github/workflows/ci.yml` | Passed. |

## Manual checks not performed

- Loading the unpacked extension in a real Chrome or Edge browser.
- Observing which `Origin` the CatchUp server sees from the real extension.
- Checking whether pressing the popup button grants `activeTab` for a live tab.
- Saving a real X post in the user's own logged-in browser; this requires the user's own risk decision under X's terms.

These browser checks remain for review. Automated tests do not prove browser permissions or live DOM compatibility.

## Fix round 1 (D12, 2026-10-21)

Tasks 9.1–9.8 were completed in order, with one commit after each verified task. All tests use invented content, fake model responses, and local HTTP mocks. The first failure or red mutation for each task was:

| Task | Observed red check | Verified result |
| --- | --- | --- |
| 9.1 | With feed links exhausting the budget, then a feed without replies and two captures, the last capture's `context_status` stayed `None`, rather than `gathered`, because the loop broke early. | Replacing `break` with `continue`; focused context suite **32 passed**. |
| 9.2 | Saving `/A` reused a waiting `/a#timestamp` item. Removing `autoescape=True` before the code change made the meaningful-underscore test fail for `/axb#timestamp` vs `/a_b`. | Case-sensitive `substr` identity comparison; extension API suite **31 passed**. |
| 9.3 | A proxy Bearer token returned 401 on the instance's own Origin; an empty captured title stayed blank; labels over 500 characters stayed uncapped. | `cu_`-scoped Bearer policy, title fallback and 500-character caps; **64 passed** in extension API/cross-site suites. |
| 9.4 | The invented page without `<article>` or `<main>` saved “Recent articles” and sponsor text. Three root-scoped generic cases failed in both direct and serialized modes (**6 failures**); `readable.ts` was missing; popup injection-order checks and **6** build-file guard cases failed. | Readability **0.6.0** installed exactly; post-only link/image/text extraction in an isolated jsdom tab; generic root fix, injection/fallback, packaged library/license and linked assets; **65 extension tests** and build passed. A probe confirmed Readability selected the invented post and omitted sidebar/sponsor text. |
| 9.5 | Adding profile links to the X fixture exposed profile links in saved `links`; “Fan of @alice” with `/mallory` links incorrectly appeared as an author reply in both execution modes. | Read handle from the first one-segment profile link, exclude `User-Name` links; **69 extension tests** and build passed. |
| 9.6 | Connected Add showed an unreadable-page error for rejected fetch; Follow, Confirm and Remove showed raw network or JSON errors. Four non-JSON 502 tests failed separately. Feed/podcast/YouTube labels and one/two-page counts failed, and the two CSS files were absent. | Normalize transport/JSON failures, friendly kind/count wording and light/dark CSS. Axe reported no violations in tested popup and options states (jsdom contrast rule disabled); **83 extension tests** and build passed with linked hashed CSS/JS files. |
| 9.7 | The first-run lede test read “Four quick steps” rather than the requested optional-extension text. | Lede corrected, and the Home, context and downgrade checks strengthened; focused backend **42 passed**, focused frontend **102 passed**, frontend build passed. |
| 9.8 | The README contract check failed on the absent “cookies” promise before the documentation update. | The contract test passes; all final checks below passed. |

Named temporary mutations for behavior that was already correct were applied, observed failing, and reverted. None is left in the branch:

| Task | Mutation | Observed failure |
| --- | --- | --- |
| 9.2 | Remove `autoescape=True` before replacing the identity query. | `/a_b` reused the waiting `/axb#timestamp` item instead of creating a second item. |
| 9.3 | Widen the token-only DELETE branch to `/api/`. | Token DELETE of a source returned 204 rather than 403. |
| 9.3 | Remove `require_connection` from each POST/GET/DELETE capture route. | Without a token the three routes returned 201, 200 and 204 rather than 401. |
| 9.5 | Take replies from `articles.filter(a => a !== article)` instead of articles after the focal post. | “A prior post” appeared before the two expected author replies, in both direct and serialized tests. |
| 9.7 | Exclude captures when computing Home's `noSources`. | Capture-only Generate was disabled rather than enabled. |
| 9.7 | Count captures in the digest hero, then independently in the no-digest rail. | Hero read “2 sources · Manage sources” instead of “1 source · Manage sources”; rail read `2` instead of `1`. |
| 9.7 | Use `source.site_url` instead of the capture's own origin. | The invented `/tag/x` page was requested once instead of zero times; the other site's page was also stored in the unmutated run. |
| 9.7 | Remove `recreate="never"` from migration 0006's downgrade. | The feed context row vanished; in a separate run with assertions reversed, the digest item's `item_id` became `NULL`. |

The 9.4 regression used the installed library's actual source via `window.eval`, with cleanup via `delete`, and checked direct and `new Function` executions, the untouched original document, missing library, short navigation-only pages, and popup routing. `npm ci` passed after the exact Readability install and adding `@types/jsdom` for the isolated-tab test. An intermediate build failed on missing jsdom types, and an intermediate test transform failed on a malformed kind-label expression; both were corrected before task verification.

### Final automated checks

| Command | Result |
| --- | --- |
| `cd frontend && npm run build` | Passed; 41 modules transformed. Run first so backend static-serving coverage is comparable. |
| `cd backend && uv run pytest --cov=catchup --cov-report=term -q --tb=short` | **634 passed**, **96%** statement coverage, **2,493/2,585** statements covered (92 missed); `api/extension.py` **95%** (136/143), `context/gather.py` **95%** (130/137), `main.py` **99%** (121/122). |
| `cd frontend && npm test -- --run` | **233 passed** in 14 files. |
| `cd extension && npm test -- --run` | **84 passed** in 8 files. |
| `cd extension && npm run build` | Passed: type check, Vite build, Readability and Apache license, both popup/options hashed CSS and JS, build-file check. |
| `docker build -t catchup:extension-fix-round1-local .` | Passed; image kept local. |
| `scripts/docker-smoke.sh catchup:extension-fix-round1-local` | Passed: loopback health, API/static responses, non-root process, saved preference, volume database and restart persistence. Throwaway resources cleaned by the script. |
| `openspec validate add-browser-extension --strict` | Passed. |

A separate local browser check opened the throwaway Docker image on loopback with a fresh browser profile, observed the exact first-run optional-extension lede and fully loaded Settings form, and reported **0 axe WCAG 2 A/AA violations**. A text-based wait for the numbered browser-extension heading timed out, but a fresh snapshot showed the heading and form; the subsequent axe audit and direct lede read both passed. The browser and container were closed. Real unpacked Chrome/Edge extension permissions, cross-world injection, and an actual X post in the user's logged-in browser were **not** exercised; the manual checks listed above still remain for review.

## Fix round 2 (D13, 2026-10-21)

Tasks 10.1–10.3 were completed in order. The invented short-post fixture has no `<article>` or `<main>` and places a sponsor banner above a short entry. Readability 0.6.0 returns the banner (275 trimmed characters) by default, but the entry (121 trimmed characters) at `charThreshold: 100`. Direct and serialized tests both **failed on unchanged code**, receiving “Support our imaginary daily notes” instead of “My tiny garden is ready.” After parsing a fresh clone with the shorter threshold, all **8 readable tests passed**. The named temporary mutation setting both 100-character checks back to 200 made **both new tests fail again with the banner**; reverting it left the readable, generic and popup suites at **60 passed**.

For 10.2, the two focused backend tests **both failed before the code change**: the stored candidate had only `url` and capped `alt` instead of the full `EntryImage` fields, and the summary request read `I1 — image, position 1;` rather than `I1 — in the post, position 1;`. Preserving the filtered image fields with a capped `alt` made **both pass**. No temporary mutation remains.

### Final automated checks

| Command | Result |
| --- | --- |
| `cd backend && uv run pytest --cov=catchup --cov-report=term` | **634 passed**, **96%** statement coverage (2,494/2,586 statements covered, 92 missed), with `frontend/dist` already built in fix round 1. Without it, 93 statements are missed. |
| `cd extension && npm test -- --run` | **86 passed** in 8 files. |
| `cd extension && npm run build` | Passed: TypeScript, Vite build (11 modules transformed), and packaged-file check. |
| `openspec validate add-browser-extension --strict` | Passed. |

Frontend was unchanged and not retested in this round. Docker build and smoke were **not run** in this round; Claude Code will run them in review. The real unpacked-extension and authenticated-X checks above remain unperformed.

### Claude Code's review of fix round 2

- **Reviews:** `/code-review` of `192da37..HEAD`, and a spec sub-agent that re-checked the delta. Neither found a defect in behavior.
- **The fixture, measured by the sub-agent:** Readability's default parse returns the banner (275 characters). At `charThreshold: 100` it returns the entry (121 characters). The paragraph has exactly two links.
- **Mutations on the changed lines:**

  | Mutation | Result |
  | --- | --- |
  | Second-parse trigger `< 500` → `< 0` | killed |
  | `charThreshold: 100` → `500` | killed |
  | Drop the `>= 100` check on the second result | survived, equivalent (see below) |
  | Final minimum `< 100` → `< 200` | killed |
  | Remove `article = shortArticle` | killed |
  | Store only `url` and `alt` for images | killed (both backend tests) |
  | Drop the alt's `[:500]` | killed |
  | Second parse on `document` instead of a clone | survived; killed after Claude's change below |

  - **Why the `>= 100` mutation is equivalent:** Readability's attempts at threshold 100 are a prefix of its default attempts. Its own length check uses whitespace-collapsed text, which is never longer than `textContent.trim()`.
  - **Claude's change:** the short-post test now also checks that the page's own document is unchanged. Under the clone mutation, both the direct and the serialized test fail on that check. Without the new check, all 8 readable tests pass.
- **Live checks:**
  - **The seven real pages from fix round 1,** saved locally from three sites: each gives its main text and links. The short note gives its 197-character body, with its two links and no sponsor text.
  - **A local instance:** a saved page with an image stores `origin: "html"`, `caption`, `width`, and `height`.
  - **Docker:** `docker build` and `scripts/docker-smoke.sh` passed.
  - **Re-run by Claude:** extension 86 tests and backend 634 tests.
- **Recorded, not fixed (D-023):**
  - **The length checks** count `textContent.trim()`, markup whitespace included, while Readability counts collapsed text. A fallback result padded past 500 characters by whitespace skips the second parse.
  - **The 10.1 note** "Without the inner `div`, Readability already returns the post" held for the planning probe's page, but not for this fixture.
  - **The 10.2 runner test** reads `model.calls[0]` as the summary call.
  - **Short pages** get a second Readability parse, only when the user clicks.


### Independent review before the manual check

A fresh sub-agent, the one that proposed the D-023 stop rules, reviewed the whole change (`c4b7251..751f972`) without the design discussion. Claude reproduced its findings.

- **Security: no defect.** Probes against the branch backend:
  - with a valid token, the digest, settings, run, token, and source-delete routes answer 403, and so do trailing-slash and `HEAD` variants of the extension routes;
  - an unknown `cu_` token gets 401;
  - a cross-origin preflight gets 405 with no CORS headers;
  - a lowercase `bearer` falls back to the cross-site rule.
- **Fix rounds:** round 1 held real defects, plan errors, and tests that could not fail. Round 2 held two real defects. Two items patched an earlier round:
  - saving images' fields undid round 1's narrowing of them;
  - round 2's second Readability parse tuned round 1's thresholds, rather than removing their cause.
- **Recorded, with the user's decision (2026-10-21), for a follow-up issue:**
  - **Sponsor text on short pages (a).** A 60-character note beside a 275-character banner saves only the banner. A 330-character post beside an indented, 380-character sponsor block saves the sponsor text first: the default parse counts 655 characters, so the second parse does not run.
    - Claude probed one rule: always take Readability's first, strict attempt (`charThreshold: 1`). It fixes these cases and keeps the seven real pages' text, but drops the release link from the release-note page's title.
    - A real fix needs one extractor in place of `readable.ts` and `generic.ts`, which share 39 near-identical lines, checked against a set of real pages. README lists the limit.
  - **Linked pages of saved pages (by design; now documented).** In the next run, the server requests up to `CATCHUP_LINKS_PER_ITEM` links recorded on a saved page, without cookies. README now says so, and warns against saving pages whose links carry private tokens. The README contract test checks both new sentences: it failed without the README change, and passed with it.
  - **Hidden text (a, low).** `generic.ts` has no visibility check, so it reads, for example, a `hidden` menu inside `<main>`.
