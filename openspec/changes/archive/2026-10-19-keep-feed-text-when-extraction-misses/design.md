# Design

Lean change for issue #47. See `proposal.md` for the motivation, and the `content-collection` delta for the requirement.

## Context

- **`article_text(entry, fallback_links, threshold, *, spacer)`** (`backend/src/catchup/collection.py:39-54`) returns `(text, origin)`:
  - It returns `(entry.content_text, "feed")` without fetching when the feed text is at least `threshold` characters long, or when the entry's link is one of `fallback_links`.
  - Otherwise it fetches `entry.link` with `safe_fetch`, and returns `(extracted.strip(), "article")` when trafilatura's `extract` gives non-empty text.
  - Every failure returns the feed text: a `FetchError`, empty extraction, or an extractor exception.
- **Callers:** the run-time check (`collection.py:99`, `:111`) and source confirmation (`api/sources.py:142`). `content_origin` matters only for `"transcript"` (`digest/summarize.py:75`). `"feed"` and `"article"` are not otherwise read.
- **`entry.content_text`** is plain text from `plain_text(description)` (`sources/feeds.py`). It can be empty.

## Decisions

### D1. When the extracted text covers the feed text
- **Words.** The feed text's words are its distinct runs of letters and digits, found with `\w+` and compared case-insensitively. Only runs of at least 3 characters count. A CJK run counts as one word.
- **Found.** A word is found when it appears anywhere in the extracted text, compared case-insensitively. Substring matching also works for CJK text, whose word boundaries differ between the feed and the page.
- **Covered.** The extracted text covers the feed text when at least 60% of the feed's words are found. A feed text with no counting word (empty, or only short tokens) is covered.
- **Example.** In #47 the feed text has 27 counting words ("switched", "httpx2", "plugins", "depending", …). The sidebar text contains one of them, "now", which is 4%, so it does not cover the feed text. This was checked on 2026-10-19. A normal excerpt is the article's opening, so nearly all its words are found.

### D2. What is stored
- **Covered:** the extracted text, with origin `"article"`, as today.
- **Not covered:** the feed text, a blank line, then the extracted text, with origin `"article"`.
- **The fallbacks,** feed text with origin `"feed"`, are unchanged.

### D3. Alternatives considered
- **Keep only the feed text when not covered.** Rejected. A feed whose text is a generic teaser ("Continue reading…") would lose a correctly extracted article.
- **Always combine the feed text and the extracted text.** Rejected. A normal excerpt would appear twice, costing tokens and repeating the opening.
- **Change trafilatura's settings.** Rejected. The default, `favor_recall`, and `favor_precision` all returned the same sidebar on the saved #47 page.
- **Detect sidebars (link lists, dates) in the extracted text.** Rejected as fragile and site-specific. Coverage needs no knowledge of page layouts.

## Risks / Trade-offs

- **[Noise reaches the model]** When the extraction misses the post, its noise (the sidebar) is still stored after the feed text. → The feed text comes first and carries the substance. In the #47 case the model then has the release note. Dropping the noise would need sidebar detection (D3).
- **[Threshold choice]** 60% and 3-character words are judgment calls. → The tests pin both boundaries. Both values are constants in one helper, so they are easy to tune.
- **[Paraphrased excerpts]** A feed excerpt that is a paraphrase, not the article's opening, may fall below 60%. → Then both texts are stored, so nothing is lost; there is only some repetition.

## Migration Plan

- No data change. The rule applies to items stored from now on, and existing items keep their stored text.
- Rollback is a revert.
