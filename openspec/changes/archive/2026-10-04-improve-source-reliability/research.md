# Research: Source reliability — Reddit link posts (#2) and rate limiting (#3)

- Date: 2026-10-04
- Query: How does CatchUp currently fetch, discover, parse, confirm, collect, and extract article text, and what external facts govern Reddit link posts, Reddit rate limits, and HTTP 429 handling?
- Git ref: main @ 2a179d7
- Change: `improve-source-reliability`
- Issues: [#2](https://github.com/Zhuoang2/catchup/issues/2), [#3](https://github.com/Zhuoang2/catchup/issues/3)

## Summary

All network access to sources goes through one function, `safe_fetch`. It creates a fresh `httpx.Client` per call with no custom headers, so requests carry httpx's default User-Agent `python-httpx/0.28.1`. It has no handling for 429 or `Retry-After`, and it does no caching. Adding a source fetches the feed at least twice in quick succession: once during preview (`discover`) and again on confirm. Pending entries with short text then trigger article fetches. Feed text is converted to plain text by an HTML parser that keeps only text nodes, so link targets inside entry content (such as Reddit's `[link]` anchor) are not retained. A Reddit entry's `<link>` points to its comments page, which is what article extraction fetches today. Externally, Reddit has announced that it will stop supporting RSS feeds on 2026-11-13. Its documented API rules require OAuth and a specific User-Agent format and say unidentified traffic may be throttled or blocked.

## Detailed Findings

### Fetching (`safe_fetch`)
- Signature `safe_fetch(url, *, same_origin=None, budget=None) -> FetchResponse` — `backend/src/catchup/net/safe_fetch.py:60`.
- Opens a new `httpx.Client(follow_redirects=False, trust_env=False)` per call, with no `headers=` argument — `safe_fetch.py:70`. The repository sets no User-Agent anywhere (`grep` for `User-Agent`/`headers=` in `backend/src` finds nothing). httpx 0.28.1's default header is `python-httpx/0.28.1` (checked by instantiating `httpx.Client()`).
- Wall-clock deadline of 30 s per call (`FETCH_DEADLINE_SECONDS`) — `safe_fetch.py:13,62-68`; per-attempt timeouts — `safe_fetch.py:84-87`.
- Non-2xx responses after redirects go through `response.raise_for_status()` — `safe_fetch.py:104`. They surface as `FetchError("fetch_failed", "The source could not be fetched.", status_code)` — `safe_fetch.py:131-134`. Response headers, including `Retry-After`, are not read or returned. `FetchResponse` carries only `url`, `content`, `content_type`, and `status_code` — `safe_fetch.py:24-29`.
- No retry, backoff, or response caching exists in `safe_fetch`.
- Call sites (6):
  - `discovery.py:50` (pasted URL)
  - `discovery.py:72` (declared feed)
  - `discovery.py:84` (probing, with `same_origin` and `budget`)
  - `api/sources.py:86` (confirm)
  - `collection.py:33` (feed check during runs)
  - `collection.py:17` (article extraction)

### Discovery and preview
- `discover(url)` fetches the pasted URL — `backend/src/catchup/sources/discovery.py:50`. If that isn't a feed, it fetches a declared feed (`discovery.py:68-75`) or probes up to 8 same-origin paths (`discovery.py:77-90`).
- For `https://www.reddit.com/r/programming/`, the first probe candidate is `<path>.rss`, giving `/r/programming.rss` — `discovery.py:41-46`. During manual verification this was the feed found (`docs/process/test-report-add-core-digest-flow.md:127-133`).
- `preview` returns the feed URL, site URL, title, notice flag, and up to 5 recent entries. Nothing is persisted, and the fetched feed is not kept for confirm — `backend/src/catchup/api/sources.py:57-80`.

### Confirm
- `confirm` fetches `data.feed_url` again and parses it — `api/sources.py:86`. A fetch error becomes a 422 with the `FetchError` code — `api/sources.py:30-31,87-88`.
- First-add marking (7 days, at most 5 pending) — `api/sources.py:95-102`. Pending entries get `article_text(...)`, which may fetch each entry's link — `api/sources.py:113-116`.
- Requests for one Reddit source are therefore: 1 page fetch + 1 probe (preview), then 1 feed fetch (confirm), then up to 5 article fetches of Reddit comment pages for short pending entries.

### Feed parsing and plain text
- `plain_text(html)` collects only `handle_data` text — `backend/src/catchup/sources/feeds.py:18-30`. Anchor `href` values are discarded, so `[link]` and `[comments]` survive only as the literal words.
- Entry content uses `entry.content[0].value`, else `entry.summary` — `feeds.py:71-73`.
- Entry `link` is `entry.link` if http(s), else the feed URL — `feeds.py:75-80`. For Reddit, `entry.link` is the comments page (see external facts).
- Identity is `entry.id`, else link, else a hash of title and date — `feeds.py:81-83`. For Reddit, `entry.id` is the post fullname (e.g. `t3_…`).

### Collection during runs and article extraction
- The runner checks sources sequentially, one `check_source` per source — `backend/src/catchup/digest/runner.py:89-94`.
- `check_source` fetches the feed once — `backend/src/catchup/collection.py:33`. On `FetchError` it records `failed` with `http_status=exc.status_code` — `collection.py:35-46` (this is how the 429 was recorded in manual verification).
- `article_text(entry, fallback_links, threshold)` behaves as follows — `collection.py:13-27`:
  - It returns the feed text when that text is at least `CATCHUP_SHORT_TEXT_CHARS` (default 500, `backend/src/catchup/config.py:26`) or when the link is a fallback link.
  - Otherwise it fetches `entry.link` with `safe_fetch` and extracts text with trafilatura.
  - On any failure it falls back to the feed text.
  - For a Reddit link post, the fetched page is the Reddit comments page, not the linked article.
- The summary prompt treats content as data and adds the substance rules — `backend/src/catchup/llm/prompts.py:24-33`. With Reddit link posts, the summaries said the item had no substantive content (`test-report-add-core-digest-flow.md:179`).

### Evidence from manual verification (2026-10-03)
- Run 1: the Reddit check returned HTTP 429, recorded as `failed` with `http_status=429` — `docs/process/test-report-add-core-digest-flow.md:139`.
- Run 2: Reddit returned 200 — `test-report…md:149`.
- Re-test:
  - Preview succeeded, but the confirm right after it failed with `fetch_failed` (rate limited); confirming 15 s later worked — `test-report…md:172`.
  - The check during run 3 hit 429 again, while the items recorded at confirm were still delivered — `test-report…md:176`.
- Link-only Reddit posts were summarized as having no substantive content — `test-report…md:159,179`.

### Tests touching this area
- `backend/tests/test_discovery.py:155` — `test_reddit_path_dot_rss_probe` (probing finds `<path>.rss`).
- There are no tests for User-Agent headers, 429 handling, or `Retry-After` in source fetching. The 429 tests in `backend/tests/test_llm_client.py:118,149` cover the model client, not `safe_fetch`.

### External facts (verified 2026-10-04)

**Reddit RSS shutdown**
- TechCrunch, Sarah Perez, 2026-09-30, fetched directly:
  - Reddit is discontinuing all RSS feed support on **2026-11-13**.
  - Public API access ends **March 2027**.
  - Developers of approved third-party apps must register before **2027-01-12**.
  - Source: https://techcrunch.com/2026/09/30/reddit-is-killing-rss-feeds-ending-public-api-access-because-of-ai-bots/
- Reddit Help Center: "Reddit will stop supporting RSS feeds on November 13, 2026."
  - Article 54058188280852, edited 2026-09-30, read through the help center JSON API by a subagent.
  - Direct fetch returned 403, so the full context is unverified. The page is about mod alerts; the scope of "all RSS" comes from the TechCrunch report.

**Reddit feed structure** (live, `/r/programming.rss` and `/r/AskProgramming.rss`, 2026-10-04)
- Atom; `<id>` = post fullname (`t3_…`); `<link href>` = comments page.
- `<content type="html">` = optional selftext `div.md`, then `submitted by <a>/u/X</a>`, then `<a href="URL">[link]</a>` and `<a href="COMMENTS">[comments]</a>`.
- Link posts: the `[link]` href is the external article.
- Self posts: the `[link]` href equals the comments URL.
- Some link posts also carry body text.

**Observed responses** (4 requests spaced ~25 s apart)

| Request | Status | Notes |
| --- | --- | --- |
| Descriptive UA | 200 | `x-ratelimit-used: 1`, `x-ratelimit-remaining: 0.0`, `cache-control: private, max-age=3600` |
| Descriptive UA, second feed | 200 | |
| Default curl UA | **403** | HTML "blocked by network security" page |
| Descriptive UA again | **429** | no `Retry-After` header |

The effect of the User-Agent could not be separated from per-IP throttling in this sample.

**Reddit Data API rules** (Data API Wiki, edited 2026-05-11, https://support.reddithelp.com/hc/en-us/articles/16160319875092)
- Clients must authenticate with OAuth. "We can and will freely throttle or block unidentified Data API users."
- User-Agent format: `<platform>:<app ID>:<version string> (by /u/<reddit username>)`. Default UAs "are drastically limited."
- 100 queries per minute per OAuth client.
- Rate-limit headers: `X-Ratelimit-Used`, `X-Ratelimit-Remaining`, `X-Ratelimit-Reset`.
- "Traffic not using OAuth or login credentials will be blocked."
- RSS is not mentioned. No limit is documented for unauthenticated RSS.

**HTTP 429 and `Retry-After`**
- RFC 6585 §4: 429 = too many requests in a given amount of time. The response MAY include `Retry-After`. 429 responses MUST NOT be stored by a cache.
- RFC 9110 §10.2.3: `Retry-After = HTTP-date / delay-seconds`, where delay-seconds are non-negative decimal seconds. HTTP-date recipients must accept IMF-fixdate, RFC 850, and asctime formats.

## Code References
- `backend/src/catchup/net/safe_fetch.py:60-137` — the only fetch path; no headers, no 429/`Retry-After` handling, headers not returned
- `backend/src/catchup/sources/discovery.py:49-90` — preview-time fetches, declared feeds, probing
- `backend/src/catchup/api/sources.py:57-140` — preview (no persistence) and confirm (re-fetch, first-add, article extraction)
- `backend/src/catchup/sources/feeds.py:18-30,63-93` — plain-text conversion drops hrefs; entry link and identity
- `backend/src/catchup/collection.py:13-27,30-86` — article extraction from `entry.link`; per-source check and failure recording
- `backend/src/catchup/digest/runner.py:89-94` — sequential source checks
- `backend/src/catchup/config.py:26` — `CATCHUP_SHORT_TEXT_CHARS` default 500
- `backend/tests/test_discovery.py:155` — Reddit probe test

## Current Specs
- `source-management`:
  - "Preview a source from a pasted URL" (`openspec/specs/source-management/spec.md:8`)
  - "Confirm and save a source" (`:42`): records the feed's entries on confirm; first-add 7 days / 5
  - "Fetch user-supplied URLs safely" (`:60-75`): SSRF guard, timeouts, size limit. It says nothing about User-Agent, rate limits, or retries.
- `content-collection`:
  - "Check every source on each run" (`openspec/specs/content-collection/spec.md:8-18`): a failed check is never `no_new_items`
  - "Keep article text for summarization" (`:55-60`): when feed text is short, fetch "the linked article" via the safe fetcher and fall back to feed text. It does not define which link is "the linked article" when an entry carries both an external link and a comments link.
- `digest-generation` "Summaries focus on substance": items without substantive content are described in one sentence.

## Related History
- Issues #2 and #3 were created 2026-10-04 from the manual verification findings of `add-core-digest-flow` (archived at `openspec/changes/archive/2026-10-03-add-core-digest-flow/`).
- Requirement-change log entry, 2026-10-03: Reddit link posts, rate limits, and a thinking toggle were deferred to the next change — `docs/process/requirements-changes.md`.
