# Proposal

## Why

A digest item from Simon Willison's Weblog, `llm-tools-datasette 0.1.1` (18 Oct 2026), was summarized from the blog's sidebar, not from the post (issue #47, found while the user was testing on 2026-10-19). The summary said the entry "only gives the title and lists some recent article titles".
- **The feed text had the substance.** It is about 250 characters: switching LLM to httpx2 in LLM 0.33 broke plugins that used httpx without depending on it, and `llm-tools-datasette` is now fixed.
- **It was replaced.** The feed text is shorter than `short_text_chars` (default 500). So `article_text` (`backend/src/catchup/collection.py:39-54`) fetched the post page, and the extracted text replaced the feed text completely.
- **The extraction was the sidebar.** trafilatura returned "18th October 2026", "Recent articles", and four post titles (310 characters). The post's own text is in the page, but it was not extracted, with trafilatura's default, `favor_recall`, or `favor_precision` setting. This was reproduced locally on 2026-10-19 from the saved page.
- **The spec requires the replacement.** `content-collection`, "Keep article text for summarization", says that the stored text "is the extracted article text".

## What Changes

- **Use the extracted page text alone only when it covers the feed text.** It covers the feed text when most of the feed text's words appear in it (see `design.md`, D1). This is the usual case: a feed excerpt is the opening of the article.
- **Otherwise keep both.** The stored text is the feed text, then a blank line, then the extracted text. The feed's own words are never lost, and an article page whose feed only says "Continue reading" still reaches the model.
- **Unchanged:**
  - the threshold (`short_text_chars`);
  - the cases that skip the page fetch: a long enough feed text, or a link shared with the feed;
  - the fallbacks to the feed text: a failed or blocked fetch, an empty extraction, or an extractor error;
  - podcast and YouTube handling;
  - host spacing.
- **Both callers get the rule,** because both use `article_text`: run-time source checks, and adding a source (`backend/src/catchup/api/sources.py:142`).
- **Out of scope:**
  - Items that are already stored or summarized are not processed again.
  - Following the links inside an entry belongs to #48.
  - Changing or replacing the extractor.

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- `content-collection`, "Keep article text for summarization":
  - The extracted text replaces the feed text only when it covers it. Otherwise the feed text is kept first and the extracted text is added after it.
  - The "Feed provides only a short excerpt" scenario becomes the covered case.
  - New scenarios cover an extraction that misses the post, and an entry with no feed text.

## Impact

- `backend/src/catchup/collection.py`: `article_text`, and a small helper for the coverage check.
- `backend/tests/test_collection.py`: new tests. The existing replacement test is kept, with its article fixture changed to contain the excerpt.
- No API, database, frontend, or configuration change.
