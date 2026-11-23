# Design

Status: **the user chose option A of D1 on 2026-11-22.** The specs and tasks are written for it. D1 still lists options B and C as the alternatives considered.

## Context

See `proposal.md` for why. The current state, at `main` 795c5e7:

- **One artwork, one script.** `frontend/scripts/make-icons.py` draws the C7 mark: a dark square with two light bars.
  - The PNGs come from `pixel()` (`make-icons.py:18-32`): the square starts at 16% of the size (21% for the maskable icon), and the bars are `int(width * .055)` high.
  - The SVG is written as text (`make-icons.py:54-60`): a square from 164 to 860, and bars `M324 430h376M324 562h376` with `stroke-width="38"`, on a 1024 canvas (`frontend/public/icon.svg:1`).
  - `install.test.ts:52-62` regenerates every icon in a temporary directory and requires the committed files to be byte-identical.
- **Where each file is used.**
  - The tab: `index.html:8-9` declares `/icon.svg` (`image/svg+xml`, no `sizes`) and then `/icon-192.png` (`sizes="192x192"`). `install.test.ts:19-31` checks both.
  - The app: `manifest.webmanifest:9-14` lists the 192, 512, maskable 512, and 1024 px PNGs. `index.html:7` uses `icon-1024.png` as the `apple-touch-icon`. `install.test.ts:33-50` checks them.
  - The offline page: `offline.html:7` declares the same SVG inline, as a percent-encoded `data:` URL. `install.test.ts:79-101` requires the decoded SVG to equal `public/icon.svg`, with fills `#f4f0e6` and `#151412`.
  - The browser extension: its build copies `frontend/public/icon-192.png` (`extension/vite.config.ts:14-20`), and its manifest declares only that size (`extension/public/manifest.json:10`, checked by `extension/src/test/manifest.test.ts:15`). Chrome scales it down for the toolbar.
- **What the blur is.** At 16 px the bars are about 0.6 px high, and the square's edges fall at 2.56 px and 13.44 px. Rendered as a 16 px image in headless Chrome 157, the icon has 12 distinct colors. Scaled from 192 px to 16 px (box filter, as an estimate of the toolbar), it has 6. The bars show as gray lines.
- **How Chrome chooses the tab icon.** Read from Chromium's source, not tested in a real tab:
  - Each `<link rel="icon">` gets a score. A candidate with `sizes="any"` or with no `sizes` scores 1.0 on desktop. A candidate with sizes scores by how close they are to 16 px times the screen's scale factors (`components/favicon/core/favicon_handler.cc:88-104`, `:134-154`).
  - The candidates are sorted by score with a stable sort, so equal scores keep the page's order (`:477-478`). After a download, the next candidate is tried only if its score is higher than the best so far (`:262-281`).
  - So Chrome takes `/icon.svg`. A sized PNG added next to it would not change the tab, unless the SVG declaration were removed.
  - The HTML standard leaves the choice to the browser. It uses the last one among equally appropriate icons, and `sizes` cannot say that one file is for small high-resolution icons (https://html.spec.whatwg.org/multipage/links.html#rel-icon).
  - Firefox and Safari were not checked.
- **Stored tab icons.** Chrome keeps a page's stored icon when the icon URL is unchanged and the stored data is not out of date (`favicon_handler.cc:510-522`). Any reload of the page marks it out of date (`components/favicon/content/content_favicon_driver.cc:225-241`). An icon redrawn at the same URL shows after the user reloads CatchUp once.

## Goals / Non-Goals

**Goals:**

- At 16 × 16 and 32 × 32 pixels, the tab icon uses only the two mark colors, and each bar is a line of whole pixels.
- One drawing rule for every icon file, kept in `make-icons.py`.

**Non-Goals:**

- New icon sizes or declarations: `favicon.ico`, 16 px or 32 px PNG files, extension icons at 16/32/48/128 px.
- The maskable icon's box. Its square's corners are about 41% of the size from the center, a little outside the 40% safe circle. This is unchanged here.
- New colors, or a different mark.
- Firefox- or Safari-specific handling.

## Decisions

### D1. The small-size artwork (the user chose A)

Three options were rendered in headless Chrome at 16 px and 32 px, on 1x and 2x screens. Each was shown on a white tab, a light tab strip, and a dark tab.

- **A. Redraw the one mark on a 16 × 16 grid (recommended).**
  - At 16 px: the square goes from 2 px to 14 px. The bars are rows 6 and 9, from 5 px to 11 px across. The mark is between and around them.
  - Every icon file follows: the SVG, the 192, 512, and 1024 px PNGs, and the maskable icon with its own box. 192, 512, and 1024 are all multiples of 16, so each PNG scales to 16 px and 32 px without blur.
  - The rendered 16 px image has exactly 2 colors and matches the pattern in "Testing".
  - At large sizes, the bars are thicker (64/1024 instead of 38/1024) and the square is a little larger (75% of the size instead of 68%).
  - The extension's toolbar icon uses the same 192 px file. Averaged over 16 × 16 equal blocks, that file has 2 colors. A browser that scales it with another filter still blends the bars: Chrome 157 drawing it in `<img width=16>` gave 7 colors, as it does for today's file. How the toolbar scales it was not checked.
- **B. Redraw only the tab SVG.**
  - `icon.svg`, and the offline page's copy of it, get A's geometry. The PNGs keep the current drawing.
  - The tab looks like A. The installed app and Safari icons do not change.
  - The extension toolbar icon stays blurred, and the tab icon and the app icon differ slightly.
  - Changes against A: no `pixel()` change; the PNG test in task 1.1 is left out; the spec drops its sentence about the PNG icons.
- **C. A bolder small mark.**
  - At 16 px: the square goes from 1 px to 15 px, and the bars are two rows high (rows 5–6 and 9–10), from 4 px to 12 px across. SVG: square from 64 to 960, bars `M256 384h512M256 640h512` with `stroke-width="128"`.
  - It is the easiest to read in a tab, but it is heavier than the C7 prototype's thin rules, and the light margin on a dark tab is 1 px.
  - It can apply to every file as in A, or to the SVG only as in B.
  - Changes against A: the geometry in D2, the pattern in "Testing", and the spec's "one pixel high" becomes "two pixels high".

A is recommended. It fixes the tab, the offline page, and the extension's toolbar icon with one rule, and it adds no files or declarations. It keeps the C7 look at large sizes.

### D2. Geometry and drawing for option A

- **SVG** (`make-icons.py` writes it; same structure as now, so the offline test's fill list stays `#f4f0e6`, `#151412`):

  ```
  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1024 1024"><rect width="1024" height="1024" fill="#f4f0e6"/><rect x="128" y="128" width="768" height="768" fill="#151412"/><path d="M320 416h384M320 608h384" stroke="#f4f0e6" stroke-width="64"/></svg>
  ```

  Each bar is a 64-unit stroke centered on y = 416 and y = 608. So the bars cover 384–448 and 576–640, and run from 320 to 704 with butt caps. Every edge is a multiple of 64, which is one pixel at 16 px.
- **PNGs** (`pixel()`): the square starts at `int(size * 0.125)` (`0.21` for the maskable icon, unchanged). With `unit = (right - left) / 12`, the bars run from `left + int(3 * unit)` to `left + int(9 * unit)`, start at `top + int(4 * unit)` and `top + int(7 * unit)`, and are `int(unit)` high. At 192, 512, and 1024 px the unit is a whole number (12, 32, 64), so every edge is on the 16 × 16 grid.
- **Offline page:** `offline.html:7` gets the new SVG, percent-encoded, in the same `data:image/svg+xml,` form.
- **Alternatives:**
  - **Hand-drawn PNGs.** Rejected: they would leave the reproducible script.
  - **A filled path for the bars.** Rejected: it adds a third fill, so the existing offline test would change.

### D3. Keep the icon declarations as they are

- No new `<link>` tags, and no change to `index.html`, the manifest, or the extension manifest. The redrawn files keep their URLs.
- **Alternatives:**
  - **Add a 32 px PNG with `sizes="32x32"`.** Rejected: Chrome keeps the SVG (Context), so the tab would not change.
  - **Drop the SVG and declare 16 px and 32 px PNGs or a `favicon.ico`.** Rejected: more files, and the tab would lose the scalable icon for no gain over A.
  - **A new icon URL so stored tab icons refresh at once.** Rejected: one reload refreshes it, and a new name would change the manifest, the tests, and the offline page.

## Risks / Trade-offs

- [The installed app and the Safari touch icon change slightly (thicker bars, larger square).] → This is wanted for one consistent mark. When an installed app picks up the new icon is up to the browser; this was not tested. Option B avoids it.
- [Chrome keeps showing the old tab icon until a reload.] → The live check reloads the page. No user action is needed beyond the next reload.
- [The renders come from an image in headless Chrome, not from a real tab.] → Chrome draws the tab icon from the same SVG at the same pixel sizes. The live check repeats the render against the built image, and the user can look at a real tab.
- [Firefox and Safari may choose another declared icon.] → Both files show the same mark under A, so either choice is sharp.

## Testing

- **New tests** in `frontend/src/install.test.ts`. The seams are `readFileSync` on `index.html` and the files in `public/`, jsdom's `DOMParser`, and `inflateSync` from `node:zlib`. Both tests compare against one fixed 16 × 16 pattern (`.` light, `#` dark):

  ```
  ................
  ................
  ..############..
  ..############..
  ..############..
  ..############..
  ..###......###..
  ..############..
  ..############..
  ..###......###..
  ..############..
  ..############..
  ..############..
  ..############..
  ................
  ................
  ```

  - `draws the tab icon on the 16 px grid`. Read `public/icon.svg`. Collect its shapes: each `rect` (missing `x` and `y` are 0), and each `h` segment of the stroked `path` as a rectangle that is `stroke-width` high and centered on the segment. Assert that every shape edge is a multiple of 64. Then color each of the 16 × 16 pixel centers with the last shape that contains it, and compare with the pattern.
  - `keeps every app icon sharp at 16 px`. For `icon-192.png`, `icon-512.png`, and `icon-1024.png`: decode the PNG (8-bit RGB, filter type 0 on every row; any other format fails the test). Split it into a 16 × 16 grid of square blocks (12 × 12 pixels at 192 px). Assert that every pixel in a block has the block's color, and that the colors follow the pattern, with `#f4f0e6` light and `#151412` dark.
- **Mutations.** Apply each alone, run the named test, restore, and check with `git diff`:
  - G1: `stroke-width="64"` → `"38"` in `make-icons.py` and `public/icon.svg`. `draws the tab icon on the 16 px grid` fails.
  - G2: the first bar `M320 416h384` → `M320 430h384` in both. The same test fails.
  - G3: the square `x="128" y="128" width="768" height="768"` → `x="164" y="164" width="696" height="696"` in both. The same test fails.
  - G4: the first bar `M320 416h384` → `M320 352h384` in both, which stays on the grid but moves one row up. The same test fails on the pattern, not on the grid check.
  - G5: in `pixel()`, the bar height `int(unit)` → `max(1, int((right - left) * .055))`, then regenerate `public/`. `keeps every app icon sharp at 16 px` fails.
  - G6: put the old SVG back into `offline.html` only. The existing `embeds the CatchUp tab icon in the offline page without another icon request` fails.
- **Checks.** `npm test -- --run` and `npm run build` in `frontend/` and `extension/`, `uv run --offline pytest` in `backend/`, and `DO_NOT_TRACK=1 openspec validate improve-small-icon-legibility --strict`.
- **At review (Claude Code).**
  - `docker build` and `scripts/docker-smoke.sh`.
  - A live check on a spare port with a fresh volume, not 8800. Fetch `/icon.svg`, `/icon-192.png`, and `/offline.html` from the container. Render `/icon.svg` at 16 px and 32 px in headless Chrome, and check that it has 2 colors and matches the pattern. Build the extension and check that its `icon-192.png` is the new file.
  - Optional for the user: open CatchUp in Chrome, reload once, and look at the tab.
