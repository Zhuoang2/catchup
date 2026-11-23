# Design

## Context

See `proposal.md` (Why) for the problem. Facts on main `795c5e7` that shape the approach:

- **Where candidates come from.** All candidates pass through `filter_image_urls` (`backend/src/catchup/sources/feeds.py:117-139`):
  - feed entries, through `_entry_images` (`feeds.py:96-114`): HTML `<img>` with `alt`, figure caption, and `width`/`height` (`feeds.py:66-78`); `media:content` and `media:thumbnail` with their `width`/`height`; image enclosures with no size;
  - X posts, through `post_item` (`sources/x_accounts.py:72-85`), with `alt` only;
  - pages saved from the browser, through `save_capture` (`api/extension.py:182-186`), with `url` and `alt` only. The extension sends no sizes (`extension/src/extract/page.ts:98-104`, `extract/x.ts:47-54`).
- **What the filter keeps.** Public `http`/`https` addresses (D-033, `net/public_hosts.py`), no `/avatar/` or `/blavatar/` path, no channel image, no exact duplicate, at most 8. The only size rule drops images whose stated width and height are both 1 or less (`feeds.py:130-131`). Sizes are read by `_dimension` (`feeds.py:53-57`), which accepts whole numbers only, so `80px` and `100%` count as not stated.
- **What feedparser keeps.** A probe with the locked feedparser 6.0.14 showed that its sanitizer keeps `width`, `height`, `class`, and `style` on `<img>`, and removes `srcset`.
- **Formula images in a real feed.** Terence Tao's public feed (read on 2026-11-22) renders every formula as `<img src="https://s0.wp.com/latex.php?latex=%7BT%7D&bg=ffffff&fg=000000&s=0&c=20201002" alt="{T}" class="latex">`, with no size. Display formulas use the same address with a longer `latex=` value. His one real image in the feed states `width="825" height="1023"`. Simon Willison's feed states no image sizes, and its `alt` texts are long descriptions.
- **Stored candidates.** Candidates are stored per item in `Item.image_candidates` (`models.py:133`) when the item is collected (`collection.py:154`, `api/sources.py:259`, `x_accounts.py:83`, `api/extension.py:182`). The runner passes them unchanged to the summary call (`digest/runner.py:366`). Items collected before this change keep their formula candidates until they are delivered.
- **Choice and text.** The prompt rule is `IMAGE_RULES` (`llm/prompts.py:34-39`); the two example outputs show `{"ref": "I1", "alt": "What the image shows"}` (`prompts.py:86`, `:103`). `_summarize` keeps at most 3 valid choices and writes each as `{"url", "alt"}`, where `alt` is the model's text, else the candidate's `alt`, else `Image from <source>`, cut to 120 characters (`digest/summarize.py:110-126`). A summary reused from an earlier run keeps its stored choice (`summarize.py:146-147`, `runner.py:421-423`).
- **Where the text is read.** `Item.summary_images` (`models.py:134`) is copied into `DigestItem.images` (`models.py:232`) when the digest is saved (`runner.py:507`). `_serialize_digest` (`api/digests.py:76-80`) returns those images, filtered by `is_public_url`, for both `/api/digests/{id}` and `/api/digests/latest`. The only renderer is `ItemImages` in `frontend/src/components/DigestArticle.tsx:39-48`, used by the main screen (`pages/Home.tsx`) and the digest page (`pages/DigestView.tsx`). It puts each image in a `<figure>` with `alt={image.alt}` and no `<figcaption>`, and hides a figure whose image fails to load.
- **Accessibility test tools.** A probe in `frontend/` showed that neither `dom-accessibility-api` version installed (0.5.16, used by `@testing-library/dom`, and 0.6.3, used by `jest-dom`) names a `<figure>` from its `<figcaption>`. So `getByRole('figure', { name })` does not work in tests, and an `<img alt="">` has the role `presentation`. axe-core 4.14.0 reports no violation for either `<img alt="">` with a `<figcaption>`, or for an `alt` equal to the caption.

## Goals / Non-Goals

**Goals:**
- One rule for meaningless candidates, applied wherever candidates are kept, and again to candidates stored before the rule.
- Visible captions that assistive technology reads once.
- A prompt that prefers fewer, self-explaining images.

**Non-Goals:**
- Fetching or measuring images; reading sizes from `style`, units, or the extension.
- A setting for the number of images, or a per-digest cap.
- Rewriting stored rows.

## Decisions

Decisions D1–D5 were the user's to confirm at plan approval; the user chose the recommendation for each on 2026-11-22. `tasks.md` is written for the recommendations, and each decision says what changes in `tasks.md` if the user picks another option.

### D1. How many images per item (user decision)

- **Recommended: the prompt prefers one; the limit stays at 3.** The model "usually" chooses one image, and a second or third only when each shows something different that the summary relies on. The code limit in `_summarize` stays 3. This keeps the user's D-021 choice ("more than one image when several matter"), and the issue's "one image per item by default" becomes the default in the prompt.
- **A. A hard limit of 1.** The prompt says "at most 1 image", and `_summarize` stops after 1 choice. Simplest to test, and gives the fewest images, but a post with two charts that matter shows only one. Change in the plan: the `digest-generation` delta says "at most 1 image" instead of "usually … never more than 3", D-040 says the same, and in `tasks.md` 3.1/3.2 the rule text becomes "Choose at most 1 image", and the existing assertions of `"at most 3"` (`test_digest_stages.py:125`, `test_long_summaries.py:62`, `:168`, `:171`) and the cap test (`test_summary_image_choices_validate_refs_cap_and_alt_fallback`) change to 1, with a mutation that sets the limit back to 3.
- **B. A setting "Images per item" (1–3, default 1).** Rejected for this change: it needs a preferences column and a migration, and edits the Settings page and `api/settings.py`, which change #12 (Anthropic provider) also edits in parallel.
- **C. Keep the prompt's "at most 3" as it is.** Rejected: the issue asks for fewer images.

### D2. Which small images are left out (user decision)

- **Recommended: a stated width or height under 100.** If either stated number is under 100, the candidate is left out; an image with no stated size is kept. This drops thin banners and dividers (600×40), small icons, Gravatar-sized avatars (96×96), and 1×1 pixels, which it replaces. In `filter_image_urls`, the condition is `any(size is not None and size < 100 for size in (image.width, image.height))`.
- **Both sides under 100.** Keeps a 600×40 banner. Rejected.
- **A lower threshold, such as 64.** Keeps 80–96 px icons and avatars. Rejected.
- **Measure images that state no size.** Rejected: "Keeping candidates MUST NOT fetch any image", and it would contact image hosts during every check.
- **Read `80px` and `style` sizes.** Left out: neither feed in #65 uses them, and the HTML parsing rules for dimensions would need their own tests. Recorded as a limit.

### D3. Digests saved before this change (user decision)

- **Recommended: show their stored text as the caption, and hide their formula images.**
  - The stored `alt` texts are the model's short descriptions in the digest's language (D-021 amendment), so they read as captions, though they may not say why the image matters.
  - `_serialize_digest` also leaves out formula images, as it already leaves out local addresses (D-033). This covers saved digests and reused summaries. Sizes are not stored with chosen images, so the size rule cannot apply here.
- **Captions only in new digests.** New summaries would store a separate `caption` field, and the reading view would show a caption only when it exists. Rejected: a second field for the same text, and old digests keep invisible text.
- **Keep formula images in old digests.** Rejected: they are the images the issue calls meaningless, and the check costs one line next to the existing one.

### D4. Caption and assistive technology (user decision)

- **Recommended: `<figure>`, `<img alt="">`, and `<figcaption lang="…">` with the text.** Screen readers announce the figure with its caption, once. This follows WAI's guidance for an image whose text alternative is already in adjacent text: an empty `alt` avoids reading it twice. The caption is real text: it can be selected, translated, and zoomed. When the image fails to load, the figure is hidden with its caption, as now. An image with an empty text is not shown, because it would then have no text alternative at all.
- **`alt` with the text, and `<figcaption aria-hidden="true">`.** Screen readers say "image" with the text. Rejected: visible text hidden from assistive technology cannot be reached by screen reader users who also see the page.
- **Two texts: a short `alt` and a longer caption.** The model would write both. Rejected: more output per image, a new stored field, and most of the two texts would repeat each other.
- **`alt` and a caption with the same text.** Rejected: read twice.

### D5. How to check that meaningless images become fewer (user decision)

Claude Code cannot use the user's model key, so the model's choices on real feeds are the user's check. Recommended:
1. **At review, the candidate rules on the same feeds.** Claude reads the current public feeds of Terence Tao's blog (`https://terrytao.wordpress.com/feed/`) and Simon Willison's blog (`https://simonwillison.net/atom/everything/`) once each, in memory without saving them. It runs `parse_feed` from main and from the branch on the same bytes, and reports the candidates per entry: formula candidates must be 0 on the branch, and real images must stay.
2. **At review, a browser check with a stub model** on a scratch container with a fresh volume and a port other than 8800: a digest whose items chose images with captions, at 1280 px and 375 px wide, with the accessibility tree read, a failing image, and images turned off.
3. **After the merge, the user's check.** When the user rebuilds their own instance, they run a digest with the same two feeds and their own model, and look at whether each shown image makes sense with its caption.

### D6. Which addresses are formulas

`is_formula_image(url)` in `sources/feeds.py` splits the address with `split_url` and returns true when, comparing in lower case:
- the last part of the path is `latex.php`. This covers `s0.wp.com/latex.php` (WordPress.com and Jetpack), any site's own `latex.php`, and the image proxy form `i0.wp.com/s0.wp.com/latex.php`;
- the host is `latex.codecogs.com`;
- the last part of the path starts with `quicklatex.com-` (QuickLaTeX caches rendered formulas as `/wp-content/ql-cache/quicklatex.com-<hash>_l3.png`).

An address that cannot be split returns false; the other rules drop it. Alternatives: matching `latex` anywhere in the address (rejected: drops `latex-guide.png`), or the `class="latex"` attribute (rejected: X posts, captures, and stored candidates have no class, so one address rule serves every caller). Google Chart formula images (`cht=tx`) are left out: the service was turned off, so they fail to load and are hidden already.

### D7. Filter stored candidates before the summary call

`stored_image_candidates(stored)` in `sources/feeds.py` turns stored candidate dicts back into `EntryImage` values, skipping entries that are not dicts or have no string `url`, reads `width` and `height` with `_dimension`, runs `filter_image_urls`, and returns the result as dicts. `runner.py:366` passes `stored_image_candidates(item.image_candidates)` instead of `item.image_candidates or []`. The filter is idempotent for candidates that passed it before, so the order and the `I1…I8` refs stay the same for new items. Alternative: a migration that rewrites `image_candidates` (rejected: stored rows stay as they are, as in D-033).

### D8. Keep the stored field, the length, and the fallback

- The text stays in the `alt` key of `summary_images` and `DigestItem.images`, and the API shape does not change. The prompt says the text is a caption.
- The limit stays at 120 characters (`summarize.py:123`), which fits "what it shows and why it matters" in one or two lines.
- The fallback order stays: the model's text, then the candidate's `alt`, then `Image from <source>`. The last one is visible now, but appears only when neither the model nor the page gave a text.

## Prompt text

`IMAGE_RULES` becomes exactly:

```
Choose at most 3 images, ordered by importance, and usually only one. Choose an image only when it shows something the summary relies on, and a reader who has not read the item can understand it from the image and its caption. Choose a second or third image only when each shows something different. Never choose logos, avatars, decorative images, or rendered formulas; choose none when unsure. For each choice, write in alt a caption of up to 120 characters in the language of the summary, saying what the image shows and why it matters.
```

(one string, followed by one space, as the current constant ends with a space). Both example outputs (`prompts.py:86`, `:103`) become `{"ref": "I1", "alt": "What the image shows and why it matters"}`. Prompts without images stay byte for byte the same; `test_no_context_system_prompt_matches_original_main_bytes` and `test_no_image_long_transcript_prompt_matches_original_main_bytes` keep passing unchanged.

## Risks / Trade-offs

- [The model still chooses a weak image] → The prompt is the only lever; the caption now gives context, and D5 step 3 is the user's check on real output.
- [A large image displayed small (`width="90"`) is dropped] → Rare in feeds; the rule follows the page's own size.
- [Formula renderers outside D6 still pass] → The list is in one function and can grow.
- [Reused summaries keep their earlier choice of up to 3 images] → Only items with a summary stored by an earlier run that did not save a digest; formula images among them are hidden by D3.
- [Old captions describe without saying why] → Accepted (D3).
- [`Image from <source>` is shown as a caption] → Only when neither the model nor the page gave a text (D8).
- [Change #12 (Anthropic provider) also edits `backend/src/catchup/llm/` in parallel] → This change edits only `IMAGE_RULES` and the two example strings in `llm/prompts.py`. A conflict there is a text conflict to resolve by hand at merge.

## Migration Plan

No migration. Candidates stored earlier are filtered when read (D7), and saved digests when served (D3). Rollback is a revert.

## Testing

Test-first (D-016). Seams:

- `filter_image_urls` and `is_formula_image` in `catchup.sources.feeds`, directly, with parametrized tables (`backend/tests/test_feeds.py`);
- `parse_feed`, `FetchResponse`, and `image_feed` (`backend/tests/test_discovery.py`);
- `client`, `connected`, and `save_page` (`backend/tests/test_extension_api.py`);
- `stored_image_candidates` directly (`backend/tests/test_feeds.py`);
- `environment`, `seed`, `stub_collection`, `execute`, and `FakeModel.calls` (`backend/tests/test_digest_runner.py`);
- `summary_messages`, `long_transcript_messages`, `summarize_items`, and `FakeModel` (`backend/tests/test_digest_stages.py`);
- `test_settings`, `TestClient(create_app(...))`, and rows written through `client.app.state.session_factory()` (`backend/tests/test_digest_history.py`, as `test_saved_digest_never_returns_local_images` does);
- `DigestArticle` rendered in `MemoryRouter`, `fireEvent.error`, and `expectAccessible` (`frontend/src/components/DigestArticle.test.tsx`).

Scenarios about what the model chooses ("Release post with a screenshot", "Benchmark drawing", "No important image") cannot be tested offline. Tests check the prompt text that asks for them, and D5 step 3 checks real output. "Digest saved before captions" uses the same rendering as any stored text, so the caption test covers it.

Named mutations, each applied alone and restored:

| Id | Mutation | Must fail |
|---|---|---|
| C1 | `is_formula_image` without the `latex.php` rule | `latex.php` rows, the mathematics-post feed test, the capture test |
| C2 | without the `latex.codecogs.com` rule | the codecogs row |
| C3 | without the `quicklatex.com-` rule | the QuickLaTeX row |
| C4 | match `latex.php` anywhere in the path, not only the last part | the kept row `https://cdn.example/latex.php/chart.png` |
| C5 | compare without lower-casing | the row `https://S0.WP.COM/LATEX.PHP?latex=x` |
| C6 | `filter_image_urls` does not call `is_formula_image` | the mathematics-post feed test and the capture test |
| S1 | the size rule needs both sides stated | the `width="99"`-only row |
| S2 | the size rule needs both sides under 100 | the 80×600 and 600×40 rows |
| S3 | `<= 100` instead of `< 100` | the kept 100×100 row |
| S4 | a missing size counts as small | the kept no-size row |
| R1 | `runner.py` passes `item.image_candidates or []` again | the stored-formula runner test |
| R2 | `stored_image_candidates` without the dict and string-`url` guard | the malformed-entries test |
| H1 | `_serialize_digest` without the formula check | the saved-digest formula test |
| P1 | rule text without "usually only one" | the prompt rule test |
| P2 | without the "understand it from the image and its caption" sentence | the prompt rule test |
| P3 | without "why it matters" | the prompt rule test |
| P4 | without "rendered formulas" | the prompt rule test |
| P5 | example outputs keep "What the image shows" | the example test |
| U1 | `<img>` keeps `alt={image.alt}` | the caption test (`alt` must be empty) |
| U2 | no `<figcaption>` | the caption test |
| U3 | `<figcaption>` without `lang` | the caption language test |
| U4 | images with empty text are shown | the image-without-text test |
| U5 | a failed image hides only the `<img>`, and its caption stays | the failed-image test |

At review, Claude runs `scripts/docker-smoke.sh` and the checks in D5 steps 1 and 2.
