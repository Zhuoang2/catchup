# Test report: recover-from-model-errors (#67)

2026-11-03. Implemented overnight by Claude Code (a Claude Opus 5.5 sub-agent) in place of Factory Droid, whose login had expired, under the same rules: `openspec-apply-change` with `tdd`, test-first (D-016), named mutations applied and reverted. Branch `recover-from-model-errors`, starting at plan commit `de2db74`.

Test setup: model-client tests use the `mock_provider` fixture and `completion()` (`backend/tests/test_llm_client.py`); the end-to-end run test uses a real `ModelClient` over `httpx2.MockTransport`; grouping and run tests use `FakeModel`. Every `ModelClient` gets `sleep=` set to a no-op or a list's `append`, so no test sleeps. The autouse network block in `backend/tests/conftest.py` stayed on. No model provider or other network service was contacted, except what Docker needed to build the image, and only the seed's fake key was used. Backend commands ran from `backend/` as `uv run -p 3.12 pytest -q -p no:cacheprovider …`.

**Probe before group 1** (D-023, openai 3.24.0 over `httpx2.MockTransport`): `models.list()` raises `AttributeError: 'str' object has no attribute '_set_private_attributes'` (in `openai/_base_client.py`) for a plain-text 200 answer and for JSON `[]`. For `{"object": "list", "data": [1, {"id": "m"}]}` it returns a page whose `data` holds the int `1` and a `Model`. For `"data": "busy"`, `data` is a `str`. This matches design D2.

Baseline before any change: **776 passed**.

## Group 1: model calls (D1, D2)

### Red before 1.2

`tests/test_llm_client.py`: **21 failed, 20 passed**.

| 1.1 check | Test | Observed before 1.2 |
| --- | --- | --- |
| 1 Gateway errors retried (502, 504) | `test_gateway_error_retries_then_succeeds` | One call, then an immediate `ProviderError` ("returned an error", from `openai.InternalServerError`) |
| 2 Gateway errors exhaust retries (502, 504 cases) | `test_server_error_exhausts_retries[502/504]` | `assert 1 == 3`: one call, then an immediate `ProviderError` |
| 4 Invalid JSON retried (cut-off, `not json`, `[1, 2]`) | `test_invalid_json_retries_then_succeeds` | One call, then an immediate `ProviderError("…returned invalid JSON.")` |
| 5 Invalid JSON on every attempt | `test_invalid_json_exhausts_retries` | `assert 1 == 3`: one call, then an immediate `ProviderError` |
| 6 Not a chat completion, retried | `test_answer_that_is_not_a_chat_completion_retries` (7 cases) | `AttributeError`: `'str'`/`'list' object has no attribute 'usage'` (plain text, HTML, JSON `[]`, JSON `"busy"`); `'str' object has no attribute 'message'` (`choices` a string); `'NoneType' object has no attribute 'content'` (`[{}]`); `'str' object has no attribute 'content'` (`message` a string) |
| 7 Not a chat completion on every attempt | `test_answer_that_is_not_a_chat_completion_exhausts_retries` | `AttributeError: 'str' object has no attribute 'usage'` |
| 8 Usage of the wrong shape | `test_usage_of_the_wrong_shape_is_not_counted` | `"n/a"`: `AttributeError: 'str' object has no attribute 'prompt_tokens'`; `"7"`: `TypeError: unsupported operand type(s) for +=: 'int' and 'str'` |
| 10 Model list that is not a model list | `test_model_list_that_is_not_a_model_list_exhausts_retries`, `…_retries_then_succeeds`, `test_model_list_skips_entries_that_are_not_models` | `AttributeError: 'str' object has no attribute '_set_private_attributes'` (both plain-text tests); `AttributeError: 'int' object has no attribute 'model_extra'` |

Guards that passed before 1.2: check 3 (`test_other_status_fails_at_once`, 400/404/422), check 9 (`test_usage_sums_concurrent_chat_calls_and_ignores_missing_usage`, unchanged), and check 11 (`test_empty_response_retries`, `test_empty_choices_retries`, `test_auth_and_balance_fail_immediately`, `test_rate_limit_retries_then_succeeds`, unchanged; no named mutation). The 500 and 503 cases of check 2 also passed.

After 1.2: `tests/test_llm_client.py` **41 passed**; full backend **800 passed**.

### Mutations

Each was applied by a script that restores the file in a `finally` block and asserts the restored text; all were reverted, and the named tests passed again.

| Mutation | Named target | Result under mutation |
| --- | --- | --- |
| Guard 3: retry every status except 401 and 402 (`if attempt == 2:`) | check 3 | 3 failed (400, 404, 422) |
| Guard 9: treat every result that is not a `ChatCompletion` as empty | check 9 | 1 failed (`test_usage_sums_concurrent_chat_calls_and_ignores_missing_usage`) |
| Remove 502 and 504 from the retry set | checks 1, 2 | 4 failed (both 502/504 cases of each), 2 passed (500, 503) |
| Parse the JSON after `_call` again, as at `client.py:133-139` | checks 4, 5 | 4 failed (all three cases of 4, and 5) |
| Read `result.usage` directly | checks 6, 7 | 5 failed: four cases of 6 (plain text, HTML, JSON list, JSON string) and 7 |
| Add the token counts without the `int` checks (`or 0`) | check 8 | 1 failed (the `"7"` case); the `"n/a"` case passed, since a `str` has no token attributes |
| Read `result.choices[0].message.content` directly | `{"choices": [{}]}` and `{"choices": "busy"}` cases of 6 | 7 failed, including both named cases |
| Remove the `AttributeError` → `ValueError` mapping in `list_models` | check 10 | 2 failed (both plain-text tests); the non-model-entry test passed, since it does not depend on the mapping |

## Group 2: the "Other" fallback (D3)

### 2.1

`AuthFailed("group failed")` replaced `ProviderError("group failed")` at `test_digest_runner.py:528`, `:556`, `:610`, `:932`, and `:1215`, and `:531` now expects `"auth_failed"`. The five tests are `test_group_failure_preserves_pending_and_retry_uses_cached_summary`, `test_record_persists_image_choices_and_retry_keeps_them`, `test_record_marks_only_valid_context_refs_and_cache_preserves_flags`, `test_failed_run_preserves_reported_usage`, and `test_failed_run_reuses_gathered_context_without_fetching_again`. On the code before 2.3, `tests/test_digest_runner.py` passed (**60 passed**). They still pass after 2.3.

### Red before 2.3

`tests/test_digest_stages.py`: **7 failed** (checks 1–4). `tests/test_model_errors.py`: **2 failed** (checks 7, 8).

| 2.2 check | Test | Observed before 2.3 |
| --- | --- | --- |
| 1 No list of topics (`{}`, `{"topics": "none"}`; `en`, `zh-Hans`) | `test_grouping_without_a_list_of_topics_falls_back_to_one_topic` (4 cases) | `ProviderError: The model provider returned invalid topics.` |
| 2 Unusable after retries, warning without detail | `test_grouping_unusable_after_retries_falls_back_and_logs_no_detail` | `ProviderError: secret detail` propagated |
| 3 A failed batch | `test_failed_batch_falls_back_without_a_merge_call` | `ProviderError: batch failed` propagated |
| 4 A failed merge | `test_failed_merge_falls_back_to_one_topic` | `ProviderError: …returned invalid topics.` |
| 7 Run whose grouping answer has no topics | `test_run_whose_grouping_has_no_topics_saves_one_other_topic` | Run `failed`, `provider_error`, "The model provider returned invalid topics." |
| 8 The live failure, end to end | `test_live_failure_recovers_end_to_end` | Run `failed`, `provider_error`, "The model provider returned an empty or invalid answer." Attempts were already 2, 3, 3 and the sleeps already matched, thanks to group 1. |

Guards that passed before 2.3: check 5 (`test_grouping_errors_that_fail_the_run_propagate`, `AuthFailed`, `InsufficientBalance`, `RateLimited`, `ConnectionFailed`) and check 6 (`test_grouping_bugs_are_not_hidden`).

After 2.3: those three files **96 passed**; full backend **814 passed**.

### Mutations

| Mutation | Named target | Result under mutation |
| --- | --- | --- |
| Guard 5: catch every `ModelError` in the fallback | check 5 | 4 failed (all four error types) |
| Guard 6: catch `Exception` in the fallback | check 6 | 1 failed |
| Re-raise `ProviderError` in the wrapper | checks 1–4, 7, 8 | 9 failed (all four cases of 1, and 2, 3, 4, 7, 8) |
| Catch the error around each batch call in `_group`, instead of in the wrapper | check 3 | 1 failed (the third batch call was unplanned, so `FakeModel` raised `StopIteration`) |

All were reverted.

## Group 3: grouping sized from the context window (D4)

### Red before 3.2

`tests/test_digest_stages.py` and `tests/test_model_errors.py` together: **14 failed**.

| 3.1 check | Test | Observed before 3.2 |
| --- | --- | --- |
| 1 `grouping_max_tokens` with a window (5 cases) | `test_grouping_budget_is_at_most_half_the_context_window` | `TypeError: grouping_max_tokens() takes 1 positional argument but 2 were given`. The `(60)` → 9,632 case passed (guard). |
| 2 `grouping_batch_chars` (7 cases) | `test_grouping_batch_chars_fit_the_context_window` | `ImportError: cannot import name 'grouping_batch_chars'` (imported inside the test, so the module still collected) |
| 3 Batches fit a small window | `test_grouping_batches_fit_a_small_context_window` | `TypeError: group_items() takes 4 positional arguments but 5 were given` |
| 5 The setting still limits batches | `test_grouping_setting_still_limits_batches_with_a_large_window` | Same `TypeError` |
| 6 A run with a small window | `test_run_with_a_small_context_window_groups_in_batches_that_fit` | `assert 1 > 1`: one grouping call |

Guards that passed before 3.2, with no named mutation: check 4 (`test_grouping_with_unknown_context_window_makes_one_call`: one call, `max_tokens` 9,632) and check 7 (`test_run_with_no_known_context_window_groups_in_one_call`: one call, 9,632).

After 3.2: full backend **832 passed**. `grep -n CATCHUP_GROUPING_BATCH_CHARS README.md` shows the new sentence at `README.md:344`.

### Mutations

| Mutation | Named target | Result under mutation |
| --- | --- | --- |
| Guard 5: use the derived budget alone, ignoring the setting | check 5 | 1 failed |
| Do not pass `context_window` at `runner.py:358` | check 6 | 1 failed |
| Drop the `context_window // 2` cap from `grouping_max_tokens` | checks 1, 3, 6 | 5 failed (the 4,096, 8,192, and 16,384 cases of 1, and 3 and 6); the cases where the cap does not bind passed |
| Return the setting unchanged from `grouping_batch_chars` | checks 2, 3, 6 | 6 failed (the four binding cases of 2, and 3 and 6) |

All were reverted.

## Final checks (task 4.1)

Run in the plan's order on the final tree.

| # | Command | Result |
| --- | --- | --- |
| 1 | `cd frontend && npm run build` | Passed (41 modules transformed) |
| 2 | `cd backend && uv run --python 3.12 pytest -p no:cacheprovider --cov=catchup --cov-report=term` | **832 passed**, **97% overall** (3,062/3,171 statements, 109 missed) |
| 3 | `cd frontend && npm test -- --run` | **259 passed** in 14 files |
| 4 | `cd extension && npm test -- --run`, then `npm run build` | **112 passed** in 8 files; build passed |
| 5 | `docker build -t catchup:model-errors-local .`, then `scripts/docker-smoke.sh catchup:model-errors-local` | Build passed; smoke passed, all 11 PASS lines, exit 0, and the script removed its container and volume. The image was removed afterwards. |
| 6 | `DO_NOT_TRACK=1 openspec validate recover-from-model-errors --strict` | "Change 'recover-from-model-errors' is valid" |

Dependencies were already installed in this checkout, so `uv sync` and `npm ci` were not rerun; they would have needed the network.

**Coverage of the changed modules:**

| Module | Statements | Missed | Coverage | Missed lines |
| --- | --- | --- | --- | --- |
| `llm/client.py` | 110 | 2 | 98% | `:96`, the unreachable `AssertionError`; `:107`, `list_models` when `data` is not a list (no planned check covers it) |
| `llm/prompts.py` | 40 | 0 | 100% | none |
| `digest/group.py` | 77 | 2 | 97% | `:41`, a topic that is not an object, and `:98`, a single oversized item; both were already uncovered |
| `digest/runner.py` | 308 | 7 | 98% | `:103`, `:178`, `:199-200`, `:234`, `:453`, `:455`; none on the changed line |

## Choices made within the plan

- A "model object" in `list_models` is an instance of `openai.types.Model`.
- `chat()` treats blank content as empty (returns `None`), so it takes the same retry path as before.
- The fallback warning reads "Topic grouping fell back to one topic for N items (ProviderError)". Check 2 asserts "ProviderError" and "3 items" in the message, and the absence of "secret detail".
- The runner's `group_items` call wraps onto a second line. It is still one statement, the only runner line this change touches, and passes `context_window` positionally.
- In check 6 of 3.1, merge calls get `FakeModel`'s default topics answer, which has no `topic_refs`. So that run's 60 items end up under "Other". The test asserts 60 distinct items, as the plan says.

## Not performed

- A live run against a provider that answers 200 with a non-JSON body. Claude Code does the live check at review.
- A test for `list_models` with a `data` field that is not a list (`client.py:107`). The plan names no check for it, so none was added.

## Fix round 1 (task group 5)

2026-11-04. Implemented by the same Claude Code sub-agent (Claude Opus 5.5), in place of Factory Droid, from plan commits `678e429` and `7241578`. Same setup and rules as above. The change: a new `InvalidAnswer(ProviderError)` in `llm/client.py`, raised by `_call`'s last attempt for an empty or invalid answer and by `_valid_topics` in `digest/group.py`. The grouping fallback now catches `InvalidAnswer` only, so an HTTP status error that persists after retries fails the run and its items stay pending.

### Red before 5.2

`tests/test_model_errors.py` and `tests/test_digest_stages.py` together: **4 failed, 55 passed**.

| 5.1 check | Test | Observed before 5.2 |
| --- | --- | --- |
| 1 Every model call answers 500, or 404 | `test_run_where_every_model_call_fails_with_a_status_error_keeps_items_pending[500/404]` | `assert ('succeeded', None) == ('failed', 'provider_error')`: the run succeeded |
| 2a A status error propagates out of `group_items` | `test_grouping_status_errors_propagate` | `Failed: DID NOT RAISE ProviderError`: the error fell back to "Other" |
| 2b `InvalidAnswer` falls back | `test_grouping_invalid_answer_falls_back_to_one_topic` | `ImportError: cannot import name 'InvalidAnswer'`. It is imported inside the test, so the module still collected. |

Guards that passed before 5.2:
- check 3: checks 1, 4, 7, and 8 of 2.2;
- check 4: `test_rate_limiting_during_grouping_keeps_items_pending`, where the run fails as `rate_limited` and both items stay `pending`.

The task predicted that implementing 5.2 would turn checks 2 and 3 of 2.2 red, and it did: `test_grouping_unusable_after_retries_falls_back_and_logs_no_detail` and `test_failed_batch_falls_back_without_a_merge_call` failed with the plain `ProviderError` propagating. They were then changed to raise `InvalidAnswer`, and check 2's log assertion to `"InvalidAnswer"`. After that, those two files gave **59 passed**, and the full backend **837 passed**.

### 5.3 test gaps (guards)

All three passed before any mutation:
- `test_model_list_that_is_not_a_model_list_exhausts_retries[data-string]`: `"data": "busy"` raises `ProviderError` after 3 calls;
- `test_usage_of_the_wrong_shape_is_not_counted[completion-count-string]`: `usage_totals() == (7, 0)`;
- `test_other_status_fails_at_once[501]`: 1 call.

### Mutations

The same restoring script was used as above; all mutations were reverted.

| Mutation | Named target | Result under mutation |
| --- | --- | --- |
| Catch `ProviderError` in the fallback again | check 1 of 5.1 | 3 failed: both cases of check 1, and check 2a |
| Catch `ModelError` in the fallback | check 4 of 5.1 | 1 failed |
| Drop the check that `data` is a list | 5.3, model list | 1 failed (`data-string`); `plain-text` passed |
| Use `int(completion)` instead of the type check | 5.3, usage | 1 failed, by assertion: `assert (7, 3) == (7, 0)` |
| Add 501 to the retry set | 5.3, 501 | 1 failed (`501`); 400, 404, and 422 passed |

### Checks (task 4.1, rerun in order)

| # | Command | Result |
| --- | --- | --- |
| 1 | `cd frontend && npm run build` | Passed |
| 2 | `cd backend && uv run --python 3.12 pytest -p no:cacheprovider --cov=catchup --cov-report=term-missing` | **840 passed**, **97% overall** (3,065/3,172 statements, 107 missed) |
| 3 | `cd frontend && npm test -- --run` | **259 passed** in 14 files |
| 4 | `cd extension && npm test -- --run`, then `npm run build` | **112 passed** in 8 files; build passed |
| 5 | `docker build -t catchup:model-errors-local .`, then `scripts/docker-smoke.sh catchup:model-errors-local` | Build passed; smoke passed, all 11 PASS lines, exit 0. The script removed its container and volume, and the image was removed afterwards. |
| 6 | `DO_NOT_TRACK=1 openspec validate recover-from-model-errors --strict` | Valid |

**Coverage of the changed modules:**
- `llm/client.py`: 99% (110/111). Only the unreachable `AssertionError` is missed. The earlier gap, `data` not a list, is now covered by 5.3.
- `llm/prompts.py`: 100%.
- `digest/group.py`: 97% (75/77). The two lines missed before are still missed.
- `digest/runner.py`: 98% (302/308). The `except ModelError` branch is now covered by the status-error run test.

### Choices made within the plan

- Check 2 of 5.1 is split into two tests, so that both of its red reasons could be observed.
- Check 4 of 5.1 also asserts the error kind `rate_limited`, and that no digest is saved.
- `test_digest_stages.py` now imports `InvalidAnswer` at module top, for the two updated checks of 2.2, since it exists from 5.2 on. The 5.1 test written before 5.2 keeps its import inside the function, as the task says.
- Coverage ran with `term-missing`, which shows what `term` shows plus the missed lines.

### Not performed

The live check against a provider is left for Claude Code's review, as before.

## Claude's review (2026-11-04)

- **Independent review of `de2db74..a18a45f`** (a sub-agent that did not write the change): 41 mutations on the changed lines; it found one high-severity plan error and four test gaps, all handled by fix round 1 above. The plan error: falling back on every `ProviderError` let a run in which every model call fails with a status error (a wrong model ID answering 404, a 5xx outage) succeed and deliver every item as "summary unavailable" for good; it reproduced this on the new code, and the old behavior (the run fails, items stay pending) on `de2db74`.
- **Live check, localhost only, before fix round 1.** A stub OpenAI-compatible server answered the first summary call with HTTP 200 `text/plain` "upstream overloaded", later summaries normally, and every grouping call with cut-off JSON. Settings' connection test and save succeeded; a run over two seeded saved-page items succeeded with one "Other" topic holding both items with their summaries, after one summary retry and three grouping attempts; the next run made no chat call. Fix round 1 does not change that path (the cut-off answer is an `InvalidAnswer`), so it was not repeated.
- **Delta review of fix round 1** (`7241578..6c5d0da`): the source change is a new `InvalidAnswer(ProviderError)`, its two raise sites, and the fallback's `except`. Two extra mutations, each run against `test_digest_stages.py`, `test_model_errors.py`, and `test_llm_client.py`: `_call` raising plain `ProviderError` for an invalid answer (1 failed) and `_valid_topics` raising plain `ProviderError` (6 failed). Full backend suite: 840 passed.
- **Not checked:** a run against a real provider.
- **Live check after merge (2026-11-04, Claude with the user).** The same run on the user's instance (`main` at `f832bb4`, DeepSeek `deepseek-flash`): 50 items were summarized and grouped into 10 topics (76,465 prompt and 30,966 completion tokens), and the server log has no "Topic grouping fell back" line. The real provider triggered none of the error paths (invalid answers, status errors); those stay covered by the tests and the stub check above.
