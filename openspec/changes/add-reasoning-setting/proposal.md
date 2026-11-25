# Proposal

## Why

Both tested providers reason before they answer by default: DeepSeek thinks at effort "high" unless told otherwise, and `claude-opus-5-5` always thinks, at effort `medium`. CatchUp only raised its output limits so that reasoning fits (design D3 of `add-core-digest-flow`, D-037), and users cannot lower it. Reasoning adds cost and waiting time to short summaries and topic grouping (#4).

## What Changes

This describes the recommended option of each decision point U1–U3 in `design.md`.

- A **Reasoning** setting for the saved model configuration, with the choices:
  - **Provider default** (the default, and every existing configuration): CatchUp sends nothing, as today;
  - **Low**: the model reasons less;
  - **Off**: no reasoning, offered for the OpenAI-compatible provider only, because several Anthropic models cannot turn thinking off.
- Every summary, merge, and grouping call of a run sends the saved choice in the provider's own parameter: `reasoning_effort` (`"low"` or `"none"`) for OpenAI-compatible providers, and `output_config.effort` (`"low"`) for Anthropic. Provider default sends neither.
- When a provider refuses a request while Reasoning is not Provider default, the run fails at once with a message that says to choose Provider default, and the main screen offers **Check settings**, instead of marking every summary unavailable.
- Settings shows a **Reasoning** select in the Model provider group, after Model. It is saved like the model: right away while the provider, base URL, and key match the saved ones, otherwise by the next successful test or by **Save**. Changing the provider resets it to Provider default.
- The model settings API reads and saves `reasoning`. A new column `model_config.reasoning` (migration `0010_model_reasoning`) stores it.
- The README's "Supported model providers" section describes the setting.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `model-settings`: two new requirements, "Choose how much the model reasons" (the stored choice, its values per provider, what each model call sends, and what happens when a provider refuses it) and "Choose reasoning in Settings" (the Reasoning select and when it is saved). No existing requirement text changes.

## Impact

- **Backend.**
  - `backend/src/catchup/models.py` (`ModelConfig.reasoning`);
  - a new migration `backend/src/catchup/migrations/versions/0010_model_reasoning.py`;
  - `backend/src/catchup/api/settings.py` (`ModelInput`, `_public_model`, `save_model`);
  - `backend/src/catchup/llm/client.py` (`ModelClient`, a new `ReasoningRejected` error);
  - `backend/src/catchup/llm/anthropic_client.py`;
  - `backend/src/catchup/llm/providers.py` (`make_model_client`);
  - `backend/src/catchup/digest/runner.py` and `backend/src/catchup/digest/summarize.py` (pass the setting on; treat `ReasoningRejected` like a rejected key).
- **Frontend.** `frontend/src/pages/Settings.tsx` and `frontend/src/pages/Home.tsx`, with their tests.
- **Docs.** `README.md`.
- **API.** `GET /api/settings/model` adds `reasoning`. `PUT /api/settings/model` accepts an optional `reasoning`; clients that do not send it keep working.
- **No new dependencies.** Both SDKs already accept the parameters: `openai` 3.24.0 sends `reasoning_effort` as given, and `anthropic` 1.13.0 sends `output_config` on both `messages.stream` and `beta.messages.stream`.
- **Not changed.** Prompts, output limits, the grouping and summary logic, the extension, and the Anthropic fallback models.
