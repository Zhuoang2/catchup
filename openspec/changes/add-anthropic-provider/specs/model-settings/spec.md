# Spec Delta

## ADDED Requirements

### Requirement: Configure the model provider
The system SHALL let the user save a provider configuration consisting of a provider, a base URL, an API key, and a model ID. The provider is one of:
- **OpenAI-compatible**, for APIs that follow OpenAI's Chat Completions format, such as DeepSeek;
- **Anthropic**, for Anthropic's Messages API.

Only one configuration is active at a time. Reads MUST report the provider, the base URL, the model ID, and whether a key is set. When nothing is saved, reads report the OpenAI-compatible provider with the base URL `https://api.deepseek.com`. A configuration saved before providers existed is OpenAI-compatible. A save or connection test that names no provider uses the saved provider, or OpenAI-compatible when nothing is saved. Any other provider value MUST be refused, and nothing is saved.

#### Scenario: Save a configuration
- **WHEN** the user submits the Anthropic provider, a base URL, an API key, and a model ID
- **THEN** the system stores the configuration, and later reads report the provider "anthropic", the base URL, the model ID, and that a key is set

#### Scenario: Update without re-entering the key
- **WHEN** the user changes the model ID and leaves the key field empty
- **THEN** the system keeps the previously stored key

#### Scenario: Configuration saved before the upgrade
- **WHEN** a configuration was saved before providers existed, and the instance is upgraded
- **THEN** reads report the provider "openai_compatible", with the same base URL, model ID, and key

#### Scenario: Save without a provider
- **WHEN** an Anthropic configuration is saved, and a client saves another model ID without naming a provider
- **THEN** the provider stays "anthropic"

#### Scenario: Unknown provider
- **WHEN** a client saves the provider "gemini"
- **THEN** the save is refused with a message asking for a valid provider, and the saved configuration is unchanged

### Requirement: Choose the provider in Settings
The Model provider group in Settings SHALL start with a **Provider** select that offers "OpenAI-compatible" and "Anthropic" and shows the saved provider.
- Choosing a provider other than the saved one MUST set **Base URL** to that provider's default address: `https://api.deepseek.com` for OpenAI-compatible, `https://api.anthropic.com` for Anthropic. It MUST empty the model list until the next successful test, hide the saved-key text, and show the key hint "Enter an API key for this provider."
- Choosing the saved provider again MUST restore the saved base URL, the saved model and its list, and the saved-key text.
- **Base URL** stays editable for both providers.
- The message for an invalid provider address MUST name the selected provider's default address as its example.
- Tests and saves send the selected provider.

#### Scenario: Choose Anthropic
- **WHEN** an OpenAI-compatible configuration with a key ending in "1234" is saved, and the user chooses "Anthropic"
- **THEN** Base URL reads `https://api.anthropic.com`, the Model select reads "Test the connection to list models", "Saved key ending in 1234" is not shown, and the key hint reads "Enter an API key for this provider."

#### Scenario: Back to the saved provider
- **WHEN** the user chooses "Anthropic" and then "OpenAI-compatible" again, without testing
- **THEN** Base URL, the Model select, and "Saved key ending in 1234" show the saved configuration again

#### Scenario: Test a new provider
- **WHEN** the user chooses "Anthropic", pastes a key ending in "7d2e", and a test succeeds with the models `claude-opus-5-5` and `claude-sonnet-5-5`
- **THEN** the provider "anthropic", `https://api.anthropic.com`, the key, and the model `claude-opus-5-5` are saved, and the page reads "Connection succeeded. Saved key ending in 7d2e with model claude-opus-5-5. Choose another model to change it."

#### Scenario: Invalid address for Anthropic
- **WHEN** the selected provider is Anthropic, and Save is refused because the base URL is not a valid address
- **THEN** the Base URL field's message reads "Enter a valid provider URL, such as https://api.anthropic.com."

## MODIFIED Requirements

### Requirement: Test the connection and list models
The system SHALL let the user test a configuration, whether or not one is saved. A successful test MUST return the provider's available model IDs so the user can pick one. The system MUST NOT rely on a hard-coded model list. The test request itself MUST NOT change the saved configuration; Settings saves the tested configuration in a separate step after a successful test (see "Save the model settings after a successful test"). For the Anthropic provider, the model IDs come from Anthropic's model list, in the order it gives, except that `claude-opus-5-5` MUST be listed first when Anthropic lists it, so that a first setup selects it.

#### Scenario: Valid credentials
- **WHEN** the user tests a configuration with a valid base URL and key
- **THEN** the system reports success and returns the provider's model IDs

#### Scenario: Invalid key
- **WHEN** the provider rejects the key
- **THEN** the system reports that the API key was rejected, without exposing the key

#### Scenario: Unreachable provider
- **WHEN** the base URL cannot be reached or does not answer within 15 seconds
- **THEN** the system reports a connection error that names the base URL

#### Scenario: Anthropic lists its models
- **WHEN** the user tests an Anthropic configuration, and Anthropic lists `claude-sonnet-5-5`, `claude-opus-5-5`, and `claude-haiku-5-5`, in that order
- **THEN** the test returns `claude-opus-5-5`, `claude-sonnet-5-5`, and `claude-haiku-5-5`, in that order

### Requirement: Never send the stored key to a different provider address
The system MUST use the stored API key only with the stored provider and base URL. A save or connection test that changes the provider or the base URL MUST include a new API key.

#### Scenario: Base URL changed without a key
- **WHEN** a key is stored for one base URL and the user saves or tests a different base URL without entering a key
- **THEN** the request is refused with a message asking for the API key, and no request is sent to the new address

#### Scenario: Provider changed without a key
- **WHEN** a key is stored for an OpenAI-compatible provider, and the user saves or tests the Anthropic provider without entering a key
- **THEN** the request is refused with a message asking for the API key, no request is sent to Anthropic, and the saved configuration is unchanged

### Requirement: Report provider errors meaningfully
When a model call fails, the system SHALL distinguish authentication failure, insufficient balance, rate limiting, and temporary provider errors, and show the user a message suited to each. For the Anthropic provider, a rejected request because the account reached its spend limit counts as insufficient balance and is not retried, and an overloaded answer (HTTP 529) counts as a temporary provider error.

#### Scenario: Insufficient balance
- **WHEN** the provider responds that the account balance is insufficient
- **THEN** the user sees a message saying the provider account has insufficient balance

#### Scenario: Anthropic spend limit reached
- **WHEN** Anthropic answers HTTP 429 with the error code `enforced_spend_limit_reached`
- **THEN** the call is not retried, and the user sees the insufficient-balance message

### Requirement: Learn the model's context window
At the start of a digest run, when the saved configuration has no recorded context window, the system SHALL ask the provider's model list once. When that list reports a context window for the entry whose ID equals the selected model ID, the system SHALL record it with the configuration. Only a positive integer is a valid context window. Later runs MUST reuse the recorded value without asking again. Changing the provider, the base URL, or the model ID MUST clear the recorded value. For the Anthropic provider, the context window is the maximum number of input tokens that Anthropic's model list reports for the model. A missing or invalid value MUST NOT block saving or running; it means the context window is unknown.

#### Scenario: Provider reports a context window
- **WHEN** a run starts and the provider lists the selected model with a context window of 1,000,000 tokens
- **THEN** the run uses that context window, the configuration records it, and the next run does not ask the provider again

#### Scenario: Provider reports none
- **WHEN** the provider's model list has no context window for the selected model
- **THEN** the run treats the context window as unknown and still completes

#### Scenario: Invalid value
- **WHEN** the provider lists the selected model with a context window of `"12"` (a string) or `true`
- **THEN** the context window is treated as unknown

#### Scenario: Model changed
- **WHEN** the user saves a different model ID
- **THEN** the recorded context window is cleared and the next run asks the provider again

#### Scenario: Provider changed
- **WHEN** a context window is recorded, and the user saves the Anthropic provider with a new key and the same model ID
- **THEN** the recorded context window is cleared, and the next run asks Anthropic's model list

### Requirement: Save the model settings after a successful test
In Settings, a successful **Test connection** SHALL save the configuration that was tested, without the user clicking **Save**:
- It saves the provider, the base URL and, when the user entered one, the API key, as they were when the test started.
- It saves the selected model when the provider lists it. Otherwise the first listed model is selected and saved.
- The page MUST say what was saved, naming the key only by its last four characters. When the first listed model replaced the selection and other models are listed, the message MUST say that choosing another model changes it.
- A failed test MUST NOT save anything.
- When the provider lists no models, nothing is saved, and the page says so.
- When saving fails after a successful test, the page MUST say that the connection worked but nothing was saved, and why.

While the provider, base URL, and key fields match the saved configuration (the provider and base URL are unchanged and no new key is entered), choosing another listed model SHALL save it right away. Model choices made in quick succession MUST be saved one at a time in the order they were made, so the last choice is the one kept. Otherwise a model choice is saved only by the next successful test or by **Save**.

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

## REMOVED Requirements

### Requirement: Configure an OpenAI-compatible provider
**Reason**: Replaced by "Configure the model provider", which adds the choice between an OpenAI-compatible provider and Anthropic.
**Migration**: Existing configurations become OpenAI-compatible configurations with the same base URL, model ID, and key. Clients that send no provider keep working.
