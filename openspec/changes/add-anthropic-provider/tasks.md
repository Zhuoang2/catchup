# Tasks

Implementer notes:
- **Read first.** Read `proposal.md`, all of `design.md` (Context, D1–D15, the user's decisions U1–U6 as recorded at plan approval, Risks, Testing), and both spec deltas under `specs/`. If something looks wrong or contradictory, stop and report instead of redesigning.
- **Work test-first with the `tdd` skill** (D-016). In each group, first write the group's tests, run them, and watch each fail for the reason the task gives. Then change the code. The seams are named in each task, and they count as agreed. They are:
  - `AnthropicModelClient(base_url, api_key, model, *, http_client=…, sleep=…)` with `httpx2.Client(transport=httpx2.MockTransport(handle))`, as `backend/tests/test_llm_client.py:18-37` and `tests/test_model_errors.py:66-93` do for `ModelClient`;
  - `make_model_client(base_url, api_key, model, provider, **options)`;
  - `app.state.model_client_factory`, and `app.dependency_overrides[get_model_client_factory]`;
  - from `backend/tests/test_digest_runner.py`: `environment`, `seed`, `stub_collection`, `execute`, and `FakeModel`; from `tests/test_model_errors.py`: `saved_digest`;
  - the Alembic `Config` and `command` pattern of `tests/test_db.py:18-50`;
  - `fetchMock`, `respond`, `mockModelProvider`, `modelPuts`, `modelSection`, and `expectAccessible` in `frontend/src/pages/Settings.test.tsx`.
- **Test rules:**
  - **No real network, and no real keys.** Every Anthropic request goes to a `MockTransport` handler. The handler asserts the host `anthropic.example`, and raises on any request it does not expect. Keys are invented strings such as `test-only-key`.
  - **Streamed answers.** Build them with one helper in `backend/tests/test_anthropic_client.py`: `stream_body(text, *, stop_reason="end_turn", input_tokens=10, output_tokens=5, cache_creation=0, cache_read=0)`. It returns an `httpx2.Response(200, headers={"content-type": "text/event-stream"}, content=…)` holding these events, in this order:
    - `message_start`, with a message whose `content` is `[]` and whose `usage` holds the input and cache counts;
    - for a non-empty `text`: `content_block_start` (a text block), one `content_block_delta` (`text_delta`), and `content_block_stop`, each with `"index": 0` (the SDK's stream helper raises `TypeError` without it);
    - `message_delta`, with `stop_reason` and `usage.output_tokens`;
    - `message_stop`.

    Each event is `event: <type>` and `data: <json>`, followed by a blank line. Add `error_event(type)` for an `error` event sent on a 200 stream. `tests/test_anthropic_runs.py` imports both.
  - **Change no existing test,** except where a task says so.
- **Mutations.** For each named mutation, apply it alone, run the named tests, record the result, and restore the code exactly. Compare with `git diff` after restoring.
- **Environment:**
  - **Backend.** Run `uv run --offline pytest …` in `backend/`. Before this run, Claude Code added `anthropic>=1.13,<2` to `backend/pyproject.toml`, locked it at exactly 1.13.0 in `backend/uv.lock` (`docstring-parser` comes with it), and committed both on this branch with the plan. Do not add, remove, or upgrade packages.
  - **Frontend and extension.** Use Node 22.17.1 with `export PATH="$HOME/.nvm/versions/node/v22.17.1/bin:$PATH"`. Then run `npm ci --offline --no-audit --no-fund` in `frontend/` (and in `extension/` for task 4.1). It installs the locked packages from the local npm cache. If it fails, stop and report. Do not change any `package.json` or `package-lock.json`.
- **Do not run** `docker build`, `scripts/docker-smoke.sh`, or any `docker` command. Claude Code runs them at review.
- **Out of scope.** Do not change:
  - `backend/src/catchup/llm/client.py`, `llm/prompts.py`, `digest/summarize.py`, `digest/group.py`;
  - the extension;
  - any thinking or effort setting (#4).
- **Do not edit:**
  - `proposal.md`, `design.md`, or the spec deltas;
  - `docs/process/decision-log.md` or `docs/process/requirements-changes.md`. Claude Code wrote D-037 and the requirements row with the plan.
- **OpenSpec.** Prefix every OpenSpec CLI call with `DO_NOT_TRACK=1`.
- **Commits.** Commit after each task group. Do not push, tag, or open a PR.

## 1. Anthropic client (D2–D10)

- [x] 1.1 Probe, then write the tests and watch them fail.

  **Probes (record both results in the test report, task 4.2):**
  - `uv run --offline python -c "import anthropic; print(anthropic.__version__)"` in `backend/` prints `1.13.0`. If the import fails or prints another version, stop and report: the dependency was not added as planned.
  - In a scratch script under `/tmp` (not committed), stream a request through `anthropic.Anthropic(api_key="test-only-key", base_url="https://anthropic.example", max_retries=0, http_client=httpx2.Client(transport=httpx2.MockTransport(…)))` to a handler that answers `httpx2.Response(200, html="<html>…</html>")`. Then call `get_final_message()`. Design D4 expects `AssertionError`. If the SDK raises anything else, or returns, stop and report.

  **In a new file `backend/tests/test_anthropic_client.py`** (`BASE = "https://anthropic.example"`):
  - **`test_lists_models_with_positive_context_windows_and_opus_first`.**
    - Page 1 answers `has_more: true`, with `last_id`. It lists:
      - `claude-sonnet-5-5`, with `max_input_tokens` 1000000;
      - `claude-opus-5-5`, with `"12"`;
      - a `claude-3-retired` entry with `lifecycle: "retired"`.
    - Page 2 is requested with `after_id`. It lists:
      - `claude-haiku-5-5`, with `max_input_tokens` `True`;
      - `claude-x-zero`, with `0`.
    - Fill every entry with `type`, `display_name`, `created_at`, and `lifecycle`.
    - `list_models()` equals `[ModelInfo("claude-opus-5-5"), ModelInfo("claude-sonnet-5-5", 1_000_000), ModelInfo("claude-haiku-5-5"), ModelInfo("claude-x-zero")]`.
    - Both requests go to path `/v1/models`, and each request's `timeout` extension is 15.0 for connect, read, write, and pool.
  - **`test_json_answer_request_shape_and_no_key_in_logs`.**
    - Model `claude-haiku-5-5`. Call `chat_json([{"role": "system", "content": "Rules"}, {"role": "user", "content": "Item"}], 200)` under `caplog.at_level(logging.DEBUG)`. It returns `{"summary": "ok"}`.
    - The request is a POST to path `/v1/messages`, with no `beta` query.
    - The body has `model`, `max_tokens == 16000`, `system == "Rules"`, `messages == [{"role": "user", "content": "Item"}]`, and `stream == True`.
    - The body has none of `temperature`, `top_p`, `top_k`, `thinking`, `output_config`, or `fallbacks`.
    - The `x-api-key` header is `test-only-key`, and there is no `anthropic-beta` header.
    - The `timeout` extension is connect 10.0, read 300.0, write 10.0, and pool 10.0.
    - `test-only-key` is not in `caplog.text`.
  - **`test_two_system_messages_join_into_the_system_field`.** `system == "One\n\nTwo"`, and only the user message is in `messages`.
  - **`test_large_output_limits_are_kept`.** Calling with 32768 sends `max_tokens == 32768`.
  - **`test_host_environment_credentials_are_never_used`.**
    - Set `ANTHROPIC_API_KEY=env-key`, `ANTHROPIC_AUTH_TOKEN=env-token`, and `ANTHROPIC_BASE_URL=https://env.example` with `monkeypatch.setenv`.
    - The request goes to `anthropic.example`, with `x-api-key: test-only-key`. No header contains `env-key` or `env-token`.
  - **`test_fenced_json_is_accepted_without_retry`,** parametrized over a block that starts with ```` ```json ```` and one that starts with ```` ``` ````. It returns the object, with one call and no sleeps.
  - **`test_invalid_answers_retry_then_succeed`,** parametrized. The first answer is one of these:
    - a 200 HTML page;
    - a stream with empty text;
    - text `Here is the JSON: {"summary": "x"}`;
    - text `["a"]`;
    - a stream cut by `stop_reason="max_tokens"` with text `{"summary": "o`.

    The second answer is valid. There are 2 calls, and the sleeps are `[0.25]`.
  - **`test_invalid_answers_exhaust_retries`.** Three HTML pages raise `InvalidAnswer`, after 3 calls, with sleeps `[0.25, 0.5]`.
  - **`test_refusal_fails_at_once`.** A stream with `stop_reason="refusal"` and no text raises `InvalidAnswer`, after 1 call, with no sleeps.
  - **`test_failures_that_do_not_retry`,** parametrized. Each case makes 1 call:
    - 401 `authentication_error` raises `AuthFailed`;
    - 402 `billing_error` raises `InsufficientBalance`;
    - 429 with `{"type": "error", "error": {"type": "rate_limit_error", "message": "…", "details": {"error_code": "enforced_spend_limit_reached"}}}` raises `InsufficientBalance`;
    - 400, 403, 404, and 413 raise `ProviderError`, and are neither `RateLimited` nor `InsufficientBalance`;
    - a 200 stream with `error_event("invalid_request_error")` raises `ProviderError`.
  - **`test_temporary_errors_retry_then_succeed`,** parametrized. The first answer is one of these, and the second is valid. Each case makes 2 calls:
    - 429 `rate_limit_error`;
    - 500, 502, 503, or 504 `api_error`;
    - 529 `overloaded_error`;
    - a 200 stream with `error_event("overloaded_error")`;
    - a 200 stream with `error_event("api_error")`.
  - **`test_rate_limit_exhaustion`.** Three 429 answers raise `RateLimited`, after 3 calls, with sleeps `[0.25, 0.5]`.
  - **`test_overload_exhaustion`.** Three 529 answers raise `ProviderError`, not `RateLimited`, after 3 calls, with sleeps `[0.25, 0.5]`.
  - **`test_connection_timeout_names_the_base_url`,** parametrized over `chat_json` and `list_models`. The handler raises `httpx2.ConnectTimeout`. The client raises `ConnectionFailed`, whose message contains `https://anthropic.example`, after 1 call.
  - **`test_model_list_rejected_key`.** A 401 `authentication_error` on `/v1/models` makes `list_models()` raise `AuthFailed`, after 1 call.
  - **`test_model_list_that_is_not_a_model_list_exhausts_retries`,** parametrized over a 200 HTML page and a 200 `{"data": "busy", "has_more": false}`, as `tests/test_llm_client.py:300-311` does for the OpenAI-compatible client. `list_models()` raises `ProviderError`, after 3 calls.
  - **`test_fallback_models`,** parametrized:
    - For each of `claude-fable-5-2`, `claude-fable-5-1`, `claude-opus-5-5`, `claude-opus-5`, and `claude-sonnet-5-5`: the request's path is `/v1/messages`, its query has `beta=true`, its `anthropic-beta` header contains `server-side-fallback-2026-07-01`, and its body has `fallbacks == "default"`.
    - For `claude-haiku-5-5` and `claude-sonnet-4-6`: there is no `beta` query, no `anthropic-beta` header, and no `fallbacks` key.
  - **`test_usage_sums_input_cache_and_output_tokens_across_threads`.**
    - Before any call, `usage_totals()` is `None`.
    - Four calls in a `ThreadPoolExecutor(max_workers=4)` each report input 10, cache creation 2, cache read 3, and output 5.
    - `usage_totals()` is then `(60, 20)`.
  - **`test_usage_of_the_wrong_shape_is_not_counted`,** parametrized over `(input_tokens, output_tokens, expected)`: `("seven", 3, (0, 3))`, `(7, "three", (7, 0))`, and `("seven", "three", (0, 0))`. Use words, not digits: the SDK turns `"7"` into 7 (always for `output_tokens`, and for `input_tokens` whenever `message_start`'s usage is otherwise valid). When both counts are words, `usage_totals()` is `(0, 0)`, not `None`, because usage was reported.

  They fail at collection, because `catchup.llm.anthropic_client` does not exist.
- [x] 1.2 Write `backend/src/catchup/llm/anthropic_client.py` as design D3–D10 describe: `AnthropicModelClient`, `FALLBACK_MODELS`, and `DEFAULT_MODEL = "claude-opus-5-5"`. Create the SDK client with `base_url`, `api_key`, `max_retries=0`, and `http_client`. Use the SDK's typed errors, their `.type`, and, for the spend limit, `.body["error"]["details"]["error_code"]`; never their message text. Catch `AssertionError` only around `get_final_message()`. In `list_models()`, read each page as raw JSON with `self._client.models.with_raw_response.list(timeout=15.0)` and `.json()`, then with `after_id=<last_id>` while `has_more` is true, inside the same retry and error mapping as `chat_json()`. A page that is not JSON (`ValueError`) or not a model list is retried, then raises `ProviderError`. Do not use the typed `client.models.list()`: its `ModelInfo` turns `"12"` into 12 and `true` into 1, and a 200 HTML page raises `AttributeError`. Then run, and watch pass:
  - `uv run --offline pytest tests/test_anthropic_client.py`;
  - `uv run --offline pytest tests/test_llm_client.py`, unchanged;
  - the full `uv run --offline pytest`.
- [x] 1.3 Run these mutations one at a time, each against `tests/test_anthropic_client.py`, and record which tests fail:

  | Mutation | Change | Expected failing test |
  | --- | --- | --- |
  | A1 | no output floor | `test_json_answer_request_shape_and_no_key_in_logs` |
  | A2 | a refusal treated as an empty answer | `test_refusal_fails_at_once` |
  | A3 | 529 not temporary | the 529 cases and `test_overload_exhaustion` (by its call count) |
  | A4 | the spend-limit check removed | the spend-limit case |
  | A5 | a fallback sent for every model | the `claude-haiku-5-5` and `claude-sonnet-4-6` cases |
  | A6 | cache tokens not added | the usage test |
  | A7 | the `base_url=` argument removed | `test_host_environment_credentials_are_never_used` |
  | A8 | no fence parsing | the fenced test |
  | A9 | retired models kept | the model-list test |
  | A10 | stream `error` events never retried | the two stream-error cases of `test_temporary_errors_retry_then_succeed` |

## 2. Provider setting, runs, and README (D1, D11–D13)

- [x] 2.1 Write these tests and watch them fail. Fixtures that need a database or the API fail on the missing column, field, or module.

  **In `backend/tests/test_db.py`.** First make the only allowed edits to existing tests there:
  - change `"0008_run_progress"` to `"0009_model_provider"` in the four head-revision assertions (lines 115, 284, 324, and 465);
  - add `assert (migrations / "versions" / "0009_model_provider.py").is_file()` to `test_migrations_live_inside_package`, after its `0008` line (line 97).

  Then add, following `test_run_progress_migration_fills_sources_total_and_downgrades`:
  - **`test_model_provider_migration_defaults_existing_config_and_downgrades`.**
    - Upgrade to `0008_run_progress`, and insert one `model_config` row with SQL.
    - Upgrade to head. `provider` is `openai_compatible`, and the other columns are unchanged.
    - Downgrade to `0008_run_progress`. There is no `provider` column, and the row is kept.

  **In a new file `backend/tests/test_model_providers.py`:**
  - `make_model_client(…, "openai_compatible")` returns a `ModelClient`, and so does a call without a provider.
  - `"anthropic"` returns an `AnthropicModelClient`, and the `http_client` and `sleep` options are passed on.
  - `"gemini"` raises `ValueError`.
  - The default base URLs are `https://api.deepseek.com` and `https://api.anthropic.com`.

  **In `backend/tests/test_settings_api.py`.** First make the only allowed edits to existing tests there:
  - `FakeProvider.__call__` takes `(base_url, api_key, model, provider)`, and records a 4-tuple;
  - `:107` expects `("https://provider.example/v1", KEY, "provider-current", "openai_compatible")`;
  - `test_save_and_read_encrypted_configuration` (`:53-56`) expects `{"provider": "openai_compatible", "base_url": "https://provider.example/v1", "model_id": "provider-current", "key_set": True, "api_key_last4": "4821"}`.

  Then add:
  - **`test_read_without_configuration_reports_the_default_provider`.** `provider == "openai_compatible"` and `base_url == "https://api.deepseek.com"`.
  - **`test_save_and_read_anthropic_configuration`.**
  - **`test_save_without_provider_keeps_the_saved_provider`.**
  - **`test_unknown_provider_is_refused`.** After `save(client)`, a PUT `{"base_url": "https://provider.example/v1", "model_id": "provider-current", "api_key": "new-test-only-key", "provider": "gemini"}` and a test `{"api_key": "new-test-only-key", "provider": "gemini"}` each give 422 `invalid_model_config` with "Choose a supported model provider.". The row is unchanged, and `fake.calls == []`.
  - **`test_provider_change_requires_a_new_key`.** After `save(client)` (OpenAI-compatible, `https://provider.example/v1`), a PUT `{"base_url": "https://provider.example/v1", "model_id": "provider-current", "api_key": "", "provider": "anthropic"}` and a test `{"provider": "anthropic"}` each give 422 `api_key_required`. Both keep the saved base URL, so only the provider rule can refuse them. The row is unchanged, and `fake.calls == []`.
  - **`test_provider_change_clears_the_context_window`.** After `save(client)`, set `context_window = 1_000_000`. A PUT `{"base_url": "https://provider.example/v1", "model_id": "provider-current", "api_key": "new-test-only-key", "provider": "anthropic"}` succeeds, and `context_window` is `None`. The base URL and model stay the same, so only the provider change can clear it.
  - **`test_connection_test_passes_the_provider`.**
    - With a key and `"anthropic"`, the last call ends with `"anthropic"`.
    - With a saved Anthropic row and no provider in the body, the last call also ends with `"anthropic"`.

  **In `backend/tests/test_model_errors.py`:** the only allowed edit is that the lambdas at `:91` and `:159` take `(base, key, model, provider)`.

  **In `backend/tests/test_digest_runner.py`:**
  - **`test_run_passes_the_saved_provider_to_every_client`.**
    - Call `seed(environment)`, then set `ModelConfig.provider = "anthropic"` in a session.
    - The factory records its arguments and returns a `FakeModel`.
    - The run succeeds, and every recorded call has four arguments ending in `"anthropic"`. These are the context-window lookup and the summary client.

  **In a new file `backend/tests/test_anthropic_runs.py`.** Follow `tests/test_model_errors.py::test_live_failure_recovers_end_to_end`:
  - Set the factory to `lambda base, key, model, provider: make_model_client(base, key, model, provider, http_client=httpx2.Client(transport=httpx2.MockTransport(handle)), sleep=sleeps.append)`. Build the `httpx2.Client` inside the lambda, as `tests/test_model_errors.py:91-93` does: the run closes the first client (`runner.py:284`), and the SDK's `close()` also closes the `http_client` passed to it.
  - Use `seed(environment, count=3)`, and set the row's provider to `anthropic`, its base URL to `https://anthropic.example`, and its model to `claude-opus-5-5`.
  - The handler routes by the request body:
    - `item_refs` in `system` means grouping;
    - `Title: Item N` in `messages[0]["content"]` means item N.
  - **`test_anthropic_run_saves_summaries_groups_and_usage`:**
    - **Answers.** `/v1/models` lists `claude-opus-5-5` with `max_input_tokens` 1000000.
      - Item 0 answers 529, then valid JSON.
      - Item 1 answers fenced JSON.
      - Item 2 answers a refusal.
      - Grouping answers one topic with `i1`, `i2`, and `i3`.
    - **Result.** The run succeeds. Items 0 and 1 have their summaries, and item 2 is unavailable.
    - **Attempts** are `{"Item 0": 2, "Item 1": 1, "Item 2": 1, "grouping": 1}`.
    - **Fallback.** Every `/v1/messages` body has `fallbacks == "default"`.
    - **Usage.** The run's `prompt_tokens` and `completion_tokens` are `(40, 20)`: Item 0's second answer, Item 1, Item 2's refusal, and grouping each report input 10 and output 5 (`stream_body` defaults), and the 529 reports none. A refusal's usage is counted.
    - **Context window.** `ModelConfig.context_window == 1_000_000`.
  - **`test_anthropic_rejected_key_fails_the_run`.** A 401 makes the run fail with `auth_failed`, and its items stay pending.

  **In a new file `backend/tests/test_readme_providers.py`.** Follow `tests/test_readme_context.py`, but compare after `" ".join(readme.split())`, as `collapse_whitespace` in `tests/test_install_docs.py:68-69` does, so README line wrapping does not matter. `README.md` contains each of these:
  - "Supported model providers";
  - "OpenAI-compatible";
  - "Anthropic";
  - "https://api.anthropic.com";
  - "claude-opus-5-5";
  - "at least 16,000 output tokens";
  - "fallback model";
  - "Changing the provider or its URL requires entering the API key again".
- [x] 2.2 Implement the provider setting:
  - **Data.** `models.py` gets `ModelConfig.provider`. Add `migrations/versions/0009_model_provider.py`, whose docstring notes that a downgrade turns Anthropic configurations into OpenAI-compatible ones.
  - **Factory.** Add `llm/providers.py`.
  - **API.** In `api/settings.py`, read and write `provider`, extend the key rule and the context-window clearing to the provider, and use the factory with the provider.
  - **Wiring.** `main.py` uses `make_model_client`. `digest/runner.py` reads `config.provider` with the rest of the configuration and passes it to both factory calls.

  Run every test file of 2.1 except `tests/test_readme_providers.py`, which can pass only after task 2.3 writes the README. Then run the full suite without it, `uv run --offline pytest --ignore=tests/test_readme_providers.py`, and watch them pass.
- [x] 2.3 Update `README.md`:
  - **Intro.** The intro at `:3-4` names both providers.
  - **Key rule.** The key rule at `:101-102` reads "Changing the provider or its URL requires entering the API key again; CatchUp will not send a stored key to a new provider or address."
  - **New section.** Add a "Supported model providers" section before "Supported sources". It covers:
    - OpenAI-compatible: DeepSeek is tested, and its base URL is the default;
    - Anthropic:
      - the base URL `https://api.anthropic.com`, and that a key comes from the Anthropic Console;
      - that models are listed from the account, with `claude-opus-5-5` first when available, and its price per million tokens ($4 input, $20 output);
      - that some models always think, so CatchUp allows at least 16,000 output tokens;
      - that for the five models in design D8 a refused request is retried on a fallback model chosen by Anthropic and billed at that model's rates;
      - that a custom address must pass Anthropic's beta headers;
      - that the SDK also reads `ANTHROPIC_CUSTOM_HEADERS` from the server's environment;
    - that collected content is sent to the chosen provider.

  Then `uv run --offline pytest tests/test_readme_providers.py tests/test_readme_context.py tests/test_install_docs.py` passes, and so does the full `uv run --offline pytest`.
- [x] 2.4 Run these mutations one at a time, and record which tests fail:

  | Mutation | Change | Expected failing tests |
  | --- | --- | --- |
  | P1 | the runner passes `"openai_compatible"` instead of the saved provider | the runner test and the Anthropic run test |
  | P2 | the key rule ignores the provider | `test_provider_change_requires_a_new_key` |
  | P3 | a provider change keeps the context window | `test_provider_change_clears_the_context_window` |
  | P4 | the migration has no server default | the migration test |
  | P5 | the test endpoint ignores the body's provider | `test_connection_test_passes_the_provider` |
  | P6 | provider validation removed | `test_unknown_provider_is_refused` |
  | Doc | the "Supported model providers" heading removed | the README test |

## 3. Settings page (D14)

- [x] 3.1 In `frontend/src/pages/Settings.test.tsx`, write these tests and watch them fail. They fail because there is no Provider select, and because the bodies have no `provider`.
  - **Test types.** Add `provider` to `ModelBody`, and an optional `provider` to `mockModelProvider`'s `saved` type.
  - **Existing tests.** The only allowed edit to them is adding `provider: 'openai_compatible'` to every expected PUT body (`modelPuts()` comparisons) and every expected test-request body. Mocked GET answers may stay without `provider`: the page treats a missing provider as OpenAI-compatible.
  - **`shows the saved provider as the first field of the Model provider group`.** A saved `provider: 'anthropic'` with `https://api.anthropic.com` gives a Provider select reading "Anthropic". It comes before Base URL in document order, inside `modelSection()`.
  - **`fills in the Anthropic address and empties the model list when Anthropic is chosen`.** This is the spec scenario "Choose Anthropic". Check the Base URL value, the Model select's only option "Test the connection to list models", that "Saved key ending in 1234" is absent, and the hint "Enter an API key for this provider.".
  - **`restores the saved configuration when the saved provider is chosen again`.** This is the scenario "Back to the saved provider".
  - **`tests and saves a new provider with its key`.** This is the scenario "Test a new provider".
    - The test body is `{ base_url: 'https://api.anthropic.com', api_key: 'key-7d2e', provider: 'anthropic' }`.
    - The PUT body is `{ base_url: 'https://api.anthropic.com', model_id: 'claude-opus-5-5', api_key: 'key-7d2e', provider: 'anthropic' }`.
    - The status reads exactly "Connection succeeded. Saved key ending in 7d2e with model claude-opus-5-5. Choose another model to change it.".
  - **`names the Anthropic address in the invalid-URL message`.** With Anthropic and a model selected, Save is refused with `invalid_model_config`. The Base URL field's message reads "Enter a valid provider URL, such as https://api.anthropic.com.".
  - **`sends the provider with Save`.**
  - **`has no accessibility violations with Anthropic chosen`.** Run `expectAccessible` on the rendered page.
- [x] 3.2 Implement design D14 in `frontend/src/pages/Settings.tsx`. In `frontend/`, run `npm test -- --run` and `npm run build`, and watch them pass.
- [x] 3.3 Run these mutations one at a time, each against `Settings.test.tsx`, and record which tests fail:

  | Mutation | Change | Expected failing test |
  | --- | --- | --- |
  | F1 | the test request omits `provider` | `tests and saves a new provider with its key` |
  | F2 | the base URL is not switched on a provider change | the "Choose Anthropic" test |
  | F3 | the saved-key text is not hidden for another provider | the "Choose Anthropic" test |
  | F4 | the invalid-URL example always names DeepSeek | `names the Anthropic address in the invalid-URL message` |

## 4. Checks and report

- [x] 4.1 Run these checks and keep their output for the final report:
  - in `backend/`: `uv run --offline pytest`;
  - in `frontend/`: `npm test -- --run` and `npm run build`;
  - in `extension/`: `npm ci --offline --no-audit --no-fund`, then `npm test -- --run` and `npm run build`. The extension is unchanged; this matches CI;
  - `DO_NOT_TRACK=1 openspec validate add-anthropic-provider --strict`;
  - `git diff --check`.

  All pass.
- [x] 4.2 Write `docs/process/test-report-add-anthropic-provider.md`. It holds:
  - the commands of 4.1, with their counts;
  - both probes of 1.1, including the SDK version and the exception class;
  - every mutation, with the tests that failed;
  - any deviation from this plan.
- [x] 4.3 Add one Droid entry for this run to `docs/process/ai-usage-log.md`, in the format of the Droid entry for `improve-context-pass-speed-and-progress`. It holds:
  - the prompt (an excerpt);
  - the tool and model;
  - the outcome;
  - what failed and how it was handled.

  Leave the session line (session id, turns, minutes) to Claude Code.

## 5. Fix round 1 (review findings)

Claude Code's review of `410df93..b63cc84` confirmed these, and the user decided the second on 2026-11-22 (design D9 now says so):
- **A stream cut by the network fails the whole run.** With SDK 1.13.0, an `httpx2.ReadTimeout` or `httpx2.RemoteProtocolError` raised while the stream is read is not an SDK error, so `_call` lets it through. The run then ends `run_failed`, instead of marking that one item's summary unavailable (design D7: connection errors are `ConnectionFailed`).
- **A server-side fallback undercounts usage.** Top-level `usage` covers only the attempt that produced the message; `usage.iterations` lists every attempt, declined ones included, and an attempt declined mid-stream is billed at normal rates.
- **A test that finishes after the user switched providers shows its models under the other provider.** `testConnection()` sets the visible model list and model without checking that the tested provider is still selected.
- **No test covers "Back to the saved provider" without a test in between.** Removing the page-load `setSavedModels(...)` leaves every test green.

- [ ] 5.1 Write these tests and watch them fail as stated:
  - in `backend/tests/test_anthropic_client.py`:
    - give `stream_body` one more keyword, `iterations=None`; when it is given, the `message_delta` event's `usage` also holds `"iterations": iterations`. Existing calls do not change.
    - add a class `BrokenStream(httpx2.SyncByteStream)` whose `__iter__` yields the `message_start` event of `stream_body("{}")` (the response content up to and including the first blank line) and then raises the exception it was given.
    - **`test_stream_cut_by_the_network_names_the_base_url`,** parametrized over `httpx2.ReadTimeout("test timeout")` and `httpx2.RemoteProtocolError("test drop")` (ids `read-timeout`, `dropped`). The only answer is `httpx2.Response(200, headers={"content-type": "text/event-stream"}, stream=BrokenStream(exc))`. `chat_json([], 200)` raises `ConnectionFailed` whose message contains `BASE`, after 1 request, with no sleeps. It fails on the current code, because the raw `httpx2` exception comes out.
    - **`test_fallback_usage_counts_every_attempt`.** Model `claude-opus-5-5`. The answer is `stream_body('{"summary": "ok"}', input_tokens=12, output_tokens=5, iterations=[{"type": "message", "model": "claude-opus-5-5", "input_tokens": 10, "output_tokens": 7, "cache_creation_input_tokens": 1, "cache_read_input_tokens": 2}, {"type": "fallback_message", "model": "claude-opus-5", "input_tokens": 12, "output_tokens": 5, "cache_creation_input_tokens": 0, "cache_read_input_tokens": 0}])` (each entry has the fields of the SDK's iteration usage types, `model` included). After `chat_json`, `usage_totals()` is `(25, 12)`. It fails on the current code with `(12, 5)`.
  - in `frontend/src/pages/Settings.test.tsx`, inside the same `describe` as `tests and saves a new provider with its key`:
    - **`restores the saved model after switching providers without a test`.** `mockModelProvider()`; render; choose "Anthropic" in the Provider select, then "OpenAI-compatible" again. Base URL is `https://api.deepseek.com`, the Model select's value is `saved-model` and its only option is `saved-model`, and `document.getElementById('key-saved')` has text "Saved key ending in 1234". It passes on the current code; mutation N4 in 5.3 shows that it can fail.
    - **`lists the tested models of a saved Anthropic provider`.** `mockModelProvider({ saved: { provider: 'anthropic', base_url: 'https://api.anthropic.com', model_id: 'claude-opus-5-5', key_set: true, api_key_last4: '1234' }, test: () => respond({ ok: true, models: ['claude-opus-5-5', 'claude-sonnet-5-5'] }) })`; render; wait for the Provider select; click Test connection; wait for the text `Connection succeeded. Saved model claude-opus-5-5.`. The Model select's options, read with `within(screen.getByLabelText('Model')).getAllByRole('option').map(option => option.textContent)`, are `['claude-opus-5-5', 'claude-sonnet-5-5']`. It passes on the current code; mutation N5 in 5.3 shows that it can fail.
    - **`keeps the tested models out of the other provider's list`.** Following the pending-promise pattern at `Settings.test.tsx:789-791`: `mockModelProvider({ test: () => pending, put: body => respond({ provider: body.provider, base_url: body.base_url, model_id: body.model_id, key_set: true, api_key_last4: '7d2e' }) })`; render; choose "Anthropic", type `key-7d2e` into API key, and click Test connection. Before the test answers, choose "OpenAI-compatible". Then resolve it inside `act` with `respond({ ok: true, models: ['claude-opus-5-5', 'claude-sonnet-5-5'] })`. The tested configuration is still saved: `await waitFor(() => expect(modelPuts()).toEqual([{ base_url: 'https://api.anthropic.com', model_id: 'claude-opus-5-5', api_key: 'key-7d2e', provider: 'anthropic' }]))`. The Provider select's value is `openai_compatible`, Base URL is `https://api.deepseek.com`, and the Model select's options, read with `within(screen.getByLabelText('Model')).getAllByRole('option').map(option => option.textContent)`, are exactly `['saved-model']`. Then click Save: `await waitFor(() => expect(modelPuts()).toHaveLength(2))`, and `modelPuts()[1]` equals `{ base_url: 'https://api.deepseek.com', model_id: 'saved-model', api_key: '', provider: 'openai_compatible' }`. The Model select shows its first option even when the page holds another model, so only this request shows which model the page holds; the mocked PUT accepts the body, although the real server would refuse it because the provider changed without a key. It fails on the current code, because the Claude models are listed.

  Change no existing test, other than the new `iterations` keyword of `stream_body`.
- [ ] 5.2 Fix them:
  - in `backend/src/catchup/llm/anthropic_client.py`, `_call` also turns `httpx2.TransportError` into `ConnectionFailed`: `except (anthropic.APIConnectionError, anthropic.APITimeoutError, httpx2.TransportError) as exc:`;
  - in `chat_json`, when `getattr(usage, "iterations", None)` is a non-empty list, sum input tokens (`input_tokens + cache_creation_input_tokens + cache_read_input_tokens`) and `output_tokens` over its entries; otherwise count the top-level `usage` as now. The entries are SDK objects (`BetaMessageIterationUsage`, `BetaFallbackMessageIterationUsage`), not dicts, so read each field with `getattr(entry, field, None)`, and count only integer values. Usage is still reported once per answer, under the lock;
  - in `frontend/src/pages/Settings.tsx`, keep the selected provider in a ref (`const selectedProvider = useRef(provider)`). Set `selectedProvider.current` in both places that call `setProvider`: the page load (next to `setProvider(settings.provider ?? 'openai_compatible')`) and `chooseProvider`. In `testConnection()`, after the test answers, call `setModels(result.models)` and `setModel(chosen ?? '')` only when `selectedProvider.current === testedProvider`; compute `replaced` and `chosen` as now, and keep the save of the tested configuration (`queueModelSave`) and the "listed no models" status as they are.

  Then run `uv run --offline pytest tests/test_anthropic_client.py tests/test_anthropic_runs.py tests/test_model_providers.py`, the full `uv run --offline pytest`, and in `frontend/` `npm test -- --run` and `npm run build`, and watch them pass.
- [ ] 5.3 Run these mutations one at a time, inspect each result before the next, restore the code after each by editing the file back, and confirm the restore by comparing `git diff` with the diff you saved before the mutation (5.1 and 5.2 are not committed yet):

  | Mutation | Change | Expected failing test |
  | --- | --- | --- |
  | N1 | `httpx2.TransportError` removed from that `except` | both cases of `test_stream_cut_by_the_network_names_the_base_url` |
  | N2 | `iterations` ignored, top-level `usage` always used | `test_fallback_usage_counts_every_attempt` |
  | N3 | the `selectedProvider.current === testedProvider` check removed | `keeps the tested models out of the other provider's list` |
  | N4 | the page-load `setSavedModels(settings.model_id ? [settings.model_id] : [])` removed | `restores the saved model after switching providers without a test` and `keeps the tested models out of the other provider's list` (no option is left after switching back) |
  | N5 | the page-load `selectedProvider.current = …` assignment removed | `lists the tested models of a saved Anthropic provider` |
  | N6 | `setModel(chosen ?? '')` moved out of the `selectedProvider.current === testedProvider` check | `keeps the tested models out of the other provider's list` (its second PUT has `model_id: 'claude-opus-5-5'`) |
- [ ] 5.4 Run the commands of task 4.1 again (no `docker build`, `scripts/docker-smoke.sh`, or any Docker command, and do not touch port 8800). Add a "Fix round 1" section to `docs/process/test-report-add-anthropic-provider.md` with the red and green results of 5.1 and 5.2, N1–N6, and the commands' counts. Add one Droid entry for this round to `docs/process/ai-usage-log.md`, after the latest entry, with a verbatim prompt excerpt in quotation marks and the tool and model as the earlier Droid entries name them; leave out the session line, which Claude Code adds at review.

  Verify: every command passes, and the report has the actual numbers.
