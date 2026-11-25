# Spec Delta

## ADDED Requirements

### Requirement: Choose how much the model reasons
The model configuration SHALL include one Reasoning choice: `default` (Provider default), `low`, or `off`.
- Reads MUST report it. When nothing is saved, and for a configuration saved before this choice existed, it is `default`.
- The OpenAI-compatible provider accepts `default`, `low`, and `off`. The Anthropic provider accepts `default` and `low`. Any other value, and `off` for Anthropic, MUST be refused, and nothing is saved.
- A save that names no Reasoning keeps the saved choice while the provider stays the same. A save that changes the provider and names no Reasoning sets it to `default`.

Every summary, merge, and grouping call of a digest run MUST send the choice that was saved when the run started:
- `default`: no reasoning parameter;
- OpenAI-compatible `low`: `reasoning_effort` set to `"low"`;
- OpenAI-compatible `off`: `reasoning_effort` set to `"none"`;
- Anthropic `low`: `output_config.effort` set to `"low"`, also when the call asks for a fallback model.

No call sends a `thinking` parameter. Listing models, connection tests, and the context-window lookup send no reasoning parameter.

When Reasoning is not `default` and the provider refuses a call with HTTP 400 or 422, the call MUST NOT be retried, and the run MUST fail at once, as for a rejected key: its items stay pending, and the run's message reads "The model provider rejected a request with the Reasoning setting. Choose Provider default in Settings, then generate again." This failure is a configuration error, so the main screen offers checking the settings as the primary action. With `default`, such a refusal is handled like any other provider error.

#### Scenario: Configuration saved before the setting existed
- **WHEN** a configuration was saved before the Reasoning choice existed, and the instance is upgraded
- **THEN** reads report the Reasoning `default`, and a digest run's model calls send no `reasoning_effort` and no `output_config`

#### Scenario: Reasoning off for an OpenAI-compatible provider
- **WHEN** an OpenAI-compatible configuration is saved with Reasoning `off`, and a digest run summarizes an item and groups the topics
- **THEN** every chat completion request of the run contains `"reasoning_effort": "none"`, and none contains `thinking`

#### Scenario: Low reasoning for Anthropic
- **WHEN** an Anthropic configuration with the model `claude-opus-5-5` is saved with Reasoning `low`, and a digest run summarizes an item and groups the topics
- **THEN** every Messages request of the run contains `"output_config": {"effort": "low"}` and asks for a fallback model, and none contains `thinking`

#### Scenario: Provider default sends nothing
- **WHEN** an OpenAI-compatible configuration is saved with Reasoning `default`, and a digest run summarizes an item
- **THEN** the chat completion request contains no `reasoning_effort`

#### Scenario: Off refused for Anthropic
- **WHEN** a client saves an Anthropic configuration with Reasoning `off`
- **THEN** the save is refused with a message asking for a Reasoning choice that the provider supports, and the saved configuration is unchanged

#### Scenario: Save without a Reasoning choice
- **WHEN** an OpenAI-compatible configuration is saved with Reasoning `low`, and a client saves another model ID without naming a Reasoning choice
- **THEN** the Reasoning stays `low`

#### Scenario: Provider changed without a Reasoning choice
- **WHEN** an OpenAI-compatible configuration is saved with Reasoning `off`, and a client saves an Anthropic configuration with a new key and no Reasoning choice
- **THEN** reads report the provider "anthropic" and the Reasoning `default`

#### Scenario: Provider refuses the setting
- **WHEN** Reasoning is `low`, and the provider answers one item's summary call with HTTP 400
- **THEN** that call is made once, the run fails with the message "The model provider rejected a request with the Reasoning setting. Choose Provider default in Settings, then generate again.", its items stay pending, and the main screen offers "Check settings" as the primary action

#### Scenario: Refusal with Provider default
- **WHEN** Reasoning is `default`, and the provider answers one item's summary call with HTTP 400
- **THEN** that item appears with a note that its summary is unavailable, and the run saves the digest

### Requirement: Choose reasoning in Settings
The Model provider group in Settings SHALL show a **Reasoning** select after **Model**. It shows the saved choice.
- Its options are "Provider default" and "Low", and also "Off" while OpenAI-compatible is the selected provider.
- Its hint reads "Less reasoning makes digests faster and cheaper. Summaries and topics may be less careful." and is associated with the select for assistive technology.
- Choosing a provider other than the saved one MUST set Reasoning to "Provider default". Choosing the saved provider again MUST restore the saved choice.

Every save from the Model provider group MUST send the Reasoning choice shown when that save starts: the automatic save after a successful test, a model choice, a Reasoning choice, and **Save**.

While the provider, base URL, and key fields match the saved configuration, choosing a Reasoning option SHALL save it right away, one save at a time in the order of the choices, together with model choices. The page MUST then read "Saved reasoning: <option>." with the option's label. Otherwise, the choice is saved by the next successful test or by **Save**. Results and errors MUST be shown and announced in the Model provider group, as for model choices; a failed save reads "The reasoning setting was not saved. " followed by the reason.

#### Scenario: Saved choice is shown
- **WHEN** an OpenAI-compatible configuration with Reasoning `off` is saved, and the user opens Settings
- **THEN** the Reasoning select reads "Off", comes after the Model select, offers "Provider default", "Low", and "Off", and is described by the hint

#### Scenario: Anthropic offers no Off
- **WHEN** an OpenAI-compatible configuration with Reasoning `off` is saved, and the user chooses "Anthropic"
- **THEN** the Reasoning select reads "Provider default" and offers only "Provider default" and "Low"

#### Scenario: Back to the saved provider restores Reasoning
- **WHEN** the user chooses "Anthropic" and then "OpenAI-compatible" again, without testing
- **THEN** the Reasoning select reads "Off" again

#### Scenario: Choosing Low saves it
- **WHEN** a configuration is saved with the model "saved-model", and the user chooses "Low"
- **THEN** the save sends the model "saved-model" and the Reasoning `low` with the saved key, and the page reads "Saved reasoning: Low."

#### Scenario: Edited key waits for a test
- **WHEN** the user pastes a new key, chooses "Low", and then a test succeeds
- **THEN** nothing is saved before the test, and the test's automatic save sends the Reasoning `low`

#### Scenario: Save sends the choice
- **WHEN** the user pastes a new key, chooses "Off", and clicks Save without testing
- **THEN** nothing is saved before Save, and Save sends the Reasoning `off` with the new key
