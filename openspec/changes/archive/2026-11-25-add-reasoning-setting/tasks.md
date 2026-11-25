# Tasks

Implementer notes:
- **Read first.** Read `proposal.md`, all of `design.md` (Context with the provider facts and probes, D1–D7, the user's decisions U1–U3 as recorded at plan approval, Risks, Testing), and the spec delta `specs/model-settings/spec.md`. If something looks wrong or contradictory, stop and report instead of redesigning.
- **Work test-first with the `tdd` skill** (D-016). In each group, first write the group's tests, run them, and watch each fail for the reason the task gives. Then change the code. The seams are named in each task, and they count as agreed. They are:
  - `ModelClient(base_url, api_key, model, *, reasoning=…, http_client=…, sleep=…)` with the `mock_provider` fixture and the `completion` helper of `backend/tests/test_llm_client.py:18-43`;
  - `AnthropicModelClient(base_url, api_key, model, *, reasoning=…, http_client=…, sleep=…)` with the `provider` fixture, `stream_body`, and `error_response` of `backend/tests/test_anthropic_client.py:17-97`;
  - `make_model_client(base_url, api_key, model, provider, reasoning, **options)` and `REASONING_CHOICES` in `backend/src/catchup/llm/providers.py`;
  - the `api` fixture of `backend/tests/test_settings_api.py`;
  - the Alembic `Config` and `command` pattern of `backend/tests/test_db.py:18-58`;
  - from `backend/tests/test_digest_runner.py`: `environment`, `seed`, `stub_collection`, `execute`, `all_rows`, and `FakeModel`; from `backend/tests/test_model_errors.py`: `saved_digest`; from `backend/tests/test_anthropic_runs.py`: `configure` and `install_factory`;
  - `app.state.model_client_factory`;
  - in `frontend/src/pages/Settings.test.tsx`: `fetchMock`, `respond`, `mockModelProvider`, `modelPuts`, `modelSection`, `expectNoBottomAlert`, `testAndSave` (inside `describe('saving model choices')`), and `expectAccessible`; in `frontend/src/pages/Home.test.tsx`: `mockPage` and `run`.
- **Test rules:**
  - **No real network, and no real keys.** Every model request goes to a `MockTransport` handler or the `respx` router, which raises on a request it does not expect. Keys are invented strings such as `test-only-key`.
  - **Request bodies.** Read them with `json.loads(request.content)`. "Absent" means the key is not in the body at all.
  - **Change no existing test,** except where a task says so.
  - **Imports.** Adding names to a test module's imports is always allowed, also where a task says "the only allowed edit". Importing `ReasoningRejected` or `REASONING_CHOICES` before they exist makes the whole module fail to collect, and with it every module that imports from it (`test_model_errors.py`, `test_anthropic_runs.py`, `test_model_providers.py`); that is the expected failure of task 1.1.
- **Mutations.** For each named mutation, apply it alone, run the named tests, record the result, and restore the code exactly. Compare with `git diff` after restoring.
- **Environment:**
  - **Backend.** Run `uv run --offline pytest …` in `backend/`. Do not add, remove, or upgrade packages.
  - **Frontend and extension.** Use Node 22.17.1 with `export PATH="$HOME/.nvm/versions/node/v22.17.1/bin:$PATH"`. Then run `npm ci --offline --no-audit --no-fund` in `frontend/` (and in `extension/` for task 5.1). It installs the locked packages from the local npm cache. If it fails, stop and report. Do not change any `package.json` or `package-lock.json`.
- **Do not run** `docker build`, `scripts/docker-smoke.sh`, or any `docker` command, and do not touch port 8800. Claude Code runs Docker at review.
- **Out of scope.** Do not change:
  - `backend/src/catchup/llm/prompts.py`, `backend/src/catchup/digest/group.py`, the output limits, or the fallback model list;
  - `AppSettings`, the preferences endpoints, or the Digest and YouTube groups of Settings;
  - the extension.
- **Do not edit:**
  - `proposal.md`, `design.md`, or the spec delta;
  - `docs/process/decision-log.md` or `docs/process/requirements-changes.md`. Claude Code wrote D-041 and the requirements row with the plan.
- **OpenSpec.** Prefix every OpenSpec CLI call with `DO_NOT_TRACK=1`.
- **Commits.** Commit after each task group. Do not push, tag, or open a PR.

## 1. Clients and factory (D2–D4)

- [x] 1.1 Write these tests and watch them fail. They fail because the clients take no `reasoning`, and because `ReasoningRejected` and `REASONING_CHOICES` do not exist.

  **In `backend/tests/test_llm_client.py`** (model `test-model`, `sleep=sleeps.append`):
  - **`test_reasoning_choice_sets_reasoning_effort`**, parametrized `("default", None)`, `("low", "low")`, `("off", "none")`. `chat_json([{"role": "user", "content": "x"}], 100)` returns the answer. The chat completion body's `reasoning_effort` equals the expected value, and is absent for `default`. `thinking` is absent.
  - **`test_refused_reasoning_raises_reasoning_rejected_without_retry`**, parametrized over statuses 400 and 422, with `reasoning="low"`. The route answers that status with `{"error": {"message": "unsupported"}}`. `chat_json` raises `ReasoningRejected`; its `code` is `"reasoning_rejected"`, and `str(exc)` is exactly "The model provider rejected a request with the Reasoning setting. Choose Provider default in Settings, then generate again." The route was called once, and `sleeps == []`.
  - **`test_refusal_with_provider_default_stays_a_provider_error`.** The same 400 with `reasoning="default"` raises an exception whose type is exactly `ProviderError`, after one call.
  - **`test_other_errors_keep_their_meaning_with_reasoning_set`**, with `reasoning="off"`: a 401 raises `AuthFailed`, and a 402 raises `InsufficientBalance`.
  - **`test_model_list_refusal_stays_a_provider_error_with_reasoning_set`.** With `reasoning="low"`, `GET /models` answers 400; `list_models()` raises an exception whose type is exactly `ProviderError`.
  - **`test_unknown_reasoning_choice_is_refused`.** `ModelClient(BASE, "test-only-key", "test-model", reasoning="max")` raises `ValueError`.

  **In `backend/tests/test_anthropic_client.py`.** The only allowed edit to existing code there: give the `provider` fixture's `make` a keyword argument `reasoning="default"`, passed to `AnthropicModelClient`. Then add:
  - **`test_low_reasoning_sends_output_config_effort`**, parametrized over `claude-haiku-5-5` and `claude-opus-5-5`, with `reasoning="low"`. The Messages body has `output_config == {"effort": "low"}`, and no `thinking`. For `claude-opus-5-5`, the body also has `fallbacks == "default"`, and the `anthropic-beta` header contains `server-side-fallback-2026-07-01`.
  - **`test_provider_default_sends_no_output_config`.** With `default`, `output_config` and `thinking` are absent.
  - **`test_anthropic_refused_reasoning_raises_reasoning_rejected`.** With `reasoning="low"`, `error_response(400, "invalid_request_error")` raises `ReasoningRejected` with the message above, after one request, with no sleeps. With `reasoning="default"`, the same answer raises exactly `ProviderError`.
  - **`test_anthropic_refuses_off`.** `AnthropicModelClient(BASE, "test-only-key", "claude-opus-5-5", reasoning="off")` raises `ValueError`.

  **In `backend/tests/test_model_providers.py`:**
  - **`test_factory_passes_the_reasoning_choice`**, parametrized over both providers. `make_model_client(BASE, "test-only-key", model, provider, "low", http_client=…, sleep=…)` with an `httpx2.MockTransport` handler that answers `completion("{}")` from `test_model_errors` (`openai_compatible`) or `stream_body("{}")` (`anthropic`). Do not use the `completion` of `test_llm_client`: it returns an `httpx.Response` for the respx bridge, and an `httpx2.MockTransport` handler that returns it fails with `TypeError`. After `chat_json([…], 100)`, the body has `"reasoning_effort": "low"` or `"output_config": {"effort": "low"}`.
  - **`test_reasoning_choices_per_provider`.** `REASONING_CHOICES == {"openai_compatible": ("default", "low", "off"), "anthropic": ("default", "low")}`.
- [x] 1.2 Implement design D2–D4 in the clients:
  - `backend/src/catchup/llm/client.py`: `ReasoningRejected(ModelError)` with `code = "reasoning_rejected"` and the message above; `REASONING_EFFORTS = {"low": "low", "off": "none"}`; the keyword `reasoning="default"` on `ModelClient`, which raises `ValueError` for anything other than `default` or a key of `REASONING_EFFORTS`; `_call(operation, *, reasoning_sent=False)`, which raises `ReasoningRejected` for an `openai.APIStatusError` with status 400 or 422 when `reasoning_sent` is true, before the existing status rules; `chat_json` adds `reasoning_effort=REASONING_EFFORTS[self.reasoning]` when the choice is not `default`, and passes `reasoning_sent`.
  - `backend/src/catchup/llm/anthropic_client.py`: `REASONING_EFFORTS = {"low": "low"}`; the same keyword and `ValueError`; `options["output_config"] = {"effort": …}` in `chat_json` when the choice is not `default`, for both endpoints; the same `_call` rule for `anthropic.APIStatusError`.
  - `backend/src/catchup/llm/providers.py`: `REASONING_CHOICES` built as `("default", *REASONING_EFFORTS)` for each client, and `make_model_client(base_url, api_key, model="", provider="openai_compatible", reasoning="default", **options)`, which passes `reasoning=reasoning`.

  Then run `uv run --offline pytest tests/test_llm_client.py tests/test_anthropic_client.py tests/test_model_providers.py`, and watch them pass.
- [x] 1.3 Run these mutations one at a time, and record which tests fail:

  | Mutation | Change | Expected failing tests |
  | --- | --- | --- |
  | R1 | `REASONING_EFFORTS["off"]` in `client.py` is `"low"` | `test_reasoning_choice_sets_reasoning_effort[off]` |
  | R2 | `ModelClient.chat_json` sends `reasoning_effort=None` for `default` | `test_reasoning_choice_sets_reasoning_effort[default]` |
  | R3 | `ModelClient.chat_json` passes `reasoning_sent=False` | `test_refused_reasoning_raises_reasoning_rejected_without_retry` |
  | R4 | both `_call` methods ignore `reasoning_sent` and raise `ReasoningRejected` for every 400 | `test_refusal_with_provider_default_stays_a_provider_error`, `test_anthropic_refused_reasoning_raises_reasoning_rejected`, `test_model_list_refusal_stays_a_provider_error_with_reasoning_set`, `test_refused_reasoning_raises_reasoning_rejected_without_retry[422]`, and the existing `test_other_status_fails_at_once[400]` and `test_failures_that_do_not_retry[400]` |
  | R5 | the Anthropic client adds `output_config` only on the non-beta endpoint | `test_low_reasoning_sends_output_config_effort[claude-opus-5-5]` |
  | R6 | `make_model_client` drops `reasoning` | `test_factory_passes_the_reasoning_choice` |

## 2. Store and save the choice (D1, D5)

- [x] 2.1 Write these tests and watch them fail. Fixtures that need the database or the API fail on the missing column or field.

  **In `backend/tests/test_db.py`.** First make the only allowed edits to existing tests there:
  - change `"0009_model_provider"` to `"0010_model_reasoning"` in the four head-revision assertions (lines 145, 314, 354, and 495);
  - add `assert (migrations / "versions" / "0010_model_reasoning.py").is_file()` to `test_migrations_live_inside_package`, after its `0009` line (line 127);
  - in `test_model_provider_migration_defaults_existing_config_and_downgrades`, change `command.upgrade(config, "head")` (line 77) to `command.upgrade(config, "0009_model_provider")`. Upgrading to head would add the `reasoning` column, and the test's `after == before` comparison would fail.

  Then add, after `test_model_provider_migration_defaults_existing_config_and_downgrades`:
  - **`test_model_reasoning_migration_defaults_existing_config_and_downgrades`.**
    - Upgrade to `0009_model_provider`, and insert one `model_config` row with SQL, with the provider `anthropic`.
    - Upgrade to head. `reasoning` is `default`, and the other columns are unchanged.
    - Downgrade to `0009_model_provider`. There is no `reasoning` column, and the row is kept with its provider.
    - With `test_run_sends_reasoning_effort_on_every_chat_call[default]` and `test_provider_default_sends_no_output_config`, this covers the scenario "Configuration saved before the setting existed".

  **In `backend/tests/test_settings_api.py`.** The only allowed edit to existing tests: add `"reasoning": "default"` to the two exact model answers (lines 53-57 and 125-128). Then add:
  - **`test_read_without_configuration_reports_default_reasoning`.** `GET /api/settings/model` reports `reasoning` `default`.
  - **`test_save_and_read_reasoning`**, parametrized `("openai_compatible", "low")`, `("openai_compatible", "off")`, `("anthropic", "low")`, `("anthropic", "default")`. A PUT with the provider, its address, a model, a key, and the `reasoning` answers 200 with that `reasoning`, and a later GET reports it.
  - **`test_unsupported_reasoning_is_refused`**, parametrized `("anthropic", "off")`, `("openai_compatible", "max")`, `("openai_compatible", "")`. After saving an OpenAI-compatible configuration with `low`, a PUT with that provider, its address, a model, a new key, and that `reasoning` answers 422 with the code `invalid_reasoning` and the message "Choose a Reasoning setting that this provider supports.", and GET reports the same answer as before the PUT. This is the spec scenario "Off refused for Anthropic".
  - **`test_save_without_reasoning_keeps_it`**, parametrized over omitting the field and sending `null`. This is the scenario "Save without a Reasoning choice".
  - **`test_provider_change_without_reasoning_resets_it`.** This is the scenario "Provider changed without a Reasoning choice".
- [x] 2.2 Implement design D1 and D5:
  - `ModelConfig.reasoning` in `backend/src/catchup/models.py`: `String(16)`, default `"default"`, server default `"default"`;
  - `backend/src/catchup/migrations/versions/0010_model_reasoning.py`, following `0009_model_provider.py`, with a docstring saying that a downgrade loses the choice;
  - in `backend/src/catchup/api/settings.py`: `ModelInput.reasoning`, the save rules of D5 before anything is written, and `reasoning` in `_public_model`.

  Then run `uv run --offline pytest tests/test_db.py tests/test_settings_api.py`, and watch them pass.
- [x] 2.3 Run these mutations one at a time, and record which tests fail:

  | Mutation | Change | Expected failing tests |
  | --- | --- | --- |
  | S1 | the migration's column has no server default | the migration test |
  | S2 | the save accepts any value of `REASONING_CHOICES["openai_compatible"]` for every provider | `test_unsupported_reasoning_is_refused[anthropic-off]` |
  | S3 | a save without `reasoning` always sets `default` | `test_save_without_reasoning_keeps_it` |
  | S4 | a save without `reasoning` always keeps the saved value | `test_provider_change_without_reasoning_resets_it` |
  | S5 | `_public_model` leaves out `reasoning` | the read and save tests |

## 3. Runs send the choice, and a refused setting fails the run (D3, D4, D7)

- [x] 3.1 Write these tests and watch them fail. They fail because the runner passes four arguments, and because summary calls do not re-raise `ReasoningRejected`.

  **In `backend/tests/test_digest_runner.py`.** The only allowed edit to an existing test: in `test_run_passes_the_saved_provider_to_every_client`, replace `assert all(len(args) == 4 and args[-1] == "anthropic" for args in calls)` with `assert all(args[3:] == ("anthropic", "default") for args in calls)`. Then add:
  - **`test_run_passes_the_saved_reasoning_to_every_client`.** With `reasoning` set to `low` on the saved row, both factory calls receive `"low"` as their fifth argument.

  **In `backend/tests/test_model_errors.py`.** The only allowed edit to existing tests: the two factories at lines 91 and 159 take a fifth parameter `reasoning` and pass `reasoning=reasoning` to `ModelClient`. Then add, following `test_live_failure_recovers_end_to_end` (real `ModelClient`, `MockTransport`, `GET …/models` answered with an empty list):
  - **`test_run_sends_reasoning_effort_on_every_chat_call`**, parametrized `("low", "low")`, `("off", "none")`, `("default", None)`. Two seeded items, valid summary and grouping answers. The run succeeds, and every chat completion body (both summaries and the grouping call) has that `reasoning_effort`, or none for `default`, and no `thinking`. This covers the scenarios "Reasoning off for an OpenAI-compatible provider" and "Provider default sends nothing".
  - **`test_refused_reasoning_fails_the_run_and_keeps_items_pending`.** Reasoning `low`; every chat call answers 400. The run fails with `error_kind` `reasoning_rejected` and exactly the message of D4. No call is repeated: each item's summary call is made at most once, and no grouping call (a body containing `item_refs`) is made. There are no `Digest` or `DigestItem` rows, and both items are `pending`. This is the scenario "Provider refuses the setting".
  - **`test_refusal_with_provider_default_keeps_the_digest`.** Reasoning `default`; Item 0's summary call answers 400, and the other calls answer validly. The run succeeds, and `saved_digest` shows Item 0 with its summary unavailable. This is the scenario "Refusal with Provider default".

  **In `backend/tests/test_anthropic_runs.py`.** The only allowed edit: `install_factory`'s lambda takes a fifth parameter `reasoning` and passes it to `make_model_client`. Then add:
  - **`test_anthropic_run_sends_low_effort_with_fallback`.** After `configure`, set `reasoning` to `low`. Every Messages body of the run has `output_config == {"effort": "low"}` and `fallbacks == "default"`, and none has `thinking`. The run succeeds. This is the scenario "Low reasoning for Anthropic".

  **In `frontend/src/pages/Home.test.tsx`.** The only allowed edit: add `['reasoning_rejected', 'Check settings']` to the table of `offers the right primary action for %s with reused summary copy` (lines 1057-1059).

  **In `backend/tests/test_readme_providers.py`.** Add the phrases "Reasoning", "Provider default", "reasoning_effort", "output_config.effort", and "choose Provider default" to the list.
- [x] 3.2 Implement:
  - `backend/src/catchup/digest/runner.py`: read `config.reasoning` with the other settings, and pass it as the fifth positional argument at both factory calls;
  - `backend/src/catchup/digest/summarize.py`: re-raise `ReasoningRejected` with `AuthFailed` and `InsufficientBalance` in `_summarize`, and add it to the fast shutdown in `summarize_items`;
  - `frontend/src/pages/Home.tsx`: add `'reasoning_rejected'` to `configErrors`;
  - `README.md`: the Reasoning paragraph of design D7, in "Supported model providers", after the Anthropic item.

  Then run `uv run --offline pytest` in `backend/` and `npm test -- --run` in `frontend/`, and watch them pass.
- [x] 3.3 Run these mutations one at a time, and record which tests fail:

  | Mutation | Change | Expected failing tests |
  | --- | --- | --- |
  | N1 | the runner passes `"default"` instead of the saved choice at the summary call | `test_run_sends_reasoning_effort_on_every_chat_call[low]` and `[off]`, `test_anthropic_run_sends_low_effort_with_fallback`, `test_run_passes_the_saved_reasoning_to_every_client`, `test_refused_reasoning_fails_the_run_and_keeps_items_pending` |
  | N2 | `_summarize` treats `ReasoningRejected` like other model errors | `test_refused_reasoning_fails_the_run_and_keeps_items_pending` (a grouping call is made) |
  | N3 | `configErrors` leaves out `reasoning_rejected` | the `reasoning_rejected` row in `Home.test.tsx` |
  | N4 | the context-window lookup passes four arguments | `test_run_passes_the_saved_reasoning_to_every_client`, `test_run_passes_the_saved_provider_to_every_client`, `test_anthropic_run_saves_summaries_groups_and_usage` |
  | Doc | the README's Reasoning paragraph removed | the README test |

## 4. Settings page (D6)

- [x] 4.1 In `frontend/src/pages/Settings.test.tsx`, write these tests and watch them fail. They fail because there is no Reasoning select, and because the bodies have no `reasoning`.
  - **Test types.** Add `reasoning` to `ModelBody`, and an optional `reasoning` to `mockModelProvider`'s `saved` type. Its default PUT answer also echoes `reasoning: body.reasoning`.
  - **Existing tests.** The only allowed edit to them is adding `reasoning: 'default'` to every expected PUT body (`modelPuts()` comparisons). Mocked GET answers may stay without `reasoning`: the page treats a missing value as Provider default.
  - **`shows the saved Reasoning after the Model select with its hint`.** A saved `reasoning: 'off'` gives a Reasoning select reading "Off", with the options "Provider default", "Low", and "Off" in that order. The Model select comes before it in document order, inside `modelSection()`. Its accessible description is exactly "Less reasoning makes digests faster and cheaper. Summaries and topics may be less careful.". This is the scenario "Saved choice is shown".
  - **`offers no Off for Anthropic and restores the saved choice`.** With the same saved value, choosing "Anthropic" shows "Provider default" with only "Provider default" and "Low"; choosing "OpenAI-compatible" again shows "Off". Then choose "Anthropic" again, paste the key `new-key-7777`, and click Test connection: the test's save is the only PUT, `{ base_url: 'https://api.anthropic.com', model_id: 'live-a', api_key: 'new-key-7777', provider: 'anthropic', reasoning: 'default' }`. The displayed value alone cannot show the reset: a select whose value has no option shows its first option. These are the scenarios "Anthropic offers no Off" and "Back to the saved provider restores Reasoning".
  - **`saves a Reasoning choice right away`.** Choosing "Low" sends exactly one PUT, `{ base_url: 'https://api.deepseek.com', model_id: 'saved-model', api_key: '', provider: 'openai_compatible', reasoning: 'low' }`, and the Model provider group's status reads exactly "Saved reasoning: Low.". Then choosing "Anthropic" and "OpenAI-compatible" again shows "Low". This is the scenario "Choosing Low saves it".
  - **`waits to save a Reasoning choice when the key was edited`.** After pasting a key and choosing "Low", no PUT is sent. A successful test then sends one PUT with `reasoning: 'low'` and the new key. This is the scenario "Edited key waits for a test".
  - **`sends the shown Reasoning with Save`.** After pasting a key and choosing "Off", no PUT is sent before Save, and Save's PUT has `reasoning: 'off'` and the new key. After "Settings saved.", choosing "Anthropic" and "OpenAI-compatible" again shows "Off". This is the scenario "Save sends the choice".
  - **`reports a failed Reasoning save in the model group`.** The PUT answers `respond({ error: { code: 'invalid_reasoning', message: 'Choose a Reasoning setting that this provider supports.' } }, 422)`. The alert in `modelSection()` reads exactly "The reasoning setting was not saved. Choose a Reasoning setting that this provider supports.", and `expectNoBottomAlert()` holds.
  - **`saves a Reasoning choice and a model choice in order`.** Inside `describe('saving model choices')`, after `testAndSave()`, hold the PUT for the Reasoning choice "Low" (as `saves quick successive model choices in order` does), then choose the model "live-b". The second PUT starts only after the first finishes, and the PUT bodies are, in order, the test's save, `{ …, model_id: 'live-a', reasoning: 'low' }`, and `{ …, model_id: 'live-b', reasoning: 'low' }`.
  - **`has no accessibility violations with the Reasoning select`.** Run `expectAccessible` on the rendered page.
- [x] 4.2 Implement design D6 in `frontend/src/pages/Settings.tsx`. In `frontend/`, run `npm test -- --run` and `npm run build`, and watch them pass.
- [x] 4.3 Run these mutations one at a time, each against `Settings.test.tsx`, and record which tests fail:

  | Mutation | Change | Expected failing test |
  | --- | --- | --- |
  | F1 | `chooseProvider` keeps the shown Reasoning | `offers no Off for Anthropic and restores the saved choice` |
  | F2 | "Off" is offered for Anthropic too | `offers no Off for Anthropic and restores the saved choice` |
  | F3 | a Reasoning choice saves without checking that the fields match the saved ones | `waits to save a Reasoning choice when the key was edited` |
  | F4 | **Save** leaves out `reasoning` | `sends the shown Reasoning with Save` |
  | F5 | a Reasoning choice sends its own request instead of using `queueModelSave` | `saves a Reasoning choice and a model choice in order` |
  | F6 | the select has no `aria-describedby` | `shows the saved Reasoning after the Model select with its hint` |
  | F7 | `queueModelSave` does not update `savedReasoning` | `saves a Reasoning choice right away` |
  | F8 | **Save** does not update `savedReasoning` | `sends the shown Reasoning with Save` |

## 5. Checks and report

- [x] 5.1 Run these checks and keep their output for the final report:
  - in `backend/`: `uv run --offline pytest`;
  - in `frontend/`: `npm test -- --run` and `npm run build`;
  - in `extension/`: `npm ci --offline --no-audit --no-fund`, then `npm test -- --run` and `npm run build`. The extension is unchanged; this matches CI;
  - `DO_NOT_TRACK=1 openspec validate add-reasoning-setting --strict`;
  - `git diff --check`.

  All pass.
- [x] 5.2 Write `docs/process/test-report-add-reasoning-setting.md`. It holds:
  - the commands of 5.1, with their counts;
  - every mutation (R1–R6, S1–S5, N1–N4, Doc, F1–F8), with the tests that failed;
  - any deviation from this plan.
- [x] 5.3 Add one Droid entry for this run to `docs/process/ai-usage-log.md`, after the latest entry, in the format of the Droid entry for `add-anthropic-provider`. It holds:
  - the prompt (a verbatim excerpt in quotation marks);
  - the tool and model;
  - the outcome;
  - what failed and how it was handled.

  Leave the session line (session id, turns, minutes) to Claude Code.

## 6. Fix round 1: a Reasoning choice made during a connection test (model-settings "Choose reasoning in Settings"; design D6)

Found at review. Choosing a Reasoning option while a connection test runs saved it at once, and then the test's automatic save sent the value shown when the test started. The select read "Low" while the saved choice was Provider default. The spec requires every save to send the choice shown when that save starts.

- [x] 6.1 Write these tests in `frontend/src/pages/Settings.test.tsx`, inside `describe('reasoning settings')`, and watch the first one fail. Hold the connection test's answer with a pending promise, as `saves the tested values without clearing a key typed while testing` does: pass `test: () => pending` to `mockModelProvider`, and resolve it with `respond({ ok: true, models: ['live-a', 'live-b'] })` inside `act`.
  - **`sends a Reasoning choice made during a connection test with the test's save`.** `mockModelProvider` with the default saved configuration (Provider default) and the held test. Render `<Settings/>`, wait for the `API key` field, click "Test connection", then choose "Low". Resolve the test. Then:
    - `modelPuts().map(body => [body.model_id, body.reasoning])` equals `[['saved-model', 'low'], ['live-a', 'low']]` (the Reasoning choice's save, then the test's save);
    - the Reasoning select has the value `low`;
    - after choosing "Anthropic" and then "OpenAI-compatible" in the Provider select, the Reasoning select has the value `low` again.

    This is the scenario "Choice made during a connection test". It fails on the current code: the second body has `'default'`.
  - **`keeps the tested provider's Reasoning when the provider changes during a test`.** `mockModelProvider` with `saved: { …the default saved configuration, reasoning: 'off' }` and the held test. Render, click "Test connection", choose "Anthropic" in the Provider select, then resolve the test. The only `PUT` has `provider: 'openai_compatible'` and `reasoning: 'off'`. It passes on the current code, and mutation T2 in 6.2 shows that it can fail.
  - **`sends the saved Reasoning with the test's save`.** `mockModelProvider` with `saved: { …the default saved configuration, reasoning: 'off' }` and the default (immediate) test answer. Render, wait for the `API key` field, and click "Test connection". `modelPuts()` equals `[{ base_url: 'https://api.deepseek.com', model_id: 'live-a', api_key: '', provider: 'openai_compatible', reasoning: 'off' }]`. It passes on the current code, and mutation T4 in 6.2 shows that it can fail.
- [x] 6.2 In `frontend/src/pages/Settings.tsx`, implement design D6's rule for the test's save: add `const selectedReasoning = useRef<Reasoning>('default')`, set `selectedReasoning.current` wherever `setReasoning` is called (the page load, `chooseReasoning`, and `chooseProvider`), and in `testConnection` send `reasoning: selectedProvider.current === testedProvider ? selectedReasoning.current : testedReasoning` in the test's `queueModelSave`. Change nothing else.

  Verify:
  - the tests from 6.1 pass, and `npm test -- --run` and `npm run build` pass in `frontend/`;
  - each mutation below, applied alone, fails the named test:

  | Id | Mutation | Expected failing test |
  | --- | --- | --- |
  | T1 | the test's save sends `testedReasoning` in every case | `sends a Reasoning choice made during a connection test with the test's save` |
  | T2 | the test's save sends `selectedReasoning.current` in every case | `keeps the tested provider's Reasoning when the provider changes during a test` |
  | T3 | `chooseReasoning` does not set `selectedReasoning.current` | `sends a Reasoning choice made during a connection test with the test's save` (also `waits to save a Reasoning choice when the key was edited`) |
  | T4 | the page load does not set `selectedReasoning.current` | `sends the saved Reasoning with the test's save` |

- [x] 6.3 Run the checks of task 5.1 again. Add a section "Fix round 1" to `docs/process/test-report-add-reasoning-setting.md`, after Droid's earlier sections, with the commands and their counts, whether 6.1's first test failed before 6.2 and the second passed, and mutations T1–T4 with the tests that failed. Add one Droid entry for this round to `docs/process/ai-usage-log.md`, after the latest entry, in the format of the Droid entry "`add-reasoning-setting` (#4): implementation"; leave the session line to Claude Code. Commit.
