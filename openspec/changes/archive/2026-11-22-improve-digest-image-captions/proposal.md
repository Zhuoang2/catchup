# Proposal

## Why

In the user's live check of #41 (2026-11-01), several digest images made little sense on their own (#65):

- **No visible text.** The summary call writes a text for each image it chooses (`backend/src/catchup/digest/summarize.py:121-123`), but the digest uses it only as the `alt` attribute (`frontend/src/components/DigestArticle.tsx:39-47`). A sighted reader sees Simon Willison's "pelican riding a bicycle" drawings, which are model outputs he uses as a benchmark, with nothing that says so.
- **Formula images are candidates.** Terence Tao's posts render each formula as an image from `https://s0.wp.com/latex.php?latex=…` (checked in his public feed on 2026-11-22: `class="latex"`, the LaTeX source as `alt`, no `width` or `height`). `filter_image_urls` (`backend/src/catchup/sources/feeds.py:117-139`) keeps them, so a post can fill all 8 candidate places with `{T}`, `{X}`, and `{L^p}`.
- **Small images are candidates.** The filter drops only images whose stated width and height are both 1 or less (`feeds.py:130-131`).
- **The prompt does not ask whether an image makes sense alone** (`backend/src/catchup/llm/prompts.py:34-39`), and allows up to 3 images per item without preferring fewer.

The security part of #65 (image addresses on this computer or a local network) shipped in #94 (D-033). This change does the rest, and its PR closes #65.

## What Changes

- **Visible captions.** In the digest reading layout, each chosen image shows its text as a caption directly under it, in the digest's language. Assistive technology reads that text once, as the figure's caption: the image itself carries an empty `alt`. An image that fails to load is hidden together with its caption. An image without text is not shown. Digests saved earlier show their stored text as the caption.
- **No formula images.** An image candidate is left out when its address is a rendered formula: a `latex.php` address (WordPress.com, Jetpack, and its image proxy), an address on `latex.codecogs.com`, or a QuickLaTeX cache file (`quicklatex.com-…`). This applies to every item that keeps image candidates, including X posts and pages saved from the browser, and to candidates stored before this change, which are filtered again before the summary call. Saved digests do not show formula images either.
- **No small images.** A candidate is left out when the page states its width or its height as under 100 px. A candidate whose size is not stated is kept, as now. This replaces the 1×1 rule.
- **A stricter prompt.** The summary call chooses an image only when a reader who has not read the item can understand it from the image and its caption, and writes the caption to say what the image shows and why it matters. It usually chooses one image, and a second or third only when each shows something different that the summary relies on. The limit stays at 3 (design D1 lists the alternatives for the user).
- No API shape, data model, or migration change. The stored field keeps its name, `alt`.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `content-collection`: "Keep image candidates for items" leaves out rendered formulas and images with a stated width or height under 100 px, for every kind of item that keeps candidates.
- `digest-generation`: "Choose important images in summaries" prefers one image, chooses only images a reader can understand with their caption, asks for a caption that says what the image shows and why it matters, and never offers candidates that the collection rules now leave out, including candidates stored earlier.
- `user-interface`: "Show chosen images from their source sites" shows each image's text as a visible caption read once by assistive technology, hides a failed image with its caption, and never shows formula images, including in digests saved earlier.

## Impact

- Code:
  - `backend/src/catchup/sources/feeds.py`: `filter_image_urls` gains the formula and size rules; a small helper filters stored candidates again;
  - `backend/src/catchup/digest/runner.py`: summary inputs use the filtered stored candidates;
  - `backend/src/catchup/api/digests.py`: `_serialize_digest` leaves out formula images;
  - `backend/src/catchup/llm/prompts.py`: `IMAGE_RULES` and the image part of the two example outputs;
  - `frontend/src/components/DigestArticle.tsx` and `frontend/src/styles/components.css`.
- Tests: `backend/tests/test_feeds.py`, `test_discovery.py`, `test_extension_api.py`, `test_digest_stages.py`, `test_digest_runner.py`, `test_digest_history.py`; `frontend/src/components/DigestArticle.test.tsx`, `frontend/src/pages/DigestView.test.tsx`, `frontend/src/pages/Home.test.tsx`.
- Docs: decision log (D-040), requirements-changes table, a test report, the AI usage log.
- Out of scope:
  - the browser extension, which sends no image sizes (`extension/src/extract/page.ts:98-104`); its captures get the address rules only;
  - sizes written with units or in `style` (`80px`, `width: 50px`), which the parser reads as not stated (`feeds.py:53-57`);
  - fetching images to measure them, a per-digest image cap, and a setting for the number of images;
  - `docs/alpha-release.md`, a dated course snapshot.
