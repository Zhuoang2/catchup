# Design

## Context

Claude Code checked the code at `main` `2f456cd` on 2026-11-15. The issues' line numbers are from 2026-11-01. The current ones are:

- **Settings** (`frontend/src/pages/Settings.tsx`):
  - `save()` (`:269-291`) sends `PUT /api/settings/model`, then `PUT /api/settings/preferences`. It updates `last4` and clears the key field only after both succeed (`:287-288`). When the second request fails, the key is already stored, but the page still shows the old saved key and keeps the typed key in the field.
  - `showError()` (`:203-214`) ties `connection_failed` to the Base URL field and four key codes to the API key field. Every other code becomes a form-wide `error`, which renders after all groups (`:428`), below the Browser extension and X accounts groups. The load failure of `:94` uses the same element.
  - The success message is created together with its `role="status"` element (`:362`). So are `browserMessage` (`:383`) and `xMessage` (`:426`). `modelStatus` (`:320`) and `copyMessage` (`:381`) stay mounted.
  - "Delete all X data" swaps itself for a confirmation group, and the group swaps back (`:416-424`). Disconnect removes its own list item (`:390`). Neither moves focus.
- **Backend codes for Save** (`backend/src/catchup/api/settings.py`):
  - `PUT /settings/model` answers `invalid_model_config` when the URL is not a valid provider URL or the model is empty (`:223`), and `api_key_required` or `missing_api_key` for key problems. Encrypting a new key raises `secret_not_configured` when the server has no secret (`crypto.py:14`).
  - `PUT /settings/preferences` answers `invalid_language` for a blank or over-long language (`:291`).
- **Settings form validation.** The Model select is `disabled` until a test lists models (`Settings.tsx:329`). A disabled control is skipped by form validation, so Save before a test sends an empty `model_id` and gets `invalid_model_config`. The Other language input exists only while "Other" is selected (`:343`); it is `required`, so an empty value blocks Save, but a value of spaces reaches the server and gets `invalid_language`.
  - `testConnection()` clears `error`, `errorField`, and `message` (`:235`).
  - The field error paragraph at `:323` renders for any `errorField`, with `id` `base-error` or else `key-error`.
- **Home** (`frontend/src/pages/Home.tsx`):
  - The run button is `disabled={running || modelReady === null}` in the run bar (`:252`) and on the Generate screen (`:286`). In a browser, a focused button that becomes disabled loses focus to `<body>`. jsdom keeps it focused (fresh-eyes probe), so tests must also check that the button is not `disabled`.
  - While the page loads, it renders only "Loading…" (`:237`), and `modelReady` is set in the same callback that ends loading (`:161`, `:169`). So `modelReady === null` never occurs with a run button on the page.
  - When Generate gets `model_not_configured` (`:215`), the page switches to the first-run actions, and the focused button is replaced.
  - When the first digest arrives, `digest` becomes set and the page switches from the Generate screen to `DigestArticle` (`:238` versus `:269`). The Generate screen's button is unmounted.
  - `StatusRegion` (`components/ui.tsx:107`) stays mounted, as the spec requires (user-interface, "Keyboard and screen-reader support").
  - The first-run and no-sources variants render separate, always-disabled buttons (`:243`, `:247`, `:278`, `:282`). They never have focus and are out of scope.
- **Sources** (`frontend/src/pages/Sources.tsx`):
  - The delete confirmation already moves focus to Cancel, back to Delete, or to the list heading after a deletion (`:133-146`), with `ref`s and effects. This is the pattern to reuse.
  - "Save and preview" unmounts its own form (`setNeedsXToken(false)`, `:184`). Confirm source and Cancel unmount the preview (`:201`, `:246`). None of them moves focus.
  - `message` is created together with its `role="status"` element (`:244`).
- **Popup** (`extension/src/popup.ts`):
  - Every view change calls `root.replaceChildren(...)` (`:120`, `:165`, `:184`, `:279`, `:302`). Each call detaches the one `statusText` element and appends it again, so the live region leaves and re-enters the document. The node stays the same, so only a `MutationObserver` shows the removal (fresh-eyes probe).
  - `popup.css` styles by position: `#popup, #popup section { display: grid }` (`:35`) stacks the buttons, and `#popup > p:nth-child(2)` (`:37`) mutes the host line.
  - `savePage`, `removePage`, and `saveXToken` set `disabled` on the focused button while they work (`:198`, `:242`, `:307`).
- **Styles.**
  - `frontend/src/styles/components.css:17-22` styles `.btn:disabled` and excludes `:disabled` from hover. `styles/tokens.test.ts:102` checks the `.btn:disabled` rule.
  - `extension/src/popup.css:60-63` does the same for `button:disabled`. `tokens.test.ts:104` finds the rule with the regex `\.btn:disabled\s*\{`, so a combined selector list would break it.
  - `.page` and `.settings-section` are grids with a row gap (`layout.css:13`, `:38`), and the save bar is a flex row with a gap. An empty paragraph there still adds a gap. `browserMessage`, `xMessage`, and the Sources `message` are direct children of these grids.
- **Tests.** Frontend tests use `fireEvent` and `expectAccessible` (`frontend/src/test/accessibility.ts`), with no `user-event`. The extension's `src/test/popup.test.ts` runs the popup in jsdom. Existing assertions that the new behavior replaces:
  - `Home.test.tsx` checks `toBeDisabled()` on "Generating…" (`:948`, `:967`, `:1120`). The other `toBeDisabled()` checks (`:246`, `:909`, `:934`, `:1212`, `:1230`, `:1250`) are on the always-disabled first-run and no-sources buttons and stay;
  - `Settings.test.tsx:329` expects invalid-language errors to be form-wide;
  - `Settings.test.tsx:350` checks the load failure.
  - `extension/src/test/popup.test.ts:283` checks that Add is `disabled` while it saves.

## Goals / Non-Goals

**Goals:**
- Every Settings Save result is visible and announced at the save bar, and a field error marks its field.
- No action in the issues' list leaves keyboard focus on `<body>`.
- Result messages are announced through status regions that exist before the message.

**Non-Goals:**
- No backend or API change.
- The always-disabled first-run and no-sources Generate buttons.
- The options page of the extension, and pages not named in the issues, except Settings' Disconnect, which removes its own button in the same way.
- Alerts (`role="alert"`) that are inserted with their text. Screen readers announce an inserted alert, so they stay as they are.

## Decisions

### D1. Settings Save feedback (#71)

- **Where results go.** The save bar gets a status region that is always mounted, and an alert for errors without a field, shown only while there is an error. The form-wide error element at the bottom (`:428`) is removed.
  - Success: the status region reads "Settings saved.", with class `inline-msg msg-ok` and the check icon.
  - The "not saved" note for a field error: the same status region, with class `inline-msg msg-error` and the alert icon.
  - An error without a field: a `field-error` paragraph with `role="alert"` and the alert icon, inside the save bar.
  - Test connection, a model choice, and the next Save clear the save bar's results.
- **Field mapping on Save.**
  - `invalid_model_config`: when the model is empty, it marks the Model select. The message is "Test the connection, then choose a model." Otherwise it marks the Base URL field: "Enter a valid provider URL, such as https://api.deepseek.com."
  - `invalid_language` marks the Other language field with the server's message.
  - The existing key and base-URL mappings stay.

  A field error uses the existing pattern: `aria-invalid`, plus a `field-error` paragraph with `role="alert"` and an `id` that the field's `aria-describedby` names. The existing paragraph after Test connection (`:323`) renders only for `base` and `key`. The Model select's new paragraph (`id="model-select-error"`) sits directly after the select. The Other language field's (`id="other-error"`) sits after its input. When `invalid_language` arrives while the Other language field is not shown, it is an error without a field. Each message appears once on the page. The save bar's status region then reads "Settings were not saved. Check the <label> field." The label is Model, Base URL, Other language, or API key. The disabled Model select cannot take focus, but its message is visible next to it and named by the save bar.
- **Two requests.** After the model request succeeds, `save()` updates `last4` and `savedBaseUrl`, and clears the key field, before it sends the preferences. When the preferences request then fails, the save bar starts with "The model settings were saved, but the Digest and YouTube settings were not." instead of "Settings were not saved.":
  - for a field error, its status region reads that sentence, then "Check the Other language field.";
  - otherwise, its alert reads that sentence, then the error message, for example "Could not connect to CatchUp.".
- **Load failure.** A separate `loadError` is shown as an error `Alert` (titled "Could not load settings") directly under the page head, above the form.
- **Alternative: show every Save error, field or not, only in the save bar.** Rejected: the spec requires that field errors are linked to their inputs and that invalid inputs are marked invalid (user-interface, "Keyboard and screen-reader support").
- **Alternative: move focus to the invalid field after Save.** Rejected for now: the disabled Model select cannot take focus. The other cases would behave differently from Test connection, which does not move focus.

### D2. Busy controls stay focusable (#72)

- **Main screen.** Both Generate / Try again buttons use `aria-disabled="true"`, not `disabled`, while `running || modelReady === null`. The click handler returns at once while `aria-disabled` is set. The label stays as today ("Generating…" while running). `modelReady === null` cannot occur with the button on the page (Context), so only the running case is tested.
- **Style.** In `components.css`, `.btn[aria-disabled="true"]` and `.btn-primary[aria-disabled="true"]` get the same rules as `:disabled`, as separate rules next to the `:disabled` ones, not as a combined selector list. Every `:not(:disabled):hover` selector also excludes `[aria-disabled="true"]`. A test in `styles/tokens.test.ts` checks both.
- **First digest.** Home remembers whether its Generate-screen button had focus when the first digest replaced that screen. The check runs in the `.then` that loads the new digest, before `setDigest` (`:195`), because by the time an effect runs, the button is already unmounted. After the switch, an effect focuses the run bar's Generate button.
- **No model.** When Generate gets `model_not_configured` while the button had focus, focus moves to "Set up your model" after the first-run actions render. It moves focus only in that case, so the existing rule still holds: when a later digest replaces the one shown, focus does not move (`Home.test.tsx:455` keeps passing).
- **Popup.** "Add this page to my next digest", Remove, and the X token's Save set `aria-disabled="true"` while they work, and their handlers return at once while it is set. `popup.css` gives `button[aria-disabled="true"]` the `:disabled` look, in a rule after `button.primary` (`:61`) so that a busy Add does not keep the primary look, and excludes it from hover.
- **Alternative: keep `disabled`, and put focus back afterwards.** Rejected: focus is already lost while the run is in progress, and a screen reader announces nothing about the button.

### D3. Focus after in-place changes (#72)

Use the Sources delete pattern: a `ref` on the target, set a flag in the handler, and focus the target in an effect after the render that shows it. A heading that receives focus gets `tabIndex={-1}`.

| Action | Focus target |
| --- | --- |
| Settings "Delete all X data" | Cancel in the confirmation |
| Settings Cancel in that confirmation | "Delete all X data" |
| Settings "Delete X data", success | X accounts heading (the section's `h2`) |
| Settings "Delete X data", failure | unchanged (the confirmation stays) |
| Settings Disconnect, success | "Connected browsers" heading |
| Sources "Save and preview", preview shown | the preview's heading (`.preview-title`). The X token form stays mounted until the repeated preview answers, then unmounts |
| Sources "Save and preview", token saved but preview failed | the address field |
| Sources Confirm source, success | the address field (now empty) |
| Sources preview Cancel | the address field |
| Home, first digest replaces the Generate screen while its Generate button had focus | Generate in the run bar |
| Home, Generate gets `model_not_configured` while it had focus | "Set up your model" |

`SettingsSection` gains an optional heading `ref`, so the X accounts heading can receive focus.

### D4. Status regions stay mounted (#72)

These paragraphs are always rendered with their `role="status"`, and are empty when there is nothing to say:
- the Settings save bar's status;
- `browserMessage` and `xMessage` in Settings;
- `message` on the Sources page.

They keep their current classes and icons, which render only with text, and an empty region has no child nodes. An empty region still adds a grid or flex gap (Context). So a rule in `components.css`, `.app [role="status"]:empty { position: absolute; }`, takes empty regions out of the layout, and a test in `styles/tokens.test.ts` checks it. Do not hide an empty region with `display: none` or `visibility: hidden`, because that removes it from the accessibility tree.

### D5. The popup's view changes (#72)

- **Layout.** After connecting, `root` holds a content `div` (class `popup-content`) and the status line. Views replace only the content container's children, so the status line stays in the document. `popup.css` moves the grid rule and the host-line rule to the container (`#popup .popup-content` and `#popup .popup-content > p:nth-child(2)`), so the popup looks as before. `disconnected()` and the "Could not connect" view still replace `root`'s content, because the status line is not used there.
- **Focus.** Each view function takes the focus target named in the browser-extension spec delta, and focuses it after rendering. The first `connected()` call, when the popup opens, does not move focus. When an action ends in `disconnected()`, "Open options" receives focus. When the popup opens disconnected, focus is not moved.
- **Preview heading.** The preview's `h2` gets `tabIndex = -1`.
- **Handlers.** `button('Cancel', connected)` passes the click event to `connected`. When `connected` takes a focus target, the handler wraps it.

## Risks / Trade-offs

- [`aria-disabled` buttons still receive clicks] → Each handler checks the flag first. Tests press the button while it is busy and assert that no second request is sent.
- [Moving focus unexpectedly] → Focus moves only when the focused control was removed, or when a view replaces the popup's content after the user's own action. The existing "focus does not move when a digest is replaced" test stays.
- [jsdom does not compute layout or move focus like a browser] → Tests check focus with `document.activeElement`, and check that a busy button is not `disabled`, because jsdom keeps focus on a disabled button. `fireEvent.click` does not focus a button, so a test focuses it first. Status regions are checked by identity; the popup's status line also with a `MutationObserver` that records no removal. The look of `aria-disabled` and of empty regions is checked through CSS rule tests. Claude Code checks the real behavior with the keyboard in the browser at review.

## Testing

- Test-first (D-016), at these seams:
  - `frontend/src/pages/Settings.test.tsx`, `Home.test.tsx`, and `Sources.test.tsx`, with `fireEvent`, `document.activeElement`, and `expectAccessible`;
  - `frontend/src/styles/tokens.test.ts`;
  - `extension/src/test/popup.test.ts`, in jsdom.
- At review, Claude Code checks with the keyboard in the browser: Settings Save errors, Delete all X data, Sources Save and preview, and Confirm. The checks run against a local stub API, with no real model key. Claude Code also runs the Docker smoke script.
