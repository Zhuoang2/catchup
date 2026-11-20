# Proposal

## Why

The browser extension reads an ordinary page with two injected functions, `extension/src/extract/readable.ts` (Mozilla Readability 0.6.0) and `extension/src/extract/generic.ts` (the fallback). An independent review before #58 merged found that the pair saves sponsor text on short pages, and that two fix rounds only tuned thresholds (#62). Probes on main `0fcb3f0` reproduce the defects. The probes used invented pages, and in-memory variants of real pages saved locally and not committed (design, "Evidence"):

- **Short pages save the sponsor block or the sidebar instead of the post.** Readability returns its longest attempt when no attempt reaches 500 characters. `readable.ts:10-14` re-parses at 100 characters, which has the same effect. On simonwillison.net's page layout:
  - a 37-character note saves only the 159-character "Sponsored by" banner and its ad link;
  - a short release note and a short link post save the sidebar ("This is a beat by…", tag counts, and the "Sponsor me for $10/month" promo) instead of the post.

  The invented cases from #62 fail in the same way. A 48-character note beside a 275-character banner saves only the banner. A 301-character post beside an indented banner saves the sponsor text first.
- **A release note loses the link in its title.** On the real "Release: llm 0.37.3" page, the link to the GitHub release is not saved. Readability's chosen block is the note body. The title row beside it is not merged, whatever the page length or flags.
- **Hidden text is read.** `generic.ts` has no visibility check, so it saves a `hidden` menu, a stylesheet-hidden block, and an inline-hidden paragraph inside `<main>`. Readability checks only inline styles and the `hidden` and `aria-hidden` attributes, so text hidden by a stylesheet reaches it too.
- **The two files have drifted.** They share 39 near-identical lines that differ in three places:
  - the image address fallback;
  - title precedence;
  - the `time[datetime]` date fallback, which only `generic.ts` has. On the real blog.python.org posts, the saved page has no date, although the page shows one in `<time datetime>`.

## What Changes

- **One extractor.** A single injected function, `extractPage()` in `extension/src/extract/page.ts`, replaces `readable.ts` and `generic.ts`.
- **Only what the page shows.** The extractor works on a copy of the page without elements the browser does not show: elements whose computed `display` is `none` (including `hidden` and stylesheet rules), and text whose computed `visibility` is `hidden` or `collapse`. The page itself is never changed.
- **The main text comes from Readability's first, strict attempt** (`charThreshold: 1`). It raises Readability's link-density limit (`linkDensityModifier: 0.3`), so a short post with a link in its title is kept. If Readability is missing, fails, or finds no text, the extractor reads the page's `article`, `main`, `[role="main"]`, or `body` instead. It never uses Readability's longest attempt.
- **The title link is kept.** When a link outside navigation, headers, footers, asides, and forms has the page's title as its text, and points to another page, it is saved first. The title can also match without a leading "Label:" or a trailing site name.
- **Each link address is saved once.**
- **The publication time** falls back to a `time[datetime]` element in the main text, then in the page's `article`, `main`, or `[role="main"]`.
- **One fallback chain in the popup.** An X post page uses `extractX`. Any other page, and an X page whose structure does not match, gets `readability.js` and then `extractPage`. If `readability.js` cannot be injected, `extractPage` still runs.
- **README.** The "Known limits" entry about sponsor text is removed. The extension section says that text the page hides is not saved.
- No change to the server, the API, the data model, the caps (16,000 characters, 8 images, 50 links), or the Readability version.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `browser-extension`: "Add the current page to the next digest" now states:
  - what is read: only what the page shows, and the main text from Readability's strict first attempt, with no longest-attempt fallback;
  - the title link, and each link saved once;
  - the date fallback.

  The requirement gains scenarios for:
  - a short note beside a sponsor banner;
  - a short post beside a longer sidebar;
  - a release note whose title links to the release;
  - hidden text;
  - a page Readability cannot read.

## Impact

- Code:
  - `extension/src/extract/page.ts` (new);
  - `extension/src/extract/readable.ts` and `extension/src/extract/generic.ts` (removed; the `CapturedPage` type moves to `page.ts`);
  - `extension/src/popup.ts`.
- Tests:
  - `extension/src/extract/page.test.ts` (new; it keeps the cases of `readable.test.ts` and `generic.test.ts`, which are removed);
  - new invented fixtures in `extension/src/extract/fixtures/`;
  - `extension/src/test/popup.test.ts`, for the injection order;
  - `extension/src/test/docs.test.ts`.
- Docs:
  - `README.md`;
  - the decision log (D-034);
  - the requirements-changes table;
  - a test report;
  - the AI usage log.
- Out of scope:
  - formula and tiny images, and captions (#65);
  - X extraction (`extractX`);
  - content in shadow DOM or frames;
  - closed `<details>` sections;
  - text hidden by opacity, clipping, or off-screen positioning;
  - server-side cleanup of saved text.
