# Design

Status: accepted (lean change, issue #4, decision D-041). On 2026-11-25 the user approved the plan with option A for U1–U3. The spec delta, the tasks, and this design describe those options.

## Context

See `proposal.md` for the motivation. What the code does today (main at 145811f):

- **One saved configuration.** `ModelConfig` (`backend/src/catchup/models.py:37-46`) holds `provider`, `base_url`, `model_id`, the encrypted key, and `context_window`. The migration head is `0009_model_provider`.
- **Settings API.** `PUT /api/settings/model` (`backend/src/catchup/api/settings.py:230-258`) takes `ModelInput` (`:28-32`): `base_url`, `model_id`, an optional `api_key`, and an optional `provider`. A save that names no provider keeps the saved one (`_model_provider`, `:185-189`). Reads come from `_public_model` (`:203-210`). The connection test (`:261-288`) only lists models.
- **OpenAI-compatible calls.** `ModelClient.chat_json` (`backend/src/catchup/llm/client.py:133-163`) sends `model`, `messages`, `max_tokens`, and `response_format: {"type": "json_object"}`, and nothing about reasoning. `_call` (`:78-100`) maps 401 to `AuthFailed`, 402 to `InsufficientBalance`, 429 to `RateLimited` after retries, 500/502/503/504 to retries, and any other status, 400 and 422 included, to `ProviderError` at once, without a retry.
- **Anthropic calls.** `AnthropicModelClient.chat_json` (`backend/src/catchup/llm/anthropic_client.py:116-164`) builds all request options in one place (`:121-132`): `model`, `messages`, `max_tokens = max(max_tokens, 16_000)`, `system`, and, for the five models in `FALLBACK_MODELS` (`:22-25`), the beta endpoint with `betas=["server-side-fallback-2026-07-01"]` and `fallbacks="default"`. It sends no `thinking` and no `output_config` (D-037, design D11 of `add-anthropic-provider`, which left `output_config.effort` for #4). `_call` (`:52-80`) treats 400 like any status that is not temporary: `ProviderError`, no retry.
- **Factory.** `make_model_client(base_url, api_key, model="", provider="openai_compatible", **options)` (`backend/src/catchup/llm/providers.py:14-21`) passes `options` to the client.
- **Runs.** `run_digest` reads the configuration once (`backend/src/catchup/digest/runner.py:255-266`), then calls `app.state.model_client_factory(base_url, key, model_id, model_provider)` twice: for the context-window lookup (`:288`) and for summaries and grouping (`:441`). Summary calls (`backend/src/catchup/digest/summarize.py:91-101`) re-raise only `AuthFailed` and `InsufficientBalance` (`:128`, `:156`); every other `ModelError` makes that item's summary unavailable (`:130`). Grouping (`backend/src/catchup/digest/group.py:66-77`) falls back to one topic only on `InvalidAnswer`; other errors fail the run. The runner fails the run with `exc.code` and `str(exc)` for any other `ModelError` (`runner.py:549-552`). Summaries saved before a failure are reused by the next run in the same language (`runner.py:419-426`).
- **Budgets.** Summaries ask for 4,096 tokens, grouping and merge for `min(32768, 8192 + 24 × count)` (`backend/src/catchup/llm/prompts.py:9-14`), sized for DeepSeek's default thinking (design D3 of `add-core-digest-flow`, task 8.1). Anthropic calls allow at least 16,000.
- **Settings page.** The Model provider group (`frontend/src/pages/Settings.tsx:377-421`) has Provider, Base URL, API key, Test connection, and Model. Every model save goes through `queueModelSave` (`:254-275`): the automatic save after a test (`:299-304`), and a model choice while the provider, base URL, and key match the saved ones (`:308-315`). **Save** (`:328-365`) PUTs the model settings, then the preferences. `chooseProvider` (`:317-326`) restores or clears the saved values.
- **Main screen.** `configErrors` (`frontend/src/pages/Home.tsx:33`) lists the run error kinds that make "Check settings" the primary action.

### Provider facts this design relies on

Read on 2026-11-24. The DeepSeek, Ollama, and Gemini pages show no update date.

- **DeepSeek, Chat Completions reference** (https://api-docs.deepseek.com/api/create-chat-completion): `reasoning_effort` takes `none`, `low`, `high`, or `max`. "none disables thinking mode; low / high / max enable thinking mode. The default effort is high." `minimal` is accepted as `low`, and `medium` and `xhigh` as `high`. `thinking` (`{"type": "enabled" | "disabled"}`) is optional; when it is omitted, "the mode follows reasoning_effort". `max_tokens` defaults to 8K without thinking and 64K with it. The thinking-mode guide (https://api-docs.deepseek.com/guides/thinking_mode) shows the same table and passes `thinking` through the OpenAI SDK's `extra_body`.
- **OpenAI, Create chat completion** (https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create.md): `reasoning_effort` takes `none`, `minimal`, `low`, `medium`, `high`, `xhigh`, and `max`, default `medium`. "Not all reasoning models support every value."
- **Ollama, OpenAI compatibility** (https://docs.ollama.com/api/openai-compatibility): `reasoning_effort` is supported. Unsupported names "resolve to the model default", and `"none"` requests no thinking on models that can turn it off. GPT-OSS maps `none` to `low` because it cannot turn thinking off.
- **Gemini, OpenAI compatibility** (https://ai.google.dev/gemini-api/docs/openai, which redirects to https://aistudio.google.com/docs/openai): `reasoning_effort` maps to Gemini's levels, `low` included. `none` turns thinking off only on 2.5 models: "Reasoning cannot be turned off for Gemini 2.5 Pro, Gemini 3, or Gemini 4 models."
- **Anthropic** (the `claude-api` skill, model table cached 2026-11-03):
  - effort is `output_config: {"effort": "low" | "medium" | "high" | "xhigh" | "max"}`, generally available, without a beta header. It is the default `medium` on `claude-opus-5-5` and `claude-haiku-5-5`, and `high` on the other current models;
  - `thinking: {"type": "disabled"}` returns HTTP 400 on `claude-opus-5-5` (at every effort) and on the Fable models; `claude-sonnet-5-5` needs `{"type": "between_tools"}` instead; `claude-opus-5` and `claude-haiku-5-5` accept it only at effort `high` or below;
  - `effort` "errors on Sonnet 4.5 / Haiku 4.5"; Opus 4.5 accepts only `low`, `medium`, and `high`;
  - thinking counts toward `max_tokens`.
- **Other OpenAI-compatible servers.** Not verified. A server that rejects unknown fields answers 400 or 422; the OpenAI SDK raises `BadRequestError` or `UnprocessableEntityError`, both `APIStatusError`.

### Probes (offline, `uv run --offline` in `backend/`, 2026-11-24)

- `openai` 3.24.0: `chat.completions.create(..., reasoning_effort=v)` puts `"reasoning_effort": v` in the body for `"none"`, `"low"`, and an invented value; without the argument the body has no such key.
- `anthropic` 1.13.0: `messages.stream(..., output_config={"effort": "low"})` and `beta.messages.stream(..., output_config=..., betas=["server-side-fallback-2026-07-01"], fallbacks="default")` both send `"output_config": {"effort": "low"}` and no `thinking`. An invented effort value is not checked by the SDK. `OutputConfigParam.effort` is typed `Literal["low", "medium", "high", "xhigh", "max"]`.

## Goals / Non-Goals

**Goals:**
- A user can lower reasoning, or turn it off where the provider allows it, from Settings.
- Nothing changes for anyone who leaves the setting at Provider default.
- A provider that refuses the setting produces one clear failure that names the fix.

**Non-Goals:**
- Raising reasoning (`medium`, `high`, `xhigh`, `max`). See U1.
- Different settings for summaries and grouping, or per-model capability lists.
- Lowering the output limits. They stay sized for the provider's default reasoning.
- Showing the model's reasoning, or `thinking.display`.
- OpenAI's `max_completion_tokens`: CatchUp sends `max_tokens`, which OpenAI's reference calls deprecated and "not compatible with o-series models". That is not part of #4.
- Re-summarizing items already summarized when the setting changes.

## Decisions

### D1. One provider-neutral choice on the model configuration

- **Column.** Migration `0010_model_reasoning` (`down_revision = "0009_model_provider"`) adds `model_config.reasoning`, `String(16)`, NOT NULL, server default `'default'`. Existing configurations read `default`, so their requests do not change. The downgrade drops the column (`batch_alter_table("model_config", recreate="never")`, as `0009` does).
- **Values.** `default`, `low`, `off`, in one table per provider in `backend/src/catchup/llm/providers.py`: `REASONING_CHOICES = {"openai_compatible": ("default", "low", "off"), "anthropic": ("default", "low")}`.
- **Alternatives considered:**
  - **A column in `app_settings`, saved with the Digest preferences.** Rejected: the choice depends on the provider, and #54 adds its own preference there.
  - **One setting per provider.** Rejected: only one configuration is saved at a time (D-037, U5).
  - **An environment variable.** Rejected: the issue asks for a setting, and Settings is where the model is chosen.
  - **The provider's own value (`none`, `low`, …) stored as given.** Rejected: the values differ per provider, and a provider-neutral value lets the page and the API share one list.

### D2. What each choice sends (decision U1)

| Choice | OpenAI-compatible | Anthropic |
| --- | --- | --- |
| `default` | nothing | nothing |
| `low` | `"reasoning_effort": "low"` | `"output_config": {"effort": "low"}` |
| `off` | `"reasoning_effort": "none"` | not offered, refused on save |

- **One standard field for OpenAI-compatible servers.** `reasoning_effort` is OpenAI's own parameter, and DeepSeek, Ollama, and Gemini read it. DeepSeek turns thinking off with `none` alone, so CatchUp never sends DeepSeek's `thinking` object, which other servers do not know.
- **No Off for Anthropic.** Turning thinking off is a 400 on `claude-opus-5-5` (the default model) and the Fable models, and needs a different value on `claude-sonnet-5-5`. `low` effort is the control that works on every current model.
- **Only chat calls.** `chat_json` adds the field. `list_models` sends nothing.
- **Fallback models.** On the beta endpoint, the same `output_config` goes with the request, and Anthropic's fallback model receives it.
- **Alternatives considered:**
  - **`minimal`.** Rejected: DeepSeek maps it to `low`, and Anthropic has no such level.
  - **Also Medium and High (U1, option B).** See U1.
  - **Model capabilities from Anthropic's model list** (`capabilities.effort`, D11 of `add-anthropic-provider`), to offer only the levels a model supports. Rejected: the page keeps only the saved model's id after a reload, OpenAI-compatible servers report no such data, and `low` is supported by every current Anthropic model.

### D3. Clients and factory

- **Constructor option.** `ModelClient(base_url, api_key, model="", *, reasoning="default", http_client=None, sleep=time.sleep)` and the same for `AnthropicModelClient`. Each client maps the choice as D2 says; a choice its provider does not accept raises `ValueError` in the constructor. The API never stores one (D5).
- **Factory.** `make_model_client(base_url, api_key, model="", provider="openai_compatible", reasoning="default", **options)` passes `reasoning=reasoning` to the client.
- **Runs.** `run_digest` reads `config.reasoning` with the other settings (`runner.py:255-266`), and passes it as a fifth positional argument at both factory calls (`:288`, `:441`): `factory(base_url, key, model_id, model_provider, reasoning)`. Positional, because the test fakes are `lambda *_: …` or `lambda *_args: …`, which accept extra positional arguments.
- **Connection test.** `test_model` keeps calling the factory with four arguments: listing models sends no reasoning.

### D4. A refused setting fails the run (decision U2)

- **New error.** `class ReasoningRejected(ModelError)` in `backend/src/catchup/llm/client.py`, `code = "reasoning_rejected"`, with the message "The model provider rejected a request with the Reasoning setting. Choose Provider default in Settings, then generate again."
- **Where it is raised.** `_call(operation, *, reasoning_sent=False)` in both clients. `chat_json` passes `reasoning_sent=True` when the client's choice is not `default`. An `APIStatusError` with status 400 or 422 then raises `ReasoningRejected` at once, before the other status rules. `list_models` never passes it, so a 400 there stays a `ProviderError`.
- **Propagation.**
  - `summarize.py` re-raises `ReasoningRejected` with `AuthFailed` and `InsufficientBalance` (`:128`), and cancels the other summary calls without waiting (`:156`).
  - Grouping does not catch it (`group.py:72` catches only `InvalidAnswer`).
  - The runner's existing `except ModelError` (`runner.py:551-552`) fails the run with `reasoning_rejected` and the message as written. Items stay pending, and summaries saved before the failure are reused.
- **Main screen.** `reasoning_rejected` joins `configErrors` (`Home.tsx:33`), so "Check settings" is the primary action ("One primary action per state": a configuration error).
- **With `default`.** Nothing changes: a 400 is a `ProviderError` as before.

### D5. Settings API

- **Input.** `ModelInput.reasoning: str | None = None`.
- **Save rules** (`save_model`), checked before anything is written:
  - A `reasoning` that is given and not null must be in `REASONING_CHOICES[provider]`. Otherwise the save is refused with `AppError("invalid_reasoning", "Choose a Reasoning setting that this provider supports.", 422)`.
  - Not given, or null: keep `row.reasoning` when the row exists and the provider is unchanged, otherwise use `default`.
- **Reads.** `_public_model` adds `"reasoning": row.reasoning if row else "default"`. `GET` and `PUT /api/settings/model` both return it.
- **Unchanged.** The key rules and the context-window reset (`settings.py:240-252`).

### D6. Settings page (`frontend/src/pages/Settings.tsx`)

- **Types.** `type Reasoning = 'default' | 'low' | 'off'`. `ModelSettings` gets an optional `reasoning`, and `ModelSave` gets `reasoning`. A read without `reasoning` counts as `'default'`.
- **State.** `reasoning` and `savedReasoning`, set from the read when the page loads.
- **Select.** A `field` after the Model field: label "Reasoning" (`htmlFor="reasoning"`), `select#reasoning`, and the hint `p#reasoning-hint` "Less reasoning makes digests faster and cheaper. Summaries and topics may be less careful." The select's `aria-describedby` is `reasoning-hint`. Options: "Provider default" (`default`), "Low" (`low`), and "Off" (`off`) only while the selected provider is OpenAI-compatible.
- **Provider change.** `chooseProvider` sets `reasoning` to `savedReasoning` when the saved provider is chosen again, otherwise to `'default'`.
- **Bodies.** Every model PUT sends `reasoning`:
  - the test's automatic save sends the value shown when that save starts, read from a ref `selectedReasoning` that every Reasoning change updates (the page load, `chooseReasoning`, and `chooseProvider`), so a choice made during the test is not overwritten. When another provider was chosen during the test (`selectedProvider.current !== testedProvider`), it sends the value captured with the tested base URL, key, and provider (`:281-283`), which belongs to the tested provider. Fix round 1: the first plan sent the value captured at the test's start in every case, which contradicted the spec;
  - a model choice and **Save** send the value shown.
- **Reasoning choice.** `chooseReasoning(choice)` sets `reasoning`. Under the same condition as a model choice (`!key && baseUrl.trim() === savedBaseUrl && provider === savedProvider`, `:311`), and only when a model is saved, it calls `queueModelSave({ base_url: savedBaseUrl, model_id: model, api_key: '', provider, reasoning: choice }, () => \`Saved reasoning: ${label}.\`, 'The reasoning setting was not saved. ')`. So reasoning and model choices share one queue and one status region.
- **Saved state.** `queueModelSave` and **Save** set `savedReasoning` from the answer's `reasoning`, or from the value sent when the answer has none.

### D7. README

The "Supported model providers" section gets a **Reasoning** paragraph: the three choices, the fields CatchUp sends (`reasoning_effort` with `low` or `none`, `output_config.effort` with `low`), that Off is offered for OpenAI-compatible providers only, and what to do when a run fails with the Reasoning message (choose Provider default).

## Decisions for the user (decided 2026-11-25: option A for U1–U3)

- **U1. Choices offered.**
  - Recommended (A): Provider default, Low, and Off (OpenAI-compatible only). It does what #4 asks, lowering or turning off reasoning, with the fewest choices that do something on both tested providers.
  - Alternative (B): also Medium and High. On DeepSeek, Medium is the same as High, its default; on `claude-opus-5-5`, Medium is the default. High raises cost and waiting time, and on Anthropic a summary's thinking could then use up the 16,000-token limit before any answer, which makes the summary unavailable. If chosen: D2's table and `REASONING_CHOICES` gain `medium` and `high` (`reasoning_effort` and `output_config.effort` with the same names), the spec's choice lists and scenarios gain them, and the tests in groups 1 and 3 add them to their tables.
- **U2. When the provider refuses a request while Reasoning is not Provider default.**
  - Recommended (A): fail the run at once with the Reasoning message (D4). No extra calls. A 400 for another reason, such as one item that is too long for the model, then also fails the run with that message, but only for users who changed the setting.
  - Alternative (B): repeat the refused call once without the setting. Only if that call succeeds does the run fail with the Reasoning message; otherwise the item is handled as today. It is exact, costs one extra call per refusal, and adds a retry path to both clients.
  - Alternative (C): no special handling. Every summary is then marked unavailable, and grouping fails with "The model provider returned an error."
- **U3. When a Reasoning choice is saved.**
  - Recommended (A): like a model choice: right away while the provider, base URL, and key match the saved ones, otherwise by the next successful test or by Save (D6).
  - Alternative (B): only by Save, like the Digest and YouTube settings. Then the test's save and model choices still send the saved value, not the one shown.

## Risks / Trade-offs

- **[#54 may also add migration 0010]** → Whichever change merges second renumbers its migration to `0011_…`, sets its `down_revision` to the other's, and updates the head-revision assertions in `backend/tests/test_db.py`. Check at merge, like decision numbers.
- **[Shared files with #54]** → `backend/src/catchup/models.py`, `backend/src/catchup/api/settings.py`, `frontend/src/pages/Settings.tsx`, `frontend/src/pages/Settings.test.tsx`, `backend/tests/test_db.py`, and `README.md`. This change edits only `ModelConfig`, `ModelInput`, the model endpoints, the Model provider group, and the "Supported model providers" section; #54 edits `AppSettings`, the preferences, and the Digest group. Expect textual conflicts only next to each other's lines.
- **[Spec overlap]** → This change only ADDS two requirements to `model-settings`, and MODIFIES no main-spec requirement. #54 and #32 do not change `model-settings`.
- **[Some models refuse a choice]** → For example Gemini 3 and 4 refuse turning reasoning off, OpenAI models without reasoning may refuse `reasoning_effort`, and Anthropic's Sonnet 4.5 and Haiku 4.5 refuse `effort`. D4 turns this into one clear failure; the README says to choose Provider default.
- **[Some servers ignore the field]** → Ollama resolves unsupported names to the model default, and GPT-OSS cannot turn thinking off. The setting then has no effect, and the run works.
- **[A 400 for another reason, with the setting on, fails the run]** → Accepted under U2 (A). The message names the setting, and Provider default restores today's handling.
- **[Quality]** → Less reasoning can make summaries and topics less careful. The hint says so. The choice stays the user's.
- **[Earlier summaries are reused]** → Changing the setting does not re-summarize items that already have a summary in the digest language.
- **[Claude Code cannot call real providers]** → Tests use fake transports. The live check uses a local stub that records request bodies. A real-provider check is optional, by the user, with their own key on their own instance.

## Migration Plan

1. The upgrade adds `model_config.reasoning` with the default `'default'`. Existing instances send the same requests as before.
2. Rollback: downgrade to `0009_model_provider`, then reinstall the previous image. The saved provider, address, model, and key are kept; the Reasoning choice is lost.

## Testing

- **Offline only.** Requests go to `httpx2.MockTransport` handlers (through the `mock_provider` fixture for `ModelClient`, and the `provider` fixture for `AnthropicModelClient`). Keys are invented test strings.
- **Named mutations per group:** R1–R6 (clients and factory), S1–S5 (API and migration), N1–N4 (runs), F1–F8 (Settings and main screen), and Doc (README).
- **Recorded survivors (D-023, not tested).** The fresh-eyes prototype found two mutations that no test catches, both without a visible effect: the Anthropic `list_models` passing `reasoning_sent=True` (the connection test sends no reasoning, and the context-window lookup swallows errors), and leaving `ReasoningRejected` out of the fast shutdown in `summarize_items` (timing only).
- **Review (Claude Code).** `/code-review`, the spec sub-agent, `scripts/docker-smoke.sh`, and a live check: a scratch container on a port other than 8800, pointed at a local OpenAI-compatible stub that records request bodies. Choose Low, generate, and check that every chat request carries `"reasoning_effort": "low"`; choose Off and check `"none"`; make the stub answer 400 and check the run's message and the "Check settings" action. Then the same with an Anthropic Messages stub and Low.
