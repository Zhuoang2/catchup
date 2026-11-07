# Tasks

Implementer notes:
- **Read first.** Read `proposal.md`, `design.md` (D1–D5, including the text table in D5), and `specs/model-settings/spec.md`. If something looks wrong or contradictory, stop and report instead of redesigning.
- **Work test-first with the `tdd` skill** (D-016). For each task, first write its verification items as failing tests and watch them fail, then implement until they pass. The seam is the mocked global `fetch` in `frontend/src/pages/Settings.test.tsx` (`fetchMock` and `respond`). Assert request URLs, methods, and JSON bodies (`JSON.parse(options.body)`), and the visible text. These seams count as agreed.
- **Test rules.**
  - No real network, no real sleeps. To hold a request open, return a promise that the test resolves later.
  - Keep `expectAccessible(container)` in the tests that already have it, and add it to the first-setup test.
  - **PUT mock.** The default mock answers `/api/settings/model` without checking the method, so a PUT that falls through to it gets the GET data. In each new test, answer `PUT /api/settings/model` by echoing the request: `model_id: body.model_id`, `base_url: body.base_url`, `key_set: true`, and `api_key_last4: body.api_key ? body.api_key.slice(-4) : <the saved last4>`.
  - **Saved-key line.** The status text also contains "Saved key ending in …", and `<code>` splits the saved-key line. Assert it with `expect(document.getElementById('key-saved')).toHaveTextContent('Saved key ending in 3f9a')`, not with `getByText`.
  - **Model provider section.** Find it with `screen.getByRole('heading', { name: 'Step 1: Model provider' }).closest('section')!` and query inside it with `within(...)`. The `<section>` has no accessible name, so `getByRole('region')` does not find it. "After the X accounts section" means an element that follows `getByRole('heading', { name: 'Step 5: X accounts' }).closest('section')` in document order.
  - **Guard tests.** Some tests below (marked *guard*) already pass on today's code, because today nothing is saved. Write them first anyway. After the implementation, check each one by mutation: remove the guard or the error routing it protects, watch the test fail, and restore the code. Record the mutation and its result in the test report.
- **Out of scope:**
  - the backend (`backend/`), including `api/settings.py`
  - errors from the bottom **Save** (#71)
  - other status messages and focus on the page (#72)
  - the Browser extension and X accounts groups
  - the Digest and YouTube fields
- **Commits.** Commit after each task group. Do not push, tag, or open a PR.

## 1. Save after a successful test

- [ ] 1.1 In `frontend/src/pages/Settings.test.tsx`, add failing tests. Each test mocks `/api/settings/model` GET and PUT separately (check `options?.method`).
  1. **First setup.** GET reports no saved key and `model_id: ''`. The user pastes `secret-3f9a`. The test lists `['live-a', 'live-b']`, and PUT answers `api_key_last4: '3f9a'`, `model_id: 'live-a'`. Assert all of these:
     - exactly one PUT `/api/settings/model`, with body `{ base_url: 'https://api.deepseek.com', model_id: 'live-a', api_key: 'secret-3f9a' }`;
     - no PUT `/api/settings/preferences`;
     - the status text `Connection succeeded. Saved key ending in 3f9a with model live-a. Choose another model to change it.`;
     - the key field is empty, and `#key-saved` reads "Saved key ending in 3f9a";
     - `expectAccessible` passes.
  2. **New key replaces the saved key.** GET reports `1234` and `saved-model`. The user pastes `new-key-9999`. The test lists `['saved-model', 'other']`. Assert:
     - the PUT body has `api_key: 'new-key-9999'` and `model_id: 'saved-model'`;
     - the status reads `Connection succeeded. Saved key ending in 9999 with model saved-model.`, with no "Choose another model" sentence;
     - `#key-saved` reads "Saved key ending in 9999".
  3. **Saved key.** The key field is empty, and the test lists `['saved-model']`. Assert:
     - the PUT body is `{ base_url: 'https://api.deepseek.com', model_id: 'saved-model', api_key: '' }`;
     - the status reads `Connection succeeded. Saved model saved-model.`
  4. **Failed test** (*guard*). The test answers 401 `auth_failed`. Assert:
     - no PUT is sent;
     - the alert is the key-field error, as in the existing "explains authentication errors" test.
  5. **No models.** The test answers `models: []`. Assert:
     - no PUT is sent;
     - the status reads `Connection succeeded, but the provider listed no models. Nothing was saved.`
  6. **Save fails after the test.** The user pastes a key. The test succeeds, and PUT answers 400 `secret_not_configured`. Assert:
     - an alert inside the "Step 1: Model provider" section reads `Connection succeeded, but nothing was saved. Set CATCHUP_SECRET_KEY on the server before saving an API key.`;
     - no alert is rendered after the X accounts section;
     - the key field still holds the pasted key;
     - the key input is not marked invalid.
  7. **Tested values are saved.** The user pastes `tested-key-1111`, and the test response is held open. Meanwhile the field changes to `typed-later`. When the test resolves:
     - the PUT carries `tested-key-1111`;
     - the key field still holds `typed-later`.
  8. **Errors without a field.** The test answers 429 `rate_limited`. Assert:
     - the alert is inside the Model provider section, and none is after the X accounts section.
  9. **Key hint.** With a saved key, `#key-hint` reads `Leave empty to keep the saved key. Testing a new key saves it.`
  10. **Status region stays mounted.** Before any test, the Model provider section contains an empty element with `role="status"`. After a successful test, the same element holds the message.

  Then update the existing tests that this change makes wrong. Leave all other existing tests as they are.
  - "fills model options from a successful provider test": mock the PUT, and replace the old "Choose a model, then click Save" assertion and its comment. The new message is `Connection succeeded. Saved model live-a. Choose another model to change it.` (no key was entered, the selection was empty, and two models are listed).
  - "shows the first-run key hint and saves preferences without exposing the key": the recorded PUT calls become `['/api/settings/model', '/api/settings/model', '/api/settings/preferences']` (automatic save, then **Save**).

  Verify: the new tests, except the guard test, fail before 1.2 for the expected reason (missing request or text), not because of a mock error.
- [ ] 1.2 Implement design D1, D2, the save-after-test part of D4, and D5 in `frontend/src/pages/Settings.tsx`. This means:
  - `modelStatus`, `modelError`, and `savedBaseUrl`;
  - the persistent status region in the Test connection row;
  - the group alert;
  - the new key hint;
  - the queue in a `useRef`, used by the save after the test;
  - the menu always set to `chosen` (D2).

  `save()` keeps its behavior, except that it clears `modelStatus` and `modelError` when it starts, and sets `savedBaseUrl` from its PUT response.

  Verify:
  - the 1.1 tests pass, all of `Settings.test.tsx` passes, and `npm test -- --run` and `npm run build` pass in `frontend/`;
  - mutation for the guard test 1.1.4: making the automatic save run even after a failed test makes 1.1.4 fail.

## 2. Choosing a model saves it

- [ ] 2.1 In `frontend/src/pages/Settings.test.tsx`, add failing tests:
  1. **Choice after a test.** A test saves `live-a`, with the list `['live-a', 'live-b']`. The user then selects `live-b` (`fireEvent.change` on the Model select). Assert:
     - a second PUT is sent with body `{ base_url: 'https://api.deepseek.com', model_id: 'live-b', api_key: '' }`;
     - the status reads `Saved model live-b.`
  2. **Edited key waits** (*guard*; covers the key-field condition of D3). After the test has saved, the user types a new key, then selects `live-b`. Assert:
     - no second PUT is sent;
     - the select shows `live-b`.
  3. **Edited base URL waits** (*guard*; covers the base-URL comparison of D3). Same as 2, but the base URL is changed instead of the key.
  4. **Nothing saved yet** (*guard*; covers that `savedBaseUrl` stays `null` until a save succeeds, D3). GET reports no saved key. The user pastes a key. A test lists `['live-a', 'live-b']`, but its PUT answers 400 `secret_not_configured`, so the key stays in the field. The user then clears the key field and selects `live-b`. Assert:
     - no PUT is sent after the failed one.
  5. **In order.** A test lists `['live-a', 'live-b', 'live-c']` and saves `live-a`. The user selects `live-b`, and its PUT is held open; then the user selects `live-c`. Assert, in this order:
     - first `await waitFor` until the PUT for `live-b` appears in `fetchMock.mock.calls`;
     - then, while it is still open, no PUT for `live-c` has been sent;
     - after the `live-b` PUT resolves, the PUT for `live-c` is sent;
     - the status reads `Saved model live-c.`
  6. **Choice save fails.** The model-choice PUT rejects (the `fetch` promise rejects, as when CatchUp cannot be reached). The mock decides by `body.model_id`, so only the PUT for the chosen model fails. Assert:
     - the group alert reads `The model was not saved. Could not connect to CatchUp.`;
     - the select keeps the choice;
     - a later choice still saves (the queue is not broken).

  Verify: 1, 5, and 6 fail before 2.2; the guard tests 2–4 pass already.
- [ ] 2.2 Implement design D3 and the model-choice part of D4 in `frontend/src/pages/Settings.tsx`.

  Verify:
  - the 2.1 tests pass, all of `Settings.test.tsx` passes, and `npm test -- --run` and `npm run build` pass;
  - mutations for the guard tests: removing the key-field condition makes 2.1.2 fail; removing the base-URL comparison makes 2.1.3 fail; setting `savedBaseUrl` from the GET response even when it does not report `key_set` makes 2.1.4 fail, and so does setting it when a save fails; starting each save without waiting for the previous one makes 2.1.5 fail.

## 3. Integration checks and report

- [ ] 3.1 Run the full checks:
  - `npm test -- --run` and `npm run build` in `frontend/` (record the counts);
  - `uv run pytest` in `backend/` (unchanged code; record the count);
  - `DO_NOT_TRACK=1 openspec validate save-model-after-test --strict`;
  - if Docker is available: `docker build -t catchup:save-model-after-test-local .` from the repository root, then `scripts/docker-smoke.sh catchup:save-model-after-test-local`.

  Write the commands and their real results to `docs/process/test-report-save-model-after-test.md`.
  - Map each spec scenario to its test. "Main screen after only a test" maps to the existing Home test `offers %s / %s guidance while keeping a saved digest` (it covers `key_set`), plus the live check.
  - List the manual live check that Claude Code runs at review (design "Migration Plan") as not performed.

  Add your entry to `docs/process/ai-usage-log.md` after the latest entry, with a faithful prompt excerpt. Leave out the session id; Claude Code adds it at review.

  Verify: every command passes, and the report has the actual numbers.
