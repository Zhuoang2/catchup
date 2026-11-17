# Proposal

## Why

- **#90.** The linked-page pass checks robots.txt for the URL that a context fetch starts from, and for nothing else.
  - **Redirects.** `gather.fetch` asks `RobotsCache.allowed` once (`backend/src/catchup/context/gather.py:57`). After that, `safe_fetch` follows up to five redirects without asking robots.txt again (`backend/src/catchup/net/safe_fetch.py:185-200`). A link on one site that redirects to a page another site disallows, or to a site whose robots.txt cannot be read (#76), is still fetched. The review of `fix-robots-errors-and-late-items` found this on 2026-11-16, and narrowed the spec to what the code does.
  - **Origin key.** `RobotsCache` keys its cache by `scheme://netloc`, as the URL writes it (`backend/src/catchup/context/robots.py:16-17`). `https://SITE.example/`, `https://site.example:443/`, and `https://site.example/` are three entries. robots.txt is read once for each spelling, and a later read that succeeds can allow pages that an earlier failed read refused.
- **#60, parts 1 and 2.** A review on 2026-10-21 (D-023) found layering that earlier fix rounds left in the same code. The behavior is correct and tested, but #90 has to change this code, so the cleanup comes first.
  - **Budget handling.** Running out of the per-run fetch budget is signalled three ways: the `EXHAUSTED` sentinel, `RobotsCache.allowed` returning `False` (`robots.py:19-20`), and a generic `FetchError` from `safe_fetch` (`safe_fetch.py:161-164`). `gather.fetch` translates each one back into the sentinel (`gather.py:53-69`), with six `budget[0] <= 0` checks in the module. Two flags, `attempted` and `exhausted`, no longer change the outcome. The page is parsed twice for comment markup, with the same XPath (`gather.py:135-138` and `context/comments.py:30-32`).
  - **Comment lookup.** `author_replies` tests membership in a list inside nested loops (`comments.py:38`, `:63`, `:70`, `:78`), so very large comment pages parse slowly.

## What Changes

- **robots.txt for every redirect.** Each redirect that a context fetch follows is checked against the robots.txt of the target's origin before the target is requested. A refused target ends that fetch as refused, like a refused start URL. Other callers of `safe_fetch` are not affected: they do not use robots.txt today.
- **One robots.txt read per site.** Origins are compared by scheme, host, and port. The host ignores letter case, and a URL without a port is the same origin as one with the scheme's default port (80 or 443).
- **One budget signal.** `safe_fetch` and `RobotsCache` raise one `BudgetExhausted` error when the per-run budget is used up. It is a `FetchError` with today's code and message, so feed discovery keeps working unchanged. The linked-page pass catches it once per item: the item keeps what it gathered and is marked done, and later items fetch nothing more in this run, as today. The sentinel, the translations, and the two flags are removed.
- **One comment-markup check.** `author_replies` takes an optional function that fetches the comment feed. It calls the function only when the page has no comment markup, so `gather.py` no longer parses the page itself.
- **Set lookup** for comment nodes in `author_replies`.
- **Parse error fixes.** `author_replies` catches `lxml.etree.ParserError`. Today it names `html.ParserError`, which does not exist, so an empty post page raises `AttributeError` instead of falling back to the comment feed. It also skips a feed entry whose summary cannot be parsed; today one such entry loses all of the item's replies. Both were found by planning probes.
- **Two small effects of the cleanup** (design D3):
  - A request that fails or is refused on the last budget unit now counts in "Linked pages read", like any other failed or refused request.
  - When a post page cannot be parsed, the comment feed is now tried, as the spec says for a page that shows no replies (with the parse error fix).
- No API, data model, or UI change. No migration.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `content-collection`: "Gather related context for website items" states that redirect targets are checked against their own robots.txt, and how origins are compared. It adds scenarios for a redirect into a disallowed site, a redirect into a site whose robots.txt cannot be read, and one site written three ways.

## Impact

- Code:
  - `backend/src/catchup/net/safe_fetch.py`: `BudgetExhausted`, and an optional per-request check;
  - `backend/src/catchup/context/robots.py`: the origin key, and the budget error;
  - `backend/src/catchup/context/gather.py`: `fetch` and the per-item loop;
  - `backend/src/catchup/context/comments.py`: the feed function, and the set lookup.
- Tests: `backend/tests/test_safe_fetch.py`, `test_context_robots.py`, `test_context_gather.py`, and `test_context_comments.py`. One existing test pins the old budget signal and changes: `test_robots_request_uses_shared_budget` expects `BudgetExhausted` instead of `False`. Every other existing test passes unchanged.
- Docs: `README.md` (the linked-pages paragraph), the decision log (D-031), the requirements-changes table, a test report, and the AI usage log.
- Out of scope:
  - #60 part 3, the frontend poll helper in `Home.test.tsx`;
  - the items in the 2026-11-01 comment on #60: tests that cannot fail in `runner.py` and `collection.py`, and the memory use at `collection.py:99`;
  - the `gathered` and `none` values of `context_status`: both stay, because tests and diagnosis read them;
  - other spellings of one host: a trailing dot, and an internationalized name written in Unicode or in its `xn--` form;
  - feed discovery's `same_origin` check, which compares the raw `netloc`.
