# Spec Delta

## ADDED Requirements

### Requirement: Learn the model's context window
At the start of a digest run, when the saved configuration has no recorded context window, the system SHALL ask the provider's model list once. When that list reports a context window for the entry whose ID equals the selected model ID, the system SHALL record it with the configuration. Only a positive integer is a valid context window. Later runs MUST reuse the recorded value without asking again. Changing the base URL or model ID MUST clear the recorded value. A missing or invalid value MUST NOT block saving or running; it means the context window is unknown.

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
