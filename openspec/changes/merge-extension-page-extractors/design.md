# Design

## Context

See `proposal.md` ("Why") for the defects. The current code, on main `0fcb3f0`:

- **Popup chain.** `savePage` (`extension/src/popup.ts:207-250`):
  - on an X post page, it runs `extractX`;
  - on any other page, it injects `files: ['readability.js']` and then runs `extractReadable`. Either failure gives `null`.
  - When the result is `null`, it runs `extractGeneric`. This includes the case where `extractX` returned `null`; that path never injects `readability.js`.
  - The result then goes through `checkedCapture` (`popup.ts:82-111`), which caps the fields, and is posted to `/api/captures`.
- **`readable.ts`.**
  - It parses `document.cloneNode(true)` with Readability's defaults.
  - Under 500 characters, it parses a fresh clone with `charThreshold: 100`, and uses that result when it has at least 100 characters.
  - It returns `null` under 100 characters.
  - Otherwise, it walks `article.content`, parsed with `DOMParser`, and skips `nav,aside,footer,header,form,script,style,noscript` below the root.
- **`generic.ts`.** It walks the live `article`, `main`, `[role="main"]`, or `body` with the same walk and the same caps. It adds the `time[datetime]` fallback, and uses `og:title ?? document.title`, `currentSrc || src`, and `anchor.href`.
- **Readability 0.6.0** (`extension/node_modules/@mozilla/readability/Readability.js`):
  - **Attempts.** When an attempt's text is under `charThreshold` (default 500), it tries again with fewer flags: `STRIP_UNLIKELYS`, then `WEIGHT_CLASSES`, then `CLEAN_CONDITIONALLY`. In the end it returns the longest attempt (`:1546-1573`).
    - `STRIP_UNLIKELYS` removes elements whose class or id matches `sponsor`, `banner`, `sidebar`, `header`, `footer`, `menu`, `related`, `comment`, and similar (`:140`).
    - `WEIGHT_CLASSES` lowers the score of names like `meta`, `promo`, and `sidebar`.
    - So a short page's longer, looser attempt can be a sponsor banner or a sidebar.
  - **Link density.** `_cleanConditionally` removes a `div` with a weight under 25 whose link density is over `0.2 + linkDensityModifier` (`:2576-2590`). `linkDensityModifier` is a documented constructor option (`:66`).
  - **Visibility.** `_isProbablyVisible` (`:2694`) reads only `node.style`, `hidden`, and `aria-hidden`.
- **jsdom 26.1.0** (the test environment). Probed:
  - `getComputedStyle` reports `display: none` for `[hidden]`, a stylesheet rule, or an inline style. It reports this only on that element; its children do not report `none`. It computes `visibility` with inheritance.
  - A cloned document or a `DOMParser` document reports `display: block` for an element hidden by a stylesheet class. Computed style must therefore come from the live page.
  - jsdom has no `checkVisibility` and no `innerText`.

### Evidence

The user approved, on 2026-11-19, saving 11 real pages locally (1.27 MB) outside the repository. They come from three sites:
- simonwillison.net: a quote, a link post, a release note, a medium post, a long post, and the home page;
- terrytao.wordpress.com: two posts, one of them 709 KB with 1,009 formula images;
- blog.python.org: the home page and two posts.

Claude read each site's terms before downloading. The pages are deleted after this change merges. The probe scripts ran main's two extractors and the candidate of D2–D5 in jsdom, on four sets:
- the real pages;
- in-memory variants of them with shortened bodies;
- the invented cases from #62;
- the existing fixtures.

The results:

| Page | Main (`readable` → `generic`) | Candidate |
|---|---|---|
| 11 real pages | Main text right; release note loses its GitHub link; Python posts have no date | Same text; release link first; Python dates read; duplicate links merged |
| Quote with a 37-character body | Only the "Sponsored by" banner and its ad link | The note |
| Release note with an 80-character body, or none | The sidebar: "This is a beat by…", tag counts, "Sponsor me for $10/month" | The title row and note, release link first |
| Link post with a 100-character body | The sidebar and promo | The post and its link |
| 48-character note beside a 275-character banner | Only the banner | The note |
| 301-character post beside an indented banner | Sponsor text first | The post |
| Hidden menu, stylesheet-hidden block, and inline-hidden paragraph in `<main>` | All three read | None |

**Live check in the built-in browser.** The census ran at 1280 px on four live pages: Simon Willison's release note, the Tao lecture notes, and two Python posts. It only read the pages and changed nothing.
- On Simon Willison's release page, the stylesheets hide only the mobile date line.
- On the Tao lecture notes, the pass covers 2,702 elements in 24 ms. It hides only share buttons, the subscribe pop-ups, and comment-form parts.
- On a Python post, it hides only the logo for the other color theme.

## Goals / Non-Goals

**Goals:**
- One injected function, with one rule for each saved field, that never uses Readability's longest attempt.
- Text the page does not show is not saved, in every path.
- Tests use invented fixtures shaped like the real pages, each checked to fail on main and to pass with the candidate.

**Non-Goals:**
- Better extraction than Readability's on long pages: on all 11 real pages, the text is unchanged.
- Reading shadow DOM, frames, or closed `<details>` content differently from today.
- Detecting text hidden by `opacity`, clipping, or off-screen positioning (screen-reader-only text stays).
- Any server change.

## Decisions

### D1. One injected function, `extractPage()`

`extension/src/extract/page.ts` exports `extractPage()` and the `CapturedPage` type, which moves from `generic.ts`. `readable.ts`, `generic.ts`, and their tests are removed.

Like the functions it replaces, `extractPage()` keeps every dependency inside its body. Chrome serializes it into the tab, and the tests run it both directly and through `new Function(...)`. It reads Readability from `globalThis.Readability` when `readability.js` was injected into the same isolated world.

- **Alternative: keep two files that share a helper module.** Rejected: an injected function cannot import, so the shared code would still be duplicated at build time, and the popup would keep two calls.

### D2. A visible copy of the page

`extractPage()` first makes `shown = document.cloneNode(true)`. It then walks `document.body` and `shown.body` in step: child `i` of a live element corresponds to child `i` of its copy. Elements are only collected during the walk and removed after it, so the pairing holds; text nodes, which are not in `children`, may be removed during the walk. For each live element:

- `script`, `style`, `template`, and `noscript` are skipped: they are not checked and not descended into;
- when `getComputedStyle(live).display` is `none`, the copy is removed with its subtree;
- when `visibility` is `hidden` or `collapse`:
  - an element with no element children is removed;
  - otherwise, only its own text nodes are removed, and the walk continues into its children. A child may set `visibility: visible` again;
- for a live `img` with a non-empty `currentSrc`, the copy's `src` attribute is set to `currentSrc`, which is the address the page actually loaded.

The copy's `<head>` is not changed, so Readability still reads JSON-LD and meta tags. The live page is never changed.

- **Why a copy.** Readability changes the document it parses, and the fallback root must not include hidden text either. A clone has no layout, so the computed style is read from the live element.
- **Alternative: `checkVisibility()`.** Rejected: jsdom does not have it, so the tests could not run the real code path.
- **Alternative: rely on Readability's own visibility check.** Rejected: it misses stylesheet rules and `visibility`, and the fallback root has no check at all.

### D3. Main text: Readability's strict first attempt, then the page's main region

- **Readability.** When `globalThis.Readability` exists, `extractPage()` parses `shown.cloneNode(true)` with `{ charThreshold: 1, linkDensityModifier: 0.3 }` inside `try`/`catch`.
  - With `charThreshold: 1`, the first attempt wins whenever it has any text. All flags are on in that attempt, so blocks named like sponsors, banners, sidebars, and comments have already been removed.
  - With `linkDensityModifier: 0.3`, `_cleanConditionally` (for `div`, `section`, `ul`, `table`, `form`, and `fieldset`) raises its link-density limit from 0.2 to 0.5 for a block with a weight under 25, and from 0.5 to 0.8 otherwise.
- **The root.** When the parse returns `content`, and `textContent` holds a non-space character, the root is `content` parsed with `DOMParser`. Otherwise (no Readability, an exception, `null`, or empty text), the root is the visible copy's `article`, `main`, or `[role="main"]`, else its `body`.

Probe on the 11 real pages and the 5 in-memory variants (characters and links of the strict first attempt):

| Page | Modifier 0 | 0.3 | 0.5 |
|---|---|---|---|
| Real pages | same | same | same |
| Home page | 248 links | 263 links | 263 links |
| Link post with a 100-character body | 30 characters, the date only | 132, the post | 132 |
| Release note with no body | 18, the date only | 90, the title row | 90 |

0.3 is the smallest of the tested values that keeps both. On every page tested, it adds no sponsor or sidebar text.

- **Alternative: keep the default parse and a second, looser parse (today).** Rejected: that is the cause of the defect.
- **Alternative: strict without the modifier**, as probed in #62. Rejected: short link posts and bare release notes lose their body.
- **Alternative: the page's main region only.** Rejected: simonwillison.net has no `article` or `main`, so its `body` includes the sponsor banner, the sidebar, and the footer.

### D4. One walk, and one rule for each field

- **Walk.** The text walk is the one shared today:
  - a new line between blocks;
  - a space between inline pieces, except before `.,!?;:)]`;
  - `nav,aside,footer,header,form,script,style,noscript` skipped below the root, but never the root itself;
  - caps of 16,000 characters, 8 images, and 50 links.
- **Addresses.** An image address is the element's `src` attribute (D2 has already put `currentSrc` there); its alt is the `alt` attribute, cut to 500 characters. A link address is its `href` attribute. Each is resolved against `document.baseURI` and kept only for `http:` and `https:`. Each link address is saved once, with the text of its first occurrence.
- **Metadata.** For each field, the first non-empty value is used:
  - `url`: `link[rel~=canonical]`, `og:url`, `location.href`, each kept only when it is `http(s)`;
  - `title`: `article.title`, `og:title`, `document.title`;
  - `site_name`: `article.siteName`, `og:site_name`, `location.hostname`;
  - `author`: `article.byline`, `meta[name="author"]`, `article:author`;
  - `published_at`: `article.publishedTime`, `article:published_time`, the first `time[datetime]` in the root, the first `time[datetime]` in the fallback region (the first of the visible copy's `article`, `main`, and `[role="main"]` that exists), else `null`. The last step is not taken from `body`, where a sidebar's dates would match. On the real Python posts, Readability leaves the `<header>` that holds the date out of its content, so only the last step finds it.

### D5. The title link

The rule:
- **Title forms.** `t` is the saved title, with whitespace collapsed and in lower case. The wanted texts are:
  - `t`;
  - `t` after its first `": "`;
  - `t` before its last `" | "`, `" - "`, `" – "`, `" — "`, or `" · "`;
  - `t` with both cuts.
- **The link.** The extractor takes the first link in the visible copy's `body` that meets all of these:
  - it is not inside `nav`, `aside`, `footer`, `header`, or `form`;
  - its address is `http(s)`, and, with the fragment removed from all three, it is neither `location.href` nor the saved `url`;
  - its collapsed, lower-case text is one of the wanted texts.
- **Saving.** That link is saved first, and the root's links follow.

Findings on the real pages:
- On the release note, `"Release: llm 0.37.3"` matches the link `llm 0.37.3`. The link before it, the label `Release`, does not match.
- On link posts, the match is the linked article, which Readability already kept.
- On a Tao post, the match is the page itself, which is skipped.
- On the other pages, no link matches.

- **Why equality.** A containment rule ("the link text is inside the title") matched the label `Release`, which comes first. A length ratio fails for short names, such as `x 1.0`.
- **Alternative: map Readability's chosen block back to the page and add its sibling rows.** Rejected: it depends on Readability's internal choice of block and needs more code.
- **Alternative: accept the loss.** Rejected: #62's "Done when" requires the release link.

### D6. One chain in the popup

```
page = null
if xPost: page = result of extractX   (no injection result → unreadable, as today)
if page === null:
  try inject readability.js; on failure continue
  page = result of extractPage
```

The only behavior change in this chain is that an X page whose structure does not match now gets `readability.js` before `extractPage`, like every other page. The X requirement's "read it as a general page" now means the same reading as on any other page. A rejection from `extractPage`'s own injection still reaches the existing `catch`, which reports "This page can't be read by extensions."

### D7. README and its contract test

- **README.** In the "Browser extension" section:
  - the "Known limits" bullet "On a short page beside a longer sponsor block, …" is removed;
  - after the sentence about Mozilla Readability, this sentence is added: "It saves only text the page shows, and takes the main text from Readability's strict first pass, so a short post is not replaced by a longer sponsor block or sidebar."
- **Contract test.** `extension/src/test/docs.test.ts` stops requiring `'sponsor text'`. It requires `'only text the page shows'` instead, and checks that the section no longer contains `'sponsor text'`.

## Risks / Trade-offs

- **Visibility follows the window.** Media queries decide what is hidden, so a narrow window can save a mobile-only line, such as Simon Willison's date. This is what the user sees. → Accepted.
- **Without Readability, the fallback can include sponsor blocks.** The fallback reads the whole `body` when the page has no `article` or `main`. This happens only when `readability.js` cannot be injected but a function can, or when Readability finds no text. → Accepted; it is no worse than `generic.ts` today.
- **A post that is mostly links** loses blocks whose link density passes the raised limit. → The title link still saves the main link; the remaining cases are recorded.
- **A title-text false positive.** A link outside the excluded regions, whose text equals the title and which points elsewhere, is saved first. → Rare. It changes only the order and adds at most one link.
- **Performance.** The pass reads one computed style per element: 24 ms for 2,702 elements on the heaviest real page. It runs only on Add.
- **Text that stays.** Closed `<details>` content, `opacity: 0`, and clipped screen-reader text are still read, as today.

## Testing

Test-first (D-016). Seams:

- **`extractPage` in `extension/src/extract/page.test.ts`.**
  - Every case runs twice, directly and serialized: `new Function(\`return (${extractPage.toString()})()\`)()`, as the current tests do.
  - The page is set with `document.documentElement.innerHTML = fixture`, and Readability with `window.eval(library)`; it is deleted in `afterEach`.
  - Every case asserts that `document.body.outerHTML` is unchanged.
- **Fixtures** in `extension/src/extract/fixtures/`, committed with the plan. Each was checked to fail on main and to pass with the candidate:
  - `release-note.html`: Simon Willison's release layout. A sponsor banner, a title row with a label link and the title link, a note body with code blocks and the `blogmark-body` class, recent articles, a sidebar with tags and a "Sponsor me" promo, and a footer.
  - `link-post.html`: a short link post. Its link density is about 0.36, so strict Readability without the modifier drops it. The page also has the sidebar and promo, and a canonical address.
  - `blog-tiny-note.html`: case A from #62.
  - `blog-indented-sponsor.html`: case B from #62.
  - `hidden-main.html`: `hidden`, a stylesheet `display: none` block, an inline `display: none` paragraph, `visibility: hidden` with a visible child, and visible text.
  - `python-post.html`: a blog.python.org-style `article > header > time`, with the body in a sibling `div`.
- **Popup:** `chromeMock.scripting.executeScript` call order and `saves()` in `extension/src/test/popup.test.ts`, including the jsdom tab test that runs the real Readability.
- **README:** `extension/src/test/docs.test.ts`.

Named mutations. Each was applied alone to the probe candidate, and it fails the listed planned tests (tasks 1.1, 1.2). The test ids are those of task 1.1.

| Id | Mutation in `page.ts` | Must fail |
|---|---|---|
| E1 | Readability without `charThreshold: 1` | tiny note, indented sponsor, link post, bare release note |
| E2 | `linkDensityModifier: 0` | link post, bare release note |
| E3 | the visible copy is a plain clone (no walk) | hidden (with and without Readability), `currentSrc` |
| E4 | no `visibility` step | hidden (both) |
| E5 | a `visibility: hidden` element is removed with its children | hidden (both): "Shown inside ghost" is missing |
| E6 | no title-link step | release note, bare release note |
| E7 | the title link may be the page's own address | own-address title |
| E8 | title match by containment (`t.includes(text)`, length ≥ 3) | release note, bare release note (the label `Release` comes first) |
| E9 | Readability parses `shown` itself instead of a clone | bare release note |
| E10 | no `published_at` step for the page's `article`/`main` | Python-style date |
| E11 | links not de-duplicated | duplicate links, link post |
| E12 | `currentSrc` not copied | `currentSrc` |
| E13 | Readability's content used even when its text is empty | empty Readability result |
| E14 | no `try`/`catch` around the parse | Readability that throws |
| U1 | popup: the X fallback runs `extractPage` without injecting `readability.js` | X fallback order |
| U2 | popup: a `readability.js` injection failure is not caught | injection failure still saves |
| E15 | the title link may be inside `nav`, `aside`, `footer`, `header`, or `form` | site-name title (P17) |
| E16 | no trailing-site-name title form | site-name title (P17) |
| R1 | README keeps the sponsor bullet | docs contract test |

Recorded survivors (D-023), found by the fresh-eyes check; no test is planned for them:
- **X3, no skip of `script`, `style`, `template`, `noscript`.** In jsdom, `script` computes to `display: none`, so JSON-LD inside `body` would be dropped from the copy. No fixture has JSON-LD in `body`.
- **X5, the date taken from `body` instead of the fallback region.** On a minimal page, Readability's own content pulled a sibling's `<time>` into the root, so no valid test separates the two.
- **X8, `collapse` not handled.** It applies only to table rows and columns.
- **X9, `og:title` before `article.title`.** Readability takes `og:title` into `article.title` itself.
- **X10, `location.href` instead of `document.baseURI`.** The two differ only with a `<base>` element.
- **X11, the fallback region preferred whenever it exists.** The fixtures with an `article` or `main` give the same result either way.

At review, Claude Code runs:
- `scripts/docker-smoke.sh`;
- the built `extractPage` from the branch, in jsdom, on the 11 saved real pages and their variants, compared with this design's Evidence table;
- the visibility census in the built-in browser, on the same four live pages.

The user may also load the built extension in Chrome and save two real pages: a short Simon Willison post, and a Tao or Python post.
