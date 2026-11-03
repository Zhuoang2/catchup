# Design

Lean change for issue #74. See `proposal.md` for the motivation, and the `user-interface` delta for the requirement.

## Context

- **Why the titles do not wrap.** Each affected title is a grid or flex item whose minimum width is its min-content width, which is its longest word:
  - `.item-title` sits in `.item`, a grid with one implicit `auto` column (`components.css:112`);
  - `.creator-item > a` sits in the `.creator-item` grid (`:130`);
  - `.entry-list a` is a flex item of `.entry-list li` (`:150`);
  - the popup's `h2` and `li` sit in the `#popup` and `section` grids (`popup.css:35`).

  `.check-title` (`:90`) and `.source-title` (`:137`) get their width from their row, and the word overflows the box.
- **What `overflow-wrap` does.** With `break-word`, a long word may break, but min-content sizes still count the whole word, so the grid and flex items above keep their width. With `anywhere`, min-content sizes count the break opportunities, so these items can shrink to their column. In both cases a line breaks inside a word only when no space fits.
- **Unbroken text comes from many places, not only titles.** For example:
  - a source's title falls back to the feed's host name (`backend/src/catchup/sources/feeds.py:360`);
  - a source check's error is the fetch error's message (`backend/src/catchup/collection.py:87`);
  - summaries are model text.

## Goals / Non-Goals

**Goals:**
- No screen scrolls horizontally at 320 px because of unbroken text, and the popup does not scroll horizontally at its 340 px width.
- No short label breaks inside a word because of the change.

**Non-Goals:**
- Truncating titles, or changing how titles are made.
- The extension's options page, and the standalone offline page.

## Decisions

### D1. `overflow-wrap: anywhere` on the roots
- **What.** Add `overflow-wrap: anywhere` to `.app` (`frontend/src/styles/base.css:4`), the element that wraps every screen (`frontend/src/components/AppShell.tsx:21`), and to the popup's `body` rule (`extension/src/popup.css:31`). Every element inherits it.
- **Why the roots.** The 320 px rule applies to every screen, and unbroken text reaches more elements than the six in #74 (see Context). One inherited value also covers elements added later.
- **The existing `overflow-wrap: anywhere` rules** (`components.css:122`, `:139`, `:148`, and `popup.css:36`) stay. They are redundant but harmless, and a test already pins `.source-feed` (`frontend/src/styles/tokens.test.ts:86-92`).
- **Alternatives:**
  - `overflow-wrap: anywhere` on the six selectors in #74 only. Rejected: host-name source titles in `.item-meta` and `.creator-source`, error messages in `.check-error`, and `.preview-title` would still widen the screen, and each new element would need its own rule.
  - `overflow-wrap: break-word` at the root. Rejected: it does not change min-content sizes, so the grid and flex items in Context would still overflow.
  - `word-break: break-all`. Rejected: it breaks ordinary words even when a space fits.

### D2. Two rows that put two texts on one flex line
- **The side effect.** Because `anywhere` lowers every element's min-content width, a short text that shares a non-wrapping flex line with a long one can now shrink below one of its words, and break inside it. A survey of every `display: flex` rule in `base.css`, `layout.css`, and `components.css`, against the markup, found two such rows. Every other row holds an icon and one text, items with `white-space: nowrap` (buttons, chips, navigation), or uses `flex-wrap: wrap`. `.key-saved` holds a text and a `<code>`, "Saved key ending in" and the last four characters, but it needs about 220 px of the 288 px column at 320 px, so it does not shrink.
- **The preview's entry date.** `.entry-list li` (`components.css:150`) holds the entry's title and its date, "3 Oct". At 320 px a long title takes most of the line. The date's share is then narrower than "Oct", so today it wraps at the space, and with `anywhere` it would break inside "Oct". → `.entry-list time` (`:151`) gets `flex: none`, so that the date keeps its one-line width, and the title wraps beside it.
- **The YouTube preview's method line.** `.preview-method` (`components.css:52`) holds the icon, the text "Caption fetching is off; videos will be listed without summaries", and the link "Change in Settings" (`frontend/src/pages/Sources.tsx:78-80`). The text and the link are separate flex items, so the link becomes a narrow column, and with `anywhere` it would break inside "Settings". → In `Sources.tsx`, wrap the text and the link in one `<span>`, as `.risk` and the X billing `.note` already do (`frontend/src/pages/Settings.tsx:301-303`, `:360`). The link then flows inline after the text.
- **Alternative:** `flex: none` on the link. Rejected: the link would stay on one line, and squeeze the text into a column of one or two words.

### D3. How it is tested
- **The repository's CSS tests read CSS text,** because jsdom has no layout (`frontend/src/styles/tokens.test.ts`, `extension/src/test/popup.test.ts:153-159`). The tests pin:
  - the root declarations;
  - that no owned rule turns wrapping back off for the title selectors in #74;
  - `flex: none` on the date;
  - the `<span>` in the method line, as a DOM check in `frontend/src/pages/Sources.test.tsx`.
- **The geometry** is checked in a browser at review (D-023's live check). At 320 px, replace the text of the first `.item-title a`, `.creator-item > a`, `.check-title`, `.source-title`, and `.entry-list a` with an 80-character string without spaces, and check that `document.documentElement.scrollWidth` is 320. Do the same in the popup at its 340 px width, with its `h2` and an entry `li`.

## Risks / Trade-offs

- **[Another flex row added later puts two texts on one line]** Its short text could break inside a word at narrow widths. → D2's pattern: give the short item `flex: none`, or wrap the texts in one inline element.
- **[A word now breaks where it used to overflow]** This is intended. Spaces are still used first, so only words wider than their column break.

## Migration Plan

- No data change. Rollback is a revert.
