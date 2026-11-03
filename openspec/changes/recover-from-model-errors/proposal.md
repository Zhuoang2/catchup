# Proposal

## Why

One bad model answer can fail a whole digest run, and a failed grouping repeats on every later run (issue #67). The issue was found in the system review of `add-x-accounts` on 2026-11-01, and the user's live check on 2026-11-03 hit the same bug class. Line numbers are at main `8faaed6`.
- **Grouping blocks later digests.** A grouping answer without `topics` raises `ProviderError` (`backend/src/catchup/digest/group.py:27-29`), and invalid or cut-off JSON does too (`backend/src/catchup/llm/client.py:134-139`). The run fails before saving (`digest/runner.py:451-452`), so its items stay pending. The next run then sends the same grouping call, and it fails again.
- **Grouping ignores the model's size.**
  - The batch limit is a fixed 200,000 characters (`CATCHUP_GROUPING_BATCH_CHARS`, `config.py:75`, passed at `digest/runner.py:358`).
  - The output budget is `min(32768, 8192 + 24 × items)`, whatever the context window (`llm/prompts.py:12-13`).
  - With an 8,192-token model and 60 items, one call carries about 40,000 characters and asks for 9,632 output tokens.
- **Some temporary errors are not retried.**
  - `_call` retries only 429, 500, and 503 (`llm/client.py:85`), so 502, 504, and invalid JSON fail at once.
  - In the summary stage that marks the item `summary_unavailable`. The item is then delivered and never summarized again.
  - The spec says temporary server errors are retried, and only an item whose summary "could not be produced after retries" is marked unavailable.
- **A non-JSON answer crashes the run.**
  - In the live check, a provider answered HTTP 200 with a body that was not JSON. The OpenAI SDK (3.24.0) then returns the body as a `str`.
  - `chat()` reads `result.usage` (`llm/client.py:125`) and raises `AttributeError`. Neither `_call` nor `_summarize` catches it.
  - The run failed with "Digest generation failed. Try again." after 15 of 18 items were summarized.
  - A probe with a mocked transport (2026-11-03) found the same crash for a JSON list or string body, and for `choices`, `message`, or `usage` of the wrong type (`design.md`, Context).

## What Changes

- **Retry more temporary errors** (`llm/client.py`):
  - 502 and 504 are retried, like 429, 500, and 503.
  - An answer whose text is not valid JSON, or is JSON but not an object, is retried like empty content.
  - So is an answer that is not a chat completion with text content.
  - All of these use the existing three attempts with backoff, then raise `ProviderError`.
- **Read answers without assuming their shape.** An answer of the wrong shape counts as empty. Token counts are added only when they are integers.
- **Fall back to one "Other" topic** (`digest/group.py`):
  - The fallback applies when the model's grouping answers are still unusable after retries: no valid topics, invalid JSON, or a server error (`ProviderError`).
  - Then the run saves all its summarized items under one "Other" topic ("其他" in a Chinese digest), in run order, and succeeds.
  - A rejected key, insufficient balance, rate limiting, or a failed connection still fails the run, and the items stay pending; their summaries are stored, so a later run only has to group them again.
- **Size grouping from the context window** (`llm/prompts.py`, `digest/group.py`, `digest/runner.py:358`):
  - When the window is known, a grouping call's output budget is at most half of it.
  - A batch's text is at most the rest of the window, minus a 2,000-character prompt allowance, and never more than `CATCHUP_GROUPING_BATCH_CHARS`.
  - With an unknown window, nothing changes.
- **Unchanged:**
  - the summary stage's budgets, and its rule that one failed item does not fail the run;
  - the number of attempts and the backoff;
  - connection errors, which are not retried;
- **The model list** (`list_models`, used by the Settings connection test and the run's context-window lookup) reads its answer the same way: an answer that is not a model list, such as a plain-text 200 page, is retried like empty content and then raises `ProviderError`, instead of `AttributeError` (a 500 in Settings).
- **Out of scope:**
  - Retrying a JSON answer that lacks `summary`.
  - Showing in the run that grouping fell back.
  - Splitting the call that combines batch topics.

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- `digest-generation`:
  - "Summarize items once and group them by topic": a grouping that cannot be completed saves the items under one "Other" topic, instead of failing the run. The "Retry after failure" scenario now names a rejected key, and a new scenario covers the fallback.
  - "Retry transient model errors": names 502 and 504, answers that are not valid JSON, and answers that are not chat completions, with new scenarios.
  - New "Fit topic grouping in the model's context window".

## Impact

- `backend/src/catchup/llm/client.py`: the retry set, and `chat()` inside `chat_json`.
- `backend/src/catchup/llm/prompts.py`: `grouping_max_tokens` takes the context window, and a new `grouping_batch_chars`.
- `backend/src/catchup/digest/group.py`: the fallback around the existing recursion, and the context window passed through.
- `backend/src/catchup/digest/runner.py:358`: passes `context_window` to `group_items`. This is the only runner line this change touches.
- Tests:
  - `test_llm_client.py` and `test_digest_stages.py` get new tests;
  - a new `test_model_errors.py` holds the run-level tests;
  - five tests in `test_digest_runner.py` change their grouping failure from `ProviderError` to `AuthFailed`, because a `ProviderError` no longer fails a run.
- `README.md`: one sentence on `CATCHUP_GROUPING_BATCH_CHARS`.
- No API, database, frontend, or extension change.
