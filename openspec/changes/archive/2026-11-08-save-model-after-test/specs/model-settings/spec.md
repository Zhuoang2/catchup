# Spec Delta

## MODIFIED Requirements

### Requirement: Test the connection and list models
The system SHALL let the user test a configuration, whether or not one is saved. A successful test MUST return the provider's available model IDs so the user can pick one. The system MUST NOT rely on a hard-coded model list. The test request itself MUST NOT change the saved configuration; Settings saves the tested configuration in a separate step after a successful test (see "Save the model settings after a successful test").

#### Scenario: Valid credentials
- **WHEN** the user tests a configuration with a valid base URL and key
- **THEN** the system reports success and returns the provider's model IDs

#### Scenario: Invalid key
- **WHEN** the provider rejects the key
- **THEN** the system reports that the API key was rejected, without exposing the key

#### Scenario: Unreachable provider
- **WHEN** the base URL cannot be reached or does not answer within 15 seconds
- **THEN** the system reports a connection error that names the base URL

## ADDED Requirements

### Requirement: Save the model settings after a successful test
In Settings, a successful **Test connection** SHALL save the configuration that was tested, without the user clicking **Save**:
- It saves the base URL and, when the user entered one, the API key, as they were when the test started.
- It saves the selected model when the provider lists it. Otherwise the first listed model is selected and saved.
- The page MUST say what was saved, naming the key only by its last four characters. When the first listed model replaced the selection and other models are listed, the message MUST say that choosing another model changes it.
- A failed test MUST NOT save anything.
- When the provider lists no models, nothing is saved, and the page says so.
- When saving fails after a successful test, the page MUST say that the connection worked but nothing was saved, and why.

While the base URL and key fields match the saved configuration (the base URL is unchanged and no new key is entered), choosing another listed model SHALL save it right away. Model choices made in quick succession MUST be saved one at a time in the order they were made, so the last choice is the one kept. Otherwise a model choice is saved only by the next successful test or by **Save**.

When a key is saved, the key field's hint MUST say that testing a new key saves it. The results of a test, of the automatic save, and of a model choice MUST be shown in the Model provider group next to **Test connection**:
- Success messages, and the message that no models were listed, MUST be announced through a status region that stays on the page.
- Errors that are not tied to the base URL or key field MUST be shown and announced as an alert in the same group, not at the bottom of the page.

**Save** keeps saving all fields, and Digest and YouTube settings are saved only by **Save**.

#### Scenario: First setup is saved by the test
- **WHEN** no model settings are saved, the user pastes a key ending in "3f9a", and a test succeeds with the models "live-a" and "live-b"
- **THEN** the base URL, the key, and the model "live-a" are saved, the page reads "Connection succeeded. Saved key ending in 3f9a with model live-a. Choose another model to change it.", the key field is empty, and the page reads "Saved key ending in 3f9a"

#### Scenario: Main screen after only a test
- **WHEN** a test has saved the model settings, a source exists, and the user opens the main screen without having clicked Save
- **THEN** Generate digest is available, and "Set up your model" is not the primary action

#### Scenario: Testing a new key replaces the saved key
- **WHEN** a key ending in "1234" is saved with the model "saved-model", the user pastes a new key ending in "9999", and a test succeeds with "saved-model" listed
- **THEN** the new key is saved with the model "saved-model", and the page reads "Connection succeeded. Saved key ending in 9999 with model saved-model."

#### Scenario: Test with the saved key
- **WHEN** a key is saved, the key field is empty, and a test succeeds with the saved model listed
- **THEN** the saved key is kept, and the page reads "Connection succeeded. Saved model saved-model."

#### Scenario: Failed test saves nothing
- **WHEN** the provider rejects the key during a test
- **THEN** no save request is sent, the saved configuration is unchanged, and the rejection is shown at the key field

#### Scenario: Provider lists no models
- **WHEN** a test succeeds but the provider lists no models
- **THEN** nothing is saved, and the page reads "Connection succeeded, but the provider listed no models. Nothing was saved."

#### Scenario: Saving fails after a successful test
- **WHEN** a test with a new key succeeds, but saving is refused because the instance secret is not configured
- **THEN** the Model provider group says that the connection succeeded but nothing was saved, and explains how to set the secret, and the key stays in the field

#### Scenario: Choosing another model saves it
- **WHEN** a test has saved the model "live-a", and the user chooses "live-b"
- **THEN** "live-b" is saved with the saved key, and the page reads "Saved model live-b."

#### Scenario: Edited fields wait for a test
- **WHEN** a test has saved the settings, the user then pastes another key or changes the base URL, and chooses another model
- **THEN** nothing is saved until the next successful test or Save

#### Scenario: Quick successive choices
- **WHEN** the user chooses "live-b" and then "live-c" before the first choice has finished saving
- **THEN** the second save starts only after the first has finished, "live-c" is the saved model, and the page reads "Saved model live-c."

#### Scenario: Key hint names the new behavior
- **WHEN** a key is saved and the user opens Settings
- **THEN** the key field's hint reads "Leave empty to keep the saved key. Testing a new key saves it."
