# Design

Full RePPIT change for issue #48. The research is in `research.md`, the motivation in `proposal.md`, and the requirements in the spec deltas.

- **Chosen:** Proposal 1, "Collect bounded item context; the summary call judges relevance". The user chose it on 2026-10-19, with one change: more than 3 links per item, and a later user setting for deep or shallow crawling.
- **Rejected:** Proposal 2, "Let the model pick which links to read, at summary time". It is recorded under D9.

## Context

- **Parsing** (`backend/src/catchup/sources/feeds.py`).
  - `parse_feed` builds `FeedEntry(identity_key, link, title, published_at, content_text, has_audio, transcripts)` (`:123-130`, `:192`).
  - `plain_text` keeps only text nodes (`:87-99`).
  - feedparser exposes `comments`, `wfw_commentrss`, `slash_comments`, and `author` (`dc:creator`).
- **Collection.**
  - `check_source` stores new items (`collection.py:57-142`).
  - `article_text` fetches the item's own page when the feed text is short, and keeps the feed text when the extraction misses it (#47, merged).
  - Source confirmation stores the first items too (`api/sources.py:89-161`).
- **The run** (`digest/runner.py`).
  - One `HostSpacer` per run (`:199`).
  - Sources are checked in order (`:204-209`).
  - Then the YouTube caption pass (`:210`), then `select_pending` and `SummaryInput(...)` (`:212-225`).
  - Summaries are recorded on the item by `record()` (`:267-278`), and the snapshot is built in one transaction (`:301-377`).
- **Summaries.**
  - `summary_messages(title, text, language)` (`llm/prompts.py:24-36`).
  - Splitting by a budget in characters (`digest/summarize.py:32-97`).
  - Four workers (`:120`).
  - Output `{"summary": ...}`.
- **Fetching.** `safe_fetch` allows public addresses only, 5 MiB, 30 s, and 5 redirects, with a `budget` counter (`net/safe_fetch.py:100-192`). `HostSpacer` keeps 1 s per host, under a lock (`net/host_spacing.py`). Nothing reads robots.txt.
- **Storage.** The migration head is `0003_digest_snapshot`. `Item` (`models.py:73-92`) and `DigestItem` (`:152-167`) carry one link per item.

## Goals / Non-Goals

**Goals:**
- Read a short post's related linked pages, and the author's replies in its comments.
- Let the summary judge relevance, and cite what it used.
- Bound every fetch, and never let context fail a run.

**Non-Goals:**
- The user-facing depth setting (a follow-up issue).
- X and login-only sites (#41).
- Comment systems loaded by script.
- Podcast and YouTube items.
- Re-gathering context for items that are already summarized.
- Changing the item's own article fetch.

## Decisions

### D1. What parsing keeps
- **Links.** `FeedEntry` gets `links: tuple[EntryLink, ...]`, where `EntryLink(url, text)`. They are taken from the same HTML that `plain_text` reads, in body order, and resolved against the entry link. Duplicates are dropped.
- **Comment pointers.** `FeedEntry` also gets `comments_url`, `comment_feed_url`, `comment_count` (an int, or None), and `author`.
- **Storage.** These are stored on `Item` as new columns:
  - `entry_links`: a JSON list of `{url, text}`;
  - `comments_url`, `comment_feed_url`, `comment_count`, `entry_author`;
  - `context_status`: `null` (not gathered), `gathered`, or `none` (nothing to gather).

  `check_source` and confirmation set them for new items. Existing items keep `null` pointers and get no context, because their links were never stored.

### D2. Link rules (`context/links.py`)
- **`related_links(item_link, site_url, links, limit)`** returns the first `limit` links in order, after dropping:
  - the item's own URL, ignoring the fragment and trailing slash;
  - same-site paths that start with `/tag/`, `/tags/`, `/category/`, `/categories/`, `/author/`, `/page/`, `/search`, or `/archive`;
  - share or login-scoped URLs (`claude.ai/code/`, `chatgpt.com/share/`, `/share?`, `/login`);
  - hosts `x.com`, `twitter.com`, and `mobile.twitter.com`;
  - URLs ending in an image extension or `.pdf`;
  - schemes other than `http` and `https`.
- **Kept:** news.ycombinator.com discussions, GitHub, docs, and other articles.
- **The default limit,** `CATCHUP_LINKS_PER_ITEM`, is 8. The user asked for more than 3. Simon Willison's median entry has 8 links, about half of them tags, so 8 covers nearly every related link in the research sample.

### D3. robots.txt (`context/robots.py`)
- **`RobotsCache`** lives for one run. Per host, it fetches `/robots.txt` once through `safe_fetch`, with a 512 KB limit, and the same spacer.
- **Matching.** It uses `urllib.robotparser`, matching CatchUp's User-Agent product token `CatchUp`.
- **Missing or unreadable files.** A missing file (404) or a fetch error means allowed. A 401 or 403 means disallowed, following the robots.txt convention.
- **Scope.** It is used only for context fetches (D4, D5), not for feeds or the item's own article. The `robots.txt` request counts against the per-run fetch limit.

### D4. The context pass (`context/gather.py`, called from `digest/runner.py`)
- **When.** It runs after the caption pass and before `select_pending`, while the status is `collecting`.
- **Which items.** Pending items of `feed`-kind sources with `context_status IS NULL`. It also covers text posts in podcast sources, the same items for which `article_text` runs.
- **The plan.** Count the planned fetches (related links, plus one post page for items with `comment_count > 0`). Store the total on the run as `context_total`, and increment `context_done` as fetches finish.
- **Fetching.** Each fetch goes through `safe_fetch(url, spacer=spacer, budget=budget)`, with one shared budget of `CATCHUP_CONTEXT_FETCHES_PER_RUN` (default 60) and the 5 MB limit. robots.txt is checked first.
- **Linked pages.** The text comes from trafilatura's `extract`, cut to 3,000 characters. An item's linked context stops at 16,000 characters. The title is the page `<title>`, or else the anchor text.
- **The result.** Each part is stored as an `ItemContext` row. The item becomes `gathered` when anything was stored, or `none` otherwise. Each item's rows are committed together, so a crash keeps what was done.
- **Failures** (`FetchError`, robots.txt refusal, extraction errors, an empty extraction) are skipped. A limit reached mid-run leaves the remaining items at `null`, so a later run gathers them.

### D5. Author replies (`context/comments.py`)
- **Primary path.** Fetch the post page (`item.link`). Parse `div.comment` or `li.comment` elements whose class contains `bypostauthor`. If there are none, match those whose `comment-author-<login>` or `.fn` text equals `entry_author`.
- **Each reply** keeps its text from `.comment-content`, plus its parent comment's text (the nearest ancestor comment, or the `In reply to` link target), each cut to 600 characters.
- **The comment feed** (`comment_feed_url`) is the fallback when the page has no comment markup. It holds the newest 10 items, matched by `dc:creator`. Pingback items are skipped.
- **Limits:** at most 10 replies and 4,000 characters, stored as one `author_replies` context row whose title is "Author replies (n)".

### D6. Storage, migration `0004_item_context`
- **`items`:** the D1 columns.
- **New table `item_contexts`:** `id`, `item_id` (FK, cascade), `ref` (`L1`…`Ln`, `A1`), `kind` (`link` or `author_replies`), `url`, `title`, `text`, `position`, and `used` (bool, default false).
- **`digest_items`:** `context_links`, JSON, nullable.
- **`digest_runs`:** `context_total` and `context_done`, ints, default 0.

### D7. Summaries
- **The prompt.** `summary_messages` gains an optional `context` list. After `Content:`, the user message adds blocks such as `Context L1 — linked page: <title> (<host>)\n<text>` and `Context A1 — author replies\n<text>`.
- **New system-prompt rules:**
  - use context only where it relates to the item;
  - never summarize a context part on its own;
  - list the refs of the parts that were used.
- **The output:** `{"summary": "...", "used": ["L1"]}`.
- **Splitting.** For split items, the parts carry the item text only, and the context goes to the combine call. The splitting budget subtracts the context's length, with a floor of 2,000 characters.
- **Recording.** `record()` validates `used` against the item's refs, and sets `ItemContext.used` for the matching rows, clearing the others. A cached summary keeps its `used` flags.

### D8. Snapshot, API, UI
- **Snapshot.** The runner copies `[{title, url, kind}]` of the used contexts, in ref order, into `DigestItem.context_links`.
- **API.** `api/digests.py` returns `also_read` per summarized item: `[]` when there is none, and `[]` for older digests.
- **Reading layout** (`DigestArticle.tsx`). When `also_read` is not empty, the item renders `<p class="also-read">Also read: <a …>title</a> · …</p>` after the summary, in the summary column. The links use `target="_blank" rel="noopener noreferrer"`, as the title link does.
- **Progress** (`Home.tsx`). While the status is `collecting`, all sources are checked, and `context_total > 0`, the progress label is "Linked pages read: n of N".

### D9. Alternatives considered
- **Proposal 2: model-picked links at summary time.** Rejected:
  - It needs an extra model call for every item with links. All 30 of Simon Willison's entries have links.
  - It moves network fetches into the summarizing stage, across 4 workers.
  - Its selection is not deterministic.
  - It re-fetches after a failed run, because nothing is stored before the summary.

  It may come back as the "deep" level of the later depth setting.
- **Reusing the item's article fetch for comments.** Rejected for simplicity. The context pass fetches the post page itself when the feed reports comments. In the research sample, the posts with comments (Tao) have full feed text, so `article_text` never fetched them.

## Risks / Trade-offs

- **[Token cost]** Up to 16,000 characters of linked context plus 4,000 of replies per item. → Limits per page and per item. Tokens are already shown per run. The depth setting will let users lower it.
- **[Slower runs]** Up to 60 fetches, with 1 s per host. GitHub-heavy entries share one host. → The per-run limit; the progress label; items left over are gathered next run.
- **[Link rules keep noise or drop useful links]** → The model is told to ignore unrelated context. The rules are constants, with tests.
- **[Comment markup varies]** Only WordPress-style server-rendered comments, and the comment feed's newest 10, are read. → A known limit; the rule is to never guess.
- **[robots.txt]** Respecting it can skip useful pages. Not respecting it would be impolite. → Respected for context fetches only.
- **[Prompt injection from linked pages]** → The system prompt already treats content as data. Context gets the same rule, and the output is validated JSON.

## Migration Plan

- Migration `0004` adds nullable columns, a table, and int columns with defaults. Existing items have `context_status = null` and no stored links, so they gather nothing.
- Rollback: downgrade drops the table and the columns, and older code ignores them.
- Testing notes:
  - Every fetch in tests goes through `respx` with the autouse DNS block.
  - robots.txt and comment HTML use small invented fixtures shaped like the research's examples.
  - The model is `FakeModel`.
  - A live check at review uses a local instance with a stub model, on Simon Willison and Terry Tao. Real-model token totals are compared with and without context.

## Open Questions

- The depth setting's levels and defaults (follow-up issue): for example, shallow is 3 links, normal is 8, deep is 8 plus model-picked links.
- Should "Also read" also appear under Creator updates? Not now: those items have no summary.
