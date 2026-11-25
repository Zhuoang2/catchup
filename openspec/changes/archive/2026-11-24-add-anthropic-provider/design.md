# Design

## Context

See `proposal.md` (Why) for the problem. Facts that shape the approach, checked on main `795c5e7`:

- **Interface the stages use.** Summaries and grouping call only `chat_json(messages, max_tokens) -> dict`, through a client the runner builds (`digest/summarize.py:91,101`, `digest/group.py:84,109`). The runner and the settings test also call `list_models()`, `usage_totals()`, and `close()` (`digest/runner.py:284-286,455`, `api/settings.py:263-264`). Errors cross the boundary as `ModelError` subclasses from `llm/client.py:20-45`: `AuthFailed`, `InsufficientBalance`, `RateLimited`, `ProviderError`, `InvalidAnswer`, and `ConnectionFailed`. The runner and the stages handle only those (`runner.py:544-547`, `summarize.py:128-131`, `group.py:72-78`).
- **Prompts.** Every prompt is one `system` message followed by one `user` message. It ends with "Return only json" and an example object (`llm/prompts.py:58-153`). Summary calls ask for 4,096 output tokens (`prompts.py:9`). Grouping calls ask for up to 32,768 (`prompts.py:12-14`). Four worker threads share one client (`summarize.py:150-153`).
- **Retries.** `ModelClient._call` makes up to 3 attempts, with sleeps of 0.25 s and 0.5 s. It retries 429, 500, 502, 503, and 504, and answers that are empty or not a JSON object. 401 and 402 fail at once (`llm/client.py:78-100`). The SDK's own retries are off (`max_retries=0`, `:71-73`).
- **Factory.** `app.state.model_client_factory` (`main.py:113`) and `get_model_client_factory()` (`api/settings.py:178-179`) return `ModelClient`. They are called as `factory(base_url, key, model_id)`. Tests replace the factory 57 times in 10 files. 54 of those replacements take any arguments (`lambda *_`). The three that take exactly three are `tests/test_model_errors.py:91,159` and `FakeProvider.__call__` (`tests/test_settings_api.py:20-22`, installed at `:38`). `tests/test_settings_api.py:107` compares a recorded call as a 3-tuple.
- **Dependencies.** `openai>=3,<4` and `httpx2>=2,<3` are already locked (`backend/pyproject.toml`). The OpenAI client tests drive the SDK through `httpx2.MockTransport` (`tests/test_llm_client.py:18-37`). The Docker image installs with `uv sync --locked` (`Dockerfile:15,17`).
- **Anthropic facts.** These come from Claude Code's `claude-api` reference (bundled with Claude Code 2.1.330; its model table was cached on 2026-11-03), and from reading the source of `anthropic` 1.13.0. That version is already unpacked in this machine's uv cache, and was read without installing it.
  - **Default model.** The default is `claude-opus-5-5`, at $4 per million input tokens and $20 per million output tokens. For comparison, `claude-sonnet-5-5` costs $2 and $10, and `claude-haiku-5-5` costs $0.10 and $0.50.
  - **Thinking.** On `claude-opus-5-5`, thinking cannot be turned off, and its default effort is `medium`.
  - **Sampling and prefill.** `temperature`, `top_p`, and `top_k` return 400 on current models. On API version `2026-10-21` they return 400 on every model. Prefilling the assistant turn returns 400.
  - **Errors.** 400, 401, 402 (billing), 403, 404, and 413 are not retryable. 429 is retryable, except a spend-limit 429. That one has no `retry-after` header, and its `error.details.error_code` is `enforced_spend_limit_reached`. 500 and 529 (overloaded) are retryable.
  - **Refusals.** A refusal is `stop_reason: "refusal"` with HTTP 200. The server-side fallback is opt-in: beta `server-side-fallback-2026-07-01` plus `fallbacks: "default"`. The reference says to include it by default for `claude-fable-5-2`, `claude-fable-5-1`, `claude-opus-5-5`, `claude-opus-5`, and `claude-sonnet-5-5`. `claude-haiku-5-5` has no server-side fallback.
  - **Streaming.** The reference says to stream long or high-`max_tokens` requests and read `get_final_message()`. A non-streaming request with a large `max_tokens` raises `ValueError` in the SDK, unless an explicit timeout is passed.
  - **Structured outputs.** These use `output_config.format`. The reference lists the models that support them. Every object in the schema needs `additionalProperties: false`.
  - **SDK versions.** Python `anthropic` 1.x is built on `httpx2`. 2.0.0 is the first release that sends API version `2026-10-21` by default. 1.13.0 sends `2023-06-01` (`anthropic/_constants.py:7`). Its dependencies are `anyio`, `docstring-parser`, `httpx2`, `jiter`, `pydantic`, `sniffio`, and `typing-extensions`. Only `docstring-parser` is not in `uv.lock` yet.
  - **Credentials.** In SDK 1.13.0, an explicit `api_key=` stops the client from reading `ANTHROPIC_API_KEY`, `ANTHROPIC_AUTH_TOKEN`, or profiles. An explicit `base_url=` wins over `ANTHROPIC_BASE_URL`. `ANTHROPIC_CUSTOM_HEADERS` is always read (`anthropic/_client.py:157-253`).
  - **Model list.** In SDK 1.13.0, `ModelInfo` has `max_input_tokens`, `lifecycle` (`active`, `deprecated`, or `retired`), and `capabilities`. `capabilities` includes `structured_outputs.supported`, and `effort` and `thinking` support (`anthropic/types/model_info.py`, `model_capabilities.py`).
  - **Stream errors.** In SDK 1.13.0, 529 becomes `OverloadedError`. An `error` event inside a stream raises a status error built from the 200 response, with `.type` taken from the body (`anthropic/_streaming.py:138-151`, `_client.py:558-583`). `MessageStream.get_final_message()` asserts that a message arrived (`anthropic/lib/streaming/_messages.py:94-100`). A 200 body with no stream events therefore raises `AssertionError`.

## Goals / Non-Goals

**Goals:**
- Anthropic works with the same prompts, stages, error kinds, progress, and usage totals as the OpenAI-compatible provider.
- The OpenAI-compatible path behaves exactly as before. `llm/client.py`, `llm/prompts.py`, `digest/summarize.py`, and `digest/group.py` stay unchanged.
- A key is never sent to a provider or address it was not saved for, and an Anthropic key in the host environment is never used.

**Non-Goals:**
- **Thinking or effort settings.** That is #4. See D11 for what this change leaves for it.
- **Prompt caching.** The system prompts are a few hundred tokens, below the smallest cacheable prefix. Item text changes with every call.
- **Other ways to reach Claude.** Clients for Amazon Bedrock, Google Vertex AI, or Microsoft Foundry are not in this change.
- **More than one saved configuration.** See U5.
- **Hiding Anthropic models by capability.** See U2.

## Decisions

### D1. A second client, picked by a provider factory

- **New module.** `llm/anthropic_client.py` defines `AnthropicModelClient(base_url, api_key, model="", *, http_client=None, sleep=time.sleep)`. It has the same methods as `ModelClient`, and imports the error classes and `ModelInfo` from `llm/client.py`.
- **Factory.** `llm/providers.py` defines `PROVIDERS = ("openai_compatible", "anthropic")` and the default base URLs: `https://api.deepseek.com` and `https://api.anthropic.com`. It also defines `make_model_client(base_url, api_key, model="", provider="openai_compatible", **options)`, which returns either client, passing `options` through (tests pass `http_client` and `sleep`). An unknown provider raises `ValueError`.
- **Wiring.** `main.py` and `get_model_client_factory()` use `make_model_client`. Every call site passes the provider as a fourth positional argument, so the 54 `lambda *_` replacements keep working. The three fixed-arity fakes, and the 3-tuple at `test_settings_api.py:107`, are updated.
- **Alternatives:**
  - A shared base class for both clients. Rejected: it would change the tested OpenAI client, and the retry rules differ (529, refusals, spend limit).
  - LiteLLM, or Anthropic's OpenAI-compatible endpoint. Rejected: the `claude-api` reference says never to fall back to OpenAI-compatible shims, and LiteLLM is a large dependency.
  - Passing the provider as a keyword argument. Rejected: `lambda *_` does not accept keywords, so all 54 replacements would break.

### D2. The official SDK (decision U1)

The `claude-api` reference says to use the official SDK in a Python project, and not to mix it with hand-written HTTP calls. Raw HTTP through `httpx2` would add no dependency, but it would re-implement request building, streaming, and typed errors. Tests drive the SDK through `httpx2.MockTransport`, as for `openai`.

### D3. Request shape

- **System text.** The leading `system` messages, joined with a blank line, become `system`. The rest stay in `messages`, in order.
- **Thinking and sampling.** No `thinking`, `temperature`, `top_p`, `top_k`, or prefill is sent. The model's default thinking and effort apply.
- **Output limit.** `max_tokens` is `max(requested, 16_000)` (D6).
- **Fallback.** For the five models in D8, the call goes through `client.beta.messages.stream(…, betas=["server-side-fallback-2026-07-01"], fallbacks="default")`. All other models use `client.messages.stream(…)`.
- **Credentials.** `base_url` and `api_key` are always passed explicitly, so `ANTHROPIC_API_KEY`, `ANTHROPIC_AUTH_TOKEN`, profiles, and `ANTHROPIC_BASE_URL` are never used.
- **Logging.** The module sets the `anthropic` logger to WARNING, as `llm/client.py:16-17` does for `openai`.

### D4. Streaming, and answers that are not a message stream

- **Streaming.** Every call streams, and reads `stream.get_final_message()`. Grouping asks for up to 32,768 tokens, and thinking can take minutes. Streaming avoids the SDK's non-streaming guard and the 300 s read timeout. The timeout is the same as the OpenAI client's: connect 10 s, read 300 s, write 10 s, pool 10 s. Pings keep a slow stream alive.
- **No message stream.** A 200 answer with no stream events, such as an HTML page from a wrong base URL, ends in `AssertionError` from the SDK's stream helper. The client converts only that error, raised by `get_final_message()`, to an invalid answer, which is retried. It never catches `Exception` broadly.
- **Probe first.** Task 1.1 probes this against the locked SDK version before the code relies on it.

### D5. JSON answers (decision U2)

- **Recommended: prompt-only JSON.** The prompts already ask for JSON and show an example.
  - The client concatenates the text blocks of the final message, and parses them as a JSON object.
  - If the whole text is one fenced code block (```` ```json ```` or ```` ``` ````), it parses the block's content.
  - Anything else is an invalid answer, retried up to 3 attempts, as today.
  - This works with every Claude model and every prompt.
- **Alternative: structured outputs (`output_config.format`).** These guarantee parseable JSON. But:
  - the stages share one `chat_json(messages, max_tokens)` with 15 test fakes, so per-stage schemas would change all of them. One shared schema would need every key optional;
  - the schema would have to follow every JSON key the prompts ask for, so the image changes planned in #65 would need to update it;
  - models without structured-output support would fail every call, unless Settings hid them by `capabilities.structured_outputs`;
  - Claude Code cannot check the schema against the real API, because it does not handle the user's key.

### D6. Output limit of at least 16,000 tokens

Thinking cannot be turned off on `claude-opus-5-5`, and it counts toward `max_tokens`. A 4,096-token summary limit could end in `stop_reason: "max_tokens"` with no text. The `claude-api` reference recommends about 16,000 for ordinary requests. `max_tokens` is a limit, not a charge. Larger grouping limits are kept, because every current model allows at least 64,000.

### D7. Errors and retries

The client turns SDK errors into the existing error kinds. The 3 attempts and the sleeps of 0.25 s and 0.5 s stay as they are.

| Anthropic answer | CatchUp error | Retried |
| --- | --- | --- |
| 401 | `AuthFailed` | no |
| 402, or 429 with `error.details.error_code == "enforced_spend_limit_reached"` | `InsufficientBalance` | no |
| other 429 | `RateLimited` after the last attempt | yes |
| 500, 502, 503, 504, 529, or a stream `error` event of type `overloaded_error` or `api_error` | `ProviderError` after the last attempt | yes |
| any other status (400, 403, 404, 413, …), or a stream `error` event of another type | `ProviderError` | no |
| `APIConnectionError`, `APITimeoutError`, or an `httpx2.TransportError` raised while a stream is read (the SDK wraps only errors while sending) | `ConnectionFailed`, naming the base URL | no |
| 200 with no stream events, no text, or text that is not a JSON object | `InvalidAnswer` after the last attempt | yes |
| `stop_reason == "refusal"` | `InvalidAnswer` at once | no |

`stop_reason == "max_tokens"` is not special: its cut-off text fails to parse, and is retried. Error messages are the fixed strings of `llm/client.py`, never the SDK's text.

### D8. Refusals and fallback models (decision U3)

- **Refusals.** A refusal raises `InvalidAnswer` at once. The stages already handle it: the summary becomes unavailable (`summarize.py:130-131`), and grouping falls back to one topic (`group.py:72-78`).
- **Fallback models.** For `claude-fable-5-2`, `claude-fable-5-1`, `claude-opus-5-5`, `claude-opus-5`, and `claude-sonnet-5-5` (`FALLBACK_MODELS` in the module), the call asks for the server-side fallback, as the `claude-api` reference says to by default. A rescued answer is billed at the fallback model's rates, and the README says so. The client reads only `text` blocks, so the fallback blocks in the answer are ignored.

### D9. Usage

- **Input tokens** are `input_tokens + cache_creation_input_tokens + cache_read_input_tokens`. The cache fields are 0 or missing without caching.
- **Output tokens** are `output_tokens` of the final message.
- **Attempts** (decided by the user on 2026-11-22, after review). When `usage.iterations` lists the attempts of a server-side fallback, input and output tokens are summed over every attempt, declined ones included: top-level `usage` covers only the attempt that produced the message, `usage.iterations` reports every attempt, and an attempt declined mid-stream is billed at normal rates (how earlier declines are billed is on Anthropic's refusals page). Without `iterations`, the top-level `usage` is used as above.
- Like the OpenAI client, the client counts only integer values, under a lock, and `usage_totals()` returns `None` until a call reports usage.

### D10. Model list (decision U4)

- **Listing.** Each page is read as raw JSON through `client.models.with_raw_response.list(timeout=15.0)`, then with `after_id` while `has_more` is true, with the same retries and error mapping as summaries. The typed `client.models.list()` is not used: in SDK 1.13.0 its `ModelInfo` turns `"12"` into 12 and `true` into 1, which the spec's "Invalid value" scenario forbids, and a 200 HTML page raises `AttributeError`. An answer that is not a model list is retried, then raises `ProviderError`, as for the OpenAI-compatible client (`tests/test_llm_client.py:300-311`).
- **Retired models.** Entries with `lifecycle == "retired"` are skipped, because calls to them fail.
- **Context window.** `ModelInfo(id, max_input_tokens)` is used only when `max_input_tokens` is a positive `int`, as `llm/client.py:116-124` does.
- **Order.** `claude-opus-5-5` is moved first when listed, and the rest keep Anthropic's order. Settings already selects the first listed model on a first setup (`Settings.tsx:268-276`), so no other default logic is needed.
- **Hard-coded list.** None; the spec forbids it.

### D11. Room for #4

All request options are built in one method of `AnthropicModelClient`. #4 can add `output_config.effort` there. The model list's `capabilities.effort` and `capabilities.thinking` say which levels each model supports, so #4 can offer only those. Nothing for #4 is built now.

### D12. Storing the provider

- **Column.** Migration `0009_model_provider` (`down_revision = "0008_run_progress"`) adds `model_config.provider`. It is `String(32)`, NOT NULL, with server default `'openai_compatible'`.
- **Downgrade.** The downgrade drops the column.
- **Alternative.** Inferring the provider from the base URL. Rejected: a proxy address would be misread.

### D13. Settings API

- **Reads.** `_public_model` adds `provider`, which is `openai_compatible` when nothing is saved.
- **Inputs.** `ModelInput` and `TestInput` add `provider: str | None = None`. `None` means the saved provider, or `openai_compatible` when nothing is saved. Any other value outside `PROVIDERS` gives 422 `invalid_model_config` with "Choose a supported model provider."
- **Key rule.** The rule at `api/settings.py:228-233,257-258` extends to the provider. Without a new key, a provider that differs from the saved one gives 422 `api_key_required`, with "Enter an API key when changing the provider or its base URL." The factory is not called.
- **Context window.** A provider change clears `context_window`, like a base URL or model change (`:239-240`).
- **Defaults.** `DEFAULT_BASE_URL` moves to `providers.py`.
- **Runner.** It reads `config.provider` once with the rest of the configuration (`runner.py:261`), and passes it to both factory calls.

### D14. Settings page (decision U5)

- **Provider select.** A **Provider** select is the first field of the Model provider group. Its options are "OpenAI-compatible" (`openai_compatible`) and "Anthropic" (`anthropic`). It loads the saved provider, or `openai_compatible` when the field is missing from the answer.
- **Choosing another provider:**
  - Base URL becomes that provider's default;
  - the model list and selection are emptied;
  - the saved-key text is hidden;
  - the key hint reads "Enter an API key for this provider.".
- **Choosing the saved provider again:** the saved base URL, model, model list, and saved-key text come back.
- **Bodies.** Tests, the automatic save, model choices, and Save all send `provider`.
- **Immediate model saves.** The condition for saving a model choice right away (`Settings.tsx:288`) also requires the selected provider to equal the saved one.
- **Example address.** The invalid-URL example (`:228`) uses the selected provider's default address.

### D15. Dependency (decision U1)

- **Before Droid runs.** Claude Code adds `anthropic` to `backend/pyproject.toml`, locks it in `backend/uv.lock`, and commits both on the branch with the plan, after the user approves the download. Droid works offline and cannot do it, and `droid exec -w` sees only committed files.
- **Recommended pin.** `anthropic>=1.13,<2`, locked at exactly 1.13.0: the SDK behavior this plan relies on (type conversion, `AssertionError`, error mapping) was probed on 1.13.0 only. The request shape used here sends no sampling parameters, so moving to 2.x later is small. The changes in 2.x that matter here are that it sends API version `2026-10-21`, sends keys as `Authorization: Bearer`, and makes `MessageParam` a union per role.
- **Network.** `uv lock` needs the network: the uv cache holds the `anthropic` 1.13.0 wheel, but not PyPI's index page for it.

## Decisions for the user (at plan approval)

The user chose the recommended option for U1–U6 on 2026-11-22, and approved the network access `uv lock` needs.

- **U1. SDK and version.**
  - Recommended: the official `anthropic` SDK, pinned `>=1.13,<2` and locked at 1.13.0.
  - Download: the package `anthropic`, plus the new dependency `docstring-parser`, from PyPI (https://pypi.org/project/anthropic/).
    - Wheels, from PyPI's metadata on 2026-11-22: `anthropic-1.13.0-py3-none-any.whl`, 1,958,595 bytes (about 1.9 MB), uploaded 2026-10-09; `docstring_parser-0.18.0-py3-none-any.whl`, 22,484 bytes, uploaded 2026-04-14. Both are already in the local uv cache; `uv lock` still reads PyPI's index over the network.
  - Alternatives: the newest 2.x, which sends API version `2026-10-21`; or raw HTTP through `httpx2`, with no new package.
- **U2. JSON answers.**
  - Recommended: prompt-only JSON, with a single fenced block accepted (D5).
  - Alternative: structured outputs with one shared schema. If chosen, groups 1 and 3 add the schema, its tests, and a capability filter in the model list, and #65 must keep the schema in step.
- **U3. Fallback models.**
  - Recommended: on, for the five models in D8, as the `claude-api` reference says to by default.
  - Alternative: off. Refusals then always make the item's summary unavailable, and group 1 drops the beta call and its tests.
- **U4. Default model.**
  - Recommended: `claude-opus-5-5`, listed first.
  - Alternatives: Anthropic's own order, or a cheaper default such as `claude-sonnet-5-5`.
- **U5. Switching providers.**
  - Recommended: one saved configuration. Switching needs the other provider's key again, and saving replaces the saved key.
  - Alternative: one saved key per provider, which needs a new table and more Settings states.
- **U6. Anthropic base URL.**
  - Recommended: editable, filled with `https://api.anthropic.com`.
  - Alternative: fixed and hidden. Proxies would then not work, and the base URL rules would need a special case.

## Risks / Trade-offs

- **[#40 may also add migration 0009]** → Whichever change merges second renumbers its migration to `0010_…`, sets its `down_revision` to the other migration, and re-runs `test_db.py`. Check this at merge, like decision numbers.
- **[#65 changes the image keys in the prompts]** → With U2 as recommended, this change does not depend on the prompt keys, and `prompts.py` and `summarize.py` are untouched. With structured outputs, the schema must follow #65.
- **[Claude Code cannot call the real API]** → Tests use a fake transport. The live check uses a local stub that speaks the Messages API's stream format. A real-API check is optional and done by the user, who enters their own key in Settings.
- **[SDK behavior on bodies with no stream events may change between versions]** → Task 1.1 probes the locked version. The test fixes the behavior (retried, then `InvalidAnswer`), not the exception class.
- **[A proxy base URL may reject the fallback beta header]** → That only affects the five fallback models. The README says that a custom address must pass Anthropic's beta headers.
- **[`ANTHROPIC_CUSTOM_HEADERS` in the host environment is still read by the SDK]** → It is the instance owner's own environment. It is noted in the README's Anthropic section.
- **[Cost and latency]** → `claude-opus-5-5` always thinks, at effort `medium`. The README states the default and the fallback billing. #4 adds a setting.
- **[Downgrading the database turns Anthropic configurations into OpenAI-compatible ones]** → The user then tests again with the right key. This is written in the migration's docstring.

## Migration Plan

1. The upgrade adds `model_config.provider`, with the default `openai_compatible`. Nothing else changes for existing instances.
2. Rollback: downgrade to `0008_run_progress`, then reinstall the previous image. The saved key and base URL are kept.

## Testing

- **Offline only.** Anthropic calls go through `httpx2.MockTransport`, with streamed bodies built from Anthropic's documented events: `message_start`, `content_block_start`, `content_block_delta`, `content_block_stop`, `message_delta`, and `message_stop`, plus `ping` and `error`. Keys are invented test strings.
- **Named mutations per group.** A1–A10 (client), P1–P6 (provider setting and runs), F1–F4 (Settings page), and Doc (README).
- **Review (Claude Code).** Claude Code runs `/code-review`, the spec sub-agent, `scripts/docker-smoke.sh`, and a live check. The live check uses a scratch container on a port other than 8800, with a local Messages-API stub on the host. In Settings, choose Anthropic, set the stub's address and an invented key, test, generate a digest, and check the run's token totals.
