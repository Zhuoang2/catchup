# Proposal

## Why

Digests are text only, so a post whose point is a chart, a screenshot, or a diagram loses it (issue #49, user testing on 2026-10-19, item F9). The research (`research.md`) found:
- **No image data survives collection.** `plain_text` drops `<img>` `src` and `alt` (`backend/src/catchup/sources/feeds.py:87-99`), and `parse_feed` reads no `media_content`, `media_thumbnail`, or image enclosures (`:153-203`), although feedparser exposes them.
- **Nothing downstream holds an image:** not the items, the digest snapshot, the model output, or the digest API. The frontend renders no `<img>`.
- **The user's sources:**
  - Simon Willison has `<img>` with alt text in 9 of 30 entries.
  - The Verge has a lead image in each entry, with 5 of 11 alts empty.
  - Terry Tao's `media:content` is mostly author avatars.
  - YouTube has one thumbnail per entry.
  - All four sampled image hosts allowed loading from `127.0.0.1:8800`.

**User decisions** (2026-10-19):
- The model decides which images are important.
- More than one may be chosen when several matter ("if there are many important images, it can pick more than one").
- Load them directly from the source site first.

## What Changes

- **Keep image candidates.** For website items and YouTube videos, CatchUp keeps up to 8 candidates in body order: images in the entry HTML (with alt text and the figure caption), `media:content` images, `media:thumbnail`, and image enclosures. These are skipped:
  - avatars and site icons (Gravatar `/avatar/` and `/blavatar/`);
  - channel images and icons;
  - `data:` URLs;
  - 1×1 tracking pixels.
- **The summary call chooses.** The candidates go to the summary call as short descriptions. The model returns up to **3** images that carry information the summary relies on, ordered by importance, each with a short alt text it writes. It returns none when no image matters. Unknown refs are dropped. The choice is stored with the summary, and reused with it.
- **The digest shows them.**
  - **Where:** the chosen images appear under the item's summary, loaded directly from the source site.
  - **How they load:** lazily, with no referrer, at most 320 px tall.
  - **Failures:** an image that fails to load is hidden.
  - **Saved digests** keep their images.
- **A setting.** "Show images from source sites", default on, in the Digest group of Settings. Its note says that opening a digest then contacts those sites. When it is off, no image is requested.
- **Out of scope:**
  - storing copies of images, or a proxy;
  - the page's `og:image`, which would need the item page that `article_text` does not keep;
  - podcast cover art;
  - images under Creator updates;
  - a cap per digest, which can be added later if digests look crowded.
- **Order.** This change follows `add-linked-pages-and-author-replies` (#48). It uses the next migration (`0005`) and extends the same summary output and reading layout.

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- `content-collection`: new requirement "Keep image candidates for items".
- `digest-generation`: new requirement "Choose important images in summaries".
- `digest-history`: new requirement "Saved digests keep their images".
- `user-interface`: new requirement "Show chosen images from their source sites", covering the reading layout, loading and failure behavior, and the setting with its note.

## Impact

- **Backend:**
  - `sources/feeds.py` (image candidates);
  - `collection.py` and `api/sources.py` (store the candidates);
  - `models.py`, with migration `0005_item_images`: `items.image_candidates`, `items.summary_images`, `digest_items.images`, and `app_settings.show_images`;
  - `llm/prompts.py` and `digest/summarize.py` (candidates and the `images` output);
  - `digest/runner.py` (record and snapshot);
  - `api/digests.py` (`images`) and `api/settings.py` (`show_images`).
- **Frontend:** `components/DigestArticle.tsx` and its CSS, and `pages/Settings.tsx`.
- **Tests:**
  - new parse, summary, snapshot, API, settings, and rendering tests;
  - updates to `DigestView.test.tsx:47` (no `img`) and `:248-276` (item children), `tokens.test.ts:263-266`, `test_digest_history.py:289-292`, and `test_db.py:63`.
- **Privacy:** the README notes the hotlinking.
