# Design

Lean change for issue #67. See `proposal.md` for the motivation, and the `digest-generation` delta for the requirements. Line numbers are at main `8faaed6`.

## Context

- **`ModelClient._call(operation)`** (`backend/src/catchup/llm/client.py:73-95`):
  - makes up to 3 attempts, and between them calls the injected `sleep` (`:57`) with 0.25 s, then 0.5 s (`:94`);
  - retries a `None` or blank-string result, and any `ValueError`. That includes the SDK's `JSONDecodeError` for a blank `application/json` body;
  - retries `APIStatusError` 429, 500, and 503 (`:85`); any other status raises `ProviderError` at once;
  - raises `AuthFailed` (401) and `InsufficientBalance` (402) at once, and `ConnectionFailed` at once.
- **`chat_json`** (`:116-140`): its `chat()` reads `result.usage` (`:125-130`) and `result.choices[0].message.content` (`:131`). `json.loads` runs after `_call` has returned (`:134-139`), so invalid JSON is never retried.
- **SDK probe** (openai 3.24.0 through `httpx2.MockTransport`, 2026-11-03). What `chat.completions.create` returns for a status-200 answer:

  | Answer body | `create()` returns | Today |
  | --- | --- | --- |
  | `text/plain` or `text/html` page | `str` | `AttributeError` at `:125` |
  | JSON `[]` | `list` | `AttributeError` at `:125` |
  | JSON `"busy"` | `str` | `AttributeError` at `:125` |
  | JSON `{"error": {...}}` | `ChatCompletion` with `choices` `None` | retried as empty |
  | JSON `{"choices": [{}]}` | `message` is `None` | `AttributeError` at `:131` |
  | JSON `{"choices": "busy"}` | `choices` is a `str` | `AttributeError` at `:131` |
  | JSON `{"choices": [{"message": "busy"}]}` | `message` is a `str` | `AttributeError` at `:131` |
  | valid choices, `"usage": "n/a"` | `usage` is a `str` | `AttributeError` at `:129` |
  | valid choices, `"usage": {"prompt_tokens": "7", ...}` | a `str` count | `TypeError` at `:129` |
  | blank `application/json` | raises `JSONDecodeError` | retried |

  Status 502 and 504 raise `openai.InternalServerError`, an `APIStatusError`.
- **The summary stage** (`digest/summarize.py:128-131`) turns `ModelError` and `ValueError` into an unavailable summary, and re-raises `AuthFailed` and `InsufficientBalance`. Any other exception, such as the `AttributeError` above, reaches `runner.py:455-462` and fails the run as `run_failed`.
- **Grouping:**
  - `group_items` (`digest/group.py:59-96`) is recursive. A payload over `batch_chars` is split into batches (`:67-75`), each batch is grouped in one call (`:81-82`), and a merge call combines the batch topics (`:83-90`).
  - `_valid_topics` raises `ProviderError` when `topics` is not a list (`:27-29`), and puts unplaced items under "其他" for `zh-Hans`, otherwise "Other" (`:47`).
  - The runner calls `group_items` once (`runner.py:358`) with `settings.grouping_batch_chars`. Any `ModelError` there fails the run (`:451-452`), and the items stay pending.
- **The runner already knows `context_window`** (`runner.py:201-215`), and uses it for the summary budget (`:343-345`).

## Goals / Non-Goals

**Goals:**
- No answer shape, and no grouping failure other than a rejected key or insufficient balance, fails a run.
- A grouping call fits the model's context window when the window is known.

**Non-Goals:**
- Changing the summary budget, the number of attempts, or the backoff.
- Making `list_models` tolerate a non-JSON answer (see `proposal.md`, Out of scope).

## Decisions

### D1. The retry set
- **Statuses retried:** 429, 500, 502, 503, and 504. Any other status (400, 404, 422, …) still raises `ProviderError` at once.
- **Invalid JSON:** `chat()` parses the content itself, inside the operation that `_call` runs. Text that is not valid JSON, or JSON that is not an object, raises `ValueError`, so `_call` retries it like empty content.
- **Attempts and backoff** are unchanged: 3 attempts, with sleeps of 0.25 s and 0.5 s.
- **After the last attempt** the error is `ProviderError("The model provider returned an empty or invalid answer.")`. No test or UI reads the old text, "returned empty content".
- **Alternatives:**
  - Retry every 5xx. Rejected: 501 and 505 are not temporary, and the spec names "temporary server errors".
  - Retry invalid JSON only once, as the issue suggests, with its own counter. Rejected: a second retry rule in `_call` saves at most one call, and three attempts already bound the cost.
  - Also retry a JSON object without `summary` or `topics`. Rejected: not in the issue, and the grouping fallback (D3) covers `topics`.

### D2. Answers that are not chat completions
- **`chat()` reads the result with `getattr` and type checks, and never assumes its type:**
  - The content is `result.choices[0].message.content` only when `choices` is a non-empty list and the content is a string. Otherwise the answer counts as empty, and `_call` retries it.
  - Usage counts as reported when `result.usage` has a `prompt_tokens` or `completion_tokens` attribute. Each count is added only when its type is exactly `int`.
- **It lives in `chat()`, not in `_call`,** because `_call` also serves `list_models`, and does not know which result type to expect.
- **Alternatives:**
  - `isinstance(result, ChatCompletion)`, as the issue comment suggests. Rejected on its own: the probe shows `ChatCompletion` objects that still crash (`choices` a string, `message` missing). Also, the existing usage test (`backend/tests/test_llm_client.py:92-109`) passes `SimpleNamespace` results, which it would turn into empty answers.
  - Catch `AttributeError` and `TypeError` in `_call`. Rejected: it would also turn bugs in CatchUp's own code into provider errors.

### D3. Grouping falls back to one "Other" topic
- **Where.** `group_items` becomes a thin wrapper around the existing recursion, which is renamed (for example `_group`). Every recursive call goes to the inner function.
  - On a `ModelError` other than `AuthFailed` and `InsufficientBalance`, the wrapper returns `[Topic(<Other title>, "", <every item id, in input order>)]`.
  - It logs a warning with the exception type and the item count, never the exception text.
  - An empty item list still returns `[]` without a call.
- **Which errors fall back:** `ProviderError` (no valid topics, invalid JSON after retries, server errors after retries, other statuses), `RateLimited`, and `ConnectionFailed`. This is the set that the summary stage already absorbs (`summarize.py:128-131`).
- **Which errors do not:**
  - `AuthFailed` and `InsufficientBalance` are re-raised, because the spec says they fail the run immediately.
  - Exceptions that are not `ModelError` propagate, and the run fails as `run_failed`, so bugs are not hidden.
- **The whole grouping falls back,** also when only one batch, or only the merge call, fails. Batch topics already returned are dropped.
- **The title** keeps the existing rule, moved into one helper used by `_valid_topics` and the fallback: "其他" when the digest language is `zh-Hans`, and "Other" otherwise, also for "original" and typed languages (pinned by `test_digest_stages.py:299-305`). The overview is empty, as for unplaced items.
- **The runner is unchanged here.** The fallback returns topics like any grouping, so `runner.py:362-448` saves and delivers them.
- **Stored state.** No new state, and no stored state changes meaning. Trace of one item: run 1 summarizes it and stores the summary (`runner.py:324-339`); grouping falls back; the save marks the item `delivered` (`:414`). Run 2 selects only `pending` items (`:262-265`), so the item is not grouped again.
- **Alternatives:**
  - The fallback in the runner, around `group_items`. Rejected: it touches more runner lines next to #66's edits, and repeats the "Other" title rule.
  - Keep the batch topics already produced when only one batch or the merge fails. Rejected for this fix: a partial result needs its own merge rules. One "Other" topic is what the issue asks for.
  - Fall back only on `ProviderError`, and keep failing the run on connection and rate-limit errors. Rejected: the summaries are already stored, the summary stage treats these errors the same way, and one rule is easier to state.

### D4. The grouping budget from the context window
- **`grouping_max_tokens(count, context_window=None)`** in `llm/prompts.py` is `min(8192 + 24 × count, 32768, context_window // 2)`. Without a window, it is unchanged.
- **`grouping_batch_chars(setting, context_window)`**, next to it:
  - the setting, when the window is unknown;
  - otherwise `min(setting, max(2_000, context_window − min(32768, context_window // 2) − 2_000))`.
- **`group_items(client, items, language, batch_chars, context_window=None)`** applies `grouping_batch_chars` once, in the wrapper. It passes `context_window` to every `grouping_max_tokens` call, for batches and for the merge.
  - `context_window` is an ordinary parameter, passed positionally at `runner.py:358`. Then `test_unexpected_failure_is_logged_without_key_or_collected_content` (`test_digest_runner.py:844-861`), whose stub of `group_items` takes only `*_args`, keeps working unchanged. A prototype run on 2026-11-03 showed that a keyword argument breaks it.
- **Numbers:**

  | Context window | Output cap | Batch text |
  | --- | --- | --- |
  | unknown | 32,768 (8,192 + 24 per item) | 200,000 (the setting) |
  | 4,096 | 2,048 | 2,000 (the floor) |
  | 8,192 | 4,096 | 2,096 |
  | 32,768 | 16,384 | 14,384 |
  | 128,000 | 32,768 | 93,232 |
  | 1,000,000 | 32,768 | 200,000 (the setting) |

  Measured with the code's `_payload` on 2026-11-03: 60 items with 599-character summaries make a 40,361-character payload. With an 8,192-token window, that becomes 20 batches of 3 items, at most 2,016 characters each, and a merge input of about 1,200 characters. The grouping system prompt is about 320 characters.
- **One character per token and the 2,000-character allowance** follow the summary budget (`runner.py:343-345`, and the spec's "Summarize long texts in full").
- **"Work with reasoning models by default" is unchanged.** The cap is lower than 32,768 only for windows below 65,536 tokens, where a larger budget would not fit anyway.
- **Alternatives:**
  - Reserve each batch's own output budget (8,192 + 24 per item) instead of the cap. Rejected: batch size and output budget would then depend on each other, for a saving only on windows from 32k to 64k tokens.
  - Use the summary single-call budget, including `CATCHUP_SINGLE_CALL_CHARS`, for grouping. Rejected: with an unknown window that is 60,000 characters, which would split DeepSeek's grouping into batches that today's runs do not need.
  - Split the merge call too, merging in rounds. Rejected: the fallback covers this rare case.

## Risks / Trade-offs

- [A cut-off grouping answer costs two more calls before the fallback, each with up to 32,768 output tokens] → The cost is bounded at three calls, and batches now fit the window, which makes cut-off answers rarer.
- [A connection drop during grouping saves the digest under "Other", where a failed run would have let a later run group the items] → The digest keeps every summary, and the rule matches the summary stage.
- [The fallback is not shown in the run] → The run succeeds with one "Other" topic, and only the log says why. Showing it is out of scope.
- [On a small window with many batches, the merge input may not fit] → The grouping falls back to "Other".
- [A small local model that reports no window still gets 200,000-character batches] → The README tells such users to lower `CATCHUP_GROUPING_BATCH_CHARS`, next to the existing `CATCHUP_SINGLE_CALL_CHARS` advice.

## Overlap with #66

`isolate-source-check-failures` (#66) is planned on another branch, and edits `runner.py:66-112` and `:221-246`.
- In the runner, this change edits only the `group_items` call at `:358`, and no imports.
- New run-level tests go in a new file, `backend/tests/test_model_errors.py`. Neither change then appends to the end of `test_digest_runner.py`.
- This change edits one line in each of five existing tests in `test_digest_runner.py`: `:528` (and the assertion at `:531`), `:556`, `:610`, `:932`, and `:1215`. A conflict is possible only if #66 edits those same tests.

## Migration Plan

- No data change. `CATCHUP_GROUPING_BATCH_CHARS` keeps its default, and becomes an upper limit when the window is known.
- Rollback is a revert.
