# Design

Lean change for issue #66. See `proposal.md` for why. Planned by Claude on 2026-11-03 while the user slept, under their instruction to fix open issues overnight; the user reviews the result before anything is pushed.

A fresh-eyes sub-agent checked the tasks against the code before Droid ran (D-023). Claude folded in its 12 findings: checks that would already pass (an empty `base`, a link `try` that already exists, a `media:content` without an image type), a `href` that feedparser empties, two missing seams, `ObjectDeletedError` after a rollback, how to patch an imported name, two stubs that return `None`, a missing preview check, DNS mocking for `article_text`, and one line number.

## Context

Line numbers are at main `8faaed6`; re-check them before editing.

- **Where parsing can raise.** Python's `urljoin` and `urlsplit` raise `ValueError` for some text, such as `https://[object Object]` or `http://[x`. Unguarded calls on text from feeds or pages:
  - `sources/feeds.py:122`: `urljoin(base, image.url.strip())`, before the `try` in `filter_image_urls`. Used for feed and YouTube images and for saved pages' images (`api/extension.py:183`).
  - `sources/feeds.py:224`: `urljoin(self.base, self.href)` in the entry HTML link collector.
  - `sources/discovery.py:118`: `urljoin(response.url, href)` for declared feeds.
  - `context/links.py:19-21`: `urlsplit(item_link)` and `urlsplit(site_url)`. `site_url` can be a feed's channel link (`feeds.py:356`).
  - Already guarded: `feeds.py:121-126` (after the join), `feeds.py:321-324` (entry links), `api/extension.py:101-106`.
- **`safe_fetch`** maps `httpx.HTTPError` (`net/safe_fetch.py:200-201`), but `httpx.InvalidURL`, raised for a URL with a character such as `\x7f`, is not an `HTTPError` subclass, so it escapes. `article_text` (`collection.py:55-62`) catches only `FetchError`.
- **No guard per source.** `check_source` (`collection.py:76-95`) catches `FetchError` and `FeedParseError`. The run's loops (`digest/runner.py:222-227` for feeds, podcasts, and YouTube; `:228-246` for X; `caption_pass`, `:66-112`, for YouTube captions) have no `try`. Anything else propagates to `run_digest`'s outer handler, which fails the run with "Digest generation failed. Try again." (`error_kind` `run_failed`).
- **Deletion during a check.** The delete route (`api/sources.py`, `delete_source`) deletes at once. A check that then commits a `SourceCheck` or items for the deleted source raises `IntegrityError` (foreign keys are on); the caption pass raises `StaleDataError` committing a deleted item. Later stages already tolerate deletion (`test_digest_runner.py:790-956`, `context/gather.py:164-167`).

## Goals / Non-Goals

**Goals:**
- No text from a feed, page, or entry can fail a source check or a run.
- One source's unexpected error is recorded against that source, and the run goes on.

**Non-Goals:**
- Retrying model calls, or grouping failures (#67).
- Refusing to delete a source during a run.
- Changing what a check reports when it succeeds.

## Decisions

### D1. One helper for parsing addresses that may be malformed
- **What.** A small module, `backend/src/catchup/net/urls.py`, with no CatchUp imports:
  - `join_url(base, href) -> str | None`: `urljoin`, or `None` when it raises `ValueError`;
  - `split_url(url) -> SplitResult | None`: `urlsplit`, or `None` when it raises `ValueError`.
- **Callers.** `filter_image_urls` (skip the candidate), the entry link collector (skip the link), discovery's declared-feed loop (skip the candidate), and `related_links` (an unparsable item link or site URL matches nothing; an unparsable link is skipped).
- **Why one helper,** rather than a `try` at each call: the same mistake appeared in four places; a named helper makes the rule visible, and later code can use it.
- **Alternative:** validate addresses once, when a feed is parsed. Rejected: images and links come from several parsers (feeds, YouTube, saved pages), and context reads links later.

### D2. `safe_fetch` maps `httpx.InvalidURL` to `invalid_url`
- Catch `httpx.InvalidURL` next to `httpx.HTTPError`, and raise `FetchError("invalid_url", "Enter a valid public HTTP or HTTPS URL.")`, the wording `_check_address` already uses. Then `article_text` falls back to the feed's text, and preview answers 422.

### D3. One guard per source in the run
- **What.** A helper in `digest/runner.py`, used by the feed loop and the X loop, runs one source's check in its own session. On any `Exception` that escapes the check:
  1. roll back the session;
  2. if the source no longer exists, skip it (log at info, with the loop's source id; reading `source.id` after a rollback of a deleted row raises `ObjectDeletedError`);
  3. otherwise record a `SourceCheck` with `status="failed"`, `error="Could not check this source."`, `entries_seen=0`, `new_count=0`, and set the source's `last_check_at` and `last_check_status`, as `check_source` does for a fetch failure;
  4. log a warning with the run id, the source id, and the exception's class only (no message, which could hold page text).
- **Scope.** `Exception` only: `KeyboardInterrupt` and `SystemExit` still stop the run.
- **X accounts.** Reads already charged to the shared `XReadBudget` stay counted, because X bills them.
- **Why in the runner,** not in `check_source`: the X loop and any later source kind get the same guard, and `check_source` stays about checking a feed.
- **Alternative:** catch `Exception` inside `check_source` only. Rejected: it would not cover X accounts, and it would be a second pattern next to `check_x_account`'s.

### D4. The caption pass is guarded per item
- The pass collects the item ids first, and loads each item with `session.get` inside the loop, skipping one that no longer exists. Each item's work and commit run in a `try`. On an `Exception`: roll back, log the class with the item's id from the collected list, and go on. An item deleted with its source is simply skipped. An item that failed for another reason keeps its previous `transcript_status`, so the next run tries again.

### D5. Deleting a source during a run stays allowed
- The checks tolerate it (D3, D4), as the later stages already do. Refusing deletion during a run, as "Delete all X data" does, was considered and not chosen: removing a source is a common action, and a run can take minutes (#64).

### D6. What the run counts
- A source skipped because it was deleted records no check. `sources_total` is counted live today (`runner.py:486`, noted in #64), so the run bar still adds up. A source recorded `failed` by D3 counts as checked.

## Risks / Trade-offs

- **[A catch-all hides a real bug]** → the warning names the run, the source, and the exception class, and the source shows "Could not check this source." on the Sources page and in the run's Needs attention list, so it is visible, not silent.
- **[Rolling back loses a check's partial work]** → a check is one transaction today; nothing partial was ever kept.
- **[An unparsable image or link is dropped silently]** → it could never have been shown or fetched anyway.

## Testing

Backend pytest only, test-first (D-016), with `FakeModel` for runs and the autouse network block. Seams: `join_url` and `split_url`; `filter_image_urls`, the link collector, and `parse_feed` with invented feeds; `related_links`; `discover` with a declared feed whose `href` cannot be joined; `safe_fetch` with a URL `httpx` rejects; `run_digest` with a bad source and a healthy one; a check that raises `RuntimeError`; deletion during a check and during the caption pass; preview and captures. Each task names a mutation that must fail its test.
