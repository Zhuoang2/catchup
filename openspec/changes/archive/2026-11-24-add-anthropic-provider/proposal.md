# Proposal

## Why

CatchUp can talk only to OpenAI-compatible APIs (D-004, issue #12). Checked on main `795c5e7`:

- **One adapter, one wire format.** `backend/src/catchup/llm/client.py:54-163` wraps the `openai` SDK. It sends Chat Completions with `response_format={"type": "json_object"}` (`:137-143`), reads `choices[0].message.content`, and reads the context window from `context_window` or `context_length` in the model list (`:102-125`). Anthropic's API uses a different request and answer shape (the Messages API), so it cannot be configured today.
- **No provider in the saved configuration.** `model_config` holds a base URL, model ID, encrypted key, last four characters, and context window (`backend/src/catchup/models.py:37-46`). Every client is built as `factory(base_url, key, model_id)` (`digest/runner.py:284,436`, `api/settings.py:263`, `main.py:113`).
- **The Settings page assumes DeepSeek.** The base URL defaults to `https://api.deepseek.com` (`frontend/src/pages/Settings.tsx:44`, `api/settings.py:24`), and the invalid-URL message names it (`Settings.tsx:228`).
- D-004 planned "Other adapters (e.g. Anthropic native) … behind the same interface".

## What Changes

- **Provider choice.** The model configuration gains a provider: **OpenAI-compatible** (as today, the default) or **Anthropic**. Existing configurations become OpenAI-compatible, with nothing else changed. Only one configuration is active at a time.
- **Anthropic adapter.** A second model client calls Anthropic's Messages API through the official `anthropic` Python SDK. It has the same surface as the current client (list models, JSON answer, token usage, close), so the summary and grouping code does not change. It:
  - lists models from Anthropic's model list, with the context window it reports, and lists `claude-opus-5-5` first when Anthropic lists it;
  - sends the prompts' system text as Anthropic's `system` field;
  - asks for at least 16,000 output tokens, because thinking cannot be turned off on some current models and counts toward that limit;
  - streams each answer and reads the final message;
  - accepts a JSON object, or a JSON object inside one fenced code block;
  - maps Anthropic's errors onto CatchUp's existing error kinds, and treats 529 (overloaded) as a temporary error;
  - does not retry a refusal; for the models that support it, asks Anthropic to retry a refused request on a fallback model of Anthropic's choice.
- **Never reuse a key across providers.** Changing the provider, like changing the base URL, requires entering the API key again. Changing the provider clears the recorded context window.
- **Settings.** The Model provider group gains a **Provider** select. Choosing a provider fills in its default address (`https://api.deepseek.com` or `https://api.anthropic.com`) and clears the model list until the next test.
- **Docs.** The README lists the supported providers and what CatchUp sends to each.
- **New dependency** `anthropic` (with one new transitive package, `docstring-parser`), added to `backend/pyproject.toml` and `backend/uv.lock` by Claude Code before implementation starts, after the user approves the download.
- Not in this change: a per-provider thinking or effort setting (#4); prompt caching; Amazon Bedrock, Google Vertex AI, or Microsoft Foundry clients.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `model-settings`:
  - "Configure an OpenAI-compatible provider" is replaced by "Configure the model provider", which adds the provider choice;
  - "Test the connection and list models" says which Anthropic model is listed first;
  - "Never send the stored key to a different provider address" also covers a provider change;
  - "Report provider errors meaningfully" adds Anthropic's spend limit and overload errors;
  - "Learn the model's context window" is cleared by a provider change;
  - "Save the model settings after a successful test" compares the provider too;
  - a new requirement, "Choose the provider in Settings", covers the Provider select.
- `digest-generation`:
  - "Work with reasoning models by default" covers models whose thinking cannot be turned off;
  - "Retry transient model errors" adds Anthropic's overload errors and answers that are not a message stream;
  - a new requirement, "Handle model refusals", covers refusals and Anthropic's fallback models.

## Impact

- **Code:**
  - new `backend/src/catchup/llm/anthropic_client.py` and `backend/src/catchup/llm/providers.py`;
  - `backend/src/catchup/api/settings.py`, `backend/src/catchup/main.py`, `backend/src/catchup/digest/runner.py`, `backend/src/catchup/models.py`;
  - a new migration `0009_model_provider`, which adds one column to `model_config`;
  - `frontend/src/pages/Settings.tsx`.
- **Unchanged:** `llm/client.py`, `llm/prompts.py`, `digest/summarize.py`, `digest/group.py`, and the extension.
- **API:** `GET /api/settings/model` returns `provider`; `PUT /api/settings/model` and `POST /api/settings/model/test` accept it. Clients that do not send it keep the saved provider.
- **Tests:** a new backend test file for the Anthropic client, new settings, runner, migration, and README tests, and Settings page tests. Three existing test fakes that take exactly three factory arguments, and the existing Settings tests that compare exact request bodies, are updated for the new provider argument.
- **Dependencies:** `anthropic` from PyPI, and `docstring-parser`. Docker builds use `uv sync --locked` (`Dockerfile:15,17`), so the lockfile must include them.
- **Docs:** `README.md`, `docs/process/decision-log.md` (D-037), `docs/process/requirements-changes.md`.
