# Tasks

Implementer notes:
- **Read first.** Read `proposal.md`, `design.md` (all of "Context", D1–D7, and "Testing"), and the spec delta under `specs/browser-extension/`. If something looks wrong or contradictory, stop and report instead of redesigning.
- **Work test-first with the `tdd` skill** (D-016). For each group, first write its tests, run them, and watch them fail. Then change the code. The seams are named in each task, and they count as agreed:
  - `extractPage` from `extension/src/extract/page.ts`, run on `document` after `document.documentElement.innerHTML = …`, directly and serialized;
  - `chromeMock.scripting.executeScript`, `genericResult`, `captured`, `connect`, `response`, `fetchMock`, and `saves` in `extension/src/test/popup.test.ts`;
  - the README section read by `extension/src/test/docs.test.ts`.
- **Fixtures.** The six new fixtures are already committed in `extension/src/extract/fixtures/`, and each was checked to fail on main and to pass with the design's rule:
  - `release-note.html`;
  - `link-post.html`;
  - `blog-tiny-note.html`;
  - `blog-indented-sponsor.html`;
  - `hidden-main.html`;
  - `python-post.html`.

  Do not change any fixture.
- **Test rules.**
  - No real network.
  - **Two modes.** Every `extractPage` case runs in both modes, as the current extractor tests do: `direct`, and `serialized` with `new Function(\`return (${extractPage.toString()})()\`)()`.
  - **The page is not changed.** Every case also asserts that `document.body.outerHTML` is unchanged after the call.
  - **Readability.** Load the library with `window.eval(library)`, where `library` is `readFileSync(resolve('node_modules/@mozilla/readability/Readability.js'), 'utf8')`. Remove it in `afterEach` with `delete (window as …).Readability`, and clear `document.head` and `document.body`.
  - Change no existing test, except where a task says so.
  - **Mutations.** For each named mutation, apply it alone, run the named tests, record the result, and restore the code exactly. Compare with `git diff` after restoring.
- **Environment.** Use Node 22.17.1 with `export PATH="$HOME/.nvm/versions/node/v22.17.1/bin:$PATH"`. Then run `npm ci --offline --no-audit --no-fund` in `extension/`. It installs the locked packages from the local npm cache; if it fails, stop and report. Do not download packages, and do not change `package.json` or `package-lock.json`.
- **Out of scope:**
  - everything outside `extension/src/extract/`, `extension/src/popup.ts`, `extension/src/test/popup.test.ts`, `extension/src/test/docs.test.ts`, `README.md`, and the test report and AI usage log of task 4.1;
  - `extension/src/extract/x.ts` and its test;
  - the backend, the frontend, and dependency versions.
- **Do not edit** `proposal.md`, `design.md`, the spec delta, `docs/process/decision-log.md`, or `docs/process/requirements-changes.md`. Claude Code wrote D-034 and the requirements row with the plan.
- **Commits.** Commit after each task group. Do not push, tag, or open a PR.

## 1. One extractor (D1–D5)

- [x] 1.1 Write `extension/src/extract/page.test.ts`, importing `extractPage` from `./page`. Run it and watch it fail on the missing module. Use `REL = 'https://code.example/garden-tools/releases/1.2'`, and `fixture(name)` reading `src/extract/fixtures/${name}.html`.

  **With Readability loaded** (in `beforeEach`):
  - **P1 `saves a tiny note, not the longer sponsor banner beside it`** (`blog-tiny-note`): `content_text` is exactly `'My tiny garden is ready. Start with seeds today.'`, and `links` is exactly `[{ url: 'https://garden.example/seeds', text: 'Start with seeds' }]`.
  - **P2 `saves a post before an indented sponsor block`** (`blog-indented-sponsor`): `content_text` starts with `'Tiny gardens thrive'` and does not match `/Support our imaginary/`. `links` is exactly `[{ url: 'https://garden.example/log', text: 'keep a log' }]`.
  - **P3 `saves a short link post, not the sidebar`** (`link-post`): `content_text` contains `'The community garden fund drive. Please consider giving to the garden fund this year.'`, and does not match `/This is a link post|Monthly briefing|Sponsor me|Sponsored by|Recent articles/`. `links` is exactly `[{ url: 'https://fund.example/', text: 'The community garden fund drive' }]`.
  - **P4 `saves the release link from the title row first`** (`release-note`):
    - `links[0]` equals `{ url: REL, text: 'garden-tools 1.2' }`;
    - `content_text` starts with `'A bug fix release for garden-tools'` and does not match `/Sponsored by|Sponsor me|This is a beat|Recent articles|Monthly briefing/`;
    - no link URL matches `/ads\.example|sponsors\.example|\/tags\//`.
  - **P5 `saves the title row of a release note without a body`.** Load `release-note`, then remove `document.querySelector('.beat-note')` before recording `outerHTML` and running the extractor.
    - `links[0].url` is `REL`;
    - `content_text` contains `'garden-tools 1.2'`, and does not match `/This is a beat|Sponsor me|Sponsored by/`.
  - **P6 `leaves out hidden text and links with Readability`** (`hidden-main`):
    - `content_text` contains `'Water tiny gardens in the morning'` and `'Shown inside ghost'`;
    - it does not match `/Hidden menu|Collapsed block|Inline hidden|Ghost text|Ghost paragraph/`;
    - `links` is exactly `[{ url: 'https://garden.example/soil', text: 'the soil guide' }]`.
  - **P8 `reads the date from the article header`** (`python-post`): `published_at` is `'2026-11-10T00:00:00.000Z'`, and `title` is `'Garden tools 2.0 is now available | Garden Insider'`.
  - **P9 `does not put a title link to the page itself first`.** Set `document.documentElement.innerHTML` to:

    ```html
    <head><title>Small garden note</title><link rel="canonical" href="https://garden.example/2026/note"></head><body><div class="masthead"><h2><a href="https://garden.example/2026/note#top">Small garden note</a></h2></div><article><p>My tiny garden is ready, and the first seedlings came up this week after a long and rainy start to the season.</p><p>See <a href="https://garden.example/seeds">the seed list</a>.</p></article></body>
    ```

    `links` is exactly `[{ url: 'https://garden.example/seeds', text: 'the seed list' }]`.
  - **P10 `saves each link address once`.** Use:

    ```html
    <head><title>Notes</title></head><body><main><p>Read <a href="https://garden.example/a">the guide</a> and then <a href="https://garden.example/a">the guide again</a>, and <a href="https://garden.example/b">more</a>.</p></main></body>
    ```

    `links` is exactly `[{ url: 'https://garden.example/a', text: 'the guide' }, { url: 'https://garden.example/b', text: 'more' }]`.
  - **P11 `saves the image address the page loaded`.** Use:

    ```html
    <head><title>Pots</title></head><body><main><p>A pot on the windowsill.</p><img src="https://garden.example/small.png" alt="Pot"></main></body>
    ```

    Then `Object.defineProperty(document.querySelector('img')!, 'currentSrc', { value: 'https://garden.example/large.png' })`. `images` is exactly `[{ url: 'https://garden.example/large.png', alt: 'Pot' }]`.
  - **P12 `saves the short post instead of the longer sponsor banner`.** Copy this case from `readable.test.ts` (`blog-short-post`), with its assertions unchanged. Also assert `published_at` is `'2026-10-21'`.
  - **P13 `keeps only post text, links and images from a page without article`.** Copy this case from `readable.test.ts` (`blog-no-article`), with its assertions unchanged.
  - **P16 `reads a page without main text from its body, without navigation`.** Replaces `rejects short navigation-only pages`. Use the same page: head `<title>Navigation</title>`, body `<nav><a href="https://garden.example/">Home</a></nav><ul><li>2023</li><li>2024</li></ul>`. `content_text` is `'2023\n2024'`, and `links` is `[]`.
  - **P17 `matches the title without its site name, and skips a header link`.** Use:

    ```html
    <head><title>Small garden note | Field Notes</title></head><body><header><a href="https://garden.example/home">Small garden note</a></header><div class="masthead"><a href="https://notes.example/small">Small garden note</a></div><article><p>My tiny garden is ready, and the first seedlings came up this week after a long and rainy start to the season.</p><p>See <a href="https://garden.example/seeds">the seed list</a>.</p></article></body>
    ```

    `links` is exactly `[{ url: 'https://notes.example/small', text: 'Small garden note' }, { url: 'https://garden.example/seeds', text: 'the seed list' }]`.

  **Without Readability** (`delete window.Readability` before the call):
  - **P7 `leaves out hidden text and links without Readability`**: the same page and assertions as P6.
  - Copy the six cases of `generic.test.ts` here, with their assertions unchanged:
    - `reads article metadata, text, images and links without changing the page`;
    - `falls back to title, host and main text when metadata is absent`;
    - `limits content, images, links and rejects non-HTTP URLs`;
    - `reads a main region inside a form without its outside form ancestor excluding it`;
    - `excludes nav text, links and images strictly inside the selected root`;
    - `does not exclude the selected root even if it is a form`.

  Leave `readable.test.ts` and `generic.test.ts` as they are; task 2.2 deletes them. A test file with no tests fails the run.

  **With a stand-in Readability**, using `PLAIN`:

  ```html
  <head><title>Plain</title></head><body><nav><a href="https://garden.example/nav">Nav</a></nav><main><p>Start here.</p><p>Continue here.</p></main></body>
  ```

  - **P14 `falls back to the main region when Readability finds no text`.** First run `window.eval('window.Readability = class { parse() { return { content: "<p> </p>", textContent: " \\n ", title: "" } } }')`. `content_text` is `'Start here.\nContinue here.'`, and `links` is `[]`.
  - **P15 `falls back to the main region when Readability throws`.** First run `window.eval('window.Readability = class { parse() { throw new Error("broken") } }')`. The assertions are the same as P14.

  Verify: the file fails only because `./page` does not exist.
- [x] 1.2 Create `extension/src/extract/page.ts` as in design D1–D5.
  - Export `type CapturedPage`, the same shape as in `generic.ts`, and `extractPage(): CapturedPage`.
  - Start with the comment `// Passed directly to chrome.scripting.executeScript; keep all runtime dependencies inside.`
  - Type the Readability global locally, as `readable.ts` does, with the options `{ charThreshold: number; linkDensityModifier: number }`.
  - Use `Node.TEXT_NODE` for text nodes, and `getComputedStyle` on the live element for D2.
  - Do not change `readable.ts`, `generic.ts`, or `popup.ts` in this group.

  Verify:
  - `npx vitest run src/extract` passes in `extension/`;
  - mutations E1–E16 from design "Testing" each fail the cases named there (P1 tiny note, P2 indented sponsor, P3 link post, P4 release note, P5 bare release note, P6/P7 hidden, P8 date, P9 own-address title, P10 duplicates, P11 `currentSrc`, P14 empty result, P15 throws, P17 site-name title). Restore the code after each.

## 2. One popup chain, and the old extractors removed (D6)

- [x] 2.1 Change `extension/src/test/popup.test.ts`. Keep each test's name, unless a new name is given.
  - **`genericResult`** (lines 51-54): return `[{ result: page }]` for every `func` call, and `[]` for `files`.
  - **Injection order.** In these three tests, the expected order becomes `['readability.js', 'extractPage']`:
    - `injects the generic extractor and saves a checked page, then removes it`;
    - `still saves an X profile as a generic page when Add is chosen`;
    - `uses generic page extraction for a help.x.com URL that looks like a post`.
  - **`falls back to generic after the X extractor returns null`**, renamed `reads the page with readability.js and extractPage after the X extractor returns null`.
    - Replace the two `mockResolvedValueOnce` calls with a `mockImplementation` that answers:
      - `[{ result: null }]` for `func.name === 'extractX'`;
      - `[]` for `files`;
      - `[{ result: captured }]` for `extractPage`.
    - Expect the order `['extractX', 'readability.js', 'extractPage']`, where `files` calls map to `'readability.js'`. Exactly one save.
  - **`saves only reader-view post content on a page without an article element`.** The expected order becomes `['readability.js', 'extractPage']`.
  - **New, after that test: `saves only a tiny note, not the sponsor banner, through the popup`.** Copy that test's jsdom-tab setup, with `blog-tiny-note.html` and the tab URL `https://garden.example/note`.
    - The saved body's `text` is `'My tiny garden is ready. Start with seeds today.'`.
    - Its `links` is `[{ url: 'https://garden.example/seeds', text: 'Start with seeds' }]`.
    - The order is `['readability.js', 'extractPage']`, and the tab's `body.outerHTML` is unchanged.
  - **The `it.each` `falls back to generic after Readability returns null for %s`**, renamed `reads %s with readability.js and extractPage`. Use `genericResult(captured)` instead of its inline mock, and expect `['readability.js', 'extractPage']`.
  - **`falls back to generic when injecting readability.js rejects`**, renamed `still runs extractPage when injecting readability.js rejects`. Expect `['readability.js', 'extractPage']` and exactly one save.

  Verify: the changed and new tests fail on the current `popup.ts`, and all other popup tests still pass.
- [x] 2.2 Implement D6 in `extension/src/popup.ts`.
  - Import `extractPage` and `type CapturedPage` from `./extract/page`.
  - Run `extractX` only on an X post page, as now.
  - When `page` is `null`, or the page is not an X post: inject `files: ['readability.js']` inside its own `try`/`catch`, then run `func: extractPage` and use `injections[0]?.result`.
  - Delete `src/extract/readable.ts`, `src/extract/generic.ts`, `src/extract/readable.test.ts`, and `src/extract/generic.test.ts`. Their cases were copied to `page.test.ts` in task 1.1. `readable.test.ts`'s `returns null without an injected Readability global` is not kept: P7 and the six copied generic cases cover a page without Readability.

  Verify:
  - `grep -rn "extractReadable\|extractGeneric\|extract/readable\|extract/generic" extension/src` prints nothing;
  - `npx vitest run` passes in `extension/`;
  - mutations U1 and U2 from design "Testing" fail the tests named there. Restore the code after each.

## 3. README (D7)

- [x] 3.1 In `extension/src/test/docs.test.ts`, test `documents collection boundaries, reader license and the linked-pages wait`:
  - replace `'sponsor text'` in the list with `'only text the page shows'`;
  - after the loop, add `expect(extension).not.toContain('sponsor text')`.

  Verify: the test fails on the current README.
- [x] 3.2 In `README.md`, section "Browser extension":
  - remove the "Known limits" bullet that starts "On a short page beside a longer sponsor block", with both of its lines;
  - after the line ``license is bundled in `extension/dist/readability-LICENSE.md`.`` (in the same paragraph), add exactly these three lines, so that `only text the page shows` stays on one line:

    ```
    It saves only text the page shows, and takes the main text from
    Readability's strict first pass, so a short post is not replaced by a
    longer sponsor block or sidebar.
    ```

  Verify:
  - `git diff README.md` shows only these two changes;
  - `npx vitest run src/test/docs.test.ts` passes;
  - mutation R1 (restore the bullet) fails it.

## 4. Checks and report

- [x] 4.1 Run the full checks:
  - `npm test -- --run` and `npm run build` in `extension/`, with Node 22.17.1 (record the counts);
  - `DO_NOT_TRACK=1 openspec validate merge-extension-page-extractors --strict` (`openspec` comes from your existing `PATH`, not from the Node 22.17.1 folder).

  Do not run `docker build` or `scripts/docker-smoke.sh`: at `--auto medium` the smoke script is refused, and Claude Code runs both at review. The backend and frontend are not changed; do not run their checks.

  Write the commands and their real results to `docs/process/test-report-merge-extension-page-extractors.md`:
  - each new or changed test, and the mutations that it kills;
  - mutations E1–E16, U1, U2, and R1, with their results, and the recorded survivors X3, X5, and X8–X11 from design "Testing", listed as not tested;
  - the Docker smoke and the live checks from design "Testing", listed as not performed (Claude Code runs them at review).

  Add your entry to `docs/process/ai-usage-log.md` after the latest entry, with a faithful prompt excerpt. Leave out the session id; Claude Code adds it at review.

  Verify: every command that ran passes, and the report has the actual numbers.
