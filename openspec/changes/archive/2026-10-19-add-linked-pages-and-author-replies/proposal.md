# Proposal

## Why

Many website posts are short notes whose point lives elsewhere. For example, the `llm-tools-datasette 0.1.1` post links to its GitHub release, `pydantic/httpx2`, and the LLM 0.33 changelog. On blogs with comments, the author often adds context in replies to readers. CatchUp reads neither (issue #48, found in user testing on 2026-10-19, items F7 and F8). The research (`research.md`) found:
- **Links are discarded at parse time.** `plain_text` (`backend/src/catchup/sources/feeds.py:87-99`) drops every `href`. `FeedEntry` (`:123-130`) has no field for links, the author, or comments, though feedparser exposes `comments`, `wfw_commentrss`, `slash_comments`, and `author`.
- **The model receives only the title and `content_text`** (`backend/src/catchup/llm/prompts.py:24-36`), and a digest item cites one link (`models.py:152-167`).
- **What the user's sources offer:**
  - Simon Willison's entries have a median of 8 links, about half of them `/tags/` pages.
  - Terry Tao's WordPress feed exposes `wfw:commentRss` and `slash:comments`.
  - His post HTML marks his own comments with `bypostauthor`.

## What Changes

- **Keep each website entry's links and comment pointers.**
  - The links are kept in body order, with their anchor text.
  - The comment pointers are the comments URL, the comment feed URL, the comment count, and the entry author.
- **A context pass, after the sources are checked and before the run picks its items.** For each pending website item whose context has not been gathered, CatchUp reads:
  - **Related links** (user decision, 2026-10-19: "more than three links"):
    - up to **8** per item by default, chosen by rules: no tag, category, archive, or search pages; no login-scoped or share pages; no images or PDFs; no x.com or twitter.com, which need a login (#41);
    - Hacker News discussion links are kept;
    - each page's extracted text is cut to 3,000 characters, with at most 16,000 characters of context per item.
  - **The author's own replies** in the post's comments, when the feed reports comments:
    - comments marked `bypostauthor`, or whose author matches the entry author, each with the comment it answers;
    - at most 10 replies and 4,000 characters;
    - when the post HTML has none, the comment feed is the fallback.
  - **Limits:**
    - at most **60** context fetches per run;
    - every fetch goes through the safe fetcher with host spacing;
    - each fetch honors robots.txt for CatchUp's User-Agent. This applies only to these new fetches, not to the item's own article fetch.
  - **Failures.** A failed or refused fetch is skipped and never fails the run.
  - **Gathered once.** Context is stored, and later runs reuse it.
- **Summaries use the context, and say what they used.**
  - Context goes to the summary call as labeled sections after the item's text.
  - The model uses only the material that relates to the item, never summarizes a linked page on its own, and returns the refs it used.
  - Unknown refs are dropped. The summary budget counts the context.
- **The digest cites the used context.** Each item shows "Also read:", followed by the titles of the linked pages and author replies the summary used, each linked to its source. The snapshot keeps them, so a saved digest shows the same links.
- **Run progress.** While the context pass runs, the run bar shows "Linked pages read: n of N".
- **Settings, for now in the environment:**
  - `CATCHUP_LINKS_PER_ITEM`, default 8;
  - `CATCHUP_CONTEXT_FETCHES_PER_RUN`, default 60;
  - `CATCHUP_AUTHOR_REPLIES`, default on.
- **Out of scope:**
  - the user-facing deep or shallow setting, a follow-up issue (user, 2026-10-19: "later we can give users the option to choose deep or shallow crawling");
  - X and other login-only sites (#41);
  - comment systems loaded by script, such as Disqus;
  - podcast and YouTube items, which are summarized only from transcripts (D-013);
  - re-gathering context for items that are already summarized.

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- **`content-collection`.** New requirement "Gather related context for website items": what is kept, the link rules, the limits, robots.txt, author replies, failure tolerance, and gathering once.
- **`digest-generation`:**
  - New requirement "Use related context in summaries".
  - "Citations come from stored data": context links come from stored context.
  - "Show run progress and per-source outcomes": the context-pass progress.
- **`digest-history`.** "Reopen a saved digest": a saved digest keeps each item's "Also read" links.
- **`user-interface`.** "Digest reading layout": items show their "Also read" links.

## Impact

- **Backend:**
  - `sources/feeds.py`, for links and comment pointers;
  - new modules for link rules, robots.txt, and comment parsing, under `backend/src/catchup/context/`;
  - `collection.py` and `api/sources.py`, which store the pointers;
  - `digest/runner.py`, for the context pass, the progress fields, and the snapshot;
  - `digest/summarize.py` and `llm/prompts.py`, for the context sections and the `used` refs;
  - `models.py`, with migration `0004`: the item's link and comment fields, a new `item_contexts` table, and the snapshot's `context_links`;
  - `config.py`, for the three settings;
  - `api/digests.py`, for `also_read`.
- **Frontend:** `components/DigestArticle.tsx` and its CSS, for "Also read"; `pages/Home.tsx`, for the progress label.
- **Tests:**
  - new backend tests for parsing, rules, robots.txt, comments, the context pass, summaries, the snapshot, and the API;
  - frontend tests for "Also read" and progress;
  - updates to tests that pin item dicts (`test_digest_history.py`), the migration head (`test_db.py:63`), and item children (`DigestView.test.tsx:248-276`).
- **Costs.** Runs do more fetching, and items with context cost more tokens. Tokens are already shown per run.
