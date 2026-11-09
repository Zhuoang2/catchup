# Proposal

## Why

On 2026-11-04 the user set up a fresh instance: they pasted a key, clicked **Test connection**, saw "Connection succeeded", and left Settings. Nothing was saved, so Home still said "Set up your model" (#85). A successful test reads like the setup is done, and the only **Save** button sits at the bottom of the page, below the Digest and YouTube groups. Saving the model settings as soon as a test succeeds removes that trap.

## What Changes

- In Settings, a successful **Test connection** saves the tested model settings right away: the base URL, the API key when one was entered, and the selected model. If the selected model is not listed, the first listed model is selected and saved. The page says what was saved, naming the key only by its last four characters.
- A failed test saves nothing. If the provider lists no models, nothing is saved, and the page says so. If saving fails after a successful test, the page says that the connection worked but nothing was saved, and why.
- After that, choosing another model saves it right away, as long as the base URL and key fields still match the saved settings. Quick successive choices are saved in order, so the last choice is kept.
- Testing a new key now replaces the saved key. The key field's hint says so when a key is saved.
- The outcome of a test, an automatic save, or a model choice is shown and announced in the Model provider group, next to **Test connection**. Test errors that are not tied to a field no longer appear at the bottom of the page.
- **Save** at the bottom is unchanged: it still saves all fields, including the model settings, and Digest and YouTube settings still need it.
- No backend or API change: the page sends the existing `PUT /api/settings/model` after `POST /api/settings/model/test` succeeds. The test request itself still saves nothing.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `model-settings`: "Test the connection and list models" now says that the test request itself saves nothing and that Settings saves after a successful test; new requirement "Save the model settings after a successful test" covers the automatic save, the model choice afterwards, the messages, and the key hint.

## Impact

- Code: `frontend/src/pages/Settings.tsx` and `frontend/src/pages/Settings.test.tsx` only.
- Backend, API, database: unchanged.
- Related issues, not fixed here: #71 (errors from the bottom **Save** still render at the bottom of the page) and #72 (other status messages that are created together with their text). This change fixes both problems only for the Model provider group's test and model-choice results.
- Docs: test report and process logs. The README does not describe the Test/Save steps, so it needs no change.
