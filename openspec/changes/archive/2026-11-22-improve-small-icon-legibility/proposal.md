# Proposal

## Why

The CatchUp icon blurs in a browser tab (#43, part 2, found in the review of #37). Its two bars are 38 units high on a 1024-unit canvas (`frontend/public/icon.svg:1`), which is about 0.6 px at 16 px. The dark square's edges also fall between pixels (2.56 px and 13.44 px). Rendered at 16 px in Chrome, the icon mixes 12 colors and the bars show as a gray smear. Part 1 of #43, the offline page's icon, was done in PR #53.

## What Changes

- **The mark is redrawn on a 16 × 16 grid** (design D1, option A, chosen by the user on 2026-11-22). Every edge lands on a whole pixel at 16 px and at 32 px:
  - the dark square goes from 2 px to 14 px at 16 px (now 2.56 px to 13.44 px);
  - each bar is 1 px high at 16 px (now about 0.6 px), from 5 px to 11 px across, with 2 px of the mark between the bars.
- **All icon files are redrawn from the same rule** by `frontend/scripts/make-icons.py`: `icon.svg`, `icon-192.png`, `icon-512.png`, `icon-1024.png`, and the maskable icon, which keeps its safe-zone box. The offline page's inline copy of `icon.svg` is updated to match.
- **The browser extension's toolbar icon gets the same fix without an extension change.** Its build copies `frontend/public/icon-192.png`, and 192 px is 12 × 16 px, so the file averages cleanly to 16 px and 32 px. Whether the toolbar's own scaling keeps the bars sharp was not checked; Chrome's `<img>` scaling still blends them.
- **No new files or `<link>` tags.** Chrome keeps using the SVG for the tab, so the declarations in `index.html` and the manifest stay as they are.
- **Other options the user did not choose (design D1):**
  - B: redraw only `icon.svg`, the tab icon, and keep the app icons as they are;
  - C: a bolder small mark, with 2 px bars at 16 px.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `local-deployment`, "Installable as an app": the tab icon stays legible at 16 px. At 16 × 16 and 32 × 32 pixels it uses only the mark's two colors, and its bars are separate lines of whole pixels. New scenario "Icon at 16 px".

## Impact

- `frontend/scripts/make-icons.py`: the drawing rule for the PNGs and the SVG text.
- `frontend/public/icon.svg`, `icon-192.png`, `icon-512.png`, `icon-1024.png`, `icon-maskable-512.png`: regenerated.
- `frontend/public/offline.html`: the inline `data:` icon.
- `frontend/src/install.test.ts`: two new tests. Existing tests do not change.
- Installed apps and the Safari touch icon show the redrawn mark once the browser updates them.
- No backend, API, manifest, `index.html`, service worker, or extension source change.
