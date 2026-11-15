# Tasks

Implementer notes:
- **Read first.** Read `proposal.md`, `design.md` (Context, D1–D5), and both spec deltas (`specs/user-interface/spec.md`, `specs/browser-extension/spec.md`). If something looks wrong or contradictory, stop and report instead of redesigning.
- **Work test-first with the `tdd` skill** (D-016). In each group, write the group's tests first and watch them fail on an assertion, then change the code. These seams count as agreed:
  - `frontend/src/pages/Settings.test.tsx`, `Home.test.tsx`, `Sources.test.tsx`, and `frontend/src/styles/tokens.test.ts`;
  - `extension/src/test/popup.test.ts`, in jsdom.

  Follow the existing test style: `fireEvent`, `screen`, `waitFor`, the existing fetch mocks, and `expectAccessible` (frontend) or `axe` (extension). Do not add `@testing-library/user-event` or any other dependency.
- **How to test focus and status regions.**
  - Check focus with `document.activeElement`, or `toHaveFocus()`.
  - A test for a status region that "is on the page before the message" takes the element before the action, then checks that the same element holds the message afterwards (`toBe(sameElement)`).
  - A test for a busy button checks all of these:
    - it has `aria-disabled="true"`;
    - it is `not.toBeDisabled()`. jsdom keeps focus on a disabled button, so focus alone cannot show the difference;
    - it is still focused. `fireEvent.click` does not focus a button, so focus it with `.focus()` before the click;
    - activating it again sends no second request.
  - The popup's status line is checked by identity and with a `MutationObserver` on `#popup` (`childList`, `subtree`). At the end, `takeRecords()` shows that no record has the status line in `removedNodes`. Re-appending the same node keeps its identity, so identity alone passes with the old code.
  - Tests marked *guard* below already pass with the old code. Mark them as guards in a comment and in the test report; they need not fail first.
- **Existing assertions that the design replaces** (design "Context", Tests). Change them, do not keep both:
  - `toBeDisabled()` on the busy "Generating…" button in `Home.test.tsx` (`:948`, `:967`, `:1120`);
  - `Settings.test.tsx` "shows invalid-language saves as form-wide errors, not key errors";
  - the load-failure check in `Settings.test.tsx` "shows load failures even after the loading state ends";
  - `popup.test.ts` "disables Add while saving and shows a run_active conflict".

  Keep the `toBeDisabled()` checks on the always-disabled first-run and no-sources buttons (`Home.test.tsx:246`, `:909`, `:934`, `:1212`, `:1230`, `:1250`) as they are.
- **Node.js.** This machine's default `node` is v20.19.0. Run every `npm` command under Node 22, for example `source ~/.nvm/nvm.sh && nvm use 22`. If `node_modules` is missing in the worktree, run `npm ci --prefer-offline` in `frontend/` and `extension/`. That may use the npm registry for packages missing from the cache.
- **Network.** Only `npm ci` and the Docker build in 5.2 may use the network (Docker Hub, GHCR, PyPI, and the npm registry). Tests use none.
- **Never touch these:**
  - the containers `catchup-e2e` (port 8800) and `catchup-e2e-d034789`;
  - the volumes `catchup-e2e` and `catchup-e2e-bak-d034789`;
  - the images `catchup:main-064d3a9` and `catchup:main-d034789`.

  Never send anything to port 8800. Never run `docker system prune`, `docker volume prune`, `docker image prune`, or `docker builder prune`.
- **Deleting.** Do not delete files, directories, or Docker images yourself. In your final message, list what you created that should be removed, with full paths and image tags. Claude Code removes them at review.
- **Out of scope:**
  - the backend;
  - the extension's options page;
  - the README;
  - the always-disabled first-run and no-sources Generate buttons.
- **Commits.** Commit after each task group. Do not push, tag, or create a release.

## 1. Settings: Save results at Save, focus, and status regions

- [ ] 1.1 In `frontend/src/pages/Settings.test.tsx`, add or change these failing tests (design D1, D3, D4):
  1. **Save before choosing a model.** Save with no model listed, and `PUT /api/settings/model` answering `invalid_model_config`. Check:
     - the Model select has `aria-invalid="true"`, and its `aria-describedby` names an alert that reads "Test the connection, then choose a model.";
     - the message appears once on the page, and the API key field is not marked invalid;
     - the save bar's status region reads "Settings were not saved. Check the Model field.".
  2. **Invalid provider URL.** With a model chosen, `invalid_model_config` marks the Base URL field invalid, with "Enter a valid provider URL, such as https://api.deepseek.com.". The message appears once, the API key field is not marked invalid, and the save bar names the Base URL field.
  3. **No instance secret.** `secret_not_configured` on Save. Check:
     - an alert inside the save bar (the element with class `save-bar`) reads "Set CATCHUP_SECRET_KEY on the server before saving an API key.";
     - the text appears once on the page;
     - no field is marked invalid.
  4. **Settings saved.** Take the save bar's status region before Save. After a successful Save, the same element reads "Settings saved.".
  5. **Model saved, rest refused.** Save a new key ending in "3f9a" with the model request succeeding and the preferences request rejected (a fetch that throws). Check:
     - the save bar says "The model settings were saved, but the Digest and YouTube settings were not." followed by "Could not connect to CatchUp.";
     - the page reads "Saved key ending in 3f9a";
     - the key field is empty.
  6. **Invalid language** (replaces the existing form-wide test). Choose "Other" in Digest language and type spaces into Other language, so that the field's `required` check passes. The model request succeeds, and the preferences request answers `invalid_language`. Check:
     - the Other language field is marked invalid, with the server's message linked to it as an alert;
     - the message appears once, and the API key field is not marked invalid;
     - the save bar's status region reads "The model settings were saved, but the Digest and YouTube settings were not. Check the Other language field.".
  7. **Load failure** (replaces the existing check). When loading fails, an alert titled "Could not load settings" appears before the Model provider heading in document order (`compareDocumentPosition`).
  8. **Test connection clears the save bar.** After a failed Save, run Test connection. The save bar's status region is empty, and its alert is gone.
  9. **Delete all X data focus.** Check each step:
     - after "Delete all X data", Cancel has focus;
     - after Cancel, "Delete all X data" has focus;
     - after a successful "Delete X data", the X accounts heading has focus;
     - the status region that announces the counts is the same element that was on the page before the deletion;
     - *guard:* when the deletion fails, the confirmation stays and the alert shows.
  10. **Disconnect focus.** After a successful Disconnect, the "Connected browsers" heading has focus. The browser status region is the same element before and after.
  11. **X token messages.** The X status region is the same element before and after "Save X token".
  12. **Empty status regions.** Before any result, the save bar's, the browser, and the X status regions are on the page and have no child nodes. In `frontend/src/styles/tokens.test.ts`, `components.css` has the rule `.app [role="status"]:empty` with `position: absolute`.

  Run `npm test -- --run src/pages/Settings.test.tsx` in `frontend/` under Node 22.

  Verify: each new or changed test fails on an assertion before 1.2. Record the counts.
- [ ] 1.2 Change `frontend/src/pages/Settings.tsx` as D1, D3, and D4 describe:
  - the save bar's persistent status region and its alert;
  - the field mapping for `invalid_model_config` and `invalid_language`, with linked error paragraphs for the Model select and the Other language field;
  - updating `last4`, `savedBaseUrl`, and the key field right after the model request succeeds;
  - `loadError` as an `Alert` under the page head;
  - removing the bottom error element;
  - a heading `ref` option on `SettingsSection`, `tabIndex={-1}` on the X accounts and "Connected browsers" headings, and the focus moves;
  - the always-mounted `browserMessage` and `xMessage` status regions, and the `:empty` rule in `components.css`;
  - the paragraph at `:323` rendering only for `base` and `key`;
  - Test connection, a model choice, and Save clearing the save bar's results.

  Keep the rest of the Model provider group's Test connection behavior as it is.

  Verify:
  - the 1.1 tests and all other Settings tests pass;
  - `npm test -- --run` passes in `frontend/`.

## 2. Main screen: Generate stays focusable

- [ ] 2.1 Add failing tests (design D2):
  1. **`frontend/src/pages/Home.test.tsx`, Generate during a run.** Focus Generate digest with `.focus()` and click it. While the run is active, check:
     - the button reads "Generating…", has `aria-disabled="true"`, and is `not.toBeDisabled()`;
     - the button is still `document.activeElement`;
     - clicking it again sends no second `POST /api/digest-runs`.

     Cover both layouts: the Generate screen (no digest yet) and the run bar (a digest shown).
  2. **`Home.test.tsx`, first digest.** Start from no digest, with focus on the Generate screen's button. When the run succeeds and the first digest is shown, focus is on the run bar's Generate button.

     The existing test "swaps the %s article after a run, retaining status and focus" must keep passing unchanged. It checks that focus does not move when a later digest replaces the one shown.
  3. **`Home.test.tsx`, no model.** Focus Generate digest and click it, with `POST /api/digest-runs` answering `model_not_configured`. After the first-run actions render, "Set up your model" has focus.
  4. **`frontend/src/styles/tokens.test.ts`.** Check:
     - `components.css` has separate rules for `.btn[aria-disabled="true"]` and `.btn-primary[aria-disabled="true"]`, with the same `background` and `color` as `.btn:disabled`. The existing test finds `.btn:disabled` with a regex, so do not merge the selectors into one list;
     - no hover rule that excludes `:disabled` lacks the matching `:not([aria-disabled="true"])`.

  Change the existing `toBeDisabled()` assertions on the busy button to check `aria-disabled="true"`. Keep those on the first-run and no-sources buttons.

  Verify: each new or changed test fails on an assertion before 2.2. Record the counts.
- [ ] 2.2 Change `frontend/src/pages/Home.tsx` and `frontend/src/styles/components.css` as D2 describes:
  - `aria-disabled` on both run buttons, and a guard in the click handler;
  - the first-digest focus move, with the focus check in the `.then` before `setDigest` (design D2);
  - the focus move to "Set up your model" after `model_not_configured`;
  - the CSS rules.

  Verify:
  - the 2.1 tests and every other Home test pass;
  - `npm test -- --run` passes in `frontend/`.

## 3. Sources: focus after the preview and the X token form

- [ ] 3.1 In `frontend/src/pages/Sources.test.tsx`, add these failing tests (design D3, D4):
  1. **Save and preview, success.** Focus "Save and preview" and submit. While the repeated preview request is pending, the X token form and its button are still on the page, and the button has focus. After the preview is shown, check:
     - the X token form is gone;
     - the preview's heading has focus;
     - the status region that reads "X token saved." is the same element that was on the page before.
  2. **Save and preview, preview fails.** When the token is saved but the repeated preview fails, the address field has focus, and the error is shown.
  3. **Confirm source.** After Confirm source succeeds, the address field is empty and has focus, and the same status region reads "Source saved.".
  4. **Cancel.** After the preview's Cancel, the address field has focus.

  Verify: each new test fails on an assertion before 3.2. Record the counts.
- [ ] 3.2 Change `frontend/src/pages/Sources.tsx` as D3 and D4 describe:
  - `ref`s and focus moves, using the page's existing delete pattern;
  - keeping the X token form mounted until the repeated preview answers;
  - `tabIndex={-1}` on the preview's heading;
  - the always-mounted `message` status region.

  Verify:
  - the 3.1 tests and every other Sources test pass;
  - `npm test -- --run` and `npm run build` pass in `frontend/`.

## 4. Extension popup: one status line, focus, and busy buttons

- [ ] 4.1 In `extension/src/test/popup.test.ts`, add or change these failing tests (design D2, D5):
  1. **One status line.** Take the `role="status"` element after connecting, and start a `MutationObserver` on `#popup` (`childList`, `subtree`). Then save a page, remove it, and follow the site (preview, then Confirm). Check:
     - after each step, the status element is the same node, and it holds that step's message;
     - at the end, `takeRecords()` has no record with the status element in `removedNodes`.
  2. **Focus after each view change:**
     - Follow, then the preview's heading;
     - Cancel, then "Follow this site";
     - Confirm, then "Follow this site";
     - Add succeeds, then "Add this page to my next digest";
     - Remove succeeds, then "Add this page to my next digest";
     - the X token prompt, then the token field;
     - the token is saved and the preview is shown, then the preview's heading;
     - a 401 during an action, then "Open options".

     *Guard:* when the popup opens connected, it does not move focus, so `document.activeElement` is still `document.body`.
  3. **Busy buttons** (replaces "disables Add while saving and shows a run_active conflict"). Focus Add with `.focus()` and click it. While the save is pending, check:
     - Add has `aria-disabled="true"`, is not `disabled`, and keeps focus;
     - a second click sends no second `POST /captures`;
     - the run_active conflict message still shows.

     Do the same for Remove and for the X token's Save.
  4. **Style.** Check:
     - `popup.css` gives `button[aria-disabled="true"]` the same `background` and `color` as `button:disabled`, in a rule that comes after `button.primary`, so a busy Add does not keep the primary look;
     - the hover rules exclude it;
     - the grid rule and the host-line rule apply to the new content container (design D5).

  Run `npm test -- --run` in `extension/` under Node 22.

  Verify: each new or changed test fails on an assertion before 4.2. Record the counts.
- [ ] 4.2 Change `extension/src/popup.ts` and `extension/src/popup.css` as D2 and D5 describe:
  - a content `div` with class `popup-content`, next to a persistent status line;
  - the `popup.css` selectors moved to that container (design D5);
  - the focus targets, wrapping handlers such as `button('Cancel', connected)` that would pass the click event on;
  - `aria-disabled` with guards on Add, Remove, and Save;
  - the CSS rules.

  Verify:
  - the 4.1 tests and every other extension test pass (`npm test -- --run` in `extension/`);
  - `npm run build` passes in `extension/`.

## 5. Full checks and report

- [ ] 5.1 Run the full checks, with `npm` under Node 22:
  - `uv run pytest` in `backend/`;
  - `npm test -- --run` and `npm run build` in `frontend/`;
  - `npm test -- --run` and `npm run build` in `extension/`;
  - `DO_NOT_TRACK=1 openspec validate fix-focus-and-result-messages --strict`.

  Verify: every command passes.
- [ ] 5.2 Run `docker build -t catchup:fix-focus-local .`, then `scripts/docker-smoke.sh catchup:fix-focus-local`.

  Verify: the build passes, and the smoke script passes every check.
- [ ] 5.3 Write `docs/process/test-report-fix-focus-and-result-messages.md`. It contains:
  - the Node.js and Python versions;
  - each group's failing counts before its change, and the passing counts after;
  - the commands of 5.1 and 5.2 with their real results;
  - a mapping from each scenario of the two spec deltas to its tests.

  Use placeholders such as `<worktree>` instead of absolute local paths. The report must not contain `/Users/` or `/private/`.

  Add your entry to `docs/process/ai-usage-log.md` after the latest entry, with a faithful prompt excerpt. Leave out the session id; Claude Code adds it at review. Commit after group 5.

  Verify: the report has the actual numbers, and `grep -nE '/Users/|/private/' docs/process/test-report-fix-focus-and-result-messages.md` prints nothing.
