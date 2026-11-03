# Tasks

Implementer notes:
- **Read first.** Read `proposal.md`, `design.md` (D1–D4), and `specs/digest-generation/spec.md`. Line numbers are at main `8faaed6`, so re-check them before editing. If something looks wrong or contradictory, stop and report instead of redesigning.
- **Work test-first with the `tdd` skill** (D-016). For each task, write its checks as failing tests, watch them fail, then implement until they pass. The seams named in each task count as agreed.
- **Guards.** A check marked "guard (already green)" passes before the change, because earlier code already enforces it. Write it and see it pass. Then apply its named mutation by hand, see the check fail, and revert the mutation. A guard with no named mutation only has to pass. Every other check must be red first.
- **Test rules:**
  - **Model client:** use the `mock_provider` fixture and `completion()` in `backend/tests/test_llm_client.py:18-43`. They bridge OpenAI's `httpx2` transport to a `respx` router.
    - Build a non-JSON body with `httpx.Response(200, text=...)` (plain text) or `httpx.Response(200, html=...)`.
    - Build a JSON body of the wrong shape with `httpx.Response(200, json=...)`.
  - **No real sleeps.** Construct every `ModelClient` with `sleep=` set to a no-op or to a list's `append` (`llm/client.py:57`). Assert the recorded backoff where a check names it.
  - **Grouping units:** use the `FakeModel` in `backend/tests/test_digest_stages.py:12-28`. It raises `StopIteration` on a call that the test did not plan, which fails the test.
  - **Runs:** put new run tests in a new file, `backend/tests/test_model_errors.py`. Import `FakeModel`, `all_rows`, `environment`, `execute`, `seed`, and `stub_collection` from `test_digest_runner`, as `test_creator_updates.py:8` does. Do not append tests to `test_digest_runner.py`: #66 adds runner tests on another branch.
  - **Network.** The autouse network block stays (`backend/tests/conftest.py:8-21`). `httpx2.MockTransport` opens no sockets. Never contact a model provider, and use only clearly fake keys, such as the seed's.
- **Out of scope:**
  - the summary budget;
  - retrying a JSON answer without `summary`;
  - showing the fallback in the run or the UI;
  - splitting the call that combines batch topics;
  - any `runner.py` line other than the `group_items` call at `:358`. The source-check loops (`:221-246`) and `caption_pass` (`:66-112`) belong to #66.
- **Commits.** Commit after each task group. Do not push, tag, or open a PR.

## 1. Model calls: retry temporary errors and answers of the wrong shape

- [x] 1.1 **Add failing tests** in `backend/tests/test_llm_client.py` (D1, D2):
  1. **Gateway errors are retried.** Parametrize 502 and 504. The first answer has that status, the second is `completion('{"ok": 1}')`. The result is `{"ok": 1}`, and `route.call_count == 2`.
  2. **Gateway errors exhaust the retries.** Add 502 and 504 to the parameters of `test_server_error_exhausts_retries` (`:164`). Each raises `ProviderError` after 3 calls.
  3. **Other statuses fail at once** (guard, already green). Parametrize 400, 404, and 422. Each raises `ProviderError` after 1 call. Mutation: "retry every status except 401 and 402".
  4. **Invalid JSON is retried.** Parametrize the first answer's content:
     - `'{"topics": [{"title": "Tech'` (cut off);
     - `"not json"`;
     - `"[1, 2]"` (JSON, but not an object).

     The second answer is `completion('{"ok": true}')`. The result is `{"ok": True}`, `route.call_count == 2`, and the recorded sleeps are `[0.25]`.
  5. **Invalid JSON on every attempt.** The cut-off content three times raises `ProviderError` after 3 calls, and the recorded sleeps are `[0.25, 0.5]`.
  6. **Answers that are not chat completions are retried.** Parametrize the first answer, each with status 200:
     - plain text `"upstream overloaded"`;
     - HTML `"<html><body>Bad gateway</body></html>"`;
     - JSON `[]`;
     - JSON `"busy"`;
     - JSON `{"choices": "busy"}`;
     - JSON `{"choices": [{}]}`;
     - JSON `{"choices": [{"message": "busy"}]}`.

     The second answer is `completion('{"ok": true}')`. The result is `{"ok": True}`, and `route.call_count == 2`.
  7. **Not a chat completion on every attempt.** The plain-text answer three times raises `ProviderError`, not `AttributeError`, after 3 calls.
  8. **Usage of the wrong shape.** A valid completion with `"usage": "n/a"` returns its data after 1 call, and `usage_totals()` is `None`. With `"usage": {"prompt_tokens": "7", "completion_tokens": 3}`, it returns its data, and `usage_totals() == (0, 3)`.
  9. **Duck-typed results** (guard, already green). `test_usage_sums_concurrent_chat_calls_and_ignores_missing_usage` (`:92-109`) stays unchanged. Mutation: "treat every result that is not an `openai.types.chat.ChatCompletion` as empty".
  10. **A model list that is not a model list.** `list_models()` with a plain-text 200 answer `"upstream overloaded"` on every attempt raises `ProviderError` (not `AttributeError`) after 3 calls; with the plain-text answer first and a valid list second, it returns the list after 2 calls. An answer `{"object": "list", "data": [1, {"id": "m"}]}` returns only the model `m`. (With openai 3.24.0, `models.list()` itself raises `AttributeError` in the SDK's post-parser for a `str` answer, before CatchUp reads `data`.)
  11. **Existing retry tests** (guards, already green): `test_empty_response_retries`, `test_empty_choices_retries`, `test_auth_and_balance_fail_immediately`, and `test_rate_limit_retries_then_succeeds` stay unchanged and pass.

  Verify: checks 1, 2 (the 502 and 504 cases), 4–8, and 10 fail before 1.2. Record each observed failure in the report: one call and an immediate `ProviderError`, or an `AttributeError` or `TypeError`.
- [x] 1.2 **Implement D1 and D2** in `backend/src/catchup/llm/client.py`:
  - add 502 and 504 to the retried statuses (`:85`);
  - `chat()` reads `usage`, `choices`, `message`, and `content` with `getattr` and type checks, and returns `None` for an answer of the wrong shape;
  - `chat()` parses the JSON itself, and raises `ValueError` for text that is not valid JSON or not an object, so that `_call` retries it. `chat_json` returns what `_call` returns;
  - `list_models`'s operation turns an `AttributeError` raised by the SDK call `self._client.models.list(...)` itself (and only that call) into `ValueError`, checks that the answer's `data` is a list (`ValueError` otherwise), and skips entries that are not model objects (D2);
  - the last-attempt message for empty or invalid answers becomes "The model provider returned an empty or invalid answer." (`:93`).

  Verify:
  - the 1.1 checks pass;
  - each named mutation fails at least one check, and is reverted:
    - "remove 502 and 504 from the retry set" fails checks 1 and 2;
    - "parse the JSON after `_call` again, as at `client.py:133-139`" fails checks 4 and 5;
    - "read `result.usage` directly, as at `client.py:125`" fails checks 6 and 7;
    - "add the token counts without the `int` checks" fails check 8;
    - "read `result.choices[0].message.content` directly, as at `client.py:131`" fails the `{"choices": [{}]}` and `{"choices": "busy"}` cases of check 6;
    - "remove the `AttributeError` → `ValueError` mapping around the SDK call in `list_models`" fails check 10;
  - `uv run --python 3.12 pytest` passes in `backend/`.

## 2. Grouping falls back to one "Other" topic

- [x] 2.1 **Move five existing tests off `ProviderError`** in `backend/tests/test_digest_runner.py`:
  - These tests make a run fail during grouping by answering the grouping call with `ProviderError("group failed")`. After D3, that no longer fails a run; only a rejected key, insufficient balance, rate limiting, or a failed connection does.
  - Change `ProviderError("group failed")` to `AuthFailed("group failed")` at `:528`, `:556`, `:610`, `:932`, and `:1215`. At `:531`, expect `"auth_failed"` instead of `"provider_error"`.
  - Nothing else in these tests changes. A prototype of D3 on 2026-11-03 broke exactly these five, and no other existing test.

  Verify: the five tests pass on the current code. They are guards: they keep passing after 2.3.
- [x] 2.2 **Add failing tests** (D3):

  **In `backend/tests/test_digest_stages.py`,** with its `FakeModel`:
  1. **No list of topics.** Answers `{}` and `{"topics": "none"}`, for 3 items in `"en"`, each give `[("Other", "", [1, 2, 3])]` as `(title, overview, item_ids)`. In `"zh-Hans"`, the title is "其他".
  2. **An unusable answer after retries.** When `chat_json` raises `ProviderError("secret detail")`, the result is the same single topic, and `caplog` holds one warning that names `ProviderError` and the item count, and does not contain "secret detail".
  3. **A failed batch.** 4 items with `batch_chars` 10: the first batch call answers a topic, and the second raises `ProviderError`. The result is one "Other" topic with `[1, 2, 3, 4]`, after exactly 2 calls, so no merge call is made.
  4. **A failed merge.** 4 items with `batch_chars` 10: four batch answers, then a merge answer `{"topics": None}`. The result is one "Other" topic with `[1, 2, 3, 4]`.
  5. **Errors that still fail the run** (guard, already green). `AuthFailed`, `InsufficientBalance`, `RateLimited`, and `ConnectionFailed` raised by `chat_json` propagate out of `group_items`. Mutation: "catch every `ModelError` in the fallback".
  6. **Bugs are not hidden** (guard, already green). A `RuntimeError` raised by `chat_json` propagates. Mutation: "catch `Exception` in the fallback".

  **In the new `backend/tests/test_model_errors.py`:**

  7. **A run whose grouping answer has no topics.**
     - Use `seed(environment, count=2)` and `stub_collection`, with a `FakeModel` subclass that answers `{"summary": "English summary"}` to summary calls, and `{}` to every other call.
     - The run succeeds. The saved topics are `[("Other", "")]`, holding "Item 0" then "Item 1", each with its summary. Both items are `delivered`.
     - A second run with a fresh `FakeModel` ends `no_new_content`, and that model gets no `chat_json` call.
  8. **The live failure, end to end.** Use a real `ModelClient` over `httpx2.MockTransport`:
     - Set `environment.app.state.model_client_factory = lambda base, key, model: ModelClient(base, key, model, http_client=httpx2.Client(transport=httpx2.MockTransport(handle)), sleep=sleeps.append)`.
     - `handle` answers `GET …/models` with `{"object": "list", "data": []}`. It tells calls apart by the request's messages: a system prompt containing `"item_refs"` is grouping, and `Title: Item 0` in the user message is that item's summary.
     - Summary calls run in 4 threads, so count attempts per call under a `threading.Lock`.
     - The answers:
       - "Item 0": a plain-text 200 answer first, then a completion `{"summary": "Zero"}`;
       - "Item 1": an HTML 200 answer on every attempt;
       - grouping: the cut-off JSON from 1.1 on every attempt.
     - Seed 2 items with `seed(environment, count=2)` and `stub_collection`.
     - Expect:
       - the run succeeds;
       - the attempts are 2, 3, and 3;
       - the sorted sleeps are `[0.25, 0.25, 0.25, 0.5, 0.5]`;
       - one topic, `("Other", "")`, holds "Item 0" with summary "Zero", then "Item 1" with `summary_unavailable` true.

     This test needs group 1. Before 2.3, it fails with `provider_error`.

  Verify: checks 1–4, 7, and 8 fail before 2.3. Checks 5 and 6 are guards.
- [x] 2.3 **Implement D3** in `backend/src/catchup/digest/group.py`:
  - rename the recursion (for example `_group`), and send every recursive call to it;
  - `group_items` wraps it: on a `ProviderError`, it returns one topic with the "Other" title, an empty overview, and every item id in input order. It logs a warning with the exception type and the item count, never the exception text;
  - one helper gives the "Other" title, used by `_valid_topics` (`:47`) and by the fallback.

  Verify:
  - the 2.1 and 2.2 checks pass;
  - each named mutation fails a check, and is reverted:
    - "re-raise `ProviderError` in the wrapper" fails checks 1–4, 7, and 8;
    - "catch the error around each batch call in `_group`, instead of in the wrapper" fails check 3;
  - `uv run --python 3.12 pytest` passes in `backend/`.

## 3. Size grouping from the context window

- [x] 3.1 **Add failing tests** (D4). Import `grouping_batch_chars` and the new `grouping_max_tokens` argument inside each test function (or reach them as `prompts.grouping_batch_chars`), not at module top: a top-level import of a name that does not exist yet fails the whole test module at collection, and hides the guards in this task:

  **In `backend/tests/test_digest_stages.py`:**
  1. **`grouping_max_tokens`.** `grouping_max_tokens(60)` is 9,632 (guard, already green). With a window:
     - `(60, 4096)` is 2,048;
     - `(60, 8192)` is 4,096;
     - `(60, 16384)` is 8,192;
     - `(60, 1_000_000)` is 9,632;
     - `(2000, 1_000_000)` is 32,768.
  2. **`grouping_batch_chars(200_000, window)`:**
     - `None` gives 200,000;
     - 4,096 gives 2,000;
     - 8,192 gives 2,096;
     - 32,768 gives 14,384;
     - 128,000 gives 93,232;
     - 1,000,000 gives 200,000.

     Also `grouping_batch_chars(10, 1_000_000)` is 10.
  3. **Batches fit a small window.**
     - Use 60 `GroupItem`s with titles `f"Item {n}"`, source "Source 0", and the summary `("word " * 120).strip()`.
     - Use a `FakeModel` fed by `itertools.repeat(answer)`. `answer` holds one topic with `item_refs` `i1`–`i60` and `topic_refs` `b1`–`b60`, so it serves both batch and merge calls.
     - Call `group_items(model, items, "en", 200_000, 8192)`. Expect:
       - more than one call;
       - in every call, `len(system) + len(user) + max_tokens` is at most 8,192, and `max_tokens` is at most 4,096;
       - every batch call's user text is at most 2,096 characters;
       - each of the 60 ids is placed exactly once.
  4. **Unknown window** (guard, already green). The same items with `group_items(model, items, "en", 200_000)` make one call, with `max_tokens` 9,632.
  5. **The setting still limits batches.** `group_items(model, items, "original", 10, 1_000_000)`, with the four items and answers of `test_batch_merge_covers_every_item_once` (`:277-292`), makes the same 5 calls, with the same result. Mutation: "use the derived budget alone, ignoring the setting".

  **In `backend/tests/test_model_errors.py`:**

  6. **A run with a small window.**
     - Use `seed(environment, count=60)` and `stub_collection`. Before the run, set the `ModelConfig` row's `context_window` to 8,192.
     - Use a `FakeModel` subclass that answers summary calls with `{"summary": "word " * 120}`, and every other call with the default topics answer.
     - Among the calls whose system prompt contains `"item_refs"` or `"topic_refs"`: there is more than one, and each meets the bound of check 3.
     - The digest holds 60 distinct items.
  7. **A run with no known window** (guard, already green). The same seed, without setting `context_window`, groups the 60 items in one call, with `max_tokens` 9,632.

  Verify: checks 1 (the window cases), 2, 3, 5, and 6 fail before 3.2. Checks 4 and 7 are guards.
- [x] 3.2 **Implement D4:**
  - in `backend/src/catchup/llm/prompts.py`, `grouping_max_tokens(count, context_window=None)` and `grouping_batch_chars(setting, context_window)`;
  - in `backend/src/catchup/digest/group.py`, `group_items(client, items, language, batch_chars, context_window=None)` applies `grouping_batch_chars` once, and passes `context_window` to every `grouping_max_tokens` call;
  - in `backend/src/catchup/digest/runner.py:358`, pass `context_window` as the fifth positional argument. A keyword argument would break the stub in `test_unexpected_failure_is_logged_without_key_or_collected_content` (`test_digest_runner.py:850`), which takes only `*_args`;
  - in `README.md`, after the `CATCHUP_SINGLE_CALL_CHARS` advice (`:340-342`), add one sentence: topic grouping is sized from the same context window, in batches of at most `CATCHUP_GROUPING_BATCH_CHARS` characters (default 200000), and users of such a model should lower that too.

  Verify:
  - the 3.1 checks pass;
  - each named mutation fails a check, and is reverted:
    - "do not pass `context_window` at `runner.py:358`" fails check 6;
    - "drop the `context_window // 2` cap from `grouping_max_tokens`" fails checks 1, 3, and 6;
    - "return the setting unchanged from `grouping_batch_chars`" fails checks 2, 3, and 6;
  - `grep -n CATCHUP_GROUPING_BATCH_CHARS README.md` shows the new sentence;
  - `uv run --python 3.12 pytest` passes in `backend/`.

## 4. Checks and report

- [x] 4.1 **The test report, checks, and logs.**
  - **Report.** Write `docs/process/test-report-recover-from-model-errors.md`. It holds:
    - each task's observed red result;
    - the guards, and each named mutation with its result;
    - the final numbers, and the coverage of `llm/client.py`, `llm/prompts.py`, `digest/group.py`, and `digest/runner.py`;
    - the manual check that was not performed: a live run against a provider that answers 200 with a non-JSON body. Claude Code does the live check at review.
  - **Checks, in this order** (in a fresh worktree, run `uv sync` in `backend/`, and `npm ci` in `frontend/` and `extension/`, first):
    1. `npm run build` in `frontend/`, so that backend coverage is measured with `frontend/dist` present;
    2. `uv run --python 3.12 pytest --cov=catchup --cov-report=term` in `backend/`;
    3. `npm test -- --run` in `frontend/`;
    4. `npm test -- --run` and `npm run build` in `extension/`;
    5. `docker build -t catchup:model-errors-local .` and `scripts/docker-smoke.sh catchup:model-errors-local`, from the repository root;
    6. `DO_NOT_TRACK=1 openspec validate recover-from-model-errors --strict`.
  - **Logs.** Add the coverage-summary line to `docs/process/coverage-summary.md`. Add your entry to `docs/process/ai-usage-log.md` after the latest entry, with a faithful excerpt of the prompt you received, and the tool and model. Leave out the session id; Claude Code adds it at review.

  Verify: every command passes, and the report has the actual numbers.

## 5. Fix round 1 (review, 2026-11-04)

The independent review found that grouping fell back also on HTTP status errors, so a run in which every model call fails (a wrong model ID, an outage) succeeded and delivered every item as "summary unavailable" for good. Read D3's "Fix round 1" and the new spec scenario "Every model call fails with a server error" first. Work test-first as before.

- [ ] 5.1 **Add failing tests:**
  1. **A run where every model call answers 500** (new test in `backend/tests/test_model_errors.py`, with a real `ModelClient` over `httpx2.MockTransport` as check 8 of 2.2 does, `GET …/models` answering a list): the run ends `failed` with error kind `provider_error`, no digest is saved, and both items are still `pending`, with `summary_unavailable` not stored. Parametrize 500 and 404. Red on the current head: the run succeeds and delivers both items.
  2. **Status errors propagate out of `group_items`** (`backend/tests/test_digest_stages.py`): `chat_json` raising `ProviderError("The model provider returned an error.")` propagates; `InvalidAnswer` falls back to one "Other" topic. Red on the current head for the first part.
  3. **Unusable answers still fall back** (guards, already green): checks 1, 3, 4, 7, and 8 of 2.2 stay green. Mutation: "catch `ProviderError` in the fallback again" fails check 1 of 5.1.
  4. **Rate limiting during grouping keeps items pending** (run-level, guard, already green): grouping raising `RateLimited` fails the run, and the items stay `pending`. Mutation: "catch `ModelError` in the fallback" fails it.
- [ ] 5.2 **Implement** the D3 "Fix round 1" bullet: `InvalidAnswer(ProviderError)` in `backend/src/catchup/llm/client.py`, raised by `_call`'s last attempt for an empty or invalid answer, and by `_valid_topics` in `backend/src/catchup/digest/group.py`; the fallback catches `InvalidAnswer` only. Check 2 of task 2.2 raises a plain `ProviderError("secret detail")` and expects the fallback; change it to raise `InvalidAnswer("secret detail")` (the plain `ProviderError` case is now check 2 of 5.1). Verify: 5.1 passes; the named mutations fail; the full backend suite passes.
- [ ] 5.3 **Test gaps the review found** (guards, already green; each must fail under its mutation):
  - `list_models` with `{"object": "list", "data": "busy"}` on every attempt raises `ProviderError` after 3 calls (add it to `test_model_list_that_is_not_a_model_list_exhausts_retries`). Mutation: drop the check that `data` is a list.
  - A valid completion with `"usage": {"prompt_tokens": 7, "completion_tokens": "3"}` gives `usage_totals() == (7, 0)`. Mutation: add `completion_tokens` without the `int` check.
  - 501 fails at once after 1 call (add it to `test_other_status_fails_at_once`). Mutation: add 501 to the retry set.
- [ ] 5.4 **Report and checks.** Add a "Fix round 1" section to `docs/process/test-report-recover-from-model-errors.md` with each red result and mutation result; run the checks of task 4.1 again, in order (including the Docker smoke); add your AI usage log entry for this round.
