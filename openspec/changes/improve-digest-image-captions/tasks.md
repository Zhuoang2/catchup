# Tasks

Implementer notes:
- **Read first.** Read `proposal.md`, `design.md` (all of "Context", D1–D8, "Prompt text", and "Testing"), and the three spec deltas under `specs/`. If something looks wrong or contradictory, stop and report instead of redesigning.
- **Work test-first with the `tdd` skill** (D-016). For each group, first write its tests, run them, and watch them fail. Then change the code. The seams are listed in design "Testing", and they count as agreed.
- **Test rules.**
  - No real network, and no fetch of any image.
  - Change no existing test, except where a task says so. Adding imports to an existing test file is allowed: `import pytest` in `backend/tests/test_feeds.py`, and `within` from `@testing-library/react` and `digestLang` from `./lang` in `frontend/src/components/DigestArticle.test.tsx`.
  - For each named mutation, apply it alone, run the named tests, record the result, and restore the code exactly. Compare with `git diff` after restoring.
  - Small traps:
    - `image_feed` in `test_discovery.py` HTML-escapes the body, so write `&` in image addresses as a plain `&`; the parser decodes it again. A `media:content` image needs `medium='image'`.
    - `dom-accessibility-api` does not name a `<figure>` from its `<figcaption>`, and an `<img alt="">` has the role `presentation` (design "Context"). Find captions with `getByText(text, { selector: 'figcaption' })`, not with `getByRole('img', { name })` or `getByRole('figure', { name })`.
- **Environment.**
  - Backend: run commands in `backend/` with `uv run --offline`, without installing new packages.
  - Frontend: use Node 22.17.1 with `export PATH="$HOME/.nvm/versions/node/v22.17.1/bin:$PATH"`. Then run `npm ci --offline --no-audit --no-fund` in `frontend/`, and again in `extension/`. Both install the locked packages from the local npm cache. If either fails, stop and report. Do not download packages, and do not change `package.json` or `package-lock.json`.
- **Out of scope:**
  - backend files other than `sources/feeds.py`, `digest/runner.py`, `api/digests.py`, and `llm/prompts.py`, and their tests named below; in particular `digest/summarize.py` keeps its limit of 3 and its fallback (design D1, D8);
  - frontend files other than `src/components/DigestArticle.tsx`, `src/styles/components.css`, and the three test files named below;
  - the extension, migrations, models, stored rows, the API shape, Settings, and dependency versions.
- **Do not edit** `proposal.md`, `design.md`, the spec deltas, `docs/process/decision-log.md`, or `docs/process/requirements-changes.md`. Claude Code wrote D-040 and the requirements row with the plan.
- **Commits.** Commit after each task group. Do not push, tag, or open a PR.

## 1. Formula and small images are not kept as candidates (content-collection; design D2, D6)

- [x] 1.1 Write failing tests in `backend/tests/test_feeds.py`:
  - `test_is_formula_image`, parametrized over `(url, expected)`, calling `is_formula_image` from `catchup.sources.feeds`:
    - `True`: `https://s0.wp.com/latex.php?latex=%7BT%7D&bg=ffffff&fg=000000&s=0&c=20201002`, `https://S0.WP.COM/LATEX.PHP?latex=x`, `https://i0.wp.com/s0.wp.com/latex.php?latex=a%2Bb`, `https://blog.example/latex.php?latex=x`, `https://latex.codecogs.com/png.image?a%2Bb`, `https://LATEX.CODECOGS.COM/svg.latex?x`, `https://blog.example/wp-content/ql-cache/quicklatex.com-0a1b2c_l3.png`;
    - `False`: `https://cdn.example/latex-guide.png`, `https://cdn.example/latex.php/chart.png`, `https://blog.example/latex.php.png`, `https://www.codecogs.com/images/logo.png`, `https://cdn.example/quicklatex.png`, `http://[x`.
  - `test_filter_image_urls_drops_small_stated_sizes`, parametrized over `(width, height, kept)`, calling `filter_image_urls([EntryImage("https://cdn.example/a.png", width=width, height=height)])` and asserting whether one image is kept:
    - dropped: `(80, 600)`, `(600, 40)`, `(99, None)`, `(None, 64)`, `(1, 1)`, `(0, 0)`;
    - kept: `(100, 100)`, `(600, None)`, `(None, None)`, `(825, 1023)`.
  - `test_filter_image_urls_drops_formula_images`: `filter_image_urls` over `EntryImage("https://s0.wp.com/latex.php?latex=x", alt="{x}")` and `EntryImage("https://cdn.example/chart.png", alt="Chart")` keeps only the chart.

  Import `is_formula_image` inside `test_is_formula_image`, not at the top of the file, so that the file's other tests still run before it exists.

  Verify: `test_is_formula_image` fails with an import error; the dropped rows `(80, 600)`, `(600, 40)`, `(99, None)`, and `(None, 64)` fail; `(1, 1)`, `(0, 0)`, and the kept rows pass, because the current 1×1 rule already drops the first two; `test_filter_image_urls_drops_formula_images` fails.
- [x] 1.2 Write failing tests through the callers:
  - in `backend/tests/test_discovery.py`, `test_formula_and_small_images_are_not_candidates`: an `image_feed` body with `<img src='https://s0.wp.com/latex.php?latex=%7BT%7D&bg=ffffff&fg=000000&s=0&c=20201002' alt='{T}' class='latex'>`, `<img src='https://s0.wp.com/latex.php?latex=%7BL%5Ep%7D&bg=ffffff' alt='{L^p}' class='latex'>`, `<img src='/icon.png' width='80' height='600'>`, `<img src='/rule.png' width='600' height='40'>`, `<img src='/wide.png' width='80px'>`, and `<img src='https://blog.example/wp-content/uploads/diagram.png' width='825' height='1023' alt='Diagram'>`, and `media="<media:content url='https://cdn.example/m.jpg' medium='image' width='64' height='64'/>"`. Parse it with `parse_feed(FetchResponse(...))`, and assert that the entry's image URLs are exactly `["https://site.example/wide.png", "https://blog.example/wp-content/uploads/diagram.png"]`;
  - in `backend/tests/test_extension_api.py`, `test_capture_drops_formula_images`: `save_page(client, connected, images=[{"url": "https://s0.wp.com/latex.php?latex=x", "alt": "x"}, {"url": "https://example.com/photo.png", "alt": "Photo"}])`, and assert that the stored `image_candidates` URLs are exactly `["https://example.com/photo.png"]`.

  Verify: both tests fail on the current code.
- [x] 1.3 In `backend/src/catchup/sources/feeds.py`, add `is_formula_image(url: str) -> bool` as in design D6, using `split_url`. In `filter_image_urls`, leave out an image when `is_formula_image(url)` is true, and replace the 1×1 condition (`feeds.py:130-131`) with the D2 rule `any(size is not None and size < 100 for size in (image.width, image.height))`. Update the docstring of `filter_image_urls` to name the new rules. Keep the other rules and the order.

  Verify:
  - the tests from 1.1 and 1.2 pass, and `uv run --offline pytest` passes in `backend/`, including `test_image_filters_duplicates_pixels_and_caps_at_eight` unchanged;
  - mutations C1–C6 and S1–S4 from design "Testing" each fail the tests named there. Restore the code after each.

## 2. Stored candidates and saved digests (digest-generation, user-interface; design D3, D7)

- [x] 2.1 Write failing tests:
  - in `backend/tests/test_feeds.py`, `test_stored_image_candidates_apply_the_rules_again`: `stored_image_candidates` from `catchup.sources.feeds` over `[{"url": "https://s0.wp.com/latex.php?latex=%7BT%7D", "alt": "{T}", "caption": "", "width": None, "height": None, "origin": "html"}, {"url": "https://cdn.example/icon.png", "alt": "", "caption": "", "width": 16, "height": 16, "origin": "html"}, "not a dict", {"alt": "no url"}, {"url": 7}, {"url": "https://cdn.example/chart.png", "alt": "Chart", "caption": "Sales", "width": None, "height": None, "origin": "media"}]` returns exactly `[{"url": "https://cdn.example/chart.png", "alt": "Chart", "caption": "Sales", "width": None, "height": None, "origin": "media"}]`. Also assert that `stored_image_candidates(None) == []`. Import `stored_image_candidates` inside the test, as in 1.1;
  - in `backend/tests/test_digest_runner.py`, `test_summary_call_is_not_offered_formula_candidates_stored_earlier`: `seed(environment)` and `stub_collection(monkeypatch)`, then set the item's `image_candidates` to `[{"url": "https://s0.wp.com/latex.php?latex=%7BT%7D", "alt": "{T}", "caption": "", "origin": "html"}, {"url": "https://cdn.example/chart.png", "alt": "Chart", "caption": "", "origin": "html"}]`, as `test_record_persists_image_choices_and_retry_keeps_them` does. Use a `FakeModel` that answers `{"summary": "Explains the chart.", "images": [{"ref": "I1", "alt": "Rising sales"}]}` and then one topic. After `execute(environment)` succeeds, assert that the summary call's user message (`model.calls[0][0][1]["content"]`) contains `I1 — in the post, position 1; alt "Chart"`, and contains neither `{T}` nor `I2` (the message lists each candidate's alt and caption, never its address), and that `environment.get(f"/api/digests/{result['digest_id']}")` returns that item's `images` as exactly `[{"url": "https://cdn.example/chart.png", "alt": "Rising sales"}]`, as `test_run_uses_source_title_for_empty_image_alt_fallback` reads it;
  - in `backend/tests/test_digest_history.py`, `test_saved_digest_never_returns_formula_images`: write a `DigestItem` whose `images` is `[{"url": "https://s0.wp.com/latex.php?latex=%7BT%7D", "alt": "{T}"}, {"url": "https://cdn.example/chart.png", "alt": "Chart"}]`, as `test_saved_digest_never_returns_local_images` does. Assert that `GET /api/digests/{id}` and `GET /api/digests/latest` both return that item's `images` as exactly `[{"url": "https://cdn.example/chart.png", "alt": "Chart"}]`, and that the stored `DigestItem.images` still has both entries.

  Verify: the three tests fail on the current code.
- [x] 2.2 Add `stored_image_candidates(stored: object) -> list[dict]` to `backend/src/catchup/sources/feeds.py` as in design D7. In `backend/src/catchup/digest/runner.py:366`, pass `stored_image_candidates(item.image_candidates)` instead of `item.image_candidates or []`. In `_serialize_digest` (`backend/src/catchup/api/digests.py:76-80`), also leave out an image when `is_formula_image(image["url"])` is true.

  Verify: the tests from 2.1 pass, and `uv run --offline pytest` passes in `backend/`. Mutations R1, R2, and H1 each fail the tests named in design "Testing". Restore the code after each.

## 3. The prompt prefers one self-explaining image (digest-generation; design D1, "Prompt text")

- [x] 3.1 Write a failing test in `backend/tests/test_digest_stages.py`, `test_image_rules_ask_for_self_explaining_images_with_captions`. For both `summary_messages("Post", "Text", "en", images=image)` and `long_transcript_messages("Talk", "Transcript", "en", images=image)`, with `image = [{"origin": "html", "alt": "Chart", "caption": ""}]`, assert that the system message contains each of: `usually only one`, `a reader who has not read the item can understand it from the image and its caption`, `Choose a second or third image only when each shows something different`, `rendered formulas`, `write in alt a caption of up to 120 characters`, `saying what the image shows and why it matters`, and `{"ref": "I1", "alt": "What the image shows and why it matters"}`.

  In the same file, change only one line of `test_image_prompts_request_summary_language_alt_and_share_neutral_example`: the asserted example becomes `'{"ref": "I1", "alt": "What the image shows and why it matters"}'`.

  Verify: the new test and the changed test fail on the current code. The other image prompt tests still pass.
- [x] 3.2 In `backend/src/catchup/llm/prompts.py`, set `IMAGE_RULES` to the exact text in design "Prompt text", and change the image part of both example outputs (`prompts.py:86`, `:103`) to `"alt": "What the image shows and why it matters"`.

  Verify:
  - the tests from 3.1 pass, and `uv run --offline pytest` passes in `backend/`, including `test_no_context_system_prompt_matches_original_main_bytes`, `test_no_image_long_transcript_prompt_matches_original_main_bytes`, and the `"at most 3"` assertions in `test_digest_stages.py` and `test_long_summaries.py`, all unchanged;
  - mutations P1–P5 each fail the tests named in design "Testing". Restore the code after each.

## 4. Visible captions in the reading view (user-interface; design D3, D4)

- [x] 4.1 Write failing tests in `frontend/src/components/DigestArticle.test.tsx`:
  - `shows each image's text once, as its figure's caption`. Render a digest with `language: 'zh-Hans'` whose item has `images: [{ url: 'https://cdn.example/chart.png', alt: 'Sales doubled after the redesign' }]`. Assert that:
    - the `.item-images figure` holds an `img` with `src` `https://cdn.example/chart.png` and an empty `alt` attribute (`toHaveAttribute('alt', '')`), followed by a `figcaption`;
    - `screen.getByText('Sales doubled after the redesign', { selector: 'figcaption' })` exists and has the `lang` attribute that `digestLang('zh-Hans')` gives;
    - `within(container.querySelector('.item-images') as HTMLElement).queryByRole('img')` is `null`, so the text is not read a second time;
    - `expectAccessible(container)` passes.
  - `does not show an image without text`. The item has `images: [{ url: 'https://cdn.example/a.png', alt: '' }, { url: 'https://cdn.example/b.png', alt: '  ' }, { url: 'https://cdn.example/c.png', alt: 'Chart' }]`. Exactly one `figure` is rendered, its `img` `src` is `https://cdn.example/c.png`, and its caption is "Chart". With only the first two images, no `.item-images` element is rendered.
  - `hides a failed image together with its caption`. Two images with texts "Growth chart" and "Interface screenshot". After `fireEvent.error` on the first `img`, `queryByText('Growth chart')` is `null`, and "Interface screenshot" is still shown in a `figcaption`.
  - `shows no caption when images are turned off`. Render the item with `images: [{ url: 'https://cdn.example/chart.png', alt: 'Chart' }]` and without `showImages`: `screen.getByText('Chart', { selector: 'figcaption' })` exists. Unmount it, and render the same digest with `showImages={false}`: `container.querySelector('figcaption')` is `null`.

  Change these existing assertions, and nothing else in them:
  - in `DigestArticle.test.tsx`, `renders chosen images in order between the summary and Also read, and hides a failed figure`: `expect(imgs.map(img => img.alt)).toEqual(['Growth chart', 'Interface screenshot'])` becomes `expect(imgs.map(img => img.getAttribute('alt'))).toEqual(['', ''])` followed by `expect(Array.from(block.querySelectorAll('figcaption')).map(caption => caption.textContent)).toEqual(['Growth chart', 'Interface screenshot'])`; and `expect(screen.getByRole('img', { name: 'Interface screenshot' })).toBeInTheDocument()` becomes `expect(screen.getByText('Interface screenshot', { selector: 'figcaption' })).toBeInTheDocument()`;
  - in `frontend/src/pages/DigestView.test.tsx`, `await screen.findByRole('img', { name: 'Growth chart' })` becomes `await screen.findByText('Growth chart', { selector: 'figcaption' })`, and `expect(screen.getByRole('img', { name: 'Growth chart' })).toBeInTheDocument()` becomes `expect(screen.getByText('Growth chart', { selector: 'figcaption' })).toBeInTheDocument()`;
  - in `frontend/src/pages/Home.test.tsx`, `expect(screen.getByRole('img', { name: 'Growth chart' })).toBeInTheDocument()` becomes `expect(screen.getByText('Growth chart', { selector: 'figcaption' })).toBeInTheDocument()`.

  Verify: the four new tests fail on the current code, and so do the changed assertions. `grep -rn "getByRole('img'\|findByRole('img'" frontend/src`, run from the repository root, prints nothing and exits 1.
- [x] 4.2 In `frontend/src/components/DigestArticle.tsx`, change `ItemImages` as in design D4: it receives the digest's `lang`, shows only images whose `alt` has text after trimming, renders each as `<figure>` with `<img alt="" …>` (keeping `loading="lazy"`, `decoding="async"`, `referrerPolicy="no-referrer"`, and `onError`) and `<figcaption lang={lang || undefined}>{image.alt}</figcaption>`, hides a failed figure with its caption, and renders nothing when no image is left. `DigestArticle` passes `lang={lang}`. In `frontend/src/styles/components.css`, next to `.item-images` (`components.css:122-124`), style the caption as secondary text like `.also-read` (`color: var(--muted)`, a smaller size, a small top margin, `overflow-wrap: anywhere`), so a long caption wraps inside the column.

  Verify:
  - `npx vitest run src/components/DigestArticle.test.tsx src/pages/DigestView.test.tsx src/pages/Home.test.tsx` passes in `frontend/`;
  - mutations U1–U5 each fail the tests named in design "Testing". Restore the code after each. There, "the caption test" and "the caption language test" are both `shows each image's text once, as its figure's caption` (its `alt` and `lang` assertions), "the image-without-text test" is `does not show an image without text`, and "the failed-image test" is `hides a failed image together with its caption`;
  - `npm test -- --run` and `npm run build` pass in `frontend/`.

## 5. Checks and report

- [x] 5.1 Run the full checks:
  - `uv run --offline pytest` in `backend/` (record the count);
  - `npm test -- --run` and `npm run build` in `frontend/` and in `extension/`, with Node 22.17.1 (record the counts);
  - `DO_NOT_TRACK=1 openspec validate improve-digest-image-captions --strict`;
  - `git diff --check`.

  Do not run `docker build`, `scripts/docker-smoke.sh`, or any Docker command, and do not touch port 8800: Claude Code runs the Docker smoke and the live checks at review.

  Write the commands and their real results to `docs/process/test-report-improve-digest-image-captions.md`:
  - each new or changed test, and the mutations that it kills;
  - mutations C1–C6, S1–S4, R1–R2, H1, P1–P5, and U1–U5, with their results;
  - the Docker smoke and the checks in design D5 steps 1–2, listed as not performed (Claude Code runs them at review), and D5 step 3 as the user's check after the merge.

  Add your entry to `docs/process/ai-usage-log.md` after the latest entry, with a faithful prompt excerpt. Leave out the session id; Claude Code adds it at review.

  Verify: every command that ran passes, and the report has the actual numbers.

## 6. Fix round 1 (review findings)

Claude Code's review of `1bc7959..ce72409` confirmed two behavior defects and one spec scenario without a test:
- the reading view throws on a saved image whose `alt` is missing or not a string, so the whole digest fails to render (`DigestArticle.tsx:41` calls `image.alt.trim()`; before this change the same data rendered);
- a formula address on `latex.codecogs.com.` (with the trailing dot that DNS accepts) stays a candidate;
- no test covers the size rule for `media:thumbnail`, which content-collection's "Small stated size" names.

- [ ] 6.1 Write these tests:
  - in `backend/tests/test_feeds.py`, add two rows to the parametrize table of `test_is_formula_image`: `("https://latex.codecogs.com./png.image?a%2Bb", True)` and `("https://LATEX.CODECOGS.COM./svg.latex?x", True)`. Both fail on the current code, because the host check keeps the trailing dot.
  - in `backend/tests/test_discovery.py`, `test_small_media_thumbnails_are_not_candidates`, following `test_formula_and_small_images_are_not_candidates`: parse `image_feed("<p>Text</p>", media="<media:thumbnail url='https://cdn.example/small.jpg' width='64' height='64'/><media:thumbnail url='https://cdn.example/large.jpg' width='480' height='360'/>")`. The entry's image addresses are exactly `["https://cdn.example/large.jpg"]`. This test passes on the current code, because the rule is implemented but untested; mutation M3 in 6.3 shows that it can fail.
  - in `frontend/src/components/DigestArticle.test.tsx`, `does not fail on a saved image without alt text`, following `does not show an image without text`: the item's images are `[{ url: 'https://cdn.example/a.png' }, { url: 'https://cdn.example/b.png', alt: null }, { url: 'https://cdn.example/c.png', alt: 'Chart' }]`, cast with `as unknown as { url: string; alt: string }[]`, because a saved digest comes from the server unchecked. The digest renders; exactly one `.item-images figure` is shown, its `img` has `src` `https://cdn.example/c.png`, and `screen.getByText('Chart', { selector: 'figcaption' })` exists. It fails on the current code with a `TypeError` from `trim`.

  Verify: the two new formula rows and the frontend test fail on the current code as stated, and the thumbnail test passes. Change no existing test.
- [ ] 6.2 Fix both defects:
  - in `backend/src/catchup/sources/feeds.py`, `is_formula_image` compares the host without a trailing dot: `(parts.hostname or "").lower().rstrip(".") == "latex.codecogs.com"`;
  - in `frontend/src/components/DigestArticle.tsx`, `ItemImages` shows only images whose `alt` is a string with text after trimming: `typeof image.alt === 'string' && image.alt.trim()`. Change nothing else in the component.

  Then run the tests of 6.1, all of `backend/tests/test_feeds.py` and `backend/tests/test_discovery.py`, and `npx vitest run src/components/DigestArticle.test.tsx` in `frontend/`, and watch them pass.
- [ ] 6.3 Run these mutations one at a time, inspect each result before the next, restore the code after each by editing the file back, and confirm the restore with `git diff`:

  | Mutation | Change | Expected failing test |
  | --- | --- | --- |
  | M1 | `.rstrip(".")` removed from `is_formula_image` | the two new rows of `test_is_formula_image` |
  | M2 | the `typeof image.alt === 'string'` check removed from `ItemImages` | `does not fail on a saved image without alt text` |
  | M3 | in `_entry_images` (`feeds.py`), the `media_thumbnail` candidate's `width` and `height` set to `None` | `test_small_media_thumbnails_are_not_candidates` |
- [ ] 6.4 Run the commands of task 5.1 again, with the same rules: no `docker build`, `scripts/docker-smoke.sh`, or any Docker command, and do not touch port 8800. Add a "Fix round 1" section to `docs/process/test-report-improve-digest-image-captions.md` with the red and green results of 6.1 and 6.2, M1–M3, and the commands' counts. Add one Droid entry for this round to `docs/process/ai-usage-log.md`, after the latest entry, with a faithful prompt excerpt; leave out the session line, which Claude Code adds at review.

  Verify: every command passes, and the report has the actual numbers.
