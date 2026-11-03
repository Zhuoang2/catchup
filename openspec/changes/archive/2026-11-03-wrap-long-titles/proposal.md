# Proposal

## Why

A title with no break points widens the page at 320 px (#74, found in the system review of `add-x-accounts` on 2026-11-01). The page's `scrollWidth` was 373. An X post whose text starts with a long address is one such title, because an X item's title is the post's first 80 characters. The `user-interface` spec forbids horizontal scrolling at 320 px ("One grid for masthead, navigation, and content").

These elements are affected:
- **Digest:** `.item-title` (`frontend/src/styles/components.css:114`) and `.creator-item > a` (`:115`).
- **Home, a run's source checks:** `.check-title` (`:90`).
- **Sources:** `.source-title` (`:137`) and the preview's `.entry-list a` (`:149-151`).
- **The extension popup:** its `h2` heading (`extension/src/popup.css:34`), which shows the tab's or the preview's title (`extension/src/popup.ts:185`, `:267`). The preview's entry titles in `#popup li` are affected in the same way.

Only four rules wrap such text today: `.also-read`, `.source-feed`, and `.preview-urls dd` (`components.css:122`, `:139`, `:148`), and the popup's `#popup p` (`popup.css:36`).

## What Changes

- **Wrap at the root.** `overflow-wrap: anywhere` is set on the app's root, `.app` (`frontend/src/styles/base.css:4`), and on the popup's `body` (`extension/src/popup.css:31`). Every element inherits it. `anywhere` is needed, not `break-word`, because only `anywhere` lets a grid or flex item shrink below its longest word (`design.md`, D1).
- **Keep short texts whole in the two rows that put two texts on one flex line** (`design.md`, D2). Without this, root wrapping would let the shorter text break inside a word:
  - `.entry-list time` (`components.css:151`) gets `flex: none`, so that the date beside a long entry title stays on one line;
  - in the source preview's method line (`frontend/src/pages/Sources.tsx:78-80`), the text and the "Change in Settings" link are wrapped in one `<span>`, as `.risk` already does in Settings, so that the link flows after the text.
- **Wrapping still prefers spaces.** A line breaks inside a word only when that word alone does not fit, so ordinary titles look as before.
- **Out of scope:**
  - the options page of the extension, which is a normal tab at most 34 rem wide;
  - the standalone offline page, which has its own CSS;
  - truncating or shortening titles.

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- `user-interface`, "One grid for masthead, navigation, and content": text without break points MUST wrap inside its column. A new scenario covers a long unbroken title at 320 px.

`browser-extension` has no layout requirement for the popup, so it does not change. The popup's fix follows the same rule, and a CSS test pins it.

## Impact

- **Frontend:** `frontend/src/styles/base.css`, `frontend/src/styles/components.css`, and `frontend/src/pages/Sources.tsx`; tests in `frontend/src/styles/tokens.test.ts` and `frontend/src/pages/Sources.test.tsx`.
- **Extension:** `extension/src/popup.css`, and a test in `extension/src/test/popup.test.ts`.
- **Docs:** in `docs/process/`, a test report, a requirements-changes row, and AI usage log entries.
- **Not changed:** the backend, the API, the data, and how titles are made.
