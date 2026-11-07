# Design

## Context

The motivation is in proposal.md ("Why"). Today:
- `testConnection()` in `frontend/src/pages/Settings.tsx` sends only `POST /api/settings/model/test`. It fills the Model menu, falls back to the first listed model when the current one is not listed, and sets the message "Connection succeeded. Choose a model, then click Save."
- `save()` sends `PUT /api/settings/model` (`base_url`, `model_id`, `api_key`), then `PUT /api/settings/preferences`. It clears the key field and sets "Settings saved."
- One `message` string drives both places: it is shown next to Test connection when it starts with "Connection", and in the save bar when it equals "Settings saved.". Its `<p role="status">` is created together with its text.
- Errors use `error` and `errorField`. `key` and `base` errors render under the Test row and are linked to their input. Errors without a field render at the very bottom of the page.
- `save_model` in `backend/src/catchup/api/settings.py` already does what an automatic save needs. It keeps the stored key when `api_key` is empty and the base URL is unchanged. It refuses a changed base URL without a key (`api_key_required`) and a missing instance secret (`secret_not_configured`). It clears the recorded context window when the base URL or model changes. Home treats the model as set up when `GET /api/settings/model` reports `key_set`.

## Goals / Non-Goals

**Goals:**
- One successful test is enough to set up the model.
- Never save a configuration that was not tested, whether through the automatic save after a test or through a model choice.

**Non-Goals:**
- Any backend or API change.
- Moving errors from the bottom **Save** (#71).
- Other status regions and focus handling on the page (#72).
- Saving Digest or YouTube settings automatically.

## Decisions

### D1. The page saves with the existing endpoint after the test

After `POST /model/test` succeeds, `testConnection()` sends `PUT /api/settings/model` with the values captured when Test was clicked: `base_url`, `api_key` (the key field's value, or `''` when it was empty, as `save()` sends today), and `model_id`, which is chosen by D2. It does not send `PUT /settings/preferences`.

- **Why.** `save_model` already has every rule this save needs. The test endpoint applies the same base-URL/key rule, so a save after a successful test only fails for reasons the test does not check, such as a missing instance secret.
- **Alternative: a `save` flag on `POST /model/test`.** This would test and save in one request. It would duplicate the save validation in the test endpoint, and it would change an API that the spec describes as read-only.
- **Alternative: keep explicit saving.** This would show "Not saved yet" next to the test result, or add a Save button in the model group. The change would be smaller, but the user preferred automatic saving (#85).

### D2. Which model is saved

The model to save is `chosen = result.models.includes(model) ? model : result.models[0]`, computed from the result. It is not read back from React state, because the `model` in the closure is the value from before the test. The page always sets the menu to `chosen` (today it does so only when the old value is not listed), so the menu shows what was saved even if the user changed the menu while the test was running.

- If `result.models` is empty, nothing is saved. The menu stays disabled, and the page reads "Connection succeeded, but the provider listed no models. Nothing was saved."
- The fallback is "replaced" when the previous selection was empty or not in the list. When the fallback replaced the selection and the list has more than one model, the success message ends with " Choose another model to change it."

### D3. Choosing a model saves it while the fields match the saved configuration

The page keeps `savedBaseUrl: string | null`, which starts as `null`. It is set from `GET /settings/model` when that reports `key_set`, and from every successful `PUT /settings/model` response (the automatic save, a model-choice save, and **Save**). It stays `null` while no configuration is saved.

The Model menu's change handler always updates the selection. It also saves when both of these hold:
- the key field is empty;
- `savedBaseUrl !== null && baseUrl.trim() === savedBaseUrl`.

This save is `PUT /api/settings/model` with `{ base_url: savedBaseUrl, model_id: <choice>, api_key: '' }`, so `save_model` keeps the stored key. When the fields do not match, nothing is sent. The next successful test or **Save** saves the choice.

- **Why this guard.** Suppose a test succeeded, the user then typed a new key or base URL, and the next test failed. The menu would still list the models of the last good provider, so a choice saved with the edited fields would store an untested key or address. Requiring that the fields match the saved configuration means that only the model changes.
- **Alternative: never save on a model choice; tell the user to click Save.** This brings back the trap from #85 for anyone who changes the fallback model.

### D4. Saves run one at a time

All automatic saves (the save after a test and model-choice saves) go through one queue, a promise chain kept in a `useRef`. Each save starts only after the previous one settles, whether it succeeded or failed, and a failure does not break the chain. The status and error show the result of the save that finished last, which is the last one queued.

- **Why.** On some platforms, arrow keys on a focused, closed `<select>` fire one change event per key press. Without the queue, overlapping PUTs could finish out of order and leave an earlier choice saved.

### D5. Where results appear, and the exact text

The Model provider group gets two new pieces of state, `modelStatus` and `modelError`. They replace the use of `message` and of the bottom error for Test connection.

The status region sits in the Test connection row: `<p className="inline-msg msg-ok" role="status">`. It is always rendered and is empty when there is nothing to say, so screen readers announce changes (#72 pattern). It shows the check icon only when it has text.

When the test request fails:
- `auth_failed`, `insufficient_balance`, `api_key_required`, and `missing_api_key` errors keep using the existing key-field display.
- `connection_failed` keeps using the existing base-URL display.
- Every other error is shown in the Model provider group. It uses `<p className="field-error" role="alert" id="model-error">`, placed where the field errors render today. It is no longer shown at the bottom of the page. Unlike the status region, `#model-error` is rendered only while `modelError` is not empty. Existing tests query `findByRole('alert')` without a name, so an always-present alert would break them.

A failed automatic save (after a test, or after a model choice) is never mapped to a field. It always uses the group alert, with the prefixes below. Starting a model-choice save clears `modelStatus` and `modelError`, but not a field error.

`save()` (the bottom **Save**) clears `modelStatus` and `modelError` when it starts. Otherwise it keeps its message, its error display, and its behavior. Starting a test clears both too.

Exact text (the `${…}` parts are filled in):

| Case | Where | Text |
|---|---|---|
| Test and save succeeded, a key was entered | status | `Connection succeeded. Saved key ending in ${last4} with model ${model}.` |
| Test and save succeeded, no key entered | status | `Connection succeeded. Saved model ${model}.` |
| …and the fallback replaced the selection, more than one model listed | status, appended | ` Choose another model to change it.` |
| Test succeeded, no models listed | status | `Connection succeeded, but the provider listed no models. Nothing was saved.` |
| Test succeeded, save failed | alert | `Connection succeeded, but nothing was saved. ${errorMessage(err)}` |
| Model choice saved | status | `Saved model ${model}.` |
| Model choice save failed | alert | `The model was not saved. ${errorMessage(err)}` |
| Key hint when a key is saved | `#key-hint` | `Leave empty to keep the saved key. Testing a new key saves it.` |

`${model}` is the `model_id` that was sent. `last4` comes from the PUT response (`api_key_last4`). After a successful automatic save, the page sets `last4` and `savedBaseUrl` from the response. It clears the key field only if the field still holds the key that was tested (`setKey(current => current === testedKey ? '' : current)`). After a failed save, the key stays in the field.

The first-run hint ("Stored encrypted on this computer. It is never shown again.") is unchanged.

## Risks / Trade-offs

- [A test of a new key replaces the saved key at once; the user can no longer try a key without keeping it.] → The hint and the success message both say so (D5). This was accepted in #85.
- [The save after a test is a second request, so the test can pass while the save fails.] → D5 reports it in place, keeps the key in the field, and nothing is half-saved, because `save_model` is one transaction.
- [Merely re-testing a saved configuration rewrites it.] → The values are the same, so this is harmless. `save_model` resets the context window only when the base URL or model changes.
- [A model choice while the fields do not match is silently unsaved.] → The menu shows the choice; the next test or **Save** saves it. This only happens after the user edited the base URL or key, when a test is the expected next step anyway.

## Migration Plan

Frontend only. No data migration. Roll back by reverting the commit.

After Droid's run, Claude Code runs the live check on a test instance (not 8800), with a stub OpenAI-compatible provider and a fake key:
1. Test only, then check that Home offers Generate with one source.
2. Choose another model, then reload Settings and check that it was kept.
3. Run a test with a rejected key, then check that nothing changed.

The Docker smoke script (`scripts/docker-smoke.sh`) also runs at review.
