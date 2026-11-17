# Design

## Context

The motivation is in proposal.md ("Why"). The code on `main` at `9d6866a`:

- **`safe_fetch`** (`backend/src/catchup/net/safe_fetch.py:136-237`) follows redirects itself (`follow_redirects=False`, at most 5). For each request URL, in this order, it:
  1. checks the deadline;
  2. checks `same_origin`, which only feed discovery uses;
  3. checks the address (`_check_address`), which also rejects a bad scheme, host, or port as `invalid_url`;
  4. takes one budget unit (`:161-164`). With no unit left, it raises `FetchError("fetch_failed", "Feed probing request limit reached.")`;
  5. waits for host spacing;
  6. sends the request.

  A 429, or a 503 with `Retry-After`, is retried once through the same steps (`:178-183`). Each `safe_fetch` call has a 30-second deadline, which starts when the call starts (`:141`).
- **Callers.** `safe_fetch` is called by:
  - `api/sources.py`, `collection.py`, and `sources/discovery.py`, without robots.txt;
  - `context/robots.py`, for robots.txt itself;
  - `context/gather.py`, for linked pages, post pages, and comment feeds.

  Only `discovery.py` and the context pass pass a budget. Discovery stops when its budget is 0, and skips to its next candidate on every other `FetchError` except `rate_limited` (`discovery.py:148-168`). One `safe_fetch` test matches the message "request limit" (`tests/test_safe_fetch.py:554`); no discovery test matches it.
- **`RobotsCache.allowed`** (`backend/src/catchup/context/robots.py:15-32`):
  - keys its cache by `f"{parts.scheme}://{parts.netloc}"`, as written;
  - returns `False` without a request when the budget is 0 (`:19-20`);
  - catches every `FetchError` from its own robots.txt request, including the budget error from a robots.txt redirect.
- **`gather.fetch`** (`gather.py:53-69`):
  1. returns `EXHAUSTED` at budget 0;
  2. asks robots;
  3. returns `EXHAUSTED` again if the robots request used the last unit;
  4. calls `safe_fetch`.

  It turns every `FetchError` into `EXHAUSTED` when the budget is 0 afterwards, and into `None` otherwise.
- **The per-item loop** (`gather.py:78-176`):
  - It skips an item when the budget is 0 and the item has no captured replies (`:79`). The item keeps `context_status` empty and is planned again next run.
  - `attempted` and `exhausted` (`:88-89`) are set on every path that reaches a fetch. So `attempted or exhausted` (`:168`) is true exactly when the item has links, comments, or captured replies. The `elif` (`:174`) covers the rest. Every item that passes `:79`, and still exists, gets `gathered` or `none`.
  - `context_done` counts a fetch that returned a response or `None` (`:101`, `:131`, `:145`), and not one that returned `EXHAUSTED`. So a request that used the last budget unit and failed, or was refused by robots.txt, is not counted.
- **Comments.**
  - `gather.py:134-147` calls `author_replies(page)`. It then parses the page again with the same comment-markup XPath as `comments.py:30-32`. Only when the page has no comment markup, and the item has a comment feed URL, does it fetch the feed (counting it in `context_total`) and call `author_replies(page, author, feed)`.
  - `author_replies` means to treat a page it cannot parse as having no markup (`comments.py:33-34`). But its `except` clause names `html.ParserError`, which `lxml.html` does not define; the class is `lxml.etree.ParserError`. For an empty or whitespace-only body, `fromstring` raises `ParserError`, and matching the clause then raises `AttributeError` (probe). `gather.py`'s `except Exception` (`:154`) logs it and skips the whole comment block, so the feed is not tried.
  - The feed is fetched even when the entry has no author, and `author_replies` then returns nothing (`comments.py:85-86`).
- **`context_status`.** The pass reads only `IS NULL` (`gather.py:27`), and the extension API resets it to `NULL` (`api/extension.py:157`). Tests assert `gathered` or `none` in 17 places.
- **Probes** on 2026-11-16, Python 3.12, with the locked httpx and lxml:
  - **`urlsplit`.**
    - `scheme` and `hostname` are lowercased.
    - `port` is `None` when absent. It is `443` for `:443`, and raises `ValueError` for `:99999` or `:abc`.
    - `hostname` drops user info, and drops the brackets of an IPv6 address.
    - A trailing dot and a Unicode host are kept as written.
  - **`httpx.URL`** lowercases a host name, drops a default port, and encodes a Unicode host as `xn--`. It keeps the letter case of an IPv6 address. So a respx route on `https://site.example/robots.txt` matches requests written as `https://SITE.example/robots.txt` and `https://site.example:443/robots.txt`.
  - **respx 0.23.1.** A route registered without a port matches every port, and the first matching route wins. A route on `https://site.example/...` also takes a request to `https://site.example:8443/...` unless a `:8443` route is registered before it.
  - **`RobotFileParser.can_fetch`** uses only the path of the URL. Host case and port do not matter.
  - **lxml.** `html.fromstring(b"")`, and `html.fromstring("<!-- c -->")`, raise `lxml.etree.ParserError`, whose bases are `LxmlError`, `Error`, and `Exception`. `lxml.html` has no `ParserError` attribute. Comment elements are hashable. Set and list membership agree for every ancestor, and new proxies for the same nodes are found in the set while the list holds them.

## Goals / Non-Goals

**Goals:**
- No request in a context fetch goes to a URL that robots.txt refuses, including redirect targets (#90).
- One robots.txt read per origin, however the URL spells the host's letter case or its default port (#90).
- One budget signal, caught in one place per item. No `EXHAUSTED` sentinel, no translations, no `attempted` or `exhausted` flags (#60, part 1).
- One comment-markup check per post page (#60, part 1).
- Linear membership tests in `author_replies` (#60, part 2).
- Every existing test passes unchanged, except the one that pins the old budget signal.

**Non-Goals:**
- #60 part 3 (the frontend poll helper) and the items in the 2026-11-01 comment on #60.
- Merging `gathered` and `none`. Both stay: tests and diagnosis read them, and merging would change a stored value for no behavior gain.
- Normalizing a trailing dot or an internationalized host name.
- Feed discovery's `same_origin` check. It still compares the raw `netloc`.
- Skipping the comment-feed request when the entry has no author.
- Robots checks for source checks and feed discovery. They do not use robots.txt today.

## Decisions

### D1. `safe_fetch` takes an optional per-request check

`safe_fetch` gains a keyword argument `allow: Callable[[str], bool] | None = None`.

- **When it is called.** For every request URL, including the start URL, each redirect target, and the single retry: after the address check, and before the budget unit is taken.
  - When it returns `False`, `safe_fetch` raises `FetchError("robots_disallowed", "robots.txt does not allow this page.")` without sending the request or taking a unit.
  - The callback may raise. Its exceptions, including `BudgetExhausted` (D3), propagate unchanged.
- **The deadline.** Time spent inside the callback does not count against the fetch's own deadline: `safe_fetch` moves its deadline forward by that time. A robots.txt request has its own 30-second deadline, as today. Without this, a slow robots.txt would use up the page's deadline, which today starts only after robots.txt is read.
  - `remaining()` is a closure that reads the enclosing `deadline` variable each time it runs. So reassigning `deadline` in `safe_fetch` is enough, with no `nonlocal`.
- **`gather.fetch`** passes `allow=robots.allowed`, and no longer asks robots itself.
- **Order.** The address check comes first, as today. So a URL with a blocked address, or a bad port, is refused before any robots.txt request. `allowed` then always gets a URL whose port parses.
- **Alternatives:**
  - **Follow redirects in `gather.py`.** Rejected: it would repeat the redirect limit, the address check, and the retry that `safe_fetch` owns.
  - **Check robots.txt for the final URL after the fetch.** Rejected: the refused target would already have been requested.
  - **Keep `gather.fetch`'s own robots check for the start URL, and check only redirect hops in `safe_fetch`.** Rejected: two call sites for one rule.

### D2. Origins are compared after normalizing the host and the default port

`RobotsCache.allowed` keys its cache with an origin built from `urlsplit`:
- the scheme;
- `hostname`, which is lowercased and has no user info. An IPv6 address is put back in brackets;
- `:port`, only when the port is not the scheme's default (80 for `http`, 443 for `https`).

The robots.txt URL is built from that origin, so all spellings fetch the same robots.txt URL.

- **Alternative: key by `hostname` alone.** Rejected: `http`, `https`, and a non-default port can serve different robots.txt files (RFC 9309, section 2.3).
- **Alternative: also strip a trailing dot, and convert a Unicode host to `xn--`.** Rejected for this change. Python's `idna` codec implements IDNA 2003, but httpx uses IDNA 2008, so the two can disagree. Both cases are rare.

### D3. One `BudgetExhausted` error

- **The error.** `safe_fetch.py` defines `class BudgetExhausted(FetchError)`. Its constructor takes no arguments and always sets today's code (`fetch_failed`) and message ("Feed probing request limit reached."), so `safe_fetch` and `RobotsCache` raise the same error. `safe_fetch` raises it at `:162-163`.
  - Discovery catches it as a `FetchError` and stops at its `if not budget[0]` check, as today.
  - `test_safe_fetch.py` still matches "request limit".
- **`RobotsCache.allowed`:**
  - raises `BudgetExhausted` when the budget is 0 and the origin is not cached yet (today it returns `False`);
  - lets a `BudgetExhausted` from its own robots.txt request propagate, without caching anything. This happens when a robots.txt redirect needs one more unit;
  - for every other `FetchError`, keeps today's rule (D1 of `fix-robots-errors-and-late-items`).
- **`gather.fetch(url)`** calls `safe_fetch(url, budget=budget, spacer=spacer, allow=robots.allowed)`.
  - It lets `BudgetExhausted` propagate.
  - It logs any other `FetchError` and returns `None`, and logs any other exception and returns `None`, as today.
  - It has no budget checks of its own.
- **The per-item loop.**
  - Keep the skip at `:79`. It is the module's one remaining budget check, and it is what leaves unreached items for the next run.
  - Wrap the item's link and comment fetches in one `try … except BudgetExhausted`. When it is raised, the item stops fetching, and keeps the rows already added.
  - Then add the captured replies, if any. They need no request.
  - Run the existing deleted-item check.
  - Then always run the status block: flush, clear the summary when contexts exist, and set `gathered` or `none`.

  `attempted`, `exhausted`, the `elif`, and `EXHAUSTED` are removed.
- **Extraction handlers.** The `except Exception` blocks around extraction must not catch `BudgetExhausted`. The comment block can now raise it from the feed function (D4). Put `except BudgetExhausted: raise` before `except Exception`, or keep the fetch outside the handler. No test can tell the difference today: the feed is the last fetch of an item, so swallowing the error there has the same outcome. The rule keeps the outcome right if a fetch is ever added after it.
- **Effect on progress.** "Linked pages read" (`context_done`) counts every fetch that finished: read, failed, or refused. A fetch stopped by `BudgetExhausted` is not counted, as today. Two edge cases change; the stored context and `context_status` do not:
  - a request that used the last unit and then failed, or was refused, is now counted, like the same request one unit earlier. Today it becomes `EXHAUSTED`;
  - once the budget is 0, a later link of the same item that needs no unit (refused by cached robots rules, blocked by the address check, or failing DNS) is now counted, and the item moves on to its next link. Today the item stops at once. Such links cost a DNS lookup but no request. The item stops at the first link that needs a unit.
- **Alternative: keep the sentinel, and only delete the flags.** Rejected: the sentinel is what forces the three translations and the extra checks.

### D4. `author_replies` fetches the comment feed through a function

The signature becomes `author_replies(page, author, feed=None, *, fetch_feed=None)`.

- **When `fetch_feed` is called.** When the page has no comment markup, `feed` is `None`, and `fetch_feed` is given, `author_replies` calls `fetch_feed()` once. It does this before checking the author, so the requests are the same as today. The function returns the feed's bytes, or `None`.
- **The existing `feed` argument stays,** so `test_context_comments.py` passes unchanged.
- **Feed entries.** An entry summary that cannot be parsed, such as one that holds only an HTML comment, is skipped. Today `html.fromstring` at `comments.py:89` runs outside any `try`, so one such entry raises `ParserError` out of `author_replies`, and the item loses every reply.
- **`gather.py`** passes a `fetch_feed` only when the item has a comment feed URL. The function:
  1. adds 1 to `context_total`;
  2. calls `fetch`;
  3. adds 1 to `context_done` when `fetch` returns;
  4. returns the content, or `None`.

  `BudgetExhausted` propagates out of `author_replies` to the item's handler (D3). `gather.py` no longer parses the page or holds the comment XPath.
- **The parse error.** `comments.py` catches `lxml.etree.ParserError` instead of the missing `html.ParserError`, for the page and for each feed entry. Without this, an empty page still raises `AttributeError` inside `author_replies`, before `fetch_feed` can be called.
- **Effect.** When the post page cannot be parsed, for example an empty body, the comment feed is now tried. Today the whole comment block is skipped. This matches the spec: "When the page shows none, the post's comment feed is used."
- **Alternative: a shared `comment_nodes(tree)` helper, called from both files.** Rejected: `gather.py` would still parse the page a second time.

### D5. Set membership for comment nodes

In `author_replies`, build `comment_set = set(comments)` once. Use it for the four membership tests (`comments.py:38`, `:63`, `:70`, `:78`). Iterate over the `comments` list, as today, so the order of replies does not change. The probe confirmed that set and list membership agree.

## Risks / Trade-offs

- [A redirect to a new site now costs a robots.txt request from the per-run budget.] → robots.txt requests already count (README, `CATCHUP_CONTEXT_FETCHES_PER_RUN`). A redirect within one site uses the cached rules.
- [The callback runs another `safe_fetch` inside `safe_fetch`, with its own client.] → The robots.txt request finishes before the page request is sent. The outer client holds at most an idle connection from the previous hop meanwhile.
- [A page fetch whose redirects pass through several new sites can take up to 30 seconds per robots.txt, plus the page's own 30 seconds.] → At most 5 redirects. Each robots.txt is cached for the rest of the run.
- [`context_done` changes in two edge cases (D3).] → No spec or UI text depends on them. The counter shows progress, and it now counts a failed or refused page the same way whatever the budget.
- [The retry of a 429 or 503 calls `allow` again (D1), and no test covers that.] → The origin is cached by then, so the second call sends nothing. Recorded, not pinned.
- [A trailing dot, or a Unicode host next to its `xn--` form, still reads robots.txt twice.] → Recorded as a Non-Goal. The second read applies the same site's rules.

## Migration Plan

Backend only. No data migration. Roll back by reverting the merge.

At review, Claude Code runs:
- the Docker smoke script (`scripts/docker-smoke.sh`);
- a live comparison on two fresh local instances (not 8800), with the same public feed and a local stub model:
  - one from an image built at `main`, and one from the branch;
  - run one digest on each, and compare `context_total`, `context_done`, and each item's stored context URLs;
  - every difference must be explained by a redirect target that robots.txt refuses, or by a page that changed between the two runs.

The redirect and spelling cases are checked by tests only. Sending requests to third-party redirect services just to test them is not needed.
