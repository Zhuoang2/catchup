## ADDED Requirements

### Requirement: Show Settings save results at Save
When the user clicks **Save** in Settings, the result SHALL appear in the save bar next to Save. The save bar MUST contain a status region that is on the page, empty, before any result.
- Success MUST be announced through that status region.
- An error that belongs to no field MUST be shown and announced as an alert in the save bar, and nowhere else on the page.
- An error that belongs to a field MUST mark that field invalid, with its message linked to the field and announced as an alert. The save bar's status region MUST then say that the settings were not saved, and name the field. These errors belong to fields:
  - a missing model belongs to the Model select;
  - an invalid provider address belongs to the Base URL field;
  - an invalid language belongs to the Other language field;
  - a missing or rejected key belongs to the API key field.
- When the model settings were saved, but the Digest and YouTube settings were not, the save bar MUST say so, and why. The page MUST then show the saved key as saved and clear the key field.
- When Settings cannot be loaded, the error MUST be shown at the top of the page.

#### Scenario: Save before choosing a model
- **WHEN** no model has been listed or chosen, and the user clicks Save
- **THEN** the Model select is marked invalid and linked to a message that says to test the connection and choose a model, and the save bar says that the settings were not saved and names the Model field

#### Scenario: Server without an instance secret
- **WHEN** the user saves a new key, and the server refuses because its instance secret is not configured
- **THEN** the save bar shows and announces "Set CATCHUP_SECRET_KEY on the server before saving an API key.", and the message appears nowhere else on the page

#### Scenario: Settings saved
- **WHEN** Save succeeds
- **THEN** the save bar's status region, which was on the page before the click, announces "Settings saved."

#### Scenario: Model saved, other settings refused
- **WHEN** the model settings are saved with a new key ending in "3f9a", but saving the Digest and YouTube settings fails because the server cannot be reached
- **THEN** the save bar says that the model settings were saved but the Digest and YouTube settings were not, and why, the page reads "Saved key ending in 3f9a", and the key field is empty

#### Scenario: Settings cannot be loaded
- **WHEN** loading the settings fails
- **THEN** the error is shown at the top of the page, above the Model provider group

### Requirement: Keep focus and announcements when content changes in place
The web interface SHALL keep keyboard focus and screen-reader announcements when part of a page changes in place.
- **Busy controls.** While a run is in progress, the main screen's Generate / Try again button MUST stay focusable and be announced as unavailable. Activating it MUST do nothing. It MUST look the same as a disabled button.
- **Removed controls.** When an action removes the control that has focus, focus MUST move to this target:
  - "Delete all X data" in Settings: Cancel in its confirmation;
  - Cancel in that confirmation: "Delete all X data";
  - Delete X data, after the deletion succeeds: the X accounts heading;
  - Disconnect for a browser, after it succeeds: the "Connected browsers" heading;
  - "Save and preview" on the Sources page: the preview's heading when the preview is shown, otherwise the address field;
  - Confirm source, after the source is saved, and Cancel in the preview: the address field;
  - when the first digest replaces the Generate screen while Generate has focus: Generate in the run bar;
  - Generate, when the server answers that no model is set up: "Set up your model".

  While the Sources page repeats the preview after "Save and preview", the X token form MUST stay on the page, so focus does not fall to the page before the preview answers.
- **Announcements.** Result messages in Settings and on the Sources page MUST be announced through status regions that are on the page, empty, before the message appears. An empty status region MUST take no visible space. Errors MUST be announced as alerts.

#### Scenario: Generate keeps focus during a run
- **WHEN** a keyboard user presses Generate digest and the run starts
- **THEN** focus stays on the button, the button is announced as unavailable while the run is in progress, and pressing it again starts no second run

#### Scenario: Delete all X data with the keyboard
- **WHEN** a keyboard user chooses "Delete all X data", then Cancel
- **THEN** focus moves to Cancel in the confirmation, then back to "Delete all X data"

#### Scenario: X data deleted
- **WHEN** the user confirms the deletion of all X data, and it succeeds
- **THEN** focus moves to the X accounts heading, and the counts are announced through a status region that was on the page before

#### Scenario: Save and preview on the Sources page
- **WHEN** the user saves the X token from the Sources page, and the preview loads
- **THEN** focus moves to the preview's heading, and "X token saved." is announced through a status region that was on the page before

#### Scenario: Confirm a source
- **WHEN** the user confirms a source preview, and the source is saved
- **THEN** the address field is empty and has focus, and "Source saved." is announced

#### Scenario: First digest replaces the Generate screen
- **WHEN** the first digest is saved while Generate has focus on the Generate screen
- **THEN** the digest is shown, and focus is on Generate in the run bar

#### Scenario: Generate finds no model set up
- **WHEN** a keyboard user presses Generate digest, and the server answers that no model is set up
- **THEN** the page shows the first-run actions, and focus is on "Set up your model"
