# Proposal

## Why

A system review on 2026-11-01 found two accessibility problems (#71, #72), and Claude checked both against `main` at `2f456cd` on 2026-11-15.
- **#71.** When Save in Settings fails with an error that belongs to no field, the error appears at the very bottom of the page. For example, `invalid_model_config` happens when no model is chosen yet, and `secret_not_configured` when the server has no instance secret. The bottom is below the Browser extension and X accounts groups, so nothing visibly changes near Save. The Model select is not marked invalid.
- **#72.** Keyboard focus falls to the page body in two cases: when a control becomes `disabled` while it has focus (Generate during a run), and when a control removes itself from the page (confirmation buttons, the X token form, the source preview, the popup's views). Several result messages also create their status element together with the text, so screen readers may not announce them.

## What Changes

- **Settings Save feedback (#71).**
  - Save errors that belong to no field are shown and announced in the save bar, next to Save.
  - `invalid_model_config` marks the Model select invalid when no model is chosen, and the Base URL field otherwise.
  - `invalid_language` marks the "Other language" field.
  - A Save that stores the model settings, but then fails to store the Digest and YouTube settings, says so.
  - A load failure is shown at the top of the page.
- **Busy controls stay focusable (#72).** The main screen's Generate / Try again button uses `aria-disabled` while a run is in progress, instead of `disabled`, so it keeps keyboard focus. It looks the same as a disabled button. When the first digest replaces the Generate screen, focus that was on Generate moves to Generate in the run bar. When Generate finds no model set up, focus moves to "Set up your model". The popup's Add, Remove, and Save buttons follow the same rule while they work.
- **Focus after in-place changes (#72).** When a control removes itself, focus moves to a defined target:
  - in Settings: "Delete all X data", its Cancel and Delete, and Disconnect for a browser;
  - in Sources: "Save and preview", and the preview's Confirm and Cancel;
  - in the popup: every view change.
- **Status regions stay on the page (#72).** Result messages in Settings, Sources, and the popup use a status region that is present, and empty, before the message appears. An empty region takes no space.

## Capabilities

### New Capabilities
<!-- none -->

### Modified Capabilities
- `user-interface`: new requirements "Show Settings save results at Save" and "Keep focus and announcements when content changes in place".
- `browser-extension`: new requirement "Keep focus and announcements in the popup".

## Impact

- Frontend:
  - `frontend/src/pages/Settings.tsx`, `Home.tsx`, `Sources.tsx`, and their tests;
  - `frontend/src/styles/components.css`, with `styles/tokens.test.ts`, for the `aria-disabled` button style.
- Extension: `extension/src/popup.ts`, `popup.css`, and `src/test/popup.test.ts`.
- No backend, API, or data change. No new dependency.
