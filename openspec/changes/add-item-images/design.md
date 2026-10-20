# Design

Full RePPIT change for issue #49. The research is in `research.md`, the motivation in `proposal.md`, and the requirements in the spec deltas.

- **Chosen:** Proposal 1, "Keep feed image candidates; the summary call picks". The user chose it on 2026-10-19, with one change: more than one image when several matter.
- **Rejected:** Proposal 2, "choose images for the whole digest after grouping". It is recorded under D8.
- **Order:** this change builds on `add-linked-pages-and-author-replies` (#48), and is implemented after it is merged.

## Context

- **Parsing** (`backend/src/catchup/sources/feeds.py`).
  - `plain_text` keeps text nodes only (`:87-99`), so `<img src alt>` is lost and `<figcaption>` text is kept.
  - `parse_feed` (`:153-203`) reads no media fields.
  - feedparser 6.0.14 exposes `media_content`, `media_thumbnail`, `enclosures` with an image type, and `entry.image`.
- **After #48:**
  - `FeedEntry` has `links` and comment pointers.
  - The migration head is `0004_item_context`.
  - The summary output is `{"summary", "used"}`.
  - `DigestItem` has `context_links`.
  - The reading layout shows "Also read".
- **Summaries.** `summary_messages` is text-only JSON (`llm/client.py:116-140`). Results are recorded by `record()` in `digest/runner.py`, and copied into `DigestItem` in the snapshot.
- **Preferences.**
  - Stored in `AppSettings` (`models.py:49-56`).
  - Served by `GET` and `PUT /api/settings/preferences` (`api/settings.py:35-38`, `:139-166`).
  - Edited in `pages/Settings.tsx`, in the Digest group.
- **Frontend.** No `<img>` is rendered (`DigestView.test.tsx:47` asserts none). There is no CSP or `Referrer-Policy`. The service worker handles navigations only.

## Goals / Non-Goals

**Goals:**
- Show the images that carry an item's point, chosen by the model, with alt text.
- Load them directly from their source sites, with a way to turn this off.

**Non-Goals:**
- Image copies or a proxy.
- `og:image`.
- Podcast cover art.
- Images under Creator updates.
- A cap per digest.
- Vision models: the model sees text descriptions only.

## Decisions

### D1. Candidates at parse time
- **The new field.** `FeedEntry.images: tuple[EntryImage, ...]`, where `EntryImage(url, alt, caption, width, height, origin)`. Website and YouTube entries fill it, in this order:
  1. `<img>` elements in the entry HTML, in body order. The alt comes from `alt`. The caption is the enclosing `<figure>`'s `<figcaption>` text.
     - **The URL (fix round 1).** Use `data-src` when present, because lazy-loading markup keeps a placeholder in `src`. Otherwise use `src`, unless it is missing or a `data:` URL. Otherwise use `srcset`, or `data-srcset`: take the candidate with the largest `w` descriptor, or the first candidate when none has one.
  2. `media_content` with `medium="image"` or an image type.
  3. `media_thumbnail`.
  4. Enclosures with an `image/*` type.
- **Filters.** Keep http(s) only. Skip:
  - `data:` URLs;
  - paths containing `/avatar/` or `/blavatar/`, on any host;
  - the feed's channel image, icon, and logo, by exact URL;
  - images whose width and height are both whole numbers of at most 1.
- **Duplicates and the cap (fix round 1).** Two candidates are duplicates only when their URLs are equal after resolving and removing the fragment. The query string is kept, because some hosts tell images apart only by it, such as `/image.php?id=1` and `?id=2`. Cap at 8.
- **Not for podcasts.** Entries with an audio enclosure keep no candidates. This covers podcast episodes. Their cover art (`entry.image`, `itunes:image`) is never read.
- **Known limits (fix round 1, recorded, not changed):**
  - The avatar rule also drops another site's `/avatar/` path, and misses avatars at other paths, such as GitHub's.
  - A channel image with a different query string, such as `?v=2`, is not matched.
  - A website feed's entry with an audio enclosure keeps no candidates.
  - Sizes with units, such as `width="1px"`, are not recognized as tracking pixels.
- **Storage.** `check_source` and confirmation store them on new items as `Item.image_candidates` (JSON).

### D2. Choosing in the summary call
- **The prompt.** `summary_messages` gains an optional `images` list. After the content and the #48 context blocks, the user message adds `Images:`, then one line per candidate, such as `I1 — in the post, position 1; alt "…"; caption "…"`. Alt and caption are each cut to 200 characters.
- **Quoting (fix round 1).** Alt and caption come from the feed, so they are data. Before the cut, whitespace, including line breaks, is collapsed to single spaces. After the cut, each is written as a JSON string (`json.dumps(..., ensure_ascii=False)`). A quote or a line break in feed text therefore cannot end the field or start a new candidate line.
- **The rules,** added to the system prompt:
  - choose at most 3 images that show something the summary relies on, ordered by importance;
  - never choose logos, avatars, or decorative images;
  - choose none when unsure;
  - write a short alt text of up to 120 characters for each;
  - (fix round 1) write each alt text in the language of the summary.
- **The output.** `{"summary": "...", "used": [...], "images": [{"ref": "I1", "alt": "..."}]}`.
- **The example (fix round 1).** The summary prompt and the long-transcript prompt show the same neutral example, `{"ref": "I1", "alt": "What the image shows"}`. The long-transcript example no longer says "Video thumbnail", which suggested choosing the thumbnail.
- **Validation.** Unknown or duplicate refs are dropped, and anything beyond 3 is cut. An empty model alt falls back to the feed alt cut to 120 characters, and then to "Image from <source name>". That fallback stays in English, like the rest of the interface.
- **Long transcripts.** A long transcript summarized in one call receives the images and the rules in that call.
- **Split items.** The images go to the combine call.

### D3. Storage, migration `0005_item_images`
- `items.image_candidates`: JSON, nullable.
- `items.summary_images`: JSON, nullable, a list of `{url, alt}`. It is written by `record()` with the summary, and kept when the summary is reused.
- `digest_items.images`: JSON, nullable.
- `app_settings.show_images`: boolean, server default true.

### D4. Snapshot and API
- The snapshot copies `summary_images` into `DigestItem.images`.
- `api/digests.py` returns `images` for each summarized item: `[]` when there is none, and for older digests.
- `GET` and `PUT /api/settings/preferences` gain `show_images`.

### D5. Reading layout (`DigestArticle.tsx`, CSS)
- **Where.** After the summary, and before #48's "Also read" line, render `<div class="item-images">`.
- **Each image** is `<figure><img src alt loading="lazy" decoding="async" referrerpolicy="no-referrer"></figure>`.
- **Size.** CSS sets `max-height: 320px`, `max-width: 100%`, `object-fit: contain`, and a thin border. Two or three images wrap in a flex row with a gap. The item grid is unchanged, because the block sits inside the summary cell.
- **Figure margin (fix round 1).** `.item-images figure` sets `margin: 0`. Without it, the browser's default figure margin indents each image by 40 px on both sides: the images no longer line up with the summary, and two or three no longer fit in one row.
- **Failure.** `onError` hides that figure.
- **The setting.** When `show_images` is false, the block is not rendered, so no request is made. `DigestView` and `Home` read the preference once with their other startup requests. If that read fails, images are shown, which matches the default.
- **Order of loading (fix round 1).** Both pages show the digest only after the preference request has also settled, so no image is requested before a stored "off" is known. Settings shows a stored false as off, and saving keeps it off.
- **Guards.** The CSS structure guards in `tokens.test.ts` are extended to allow the new class.

### D6. Settings (`pages/Settings.tsx`)
- In the Digest group, the toggle "Show images from source sites", with the note "Opening a digest loads its images from the sites that published them." It is associated with the toggle through `aria-describedby`, as the YouTube caption note is.

### D7. Privacy
- Hotlinking sends the user's IP address and a normal browser request to each image host, with no referrer (`referrerpolicy="no-referrer"`). The README's privacy notes, and the Settings note, say this.
- **The README (fix round 1).** A `## Privacy` section, after "Install as an app", holds the existing note on the model provider and the image note. The image note says:
  - images load when a digest is shown, including the latest digest on the home page;
  - if CatchUp cannot read the setting, images are shown.
- No cookies were set by the four sampled hosts (research, External Facts).

### D8. Alternatives considered
- **Proposal 2: one image-selection call for the whole digest, after grouping.** Rejected:
  - it judges from summaries, not the full text;
  - it adds a run stage and a stepper step;
  - the summary cannot refer to the image.
- **Storing image copies.** Rejected for now, as the user asked to try hotlinking first. It may return if hosts block hotlinking or images disappear.
- **`og:image` from the page.** Left out. `article_text` drops the page after extraction, and the research showed that `og:image` is usually the feed's lead image (The Verge) or the site icon (Tao).

## Risks / Trade-offs

- **[The model sees descriptions, not pixels]** A well-captioned decorative image may be chosen. → Strict rules, "none when unsure", and the 3-image cap.
- **[Crowded digests]** Up to 3 images per item. → The cap. A cap per digest or per topic can follow, if the user finds digests crowded.
- **[Images disappear or become blocked]** → The figure is hidden on error.
- **[Large images]** The Verge's lead image is 1.2 MB. → Lazy loading. There is no resizing without a proxy.
- **[Privacy]** → The setting, the note, and no referrer.
- **[Tokens]** Each candidate adds about 1 line. → At most 8 candidates, with alt and caption cut to 200 characters each.

## Migration Plan

- Migration `0005` adds nullable JSON columns and one boolean column with a default, so existing items and digests are unaffected.
- Rollback: downgrade drops the columns.
- Testing notes:
  - parsing fixtures shaped like the research's four sources;
  - `FakeModel` for the choice;
  - backend API tests;
  - frontend vitest and axe for the figure, the error hiding, and the setting;
  - a live check at review with a stub model on Simon Willison and The Verge, at 1440, 900, and 420 px, in both themes.

## Open Questions

- A cap per digest (for example, 1 per topic), if digests look crowded.
- YouTube thumbnails are candidates, and the model decides. Should they be dropped if the model picks them too often?
